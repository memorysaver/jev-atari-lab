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


def test_two_stage_uses_model_target_and_keeps_all_actions(tmp_path, monkeypatch):
    import httpx

    from jev_atari.mspacman_questions import PIN, Policy

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    requests = []

    def handler(req):
        body = json.loads(req.content)
        requests.append(body)
        choices = body["questions"]["decision"]["criteria"]
        choice = "ghost-2" if "PELLETS" in choices else "LEFT"
        return httpx.Response(
            200,
            json={
                "model": PIN,
                "answers": {
                    "decision": {
                        "type": "choice",
                        "choice": choice,
                        "confidence": 1,
                        "probabilities": {k: float(k == choice) for k in choices},
                    }
                },
                "usage": {"cost": 0},
            },
        )

    policy = Policy(tmp_path, client=httpx.Client(transport=httpx.MockTransport(handler)))
    policy.trace(tmp_path / "episode")
    result = policy.choose({"synthetic": True}, "two-stage")
    assert result["action"] == NAMES.index("LEFT")
    assert requests[1]["state"]["selected_intent"] == "ghost-2"
    assert requests[0]["state"]["observation"] == requests[1]["state"]["observation"]
    assert set(requests[1]["questions"]["decision"]["criteria"]) == set(NAMES)
    assert policy.budget.used == 2
    assert len((tmp_path / "episode" / "model-exchanges.jsonl").read_text().splitlines()) == 2
    policy.api.close()


def test_model_pin_failure_and_budget_closure(tmp_path, monkeypatch):
    import httpx
    import pytest

    from jev_atari.models import BudgetExceeded, ModelError
    from jev_atari.mspacman_questions import Budget, Policy

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"model": "different", "usage": {"cost": 0}})
        )
    )
    policy = Policy(tmp_path, client=client)
    with pytest.raises(ModelError, match="model mismatch"):
        policy.choose({}, "direct")
    assert policy.budget.used == 1
    policy.budget.close("test-complete")
    with pytest.raises(BudgetExceeded):
        Budget(tmp_path / "budget.json").reserve()
    policy.api.close()


def test_all_native_action_effects_after_startup():
    expected_signs = [
        (None, None),
        (None, -1),
        (1, None),
        (-1, None),
        (None, 1),
        (1, -1),
        (-1, -1),
        (1, 1),
        (-1, 1),
    ]
    with make_game("MsPacman", 0) as env:
        for action, (sx, sy) in enumerate(expected_signs):
            env.reset(seed=514)
            start = env.unwrapped.ale.getRAM()[[10, 16]].astype(int)
            for _ in range(400):
                env.step(action)
            delta = env.unwrapped.ale.getRAM()[[10, 16]].astype(int) - start
            if sx is not None:
                assert delta[0] * sx > 0, NAMES[action]
            if sy is not None:
                assert delta[1] * sy > 0, NAMES[action]
