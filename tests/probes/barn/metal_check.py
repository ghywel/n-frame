#!/usr/bin/env python3
"""Does the Metal engine (Cadence's) draw what libplacebo draws, memory included? (2026-11-18)

    metal_check.py <quaddemo> <video.mp4> <metal-high-graph> <metal-memory-graph> <lp-high.mkv> <lp-memory.mkv> <workdir>
                   [--first-lp 60] [--pairs 186:212]

QuadDemo (the demo's engine, the same graphs Cadence bundles) renders the clip with each graph at 23.976 -> 47.952
and exports 16-bit RGB to a file in <workdir> (it replaces a pipe with a file, so a file it is: the source is cut
to the frames needed, read, and deleted before the next run). libplacebo's two renders (fielddump's trim from
--first-lp) are the reference. For each pair's inserted frame on the wall band, the CHANGE that the memory makes
(memory minus High) is compared between the two hosts: its size on each, and the correlation of the two change maps.
The hosts' colour paths differ slightly (Metal's RGB is converted to limited-range luma here), so absolute
cross-host differences are reported but not judged; a memory that does nothing on Metal shows as a change of ~0
there against libplacebo's, and a change map uncorrelated with libplacebo's means the two sides diverge.
"""
import argparse, os, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
for a in ('quaddemo', 'video', 'mhigh', 'mmem', 'lphigh', 'lpmem', 'work'):
    ap.add_argument(a)
ap.add_argument('--first-lp', type=int, default=60); ap.add_argument('--pairs', default='186:212')
a = ap.parse_args()
p0, p1 = map(int, a.pairs.split(':'))
W, H = 1920, 1080; fb = W * H * 6
want = {2 * k + 1: k for k in range(p0, p1 + 1)}


def metal(graph, tag):
    out_path = os.path.join(a.work, f'export-{tag}.rgb48')
    r = subprocess.run([a.quaddemo, '--graph', graph, '--video', a.video, '--out-fps', '47.952', '--frames', str(p1 + 4),
                        '--export', out_path], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'QuadDemo failed ({tag}): {r.stderr[-800:]}')
    n = os.path.getsize(out_path) // fb
    out = {}
    with open(out_path, 'rb') as f:
        for j in range(n):
            b = f.read(fb)
            if j in want:
                x = np.frombuffer(b, '<u2').reshape(H, W, 3).astype(np.float64) / 65535
                out[want[j]] = 16 + 219 * (0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2])
    os.remove(out_path)
    missing = [k for k in range(p0, p1 + 1) if k not in out]
    if missing:
        sys.exit(f'{tag}: {n} frames exported, pairs missing: {missing[:5]}')
    return out, n


def lp(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
    x = np.frombuffer(r, np.uint8).reshape(-1, H, W)
    return {k: x[(k - a.first_lp) * 2 + 1].astype(np.float64) for k in range(p0, p1 + 1)}


mh, nh = metal(a.mhigh, 'high')
mm, nm = metal(a.mmem, 'memory')
lh, lm = lp(a.lphigh), lp(a.lpmem)
print(f'Metal frames exported: High {nh}, memory {nm}')
band = (slice(0, 400), slice(64, 1856))
print('pair | wall band mean |memory - High|: Metal  libplacebo | correlation of the change maps | |memory Metal - memory lp|')
cs = []
for k in range(p0, p1 + 1, 2):
    dm = (mm[k] - mh[k])[band]; dl = (lm[k] - lh[k])[band]
    c = np.corrcoef(dm.ravel(), dl.ravel())[0, 1] if dm.std() > 0 and dl.std() > 0 else float('nan')
    cs.append(c)
    print(f'{k} | {np.abs(dm).mean():6.2f} {np.abs(dl).mean():6.2f} | {c:+.2f} | {np.abs(mm[k] - lm[k])[band].mean():5.2f}')
print('median correlation', round(float(np.nanmedian(cs)), 2))
