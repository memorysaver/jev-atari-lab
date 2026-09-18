# Calibrating native Pong match evaluation — 2026-09-18

Nine local episodes establish a practical duration range and expose why a frame
cap must not be reported as a completed match. Random play lost all three games
within 3,924 frames. Tracking and interception needed substantially longer, and
two episodes remained unfinished at 20,000 frames. No model calls were made.

This is training-only calibration on seeds 50, 51, 52, before freezing the separate
[development feasibility trial](pong-matches-protocol.md). The new interception
controller was specified before observing these outcomes and was not tuned afterward.

## Every outcome

All arms use the same RAM-derived objects, six ALE actions, hold=4, sticky=0.25,
mode=0, difficulty=0 and reset NOOPs=0..30. Cells show agent:opponent points.

| Seed | Policy | Score | Return | Raw frames | Native outcome |
| --- | --- | ---: | ---: | ---: | --- |
| 50 | Random | 0:21 | -21 | 3,272 | Loss |
| 50 | Track 4px | 12:12 | 0 | 20,000 | Unfinished |
| 50 | Intercept | 5:17 | -12 | 20,000 | Unfinished |
| 51 | Random | 0:21 | -21 | 3,360 | Loss |
| 51 | Track 4px | 2:21 | -19 | 13,037 | Loss |
| 51 | Intercept | 7:21 | -14 | 11,528 | Loss |
| 52 | Random | 0:21 | -21 | 3,924 | Loss |
| 52 | Track 4px | 2:21 | -19 | 17,401 | Loss |
| 52 | Intercept | 2:21 | -19 | 12,549 | Loss |

| Metric | Random | Track 4px | Intercept |
| --- | ---: | ---: | ---: |
| Mean return through termination or cap | -21 | -12.67 | -15 |
| Sample SD of those returns | 0 | 10.97 | 3.61 |
| Native completions / scheduled episodes | 3 / 3 | 2 / 3 | 2 / 3 |
| Confirmed wins / scheduled episodes | 0 / 3 | 0 / 3 | 0 / 3 |
| Mean return among completed matches only | -21 | -19 | -16.5 |

Completion-conditioned means reverse the apparent order of tracking and interception
because unfinished games are excluded. Neither mean alone establishes superiority.
The unfinished 12:12 game is not a draw and its hypothetical final result is unknown.
These three training seeds do not support population confidence or learning claims.

## The new controller

`reflected-intercept-4px-v1` uses the observed ball box and finite-difference velocity
to project contact with the right paddle. It approximates wall reflections using
playfield y=34..194, uses the existing 4px movement tolerance, and recenters when
the ball moves away. If velocity is unavailable it tracks the current ball center;
if an object is absent it requests NOOP. It never reads hidden emulator velocity,
simulates future states, or supplies its calculation to Jev.

The result does not establish a stronger baseline: its mean capped return was
worse than simple tracking. An approximate motion model and better-looking controller
design do not guarantee better control. Target positions and the prediction mode
are recorded with each decision so this behavior can be inspected.

## Duration and budget implications

Tracking and interception's completed matches took 11,528..17,401 raw frames,
roughly 2,882..4,351 decisions at hold=4. Some games needed more than 20,000 frames.
The separate first Jev match attempt therefore uses a 20,000-frame safety cap and
5,500 HTTP attempts, including retries, for at most 5,000 executed decisions.
This does not guarantee native completion. A larger multi-seed study remains future work.

## Evidence

The [results](../experiments/pong-match-calibration-v1-results.json),
[plan](../experiments/pong-match-calibration-v1-plan.json), and
[audit](../experiments/pong-match-calibration-v1-audit.json) are readable indexes.
The [LFS archive](../experiments/pong-match-calibration-v1-2026-09-18.tar.gz) and its
[manifest](../experiments/pong-match-calibration-v1-2026-09-18.manifest.json)
preserve all nine episodes: 105,071 controlled frames and 26,270 decisions.
Calibration did not record videos; the saved actions can render videos on replay.

The run used a working implementation before its commit. `source.json` and
`implementation-diff.txt` preserve its exact source patch, SHA-256 and base revision.
The subsequent implementation/protocol commit is `01db805`. All nine traces passed
emulator replay with matching observations, rewards and raw RAM/RGB hashes; the
verifier also recomputed every local action, native outcome and aggregate metric.
Auditing and restoration used no API calls.

```bash
git lfs pull
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong-match-calibration-v1-2026-09-18.manifest.json \
  --out restored-match-calibration
uv run python scripts/verify_matches.py \
  --run restored-match-calibration/pong-match-calibration-v1 \
  --out artifacts/match-calibration-audit
```
