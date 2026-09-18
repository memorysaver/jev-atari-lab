"""Verify saved Pong actions against the real emulator; never construct an API client."""

from pathlib import Path

import imageio.v2 as imageio

from jev_atari.environment import Pong, Protocol
from jev_atari.io import digest, new_directory, read_json, write_json


def inspect_step(episode: Path, decision: int, exchanges: Path | None = None) -> dict:
    """Expose a decision without pretending reconstructed requests are original captures."""
    import json

    from jev_atari.choice import ActionProgram, OutcomeChoiceProgram
    from jev_atari.program import QuestionProgram

    manifest = read_json(episode / "manifest.json")
    if decision < 0:
        raise ValueError("Decision must be nonnegative")
    row = None
    with (episode / "transitions.jsonl").open() as log:
        for line in log:
            candidate = json.loads(line)
            if candidate["decision"] == decision:
                row = candidate
                break
    if row is None:
        raise ValueError("Decision not found in episode")
    result = {"decision": row, "request": None, "response": None, "input_origin": "unavailable"}
    prediction = row.get("prediction") or {}
    if exchanges is None and (episode / "model-exchanges.jsonl").exists():
        exchanges = episode / "model-exchanges.jsonl"
    if exchanges and prediction.get("exchange_id") is not None:
        with exchanges.open() as log:
            for line in log:
                exchange = json.loads(line)
                if exchange["exchange_id"] == prediction["exchange_id"]:
                    if exchange["request"]["state"]["observation"] != row["observation"]:
                        raise ValueError("Exchange file does not match the episode observation")
                    result.update(
                        request=exchange["request"],
                        response=exchange["response"],
                        input_origin="recorded-json-exchange",
                    )
                    return result
        raise ValueError("Model exchange ID not found")
    config = manifest.get("question_program")
    if config and prediction.get("backend") == "jev":
        schema = config.get("schema_version")
        if schema == "action-choice-program-v1":
            program = ActionProgram.from_dict(config)
        elif schema == "outcome-choice-program-v1":
            program = OutcomeChoiceProgram(QuestionProgram.from_dict(config["base"]))
        else:
            program = QuestionProgram.from_dict(config)
        if program.hash != prediction["program_hash"]:
            raise ValueError("Recorded question program hash differs")
        result.update(
            request=program.request(row["observation"], prediction["requested_model"]),
            input_origin="reconstructed-from-recorded-program-and-observation",
        )
    return result


def replay_episode(episode: Path, out: Path, *, video: bool = False) -> dict:
    import json

    manifest = read_json(episode / "manifest.json")
    if manifest["kind"] != "pong-play-v1":
        raise ValueError("Verified replay currently supports Pong object-observation episodes")
    config = manifest["protocol"]
    protocol = Protocol(
        **{k: config[k] for k in ("hold_frames", "sticky", "observation", "noop_max")}
    )
    if protocol.manifest() != config:
        raise ValueError("Replay requires the recorded protocol, dependency versions and ROM hash")
    source_summary = read_json(episode / "summary.json")
    source_frames = (
        iter((episode / "frames.jsonl").read_text().splitlines())
        if (episode / "frames.jsonl").exists()
        else None
    )
    new_directory(out)
    report = {
        "kind": "verified-pong-replay-v1",
        "status": "incomplete",
        "api_attempts": 0,
        "source_episode": str(episode),
        "source_status": source_summary["status"],
        "decisions": 0,
        "raw_frames": 0,
        "reward": 0.0,
        "protocol_hash": config["protocol_hash"],
        "raw_frame_evidence": "verified-against-original"
        if source_frames is not None
        else "reconstructed-from-recorded-actions",
    }
    writer = None
    try:
        with (
            Pong(protocol) as env,
            (episode / "transitions.jsonl").open() as log,
            (out / "frames.jsonl").open("w") as frame_log,
        ):
            observation = env.reset(manifest["seed"])
            report["reset_frames"] = env.reset_frames
            if video:
                writer = imageio.get_writer(
                    out / "replay.mp4",
                    fps=60,
                    codec="libx264",
                    macro_block_size=1,
                    ffmpeg_log_level="error",
                )
            for index, line in enumerate(log):
                row = json.loads(line)
                if row["decision"] != index or digest(row["observation"]) != digest(observation):
                    raise ValueError(f"Replay input differs at decision {index}")
                transition = env.step(
                    row["action"], frames=row["raw_frames"], capture=video, trace=True
                )
                for frame in transition.raw_states:
                    frame_row = {"decision": index, **frame}
                    if source_frames is not None:
                        original = next(source_frames, None)
                        if original is None or digest(json.loads(original)) != digest(frame_row):
                            raise ValueError(f"Replay raw frame differs at decision {index}")
                    frame_log.write(json.dumps(frame_row) + "\n")
                if (
                    digest(transition.observation) != digest(row["next_observation"])
                    or transition.rewards != row["rewards"]
                    or transition.terminated != row["terminated"]
                ):
                    raise ValueError(f"Replay outcome differs at decision {index}")
                # Recorded truncation can be an external point/decision limit.
                if transition.truncated and not row["truncated"]:
                    raise ValueError(f"Unexpected environment truncation at decision {index}")
                if writer:
                    for frame in transition.rgb_frames:
                        writer.append_data(frame)
                observation = transition.observation
                report["decisions"] += 1
                report["raw_frames"] += transition.raw_frames
                report["reward"] += transition.reward
            for key in ("decisions", "raw_frames", "reward"):
                if report[key] != source_summary[key]:
                    raise ValueError(f"Replay totals differ: {key}")
            if source_frames is not None and next(source_frames, None) is not None:
                raise ValueError("Extra raw frames in source")
            report["status"] = "verified"
            report["interpretation"] = (
                "Recorded observations, actions and outcomes reproduced; no model resampling. "
                "An incomplete source remains an incomplete original experiment."
            )
            return report
    finally:
        if writer:
            writer.close()
        write_json(out / "verification.json", report)
