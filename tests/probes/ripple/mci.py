#!/usr/bin/env python3
"""Reproduce the independent CPU MCI baseline and verify its displayed predecessor.

mci.py SCRATCH --ffmpeg PATH --ffprobe PATH

Reads {shirt,suit}-source.mkv and {shirt,suit}/mci.mkv. Writes only new
{shirt,suit}/mci-recheck.mkv, diagnostic logs, and path-free mci-recheck.json.
The shown mci.mkv files are never overwritten. Matching decoded grayscale bytes
verify this reproduction's pixels, not a historical command or a quality verdict.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np


FILTER = ('settb=expr=1/48000,setpts=N*2002,tpad=stop_mode=clone:stop=2,'
          'minterpolate=fps=48000/1001:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1')
SOURCE_INDICES = [48, 60, 72, 84]
OUTPUT_INDICES = [96, 120, 144, 168]
CROPS = {'shirt': (240,230,700,620), 'suit': (160,80,960,800)}


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def probe(ffprobe,path):
    result=subprocess.run([ffprobe,'-v','error','-select_streams','v:0','-count_frames',
        '-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(path)],
        capture_output=True,check=True)
    streams=json.loads(result.stdout)['streams']
    if len(streams)!=1:
        raise ValueError('expected one selected video stream')
    s=streams[0]
    return dict(width=int(s['width']),height=int(s['height']),frames=int(s['nb_read_frames']),rate=s['r_frame_rate'])


def decode_hash(ffmpeg,path,info,log):
    """Bounded-memory hash/count of every decoded grayscale16 sample, in frame order."""
    command=[ffmpeg,'-nostdin','-v','error','-i',str(path),'-map','0:v:0','-an',
             '-fps_mode','passthrough','-pix_fmt','gray16le','-f','rawvideo','-']
    digest=hashlib.sha256();size=0
    with log.open('wb') as errors:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors)
        try:
            for block in iter(lambda:process.stdout.read(1024*1024),b''):
                digest.update(block);size+=len(block)
        finally:
            process.stdout.close()
        if process.wait()!=0:
            raise RuntimeError('grayscale decoding failed; inspect the external decode log')
    frame_bytes=info['width']*info['height']*2
    if size%frame_bytes or size//frame_bytes!=info['frames']:
        raise ValueError('decoded grayscale length disagrees with probed frame count')
    return dict(pixel_format='gray16le',sha256=digest.hexdigest(),frames=size//frame_bytes,bytes=size,
                width=info['width'],height=info['height'])


def selected_gray(ffmpeg,path,indices,info,log):
    select='+'.join(f'eq(n\\,{n})' for n in indices)
    command=[ffmpeg,'-nostdin','-v','error','-i',str(path),'-map','0:v:0','-an',
             '-vf','select='+select,'-fps_mode','passthrough','-pix_fmt','gray16le','-f','rawvideo','-']
    with log.open('wb') as errors:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=errors,check=True)
    array=np.frombuffer(result.stdout,'<u2')
    expected=len(indices)*info['width']*info['height']
    if array.size!=expected:
        raise ValueError('explicit retained-frame selection has the wrong decoded length')
    return array.reshape(len(indices),info['height'],info['width'])


def compare_retained(source,output):
    difference=(output.astype(np.float64)-source.astype(np.float64))*(255.0/65535.0)
    return [dict(source_frame=s,output_frame=o,rms_dn=float(np.sqrt(np.mean(d*d))),
                 max_abs_dn=float(np.max(np.abs(d))),exact_pixels=bool(np.array_equal(a,b)))
            for s,o,d,a,b in zip(SOURCE_INDICES,OUTPUT_INDICES,difference,source,output)]


def compare_midpoints_to_endpoints(source_pairs,midpoints):
    rows=[]
    for i,k in enumerate(SOURCE_INDICES):
        a,b=source_pairs[2*i:2*i+2];mid=midpoints[i]
        da=(mid.astype(np.float64)-a.astype(np.float64))*(255.0/65535.0)
        db=(mid.astype(np.float64)-b.astype(np.float64))*(255.0/65535.0)
        eq_a,eq_b=mid==a,mid==b
        rows.append(dict(source_a=k,source_b=k+1,output_midpoint=2*k+1,
            rms_to_a_dn=float(np.sqrt(np.mean(da*da))),rms_to_b_dn=float(np.sqrt(np.mean(db*db))),
            exact_pixel_fraction_a=float(np.mean(eq_a)),exact_pixel_fraction_b=float(np.mean(eq_b)),
            exact_pixel_fraction_either=float(np.mean(eq_a|eq_b)),
            whole_crop_equals_a=bool(eq_a.all()),whole_crop_equals_b=bool(eq_b.all())))
    return rows


def holding_check(root,case,ffmpeg,source_info,shown_info,recheck_info):
    indices=[k+j for k in SOURCE_INDICES for j in (0,1)]
    midpoint_indices=[2*k+1 for k in SOURCE_INDICES]
    source=selected_gray(ffmpeg,root/f'{case}-source.mkv',indices,source_info,root/case/'mci-recheck-hold-source.log')
    shown=selected_gray(ffmpeg,root/case/'mci.mkv',midpoint_indices,shown_info,root/case/'mci-recheck-hold-shown.log')
    recheck=selected_gray(ffmpeg,root/case/'mci-recheck.mkv',midpoint_indices,recheck_info,root/case/'mci-recheck-hold-new.log')
    x,y,w,h=CROPS[case]
    if x+w>source_info['width'] or y+h>source_info['height']:
        raise ValueError('registered holding-check crop exceeds the source')
    source=source[:,y:y+h,x:x+w];shown=shown[:,y:y+h,x:x+w];recheck=recheck[:,y:y+h,x:x+w]
    old=compare_midpoints_to_endpoints(source,shown);new=compare_midpoints_to_endpoints(source,recheck)
    return dict(crop=list(CROPS[case]),shown=old,recheck=new,
                any_whole_crop_held=any(row['whole_crop_equals_a'] or row['whole_crop_equals_b'] for row in old+new),
                scope='Exact endpoint-holding check on four declared crops only; neither correspondence accuracy nor a quality score')


def verify_case(root,case,ffmpeg,ffprobe,replace):
    source=root/f'{case}-source.mkv';shown=root/case/'mci.mkv'
    output=root/case/'mci-recheck.mkv';pending=output.with_name('mci-recheck.partial.mkv')
    if output.resolve() in (source.resolve(),shown.resolve()) or pending.resolve() in (source.resolve(),shown.resolve()):
        raise ValueError('recheck may not overwrite a source or shown original')
    if (output.exists() or pending.exists()) and not replace:
        raise FileExistsError('recheck output already exists; choose --replace-recheck to repeat this new verification')
    info=probe(ffprobe,source);shown_info=probe(ffprobe,shown)
    if Fraction(info['rate'])!=Fraction(24000,1001) or info['frames']<=max(SOURCE_INDICES):
        raise ValueError('expected a native 24000/1001 source with all explicit retained indices')
    expected=2*info['frames']
    for actual in (shown_info,):
        if (actual['width'],actual['height'],actual['frames'])!=(info['width'],info['height'],expected):
            raise ValueError('shown original dimensions/count differ from the registered source')
        if abs(float(Fraction(actual['rate'])/Fraction(48000,1001))-1)>1e-5:
            raise ValueError('shown original has an unexpected output rate')
    source_sha,shown_sha=file_hash(source),file_hash(shown)
    template=['FFMPEG','-nostdin','-y','-v','warning','-i','SOURCE','-vf',FILTER,'-an',
              '-frames:v',str(expected),'-c:v','ffv1','-level','3','-pix_fmt','yuv420p','OUTPUT']
    command=[ffmpeg if v=='FFMPEG' else str(source) if v=='SOURCE' else str(pending) if v=='OUTPUT' else v for v in template]
    print(f'{case}: rendering CPU MCI recheck ({info["frames"]} → {expected} frames)',flush=True)
    start=time.monotonic()
    with (root/case/'mci-recheck-render.log').open('wb') as errors:
        subprocess.run(command,stdout=subprocess.DEVNULL,stderr=errors,check=True)
    elapsed=time.monotonic()-start
    actual=probe(ffprobe,pending)
    if (actual['width'],actual['height'],actual['frames'])!=(info['width'],info['height'],expected):
        raise ValueError('recheck render has the wrong dimensions/count')
    if abs(float(Fraction(actual['rate'])/Fraction(48000,1001))-1)>1e-5:
        raise ValueError('recheck render has the wrong rate')
    pending.replace(output)
    print(f'{case}: comparing complete decoded grayscale streams',flush=True)
    old=decode_hash(ffmpeg,shown,shown_info,root/case/'mci-recheck-shown-decode.log')
    new=decode_hash(ffmpeg,output,actual,root/case/'mci-recheck-new-decode.log')
    a=selected_gray(ffmpeg,source,SOURCE_INDICES,info,root/case/'mci-recheck-source-retained.log')
    b=selected_gray(ffmpeg,shown,OUTPUT_INDICES,shown_info,root/case/'mci-recheck-shown-retained.log')
    c=selected_gray(ffmpeg,output,OUTPUT_INDICES,actual,root/case/'mci-recheck-new-retained.log')
    held=holding_check(root,case,ffmpeg,info,shown_info,actual)
    if file_hash(source)!=source_sha or file_hash(shown)!=shown_sha:
        raise ValueError('source or shown original changed during verification')
    equal=old==new
    print(f'{case}: decoded grayscale equality = {equal}; retained indices checked explicitly',flush=True)
    return dict(source=info,shown=shown_info,recheck=actual,command_template=template,source_sha256=source_sha,
                shown_container_sha256=shown_sha,recheck_container_sha256=file_hash(output),
                shown_decoded_gray=old,recheck_decoded_gray=new,decoded_gray_equal=equal,
                retained_shown=compare_retained(a,b),retained_recheck=compare_retained(a,c),
                midpoint_endpoint_comparison=held,
                wall_seconds=elapsed,scope='Pixel provenance comparison only; no quality verdict')


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('root',type=Path);p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True)
    p.add_argument('--cases',nargs='+',choices=('shirt','suit'),default=['shirt','suit'])
    p.add_argument('--replace-recheck',action='store_true')
    p.add_argument('--check-holding-only',action='store_true',help='add explicit midpoint/endpoint checks to an already completed recheck; do not render')
    args=p.parse_args()
    if len(set(args.cases))!=len(args.cases):p.error('case names must be unique')
    if args.check_holding_only:
        destination=args.root/'mci-recheck.json';report=json.loads(destination.read_text())
        if report.get('execution_status')!='complete':
            raise ValueError('holding-only mode requires a completed pixel-provenance recheck')
        if file_hash(args.ffmpeg)!=report['ffmpeg_binary_sha256']:
            raise ValueError('holding-only mode requires the verified decoder binary')
        report['holding_check_status']='incomplete'
        destination.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        for case in args.cases:
            record=report['cases'][case]
            files=((args.root/f'{case}-source.mkv','source_sha256'),(args.root/case/'mci.mkv','shown_container_sha256'),
                   (args.root/case/'mci-recheck.mkv','recheck_container_sha256'))
            if any(file_hash(path)!=record[key] for path,key in files):
                raise ValueError('a previously verified input changed before the holding check')
            record['midpoint_endpoint_comparison']=holding_check(args.root,case,args.ffmpeg,record['source'],record['shown'],record['recheck'])
            if any(file_hash(path)!=record[key] for path,key in files):
                raise ValueError('a previously verified input changed during the holding check')
        report['holding_check_status']='complete' if all('midpoint_endpoint_comparison' in v for v in report['cases'].values()) else 'partial'
        destination.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(json.dumps({case:report['cases'][case]['midpoint_endpoint_comparison'] for case in args.cases},indent=2));return
    report=dict(schema=1,execution_status='incomplete',condition='CPU_MCI_pipeline_provenance_recheck',cases={},
                scope='Compare new decoded pixels with the shown originals; neither historical-command proof nor quality conclusion',
                retained_source_indices=SOURCE_INDICES,retained_output_indices=OUTPUT_INDICES,
                decode_command_template=['FFMPEG','-nostdin','-v','error','-i','VIDEO','-map','0:v:0','-an',
                                         '-fps_mode','passthrough','-pix_fmt','gray16le','-f','rawvideo','-'])
    destination=args.root/'mci-recheck.json'
    write=lambda:destination.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    write()
    report['ffmpeg_version']=subprocess.run([args.ffmpeg,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    report['ffmpeg_binary_sha256']=file_hash(args.ffmpeg)
    report['ffprobe_version']=subprocess.run([args.ffprobe,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    report['ffprobe_binary_sha256']=file_hash(args.ffprobe)
    for case in args.cases:
        report['active_case']=case;write()
        report['cases'][case]=verify_case(args.root,case,args.ffmpeg,args.ffprobe,args.replace_recheck);write()
    report.pop('active_case',None)
    report['execution_status']='complete'
    report['all_decoded_gray_equal']=all(v['decoded_gray_equal'] for v in report['cases'].values())
    report['all_explicit_retained_pixels_equal']=all(row['exact_pixels'] for v in report['cases'].values()
        for group in ('retained_shown','retained_recheck') for row in v[group])
    report['holding_check_status']='complete'
    write();print(json.dumps({k:report[k] for k in ('execution_status','all_decoded_gray_equal','all_explicit_retained_pixels_equal')},indent=2))


if __name__=='__main__':main()
