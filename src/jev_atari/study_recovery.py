"""Explicit offline recovery of a completed response rejected by the v1 CLI parser."""

import hashlib
from pathlib import Path

from jev_atari.io import digest, read_json, write_json
from jev_atari.study import parse_proposal


def recover_diagnostic_response(invocation: Path):
    """Never rerun or choose among messages; original execution metadata is immutable."""
    import json

    execution = read_json(invocation / "execution.json")
    events = read_json(invocation / "events.json")
    packet = read_json(invocation / "packet.json")
    if (
        execution["status"] != "incomplete"
        or execution.get("exit_code") != 0
        or execution.get("unexpected_item_types") != ["error"]
        or execution.get("error_type") != "ValueError"
        or execution["packet_hash"] != digest(packet)
        or execution["isolation"]["repository_mounted"]
        or execution["isolation"]["host_home_mounted"]
    ):
        raise ValueError("Not an eligible diagnostic-event parser failure")
    messages = [e["text"] for e in events if e["type"] == "agent_message"]
    if len(messages) != 1 or [e["type"] for e in events] != ["agent_message", "turn.completed"]:
        raise ValueError("Recovery needs one original final response and a completed turn")
    proposal = json.loads(messages[0])
    program = parse_proposal(proposal, packet)
    record = {
        "kind": "teacher-cli-diagnostic-recovery-v1",
        "packet_hash": digest(packet),
        "original_execution_hash": digest(execution),
        "original_events_hash": digest(events),
        "proposal": proposal,
        "program": program.to_dict(),
        "program_hash": program.hash,
        "new_model_calls": 0,
        "reason": "A completed CLI diagnostic error item was misclassified as tool activity.",
        "limitation": "The original recorder retained the item type but not its message. "
        "The specific diagnostic cause cannot be reconstructed.",
    }
    path = invocation / "recovery.json"
    if path.exists():
        if read_json(path) != record:
            raise ValueError("Recovery record changed")
    else:
        write_json(path, record)
    return record


def verify_continuation(root, receipt_path, source_revision):
    receipt = read_json(receipt_path)
    plan = read_json(root / "plan.json")
    if (
        receipt["kind"] != "pong-study-parser-continuation-v1"
        or receipt["source_revision"] != source_revision
        or receipt["original_plan_hash"] != digest(plan)
    ):
        raise ValueError("Continuation source or plan mismatch")
    budget = read_json(root / "budget.json")
    before = receipt["budget_before"]
    for key in (
        "started_at",
        "max_attempts",
        "nonfinal_limit",
        "final_limit",
        "teacher_limit",
        "live_seconds",
    ):
        if budget[key] != before[key]:
            raise ValueError("Continuation changed a budget or deadline")
    for key in (
        "attempts",
        "nonfinal_attempts",
        "final_attempts",
        "teacher_invocations",
        "teacher_repairs",
    ):
        if budget[key] < before[key]:
            raise ValueError("Continuation reset accounting")
    if before["training_closed"] and not budget["training_closed"]:
        raise ValueError("Continuation reopened sealed training")
    for entry in receipt["preserved_files"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid preserved path")
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("A preserved original artifact changed")
    return (plan["source_revision"],)
