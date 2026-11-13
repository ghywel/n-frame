#!/usr/bin/env python3
"""CPU test of FLOW_SHARPEN on High's dumped flow fields (2026-11-13; no GPU).

    sharpen_sim.py <suite-root> <dump-root> <case> [...]        PHOTO_PATCH=<npy> for GPT's photographic cases

High's half-resolution flow is right inside a moving object and FATTENED about 30 px into the background around it
(the ring the final picture shows). The variational passes cannot repair that: the true vector is tens of pixels from
the fattened one, outside any linearisation. FLOW_SHARPEN is a discrete re-selection, per half-resolution texel of each
frame's own field: the texel's vector against zero and the vectors found R texels away in eight directions (beyond the
fattened rim), each scored by the texel's OWN match (a small patch of this frame against the other frame displaced);
a candidate replaces the vector only where it matches at least twice as well and by more than the noise. Every texel is
asked where IT went, so a small object passing over uniform ground cannot be mistaken for the ground (the trap a
bilateral test falls into). Then the shipped final pass and the vote are replayed on the sharpened fields.
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates, zoom

import warpsim as ws

H, W = ws.H, ws.W
hy, hx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)


def half(img):
    return img.reshape(H // 2, 2, W // 2, 2).mean((1, 3))


def hs(img, x, y):
    return map_coordinates(img, [y, x], order=1, mode='nearest')


def cost(a_h, b_h, v, taps):
    """Mean absolute difference of a patch of a_h against b_h displaced by v (px, full-res units), one vector per patch."""
    r = taps // 2
    acc = 0.0
    for j in range(-r, r + 1):
        for i in range(-r, r + 1):
            acc = acc + np.abs(hs(a_h, hx + i, hy + j) - hs(b_h, hx + i + v[..., 0] / 2, hy + j + v[..., 1] / 2))
    return acc / (taps * taps)


def sharpen(f_h, a_h, b_h, radii=(8, 16), taps=3, kappa=0.5, eps=2.0 / 255, zero=True, stats=None, g_h=None, occ_lo=4.0):
    cands = [f_h]
    if zero:
        cands.append(np.zeros_like(f_h))
    for R in radii:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            cands.append(np.stack([hs(f_h[..., 0], hx + dx * R, hy + dy * R), hs(f_h[..., 1], hx + dx * R, hy + dy * R)], -1))
    costs = np.stack([cost(a_h, b_h, c, taps) for c in cands])
    k = np.argmin(costs, 0)
    best = np.take_along_axis(costs, k[None], 0)[0]
    v = np.take_along_axis(np.stack(cands), k[None, ..., None], 0)[0]
    take = (best < kappa * costs[0]) & (costs[0] - best > eps)
    out = np.where(take[..., None], v, f_h)
    if g_h is not None:
        # THE UNMATCHED TEXEL (visible in this frame only): no candidate matches, so the data cannot choose. Take the
        # candidate that EXPLAINS the failure: one whose landing place in the other frame belongs to a different motion
        # (the other frame's own flow there, reversed, is far from the candidate): "this went under that".
        unmatched = (~take) & (costs[0] > 3 * eps) & (best > kappa * costs[0])
        C = np.stack(cands)
        d = np.stack([np.hypot(-hs(g_h[..., 0], hx + c[..., 0] / 2, hy + c[..., 1] / 2) - c[..., 0],
                               -hs(g_h[..., 1], hx + c[..., 0] / 2, hy + c[..., 1] / 2) - c[..., 1]) for c in cands])
        j = np.argmax(d[1:], 0) + 1                      # never the texel's own vector
        dj = np.take_along_axis(d, j[None], 0)[0]
        vj = np.take_along_axis(C, j[None, ..., None], 0)[0]
        occ = unmatched & (dj > occ_lo) & (d[0] < 0.5 * dj)   # its own vector's story is "should have matched"; the other's is "covered"
        out = np.where(occ[..., None], vj, out)
        take = take | occ
    if stats is not None:
        stats.append(float(take.mean()))
    return out


def up(f_h):
    """Half-res field back to the full-res grid, bilinear, as the final pass reads it."""
    x = (ws.XX + 0.5) / 2 - 0.5
    y = (ws.YY + 0.5) / 2 - 0.5
    return np.stack([hs(f_h[..., 0], x, y), hs(f_h[..., 1], x, y)], -1)


def run(suite, dump, case, save=None):
    d = suite / case
    n = ws.scenes.SOURCE_FRAMES
    src, truth = ws.read(d / 'source.mkv', n), ws.read(d / 'truth.mkv', n * 5 // 2)
    fab, fba, sup = (np.load(dump / case / f'{x}.npy', mmap_mode='r') for x in ('fab', 'fba', 'sup'))
    names = ('high', 'vote', 'sharp+vote', 'sharp2+occ', 'sharp2+occ+vote')
    res = {v: dict(roi=[], feat=[], err=[]) for v in names}
    cache = {}
    stats = []
    for m in range(5, len(truth) - 5):
        if m % 5 == 0:
            continue
        k, t = int(np.floor(m * 0.4 + 1e-6)), (m * 0.4) % 1
        a, b = src[k], src[k + 1]
        FA, FB, SU = np.asarray(fab[m]), np.asarray(fba[m]), np.asarray(sup[m])
        if k not in cache:
            a_h, b_h = half(a), half(b)
            fa_h = np.stack([half(FA[..., 0]), half(FA[..., 1])], -1)
            fb_h = np.stack([half(FB[..., 0]), half(FB[..., 1])], -1)
            sa, sb = sharpen(fa_h, a_h, b_h, stats=stats), sharpen(fb_h, b_h, a_h, stats=stats)
            # second round with the unmatched rule, each field against the other's first-round result
            ta, tb = sharpen(sa, a_h, b_h, g_h=sb), sharpen(sb, b_h, a_h, g_h=sa)
            cache = {k: (up(sa), up(sb), up(ta), up(tb))}
        SA, SB, TA, TB = cache[k]
        _, roi, feat = ws.scenes.render(case, m * 0.4)
        outs = dict(high=ws.warp_high(a, b, FA, FB, SU, t), vote=ws.warp_bcv(a, b, FA, FB, SU, t, which='bg'))
        outs['sharp+vote'] = ws.warp_bcv(a, b, SA, SB, SU, t, which='bg')
        outs['sharp2+occ'] = ws.warp_occ(a, b, TA, TB, SU, t)
        outs['sharp2+occ+vote'] = ws.warp_occ(a, b, TA, TB, SU, t, base_fn=lambda *q: ws.warp_bcv(*q, which='bg'))
        for v, o in outs.items():
            e = (o - truth[m]) ** 2
            res[v]['roi'].append(e[roi].mean()); res[v]['feat'].append(e[feat].mean())
            res[v]['err'].append(float(np.abs(o - truth[m])[roi].mean()))
        if save and m == save[0]:
            ys, xs = np.where(roi)
            y0, y1, x0, x1 = max(ys.min() - 20, 0), min(ys.max() + 20, H), max(xs.min() - 30, 0), min(xs.max() + 30, W)
            c = lambda z: np.clip(z[y0:y1, x0:x1], 0, 1)
            top = np.hstack([c(truth[m])] + [c(outs[v]) for v in names] + [c((FA[..., 0] + 4) / 40), c((TA[..., 0] + 4) / 40)])
            bot = np.hstack([c(truth[m]) * 0] + [c(np.abs(outs[v] - truth[m]) * 4) for v in names] + [c((-FB[..., 0] + 4) / 40), c((-TB[..., 0] + 4) / 40)])
            img = (np.vstack([top, bot]) * 255).astype(np.uint8)
            subprocess.run([ws.FF, '-nostdin', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'gray', '-video_size',
                            f'{img.shape[1]}x{img.shape[0]}', '-i', '-', '-frames:v', '1', str(save[1])], input=img.tobytes())
    p = lambda x: float(-10 * np.log10(max(np.mean(x), 1e-16)))
    print(f"{case}: texels re-selected {100 * np.mean(stats):.2f}%")
    for v in names:
        r = res[v]
        print(f"   {v:11s} ROI {p(r['roi']):6.2f}  feature {p(r['feat']):6.2f}  flicker {np.mean(np.abs(np.diff(r['err']))) * 255:.3f}", flush=True)


if __name__ == '__main__':
    suite, dump = Path(sys.argv[1]), Path(sys.argv[2])
    out = Path(os.path.expanduser('~/np-scratch-int/motion-20261113/cpu'))
    for case in sys.argv[3:]:
        run(suite, dump, case, save=(int(os.environ.get('SAVE_M', '17')), out / f'sharp_{case}.png'))
