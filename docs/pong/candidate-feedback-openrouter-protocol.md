# Candidate feedback on OpenRouter: three-round Pong closure

Prospective protocol, 2026-09-23. The owner authorized restarting experiments,
then requested about three more rounds before closing Pong and moving to another
Atari game. Interpret this as **one A/B search with three consecutive rounds**,
followed by final evaluation and reporting, regardless of improvement. This is a
new study, not a continuation/reset of the HTTP-402-stopped criteria study.
The original research goals remain unachieved unless their evidence requirements
are met; ending this bounded Pong stage does not claim statistical convergence.

## Question and scope

Does training experience that includes the teacher's own previous proposal help
produce a better question policy than proposal search without trajectory feedback?
Previous rejected proposals did not generate the next teacher packet's experience:
the incumbent remained v2. The new feedback mechanism is motivated by that observed
limitation, but the old results do not establish that it caused failure.

A receives fresh incumbent and previous-candidate training trajectories; B receives
no trajectories or scores. Both have three proposal opportunities, the same initial
question, representation, selector, and their own proposal-only memory. The selected
current question indirectly reveals selection history to both. Costs/context lengths
are reported separately; equal proposal counts are not equal compute. This study
has no incumbent-only feedback arm, so it cannot isolate feedback-source effects.
Provider and seed changes also preclude attributing old/new score differences to
this mechanism. No coordinator-authored candidate or diagnostic strategy is inserted.

## Fixed executor and environment

- Backend: OpenRouter Decisions, `https://openrouter.ai/api/alpha/decisions`.
- Request alias: `~typesafe/jev-latest`; required response identity:
  `typesafe/jev-1.13-20260917`. Abort before action execution on model drift.
  Equivalence to direct-provider `jev-1.13.0` is not assumed.
- One native-action Choice, original Pong RAM objects and finite-difference history,
  all six actions, probability argmax, default `Protocol()`: four raw frames per
  decision and sticky probability 0.25. No computed action injection, fallback,
  action mask, new sensor, question topology, weight or reward change.
