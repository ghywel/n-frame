#!/usr/bin/env python3
"""The gate's table for any number of labels: analyze.py --variants output from N runs (run{1..N}-all.txt, or
run{1..N}.txt), each label's per-case mean over the runs against the control 'vp', the capped-at-40 means, and the
cases moved more than 0.3 dB either way.

    gatetable.py <gate dir> [runs] [suffix] [control]   e.g. gatetable.py $NP/limb/gate 3 -all
    (control: the label the others are measured against, 'vp' unless named -- gateset.sh names the player's
    default, 'cage', when a switch is gated on top of it)"""
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import ladder_sets   # the headline set (2026-10-22) and the frozen 42

G = sys.argv[1]
R = int(sys.argv[2]) if len(sys.argv) > 2 else 3
suf = sys.argv[3] if len(sys.argv) > 3 else "-all"
CTRL = sys.argv[4] if len(sys.argv) > 4 else "vp"
CAP = 40.0
per = {}
labels = None
for r in range(1, R + 1):
    for ln in open(f"{G}/run{r}{suf}.txt"):
        if ln.startswith("case") and "|" in ln:
            labels = ln.split("|")[1].split()
            continue
        m = re.match(r"^(\S+)\s+(\S+)\s+(\S+)\s+\|\s+(.*)$", ln)
        if m and labels and not ln.startswith("-") and not ln.startswith("summary"):
            # Only the first column group: since 2026-10-22 analyze.py also prints " | min ..." and "|R ..." groups on
            # the same row, and a row whose field count no longer matched was skipped without a word.
            vals = m.group(4).split("|")[0].split()
            if len(vals) != len(labels):
                print(f"gatetable: a row for {m.group(1)} has {len(vals)} values for {len(labels)} labels", file=sys.stderr)
                continue
            f = lambda x: float(x) if x not in ("-", "inf") else math.nan
            per.setdefault(m.group(1), []).append({"linear": f(m.group(3)), **{l: f(v) for l, v in zip(labels, vals)}})
assert CTRL in labels, (CTRL, labels)
others = [l for l in labels if l != CTRL]
rows = {}
for c, runs in sorted(per.items()):
    rows[c] = {l: statistics.mean(x[l] for x in runs) for l in ["linear"] + labels}
print(f"{len(rows)} cases, {R} runs; labels {labels}")
print(f"{'case':26}{'linear':>8}{CTRL:>8}" + "".join(f"{l:>10}" for l in others))
for c, v in rows.items():
    print(f"{c:26}{v['linear']:8.2f}{v[CTRL]:8.2f}" + "".join(f"{v[l] - v[CTRL]:+10.2f}" for l in others))
# The capped means over the headline set when all of it is present (2026-10-22: V2x/V3x/H2x in place of V2/V3/H2), and
# over the frozen 42 beside it; a tree with neither complete (a probe's own case list) averages over its rows, as before.
hset, fset, hfull, ffull = ladder_sets.split(rows)
sets = ([("headline", hset)] if hfull else []) + ([("frozen 42", fset)] if ffull else [])
if not sets:
    sets = [("all rows", list(rows))]
for name, over in sets[1:]:
    cvo = statistics.mean(min(rows[c][CTRL], CAP) for c in over)
    print(f"\n[{name}] " + "; ".join(f"{l} {statistics.mean(min(rows[c][l], CAP) for c in over) - cvo:+.3f}" for l in others)
          + f" against {CTRL} {cvo:.3f} (capped)")
print(f"\ncapped means below are over: {sets[0][0]} ({len(sets[0][1])} cases)")
cv = statistics.mean(min(rows[c][CTRL], CAP) for c in sets[0][1])
for l in others:
    cl = statistics.mean(min(rows[c][l], CAP) for c in sets[0][1])
    down = sorted(((v[l] - v[CTRL], c) for c, v in rows.items() if v[l] - v[CTRL] < -0.3))
    up = sorted(((v[l] - v[CTRL], c) for c, v in rows.items() if v[l] - v[CTRL] > 0.3), reverse=True)
    print(f"\n{l}: capped mean {cl:.3f} vs {CTRL} {cv:.3f} ({cl - cv:+.3f}); down >0.3: {len(down)}  up >0.3: {len(up)}")
    print("  down: " + ", ".join(f"{c} {d:+.2f}" for d, c in down))
    print("  up:   " + ", ".join(f"{c} {d:+.2f}" for d, c in up))
