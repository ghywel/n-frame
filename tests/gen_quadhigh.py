#!/usr/bin/env python3
"""Generate FORM Q: today's High on the four-frame window's fixed middle pair (MULTIFRAME-PORT.md, 2026-10-25).

    ./gen_quadhigh.py [output.glsl]       (default: ../shaders/quadhigh-interpolation.glsl)
    QH_CORR=0 ./gen_quadhigh.py out.glsl  the instrument check: the correction forced to zero (must reproduce High)

WHY THIS SHAPE. A four-frame window is {k-1, k, k+1, k+2} at 24 -> 60 and its straddling pair is slots 1 and 2 at every
phase (gen_quaddirectional.py's own window analysis), so the window changes exactly when the middle pair does and a
two-frame estimator's pair caches keep their meaning there. Form Q is therefore two generated files put together:
  - the whole least-squares quad (QUAD_MODE 1; shaders/quaddirectional-interpolation-propagated.glsl), whose three slot
    pairs' plain chains and full-resolution level now feed ONLY the acceleration fit;
  - today's shipped High (the -lattice-cut tier), every pass, renamed into the middle pair: each texture it defines
    takes an HI_ prefix, its frame A reads become slot 1 and its frame B reads slot 2;
and a final pass that is High's own (motion-aware cut gate, support fallback, the warp along High's half-resolution
flow) with the quad's correction s(1 - s) a/2 added to both warp coordinates, gated by the quad's residual and round
trips and by one new test: the quad's plain middle-pair flow must agree with High's (where High repaired an alias the
plain chain still has, the plain acceleration is meaningless and the output is High's). Then the prune.

The conservative form: wherever the correction is off the output is High's, which QH_CORR=0 proves on the ladder before
anything is measured. It costs about High plus the whole quad; the cheaper form (High's flows in the fit, the quad's
plain middle chain dropped) is the follow-up if this one passes.
"""
import os
import pathlib
import re
import sys

import add_human_reading as READING
import prune_passes

HERE = pathlib.Path(__file__).resolve().parent
SHADERS = HERE.parent / "shaders"
QUAD = SHADERS / "quaddirectional-interpolation-propagated.glsl"
HIGH = SHADERS / "bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut.glsl"
DST = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else SHADERS / "quadhigh-interpolation.glsl"
QH_CORR = os.environ.get("QH_CORR", "1")
assert QH_CORR in ("0", "1"), "QH_CORR is 1 (the correction) or 0 (the instrument check: High exactly)"
# FORM Q2 (2026-10-27, MULTIFRAME-PORT.md): High's middle flow in the fit, the quad's plain middle chain and reading tail
# dropped, and the least-squares residual applied as a gate (QH_RESID=0 leaves it off: the isolating variant)
QH_FORM = os.environ.get("QH_FORM", "1")
QH_RESID = os.environ.get("QH_RESID", "1")
assert QH_FORM in ("1", "2", "3", "4") and QH_RESID in ("0", "1"), "QH_FORM is 1 to 4; QH_RESID is 0 or 1"
# FORM Q4 (2026-10-29): Q3 with the acceleration kept only along directions the anchor frame constrains (structure tensor)
# FORM Q3 (2026-10-27): High's estimator on all three slot pairs (HA_ on 0-1, HI_ on 1-2, HC_ on 2-3), no plain chains

SUFFIX = r"(?:_tex|_pos|_pt|_size|_raw|_mul)?\b"     # a texture's name as a bare word or with its accessor suffixes


def sub_n(text, pat, rep, n, flags=0):
    out, k = re.subn(pat, rep, text, flags=flags)
    assert k == n, f"{pat!r}: expected {n} substitutions, made {k}"
    return out


