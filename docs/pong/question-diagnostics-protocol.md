# Question execution diagnostics v1

Frozen before new local-control outcomes, 2026-09-20. This follows the owner's
request to continue the [next research design](teacher-study-next.md). It is a
separate **zero-model-call** study, not a continuation of the expired teacher study.

## Recorded-state analysis

Analyze all eight first-round development trajectories from teacher-study-v1 and
its two fixed-input probe blocks. Check input bytes against the published archive
manifest. Report action agreement, confusion counts and probability assigned to
the interpreted rule action. Stratify trajectory agreement by observed motion,
interpretation mode and number of target reflections. Report every rule, including
alternative interpretations, on every trajectory and shared probe set.

Development analysis is retrospective and must not become a supposedly train-only
teacher packet. Different policies visited different states. The shared 32 training
states, with two repeats per program, support a more controlled adherence comparison;
64 responses are not 64 independent states. No new Jev predictions are generated.

## Explicit operationalizations

- `v2`: current bounding-box center, strict 4px deadband, RIGHT/up and LEFT/down.
- `intercept`: A's incoming-ball arrival formula; only positive valid vx with ball
  right edge before the paddle; reflect projected center into exactly [35,192].
  Outgoing/unknown motion uses current ball height. This differs from the older
  `InterceptPolicy`, which recenters on outgoing motion and uses other wall bounds.
- `lookahead`: B interpreted using the latest valid supplied pixels/raw-frame velocity;
  incoming target equals current center plus vy times requested hold (four frames).
  Unknown/outgoing motion uses current height; no additional wall reflection.
- `lookahead-conservative`: the same B interpretation, but require three consecutive
  visible history samples with positive time intervals and no x/y velocity sign
  reversal across the last two segments. Otherwise use current height.

B's "reliably" and "evident bounce" do not uniquely specify an algorithm. The two B
implementations are sensitivity analyses, not claims of recovered teacher intent.
Velocity validity means finite differences exist, not proof of collision-free motion.
All rules use only the existing observation. Missing ball/player chooses NOOP.
Synthetic tests cover time units, reflection boundaries, missing/outgoing motion,
recent sign reversals and exact 4px boundaries. Diagnostic actions never replace
recorded Jev actions or modify its action probabilities.

## Local strategy trials

Run all four Python rules on training seeds 80/81/82/83, with the unchanged default
Pong protocol, six-action environment, four-frame decisions and sticky actions.
Each episode ends at native termination or 20,000 controlled raw frames. Schedule
seed-major, rules in the order above. Maximum 16 episodes / 320,000 controlled frames.
Record every decision, raw-frame trace and video; independently replay all episodes
and verify that executed actions match the frozen implementation. Reset frames
remain separate. No API credentials, model calls, teacher revisions or policy gate.

These are fresh local training rollouts, not paired replacements for the prior
Jev development episodes. Report all per-seed returns, native completion/win
denominators and censored outcomes. Do not compare means across these different
seed sets as a causal Jev-versus-Python effect, promote a Jev question, or open the
reserved final seeds. A strong literal controller would motivate a later bounded
Jev adherence study; weak literal control would motivate a strategy change first.

Working evidence: `artifacts/pong/question-diagnostics-v1/`. Publish reviewed data
under `experiments/pong/question-diagnostics-v1/`, with an LFS archive and checksums.
Preserve the old study and all negative results unchanged.
