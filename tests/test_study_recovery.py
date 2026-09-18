"""Regression tests for diagnostic events and zero-call study continuation."""

import hashlib
import json

import pytest

from jev_atari.choice import ActionProgram
from jev_atari.io import digest, read_json, write_json
from jev_atari.study import StudyBudget, teacher_packet
from jev_atari.study_recovery import recover_diagnostic_response, verify_continuation
from jev_atari.study_runner import propose
from jev_atari.teacher import summarize_events


def test_diagnostic_is_not_a_tool_but_started_commands_are():
    lines = [
        {"type": "item.completed", "item": {"type": "error", "message": "private detail"}},
        {"type": "item.started", "item": {"type": "command_execution"}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "{}"}},
        {"type": "turn.completed", "usage": {"input_tokens": 5}},
    ]
    events, unexpected = summarize_events("\n".join(map(json.dumps, lines)))
    assert unexpected == ["command_execution"]
    assert [e["type"] for e in events] == ["diagnostic_error", "agent_message", "turn.completed"]
    assert "private detail" not in json.dumps(events)
    events, unexpected = summarize_events('{"type":"turn.failed"}')
    assert events[0]["type"] == "turn.failed" and not unexpected


def original_invocation(root):
    packet = teacher_packet(
        "B", 1, ActionProgram(), {"split": "train", "examples": [], "episodes": []}, []
    )
    proposal = {
        "name": "original-single-answer",
        "guidance": "Choose NOOP.",
        "hypothesis": "Synthetic only",
        "operator": "test",
        "evidence_ids": [],
        "predicted_changes": "Test fixture",
        "regression_risks": "Test fixture",
    }
    execution = {
        "status": "incomplete",
        "exit_code": 0,
        "unexpected_item_types": ["error"],
        "error_type": "ValueError",
        "packet_hash": digest(packet),
        "isolation": {"repository_mounted": False, "host_home_mounted": False},
    }
    events = [
        {"type": "agent_message", "text": json.dumps(proposal)},
        {"type": "turn.completed", "usage": {}},
    ]
    for name, value in (("packet", packet), ("execution", execution), ("events", events)):
        write_json(root / f"{name}.json", value)
    return packet


def test_recovery_preserves_original_and_uses_no_new_invocation(tmp_path):
    invocation = tmp_path / "teacher" / "invocation-1"
    packet = original_invocation(invocation)
    originals = {p: p.read_bytes() for p in invocation.iterdir()}
    recovered = recover_diagnostic_response(invocation)
    assert recovered["new_model_calls"] == 0
    budget = StudyBudget(tmp_path / "budget.json")
    program, proposal = propose(invocation.parent, packet, budget, None, None)
    assert program.name == proposal["name"] == "original-single-answer"
    assert read_json(budget.path)["teacher_invocations"] == 0
    assert all(p.read_bytes() == content for p, content in originals.items())
    assert recover_diagnostic_response(invocation) == recovered
    events = read_json(invocation / "events.json")
    events.insert(0, events[0])
    write_json(invocation / "events.json", events)
    with pytest.raises(ValueError, match="one original"):
        recover_diagnostic_response(invocation)


def test_recovery_rejects_tool_activity(tmp_path):
    original_invocation(tmp_path)
    execution = read_json(tmp_path / "execution.json")
    execution["unexpected_item_types"].append("command_execution")
    write_json(tmp_path / "execution.json", execution)
    with pytest.raises(ValueError, match="eligible"):
        recover_diagnostic_response(tmp_path)


def test_continuation_checks_source_originals_and_nonreset_budget(tmp_path):
    plan = {"source_revision": "original-source"}
    write_json(tmp_path / "plan.json", plan)
    budget = StudyBudget(tmp_path / "budget.json", clock=lambda: 100)
    budget.reserve("nonfinal")
    receipt = {
        "kind": "pong-study-parser-continuation-v1",
        "source_revision": "fixed-source",
        "original_plan_hash": digest(plan),
        "budget_before": read_json(budget.path),
        "preserved_files": [
            {
                "path": "plan.json",
                "sha256": hashlib.sha256((tmp_path / "plan.json").read_bytes()).hexdigest(),
            }
        ],
    }
    path = tmp_path / "receipt.json"
    write_json(path, receipt)
    assert verify_continuation(tmp_path, path, "fixed-source") == ("original-source",)
    with pytest.raises(ValueError, match="source"):
        verify_continuation(tmp_path, path, "different")
    state = read_json(budget.path)
    state["attempts"] = 0
    write_json(budget.path, state)
    with pytest.raises(ValueError, match="reset"):
        verify_continuation(tmp_path, path, "fixed-source")
    write_json(budget.path, receipt["budget_before"])
    state = read_json(budget.path)
    state["started_at"] = 101
    write_json(budget.path, state)
    with pytest.raises(ValueError, match="deadline"):
        verify_continuation(tmp_path, path, "fixed-source")
    write_json(budget.path, receipt["budget_before"])
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="artifact"):
        verify_continuation(tmp_path, path, "fixed-source")
