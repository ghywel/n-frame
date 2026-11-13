#!/usr/bin/env python3
"""Interleaved warmed FFmpeg pipeline timing from a saved file; not a native Metal timing.

timing.py OUT SOURCE --ffmpeg PATH --shaders high=PATH combined=PATH
One warm-up per shader, then three alternating-order rounds; decode+init+GPU+null sink.
"""
import argparse
import json
from pathlib import Path
import re
import statistics
from run import call


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('out',type=Path);ap.add_argument('source',type=Path)
    ap.add_argument('--ffmpeg',required=True);ap.add_argument('--shaders',nargs='+',required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);shaders=dict(s.split('=',1) for s in a.shaders)
    assert len(shaders)==len(a.shaders), 'Duplicate shader label'
    assert all(k.replace('-','').replace('_','').isalnum() for k in shaders), 'Unsafe label'
    rows={k:[] for k in shaders};counts=set()
    for repeat in range(4):
        order=list(shaders) if repeat%2==0 else list(reversed(shaders))
        for name in order:
            output,seconds=call([a.ffmpeg,'-nostdin','-v','warning','-init_hw_device','vulkan=vk','-filter_hw_device','vk',
                 '-i',str(a.source),'-vf',f'libplacebo=fps=60:frame_mixer=custom_n:custom_shader_path={Path(shaders[name]).resolve()}:dithering=none',
                 '-an','-progress','pipe:1','-f','null','-'],a.out/f'{repeat}-{name}.log',gpu=True)
            frames=[int(v) for v in re.findall(rb'^frame=(\d+)',output,re.M)]
            assert frames and frames[-1]>100;counts.add(frames[-1])
            if repeat:rows[name].append(seconds)
            print(repeat,name,frames[-1],round(seconds,4),flush=True)
    assert len(counts)==1,counts
    result={k:dict(seconds=v,median_seconds=statistics.median(v),
                   median_ms_per_output=statistics.median(v)/next(iter(counts))*1000) for k,v in rows.items()}
    result['scope']='Warm interleaved FFmpeg process+decode+GPU+null-sink time, not isolated GPU or Cadence Metal'
    (a.out/'timing.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
