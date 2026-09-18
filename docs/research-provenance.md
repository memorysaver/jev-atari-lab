# Research provenance and implementation decisions

Historical research snapshot: private `memorysaver/idea` commit
`d591120290ef6216c1518e2c0d20bc0e5d8c7272`, topic
`deep-research/jev-structured-question-rl/atari/` (2026-09-17).

On 2026-09-18, the owner designated this repository's `docs/` as the canonical
home for all project research, including the teacher-optimizer objective,
evaluation methods, optimization patterns and paper planning. The
[research index](README.md), [direction](research-direction.md),
[optimizer design](teacher-optimizer.md), [evaluation framework](evaluation-framework.md),
[roadmap](research-roadmap.md) and [related work](related-work.md) consolidate
that direction in English. Readers do not need access to the historical private
notes. Those notes remain provenance, not a required upstream source of new research.

This repository owns the prototype code, tests, research and implementation decisions.
It is not a copy of the private workspace configuration. No upstream configuration,
credentials, runtime inventories, or ROM assets are included.

## Implemented choices

- Use Gymnasium/ALE directly and a small attributed Pong extractor instead of installing
  the whole OCAtari stack. Its inspected requirements pinned older NumPy/OpenCV versions
  and pulled in unrelated ML dependencies. The selected implementation is locked with
  Python 3.12, Gymnasium 1.3.0 and ale-py 0.11.2.
- Implement both RAM and simple RGB object modes, but use RAM for the first controlled
  evaluation. Keep the mode in every artifact.
- Start with fixed heuristic-continuation Monte Carlo branch labels and offline
  question selection. TD/Q-learning is deliberately a later, distinct experiment.
- Support imported teacher proposals so the first experiment only requires a Jev key.
  OpenRouter is an optional teacher adapter, not a prerequisite for local baselines.

## First-party references inspected

- [ALE environment options](https://ale.farama.org/environments/)
- [Pong action/reward reference](https://ale.farama.org/environments/pong/)
- [ALE installation and ROM packaging](https://ale.farama.org/getting-started/)
- [Gymnasium termination vs truncation](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)
- [TypeSafe state](https://docs.typesafe.ai/concepts/state)
- [TypeSafe Score](https://docs.typesafe.ai/primitives/score)
- [TypeSafe HTTP API](https://docs.typesafe.ai/api)
- [OpenRouter API](https://openrouter.ai/docs/api/reference/overview)
- OCAtari source and license: [third-party notices](../THIRD_PARTY_NOTICES.md)

Official API claims and launch speed benchmarks are not evidence of this prototype's
learning efficiency. Local environment and mock validation are recorded separately
in [validation.md](validation.md).
