#!/usr/bin/env python3
"""Focused audit counterfactuals from one existing bar capture; no render/GPU.

Writes isolated JSON copies and read-only media/log symlinks under a fresh OUT.
Every corruption is preserved with its expected rejection, rather than repaired
in place. These constructed records are controls, not new execution evidence.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
from audit_replays import audit
from gate import require, save, sha


def load(path):
    return json.loads(Path(path).read_text())


def fixture(destination, matrix_path, replays_path, fixtures_path, case):
    matrix=load(matrix_path);replays=load(replays_path)
    selected=[r for r in matrix['rows'] if r['case']==case and r['mb_size']==16]
    require(len(selected)==1 and len(selected[0]['capsules'])==1, 'control needs one block16 capture/draw')
    row=copy.deepcopy(selected[0]);cap=row['capsules'][0]
    outputs=[r for r in replays['rows'] if (r['case'],r['mb_size'],r['draw_index'])==(case,16,cap['draw_index'])]
    require(len(outputs)==1, 'control requires corresponding complete GPU output')
    destination.mkdir(parents=True,exist_ok=False)
    captures=destination/'captures';captured=captures/f'{case}-mb16';captured.mkdir(parents=True)
    replay_dir=destination/'replays';replay_dir.mkdir()
    original=matrix_path.parent/f'{case}-mb16'
    shutil.copyfile(original/'capture.json',captured/'capture.json')
    for name in (cap['file'],'output.framemd5','capture.log'):
        (captured/name).symlink_to((original/name).resolve())
    name=f"{case}-mb16-draw{cap['draw_index']}"
    shutil.copyfile(replays_path.parent/(name+'.json'),replay_dir/(name+'.json'))
    (replay_dir/(name+'.log')).symlink_to((replays_path.parent/(name+'.log')).resolve())
    fixtures=destination/'fixtures.json';shutil.copyfile(fixtures_path,fixtures)
    matrix['rows']=[row]
    matrix.pop('script_sha256',None)  # This derived single-row matrix was not executed.
    matrix['constructed_audit_control']=True
    matrix_out=captures/'capture-matrix.json';save(matrix_out,matrix)
    replays['rows']=[copy.deepcopy(outputs[0])];replays['hashes']['matrix']=sha(matrix_out)
    replays['constructed_audit_control']=True
    replays_out=replay_dir/'replays.json';save(replays_out,replays)
    return dict(matrix=matrix_out,replays=replays_out,fixtures=fixtures,
                manifest=captured/'capture.json',raw=replay_dir/(name+'.json'))


def bind_matrix(paths, matrix):
    save(paths['matrix'],matrix)
    result=load(paths['replays']);result['hashes']['matrix']=sha(paths['matrix']);save(paths['replays'],result)


def bind_raw(paths, response):
    save(paths['raw'],response)
    result=load(paths['replays']);row=result['rows'][0]
    row['result_sha256']=sha(paths['raw'])
    clean=copy.deepcopy(response);clean.pop('capsule',None);clean.pop('shader',None)
    row['response']=clean;save(paths['replays'],result)


def corrupt(name, paths):
    matrix=load(paths['matrix']);result=load(paths['replays'])
    if name=='empty_matrix_rows':
        matrix['rows']=[];bind_matrix(paths,matrix)
    elif name=='empty_replay_rows':
        result['rows']=[];save(paths['replays'],result)
    elif name=='empty_capsules':
        matrix['rows'][0]['capsules']=[];bind_matrix(paths,matrix)
    elif name=='duplicate_case':
        matrix['rows'].append(copy.deepcopy(matrix['rows'][0]));bind_matrix(paths,matrix)
    elif name in ('substituted_capsule_metadata','substituted_source_hash'):
        manifest=load(paths['manifest'])
        if name=='substituted_capsule_metadata':
            # Keep both JSON copies consistent and rehash them. Actual capsule
            # bytes, not just a stale metadata hash, must defeat this substitution.
            manifest['capsules'][0]['alpha']=1+manifest['capsules'][0]['alpha']%1023
            matrix['rows'][0]['capsules']=copy.deepcopy(manifest['capsules'])
        else:manifest['hashes']['source']='0'*64
        save(paths['manifest'],manifest)
        matrix['rows'][0]['capture_manifest_sha256']=sha(paths['manifest'])
        bind_matrix(paths,matrix)
    elif name=='changed_raw_gpu_result':
        response=load(paths['raw']);response['alpha']+=1;save(paths['raw'],response)
    else:
        response=load(paths['raw'])
        if name=='truncated_iterations':response['iterations'].pop()
        elif name=='wrong_warmup':response['iterations'][0]['warmup']=False
        elif name=='wrong_readback_mode':
            response['readback_mode']='direct'
            result['readback_mode']='staging';save(paths['replays'],result)
        else:raise ValueError('unknown control '+name)
        # Rehash/self-consistently rewrite the summary: the semantic audit,
        # rather than only a raw SHA mismatch, must reject these three faults.
        bind_raw(paths,response)


FAULTS={
    'empty_matrix_rows':'incomplete/empty capture matrix',
    'empty_replay_rows':'incomplete/empty replay evidence',
    'empty_capsules':'uncertified stream or empty capsule selection',
    'duplicate_case':'duplicate matrix case/block',
    'substituted_capsule_metadata':'recorded capsule metadata differs from actual bytes',
    'substituted_source_hash':'capture source is not the declared CPU fixture/pinned scalar source',
    'changed_raw_gpu_result':'raw GPU result/log changed',
    'truncated_iterations':'truncated replay iteration records',
    'wrong_warmup':'wrong warmup/measurement flags',
    'wrong_readback_mode':'GPU result does not explicitly match requested readback mode',
}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    p.add_argument('--matrix',type=Path,required=True);p.add_argument('--replays',type=Path,required=True)
    p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--case',default='bars_v9')
    a=p.parse_args();out=a.out.resolve()
    require(not out.exists() or not any(out.iterdir()), 'controls require a fresh empty output directory')
    out.mkdir(parents=True,exist_ok=True);summary=out/'audit-controls.json'
    save(summary,dict(execution_status='incomplete'))
    originals={key:sha(getattr(a,key)) for key in ('matrix','replays','fixtures')}
    paths=fixture(out/'positive',a.matrix,a.replays,a.fixtures,a.case)
    positive=audit(paths['matrix'],paths['fixtures'],paths['replays'])
    save(out/'positive-audit.json',positive);rows=[]
    for name,expected in FAULTS.items():
        paths=fixture(out/name,a.matrix,a.replays,a.fixtures,a.case);corrupt(name,paths)
        try:audit(paths['matrix'],paths['fixtures'],paths['replays'])
        except ValueError as error:
            require(str(error)==expected, f'{name}: failed for an unexpected reason: {error}')
            rejection=dict(name=name,refused=True,reason=str(error),matrix_sha256=sha(paths['matrix']),
                           replay_summary_sha256=sha(paths['replays']))
            save(out/name/'rejection.json',rejection);rows.append(rejection);print('rejected',name,flush=True)
        else:raise ValueError('audit silently accepted '+name)
    require(originals=={key:sha(getattr(a,key)) for key in originals}, 'original evidence changed during controls')
    save(summary,dict(schema=1,execution_status='complete',scope='Constructed evidence-audit controls; no new GPU execution',
        case=a.case,input_summary_sha256=originals,positive_audit_sha256=sha(out/'positive-audit.json'),
        control_script_sha256=sha(__file__),auditor_script_sha256=sha(Path(__file__).with_name('audit_replays.py')),rows=rows))
    print(summary)


if __name__=='__main__':main()
