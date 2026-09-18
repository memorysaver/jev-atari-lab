"""Audit the interrupted no-FIRE study, including its separately budgeted continuation."""

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean

from jev_atari.choice import ActionProgram, validate_choices
from jev_atari.controls import horizon_result, rule_agreement
from jev_atari.io import digest, read_json, write_json
from jev_atari.replay import replay_episode


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def metrics(episodes):
    rows = [row for episode in episodes for row in lines(episode / "transitions.jsonl")]
    confidence = [r["prediction"]["choice_answer"]["confidence"] for r in rows]
    probabilities = [
        sorted(r["prediction"]["action_probabilities"].values(), reverse=True) for r in rows
    ]
    margins = [p[0] - p[1] for p in probabilities]
    counts = Counter(str(r["action"]) for r in rows)
    disagreements = sum(
        rule_agreement(e / "transitions.jsonl")["different_actions"] for e in episodes
    )
    return {
        "decisions": len(rows),
        "action_counts": dict(sorted(counts.items())),
        "noop_fraction": counts["0"] / len(rows),
        "fire_variant_count": sum(counts[str(a)] for a in (1, 4, 5)),
        "rule_agreement_fraction": 1 - disagreements / len(rows),
        "mean_confidence": mean(confidence),
        "confidence_below_0_3": sum(c < 0.3 for c in confidence),
        "confidence_below_0_5": sum(c < 0.5 for c in confidence),
        "mean_top_two_margin": mean(margins),
        "top_two_margin_below_0_1": sum(m < 0.1 - 1e-12 for m in margins),
    }


def audit_run(root, out):
    plan = read_json(root / "plan.json")
    report = read_json(root / "comparison.json")
    assert digest(plan) == report["plan_hash"]
    assert report["api_attempts"] <= plan["max_http_attempts"]
    episodes = list(report["episodes"])
    if report["status"] == "incomplete":
        episodes.append(report["interrupted_episode"])
    assert [{k: e[k] for k in ("seed", "arm")} for e in episodes] == plan["schedule"][
        : len(episodes)
    ]
    if report["status"] == "complete":
        assert len(episodes) == len(plan["schedule"])
    exchanges = []
    checks = []
    for e in episodes:
        episode = root / e["arm"] / f"seed-{e['seed']}"
        manifest = read_json(episode / "manifest.json")
        summary = read_json(episode / "summary.json")
        assert manifest["protocol"] == plan["protocol"]
        assert manifest["seed"] == e["seed"] and manifest["point_limit"] is None
        assert all(e[k] == v for k, v in summary.items())
        assert all(
            e[k] == v for k, v in horizon_result(summary, plan["frames_per_episode"]).items()
        )
        program = ActionProgram.from_dict(plan["arms"][e["arm"]]["program"])
        assert manifest["question_program"] == program.to_dict()
        captured = lines(episode / "model-exchanges.jsonl")
        exchanges.extend(captured)
        assert [x["transport"] for x in captured] == read_json(episode / "api-ledger.json")
        by_id = {x["exchange_id"]: x for x in captured}
        assert len(by_id) == len(captured)
        rows = lines(episode / "transitions.jsonl")
        used = set()
        for row in rows:
            prediction = row["prediction"]
            exchange = by_id[prediction["exchange_id"]]
            used.add(prediction["exchange_id"])
            assert exchange["request"] == program.request(
                row["observation"], plan["requested_model"]
            )
            assert exchange["response"]["model"] == plan["requested_model"]
            assert prediction["program_hash"] == program.hash
            answer = validate_choices(
                exchange["response"], exchange["request"]["questions"], prefer_probabilities=True
            )["next_action"]
            action_ids = {
                a["ale_meaning"]: a["id"] for a in row["observation"]["candidate_actions"]
            }
            assert answer == prediction["choice_answer"]
            assert row["action"] == prediction["chosen_action"] == action_ids[answer["choice"]]
        unused = [x for x in captured if x["exchange_id"] not in used]
        if summary["status"] == "incomplete":
            assert len(unused) == 1 and rows
            assert unused[0]["request"] == program.request(
                rows[-1]["next_observation"], plan["requested_model"]
            )
            assert unused[0]["response"] is None
        else:
            for failed in unused:
                status = failed["transport"]["status"]
                assert failed["response"] is None
                assert status == 429 or isinstance(status, int) and 500 <= status < 600
                following = by_id[failed["exchange_id"] + 1]
                assert failed["request"] == following["request"]
                assert following["transport"]["attempt"] == failed["transport"]["attempt"] + 1
            assert e["rule_4px_agreement"] == rule_agreement(episode / "transitions.jsonl")
        replay = replay_episode(episode, out / e["arm"] / f"seed-{e['seed']}")
        checks.append({"seed": e["seed"], "exchanges": len(captured), "replay": replay})
    assert [x["exchange_id"] for x in exchanges] == list(range(1, report["api_attempts"] + 1))
    assert [x["transport"] for x in exchanges] == read_json(root / "api-ledger.json")
    return {"plan_hash": digest(plan), "comparison_hash": digest(report), "episodes": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Output already exists")
    original = args.source / "pong-no-fire-v3"
    continuation = args.source / "pong-no-fire-v3-continuation"
    a, b = [read_json(r / "comparison.json") for r in (original, continuation)]
    assert a["status"] == "incomplete" and b["status"] == "complete"
    assert [e["seed"] for e in a["episodes"]] == [36, 37]
    assert a["interrupted_episode"]["seed"] == 46
    assert [e["seed"] for e in b["episodes"]] == [46, 47]
    assert a["api_attempts"] + b["api_attempts"] <= 2200
    plans = [read_json(r / "plan.json") for r in (original, continuation)]
    for key in ("protocol", "arms", "requested_model", "frames_per_episode"):
        assert plans[0][key] == plans[1][key]
    reference = read_json(original / "reference.json")
    baseline = read_json(args.baseline / "comparison.json")
    assert digest(baseline) == reference["reference_comparison_hash"]
    checks = [audit_run(r, args.out / r.name) for r in (original, continuation)]
    seeds = [36, 37, 46, 47]
    new_paths = [
        (original if seed in (36, 37) else continuation) / "jev-vertical" / f"seed-{seed}"
        for seed in seeds
    ]
    old_paths = [args.baseline / "jev-vertical" / f"seed-{seed}" for seed in seeds]
    result = {
        "kind": "no-fire-follow-up-audit-v1",
        "status": "verified",
        "audit_api_calls": 0,
        "combined_attempts": a["api_attempts"] + b["api_attempts"],
        "combined_attempt_cap": 2200,
        "http_status_counts": dict(
            Counter(a["http_status_counts"]) + Counter(b["http_status_counts"])
        ),
        "usage": {k: a["usage"][k] + b["usage"][k] for k in a["usage"]},
        "http_wall_seconds": a["http_wall_seconds"] + b["http_wall_seconds"],
        "reference": metrics(old_paths),
        "candidate": metrics(new_paths),
        "selected_complete_episodes": a["episodes"] + b["episodes"],
        "interrupted_prefix": a["interrupted_episode"],
        "checks": checks,
        "interpretation": (
            "Historical baseline, seen development seeds, manual question edit; "
            "no promotion or causal learning claim. Failed prefix excluded from "
            "fixed-horizon scores, included in costs and audit."
        ),
    }
    write_json(args.out / "verification.json", result)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("checks", "selected_complete_episodes", "interrupted_prefix")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
