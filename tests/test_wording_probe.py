"""Protect the frozen intervention and prospective screen without live calls."""

from copy import deepcopy
from pathlib import Path

import pytest

from jev_atari.choice import ActionProgram
from jev_atari.io import read_json, write_json
from jev_atari.motion_probe import MODEL, PRECISE, STRATA, schedule, summarize
from jev_atari.wording_probe import COMPACT, programs_for, provenance, screen, validate_pack

ROOT = Path(__file__).resolve().parents[1]


def test_only_question_changes_for_every_published_state():
    states = read_json(ROOT / "experiments/pong/motion-probe-v1/inputs.json")
    for state in states:
        compact = COMPACT.request(state["observation"], MODEL)
        expanded = PRECISE.request(state["observation"], MODEL)
        assert compact != expanded
        compact["questions"]["next_action"]["instructions"]["question"] = PRECISE.guidance
        assert compact == expanded
        assert set(compact["state"]) == {"observation"}
    assert len(COMPACT.guidance) < len(PRECISE.guidance)


def test_preflight_rejects_modified_inputs_programs_and_provenance(tmp_path):
    states = read_json(ROOT / "experiments/pong/motion-probe-v1/inputs.json")
    original = {
        "inputs.json": states,
        "programs.json": programs_for(ROOT),
        "provenance.json": provenance(ROOT, states),
        "coverage.json": read_json(ROOT / "experiments/pong/motion-probe-v1/coverage.json"),
    }
    for name, value in original.items():
        write_json(tmp_path / name, value)
    assert validate_pack(tmp_path, ROOT) == states
    for name in original:
        write_json(tmp_path / name, [])
        with pytest.raises(ValueError):
            validate_pack(tmp_path, ROOT)
        write_json(tmp_path / name, original[name])


def test_screen_requires_complete_schedule_and_all_strata():
    states = read_json(ROOT / "experiments/pong/motion-probe-v1/inputs.json")
    programs = programs_for(ROOT)
    rows = []
    for item in schedule(states, programs):
        state = next(s for s in states if s["id"] == item["id"])
        action = state["rule_actions"]["lookahead-conservative"]
        rows.append(
            {
                **item,
                "prediction": {"chosen_action": action if item["program"] != "expanded" else 1},
            }
        )
    report = {
        "status": "complete",
        "completed_predictions": 480,
        "metrics": summarize(states, programs, rows),
    }
    assert screen(report)["status"] == "eligible-for-separate-study-design"
    for stratum in STRATA:
        bad = deepcopy(report)
        row = next(
            r for r in bad["metrics"] if r["program"] == "compact" and r["stratum"] == stratum
        )
        row["agreement"]["lookahead-conservative"] = 0.5
        assert screen(bad)["status"] == "not-eligible"
    report["status"] = "incomplete"
    assert screen(report)["status"] == "not-eligible"
    empty = {
        "status": "incomplete",
        "completed_predictions": 0,
        "metrics": summarize(states, programs, []),
    }
    assert screen(empty)["status"] == "not-eligible"


def test_documented_candidate_matches_executable_guidance():
    doc = (ROOT / "docs/pong/teacher-rounds/D002-compact-wording.md").read_text()
    assert doc.split("```text\n", 1)[1].split("\n```", 1)[0] == COMPACT.guidance
    assert ActionProgram.from_dict(programs_for(ROOT)["expanded"]) == PRECISE
