# Next research: separate strategy quality from question execution

Status: **proposed after teacher-study-v1; no new live study launched here**.
The [incomplete first study](teacher-study-results-2026-09-20.md) provides two rejected
edits and a transport failure, not a multi-round learning curve. Preserve its
frozen protocol and reserve a distinct study ID, budget and data split for a new run.

## Questions to resolve

1. Does the intended rule produce useful control if implemented literally?
2. Does Jev's action follow that rule on the same observation?
3. Does a teacher edit improve held-out gameplay under a fixed total cost?

These are different measurements. A wording change can improve adherence to a bad
rule. A policy can score better while disagreeing with its prose. Confidence is
neither an observed reward nor a calibrated estimate of correctness.

## Decompose the failed intervention

Compare small, predeclared operators: clarify current-center comparison; add a
single four-frame vertical lookahead; add incoming-ball gating; then add reflection
handling. Keep observations, action space and decoder fixed. Do not treat this
post-result decomposition as the original study's predeclared hypothesis.

Implement each intended rule as an offline diagnostic evaluator first. Validate
coordinate units, finite-difference time intervals, missing ball states, velocity
signs and wall contact on synthetic cases. These Python diagnostics must not
silently replace Jev actions. Run literal controllers as explicitly separate arms
before spending a large teacher/Jev budget on complex prediction wording.

For each shared input, record intended direction, Jev distribution/action, vertical
gap, incoming/outgoing motion, time to contact and reflection count. Stratify
adherence and repeated-query variation by these conditions. Review failure windows
before a missed paddle contact, not only a point several frames later. Missing
counterfactuals stay missing; do not call those windows TD targets or causal credit.

## Teacher optimizer comparison

Retain a no-trajectory-feedback control, an unchanged-policy reference and at least
one limited-edit operator. Compare experience selection methods under explicit
teacher and Jev resource accounting. Context volume and token costs differ between
arms; equal invocation counts alone are not equal compute budgets.

A teacher proposal should state one mechanism, referenced training evidence,
predicted action changes and a falsifying outcome. Preserve the exact input,
response, program diff, fixed-input probe and gate result. Multiple independent
optimizer runs and untouched final seeds are necessary before estimating a
repeatable benefit. Development reuse must be reported as selection exposure.

## Reliability before another long run

The post-study recorder now retains failed subprocess diagnostics privately before
raising; public records contain only a retention flag. Test failure paths without
live APIs, including a nonzero exit with `turn.failed`. A future protocol should
predeclare whether access failures stop the study or permit bounded identical-packet
transport retries. Do not reinterpret schema-repair allowances as transport retries.

Supervision must detect a terminated process promptly, preserve the failed record,
and report the actual stopped state. The original study spent about 3 hours 19
minutes running before it stopped; elapsed time until discovery is not model
computation. A new bounded launch should follow a successful access check counted
inside its own approved budget, never reset the old study's deadline or reuse final
data as training feedback.

## Paper boundary

A supported near-term contribution is the representation and audit methodology:
versioned structured questions as executable policies, controlled teacher-visible
experience, measurable behavioral edits and reproducible environmental outcomes.
Evidence for a successful optimizer requires more than that methodology. This
study supplies negative/incomplete results and precise next tests; it does not
establish novelty, RL convergence or a stronger Atari agent.
