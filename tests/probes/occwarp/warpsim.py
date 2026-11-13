#!/usr/bin/env python3
"""CPU replay of the final warp on High's own dumped flow fields (2026-11-13; no GPU).

    warpsim.py <suite-root> <dump-root> <case> [<case> ...]

For each case: the source frames and exact truth from the motionstress suite, the flow fields from flowdump.py
(fab = A -> B on A's grid, fba = B -> A on B's grid, both in px as the final pass reads them, per output frame), and a
set of candidate warps evaluated at every interior synthesized output. 'high' replays the shipped final pass and is
checked against High's real render first (the instrument check: the replay must reproduce the picture). Scores are the
suite's: PSNR of the mean squared error over the ROI and over the feature mask, plus the suite's worst-1% ROI RMS and a
temporal measure, the mean absolute frame-to-frame change of the ERROR inside the ROI (a snap or flicker shows there).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'motionstress'))
import scenes  # noqa: E402
if os.environ.get('PHOTO_PATCH'):                      # GPT's photographic cases: the external crop, never committed
    import photo  # noqa: E402
    photo.configure(os.environ['PHOTO_PATCH'])
    _analytic = scenes.render
    scenes.render = lambda name, t: photo.render(name, t) if name in photo.CASES else _analytic(name, t)

FF = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
H, W = scenes.H, scenes.W
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def read(path, n):
    r = subprocess.run([FF, '-nostdin', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'gray16le', '-'], capture_output=True)
    return np.frombuffer(r.stdout, '<u2').reshape(n, H, W).astype(np.float32) / 65535


def samp(img, x, y):
    return map_coordinates(img, [y, x], order=1, mode='nearest')


def sm(lo, hi, v):
    t = np.clip((v - lo) / np.maximum(hi - lo, 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def warp_high(a, b, fab, fba, sup, t):
    """The shipped final pass: A's flow at the output pixel for both endpoints, and the coherence fallback."""
    vx, vy = fab[..., 0], fab[..., 1]
    warped = (1 - t) * samp(a, XX - t * vx, YY - t * vy) + t * samp(b, XX + (1 - t) * vx, YY + (1 - t) * vy)
    un = (1 - sm(0.50, 0.70, sup[..., 0])) * (1 - sm(0.40, 0.55, sup[..., 1])) * (1 - sm(0.50, 1.0, sup[..., 2]))
    return warped * (1 - un) + un * ((1 - t) * a + t * b)


def hyp(a, b, fab, fba, h, t, lo, hi):
    """One hypothesis h (px, per pixel): both endpoint samples and each side's validity, its own frame's flow there agreeing."""
    hx, hy = h[..., 0], h[..., 1]
    qax, qay = XX - t * hx, YY - t * hy
    qbx, qby = XX + (1 - t) * hx, YY + (1 - t) * hy
    wa = 1 - sm(lo, hi, np.hypot(samp(fab[..., 0], qax, qay) - hx, samp(fab[..., 1], qax, qay) - hy))
    wb = 1 - sm(lo, hi, np.hypot(-samp(fba[..., 0], qbx, qby) - hx, -samp(fba[..., 1], qbx, qby) - hy))
    return samp(a, qax, qay), samp(b, qbx, qby), wa, wb


