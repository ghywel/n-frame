#!/usr/bin/env python3
"""Exercise the actual render/decode guards with a broken shader and a short stream.

failure_controls.py OUT SOURCE_12_FRAME_MKV --ffmpeg PATH
One deliberately failed GPU render; run serially with other GPU jobs.
"""
import argparse
import json
from pathlib import Path
from run import call, read


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out',type=Path);ap.add_argument('source',type=Path)
    ap.add_argument('--ffmpeg',required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    shader=a.out/'deliberately-broken.glsl'
    shader.write_text('//!HOOK FRAME_MIX\n//!BIND HOOKED\n//!BIND NEXT\n'
                      'vec4 hook() { return MOTIONSTRESS_UNDEFINED_SYMBOL; }\n')
    rejected={}
    try:
        call([a.ffmpeg,'-nostdin','-v','warning','-init_hw_device','vulkan=vk','-filter_hw_device','vk',
              '-i',str(a.source),'-vf',f'settb=expr=1/120,setpts=N*5,libplacebo=fps=60:frame_mixer=custom_n:custom_shader_path={shader.resolve()}',
              '-an','-f','null','-'],a.out/'broken-shader.log',gpu=True)
    except RuntimeError:
        error=(a.out/'broken-shader.log').read_text().lower()
        assert 'motionstress_undefined_symbol' in error and ('compile status' in error or 'failed to' in error), error
        rejected['compile_failure_refused']=True
    assert rejected.get('compile_failure_refused'), 'Invalid shader silently accepted'
    try:
        # The supplied source has 12 frames; a scorer expecting 30 must refuse it.
        read(a.ffmpeg,a.source,30)
    except AssertionError:
        rejected['short_stream_refused']=True
    assert rejected.get('short_stream_refused'), 'Short stream silently accepted'
    (a.out/'controls.json').write_text(json.dumps(rejected,indent=2)+'\n')
    print(json.dumps(rejected))


if __name__=='__main__':main()
