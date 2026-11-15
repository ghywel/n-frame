#!/usr/bin/env python3
"""Read-only capture/replay evidence audit; never rerenders or creates a GPU.

Existing execution script hashes remain historical. This records a separate audit.
The supplied fixture manifest supplies original CPU input identities; its media
paths need not exist on the replay host. --cases scopes the declared matrix only.
"""
from array import array
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
from capture import ORIGINAL_SHA, validate_capsule
from gate import certified_gate, compare, parse_frames, require, save, sha


def validate_matrix(matrix_path, fixtures_path, selection='all'):
    matrix_path,fixtures_path=Path(matrix_path),Path(fixtures_path)
    matrix=json.loads(matrix_path.read_text());fixtures=json.loads(fixtures_path.read_text())
    require(matrix.get('execution_status')=='complete' and matrix.get('rows'), 'incomplete/empty capture matrix')
    require(fixtures.get('execution_status')=='complete' and fixtures.get('schema')==1, 'incomplete CPU fixture manifest')
    if 'fixtures_sha256' in matrix:
        require(matrix['fixtures_sha256']==sha(fixtures_path), 'capture matrix/fixture manifest hash disagreement')
    names=None if selection=='all' else set(selection.split(','))
    selected=[r for r in matrix['rows'] if names is None or r['case'] in names]
    require(selected and (names is None or names=={r['case'] for r in selected}), 'unknown/empty matrix selection')
    seen=set();bindings=[]
    for row in selected:
        name,mb=row['case'],row['mb_size'];key=(name,mb)
        require(re.fullmatch('[a-z0-9_]+',name) and name in fixtures['cases'] and mb in (4,8,16), 'invalid matrix case/block')
        require(key not in seen, 'duplicate matrix case/block');seen.add(key)
        require(row.get('complete_stream_exact') is True and row.get('capsules'), 'uncertified stream or empty capsule selection')
        case=fixtures['cases'][name];folder=matrix_path.parent/f'{name}-mb{mb}'
        manifest_path=folder/'capture.json'
        require(sha(manifest_path)==row['capture_manifest_sha256'], 'capture manifest changed')
        manifest=json.loads(manifest_path.read_text())
        require(manifest.get('execution_status')=='complete' and manifest.get('returncode')==0, 'incomplete capture execution')
        require(manifest['hashes']['source']==case['sha256'] and manifest['hashes']['original_c']==ORIGINAL_SHA,
                'capture source is not the declared CPU fixture/pinned scalar source')
        require(all(manifest['source'][k]==case[k] for k in ('width','height','pix_fmt','frames','rate','output_rate')),
                'capture/CPU fixture stream metadata mismatch')
        require(row['capsules']==manifest['capsules'], 'matrix capsules differ from their capture manifest')
        draws=manifest['requested_draws']
        require(draws and draws==sorted(set(draws)) and len(draws)<=16 and
                draws==[c['draw_index'] for c in row['capsules']], 'requested/captured draw selection mismatch')
        require(sha(folder/'output.framemd5')==manifest['output_records_sha256'] and
                sha(folder/'capture.log')==manifest['log_sha256'], 'capture output/log evidence changed')
        frames=parse_frames((folder/'output.framemd5').read_text(),case)
        require(manifest['output_frames']==len(frames['frames']), 'capture output count disagrees')
        rate,fps=Fraction(case['rate']),Fraction(case['output_rate'])
        denominator=math.lcm(rate.numerator,fps.numerator)
        for cap in row['capsules']:
            require(Path(cap['file']).name==cap['file'] and cap['file']==f"draw-{cap['draw_index']:010d}.bin", 'invalid capsule filename')
            path=folder/cap['file'];actual=validate_capsule(path)
            require(all(cap.get(k)==v for k,v in actual.items()), 'recorded capsule metadata differs from actual bytes')
            require(actual['width']==case['width'] and actual['height']==case['height'] and
                    actual['pixel_format']==case['pix_fmt'] and actual['mb_size']==mb, 'capsule case/block mismatch')
            require(Fraction(*actual['input_time_base'])==Fraction(1,denominator) and
                    Fraction(*actual['output_time_base'])==1/fps, 'capsule does not use registered time bases')
            indices=[actual[k]*Fraction(*actual['input_time_base'])*rate for k in ('source_a_pts','source_b_pts')]
            require(all(i.denominator==1 and 0<=i<=case['frames']+1 for i in indices) and indices[1]==indices[0]+1,
                    'source PTS do not identify adjacent registered inputs/tail clones')
            pair=[dict(normalized_input_index=int(i),original_frame_index=min(int(i),case['frames']-1),
                       cloned_tail=i>=case['frames']) for i in indices]
            require('source_pair' not in cap or cap['source_pair']==pair, 'recorded source pair disagrees with PTS')
            index=actual['output_pts']*Fraction(*actual['output_time_base'])*fps
            require(index.denominator==1 and 0<=index<len(frames['frames']) and cap['output_frame_index']==int(index),
                    'capsule output identity disagrees with frame records')
            with path.open('rb') as f:
                h=struct.unpack('<64I',f.read(256));f.seek(256+4*h[30]);packed=array('I');packed.frombytes(f.read(4*h[38]))
            if sys.byteorder!='little':packed.byteswap()
            require(hashlib.md5(bytes(v for v in packed)).hexdigest()==frames['frames'][int(index)]['md5'], 'golden is not actual emitted output')
            bindings.append(dict(case=name,mb_size=mb,draw_index=actual['draw_index'],path=path,actual=actual,
                capsule_sha256=actual['capsule_sha256'],source_sha256=case['sha256'],source_pair=pair,
                source_pair_metadata_present_at_capture='source_pair' in cap,
                capture_script_sha256=manifest['capture_script_sha256'],capture_manifest_sha256=sha(manifest_path),
                original_cpu_reference_sha256=row['cpu_reference_sha256'],
                original_matrix_complete_stream_exact_assertion=True,
                capture_golden_vs_emitted_output_verified=True,cpu_baseline_reaudited=False))
    return matrix,bindings