- Initial v2 program: `examples/vertical-policy-program.json`, hash
  `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.
- Teacher may edit guidance (maximum 2,000 characters), all six action criteria
  (1..500 characters each), and name (1..100). Preserve `action-choice-program-v2`
  validation and all native action meanings.
- Every episode ends at **2,000 controlled raw frames**, or earlier native termination.
  Primary reward is points scored minus conceded at this cap. No mastery claim.

## Fresh seeds and immutable ordering

| Round | Training | Development |
| --- | --- | --- |
| 1 | 200, 201 | 206, 207 |
| 2 | 202, 203 | 206, 207 |
| 3 | 204, 205 | 206, 207 |

Final seeds: **248,249,258,259,268,269,278,279**. Before access, inspect local episode
manifests in `artifacts/` and `experiments/` for prior use of any proposed seed.
This is local exposure checking, not a remote inventory guarantee. Older reserved
final seeds stay untouched. Split suffixes retain their original meaning.

Each round:

1. Invoke B using its selected current program and proposal-only memory. The first
   real B proposal is the counted teacher access check; no disposable live preflight.
2. Collect A training experience. In round one, execute its incumbent on both seeds.
   In rounds two and three, on each new seed execute the incumbent first and its
   immediately previous proposal second, **regardless of selection or probe failure**.
   Always execute both roles even if their hashes match; no post-hoc deduplication.
   Each is a fresh rollout with separately recorded API draws. Replay and audit each
   episode before including it in teacher evidence. The first training decision is
   also the counted Jev access check; the successful earlier pilot is provenance.
3. Sample at most **48 examples**. For two episodes: 16 evenly spaced decisions per
   episode, plus the first four scoring decisions and each immediate predecessor.
   For four episodes: eight evenly spaced decisions per episode, plus the first two
   scoring decisions and each immediate predecessor. Deduplicate indices within
   episodes. Label each example and summary with role, seed and generating program
   hash; attach generating programs to summaries. Role-qualified example IDs prevent
   collisions on shared seeds. Include actual action/reward/next objects. Trajectories
   are not same-state counterfactuals. Complete episodes require at least 16 decisions.
4. Invoke A using this packet and proposal-only memory. Never supply development
   scores, explicit selection labels, diagnostic labels/results, final data, or
   coordinator findings. The existing 200 KB serialized-packet limit remains a
   pre-call hard stop; do not adaptively trim or add a teacher call.
5. Probe V2/A/B on the same 80 published training motion states, twice each, rotating
   order by state index plus repeat: 480 fresh calls. Minimal screen: all 160 answers
   complete, all 16 missing-object cases choose NOOP/FIRE, and visible cases include
   upward and downward actions. These reused diagnostics are not final validation;
   agreement with a reference rule is not gameplay reward or own-rule adherence.
6. Evaluate fresh V2 and eligible A/B candidates on both development seeds; rotate
   `[V2,A,B]` by `(round_index + seed_index) mod 3`. Skip only ineligible candidate
   development episodes. Select an arm's candidate iff it is nonregressing on both
   seeds, mean gain over fresh V2 is at least +1, and this exceeds its previous best
   development gain (initially zero). Ties retain the incumbent. Earlier best gains
   are historical, not fresh candidate-versus-incumbent comparisons. Three uses of
   the same development pair are selection exposure, not independent confirmation.
7. Preserve all proposals, skipped evaluations, rejections, costs and role provenance.
   Continue to round three even with no improvement, unless a technical/budget stop
   requires preserving an incomplete run. No schedule extension to obtain success.

## Teacher and finite budget

Use the existing packet-only Bubblewrap-isolated Codex teacher, pinned local
0.154.0 binary; request `gpt-6-astra`, reasoning `high`. Record binary hash, isolation
checks, context preview, instructions, schema, exact packets/proposals, usage and
execution results before evaluation. Provider model attestation is unavailable.
Host repository, prior conversations, tools, apps, web and memory are unavailable.
Credentials stay in private runtime storage.

Six normal teacher calls plus at most two global schema repairs and two global
failed-access retries: **10 invocations**, each with a 900-second timeout. Each
proposal has at most one repair and one failed-access retry, maximum three attempts.
Retain the original criteria-study retry qualifications: failed access requires
nonzero exit plus `turn.failed`, without a candidate, completed turn or tool activity.
Repeat the identical packet; schema repairs retain the hypothesis. Timeouts/local
preparation failures/returned candidates are not quality-resampling opportunities.

| Work | Maximum scheduled Jev calls |
| --- | ---: |
| Training: 2 + 4 + 4 episodes, 500 decisions each | 5,000 |
| Development: 3 rounds x 3 policies x 2 seeds x 500 | 9,000 |
| Diagnostic probes: 3 x 480 | 1,440 |
| Final: at most 3 distinct programs x 8 seeds x 500 | 12,000 |
| Total | **27,440** |

Hard budget: **30,000 attempts**, with **17,000 nonfinal** and **13,000 final**.
Reserve durably before every request; final capacity cannot fund search. OpenRouter
has **zero automatic HTTP or transport retries**. Per episode: maximum 500 attempts;
per probe: 480. Any failed request/integrity mismatch stops this root incomplete.
Never reset budgets, overwrite roots, or silently resume failed episodes.
Deadline: 24 hours from the first teacher/Jev invocation. Report controlled frames,
reset frames, decision counts, wall time, tokens and OpenRouter-reported USD costs
separately. The call cap is not a dollar cap; teacher dollar billing is unavailable.

Before the first live call, commit source/protocol, verify a clean worktree, write
`plan.json` with seeds/limits/source/model/probe hash/teacher provenance, and create
the budget/status. Failure to write preparation metadata prevents all live access.
The new entrypoint owns preparation and access in one Python process, avoiding the
previous pilot's shell sequencing deviation. Runtime: `artifacts/pong/candidate-feedback-openrouter-v1/`.

## Final seal and stage closure

After round three, seal V2, selected A1 and selected B1 with exact program hashes,
source, environment, model pin, horizon and final seeds. Close teacher and nonfinal
access before final evaluation. For each seed, execute each distinct program hash
once; rotate hash order by seed index. Identical retained programs share one fresh
trajectory, explicitly not independent samples. Replay/audit every final episode.

Primary comparison: selected **A1 minus V2**, eight paired seed returns, mean gain
at least +1 and lower 95% percentile-bootstrap bound above zero. Use 20,000 paired
seed resamples, RNG 20260923. Also report B1-V2 and A1-B1, all paired returns and
intervals, using the same draws. No choice of best round based on final outcomes.
The primary rule is a small-sample bounded-horizon improvement screen, not mastery.

**One A/B search cannot establish repeatable optimizer advantage.** Seed intervals
are conditional on these selected programs and do not measure teacher-run variance.
Three sequential edits are not three independent optimizer replications. Milestone
two remains unestablished even if A1 beats B1. Preserve earlier unsuccessful studies
and this planned stage closure when interpreting the broader search history.
Final data never enters another proposal under an untouched-test claim.

Finish Pong reporting after this stage regardless of pass/fail. A technical stop
also gets a report and preserves incomplete evidence; any recovery needs a distinct,
prospective decision. The separate next-game recommendation allocates no live calls.
