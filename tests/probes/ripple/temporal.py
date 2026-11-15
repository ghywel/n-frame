#!/usr/bin/env python3
"""Locate native 2x interpolation ripple in a tracked garment interior (CPU only).

This is a diagnostic, NOT a truth/quality score. Real folds, lighting and film grain
can produce the same signal. Register using SOURCE frames alone. Never fit to a
render or shader field. A poor/ambiguous translation makes the remaining track
unknown; it does not count as clean. No affine/cloth deformation is fitted away.

Example (crop at the first SELECTED source frame, not the clip's first frame):
  temporal.py source.mkv high.mkv prev.mkv --crop 440:450:140:140 \
      --start-frame 48 --frames 37 --margin 160 --out /tmp/shirt-temporal

Only the crop plus margin is decoded. Render frame 2*n must retain source frame n.
Frames after the final selected source frame are not used. All source-derived
transforms and validity decisions are shared by every supplied render. JSON has
registration residual/ambiguity and per-scale scalar summaries. NPZ and fixed-scale
PNG maps retain spatial structure; differences of scalar frame errors are NOT used.

Temporal curvature is J[k-1]-2*J[k]+J[k+1], in 8-bit-equivalent DN per output
sample squared, separately at inserted and retained-source centers. "shape" removes
only each curvature image's ROI mean, while mean brightness curvature is reported
separately. Midpoint departure compares an insertion with the mean of its two
REGISTERED sources; this is not a ground truth. A piecewise-linear registered-source
control exposes the expected parity effect from source grain and genuine motion.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.signal import fftconvolve


def crop_arg(value):
    try:
        x, y, w, h = (int(v) for v in value.split(':'))
    except ValueError as exc:
        raise argparse.ArgumentTypeError('crop must be x:y:w:h') from exc
    if min(x, y) < 0 or min(w, h) < 16:
        raise argparse.ArgumentTypeError('crop origin must be nonnegative and size at least 16x16')
    return x, y, w, h


def probe(path, ffprobe):
    result = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'v:0',
                             '-show_entries', 'stream=width,height,avg_frame_rate',
                             '-of', 'json', str(path)], capture_output=True, check=True)
    streams = json.loads(result.stdout)['streams']
    if len(streams) != 1:
        raise ValueError(f'{path}: expected one selected video stream')
    s = streams[0]
    return int(s['width']), int(s['height']), Fraction(s['avg_frame_rate'])


def decode(path, first, count, crop, ffmpeg):
    x, y, w, h = crop
    vf = f'trim=start_frame={first}:end_frame={first + count},crop={w}:{h}:{x}:{y}'
    result = subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-i', str(path),
                             '-an', '-vf', vf, '-fps_mode', 'passthrough',
                             '-frames:v', str(count), '-pix_fmt', 'gray16le',
                             '-f', 'rawvideo', '-'], capture_output=True, check=True)
    a = np.frombuffer(result.stdout, dtype='<u2')
    if a.size != count * h * w:
        raise ValueError(f'{path}: decoded {a.size // (h*w)} frames, expected {count}; aborting')
    return a.reshape(count, h, w).astype(np.float32) / 65535.0


def patch(a, pos, size):
    w, h = size
    x, y = pos
    if x < 0 or y < 0 or x + w > a.shape[1] or y + h > a.shape[0]:
        raise ValueError('tracked crop left the decoded window')
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    return map_coordinates(a, [yy + y, xx + x], order=1, mode='nearest')


def translation(a, b, pos, size, args):
    """Bounded source-to-source normalized correlation, independent of renders."""
    w, h = size
    x, y = pos
    r = args.max_shift
    x0, y0 = max(0, int(np.floor(x-r))), max(0, int(np.floor(y-r)))
    x1 = min(b.shape[1]-w, int(np.ceil(x+r)))
    y1 = min(b.shape[0]-h, int(np.ceil(y+r)))
    if x1-x0 < 4 or y1-y0 < 4:
        return dict(valid=False, reasons=['insufficient_search_support'], position=list(pos))
    ta = patch(a, pos, size).astype(np.float64)
    search = b[y0:y1+h, x0:x1+w].astype(np.float64)
    t = ta-ta.mean()
    energy = float(np.sum(t*t))
    std_dn = float(np.std(ta)*255)
    if std_dn < args.min_texture_dn:
        return dict(valid=False, reasons=['low_texture'], texture_dn=std_dn, position=list(pos))
    kernel = np.ones((h, w), np.float64)
    sums = fftconvolve(search, kernel, mode='valid')
    squares = fftconvolve(search*search, kernel, mode='valid')
    variance = np.maximum(squares-sums*sums/(w*h), 0)
    numerator = fftconvolve(search, t[::-1, ::-1], mode='valid')
    corr = numerator / np.sqrt(np.maximum(energy*variance, 1e-20))
    iy, ix = np.unravel_index(np.argmax(corr), corr.shape)
    best = float(corr[iy, ix])
    yy, xx = np.mgrid[:corr.shape[0], :corr.shape[1]]
    rival = corr[(xx-ix)**2+(yy-iy)**2 >= args.ambiguity_radius**2]
    second = float(np.max(rival)) if rival.size else None
    gap = best-second if second is not None else 0.0
    sub = np.zeros(2)
    edge = ix in (0, corr.shape[1]-1) or iy in (0, corr.shape[0]-1)
    if not edge:
        gx = 0.5*(corr[iy, ix+1]-corr[iy, ix-1])
        gy = 0.5*(corr[iy+1, ix]-corr[iy-1, ix])
        hxx = corr[iy, ix+1]+corr[iy, ix-1]-2*best
        hyy = corr[iy+1, ix]+corr[iy-1, ix]-2*best
        hxy = 0.25*(corr[iy+1, ix+1]-corr[iy+1, ix-1]-corr[iy-1, ix+1]+corr[iy-1, ix-1])
        hessian = np.array([[hxx, hxy], [hxy, hyy]])
        if np.max(np.linalg.eigvalsh(hessian)) < -1e-9:
            sub = np.clip(-np.linalg.solve(hessian, [gx, gy]), -0.75, 0.75)
    new = np.array([x0+ix, y0+iy], float)+sub
    tb = patch(b, new, size).astype(np.float64)
    # Gain/offset are fitted ONLY to report registration quality. Output pixels
    # are never photometrically normalized for the temporal measurements.
    z = tb-tb.mean()
    gain = float(np.sum(t*z)/max(np.sum(z*z), 1e-20))
    offset = float(ta.mean()-gain*tb.mean())
    residual = float(np.sqrt(np.mean((ta-(gain*tb+offset))**2))*255)
    reasons = []
    if edge:
        reasons.append('peak_at_search_boundary')
    if best < args.min_corr:
        reasons.append('weak_correlation')
    if gap < args.min_peak_gap:
        reasons.append('ambiguous_translation')
    if residual > args.max_fit_dn:
        reasons.append('poor_rigid_fit')
    if not 0.5 <= gain <= 2:
        reasons.append('extreme_photometric_fit')
    return dict(valid=not reasons, reasons=reasons, position=new.tolist(),
                shift=(new-pos).tolist(), correlation=best, rival_correlation=second,
                peak_gap=gap, texture_dn=std_dn, fit_residual_dn=residual,
                raw_residual_dn=float(np.sqrt(np.mean((ta-tb)**2))*255),
                fitted_gain=gain, fitted_offset_dn=offset*255)


def track(source, origin, size, args):
    smooth = gaussian_filter(source, (0, args.fit_sigma, args.fit_sigma), mode='reflect')
    positions = [np.asarray(origin, float)]
    fits = []
    for i in range(len(source)-1):
        fit = translation(smooth[i], smooth[i+1], positions[-1], size, args)
        fit['source_pair'] = [args.start_frame+i, args.start_frame+i+1]
        fits.append(fit)
        if not fit['valid']:
            break  # reacquiring from an untrusted crop would propagate a false track
        positions.append(np.asarray(fit['position']))
    return np.asarray(positions), fits


def stats(a):
    if not a.size:
        return None
    return dict(rms_dn=float(np.sqrt(np.mean(a*a))*255),
                abs_p95_dn=float(np.percentile(np.abs(a), 95)*255),
                abs_p99_dn=float(np.percentile(np.abs(a), 99)*255))


def block_map(a, block):
    """RMS across time and each spatial tile; preserve the final partial tiles."""
    h, w = a.shape[1:]
    return np.array([[np.sqrt(np.mean(a[:, y:y+block, x:x+block]**2))*255
                      for x in range(0, w, block)] for y in range(0, h, block)], np.float32)


def describe(a, block):
    if not a.size:
        return None
    mean = a.mean(axis=(1, 2), keepdims=True)
    shape = a-mean
    tiles = block_map(shape, block)
    return dict(all=stats(a), spatially_nonuniform=stats(shape),
                roi_mean=stats(mean), block_shape_rms_p95_dn=float(np.percentile(tiles, 95)),
                block_shape_rms_max_dn=float(tiles.max()), frames=int(len(a)))


def metrics(render, source, edge, block):
    report, maps = {}, {}
    for sigma in (1, 2, 4):
        r = gaussian_filter(render, (0, sigma, sigma), mode='reflect')
        s = gaussian_filter(source, (0, sigma, sigma), mode='reflect')
        cut = (slice(None), slice(edge, -edge), slice(edge, -edge))
        d = (r[:-2]-2*r[1:-1]+r[2:])[cut]
        center = np.arange(1, len(r)-1)
        inserted, retained = d[center % 2 == 1], d[center % 2 == 0]
        departure_full = r[1::2]-0.5*(s[:-1]+s[1:])
        departure = departure_full[cut]
        change = np.diff(departure, axis=0)  # pixelwise, shared material coordinates
        spatial = (
            np.roll(departure_full, 1, 1)+np.roll(departure_full, -1, 1)
            +np.roll(departure_full, 1, 2)+np.roll(departure_full, -1, 2)-4*departure_full)
        report[str(sigma)] = dict(inserted_center=describe(inserted, block),
                                  retained_center=describe(retained, block),
                                  midpoint_departure=describe(departure, block),
                                  midpoint_departure_change=describe(change, block),
                                  departure_laplacian_rms_dn_per_px2=float(np.sqrt(np.mean(spatial[cut]**2))*255))
        for label, a in [('inserted', inserted), ('retained', retained), ('departure_change', change)]:
            if not a.size:
                continue
            shape = a-a.mean(axis=(1, 2), keepdims=True)
            maps[f'sigma{sigma}_{label}_shape_rms_dn'] = np.sqrt(np.mean(shape*shape, axis=0))*255
            maps[f'sigma{sigma}_{label}_block_shape_rms_dn'] = block_map(shape, block)
    return report, maps


def write_maps(out, name, maps, maximum):
    np.savez_compressed(out/f'{name}-maps.npz', **maps)
    for key, values in maps.items():
        if '_block_' in key:
            continue
        # Fixed, shared scale: black=0 DN, white=maximum DN. NPZ retains values.
        im = np.clip(values/maximum, 0, 1)*255
        pixels = np.rint(im).astype('uint8')
        height, width = pixels.shape
        def chunk(kind, body):
            data = kind+body
            return struct.pack('>I', len(body))+data+struct.pack('>I', zlib.crc32(data))
        scanlines = b''.join(b'\x00'+row.tobytes() for row in pixels)
        png = b'\x89PNG\r\n\x1a\n'
        png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))
        png += chunk(b'IDAT', zlib.compress(scanlines))+chunk(b'IEND', b'')
        (out/f'{name}-{key}.png').write_bytes(png)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('source', type=Path)
    p.add_argument('renders', nargs='+', type=Path)
    p.add_argument('--crop', required=True, type=crop_arg)
    p.add_argument('--start-frame', type=int, default=0)
    p.add_argument('--frames', required=True, type=int)
    p.add_argument('--margin', type=int, default=128)
    p.add_argument('--max-shift', type=int, default=32)
    p.add_argument('--fit-sigma', type=float, default=2)
    p.add_argument('--min-texture-dn', type=float, default=0.75)
    p.add_argument('--min-corr', type=float, default=0.65)
    p.add_argument('--min-peak-gap', type=float, default=0.01)
    p.add_argument('--ambiguity-radius', type=int, default=4)
    p.add_argument('--max-fit-dn', type=float, default=10)
    p.add_argument('--retained-tolerance-dn', type=float, default=0.5)
    p.add_argument('--edge', type=int, default=12, help='discard patch edge; at least 3*sigma_max')
    p.add_argument('--block', type=int, default=32)
    p.add_argument('--map-max-dn', type=float, default=8)
    p.add_argument('--max-decoded-mib', type=float, default=512)
    p.add_argument('--ffmpeg', default=str(Path.home()/'np-build/ffmpeg/ffmpeg'))
    p.add_argument('--ffprobe', default=shutil.which('ffprobe') or 'ffprobe')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    if args.frames < 4 or args.start_frame < 0 or args.margin < 0 or args.max_shift < 2:
        p.error('need >=4 source frames, nonnegative start/margin and max-shift >=2')
    if min(args.crop[2:]) <= 2*args.edge or args.edge < 12 or args.block < 1:
        p.error('edge must be >=12 and smaller than half the crop, block positive')
    if args.fit_sigma <= 0 or args.map_max_dn <= 0 or args.max_decoded_mib <= 0:
        p.error('sigma, map scale and memory limit must be positive')
    if len({q.stem for q in args.renders}) != len(args.renders):
        p.error('render filename stems must be distinct')
    if any(q.stem == 'registered-linear-control' for q in args.renders):
        p.error('registered-linear-control is a reserved render name')
    width, height, rate = probe(args.source, args.ffprobe)
    x, y, w, h = args.crop
    if x+w > width or y+h > height:
        p.error('crop exceeds the source image')
    x0, y0 = max(0, x-args.margin), max(0, y-args.margin)
    x1, y1 = min(width, x+w+args.margin), min(height, y+h+args.margin)
    # Chroma-subsampled decoders can round odd crop origins. Align the decode
    # rectangle to even coordinates; the tracked grayscale ROI keeps exact pixels.
    x0, y0 = x0//2*2, y0//2*2
    x1, y1 = min(width, (x1+1)//2*2), min(height, (y1+1)//2*2)
    decoded = (x0, y0, x1-x0, y1-y0)
    memory = (3*args.frames-1)*decoded[2]*decoded[3]*4/2**20
    if memory > args.max_decoded_mib:
        p.error(f'bounded decoded arrays require {memory:.1f} MiB, over limit {args.max_decoded_mib}')
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'temporal.json').write_text(json.dumps(dict(execution_status='incomplete',
                                                         source=str(args.source)))+'\n')
    source = decode(args.source, args.start_frame, args.frames, decoded, args.ffmpeg)
    positions, fits = track(source, (x-x0, y-y0), (w, h), args)
    n = len(positions)
    report = dict(schema=1, kind='native_2x_diagnostic_not_ground_truth',
                  source=str(args.source), source_rate=str(rate),
                  crop_at_first_selected_source=list(args.crop), decoded_crop=list(decoded),
                  requested_source_frames=args.frames, accepted_source_frames=n,
                  tracking_status='complete' if n == args.frames else 'unknown_after_rejected_pair',
                  fits=fits, positions_in_decoded_crop=positions.tolist(),
                  settings={k: v for k, v in vars(args).items() if k not in {'source', 'renders', 'out'}},
                  limitations=['Translation only: true cloth deformation can invalidate tracking or create curvature.',
                               'Independent film grain creates parity curvature even for a benign linear interpolator.',
                               'Subpixel registration resampling can change grain variance between parity classes.',
                               'Native insertions have no truth; a smaller diagnostic value does not prove better quality.',
                               'ROIs must exclude silhouette, collar, arms and occlusions; this tracker cannot identify them.',
                               'Frame alignment is checked by retained-source pixel agreement, not only rate metadata.'],
                  renders={})
    args.out.mkdir(parents=True, exist_ok=True)
    if n >= 4:
        registered_source = np.stack([patch(source[i], pos, (w, h)) for i, pos in enumerate(positions)])
        out_positions = np.empty((2*n-1, 2))
        out_positions[::2] = positions
        out_positions[1::2] = 0.5*(positions[:-1]+positions[1:])
        control = np.empty((2*n-1, h, w), np.float32)
        control[::2] = registered_source
        control[1::2] = 0.5*(registered_source[:-1]+registered_source[1:])
        scores, maps = metrics(control, registered_source, args.edge, args.block)
        report['registered_linear_control'] = scores
        write_maps(args.out, 'registered-linear-control', maps, args.map_max_dn)
        for path in args.renders:
            rw, rh, rr = probe(path, args.ffprobe)
            # Matroska's millisecond clock can report a nearby rational rate.
            # This permits only metadata rounding; retained pixels below still
            # have to prove the requested source/render frame correspondence.
            if (rw, rh) != (width, height) or abs(float(rr/(2*rate))-1) > 1e-5:
                raise ValueError(f'{path}: expected source dimensions and 2x rate, got {(rw, rh, str(rr))}')
            render = decode(path, 2*args.start_frame, 2*n-1, decoded, args.ffmpeg)
            retained_error = np.abs(render[::2]-source[:n])*255
            retained_mae = retained_error.mean(axis=(1, 2))
            if float(retained_mae.max()) > args.retained_tolerance_dn:
                raise ValueError(f'{path}: retained-source MAE {retained_mae.max():.4f} DN exceeds tolerance; alignment/color pipeline unverified')
            registered = np.stack([patch(render[i], pos, (w, h)) for i, pos in enumerate(out_positions)])
            scores, maps = metrics(registered, registered_source, args.edge, args.block)
            report['renders'][path.stem] = dict(path=str(path), reported_rate=str(rr), retained_mae_max_dn=float(retained_mae.max()),
                                               source_frames=n, output_frames=2*n-1, scales=scores)
            write_maps(args.out, path.stem, maps, args.map_max_dn)
    else:
        report['measurement_status'] = 'unknown: fewer than four trusted source frames; no render scored'
    report['execution_status'] = 'complete'
    (args.out/'temporal.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(output=str(args.out/'temporal.json'), accepted_source_frames=n,
                         requested_source_frames=args.frames, tracking_status=report['tracking_status'],
                         renders=list(report['renders'])), indent=2))
    return report


if __name__ == '__main__':
    main()
