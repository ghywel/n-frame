#!/usr/bin/env python3
"""Add an endpoint-data acceptance guard to generated inverse2 shader text.

add(text) -> text; text must already contain build.py's inverse2 variant.
No shipped source mutation and no imports from the build module.
Registration: INVERSE-GUARD.md.
"""

HELPER = '''
// MOTIONSTRESS inverse2-data: compare the same endpoint support for both flows.
// GLOBAL_GAIN compensates the matching data only; output colours remain original.
float ms_endpoint_cost(vec2 p, vec2 f) {
    vec2 gg = texelFetch(GLOBAL_GAIN_raw, ivec2(0), 0).rg;
    float sum_cost = 0.0;
    vec2 lo = 0.5 * HOOKED_pt;
    vec2 hi = vec2(1.0) - lo;
    for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
            vec2 q = p + vec2(float(i), float(j)) * HOOKED_pt;
            vec2 a = q - mix_t * f;
            vec2 b = q + (1.0 - mix_t) * f;
            if (any(lessThan(a, lo)) || any(greaterThan(a, hi))
                || any(lessThan(b, lo)) || any(greaterThan(b, hi)))
                return 1.0e6;
            float la = dot(HOOKED_tex(a).rgb, vec3(0.299, 0.587, 0.114));
            float lb = (dot(NEXT_tex(b).rgb, vec3(0.299, 0.587, 0.114)) - gg.y) / gg.x;
            sum_cost += abs(la - lb);
        }
    }
    return sum_cost / 9.0;
}
'''


def add(text):
    assert text.count('// MOTIONSTRESS inverse2:') == 1, 'input must be the generated inverse2 variant'
    marker = '//!DESC [high] motion-compensated warp'
    assert text.count(marker) == 1
    start = text.rfind('//!HOOK FRAME_MIX', 0, text.index(marker))
    end = text.find('//!HOOK FRAME_MIX', text.index(marker))
    assert start >= 0 and end > start
    block = text[start:end]
    assert '//!BIND GLOBAL_GAIN\n' not in block
    assert block.count('//!BIND NEXT\n') == 1 and block.count('vec4 hook() {') == 1
    block = block.replace('//!BIND NEXT\n', '//!BIND NEXT\n//!BIND GLOBAL_GAIN\n', 1)
    block = block.replace('vec4 hook() {', HELPER+'\nvec4 hook() {', 1)
    old = '    float ms_best = length((ms_q + mix_t * ms_next - ms_p) / HOOKED_pt);'
    assert block.count(old) == 1
    block = block.replace(old, old+'\n    float ms_data_best = ms_endpoint_cost(ms_p, flow_ab);')
    old = '        if (all(greaterThanEqual(ms_q, vec2(0.0)))'
    assert block.count(old) == 1
    block = block.replace(old, '        float ms_data = ms_endpoint_cost(ms_p, ms_try);\n'+old)
    old = '            && ms_err + 0.0001 < ms_best) {'
    assert block.count(old) == 1
    block = block.replace(old, '            && ms_err + 0.0001 < ms_best\n'
                              '            && ms_data + 1.0e-6 < ms_data_best) {')
    old = '            ms_best = ms_err;'
    assert block.count(old) == 1
    block = block.replace(old, old+'\n            ms_data_best = ms_data;')
    result = text[:start]+block+text[end:]
    assert result.count('// MOTIONSTRESS inverse2-data:') == 1
    return result
