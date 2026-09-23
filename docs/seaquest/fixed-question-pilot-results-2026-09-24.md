# Seaquest first Jev pilot: successful execution, collapsed action behavior

**Complete:** two fixed-question Jev trajectories ended natively at 80 points each.
All **1,108 decisions** match a simple retrospective rule: choose DOWN while
objects are active, otherwise NOOP. The transport/recording/replay pipeline worked;
this is not evidence of a learned rescue/resource-management policy.

[Frozen pilot protocol](fixed-question-pilot-protocol.md) ·
[Observation gate](observation-v2-results-2026-09-24.md) ·
[Reviewed evidence](../../experiments/seaquest/fixed-question-pilot-v1/README.md)

## Matched training results

All programs have the same maximum 3,200 raw frames, sticky 0.25, four-frame hold,
18 native actions and no automatic startup controller. Native termination ends an
episode early; surviving at the frame cap is separately labeled.

| Program | Seed 310 score / frames | Seed 311 score / frames | Life losses per seed | End |
| --- | --- | --- | --- | --- |
| Jev fixed question | 80 / 2,213 | 80 / 2,213 | 4, 4 | Native termination |
| Random | 40 / 1,713 | 40 / 2,393 | 4, 4 | Native termination |
| Scripted sweep | 80 / 3,200 | 80 / 3,200 | 2, 2 | Frame cap |

The Jev scores exceed random here and equal the sweep's capped scores. Jev loses
all lives sooner, while sweep remains alive. This is a descriptive comparison of
two training seeds, not statistical superiority, teacher benefit or mastery.
[Original matched controls and their replays](../../experiments/seaquest/pilot-v1-controls/README.md)
are retained separately. Their open-loop/random actions do not use their semantic
observations, so the calibration-v1 decoder does not give them a control advantage.

## Main finding: general instructions did not yield differentiated behavior

Each Jev trajectory has **463 DOWN and 91 NOOP actions**, with no firing, horizontal,
upward or diagonal selections. Every NOOP coincides with unavailable object state;
every active-state action is DOWN. Each episode has 335 decisions taken with the
player below its initial surface height and a maximum carried-diver reading of one.
Thus it entered active play, but did not exhibit purposeful switching between the
prompt's rescue, firing, evasion and oxygen priorities.

The baseline is explicitly coordinator-authored, with global guidance and generic
native-action option descriptions. It was fixed before live calls. The collapsed
rule was identified after seeing the first trajectory; it is a descriptive fit on
visited states, not a prospectively tested policy or proof of Jev's internal reasoning.
Possible explanations include over-weighting the instruction to leave the surface,
weak action-specific conditions, or difficulty using the state/history. This pilot
does not distinguish them. Do not generalize the failure to all Jev representations.

The two runs had **identical semantic observations at all 554 decision indices**,
identical actions, and identical raw-frame records at **552/554 decision blocks**.
Changing seeds under this nearly constant action policy supplied little effective
state diversity. These are two executions, not convincing independent robustness
or optimizer replications. Subsequent evaluations need measured start/state diversity,
with any reset-randomization change frozen before the next data collection.

## Observation scope during live execution

All 462 active player boxes per episode had expected-color support. Six shark-box
support mismatches per episode remain retained. Diver boxes had support at all 741
observations per episode. These checks are limited pixel support inside proposed
boxes, not exact object identity/shape/recall validation. The pilot encountered no
player-fired missile, enemy-submarine or enemy-missile box in its recorded action
trajectory; their prior calibration coverage is not live-pilot coverage.

A carried count of one is not evidence of a completed rescue/unloading cycle, and
no validated cause-of-death classifier is implemented. Native rewards and life loss
come directly from ALE. No counterfactual consequence labels were invented.

## Provenance, resources and audit

- Frozen source `cce2c5f57685bcfc99f203c2aa8476ef344a6c22`.
- Fixed program hash `d76d597a229e8fc4ac82076ee29bddbe0cf087280d7fa29cac9aec37cf23a66b`.
  [Exact program](../../examples/seaquest-policy-program.json).
- Requested OpenRouter `~typesafe/jev-latest`; all successful responses matched
  `typesafe/jev-1.13-20260917`. No model substitution or program edit.
- **1,108/2,000 permitted attempts**, all HTTP 200; zero live retries or failures.
  Retry failure paths were tested with synthetic HTTP, not demonstrated by this run.
- **4,426 controlled frames / 1,108 decisions**, zero reset no-ops. Two native ends.
- **2,827,464 input / 205,162 output tokens**; **342.64 seconds** recorded API time.
  The supervised process ran about 346.50 seconds and exited zero.
- Successful-response OpenRouter cost: **US$0.118753488**. **Zero teacher calls.**
  Call accounting is separate from unknown failed-call billing; no failure occurred here.
- Both original and restored pilot archives passed original-request reconstruction,
  original-response action decoding and complete raw-frame emulator replay.
  Each full replay audit adds a separate 4,426 emulator frames and zero API calls;
  an earlier first-episode-only replay adds another 2,213 frames.
- Four matched control trajectories used 10,506 collection frames, 10,506 initial
  replay frames and a separate 10,506-frame restored replay. Zero model calls.
- All exact exchanges, videos, observations, raw frames, plans, budgets, results,
  costs and failed box checks are preserved. Local Git LFS archives were restored;
  no remote preservation or retrieval is claimed.

The pilot is closed with unused capacity; that capacity is not reused for adaptive
prompt trials. Pong remains closed. Earlier negative results remain in the record.

## Next research question

Can a teacher turn the observed action collapse into **state-dependent action
criteria** that improve control? Freeze a separate representation/teacher experiment,
retain this fixed question and the observed collapse rule as explicit controls,
and supply only training evidence to an isolated teacher. Check whether actions
respond to relevant state differences before a larger gameplay budget, while
keeping actual return as the outcome. Action diversity alone is not success.

Separate strategy quality, question execution, and feedback benefit: a better manual
prompt would not establish teacher learning, and one improved teacher proposal would
not establish a repeatable feedback advantage. Do not expand into a long optimizer
study before the next bounded action-discrimination test is interpretable.
