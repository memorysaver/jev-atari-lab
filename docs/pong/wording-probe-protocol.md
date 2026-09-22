# Compact versus expanded wording probe v1

Frozen before model access, 2026-09-22, following the owner's request to find and
continue the Atari Jev study. This distinct diagnostic follows the negative
[motion probe](motion-probe-results-2026-09-21.md). Its budget does not resume any
expired study. This protocol authorizes no follow-on gameplay within this run.

## Intervention and controls

Compare v2, the unchanged explicit-motion question (expanded), and one compact
restatement of the same conservative rule. The only changed request field between
expanded and compact is `questions.next_action.instructions.question`. Preserve
the observation, six native action criteria, model `jev-1.13.0`, one Choice question
and probability-argmax decoder. Program names are metadata outside model requests.
Exact text is in [D002](teacher-rounds/D002-compact-wording.md) and frozen source
[`wording_probe.py`](../../src/jev_atari/wording_probe.py).

The intended rule is unchanged: initially track ball center; add four raw frames
of vertical velocity only with valid incoming velocity and three visible, strictly
time-ordered ball samples without x or y sign reversal. Zero displacement is allowed.
Otherwise retain current height. Missing ball/player means NOOP. Gaps below -4
mean RIGHT (UP), above +4 mean LEFT (DOWN), inclusive deadband means NOOP. No FIRE,
extra time scaling or wall reflection. The existing conservative Python evaluator
is the reference; it never supplies the model's input or chosen action.

This tests a specific restatement, not text length alone: redundancy and surface
wording change together. The coordinator has seen earlier training/development
and diagnostic results. No isolated teacher is invoked; its interactive cost/model
version are not independently recorded. There is exactly one new candidate and
no response-dependent edit, alternative model or quality-based resampling.

## Inputs and execution

Regenerate the same 80 states (eight per ten strata) used in motion-probe-v1 from
the checksummed question-diagnostics-v1 Python trajectories, training seeds
80/81/82/83. Verify exact equality with the published input/coverage files. These
states are deliberately reused and already inspected; this is exploratory training
evidence, not an untouched validation set. Rewards, successors, previous Jev
answers, reference actions and stratum labels stay outside requests. There are
no new emulator frames, gameplay outcomes, final-test seeds or videos.

Every state receives all three programs twice, rotating program order by
(state index + repeat) modulo three: 480 scheduled predictions. Freshly evaluate
the expanded and v2 controls; historical answers are context, not this comparison's
control outcomes. Record repeat variation and all strata, not just the targeted bin.

Use explicit `--backend jev` and the existing shared local credential environment.
Freeze code, protocol and proposal in a local Git commit before calls. Limit this
study to **520 total HTTP attempts including retries**, and **four hours** from the
first reserved attempt. The existing durable budget reserves before transmission.
Eligible transport/429/500/502/503/504/529 errors may retry at most twice per
prediction against the same cap. Exhausted retries, malformed responses, model
mismatch or limits stop the run, retaining incomplete evidence. Never overwrite,
resume or reset this run. No teacher API calls are scheduled.

## Predeclared measurements and screen

Primary contrast: compact minus freshly evaluated expanded agreement with the
conservative reference on the balanced 80-state set. Report the uncertain-conflict
and stable-conflict bins explicitly, all basic fallback/up/down/hold bins, v2's
agreement with its own rule, all four diagnostic-rule scores, repeated-action
flips, attempt/token costs and API elapsed time. Two answers per state and nearby
trajectory states are correlated; these are descriptive results, not independent
sample significance tests or natural-gameplay accuracy estimates.

The compact question is eligible only for **separate future gameplay-study design**
if all of these prospectively chosen conditions hold:

- All 480 scheduled responses complete without model substitution.
- Conservative-rule agreement is at least 80% overall (128/160).
- Overall agreement improves by at least 10 percentage points over fresh expanded.
- Missing-object agreement is 16/16.
- Each of the other nine strata has at least 12/16 agreement on eight states.

These pragmatic screening thresholds are not empirically calibrated guarantees
of good gameplay. Any failed condition makes the candidate ineligible; preserve
all failures. A pass is not policy promotion, Atari mastery or evidence of teacher
learning. The gameplay reference stays v2. No extension or additional search is
part of this budget, regardless of the outcome. Future causal claims about
experience feedback still require the [teacher endpoint](research-endpoint.md).

## Evidence and offline reproduction

Working root: `artifacts/pong/wording-probe-v1/{pack,run,audit}/`. Reviewed local
evidence: `experiments/pong/wording-probe-v1/`. Store selected observations, source
hashes, programs, proposal provenance, schedule/source commit, original HTTP JSON,
parsed predictions, durable budget, metrics, screen and audit. Archives use Git
LFS. Local preparation is not remote preservation; claim remote availability only
after a separately authorized publication and fresh remote retrieval verification.

```bash
uv run python scripts/wording_probe.py prepare \
  --source artifacts/pong/question-diagnostics-v1/local \
  --out artifacts/pong/wording-probe-v1/pack
uv run --env-file "$HOME/.config/typesafe/credentials.env" python scripts/wording_probe.py run \
  --backend jev --pack artifacts/pong/wording-probe-v1/pack \
  --out artifacts/pong/wording-probe-v1/run
uv run python scripts/wording_probe.py verify \
  --source artifacts/pong/question-diagnostics-v1/local \
  --pack artifacts/pong/wording-probe-v1/pack --run artifacts/pong/wording-probe-v1/run \
  --out artifacts/pong/wording-probe-v1/audit
```

The verifier reconstructs the selection from training sources and checks every
request/response, action, program/model hash, schedule, cost and screen without
model access. It shares the previous probe's audited recorder, with an explicit
study identity and preparation function; the original protocol remains unchanged.
