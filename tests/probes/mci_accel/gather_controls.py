#!/usr/bin/env python3
"""Bounded CPU scatter/gather equivalence controls; no renderer or GPU execution.

Usage: gather_controls.py /path/to/ffmpeg/libavfilter/vf_minterpolate.c
Reads the pinned tables. See GPU-DESIGN.md for the evidence boundary.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

M = 1024
SOURCE_SHA = '42e776a33821d7e08a20371a554513bca17ee427aac123ec0923bc4cbefad8e7'


def trunc_div(n, d):
    return (abs(n) // d) * (-1 if n < 0 else 1)


def clip(v, lo, hi):
    return min(hi, max(lo, v))


def tables(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('unregistered FFmpeg source; re-audit before changing the pin')
    text = raw.decode()
    result = {}
    for b in (4, 8, 16):
        match = re.search(r'obmc_linear' + str(2*b) + r'\[\d+\]\s*=\s*\{([^}]+)\}', text)
        values = [int(v) for v in re.findall(r'\d+', match[1])]
        assert len(values) == (2*b)**2
        result[b] = values
    return result


def fields(width, height, b, collision=False):
    """Two raw source-indexed maps, each component inside default [-32,32]."""
    result = []
    for direction in (0, 1):
        plane = []
        for by in range(height // b):
            row = []
            for bx in range(width // b):
                if collision:
                    # Drive many supports onto p=(40,40), keeping the proved bound.
                    mv = tuple(clip(2*(40-(v*b+b//2)), -32, 32) for v in (bx, by))
                else:
                    mv = ((17*bx+11*by+7*direction) % 65-32,
                          (13*bx+23*by+19*direction+1) % 65-32)
                row.append(mv)
            plane.append(row)
        result.append(plane)
    return result


def support(bx, by, raw, direction, alpha, b, width, height):
    a = alpha if direction else M-alpha
    sx = bx*b-b//2+trunc_div(raw[0]*a, M)
    sy = by*b-b//2+trunc_div(raw[1]*a, M)
    return (sx, sy, clip(sx, 0, width-1), clip(sy, 0, height-1),
            clip(sx+2*b, 0, width-1), clip(sy+2*b, 0, height-1))


def record(direction, bx, by, raw, weight, x, y, alpha, width, height):
    v = raw if not direction else (-raw[0], -raw[1])
    da = (clip(trunc_div(v[0]*alpha, M), -x, width-x-1),
          clip(trunc_div(v[1]*alpha, M), -y, height-y-1))
    db = (clip(trunc_div(-v[0]*(M-alpha), M), -x, width-x-1),
          clip(trunc_div(-v[1]*(M-alpha), M), -y, height-y-1))
    return ((direction, by, bx), weight, da, db)


def scatter(flow, width, height, b, alpha, table, cap=16, reverse=False):
    pixels = [[[] for _ in range(width)] for _ in range(height)]
    blocks = [(d, by, bx) for d in (0, 1) for by in range(height//b) for bx in range(width//b)]
    if reverse:
        blocks.reverse()
    for d, by, bx in blocks:
        raw = flow[d][by][bx]
        sx, sy, x0, y0, x1, y1 = support(bx, by, raw, d, alpha, b, width, height)
        for y in range(y0, y1):
            for x in range(x0, x1):
                weight = table[x-sx+(y-sy)*2*b]
                dst = pixels[y][x]
                if weight and (cap is None or len(dst) < cap):
                    dst.append(record(d, bx, by, raw, weight, x, y, alpha, width, height))
    return pixels


def block_range(p, b, s, count):
    # The lower bound on the anchor is strict; Python // supplies floor here.
    lo = (p-3*b//2-s)//b+1
    hi = (p+b//2+s)//b
    return range(max(0, lo), min(count-1, hi)+1)


def gather(flow, x, y, width, height, b, alpha, table):
    result = []
    for d in (0, 1):
        a = alpha if d else M-alpha
        s = (32*a)//M
        for by in block_range(y, b, s, height//b):
            for bx in block_range(x, b, s, width//b):
                raw = flow[d][by][bx]
                sx, sy, x0, y0, x1, y1 = support(bx, by, raw, d, alpha, b, width, height)
                if not (x0 <= x < x1 and y0 <= y < y1):
                    continue
                weight = table[x-sx+(y-sy)*2*b]
                if weight:
                    result.append(record(d, bx, by, raw, weight, x, y, alpha, width, height))
                    if len(result) == 16:
                        return result
    return result


def source_value(ref, plane, x, y):
    return (17*x+29*y+7*x*y+31*plane+59*ref+ref*x*3) % 256


def value(records, x, y, alpha, plane=0, hsub=0, vsub=0):
    if not records:
        records = [(None, 1, (0, 0), (0, 0))]
    total = weight_sum = 0
    for _, weight, da, db in records:
        for ref, offset, phase_weight in ((1, da, M-alpha), (2, db, alpha)):
            xx = (x >> hsub)+trunc_div(offset[0], 1 << hsub)
            yy = (y >> vsub)+trunc_div(offset[1], 1 << vsub)
            w = weight*phase_weight
            total += w*source_value(ref, plane, xx, yy)
            weight_sum += w
    assert total+(weight_sum//2) < 2**31
    return (total+weight_sum//2)//weight_sum


def chroma_last_writer(scattered, width, height, alpha):
    out = [[None for _ in range((width+1)//2)] for _ in range((height+1)//2)]
    for y in range(height):
        for x in range(width):
            out[y//2][x//2] = value(scattered[y][x], x, y, alpha, 1, 1, 1)
    return out


def run(table):
    checked = 0
    chroma_first_writer_differences = 0
    for width, height, b in ((67, 55, 16), (35, 29, 8), (19, 17, 4)):
        flow = fields(width, height, b)
        for alpha in (1, 257, 511, 512, 767, 1023):
            scattered = scatter(flow, width, height, b, alpha, table[b])
            for y in range(height):
                for x in range(width):
                    actual = gather(flow, x, y, width, height, b, alpha, table[b])
                    assert actual == scattered[y][x], (width, height, alpha, x, y)
                    assert value(actual, x, y, alpha) == value(scattered[y][x], x, y, alpha)
                    if x == width-1 or y == height-1:
                        assert not actual, 'CPU exclusive endpoint leaves the last row/column unsupported'
                    checked += 1
            chroma = chroma_last_writer(scattered, width, height, alpha)
            for cy, row in enumerate(chroma):
                for cx, expected in enumerate(row):
                    x, y = min(2*cx+1, width-1), min(2*cy+1, height-1)
                    actual = gather(flow, x, y, width, height, b, alpha, table[b])
                    assert value(actual, x, y, alpha, 1, 1, 1) == expected
                    first = value(scattered[2*cy][2*cx], 2*cx, 2*cy, alpha, 1, 1, 1)
                    chroma_first_writer_differences += first != expected
    assert chroma_first_writer_differences > 0
    assert trunc_div(-1, 2) == 0 and (-1)//2 == -1
    assert (2 >> 1)+trunc_div(-1, 2) == 1 and (2-1)//2 == 0

    width = height = 80
    b = 16
    alpha = 512
    flow = fields(width, height, b, collision=True)
    capped = scatter(flow, width, height, b, alpha, table[b])
    unlimited = scatter(flow, width, height, b, alpha, table[b], cap=None)
    reversed_order = scatter(flow, width, height, b, alpha, table[b], reverse=True)
    p = (40, 40)
    x, y = p
    selected = gather(flow, x, y, width, height, b, alpha, table[b])
    assert len(unlimited[y][x]) > 16 and len(selected) == 16
    assert selected == capped[y][x] == unlimited[y][x][:16]
    assert selected != reversed_order[y][x]
    capped_picture = value(selected, x, y, alpha)
    full_picture = value(unlimited[y][x], x, y, alpha)
    reversed_picture = value(reversed_order[y][x], x, y, alpha)
    assert capped_picture != full_picture and capped_picture != reversed_picture
    # Every possible default-bound component satisfies the support-displacement bound.
    for alpha in range(1, M):
        s = 32*alpha//M
        assert all(abs(trunc_div(mv*alpha, M)) <= s for mv in range(-32, 33))
    return dict(scope='CPU formula constructions only; not execution of the C filter, GPU or film evidence',
        pinned_source_sha256=SOURCE_SHA,ordered_scatter_gather_luma_sites=checked,
        chroma_first_writer_counterexample_count=chroma_first_writer_differences,
        negative_division='C truncation differs from floor; chroma address counterexample: 1 versus 0',
        last_row_and_column_use_zero_motion_fallback=True,
        cap_control=dict(pixel=p,eligible_pairs=len(unlimited[y][x]),accepted_pairs=len(selected),
            canonical_value=capped_picture,uncapped_value=full_picture,reversed_order_value=reversed_picture),
        phase_shift_bound_exhaustive_for_default_integer_mv=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ffmpeg_source', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(tables(args.ffmpeg_source)), indent=2, allow_nan=False))