def high_estimator(prefix="HI_", fa="FRAME1", fb="FRAME2"):
    """High's passes up to (not including) its final pass, renamed (prefix) onto one slot pair of a four-frame window:
    frame A read from fa, frame B from fb (slots 1 and 2 for Forms Q and Q2; Q3 adds 0-1 and 2-3)."""
    text = READING.strip_tail(HIGH.read_text())
    text = text[text.index("//!"):]                              # its file header describes a two-frame shader
    est, final = text[:READING.final_pass(text)], text[READING.final_pass(text):]
    names = sorted(set(re.findall(r"^//!(?:SAVE|TEXTURE) (\S+)", est, re.M)))
    assert "FRAME_MIX" not in names and len(names) > 60, f"High defines {len(names)} textures?"
    for n in names:
        est = re.sub(rf"\b{n}(?={SUFFIX})", prefix + n, est)
        final = re.sub(rf"\b{n}(?={SUFFIX})", prefix + n, final)
    # the frames: A is slot 1, B is slot 2. Reads move; geometry stays on HOOKED (every slot has the same geometry),
    # and the size directives (HOOKED.w) are left alone. Pass by pass, so each gains exactly the binds it now reads.
    passes = re.split(r"(?=^//!(?:HOOK|TEXTURE) )", est, flags=re.M)
    out = []
    for p in passes:
        if not p.startswith("//!HOOK"):
            out.append(p)
            continue
        reads_a = "HOOKED_tex(" in p and fa != "HOOKED"            # slot 0 IS the hooked frame: nothing to move
        reads_b = re.search(r"\bNEXT_", p) is not None
        p = p.replace("HOOKED_tex(", fa + "_tex(")
        p = p.replace("NEXT_tex(", fb + "_tex(")
        p = re.sub(r"\bNEXT_(pos|pt|size)\b", r"HOOKED_\1", p)
        binds = []
        if reads_a:
            binds.append(fa)
        if reads_b:
            binds.append(fb)
            if "//!BIND HOOKED\n" not in p:
                binds.append("HOOKED")                            # the geometry the shifted reads now use
        p = p.replace("//!BIND NEXT\n", "")
        lines = p.split("\n")
        last = max(i for i, l in enumerate(lines) if l.startswith("//!BIND") or l.startswith("//!HOOK"))
        for b in reversed(binds):
            if f"//!BIND {b}" not in lines:
                lines.insert(last + 1, f"//!BIND {b}")
        p = "\n".join(lines)
        assert sum(l.startswith("//!BIND") for l in p.split("\n")) <= 16, "a renamed High pass binds more than 16"
        out.append(p)
    est = "".join(out)
    code = "\n".join(l for l in est.split("\n") if not l.lstrip().startswith("//") or l.startswith("//!"))
    assert "NEXT_" not in code and "BIND NEXT" not in code, "a two-frame NEXT reference survived in High's estimator"
    assert fa == "HOOKED" or "HOOKED_tex(" not in code, "a frame-A read was not moved to its slot"
    assert not re.search(r"\bmix_t\b", code), "mix_t is only valid for two frames"
    # High's cut rule, read from its own final pass so it cannot drift
    m = re.search(rf"if \({prefix}SCENE_DIFF_tex\(vec2\(0\.5\)\)\.r > SCENE_CUT_DIFF && cut_res\.r > ([0-9.]+) \* cut_res\.g\)", final)
    assert m, "High's motion-aware cut rule not found in its final pass"
    cut_ratio = m.group(1)
    m = re.search(r"const float SCENE_CUT_DIFF = ([0-9.]+);", final)
    assert m, "High's SCENE_CUT_DIFF not found"
    # High's support fallback, read from its final pass the same way
    sup = re.search(r"float unwarped = (.+?);\n", final, re.S)
    assert sup and "sup.x" in sup.group(1), "High's support fallback not found"
    return est, cut_ratio, m.group(1), " ".join(sup.group(1).split())


CUT_PACK = """\
//!HOOK FRAME_MIX
//!BIND HI_SCENE_DIFF
//!BIND HI_SCENE_RES
//!BIND SCENE_DIFF
//!BIND SCENE_DIFF_BC
//!BIND SCENE_DIFF_CD
//!SAVE QH_CUTS
//!WIDTH 1
//!HEIGHT 1
//!COMPONENTS 4
//!DESC [quadhigh] the five cut statistics in one texel: High's motion-aware verdict on the middle pair, the quad's three pairs
// A pass binds at most 16 textures; the final pass needs the four frames, six full-resolution flows, two half-resolution
// ones and High's support, so the cut statistics come to it packed. .r = High's verdict for slots 1-2 (its own rule,
// copied from its final pass by the generator), .g/.b/.a = the quad's raw statistics for slots 0-1, 1-2 and 2-3.
vec4 hook() {
    vec2 cut_res = HI_SCENE_RES_tex(vec2(0.5)).rg;
    float high_cut = (HI_SCENE_DIFF_tex(vec2(0.5)).r > @CUTDIFF@ && cut_res.r > @CUTRATIO@ * cut_res.g) ? 1.0 : 0.0;
    return vec4(high_cut, SCENE_DIFF_tex(vec2(0.5)).r, SCENE_DIFF_BC_tex(vec2(0.5)).r, SCENE_DIFF_CD_tex(vec2(0.5)).r);
}
"""


