#!/usr/bin/env python3
"""Imports-to-interpolation diagnostics D1-D3 (IMPORTS-TO-INTERPOLATION.md, pre-registered at 8d9b76b before this ran).

    diagnose.py <prospect-root> [window ...]        default: film tv anime cartoon cg; writes <root>/imports.json

Streams each window's three decoded videos (ref, high, linear: GPT's 640-wide renders, tests/probes/prospect/) in
lockstep, frame index for frame index, with a rolling buffer of eleven ref frames. For every eligible withheld frame n
(GPT's metrics: not a cut, a hold, low signal or a boundary), on GPT's 16 x 16 grid of cells, from the RETAINED frames
n-5 .. n+5 only: coherent change, oscillation, raw change (D1), and the six retained frames' per-pixel median (D3); the
truth, High and the blend score each cell. D2 runs over every adjacent pair of ref frames.
"""
import collections
import json
import os
import subprocess
import sys

import numpy as np

FF = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
G = 16


def stream(path, w, h):
    p = subprocess.Popen([FF, '-nostdin', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         stdout=subprocess.PIPE)
    n = w * h
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w).astype(np.float32)


def cells(a, ch, cw):
    """mean over each cell of a (H, W) array cropped to the grid"""
    return a[:ch * G, :cw * G].reshape(G, ch, G, cw).mean(axis=(1, 3))


