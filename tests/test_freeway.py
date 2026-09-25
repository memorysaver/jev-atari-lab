"""Offline Freeway contracts; never call a live model."""

import numpy as np
import pytest

from jev_atari.arcade import make_game
from jev_atari.freeway import FreewayProgram, Observer, literal, prefix_length, screen_checks


def test_observer_history_is_immutable_and_matches_pixels():
    with make_game("Freeway", 0) as env:
        env.reset(seed=410)
        for _ in range(128):
            env.step(0)
        observer = Observer()
        first = observer.observe(env.unwrapped.ale.getRAM(), 128)
        checks = screen_checks(first, env.unwrapped.ale.getScreenRGB())
        assert all(c["pixels"] > 0 for c in checks if c["on_screen"])
        for _ in range(8):
            env.step(1)
        second = observer.observe(env.unwrapped.ale.getRAM(), 136)
        assert second["player"][1] < first["player"][1]
        assert second["history"][0]["player"] == first["player"]
        assert first["history"] == []
        assert [a["ale_meaning"] for a in first["candidate_actions"]] == ["NOOP", "UP", "DOWN"]


def test_motion_rule_distinguishes_approaching_from_receding():
    observer = Observer()
    ram = np.zeros(128, dtype=np.uint8)
    ram[14] = 153  # player top y=40, just below lane zero y=27..37
    ram[117] = 19  # previous car x=16
    observer.observe(ram, 0)
    ram[117] = 35  # car x=32, approaching player x44..50
    approaching = observer.observe(ram, 16)
    assert literal(approaching) == (0, "wait-moving")
    approaching["history"][0]["cars"][0]["bbox"][0] = 48
    assert literal(approaching) == (1, "advance")


def test_program_keeps_actions_and_excludes_labels():
    obs = Observer().observe(np.zeros(128, dtype=np.uint8), 0)
    request = FreewayProgram().request(obs, "test")
    assert set(request["questions"]["next_action"]["criteria"]) == {"NOOP", "UP", "DOWN"}
    assert "branch" not in request["state"]["observation"]
    with pytest.raises(ValueError):
        FreewayProgram(action_criteria={"UP": "Only up"})
    assert prefix_length(410) == prefix_length(410)
    assert 128 <= prefix_length(411) < 256


def test_budget_is_durable_and_cannot_reopen(tmp_path):
    from jev_atari.freeway_research import Budget
    from jev_atari.io import read_json, write_json
    from jev_atari.models import BudgetExceeded

    path = tmp_path / "budget.json"
    budget = Budget(path, 2, clock=lambda: 100)
    budget.reserve()
    resumed = Budget(path, 2, clock=lambda: 101)
    assert resumed.used == 1
    resumed.reserve()
    state = read_json(path)
    assert state["used"] == 2 and state["round_attempts"] == {"2": 2}
    state["closed"] = True
    write_json(path, state)
    with pytest.raises(BudgetExceeded):
        resumed.reserve()


def test_budget_round_cap_and_deadline(tmp_path):
    from jev_atari.freeway_research import Budget
    from jev_atari.io import read_json, write_json
    from jev_atari.models import BudgetExceeded

    path = tmp_path / "budget.json"
    budget = Budget(path, 2, clock=lambda: 100)
    budget.reserve()
    state = read_json(path)
    state["round_attempts"]["2"] = 1300
    write_json(path, state)
    with pytest.raises(BudgetExceeded):
        budget.reserve()
    with pytest.raises(BudgetExceeded):
        Budget(path, 3, clock=lambda: 86500).reserve()


def test_ten_round_mock_pipeline_and_audit(tmp_path, monkeypatch):
    """Exercise all round boundaries and final preservation with synthetic responses."""
    import json
    import sys
    from pathlib import Path

    import httpx

    from jev_atari import freeway
    from jev_atari import freeway_research as study
    from jev_atari.io import read_json, write_json
    from jev_atari.seaquest_pilot import PIN
    from jev_atari.seaquest_research import ResearchEvaluator

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setattr(freeway, "CAP", 272)
    monkeypatch.setattr(study, "revision", lambda: "synthetic-frozen")
    root = tmp_path / "study"
    monkeypatch.setattr(study, "ROOT", root)
    for seed in study.TRAIN:
        freeway.play(root / "round-01" / f"up-hold-16-seed-{seed}", seed, rule="up")
    write_json(root / "round-01" / "result.json", {"round": 1})

    def handler(request):
        body = json.loads(request.content)
        options = body["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": PIN,
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "UP",
                        "confidence": 1,
                        "probabilities": {k: int(k == "UP") for k in options},
                    }
                },
            },
        )

    monkeypatch.setattr(
        study,
        "ResearchEvaluator",
        lambda budget: ResearchEvaluator(
            budget, client=httpx.Client(transport=httpx.MockTransport(handler))
        ),
    )
    study.run(2)
    for number in range(3, 9):
        proposal = tmp_path / f"proposal-{number}.json"
        write_json(proposal, FreewayProgram(name=f"synthetic-{number}").to_dict())
        study.run(number, proposal, "Synthetic fixture, not live evidence")
    study.run(9)
    study.run(10)
    assert read_json(root / "budget.json")["closed"]
    assert read_json(root / "selection.json")["round"] == 3
    assert not read_json(root / "completion.json")["promoted"]
    with pytest.raises(ValueError):
        study.run(11)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from verify_freeway_research import verify

    result = verify(root, tmp_path / "audit.json")
    assert result["status"] == "verified" and result["episode_count"] == 32
