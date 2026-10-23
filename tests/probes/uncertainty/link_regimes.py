#!/usr/bin/env python3
"""RUN-ON: cpu. COMMAND: python3 tests/probes/uncertainty/link_regimes.py OLD NEW --out JSON
DOES O9'S MISS GENERALISE? (Local, 2026-10-23, after GPT's G014: the frozen M2c+A4 link covariance over-predicted held-out
O9's link-induced variance 2.49x / 2.25x, and GPT asked for more varied, independent regimes before any new model.)

OLD is the 10-22 Arc export (M2c, A4, O9: GPT's training and its used holdout); NEW is a fresh Arc export of the
same tool (export_links.sh, 2026-10-23) with M2c_period40_v10 again plus six cases never exported before.
  INSTRUMENT: NEW's M2c_period40_v10 must equal OLD's array for array (the Arc, a fresh container a day later); a
  difference refuses the comparison. link_covariance.sample's own reconstruction and coherent-fault gates run on
  every case as before.
  SEALED: A5_accel_tex_a067 and O5_osc_textured are exported but NOT READ here (this tool refuses them): they are
  the untouched holdout for any conditioned covariance model proposed after this result.
  READ: M2c_period40_v6 (the same print, slower), M1c_noise_v6 (noise texture), L7_textured_large (16 px/frame,
  its own print), O10_osc_tex_tiny (4 px oscillation, 6 samples a period). GPT's covariance and mean are rebuilt
  from OLD's M2c+A4 exactly as link_covariance.py builds them (same seed, same sampling), frozen, and propagated.
PRE-REGISTERED (Local, written before NEW was read): O9's miss is the rule, not the exception: the full-covariance
  predicted / observed variance ratio leaves [0.5, 2] on at least one axis on at least 3 of the 4 READ cases; the full
  covariance still beats its diagonal counterfactual (smaller |log ratio| on both axes) on at least 3 of the 4.
  Refuted otherwise. Descriptive alongside: each case's per-link x error SD by tau, which says whether the regimes
  differ in scale (one number would then carry most of the miss) or in shape.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from link_covariance import CASES, evaluate, sample

READ = ['M2c_period40_v6', 'M1c_noise_v6', 'L7_textured_large', 'O10_osc_tex_tiny']
SEALED = {'A5_accel_tex_a067', 'O5_osc_textured'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('old', type=Path); p.add_argument('new', type=Path); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    assert not SEALED & set(READ)
    za, zb = np.load(a.old / 'M2c_period40_v10.npz'), np.load(a.new / 'M2c_period40_v10.npz')
    same = {k: bool(np.array_equal(za[k], zb[k])) for k in za.files}
    if not all(same.values()): raise ValueError(f'the Arc does not repeat M2c across exports: {same}')
    rng = np.random.default_rng(20261022)
    old = [sample(a.old / (c + '.npz'), c, rng) for c in CASES]          # link_covariance.py's own draw order
    train = np.concatenate([d['error'] for d in old[:2]])
    mu, cov = train.mean(axis=0), np.cov(train, rowvar=False, ddof=1)
    rows = {c: evaluate(d, mu, cov) for c, d in zip(CASES, old)}
    rng = np.random.default_rng(20261023)
    for c in READ:
        d = sample(a.new / (c + '.npz'), c, rng)
        rows[c] = evaluate(d, mu, cov)
        rows[c]['link_x_sd_by_tau'] = dict(zip(['-3', '-2', '-1', '+1', '+2'], d['error'][:, ::2].std(axis=0).tolist()))
    for c in CASES:
        rows[c]['link_x_sd_by_tau'] = dict(zip(['-3', '-2', '-1', '+1', '+2'],
                                               old[CASES.index(c)]['error'][:, ::2].std(axis=0).tolist()))
    band = [c for c in READ if not all(.5 < r < 2 for r in rows[c]['full_to_actual'])]
    beats = [c for c in READ if all(abs(np.log(f)) < abs(np.log(g)) for f, g in
                                    zip(rows[c]['full_to_actual'], rows[c]['diagonal_to_actual']))]
    held = len(band) >= 3 and len(beats) >= 3
    result = {'instrument_m2c_identical': same, 'cases': rows, 'outside_band': band, 'full_beats_diagonal': beats,
              'prediction_held': held, 'sealed': sorted(SEALED),
              'input_sha256': {c: hashlib.sha256((a.new / (c + '.npz')).read_bytes()).hexdigest() for c in READ}}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, indent=2) + '\n')
    for c, r in rows.items():
        print(f"{c:22s} full/obs {r['full_to_actual'][0]:.3f} {r['full_to_actual'][1]:.3f}  diag/obs "
              f"{r['diagonal_to_actual'][0]:.3f} {r['diagonal_to_actual'][1]:.3f}  cover68 {r['gaussian_68_ellipse_coverage']:.3f}  "
              f"x sd by tau {' '.join(f'{v:.3f}' for v in r['link_x_sd_by_tau'].values())}")
    print('outside band', band, 'full beats diagonal', beats, 'PREDICTION', 'HELD' if held else 'REFUTED')
    return 0 if held else 3


if __name__ == '__main__':
    raise SystemExit(main())
