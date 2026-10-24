"""Level 6 otimizado. Para cada padrao fica com o menor programa valido entre:
- chord_program (resolution.py): varredura por retas com carimbos (2 emissores na mesma reta) e furos;
- greedy_beam: busca em feixe linha a linha com numpy (avalia as 4096 combinacoes de acao dos
  6 emissores, nunca deixa halo virar materia, maximiza alvos desenhados + potencial de proximidade);
e depois aplica o vai-e-vem: repete o trecho da copia mais barata ida e volta (F<->B) nas copias seguintes.
Uso: python level6_optimizer.py   (gera out_level-6_*.txt na mesma pasta)
"""
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import resolution as rs
from resolution import DIRECTIONS, START, KEYS, geometry, best_program, accepted_at, run_program

ACTS = "-FBT"
_GG = {}


def greedy_geo(radius):
    if radius not in _GG:
        interior, rays, pos_of = geometry(radius)
        cells = sorted(interior)
        idx = {c: i for i, c in enumerate(cells)}
        n = 6 * radius
        masks = {}
        for e in KEYS:
            m = np.zeros((n, len(cells)), dtype=np.int8)
            for p in range(n):
                for c in rays[e][p]:
                    m[p, idx[c]] = 1
            masks[e] = m
        _GG[radius] = cells, idx, masks, pos_of
    return _GG[radius]




