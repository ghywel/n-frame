#!/usr/bin/env python3
"""The table for buildgate.sh: each shader's ladder on build A against build B, losses first.

    buildtable.py <outroot> <A> <B> [tag ...]

Scores exactly as analyze.py does (its parse() and mean_interp() are copied below, unchanged: psnr_y, interpolated
frames only, the first five outputs skipped, the 40 dB cap for the capped mean), so the numbers are the ladder's own.
For hold, linear and every tag it prints the per-case B - A, the count within 0.01 and 0.10 dB, the worst cases,
and the capped means. The control line compares two tags on build A (the first two given): the same table must see a
real difference there, or it could not see one between the builds either.
"""
import os
import re
import sys

SKIP_STARTUP = 5
CAP_DB = float(os.environ.get("CAP_DB", "40"))


def parse(path):
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path):
        m = re.match(r"n:(\d+).*?psnr_y:([0-9.]+|inf)", line)
        if m:
            v = m.group(2)
            out[int(m.group(1))] = float("inf") if v == "inf" else float(v)
    return out


def mean_interp(d):
    """Mean PSNR over genuinely-interpolated frames."""
    vals = [v for n, v in d.items()
            if n > SKIP_STARTUP and (n - 1) % 5 != 0 and v != float("inf")]
    if not vals:
        return float("inf") if d else None
    return sum(vals) / len(vals)


root, A, B = sys.argv[1:4]
tags = sys.argv[4:]
cases = sorted(c for c in os.listdir(os.path.join(root, A))
               if os.path.isdir(os.path.join(root, A, c)) and not c.startswith("._"))
# Since 2026-10-22 bench.sh all renders 45 cases (the frozen 42 and the headline set's V2x/V3x/H2x): the capped means
# here are over the headline set when all of it is present, else the frozen 42, else every case (tests/ladder_sets.py).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import ladder_sets
_h, _f, _hfull, _ffull = ladder_sets.split(cases)
MEAN_SET = _h if _hfull else (_f if _ffull else cases)
MEAN_NAME = "headline" if _hfull else ("frozen 42" if _ffull else "all cases")


def score(build, case, label):
    return mean_interp(parse(os.path.join(root, build, case, label + ".log")))


def finite(v):
    return v is not None and v != float("inf")


print("build A = %s, build B = %s, %d cases; capped means over the %s set (%d)" % (A, B, len(cases), MEAN_NAME, len(MEAN_SET)))
print("%-10s %6s %6s %6s %9s %9s   %s" % ("mode", "cases", "<=0.01", "<=0.10", "capped A", "capped B", "worst B - A (losses first)"))
for label in ["hold", "linear"] + tags:
    rows = []
    for c in cases:
        a, b = score(A, c, label), score(B, c, label)
        if finite(a) and finite(b):
            rows.append((b - a, c, a, b))
    if not rows:
        print("%-10s no scoreable cases" % label)
        continue
    n01 = sum(abs(d) <= 0.01 for d, *_ in rows)
    n10 = sum(abs(d) <= 0.10 for d, *_ in rows)
    mrows = [r for r in rows if r[1] in MEAN_SET] or rows
    capA = sum(min(a, CAP_DB) for _, _, a, _ in mrows) / len(mrows)
    capB = sum(min(b, CAP_DB) for _, _, _, b in mrows) / len(mrows)
    rows.sort()
    worst = ", ".join("%s %+.2f" % (c, d) for d, c, _, _ in rows[:3])
    best = ", ".join("%s %+.2f" % (c, d) for d, c, _, _ in rows[-2:])
    print("%-10s %6d %6d %6d %9.3f %9.3f   %s | top: %s" % (label, len(rows), n01, n10, capA, capB, worst, best))

if len(tags) >= 2:
    t0, t1 = tags[0], tags[1]
    diffs = [score(A, c, t1) - score(A, c, t0) for c in cases
             if finite(score(A, c, t0)) and finite(score(A, c, t1))]
    big = sum(abs(d) > 0.10 for d in diffs)
    print("control: %s against %s on build %s differ by more than 0.10 dB on %d of %d cases (must be many)"
          % (t1, t0, A, big, len(diffs)))

print()
print("per case, B - A:")
print("%-26s" % "case" + "".join("%9s" % l for l in ["hold", "linear"] + tags))
for c in cases:
    cells = []
    for label in ["hold", "linear"] + tags:
        a, b = score(A, c, label), score(B, c, label)
        cells.append("%+9.2f" % (b - a) if finite(a) and finite(b) else "%9s" % ("inf" if a == b else "-"))
    print("%-26s" % c + "".join(cells))
