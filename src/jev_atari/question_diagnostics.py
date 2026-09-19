"""Explicit diagnostic interpretations of prose policies, never a Jev fallback."""

import math

RULES = ("v2", "intercept", "lookahead", "lookahead-conservative")


def reflect(target, low=35.0, high=192.0):
    """Fold a projected center into the teacher's stated interval, including many bounces."""
    span = high - low
    if not math.isfinite(target) or span <= 0:
        raise ValueError("Finite target and increasing bounds required")
    offset = (target - low) % (2 * span)
    count = math.ceil(max(low - target, target - high, 0) / span)
    return low + min(offset, 2 * span - offset), count


def recent_bounce(observation):
    """Sign reversal across the last two observable segments; not hidden collision truth."""
    history = observation.get("history", [])[-3:]
    if len(history) < 3:
        return None
    velocities = []
    for before, after in zip(history, history[1:], strict=False):
        a, b = before["boxes"].get("ball"), after["boxes"].get("ball")
        dt = after["offset_raw_frames"] - before["offset_raw_frames"]
        if a is None or b is None or dt <= 0:
            return None
        velocities.append([(b[i] - a[i]) / dt for i in (0, 1)])
    return any(a * b < 0 for a, b in zip(*velocities, strict=True))


def interpret(observation, rule):
    if rule not in RULES:
        raise ValueError("Unknown diagnostic rule")
    objects = {o["id"]: o for o in observation["objects"]}
    ball = objects.get("ball", {})
    b, p = ball.get("bbox"), objects.get("player", {}).get("bbox")
    result = {
        "rule": rule,
        "action": 0,
        "mode": "missing-object",
        "motion": "unknown",
        "target_y": None,
        "current_gap": None,
        "target_gap": None,
        "time_to_contact_raw_frames": None,
        "reflections": 0,
        "recent_sign_reversal": recent_bounce(observation),
    }
    if b is None or p is None:
        return result
    center, player_center = b[1] + b[3] / 2, p[1] + p[3] / 2
    target = center
    result["mode"] = "current-height"
    velocity = ball.get("velocity") if ball.get("velocity_valid") else None
    valid = (
        velocity is not None
        and len(velocity) == 2
        and all(isinstance(v, (int, float)) and math.isfinite(v) for v in velocity)
    )
    if valid:
        vx, vy = velocity
        result["motion"] = "incoming" if vx > 0 else "outgoing" if vx < 0 else "stationary-x"
        if vx > 0 and b[0] + b[2] < p[0]:
            result["time_to_contact_raw_frames"] = (p[0] - b[0] - b[2]) / vx
        if rule == "intercept" and result["time_to_contact_raw_frames"] is not None:
            target, count = reflect(center + vy * result["time_to_contact_raw_frames"])
            result.update(mode="intercept", reflections=count)
        if rule.startswith("lookahead") and vx > 0:
            # B's "reliably" and "evident bounce" are underspecified. Report both choices.
            trusted = rule == "lookahead" or result["recent_sign_reversal"] is False
            if trusted:
                target = center + vy * observation["control"]["requested_hold_frames"]
                result["mode"] = "lookahead"
            else:
                result["mode"] = "uncertain-motion-fallback"
    gap = target - player_center
    result.update(
        target_y=target,
        current_gap=center - player_center,
        target_gap=gap,
        action=2 if gap < -4 else 3 if gap > 4 else 0,
    )
    return result


class DiagnosticPolicy:
    def __init__(self, rule):
        if rule not in RULES:
            raise ValueError("Unknown diagnostic rule")
        self.rule = rule
        self.name = f"diagnostic-{rule}-v1"

    def choose(self, observation):
        result = interpret(observation, self.rule)
        return result["action"], {"policy": self.name, **result}
