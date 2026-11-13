#!/usr/bin/env python3
"""Bounded 24->60 stress suite. Inputs/truth rendered at exact continuous times.

run.py OUT --ffmpeg PATH --shaders high=FILE linear=linear [--cases NAME ...]
Reject failed/fallback renders, wrong lengths and retained-source misalignment.
Scores interior synthesized frames only, preserving regional and feature errors.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np
import scenes

ENV = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0',
           MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')


def call(cmd, log, gpu=False):
    t = time.monotonic()
    r = subprocess.run(cmd, capture_output=True, env=ENV)
    log.write_bytes(r.stderr)
    err = r.stderr.decode(errors='replace').lower()
    if r.returncode or (gpu and (err.count('hook skipped') > 2 or any(x in err for x in ('compile status', 'disabling', 'failed to')))):
        raise RuntimeError(f'{log}: failed process {r.returncode}: {err[-2000:]}')
    return r.stdout, time.monotonic()-t


def read(ff, path, count):
    data, _ = call([ff, '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'gray16le', '-'],
                   path.with_suffix('.decode.log'))
    a = np.frombuffer(data, '<u2')
    assert a.size == count*scenes.W*scenes.H, (path, a.size, count)
    return a.reshape(count, scenes.H, scenes.W).astype(np.float32)/65535


def prepare(ff, case, d):
    n = scenes.SOURCE_FRAMES
    for stem, count, step, rate in [('source', n, 1., 24), ('truth', n*5//2, .4, 60)]:
        raw = d/f'{stem}.gray16'
        with raw.open('wb') as f:
            for k in range(count):
                a, _, _ = scenes.render(case, k*step)
                assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
                f.write(np.rint(a*65535).astype('<u2').tobytes())
        call([ff, '-nostdin', '-y', '-v', 'warning', '-f', 'rawvideo', '-pixel_format', 'gray16le',
              '-video_size', f'{scenes.W}x{scenes.H}', '-framerate', str(rate), '-i', str(raw),
              '-vf', 'format=yuv444p16le', '-c:v', 'ffv1', str(d/f'{stem}.mkv')], d/f'{stem}.encode.log')
        raw.unlink()


def psnr(mse):
    return float(-10*np.log10(max(float(mse), 1e-16)))


def measure(case, im, truth):
    n = len(truth)
    retained = [k for k in range(5, n-5) if k % 5 == 0]
    alignment = max(float(np.sqrt(np.mean((im[k]-truth[k])**2))*255) for k in retained)
    assert alignment < 2.55, f'{case}: source misalignment {alignment} DN'
    rows=[]
    for k in range(5, n-5):
        if k % 5 == 0: continue
        _, roi, features = scenes.render(case, k*.4)
        assert roi.any() and features.any()
        e=(im[k]-truth[k])**2
        region=e[roi]; feat=e[features]
        rows.append(dict(frame=k, phase=(k*.4)%1, mse=float(e.mean()), roi_mse=float(region.mean()),
                         feature_mse=float(feat.mean()), feature_bad_05=float(np.mean(feat > .05**2)),
                         roi_worst_1pct_mse=float(np.sort(region)[-max(1, len(region)//100):].mean())))
    assert rows
    return dict(frames=len(rows), retained_rms_dn=alignment,
                psnr=psnr(np.mean([r['mse'] for r in rows])),
                roi_psnr=psnr(np.mean([r['roi_mse'] for r in rows])),
                feature_psnr=psnr(np.mean([r['feature_mse'] for r in rows])),
                feature_bad_05=float(np.mean([r['feature_bad_05'] for r in rows])),
                roi_worst_1pct_rms_dn=float(np.sqrt(np.mean([r['roi_worst_1pct_mse'] for r in rows]))*255), rows=rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('out', type=Path)
    ap.add_argument('--ffmpeg', required=True); ap.add_argument('--shaders', nargs='+', required=True)
    ap.add_argument('--cases', nargs='+', default=None)
    ap.add_argument('--photo-patch', type=Path)
    args=ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    manifest={}; report={}
    scene_bytes=Path(scenes.__file__).read_bytes()+b'prep-yuv444p16-v1'
    if args.photo_patch:
        import photo
        photo.configure(args.photo_patch)
        original_render=scenes.render
        scenes.render=lambda name,t: photo.render(name,t) if name in photo.CASES else original_render(name,t)
        scenes.CASES.update(photo.CASES)
        scene_bytes+=Path(photo.__file__).read_bytes()+args.photo_patch.read_bytes()
    if args.cases is None: args.cases=list(scenes.CASES)
    scene_hash=hashlib.sha256(scene_bytes).hexdigest()
    for spec in args.shaders:
        label, path=spec.split('=', 1)
        assert label not in ('source', 'truth') and label not in manifest, 'Reserved/duplicate label'
        assert label.replace('-', '').replace('_', '').isalnum(), 'Unsafe label'
        manifest[label]=dict(path=path, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest() if path!='linear' else None)
    for case in args.cases:
        assert case in scenes.CASES
        d=args.out/case; d.mkdir(exist_ok=True)
        stamp=d/'scene.sha256'
        if not stamp.exists() or stamp.read_text()!=scene_hash:
            prepare(args.ffmpeg, case, d); stamp.write_text(scene_hash)
        truth=read(args.ffmpeg, d/'truth.mkv', scenes.SOURCE_FRAMES*5//2)
        rows={}
        for label, meta in manifest.items():
            target=d/f'{label}.mkv'
            sh=meta['path']
            mix='linear' if sh=='linear' else f'custom_n:custom_shader_path={Path(sh).resolve()}'
            _, seconds=call([args.ffmpeg, '-nostdin', '-y', '-v', 'warning', '-init_hw_device', 'vulkan=vk',
                            '-filter_hw_device', 'vk', '-i', str(d/'source.mkv'), '-vf',
                            f'settb=expr=1/120,setpts=N*5,libplacebo=fps=60:frame_mixer={mix}:dithering=none', '-c:v', 'ffv1',
                            '-pix_fmt', 'yuv444p16le', str(target)], d/f'{label}.render.log', gpu=True)
            im=read(args.ffmpeg, target, len(truth)); score=measure(case, im, truth)
            score.update(wall_seconds=seconds, shader_sha256=meta['sha256'])
            # A one-output shift must be visible on moving cases. Recorded, not used to tune a threshold.
            score['shift_control_mse']=float(np.mean((truth[6:-5]-truth[5:-6])**2))
            rows[label]=score
            (d/f'{label}.json').write_text(json.dumps(score,indent=2)+'\n')
            print(case, label, 'PSNR %.3f ROI %.3f feature %.3f bad %.4f worst1%% %.2fDN'%
                  (score['psnr'],score['roi_psnr'],score['feature_psnr'],score['feature_bad_05'],score['roi_worst_1pct_rms_dn']),flush=True)
        report[case]=rows
        (args.out/'summary.json').write_text(json.dumps(dict(scene_sha256=scene_hash, manifest=manifest, cases=report),indent=2)+'\n')


if __name__=='__main__': main()