def validate_response(response, cap, repeats, readback_mode=None):
    samples=sum(cap['plane_words'])
    require(type(repeats) is int and repeats>=3, 'insufficient replay repetitions')
    mode=response.get('readback_mode','direct')
    require(mode in ('direct','staging'), 'unknown GPU readback mode')
    require(readback_mode is None or response.get('readback_mode')==readback_mode,
            'GPU result does not explicitly match requested readback mode')
    require(response.get('status')=='success' and response.get('full_yuv_byte_equal') is True and
            response.get('software') is False and bool(response.get('device')) and
            response.get('validated_samples')==samples and response.get('samples')==samples and
            response.get('warmup_iterations')==1 and response.get('measured_iterations')==repeats and
            response.get('dispatches')==3*(repeats+1), 'incomplete/nonhardware GPU result')
    require((response['width'],response['height'],response['alpha'])==(cap['width'],cap['height'],cap['alpha']),
            'GPU/capsule metadata mismatch')
    iterations=response.get('iterations')
    require(isinstance(iterations,list) and len(iterations)==repeats+1, 'truncated replay iteration records')
    for i,record in enumerate(iterations):
        require(record.get('warmup') is (i==0), 'wrong warmup/measurement flags')
        for k in ('upload_and_poison_wall_ns','dispatch_finish_wall_ns','download_wall_ns','pack_compare_wall_ns','total_replay_wall_ns'):
            require(type(record.get(k)) is int and record[k]>=0, 'invalid replay duration')
        require(record['total_replay_wall_ns']>=sum(record[k] for k in
                ('upload_and_poison_wall_ns','dispatch_finish_wall_ns','download_wall_ns','pack_compare_wall_ns')),
                'whole replay wall time is shorter than its serial measured components')
        times,counts=record['kernel_plane_ns'],record['timer_query_counts']
        require(len(times)==len(counts)==3, 'incomplete per-plane timer records')
        for value,count in zip(times,counts):
            require(type(count) is int and count>=0 and
                    ((count==1 and type(value) is int and value>=0) or (count!=1 and value is None)),
                    'timer availability/value disagreement')


