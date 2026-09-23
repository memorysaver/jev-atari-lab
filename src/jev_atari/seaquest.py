"""Experimental Seaquest RAM mapping for local calibration, not a validated policy input.

Mapping adapted from MIT-licensed OCAtari revision
99c874675df6b76a33a80b57776c123fbcd051af; see THIRD_PARTY_NOTICES.md.
Never infer rewards, life-loss causes, or preferred actions from these objects.
"""

import numpy as np

EXTRACTOR = "seaquest-ram-calibration-v1"
UPSTREAM = "99c874675df6b76a33a80b57776c123fbcd051af"
PLAYER_COLOR = (187, 187, 53)
OXYGEN_COLOR = (214, 214, 214)


def decode(ram):
    values = np.asarray(ram)
    if values.shape != (128,) or not np.issubdtype(values.dtype, np.integer):
        raise ValueError("Expected 128 integer RAM bytes")
    if (values < 0).any() or (values > 255).any():
        raise ValueError("RAM bytes outside 0..255")
    r = values.astype(int)
    objects = []

    def add(identity, kind, x, y, width, height, **extra):
        objects.append(
            {"id": identity, "kind": kind, "bbox": [int(x), int(y), width, height], **extra}
        )

    if not 0 < r[105] < 15:
        add("player", "player", r[70], r[97] + 33, 16, 11, facing="right" if r[86] == 0 else "left")
    for lane in range(4):
        submarine = 3 < r[89 + lane] % 8 < 7
        for slot in range(3):
            x = (r[30 + lane] + 16 * slot) % 256
            if r[36 + lane] & (1 << (2 - slot)) and x <= 165:
                kind = "enemy_submarine" if submarine else "shark"
                y = 141 - lane * 24 + (0 if submarine else r[93] - 4)
                add(f"enemy-{lane}-{slot}", kind, x, y, 8, 11 if submarine else 7)
        x = r[71 + lane]
        if 0 < x < 160:
            kind = "enemy_missile" if submarine else "diver"
            add(
                f"lane-item-{lane}",
                kind,
                x + (3 if submarine else 0),
                141 - lane * 24 + (4 if submarine else 0),
                6 if submarine else 8,
                4 if submarine else 11,
            )
    if r[60] >= 2 and r[118] < 160:
        add("surface-enemy", "enemy_submarine", r[118], 45, 8, 11)
    if 0 < r[103] < 160:
        add("player-missile", "player_missile", r[103], r[97] + 40, 8, 1)
    return {
        "schema_version": EXTRACTOR,
        "game": "ALE/Seaquest-v5",
        "objects": objects,
        "oxygen_raw": int(r[102]),
        "oxygen_bar_pixels": min(int(r[102]), 63),
        "carried_divers_raw": int(r[62]),
        "carried_divers": int(r[62]) if r[62] <= 6 else None,
        "reserve_lives_raw": int(r[59]),
        "player_animation_raw": int(r[105]),
        "validation": "experimental; calibrated fields and coverage reported separately",
    }


def pixel_checks(observation, rgb):
    """Independent screen evidence for two mappings, not full semantic validation."""
    if rgb.shape != (210, 160, 3):
        raise ValueError("Expected Seaquest RGB frame")
    oxygen_width = int(np.all(rgb[172, 49:112] == OXYGEN_COLOR, axis=1).sum())
    player = next((o for o in observation["objects"] if o["kind"] == "player"), None)
    player_pixels = None
    if player:
        x, y, w, h = player["bbox"]
        crop = rgb[max(0, y) : min(210, y + h), max(0, x) : min(160, x + w)]
        player_pixels = int(np.all(crop == PLAYER_COLOR, axis=2).sum())
    return {
        "oxygen_screen_pixels": oxygen_width,
        "oxygen_width_matches_ram": oxygen_width == observation["oxygen_bar_pixels"],
        "player_color_pixels_inside_box": player_pixels,
    }
