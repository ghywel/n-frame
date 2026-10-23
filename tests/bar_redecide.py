#!/usr/bin/env python3
"""THE ACROSS COMPONENT RE-DECIDED ON A ONE-DIMENSIONAL PRINT: a switch for gen_variational.py (2026-10-22, evening;
NFRAME-LIMITS.md "C3's flow against its truth" and its sequel "why always -9").

What the measurement found (tests/probes/cage/c3_flow.py): on C3 (9 px bars rotating and drifting 1-2 px a frame) the
whole gap between the shipped tiers (22-23 dB on the disc) and the oracle (36.5) is the ACROSS-bar error where it
exceeds 2 px; along-bar and fine errors cost nothing. The coarse levels read the bars' Moire (a 72 px pattern moving
at about -8 times the bars' across speed) and the finer levels, which only nudge, lock the nearest basin of the true
bars: one or two periods out on the fast half of the disc. The pyramid cannot be prefiltered (REFUTED 2026-09-03:
the aliased detail is load-bearing elsewhere), so the re-decision is made where the bars are resolved, at the end.

BAR_REDECIDE=1 -- one pass after the half-res chain's last vector median (A->B; the pruned tiers warp with A->B only),
cached per source pair like the passes around it. Per half-res texel:
  1. ONE-DIMENSIONAL? the 5 x 5 structure tensor of LUMA_A_H: the patch is a print of bars if lambda2 / lambda1 is under
     BAR_ONE_D (0.15, the record's own threshold for a one-dimensional patch, NFRAME-LIMITS.md "C3's aperture") and the
     RMS gradient is over BAR_MIN_GRAD; else the flow is kept as it is.
  2. THE SEARCH along the gradient's direction n (the across direction): candidates v0 + s n for s = -BAR_REACH..
     +BAR_REACH full-res px in 1 px steps (12: a 9 px period and a third either way), each scored by the mean absolute
     difference of a 7 x 7 grid of full-resolution taps 2 px apart (a 13 px block) between frame A at the texel and
     frame B displaced by the candidate (the luma of HOOKED and NEXT, bilinear).
  3. THE CHOICE: among the local minima of that 1-D cost whose cost is within BAR_TIE_REL (25%) of the lowest plus
     BAR_TIE_ABS (1/255), the one whose ACROSS speed |(v0 + s n) . n| is smallest -- the small-motion prior REG_LAMBDA
     already argues for, applied where the bars are resolved instead of where their Moire is -- refined to a sub-pixel
     by a parabola through its neighbours. It replaces the flow only if it moves the across component by more than
     BAR_SWITCH (2 px: a different basin; the fine errors cost nothing); the along component is never touched.
Without the variable the output is byte-identical. A variant whatever it measures (it adds a pass and up to 1225
full-resolution fetches per one-dimensional half-res texel per source pair).

PRE-REGISTERED (written before any render; on the High tier, BAR_REDECIDE=1 against the shipped High file, the M5, one
sitting):
  KILLS it: C3's disc (cage.sh's rectangle) up less than 3.0 dB; or C1 or C2 down more than 0.5 dB on the frame or on
  the cage's rectangle; or any of the 45 ladder cases down more than 1.0 dB; or either capped mean (the frozen 42, the
  headline 42) below High's by more than 0.05.
  PREDICTED: C3's disc 27 to 33 dB (the fast half's period locks undone; some of the smear remains where the 13 px
  block cannot tell basins apart); C1, C2 within 0.2; the ladder unmoved but for the bar cases (V1, V2, V2x, H1, H2,
  H2x, V3, V3x, the P family), each within +-0.5, V3/V3x a coin at their exact half-period tie.

GPT'S COUNTEREXAMPLE (CHAT-LEDGER.md G007/G008; tests/probes/cage/bar_gpu.py, reproduced byte for byte by Local the
same evening): fed a known-correct +6 px/frame on period-9 bars, this pass returns -3 (and -6 -> +3): on an exact
period every basin ties, and the smallest-speed prior erases valid incoming motion. BAR_KEEP=1 (with BAR_REDECIDE=1):
the incoming basin is kept whenever it is itself near-best (any 1-D cost within BAR_SWITCH of s = 0 inside the tie
set); the prior then only replaces an incoming flow that the full-resolution cost has already shown to be worse.
PRE-REGISTERED (before any render): the counterexample is FIXED if bar_gpu.py's +6 and -6 seeds come back within 0.2
px of themselves and +3 stays +3. On C3, against High: if the disc keeps 3.0 dB or more, C3's gain never needed the
prior; under 1.5, the prior was load-bearing (C3's locks are near-ties the full-resolution block cannot rank); between,
partial. Ladder as before (none of the 45 down over 1.0, capped means within 0.05), C1, C2 not down 0.5. Predicted:
fixed; C3 under 1.5 (load-bearing), because the measured locks sit one period out on a print whose wall grain rarely
reaches the 13 px block.
MEASURED the same night: BAR_KEEP fixes the counterexample exactly (+6, -6, +3 kept) but C3 keeps +0.44 of +3.87 and
C2 falls 0.68: the prior is load-bearing, and the keep form is killed.
THE PAIRED FULL-PIPELINE TEST (pre-registered before its render): C4_bars_fast_pan (scenes.sh: C1's bars and wall
panning rigidly across the bars at +6 px/frame, so -3 is the slowest basin), cage.sh's swept rectangle, High against
High + BAR_REDECIDE (and + BAR_KEEP). If High's own flow carries +6 into the last pass, BAR_REDECIDE erases it and
reads 3 dB or more under High; if High already fails there, the two read within 0.5. Predicted: the former (the wall's
grain and the global seed carry the pan), so BAR_REDECIDE is not adoptable as it stands.
BAR_BASIN=1 (with BAR_REDECIDE=1; Local, 2026-10-23, after GPT's G009-G017 and its broader-support guard, bar_guard.py): a
basin change needs broader evidence. The incoming basin is the fine cost's local minimum nearest s = 0 (within 4 px),
parabola-refined as the proposal is; GPT's 7 x 7 SAD at spacing 8 (a 48 px block) scores the proposal against it, each
at its own fine minimum, and the change is made only if the proposal wins by over 1/255; refused, the incoming vector is
kept exactly. A proposal that IS the incoming basin passes unguarded. Measured (tests/probes/cage/bar_basin.py, its
docstring pre-registered; NFRAME-LIMITS.md): GPT's guided scene sends 0 samples to the alias (bars 3.65%, the +-1 px
guard 1.26%) and its damage mask reads 2.6 times better than High; isolated +6, -6, +3 kept; over High C1 +2.47, C2
+0.24, C3 +3.82, C4 +2.34 on the rectangles.
    bar_redecide.add(t, keep=False, basin=False) -> t      every anchor asserted exactly once
"""

