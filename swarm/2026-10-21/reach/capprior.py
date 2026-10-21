"""Two more offline variants on W3 (1-D emulation, see descent.py):
 (C) the 1/8 prior CAPPED at half the texel's own zero-SAD: penalty = min(0.3|f|, 0.5*SAD(0)), wide +-5 from zero added;
 (D) the 1/8 prior centred on the texel's OWN best coarse candidate by raw SAD (local, no frame-wide term), gated: only
     when that candidate is > 1.5 coarse texels from zero (else centre stays at zero), with the doubled first step."""
import numpy as np
from w3levels import wall, level
from descent import descend, ring_start, refine_e
def run(v, v_prev, mode):
    A = wall(0.0); B = wall(-v)
    As, Bs = level(A, 16), level(B, 16); Ae, Be = level(A, 8), level(B, 8)
    z = np.zeros(As.shape)
    first, rounds = (1.5, 6) if mode == "D" else (0.75, 5)
    off_a, ca = descend(As, Bs, z, first, rounds)
    off_b, cb = descend(As, Bs, ring_start(As, Bs, off_a), first, rounds)
    off_c, cc = descend(As, Bs, np.full(As.shape, v_prev / 16.0), first, rounds)
    def up(o): return np.repeat(np.repeat(o, 2, 0), 2, 1)[:Ae.shape[0], :Ae.shape[1]] * 2.0
    prev_e = np.full(Ae.shape, v_prev / 8.0)
    # local centre (D): the coarse candidate with the lowest raw cost among the three
    C = np.stack([ca, cb, cc]); O = np.stack([off_a, off_b, off_c])
    loc = np.take_along_axis(O, C.argmin(0)[None], 0)[0]
    loc = np.where(np.abs(loc) > 1.5, loc, 0.0)
    g = up(loc) if mode == "D" else 0.0
    picks, scores = [], []
    _, sad0 = refine_e(Ae, Be, np.zeros(Ae.shape), R=0)
    seeds = [(off_a, False), (off_b, False), (off_c, True)]
    for o, trusted in seeds:
        r, s = refine_e(Ae, Be, up(o))
        pen = 0.3 * np.abs(r - g)
        if mode == "C": pen = np.minimum(pen, 0.5 * sad0)
        picks.append(r); scores.append(s + pen + (0.5 * np.abs(r - prev_e) if trusted else 0.0))
    if mode == "C":
        r, s = refine_e(Ae, Be, np.zeros(Ae.shape), R=5)
        picks.append(r); scores.append(s + np.minimum(0.3 * np.abs(r), 0.5 * sad0))
    P = np.stack(picks); Sc = np.stack(scores)
    pick = np.take_along_axis(P, Sc.argmin(0)[None], 0)[0]
    tre = v / 8.0; sl8 = (slice(4, -4), slice(12, -12))
    return np.mean(np.abs(pick[sl8] - tre) <= 0.75), np.mean(np.abs(pick[sl8]) <= 0.75)
for mode, label in (("C", "prior capped at 0.5*SAD(0), wide +-5"), ("D", "doubled step + prior centred on the texel's own coarse winner (>1.5 texels)")):
    print("==", mode, label, " E_pick near truth / near zero")
    for v in (16, 20, 24, 28, 32, 34, 36, 38, 40):
        t, zz = run(float(v), float(v) - 1.0, mode)
        print(f"{v:3}  {t:.2f}/{zz:.2f}")
    print()