CUT_PACK3 = CUT_PACK.replace("//!BIND SCENE_DIFF\n//!BIND SCENE_DIFF_BC\n//!BIND SCENE_DIFF_CD\n",
                              "//!BIND HA_SCENE_DIFF\n//!BIND HC_SCENE_DIFF\n") \
    .replace("SCENE_DIFF_tex(vec2(0.5)).r, SCENE_DIFF_BC_tex(vec2(0.5)).r, SCENE_DIFF_CD_tex(vec2(0.5)).r",
             "HA_SCENE_DIFF_tex(vec2(0.5)).r, HI_SCENE_DIFF_tex(vec2(0.5)).r, HC_SCENE_DIFF_tex(vec2(0.5)).r") \
    .replace("the quad's three pairs", "the three Highs' raw statistics (Form Q3)")
assert "HA_SCENE_DIFF_tex" in CUT_PACK3 and "SCENE_DIFF_BC" not in CUT_PACK3


def quad_parts():
    text = QUAD.read_text()
    text = sub_n(text, r"const int QUAD_MODE = 0;", "const int QUAD_MODE = 1;", 2)
    head_end = text.index("//!")
    body = text[head_end:]
    mk = body.index(READING.MARKER)                         # the reading tail, carried as the quad has it
    fp = READING.final_pass(body[:mk])                      # (the tail's own paint pass also saves FRAME_MIX)
    return body[:fp], body[fp:mk], body[mk:]


def final_pass(quad_final, sup_expr):
    """The quad's final pass, its acceleration fit kept verbatim, its warp replaced by High's."""
    code = quad_final
    # binds: the quad's own plus High's flow and support and the packed cuts; the three raw cut textures go
    code = sub_n(code, r"^//!BIND SCENE_DIFF\n//!BIND SCENE_DIFF_BC\n//!BIND SCENE_DIFF_CD\n",
                 "//!BIND QH_CUTS\n//!BIND HI_FLOW_H_AB\n//!BIND HI_SUPPORT\n", 1, re.M)
    for b in ("FLOW_H_AB", "FLOW_H_CD"):                      # the straddle flows of the edge windows: not read now
        code = sub_n(code, rf"^//!BIND {b}\n", "", 1, re.M)
    code = sub_n(code, r"^//!DESC \[quad\] motion-compensated warp \(cubic placement\)$",
                 "//!DESC [quadhigh] High's warp with the quad's least-squares correction (Form Q)", 1, re.M)
    # the straddle: the interior windows only (slots 1-2); the edges hold the nearer frame
    code = sub_n(code, r"(    float s  = clamp\(\(0\.0 - tA\) / L, 0\.0, 1\.0\);\n)",
                 r"\1    if (p != 1)\n        return s < 0.5 ? slot_tex(p, HOOKED_pos) : slot_tex(p + 1, HOOKED_pos);\n", 1)
    code = sub_n(code, r"    vec2 f_fwd = \(p == 0 \? FLOW_H_AB_tex\(HOOKED_pos\)\.xy\n\s*: p == 1 \? FLOW_H_BC_tex\(HOOKED_pos\)\.xy\n"
                       r"\s*: FLOW_H_CD_tex\(HOOKED_pos\)\.xy\) \* 2\.0 \* HOOKED_pt;\n",
                 "    vec2 f_fwd = HI_FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;      // High's flow, slots 1 -> 2\n"
                 "    vec2 f_plain = FLOW_H_BC_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;   // the quad's own, for the agreement gate\n", 1)
    code = sub_n(code, r"    float cut01 = SCENE_DIFF_tex\(vec2\(0\.5\)\)\.r;\n    float cut12 = SCENE_DIFF_BC_tex\(vec2\(0\.5\)\)\.r;\n"
                       r"    float cut23 = SCENE_DIFF_CD_tex\(vec2\(0\.5\)\)\.r;\n",
                 "    vec4 cuts = QH_CUTS_tex(vec2(0.5));\n    float cut01 = cuts.g;\n    float cut12 = cuts.b;\n    float cut23 = cuts.a;\n", 1)
    code = sub_n(code, r"    float cut_straddle = p == 0 \? cut01 : p == 1 \? cut12 : cut23;\n    if \(cut_straddle > SCENE_CUT_DIFF\)\n",
                 "    if (cuts.r > 0.5)                                    // High's motion-aware verdict on the middle pair\n", 1)
    # the agreement gate and the switch, just before the correction is formed
    code = sub_n(code, r"(    vec2 corr = s \* \(1\.0 - s\) \* \(0\.5 \* accel_w \+ jerk_w \* \(jgeom / 6\.0\)\);\n)",
                 r"\1    // FORM Q: the plain fit is believed only where the plain middle flow agrees with High's (fully under\n"
                 r"    // QH_AGREE_LO px, not at all past QH_AGREE_HI): where High repaired an alias, the output is High's.\n"
                 r"    corr *= 1.0 - smoothstep(QH_AGREE_LO, QH_AGREE_HI, length((f_fwd - f_plain) / HOOKED_pt));\n"
                 r"    if (QH_CORR == 0) corr = vec2(0.0);\n", 1)
    code = sub_n(code, r"(const int QUAD_MODE = 1;\n)",
                 r"\1const float QH_AGREE_LO = 0.5;   // px: the plain and High middle flows agree (Form Q's gate)\n"
                 r"const float QH_AGREE_HI = 1.0;   // px: past this they disagree and the correction is off\n"
                 rf"const int QH_CORR = {QH_CORR};          // 0 = the instrument check: exactly High's warp\n", 1)
    # High's warp and support fallback in place of the quad's plain mix
    code = sub_n(code, r"    vec4 sa = slot_tex\(p, uv_a\);\n    vec4 sb = slot_tex\(p \+ 1, uv_b\);\n\n    return mix\(sa, sb, s\);\n",
                 "    vec4 warped = mix(FRAME1_tex(uv_a), FRAME2_tex(uv_b), s);\n"
                 "    vec3 sup = HI_SUPPORT_tex(HOOKED_pos).rgb;            // High's support and agreement fallback, verbatim\n"
                 f"    float unwarped = {sup_expr};\n"
                 "    if (unwarped <= 0.0) return warped;\n"
                 "    return mix(warped, mix(FRAME1_tex(HOOKED_pos), FRAME2_tex(HOOKED_pos), s), unwarped);\n", 1)
    if QH_FORM in ("2", "3", "4"):
        code = form2(code)
    if QH_FORM in ("3", "4"):
        code = form3(code, sup_expr)
    if QH_FORM == "4":
        code = form4(code)
    assert sum(l.startswith("//!BIND") for l in code.split("\n")) <= 16, "the final pass binds more than 16"
    return code


