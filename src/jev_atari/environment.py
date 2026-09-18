"""Synchronous ALE control with complete in-process replay snapshots."""

import hashlib
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from importlib.metadata import version

import ale_py
import ale_py.roms
import gymnasium as gym
import numpy as np

from jev_atari.io import digest
from jev_atari.observation import (
    ACTION_NAMES,
    EXTRACTOR,
    Tracker,
    make_observation,
    ram_boxes,
    vision_boxes,
)


@dataclass(frozen=True)
class Protocol:
    hold_frames: int = 4
    sticky: float = 0.25
    observation: str = "ram"
    noop_max: int = 30

    def __post_init__(self) -> None:
        if not 1 <= self.hold_frames <= 16:
            raise ValueError("hold_frames must be between 1 and 16")
        if not 0 <= self.sticky <= 1 or self.observation not in {"ram", "vision"}:
            raise ValueError("invalid sticky probability or observation source")
        if not 0 <= self.noop_max <= 60:
            raise ValueError("noop_max must be between 0 and 60")

    def manifest(self) -> dict:
        data = {
            **asdict(self),
            "game": "ALE/Pong-v5",
            "mode": 0,
            "difficulty": 0,
            "frameskip": 1,
            "full_action_space": False,
            "extractor": EXTRACTOR,
            "rom_sha256": hashlib.sha256(ale_py.roms.get_rom_path("pong").read_bytes()).hexdigest(),
            "versions": {p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
        }
        return {**data, "protocol_hash": digest(data)}


@dataclass
class Transition:
    observation: dict
    rewards: list[float]
    terminated: bool
    truncated: bool
    rgb_frames: list[np.ndarray]
    raw_states: list[dict] = field(default_factory=list)

    @property
    def reward(self) -> float:
        return sum(self.rewards)

    @property
    def raw_frames(self) -> int:
        return len(self.rewards)


class Pong:
    def __init__(self, protocol: Protocol | None = None):
        protocol = protocol or Protocol()
        self.protocol = protocol
        gym.register_envs(ale_py)
        self.env = gym.make(
            "ALE/Pong-v5",
            frameskip=1,
            repeat_action_probability=protocol.sticky,
            mode=0,
            difficulty=0,
            full_action_space=False,
            render_mode="rgb_array",
            max_episode_steps=-1,
        )
        if self.env.unwrapped.get_action_meanings() != ACTION_NAMES:
            self.env.close()
            raise RuntimeError("Pong action set differs from the validated protocol")
        self.initialized = False

    def reset(self, seed: int) -> dict:
        self.env.reset(seed=seed)
        self.raw_frames = 0
        self.tracker = Tracker()
        self.ended = False
        self.initialized = True
        noops = int(np.random.default_rng(seed).integers(0, self.protocol.noop_max + 1))
        for _ in range(noops):
            _, reward, terminated, truncated, _ = self.env.step(0)
            self.raw_frames += 1
            if reward or terminated or truncated:
                raise RuntimeError("Unexpected reward/termination during reset NOOPs")
        self.reset_frames = self.raw_frames
        self._refresh(None, [])
        return deepcopy(self.observation)

    def _refresh(self, action: int | None, events: list[str]) -> None:
        self.rgb = self.env.unwrapped.ale.getScreenRGB().copy()
        self.ram = self.env.unwrapped.ale.getRAM().copy()
        boxes = (
            ram_boxes(self.ram) if self.protocol.observation == "ram" else vision_boxes(self.rgb)
        )
        self.observation = make_observation(
            self.tracker,
            boxes,
            self.raw_frames,
            source=self.protocol.observation,
            hold=self.protocol.hold_frames,
            sticky=self.protocol.sticky,
            last_action=action,
            events=events,
        )

    def step(
        self,
        action: int,
        *,
        frames: int | None = None,
        stop_on_point: bool = False,
        capture: bool = False,
        trace: bool = False,
    ) -> Transition:
        if not self.initialized or self.ended:
            raise RuntimeError("Reset is required before stepping")
        if type(action) is not int or action not in range(6):
            raise ValueError("action must be an integer from 0 to 5")
        count = self.protocol.hold_frames if frames is None else frames
        if not 1 <= count <= self.protocol.hold_frames:
            raise ValueError("frames must be within the configured action hold")
        rewards, video, events, raw_states = [], [], [], []
        terminated = truncated = False
        for _ in range(count):
            _, reward, terminated, truncated, _ = self.env.step(action)
            self.raw_frames += 1
            rewards.append(float(reward))
            if capture:
                video.append(self.env.unwrapped.ale.getScreenRGB().copy())
            if trace:
                raw_states.append(
                    {
                        "raw_frame": self.raw_frames,
                        "requested_action_id": action,
                        "ram_bytes": self.env.unwrapped.ale.getRAM().tolist(),
                        "rgb_sha256": hashlib.sha256(
                            self.env.unwrapped.ale.getScreenRGB().tobytes()
                        ).hexdigest(),
                        "reward": float(reward),
                        "terminated": terminated,
                        "truncated": truncated,
                    }
                )
            if reward:
                events.append("point_scored" if reward > 0 else "point_lost")
                self.tracker.clear_ball_history()
            if terminated or truncated or (stop_on_point and reward):
                break
        self.ended = terminated or truncated
        self._refresh(action, events)
        return Transition(
            deepcopy(self.observation), rewards, terminated, truncated, video, raw_states
        )

    def snapshot(self) -> dict:
        if not self.initialized:
            raise RuntimeError("Reset before snapshot")
        return {
            "ale": self.env.unwrapped.clone_state(include_rng=True),
            "env_rng": deepcopy(self.env.unwrapped.np_random.bit_generator.state),
            "tracker": deepcopy(self.tracker),
            "observation": deepcopy(self.observation),
            "raw_frames": self.raw_frames,
            "reset_frames": self.reset_frames,
            "rgb": self.rgb.copy(),
            "ram": self.ram.copy(),
            "ended": self.ended,
        }

    def restore(self, snapshot: dict) -> dict:
        if not self.initialized:
            raise RuntimeError("Reset before restore")
        self.env.unwrapped.restore_state(snapshot["ale"])
        self.env.unwrapped.np_random.bit_generator.state = deepcopy(snapshot["env_rng"])
        for name in ("tracker", "observation", "raw_frames", "reset_frames", "rgb", "ram", "ended"):
            setattr(self, name, deepcopy(snapshot[name]))
        # ALE may retain screen/RAM query caches until the next act(). Use saved observations.
        return deepcopy(self.observation)

    def close(self) -> None:
        self.env.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
