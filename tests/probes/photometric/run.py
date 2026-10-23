#!/usr/bin/env python3
"""Score PLAN.md's scenes: every shader through each scene's half-rate input back to its full rate, every withheld frame
scored against the exact reference (16-bit luma PSNR, frames 1 .. N-3), and High-family flow tapped at one middle pair
(flowtap.py's calibrated tail): median flow and the share of pixels over 1 px from the scene's truth.

    run.py <scenes-dir> <out.json> name=shader.glsl|linear ...      a scene's truth flow is read from its name:
                                                                     fade-* 0, pan-* +6, ramp* and sheet* +4 (x), all else none
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FF = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
ENV = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')


def frames(path, chain, w, h, hw):
    cmd = [FF, '-nostdin', '-v', 'error'] + (['-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk'] if hw else []) + \
          ['-i', path, '-vf', chain, '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'gray16le', '-']
    r = subprocess.run(cmd, capture_output=True, env=ENV)
    if b'compile status' in r.stderr.lower() or b'disabling' in r.stderr.lower():
        sys.exit(f'shader refused: {r.stderr[-300:]}')
    a = np.frombuffer(r.stdout, '<u2').astype(float) / 65535
    if a.size % (w * h): sys.exit(f'short output for {chain[:50]}')
    return a.reshape(-1, h, w)


def truth(scene):
    return 0.0 if scene.startswith('fade') else 6.0 if scene.startswith('pan') else 4.0 if scene.startswith(('ramp', 'sheet')) else None


def main():
    root, out = sys.argv[1], sys.argv[2]
    shaders = dict(a.split('=', 1) for a in sys.argv[3:])
    res = {}
    for scene in sorted(os.listdir(root)):
        d = os.path.join(root, scene)
        if not os.path.exists(os.path.join(d, 'scene.txt')):
            continue
        w, h, rate, half = open(os.path.join(d, 'scene.txt')).read().split(); w, h = int(w), int(h)
        ref = frames(os.path.join(d, 'ref.mkv'), 'null', w, h, False)
        res[scene] = {}
        for name, sh in shaders.items():
            chain = (f'libplacebo=fps={rate}:frame_mixer=linear' if sh == 'linear' else
                     f'libplacebo=fps={rate}:frame_mixer=custom_n:custom_shader_path={sh}')
            im = frames(os.path.join(d, 'half.mkv'), chain, w, h, True)
            n = min(len(im), len(ref))
            keep = [k for k in range(1, n - 2, 2)]
            retained = max(float(np.sqrt(((im[k] - ref[k]) ** 2).mean())) * 65535 / 257 for k in range(0, n - 2, 2))
            if retained > 2.55:
                sys.exit(f'{scene} {name}: retained frames misaligned (RMS {retained:.2f} codes)')
            mse = np.mean([((im[k] - ref[k]) ** 2).mean() for k in keep])
            row = {'psnr': float(-10 * np.log10(mse)), 'frames': len(keep)}
            t = truth(scene)
            if sh != 'linear' and t is not None:
                tap = os.path.join(d, f'_flow_{name}')
                subprocess.run([sys.executable, os.path.join(HERE, 'flowtap.py'), os.path.join(d, 'half.mkv'), sh, '5',
                                str(w), str(h), half, tap], check=True, capture_output=True, env=ENV)
                v = np.load(tap + '.npy')[32:-32, 32:-32]
                err = np.hypot(v[..., 0] - t, v[..., 1])
                row.update(flow_median_x=float(np.median(v[..., 0])), flow_off_1px=float(np.mean(err > 1)))
            res[scene][name] = row
            print(f"{scene:18s} {name:16s} PSNR {row['psnr']:6.2f}" + (f"  flow x {row['flow_median_x']:+.2f}  off >1px "
                  f"{100 * row['flow_off_1px']:5.1f}%" if 'flow_median_x' in row else ''), flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
