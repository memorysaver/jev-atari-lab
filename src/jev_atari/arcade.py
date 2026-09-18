"""Cross-game ALE discovery and a bounded raw-RAM direct-policy track.

Raw RAM is an experimental transport, not a verified semantic game adapter.
The separate Pong track retains its object observations and outcome critic.
"""

import hashlib
import json
import random
import time
from collections import deque
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import ale_py
import ale_py.roms
import gymnasium as gym
import imageio.v2 as imageio

from jev_atari.choice import ActionPolicy, ActionProgram
from jev_atari.io import digest, new_directory, write_json


def game_catalog() -> list[dict]:
    """Discover the installed discrete, single-agent ALE v5 scope without booting games."""
    gym.register_envs(ale_py)
    return [
        {
            "env_id": env_id,
            "name": env_id.removeprefix("ALE/").removesuffix("-v5"),
            "rom_id": spec.kwargs["game"],
            "semantic_adapter": "pong-objects" if env_id == "ALE/Pong-v5" else "not-implemented",
            "live_jev_evidence": "pong-pilot" if env_id == "ALE/Pong-v5" else "not-tested",
        }
        for env_id, spec in sorted(gym.registry.items())
        if env_id.startswith("ALE/")
        and env_id.endswith("-v5")
        and not spec.kwargs.get("continuous", False)
    ]


def resolve_game(value: str) -> dict:
    for game in game_catalog():
        if value.casefold() in {
            game["env_id"].casefold(),
            game["name"].casefold(),
            game["rom_id"].casefold(),
        }:
            return game
    raise ValueError(f"Unknown registered ALE game: {value}. Run 'jev-atari games'.")


def make_game(env_id: str, sticky: float = 0.25):
    if not 0 <= sticky <= 1:
        raise ValueError("sticky must be between 0 and 1")
    return gym.make(
        resolve_game(env_id)["env_id"],
        obs_type="ram",
        frameskip=1,
        repeat_action_probability=sticky,
        full_action_space=False,
        render_mode="rgb_array",
        max_episode_steps=-1,
    )


def inventory(*, check: bool = False, frames: int = 8) -> dict:
    if not 1 <= frames <= 1000:
        raise ValueError("Inventory frames must be between 1 and 1000 per game")
    games = game_catalog()
    for game in games:
        game["environment_status"] = "not-checked"
        if not check:
            continue
        env = None
        try:
            env = make_game(game["env_id"])
            _, _ = env.reset(seed=0)
            game["action_names"] = env.unwrapped.get_action_meanings()
            executed = 0
            # Exercise legal actions, including FIRE, without claiming meaningful play.
            for index in range(frames):
                _, _, terminated, truncated, _ = env.step(index % env.action_space.n)
                executed += 1
                if terminated or truncated:
                    break
            game.update(environment_status="smoke-passed", raw_frames=executed)
        except Exception as exc:
            game.update(environment_status="smoke-failed", error_type=type(exc).__name__)
        finally:
            if env is not None:
                env.close()
    return {
        "kind": "ale-catalog-v1",
        "ale_version": version("ale-py"),
        "scope": "installed discrete single-agent ALE/*-v5 registrations",
        "game_count": len(games),
        "checked": check,
        "api_attempts": 0,
        "games": games,
    }