def greedy_la(radius, target, count, limit, decay=0.35, wnew=100.0, noise=0.0, seed=0, K=6, gamma=1.0, init=()):
    # guloso com olhar de 2 passos: para as K melhores jogadas, soma a melhor jogada seguinte
    cells, idx, masks, pos_of = greedy_geo(radius)
    interior = set(cells)
    n = 6 * radius
    N = len(cells)
    halo = {(y + dy, x + dx) for y, x in target for dy, dx in DIRECTIONS.values()} & interior - target
    T = np.zeros(N, bool)
    H = np.zeros(N, bool)
    for c in target:
        T[idx[c]] = True
    for c in halo:
        H[idx[c]] = True
    tl = sorted(target)
    tidx = np.array([idx[c] for c in tl])
    linepos = {e: np.array([pos_of[e][c] for c in tl]) for e in KEYS}
    fams = [(KEYS[f], KEYS[f + 3]) for f in range(3)]
    pw = np.power(decay, np.arange(4 * n + 8)).astype(np.float32)
    rng = np.random.default_rng(seed)

    def option(pos, act, e, a):
        p, on = pos[e], act[e]
        if a == "F":
            p = (p + 1) % n
        elif a == "B":
            p = (p - 1) % n
        elif a == "T":
            on = not on
        return p, on

    def evaluate(pos, act, matter, stall):
        undrawn = T & ~matter
        u = ~matter[tidx]
        if not u.any():
            u = np.ones_like(u)
        fam_hits, fam_d, fam_ops = [], [], []
        for a, b in fams:
            hs, ds, ops = [], [], []
            opt_a = [option(pos, act, a, x) for x in ACTS]
            opt_b = [option(pos, act, b, x) for x in ACTS]
            for i, (pa, oa) in enumerate(opt_a):
                for j, (pb, ob) in enumerate(opt_b):
                    h = np.zeros(N, np.int8)
                    if oa:
                        h = h + masks[a][pa]
                    if ob:
                        h = h + masks[b][pb]
                    hs.append(h)
                    da = np.abs(linepos[a][u] - pa)
                    da = np.minimum(da, n - da) + (0 if oa else 1)
                    db = np.abs(linepos[b][u] - pb)
                    db = np.minimum(db, n - db) + (0 if ob else 1)
                    ds.append(np.minimum(da, db))
                    ops.append((ACTS[i], ACTS[j], (i > 0) + (j > 0), oa + ob))
            fam_hits.append(np.array(hs))
            fam_d.append(np.array(ds))
            fam_ops.append(ops)
        hits = fam_hits[0][:, None, None, :] + fam_hits[1][None, :, None, :] + fam_hits[2][None, None, :, :]
        eq2 = hits == 2
        bad = (eq2 & H).any(-1) | ((hits >= 3) & matter & T).any(-1)
        new = (eq2 & undrawn).sum(-1)
        d0, d1, d2 = fam_d[0][:, None, None, :], fam_d[1][None, :, None, :], fam_d[2][None, None, :, :]
        cost = d0 + d1 + d2 - np.maximum(np.maximum(d0, d1), d2)

        def per(k):
            return (np.array([o[k] for o in fam_ops[0]])[:, None, None] + np.array([o[k] for o in fam_ops[1]])[None, :, None]
                    + np.array([o[k] for o in fam_ops[2]])[None, None, :])

        if stall > n // 3:
            k = int(np.argmin(cost[0, 0, 0]))
            phi = 50 * pw[cost[..., k]] - 0.5 * per(3)
        else:
            phi = pw[cost].sum(-1)
        score = wnew * new + phi - 0.01 * per(2)
        if noise:
            score = score + rng.random(score.shape) * noise
        score[bad] = -1e18
        return score, hits, fam_ops

    def step(pos, act, matter, combo, hits, fam_ops):
        acts = {}
        for f, k in enumerate(combo):
            a, b = fams[f]
            acts[a], acts[b] = fam_ops[f][k][0], fam_ops[f][k][1]
        npos, nact = dict(pos), dict(act)
        for e in KEYS:
            npos[e], nact[e] = option(pos, act, e, acts[e])
        nm = matter.copy()
        h = hits[combo]
        nm[h == 2] = True
        nm[h >= 3] = False
        accepted = T[nm].sum() == T.sum() and not (nm & H).any()
        if accepted:
            nm[T] = False
        return acts, npos, nact, nm, accepted

    pos = {e: START[e] * radius for e in KEYS}
    act = {e: False for e in KEYS}
    matter = np.zeros(N, bool)
    acc, stall, lines = 0, 0, []
    for line in init:
        # aplica um prefixo pronto (ex.: carimbos das retas boas) e continua dele
        acts = dict(zip(KEYS, line))
        for e in KEYS:
            pos[e], act[e] = option(pos, act, e, acts[e])
        h = np.zeros(N, np.int8)
        for e in KEYS:
            if act[e]:
                h = h + masks[e][pos[e]]
        matter[h == 2] = True
        matter[h >= 3] = False
        if T[matter].sum() == T.sum() and not (matter & H).any():
            acc += 1
            matter[T] = False
        lines.append(list(line))
    while acc < count:
        score, hits, fam_ops = evaluate(pos, act, matter, stall)
        flat = score.reshape(-1)
        cand = np.argpartition(-flat, K)[:K] if flat.size > K else np.arange(flat.size)
        best = None
        for c in cand:
            if flat[c] < -1e17:
                continue
            combo = np.unravel_index(c, score.shape)
            acts, npos, nact, nm, accepted = step(pos, act, matter, combo, hits, fam_ops)
            if accepted:
                total = flat[c] + 1e6
            else:
                s2, _, _ = evaluate(npos, nact, nm, stall)
                total = flat[c] + gamma * s2.max()
            if best is None or total > best[0]:
                best = (total, acts, npos, nact, nm, accepted)
        if best is None:
            return None
        _, acts, npos, nact, nm, accepted = best
        before = matter[tidx].sum()
        pos, act, matter = npos, nact, nm
        if accepted:
            acc += 1
            stall = 0
        elif matter[tidx].sum() > before:
            stall = 0
        else:
            stall += 1
        lines.append([acts[e] for e in KEYS])
        if len(lines) >= limit or stall > 3 * n:
            return None
    return lines


