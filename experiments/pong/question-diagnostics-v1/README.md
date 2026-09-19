# Question execution diagnostics v1

Zero new Jev/teacher calls. This study analyzes already published Jev responses
and separately runs four Python interpretations on four training seeds.
It is not a promoted Jev policy, a teacher update or a held-out performance claim.

[Full report](../../../docs/pong/question-diagnostics-results-2026-09-20.md) ·
[Frozen protocol](../../../docs/pong/question-diagnostics-protocol.md)

- [Adherence, confusion matrices and strata](adherence.json).
- [One original Jev request/response with opposite requested direction](example.json).
- [Local trial plan](plan.json), [per-seed outcomes and denominators](local-results.json),
  [independent replay verification](verification.json).
- [LFS archive manifest](question-diagnostics-v1.manifest.json).

The archive preserves the initial analysis and the later `analysis-extended`
version, which adds an explicitly exploratory same-action subset and a deterministic
first-discrepancy example. `adherence.json` is the extended result. No original data,
frozen controller or trial outcome was overwritten. Original Jev evidence remains
in the separate [teacher-study-v1 archive](../teacher-study-v1/README.md); source
hashes in the diagnostic results identify the exact inputs.

All 16 local videos are in the archive and separately under `videos/`. Example
seed-80 videos: [v2](videos/v2/seed-80/replay.mp4),
[interception](videos/intercept/seed-80/replay.mp4),
[lookahead](videos/lookahead/seed-80/replay.mp4),
[conservative lookahead](videos/lookahead-conservative/seed-80/replay.mp4).
The conservative 14:8 episode is capped and unfinished, not a completed win.

## Restore and verify local strategy trials

```bash
git lfs pull --include='experiments/pong/question-diagnostics-v1/**'
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/question-diagnostics-v1/question-diagnostics-v1.manifest.json \
  --out artifacts/restored-question-diagnostics
uv run python scripts/question_diagnostics.py verify \
  --run artifacts/restored-question-diagnostics/question-diagnostics-v1/local \
  --out artifacts/question-diagnostics-replay
```

## Reproduce the adherence analysis

First restore teacher-study-v1 using its linked instructions, then:

```bash
uv run python scripts/question_diagnostics.py analyze \
  --study artifacts/restored-teacher-study/teacher-study-v1/run \
  --out artifacts/reproduced-question-adherence
cmp experiments/pong/question-diagnostics-v1/adherence.json \
  artifacts/reproduced-question-adherence/results.json
```

Use new output directories. Neither command calls a model or needs API credentials.
Adherence measures agreement with explicit interpretations, not optimal action
correctness. Python outcomes cannot be substituted for Jev outcomes.
