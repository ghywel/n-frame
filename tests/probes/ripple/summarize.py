#!/usr/bin/env python3
"""Validate and compact the registered ripple experiment without decoding video.

  summarize.py SCRATCH --initial-video-defect-confirmed

Writes review-summary.json and review-summary.md under SCRATCH (or --out-dir).
The required original, Newton and AA groups must be complete. Optional OBMC is
pending until both corresponding score files are complete; a malformed completed
file fails. Every duplicate prev record must match exactly. Scores are checked
against their per-frame arithmetic, renderer counts, retained-frame checks and
shader hashes. No absolute input paths enter the portable output.

The explicit human-observation flags separately record the initial defect
confirmation, the owner's calmer-MCI-shirt verdict and the no-clear-OBMC-gain verdict.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import statistics


CASES = {'shirt': (119, [240, 230, 700, 620]), 'suit': (143, [160, 80, 960, 800])}
ORIGINAL = ['high', 'prev', 'vote-nearest', 'prev-no-fallback', 'linear',
            'prev-e-temporal-off', 'prev-h-data-refine-off', 'prev-inverse2']
GROUPS = [('original', '', ORIGINAL), ('newton', '-newton', ['prev', 'prev-newton']),
          ('aa', '-aa', ['prev', 'prev-aa-box']), ('obmc', '-obmc', ['prev', 'prev-obmc8'])]
ODD = list(range(49, 96, 2))
EVEN = list(range(50, 95, 2))
FRAME_COLUMNS = ['source_frame', 'raw_psnr_db', 'sigma2_psnr_db', 'sigma2_gradient_rms_dn_per_px',
                 'raw_worst_1pct_rms_dn', 'sigma2_worst_1pct_rms_dn',
                 'raw_worst_tile_rms_dn', 'raw_worst_tile_x', 'raw_worst_tile_y',
                 'raw_worst_tile_width', 'raw_worst_tile_height',
                 'sigma2_worst_tile_rms_dn', 'sigma2_worst_tile_x', 'sigma2_worst_tile_y',
                 'sigma2_worst_tile_width', 'sigma2_worst_tile_height']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    require(path.is_file(), f'missing required input: {path.name}')
    return json.loads(path.read_text())


def close(a, b, context, tolerance=1e-8):
    require(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance*max(1, abs(a), abs(b)),
            f'{context}: inconsistent arithmetic ({a} versus {b})')


def rate(actual, expected, context):
    close(float(Fraction(actual)/Fraction(expected)), 1, context, 1e-5)


def finite(value, context='data'):
    if isinstance(value, dict):
        for k, v in value.items():
            finite(v, context+'.'+k)
    elif isinstance(value, list):
        for v in value:
            finite(v, context)
    elif isinstance(value, float):
        require(math.isfinite(value), f'{context}: non-finite number')


def safe_strings(value):
    """Defence in depth after allowlisting fields: fail rather than leak a path."""
    if isinstance(value, dict):
        for k, v in value.items():
            safe_strings(k); safe_strings(v)
    elif isinstance(value, list):
        for v in value:
            safe_strings(v)
    elif isinstance(value, str):
        require(not value.startswith(('/', '~/', 'file://')) and
                not re.search(r'(?:/Users/|/Volumes/|/home/|[A-Za-z]:\\)', value),
                'portable output contains an absolute/private path')


def check_tile(tile, crop, context, gradient=False):
    x, y, w, h = crop
    key = 'rms_dn_per_px' if gradient else 'rms_dn'
    require(tile[key] >= 0, context+': negative tile error')
    require(x <= tile['x'] < x+w and y <= tile['y'] < y+h, context+': tile outside ROI')
    require(1 <= tile['width'] <= 32 and 1 <= tile['height'] <= 32, context+': bad tile size')
    require(tile['x']+tile['width'] <= x+w and tile['y']+tile['height'] <= y+h,
            context+': tile crosses ROI boundary')


def check_metric(v, context, crop, gradient=False):
    require(v['mse'] >= 0, context+': negative MSE')
    close(v['psnr_db'], -10*math.log10(max(v['mse'], 1e-16)), context+' PSNR')
    close(v['rms_dn'], math.sqrt(v['mse'])*255, context+' RMS')
    require(v['worst_1pct_rms_dn']+1e-6 >= v['rms_dn'], context+': tail below full RMS')
    check_tile(v['worst_tile'], crop, context)
    if gradient:
        require(v['gradient_mse'] >= 0, context+': negative gradient MSE')
        close(v['gradient_rms_dn_per_px'], math.sqrt(v['gradient_mse'])*255, context+' gradient', 2e-7)
        check_tile(v['worst_gradient_tile'], crop, context, True)


def validate_score(doc, case, labels, name):
    n, crop = CASES[case]
    expected = 2*((n+1)//2)
    finite(doc, name)
    require(doc['schema'] == 1 and doc['execution_status'] == 'complete', name+': incomplete/schema mismatch')
    require(doc['condition'] == 'even_half_input_reconstruction_doubled_displacement', name+': wrong condition')
    require(doc['source_info']['frames'] == n and doc['half_input_frames'] == (n+1)//2 and
            doc['expected_render_frames'] == expected, name+': wrong frame counts')
    require((doc['source_info']['width'], doc['source_info']['height']) == (1920, 1080), name+': wrong dimensions')
    rate(doc['source_info']['rate'], '24000/1001', name+' source rate')
    require(doc['crop'] == crop and doc['first_frame'] == 49 and doc['last_frame'] == 95 and
            doc['scored_original_odd_frames'] == ODD and doc['block_size'] == 32, name+': wrong registered ROI/frames')
    require(doc['retained_tolerance_dn'] == 2.55, name+': changed alignment threshold')
    require(set(doc['renders']) == set(labels), name+': missing/unexpected variants')
    for label, record in doc['renders'].items():
        context = name+'/'+label
        info = record['info']
        require(info['frames'] == expected and (info['width'], info['height']) == (1920, 1080), context+': render counts/dimensions')
        rate(info['rate'], doc['source_info']['rate'], context+' render rate')
        require(record['scored_frames'] == len(ODD), context+': scored-frame count')
        alignment = record['retained_mae_by_original_frame']
        require(set(alignment) == {str(i) for i in EVEN}, context+': retained frame indices')
        require(min(alignment.values()) >= 0 and max(alignment.values()) < 2.55, context+': retained alignment failed')
        close(record['retained_mae_max_dn'], max(alignment.values()), context+' retained maximum')
        rows = record['per_frame']
        require([r['source_frame'] for r in rows] == ODD and [r['render_frame'] for r in rows] == ODD,
                context+': per-frame indices or order')
        for scale in ('raw', 'sigma1', 'sigma2'):
            values = [r['scales'][scale] for r in rows]
            for row, value in zip(rows, values):
                check_metric(value, f'{context}/{scale}/{row["source_frame"]}', crop, scale != 'raw')
            summary = record['summary'][scale]
            check_metric(summary, context+'/'+scale+'/summary', crop, scale != 'raw')
            close(summary['mse'], statistics.fmean(v['mse'] for v in values), context+' pooled MSE')
            close(summary['worst_1pct_rms_dn'], math.sqrt(statistics.fmean(v['worst_1pct_rms_dn']**2 for v in values)),
                  context+' pooled tail')
            worst = max(rows, key=lambda r: r['scales'][scale]['worst_tile']['rms_dn'])
            require(summary['worst_tile'] == {**worst['scales'][scale]['worst_tile'], 'source_frame':worst['source_frame']},
                    context+': inconsistent worst tile')
            if scale != 'raw':
                close(summary['gradient_mse'], statistics.fmean(v['gradient_mse'] for v in values), context+' pooled gradient')
                worst_g = max(rows, key=lambda r: r['scales'][scale]['worst_gradient_tile']['rms_dn_per_px'])
                require(summary['worst_gradient_tile'] == {**worst_g['scales'][scale]['worst_gradient_tile'],
                                                           'source_frame':worst_g['source_frame']},
                        context+': inconsistent worst gradient tile')
    return doc['renders']


def sidecar(root, case, label, native, hashes):
    n, _ = CASES[case]
    folder = case if native else 'withheld-'+case
    path = root/folder/(label+'.json')
    info = read(path)
    require('execution_status' not in info or info['execution_status']=='complete',
            f'{folder}/{label}: renderer sidecar is incomplete')
    source = n if native else (n+1)//2
    require(info['source_frames'] == source and info['output_frames'] == 2*source and
            (info['width'], info['height']) == (1920, 1080), f'{folder}/{label}: invalid renderer counts')
    rate(info['rate'], '48000/1001' if native else '24000/1001', f'{folder}/{label} rate')
    sha = info['shader_sha256']
    require(sha is None if label == 'linear' else isinstance(sha, str) and bool(re.fullmatch('[0-9a-f]{64}', sha)),
            f'{folder}/{label}: invalid shader hash')
    if label in hashes:
        require(sha == hashes[label], f'{folder}/{label}: shader hash changed across renders')
    hashes[label] = sha
    return {**{key:info[key] for key in ('source_frames', 'output_frames', 'width', 'height', 'rate', 'shader_sha256')},
            'completion_marker':'explicit_complete' if 'execution_status' in info else 'legacy_unmarked',
            'render_log_available':path.with_suffix('.log').is_file()}


def compact_metrics(record):
    result = {}
    for scale in ('raw', 'sigma2'):
        value = record['summary'][scale]
        result[scale] = {k:value[k] for k in ('psnr_db', 'rms_dn', 'worst_1pct_rms_dn', 'worst_tile')}
        if scale != 'raw':
            result[scale].update({k:value[k] for k in ('gradient_rms_dn_per_px', 'worst_gradient_tile')})
    return result


def delta(record, base):
    fields = [('raw', 'psnr_db'), ('sigma2', 'psnr_db'), ('sigma2', 'gradient_rms_dn_per_px'),
              ('raw', 'worst_1pct_rms_dn'), ('sigma2', 'worst_1pct_rms_dn')]
    out = {scale+'_'+key:record['summary'][scale][key]-base['summary'][scale][key] for scale, key in fields}
    extrema = {}
    for scale, key in fields:
        differences = [(r['scales'][scale][key]-b['scales'][scale][key], r['source_frame'])
                       for r,b in zip(record['per_frame'], base['per_frame'])]
        low, high = min(differences), max(differences)
        extrema[scale+'_'+key] = dict(minimum_delta=low[0], minimum_frame=low[1],
                                     maximum_delta=high[0], maximum_frame=high[1])
    return dict(summary=out, per_frame_extrema=extrema)


def frame_rows(record):
    out = []
    for row in record['per_frame']:
        a, b = row['scales']['raw'], row['scales']['sigma2']
        values = [row['source_frame'], a['psnr_db'], b['psnr_db'], b['gradient_rms_dn_per_px'],
                  a['worst_1pct_rms_dn'], b['worst_1pct_rms_dn']]
        for v in (a,b):
            values.extend(v['worst_tile'][k] for k in ('rms_dn', 'x', 'y', 'width', 'height'))
        out.append(values)
    return out


def temporal(root):
    path = root/'temporal-shirt-48/temporal.json'
    if not path.exists():
        return dict(status='unavailable')
    doc = read(path)
    finite(doc)
    require(doc['kind'] == 'native_2x_diagnostic_not_ground_truth' and doc['schema'] == 1,
            'temporal report: wrong condition/schema')
    require(doc.get('execution_status') in (None, 'complete'), 'temporal report is incomplete')
    require(doc['settings']['start_frame'] == 48 and doc['requested_source_frames'] == 37 and
            doc['accepted_source_frames'] == 8 and len(doc['positions_in_decoded_crop']) == 8 and
            doc['tracking_status'] == 'unknown_after_rejected_pair', 'temporal report: changed registered coverage')
    require(len(doc['fits']) == 8 and all(f['valid'] for f in doc['fits'][:-1]), 'temporal report: inconsistent accepted track')
    rejected = doc['fits'][-1]
    require(not rejected['valid'] and rejected['source_pair'] == [55,56] and
            rejected['reasons'] == ['ambiguous_translation'], 'temporal report: missing expected rejection')
    return dict(status='partial_track_followed_by_unknown', accepted_source_frame_range=[48,55],
                unmeasured_source_frame_range=[56,84], requested_source_frames=37, accepted_source_frames=8,
                legacy_report_without_completion_marker=doc.get('execution_status') is None,
                crop=doc['crop_at_first_selected_source'],
                rejected_pair={k:rejected[k] for k in ('source_pair', 'reasons', 'correlation', 'rival_correlation',
                                                      'peak_gap', 'fit_residual_dn')},
                scope='Registration coverage only; not a native temporal quality verdict')


def math_controls(root):
    result = {}
    for stem in ('geometry', 'newton', 'obmc'):
        path = root/(stem+'-controls.json')
        if path.exists():
            value = read(path)
            finite(value); safe_strings(value)
            result[stem] = dict(status='available', artifact=path.name, values=value)
        else:
            result[stem] = dict(status='unavailable')
    return result


def current_aa_controls(root):
    path=root/'aa-controls/comparison.json'
    if not path.exists():
        return dict(status='unavailable')
    values=read(path)
    finite(values); safe_strings(values)
    expected={'L0_static', 'L6_flat_large', 'M1_noise_large', 'A4_accel_tex_a033'}
    require(len(values)==4 and {v['case'] for v in values}==expected, 'AA control cases incomplete')
    for row in values:
        require(set(row['scores'])=={'prev','prev-aa-box'}, 'AA control variants differ')
        for region in ('whole','interior'):
            close(row['delta'][region], row['scores']['prev-aa-box'][region]-row['scores']['prev'][region],
                  'AA control comparison '+row['case'])
    return dict(status='comparison_available', artifact='aa-controls/comparison.json', values=values,
                validation_scope='Comparison arithmetic verified; underlying control-run validation is recorded separately',
                scope='Current AA-box small regression probe; distinct from historical prefilter failures and real-film attribution')


def measurement_controls(root):
    path=root/'measurement-controls.json'
    if not path.exists():
        return dict(status='unavailable')
    values=read(path)
    finite(values); safe_strings(values)
    require(values['status']=='pass', 'measurement controls have not passed')
    return dict(status='available',artifact=path.name,values=values)


def gather(root, confirmed=False, mci_shirt_calmer=False, obmc_no_clear_improvement=False):
    hashes, cases = {}, {}
    optional_pending = False
    for case, (n,crop) in CASES.items():
        records, group_status, score_artifacts = {}, {}, []
        for name, suffix, labels in GROUPS:
            relative = f'withheld-{case}{suffix}-scores/withheld.json'
            path = root/relative
            if name == 'obmc' and (not path.exists() or read(path).get('execution_status') != 'complete'):
                group_status[name] = 'pending'
                optional_pending = True
                continue
            doc = read(path)
            values = validate_score(doc, case, labels, relative)
            if records:
                require(values['prev'] == records['prev'], relative+': duplicate prev baseline differs')
            records.update(values)
            group_status[name] = 'complete'
            score_artifacts.append(relative)
        rows, native = {}, {}
        for label, record in records.items():
            withheld_info = sidecar(root, case, label, False, hashes)
            native[label] = sidecar(root, case, label, True, hashes)
            rows[label] = dict(shader_sha256=withheld_info['shader_sha256'],
                               renderer_completion_marker=withheld_info['completion_marker'],
                               renderer_log_available=withheld_info['render_log_available'],
                               retained_mae_max_dn=record['retained_mae_max_dn'],
                               summary=compact_metrics(record), against_prev=delta(record, records['prev']),
                               against_high=delta(record, records['high']), per_frame=frame_rows(record))
        cases[case] = dict(original_frames=n, half_input_frames=(n+1)//2, reconstructed_frames=2*((n+1)//2),
                           native_output_frames=2*n, crop=crop, scored_odd_frames=ODD,
                           score_groups=group_status, score_artifacts=score_artifacts,
                           native_renderer_metadata=native, variants=rows)
    manifest_path = root/'shaders/manifest.json'
    if manifest_path.exists():
        manifest = read(manifest_path)
        for label, sha in hashes.items():
            if label+'.glsl' in manifest:
                require(manifest[label+'.glsl'] == sha, 'shader manifest differs: '+label)
    mci = dict(status='pending')
    if (root/'mci-controls.json').exists():
        values = read(root/'mci-controls.json')
        require(set(values) == set(CASES), 'MCI control cases incomplete')
        finite(values)
        for case,(n,_) in CASES.items():
            v = values[case]
            require(v['source_frames'] == n and v['output_frames'] == 2*n and len(v['retained_rms_dn']) > 0,
                    'MCI count/sample check failed: '+case)
            require(all(0 <= x < 2.55 for x in v['retained_rms_dn']), 'MCI retained check failed: '+case)
        mci = dict(status='instrument_checks_available', checks=values,
                   scope='Instrument checks cover only the listed retained samples; human observation is recorded separately')
    mci['human_observation'] = dict(shirt_noticeably_calmer=mci_shirt_calmer,
        provenance='Explicit --mci-shirt-calmer flag' if mci_shirt_calmer else 'Not supplied to this run',
        scope='Owner comparison of the shirt preview only; not suit, OBMC, a quantitative score or deployment approval')
    out = dict(schema=1, status='required_complete_optional_pending' if optional_pending else 'all_score_groups_complete',
               experiment=root.name, condition='real_withheld_frames_from_even_half_rate_input',
               displacement_relative_to_native_2x=2, source_rate='24000/1001', native_output_rate='48000/1001',
               per_frame_columns=FRAME_COLUMNS, shader_hashes=hashes, cases=cases,
               first_video_observation=dict(defect_confirmed=confirmed,
                   provenance='Explicit --initial-video-defect-confirmed flag' if confirmed else 'Not supplied to this run',
                   scope='Only whether the initial video depicts the reported defect; no later variant verdict'),
               obmc_human_observation=dict(no_clear_improvement=obmc_no_clear_improvement,
                   provenance='Explicit --obmc-no-clear-improvement flag' if obmc_no_clear_improvement else 'Not supplied to this run',
                   scope='Owner native shirt comparison of prior High versus same-field OBMC; not a suit verdict'),
               native_tracking=temporal(root), independent_mci=mci, controlled_math=math_controls(root),
               current_aa_controls=current_aa_controls(root),
               measurement_controls=measurement_controls(root),
               interpretation=['Higher PSNR is better; lower gradient, tail and tile error is better.',
                               'Worst-tile maxima may occur at different coordinates; they are not matched-location deltas.',
                               'These truth metrics have doubled endpoint displacement and do not prove a native temporal fix.',
                               'Geometry controls are controlled mathematical evidence, not a real-film causal attribution.'])
    finite(out); safe_strings(out)
    return out


def markdown(data):
    lines = ['# Ripple experiment: compact numeric record', '',
             f'Status: `{data["status"]}`. Required original, Newton and AA score groups were validated.', '',
             'The withheld test reconstructs odd originals from even originals: twice the native interpolation displacement.',
             'All duplicate previous-High baselines match exactly. Renderer counts, hashes, retained alignment and score arithmetic passed.', '',
             'Renderer sidecars without completion markers are explicitly labeled legacy. A historical log alone does not prove process exit status; full decoded counts and retained-frame alignment were independently checked.', '',
             'Initial video depicts the reported defect: '+('confirmed by the explicit recorded flag.' if data['first_video_observation']['defect_confirmed'] else 'not recorded by this invocation.'),
             'This does not record a human verdict on later variants.', '']
    for case, record in data['cases'].items():
        lines += [f'## {case.title()}', '',
                  f'{record["original_frames"]} originals; {record["half_input_frames"]} half-rate inputs; {record["reconstructed_frames"]} reconstructed frames; {record["native_output_frames"]} native 2x outputs. ROI `{record["crop"]}`; 24 withheld frames 49–95.', '',
                  '| Variant | Raw PSNR dB | σ2 gradient DN/px | Raw tail DN | σ2 tail DN | Worst σ2 tile DN; frame, x, y |',
                  '|---|---:|---:|---:|---:|---|']
        for label,row in record['variants'].items():
            a,b = row['summary']['raw'], row['summary']['sigma2']; tile=b['worst_tile']
            lines.append(f'| {label} | {a["psnr_db"]:.5f} | {b["gradient_rms_dn_per_px"]:.5f} | {a["worst_1pct_rms_dn"]:.3f} | {b["worst_1pct_rms_dn"]:.3f} | {tile["rms_dn"]:.3f}; {tile["source_frame"]}, {tile["x"]}, {tile["y"]} |')
        lines += ['', '| Variant | Δ raw dB vs prev / High | Δ σ2 dB vs prev / High | Δ gradient vs prev / High | Δ σ2 tail vs prev / High |',
                  '|---|---:|---:|---:|---:|']
        for label,row in record['variants'].items():
            p,h = row['against_prev']['summary'],row['against_high']['summary']
            cells = [f'{p[k]:+.5f} / {h[k]:+.5f}' for k in ('raw_psnr_db','sigma2_psnr_db','sigma2_gradient_rms_dn_per_px','sigma2_worst_1pct_rms_dn')]
            lines.append('| '+label+' | '+' | '.join(cells)+' |')
        lines += ['', 'Optional OBMC score group: **'+record['score_groups']['obmc']+'**.', '']
    tracking=data['native_tracking']
    lines += ['## Native temporal coverage', '']
    if tracking['status']=='unavailable':
        lines += ['Source-only tracker metadata unavailable.']
    else:
        r=tracking['rejected_pair']
        lines += [f'The source-only shirt tracker accepted 48–55; 56–84 are unknown. Pair 55→56 was rejected: correlation {r["correlation"]:.5f}, rival {r["rival_correlation"]:.5f}, gap {r["peak_gap"]:.5f}, fitted residual {r["fit_residual_dn"]:.3f} DN.',
                  'This is coverage metadata, not a native temporal quality score.']
    lines += ['', 'Geometry/Newton/OBMC CPU control values and per-frame metric rows are retained in the JSON. Their scopes remain separate from film attribution.',
              'Runnable temporal/withheld measurement controls: `'+data['measurement_controls']['status']+'`.',
              'MCI status: `'+data['independent_mci']['status']+'`.',
              ('Owner reports the MCI shirt is noticeably calmer than current High in the displayed native preview.'
               if data['independent_mci']['human_observation']['shirt_noticeably_calmer']
               else 'No human MCI quality verdict was supplied to this invocation.'),
              'That MCI observation does not apply to the suit or the same-field OBMC diagnostic.',
              ('Owner reports no clear improvement in the same-field OBMC shirt preview: visual benefit not established.'
               if data['obmc_human_observation']['no_clear_improvement']
               else 'No human same-field OBMC verdict was supplied to this invocation.'), '']
    aa=data['current_aa_controls']
    if aa['status']=='comparison_available':
        lines += ['## Current AA control probe', '',
                  'These four current-baseline comparisons are separate from the historical prefilter failures. Only comparison arithmetic is validated by this summary.', '',
                  '| Case | Whole Δ dB | Interior Δ dB |', '|---|---:|---:|']
        for row in aa['values']:
            lines.append(f'| {row["case"]} | {row["delta"]["whole"]:+.5f} | {row["delta"]["interior"]:+.5f} |')
        lines.append('')
    return '\n'.join(lines)


def rounded(value):
    if isinstance(value,float):
        return float(f'{value:.10g}')
    if isinstance(value,list):
        return [rounded(x) for x in value]
    if isinstance(value,dict):
        return {k:rounded(v) for k,v in value.items()}
    return value


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('root',type=Path)
    parser.add_argument('--out-dir',type=Path)
    parser.add_argument('--initial-video-defect-confirmed',action='store_true')
    parser.add_argument('--mci-shirt-calmer',action='store_true')
    parser.add_argument('--obmc-no-clear-improvement',action='store_true')
    args=parser.parse_args(argv)
    out=args.out_dir or args.root
    out.mkdir(parents=True,exist_ok=True)
    # An interrupted/invalid rerun cannot leave a stale complete JSON/Markdown.
    (out/'review-summary.json').write_text('{"status":"incomplete"}\n')
    (out/'review-summary.md').write_text('Summary incomplete: validation has not finished.\n')
    data=gather(args.root,args.initial_video_defect_confirmed,args.mci_shirt_calmer,args.obmc_no_clear_improvement)
    text=json.dumps(rounded(data),indent=2,allow_nan=False)
    # Keep each numeric per-frame row on one reviewable line.
    text=re.sub(r'\[\n\s*(-?\d[^\[\]{}]*?)\n\s*\]',lambda m:'['+' '.join(m.group(1).split())+']',text)
    require(json.loads(text)==rounded(data),'compact JSON formatting altered data')
    (out/'review-summary.json').write_text(text+'\n')
    (out/'review-summary.md').write_text(markdown(data))
    print(json.dumps(dict(status=data['status'],json=str(out/'review-summary.json'),markdown=str(out/'review-summary.md'))))
    return data


if __name__=='__main__':
    main()
