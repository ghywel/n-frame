#!/usr/bin/env python3
"""Coloured edge fixtures for the MCI exactness gate (PLAN.md, F5's finding).

    colour_fixtures.py OUT --source FILM.mkv --ffmpeg FFMPEG [--start 60]

GPT's small fixtures (../mci_accel/gate.py prepare) are grey: U = V = 128 everywhere, so a chroma error in them is
invisible, and both odd-size border cases are among them. These are 24-frame crops of a cached 1080p film window with
real chroma, at sizes and samplings that put chroma cells on the frame's edge: 638x358 4:2:0 (odd chroma rows),
637x357 4:2:0 (a one-pixel-wide and one-pixel-high last cell), 639x359 4:4:4, 638x359 4:2:2 and 639x358 4:4:0, and the
first again at 60 fps (phases off the midpoint). The manifest has gate.py's format, so `gate_fused.py check
--fixtures OUT/fixtures.json` runs them. Media stays outside the repository.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

CASES = {   # name: (width, height, pix_fmt, crop x, crop y, output rate)
    'colour420':     (638, 358, 'yuv420p', 641, 361, '48000/1001'),
    'colour420odd':  (637, 357, 'yuv420p', 901, 301, '48000/1001'),
    'colour444':     (639, 359, 'yuv444p', 641, 361, '48000/1001'),
    'colour422':     (638, 359, 'yuv422p', 1101, 421, '48000/1001'),
    'colour440':     (639, 358, 'yuv440p', 321, 501, '48000/1001'),
    'colour420_60':  (638, 358, 'yuv420p', 641, 361, '60000/1001'),
}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--ffmpeg', required=True)
    ap.add_argument('--start', type=int, default=60)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    manifest = a.out / 'fixtures.json'
    assert not manifest.exists(), 'fixtures are immutable: use a fresh directory'
    cases = {}
    for name, (w, h, fmt, x, y, out_rate) in CASES.items():
        path = (a.out / f'{name}.mkv').resolve()
        # through 4:4:4 so an odd crop origin is exact for every target sampling; fixed swscale flags
        vf = (f'trim=start_frame={a.start}:end_frame={a.start + 24},scale=flags=bicubic+accurate_rnd+full_chroma_int,'
              f'format=yuv444p,crop={w}:{h}:{x}:{y}:exact=1,scale=flags=bicubic+accurate_rnd+full_chroma_int,'
              f'format={fmt},settb=expr=1/24000,setpts=N*1001')
        cmd = [a.ffmpeg, '-nostdin', '-y', '-v', 'error', '-threads', '1', '-filter_threads', '1', '-i',
               str(a.source.resolve()), '-map', '0:v:0', '-an', '-vf', vf, '-frames:v', '24', '-c:v', 'ffv1',
               '-level', '3', '-threads', '1', '-pix_fmt', fmt, str(path)]
        subprocess.run(cmd, check=True)
        cases[name] = dict(width=w, height=h, pix_fmt=fmt, frames=24, rate='24000/1001', output_rate=out_rate,
                           path=str(path), sha256=sha(path), original_source=str(a.source.resolve()),
                           original_source_sha256=sha(a.source), preparation_command=cmd,
                           preparation_command_sha256=hashlib.sha256(
                               json.dumps(cmd, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
    manifest.write_text(json.dumps(dict(schema=1, execution_status='complete', preparer_ffmpeg=a.ffmpeg,
                                        preparer_ffmpeg_sha256=sha(a.ffmpeg), cases=cases), indent=2) + '\n')
    print('prepared', ', '.join(cases))


if __name__ == '__main__':
    main()
