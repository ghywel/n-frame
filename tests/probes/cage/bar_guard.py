#!/usr/bin/env python3
"""RUN-ON: mac. COMMAND: python3 tests/probes/cage/bar_guard.py --out "$NP_SCRATCH/bar-guard"
PREDICTION: G011; guided corruption <.2%, C3 gain over High >=3dB. Either miss kills it.
A fixed broader-support guard, no parameter tuning. Generated diagnostic variants only.
COST: short guided-case renders, then three C3 renders through cage.sh.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import bar_gpu as gpu
import bar_pipeline as pipe

HELPER='''float guard_sad(vec2 c, vec2 v) {
    float sad = 0.0;
    for (int y=-3; y<=3; y++) for (int x=-3; x<=3; x++) {
        vec2 q=c+8.0*vec2(float(x),float(y));
        sad += abs(bar_lum_a(q)-bar_lum_b(q+v));
    }
    return sad/49.0;
}
'''
GUARD='''    float old_cost=1.0e30;
    for (int k=-2; k<=2; k++)
        old_cost=min(old_cost,guard_sad(c,vf+0.5*float(k)*n));
    float new_cost=guard_sad(c,vf+s*n);
    if (new_cost >= old_cost - 1.0/255.0) {
        imageStore(FLOW_H_AB_BARS_CACHE, coord, keep);
        return keep;
    }
'''

def guarded(t):
    old=gpu.bar.PASS
    assert t.count(old)==1,'original bars pass not found exactly once'
    assert old.count('vec4 hook() {')==1
    new=old.replace('vec4 hook() {',HELPER+'vec4 hook() {')
    anchor='    vec4 result = vec4((vf + s * n) * 0.5, 0.0, 0.0);'
    assert new.count(anchor)==1
    new=new.replace(anchor,GUARD+anchor)
    return t.replace(old,new)

def score_logs(folder,name):
    log=folder/(name+'-cage.log'); err=folder/(name+'.err')
    text=err.read_text().lower()
    if any(x in text for x in ['compile status','disabling','failed to','error reinit']): raise ValueError('C3 render refused')
    vals=[]; ns=[]
    for line in log.read_text().splitlines():
        m=re.search(r'psnr_y:([0-9.]+|inf)',line); n=re.search(r'n:(\d+)',line)
        if not m or not n: raise ValueError('invalid scoring line')
        k=int(n[1]); ns.append(k)
        if k>5 and k%5!=1: vals.append(float(m[1]))
    if len(ns)!=120 or ns!=list(range(1,121)): raise ValueError(f'C3 count {len(ns)} !=120')
    return {'mean_db':float(np.mean(vals)),'scored':len(vals)}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',required=True,type=Path)
    p.add_argument('--pipeline',required=True,type=Path); a=p.parse_args()
    out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True); base=a.pipeline.resolve()
    ff=str(Path.home()/'np-build/ffmpeg/ffmpeg')
    text=(base/'high1.glsl').read_text(); original=base/'high0.glsl'
    if original.read_text()!=pipe.HIGH.read_text(): raise ValueError('High source changed')
    sh=out/'guard.glsl'; sh.write_text(guarded(text))
    tail=gpu.shader(6,False); tail=tail[tail.rindex('//!HOOK FRAME_MIX'):]
    flow=out/'guard-flow.glsl'; flow.write_text(sh.read_text()+tail)
    v=pipe.render(ff,out,'guided-flow',base/'case3.rgb48',flow)
    repeat=pipe.render(ff,out,'guided-repeat',base/'case3.rgb48',flow)
    if not np.array_equal(v,repeat): raise ValueError('guard repeat differs')
    raw=pipe.read_raw(base/'case3_flow0.rgba64',10); z=np.rint(raw[...,2]*1024).astype(int)
    vx=2*(z//32-16+raw[...,0]); sl=(slice(None),slice(24,-24),slice(48,-48))
    corrupt=float(np.mean((abs(vx[sl]-6)<.5)&(abs(v[sl][...,0]+3)<.5)))
    print('guided corruption',corrupt,flush=True)
    env=os.environ.copy(); env.update(FFMPEG=ff,PY=sys.executable,OUTROOT=str(out/'cage'),SHADERS=f'{original} {base/"high1.glsl"} {sh}',
        MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0',MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
    r=subprocess.run(['bash',str(pipe.REPO/'tests/probes/cage/cage.sh'),'C3_bars_spin_drift'],capture_output=True,text=True,env=env)
    (out/'cage-driver.log').write_text(r.stdout+r.stderr)
    if r.returncode or 'FAILED' in r.stdout: raise ValueError('cage driver failed')
    scores={name:score_logs(out/'cage/C3_bars_spin_drift',name) for name in ['high0','high1','guard']}
    result={'corruption_fraction':corrupt,'repeat_identical':True,'c3':scores,
        'survives':corrupt<.002 and scores['guard']['mean_db']-scores['high0']['mean_db']>=3,
        'guard_sha256':hashlib.sha256(sh.read_bytes()).hexdigest()}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return 0 if result['survives'] else 3
if __name__=='__main__':raise SystemExit(main())
