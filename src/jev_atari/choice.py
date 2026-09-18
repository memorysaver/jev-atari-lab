"""Choice primitives for a categorical critic and a direct action policy.

Action-choice probabilities are preferences over actions, never outcome probabilities
or Q values. The outcome-choice control preserves the critic's state and target.
"""

import math
import time
from dataclasses import asdict, dataclass

from jev_atari.io import digest
from jev_atari.models import JevEvaluator, ModelError
from jev_atari.program import DEFAULT_PROGRAM, QuestionProgram

OUTCOMES = ("loss", "no_event", "gain")


@dataclass(frozen=True)
class OutcomeChoiceProgram:
    base: QuestionProgram = DEFAULT_PROGRAM

    @property
    def horizon_frames(self):
        return self.base.horizon_frames

    @property
    def name(self):
        return f"{self.base.name}-outcome-choice"

    def to_dict(self):
        return {"schema_version": "outcome-choice-program-v1", "base": self.base.to_dict()}

    @property
    def hash(self):
        return digest(self.to_dict())

    def request(self, observation: dict, model: str) -> dict:
        request = self.base.request(observation, model)
        for question in request["questions"].values():
            question["type"] = "choice"
            question["criteria"] = dict(zip(OUTCOMES, question["criteria"], strict=True))
            question["instructions"] = question["instructions"].replace(
                "Higher levels mean better outcomes for the player controlling the RIGHT paddle. ",
                "Choose the first-event category for the player controlling the RIGHT paddle. ",
            )
        return request


@dataclass(frozen=True)
class ActionProgram:
    name: str = "pong-action-choice-v1"
    guidance: str = (
        "Which available action should the RIGHT paddle take now to return the ball? "
        "Choose for the next requested action duration using current positions and recent motion."
    )
    schema_version: str = "action-choice-program-v1"

    def __post_init__(self):
        if self.schema_version != "action-choice-program-v1":
            raise ValueError("Unsupported action program schema")
        if not isinstance(self.name, str) or not 1 <= len(self.name) <= 100:
            raise ValueError("Action program name must be 1–100 characters")
        if not isinstance(self.guidance, str) or not 1 <= len(self.guidance) <= 2000:
            raise ValueError("Action guidance must be 1–2000 characters")

    @classmethod
    def from_dict(cls, value: dict):
        if set(value) - {"name", "guidance", "schema_version"}:
            raise ValueError("Unknown action program fields")
        return cls(**value)

    def to_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return digest(self.to_dict())

    def request(self, observation: dict, model: str) -> dict:
        return {
            "model": model,
            "state": {"observation": observation},
            "questions": {
                "next_action": {
                    "type": "choice",
                    "instructions": {
                        "question": self.guidance,
                        "read": "`observation.objects`, `observation.history` and "
                        "`observation.candidate_actions`",
                        "coordinates": "x increases right; y increases down. Follow the action "
                        "effect descriptions, not the direction implied by joystick names.",
                    },
                    "criteria": {
                        action["ale_meaning"]: (
                            f"{action['effect']} movement of the RIGHT paddle for "
                            f"{action['hold_raw_frames']} raw frames (action {action['id']})."
                        )
                        for action in observation["candidate_actions"]
                    },
                }
            },
        }


