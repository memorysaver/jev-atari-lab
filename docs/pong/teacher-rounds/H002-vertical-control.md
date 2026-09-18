# H002: Vertical-control direct policy

Retrospective entry, recorded 2026-09-18; a separate track from H001.
Source entry: `direct-policy-pilot` in
[question-history.json](../../../experiments/question-history.json).
Full protocol/results: [direct-policy pilot](../../policy-online-2026-09-18.md).

## Teacher and input

- Source: interactive coding assistant; imported proposal, no external teacher API.
- Exact teacher model/version and full conversation transcript: not recorded.
- The original report states that the proposal used training seeds 20/21 and was
  frozen before development seeds 26/27. Exact context isolation cannot be recovered.
- Preserved feedback: `artifacts/policy-online-v1/train-feedback.json` inside the
  [original evidence archive](../../../experiments/atari-evidence-2026-09-18.manifest.json).

## Question change and hypothesis

Parent `pong-action-choice-v1`:
`e3c2d203ffcab06c3e5b355ceb3350044a3f13a9ef5f4c53cb1bd2adb307defa`.

Candidate `pong-vertical-control-v2`:
`2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

Training showed wrong-direction movement and quick losses. The revision explained
bounding-box center y, larger-y/down coordinates, RIGHT/up and LEFT/down semantics,
a 4px deadband and missing-object NOOP. It also separated horizontal ball movement
and player-side labels from vertical control. The hypothesis was that explicit
semantics and a tracking rule would reduce those errors. This changes several
guidance components, so their individual effects were not isolated.

Exact before/after text is in the source JSON; the runnable candidate is
[vertical-policy-program.json](../../../examples/vertical-policy-program.json).

## Evaluation and decision

Jev `jev-1.13.0`. Baseline returns on seeds 26/27 were -5/-5; candidate returns
were 0/+1 after 500 decisions each. Both candidate episodes failed to complete the
predeclared five-point windows. Gate result: `accepted=false`,
`incomplete_point_windows`. Better short-run results did not override that gate.

The study used 1,807 Jev HTTP attempts, 2,881,301 input tokens and 123,809 output
tokens, including failures and diagnostics. A documented decoder correction and
prefix audit occurred during the pilot; see the report before attributing the
entire result to guidance alone. Interactive teacher cost was not recorded.

## Later evidence and lesson

[Fixed-frame controls](../../pong-controls-2026-09-18.md) later evaluated unchanged
v2 and found only 66.85% agreement with its literal rule. The
[long trial](../../pong-match-feasibility-2026-09-18.md) later ended at 7:18,
unfinished. Neither is another teacher proposal or retroactive promotion.

Explicit observation/action semantics are a candidate optimization pattern.
Separate semantic clarification from the strategy change, use fixed-input probes,
and test online return before making a mechanism claim. V2 remains an explicit
experimental reference, not the default selected by the original pilot gate.
