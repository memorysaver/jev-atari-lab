"""Baseline policies operate on exactly the same observable object state."""

import random

HEURISTIC_VERSION = "track-ball-center-v1"
HEURISTIC_DESCRIPTION = (
    "After the first candidate action, follow track-ball-center-v1: at each decision, "
    "if ball or player is absent choose NOOP; otherwise compare bounding-box center y. "
    "If ball center is more than 2 pixels above paddle center choose RIGHT (moves up); "
    "if more than 2 below choose LEFT (moves down); otherwise NOOP. "
    "Repeat each requested action for the configured hold_frames. No future lookahead."
)


class HeuristicPolicy:
    name = HEURISTIC_VERSION

    def __init__(self, deadband_pixels: int = 2):
        if type(deadband_pixels) is not int or deadband_pixels < 0:
            raise ValueError("deadband_pixels must be a nonnegative integer")
        self.deadband_pixels = deadband_pixels
        if deadband_pixels != 2:
            self.name = f"track-ball-center-{deadband_pixels}px-v1"

    def choose(self, observation: dict) -> tuple[int, dict]:
        objects = {o["id"]: o for o in observation["objects"]}
        ball, player = objects["ball"]["bbox"], objects["player"]["bbox"]
        action = 0
        if ball is not None and player is not None:
            delta = ball[1] + ball[3] / 2 - player[1] - player[3] / 2
            if delta < -self.deadband_pixels:
                action = 2
            elif delta > self.deadband_pixels:
                action = 3
        return action, {"policy": self.name}


class RandomPolicy:
    name = "random-v1"

    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def choose(self, observation: dict) -> tuple[int, dict]:
        return self.rng.choice([a["id"] for a in observation["candidate_actions"]]), {
            "policy": self.name,
            "selection_probability": 1 / 6,
        }


class InterceptPolicy:
    """Predict a right-paddle intercept from observable velocity and reflected walls."""

    name = "reflected-intercept-4px-v1"
    deadband_pixels = 4
    # Approximate playfield from the existing object adapter, not hidden RAM velocity.
    top = 34
    bottom = 194

    def choose(self, observation: dict) -> tuple[int, dict]:
        objects = {o["id"]: o for o in observation["objects"]}
        ball, player = objects["ball"], objects["player"]["bbox"]
        box = ball["bbox"]
        if box is None or player is None:
            return 0, {"policy": self.name, "target_y": None, "mode": "missing-object"}
        x, y = box[0] + box[2] / 2, box[1] + box[3] / 2
        target, mode = y, "track-without-velocity"
        velocity = ball.get("velocity") if ball.get("velocity_valid") else None
        if velocity and velocity[0] > 0:
            # Ball's leading edge meets the paddle's left edge. Reflect its center.
            dt = max(0, (player[0] - box[2] / 2 - x) / velocity[0])
            low, high = self.top + box[3] / 2, self.bottom - box[3] / 2
            span = high - low
            offset = (y + velocity[1] * dt - low) % (2 * span)
            target = low + (offset if offset <= span else 2 * span - offset)
            mode = "predicted-intercept"
        elif velocity and velocity[0] < 0:
            target, mode = (self.top + self.bottom) / 2, "recenter-away"
        delta = target - player[1] - player[3] / 2
        action = 2 if delta < -self.deadband_pixels else 3 if delta > self.deadband_pixels else 0
        return action, {"policy": self.name, "target_y": target, "mode": mode}
