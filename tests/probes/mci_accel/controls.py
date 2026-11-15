#!/usr/bin/env python3
"""Cheap CPU/parser counterfactuals. Optional --ffmpeg proves chroma-only refusal."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from gate import canonical, certified_gate, command, compare, parse_frames, parse_profile, save, sha
from summarize import record


CASE=dict(width=66,height=34,pix_fmt='yuv420p',frames=2,rate='24',output_rate='24')
TEXT='''#format: frame checksums
#version: 2
#hash: MD5
#software: test
#tb 0: 1/24
#media_type 0: video
#codec_id 0: rawvideo
#dimensions 0: 66x34
#sar 0: 1/1
#stream#, dts, pts, duration, size, hash
0, 0, 0, 1, 3366, 11111111111111111111111111111111
0, 1, 1, 1, 3366, 22222222222222222222222222222222
'''


def rejects(name, f):
    try: f()
    except (ValueError,KeyError): print('rejected',name); return
    raise AssertionError('silently accepted '+name)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ffmpeg');a=p.parse_args()
    base=parse_frames(TEXT,CASE);compare(base,copy.deepcopy(base))
    for field,value in (('md5','0'*32),('pts',2),('dts',2),('duration',2),('bytes',3365)):
        bad=copy.deepcopy(base);bad['frames'][1][field]=value
        rejects('changed '+field,lambda:compare(base,bad))
    rejects('truncation',lambda:parse_frames(TEXT.rsplit('0, 1,',1)[0],CASE))
    rejects('extra frame',lambda:parse_frames(TEXT+'0, 2, 2, 1, 3366, '+'3'*32+'\n',CASE))
    rejects('timestamp',lambda:parse_frames(TEXT.replace('0, 1, 1,','0, 1, 2,'),CASE))
    rejects('timebase',lambda:parse_frames(TEXT.replace('1/24','1/25'),CASE))
    rejects('partial hash',lambda:parse_frames(TEXT.replace('2'*32,'2'*31),CASE))
    rejects('partial record',lambda:parse_frames(TEXT+'0, 2,',CASE))
    rejects('missing header',lambda:parse_frames(TEXT.replace('#hash: MD5\n',''),CASE))
    profile='MCI_PROFILE pairs=12 draws=12 me_us=123 overlap_us=45 output_us=67'
    assert parse_profile(profile)['pairs']==12
    dummy='MCI_PROFILE pairs=0 draws=0 me_us=0 overlap_us=0 output_us=0'
    assert parse_profile(dummy+'\n'+profile)==parse_profile(profile)
    rejects('dummy only',lambda:parse_profile(dummy))
    rejects('nonzero inactive profile',lambda:parse_profile(dummy.replace('draws=0','draws=1')+'\n'+profile))
    rejects('missing profile',lambda:parse_profile(''))
    rejects('duplicate profile',lambda:parse_profile(profile+'\n'+profile))
    rejects('malformed profile',lambda:parse_profile(profile.replace('me_us=123','me_us=-1')))
    with tempfile.TemporaryDirectory(prefix='mci-gate-evidence-') as td:
        root=Path(td);source=root/'input';source.write_bytes(b'fixture')
        case=dict(CASE,path=str(source),sha256=sha(source),original_source_sha256=None,
                  preparation_command_sha256=hashlib.sha256(canonical(None)).hexdigest())
        fixture=root/'fixtures.json';save(fixture,dict(schema=1,execution_status='complete',cases={'test':case},
                                                     preparer_ffmpeg_sha256='0'*64))
        hashes={}; paths={}
        for role in ('baseline','candidate'):
            binary=root/role;binary.write_bytes(role.encode());hashes[role]=sha(binary)
            mask,threads=(None,1) if role=='baseline' else (15,4)
            cmd=command(binary,case,threads,mask,16);stem=root/(role+'-run')
            stem.with_suffix('.framemd5').write_text(TEXT);stem.with_suffix('.log').write_text(dummy+'\n'+profile)
            rec=dict(execution_status='complete',returncode=0,binary_sha256=hashes[role],case=case,
                     source_sha256=case['sha256'],mask=mask,filter_threads=threads,mb_size=16,
                     command=cmd,command_sha256=hashlib.sha256(canonical(cmd)).hexdigest(),
                     frame_records=base,profile=parse_profile(profile),output_frames=2,
                     wall_seconds=1.0,user_seconds=0.1,system_seconds=0.01,output_fps=2.0,
                     source_duration_wall_ratio=2/24,
                     framemd5_sha256=sha(stem.with_suffix('.framemd5')),log_sha256=sha(stem.with_suffix('.log')))
            paths[role]=str(stem.with_suffix('.json'));save(paths[role],rec)
        gate=root/'gate.json';entry=dict(case='test',mb_size=16,mask=15,threads=4,repetition=0,exact=True,
                 baseline_record=paths['baseline'],candidate_record=paths['candidate'])
        evidence=dict(schema=1,execution_status='complete',fixtures_sha256=sha(fixture),binary_sha256=hashes,
                      host=dict(system='mock control'),rows=[entry])
        save(gate,evidence);certified_gate(gate,fixture,hashes)
        subprocess.run([sys.executable,str(Path(__file__).with_name('summarize.py')),str(root/'compact'),
                        '--fixtures',str(fixture),'--checks',str(gate)],check=True,capture_output=True)
        compact=(root/'compact.json').read_text()
        assert str(root) not in compact and json.loads(compact)['execution_status']=='complete'
        print('portable mocked evidence extraction passed')
        original=json.loads(Path(paths['candidate']).read_text())
        record(paths['candidate'],case,hashes,'candidate')
        bad=copy.deepcopy(original);bad['command'][bad['command'].index('-filter_threads')+1]='2'
        bad['command_sha256']=hashlib.sha256(canonical(bad['command'])).hexdigest()
        save(paths['candidate'],bad)
        rejects('timed command with recomputed hash',lambda:record(paths['candidate'],case,hashes,'candidate'))
        save(paths['candidate'],original)
        for field,value in (('output_frames',1),('output_fps',99),('source_duration_wall_ratio',99),('wall_seconds',0)):
            bad=dict(original);bad[field]=value;save(paths['candidate'],bad)
            rejects('timed '+field,lambda:record(paths['candidate'],case,hashes,'candidate'))
            save(paths['candidate'],original)
        for field,value in (('execution_status','incomplete'),('mask',0),('filter_threads',1),('source_sha256','0'*64)):
            original=json.loads(Path(paths['candidate']).read_text());bad=dict(original);bad[field]=value
            save(paths['candidate'],bad)
            rejects('certification '+field,lambda:certified_gate(gate,fixture,hashes))
            save(paths['candidate'],original)
        save(gate,dict(evidence,execution_status='incomplete'))
        rejects('incomplete summary',lambda:certified_gate(gate,fixture,hashes))
        save(gate,evidence);(root/'candidate-run.framemd5').write_text(TEXT.replace('2'*32,'3'*32))
        rejects('changed raw evidence',lambda:certified_gate(gate,fixture,hashes))
    if a.ffmpeg:
        with tempfile.TemporaryDirectory(prefix='mci-gate-control-') as td:
            root=Path(td);raw=bytearray([128])*(3366*2)
            def decode(name,data):
                source=root/(name+'.yuv');source.write_bytes(data)
                result=subprocess.run([a.ffmpeg,'-nostdin','-v','error','-threads','1','-f','rawvideo',
                    '-pixel_format','yuv420p','-video_size','66x34','-framerate','24','-i',str(source),
                    '-frames:v','2','-c:v','rawvideo','-threads','1','-pix_fmt','yuv420p',
                    '-fps_mode','passthrough','-enc_time_base','filter','-f','framemd5','-'],check=True,capture_output=True)
                return parse_frames(result.stdout.decode(),CASE)
            original=decode('original',raw);compare(original,decode('repeat',raw))
            raw[3366+66*34]+=1  # U only, second frame; grayscale-only gates miss it.
            rejects('actual single chroma pixel',lambda:compare(original,decode('chroma-fault',raw)))
            raw[3366+66*34]-=1;raw[3366+17]+=1
            rejects('actual single luma pixel',lambda:compare(original,decode('luma-fault',raw)))
    print('all exactness controls passed')


if __name__=='__main__':main()
