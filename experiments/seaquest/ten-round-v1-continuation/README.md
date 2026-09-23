# Ten-round Seaquest study: reviewed local evidence

Exactly ten rounds and 24 bounded episodes completed; all unused model-call
capacity is closed. The selected round-three program improved development mean
return from 80 to 370 and final mean from 80 to 290, with no seed regression.
Both prospective gates passed. This is bounded policy improvement over the
collapsed baseline, not mastery or an estimate of teacher-feedback benefit.

[Full report](../../../docs/seaquest/ten-round-results-2026-09-24.md) ·
[Frozen protocol](../../../docs/seaquest/ten-round-protocol.md) ·
[Continuation contract](../../../docs/seaquest/ten-round-continuation-protocol.md) ·
[All recordings](videos.md)

- [Plan](records/plan.json), [all round results](records/results.json),
  [closed budget](records/budget.json), [finalist seal](records/finalist-seal.json).
- [Episode metrics and paired gates](final-metrics.json), [closure](closure.json),
  [API costs](costs.json).
- [Original full audit](verification.json), [restored full audit](restored-verification.json).
- [Literal-rule diagnostics](literal-rule-check-final.json),
  [checker method](literal-rule-check-final-method.txt), [movement-branch counts](literal-branch-diagnostic.json).
- [Archive manifest](seaquest-ten-round-v1-continuation.manifest.json) and
  [24-video hash/frame index](video-index.json).
- [Preserved original interruption](../ten-round-v1-interrupted/README.md).

The archive contains original requests/responses, actions, observations, raw-frame
RAM/RGB hashes, rewards, life/end flags, pixel checks, exact proposals, audits and
all videos. Round four includes an explicitly documented exact-state continuation
following HTTP 520, with the original partial recording retained. Imported calls
are counted once: 16,848 attempts, 16,778 executed decisions, 70 failed attempts,
US$2.235472092 provider-reported cost, zero isolated teacher calls.
The interactive coordinator authored seven proposals; there is no external
teacher transcript or no-feedback control.

All 327 archive members passed checksums. Restored API/frame/video audits matched
the original audit and cost records. Archives and videos are local Git LFS objects;
no remote retrieval is claimed. No credentials, ROMs or emulator snapshots are included.

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/seaquest/ten-round-v1-continuation/seaquest-ten-round-v1-continuation.manifest.json \
  --out artifacts/seaquest/restored-ten-round-example
uv run python scripts/verify_seaquest_research.py \
  --run artifacts/seaquest/restored-ten-round-example/ten-round-v1-continuation \
  --out artifacts/seaquest/restored-ten-round-example-audit
```
