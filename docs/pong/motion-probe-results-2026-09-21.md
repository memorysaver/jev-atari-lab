# Motion-reliability probe: explicit wording regressed

**Observed negative result:** The precise motion-reliability question matched the
conservative reference on only **1/16 responses** in the primary uncertain-motion
conflict stratum, versus **6/16** for the original ambiguous question. Across the
balanced 80-state probe, agreement fell from **99/160 (61.88%)** to **73/160 (45.63%)**.
The hypothesis that this explicit definition would improve that behavior was not
supported by this evaluation. The question is not promoted; the gameplay reference
remains v2. No gameplay or final-test evaluation was performed.

This is a fresh **480-call Jev 1.13.0 evaluation**, following the
[frozen protocol](motion-probe-protocol.md). It is separate from the expired teacher
study. The interactive coordinator authored the new question after prior development
exposure; it is a manual diagnostic intervention, not a newly isolated teacher
proposal or learned optimizer step. See [D001](teacher-rounds/D001-motion-reliability.md)
for exact before/after text and provenance.

## What changed

The original B question refers to "reliable" finite differences and an "evident
bounce" without a unique executable definition. The new question explicitly
requires incoming valid velocity, the last three history samples to contain visible
ball boxes with increasing timestamps, and no reversal in the signs of successive
x or y displacements. Otherwise track current height. Eligible states use vy*4,
the same four-pixel deadband and the same native action meanings.

This corresponds to the conservative Python interpretation tested previously.
It does not inject a computed target or action into Jev's input. All six native
action criteria remain unchanged, with one Choice question and the same argmax
decoder. Only program name/guidance differs. Longer wording and explicit conditions
change together; this study cannot isolate text length from logical complexity.

## Why a stratified probe matters

The pool contains **66,020 unique observations** from the 16 published Python
training episodes on seeds 80/81/82/83. Selection ignores rewards, successors and
executed actions. Every source manifest/transition file is checked against its
published archive checksum. Reference actions and stratum labels remain outside
model requests.

Only **531/66,020 (0.80%)** of unique states have uncertain incoming motion where
latest-segment and conservative lookahead prescribe different actions. The
hash-uniform 32-state coverage reference from the same pool included zero such
states and covered only five of ten strata. The earlier teacher study's distinct
32-state probe also could not distinguish the two B interpretations, as reported
in the [previous diagnostic study](question-diagnostics-results-2026-09-20.md).

The new selection takes eight lowest observation hashes in each of ten disjoint
strata, for **80 states**. Each program receives two queries per state, with rotated
order. It therefore measures selected behaviors rather than natural gameplay
frequencies. The 160 responses per program are not 160 independent states.
The 32-state coverage reference and 80-state probe differ in size; this is not
an equal-budget test of sampling methods.

## All strata, including regressions

Every cell below compares against the **same conservative reference rule**. V2 was
authored to track current height, so disagreement with a different reference is not
automatically failure to execute v2. Counts are 16 responses on eight states each.

| State stratum | v2 | Ambiguous B | Precise candidate |
| --- | ---: | ---: | ---: |
| missing | 16/16 | 16/16 | 16/16 |
| unknown-motion | 10/16 | 5/16 | 0/16 |
| outgoing | 10/16 | 7/16 | 6/16 |
| stationary-x | 8/16 | 7/16 | 2/16 |
| incoming-uncertain-conflict | 8/16 | 6/16 | 1/16 |
| incoming-uncertain-same | 10/16 | 15/16 | 16/16 |
| incoming-stable-conflict | 4/16 | 5/16 | 11/16 |
| incoming-stable-same-up | 12/16 | 6/16 | 8/16 |
| incoming-stable-same-down | 16/16 | 16/16 | 11/16 |
| incoming-stable-same-hold | 15/16 | 16/16 | 2/16 |

The precise question improves agreement in stable-motion conflict states from
5/16 to 11/16, but worsens the intended uncertain-motion contrast from 6/16 to 1/16.
Unknown-motion agreement falls from 5/16 to 0/16, and stable hold agreement from
16/16 to 2/16. Thus a favorable result in one subcase would have hidden substantial
regressions elsewhere. The primary-stratum change is -31.25 percentage points;
the balanced overall change is -16.25 points. These are descriptive differences,
not statistical significance or population estimates.

There is evidence of behavior change without the intended conditional behavior:
on uncertain-motion conflict states the precise question agrees with unrestricted
latest-segment lookahead **11/16** times and conservative fallback **1/16** times.
This is consistent with a failure to apply the specified reliability condition;
it does not reveal the model's internal computation or prove that one particular
phrase caused the failure.

For reference, v2 matches its own current-height rule on **117/160 (73.13%)**
responses. Ambiguous B matches latest-segment lookahead on **103/160 (64.38%)** and
the conservative interpretation on **99/160 (61.88%)**. The precise candidate's
intended conservative rule matches **73/160 (45.63%)**. These different rule labels
must not be mistaken for a common optimal-action target.

Repeated actions differ on 5/80 state pairs for v2, 5/80 for ambiguous B and 3/80
for the precise question. Lower repeated-action variation did not imply better
rule execution. Probabilities, confidence values and repeat variation are not
calibrated reward or Q estimates.

## Execution, costs and audit

The implementation and protocol were frozen before inference at
`f7899acf9a01952207e62c155e0994a436c7f233`. All **480 scheduled predictions** completed
in **480 HTTP attempts**, below the separate 520-attempt/four-hour cap. There were
no HTTP failures, retries, model substitutions or unexecuted attempts. Teacher
invocations and new emulator frames were zero. Previously reserved final seeds
remain unused; the old study budget was not changed.

The provider reported **826,394 input tokens** and **32,937 output tokens**, with
usage available for every attempt. Summed API elapsed time was **118.01 seconds**.
This is API time, not game simulation time. Monetary billing was not recorded.

The independent offline auditor regenerated the full stratified selection from
the published training sources, verified all 480 original request/response pairs,
checked model/program identities, probabilities, actions, schedule, reservations,
repeat counts and cost/metric totals. It made no model calls. The repository's
127 tests include mocked transient failure/retry recording, audit rejection of a
modified prediction and durable budget/no-reset checks.

[Full evidence and reproduction instructions](../../experiments/pong/motion-probe-v1/README.md)
include selected observations, reference labels outside requests, exact programs,
provenance, all raw HTTP JSON, parsed responses, the durable budget and audit.
No new videos exist for this fixed-input study: the emulator was not advanced.
The source training trajectories and videos remain in their original archive.

## Implication for the teacher optimizer

The evaluation instrument successfully exposed a failure that the small earlier
probe could not distinguish. The wording intervention itself failed. Keep these
outcomes separate: a better diagnostic does not mean a better policy.

Future candidate evaluation should track three things: the behavior a proposed
edit intends to change, behavior that should remain unchanged, and actual game
return. Strata need explicit denominators so missing-ball NOOPs cannot dominate a
score. Before another long rollout, require prospectively defined checks on
unknown-motion fallback and stable up/down/hold behavior, alongside the targeted
condition. No such promotion gate was retroactively applied in this study.

A useful next experiment is an atomic comparison of compact versus expanded
statements of the same rule, followed separately by a change to the reliability
condition. Keep inputs, native actions and decoding fixed. Any future screening
threshold or candidate search budget must be frozen before those responses.
This study supports that narrower next test; it does not establish which wording
will succeed, a learned teacher optimizer, improved gameplay or novelty.
