# Ms. Pac-Man direct versus target-action pilot v1, 2026-09-28

Frozen after six zero-API calibration episodes and before any live request.
Owner authorization: proceed with the proposed small Ms. Pac-Man pilot, 2026-09-28.
This is a fixed-program comparison, not teacher learning or mastery.

## Entry evidence and limitations

Calibration v1 used training seeds 510/511. Controlled returns were random 300/300,
pellet pursuit 730/550, and ghost-aware pursuit 1760/700. All 1,890 control
observations had pixel-supported player coordinates within three pixels of the
corridor graph. Six complete videos and every raw frame replayed. These are two
starts, not population estimates. Other object visibility remains provisional;
no exhaustive ghost-state, collision, power-pellet or maze-transition validation.
All nine native actions are retained. Collection stops on the first maze change.

## Fixed programs and observation contract

`src/jev_atari/mspacman_questions.py:PROGRAM` contains the exact frozen prompts.
The **direct** arm selects one action in one request. The **two-stage** arm first
selects UNAVAILABLE, PELLETS or one of four ghost slots, then requests an action
using that model-selected intent and the identical original observation. Nothing
steps the emulator between those two requests. No controller repairs the answer.
All nine actions remain in the final question in both arms. Observations include
positions, visible regular pellets, geometry, exits and two historical frames;
no reference intent, safe action or precomputed route enters either request.

The strategy is nearby-normal-ghost avoidance (L1 distance at most 32), otherwise
shortest-path pursuit of a visible regular pellet. The local reference implements
this strategy literally using the supplied corridor graph. Equal shortest routes
can have different valid first actions; exact Python-action agreement is a
conservative diagnostic, not optimality or a claim that every mismatch is wrong.

## Schedule and sealed starts

- Build 24 training probes from calibration trajectories, 12 evade/12 collect.
  Selection is deterministic in avoid/pellet/random and seed 510/511 order,
  at most six per group from each source episode, keeping distinct observation
  hashes. Consecutive/repeated underlying situations remain correlated; these
  are not 24 independent trials. Freeze packet SHA-256 before requests.
- Evaluate direct then two-stage on each probe: exactly 72 planned attempts.
- Development seeds **516 and 517**, each with a 272-frame NOOP prefix, up to
  **2,048 controlled raw frames**, eight-frame action hold, sticky 0.25.
- On each start run random, pellet-only and ghost-aware local controls, plus
  both model arms. Alternate model-arm order between seeds. Ten episodes max.
- No program changes after probes or development access. No final tests;
  seeds 518/519 remain unused. Do not present this pilot as final confirmation.
- Every episode records a complete 60-fps video and raw-frame RAM/RGB hashes,
  rewards/lives, observations and actions. Every API exchange is retained with
  credential redaction, including failed attempts. Replay all completed episodes.

## Resource and transport limits

Explicit backend **OpenRouter**, `https://openrouter.ai/api/alpha/decisions`.
Requested `~typesafe/jev-latest`; require `typesafe/jev-1.13-20260917` in every
response, stopping before action execution on mismatch. Existing protected local
credentials are read via an environment file; no credentials enter this repo.

Maximum planned attempts: 72 + 2*(256 + 512) = **1,608**. Durable hard ceiling
**1,700 HTTP attempts**, **zero retries**, **one hour**, and stop before the next
request once cumulative reported cost reaches **US$2** (one request can cross
that threshold). Charge both stages; report actual calls, tokens where supplied,
API wall time and provider-reported costs separately from emulator frames.
Stop on transport, response validation or model-identity error; no fallback,
allocation reopening or implicit change of backend/model. Close unused capacity
on completion or interruption. Missing cost fields are not proof of free use.

## Outcomes

Primary: paired native controlled return, two-stage minus direct, by seed.
Exploratory gameplay gate: nonnegative gain on both starts and positive mean gain.
Report life losses, end reasons, calls and cost alongside returns. The arms have
equal environment opportunities; two-stage has up to twice the requests. This
cannot establish equal-cost superiority or isolate decomposition from compute.

Diagnostics on fixed probes: intermediate-intent agreement and final literal-action
agreement, with separate evade/collect denominators. Report one- and two-stage
agreement on the same observations. Intermediate accuracy alone cannot pass the
gameplay gate. Two starts and one deterministic packet do not establish reliable
improvement; no adaptive teacher experiment is launched by this protocol.
