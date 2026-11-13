#!/usr/bin/env python3
"""Additional full-resolution global-pan witness for the current High variant.

add(text) -> text. Source transforms are asserted; generated shaders stay external.
Registration and limitations: GLOBAL-PREDICTION.md. No GPU work on import.
"""
import re


PASS = '''//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND NEXT
//!BIND GLOBAL_GAIN
//!BIND LUMA_A_S
//!SAVE GLOBAL_VERIFY_COST
//!WIDTH 17
//!HEIGHT 9
//!COMPONENTS 4
//!DESC [motionstress] full-resolution pan witness: residual, zero residual, majority support and valid fraction
vec4 hook() {
    ivec2 c = ivec2(gl_FragCoord.xy);
    vec2 shift = (vec2(c) * 0.5 - vec2(4.0, 2.0)) * LUMA_A_S_pt;
    vec2 gg = texelFetch(GLOBAL_GAIN_raw, ivec2(0), 0).rg;
    const int N = 16;
    float residual = 0.0, zero = 0.0, good = 0.0, valid = 0.0;
    for (int y = 0; y < N; y++) {
        for (int x = 0; x < N; x++) {
            vec2 uv = vec2(0.15) + (vec2(float(x), float(y)) + 0.5) / float(N) * 0.7;
            vec2 bv = uv + shift;
            if (any(lessThan(bv, 0.5 * HOOKED_pt)) || any(greaterThan(bv, vec2(1.0) - 0.5 * HOOKED_pt))) continue;
            float a = dot(HOOKED_tex(uv).rgb, vec3(0.299, 0.587, 0.114));
            float b0 = (dot(NEXT_tex(uv).rgb, vec3(0.299, 0.587, 0.114)) - gg.y) / gg.x;
            float bs = (dot(NEXT_tex(bv).rgb, vec3(0.299, 0.587, 0.114)) - gg.y) / gg.x;
            float r = abs(a-bs), z = abs(a-b0);
            residual += r; zero += z; valid += 1.0;
            if (z > 2.0 / 255.0 && r < 0.25 * z) good += 1.0;
        }
    }
    return vec4(residual / max(valid, 1.0), zero / max(valid, 1.0), good / float(N*N), valid / float(N*N));
}

'''

CHOOSE = '''    // MOTIONSTRESS global-fullres: preserve the existing result unless a broad direct witness wins.
    bool ms_verified = false;
    float ms_best = 1.0e30;
    vec2 ms_shift = vec2(0.0);
    for (int y = 0; y < 9; y++) {
        for (int x = 0; x < 17; x++) {
            vec4 v = texelFetch(GLOBAL_VERIFY_COST_raw, ivec2(x, y), 0);
            if (v.a < 0.95 || v.r >= 1.5 / 255.0 || v.r >= 0.20 * v.g || v.b < 0.65) continue;
            vec2 s = vec2(float(x), float(y)) * 0.5 - vec2(4.0, 2.0);
            float cost = v.r + 0.002 * length(s);
            if (cost < ms_best) { ms_best = cost; ms_shift = s; ms_verified = true; }
        }
    }
    if (ms_verified) bestShift = ms_shift;
'''


def add(text):
    assert '//!SAVE GLOBAL_VERIFY_COST' not in text, 'Already patched'
    assert text.count('//!SAVE GLOBAL_GAIN\n') == 1, 'Requires current GLOBAL_GAIN High'
    blocks = re.split(r'(?=^//!HOOK FRAME_MIX\n)', text, flags=re.M)
    found = []
    for i, block in enumerate(blocks):
        if '//!SAVE GLOBAL_SHIFT\n' not in block:
            continue
        assert '//!WIDTH 1\n//!HEIGHT 1\n' in block
        assert 'for (int y = 0; y < 9; y++)' in block and 'for (int x = 0; x < 17; x++)' in block
        assert block.count('//!BIND GLOBAL_COST\n') == 1
        block = block.replace('//!BIND GLOBAL_COST\n', '//!BIND GLOBAL_COST\n//!BIND GLOBAL_VERIFY_COST\n')
        anchor = '    vec2 prev = imageLoad(GLOBAL_PREV, ivec2(0)).xy;'
        assert block.count(anchor) == 1
        block = block.replace(anchor, CHOOSE + anchor)
        gate = '    if (GLOBAL_COST_tex((vec2(17 / 2, 9 / 2) + 0.5) / GLOBAL_COST_size).g > GLOBAL_MOIRE_MAX) bestShift = vec2(0.0);'
        assert block.count(gate) == 1
        block = block.replace(gate, gate.replace('if (GLOBAL_COST', 'if (!ms_verified && GLOBAL_COST'))
        # The previous GLOBAL_PREV storage declaration belongs to the preceding block;
        # inserting a pass here leaves it defined before both users.
        blocks[i] = PASS + block
        found.append(i)
    assert len(found) == 1, f'Expected one global-shift block, found {len(found)}'
    result = ''.join(blocks)
    assert result.count('MOTIONSTRESS global-fullres') == 1
    assert result.count('if (pair_changed) imageStore(GLOBAL_PREV') == text.count('if (pair_changed) imageStore(GLOBAL_PREV')
    return result
