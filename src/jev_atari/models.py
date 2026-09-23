"""Bounded HTTP clients. Tests inject MockTransport; no implicit live calls."""

import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from jev_atari.program import QuestionProgram


class ModelError(RuntimeError):
    pass


class BudgetExceeded(ModelError):
    pass


@dataclass
class CallBudget:
    max_calls: int
    used: int = 0

    def __post_init__(self):
        if self.max_calls < 1:
            raise ValueError("max_calls must be positive")

    def reserve(self) -> None:
        if self.used >= self.max_calls:
            raise BudgetExceeded(f"HTTP call budget exhausted ({self.max_calls})")
        self.used += 1


class JsonAPI:
    def __init__(
        self,
        endpoint: str,
        key: str,
        budget: CallBudget,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 2,
        retry_transport: bool = False,
    ):
        if not key:
            raise ModelError("Required API key environment variable is missing")
        self.endpoint, self.key, self.budget = endpoint, key, budget
        self.client = client or httpx.Client(timeout=60, follow_redirects=False)
        self.max_retries = max_retries
        self.retry_transport = retry_transport
        self.retry_statuses = {429, 500, 502, 503, 504, 529}
        self.ledger: list[dict] = []
        self.trace_path: Path | None = None

    def record_exchange(self, entry: dict, request: dict, response: dict | None = None):
        """Persist JSON bodies, never headers or unsuccessful HTTP response bodies."""
        if self.trace_path is None:
            return
        row = {
            "exchange_id": self.budget.used,
            "request": request,
            "response": response,
            "transport": entry,
        }
        # A provider may echo input or credentials. Even successful bodies are redacted.
        serialized = json.dumps(row, allow_nan=False).replace(self.key, "[REDACTED]")
        with self.trace_path.open("a") as log:
            log.write(serialized + "\n")
            log.flush()

    def post(self, payload: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            self.budget.reserve()
            start = time.monotonic()
            entry = {"attempt": attempt + 1, "requested_model": payload["model"]}
            try:
                response = self.client.post(
                    self.endpoint,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.key}"},
                )
            except httpx.HTTPError:
                entry.update(status="transport_error", elapsed_seconds=time.monotonic() - start)
                self.ledger.append(entry)
                self.record_exchange(entry, payload)
                if self.retry_transport and attempt < self.max_retries:
                    time.sleep(min(0.25 * 2**attempt, 1))
                    continue
                raise ModelError("Model transport failed; no action was executed") from None
            entry.update(status=response.status_code, elapsed_seconds=time.monotonic() - start)
            self.ledger.append(entry)
            if response.status_code in self.retry_statuses:
                if attempt < self.max_retries:
                    self.record_exchange(entry, payload)
                    time.sleep(min(0.25 * 2**attempt, 1))
                    continue
            if not response.is_success:
                self.record_exchange(entry, payload)
                # Error bodies can echo credentials/request content: do not log them.
                raise ModelError(f"Model API returned HTTP {response.status_code}")
            try:
                value = response.json()
            except ValueError:
                self.record_exchange(entry, payload)
                raise ModelError("Model API returned invalid JSON") from None
            if not isinstance(value, dict):
                self.record_exchange(entry, payload)
                raise ModelError("Model API response must be an object")
            entry["response_model"] = value.get("model")
            entry["usage"] = value.get("usage", {})
            self.record_exchange(entry, payload, value)
            return value
        raise AssertionError("unreachable")

    def close(self):
        self.client.close()


