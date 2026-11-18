#!/usr/bin/env python3
"""Dump what High's final pass decides at every pixel of a real clip, at native 24000/1001 -> 48000/1001 (2026-11-18).

    fielddump.py <shader.glsl> <source.mkv> <out-dir> [--first N] [--last N] [--keep a:b] [--sub S] [--ffmpeg PATH]

Three diagnostic copies of the shader replace the body of the final pass ("[high] motion-compensated warp") with
one read at the output position, each at the point in the body where that quantity exists:

  flow  FLOW_H_AB in full-res px (x, y) and the coherence gate's unwarp weight (the share of the plain A/B blend)
  vote  WARP_VOTE's picked vector in full-res px (x, y) at the nearest texel, and its weight (0 = High's own vector)
  sup   the SUPPORT texture's three channels, which the gate reads

Vectors are encoded 0.5 + px / 256 (so +-128 px, 0.004 px a code) and weights as they are, and read back from
rgb48le converted INSIDE the filter graph (tests/TESTING.md's field-read rule). The render is ripple/render.py's:
exact input PTS, libplacebo at twice the source rate, dithering off, MoltenVK's deterministic switches.

Output frame 2k is source frame k (the retained instant) and 2k+1 the midpoint of pair (k, k+1). Only the
midpoints of the kept pairs are saved, subsampled by --sub (2 by default: the flow is half resolution anyway),
as float16 arrays <name>.npy of shape (pairs, H/sub, W/sub, 3), with pairs.json naming the source pair of each.

The source can be trimmed (--first/--last, source frame numbers, inclusive) so the shader's history starts there;
pair numbers in the output stay those of the untrimmed source. A diagnostic copy that fails to compile makes
libplacebo fall back to its own mixer silently, which would hand back a picture, not a field: every run is
refused unless its stderr is free of compile errors and hook skips past the window's lead-in, and calibrate.py
must pass (a still reads exactly zero, a known translation its speed) before any of it is believed.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ENV = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
FINAL = '//!DESC [high] motion-compensated warp\n'
AT_WARPED = '    vec4 warped = mix(warped_a, warped_b, mix_t);\n'
AT_VOTE = '        float wv_w = WV_FLOW_F_AB_PICK_tex(HOOKED_pos).z;\n'
AT_HOOK = 'vec4 hook() {\n    // Too different to blend'

READS = {
    'flow': (AT_WARPED, AT_WARPED.replace('    vec4 warped', '    return vec4(0.5 + FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 / 256.0, unwarped, 1.0);\n    vec4 warped')),
    'vote': (AT_VOTE, AT_VOTE + '        { vec2 q = (floor(HOOKED_pos * WV_FLOW_F_AB_PICK_size) + 0.5) / WV_FLOW_F_AB_PICK_size;\n'
                                '          return vec4(0.5 + WV_FLOW_F_AB_PICK_tex(q).xy / 256.0, wv_w, 1.0); }\n'),
    'sup': (AT_HOOK, 'vec4 hook() {\n    return vec4(SUPPORT_tex(HOOKED_pos).rgb, 1.0);\n    // Too different to blend'),
    # The levels, horizontal components only, each in full-res px (the pan is horizontal): every texture's own unit
    # read from its consumer (1/16 texels x16: the 1/8 refine reads seeds.xy * 2 in 1/8 texels; 1/8 texels x8;
    # quarter texels x4; GLOBAL_SHIFT in coarse texels x16).
    'lv1': (AT_HOOK, 'vec4 hook() {\n    return vec4(0.5 + FLOW_S_AB_tex(HOOKED_pos).x * 16.0 / 256.0, '
                     '0.5 + FLOW_E_AB_RAW_tex(HOOKED_pos).x * 8.0 / 256.0, 0.5 + FLOW_E_AB_tex(HOOKED_pos).x * 8.0 / 256.0, 1.0);\n'
                     '    // Too different to blend'),
    'lv2': (AT_HOOK, 'vec4 hook() {\n    return vec4(0.5 + FLOW_Q_AB_tex(HOOKED_pos).x * 4.0 / 256.0, '
                     '0.5 + GLOBAL_SHIFT_tex(vec2(0.5)).x * 16.0 / 256.0, 0.5 + FLOW_S_AB_tex(HOOKED_pos).z * 16.0 / 256.0, 1.0);\n'
                     '    // Too different to blend'),
}
BINDS = {'lv1': ('FLOW_S_AB', 'FLOW_E_AB_RAW', 'FLOW_E_AB'), 'lv2': ('FLOW_Q_AB', 'GLOBAL_SHIFT', 'FLOW_S_AB')}
DECODE = {'flow': (True, True, False), 'vote': (True, True, False), 'sup': (False, False, False),
          'lv1': (True, True, True), 'lv2': (True, True, True)}


def variant(text, name):
    at, new = READS[name]
    assert text.count(FINAL) == 1, 'no single final warp pass'
    i = text.index(FINAL)
    head, tail = text[:i], text[i:]
    # the final pass's own FLOW_H -> px factor: 2.0 in the 1080p-tuned files, 4.0 in a -4k twin (scale_shader.py doubles
    # it). Read with a fixed 2.0, a 4K twin's field came back at exactly half (2026-11-18, the barn's 4K check).
    import re
    m = re.findall(r'vec2 flow_ab = FLOW_H_AB_tex\(HOOKED_pos\)\.xy \* ([0-9.]+) \* HOOKED_pt;', tail)
    assert len(m) == 1, f"the final pass's flow factor: {m}"
    new = new.replace('FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 / 256.0', f'FLOW_H_AB_tex(HOOKED_pos).xy * {m[0]} / 256.0')
    assert tail.count(at) == 1, f'{name}: insertion point not found exactly once in the final pass'
    tail = tail.replace(at, new, 1)
    if name in BINDS:
        j = head.rindex('//!SAVE FRAME_MIX\n')
        for b in BINDS[name]:
            assert f'//!SAVE {b}\n' in head, f'{name}: no pass saves {b}'
        head = head[:j] + ''.join(f'//!BIND {b}\n' for b in BINDS[name] if f'//!BIND {b}\n' not in head[head.rindex('//!HOOK'):]) + head[j:]
    out = head + tail
    assert out != text
    return out


def probe(ffprobe, src):
    r = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                        'stream=width,height,r_frame_rate,nb_read_frames', '-of', 'json', str(src)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)['streams'][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shader'); ap.add_argument('source', type=Path); ap.add_argument('out', type=Path)
    ap.add_argument('--first', type=int, default=0); ap.add_argument('--last', type=int, default=None)
    ap.add_argument('--keep', default=None, help='source pairs a:b to save (first pair index a, last b, inclusive)')
    ap.add_argument('--sub', type=int, default=2)
    ap.add_argument('--only', default='flow,vote,sup')
    # libplacebo's own output format. Left to its default it outputs the SOURCE's format (yuv420p here), so the
    # field went RGB -> 4:2:0 limited YUV -> rgb48le and read (+6.75, +1.00) for a true (+7, +2) (calibrate.py,
    # 2026-11-18, the first run). 'yuv420p' reproduces that failure on purpose.
    ap.add_argument('--out-format', default='rgb48le')
    ap.add_argument('--ffmpeg', default=str(Path.home() / 'np-scratch-int/n-frame/np-build/ffmpeg/ffmpeg'))
    a = ap.parse_args()
    ffprobe = str(Path(a.ffmpeg).with_name('ffprobe'))
    a.out.mkdir(parents=True, exist_ok=True)
    m = probe(ffprobe, a.source)
    w, h = int(m['width']), int(m['height'])
    n_src = int(m['nb_read_frames'])
    last = n_src - 1 if a.last is None else a.last
    num, den = map(int, m['r_frame_rate'].split('/'))
    k0, k1 = (map(int, a.keep.split(':')) if a.keep else (a.first, last - 1))
    text = Path(a.shader).read_text()
    pairs = list(range(k0, k1 + 1))
    for name in a.only.split(','):
        g = a.out / f'diag-{name}.glsl'
        g.write_text(variant(text, name))
        vf = (f'trim=start_frame={a.first}:end_frame={last + 1},'
              f'settb=expr=1/{2 * num},setpts=N*{2 * den},'
              f'libplacebo=fps={2 * num}/{den}:frame_mixer=custom_n:custom_shader_path={g.resolve()}:dithering=none'
              f':format={a.out_format},format=rgb48le')
        cmd = [a.ffmpeg, '-nostdin', '-y', '-v', 'warning', '-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk',
               '-i', str(a.source), '-vf', vf, '-f', 'rawvideo', '-']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
        fb = w * h * 3 * 2
        keep = []
        j = 0
        while True:
            b = p.stdout.read(fb)
            if len(b) < fb:
                break
            src_pair = a.first + j // 2
            if j % 2 == 1 and k0 <= src_pair <= k1:
                f = np.frombuffer(b, '<u2').reshape(h, w, 3)[::a.sub, ::a.sub].astype(np.float32) / 65535
                for c, is_vec in enumerate(DECODE[name]):
                    if is_vec:
                        f[..., c] = (f[..., c] - 0.5) * 256
                keep.append(f.astype(np.float16))
            j += 1
        err = p.stderr.read().decode(errors='replace')
        p.wait()
        (a.out / f'{name}.log').write_text(err)
        low = err.lower()
        expected = 2 * (last + 1 - a.first)
        skipped = low.count('hook skipped')
        if p.returncode or any(x in low for x in ('compile status', 'disabling', 'failed to')) or skipped > 8:
            sys.exit(f'REFUSED {name}: rc {p.returncode}, {skipped} skips, {err[-1200:]}')
        if j != expected:
            sys.exit(f'REFUSED {name}: {j} output frames, expected {expected}')
        if len(keep) != len(pairs):
            sys.exit(f'REFUSED {name}: saved {len(keep)} pairs, expected {len(pairs)}')
        np.save(a.out / f'{name}.npy', np.stack(keep))
        print(f'{name}: {j} output frames read, {len(keep)} pairs saved ({skipped} hook skips at the lead-in)', flush=True)
    (a.out / 'pairs.json').write_text(json.dumps(dict(pairs=pairs, sub=a.sub, width=w, height=h, first=a.first, last=last,
                                                      shader=str(a.shader), source=str(a.source)), indent=1) + '\n')


if __name__ == '__main__':
    main()
