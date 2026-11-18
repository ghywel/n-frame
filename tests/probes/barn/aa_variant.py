#!/usr/bin/env python3
"""Apply the ripple probe's cascaded box low-pass (ripple/aa_pyramid.py, GPT's, 2026-11-15) to the CURRENT High, at
chosen levels only (2026-11-18). GPT's file is imported, not edited: its hash lock names the earlier High, so this
wrapper re-implements only the lock and the level choice, and reuses its pass text and its replacement rule.

    aa_variant.py <high.glsl> <out.glsl> --levels S        (the 1/16 level's luma low-passed; the rest untouched)
    aa_variant.py <high.glsl> <out.glsl> --levels H,Q,E,S  (GPT's whole cascade)

The cascade passes are always all four (each level averages the one above); only the named levels' LUMA passes read
them. Checks: every named level's single source-luma expression replaced, gain compensation and the energy channel
kept, hook count up by exactly eight, and nothing else in the file changed (an unnamed level's pass is byte-identical).
"""
import argparse, hashlib, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'ripple'))
import aa_pyramid  # noqa: E402

HIGH_SHA256 = hashlib.sha256(Path(__file__).resolve().parents[3].joinpath(
    'shaders/bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut.glsl').read_bytes()).hexdigest()


def apply(text, levels, any_base=False):
    if not any_base and hashlib.sha256(text.encode()).hexdigest() != HIGH_SHA256:
        raise SystemExit('expected the shipped High byte for byte')
    original = text
    reps = []
    for side, source in (('A', 'HOOKED'), ('B', 'NEXT')):
        for level, _ in aa_pyramid.LEVELS:
            if level not in levels:
                continue
            marker = f'//!SAVE LUMA_{side}_{level}\n'
            assert text.count(marker) == 1, marker
            at = text.index(marker)
            start = text.rfind('//!HOOK FRAME_MIX\n', 0, at)
            nxt = re.search(r'^//!(?:HOOK|TEXTURE|PARAM) ', text[at + len(marker):], re.M)
            end = at + len(marker) + nxt.start() if nxt else len(text)
            block = text[start:end]
            old = f'dot({source}_tex({source}_pos).rgb, vec3(0.299, 0.587, 0.114))'
            bind = f'//!BIND {source}\n'
            assert block.count(old) == 1 and block.count(bind) == 1, f'LUMA_{side}_{level}'
            new = f'AA_{side}_{level}_tex({source}_pos).r'
            ch = block.replace(old, new, 1).replace(bind, bind + f'//!BIND AA_{side}_{level}\n', 1)
            if side == 'B':
                assert f'gg_b({new})' in ch, 'gain compensation lost'
            if level in ('S', 'E'):
                assert f'ENERGY_{side}_tex({source}_pos).r' in ch, 'energy lost'
            reps.append((start, end, ch))
    for start, end, ch in sorted(reps, reverse=True):
        text = text[:start] + ch + text[end:]
    at = text.index('//!SAVE LUMA_A_S\n')
    start = text.rfind('//!HOOK FRAME_MIX\n', 0, at)
    text = text[:start] + aa_pyramid._passes() + text[start:]
    assert text.count('//!HOOK FRAME_MIX') == original.count('//!HOOK FRAME_MIX') + 8
    assert len(reps) == 2 * len(levels)
    return text


ap = argparse.ArgumentParser()
ap.add_argument('src', type=Path); ap.add_argument('out', type=Path); ap.add_argument('--levels', required=True)
ap.add_argument("--any-base", action="store_true", help="a generated variant of High (e.g. ALIAS_REACH=5): the structural checks still run")
ap.add_argument("--s-width", type=int, default=16, choices=(16, 32), help="the 1/16 level box: 16 (the cascade as GPT built it) or 32 (4 x 4 taps of the 8 px level)")
a = ap.parse_args()
lv = a.levels.split(',')
assert set(lv) <= {'H', 'Q', 'E', 'S'}, lv
out = apply(a.src.read_text(), lv, a.any_base)
if a.s_width == 32:
    # widen the cascade's S pass (both sides) from 2 x 2 taps of AA_*_E at +-0.5 texel to 4 x 4 at +-0.5, +-1.5
    for side in ('A', 'B'):
        i = out.index(f'//!SAVE AA_{side}_S\n')
        j = out.index('return vec4(0.25 * s, 0.0, 0.0, 0.0);', i)
        k = out.index('float s = ', i)
        assert k < j
        taps = ' + '.join(f'AA_{side}_E_tex(uv + vec2({x:.1f}, {y:.1f}) * o)' + '.r'
                          for y in (-3, -1, 1, 3) for x in (-3, -1, 1, 3))
        out = out[:k] + f'float s = 0.25 * ({taps});' + out[out.index(';', k) + 1:]
        assert out.count(f'AA_{side}_E_tex(uv + vec2(3.0, 3.0) * o).r') == 1
    print('S box widened to 32 px')
a.out.write_text(out)
print(a.out, 'levels', ','.join(lv))
