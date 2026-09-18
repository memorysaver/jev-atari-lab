"""Fixed-frame, paired Pong controls with one shared HTTP-attempt budget."""

import json
from collections import Counter
from pathlib import Path

from jev_atari.choice import ActionPolicy, ActionProgram
from jev_atari.experiment import play, split_for_seed
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.models import ModelError
from jev_atari.online import trajectory_diagnostics
from jev_atari.policies import HeuristicPolicy


class PinnedActionPolicy(ActionPolicy):
    def choose(self, observation):
        action, prediction = super().choose(observation)
        if prediction["response_model"] != self.evaluator.model:
            raise ModelError("Response model changed; refusing to execute its action")
        return action, prediction


def horizon_result(summary: dict, frames: int) -> dict:
    """Only native termination earns a conceptual zero-reward absorbing tail."""
    actual = summary["raw_frames"]
    terminal = summary["end_reason"] == "native_termination" and summary["terminated"]
    reached = summary["end_reason"] == "decision_limit" and actual == frames
    complete = summary["status"] == "complete" and 0 < actual <= frames and (terminal or reached)
    return {
        "evaluation_complete": complete,
        "evaluation_horizon_frames": frames,
        "absorbing_tail_frames": frames - actual if complete and terminal else 0,
        "evaluation_reward": summary["reward"] if complete else None,
    }


def rule_agreement(path: Path) -> dict:
    rule = HeuristicPolicy(4)
    count, different, first = 0, 0, []
    for line in path.read_text().splitlines():
        row = json.loads(line)
        expected, _ = rule.choose(row["observation"])
        count += 1
        if row["action"] != expected:
            different += 1
            if len(first) < 10:
                first.append(
                    {"decision": row["decision"], "actual": row["action"], "rule": expected}
                )
    return {
        "decisions": count,
        "different_actions": different,
        "agreement_fraction": (count - different) / count if count else None,
        "first_differences": first,
        "interpretation": "Compared on this policy's visited states, not paired state indices. "
        "Rule agreement measures instruction execution, not optimal gameplay.",
    }


