# Question diagnostics: execution gaps and literal strategy controls

**Observed:** The failed interception question has a large action-adherence gap,
including states where interception and ordinary tracking prescribe the same
movement. Separately, four Python interpretations produce mixed results on four
training seeds. Conservative short-horizon prediction has the best observed mean,
but no controller wins a completed match and no Jev policy is promoted.

This follows the [frozen diagnostic protocol](question-diagnostics-protocol.md),
with **zero new Jev or teacher calls**. The earlier teacher study and its unused
final seeds remain unchanged. This is a diagnostic study, not a new teacher round.

## Does Jev execute the question's rule?

We interpreted the original A question using its explicit arrival formula and
[35,192] reflection interval. We evaluated that rule on the exact original
observations without executing substitute actions. Source bytes were checked
against the published teacher-study archive manifest.

| A candidate trajectory | All decisions matching rule | Active interception matching rule | Missing-object decisions matching rule |
| --- | ---: | ---: | ---: |
| Seed 66 | 379/757 (50.07%) | 28/289 (9.69%) | 328/328 |
| Seed 67 | 432/758 (56.99%) | 62/309 (20.06%) | 309/309 |

The pooled active-interception agreement is **90/598 (15.05%)**. In 494 of those
598 decisions the rule requests RIGHT/up but Jev chooses LEFT/down. Missing-object
NOOP agreement substantially inflates the overall percentage. These are
instruction-adherence labels, not labels of the optimal action.

An exploratory follow-up after seeing these results compares the two rule outputs
on the same A-candidate states. In **576 of 598** active-interception states,
current-height tracking and interception prescribe the same action; Jev matches
that shared action only **82/576 (14.24%)**. Thus disagreement between the two target
strategies cannot explain most of this measured adherence gap. This does not reveal
Jev's internal calculation or identify which wording component caused the failure.
The subset and example selection are post-hoc, not original primary endpoints.

### One original decision

At seed 66, decision 24, the ball center is y=162 and player center y=154.5. The
observed ball velocity is (1,-2) pixels per raw frame. The stated arrival calculation
is `(140-26-2)/1 = 112` frames. Projected y=-62 reflects at the stated lower bound
to y=132. The target is 22.5 pixels above the paddle: the rule requests RIGHT/up.
Jev assigns RIGHT 0.35, LEFT 0.38, NOOP 0.25 and 0.01 to each movement+FIRE alias;
its recorded argmax action is LEFT/down. Current-height tracking would move down
in this particular example; the larger subset above shows that this explanation
does not cover most active-interception states.

[Original request, response, transition and diagnostic calculation](../../experiments/pong/question-diagnostics-v1/example.json)
preserve this first matching discrepancy in seed order, rather than a fabricated
illustration or reconstructed provider response.

## Shared-input probes and B's ambiguity

Original probes contain 32 training observations and two repeats per program.
They were already collected in teacher-study-v1; this study adds no predictions.

| Program and diagnostic interpretation | Agreement on 64 responses |
| --- | ---: |
| A parent / current-height v2 | 42/64 (65.63%) |
| A candidate / stated interception | 30/64 (46.88%) |
| B parent / current-height v2 | 41/64 (64.06%) |
| B candidate / four-frame lookahead | 42/64 (65.63%) |
| B candidate / conservative lookahead | 42/64 (65.63%) |

The two B interpretations prescribe identical actions on these probes, so this
small probe set cannot distinguish their strategy consequences. Across B's visited
development states, lookahead agreement is 57.58% and 53.74%; the conservative
interpretation gives 57.78% and 53.90%. All counts, confusion matrices and strata
are in the [adherence results](../../experiments/pong/question-diagnostics-v1/adherence.json).
Responses share states and trajectories; these are not independent Bernoulli trials.

B's "reliable" motion and "evident bounce" are not uniquely executable definitions.
The conservative version requires two successive observable motion segments with
no velocity sign reversal; otherwise it falls back to current height. Both
operationalizations were fixed before new local gameplay. Neither is asserted to
be the teacher's uniquely intended algorithm.

## Is the literal strategy useful?

Run the four frozen Python controllers in the real local ALE environment on
training seeds 80/81/82/83, capped at 20,000 controlled frames or native termination.
All share observations, the six-action environment and sticky-action settings.
They are explicitly separate control arms; no Python action replaces a Jev action.

| Python rule | Seed 80 return | Seed 81 | Seed 82 | Seed 83 | Mean | Native completions / 4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Current-height v2 | -15 | -12 | -9 | -10 | -11.5 | 3/4 |
| A interception | -5 | -10 | -5 | -18 | -9.5 | 1/4 |
| B latest-segment lookahead | -5 | -17 | -2 | -18 | -10.5 | 2/4 |
| B conservative lookahead | +6 | -15 | -1 | -10 | -5.0 | 2/4 |

All eight native completions were losses: win denominators are 0/3, 0/1, 0/2 and
0/2 respectively. Remaining episodes are censored, not draws or wins. In particular,
conservative seed 80 ended **14:8 at the cap**, not a completed victory.

Conservative lookahead gains +21, -3, +8 and 0 relative to literal v2, averaging
+6.5 on these four seeds. Its seed-81 regression prevents a universal improvement
claim. A interception averages +2 versus literal v2 but regresses by 8 on seed 83.
These are small training comparisons, not held-out estimates or a selection gate.
No historical Jev mean is subtracted from these new Python means: the seed sets
and visited trajectories differ.

The result narrows the research problem. Execution fidelity matters, while even
perfect execution of these operationalizations does not yet provide robust Pong
control. A higher adherence score alone would not establish improved gameplay.

## Preservation and reproducibility

The controller implementation and protocol were committed before local rollouts at
`dfec7fd`; the exact full revision appears in the trial plan. The original analysis
and later exploratory subset/example extension are both retained. Original frozen
rules, recorded actions and outcomes were not changed after inspection.

All **16 episodes**, **282,134 controlled raw frames** and **16 videos** are retained.
Every local action was checked against the frozen controller; independent replay
verified observations, frame hashes and rewards. Synthetic tests cover time units,
reflection geometry, missing/outgoing motion, sign changes and deadband boundaries.
The repository has 122 passing tests. Model calls and billed inference are zero
for this diagnostic study; local compute is not claimed to be free.

[Data, videos, manifest and replay instructions](../../experiments/pong/question-diagnostics-v1/README.md)
include per-decision diagnostic rows, original example exchanges, full local traces
and replay audits. Development-derived diagnostics remain separately labeled;
they must not be presented to a future teacher as training-only feedback.

## Implication for the next optimizer

A next bounded teacher protocol should require a precise motion-reliability
condition and predicted actions on synthetic boundary cases, then test behavior
on a stratified training-state probe before expensive rollouts. Preserve missing
objects, incoming/outgoing motion and boundary cases as separate denominators.
Any probe-screening gate must be frozen prospectively; it was not applied here.

Compare atomic edits to action semantics and target calculation separately. Keep
a literal reference implementation for auditing, not as a hidden executor fallback.
Still evaluate actual Jev gameplay and retain a no-feedback control. These are
proposed optimizer changes motivated by diagnostics, not evidence that the teacher
has already learned an effective update rule.
