"""Bounded online policy trials and train-only trajectory feedback."""

import json
from pathlib import Path

from jev_atari.experiment import play, split_for_seed
from jev_atari.io import digest, new_directory, read_json, write_json


class ReplayPrefixEvaluator:
    """Replay verified predictions from an interrupted first episode, then call live."""

    def __init__(self, evaluator, path: Path):
        self.evaluator = evaluator
        self.rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.replayed = 0
        self.backend, self.model = evaluator.backend, evaluator.model

    def evaluate(self, observation, program):
        if self.replayed >= len(self.rows):
            return self.evaluator.evaluate(observation, program)
        row = self.rows[self.replayed]
        prediction = row["prediction"]
        if (
            digest(row["observation"]) != digest(observation)
            or prediction["program_hash"] != program.hash
        ):
            raise ValueError("Replay prefix observation or program differs")
        if prediction["requested_model"] != self.model or prediction["backend"] != self.backend:
            raise ValueError("Replay prefix model or backend differs")
        if prediction["response_model"] != self.model:
            raise ValueError("Replay requires a pinned matching response model")
        if (
            prediction.get("prediction_type") != "action-choice"
            or row["action"] != prediction["chosen_action"]
        ):
            raise ValueError("Replay prefix is not a matching action prediction")
        probabilities = {int(k): v for k, v in prediction["action_probabilities"].items()}
        if probabilities[row["action"]] + 1e-12 < max(probabilities.values()):
            raise ValueError("Replay prefix action does not satisfy probability argmax")
        self.replayed += 1
        return {**prediction, "replayed_prefix": True}

    @property
    def ledger(self):
        return self.evaluator.ledger

    def close(self):
        self.evaluator.close()


def run_policy_suite(
    protocol,
    policy,
    *,
    seeds: list[int],
    decisions: int,
    point_limit: int,
    out: Path,
    evaluator=None,
    video: bool = False,
) -> dict:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Suite seeds must be nonempty and unique")
    splits = {split_for_seed(seed) for seed in seeds}
    if len(splits) != 1:
        raise ValueError("A policy suite must belong to one split")
    if type(point_limit) is not int or point_limit < 1 or decisions < 1:
        raise ValueError("Positive decision and point limits are required")
    new_directory(out)
    start = len(evaluator.ledger) if evaluator else 0
    program = policy.program.to_dict() if hasattr(policy, "program") else None
    report = {
        "kind": "online-policy-suite-v1",
        "status": "incomplete",
        "split": splits.pop(),
        "seeds": seeds,
        "protocol": protocol.manifest(),
        "policy": policy.name,
        "selection_rule": getattr(policy, "selection_rule", None),
        "program": program,
        "program_hash": digest(program) if program else None,
        "max_decisions": decisions,
        "point_limit": point_limit,
        "backend": evaluator.backend if evaluator else "local",
        "requested_model": evaluator.model if evaluator else None,
        "episodes": [],
    }
    write_json(out / "suite.json", report)
    try:
        for seed in seeds:
            summary = play(
                protocol,
                policy,
                seed=seed,
                decisions=decisions,
                point_limit=point_limit,
                out=out / f"seed-{seed}",
                evaluator=evaluator,
                video=video,
            )
            report["episodes"].append({"seed": seed, **summary})
            write_json(out / "suite.json", report)
        ledger = evaluator.ledger[start:] if evaluator else []
        models = sorted({row["response_model"] for row in ledger if row.get("response_model")})
        if evaluator and len(models) != 1:
            raise ValueError("Policy suite requires one consistent response model")
        report["response_models"] = models
        report["total_reward"] = sum(e["reward"] for e in report["episodes"])
        report["total_points_scored"] = sum(e["points_scored"] for e in report["episodes"])
        report["total_points_lost"] = sum(e["points_lost"] for e in report["episodes"])
        report["all_reached_point_limit"] = all(
            e["end_reason"] == "point_limit" for e in report["episodes"]
        )
        report["status"] = "complete"
        return report
    finally:
        ledger = evaluator.ledger[start:] if evaluator else []
        report["api_attempts"] = len(ledger)
        report["replayed_predictions"] = getattr(evaluator, "replayed", 0)
        report["usage"] = {
            field: sum(row.get("usage", {}).get(field, 0) for row in ledger)
            for field in ("input_tokens", "output_tokens")
        }
        write_json(out / "suite.json", report)
        write_json(out / "api-ledger.json", ledger)


