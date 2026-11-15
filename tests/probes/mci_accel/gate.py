#!/usr/bin/env python3
"""Prepare immutable inputs; gate all-plane exactness; time serial interleaved runs.

See GATE.md. All generated inputs, frame records, logs and results stay external.
No third-party Python modules. A benchmark requires a successful exactness gate.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import statistics
import subprocess
import time


PROFILE = re.compile(r'MCI_PROFILE pairs=(\d+) draws=(\d+) me_us=(\d+) overlap_us=(\d+) output_us=(\d+)')
PROFILE_KEYS = ('pairs', 'draws', 'me_us', 'overlap_us', 'output_us')
DEFAULT_CONFIGS = '0:1,1:1,2:2,4:4,8:1,15:4'


def require(test, message):
    if not test:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.partial')
    pending.write_text(json.dumps(value, indent=2) + '\n')
    pending.replace(path)


def host():
    return dict(system=platform.platform(),machine=platform.machine(),processor=platform.processor(),
                logical_cpus=os.cpu_count())


def probe(ffprobe, path):
    p = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'v:0', '-count_frames',
        '-show_entries', 'stream=width,height,pix_fmt,r_frame_rate,nb_read_frames',
        '-of', 'json', str(path)], capture_output=True, check=True)
    streams = json.loads(p.stdout)['streams']
    require(len(streams) == 1, 'expected exactly one selected video stream')
    s = streams[0]
    return dict(width=int(s['width']), height=int(s['height']), pix_fmt=s['pix_fmt'],
                frames=int(s['nb_read_frames']), rate=str(Fraction(s['r_frame_rate'])))


def frame_bytes(case):
    w, h = case['width'], case['height']
    if case['pix_fmt'] == 'yuv420p':
        return w*h + 2*((w+1)//2)*((h+1)//2)
    require(case['pix_fmt'] == 'yuv444p', 'unsupported gate pixel format')
    return 3*w*h


def output_count(case):
    n = Fraction(case['frames']) * Fraction(case['output_rate']) / Fraction(case['rate'])
    require(n.denominator == 1, 'fixture duration does not contain an integral output count')
    return int(n)


def parse_frames(text, case):
    """Strict v2 rawvideo framemd5 parser; checks expected physical times and bytes."""
    headers, rows = {}, []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith('#'):
            if ': ' in line:
                key, value = line[1:].split(': ', 1)
                require(key not in headers, 'duplicate frame-record header')
                headers[key] = value.strip()
            else:
                require(line.startswith('#stream#,'), 'unrecognized frame-record comment')
            continue
        parts = [p.strip() for p in line.split(',')]
        require(len(parts) == 6, 'malformed/incomplete frame record')
        require(re.fullmatch('[0-9a-f]{32}', parts[5]) is not None, 'invalid MD5 frame hash')
        nums = [int(p) for p in parts[:5]]
        require(nums[0] == 0, 'unexpected output stream')
        rows.append(dict(zip(('stream', 'dts', 'pts', 'duration', 'bytes', 'md5'), nums+[parts[5]])))
    required = {'format': 'frame checksums', 'version': '2', 'hash': 'MD5',
                'media_type 0': 'video', 'codec_id 0': 'rawvideo',
                'dimensions 0': f"{case['width']}x{case['height']}"}
    for key, value in required.items():
        require(headers.get(key) == value, f'wrong/missing header {key}')
    require('tb 0' in headers and 'sar 0' in headers, 'missing timing/aspect header')
    tb, rate = Fraction(headers['tb 0']), Fraction(case['output_rate'])
    require(tb > 0, 'nonpositive output time base')
    require(len(rows) == output_count(case), 'wrong output count (including truncated output)')
    for i, row in enumerate(rows):
        require(row['pts']*tb == Fraction(i, 1)/rate, f'wrong PTS at output {i}')
        require(row['dts'] == row['pts'], f'wrong rawvideo DTS at output {i}')
        require(row['duration']*tb == 1/rate, f'wrong duration at output {i}')
        require(row['bytes'] == frame_bytes(case), f'wrong all-plane byte count at output {i}')
    # Software strings legitimately differ across builds; all semantic headers stay.
    headers.pop('software', None)
    return dict(headers=headers, frames=rows)


def parse_profile(text):
    found = PROFILE.findall(text)
    require(found and text.count('MCI_PROFILE') == len(found), 'missing/malformed MCI_PROFILE')
    rows = [dict(zip(PROFILE_KEYS,map(int,values))) for values in found]
    active = [row for row in rows if row['pairs'] > 0]
    require(len(active) == 1, 'expected exactly one active bidirectional MCI_PROFILE')
    require(all(row['pairs'] > 0 or not any(row.values()) for row in rows), 'nonzero inactive MCI_PROFILE')
    return active[0]


def compare(reference, candidate):
    require(reference['headers'] == candidate['headers'], 'semantic frame-record headers changed')
    require(len(reference['frames']) == len(candidate['frames']), 'frame count changed')
    for i, (a, b) in enumerate(zip(reference['frames'], candidate['frames'])):
        require(a == b, f'output frame {i} differs (pixels, timestamp, duration or size)')


def specs(scratch):
    motion = scratch/'motionstress-20261113'
    ripple = scratch/'translation-ripple-20261115'
    result = {}
    for name in ('bars_v9', 'bars_h9', 'face_occluded'):
        result[name] = dict(source=motion/name/'source.mkv', filters='', width=640, height=360)
    result['pan43'] = dict(source=motion/'round2/pan_detail43/source.mkv', filters='', width=640, height=360)
    for name in ('frozen', 'grain'):
        result['rigid_'+name] = dict(source=ripple/'rigid'/name/'source.mkv', filters='',
                                     width=640, height=360, rate='24000/1001')
    result['static'] = dict(lavfi='color=c=gray:size=640x360:rate=24', width=640, height=360)
    result['cut'] = dict(source=motion/'bars_v9/source.mkv', filters="negate=enable='gte(n,6)'", width=640, height=360)
    result['border420'] = dict(source=motion/'round2/pan_detail43/source.mkv', filters='crop=638:358:1:1:exact=1', width=638, height=358)
    result['border444'] = dict(source=motion/'round2/pan_detail43/source.mkv', filters='crop=639:359:1:1:exact=1', width=639, height=359, pix_fmt='yuv444p')
    for name, n in (('shirt',119), ('suit',143)):
        result[name] = dict(source=ripple/f'{name}-source.mkv', original=True,
                            width=1920, height=1080, rate='24000/1001', frames=n)
    for item in result.values():
        item.setdefault('rate', '24')
        item.setdefault('frames', 12)
        item.setdefault('pix_fmt', 'yuv420p')
        item['output_rate'] = str(2*Fraction(item['rate']))
    return result


def prepare(args):
    root = args.out.resolve(); root.mkdir(parents=True, exist_ok=True)
    index = root/'fixtures.json'
    if index.exists():
        data = load_fixtures(index)
        print(f"Verified existing immutable fixtures: {len(data['cases'])}")
        return
    save(root/'prepare-status.json', dict(execution_status='incomplete'))
    cases = {}
    for name, spec in specs(args.scratch.resolve()).items():
        case = {k:spec[k] for k in ('width','height','pix_fmt','frames','rate','output_rate')}
        source = spec.get('source'); original_hash = sha(source) if source else None
        command = None
        if spec.get('original'):
            target = source
        else:
            target = root/f'{name}.mkv'
            pending = root/f'{name}.partial.mkv'
            command = [args.ffmpeg, '-nostdin', '-y', '-v', 'error', '-threads', '1', '-filter_threads', '1']
            command += ['-i',str(source)] if source else ['-f','lavfi','-i',spec['lavfi']]
            filters = [f for f in (spec.get('filters'), f"format={case['pix_fmt']}",
                       f"settb=expr=1/{Fraction(case['rate']).numerator},setpts=N*{Fraction(case['rate']).denominator}") if f]
            command += ['-map','0:v:0','-an','-vf',','.join(filters),'-frames:v',str(case['frames']),
                        '-c:v','ffv1','-level','3','-threads','1','-pix_fmt',case['pix_fmt'],str(pending)]
            with (root/f'{name}.prepare.log').open('wb') as log:
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=log, check=True)
            pending.replace(target)
        actual = probe(args.ffprobe, target)
        require(actual == {k:case[k] for k in actual}, f'{name}: prepared stream mismatch: {actual}')
        require(not source or sha(source) == original_hash, 'original source changed during preparation')
        case.update(path=str(target.resolve()), sha256=sha(target), original_source=str(source) if source else None,
                    original_source_sha256=original_hash, preparation_command=command,
                    preparation_command_sha256=hashlib.sha256(canonical(command)).hexdigest())
        cases[name] = case
        print('prepared', name, flush=True)
    cases['pan43_60'] = dict(cases['pan43'], output_rate='60')
    data = dict(schema=1, execution_status='complete', preparer_ffmpeg=str(Path(args.ffmpeg).resolve()),
                preparer_ffmpeg_sha256=sha(args.ffmpeg), ffprobe_sha256=sha(args.ffprobe), cases=cases)
    save(index, data); save(root/'prepare-status.json', dict(execution_status='complete', manifest_sha256=sha(index)))


def load_fixtures(path):
    data = json.loads(Path(path).read_text())
    require(data.get('execution_status') == 'complete' and data.get('schema') == 1, 'incomplete/unsupported fixture manifest')
    require(bool(data.get('cases')), 'no fixtures')
    for name, case in data['cases'].items():
        require(re.fullmatch('[a-z0-9_]+', name) is not None, 'unsafe fixture name')
        require(sha(case['path']) == case['sha256'], f'{name}: immutable input changed')
        output_count(case); frame_bytes(case)
    return data


def configs(text):
    result = []
    for item in text.split(','):
        mask, threads = map(int, item.split(':'))
        require(0 <= mask <= 15 and 1 <= threads <= 64, 'invalid mask:threads')
        require((mask,threads) not in result, 'duplicate mask:threads')
        result.append((mask,threads))
    require(bool(result), 'empty configurations')
    return result


def command(binary, case, threads, mask, mb_size):
    rate, output_rate = Fraction(case['rate']), Fraction(case['output_rate'])
    denominator = math.lcm(rate.numerator, output_rate.numerator)
    step = denominator * rate.denominator // rate.numerator
    filters = f'settb=expr=1/{denominator},setpts=N*{step},tpad=stop_mode=clone:stop=2,'
    filters += f'minterpolate=fps={output_rate}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:mb_size={mb_size}:vsbmc=1:mci_profile=1'
    if mask is not None:
        filters += f':mci_accel={mask}'
    return [str(Path(binary).resolve()),'-nostdin','-v','info','-nostats','-threads','1',
            '-filter_threads',str(threads),'-i',case['path'],'-map','0:v:0','-an','-vf',filters,
            '-frames:v',str(output_count(case)),'-c:v','rawvideo','-threads','1',
            '-pix_fmt',case['pix_fmt'],'-fps_mode','passthrough','-enc_time_base','filter','-f','framemd5','-']


def run(root, name, binary, case, threads, mask, mb_size, binary_hash):
    root.mkdir(parents=True, exist_ok=True)
    record = root/f'{name}.json'; frames = root/f'{name}.framemd5'; log = root/f'{name}.log'
    cmd = command(binary,case,threads,mask,mb_size)
    context = dict(command=cmd, command_sha256=hashlib.sha256(canonical(cmd)).hexdigest(),
                   binary_sha256=binary_hash, source_sha256=case['sha256'], mask=mask,
                   filter_threads=threads, mb_size=mb_size, case=case)
    save(record, dict(execution_status='incomplete', **context))
    require(sha(binary) == binary_hash and sha(case['path']) == case['sha256'], 'binary/source changed before run')
    before = resource.getrusage(resource.RUSAGE_CHILDREN); start = time.perf_counter()
    with frames.open('wb') as out, log.open('wb') as err:
        process = subprocess.run(cmd, stdout=out, stderr=err)
    wall = time.perf_counter()-start; after = resource.getrusage(resource.RUSAGE_CHILDREN)
    require(process.returncode == 0, f'{name}: FFmpeg failed ({process.returncode}); see {log}')
    parsed = parse_frames(frames.read_text(),case); profile = parse_profile(log.read_text())
    require(sha(binary) == binary_hash and sha(case['path']) == case['sha256'], 'binary/source changed during run')
    result = dict(execution_status='complete', **context, frame_records=parsed, profile=profile,
                  framemd5_sha256=sha(frames), log_sha256=sha(log), returncode=0,
                  wall_seconds=wall, user_seconds=after.ru_utime-before.ru_utime,
                  system_seconds=after.ru_stime-before.ru_stime,
                  output_frames=output_count(case), output_fps=output_count(case)/wall,
                  source_duration_wall_ratio=float(Fraction(case['frames'])/Fraction(case['rate']))/wall)
    save(record,result)
    return result


def select(data, names):
    selected = list(data['cases']) if names == 'all' else names.split(',')
    require(len(selected) == len(set(selected)) and selected, 'empty/duplicate case selection')
    require(all(n in data['cases'] for n in selected), 'unknown selected case')
    return [(n,data['cases'][n]) for n in selected]


def check(args):
    data = load_fixtures(args.fixtures); root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=True)
    summary_path = root/'check-summary.json'
    save(summary_path, dict(execution_status='incomplete'))
    hashes = dict(baseline=sha(args.baseline), candidate=sha(args.candidate))
    rows=[]
    for name, case in select(data,args.cases):
        for mb in args.mb_sizes:
            require(mb in (4,8,16), 'registered mb_sizes are 4,8,16')
            reference = run(root/f'{name}-mb{mb}', 'baseline', args.baseline,case,1,None,mb,hashes['baseline'])
            for mask, threads in configs(args.configs):
                for repetition in range(args.repeats):
                    label=f'm{mask}-t{threads}-r{repetition}'
                    result=run(root/f'{name}-mb{mb}',label,args.candidate,case,threads,mask,mb,hashes['candidate'])
                    compare(reference['frame_records'],result['frame_records'])
                    require(reference['profile']['pairs'] == result['profile']['pairs'] and
                            reference['profile']['draws'] == result['profile']['draws'], 'stage invocation counts changed')
                    rows.append(dict(case=name,mb_size=mb,mask=mask,threads=threads,repetition=repetition,
                                     baseline_record=str(root/f'{name}-mb{mb}'/'baseline.json'),
                                     candidate_record=str(root/f'{name}-mb{mb}'/f'{label}.json'),exact=True))
                    print('exact',name,mb,label,flush=True)
    summary=dict(schema=1,execution_status='complete',fixtures_sha256=sha(args.fixtures),binary_sha256=hashes,
                 host=host(),rows=rows)
    save(summary_path,summary)


def certified_gate(path, fixtures, binaries):
    gate=json.loads(Path(path).read_text())
    inputs=load_fixtures(fixtures)['cases']
    require(gate.get('execution_status') == 'complete' and gate.get('schema') == 1, 'exactness gate incomplete')
    require(gate['fixtures_sha256'] == sha(fixtures) and gate['binary_sha256'] == binaries, 'gate binary/input manifest mismatch')
    require(bool(gate['rows']), 'empty exactness gate')
    for row in gate['rows']:
        require(row.get('exact') is True, 'nonexact gate row')
        require(row['case'] in inputs, 'gate case is absent from current fixtures')
        records=[]
        for key, role in (('baseline_record','baseline'),('candidate_record','candidate')):
            rec=json.loads(Path(row[key]).read_text())
            require(rec.get('execution_status') == 'complete' and rec.get('returncode') == 0, 'incomplete gate run')
            require(rec['binary_sha256'] == binaries[role], 'gate run binary mismatch')
            require(rec['case'] == inputs[row['case']] and rec['source_sha256'] == inputs[row['case']]['sha256'], 'gate run input mismatch')
            require(rec['mb_size'] == row['mb_size'], 'gate run block size mismatch')
            require(rec['mask'] == (None if role=='baseline' else row['mask']) and
                    rec['filter_threads'] == (1 if role=='baseline' else row['threads']), 'gate run configuration mismatch')
            require(rec['command_sha256'] == hashlib.sha256(canonical(rec['command'])).hexdigest(), 'gate command hash mismatch')
            require(rec['command'] == command(rec['command'][0],rec['case'],rec['filter_threads'],rec['mask'],rec['mb_size']), 'gate command does not match registered pipeline')
            stem=Path(row[key]).with_suffix('')
            require(sha(stem.with_suffix('.framemd5')) == rec['framemd5_sha256'] and
                    sha(stem.with_suffix('.log')) == rec['log_sha256'], 'gate evidence changed')
            parsed=parse_frames(stem.with_suffix('.framemd5').read_text(),rec['case'])
            require(parsed == rec['frame_records'], 'gate JSON differs from raw frame records')
            require(parse_profile(stem.with_suffix('.log').read_text()) == rec['profile'], 'gate profile changed')
            records.append(rec)
        compare(records[0]['frame_records'],records[1]['frame_records'])
        require(all(records[0]['profile'][k] == records[1]['profile'][k] for k in ('pairs','draws')), 'gate stage invocation counts changed')
    return gate


def bench(args):
    data=load_fixtures(args.fixtures); root=args.out.resolve(); root.mkdir(parents=True,exist_ok=True)
    summary_path=root/'bench-summary.json'; save(summary_path,dict(execution_status='incomplete'))
    hashes=dict(baseline=sha(args.baseline),candidate=sha(args.candidate))
    gate=certified_gate(args.gate,args.fixtures,hashes)
    benchmark_host=host()
    rows=[]
    for name,case in select(data,args.cases):
        for mb in args.mb_sizes:
            for mask,threads in configs(args.configs):
                certified=[r for r in gate['rows'] if r['case']==name and r['mb_size']==mb and
                           r['mask']==mask and r['threads']==threads]
                require(bool(certified), 'requested benchmark configuration has not passed exactness')
                expected_profile=json.loads(Path(certified[0]['baseline_record']).read_text())['profile']
                dest=root/f'{name}-mb{mb}-m{mask}-t{threads}'; results={'baseline':[],'candidate':[]}; reference=None
                for repeat in range(-args.warmups,args.rounds):
                    order=('baseline','candidate') if repeat%2==0 else ('candidate','baseline')
                    for role in order:
                        label=f'{role}-'+(f'warm{-repeat}' if repeat<0 else f'round{repeat}')
                        result=run(dest,label,getattr(args,role),case,1 if role=='baseline' else threads,
                                   None if role=='baseline' else mask,mb,hashes[role])
                        if reference is None: reference=result['frame_records']
                        compare(reference,result['frame_records'])
                        require(all(result['profile'][k] == expected_profile[k] for k in ('pairs','draws')),
                                'timed stage invocation counts differ from the certified baseline')
                        if repeat>=0: results[role].append(result)
                    print('timed' if repeat>=0 else 'warmed',name,mb,mask,threads,repeat,flush=True)
                row=dict(case=name,mb_size=mb,mask=mask,threads=threads,rounds=args.rounds,warmups=args.warmups,roles={})
                for role, runs in results.items():
                    metric={key:[r[key] for r in runs] for key in ('wall_seconds','user_seconds','system_seconds','output_fps','source_duration_wall_ratio')}
                    metric.update({key:[r['profile'][key] for r in runs] for key in PROFILE_KEYS})
                    row['roles'][role]={key:dict(values=values,median=statistics.median(values),minimum=min(values),maximum=max(values)) for key,values in metric.items()}
                row['wall_speedup']=row['roles']['baseline']['wall_seconds']['median']/row['roles']['candidate']['wall_seconds']['median']
                rows.append(row)
    save(summary_path,dict(schema=1,execution_status='complete',exactness_gate_sha256=sha(args.gate),
         fixtures_sha256=sha(args.fixtures),binary_sha256=hashes,host=benchmark_host,exactness_host=gate['host'],
         sink='rawvideo framemd5',rows=rows))


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='action',required=True)
    prep=sub.add_parser('prepare'); prep.add_argument('out',type=Path); prep.add_argument('--scratch',type=Path,required=True)
    prep.add_argument('--ffmpeg',required=True); prep.add_argument('--ffprobe',required=True)
    for name in ('check','bench'):
        p=sub.add_parser(name); p.add_argument('out',type=Path); p.add_argument('--fixtures',type=Path,required=True)
        p.add_argument('--baseline',required=True); p.add_argument('--candidate',required=True)
        p.add_argument('--cases',default='bars_v9,bars_h9,face_occluded,pan43,static,cut,border420,border444,pan43_60')
        p.add_argument('--configs',default=DEFAULT_CONFIGS); p.add_argument('--mb-sizes',type=int,nargs='+',default=[16])
        if name=='check': p.add_argument('--repeats',type=int,default=1)
        else:
            p.add_argument('--gate',type=Path,required=True); p.add_argument('--rounds',type=int,default=3)
            p.add_argument('--warmups',type=int,default=1)
    args=parser.parse_args()
    if args.action=='check': require(args.repeats>=1,'repeats must be positive')
    if args.action=='bench': require(args.rounds>=1 and args.warmups>=1,'positive rounds and warmups required')
    {'prepare':prepare,'check':check,'bench':bench}[args.action](args)


if __name__=='__main__':
    main()
