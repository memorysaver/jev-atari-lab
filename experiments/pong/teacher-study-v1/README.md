# Teacher study v1 evidence

**Incomplete study:** one completed teacher round; second-round A invocation failed.
Neither first-round candidate passed the frozen gate. No final tests were run.
Read the [report](../../../docs/pong/teacher-study-results-2026-09-20.md) and
[teacher log](../../../docs/pong/teacher-log.md) before interpreting videos.

- [Descriptive results and costs](descriptive-results.json), [episode table](episodes.csv).
- [Independent verification](verification.json), [closure](closure.json).
- Original [plan](records/plan.json), [terminal status](records/status.json),
  [budget](records/budget.json), [parser continuation](records/continuations/parser-recovery.json).
- Exact teacher packets, outputs and changes: [A round one](records/round-01/A/question-changes.json),
  [B round one](records/round-01/B/question-changes.json),
  [failed round-two invocation](records/round-02/A/teacher/invocation-1/execution.json).
- [LFS archive manifest](teacher-study-v1.manifest.json): checksums and every member.

`records/` contains byte-identical selected original records for browsing. The LFS
archive contains the entire original run except the empty runtime lock, all 12
videos, frame/action traces, requests/responses, teacher contexts and failures,
original/continuation runner logs, independent replay audits and report JSON.
The manifest preserves original bytes; no credentials, ROMs or emulator snapshots
are included. Missing historical diagnostic bodies cannot be reconstructed.

## Watch actual episodes

All 12 videos are also published individually under `videos/`, using Git LFS.
These are original recordings; API waits are excluded from simulation-time video.

- A interception candidate: [seed 66](videos/round-01/A/development/candidate/seed-66/jev/seed-66/replay.mp4),
  [seed 67](videos/round-01/A/development/candidate/seed-67/jev/seed-67/replay.mp4); both lost 0:21.
- B four-frame lookahead: [seed 66](videos/round-01/B/development/candidate/seed-66/jev/seed-66/replay.mp4),
  [seed 67](videos/round-01/B/development/candidate/seed-67/jev/seed-67/replay.mp4); both capped, at 7:18 and 12:12.

## Restore and independently audit

From the repository root, with the locked environment installed:

```bash
git lfs pull --include='experiments/pong/teacher-study-v1/**'
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/teacher-study-v1/teacher-study-v1.manifest.json \
  --out artifacts/restored-teacher-study
uv run python scripts/verify_teacher_study.py \
  --run artifacts/restored-teacher-study/teacher-study-v1/run \
  --out artifacts/restored-teacher-study-audit
uv run python scripts/summarize_teacher_study.py \
  --run artifacts/restored-teacher-study/teacher-study-v1/run \
  --audit artifacts/restored-teacher-study-audit \
  --out artifacts/restored-teacher-study-report
```

Choose new output directories: verification/report commands preserve previous
outputs. These commands make no model calls and need no API credentials. Replay
uses the pinned environment and locally available game installation; it re-executes
recorded actions rather than regenerating Jev responses.

The independent verifier checks frame hashes, observations, rewards, exchanges,
program lineage, teacher-visible packets, gates, budgets and the explicit parser
continuation. A verified incomplete study remains incomplete. Requested teacher
model settings remain distinct from unavailable provider model attestation.