@dataclass(frozen=True)
class ArcadeActionProgram(ActionProgram):
    name: str = "atari-raw-ram-direct-v1"
    guidance: str = (
        "Choose one available joystick action to maximize the game's cumulative reward. "
        "Use current RAM and recent history as evidence. Byte meanings and physical "
        "action effects have not been decoded; do not assume Pong coordinates. "
        "Some games require FIRE or movement to start or resume after losing a life."
    )
    schema_version: str = "arcade-action-choice-v1"
    game_id: str = "ALE/Breakout-v5"

    def __post_init__(self):
        ActionProgram(name=self.name, guidance=self.guidance)
        if self.schema_version != "arcade-action-choice-v1":
            raise ValueError("Expected an arcade-action-choice-v1 program")
        if resolve_game(self.game_id)["env_id"] != self.game_id:
            raise ValueError("Program game_id must be a canonical ALE environment ID")

    @classmethod
    def from_dict(cls, value: dict):
        if set(value) - {"name", "guidance", "schema_version", "game_id"}:
            raise ValueError("Unknown arcade program fields")
        return cls(**value)

    def request(self, observation: dict, model: str) -> dict:
        if observation["game"] != self.game_id or observation["schema_version"] != "atari-ram-v1":
            raise ValueError("Program and observation game/schema differ")
        return {
            "model": model,
            "state": {"observation": observation},
            "questions": {
                "next_action": {
                    "type": "choice",
                    "instructions": {
                        "question": self.guidance,
                        "read": "observation.ram_bytes, observation.history, observation.lives, "
                        "observation.last_reward and observation.candidate_actions",
                        "contract": "RAM array index is the byte address. Joystick names are "
                        "environment labels, not verified physical movement descriptions.",
                    },
                    "criteria": {
                        a["ale_meaning"]: f"Request joystick {a['ale_meaning']} "
                        f"for {a['hold_raw_frames']} raw frames (action {a['id']})."
                        for a in observation["candidate_actions"]
                    },
                }
            },
        }


