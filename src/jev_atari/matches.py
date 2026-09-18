"""Native-match attempts with explicit censoring and bounded, shared API costs."""

from collections import Counter
from pathlib import Path
from statistics import mean, stdev

from jev_atari.choice import ActionProgram
from jev_atari.controls import PinnedActionPolicy
from jev_atari.experiment import play, split_for_seed
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.policies import HeuristicPolicy, InterceptPolicy, RandomPolicy


def match_result(summary: dict, max_frames: int) -> dict:
    native = (
        summary["status"] == "complete"
        and summary["end_reason"] == "native_termination"
        and summary["terminated"]
        and max(summary["points_scored"], summary["points_lost"]) == 21
        and summary["points_scored"] != summary["points_lost"]
    )
    capped = (
        summary["status"] == "complete"
        and summary["end_reason"] == "decision_limit"
        and not summary["terminated"]
        and summary["raw_frames"] == max_frames
    )
    valid = 0 < summary["raw_frames"] <= max_frames
    native, capped = native and valid, capped and valid
    return {
        "evaluation_complete": native or capped,
        "native_match_complete": native,
        "censored": not native,
        "outcome": ("win" if summary["reward"] > 0 else "loss") if native else "unfinished",
        "capped_episode_return": summary["reward"] if native or capped else None,
        "full_match_return": summary["reward"] if native else None,
    }


def aggregate_matches(episodes: list[dict], scheduled: int) -> dict:
    valid = [e["capped_episode_return"] for e in episodes if e["evaluation_complete"]]
    full = [e["full_match_return"] for e in episodes if e["native_match_complete"]]
    wins = sum(e["outcome"] == "win" for e in episodes)
    losses = sum(e["outcome"] == "loss" for e in episodes)
    return {
        "scheduled_episodes": scheduled,
        "recorded_episodes": len(episodes),
        "evaluated_episodes": len(valid),
        "native_matches": len(full),
        "wins": wins,
        "losses": losses,
        "unfinished_or_unstarted": scheduled - len(full),
        "completion_rate": len(full) / scheduled,
        "win_rate_completed_matches": wins / len(full) if full else None,
        "win_fraction_all_scheduled": wins / scheduled,
        "possible_win_fraction_bounds": [wins / scheduled, (scheduled - losses) / scheduled],
        "mean_capped_return": mean(valid) if valid else None,
        "sample_sd_capped_return": stdev(valid) if len(valid) > 1 else None,
        "mean_completed_match_return": mean(full) if full else None,
        "end_reasons": dict(Counter(e["end_reason"] for e in episodes)),
        "interpretation": "Capped-return mean includes frame-capped episodes but excludes errors. "
        "Denominators are explicit. Completed-match means and win rates may be "
        "selection-biased when completion is low. Bounds treat every unfinished/unstarted match "
        "as an unknown win or loss, not a draw. No confidence interval from this small pilot.",
    }


