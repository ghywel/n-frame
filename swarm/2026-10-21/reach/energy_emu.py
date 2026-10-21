"""The energy channel (tests/coarse_energy.py) added to the 1-D W3 emulation: energy = 4x4-block 2-px gradient magnitude on
dense 2x2 taps at 1/4, separable Gaussian sigma 3 quarter texels (12 px); one sample per 1/16 and 1/8 texel; cost
|dL| + W|dE| (W_S 8, W_E 1). Reports (a) how much of the energy image's variance sits at each scale (frame-level
attenuation of the 32-px grain by the Gaussian), (b) the descents and the 1/8 pick with and without energy."""
import numpy as np
from w3levels import wall, level
TIE = 1e-4; REG = 0.06
def energy(img):
    h, w = img.shape[0] // 4, img.shape[1] // 4
    E = np.zeros((h, w))
    for j in (0, 1):
        for i in (0, 1):
            # taps at quarter-texel centre + (i*2-1, j*2-1) quarter texels -> pixel offsets
            py = 4 * np.arange(h) + 1.5 + (j * 2 - 1) * 4; px = 4 * np.arange(w) + 1.5 + (i * 2 - 1) * 4
            def smp(dy, dx):
                yy = np.clip(np.round(py + dy).astype(int), 0, img.shape[0] - 1); xx = np.clip(np.round(px + dx).astype(int), 0, img.shape[1] - 1)
                return img[yy][:, xx]
            c = smp(0, 0)
            E += np.abs(smp(0, 8) - c) + np.abs(smp(8, 0) - c)
    E /= 4.0
    g = np.exp(-np.arange(-6, 7) ** 2 / 18.0); g /= g.sum()
    E = np.apply_along_axis(lambda r: np.convolve(r, g, "same"), 1, E)
    E = np.apply_along_axis(lambda r: np.convolve(r, g, "same"), 0, E)
    return E
def pick(E, f):   # one sample per level texel (nearest quarter texel to the texel centre)
    s = f // 4; return E[s // 2::s, s // 2::s][: E.shape[0] // s, : E.shape[1] // s]
def cost1d(A, B, d, W):
    L_A, E_A = A; L_B, E_B = B
    h, w = L_A.shape
    xs = np.arange(w)[None, :] + d; x0 = np.floor(xs).astype(int); t = xs - x0
    def rd(img, xx): return np.take_along_axis(img, np.clip(xx, 0, w - 1), 1)
    D = np.abs(L_A - ((1 - t) * rd(L_B, x0) + t * rd(L_B, x0 + 1))) + W * np.abs(E_A - ((1 - t) * rd(E_B, x0) + t * rd(E_B, x0 + 1)))
    S = np.zeros_like(D)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1): S += np.roll(np.roll(D, oy, 0), ox, 1)
    return S
def descend(A, B, start, W, first=0.75, rounds=5):
    best = start.copy(); bc = cost1d(A, B, best, W) + REG * np.abs(best); step = first
    for _ in range(rounds):
        cand, cb = best.copy(), bc.copy()
        for s in (-1.0, 1.0):
            d = best + s * step; c = cost1d(A, B, d, W) + REG * np.abs(d); m = c < cb * (1 - TIE)
            cand = np.where(m, d, cand); cb = np.where(m, c, cb)
        best, bc = cand, cb; step *= 0.5
    return best, bc
def ring(A, B, off_a, W):
    bestc = np.full(off_a.shape, 1e30); st = np.zeros(off_a.shape)
    for o in (-1.0, 1.0):
        d = np.full(off_a.shape, o); c = cost1d(A, B, d, W) + REG; m = (np.abs(d - off_a) >= 0.75) & (c < bestc)
        bestc = np.where(m, c, bestc); st = np.where(m, d, st)
    return st
def refine(A, B, seed, W, R=2):
    best = seed.copy(); bc = cost1d(A, B, seed, W)
    for k in range(-R, R + 1):
        if k == 0: continue
        d = seed + k; c = cost1d(A, B, d, W) + 0.05 * abs(k); m = c < bc * (1 - TIE); best = np.where(m, d, best); bc = np.where(m, c, bc)
    return best, cost1d(A, B, best, W)
def run(v, WS, WE, recentre=False):
    A = wall(0.0); B = wall(-v); EA, EB = energy(A), energy(B)
    S_A = (level(A, 16), pick(EA, 16)); S_B = (level(B, 16), pick(EB, 16)); E_A = (level(A, 8), pick(EA, 8)); E_B = (level(B, 8), pick(EB, 8))
    z = np.zeros(S_A[0].shape)
    oa, _ = descend(S_A, S_B, z, WS); ob, _ = descend(S_A, S_B, ring(S_A, S_B, oa, WS), WS); oc, _ = descend(S_A, S_B, np.full(z.shape, (v - 1) / 16.0), WS)
    tr = v / 16.0; sl = (slice(2, -2), slice(6, -6)); near = lambda x, t: np.mean(np.abs(x[sl] - t) <= 0.5)
    def up(o): return np.repeat(np.repeat(o, 2, 0), 2, 1)[: E_A[0].shape[0], : E_A[0].shape[1]] * 2.0
    g = v / 8.0 if recentre else 0.0; prev = np.full(E_A[0].shape, (v - 1) / 8.0)
    P, Sc = [], []
    for o, trusted in ((oa, False), (ob, False), (oc, True)):
        r, s = refine(E_A, E_B, up(o), WE); P.append(r); Sc.append(s + 0.3 * np.abs(r - g) + (0.5 * np.abs(r - prev) if trusted else 0))
    pk = np.take_along_axis(np.stack(P), np.stack(Sc).argmin(0)[None], 0)[0]; sl8 = (slice(4, -4), slice(12, -12))
    return near(oa, tr), near(ob, tr), near(oc, tr), np.mean(np.abs(pk[sl8] - v / 8.0) <= 0.75), np.mean(np.abs(pk[sl8]) <= 0.75)
if __name__ == "__main__":
    A = wall(0.0); E = energy(A); L = level(A, 4)
    # scale content: variance of row-means after block-averaging at 32 and 128 px, luma vs energy (quarter res: 8 and 32 texels)
    def band(img, s): 
        h, w = img.shape[0] // s * s, img.shape[1] // s * s
        return img[:h, :w].reshape(h // s, s, w // s, s).mean((1, 3))
    for name, img in (("luma@1/4", L), ("energy", E)):
        tot = img.var(); b128 = band(img, 32).var(); b32 = band(img, 8).var() - b128
        print(f"{name}: var total {tot:.5f}  128-px scale {b128/tot:.2f}  32-px scale {b32/tot:.2f}  finer {1-(b32+b128)/tot:.2f}")
    print("\n v   zero  ring  temp  E_pick (near truth/near zero)   [luma only | +energy W_S 8 W_E 1 | +energy, prior on truth]")
    for v in (20, 24, 28, 30, 32, 34, 36, 38, 40):
        a = run(float(v), 0, 0); b = run(float(v), 8, 1); c = run(float(v), 8, 1, True)
        f = lambda r: f"{r[0]:.2f} {r[1]:.2f} {r[2]:.2f} {r[3]:.2f}/{r[4]:.2f}"
        print(f"{v:3}  {f(a)}  |  {f(b)}  |  {f(c)}")
