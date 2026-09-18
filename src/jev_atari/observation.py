"""Fixed observation extraction, independent of learned question programs.

Pong RAM mappings adapted from OCAtari (MIT); see THIRD_PARTY_NOTICES.md.
Velocity is estimated here from timestamped observations, not RAM-internal velocity.
"""

from collections import deque
from copy import deepcopy

import numpy as np

SCHEMA = "atari-object-observation-v1"
EXTRACTOR = "pong-ocatari-derived-v1"
ACTION_NAMES = ["NOOP", "FIRE", "RIGHT", "LEFT", "RIGHTFIRE", "LEFTFIRE"]
# Verified by actual emulator action probes, not inferred from joystick labels.
ACTION_EFFECTS = ["hold", "hold", "up", "down", "up", "down"]


def ram_boxes(ram: np.ndarray) -> dict[str, list[int] | None]:
    r = [int(x) for x in ram]  # avoid uint8 underflow in offset calculations
    boxes = {"player": None, "opponent": None, "ball": None}
    if r[51] >= 34:
        y = max(34, r[51] - 13)
        height = r[51] - 33 if r[51] < 47 else min(15, 194 - y)
        if height > 0:
            boxes["player"] = [140, y, 4, height]
    if r[50] > 33:
        y = max(34, r[50] - 15)
        height = min(15, r[50] - 33, 194 - y)
        if height > 0:
            boxes["opponent"] = [16, y, 4, height]
    if r[54] != 0 and r[49] > 49:
        boxes["ball"] = [r[49] - 49, r[54] - 14, 2, 4]
    return boxes


def vision_boxes(rgb: np.ndarray) -> dict[str, list[int] | None]:
    """Pong-specific color components, no RAM fallback; HUD rows excluded."""
    colors = {"player": (92, 186, 92), "opponent": (213, 130, 74), "ball": (236, 236, 236)}
    boxes = {}
    for name, color in colors.items():
        ys, xs = np.where(np.all(rgb[34:194] == color, axis=2))
        boxes[name] = (
            [
                int(xs.min()),
                int(ys.min()) + 34,
                int(xs.max() - xs.min() + 1),
                int(ys.max() - ys.min() + 1),
            ]
            if len(xs)
            else None
        )
    return boxes


class Tracker:
    def __init__(self) -> None:
        self.samples: deque = deque(maxlen=4)
        self.last_seen: dict[str, int] = {}

    def update(self, boxes: dict, raw_frame: int) -> list[dict]:
        previous = self.samples[-1] if self.samples else None
        objects = []
        for name, box in boxes.items():
            old = previous["boxes"].get(name) if previous else None
            dt = raw_frame - previous["frame"] if previous else 0
            valid = box is not None and old is not None and dt > 0
            if box is not None:
                self.last_seen[name] = raw_frame
            velocity = [(box[i] - old[i]) / dt for i in (0, 1)] if valid else None
            objects.append(
                {
                    "id": name,
                    "kind": "ball" if name == "ball" else "paddle",
                    "present": box is not None,
                    "bbox": box,
                    "velocity": velocity,
                    "velocity_valid": valid,
                    "sample_interval_raw_frames": dt if valid else None,
                    "age_since_last_seen_raw_frames": (
                        raw_frame - self.last_seen[name] if name in self.last_seen else None
                    ),
                }
            )
        self.samples.append({"frame": raw_frame, "boxes": deepcopy(boxes)})
        return objects

    def clear_ball_history(self) -> None:
        """A scored point breaks identity even if a ball reappears in one action chunk."""
        for sample in self.samples:
            sample["boxes"]["ball"] = None

    def history(self, raw_frame: int) -> list[dict]:
        return [
            {"offset_raw_frames": x["frame"] - raw_frame, "boxes": deepcopy(x["boxes"])}
            for x in self.samples
        ]


def make_observation(
    tracker: Tracker,
    boxes: dict,
    raw_frame: int,
    *,
    source: str,
    hold: int,
    sticky: float,
    last_action: int | None,
    events: list[str],
) -> dict:
    objects = tracker.update(boxes, raw_frame)
    return {
        "schema_version": SCHEMA,
        "extractor_version": EXTRACTOR,
        "game": "ALE/Pong-v5",
        "observation_source": source,
        "coordinates": {
            "width_px": 160,
            "height_px": 210,
            "origin": "top_left",
            "x_positive": "right",
            "y_positive": "down",
            "bbox_format": "x_y_width_height",
            "velocity_unit": "pixels_per_raw_frame",
        },
        "control": {
            "requested_hold_frames": hold,
            "sticky_action_probability": sticky,
            "last_requested_action_id": last_action,
            "last_executed_action_id": None,
        },
        "objects": objects,
        "history": tracker.history(raw_frame),
        "events_observed": events,
        "candidate_actions": [
            {"id": i, "ale_meaning": name, "effect": ACTION_EFFECTS[i], "hold_raw_frames": hold}
            for i, name in enumerate(ACTION_NAMES)
        ],
    }
