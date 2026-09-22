# Criteria-edit teacher study: reviewed local evidence

**Incomplete:** HTTP 402 stopped the fourth of six scheduled rounds. Three rounds
completed and all six evaluated proposals were rejected. Two additional teacher
proposals lack complete development evaluation. No final tests were run.

[Report](../../../docs/pong/criteria-teacher-results-2026-09-23.md) ·
[Frozen protocol](../../../docs/pong/criteria-teacher-protocol.md) ·
[Teacher log](../../../docs/pong/criteria-teacher-log.md)

- [Every episode and descriptive results](descriptive-results.json), [costs](costs.json).
- [Original-run audit](verification.json), [terminal-state closure](closure.json).
- Original [plan](records/plan.json), [status](records/status.json), [budget](records/budget.json).
- [Archive manifest](criteria-teacher-v1.manifest.json), [restored-run audit](restored-verification.json).
- [Restoration comparison](restoration-verification.json), [restored cost record](restored-costs.json).

`records/` contains byte-identical original JSON and instruction files for browsing.
The LFS archive contains the complete original run except its empty runtime lock:
all 27 videos, observations, actions, predictions, raw frames, model exchanges,
teacher packets/proposals, 1,920 probe responses and the incomplete episode. The
videos are also available individually under `videos/`. API waits are absent from
simulation-time recordings. No credentials, ROMs or emulator snapshots are included.

## Exact teacher records

| Search / round | Experience feedback A | No empirical feedback B |
| --- | --- | --- |
| 1 / 1 | [C1-R1-A](../../../docs/pong/teacher-rounds/C1-R1-A.md) | [C1-R1-B](../../../docs/pong/teacher-rounds/C1-R1-B.md) |
| 1 / 2 | [C1-R2-A](../../../docs/pong/teacher-rounds/C1-R2-A.md) | [C1-R2-B](../../../docs/pong/teacher-rounds/C1-R2-B.md) |
| 2 / 1 | [C2-R1-A](../../../docs/pong/teacher-rounds/C2-R1-A.md) | [C2-R1-B](../../../docs/pong/teacher-rounds/C2-R1-B.md) |
| 2 / 2, incomplete | [C2-R2-A](../../../docs/pong/teacher-rounds/C2-R2-A.md) | [C2-R2-B](../../../docs/pong/teacher-rounds/C2-R2-B.md) |

These pages render recorded proposals and observed dispositions, not reconstructed
private reasoning. The fourth round has no selection result. The interrupted B
episode's 1:1 score after 684 frames is not a complete evaluation.

## Restore and audit without model access

The archive is prepared locally. **No remote push or retrieval has occurred.**
Choose fresh output directories:

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/criteria-teacher-v1/criteria-teacher-v1.manifest.json \
  --out artifacts/restored-criteria-teacher
uv run python scripts/verify_criteria_study.py \
  --run artifacts/restored-criteria-teacher/criteria-teacher-v1/run \
  --out artifacts/restored-criteria-teacher-audit
```

Restoration checks the archive and every member's SHA-256. The auditor replays all
27 trajectories, verifies teacher provenance and original model exchanges, and
recomputes the three completed selections and actual costs. Its explicit final
verification flag stays false. These commands need no model credentials or calls.
The frozen live experiment cannot be resumed or overwritten after its terminal stop.

Local restoration and all 27 replay checks passed. The original and restored
audits list teacher usage in different filesystem traversal order, so their cost
hashes differ. Every scalar cost and the multiset of teacher-usage events agree;
the restoration comparison records this explicitly. No monetary charge is inferred.