def greedy_beam(radius, target, count, limit, decay=0.35, wnew=100.0, noise=0.0, seed=0, W=6, C=4):
    # busca em feixe: mantem os W melhores estados e expande as C melhores jogadas de cada um
    cells, idx, masks, pos_of = greedy_geo(radius)
    interior = set(cells)
    n = 6 * radius
    N = len(cells)
    halo = {(y + dy, x + dx) for y, x in target for dy, dx in DIRECTIONS.values()} & interior - target
    T = np.zeros(N, bool)
    H = np.zeros(N, bool)
    for c in target:
        T[idx[c]] = True
    for c in halo:
        H[idx[c]] = True
    tl = sorted(target)
    tidx = np.array([idx[c] for c in tl])
    linepos = {e: np.array([pos_of[e][c] for c in tl]) for e in KEYS}
    fams = [(KEYS[f], KEYS[f + 3]) for f in range(3)]
    pw = np.power(decay, np.arange(4 * n + 8)).astype(np.float32)
    rng = np.random.default_rng(seed)

    def option(pos, act, e, a):
        p, on = pos[e], act[e]
        if a == "F":
            p = (p + 1) % n
        elif a == "B":
            p = (p - 1) % n
        elif a == "T":
            on = not on
        return p, on

    def evaluate(pos, act, matter, stall):
        undrawn = T & ~matter
        u = ~matter[tidx]
        if not u.any():
            u = np.ones_like(u)
        fam_hits, fam_d, fam_ops = [], [], []
        for a, b in fams:
            hs, ds, ops = [], [], []
            opt_a = [option(pos, act, a, x) for x in ACTS]
            opt_b = [option(pos, act, b, x) for x in ACTS]
            for i, (pa, oa) in enumerate(opt_a):
                for j, (pb, ob) in enumerate(opt_b):
                    h = np.zeros(N, np.int8)
                    if oa:
                        h = h + masks[a][pa]
                    if ob:
                        h = h + masks[b][pb]
                    hs.append(h)
                    da = np.abs(linepos[a][u] - pa)
                    da = np.minimum(da, n - da) + (0 if oa else 1)
                    db = np.abs(linepos[b][u] - pb)
                    db = np.minimum(db, n - db) + (0 if ob else 1)
                    ds.append(np.minimum(da, db))
                    ops.append((ACTS[i], ACTS[j], (i > 0) + (j > 0), oa + ob))
            fam_hits.append(np.array(hs))
            fam_d.append(np.array(ds))
            fam_ops.append(ops)
        hits = fam_hits[0][:, None, None, :] + fam_hits[1][None, :, None, :] + fam_hits[2][None, None, :, :]
        eq2 = hits == 2
        bad = (eq2 & H).any(-1) | ((hits >= 3) & matter & T).any(-1)
        new = (eq2 & undrawn).sum(-1)
        d0, d1, d2 = fam_d[0][:, None, None, :], fam_d[1][None, :, None, :], fam_d[2][None, None, :, :]
        cost = d0 + d1 + d2 - np.maximum(np.maximum(d0, d1), d2)

        def per(k):
            return (np.array([o[k] for o in fam_ops[0]])[:, None, None] + np.array([o[k] for o in fam_ops[1]])[None, :, None]
                    + np.array([o[k] for o in fam_ops[2]])[None, None, :])

        if stall > n // 3:
            k = int(np.argmin(cost[0, 0, 0]))
            phi = 50 * pw[cost[..., k]] - 0.5 * per(3)
        else:
            phi = pw[cost].sum(-1)
        score = wnew * new + phi - 0.01 * per(2)
        if noise:
            score = score + rng.random(score.shape) * noise
        score[bad] = -1e18
        return score, hits, fam_ops

    def step(pos, act, matter, combo, hits, fam_ops):
        acts = {}
        for f, k in enumerate(combo):
            a, b = fams[f]
            acts[a], acts[b] = fam_ops[f][k][0], fam_ops[f][k][1]
        npos, nact = dict(pos), dict(act)
        for e in KEYS:
            npos[e], nact[e] = option(pos, act, e, acts[e])
        nm = matter.copy()
        h = hits[combo]
        nm[h == 2] = True
        nm[h >= 3] = False
        accepted = T[nm].sum() == T.sum() and not (nm & H).any()
        if accepted:
            nm[T] = False
        return acts, npos, nact, nm, accepted

    pos = {e: START[e] * radius for e in KEYS}
    act = {e: False for e in KEYS}
    matter = np.zeros(N, bool)
    # estado: (valor, linhas, pos, act, matter, aceitos, travado, celulas_desenhadas)
    beam = [(0.0, [], pos, act, matter, 0, 0, 0)]
    while True:
        children = []
        for val, lines, pos, act, matter, acc, stall, cum in beam:
            score, hits, fam_ops = evaluate(pos, act, matter, stall)
            flat = score.reshape(-1)
            cand = np.argpartition(-flat, C)[:C] if flat.size > C else np.arange(flat.size)
            for c in cand:
                if flat[c] < -1e17:
                    continue
                combo = np.unravel_index(c, score.shape)
                acts, npos, nact, nm, accepted = step(pos, act, matter, combo, hits, fam_ops)
                drawn = int(nm[tidx].sum()) - int(matter[tidx].sum())
                nacc = acc + (1 if accepted else 0)
                nstall = 0 if (accepted or drawn > 0) else stall + 1
                ncum = cum + max(drawn, 0) + (len(tl) if accepted else 0)
                nlines = lines + [[acts[e] for e in KEYS]]
                if nacc >= count:
                    return nlines
                v = ncum * wnew + float(flat[c]) - wnew * max(drawn, 0) + nacc * 1e6
                children.append((v, nlines, npos, nact, nm, nacc, nstall, ncum))
        if not children:
            return None
        children.sort(key=lambda s: -s[0])
        beam, seen = [], set()
        for ch in children:
            key = (tuple(ch[2].values()), tuple(ch[3].values()), ch[4].tobytes())
            if key in seen:
                continue
            seen.add(key)
            beam.append(ch)
            if len(beam) == W:
                break
        if len(beam[0][1]) >= limit or min(s[6] for s in beam) > 3 * n:
            return None


