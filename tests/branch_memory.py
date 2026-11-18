#!/usr/bin/env python3
"""BRANCH_MEMORY=1 for gen_variational.py (2026-11-18; tests/probes/barn/PLAN.md): the bars keep the branch they were on.

A periodic surface moving about one period a frame has a lattice of readings that explain the pair equally well (the
truth d, and d - P, d + P ...), and the same lattice in every pair: more frames in the window cannot choose among them
(PRIOR-ART.md). What can is history. On the owner's barn (a corrugated wall, period 27-33 px, a pan of 20-36 px a frame)
the pan starts from rest, where the reading is unambiguous, and High's dominant wall reading followed the truth for
about ninety pairs before dropping it in ONE pair (+23 -> -7, a velocity change no camera makes) where the pan is about a
period and the still reading wins the 1/8 level's small-motion prior. High already has a temporal seed at the 1/8 level,
but (a) it is last pair's COARSE flow, which cannot hold more than 23 px, and (b) it is gated on a forward/backward round
trip, which fails on bars exactly because the two directions pick different branches.

This switch adds a memory with neither limit:
  write  a pass just before the final warp stores the final A->B field (FLOW_H_AB) at 1/8 resolution, in 1/8 texels,
         with a valid flag; at a cut (the final pass's own cut test) it stores the flag cleared, so a new shot starts
         without memory. Zero-initialised storage is the same as "no memory" at the clip's start.
  read   both 1/8 refines (A->B and B->A) take a fifth candidate: the remembered vector at the point this cell came
         from (A->B: the cell minus its own remembered vector, one fixed-point step; B->A: the negated memory, two steps
         back), refined by the level's own +-2 texel search. It replaces the cell's pick ONLY where
           - it is a different branch (more than BM_SEP texels from the pick),
           - its SAD is within BM_TIE (relative) + BM_EPS of the pick's: the frames cannot tell them apart, and
           - the cell has texture (local contrast above BM_CONTRAST): a flat cell's "tie" is not evidence.
         No prior is added and nothing changes where the data decides; the memory only breaks ties.

The risk this is written against (the 2026-09 temporal seed's lesson: an ungated seed re-found its own mistakes and an
accelerating texture lagged): here a remembered branch is taken only on a tie, the candidate is refined to this pair's
own minimum in its basin, and a cut clears it. What it cannot fix: a branch that was wrong from the start (no
unambiguous history), and the passes after the 1/8 level (the quarter-level carry, the print lattice) can still
switch a cell back; the per-level dump will say where.

    branch_memory.add(text)   once, after every other switch and before the prune
"""

import os

# The shipped form (2026-11-18, the owner's verdict on the barn and the exterior shot: "Better"): BM_FORM=2, BM_TIE=0.25.
# Form 1 and tie 0.10 are kept by name for the record (tests/probes/barn/PLAN.md): BM_FORM=1 BM_TIE=0.10.
BM_TIE = float(os.environ.get("BM_TIE", "0.25"))
# BM_FORM=2 (2026-11-18, after form 1's run): the remembered candidate is the LOCAL MAJORITY of the memory over 3 x 3
# samples two cells apart (48 px), where at least five agree within BM_SEP; else the cell's own. Form 1 eroded: a cell
# that lost one tie (grain on a 24 px window) dropped to the alias and its own memory then held the alias, so the wall's
# share at the truth fell 58 -> 36% over five pairs and the mode flipped. The majority re-offers a lost cell its
# neighbours' branch every pair.
BM_FORM = int(os.environ.get("BM_FORM", "2"))
# BM_SUBPIX=1 (2026-11-18, registered in tests/probes/barn/PLAN.md): the remembered candidate refined at half- and
# quarter-texel steps before the tie test; the 1/8 refine steps in whole texels, which favours an alias that sits on them.
BM_SUBPIX = os.environ.get("BM_SUBPIX", "0") == "1"
assert BM_FORM in (1, 2), BM_FORM
BM_EPS = 0.01
BM_SEP = 1.5
BM_CONTRAST = 0.02
SCENE_CUT_DIFF = 0.125      # the final pass's own constant; asserted below

FINAL = "//!DESC [high] motion-compensated warp\n"
E_AB = "//!DESC [high] refine flow A->B (1/8 res)\n"
E_BA = "//!DESC [high] refine flow B->A (1/8 res)\n"
PICK = "    vec4 result = vec4(best_off / LUMA_A_E_pt, 0.0, 0.0);\n"

TEXTURE = """//!TEXTURE BM_AB_ST
//!SIZE 480 270
//!FORMAT rgba32f
//!STORAGE

"""

WRITE = f"""//!HOOK FRAME_MIX
//!BIND FLOW_H_AB
//!BIND LUMA_A_E
//!BIND SCENE_DIFF
//!BIND SCENE_RES
//!BIND BM_AB_ST
//!SAVE BM_W
//!WIDTH HOOKED.w 8 /
//!HEIGHT HOOKED.h 8 /
//!COMPONENTS 1
//!DESC [memory] the final A->B field at 1/8 res, kept for the next pair's 1/8 refines (BRANCH_MEMORY); cleared at a cut
vec4 hook() {{
    if (!pair_changed) return vec4(0.0);
    ivec2 coord = ivec2(LUMA_A_E_pos * LUMA_A_E_size);
    vec2 cut_res = SCENE_RES_tex(vec2(0.5)).rg;
    bool cut = SCENE_DIFF_tex(vec2(0.5)).r > {SCENE_CUT_DIFF} && cut_res.r > 0.300 * cut_res.g;
    vec2 f = FLOW_H_AB_tex(LUMA_A_E_pos).xy * 0.25;      // half-res texels -> 1/8 texels
    imageStore(BM_AB_ST, coord, vec4(f, cut ? 0.0 : 1.0, 0.0));
    return vec4(0.0);
}}

"""


