"""CPU-only: the dilution each ladder case applies to a region-confined defect.

For each case, render source frames 0..5 at 24 fps (lavfi, no libplacebo) as 8-bit gray and compute
  band  = bandmetric.py's moving band from frames 2 and 4 (|diff| > 12, dilated 4 px), as a share of the frame
  tex   = share of pixels where the frame-3 gradient magnitude exceeds 2 levels (anything not flat)
  dil   = 10 log10(1 / band): the dB by which a defect confined to the band is understated by a whole-frame mean
"""
import os, subprocess, sys
import numpy as np

TESTS = sys.argv[1]
FF = os.environ.get("FFMPEG", "ffmpeg")
W, H = 1280, 720
cases = subprocess.run(["bash", "-c", '. "%s/scenes.sh"; echo $ALL_CASES' % TESTS], capture_output=True, text=True).stdout.split()

def scene(c, r):
    return subprocess.run(["bash", "-c", '. "%s/scenes.sh"; scene %s %d' % (TESTS, c, r)], capture_output=True, text=True).stdout.strip()

def dilate(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o

print("%-28s %7s %7s %7s" % ("case", "band%", "tex%", "dil_dB"))
for c in cases:
    s = scene(c, 24)
    p = subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i", s, "-frames:v", "6", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True)
    a = np.frombuffer(p.stdout, np.uint8)
    n = len(a) // (W * H)
    if n < 5:
        print("%-28s render failed (%d frames)" % (c, n)); continue
    f = a[:n * W * H].reshape(n, H, W).astype(np.float64)
    band = dilate(np.abs(f[2] - f[4]) > 12.0, 4)
    gy, gx = np.gradient(f[3])
    tex = np.hypot(gx, gy) > 2.0
    bs = band.mean(); ts = tex.mean()
    dil = 10 * np.log10(1.0 / bs) if bs > 0 else float("inf")
    print("%-28s %7.1f %7.1f %7.1f" % (c, 100 * bs, 100 * ts, dil), flush=True)
