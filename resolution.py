from collections import deque
from itertools import combinations, permutations
from pathlib import Path

LEVEL = 6

DIRECTIONS = {"1": (0, 2), "2": (1, 1), "3": (1, -1), "4": (0, -2), "5": (-1, -1), "6": (-1, 1)}


def board(radius):
    last = 2 * radius
    rows = []
    for i in range(last + 1):
        indent = abs(radius - i)
        count = last + 1 - indent  
        if i in (0, last):
            cells = ["*"] * count
        else:
            cells = ["*"] + ["O"] * (count - 2) + ["*"]
        pad = "-" * indent
        rows.append(pad + "-".join(cells) + pad)
    return rows


def solve_level1(text):
    n, *radii = map(int, text.split())
    assert len(radii) == n, f"esperava {n} raios, encontrei {len(radii)}"
    return "".join("\n".join(board(r)) + "\n\n" for r in radii)


def read_boards(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    n, pos, boards = int(lines[0]), 1, []
    for _ in range(n):
        _, rows, cols = map(int, lines[pos].split())
        grid = [list(line) for line in lines[pos + 1:pos + 1 + rows]]
        assert len(grid) == rows and all(len(row) == cols for row in grid)
        boards.append(grid)
        pos += 1 + rows
    assert pos == len(lines), "linhas a mais no input"
    return boards


def fire(grid):
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch in DIRECTIONS:
                dr, dc = DIRECTIONS[ch]
                y, x = r + dr, c + dc
                while 0 <= y < len(grid) and 0 <= x < len(grid[y]):
                    if grid[y][x] == "O":
                        grid[y][x] = "M"
                    y, x = y + dr, x + dc
    return grid


def solve_level2(text):
    return "".join("\n".join(map("".join, fire(grid))) + "\n\n" for grid in read_boards(text))


def hits(grid, emitters=None):
    if emitters is None:
        emitters = [((r, c), ch) for r, row in enumerate(grid) for c, ch in enumerate(row) if ch in DIRECTIONS]
    count = {}
    for (r, c), ch in emitters:
        dr, dc = DIRECTIONS[ch]
        y, x = r + dr, c + dc
        while 0 <= y < len(grid) and 0 <= x < len(grid[y]):
            if grid[y][x] in "OM":
                count[y, x] = count.get((y, x), 0) + 1
            y, x = y + dr, x + dc
    return count


def fire_level3(grid, emitters=None):
    for (y, x), n in hits(grid, emitters).items():
        if n == 2:
            grid[y][x] = "M"
        elif n >= 3:
            grid[y][x] = "O"
    return grid


def solve_level3(text):
    return "".join("\n".join(map("".join, fire_level3(grid))) + "\n\n" for grid in read_boards(text))


def ring(radius):
    R = radius
    return ([(0, R + 2 * k) for k in range(R)] + [(k, 3 * R + k) for k in range(R)]
            + [(R + k, 4 * R - k) for k in range(R)] + [(2 * R, 3 * R - 2 * k) for k in range(R)]
            + [(2 * R - k, R - k) for k in range(R)] + [(R - k, k) for k in range(R)])


START = {"1": 5, "2": 0, "3": 1, "4": 2, "5": 3, "6": 4}


def submit(grid, pattern):
    if not all(grid[y][x] == "M" for y, x in pattern):
        return False
    for y, x in pattern:
        for dy, dx in DIRECTIONS.values():
            ny, nx = y + dy, x + dx
            if (ny, nx) not in pattern and 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]) and grid[ny][nx] == "M":
                return False
    for y, x in pattern:
        grid[y][x] = "O"
    return True


def run_program(radius, program, pattern=None):
    grid = [list(row) for row in board(radius)]
    cells = ring(radius)
    pos = {k: START[k] * radius for k in START}
    active = {k: False for k in START}
    submitted = 0
    for line in program:
        for k, op in zip("123456", line):
            if op == "F":
                pos[k] = (pos[k] + 1) % len(cells)
            elif op == "B":
                pos[k] = (pos[k] - 1) % len(cells)
            elif op == "T":
                active[k] = not active[k]
        fire_level3(grid, [(cells[pos[k]], k) for k in START if active[k]])
        if pattern and submit(grid, pattern):
            submitted += 1
    return grid, submitted


