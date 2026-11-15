#!/usr/bin/env python3
"""Score real withheld frames, separately from native-rate ripple diagnostics.

The source is the original full-rate clip. Each reconstruction must have been
rendered at that same rate from its EVEN frames at half rate. Thus the displacement
between interpolation endpoints is TWICE the native 2x interpolation displacement.
This is a different stress condition, not ground truth for native 24 -> 48 output.

  withheld.py source.mkv high=high-half-recon.mkv prev=prev-half-recon.mkv \
      --crop 240:230:700:620 --first-frame 49 --last-frame 95 --out /tmp/shirt-withheld

Count every stream first, then decode only the selected interval and crop plus a
small Gaussian support margin. Only odd original frame indices with two genuine
neighbors are scored. Even retained frames must align within the specified MAE
before a reconstruction is scored. All geometry is fixed across variants.

PSNR (160 dB ceiling), worst-1% RMS, and worst 32x32 tile RMS are reported on raw
and Gaussian-1/2 luma. The smoothed images additionally have vector-gradient error
in DN/pixel. Per-frame records retain local failures; summary PSNR pools MSE rather
than averaging dB. Film grain is part of real truth but cannot be predicted exactly.
Lower smoothed error alone can reward blur; inspect gradient and boundary maps.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
from scipy.ndimage import gaussian_filter

from temporal import crop_arg, decode, write_maps


def video_info(path, ffprobe):
    command = [ffprobe, '-v', 'error', '-select_streams', 'v:0', '-count_frames',
               '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames', '-of', 'json', str(path)]
    result = subprocess.run(command, capture_output=True, check=True)
    streams = json.loads(result.stdout)['streams']
    if len(streams) != 1:
        raise ValueError(f'{path}: expected one selected video stream')
    s = streams[0]
    return dict(width=int(s['width']), height=int(s['height']),
                rate=s['avg_frame_rate'], frames=int(s['nb_read_frames']))


def tile_scores(squared, block, origin):
    h, w = squared.shape
    values, worst = [], None
    for y in range(0, h, block):
        row = []
        for x in range(0, w, block):
            tile = squared[y:y+block, x:x+block]
            rms = float(np.sqrt(np.mean(tile))*255)
            row.append(rms)
            if worst is None or rms > worst['rms_dn']:
                worst = dict(rms_dn=rms, x=origin[0]+x, y=origin[1]+y,
                             width=tile.shape[1], height=tile.shape[0])
        values.append(row)
    return np.asarray(values, np.float32), worst


def error_stats(error, block, origin):
    e = np.square(error, dtype=np.float64)
    mse = float(e.mean())
    count = max(1, int(np.ceil(e.size*0.01)))
    tail = np.partition(e.ravel(), e.size-count)[-count:]
    tiles, worst = tile_scores(e, block, origin)
    return dict(mse=mse, psnr_db=float(-10*np.log10(max(mse, 1e-16))),
                exact_match=bool(mse == 0), mae_dn=float(np.abs(error).mean()*255),
                rms_dn=float(np.sqrt(mse)*255), worst_1pct_rms_dn=float(np.sqrt(tail.mean())*255),
                worst_tile=worst), tiles


def gradient_error(a, b):
    ay, ax = np.gradient(a)
    by, bx = np.gradient(b)
    return (ax-bx)**2+(ay-by)**2


def score(reference, render, frame_indices, roi, block, origin):
    rows, sums, worst_frames = [], {}, {}
    y, x, h, w = roi
    selection = np.s_[y:y+h, x:x+w]
    # Gradients have support outside the ROI too; differentiate the padded image
    # before cropping. No artificial derivative boundary at the garment ROI edge.
    for local, frame in frame_indices:
        row = dict(source_frame=frame, render_frame=frame, scales={})
        for sigma in (0, 1, 2):
            a = reference[local] if sigma == 0 else gaussian_filter(reference[local], sigma, mode='reflect')
            b = render[local] if sigma == 0 else gaussian_filter(render[local], sigma, mode='reflect')
            error = b[selection]-a[selection]
            value, tiles = error_stats(error, block, origin)
            key = 'raw' if sigma == 0 else f'sigma{sigma}'
            if sigma:
                ge = gradient_error(a, b)[selection]
                _, worst_gradient = tile_scores(ge, block, origin)
                value['gradient_mse'] = float(ge.mean())
                value['gradient_rms_dn_per_px'] = float(np.sqrt(ge.mean())*255)
                value['worst_gradient_tile'] = {
                    **{k: v for k, v in worst_gradient.items() if k != 'rms_dn'},
                    'rms_dn_per_px': worst_gradient['rms_dn']}
            row['scales'][key] = value
            if key not in sums:
                sums[key] = dict(squared=np.zeros_like(error, np.float64),
                                 tile_squared=np.zeros_like(tiles, np.float64))
            sums[key]['squared'] += error.astype(np.float64)**2
            sums[key]['tile_squared'] += tiles.astype(np.float64)**2
            if key not in worst_frames or value['worst_tile']['rms_dn'] > worst_frames[key]['value']:
                worst_frames[key] = dict(value=value['worst_tile']['rms_dn'], source_frame=frame,
                                         error=np.abs(error)*255)
                if sigma:
                    worst_frames[key]['gradient'] = np.sqrt(ge)*255
        rows.append(row)
    summary, maps = {}, {}
    for key in sums:
        values = [r['scales'][key] for r in rows]
        mse = float(np.mean([v['mse'] for v in values]))
        worst = max(rows, key=lambda r: r['scales'][key]['worst_tile']['rms_dn'])
        summary[key] = dict(mse=mse, psnr_db=float(-10*np.log10(max(mse, 1e-16))),
                            mae_dn=float(np.mean([v['mae_dn'] for v in values])),
                            rms_dn=float(np.sqrt(mse)*255),
                            worst_1pct_rms_dn=float(np.sqrt(np.mean([v['worst_1pct_rms_dn']**2 for v in values]))),
                            worst_tile={**worst['scales'][key]['worst_tile'], 'source_frame': worst['source_frame']})
        if key != 'raw':
            gmse = float(np.mean([v['gradient_mse'] for v in values]))
            summary[key]['gradient_mse'] = gmse
            summary[key]['gradient_rms_dn_per_px'] = float(np.sqrt(gmse)*255)
            g_worst = max(rows, key=lambda r: r['scales'][key]['worst_gradient_tile']['rms_dn_per_px'])
            summary[key]['worst_gradient_tile'] = {**g_worst['scales'][key]['worst_gradient_tile'],
                                                    'source_frame': g_worst['source_frame']}
        maps[f'{key}_rms_error_dn'] = np.sqrt(sums[key]['squared']/len(rows))*255
        maps[f'{key}_block_rms_error_dn'] = np.sqrt(sums[key]['tile_squared']/len(rows))
        maps[f'{key}_worst_tile_frame_{worst_frames[key]["source_frame"]}_abs_error_dn'] = worst_frames[key]['error']
        if key != 'raw':
            maps[f'{key}_worst_tile_frame_{worst_frames[key]["source_frame"]}_gradient_error_dn_per_px'] = worst_frames[key]['gradient']
    return dict(summary=summary, per_frame=rows), maps


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('source', type=Path)
    p.add_argument('renders', nargs='+', help='LABEL=PATH; PATH alone uses its filename stem')
    p.add_argument('--crop', required=True, type=crop_arg)
    p.add_argument('--first-frame', required=True, type=int)
    p.add_argument('--last-frame', required=True, type=int, help='inclusive original-source index')
    p.add_argument('--retained-tolerance-dn', type=float, default=2.55)
    p.add_argument('--block', type=int, default=32)
    p.add_argument('--map-max-dn', type=float, default=16)
    p.add_argument('--max-decoded-mib', type=float, default=512)
    p.add_argument('--ffmpeg', default=str(Path.home()/'np-build/ffmpeg/ffmpeg'))
    p.add_argument('--ffprobe', default=shutil.which('ffprobe') or 'ffprobe')
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args(argv)
    if args.first_frame < 0 or args.last_frame <= args.first_frame or args.block < 1:
        p.error('require nonnegative first frame, later last frame and positive block size')
    if min(args.retained_tolerance_dn, args.map_max_dn, args.max_decoded_mib) <= 0:
        p.error('tolerance, map scale and memory limit must be positive')
    renders = []
    for item in args.renders:
        label, name = item.split('=', 1) if '=' in item else (Path(item).stem, item)
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in label):
            p.error('labels must use only letters, digits, underscores and hyphens')
        renders.append((label, Path(name)))
    if len({label for label, _ in renders}) != len(renders):
        p.error('labels must be unique')
    args.out.mkdir(parents=True, exist_ok=True)
    destination = args.out/'withheld.json'
    destination.write_text(json.dumps(dict(execution_status='incomplete', source=str(args.source)))+'\n')
    info = video_info(args.source, args.ffprobe)
    if args.last_frame >= info['frames']:
        p.error('selected interval exceeds original source frame count')
    expected = 2*((info['frames']+1)//2)
    width, height = info['width'], info['height']
    x, y, w, h = args.crop
    if x+w > width or y+h > height:
        p.error('crop exceeds the source image')
    x0, y0 = max(0, x-10)//2*2, max(0, y-10)//2*2
    x1, y1 = min(width, (x+w+11)//2*2), min(height, (y+h+11)//2*2)
    decoded = (x0, y0, x1-x0, y1-y0)
    count = args.last_frame-args.first_frame+1
    memory = 2*count*decoded[2]*decoded[3]*4/2**20
    if memory > args.max_decoded_mib:
        p.error(f'decoded source+render arrays require {memory:.1f} MiB, over limit')
    frames = np.arange(args.first_frame, args.last_frame+1)
    scored = [(i, int(n)) for i, n in enumerate(frames) if n % 2 and 0 < n < info['frames']-1]
    even = frames % 2 == 0
    if not scored or not even.any():
        p.error('interval needs both withheld odd frames and retained even frames')
    reference = decode(args.source, args.first_frame, count, decoded, args.ffmpeg)
    roi = (y-y0, x-x0, h, w)
    selection = np.s_[:, roi[0]:roi[0]+h, roi[1]:roi[1]+w]
    report = dict(schema=1, execution_status='incomplete', condition='even_half_input_reconstruction_doubled_displacement',
                  source=str(args.source), source_info=info, half_input_frames=(info['frames']+1)//2,
                  expected_render_frames=expected, crop=list(args.crop), decoded_crop=list(decoded),
                  first_frame=args.first_frame, last_frame=args.last_frame,
                  scored_original_odd_frames=[n for _, n in scored], block_size=args.block,
                  retained_tolerance_dn=args.retained_tolerance_dn, map_max_dn=args.map_max_dn,
                  notes=['These are real withheld original frames; they are not native-2x midpoint truth.',
                         'Endpoints are two original frame intervals apart: twice the native displacement.',
                         'Film grain and genuinely unpredictable detail contribute error.',
                         'The ROI includes object boundaries; no boundary failures are masked away.',
                         'Gradient metrics are computed after Gaussian sigma 1 and 2 pixels.',
                         'PSNR pools MSE across scored pixels and is capped at 160 dB for exact matches.'], renders={})
    for label, path in renders:
        actual = video_info(path, args.ffprobe)
        if actual['frames'] != expected or (actual['width'], actual['height']) != (width, height):
            raise ValueError(f'{path}: expected {expected} frames at {width}x{height}, got {actual}')
        if abs(float(Fraction(actual['rate'])/Fraction(info['rate']))-1) > 1e-5:
            raise ValueError(f'{path}: reconstruction rate must equal original source rate')
        render = decode(path, args.first_frame, count, decoded, args.ffmpeg)
        retained = np.abs(render[selection][even]-reference[selection][even])*255
        retained_mae = retained.mean(axis=(1, 2))
        if float(retained_mae.max()) >= args.retained_tolerance_dn:
            raise ValueError(f'{path}: retained-source alignment failed, max ROI MAE {retained_mae.max():.4f} DN')
        result, maps = score(reference, render, scored, roi, args.block, (x, y))
        report['renders'][label] = dict(path=str(path), info=actual,
                                       retained_mae_max_dn=float(retained_mae.max()),
                                       retained_mae_by_original_frame={str(int(n)):float(v) for n,v in zip(frames[even], retained_mae)},
                                       scored_frames=len(scored), **result)
        write_maps(args.out, label, maps, args.map_max_dn)
        del render
    report['execution_status'] = 'complete'
    destination.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(output=str(destination), source_frames=info['frames'],
                         expected_render_frames=expected, scored_frames=len(scored), renders=list(report['renders'])), indent=2))
    return report


if __name__ == '__main__':
    main()
