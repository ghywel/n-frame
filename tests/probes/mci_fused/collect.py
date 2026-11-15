#!/usr/bin/env python3
"""Path-free numbers from this block's external evidence, for the repository (media and raw records stay outside).

    collect.py OUT.json label=rawbench.json ... [--bench label=bench-summary.json ...] [--checks label=check-summary.json ...]

rawbench.json: medians and the wall samples of every variant. bench-summary.json (GPT's bench): medians and ranges.
check-summary.json (GPT's gate): the count of comparisons and how many were exact. Nothing is rerun.
"""
import json
import sys


def raw(path):
    j = json.load(open(path))
    out = dict(binaries=j['binaries'], host=j['host'], rounds=j['rounds'], sink=j['sink'], source=j['source'], cases={})
    for name, c in j['cases'].items():
        out['cases'][name] = dict(output_frames=c['output_frames'], source_seconds=c['source_seconds'],
                                  median=c['median'], wall_samples={k: [x['wall'] for x in v] for k, v in c['samples'].items()})
    return out


def bench(path):
    j = json.load(open(path))
    rows = []
    for r in j['rows']:
        row = dict(case=r['case'], mask=r['mask'], threads=r['threads'], wall_speedup=r['wall_speedup'])
        for role in ('baseline', 'candidate'):
            row[role] = {k: {s: r['roles'][role][k][s] for s in ('median', 'minimum', 'maximum')}
                         for k in ('wall_seconds', 'user_seconds', 'me_us', 'overlap_us', 'output_us')}
        rows.append(row)
    return dict(binary_sha256=j['binary_sha256'], sink=j['sink'], rows=rows)


def check(path):
    j = json.load(open(path))
    rows = j['rows']
    return dict(status=j['execution_status'], comparisons=len(rows), exact=sum(1 for r in rows if r['exact'] is True),
                configs=sorted({f"{r['mask']}:{r['threads']}" for r in rows}), cases=sorted({r['case'] for r in rows}),
                mb_sizes=sorted({r['mb_size'] for r in rows}))


def main():
    out, mode, result = sys.argv[1], raw, dict(raw={}, bench={}, checks={})
    key = 'raw'
    for a in sys.argv[2:]:
        if a in ('--bench', '--checks'):
            key, mode = a[2:], dict(bench=bench, checks=check)[a[2:]]
            continue
        label, path = a.split('=', 1)
        result[key][label] = mode(path)
    json.dump(result, open(out, 'w'), indent=1, sort_keys=True)
    print('collected', {k: len(v) for k, v in result.items()})


if __name__ == '__main__':
    main()
