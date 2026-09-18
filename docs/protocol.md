# Implemented experiment protocol

## Target and interpretation

For a candidate requested action held for four raw frames, predict the first scoring
event within H raw frames, then continue with `track-ball-center-v1`. The three labels
are -1 (loss), 0 (no event through the complete window) and +1 (gain). H defaults to 240.
The continuation policy tracks ball center y with a two-pixel deadband and is frozen.

This is finite-horizon action-value prediction under a specified continuation.
At deployment, a greedy Jev actor recomputes values every step. That actor differs
from the heuristic continuation used for labels; its return MUST be measured online.
Offline prediction quality does not establish improved online return or Q* accuracy.

An actual point stops branch execution immediately, even inside a held action.
Other termination or truncation before the complete horizon is censored, not label 0.
The playing harness separately records native termination and an external decision
cutoff; it never substitutes a fresh reset observation as the final state.

## Data collection

The default root behavior alternates heuristic and seeded uniform random decisions.
`collect --behavior heuristic|random` can instead follow a single fixed policy; the
manifest records that choice. This changes root sampling, not the branch continuation.
Coverage reports retain all sampled roots and report missing classes and action differences;
no outcome-conditioned root filtering or relabeling is applied. After a
warmup, roots are sampled at a fixed decision stride. Duplicate observation/RAM
fingerprints within a dataset are skipped. Every action starts from the same snapshot
including the same RNG state; this is a paired single sample, not an exact expectation
over sticky-action randomness. Independent episodes are needed for uncertainty estimates.

Seed last digits 0–5/6–7/8–9 partition train/development/test. All branches of a root stay
together. Learning rejects overlapping seed, root ID or observation fingerprint across
train and development, mismatched protocols, horizons, or continuation policies.
Final-test data can be evaluated but cannot enter teacher packets or selection.

Small deterministic games can yield repeated physical states across seeds. Fingerprint
rejection is conservative; a new seed alone does not guarantee a distinct observation.
The split mechanism reduces accidental leakage, not semantic train/test similarity.

## Learning and acceptance

`learn` performs ONE explicit round:

1. Evaluate the current question program on train data, or reuse a matching complete
   `--train-evaluation` report. Reuse validates dataset/program/model/backend and every
   root identity. Original evaluation attempts still count toward the pilot cost.
2. Export up to nine unique train examples: start with four worst and two best errors,
   include any missing outcome class and an action-contrast example if available, then
   fill remaining slots in error order. All examples are from training only.
3. Read a manually provided proposal or call an explicitly configured OpenRouter teacher.
4. Validate one to three programs. They may only change name, guidance and three
   evidence hints. Outcome anchors and aggregation remain fixed in code.
5. Compare baseline and all candidates on development data using the same Jev model.
6. Accept the eligible candidate with lowest Brier score, or retain the current program.

Default acceptance requires a Brier reduction of 0.01 and no regression in MAE or
sampled regret. These are root-averaged diagnostic metrics, not confidence intervals.
There is no automatic claim of significance, deployment, or final-test success.
Mock evaluations are labeled synthetic; automatic paid teacher calls on mock feedback
are prohibited. Question constraints validate structure and preserve anchors; they
cannot prove that a teacher's prose is semantically honest or free from overfitting.

The outcome hint strings may add evidence guidance but cannot change the code-level
reward mapping. Hints, instructions and arrays are hashed as a question program. Changes
to the sensor/serializer are outside this loop and require a new controlled comparison.
Programs have character bounds (4000 for guidance, 1000 per hint), not exact token limits.

## Time, budgets and provenance

The protocol manifest records source mode, hold duration, sticky probability, no-op
reset settings, ALE/Gymnasium/NumPy versions and ROM SHA-256. Dependency resolution is
committed in `uv.lock`. Program and dataset hashes prevent silently mixing revisions.
Keep the implementation Git commit alongside published results; this prototype does
not pretend that model aliases such as `jev-latest` are immutable.

Every branch frame counts, along with root collection and reset frames. The declared
root/warmup/stride/horizon limits bound collection; failure to collect the requested
roots yields an incomplete dataset rejected by evaluation.

Each HTTP attempt, including rate-limit retries, reserves one call from the command's
explicit budget. A state request asks all six questions at once. Retries can consume a
budget before the requested number of decisions; such a run is incomplete, never a
successful shortened experiment. Failed responses are not silently replaced by a local
policy. Report actual provider usage and wall time; price estimates are not fabricated.
Budgets reset between CLI invocations, so an experiment operator must sum all invocations.

API keys come from environment variables. The shared local credential file is
`~/.config/typesafe/credentials.env`, loaded explicitly with `uv run --env-file`. Error bodies and authorization headers are
not written to artifacts. `.env` is ignored and only loaded explicitly via uv if desired.

## Current limits / next experiments

- Jev 1.13.0 authentication and six-action predictions were verified on 2026-09-18.
  An external teacher API has not been tested; imported proposals can come from the
  interactive assistant using train-only feedback.
- This object/critic protocol is Pong-specific. A separate experimental raw-RAM runner
  now covers registered games; semantic adapters, neural baselines and robust
  multiple-training-run uncertainty estimates remain future experiments.
