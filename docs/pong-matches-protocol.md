# Native-match feasibility protocol

This stage tests whether the existing direct policy can complete a native Pong
match within a practical API budget. It does not revise a question or establish
teacher learning. Final-test seeds remain untouched.

## Local calibration

Before selecting the live horizon, run random, literal 4px tracking, and a new
reflected-intercept controller on **training seeds 50, 51, 52**, capped at 20,000
controlled raw frames per episode. No API requests or videos are needed for this
calibration; record every decision and raw frame for replay. Preserve the working
source patch and its base revision because calibration precedes the protocol commit.

The intercept controller uses the same visible boxes and finite-difference velocity
as Jev. It projects rightward motion to paddle contact with approximate wall
reflection (playfield y=34..194), uses a 4px tolerance, recenters while the ball
moves away, and tracks the ball if velocity is unavailable. It reads no hidden
velocity or future emulator states. It is a candidate control, not an assumed
stronger or optimal policy. Its predictions are saved with each chosen action.

Calibration results: random lost all three games in 3,272..3,924 frames. Tracking
completed two losses in 13,037 and 17,401 frames, and reached the cap at 12-12 on
seed 50. Intercept completed two losses in 11,528 and 12,549 frames and reached the
cap at 5-17 on seed 50. Mean capped returns were -21, -12.67, and -15 respectively.
The new controller did not improve the primary score over tracking in this sample.
These are training-only observations used to assess duration, not held-out evidence.

## Frozen live feasibility trial

- Fresh development seed: **56**. One realization per arm; no final-test seed.
- Arms in order: random, track-4px, reflected-intercept, Jev v2.
- Jev program: `examples/vertical-policy-program.json`, unchanged hash
  `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.
- Model: `jev-1.13.0`, checked on every returned prediction.
- Existing RAM object observations, six ALE actions, probability argmax, hold=4,
  sticky=0.25, reset NOOPs=0..30, mode=0, difficulty=0.
- Stop each episode at native termination or **20,000 controlled raw frames**
  (at most 5,000 decisions). No intermediate point cutoff or fabricated terminal tail.
- One shared cap of **5,500 HTTP attempts**, including retries. Local arms use none.
  Stop the suite on an error, preserve the partial episode, and do not silently
  restart, raise the budget, switch policy, or fill missing actions.
- Record videos, every model request/response, every decision, every controlled
  frame, native termination, external cutoffs, API ledger and source commit.

The v2 question is selected from previous development evidence. The no-FIRE v3
question is not promoted or rerun here. This is a single-seed feasibility trial,
not a paired v2/v3 test, learning curve, or statistically reliable ranking.

## Metrics and censoring

Report return (scored minus conceded) through native termination or the frame cap.
Report native-match return only when a player reaches 21. Frame-capped games are
unfinished even when the agent leads; API/error prefixes have no completed
protocol score. Never drop partial work from cost accounting.

For each arm publish scheduled, started, evaluated, and native-completed counts;
points; frames; stop reason; full-match wins/losses; and all cost ledgers. Show both
win rate among completed games and confirmed wins divided by all scheduled games.
Treat unfinished/unstarted games as unknown results when giving possible win-rate
bounds. Completion-conditioned scores may be biased. Sample standard deviation
is undefined for one episode, and no confidence interval is claimed for this trial.

API latency pauses the emulator; videos show simulation time. Historical latency
suggests a capped Jev episode may take roughly 20-25 minutes in wall time, but
provider failures or latency changes can alter that. Token usage is reported, not
an invented monetary charge.

```bash
uv run --env-file "$HOME/.config/typesafe/credentials.env" jev-atari match-suite \
  --backend jev --arms random track-4px intercept jev \
  --seeds 56 --split development --max-frames 20000 \
  --program examples/vertical-policy-program.json --model jev-1.13.0 \
  --max-api-calls 5500 --video --source-revision COMMIT \
  --out artifacts/pong-match-feasibility-v1
```
