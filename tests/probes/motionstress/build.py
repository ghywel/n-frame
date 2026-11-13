#!/usr/bin/env python3
"""Regenerate current High, assert shipped identity, then build motionstress experiments.

    build.py OUT
Generated GLSL remains outside the repository. No manual shader edits.
"""
import importlib.util
import json
from pathlib import Path
import sys
import hashlib
import global_candidate
import inverse_guard

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('content',ROOT/'tests/probes/content/content.py')
content=importlib.util.module_from_spec(spec);spec.loader.exec_module(content)
ANCHOR='    vec2 flow_ab = FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;'
INVERSE='''
    // MOTIONSTRESS inverse2: F is indexed in A, not at output p.
    // Bounded fixed-point candidates, selected only by improved reprojection.
    // Ambiguous foreground/background roots remain ambiguous; ties retain High.
    vec2 ms_p = HOOKED_pos;
    vec2 ms_q = ms_p - mix_t * flow_ab;
    vec2 ms_next = FLOW_H_AB_tex(ms_q).xy * 2.0 * HOOKED_pt;
    float ms_best = length((ms_q + mix_t * ms_next - ms_p) / HOOKED_pt);
    for (int ms_i = 0; ms_i < 2; ms_i++) {
        vec2 ms_try = ms_next;
        ms_q = ms_p - mix_t * ms_try;
        ms_next = FLOW_H_AB_tex(ms_q).xy * 2.0 * HOOKED_pt;
        float ms_err = length((ms_q + mix_t * ms_next - ms_p) / HOOKED_pt);
        if (all(greaterThanEqual(ms_q, vec2(0.0))) && all(lessThanEqual(ms_q, vec2(1.0)))
            && ms_err + 0.0001 < ms_best) {
            flow_ab = ms_try;
            ms_best = ms_err;
        }
    }
'''


def main(out):
    out.mkdir(parents=True,exist_ok=True)
    base=out/'high.glsl';content.generate(content.HIGH_ENV,base)
    shipped=ROOT/'shaders'/f"{content.SHIPPED['high']}.glsl"
    assert base.read_bytes()==shipped.read_bytes(),'Regenerated High does not equal shipped High'
    text=base.read_text();assert text.count(ANCHOR)==1
    dst=out/'inverse2.glsl';dst.write_text(text.replace(ANCHOR,ANCHOR+INVERSE))
    assert dst.read_text().count('MOTIONSTRESS inverse2')==1
    guard_dst=out/'inverse-data.glsl';guard_dst.write_text(inverse_guard.add(dst.read_text()))
    global_dst=out/'global-fullres.glsl';global_dst.write_text(global_candidate.add(text))
    combined=out/'combined.glsl';combined.write_text(global_candidate.add(guard_dst.read_text()))
    (out/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in (base,dst,global_dst,guard_dst,combined)},indent=2)+'\n')
    print(out)


if __name__=='__main__':main(Path(sys.argv[1]).resolve())
