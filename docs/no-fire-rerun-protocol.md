# Question-only no-FIRE follow-up

This protocol is frozen before running the
[no-FIRE question](../examples/vertical-policy-no-fire-program.json). The exact
[proposal](../experiments/no-fire-question-proposal.json) changes the guidance
and name, retaining all six action options, their criteria, the observation
format, 4px rule, and probability-argmax decoder. There is no action mask or
confidence-triggered fallback.

Run Jev `jev-1.13.0` on development seeds **36, 37, 46, 47**, in that order, for
**2,000 controlled raw frames / 500 decisions each**, with no point cutoff.
Use the existing RAM protocol: hold=4, sticky=0.25, reset NOOPs=0..30. Record all
four videos, decisions, frame states, JSON exchanges and HTTP ledgers. One shared
cap of **2,200 HTTP attempts** includes retries for at most 2,000 decision calls.
Errors stop execution and remain incomplete; native termination uses the existing
zero-reward absorbing-tail convention. No teacher or extra diagnostic API calls.

The reference is the `jev-vertical` arm in the
[prior fixed-frame results](../experiments/pong-controls-v1-results.json), whose
program hash is `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.
That baseline is reused, not freshly sampled. These development seeds have already
been inspected, and the proposal was authored in that context. This is an
exploratory follow-up, not train-only learning, an independent final test, or a
contemporaneous randomized comparison. API variability can affect differences.

Report every seed's scored/lost points and net-reward change, total cost, 4px rule
agreement on visited states, NOOP/FIRE counts, mean confidence, fractions below
0.3/0.5, and the top-two probability margin. Confidence thresholds are descriptive,
not validated action gates. The old run selected no FIRE variants in 4,000 decisions,
so improved play cannot automatically be attributed to eliminating FIRE actions.
No selection gate or automatic promotion is introduced.

```bash
uv run --env-file "$HOME/.config/typesafe/credentials.env" jev-atari compare-controls \
  --candidate-only --backend jev --model jev-1.13.0 --max-api-calls 2200 \
  --baseline-program examples/vertical-policy-program.json \
  --candidate-program examples/vertical-policy-no-fire-program.json \
  --seeds 36 37 46 47 --frames 2000 --video \
  --out artifacts/pong-no-fire-v3
```

`--candidate-only` executes only the candidate; it does not replay or invent baseline
episodes. The inherited internal arm key is `jev-vertical`; the saved program name
and hash identify this new v3 candidate. The required baseline-program argument is
not evaluated in this mode. The runtime plan saves the actual source revision when
`--source-revision` is provided. Use `scripts/verify_controls.py` to audit the four
new episodes without API calls, then archive the original evidence using Git LFS.
