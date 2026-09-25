"""Freeway objects, explicit local controls, and replayable native episodes.

RAM coordinates/colors adapted from OCAtari 99c874675df6b76a33a80b57776c123fbcd051af.
See THIRD_PARTY_NOTICES.md. No collision detector or optimal-action labels are claimed.
"""

import hashlib
import json
import random
import time
from collections import Counter, deque
from dataclasses import dataclass
from importlib.metadata import version

import ale_py.roms
import imageio.v2 as imageio
import numpy as np

from jev_atari.arcade import make_game
from jev_atari.choice import ActionProgram
from jev_atari.experiment import split_for_seed
from jev_atari.io import new_directory, write_json

NAMES = ("NOOP", "UP", "DOWN")
COLORS = [
    (167, 26, 26),
    (180, 231, 117),
    (105, 105, 15),
    (228, 111, 111),
    (24, 26, 167),
    (162, 98, 33),
    (84, 92, 214),
    (184, 50, 50),
    (135, 183, 84),
    (210, 210, 64),
]
SCHEMA = "freeway-objects-v1"
HOLD = 16
CAP = 9000


class Observer:
    def __init__(self, hold=HOLD):
        self.history = deque(maxlen=3)
        self.hold = hold

    def observe(self, ram, frame, ended=False):
        current = {
            "raw_frame": frame,
            "player": [44, 193 - int(ram[14]), 6, 8],
            "cars": [
                {"lane": i, "bbox": [int(ram[117 - i]) - 3, 27 + 16 * i, 8, 10]} for i in range(10)
            ],
        }
        result = dict(
            schema_version=SCHEMA,
            game="ALE/Freeway-v5",
            **current,
            history=list(self.history),
            ended=ended,
            candidate_actions=[
                {"id": i, "ale_meaning": name, "hold_raw_frames": self.hold}
                for i, name in enumerate(NAMES)
            ],
        )
        self.history.append(current)
        return result


def screen_checks(obs, rgb):
    checks = []
    for name, box, color in [("player", obs["player"], (252, 252, 84))] + [
        (f"car-{c['lane']}", c["bbox"], COLORS[c["lane"]]) for c in obs["cars"]
    ]:
        x, y, w, h = box
        crop = rgb[max(0, y) : min(210, y + h), max(0, x) : min(160, x + w)]
        checks.append(
            {
                "object": name,
                "pixels": int(np.all(crop == color, axis=2).sum()),
                "on_screen": x + w > 0 and x < 160,
            }
        )
    return checks


def literal(obs, rule="predictive"):
    """Declared heuristic and branch, never an optimal action or collision truth."""
    if rule == "up":
        return 1, "always-up"
    if rule not in {"reactive", "predictive", "narrow"}:
        raise ValueError("Unknown local rule")
    px, py, pw, ph = obs["player"]
    hold = obs["candidate_actions"][0]["hold_raw_frames"]
    margin = 2 if rule != "narrow" else 0
    previous = obs["history"][-1] if obs["history"] else None
    threats = []
    for car in obs["cars"]:
        x, y, w, h = car["bbox"]
        # Only wait before entry; standing in a lane is not declared safe.
        if not (py >= y + h and py - hold < y + h and py + ph > y):
            continue
        vx = 0.0
        if rule != "reactive" and previous:
            old = previous["cars"][car["lane"]]["bbox"][0]
            dt = obs["raw_frame"] - previous["raw_frame"]
            dx = (x - old + 80) % 160 - 80
            vx = dx / dt if dt else 0
        entry = max(0, py - (y + h))
        exit_time = min(hold, py + ph - y)
        for t in range(int(entry), int(exit_time) + 1):
            cx = (x + 3 + vx * t) % 160 - 3
            if cx + w + margin > px and cx - margin < px + pw:
                threats.append(vx)
                break
    if threats:
        return 0, "wait-moving" if any(v != 0 for v in threats) else "wait-static-or-unknown"
    return 1, "advance"


@dataclass(frozen=True)
class FreewayProgram(ActionProgram):
    name: str = "freeway-baseline-v1"
    schema_version: str = "freeway-choice-v1"
    guidance: str = (
        "Control the left chicken to earn points by reaching the top across traffic. "
        "Choose UP to advance, NOOP to wait, or DOWN to retreat. Avoid cars and unnecessary "
        "waiting. Use recent car motion to decide whether a gap is opening or closing. "
        "Coordinates are [x,y,width,height]; smaller y is upward. Car lane IDs identify "
        "fixed lanes. Cars wrap horizontally; a large position jump is not high speed. "
        "UP normally decreases player y by about one pixel per raw frame; collision "
        "recovery can override requested movement. After a crossing the chicken returns "
        "to the bottom. Each choice lasts 16 raw frames. Reconsider after that interval."
    )

    def __post_init__(self):
        ActionProgram(name=self.name, guidance=self.guidance)
        if self.schema_version != "freeway-choice-v1":
            raise ValueError("Wrong program schema")
        if self.action_criteria is not None and set(self.action_criteria) != set(NAMES):
            raise ValueError("All three actions must remain available")

    def request(self, observation, model):
        if observation["schema_version"] != SCHEMA:
            raise ValueError("Wrong observation schema")
        return {
            "model": model,
            "state": {"observation": observation},
            "questions": {
                "next_action": {
                    "type": "choice",
                    "instructions": {
                        "question": self.guidance,
                        "read": "observation.player, observation.cars, observation.history, "
                        "observation.raw_frame, observation.candidate_actions",
                        "contract": "Object boxes have bounded pixel-support validation. No safe "
                        "action, collision forecast or rule label is supplied.",
                    },
                    "criteria": self.action_criteria
                    or {
                        "NOOP": "Wait for the next 16 raw frames.",
                        "UP": "Request upward movement for the next 16 raw frames.",
                        "DOWN": "Request downward movement for the next 16 raw frames.",
                    },
                }
            },
        }