def warp_occ(a, b, fab, fba, sup, t, lo=1.0, hi=2.0, clo=4.0, chi=8.0, one_sided=True, base_fn=None):
    """Two hypotheses (A's opinion at the pixel, B's opinion at the pixel); two-sided-valid first, then one-sided, else
    High; engaged only where the two opinions disagree (the conflict gate), so elsewhere the output is High's exactly."""
    base = (base_fn or warp_high)(a, b, fab, fba, sup, t)
    conflict = sm(clo, chi, np.hypot(fab[..., 0] + fba[..., 0], fab[..., 1] + fba[..., 1]))
    if not conflict.any():
        return base
    ca1, cb1, wa1, wb1 = hyp(a, b, fab, fba, fab, t, lo, hi)
    ca2, cb2, wa2, wb2 = hyp(a, b, fab, fba, -fba, t, lo, hi)
    two1, two2 = wa1 * wb1, wa2 * wb2
    c1 = (1 - t) * ca1 + t * cb1
    c2 = (1 - t) * ca2 + t * cb2
    two = two1 + (1 - two1) * two2
    col2 = np.where(two > 1e-6, (two1 * c1 + (1 - two1) * two2 * c2) / np.maximum(two, 1e-6), 0)
    res = two * col2 + (1 - two) * base
    if one_sided:
        # one side only: the sample whose own frame agrees with the hypothesis it was taken under
        s1 = np.where(wa1 >= wb1, ca1, cb1); o1 = np.maximum(wa1, wb1)
        s2 = np.where(wa2 >= wb2, ca2, cb2); o2 = np.maximum(wa2, wb2)
        one = np.maximum(o1, o2); cs = np.where(o1 >= o2, s1, s2)
        res = two * col2 + (1 - two) * (one * cs + (1 - one) * base)
    return conflict * res + (1 - conflict) * base


def fsamp(f, x, y):
    return np.stack([samp(f[..., 0], x, y), samp(f[..., 1], x, y)], -1)


def candidates(fab, fba, t, which, R):
    """The candidate vectors at each output pixel (px, A -> B sense). c0 is always High's own (A's flow at the pixel)."""
    c0 = fab
    out = [c0]
    if 'b' in which:                                   # B's opinion at the pixel
        out.append(-fba)
    if 'g' in which:                                   # gathered: A's flow where c0 says the content came from (GPT's inverse step)
        out.append(fsamp(fab, XX - t * c0[..., 0], YY - t * c0[..., 1]))
        c1 = -fba
        out.append(-fsamp(fba, XX + (1 - t) * c1[..., 0], YY + (1 - t) * c1[..., 1]))
    if 'z' in which:
        out.append(np.zeros_like(c0))
    if 'r' in which:                                   # the neighbourhood's motions, R px away: beyond a fattened flow's rim
        for dx, dy in ((R, 0), (-R, 0), (0, R), (0, -R)):
            out.append(fsamp(fab, XX + dx, YY + dy))
    return out


def bilateral_cost(a, b, c, t, taps, step):
    """Mean absolute endpoint difference over a patch, the SAME vector for every tap (as a shader pass computes it)."""
    acc = 0.0
    r = taps // 2
    for j in range(-r, r + 1):
        for i in range(-r, r + 1):
            x, y = XX + i * step, YY + j * step
            acc = acc + np.abs(samp(a, x - t * c[..., 0], y - t * c[..., 1]) - samp(b, x + (1 - t) * c[..., 0], y + (1 - t) * c[..., 1]))
    return acc / (taps * taps)


def self_cost(img, x0, y0, d, taps=3):
    """How well a frame matches ITSELF displaced by d around (x0, y0): small where d is a period of the local pattern."""
    acc = 0.0
    r = taps // 2
    for j in range(-r, r + 1):
        for i in range(-r, r + 1):
            acc = acc + np.abs(samp(img, x0 + i, y0 + j) - samp(img, x0 + i + d[..., 0], y0 + j + d[..., 1]))
    return acc / (taps * taps)


