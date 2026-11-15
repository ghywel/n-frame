#!/usr/bin/env python3
"""One-change WARP_VOTE=2 diagnostic; see VOTE-SAMPLING.md before interpreting it."""

import argparse
import itertools
import json
from pathlib import Path


OLD = """    {   // WARP_VOTE=2: the winner scored at half resolution (the weight read bilinearly, the vector from the nearest texel,
        // so no in-between vector is ever sampled)
        float wv_w = WV_FLOW_F_AB_PICK_tex(HOOKED_pos).z;
        if (wv_w > 0.0) {
            vec2 wv_uv = (floor(HOOKED_pos * WV_FLOW_F_AB_PICK_size) + 0.5) / WV_FLOW_F_AB_PICK_size;
            vec2 wv_v = WV_FLOW_F_AB_PICK_tex(wv_uv).xy * HOOKED_pt;
"""

NEW = """    {   // RIPPLE diagnostic: confidence and vector belong to the same nearest half-resolution texel.
        // This prevents neighboring confidence from drawing a locally rejected candidate.
        vec2 wv_uv = (floor(HOOKED_pos * WV_FLOW_F_AB_PICK_size) + 0.5) / WV_FLOW_F_AB_PICK_size;
        float wv_w = WV_FLOW_F_AB_PICK_tex(wv_uv).z;
        if (wv_w > 0.0) {
            vec2 wv_v = WV_FLOW_F_AB_PICK_tex(wv_uv).xy * HOOKED_pt;
"""


def add_nearest_weight(text: str) -> str:
    """Change only DRAW's confidence sampling; refuse an unexpected source shape."""
    if text.count(OLD) != 1:
        raise ValueError(f"expected exactly one light-vote DRAW anchor, found {text.count(OLD)}")
    return text.replace(OLD, NEW, 1)


def smoothstep(lo: float, hi: float, x: float) -> float:
    t = min(1.0, max(0.0, (x - lo) / (hi - lo)))
    return t * t * (3.0 - 2.0 * t)


def bilinear(weights, x: float, y: float) -> float:
    return ((1.0 - x) * (1.0 - y) * weights[0]
            + x * (1.0 - y) * weights[1]
            + (1.0 - x) * y * weights[2] + x * y * weights[3])


def draw_pick(weights, vectors, x: float, y: float, nearest_weight: bool):
    nearest = int(x > 0.5) + 2 * int(y > 0.5)
    weight = weights[nearest] if nearest_weight else bilinear(weights, x, y)
    return vectors[nearest], weight


def control() -> dict:
    """Scalar horizontal-flow witness, with GLSL's exact weight and ownership rules."""
    c0, candidate, a_flow_at_candidate = 8.0, -16.0, 8.0
    cost0, best_cost = 0.08, 0.01
    before_ownership = ((1.0 - smoothstep(0.25, 0.5, best_cost / cost0))
                        * smoothstep(2.0 / 255.0, 4.0 / 255.0, cost0 - best_cost))
    tolerance = max(0.5 * abs(candidate - c0), 1.0)
    own_weight = before_ownership * (1.0 - smoothstep(
        0.5, 1.0, abs(a_flow_at_candidate - candidate) / tolerance))
    assert before_ownership == 1.0 and own_weight == 0.0
    weights = [own_weight, 1.0, 1.0, 1.0]
    vectors = [candidate, 8.0, 8.0, 8.0]
    old_vector, old_weight = draw_pick(weights, vectors, 0.25, 0.25, False)
    new_vector, new_weight = draw_pick(weights, vectors, 0.25, 0.25, True)
    assert old_vector == new_vector == candidate
    assert old_weight == 7.0 / 16.0 and new_weight == 0.0

    # All four nearest-cell quadrants; no rejected cell may borrow any confidence.
    checked = 0
    for weights in itertools.product((0.0, 0.25, 1.0), repeat=4):
        for x, y in itertools.product((0.25, 0.75), repeat=2):
            nearest = int(x > 0.5) + 2 * int(y > 0.5)
            if weights[nearest] == 0.0:
                _, weight = draw_pick(weights, vectors, x, y, True)
                assert weight == 0.0
                checked += 1
            if len(set(weights)) == 1:
                assert draw_pick(weights, vectors, x, y, False) == draw_pick(weights, vectors, x, y, True)
    assert bilinear([0.0] * 4, 0.25, 0.25) == 0.0

    fixture = "prefix\n" + OLD + "suffix\n"
    assert add_nearest_weight(fixture) == "prefix\n" + NEW + "suffix\n"
    for bad in ("", OLD + OLD, NEW):
        try:
            add_nearest_weight(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("unexpected transform anchor was accepted")

    return {
        "scope": "CPU rule replay only; no GPU or footage result",
        "candidate_px": candidate,
        "baseline_px": c0,
        "before_ownership": before_ownership,
        "own_weight": own_weight,
        "original_draw_weight": old_weight,
        "nearest_draw_weight": new_weight,
        "rejected_cell_quadrants_checked": checked,
        "equal_weight_control": "pass",
        "anchor_refusal_control": "pass",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    if args.control:
        if args.source or args.output:
            parser.error("--control takes no input or output path")
        print(json.dumps(control(), indent=2))
    else:
        if args.source is None or args.output is None:
            parser.error("provide source and output, or --control")
        if args.source.resolve() == args.output.resolve():
            parser.error("output must differ from source")
        args.output.write_text(add_nearest_weight(args.source.read_text()))


if __name__ == "__main__":
    main()
