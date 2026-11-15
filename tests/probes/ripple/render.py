#!/usr/bin/env python3
"""Serial exact doubling of native 24000/1001 or withheld-input 12000/1001 footage.

render.py OUT SOURCE --ffmpeg PATH --ffprobe PATH --shaders label=path [...]
Exact input PTS; reject failed/fallback renders and unexpected output count.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from fractions import Fraction

ENV=dict(os.environ,MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0',
         MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')


def call(cmd,log,gpu=False):
    start=time.monotonic();r=subprocess.run(cmd,capture_output=True,env=ENV)
    log.write_bytes(r.stderr);error=r.stderr.decode(errors='replace').lower()
    if r.returncode or (gpu and (error.count('hook skipped')>2 or any(s in error for s in ('compile status','disabling','failed to')))):
        raise RuntimeError(f'{log}: {r.returncode}: {error[-1500:]}')
    return r.stdout,time.monotonic()-start


def probe(ffprobe,path):
    r=subprocess.run([ffprobe,'-v','error','-select_streams','v:0','-count_frames','-show_entries',
                      'stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(path)],check=True,capture_output=True)
    return json.loads(r.stdout)['streams'][0]


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def incomplete(path, **context):
    """Invalidate earlier evidence before a rerun can fail or overwrite its media."""
    path.write_text(json.dumps(dict(execution_status='incomplete',**context),indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('source',type=Path)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True);p.add_argument('--shaders',nargs='+',required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    specs=[];seen=set()
    for spec in a.shaders:
        label,path=spec.split('=',1)
        if label in seen or not label.replace('-','').isalnum():
            p.error('shader labels must be unique alphanumeric/hyphen names')
        seen.add(label)
        target=a.out/f'{label}.mkv'
        if target.resolve()==a.source.resolve():
            p.error('output must not overwrite the input source')
        specs.append((label,path,target))
    for label,path,target in specs:
        incomplete(a.out/f'{label}.json',source=str(a.source),shader=path)
    m=probe(a.ffprobe,a.source)
    rate=Fraction(m['r_frame_rate']);assert rate in (Fraction(24000,1001),Fraction(12000,1001)),m
    target_rate=str(2*rate)
    n=int(m['nb_read_frames']);source_sha=sha256(a.source)
    for label,path,target in specs:
        shader_sha=None if path=='linear' else sha256(path)
        mode='linear' if path=='linear' else f'custom_n:custom_shader_path={Path(path).resolve()}'
        pending=target.with_name(target.stem+'.partial.mkv')
        _,seconds=call([a.ffmpeg,'-nostdin','-y','-v','warning','-init_hw_device','vulkan=vk','-filter_hw_device','vk',
             '-i',str(a.source),'-vf',f'settb=expr=1/{2*rate.numerator},setpts=N*{2*rate.denominator},libplacebo=fps={target_rate}:frame_mixer={mode}:dithering=none',
             '-an','-c:v','ffv1','-level','3','-pix_fmt','yuv420p',str(pending)],a.out/f'{label}.log',True)
        output=probe(a.ffprobe,pending);assert int(output['nb_read_frames'])==n*2,(label,n,output)
        assert (output['width'],output['height'])==(m['width'],m['height']),output
        assert abs(float(Fraction(output['r_frame_rate'])/(2*rate))-1)<1e-5,output
        assert sha256(a.source)==source_sha,'source changed during render'
        assert path=='linear' or sha256(path)==shader_sha,'shader changed during render'
        pending.replace(target)
        record=dict(execution_status='complete',source=str(a.source),source_sha256=source_sha,output_sha256=sha256(target),
                    source_frames=n,output_frames=n*2,width=m['width'],height=m['height'],input_rate=str(rate),rate=target_rate,
                    shader_sha256=shader_sha,wall_seconds=seconds)
        (a.out/f'{label}.json').write_text(json.dumps(record,indent=2)+'\n')
        print(label,record,flush=True)


if __name__=='__main__':main()