def solve_level4(text):
    tokens = text.split()
    n, i, out = int(tokens[0]), 1, []
    for _ in range(n):
        radius, count = int(tokens[i]), int(tokens[i + 1])
        program = [tokens[i + 2 + 6 * j:i + 8 + 6 * j] for j in range(count)]
        i += 2 + 6 * count
        out.append("\n".join(map("".join, run_program(radius, program)[0])) + "\n\n")
    assert i == len(tokens), "tokens a mais no input"
    return "".join(out)


def solve_level5(text):
    tokens = text.split()
    n, i, out = int(tokens[0]), 1, []
    for _ in range(n):
        radius, rows = int(tokens[i]), int(tokens[i + 1])
        pattern = {(y, x) for y, line in enumerate(tokens[i + 3:i + 3 + rows]) for x, ch in enumerate(line) if ch == "M"}
        i += 3 + rows
        count = int(tokens[i])
        program = [tokens[i + 1 + 6 * j:i + 7 + 6 * j] for j in range(count)]
        i += 1 + 6 * count
        out.append(f"{run_program(radius, program, pattern)[1]}\n")
    assert i == len(tokens), "tokens a mais no input"
    return "".join(out)


HEX = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
KING = [(dq, dr) for dq in (-1, 0, 1) for dr in (-1, 0, 1) if dq or dr]


def sign(v):
    return (v > 0) - (v < 0)