BAR_ONE_D = 0.15
BAR_MIN_GRAD = 0.02       # RMS luma gradient over the 5 x 5 (half-res central differences): a print, not a flat wall
BAR_REACH = 12            # full-res px either way along the normal
BAR_TIE_REL = 0.25
BAR_TIE_ABS = 1.0 / 255.0
BAR_SWITCH = 2.0          # px: the across change that counts as a different basin

def pass_text(keep=False):
    return f"""
// ---------------------------------------------------------------------
// BAR_REDECIDE (tests/bar_redecide.py, 2026-10-22): on a one-dimensional print the coarse levels read the bars' Moire
// and the finer levels lock the nearest basin of the true bars, a period or two out (C3). Where the half-res patch is
// one-dimensional, the across component is searched again at full resolution along the bars' normal and the smallest
// across speed among the near-best basins is taken; the along component is never touched.
// ---------------------------------------------------------------------
//!TEXTURE FLOW_H_AB_BARS_CACHE
//!SIZE 1920 1080
//!FORMAT rgba32f
//!STORAGE

//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND NEXT
//!BIND LUMA_A_H
//!BIND FLOW_H_AB_BARS_CACHE
//!BIND FLOW_H_AB
//!SAVE FLOW_H_AB
//!WIDTH HOOKED.w 2 /
//!HEIGHT HOOKED.h 2 /
//!COMPONENTS 2
//!DESC [bars] the across component re-decided on a one-dimensional print (A->B, half res)
const float BAR_ONE_D = {BAR_ONE_D};
const float BAR_MIN_GRAD = {BAR_MIN_GRAD};
const int BAR_REACH = {BAR_REACH};
const float BAR_TIE_REL = {BAR_TIE_REL};
const float BAR_TIE_ABS = {BAR_TIE_ABS:.8f};
const float BAR_SWITCH = {BAR_SWITCH};
float bar_lum_a(vec2 px) {{ return dot(HOOKED_tex(px / HOOKED_size).rgb, vec3(0.299, 0.587, 0.114)); }}
float bar_lum_b(vec2 px) {{ return dot(NEXT_tex(px / HOOKED_size).rgb, vec3(0.299, 0.587, 0.114)); }}
vec4 hook() {{
    ivec2 coord = ivec2(FLOW_H_AB_pos * FLOW_H_AB_size);
    if (!pair_changed)
        return imageLoad(FLOW_H_AB_BARS_CACHE, coord);
    vec2 v0 = FLOW_H_AB_tex(FLOW_H_AB_pos).xy;
    vec4 keep = vec4(v0, 0.0, 0.0);
    float jxx = 0.0, jyy = 0.0, jxy = 0.0;
    for (int j = -2; j <= 2; j++) {{
        for (int i = -2; i <= 2; i++) {{
            vec2 u = FLOW_H_AB_pos + vec2(float(i), float(j)) * LUMA_A_H_pt;
            float gx = 0.5 * (LUMA_A_H_tex(u + vec2(LUMA_A_H_pt.x, 0.0)).r - LUMA_A_H_tex(u - vec2(LUMA_A_H_pt.x, 0.0)).r);
            float gy = 0.5 * (LUMA_A_H_tex(u + vec2(0.0, LUMA_A_H_pt.y)).r - LUMA_A_H_tex(u - vec2(0.0, LUMA_A_H_pt.y)).r);
            jxx += gx * gx; jyy += gy * gy; jxy += gx * gy;
        }}
    }}
    float tr = jxx + jyy, dt = jxx * jyy - jxy * jxy;
    float dsc = sqrt(max(0.25 * tr * tr - dt, 0.0));
    float l1 = 0.5 * tr + dsc, l2 = 0.5 * tr - dsc;
    if (sqrt(l1 / 25.0) < BAR_MIN_GRAD || l2 > BAR_ONE_D * l1) {{
        imageStore(FLOW_H_AB_BARS_CACHE, coord, keep);
        return keep;
    }}
    vec2 n = abs(jxy) > 1.0e-12 ? normalize(vec2(l1 - jyy, jxy)) : (jxx >= jyy ? vec2(1.0, 0.0) : vec2(0.0, 1.0));
    vec2 c = FLOW_H_AB_pos * HOOKED_size;
    vec2 vf = v0 * 2.0;
    float a[49];
    for (int y = -3; y <= 3; y++)
        for (int x = -3; x <= 3; x++)
            a[(y + 3) * 7 + x + 3] = bar_lum_a(c + vec2(float(x), float(y)) * 2.0);
    float cost[2 * BAR_REACH + 1];
    float cmin = 1.0e30;
    for (int s = -BAR_REACH; s <= BAR_REACH; s++) {{
        vec2 v = vf + float(s) * n;
        float sad = 0.0;
        for (int y = -3; y <= 3; y++)
            for (int x = -3; x <= 3; x++)
                sad += abs(a[(y + 3) * 7 + x + 3] - bar_lum_b(c + vec2(float(x), float(y)) * 2.0 + v));
        cost[s + BAR_REACH] = sad / 49.0;
        cmin = min(cmin, sad / 49.0);
    }}
    float tie = cmin * (1.0 + BAR_TIE_REL) + BAR_TIE_ABS;
{KEEP_BLOCK if keep else ""}    int best = -1;
    float best_mag = 1.0e30;
    for (int i = 1; i < 2 * BAR_REACH; i++) {{
        if (cost[i] > cost[i - 1] || cost[i] > cost[i + 1] || cost[i] > tie)
            continue;
        float mag = abs(dot(vf, n) + float(i - BAR_REACH));
        if (mag < best_mag - 0.5 || (mag < best_mag + 0.5 && best >= 0 && abs(i - BAR_REACH) < abs(best - BAR_REACH))) {{
            best_mag = min(mag, best_mag);
            best = i;
        }}
    }}
    if (best < 0) {{
        imageStore(FLOW_H_AB_BARS_CACHE, coord, keep);
        return keep;
    }}
    float den = cost[best - 1] - 2.0 * cost[best] + cost[best + 1];
    float sub = den > 1.0e-9 ? clamp(0.5 * (cost[best - 1] - cost[best + 1]) / den, -0.5, 0.5) : 0.0;
    float s = float(best - BAR_REACH) + sub;
    if (abs(s) <= BAR_SWITCH) {{
        imageStore(FLOW_H_AB_BARS_CACHE, coord, keep);
        return keep;
    }}
    vec4 result = vec4((vf + s * n) * 0.5, 0.0, 0.0);
    imageStore(FLOW_H_AB_BARS_CACHE, coord, result);
    return result;
}}
"""


