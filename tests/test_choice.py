import json
from copy import deepcopy

import httpx
import pytest

from jev_atari.choice import (
    OUTCOMES,
    ActionPolicy,
    ActionProgram,
    ChoiceEvaluator,
    OutcomeChoiceProgram,
    validate_choices,
)
from jev_atari.environment import Pong, Protocol
from jev_atari.experiment import evaluate_actions, play
from jev_atari.models import ModelError
from jev_atari.program import DEFAULT_PROGRAM


@pytest.fixture
def observation():
    with Pong(Protocol(noop_max=0)) as env:
        return env.reset(0)


def answer(questions):
    return {
        "model": "test-model",
        "answers": {
            name: {
                "type": "choice",
                "choice": list(question["criteria"])[0],
                "probabilities": {
                    option: float(index == 0) for index, option in enumerate(question["criteria"])
                },
                "confidence": 1.0,
            }
            for name, question in questions.items()
        },
    }


def test_direct_action_has_one_question_and_no_future_outcome_contract(observation):
    program = ActionProgram()
    request = program.request(observation, "test")
    assert request["state"] == {"observation": observation}
    assert list(request["questions"]) == ["next_action"]
    assert len(request["questions"]["next_action"]["criteria"]) == 6
    assert "up movement" in request["questions"]["next_action"]["criteria"]["RIGHT"]
    assert ActionProgram.from_dict(json.loads(json.dumps(program.to_dict()))).hash == program.hash


def test_outcome_choice_preserves_state_horizon_and_anchors(observation):
    original = DEFAULT_PROGRAM.request(observation, "test")
    program = OutcomeChoiceProgram()
    request = program.request(observation, "test")
    assert request["state"] == original["state"]
    assert program.hash != DEFAULT_PROGRAM.hash
    assert program.horizon_frames == DEFAULT_PROGRAM.horizon_frames
    for name, question in request["questions"].items():
        assert question["type"] == "choice"
        assert list(question["criteria"]) == list(OUTCOMES)
        assert list(question["criteria"].values()) == original["questions"][name]["criteria"]


@pytest.mark.parametrize(
    "tamper", ["extra", "missing", "unknown", "sum", "nan", "confidence", "argmax"]
)
def test_invalid_choices_are_rejected(observation, tamper):
    questions = ActionProgram().request(observation, "test")["questions"]
    response = answer(questions)
    item = response["answers"]["next_action"]
    if tamper == "extra":
        response["answers"]["unexpected"] = item
    elif tamper == "missing":
        del item["probabilities"]["NOOP"]
    elif tamper == "unknown":
        item["choice"] = "TELEPORT"
    elif tamper == "sum":
        item["probabilities"]["NOOP"] = 0.9
    elif tamper == "nan":
        item["probabilities"]["NOOP"] = float("nan")
    elif tamper == "confidence":
        item["confidence"] = 2
    else:
        item["choice"] = "RIGHT"
    with pytest.raises(ModelError, match="Malformed Jev Choice"):
        validate_choices(response, questions)


def test_six_option_rounding_and_tied_choice(observation):
    questions = ActionProgram().request(observation, "test")["questions"]
    response = answer(questions)
    item = response["answers"]["next_action"]
    item["probabilities"] = {option: 0.17 for option in item["probabilities"]}
    item["choice"] = "RIGHT"  # Provider may select any tied maximum.
    result = validate_choices(response, questions)["next_action"]
    assert sum(result["probabilities"].values()) == pytest.approx(1)
    assert result["reported_probabilities"]["NOOP"] == 0.17
    assert result["choice"] == "RIGHT"
    item["probabilities"] = {option: 0.0 for option in item["probabilities"]}
    item["probabilities"].update(RIGHT=0.49999999999999994, NOOP=0.5)
    assert validate_choices(response, questions)["next_action"]["choice"] == "RIGHT"


