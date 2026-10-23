#!/usr/bin/env python3
"""Bounded, local missing-frame prospecting. See PREDICTION.md for frozen rules.

sample MANIFEST OUT: first title per class from content.py's private manifest;
copy five minutes centred at runtime midpoint, video only (bounded input seek).
controls OUT: CPU adversaries and actual GPU alignment control.
scan OUT: prepare width-640 references, render High/linear, stream scores, rank.
score OUT: re-rank existing measurements without rendering or NAS traffic.

All footage, source identities, generated files and detailed measurements stay
in OUT outside git. No full-source decode/hash. FFMPEG/FFPROBE override builds.
ssim8 is a non-overlapping 8x8 luma statistic, not ffmpeg's SSIM implementation.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[3]
FF = os.environ.get('FFMPEG', str(Path.home() / 'np-build/ffmpeg/ffmpeg'))
FP = os.environ.get('FFPROBE', str(Path.home() / 'np-build/ffmpeg/ffprobe'))
HIGH = REPO / 'shaders/bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut.glsl'
os.environ.setdefault('MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS', '0')
os.environ.setdefault('MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE', '1')


def save(p, x):
    p.write_text(json.dumps(x, indent=2, allow_nan=False) + '\n')


def call(cmd, root, log):
    with (root / log).open('w') as f:
        r = subprocess.run(cmd, cwd=root, stdout=f, stderr=f)
    text = (root / log).read_text(errors='replace')
    if r.returncode or re.search(r'compile status.*error|Failed.*shader|Error reinitializing', text, re.I):
        raise RuntimeError(f'command refused: {log} (exit {r.returncode})')
    if text.count('hook skipped') > 2:
        raise RuntimeError(f'hooks skipped: {log}')


def probe(p):
    r = subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height,r_frame_rate,avg_frame_rate,field_order,color_transfer:format=duration',
                        '-of', 'json', str(p)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    return dict(d['streams'][0], duration=float(d['format']['duration']))


def sample(manifest, out):
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'sources.json').exists():
        raise ValueError('sources.json already exists; reuse it, do not fetch again')
    clips = json.loads(manifest.read_text())
    rows = []
    for cls in ['film', 'tv', 'anime', 'cartoon', 'cg']:
        c = next(c for c in clips if c['class'] == cls)
        p = Path(c['file']); meta = probe(p)
        if meta['r_frame_rate'] not in ('24000/1001', '24/1', '25/1'):
            raise ValueError(f'{cls}: unsupported rate')
        if meta.get('field_order', 'unknown') not in ('progressive', 'unknown'):
            raise ValueError(f'{cls}: interlaced source')
        if meta.get('color_transfer') in ('smpte2084', 'arib-std-b67'):
            raise ValueError(f'{cls}: HDR needs a separate colour-managed protocol')
        start = round(max(0, meta['duration'] / 2 - 150), 3)
        root = out / cls; root.mkdir()
        # Accurate input seeking on transcode, not packet-copy pre-roll whose
        # effective origin varies by keyframe. Decode five minutes ONCE, locally
        # encode lossless FFV1 at native size, avoid any source re-read later.
        call([FF, '-nostdin', '-y', '-v', 'warning', '-ss', str(start), '-t', '300', '-i', str(p),
              '-map', '0:v:0', '-an', '-sn', '-fps_mode', 'passthrough', '-c:v', 'ffv1',
              str(root / 'native.mkv')], root, 'sample.log')
        row = dict(id=cls, source=str(p), start=start, requested_seconds=300, meta=meta,
                   bytes_local=(root / 'native.mkv').stat().st_size)
        rows.append(row); save(out / 'sources.partial.json', rows)
        print(f'sampled {cls}: {start:.3f}s, local {row["bytes_local"] / 1e6:.0f} MB', flush=True)
    save(out / 'sources.json', rows)


def prepare(root, rate, width=640):
    meta = probe(root / 'native.mkv')
    w = min(width, meta['width']); w -= w % 2
    h = round(meta['height'] * w / meta['width'] / 2) * 2
    native_count = frame_count(root / 'native.mkv')
    keep = native_count - native_count % 2
    # A last odd-index frame has no right anchor. Trim only that untestable
    # tail, before decimation, rather than silently accept a renderer count gap.
    save(root / 'prepare.json', dict(native_frames=native_count, reference_frames=keep,
                                     tail_unpaired_frames=native_count-keep, width=w, height=h, rate=rate))
    call([FF, '-nostdin', '-y', '-v', 'warning', '-i', str(root / 'native.mkv'), '-an', '-sn',
          '-vf', f'trim=end_frame={keep},scale={w}:{h}:flags=lanczos,format=yuv420p,setpts=N/({rate})/TB',
          '-r', rate, '-c:v', 'ffv1', str(root / 'ref.mkv')], root, 'prepare.log')
    # CFR timestamps have no dropped/duplicated frames silently admitted: the
    # timestamp-normalisation is only valid if native decode count is unchanged.
    if frame_count(root / 'ref.mkv') != keep:
        raise ValueError('CFR normalisation changed frame count')
    half = str(Fraction(rate) / 2)
    call([FF, '-nostdin', '-y', '-v', 'warning', '-i', str(root / 'ref.mkv'), '-vf',
          f"select='not(mod(n,2))',setpts=N/({half})/TB", '-r', half,
          '-an', '-c:v', 'ffv1', str(root / 'half.mkv')], root, 'half.log')
    return w, h


def frame_count(p):
    return int(subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                              '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(p)],
                             capture_output=True, text=True, check=True).stdout.strip())


def render(root, rate, name):
    chain = f'libplacebo=fps={rate}:frame_mixer='
    chain += 'linear' if name == 'linear' else 'custom_n:custom_shader_path=high.glsl'
    call([FF, '-nostdin', '-y', '-v', 'warning', '-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk',
          '-i', str(root / 'half.mkv'), '-vf', chain + ',format=yuv420p', '-an',
          '-c:v', 'ffv1', str(root / f'{name}.mkv')], root, f'{name}.log')


def frames(path, w, h):
    with path.with_suffix('.decode.log').open('w') as log:
        p = subprocess.Popen([FF, '-nostdin', '-v', 'error', '-i', str(path), '-map', '0:v:0',
                              '-vf', 'extractplanes=y', '-pix_fmt', 'gray', '-fps_mode', 'passthrough',
                              '-f', 'rawvideo', '-'], stdout=subprocess.PIPE, stderr=log)
        try:
            while True:
                b = p.stdout.read(w * h)
                if not b:
                    break
                if len(b) != w * h:
                    raise ValueError('truncated frame: ' + path.name)
                yield np.frombuffer(b, np.uint8).reshape(h, w).astype(np.float32)
            if p.wait():
                raise ValueError('decode failed: ' + path.name)
        finally:
            if p.poll() is None:
                p.terminate(); p.wait()
            p.stdout.close()


def rms(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def ssim8(a, b):
    h, w = a.shape; h -= h % 8; w -= w % 8
    a = a[:h, :w].reshape(h // 8, 8, w // 8, 8)
    b = b[:h, :w].reshape(h // 8, 8, w // 8, 8)
    ma, mb = a.mean((1, 3)), b.mean((1, 3))
    va, vb = (a * a).mean((1, 3)) - ma * ma, (b * b).mean((1, 3)) - mb * mb
    cov = (a * b).mean((1, 3)) - ma * mb
    return float(np.mean(((2 * ma * mb + 6.5025) * (2 * cov + 58.5225)) /
                         ((ma * ma + mb * mb + 6.5025) * (va + vb + 58.5225))))


def tiles(a, b):
    # 16 x 16 equal-sized cells; at most 15 bottom/right pixels omitted here
    # only. Whole-frame RMSE/SSIM still use their documented full domain.
    h, w = a.shape; h -= h % 16; w -= w % 16
    e = (a[:h, :w] - b[:h, :w]) ** 2
    return np.sqrt(e.reshape(16, h // 16, 16, w // 16).mean((1, 3)))


def alignment(retained, nref, nout):
    if nref != nout:
        raise ValueError(f'count mismatch {nref} != {nout}')
    if not retained or max(retained) > 2.55:
        raise ValueError(f'passthrough alignment refused: max RMS {max(retained, default=-1):.3f}')


def measure(root, w, h, rate, high='high'):
    call([FF, '-nostdin', '-v', 'warning', '-i', str(root / 'ref.mkv'), '-vf',
          'scdet=threshold=8,metadata=print:file=scdet.txt', '-an', '-f', 'null', '-'], root, 'scdet.log')
    scores = [float(v) for v in re.findall(r'lavfi.scd.score=([\d.]+)', (root / 'scdet.txt').read_text())]
    rows, retained, count = [], [], 0
    previous = middle = None
    streams = [frames(root / f'{name}.mkv', w, h) for name in ['ref', high, 'linear']]
    sentinel = object()
    try:
        for n, triplet in enumerate(itertools.zip_longest(*streams, fillvalue=sentinel)):
            if any(v is sentinel for v in triplet):
                raise ValueError('stream count mismatch')
            ref, sh, lin = triplet; count += 1
            if n % 2 == 0:
                retained.append(rms(ref, sh))
                if middle is not None:
                    row, midref = middle
                    row.update(adj_right=rms(midref, ref), endpoint=rms(previous, ref))
                    rows.append(row); middle = None
                previous = ref
            else:
                ts, tl = tiles(ref, sh), tiles(ref, lin)
                excess = ts - tl
                iy, ix = np.unravel_index(np.argmax(excess), excess.shape)
                middle = (dict(frame=n, seconds=n / float(Fraction(rate)), shader=rms(ref, sh),
                               linear=rms(ref, lin), ssim_shader=ssim8(ref, sh), ssim_linear=ssim8(ref, lin),
                               adj_left=rms(previous, ref), tile_excess=float(excess[iy, ix]),
                               tile_ratio=float(ts[iy, ix] / max(tl[iy, ix], .1)),
                               tile_xy=[int(ix), int(iy)], tile_shader=float(ts[iy, ix]),
                               tile_linear=float(tl[iy, ix])), ref)
        alignment(retained, count, count)
        if len(scores) != count:
            raise ValueError(f'scdet count mismatch {len(scores)} != {count}')
    finally:
        for stream in streams:
            stream.close()
    cut_frames = np.flatnonzero(np.array(scores) >= 8)
    guard = float(Fraction(rate)) * .25
    for row in rows:
        # A withheld pair straddles a cut if either boundary crosses it.
        n = row['frame']
        row['cut'] = bool(np.any(np.abs(cut_frames - n) <= guard + 1))
        row['boundary'] = row['seconds'] < .5 or row['seconds'] > (count - 1) / float(Fraction(rate)) - .5
        row['hold'] = min(row['adj_left'], row['adj_right']) < 1.5
        row['low'] = row['endpoint'] < 2 or row['shader'] < 2
    result = dict(frames=count, retained_max=max(retained), retained_median=float(np.median(retained)),
                  scdet_cuts=len(cut_frames), width=w, height=h, rate=rate, rows=rows)
    save(root / ('metrics.json' if high == 'high' else f'metrics_{high}.json'), result)
    return result


def shortlist(result):
    rows = result['rows']
    base = [r for r in rows if not any(r[k] for k in ('cut', 'boundary', 'hold', 'low'))]
    threshold = min(50., float(np.percentile([r['endpoint'] for r in base], 97.5))) if base else 50.
    eligible = []
    for r in rows:
        r['extreme'] = r['endpoint'] > threshold or r['endpoint'] >= 50
        # Overlapping counts retained; exclusive reason follows this priority.
        r['bucket'] = next((k for k in ('boundary', 'cut', 'hold', 'low', 'extreme') if r[k]), 'eligible')
        r['loss_db'] = float(20 * np.log10(max(r['shader'], .01) / max(r['linear'], .01)))
        r['regression'] = r['loss_db'] >= 1 and r['ssim_linear'] - r['ssim_shader'] >= .005
        r['local_regression'] = r['tile_excess'] >= 2 and r['tile_ratio'] >= 1.25
        if r['bucket'] == 'eligible':
            eligible.append(r)
    x = np.array([r['loss_db'] / 10 for r in eligible])
    med = float(np.median(x)) if len(x) else 0
    scale = max(.1, float(1.4826 * np.median(np.abs(x - med)))) if len(x) else .1
    for r in rows:
        r['robust_z'] = (r['loss_db'] / 10 - med) / scale
    picked = []
    for lane, key, limit in [('relative', 'robust_z', 3), ('absolute', 'shader', 2)]:
        selected = []
        for r in sorted(eligible, key=lambda r: r[key], reverse=True):
            if all(abs(r['seconds'] - x['seconds']) >= 1 for x in selected):
                selected.append(r)
            if len(selected) == limit:
                break
        picked.extend(dict(r, lane=lane) for r in selected)
    raw = sorted(rows, key=lambda r: r['shader'], reverse=True)[:20]
    return dict(counts=dict(Counter(r['bucket'] for r in rows)),
                overlapping={k: sum(r[k] for r in rows) for k in ('cut', 'boundary', 'hold', 'low', 'extreme')},
                extreme_threshold=threshold, median_eligible_gain_db=-float(np.median([r['loss_db'] for r in eligible])) if eligible else None,
                eligible_regressions=sum(r['regression'] for r in eligible),
                eligible_local_regressions=sum(r['local_regression'] for r in eligible),
                raw_top20_excluded=sum(r['bucket'] != 'eligible' for r in raw), candidates=picked)


def controls(out):
    root = out / 'controls'; root.mkdir(parents=True, exist_ok=True)
    yy, xx = np.indices((128, 256))
    a = (100 + 35 * np.sin(xx / 8) + 25 * np.cos(yy / 6)).astype(np.float32)
    assert rms(a, a) == 0 and abs(ssim8(a, a) - 1) < 1e-6
    # Exact translation of an affine intensity plane: the true time-midpoint
    # equals the blend. This checks frame-1/3 -> frame-2 arithmetic independently.
    affine = 80 + xx.astype(np.float32) / 4 + yy.astype(np.float32) / 8
    left, right = affine + 2, affine - 2
    assert rms((left + right)/2, affine) == 0
    b = a.copy(); b[48:80, 96:128] += 40
    assert rms(a, b) > 2 and tiles(a, b).max() > 20
    for counts in [(5, 4), (4, 5)]:
        try: alignment([0], *counts)
        except ValueError: pass
        else: raise AssertionError('count counterfactual missed')
    try: alignment([rms(a, np.roll(a, 8, 1))], 5, 5)
    except ValueError: pass
    else: raise AssertionError('shift counterfactual missed')
    # Scorer controls use actual image-derived residuals above, then named
    # independent labels. Actual scdet decoding is checked on a cut below.
    ordinary = dict(frame=25, seconds=1., shader=3., linear=4., ssim_shader=.95, ssim_linear=.94,
                    endpoint=8., tile_excess=0., tile_ratio=1., cut=False, boundary=False, hold=False, low=False)
    rs = [dict(ordinary, frame=25+2*i, seconds=1+i/12) for i in range(40)]
    for key in ['cut', 'hold', 'low']:
        rs.append(dict(ordinary, **{key: True}, shader=30.))
    rs.append(dict(ordinary, shader=30., endpoint=90.))
    rs.append(dict(ordinary, shader=10., linear=3., ssim_shader=.7, seconds=10.))
    s = shortlist(dict(rows=rs))
    assert all(s['counts'].get(k) for k in ['cut', 'hold', 'low', 'extreme'])
    assert s['candidates'][0]['regression'] and s['candidates'][0]['seconds'] == 10
    # Smooth moving synthetic: oracle midpoint known analytically, not a
    # duplicated frame. Distinct texture in both directions, no clipping.
    raw = root / 'moving.gray'
    with raw.open('wb') as f:
        for n in range(72):
            frame = 110 + 40*np.sin((xx-2*n)/8) + 30*np.cos((yy-n)/6) + 15*np.sin((xx+yy-3*n)/17)
            f.write(np.rint(frame).astype('uint8').tobytes())
    call([FF, '-nostdin', '-y', '-v', 'warning', '-f', 'rawvideo', '-pixel_format', 'gray',
          '-video_size', '256x128', '-framerate', '24', '-i', str(raw), '-vf', 'format=yuv420p',
          '-c:v', 'ffv1', str(root / 'native.mkv')], root, 'source.log')
    w, h = prepare(root, '24', 256); shutil.copyfile(HIGH, root / 'high.glsl')
    for name in ['linear', 'high']:
        render(root, '24', name)
    m = measure(root, w, h, '24')
    # A real decoded black/white cut: exercise scdet, not an injected cut flag.
    cutraw = root / 'cut.gray'
    cutraw.write_bytes(b''.join(np.full((128, 256), 32 if n < 36 else 224,
                                      dtype='uint8').tobytes() for n in range(72)))
    call([FF, '-nostdin', '-v', 'warning', '-f', 'rawvideo', '-pixel_format', 'gray',
          '-video_size', '256x128', '-framerate', '24', '-i', str(cutraw), '-vf',
          'scdet=threshold=8,metadata=print:file=cut-scdet.txt', '-f', 'null', '-'], root, 'cut.log')
    cuts = [float(x) for x in re.findall(r'lavfi.scd.score=([\d.]+)', (root/'cut-scdet.txt').read_text())]
    assert len(cuts) == 72 and cuts[36] >= 8 and max(cuts[:36] + cuts[37:]) == 0
    assert rms(a, a + .25) < 1.5 and rms(a, a + .25) < 2  # actual noise/hold floor
    # Shifted-reference alarm using the real GPU output, not only CPU arrays.
    refs = list(frames(root/'ref.mkv', w, h)); preds = list(frames(root/'high.mkv', w, h))
    shifted = [rms(preds[n], refs[n+2]) for n in range(2, 66, 2)]
    try: alignment(shifted, len(refs), len(preds))
    except ValueError: pass
    else: raise AssertionError('GPU shifted reference accepted')
    save(root/'results.json', dict(cpu_controls='pass', gpu_frames=m['frames'],
                                  retained_max=m['retained_max'], shifted_min_rms=min(shifted),
                                  shader_sha256=hashlib.sha256(HIGH.read_bytes()).hexdigest()))
    print('CPU adversaries and GPU alignment controls pass', flush=True)


def scan(out, only=None):
    for src in json.loads((out / 'sources.json').read_text()):
        if only and src['id'] != only:
            continue
        root = out / src['id']; rate = src['meta']['r_frame_rate']
        if (root / 'metrics.json').exists():
            continue
        print(f'{src["id"]}: preparing local reference', flush=True)
        w, h = prepare(root, rate)
        shutil.copyfile(HIGH, root / 'high.glsl')
        for name in ['linear', 'high']:
            print(f'{src["id"]}: rendering {name}', flush=True); render(root, rate, name)
        print(f'{src["id"]}: scoring', flush=True); measure(root, w, h, rate)
    score(out)


def score(out):
    result = dict(sources={})
    for p in sorted(out.glob('*/metrics.json')):
        if p.parent.name == 'controls':
            continue
        m = json.loads(p.read_text()); s = shortlist(m)
        sha = hashlib.sha256((p.parent/'high.glsl').read_bytes()).hexdigest()
        if 'shader_sha256' in result and result['shader_sha256'] != sha:
            raise ValueError('mixed shader provenance')
        result['shader_sha256'] = sha
        result['sources'][p.parent.name] = dict(frames=m['frames'], retained_max=m['retained_max'], **s)
        save(p.parent / 'ranked.json', s)
        print(p.parent.name, s['counts'], f'median gain {s["median_eligible_gain_db"]:.2f} dB', flush=True)
        for r in s['candidates']:
            print(f'  {r["lane"]:8} frame {r["frame"]:5d} @{r["seconds"]:7.3f} '
                  f'RMS {r["shader"]:.2f}/{r["linear"]:.2f}, loss {r["loss_db"]:+.2f} dB '
                  f'SSIM8 {r["ssim_shader"]:.4f}/{r["ssim_linear"]:.4f}', flush=True)
    save(out / 'summary.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sample', 'controls', 'scan', 'score'])
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--only')
    args = parser.parse_args()
    if args.command == 'sample':
        sample(args.paths[0].resolve(), args.paths[1].resolve())
    elif args.command == 'controls':
        controls(args.paths[0].resolve())
    elif args.command == 'scan':
        scan(args.paths[0].resolve(), args.only)
    else:
        score(args.paths[0].resolve())
