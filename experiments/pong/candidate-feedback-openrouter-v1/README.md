# Pong candidate-feedback study: reviewed local evidence

Closed on owner request. The original run remains **incomplete**: HTTP 502 stopped
second-round training after 6,106 attempts. One A/B round completed; B was accepted
on development (+1.5 mean over V2), A rejected (-12.5). No final evaluation ran,
and the second A teacher never received the rejected candidate's experience.

[Closure report](../../../docs/pong/candidate-feedback-results-2026-09-24.md) ·
[Frozen protocol](../../../docs/pong/candidate-feedback-openrouter-protocol.md)

- [Descriptive episode results](descriptive-results.json), [costs](costs.json).
- [Original-run verification](verification.json), [closure](closure.json).
- Original [plan](records/plan.json), [status](records/status.json), [budget](records/budget.json).
- [Archive manifest](candidate-feedback-openrouter-v1.manifest.json),
  [restored verification](restored-verification.json), [restoration comparison](restoration-verification.json).

The archive retains all original run files except the empty runtime lock, including
12 videos, original HTTP requests/responses, raw frame evidence, predictions,
teacher contexts/proposals and the interrupted trajectory. `records/` contains
byte-identical JSON/text files for browsing; `videos/` also exposes individual MP4s.
No credentials, ROMs or emulator snapshots are included. Source protocol and plan
are prospective; this report and audit are retrospective.

This is local reviewed evidence stored with Git LFS. No remote upload, preservation
or retrieval has been established.

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/candidate-feedback-openrouter-v1/candidate-feedback-openrouter-v1.manifest.json \
  --out artifacts/pong/restored-candidate-feedback-openrouter-v1
uv run python scripts/verify_candidate_study.py \
  --run artifacts/pong/restored-candidate-feedback-openrouter-v1/candidate-feedback-openrouter-v1 \
  --out artifacts/pong/restored-candidate-feedback-openrouter-v1-audit
```
