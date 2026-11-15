#!/usr/bin/env python3
"""Run the registered GPU capture matrix serially and bind it to CPU exactness evidence.

run_captures.py GPU_OUT CPU_OUT CAPTURE_FFMPEG_SOURCE ORIGINAL_FFMPEG_SOURCE
No GPU dispatch, new media lookup, or performance measurement.
"""
import json
from pathlib import Path
import subprocess
import sys
from capture import sha, save, require
from gate import certified_gate, load_fixtures, parse_frames, compare


def main():
    root, cpu, build, original = [Path(p).resolve() for p in sys.argv[1:]]
    root.mkdir(parents=True, exist_ok=True)
    status = root/'capture-matrix.json'
    save(status, dict(execution_status='incomplete'))
    executed_script_sha=sha(__file__)
    fixture_path=cpu/'inputs/fixtures.json';fixture_sha=sha(fixture_path)
    fixtures = load_fixtures(fixture_path)['cases']
    small = ['bars_v9','bars_h9','face_occluded','pan43','static','cut',
             'border420','border444','rigid_frozen','rigid_grain','pan43_60']
    specs = [(name,16,'1,2,3,4,5' if name=='pan43_60' else '5','small-check') for name in small]
    specs += [(name,mb,'5','border-check') for name in ['border420','border444'] for mb in [4,8]]
    specs += [('shirt',16,'30','film-check'),('suit',16,'60','film-check')]
    rows = [];certifications={}
    for name,mb,draws,reference_folder in specs:
        case = fixtures[name]; dest = root/f'{name}-mb{mb}'
        if reference_folder not in certifications:
            gate_path=cpu/reference_folder/'check-summary.json'
            gate=json.loads(gate_path.read_text())
            certifications[reference_folder]=certified_gate(gate_path,fixture_path,gate['binary_sha256'])
        cmd = [sys.executable,str(Path(__file__).with_name('capture.py')),'run',case['path'],str(dest),
               '--ffmpeg',str(build/'ffmpeg'),'--ffprobe',str(build/'ffprobe'),
               '--original-source',str(original/'libavfilter/vf_minterpolate.c'),
               '--capture-source',str(build/'libavfilter/vf_minterpolate.c'),
               '--draws',draws,'--fps',case['output_rate'],'--mb-size',str(mb)]
        subprocess.run(cmd,check=True)
        manifest=json.loads((dest/'capture.json').read_text())
        require(manifest['execution_status']=='complete' and manifest['returncode']==0 and
                manifest['hashes']['source']==case['sha256'],
                'capture manifest/input mismatch')
        reference=cpu/reference_folder/f'{name}-mb{mb}'/'baseline.json'
        require(any(r['case']==name and r['mb_size']==mb and Path(r['baseline_record']).resolve()==reference.resolve()
                    for r in certifications[reference_folder]['rows']), 'CPU baseline is absent from its completed gate')
        record=json.loads(reference.read_text())
        require(record['execution_status']=='complete' and record['returncode']==0 and record['source_sha256']==case['sha256'] and
                record['case']==case and record['mask'] is None and record['filter_threads']==1 and record['mb_size']==mb,
                'CPU reference incomplete or input changed')
        raw=reference.with_suffix('.framemd5')
        require(sha(raw)==record['framemd5_sha256'],'CPU raw frame evidence changed')
        expected=parse_frames(raw.read_text(),case)
        compare(expected,record['frame_records'])
        require(sha(dest/'output.framemd5')==manifest['output_records_sha256'] and
                sha(dest/'capture.log')==manifest['log_sha256'], 'capture raw evidence changed')
        compare(expected,parse_frames((dest/'output.framemd5').read_text(),case))
        rows.append(dict(case=name,mb_size=mb,capture_manifest=str(dest/'capture.json'),
                         capture_manifest_sha256=sha(dest/'capture.json'),
                         cpu_reference_sha256=sha(reference),complete_stream_exact=True,
                         capsules=manifest['capsules']))
        print('captured and full-stream exact',name,mb,flush=True)
    require(sha(__file__)==executed_script_sha and sha(fixture_path)==fixture_sha, 'capture matrix script/fixtures changed during execution')
    save(status,dict(execution_status='complete',rows=rows,script_sha256=executed_script_sha,fixtures_sha256=fixture_sha))


if __name__=='__main__':main()
