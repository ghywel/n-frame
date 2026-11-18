#!/usr/bin/env python3
"""How much of the barn's corrugated wall a field reads at the true pan, per pair (2026-11-18).

    wallscore.py <scene.json> <fields-dir> [<fields-dir> ...] [--band 0:200] [--tol 4] [--pairs a:b]

Truth per pair: scene.py's strongest horizontal phase-correlation peak over the wall band (rows 0-260, the source's
pixels only, no shader), kept where the peak is clear (height >= 0.10) and the pan is at least 8 px. The wall is
seen at an angle, so the true motion varies a few px across it: --tol (4 px) absorbs that. Reported per field
directory: the share of the band's texels within --tol of the truth, and the share at or below zero (the backward
alias and the still reading), pair by pair and pooled.
"""
import argparse, json
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('scene'); ap.add_argument('fields', nargs='+', type=Path)
ap.add_argument('--band', default='0:200'); ap.add_argument('--x', default='64:1856')
ap.add_argument('--tol', type=float, default=4.0); ap.add_argument('--pairs', default='100:300')
ap.add_argument('--every', type=int, default=10)
a = ap.parse_args()
rows = json.load(open(a.scene))['rows']
truth = {}
for r in rows:
    s, h = r['peaks'][0]
    if h >= 0.10 and s >= 8:
        truth[r['pair'][0]] = s
p0, p1 = map(int, a.pairs.split(':'))
y0, y1 = map(int, a.band.split(':')); x0, x1 = map(int, a.x.split(':'))
res = {}
for d in a.fields:
    meta = json.loads((d / 'pairs.json').read_text()); sub = meta['sub']
    f = np.load(d / 'flow.npy', mmap_mode='r')
    per = {}
    for i, k in enumerate(meta['pairs']):
        if k in truth and p0 <= k <= p1:
            v = np.asarray(f[i, y0 // sub:y1 // sub, x0 // sub:x1 // sub, 0], np.float32)
            h, e = np.histogram(v, bins=np.arange(-64, 65, 1.0))
            c = np.convolve(h, np.ones(2 * int(a.tol) + 1), 'same')
            per[k] = (float(np.mean(np.abs(v - truth[k]) <= a.tol)), float(np.mean(v <= 0.0)), float(c.max() / v.size))
    res[d.name] = per
names = list(res)
common = sorted(set.intersection(*[set(res[n]) for n in names]))
print(f'{len(common)} pairs with a clear truth in {a.pairs}; share of the wall band within {a.tol} px of the true pan '
      f'(and share reading <= 0)')
print('each cell: at truth / reading <= 0 / coherent (within the tolerance of the band\'s own mode)')
print('pair  truth  ' + '  '.join(f'{n:>22s}' for n in names))
for k in common[::a.every]:
    print(f'{k:4d} {truth[k]:+6.1f}  ' + '  '.join(f'{100*res[n][k][0]:5.1f} /{100*res[n][k][1]:5.1f} /{100*res[n][k][2]:5.1f}' for n in names))
print('pooled       ' + '  '.join(f'{100*np.mean([res[n][k][0] for k in common]):5.1f} /{100*np.mean([res[n][k][1] for k in common]):5.1f} /{100*np.mean([res[n][k][2] for k in common]):5.1f}' for n in names))
