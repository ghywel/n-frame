#!/usr/bin/env python3
"""GLOBAL_GAIN: the pair's brightness change taken out of what the matcher reads (2026-10-23; tests/probes/photometric/
PLAN.md, F1). A switch for gen_variational.py.

The defect (PLAN.md, measured): the matcher compares raw luma and the texture energy at every level and nothing
compensates a gain or an offset, so a still picture under a pure x1.06 fade is read as motion on a third to a half of
its pixels and High loses 2-4 dB to a plain blend; a real fade-in (GPT's cartoon 6525) loses 5 dB.

GLOBAL_GAIN=1 adds two small passes before everything else:
  [gain] grid   frame A's and frame B's mean luma over each cell of a 32 x 18 grid (8 x 8 bilinear taps a cell);
  [gain] fit    one texel: B = g A + b fitted to the 576 cells by least squares, refitted three times on the cells
                within 2.5 RMS of the previous fit (trimmed, so a moving object does not drive it). The offset alone
                where frame A's cells hardly vary (g = 1). Identity unless the change it describes reaches GG_DEAD
                (2.5 code values) somewhere in [0, 1], or when fewer than half the cells survive the trim; g is
                clamped to [0.5, 2].
and every read of frame B's luma for MATCHING (the energy channel's gradients, the four pyramid levels, the print
lattice's and the prior's full-resolution reads) becomes (l - b) / g. Frame A is never touched; the picture is mixed
from the original frames, so the fade itself is the blend's; the scene-cut statistics and the warp keep the true
frames. Without the variable the output is byte-identical.
GLOBAL_GAIN=1 was KILLED by its pre-registered ladder test (PLAN.md: translating bars and stairs read as a brightness
change, H2x -4.6 dB). GLOBAL_GAIN=2 (F1b) keeps the fit and accepts it only where it explains the frames: a second grid
pass sums the frames' zero-motion difference over the same taps raw and compensated, and the gain is used only if the
compensated sum is under GG_ACCEPT (0.7) of the raw one, else identity.
    global_gain.add(t, accept=False) -> (t, changed passes, reads)      every changed pass counted and asserted
"""
import re

GG_DEAD = 2.5 / 255.0
LUMA = "dot(NEXT_tex({}).rgb, vec3(0.299, 0.587, 0.114))"
KEEP = ("scene-cut statistic", "[cut]", "motion-compensated warp")      # these read the true frames

