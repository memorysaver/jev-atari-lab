"""Ten-round coordinator-guided Seaquest study with immutable proposals and full videos."""

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from statistics import mean

import ale_py.roms
import imageio.v2 as imageio

from jev_atari.arcade import make_game
from jev_atari.choice import ActionPolicy, ActionProgram
from jev_atari.experiment import split_for_seed
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.seaquest_observation import SCHEMA, Observer, screen_checks
from jev_atari.seaquest_pilot import MODEL, PIN, PilotEvaluator, SeaquestProgram
from jev_atari.study import StudyBudget

TRAIN = (320, 321)
DEV = (326, 327)
FINAL = (328, 329)
DECISIONS = 800
PREFIX_DECISIONS = 64
MAX_CALLS = 24000
LIVE_SECONDS = 86400
NAMES = (
    "NOOP",
    "FIRE",
    "UP",
    "RIGHT",
    "LEFT",
    "DOWN",
    "UPRIGHT",
    "UPLEFT",
    "DOWNRIGHT",
    "DOWNLEFT",
    "UPFIRE",
    "RIGHTFIRE",
    "LEFTFIRE",
    "DOWNFIRE",
    "UPRIGHTFIRE",
    "UPLEFTFIRE",
    "DOWNRIGHTFIRE",
    "DOWNLEFTFIRE",
)


@dataclass(frozen=True)
class CriteriaProgram(ActionProgram):
    schema_version: str = "seaquest-action-criteria-v2"

    def __post_init__(self):
        ActionProgram(name=self.name, guidance=self.guidance)
        if self.schema_version != "seaquest-action-criteria-v2":
            raise ValueError("Unknown Seaquest criteria schema")
        if not isinstance(self.action_criteria, dict) or set(self.action_criteria) != set(NAMES):
            raise ValueError("Exactly eighteen native action criteria required")
        if any(
            not isinstance(x, str) or not 1 <= len(x) <= 500 for x in self.action_criteria.values()
        ):
            raise ValueError("Criteria length must be 1..500")

    def request(self, observation, model):
        request = SeaquestProgram(guidance=self.guidance).request(observation, model)
        if set(self.action_criteria) != {
            a["ale_meaning"] for a in observation["candidate_actions"]
        }:
            raise ValueError("Cannot mask or introduce actions")
        request["questions"]["next_action"]["criteria"] = {
            a["ale_meaning"]: self.action_criteria[a["ale_meaning"]]
            for a in observation["candidate_actions"]
        }
        return request


def load_program(value):
    cls = (
        SeaquestProgram
        if value["schema_version"] == "seaquest-action-choice-v1"
        else CriteriaProgram
    )
    return cls.from_dict(value)


def prefix_actions(seed):
    rng = random.Random(seed)
    return [0] * 32 + [rng.randrange(18) for _ in range(32)]


class ResearchBudget:
    """Single-writer budget resumed only at round boundaries; each attempt is durable."""

    def __init__(self, path, round_number, *, clock=time.time):
        self.path, self.clock, self.round_number = path, clock, round_number
        if not path.exists():
            StudyBudget.save(
                self,
                {
                    "max_calls": MAX_CALLS,
                    "used": 0,
                    "started_at": None,
                    "live_seconds": LIVE_SECONDS,
                    "round_attempts": {},
                    "closed": False,
                },
            )
        state = read_json(path)
        self.used, self.max_calls = state["used"], state["max_calls"]

    def reserve(self):
        state, now = read_json(self.path), self.clock()
        key = str(self.round_number)
        limit = 2000 if self.round_number <= 8 else 4000
        if (
            state["closed"]
            or state["used"] >= MAX_CALLS
            or state["round_attempts"].get(key, 0) >= limit
        ):
            raise BudgetExceeded("Seaquest research call allocation closed/exhausted")
        if state["started_at"] is not None and now >= state["started_at"] + LIVE_SECONDS:
            raise BudgetExceeded("Seaquest research deadline exhausted")
        state["started_at"] = state["started_at"] or now
        state["used"] += 1
        state["round_attempts"][key] = state["round_attempts"].get(key, 0) + 1
        StudyBudget.save(self, state)
        self.used = state["used"]


class ResearchEvaluator(PilotEvaluator):
    """Prospective continuation transport; original pilot defaults remain unchanged."""

    def __init__(self, budget, *, client=None):
        super().__init__(budget, client=client)
        self.api.retry_statuses = self.api.retry_statuses | {520}

    @property
    def transport_manifest(self):
        return {
            **super().transport_manifest,
            "retry_http_statuses": sorted(self.api.retry_statuses),
        }


