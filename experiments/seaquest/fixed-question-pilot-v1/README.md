# First Seaquest Jev pilot: reviewed local evidence

Two completed fixed-question trajectories, 80 points each, native termination at
2,213 frames. All 1,108 actions fit DOWN when active, NOOP when unavailable.
This is an instrumentation pilot with a coordinator-authored baseline, not learning.

[Results and limits](../../../docs/seaquest/fixed-question-pilot-results-2026-09-24.md) ·
[Frozen protocol](../../../docs/seaquest/fixed-question-pilot-protocol.md)

- [Original plan](records/plan.json), [results](records/results.json), [budget](records/budget.json).
- [Descriptive action/coverage analysis](descriptive-analysis.json), [costs](costs.json).
- [Original audit](verification.json), [restored audit](restored-verification.json),
  [closure](closure.json), [supervision](supervision.json).
- [Archive manifest](seaquest-fixed-question-pilot-v1.manifest.json).
- [Seed 310 video](videos/seed-310/episode.mp4), [seed 311 video](videos/seed-311/episode.mp4).
- [Matched local controls](../pilot-v1-controls/README.md).

The archive contains every original HTTP exchange, action, observation, raw-frame
RAM/RGB hash, reward/life/end flag and both videos. No credentials, ROMs or emulator
snapshots. Byte-identical JSON metadata is browsable in `records/`. Archives and
videos are local Git LFS evidence; no remote retrieval claim.

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/seaquest/fixed-question-pilot-v1/seaquest-fixed-question-pilot-v1.manifest.json \
  --out artifacts/seaquest/restored-fixed-question-pilot-v1
uv run python scripts/verify_seaquest_pilot.py \
  --run artifacts/seaquest/restored-fixed-question-pilot-v1/fixed-question-pilot-v1 \
  --out artifacts/seaquest/restored-fixed-question-pilot-v1-audit
```
