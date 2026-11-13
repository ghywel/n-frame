#!/usr/bin/env python3
"""WARP_VOTE: the final warp's vector chosen among four candidates by how well the two frames agree (2026-11-13).

    warp_vote.py <in.glsl> <out.glsl>      or, as a module: warp_vote.add(text) -> text

THE DEFECT (tests/probes/occwarp/PLAN.md; GPT's G030 named its first half). The final pass warps both frames along A's
flow read AT THE OUTPUT PIXEL. Where the field is the same on both sides of the pixel that is exact. At a moving
object's leading edge it is not: the output pixel is the object, but in frame A that place is still background, so the
background's vector is used and the object's edge is drawn twice (a ghost bulge); and inside an object whose smooth
parts carry a poorer vector than its features, a feature is drawn with the vector of the smooth patch it has moved onto.

THE CHANGE. Three more candidate vectors are read beside High's own c0 = F_A(p):
    c1 = -F_B(p)                     frame B's opinion at the pixel (the B -> A field, which the prune otherwise drops)
    c2 =  F_A(p - t c0)              A's flow where c0 says the content came from (GPT's inverse step, G029)
    c3 = -F_B(p + (1 - t) c1)        the same from B's side
Each candidate is scored by the mean absolute difference of the two endpoints it implies over 3 x 3 taps 3 px apart
(a 7 px footprint) (B's luma with the adopted global gain taken out, for matching only). The best candidate replaces c0 only where
it explains the frames at least twice as well (cost under WV_KAPPA of c0's) and by more than the noise (WV_EPS), fading
in between; the two PICTURES are blended, so no in-between vector is ever sampled. Where every candidate equals c0
(nearly everywhere) nothing is computed and the output is High's, bit for bit. A candidate that merely ties (a periodic
print's alias, a flat region) never wins.

THE FOOTPRINT (the third form, 2026-11-13). The first form's taps were 1 px apart, and it lost 1.24 dB on the cage:
with a 3 px patch a candidate can put BOTH its endpoints in the flat gap between two thin bars and "match" there,
although the output pixel is on a bar (99% of the added error sat on 7% of the switched pixels, winners 4 to 10 px
from the truth). A guard on the picture's periodicity (the second form) did not catch it. Taps 3 px apart, a 7 px
footprint at the same nine reads, always see a bar: in the CPU replay the cage goes from 1.1 dB under High to 0.26
over it and the faces keep their gain. It does not decide visibility: background uncovered behind a moving object
is seen in one frame only and stays as High draws it.

4K. The two pixel constants carry the _PX suffix scale_shader.py scales with the frame.

4K. The two pixel constants carry the _PX suffix scale_shader.py scales with the frame.

COST, AND WHY THIS IS A VARIANT (tests/probes/occwarp/PLAN.md). It keeps High's half-resolution B -> A chain alive
through the prune (86 -> 103 passes) and scores up to 72 reads at the pixels where a candidate differs: +16.7% on
libplacebo, +15% at 1080p and +20% at 4K on the Metal engine, where High already runs at 59 fps at 1080p on the M5.
Four cheaper forms were measured and dropped: frame B's opinion from the quarter-resolution field (+4.4% with a 2 px
dispute floor, +7.4% without: the cage 0.93 to 0.95 dB down), one cloned half-resolution refine of it (+7.6%, the cage
1.40 down), and abstaining where High's alias detector finds a rival basin (the photographs' gain lost: it flags
object edges). The refined B -> A field is what keeps the cage; the cost is the price of it.
"""
import re
import sys

MARKER = "//!DESC [high] motion-compensated warp"

HELPER = """\
// WARP_VOTE (tests/warp_vote.py): a candidate vector's bilateral cost, the two endpoints it implies compared over
// 3 x 3 taps WV_STEP_PX apart. B's luma has the adopted global gain taken out (matching only; the picture keeps B).
const float WV_KAPPA = 0.5;         // a candidate must explain the frames at least twice as well as High's vector
const float WV_EPS = 2.0 / 255.0;   // and by more than this (the noise floor of a 3 x 3 mean absolute difference)
const float WV_SAME_PX = 0.5;         // px: a candidate this close to High's vector is High's vector
const float WV_STEP_PX = 3.0;         // px between the patch's taps: a 7 px footprint (see THE FOOTPRINT in the module)
float wv_cost(vec2 c, vec2 gg) {
    float acc = 0.0;
    for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
            vec2 o = vec2(float(i), float(j)) * (WV_STEP_PX * HOOKED_pt);
            float a = dot(HOOKED_tex(HOOKED_pos + o - c * mix_t).rgb, vec3(0.299, 0.587, 0.114));
            float b = dot(NEXT_tex(NEXT_pos + o + c * (1.0 - mix_t)).rgb, vec3(0.299, 0.587, 0.114));
            acc += abs(a - (b - gg.y) / gg.x);
        }
    }
    return acc / 9.0;
}
"""

