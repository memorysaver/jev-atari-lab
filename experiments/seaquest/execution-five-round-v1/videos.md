# Five-round study recordings

Six literal-control episodes and four Jev episodes, all full 60 fps videos including the 256-frame startup prefix. Local controls are explicitly not model predictions. See the [hash/frame index](video-index.json).

| Round | Actor | Seed | Controlled return | Life losses | Full video |
| --- | --- | --- | --- | --- | --- |
| 1 | literal-simple | 320 | 340 | 1 | [Watch](videos/round-01/literal-simple/seed-320/episode.mp4) |
| 1 | literal-simple | 321 | 300 | 1 | [Watch](videos/round-01/literal-simple/seed-321/episode.mp4) |
| 1 | literal-late-diver | 320 | 360 | 1 | [Watch](videos/round-01/literal-late-diver/seed-320/episode.mp4) |
| 1 | literal-late-diver | 321 | 340 | 1 | [Watch](videos/round-01/literal-late-diver/seed-321/episode.mp4) |
| 5 | literal-reference | 348 | 380 | 0 | [Watch](videos/round-05/literal-reference/seed-348/episode.mp4) |
| 5 | literal-reference | 349 | 420 | 0 | [Watch](videos/round-05/literal-reference/seed-349/episode.mp4) |
| 5 | baseline | 348 | 280 | 2 | [Watch](videos/round-05/baseline/seed-348/episode.mp4) |
| 5 | candidate | 348 | 260 | 1 | [Watch](videos/round-05/candidate/seed-348/episode.mp4) |
| 5 | baseline | 349 | 320 | 2 | [Watch](videos/round-05/baseline/seed-349/episode.mp4) |
| 5 | candidate | 349 | 220 | 3 | [Watch](videos/round-05/candidate/seed-349/episode.mp4) |

All ten episodes reached the fixed cap. State probes do not step the emulator; their original source traces and exact observations are in the archive.