def run_matches(
    protocol,
    *,
    arms: list[str],
    seeds: list[int],
    split: str,
    max_frames: int,
    out: Path,
    evaluator=None,
    program: ActionProgram | None = None,
    video: bool = False,
    source_revision: str | None = None,
    on_episode=None,
) -> dict:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be nonempty and unique")
    if split not in {"train", "development"} or any(split_for_seed(s) != split for s in seeds):
        raise ValueError("Use a single declared train/development split; final test stays reserved")
    if (
        not arms
        or len(set(arms)) != len(arms)
        or set(arms) - {"random", "track-4px", "intercept", "jev"}
    ):
        raise ValueError("Use unique known match arms")
    if type(max_frames) is not int or max_frames < 1 or max_frames % protocol.hold_frames:
        raise ValueError("max_frames must be a positive multiple of hold_frames")
    live = "jev" in arms
    if live:
        if (
            evaluator is None
            or program is None
            or evaluator.backend != "jev"
            or evaluator.api.budget.used
            or evaluator.ledger
        ):
            raise ValueError("Jev matches require a frozen program and a fresh shared evaluator")
    elif evaluator is not None or program is not None:
        raise ValueError("Local-only runs must not have a model or question program")
    new_directory(out)
    schedule = [
        {"seed": seed, "arm": arm}
        for i, seed in enumerate(seeds)
        for arm in (arms if i % 2 == 0 else list(reversed(arms)))
    ]
    plan = {
        "kind": "pong-match-plan-v1",
        "source_revision": source_revision,
        "protocol": protocol.manifest(),
        "split": split,
        "seeds": seeds,
        "arms": arms,
        "schedule": schedule,
        "max_frames_per_episode": max_frames,
        "max_decisions_per_episode": max_frames // protocol.hold_frames,
        "point_limit": None,
        "program": program.to_dict() if program else None,
        "program_hash": program.hash if program else None,
        "model": evaluator.model if live else None,
        "max_http_attempts": evaluator.api.budget.max_calls if live else 0,
        "max_decision_calls": len(seeds) * (max_frames // protocol.hold_frames) if live else 0,
        "local_policies": {
            "random": "Uniform over all six legal actions; fresh RNG seeded by episode seed.",
            "track-4px": HeuristicPolicy(4).name,
            "intercept": {"name": InterceptPolicy.name, "deadband": 4, "top": 34, "bottom": 194},
        },
        "stop_rule": "Native termination or frame cap. Errors stop the suite; no automatic "
        "restart, action fallback, absorbing tail, or extra budget. Retain partial evidence.",
        "primary_metric": "Undiscounted episode return through native termination or frame cap; "
        "report full-match completion and win denominators separately.",
        "inference_rule": "One realization per arm/seed; no teacher update or promotion. "
        "All six actions and the observation/decoder contracts remain unchanged.",
    }
    write_json(out / "plan.json", plan)
    report = {
        "kind": "pong-match-suite-v1",
        "status": "incomplete",
        "plan_hash": digest(plan),
        "episodes": [],
    }
    write_json(out / "results.json", report)
    try:
        for item in schedule:
            arm, seed = item["arm"], item["seed"]
            report["active_episode"] = item
            write_json(out / "results.json", report)
            path = out / arm / f"seed-{seed}"
            policies = {
                "random": lambda seed=seed: RandomPolicy(seed),
                "track-4px": lambda: HeuristicPolicy(4),
                "intercept": InterceptPolicy,
                "jev": lambda: PinnedActionPolicy(evaluator, program),
            }
            if evaluator:
                evaluator.api.trace_path = path / "model-exchanges.jsonl" if arm == "jev" else None
            summary = play(
                protocol,
                policies[arm](),
                seed=seed,
                decisions=max_frames // protocol.hold_frames,
                point_limit=None,
                out=path,
                video=video,
                evaluator=evaluator if arm == "jev" else None,
            )
            row = {**item, **summary, **match_result(summary, max_frames)}
            report["episodes"].append(row)
            write_json(path / "evaluation.json", row)
            if not row["evaluation_complete"]:
                raise ValueError("Unexpected environment termination/truncation")
            if on_episode:
                on_episode(row)
        report.pop("active_episode", None)
        report["status"] = "complete"
        return report
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        item = report.get("active_episode")
        if item:
            path = out / item["arm"] / f"seed-{item['seed']}" / "summary.json"
            if path.exists() and item not in [
                {k: e[k] for k in ("arm", "seed")} for e in report["episodes"]
            ]:
                summary = read_json(path)
                report["episodes"].append({**item, **summary, **match_result(summary, max_frames)})
        raise
    finally:
        report["aggregates"] = {
            arm: aggregate_matches([e for e in report["episodes"] if e["arm"] == arm], len(seeds))
            for arm in arms
        }
        ledger = evaluator.ledger if evaluator else []
        report["api_attempts"] = evaluator.api.budget.used if evaluator else 0
        report["http_status_counts"] = dict(Counter(str(e["status"]) for e in ledger))
        report["http_wall_seconds"] = sum(e["elapsed_seconds"] for e in ledger)
        report["usage"] = {
            k: sum(e.get("usage", {}).get(k, 0) for e in ledger)
            for k in ("input_tokens", "output_tokens")
        }
        write_json(out / "api-ledger.json", ledger)
        write_json(out / "results.json", report)