def play_episode(path, seed, evaluator, source, program, *, resume=False):
    if not resume:
        new_directory(path)
    observer, histogram = Observer(), Counter()
    ledger_start = len(evaluator.ledger)
    evaluator.api.trace_path = path / "model-exchanges.jsonl"
    summary = dict(
        status="incomplete",
        seed=seed,
        decisions=0,
        agent_decisions=0,
        frames=0,
        controlled_frames=0,
        reward=0.0,
        controlled_reward=0.0,
        prefix_reward=0.0,
        life_losses=0,
        controlled_life_losses=0,
        terminated=False,
        truncated=False,
        max_carried_divers=0,
    )
    previous_rows, previous_ledger, previous_wall = [], [], 0.0
    if resume:
        summary = read_json(path / "summary.json")
        manifest = read_json(path / "manifest.json")
        if summary["status"] != "incomplete" or summary["terminated"] or summary["truncated"]:
            raise ValueError("Only an unfinished nonterminal trajectory can resume")
        if manifest["seed"] != seed or manifest["program"] != program.to_dict():
            raise ValueError("Continuation must keep original seed and exact program")
        previous_rows = [
            json.loads(s) for s in (path / "transitions.jsonl").read_text().splitlines()
        ]
        previous_ledger = read_json(path / "api-ledger.json")
        previous_wall = summary["wall_seconds"]
        histogram.update(summary["action_histogram"])
        write_json(path / "predecessor-summary.json", summary)
        write_json(
            path / "continuation.json",
            {
                "source_revision": source,
                "predecessor_manifest_hash": digest(manifest),
                "predecessor_summary_hash": digest(summary),
                "program_hash": program.hash,
                "predecessor_files": {
                    name: {
                        "bytes": (path / name).stat().st_size,
                        "sha256": hashlib.sha256((path / name).read_bytes()).hexdigest(),
                    }
                    for name in ("transitions.jsonl", "model-exchanges.jsonl", "episode.mp4")
                },
                "predecessor_frames": summary["frames"],
                "predecessor_decisions": summary["decisions"],
                "recovery": "Exact raw-frame replay to the unexecuted observation; no old "
                "model calls repeated",
                "model_transport": evaluator.transport_manifest,
            },
        )
        (path / "episode.mp4").rename(path / "predecessor-episode.mp4")
    started, writer = time.monotonic(), None
    try:
        with (
            make_game("Seaquest") as env,
            (path / "transitions.jsonl").open("a" if resume else "x") as stream,
        ):
            env.reset(seed=seed)
            names = env.unwrapped.get_action_meanings()
            assert tuple(names) == NAMES
            lives = env.unwrapped.ale.lives()
            obs = observer.observe(
                env.unwrapped.ale.getRAM(), raw_frame=0, lives=lives, names=names
            )
            if not resume:
                write_json(
                    path / "manifest.json",
                    {
                        "kind": "seaquest-research-episode-v1",
                        "seed": seed,
                        "split": split_for_seed(seed),
                        "source_revision": source,
                        "program": program.to_dict(),
                        "program_hash": program.hash,
                        "schema": SCHEMA,
                        "action_names": names,
                        "model_transport": evaluator.transport_manifest,
                        "max_agent_decisions": DECISIONS,
                        "prefix_actions": prefix_actions(seed),
                    },
                )
            writer = imageio.get_writer(
                path / "episode.mp4",
                fps=60,
                codec="libx264",
                macro_block_size=1,
                ffmpeg_log_level="error",
            )
            replay_frames = 0
            for row in previous_rows:
                assert row["observation"] == obs
                for expected in row["frames"]:
                    _, reward, terminated, truncated, _ = env.step(row["action"])
                    ram, rgb = env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB()
                    lives = env.unwrapped.ale.lives()
                    assert expected == {
                        "ram": ram.tolist(),
                        "rgb_hash": hashlib.sha256(rgb.tobytes()).hexdigest(),
                        "reward": float(reward),
                        "lives": lives,
                        "terminated": terminated,
                        "truncated": truncated,
                    }
                    writer.append_data(rgb)
                    replay_frames += 1
                obs = observer.observe(
                    ram,
                    raw_frame=replay_frames,
                    lives=lives,
                    names=names,
                    ended=terminated or truncated,
                )
                assert obs == row["next_observation"] and screen_checks(obs, rgb) == row["checks"]
            if resume:
                assert (
                    replay_frames == summary["frames"]
                    and len(previous_rows) == summary["decisions"]
                )
                write_json(
                    path / "continuation-replay.json",
                    {
                        "status": "verified",
                        "frames": replay_frames,
                        "api_attempts": 0,
                        "resume_observation_hash": digest(obs),
                        "global_attempts_before_resume": evaluator.api.budget.used,
                    },
                )
            actor = ActionPolicy(evaluator, program)
            for decision in range(len(previous_rows), PREFIX_DECISIONS + DECISIONS):
                controlled = decision >= PREFIX_DECISIONS
                if controlled:
                    if decision == PREFIX_DECISIONS:
                        write_json(path / "controlled-start.json", obs)
                    action, prediction = actor.choose(obs)
                    histogram[names[action]] += 1
                else:
                    action, prediction = prefix_actions(seed)[decision], None
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
                    summary["controlled_frames"] += int(controlled)
                    summary["reward"] += float(reward)
                    summary["controlled_reward" if controlled else "prefix_reward"] += float(reward)
                    loss = max(0, lives - new_lives)
                    summary["life_losses"] += loss
                    summary["controlled_life_losses"] += loss * int(controlled)
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
                            "phase": "control" if controlled else "prefix",
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
                summary["max_carried_divers"] = max(
                    summary["max_carried_divers"], next_obs["carried_divers"] or 0
                )
                summary.update(decisions=decision + 1, terminated=terminated, truncated=truncated)
                summary["agent_decisions"] += int(controlled)
                obs = next_obs
                if controlled and summary["agent_decisions"] % 100 == 0:
                    print(
                        json.dumps(
                            {
                                "event": "progress",
                                "episode": str(path),
                                "decisions": summary["agent_decisions"],
                                "reward": summary["controlled_reward"],
                                "attempts": evaluator.api.budget.used,
                            }
                        ),
                        flush=True,
                    )
                if terminated or truncated:
                    break
            if summary["agent_decisions"] == 0:
                raise ValueError("Prefix terminated before model control")
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
        ledger = previous_ledger + evaluator.ledger[ledger_start:]
        summary.update(
            wall_seconds=previous_wall + time.monotonic() - started,
            api_attempts=len(ledger),
            reported_cost_usd=sum((e.get("usage") or {}).get("cost", 0) for e in ledger),
            action_histogram=dict(histogram),
        )
        write_json(path / "api-ledger.json", ledger)
        write_json(path / "summary.json", summary)
    return summary