def pen_program(radius, cells, count):
    lim = radius - 1
    target = {((x - 2 * radius - (y - radius)) // 2, y - radius) for y, x in cells}
    halo = {(q + dq, r + dr) for q, r in target for dq, dr in HEX} - target

    def allowed(c):
        return abs(c[0]) <= lim and abs(c[1]) <= lim and c not in halo

    def nearest(start, todo):
        if start in todo:
            return [start]
        prev, queue = {start: None}, deque([start])
        while queue:
            cur = queue.popleft()
            for dq, dr in KING:
                nxt = (cur[0] + dq, cur[1] + dr)
                if nxt not in prev and allowed(nxt):
                    prev[nxt] = cur
                    if nxt in todo:
                        path = [nxt]
                        while prev[path[-1]] != start:
                            path.append(prev[path[-1]])
                        return path[::-1]
                    queue.append(nxt)

    def step(a, b, ops=("-", "-")):
        dq, dr = b[0] - a[0], b[1] - a[1]
        return [ops[0] if not dr else "F" if dr < 0 else "B", ops[1] if not dq else "F" if dq > 0 else "B", "-", "-", "-", "-"]

    start = min(target, key=lambda c: (max(abs(c[0]), abs(c[1])), c))
    pos, lines = (0, 0), []
    while pos != start:
        nxt = (pos[0] + sign(start[0] - pos[0]), pos[1] + sign(start[1] - pos[1]))
        lines.append(step(pos, nxt))
        pos = nxt
    lines.append(["T", "T", "-", "-", "-", "-"])
    todo, done = target - {start}, 0
    while True:
        if not todo:
            done += 1
            if done == count:
                return lines
            todo = set(target)
        for nxt in nearest(pos, todo):
            lines.append(step(pos, nxt))
            pos = nxt
            todo.discard(nxt)


KEYS = "123456"
ERASE_MAX = 10
ERASE_SUBSETS = 24
_GEOMETRY = {}


def geometry(radius):
    # para cada emissor e posicao no anel: as celulas internas que o raio atravessa
    if radius not in _GEOMETRY:
        grid = board(radius)
        interior = {(y, x) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == "O"}
        rays, pos_of = {}, {k: {} for k in KEYS}
        for k in KEYS:
            dy, dx = DIRECTIONS[k]
            rays[k] = []
            for p, (y, x) in enumerate(ring(radius)):
                hit = []
                y, x = y + dy, x + dx
                while 0 <= y < len(grid) and 0 <= x < len(grid[y]):
                    if (y, x) in interior:
                        hit.append((y, x))
                    y, x = y + dy, x + dx
                rays[k].append(frozenset(hit))
                for c in hit:
                    pos_of[k][c] = p
        _GEOMETRY[radius] = interior, rays, pos_of
    return _GEOMETRY[radius]


def cdist(a, b, n):
    d = (b - a) % n
    return min(d, n - d)


def step_toward(a, b, n):
    d = (b - a) % n
    if d == 0:
        return "-", a
    return ("F", (a + 1) % n) if d <= n - d else ("B", (a - 1) % n)


def invariant(k, cell):
    (y, x), (dy, dx) = cell, DIRECTIONS[k]
    return y if dy == 0 else x - y if dy == dx else x + y


def along(k, cell):
    # ordem das celulas ao longo de uma reta da familia do emissor k
    return cell[1] if DIRECTIONS[k][0] == 0 else cell[0]


def safe_frame(rays, frame, target, halo, allow=()):
    # nenhum halo com 2 acertos (viraria materia) e nenhum alvo com 3+ (seria destruido);
    # halos em allow podem virar materia (serao apagados no frame seguinte)
    hits = {}
    for e, p in frame.items():
        for c in rays[e][p]:
            hits[c] = hits.get(c, 0) + 1
    return not any((h == 2 and c in halo and c not in allow) or (h >= 3 and c in target) for c, h in hits.items())


def paint_frames(radius, pos_of, chord_cells, target, halo, d1, p1, painters, ready, active_prev):
    # D1 sozinho na reta (1 acerto); cada pintor ativo cruzando a reta da +1 -> materia naquela celula.
    # ready[e] = (primeiro frame em que o emissor pode ser ligado/andar, posicao atual)
    n = 6 * radius
    segs, cur = [], []
    for c in sorted(chord_cells, key=lambda c: along(d1, c)) + [None]:
        if c is None or c in halo:
            idx = [i for i, cc in enumerate(cur) if cc in target]
            if idx:
                segs.append(cur[idx[0]:idx[-1] + 1])
            cur = []
        else:
            cur.append(c)
    pos = {e: ready[e][1] for e in painters}
    ready = {e: ready[e][0] for e in painters}
    plan = {e: {} for e in painters}

    def start_at(e, g):
        # emissor ja ligado pode seguir direto se o alvo esta a 1 passo;
        # ready pode ser negativo: o emissor desligado ja vinha andando antes deste trecho
        if e in active_prev and not plan[e] and cdist(pos[e], g, n) <= 1:
            return 0
        return max(0, ready[e] + cdist(pos[e], g, n))

    for seg in sorted(segs, key=len, reverse=True):
        start, e, s = min((start_at(e, pos_of[e][s[0]]), e, s) for e in painters for s in (seg, seg[::-1]))
        for j, c in enumerate(s):
            plan[e][start + j] = pos_of[e][c]
        pos[e] = pos_of[e][s[-1]]
        ready[e] = start + len(s) + 1
    total = max(max(pl) for pl in plan.values() if pl) + 1
    return [dict({d1: p1}, **{e: plan[e][j] for e in painters if j in plan[e]}) for j in range(total)]


def chord_program(radius, target, count, fam, rev, one_family):
    # retas "boas" (ate 4 halos): dois emissores paralelos na mesma reta acertam 2x a reta inteira
    # (vira materia) e ate 4 emissores das outras familias furam (3 acertos) as celulas de halo;
    # retas "ruins": um emissor na reta e os outros pintam celula a celula cruzando por ela
    interior, rays, pos_of = geometry(radius)
    n = 6 * radius
    halo = {(y + dy, x + dx) for y, x in target for dy, dx in DIRECTIONS.values()} & interior - target
    d1, d2 = KEYS[fam], KEYS[fam + 3]
    others = [k for k in KEYS if k not in (d1, d2)]
    families = [[others[0], KEYS[(KEYS.index(others[0]) + 3) % 6]]]
    families.append([e for e in others if e not in families[0]])

    def stamps(p, hs):
        return [dict({d1: p, d2: pos_of[d2][next(iter(rays[d1][p]))]}, **{e: pos_of[e][h] for e, h in zip(perm, hs)})
                for perm in permutations(others, len(hs))]

    one = []
    chords = sorted({pos_of[d1][c] for c in target}, key=lambda p: invariant(d1, next(iter(rays[d1][p]))))
    for p in chords[::-1] if rev else chords:
        hs = sorted(rays[d1][p] & halo)
        stampable = len(hs) <= 4 and any(safe_frame(rays, fr, target, halo) for fr in stamps(p, hs))
        one.append(("stamp" if stampable else "paint", p, hs))
    seq = [s for j in range(count) for s in (one if j % 2 == 0 else one[::-1])]

    pos = {k: START[k] * radius for k in KEYS}
    t_free = {k: 1 for k in KEYS}
    frame_line, resets, assigns = [], [], []
    active_prev = {}

    def place(options, allow=()):
        nonlocal active_prev
        k = len(frame_line)
        base = frame_line[-1] + 1 if k else 1
        best = None
        for frame in options:
            if not safe_frame(rays, frame, target, halo, allow):
                continue
            moved = sum(cdist(pos[e], p, n) for e, p in frame.items())
            if all(cdist(active_prev[e], p, n) <= 1 for e, p in frame.items() if e in active_prev):
                L = max([base] + [t_free[e] + cdist(pos[e], p, n) for e, p in frame.items() if e not in active_prev])
                if best is None or (L, moved) < best[0]:
                    best = (L, moved), frame, False
            if k:
                # desliga tudo, reposiciona e liga de novo
                L = max([base + 1] + [(base + 1 if e in active_prev else t_free[e]) + cdist(pos[e], p, n)
                                      for e, p in frame.items()])
                if best is None or (L, moved + 1) < best[0]:
                    best = (L, moved + 1), frame, True
        if best is None:
            return False
        (L, _), frame, reset = best
        for e in KEYS:
            if e in active_prev and (reset or e not in frame):
                t_free[e] = (base if reset else L) + 1
        pos.update(frame)
        active_prev = dict(frame)
        frame_line.append(L)
        resets.append(reset)
        assigns.append(frame)
        return True

    def erase_frames(p, left):
        # D1 sozinho na reta + uma reta de cada outra familia por halo sobrando: 3 acertos apagam
        (qa, qb), (sa, sb) = families
        out = []
        for q1, q2 in ((qa, qb), (qb, qa)):
            for s1, s2 in ((sa, sb), (sb, sa)):
                fr = {d1: p}
                for (eq, es), h in zip(((q1, s1), (q2, s2)), left):
                    fr[eq], fr[es] = pos_of[eq][h], pos_of[es][h]
                out.append(fr)
        return out

    def snapshot():
        return dict(pos), dict(t_free), dict(active_prev), len(frame_line)

    def restore(snap):
        nonlocal active_prev
        pos.clear(), pos.update(snap[0])
        t_free.clear(), t_free.update(snap[1])
        active_prev = dict(snap[2])
        del frame_line[snap[3]:], resets[snap[3]:], assigns[snap[3]:]

    def run_plan(plan):
        return all(place(opts, allow) for opts, allow in plan)

    for kind, p, hs in seq:
        if kind == "stamp":
            if not place(stamps(p, hs)):
                return None
            continue
        # reta ruim: compara pintura (planejada com o estado real) e carimbar+apagar, pelo custo em linhas
        base = frame_line[-1] + 1 if frame_line else 1
        ready = {e: (1 if e in active_prev else t_free[e] - base, pos[e]) for e in others}
        plans = []
        for painters in ([] if one_family else [others]) + families:
            frames = paint_frames(radius, pos_of, rays[d1][p], target, halo, d1, p, painters, ready, active_prev)
            plans.append([([fr], ()) for fr in frames])
        if 4 < len(hs) <= ERASE_MAX:
            keeps = list(combinations(hs, 4))
            if len(keeps) > ERASE_SUBSETS:
                # amostra fixa (deterministica) de quais 4 halos furar no carimbo
                keeps = keeps[::len(keeps) // ERASE_SUBSETS + 1]
            for keep in keeps:
                left = [h for h in hs if h not in keep]
                plan = [(stamps(p, list(keep)), tuple(left))]
                plan += [(erase_frames(p, left[i:i + 2]), ()) for i in range(0, len(left), 2)]
                plans.append(plan)
        snap, best = snapshot(), None
        for plan in plans:
            if run_plan(plan) and (best is None or frame_line[-1] < best[0]):
                best = frame_line[-1], plan
            restore(snap)
        if best is None or not run_plan(best[1]):
            return None

    wants = {k: [] for k in KEYS}
    for k in range(len(frame_line)):
        L, off = frame_line[k], (frame_line[k - 1] + 1 if k and resets[k] else frame_line[k])
        prev, cur = assigns[k - 1] if k else {}, assigns[k]
        for e in KEYS:
            if e in prev and (resets[k] or e not in cur):
                wants[e].append((off, None, "off"))
            if e in cur:
                wants[e].append((L, cur[e], "move" if e in prev and not resets[k] else "on"))

    total = frame_line[-1]
    act = {k: ["-"] * (total + 1) for k in KEYS}
    for k in KEYS:
        p, free = START[k] * radius, 1
        for line, goal, kind in sorted(wants[k], key=lambda w: w[0]):
            if kind == "on":
                while free < line:
                    act[k][free], p = step_toward(p, goal, n)
                    free += 1
                act[k][line] = "T"
            elif kind == "off":
                act[k][line] = "T"
            else:
                act[k][line], p = step_toward(p, goal, n)
            if goal is not None and p != goal:
                return None
            free = line + 1
    return [[act[k][i] for k in KEYS] for i in range(1, total + 1)]


def accepted_at(radius, program, pattern, count):
    # linha em que o padrao foi aceito pela count-esima vez (None se nunca)
    grid, cells = [list(row) for row in board(radius)], ring(radius)
    pos = {k: START[k] * radius for k in START}
    active = {k: False for k in START}
    got = 0
    for i, line in enumerate(program):
        for k, op in zip(KEYS, line):
            if op == "F":
                pos[k] = (pos[k] + 1) % len(cells)
            elif op == "B":
                pos[k] = (pos[k] - 1) % len(cells)
            elif op == "T":
                active[k] = not active[k]
        fire_level3(grid, [(cells[pos[k]], k) for k in START if active[k]])
        if submit(grid, pattern):
            got += 1
            if got == count:
                return i + 1
    return None


def best_program(radius, cells, count):
    best = pen_program(radius, cells, count)
    for fam in range(3):
        for rev, one_family in ((False, False), (True, False), (False, True), (True, True)):
            program = chord_program(radius, cells, count, fam, rev, one_family)
            if program is not None:
                end = accepted_at(radius, program, cells, count)
                if end is not None and end < len(best):
                    best = program[:end]
    return best


def solve_level6(text):
    tokens = text.split()
    n, i, out, score = int(tokens[0]), 1, [], 0
    for _ in range(n):
        radius, rows, _, count = map(int, tokens[i:i + 4])
        cells = {(y, x) for y, line in enumerate(tokens[i + 4:i + 4 + rows]) for x, ch in enumerate(line) if ch == "M"}
        i += 4 + rows
        program = best_program(radius, cells, count)
        assert run_program(radius, program, cells)[1] == count
        score += len(program)
        out.append("\n".join(map(" ".join, program)) + "\n\n")
    assert i == len(tokens), "tokens a mais no input"
    print("score", score)
    return "".join(out)


SOLVERS = {1: solve_level1, 2: solve_level2, 3: solve_level3, 4: solve_level4, 5: solve_level5, 6: solve_level6}


def main():
    base = Path(__file__).resolve().parent
    for path in sorted(base.rglob(f"in_level-{LEVEL}_*.txt")):
        out = path.with_name("out" + path.name[2:])
        result = SOLVERS[LEVEL](path.read_text())
        if "example" in path.name:
            ok = out.exists() and out.read_bytes() == result.encode()
            print(f"{path.name}: {'OK' if ok else 'FALHOU'}")
        else:
            out.write_text(result, newline="\n")
            print(f"{path.name} -> {out.name}")


if __name__ == "__main__":
    main()
