#!/usr/bin/env python3
"""D1h's FIELD, ROW BAND BY ROW BAND: which alias each part of the still window chose, and whether it holds it
(2026-10-22, the swarm's periodic-alias lane; the kill test of proposal 3, written after the picture was rendered:
region hold 7.22, linear 10.01, the recommendation 6.78, High 9.90, quad 10.70).

    d1_rowsign.py <dir with v%03d.png | file.rgb48> <first frame> <count>     the reader (CPU; no GPU)
    d1_rowsign.py --selftest                                                   the verdict logic on a made-up field

THE EXPORT TO READ (the GPU side, modelled on tests/loop.sh: read_view 4 is the raw machine velocity, 0.5 + px / 64 in
R (x) and G (y), FLOW_H_AB in full-resolution px per source pair; format=rgb48le INSIDE the graph, as tests/fieldcheck.py
requires, or the zero level reads 219/255 and every number is wrong; N:N at fps=24, one frame per source pair):

    W=<workdir>; REPO=<the worktree>; cd $W
    for s in rec:bidirectional-interpolation-variational-propagated \\
             high:bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut; do
      lab=${s%%:*}; f=$REPO/shaders/${s#*:}.glsl
      sed '/^\\/\\/!PARAM read_view/,/^$/ s/^0$/4/' "$f" > "$lab-rv4.glsl"
      grep -A5 "^//!PARAM read_view" "$lab-rv4.glsl" | grep -q "^4$" || echo "read_view patch failed"
      mkdir -p "$lab"
      $FFMPEG -y -hide_banner -loglevel error -init_hw_device vulkan=vk -filter_hw_device vk \\
        -f lavfi -i "$(. $REPO/tests/scenes.sh; scene D1h_print_behind_window_v12 24)" \\
        -vf "libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path=$lab-rv4.glsl,select='between(n\\,6\\,15)',format=rgb48le" \\
        -start_number 6 -frames:v 10 "$lab/v%03d.png"
      python3 $REPO/tests/probes/cage/d1_rowsign.py "$lab" 6 10
    done

Frames 6..15 of the 24: after the caches have a history, before N - 8 = 16. (The quad's export is the same with its
file; it reads FLOW_H_AB too.)

WHAT IS PRINTED. The window is x 490..789, y 210..509 (scenes.sh, D1). Columns 506..773 are read (16 px in from the
window's sides, so the side edges' texels are left out); the rows are cut into 24-px bands from the window's top (one
bar period each; band 12 is the 12-px remainder). Per band: the median vertical flow over the frames (+ is down, the
print's true direction at 12 px/frame; -12 is the alias), the share of frames whose band median is positive, the
median |fy|, the share of the band's texels within 3 px of zero / within 3 px of +-12 / elsewhere, and the FLIP share:
the fraction of consecutive frame pairs on which the band's median sign changed. Then the whole window's fy
histogram (1-px bins) pooled over the frames.

THE VERDICTS, applied automatically (a band "has an alias" when its median |fy| is at least 6 px):
  SPLIT      the top four bands' sign majority differs from the bottom four's, each side consistent on at least two
             thirds of its band-frames, with an alias in both: the extrinsic-edge mechanism (each window edge votes for
             the alias that maps a bar texel inward) is confirmed; the fix is the survey's ownership gate.
  ONE SIGN   at least 90 percent of the band-frames with an alias share one sign: persistence broke the tie once and
             held it; SPLIT is killed.
  FLICKER    the mean flip share over the bands is over 10 percent: "graceful" is killed, whatever else holds.
  ZERO FLOOR at least half the band-frames have |median fy| under 3 px: the field collapsed to the small-motion floor
             and chose neither alias (a near-blend warp); both hypotheses are moot and the number to explain is why the
             recommendation then reads BELOW the blend (the texels that did choose).
The instrument check of fieldcheck.py is kept: off the window (rows 0..150) the field must read exactly 0.5.
"""
import os
import pathlib
import subprocess
import sys

import numpy as np

FF = os.environ.get("FFMPEG", os.path.expanduser("~/np-build/ffmpeg/ffmpeg"))
W, H, FS = 1280, 720, 32.0
X0, X1, Y0, Y1 = 490, 790, 210, 510                        # the window (scenes.sh, D1)
CX0, CX1 = X0 + 16, X1 - 16                                # the columns read
BAND = 24


