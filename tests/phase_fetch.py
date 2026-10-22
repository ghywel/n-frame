#!/usr/bin/env python3
"""THE PHASE-EXACT FETCH OF THE COARSE SEARCH'S TARGET TAPS: a switch for gen_variational.py (2026-10-21, the swarm's
wildcard lane; np-scratch/swarm-20261021/wildcard.md, proposal 1 and its pre-registration).

PHASE_FETCH=1 -- in the fused coarse pass (1/16) every SAD reads its TARGET taps from the full-resolution frame at the
position of the reference tap shifted by the candidate's exact offset, instead of from the stored 1/16 luma of the
target frame at that position. The stored level is one sample per 16-px texel on a fixed grid (the downsample passes:
one {tex}_tex({tex}_pos) each); read at a fractional offset it returns a bilinear blend of two fixed-grid samples, so the
target's Moire is the target's grid's and the reference's is the reference's, and they agree only when the candidate is
a whole 1/16 texel (NFRAME-LIMITS.md 2026-09-30, "the lock is a comb in speed, period 8 px": immune within a pixel of
8 and 16; section 8: "point sampling: full contrast, wrong motion at every other speed"). Fetched from the frame at
`uv_target + o`, the target tap is the same scene point as the reference tap shifted by the candidate, sampled on the
same lattice phase, and the match is shift-invariant at every candidate. The texture-period ambiguity (d against d + kP)
is untouched: that is the scene's, and the carry, the cage and the lattice own it. A 1-D numpy model of the two forms
is tests-side in np-scratch/swarm-20261021/wildcard/comb_toy.py.

What changes, and nothing else:
  - the fused coarse pass binds HOOKED (frame A) and NEXT (frame B) beside the 1/16 lumas it already has;
  - two one-line luma helpers before sad5x5_s, the downsample passes' own luma formula;
  - in sad5x5_s (A->B) the B tap LUMA_B_S_tex(uv_b + o).r becomes lum_pf_b(uv_b + o); in sad5x5_s2 (B->A) the A tap
    LUMA_A_S_tex(uv_a + o).r becomes lum_pf_a(uv_a + o). The REFERENCE taps (A in A->B, B in B->A), the contrast gates,
    REG_LAMBDA, TIE_MARGIN, the three descents and the ring are exactly as before. With COARSE_ENERGY=1 the energy term
    keeps its stored-grid .g sample (a 12-px Gaussian field, where the grid is harmless) and only the luma moves.
Why the frame and not the 1/8 luma: LUMA_*_E is made AFTER the coarse pass in this base (propagated base, 707 against
347, moved ahead only by GLOBAL_SEED), and it is itself a fixed grid at 8 px, which would move the comb to period 8
rather than remove it. Taps per candidate are unchanged (9 and 9 at COARSE_WINDOW_RADIUS 1); the 9 target taps now hit
a full-resolution RGB texture 16 px apart instead of a 1/256-size single-channel one, so the pass pays in bandwidth,
not in arithmetic: about 131 candidate evaluations per direction per coarse texel (3 descents of 1 + 5 x 8, plus the
ring), 2 x 131 x 9 / 256 = about 9 full-resolution fetches per output pixel. The gate times it.
Without the variable the output is byte-identical.

PHASE_GATE=1 (2026-10-22, with PHASE_FETCH=1; the gated form of swarm/2026-10-21/wildcard.md, "Item 10's result",
(3)): the fetch traded along the texture period through REACH: where a period alias lies within the coarse search's
23 px, the frame fetch restores the true ambiguity the stored grid had hidden (P1, V3, V1, H1 lost 2.5-6.7 dB), and
where the alias is out of reach it removes a lock (L7 +19.7, P5, M2, L6). The cue is the two-basin tie the pass already
computes: after the three descents under the frame fetch, where the ring descent's basin lies 0.75 coarse texel or
more from the zero descent's AND cost_b is within 10 percent of cost_a, a period alias is in reach, and the three
descents are run again on the stored grid, whose result the texel keeps (both directions; the temporal descent too).
Elsewhere the fetch's result stands. The target taps switch by one pass-level flag (pf_on), so the stored form is the
base's own SAD line, unchanged. Pre-registered kill test (the lane's, verbatim): kills it if any of P1, V3, V1, H1, L1
is still more than 1.0 below the recommendation, or L7/P5/M2/L6 keep less than half their gain, or the capped mean is
under 38.26; confirms with all nine inside those bounds and M1c_v12 unchanged.
KILLED 2026-10-22 (the M5): P1, V3, V1, H1, L1 exactly as ungated and P5's gain lost; the gate never opens where an
alias is in reach (tests/probes/phasefetch/gate_fire.py; NFRAME-LIMITS.md, "The phase fetch gated by the two-basin
tie"). Kept, off.
    phase_fetch.add(t, gate=False) -> t      every anchor asserted exactly once
"""