def _read(ab):
    uv = "uv_a" if ab else "uv_b"
    contrast = "local_contrast_5x5_e" if ab else "local_contrast_5x5_e2"
    sad = "sad5x5_e" if ab else "sad5x5_e2"
    # A->B: the cell came from (cell - m) in the previous pair's A; B->A: frame B's cell came from (cell - 2m), and its
    # B->A vector is about -m
    step, sign = ("1", "") if ab else ("2", "-")
    majority = "" if BM_FORM == 1 else f"""            {{   // BM_FORM=2: the local majority of the memory (3 x 3 samples, two cells apart)
                vec2 mv[9]; float mz[9];
                for (int j = 0; j < 9; j++) {{
                    vec4 q = imageLoad(BM_AB_ST, clamp(bmc + 2 * ivec2(j % 3 - 1, j / 3 - 1), ivec2(0), ivec2(LUMA_A_E_size) - 1));
                    mv[j] = q.xy; mz[j] = q.z;
                }}
                int jb = -1, nb = 0;
                for (int j = 0; j < 9; j++) {{
                    if (mz[j] < 0.5) continue;
                    int n = 0;
                    for (int i = 0; i < 9; i++) if (mz[i] > 0.5 && length(mv[i] - mv[j]) <= {BM_SEP}) n++;
                    if (n > nb) {{ nb = n; jb = j; }}
                }}
                if (nb >= 5) bm = {sign}mv[jb] * LUMA_A_E_pt;
            }}
"""
    subpix = "" if not BM_SUBPIX else f"""            for (int st = 0; st < 2; st++) {{   // BM_SUBPIX: half, then quarter texel
                vec2 c0 = ref_m;
                for (int j = 0; j < 9; j++) {{
                    if (j == 4) continue;
                    vec2 c = c0 + vec2(float(j % 3 - 1), float(j / 3 - 1)) * (st == 0 ? 0.5 : 0.25) * LUMA_A_E_pt;
                    float sc = {sad}({uv}, {uv} + c);
                    if (sc < sad_m) {{ sad_m = sc; ref_m = c; }}
                }}
            }}
"""
    return f"""    // BRANCH_MEMORY (tests/branch_memory.py): the previous pair's final vector at the point this cell came from, refined
    // here, takes the cell only on a tie with the pick, on a different branch, on texture.
    {{
        vec4 bm0 = imageLoad(BM_AB_ST, coord);
        if (bm0.z > 0.5) {{
            ivec2 bmc = clamp(coord - {step} * ivec2(floor(bm0.xy + 0.5)), ivec2(0), ivec2(LUMA_A_E_size) - 1);
            vec4 bm1 = imageLoad(BM_AB_ST, bmc);
            vec2 bm = {sign}(bm1.z > 0.5 ? bm1.xy : bm0.xy) * LUMA_A_E_pt;
{majority}            float sad_m;
            vec2 ref_m = refine_e({uv}, bm, sad_m);
{subpix}            float sad_p = {sad}({uv}, {uv} + best_off);
            if (length((ref_m - best_off) / LUMA_A_E_pt) > {BM_SEP} && sad_m <= sad_p * (1.0 + {BM_TIE}) + {BM_EPS}
                && {contrast}({uv}) > {BM_CONTRAST})
                best_off = ref_m;
        }}
    }}
"""


def _pass_bounds(t, desc):
    assert t.count(desc) == 1, f"branch_memory: {desc.strip()} found {t.count(desc)} times"
    d = t.index(desc)
    start = t.rfind("//!HOOK FRAME_MIX\n", 0, d)
    nxt = t.find("//!HOOK ", d)
    tex = t.find("//!TEXTURE ", d)
    end = min(x for x in (nxt, tex, len(t)) if x >= 0)
    return start, end


def add(t):
    assert "BM_AB_ST" not in t, "branch_memory: already applied"
    assert f"const float SCENE_CUT_DIFF = {SCENE_CUT_DIFF};" in t, "branch_memory: the final pass's cut constant moved"
    assert "SCENE_RES" in t, "branch_memory: needs CUT_MOTION=1 (the cut test reads SCENE_RES)"
    # the two 1/8 refines: bind the memory, insert the read before the pick is stored (B->A first: it is later in the text)
    for desc, ab in ((E_BA, False), (E_AB, True)):
        s, e = _pass_bounds(t, desc)
        p = t[s:e]
        assert p.count(PICK) == 1, f"branch_memory: the pick line in {desc.strip()}"
        assert p.count("//!SAVE ") == 1
        i = p.index("//!SAVE ")
        p = p[:i] + "//!BIND BM_AB_ST\n" + p[i:]
        p = p.replace(PICK, _read(ab) + PICK, 1)
        t = t[:s] + p + t[e:]
    # the storage, declared before its first user (the A->B refine)
    s, _ = _pass_bounds(t, E_AB)
    j = t.rfind("//!TEXTURE ", 0, s)
    k = t.rfind("//!HOOK ", 0, s - 1)
    at = j if j > k else s                    # before the refine's own storage declaration, if it has one right above
    t = t[:at] + TEXTURE + t[at:]
    # the write, just before the final warp
    s, _ = _pass_bounds(t, FINAL)
    t = t[:s] + WRITE + t[s:]
    want = 1 + 2 + 2 * 2 + (2 if BM_FORM == 2 else 0) + 1 + 1   # texture, 2 binds, 2x2 loads (+1 a pass for the majority), write bind + store
    assert t.count("BM_AB_ST") == want, (t.count("BM_AB_ST"), want)
    return t
