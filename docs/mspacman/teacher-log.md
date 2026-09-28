# Ms. Pac-Man coordinator log

## M001 — observation and calibration setup, 2026-09-28

Status: prospective implementation and local calibration. Author: interactive
Codex coordinator; no isolated teacher call. The conversation reviewed completed
Pong, Seaquest and Freeway results. There is no train-only teacher isolation or
original standalone teacher transcript. No Ms. Pac-Man held-out data was seen.

Hypothesis: maze decisions can expose target-selection and action-execution
errors separately. First establish a grounded first-maze observation adapter and
native-score differences among random, pellet pursuit and ghost-aware pursuit.
The two local pursuit policies compute graph paths from the supplied geometry;
those paths and action labels do not enter model observations.

Exact implementation is in `src/jev_atari/mspacman.py` and collection/audit code
in `src/jev_atari/mspacman_pilot.py`. Per-run manifests retain source hashes.
The [calibration protocol](calibration-protocol.md) fixes starts, horizon, controls
and observation gates before calibration outcomes. All model capacity remains
unallocated until a separate bounded live protocol is frozen.
