#!/usr/bin/env python3
"""Verify external exactness/timing evidence; emit compact path-free JSON/Markdown.

summarize.py OUT_STEM --fixtures fixtures.json --checks CHECK [...] [--benches BENCH ...]
No media decode, GPU work or benchmarking. Original records remain external.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics
from gate import canonical, certified_gate, command, compare, load_fixtures, parse_frames, parse_profile, require, save, sha


def record(path, case, binaries, role):
    path=Path(path);rec=json.loads(path.read_text());stem=path.with_suffix('')
    require(rec.get('execution_status')=='complete' and rec.get('returncode')==0, 'incomplete external run')
    require(rec['case']==case and rec['source_sha256']==case['sha256'], 'run/input disagreement')
    require(rec['binary_sha256']==binaries[role], 'run/binary disagreement')
    require(sha(stem.with_suffix('.framemd5'))==rec['framemd5_sha256'] and
            sha(stem.with_suffix('.log'))==rec['log_sha256'], 'run raw evidence changed')
    parsed=parse_frames(stem.with_suffix('.framemd5').read_text(),case)
    require(parsed==rec['frame_records'] and parse_profile(stem.with_suffix('.log').read_text())==rec['profile'],
            'run JSON disagrees with raw evidence')
    require(hashlib.sha256(canonical(rec['command'])).hexdigest()==rec['command_sha256'], 'run command hash disagreement')
    require(rec['command']==command(rec['command'][0],case,rec['filter_threads'],rec['mask'],rec['mb_size']),
            'run command differs from registered pipeline/configuration')
    count=len(parsed['frames'])
    require(type(rec['output_frames']) is int and rec['output_frames']==count, 'run output count disagrees with raw records')
    wall=rec['wall_seconds']
    require(isinstance(wall,(int,float)) and math.isfinite(wall) and wall>0, 'invalid process wall time')
    derived=dict(output_fps=count/wall,
                 source_duration_wall_ratio=float(Fraction(case['frames'])/Fraction(case['rate']))/wall)
    require(all(rec[key]==value for key,value in derived.items()), 'stale/inconsistent derived timing metric')
    rec.update(derived)
    compact={key:rec[key] for key in ('binary_sha256','source_sha256','command_sha256','framemd5_sha256','log_sha256',
                                     'mask','filter_threads','mb_size','profile','output_frames')}
    compact.update(record_sha256=sha(path), semantic_frame_records_sha256=hashlib.sha256(canonical(parsed)).hexdigest())
    return rec,compact


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out_stem',type=Path)
    p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--checks',nargs='+',type=Path,required=True)
    p.add_argument('--benches',nargs='*',type=Path,default=[]);a=p.parse_args()
    output=a.out_stem.with_suffix('.json');markdown=a.out_stem.with_suffix('.md')
    save(output,dict(execution_status='incomplete'));markdown.write_text('Evidence extraction incomplete.\n')
    fixtures=load_fixtures(a.fixtures);cases=fixtures['cases'];checks=[];check_by_sha={};runs={};timings=[]
    for path in a.checks:
        original=json.loads(path.read_text());binary_hashes=original['binary_sha256']
        check=certified_gate(path,a.fixtures,binary_hashes);digest=sha(path)
        require(digest not in check_by_sha, 'duplicate check summary')
        check_by_sha[digest]=check;entries=[]
        for row in check['rows']:
            ids={}
            for role in ('baseline','candidate'):
                rec,small=record(row[role+'_record'],cases[row['case']],binary_hashes,role)
                ids[role]=small['record_sha256'];runs[ids[role]]=small
            entries.append({k:row[k] for k in ('case','mb_size','mask','threads','repetition','exact')}|dict(records=ids))
        checks.append(dict(summary_sha256=digest,binary_sha256=binary_hashes,host=check['host'],rows=entries))
    for path in a.benches:
        bench=json.loads(path.read_text())
        require(bench.get('execution_status')=='complete' and bench.get('schema')==1, 'incomplete benchmark')
        require(bench['exactness_gate_sha256'] in check_by_sha, 'benchmark lacks supplied exactness gate')
        check=check_by_sha[bench['exactness_gate_sha256']]
        require(bench['fixtures_sha256']==sha(a.fixtures) and bench['binary_sha256']==check['binary_sha256'], 'benchmark provenance mismatch')
        require(bench['sink']=='rawvideo framemd5' and bench['rows'], 'wrong benchmark sink/empty results')
        rows=[]
        for row in bench['rows']:
            require(row['rounds']>=1 and row['warmups']>=1, 'missing timed rounds/warmups')
            certification=[r for r in check['rows'] if all(r[k]==row[k] for k in ('case','mb_size','mask','threads'))]
            require(certification, 'timed configuration was not certified')
            base=json.loads(Path(certification[0]['baseline_record']).read_text());reference=base['frame_records']
            folder=path.parent/f"{row['case']}-mb{row['mb_size']}-m{row['mask']}-t{row['threads']}"
            ids={};expected_metrics={}
            for role in ('baseline','candidate'):
                role_ids=[];timed=[]
                for i in range(-row['warmups'],row['rounds']):
                    label=role+'-'+(f'warm{-i}' if i<0 else f'round{i}')
                    rec,small=record(folder/(label+'.json'),cases[row['case']],bench['binary_sha256'],role)
                    require(rec['mask']==(None if role=='baseline' else row['mask']) and
                            rec['filter_threads']==(1 if role=='baseline' else row['threads']) and
                            rec['mb_size']==row['mb_size'], 'timing configuration mismatch')
                    compare(reference,rec['frame_records'])
                    require(all(rec['profile'][k]==base['profile'][k] for k in ('pairs','draws')), 'timing stage counts changed')
                    rid=small['record_sha256'];runs[rid]=small;role_ids.append(dict(warmup=i<0,index=i,record=rid))
                    if i>=0:timed.append(rec)
                ids[role]=role_ids
                actual={k:[r[k] for r in timed] for k in ('wall_seconds','user_seconds','system_seconds','output_fps','source_duration_wall_ratio')}
                actual.update({k:[r['profile'][k] for r in timed] for k in ('pairs','draws','me_us','overlap_us','output_us')})
                expected_metrics[role]={}
                for key,values in actual.items():
                    require(all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in values), 'invalid timing metric')
                    metric=dict(values=values,median=statistics.median(values),minimum=min(values),maximum=max(values))
                    require(metric==row['roles'][role][key], 'timing summary disagrees with its individual records')
                    expected_metrics[role][key]=metric
            speed=expected_metrics['baseline']['wall_seconds']['median']/expected_metrics['candidate']['wall_seconds']['median']
            require(speed==row['wall_speedup'], 'wrong reported speedup')
            rows.append({k:row[k] for k in ('case','mb_size','mask','threads','rounds','warmups','wall_speedup')}|
                        dict(roles=expected_metrics,records=ids))
        timings.append(dict(summary_sha256=sha(path),exactness_gate_sha256=bench['exactness_gate_sha256'],
                            host=bench['host'],sink=bench['sink'],rows=rows))
    used={r['case'] for c in checks for r in c['rows']}
    compact_cases={name:{k:cases[name][k] for k in ('width','height','pix_fmt','frames','rate','output_rate','sha256','original_source_sha256','preparation_command_sha256')} for name in sorted(used)}
    result=dict(schema=1,execution_status='complete',scope='All-plane output equivalence and CPU process timing; no quality/GPU claim',
                fixtures_sha256=sha(a.fixtures),fixture_preparer_sha256=fixtures['preparer_ffmpeg_sha256'],
                cases=compact_cases,checks=checks,benchmarks=timings,runs=runs)
    # The schema intentionally omits raw commands, source/output paths and hostnames.
    save(output,result)
    lines=['# CPU MCI exactness and timing','',
           'All-plane byte/timestamp equality; this is not an interpolation-quality claim.','',
           '| Case | Block | Mask | Threads | Exact runs |','|---|---:|---:|---:|---:|']
    groups={}
    for check in checks:
        for row in check['rows']:
            key=tuple(row[k] for k in ('case','mb_size','mask','threads'));groups[key]=groups.get(key,0)+1
    lines += ['| '+' | '.join(map(str,(*key,count)))+' |' for key,count in sorted(groups.items())]
    if timings:
        lines += ['','| Case | Block | Mask / threads | Baseline s | Candidate s | Speedup | Candidate ME / overlap / output ms |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for bench in timings:
            for row in bench['rows']:
                b,c=row['roles']['baseline'],row['roles']['candidate']
                stages=' / '.join(f"{c[k]['median']/1000:.2f}" for k in ('me_us','overlap_us','output_us'))
                lines.append(f"| {row['case']} | {row['mb_size']} | {row['mask']} / {row['threads']} | {b['wall_seconds']['median']:.4f} | {c['wall_seconds']['median']:.4f} | {row['wall_speedup']:.3f}x | {stages} |")
        lines += ['','Times are warmed interleaved process medians, with a consistent framemd5 sink. Stage wall times are not CPU time.']
    else:lines += ['','Timing pending; no speedup claim.']
    markdown.write_text('\n'.join(lines)+'\n');print(output);print(markdown)


if __name__=='__main__':main()
