"""Verify and extract the published experiment archive into a new directory."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


def restore(manifest_path: Path, out: Path) -> dict:
    if out.exists():
        raise ValueError("Destination already exists; choose a new directory")
    manifest = json.loads(manifest_path.read_text())
    archive = manifest_path.parent / manifest["archive"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Archive checksum mismatch; run git lfs pull if this is a pointer file")
    expected = {row["path"]: row for row in manifest["files"]}
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != len(expected) or {m.name for m in members} != set(expected):
            raise ValueError("Archive members differ from manifest")
        for member in members:
            path = Path(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe archive member")
            if member.size != expected[member.name]["bytes"]:
                raise ValueError("Archive member size differs")
            data = tar.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != expected[member.name]["sha256"]:
                raise ValueError("Archive member checksum differs")
        out.mkdir(parents=True, exist_ok=False)
        tar.extractall(out, filter="data")
    return {"status": "verified", "files": len(expected), "destination": str(out)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "experiments/atari-evidence-2026-09-18.manifest.json",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.manifest, args.out), indent=2))
