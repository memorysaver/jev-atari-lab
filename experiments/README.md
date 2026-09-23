# Experiment journal

Latest: [teacher-study-v1](pong/teacher-study-v1/README.md) preserves one completed teacher round,
12 replay-verified episodes and the failed second-round teacher call. Neither
candidate was promoted; final tests were not run.

This directory publishes the evidence, including failed attempts and rejected
question changes. Archives and videos use Git LFS. JSON indexes remain readable
on GitHub. Nothing here establishes general Atari mastery or RL convergence.

New evidence is grouped by game, starting at [pong/](pong/README.md). Historical
files remain at their published paths. The [Pong teacher log](../docs/pong/teacher-log.md)
provides a unified view of proposal provenance, exact changes and later outcomes.

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

## Question-only no-FIRE clarification

The [no-FIRE candidate](../examples/vertical-policy-no-fire-program.json) keeps
the six default `ALE/Pong-v5` actions (`NOOP`, `FIRE`, `RIGHT`, `LEFT`, `RIGHTFIRE`,
`LEFTFIRE`) visible and selectable. It changes only the guidance and version name:
explain the fire-button combinations and explicitly request RIGHT/up, LEFT/down,
or NOOP/no vertical movement for this policy. There is no action mask, renamed
option, decoder override, or confidence-based fallback.

The [proposal record](no-fire-question-proposal.json) preserves the before/after
programs, hashes and exact text replacement. This was a user-requested manual edit
after viewing development results, not an isolated train-only teacher update.
The proposal record describes its creation before evaluation and remains unchanged.
The [follow-up report](../docs/pong-no-fire-2026-09-18.md) records the subsequent
evaluation; the candidate is not promoted. All 4,000 decisions
in the fixed-frame comparison already avoided FIRE variants, so this clarification
does not fix an observed FIRE-selection failure or establish better confidence or play.
The original candidate and published experiment artifacts remain unchanged.

The [bounded rerun protocol](../docs/no-fire-rerun-protocol.md) specifies a
candidate-only follow-up with a 2,200-attempt cap and historical baseline reuse.

## Preserved artifacts

The [long Jev feasibility trial](../docs/pong-match-feasibility-2026-09-18.md)
uses fresh development seed 56. Frozen v2 Jev reached 20,000 frames at 7:18
(return -11), with the native match unfinished; local controls completed losses.
All 5,000 model calls succeeded. `pong-match-feasibility-v1-2026-09-18.tar.gz`
contains all four videos, original exchanges, 54,013 controlled frames across
four policies, trajectories and replay audits. See the
[results index](pong-match-feasibility-v1-results.json) and
[trace analysis](pong-match-feasibility-v1-trace-analysis.json).
This is a fixed-policy feasibility trial, not a teacher update or a win-rate estimate.

The [native-match calibration](../docs/pong-match-calibration-2026-09-18.md) adds
nine local training episodes with zero API calls. Random lost all three native
games; tracking and interception each had two losses and one unfinished game at
20,000 frames. The interception candidate did not improve mean capped return.
`pong-match-calibration-v1-2026-09-18.tar.gz` preserves all 105,071 controlled
frames, every decision, the working source patch and offline audits. The
[results index](pong-match-calibration-v1-results.json) reports explicit completion
and win-rate denominators. Calibration videos were not recorded and can be rendered
from replay. This is duration calibration, not Jev learning evidence.

The [no-FIRE follow-up](../docs/pong-no-fire-2026-09-18.md) scored -5 versus the
historical v2 total of -3. Confidence and rule agreement increased without an
aggregate score improvement. Its LFS archive `pong-no-fire-study-2026-09-18.tar.gz`
retains four full short episodes, an interrupted prefix, five videos, original
API/frame logs, a separate continuation plan and audits. Combined use was
2,089 of 2,200 permitted HTTP attempts; all recorded frames replay successfully.
The [results index](pong-no-fire-study-results.json) includes both successful and
failed work. This manual development follow-up is not a promoted teacher round.

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

[Question diagnostics v1](pong/question-diagnostics-v1/README.md) adds 16 replayed Python control episodes,
original-state adherence analysis and 16 videos, with zero new model calls.

[Motion probe v1](pong/motion-probe-v1/README.md) preserves 480 fresh Jev responses on 80 stratified
training states, with negative wording results and no gameplay promotion.

[Compact wording probe](pong/wording-probe-v1/README.md): 480 fresh Jev responses,
negative same-rule wording result and a failed prospective screen. Evidence is
reviewed locally; no remote preservation, gameplay improvement or teacher benefit is claimed.

[Relative-motion controls](pong/relative-motion-controls-v1/README.md): 32 replayed
training episodes and videos with zero model calls. A manually operationalized
teacher hypothesis improves mean capped return but regresses on two seeds. No Jev
improvement or final-test claim; the archive is locally verified only.

[Criteria-edit teacher study](pong/criteria-teacher-v1/README.md): HTTP 402 stopped
the fourth round after 15,093 Jev attempts. Three rounds rejected all six evaluated
proposals. All 27 trajectories and eight teacher outputs are retained and replayed;
no final test ran. Local evidence only; no remote preservation is claimed.

[OpenRouter playback pilot](pong/openrouter-player-pilot-v1/README.md): one successful
access check and 100 successful playback requests, with model identity pinned and
400 frames replayed. Records disclose the supplementary plan-writer failure; the
source/schedule were frozen before calls. No policy-improvement or final-test claim.
