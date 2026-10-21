#!/usr/bin/env python3
"""THE LOCAL CENTRE OF THE 1/8 LEVEL'S SMALL-MOTION PRIOR: a switch for gen_variational.py (2026-10-21, the swarm's reach
lane; np-scratch/swarm-20261021/reach.md and reach-addendum.md).

LOCAL_CENTRE=1 -- the 1/8 level scores every candidate with SEED_MAG_LAMBDA * |flow - centre| instead of
SEED_MAG_LAMBDA * |flow|. The prior was put there against fisheye bulges on flat ground, toward SMALL motion; at 4.6
1/8-texels of true motion it costs 1.39, more than the SAD gap between the truth and zero on a textured wall (0.87,
emulated on W3), so a correct far candidate loses even when it is in the set. The global seed re-centres it on the
frame's shift (GLOBAL_SEED, 2026-09-20) and cannot see a lone mover. Here the centre is LOCAL: the texel's own best
coarse candidate by cost (the lowest of the zero, ring and temporal descents' costs, taken in the fused coarse pass and
kept in a new storage image per direction, CENTRE_S_AB / CENTRE_S_BA), used only where
  - it lies more than 1.5 coarse texels (24 px) from zero: faded in between 1.0 and 2.0 texels, the global seed's own
    form, so nothing switches; inside that the per-texel search reaches the motion on its own and the prior toward
    zero keeps doing what it was built for (the period family's motions, 0.4-1.5 texels, never open it);
  - and at least LC_AGREE of its 8 coarse neighbours' own winners lie within LC_TOL texel of it (a pan agrees over the
    whole wall; a 3-texel-wide limb's centre column has eight limb neighbours, its edge columns five). Read at the 1/8
    level, one dispatch after the coarse pass wrote them, so every neighbour's value is final.
Elsewhere the centre is zero and every scored term is exactly what it was. With GLOBAL_SEED=1 the frame's shift comes
first: where it is non-zero it is the centre (unchanged from -global), where the frame's gate zeroed it the local centre
takes over. Nothing else changes: no new pass, no new candidate, no change to any SAD.
    local_centre.add(t, global_seed) -> t      every anchor asserted exactly once (or exactly twice where the two directions share a line)
"""
import re

LC_AGREE = 5       # of the 8 coarse neighbours
LC_TOL = 1.0       # coarse texels: a neighbour's winner within this of the texel's own counts as agreeing
LC_FADE = (1.0, 2.0)   # coarse texels: the centre fades in over this range of its own length (1.5 is the midpoint)

TEX = """//!TEXTURE CENTRE_S_{D}
//!SIZE 240 135
//!FORMAT rgba32f
//!STORAGE

"""

# the fused coarse pass: after the three descents, the texel's own winner by cost (zero, ring, temporal), kept for the
# 1/8 level; a flat block (the contrast gate's early return) writes zero like the other caches
WIN = """    {{
        // LOCAL_CENTRE: the texel's own best coarse candidate by cost, for the 1/8 level's prior (tests/local_centre.py)
        vec2 win = off_a; float wc = cost_a;
        if (cost_b < wc) {{ win = off_b; wc = cost_b; }}
        if (cost_c < wc) {{ win = off_c; wc = cost_c; }}
        imageStore(CENTRE_S_{D}, coord, vec4(win / LUMA_A_S_pt, 0.0, 0.0));
    }}
"""

# the 1/8 level: the centre from the texel's own winner and its 3x3 coarse neighbours
READ = """    {{
        // LOCAL_CENTRE (tests/local_centre.py): the prior's centre is the texel's own coarse winner where it is far
        // (faded in over {lo:.1f}-{hi:.1f} coarse texels) and at least {agree} of its 8 coarse neighbours agree within {tol:.1f} texel
        vec2 own = imageLoad(CENTRE_S_{D}, scoord).xy;
        int agree = 0;
        for (int j = -1; j <= 1; j++) {{
            for (int i = -1; i <= 1; i++) {{
                if (i == 0 && j == 0) continue;
                ivec2 q = clamp(scoord + ivec2(i, j), ivec2(0), ivec2({SSIZE}) - 1);
                if (length(imageLoad(CENTRE_S_{D}, q).xy - own) <= {tol:.1f}) agree++;
            }}
        }}
        if (agree >= {agree}) {LHS} = {SIGN}own * smoothstep({lo:.1f}, {hi:.1f}, length(own)) * 2.0 * LUMA_A_E_pt;
    }}
"""


