#!/usr/bin/env python3
"""Prior-High luma-only cascade-box diagnostic; see AA-PYRAMID.md for its known risks."""

import argparse
import hashlib
import json
import re
from pathlib import Path


PREV_HIGH_SHA256 = "b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece"
LEVELS = (("H", 2), ("Q", 4), ("E", 8), ("S", 16))


def _passes() -> str:
    blocks = []
    for side, source in (("A", "HOOKED"), ("B", "NEXT")):
        previous = source
        for level, divisor in LEVELS:
            name = f"AA_{side}_{level}"
            reads = []
            for x, y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                sample = f"{previous}_tex(uv + vec2({x}.0, {y}.0) * o)"
                reads.append(f"dot({sample}.rgb, vec3(0.299, 0.587, 0.114))" if level == "H" else f"{sample}.r")
            value = "\n             + ".join(reads)
            blocks.append(f"""//!HOOK FRAME_MIX
//!BIND {previous}
//!SAVE {name}
//!WIDTH HOOKED.w {divisor} /
//!HEIGHT HOOKED.h {divisor} /
//!COMPONENTS 1
//!DESC [ripple AA] raw frame {side} luma: four-tap box cascade to {level} (diagnostic only)
vec4 hook() {{
    vec2 uv = {previous}_pos;
    vec2 o = 0.5 * {previous}_pt;
    float s = {value};
    return vec4(0.25 * s, 0.0, 0.0, 0.0);
}}

""")
            previous = name
    return "".join(blocks)


def add_cascade_box(text: str) -> str:
    """Change only eight luma expressions/binds and add eight AA source passes."""
    if hashlib.sha256(text.encode()).hexdigest() != PREV_HIGH_SHA256:
        raise ValueError("expected the exact registered prior High; re-baseline before applying this diagnostic")
    original = text
    replacements = []
    for side, source in (("A", "HOOKED"), ("B", "NEXT")):
        for level, _ in LEVELS:
            marker = f"//!SAVE LUMA_{side}_{level}\n"
            if text.count(marker) != 1:
                raise ValueError(f"expected exactly one {marker.strip()}")
            at = text.index(marker)
            start = text.rfind("//!HOOK FRAME_MIX\n", 0, at)
            following = re.search(r"^//!(?:HOOK|TEXTURE|PARAM) ", text[at + len(marker):], re.M)
            end = at + len(marker) + following.start() if following else len(text)
            block = text[start:end]
            old = f"dot({source}_tex({source}_pos).rgb, vec3(0.299, 0.587, 0.114))"
            bind = f"//!BIND {source}\n"
            if block.count(old) != 1 or block.count(bind) != 1:
                raise ValueError(f"unexpected source-luma formation in LUMA_{side}_{level}")
            new = f"AA_{side}_{level}_tex({source}_pos).r"
            changed = block.replace(old, new, 1).replace(bind, bind + f"//!BIND AA_{side}_{level}\n", 1)
            # Preserve compensation and energy expressions, not merely their binding names.
            if side == "B" and f"gg_b({new})" not in changed:
                raise ValueError("B gain compensation was not retained")
            if level in ("S", "E") and f"ENERGY_{side}_tex({source}_pos).r" not in changed:
                raise ValueError("texture energy expression was not retained")
            replacements.append((start, end, changed))
    for start, end, changed in sorted(replacements, reverse=True):
        text = text[:start] + changed + text[end:]
    at = text.index("//!SAVE LUMA_A_S\n")
    start = text.rfind("//!HOOK FRAME_MIX\n", 0, at)
    text = text[:start] + _passes() + text[start:]
    if text.count("//!HOOK FRAME_MIX") != original.count("//!HOOK FRAME_MIX") + 8:
        raise ValueError("unexpected hook-count change")
    return text


def control() -> dict:
    import numpy as np

    def reduce_axis(a, out_n):
        # Pixel-center coordinates; clamped linear texture reads, exactly the shader's two taps per axis.
        uv = (np.arange(out_n) + 0.5) / out_n
        p = uv * len(a) - 0.5
        return 0.5 * (np.interp(p - 0.5, np.arange(len(a)), a)
                      + np.interp(p + 0.5, np.arange(len(a)), a))

    n = 256
    rng = np.random.default_rng(20261115)
    original = rng.random(n)
    value = original.copy()
    worst = 0.0
    for _, divisor in LEVELS:
        value = reduce_axis(value, n // divisor)
        exact = original.reshape(-1, divisor).mean(axis=1)
        worst = max(worst, float(np.max(np.abs(value - exact))))
    assert worst < 1e-14
    value = (np.arange(n) % 2).astype(float)
    for _, divisor in LEVELS:
        value = reduce_axis(value, n // divisor)
        assert np.max(np.abs(value - 0.5)) < 1e-14
    n = 1080
    ramp = (np.arange(n) + 0.5) / n
    constant = np.full(n, 0.375)
    dimensions = []
    ramp_error = 0.0
    for _, divisor in LEVELS:
        out_n = int(np.floor(n / divisor + 0.5))
        dimensions.append(out_n)
        ramp = reduce_axis(ramp, out_n)
        constant = reduce_axis(constant, out_n)
        expected = (np.arange(out_n) + 0.5) / out_n
        ramp_error = max(ramp_error, float(np.max(np.abs(ramp[2:-2] - expected[2:-2]))))
        assert np.max(np.abs(constant - 0.375)) < 1e-14
    assert ramp_error < 1e-14
    return {"scope": "CPU sampling arithmetic only; no GLSL execution",
            "divisible_box_max_error": worst, "checkerboard": "mean preserved at every level",
            "constant": "preserved", "height1080_dimensions": dimensions,
            "height1080_interior_ramp_max_error": ramp_error}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    if args.control:
        if args.source or args.output:
            parser.error("--control takes no paths")
        print(json.dumps(control(), indent=2))
    else:
        if args.source is None or args.output is None:
            parser.error("provide source and output, or --control")
        if args.source.resolve() == args.output.resolve():
            parser.error("output must differ from source")
        args.output.write_text(add_cascade_box(args.source.read_text()))


if __name__ == "__main__":
    main()
