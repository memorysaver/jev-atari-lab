"""Real environment rollouts, branching datasets, and bounded offline evaluation."""

import json
import time
from collections import Counter, deque
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from jev_atari.environment import Pong, Protocol
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.observation import SCHEMA
from jev_atari.policies import HEURISTIC_VERSION, HeuristicPolicy, RandomPolicy
from jev_atari.program import QuestionProgram


def split_for_seed(seed: int) -> str:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    return "train" if seed % 10 < 6 else "development" if seed % 10 < 8 else "test"


def fingerprint(env: Pong) -> str:
    return digest({"ram": env.ram.tolist(), "observation": env.observation})


def play(
    protocol: Protocol,
    policy,
    *,
    seed: int,
    decisions: int,
    out: Path,
    video: bool = False,
    evaluator=None,
    point_limit: int | None = None,
) -> dict:
    if decisions < 1:
        raise ValueError("decisions must be positive")
    if point_limit is not None and (type(point_limit) is not int or point_limit < 1):
        raise ValueError("point_limit must be a positive integer")
    ledger_start = len(evaluator.ledger) if evaluator else 0
    new_directory(out)
    manifest = {
        "kind": "pong-play-v1",
        "protocol": protocol.manifest(),
        "seed": seed,
        "split": split_for_seed(seed),
        "policy": policy.name,
        "max_decisions": decisions,
        "point_limit": point_limit,
        "video_clock": "simulation, 60 raw frames/second",
    }
    if hasattr(policy, "program"):
        manifest["question_program"] = policy.program.to_dict()
    if evaluator is not None and hasattr(evaluator, "transport_manifest"):
        manifest["model_transport"] = evaluator.transport_manifest
    write_json(out / "manifest.json", manifest)
    summary = {
        "status": "running",
        "reward": 0.0,
        "decisions": 0,
        "raw_frames": 0,
        "points_scored": 0,
        "points_lost": 0,
        "terminated": False,
        "truncated": False,
        "backend": getattr(evaluator, "backend", "local"),
        "end_reason": None,
    }
    start = time.monotonic()
    writer = None
    try:
        with (
            Pong(protocol) as env,
            (out / "transitions.jsonl").open("w") as log,
            (out / "frames.jsonl").open("w") as frame_log,
        ):
            obs = env.reset(seed)
            summary["reset_frames"] = env.reset_frames
            if video:
                writer = imageio.get_writer(
                    out / "replay.mp4",
                    fps=60,
                    codec="libx264",
                    macro_block_size=1,
                    ffmpeg_log_level="error",
                )
            for index in range(decisions):
                frame_before = env.raw_frames
                action, prediction = policy.choose(deepcopy(obs))
                if env.raw_frames != frame_before:
                    raise RuntimeError("Policy advanced the emulator during inference")
                final_point_pending = point_limit is not None and (
                    summary["points_scored"] + summary["points_lost"] == point_limit - 1
                )
                transition = env.step(
                    action, capture=video, stop_on_point=final_point_pending, trace=True
                )
                for frame in transition.raw_states:
                    frame_log.write(json.dumps({"decision": index, **frame}) + "\n")
                frame_log.flush()
                for frame in transition.rgb_frames:
                    writer.append_data(frame)
                points = summary["points_scored"] + summary["points_lost"]
                points += sum(r != 0 for r in transition.rewards)
                point_cutoff = point_limit is not None and points >= point_limit
                cutoff = (index + 1 == decisions or point_cutoff) and not transition.terminated
                row = {
                    "decision": index,
                    "observation": obs,
                    "action": action,
                    "prediction": prediction,
                    "rewards": transition.rewards,
                    "raw_frames": transition.raw_frames,
                    "next_observation": transition.observation,
                    "terminated": transition.terminated,
                    "truncated": transition.truncated or cutoff,
                }
                log.write(json.dumps(row, allow_nan=False) + "\n")
                log.flush()
                summary["reward"] += transition.reward
                summary["decisions"] += 1
                summary["raw_frames"] += transition.raw_frames
                summary["points_scored"] += sum(r > 0 for r in transition.rewards)
                summary["points_lost"] += sum(r < 0 for r in transition.rewards)
                summary["terminated"] = transition.terminated
                summary["truncated"] = transition.truncated or cutoff
                obs = transition.observation
                if transition.terminated:
                    summary["end_reason"] = "native_termination"
                elif transition.truncated:
                    summary["end_reason"] = "environment_truncation"
                elif point_cutoff:
                    summary["end_reason"] = "point_limit"
                elif cutoff:
                    summary["end_reason"] = "decision_limit"
                if transition.terminated or transition.truncated or point_cutoff:
                    break
            imageio.imwrite(out / "last-frame.png", env.rgb)
            summary["status"] = "complete"
    except Exception as exc:
        summary["status"] = "incomplete"
        summary["error_type"] = type(exc).__name__
        summary["end_reason"] = "error"
        raise
    finally:
        if writer:
            writer.close()
        summary["wall_seconds"] = time.monotonic() - start
        summary["simulated_seconds"] = summary["raw_frames"] / 60
        if evaluator:
            ledger = evaluator.ledger[ledger_start:]
            summary["api_attempts"] = len(ledger)
            write_json(out / "api-ledger.json", ledger)
        write_json(out / "summary.json", summary)
    return summary


