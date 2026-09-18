# Structured-question comparison — 2026-09-18

The user proposed asking only which action to take. We implemented that direct actor
and a categorical-outcome critic, then compared them with the unchanged Score critic
on the same 24 development states. Both new modes are optional; the default remains
unchanged. Direct action choice used fewer tokens but did not have the lowest sampled
regret in this exploratory comparison.

## What the official documentation says

- [Primitives](https://docs.typesafe.ai/primitives): each question should ask for one
  focused judgment; question IDs are not model-visible. Reference relevant state fields
  explicitly, and batch independent questions that need the same state.
- [Choice](https://docs.typesafe.ai/primitives/choice): use a map of named options for
  selecting among categories or actions. Both option names and descriptions are visible.
  `instructions` can be a string or an object with descriptive fields; these fields are
  user-defined, not reserved API features. Start with simple descriptions.
- [Score](https://docs.typesafe.ai/primitives/score): use descriptive ordered levels for
  one dimension. A mean score cannot distinguish certainty in the middle level from
  uncertainty between the endpoints. For discrete categories with no intermediate outcome,
  the documentation suggests Choice. It does not establish that Choice will improve Pong.

Our interpretation: first loss/no event/first gain have a reward ordering but are also
three distinct events, so Choice is a reasonable alternative to test. Direct action
choice changes the task further, from predicting a future event to choosing an immediate
move. The original Score integration was schema-valid; this tests behavioral effects,
not a claim that the original API shape was invalid.

## Three fixed arms

| Arm | Questions per state | Task | How action is selected |
| --- | ---: | --- | --- |
| Existing Score critic | 6 Score | First point within 240 raw frames for each action | Max P(gain) − P(loss) |
| Outcome Choice critic | 6 Choice | Same first-point target, named loss/no_event/gain | Max P(gain) − P(loss) |
| Direct action Choice | 1 Choice | Which move should the right paddle take now to return the ball? | Returned maximum-probability option |

All arms use the same six ALE action IDs and unchanged RAM object/history observations.
The categorical critic retains the exact state and outcome descriptions; it changes
the primitive, category keys and one sentence about ordered levels. It is a close
ablation, not a byte-identical prompt differing only in the type field.

The direct actor removes the future-outcome task contract and gives one short question,
explicit state paths and a coordinate clarification. It contains no computed intercept,
hand-coded choice rule or future outcome. Its action probabilities are not return
estimates, so we do not assign it an outcome Brier, value MAE or Q-learning interpretation.

The actual direct question uses the following structure, with all six options generated
from the observation (including the FIRE aliases):

```json
{
  "type": "choice",
  "instructions": {
    "question": "Which available action should the RIGHT paddle take now to return the ball? Choose for the next requested action duration using current positions and recent motion.",
    "read": "`observation.objects`, `observation.history` and `observation.candidate_actions`",
    "coordinates": "x increases right; y increases down. Follow the action effect descriptions, not the direction implied by joystick names."
  },
  "criteria": {
    "NOOP": "hold movement of the RIGHT paddle for 4 raw frames (action 0).",
    "FIRE": "hold movement of the RIGHT paddle for 4 raw frames (action 1).",
    "RIGHT": "up movement of the RIGHT paddle for 4 raw frames (action 2).",
    "LEFT": "down movement of the RIGHT paddle for 4 raw frames (action 3).",
    "RIGHTFIRE": "up movement of the RIGHT paddle for 4 raw frames (action 4).",
    "LEFTFIRE": "down movement of the RIGHT paddle for 4 raw frames (action 5)."
  }
}
```

## Measured results

Jev `jev-1.13.0`; reused development seeds 16/17, 12 roots each. Original Score predictions
are reused from the previous pilot; both new question definitions were frozen before
their live evaluation. No result-driven wording changes were made in this comparison.

| Arm | Sampled regret ↓ | Regret on 7 informative roots ↓ | Outcome Brier ↓ | Mean input tokens/state |
| --- | ---: | ---: | ---: | ---: |
| Existing Score critic | 0.291667 | 1.000000 | 0.864183 | 2,828 |
| Outcome Choice critic | **0.166667** | **0.571429** | 0.845649 | 2,966 |
| Direct action Choice | 0.250000 | 0.857143 | Not applicable | **1,498** |
| Fixed tracking heuristic | 0.208333 | — | Not applicable | 0 |

Outcome Choice MAE was 0.434807 versus Score's 0.448889. Its Brier remains worse than
the uniform predictor's 0.666667 and the prior pilot's constant-frequency control
(0.561216). Better action ordering in these samples does not imply calibrated outcomes.

Per-seed sampled regret:

| Seed | Score | Outcome Choice | Direct action |
| --- | ---: | ---: | ---: |
| 16 | 0.333333 | 0.166667 | 0.333333 |
| 17 | 0.250000 | 0.166667 | 0.166667 |

There are only seven roots where actions have different observed outcomes. The direct
actor's total regret fell by just one reward unit across 24 roots. This is not strong
evidence that direct action choice is superior. The categorical critic's apparent
improvement likewise needs replication with independent episodes and repeated inference.

All three arms already batch their questions into one HTTP request per state. The direct
actor cuts mean input tokens by 47.0% versus Score; it does not reduce the request count.
Mean prediction wall times were 0.300 / 0.292 / 0.279 seconds for Score / outcome Choice /
direct action respectively, but the runs were not a controlled latency benchmark.

## Failures, cost and limits

The first categorical run failed client validation on its 17th response. That response
was not retained, so the exact cause cannot be established. A one-request diagnostic of
that state passed validation. We added flushed per-root `predictions.jsonl` checkpoints
to both evaluation CLIs and reran the categorical arm once; the full rerun passed.
Validation was not loosened to make that run pass.

The combined cap was increased from 60 to 70 with a progress update explaining the
rerun. Actual new usage: 66 requests (17 initial categorical + 1 diagnostic + 24 categorical
rerun + 24 direct action), 160,572 input tokens, 11,373 output tokens, 19.755 summed HTTP
seconds. This includes discarded partial-run work and excludes historical Score calls.
The provider bill was not queried.

These are reused development states, not a new test set. Each branch has one paired RNG
realization and a frozen heuristic continuation after the first action. A deployed actor
would instead choose every later action itself. No online return improvement, statistical
significance, temporal credit assignment or learned-policy convergence was established.
We did not pass either new representation through the old question-text acceptance gate.

## Reproduce and use

Use fresh output directories and a previously collected dataset. `--primitive choice`
wraps the original outcome program; `--program` still accepts the base Score-program JSON.
Direct action mode accepts [action-program.json](../examples/action-program.json).

```bash
uv run --env-file "$HOME/.config/typesafe/credentials.env" jev-atari evaluate \
  --dataset artifacts/pilot-v2/development/dataset.json --primitive choice \
  --backend jev --model jev-1.13.0 --max-api-calls 30 --out artifacts/repro-outcome-choice

uv run --env-file "$HOME/.config/typesafe/credentials.env" jev-atari evaluate-actions \
  --dataset artifacts/pilot-v2/development/dataset.json \
  --backend jev --model jev-1.13.0 --max-api-calls 30 --out artifacts/repro-action-choice

uv run --env-file "$HOME/.config/typesafe/credentials.env" jev-atari play \
  --policy jev-action --program examples/action-program.json --model jev-1.13.0 \
  --seed 0 --decisions 100 --max-api-calls 110 --video --out artifacts/action-demo
```

The 100-decision play command is only a short deployment smoke test, not a complete-game
comparison. For a categorical critic actor use `play --policy jev --primitive choice`.
Local comparison artifacts are in `artifacts/choice-v1/`, including the frozen plan,
programs, complete reports, partial-run ledgers and `comparison.json`.

```text
dataset: f4589c8698d814f33dc7249217d9481d1b139267e109365493b9bc27e97b5bfb
outcome-choice program: a6082ca0a250a605b29e145430d2d26c4021afb5fe653192561859bda33e4382
direct-action program: e3c2d203ffcab06c3e5b355ceb3350044a3f13a9ef5f4c53cb1bd2adb307defa
```
