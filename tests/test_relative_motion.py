"""Check units, braking, missing observations and ambiguous bounce interpretation."""

from copy import deepcopy

from jev_atari.relative_motion import interpret


def observation():
    return {
        "objects": [
            {"id": "ball", "bbox": [80, 104, 2, 4], "velocity_valid": True, "velocity": [1, 0]},
            {
                "id": "player",
                "bbox": [140, 92.5, 4, 15],
                "velocity_valid": True,
                "velocity": [0, 4],
            },
        ],
        "history": [],
    }


def test_relative_motion_brakes_using_two_raw_frames_not_history_intervals():
    obs = observation()
    assert interpret(obs, "track-4")["action"] == 3
    r = interpret(obs, "relative-lookahead-2")
    assert r["ball_target"] == 106 and r["player_target"] == 108 and r["action"] == 0
    assert interpret(obs, "ball-lookahead-2")["action"] == 3


def test_unknown_velocity_retains_current_center_and_missing_bbox_holds():
    obs = observation()
    obs["objects"][1]["velocity_valid"] = False
    r = interpret(obs, "relative-lookahead-2")
    assert not r["player_forecast"] and r["action"] == 3
    obs["objects"][0]["bbox"] = None
    assert interpret(obs, "relative-lookahead-2")["action"] == 0


def test_teacher_ball_limits_and_player_forecast_are_separate():
    obs = observation()
    obs["objects"][0].update(bbox=[80, 193, 2, 4], velocity=[1, 1])
    obs["objects"][1].update(bbox=[140, 182.5, 4, 15], velocity=[0, 0])
    r = interpret(obs, "relative-lookahead-2")
    assert r["ball_target"] == 191 and r["player_target"] == 190 and r["action"] == 0


def test_guard_detects_vertical_not_horizontal_reversal_and_retains_sensitivity():
    obs = observation()
    obs["objects"][0].update(bbox=[80, 183, 2, 4], velocity=[1, -1])
    obs["objects"][1].update(bbox=[140, 180.5, 4, 15], velocity=[0, 0])
    obs["history"] = [
        {"offset_raw_frames": t, "boxes": {"ball": [x, y, 2, 4]}}
        for t, x, y in [(-8, 70, 178), (-4, 74, 188), (0, 78, 183)]
    ]
    assert interpret(obs, "relative-lookahead-2")["action"] == 0
    assert interpret(obs, "relative-unguarded-2")["action"] == 2
    other = deepcopy(obs)
    for sample, x, y in zip(other["history"], [70, 74, 70], [187, 185, 183], strict=True):
        sample["boxes"]["ball"] = [x, y, 2, 4]
    assert interpret(other, "relative-lookahead-2")["vertical_reversal"] is False
