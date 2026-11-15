#!/usr/bin/env python3
"""Prepare/score the preregistered frozen photographed-plane experiment; no GPU.

  rigid.py prepare SOURCE R/rigid
  rigid.py score R/rigid frozen oracle=ORACLE.mkv estimate=ESTIMATE.mkv
  rigid.py score R/rigid grain oracle=ORACLE.mkv estimate=ESTIMATE.mkv

See RIGID.md. All imagery stays outside the repository. Score requires complete,
hash-verified render.py sidecars. It reports instrument failures without adjusting
thresholds. No estimated-field attribution is valid if any instrument gate fails.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.ndimage import gaussian_filter

W,H,N=640,360,12
RATE=Fraction(24000,1001)
ORIGIN=(400,250)
ROI=(128,48,384,264)
PAD=10
SELECT=np.arange(9,20)
SOURCE_GATE=np.arange(8,21,2)
SEED=221115
NOISE_DN=2.0
SHADERS={
    'oracle':'b7ef3875a3c644947db4e0488d3d6871ae830370601f0963b033ec7d8008d464',
    'estimate':'0d8ec94d53dbbd7a607265eb3c62f62ccab3797df58ad3c580e5efe5ac9cc3c6',
}
GATES=dict(selected_source_full_frame_mae_max_dn=.5,each_oracle_midpoint_cpu_blend_rms_max_dn=1.0)


def require(ok,message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def certify_sidecar(label,side,source_hash,output_hash):
    require(label in SHADERS,'unregistered render label')
    require(side.get('execution_status')=='complete','render sidecar is not explicitly complete')
    require(side['shader_sha256']==SHADERS[label],f'{label}: registered shader hash mismatch')
    require(side['source_sha256']==source_hash and side['output_sha256']==output_hash,'render media hash mismatch')
    require(side['source_frames']==N and side['output_frames']==2*N and
            (side['width'],side['height'])==(W,H),'renderer counts/dimensions mismatch')
    require(Fraction(side['input_rate'])==RATE and Fraction(side['rate'])==2*RATE,'renderer rate metadata mismatch')


def probe(path,ffprobe):
    r=subprocess.run([ffprobe,'-v','error','-select_streams','v:0','-count_frames',
        '-show_entries','stream=width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,r_frame_rate,nb_read_frames',
        '-of','json',str(path)],capture_output=True,check=True)
    streams=json.loads(r.stdout)['streams']
    require(len(streams)==1,'expected one selected video stream')
    return streams[0]


def decode(path,ffmpeg,width=W,height=H,frames=None,frame=None):
    cmd=[ffmpeg,'-nostdin','-v','error','-i',str(path),'-an']
    if frame is not None:
        cmd+=['-vf',f'select=eq(n\\,{frame})','-frames:v','1']
    cmd+=['-pix_fmt','gray16le','-f','rawvideo','-']
    r=subprocess.run(cmd,capture_output=True,check=True)
    a=np.frombuffer(r.stdout,dtype='<u2')
    require(a.size%(width*height)==0,'incomplete decoded frame')
    a=a.reshape(-1,height,width).copy()
    if frames is not None:
        require(len(a)==frames,f'{path.name}: expected {frames} decoded frames, got {len(a)}')
    return a


def encode(path,a,rate,ffmpeg,ffprobe):
    path.parent.mkdir(parents=True,exist_ok=True)
    pending=path.with_name(path.stem+'.partial.mkv')
    command=[ffmpeg,'-nostdin','-y','-v','error','-f','rawvideo','-pixel_format','gray16le',
             '-video_size',f'{W}x{H}','-framerate',str(rate),'-i','pipe:0','-an','-c:v','ffv1',
             '-level','3','-pix_fmt','gray16le','-color_range','pc','-colorspace','bt709',
             '-color_primaries','bt709',str(pending)]
    subprocess.run(command,input=np.asarray(a,dtype='<u2').tobytes(),capture_output=True,check=True)
    info=probe(pending,ffprobe)
    require(int(info['nb_read_frames'])==len(a) and info['pix_fmt']=='gray16le','fixture format/count mismatch')
    require(abs(float(Fraction(info['r_frame_rate'])/rate)-1)<1e-5,'fixture rate mismatch')
    decoded=decode(pending,ffmpeg,frames=len(a))
    require(np.array_equal(decoded,a),'fixture FFV1 round trip changed code values')
    pending.replace(path)
    return dict(name=path.name,sha256=sha(path),frames=len(a),rate=str(rate),format=info)


def plate_frame(plate,t):
    x=ORIGIN[0]+16*t
    require(x==int(x),'unregistered fractional plate sample')
    x=int(x);y=ORIGIN[1]
    a=plate[y:y+H,x:x+W]
    require(a.shape==(H,W),'plate crop exceeded source support')
    return a


def material_patch(image,t):
    x=ROI[0]+16*(7-t);y=ROI[1];w,h=ROI[2:]
    require(x==int(x),'material registration would require resampling')
    x=int(x)
    require(x-PAD>=0 and x+w+PAD<=W and y-PAD>=0 and y+h+PAD<=H,'material ROI outside frame')
    return image[y-PAD:y+h+PAD,x-PAD:x+w+PAD]


def align(a,step):
    return np.stack([material_patch(frame,i*step) for i,frame in enumerate(a)]).astype(np.float32)/65535


def core(a):
    return a[...,PAD:-PAD,PAD:-PAD]


def rms_dn(a):
    return float(np.sqrt(np.mean(np.asarray(a,dtype=np.float64)**2))*255)


def gradient_square(a):
    gy,gx=np.gradient(a,axis=(-2,-1))
    return gy*gy+gx*gx


def filtered(a,sigma):
    return a if sigma==0 else gaussian_filter(a,(0,sigma,sigma),mode='reflect')


def measurements(actual,reference):
    """All errors share exact material coordinates; indices refer to outputs."""
    result={}
    for sigma in (0,2):
        error=filtered(actual-reference,sigma)
        pixels=core(error)
        grad=core(gradient_square(error))
        curvature=core(error[SELECT-1]-2*error[SELECT]+error[SELECT+1])
        rows=[dict(output_index=int(j),parity='inserted' if j%2 else 'source',
                   rms_dn=rms_dn(pixels[j]),mae_dn=float(np.abs(pixels[j]).mean()*255),
                   gradient_rms_dn_per_px=float(np.sqrt(grad[j].mean())*255),
                   curvature_rms_dn=rms_dn(curvature[k])) for k,j in enumerate(SELECT)]
        aggregates={}
        for name,indices in [('all',SELECT),('source',SELECT[SELECT%2==0]),('inserted',SELECT[SELECT%2==1])]:
            where=np.isin(SELECT,indices)
            aggregates[name]=dict(frames=len(indices),rms_dn=rms_dn(pixels[indices]),
                mae_dn=float(np.abs(pixels[indices]).mean()*255),
                gradient_rms_dn_per_px=float(np.sqrt(grad[indices].mean())*255),
                curvature_rms_dn=rms_dn(curvature[where]))
        result['raw' if sigma==0 else 'sigma2']=dict(parity=aggregates,per_output=rows,
            all_output_error_first_difference_rms_dn=rms_dn(np.diff(pixels[SELECT],axis=0)),
            inserted_only_error_first_difference_rms_dn=rms_dn(np.diff(pixels[SELECT[SELECT%2==1]],axis=0)),
            difference_step_source_frames=dict(all_outputs=.5,inserted_only=1.0))
    return result


def shape_features(actual,clean):
    result={}
    mids=SELECT[SELECT%2==1]
    for sigma in (0,2):
        a=filtered(actual,sigma);t=filtered(clean,sigma)
        rows=[]
        for j in SELECT:
            image=core(a[j]);truth=core(t[j]);u=image-image.mean();v=truth-truth.mean()
            variance=float(np.mean(v*v));require(variance>1e-12,'contrast reference is flat')
            gain=float(np.mean(u*v)/variance)
            gy,gx=np.gradient(a[j]);ty,tx=np.gradient(t[j])
            numerator=float(np.mean(core(gy*ty+gx*tx)))
            denominator=float(np.mean(core(ty*ty+tx*tx)))
            rows.append(dict(output_index=int(j),parity='inserted' if j%2 else 'source',
                contrast_gain=gain,contrast_gain_error=gain-1,
                contrast_rms_ratio=float(np.std(image)/np.std(truth)),
                gradient_gain=numerator/max(denominator,1e-20),
                contrast_fit_residual_rms_dn=rms_dn(u-gain*v)))
        chord=a[mids]-.5*(a[mids-1]+a[mids+1])
        chord_rows=[dict(output_index=int(j),rms_dn=rms_dn(core(chord[k])),
             gradient_rms_dn_per_px=float(np.sqrt(core(gradient_square(chord[k])).mean())*255)) for k,j in enumerate(mids)]
        result['raw' if sigma==0 else 'sigma2']=dict(per_output=rows,source_to_inserted_chord=chord_rows,
             source_to_inserted_chord_rms_dn=rms_dn(core(chord)),
             source_to_inserted_chord_gradient_rms_dn_per_px=float(np.sqrt(core(gradient_square(chord)).mean())*255))
    return result


def prepare(args):
    root=args.out;root.mkdir(parents=True,exist_ok=True)
    write_json(root/'fixtures.json',dict(execution_status='incomplete'))
    source_info=probe(args.source,args.ffprobe)
    require((source_info['width'],source_info['height'])==(1920,1080),'registered source must be 1920x1080')
    plate=decode(args.source,args.ffmpeg,1920,1080,frames=1,frame=48)[0]
    np.save(root/'plate-gray16.npy',plate)
    clean_source=np.stack([plate_frame(plate,float(i)) for i in range(N)])
    clean_truth=np.stack([plate_frame(plate,i/2) for i in range(2*N)])
    aligned_truth=align(clean_truth,.5)
    require(np.array_equal(aligned_truth,np.repeat(aligned_truth[:1],2*N,axis=0)),
            'known-motion material truth changed under exact registration')
    truth_info=encode(root/'truth.mkv',clean_truth,2*RATE,args.ffmpeg,args.ffprobe)
    rng=np.random.Generator(np.random.PCG64(SEED))
    noise=rng.normal(0,NOISE_DN/255,clean_source.shape)
    base=clean_source.astype(np.float64)/65535
    proposed=base+noise
    noisy=np.rint(np.clip(proposed,0,1)*65535).astype(np.uint16)
    condition_info={}
    for name,data in [('frozen',clean_source),('grain',noisy)]:
        info=encode(root/name/'source.mkv',data,RATE,args.ffmpeg,args.ffprobe)
        residual=core(align(data,1)-align(clean_source,1))*255
        centered=residual-residual.mean(axis=(1,2),keepdims=True)
        condition_info[name]=dict(source=info,noise_sigma_dn=0 if name=='frozen' else NOISE_DN,
            material_noise_rms_dn_by_source=[float(np.sqrt(np.mean(v.astype(np.float64)**2))) for v in residual],
            material_noise_mean_dn_by_source=[float(v.mean()) for v in residual],
            adjacent_material_noise_covariance_dn2=[float(np.mean(centered[i]*centered[i+1])) for i in range(N-1)],
            clipped_low_count=0 if name=='frozen' else int(np.sum(proposed<0)),
            clipped_high_count=0 if name=='frozen' else int(np.sum(proposed>1)),
            total_noise_samples=int(data.size))
    manifest=dict(execution_status='complete',schema=1,
        scope='Frozen photographed plane containing clothing/face/scene texture; not segmented cloth or film causality',
        original=dict(name=args.source.name,sha256=sha(args.source),frame=48,format=source_info),
        conversion=dict(pixel_format='gray16le',normalization='decoded_uint16 / 65535',
            transfer='No gamma linearization; source code-value luma retained',
            output_range='pc',output_matrix='bt709',output_primaries='bt709',
            color_transfer_tag='unspecified, matching absent source transfer tag',
            ffmpeg_sha256=sha(args.ffmpeg),ffprobe_sha256=sha(args.ffprobe)),
        size=[W,H],source_frames=N,truth_frames=2*N,source_rate=str(RATE),output_rate=str(2*RATE),
        origin=list(ORIGIN),displacement_px_per_source_frame=[-16,0],material_roi_at_t7=list(ROI),
        material_roi_x_formula='128 + 16*(7-t)',scored_output_indices=SELECT.tolist(),
        temporal_support_output_indices=[8,20],noise_seed=SEED,noise_generator='PCG64',numpy_version=np.__version__,
        truth=truth_info,plate_sha256=sha(root/'plate-gray16.npy'),conditions=condition_info,
        gates=GATES)
    write_json(root/'fixtures.json',manifest)
    print(json.dumps(dict(execution_status='complete',fixtures=str(root/'fixtures.json'),
                         sources=[str(root/c/'source.mkv') for c in condition_info])))
    return manifest


def score(args):
    root=args.root;destination=args.out or root/args.condition/'scores.json'
    write_json(destination,dict(execution_status='incomplete'))
    meta=json.loads((root/'fixtures.json').read_text())
    require(meta['execution_status']=='complete' and meta['source_frames']==N and meta['truth_frames']==2*N and
            meta['source_rate']==str(RATE) and meta['output_rate']==str(2*RATE) and
            meta['size']==[W,H] and meta['origin']==list(ORIGIN) and
            meta['displacement_px_per_source_frame']==[-16,0] and meta['noise_seed']==SEED and meta['gates']==GATES and
            meta['scored_output_indices']==SELECT.tolist() and meta['material_roi_at_t7']==list(ROI),
            'fixture manifest differs from registration')
    source_path=root/args.condition/'source.mkv';truth_path=root/'truth.mkv'
    require(sha(source_path)==meta['conditions'][args.condition]['source']['sha256'],'fixture source hash changed')
    require(sha(truth_path)==meta['truth']['sha256'],'fixture truth hash changed')
    src=decode(source_path,args.ffmpeg,frames=N);truth=decode(truth_path,args.ffmpeg,frames=2*N)
    source_aligned=align(src,1);clean=align(truth,.5)[:2*N-1]
    require(np.array_equal(clean,np.repeat(clean[:1],len(clean),axis=0)),'material truth not constant')
    cpu=np.empty_like(clean);cpu[::2]=source_aligned;cpu[1::2]=.5*(source_aligned[:-1]+source_aligned[1:])
    specs={}
    for spec in args.renders:
        label,path=spec.split('=',1)
        require(label and label not in specs and label.replace('-','').replace('_','').isalnum(),'invalid/duplicate label')
        specs[label]=Path(path)
    require(set(specs)==set(SHADERS),'exactly the registered oracle and estimate labels are required')
    loaded={};instruments={};violations=[]
    for label,path in specs.items():
        side=json.loads(path.with_suffix('.json').read_text())
        certify_sidecar(label,side,sha(source_path),sha(path))
        info=probe(path,args.ffprobe)
        require(int(info['nb_read_frames'])==2*N and (info['width'],info['height'])==(W,H),'decoded output geometry/count mismatch')
        require(abs(float(Fraction(info['r_frame_rate'])/(2*RATE))-1)<1e-5,'output rate mismatch')
        a=decode(path,args.ffmpeg,frames=2*N);aligned=align(a,.5)[:2*N-1];loaded[label]=aligned
        retained=[]
        for j in SOURCE_GATE:
            error=(a[j].astype(np.float32)-src[j//2].astype(np.float32))/65535
            mae=float(np.abs(error).mean()*255)
            retained.append(dict(output_index=int(j),source_index=int(j//2),full_frame_mae_dn=mae,
                                 material_roi_mae_dn=float(np.abs(core(aligned[j]-source_aligned[j//2])).mean()*255)))
            if mae>.5:violations.append(f'{label}: source output {j} MAE exceeds 0.5 DN')
        instruments[label]=dict(shader_sha256=side['shader_sha256'],output_sha256=side['output_sha256'],
                               output_format=info,retained_source_checks=retained)
    oracle_checks=[]
    for j in SELECT[SELECT%2==1]:
        error=core(loaded['oracle'][j]-cpu[j]);rms=rms_dn(error)
        oracle_checks.append(dict(output_index=int(j),rms_dn=rms,mae_dn=float(np.abs(error).mean()*255)))
        if rms>1:violations.append(f'oracle: midpoint {j} RMS exceeds 1.0 DN')
    kernel=np.exp(-np.arange(-8,9,dtype=float)**2/8);kernel/=kernel.sum()
    sigma=meta['conditions'][args.condition]['noise_sigma_dn']
    results={}
    for label,a in loaded.items():
        results[label]=dict(against_clean=measurements(a,clean),against_cpu_blend=measurements(a,cpu),
                            against_gpu_oracle=measurements(a,loaded['oracle']),shape=shape_features(a,clean))
    report=dict(execution_status='complete',instrument_gate_pass=not violations,
        field_attribution_valid=not violations,violations=violations,condition=args.condition,
        registered_shader_sha256=SHADERS,
        scope=meta['scope'],scored_output_indices=SELECT.tolist(),material_roi_at_t7=list(ROI),
        source_sha256=sha(source_path),truth_sha256=sha(truth_path),
        gates=meta['gates'],renderer_instruments=instruments,oracle_midpoint_cpu_blend_checks=oracle_checks,
        ideal_unclipped_noise=dict(source_rms_dn=sigma,midpoint_rms_dn=sigma/np.sqrt(2),
             inserted_centered_curvature_rms_dn=0,source_centered_curvature_rms_dn=sigma*np.sqrt(1.5),
             sigma2_source_rms_dn=sigma*float(np.sum(kernel*kernel)),
             sigma2_midpoint_rms_dn=sigma*float(np.sum(kernel*kernel))/np.sqrt(2)),
        realized_noise=meta['conditions'][args.condition],
        realized_cpu_blend_against_clean=measurements(cpu,clean),
        realized_cpu_blend_shape=shape_features(cpu,clean),renders=results,
        interpretation=['The clean plane includes frozen original grain as material texture.',
             'Added source grain is known; no new midpoint grain realization is treated as predictable truth.',
             'Compare estimated output minus GPU oracle only conditional on every instrument gate.',
             'All-output and inserted-only differences have different time steps; both are reported.',
             'Gate limits are acceptance bounds, not measured precision or film-causality evidence.'])
    write_json(destination,report)
    print(json.dumps(dict(output=str(destination),instrument_gate_pass=not violations,violations=violations)))
    return report


def controls(args):
    destination=args.out or args.root/'cpu-controls.json'
    write_json(destination,dict(execution_status='incomplete'))
    truth=decode(args.root/'truth.mkv',args.ffmpeg,frames=2*N)
    clean=align(truth,.5)[:2*N-1]
    require(np.array_equal(clean,np.repeat(clean[:1],len(clean),axis=0)),'registered material is not stationary')
    results={}
    for condition in ('frozen','grain'):
        src=decode(args.root/condition/'source.mkv',args.ffmpeg,frames=N)
        aligned=align(src,1)
        cpu=np.empty_like(clean);cpu[::2]=aligned;cpu[1::2]=.5*(aligned[:-1]+aligned[1:])
        value=measurements(cpu,clean);features=shape_features(cpu,clean)
        require(features['raw']['source_to_inserted_chord_rms_dn']<1e-5,'exact CPU blend has a nonzero midpoint chord')
        if condition=='frozen':
            require(value['raw']['parity']['all']['rms_dn']==0,'frozen oracle is not exact')
        results[condition]=dict(raw_clean_error=value['raw']['parity'],
            sigma2_clean_error=value['sigma2']['parity'],
            raw_midpoint_chord_rms_dn=features['raw']['source_to_inserted_chord_rms_dn'])
    repeated=clean.copy()
    pattern=np.sin(np.arange(clean.shape[2])[None,:]*2*np.pi/32)/255
    repeated[1::2]=np.clip(repeated[1::2]+pattern,0,1)
    proof=measurements(repeated,clean)['raw']
    require(proof['inserted_only_error_first_difference_rms_dn']==0 and
            proof['all_output_error_first_difference_rms_dn']>.5,'both-parity control failed')
    valid=dict(execution_status='complete',source_sha256='1'*64,output_sha256='2'*64,
               shader_sha256=SHADERS['estimate'],source_frames=N,output_frames=2*N,width=W,height=H,
               input_rate=str(RATE),rate=str(2*RATE))
    certify_sidecar('estimate',valid,'1'*64,'2'*64)
    impostor={**valid,'shader_sha256':SHADERS['oracle']}
    try:
        certify_sidecar('estimate',impostor,'1'*64,'2'*64)
    except ValueError as error:
        require('registered shader hash mismatch' in str(error),'wrong shader rejected for unexpected reason')
    else:
        raise AssertionError('oracle passed as estimator was falsely certified')
    report=dict(execution_status='complete',status='pass',scope='CPU fixture/measurement/certification controls only',
                exact_material_stationarity=True,conditions=results,
                repeated_midpoint_error=dict(inserted_only_change_dn=proof['inserted_only_error_first_difference_rms_dn'],
                                             all_output_change_dn=proof['all_output_error_first_difference_rms_dn']),
                oracle_as_estimate_refused=True,source_alignment_gate_outputs=SOURCE_GATE.tolist())
    write_json(destination,report);print(json.dumps(report,indent=2));return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--ffmpeg',default=str(Path.home()/'np-build/ffmpeg/ffmpeg'))
    p.add_argument('--ffprobe',default=str(Path.home()/'np-build/ffmpeg/ffprobe'))
    sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('source',type=Path);prep.add_argument('out',type=Path)
    scor=sub.add_parser('score');scor.add_argument('root',type=Path);scor.add_argument('condition',choices=['frozen','grain'])
    scor.add_argument('renders',nargs='+');scor.add_argument('--out',type=Path)
    ctrl=sub.add_parser('controls');ctrl.add_argument('root',type=Path);ctrl.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    return {'prepare':prepare,'score':score,'controls':controls}[args.command](args)


if __name__=='__main__':main()
