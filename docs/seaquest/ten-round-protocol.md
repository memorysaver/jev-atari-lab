# Seaquest ten-round autonomous research protocol

Prospective, 2026-09-24. The owner explicitly requested ten autonomous research
rounds, complete records and recordings, then a stop. This new allocation does
not reopen Pong or the closed fixed-question pilot. Freeze this protocol and its
implementation before any new model call.

## Question and authorship

Can training-feedback-guided question editing improve Seaquest control over the
coordinator-authored DOWN/NOOP-collapsed baseline? The interactive coordinator
writes proposals using prior training records. This is **not an isolated teacher
experiment or an A/B estimate of feedback benefit**. No subagents or external
teacher calls are used. Every proposal records its hypothesis, exact program,
training evidence references, provenance and regression risks before execution.
Do not claim repeated optimizer success from seven sequential edits.

## Ten rounds and data separation

1. Round 1: unchanged original baseline on training seeds **320,321**.
2. Rounds 2 through 8: one new coordinator-authored question per round on the same
   two training seeds. Both complete games/caps are retained even if the first is poor.
   Edits may change guidance and native-action criteria only. All 18 actions remain
   available. Guidance <=2,000 characters; each criterion <=500. No action mask,
   code policy, observation rewrite, new reward or silent fallback.
3. Before round 9, select the revision with greatest mean controlled native return
   among rounds 2..8; earliest round breaks ties. Seal it before development access.
   Round 9 compares unchanged baseline and sealed candidate on **326,327**.
4. Round 10 compares the same two fixed programs on untouched final seeds **328,329**.
   Run this diagnostic even if the development gate fails, labeling rejection.
   No edit or new selection follows development/final data. Stop and close all
   unused capacity after round 10. No eleventh round or extra final seeds.

The development and final gates each require mean paired controlled-return gain
>=20 with neither seed regressing. Both must pass to report this bounded study's
held-out improvement. This is an engineering gate on two seeds, not a significance
test, mastery criterion or proof of repeatable teacher benefit. Training selection
can overfit. Failed candidates, zero gains and incomplete work stay in the record.

## Environment, starts and observations

ALE Seaquest mode 0, difficulty 0, sticky 0.25, frameskip one, four-frame action
hold, all 18 native actions. Use unchanged `seaquest-objects-v2` and its three-snapshot
history; its previous bounded pixel-support gate passed. Shapes, persistent object
identities, full rescue semantics and causes of death remain provisional.

Each episode begins with **32 NOOP holds (128 frames), then 32 uniformly random
native-action holds (128 frames), using Python random.Random(seed)**. This seed-based
prefix is fixed independently of program and does not consult rewards. Record and
film every prefix frame. No resampling for favorable starts or success. If a prefix
ends natively, stop that study as incomplete rather than selecting a replacement.
Do not inspect development/final prefix outcomes before their scheduled round.

After the prefix, allow at most **800 Jev decisions / 3,200 controlled frames** or
native termination. No automatic FIRE, reset or life-loss controller. Prefix frames,
rewards and life losses are separated from controlled frames/rewards in all summaries;
also report total episode return. The primary endpoint is controlled native reward.
Measure actual start-state differences; different seeds alone do not prove diversity.
This new start contract is not directly comparable to the original no-prefix pilot.

## Transport and limits

OpenRouter Decisions, requested `~typesafe/jev-latest`, response pinned to
`typesafe/jev-1.13-20260917`. One Choice request per decision; use the existing
probability-argmax/provider-tie decoder. Stop before action on model drift or invalid
response. Every original request/response, usage, timing and decoded action is retained.

Maximum **24,000 HTTP attempts** total: <=2,000 in each of rounds 1..8 and <=4,000
in each of rounds 9..10. At most 19,200 successful executed model decisions across
24 episodes. Reserve/fsync before every attempt, including retries; no reset when
moving to a new round. The first attempted call starts a 24-hour deadline.
Unused per-round capacity cannot be shifted to extra experiments. At the pilot's
observed price, expected successful-response costs are a few US dollars; this is
an estimate, not a monetary hard cap or a billing guarantee.

At most two same-observation retries for transport or HTTP 429/500/502/503/504/529.
Payment/authentication errors, invalid JSON/choices and model drift stop incomplete.
If retries are exhausted, preserve the technical failure and do not silently rerun
or substitute a local controller. Technical failure is not a completed research round.

## Records, verification and stopping

- Commit source/protocol and require a clean tree before initialization/execution.
- Write root plan, ROM/version/model metadata and durable budget before calls.
- Save each immutable round plan and proposal before its first evaluation call.
- Save raw-frame RAM/RGB hashes, observations/history, pixel checks, native rewards,
  lives/end flags, original exchanges and a full **60 fps MP4 for every episode**.
- Write incremental results and always close video/ledger/summary on failure.
- Audit requests, original action decoding, all raw frames and video frame counts.
- Preserve reviewed local LFS archives with checksums; restore and re-audit. No ROM,
  emulator snapshot or credential may enter tracked evidence. No remote claim without
  verified remote retrieval.
- Report all ten rounds, retained/rejected candidates, final gate, costs and limitations;
  close the budget after round 10 regardless of result.

The thread's historical goal record still describes a blocked Pong objective;
it is not a completion criterion for this separate owner-authorized Seaquest study.
