#!/usr/bin/env python3
"""Extract complete stress/ladder/real evidence without decoding or rendering.

    summarize.py SCRATCH_ROOT [--require-timing]

Reads individual per-case JSONs, never the overwrite-prone synthetic summary.json.
Missing cases, labels, inconsistent hashes/counts or broken stored arithmetic fail.
Writes review-summary.json and review-summary.md under SCRATCH_ROOT only.
Timing may be pending unless --require-timing is supplied. Standard library only.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics

ORIGINAL = ('face_static', 'face_slow', 'face_fast', 'face_counterpan', 'face_occluded',
            'face_lowcontrast', 'pan_detail', 'pan_mixed', 'bars_v9', 'bars_v24',
            'bars_h9', 'bars_h24', 'bars_diagonal', 'bars_static')
ROUND2 = ORIGINAL + ('pan_detail37', 'pan_detail43', 'pan_mixed45')
PHOTOS = ('photo_fast', 'photo_counterpan')
REAL = ('film1-2986.7', 'film1-3055.7', 'tv1-216.0', 'tv1-241.1', 'cg1-862.4', 'cg1-947.9')
ROOT = Path(__file__).resolve().parents[3]
METRICS = ('psnr', 'roi_psnr', 'feature_psnr', 'feature_bad_05', 'roi_worst_1pct_rms_dn')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path, evidence, root):
    require(path.is_file(), f'Missing required evidence: {path}')
    raw = path.read_bytes()
    evidence[str(path.relative_to(root))] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def finite_numbers(values, name):
    require(all(isinstance(v, (int, float)) and math.isfinite(v) for v in values), f'{name}: invalid numeric value')


def stress(root, folder, cases, labels, evidence, hashes):
    result = {}
    for name in cases:
        scores = {}
        for label in labels:
            r = read(folder/name/f'{label}.json', evidence, root)
            finite_numbers([r[k] for k in METRICS]+[r['retained_rms_dn']], f'{name}/{label}')
            require(r['frames'] == len(r['rows']) == 16, f'{name}/{label}: expected 16 scored frames')
            require([x['frame'] for x in r['rows']] == [k for k in range(5, 25) if k % 5],
                    f'{name}/{label}: unexpected scored indices')
            require(r['retained_rms_dn'] < 2.55, f'{name}/{label}: alignment fails')
            for metric, rowkey in (('psnr','mse'), ('roi_psnr','roi_mse'), ('feature_psnr','feature_mse')):
                mean = statistics.mean(x[rowkey] for x in r['rows'])
                actual = -10*math.log10(max(mean, 1e-16))
                require(abs(r[metric]-actual) < 1e-4, f'{name}/{label}: {metric} arithmetic mismatch')
            actual = math.sqrt(statistics.mean(x['roi_worst_1pct_mse'] for x in r['rows']))*255
            require(abs(actual-r['roi_worst_1pct_rms_dn']) < 1e-4, f'{name}/{label}: tail arithmetic mismatch')
            sh = r['shader_sha256']
            require(sh == hashes.setdefault(label, sh), f'{name}/{label}: shader identity changed between cases')
            scores[label] = {k:r[k] for k in METRICS}
            scores[label]['retained_rms_dn'] = r['retained_rms_dn']
        high = scores['high']
        for label in labels:
            if label == 'high': continue
            scores[label]['delta_from_high'] = {k: scores[label][k]-high[k] for k in METRICS}
            scores[label]['tail_change_percent'] = 100*(scores[label]['roi_worst_1pct_rms_dn']/high['roi_worst_1pct_rms_dn']-1)
        result[name] = scores
    return result


def ladder(root, label, evidence):
    r = read(root/'ladder'/f'{label}-comparison.json', evidence, root)
    spec = importlib.util.spec_from_file_location('ladder_sets', ROOT/'tests/ladder_sets.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    names = [c['case'] for c in r['cases']]
    require(len(names) == len(set(names)) == 45, f'{label}: expected 45 unique ladder cases')
    require(set(names) == set(mod.frozen())|set(mod.headline()), f'{label}: wrong ladder case set')
    require(r['variant'] == label, f'{label}: wrong variant identity')
    result = {}
    for key in ('frame', 'frame_interior', 'region', 'region_interior'):
        rows = []
        for c in r['cases']:
            s = c[key]
            finite_numbers((s['high'], s['variant'], s['delta']), f'{label}/{c["case"]}/{key}')
            require(s['frames'] == (42 if 'interior' in key else 44), f'{label}/{key}: unexpected count')
            require(abs(s['variant']-s['high']-s['delta'])<1e-6, f'{label}/{key}: delta mismatch')
            rows.append(dict(case=c['case'], **s))
        byname = {v['case']:v for v in rows}
        summaries = {}
        for scope, nameset in (('headline',mod.headline()),('frozen',mod.frozen())):
            a = statistics.mean(min(byname[n]['high'],40) for n in nameset)
            b = statistics.mean(min(byname[n]['variant'],40) for n in nameset)
            summaries[scope] = dict(high_capped_mean=a, variant_capped_mean=b, delta=b-a)
        result[key] = dict(cases=rows, worst=sorted(rows,key=lambda v:v['delta'])[:5],
                           losses_over_01=sum(v['delta']<-.1 for v in rows),
                           losses_over_1=sum(v['delta']<-1 for v in rows), means=summaries)
    return result


def real(root, evidence, hashes):
    r = read(root/'real/scores.json', evidence, root)
    require(set(r) == set(REAL), 'real: expected six registered cached windows')
    rows = {}
    for case, values in r.items():
        require(set(values) == {'high','combined'}, f'real/{case}: wrong shader labels')
        for label, s in values.items():
            finite_numbers([s[k] for k in ('psnr','ssim8','worst1pct_rms_dn','alignment_rms_dn')], f'real/{case}/{label}')
            require(s['alignment_rms_dn']<2.55 and s['frames'] in (32,33), f'real/{case}/{label}: alignment/count')
            require(s['source_frames']==(s['reference_frames']+1)//2,
                    f'real/{case}/{label}: half-input/reference count mismatch')
            require(s['output_frames']==2*s['source_frames'], f'real/{case}/{label}: output length')
            require(s['shader_sha256']==hashes[label], f'real/{case}/{label}: shader mismatch')
        a,b=values['high'],values['combined']
        rows[case] = dict(high_psnr=a['psnr'], delta_psnr=b['psnr']-a['psnr'],
                          delta_ssim8=b['ssim8']-a['ssim8'],
                          tail_change_percent=100*(b['worst1pct_rms_dn']/a['worst1pct_rms_dn']-1))
    return rows


def markdown(result):
    lines=['# Motion stress evidence extraction', '',
           'All values read from complete per-case records; no GPU or decoding rerun.',
           'PSNR deltas are dB; negative tail change is better. Ladder means preserve its per-frame-PSNR convention.', '']
    for group in ('original','round2','photos'):
        rows=result[group]
        primary='combined' if group!='original' else 'inverse2'
        lines += [f'## {group}: {primary} versus High', '',
                  '| Case | High feature dB | Frame delta | ROI delta | Feature delta | Tail RMS change % |',
                  '|---|---:|---:|---:|---:|---:|']
        for name,r in rows.items():
            d=r[primary]['delta_from_high']
            lines += [f"| {name} | {r['high']['feature_psnr']:.3f} | {d['psnr']:+.3f} | {d['roi_psnr']:+.3f} | {d['feature_psnr']:+.3f} | {r[primary]['tail_change_percent']:+.2f} |"]
        lines += ['']
    lines += ['## Round-two feature ablation', '', '| Case | Inverse-data | Global-fullres | Combined |', '|---|---:|---:|---:|']
    for name,r in result['round2'].items():
        vals=' | '.join(f"{r[k]['delta_from_high']['feature_psnr']:+.3f}" for k in ('inverse-data','global-fullres','combined'))
        lines += [f'| {name} | {vals} |']
    lines += ['', '## Ladder', '', '| Variant / reading | Worst case | Worst delta | Losses >0.1 dB | Losses >1 dB | Headline capped delta | Frozen capped delta |', '|---|---|---:|---:|---:|---:|---:|']
    for name,r in result['ladder'].items():
        for key,s in r.items():
            w=s['worst'][0]
            lines += [f"| {name} / {key} | {w['case']} | {w['delta']:+.3f} | {s['losses_over_01']} | {s['losses_over_1']} | {s['means']['headline']['delta']:+.3f} | {s['means']['frozen']['delta']:+.3f} |"]
    lines += ['', '## Six cached real windows', '', '| Window | High PSNR | Delta PSNR | Delta SSIM8 | Tail RMS change % |', '|---|---:|---:|---:|---:|']
    for name,r in result['real'].items():
        lines += [f"| {name} | {r['high_psnr']:.3f} | {r['delta_psnr']:+.3f} | {r['delta_ssim8']:+.6f} | {r['tail_change_percent']:+.2f} |"]
    t=result['timing']
    lines += ['', '## Timing', '']
    if t['status']=='pending': lines += ['Timing pending; no cost claim yet.']
    else:
        lines += [f"High {t['high']['median_ms_per_output']:.3f} ms/output; combined {t['combined']['median_ms_per_output']:.3f} ms/output; change {t['change_percent']:+.2f}%.", '', t['scope']]
    lines += ['', f"Original/round-two High maximum feature-PSNR difference: {result['baseline_repeat_max_feature_db']:.6f} dB.", '']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    p.add_argument('--require-timing',action='store_true');args=p.parse_args()
    root=args.root.resolve();evidence={};hashes={}
    result={}
    result['original']=stress(root,root,ORIGINAL,('high','inverse2','linear'),evidence,hashes)
    result['round2']=stress(root,root/'round2',ROUND2,('high','inverse-data','global-fullres','combined'),evidence,hashes)
    result['photos']=stress(root,root/'photos',PHOTOS,('high','inverse2','inverse-data','combined'),evidence,hashes)
    result['baseline_repeat_max_feature_db']=max(abs(result['original'][c]['high']['feature_psnr']-result['round2'][c]['high']['feature_psnr']) for c in ORIGINAL)
    result['ladder']={v:ladder(root,v,evidence) for v in ('inverse2','combined')}
    result['real']=real(root,evidence,hashes)
    timing=root/'timing/timing.json'
    if timing.exists():
        t=read(timing,evidence,root)
        for k in ('high','combined'):
            require(len(t[k]['seconds'])==3 and min(t[k]['seconds'])>0, f'{k}: incomplete timing')
            require(abs(statistics.median(t[k]['seconds'])-t[k]['median_seconds'])<1e-6,f'{k}: wrong timing median')
        result['timing']=dict(t,status='complete',change_percent=100*(t['combined']['median_seconds']/t['high']['median_seconds']-1))
    else:
        require(not args.require_timing,'Timing missing; --require-timing refuses partial report')
        result['timing']=dict(status='pending')
    result['shader_hashes']=hashes;result['source_json_sha256']=evidence
    (root/'review-summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (root/'review-summary.md').write_text(markdown(result))
    print(f"Validated {len(evidence)} evidence JSON files; 14 original +17 round-two +2 photo cases, two 45-case ladder comparisons, six real windows. Timing {result['timing']['status']}.")


if __name__=='__main__': main()
