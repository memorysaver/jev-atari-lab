# H001: First-event value question

Retrospective entry, recorded 2026-09-18; not a new execution.
Source entry: `value-question-pilot` in
[question-history.json](../../../experiments/question-history.json).
Full protocol/results: [value pilot](../../pilot-2026-09-18.md).

## Teacher and input

- Source: interactive coding assistant; imported proposal, no external teacher API.
- Exact teacher model/version and full conversation transcript: not recorded.
- The original report states only training evidence was used before the proposal
  was frozen. This historical account is not a newly verified context-isolation audit.
- Training: seeds 10/11, 32 roots. Development: seeds 16/17, 24 roots.
- Preserved feedback: `artifacts/pilot-v2/round/teacher-packet.json` inside the
  [original evidence archive](../../../experiments/atari-evidence-2026-09-18.manifest.json).

## Question change and hypothesis

Parent `pong-baseline-v1`:
`dbaddfa2d5a2a0ea457572b6d5fe4d2d6d8d679a9070121df625a6999dc7c035`.

Candidate `pong-first-event-evidence-v2`:
`e9a2abfaeea964b6d9846ee407a93f296232bed37c7c9df2af1827385293ab08`.

Changed general and per-outcome guidance: distinguish scoreless horizons from
uncertainty, paddle contact from scoring, and the four-frame candidate from the
fixed continuation. Training predictions appeared to overestimate gains. The
hypothesis was that clearer outcome semantics would improve consequence estimates.
Exact text/diff is preserved in the linked JSON, not reconstructed here.

## Evaluation and decision

Jev `jev-1.13.0`; fixed 240-frame first-event labels. Development Brier improved
0.864183 to 0.558266, but value MAE worsened 0.448889 to 0.454869; sampled regret
remained 0.291667. The frozen gate rejected the candidate for `mae_regression` and
retained the parent. There was no online gameplay test or same-input repeat-noise study.

The complete pilot used 82 Jev HTTP attempts, including diagnostics/invalid work,
282,823 input tokens and 7,708 output tokens. Teacher API calls: none; interactive
teacher time/tokens/cost: not recorded. These are study totals, not proposal-only costs.

## Lesson to test

Probability calibration and useful action discrimination can move differently.
A constant training-frequency predictor nearly matched the candidate's Brier score.
Test decision quality and local-control baselines before interpreting prediction
improvement as control improvement. This is a diagnostic finding, not a replicated
optimization pattern.
