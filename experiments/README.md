# Experiment journal

This directory publishes the evidence, including failed attempts and rejected
question changes. Archives and videos use Git LFS. JSON indexes remain readable
on GitHub. Nothing here establishes general Atari mastery or RL convergence.

## Read the actual decisions and teacher changes

- [One Pong decision](pong-decision-111.json): decision 111 from seed 27. The request
  is explicitly reconstructed from its saved program and observation; the prediction
  and outcome are original recorded data. The full provider body was not retained.
- [Question history](question-history.json): complete before/after question programs,
  changed fields, teacher-feedback locations, validation metrics and acceptance decisions.
- [Environment inventory](environment-check-2026-09-18.json): 104 registered games,
  all passing eight-frame local smoke checks; zero model calls.
- [Replay verification](replay-verification-2026-09-18.json): all 14 historical Pong
  episode traces reproduce their recorded observations and outcomes, including
  incomplete prefixes. No model requests are needed to replay recorded actions.

## Historical question revisions

| Revision | What the teacher changed | Evaluation | Decision |
| --- | --- | --- | --- |
| Value question: baseline to first-event evidence | Clarified finite horizon, fixed continuation, and no-point as a real outcome; discouraged confusing contact with scoring | Brier 0.8642 to 0.5583; MAE 0.4489 to 0.4549; sampled regret unchanged | Rejected: MAE regression |
| Direct policy: baseline to vertical control | Explicit center-y comparison, 4px tolerance, actual RIGHT/LEFT movement effects and missing-object behavior | Baseline lost 5 points on each dev seed; candidate ran 500 decisions each, total 1 scored / 0 lost | Not promoted: five-point windows incomplete |

Both proposals were authored by the interactive coding assistant using training
feedback. They are not outputs of an external teacher API run. The saved provenance
and explicit hypotheses are included; an exact teacher API transcript does not exist.
These are separate pilot tracks, not two consecutive rounds of one learning curve.

Full reports: [value pilot](../docs/pilot-2026-09-18.md),
[question-form comparison](../docs/choice-ablation-2026-09-18.md),
[online policy pilot](../docs/policy-online-2026-09-18.md).

## Preserved artifacts

`atari-evidence-2026-09-18.tar.gz` contains the entire reviewed working artifact tree
at publication, including original datasets, logs, predictions, programs, feedback,
selection decisions, failure ledgers, videos, still frames and replay verification.
`atari-evidence-2026-09-18.manifest.json` lists every file's size and SHA-256.
Original experiment files are preserved byte-for-byte. New reconstruction records
live under `preservation-replay/` and `preservation-all/`, clearly separated from originals.

`original-source-2026-09-18.tar.gz` preserves the English source code, tests, dependency
lock, example programs and attribution used before the repository history rewrite.
Its manifest records the original source commit. It contains no Git history, old
README, credentials, ROMs or private research repository.

```bash
git lfs pull
uv run python scripts/restore_experiments.py --out restored
uv run jev-atari replay \
  --episode restored/artifacts/policy-online-v1/development-candidate-resumed/seed-27 \
  --video --out artifacts/replay-seed-27
```

Offline branch datasets are preserved but are not serialized emulator snapshots.
See [replay boundaries and new logging contracts](../docs/replay.md).

## Publishing future rounds

Keep working artifacts outside Git until reviewed. Use the archive tool with the
credential environment loaded so it can reject known token values without printing
them. Add an English journal entry explaining inputs, teacher changes, results,
rejections, costs and limitations. Publish checksums alongside the LFS object.

```bash
uv run --env-file "$HOME/.config/typesafe/credentials.env" \
  python scripts/archive_experiments.py \
  --source artifacts/round-02 --out experiments/round-02.tar.gz
```

Do not overwrite a published archive or quietly discard failed rounds. Preserve the
question program and observation contract that generated each result.
