#!/usr/bin/env python3
"""C3's CEILING: the disc warped by the TRUE per-texel flow, scored as cage.sh scores it (2026-10-22, the swarm's
periodic-alias lane, proposal 2; NFRAME-LIMITS.md "The cage" took the same oracle for C1 with its uniform 0.5 px, 37.4
against the blend's 43.2, and C3's was never taken).

    c3_oracle.py [workdir]          CPU only: lavfi sources, numpy; no Vulkan, no shader

C3_bars_spin_drift (scenes.sh, scene_edge): the bars and the wall rotate rigidly about the grid's origin at 0.15 rad/s
while the origin translates at (24, 12) px/s, so the true flow at pixel (X, Y), per SOURCE frame (1/24 s), is
    v = (1, 0.5) + (0.15 / 24) * (-(Y - cy), X - cx),   cx = 640 + 24 t, cy = 360 + 12 t   (the scene's own comment).
For every output instant of the 60 fps grid that is not a passthrough (n > 5 and n % 5 != 1, 1-based, as cage.sh's
reader skips them), the two bracketing source frames A (k = floor(24 t)) and B (k + 1) are warped to the instant and
scored against the 60 fps render on the disc's rectangle (crop=650:630:340:60, cage.sh's region), PSNR-Y per frame,
then the mean over the scored frames. Five rows:
    hold          the source frame at or before the instant (what fps=60 does)
    linear        (1 - f) A + f B, the blend
    oracle-flow   A warped by -f v and B by +(1 - f) v, each at the OUTPUT pixel's v (the linear flow, as asked), the
                  two averaged time-weighted (1 - f, f)
    oracle-equal  the same two warps averaged equally (the record's "equal footing")
    oracle-rigid  the exact inverse of the rigid motion (pattern coordinates carried between instants), time-weighted:
                  the ceiling of the flow route with no linearisation; its gap to oracle-flow is the linearisation's cost
Bilinear sampling throughout. Also printed: the same five on the WHOLE frame, and the record's numbers for the disc
(hold 24.4, blend 28.9, the recommendation 21.9, the three-switch file 22.7) for the reader to check the instrument
against (hold and linear here should land within a few tenths of cage.sh's).
"""
import os
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
TESTS = HERE.parent.parent
FF = os.environ.get("FFMPEG", os.path.expanduser("~/np-build/ffmpeg/ffmpeg"))
WORK = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NP_SCRATCH", os.path.expanduser("~/Developer/np-scratch")) + "/cage/c3_oracle")
WORK.mkdir(parents=True, exist_ok=True)
W, H = 1280, 720
RX, RY, RW, RH = 340, 60, 650, 630            # cage.sh's disc rectangle: crop=650:630:340:60
OMEGA, VX, VY = 0.15, 24.0, 12.0              # rad/s, px/s, px/s (scenes.sh, C3)


def scene(rate):
    out = subprocess.run(["bash", "-c", f". '{TESTS}/scenes.sh'; scene_edge C3_bars_spin_drift {rate}"],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert out and "UNKNOWN" not in out, out
    return out


def luma(rate):
    """the Y plane of the yuv420p render, every frame, as float32 0..255"""
    raw = WORK / f"c3-{rate}.y"
    if not raw.exists():
        subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", scene(rate),
                        "-pix_fmt", "yuv420p", "-f", "rawvideo", str(raw)], check=True)
    a = np.fromfile(raw, np.uint8)
    fsz = W * H * 3 // 2
    n = a.size // fsz
    return a[: n * fsz].reshape(n, fsz)[:, : W * H].reshape(n, H, W).astype(np.float32)


def bilinear(img, x, y):
    x = np.clip(x, 0, W - 1); y = np.clip(y, 0, H - 1)
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
    x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
    fx = x - x0; fy = y - y0
    return ((img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) + (img[y1, x0] * (1 - fx) + img[y1, x1] * fx) * fy)


def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)


YY, XX = np.mgrid[0:H, 0:W].astype(np.float64)


def flow_at(t):
    """the true flow per source frame at output time t, at every pixel"""
    cx, cy = 640 + VX * t, 360 + VY * t
    return np.stack([1.0 + (OMEGA / 24.0) * (-(YY - cy)), 0.5 + (OMEGA / 24.0) * (XX - cx)])


def rigid_source_pos(t_out, t_src):
    """where the content at pixel (X, Y) of the instant t_out sat in the frame at t_src (the exact inverse)"""
    th = OMEGA * t_out
    u = (XX - 640 - VX * t_out) * np.cos(th) + (YY - 360 - VY * t_out) * np.sin(th)
    w = (YY - 360 - VY * t_out) * np.cos(th) - (XX - 640 - VX * t_out) * np.sin(th)
    ths = OMEGA * t_src
    xs = 640 + VX * t_src + u * np.cos(ths) - w * np.sin(ths)
    ys = 360 + VY * t_src + u * np.sin(ths) + w * np.cos(ths)
    return xs, ys


def main():
    src = luma(24); tru = luma(60)
    n60 = min(len(tru), (len(src) - 1) * 60 // 24)
    rows = {"hold": [], "linear": [], "oracle-flow": [], "oracle-equal": [], "oracle-rigid": []}
    full = {k: [] for k in rows}
    sl = (slice(RY, RY + RH), slice(RX, RX + RW))
    for n in range(n60):
        if n + 1 <= 5 or (n + 1) % 5 == 1:               # cage.sh's reader: n (1-based) > 5 and n % 5 != 1
            continue
        t = n / 60.0
        k = int(np.floor(t * 24.0 + 1e-9)); f = t * 24.0 - k
        if k + 1 >= len(src):
            break
        A, B = src[k], src[k + 1]
        T = tru[n]
        v = flow_at(t)
        wa = bilinear(A, XX - f * v[0], YY - f * v[1])
        wb = bilinear(B, XX + (1 - f) * v[0], YY + (1 - f) * v[1])
        xa, ya = rigid_source_pos(t, k / 24.0); xb, yb = rigid_source_pos(t, (k + 1) / 24.0)
        ra = bilinear(A, xa, ya); rb = bilinear(B, xb, yb)
        out = {"hold": A, "linear": (1 - f) * A + f * B,
               "oracle-flow": (1 - f) * wa + f * wb, "oracle-equal": 0.5 * (wa + wb),
               "oracle-rigid": (1 - f) * ra + f * rb}
        for key, img in out.items():
            rows[key].append(psnr(img[sl], T[sl])); full[key].append(psnr(img, T))
    print(f"C3_bars_spin_drift, PSNR-Y, {len(rows['hold'])} scored output frames (the passthrough instants excluded)")
    print(f"  {'mode':14s} {'disc mean':>10s} {'disc min':>9s}   {'frame mean':>10s}")
    for key in rows:
        print(f"  {key:14s} {np.mean(rows[key]):10.2f} {np.min(rows[key]):9.2f}   {np.mean(full[key]):10.2f}")
    print("  the record (cage.sh, the GPU, 2026-09-21): disc hold 24.4, linear 28.9, the recommendation 21.9, "
          "the three-switch file 22.7; the shipped High tier 23.2 (2026-10-21)")


if __name__ == "__main__":
    main()
