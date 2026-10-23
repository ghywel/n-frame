#!/usr/bin/env python3
"""COHERENCE_ZM: the coherence gate's zero-motion test made blind to a local change of brightness (2026-10-23;
tests/probes/photometric/PLAN.md, F2). A switch for gen_variational.py, with COHERENCE_GATE=1.

Measured on GPT's TV 73 (a nearly still toaster whose brushed-metal grille catches a moving highlight): High's flow
invents 6-7 px vectors there and High loses 5.6 dB to a blend. The coherence gate exists for exactly this, a patch of
wrong flow its neighbours disagree with, and its first test passes on 99% of the patch (support median 0.08). It stays
closed because its other two tests compare the frames at zero motion with a RAW sum of absolute differences, and the
highlight makes the frames differ at zero although nothing moved (absolute agreement median >= 1, relative 1.85).

COHERENCE_ZM=1 changes only the support pass: both sums (at zero, and at the flow) compare 5 x 5 patches with each
patch's own mean removed, so a local offset of brightness is not counted as disagreement; the contrast it is divided
by, the support count and every threshold are unchanged. Without the variable the output is byte-identical.
    coherence_zm.add(t) -> t      every anchor asserted exactly once
"""

OLD = """    float sad0 = 0.0, sadf = 0.0, lo = 1.0, hi = 0.0;
    vec2 fuv = f0 * LUMA_A_H_pt;
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            vec2 o = vec2(float(x), float(y)) * LUMA_A_H_pt;
            float a = LUMA_A_H_tex(uv + o).r;
            sad0 += abs(a - LUMA_B_H_tex(uv + o).r);
            sadf += abs(a - LUMA_B_H_tex(uv + fuv + o).r);
            lo = min(lo, a); hi = max(hi, a);
        }
    }
"""
NEW = """    // COHERENCE_ZM (tests/coherence_zm.py): each 5 x 5 patch's own mean removed, so a local change of brightness
    // (a highlight sliding on metal, a light coming up) is not read as disagreement at zero motion
    float sad0 = 0.0, sadf = 0.0, lo = 1.0, hi = 0.0;
    vec2 fuv = f0 * LUMA_A_H_pt;
    float ma = 0.0, mb0 = 0.0, mbf = 0.0;
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            vec2 o = vec2(float(x), float(y)) * LUMA_A_H_pt;
            ma += LUMA_A_H_tex(uv + o).r; mb0 += LUMA_B_H_tex(uv + o).r; mbf += LUMA_B_H_tex(uv + fuv + o).r;
        }
    }
    ma /= 25.0; mb0 /= 25.0; mbf /= 25.0;
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            vec2 o = vec2(float(x), float(y)) * LUMA_A_H_pt;
            float a = LUMA_A_H_tex(uv + o).r;
            sad0 += abs((a - ma) - (LUMA_B_H_tex(uv + o).r - mb0));
            sadf += abs((a - ma) - (LUMA_B_H_tex(uv + fuv + o).r - mbf));
            lo = min(lo, a); hi = max(hi, a);
        }
    }
"""


def add(t):
    n = t.count(OLD)
    assert n == 1, f"coherence_zm: the support pass's sums found {n} times (needs COHERENCE_GATE=1)"
    return t.replace(OLD, NEW)
