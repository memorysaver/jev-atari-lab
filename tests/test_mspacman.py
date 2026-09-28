"""Offline Ms. Pac-Man observation and replay contracts; no live model calls."""

import json

from jev_atari.arcade import make_game
from jev_atari.mspacman import NAMES, Observer, literal
from jev_atari.mspacman_pilot import audit, play


def test_initial_geometry_and_observation_are_grounded():
    with make_game("MsPacman", 0) as env:
        env.reset(seed=510)
        observer = Observer(env.unwrapped.ale.getScreenRGB())
        obs, checks = observer.observe(
            env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB(), 0
        )
        assert checks["player_pixels"] > 0 and checks["graph_error"] == 0
        assert len(obs["pellets"]) > 100
        assert {e["direction"] for e in obs["exits"]} == {"LEFT", "RIGHT"}
        assert tuple(a["ale_meaning"] for a in obs["candidate_actions"]) == NAMES
        assert "reference_action" not in json.dumps(obs)
        assert "safe_route" not in json.dumps(obs)
        assert observer.maze.nearest([80, 80])[1] > 3
        for _ in range(320):
            env.step(2)
        nxt, checks = observer.observe(
            env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB(), 320
        )
        assert nxt["player"]["xy"][0] > obs["player"]["xy"][0]
        assert checks["player_pixels"] > 0
        assert nxt["history"][0]["player"] == obs["player"]
        assert obs["history"] == []


def test_local_policies_and_raw_frame_video_replay(tmp_path):
    path = tmp_path / "episode"
    summary = play(path, 510, "pellet", cap=64)
    result = audit(path)
    assert result["frames"] == summary["frames"] == 336
    assert result["decisions"] == 8
    assert summary["status"] == "complete"
    assert summary["observation_checks"]["supported_on_graph"] == 8
    assert not (path / "model-exchanges.jsonl").exists()


def test_missing_player_does_not_invent_local_action():
    assert literal({"player": {"visible": False}}, None) == (0, "unavailable")
