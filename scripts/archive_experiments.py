"""Build a reviewed, checksummed data archive; never include credentials or ROMs."""

import argparse
import gzip
import hashlib
import json
import os
import re
import tarfile
from pathlib import Path


def archive(source: Path, output: Path) -> dict:
    if output.exists() or output.with_suffix("").with_suffix(".manifest.json").exists():
        raise ValueError("Archive or manifest already exists")
    if not source.is_dir():
        raise ValueError("Source directory does not exist")
    files = []
    secrets = [os.environ.get(k, "") for k in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY")]
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed in experiment archives")
        if not path.is_file():
            continue
        if path.suffix not in {".json", ".jsonl", ".png", ".mp4", ".md", ".txt"}:
            raise ValueError(f"Unreviewed file type: {path.name}")
        data = path.read_bytes()
        if any(secret and secret.encode() in data for secret in secrets):
            raise ValueError("Credential found; refusing to archive")
        if path.suffix in {".json", ".jsonl", ".md", ".txt"}:
            text = data.decode()
            if re.search(r"\bBearer\s+[A-Za-z0-9_.-]+|\b(?:sk-|ts_)[A-Za-z0-9_-]{20,}", text):
                raise ValueError("Possible credential found; refusing to archive")
        files.append(
            {
                "path": str(Path(source.name) / path.relative_to(source)),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            for row in files:
                path = source / Path(row["path"]).relative_to(source.name)
                info = tar.gettarinfo(path, arcname=row["path"])
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                with path.open("rb") as content:
                    tar.addfile(info, content)
    manifest = {
        "kind": "experiment-archive-v1",
        "archive": output.name,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "file_count": len(files),
        "uncompressed_bytes": sum(f["bytes"] for f in files),
        "files": files,
    }
    output.with_suffix("").with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return {k: v for k, v in manifest.items() if k != "files"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(archive(args.source, args.out), indent=2))
