# Research direction

**Can experience improve structured questions used by a fixed decision model,
and does that improve sequential decision-making at a competitive total cost?**

The original value-based track remains a core research question. A direct-action
track provides a simpler comparison. Neither is automatically Q-learning.

The teacher proposes question changes from training evidence. Jev answers those
questions; the environment supplies outcomes. Development evaluation selects or
rejects candidates. The learned artifact is the external question program, not
updated Jev or teacher model weights.

## Next controlled comparisons

- The [first fixed-frame controls](pong-controls-2026-09-18.md) now compare both
  Jev questions with Python 2px and 4px rules. The vertical question had better
  aggregate reward but only 66.85% literal-rule agreement; replicate this result
  and separate instruction execution from strategy quality. The value critic
  still needs a matched online comparison.
- Test multiple teacher rounds with fixed observation/action/reward contracts.
- Separate trajectory-only feedback from snapshot-based action comparisons.
  Heuristic continuation does not estimate Jev continuation value.
- Compare one-time advice with experience-driven revisions under matched budgets.
- Only then test structural question changes, retrieval or TD targets.

Isolate teacher requests to training evidence. An interactive assistant that has
seen development results is not strictly train-only just because the latest input
contains only training examples.

## Related work and novelty limits

[GEPA](https://arxiv.org/abs/2507.19457) is a relevant outer-loop prompt optimizer.
We inspected its adapter interface but have not integrated or benchmarked it.
[Reflexion](https://arxiv.org/abs/2303.11366) and
[TextGrad](https://arxiv.org/abs/2406.07496) provide related language-feedback methods.
[TypeSafe's autoresearch example](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery)
already adds, revises and drops structured questions for supervised feature discovery.

Teacher-authored question revision is not a new learning principle. A contribution
would require evidence about temporal credit, representation, generalization, or
this system's quality/cost tradeoff. Those claims have not been established.
