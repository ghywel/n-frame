#!/usr/bin/env python3
"""The pre-registered test scenes of PLAN.md, made exactly in numpy (truth known), each as <dir>/ref.mkv (full rate) and
<dir>/half.mkv (every second frame), 10-bit FFV1.

    scenes.py <still-tv.mkv> <still-cartoon.mkv> <out>

  fade-<shot>-<g>   a still picture under a pure fade: frame k = A * g**(k/2), so each decimated pair brightens by g
                    (g = 1.03, 1.06, 1.12); no motion anywhere; the start darkened so that the last frame's brightest pixel is 0.95 (no clipping)
  pan-<g>           the TV still's textured toaster panning +6 px per decimated pair (+3 a full-rate frame), cropped
                    from a wider canvas (no wrap), under the same fades (g = 1.00 is the pan's own control)
  ramp              a smooth horizontal luma ramp, 0.15 -> 0.85 over the frame, panning +4 px per decimated pair, no
                    fade: translation and an additive change are the same image change here (GPT, prospect RESULTS.md)
"""
import os
import subprocess
import sys

import numpy as np

FF = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
N = 24


def still(path):
    r = subprocess.run([FF, '-v', 'error', '-i', path, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-'],
                       capture_output=True)
    w, h = map(int, subprocess.run([os.path.join(os.path.dirname(FF), 'ffprobe'), '-v', 'error', '-select_streams', 'v:0',
                                    '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path],
                                   capture_output=True, text=True).stdout.split(','))
    return np.frombuffer(r.stdout, '<u2').reshape(h, w, 3).astype(float) / 65535


def write(d, frames, rate, half):
    os.makedirs(d, exist_ok=True); h, w = frames[0].shape[:2]
    for name, fs, r in (('ref', frames, rate), ('half', frames[::2], half)):
        raw = os.path.join(d, name + '.rgb48')
        np.stack([np.rint(np.clip(f, 0, 1) * 65535).astype('<u2') for f in fs]).tofile(raw)
        subprocess.run([FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-video_size', f'{w}x{h}',
                        '-framerate', r, '-i', raw, '-c:v', 'ffv1', '-pix_fmt', 'yuv420p10le', os.path.join(d, name + '.mkv')],
                       check=True)
        os.remove(raw)
    open(os.path.join(d, 'scene.txt'), 'w').write(f'{w} {h} {rate} {half}\n')


def main():
    tv, cartoon, out = still(sys.argv[1]), still(sys.argv[2]), sys.argv[3]
    for shot, A, rate, half in (('tv', tv, '25', '25/2'), ('cartoon', cartoon, '24000/1001', '12000/1001')):
        for g in (1.03, 1.06, 1.12):
            s = 0.95 / (A.max() * g ** ((N - 1) / 2))
            write(f'{out}/fade-{shot}-{g:.2f}', [A * s * g ** (k / 2) for k in range(N)], rate, half)
    H, W = tv.shape[:2]; w = W - 3 * N
    for g in (1.00, 1.03, 1.06, 1.12):
        s = 0.95 / (tv.max() * g ** ((N - 1) / 2))
        write(f'{out}/pan-{g:.2f}', [tv[:, 3 * N - 3 * k: 3 * N - 3 * k + w] * s * g ** (k / 2) for k in range(N)], '25', '25/2')
    x = np.arange(1280 + 2 * N, dtype=float)
    ramp = .15 + .70 * x / x[-1]
    write(f'{out}/ramp', [np.broadcast_to(ramp[2 * N - 2 * k: 2 * N - 2 * k + 1280][None, :, None], (720, 1280, 3)).copy()
                          for k in range(N)], '24000/1001', '12000/1001')
    print('scenes written under', out)


if __name__ == '__main__':
    main()