def prefix_length(seed):
    return 128 + random.Random(seed).randrange(128)


def play(path, seed, *, rule=None, program=None, evaluator=None, hold=HOLD, source="uncommitted"):
    if (rule is None) == (evaluator is None):
        raise ValueError("Exactly one local or live policy required")
    new_directory(path)
    start = time.monotonic()
    ledger_start = len(evaluator.ledger) if evaluator else 0
    if evaluator:
        evaluator.api.trace_path = path / "model-exchanges.jsonl"
    summary = dict(
        status="incomplete",
        seed=seed,
        frames=0,
        controlled_frames=0,
        decisions=0,
        reward=0.0,
        prefix_reward=0.0,
        terminated=False,
        truncated=False,
        action_histogram={},
        branches={},
    )
    counts, branches = Counter(), Counter()
    observer = Observer(hold)
    rng = random.Random(seed)
    writer = None
    try:
        with make_game("Freeway") as env, (path / "transitions.jsonl").open("x") as log:
            env.reset(seed=seed)
            assert tuple(env.unwrapped.get_action_meanings()) == NAMES
            write_json(
                path / "manifest.json",
                dict(
                    kind="freeway-episode-v1",
                    seed=seed,
                    split=split_for_seed(seed),
                    rule=rule,
                    program=program.to_dict() if program else None,
                    program_hash=program.hash if program else None,
                    source_revision=source,
                    hold=hold,
                    frame_cap=CAP,
                    sticky=0.25,
                    mode=0,
                    difficulty=0,
                    prefix_noops=prefix_length(seed),
                    schema=SCHEMA,
                    fps=60,
                    rom_sha256=hashlib.sha256(
                        ale_py.roms.get_rom_path("freeway").read_bytes()
                    ).hexdigest(),
                    versions={p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
                    transport=evaluator.transport_manifest
                    if evaluator
                    else {"backend": "local", "calls": 0},
                ),
            )
            writer = imageio.get_writer(
                path / "episode.mp4",
                fps=60,
                codec="libx264",
                macro_block_size=1,
                ffmpeg_log_level="error",
            )
            obs = observer.observe(env.unwrapped.ale.getRAM(), 0)
            while summary["frames"] < CAP:
                controlled = summary["frames"] >= prefix_length(seed)
                count = (
                    min(hold, CAP - summary["frames"])
                    if controlled
                    else min(hold, prefix_length(seed) - summary["frames"])
                )
                prediction = None
                if not controlled:
                    action, branch = 0, "prefix"
                elif evaluator:
                    prediction = evaluator.evaluate(obs, program)
                    action, branch = prediction["chosen_action"], "model"
                elif rule == "random":
                    action, branch = rng.randrange(3), "random"
                else:
                    action, branch = literal(obs, rule)
                frames = []
                for _ in range(count):
                    _, reward, terminated, truncated, _ = env.step(action)
                    ram, rgb = env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB()
                    frames.append(
                        dict(
                            ram=ram.tolist(),
                            rgb_hash=hashlib.sha256(rgb.tobytes()).hexdigest(),
                            reward=float(reward),
                            terminated=terminated,
                            truncated=truncated,
                        )
                    )
                    writer.append_data(rgb)
                    summary["frames"] += 1
                    summary["controlled_frames"] += int(controlled)
                    summary["reward" if controlled else "prefix_reward"] += float(reward)
                    if terminated or truncated:
                        break
                nxt = observer.observe(ram, summary["frames"], terminated or truncated)
                log.write(
                    json.dumps(
                        dict(
                            phase="control" if controlled else "prefix",
                            observation=obs,
                            action=action,
                            branch=branch,
                            prediction=prediction,
                            frames=frames,
                            next_observation=nxt,
                            checks=screen_checks(nxt, rgb),
                        )
                    )
                    + "\n"
                )
                log.flush()
                obs = nxt
                if controlled:
                    counts[NAMES[action]] += 1
                    branches[branch] += 1
                    summary["decisions"] += 1
                    if summary["decisions"] % 128 == 0:
                        print(
                            json.dumps(
                                dict(
                                    event="progress",
                                    episode=str(path),
                                    decisions=summary["decisions"],
                                    reward=summary["reward"],
                                )
                            ),
                            flush=True,
                        )
                summary.update(terminated=terminated, truncated=truncated)
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
        ledger = evaluator.ledger[ledger_start:] if evaluator else []
        write_json(path / "api-ledger.json", ledger)
        summary.update(
            wall_seconds=time.monotonic() - start,
            api_attempts=len(ledger),
            reported_cost_usd=sum((r.get("usage") or {}).get("cost", 0) for r in ledger),
            action_histogram=dict(counts),
            branches=dict(branches),
        )
        write_json(path / "summary.json", summary)
    print(
        json.dumps(dict(event="episode-complete", episode=str(path), summary=summary)), flush=True
    )
    return summary
