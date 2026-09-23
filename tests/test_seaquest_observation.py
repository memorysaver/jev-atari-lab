"""Protect original calibration, animation availability, and raw-time history boundaries."""

import numpy as np

from jev_atari.seaquest import decode
from jev_atari.seaquest_observation import Observer, decode_v2, screen_checks


def test_new_visibility_contract_preserves_original_decoder():
    ram = np.zeros(128, dtype=np.uint8)
    ram[70], ram[97], ram[105] = 70, 40, 23
    assert any(o["kind"] == "player" for o in decode(ram)["objects"])
    assert decode_v2(ram)["objects"] == []
    ram[105] = 0
    assert decode_v2(ram)["object_state"] == "active"
    assert decode_v2(ram, ended=True)["objects"] == []


def test_history_clears_on_animation_end_and_native_life_loss():
    ram = np.zeros(128, dtype=np.uint8)
    observer = Observer()

    def observe(frame, lives=4, ended=False):
        return observer.observe(ram, raw_frame=frame, lives=lives, names=["NOOP"], ended=ended)

    assert observe(0)["history"] == []
    assert [h["raw_frame"] for h in observe(4)["history"]] == [0]
    assert [h["raw_frame"] for h in observe(8)["history"]] == [0, 4]
    ram[105] = 23
    assert observe(12)["history"] == []
    ram[105] = 0
    assert observe(16)["history"] == []
    assert observe(20, lives=3)["history"] == []
    assert observe(24, ended=True)["history"] == []
    assert observe(28)["history"] == []


def test_box_support_is_independent_of_ram_mapping():
    ram = np.zeros(128, dtype=np.uint8)
    ram[70], ram[97], ram[102] = 70, 40, 20
    observation = decode_v2(ram)
    rgb = np.zeros((210, 160, 3), dtype=np.uint8)
    rgb[73:84, 70:86] = (236, 236, 236)
    rgb[172, 49:69] = (214, 214, 214)
    checks = screen_checks(observation, rgb)
    assert checks["oxygen_matches"]
    assert checks["objects"][0]["color_pixels"] == 176
    rgb[73:84, 70:86] = 0
    assert screen_checks(observation, rgb)["objects"][0]["color_pixels"] == 0