def window(root, name):
    m = json.load(open(f'{root}/{name}/metrics.json'))
    w, h = m['width'], m['height']; ch, cw = h // G, w // G
    elig = {r['frame'] for r in m['rows'] if not (r['cut'] or r['hold'] or r['low'] or r['boundary'])}
    ref, hi, li = (stream(f'{root}/{name}/{s}.mkv', w, h) for s in ('ref', 'high', 'linear'))
    buf = collections.deque(maxlen=11); hb = collections.deque(maxlen=11); lb = collections.deque(maxlen=11)
    t = np.array([-5, -3, -1, 1, 3, 5], np.float32); tc = t - t.mean()
    out = collections.defaultdict(list)
    d2 = {'pairs': 0, 'moving': 0, 'mixed': 0}
    # D2b (registered at 3ecb870): held drawings by their alternation over three consecutive pairs; "coexist" = at least
    # 2% of the textured cells on twos and 2% on ones in the same triple (fixed here before the first D2b run)
    d2b = {'triples': 0, 'moving_cells': 0, 'twos_cells': 0, 'ones_cells': 0, 'moving_triples': 0, 'mixed_triples': 0}
    hist = collections.deque(maxlen=3)
    prev = None
    for i, (r, a, b) in enumerate(zip(ref, hi, li)):
        buf.append(r); hb.append(a); lb.append(b)
        if prev is not None:                                                  # D2: every adjacent pair
            d = r - prev
            rms = np.sqrt(cells(d * d, ch, cw)); sd = np.sqrt(np.maximum(cells(r * r, ch, cw) - cells(r, ch, cw) ** 2, 0))
            cut = np.sqrt((d * d).mean()) >= 40
            hist.append(None if cut else rms)
            if len(hist) == 3 and all(x is not None for x in hist):
                r0, r1, r2 = hist; tx = sd > 4
                mv_any = tx & (np.maximum(np.maximum(r0, r1), r2) > 3.0)
                twos = tx & (((r0 > 3) & (r1 < 1) & (r2 > 3)) | ((r0 < 1) & (r1 > 3) & (r2 < 1)))
                ones = tx & (r0 > 3) & (r1 > 3) & (r2 > 3)
                d2b['triples'] += 1; d2b['moving_cells'] += int(mv_any.sum())
                d2b['twos_cells'] += int(twos.sum()); d2b['ones_cells'] += int(ones.sum())
                if mv_any.sum() >= 0.1 * max(tx.sum(), 1):
                    d2b['moving_triples'] += 1
                    if twos.sum() >= 0.02 * tx.sum() and ones.sum() >= 0.02 * tx.sum():
                        d2b['mixed_triples'] += 1
            if not cut:                                                       # not a cut
                tex = sd > 4
                if tex.sum() >= 0.1 * G * G:
                    mv, held = (rms > 3.0) & tex, (rms < 1.0) & tex
                    d2['pairs'] += 1
                    if mv.sum() >= 0.1 * tex.sum():
                        d2['moving'] += 1
                        if held.sum() >= 0.1 * tex.sum():
                            d2['mixed'] += 1
        prev = r
        n = i - 5                                                             # the withheld frame at the buffer's centre
        if len(buf) < 11 or n not in elig:
            continue
        R = np.stack([buf[k] for k in (0, 2, 4, 6, 8, 10)])                   # n-5, n-3, n-1, n+1, n+3, n+5
        truth, H_, L_ = buf[5], hb[5], lb[5]
        mh, ml = cells((H_ - truth) ** 2, ch, cw), cells((L_ - truth) ** 2, ch, cw)
        med = np.median(R, axis=0); mm = cells((med - truth) ** 2, ch, cw)
        D = np.diff(R, axis=0)
        coh = np.mean([np.abs(cells(D[j], ch, cw)) / (cells(np.abs(D[j]), ch, cw) + 1e-3) for j in range(5)], axis=0)
        slope = np.tensordot(tc, R - R.mean(0), axes=1) / (tc ** 2).sum()
        resid = R - R.mean(0) - slope[None] * tc[:, None, None]
        tot = ((R - R.mean(0)) ** 2).mean(0)
        osc = cells(np.where(tot > 1.0, (resid ** 2).mean(0) / np.maximum(tot, 1e-6), 0.0), ch, cw)
        raw = cells(np.abs(R[3] - R[2]), ch, cw)
        coh1 = np.abs(cells(D[2], ch, cw)) / (cells(np.abs(D[2]), ch, cw) + 1e-3)    # D1b: the one pair n-1 -> n+1
        target = (mh > 2 * ml) & (np.sqrt(mh) > 3.0)
        for k, v in (('coh', coh), ('coh1', coh1), ('osc', osc), ('raw', raw), ('target', target), ('med_beats_high', mm < mh),
                     ('mh', mh), ('ml', ml)):
            out[k].append(v.ravel())
        out['frame'].append(np.full(G * G, n)); out['cell'].append(np.arange(G * G))
    # FAIL CLOSED (GPT's G028): zip stops at the shortest stream, so the three streams must have been the same length
    counts = [sum(1 for _ in stream(f'{root}/{name}/{s}.mkv', w, h)) for s in ('ref', 'high', 'linear')]
    if len(set(counts)) != 1 or counts[0] != i + 1:
        raise SystemExit(f'REFUSED {name}: stream lengths {counts}, consumed {i + 1}')
    A = {k: np.concatenate(v) for k, v in out.items()}
    res = {'eligible_frames': len(out['frame']), 'cells': int(A['target'].size), 'base_rate': float(A['target'].mean())}
    for f in ('coh', 'coh1', 'osc', 'raw'):
        top = A[f] >= np.quantile(A[f], 0.99)
        res[f'lift_{f}'] = float(A['target'][top].mean() / max(A['target'].mean(), 1e-9))
    # sizing (exploratory, after D1b): replace High by the blend in the top q of cells by a cue; the change in the
    # window's total squared error, and in the failed cells' (negative = better)
    tot = A['mh'].sum()
    for f in ('coh1', 'coh', 'raw'):
        for q in (0.005, 0.01, 0.02, 0.05):
            g = A[f] >= np.quantile(A[f], 1 - q)
            res[f'swap_{f}_{q}'] = float((A['ml'][g] - A['mh'][g]).sum() / tot)
    res['d3_med_beats_high_target'] = float(A['med_beats_high'][A['target']].mean()) if A['target'].any() else None
    res['d3_med_beats_high_all'] = float(A['med_beats_high'].mean())
    res['d2'] = d2; res['d2_mixed_share_of_moving'] = d2['mixed'] / max(d2['moving'], 1)
    res['d2b'] = d2b
    res['d2b_twos_share_of_moving_cells'] = d2b['twos_cells'] / max(d2b['moving_cells'], 1)
    res['d2b_mixed_share_of_moving_triples'] = d2b['mixed_triples'] / max(d2b['moving_triples'], 1)
    if name == 'tv':                                                          # GPT's TV 73 at 640 px: its cell, as a check
        sel = A['frame'] == 73
        if sel.any():
            res['tv73'] = {f: [round(float(x), 3) for x in A[f][sel][np.argsort(-A['mh'][sel])[:3]]] for f in ('coh', 'osc', 'raw', 'mh', 'ml')}
    return res


def main():
    root = sys.argv[1]; names = sys.argv[2:] or ['film', 'tv', 'anime', 'cartoon', 'cg']
    allres = {}
    for nm in names:
        allres[nm] = r = window(root, nm)
        print(nm, json.dumps(r), flush=True)
    json.dump(allres, open(f'{root}/imports.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
