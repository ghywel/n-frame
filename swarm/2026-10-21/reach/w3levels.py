"""Offline (CPU) per-level cost surfaces for W3's wall texture under a pure horizontal pan.
Emulates the shader's point-sampled pyramid (one bilinear tap at each level texel's centre = the mean of the
central 2x2 pixels of the footprint) and its 3x3-texel SAD, per level, for a shift of v px. For each level and v:
  - the mean cost over texels at every candidate shift (half-texel steps, +-R texels), its argmin;
  - the share of texels whose own per-texel argmin lies within 0.5 texel of the truth, and within 0.5 of zero.
No GPU: numpy only. Texture per tests/scenes.sh W3 (geq, three cell sizes 128/32/4 summed)."""
import numpy as np, sys
W, H = 1280, 720
PAD = 200
def cells(X, Y, c, a, b, m):
    return np.mod(np.floor(np.abs(np.sin(np.floor(X / c) * a + np.floor(Y / c) * b)) * m), 256.0)
def wall(x0):
    ys, xs = np.mgrid[0:H, 0:W + 2 * PAD].astype(np.float64)
    X = xs + x0 - PAD; Y = ys
    lum = 0.25 * cells(X, Y, 128, 12.9898, 78.233, 43758.5453) + 0.35 * cells(X, Y, 32, 39.3468, 11.135, 24634.6345) \
        + 0.40 * cells(X, Y, 4, 12.9898, 78.233, 43758.5453)
    return np.clip(np.round(lum), 0, 255) / 255.0
def level(img, f):
    # point sample at each f x f footprint's centre: bilinear at pixel coord f*i + f/2 - 0.5 -> mean of 2x2
    h, w = img.shape[0] // f, img.shape[1] // f
    c = f // 2
    return 0.25 * (img[c-1:h*f:f, c-1:w*f:f] + img[c:h*f:f, c-1:w*f:f] + img[c-1:h*f:f, c:w*f:f] + img[c:h*f:f, c:w*f:f])[:h, :w]
def sad3(A, B, dx_tex):
    # 3x3 window SAD of A against B shifted by dx_tex (texels, may be half): bilinear read of B
    h, w = A.shape
    xs = np.arange(w) + dx_tex
    x0 = np.floor(xs).astype(int); t = xs - x0
    def rd(img, xx):
        xx = np.clip(xx, 0, w - 1); return img[:, xx]
    Bs = (1 - t) * rd(B, x0) + t * rd(B, x0 + 1)
    D = np.abs(A - Bs)
    S = np.zeros_like(D)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            S += np.roll(np.roll(D, oy, 0), ox, 1)
    return S
def run(v, f, R):
    A = wall(0.0); B = wall(-v)   # the wall moves left by v px in B? W3: x = -(192t+192t^2): the wall slides left, content moves -v. Use B(x) = A(x - v) i.e. content shifted right by v: wall(x0=-v) gives X = xs - v.
    As = level(A, f); Bs = level(B, f)
    truth = v / f
    cands = np.arange(-R, R + 0.001, 0.5)
    costs = []
    for d in cands:
        S = sad3(As, Bs, d)
        costs.append(S[2:-2, 2 * R // 1 + 4:-(2 * R // 1 + 4)])   # interior
    costs = np.stack(costs)   # (ncand, h, w)
    mean = costs.mean(axis=(1, 2))
    am = costs.argmin(axis=0)
    best = cands[am]
    near_truth = np.mean(np.abs(best - truth) <= 0.5)
    near_zero = np.mean(np.abs(best) <= 0.5)
    i_true = int(np.argmin(np.abs(cands - truth)))
    i_zero = int(np.argmin(np.abs(cands)))
    return cands[mean.argmin()], mean[i_true], mean[i_zero], mean.min(), near_truth, near_zero, cands, mean
if __name__ == "__main__":
    print("level  v_px  truth_tex  frame-argmin  meancost@truth  @zero  min   share-texel-argmin-near-truth  near-zero")
    for f, R in ((16, 4), (8, 8), (4, 12)):
        for v in (12, 20, 24, 30, 32, 37, 40):
            am, ct, cz, cm, nt, nz, cands, mean = run(float(v), f, R)
            print(f"1/{f:<3} {v:4}  {v/f:7.2f}    {am:6.2f}       {ct:.4f}        {cz:.4f} {cm:.4f}   {nt:5.2f}  {nz:5.2f}")
        print()
