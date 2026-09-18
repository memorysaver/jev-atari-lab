"""Packet-only Codex teacher in an empty Bubblewrap filesystem, without model tools."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from jev_atari.io import digest, write_json

TEACHER_MODEL = "gpt-6-astra"
DISABLED_FEATURES = (
    "shell_tool",
    "unified_exec",
    "code_mode",
    "code_mode_host",
    "multi_agent",
    "apps",
    "plugins",
    "hooks",
    "memories",
    "shell_snapshot",
    "browser_use",
    "browser_use_external",
    "computer_use",
    "image_generation",
    "view_image",
    "in_app_browser",
    "workspace_dependencies",
    "skill_search",
    "sleep_tool",
    "goals",
)
INSTRUCTIONS = (
    "You are the experimental Pong question-policy teacher. Use only the supplied JSON packet. "
    "Do not use tools, files, web, other agents or prior conversation. Return one JSON proposal "
    "matching the schema. Improve the current policy by changing guidance only. Keep <=2000 "
    "characters, and change one principal mechanism when practical. Explain a concise hypothesis, "
    "predicted action changes and regressions, not a claim of proven improvement. "
    "Cite only provided example IDs; without examples use an empty evidence_ids list. "
    "No code changes, new sensors, extra questions or action masking."
)
PROPOSAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **{
            key: {"type": "string"}
            for key in (
                "name",
                "guidance",
                "hypothesis",
                "operator",
                "predicted_changes",
                "regression_risks",
            )
        },
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "name",
        "guidance",
        "hypothesis",
        "operator",
        "evidence_ids",
        "predicted_changes",
        "regression_risks",
    ],
}


def bubblewrap(binary: Path, private_home: Path, work: Path):
    """Only system runtime, dedicated auth/runtime and output mounts are visible."""
    command = [
        "bwrap",
        "--die-with-parent",
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--new-session",
        "--clearenv",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--symlink",
        "usr/bin",
        "/bin",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/etc",
        "--dir",
        "/home/teacher",
        "--ro-bind",
        str(binary),
        "/teacher-codex",
        "--bind",
        str(private_home),
        "/codex",
        "--bind",
        str(work),
        "/work",
        "--setenv",
        "HOME",
        "/home/teacher",
        "--setenv",
        "CODEX_HOME",
        "/codex",
        "--setenv",
        "PATH",
        "/usr/local/bin:/usr/bin",
        "--setenv",
        "TERM",
        "dumb",
        "--setenv",
        "LANG",
        "C.UTF-8",
        "--chdir",
        "/work",
    ]
    for name in ("resolv.conf", "hosts", "nsswitch.conf", "ssl", "ca-certificates"):
        source = Path("/etc") / name
        if source.exists():
            command += ["--ro-bind", str(source.resolve()), f"/etc/{name}"]
    return command


def teacher_config():
    return (
        'model = "gpt-6-astra"\nmodel_reasoning_effort = "high"\n'
        'approval_policy = "never"\nsandbox_mode = "read-only"\n'
        'web_search = "disabled"\nproject_doc_max_bytes = 0\n'
        'cli_auth_credentials_store = "file"\n'
        f"developer_instructions = {json.dumps(INSTRUCTIONS)}\n"
        "[features]\n" + "".join(f"{name} = false\n" for name in DISABLED_FEATURES)
    )


def isolation_check(binary: Path):
    with tempfile.TemporaryDirectory(prefix="jev-teacher-isolation-") as tmp:
        root = Path(tmp)
        private, work = root / "private", root / "work"
        private.mkdir()
        work.mkdir()
        private.joinpath("config.toml").write_text(teacher_config())
        command = bubblewrap(binary, private, work)
        check = subprocess.run(
            command
            + [
                "/usr/bin/sh",
                "-c",
                "test ! -e /home/memorysaver && test ! -e /root && "
                "test ! -e /work/AGENTS.md && test ! -e /codex/auth.json && "
                "/teacher-codex --version",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return {
            "kind": "teacher-isolation-check-v1",
            "filesystem_check": "passed",
            "codex_version": check.stdout.strip(),
            "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "config_sha256": hashlib.sha256(teacher_config().encode()).hexdigest(),
            "disabled_features": list(DISABLED_FEATURES),
            "repository_mounted": False,
            "host_home_mounted": False,
            "network": "provider access; web tool disabled",
            "api_calls": 0,
        }


def invoke_teacher(packet, out, budget, *, binary: Path, auth_home: Path, repair=False):
    serialized = json.dumps(packet, allow_nan=False)
    if len(serialized.encode()) > 200000:
        raise ValueError("Teacher packet exceeds 200 KB")
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "packet.json", packet)
    write_json(out / "response-schema.json", PROPOSAL_SCHEMA)
    out.joinpath("instructions.txt").write_text(INSTRUCTIONS + "\n")
    metadata = {
        "requested_model": TEACHER_MODEL,
        "requested_reasoning_effort": "high",
        "packet_hash": digest(packet),
        "status": "prepared",
        "timeout_seconds": 900,
        "isolation": isolation_check(binary),
        "invocation_mode": "isolated Codex exec",
        "provider_response_model": None,
        "provider_response_model_note": "CLI final JSON is not an API model attestation.",
    }
    write_json(out / "execution.json", metadata)
    with tempfile.TemporaryDirectory(prefix="jev-teacher-runtime-") as tmp:
        root = Path(tmp)
        private, work = root / "private", root / "work"
        private.mkdir(mode=0o700)
        work.mkdir(mode=0o700)
        # Credentials never enter the experiment output or request packet.
        shutil.copyfile(auth_home / "auth.json", private / "auth.json")
        os.chmod(private / "auth.json", 0o600)
        if (auth_home / "models_cache.json").exists():
            shutil.copyfile(auth_home / "models_cache.json", private / "models_cache.json")
        private.joinpath("config.toml").write_text(teacher_config())
        write_json(work / "schema.json", PROPOSAL_SCHEMA)
        preview = subprocess.run(
            bubblewrap(binary, private, work)
            + ["/teacher-codex", "debug", "prompt-input", "PACKET_SUPPLIED_ON_STDIN"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        write_json(
            out / "context-preview.json",
            {
                "note": "Offline context preview; the invocation receives packet.json on stdin.",
                "messages": json.loads(preview.stdout),
            },
        )
        command = bubblewrap(binary, private, work) + [
            "/teacher-codex",
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--model",
            TEACHER_MODEL,
            "-c",
            'model_reasoning_effort="high"',
            "--output-schema",
            "/work/schema.json",
            "--output-last-message",
            "/work/answer.json",
            "--json",
            "-",
        ]
        budget.reserve("teacher_repair" if repair else "teacher")
        start = time.time()
        metadata.update(status="running", started_at=start)
        write_json(out / "execution.json", metadata)
        try:
            process = subprocess.run(
                command, input=serialized, capture_output=True, text=True, timeout=900
            )
            metadata["exit_code"] = process.returncode
            # Publish only final messages and usage, not private runtime/auth/debug logs.
            events = []
            for line in process.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "turn.completed":
                    events.append({"type": "turn.completed", "usage": event.get("usage")})
                elif event.get("type") == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        events.append({"type": "agent_message", "text": item.get("text")})
                    elif item.get("type") not in {"reasoning"}:
                        metadata.setdefault("unexpected_item_types", []).append(item.get("type"))
            write_json(out / "events.json", events)
            if metadata.get("unexpected_item_types"):
                raise ValueError("Teacher attempted non-message activity")
            if process.returncode or not (work / "answer.json").exists():
                # Keep diagnostics privately; never echo provider/credential text in public records.
                diagnostic = Path(tempfile.mkdtemp(prefix="jev-teacher-error-"))
                os.chmod(diagnostic, 0o700)
                (diagnostic / "stderr.txt").write_text(process.stderr)
                raise RuntimeError(
                    "Teacher failed; private diagnostic retained in temporary directory"
                )
            answer = work.joinpath("answer.json").read_text()
            if len(answer.encode()) > 16000:
                raise ValueError("Teacher response exceeds 16 KB")
            value = json.loads(answer)
            write_json(out / "proposal.json", value)
            metadata["status"] = "complete"
            return value
        except Exception as exc:
            metadata.update(status="incomplete", error_type=type(exc).__name__)
            raise
        finally:
            metadata["wall_seconds"] = time.time() - start
            write_json(out / "execution.json", metadata)
