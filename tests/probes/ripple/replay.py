#!/usr/bin/env python3
"""Calibrate field decoding and replay vote-off native midpoint warp on selected full-resolution fields.

replay.py ROOT --ffmpeg PATH
ROOT is this block's scratch layout; garment rectangle is an exploratory fixed probe, not a segmentation mask.
"""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy.ndimage import map_coordinates
from render import sha256,incomplete


def read(ff,path,frames,crop):
    x,y,w,h=crop
    filters='select='+ '+'.join(f'eq(n\\,{n})' for n in frames)+f',crop={w}:{h}:{x}:{y}'
    r=subprocess.run([ff,'-v','error','-i',str(path),'-vf',filters,'-fps_mode','passthrough','-pix_fmt','gray16le','-f','rawvideo','-'],
                     capture_output=True,check=True)
    a=np.frombuffer(r.stdout,'<u2');assert a.size==len(frames)*w*h
    return a.reshape(len(frames),h,w).astype(np.float32)/65535


def sm(lo,hi,v):
    t=np.clip((v-lo)/(hi-lo),0,1);return t*t*(3-2*t)


def load_dump(root, stem):
    meta=json.loads((root/(stem+'.json')).read_text())
    if meta.get('execution_status') not in (None,'complete'):
        raise ValueError(f'{stem}: diagnostic dump is incomplete')
    frames=meta['frames']
    if not frames or any(type(k) is not int or k<0 for k in frames) or frames!=sorted(set(frames)):
        raise ValueError(f'{stem}: invalid diagnostic frame indices')
    path=root/(stem+'.npy')
    if 'array_sha256' in meta and sha256(path)!=meta['array_sha256']:
        raise ValueError(f'{stem}: array does not match its recorded hash')
    array=np.load(path,allow_pickle=False)
    expected=(len(frames),meta['height'],meta['width'],3)
    if array.shape!=expected or not np.issubdtype(array.dtype,np.floating) or not np.isfinite(array).all():
        raise ValueError(f'{stem}: expected finite float array {expected}, got {array.shape}/{array.dtype}')
    if np.min(array)<0 or np.max(array)>1:
        raise ValueError(f'{stem}: diagnostic RGB encoding outside [0,1]')
    return meta,array


def require_matching_dumps(metas):
    first=metas[0]
    for key in ('frames','crop','width','height'):
        if any(m[key]!=first[key] for m in metas[1:]):
            raise ValueError(f'diagnostic frame/crop mismatch: {key}')
    # Historical dumps have no source hashes/rate record. Do not quietly mix them
    # with freshly recorded provenance or claim that missing provenance was checked.
    for key in ('source_sha256','input_rate','rate','source_frames'):
        if any(key in m for m in metas) and (not all(key in m for m in metas) or any(m[key]!=first[key] for m in metas[1:])):
            raise ValueError(f'diagnostic source provenance mismatch: {key}')
    if any(k%2!=1 for k in first['frames']):
        raise ValueError('replay requires odd native-2x midpoint indices')
    if first['crop'] is None or len(first['crop'])!=4 or first['crop'][2:]!=[first['width'],first['height']]:
        raise ValueError('replay requires an explicit, dimension-matched crop')


