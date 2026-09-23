# Pong closure: OpenRouter candidate-feedback study

**Closed on owner request, 2026-09-24; execution remains incomplete.** HTTP 502
stopped the second of three planned rounds. The zero-retry frozen protocol stopped
immediately. No restart, extra Pong model calls, final seal or final evaluation
was performed during closure. This ends the bounded Pong stage, not the broader
research objective, and does not claim optimization convergence or mastery.

[Frozen protocol](candidate-feedback-openrouter-protocol.md) ·
[Launch record](candidate-feedback-openrouter-log.md) ·
[Reviewed local evidence](../../experiments/pong/candidate-feedback-openrouter-v1/README.md)

## Observed outcome

| Round-one program | Seed 206 score / return | Seed 207 score / return | Paired gain over V2 | Frozen selector |
| --- | --- | --- | --- | --- |
| V2 baseline | 0:0 / 0 | 1:2 / -1 | Reference | Retained for A |
| A: reflected interception | 0:13 / -13 | 0:13 / -13 | -13, -12; mean **-12.5** | Rejected |
| B: incoming four-frame lead | 1:0 / +1 | 1:0 / +1 | +1, +2; mean **+1.5** | Accepted |

Each episode had a 2,000 controlled-frame cap; these are not completed native-match
wins. Both proposals passed the minimal 160-response probe screen. B had no
trajectory feedback. Its acceptance is an observed development selection, not
untouched-test improvement, repeatability or evidence that feedback is harmful.
Only one paired teacher round completed; random response and trajectory variation
remain plausible contributors. No comparisons are pooled with direct-provider runs.

A proposed long-horizon reflected arrival-height tracking with approximate wall
coordinates. B proposed a short incoming-ball lead capped at four raw frames.
B's second proposal extended its lead to twelve frames with fallbacks; it was
recorded but never probed or development-evaluated. Exact wording, evidence IDs,
context, schema and usage remain in the original teacher records below.

## What the interruption leaves unanswered

Second-round training executed V2 on seed 202 (2:1) and seed 203 (3:2).
The rejected A proposal scored 0:13 on seed 202; on seed 203 it reached 0:2 after
500 controlled frames and then encountered HTTP 502. That last episode contains
125 executed decisions, 126 requests and one failed response. It is excluded from
complete-episode performance comparisons.

**The second A teacher was never invoked.** Although its rejected proposal produced
new training trajectories, those data were not delivered in a subsequent teacher
packet. The central candidate-experience feedback hypothesis therefore remains
untested. It would be wrong to claim this experiment showed that learning from
one's own failures succeeded or failed.

## Teacher provenance and exact records

The frozen source was `96ec5944460406af41ba565e95049b16bbaae7e2`.
Jev requested `~typesafe/jev-latest` through OpenRouter Decisions; all successful
responses matched the required `typesafe/jev-1.13-20260917` identity. Teachers used
the pinned Codex 0.154.0 binary in the recorded Bubblewrap packet-only sandbox,
requesting `gpt-6-astra` with high reasoning. Provider model attestation is absent.
No schema repairs, access retries or coordinator-authored candidate substitutions occurred.

| Entry | Teacher-visible evidence | Proposal and outcome |
| --- | --- | --- |
| R1-B | Game contract, V2, no empirical feedback | [Exact packet](../../experiments/pong/candidate-feedback-openrouter-v1/records/search-1/round-1/B/teacher/invocation-1/packet.json), [proposal](../../experiments/pong/candidate-feedback-openrouter-v1/records/search-1/round-1/B/teacher/validated.json): four-frame lead, accepted on development |
| R1-A | V2 training seeds 200/201, role-qualified examples | [Exact packet](../../experiments/pong/candidate-feedback-openrouter-v1/records/search-1/round-1/A/teacher/invocation-1/packet.json), [proposal](../../experiments/pong/candidate-feedback-openrouter-v1/records/search-1/round-1/A/teacher/validated.json): reflected interception, rejected |
| R2-B | Selected B program, its previous proposal, no trajectories/scores | [Exact packet](../../experiments/pong/candidate-feedback-openrouter-v1/records/search-1/round-2/B/teacher/invocation-1/packet.json), [proposal](../../experiments/pong/candidate-feedback-openrouter-v1/records/search-1/round-2/B/teacher/validated.json): twelve-frame lead, unevaluated |

Their sibling invocation directories retain exact instructions, response schema,
context preview, execution metadata, usage events and original final JSON. The
coordinator's retrospective interpretation is not part of their isolated context.

## Resources and verification

- **6,106 Jev attempts:** 6,105 successful, one HTTP 502; zero final requests.
- **12 trajectories:** 11 complete and one incomplete; all replayed, including raw
  frame RAM/RGB hashes, actions, observations and observed rewards.
- **5,625 gameplay decisions / 22,500 controlled frames**, plus 95 reset frames.
- **480 diagnostic requests**, separate from gameplay decisions.
- Jev usage: **11,012,103 input / 418,665 output tokens**; recorded API time
  **2,530.02 seconds**. Total supervisor wall time was **2,717.52 seconds**.
- Three completed teacher invocations: **83,355 input / 4,552 output tokens**;
  separate reported reasoning-output field totals 1,873. Do not double-count it.
- OpenRouter successful-response reported cost: **US$0.462508326**. Failed-request
  billing and teacher USD billing are unavailable; this is not a complete invoice.
- Offline closure/auditing uses **zero model calls**. Original packets, original
  exchanges, the completed selection and all 12 replays passed the new auditor.
  No final-test result was invented or opened during closure.

The original supervisor's top-level `status` string was overwritten by its nested
study status object at exit. Its `exit_code=1` and end timestamp preserve the actual
termination. The separate closure record explains this schema issue; the original
runtime records are unchanged. Reviewed archives and videos use local Git LFS;
no remote publication or retrieval is claimed.

## Bounded lessons and handoff

Across these Pong attempts, additional prediction prose has not established a
reliable improvement. The short-lead proposal is a useful development-positive
reference, while reflected interception again failed. These are associations,
not a controlled causal comparison of horizon, wording or execution quality.
A minimal missing-object/directional probe can pass while gameplay is poor.

Pong leaves us with replayable failures, a teacher-feedback delivery limitation,
and a functioning pinned OpenRouter transport that can still fail transiently.
For Seaquest, validate semantic observations and behavior coverage first, measure
strategy execution separately from score, and freeze a bounded transport-retry
policy before paid collection. Carry the method and lessons forward, not a claim
of learned Pong mastery. [Seaquest entrypoint](../seaquest/README.md).
