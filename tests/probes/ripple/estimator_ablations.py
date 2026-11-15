#!/usr/bin/env python3
"""Narrow prior-High diagnostics; registered in ESTIMATOR-ABLATIONS.md."""

import argparse
import hashlib
import re
from pathlib import Path


PREV_HIGH_SHA256 = "b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece"
TRUST_OLD = "    bool trusted = rt < SEED_RT_MAX && length(prev_e) > 0.0;"
TRUST_NEW = "    bool trusted = false;  // RIPPLE diagnostic: no E temporal candidate or temporal-distance prior"
H_WRITE = """    vec4 result = vec4(best_off / LUMA_A_H_pt, 0.0, 0.0);
    imageStore(FLOW_H_AB_CACHE, coord, result);
    return result;
"""
H_OVERRIDE = """    // RIPPLE diagnostic: discard this H pass's data search and subpixel correction; keep the Q seed.
    best_off = base_off;
"""


def _require_prev_high(text: str):
    if re.search(r"\bWARP_VOTE\b", text):
        raise ValueError("expected prior High with WARP_VOTE=0, not a voting shader")
    required = (
        "//!SAVE SUPPORT\n",
        "//!DESC [high] variational Q A->B (iter 8)\n",
        "//!DESC [high] variational H A->B (iter 4)\n",
        "//!DESC [high] motion-compensated warp\n",
    )
    for marker in required:
        if text.count(marker) != 1:
            raise ValueError(f"unexpected prior-High structure: {marker.strip()!r}")
    if "//!SAVE FLOW_H_BA\n" in text:
        raise ValueError("expected the pruned prior-High half-resolution chain")
    if "RIPPLE diagnostic:" in text:
        raise ValueError("apply each estimator ablation separately to unmodified prior High")
    if hashlib.sha256(text.encode()).hexdigest() != PREV_HIGH_SHA256:
        raise ValueError("input differs from the registered prior High; re-baseline before applying this diagnostic")


def _pass_span(text: str, description: str):
    marker = f"//!DESC {description}\n"
    if text.count(marker) != 1:
        raise ValueError(f"expected exactly one pass {description!r}")
    at = text.index(marker)
    start = text.rfind("//!HOOK FRAME_MIX\n", 0, at)
    if start < 0:
        raise ValueError(f"no FRAME_MIX hook before {description!r}")
    following = re.search(r"^//!(?:HOOK|TEXTURE|PARAM) ", text[at + len(marker):], re.M)
    end = at + len(marker) + following.start() if following else len(text)
    return start, end


def add_e_temporal_off(text: str) -> str:
    """Disable candidate C and its prior at E in both directions; retain other memory."""
    _require_prev_high(text)
    if text.count(TRUST_OLD) != 2:
        raise ValueError("expected exactly two original E temporal trust booleans")
    edits = []
    for direction, cache in (("A->B", "AB"), ("B->A", "BA")):
        start, end = _pass_span(text, f"[high] refine flow {direction} (1/8 res)")
        block = text[start:end]
        expected = (
            TRUST_OLD,
            "    float tl = trusted ? SEED_TEMP_LAMBDA : 0.0;",
            "    float score_c = trusted ? sad_c ",
            f"    imageStore(FLOW_E_{cache}_CACHE, coord, result);",
        )
        if any(block.count(anchor) != 1 for anchor in expected):
            raise ValueError(f"unexpected E temporal selection/cache structure in {direction}")
        edits.append((start, end, block.replace(TRUST_OLD, TRUST_NEW, 1)))
    for start, end, block in reversed(edits):
        text = text[:start] + block + text[end:]
    return text


def add_h_data_refine_off(text: str) -> str:
    """Keep Q→H seed and downstream H stages; discard only H search/subpixel updates."""
    _require_prev_high(text)
    start, end = _pass_span(text, "[high] refine flow A->B (half res)")
    block = text[start:end]
    expected = (
        "    if (!pair_changed)\n        return imageLoad(FLOW_H_AB_CACHE, coord);",
        "    vec2 base_off = FLOW_Q_AB_tex(snap_texel(uv_a, FLOW_Q_AB_size)).xy * 2.0 * LUMA_A_H_pt;",
        "    vec2 best_off = base_off;",
        H_WRITE,
    )
    if any(block.count(anchor) != 1 for anchor in expected):
        raise ValueError("unexpected H seed/search/cache structure")
    block = block.replace(H_WRITE, H_OVERRIDE + H_WRITE, 1)
    return text[:start] + block + text[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("e-temporal-off", "h-data-refine-off"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("output must differ from source")
    transform = add_e_temporal_off if args.mode == "e-temporal-off" else add_h_data_refine_off
    args.output.write_text(transform(args.source.read_text()))


if __name__ == "__main__":
    main()