def warp_bcv(a, b, fab, fba, sup, t, which='bgzr', R=24.0, taps=3, step=1.0, kappa=0.5, eps=2.0 / 255, soft=True, stats=None,
             own=False, alias=False, doubt=()):
    """Bilateral candidate vote: High's vector is replaced only by a candidate whose endpoints agree at least 1/kappa
    times better AND by more than eps; the replacement fades in with the size of the improvement (soft)."""
    cs = candidates(fab, fba, t, which, R)
    cost = np.stack([bilateral_cost(a, b, c, t, taps, step) for c in cs])
    k = np.argmin(cost, 0)
    best = np.take_along_axis(cost, k[None], 0)[0]
    v = np.take_along_axis(np.stack(cs), k[None, ..., None], 0)[0]
    c0 = cost[0]
    for r in doubt:      # THE SUB-PIXEL DOUBT: High's vector is judged by the best of itself and its neighbours r px away,
        #                  so a vector right to a fraction of a pixel is not out-voted on thin detail by a look-alike
        for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
            c0 = np.minimum(c0, bilateral_cost(a, b, fab + np.array([dx, dy], np.float32), t, taps, step))
    if soft:   # full replacement once the best costs under kappa/2 of High's; none at kappa; and only beyond the noise floor
        w = (1 - sm(0.5 * kappa, kappa, best / np.maximum(c0, 1e-6))) * sm(eps, 2 * eps, c0 - best)
    else:
        w = ((best < kappa * c0) & (c0 - best > eps)).astype(np.float32)
    if own:      # the winner must be OWNED at both endpoints: each frame's own flow there agrees with it (two-sided, so
        #          a chance match in a region one frame cannot see is refused)
        qax, qay = XX - t * v[..., 0], YY - t * v[..., 1]
        qbx, qby = XX + (1 - t) * v[..., 0], YY + (1 - t) * v[..., 1]
        da = np.hypot(samp(fab[..., 0], qax, qay) - v[..., 0], samp(fab[..., 1], qax, qay) - v[..., 1])
        db = np.hypot(-samp(fba[..., 0], qbx, qby) - v[..., 0], -samp(fba[..., 1], qbx, qby) - v[..., 1])
        if own == 'rel':     # nearer the winner than halfway to High's vector (the fields are good to a few px, not to one)
            tol = np.maximum(0.5 * np.hypot(v[..., 0] - fab[..., 0], v[..., 1] - fab[..., 1]), 1.0)
            w = w * (1 - sm(0.5, 1.0, da / tol)) * (1 - sm(0.5, 1.0, db / tol))
        else:
            w = w * (1 - sm(1.0, 2.0, da)) * (1 - sm(1.0, 2.0, db))
    if alias:    # and not a PERIOD of the picture: a frame that matches itself under the two vectors' difference but not
        #          under half or a third of it is periodic along it (a flat patch matches under all three and is harmless)
        d = v - fab
        per = 0.0
        for img, x0, y0 in ((a, XX - t * fab[..., 0], YY - t * fab[..., 1]), (b, XX + (1 - t) * fab[..., 0], YY + (1 - t) * fab[..., 1])):
            s1 = self_cost(img, x0, y0, d)
            s23 = np.maximum(self_cost(img, x0, y0, d / 2), self_cost(img, x0, y0, d / 3))
            per = np.maximum(per, (1 - sm(0.5 * kappa * c0, kappa * c0, s1)) * sm(eps, 2 * eps, s23 - 2 * s1))
        w = w * (1 - per)
    if stats is not None:
        stats.append(float((w > 0.5).mean()))
    hi_ = (1 - t) * samp(a, XX - t * fab[..., 0], YY - t * fab[..., 1]) + t * samp(b, XX + (1 - t) * fab[..., 0], YY + (1 - t) * fab[..., 1])
    new = (1 - t) * samp(a, XX - t * v[..., 0], YY - t * v[..., 1]) + t * samp(b, XX + (1 - t) * v[..., 0], YY + (1 - t) * v[..., 1])
    warped = hi_ + w * (new - hi_)                      # blend the PICTURES, not the vectors: no in-between vector is ever sampled
    un = (1 - sm(0.50, 0.70, sup[..., 0])) * (1 - sm(0.40, 0.55, sup[..., 1])) * (1 - sm(0.50, 1.0, sup[..., 2]))
    return warped * (1 - un) + un * ((1 - t) * a + t * b)