def branch_outcome(env: Pong, action: int, horizon: int) -> dict:
    """Execute one candidate then the frozen heuristic; stop at FIRST scoring event."""
    policy = HeuristicPolicy()
    elapsed = 0
    tail = deque(maxlen=4)
    while elapsed < horizon:
        t = env.step(
            action,
            frames=min(env.protocol.hold_frames, horizon - elapsed),
            stop_on_point=True,
        )
        elapsed += t.raw_frames
        tail.append(
            {
                "offset_raw_frames": elapsed,
                "objects": t.observation["objects"],
                "requested_action": action,
                "rewards": t.rewards,
            }
        )
        event = next((r for r in t.rewards if r != 0), None)
        if event is not None:
            return {
                "label": 1 if event > 0 else -1,
                "raw_frames": elapsed,
                "censored": False,
                "terminated": t.terminated,
                "truncated": t.truncated,
                "observed_tail": list(tail),
            }
        if t.terminated or t.truncated:
            return {
                "label": None,
                "raw_frames": elapsed,
                "censored": True,
                "terminated": t.terminated,
                "truncated": t.truncated,
                "observed_tail": list(tail),
            }
        action, _ = policy.choose(t.observation)
    return {
        "label": 0,
        "raw_frames": elapsed,
        "censored": False,
        "terminated": False,
        "truncated": False,
        "observed_tail": list(tail),
    }


