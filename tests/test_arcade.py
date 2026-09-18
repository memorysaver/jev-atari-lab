import json

import httpx
import pytest

from jev_atari.arcade import ArcadeActionProgram, arcade_play, game_catalog, resolve_game
from jev_atari.choice import ChoiceEvaluator
from jev_atari.io import read_json
from jev_atari.models import BudgetExceeded


def test_catalog_uses_installed_registration_and_rejects_unknown_game():
    assert len(game_catalog()) > 50
    assert resolve_game("space_invaders")["env_id"] == "ALE/SpaceInvaders-v5"
    assert resolve_game("Pong")["semantic_adapter"] == "pong-objects"
    with pytest.raises(ValueError, match="Unknown"):
        resolve_game("not-a-game")


def test_random_run_exact_frame_cap_and_variable_action_set(tmp_path):
    report = arcade_play(
        "Freeway", policy="random", seed=0, frames=11, hold=4, sticky=0.25, out=tmp_path / "run"
    )
    assert (report["raw_frames"], report["decisions"], report["api_attempts"]) == (11, 3, 0)
    assert report["end_reason"] == "frame_limit"
    rows = [json.loads(s) for s in (tmp_path / "run/transitions.jsonl").read_text().splitlines()]
    assert len(rows[0]["observation"]["candidate_actions"]) == 3
    assert len(rows[0]["observation"]["ram_bytes"]) == 128
    assert rows[-1]["raw_frames"] == 3
    assert rows[-1]["observation"]["candidate_actions"][0]["hold_raw_frames"] == 3
    assert rows[0]["next_ram_bytes"] == rows[1]["observation"]["ram_bytes"]


def test_generic_jev_requests_are_game_specific_and_budget_failure_is_incomplete(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-only")
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        question = body["questions"]["next_action"]
        assert len(question["criteria"]) == 4  # Breakout, not Pong's six actions.
        assert "RIGHT paddle" not in json.dumps(question)
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "FIRE",
                        "confidence": 1,
                        "probabilities": {k: int(k == "FIRE") for k in question["criteria"]},
                    }
                },
            },
        )

    evaluator = ChoiceEvaluator(
        model="test-model", max_calls=1, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    evaluator.api.trace_path = tmp_path / "exchanges.jsonl"
    try:
        with pytest.raises(BudgetExceeded):
            arcade_play(
                "Breakout",
                policy="jev-action",
                seed=0,
                frames=8,
                hold=4,
                sticky=0.25,
                out=tmp_path / "run",
                evaluator=evaluator,
            )
        report = read_json(tmp_path / "run/summary.json")
        assert report["status"] == "incomplete"
        assert report["raw_frames"] == 4
        assert report["api_attempts"] == 1
        assert len(seen) == 1
        exchange = read_json(tmp_path / "exchanges.jsonl")
        assert exchange["request"] == seen[0]
        assert exchange["response"]["answers"]["next_action"]["choice"] == "FIRE"
        assert exchange["exchange_id"] == 1
        assert "Authorization" not in (tmp_path / "exchanges.jsonl").read_text()
    finally:
        evaluator.close()


def test_program_schema_and_game_are_not_interchangeable():
    program = ArcadeActionProgram()
    assert ArcadeActionProgram.from_dict(program.to_dict()).hash == program.hash
    with pytest.raises(ValueError, match="schema"):
        program.request({"game": "ALE/Pong-v5", "schema_version": "atari-ram-v1"}, "test")
    with pytest.raises(ValueError, match="Expected"):
        ArcadeActionProgram(schema_version="action-choice-program-v1")