def form2(code):
    """Form Q2: High's middle flow in the fit in place of the plain one, the agreement gate gone with the plain middle
    chain, and the least-squares residual (in true pixels) applied to the acceleration."""
    for b in ("FLOW_H_BC", "FLOW_F_BC", "FLOW_F_CB"):         # the plain middle chain: no longer read
        code = sub_n(code, rf"^//!BIND {b}\n", "", 1, re.M)
    code = sub_n(code, r"    vec2 f_plain = FLOW_H_BC_tex\(HOOKED_pos\)\.xy \* 2\.0 \* HOOKED_pt;   // the quad's own, for the agreement gate\n", "", 1)
    code = sub_n(code, r"    // FORM Q: the plain fit is believed only.*?\n.*?\n    corr \*= 1\.0 - smoothstep\(QH_AGREE_LO, QH_AGREE_HI, length\(\(f_fwd - f_plain\) / HOOKED_pt\)\);\n",
                 "", 1, re.S)
    code = sub_n(code, r"const float QH_AGREE_LO = 0\.5;.*?\nconst float QH_AGREE_HI = 1\.0;.*?\n",
                 "const float QH_RESID_LO = 0.5;  // px: the least-squares fit's largest residual, fully trusted under this\n"
                 "const float QH_RESID_HI = 1.0;  // px: no correction past this (Form Q2; the agreement gate's scale)\n"
                 f"const int QH_RESID = {QH_RESID};            // 0 = the isolating variant: the residual not applied\n", 1)
    # anchor 1: the middle displacement is High's (slot 1 -> 2); its round trip is High's support's business
    code = sub_n(code, r"        f_next = FLOW_F_BC_tex\(HOOKED_pos\)\.xy \* HOOKED_pt;\n",
                 "        f_next = f_fwd;                                  // FORM Q2: High's middle flow\n", 1)
    code = sub_n(code, r"        vec2 rn = FLOW_F_CB_tex\(HOOKED_pos \+ f_next\)\.xy \* HOOKED_pt;\n        rt_next = length\(f_next \+ rn\) / length\(HOOKED_pt\);\n",
                 "        rt_next = 0.0;                                   // High's link: its support fallback covers it\n", 1)
    # anchor 2: slot 2 -> 1 is High's flow reversed, at the output texel like everything else here
    code = sub_n(code, r"        f_prev = FLOW_F_CB_tex\(HOOKED_pos\)\.xy \* HOOKED_pt;\n",
                 "        f_prev = -f_fwd;                                 // FORM Q2: High's middle flow, reversed\n", 1)
    code = sub_n(code, r"        vec2 rp = FLOW_F_BC_tex\(HOOKED_pos \+ f_prev\)\.xy \* HOOKED_pt;\n        rt_prev = length\(f_prev \+ rp\) / length\(HOOKED_pt\);\n",
                 "        rt_prev = 0.0;                                   // High's link: its support fallback covers it\n", 1)
    # the residual in true pixels, and the gate
    code = sub_n(code, r"(    float resid = 0\.0;\n)", r"\1    float resid_px = 0.0;\n", 1)
    code = sub_n(code, r"(            resid = max\(length\(rp2\), max\(length\(rn2\), length\(rf2\)\)\)\n                  / length\(HOOKED_pt\);\n)",
                 r"\1            resid_px = max(length(rp2 / HOOKED_pt), max(length(rn2 / HOOKED_pt), length(rf2 / HOOKED_pt)));\n", 1)
    code = sub_n(code, r"(        accel \*= g3;\n)",
                 r"\1        if (QH_RESID == 1)                               // FORM Q2: the fit's own residual as a gate\n"
                 r"            accel *= 1.0 - smoothstep(QH_RESID_LO, QH_RESID_HI, resid_px);\n", 1)
    code = code.replace("(Form Q)", "(Form Q2)", 1)
    assert "FLOW_F_BC" not in code and "FLOW_F_CB" not in code and "FLOW_H_BC" not in code, "a plain middle read survived"
    return code


