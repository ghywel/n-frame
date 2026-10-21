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
    phase_fetch.add(t) -> t      every anchor asserted exactly once
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


def add(t):
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
    return t
