# Five-round Seaquest execution study evidence

Five rounds completed and stopped. No wording revision was promoted: the sealed
candidate regressed on final movement macro agreement (68.75% to 60.94%) and
paired game mean return (300 to 240). Literal late-diver controls scored 400 mean
on those same final starts, with zero model calls. This is a negative wording
result with useful strategy/execution diagnostics, not teacher learning or mastery.

[Report and lessons](../../../docs/seaquest/execution-five-round-results-2026-09-25.md) ·
[Frozen protocol](../../../docs/seaquest/execution-five-round-protocol.md) ·
[All ten recordings](videos.md)

- [Plan](records/plan.json), [results](records/results.json), [closed budget](records/budget.json),
  [finalist seal](records/finalist-seal.json).
- [Round-three proposal](records/round-03/proposal.json) and
  [round-four proposal](records/round-04/proposal.json), authored before evaluation.
- [Final metrics](final-metrics.json), [costs](costs.json), [closure](closure.json).
- [Historical comparison and label parity](historical-comparison.json),
  [conditional-branch composition](branch-composition.json).
- [Original audit](verification.json), [restored audit](restored-verification.json).
- [Archive manifest](seaquest-execution-five-round-v1.manifest.json),
  [video hashes and frame counts](video-index.json).

The archive retains exact training/final observations, source traces, sampling
provenance, original API exchanges, predictions, labels, every game transition,
full videos, proposals and audits. Labels were not sent to the model. Six new
literal-control episodes are explicitly separate from four Jev episodes. Historical
model calls in copied source traces are not counted as new calls or replications.

Use was 3,914 attempts, including two recovered HTTP 520 responses; reported cost
was US$0.573014148. There were two coordinator proposals and zero isolated teacher
calls. All ten videos and restored original-exchange/frame audits passed. Archive
and video files use Git LFS. No credentials, ROMs or emulator snapshots are included.

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/seaquest/execution-five-round-v1/seaquest-execution-five-round-v1.manifest.json \
  --out artifacts/seaquest/restored-execution-example
uv run python scripts/verify_seaquest_execution.py \
  --run artifacts/seaquest/restored-execution-example/execution-five-round-v1 \
  --out artifacts/seaquest/restored-execution-example-audit
```
