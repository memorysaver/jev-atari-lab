"""Guard state stratification, labels, schedule balance and durable call limits."""

import pytest

from jev_atari.io import read_json
from jev_atari.models import BudgetExceeded
from jev_atari.motion_probe import LIMIT, PRECISE, ProbeBudget, classify, schedule, summarize
from jev_atari.observation import Tracker, make_observation


def state():
    tracker = Tracker()
    for t, x, y in [(0, 80, 100), (4, 84, 96), (8, 88, 100)]:
        obs = make_observation(
            tracker,
            {"ball": [x, y, 2, 4], "player": [140, 96, 4, 15]},
            t,
            source="ram",
            hold=4,
            sticky=0.25,
            last_action=0,
            events=[],
        )
    return obs


def test_conflict_stratum_uses_motion_and_not_reward():
    obs = state()
    assert classify(obs) == "incoming-uncertain-same"
    obs["objects"][1]["bbox"][1] = 92
    assert classify(obs) == "incoming-uncertain-conflict"
    obs["objects"][0]["bbox"] = None
    assert classify(obs) == "missing"


def test_round_robin_and_repeats_are_complete():
    states = [{"id": str(i)} for i in range(4)]
    rows = schedule(states, {"v2": {}, "ambiguous": {}, "precise": {}})
    assert len(rows) == 24
    assert len({(r["id"], r["program"], r["repeat"]) for r in rows}) == 24
    assert [r["program"] for r in rows[:3]] == ["v2", "ambiguous", "precise"]
    assert rows[3]["program"] == "ambiguous"


def test_budget_persists_and_cannot_reset(tmp_path):
    now = [100.0]
    p = tmp_path / "budget.json"
    b = ProbeBudget(p, clock=lambda: now[0])
    b.reserve()
    assert read_json(p)["used"] == 1
    with pytest.raises(ValueError):
        ProbeBudget(p)
    now[0] += 14400
    with pytest.raises(BudgetExceeded):
        b.reserve()
    assert read_json(p)["used"] == 1
    now[0] = 100
    b.used = LIMIT
    with pytest.raises(BudgetExceeded):
        b.reserve()


def test_labels_stay_out_of_model_input_and_missing_denominators():
    obs = state()
    request = PRECISE.request(obs, "jev-1.13.0")
    assert request["state"]["observation"] == obs
    assert "rule_actions" not in request["state"]
    results = summarize([], {"precise": {}}, [])
    assert all(r["responses"] == 0 and r["agreement"]["v2"] is None for r in results)


@pytest.mark.parametrize("kind", ["motion-probe-v1", "wording-probe-v1"])
def test_mock_transport_retry_roundtrip_and_audit(tmp_path, monkeypatch, kind):
    import importlib.util
    import json
    from pathlib import Path

    import httpx

    from jev_atari.choice import ChoiceEvaluator
    from jev_atari.io import digest, write_json
    from jev_atari.motion_probe import MODEL
    from jev_atari.question_diagnostics import RULES, interpret

    spec = importlib.util.spec_from_file_location(
        "motion_runner", Path(__file__).resolve().parents[1] / "scripts/motion_probe.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    obs = state()
    states = [
        {
            "id": digest(obs),
            "stratum": classify(obs),
            "observation": obs,
            "rule_actions": {r: interpret(obs, r)["action"] for r in RULES},
        }
    ]
    programs = {name: PRECISE.to_dict() for name in ["v2", "ambiguous", "precise"]}
    pack = tmp_path / "pack"
    values = {
        "inputs.json": states,
        "programs.json": programs,
        "coverage.json": {},
        "provenance.json": {},
    }
    for name, value in values.items():
        write_json(pack / name, value)
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if len(calls) == 1:
            return httpx.Response(529)
        options = payload["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": MODEL,
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "NOOP",
                        "confidence": 1,
                        "probabilities": {k: int(k == "NOOP") for k in options},
                    }
                },
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-key")
    monkeypatch.setattr(
        module,
        "ChoiceEvaluator",
        lambda **kw: ChoiceEvaluator(
            **kw, client=httpx.Client(transport=httpx.MockTransport(handler))
        ),
    )
    monkeypatch.setattr(
        module.subprocess,
        "check_output",
        lambda args, **kw: "" if "status" in args else "synthetic-source\n",
    )

    def fake_prepare(source, out, repository):
        for name, value in values.items():
            write_json(out / name, value)
        return states, programs

    monkeypatch.setattr(module, "prepare", fake_prepare)
    report = module.run(pack, tmp_path / "run", "jev", kind=kind)
    assert report["status"] == "complete" and report["attempts"] == 7
    assert report["completed_predictions"] == 6 and report["non_200_attempts"] == 1
    assert calls[0] == calls[1]
    result = module.verify(
        pack,
        tmp_path / "run",
        tmp_path / "audit",
        tmp_path,
        tmp_path,
        kind=kind,
        prepare_fn=fake_prepare,
    )
    assert result["status"] == "verified" and result["predictions"] == 6
    with pytest.raises(AssertionError):
        module.verify(
            pack,
            tmp_path / "run",
            tmp_path / "wrong-study",
            tmp_path,
            tmp_path,
            kind="unrelated-study",
            prepare_fn=fake_prepare,
        )
    rows = (tmp_path / "run/predictions.jsonl").read_text().splitlines()
    bad = json.loads(rows[0])
    bad["prediction"]["chosen_action"] = 3
    rows[0] = json.dumps(bad)
    (tmp_path / "run/predictions.jsonl").write_text("\n".join(rows) + "\n")
    with pytest.raises(AssertionError):
        module.verify(
            pack,
            tmp_path / "run",
            tmp_path / "bad-audit",
            tmp_path,
            tmp_path,
            kind=kind,
            prepare_fn=fake_prepare,
        )
