# Jev Atari Lab

Read README.md before work and preserve unrelated changes. This repository owns the
implementation; upstream research lives in the private idea repository.

- Use Python 3.12 and `uv sync --dev`; run `uv run pytest` and `uv run ruff check .`.
- Keep emulator frames, controller decisions and API wall time separate.
- Keep observation extraction, question programs and observed rewards separate.
- Never train or propose from final-test data. Seeds and all branches of a root
  belong to exactly one split. Model predictions are not observed outcomes.
- Write all tracked documentation, prompts, comments and commit messages in English.
- Never commit API keys, `.env`, ROM files or emulator snapshots.
- Keep working runtime logs in ignored `artifacts/`. Reviewed experiment archives may
  be published under `experiments/` with checksums and provenance. Store archives and
  videos using Git LFS; verify remote retrieval before claiming preservation.
- No live model calls in tests. Live calls require an explicitly selected backend
  and bounded call budget. Mock results must be labeled and cannot establish learning.
- Pin dependencies and record protocol/model/program versions in artifacts.