def arcade_play(
    game: str,
    *,
    policy: str,
    seed: int,
    frames: int,
    hold: int,
    sticky: float,
    out: Path,
    evaluator=None,
    program: ArcadeActionProgram | None = None,
    video: bool = False,
) -> dict:
    game = resolve_game(game)
    if policy not in {"random", "jev-action"}:
        raise ValueError("Arcade policy must be random or jev-action")
    if frames < 1 or not 1 <= hold <= 16 or not 0 <= sticky <= 1 or seed < 0:
        raise ValueError("Invalid frame budget, hold duration, sticky probability or seed")
    if policy == "jev-action" and evaluator is None:
        raise ValueError("Jev policy requires an explicitly budgeted evaluator")
    if policy == "random" and (evaluator is not None or program is not None):
        raise ValueError("Random policy does not use a model or question program")
    if policy == "jev-action":
        program = program or ArcadeActionProgram(game_id=game["env_id"])
        if program.game_id != game["env_id"]:
            raise ValueError("Question program targets another game")
    new_directory(out)
    summary = {
        "status": "incomplete",
        "game": game["env_id"],
        "policy": policy,
        "seed": seed,
        "reward": 0.0,
        "raw_frames": 0,
        "decisions": 0,
        "end_reason": "error",
        "terminated": False,
        "truncated": False,
        "api_attempts": 0,
        "observation_source": "raw-ram",
        "semantic_adapter": "not-used",
    }
    env, writer = None, None
    started = time.monotonic()
    ledger_start = len(evaluator.ledger) if evaluator else 0
    try:
        env = make_game(game["env_id"], sticky)
        ram, info = env.reset(seed=seed)
        names = env.unwrapped.get_action_meanings()
        # Raw-frame capture uses an explicit 60-fps playback convention, not the
        # wrapper render_fps metadata (which is not the raw ALE clock).
        manifest = {
            "kind": "arcade-run-v1",
            "game": game,
            "seed": seed,
            "policy": policy,
            "frameskip": 1,
            "hold_frames": hold,
            "sticky": sticky,
            "frame_limit": frames,
            "mode": "ALE default",
            "difficulty": "ALE default",
            "reset_noops": 0,
            "auto_fire": False,
            "full_action_space": False,
            "action_names": names,
            "observation_schema": "atari-ram-v1",
            "history_length": 4,
            "rom_sha256": hashlib.sha256(
                ale_py.roms.get_rom_path(game["rom_id"]).read_bytes()
            ).hexdigest(),
            "versions": {p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
            "program": program.to_dict() if program else None,
            "program_hash": program.hash if program else None,
            "model": evaluator.model if evaluator else None,
            "max_api_calls": evaluator.api.budget.max_calls if evaluator else 0,
            "video_playback_fps": 60,
            "interpretation": "Raw-RAM exploration; not an object-adapter or learning benchmark",
        }
        write_json(out / "manifest.json", {**manifest, "manifest_hash": digest(manifest)})
        if video:
            writer = imageio.get_writer(
                out / "replay.mp4", fps=60, codec="libx264", macro_block_size=1
            )
        rng = random.Random(seed)
        history = deque(maxlen=4)
        last_action, last_reward = None, 0.0
        actor = ActionPolicy(evaluator, program) if evaluator else None
        with (
            (out / "transitions.jsonl").open("w") as log,
            (out / "frames.jsonl").open("w") as frame_log,
        ):
            while summary["raw_frames"] < frames:
                count = min(hold, frames - summary["raw_frames"])
                history.append({"raw_frame": summary["raw_frames"], "ram_bytes": ram.tolist()})
                observation = {
                    "schema_version": "atari-ram-v1",
                    "game": game["env_id"],
                    "ram_bytes": ram.tolist(),
                    "raw_frame": summary["raw_frames"],
                    "lives": int(info.get("lives", 0)),
                    "last_reward": last_reward,
                    "last_requested_action_id": last_action,
                    "sticky_action_probability": sticky,
                    "history": list(history),
                    "candidate_actions": [
                        {"id": i, "ale_meaning": name, "hold_raw_frames": count}
                        for i, name in enumerate(names)
                    ],
                }
                action, prediction = (
                    actor.choose(observation) if actor else (rng.randrange(len(names)), None)
                )
                if type(action) is not int or not 0 <= action < len(names):
                    raise ValueError("Policy returned an invalid action")
                rewards = []
                for _ in range(count):
                    ram, reward, terminated, truncated, info = env.step(action)
                    rewards.append(float(reward))
                    summary["raw_frames"] += 1
                    summary["reward"] += float(reward)
                    summary.update(terminated=terminated, truncated=truncated)
                    frame_log.write(
                        json.dumps(
                            {
                                "decision": summary["decisions"],
                                "raw_frame": summary["raw_frames"],
                                "requested_action_id": action,
                                "ram_bytes": ram.tolist(),
                                "rgb_sha256": hashlib.sha256(
                                    env.unwrapped.ale.getScreenRGB().tobytes()
                                ).hexdigest(),
                                "reward": float(reward),
                                "terminated": terminated,
                                "truncated": truncated,
                            }
                        )
                        + "\n"
                    )
                    if writer:
                        writer.append_data(env.unwrapped.ale.getScreenRGB())
                    if terminated or truncated:
                        break
                row = {
                    "decision": summary["decisions"],
                    "observation": observation,
                    "action": action,
                    "prediction": prediction,
                    "rewards": rewards,
                    "raw_frames": len(rewards),
                    "next_ram_bytes": ram.tolist(),
                    "terminated": terminated,
                    "truncated": truncated,
                }
                log.write(json.dumps(row, allow_nan=False) + "\n")
                log.flush()
                frame_log.flush()
                summary["decisions"] += 1
                last_action, last_reward = action, sum(rewards)
                if terminated or truncated:
                    break
        summary["end_reason"] = (
            "native_termination"
            if summary["terminated"]
            else "environment_truncation"
            if summary["truncated"]
            else "frame_limit"
        )
        summary["truncated"] = summary["truncated"] or summary["end_reason"] == "frame_limit"
        summary["status"] = "complete"
        return summary
    finally:
        summary["wall_seconds"] = time.monotonic() - started
        if evaluator:
            ledger = evaluator.ledger[ledger_start:]
            summary["api_attempts"] = len(ledger)
            write_json(out / "api-ledger.json", ledger)
        write_json(out / "summary.json", summary)
        if writer:
            writer.close()
        if env is not None:
            env.close()