FORM3_ANCHORS = """\
    // FORM Q3: every link is a High estimate, read at the output texel as High's own warp reads its flow: slots 0-1
    // from HA_, 1-2 from HI_ (f_fwd), 2-3 from HC_. High keeps no half-resolution reverse flow, so there are no round
    // trips; a link is believed only where its own High does not fall back (below), and the residual gates the fit.
    vec2 f01 = HA_FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;
    vec2 f23 = HC_FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;
    rt_prev = 0.0;
    rt_next = 0.0;
    rt_far  = 0.0;
    if (anchor == 1) {
        f_prev = -f01;
        f_next = f_fwd;
        // Composed two-interval flow: slot1 -> slot2 -> slot3.
        vec2 link = HC_FLOW_H_AB_tex(HOOKED_pos + f_next).xy * 2.0 * HOOKED_pt;
        f_far  = f_next + link;
        tau_p = (rts_mix[0] - rts_mix[1]) / L;
        tau_n = (rts_mix[2] - rts_mix[1]) / L;
        tau_f = (rts_mix[3] - rts_mix[1]) / L;
        cut_adj  = max(cut01, cut12);
        cut_link = cut23;
    } else {
        f_prev = -f_fwd;
        f_next = f23;
        // Composed two-interval flow: slot2 -> slot1 -> slot0.
        vec2 link = -HA_FLOW_H_AB_tex(HOOKED_pos + f_prev).xy * 2.0 * HOOKED_pt;
        f_far  = f_prev + link;
        tau_p = (rts_mix[1] - rts_mix[2]) / L;
        tau_n = (rts_mix[3] - rts_mix[2]) / L;
        tau_f = (rts_mix[0] - rts_mix[2]) / L;
        cut_adj  = max(cut12, cut23);
        cut_link = cut01;
    }
    float link_fallback = max(qh_unwarped(HA_SUPPORT_tex(HOOKED_pos).rgb), qh_unwarped(HC_SUPPORT_tex(HOOKED_pos).rgb));
"""


