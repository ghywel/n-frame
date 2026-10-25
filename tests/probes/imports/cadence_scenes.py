#!/usr/bin/env python3
"""Import 2's synthetic scenes and scorer (IMPORTS-TO-INTERPOLATION.md, LOCAL_CADENCE, pre-registered at f715658).

    cadence_scenes.py make  <out>                       the three scenes: <out>/<scene>/src24.mkv and truth60.mkv
    cadence_scenes.py score <out> name=shader|linear ...  24 -> 60 through each, scored against the exact truth

A textured background (an analytic sum of sines) pans +3 px a source frame, and a textured disc (radius 80, its own
analytic texture) moves +8 px a source frame. Both textures are functions of continuous position, so every frame, at
any fractional time, is exact. Scenes:
  mixed   background on ONES, disc drawn ON TWOS (its drawing advances 16 px every second source frame, held between)
  ones    both on ones (the control: nothing is ever held)
  twos    both on twos (the whole frame held every second frame: what the existing global cadence branch handles)
  still   the disc on ones over a STILL background (added for LOCAL_CADENCE=2: the control the first form lacked)
The truth at 60 fps puts both at their smooth positions, background 3 tau and disc 8 tau (tau in source frames): the
existing cadence branch's convention, the span from the first copy of a drawing to the next drawing.
Scored on the synthesized outputs only (every fifth 60 fps output sits on a source frame), the first and last ten
outputs dropped (the four-frame window's lead-in): PSNR over the frame, and over the truth's disc dilated 24 px.
"""
import os
import subprocess
import sys

import numpy as np

FF = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
W, H, N24 = 1280, 720, 72
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64) + 0.5


def bg(off):
    x = xx - off
    return (0.42 + 0.10 * np.sin(2 * np.pi * x / 37.0) * np.cos(2 * np.pi * yy / 53.0)
            + 0.07 * np.sin(2 * np.pi * (x * 0.6 + yy * 0.8) / 23.0) + 0.04 * np.cos(2 * np.pi * x / 9.7))


def disc(img, cx, cy=360.0, r=80.0):
    dx, dy = xx - cx, yy - cy
    inside = np.clip(r + 0.5 - np.hypot(dx, dy), 0, 1)
    tex = 0.72 + 0.14 * np.sin(2 * np.pi * dx / 11.0) * np.cos(2 * np.pi * dy / 13.0) + 0.06 * np.sin(2 * np.pi * (dx + dy) / 7.0)
    return img * (1 - inside) + tex * inside, inside


def frame(t_bg, t_disc):
    return disc(bg(3.0 * t_bg), 200.0 + 8.0 * t_disc)


def write(path, frames, rate):
    raw = path + '.gray16'
    np.stack([np.rint(np.clip(f, 0, 1) * 65535).astype('<u2') for f in frames]).tofile(raw)
    subprocess.run([FF, '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray16le', '-video_size', f'{W}x{H}',
                    '-framerate', rate, '-i', raw, '-vf', 'format=yuv444p16le', '-c:v', 'ffv1', path], check=True)
    os.remove(raw)


def make(out):
    held = lambda k: 2 * (k // 2)
    for name, tb, td in (('mixed', lambda k: k, held), ('ones', lambda k: k, lambda k: k), ('twos', held, held),
                         ('still', lambda k: 0, lambda k: k)):          # the control LOCAL_CADENCE=1 lacked (C2b)
        d = f'{out}/{name}'; os.makedirs(d, exist_ok=True)
        write(f'{d}/src24.mkv', [frame(tb(k), td(k))[0] for k in range(N24)], '24')
        tr = [frame(0 if name == 'still' else m * 24 / 60, m * 24 / 60) for m in range(N24 * 60 // 24)]
        write(f'{d}/truth60.mkv', [f for f, _ in tr], '60')
        np.save(f'{d}/disc60.npy', np.stack([m > 0 for _, m in tr]))
        print('made', name)


def read(path):
    r = subprocess.run([FF, '-nostdin', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'gray16le', '-'], capture_output=True)
    return np.frombuffer(r.stdout, '<u2').reshape(-1, H, W).astype(np.float64) / 65535


def score(out, shaders):
    from scipy.ndimage import binary_dilation
    env = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
    for scene in ('mixed', 'ones', 'twos', 'still'):
        d = f'{out}/{scene}'; truth = read(f'{d}/truth60.mkv'); mask = np.load(f'{d}/disc60.npy')
        rows = []
        for name, sh in shaders.items():
            mix = 'linear' if sh == 'linear' else f'custom_n:custom_shader_path={sh}'
            o = f'{d}/out_{name}.mkv'
            r = subprocess.run([FF, '-nostdin', '-v', 'warning', '-y', '-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk',
                                '-i', f'{d}/src24.mkv', '-vf', f'libplacebo=fps=60:frame_mixer={mix}', '-c:v', 'ffv1', '-pix_fmt',
                                'yuv444p16le', o], capture_output=True, text=True, env=env)
            # FAIL CLOSED (2026-10-25, GPT's G028: the first form printed 40 dB for a failed, disabled, 30-frame render):
            # a non-zero exit, a disabled or uncompiled shader, more than a window's lead-in of skipped hooks, a frame
            # count other than the truth's, or source instants that do not reproduce the source all refuse the scene
            err = r.stderr.lower()
            if r.returncode or any(s in err for s in ('compile status', 'disabling', 'failed to', 'error reinit')):
                sys.exit(f'REFUSED {scene} {name}: render failed or shader disabled (rc {r.returncode})')
            if err.count('skipped') > 8:
                sys.exit(f'REFUSED {scene} {name}: {err.count("skipped")} skipped hooks')
            im = read(o)
            if len(im) != len(truth):
                sys.exit(f'REFUSED {scene} {name}: {len(im)} frames, the truth has {len(truth)}')
            src = read(f'{d}/src24.mkv')
            worst = max(np.sqrt(((im[m] - src[m * 24 // 60]) ** 2).mean()) * 255 for m in range(10, len(im) - 10, 5))
            if worst > 1.0:
                sys.exit(f'REFUSED {scene} {name}: a source instant is {worst:.2f} codes from its source frame (alignment)')
            n = len(im)
            keep = [m for m in range(10, n - 10) if m % 5 != 0]
            ef, ed = [], []
            for m in keep:
                e = (im[m] - truth[m]) ** 2; md = binary_dilation(mask[m], iterations=24)
                ef.append(e.mean()); ed.append(e[md].mean())
            rows.append((name, -10 * np.log10(np.mean(ef)), -10 * np.log10(np.mean(ed)), np.mean(ed)))
            print(f'{scene:6s} {name:14s} frame {rows[-1][1]:6.2f} dB   disc region {rows[-1][2]:6.2f} dB', flush=True)


if __name__ == '__main__':
    cmd, out = sys.argv[1], sys.argv[2]
    if cmd == 'make':
        make(out)
    else:
        score(out, dict(a.split('=', 1) for a in sys.argv[3:]))
