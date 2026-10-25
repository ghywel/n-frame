#!/usr/bin/env python3
"""L022 review: analytic attacks, with positive and negative controls.

    python review_attacks.py OUT

NumPy and SciPy; no footage or source edits. Writes JSON and a native analytic
history fixture (working luma, no transfer function assumed) outside the repo.
Optional --gpu-spectrum FFMPEG runs the unchanged spectrum shader on synthetic inputs.
Predictions: REVIEW-PREDICTION.md. Scope/interpretation: GPT-REVIEW.md.
"""
import argparse
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[3]


def rms(a):
    return float(np.sqrt(np.mean(np.square(a))))


def constants(name):
    """Read the actual literal, without executing a generator's top-level code."""
    tree = ast.parse((ROOT / 'tests/gen_quaddirectional.py').read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def history_report(frames):
    # Actual LC_DUP for mean absolute differences; the proposed history's RMS
    # version has the same binary decisions on the exact plateau examples.
    diff = np.mean(np.abs(np.diff(frames, axis=0)), axis=(1, 2))
    held = diff < .012
    alternating = held[:-2] == held[2:]
    alternating &= held[:-2] != held[1:-1]
    return dict(pairs=len(diff), qualifying_windows=int(alternating.sum()),
                windows=len(alternating), held_max=float(diff[held].max()) if held.any() else None,
                moving_min=float(diff[~held].min()) if (~held).any() else None,
                min_spatial_sd=float(np.std(frames, axis=(1, 2)).min()),
                pattern=''.join('H' if b else 'M' for b in held))


def strip(x, y, t, speed=64., soft=True):
    """A material texture translated at constant speed; no held source times.

    Period 4*speed, two plateaus of width 2*speed. Dense-cell test includes
    smooth transitions around both boundaries; no temporal discontinuities.
    """
    q = np.mod(x - speed * t, 4 * speed)
    if soft:
        # Periodic, continuous, piecewise smooth square wave; transition width 8px.
        z = np.sin(2 * np.pi * q / (4 * speed)) / np.sin(2 * np.pi * 4 / (4 * speed))
        u = np.clip((z + 1) / 2, 0, 1)
        level = u * u * (3 - 2 * u)
    else:
        level = (q < 2 * speed).astype(float)
    return .25 + .4 * level + .08 * np.sin(2 * np.pi * y / 17)


def cadence(out):
    actual = constants('LOCAL_CADENCE_CONSTANTS')
    assert 'LC_DUP = 0.012' in actual and actual.count('* 6.0 * HOOKED_pt') == 3
    y, x = np.mgrid[:32, :32].astype(float) + .5
    x += 16
    dense = np.stack([strip(x, y, t) for t in range(48)])
    dense_row = history_report(dense)
    assert dense_row['qualifying_windows'] == 45 and dense_row['held_max'] == 0
    # Literal positions from the currently built 5x5/six-pixel tap footprint.
    ty, tx = np.meshgrid(np.arange(-2, 3) * 6 + .5, np.arange(-2, 3) * 6 + 1.5,
                         indexing='ij')
    taps = np.stack([strip(tx, ty, t, speed=3, soft=False) for t in range(48)])
    tap_row = history_report(taps)
    assert tap_row['qualifying_windows'] == 45 and tap_row['held_max'] == 0
    assert min(dense_row['min_spatial_sd'], tap_row['min_spatial_sd']) > 4 / 255
    still = history_report(np.repeat(dense[:1], 48, axis=0))
    generic = np.stack([.5 + .17 * np.sin((x - 3*t) * 2*np.pi/19)
                        + .13 * np.cos((x - 3*t + y) * 2*np.pi/31) for t in range(48)])
    moving = history_report(generic)
    assert still['qualifying_windows'] == moving['qualifying_windows'] == 0
    # Native 512x144 texture with a dense-cell ROI x=16:48,y=0:32.
    fy, fx = np.mgrid[:144, :512].astype(float) + .5
    full = np.stack([strip(fx, fy, t) for t in range(48)])
    np.savez_compressed(out / 'constant-speed-history.npz', luma=full.astype('float32'),
                        roi_xywh=np.array([16, 0, 32, 32]), displacement_per_frame=np.array([64., 0.]))
    return dict(dense_cell=dense_row, actual_sparse_taps=tap_row, stationary_control=still,
                generic_pan_control=moving, dense_speed_px_per_source_frame=64,
                sparse_speed_px_per_source_frame=3)


def light_competition():
    y, x = np.mgrid[:25, :25].astype(float)
    d, a = 4., 1/128
    A = .3 + a*x + y/256
    B = .3 + a*(x-d) + y/256
    offset = float(np.mean(B-A))
    light = rms(B-offset-A)
    motion = rms((.3 + a*(x+d-d) + y/256)-A)
    assert light == motion == 0
    texture = lambda z: .5 + .1*np.sin(z*.47) + .09*np.cos((z+y)*.83)
    ta, tb = texture(x), texture(x-d)
    pan_light = rms(tb - np.mean(tb-ta) - ta)
    assert pan_light > .05 and rms(texture(x+d-d)-ta) == 0
    # A genuinely stationary texture under a constant offset: light fits exactly;
    # raw shifted candidates cannot erase the positive mean difference on this torus.
    rng = np.random.default_rng(20261025)
    tex = rng.uniform(.25, .65, (32, 32)); lit = tex + .04
    best_motion = min(rms(np.roll(lit, (dy, dx), (0, 1))-tex)
                      for dy in range(-4, 5) for dx in range(-4, 5))
    light_positive = rms(lit - .04 - tex)
    assert light_positive < 1e-15 and best_motion >= .04 - 1e-15
    return dict(ramp_correct_motion_rms=motion, ramp_zero_plus_offset_rms=light,
                ramp_offset=offset, ramp_raw_change_dn=abs(offset)*255,
                generic_pan_light_rms=pan_light, true_light_corrected_rms=light_positive,
                true_light_best_raw_shift_rms=best_motion)


def residual_coordinates():
    code = (ROOT / 'tests/global_gain.py').read_text()
    assert 'NEXT_tex(uv + v)' in code and '- LOCAL_LIGHT_tex(uv).r' in code
    x = np.arange(128, dtype=float) + .5
    d = 8.
    A = lambda z: .4 + .1*np.sin(z*.17)
    L = lambda z: .08*np.sin(2*np.pi*z/64)
    B = lambda z: A(z-d) + L(z)
    rA = lambda z: B(z+d)-A(z)
    # The mode-2 grid stores r_A(x). The helper looks it up at y=x+d.
    wrong = B(x+d)-rA(x+d)-A(x)
    expected = L(x+d)-L(x+2*d)
    correct = B(x+d)-rA(x)-A(x)
    assert np.max(np.abs(wrong-expected)) < 1e-15 and rms(correct) < 1e-15
    assert rms(wrong) > .04
    for dd, ll in ((0., L), (d, lambda z: np.full_like(z, .04))):
        bb = lambda z: A(z-dd) + ll(z)
        rr = lambda z: bb(z+dd)-A(z)
        assert rms(bb(x+dd)-rr(x+dd)-A(x)) < 1e-15
    return dict(wrong_coordinate_rms=rms(wrong), wrong_coordinate_rms_dn=rms(wrong)*255,
                correctly_transported_rms=rms(correct), displacement_px=d,
                note='Ideal dense residual, unity gate; grid smoothing/gating are not simulated.')


def spectrum_trace(y):
    t = np.arange(-4, 4, dtype=float)
    centered = y - y.mean()
    tc = t-t.mean()
    residual = centered - tc * np.dot(tc, centered)/np.dot(tc, tc)
    power = []
    for f in range(1, 5):
        z = np.sum(residual * np.exp(-2j*np.pi*f*t/8))
        power.append(float(abs(z)**2/64*(1 if f == 4 else 2)))
    energy = sum(power)
    return dict(power=power, energy=energy, centroid_bin=float(np.dot(np.arange(1, 5), power)/energy)
                if energy > 1e-25 else None)


def spectrum():
    t = np.arange(-4, 4, dtype=float)
    pan = spectrum_trace(.5 + .1*np.sin(2*np.pi*(1.5-4*t)/16))
    line = spectrum_trace(.5 + .01*t)
    flat = spectrum_trace(np.full(8, .5))
    assert pan['energy'] > .004 and line['energy'] < 1e-25 and flat['energy'] == 0
    return dict(uniform_pan=pan, linear_trace_control=line, constant_control=flat,
                true_pan_temporal_frequency_at_24fps_hz=6.,
                shader_centroid_at_24fps_hz=pan['centroid_bin']*3)


def harness_fault():
    """Execute the actual scorer with injected failed/short subprocess replies.

    No FFmpeg run or source-file edits. A valid-looking partial decode is the
    failure counterfactual: the scorer must refuse it, not publish finite PSNR.
    """
    path = ROOT/'tests/probes/imports/cadence_scenes.py'
    spec = importlib.util.spec_from_file_location('reviewed_cadence_scenes', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.W = module.H = 8
    calls = []

    def failed_run(cmd, **kwargs):
        calls.append(cmd)
        if '-init_hw_device' in cmd:
            return SimpleNamespace(returncode=1, stdout='', stderr='Disabling custom shader: injected failure')
        truth = str(cmd[cmd.index('-i')+1]).endswith('truth60.mkv')
        data = np.full((180 if truth else 30, 8, 8), 20000 if truth else 20655, dtype='<u2')
        return SimpleNamespace(returncode=0 if truth else 1, stdout=data.tobytes(),
                               stderr=b'' if truth else b'Injected decoder failure after partial output')

    printed = io.StringIO()
    with patch.object(module.subprocess, 'run', failed_run), \
            patch.object(module.np, 'load', return_value=np.ones((180, 8, 8), dtype=bool)), \
            contextlib.redirect_stdout(printed):
        module.score('injected-no-files', {'failed-and-short': 'unused.glsl'})
    lines = printed.getvalue().splitlines()
    assert len(lines) == 4 and all('40.00' in line for line in lines)
    return dict(fault_accepted=True, printed_scores=lines, render_returncode=1,
                output_decode_returncode=1, truth_frames=180, decoded_output_frames=30,
                subprocess_calls=len(calls), scope='Injected process responses to the actual unchanged scorer')


def gpu_spectrum(out, ffmpeg):
    """Run the unmodified spectrum shader; grayscale inputs reveal silent fallback."""
    w, h, n = 192, 96, 16
    x = np.arange(w, dtype=float)+.5
    env = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0',
               MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
    shader = out/'spectrum.glsl'
    shader.write_bytes((ROOT/'shaders/effects/spectrum.glsl').read_bytes())
    result = {}
    for name in ('constant', 'pan'):
        rgb = np.empty((n, h, w, 4), dtype='<u2'); rgb[..., 3] = 65535
        for k in range(n):
            y = np.full(w, .5) if name == 'constant' else .5+.1*np.sin(2*np.pi*(x-4*k)/16)
            rgb[k, ..., :3] = np.rint(y[None, :, None]*65535).astype('<u2')
        inp, dst = out/f'{name}-in.rgba64', out/f'{name}-spectrum.rgba64'
        rgb.tofile(inp)
        cmd = [str(ffmpeg), '-nostdin', '-y', '-hide_banner', '-loglevel', 'warning',
               '-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk',
               '-f', 'rawvideo', '-pixel_format', 'rgba64le', '-video_size', f'{w}x{h}',
               '-framerate', '24', '-color_primaries', 'bt709', '-color_trc', 'linear',
               '-colorspace', 'bt709', '-color_range', 'pc', '-i', str(inp),
               '-vf', f'libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path={shader}:dithering=none:format=rgba64le',
               '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgba64le', str(dst)]
        run = subprocess.run(cmd, capture_output=True, text=True, env=env)
        (out/f'{name}-spectrum.log').write_text(run.stderr)
        assert run.returncode == 0, run.stderr[-3000:]
        assert not any(s in run.stderr.lower() for s in ('compile status', 'disabling', 'failed to')), run.stderr
        a = np.fromfile(dst, '<u2')
        assert a.size == n*h*w*4, f'{name}: unexpected output count {a.size}'
        a = a.reshape(n, h, w, 4)[4:12, ..., :3].astype(float)/65535
        spread = float(np.mean(np.max(a, axis=-1)-np.min(a, axis=-1)))
        assert spread < .005 if name == 'constant' else spread > .05, (name, spread)
        result[name] = dict(output_frames=n, scored_frames=8, mean_rgb_channel_spread=spread)
    result['shader_sha256'] = hashlib.sha256(shader.read_bytes()).hexdigest()
    result['scope'] = 'Actual spectrum shader on M5; no interpolation quality claim'
    (out/'gpu-spectrum.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--gpu-spectrum', type=Path, metavar='FFMPEG', help='Optional actual spectrum GPU control')
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    paths = ['tests/global_gain.py', 'tests/gen_quaddirectional.py',
             'tests/probes/imports/diagnose.py', 'shaders/effects/spectrum.body.glsl',
             'tests/probes/imports/cadence_scenes.py']
    result = dict(source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                  cadence=cadence(out), light_competition=light_competition(),
                  residual_coordinates=residual_coordinates(), spectrum=spectrum(), harness_fault=harness_fault(),
                  scope='CPU analytic counterexamples; no GPU field or quality verdict')
    if args.gpu_spectrum:
        result['gpu_spectrum'] = gpu_spectrum(out, args.gpu_spectrum)
    (out/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
