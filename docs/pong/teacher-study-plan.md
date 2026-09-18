# Proposed first longitudinal teacher study

Status: **owner approved**, 2026-09-19. The owner replied "approved, go" after
reviewing this proposal. Goal mode now tracks implementation, bounded execution
and publication. The [frozen execution protocol](teacher-study-protocol.md)
specifies the harness details. Changes to approved limits require a new decision.

## Question and goal completion

Can GPT-6 Astra with high reasoning improve a fixed Jev direct policy through
experience-informed guidance revisions? Does it outperform revision without
trajectory feedback under the same proposal and evaluation opportunities?

The goal is to complete a bounded three-round experiment, final evaluation, audits
and publication, including negative or inconclusive findings. Completion does not
require winning Pong. This is one exploratory optimizer run per arm, not a replicated
optimizer benchmark or evidence that this is a new learning principle.

## Fixed contracts

- Executor: `jev-1.13.0`; starting question: `pong-vertical-control-v2`, hash
  `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.
- RAM objects/history, all six native actions, probability argmax, four-frame hold,
  sticky probability 0.25, mode/difficulty 0, reset NOOPs 0..30.
- One action Choice question; only name/guidance may change, within existing limits.
  No new sensors, action mask, reward shaping, heuristic action override or weights.
- Teacher: explicitly request `gpt-6-astra` and `high`. Local Codex configuration
  currently names these settings; that is not proof of a completed invocation.
  Record requested settings and runtime metadata, including any unavailable fields.
  If the requested teacher cannot be run, stop instead of substituting another model.

The [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
documents explicit model/reasoning configuration. Run access and returned identity
must still be checked locally after approval.

## Arms and visibility

| Arm | Teacher input | Selection |
| --- | --- | --- |
| A: experience | Current question, fixed game contract, sampled training traces/results and training-grounded modification memory | Frozen development gate |
| B: no trajectory feedback | Same initial prior knowledge, current question and prior proposed edits; no empirical scores, traces or outcome memory | Same development gate |
| V2 reference | Unchanged starting question | Never optimized |

Use fresh teacher agents/sessions with no inherited conversation. The coordinator
has seen old development results and is not the experimental proposal generator.
Teacher contexts receive only the prepared packet, not repository-wide access,
development trajectories or final-test results. Verify the isolation mechanism
before live work; a new session alone does not restrict filesystem/tool access.

Each optimizing arm gets one candidate per round. Both teachers know the current
selected question, which indirectly reveals selection history; B is a no-trajectory
feedback control, not a claim of zero selection information. The A arm's extra
training-data cost is charged explicitly. Proposal/evaluation opportunities match;
actual total costs need not match. Report quality against those actual costs.

## Three rounds

Proposed unused training seeds: 60/61, then 62/63, then 64/65. Proposed development
seeds: 66/67. Reserve 68/69/78/79 for final evaluation. Check the evidence inventory
before freezing the protocol; a previously exposed seed must not be labeled fresh.

For each round:

1. Run A's incumbent on two training seeds, at most 10,000 controlled frames each.
   Select a bounded packet containing representative states and scoring/failure
   windows by a deterministic, recorded sampling rule. Do not provide future labels
   as if they were policy observations.
2. Each isolated teacher proposes one guidance change, a concise rationale,
   expected action changes and possible regressions. Record exact inputs, outputs,
   parent/candidate hashes and diffs before evaluation. Invalid proposals are logged.
3. On 32 training inputs per arm, query parent and candidate twice each, interleaved.
   Measure action flips/distribution changes and repeat-query noise. These probes
   are diagnostic, not an alternative reward or a filter chosen after seeing results.
4. Evaluate both parent and candidate afresh on both development seeds, capped at
   20,000 frames each or native termination. Interleave program order. Do not rely
   on a historical parent's score as a fresh paired measurement.
5. Retain the candidate only if both seed returns are no worse and the mean paired
   gain is at least +1 point. Otherwise retain the parent. Missing/failed evaluations
   are inconclusive, never a promotion. This is a conservative engineering gate,
   not a statistical significance test. No early stop merely for absent improvement.
6. Append the teacher log, gate result, all costs and limitations. Teacher-visible
   memory derives from training evidence; detailed development results stay with
   the coordinator. Complete all three rounds unless a resource/integrity stop applies.

## Final evaluation

Freeze A's selected question and B's selected question before opening the four
final seeds. Evaluate both and unchanged V2 with a 20,000-frame cap on each seed.
If programs are identical, shared evaluations must be labeled as shared, not
independent repetitions. Local tracking/random controls can run without model calls.

Primary endpoint: paired capped episode return. Also report points, native-match
completion, wins with explicit denominators, failures, costs and per-seed variation.
A capped score is not a native-match win. Do not choose a checkpoint from final
scores or use them in a subsequent proposal. More replication is needed for
population-level claims. A versus V2 tests improvement; A versus B tests the
additional value of this experience-feedback process.

## Resource limits proposed for approval

| Work | Maximum scheduled Jev decisions/queries before retries |
| --- | ---: |
| Training: 3 rounds x 2 episodes x 2,500 decisions | 15,000 |
| Development: 3 rounds x 2 arms x 2 programs x 2 seeds x 5,000 | 120,000 |
| Final: 3 programs x 4 seeds x 5,000 | 60,000 |
| Probes: 3 rounds x 2 arms x 32 states x 2 programs x 2 repeats | 768 |
| Total | 195,768 |

Hard Jev limit: **220,000 HTTP attempts**, including up to 100 preflight calls,
retries, invalid responses and all incomplete work. Unused reserve does not fund
extra candidates or exploratory reruns. Reserve 66,000 attempts for final evaluation;
training/development/probes/preflight cannot consume that allocation.

Teacher limit: **8 isolated invocations** (six proposals plus up to two technical
repairs); no quality-based resampling. Record model use and distinguish a hosted
session from individual internal provider requests if only session counts are visible.
Bound each invocation to 15 minutes and its packet/output size in the executable
protocol. Repairs may fix syntax/schema only and must remain in the record.

Stop new live work after **24 hours from the first preflight model invocation** or
at an earlier exhausted cap. Save status and finish offline audits/reporting even
if the scheduled experiment is incomplete. Only transient request failures may be
retried under a frozen bounded policy; no unrecorded episode restarts. Pin/model,
split, request integrity or replay mismatches stop dependent experimental work.

The previous 5,000-call trial took 1,326.8 seconds of HTTP time. Linear extrapolation
gives about 14.4 hours for the scheduled calls, or 16.2 hours at the attempt cap,
before teacher/engineering/audit overhead; changed prompts and service behavior may
change this substantially. At the old payload size, 220,000 successful calls would
correspond to roughly 371 million input and 15.1 million output tokens. This is
an order-of-magnitude estimate, not a token ceiling or a verified monetary quote.
Actual billing rates/charges have not been established; an attempt cap is not a
currency-denominated budget. Teacher resources are additional and logged separately.

## Implementation and publication after approval

First implement the state-probe runner, packet/context isolation, round orchestration,
global budgets/checkpoints and a frozen-policy-only final-evaluation path. The
existing `match-suite` rejects final-test seeds; keep that default and add an
explicit sealed evaluation entry point instead of weakening training guards.
Validate with local/mock tests before spending the live budget. Freeze the source,
sampling/gate/retry rules and ordered plan before experiment execution.

Publish every round under `docs/pong/teacher-rounds/` and link from the teacher log.
Keep working evidence in `artifacts/pong/teacher-study-v1/`; publish reviewed logs,
raw frames, Jev exchanges, teacher packets/proposals, failed work and manifests in
`experiments/pong/teacher-study-v1/`. Preserve videos/archives with Git LFS and verify
remote retrieval/replay. Plot selected-question return against cumulative cost,
with rejected proposals and incomplete results visible.

Owner approval is required because the owner explicitly requested review before
starting goal mode and live experimentation. Approval of this plan includes the
isolated teacher invocations, bounded model use, implementation, audits and public
repository publication described above; it does not authorize increasing limits.
