#!/usr/bin/env python3
"""Dump selected full-resolution diagnostic outputs, converting to RGB48 inside the graph.

dump.py OUT SOURCE --ffmpeg PATH --ffprobe PATH --shader FILE --frames 97 121 ...
Optional --crop x y w h (after interpolation, never changes estimator input).
Field variants encode full-pixel displacement as 0.5+flow/256; decode explicitly after calibration.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
from render import call,probe,sha256,incomplete


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('source',type=Path)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True);p.add_argument('--shader',type=Path,required=True)
    p.add_argument('--frames',type=int,nargs='+',required=True);p.add_argument('--crop',type=int,nargs=4)
    a=p.parse_args()
    if a.out.suffix not in ('','.npy'):
        p.error('output must have .npy or no suffix')
    a.out=a.out.with_suffix('.npy');a.out.parent.mkdir(parents=True,exist_ok=True)
    incomplete(a.out.with_suffix('.json'),source=str(a.source),shader=str(a.shader),frames=a.frames,crop=a.crop)
    m=probe(a.ffprobe,a.source)
    assert len(set(a.frames))==len(a.frames) and a.frames==sorted(a.frames)
    assert min(a.frames)>=0 and max(a.frames)<2*int(m['nb_read_frames'])
    rate=Fraction(m['r_frame_rate'])
    assert rate in (Fraction(24000,1001),Fraction(12000,1001),Fraction(24),Fraction(12)),m
    source_sha,shader_sha=sha256(a.source),sha256(a.shader)
    w,h=m['width'],m['height'];filters=[
        f'settb=expr=1/{2*rate.numerator}',f'setpts=N*{2*rate.denominator}',
        f'libplacebo=fps={2*rate}:frame_mixer=custom_n:custom_shader_path={a.shader.resolve()}:dithering=none',
        'format=rgb48le','select='+ '+'.join(f'eq(n\\,{n})' for n in a.frames)]
    if a.crop:
        x,y,cw,ch=a.crop;assert x>=0 and y>=0 and cw>0 and ch>0 and x+cw<=w and y+ch<=h
        filters.append(f'crop={cw}:{ch}:{x}:{y}');w,h=cw,ch
    raw,seconds=call([a.ffmpeg,'-nostdin','-v','warning','-init_hw_device','vulkan=vk','-filter_hw_device','vk',
        '-i',str(a.source),'-vf',','.join(filters),'-an','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb48le','-'],
        a.out.with_suffix('.log'),True)
    values=np.frombuffer(raw,'<u2');assert values.size==len(a.frames)*w*h*3,(values.size,len(a.frames),w,h)
    assert sha256(a.source)==source_sha and sha256(a.shader)==shader_sha,'source or shader changed during dump'
    pending=a.out.with_name(a.out.name+'.partial')
    with pending.open('wb') as stream:
        np.save(stream,values.reshape(len(a.frames),h,w,3).astype(np.float32)/65535)
    pending.replace(a.out)
    a.out.with_suffix('.json').write_text(json.dumps(dict(execution_status='complete',source=str(a.source),source_sha256=source_sha,
        shader_sha256=shader_sha,array_sha256=sha256(a.out),input_rate=str(rate),rate=str(2*rate),
        source_frames=int(m['nb_read_frames']),frames=a.frames,crop=a.crop,width=w,height=h,wall_seconds=seconds),indent=2)+'\n')
    print(a.out,len(a.frames),w,h,flush=True)


if __name__=='__main__':main()