def form3(code, sup_expr):
    """Form Q3: the outer links from the HA_ and HC_ Highs in place of the quad's plain full-resolution flows."""
    for b in ("FLOW_F_AB", "FLOW_F_BA", "FLOW_F_CD", "FLOW_F_DC"):
        code = sub_n(code, rf"^//!BIND {b}\n", "", 1, re.M)
    code = sub_n(code, r"^(//!BIND HI_SUPPORT\n)", r"\1//!BIND HA_FLOW_H_AB\n//!BIND HA_SUPPORT\n//!BIND HC_FLOW_H_AB\n//!BIND HC_SUPPORT\n", 1, re.M)
    code = sub_n(code, r"    if \(anchor == 1\) \{\n        f_prev = .*?        cut_link = cut01;\n    \}\n",
                 FORM3_ANCHORS.replace("\\", "\\\\"), 1, re.S)
    code = sub_n(code, r"(            accel \*= 1\.0 - smoothstep\(QH_RESID_LO, QH_RESID_HI, resid_px\);\n)",
                 r"\1        accel *= 1.0 - link_fallback;                     // FORM Q3: an outer High that falls back is not believed\n", 1)
    code = sub_n(code, r"(\nvec4 hook\(\) \{\n)",
                 "\nfloat qh_unwarped(vec3 sup) {   // High's own support fallback weight, copied from its final pass\n"
                 f"    return {sup_expr};\n}}\n" + r"\1", 1)
    code = code.replace("(Form Q2)", "(Form Q3)", 1)
    for gone in ("FLOW_F_AB", "FLOW_F_BA", "FLOW_F_CD", "FLOW_F_DC", "FLOW_F_BC", "FLOW_F_CB"):
        assert gone not in code, f"{gone} survived in Form Q3's final pass"
    return code


def st_pass(luma, name, slot):
    """The structure tensor of one slot from High's half-resolution luma: central-difference gradients, their products
    over a 5 x 5 Gaussian window (sigma 1.5 texels), stored x1000 so the small values keep half-float precision."""
    return f"""\
//!HOOK FRAME_MIX
//!BIND {luma}
//!SAVE {name}
//!WIDTH HOOKED.w 2 /
//!HEIGHT HOOKED.h 2 /
//!COMPONENTS 3
//!DESC [quadhigh] structure tensor of slot {slot} (High's half-resolution luma), 5 x 5 Gaussian window, x1000 (Form Q4)
vec4 hook() {{
    vec2 pt = {luma}_pt;
    vec3 acc = vec3(0.0);
    float ws = 0.0;
    for (int j = -2; j <= 2; j++) {{
        for (int i = -2; i <= 2; i++) {{
            vec2 q = {luma}_pos + vec2(float(i), float(j)) * pt;
            float gx = 0.5 * ({luma}_tex(q + vec2(pt.x, 0.0)).r - {luma}_tex(q - vec2(pt.x, 0.0)).r);
            float gy = 0.5 * ({luma}_tex(q + vec2(0.0, pt.y)).r - {luma}_tex(q - vec2(0.0, pt.y)).r);
            float w = exp(-float(i * i + j * j) / (2.0 * 1.5 * 1.5));
            acc += w * vec3(gx * gx, gx * gy, gy * gy);
            ws += w;
        }}
    }}
    return vec4(1000.0 * acc / ws, 0.0);
}}
"""


FORM4_PROJECT = """\
        // FORM Q4: the acceleration kept only along directions the anchor frame constrains (its structure tensor,
        // Shi-Tomasi per direction): along a clean edge a match is free, and its pair-to-pair noise is not acceleration
        {
            vec3 st = (anchor == 1 ? QH_ST_A_tex(HOOKED_pos).xyz : QH_ST_B_tex(HOOKED_pos).xyz) * 0.001;
            float tr = st.x + st.z;
            float dt = st.x * st.z - st.y * st.y;
            float disc = sqrt(max(0.25 * tr * tr - dt, 0.0));
            float l1 = 0.5 * tr + disc;
            float l2 = max(0.5 * tr - disc, 0.0);
            vec2 e1 = abs(st.y) > 1.0e-12 ? normalize(vec2(st.y, l1 - st.x))
                                          : (st.x >= st.z ? vec2(1.0, 0.0) : vec2(0.0, 1.0));
            vec2 e2 = vec2(-e1.y, e1.x);
            vec2 ap = accel / HOOKED_pt;
            ap = smoothstep(QH_ST_LO, QH_ST_HI, l1) * dot(ap, e1) * e1
               + smoothstep(QH_ST_LO, QH_ST_HI, l2) * dot(ap, e2) * e2;
            accel = ap * HOOKED_pt;
        }
"""


