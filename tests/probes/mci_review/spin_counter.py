#!/usr/bin/env python3
"""Separate wavefront robustness repair: saturate the spin counter at 256.

The first yield remains wait iteration 257, and every later iteration still
yields. Unlike an indefinitely incremented signed int, this cannot overflow if a
predecessor thread is stopped for a long time. No dependency or atomic changes.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

OLD = """                    while (atomic_load(above) < need)
                        if (++spins > 256)
                            sched_yield();
"""
NEW = """                    while (atomic_load(above) < need) {
                        if (spins < 256)
                            spins++;
                        else
                            sched_yield();
                    }
"""


def transform(text):
    if text.count(OLD) != 1:
        raise ValueError("expected exactly one original wavefront wait")
    return text.replace(OLD, NEW, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if (a.out / "vf_minterpolate.c").resolve() == a.source.resolve():
        raise ValueError("input and output must differ")
    before = a.source.read_text(); after = transform(before)
    # The first thousand wait iterations must make the same scheduling choice.
    old = new = 0
    for _ in range(1000):
        old += 1
        expected_yield = old > 256
        actual_yield = new >= 256
        if new < 256: new += 1
        assert actual_yield == expected_yield
    patch = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="a/libavfilter/vf_minterpolate.c", tofile="b/libavfilter/vf_minterpolate.c"))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "vf_minterpolate.c").write_text(after)
    (a.out / "spin-counter.patch").write_text(patch)
    sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
    meta = dict(status="generated_not_built", source_sha256=sha(before), fixed_sha256=sha(after),
        patch_sha256=sha(patch), generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        schedule_control_iterations=1000, first_yield_iteration=257)
    (a.out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__": main()
