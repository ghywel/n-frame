#!/usr/bin/env python3
"""Actual BAR_REDECIDE GLSL with exact input flow, isolated on the GPU.

RUN-ON: mac (or arc with the supported rgba64le output selected here)
COMMAND: python3 tests/probes/cage/bar_gpu.py --out "$NP_SCRATCH/bar-review/gpu"
PREDICTION: CHAT-LEDGER G006/G007, before rendering. Correct +6/-6 seeds on
period-9 bars become -3/+3 within .2 px at the median; correct +3 stays +3.
The bypass reads each known seed within .01 px and flat background within .01.
REFUTED-BY: those conditions fail. Instrument failure is reported separately.
COST: eight short 256x128 renders, sequential. No shipped shader modifications.

The bars pass is imported verbatim from tests/bar_redecide.py. Only its inputs
and final diagnostic output are supplied here. This isolates the decision's
causal effect; it is not an end-to-end High regression. The marker run is
descriptive: a strong co-moving marker should give a locally distinguishable
basin, but no GPU marker coverage threshold is preregistered.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bar_redecide as bar

W, H, INPUT_FRAMES = 256, 128, 16
FIRST, LAST = 3, 12
OUTPUT_FRAMES = LAST-FIRST+1


def shader(speed, enable):
    pre = f"""//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND FRAME1
//!SAVE LUMA_A_H
//!WIDTH HOOKED.w 2 /
//!HEIGHT HOOKED.h 2 /
//!COMPONENTS 1
//!DESC [probe] half-res luma for the actual bars pass
vec4 hook() {{ return vec4(dot(HOOKED_tex(HOOKED_pos).rgb, vec3(0.299,0.587,0.114))); }}

//!HOOK FRAME_MIX
//!BIND HOOKED
//!SAVE FLOW_H_AB
//!WIDTH HOOKED.w 2 /
//!HEIGHT HOOKED.h 2 /
//!COMPONENTS 2
//!DESC [probe] exact seed in half-res pixels
vec4 hook() {{ return vec4(HOOKED_pos.y < 0.75 ? {float(speed)/2.0} : 0.0, 0.0, 0.0, 0.0); }}

"""
    post = """
