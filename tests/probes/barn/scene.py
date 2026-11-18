#!/usr/bin/env python3
"""The barn clip's ground facts, from the source pixels alone (no shader): the corrugation period and the pan.

    python3 scene.py <source.mkv> [--band y0:y1] [--x x0:x1] [--first N] [--last N] [--ffmpeg PATH] [--json OUT]

For each consecutive source pair (n, n+1) in the band it prints:
  - the period of the wall's vertical corrugation (autocorrelation of the column-mean horizontal gradient),
  - the three strongest horizontal phase-correlation peaks between the pair (subpixel), with their heights.
On a periodic wall the peaks repeat a period apart; the strongest one is not necessarily the true shift. The
second and third peaks say how ambiguous the pair is. The true shift is read from non-periodic content in the band
(the posters' edges, the seam's rivets), checked by eye against crops, not assumed from the strongest peak.

No shader runs here, so nothing here can be fooled by the estimator under test. Written 2026-11-18 for the
barn clip (owner-supplied; its path is not recorded here).
"""
import argparse, json, subprocess, sys
import numpy as np

def frames(path, ff, w, h, first, last):
    cmd = [ff, '-nostdin', '-v', 'error', '-i', path, '-vf', f"select='between(n\\,{first}\\,{last})'",
           '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = first
    while True:
        b = p.stdout.read(w * h)
        if len(b) < w * h:
            break
        yield n, np.frombuffer(b, np.uint8).reshape(h, w).astype(np.float64)
        n += 1
    p.wait()
    if p.returncode != 0:
        sys.exit(f'ffmpeg failed ({p.returncode})')

def period(img):
    g = np.diff(img, axis=1).mean(axis=0)
    g -= g.mean()
    ac = np.correlate(g, g, 'full')[len(g) - 1:]
    ac /= ac[0]
    lo, hi = 8, 80
    k = lo + int(np.argmax(ac[lo:hi]))
    if 0 < k < len(ac) - 1:
        a, b, c = ac[k - 1], ac[k], ac[k + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    else:
        d = 0.0
    return k + d, float(ac[k])

def phase_peaks(a, b, npk=3, sup=4):
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    A = np.fft.fft2((a - a.mean()) * win)
    B = np.fft.fft2((b - b.mean()) * win)
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-9
    r = np.real(np.fft.ifft2(R))
    # shift d such that b(x) = a(x - d): positive d = content moved right
    W = a.shape[1]
    row0 = r[0, :].copy()           # horizontal-only slice (dy = 0), after checking dy below
    dy, dx = np.unravel_index(np.argmax(r), r.shape)
    if dy > a.shape[0] // 2:
        dy -= a.shape[0]
    line = r[(dy) % a.shape[0], :].copy()
    out = []
    for _ in range(npk):
        k = int(np.argmax(line))
        h = line[k]
        a1, b1, c1 = line[k - 1], line[k], line[(k + 1) % W]
        den = (a1 - 2 * b1 + c1)
        d = 0.5 * (a1 - c1) / den if den != 0 else 0.0
        s = k + d
        if s > W / 2:
            s -= W
        out.append((round(-s, 2), round(float(h), 4)))
        for j in range(-sup, sup + 1):
            line[(k + j) % W] = -1
    return int(dy), out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--band', default='0:260')
    ap.add_argument('--x', default='64:1856')
    ap.add_argument('--first', type=int, default=0)
    ap.add_argument('--last', type=int, default=335)
    ap.add_argument('--ffmpeg', default='ffmpeg')
    ap.add_argument('--json')
    a = ap.parse_args()
    y0, y1 = map(int, a.band.split(':'))
    x0, x1 = map(int, a.x.split(':'))
    prev = None
    rows = []
    for n, f in frames(a.src, a.ffmpeg, 1920, 1080, a.first, a.last):
        cur = f[y0:y1, x0:x1]
        P, pq = period(cur)
        if prev is not None:
            dy, pk = phase_peaks(prev, cur)
            rows.append(dict(pair=[n - 1, n], period=round(P, 2), period_q=round(pq, 3), dy=dy, peaks=pk))
            print(f'{n-1:4d}->{n:<4d} period {P:6.2f} (ac {pq:.2f})  dy {dy:+d}  ' +
                  '  '.join(f'{s:+7.2f} [{h:.3f}]' for s, h in pk))
        prev = cur
    if a.json:
        json.dump(dict(band=[y0, y1], x=[x0, x1], rows=rows), open(a.json, 'w'), indent=1)
    print(f'{len(rows)} pairs')

main()
