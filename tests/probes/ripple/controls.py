#!/usr/bin/env python3
"""Runnable CPU counterfactuals for temporal.py and withheld.py; no GPU.

  controls.py --out /tmp/ripple-measurement-controls.json

Requires NumPy/SciPy and FFmpeg/ffprobe with FFV1. Temporary tiny videos are
deleted after checking valid truth, wrong counts, retained corruption, and stale
report protection. The controls do not establish a real-footage cause or fix.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np
from scipy.ndimage import gaussian_filter, shift

import temporal
import withheld


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def tracking_controls():
    settings=SimpleNamespace(max_shift=12,min_texture_dn=.75,ambiguity_radius=4,
                             min_corr=.65,min_peak_gap=.01,max_fit_dn=10)
    rng=np.random.default_rng(2206)
    a=gaussian_filter(rng.normal(size=(180,180)),2)
    a=(.4+.15*a/a.std()).astype(np.float32)
    b=shift(a,(-1.7,2.3),order=1,mode='reflect')
    fit=temporal.translation(a,b,np.array([40.,40.]),(96,96),settings)
    error=float(np.max(np.abs(np.asarray(fit['shift'])-[2.3,-1.7])))
    check(fit['valid'] and error<.08,'subpixel translation control failed')
    flat=np.full_like(a,.5)
    flat_fit=temporal.translation(flat,flat,np.array([40.,40.]),(96,96),settings)
    y,x=np.mgrid[:180,:180]
    bars=(.5+.1*np.sin(x*2*np.pi/12)).astype(np.float32)
    bar_fit=temporal.translation(bars,bars,np.array([40.,40.]),(96,96),settings)
    check(not flat_fit['valid'] and 'low_texture' in flat_fit['reasons'],'flat patch silently tracked')
    check(not bar_fit['valid'],'periodic/aperture-ambiguous patch silently tracked')
    return dict(known_shift=[2.3,-1.7], measured_shift=fit['shift'], max_error_px=error,
                flat_rejection=flat_fit['reasons'], periodic_rejection=bar_fit['reasons']),a[40:136,40:136]


def temporal_controls(texture):
    source=np.repeat(texture[None],8,axis=0)
    truth=np.repeat(texture[None],15,axis=0)
    base,_=temporal.metrics(truth,source,12,32)
    check(base['2']['midpoint_departure_change']['all']['rms_dn']==0,'unchanged truth has temporal error')
    pattern=np.sin(np.arange(96)[None,:]*2*np.pi/32)/255

    alternating=truth.copy()
    for i in range(7):
        alternating[2*i+1]+=(-1)**i*pattern
    score,_=temporal.metrics(alternating,source,12,32)
    synthesized_error=alternating[1::2]-truth[1::2]
    old_scalar=float(np.mean(np.abs(np.diff(np.abs(synthesized_error).mean(axis=(1,2)))))*255)
    pixel_change=score['2']['midpoint_departure_change']['all']['rms_dn']
    check(old_scalar<1e-4 and pixel_change>1,'constant-total-error ripple was missed')

    repeated=truth.copy(); repeated[1::2]+=pattern
    repeated_error=repeated-truth
    same_midpoint_change=float(np.sqrt(np.mean(np.diff(repeated_error[1::2],axis=0)**2))*255)
    all_output_change=float(np.sqrt(np.mean(np.diff(repeated_error,axis=0)**2))*255)
    parity,_=temporal.metrics(repeated,source,12,32)
    check(same_midpoint_change==0 and all_output_change>.5,'both-parity blind-spot control failed')
    check(parity['2']['midpoint_departure_change']['all']['rms_dn']<1e-5,
          'identical midpoint errors unexpectedly differ')
    check(parity['2']['inserted_center']['spatially_nonuniform']['rms_dn']>1 and
          parity['2']['retained_center']['spatially_nonuniform']['rms_dn']>1,
          'all-output curvature missed retained/inserted alternation')
    return dict(unchanged_control_zero=True,
                alternating_sign_ripple=dict(old_scalar_mae_change_dn=old_scalar,
                                             sigma2_pixelwise_midpoint_error_change_dn=pixel_change),
                repeated_midpoint_error=dict(synthesized_only_error_change_dn=same_midpoint_change,
                                             all_output_error_change_dn=all_output_change,
                                             sigma2_insertion_curvature_dn=parity['2']['inserted_center']['spatially_nonuniform']['rms_dn'],
                                             sigma2_retained_curvature_dn=parity['2']['retained_center']['spatially_nonuniform']['rms_dn']))


def truth_controls():
    y,x=np.mgrid[:52,:52]
    a=np.repeat(((x+y)/200+.1)[None],7,axis=0).astype(np.float32)
    rows=[(i,i) for i in (1,3,5)]
    zero,_=withheld.score(a,a.copy(),rows,(10,10,32,32),16,(100,200))
    check(all(v['mse']==0 and v['psnr_db']==160 for v in zero['summary'].values()),'exact truth scored nonzero')
    b=a.copy(); b[3,18:22,18:22]+=.1
    defect,_=withheld.score(a,b,rows,(10,10,32,32),16,(100,200))
    raw=defect['summary']['raw']
    check(raw['worst_tile']['source_frame']==3 and raw['worst_1pct_rms_dn']>raw['rms_dn'],
          'localized fault or worst frame was missed')
    check(defect['summary']['sigma1']['gradient_rms_dn_per_px']>0,'localized fault gradient missed')
    bright,_=withheld.score(a,a+.05,rows,(10,10,32,32),16,(100,200))
    check(bright['summary']['sigma1']['gradient_rms_dn_per_px']<1e-4 and
          abs(bright['summary']['raw']['rms_dn']-12.75)<1e-4,'brightness/gradient separation failed')
    return dict(exact_truth_zero=True, localized_fault_summary=defect['summary'],
                uniform_brightness_rms_dn=bright['summary']['raw']['rms_dn'],
                uniform_brightness_gradient_dn_per_px=bright['summary']['sigma1']['gradient_rms_dn_per_px'])


def tiny_video_controls(ffmpeg,ffprobe):
    with TemporaryDirectory(prefix='ripple-measurement-control-') as td:
        root=Path(td)
        y,x=np.mgrid[:52,:52]
        source_array=np.stack([.2+(x+y)/300+.01*i for i in range(7)]).astype(np.float32)
        def encode(name,a):
            path=root/name
            subprocess.run([ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pixel_format','gray16le',
                            '-video_size','52x52','-framerate','24','-i','pipe:0','-c:v','ffv1',str(path)],
                           input=np.rint(a*65535).astype('<u2').tobytes(),check=True,capture_output=True)
            return path
        source=encode('source.mkv',source_array)
        good=encode('correct.mkv',np.concatenate([source_array,source_array[-1:]]))
        wrong_count=encode('wrong-count.mkv',source_array)
        bad=source_array.copy(); bad[::2]+=.05
        wrong_alignment=encode('wrong-alignment.mkv',np.concatenate([bad,bad[-1:]]))
        def args(path):
            return [str(source),str(path),'--crop','10:10:32:32','--first-frame','1','--last-frame','5',
                    '--ffmpeg',ffmpeg,'--ffprobe',ffprobe,'--out',str(root/'scores')]
        with contextlib.redirect_stdout(io.StringIO()):
            good_result=withheld.main(args(good))
        check(good_result['scored_original_odd_frames']==[1,3,5] and
              good_result['renders']['correct']['summary']['raw']['mse']==0,'tiny truth video failed')
        for bad_path,expected in [(wrong_count,'expected 8 frames'),(wrong_alignment,'retained-source alignment failed')]:
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    withheld.main(args(bad_path))
            except ValueError as error:
                check(expected in str(error),'invalid video failed for an unexpected reason')
            else:
                raise AssertionError('invalid video silently scored')
            state=json.loads((root/'scores/withheld.json').read_text())
            check(state['execution_status']=='incomplete','failed rerun retained a stale complete report')
        return dict(source_frames=7,required_render_frames=8,scored_odd_frames=[1,3,5],
                    exact_reconstruction_zero=True,wrong_count_rejected=True,
                    corrupted_retained_rejected=True,failed_rerun_incomplete=True)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--ffmpeg',default=str(Path.home()/'np-build/ffmpeg/ffmpeg'))
    p.add_argument('--ffprobe',default=str(Path.home()/'np-build/ffmpeg/ffprobe'))
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text('{"status":"incomplete"}\n')
    tracking,texture=tracking_controls()
    report=dict(status='pass',scope='CPU measurement counterfactuals only; not a film-cause or quality verdict',
                tracking=tracking,temporal=temporal_controls(texture),withheld=truth_controls(),
                tiny_video=tiny_video_controls(args.ffmpeg,args.ffprobe))
    result=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if args.out:
        args.out.write_text(result)
    print(result,end='')
    return report


if __name__=='__main__':
    main()
