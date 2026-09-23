"""Verify original model exchanges, action decoding and emulator replay for the pilot."""

import argparse
import json
from pathlib import Path

from seaquest_observation_check import verify_episode

from jev_atari.choice import validate_choices
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.seaquest_pilot import MAX_ATTEMPTS, MODEL, PIN, SEEDS, SeaquestProgram


def verify(root, out):
    new_directory(out)
    plan, report, budget = [
        read_json(root / f"{name}.json") for name in ("plan", "results", "budget")
    ]
    assert report["plan_hash"] == digest(plan)
    assert plan["seeds"] == list(SEEDS) and plan["model"] == MODEL and plan["response_model"] == PIN
    program = SeaquestProgram.from_dict(plan["program"])
    assert program.hash == plan["program_hash"]
    assert budget["used"] <= budget["max_calls"] == MAX_ATTEMPTS
    index, episodes, ledger = 0, [], []
    for seed in SEEDS:
        path = root / f"seed-{seed}"
        if not path.exists():
            continue
        summary, manifest = read_json(path / "summary.json"), read_json(path / "manifest.json")
        assert manifest["seed"] == seed and manifest["program"] == program.to_dict()
        assert (
            manifest["program_hash"] == program.hash
            and manifest["source_revision"] == plan["source_revision"]
        )
        assert manifest["model_transport"]["expected_response_model"] == PIN
        assert manifest["model_transport"]["max_retries"] == 2
        rows = [json.loads(s) for s in (path / "transitions.jsonl").read_text().splitlines()]
        trace = path / "model-exchanges.jsonl"
        exchanges = (
            [json.loads(s) for s in trace.read_text().splitlines()] if trace.exists() else []
        )
        assert [e["transport"] for e in exchanges] == read_json(path / "api-ledger.json")
        assert len(exchanges) == summary["api_attempts"]
        pending = iter(exchanges)
        for row in rows:
            request = program.request(row["observation"], MODEL)
            for exchange in pending:
                index += 1
                assert exchange["exchange_id"] == index and exchange["request"] == request
                if exchange["exchange_id"] == row["prediction"]["exchange_id"]:
                    break
                assert exchange["response"] is None
            else:
                raise AssertionError("Action lacks original response")
            response, prediction = exchange["response"], row["prediction"]
            assert response["model"] == prediction["response_model"] == PIN
            assert (
                prediction["requested_model"] == MODEL
                and prediction["program_hash"] == program.hash
            )
            assert (
                prediction["usage"]
                == response.get("usage", {})
                == exchange["transport"].get("usage", {})
            )
            answer = validate_choices(response, request["questions"], prefer_probabilities=True)[
                "next_action"
            ]
            assert answer == prediction["choice_answer"]
            ids = {a["ale_meaning"]: a["id"] for a in row["observation"]["candidate_actions"]}
            assert row["action"] == prediction["chosen_action"] == ids[answer["choice"]]
        remaining = list(pending)
        assert not remaining or summary["status"] == "incomplete"
        for exchange in remaining:
            index += 1
            assert exchange["exchange_id"] == index
            if rows:
                assert exchange["request"] == program.request(rows[-1]["next_observation"], MODEL)
        assert summary["reward"] == sum(f["reward"] for row in rows for f in row["frames"])
        audit = verify_episode(path, out / f"seed-{seed}")
        episodes.append({"seed": seed, "status": summary["status"], "replay": audit})
        ledger.extend(e["transport"] for e in exchanges)
    assert index == budget["used"]
    if report["status"] == "complete":
        assert len(episodes) == len(SEEDS) and all(e["status"] == "complete" for e in episodes)
        assert report["episodes"] == [
            read_json(root / f"seed-{seed}" / "summary.json") for seed in SEEDS
        ]
    costs = {
        "attempts": len(ledger),
        "non_200": sum(e["status"] != 200 for e in ledger),
        "input_tokens": sum((e.get("usage") or {}).get("input_tokens", 0) for e in ledger),
        "output_tokens": sum((e.get("usage") or {}).get("output_tokens", 0) for e in ledger),
        "reported_cost_usd": sum((e.get("usage") or {}).get("cost", 0) for e in ledger),
        "api_seconds": sum(e["elapsed_seconds"] for e in ledger),
        "teacher_calls": 0,
        "billing_limits": "Successful-response costs only; failed-attempt billing unknown.",
    }
    write_json(out / "costs.json", costs)
    result = {
        "status": "verified",
        "pilot_status": report["status"],
        "episodes": episodes,
        "plan_hash": digest(plan),
        "report_hash": digest(report),
        "costs_hash": digest(costs),
        "audit_api_attempts": 0,
        "scope": "Original requests/responses, decoded actions and raw-frame replay.",
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.run, a.out)))