def decode_png(png):
    raw = subprocess.run([FF, "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint16).reshape(H, W, 3).astype(np.float64) / 65535.0


def load(path, first, count):
    p = pathlib.Path(path)
    if p.is_dir():
        return [decode_png(p / f"v{first + i:03d}.png") for i in range(count)]
    a = np.fromfile(p, np.uint16).reshape(-1, H, W, 3).astype(np.float64) / 65535.0
    return [a[i] for i in range(min(count, len(a)))]


def analyse(frames, label=""):
    bands = []
    y = Y0
    while y < Y1:
        bands.append((y, min(y + BAND, Y1))); y += BAND
    nb, nf = len(bands), len(frames)
    med = np.zeros((nb, nf)); medx = np.zeros((nb, nf)); z = np.zeros((nb, nf)); al = np.zeros((nb, nf))
    pooled = []
    for i, im in enumerate(frames):
        off = im[0:150, :, :2]
        zero = np.median(off, axis=(0, 1))
        if np.any(np.abs(zero - 0.5) > 0.0005):
            sys.exit(f"  READ PATH BROKEN: the zero level off the window reads ({zero[0]:.4f}, {zero[1]:.4f}) instead of "
                     f"0.5: an 8-bit or limited-range intermediate; render with format=rgb48le inside the graph")
        fx = (im[..., 0] - 0.5) * 2 * FS; fy = (im[..., 1] - 0.5) * 2 * FS
        win = fy[Y0:Y1, CX0:CX1]; pooled.append(win.ravel())
        for b, (ya, yb) in enumerate(bands):
            seg = fy[ya:yb, CX0:CX1]; segx = fx[ya:yb, CX0:CX1]
            med[b, i] = np.median(seg); medx[b, i] = np.median(segx)
            z[b, i] = (np.abs(seg) < 3).mean(); al[b, i] = (np.abs(np.abs(seg) - 12) <= 3).mean()
    sign = np.sign(med)
    flips = np.array([(sign[b, 1:] != sign[b, :-1]).mean() if nf > 1 else 0.0 for b in range(nb)])
    print(f"\n== D1h, {label or 'the field'}: {nf} frames, FLOW_H_AB (A->B) in px per source pair; + is down (the truth is +12)")
    print(f"{'band':>4s} {'rows':>9s} {'med fy':>7s} {'med fx':>7s} {'share +':>7s} {'med|fy|':>7s} {'~0':>5s} {'~12':>5s} {'other':>5s} {'flips':>6s}")
    for b, (ya, yb) in enumerate(bands):
        m = med[b]
        print(f"{b:4d} {ya:4d}..{yb - 1:<4d} {np.median(m):+7.2f} {np.median(medx[b]):+7.2f} {100 * (m > 0).mean():6.0f}% "
              f"{np.median(np.abs(m)):7.2f} {100 * z[b].mean():4.0f}% {100 * al[b].mean():4.0f}% "
              f"{100 * (1 - z[b].mean() - al[b].mean()):4.0f}% {100 * flips[b]:5.0f}%")
    allv = np.concatenate(pooled)
    hist, edges = np.histogram(allv, bins=np.arange(-20.5, 21.5, 1.0))
    print("\nthe window's fy, pooled (1-px bins, share): " + " ".join(f"{int(e + 0.5):+d}:{100 * h / allv.size:.0f}" for e, h in zip(edges[:-1], hist) if h / allv.size >= 0.005))
    # the verdicts
    has = np.abs(med) >= 6
    top, bot = slice(0, 4), slice(nb - 5, nb - 1)          # the top four bands; the bottom four full bands (the remainder left out)
    def majority(sl):
        s = sign[sl][has[sl]]
        if s.size == 0: return 0.0, 0.0
        pos = (s > 0).mean()
        return (1.0 if pos >= 0.5 else -1.0), max(pos, 1 - pos)
    mt, ct = majority(top); mb, cb = majority(bot)
    verdicts = []
    zero_floor = (np.abs(med) < 3).mean() >= 0.5
    if zero_floor:
        verdicts.append("ZERO FLOOR: at least half the band-frames sit under 3 px; the field chose neither alias")
    if has.any():
        s = sign[has]
        one = max((s > 0).mean(), (s < 0).mean())
        if one >= 0.9:
            verdicts.append(f"ONE SIGN: {100 * one:.0f}% of the aliased band-frames share one sign ({'+' if (s > 0).mean() >= 0.5 else '-'}); "
                            "persistence broke the tie and held it; the split hypothesis is killed")
        elif mt != 0 and mb != 0 and mt != mb and ct >= 2 / 3 and cb >= 2 / 3:
            verdicts.append(f"SPLIT: the top bands read {'+' if mt > 0 else '-'} ({100 * ct:.0f}% consistent) and the bottom bands "
                            f"{'+' if mb > 0 else '-'} ({100 * cb:.0f}%): the extrinsic-edge mechanism is confirmed")
        else:
            verdicts.append(f"NEITHER CLEAN: aliased band-frames {100 * (s > 0).mean():.0f}% +; top majority {mt:+.0f} ({100 * ct:.0f}%), "
                            f"bottom {mb:+.0f} ({100 * cb:.0f}%)")
    if flips.mean() > 0.10:
        verdicts.append(f"FLICKER: the bands' sign flips on {100 * flips.mean():.0f}% of frame pairs; 'graceful' is killed")
    else:
        verdicts.append(f"no flicker: sign flips on {100 * flips.mean():.0f}% of frame pairs")
    print("\nverdicts:")
    for v in verdicts:
        print("  " + v)
    return med, flips


def selftest():
    rng = np.random.default_rng(1)
    frames = []
    for i in range(10):
        im = np.full((H, W, 3), 0.5)
        fy = np.zeros((H, W)); fx = np.zeros((H, W))
        wall = 360 + int(8 * np.sin(i))                     # a wandering domain wall near the middle
        fy[Y0:wall, X0:X1] = 12 + rng.normal(0, 0.3, (wall - Y0, X1 - X0))
        fy[wall:Y1, X0:X1] = -12 + rng.normal(0, 0.3, (Y1 - wall, X1 - X0))
        im[..., 0] = 0.5 + fx / 64; im[..., 1] = 0.5 + fy / 64
        frames.append(im)
    med, flips = analyse(frames, "selftest: top half +12, bottom half -12, a wall wandering +-8 px")
    assert med[0].mean() > 6 and med[-2].mean() < -6, "the selftest field was not read back"
    print("\nselftest passed: the reader sees the made-up split")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        path, first, count = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
        analyse(load(path, first, count), str(path))
