#!/usr/bin/env python3
"""RUN-ON: mac. COMMAND: python3 tests/probes/cage/guard_followup.py --work "$NP_SCRATCH/bar-guard"
Round 2 of G011/G013: unchanged fixed guard. Kill on C1/C2 loss >.5dB, any ladder loss >1dB,
or capped mean loss >.05dB; repeat C3 and score the previously selected guided damage mask.
A smoke failure stops before the full ladder. No shader parameters are fitted.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import bar_pipeline as pipe
import bar_guard as guard

def values(p):
    text=p.read_text(); rows=[]
    for line in text.splitlines():
        m=re.search(r'psnr_y:([0-9.]+|inf)',line); n=re.search(r'n:(\d+)',line)
        if not m or not n:raise ValueError('invalid stats '+str(p))
        if int(n[1])>5 and int(n[1])%5!=1:rows.append(min(99,float(m[1])))
    if len(text.splitlines())!=120:raise ValueError('expected 120 outputs '+str(p))
    return float(np.mean(rows))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=Path);a=p.parse_args();w=a.work.resolve()
    out=w/'followup';out.mkdir(exist_ok=True)
    ff=str(Path.home()/'np-build/ffmpeg/ffmpeg');base=w.parent/'bar-pipeline'
    env=os.environ.copy();env.update(FFMPEG=ff,PY=sys.executable,OUTROOT=str(out/'cage'),SHADERS=f'{base/"high0.glsl"} {w/"guard.glsl"}',MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0',MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
    r=subprocess.run(['bash',str(pipe.REPO/'tests/probes/cage/cage.sh')],env=env,capture_output=True,text=True)
    (out/'cage.log').write_text(r.stdout+r.stderr)
    if r.returncode or 'FAILED' in r.stdout:raise ValueError('cage failed')
    cages={}
    for c in ['C1_cage_drift','C2_cage_drift_occluded','C3_bars_spin_drift']:
        d=out/'cage'/c
        for err in d.glob('*.err'):
            if any(x in err.read_text().lower() for x in ['compile status','disabling','failed to']):raise ValueError('shader failed')
        cages[c]={kind:{mode:values(d/(mode+suffix+'.log')) for mode in ['high0','guard']}
                  for kind,suffix in [('frame',''),('region','-cage')]}
    repeat={mode:(out/f'cage/C3_bars_spin_drift/{mode}-cage.log').read_bytes()==(w/f'cage/C3_bars_spin_drift/{mode}-cage.log').read_bytes() for mode in ['high0','guard']}
    # Read the exact existing mask; never select it by guard image error.
    v=[]
    for i in [0,1]:
        r=pipe.read_raw(base/f'case3_flow{i}.rgba64',10);z=np.rint(r[...,2]*1024).astype(int);v.append(2*(z//32-16+r[...,0]))
    m=np.roll((abs(v[0]-6)<.5)&(abs(v[1]+3)<.5),3,axis=2)[:,24:-24,48:-48]
    im=pipe.render(ff,out,'guided-guard',base/'case3.rgb48',w/'guard.glsl',48,False)
    u=np.arange(512)[None,:]+.5-6*np.arange(6,26)[:,None]/2
    tr=.5+.08*np.cos(2*np.pi*(u%9)/9)+.3*np.cos(2*np.pi*u/512)
    e=(im-tr[:,None,:])**2
    local=float(e[1::2,24:-24,48:-48][m].mean());whole=float(e[1::2,24:-24,48:-48].mean())
    smoke=all(vals['guard']-vals['high0']>=-.5 for c,row in cages.items() if c!='C3_bars_spin_drift' for vals in row.values())
    result={'cages':cages,'c3_logs_identical':repeat,'fixed_local_mask_mse':local,'guided_crop_mse':whole,'smoke_pass':smoke}
    print(json.dumps(result),flush=True)
    if smoke:
        env['OUTROOT']=str(out/'ladder')
        for name,sh in [('high',base/'high0.glsl'),('guard',w/'guard.glsl')]:
            with (out/f'{name}-ladder.log').open('w') as log:
                r=subprocess.run(['bash',str(pipe.REPO/'tests/bench.sh'),'all',str(sh),name],env=env,stdout=log,stderr=subprocess.STDOUT)
            if r.returncode or 'FAILED' in (out/f'{name}-ladder.log').read_text():raise ValueError('ladder failed')
            print(name,'ladder rendered',flush=True)
        cases=sorted(p for p in (out/'ladder').iterdir() if p.is_dir())
        if len(cases)!=45:raise ValueError('case count !=45')
        rows=[]
        for c in cases:
            # Ladder sources are one second (60 outputs), unlike cage's 120.
            scores={}
            for name in ['high','guard']:
                f=c/f'{name}.log';lines=f.read_text().splitlines()
                if len(lines)!=60:raise ValueError('ladder frame count !=60')
                err=(c/f'{name}.err').read_text().lower()
                if any(s in err for s in ['compile status','disabling','failed to']):raise ValueError('ladder fallback')
                vs=[float(re.search(r'psnr_y:([0-9.]+|inf)',s)[1]) for n,s in enumerate(lines,1) if n>5 and n%5!=1]
                scores[name]=float(np.mean(vs))
            rows.append({'case':c.name,**scores,'delta':scores['guard']-scores['high']})
        result['ladder']=rows;result['ladder_worst']=min(rows,key=lambda r:r['delta'])
        result['ladder_capped_union_delta']=float(np.mean([min(40,r['guard'])-min(40,r['high']) for r in rows]))
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0
if __name__=='__main__':raise SystemExit(main())
