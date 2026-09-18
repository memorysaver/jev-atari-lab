# Replay, model exchanges, and question history

## Two clocks

A raw frame is one emulator step with frameskip=1. A decision normally requests one
action for four raw frames. Jev is called once per decision, with recent observation
history; it is not called on every intermediate raw frame. API waits pause simulation.

New runs preserve these distinct records:

| File | Contents |
| --- | --- |
| `manifest.json` | Environment/ROM/dependency versions, seed, protocol, program |
| `model-exchanges.jsonl` | Sent JSON request including questions/state, successful JSON response, HTTP status/timing and exchange ID; no auth headers |
| `transitions.jsonl` | Decision observation, validated prediction, action, resulting reward and next observation/RAM |
| `frames.jsonl` | Each controlled raw frame's RAM, RGB SHA-256, requested action and reward |
| `summary.json` | Actual frames, decisions, return and end reason, including incomplete runs |
| `replay.mp4` | Optional 60-fps simulation-time video |

Reset no-ops are accounted for separately and reproducible from the recorded seed.
They are not Jev decisions. Sticky actions can differ from the requested joystick
action; do not label the request as a directly observed executed action.

For `policy-suite`, model exchanges are at the suite root and IDs span episodes.
For `compare-controls`, exchanges are inside each episode directory, with IDs
unique across the entire comparison's shared budget. Each
prediction's `exchange_id` links to the API record. Retries also get records and
consume budget. Unsuccessful HTTP bodies are omitted because they may echo secrets;
status and request remain. Successful bodies are captured as parsed JSON, with the
credential value redacted if echoed. This is not a byte-for-byte wire capture.

## Every teacher round

The value-learning command saves:

- `input-program.json`: the parent question program.
- `teacher-packet.json`: exact train-only feedback given to the proposer.
- `teacher-exchanges.jsonl`: API request/response when the optional teacher API is used.
- `proposals.json`: the returned or imported proposal, including rejected candidates.
- `question-changes.json`: before/after values for each changed field, parent/candidate hashes.
- `development-baseline.json` and `development-candidate-N.json`: measured comparisons.
- `selection.json`, `selected-program.json`, `status.json`: acceptance, rejection reasons and completion.
- Model and teacher ledgers: costs including failures and retries.

Imported proposals must document their author and generation process separately;
they do not imply that the teacher API ran. We preserve proposals and explicit
hypotheses, not an invented transcript of a teacher's private reasoning.
Current online direct-policy feedback/selection is separate from this offline learner;
there is no hidden automatic multi-round online RL scheduler.

## Restore and verify the historical Pong experiments

```bash
git lfs pull
uv run python scripts/restore_experiments.py --out restored
uv run jev-atari replay \
  --episode restored/artifacts/policy-online-v1/development-candidate-resumed/seed-27 \
  --video --out artifacts/replayed-seed-27
```

Restore checks the archive and every member's SHA-256 before extraction, rejects
unsafe paths and refuses an existing destination. Replay requires matching protocol,
ROM hash and dependency versions. It checks every decision input, next observation,
reward and termination, and checks raw-frame hashes where the original contains them.
No API client or key is used. A successful replay of an incomplete episode verifies
the recorded prefix, not completion of the original experiment.

The historical archive predates exchange logging. It preserves the original
normalized predictions and any provider fields that were retained, but **full original
API bodies are unavailable**. Requests can be reconstructed from the saved observation,
question program and matching source; they must be labeled reconstructed.
Raw frames generated now are similarly labeled reconstructed and saved separately.
Original files remain byte-for-byte intact in the archive.

To inspect the input, saved prediction and outcome of one historical decision:

```bash
uv run jev-atari inspect-step \
  --episode restored/artifacts/policy-online-v1/development-candidate-resumed/seed-27 \
  --decision 111
```

New runs read the captured exchange; suites can pass `--exchanges PATH` to their
root log. Old runs reconstruct the request and label its origin explicitly.
A readable saved example is [pong-decision-111.json](../experiments/pong-decision-111.json).

Pong snapshot branches were originally in-process, not serialized. Frozen branch
datasets preserve their observations, measured outcomes and collection protocol;
they support offline re-evaluation. They do not contain standalone restorable emulator
snapshots. Re-running collection is a distinct experiment and may require replaying the
original collector with matching versions. The source snapshot is archived for that purpose.

The generic raw-RAM runner records enough data for future replay tooling, but the
`replay` verification command currently supports the Pong object track only.

## LFS preservation

Videos (`*.mp4`) and reviewed experiment archives (`experiments/*.tar.gz`) are LFS
objects. Git stores their pointers; `git lfs pull` retrieves actual bytes. Checksums
and readable round summaries remain ordinary text in Git. Working `artifacts/`
remain ignored, and publishing requires review for credentials, ROMs and unrelated data.

See [GitHub's LFS documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage).