def form4(code):
    """Form Q4: Q3 plus the structure-tensor projection of the acceleration."""
    code = sub_n(code, r"^(//!BIND HC_SUPPORT\n)", r"\1//!BIND QH_ST_A\n//!BIND QH_ST_B\n", 1, re.M)
    i = code.index("        accel *= 1.0 - link_fallback;")
    j = code.index("\n", i) + 1
    code = code[:j] + FORM4_PROJECT + code[j:]
    code = sub_n(code, r"(const int QH_RESID = [01];.*?\n)",
                 r"\1const float QH_ST_LO = 1.0e-4;   // squared luma gradient: a direction is free under this (3x grain)\n"
                 r"const float QH_ST_HI = 4.0e-4;   // and fully constrained over this (13x grain); Form Q4\n", 1)
    code = code.replace("(Form Q3)", "(Form Q4)", 1)
    assert sum(l.startswith("//!BIND") for l in code.split("\n")) <= 16
    return code


HEADER = """\
// =====================================================================
// GENERATED FILE -- DO NOT EDIT BY HAND.  Form Q (MULTIFRAME-PORT.md):
//   {env}./tests/gen_quadhigh.py
// from shaders/quaddirectional-interpolation-propagated.glsl (QUAD_MODE 1) and
// shaders/bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut.glsl
// (today's High, renamed into the window's fixed middle pair, slots 1-2).
//
// Four frames: High's whole estimator on the straddling pair, the quad's plain chains for the least-squares
// acceleration through all four, High's final warp with the quad's correction s(1-s)a/2, gated by the outer
// links' round trips and {gate}.
// Where the correction is off the output is High's. The window's first and last outputs fall back to the
// builtin mixer, as for every four-frame shader.
// =====================================================================
"""


def main():
    est, cut_ratio, cut_diff, sup_expr = high_estimator()
    q_est, q_final, q_tail = quad_parts()
    cut = (CUT_PACK3 if QH_FORM in ("3", "4") else CUT_PACK).replace("@CUTRATIO@", cut_ratio).replace("@CUTDIFF@", cut_diff)
    if QH_FORM in ("2", "3", "4"):
        q_tail = ""                                           # the quad's tail reads the plain middle flows: not carried
    if QH_FORM in ("3", "4"):                                 # three Highs, no plain chain: the quad gives only its final pass
        ha, _, _, _ = high_estimator("HA_", "HOOKED", "FRAME1")
        hc, _, _, _ = high_estimator("HC_", "FRAME2", "FRAME3")
        q_est = ha.rstrip("\n") + "\n\n" + hc
    if QH_FORM == "4":                                        # the two structure tensors, after High's lumas exist
        cut = st_pass("HI_LUMA_A_H", "QH_ST_A", 1) + "\n" + st_pass("HI_LUMA_B_H", "QH_ST_B", 2) + "\n" + cut
    text = q_est.rstrip("\n") + "\n\n" + est.rstrip("\n") + "\n\n" + cut + "\n" + final_pass(q_final, sup_expr) + q_tail
    text, _ = prune_passes.prune(text, twins=True, report=sys.stderr)
    code = "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("//"))
    assert code.count("{") == code.count("}") and code.count("(") == code.count(")"), "unbalanced"
    assert "//!BIND FRAME3" in text, "four frames not declared"
    env = (f"QH_FORM={QH_FORM} " if QH_FORM != "1" else "") + ("QH_RESID=0 " if QH_FORM != "1" and QH_RESID == "0" else "") \
        + ("QH_CORR=0 " if QH_CORR == "0" else "")
    gate = (("all three links from High's estimator (HA_, HI_, HC_), each outer link gated by its High's fallback, "
             if QH_FORM == "3" else "all three links from High's estimator, the acceleration only along directions the anchor's "
            "structure tensor constrains, " if QH_FORM == "4" else "High's middle flow in the fit, ")
            + ("the fit's least-squares residual applied (0.5-1 px)" if QH_RESID == "1"
               else "the residual NOT applied (the isolating variant)")) if QH_FORM in ("2", "3", "4") \
        else "agreement between the quad's plain middle flow and High's (within 0.5-1 px)"
    DST.write_text(HEADER.format(env=env, gate=gate) + text, newline="\n")
    print(f"  {DST.name}: {text.count('//!HOOK')} passes (High {est.count('//!HOOK')} + the quad's), OK")


if __name__ == "__main__":
    main()
