#!/usr/bin/env python3
"""WHICH COARSE BASIN IS THE TRUTH on P1 and P5, under the stored grid and under the phase fetch (2026-10-22, evening;
after PHASE_GATE's kill: a gate must know WHICH basin is the alias, so the candidate cue was "does off_b - off_a equal the
texture's period?").

    basins.py <work> <rec.glsl> <phase.glsl>

Taps (moire_cue.py's method) after the fused coarse pass: off_a (the zero descent, FLOW_S_AB.xy x 16), off_b (the ring
descent, .zw x 16), and the final half-res flow (FLOW_H_AB x 2, after the warp's last pass), per 1/8 cell inside the box
eroded 32 px, frames 4-19 at N:N. Truth: P1 (4, 0), P5 (8, 0) px per source frame (scenes.sh; TEX_P: 24 px bars along x,
a speckle of period 2 pi 2.2 = 13.8 px in x and 2 pi 1.8 = 11.3 px in y).

PRE-REGISTERED (on paper, before the run): the x aliases of the speckle are v + 13.8 k, so on both cases the two
basins, when distinct, are one speckle period apart (separation 13.8 px = 0.86 coarse texel, x) whatever the speed: a
"separation equals the period" cue is as speed-blind as moire_s and cannot separate P1 from P5. What differs is which
basin is the truth: P1's truth (4) is the smaller-magnitude basin against its alias (-9.8); P5's truth (8) is the larger
against its alias (-5.8), the "alias trap". Predicted reading: under the fetch, P1's final flow sits on an alias and
P5's on the truth; under the stored grid the reverse. Printed per case and shader: the shares of off_a, off_b and the
final x within 1.5 px of the truth and of each alias v +- 13.8, and the separation |off_b - off_a| quartiles.
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import moire_cue                                                                 # noqa: E402

D = moire_cue.dump_masks
TAPS = {
    "Sa": ("[high] coarse flow search A->B and B->A (1/16 res)", ["FLOW_S_AB"],
           "texelFetch(FLOW_S_AB_raw, ivec2(p * FLOW_S_AB_size), 0).xy * 16.0"),
    "Sb": ("[high] coarse flow search A->B and B->A (1/16 res)", ["FLOW_S_AB"],
           "texelFetch(FLOW_S_AB_raw, ivec2(p * FLOW_S_AB_size), 0).zw * 16.0"),
    "H": ("[high] motion-compensated warp", ["FLOW_H_AB"], "texelFetch(FLOW_H_AB_raw, ivec2(p * FLOW_H_AB_size), 0).xy * 2.0"),
}
for k, (desc, binds, expr) in TAPS.items():
    D.TAPS[f"b{k}"] = (desc, binds, f"""
    vec2 p = (gl_FragCoord.xy * 8.0) / HOOKED_size;
    return vec4({expr}, 0.0, 0.0);""")
CASES = {"P1_stairs_along_v4": 4.0, "P5_stairs_along_v8_alias": 8.0}
PER = 2 * np.pi * 2.2


def main():
    work = pathlib.Path(sys.argv[1]).resolve(); work.mkdir(parents=True, exist_ok=True)
    shaders = {"rec": pathlib.Path(sys.argv[2]), "phase": pathlib.Path(sys.argv[3])}
    H, W = moire_cue.H, moire_cue.W
    cy, cx = np.mgrid[0:H // 8, 0:W // 8]
    cy, cx = cy * 8 + 4.0, cx * 8 + 4.0
    for c, v in CASES.items():
        x0, y0, w, h, _ = moire_cue.CASES[c]
        print(f"== {c}: truth ({v:+.0f}, 0); speckle aliases {v - PER:+.1f}, {v + PER:+.1f}")
        for sname, sh in shaders.items():
            got = {}
            for k in TAPS:
                glsl = work / f"_{sname}-{k}.glsl"
                glsl.write_text(D.tapped(sh.read_text(), f"b{k}"))
                f = moire_cue.render(work, f"{c}", glsl)
                vals = []
                for n in moire_cue.FRAMES:
                    T = n / 24.0
                    m = (cx >= x0(T) + 32) & (cx < x0(T) + w - 32) & (cy >= y0(T) + 32) & (cy < y0(T) + h - 32)
                    vals.append(f[n][m])
                got[k] = np.concatenate(vals)
            sep = np.hypot(*(got["Sb"] - got["Sa"]).T)
            line = []
            for k in TAPS:
                x = got[k][:, 0]
                line.append(f"{k}: truth {100 * np.mean(np.abs(x - v) <= 1.5):4.0f}% alias- {100 * np.mean(np.abs(x - (v - PER)) <= 1.5):3.0f}% "
                            f"alias+ {100 * np.mean(np.abs(x - (v + PER)) <= 1.5):3.0f}% med {np.median(x):+.1f}")
            print(f"  {sname:6s} " + " | ".join(line))
            print(f"         separation |off_b - off_a| px: p25 {np.percentile(sep, 25):.1f} med {np.median(sep):.1f} p75 {np.percentile(sep, 75):.1f}")


if __name__ == "__main__":
    main()
