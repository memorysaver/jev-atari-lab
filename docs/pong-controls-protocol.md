# Fixed-frame Pong controls

This protocol is frozen before the first live comparison. It isolates question
wording, the tracking deadband, and execution of the same rule by Jev or Python.
It is a development pilot, not a teacher-learning round or a final-test benchmark.

## Four fixed arms

| Arm | Definition |
| --- | --- |
| `jev-original` | Unchanged [original direct question](../examples/action-program.json) |
| `jev-vertical` | Unchanged [vertical-control question](../examples/vertical-policy-program.json), asking Jev to apply the 4px rule |
| `python-4px` | The same center-y rule, computed directly from the observed bounding boxes |
| `python-2px` | The existing tracking heuristic, unchanged |

State contains object bounding boxes `[x, y, width, height]`, motion history and
action metadata. No precomputed center gap, recommended action, or rule result is
added to Jev's input. The candidate question asks Jev to compute center y as
`y + height / 2`. A ball more than four pixels above/below the paddle requests
RIGHT/up or LEFT/down; within the inclusive +/-4px band or with either object
absent, request NOOP. Both implementations prefer the non-FIRE action.

Python's 2px continuation in the older value experiments remains unchanged.

## Frozen first-run settings

- Development seeds: **36, 37, 46, 47**. These were absent from the existing pilot
  records when selected. No final-test seed is used.
- Jev: **jev-1.13.0**, validated probability argmax, provider choice only for ties.
  A different returned model stops the experiment before its action executes.
- RAM object observations; six original actions; hold=4 raw frames; sticky=0.25;
  reset NOOPs=0..30; original ROM, mode and difficulty in the protocol manifest.
- **2,000 controlled raw frames per policy/seed**, excluding reset frames, at most
  500 decisions. The current CLI requires a horizon divisible by the action hold.
- No five-point cutoff. Native game termination ends emulator execution and adds
  a conceptual zero-reward absorbing tail to the evaluation horizon, without
  inventing frames or actions. Environment truncation and API failure are incomplete,
  have no evaluation reward, and stop the comparison.
- One shared **4,400 HTTP-attempt cap**, including retries, for up to 4,000 decision
  calls across both Jev arms. No teacher calls, cache, paid diagnostics, or cap reset.
- Each seed runs Python 2px, then Python 4px. Jev original runs before vertical on
  seeds 36/46; vertical runs before original on seeds 37/47. Calls are sequential.
- No question edits or automatic candidate promotion during the comparison.

## Measures and interpretation

The primary measure is each seed's undiscounted net reward over the fixed horizon.
Report scored/lost points separately, native terminations, actual emulator frames,
reset frames, absorbing-tail frames, decisions, tokens, HTTP attempts and elapsed
time. Failed calls count toward costs. Provider billing is not inferred from tokens.

Report paired reward differences for vertical-minus-original,
vertical-minus-Python-4px, and Python-4px-minus-Python-2px. Do not compare actions
at the same decision index once trajectories diverge. Instead, evaluate Python's
4px rule on each policy's own recorded observations and count action disagreements.
This diagnoses rule execution; matching the rule does not prove optimal control.

There is one API realization per arm/seed. Four seeds and short horizons cannot
establish statistical significance, learning convergence, full-game win rates, or
generalization to Atari. Replaying cached actions is verification, not an independent
trial. No post-hoc seed replacement or selection threshold is used.

## Run and audit

```bash
uv run --env-file "$HOME/.config/typesafe/credentials.env" jev-atari compare-controls \
  --backend jev --model jev-1.13.0 --max-api-calls 4400 \
  --baseline-program examples/action-program.json \
  --candidate-program examples/vertical-policy-program.json \
  --seeds 36 37 46 47 --frames 2000 --video \
  --out artifacts/pong-controls-v1
```

Optionally provide `--source-revision` with the source commit used. Each run writes
its immutable `plan.json` (including full programs/hashes and schedule) before
any policy executes. `comparison.json` saves completed episodes and incomplete
status during execution; the shared API ledger is written on exit.

Each `<arm>/seed-<seed>/` contains the original episode manifest, per-decision
transitions, per-frame RAM/RGB hashes, summary, evaluation and video. Jev episodes
also contain complete successful JSON request/response exchanges and a per-episode
API ledger. Exchange IDs are unique across the shared budget.

```bash
uv run jev-atari inspect-step \
  --episode artifacts/pong-controls-v1/jev-vertical/seed-36 --decision 100
uv run jev-atari replay \
  --episode artifacts/pong-controls-v1/jev-vertical/seed-36 \
  --out artifacts/pong-controls-replay/seed-36
```

Publish the original evidence, failed runs if any, checksummed archive, and all
per-seed results after verification. This new protocol does not retroactively
change the rejected five-point gate in the historical pilot.
