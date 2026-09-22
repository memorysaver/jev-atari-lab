# Compact wording probe v1: reviewed local evidence

**Negative result:** Compact conservative-rule agreement was 62/160 (38.75%),
versus 76/160 (47.50%) for the freshly evaluated expanded question. The candidate
failed its prospective screen. No gameplay, isolated teacher call or final-test
evaluation occurred. All 480 Jev responses are retained in the local LFS archive.

[Report](../../../docs/pong/wording-probe-results-2026-09-22.md) ·
[Frozen protocol](../../../docs/pong/wording-probe-protocol.md) ·
[Manual proposal D002](../../../docs/pong/teacher-rounds/D002-compact-wording.md)

- [Programs](programs.json), [guidance diff](guidance-diff.txt), [provenance](provenance.json).
- [Inputs and audit labels](inputs.json), [coverage](coverage.json), [intervention audit](intervention-audit.json).
- [Plan and source revision](plan.json), [durable budget](budget.json).
- [Results](results.json), [prospective screen](screen.json), [independent audit](verification.json).
- [Post-hoc paired description](paired-description.json), [archive manifest](wording-probe-v1.manifest.json).

The same 80 training states had been inspected in motion-probe-v1. This is
exploratory reuse, not a held-out test. Labels in `inputs.json` are for the auditor;
the model requests contain only original observations. Raw requests/responses,
parsed predictions and attempt records are in the archive. The original training
pool remains in the separate [question-diagnostics archive](../question-diagnostics-v1/README.md).
No new emulator frames or videos were generated.

## Restore and audit without model access

This branch's archive is prepared locally. **It has not been pushed or retrieved
from a remote checkout.** Local verification is not remote preservation. A future
authorized publication must verify remote LFS retrieval before changing that status.

First restore question-diagnostics-v1 using its linked instructions, then choose
fresh output directories for:

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/wording-probe-v1/wording-probe-v1.manifest.json \
  --out artifacts/restored-wording-probe
uv run python scripts/wording_probe.py verify \
  --pack artifacts/restored-wording-probe/wording-probe-v1/pack \
  --run artifacts/restored-wording-probe/wording-probe-v1/run \
  --source artifacts/restored-question-diagnostics/question-diagnostics-v1/local \
  --out artifacts/wording-probe-restored-audit
```

These commands check archive SHA-256, reconstruct the selection from the original
training files, and validate model responses, metrics and the frozen screen. They
make no model calls. Live execution is separate, needs explicit `--backend jev`,
requires a clean committed source and enforces its own durable 520-attempt cap.
Re-querying the provider is a new realization, not recovery of an original response.
