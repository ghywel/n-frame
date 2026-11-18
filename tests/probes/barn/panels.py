#!/usr/bin/env python3
"""Look at what High decided on chosen pairs of the barn clip: a 2 x 2 panel per pair, written as PNG.

    panels.py <fields-dir> <source.mkv> <out-dir> <pair> [<pair> ...] [--lo -20] [--hi 40]

top left: source frame k (half resolution); top right: FLOW_H_AB's x in px, grey from --lo (black) to --hi (white),
with the true wall speed's grey marked in the colour bar at the bottom of the panel; bottom left: the coherence gate's
unwarp weight (white = the plain A/B blend); bottom right: the vote's weight (white = the vote's vector).
Reads fielddump.py's arrays (pairs.json names each pair). 2026-11-18.
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('fields', type=Path); ap.add_argument('source'); ap.add_argument('out', type=Path)
ap.add_argument('pairs', type=int, nargs='+'); ap.add_argument('--lo', type=float, default=-20); ap.add_argument('--hi', type=float, default=40)
ap.add_argument('--ffmpeg', default='ffmpeg')
a = ap.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
meta = json.loads((a.fields / 'pairs.json').read_text())
P = meta['pairs']; sub = meta['sub']
flow = np.load(a.fields / 'flow.npy', mmap_mode='r'); vote = np.load(a.fields / 'vote.npy', mmap_mode='r')
for k in a.pairs:
    i = P.index(k)
    f = np.asarray(flow[i], np.float32); v = np.asarray(vote[i], np.float32)
    h, w = f.shape[:2]
    raw = subprocess.run([a.ffmpeg, '-v', 'error', '-i', a.source, '-vf', f"select='eq(n\\,{k})',scale={w}:{h},format=gray",
                          '-frames:v', '1', '-f', 'rawvideo', '-'], capture_output=True).stdout
    src = np.frombuffer(raw, np.uint8).reshape(h, w)
    fx = np.clip((f[..., 0] - a.lo) / (a.hi - a.lo) * 255, 0, 255).astype(np.uint8)
    bar = np.tile(np.linspace(0, 255, w).astype(np.uint8), (12, 1))
    fx[-12:] = bar
    ticks = [int((t - a.lo) / (a.hi - a.lo) * w) for t in range(int(a.lo), int(a.hi) + 1, 10)]
    for t in ticks:
        if 0 <= t < w: fx[-20:-12, t] = 255 if t < w / 2 else 0
    unw = (np.clip(f[..., 2], 0, 1) * 255).astype(np.uint8)
    vw = (np.clip(v[..., 2], 0, 1) * 255).astype(np.uint8)
    img = np.concatenate([np.concatenate([src, fx], 1), np.concatenate([unw, vw], 1)], 0)
    p = a.out / f'panel-{k}.pgm'
    p.write_bytes(b'P5 %d %d 255\n' % (img.shape[1], img.shape[0]) + img.tobytes())
    subprocess.run([a.ffmpeg, '-v', 'error', '-y', '-i', str(p), str(p.with_suffix('.png'))], check=True)
    p.unlink()
    print(p.with_suffix('.png'))
