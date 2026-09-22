# C1-R2-A: criteria-edit teacher proposal

Search 1, round 2, arm A. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **training only**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-2/A/teacher/invocation-1/packet.json), hash `60fbcc85749809d804e3cda8a873f30727f27e81320728291db30c19b70c56a0`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-2/A/teacher/validated.json). Program: `pong-relative-motion-lookahead-v1`; hash `67d2e249f331df8db6fe21a26369487bea5bd93ed2e36332e597fe859f5feef4`.

Teacher-reported hypothesis (not an observed result):

Current-center tracking ignores substantial paddle motion during and after an action. In train-103-decision-232, NOOP accompanies another 16 pixels of downward displacement; in train-103-decision-332 and train-103-decision-499, a reversal request still accompanies motion in the previous direction. Comparing short-term forecast centers may initiate braking or reversal earlier and reduce oscillation, potentially reducing concessions. These observations do not establish an improvement in points scored minus conceded.

Operator: Replace the instantaneous vertical-gap comparison with a two-raw-frame relative-motion forecast, retaining the four-pixel tolerance, missing-object hold and native action preferences.

Predicted changes: Movement should begin earlier when the ball is pulling away vertically and stop earlier when the paddle is closing rapidly. Some currently aligned states should request a correction because their forecast gap is large, while some visibly misaligned states should hold because their forecast centers converge. This could improve contact timing without requiring a full-flight intercept estimate.

Regression risks: Finite-difference velocities are averages, and sticky actions make future paddle displacement uncertain. Two-frame extrapolation may brake too early or trigger unnecessary reversals. Wall reflections are approximate, and clipped paddle boxes distort center motion. Short lookahead still cannot anticipate distant bounces. Changed contact positions could produce easier opponent returns or longer rallies, reducing scoring within the frame cap.

Referenced training examples: train-103-decision-232, train-103-decision-332, train-103-decision-499, train-102-decision-499, train-102-decision-365.

### Exact guidance

````text
Which action should reduce the anticipated vertical gap while avoiding overshoot? Read player and ball from observation.objects. A bbox is [x,y,width,height]; vertical center is y plus half height. Larger y means DOWN. RIGHT moves UP; LEFT moves DOWN. If either object is absent, choose NOOP.
Use a short lookahead instead of comparing only current centers. Estimate each object's vertical center two raw frames ahead by adding twice its vertical velocity to its current center, but only when that object's velocity_valid is true and velocity is available. Otherwise use its current center as a fallback; missing velocity is unknown, not evidence of rest. These estimates are approximate, especially after an action change.
For the ball forecast, reflect any excursion beyond approximate ball-center limits y=32 and y=194 back into the playfield. If history shows a recent vertical reversal and the latest velocity spans that bounce, use the current ball center until the direction becomes clear. Use the player's observed bbox height, including when clipped near a wall.
Compare the forecast ball center with the forecast player center. Ball more than four pixels ABOVE: RIGHT. More than four pixels BELOW: LEFT. Within four pixels: NOOP. Thus a paddle rapidly approaching alignment can stop before its current center reaches the ball; if its forecast passes the ball by more than four pixels, reverse. A ball moving vertically away can justify starting movement before the current gap exceeds four pixels. Horizontal travel alone never selects UP or DOWN.
Prefer NOOP, RIGHT and LEFT over their FIRE aliases. The lookahead does not change the action duration: act for the fixed four raw frames, then reconsider from the next observation.
````

### Exact action criteria

**NOOP**

````text
Hold when either essential object is absent or the two forecast centers defined in guidance differ by at most four pixels. This includes braking before current alignment when existing paddle motion is already closing the gap. Prefer NOOP to FIRE.
````

**FIRE**

````text
Provides the same vertical hold as NOOP. Appropriate when an essential object is absent or the forecast centers are within four pixels. It adds no vertical correction; prefer NOOP.
````

**RIGHT**

````text
Move UP when the forecast ball center is more than four pixels above the forecast player center. This can brake downward overshoot even if the ball is currently below the paddle. Use the velocity fallbacks in guidance. Prefer RIGHT to RIGHTFIRE.
````

**LEFT**

````text
Move DOWN when the forecast ball center is more than four pixels below the forecast player center. This can brake upward overshoot even if the ball is currently above the paddle. Use the velocity fallbacks in guidance. Prefer LEFT to LEFTFIRE.
````

**RIGHTFIRE**

````text
Move UP under the same condition as RIGHT: the forecast ball center is more than four pixels above the forecast player center. FIRE adds no vertical advantage; prefer RIGHT.
````

**LEFTFIRE**

````text
Move DOWN under the same condition as LEFT: the forecast ball center is more than four pixels below the forecast player center. FIRE adds no vertical advantage; prefer LEFT.
````

## Observed evaluation and disposition

Disposition: **rejected**.

Paired development return gains over fresh v2: [-1.0, 0.0]; mean -0.5. Previous best development gain: +0. The previous best is historical, not a freshly rerun incumbent.

Selection is an engineering gate, not a held-out improvement claim. Final evaluation follows only after all selected programs are sealed.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