def validate_choices(payload: dict, questions: dict, *, prefer_probabilities=False) -> dict:
    try:
        if not isinstance(payload.get("model"), str) or not payload["model"]:
            raise ValueError("Missing model")
        if set(payload["answers"]) != set(questions):
            raise ValueError("Missing or extra questions")
        answers = {}
        for name, question in questions.items():
            item = payload["answers"][name]
            options = list(question["criteria"])
            if item["type"] != "choice" or set(item["probabilities"]) != set(options):
                raise ValueError("Incorrect options")
            probabilities = {option: float(item["probabilities"][option]) for option in options}
            confidence = float(item["confidence"])
            if any(
                not math.isfinite(x) or not 0 <= x <= 1
                for x in [*probabilities.values(), confidence]
            ):
                raise ValueError("Invalid probability")
            total = sum(probabilities.values())
            rounded = all(abs(x - round(x, 2)) < 1e-10 for x in probabilities.values())
            tolerance = len(options) * 0.005 + 1e-7 if rounded else 1e-4
            if total <= 0 or abs(total - 1) > tolerance:
                raise ValueError("Invalid distribution")
            choice = item["choice"]
            if choice not in probabilities:
                raise ValueError("Unknown choice")
            consistent = probabilities[choice] + 1e-12 >= max(probabilities.values())
            if not consistent and not prefer_probabilities:
                raise ValueError("Choice is not a maximum-probability option")
            answers[name] = {
                "choice": choice if consistent else max(probabilities, key=probabilities.get),
                "reported_choice": choice,
                "choice_matches_probabilities": consistent,
                "probabilities": {option: value / total for option, value in probabilities.items()},
                "reported_probabilities": probabilities,
                "confidence": confidence,
            }
        return answers
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ModelError("Malformed Jev Choice answer; refusing to choose an action") from exc


class ChoiceEvaluator(JevEvaluator):
    def evaluate(self, observation: dict, program: ActionProgram | OutcomeChoiceProgram) -> dict:
        if not isinstance(program, (ActionProgram, OutcomeChoiceProgram)):
            raise ValueError("Choice evaluator requires an action or outcome Choice program")
        request = program.request(observation, self.model)
        start = time.monotonic()
        payload = self.api.post(request)
        try:
            choices = validate_choices(
                payload,
                request["questions"],
                prefer_probabilities=isinstance(program, ActionProgram),
            )
        except ModelError:
            # Only request-known option names and finite numbers, never response text.
            diagnostics = {}
            raw_answers = payload.get("answers", {})
            for name, question in request["questions"].items():
                raw = raw_answers.get(name, {}) if isinstance(raw_answers, dict) else {}
                if not isinstance(raw, dict):
                    continue
                raw_p = raw.get("probabilities", {})
                if not isinstance(raw_p, dict):
                    continue
                options = question["criteria"]
                choice = raw.get("choice")
                diagnostics[name] = {
                    "known_choice": choice
                    if isinstance(choice, str) and choice in options
                    else None,
                    "probabilities": {
                        key: value if type(value) in (int, float) and math.isfinite(value) else None
                        for key in options
                        for value in [raw_p.get(key)]
                    },
                }
            self.api.ledger[-1]["choice_validation_failure"] = diagnostics
            raise
        result = {
            "backend": self.backend,
            "requested_model": self.model,
            "response_model": payload["model"],
            "program_hash": program.hash,
            "usage": payload.get("usage", {}),
            "elapsed_seconds": time.monotonic() - start,
            "exchange_id": self.api.budget.used,
        }
        if isinstance(program, ActionProgram):
            answer = choices["next_action"]
            actions = {a["ale_meaning"]: a["id"] for a in observation["candidate_actions"]}
            result.update(
                prediction_type="action-choice",
                selection_rule="probability-argmax-provider-tie-v1",
                chosen_action=actions[answer["choice"]],
                action_probabilities={actions[k]: v for k, v in answer["probabilities"].items()},
                choice_answer=answer,
            )
        else:
            result["prediction_type"] = "outcome-choice"
            result["answers"] = {}
            for action in observation["candidate_actions"]:
                answer = choices[f"action_{action['id']}"]
                p = [answer["probabilities"][key] for key in OUTCOMES]
                result["answers"][action["id"]] = {
                    "probabilities": p,
                    "q": p[2] - p[0],
                    "confidence": answer["confidence"],
                    "choice_answer": answer,
                }
        return result


class ActionPolicy:
    selection_rule = "probability-argmax-provider-tie-v1"

    def __init__(self, evaluator: ChoiceEvaluator, program: ActionProgram):
        self.evaluator, self.program = evaluator, program
        self.name = f"{evaluator.backend}:{program.name}"

    def choose(self, observation: dict) -> tuple[int, dict]:
        result = self.evaluator.evaluate(observation, self.program)
        return result["chosen_action"], result
