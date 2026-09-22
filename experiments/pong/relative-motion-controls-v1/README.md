# Relative-motion controls v1: reviewed local evidence

The teacher-inspired literal relative-motion rule averaged +0.75 capped return,
versus -0.75 for current-center tracking: a paired gain of +1.5 on eight training
seeds, with four gains, two ties and two regressions. All 32 episodes reached the
2,000-frame cap; no native match completed. These are manual Python interpretations,
not Jev improvement or a policy promotion. No model calls were made.

[Report](../../../docs/pong/relative-motion-controls-results-2026-09-23.md) ·
[Frozen protocol](../../../docs/pong/relative-motion-controls-protocol.md)

- [Plan and frozen source](plan.json), [original teacher source](teacher-source.json).
- [Every episode and aggregates](results.json), [paired description](paired-description.json).
- [Original-run audit](verification.json), [archive manifest](relative-motion-controls-v1.manifest.json).
- [Archive restoration and replay audit](restored-verification.json).

The LFS archive contains every observation, chosen action, diagnostic prediction,
raw-frame record, reward, summary and video. All four rules ran on all eight seeds;
the ball-only and unguarded variants are ablations declared before these rollouts.
Results are not supplied to the running criteria study's teachers.

## Restore and verify

The archive is prepared and verified locally. It has not been pushed or retrieved
from a remote checkout; remote preservation is not claimed. Choose fresh paths:

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/relative-motion-controls-v1/relative-motion-controls-v1.manifest.json \
  --out artifacts/restored-relative-motion
uv run python scripts/relative_motion_controls.py verify \
  --run artifacts/restored-relative-motion/relative-motion-controls-v1 \
  --out artifacts/restored-relative-motion-audit
```

Restoration checks the archive and every member's SHA-256. The second command
replays all 32 episodes, recomputes actions and diagnostic predictions, and checks
the original teacher hash, frozen schedule, protocol and aggregate results. Neither
command contacts a model provider. Re-running the experiment is a separate run and
requires clean committed source; existing experiment directories cannot be reused.
