#!/usr/bin/env python3
"""The filter with nothing else in the way: a raw source and a null sink (PLAN.md, the timing note).

    rawbench.py OUT --fixtures FIXTURES.json --baseline STOCK_FFMPEG --candidate FFMPEG --prep-ffmpeg FFMPEG
                [--cases shirt,suit] [--configs 15:4,19:1,19:4,19:8] [--rounds 5]

GPT's bench (../mci_accel/gate.py bench) times the whole registered pipeline: FFV1 decoded on one thread, the filter,
and an MD5 of every output frame. Once the filter is fast those two set the wall time (about 27 ms a decoded 1080p
frame), so the pipeline no longer measures the filter. This keeps gate.py's filter chain and frame cap exactly and
changes the two ends only: the same frames stored uncompressed (prepared once here), and `-f null`.

Before any timing every variant is run once on the raw source into framemd5 and must equal stock's records; a
variant that differs is refused. Then one warm-up and N interleaved rounds per variant: process wall time, child
CPU time and the filter's own MCI_PROFILE stage times; peak resident memory from one further run each
(a helper process's ru_maxrss). One process at a time.
"""
import argparse
import importlib.util
import json
import os
import re
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location('gate', Path(__file__).resolve().parents[1] / 'mci_accel' / 'gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def raw_case(case, name, out, prep):
    path = out / f'{name}-raw.mkv'
    if not path.exists():
        subprocess.run([prep, '-nostdin', '-y', '-v', 'error', '-i', case['path'], '-map', '0:v:0', '-an', '-c:v',
                        'rawvideo', '-pix_fmt', case['pix_fmt'], '-fps_mode', 'passthrough', str(path)], check=True)
    return dict(case, path=str(path))


def command(binary, case, threads, mask, sink):
    cmd = gate.command(binary, case, threads, mask, 16)
    assert cmd[-3:] == ['-f', 'framemd5', '-']
    return cmd if sink == 'framemd5' else cmd[:-2] + ['null', '-']


def run(cmd):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t = time.monotonic()
    p = subprocess.run(cmd, capture_output=True)
    wall = time.monotonic() - t
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    assert p.returncode == 0, p.stderr.decode()[-600:]
    prof = [m for m in gate.PROFILE.finditer(p.stderr.decode()) if int(m.group(1))]
    assert len(prof) == 1, 'expected one active MCI_PROFILE'
    stage = dict(zip(gate.PROFILE_KEYS, map(int, prof[0].groups())))
    return dict(wall=wall, cpu=(after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime), **stage), p.stdout


def peak_rss(cmd):
    """Peak resident memory of one run, bytes: the run is the only child of a fresh helper process, whose
    children's ru_maxrss is then this run's alone (bytes on macOS, KiB on Linux). Not part of the timed rounds."""
    code = ('import resource,subprocess,sys;p=subprocess.run(sys.argv[1:],capture_output=True);'
            'print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if p.returncode==0 else -1)')
    value = int(subprocess.run([sys.executable, '-c', code] + cmd, capture_output=True).stdout or -1)
    return None if value < 0 else value * (1 if sys.platform == 'darwin' else 1024)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--fixtures', type=Path, required=True)
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--prep-ffmpeg', required=True)
    ap.add_argument('--cases', default='shirt,suit')
    ap.add_argument('--configs', default='15:4,19:1,19:4,19:8')
    ap.add_argument('--rounds', type=int, default=5)
    ap.add_argument('--no-stock-timing', action='store_true',
                    help='stock gives the exactness reference only (its time is known from an earlier run)')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    fixtures = json.loads(a.fixtures.read_text())['cases']
    variants = [('stock', a.baseline, None, 1)]
    for item in a.configs.split(','):
        mask, threads = map(int, item.split(':'))
        variants.append((f'm{mask}-t{threads}', a.candidate, mask, threads))
    result = dict(binaries=dict(baseline=gate.sha(a.baseline), candidate=gate.sha(a.candidate)),
                  host=gate.host(), sink='null', source='rawvideo in matroska', rounds=a.rounds, cases={})
    for name in a.cases.split(','):
        case = raw_case(fixtures[name], name, a.out, a.prep_ffmpeg)
        rows = {}
        reference = None
        for label, binary, mask, threads in variants:          # exactness on the raw source first
            _, out = run(command(binary, case, threads, mask, 'framemd5'))
            records = [l.split(',')[-1].strip() for l in out.decode().split('\n') if l and not l.startswith('#')]
            assert len(records) == gate.output_count(case), (label, len(records))
            if reference is None:
                reference = records
            assert records == reference, f'{name} {label}: differs from stock on the raw source; not timed'
            if label == 'stock' and a.no_stock_timing:
                continue
            rows[label] = []
            run(command(binary, case, threads, mask, 'null'))   # warm-up, discarded
            print('exact+warm', name, label, flush=True)
        for r in range(a.rounds):
            order = variants if r % 2 == 0 else variants[::-1]
            for label, binary, mask, threads in order:
                if label in rows:
                    rows[label].append(run(command(binary, case, threads, mask, 'null'))[0])
            print('round', name, r, flush=True)
        frames, seconds = gate.output_count(case), float(case['frames'] / gate.Fraction(case['rate']))
        peak = {label: peak_rss(command(binary, case, threads, mask, 'null'))
                for label, binary, mask, threads in variants if label in rows}
        summary = {}
        for label, ms in rows.items():
            med = {k: statistics.median(x[k] for x in ms) for k in ms[0]}
            med.update(wall_min=min(x['wall'] for x in ms), wall_max=max(x['wall'] for x in ms),
                       output_fps=frames / med['wall'], realtime_factor=seconds / med['wall'],
                       filter_ms_per_pair=(med['me_us'] + med['overlap_us'] + med['output_us']) / 1000 / med['pairs'],
                       peak_rss_bytes=peak[label])
            summary[label] = med
        result['cases'][name] = dict(output_frames=frames, source_seconds=seconds, samples=rows, median=summary)
        (a.out / 'rawbench.json').write_text(json.dumps(result, indent=1) + '\n')
    for name, c in result['cases'].items():
        for label, m in c['median'].items():
            print(f"{name:6s} {label:8s} wall {m['wall']:7.3f} s ({m['wall_min']:.3f}-{m['wall_max']:.3f})  cpu {m['cpu']:7.2f} s  "
                  f"x{m['realtime_factor']:5.2f} real time  filter {m['filter_ms_per_pair']:6.2f} ms/pair  "
                  f"me {m['me_us']/1e6:.3f} overlap {m['overlap_us']/1e6:.3f} output {m['output_us']/1e6:.3f}  "
                  f"peak {(m['peak_rss_bytes'] or 0)/2**20:.0f} MiB")


if __name__ == '__main__':
    main()
