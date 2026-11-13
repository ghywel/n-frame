#!/usr/bin/env python3
"""Six bounded cached real-footage windows, no NAS reads. Not the full content gate.

real.py OUT CONTENT_CACHE --ffmpeg PATH --ffprobe PATH --shaders high=PATH variant=PATH
Uses both pre-existing windows of film1, tv1 and cg1 (chosen before new renders).
Exact timestamps, full-length and retained-frame checks; PSNR plus nonoverlapping
8x8 luma SSIM and high-tail error. Original cached sources remain untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from run import call, psnr


def decode(ff, path, w, h, log):
    raw,_=call([ff,'-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','gray16le','-'],log)
    a=np.frombuffer(raw,'<u2');assert a.size and a.size%(w*h)==0
    return a.reshape(-1,h,w).astype(np.float32)/65535


def ssim8(a,b):
    h,w=a.shape; h-=h%8;w-=w%8
    a=a[:h,:w].reshape(h//8,8,w//8,8);b=b[:h,:w].reshape(h//8,8,w//8,8)
    ma=a.mean((1,3));mb=b.mean((1,3))
    va=np.maximum((a*a).mean((1,3))-ma*ma,0);vb=np.maximum((b*b).mean((1,3))-mb*mb,0)
    cov=(a*b).mean((1,3))-ma*mb
    return float(np.mean((2*ma*mb+.01**2)*(2*cov+.03**2)/((ma*ma+mb*mb+.01**2)*(va+vb+.03**2))))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('cache',type=Path)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True);p.add_argument('--shaders',nargs='+',required=True)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    shaders=dict(v.split('=',1) for v in args.shaders);report={}
    assert len(shaders)==len(args.shaders), 'Duplicate shader label'
    for category in ('film1','tv1','cg1'):
        sources=sorted((args.cache/'real'/category).glob('ref_*.mkv'));assert len(sources)==2
        for ref in sources:
            timecode=ref.stem.removeprefix('ref_');half=ref.parent/f'half_{timecode}.mkv';assert half.exists()
            key=f'{category}-{timecode}';d=args.out/key;d.mkdir(exist_ok=True)
            probe=subprocess.run([args.ffprobe,'-v','error','-select_streams','v:0','-show_entries',
                'stream=width,height,r_frame_rate','-of','json',str(ref)],check=True,capture_output=True,text=True)
            m=json.loads(probe.stdout)['streams'][0];w,h,rate=m['width'],m['height'],m['r_frame_rate']
            truth=decode(args.ffmpeg,ref,w,h,d/'ref.decode.log'); n=len(truth);rows={}
            half_probe=subprocess.run([args.ffprobe,'-v','error','-select_streams','v:0','-count_frames',
                '-show_entries','stream=nb_read_frames','-of','json',str(half)],check=True,capture_output=True,text=True)
            input_frames=int(json.loads(half_probe.stdout)['streams'][0]['nb_read_frames'])
            assert input_frames==(n+1)//2, (half, input_frames, n)
            for name,shader in shaders.items():
                assert name.replace('-','').replace('_','').isalnum()
                dst=d/f'{name}.mkv'
                call([args.ffmpeg,'-nostdin','-y','-v','warning','-init_hw_device','vulkan=vk','-filter_hw_device','vk',
                    '-i',str(half),'-vf',f'settb=expr=1/120000,setpts=N*2/({rate})/TB,libplacebo=fps={rate}:frame_mixer=custom_n:custom_shader_path={Path(shader).resolve()}:dithering=none',
                    '-c:v','ffv1','-pix_fmt','yuv444p16le',str(dst)],d/f'{name}.log',gpu=True)
                out=decode(args.ffmpeg,dst,w,h,d/f'{name}.decode.log')
                assert len(out)==2*((n+1)//2),(key,len(out),n)
                keep=list(range(5,n-4,2));assert len(keep)>10
                alignment=max(float(np.sqrt(np.mean((out[k]-truth[k])**2))*255) for k in range(4,n-4,2))
                assert alignment<2.55,(key,name,alignment)
                mse=[];ssim=[];tail=[]
                for k in keep:
                    e=(out[k]-truth[k])**2;mse.append(float(e.mean()));ssim.append(ssim8(out[k],truth[k]))
                    a=e.ravel();j=max(1,len(a)//100);tail.append(float(np.partition(a,len(a)-j)[-j:].mean()))
                score=dict(psnr=psnr(np.mean(mse)),ssim8=float(np.mean(ssim)),worst1pct_rms_dn=float(np.sqrt(np.mean(tail))*255),
                    alignment_rms_dn=alignment,frames=len(keep),source_frames=input_frames,reference_frames=n,output_frames=len(out),
                    shader_sha256=hashlib.sha256(Path(shader).read_bytes()).hexdigest())
                rows[name]=score;print(key,name,json.dumps(score),flush=True)
            report[key]=rows;(args.out/'scores.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
