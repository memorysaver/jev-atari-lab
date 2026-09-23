"""Explicit OpenRouter Decisions transport with a required response-model pin."""

import os

import httpx

from jev_atari.choice import ChoiceEvaluator
from jev_atari.models import CallBudget, JsonAPI, ModelError

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"


class OpenRouterChoiceEvaluator(ChoiceEvaluator):
    backend = "openrouter"

    def __init__(
        self,
        *,
        model: str,
        expected_response_model: str,
        max_calls: int,
        client: httpx.Client | None = None,
    ):
        if not model.startswith(("typesafe/", "~typesafe/")):
            raise ValueError("OpenRouter Jev requires a typesafe/ or ~typesafe/ model ID")
        if not expected_response_model or not expected_response_model.startswith("typesafe/"):
            raise ValueError("OpenRouter requires an explicit --expected-response-model pin")
        self.model = model
        self.expected_response_model = expected_response_model
        self.api = JsonAPI(
            ENDPOINT,
            os.environ.get("OPENROUTER_API_KEY", ""),
            CallBudget(max_calls),
            client=client,
            max_retries=0,
            retry_transport=False,
        )

    @property
    def transport_manifest(self):
        return {
            "backend": self.backend,
            "endpoint": ENDPOINT,
            "requested_model": self.model,
            "expected_response_model": self.expected_response_model,
            "max_api_calls": self.api.budget.max_calls,
            "max_retries": 0,
        }

    def evaluate(self, observation, program):
        result = super().evaluate(observation, program)
        if result["response_model"] != self.expected_response_model:
            raise ModelError("OpenRouter response model changed; refusing to execute its action")
        result["expected_response_model"] = self.expected_response_model
        return result
