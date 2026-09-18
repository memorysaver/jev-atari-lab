from copy import deepcopy

import httpx
import pytest

from jev_atari.environment import Pong, Protocol
from jev_atari.models import (
    BudgetExceeded,
    JevEvaluator,
    ModelError,
    ValuePolicy,
    validate_answers,
)
from jev_atari.program import DEFAULT_PROGRAM


@pytest.fixture
def observation():
    with Pong(Protocol(noop_max=0)) as env:
        return env.reset(0)


def response():
    return {
        "model": "test-pinned-jev",
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "answers": {
            f"action_{a}": {
                "type": "score",
                "score": 1.4,
                "confidence": 0.2,
                "probabilities": {"0": 0.1, "1": 0.4, "2": 0.5},
            }
            for a in range(6)
        },
    }


def test_every_question_identifies_action_and_keeps_reward_anchors(observation):
    request = DEFAULT_PROGRAM.request(observation, "test")
    assert len(request["questions"]) == 6
    for a in range(6):
        q = request["questions"][f"action_{a}"]
        assert f"candidate action {a}:" in q["instructions"]
        assert len(q["criteria"]) == 3
    assert request["state"]["task_contract"]["continuation_policy_id"] == "track-ball-center-v1"


def test_real_client_request_shape_and_bounded_retry(monkeypatch, observation):
    monkeypatch.setenv("TYPESAFE_API_KEY", "unit-test-placeholder")
    monkeypatch.setattr("jev_atari.models.time.sleep", lambda _: None)
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.path == "/v1/systemone"
        assert request.headers["Authorization"] == "Bearer unit-test-placeholder"
        return httpx.Response(429 if len(requests) == 1 else 200, json=response())

    evaluator = JevEvaluator(
        model="test", max_calls=2, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = evaluator.evaluate(observation, DEFAULT_PROGRAM)
    assert result["answers"][0]["q"] == pytest.approx(0.4)
    assert len(evaluator.ledger) == 2
    with pytest.raises(BudgetExceeded):
        evaluator.evaluate(observation, DEFAULT_PROGRAM)
    assert len(requests) == 2
    assert "unit-test-placeholder" not in str(evaluator.ledger)
    evaluator.close()


@pytest.mark.parametrize("mutation", ["missing", "nan", "bad_sum", "score", "extra", "confidence"])
def test_malformed_answers_are_not_executed(mutation):
    payload = deepcopy(response())
    item = payload["answers"]["action_0"]
    if mutation == "missing":
        del payload["answers"]["action_0"]
    elif mutation == "nan":
        item["probabilities"]["0"] = float("nan")
    elif mutation == "bad_sum":
        item["probabilities"]["0"] = 0.9
    elif mutation == "score":
        item["score"] = 0
    elif mutation == "extra":
        payload["answers"]["action_6"] = item
    else:
        item["confidence"] = 1.1
    with pytest.raises(ModelError):
        validate_answers(payload, list(range(6)))


def test_confidence_is_not_used_as_value(observation):
    class Evaluator:
        backend = "test"

        def evaluate(self, observation, program):
            return {
                "answers": {0: {"q": -0.9, "confidence": 1.0}, 1: {"q": 0.5, "confidence": 0.1}}
            }

    assert ValuePolicy(Evaluator(), DEFAULT_PROGRAM).choose(observation)[0] == 1


def test_http_error_does_not_echo_secrets(monkeypatch, observation):
    monkeypatch.setenv("TYPESAFE_API_KEY", "unit-secret")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(401, text="unit-secret"))
    )
    evaluator = JevEvaluator(model="test", max_calls=1, client=client)
    with pytest.raises(ModelError, match="HTTP 401") as exc:
        evaluator.evaluate(observation, DEFAULT_PROGRAM)
    assert "unit-secret" not in str(exc.value)
    evaluator.close()


def test_missing_key_fails_before_transport(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(ModelError, match="missing"):
        JevEvaluator(model="test", max_calls=1)


def test_rounded_live_scores_are_accepted_and_original_values_preserved():
    payload = response()
    item = payload["answers"]["action_0"]
    item.update(probabilities={"0": 0.47, "1": 0.10, "2": 0.43}, score=0.95)
    answer = validate_answers(payload, list(range(6)))[0]
    assert answer["reported_score"] == 0.95
    assert answer["score"] == pytest.approx(0.96)
    assert answer["q"] == pytest.approx(-0.04)
    item.update(probabilities={"0": 0.33, "1": 0.33, "2": 0.33}, score=1.0)
    answer = validate_answers(payload, list(range(6)))[0]
    assert sum(answer["probabilities"]) == pytest.approx(1)
    assert answer["reported_probabilities"] == [0.33, 0.33, 0.33]


def test_rounding_tolerance_does_not_accept_large_or_high_precision_errors():
    payload = response()
    item = payload["answers"]["action_0"]
    for probabilities, score in [
        ({"0": 0.32, "1": 0.32, "2": 0.32}, 1.0),
        ({"0": 0.47, "1": 0.10, "2": 0.43}, 0.93),
        ({"0": 0.331, "1": 0.331, "2": 0.331}, 1.0),
    ]:
        item.update(probabilities=probabilities, score=score)
        with pytest.raises(ModelError):
            validate_answers(payload, list(range(6)))