KEEP_BLOCK = """    // BAR_KEEP: the incoming basin stays whenever it is itself near-best (GPT's counterexample, G008)
    for (int i = BAR_REACH - int(BAR_SWITCH); i <= BAR_REACH + int(BAR_SWITCH); i++) {
        if (cost[i] <= tie) {
            imageStore(FLOW_H_AB_BARS_CACHE, coord, keep);
            return keep;
        }
    }
"""
PASS = pass_text(False)
PASS_KEEP = pass_text(True)

# BAR_BASIN: GPT's broader-support SAD (tests/probes/cage/bar_guard.py's HELPER, G011, verbatim) judging basin against
# basin, each at its own fine minimum (tests/probes/cage/bar_basin.py, Local, 2026-10-23).
GUARD_HELPER = """float guard_sad(vec2 c, vec2 v) {
    float sad = 0.0;
    for (int y=-3; y<=3; y++) for (int x=-3; x<=3; x++) {
        vec2 q=c+8.0*vec2(float(x),float(y));
        sad += abs(bar_lum_a(q)-bar_lum_b(q+v));
    }
    return sad/49.0;
}
"""
BASIN_BLOCK = """    // BASIN AGAINST BASIN (tests/probes/cage/bar_basin.py): the incoming basin at its own fine minimum
    int ib = -1;
    for (int k = 0; k <= 4; k++) {
        int lo = BAR_REACH - k, hi = BAR_REACH + k;
        if (ib < 0 && cost[lo] <= cost[lo - 1] && cost[lo] <= cost[lo + 1]) ib = lo;
        if (ib < 0 && cost[hi] <= cost[hi - 1] && cost[hi] <= cost[hi + 1]) ib = hi;
    }
    if (ib != best) {
        float s_in = 0.0;
        if (ib >= 0) {
            float d2 = cost[ib - 1] - 2.0 * cost[ib] + cost[ib + 1];
            s_in = float(ib - BAR_REACH) + (d2 > 1.0e-9 ? clamp(0.5 * (cost[ib - 1] - cost[ib + 1]) / d2, -0.5, 0.5) : 0.0);
        }
        if (guard_sad(c, vf + s * n) >= guard_sad(c, vf + s_in * n) - 1.0 / 255.0) {
            vec4 kept = keep;
            imageStore(FLOW_H_AB_BARS_CACHE, coord, kept);
            return kept;
        }
    }
"""
BASIN_ANCHOR = "    vec4 result = vec4((vf + s * n) * 0.5, 0.0, 0.0);"
assert PASS.count("vec4 hook() {") == 1 and PASS.count(BASIN_ANCHOR) == 1
PASS_BASIN = PASS.replace("vec4 hook() {", GUARD_HELPER + "vec4 hook() {").replace(BASIN_ANCHOR, BASIN_BLOCK + BASIN_ANCHOR)


def add(t, keep=False, basin=False):
    d = "//!DESC [high] vector median filter on flow A->B (pass 2)\n"
    k = t.count(d)
    assert k == 1, f"bar_redecide: the half-res chain's last median found {k} times"
    i = t.index(d)
    j = t.index("\n}\n", i) + 3
    assert "//!HOOK" not in t[i:j], "bar_redecide: the median pass's body runs into another pass"
    for need in ("//!SAVE LUMA_A_H\n", "//!BIND NEXT\n"):
        assert need in t, f"bar_redecide: the shader has no {need.strip()}"
    assert not (keep and basin), "bar_redecide: BAR_KEEP and BAR_BASIN are alternatives"
    return t[:j] + (PASS_KEEP if keep else PASS_BASIN if basin else PASS) + t[j:]
