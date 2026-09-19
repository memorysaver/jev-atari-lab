"""Offline verification of a published Pong teacher study, including partial runs."""

import argparse
import json
import sys
from pathlib import Path

from jev_atari.choice import ActionProgram, validate_choices
from jev_atari.io import digest, read_json, write_json
from jev_atari.study import (
    DEV_SEEDS,
    FINAL_SEEDS,
    MODEL,
    TRAIN_SEEDS,
    parse_proposal,
    probe_report,
    read_rows,
    sample_training,
    select_policy,
    teacher_packet,
)
from jev_atari.study_recovery import verify_continuation


def verify_study(root, out, repository):
    sys.path.insert(0, str(repository / "scripts"))
    from verify_matches import verify

    if out.exists():
        raise ValueError("Audit output already exists")
    plan, budget = read_json(root / "plan.json"), read_json(root / "budget.json")
    source = plan["source_revision"]
    status = read_json(root / "status.json")
    assert status["status"] in {"complete", "incomplete"}, "Refuse a moving live study"
    continuation_path = root / "continuations/parser-recovery.json"
    continuations = []
    allowed_sources = {source}
    if continuation_path.exists():
        receipt = read_json(continuation_path)
        verify_continuation(root, continuation_path, status["source_revision"])
        allowed_sources.add(receipt["source_revision"])
        continuations.append(
            {"path": str(continuation_path.relative_to(root)), "sha256": digest(receipt)}
        )
    assert status["source_revision"] in allowed_sources
    assert status["budget"] == budget
    assert plan["train_seeds"] == [list(seeds) for seeds in TRAIN_SEEDS]
    assert plan["development_seeds"] == list(DEV_SEEDS)
    assert plan["final_seeds"] == list(FINAL_SEEDS)
    for key, expected in [
        ("max_attempts", 220000),
        ("nonfinal_limit", 154000),
        ("final_limit", 66000),
        ("teacher_limit", 8),
        ("live_seconds", 86400),
    ]:
        assert budget[key] == expected
    initial = ActionProgram.from_dict(
        read_json(repository / "examples/vertical-policy-program.json")
    )
    assert initial.hash == plan["initial_program_hash"]
    incumbents = {"A": initial, "B": initial}
    selections = []
    counts = {"final": 0, "nonfinal": 0}
    suites = []
    for path in sorted(root.rglob("plan.json")):
        p = read_json(path)
        if p.get("kind") != "pong-study-episode-plan-v1":
            continue
        assert p["source_revision"] in allowed_sources
        assert p["model"] == MODEL and p["protocol"] == plan["protocol"]
        expected_cap = 10000 if "training" in path.parts else 20000
        assert p["max_frames_per_episode"] == expected_cap
        assert p["max_decisions_per_episode"] == expected_cap // 4
        assert p["point_limit"] is None
        rel = path.parent.relative_to(root)
        report = read_json(path.parent / "results.json")
        audited = verify(path.parent, out / "episodes" / rel)
        phase = "final" if p["split"] == "test" else "nonfinal"
        counts[phase] += report["api_attempts"]
        suites.append(
            {
                "path": str(rel),
                "results_hash": digest(report),
                "audit_status": audited["status"],
                "split": p["split"],
            }
        )

    probe_audits = []
    for changes_path in sorted(root.glob("round-*/[AB]/question-changes.json")):
        changes = read_json(changes_path)
        probe = changes_path.parent / "probes"
        if not (probe / "model-exchanges.jsonl").exists():
            continue
        programs = {
            "parent": ActionProgram.from_dict(changes["before"]),
            "candidate": ActionProgram.from_dict(changes["after"]),
        }
        states = {s["id"]: s for s in read_json(probe / "inputs.json")}
        predictions = read_rows(probe / "predictions.jsonl")
        exchanges = read_rows(probe / "model-exchanges.jsonl")
        assert [x["exchange_id"] for x in exchanges] == list(range(1, len(exchanges) + 1))
        assert [x["transport"] for x in exchanges] == read_json(probe / "api-ledger.json")
        pending = iter(exchanges)
        for row in predictions:
            request = programs[row["program_role"]].request(states[row["id"]]["observation"], MODEL)
            for exchange in pending:
                assert exchange["request"] == request
                if exchange["exchange_id"] == row["prediction"]["exchange_id"]:
                    break
                assert exchange["response"] is None
            else:
                raise AssertionError("Probe prediction lacks exchange")
            assert exchange["response"]["model"] == MODEL
            answer = validate_choices(
                exchange["response"], request["questions"], prefer_probabilities=True
            )["next_action"]
            assert answer == row["answer"] == row["prediction"]["choice_answer"]
        remaining = list(pending)
        if (probe / "results.json").exists():
            report = read_json(probe / "results.json")
            assert not remaining and len(predictions) == 128
            assert report["metrics"] == probe_report(predictions)
            assert report["inputs_hash"] == digest(list(states.values()))
        counts["nonfinal"] += len(exchanges)
        probe_audits.append(
            {
                "path": str(probe.relative_to(root)),
                "queries": len(predictions),
                "attempts": len(exchanges),
                "unexecuted_attempts": len(remaining),
            }
        )

    teacher_checks, memories = [], {"A": [], "B": []}
    for rd in sorted(root.glob("round-*")):
        if not (rd / "training-evidence.json").exists():
            continue
        number = int(rd.name.split("-")[1])
        paths = [p / "jev" / p.name for p in sorted((rd / "training").glob("seed-*"))]
        for path in paths:
            assert (
                read_json(path / "manifest.json")["question_program"] == incumbents["A"].to_dict()
            )
        evidence = sample_training(paths)
        assert evidence == read_json(rd / "training-evidence.json")
        for arm in ("A", "B"):
            tr = rd / arm / "teacher"
            first = tr / "invocation-1"
            if not (first / "packet.json").exists():
                continue
            packet = read_json(first / "packet.json")
            program = ActionProgram.from_dict(packet["current_program"])
            assert program.hash == incumbents[arm].hash
            assert packet == teacher_packet(arm, number, program, evidence, memories[arm])
            original_responses = []
            for invocation in sorted(tr.glob("invocation-*")):
                execution = read_json(invocation / "execution.json")
                assert execution["requested_model"] == "gpt-6-astra"
                assert execution["requested_reasoning_effort"] == "high"
                assert not execution["isolation"]["repository_mounted"]
                assert not execution["isolation"]["host_home_mounted"]
                assert execution["packet_hash"] == digest(read_json(invocation / "packet.json"))
                events_path = invocation / "events.json"
                events = read_json(events_path) if events_path.exists() else []
                messages = [e["text"] for e in events if e["type"] == "agent_message"]
                recovery_path = invocation / "recovery.json"
                if recovery_path.exists():
                    assert continuations and number == 1 and arm == "A"
                    recovery = read_json(recovery_path)
                    assert execution["status"] == "incomplete" and execution["exit_code"] == 0
                    assert execution["unexpected_item_types"] == ["error"]
                    assert recovery["original_execution_hash"] == digest(execution)
                    assert recovery["original_events_hash"] == digest(events)
                    assert recovery["packet_hash"] == digest(packet)
                    assert recovery["new_model_calls"] == 0
                    assert [e["type"] for e in events] == ["agent_message", "turn.completed"]
                    assert recovery["proposal"] == json.loads(messages[0])
                    recovered = parse_proposal(recovery["proposal"], packet)
                    assert recovery["program"] == recovered.to_dict()
                    assert recovery["program_hash"] == recovered.hash
                    original_responses.append(recovery["proposal"])
                elif execution["status"] == "complete":
                    assert execution["exit_code"] == 0
                    assert not execution.get("unexpected_item_types")
                    assert any(e["type"] == "turn.completed" for e in events)
                    assert not any(e["type"] == "turn.failed" for e in events)
                    output = read_json(invocation / "proposal.json")
                    assert messages and json.loads(messages[-1]) == output
                    original_responses.append(output)
                teacher_checks.append(
                    {
                        "path": str(invocation.relative_to(root)),
                        "status": execution["status"],
                        "reserved": execution.get("started_at") is not None,
                    }
                )
            if (tr / "validated.json").exists():
                validated = read_json(tr / "validated.json")
                assert original_responses and validated["proposal"] == original_responses[-1]
                assert validated["packet_hash"] == digest(packet)
                candidate = parse_proposal(validated["proposal"], packet)
                assert candidate.to_dict() == validated["program"]
                changes = read_json(rd / arm / "question-changes.json")
                if (rd / arm / "probes" / "inputs.json").exists():
                    assert read_json(rd / arm / "probes" / "inputs.json") == [
                        e for e in evidence["examples"] if e["probe"]
                    ]
                for role, expected_program in (("parent", program), ("candidate", candidate)):
                    for episode_plan in (rd / arm / "development" / role).glob("seed-*/plan.json"):
                        assert read_json(episode_plan)["program_hash"] == expected_program.hash
                assert changes["before"] == program.to_dict()
                assert changes["after"] == candidate.to_dict()
                assert changes["parent_hash"] == program.hash
                assert changes["candidate_hash"] == candidate.hash
                assert changes["proposal"] == validated["proposal"]
                assert changes["packet_hash"] == digest(packet)
                selection_file = rd / arm / "selection.json"
                if selection_file.exists():
                    old_rows = [
                        read_json(
                            rd / arm / "development" / "parent" / f"seed-{s}" / "results.json"
                        )["episodes"][0]
                        for s in DEV_SEEDS
                    ]
                    new_rows = [
                        read_json(
                            rd / arm / "development" / "candidate" / f"seed-{s}" / "results.json"
                        )["episodes"][0]
                        for s in DEV_SEEDS
                    ]
                    expected = select_policy(old_rows, new_rows)
                    selected = candidate if expected["accepted"] else program
                    expected["selected_program"] = selected.to_dict()
                    expected["selected_program_hash"] = selected.hash
                    assert read_json(selection_file) == expected
                    incumbents[arm] = selected
                    selections.append({"round": number, "arm": arm, "decision": expected})
                memories[arm].append({"round": number, "proposal": validated["proposal"]})

    if (root / "final-seal.json").exists():
        seal = read_json(root / "final-seal.json")
        assert seal["sha256"] == digest(seal["seal"])
        expected_programs = {**incumbents, "V2": initial}
        assert len(selections) == 6 and budget["training_closed"]
        assert seal["seal"]["source_revision"] == status["source_revision"]
        assert seal["seal"]["programs"] == {k: p.to_dict() for k, p in expected_programs.items()}
        assert seal["seal"]["program_hashes"] == {k: p.hash for k, p in expected_programs.items()}
        assert seal["seal"]["protocol"] == plan["protocol"]
        assert seal["seal"]["seeds"] == list(FINAL_SEEDS)
        assert seal["seal"]["model"] == MODEL and seal["seal"]["max_frames"] == 20000
    if status["status"] == "complete":
        assert len(suites) == 42 and len(probe_audits) == 6 and len(selections) == 6
        assert len(status["rounds"]) == 3
        for rd in status["rounds"]:
            assert rd["decisions"] == {
                s["arm"]: s["decision"] for s in selections if s["round"] == rd["round"]
            }
        final = read_json(root / "final-results.json")
        for arm in ("A", "B", "V2"):
            rows = [
                read_json(root / "final" / arm / f"seed-{s}" / "results.json")["episodes"][0]
                for s in FINAL_SEEDS
            ]
            assert final[arm] == rows and all(r["evaluation_complete"] for r in rows)
        assert status["final_seal_hash"] == seal["sha256"]
    assert counts["nonfinal"] == budget["nonfinal_attempts"]
    assert counts["final"] == budget["final_attempts"]
    assert sum(counts.values()) == budget["attempts"] <= 220000
    assert counts["nonfinal"] <= 154000 and counts["final"] <= 66000
    assert sum(t["reserved"] for t in teacher_checks) == budget["teacher_invocations"] <= 8
    result = {
        "kind": "pong-teacher-study-audit-v1",
        "status": "verified",
        "api_calls_for_audit": 0,
        "plan_hash": digest(plan),
        "budget_hash": digest(budget),
        "study_status": status["status"],
        "continuations": continuations,
        "source_revisions": sorted(allowed_sources),
        "episode_suites": suites,
        "selections": selections,
        "probes": probe_audits,
        "teacher_invocations": teacher_checks,
        "attempts": counts,
        "scope": "Provenance, packet isolation, raw exchanges and emulator replay. "
        "Does not infer missing model attestation or establish learning.",
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = verify_study(args.run, args.out, args.repository)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"episode_suites", "probes", "teacher_invocations"}
            }
        )
    )