LUMA = "vec3(0.299, 0.587, 0.114)"

HELPERS = f"""// PHASE_FETCH (tests/phase_fetch.py): the target frame's luma at the EXACT position of the reference tap shifted by
// the candidate, from the full-resolution frame, so both sides of the SAD sit on the same lattice phase. The stored
// 1/16 luma read at a fractional offset is a blend of two fixed-grid samples and matches only at whole texels.
float lum_pf_a(vec2 p) {{ return dot(HOOKED_tex(p).rgb, {LUMA}); }}
float lum_pf_b(vec2 p) {{ return dot(NEXT_tex(p).rgb, {LUMA}); }}
"""

# the SAD lines, in the base's form and in COARSE_ENERGY's form (coarse_energy.py rewrites them before this runs)
SAD_AB = "            s += abs(LUMA_A_S_tex(uv_a + o).r - LUMA_B_S_tex(uv_b + o).r);"
SAD_AB_PF = "            s += abs(LUMA_A_S_tex(uv_a + o).r - lum_pf_b(uv_b + o));"
SAD_BA = "            s += abs(LUMA_B_S_tex(uv_b + o).r - LUMA_A_S_tex(uv_a + o).r);"
SAD_BA_PF = "            s += abs(LUMA_B_S_tex(uv_b + o).r - lum_pf_a(uv_a + o));"
SAD_AB_E = ("            vec2 la = LUMA_A_S_tex(uv_a + o).rg, lb = LUMA_B_S_tex(uv_b + o).rg;\n"
            "            s += abs(la.r - lb.r) + ENERGY_W_S * abs(la.g - lb.g);")
SAD_AB_E_PF = ("            vec2 la = LUMA_A_S_tex(uv_a + o).rg, lb = LUMA_B_S_tex(uv_b + o).rg;\n"
               "            s += abs(la.r - lum_pf_b(uv_b + o)) + ENERGY_W_S * abs(la.g - lb.g);")
SAD_BA_E = ("            vec2 lb2 = LUMA_B_S_tex(uv_b + o).rg, la2 = LUMA_A_S_tex(uv_a + o).rg;\n"
            "            s += abs(lb2.r - la2.r) + ENERGY_W_S * abs(lb2.g - la2.g);")
SAD_BA_E_PF = ("            vec2 lb2 = LUMA_B_S_tex(uv_b + o).rg, la2 = LUMA_A_S_tex(uv_a + o).rg;\n"
               "            s += abs(lb2.r - lum_pf_a(uv_a + o)) + ENERGY_W_S * abs(lb2.g - la2.g);")

# PHASE_GATE: the target tap switches on pf_on; the stored branch is the base's own read
GATED = {
    SAD_AB_PF: "            s += abs(LUMA_A_S_tex(uv_a + o).r - (pf_on ? lum_pf_b(uv_b + o) : LUMA_B_S_tex(uv_b + o).r));",
    SAD_BA_PF: "            s += abs(LUMA_B_S_tex(uv_b + o).r - (pf_on ? lum_pf_a(uv_a + o) : LUMA_A_S_tex(uv_a + o).r));",
    SAD_AB_E_PF: ("            vec2 la = LUMA_A_S_tex(uv_a + o).rg, lb = LUMA_B_S_tex(uv_b + o).rg;\n"
                  "            s += abs(la.r - (pf_on ? lum_pf_b(uv_b + o) : lb.r)) + ENERGY_W_S * abs(la.g - lb.g);"),
    SAD_BA_E_PF: ("            vec2 lb2 = LUMA_B_S_tex(uv_b + o).rg, la2 = LUMA_A_S_tex(uv_a + o).rg;\n"
                  "            s += abs(lb2.r - (pf_on ? lum_pf_a(uv_a + o) : la2.r)) + ENERGY_W_S * abs(lb2.g - la2.g);"),
}
GATE_FLAG = """// PHASE_GATE (tests/phase_fetch.py): the coarse SAD's target taps come from the frame while pf_on, from the stored
// 1/16 luma (the base's read) when the gate below finds a period alias in reach and the descents run again.
bool pf_on = true;
const float PG_SEP = 0.75;          // the two basins' separation, coarse texels (the ring's own exclusion radius)
const float PG_TIE = 0.10;          // cost_b within this fraction of cost_a: a tie
"""