PASSES = f"""
// ---------------------------------------------------------------------
// GLOBAL_GAIN (tests/global_gain.py, 2026-10-23): the pair's luma gain and offset, so that a fade or a change of
// lighting is not read as motion. Frame B's luma is compensated wherever the matcher reads it; the picture is not.
// ---------------------------------------------------------------------
//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND NEXT
//!SAVE GAIN_GRID
//!WIDTH 32
//!HEIGHT 18
//!COMPONENTS 2
//!DESC [gain] frames A and B: mean luma over each cell of a 32 x 18 grid
vec4 hook() {{
    vec2 c = floor(gl_FragCoord.xy);
    float sa = 0.0, sb = 0.0;
    for (int j = 0; j < 8; j++) {{
        for (int i = 0; i < 8; i++) {{
            vec2 uv = (c + (vec2(float(i), float(j)) + 0.5) / 8.0) / vec2(32.0, 18.0);
            sa += dot(HOOKED_tex(uv).rgb, vec3(0.299, 0.587, 0.114));
            sb += dot(NEXT_tex(uv).rgb, vec3(0.299, 0.587, 0.114));
        }}
    }}
    return vec4(sa / 64.0, sb / 64.0, 0.0, 0.0);
}}

//!HOOK FRAME_MIX
//!BIND GAIN_GRID
//!SAVE {{FIT}}
//!WIDTH 1
//!HEIGHT 1
//!COMPONENTS 2
//!DESC [gain] the pair's luma gain and offset, B = g A + b, a trimmed fit (identity inside the dead band)
const float GG_DEAD = {GG_DEAD:.8f};
vec4 hook() {{
    float g = 1.0, b = 0.0, s = 1.0e9, kept = 0.0;
    for (int it = 0; it < 4; it++) {{
        float sw = 0.0, sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0;
        for (int y = 0; y < 18; y++) {{
            for (int x = 0; x < 32; x++) {{
                vec2 m = texelFetch(GAIN_GRID_raw, ivec2(x, y), 0).rg;
                float w = abs(m.y - (g * m.x + b)) <= 2.5 * s ? 1.0 : 0.0;
                sw += w; sx += w * m.x; sy += w * m.y; sxx += w * m.x * m.x; sxy += w * m.x * m.y;
            }}
        }}
        kept = sw;
        if (sw < 1.0) break;
        float mx = sx / sw, my = sy / sw, vx = sxx / sw - mx * mx;
        g = vx > 1.0e-4 ? clamp((sxy / sw - mx * my) / vx, 0.5, 2.0) : 1.0;
        b = my - g * mx;
        float ss = 0.0, n = 0.0;
        for (int y = 0; y < 18; y++) {{
            for (int x = 0; x < 32; x++) {{
                vec2 m = texelFetch(GAIN_GRID_raw, ivec2(x, y), 0).rg;
                float r = m.y - (g * m.x + b);
                float w = it == 0 || abs(r) <= 2.5 * s ? 1.0 : 0.0;
                ss += w * r * r; n += w;
            }}
        }}
        s = max(sqrt(ss / max(n, 1.0)), 0.5 / 255.0);
    }}
    float effect = max(abs(b), abs(g - 1.0 + b));
    if (effect < GG_DEAD || kept < 0.5 * 576.0)
        return vec4(1.0, 0.0, 0.0, 0.0);
    return vec4(g, b, 0.0, 0.0);
}}
"""
CHECK = """
//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND NEXT
//!BIND GAIN_FIT
//!SAVE GAIN_CHECK
//!WIDTH 32
//!HEIGHT 18
//!COMPONENTS 2
//!DESC [gain] the frames' zero-motion difference over each cell's taps, raw and with the fitted gain taken out
vec4 hook() {
    vec2 c = floor(gl_FragCoord.xy);
    vec2 gg = texelFetch(GAIN_FIT_raw, ivec2(0), 0).rg;
    float raw = 0.0, comp = 0.0;
    for (int j = 0; j < 8; j++) {
        for (int i = 0; i < 8; i++) {
            vec2 uv = (c + (vec2(float(i), float(j)) + 0.5) / 8.0) / vec2(32.0, 18.0);
            float a = dot(HOOKED_tex(uv).rgb, vec3(0.299, 0.587, 0.114));
            float b = dot(NEXT_tex(uv).rgb, vec3(0.299, 0.587, 0.114));
            raw += abs(a - b); comp += abs(a - (b - gg.y) / gg.x);
        }
    }
    return vec4(raw, comp, 0.0, 0.0);
}

//!HOOK FRAME_MIX
//!BIND GAIN_FIT
//!BIND GAIN_CHECK
//!SAVE GLOBAL_GAIN
//!WIDTH 1
//!HEIGHT 1
//!COMPONENTS 2
//!DESC [gain] the fit accepted only if it explains the frames: compensated difference under GG_ACCEPT of the raw
const float GG_ACCEPT = 0.7;
vec4 hook() {
    vec2 gg = texelFetch(GAIN_FIT_raw, ivec2(0), 0).rg;
    float raw = 0.0, comp = 0.0;
    for (int y = 0; y < 18; y++) {
        for (int x = 0; x < 32; x++) {
            vec2 s = texelFetch(GAIN_CHECK_raw, ivec2(x, y), 0).rg;
            raw += s.x; comp += s.y;
        }
    }
    return comp < GG_ACCEPT * raw ? vec4(gg, 0.0, 0.0) : vec4(1.0, 0.0, 0.0, 0.0);
}
"""
HELPER = ("float gg_b(float l) { vec2 gg = texelFetch(GLOBAL_GAIN_raw, ivec2(0), 0).rg; return (l - gg.y) / gg.x; }  "
          "// GLOBAL_GAIN\n")
PAT = re.compile(r"dot\(NEXT_tex\(([^;]*?)\)\.rgb, vec3\(0\.299, 0\.587, 0\.114\)\)")


def add(t, accept=False):
    passes = PASSES.replace('{FIT}', 'GAIN_FIT' if accept else 'GLOBAL_GAIN') + (CHECK if accept else '')
    i = t.index("//!HOOK")
    blocks = t[i:].split("\n//!HOOK")
    out, changed, reads = [], [], 0
    for k, blk in enumerate(blocks):
        blk = blk if k == 0 else "//!HOOK" + blk
        desc = (re.search(r"^//!DESC (.*)$", blk, re.M) or [None, ""])[1]
        n = len(PAT.findall(blk))
        if n and not any(s in desc for s in KEEP):
            assert "//!BIND NEXT\n" in blk, f"global_gain: a pass reads NEXT without binding it: {desc}"
            blk = PAT.sub(lambda m: f"gg_b(dot(NEXT_tex({m.group(1)}).rgb, vec3(0.299, 0.587, 0.114)))", blk)
            blk = blk.replace("//!BIND NEXT\n", "//!BIND NEXT\n//!BIND GLOBAL_GAIN\n", 1)
            lines = blk.split("\n"); j = 0
            while j < len(lines) and lines[j].startswith("//!"):
                j += 1
            lines.insert(j, HELPER.rstrip("\n"))
            blk = "\n".join(lines)
            changed.append(desc); reads += n
        out.append(blk)
    assert reads > 0 and len(changed) >= 3, f"global_gain: only {len(changed)} passes changed"
    for d in ("downsample frame B to 1/16", "downsample frame B to 1/8", "downsample frame B to 1/4", "[energy] frame B"):
        if "//!DESC " + d in t or any(("//!DESC " + d) in b for b in blocks):
            assert any(d in c for c in changed), f"global_gain: no compensated pass '{d}'"
    t = t[:i] + passes.lstrip("\n") + "\n" + "\n//!HOOK".join(b[len("//!HOOK"):] if k else b for k, b in enumerate(out))
    t = t.replace("\n\n//!HOOK", "\n\n//!HOOK")
    return t, changed, reads
