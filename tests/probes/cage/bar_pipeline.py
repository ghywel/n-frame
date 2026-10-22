#!/usr/bin/env python3
"""RUN-ON: mac. COMMAND: python3 tests/probes/cage/bar_pipeline.py --out "$NP_SCRATCH/bar-pipeline"
PREDICTION/REFUTED-BY: CHAT-LEDGER G009; >1% matched +6-to--3 corruption in one guided case.
COST: four cases, High and bars, short 512x128 GPU renders. Exact scene truth, no clipping.
No parameter fitting. Inputs, variants, logs, raw results and summary stay outside git.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import bar_gpu as gpu

REPO = Path(__file__).resolve().parents[3]
HIGH = REPO/'shaders/bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut.glsl'
W,H,N = 512,128,16
CASES = [(0.15,0.,256),(0.15,0.25,256),(0.15,0.25,512),(0.08,0.30,512)]

def source(path, a,b,p, rate=24):
    with path.open('wb') as f:
        for n in range(round(N*rate/24)):
            u=np.arange(W)+.5-6*n*24/rate
            line=.5+a*np.cos(2*np.pi*(u%9)/9)+b*np.cos(2*np.pi*u/p)
            assert line.min()>=0 and line.max()<=1
            rgb=np.broadcast_to(np.rint(line*65535).astype('<u2')[None,:,None],(H,W,3))
            f.write(rgb.tobytes())

def read_raw(dst, count):
    if dst.stat().st_size!=count*H*W*8: raise ValueError('short output '+dst.name)
    return np.fromfile(dst,'<u2').reshape(count,H,W,4).astype(float)/65535

def render(ff, out, name, src, sh, rate=24, field=True):
    dst=out/(name+'.rgba64')
    env=os.environ.copy()
    env.update(MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0',MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
    cmd=[ff,'-nostdin','-y','-hide_banner','-loglevel','warning','-init_hw_device','vulkan=vk','-filter_hw_device','vk',
         '-f','rawvideo','-pixel_format','rgb48le','-video_size',f'{W}x{H}','-framerate','24','-i',str(src),'-vf',
         f"libplacebo=fps={rate}:frame_mixer=custom_n:custom_shader_path={sh}:dithering=none,format=rgba64le,select='between(n,{3*rate//24},{13*rate//24-1})'",
         '-fps_mode','passthrough','-f','rawvideo',str(dst)]
    r=subprocess.run(cmd,capture_output=True,text=True,env=env)
    (out/(name+'.log')).write_text(r.stderr)
    if r.returncode or any(s in r.stderr.lower() for s in ['compile status','disabling','failed to','error reinit']):
        raise ValueError('render refused: '+name)
    count=10*rate//24
    raw=read_raw(dst,count)
    if not field: return raw[...,:3].mean(axis=-1)
    packed=raw[...,2]*1024
    if np.max(abs(packed-np.rint(packed)))>.05: raise ValueError('split readback invalid')
    z=np.rint(packed).astype(int)
    return np.stack([2*(z//32-16+raw[...,0]),2*(z%32-16+raw[...,1])],-1)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ffmpeg',default=str(Path.home()/'np-build/ffmpeg/ffmpeg'))
    args=p.parse_args(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    # Additional controls added after the first four-case run; no gate or cases changed.
    gpu.W=W; gpu.H=H
    calibration=gpu.render(args.ffmpeg,out,'calibration',6,False)
    if abs(calibration['median_xy'][0]-6)>.01 or calibration['background_max_abs']>.01:
        raise ValueError('constant/zero readback failed')
    short=out/'short.rgba64'; short.write_bytes((out/'calibration.rgba64').read_bytes()[:-8])
    try: read_raw(short,10)
    except ValueError: pass
    else: raise ValueError('short file accepted')
    env=os.environ.copy()
    # Freeze generator settings rather than inherit any switches from the caller.
    for key in ['PHASE_FETCH','PHASE_FETCH_E','PHASE_GATE','BAR_KEEP','STICKY_CACHE','EDGE_PROP','LOCAL_CENTRE','TRUST_GATE']:
        env[key]='0'
    env.update({k:'1' for k in ['GLOBAL_SEED','QZERO_MOIRE','COHERENCE_GATE','COARSE_ENERGY','ALIAS_PRIOR','ALIAS_CARRY','OUTLINE_ADOPT','PRINT_LATTICE','CUT_MOTION','ZERO_SEED']})
    env.update(COARSE_ENERGY_WS='8',COARSE_ENERGY_WE='1',PRUNE='2',PYTHONDONTWRITEBYTECODE='1')
    texts=[]
    for enable in [0,1]:
        env['BAR_REDECIDE']=str(enable); sh=out/f'high{enable}.glsl'
        cmd=[sys.executable,str(REPO/'tests/gen_variational.py'),'0,0,8,4','0.3','0.08',str(sh),'0','0,0,2,0','bidirectional-interpolation-propagated.glsl']
        r=subprocess.run(cmd,env=env,cwd=REPO,capture_output=True,text=True)
        (out/f'generate{enable}.log').write_text(r.stdout+r.stderr)
        if r.returncode: raise ValueError('generation failed')
        texts.append(sh.read_text())
    if texts[0]!=HIGH.read_text(): raise ValueError('unchanged High does not reproduce')
    tail=gpu.shader(6,False); tail=tail[tail.rindex('//!HOOK FRAME_MIX'):]
    for i,t in enumerate(texts): (out/f'flow{i}.glsl').write_text(t+'\n'+tail)
    rows=[]
    for ci,(a,b,pitch) in enumerate(CASES):
        src=out/f'case{ci}.rgb48'; source(src,a,b,pitch)
        vs=[render(args.ffmpeg,out,f'case{ci}_flow{i}',src,out/f'flow{i}.glsl') for i in [0,1]]
        x0,x1=[v[:,24:-24,48:-48,0] for v in vs]
        correct=abs(x0-6)<.5; destroyed=correct&(abs(x1+3)<.5)
        row={'case':ci,'fine':a,'broad':b,'period':pitch,'baseline_correct':float(correct.mean()),
             'correct_to_alias':float(destroyed.mean()),'median_x':[float(np.median(x)) for x in [x0,x1]]}
        if destroyed.mean()>.01:
            repeat=render(args.ffmpeg,out,f'case{ci}_repeat',src,out/'flow1.glsl')
            row['repeat_identical']=bool(np.array_equal(repeat,vs[1]))
            if not row['repeat_identical']: raise ValueError('witness does not repeat')
            repeat0=render(args.ffmpeg,out,f'case{ci}_repeat_high',src,out/'flow0.glsl')
            row['baseline_repeat_identical']=bool(np.array_equal(repeat0,vs[0]))
            if not row['baseline_repeat_identical']: raise ValueError('baseline witness does not repeat')
            # True 48fps frames at the selected 24->48 instants, including passthrough.
            u=np.arange(W)[None,:]+.5-6*np.arange(6,26)[:,None]/2
            truth=.5+a*np.cos(2*np.pi*(u%9)/9)+b*np.cos(2*np.pi*u/pitch)
            errs=[]; images=[]; passthrough=[]
            for i in [0,1]:
                image=render(args.ffmpeg,out,f'case{ci}_picture{i}',src,out/f'high{i}.glsl',48,False)
                images.append(image)
                e=(image[:,24:-24,48:-48]-truth[:,None,48:-48])**2
                errs.append(float(e[1::2].mean()))
                passthrough.append(float(np.max(np.sqrt(e[::2]))))
            if max(passthrough)>.001: raise ValueError('picture alignment/readback refused')
            row['synthesized_mse']=errs
            row['synthesized_psnr']=[float(-10*np.log10(e)) for e in errs]
            row['passthrough_max_abs_error']=passthrough
            # Exploratory after the first run: masks selected on field differences, NOT image errors.
            fullmask=(abs(vs[0][...,0]-6)<.5)&(abs(vs[1][...,0]+3)<.5)
            local=[]
            for shift in [0,3,-3]:
                m=np.roll(fullmask,shift,axis=2)[:,24:-24,48:-48]
                es=[((im-truth[:,None,:])**2)[1::2,24:-24,48:-48][m].mean() for im in images]
                local.append({'mask_shift_x':shift,'samples':int(m.sum()),'mse':[float(e) for e in es],
                              'bars_psnr_delta':float(10*np.log10(es[0]/es[1]))})
            row['exploratory_flow_selected_picture_masks']=local
        rows.append(row); print(json.dumps(row),flush=True)
    result={'cases':rows,'prediction_held':any(r['broad'] and r['correct_to_alias']>.01 for r in rows),
            'unchanged_high_identical':True,'high_sha256':hashlib.sha256(HIGH.read_bytes()).hexdigest(),
            'calibration':calibration,'short_output_refused':True,
            'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.rgba64')},
            'scope':'512x128 full High pipeline; global rigid translation +6 px/frame'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['prediction_held'] else 3
if __name__=='__main__': raise SystemExit(main())
