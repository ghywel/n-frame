#!/usr/bin/env python3
"""WHERE THE PHASE GATE OPENS: the gate's decision and its two inputs per coarse texel, on the cases the fetch moved
(2026-10-22; PHASE_GATE in tests/phase_fetch.py; read beside the ladder, never instead of it).

    gate_fire.py <work> <gate.glsl> [cases=moire_cue's nine + M1c_noise_v12]

A diagnostic copy of the gated shader (gate.glsl, PHASE_FETCH=1 PHASE_GATE=1) records, in the A->B direction, the
two-basin separation (coarse texels) and the relative cost gap (cost_b - cost_a) / cost_a as the frame fetch's descents
found them, and whether the gate opened, into FLOW_S_AB_CACHE2's spare .zw (the temporal descent's store, whose z and
w the recommendation writes as 0); moire_cue.py's tap method then reads them per 1/8 cell after the fused coarse pass,
inside each case's box eroded 32 px, frames 4-19 at N:N. The diagnostic copy's picture is not scored (its own later
passes may read the spare channels); only the coarse pass's decision is read, and that pass is the gated one's, byte
for byte, up to the store.

Printed per case: the share of texels where the gate opened; the share with two basins (separation >= 0.75 texel);
among those, the relative cost gap's quartiles (the tie threshold is 0.10).
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import moire_cue                                                                 # noqa: E402  (CASES, render, the tap)

D = moire_cue.dump_masks
D.TAPS["fire"] = ("[high] coarse flow search A->B and B->A (1/16 res)", ["FLOW_S_AB", "FLOW_S_AB_CACHE2"], """
    vec2 p = (gl_FragCoord.xy * 8.0) / HOOKED_size;
    vec4 g = imageLoad(FLOW_S_AB_CACHE2, ivec2(p * FLOW_S_AB_size));
    float fired = g.z >= 100.0 ? 1.0 : 0.0;
    float sep = g.z - 100.0 * fired;
    return vec4(fired * 10.0 + min(sep, 0.99), clamp(g.w * 10.0, -31.0, 31.0), 0.0, 0.0);""")


def diag(gate_text):
    """the gated shader with its A->B decision inputs stored in FLOW_S_AB_CACHE2.zw (z = separation + 100 if opened)"""
    t = gate_text
    a = "        pf_on = false;\n        off_a = descend_s(uv_a, vec2(0.0), cost_a);\n"
    assert t.count(a) == 1
    t = t.replace(a, "        pg_open = 100.0;\n" + a)
    a = "    if (length((off_b - off_a) / LUMA_A_S_pt) >= PG_SEP && abs(cost_b - cost_a) <= PG_TIE * cost_a) {\n"
    assert t.count(a) == 2
    i = t.rindex(a)                                              # the A->B direction (hook(), after coarse_ba())
    t = t[:i] + ("    float pg_sep = length((off_b - off_a) / LUMA_A_S_pt), pg_rel = (cost_b - cost_a) / max(cost_a, 1.0e-6);\n"
                 "    float pg_open = 0.0;\n") + t[i:]
    a = "    imageStore(FLOW_S_AB_CACHE2, coord, vec4(off_c / LUMA_A_S_pt, 0.0, 0.0));\n"
    assert t.count(a) == 1
    t = t.replace(a, "    imageStore(FLOW_S_AB_CACHE2, coord, vec4(off_c / LUMA_A_S_pt, pg_open + min(pg_sep, 0.99), pg_rel));\n")
    return t


def main():
    work = pathlib.Path(sys.argv[1]).resolve(); work.mkdir(parents=True, exist_ok=True)
    gate = pathlib.Path(sys.argv[2]).read_text()
    cases = sys.argv[3].split(",") if len(sys.argv) > 3 else list(moire_cue.CASES) + ["M1c_noise_v12"]
    moire_cue.CASES.setdefault("M1c_noise_v12", (lambda T: 288 * T, lambda T: 210, 300, 300, 0.0))
    glsl = work / "_tap-fire.glsl"
    glsl.write_text(D.tapped(diag(gate), "fire"))
    H, W = moire_cue.H, moire_cue.W
    cy, cx = np.mgrid[0:H // 8, 0:W // 8]
    cy, cx = cy * 8 + 4.0, cx * 8 + 4.0
    print(f"gate_fire: frames {moire_cue.FRAMES.start}..{moire_cue.FRAMES.stop - 1}, box eroded {moire_cue.ERODE} px, A->B")
    print(f"{'case':26s} {'fetch dB':>8s} {'cells':>6s} {'opened%':>8s} {'2basin%':>8s} | rel gap among 2-basin: p10 p25 med p75 p90")
    for c in cases:
        x0, y0, w, h, delta = moire_cue.CASES[c]
        f = moire_cue.render(work, c, glsl)
        X, Y = [], []
        for n in moire_cue.FRAMES:
            T = n / 24.0
            m = (cx >= x0(T) + moire_cue.ERODE) & (cx < x0(T) + w - moire_cue.ERODE) & \
                (cy >= y0(T) + moire_cue.ERODE) & (cy < y0(T) + h - moire_cue.ERODE)
            X.append(f[n][..., 0][m]); Y.append(f[n][..., 1][m] / 10.0)
        x, rel = np.concatenate(X), np.concatenate(Y)
        opened = x >= 9.5
        sep = np.where(opened, x - 10.0, x)                   # min(sep, 0.99): >= 0.75 is two basins
        two = sep >= 0.745
        q = np.percentile(rel[two], [10, 25, 50, 75, 90]) if two.any() else [np.nan] * 5
        print(f"{c:26s} {delta:+8.1f} {x.size:6d} {100 * opened.mean():8.1f} {100 * two.mean():8.1f} | "
              + " ".join(f"{v:+.3f}" for v in q))


if __name__ == "__main__":
    main()
