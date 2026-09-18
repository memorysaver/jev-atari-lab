import pytest
from test_controls import make_evaluator

from jev_atari.choice import ActionProgram
from jev_atari.environment import Protocol
from jev_atari.io import read_json
from jev_atari.matches import aggregate_matches, match_result, run_matches
from jev_atari.models import BudgetExceeded
from jev_atari.policies import InterceptPolicy
from jev_atari.replay import replay_episode


def summary(*, scored=21, lost=10, frames=100, reason="native_termination", status="complete"):
    return {
        "points_scored": scored,
        "points_lost": lost,
        "reward": scored - lost,
        "status": status,
        "end_reason": reason,
        "raw_frames": frames,
        "terminated": reason == "native_termination",
    }


def test_capped_lead_is_not_a_win_and_errors_are_not_evaluated():
    win = match_result(summary(), 200)
    assert win["outcome"] == "win" and win["full_match_return"] == 11
    capped = match_result(summary(scored=5, lost=2, frames=200, reason="decision_limit"), 200)
    assert capped["evaluation_complete"] and capped["capped_episode_return"] == 3
    assert capped["outcome"] == "unfinished" and capped["full_match_return"] is None
    failed = match_result(summary(scored=5, lost=2, reason="error", status="incomplete"), 200)
    assert not failed["evaluation_complete"] and failed["capped_episode_return"] is None
    invalid = match_result(summary(scored=5, lost=2), 200)
    assert not invalid["native_match_complete"]
    rows = [
        {**x, "end_reason": r}
        for x, r in [(win, "native_termination"), (capped, "decision_limit"), (failed, "error")]
    ]
    a = aggregate_matches(rows, 4)
    assert a["mean_capped_return"] == 7  # Error and unstarted are excluded, not scored zero.
    assert a["win_rate_completed_matches"] == 1
    assert a["win_fraction_all_scheduled"] == a["completion_rate"] == 0.25
    assert a["possible_win_fraction_bounds"] == [0.25, 1]


def observation(x, y, velocity):
    return {
        "objects": [
            {"id": "player", "bbox": [140, 106, 4, 16]},
            {
                "id": "ball",
                "bbox": [x, y, 2, 4],
                "velocity": velocity,
                "velocity_valid": velocity is not None,
            },
        ]
    }


def test_intercept_uses_reflection_and_recenters_away():
    p = InterceptPolicy()
    # At center (101, 172), 38 frames to contact; y=248 reflects at center y=192 to 136.
    action, details = p.choose(observation(100, 170, [1, 2]))
    assert action == 3 and details["target_y"] == 136
    action, details = p.choose(observation(100, 40, [-1, -2]))
    assert action == 0 and details["mode"] == "recenter-away"
    assert p.choose(observation(100, 40, None))[0] == 2
    obs = observation(100, 40, None)
    obs["objects"][1]["bbox"] = None
    assert p.choose(obs)[0] == 0


def test_real_local_cap_and_replay_without_model(tmp_path):
    report = run_matches(
        Protocol(noop_max=0),
        arms=["random", "track-4px", "intercept"],
        seeds=[50],
        split="train",
        max_frames=40,
        out=tmp_path / "run",
    )
    assert report["status"] == "complete" and report["api_attempts"] == 0
    assert all(e["censored"] for e in report["episodes"])
    for e in report["episodes"]:
        path = tmp_path / "run" / e["arm"] / "seed-50"
        assert read_json(path / "manifest.json")["point_limit"] is None
        assert replay_episode(path, tmp_path / "replay" / e["arm"])["raw_frames"] == 40


def test_shared_live_budget_preserves_error_and_unstarted_denominators(tmp_path, monkeypatch):
    evaluator = make_evaluator(monkeypatch, 3)
    try:
        with pytest.raises(BudgetExceeded):
            run_matches(
                Protocol(noop_max=0),
                arms=["jev"],
                seeds=[56, 57, 66],
                split="development",
                max_frames=8,
                out=tmp_path / "run",
                evaluator=evaluator,
                program=ActionProgram(),
            )
        report = read_json(tmp_path / "run/results.json")
        assert report["api_attempts"] == 3 and report["status"] == "incomplete"
        a = report["aggregates"]["jev"]
        assert a["scheduled_episodes"] == 3 and a["recorded_episodes"] == 2
        assert a["evaluated_episodes"] == 1 and a["unfinished_or_unstarted"] == 3
        assert report["episodes"][1]["capped_episode_return"] is None
        assert replay_episode(tmp_path / "run/jev/seed-57", tmp_path / "replay")["raw_frames"] == 4
    finally:
        evaluator.close()


@pytest.mark.parametrize(
    "seeds,split,frames",
    [
        ([58], "development", 8),
        ([50], "development", 8),
        ([56, 56], "development", 8),
        ([56], "development", 7),
    ],
)
def test_invalid_design_rejected_before_creating_run(tmp_path, seeds, split, frames):
    with pytest.raises(ValueError):
        run_matches(
            Protocol(),
            arms=["random"],
            seeds=seeds,
            split=split,
            max_frames=frames,
            out=tmp_path / "run",
        )
    assert not (tmp_path / "run").exists()
