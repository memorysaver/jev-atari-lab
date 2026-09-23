# Candidate-feedback OpenRouter study: launch record

The three-round Pong closure study launched at **2026-09-23T15:04:35.793746+00:00**.
This is a launch record, not a completed-result report. Read runtime status for
subsequent completion or a technical stop.

- Frozen source: `96ec5944460406af41ba565e95049b16bbaae7e2`.
- [Prospective protocol](candidate-feedback-openrouter-protocol.md).
- Working root: `artifacts/pong/candidate-feedback-openrouter-v1/`.
- Supervisor: `artifacts/pong/candidate-feedback-openrouter-v1-supervision.json`;
  runner log is the adjacent `candidate-feedback-openrouter-v1-runner.log`.
- Plan/source/seed inventory and budget were written before the first teacher call.
  All 16 proposed training/development/final seeds had no existing local episode
  manifests at preflight. Earlier experiment roots remain preserved.
- One A/B search, three sequential rounds, then sealed final evaluation; maximum
  30,000 Jev attempts and 10 teacher invocations, with a 24-hour live deadline.
- Validation before access: full suite 155 tests passed; the subsequently added
  preparation-failure test and all five other new study tests passed together.
  Ruff lint/format and whitespace checks passed. Tests used no live models.

The supervised runner executes all rounds and final evaluation, writes round
selections and the final endpoint, and records its actual exit status. Errors
preserve incomplete records. An ended process must never be described as running.
No live non-Pong experiment has started; [Seaquest is the next-game recommendation](../next-atari-game-2026-09-23.md).

## Closure, 2026-09-24

The runner exited 1 after an HTTP 502 in second-round training. The owner requested
Pong closure, with no restart. [Closure report](candidate-feedback-results-2026-09-24.md)
and [verified local evidence](../../experiments/pong/candidate-feedback-openrouter-v1/README.md)
supersede the launch-time running state. No final tests were executed.
