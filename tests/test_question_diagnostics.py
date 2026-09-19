"""Geometry and time-unit checks for diagnostic controllers; no model calls."""

from copy import deepcopy

import pytest

from jev_atari.observation import Tracker, make_observation
from jev_atari.policies import HeuristicPolicy
from jev_atari.question_diagnostics import DiagnosticPolicy, interpret, reflect


def obs():
    tracker = Tracker()
    result = None
    for frame, x, y in [(0, 80, 96), (8, 88, 104), (12, 92, 108)]:
        result = make_observation(
            tracker,
            {"ball": [x, y, 2, 4], "player": [140, 100, 4, 16]},
            frame,
            source="ram",
            hold=4,
            sticky=0.25,
            last_action=0,
            events=[],
        )
    return result


def test_time_units_and_distinct_horizons():
    state = obs()
    assert interpret(state, "v2")["action"] == 0  # gap 2 px
    short = interpret(state, "lookahead")
    assert short["target_y"] == 114 and short["action"] == 3  # 1 px/frame * 4
    long = interpret(state, "intercept")
    assert long["time_to_contact_raw_frames"] == 46
    assert long["target_y"] == 156 and long["action"] == 3
    assert interpret(state, "lookahead-conservative") == {**short, "rule": "lookahead-conservative"}


@pytest.mark.parametrize(
    "target,expected,count",
    [(35, 35, 0), (192, 192, 0), (30, 40, 1), (200, 184, 1), (400, 86, 2), (-200, 114, 2)],
)
def test_reflections(target, expected, count):
    assert reflect(target) == (expected, count)


def test_missing_outgoing_and_unknown_motion():
    state = obs()
    for velocity, valid in [([-1, 1], True), ([1, 1], False), (None, False)]:
        state["objects"][0].update(velocity=velocity, velocity_valid=valid)
        assert interpret(state, "intercept")["target_y"] == 110
        assert interpret(state, "lookahead")["target_y"] == 110
    state["objects"][0]["bbox"] = None
    assert all(DiagnosticPolicy(r).choose(state)[0] == 0 for r in ["v2", "intercept", "lookahead"])


def test_recent_sign_reversal_is_an_explicit_ambiguity():
    state = obs()
    state["history"][0]["boxes"]["ball"][1] = 120
    assert interpret(state, "lookahead")["action"] == 3
    conservative = interpret(state, "lookahead-conservative")
    assert conservative["recent_sign_reversal"] is True
    assert conservative["action"] == 0


def test_boundaries_and_purity_match_existing_v2():
    state = obs()
    for delta in [-5, -4, 0, 4, 5]:
        state["objects"][0]["bbox"][1] = 108 + delta - 2
        original = deepcopy(state)
        assert DiagnosticPolicy("v2").choose(state)[0] == HeuristicPolicy(4).choose(state)[0]
        assert state == original
    state["objects"][0]["bbox"][0] = 140
    assert interpret(state, "intercept")["mode"] == "current-height"