def validate_answers(payload: dict, ids: list[int]) -> dict[int, dict]:
    try:
        if not isinstance(payload.get("model"), str) or not payload["model"]:
            raise ValueError("missing response model identifier")
        raw = payload["answers"]
        if set(raw) != {f"action_{i}" for i in ids}:
            raise ValueError("missing or extra answers")
        answers = {}
        for action in ids:
            item = raw[f"action_{action}"]
            if item["type"] != "score" or set(item["probabilities"]) != {"0", "1", "2"}:
                raise ValueError("invalid answer schema")
            p = [float(item["probabilities"][str(i)]) for i in range(3)]
            score, confidence = float(item["score"]), float(item["confidence"])
            if any(not math.isfinite(x) or not 0 <= x <= 1 for x in [*p, confidence]):
                raise ValueError("invalid probability")
            # Live Jev 1.13 returns independently rounded two-decimal probabilities
            # and scores. Three +/-0.005 probability errors allow a sum error of
            # 0.015 and a weighted-index error of 0.015 + 0.005 for the score.
            rounded = all(abs(x - round(x, 2)) < 1e-10 for x in [*p, score])
            sum_tolerance = 0.0150001 if rounded else 1e-4
            score_tolerance = 0.0200001 if rounded else 1e-3
            total = sum(p)
            if abs(total - 1) > sum_tolerance:
                raise ValueError("probabilities do not sum to one")
            expected = p[1] + 2 * p[2]
            if (
                not math.isfinite(score)
                or not 0 <= score <= 2
                or abs(score - expected) > score_tolerance
            ):
                raise ValueError("score differs from expected rubric index")
            normalized = [x / total for x in p]
            answers[action] = {
                "probabilities": normalized,
                "confidence": confidence,
                "score": normalized[1] + 2 * normalized[2],
                "q": normalized[2] - normalized[0],
                "reported_probabilities": p,
                "reported_score": score,
            }
        return answers
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ModelError("Malformed Jev answer; refusing to choose an action") from exc


class JevEvaluator:
    backend = "jev"

    def __init__(self, *, model: str, max_calls: int, client: httpx.Client | None = None):
        self.model = model
        self.api = JsonAPI(
            "https://api.typesafe.ai/v1/systemone",
            os.environ.get("TYPESAFE_API_KEY", ""),
            CallBudget(max_calls),
            client=client,
        )

    def evaluate(self, observation: dict, program: QuestionProgram) -> dict:
        start = time.monotonic()
        payload = self.api.post(program.request(observation, self.model))
        answers = validate_answers(payload, [a["id"] for a in observation["candidate_actions"]])
        return {
            "backend": self.backend,
            "requested_model": self.model,
            "response_model": payload.get("model"),
            "program_hash": program.hash,
            "answers": answers,
            "usage": payload.get("usage", {}),
            "elapsed_seconds": time.monotonic() - start,
            "exchange_id": self.api.budget.used,
        }

    @property
    def ledger(self):
        return self.api.ledger

    def close(self):
        self.api.close()


class MockEvaluator:
    """Constant synthetic probabilities for plumbing only, never evidence of learning."""

    backend = "mock"
    model = "synthetic-constant-v1"

    def __init__(self, max_calls: int):
        self.budget = CallBudget(max_calls)
        self.ledger: list[dict] = []

    def evaluate(self, observation: dict, program: QuestionProgram) -> dict:
        self.budget.reserve()
        self.ledger.append({"status": "synthetic", "elapsed_seconds": 0, "usage": {}})
        return {
            "backend": "mock",
            "requested_model": self.model,
            "response_model": self.model,
            "program_hash": program.hash,
            "usage": {},
            "elapsed_seconds": 0,
            "answers": {
                a["id"]: {
                    "probabilities": [0.25, 0.5, 0.25],
                    "score": 1.0,
                    "q": 0.0,
                    "confidence": 0.0,
                }
                for a in observation["candidate_actions"]
            },
        }

    def close(self):
        pass


class ValuePolicy:
    def __init__(self, evaluator, program: QuestionProgram):
        self.evaluator, self.program = evaluator, program
        self.name = f"{evaluator.backend}:{program.name}"

    def choose(self, observation: dict) -> tuple[int, dict]:
        result = self.evaluator.evaluate(observation, self.program)
        # Stable smallest-id tie-break; confidence is deliberately not value.
        action = max(sorted(result["answers"]), key=lambda a: result["answers"][a]["q"])
        return action, result
