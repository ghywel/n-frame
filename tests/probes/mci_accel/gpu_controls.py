#!/usr/bin/env python3
"""Fail-closed capsule and actual-GPU counterfactuals, never a benchmark.

Default --stage python runs only the Python validator. --stage host additionally
runs replay --validate-only. --stage gpu explicitly enables real GPU dispatches.
All generated fault capsules, shaders, commands and logs stay in OUT.
"""
import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from gate import canonical, require, save, sha


HEADER_WORDS=64
STORE='dst[pc.plane_offset + out_index] = result;'
STATUSES={'validated':0,'success':0,'validation_error':2,'setup_error':3,
          'gpu_mismatch':4,'gpu_output_invalid':5}


def word(data, index, value):
    result=bytearray(data);struct.pack_into('<I',result,4*index,value & 0xffffffff)
    return bytes(result)


def timing(data, ap, bp, op, alpha, input_den=1024, output_num=1):
    """Consistent rational phase, permitting deliberately overflowing stock math."""
    for index,value in ((18,ap),(20,bp),(22,op)):
        data=word(word(data,index,value),index+1,value>>32)
    for index,value in ((8,alpha),(24,1),(25,input_den),(26,output_num),(27,1024)):
        data=word(data,index,value)
    return data


def mutations(data):
    require(len(data)>=4*HEADER_WORDS, 'positive capsule has no complete header')
    h=struct.unpack_from('<64I',data)
    a,golden,vectors,table=(HEADER_WORDS+h[i] for i in (28,30,31,32))
    table_word=struct.unpack_from('<I',data,4*table)[0]
    golden_word=struct.unpack_from('<I',data,4*golden)[0]
    bad=dict(truncated=data[:-1],trailing=data+b'\0\0\0\0',
             wrong_magic=word(data,0,h[0]^1),wrong_version=word(data,1,2),
             wrong_table=word(data,table,table_word^1),out_of_bound_mv=word(data,vectors,33),
             nonzero_reserved=word(data,44,1),wrong_offset=word(data,28,1),
             wrong_count=word(data,38,h[38]+1),sample_above_byte=word(data,a,256),
             endpoint_alpha=word(data,8,0),equal_source_pts=word(word(data,20,h[18]),21,h[19]),
             wrong_search=word(data,7,33),global_anchor_mv=word(data,vectors,-1),
             wrong_interior_alpha=word(data,8,1+h[8]%1023))
    # These phases agree in unbounded arithmetic: refusal must come from the
    # original signed-int64 operation bounds, not an incidental phase mismatch.
    bad.update(overflow_rescale_factor=timing(data,-257,767,0,257,(1<<31)-1,(1<<31)-1),
               overflow_rescaled_pts=timing(data,(1<<53)-1,(1<<53)+1,1<<53,512),
               overflow_source_scale=timing(data,(1<<53)+1,(1<<53)+3,(1<<53)+2,512),
               overflow_source_delta=timing(data,-1,(1<<63)-1,(1<<53)-1,1),
               overflow_phase_numerator=timing(data,-(1<<53),(1<<62)-(1<<53),0,2))
    # This fault is intentionally structurally valid. Only the rendering comparison
    # can reject it; host-side rejection would not establish GPU fault detection.
    changed_golden=word(data,golden,golden_word^1)
    return bad,changed_golden,h


def python_reject(validator,path):
    try:
        validator(path)
    except ValueError:
        return
    raise ValueError('Python capsule validator silently accepted '+path.name)


def invoke(out,name,runner,capsule,expected,shader=None,samples=None,readback='direct'):
    command=[str(runner),'--readback',readback]
    command += ['--validate-only',str(capsule)] if shader is None else [
        '--shader',str(shader),'--repeats','1',str(capsule)]
    source_hash=sha(capsule);binary_hash=sha(runner);shader_hash=sha(shader) if shader else None
    metadata=dict(command=command,command_sha256=hashlib.sha256(canonical(command)).hexdigest(),
                  capsule_sha256=source_hash,runner_sha256=binary_hash,shader_sha256=shader_hash,
                  expected_status=expected,readback_mode=readback)
    record=out/(name+'.json');save(record,dict(execution_status='incomplete',**metadata))
    proc=subprocess.run(command,capture_output=True)
    stdout=out/(name+'.stdout');stderr=out/(name+'.stderr')
    stdout.write_bytes(proc.stdout);stderr.write_bytes(proc.stderr)
    try:
        response=json.loads(proc.stdout)
    except (ValueError,UnicodeDecodeError) as error:
        raise ValueError(f'{name}: runner did not return its structured status') from error
    require(isinstance(response,dict) and response.get('status')==expected,
            f'{name}: expected {expected}, received {response!r}')
    require(proc.returncode==STATUSES[expected], f'{name}: status/exit code disagree')
    require(response.get('readback_mode')==readback, f'{name}: requested readback mode was not confirmed')
    if expected in ('success','gpu_mismatch','gpu_output_invalid'):
        require(type(response.get('dispatches')) is int and response['dispatches']>0,
                f'{name}: no actual GPU dispatch certified')
        require(response.get('validated_samples')==samples, f'{name}: full GPU output was not inspected')
        require(response.get('software') is False and bool(response.get('device')),
                f'{name}: hardware device provenance missing')
    else:
        require(response.get('dispatches',0)==0, f'{name}: validation unexpectedly dispatched GPU work')
    require(sha(capsule)==source_hash and sha(runner)==binary_hash and
            (shader is None or sha(shader)==shader_hash), f'{name}: control inputs changed during execution')
    save(record,dict(execution_status='complete',**metadata,response=response,returncode=proc.returncode,
                     stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)))
    # Compact result deliberately excludes absolute paths and raw commands.
    return dict(name=name,status=expected,returncode=proc.returncode,
                capsule_sha256=source_hash,runner_sha256=binary_hash,shader_sha256=shader_hash,
                command_sha256=metadata['command_sha256'],record_sha256=sha(record),
                stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),
                dispatches=response.get('dispatches',0),validated_samples=response.get('validated_samples',0),
                device_name=response.get('device'),software=response.get('software'),readback_mode=readback)


