"""Synthetic transport only: study limits, provenance and complete video/replay evidence."""

import json
import sys
from pathlib import Path

import httpx
import pytest

from jev_atari import seaquest_research as study
from jev_atari.io import read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.seaquest_pilot import PIN, PilotEvaluator, SeaquestProgram


def test_durable_round_budget_survives_reopen_and_closes(tmp_path):
    path = tmp_path / "budget.json"
    first = study.ResearchBudget(path, 1, clock=lambda: 10)
    first.reserve()
    second = study.ResearchBudget(path, 2, clock=lambda: 11)
    assert second.used == 1
    second.reserve()
    state = read_json(path)
    assert state["round_attempts"] == {"1": 1, "2": 1}
    state["round_attempts"]["2"] = 2000
    write_json(path, state)
    with pytest.raises(BudgetExceeded):
        second.reserve()
    third = study.ResearchBudget(path, 3, clock=lambda: 10 + study.LIVE_SECONDS)
    with pytest.raises(BudgetExceeded):
        third.reserve()
    state["closed"] = True
    write_json(path, state)
    with pytest.raises(BudgetExceeded):
        first.reserve()


def test_no_action_mask_and_program_roundtrip():
    criteria = {n: f"Select {n} when its stated motion is needed." for n in study.NAMES}
    p = study.CriteriaProgram(name="synthetic", guidance="Synthetic test", action_criteria=criteria)
    assert study.load_program(p.to_dict()).hash == p.hash
    with pytest.raises(ValueError):
        study.CriteriaProgram(action_criteria={"NOOP": "wait"})
    assert study.prefix_actions(320) != study.prefix_actions(321)


def test_prefix_video_and_raw_replay_with_mock_api(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setattr(study, "DECISIONS", 3)
    budget = study.ResearchBudget(tmp_path / "budget.json", 1)
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert body["state"]["observation"]["raw_frame"] >= 256
        assert read_json(budget.path)["used"] == len(calls)
        options = body["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": PIN,
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "DOWNFIRE",
                        "confidence": 1,
                        "probabilities": {k: int(k == "DOWNFIRE") for k in options},
                    }
                },
            },
        )

    ev = PilotEvaluator(budget, client=httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        path = tmp_path / "episode"
        summary = study.play_episode(path, 320, ev, "synthetic", SeaquestProgram())
    finally:
        ev.close()
    assert summary["status"] == "complete" and summary["agent_decisions"] == 3
    assert summary["decisions"] == 67 and summary["frames"] == 268
    assert summary["controlled_frames"] == 12 and summary["api_attempts"] == 3
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from seaquest_observation_check import verify_episode

    assert verify_episode(path, tmp_path / "audit")["status"] == "verified"
    assert (path / "episode.mp4").stat().st_size > 0


def test_gate_needs_gain_and_no_seed_regression():
    def rows(values):
        return [
            {"seed": seed, "role": role, "summary": {"controlled_reward": value}}
            for seed, pair in zip((326, 327), values, strict=True)
            for role, value in zip(("baseline", "candidate"), pair, strict=True)
        ]

    assert study.paired_gate(rows(((80, 100), (80, 100))))["passed"]
    assert not study.paired_gate(rows(((80, 160), (80, 60))))["passed"]
    assert not study.paired_gate(rows(((80, 80), (80, 80))))["passed"]


def test_round_order_and_stop_before_any_model_call(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "source_revision", lambda: "frozen")
    write_json(tmp_path / "plan.json", {"source_revision": "frozen"})
    write_json(tmp_path / "results.json", {"status": "running", "rounds": []})
    with pytest.raises(ValueError, match="exactly once"):
        study.run_round(tmp_path, 2)
    write_json(tmp_path / "results.json", {"status": "running", "rounds": [{}] * 10})
    with pytest.raises(ValueError, match="exactly once"):
        study.run_round(tmp_path, 11)
    write_json(tmp_path / "results.json", {"status": "complete", "rounds": [{}] * 10})
    with pytest.raises(ValueError, match="closed"):
        study.run_round(tmp_path, 11)
    assert not list(tmp_path.glob("round-*"))


def test_520_continuation_replays_without_repeating_old_model_calls(tmp_path, monkeypatch):
    import shutil

    from jev_atari.models import ModelError

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setattr(study, "DECISIONS", 5)
    original = tmp_path / "original"
    budget = study.ResearchBudget(tmp_path / "budget.json", 4)
    original_requests = []

    def success(body):
        options = body["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": PIN,
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "DOWNFIRE",
                        "confidence": 1,
                        "probabilities": {k: int(k == "DOWNFIRE") for k in options},
                    }
                },
            },
        )

    def before(request):
        body = json.loads(request.content)
        original_requests.append(body)
        return success(body) if len(original_requests) <= 2 else httpx.Response(520)

    ev = PilotEvaluator(budget, client=httpx.Client(transport=httpx.MockTransport(before)))
    try:
        with pytest.raises(ModelError, match="520"):
            study.play_episode(original, 321, ev, "original-source", SeaquestProgram())
    finally:
        ev.close()
    assert budget.used == 3
    saved = {
        name: (original / name).read_bytes()
        for name in ("transitions.jsonl", "model-exchanges.jsonl", "episode.mp4", "summary.json")
    }
    resumed = tmp_path / "resumed"
    shutil.copytree(original, resumed)
    requests = []

    def after(request):
        body = json.loads(request.content)
        requests.append(body)
        assert read_json(budget.path)["used"] == 3 + len(requests)
        return httpx.Response(520) if len(requests) == 1 else success(body)

    ev = study.ResearchEvaluator(budget, client=httpx.Client(transport=httpx.MockTransport(after)))
    try:
        summary = study.play_episode(
            resumed, 321, ev, "continuation-source", SeaquestProgram(), resume=True
        )
    finally:
        ev.close()
    assert requests[0] == requests[1] == original_requests[-1]
    assert len(requests) == 4 and budget.used == 7
    assert summary["agent_decisions"] == 5 and summary["frames"] == 276
    assert summary["api_attempts"] == 7 and summary["status"] == "complete"
    for name, content in saved.items():
        assert (original / name).read_bytes() == content
    for name in ("transitions.jsonl", "model-exchanges.jsonl"):
        assert (resumed / name).read_bytes().startswith(saved[name])
    assert (resumed / "predecessor-episode.mp4").read_bytes() == saved["episode.mp4"]
    assert read_json(resumed / "continuation-replay.json")["frames"] == 264
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from seaquest_observation_check import verify_episode

    assert verify_episode(resumed, tmp_path / "resumed-audit")["status"] == "verified"

    damaged = tmp_path / "damaged"
    shutil.copytree(original, damaged)
    rows = [json.loads(s) for s in (damaged / "transitions.jsonl").read_text().splitlines()]
    rows[0]["frames"][0]["ram"][0] ^= 1
    (damaged / "transitions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    ev = study.ResearchEvaluator(budget, client=httpx.Client(transport=httpx.MockTransport(after)))
    try:
        with pytest.raises(AssertionError):
            study.play_episode(
                damaged, 321, ev, "continuation-source", SeaquestProgram(), resume=True
            )
    finally:
        ev.close()
    assert budget.used == 7
