"""Check English-only tracked text and local Markdown links."""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
errors = []
for name in filter(None, paths):
    path = root / name
    if path.suffix not in {".md", ".py", ".json", ".toml", ".yml", ".yaml"}:
        continue
    content = path.read_text()
    if re.search(r"[\u3400-\u9fff]", content):
        errors.append(f"Non-English CJK text: {name}")
    if path.suffix == ".md":
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if "://" in target or target.startswith("#"):
                continue
            target = unquote(target.split("#")[0])
            if target and not (path.parent / target).exists():
                errors.append(f"Broken link: {name} -> {target}")
if errors:
    raise SystemExit("\n".join(errors))
print("Tracked text and local Markdown links passed.")
