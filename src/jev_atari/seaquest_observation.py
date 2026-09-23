"""Versioned Seaquest object observations; original calibration decoder stays unchanged."""

from collections import deque
from copy import deepcopy

import numpy as np

from jev_atari.seaquest import decode

SCHEMA = "seaquest-objects-v2"
COLORS = {
    "player": ((187, 187, 53), (236, 236, 236)),
    "shark": ((92, 186, 92), (198, 108, 58), (160, 171, 79), (72, 160, 72), (198, 89, 179)),
    "enemy_submarine": ((170, 170, 170),),
    "diver": ((66, 72, 200),),
    "enemy_missile": ((66, 72, 200),),
    "player_missile": ((187, 187, 53),),
}


def decode_v2(ram, *, ended=False):
    result = decode(ram)
    result["schema_version"] = SCHEMA
    unavailable = ended or result["player_animation_raw"] != 0
    result["object_state"] = "unavailable-during-animation-or-end" if unavailable else "active"
    # Animation RAM can retain stale positions. Do not supply them as active objects.
    if unavailable:
        result["objects"] = []
    else:
        result["objects"] = [o for o in result["objects"] if o["bbox"][0] < 160]
    result["ended"] = ended
    return result


def screen_checks(observation, rgb):
    objects = []
    for obj in observation["objects"]:
        x, y, width, height = obj["bbox"]
        crop = rgb[max(0, y) : min(210, y + height), max(0, x) : min(160, x + width)]
        mask = np.zeros(crop.shape[:2], dtype=bool)
        for color in COLORS[obj["kind"]]:
            mask |= np.all(crop == color, axis=2)
        objects.append(
            {
                "id": obj["id"],
                "kind": obj["kind"],
                "bbox": obj["bbox"],
                "color_pixels": int(mask.sum()),
            }
        )
    oxygen = int(np.all(rgb[172, 49:112] == (214, 214, 214), axis=1).sum())
    return {
        "objects": objects,
        "oxygen_matches": oxygen == observation["oxygen_bar_pixels"],
        "oxygen_pixels": oxygen,
    }


class Observer:
    """Recent raw-time snapshots; clear across animation/end and native life losses."""

    def __init__(self):
        self.history = deque(maxlen=3)
        self.previous_lives = None

    def observe(self, ram, *, raw_frame, lives, names, ended=False):
        observation = decode_v2(ram, ended=ended)
        if (self.previous_lives is not None and lives < self.previous_lives) or observation[
            "object_state"
        ] != "active":
            self.history.clear()
        self.previous_lives = lives
        observation.update(
            raw_frame=raw_frame,
            lives=lives,
            history=deepcopy(list(self.history)),
            candidate_actions=[
                {"id": i, "ale_meaning": name, "hold_raw_frames": 4} for i, name in enumerate(names)
            ],
        )
        if observation["object_state"] == "active":
            self.history.append(
                {"raw_frame": raw_frame, "objects": deepcopy(observation["objects"])}
            )
        return observation
