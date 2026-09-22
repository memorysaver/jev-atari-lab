# Compact wording regressed despite local fallback improvements

**Observed negative result:** A compact restatement of the same conservative
motion rule matched its reference on **62/160 responses (38.75%)**, versus
**76/160 (47.50%)** for the freshly evaluated expanded question: **-8.75 percentage
points**. It failed the prospective screen and is not promoted. V2 remains the
gameplay reference. No gameplay, teacher API invocation or final-test evaluation
was performed; neither teacher-optimization milestone has been established.

This completes the atomic restatement experiment suggested by the
[previous motion probe](motion-probe-results-2026-09-21.md), under a separate
[frozen protocol](wording-probe-protocol.md). All **480 Jev 1.13.0 predictions**
completed in 480 HTTP attempts, with no failure, retry or model substitution.
[Reviewed local evidence](../../experiments/pong/wording-probe-v1/README.md) retains
every request, response, program, input, schedule, budget and offline audit.
Remote publication/retrieval has not been performed for this study.

## What was held fixed

The expanded arm uses D001's exact question. [D002](teacher-rounds/D002-compact-wording.md)
compresses its guidance from **1,365 to 820 characters**, preserving the intended
incoming-velocity condition, three-sample visibility/timing/sign checks, four-frame
lookahead, current-height fallback, four-pixel deadband and native action meanings.
Only the question-text field differs inside expanded/compact model requests.
Observations, action criteria, model version and probability-argmax decoding match.
Wording, redundancy and length change together; this is not a pure text-length test.

All three programs, including the unchanged v2 control, were queried afresh twice
on the same 80 states, with rotated query order. Historical expanded responses
are not the experimental control. Its prior 73/160 and current 76/160 are distinct
realizations of the same question, not evidence of a code or policy improvement.

The states were reconstructed from the checksummed training trajectories on seeds
80/81/82/83, with exact equality to the previous eight-state-per-stratum selection.
They are deliberately reused and already inspected. The coordinator had seen
development and prior diagnostic results when authoring this manual restatement;
this is exploratory evidence, not an isolated teacher proposal or held-out test.
No reward, successor, previous answer, reference action or stratum label enters
the model request. Interactive-author model version/token cost were not independently
recorded; there were no separate teacher API calls.

## All behaviors, including regressions

Every table cell compares with the **same conservative reference**, on 16 responses
from eight states. V2 intends current-height tracking, so disagreement with this
different rule is not necessarily a v2 execution error.

| Stratum | V2 | Expanded | Compact |
| --- | ---: | ---: | ---: |
| Missing object | 16/16 | 16/16 | 16/16 |
| Unknown motion | 9/16 | 0/16 | 0/16 |
| Outgoing | 10/16 | 6/16 | 6/16 |
| Stationary x | 8/16 | 2/16 | 2/16 |
| Incoming uncertain conflict | 8/16 | 1/16 | 7/16 |
| Incoming uncertain same | 12/16 | 16/16 | 7/16 |
| Incoming stable conflict | 4/16 | 10/16 | 7/16 |
| Incoming stable same up | 11/16 | 10/16 | 3/16 |
| Incoming stable same down | 16/16 | 12/16 | 2/16 |
| Incoming stable same hold | 15/16 | 3/16 | 12/16 |
| **Balanced total** | **109/160** | **76/160** | **62/160** |

The compact question improves uncertain-conflict agreement from 1/16 to 7/16 and
stable-hold agreement from 3/16 to 12/16. Those gains coexist with substantial
regressions: stable up falls from 10/16 to 3/16, stable down from 12/16 to 2/16, and
uncertain-same from 16/16 to 7/16. Unknown-motion agreement remains zero in both
wordings. A favorable subcase does not support retaining this candidate overall.

Repeated actions differ on **3/80** state pairs for v2, **6/80** for expanded and
**11/80** for compact. V2's agreement with its **own** current-height rule is
117/160 (73.13%). Its score against the conservative reference in the table is a
different measurement. None of these rule targets is established to be optimal.

For a post-hoc paired description, compact alone is correct on 18 paired responses,
expanded alone on 32, both on 44, and neither on 66. Averaging the two repetitions
per state, 13 states improve, 19 regress and 48 tie. These are descriptive counts,
not independent trials or statistical significance. Selected strata are equally
weighted here, unlike their natural gameplay frequencies; no population accuracy
or reward gain is estimated.

## Prospective disposition

The frozen screen required a complete schedule, at least 128/160 overall matches,
at least +10 percentage points over expanded, 16/16 missing-object matches and
at least 12/16 in each of the other nine strata. Compact passed completion,
missing-object behavior and stable hold only. It failed both overall conditions
and the remaining eight behavioral strata. The [machine-readable screen](../../experiments/pong/wording-probe-v1/screen.json)
was recomputed by the offline auditor.

These were pragmatic diagnostic thresholds, not calibrated guarantees of gameplay
quality. Even a pass would only qualify the candidate for a separately designed
study. The observed failure stops this candidate here; there is no adaptive wording
revision, longer run, threshold change or budget extension in this experiment.

## Costs, provenance and verification

The protocol, proposal and executable source were committed before model access at
`e5949244abf2fe02c15d82d3dcbc2d0e9860596c`. All scheduled predictions completed within
the separate 520-attempt/four-hour limit. Provider usage was present for every
attempt: **819,674 input tokens** and **32,969 output tokens**. Summed API elapsed
time was **124.25 seconds**. This is request time, not emulated game time; new
emulator frames were zero. Monetary billing was not recorded.

The offline auditor regenerated all selected observations from the published source
checksums, verified every original request/response and parsed action, and
recomputed schedule, model/program identities, metrics, repeat counts, attempt
reservations, costs and screen. It used zero model calls. The shared verifier also
revalidated all 480 responses of the original motion-probe-v1 without modifying
that historical protocol or result.

All **132 tests** passed before live access, including mocked transient transport
failure and audit round trips for both study identities, rejection of modified
inputs/programs/provenance, a request-field equality check on all 80 observations,
and refusal to pass incomplete or behaviorally failing screens. Lint, formatting
and tracked-document checks passed. The evidence archive is locally checksummed
and restored for offline verification; no remote preservation is claimed.

## What to investigate next

**Inference, not an established mechanism:** shortening this conditional question
does not recover its intended behavior. The two fresh wordings both fail unknown
motion and struggle with outgoing/stationary states, where the reference simply
tracks current height. This points toward testing the prerequisites of the action
decision before adding more reliability or interception logic. It does not identify
Jev's internal computation or prove that all compact wording will fail.

The next proposed experiment should separate three observable skills: identifying
the ball/player centers, classifying their gap against the deadband, and mapping
the resulting vertical direction to native actions. Use an unchanged v2 anchor
and a tightly limited teacher edit, with labels outside model inputs and a fresh
prospective budget. If intermediate structured questions are introduced, declare
the changed question topology and cost explicitly; that is a different intervention
from this fixed one-question restatement. Do not inject a Python-computed action
and describe it as learned Jev control.

This is a proposed design direction, not an executed third probe or automatic
authorization to keep searching. A successful diagnostic still needs a frozen
gameplay comparison and the independent feedback/no-feedback teacher searches
described in the [research endpoint](research-endpoint.md). The present advance
is a completed falsification of one specific wording hypothesis and a more precise
location for the next investigation, not policy improvement.
