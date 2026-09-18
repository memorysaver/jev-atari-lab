"""Versioned text parameters; reward anchors and aggregation stay in code."""

from dataclasses import asdict, dataclass

from jev_atari.io import digest
from jev_atari.policies import HEURISTIC_DESCRIPTION, HEURISTIC_VERSION

ANCHORS = (
    "The first scoring event within the complete horizon is the player losing a point.",
    "No scoring event occurs during the complete horizon.",
    "The first scoring event within the complete horizon is the player scoring a point.",
)


@dataclass(frozen=True)
class QuestionProgram:
    name: str
    horizon_frames: int
    guidance: str
    outcome_guidance: tuple[str, str, str] = ("", "", "")
    schema_version: str = "question-program-v1"

    def __post_init__(self) -> None:
        if self.schema_version != "question-program-v1":
            raise ValueError("Unsupported question program schema")
        if not isinstance(self.name, str) or not 1 <= len(self.name) <= 100:
            raise ValueError("program name must be 1–100 characters")
        if type(self.horizon_frames) is not int or not 4 <= self.horizon_frames <= 3600:
            raise ValueError("horizon_frames must be 4–3600")
        if not isinstance(self.guidance, str) or not 1 <= len(self.guidance) <= 4000:
            raise ValueError("guidance must be 1–4000 characters")
        if len(self.outcome_guidance) != 3 or any(
            not isinstance(x, str) or len(x) > 1000 for x in self.outcome_guidance
        ):
            raise ValueError("exactly three outcome hints of at most 1000 characters are required")

    @classmethod
    def from_dict(cls, value: dict):
        allowed = {"name", "horizon_frames", "guidance", "outcome_guidance", "schema_version"}
        if set(value) - allowed:
            raise ValueError("Unknown question-program fields")
        value = dict(value)
        if "outcome_guidance" in value:
            if not isinstance(value["outcome_guidance"], (list, tuple)):
                raise ValueError("outcome_guidance must be an array")
            value["outcome_guidance"] = tuple(value["outcome_guidance"])
        return cls(**value)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def hash(self) -> str:
        return digest(self.to_dict())

    def request(self, observation: dict, model: str) -> dict:
        questions = {}
        for action in observation["candidate_actions"]:
            instructions = (
                f"Evaluate candidate action {action['id']}: {action['ale_meaning']} "
                f"({action['effect']}) requested for {action['hold_raw_frames']} raw frames. "
                f"Predict the first scoring event within {self.horizon_frames} raw frames "
                "from the current state, including this action. After this action follow "
                "the continuation policy in task_contract. Higher levels mean better outcomes "
                "for the player controlling the RIGHT paddle. "
                "Use only available observations; missing velocity is unknown, not zero. "
                "Keep the outcome definitions unchanged. Evaluation guidance: " + self.guidance
            )
            questions[f"action_{action['id']}"] = {
                "type": "score",
                "instructions": instructions,
                "criteria": [
                    {"outcome": anchor, "evidence_guidance": hint}
                    for anchor, hint in zip(ANCHORS, self.outcome_guidance, strict=True)
                ],
            }
        return {
            "model": model,
            "state": {
                "observation": observation,
                "task_contract": {
                    "player_side": "right",
                    "outcome_horizon_raw_frames": self.horizon_frames,
                    "continuation_policy_id": HEURISTIC_VERSION,
                    "continuation_policy": HEURISTIC_DESCRIPTION,
                    "target": "first-point outcome: loss=-1, no event=0, gain=1",
                },
            },
            "questions": questions,
        }


DEFAULT_PROGRAM = QuestionProgram(
    name="pong-baseline-v1",
    horizon_frames=240,
    guidance=(
        "Consider ball direction and speed, paddle position, and the requested action. "
        "Use the recent history to distinguish approaching and departing motion. "
        "Account for uncertainty and sticky actions."
    ),
)