def audit(matrix_path,fixtures_path,replays_path,selection='all',cpu_root=None):
    audit_sha=sha(__file__)
    inputs_sha=[sha(p) for p in (matrix_path,fixtures_path,replays_path)]
    matrix,bindings=validate_matrix(matrix_path,fixtures_path,selection)
    if cpu_root is not None:
        references={}
        for summary in Path(cpu_root).glob('*-check/check-summary.json'):
            raw=json.loads(summary.read_text())
            gate=certified_gate(summary,fixtures_path,raw['binary_sha256'])
            for row in gate['rows']:
                path=Path(row['baseline_record']);references[sha(path)]=path
        verified=set()
        for binding in bindings:
            digest=binding['original_cpu_reference_sha256']
            require(digest in references, 'recorded CPU baseline absent from completed exactness gates')
            path=references[digest];reference=json.loads(path.read_text())
            require(reference['source_sha256']==binding['source_sha256'] and reference['mb_size']==binding['mb_size'],
                    'CPU baseline input/block mismatch')
            key=(binding['case'],binding['mb_size'])
            if key not in verified:
                folder=Path(matrix_path).parent/f'{key[0]}-mb{key[1]}'
                actual=parse_frames((folder/'output.framemd5').read_text(),reference['case'])
                compare(reference['frame_records'],actual);verified.add(key)
            binding['cpu_baseline_reaudited']=True
    replays_path=Path(replays_path);result=json.loads(replays_path.read_text())
    require(result.get('execution_status')=='complete' and result.get('rows'), 'incomplete/empty replay evidence')
    require(result['hashes']['matrix']==sha(matrix_path), 'replay used a different capture matrix')
    require('fixtures' not in result['hashes'] or result['hashes']['fixtures']==sha(fixtures_path), 'replay fixture identity changed')
    by_key={(b['case'],b['mb_size'],b['draw_index']):b for b in bindings}
    rows=result['rows'];keys=[(r['case'],r['mb_size'],r['draw_index']) for r in rows]
    require(len(keys)==len(set(keys)) and set(keys)==set(by_key), 'missing/duplicate/unrequested GPU replay rows')
    compact=[]
    for key,row in zip(keys,rows):
        b=by_key[key];name=f'{key[0]}-mb{key[1]}-draw{key[2]}'
        output=replays_path.parent/(name+'.json');log=replays_path.parent/(name+'.log')
        require(sha(output)==row['result_sha256'] and sha(log)==row['log_sha256'], 'raw GPU result/log changed')
        response=json.loads(output.read_text());validate_response(response,b['actual'],response.get('measured_iterations'),result.get('readback_mode'))
        response.pop('capsule',None);response.pop('shader',None)
        require(response==row['response'] and row['capsule_sha256']==b['capsule_sha256'], 'replay summary/raw result disagreement')
        compact.append({k:v for k,v in b.items() if k not in ('path','actual')}|
                       dict(result_sha256=row['result_sha256'],log_sha256=row['log_sha256'],response=response,
                            readback_mode=response.get('readback_mode','direct'),
                            readback_mode_provenance='recorded' if 'readback_mode' in response else 'legacy_default_direct'))
    require(audit_sha==sha(__file__) and inputs_sha==[sha(p) for p in (matrix_path,fixtures_path,replays_path)],
            'auditor or input summaries changed during audit')
    return dict(schema=1,execution_status='complete',scope='Read-only re-audit of existing executions; no re-render',
        original_replay_summary_sha256=sha(replays_path),original_replay_script_sha256=result['script_sha256'],
        original_capture_matrix_script_sha256=matrix.get('script_sha256'),
        original_capture_matrix_script_provenance='recorded' if matrix.get('script_sha256') else 'not_recorded',
        fixtures_sha256=sha(fixtures_path),replay_hashes=result['hashes'],audit_script_sha256=audit_sha,selection=selection,
        cpu_baseline_reaudited=cpu_root is not None,rows=compact)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('matrix',type=Path);p.add_argument('replays',type=Path)
    p.add_argument('out',type=Path);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--cases',default='all')
    p.add_argument('--cpu-root',type=Path)
    a=p.parse_args();save(a.out,dict(execution_status='incomplete'))
    result=audit(a.matrix,a.fixtures,a.replays,a.cases,a.cpu_root);save(a.out,result);print(a.out)


if __name__=='__main__':main()
