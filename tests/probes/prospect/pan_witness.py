#!/usr/bin/env python3
"""Exploratory rigid-pan witness AFTER discovery, not a fitted ranking guard.

pan_witness.py ROOT FRAME: ROOT contains ref/high/linear FFV1 videos. Fit a
single global translation between endpoints A,C, without looking at B. Use
half of it to predict withheld B. Compare in the common interior. Adjacent
fits A->B and B->C check constant velocity independently of shader flow.
CPU roll and affine/subpixel oracles precede footage. Small global search,
quarter-pixel refinement; periodic or nonrigid footage can invalidate this
model. Output retained even if it refutes the proposed rigid-pan explanation.
"""
from pathlib import Path
import subprocess
import sys
import numpy as np
import reconstruct as r


def extract(p, ns):
    meta = r.probe(p); w, h = meta['width'], meta['height']
    expr = '+'.join(f'eq(n,{n})' for n in sorted(ns))
    proc = subprocess.run([r.FF, '-nostdin', '-v', 'error', '-i', str(p), '-vf',
                           f"select='{expr}',extractplanes=y", '-fps_mode', 'passthrough',
                           '-pix_fmt', 'gray', '-f', 'rawvideo', '-'], capture_output=True, check=True)
    a = np.frombuffer(proc.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)
    if len(a) != len(ns):
        raise ValueError('extraction count mismatch')
    return a


def warped(a, dx, dy, margin=32, stride=2):
    h, w = a.shape
    yy, xx = np.mgrid[margin:h-margin:stride, margin:w-margin:stride]
    x, y = xx-dx, yy-dy
    ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x-ix, y-iy
    return ((1-fx)*(1-fy)*a[iy, ix] + fx*(1-fy)*a[iy, ix+1] +
            (1-fx)*fy*a[iy+1, ix] + fx*fy*a[iy+1, ix+1])


def fit(a, b):
    h, w = a.shape; crop = b[32:h-32:2, 32:w-32:2]
    trials = []
    for dy in range(-24, 25):
        for dx in range(-24, 25):
            cost = float(np.mean((a[32-dy:h-32-dy:2, 32-dx:w-32-dx:2]-crop)**2))
            trials.append((cost, dx, dy))
    _, dx, dy = min(trials)
    fine = [(r.rms(warped(a, x, y), crop), x, y)
            for x in np.arange(dx-.75, dx+1, .25) for y in np.arange(dy-.75, dy+1, .25)]
    err, x, y = min(fine)
    return dict(dx=float(x), dy=float(y), rms=err, search_boundary=abs(dx)==24 or abs(dy)==24)


def photometric(a, b):
    x, y = a[32:-32:2,32:-32:2].astype(float), b[32:-32:2,32:-32:2].astype(float)
    gain = float(np.mean((x-x.mean())*(y-y.mean())) / max(np.var(x), 1e-8))
    bias = float(y.mean()-gain*x.mean())
    err, unchanged = r.rms(gain*x+bias, y), r.rms(x,y)
    return dict(gain=gain, bias=bias, rms=err, unchanged_rms=unchanged,
                fraction_change_explained=1-err**2/max(unchanged**2,1e-8))


def main(root, n):
    yy, xx = np.indices((160, 192)); rng = np.random.default_rng(20261023)
    a = rng.uniform(30, 220, (160, 192)).astype(np.float32)
    c = fit(a, np.roll(a, (2, -3), (0, 1)))
    assert c['dx'] == -3 and c['dy'] == 2 and c['rms'] == 0
    affine = (70+xx/4+yy/8).astype(np.float32)
    assert r.rms(warped(affine, 1.25, -.5), affine[32:-32:2,32:-32:2]-.25) == 0
    light = photometric(a, 1.1*a+3)
    assert abs(light['gain']-1.1)<1e-5 and abs(light['bias']-3)<1e-4 and light['rms']<1e-4
    a, b, c = extract(root/'ref.mkv', [n-1, n, n+1])
    ab, bc, ac = fit(a, b), fit(b, c), fit(a, c)
    predicted = (warped(a, ac['dx']/2, ac['dy']/2) + warped(c, -ac['dx']/2, -ac['dy']/2))/2
    target = b[32:-32:2,32:-32:2]
    high = extract(root/'high.mkv', [n])[0][32:-32:2,32:-32:2]
    linear = extract(root/'linear.mkv', [n])[0][32:-32:2,32:-32:2]
    result = dict(frame=n, a_to_b=ab, b_to_c=bc, a_to_c=ac,
                  photometric_a_to_b=photometric(a,b), photometric_b_to_c=photometric(b,c),
                  photometric_a_to_c=photometric(a,c),
                  adjacent_displacement_disagreement=float(np.hypot(ab['dx']-bc['dx'], ab['dy']-bc['dy'])),
                  endpoint_only_pan_rms=r.rms(predicted, target), high_rms=r.rms(high, target),
                  linear_rms=r.rms(linear, target), controls='integer roll and affine subpixel passed',
                  domain='32-pixel common interior, stride 2, gamma-coded luma; exploratory')
    r.save(root/f'pan-{n}.json', result)
    print(result)


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(), int(sys.argv[2]))
