#!/usr/bin/env python3
"""Calibrate fielddump.py before believing it (the field-read rule), 2026-11-18.

    calibrate.py <shader.glsl> <out-dir> [--ffmpeg PATH]

Four checks, PASS or FAIL each, exit 1 on any FAIL:
  path      a copy of the shader whose final pass writes the constant (+7, +2) px through fielddump's encoding must
            read back within 0.01 px: the read path alone, with no estimator in it;
  control   the same constant read through libplacebo's default 4:2:0 output must MISS by more than 1 px (the
            failure the --out-format switch exists for: it read (+3.5, +4.5));
  still     M1's noise square, not moving: the field must read exactly zero (within one code, 0.004 px);
  speed     M1's noise square at 384 px/s (16.016 px a source frame at 24000/1001): inside the square the median
            must read within 0.5 px of the truth and the background exactly zero.

What the first version taught (kept here so it is not met twice): a rigid translation of a real film frame read
(+6.75, +1.00) and (+6.13, +1.12) for a true (+7, +2), in blotches. The read path was exact (the constant check);
the blotches sit on flat regions (a dark coat, hangar shadow), where every vector matches and High's magnitude
prior sends the tie to zero. A real frame is therefore not a calibration of the speed; a textured square is.
High's speed on M1 reads 15.75 for 16.02, 0.27 px short (a bias toward zero, recorded, not chased here).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent.parent
ENV = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
AT = '    vec4 warped = mix(warped_a, warped_b, mix_t);\n'


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, **kw)
    if r.returncode:
        sys.exit(f'FAILED: {" ".join(map(str, cmd))[:300]}\n{r.stderr.decode(errors="replace")[-1500:]}')
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shader'); ap.add_argument('out', type=Path)
    ap.add_argument('--ffmpeg', default=str(Path.home() / 'np-scratch-int/n-frame/np-build/ffmpeg/ffmpeg'))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    fails = 0

    def check(ok, msg):
        nonlocal fails
        print(('PASS  ' if ok else 'FAIL  ') + msg, flush=True)
        fails += 0 if ok else 1

    scene = run(['bash', '-c', 'source ./scenes.sh >/dev/null 2>&1; scene M1_noise_large 24'], cwd=TESTS).decode().strip()
    assert 'r=24:d=1' in scene, scene
    moving = scene.replace('r=24:d=1', 'r=24000/1001:d=2')
    still = moving.replace('X-(384*T)', 'X-(384*0.5)').replace('min((384*T)+300', 'min((384*0.5)+300').replace('max((384*T)', 'max((384*0.5)')
    assert still != moving and '384*T' not in still, 'the still edit did not take'
    for name, s in (('m1', moving), ('m1still', still)):
        run([a.ffmpeg, '-nostdin', '-v', 'error', '-y', '-f', 'lavfi', '-i', s, '-c:v', 'ffv1', '-level', '3',
             '-pix_fmt', 'yuv420p', str(a.out / f'{name}.mkv')])

    text = Path(a.shader).read_text()
    assert text.count(AT) == 1
    const = a.out / 'const.glsl'
    const.write_text(text.replace(AT, '    return vec4(0.5 + 7.0 / 256.0, 0.5 + 2.0 / 256.0, 0.3, 1.0);\n' + AT))
    for fmt, want_exact in (('rgb48le', True), ('yuv420p', False)):
        vf = (f'settb=expr=1/48000,setpts=N*2002,libplacebo=fps=48000/1001:frame_mixer=custom_n:custom_shader_path={const}'
              f':dithering=none:format={fmt},format=rgb48le')
        raw = run([a.ffmpeg, '-nostdin', '-v', 'error', '-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk',
                   '-i', str(a.out / 'm1.mkv'), '-vf', vf, '-f', 'rawvideo', '-'], env=ENV)
        f = np.frombuffer(raw, '<u2').reshape(-1, 720, 1280, 3)[21].astype(np.float64) / 65535
        x, y = (f[..., 0].mean() - 0.5) * 256, (f[..., 1].mean() - 0.5) * 256
        miss = max(abs(x - 7), abs(y - 2))
        if want_exact:
            check(miss < 0.01, f'path: a written (+7, +2) reads ({x:+.4f}, {y:+.4f}) through rgb48le')
        else:
            check(miss > 1.0, f'control: through libplacebo\'s 4:2:0 output it reads ({x:+.3f}, {y:+.3f}) (must miss)')

    for name in ('m1still', 'm1'):
        run([sys.executable, str(HERE / 'fielddump.py'), a.shader, str(a.out / f'{name}.mkv'), str(a.out / name),
             '--only', 'flow', '--keep', '4:12', '--ffmpeg', a.ffmpeg])
    s = np.load(a.out / 'm1still' / 'flow.npy').astype(np.float32)
    check(np.abs(s[..., :2]).max() < 0.004, f'still: max |flow| {np.abs(s[..., :2]).max():.4f} px over the whole frame, {s.shape[0]} pairs')
    m = np.load(a.out / 'm1' / 'flow.npy').astype(np.float32)
    meds, bgs = [], []
    for i, k in enumerate(range(4, 13)):
        x0 = int(16.016 * k) // 2 + 20
        q = m[i, 125:235, x0:x0 + 110, :2]
        meds.append(np.median(q.reshape(-1, 2), axis=0))
        bgs.append(np.abs(m[i, 300:, :, :2]).max())
    meds = np.array(meds)
    check(np.all(np.abs(meds[:, 0] - 16.016) < 0.5) and np.all(np.abs(meds[:, 1]) < 0.05),
          f'speed: inside the square x {meds[:, 0].min():.3f}..{meds[:, 0].max():.3f}, y {meds[:, 1].min():+.3f}..{meds[:, 1].max():+.3f} (truth +16.016, 0)')
    check(max(bgs) < 0.004, f'speed: background below the square max |flow| {max(bgs):.4f} px')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
