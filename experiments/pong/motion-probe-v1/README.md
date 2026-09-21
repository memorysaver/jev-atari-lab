# Stratified motion-reliability probe v1

**Negative result:** Explicit reliability wording regressed on its intended
uncertain-motion condition and on several basic behaviors. No policy promotion,
gameplay rollout, teacher invocation or final-test access occurred.

[Report](../../../docs/pong/motion-probe-results-2026-09-21.md) ·
[Frozen protocol](../../../docs/pong/motion-probe-protocol.md) ·
[Manual question revision](../../../docs/pong/teacher-rounds/D001-motion-reliability.md)

- [Programs](programs.json), [exact guidance diff](guidance-diff.txt), [provenance](provenance.json).
- [80 selected observations and audit labels](inputs.json), [coverage](coverage.json).
- [Frozen schedule and source](plan.json), [durable budget](budget.json).
- [480-response results and costs](results.json), [independent audit](verification.json).
- [LFS archive manifest](motion-probe-v1.manifest.json).

`inputs.json` contains reference labels for readers and the auditor. Actual model
requests contain only the original observation. All HTTP JSON requests/responses
and parsed predictions are retained in the LFS archive. The original 66,020-state
pool is reconstructed from the separate, already published
[question-diagnostics training archive](../question-diagnostics-v1/README.md).
No new frames or videos were produced because this study queried fixed states.

## Restore and verify without model access

Restore question-diagnostics-v1 using its linked instructions, then:

```bash
git lfs pull --include='experiments/pong/motion-probe-v1/**'
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/motion-probe-v1/motion-probe-v1.manifest.json \
  --out artifacts/restored-motion-probe
uv run python scripts/motion_probe.py verify \
  --pack artifacts/restored-motion-probe/motion-probe-v1/pack \
  --run artifacts/restored-motion-probe/motion-probe-v1/run \
  --source artifacts/restored-question-diagnostics/question-diagnostics-v1/local \
  --out artifacts/motion-probe-audit
```

These verification commands need no API key and make no model calls. They
regenerate state selection, check original source hashes and recompute metrics
from validated responses. Choose fresh output directories. The live command is
separate, requires an explicit backend, enforces the frozen cap and never resumes
or overwrites an existing output. Re-querying a stochastic service is a new
realization, not reproduction of the original HTTP response.