def load_render_record(path):
    record=json.loads(path.with_suffix('.json').read_text())
    if record.get('execution_status') not in (None,'complete'):
        raise ValueError(f'{path.name}: render is incomplete')
    if record['output_frames']!=2*record['source_frames']:
        raise ValueError(f'{path.name}: render count record is inconsistent')
    if 'output_sha256' in record and sha256(path)!=record['output_sha256']:
        raise ValueError(f'{path.name}: media does not match its recorded hash')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--ffmpeg',required=True)
    args=p.parse_args();r=args.root
    incomplete(r/'replay.json',scope='native midpoint replay; validation has not completed')
    cal_static,static_array=load_dump(r,'cal-static')
    cal_translation,known_array=load_dump(r,'cal-translation')
    static=(static_array[...,:2]-.5)*256
    if known_array.shape[1]<210 or known_array.shape[2]<340:
        raise ValueError('translation calibration lacks the registered interior')
    known=(known_array[0,145:210,275:340,:2]-.5)*256
    assert np.max(np.abs(static))<.02
    med=np.median(known,axis=(0,1));assert abs(med[0]-32)<2 and abs(med[1])<1
    meta,field_array=load_dump(r,'shirt-field')
    qmeta,quarter_array=load_dump(r,'shirt-quarter')
    smeta,sup=load_dump(r,'shirt-support')
    require_matching_dumps([meta,qmeta,smeta]);frames=meta['frames'];crop=meta['crop']
    if any(np.min(a[...,:2])<=0 or np.max(a[...,:2])>=1 for a in (field_array,quarter_array)):
        raise ValueError('field encoding saturated; displacement/gradient attribution is invalid')
    if 'source_sha256' in meta and sha256(r/'shirt-source.mkv')!=meta['source_sha256']:
        raise ValueError('shirt source differs from the diagnostic source')
    sourceframes=sorted({k//2 for k in frames}|{k//2+1 for k in frames})
    source=dict(zip(sourceframes,read(args.ffmpeg,r/'shirt-source.mkv',sourceframes,crop)))
    names=('high','prev','vote-nearest','prev-no-fallback','linear')
    render_records=[load_render_record(r/'shirt'/f'{name}.mkv') for name in names]
    images={name:read(args.ffmpeg,r/'shirt'/f'{name}.mkv',frames,crop) for name in names}
    f=(field_array[...,:2]-.5)*256
    q=(quarter_array[...,:2]-.5)*256
    h,w=f.shape[1:3];yy,xx=np.mgrid[:h,:w].astype(np.float32)
    sample=lambda im,x,y:map_coordinates(im,[y,x],order=1,mode='nearest')
    rows=[];probecrop=(440,450,140,140);x,y,pw,ph=probecrop;x-=crop[0];y-=crop[1]
    if min(h,w)<=128 or x<0 or y<0 or x+pw>w or y+ph>h:
        raise ValueError('registered probe/replay interior lies outside the diagnostic crop')
    roi=np.s_[y:y+ph,x:x+pw]
    for i,k in enumerate(frames):
        a,b=source[k//2],source[k//2+1];flow=f[i];fx,fy=flow[...,0],flow[...,1]
        wa=sample(a,xx-.5*fx,yy-.5*fy);wb=sample(b,xx+.5*fx,yy+.5*fy)
        u=(1-sm(.5,.7,sup[i,...,0]))*(1-sm(.4,.55,sup[i,...,1]))*(1-sm(.5,1,sup[i,...,2]))
        replay=(1-u)*.5*(wa+wb)+u*.5*(a+b)
        inside=np.s_[64:-64,64:-64]
        valid=(xx-.5*fx>=0)&(xx-.5*fx<=w-1)&(yy-.5*fy>=0)&(yy-.5*fy<=h-1)\
             &(xx+.5*fx>=0)&(xx+.5*fx<=w-1)&(yy+.5*fy>=0)&(yy+.5*fy<=h-1)
        if not valid[inside].all():
            raise ValueError(f'{k}: replay interior reaches outside decoded source support')
        error=float(np.sqrt(np.mean((replay[inside]-images['prev'][i][inside])**2))*255)
        assert error<1.0,(k,'warp replay failed',error)
        rflow=flow[roi];dyx,dxx=np.gradient(fx);dyy,dxy=np.gradient(fy)
        ja=(1-.5*dxx)*(1-.5*dyy)-.25*dyx*dxy
        jb=(1+.5*dxx)*(1+.5*dyy)-.25*dyx*dxy
        stats={}
        for name in ('high','vote-nearest','prev-no-fallback','linear'):
            dif=(images[name][i]-images['prev'][i])[roi]*255
            stats[name]=dict(rms_difference_dn=float(np.sqrt(np.mean(dif*dif))),max_difference_dn=float(np.max(np.abs(dif))))
        rows.append(dict(output_frame=k,source_pair=[k//2,k//2+1],replay_rms_dn=error,
            flow_x_quantiles=np.quantile(rflow[...,0],[0,.1,.5,.9,1]).tolist(),flow_y_quantiles=np.quantile(rflow[...,1],[0,.1,.5,.9,1]).tolist(),
            gradient_quantiles=np.quantile(np.sqrt(dxx*dxx+dyx*dyx+dxy*dxy+dyy*dyy)[roi],[.5,.9,.99]).tolist(),
            orientation_reversal_fraction_a=float(np.mean(ja[roi]<0)),orientation_reversal_fraction_b=float(np.mean(jb[roi]<0)),
            fallback_mean=float(np.mean(u[roi])),fallback_max=float(np.max(u[roi])),differences_from_previous_high=stats,
            quarter_to_half_rms_px=float(np.sqrt(np.mean((q[i][roi]-rflow)**2)))))
        np.savez_compressed(r/f'shirt-replay-{k}.npz',replay=replay,warped=.5*(wa+wb),fallback=u,
                            endpoint_difference=wa-wb,det_a=ja,det_b=jb)
    report=dict(execution_status='complete',scope='Exploratory fixed probe rectangle; not ground-truth flow or clothing segmentation.',
                diagnostic_provenance='legacy_unmarked' if any(m.get('execution_status') is None for m in (meta,qmeta,smeta,cal_static,cal_translation,*render_records)) else 'complete_markers_checked',
                probe_crop=probecrop,static_abs_max_px=float(np.max(np.abs(static))),known_translation_median_px=med.tolist(),rows=rows)
    (r/'replay.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':main()