def collect(
    protocol: Protocol,
    *,
    seeds: list[int],
    split: str,
    roots_per_seed: int,
    warmup: int,
    stride: int,
    horizon: int,
    out: Path,
    behavior: str = "mixed",
) -> dict:
    if len(seeds) != len(set(seeds)) or not seeds or any(split_for_seed(s) != split for s in seeds):
        raise ValueError("Seeds must be unique and belong to the requested split (see README)")
    if roots_per_seed < 1 or warmup < 0 or stride < 1 or not 4 <= horizon <= 3600:
        raise ValueError("Invalid root count, warmup, stride or horizon")
    if behavior not in {"mixed", "heuristic", "random"}:
        raise ValueError("Unknown collection behavior")
    new_directory(out)
    manifest = {
        "kind": "pong-branch-dataset-v1",
        "protocol": protocol.manifest(),
        "split": split,
        "seeds": seeds,
        "horizon_frames": horizon,
        "continuation_policy": HEURISTIC_VERSION,
        "roots_per_seed": roots_per_seed,
        "warmup_decisions": warmup,
        "stride": stride,
        "behavior": {
            "mixed": "alternating heuristic and seeded random decisions",
            "heuristic": HEURISTIC_VERSION,
            "random": "seeded uniform random decisions",
        }[behavior],
        "status": "running",
        "root_raw_frames": 0,
        "branch_raw_frames": 0,
    }
    write_json(out / "manifest.json", manifest)
    roots = []
    seen = set()
    try:
        with Pong(protocol) as env:
            for seed in seeds:
                obs = env.reset(seed)
                manifest["root_raw_frames"] += env.reset_frames
                heuristic, random = HeuristicPolicy(), RandomPolicy(seed)
                found = 0
                max_walk = warmup + stride * (roots_per_seed + 100)
                for decision in range(max_walk):
                    if decision >= warmup and (decision - warmup) % stride == 0:
                        fp = fingerprint(env)
                        if fp not in seen:
                            seen.add(fp)
                            snapshot = env.snapshot()
                            outcomes = {}
                            try:
                                for action in range(6):
                                    env.restore(snapshot)
                                    outcome = branch_outcome(env, action, horizon)
                                    manifest["branch_raw_frames"] += outcome["raw_frames"]
                                    outcomes[str(action)] = outcome
                            finally:
                                env.restore(snapshot)
                            root = {
                                "root_id": digest(
                                    [manifest["protocol"]["protocol_hash"], seed, decision]
                                ),
                                "root_fingerprint": fp,
                                "seed": seed,
                                "decision": decision,
                                "observation": deepcopy(obs),
                                "outcomes": outcomes,
                            }
                            roots.append(root)
                            found += 1
                            if found >= roots_per_seed:
                                break
                    policy = (
                        heuristic
                        if behavior == "heuristic" or (behavior == "mixed" and decision % 2 == 0)
                        else random
                    )
                    action, _ = policy.choose(obs)
                    transition = env.step(action)
                    manifest["root_raw_frames"] += transition.raw_frames
                    obs = transition.observation
                    if transition.terminated or transition.truncated:
                        break
                if found != roots_per_seed:
                    raise RuntimeError(
                        "Episode ended before the requested unique roots were collected"
                    )
        manifest["status"] = "complete"
    finally:
        manifest["root_count"] = len(roots)
        manifest["total_raw_frames"] = manifest["root_raw_frames"] + manifest["branch_raw_frames"]
        manifest["dataset_hash"] = digest({"manifest": manifest, "roots": roots})
        write_json(out / "manifest.json", manifest)
        write_json(out / "dataset.json", {"manifest": manifest, "roots": roots})
        write_json(out / "coverage.json", dataset_coverage({"manifest": manifest, "roots": roots}))
    return manifest


def dataset_coverage(data: dict) -> dict:
    """Describe observed labels without treating correlated branches as episodes."""
    labels = Counter()
    informative = 0
    censored = 0
    for root in data["roots"]:
        observed = []
        for outcome in root["outcomes"].values():
            if outcome["censored"]:
                censored += 1
            else:
                observed.append(outcome["label"])
        labels.update(observed)
        informative += len(set(observed)) > 1
    return {
        "split": data["manifest"]["split"],
        "roots": len(data["roots"]),
        "seeds": sorted({root["seed"] for root in data["roots"]}),
        "labels": {str(label): labels[label] for label in (-1, 0, 1)},
        "censored_branches": censored,
        "roots_with_action_difference": informative,
        "missing_labels": [label for label in (-1, 0, 1) if not labels[label]],
        "interpretation": "paired single-sample branches; coverage is not model performance",
    }


def load_dataset(path: Path) -> dict:
    data = read_json(path)
    m = data["manifest"]
    if m["kind"] != "pong-branch-dataset-v1" or m["status"] != "complete" or not data["roots"]:
        raise ValueError("Expected a complete, nonempty real branch dataset")
    if m["continuation_policy"] != HEURISTIC_VERSION:
        raise ValueError("Unsupported continuation policy")
    unhashed = {k: v for k, v in m.items() if k != "dataset_hash"}
    if digest({"manifest": unhashed, "roots": data["roots"]}) != m["dataset_hash"]:
        raise ValueError("Dataset integrity hash mismatch")
    for root in data["roots"]:
        if split_for_seed(root["seed"]) != m["split"]:
            raise ValueError("Dataset seed/split mismatch")
        if root["observation"]["schema_version"] != SCHEMA:
            raise ValueError("Unknown observation schema")
        if set(root["outcomes"]) != {str(i) for i in range(6)}:
            raise ValueError("All six candidate outcomes are required")
    return data


