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

## M002 — fixed direct versus target-action comparison, 2026-09-28

Prospective after calibration: freeze two prompts using identical observations
and native actions. The coordinator saw only calibration seeds 510/511. No
Ms. Pac-Man development/final traces informed these programs. No teacher is
invoked. The two-stage program names its own intent and passes that answer
verbatim to its action question. The direct program performs both instructions
in one request. Exact prompts are in `mspacman_questions.py:PROGRAM` and copied
into the run. This changes both decomposition and HTTP-request count; it cannot
isolate equal-compute decomposition benefit.

The frozen 24-observation packet SHA-256 is
`a36a792d2a1a1067df6a7382c613465cbea96f448846778b27c527e592f505ec`.
The [pilot protocol](pilot-protocol.md) fixes two development seeds, outcomes,
1,700-attempt ceiling, zero retries and one-hour/US$2 reported-cost stopping.
No edits are permitted after any probe or development result. Final seeds stay
unused. Exact literal-action agreement includes route-tie ambiguity, reported
as a diagnostic rather than automatic proof of a wrong action.

### M002 outcome

One HTTP attempt failed at transport before a response, model action or development
run. The network environment failed a separate DNS lookup. The full unused
allocation was closed with no retry or fallback. All frozen programs and the
packet are retained; no performance claim or proposal promotion is possible.
See [the report](pilot-results-2026-09-28.md) for evidence and continuation boundary.