//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND FLOW_H_AB
//!DESC [probe] split-encoded flow in full-res pixels
vec4 hook() {
    vec2 v = texelFetch(FLOW_H_AB_raw, ivec2(HOOKED_pos * FLOW_H_AB_size), 0).xy * 2.0;
    vec2 h = v / 2.0;
    vec2 w = floor(h);
    float packed = ((w.x + 16.0) * 32.0 + w.y + 16.0) / 1024.0;
    return vec4(fract(h.x), fract(h.y), packed, 1.0);
}
"""
    return pre + (bar.PASS if enable else "") + post


def source(path, speed, marker):
    x = np.arange(W, dtype=float)+.5
    with path.open("wb") as stream:
        for t in range(INPUT_FRAMES):
            u = x-speed*t
            line = .5+.25*np.cos(2*np.pi*(u % 9)/9)+marker*np.tanh((u-96)/4)
            a = np.broadcast_to(line, (H, W)).copy()
            a[3*H//4:] = .5
            rgb = np.repeat(np.rint(np.clip(a, 0, 1)*65535).astype("<u2")[..., None], 3, axis=-1)
            stream.write(rgb.tobytes())


def decode(path):
    expected = OUTPUT_FRAMES*H*W*4*2
    if path.stat().st_size != expected:
        raise ValueError(f"short/wrong export: {path.name}: {path.stat().st_size} bytes, expected {expected}")
    a = np.fromfile(path, dtype="<u2").reshape(OUTPUT_FRAMES, H, W, 4).astype(float)/65535
    packed = a[..., 2]*1024
    if np.max(abs(packed-np.rint(packed))) > .05:
        raise ValueError("split whole-part readback is not calibrated")
    whole = np.rint(packed).astype(int)
    v = np.stack([2*(whole//32-16+a[..., 0]), 2*(whole%32-16+a[..., 1])], axis=-1)
    if not np.isfinite(v).all():
        raise ValueError("nonfinite flow")
    return v


def render(ff, out, name, speed, enable, marker=0.0):
    src, glsl, dst = out/f"{name}.rgb48", out/f"{name}.glsl", out/f"{name}.rgba64"
    source(src, speed, marker)
    glsl.write_text(shader(speed, enable))
    env = os.environ.copy()
    if sys.platform == "darwin":
        env["MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS"] = "0"
        env["MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE"] = "1"
    graph = (f"libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path={glsl}:dithering=none,"
             f"format=rgba64le,select='between(n,{FIRST},{LAST})'")
    command = [ff, "-nostdin", "-y", "-hide_banner", "-loglevel", "warning",
               "-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk",
               "-f", "rawvideo", "-pixel_format", "rgb48le", "-video_size", f"{W}x{H}",
               "-framerate", "24", "-i", str(src), "-vf", graph, "-fps_mode", "passthrough",
               "-f", "rawvideo", "-pix_fmt", "rgba64le", str(dst)]
    p = subprocess.run(command, capture_output=True, text=True, env=env)
    (out/f"{name}.log").write_text(p.stderr)
    if p.returncode or any(s in p.stderr.lower() for s in
                          ("compile status", "disabling", "failed to", "error reinit")):
        raise ValueError(f"render refused: {name}, see its log")
    v = decode(dst)
    interior = v[:, 16:80, 32:-32]
    row = {"name": name, "speed": speed, "bars_enabled": enable, "marker": marker,
           "frames": OUTPUT_FRAMES, "median_xy": np.median(interior, axis=(0, 1, 2)).tolist(),
           "x_p05_p95": np.percentile(interior[..., 0], [5, 95]).tolist(),
           "background_max_abs": float(np.max(abs(v[:, 112:120, 32:-32]))),
           "output_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
           "shader_sha256": hashlib.sha256(glsl.read_bytes()).hexdigest()}
    if marker:
        values = []
        for i, t in enumerate(range(FIRST, LAST+1)):
            c = int(96+speed*t)
            values.append(v[i, 16:80, c-4:c+4, 0].ravel())
        z = np.concatenate(values)
        row["marker_local_median"] = float(np.median(z))
        row["marker_local_within_point2_of_truth"] = float(np.mean(abs(z-speed) < .2))
    print(json.dumps(row), flush=True)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--ffmpeg", default=os.environ.get("FFMPEG", str(Path.home()/"np-build/ffmpeg/ffmpeg")))
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    instrument = {}
    for speed in (6, -6, 3):
        row = render(args.ffmpeg, out, f"bypass_{speed}", speed, False)
        rows.append(row)
        instrument[f"bypass_{speed}"] = (abs(row["median_xy"][0]-speed) < .01 and
                                         abs(row["median_xy"][1]) < .01 and row["background_max_abs"] < .01)
        if not instrument[f"bypass_{speed}"]:
            raise ValueError(f"bypass instrument failed at {speed}")
    # A short export must be refused by the same decoder before the scientific runs.
    short = out/"short-control.rgba64"
    short.write_bytes((out/"bypass_6.rgba64").read_bytes()[:-8])
    try:
        decode(short)
    except ValueError:
        instrument["short_export_refused"] = True
    else:
        raise ValueError("decoder accepted a truncated export")
    hypotheses = {}
    for speed, expected in ((6, -3), (-6, 3), (3, 3)):
        row = render(args.ffmpeg, out, f"bars_{speed}", speed, True)
        rows.append(row)
        hypotheses[f"choice_{speed}"] = abs(row["median_xy"][0]-expected) < .2
        instrument[f"background_{speed}"] = row["background_max_abs"] < .01
    repeat = render(args.ffmpeg, out, "bars_6_repeat", 6, True)
    rows.append(repeat)
    instrument["repeat_byte_identical"] = repeat["output_sha256"] == rows[3]["output_sha256"]
    rows.append(render(args.ffmpeg, out, "marker_6", 6, True, .15))
    result = {"instrument": instrument, "hypotheses": hypotheses, "runs": rows,
              "bar_pass_sha256": hashlib.sha256(bar.PASS.encode()).hexdigest(),
              "ffmpeg_sha256": hashlib.sha256(Path(args.ffmpeg).read_bytes()).hexdigest(),
              "scope": "isolated actual GLSL pass, correct seeded flow; not end-to-end High"}
    result["verdict"] = ("INSTRUMENT_REFUSED" if not all(instrument.values()) else
                         "PREDICTIONS_HELD" if all(hypotheses.values()) else "PREDICTIONS_REFUTED")
    (out/"results.json").write_text(json.dumps(result, indent=2)+"\n")
    print(result["verdict"], flush=True)
    return 1 if not all(instrument.values()) else 0 if all(hypotheses.values()) else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as e:
        print(f"INSTRUMENT REFUSED: {e}", file=sys.stderr)
        raise SystemExit(1)
