"""First-maze Ms. Pac-Man observations and explicit local controls.

Coordinate/color facts adapt OCAtari; see THIRD_PARTY_NOTICES.md.
Graph extraction and navigation are project implementations, not optimal policies.
"""

import heapq
from collections import deque

import numpy as np

SCHEMA = "mspacman-first-maze-v1"
NAMES = ("NOOP", "UP", "RIGHT", "LEFT", "DOWN", "UPRIGHT", "UPLEFT", "DOWNRIGHT", "DOWNLEFT")
DIRECTIONS = {"UP": (0, -1), "RIGHT": (1, 0), "LEFT": (-1, 0), "DOWN": (0, 1)}
PINK = (228, 111, 111)
PLAYER = (210, 164, 74)
GHOSTS = ((180, 122, 48), (84, 184, 153), (198, 89, 179), (200, 72, 72))
BLUE = (66, 114, 194)
XS = (10, 18, 26, 34, 42, 50, 58, 66, 74, 80, 86, 94, 102, 110, 118, 126, 134, 142, 150)


def components(mask):
    seen = set()
    result = []
    height, width = mask.shape
    for yy, xx in zip(*np.where(mask), strict=True):
        point = int(xx), int(yy)
        if point in seen:
            continue
        todo = deque([point])
        seen.add(point)
        component = []
        while todo:
            x, y = todo.popleft()
            component.append((x, y))
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                p = nx, ny
                if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and p not in seen:
                    seen.add(p)
                    todo.append(p)
        result.append(component)
    return result


def color_support(rgb, box, colors):
    x, y, w, h = box
    crop = rgb[max(0, y) : min(170, y + h), max(0, x) : min(160, x + w)]
    return int(sum(np.all(crop == color, axis=2).sum() for color in colors))


class Maze:
    """Static first-maze geometry, inferred from the initial rendered walls."""

    def __init__(self, rgb):
        pink = np.all(rgb == PINK, axis=2)
        wall = np.zeros(pink.shape, dtype=bool)
        self.pellet_sites = []
        for comp in components(pink):
            xx, yy = zip(*comp, strict=True)
            box = [min(xx), min(yy), max(xx) - min(xx) + 1, max(yy) - min(yy) + 1]
            if len(comp) > 32:
                for x, y in comp:
                    wall[y, x] = True
            elif box[1] < 170 and box[2:] == [4, 2]:
                self.pellet_sites.append(box)
        self.pellet_sites.sort(key=lambda b: (b[1], b[0]))
        self.nodes = []
        for y in range(8, 165, 12):
            for x in XS:
                if 70 <= x <= 90 and 62 <= y <= 96:
                    continue  # The ghost house is not a player corridor.
                if not wall[y - 3 : y + 4, x - 2 : x + 3].any():
                    self.nodes.append((x, y))
        self.adj = {p: {} for p in self.nodes}
        self.edges = []
        for i, (x, y) in enumerate(self.nodes):
            for xx, yy in self.nodes[:i]:
                vertical = x == xx and abs(y - yy) == 12
                horizontal = y == yy and abs(x - xx) <= 12
                if not (vertical or horizontal):
                    continue
                if wall[min(y, yy) - 3 : max(y, yy) + 4, min(x, xx) - 2 : max(x, xx) + 3].any():
                    continue
                self.edges.append(((x, y), (xx, yy)))
                dx, dy = int(np.sign(xx - x)), int(np.sign(yy - y))
                old = (x, y)
                while old != (xx, yy):
                    new = old[0] + dx, old[1] + dy
                    self.adj.setdefault(old, {})[new] = 1
                    self.adj.setdefault(new, {})[old] = 1
                    old = new
        # Upper/lower side tunnels: explicit wrap geometry, excluded from route
        # correctness claims until action probes and trajectory checks pass.
        for y in (56, 104):
            for start, stop in ((10, -1), (150, 160)):
                step = -1 if stop < start else 1
                old = (start, y)
                for x in range(start + step, stop, step):
                    new = (x, y)
                    self.adj.setdefault(old, {})[new] = 1
                    self.adj.setdefault(new, {})[old] = 1
                    old = new
            self.adj[(0, y)][(159, y)] = 1
            self.adj[(159, y)][(0, y)] = 1
        self.points = np.array(list(self.adj))

    def nearest(self, xy):
        distances = np.abs(self.points - xy).sum(axis=1)
        i = int(distances.argmin())
        return tuple(int(v) for v in self.points[i]), int(distances[i])

    def exits(self, xy):
        p, error = self.nearest(xy)
        if error > 3:
            return []
        result = []
        for name, (dx, dy) in DIRECTIONS.items():
            q = ((p[0] + dx) % 160, p[1] + dy)
            if q not in self.adj[p]:
                continue
            for _ in range(7):
                nxt = ((q[0] + dx) % 160, q[1] + dy)
                if nxt not in self.adj[q]:
                    break
                q = nxt
            result.append({"direction": name, "endpoint": list(q)})
        return result

    def distances(self, origin):
        start, _ = self.nearest(origin)
        distances, first = {start: 0}, {start: "NOOP"}
        todo = [(0, start)]
        while todo:
            dist, p = heapq.heappop(todo)
            if distances[p] != dist:
                continue
            for q, cost in self.adj[p].items():
                if dist + cost >= distances.get(q, float("inf")):
                    continue
                dx = (q[0] - p[0] + 80) % 160 - 80
                dy = q[1] - p[1]
                direction = next(k for k, v in DIRECTIONS.items() if v == (dx, dy))
                distances[q] = dist + cost
                first[q] = direction if p == start else first[p]
                heapq.heappush(todo, (dist + cost, q))
        return distances, first


