# OpenRouter Jev playback pilot

The requested `~typesafe/jev-latest` alias returned
`typesafe/jev-1.13-20260917` through OpenRouter's Decisions API. One access request
and all 100 subsequent playback requests succeeded. Playback ran 400 controlled
frames at 0:0 and replayed successfully. This validates transport and playback,
not policy improvement or equivalence with the direct endpoint.

[Protocol and report](../../../docs/pong/openrouter-migration.md) ·
[Original video](replay.mp4) · [Verification](verification.json)

- [Access-check result](preflight-result.json), [episode summary](summary.json).
- [Episode manifest](manifest.json), including alias, required response-model identity and limits.
- [Supplementary plan record](plan.json), explicitly written after the run's initial metadata failure.
- [Archive manifest](openrouter-player-pilot-v1.manifest.json), [restored replay](restored-verification.json).

The source and schedule were committed before playback. The supplementary JSON
plan writer failed before launch and was subsequently reconstructed with an explicit
timing/deviation note. The original episode manifest and client enforced the same
declared model pin, 100-attempt ceiling and zero retries. No adaptive changes occurred.

Total OpenRouter-reported cost for 101 requests was US$0.007068852; this is not an
invoice reconciliation. The previous TypeSafe experiment remains closed and has
not been resumed, rewritten or pooled with these results. No final-test seed was used.

## Restore

The LFS archive includes the original access exchange, all 100 playback exchanges,
observations, predictions, actions, rewards, frame records, video and audit. It is
prepared locally; no remote push or retrieval is claimed. Choose fresh paths:

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong/openrouter-player-pilot-v1/openrouter-player-pilot-v1.manifest.json \
  --out artifacts/restored-openrouter-player
uv run jev-atari replay \
  --episode artifacts/restored-openrouter-player/openrouter-player-pilot-v1/episode \
  --out artifacts/restored-openrouter-player-audit
```

Restoration checks every archived member's checksum. Replay requires no model calls
and verifies recorded observations, frames and rewards against the local emulator.
