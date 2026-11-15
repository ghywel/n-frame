#!/usr/bin/env python3
"""Serial hardware GPU replay of a completed capture matrix, with bound evidence.

Portable runner: on another host, copy captures preserving paths below the matrix
directory; absolute capture_manifest paths are reconstructed locally by case/block.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from capture import validate_capsule
from gate import require, save, sha
from audit_replays import validate_matrix, validate_response


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('matrix',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--runner',type=Path,required=True);p.add_argument('--shader',type=Path,required=True)
    p.add_argument('--fixtures',type=Path,required=True)
    p.add_argument('--readback',choices=('direct','staging'),default='direct')
    p.add_argument('--device');p.add_argument('--cases',default='all');p.add_argument('--repeats',type=int,default=3)
    a=p.parse_args();require(a.repeats>=3,'at least three measured repetitions required')
    a.out.mkdir(parents=True,exist_ok=True);status=a.out/'replays.json'
    save(status,dict(execution_status='incomplete'))
    executed_script_sha=sha(__file__)
    auditor_sha=sha(Path(__file__).with_name('audit_replays.py'))
    matrix,bindings=validate_matrix(a.matrix,a.fixtures,a.cases)
    bound={(b['case'],b['mb_size'],b['draw_index']):b for b in bindings}
    selected=matrix['rows'] if a.cases=='all' else [r for r in matrix['rows'] if r['case'] in a.cases.split(',')]
    require(selected and (a.cases=='all' or set(a.cases.split(','))=={r['case'] for r in selected}), 'unknown/empty cases')
    hashes=dict(runner=sha(a.runner),shader=sha(a.shader),matrix=sha(a.matrix),fixtures=sha(a.fixtures));rows=[]
    env=dict(os.environ)
    if os.uname().sysname=='Darwin':
        env.update(MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0',MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
    for row in selected:
        folder=a.matrix.parent/f"{row['case']}-mb{row['mb_size']}"
        manifest=folder/'capture.json'
        require(sha(manifest)==row['capture_manifest_sha256'],'capture manifest changed')
        for cap in row['capsules']:
            path=folder/cap['file'];actual=bound[(row['case'],row['mb_size'],cap['draw_index'])]['actual']
            require(actual['capsule_sha256']==cap['capsule_sha256'],'capsule changed')
            name=f"{row['case']}-mb{row['mb_size']}-draw{cap['draw_index']}"
            cmd=[str(a.runner.resolve()),'--shader',str(a.shader.resolve()),'--repeats',str(a.repeats),
                 '--readback',a.readback]
            if a.device:cmd+=['--device',a.device]
            cmd.append(str(path.resolve()))
            with (a.out/(name+'.json')).open('wb') as out,(a.out/(name+'.log')).open('wb') as log:
                result=subprocess.run(cmd,stdout=out,stderr=log,env=env)
            require(result.returncode==0,f'{name}: GPU replay failed; preserve logs')
            response=json.loads((a.out/(name+'.json')).read_text())
            validate_response(response,actual,a.repeats,a.readback)
            require(not a.device or response['device']==a.device, 'selected device differs from request')
            require(hashes==dict(runner=sha(a.runner),shader=sha(a.shader),matrix=sha(a.matrix),fixtures=sha(a.fixtures)) and
                    sha(path)==cap['capsule_sha256'],'replay inputs changed')
            response.pop('capsule',None);response.pop('shader',None)
            rows.append(dict(case=row['case'],mb_size=row['mb_size'],draw_index=cap['draw_index'],
                             capsule_sha256=cap['capsule_sha256'],result_sha256=sha(a.out/(name+'.json')),
                             log_sha256=sha(a.out/(name+'.log')),response=response))
            print('GPU exact',name,response['device'],flush=True)
    require(sha(__file__)==executed_script_sha and sha(Path(__file__).with_name('audit_replays.py'))==auditor_sha,
            'wrapper/auditor source changed during replay')
    save(status,dict(execution_status='complete',hashes=hashes,rows=rows,selection=a.cases,readback_mode=a.readback,
                     environment={k:env[k] for k in ['MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS',
                        'MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE'] if k in env},
                     script_sha256=executed_script_sha,auditor_script_sha256=auditor_sha))


if __name__=='__main__':main()
