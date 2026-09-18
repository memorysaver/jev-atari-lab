import json

import httpx
import pytest

from jev_atari.choice import ActionProgram, ChoiceEvaluator
from jev_atari.controls import horizon_result, run_control_comparison
from jev_atari.environment import Protocol
from jev_atari.io import read_json
from jev_atari.models import BudgetExceeded, ModelError
from jev_atari.policies import HEURISTIC_VERSION, HeuristicPolicy
from jev_atari.replay import inspect_step, replay_episode


@pytest.mark.parametrize("gap,action", [(-5, 2), (-4, 0), (0, 0), (4, 0), (5, 3)])
def test_four_pixel_rule_boundary_and_action_semantics(gap, action):
    observation = {
        "objects": [
            {"id": "player", "bbox": [140, 100, 4, 12]},
            {"id": "ball", "bbox": [70, 104 + gap, 2, 4]},
        ]
    }
    assert HeuristicPolicy(4).choose(observation)[0] == action
    if abs(gap) == 4:
        assert HeuristicPolicy().choose(observation)[0] != action
    observation["objects"][1]["bbox"] = None
    assert HeuristicPolicy(4).choose(observation)[0] == 0
    assert HeuristicPolicy().name == HEURISTIC_VERSION


@pytest.mark.parametrize(
    "status,reason,terminal,actual,complete,tail",
    [
        ("complete", "decision_limit", False, 2000, True, 0),
        ("complete", "native_termination", True, 1501, True, 499),
        ("complete", "environment_truncation", False, 1501, False, 0),
        ("incomplete", "error", False, 500, False, 0),
        ("complete", "point_limit", False, 500, False, 0),
        ("complete", "decision_limit", False, 1996, False, 0),
    ],
)
def test_terminal_tail_never_fills_errors_or_incomplete_windows(
    status,
    reason,
    terminal,
    actual,
    complete,
    tail,
):
    result = horizon_result(
        {
            "status": status,
            "end_reason": reason,
            "terminated": terminal,
            "raw_frames": actual,
            "reward": -5,
        },
        2000,
    )
    assert result["evaluation_complete"] is complete
    assert result["absorbing_tail_frames"] == tail
    assert result["evaluation_reward"] == (-5 if complete else None)


def make_evaluator(monkeypatch, cap, *, retry=False, response_model="test-model"):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-token")
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        if retry and count == 1:
            return httpx.Response(503)
        question = json.loads(request.content)["questions"]["next_action"]
        return httpx.Response(
            200,
            json={
                "model": response_model,
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "NOOP",
                        "confidence": 1,
                        "probabilities": {key: int(key == "NOOP") for key in question["criteria"]},
                    }
                },
                "usage": {"input_tokens": 10, "output_tokens": 1},
            },
        )

    return ChoiceEvaluator(
        model="test-model",
        max_calls=cap,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def run(evaluator, out, *, frames=8):
    return run_control_comparison(
        Protocol(noop_max=0),
        baseline=ActionProgram(),
        candidate=ActionProgram(name="candidate"),
        seeds=[36, 37],
        frames=frames,
        evaluator=evaluator,
        out=out,
    )


def test_shared_budget_retry_exact_horizon_and_recorded_replay(tmp_path, monkeypatch):
    evaluator = make_evaluator(monkeypatch, 9, retry=True)
    try:
        report = run(evaluator, tmp_path / "run")
        assert report["status"] == "complete"
        assert report["api_attempts"] == 9  # Eight decisions plus one retry, across four arms.
        assert report["http_status_counts"] == {"503": 1, "200": 8}
        assert report["usage"] == {"input_tokens": 80, "output_tokens": 8}
        assert all(e["raw_frames"] == 8 for e in report["episodes"])
        assert all(e["end_reason"] == "decision_limit" for e in report["episodes"])
        assert [e["arm"] for e in report["episodes"]][-2:] == ["jev-vertical", "jev-original"]
        for e in report["episodes"]:
            path = tmp_path / "run" / e["arm"] / f"seed-{e['seed']}"
            assert read_json(path / "manifest.json")["point_limit"] is None
            replay = replay_episode(path, tmp_path / "verified" / e["arm"] / str(e["seed"]))
            assert replay["status"] == "verified"
            if e["arm"].startswith("jev-"):
                inspected = inspect_step(path, 0)
                assert inspected["input_origin"] == "recorded-json-exchange"
                assert inspected["response"]["model"] == "test-model"
        assert sum(e.get("api_attempts", 0) for e in report["episodes"]) == 9
    finally:
        evaluator.close()


def test_budget_exhaustion_preserves_partial_evidence_without_resetting_cap(tmp_path, monkeypatch):
    evaluator = make_evaluator(monkeypatch, 3)
    try:
        with pytest.raises(BudgetExceeded):
            run(evaluator, tmp_path / "run")
        report = read_json(tmp_path / "run/comparison.json")
        assert report["status"] == "incomplete"
        assert report["api_attempts"] == 3
        assert report["interrupted_episode"]["arm"] == "jev-vertical"
        assert report["interrupted_episode"]["raw_frames"] == 4
        assert report["interrupted_episode"]["evaluation_reward"] is None
        assert len(read_json(tmp_path / "run/api-ledger.json")) == 3
    finally:
        evaluator.close()


def test_model_change_is_recorded_but_never_executed(tmp_path, monkeypatch):
    evaluator = make_evaluator(monkeypatch, 8, response_model="different-model")
    try:
        with pytest.raises(ModelError, match="Response model changed"):
            run(evaluator, tmp_path / "run")
        report = read_json(tmp_path / "run/comparison.json")
        assert report["interrupted_episode"]["raw_frames"] == 0
        assert report["api_attempts"] == 1
        exchange = json.loads(
            (tmp_path / "run/jev-original/seed-36/model-exchanges.jsonl").read_text()
        )
        assert exchange["response"]["model"] == "different-model"
    finally:
        evaluator.close()


def test_invalid_horizon_is_rejected_before_any_call(tmp_path, monkeypatch):
    evaluator = make_evaluator(monkeypatch, 8)
    try:
        with pytest.raises(ValueError, match="multiple of hold_frames"):
            run(evaluator, tmp_path / "run", frames=7)
        assert evaluator.api.budget.used == 0
        assert not (tmp_path / "run").exists()
    finally:
        evaluator.close()
