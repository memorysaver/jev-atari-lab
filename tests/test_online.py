import json
from copy import deepcopy

import httpx
import pytest

from jev_atari.choice import ActionPolicy, ActionProgram, ChoiceEvaluator
from jev_atari.environment import Protocol
from jev_atari.experiment import play
from jev_atari.io import read_json, write_json
from jev_atari.online import (
    ReplayPrefixEvaluator,
    policy_feedback,
    run_policy_suite,
    select_policy_candidate,
    trajectory_diagnostics,
)
from jev_atari.policies import HeuristicPolicy


def test_point_window_stops_exactly_at_event(tmp_path):
    summary = play(
        Protocol(),
        HeuristicPolicy(),
        seed=0,
        decisions=1000,
        point_limit=1,
        out=tmp_path / "point",
    )
    assert summary["end_reason"] == "point_limit"
    assert summary["points_scored"] + summary["points_lost"] == 1
    assert summary["truncated"] and not summary["terminated"]
    last = json.loads((tmp_path / "point/transitions.jsonl").read_text().splitlines()[-1])
    assert sum(last["rewards"]) != 0


def test_online_suite_ledger_counts_are_per_episode_and_feedback_is_train_only(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-token")

    def handler(request):
        questions = json.loads(request.content)["questions"]
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "NOOP",
                        "confidence": 1,
                        "probabilities": {
                            k: int(k == "NOOP") for k in questions["next_action"]["criteria"]
                        },
                    }
                },
                "usage": {"input_tokens": 10, "output_tokens": 1},
            },
        )

    evaluator = ChoiceEvaluator(
        model="test-model",
        max_calls=4,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        suite = run_policy_suite(
            Protocol(),
            ActionPolicy(evaluator, ActionProgram()),
            seeds=[20, 21],
            decisions=2,
            point_limit=5,
            out=tmp_path / "suite",
            evaluator=evaluator,
        )
        assert suite["status"] == "complete"
        assert not suite["all_reached_point_limit"]
        assert [e["end_reason"] for e in suite["episodes"]] == ["decision_limit"] * 2
        assert [e["api_attempts"] for e in suite["episodes"]] == [2, 2]
        assert suite["api_attempts"] == 4
        assert suite["usage"] == {"input_tokens": 40, "output_tokens": 4}
        assert len(read_json(tmp_path / "suite/seed-21/api-ledger.json")) == 2
        packet = policy_feedback(tmp_path / "suite/suite.json")
        assert packet["split"] == "train"
        replay = ReplayPrefixEvaluator(evaluator, tmp_path / "suite/seed-20/transitions.jsonl")
        observation = replay.rows[0]["observation"]
        with pytest.raises(ValueError, match="observation or program"):
            replay.evaluate({"different": True}, ActionProgram())
        with pytest.raises(ValueError, match="observation or program"):
            replay.evaluate(observation, ActionProgram(name="changed"))
        assert replay.replayed == 0
        prediction = replay.evaluate(observation, ActionProgram())
        assert prediction["replayed_prefix"]
        assert evaluator.api.budget.used == 4  # Verified replay makes no paid request.
        suite["split"] = "development"
        write_json(tmp_path / "suite/suite.json", suite)
        with pytest.raises(ValueError, match="training only"):
            policy_feedback(tmp_path / "suite/suite.json")
    finally:
        evaluator.close()


def test_policy_gate_requires_actual_reward_improvement_without_seed_regression():
    baseline = {
        "kind": "online-policy-suite-v1",
        "status": "complete",
        "split": "development",
        "seeds": [26, 27],
        "protocol": {"hold": 4},
        "max_decisions": 500,
        "point_limit": 5,
        "backend": "jev",
        "requested_model": "pinned",
        "response_models": ["pinned"],
        "selection_rule": "probability-argmax-provider-tie-v1",
        "all_reached_point_limit": True,
        "program": ActionProgram().to_dict(),
        "episodes": [{"seed": 26, "reward": -5}, {"seed": 27, "reward": -3}],
    }
    candidate = deepcopy(baseline)
    candidate["program"]["name"] = "candidate"
    assert not select_policy_candidate(baseline, candidate)["accepted"]
    candidate["episodes"][0]["reward"] = -3
    assert select_policy_candidate(baseline, candidate)["accepted"]
    candidate["episodes"][1]["reward"] = -5
    assert (
        "per_seed_reward_regression"
        in select_policy_candidate(baseline, candidate)["rejection_reasons"]
    )
    candidate["all_reached_point_limit"] = False
    assert (
        "incomplete_point_windows"
        in select_policy_candidate(baseline, candidate)["rejection_reasons"]
    )
    candidate["split"] = "test"
    with pytest.raises(ValueError, match="development only"):
        select_policy_candidate(baseline, candidate)


def test_policy_suite_rejects_mixed_seed_splits_before_output(tmp_path):
    with pytest.raises(ValueError, match="one split"):
        run_policy_suite(
            Protocol(),
            HeuristicPolicy(),
            seeds=[20, 26],
            decisions=10,
            point_limit=1,
            out=tmp_path / "bad",
        )
    assert not (tmp_path / "bad").exists()


def test_return_proxy_excludes_left_side_bounce_and_point_reset(tmp_path):
    rows = []
    for x, vx, reward in [
        (132, 1, 0),
        (136, -1, 0),
        (22, 1, 0),
        (20, -1, 0),
        (138, 1, 1),
        (135, -1, 0),
    ]:
        rows.append(
            {
                "observation": {
                    "objects": [
                        {"id": "ball", "bbox": [x, 100, 2, 4], "velocity": [vx, 0]},
                        {"id": "player", "bbox": [140, 100, 4, 15]},
                    ]
                },
                "action": 0,
                "rewards": [reward],
                "prediction": {},
            }
        )
    path = tmp_path / "trace.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    assert trajectory_diagnostics(path)["estimated_right_paddle_returns"] == 1
