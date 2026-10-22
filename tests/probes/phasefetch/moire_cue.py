#!/usr/bin/env python3
"""THE PHASE FETCH'S GATE CUE, MEASURED: does moire_s tell the fetch's gainers from its losers? (2026-10-22; the swarm's
item 10 and its night handoff, swarm/2026-10-21/NIGHT-2026-10-21.md decision 6: "the gate's cue measured (moire_s on L7
and P1) before a third switch"; the gated form's design in swarm/2026-10-21/wildcard.md, "Item 10's result").

    moire_cue.py <work> [shader=shaders/bidirectional-interpolation-variational-propagated.glsl] [cases=the nine]

PHASE_FETCH=1 on the recommendation: L7 +19.7, P5 +8.5, M2 +7.2, L6 +6.2 against P1 -6.7, V3 -5.4, V1 -3.0, H1 -2.5,
L1 -2.2 (the 42-case ladder, the night of 10-21). A gate would take the fetch where it gains and the stored grid where
it loses. moire_s (the base's Moire evidence: 1 - the 1/8 box contrast / the 1/16 point contrast over a 3x3 of 1/16
texels, 0 where the point contrast is under 0.02) is the free candidate. This taps it.

THE TAP (dump_masks.py's method, its tapped() reused): a pass right after "[high] refine flow A->B (1/8 res)" (the pass
that calls moire_s(uv_a) under ZERO_SEED) writes, per 1/8 cell, x = 10 moire_s and y = 100 x the point contrast
(clamped to 31) into DIAG_TAP; the reading tail is re-pointed to it, read_view 4, rgb48le inside the graph (the M5
writes it; Mesa cannot, use the M5). Decoded at pixel (8 i + 4, 8 j + 4). N:N at 24, frames 4..19; a cell counts when
its centre lies in the case's box at T = n / 24 eroded by 32 px (moire_s reaches 24 px: one 1/16 texel and the box's
quarter-texel taps), so the box's own edge never enters.

PRE-REGISTERED (written before the run):
  The decisive pair is P1 and P5: the same texture (TEX_P, period-24 stairs plus a fine speckle), the same 600 x 300
  box, moving 4 and 8 px/frame along the bars. moire_s reads frame A's texture alone, so it is speed-blind.
  PREDICTION: P1 and P5 read the same moire_s distribution (medians within 0.05, p25-p75 bands overlapping), so no
  threshold on moire_s can send P1 to the stored grid and P5 to the fetch. Also predicted, from a pure period's
  attenuation through the 8-px box and the +-4 px quad: L7 (period 15.7) near 1, the period-24 family (V1, H1, V3)
  near 0.5-0.7, M2 (period 40) near 0.2-0.3, so the gainers straddle the losers in moire_s; L1 and L6 (flat
  interiors) read 0 (point contrast under 0.02) and are reported, not judged: their gain and loss live on edges.
  DECISION:
    CUE HOLDS -> build PHASE_FETCH gated by moire_s next: a threshold separates the in-box medians of every period
      loser (P1, V1, H1, V3) from every period gainer (L7, P5, M2), each case's p25-p75 band on its own side.
    CUE FAILS -> moire_s is refused as the gate; the next build is the speed-aware cue, the two-basin tie the fused
      coarse pass already computes (wildcard.md, "Classes and the gate"): the ring descent's basin >= 0.75 texel from
      the zero descent's with cost_b within 10% of cost_a under the frame fetch.
Numbers only; the renders stay in <work>.
"""
import os
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
TESTS = HERE.parent.parent
REPO = TESTS.parent
sys.path.insert(0, str(HERE.parent / "trust"))
import dump_masks                                                                 # noqa: E402  (tapped(), FS)

FF = os.environ.get("FFMPEG", os.path.expanduser("~/np-build/ffmpeg/ffmpeg"))
W, H = 1280, 720
CASES = {   # name: (x0(T), y0(T), w, h) from tests/scenes.sh, T in seconds; the fetch's measured delta on the 42 (dB)
    "L7_textured_large":        (lambda T: 384 * T, lambda T: 210, 300, 300, +19.7),
    "P5_stairs_along_v8_alias": (lambda T: 100 + 192 * T, lambda T: 210, 600, 300, +8.5),
    "M2_period40":              (lambda T: 384 * T, lambda T: 210, 300, 300, +7.2),
    "L6_flat_large":            (lambda T: 384 * T, lambda T: 210, 300, 300, +6.2),
    "P1_stairs_along_v4":       (lambda T: 100 + 96 * T, lambda T: 210, 600, 300, -6.7),
    "V3_stairs_sq24_v12":       (lambda T: 490, lambda T: 100 + 288 * T, 300, 300, -5.4),
    "V1_bars_sine24_v6":        (lambda T: 490, lambda T: 100 + 144 * T, 300, 300, -3.0),
    "H1_bars_sine24_h6":        (lambda T: 100 + 144 * T, lambda T: 210, 300, 300, -2.5),
    "L1_trans_8px":             (lambda T: 192 * T, lambda T: 310, 100, 100, -2.2),
}
GAIN, LOSS = ["L7_textured_large", "P5_stairs_along_v8_alias", "M2_period40"], \
             ["P1_stairs_along_v4", "V1_bars_sine24_v6", "H1_bars_sine24_h6", "V3_stairs_sq24_v12"]