VARIANTS = {
    'high': warp_high,
    'occ': warp_occ,
    'bcv-g': lambda *a, **k: warp_bcv(*a, which='g', **k),          # the gathered candidates only (GPT's inverse-data idea)
    'bcv-bg': lambda *a, **k: warp_bcv(*a, which='bg', **k),
    'bcv-bgz': lambda *a, **k: warp_bcv(*a, which='bgz', **k),
    'bcv': warp_bcv,                                                # all: B's opinion, gathered, zero, the ring
    'bcv-hard': lambda *a, **k: warp_bcv(*a, soft=False, **k),
    'vote2': lambda *a, **k: warp_bcv(*a, which='bg', own='rel', alias=True, **k),    # relative ownership and the period guard
    'vote2-own': lambda *a, **k: warp_bcv(*a, which='bg', own='rel', **k),
    'vote2-alias': lambda *a, **k: warp_bcv(*a, which='bg', alias=True, **k),
    'vote3': lambda *a, **k: warp_bcv(*a, which='bg', doubt=(0.5,), **k),             # the sub-pixel doubt, half a pixel
    'vote3b': lambda *a, **k: warp_bcv(*a, which='bg', doubt=(0.5, 1.0), **k),        # half and one pixel
}


def run(suite, dump, case, variants):
    d = suite / case
    n = scenes.SOURCE_FRAMES
    src, truth = read(d / 'source.mkv', n), read(d / 'truth.mkv', n * 5 // 2)
    real = read(d / 'high.mkv', n * 5 // 2)
    fab, fba, sup = (np.load(dump / case / f'{x}.npy', mmap_mode='r') for x in ('fab', 'fba', 'sup'))
    res = {v: dict(roi=[], feat=[], tail=[], err=[]) for v in variants}
    check = 0.0
    for m in range(5, len(truth) - 5):
        if m % 5 == 0:
            continue
        k, t = int(np.floor(m * 0.4 + 1e-6)), (m * 0.4) % 1
        _, roi, feat = scenes.render(case, m * 0.4)
        for v in variants:
            out = VARIANTS[v](src[k], src[k + 1], np.asarray(fab[m]), np.asarray(fba[m]), np.asarray(sup[m]), t)
            if v == 'high':
                check = max(check, float(np.sqrt(np.mean((out - real[m]) ** 2)) * 255))
            e = (out - truth[m]) ** 2
            r = res[v]
            r['roi'].append(e[roi].mean()); r['feat'].append(e[feat].mean())
            reg = np.sort(e[roi]); r['tail'].append(reg[-max(1, len(reg) // 100):].mean())
            r['err'].append((out - truth[m])[roi].copy() if False else float(np.abs(out - truth[m])[roi].mean()))
    p = lambda x: float(-10 * np.log10(max(np.mean(x), 1e-16)))
    row = {v: dict(roi=p(r['roi']), feat=p(r['feat']), tail_dn=float(np.sqrt(np.mean(r['tail'])) * 255),
                   flicker=float(np.mean(np.abs(np.diff(r['err']))) * 255)) for v, r in res.items()}
    row['_replay_rms_dn'] = check
    return row


def main():
    suite, dump = Path(sys.argv[1]), Path(sys.argv[2])
    variants = os.environ.get('VARIANTS', ','.join(VARIANTS)).split(',')
    out = {}
    for case in sys.argv[3:]:
        row = out[case] = run(suite, dump, case, variants)
        print(f"{case}: replay of High against its real render {row['_replay_rms_dn']:.3f} DN RMS (worst frame)")
        for v in variants:
            r = row[v]
            print(f"   {v:10s} ROI {r['roi']:6.2f}  feature {r['feat']:6.2f}  worst-1% {r['tail_dn']:6.2f} DN  flicker {r['flicker']:.3f}", flush=True)
    (dump / 'warpsim.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
