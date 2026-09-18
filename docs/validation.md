# Local validation — initial checks on 2026-09-17

## Fixed-frame controls — 2026-09-18

- 83 tests pass, including deadband boundaries, a single budget across arms/seeds,
  retries, incomplete-run preservation, pinned-model enforcement before execution,
  and native-terminal versus error treatment at the evaluation horizon.
- Lint, formatting, repository checks and wheel/source builds pass; GitHub CI
  passed for the frozen experiment implementation commit `c415207`.
- All 16 real episodes replay with matching observations, rewards and frame hashes.
  All 4,000 original JSON exchanges match the program/state and decoded action.
- The [report](pong-controls-2026-09-18.md) preserves the complete fixed-seed
  comparison, costs, literal-rule disagreement and limits. No teacher learning
  or final-test evaluation occurred in this round.

## English rebuild and evidence preservation — 2026-09-18

- 104 registered discrete single-agent ALE v5 environments passed an eight-frame
  boot/action smoke check. This is infrastructure coverage, not Jev gameplay coverage.
- All 14 preserved Pong episode traces replayed with matching decision observations,
  rewards and outcomes, including the two interrupted prefixes. No model calls.
- The 183-file evidence archive was extracted into a fresh directory after checking
  both archive and member hashes. Seed 27 replayed successfully from the restored copy.
- New logging captures request/response JSON, exchange IDs, and every controlled
  raw frame's RAM/reward/RGB hash. Original missing API bodies remain unavailable.
- The English source snapshot used by the historical experiments is preserved separately.
- Archive corruption was rejected before extraction. Lint, formatting, local links
  and English-only text checks passed. The test suite now contains 68 passing tests.

The sections below retain the original checks and their dates.

Environment: Linux x86_64, Python 3.12.14, Gymnasium 1.3.0, ale-py 0.11.2,
NumPy 2.5.3. Pong mode=0/difficulty=0, raw frameskip=1, action hold=4,
sticky=0.25, no-op reset up to 30. Dependency versions are in `uv.lock`.

## Verified locally

- `uv run pytest -q`: 29 tests passed; Ruff lint/format and wheel/sdist build passed.
- Real emulator boot and RGB/RAM reads; six expected minimal actions.
- `doctor`: replay from a snapshot with sticky=0.25 reproduces RGB, RAM, observation
  JSON, rewards and termination flags across the same 24-action sequence.
- Deterministic movement probe: action 2 moves paddle y by -10 pixels, action 3 by +9
  pixels over the first four frames from reset. These validate direction, not a constant
  speed law across all states.
- Missing/reappearing objects invalidate velocity; action duration does not double-skip.
- RAM and RGB extraction routes both run without cross-source fallback.
- API mock tests check body/auth shape, bounded retries, malformed probabilities,
  inconsistent scores, credential-free error messages and missing keys.
- Offline learning tests reject final-test feedback, overlapping lineages, target changes
  and corrupted datasets. Exhausted budgets cannot publish a selected program.

## Actual local baseline runs

Both use seed 0 and the same 3,000-decision maximum; one episode each, not a benchmark.

| Policy | Decisions | Raw frames (excluding reset) | Scored / lost | Return | End reason |
| --- | --- | --- | --- | --- | --- |
| Random | 979 | 3,916 | 1 / 21 | -20 | Native termination |
| Track ball center | 3,000 | 12,000 | 9 / 18 | -9 | External cutoff |

The heuristic's recorded MP4 contains 200 simulated seconds; API calls were zero.
The different end reasons and single seed preclude a broad comparative claim.
Artifacts are local under `artifacts/random-baseline/` and `artifacts/heuristic-demo/`.

## Actual branch datasets and synthetic learning smoke test

- Train seeds 0/1: 12 roots, 72 branches; labels -1:10, 0:62, +1:0.
  Four roots have differing labels across actions. Total collection: 18,232 raw frames.
- Development seeds 6/7: 6 roots, 36 branches; labels -1:16, 0:20, +1:0.
  Two roots have differing labels across actions. Total collection: 6,846 raw frames.
- Horizon 240; all branch continuations use the frozen heuristic.
- A full 24-call **mock** optimization round completed; constant predictions produced
  no improvement, so the manual candidate was rejected and the baseline retained.

This corpus lacks positive scoring labels. It validates execution and selection plumbing,
not learning to win Pong. Increase coverage before real quality comparisons.

## Not yet verified

As of the initial 2026-09-17 run, no live service request had been made. This was
superseded by the [2026-09-18 live pilot](pilot-2026-09-18.md): Jev authentication,
prediction and one train-feedback proposal comparison now ran successfully. External
OpenRouter teacher behavior, improved online return, sample efficiency and TD/Q-learning
remain unverified. Actual provider billing was not checked.

Current implementation checks on 2026-09-18: 40 tests passed, including rounded live
response handling, train-evaluation reuse, outcome coverage and teacher example coverage.

After the Choice representation work: 53 tests passed, including one-question action
requests, categorical reward conversion, malformed Choice responses, censored action
labels, mocked direct-action deployment and partial evaluation checkpoints. The
[Choice comparison](choice-ablation-2026-09-18.md) records 66 additional real API calls.

The [online policy pilot](policy-online-2026-09-18.md) adds real model-controlled
episodes, five-point truncation, train-only policy feedback, a paired development gate,
verified interrupted-episode replay and probability-argmax handling of an observed
provider-choice inconsistency. Current validation: 60 passing tests. No full-match
win-rate or RL convergence claim is made.
