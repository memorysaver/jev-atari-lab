# C2-R1-B: criteria-edit teacher proposal

Search 2, round 1, arm B. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **no empirical feedback**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-1/B/teacher/invocation-1/packet.json), hash `673cd152ad34d23a0ca6b96fc13cb0be98f17a6a41dec97d47de64e44584edca`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-1/B/teacher/validated.json). Program: `pong-incoming-intercept`; hash `26fbe1dbff5e34aa8618e0b6c1b236bf5cc8b4fad959abcde9d208955a05814c`.

Teacher-reported hypothesis (not an observed result):

Current-height tracking may lag behind a diagonally approaching ball. Targeting its estimated arrival height could position the paddle earlier and reduce conceded points, provided motion and rebound estimates are reliable.

Operator: Replace current-height tracking with history-based incoming interception; preserve movement meanings, deadband, missing-object fallback and non-FIRE preference.

Predicted changes: During clear incoming diagonal motion, movement should begin toward the estimated contact height before the ball reaches that height. Outgoing or uncertain-motion states should retain current-height tracking. This may improve points scored minus conceded through more successful returns; no empirical improvement is established.

Regression risks: Finite-difference estimates near rebounds, uncertain wall locations and long flight times can produce incorrect targets. Sticky actions can cause overshoot despite reassessment. More reliable contact may still produce easy opponent returns, so fewer misses need not yield a better point differential.

Referenced training examples: none.

### Exact guidance

````text
Which action best aligns the player paddle with the ball's expected arrival height? Read player and ball in observation.objects. A bbox is [x, y, width, height]; vertical center is y plus half the height. Larger y means DOWN. The player is the right paddle: RIGHT moves UP and LEFT moves DOWN, regardless of the ball's horizontal direction.
Use observation.history, when available, to estimate ball motion from successive positions. Missing velocity is unknown, not zero. The principal change is to target the incoming ball's predicted vertical position at the player's left face instead of always chasing its current height. When the ball is moving toward the player and motion is sufficiently clear, estimate the remaining horizontal travel time and corresponding vertical travel. Account for top or bottom rebounds only when the relevant boundary is supported by the observation or history; do not invent wall coordinates or extrapolate straight through a known wall. After an apparent rebound, use the newest consistent motion rather than averaging across the reversal. If the arrival estimate is uncertain, use the current ball center. Also use the current ball center while the ball travels away.
If the target is more than four pixels below the player center, choose LEFT. If it is more than four pixels above, choose RIGHT. Within four pixels choose NOOP. If player or ball is absent, choose NOOP. Prefer non-FIRE actions when a FIRE alias gives the same movement. Act for the next four raw frames, then reassess; do not commit to a full predicted trajectory.
````

### Exact action criteria

**NOOP**

````text
Hold position when the target height is within four pixels of the player center, or when player or ball is absent. The target is the supported incoming arrival estimate, otherwise the current ball center. Prefer this stationary action over FIRE.
````

**FIRE**

````text
Stationary FIRE alternative when the same alignment conditions as NOOP apply. It provides no vertical correction; prefer NOOP when firing has no distinct benefit supported by the observation.
````

**RIGHT**

````text
Move UP when the target height is more than four pixels above the player center. Use the supported incoming arrival estimate, otherwise the current ball center. Being the right paddle or seeing rightward ball motion alone does not justify RIGHT.
````

**LEFT**

````text
Move DOWN when the target height is more than four pixels below the player center. Use the supported incoming arrival estimate, otherwise the current ball center. Reassess after the requested duration to avoid passing the target.
````

**RIGHTFIRE**

````text
Move UP with FIRE when the target is more than four pixels above the player center, under the same targeting rule as RIGHT. Prefer RIGHT unless the observation supports a distinct benefit from firing.
````

**LEFTFIRE**

````text
Move DOWN with FIRE when the target is more than four pixels below the player center, under the same targeting rule as LEFT. Prefer LEFT unless the observation supports a distinct benefit from firing.
````

## Observed evaluation and disposition

Disposition: **rejected**.

Paired development return gains over fresh v2: [-1.0, 0.0]; mean -0.5. Previous best development gain: +0. The previous best is historical, not a freshly rerun incumbent.

Selection is an engineering gate, not a held-out improvement claim. Final evaluation follows only after all selected programs are sealed.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
