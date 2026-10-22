#!/usr/bin/env python3
"""The ladder's case sets, read from scenes.sh, for every tool that averages over the ladder (2026-10-22).

    import ladder_sets; ladder_sets.frozen(); ladder_sets.headline(); ladder_sets.split(present_cases)
    ./ladder_sets.py            prints the sets and checks them (exit 1 on any fault)

FROZEN is ALL_CASES, the 42 cases every number in the record to 2026-10-21 was averaged over. HEADLINE is the set the
headline mean is taken over from 2026-10-22, on Gareth's decision: the frozen 42 with V2, V3 and H2 replaced by V2x, V3x
and H2x (the same stairs with an exact-coverage truth: tests/TESTING.md, "LADDER2"). Both are printed, so an old number
still has its comparable. The check: HEADLINE must be FROZEN with exactly those three substitutions, in place, and
every name must be a case scenes.sh renders. A tool that averaged over whatever folders exist would mix V2 and V2x
once bench.sh all renders both; this is the one place that says which cases a mean is over.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SWAP = {"V2_stairs_sq24_v6": "V2x_stairs_cov_v6", "V3_stairs_sq24_v12": "V3x_stairs_cov_v12",
        "H2_stairs_sq24_h6": "H2x_stairs_cov_h6"}


def _read(name):
    text = open(os.path.join(HERE, "scenes.sh")).read()
    m = re.search(r'^%s="([^"]+)"' % name, text, re.M)
    if not m:
        raise SystemExit("ladder_sets: %s not found in scenes.sh" % name)
    return m.group(1).split()


def frozen():
    return _read("ALL_CASES")


def headline():
    return _read("HEADLINE_CASES")


def check():
    f, h = frozen(), headline()
    faults = []
    if len(f) != 42:
        faults.append("ALL_CASES has %d cases, not 42" % len(f))
    if [SWAP.get(c, c) for c in f] != h:
        faults.append("HEADLINE_CASES is not ALL_CASES with V2/V3/H2 -> V2x/V3x/H2x in place")
    scenes = open(os.path.join(HERE, "scenes.sh")).read()
    for c in set(f) | set(h):
        if not re.search(r"^\s+%s\)" % re.escape(c), scenes, re.M):
            faults.append("%s has no case in scene()" % c)
    return faults


def split(present):
    """Given the case folders present, return (headline cases present, frozen cases present, complete flags)."""
    p = set(present)
    h = [c for c in headline() if c in p]
    f = [c for c in frozen() if c in p]
    return h, f, len(h) == 42, len(f) == 42


if __name__ == "__main__":
    bad = check()
    print("FROZEN (ALL_CASES): %d   HEADLINE (from 2026-10-22): %d   swapped: %s" % (
        len(frozen()), len(headline()), ", ".join("%s -> %s" % kv for kv in SWAP.items())))
    for b in bad:
        print("FAULT:", b)
    sys.exit(1 if bad else 0)