FRAMES = range(4, 20)
ERODE = 32
dump_masks.TAPS["moire"] = ("[high] refine flow A->B (1/8 res)", ["LUMA_A_S", "LUMA_A_E"], """
    vec2 uv = (vec2(ivec2(gl_FragCoord.xy)) + 0.5) / vec2(LUMA_A_E_size);
    float plo = 1.0, phi = 0.0, blo = 1.0, bhi = 0.0;
    for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
            vec2 c = uv + vec2(float(i), float(j)) * LUMA_A_S_pt;
            float p = LUMA_A_S_tex(c).r;
            float b = 0.25 * (LUMA_A_E_tex(c + vec2(-0.25, -0.25) * LUMA_A_S_pt).r + LUMA_A_E_tex(c + vec2(0.25, -0.25) * LUMA_A_S_pt).r
                            + LUMA_A_E_tex(c + vec2(-0.25, 0.25) * LUMA_A_S_pt).r + LUMA_A_E_tex(c + vec2(0.25, 0.25) * LUMA_A_S_pt).r);
            plo = min(plo, p); phi = max(phi, p); blo = min(blo, b); bhi = max(bhi, b);
        }
    }
    float cp = phi - plo, cb = bhi - blo;
    float m = cp > 0.02 ? clamp(1.0 - cb / cp, 0.0, 1.0) : 0.0;
    return vec4(m * 10.0, min(cp * 100.0, 31.0), 0.0, 0.0);""")


def scene(case):
    return subprocess.run(["bash", "-c", f'. "{TESTS}/scenes.sh"; scene {case} 24'], capture_output=True, text=True,
                          check=True).stdout.strip()


def render(work, case, glsl):
    dst = work / f"{case}.rgb48"
    cmd = [FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "warning", "-init_hw_device", "vulkan=vk",
           "-filter_hw_device", "vk", "-f", "lavfi", "-i", scene(case) + ",format=rgb48le",
           "-vf", f"libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path={glsl},format=rgb48le",
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb48le", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    err = r.stderr.lower()
    if r.returncode or any(s in err for s in ("compile status", "disabling", "failed to configure", "error reinit")):
        sys.exit(f"{case}: REFUSED (the shader did not run):\n{r.stderr[:600]}")
    a = np.fromfile(dst, np.uint16)
    n = a.size // (H * W * 3)
    if n < max(FRAMES) + 1: sys.exit(f"{case}: {n} frames, want at least {max(FRAMES) + 1}: REFUSED")
    return (a[: n * H * W * 3].reshape(n, H, W, 3)[:, 4::8, 4::8, :2].astype(np.float64) / 65535.0 - 0.5) * 2 * dump_masks.FS


def main():
    work = pathlib.Path(sys.argv[1]).resolve(); work.mkdir(parents=True, exist_ok=True)
    shader = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "shaders/bidirectional-interpolation-variational-propagated.glsl"
    cases = sys.argv[3].split(",") if len(sys.argv) > 3 else list(CASES)
    glsl = work / "_tap-moire.glsl"
    glsl.write_text(dump_masks.tapped(shader.read_text(), "moire"))
    cy, cx = np.mgrid[0:H // 8, 0:W // 8]
    cy, cx = cy * 8 + 4.0, cx * 8 + 4.0
    out = {}
    print(f"moire_cue: {shader.name}, frames {FRAMES.start}..{FRAMES.stop - 1}, box eroded {ERODE} px")
    print(f"{'case':26s} {'fetch dB':>8s} {'cells':>6s} {'flat%':>6s} {'p10':>6s} {'p25':>6s} {'median':>6s} {'p75':>6s} {'p90':>6s}")
    for c in cases:
        x0, y0, w, h, delta = CASES[c]
        f = render(work, c, glsl)
        vals, flat = [], 0
        for n in FRAMES:
            T = n / 24.0
            m = (cx >= x0(T) + ERODE) & (cx < x0(T) + w - ERODE) & (cy >= y0(T) + ERODE) & (cy < y0(T) + h - ERODE)
            mo, cp = f[n][..., 0][m] / 10.0, f[n][..., 1][m] / 100.0
            vals.append(mo); flat += int((cp <= 0.02).sum())
        v = np.concatenate(vals)
        q = np.percentile(v, [10, 25, 50, 75, 90])
        out[c] = q
        print(f"{c:26s} {delta:+8.1f} {v.size:6d} {100 * flat / v.size:6.1f} " + " ".join(f"{x:6.3f}" for x in q))
    np.save(work / "quantiles.npy", out, allow_pickle=True)
    if not all(c in out for c in GAIN + LOSS): return
    p1, p5 = out["P1_stairs_along_v4"], out["P5_stairs_along_v8_alias"]
    print(f"\nthe decisive pair: P1 median {p1[2]:.3f} [{p1[1]:.3f}, {p1[3]:.3f}], "
          f"P5 median {p5[2]:.3f} [{p5[1]:.3f}, {p5[3]:.3f}]: "
          + ("SAME (within 0.05, bands overlap)" if abs(p1[2] - p5[2]) <= 0.05 and p1[1] <= p5[3] and p5[1] <= p1[3]
             else "DIFFERENT"))
    lo_g, hi_g = min(out[c][1] for c in GAIN), max(out[c][3] for c in GAIN)
    lo_l, hi_l = min(out[c][1] for c in LOSS), max(out[c][3] for c in LOSS)
    holds = hi_l < lo_g or hi_g < lo_l
    print(f"gainers' p25-p75 span [{lo_g:.3f}, {hi_g:.3f}], losers' [{lo_l:.3f}, {hi_l:.3f}]: "
          + ("CUE HOLDS (a threshold separates them)" if holds else
             "CUE FAILS (the bands overlap: moire_s is refused as the gate; next, the two-basin tie cue)"))


if __name__ == "__main__":
    main()
