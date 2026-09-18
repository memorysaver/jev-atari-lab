"""Audit every saved request, decoded action and emulator frame without API calls."""

import argparse
import json
from pathlib import Path

from jev_atari.choice import ActionProgram, validate_choices
from jev_atari.controls import horizon_result, rule_agreement
from jev_atari.io import digest, read_json, write_json
from jev_atari.replay import replay_episode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
root = args.run
if args.out.exists():
    raise ValueError("Output already exists; choose a new directory")
plan = read_json(root / "plan.json")
report = read_json(root / "comparison.json")
assert report["status"] == "complete"
assert report["api_attempts"] <= plan["max_http_attempts"]
assert digest(plan) == report["plan_hash"]
assert [{k: e[k] for k in ("seed", "arm")} for e in report["episodes"]] == plan["schedule"]
all_exchanges = []
checks = []
for e in report["episodes"]:
    episode = root / e["arm"] / f"seed-{e['seed']}"
    manifest = read_json(episode / "manifest.json")
    summary = read_json(episode / "summary.json")
    assert manifest["protocol"] == plan["protocol"]
    assert manifest["point_limit"] is None
    assert manifest["seed"] == e["seed"]
    assert all(e[k] == v for k, v in summary.items())
    assert all(e[k] == v for k, v in horizon_result(summary, plan["frames_per_episode"]).items())
    assert e["evaluation_complete"]
    assert e["rule_4px_agreement"] == rule_agreement(episode / "transitions.jsonl")
    rows = [json.loads(line) for line in (episode / "transitions.jsonl").read_text().splitlines()]
    exchange_count = 0
    if e["arm"].startswith("jev-"):
        program = ActionProgram.from_dict(plan["arms"][e["arm"]]["program"])
        assert manifest["question_program"] == program.to_dict()
        exchanges = [
            json.loads(line)
            for line in (episode / "model-exchanges.jsonl").read_text().splitlines()
        ]
        all_exchanges.extend(exchanges)
        exchange_count = len(exchanges)
        assert [x["transport"] for x in exchanges] == read_json(episode / "api-ledger.json")
        by_id = {x["exchange_id"]: x for x in exchanges}
        assert len(by_id) == len(exchanges)
        for row in rows:
            prediction = row["prediction"]
            exchange = by_id[prediction["exchange_id"]]
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
    replay = replay_episode(episode, args.out / e["arm"] / f"seed-{e['seed']}")
    checks.append(
        {
            "arm": e["arm"],
            "seed": e["seed"],
            "verified_decisions": len(rows),
            "verified_exchanges": exchange_count,
            "replay": replay,
        }
    )
    print(e["arm"], e["seed"], "verified", flush=True)
assert [x["exchange_id"] for x in all_exchanges] == list(range(1, report["api_attempts"] + 1))
assert [x["transport"] for x in all_exchanges] == read_json(root / "api-ledger.json")
audit = {
    "kind": "pong-controls-audit-v1",
    "status": "verified",
    "plan_hash": digest(plan),
    "comparison_hash": digest(report),
    "api_attempts_used_for_audit": 0,
    "episodes": checks,
    "checks": [
        "plan and schedule",
        "episode manifests and summaries",
        "fixed horizons",
        "rule agreement on visited states",
        "original request JSON matches saved program and state",
        "recorded response decodes to recorded action",
        "global exchange IDs and per-episode ledgers",
        "emulator replay checks every observation, reward, and raw RAM/RGB hash",
    ],
}
write_json(args.out / "verification.json", audit)
print("All control evidence verified without API calls.")
