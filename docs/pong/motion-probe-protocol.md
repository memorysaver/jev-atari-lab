# Stratified motion-reliability probe v1

Frozen before new model responses, 2026-09-21. Owner requested continued research
and evaluation. This is a new bounded diagnostic study, not a reset or extension
of teacher-study-v1's expired clock or budget.

## Question intervention and provenance

Compare three fixed programs: v2; the original round-one B lookahead question;
and `pong-explicit-motion-reliability-v1` in `src/jev_atari/motion_probe.py`.
The new guidance explicitly requires valid incoming velocity, three consecutive
visible history samples with increasing timestamps, and nonnegative products of
successive x and y displacements. Otherwise track current ball height. If eligible,
advance by vy*4, with the same 4px deadband and action meanings. This operationalizes
the previously evaluated conservative Python rule without inserting its computed
answer or target into the Jev input.

The interactive coordinator authored this diagnostic revision after seeing prior
development results. It is **manual and development-informed**, not an isolated
teacher-generated proposal or learned update. Exact source, programs, inputs and
hashes are saved before model access. No teacher invocation is scheduled.
Jev weights/version, observations, one Choice question, six native action criteria
and probability-argmax decoding remain unchanged. Only guidance/name differs.

## Training state selection

Use all recorded pre-action observations from the 16 Python training episodes
on seeds 80/81/82/83 in question-diagnostics-v1. Check manifests and transitions
against that published archive's SHA-256 inventory. Ignore rewards, successors
and executed actions when selecting inputs. Deduplicate by canonical observation
hash, preserving the first source in fixed rule/seed order.

Ten disjoint strata: missing object; unknown velocity; outgoing; stationary x;
incoming uncertain motion with/without disagreement between latest-segment and
conservative lookahead; incoming stable motion with disagreement between current
tracking and conservative lookahead; and stable agreement split into up/down/hold.
These bins and their predicates are versioned in the source.

Select the eight lowest observation hashes per stratum, at most 80 states. Do not
backfill underfilled/empty strata. Also report coverage of the 32 lowest hashes
from the same unique pool as a hash-uniform coverage reference, without additional
model calls. This compares coverage, not representative policy performance.
The two disambiguation bins intentionally oversample rare rule disagreements.
The resulting micro average is not an estimate of natural gameplay accuracy.

Original frame/state histories are preserved. Model requests receive only the
original observation. State IDs, stratum labels, rule actions and source metadata
stay outside the model input. Synthetic tests validate classification, schedule,
label separation and budget behavior; synthetic data are not live evidence.

## Evaluation and bounds

For every selected state query all three programs twice. Rotate program order by
(state index + repeat) modulo three. Maximum 480 successful predictions and
**520 HTTP attempts including retries**, with a new four-hour deadline beginning
at the first attempt. Explicit `--backend jev`, pinned `jev-1.13.0`, shared local
credential environment. Every attempt reserves durable capacity before sending.
Never overwrite/resume an existing output directory or reset the budget.

Retry existing eligible transport/429/500/502/503/504/529 failures at most twice
per prediction, charged to the same cap. Malformed answers, model mismatch,
exhausted retries or limits stop execution and preserve the prefix. No alternative
model, decoder, hidden controller or quality-based resampling.

Report per-program/per-stratum counts, agreement with all four frozen diagnostic
rules, repeated-action variation, raw response distributions and costs. The primary
mechanistic contrast is precise versus ambiguous agreement with the conservative
rule on incoming-uncertain-conflict states. Also report stable-conflict and basic
up/down/hold behavior to expose regressions. Evaluate both interpretations of B;
do not retroactively declare ambiguous wording to have one unique meaning.

No gameplay rollouts, rewards, confidence calibration claim, promotion gate,
held-out test access or statistical significance claim. Correlated states and
repeated requests are not independent trials. A favorable result would support a
future bounded gameplay test, not prove an effective teacher optimizer.

## Evidence

Working root: `artifacts/pong/motion-probe-v1/`; publication:
`experiments/pong/motion-probe-v1/`. Save full selected observations, program texts,
provenance/coverage, schedule, durable reservations, original HTTP JSON exchanges,
parsed predictions, failures and metrics. Reproduce state selection from the
published training archive and validate all original responses offline. Publish
checksummed LFS evidence and verify it from a fresh remote checkout. No new videos
are generated because the emulator is not advanced during this fixed-input study.