INV = {"F": "B", "B": "F", "T": "T", "-": "-"}


def accept_lines(R, prog, T):
    grid = [list(r) for r in rs.board(R)]
    cells = rs.ring(R)
    pos = {k: rs.START[k] * R for k in rs.START}
    act = {k: False for k in rs.START}
    acc, firsts, cur_first = [], [], None
    for i, line in enumerate(prog):
        before = sum(grid[y][x] == 'M' for y, x in T)
        for k, op in zip(rs.KEYS, line):
            if op == 'F': pos[k] = (pos[k] + 1) % len(cells)
            elif op == 'B': pos[k] = (pos[k] - 1) % len(cells)
            elif op == 'T': act[k] = not act[k]
        rs.fire_level3(grid, [(cells[pos[k]], k) for k in rs.START if act[k]])
        after = sum(grid[y][x] == 'M' for y, x in T)
        if cur_first is None and after > before:
            cur_first = i + 1
        if rs.submit(grid, T):
            if cur_first is None:
                cur_first = i + 1
            acc.append(i + 1)
            firsts.append(cur_first)
            cur_first = None
    return acc, firsts


def pingpong(R, prog, T, count):
    best = prog
    if count < 2:
        return best
    acc, firsts = accept_lines(R, prog, T)
    for k in range(min(len(acc), count)):
        s, b = firsts[k], acc[k]
        seg = prog[s - 1:b]
        fwd = seg
        rev = [["-"] * 6] + [[INV[o] for o in line] for line in reversed(seg)]
        cand = list(prog[:b])
        for j in range(count - k - 1):
            cand += rev if j % 2 == 0 else fwd
        if len(cand) >= len(best):
            continue
        end = rs.accepted_at(R, cand, T, count)
        if end is not None and end < len(best):
            best = cand[:end]
    return best




VARIANTS = [(0.35, 0.05, 2, 6, 4), (0.5, 0.05, 3, 6, 4), (0.35, 0.05, 5, 12, 4)]


def parse(text):
    tokens = text.split()
    n, i, out = int(tokens[0]), 1, []
    for _ in range(n):
        radius, rows, _, count = map(int, tokens[i:i + 4])
        cells = {(y, x) for y, line in enumerate(tokens[i + 4:i + 4 + rows]) for x, ch in enumerate(line) if ch == "M"}
        i += 4 + rows
        out.append((radius, cells, count))
    return out


def solve_one(args):
    radius, cells, count = args
    best = best_program(radius, cells, count)
    for decay, noise, seed, width, children in VARIANTS:
        g = greedy_beam(radius, cells, count, len(best), decay, 100.0, noise, seed, width, children)
        if g is not None and len(g) < len(best) and accepted_at(radius, g, cells, count) == len(g):
            best = g
    best = pingpong(radius, best, cells, count)
    assert run_program(radius, best, cells)[1] == count
    return best


def main():
    base = Path(__file__).resolve().parent
    for path in sorted(base.glob("in_level-6_*.txt")):
        with Pool() as pool:
            programs = pool.map(solve_one, parse(path.read_text()), chunksize=1)
        out = path.with_name("out" + path.name[2:])
        out.write_text("".join("\n".join(map(" ".join, p)) + "\n\n" for p in programs), newline="\n")
        print(path.name, "->", out.name, "score", sum(map(len, programs)), flush=True)


if __name__ == "__main__":
    main()
