#!/usr/bin/env python3
"""RUN-ON: mac. COMMAND: python3 tests/probes/cage/bar_basin.py --pipeline "$NP_SCRATCH/bar-pipeline" --out "$NP_SCRATCH/bar-basin"
BASIN AGAINST BASIN (Local, 2026-10-23, after GPT's G009-G017). A diagnostic variant of GPT's broader-support guard
(bar_guard.py), not a production switch. COST: isolated seeds, the guided case, C1-C4 x five shaders.

WHERE THE GUARD'S REMAINING DAMAGE IS (measured post hoc on GPT's own raw outputs, $NP_SCRATCH/bar-pipeline and
bar-guard, before this tool was written): on the guided case (fine .08, broad .30, P 512) the guard still sends 4196
crop samples (1.26%) to the -3 alias, against bars' 12152 (3.65%); GPT's corruption count (.048%) sees only 160 of them
because it counts seeds High had within .5 px of +6, while at these flips High read +5.8 to +8.4 (median +7.7). The
flips sit within 30 degrees of the broad sinusoid's extrema (1956 + 960 + 960 + 320 samples; none elsewhere), where
the 48 px block cannot see the broad signal's slope. There the guard compares the alias, refined to the fine bars'
exact minimum, with the INCOMING vector refined only over +-1 px: an incoming +7.7 a period-9 comb's minimum 1.7 px
away loses to an alias that fits the bars exactly, and the guard permits the switch. The mask's error is concentrated
(top 10% of its samples carry 89% of the guard's error), as flips, not drift, would make it.

THE CANDIDATE: compare basin with basin, each at its own fine minimum. The incoming basin is the fine 1-D cost's local
minimum nearest s = 0 (within 4 px, under half a period), parabola-refined like the proposal; the guard's broader
48 px SAD (bar_guard.HELPER, unchanged) then scores vf + s_in n against vf + s n, and the change is permitted only if
the proposal beats it by over 1/255 (GPT's margin, unchanged). If the proposal IS the incoming basin, it is no basin
change and passes unguarded, as in the unguarded pass. Refused, two forms (combined in one run, split only by result):
  basin      keeps the incoming vector exactly (as the guard does);
  basinsnap  moves it to the incoming basin's refined minimum (vf + s_in n): the incoming basin was trusted, so its
             own fine fit is used. (This one changes pixels the guard would leave alone; the ladder decides.)

PRE-REGISTERED (written before any render of either variant):
  P1 guided case: samples High had in the +6 basin (|x - 6| < 4.5) that the variant sends within .5 px of -3:
     basin and basinsnap each under 0.2% of the crop (bars and guard measured above at 3.65% / 1.26%). GPT's fixed
     +3-shifted damage mask: basin's MSE within 2x High's (High .000081417); basinsnap's at or under basin's.
  P2 isolated pure-period seeds (bar_gpu.py's scene, no broad evidence anywhere): +6, -6, +3 come back within .2 px.
  P3 C3 (cage rectangle): each variant at least +3.0 dB over the same run's High. Under 3.0 kills that variant.
  P4 C4 (cage rectangle): each variant at least +1.0 dB over High, kill under that (bars alone read +2.25: the
     pyramid's +15 lock is the incoming basin there; the prediction is that the wall's 32 px blocks inside the 48 px
     block tell +15 from +6, so the change is permitted). GPT's guard is run beside them, prediction the same.
  P5 C1, C2: neither variant down more than 0.5 dB on the frame or the rectangle.
  Survivors then face the 45-case gate (no case down 1 dB, capped frozen/headline means within .05), the build gate's
  real footage and timing, outside this tool. No threshold or margin is tuned after a result.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

import bar_gpu as gpu
import bar_guard as guard
import bar_pipeline as pipe
import guard_followup as follow

ANCHOR = '    vec4 result = vec4((vf + s * n) * 0.5, 0.0, 0.0);'


def block(snap):
    kept = 'vec4((vf + s_in * n) * 0.5, 0.0, 0.0)' if snap else 'keep'
    return f'''    // BASIN AGAINST BASIN (tests/probes/cage/bar_basin.py): the incoming basin at its own fine minimum
    int ib = -1;
    for (int k = 0; k <= 4; k++) {{
        int lo = BAR_REACH - k, hi = BAR_REACH + k;
        if (ib < 0 && cost[lo] <= cost[lo - 1] && cost[lo] <= cost[lo + 1]) ib = lo;
        if (ib < 0 && cost[hi] <= cost[hi - 1] && cost[hi] <= cost[hi + 1]) ib = hi;
    }}
    if (ib != best) {{
        float s_in = 0.0;
        if (ib >= 0) {{
            float d2 = cost[ib - 1] - 2.0 * cost[ib] + cost[ib + 1];
            s_in = float(ib - BAR_REACH) + (d2 > 1.0e-9 ? clamp(0.5 * (cost[ib - 1] - cost[ib + 1]) / d2, -0.5, 0.5) : 0.0);
        }}
        if (guard_sad(c, vf + s * n) >= guard_sad(c, vf + s_in * n) - 1.0 / 255.0) {{
            vec4 kept = {kept};
            imageStore(FLOW_H_AB_BARS_CACHE, coord, kept);
            return kept;
        }}
    }}
'''


def variant_pass(snap):
    old = gpu.bar.PASS
    assert old.count('vec4 hook() {') == 1 and old.count(ANCHOR) == 1
    return old.replace('vec4 hook() {', guard.HELPER + 'vec4 hook() {').replace(ANCHOR, block(snap) + ANCHOR)


def variant(t, snap):
    assert t.count(gpu.bar.PASS) == 1, 'original bars pass not found exactly once'
    return t.replace(gpu.bar.PASS, variant_pass(snap))


def vx(path):
    r = pipe.read_raw(path, 10)
    z = np.rint(r[..., 2] * 1024).astype(int)
    return 2 * (z // 32 - 16 + r[..., 0])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pipeline', required=True, type=Path); p.add_argument('--out', required=True, type=Path)
    a = p.parse_args(); base = a.pipeline.resolve(); out = a.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    ff = str(Path.home() / 'np-build/ffmpeg/ffmpeg')
    if (base / 'high0.glsl').read_text() != pipe.HIGH.read_text(): raise ValueError('High source changed')
    bars = (base / 'high1.glsl').read_text()
    shaders = {'high0': base / 'high0.glsl', 'high1': base / 'high1.glsl'}
    for name, text in [('guard', guard.guarded(bars)), ('basin', variant(bars, False)), ('basinsnap', variant(bars, True))]:
        shaders[name] = out / f'{name}.glsl'; shaders[name].write_text(text)
    result = {'sha256': {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in shaders.items()}}

    # P2: the isolated pure-period seeds, the pass swapped in bar_gpu's harness (its bypass checks first).
    iso = out / 'isolated'; iso.mkdir(exist_ok=True); original = gpu.bar.PASS; result['isolated'] = {}
    for speed in (6, -6, 3):
        row = gpu.render(ff, iso, f'bypass_{speed}', speed, False)
        if abs(row['median_xy'][0] - speed) > .01 or row['background_max_abs'] > .01: raise ValueError('bypass failed')
    for name, snap in [('basin', False), ('basinsnap', True)]:
        gpu.bar.PASS = variant_pass(snap)
        try:
            for speed in (6, -6, 3):
                row = gpu.render(ff, iso, f'{name}_{speed}', speed, True)
                result['isolated'][f'{name}_{speed}'] = row['median_xy'][0]
        finally:
            gpu.bar.PASS = original
    result['P2'] = all(abs(v - int(k.split('_')[1])) < .2 for k, v in result['isolated'].items())
    print(json.dumps(result['isolated']), flush=True)

    # P1: the guided case, flow and picture.
    tail = gpu.shader(6, False); tail = tail[tail.rindex('//!HOOK FRAME_MIX'):]
    src = base / 'case3.rgb48'; sl = (slice(None), slice(24, -24), slice(48, -48))
    h = vx(base / 'case3_flow0.rgba64')
    flows = {'high1': vx(base / 'case3_flow1.rgba64')}
    for name in ['guard', 'basin', 'basinsnap']:
        f = out / f'{name}-flow.glsl'; f.write_text(shaders[name].read_text() + '\n' + tail)
        v = pipe.render(ff, out, f'guided_{name}', src, f)[..., 0]
        if not np.array_equal(v, pipe.render(ff, out, f'guided_{name}_repeat', src, f)[..., 0]): raise ValueError('repeat differs')
        flows[name] = v
    flips = {k: float(np.mean((abs(h[sl] - 6) < 4.5) & (abs(v[sl] + 3) < .5))) for k, v in flows.items()}
    mask = np.roll((abs(h - 6) < .5) & (abs(flows['high1'] + 3) < .5), 3, axis=2)[sl]
    u = np.arange(pipe.W)[None, :] + .5 - 6 * np.arange(6, 26)[:, None] / 2
    truth = .5 + .08 * np.cos(2 * np.pi * (u % 9) / 9) + .3 * np.cos(2 * np.pi * u / 512)
    local, crop = {}, {}
    for name in ['high0', 'high1', 'guard', 'basin', 'basinsnap']:
        im = pipe.render(ff, out, f'guided_picture_{name}', src, shaders[name], 48, False)
        e = ((im - truth[:, None, :]) ** 2)[1::2][sl]
        local[name], crop[name] = float(e[mask].mean()), float(e.mean())
    result.update(guided_flips=flips, guided_mask_mse=local, guided_crop_mse=crop)
    result['P1'] = {n: flips[n] < .002 for n in ['basin', 'basinsnap']}
    result['P1']['basin_mask'] = local['basin'] <= 2 * local['high0']
    result['P1']['snap_mask'] = local['basinsnap'] <= local['basin']
    print(json.dumps({k: result[k] for k in ['guided_flips', 'guided_mask_mse', 'guided_crop_mse', 'P1']}), flush=True)

    # P3-P5: the cage, C1-C4, five shaders through cage.sh.
    env = os.environ.copy(); env.update(FFMPEG=ff, PY=sys.executable, OUTROOT=str(out / 'cage'),
        SHADERS=' '.join(str(v) for v in shaders.values()),
        MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
    cases = ['C1_cage_drift', 'C2_cage_drift_occluded', 'C3_bars_spin_drift', 'C4_bars_fast_pan']
    r = subprocess.run(['bash', str(pipe.REPO / 'tests/probes/cage/cage.sh'), *cases], env=env, capture_output=True, text=True)
    (out / 'cage.log').write_text(r.stdout + r.stderr)
    if r.returncode or 'FAILED' in r.stdout: raise ValueError('cage failed')
    cage = {}
    for c in cases:
        d = out / 'cage' / c
        cage[c] = {k: {'frame': follow.values(d / f'{k}.log'), 'region': follow.values(d / f'{k}-cage.log')} for k in shaders}
    result['cage'] = cage
    up = lambda c, k, kind='region': cage[c][k][kind] - cage[c]['high0'][kind]
    for k in ['guard', 'basin', 'basinsnap', 'high1']:
        print(k, {c[:2]: (round(up(c, k, 'frame'), 3), round(up(c, k), 3)) for c in cases}, flush=True)
    result['P3'] = {k: up(cases[2], k) >= 3.0 for k in ['basin', 'basinsnap']}
    result['P4'] = {k: up(cases[3], k) >= 1.0 for k in ['guard', 'basin', 'basinsnap']}
    result['P5'] = {k: all(up(c, k, kind) >= -.5 for c in cases[:2] for kind in ['frame', 'region']) for k in ['basin', 'basinsnap']}
    result['survives'] = {k: result['P1'][k] and result['P2'] and result['P3'][k] and result['P4'][k] and result['P5'][k]
                          for k in ['basin', 'basinsnap']}
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['P1', 'P2', 'P3', 'P4', 'P5', 'survives']}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
