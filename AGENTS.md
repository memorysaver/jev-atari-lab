# Jev Atari Lab

Read README.md before work and preserve unrelated changes. This repository owns
the implementation and project research. Per the owner's 2026-09-18 direction,
`docs/` is the canonical home for research ideas, hypotheses, evaluation methods,
optimizer patterns and paper planning; historical private notes are provenance.
Start at `docs/README.md`. This project-specific direction overrides the workspace
default of keeping new research in the private idea repository.

- Use Python 3.12 and `uv sync --dev`; run `uv run pytest` and `uv run ruff check .`.
- Keep emulator frames, controller decisions and API wall time separate.
- Keep observation extraction, question programs and observed rewards separate.
- Never train or propose from final-test data. Seeds and all branches of a root
  belong to exactly one split. Model predictions are not observed outcomes.
- Write all tracked documentation, prompts, comments and commit messages in English.
- Distinguish observed results, source-reported claims, proposed methods and
  unconfirmed conclusions. Link research updates from `docs/README.md`; preserve
  negative results and never retroactively rewrite frozen experiment protocols.
- Keep game-specific research under `docs/<game>/`, with an evaluation profile and
  teacher log using `docs/templates/`. New working/published evidence uses
  `artifacts/<game>/` and `experiments/<game>/`; preserve historical paths. Record
  teacher provenance and proposal context before evaluation; never invent missing
  transcripts or treat a manual revision as an isolated automated teacher run.
- Never commit API keys, `.env`, ROM files or emulator snapshots.
- Keep working runtime logs in ignored `artifacts/`. Reviewed experiment archives may
  be published under `experiments/` with checksums and provenance. Store archives and
  videos using Git LFS; verify remote retrieval before claiming preservation.
- No live model calls in tests. Live calls require an explicitly selected backend
  and bounded call budget. Mock results must be labeled and cannot establish learning.
- Pin dependencies and record protocol/model/program versions in artifacts.