- No TD target, target evaluator, Bellman update or variable-duration semi-MDP learning
  is implemented yet. Add these only after proving the outcome-prediction loop useful.
- Replay snapshots are in-process; disk serialization and crash-resume are not implemented.
- No aggregate experiment scheduler or automatic multi-round online rollout is hidden in
  `learn`; feed its selected program into the next explicit round, and evaluate online.
- A small corpus with no gains is useful for plumbing but cannot validate learning to win.
  Expand trajectory coverage before quality claims; do not quietly relabel loss avoidance
  or ball contact as a scoring reward.

## Provider rounding

The live Jev 1.13.0 endpoint was observed returning two-decimal scores and probabilities,
including score 0.95 beside probabilities [0.47, 0.10, 0.43] (weighted index 0.96).
When all these numbers have at most two decimal places, allow 0.015 sum error and 0.020
weighted-score error, plus floating point epsilon. These bounds follow from three
independent probability rounding errors of at most 0.005 and a score error of 0.005.
Higher-precision answers retain the original strict tolerances. Reject nonfinite numbers,
out-of-range values and larger discrepancies. Normalize accepted probabilities to sum to
one and derive q and score from them; retain original probabilities and score in artifacts.
This is a transport precision adjustment, not empirical recalibration.

The [official primitive documentation](https://docs.typesafe.ai/primitives) describes
independent typed answers; the rounding behavior above is an observation from our live
request, not a precision guarantee made by those docs.

## Alternative Choice representations

`evaluate --primitive choice` keeps the original outcome state/target and converts the
six Score questions to named categorical outcomes. A distinct program hash includes the
representation version. `evaluate-actions` instead asks one immediate-action Choice and
computes sampled regret from the same frozen branches; it never treats action preferences
as outcome probabilities or Q values. Direct action reports omit Brier and value MAE.
Both CLI evaluators flush complete rows to `predictions.jsonl` before proceeding, preserving
partial evidence if a later request fails. This is checkpointing, not automatic resume.

The direct action runtime is `play --policy jev-action`. The categorical critic runtime is
`play --policy jev --primitive choice`. Neither is silently promoted to the default or
passed through the existing text-only learning gate. Choice response validation checks
option membership, finite probabilities and bounded rounding. The categorical critic
also requires the returned choice to be a maximum; direct actors resolve disagreement
using the distribution as described below. For N two-decimal probabilities, sum tolerance is N × 0.005
plus floating-point epsilon; accepted probabilities are normalized and originals retained.

See the [2026-09-18 representation comparison](choice-ablation-2026-09-18.md) for measured
results, token usage and the limits of comparison on already-used development states.

## Online direct-policy suites

`policy-suite` uses the model's own selected action at every decision, with no heuristic
continuation or fallback. Seeds in one suite must belong to a single split. A point limit
counts both positive and negative scoring events; only the action awaiting the final
point is allowed to end early on that point. All other actions retain the normal hold.
The point limit is an external truncation, distinct from ALE's native match termination.
Decision-limit exits are reported separately and cannot satisfy the five-point completion
condition. Every episode retains a JSONL trace and optional video.

`policy-feedback` exports only training episodes, taking up to two loss contexts and one
gain context per seed. A point's reward follows many actions; showing nearby actions is
not proof of individual causal credit. Policy proposals can change text without changing
observations or control duration. The explicit online gate compares matching development
seeds/protocols/models/limits, requires completed point windows, total reward improvement
of at least two, and no per-seed regression. It is a pilot acceptance rule, not a significance
test. Final-test suites cannot generate feedback or select a policy.

An interrupted first episode can replay its saved predictions using `--replay-prefix`.
Replay reconstructs the emulator from the original seed and checks each current observation
against the saved one, along with program, requested/response model, backend and action.
Only a matching prefix is accepted; new observations call the model normally. The original
HTTP attempts remain part of total cost; replayed predictions do not count as new attempts.
Suite/episode ledgers record only newly issued requests, so sum distinct original and resumed
suite ledgers, not their duplicated per-episode files.

Choice maximum-probability validation permits only 1e-12 floating-point tie error, in addition
to the existing two-decimal sum tolerance. On validation failure the ledger saves only known
option names and finite numeric probabilities, never arbitrary response text or credentials.


A live direct-policy request was observed with `choice=NOOP`, P(NOOP)=0.46 and P(LEFT)=0.47.
Direct actors now select the maximum of the validated action probability distribution,
retaining the provider choice on numerical ties and preserving `reported_choice` plus
`choice_matches_probabilities`. This resolves an observed provider inconsistency without
a heuristic fallback or another API call. Unknown options, invalid probabilities and malformed
schemas still stop execution. The selection rule is recorded separately from question text
as `probability-argmax-provider-tie-v1`; policy selection compares that rule as well.

`trajectory_diagnostics` estimates right-paddle returns from a positive-to-negative ball
horizontal velocity change near x >= 120. This is an observation-derived proxy that can
miss contacts, not a new reward. It also counts requested movement opposing the instantaneous
vertical gap; anticipatory interception can intentionally oppose that gap, so the count is
a diagnostic rather than a general action-correctness label.
