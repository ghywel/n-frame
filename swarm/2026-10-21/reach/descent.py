"""Emulate the recommendation's 1/16 descents (zero, ring, temporal) and the 1/8 arbitration on W3's wall, offline.
descend_s: 8-neighbour pattern search, step 0.75 texel halving over 5 rounds (or FIRST/ROUNDS), cost = 3x3 SAD +
REG_LAMBDA*|d|, TIE_MARGIN 1e-4. Ring: best of the +-1 ring at >=0.75 from off_a. Temporal: start at the previous
pair's flow (here: the truth of the previous pair, v_prev, i.e. the best case for the temporal seed).
1/8: each seed doubled, refined over +-2 texels (REFINE_REG_LAMBDA 0.05), scored SAD + 0.3*|f| (+0.5*|f-prev| if trusted).
Reports, per speed: share of texels whose coarse pick (best of the three by 1/8 score) and 1/8 pick are near truth / near zero.
Also the variant with the first step doubled (1.5, 6 rounds) and a 1/8 search of +-5 texels from zero."""
import numpy as np
from w3levels import wall, level, sad3
REG = 0.06; TIE = 1e-4
def descend(As, Bs, start, first=0.75, rounds=5, cache={}):
    # start: array (h,w) of x-offsets in texels (y fixed at 0: the pan is horizontal; the y search is omitted)
    def cost(d):
        # d: array of per-texel offsets; evaluate SAD per texel at its own offset (bilinear in x)
        h, w = As.shape
        xs = np.arange(w)[None, :] + d
        x0 = np.floor(xs).astype(int); t = xs - x0
        def rd(xx):
            xx = np.clip(xx, 0, w - 1); return np.take_along_axis(Bs, xx, 1)
        Bsh = (1 - t) * rd(x0) + t * rd(x0 + 1)
        D = np.abs(As - Bsh)   # NOTE: the window is applied on the per-texel difference at THIS texel's offset
        S = np.zeros_like(D)
        for oy in (-1, 0, 1):
            for ox in (-1, 0, 1):
                S += np.roll(np.roll(D, oy, 0), ox, 1)
        return S + REG * np.abs(d)
    best = start.copy(); bc = cost(best)
    step = first
    for _ in range(rounds):
        cand = best.copy(); cb = bc.copy()
        for s in (-1.0, 1.0):
            d = best + s * step
            c = cost(d)
            m = c < cb * (1 - TIE)
            cand = np.where(m, d, cand); cb = np.where(m, c, cb)
        best = cand; bc = cb
        step *= 0.5
    return best, bc
def ring_start(As, Bs, off_a):
    # the x-only ring: candidates -1, +1 (the y ring points are omitted in this 1-D emulation)
    h, w = As.shape
    bestc = np.full(As.shape, 1e30); st = np.zeros(As.shape)
    for o in (-1.0, 1.0):
        d = np.full(As.shape, o)
        far = np.abs(d - off_a) >= 0.75
        # cost at o
        xs = np.arange(w)[None, :] + d; x0 = np.floor(xs).astype(int)
        Bsh = np.take_along_axis(Bs, np.clip(x0, 0, w - 1), 1)
        D = np.abs(As - Bsh); S = np.zeros_like(D)
        for oy in (-1, 0, 1):
            for ox in (-1, 0, 1): S += np.roll(np.roll(D, oy, 0), ox, 1)
        c = S + REG * np.abs(d)
        m = far & (c < bestc)
        bestc = np.where(m, c, bestc); st = np.where(m, d, st)
    return st
def refine_e(Ae, Be, seed, R=2, lam=0.05):
    best = seed.copy()
    def cost(d):
        h, w = Ae.shape
        xs = np.arange(w)[None, :] + d; x0 = np.floor(xs).astype(int); t = xs - x0
        def rd(xx): return np.take_along_axis(Be, np.clip(xx, 0, w - 1), 1)
        D = np.abs(Ae - ((1 - t) * rd(x0) + t * rd(x0 + 1))); S = np.zeros_like(D)
        for oy in (-1, 0, 1):
            for ox in (-1, 0, 1): S += np.roll(np.roll(D, oy, 0), ox, 1)
        return S
    bc = cost(seed)
    for k in range(-R, R + 1):
        if k == 0: continue
        d = seed + k; c = cost(d) + lam * abs(k)
        m = c < bc * (1 - TIE); best = np.where(m, d, best); bc = np.where(m, c, bc)
    return best, cost(best)
def run(v, v_prev, first=0.75, rounds=5, wide=None, recentre=False):
    A = wall(0.0); B = wall(-v)
    As, Bs = level(A, 16), level(B, 16); Ae, Be = level(A, 8), level(B, 8)
    z = np.zeros(As.shape)
    off_a, _ = descend(As, Bs, z, first, rounds)
    off_b, _ = descend(As, Bs, ring_start(As, Bs, off_a), first, rounds)
    off_c, _ = descend(As, Bs, np.full(As.shape, v_prev / 16.0), first, rounds)
    tr = v / 16.0
    sl = (slice(2, -2), slice(6, -6))
    def near(x, t): return np.mean(np.abs(x[sl] - t) <= 0.5)
    out = {"S_zero": (near(off_a, tr), near(off_a, 0)), "S_ring": (near(off_b, tr), near(off_b, 0)), "S_temp": (near(off_c, tr), near(off_c, 0))}
    # 1/8: upsample seeds (nearest), refine, score
    def up(o): return np.repeat(np.repeat(o, 2, 0), 2, 1)[:Ae.shape[0], :Ae.shape[1]] * 2.0
    prev_e = np.full(Ae.shape, v_prev / 8.0)
    g = (v / 8.0) if recentre else 0.0
    picks = []; scores = []
    for o, trusted in ((off_a, False), (off_b, False), (off_c, True)):
        r, s = refine_e(Ae, Be, up(o))
        sc = s + 0.3 * np.abs(r - g) + (0.5 * np.abs(r - prev_e) if trusted else 0.0)
        picks.append(r); scores.append(sc)
    if wide is not None:
        r, s = refine_e(Ae, Be, np.zeros(Ae.shape), R=wide)
        picks.append(r); scores.append(s + 0.3 * np.abs(r - g))
    P = np.stack(picks); Sc = np.stack(scores)
    pick = np.take_along_axis(P, Sc.argmin(0)[None], 0)[0]
    tre = v / 8.0
    sl8 = (slice(4, -4), slice(12, -12))
    out["E_pick"] = (np.mean(np.abs(pick[sl8] - tre) <= 0.75), np.mean(np.abs(pick[sl8]) <= 0.75))
    return out
if __name__ == "__main__":
    import itertools
    for label, kw in (("as shipped (0.75 x5)", {}), ("first step doubled (1.5 x6)", {"first": 1.5, "rounds": 6}),
                      ("shipped + 1/8 wide +-5 from zero", {"wide": 5}), ("shipped + wide +-5 + prior centred on truth", {"wide": 5, "recentre": True}),
                      ("doubled + prior centred on truth", {"first": 1.5, "rounds": 6, "recentre": True})):
        print("==", label, "  (share near truth / near zero)")
        print(" v   S_zero        S_ring        S_temp        E_pick")
        for v in (16, 20, 24, 28, 32, 34, 36, 38, 40):
            o = run(float(v), float(v) - 1.0, **kw)
            print(f"{v:3} " + "  ".join(f"{o[k][0]:.2f}/{o[k][1]:.2f}" for k in ("S_zero", "S_ring", "S_temp", "E_pick")))
        print()
