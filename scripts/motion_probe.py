"""Prepare, run and audit a bounded three-question Jev motion-reliability probe."""

import argparse
import json
import subprocess
from pathlib import Path

from jev_atari.choice import ActionPolicy, ActionProgram, ChoiceEvaluator, validate_choices
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.motion_probe import LIMIT, MODEL, ProbeBudget, prepare, schedule, summarize


def run(pack, out, backend):
    if backend != "jev":
        raise ValueError("Live execution needs explicit --backend jev")
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Commit source before live execution")
    states, programs = read_json(pack / "inputs.json"), read_json(pack / "programs.json")
    order = schedule(states, programs)
    if len(states) > 80 or len(order) > 480:
        raise ValueError("Prepared inputs exceed the frozen budget")
    new_directory(out)
    plan = {
        "kind": "motion-probe-v1",
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "model": MODEL,
        "max_attempts": LIMIT,
        "max_live_seconds": 14400,
        "input_hash": digest(states),
        "programs_hash": digest(programs),
        "schedule": order,
        "selection": "None; diagnostic only. No rollout, promotion or teacher invocation.",
    }
    write_json(out / "plan.json", plan)
    report = {"status": "incomplete", "plan_hash": digest(plan), "completed_predictions": 0}
    write_json(out / "results.json", report)
    evaluator = None
    rows = []
    try:
        evaluator = ChoiceEvaluator(model=MODEL, max_calls=LIMIT)
        evaluator.api.budget = ProbeBudget(out / "budget.json")
        evaluator.api.retry_transport = True
        evaluator.api.trace_path = out / "model-exchanges.jsonl"
        lookup = {s["id"]: s for s in states}
        with (out / "predictions.jsonl").open("x") as stream:
            for item in order:
                result = evaluator.evaluate(
                    lookup[item["id"]]["observation"],
                    ActionProgram.from_dict(programs[item["program"]]),
                )
                if result["response_model"] != MODEL:
                    raise ValueError("Response model differs; stop without substitution")
                row = {**item, "prediction": result}
                stream.write(json.dumps(row) + "\n")
                stream.flush()
                rows.append(row)
                if len(rows) % 30 == 0:
                    print(
                        json.dumps(
                            {"predictions": len(rows), "attempts": evaluator.api.budget.used}
                        ),
                        flush=True,
                    )
        report["status"] = "complete"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        raise
    finally:
        ledger = evaluator.ledger if evaluator else []
        report.update(
            completed_predictions=len(rows),
            attempts=len(ledger),
            metrics=summarize(states, programs, rows),
            reported_input_tokens=sum(
                (e.get("usage") or {}).get("input_tokens", 0) for e in ledger
            ),
            reported_output_tokens=sum(
                (e.get("usage") or {}).get("output_tokens", 0) for e in ledger
            ),
            attempts_without_usage=sum(not e.get("usage") for e in ledger),
            api_elapsed_seconds=sum(e.get("elapsed_seconds", 0) for e in ledger),
            non_200_attempts=sum(e["status"] != 200 for e in ledger),
        )
        write_json(out / "api-ledger.json", ledger)
        write_json(out / "results.json", report)
        if evaluator:
            evaluator.close()
    return report