def require_disjoint(train: dict, development: dict) -> None:
    if train["manifest"]["split"] != "train" or development["manifest"]["split"] != "development":
        raise ValueError("Learning requires train and development data, never final-test data")
    for field in ("protocol", "horizon_frames", "continuation_policy"):
        if train["manifest"][field] != development["manifest"][field]:
            raise ValueError(f"Train/development {field} mismatch")
    for field in ("seed", "root_id", "root_fingerprint"):
        if {x[field] for x in train["roots"]} & {x[field] for x in development["roots"]}:
            raise ValueError(f"Train/development overlap: {field}")


def evaluate(data: dict, program: QuestionProgram, evaluator, *, on_row=None) -> dict:
    if program.horizon_frames != data["manifest"]["horizon_frames"]:
        raise ValueError("Question and dataset horizons must match")
    rows, briers, absolute_errors, regrets = [], [], [], []
    informative_regrets, heuristic_regrets = [], []
    response_models = set()
    for root in data["roots"]:
        prediction = evaluator.evaluate(root["observation"], program)
        response_models.add(prediction["response_model"])
        labels = {}
        root_brier, root_errors = [], []
        for action, outcome in root["outcomes"].items():
            if outcome["censored"]:
                continue
            label = outcome["label"]
            if type(label) is not int or label not in {-1, 0, 1}:
                raise ValueError("Invalid observed outcome")
            labels[int(action)] = label
            answer = prediction["answers"][int(action)]
            brier = sum(
                (p - int(i == label + 1)) ** 2 for i, p in enumerate(answer["probabilities"])
            )
            root_brier.append(brier)
            root_errors.append(abs(answer["q"] - label))
        if not labels:
            raise ValueError("Root has no uncensored labels")
        briers.append(float(np.mean(root_brier)))
        absolute_errors.append(float(np.mean(root_errors)))
        chosen = max(range(6), key=lambda a: prediction["answers"][a]["q"])
        if len(labels) == 6:
            regret = max(labels.values()) - labels[chosen]
            regrets.append(regret)
            heuristic_action, _ = HeuristicPolicy().choose(root["observation"])
            heuristic_regrets.append(max(labels.values()) - labels[heuristic_action])
            if len(set(labels.values())) > 1:
                informative_regrets.append(regret)
        rows.append(
            {
                "root_id": root["root_id"],
                "root_fingerprint": root["root_fingerprint"],
                "chosen_action": chosen,
                "prediction": prediction,
                "brier": briers[-1],
                "mae": absolute_errors[-1],
            }
        )
        if on_row is not None:
            on_row(rows[-1])
    if len(response_models) != 1:
        raise ValueError("Model version changed during evaluation; rerun with a pinned model")
    return {
        "kind": "question-evaluation-v1",
        "backend": evaluator.backend,
        "requested_model": evaluator.model,
        "response_models": list(response_models),
        "dataset_hash": data["manifest"]["dataset_hash"],
        "split": data["manifest"]["split"],
        "protocol_hash": data["manifest"]["protocol"]["protocol_hash"],
        "program_hash": program.hash,
        "program": program.to_dict(),
        "coverage": dataset_coverage(data),
        "metrics": {
            "roots": len(rows),
            "brier": float(np.mean(briers)),
            "mae": float(np.mean(absolute_errors)),
            "sampled_regret": float(np.mean(regrets)) if regrets else None,
            "informative_roots": len(informative_regrets),
            "informative_sampled_regret": (
                float(np.mean(informative_regrets)) if informative_regrets else None
            ),
            "heuristic_sampled_regret": (
                float(np.mean(heuristic_regrets)) if heuristic_regrets else None
            ),
        },
        "rows": rows,
        "interpretation": "synthetic plumbing only"
        if evaluator.backend == "mock"
        else "offline finite-horizon heuristic-continuation prediction; not online improvement",
    }