def add(t, global_seed=False):
    def once(a, n=1):
        k = t.count(a)
        assert k == n, f"local centre: anchor found {k} times, expected {n}: {a[:70]!r}"

    # the storage images, after the coarse caches' declarations
    a = "//!TEXTURE FLOW_S_BA_CACHE2\n//!SIZE 240 135\n//!FORMAT rgba32f\n//!STORAGE\n\n"
    once(a)
    t = t.replace(a, a + TEX.format(D="AB") + TEX.format(D="BA"))
    # the fused coarse pass binds both
    a = "//!SAVE FLOW_S_AB\n"
    once(a)
    t = t.replace(a, "//!BIND CENTRE_S_AB\n//!BIND CENTRE_S_BA\n" + a)
    # the flat block's early return writes zero
    for d in ("AB", "BA"):
        a = f"        imageStore(FLOW_S_{d}_CACHE2, coord, result);\n"
        once(a)
        t = t.replace(a, a + f"        imageStore(CENTRE_S_{d}, coord, result);\n")
    # the winner, after the third descent of each direction
    a = "    vec2 off_c = descend_s(uv_a, prev_s, cost_c);\n"
    once(a)
    t = t.replace(a, a + WIN.format(D="AB"))
    a = "    vec2 off_c = descend_s2(uv_b, prev_s, cost_c);\n"
    once(a)
    t = t.replace(a, a + WIN.format(D="BA"))
    # the 1/8 passes bind their direction's image
    for d in ("AB", "BA"):
        a = f"//!SAVE FLOW_E_{d}_RAW\n"
        once(a)
        t = t.replace(a, f"//!BIND CENTRE_S_{d}\n" + a)
    # the two 1/8 RAW passes' spans, as add_global_seed cuts them
    i = t.index("//!SAVE FLOW_E_AB_RAW"); j = t.index("//!SAVE FLOW_E_BA_RAW"); k2 = t.index("//!SAVE FLOW_E_AB\n", j)
    ab, ba = t[i:j], t[j:k2]
    lo, hi = LC_FADE
    if global_seed:
        # g_e exists (the frame's shift, A->B in both passes: the B->A pass adds it); the local centre fills its zero.
        # In the B->A pass the local winner is a B->A flow, so it enters with the sign the pass's terms expect (+ g_e).
        for d, body, sign in (("AB", ab, ""), ("BA", ba, "-")):
            a = "    vec2 g_e = GLOBAL_SHIFT_tex(vec2(0.5)).xy * 2.0 * LUMA_A_E_pt;"
            assert body.count(a) == 1, "local centre: the global seed's g_e line"
            ssize = "LUMA_A_S_size" if d == "AB" else "LUMA_B_S_size"
            blk = READ.format(D=d, SSIZE=ssize, LHS="g_e", SIGN=sign, lo=lo, hi=hi, agree=LC_AGREE, tol=LC_TOL)
            # scoord is declared later in the pass than g_e; place the block right after the base_off3 line
            b = f"    vec2 base_off3 = imageLoad(FLOW_S_{d}_CACHE2, scoord).xy * 2.0 * LUMA_A_E_pt;\n"
            assert body.count(b) == 1, "local centre: the base_off3 line"
            body = body.replace(b, b + "    if (g_e == vec2(0.0))\n" + blk)
            if d == "AB": ab = body
            else: ba = body
    else:
        for d in ("AB", "BA"):
            body = ab if d == "AB" else ba
            n = len(re.findall(r"SEED_MAG_LAMBDA \* length\(ref_(\w) / LUMA_A_E_pt\)", body))
            assert n == 4, f"local centre: {n} prior terms in the {d} pass, expected 4 (a, b, c and the zero seed)"
            body = re.sub(r"SEED_MAG_LAMBDA \* length\(ref_(\w) / LUMA_A_E_pt\)", r"SEED_MAG_LAMBDA * length((ref_\1 - g_e) / LUMA_A_E_pt)", body)
            ssize = "LUMA_A_S_size" if d == "AB" else "LUMA_B_S_size"
            blk = READ.format(D=d, SSIZE=ssize, LHS="g_e", SIGN="", lo=lo, hi=hi, agree=LC_AGREE, tol=LC_TOL)
            b = f"    vec2 base_off3 = imageLoad(FLOW_S_{d}_CACHE2, scoord).xy * 2.0 * LUMA_A_E_pt;\n"
            assert body.count(b) == 1, "local centre: the base_off3 line"
            body = body.replace(b, b + "    vec2 g_e = vec2(0.0);   // the small-motion prior's centre: zero, or the texel's own coarse winner (LOCAL_CENTRE)\n" + blk)
            if d == "AB": ab = body
            else: ba = body
    return t[:i] + ab + ba + t[k2:]
