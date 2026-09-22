"""Literal training-only interpretations of the teacher's relative-motion hypothesis."""

import math

from jev_atari.question_diagnostics import reflect

RULES = ("track-4", "ball-lookahead-2", "relative-lookahead-2", "relative-unguarded-2")
SEEDS = (130, 131, 132, 133, 134, 135, 140, 141)
FRAMES = 2000
SOURCE_HASH = "67d2e249f331df8db6fe21a26369487bea5bd93ed2e36332e597fe859f5feef4"


def vertical_reversal(observation):
    history = observation.get("history", [])[-3:]
    if len(history) != 3:
        return None
    velocities = []
    for a, b in zip(history, history[1:], strict=False):
        before, after = a["boxes"].get("ball"), b["boxes"].get("ball")
        dt = b["offset_raw_frames"] - a["offset_raw_frames"]
        if before is None or after is None or dt <= 0:
            return None
        velocities.append((after[1] - before[1]) / dt)
    return velocities[0] * velocities[1] < 0


def velocity_y(obj):
    velocity = obj.get("velocity") if obj.get("velocity_valid") else None
    if (
        velocity is None
        or len(velocity) != 2
        or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in velocity)
    ):
        return None
    return velocity[1]


def interpret(observation, rule):
    if rule not in RULES:
        raise ValueError("Unknown relative-motion diagnostic rule")
    objects = {o["id"]: o for o in observation["objects"]}
    ball, player = objects.get("ball", {}), objects.get("player", {})
    b, p = ball.get("bbox"), player.get("bbox")
    result = {
        "rule": rule,
        "action": 0,
        "mode": "missing-object",
        "ball_target": None,
        "player_target": None,
        "gap": None,
        "ball_forecast": False,
        "player_forecast": False,
        "vertical_reversal": vertical_reversal(observation),
    }
    if b is None or p is None:
        return result
    ball_target, player_target = b[1] + b[3] / 2, p[1] + p[3] / 2
    by, py = velocity_y(ball), velocity_y(player)
    guard = rule != "relative-unguarded-2" and result["vertical_reversal"] is True
    if rule != "track-4" and by is not None and not guard:
        ball_target, _ = reflect(ball_target + 2 * by, low=32, high=194)
        result["ball_forecast"] = True
    if rule.startswith("relative-") and py is not None:
        player_target += 2 * py
        result["player_forecast"] = True
    gap = ball_target - player_target
    result.update(
        mode="forecast"
        if result["ball_forecast"] or result["player_forecast"]
        else "current-height",
        ball_target=ball_target,
        player_target=player_target,
        gap=gap,
        action=2 if gap < -4 else 3 if gap > 4 else 0,
    )
    return result


class RelativePolicy:
    def __init__(self, rule):
        if rule not in RULES:
            raise ValueError("Unknown diagnostic rule")
        self.rule, self.name = rule, f"literal-{rule}-v1"

    def choose(self, observation):
        result = interpret(observation, self.rule)
        return result["action"], {"policy": self.name, **result}
