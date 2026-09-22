# Criteria-edit teacher study: incomplete, 2026-09-23

The study stopped on **HTTP 402** during the fourth of six scheduled rounds.
Three rounds completed; all six evaluated proposals were rejected. Two further
teacher proposals were recorded but lack complete development evaluations.
**No final test was run, and neither research milestone was achieved.**

[Frozen protocol](criteria-teacher-protocol.md) · [Study log](criteria-teacher-log.md) ·
[Reviewed local evidence](../../experiments/pong/criteria-teacher-v1/README.md).

## What ran

The intervention allowed an isolated teacher to edit guidance and all six native
action criterion descriptions. Jev 1.13.0, original observations/history, the
probability-argmax decoder, four-frame action hold and sticky actions 0.25 stayed
fixed. Each episode capped at 2,000 controlled raw frames. A received sampled
training experience; B received no empirical feedback. Both received their current
program and own prior proposals. Development trajectories and outcomes were not
supplied to either teacher, although retained-program identity reveals indirect
selection history.

The source was frozen at `4b61d879b3802a5eb18d2194fe2ddc3124fbba09`.
Three independent two-round searches, a 60,000-attempt ceiling and a separate
31,000-attempt final reserve were planned. Actual execution completed search 1,
completed search 2 round 1, and stopped in search 2 round 2. Search 3 never started.

## Completed development comparisons

Returns are points scored minus points lost, with paired gains over a fresh v2
baseline on the same two development seeds. Both seeds had to avoid regression,
mean gain had to be at least +1, and the historical best gain had to be exceeded.

| Search / round | Seeds | v2 returns | A returns | B returns | A mean gain | B mean gain |
| --- | --- | --- | --- | --- | ---: | ---: |
| 1 / 1 | 106,107 | +2,-2 | -3,-6 | -2,-1 | -4.5 | -1.5 |
| 1 / 2 | 106,107 | 0,+1 | -1,+1 | -4,+1 | -0.5 | -2.0 |
| 2 / 1 | 116,117 | -1,+1 | -6,-5 | -2,+1 | -5.5 | -0.5 |

All six proposals failed the unchanged gate. A1 and B1 remain the identical v2
program, so the predeclared primary A1-versus-v2 comparison could not show positive
gain under the planned identical-hash trajectory sharing. That structural limit
is not an executed final-test result. Other searches cannot replace A1 post hoc.

Four fixed-input probes completed, totaling 1,920 responses. Every program passed
the minimal missing-object hold and up/down availability screen. Passing that
screen did not establish accurate execution of the intended rule or better play.
The separate [literal relative-motion controls](relative-motion-controls-results-2026-09-23.md)
are training-only Python diagnostics and were not fed to these teachers.

## Technical stop and missing evidence

Search 2 round 2 collected v2 training scores 2:1 and 3:2 on seeds 112/113. A then
proposed a 24-frame bounded incoming forecast; B proposed an eight-frame bounded
forecast. Both passed the basic probe. The first development episode, B on seed
116, stopped after **171 decisions / 684 controlled frames**, at **1:1**. Its next
request returned HTTP 402 and the supervisor exited with code 1.

The transport record contains the status code but no error response body. Account
balance or payment cause therefore remains unconfirmed. The interrupted 1:1 score
is censored and excluded from complete evaluation means and selection. The rest
of that round, all of search 3, the final seal and final evaluation are absent.
No retry, episode restart, budget reset or model substitution followed this stop.

## Costs and preservation

| Resource | Recorded use |
| --- | ---: |
| Jev HTTP attempts | 15,093 |
| Successful Jev responses | 15,091 |
| Non-200 attempts | 2: one transport failure, one HTTP 402 |
| Jev input / output tokens | 27,433,995 / 1,034,742 |
| Attempts lacking token usage | 2 |
| Summed Jev request wall time | 4,283.16 seconds |
| Teacher invocations | 8 successful; no repair/access retry |
| Teacher reported input / output tokens | 272,179 / 11,400 |
| Teacher reported reasoning-output tokens | 4,113, retained as a separate provider field |
| Summed teacher subprocess wall time | 381.89 seconds |
| Recorded episodes | 26 complete evaluations, 1 incomplete |
| Controlled frames / decisions | 52,684 / 13,171 |
| Reset frames | 267, separate from controlled frames |
| Original videos | 27 |
| Final-test calls | 0 |

Teacher configuration requested `gpt-6-astra` with high reasoning effort through
the pinned isolated Codex adapter; the CLI does not attest the provider's actual
response-model identity. Teacher usage fields are preserved without treating
reasoning tokens as an additional disjoint billable total. Currency charges and
account balance were not recorded, so no dollar-cost claim is made.

The offline auditor replayed **all 27 trajectories**, including the interrupted
one, checked original model requests/responses, reconstructed teacher packets and
original proposals, recomputed completed selections and reconciled every attempt.
Its receipt explicitly reports that final evaluation was not verified because it
never occurred. Verification made no model calls. All 146 tests pass.

The local LFS archive excludes only the empty runtime lock. It preserves original
records and videos, with checksums, exact teacher pages and audit receipts. Local
archive restoration passed all 506 member checksums, and a second full replay of
all 27 extracted trajectories passed. Teacher-usage list order differs between
filesystem walks; its multiset and every scalar cost agree. No remote push or
retrieval is claimed.

## Next action

The frozen protocol forbids resuming or overwriting this run. Restore service
access before any future live experiment, then freeze a distinct bounded protocol
and explicit data provenance. The [candidate-feedback design note](teacher-study-next.md#candidate-experience-after-rejection-proposed-follow-up-2026-09-23)
identifies a testable limitation of incumbent-only feedback after rejection; it
does not explain these failures causally or authorize changing this study.
The overall research goal remains unmet. This incomplete study must not be
presented as evidence that feedback optimization works or cannot work in general.
