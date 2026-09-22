"""Offline reporting regressions: failed calls, duplicate ledgers and missing tests."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from jev_atari import teacher
from jev_atari.io import digest, read_json, write_json
from jev_atari.study import StudyBudget


def reporting_module():
    path = Path(__file__).resolve().parents[1] / "scripts/summarize_teacher_study.py"
    spec = importlib.util.spec_from_file_location("study_summary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cost_counts_exchanges_once_and_does_not_invent_usage(tmp_path):
    module = reporting_module()
    transport = {
        "status": 200,
        "elapsed_seconds": 1,
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }
    failed = {"status": 529, "elapsed_seconds": 2, "usage": None}
    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "model-exchanges.jsonl").write_text(
        "\n".join(json.dumps({"transport": t}) for t in (failed, transport)) + "\n"
    )
    # Suite and episode ledgers describe the SAME transport, not more calls.
    write_json(episode / "api-ledger.json", [failed, transport])
    write_json(tmp_path / "api-ledger.json", [failed, transport])
    result = module.costs(tmp_path)
    assert result["http_attempts"] == 2
    assert result["reported_input_tokens"] == 10
    assert result["attempts_without_usage"] == 1
    assert result["non_200_attempts"] == 1 and result["api_elapsed_seconds"] == 3
    assert result["monetary_cost"] is None


def test_unopened_final_is_missing_not_a_zero_score(tmp_path):
    module = reporting_module()
    run, audit = tmp_path / "run", tmp_path / "audit"
    budget = {"attempts": 0}
    write_json(run / "budget.json", budget)
    write_json(run / "status.json", {"status": "incomplete"})
    write_json(
        audit / "verification.json",
        {"status": "verified", "budget_hash": digest(budget), "study_status": "incomplete"},
    )
    report = module.summarize(run, audit, tmp_path / "report")
    assert all(p["n"] == 0 and p["mean_paired_difference"] is None for p in report["paired_final"])
    for arm in report["final_aggregates"].values():
        assert arm["scheduled_episodes"] == 4 and arm["recorded_episodes"] == 0
        assert arm["mean_capped_return"] is None
        assert arm["win_rate_completed_matches"] is None
        assert arm["possible_win_fraction_bounds"] == [0, 1]
    write_json(run / "budget.json", {"attempts": 1})
    with pytest.raises(AssertionError):
        module.summarize(run, audit, tmp_path / "stale-report")


def test_failed_teacher_retains_private_diagnostics_before_raising(tmp_path, monkeypatch):
    auth = tmp_path / "auth"
    auth.mkdir()
    (auth / "auth.json").write_text("{}")
    monkeypatch.setattr(teacher, "isolation_check", lambda binary, *args: {})
    monkeypatch.setattr(teacher, "bubblewrap", lambda *args: [])
    responses = iter(
        [
            SimpleNamespace(stdout="[]"),
            SimpleNamespace(
                returncode=1,
                stdout='{"type":"turn.failed"}\n',
                stderr="synthetic-private-provider-detail",
            ),
        ]
    )
    monkeypatch.setattr(teacher.subprocess, "run", lambda *a, **kw: next(responses))
    original = teacher.tempfile.mkdtemp
    monkeypatch.setattr(
        teacher.tempfile,
        "mkdtemp",
        lambda suffix=None, prefix=None, dir=None: original(suffix, prefix, tmp_path),
    )
    out = tmp_path / "public"
    budget = StudyBudget(tmp_path / "budget.json")
    with pytest.raises(ValueError, match="did not complete"):
        teacher.invoke_teacher({}, out, budget, binary=Path("/unused"), auth_home=auth)
    metadata = read_json(out / "execution.json")
    assert metadata["private_diagnostics_retained"] is True
    assert metadata["status"] == "incomplete"
    assert read_json(budget.path)["teacher_invocations"] == 1
    diagnostic = next(tmp_path.glob("jev-teacher-error-*"))
    assert diagnostic.stat().st_mode & 0o777 == 0o700
    for path in diagnostic.iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
    assert "synthetic-private-provider-detail" in (diagnostic / "stderr.txt").read_text()
    assert all("synthetic-private-provider-detail" not in p.read_text() for p in out.iterdir())
