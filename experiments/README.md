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

## Proposed question-only clarification

The [no-FIRE candidate](../examples/vertical-policy-no-fire-program.json) keeps
the six default `ALE/Pong-v5` actions (`NOOP`, `FIRE`, `RIGHT`, `LEFT`, `RIGHTFIRE`,
`LEFTFIRE`) visible and selectable. It changes only the guidance and version name:
explain the fire-button combinations and explicitly request RIGHT/up, LEFT/down,
or NOOP/no vertical movement for this policy. There is no action mask, renamed
option, decoder override, or confidence-based fallback.

The [proposal record](no-fire-question-proposal.json) preserves the before/after
programs, hashes and exact text replacement. This was a user-requested manual edit
after viewing development results, not an isolated train-only teacher update.
It is **not evaluated or promoted**, and made no new API calls. All 4,000 decisions
in the fixed-frame comparison already avoided FIRE variants, so this clarification
does not fix an observed FIRE-selection failure or establish better confidence or play.
The original candidate and published experiment artifacts remain unchanged.

## Preserved artifacts

The [fixed-frame controls](../docs/pong-controls-2026-09-18.md) compare four policies
on four new development seeds. This is not another teacher revision: both Jev
programs are unchanged. Aggregate net rewards were -52 (original Jev), -3 (vertical
Jev), -14 (Python 4px), and -15 (Python 2px), with 2,000 frames per episode.
Vertical Jev's literal-rule agreement was 66.85%; the aggregate advantage was
concentrated in one seed. All per-seed outcomes remain in the report.

`pong-controls-v1-2026-09-18.tar.gz` contains all 16 videos, original model exchanges,
frame/decision traces, ledgers and audit records. Its manifest checks every member.
Readable indexes are [plan](pong-controls-v1-plan.json),
[results](pong-controls-v1-results.json), and
[one original input/output showing rule disagreement](pong-controls-v1-decision-15.json).
All 16 episodes and all 4,000 API exchanges passed offline verification. The run
used 4,000 of 4,400 allowed attempts; there were no failures or retries.

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
