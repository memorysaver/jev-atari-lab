# Evaluating question updates and optimizer patterns

Status: proposed framework, 2026-09-18. Existing experiments supply trajectories,
question versions and API ledgers. A repeated state-probe harness, independent
optimizer trials and the full round-record contract still need implementation.

The primary question is **which optimization mechanism produces reliable policy
improvements, in which situations, at what cost?** Text changes, behavior changes
and reward changes measure different parts of that question.

## 1. Describe the intervention

Record the parent and candidate question hashes, exact diff, teacher/context
version, evidence IDs, edited component and proposed operator. Examples of
operators include changing a threshold, clarifying coordinates, adding a condition
and replacing an action rule. Define categories before confirmatory analysis.

Text length, token count, number of changed fields and edit distance describe the
size of an intervention. They do not measure its intelligence or usefulness. A
one-token threshold edit can matter more than a paragraph of rewritten guidance.
Record the teacher's predicted effect separately from measured effects.

## 2. Measure behavior on the same inputs

Create a versioned probe set from training data, with a separate development set
for evaluation. Preserve observations, history and request construction. Include
ordinary states as well as predefined situations such as approach, retreat,
overshoot and missing observations. Record sampling weights; a failure-only sample
does not estimate average behavior during play.

For old and new returned action distributions p_i and q_i on input i, measure:

- **Action flip rate:** the fraction of inputs on which decoded argmax actions
  differ, using the runtime's fixed tie-breaking rule.
- **Distribution change:** mean Jensen-Shannon divergence, with m_i = (p_i + q_i)/2
  and JS(p_i, q_i) = [KL(p_i || m_i) + KL(q_i || m_i)] / 2. State the log base;
  with base 2 the range is 0 to 1. Validate and normalize provider outputs using
  the declared decoder before analysis; do not silently repair invalid responses.
- **Situation-specific change:** the same measures by prespecified situation,
  with counts and uncertainty, plus action frequency and rule agreement where relevant.

Repeat old-versus-old and new-versus-new queries under recorded settings to estimate
provider variability. Interleave query order where feasible so a time-dependent
service change is less likely to look like a prompt effect. Report repeat counts,
model versions, invalid outputs and missing pairs.

The controller currently executes argmax. A large distribution change may leave
every executed action unchanged; a tiny change near a tie can change an action.
Neither action flips nor output concentration imply better play. The
[no-FIRE experiment](pong-no-fire-2026-09-18.md) already shows why confidence and
adherence cannot be the reward objective. These diagnostic probes are our proposed
instrumentation, not a metric attributed to GEPA or TextGrad.

## 3. Measure the resulting policy

Freeze the environment, action space, observation adapter, model, control interval,
startup protocol, seeds, frame caps and stopping rules before comparison. Run both
policies on matched evaluation seeds and report each pair:

`delta_i = return(candidate, seed_i) - return(incumbent, seed_i)`.

Matching seeds reduces some variation; once actions diverge, trajectories and
random-event consumption can diverge too. This is a paired policy comparison,
not a claim that every subsequent transition has an identical counterfactual.

Predeclare the primary endpoint. For fixed-horizon studies it can be capped
episodic return. For native matches, record completed wins/losses and unfinished
runs separately. Report all scheduled episodes, completion rate and denominators;
completed-only win rate can be distorted by which policies finish. A frame cap is
not a terminal game outcome. API failures stay incomplete and retain their costs;
report any retry/restart policy and do not turn failures into fabricated returns.

Report mean paired differences and the full small-sample results. With sufficient
data, estimate uncertainty at the independent seed or optimization-run level;
do not treat correlated frames as independent samples. For repeated optimizer
trials, resampling should respect run/seed nesting and pairing. Predeclare the
interval method, practical improvement threshold and replication plan. One seed
or a three-round pilot cannot establish a population advantage.

## 4. Measure learning under a resource budget

Plot selected-policy performance against cumulative resources, not just round
number. Evaluate checkpoints according to a frozen schedule. The development
selector chooses checkpoints; never display an oracle chosen by final-test return.
Repeated development selection can overfit, so final claims require untouched
evaluation after optimizer design and policy selection are frozen.

Keep a resource ledger for every arm, including unsuccessful candidates:

| Resource | Include |
| --- | --- |
| Teacher | Calls, tokens, retries, model/version, context construction and wall time |
| Jev | All HTTP attempts, probe calls, rollouts, retries, invalid outputs and tokens |
| Environment | Collection, branching, validation, resets and replay frames, separately |
| Time | Model/API wall time, end-to-end wall time and simulated game time, separately |
| Money | Actual billed cost where available; otherwise dated rates and labeled estimates |

Compare quality at matched budgets or show an explicit quality/resource frontier.
Token counts alone are not comparable costs across models. A target-score efficiency
measure needs a predeclared target and a rule for runs that never reach it. Do not
divide improvement by cost without also reporting both quantities and uncertainty.

## 5. Isolate optimizer mechanisms

These are planned comparisons, not a mandate to run all combinations immediately.
Hold teacher/executor versions and starting questions fixed unless they are the
factor under study. Account for unequal evidence-generation and execution costs.

| Comparison | Question it answers |
| --- | --- |
| Frozen question versus optimized question | Does the complete process improve its starting policy? |
| Teacher with versus without trajectory feedback | Does experience add value beyond extra proposal attempts? |
| One-shot versus iterative proposals under a shared budget | Does iterative feedback help? |
| Generic reflection versus structured evidence packet | Does organizing evidence help? |
| Episode feedback versus local action branches | Does more explicit credit assignment justify its cost? |
| Greedy selection versus candidate/Pareto pool | Does retaining alternatives improve search? |
| No memory versus accepted/rejected edit memory | Does the optimizer reuse experience without accumulating regressions? |
| Proposed optimizer versus a GEPA adapter | Does the mechanism improve on a relevant prompt optimizer? |
| Single guidance versus richer question representation | Does structure help after accounting for information and calls? |
| Fixed optimizer with different executors; direct Python rule | What does Jev contribute to performance and cost? |

For the no-feedback control, permit the same number of proposals and evaluation
opportunities but withhold trajectory feedback from its teacher. Report actual
resource use as well as limits. Keep development feedback available only through
the declared selector interface; richer development feedback becomes an additional
optimization input and must be documented. Final-test results never feed selection.

## 6. Turn observations into testable patterns

Join each edit's provenance to probe changes, paired return differences and total
costs. Report patterns as **operator + applicable situation + measured effect +
regressions + resource conditions**, with links to the underlying rounds.

For example, an action-duration clarification might change overshoot decisions
without improving complete-match return. That would identify a behavioral effect,
not an effective optimizer pattern. This example is hypothetical.

Discover candidate patterns on training experiments, then freeze their definitions
and test them on independent runs and fresh seeds. Report unsuccessful edits and
unscreened or unevaluated proposals; an online evaluation filter creates selection
bias. Use controlled ablations to investigate mechanisms and declare exploratory
analyses and multiple comparisons. Cross-game confirmation requires held-out games
and recorded prior game knowledge. A convincing teacher explanation alone supplies
none of these measurements.

See the [optimizer design](teacher-optimizer.md), [roadmap](research-roadmap.md)
and [related work](related-work.md) for implementation stages and attribution.
