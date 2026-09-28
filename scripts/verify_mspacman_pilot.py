"""Replay Ms. Pac-Man evidence and bind decisions to original model exchanges."""

import argparse
import json
from collections import Counter
from pathlib import Path

import imageio.v2 as imageio

from jev_atari.choice import validate_choices
from jev_atari.io import digest, read_json, write_json
from jev_atari.mspacman import NAMES, Maze, literal
from jev_atari.mspacman_pilot import audit
from jev_atari.mspacman_questions import PIN, PROGRAM, request


def exchanges(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return {r["exchange_id"]: r for r in rows}


def verify_prediction(obs, prediction, arm, original):
    assert prediction["program_hash"] == digest(PROGRAM)
    responses = prediction["responses"]
    assert [r["stage"] for r in responses] == (
        ["direct"] if arm == "direct" else ["intent", "action"]
    )
    intent = None
    for response in responses:
        row = original.pop(response["exchange_id"])
        expected = request(obs, response["stage"], intent)
        assert row["request"] == expected
        assert row["transport"]["status"] == 200
        assert row["response"]["model"] == response["response_model"] == PIN
        answer = validate_choices(
            row["response"], expected["questions"], prefer_probabilities=True
        )["decision"]
        assert answer == response["answer"]
        assert row["response"].get("usage", {}) == response["usage"]
        intent = answer["choice"]
    assert prediction["action"] == NAMES.index(responses[-1]["answer"]["choice"])


def verify(root, calibration):
    complete = read_json(root / "closure.json")["status"] == "completed"
    plan = read_json(root / "plan.json")
    packet = read_json(root / "packet.json")
    assert digest(packet) == plan["packet_hash"]
    assert read_json(root / "program.json") == PROGRAM
    assert plan["program_hash"] == digest(PROGRAM)
    maze = Maze(imageio.imread(calibration / "avoid" / "seed-510" / "initial.png"))
    result = {"complete": complete, "probes": {}, "episodes": [], "unconsumed_exchanges": 0}
    trace = root / "probes" / "model-exchanges.jsonl"
    original = exchanges(trace) if trace.exists() else {}
    counters = {"direct": Counter(), "two-stage": Counter()}
    probe_results = root / "probes" / "results.jsonl"
    if probe_results.exists():
        for line in probe_results.read_text().splitlines():
            row = json.loads(line)
            item = packet[row["index"]]
            obs, pred, arm = item["observation"], row["prediction"], row["arm"]
            verify_prediction(obs, pred, arm, original)
            expected, _ = literal(obs, maze, "avoid")
            counters[arm]["n"] += 1
            counters[arm]["literal_action_matches"] += int(pred["action"] == expected)
            counters[arm][f"{item['group']}_n"] += 1
            counters[arm][f"{item['group']}_matches"] += int(pred["action"] == expected)
            if arm == "two-stage":
                counters[arm]["intent_matches"] += int(
                    pred["responses"][0]["answer"]["choice"] == item["reference_intent"]
                )
    result["probes"] = {k: dict(v) for k, v in counters.items()}
    result["unconsumed_exchanges"] += len(original)
    if complete:
        assert not original
        assert all(v["n"] == 24 for v in counters.values())
    for manifest in sorted((root / "episodes").rglob("manifest.json")):
        path = manifest.parent
        checked = audit(path)
        m = read_json(manifest)
        trace = path / "model-exchanges.jsonl"
        if trace.exists():
            original = exchanges(trace)
            for line in (path / "transitions.jsonl").read_text().splitlines():
                row = json.loads(line)
                if row["controlled"]:
                    verify_prediction(row["observation"], row["prediction"], m["rule"], original)
            result["unconsumed_exchanges"] += len(original)
            if complete:
                assert not original
        checked.update(seed=m["seed"], arm=m["rule"])
        result["episodes"].append(checked)
    budget = read_json(root / "budget.json")
    ledgers = read_json(root / "api-ledger.json")
    trace_rows = [r for p in root.rglob("model-exchanges.jsonl") for r in exchanges(p).values()]
    assert len(trace_rows) == len(ledgers) == budget["used"]
    assert sorted(r["exchange_id"] for r in trace_rows) == list(range(1, budget["used"] + 1))
    assert budget["closed"] and budget["used"] <= plan["max_calls"]
    result["attempts"] = budget["used"]
    result["reported_cost_usd"] = budget["reported_cost_usd"]
    result["missing_cost_records"] = sum("cost" not in (r.get("usage") or {}) for r in ledgers)
    result["api_seconds"] = sum(r["elapsed_seconds"] for r in ledgers)
    if complete:
        assert len(result["episodes"]) == 10
        scores = {(e["arm"], e["seed"]): e["reward"] for e in result["episodes"]}
        gains = [scores["two-stage", seed] - scores["direct", seed] for seed in (516, 517)]
        result["paired_score_gains"] = gains
        result["exploratory_gameplay_gate"] = min(gains) >= 0 and sum(gains) > 0
    write_json(root / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run, args.calibration), indent=2))