VOTE = """\
    vec4 warped = mix(warped_a, warped_b, mix_t);
    {   // WARP_VOTE: High's vector against B's opinion and the two gathered vectors
        vec2 wv_c1 = -FLOW_H_BA_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;
        vec2 wv_c2 = FLOW_H_AB_tex(HOOKED_pos - flow_ab * mix_t).xy * 2.0 * HOOKED_pt;
        vec2 wv_c3 = -FLOW_H_BA_tex(HOOKED_pos + wv_c1 * (1.0 - mix_t)).xy * 2.0 * HOOKED_pt;
        float wv_d1 = length((wv_c1 - flow_ab) / HOOKED_pt), wv_d2 = length((wv_c2 - flow_ab) / HOOKED_pt),
              wv_d3 = length((wv_c3 - flow_ab) / HOOKED_pt);
        if (max(wv_d1, max(wv_d2, wv_d3)) > WV_SAME_PX) {
            vec2 wv_gg = @GG@;
            float wv_k0 = wv_cost(flow_ab, wv_gg);
            float wv_best = wv_k0; vec2 wv_v = flow_ab;
            if (wv_d1 > WV_SAME_PX) { float k = wv_cost(wv_c1, wv_gg); if (k < wv_best) { wv_best = k; wv_v = wv_c1; } }
            if (wv_d2 > WV_SAME_PX) { float k = wv_cost(wv_c2, wv_gg); if (k < wv_best) { wv_best = k; wv_v = wv_c2; } }
            if (wv_d3 > WV_SAME_PX) { float k = wv_cost(wv_c3, wv_gg); if (k < wv_best) { wv_best = k; wv_v = wv_c3; } }
            float wv_w = (1.0 - smoothstep(0.5 * WV_KAPPA, WV_KAPPA, wv_best / max(wv_k0, 1.0e-6)))
                       * smoothstep(WV_EPS, 2.0 * WV_EPS, wv_k0 - wv_best);
            if (wv_w > 0.0) {
                vec4 wv_new = mix(warp_sample_a(HOOKED_pos - wv_v * mix_t), warp_sample_b(NEXT_pos + wv_v * (1.0 - mix_t)), mix_t);
                warped = mix(warped, wv_new, wv_w);
            }
        }
    }
"""


def add(text):
    assert "WARP_VOTE" not in text, "already applied"
    assert text.count(MARKER) == 1, "expected one final warp pass"
    assert "//!SAVE FLOW_H_BA\n" in text, "WARP_VOTE needs the half-resolution B -> A field (apply before the prune)"
    start = text.rfind("//!HOOK FRAME_MIX", 0, text.index(MARKER))
    nxt = re.search(r"^//!(?:HOOK|TEXTURE|PARAM) ", text[text.index(MARKER) + len(MARKER):], re.M)
    end = text.index(MARKER) + len(MARKER) + nxt.start() if nxt else len(text)
    block = text[start:end]
    assert block.count("//!BIND FLOW_H_AB\n") == 1 and "//!BIND FLOW_H_BA\n" not in block
    block = block.replace("//!BIND FLOW_H_AB\n", "//!BIND FLOW_H_AB\n//!BIND FLOW_H_BA\n", 1)
    gain = "//!SAVE GLOBAL_GAIN\n" in text
    if gain:
        assert "//!BIND GLOBAL_GAIN\n" not in block
        block = block.replace("//!BIND FLOW_H_BA\n", "//!BIND FLOW_H_BA\n//!BIND GLOBAL_GAIN\n", 1)
    assert block.count("\nvec4 hook() {") == 1
    block = block.replace("\nvec4 hook() {", "\n" + HELPER + "vec4 hook() {", 1)
    old = "    vec4 warped = mix(warped_a, warped_b, mix_t);\n"
    assert block.count(old) == 1, "the final blend line was not found"
    vote = VOTE.replace("@GG@", "texelFetch(GLOBAL_GAIN_raw, ivec2(0), 0).rg" if gain else "vec2(1.0, 0.0)")
    block = block.replace(old, vote, 1)
    assert sum(l.startswith("//!BIND") for l in block.split("\n")) <= 16
    out = text[:start] + block + text[end:]
    assert out.count("{") - out.count("}") == text.count("{") - text.count("}")
    return out


if __name__ == "__main__":
    open(sys.argv[2], "w", newline="\n").write(add(open(sys.argv[1]).read()))
