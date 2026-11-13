#!/usr/bin/env python3
"""CPU reviewer controls for motionstress geometry and the actual scorer.

    python controls.py OUT.json

No GPU or source fixture cache changes. Tests constant/affine flow, the two-root
visibility ambiguity, correct frame alignment, a deliberate one-output shift,
and corruption confined to one synthesized facial-feature frame.
"""
import json
from pathlib import Path
import sys

import numpy as np
import scenes
import run


def solve(field, p, t):
    # Scalar version of the generated proposal sequence/acceptance logic.
    best = float(field(p))
    q = p-t*best
    nxt = float(field(q))
    best_error = abs(q+t*nxt-p)
    initial = best
    for _ in range(2):
        candidate = nxt
        q = p-t*candidate
        nxt = float(field(q))
        error = abs(q+t*nxt-p)
        if error+1e-4 < best_error:
            best, best_error = candidate, error
    return initial, best, best_error


def geometry():
    for value in (-48., 0., 32.):
        for phase in (0., .2, .4, .6, .8, 1.):
            a, b, _ = solve(lambda q: value, 100., phase)
            assert a == b == value
    p, t, d, k = 100., .4, 12., .2
    a, b, residual = solve(lambda q: d+k*q, p, t)
    exact = (d+k*p)/(1+t*k)
    assert abs(b-exact) < abs(a-exact)/100
    f = lambda q: 20. if 0 <= q <= 60 else 0.
    roots = []
    for v in (0., 20.):
        q = 65.-.5*v
        error = abs(q+.5*f(q)-65.)
        assert error == 0
        roots.append(dict(flow=v, source=q, residual=error))
    return dict(constant_identity=True, affine_initial_error=abs(a-exact),
                affine_selected_error=abs(b-exact), affine_residual=residual,
                distinct_exact_visibility_roots=roots)


def scorer():
    count = scenes.SOURCE_FRAMES*5//2
    name = 'face_fast'
    truth = np.stack([scenes.render(name, k*.4)[0] for k in range(count)])
    clean = run.measure(name, truth, truth)
    assert clean['retained_rms_dn'] == 0 and all(row['mse'] == 0 for row in clean['rows'])
    rejected = False
    try:
        run.measure(name, np.roll(truth, 1, axis=0), truth)
    except AssertionError as exc:
        assert 'source misalignment' in str(exc)
        rejected = True
        reason = str(exc)
    assert rejected, 'Actual scorer accepted a one-output temporal shift'
    bad = truth.copy()
    _, _, features = scenes.render(name, 7*.4)
    bad[7, features] += .15
    damaged = run.measure(name, bad, truth)
    assert damaged['retained_rms_dn'] == 0
    changed = [row for row in damaged['rows'] if row['feature_mse'] > 1e-10]
    assert len(changed) == 1 and changed[0]['frame'] == 7
    assert changed[0]['feature_bad_05'] == 1
    assert abs(changed[0]['feature_mse']-.15**2) < 1e-6
    return dict(clean_alignment_pass=True, scored_frames=clean['frames'],
                shifted_rejected=reason, single_inserted_fault_frame=7,
                fault_feature_mse=changed[0]['feature_mse'], retained_unchanged=True)


def main():
    result = dict(geometry=geometry(), scorer=scorer())
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
