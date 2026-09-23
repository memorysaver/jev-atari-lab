# Seaquest calibration v1: local evidence

Eight local trajectories and their recorded-action replays; zero API calls.
[Report](../../../docs/seaquest/calibration-results-2026-09-24.md) ·
[Frozen protocol](../../../docs/seaquest/calibration-protocol.md)

- [Plan](plan.json), [results](results.json), [18 action-effect checks](action-effects.json).
- [146 player-box disagreements](player-box-disagreements.json), retained as mapping limitations.
- [Archive manifest](seaquest-calibration-v1.manifest.json),
  [restored replay verification](restored-verification.json).

The LFS archive retains original and replayed raw-frame RAM/RGB hashes, semantic
observations, actions/rewards/lives, summaries and four videos. No credentials,
ROMs or emulator snapshots are included. Local preservation only; no remote claim.

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/seaquest/calibration-v1/seaquest-calibration-v1.manifest.json \
  --out artifacts/seaquest/restored-calibration-v1
uv run python scripts/verify_seaquest_calibration.py \
  --run artifacts/seaquest/restored-calibration-v1/calibration-v1 \
  --out artifacts/seaquest/restored-calibration-v1-audit
```

The source mapping is experimental: pixel checks support the oxygen display but
expose player animation failures; moving objects and full diver/rescue cycles
remain unvalidated. These are calibration controls, not learned policies.