def trajectory_diagnostics(path: Path) -> dict:
    """Observation-derived control diagnostics; returns are a proxy, not ALE rewards."""
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    last_direction = None
    returns, opposed, visible, disagreements = 0, 0, 0, 0
    for row in rows:
        objects = {o["id"]: o for o in row["observation"]["objects"]}
        ball, player = objects["ball"], objects["player"]
        if ball["bbox"] is not None and player["bbox"] is not None:
            visible += 1
            b, p = ball["bbox"], player["bbox"]
            gap = b[1] + b[3] / 2 - p[1] - p[3] / 2
            opposed += (gap > 4 and row["action"] in (2, 4)) or (
                gap < -4 and row["action"] in (3, 5)
            )
        velocity = ball.get("velocity")
        if ball["bbox"] is None or velocity is None:
            last_direction = None
        elif velocity[0] != 0:
            direction = 1 if velocity[0] > 0 else -1
            if last_direction == 1 and direction == -1 and ball["bbox"][0] >= 120:
                returns += 1
            last_direction = direction
        if any(row["rewards"]):
            last_direction = None
        choice = row.get("prediction", {}).get("choice_answer", {})
        disagreements += choice.get("choice_matches_probabilities") is False
    return {
        "decisions": len(rows),
        "visible_ball_and_player_decisions": visible,
        "requests_opposing_instantaneous_vertical_gap": opposed,
        "estimated_right_paddle_returns": returns,
        "provider_choice_disagreements": disagreements,
        "interpretation": "Returns inferred from positive-to-negative ball vx near the right "
        "paddle; may miss contacts. Opposing instantaneous gap is not always a wrong action.",
    }


def policy_feedback(suite_path: Path) -> dict:
    suite = read_json(suite_path)
    if suite["kind"] != "online-policy-suite-v1" or suite["status"] != "complete":
        raise ValueError("A completed online policy suite is required")
    if suite["split"] != "train" or any(split_for_seed(s) != "train" for s in suite["seeds"]):
        raise ValueError("Policy feedback must come from training only")
    examples = []
    for episode in suite["episodes"]:
        path = suite_path.parent / f"seed-{episode['seed']}" / "transitions.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        losses = [i for i, row in enumerate(rows) if sum(row["rewards"]) < 0]
        gains = [i for i, row in enumerate(rows) if sum(row["rewards"]) > 0]
        for event_index in losses[:2] + gains[:1]:
            indices = sorted({max(0, event_index - lag) for lag in (8, 4, 1, 0)})
            examples.append(
                {
                    "observed_point_reward": sum(rows[event_index]["rewards"]),
                    "context": [rows[i] for i in indices],
                }
            )
    return {
        "kind": "online-policy-feedback-v1",
        "split": "train",
        "suite_hash": digest(suite),
        "program": suite["program"],
        "protocol": suite["protocol"],
        "episode_results": suite["episodes"],
        "examples": examples,
        "instructions": "Propose one general policy guidance revision using these TRAIN "
        "trajectories only. Preserve observations, action options and control duration. "
        "Do not include per-state actions, seed IDs or executable code. Point reward follows "
        "many actions; these contexts do not establish which individual action caused it. "
        "Return an action-choice-program-v1 program with name and guidance.",
    }


def select_policy_candidate(baseline: dict, candidate: dict) -> dict:
    for report in (baseline, candidate):
        if report["kind"] != "online-policy-suite-v1" or report["status"] != "complete":
            raise ValueError("Selection requires completed policy suites")
        if report["split"] != "development":
            raise ValueError("Policy selection requires development only")
    for field in (
        "seeds",
        "protocol",
        "max_decisions",
        "point_limit",
        "backend",
        "requested_model",
        "response_models",
        "selection_rule",
    ):
        if baseline[field] != candidate[field]:
            raise ValueError(f"Incomparable policy suites: {field}")
    pairs = []
    for old, new in zip(baseline["episodes"], candidate["episodes"], strict=True):
        if old["seed"] != new["seed"]:
            raise ValueError("Episode seed order differs")
        pairs.append(
            {
                "seed": old["seed"],
                "baseline_reward": old["reward"],
                "candidate_reward": new["reward"],
                "gain": new["reward"] - old["reward"],
            }
        )
    reasons = []
    if not baseline["all_reached_point_limit"] or not candidate["all_reached_point_limit"]:
        reasons.append("incomplete_point_windows")
    if sum(pair["gain"] for pair in pairs) < 2:
        reasons.append("total_reward_gain_below_two")
    if any(pair["gain"] < 0 for pair in pairs):
        reasons.append("per_seed_reward_regression")
    return {
        "kind": "online-policy-selection-v1",
        "accepted": not reasons,
        "rejection_reasons": reasons,
        "pairs": pairs,
        "selected_program": (baseline if reasons else candidate)["program"],
        "interpretation": "predeclared short-window pilot gate; not statistical significance",
    }