def source_revision():
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Commit implementation before study execution")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def initialize(root):
    source = source_revision()
    for manifest in Path("artifacts/seaquest").rglob("manifest.json"):
        if read_json(manifest).get("seed") in TRAIN + DEV + FINAL:
            raise ValueError("Study seeds already exposed in episode manifests")
    new_directory(root)
    plan = {
        "kind": "seaquest-ten-round-study-v1",
        "source_revision": source,
        "rounds": 10,
        "train_seeds": TRAIN,
        "development_seeds": DEV,
        "final_seeds": FINAL,
        "decisions_per_episode": DECISIONS,
        "max_attempts": MAX_CALLS,
        "prefix": "32 NOOP holds then 32 random.Random(seed).randrange(18) holds; "
        "each hold 4 frames",
        "live_seconds": LIVE_SECONDS,
        "model": MODEL,
        "response_model": PIN,
        "schema": SCHEMA,
        "mode": 0,
        "difficulty": 0,
        "sticky": 0.25,
        "frameskip": 1,
        "hold_frames": 4,
        "program_baseline": SeaquestProgram().to_dict(),
        "rom_sha256": hashlib.sha256(ale_py.roms.get_rom_path("seaquest").read_bytes()).hexdigest(),
        "versions": {p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
        "authorship": "Interactive coordinator proposals based on training evidence; "
        "zero isolated teachers",
        "gate": "Paired controlled return: mean gain >=20 and no seed regression; "
        "both dev and final must pass",
        "candidate_selection": "Highest training mean among complete rounds 2..8; earliest round "
        "breaks ties",
    }
    write_json(root / "plan.json", plan)
    ResearchBudget(root / "budget.json", 1)
    write_json(
        root / "results.json", {"status": "running", "plan_hash": digest(plan), "rounds": []}
    )


def paired_gate(episodes):
    grouped = {}
    for row in episodes:
        grouped.setdefault(row["seed"], {})[row["role"]] = row["summary"]["controlled_reward"]
    gains = [p["candidate"] - p["baseline"] for p in grouped.values()]
    return {
        "passed": mean(gains) >= 20 and min(gains) >= 0,
        "mean_gain": mean(gains),
        "paired_gains": gains,
    }


def run_round(root, number, proposal_path=None):
    source = source_revision()
    plan, report = read_json(root / "plan.json"), read_json(root / "results.json")
    if (
        source != plan.get("continuation_revision", plan["source_revision"])
        or report["status"] != "running"
    ):
        raise ValueError("Study source changed or study closed")
    if number != len(report["rounds"]) + 1 or not 1 <= number <= 10:
        raise ValueError("Rounds must execute exactly once in order, stopping at ten")
    path = root / f"round-{number:02d}"
    new_directory(path)
    baseline = SeaquestProgram()
    if number <= 8:
        if number == 1:
            program = baseline
            proposal = {
                "origin": "unchanged coordinator baseline",
                "hypothesis": "Measure baseline under fixed varied starts",
                "program": program.to_dict(),
                "evidence": [],
                "risks": "Known DOWN/NOOP collapse may persist",
            }
        else:
            proposal = read_json(proposal_path)
            if set(proposal) != {"origin", "hypothesis", "program", "evidence", "risks"}:
                raise ValueError("Proposal must include provenance, hypothesis, risks and evidence")
            if proposal["origin"] != "interactive-coordinator-training-feedback":
                raise ValueError("Do not invent isolated teacher provenance")
            for evidence in proposal["evidence"]:
                evidence_path = Path(evidence)
                if (
                    evidence_path.name != "results.json"
                    or evidence_path.parent.parent.resolve() != root.resolve()
                ):
                    raise ValueError(
                        "Evidence must reference this study's completed training round"
                    )
                if (
                    int(evidence_path.parent.name.split("-")[1]) >= number
                    or int(evidence_path.parent.name.split("-")[1]) > 8
                ):
                    raise ValueError("Future or non-training evidence prohibited")
                if read_json(evidence_path)["status"] != "complete":
                    raise ValueError("Incomplete evidence")
            program = load_program(proposal["program"])
        write_json(path / "proposal.json", proposal)
        jobs = [("candidate", program, seed) for seed in TRAIN]
    else:
        if number == 9:
            candidates = [r for r in report["rounds"] if 2 <= r["round"] <= 8]
            chosen = max(candidates, key=lambda r: (r["mean_controlled_return"], -r["round"]))
            finalist = read_json(root / f"round-{chosen['round']:02d}" / "proposal.json")["program"]
            seal = {
                "chosen_training_round": chosen["round"],
                "program": finalist,
                "program_hash": load_program(finalist).hash,
                "frozen_before_development": True,
            }
            write_json(root / "finalist-seal.json", seal)
        seal = read_json(root / "finalist-seal.json")
        program = load_program(seal["program"])
        assert program.hash == seal["program_hash"]
        seeds = DEV if number == 9 else FINAL
        jobs = [
            (role, p, seed)
            for seed in seeds
            for role, p in (("baseline", baseline), ("candidate", program))
        ]
    round_plan = {
        "round": number,
        "study_plan_hash": digest(plan),
        "source_revision": source,
        "jobs": [
            {"role": role, "seed": seed, "program": p.to_dict(), "program_hash": p.hash}
            for role, p, seed in jobs
        ],
    }
    write_json(path / "plan.json", round_plan)
    budget = ResearchBudget(root / "budget.json", number)
    result = {
        "status": "incomplete",
        "round": number,
        "plan_hash": digest(round_plan),
        "episodes": [],
    }
    write_json(path / "results.json", result)
    evaluator = ResearchEvaluator(budget)
    try:
        for role, p, seed in jobs:
            summary = play_episode(path / role / f"seed-{seed}", seed, evaluator, source, p)
            result["episodes"].append({"role": role, "seed": seed, "summary": summary})
            write_json(path / "results.json", result)
        result.update(
            status="complete",
            mean_controlled_return=mean(
                e["summary"]["controlled_reward"]
                for e in result["episodes"]
                if e["role"] == "candidate"
            ),
        )
        if number >= 9:
            result["gate"] = paired_gate(result["episodes"])
        report["rounds"].append({k: v for k, v in result.items() if k != "episodes"})
        if number == 10:
            report["status"] = "complete"
            report["stopped_after_round"] = 10
            state = read_json(budget.path)
            state["closed"] = True
            StudyBudget.save(budget, state)
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        report["status"] = "incomplete-technical-stop"
        raise
    finally:
        evaluator.close()
        write_json(path / "results.json", result)
        report["budget"] = read_json(budget.path)
        write_json(root / "results.json", report)
    print(json.dumps(result), flush=True)


def continue_study(predecessor, root, audit, archive_manifest):
    """New append-only lineage, preserving the stopped original tree and its budget."""
    source = source_revision()
    old_plan, old_report, old_budget = [
        read_json(predecessor / f"{n}.json") for n in ("plan", "results", "budget")
    ]
    verified = read_json(audit / "verification.json")
    if (
        old_report["status"] != "incomplete-technical-stop"
        or len(old_report["rounds"]) != 3
        or verified["status"] != "verified"
        or verified["report_hash"] != digest(old_report)
        or verified["plan_hash"] != digest(old_plan)
    ):
        raise ValueError("Require the audited original round-four technical stop")
    archived = read_json(archive_manifest)
    archive_path = archive_manifest.parent / archived["archive"]
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != archived["sha256"]:
        raise ValueError("Predecessor archive checksum mismatch")
    for member in archived["files"]:
        original = predecessor / Path(member["path"]).relative_to(predecessor.name)
        if hashlib.sha256(original.read_bytes()).hexdigest() != member["sha256"]:
            raise ValueError("Predecessor differs from its closed archive")
    failed = predecessor / "round-04" / "candidate" / "seed-321"
    if read_json(failed / "api-ledger.json")[-1]["status"] != 520:
        raise ValueError("This continuation is specific to the preserved HTTP 520 stop")
    if root.exists():
        raise ValueError("Never overwrite a continuation root")
    shutil.copytree(predecessor, root)
    lineage = root / "continuation"
    for name in ("plan", "results", "budget"):
        write_json(lineage / f"predecessor-{name}.json", read_json(predecessor / f"{name}.json"))
    write_json(lineage / "predecessor-audit.json", verified)
    for name in ("closure", "stop-verification", "stop-costs"):
        if (root / f"{name}.json").exists():
            shutil.move(root / f"{name}.json", lineage / f"predecessor-{name}.json")
    plan = {
        **old_plan,
        "continuation_revision": source,
        "predecessor_root": str(predecessor),
        "predecessor_plan_hash": digest(old_plan),
        "predecessor_report_hash": digest(old_report),
        "predecessor_budget_hash": digest(old_budget),
        "predecessor_archive_sha256": archived["sha256"],
        "continuation": "Resume round 4 seed 321 at its recorded unexecuted observation; "
        "same overall budgets/deadline; add HTTP 520 to bounded transient "
        "retries",
    }
    write_json(root / "plan.json", plan)
    report = {**old_report, "plan_hash": digest(plan), "status": "continuing-round-04"}
    write_json(root / "results.json", report)
    path = root / "round-04"
    result = read_json(path / "results.json")
    write_json(lineage / "predecessor-round-04-results.json", result)
    budget = ResearchBudget(root / "budget.json", 4)
    evaluator = ResearchEvaluator(budget)
    try:
        program = load_program(read_json(path / "proposal.json")["program"])
        summary = play_episode(
            path / "candidate" / "seed-321", 321, evaluator, source, program, resume=True
        )
        result["episodes"].append({"role": "candidate", "seed": 321, "summary": summary})
        result.pop("error_type", None)
        result.update(
            status="complete",
            mean_controlled_return=mean(
                e["summary"]["controlled_reward"] for e in result["episodes"]
            ),
        )
        result["continuation_revision"] = source
        report["rounds"].append({k: v for k, v in result.items() if k != "episodes"})
        report["status"] = "running"
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        report["status"] = "incomplete-technical-stop"
        raise
    finally:
        evaluator.close()
        write_json(path / "results.json", result)
        report["budget"] = read_json(budget.path)
        write_json(root / "results.json", report)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--continue-from", type=Path)
    parser.add_argument("--predecessor-audit", type=Path)
    parser.add_argument("--predecessor-archive", type=Path)
    parser.add_argument("--round", type=int)
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--backend", choices=["openrouter"], required=True)
    args = parser.parse_args()
    if args.continue_from:
        continue_study(
            args.continue_from, args.root, args.predecessor_audit, args.predecessor_archive
        )
    elif args.initialize:
        initialize(args.root)
    else:
        run_round(args.root, args.round, args.proposal)
