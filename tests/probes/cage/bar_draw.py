#!/usr/bin/env python3
"""RUN-ON: mac. COMMAND: python3 tests/probes/cage/bar_draw.py --pipeline "$NP_SCRATCH/bar-pipeline" --basin "$NP_SCRATCH/bar-basin" --out DIR
RANDOM BARS (Local, 2026-10-23; the "one unexpected thing" of the day). GPT's guided scene is one hand-picked tuple
(period 9, +6, broad .30 at 512). This draws six with a fixed seed, so that neither of us chose them: a fine period
p in [6, 12] px (drawn from [6, 14], kept only inside the bars pass's 12 px reach of its slower alias v - p), a speed v up to p + 12 and |v - p| < v (so the
smallest-speed prior prefers the alias), fine amplitude in [.06, .2], broad amplitude in [0, .3] and period in
[128, 1024]; never clipping. bar_pipeline.py's frame, crop and read path; High, High + BAR_REDECIDE, + BAR_BASIN
(the shaders bar_pipeline.py and bar_basin.py generated, hashes recorded).

PRE-REGISTERED (before any draw was rendered or printed): per tuple, the share of crop samples where High reads within
.5 px of v and the variant within .5 of v - p (bar_pipeline.py's measure). BAR_BASIN under 0.2% on every draw where
High supplies the correct seed on 1% or more; BAR_REDECIDE over 1% on at least half of those draws. Picture (24 -> 48,
the synthesized half-instants against the analytic truth, the crop): BAR_BASIN not below High by more than 0.5 dB on
any draw. Refuted otherwise; the draws are not re-rolled.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import bar_gpu as gpu
import bar_pipeline as pipe

W, H, N = pipe.W, pipe.H, pipe.N


def draw(seed=20261023, k=6):
    rng = np.random.default_rng(seed); out = []
    while len(out) < k:
        p = int(rng.integers(6, 15)); v = int(rng.integers(1, 13 + p))
        a = round(float(rng.uniform(.06, .2)), 3); b = round(float(rng.uniform(0, .3)), 3); P = int(rng.integers(128, 1025))
        if abs(v - p) < v and p <= 12 and .5 - a - b >= 0 and .5 + a + b <= 1:
            out.append((p, v, a, b, P))
    return out


def source(path, p, v, a, b, P):
    with path.open('wb') as f:
        for n in range(N):
            u = np.arange(W) + .5 - v * n
            line = .5 + a * np.cos(2 * np.pi * (u % p) / p) + b * np.cos(2 * np.pi * u / P)
            f.write(np.broadcast_to(np.rint(line * 65535).astype('<u2')[None, :, None], (H, W, 3)).tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pipeline', type=Path, required=True); ap.add_argument('--basin', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=True); ff = str(Path.home() / 'np-build/ffmpeg/ffmpeg')
    sh = {'high': a.pipeline / 'high0.glsl', 'bars': a.pipeline / 'high1.glsl', 'basin': a.basin / 'basin.glsl'}
    if sh['high'].read_text() != pipe.HIGH.read_text(): raise ValueError('High source changed')
    tail = gpu.shader(6, False); tail = tail[tail.rindex('//!HOOK FRAME_MIX'):]
    for k, s in sh.items(): (out / f'{k}-flow.glsl').write_text(s.read_text() + '\n' + tail)
    rows = []; sl = (slice(None), slice(24, -24), slice(48, -48))
    for i, (p, v, am, b, P) in enumerate(draw()):
        src = out / f'draw{i}.rgb48'; source(src, p, v, am, b, P)
        fx = {k: pipe.render(ff, out, f'draw{i}_flow_{k}', src, out / f'{k}-flow.glsl')[..., 0][sl] for k in sh}
        seed = abs(fx['high'] - v) < .5
        flips = {k: float(np.mean(seed & (abs(fx[k] - (v - p)) < .5))) for k in ['bars', 'basin']}
        u = np.arange(W)[None, :] + .5 - v * np.arange(6, 26)[:, None] / 2
        truth = .5 + am * np.cos(2 * np.pi * (u % p) / p) + b * np.cos(2 * np.pi * u / P)
        psnr = {}
        for k, s in sh.items():
            im = pipe.render(ff, out, f'draw{i}_picture_{k}', src, s, 48, False)
            e = (im - truth[:, None, :]) ** 2
            if np.sqrt(e[::2][sl].max()) > .001: raise ValueError('passthrough misaligned')
            psnr[k] = float(-10 * np.log10(e[1::2][sl].mean()))
        row = {'draw': i, 'period': p, 'speed': v, 'alias': v - p, 'fine': am, 'broad': b, 'broad_period': P,
               'high_correct': float(seed.mean()), 'flips': flips, 'psnr': psnr,
               'median_x': {k: float(np.median(x)) for k, x in fx.items()}}
        rows.append(row); print(json.dumps(row), flush=True)
    seeded = [r for r in rows if r['high_correct'] >= .01]
    held = (all(r['flips']['basin'] < .002 for r in seeded) and
            sum(r['flips']['bars'] > .01 for r in seeded) * 2 >= len(seeded) and
            all(r['psnr']['basin'] - r['psnr']['high'] >= -.5 for r in rows))
    res = {'rows': rows, 'seeded_draws': len(seeded), 'prediction_held': held,
           'sha256': {k: hashlib.sha256(s.read_bytes()).hexdigest() for k, s in sh.items()}}
    (out / 'results.json').write_text(json.dumps(res, indent=2) + '\n')
    print('seeded draws', len(seeded), 'PREDICTION', 'HELD' if held else 'REFUTED', flush=True)
    return 0 if held else 3


if __name__ == '__main__':
    raise SystemExit(main())
