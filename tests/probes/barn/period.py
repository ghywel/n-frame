#!/usr/bin/env python3
"""The wall's corrugation period per source frame, from the power spectrum of the column-mean horizontal gradient.

    python3 period.py <source.mkv> --band y0:y1 --x x0:x1 [--first N] [--last N] [--every K] [--ffmpeg PATH]

Searches 12-48 px (the corrugation at 1080p is about 25 px by eye on frame 192). A zero-padded FFT with a
parabolic peak gives the period to about 0.05 px; the peak's share of the band's power says whether the band is
wall or not (posters and actors lower it). Written 2026-11-18 for the barn clip (owner-supplied; its path is not recorded here).
"""
import argparse, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('--band', default='0:200'); ap.add_argument('--x', default='64:1856')
ap.add_argument('--first', type=int, default=0); ap.add_argument('--last', type=int, default=335)
ap.add_argument('--every', type=int, default=6); ap.add_argument('--ffmpeg', default='ffmpeg')
a = ap.parse_args()
y0, y1 = map(int, a.band.split(':')); x0, x1 = map(int, a.x.split(':'))
W, H = 1920, 1080
cmd = [a.ffmpeg, '-nostdin', '-v', 'error', '-i', a.src, '-vf', f"select='between(n\\,{a.first}\\,{a.last})'",
       '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
n = a.first; count = 0
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H: break
    if (n - a.first) % a.every == 0:
        f = np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float64)[y0:y1, x0:x1]
        g = np.diff(f, axis=1).mean(axis=0); g -= g.mean(); g *= np.hanning(len(g))
        N = 16384
        S = np.abs(np.fft.rfft(g, N)) ** 2
        fr = np.fft.rfftfreq(N)
        m = (fr > 1 / 48) & (fr < 1 / 12)
        k = np.flatnonzero(m)[np.argmax(S[m])]
        a1, b1, c1 = np.log(S[k - 1] + 1e-12), np.log(S[k] + 1e-12), np.log(S[k + 1] + 1e-12)
        d = 0.5 * (a1 - c1) / (a1 - 2 * b1 + c1)
        fpk = (k + d) / N
        share = S[k - 40:k + 41].sum() / S[1:].sum()
        print(f'{n:4d}  period {1 / fpk:6.2f} px  peak share {share:.2f}')
        count += 1
    n += 1
p.wait()
if p.returncode: sys.exit('ffmpeg failed')
print(f'{count} frames')
