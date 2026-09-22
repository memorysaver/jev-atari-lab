# C1-R1-B: criteria-edit teacher proposal

Search 1, round 1, arm B. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **no empirical feedback**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-1/B/teacher/invocation-1/packet.json), hash `673cd152ad34d23a0ca6b96fc13cb0be98f17a6a41dec97d47de64e44584edca`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-1/B/teacher/validated.json). Program: `pong-incoming-intercept`; hash `abfb6be24346e0546420ca61a5200e9eba59f4afac6445041c97fffa3ac69fc7`.

Teacher-reported hypothesis (not an observed result):

Tracking current ball height can leave the paddle behind an incoming diagonal trajectory. Targeting a credible arrival-height estimate may establish interception alignment earlier and reduce conceded points.

Operator: Replace guidance and all six action-criterion descriptions with incoming-interception targeting.

Predicted changes: During reliably observed incoming flight, movement should follow predicted arrival height, sometimes differing from current-height tracking. Uncertain trajectories retain current-height tracking. This may improve points scored minus conceded through more successful returns; no improvement has been measured.

Regression risks: Finite-difference estimates can be stale near collisions, and uncertain wall limits can invalidate long projections. Prediction errors, sticky actions, and the fixed four-frame interval may cause overshoot. Conservative fallback may limit gains, and successful returns do not guarantee more points scored.

Referenced training examples: none.

### Exact guidance

````text
Which action should align the player paddle with the ball's expected arrival height? Read player and ball from observation.objects and use the supplied history to estimate ball motion when available. A bbox is [x, y, width, height]; vertical center is y + height/2. Larger y means lower. The player is the right paddle: RIGHT moves UP and LEFT moves DOWN.
Use one principal change: target the incoming ball's predicted interception height instead of always chasing its current height. When consecutive observations establish rightward ball motion toward the player, estimate the time until the ball's right edge reaches the player's left edge from their horizontal gap and the ball's horizontal speed. Project the ball center vertically over that time using its observed vertical speed. Account for top/bottom reflections only when the ball-center bounce limits are established by the supplied observation/history; do not invent boundary coordinates. If a possible reflection makes the projection uncertain, use the current ball center. Use consistent time units for displacement and arrival time. Do not extrapolate across an observed bounce or reset using stale velocity.
If velocity is missing, inconsistent, or the ball is moving away, use the current ball center as the target. Missing velocity is unknown, not zero. If player or ball is absent, choose NOOP.
If the target is more than four pixels below the player center, choose LEFT. If more than four pixels above, choose RIGHT. Within four pixels, choose NOOP. Prefer non-FIRE actions over their equivalent FIRE alternatives. Horizontal direction determines whether prediction applies, never the paddle's vertical movement directly. Reconsider after each four-raw-frame decision using the new observation.
````

### Exact action criteria

**NOOP**

````text
Choose when the selected target height is within four pixels of the player center, or when player or ball is absent. The target is a credible incoming interception estimate when available, otherwise the current ball center. Prefer this stationary action over FIRE.
````

**FIRE**

````text
Stationary FIRE alternative when the selected target is within four pixels of the player center, or an object is absent. It supplies no vertical correction; prefer NOOP when both have the same movement effect.
````

**RIGHT**

````text
Move UP when the selected target is more than four pixels above the player center. Use a credible incoming interception estimate, otherwise current ball height. The player being on the right or the ball traveling right does not itself justify this action.
````

**LEFT**

````text
Move DOWN when the selected target is more than four pixels below the player center. Use a credible incoming interception estimate, otherwise current ball height. Larger screen y means lower. Prefer this over LEFTFIRE for the same correction.
````

**RIGHTFIRE**

````text
Move UP with FIRE when the selected target is more than four pixels above the player center, using the same interception estimate or fallback as RIGHT. Prefer RIGHT when the movement effects are equivalent.
````

**LEFTFIRE**

````text
Move DOWN with FIRE when the selected target is more than four pixels below the player center, using the same interception estimate or fallback as LEFT. Prefer LEFT when the movement effects are equivalent.
````

## Observed evaluation and disposition

Disposition: **rejected**.

Paired development return gains over fresh v2: [-4.0, 1.0]; mean -1.5. Previous best development gain: +0. The previous best is historical, not a freshly rerun incumbent.

Selection is an engineering gate, not a held-out improvement claim. Final evaluation follows only after all selected programs are sealed.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
