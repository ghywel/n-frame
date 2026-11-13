#!/usr/bin/env python3
"""Dump High's own final flow fields for a motionstress case, as the final pass reads them (2026-11-13).

    flowdump.py <unpruned-high.glsl> <case-dir> <out-dir>     writes fab.npy, fba.npy (px, full-res grid, per output frame)
                                                             and sup.npy (the SUPPORT texture's three channels)

The unpruned High (PRUNE=0, the shipped switches) keeps its half-resolution B->A chain. Three diagnostic copies replace
the final pass's body with one read at the output position, encoded 0.5 + px / 256 in 16 bits; the render is the
motionstress runner's own (exact 1/120 timestamps, 24 -> 60), converted to rgb48le INSIDE the filter graph (the
field-read rule). Calibrate before use: a static case must read exactly zero and a known translation its speed.
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

FF = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
ENV = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
FINAL = '//!DESC [high] motion-compensated warp\n'
HOOK = 'vec4 hook() {\n    // Too different to blend'
READS = {'fab': ('', 'return vec4(0.5 + FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 / 256.0, 0.5, 1.0);'),
         'fba': ('//!BIND FLOW_H_BA\n', 'return vec4(0.5 + FLOW_H_BA_tex(HOOKED_pos).xy * 2.0 / 256.0, 0.5, 1.0);'),
         'sup': ('', 'return vec4(SUPPORT_tex(HOOKED_pos).rgb, 1.0);')}


def variant(text, name):
    bind, ret = READS[name]
    assert text.count(FINAL) == 1 and '//!SAVE FLOW_H_BA\n' in text, 'needs the unpruned High'
    i = text.index(FINAL)
    head, tail = text[:i], text[i:]
    assert tail.count(HOOK) == 1
    tail = tail.replace(HOOK, 'vec4 hook() {\n    ' + ret + '\n    // Too different to blend', 1)
    if bind:
        j = head.rindex('//!SAVE FRAME_MIX\n')
        head = head[:j] + bind + head[j:]
    return head + tail


def main(shader, case, out):
    out.mkdir(parents=True, exist_ok=True)
    text = Path(shader).read_text()
    probe = subprocess.run([os.path.join(os.path.dirname(FF), 'ffprobe'), '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=width,height', '-of', 'csv=p=0', str(case / 'source.mkv')], capture_output=True, text=True)
    w, h = map(int, probe.stdout.strip().split(','))
    for name in READS:
        g = out / f'diag-{name}.glsl'
        g.write_text(variant(text, name))
        r = subprocess.run([FF, '-nostdin', '-y', '-v', 'warning', '-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk',
                            '-i', str(case / 'source.mkv'), '-vf',
                            f'settb=expr=1/120,setpts=N*5,libplacebo=fps=60:frame_mixer=custom_n:custom_shader_path={g}:dithering=none,format=rgb48le',
                            '-f', 'rawvideo', '-'], capture_output=True, env=ENV)
        err = r.stderr.decode(errors='replace').lower()
        if r.returncode or err.count('hook skipped') > 2 or any(x in err for x in ('compile status', 'disabling', 'failed to')):
            raise SystemExit(f'REFUSED {name}: {err[-800:]}')
        a = np.frombuffer(r.stdout, '<u2').reshape(-1, h, w, 3).astype(np.float32) / 65535
        np.save(out / f'{name}.npy', ((a[..., :2] - 0.5) * 256).astype(np.float32) if name != 'sup' else a)
        print(name, a.shape, flush=True)


if __name__ == '__main__':
    main(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]))
