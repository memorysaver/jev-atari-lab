"""Frozen fixed-question Seaquest pilot, with durable OpenRouter retry accounting."""

import argparse
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import ale_py.roms
import imageio.v2 as imageio

from jev_atari.arcade import make_game
from jev_atari.choice import ActionPolicy, ActionProgram
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.openrouter import OpenRouterChoiceEvaluator
from jev_atari.seaquest_observation import SCHEMA, Observer, screen_checks
from jev_atari.study import StudyBudget

MODEL = "~typesafe/jev-latest"
PIN = "typesafe/jev-1.13-20260917"
SEEDS = (310, 311)
DECISIONS = 800
MAX_ATTEMPTS = 2000


@dataclass(frozen=True)
class SeaquestProgram(ActionProgram):
    name: str = "seaquest-rescue-and-oxygen-baseline-v1"
    schema_version: str = "seaquest-action-choice-v1"
    guidance: str = (
        "Choose one native action to earn game score in Seaquest. Control the player submarine. "
        "Leave the surface by moving down to engage in play; remaining at the surface without "
        "scoring is not success. Collect divers by contacting them, avoid enemy bodies and "
        "missiles, and fire toward enemies when useful. Oxygen is a displayed resource with raw "
        "level 0..64; it decreases underwater. Return to the surface before it is exhausted. "
        "Return collected divers to the surface; capacity is six. Do not treat oxygen or "
        "carried-diver readings as a precomputed action or reward. Use current positions and "
        "recent motion to balance progress with survival. Do not chase an enemy into immediate "
        "danger or continue diving when oxygen is nearly empty. "
        "Boxes are [x,y,width,height], x increases right and y increases down. UP means decreasing "
        "y and DOWN increasing y; left/right change x. FIRE can be combined with movement. "
        "History has raw-frame timestamps and RAM-slot IDs, not guaranteed object identities. "
        "Do not extrapolate across subtype changes, sudden jumps, missing objects or life losses. "
        "When object_state is unavailable during animation/end, positions are unknown; choose "
        "NOOP until active observations return. Act for four raw frames, then reconsider."
    )

    def __post_init__(self):
        ActionProgram(name=self.name, guidance=self.guidance)
        if self.schema_version != "seaquest-action-choice-v1" or self.action_criteria is not None:
            raise ValueError("Unsupported Seaquest program schema")

    def request(self, observation, model):
        if observation["schema_version"] != SCHEMA or observation["game"] != "ALE/Seaquest-v5":
            raise ValueError("Seaquest observation contract mismatch")
        return {
            "model": model,
            "state": {"observation": observation},
            "questions": {
                "next_action": {
                    "type": "choice",
                    "instructions": {
                        "question": self.guidance,
                        "read": "observation.objects, observation.history, observation.oxygen_raw, "
                        "observation.carried_divers, observation.lives, observation.object_state, "
                        "observation.candidate_actions",
                        "contract": "Oxygen and active boxes passed limited training checks. "
                        "Exact shapes/identities and full rescue semantics remain provisional.",
                    },
                    "criteria": {
                        a["ale_meaning"]: f"Request {a['ale_meaning']} for four raw frames. "
                        "Directional names specify submarine motion; FIRE requests a torpedo."
                        for a in observation["candidate_actions"]
                    },
                }
            },
        }


class PilotBudget:
    def __init__(self, path, *, clock=time.time):
        if path.exists():
            raise ValueError("Never reset a pilot budget")
        self.path, self.clock = path, clock
        self.max_calls, self.used, self.started_at = MAX_ATTEMPTS, 0, None
        self.save()

    def save(self):
        StudyBudget.save(
            self,
            {
                "max_calls": self.max_calls,
                "used": self.used,
                "started_at": self.started_at,
                "live_seconds": 7200,
            },
        )

    def reserve(self):
        now = self.clock()
        if self.used >= self.max_calls or (
            self.started_at is not None and now >= self.started_at + 7200
        ):
            raise BudgetExceeded("Seaquest pilot attempt/time budget exhausted")
        if self.started_at is None:
            self.started_at = now
        self.used += 1
        self.save()


class PilotEvaluator(OpenRouterChoiceEvaluator):
    def __init__(self, budget, *, client=None):
        super().__init__(
            model=MODEL, expected_response_model=PIN, max_calls=budget.max_calls, client=client
        )
        self.api.budget = budget
        self.api.max_retries = 2
        self.api.retry_transport = True

    @property
    def transport_manifest(self):
        return {**super().transport_manifest, "max_retries": 2, "retry_transport": True}