def verify(pack, run_path, out, source, repository):
    new_directory(out)
    states, programs = prepare(source, out / "regenerated-pack", repository)
    for name in ["inputs.json", "programs.json", "coverage.json", "provenance.json"]:
        assert read_json(pack / name) == read_json(out / "regenerated-pack" / name)
    plan, report = read_json(run_path / "plan.json"), read_json(run_path / "results.json")
    assert plan["model"] == MODEL and plan["max_attempts"] == LIMIT
    assert plan["max_live_seconds"] == 14400
    assert plan["input_hash"] == digest(states) and plan["programs_hash"] == digest(programs)
    assert plan["schedule"] == schedule(states, programs) and len(states) <= 80
    assert report["plan_hash"] == digest(plan) and report["status"] in ["complete", "incomplete"]

    def lines(name):
        p = run_path / name
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    rows, exchanges = lines("predictions.jsonl"), lines("model-exchanges.jsonl")
    assert [x["transport"] for x in exchanges] == read_json(run_path / "api-ledger.json")
    assert [x["exchange_id"] for x in exchanges] == list(range(1, len(exchanges) + 1))
    assert len(exchanges) == report["attempts"] <= LIMIT
    if (run_path / "budget.json").exists():
        budget = read_json(run_path / "budget.json")
        assert budget["used"] == len(exchanges)
        assert budget["max_calls"] == LIMIT and budget["live_seconds"] == 14400
    lookup = {s["id"]: s for s in states}
    pending = iter(exchanges)
    assert [{k: r[k] for k in ["id", "program", "repeat"]} for r in rows] == plan["schedule"][
        : len(rows)
    ]
    for row in rows:
        request = ActionProgram.from_dict(programs[row["program"]]).request(
            lookup[row["id"]]["observation"], MODEL
        )
        for exchange in pending:
            assert exchange["request"] == request
            if exchange["exchange_id"] == row["prediction"]["exchange_id"]:
                break
            assert exchange["response"] is None
        else:
            raise AssertionError("Prediction lacks exchange")
        assert exchange["response"]["model"] == MODEL
        answer = validate_choices(
            exchange["response"], request["questions"], prefer_probabilities=True
        )["next_action"]
        assert answer == row["prediction"]["choice_answer"]
        ids = {
            a["ale_meaning"]: a["id"] for a in lookup[row["id"]]["observation"]["candidate_actions"]
        }
        assert ids[answer["choice"]] == row["prediction"]["chosen_action"]
        assert (
            row["prediction"]["program_hash"]
            == ActionProgram.from_dict(programs[row["program"]]).hash
        )
        assert row["prediction"]["requested_model"] == row["prediction"]["response_model"] == MODEL
        assert row["prediction"]["selection_rule"] == ActionPolicy.selection_rule
        assert row["prediction"]["action_probabilities"] == {
            str(ids[name]): p for name, p in answer["probabilities"].items()
        }
        assert exchange["transport"].get("usage", {}) == exchange["response"].get("usage", {})
    remaining = list(pending)
    if report["status"] == "complete":
        assert len(rows) == len(plan["schedule"]) and not remaining
    elif remaining:
        item = plan["schedule"][len(rows)]
        request = ActionProgram.from_dict(programs[item["program"]]).request(
            lookup[item["id"]]["observation"], MODEL
        )
        assert all(e["request"] == request for e in remaining)
    assert report["completed_predictions"] == len(rows)
    assert report["metrics"] == summarize(states, programs, rows)
    ledger = [e["transport"] for e in exchanges]
    for field in ("input_tokens", "output_tokens"):
        assert report["reported_" + field] == sum(
            (e.get("usage") or {}).get(field, 0) for e in ledger
        )
    assert report["attempts_without_usage"] == sum(not e.get("usage") for e in ledger)
    assert report["non_200_attempts"] == sum(e["status"] != 200 for e in ledger)
    assert report["api_elapsed_seconds"] == sum(e.get("elapsed_seconds", 0) for e in ledger)
    result = {
        "status": "verified",
        "run_status": report["status"],
        "audit_api_attempts": 0,
        "source_revision": plan["source_revision"],
        "states": len(states),
        "predictions": len(rows),
        "attempts": len(exchanges),
        "unexecuted_attempts": len(remaining),
        "plan_hash": digest(plan),
        "results_hash": digest(report),
        "scope": "Training-source hashes, deterministic selection, requests/responses and metrics. "
        "No gameplay inference.",
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["prepare", "run", "verify"])
    for name in ["source", "pack", "run"]:
        p.add_argument("--" + name, type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--repository", type=Path, default=Path.cwd())
    p.add_argument("--backend", choices=["jev"])
    a = p.parse_args()
    if a.operation == "prepare":
        prepare(a.source, a.out, a.repository)
    elif a.operation == "run":
        run(a.pack, a.out, a.backend)
    else:
        print(json.dumps(verify(a.pack, a.run, a.out, a.source, a.repository)))
