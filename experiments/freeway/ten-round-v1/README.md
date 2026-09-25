# Freeway ten-round study, 2026-09-26

Completed exactly ten rounds; allocation closed; no revision promoted.
Development and final paired mean gains were zero. Full
[results and lessons](../../../docs/freeway/ten-round-results-2026-09-26.md),
[frozen protocol](../../../docs/freeway/ten-round-protocol.md), and
[all 42 recordings](videos.md).

Frozen live source: `d11474f`. Six coordinator-authored proposals, zero isolated
teacher calls, fixed Jev weights; no causal teacher-feedback or mastery claim.
All 42 episodes ended natively at 8,192 raw frames. Generic and selected Jev both
scored 23/26 on final seeds; local predictive controls scored 29/29.

- [Resource accounting](records/resources.json): 11,711 successful attempts,
  reported cost US$0.978697986; interactive coordinator and local compute excluded.
- [Replay/API/video audit](records/audit.json): all 344,064 collected raw frames.
- [Selection seal](records/selection.json) and [closed budget](records/budget.json).
- [Archive manifest](freeway-ten-round-v1.manifest.json): 310 files,
  482,830,396 uncompressed bytes.
- [Complete archive](freeway-ten-round-v1.tar.gz), SHA-256:
  `1c41a76cfcbc963f37ca79d9ac6d5004353897ecc8701cc288505217d6712eb0`.

The archive contains all observations/actions/raw frames, model request/response
bodies, programs/provenance, diagnostic packets, complete videos and summaries.
Reviewed records expose compact results; recordings and archives use Git LFS.
No credentials, ROMs or emulator snapshots are included.

## Restore and verify without API calls

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/freeway/ten-round-v1/freeway-ten-round-v1.manifest.json \
  --out artifacts/freeway/reproduction
uv run python scripts/verify_freeway_research.py \
  --root artifacts/freeway/reproduction/ten-round-v1 \
  --out artifacts/freeway/reproduction-audit.json
```

A fresh directory is required. Restore checks every member hash before extraction.
Verification replays actions, reconstructs observations, checks rewards and frames,
validates original response pins/selected actions, checks all video frame counts,
and recomputes probe metrics, selection, gates and budget accounting. It makes no
model calls. Calibration source metadata says uncommitted because that round
preceded the live freeze; decoder hashes and frozen-source equality are preserved.

Local preservation checks passed: the restored full audit is byte-identical to
the original, and all 42 standalone video hashes match the audited recordings.
[Preservation record](preservation.json).
