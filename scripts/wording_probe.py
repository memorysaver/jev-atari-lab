"""Prepare, execute and independently audit the frozen compact-wording diagnostic."""

import argparse
import json
from pathlib import Path

from motion_probe import run, verify

from jev_atari.io import read_json, write_json
from jev_atari.wording_probe import KIND, prepare, screen, validate_pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "run", "verify"])
    for name in ["source", "pack", "run"]:
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--backend", choices=["jev"])
    args = parser.parse_args()
    required = {
        "prepare": ["source"],
        "run": ["pack", "backend"],
        "verify": ["source", "pack", "run"],
    }
    for name in required[args.operation]:
        if getattr(args, name) is None:
            parser.error(f"{args.operation} requires --{name}")
    if args.operation == "prepare":
        prepare(args.source, args.out, args.repository)
    elif args.operation == "run":
        validate_pack(args.pack, args.repository)
        report = run(args.pack, args.out, args.backend, kind=KIND)
        write_json(args.out / "screen.json", screen(report))
    else:
        result = verify(
            args.pack,
            args.run,
            args.out,
            args.source,
            args.repository,
            kind=KIND,
            prepare_fn=prepare,
        )
        evaluation = screen(read_json(args.run / "results.json"))
        if (args.run / "screen.json").exists():
            assert evaluation == read_json(args.run / "screen.json")
        elif result["run_status"] == "complete":
            raise ValueError("Complete run lacks its prospective screen")
        write_json(args.out / "screen.json", evaluation)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
