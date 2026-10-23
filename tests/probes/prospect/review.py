#!/usr/bin/env python3
"""Inspect prospecting candidates, then confirm chosen events at native size.

review.py sheets OUT [ID]             all ranked events; columns ref/High/linear
review.py confirm OUT ID FRAME        3 s native window, High twice and linear
review.py timing OUT                  decoded native PTS cadence, local only

Uses the same frozen scorer and exact input-frame parity. Native confirmations
are separate observations; do not transfer a width-640 diagnosis automatically.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
import reconstruct as r


def sheets(root, candidates=None, name='sheet'):
    if candidates is None:
        candidates = json.loads((root/'ranked.json').read_text())['candidates']
    by_frame = {x['frame']: x for x in candidates}
    ns = sorted(by_frame)
    if not ns:
        return
    expr = '+'.join(f'eq(n,{n})' for n in ns)
    filters = [f"[{i}:v]select='{expr}',setpts=N/TB,scale=640:-2,setsar=1[x{i}]" for i in range(3)]
    filters += [f'[x0][x1][x2]hstack=inputs=3,tile=1x{len(ns)}[o]']
    cmd = [r.FF, '-nostdin', '-y', '-v', 'warning']
    for n in ['ref', 'high', 'linear']:
        cmd += ['-i', str(root/f'{n}.mkv')]
    cmd += ['-filter_complex', ';'.join(filters), '-map', '[o]', '-frames:v', '1', '-update', '1', str(root/f'{name}.png')]
    r.call(cmd, root, f'{name}.log')
    r.save(root/f'{name}.json', dict(columns=['withheld original', 'High', 'linear'],
                                     rows=[by_frame[n] for n in ns]))


def confirm(out, sid, n):
    src = next(x for x in json.loads((out/'sources.json').read_text()) if x['id'] == sid)
    parent = out/sid; root = parent/f'native-{n}'
    root.mkdir(exist_ok=True)
    rate = src['meta']['r_frame_rate']; fps = float(Fraction(rate))
    start = max(0, (n - round(fps*1.5))//2*2)
    length = round(fps*3)//2*2
    r.call([r.FF, '-nostdin', '-y', '-v', 'warning', '-i', str(parent/'native.mkv'), '-vf',
            f'trim=start_frame={start}:end_frame={start+length},setpts=N/({rate})/TB', '-frames:v', str(length),
            '-an', '-sn', '-c:v', 'ffv1', str(root/'native.mkv')], root, 'extract.log')
    w, h = r.prepare(root, rate, 16384)
    shutil.copyfile(parent/'high.glsl', root/'high.glsl')
    for name in ['linear', 'high', 'high2']:
        r.render(root, rate, name)
    one = r.measure(root, w, h, rate)
    two = r.measure(root, w, h, rate, high='high2')
    a = next(x for x in one['rows'] if x['frame'] == n-start)
    b = next(x for x in two['rows'] if x['frame'] == n-start)
    r.shortlist(one); r.shortlist(two)
    diff = []
    for x, y in zip(r.frames(root/'high.mkv', w, h), r.frames(root/'high2.mkv', w, h), strict=True):
        diff.append(r.rms(x, y))
    result = dict(source_id=sid, source_local_frame=n, confirmation_start_frame=start,
                  original_seconds=src['start']+n/fps, candidate=a, repeat_candidate=b,
                  repeat_max_rms=max(diff), repeat_median_rms=float(np.median(diff)),
                  width=w, height=h, count=one['frames'], retained_max=one['retained_max'])
    r.save(root/'confirmation.json', result)
    # Show candidate and its two neighbouring withheld moments as context.
    sheets(root, [x for x in one['rows'] if x['frame'] in (n-start-2, n-start, n-start+2)], 'native-sheet')
    r.call([r.FF, '-nostdin', '-y', '-v', 'warning', '-i', str(root/'ref.mkv'), '-vf',
            f"select='between(n,{n-start-1},{n-start+1})',scale=640:-2,setsar=1,tile=3x1",
            '-frames:v', '1', '-update', '1', str(root/'source-triplet.png')], root, 'source-triplet.log')
    print(json.dumps(result), flush=True)


def timing(out):
    result = {}
    for src in json.loads((out/'sources.json').read_text()):
        p = out/src['id']/'native.mkv'
        text = subprocess.run([r.FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                               'packet=pts_time', '-of', 'csv=p=0', str(p)],
                              capture_output=True, text=True, check=True).stdout
        times = np.array([float(x) for x in text.splitlines() if x.strip()])
        dt = np.diff(times); period = 1/float(Fraction(src['meta']['r_frame_rate']))
        # FFV1 has one frame per packet, no frame reordering. Millisecond
        # Matroska rounding is tolerated; a dropped/duplicated interval is not.
        ok = bool(np.all(np.abs(dt-period) < .0011))
        result[src['id']] = dict(frames=len(times), min_dt=float(dt.min()), max_dt=float(dt.max()),
                                 nominal_period=period, cfr_with_ms_rounding=ok)
        if not ok:
            raise ValueError(f'{src["id"]}: cadence refusal; see native packet PTS')
    r.save(out/'cadence-check.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['sheets', 'confirm', 'timing'])
    p.add_argument('out', type=Path)
    p.add_argument('id', nargs='?')
    p.add_argument('frame', type=int, nargs='?')
    a = p.parse_args(); out = a.out.resolve()
    if a.command == 'timing':
        timing(out)
    elif a.command == 'confirm':
        confirm(out, a.id, a.frame)
    else:
        for path in sorted(out.glob('*/ranked.json')):
            if not a.id or path.parent.name == a.id:
                sheets(path.parent)