def evaluate_actions(data: dict, program, evaluator, *, on_row=None) -> dict:
    """Measure a direct actor against observed branches without inventing critic scores."""
    rows, regrets, informative, heuristic_regrets = [], [], [], []
    models = set()
    for root in data["roots"]:
        labels = {
            int(action): outcome["label"]
            for action, outcome in root["outcomes"].items()
            if not outcome["censored"]
        }
        if any(type(label) is not int or label not in {-1, 0, 1} for label in labels.values()):
            raise ValueError("Invalid observed outcome")
        prediction = evaluator.evaluate(root["observation"], program)
        models.add(prediction["response_model"])
        chosen = prediction["chosen_action"]
        if type(chosen) is not int or chosen not in range(6):
            raise ValueError("Invalid chosen action")
        regret = None
        if len(labels) == 6:
            regret = max(labels.values()) - labels[chosen]
            regrets.append(regret)
            if len(set(labels.values())) > 1:
                informative.append(regret)
            heuristic_action, _ = HeuristicPolicy().choose(root["observation"])
            heuristic_regrets.append(max(labels.values()) - labels[heuristic_action])
        rows.append(
            {
                "root_id": root["root_id"],
                "root_fingerprint": root["root_fingerprint"],
                "chosen_action": chosen,
                "observed_label": labels.get(chosen),
                "sampled_regret": regret,
                "prediction": prediction,
            }
        )
        if on_row is not None:
            on_row(rows[-1])
    if len(models) != 1:
        raise ValueError("Model version changed during evaluation; use a pinned model")
    return {
        "kind": "action-evaluation-v1",
        "backend": evaluator.backend,
        "requested_model": evaluator.model,
        "response_models": list(models),
        "dataset_hash": data["manifest"]["dataset_hash"],
        "split": data["manifest"]["split"],
        "protocol_hash": data["manifest"]["protocol"]["protocol_hash"],
        "label_horizon_frames": data["manifest"]["horizon_frames"],
        "program_hash": program.hash,
        "program": program.to_dict(),
        "coverage": dataset_coverage(data),
        "metrics": {
            "roots": len(rows),
            "complete_roots": len(regrets),
            "sampled_regret": float(np.mean(regrets)) if regrets else None,
            "informative_roots": len(informative),
            "informative_sampled_regret": float(np.mean(informative)) if informative else None,
            "heuristic_sampled_regret": (
                float(np.mean(heuristic_regrets)) if heuristic_regrets else None
            ),
        },
        "rows": rows,
        "interpretation": "action preferences are not Q values; regret uses a single observed "
        "branch with heuristic continuation, not an online episode",
    }


def doctor(protocol: Protocol) -> dict:
    """A real emulator smoke test, including stochastic replay and action direction."""
    with Pong(protocol) as env:
        env.reset(7)
        policy = HeuristicPolicy()
        for _ in range(100):
            env.step(policy.choose(env.observation)[0])
        snapshot = env.snapshot()
        results = []
        for _ in range(2):
            env.restore(snapshot)
            trace = []
            for action in [0, 2, 3, 4, 5, 1] * 4:
                t = env.step(action)
                trace.append(
                    digest(
                        {
                            "obs": t.observation,
                            "rewards": t.rewards,
                            "terminated": t.terminated,
                            "truncated": t.truncated,
                            "rgb": env.rgb.tolist(),
                            "ram": env.ram.tolist(),
                        }
                    )
                )
            results.append(trace)
        if results[0] != results[1]:
            raise RuntimeError("Full observation/reward/RGB/RAM restore replay differs")
    # Independent zero-sticky probes verify the mapped movement directions.
    directions = {}
    with Pong(Protocol(**{**asdict(protocol), "sticky": 0, "noop_max": 0})) as env:
        for action in (2, 3):
            obs = env.reset(0)
            before = next(o["bbox"][1] for o in obs["objects"] if o["id"] == "player")
            t = env.step(action)
            after = next(o["bbox"][1] for o in t.observation["objects"] if o["id"] == "player")
            directions[str(action)] = after - before
    if not (directions["2"] < 0 < directions["3"]):
        raise RuntimeError("Pong action semantics differ from the documented aliases")
    return {
        "protocol": protocol.manifest(),
        "replay_identical": True,
        "action_y_displacements": directions,
        "model_calls": 0,
    }
