#!/usr/bin/env python3
"""make_prints.py [outdir]: the printable targets for REAL-MOTION-RIG.md (2026-10-22), A4 at 300 dpi.

    ~/np-build/venv/bin/python3 tests/probes/rig/make_prints.py ~/Developer/np-scratch/n-frame/rig

Writes four A4 sheets as PNG (grey, 2480 x 3508 px), then PDF beside each through macOS `sips` with the resolution set
to 300 dpi, so "print at actual size" gives the stated millimetres. Every sheet carries a 100 mm scale bar: measure it
after printing and write the number in the take log, because a printer that scales by 3% makes every speed 3% wrong.

  disc-noise    a 190 mm disc of aperiodic noise at five scales (about 1.5 mm to 25 mm across), a white rim dot for
                counting revolutions, a cross at the centre. The main target: the matcher's best case on real texture.
  disc-checker  a 190 mm polar checkerboard, 36 sectors x 8 rings: the wagon wheel. Motion across the sectors is the
                period trap on real content; the inner rings move slower, so one disc sweeps the trap's speeds.
  markers       black dots of 6, 10 and 16 mm on white, with a 100 mm bar: cut out and stick on the spring's weight and the
                pendulum's bob. A dot's centroid is tracked without the shader, which makes it the answer key.
  noise-patch   a 120 x 120 mm square of the same noise, for the weight and the bob's face (texture the shader can read).

Why these scales: the rig is framed so the disc spans about 680 px of a 1920 x 1080 frame, about 3.6 video px per mm. At
that scale the noise's features run from about 5 px to 90 px, so structure sits above the coarse level's Nyquist (about
40 px at 1280 wide, NFRAME-LIMITS "the non-affine cliff") and fine grain below it, as real surfaces have. Deterministic:
the same seed gives the same sheets.
"""
import os
import subprocess
import sys

import numpy as np

DPI = 300
W, H = 2480, 3508                      # A4 at 300 dpi
MM = DPI / 25.4                        # px per mm
FF = os.environ.get("FFMPEG", os.path.expanduser("~/np-build/ffmpeg/ffmpeg"))
rng = np.random.default_rng(20261022)


def blur(a, sigma):
    """Separable Gaussian blur by FFT (periodic edges are fine: the noise is cropped well inside)."""
    if sigma <= 0:
        return a
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.fftfreq(a.shape[1])[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def noise(h, w):
    """Five octaves of band-limited noise, 1.5 mm to 25 mm, equal weight, stretched to full contrast."""
    out = np.zeros((h, w))
    for mm in (1.5, 3.0, 6.0, 12.0, 25.0):
        s = mm * MM / 2.5
        n = blur(rng.standard_normal((h, w)), s)
        out += n / n.std()
    out = (out - out.mean()) / out.std()
    return np.clip(0.5 + 0.18 * out, 0.02, 0.98)


def scale_bar(img, x0, y0):
    """A 100 mm bar, 3 mm tall, with a tick every 10 mm and a longer one at 50."""
    L, T = int(round(100 * MM)), int(round(3 * MM))
    img[y0:y0 + T, x0:x0 + L] = 0.0
    for k in range(11):
        x = x0 + int(round(k * 10 * MM))
        tick = int(round((6 if k % 5 == 0 else 4) * MM))
        img[y0 - tick:y0, max(x - 2, 0):x + 3] = 0.0


def disc_mask(cx, cy, r):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r, xx - cx, yy - cy


def sheet_disc_noise():
    img = np.ones((H, W))
    r = 95 * MM
    cx, cy = W / 2, H / 2 - 20 * MM
    m, dx, dy = disc_mask(cx, cy, r)
    img[m] = noise(H, W)[m]
    rr = np.hypot(dx, dy)
    img[np.abs(rr - r) < 0.6 * MM] = 0.0                                   # the disc's edge
    img[(np.hypot(dx, dy - (-r + 9 * MM)) < 4 * MM)] = 1.0                 # the white rim dot, for counting turns
    img[(np.abs(dx) < 0.4 * MM) & (np.abs(dy) < 6 * MM)] = 0.0             # the centre cross
    img[(np.abs(dy) < 0.4 * MM) & (np.abs(dx) < 6 * MM)] = 0.0
    scale_bar(img, int(W / 2 - 50 * MM), int(H - 30 * MM))
    return img


def sheet_disc_checker():
    img = np.ones((H, W))
    r = 95 * MM
    cx, cy = W / 2, H / 2 - 20 * MM
    m, dx, dy = disc_mask(cx, cy, r)
    ang = (np.arctan2(dy, dx) + np.pi) / (2 * np.pi)
    ring = np.floor(np.hypot(dx, dy) / r * 8)
    sector = np.floor(ang * 36)
    chk = ((ring + sector) % 2 == 0)
    img[m] = np.where(chk[m], 0.08, 0.92)
    img[np.abs(np.hypot(dx, dy) - r) < 0.6 * MM] = 0.0
    img[(np.abs(dx) < 0.4 * MM) & (np.abs(dy) < 6 * MM)] = 0.5
    img[(np.abs(dy) < 0.4 * MM) & (np.abs(dx) < 6 * MM)] = 0.5
    scale_bar(img, int(W / 2 - 50 * MM), int(H - 30 * MM))
    return img


def sheet_markers():
    img = np.ones((H, W))
    yy, xx = np.mgrid[0:H, 0:W]
    y = 40 * MM
    for d in (6, 10, 16):
        for k in range(6):
            cx = (25 + k * 30) * MM
            img[np.hypot(xx - cx, yy - y) <= d / 2 * MM] = 0.0
        y += 45 * MM
    scale_bar(img, int(W / 2 - 50 * MM), int(H - 30 * MM))
    return img


def sheet_noise_patch():
    img = np.ones((H, W))
    s = int(round(120 * MM))
    x0, y0 = (W - s) // 2, int(40 * MM)
    img[y0:y0 + s, x0:x0 + s] = noise(H, W)[y0:y0 + s, x0:x0 + s]
    img[y0 + s + int(20 * MM):y0 + s + int(70 * MM), x0:x0 + s] = noise(H, W)[:int(50 * MM), :s]
    scale_bar(img, int(W / 2 - 50 * MM), int(H - 30 * MM))
    return img


def write(img, path):
    g = np.round(np.clip(img, 0, 1) * 255).astype(np.uint8)
    p = subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray",
                        "-s", "%dx%d" % (W, H), "-i", "-", "-frames:v", "1", path], input=g.tobytes())
    if p.returncode:
        sys.exit("ffmpeg failed on " + path)
    subprocess.run(["sips", "-s", "dpiWidth", str(DPI), "-s", "dpiHeight", str(DPI), path], capture_output=True, check=True)
    pdf = path[:-4] + ".pdf"
    subprocess.run(["sips", "-s", "format", "pdf", path, "--out", pdf], capture_output=True, check=True)
    return pdf


def main():
    out = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Developer/np-scratch/n-frame/rig")
    os.makedirs(out, exist_ok=True)
    for name, fn in (("disc-noise", sheet_disc_noise), ("disc-checker", sheet_disc_checker),
                     ("markers", sheet_markers), ("noise-patch", sheet_noise_patch)):
        pdf = write(fn(), os.path.join(out, name + ".png"))
        print("wrote", os.path.join(out, name + ".png"), "and", pdf)


if __name__ == "__main__":
    main()
