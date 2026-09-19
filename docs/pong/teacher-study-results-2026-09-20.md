# Teacher study v1: one completed round, technical stop in round two

**Observed:** Neither first-round candidate passed the frozen development gate.
The experience-informed teacher proposed a long-horizon interception target and
lost 0:21 on both development seeds. The no-trajectory-feedback control proposed
a four-frame lookahead, improving one seed and regressing on the other.
Both arms retained `pong-vertical-control-v2`.

**Study status: incomplete.** Round two collected its two training episodes, but
the A teacher process exited with `turn.failed` and no proposal. Round three and
all final evaluations were not run. This does not establish that either optimizer
learns, that feedback is harmful, or that the control is superior.

## Design and provenance

The [approved plan](teacher-study-plan.md) and [frozen protocol](teacher-study-protocol.md)
requested three rounds comparing an experience-informed teacher (A) with a teacher
receiving no empirical trajectories or outcomes (B). Jev `jev-1.13.0`, object inputs,
six native actions, probability argmax and four-frame decisions remained fixed.
Only question name/guidance could change. The requested teacher was `gpt-6-astra`,
reasoning `high`, in a fresh filesystem-isolated Codex invocation. Provider-level
model attestation is unavailable; requested settings are not independent verification.

The original runner was frozen at `94ceb931b883b89e970786eee29f49ecb819faac`.
An [explicit parser continuation](teacher-study-continuation.md) at
`16722dfa725472b1200b1e7de2d54ed11eaf9731` recovered the first teacher's one existing
completed response, without resampling it or resetting the budget. Original failure
records, original source identities and the continuation receipt remain preserved.
Publication/reporting changes happened after execution and did not alter the run.

## First-round results

Each parent/candidate received an independent Jev realization on the same seed,
with at most 20,000 controlled raw frames or native termination. Scores are player:opponent.
An unfinished capped episode is not a draw or a win.

| Arm | Seed | Parent score / return | Candidate score / return | Paired gain |
| --- | ---: | --- | --- | ---: |
| A: trajectory feedback | 66 | 11:20 / -9, capped | 0:21 / -21, native loss | -12 |
| A: trajectory feedback | 67 | 11:21 / -10, native loss | 0:21 / -21, native loss | -11 |
| B: no trajectory feedback | 66 | 11:19 / -8, capped | 7:18 / -11, capped | -3 |
| B: no trajectory feedback | 67 | 10:21 / -11, native loss | 12:12 / 0, capped | +11 |

A's mean paired gain was **-11.5**. B's was **+4.0**, but the gate required no
regression on either seed and mean gain at least +1. Both were rejected under
that predeclared rule. B's positive average does not override its seed-66 regression.
The gate is an engineering selection rule, not a statistical significance test.

| First-round group | Native completions / evaluated episodes | Wins / native completions | Mean capped return |
| --- | ---: | --- | ---: |
| A parent | 1/2 | 0/1 | -9.5 |
| A candidate | 2/2 | 0/2 | -21.0 |
| B parent | 1/2 | 0/1 | -9.5 |
| B candidate | 0/2 | unavailable (0 completed) | -5.5 |

There were zero observed wins in all four groups. Unknown outcomes of capped
episodes remain unknown. Completion and completed-match win rates can themselves
be biased by policies' different episode durations.

## What the teacher changed

- [T001-A](teacher-rounds/T001-A.md): replace the current ball-height target with
  an incoming-ball intercept estimate, including travel time and wall reflections.
  Exact visible training examples, rationale, before/after guidance and output are linked.
- [T001-B](teacher-rounds/T001-B.md): estimate the ball's vertical displacement over
  the next four raw frames, with a fallback to current height when motion is unreliable.
- [T002-A](teacher-rounds/T002-A.md): training packet prepared and invocation failed;
  there is no second-round proposal, edit or measured candidate outcome.

The fixed-input probe used 32 training states, two parent and two candidate queries
per state. Parent/candidate action flips were 50.0% for A and 21.875% for B; repeat
flips within a single program ranged from 6.25% to 12.5%. This demonstrates behavior
changes and repeat variation, not policy improvement. It also cautions against
attributing an independent parent/candidate trajectory difference entirely to the edit.

**Inference for follow-up:** Interception guidance may demand arithmetic or motion
interpretation that Jev does not execute reliably, but these results do not identify
that mechanism. The same strategy may also be poor in this environment. Separate
literal-rule execution, question adherence and game return before drawing a causal
conclusion. See the [next research design](teacher-study-next.md).

## Failure and timing

The first Jev request was at `2026-09-18T16:29:41.682233Z` (September 19 in Taipei).
The technical stop was at `2026-09-18T19:49:00.046751Z`, about 3 hours 19 minutes
later. The original 24-hour deadline was `2026-09-19T16:29:41.682233Z`.
The stopped process was discovered when supervision resumed near that deadline;
it had not been making calls throughout the intervening time. No budget or clock
was reset, and no new live continuation was launched.

Round-two training scores were 5:11 and 11:6 at 10,000 frames. Those are additional
fixed-v2 training observations, not second-round improvement. The next teacher
process returned exit code 1 after about 1.86 seconds. Its public event record has
diagnostic/error markers and `turn.failed`, without a completed turn or final answer.
The original recorder discarded error bodies and raised before retaining private
stderr; the underlying provider/transport reason is **unavailable**. Authentication,
quota, model access and context failure are not established explanations.

A later code fix retains failed subprocess stdout/stderr privately with owner-only
permissions, before raising, while publishing only a retention flag. Mocked tests
cover this path. It cannot reconstruct the lost historical diagnostic. No repair
or quality-based teacher resampling was performed.

## Cost, coverage and preservation

- Jev: **41,080 HTTP attempts**, including **9 non-200 attempts**, against 220,000 allowed.
  All attempts were nonfinal; the reserved 66,000 final attempts were unused.
- Recorded Jev usage: **69,527,175 input tokens**, **2,820,288 output tokens**;
  nine attempts have no reported usage. API elapsed time totals 11,088.79 seconds.
- Teacher: **3 invocation reservations**, two completed proposals (one recovered
  offline) and one failed invocation; zero repairs. Completed turns report 69,358
  input and 1,452 output tokens combined. Failed-turn usage and monetary billing
  are unavailable, not zero.
- Completed coverage: **12 of 42 scheduled episodes**, **163,258 controlled raw frames**,
  **40,815 controller decisions**, **12 original videos**, and two 128-query probe blocks.
  One decision generally spans four frames; each intermediate frame has a trace,
  not a fictitious Jev request. The final shorter action can span fewer frames.
- Independent offline audit verified all 12 recorded episodes, original requests and
  responses, actions, frames, rewards, program lineage, teacher packets, probes,
  gates, continuation preservation and global accounting. Audit makes no model calls.

[Machine-readable results, CSV, audit and LFS archive](../../experiments/pong/teacher-study-v1/README.md)
preserve all completed work and the failed teacher operation. Final results are
explicitly missing, not zero-scored test games. Development seeds must not be
relabelled as held-out tests in a later study.

## What remains unresolved

This is one incomplete optimizer trajectory per arm and only two development seeds.
A and B differ in context volume and token cost as well as feedback. The current
selected program indirectly exposes selection history even though development
scores and acceptance labels are withheld. Short scoring windows do not identify
counterfactual action credit. There is no held-out improvement estimate, no
replicated optimizer comparison, no TD update, and no evidence of Atari mastery.

The implemented result is an auditable teacher-proposal, probe, evaluate and
retain/reject workflow. Whether an experience-driven question optimizer reliably
improves Jev remains the central open research question.
