# 1-D toy of a point-sampled coarse level (stride 8) matching a translated texture.
# Stock: both frames decimated on the SAME fixed grid, candidate shifts read by linear interp of B's coarse row.
# Phase-exact: B's taps fetched from the full-res row at the candidate's exact offset (no fixed-grid decimation of B).
# Also: PIV-style peak ratio Q = second-best SAD / best SAD (second-best at least 3 px from the best).
import numpy as np
rng = np.random.default_rng(1)
N = 4096; x = np.arange(N); S = 8
def smooth(s, sigma=1.0):
    k = np.arange(-4, 5); g = np.exp(-k**2/(2*sigma**2)); g /= g.sum()
    return np.convolve(s, g, mode='same')
bars = ((x % 14) < 7).astype(float)
mod = 0.5 + 0.5*((x % 28) < 14)
textures = {
    'print14/28': smooth(bars*mod, 1.0),
    'random':     smooth(rng.random(N), 1.0),
}
speeds = [3, 4, 5, 6, 7, 8, 9, 11, 13, 15, 16, 17, 19]
cands = np.arange(-32, 33)           # px
i0, W = 1024//S, 64                  # window of 64 coarse texels
idx = np.arange(i0, i0+W)
def sad_stock(A, B, v):
    Ac = A[::S]; Bc = B[::S]
    out = []
    for c in cands:
        pos = idx + c/S
        Bi = np.interp(pos, np.arange(len(Bc)), Bc)
        out.append(np.abs(Ac[idx] - Bi).sum())
    return np.array(out)
def sad_exact(A, B, v):
    out = []
    for c in cands:
        out.append(np.abs(A[idx*S] - B[idx*S + c]).sum())
    return np.array(out)
def q_ratio(s):
    b = s.argmin(); far = np.abs(cands - cands[b]) >= 3
    return s[far].min() / max(s[b], 1e-9)
def classify(c, v, P):
    if c == v: return 'TRUE '
    if (c - v) % P == 0: return 'alias'
    return 'WRONG'
for name, A in textures.items():
    P = 28 if 'print' in name else 10**9
    print(f"\n== {name} ==   v | stock argmin  | phase-exact argmin | Q stock | Q exact")
    for v in speeds:
        B = np.roll(A, v) + rng.normal(0, 0.005, N)   # B(x) = A(x - v) + noise
        ss, se = sad_stock(A, B, v), sad_exact(A, B, v)
        cs, ce = cands[ss.argmin()], cands[se.argmin()]
        print(f"  {v:3d} | {cs:4d} {classify(cs, v, P)} | {ce:4d} {classify(ce, v, P)}          | {q_ratio(ss):6.2f} | {q_ratio(se):6.2f}")
