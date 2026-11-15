#!/usr/bin/env python3
"""Build current/prior High and diagnostic copies externally; source transforms assert their sites."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('content',ROOT/'tests/probes/content/content.py')
content=importlib.util.module_from_spec(spec);spec.loader.exec_module(content)


def diagnostic(text, expression, binds=()):
    marker='//!DESC [high] motion-compensated warp\n'
    assert text.count(marker)==1
    i=text.index(marker);start=text.rfind('//!HOOK FRAME_MIX',0,i)
    end=text.find('//!HOOK FRAME_MIX',i);end=len(text) if end<0 else end
    block=text[start:end]
    anchor='vec4 hook() {\n    // Too different to blend'
    assert block.count(anchor)==1
    block=block.replace(anchor,'vec4 hook() {\n    '+expression+'\n    // Too different to blend')
    for bind in binds:
        if f'//!BIND {bind}\n' not in block:
            block=block.replace('//!BIND HOOKED\n',f'//!BIND HOOKED\n//!BIND {bind}\n')
    return text[:start]+block+text[end:]


def main(out):
    out.mkdir(parents=True,exist_ok=True)
    for name,env in [('high',content.HIGH_ENV),('prev',dict(content.HIGH_ENV,WARP_VOTE='0'))]:
        p=out/f'{name}.glsl';content.generate(env,p)
    high=(out/'high.glsl').read_text()
    assert (out/'high.glsl').read_bytes()==(ROOT/'shaders'/f"{content.SHIPPED['high']}.glsl").read_bytes()
    prev=(out/'prev.glsl').read_text()
    for name,expr,binds in [
        ('field','return vec4(0.5 + FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 / 256.0, 0.5, 1.0);',()),
        ('support','return vec4(SUPPORT_tex(HOOKED_pos).rgb, 1.0);',()),
        ('quarter','return vec4(0.5 + FLOW_Q_AB_tex(HOOKED_pos).xy * 4.0 / 256.0, 0.5, 1.0);',('FLOW_Q_AB',)),
    ]:
        (out/f'{name}.glsl').write_text(diagnostic(high,expr,binds))
    from vote_sampling import add_nearest_weight
    (out/'vote-nearest.glsl').write_text(add_nearest_weight(high))
    old='    return mix(warped, mix(HOOKED_tex(HOOKED_pos), NEXT_tex(NEXT_pos), mix_t), unwarped);'
    assert prev.count(old)==1
    (out/'prev-no-fallback.glsl').write_text(prev.replace(old,'    return warped;'))
    from estimator_ablations import add_e_temporal_off,add_h_data_refine_off
    from aa_pyramid import add_cascade_box
    from newton import add as add_newton
    from obmc import add as add_obmc
    for name,transform in [('prev-e-temporal-off',add_e_temporal_off),
                           ('prev-h-data-refine-off',add_h_data_refine_off),
                           ('prev-aa-box',add_cascade_box),('prev-newton',add_newton),
                           ('prev-obmc8',add_obmc)]:
        (out/f'{name}.glsl').write_text(transform(prev))
    # Reuse the unchanged Nov13 proposal, explicitly on pre-vote High.
    sys.path.insert(0,str(ROOT/'tests/probes/motionstress'))
    spec=importlib.util.spec_from_file_location('motionstress_builder',ROOT/'tests/probes/motionstress/build.py')
    ms=importlib.util.module_from_spec(spec);spec.loader.exec_module(ms)
    assert prev.count(ms.ANCHOR)==1
    (out/'prev-inverse2.glsl').write_text(prev.replace(ms.ANCHOR,ms.ANCHOR+ms.INVERSE))
    (out/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                              for p in out.glob('*.glsl')},indent=2)+'\n')
    print(out)


if __name__=='__main__':main(Path(sys.argv[1]).resolve())
