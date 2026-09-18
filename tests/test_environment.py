from copy import deepcopy

import numpy as np
import pytest

from jev_atari.environment import Pong, Protocol
from jev_atari.experiment import branch_outcome, doctor
from jev_atari.io import digest
from jev_atari.observation import Tracker, ram_boxes
from jev_atari.policies import HeuristicPolicy


def test_real_sticky_replay_and_action_mapping():
    result = doctor(Protocol(sticky=0.25))
    assert result["replay_identical"]
    assert result["action_y_displacements"]["2"] < 0
    assert result["action_y_displacements"]["3"] > 0


def test_step_counts_raw_frames_and_no_implicit_advancement():
    with Pong(Protocol(noop_max=0)) as env:
        obs = env.reset(0)
        assert env.raw_frames == 0
        for _ in range(20):
            HeuristicPolicy().choose(deepcopy(obs))
        assert env.raw_frames == 0
        assert env.env.unwrapped.ale.getEpisodeFrameNumber() == 0
        transition = env.step(2, capture=True)
        assert transition.raw_frames == env.raw_frames == len(transition.rgb_frames) == 4
        assert env.env.unwrapped.ale.getEpisodeFrameNumber() == 4
        assert transition.observation["control"]["last_executed_action_id"] is None
        assert "seed" not in transition.observation


def test_branch_does_not_pollute_live_state():
    with Pong(Protocol(noop_max=0)) as env:
        env.reset(0)
        for _ in range(80):
            env.step(2)
        snapshot = env.snapshot()
        before = digest(env.observation)
        outcome = branch_outcome(env, 3, 121)
        assert 1 <= outcome["raw_frames"] <= 121
        if outcome["label"] == 0:
            assert outcome["raw_frames"] == 121
        env.restore(snapshot)
        assert digest(env.observation) == before
        first = env.step(2)
        env.restore(snapshot)
        second = env.step(2)
        assert first.observation == second.observation
        assert first.rewards == second.rewards


def test_missing_ball_invalidates_velocity_until_new_pair():
    tracker = Tracker()
    boxes = {"ball": [40, 50, 2, 4]}
    assert not tracker.update(boxes, 0)[0]["velocity_valid"]
    assert tracker.update({"ball": [48, 46, 2, 4]}, 4)[0]["velocity"] == [2, -1]
    missing = tracker.update({"ball": None}, 8)[0]
    assert missing["bbox"] is None and missing["velocity"] is None
    assert missing["age_since_last_seen_raw_frames"] == 4
    assert not tracker.update(boxes, 12)[0]["velocity_valid"]
    tracker.clear_ball_history()
    assert not tracker.update(boxes, 16)[0]["velocity_valid"]


def test_zero_ram_does_not_underflow_to_huge_coordinates():
    assert all(x is None for x in ram_boxes(np.zeros(128, dtype=np.uint8)).values())


def test_ram_and_vision_both_run_without_hidden_fallback():
    for source in ("ram", "vision"):
        with Pong(Protocol(observation=source)) as env:
            obs = env.reset(0)
            for _ in range(100):
                obs = env.step(HeuristicPolicy().choose(obs)[0]).observation
            assert obs["observation_source"] == source
            assert any(o["id"] == "player" and o["present"] for o in obs["objects"])


@pytest.mark.parametrize("action", [-1, 6, True, "2"])
def test_rejects_invalid_actions(action):
    with Pong() as env:
        env.reset(0)
        with pytest.raises(ValueError):
            env.step(action)
