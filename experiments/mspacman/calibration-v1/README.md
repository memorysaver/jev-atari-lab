# Ms. Pac-Man calibration v1: reviewed local evidence

Six zero-API episodes completed under the [frozen protocol](../../../docs/mspacman/calibration-protocol.md).
[Results and limitations](../../../docs/mspacman/pilot-results-2026-09-28.md).

| Controller | Seed | Controlled return | Video |
| --- | ---: | ---: | --- |
| Random | 510 | 300 | [Watch](videos/random-seed-510.mp4) |
| Random | 511 | 300 | [Watch](videos/random-seed-511.mp4) |
| Pellet pursuit | 510 | 730 | [Watch](videos/pellet-seed-510.mp4) |
| Pellet pursuit | 511 | 550 | [Watch](videos/pellet-seed-511.mp4) |
| Ghost-aware pursuit | 510 | 1760 | [Watch](videos/avoid-seed-510.mp4) |
| Ghost-aware pursuit | 511 | 700 | [Watch](videos/avoid-seed-511.mp4) |

All videos include the 272-frame startup prefix at 60 fps. Five episodes ended
natively; ghost-aware seed 510 reached the controlled frame cap. These are local
Python controllers, not Jev gameplay or learned policies.

[Plan](plan.json), [results](results.json), [original audit](audit.json),
[restored audit](restored-audit.json), [video hashes/counts](video-index.json),
[archive manifest](mspacman-calibration-v1.manifest.json).
The archive preserves 33 files: complete transitions with raw RAM/RGB hashes,
observations, original videos, initial images, manifests and summaries. No ROMs,
emulator snapshots or credentials. Local LFS preservation only; no remote claim.

```bash
uv run python scripts/restore_experiments.py \
  --manifest experiments/mspacman/calibration-v1/mspacman-calibration-v1.manifest.json \
  --out artifacts/mspacman/restored-calibration-example
uv run python -m jev_atari.mspacman_pilot audit \
  --out artifacts/mspacman/restored-calibration-example/calibration-v1
```