def play_episode(path, seed, evaluator, source, program):
    new_directory(path)
    observer = Observer()
    ledger_start = len(evaluator.ledger)
    evaluator.api.trace_path = path / "model-exchanges.jsonl"
    summary = {
        "status": "incomplete",
        "seed": seed,
        "decisions": 0,
        "frames": 0,
        "reward": 0.0,
        "life_losses": 0,
        "terminated": False,
        "truncated": False,
        "active_underwater_decisions": 0,
        "max_carried_divers": 0,
    }
    started = time.monotonic()
    writer = None
    try:
        with make_game("Seaquest") as env, (path / "transitions.jsonl").open("x") as stream:
            env.reset(seed=seed)
            names = env.unwrapped.get_action_meanings()
            lives = env.unwrapped.ale.lives()
            obs = observer.observe(
                env.unwrapped.ale.getRAM(), raw_frame=0, lives=lives, names=names
            )
            write_json(
                path / "manifest.json",
                {
                    "kind": "seaquest-pilot-episode-v1",
                    "seed": seed,
                    "split": "train",
                    "source_revision": source,
                    "program": program.to_dict(),
                    "program_hash": program.hash,
                    "schema": SCHEMA,
                    "action_names": names,
                    "model_transport": evaluator.transport_manifest,
                    "max_decisions": DECISIONS,
                },
            )
            writer = imageio.get_writer(
                path / "episode.mp4",
                fps=60,
                codec="libx264",
                macro_block_size=1,
                ffmpeg_log_level="error",
            )
            actor = ActionPolicy(evaluator, program)
            for decision in range(DECISIONS):
                action, prediction = actor.choose(obs)
                frames = []
                for _ in range(4):
                    _, reward, terminated, truncated, _ = env.step(action)
                    ram, rgb = env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB()
                    new_lives = env.unwrapped.ale.lives()
                    frames.append(
                        {
                            "ram": ram.tolist(),
                            "rgb_hash": hashlib.sha256(rgb.tobytes()).hexdigest(),
                            "reward": float(reward),
                            "lives": new_lives,
                            "terminated": terminated,
                            "truncated": truncated,
                        }
                    )
                    writer.append_data(rgb)
                    summary["frames"] += 1
                    summary["reward"] += float(reward)
                    summary["life_losses"] += max(0, lives - new_lives)
                    lives = new_lives
                    if terminated or truncated:
                        break
                next_obs = observer.observe(
                    ram,
                    raw_frame=summary["frames"],
                    lives=lives,
                    names=names,
                    ended=terminated or truncated,
                )
                stream.write(
                    json.dumps(
                        {
                            "observation": obs,
                            "action": action,
                            "prediction": prediction,
                            "frames": frames,
                            "next_observation": next_obs,
                            "checks": screen_checks(next_obs, rgb),
                        }
                    )
                    + "\n"
                )
                stream.flush()
                player = next((o for o in obs["objects"] if o["kind"] == "player"), None)
                summary["active_underwater_decisions"] += bool(player and player["bbox"][1] > 46)
                summary["max_carried_divers"] = max(
                    summary["max_carried_divers"], next_obs["carried_divers"] or 0
                )
                summary.update(decisions=decision + 1, terminated=terminated, truncated=truncated)
                obs = next_obs
                if decision % 100 == 0:
                    print(
                        json.dumps(
                            {
                                "event": "pilot_progress",
                                "seed": seed,
                                "decisions": decision + 1,
                                "reward": summary["reward"],
                                "attempts": evaluator.api.budget.used,
                            }
                        ),
                        flush=True,
                    )
                if terminated or truncated:
                    break
            summary.update(
                status="complete",
                end_reason="native_termination"
                if terminated
                else "environment_truncation"
                if truncated
                else "frame_cap",
            )
    finally:
        if writer:
            writer.close()
        ledger = evaluator.ledger[ledger_start:]
        summary.update(
            wall_seconds=time.monotonic() - started,
            api_attempts=len(ledger),
            reported_cost_usd=sum((e.get("usage") or {}).get("cost", 0) for e in ledger),
        )
        write_json(path / "api-ledger.json", ledger)
        write_json(path / "summary.json", summary)
    return summary


def run(root, validation):
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Freeze committed pilot source before live access")
    gate = read_json(validation / "results.json")
    if not gate["pilot_gate_passed"] or gate["status"] != "complete":
        raise ValueError("Fresh observation validation gate not passed")
    for p in gate["episodes"]:
        audit = read_json(
            validation / "replay" / p["policy"] / f"seed-{p['seed']}" / "verification.json"
        )
        if audit["status"] != "verified" or audit["summary_hash"] != digest(p):
            raise ValueError("Missing/stale observation validation replay")
    for path in Path("artifacts/seaquest").rglob("manifest.json"):
        if read_json(path).get("seed") in SEEDS:
            raise ValueError("Pilot seeds already exposed in episode manifests")
    new_directory(root)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    program = SeaquestProgram()
    plan = {
        "kind": "seaquest-fixed-question-pilot-v1",
        "source_revision": source,
        "validation_results_hash": digest(gate),
        "validation_root": str(validation),
        "seeds": SEEDS,
        "split": "train",
        "decisions_per_episode": DECISIONS,
        "max_attempts": MAX_ATTEMPTS,
        "max_retries_per_decision": 2,
        "live_seconds": 7200,
        "program": program.to_dict(),
        "program_hash": program.hash,
        "model": MODEL,
        "response_model": PIN,
        "game": "ALE/Seaquest-v5",
        "schema": SCHEMA,
        "frameskip": 1,
        "hold_frames": 4,
        "sticky": 0.25,
        "mode": 0,
        "difficulty": 0,
        "reset_noops": 0,
        "automatic_fire": False,
        "full_action_space": False,
        "rom_sha256": hashlib.sha256(ale_py.roms.get_rom_path("seaquest").read_bytes()).hexdigest(),
        "versions": {p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
        "teacher_invocations": 0,
        "origin": "Coordinator-authored fixed instrumentation baseline; not learned.",
    }
    write_json(root / "plan.json", plan)
    budget = PilotBudget(root / "budget.json")
    report = {"status": "incomplete", "plan_hash": digest(plan), "episodes": []}
    write_json(root / "results.json", report)
    evaluator = None
    try:
        evaluator = PilotEvaluator(budget)
        for seed in SEEDS:
            report["episodes"].append(
                play_episode(root / f"seed-{seed}", seed, evaluator, source, program)
            )
            write_json(root / "results.json", report)
        report["status"] = "complete"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        raise
    finally:
        report["budget"] = read_json(budget.path)
        write_json(root / "results.json", report)
        if evaluator:
            evaluator.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend", choices=["openrouter"], required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--validation", type=Path, required=True)
    args = p.parse_args()
    run(args.out, args.validation)
