# Interrupted Ms. Pac-Man direct versus target-action pilot v1

The first model request failed at transport. A separate DNS lookup failed in the
current restricted-network execution environment. No successful responses, model
actions, model videos, or development/final episodes exist for this allocation.
The unused capacity is closed. This is not a negative model-performance result.

[Protocol](../../../docs/mspacman/pilot-protocol.md) ·
[Report](../../../docs/mspacman/pilot-results-2026-09-28.md) ·
[Exact prompts](program.json) · [Plan](plan.json) · [Budget](budget.json) ·
[Closure](closure.json) · [Original exchange audit](interruption-audit.json) ·
[Verification](verification.json) · [Restored verification](restored-verification.json).

The [archive manifest](mspacman-direct-vs-target-v1-interrupted.manifest.json)
indexes 11 files, including the 24-state frozen training packet and original
failed exchange. No credentials, ROMs or emulator snapshots are included.
Provider cost is unavailable; zero accumulated reported cost means no usage
record was received. Local LFS preservation only; no remote retrieval claim.

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/mspacman/direct-vs-target-v1-interrupted/mspacman-direct-vs-target-v1-interrupted.manifest.json \
  --out artifacts/mspacman/restored-pilot-example
uv run python scripts/verify_mspacman_pilot.py \
  --run artifacts/mspacman/restored-pilot-example/direct-vs-target-v1 \
  --calibration artifacts/mspacman/restored-calibration-example/calibration-v1
```

Restore the calibration archive first using its adjacent README instructions.
Preserve this closed v1 if a newly authorized bounded continuation is launched.
