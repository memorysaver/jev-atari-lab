import json

import pytest

from jev_atari.environment import Protocol
from jev_atari.experiment import play
from jev_atari.policies import RandomPolicy
from jev_atari.replay import replay_episode


def test_replay_reconstructs_observations_rewards_and_rejects_tampering(tmp_path, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    original = tmp_path / "episode"
    play(Protocol(noop_max=0), RandomPolicy(0), seed=0, decisions=12, out=original)
    report = replay_episode(original, tmp_path / "verified")
    assert report["status"] == "verified"
    assert report["raw_frames"] == 48
    assert report["api_attempts"] == 0
    assert report["raw_frame_evidence"] == "verified-against-original"
    assert len((original / "frames.jsonl").read_text().splitlines()) == 48
    path = original / "transitions.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[1]["rewards"][0] = 123
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="outcome differs"):
        replay_episode(original, tmp_path / "tampered")


def test_replay_refuses_different_protocol_version(tmp_path):
    original = tmp_path / "episode"
    play(Protocol(noop_max=0), RandomPolicy(0), seed=0, decisions=1, out=original)
    path = original / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["protocol"]["versions"]["ale-py"] = "unmatched"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="versions"):
        replay_episode(original, tmp_path / "mismatch")