def run_control_comparison(
    protocol,
    *,
    baseline: ActionProgram,
    candidate: ActionProgram,
    seeds: list[int],
    frames: int,
    evaluator,
    out: Path,
    video: bool = False,
    source_revision: str | None = None,
    on_episode=None,
) -> dict:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be nonempty and unique")
    if any(split_for_seed(seed) != "development" for seed in seeds):
        raise ValueError("Control comparison requires development seeds only")
    if type(frames) is not int or frames < 1 or frames % protocol.hold_frames:
        raise ValueError("frames must be a positive multiple of hold_frames")
    if evaluator.backend != "jev" or evaluator.api.budget.used or evaluator.ledger:
        raise ValueError("Comparison requires a fresh Jev evaluator and shared budget")
    new_directory(out)
    policies = {
        "python-2px": HeuristicPolicy(2),
        "python-4px": HeuristicPolicy(4),
        "jev-original": PinnedActionPolicy(evaluator, baseline),
        "jev-vertical": PinnedActionPolicy(evaluator, candidate),
    }
    schedule = []
    for index, seed in enumerate(seeds):
        jev_order = ["jev-original", "jev-vertical"]
        if index % 2:
            jev_order.reverse()
        schedule.extend(
            {"seed": seed, "arm": arm} for arm in ["python-2px", "python-4px", *jev_order]
        )
    plan = {
        "kind": "pong-control-plan-v1",
        "source_revision": source_revision,
        "split": "development",
        "seeds": seeds,
        "protocol": protocol.manifest(),
        "frames_per_episode": frames,
        "max_decisions": frames // protocol.hold_frames,
        "point_limit": None,
        "requested_model": evaluator.model,
        "max_http_attempts": evaluator.api.budget.max_calls,
        "max_decision_calls": 2 * len(seeds) * (frames // protocol.hold_frames),
        "schedule": schedule,
        "arms": {
            arm: {
                "policy": policy.name,
                "program": policy.program.to_dict() if hasattr(policy, "program") else None,
                "program_hash": policy.program.hash if hasattr(policy, "program") else None,
                "deadband_pixels": getattr(policy, "deadband_pixels", None),
            }
            for arm, policy in policies.items()
        },
        "selection_rule": ActionPolicy.selection_rule,
        "primary_metric": "undiscounted net reward over the fixed evaluation horizon",
        "termination_rule": "Native terminal has a zero-reward absorbing tail; reset NOOPs "
        "are excluded from the horizon. Errors and environment truncation are incomplete.",
        "inference_rule": "Fresh model calls; no cache, teacher revision, or policy promotion. "
        "Jev order alternates by seed. One API realization per policy/seed.",
    }
    write_json(out / "plan.json", plan)
    report = {
        "kind": "pong-control-comparison-v1",
        "status": "incomplete",
        "plan_hash": digest(plan),
        "episodes": [],
        "interpretation": "Paired development pilot, not a learning curve, independent "
        "test, or statistical significance claim. No automatic policy promotion.",
    }
    write_json(out / "comparison.json", report)
    try:
        for item in schedule:
            arm, seed = item["arm"], item["seed"]
            episode = out / arm / f"seed-{seed}"
            report["active_episode"] = item
            write_json(out / "comparison.json", report)
            live = arm.startswith("jev-")
            evaluator.api.trace_path = episode / "model-exchanges.jsonl" if live else None
            summary = play(
                protocol,
                policies[arm],
                seed=seed,
                decisions=frames // protocol.hold_frames,
                point_limit=None,
                out=episode,
                evaluator=evaluator if live else None,
                video=video,
            )
            ledger = read_json(episode / "api-ledger.json") if live else []
            result = {
                **item,
                **summary,
                **horizon_result(summary, frames),
                "http_wall_seconds": sum(e["elapsed_seconds"] for e in ledger),
                "usage": {
                    field: sum(e.get("usage", {}).get(field, 0) for e in ledger)
                    for field in ("input_tokens", "output_tokens")
                },
                "rule_4px_agreement": rule_agreement(episode / "transitions.jsonl"),
                "diagnostics": trajectory_diagnostics(episode / "transitions.jsonl"),
            }
            write_json(episode / "evaluation.json", result)
            report["episodes"].append(result)
            write_json(out / "comparison.json", report)
            if not result["evaluation_complete"]:
                raise ValueError("Episode did not complete its evaluation horizon")
            if on_episode:
                on_episode(result)
        report.pop("active_episode", None)
        report["totals"] = {}
        for arm in policies:
            rows = [e for e in report["episodes"] if e["arm"] == arm]
            report["totals"][arm] = {
                key: sum(row.get(key, 0) for row in rows)
                for key in (
                    "reward",
                    "points_scored",
                    "points_lost",
                    "raw_frames",
                    "reset_frames",
                    "decisions",
                    "api_attempts",
                    "wall_seconds",
                    "http_wall_seconds",
                    "absorbing_tail_frames",
                )
            }
            report["totals"][arm]["native_terminations"] = sum(e["terminated"] for e in rows)
            report["totals"][arm]["usage"] = {
                field: sum(e["usage"][field] for e in rows)
                for field in ("input_tokens", "output_tokens")
            }
        rewards = {(e["arm"], e["seed"]): e["evaluation_reward"] for e in report["episodes"]}
        report["paired_reward_differences"] = [
            {
                "left": left,
                "right": right,
                "difference": "left minus right",
                "per_seed": [
                    {"seed": seed, "gain": rewards[left, seed] - rewards[right, seed]}
                    for seed in seeds
                ],
            }
            for left, right in (
                ("jev-vertical", "jev-original"),
                ("jev-vertical", "python-4px"),
                ("python-4px", "python-2px"),
            )
        ]
        report["status"] = "complete"
        return report
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        active = report.get("active_episode")
        if active:
            summary_path = out / active["arm"] / f"seed-{active['seed']}" / "summary.json"
            if summary_path.exists():
                summary = read_json(summary_path)
                report["interrupted_episode"] = {
                    **active,
                    **summary,
                    **horizon_result(summary, frames),
                }
        raise
    finally:
        report["api_attempts"] = evaluator.api.budget.used
        report["http_status_counts"] = dict(Counter(str(e["status"]) for e in evaluator.ledger))
        report["http_wall_seconds"] = sum(e["elapsed_seconds"] for e in evaluator.ledger)
        report["usage"] = {
            field: sum(e.get("usage", {}).get(field, 0) for e in evaluator.ledger)
            for field in ("input_tokens", "output_tokens")
        }
        write_json(out / "api-ledger.json", evaluator.ledger)
        write_json(out / "comparison.json", report)
