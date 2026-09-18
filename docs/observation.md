# Observation contract v1

The actor receives `atari-object-observation-v1`. Both the local baselines and Jev
consume the same dictionary. The raw emulator state, split, episode seed and root
identifiers are excluded from this input.

| Field | Meaning |
| --- | --- |
| `coordinates` | Full 160×210 RGB canvas, top-left origin, x right and y down; boxes are x/y/width/height |
| `observation_source` | `ram` or `vision`; no RAM fallback in vision mode |
| `objects` | Player, opponent and ball; presence, box, velocity validity and last-seen age |
| `history` | Up to four decision observations, including current; offsets in real emulator frames |
| `control` | Requested hold duration, sticky probability, last requested action; actual executed action unknown |
| `candidate_actions` | All six ALE action IDs, meanings, verified movement alias and hold duration |
| `events_observed` | Only already-observed scoring events from the latest action chunk |

Object speeds are backward coordinate differences divided by actual elapsed raw
frames. They are not the emulator's hidden physical velocity. A wall reflection
within the interval can make an average velocity misleading. The history remains
available for the evaluator. Missing objects use null boxes and velocities, not zeros.
Scoring breaks ball identity and invalidates the preceding ball track.

RAM extraction uses a minimal, attributed OCAtari-derived mapping. Vision extraction
uses Pong-specific palette colors inside rows 34–193; it is not a general detector.
There is no learned perception or claim that RAM and vision observations carry the
same information. The RAM route is explicitly privileged.

The API's `state` contains this dictionary under `observation`, plus a fixed
`task_contract`: player side, first-point horizon, outcome definition and the exact
heuristic continuation rule. Questions identify actions inside their instructions;
question keys alone carry no inference semantics in the TypeSafe API.

No precomputed intercept, recommended action, future branch trace, seed, root ID,
or outcome label is included. Scores returned by Jev are predictions, recorded
separately from ALE rewards. Geometry features/world-model predictions can later
be added as explicit, separately versioned ablations.

The replay snapshot is a different object: it contains ALE state including RNG,
Gymnasium RNG, cached RAM/RGB, tracker history, raw-frame counters and termination
state. It is currently in-memory only. After restore, the saved observation is used
because ALE query caches may remain stale until `act()` runs again. `doctor` compares
subsequent RGB/RAM, rewards, termination flags and JSON after identical action sequences.

Synchronous inference never advances the emulator. A video is rendered at simulated
60 FPS; API response time only affects wall-clock experiment duration. An asynchronous
real-time controller would require a separate protocol.