def run(args):
    # Import here so --help works before the separately owned exporter is present.
    from capture import validate_capsule
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    summary=out/'gpu-controls.json';save(summary,dict(execution_status='incomplete',stage=args.stage))
    require(args.stage=='python' or args.runner is not None, 'host/GPU controls require --runner')
    require(args.stage!='gpu' or args.shader is not None, 'GPU controls require --shader')
    runner=args.runner.resolve() if args.runner else None
    shader=args.shader.resolve() if args.shader else None
    trial=partial(invoke,readback=args.readback)
    capsules=[p.resolve() for p in args.capsules]
    require(len(capsules)==len(set(capsules)), 'duplicate positive capsules')
    rows=[];positive=[]
    for i,path in enumerate(capsules):
        validate_capsule(path)
        h=struct.unpack_from('<64I',path.read_bytes())
        positive.append(dict(capsule_sha256=sha(path),width=h[4],height=h[5],block=h[6],alpha=h[8],samples=h[38]))
        if args.stage in ('host','gpu'):
            rows.append(trial(out,f'positive-{i}-validate',runner,path,'validated'))
        if args.stage=='gpu':
            rows.append(trial(out,f'positive-{i}-gpu',runner,path,'success',shader,h[38]))
    faults,changed_golden,h=mutations(capsules[0].read_bytes())
    fault_paths={};refusals=[]
    for name,data in faults.items():
        path=out/(name+'.bin');path.write_bytes(data);fault_paths[name]=path
        python_reject(validate_capsule,path);refusals.append(dict(name=name,capsule_sha256=sha(path)))
        if args.stage in ('host','gpu'):
            rows.append(trial(out,name+'-validate',runner,path,'validation_error'))
    golden=out/'changed-golden.bin';golden.write_bytes(changed_golden)
    validate_capsule(golden)
    if args.stage in ('host','gpu'):
        rows.append(trial(out,'changed-golden-validate',runner,golden,'validated'))
    if args.stage=='gpu':
        # The normal entry point must retain its validation guard too.
        for name in ('truncated','wrong_table','out_of_bound_mv'):
            rows.append(trial(out,name+'-gpu-entry',runner,fault_paths[name],'validation_error',shader))
        rows.append(trial(out,'changed-golden-gpu',runner,golden,'gpu_mismatch',shader,h[38]))
        original=shader.read_text()
        require(original.count(STORE)==1, 'unregistered GPU store anchor; review the new shader before fault injection')
        xor_shader=out/'fault-xor.comp';xor_shader.write_text(original.replace(STORE,
            'dst[pc.plane_offset + out_index] = uint(result) ^ 1u;'))
        empty_shader=out/'fault-no-write.comp';empty_shader.write_text(original.replace(STORE,
            '/* deliberate no-write counterfactual: output must retain poison */'))
        rows.append(trial(out,'xor-shader-gpu',runner,capsules[0],'gpu_mismatch',xor_shader,h[38]))
        rows.append(trial(out,'no-write-shader-gpu',runner,capsules[0],'gpu_output_invalid',empty_shader,h[38]))
    result=dict(schema=1,execution_status='complete',stage=args.stage,readback_mode=args.readback,
                scope='Capsule validation and explicit failure detection; no speed or interpolation-quality claim',
                gpu_controls_status='complete' if args.stage=='gpu' else 'not_run',
                positive_capsules=positive,python_validation_refusals=refusals,
                changed_golden_passed_python_validation=True,runner_trials=rows)
    save(summary,result);print(summary)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    p.add_argument('--capsules',type=Path,nargs='+',required=True)
    p.add_argument('--stage',choices=('python','host','gpu'),default='python')
    p.add_argument('--runner',type=Path);p.add_argument('--shader',type=Path)
    p.add_argument('--readback',choices=('direct','staging'),default='direct')
    run(p.parse_args())


if __name__=='__main__':main()
