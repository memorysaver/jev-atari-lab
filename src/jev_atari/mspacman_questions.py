"""Explicit one-question versus target-then-action Ms. Pac-Man comparison."""

import os
import time

from jev_atari.choice import validate_choices
from jev_atari.io import digest, read_json, write_json
from jev_atari.models import BudgetExceeded, JsonAPI, ModelError
from jev_atari.mspacman import NAMES, target
from jev_atari.openrouter import ENDPOINT

MODEL = "~typesafe/jev-latest"
PIN = "typesafe/jev-1.13-20260917"
MAX_CALLS = 1700
CONTRACT = (
    "Control Ms. Pac-Man for the next 8 raw frames using the given screen-coordinate observations. "
    "x increases right, y increases down. The maze is a graph of straight corridor_segments; "
    "side tunnels wrap horizontally on tunnel_rows. exits lists currently open cardinal "
    "directions and their endpoints up to 8 pixels away, not recommended moves. "
    "Unknown ghosts and occluded pellets are not known to be absent. Blue is a ghost appearance, "
    "not a remaining vulnerability timer. All nine native joystick actions remain available."
)
TARGET_RULE = (
    "If player.visible is false or exits is empty choose UNAVAILABLE. Otherwise, among visible "
    "normal ghosts, find the smallest Manhattan distance abs(dx)+abs(dy) from the player. "
    "If that distance is at most 32 choose that ghost ID, breaking ties by ID. "
    "If there is no such nearby ghost choose PELLETS."
)
ACTION_RULE = (
    "For UNAVAILABLE choose NOOP. For a selected ghost, choose the cardinal exit whose endpoint "
    "has greatest Manhattan distance from that ghost; break ties by exits order. "
    "For PELLETS, use corridor connectivity to choose a visible regular pellet with the shortest "
    "positive route distance, breaking target ties by pellet ID, and move along a shortest route "
    "toward it. Do not move directly through walls. If no reachable pellet exists choose NOOP. "
    "NOOP may retain movement; native diagonals combine joystick directions."
)
INTENTS = {
    "UNAVAILABLE": "Player or exits unavailable.",
    "PELLETS": "Pursue regular pellets.",
    **{f"ghost-{i}": f"Evade visible normal ghost-{i}." for i in range(4)},
}
ACTIONS = {name: f"Native {name} joystick input for 8 raw frames." for name in NAMES}
PROGRAM = {
    "version": "mspacman-direct-vs-target-action-v1",
    "contract": CONTRACT,
    "target_rule": TARGET_RULE,
    "action_rule": ACTION_RULE,
    "intent_criteria": INTENTS,
    "action_criteria": ACTIONS,
}


def reference_intent(obs):
    if not obs["player"]["visible"] or not obs["exits"]:
        return "UNAVAILABLE"
    obj, mode = target(obs)
    return obj["id"] if mode == "evade" else "PELLETS"


def request(obs, stage, intent=None, model=MODEL):
    if stage not in {"direct", "intent", "action"}:
        raise ValueError("Unknown question stage")
    observation = obs
    state = {"observation": observation}
    if stage == "intent":
        instructions = CONTRACT + " " + TARGET_RULE
        criteria = INTENTS
    elif stage == "direct":
        instructions = CONTRACT + " First apply this target rule internally: " + TARGET_RULE
        instructions += " Then choose the next action: " + ACTION_RULE
        criteria = ACTIONS
    else:
        if intent not in INTENTS:
            raise ValueError("A valid model-selected intent is required")
        state["selected_intent"] = intent
        instructions = CONTRACT + " The first model stage selected state.selected_intent. "
        instructions += "Execute that intent using this rule: " + ACTION_RULE
        criteria = ACTIONS
    return {
        "model": model,
        "state": state,
        "questions": {
            "decision": {"type": "choice", "instructions": instructions, "criteria": criteria}
        },
    }


class Budget:
    """Durable non-reopenable attempt, cost and wall-time allocation."""

    def __init__(self, path, *, clock=time.time):
        self.path, self.clock = path, clock
        if not path.exists():
            write_json(
                path,
                {
                    "max_calls": MAX_CALLS,
                    "used": 0,
                    "closed": False,
                    "started_at": clock(),
                    "max_seconds": 3600,
                    "reported_cost_usd": 0.0,
                    "cost_stop_usd": 2.0,
                },
            )
        self.used = read_json(path)["used"]
        self.max_calls = MAX_CALLS

    def reserve(self):
        state = read_json(self.path)
        if (
            state["closed"]
            or state["used"] >= state["max_calls"]
            or self.clock() - state["started_at"] >= state["max_seconds"]
            or state["reported_cost_usd"] >= state["cost_stop_usd"]
        ):
            raise BudgetExceeded("Ms. Pac-Man pilot budget is closed or exhausted")
        self.used = state["used"] + 1
        state["used"] = self.used
        write_json(self.path, state)

    def charge(self, cost):
        state = read_json(self.path)
        state["reported_cost_usd"] += cost
        write_json(self.path, state)

    def close(self, reason):
        state = read_json(self.path)
        state.update(closed=True, close_reason=reason)
        write_json(self.path, state)


class Policy:
    def __init__(self, root, *, model=MODEL, pin=PIN, client=None):
        self.model, self.pin = model, pin
        self.budget = Budget(root / "budget.json")
        self.api = JsonAPI(
            ENDPOINT,
            os.environ.get("OPENROUTER_API_KEY", ""),
            self.budget,
            client=client,
            max_retries=0,
            retry_transport=False,
        )
        self.offset = 0
        self.manifest = {
            "backend": "openrouter",
            "endpoint": ENDPOINT,
            "model": model,
            "expected_response_model": pin,
            "program": PROGRAM,
            "program_hash": digest(PROGRAM),
            "max_attempts": MAX_CALLS,
            "max_retries": 0,
            "max_seconds": 3600,
            "cost_stop_usd": 2.0,
        }

    def trace(self, path):
        path.mkdir(parents=True, exist_ok=True)
        self.api.trace_path = path / "model-exchanges.jsonl"
        self.offset = len(self.api.ledger)

    def ask(self, obs, stage, intent=None):
        body = request(obs, stage, intent, self.model)
        payload = self.api.post(body)
        cost = (payload.get("usage") or {}).get("cost", 0)
        self.budget.charge(cost or 0)
        if payload.get("model") != self.pin:
            raise ModelError("Response model mismatch; no action executed")
        answer = validate_choices(payload, body["questions"], prefer_probabilities=True)["decision"]
        return {
            "stage": stage,
            "exchange_id": self.budget.used,
            "answer": answer,
            "response_model": payload["model"],
            "usage": payload.get("usage", {}),
        }

    def choose(self, obs, arm):
        if arm == "direct":
            responses = [self.ask(obs, "direct")]
        elif arm == "two-stage":
            first = self.ask(obs, "intent")
            responses = [first, self.ask(obs, "action", first["answer"]["choice"])]
        else:
            raise ValueError("Unknown arm")
        return {
            "action": NAMES.index(responses[-1]["answer"]["choice"]),
            "responses": responses,
            "program_hash": digest(PROGRAM),
        }

    def resources(self):
        ledger = self.api.ledger[self.offset :]
        return {
            "http_attempts": len(ledger),
            "api_seconds": sum(r["elapsed_seconds"] for r in ledger),
            "reported_cost_usd": sum((r.get("usage") or {}).get("cost", 0) or 0 for r in ledger),
        }
