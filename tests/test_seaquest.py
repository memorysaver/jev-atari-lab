"""Seaquest calibration mappings are observable inputs, never inferred rewards or actions."""

import numpy as np
import pytest

from jev_atari.arcade import make_game
from jev_atari.seaquest import OXYGEN_COLOR, decode, pixel_checks


def test_mapping_missing_player_zero_oxygen_and_lane_semantics():
    ram = np.zeros(128, dtype=np.uint8)
    ram[70], ram[97], ram[102], ram[62] = 70, 40, 64, 3
    ram[71], ram[36], ram[30] = 50, 4, 70
    obs = decode(ram)
    assert obs["objects"][0]["bbox"] == [70, 73, 16, 11]
    assert obs["oxygen_bar_pixels"] == 63 and obs["carried_divers"] == 3
    assert {o["kind"] for o in obs["objects"]} == {"player", "diver", "shark"}
    ram[89] = 4
    assert {o["kind"] for o in decode(ram)["objects"]} == {
        "player",
        "enemy_missile",
        "enemy_submarine",
    }
    ram[105], ram[102], ram[62] = 1, 0, 255
    obs = decode(ram)
    assert not any(o["kind"] == "player" for o in obs["objects"])
    assert obs["oxygen_raw"] == 0 and obs["carried_divers"] is None
    assert "reward" not in obs and "preferred_action" not in obs
    with pytest.raises(ValueError):
        decode([0] * 127)
    with pytest.raises(ValueError):
        decode([256] * 128)


def test_pixel_comparison_can_disagree_with_ram():
    ram = np.zeros(128, dtype=np.uint8)
    ram[102] = 20
    rgb = np.zeros((210, 160, 3), dtype=np.uint8)
    rgb[170:175, 49:69] = OXYGEN_COLOR
    assert pixel_checks(decode(ram), rgb)["oxygen_width_matches_ram"]
    ram[102] = 21
    assert not pixel_checks(decode(ram), rgb)["oxygen_width_matches_ram"]


def test_native_movement_on_matched_real_emulator_states():
    env = make_game("Seaquest", sticky=0)
    try:
        names = env.unwrapped.get_action_meanings()
        assert len(names) == 18
        for name, coordinate, sign in (
            ("UP", 1, -1),
            ("DOWN", 1, 1),
            ("LEFT", 0, -1),
            ("RIGHT", 0, 1),
        ):
            env.reset(seed=300)
            for _ in range(128):
                env.step(names.index("NOOP"))
            for _ in range(40):
                env.step(names.index("DOWN"))
            before = decode(env.unwrapped.ale.getRAM())["objects"][0]["bbox"]
            for _ in range(8):
                env.step(names.index(name))
            after = decode(env.unwrapped.ale.getRAM())["objects"][0]["bbox"]
            assert (after[coordinate] - before[coordinate]) * sign > 0
    finally:
        env.close()


def test_calibration_recorded_action_replay_detects_tampering(tmp_path, monkeypatch):
    import importlib
    import json
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    calibration = importlib.import_module("seaquest_calibration")
    path = tmp_path / "original"
    original = calibration.trajectory(path, 300, "random", frames=180)
    rows = [json.loads(line) for line in (path / "transitions.jsonl").read_text().splitlines()]
    replay = calibration.trajectory(tmp_path / "replay", 300, "random", frames=180, recorded=rows)
    assert original == replay and original["api_attempts"] == 0
    rows[0]["frames"][0]["rgb_sha256"] = "tampered"
    with pytest.raises(ValueError, match="Replay mismatch"):
        calibration.trajectory(tmp_path / "tampered", 300, "random", frames=180, recorded=rows)
