# Seaquest fixed-question Jev pilot v1

Prospective, 2026-09-24. Owner requested continued research. The separate fresh
observation-v2 gate passed before this pilot was specified; its results do not
establish policy skill. This pilot measures basic control and coverage with a
**coordinator-authored fixed question**, not an isolated teacher proposal or learning.

## Frozen contract

- Source implementation: `jev_atari.seaquest_pilot`; exact baseline is
  `SeaquestProgram()` and its JSON/hash in the pre-call plan.
- Training seeds **310,311**, in that order. No development or final cases used.
- Maximum **800 decisions / 3,200 controlled raw frames per seed**, or earlier
  native termination. No automatic FIRE/reset no-ops/life-loss controller.
- ALE Seaquest mode 0, difficulty 0, frameskip one, four-frame action hold, sticky
  0.25, all 18 native actions. Record ROM/dependency versions before calls.
- `seaquest-objects-v2`, including three raw-time history snapshots; history resets
  at unavailable animation/end states and native life losses. Observation mapping
  and provisional semantics are fixed throughout the pilot. No inferred best action.
- One native-action Choice; validate all probabilities and decode probability
  argmax with the existing provider-choice tie handling. No action masks/fallback.
- OpenRouter Decisions endpoint, requested `~typesafe/jev-latest`, response pinned
  to `typesafe/jev-1.13-20260917`. Model drift stops before executing an action.
- No teacher invocations, adaptive prompt edits, resampling for quality, selector,
  success-conditioned stopping, or native-game mastery claim.

## Admission, retries and total budget

Require the completed [v2 observation gate](observation-v2-protocol.md) and original
raw-frame replay verifications. Commit this protocol and implementation, require
a clean worktree, and write source/gate/program/model/seed/budget metadata before
live access. Never overwrite an existing run or reset its clock/budget.

A durable global budget reserves and fsyncs **before every HTTP attempt**:
**2,000 attempts total**, including retries, for at most 1,600 executed decisions.
A 7,200-second deadline starts on the first attempted request. Unused capacity does
not authorize extra episodes or more seeds. Budget exhaustion stops incomplete.

Per decision, at most two identical-request retries after transport exceptions or
HTTP 429/500/502/503/504/529. The emulator remains on the same unexecuted observation.
Retries count against the same global cap. No retry for payment/authentication errors,
invalid JSON/choices, response-model drift or a returned candidate/action of poor
quality. Preserve every failed attempt and original successful body; never log keys.
This is a new prospective retry policy; stopped Pong budgets/protocols stay closed.

## Measurements and controls

Primary descriptive outcome: native score at native end or the fixed cap, with
actual frame/decision counts. Report native life losses, time spent below starting
surface y=46, maximum observed carried-diver count and action histogram. These are
coverage diagnostics, not independently validated causes of death/rescue success.
Zero score at the surface is lack of active play, not survival-based success.

Run random and original scripted-sweep local controls on the same two training
seeds and 3,200-frame caps, with matched reset/sticky/hold/native actions. No model
calls for controls. Their semantic representation is irrelevant to their fixed
random/open-loop actions; their raw trajectories are retained and replayed.
Do not treat two seeds, repeated frames or shared starting states as optimizer
replications. Do not tune the frozen Jev prompt after seeing these controls.

Retain raw-frame RAM/RGB hashes, observations, all requests/responses, predictions,
actions/rewards, videos, API timing and reported usage/cost. Replay every trajectory;
reconstruct action decoding from its original response. Monetary totals cover only
reported successful-response usage, not unknown failed-request billing.

After completion or a technical stop, audit/report the result and preserve local
reviewed evidence. A passed instrumentation pilot can inform a separately frozen
teacher study, but does not itself establish feedback benefit or mastery.