def test_direct_actor_uses_probability_argmax_when_provider_choice_disagrees(observation):
    questions = ActionProgram().request(observation, "test")["questions"]
    response = answer(questions)
    item = response["answers"]["next_action"]
    item.update(
        choice="NOOP",
        probabilities={
            "NOOP": 0.45999999999999996,
            "FIRE": 0.0,
            "RIGHT": 0.05,
            "LEFT": 0.47,
            "RIGHTFIRE": 0.0,
            "LEFTFIRE": 0.02,
        },
    )
    with pytest.raises(ModelError):
        validate_choices(response, questions)
    result = validate_choices(response, questions, prefer_probabilities=True)["next_action"]
    assert result["choice"] == "LEFT"
    assert result["reported_choice"] == "NOOP"
    assert not result["choice_matches_probabilities"]


def test_choice_critic_converts_outcome_probabilities_to_value(monkeypatch, observation):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    def handler(request):
        questions = json.loads(request.content)["questions"]
        response = answer(questions)
        for item in response["answers"].values():
            item.update(choice="gain", probabilities={"loss": 0.1, "no_event": 0.3, "gain": 0.6})
        return httpx.Response(200, json=response)

    evaluator = ChoiceEvaluator(
        model="test-model", max_calls=1, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    try:
        prediction = evaluator.evaluate(observation, OutcomeChoiceProgram())
        assert prediction["answers"][0]["q"] == pytest.approx(0.5)
        assert prediction["prediction_type"] == "outcome-choice"
    finally:
        evaluator.close()


def test_invalid_choice_diagnostics_do_not_echo_response_text(monkeypatch, observation):
    monkeypatch.setenv("TYPESAFE_API_KEY", "private-test-token")

    def handler(request):
        payload = answer(json.loads(request.content)["questions"])
        payload["answers"]["next_action"]["choice"] = "private-test-token"
        payload["answers"]["next_action"]["probabilities"]["NOOP"] = "private-test-token"
        return httpx.Response(200, json=payload)

    evaluator = ChoiceEvaluator(
        model="test-model", max_calls=1, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(ModelError):
            evaluator.evaluate(observation, ActionProgram())
        diagnostics = evaluator.ledger[-1]["choice_validation_failure"]["next_action"]
        assert diagnostics["known_choice"] is None
        assert diagnostics["probabilities"]["NOOP"] is None
        assert "private-test-token" not in json.dumps(evaluator.ledger)
    finally:
        evaluator.close()


def test_action_preferences_never_become_value_or_brier(monkeypatch, observation, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    def handler(request):
        return httpx.Response(200, json=answer(json.loads(request.content)["questions"]))

    evaluator = ChoiceEvaluator(
        model="test-model", max_calls=4, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    program = ActionProgram()
    data = {
        "manifest": {
            "dataset_hash": "fixture",
            "split": "train",
            "protocol": {"protocol_hash": "fixture"},
            "horizon_frames": 240,
        },
        "roots": [
            {
                "root_id": "one",
                "root_fingerprint": "fixture",
                "seed": 0,
                "observation": observation,
                "outcomes": {
                    str(a): {"label": -1 if a == 0 else 1, "censored": False} for a in range(6)
                },
            }
        ],
    }
    try:
        report = evaluate_actions(data, program, evaluator)
        assert report["metrics"]["sampled_regret"] == 2
        assert "brier" not in report["metrics"] and "mae" not in report["metrics"]
        prediction = report["rows"][0]["prediction"]
        assert "answers" not in prediction and "q" not in prediction
        assert prediction["action_probabilities"][0] == 1
        censored = deepcopy(data)
        censored["roots"][0]["outcomes"]["0"].update(censored=True, label=None)
        report = evaluate_actions(censored, program, evaluator)
        assert report["rows"][0]["observed_label"] is None
        assert report["metrics"]["sampled_regret"] is None
        summary = play(
            Protocol(noop_max=0),
            ActionPolicy(evaluator, program),
            seed=0,
            decisions=2,
            out=tmp_path / "play",
            evaluator=evaluator,
        )
        assert summary["status"] == "complete" and summary["decisions"] == 2
    finally:
        evaluator.close()