class Observer:
    def __init__(self, initial_rgb, hold=8):
        self.maze = Maze(initial_rgb)
        self.hold = hold
        self.history = deque(maxlen=2)

    def observe(self, ram, rgb, frame):
        box = [int(ram[10]) - 13, int(ram[16]) + 1, 10, 10]
        player_pixels = color_support(rgb, box, [PLAYER])
        xy = [int(ram[10]) - 8, int(ram[16]) + 6]
        _, graph_error = self.maze.nearest(xy)
        player = {"xy": xy, "visible": player_pixels > 0}
        ghosts = []
        for i, color in enumerate(GHOSTS):
            box_g = [int(ram[6 + i]) - 13, int(ram[12 + i]) + 1, 10, 10]
            normal = color_support(rgb, box_g, [color])
            vulnerable = color_support(rgb, box_g, [BLUE])
            ghosts.append(
                {
                    "id": f"ghost-{i}",
                    "xy": [int(ram[6 + i]) - 8, int(ram[12 + i]) + 6],
                    "visible": bool(normal or vulnerable),
                    "appearance": "normal" if normal else "blue" if vulnerable else "unknown",
                }
            )
        pellets = []
        for i, box_p in enumerate(self.maze.pellet_sites):
            if color_support(rgb, box_p, [PINK]) >= 4:
                pellets.append({"id": f"pellet-{i}", "xy": [box_p[0] + 2, box_p[1] + 1]})
        # All visible regular pellets are exposed. Disappearance is not asserted
        # to mean consumption; sprites can occlude a pellet.
        current = {"frame": frame, "player": player, "ghosts": ghosts}
        obs = {
            "schema_version": SCHEMA,
            "maze_id": int(ram[0]),
            **current,
            "pellets": pellets,
            "exits": self.maze.exits(xy) if player["visible"] else [],
            "corridor_segments": [[list(a), list(b)] for a, b in self.maze.edges],
            "tunnel_rows": [56, 104],
            "history": list(self.history),
            "candidate_actions": [
                {"id": i, "ale_meaning": name, "hold_raw_frames": self.hold}
                for i, name in enumerate(NAMES)
            ],
        }
        self.history.append(current)
        checks = {
            "player_pixels": player_pixels,
            "graph_error": graph_error,
            "visible_ghosts": sum(g["visible"] for g in ghosts),
            "visible_pellets": len(pellets),
        }
        return obs, checks


def target(obs, avoid=True):
    """Fixed selection rule for probes; L1 proximity is not collision risk."""
    x, y = obs["player"]["xy"]

    def distance(obj):
        xx, yy = obj["xy"]
        return abs(xx - x) + abs(yy - y), obj["id"]

    threats = [g for g in obs["ghosts"] if g["visible"] and g["appearance"] == "normal"]
    if avoid and threats:
        nearest = min(threats, key=distance)
        if distance(nearest)[0] <= 32:
            return nearest, "evade"
    if obs["pellets"]:
        return min(obs["pellets"], key=distance), "collect"
    return None, "none"


def literal(obs, maze, rule="avoid"):
    if not obs["player"]["visible"] or not obs["exits"]:
        return 0, "unavailable"
    obj, mode = target(obs, avoid=rule == "avoid")
    if obj is None:
        return 0, "no-visible-target"
    if mode == "evade":
        gx, gy = obj["xy"]
        exit_ = max(
            obs["exits"], key=lambda e: abs(e["endpoint"][0] - gx) + abs(e["endpoint"][1] - gy)
        )
        return NAMES.index(exit_["direction"]), mode
    distances, first = maze.distances(obs["player"]["xy"])
    # Local controls use the same supplied geometry and visible pellets. The
    # route is computed only in this controller, never inserted into observations.
    choices = []
    for pellet in obs["pellets"]:
        point, _ = maze.nearest(pellet["xy"])
        if distances.get(point, 0) > 0:
            choices.append((distances[point], pellet["id"], first[point]))
    if not choices:
        return 0, "no-reachable-pellet"
    return NAMES.index(min(choices)[2]), mode