def gate_block(d, uv, sad, desc):
    """The re-run on the stored grid, inserted before the temporal descent of direction d ('' A->B, '2' B->A)."""
    return f"""    // PHASE_GATE: two basins, 0.75 coarse texel or more apart, within 10 percent in cost under the frame fetch: a
    // period alias in reach (the trade's mechanism); the stored grid hides it, so the three descents run there instead
    if (length((off_b - off_a) / LUMA_A_S_pt) >= PG_SEP && abs(cost_b - cost_a) <= PG_TIE * cost_a) {{
        pf_on = false;
        off_a = {desc}({uv}, vec2(0.0), cost_a);
        start_b = vec2(0.0);
        best_ring = 1.0e30;
        for (int y = -1; y <= 1; y++) {{
            for (int x = -1; x <= 1; x++) {{
                if (x == 0 && y == 0)
                    continue;
                vec2 o = vec2(float(x), float(y)) * LUMA_A_S_pt;
                if (length((o - off_a) / LUMA_A_S_pt) < 0.75)
                    continue;
                float c = {sad}({uv}, {uv} + o) + REG_LAMBDA * length(o / LUMA_A_S_pt);
                if (c < best_ring) {{
                    best_ring = c;
                    start_b = o;
                }}
            }}
        }}
        off_b = {desc}({uv}, start_b, cost_b);
    }}
"""


def add(t, gate=False):
    def once(a):
        k = t.count(a)
        assert k == 1, f"phase fetch: anchor found {k} times, expected 1: {a[:70]!r}"

    # the fused coarse pass binds both frames (HOOKED is frame A, NEXT frame B, as the downsample passes bind them)
    a = "//!SAVE FLOW_S_AB\n"
    once(a)
    t = t.replace(a, "//!BIND HOOKED\n//!BIND NEXT\n" + a)
    # the helpers, before the first SAD function of the pass (sad5x5_s2 is in the same pass: the fused base)
    a = "float sad5x5_s(vec2 uv_a, vec2 uv_b) {\n"
    once(a)
    i = t.index(a); j = t.index("float sad5x5_s2(vec2 uv_b, vec2 uv_a) {\n")
    assert i < j and "//!HOOK" not in t[i:j], "phase fetch: sad5x5_s and sad5x5_s2 are not in one fused pass"
    t = t.replace(a, HELPERS + a)
    # the target taps, in whichever form the SAD lines have
    energy = SAD_AB_E in t
    for old, new in ((SAD_AB_E, SAD_AB_E_PF), (SAD_BA_E, SAD_BA_E_PF)) if energy else ((SAD_AB, SAD_AB_PF), (SAD_BA, SAD_BA_PF)):
        once(old)
        t = t.replace(old, new)
    assert "lum_pf_b(uv_b + o)" in t and "lum_pf_a(uv_a + o)" in t
    if not gate:
        return t
    for old, new in ((SAD_AB_E_PF, GATED[SAD_AB_E_PF]), (SAD_BA_E_PF, GATED[SAD_BA_E_PF])) if energy else \
            ((SAD_AB_PF, GATED[SAD_AB_PF]), (SAD_BA_PF, GATED[SAD_BA_PF])):
        once(old)
        t = t.replace(old, new)
    a = "float sad5x5_s(vec2 uv_a, vec2 uv_b) {\n"
    once(a)
    t = t.replace(a, GATE_FLAG + a)
    # each direction: pf_on reset at its start (the pass runs B->A, then A->B, in one thread), the gate before the
    # temporal descent so that descent runs in whichever form the texel kept
    for start, uv, sad, desc in (("    vec2 uv_b = LUMA_A_S_pos;\n", "uv_b", "sad5x5_s2", "descend_s2"),
                                 ("    vec2 uv_a = LUMA_A_S_pos;\n", "uv_a", "sad5x5_s", "descend_s")):
        once(start)
        t = t.replace(start, start + "    pf_on = true;\n")
        c = f"    vec2 off_c = {desc}({uv}, prev_s, cost_c);\n"
        once(c)
        t = t.replace(c, gate_block("", uv, sad, desc) + c)
    assert t.count("        pf_on = false;\n") == 2 and t.count("    pf_on = true;\n") == 2 and t.count("bool pf_on = true;") == 1
    return t
