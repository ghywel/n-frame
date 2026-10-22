#!/usr/bin/env python3
"""Summarise ground-truth PSNR logs written by bench.sh.

    ./analyze.py                 # every case found, default 'shader' column
    ./analyze.py --variants      # every label found, side by side
    ./analyze.py L2_trans_16px   # specific cases

Two details matter for reading the numbers honestly:

* At 24->60 every 5th output frame lands exactly on a source frame and is a
  trivial passthrough for every mode, so those are excluded -- they would
  otherwise inflate every column by the same meaningless amount.
* The first few output frames are dropped: the hook falls back to a
  zero-order hold until it has a full frame window, so they measure startup
  behaviour rather than interpolation quality.

Also note the ceiling: 'hold' can reach infinite PSNR on a static scene
because it copies frames byte-for-byte, while anything going through
libplacebo tops out around 79 dB from the GPU round-trip alone. Do not read
that gap as a shader defect.

AND DO NOT AVERAGE THE RAW COLUMN. A decibel is not the same quantity at both
ends of this table. Found 2026-09-10 while ablating the shipped components:
removing the whole variational cascade IMPROVED the plain ladder mean by 1.29
dB, which read as the cascade being a liability -- but the gain was
L2_trans_16px moving 50.01 -> 71.08 and L6_flat_large 48.72 -> 65.55, two
cases that are already far past any visible error, while its losses were on
the aperture series where error is visible. Restricted to the regime that can
matter the cascade is a positive, not a liability. The same averaging had the
zero seed, which rescues H1 from 19.28 to 55.86 dB, contributing no more per
case than a change nobody could see. So the summary below CAPS each case
before averaging: improvements above the cap contribute nothing, differences
below it count in full. The cap is a convention (see CAP_DB), not a
perceptual measurement -- it is there to stop the arithmetic being nonsense,
not to claim a threshold of visibility.
"""
import os
import re
import sys

OUTROOT = os.environ.get("OUTROOT") or os.path.join(
    os.environ.get("TMPDIR", "/tmp"), "interp-bench")
SKIP_STARTUP = 5
# The window's END (2026-10-21, found by the swarm's mathematics lane and confirmed on the gate logs): the last two
# outputs of every case fall through to libplacebo's own mixer (the hook has no frame after them: the "two boundary
# hook-skipped lines" bench.sh allows) and read IDENTICAL for the shader, hold and linear (L1: 36.63 and 31.30), yet
# were scored under the shader's name, diluting every shader toward hold by about a dB on the clean cases (L1 65.69 as
# scored, 67.20 without them). SKIP_END=2 drops them. It defaults to 0 so every number in the record stays comparable;
# a run that sets it says so in its label. The gate reads both forms until the record resets.
SKIP_END = int(os.environ.get("SKIP_END", "0"))
BASELINES = ("hold", "linear")


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


# Above this, a difference is not a difference anyone can see, and averaging it
# against a case sitting at 19 dB is arithmetic on two different quantities.
# 40 dB is the usual convention for visually lossless 8-bit; it is a
# convention and the honest way to place it is the owner's eyes on a render.
CAP_DB = float(os.environ.get("CAP_DB", "40"))


def scored(d):
    """The genuinely-interpolated frames: after the start skip, before the end skip, not the passthrough phase.
    `(n - 1) % 5 != 0` is the passthrough rule for 24 -> 60 exactly (psnr's n is 1-based); any other ratio needs its
    own rule (the swarm's instruments lane, 2026-10-21)."""
    last = max(d) if d else 0
    return [(n, v) for n, v in d.items()
            if n > SKIP_STARTUP and n <= last - SKIP_END and (n - 1) % 5 != 0 and v != float("inf")]


def mean_interp(d):
    """Mean PSNR over genuinely-interpolated frames."""
    vals = [v for _, v in scored(d)]
    if not vals:
        return float("inf") if d else None
    return sum(vals) / len(vals)


def min_interp(d):
    """The worst scored frame: a dB mean is a geometric mean of MSE, so one bad frame among forty barely moves it
    (one 15 dB frame among 44 at 45 moves the mean 0.68 dB); the minimum is where a defect shows (2026-10-21)."""
    vals = [v for _, v in scored(d)]
    return min(vals) if vals else None


def phase_profile(d):
    """Mean per output phase, keyed by (n - 1) % 5 -> t = 0.4, 0.8, 0.2, 0.6 for phases 1..4 at 24 -> 60. The
    shaders are not time-symmetric (L1 reads 70.95 / 64.10 / 70.36 / 63.32 by phase; linear is symmetric to 0.01), so
    a mean hides which phases carry the error (the swarm's mathematics lane, 2026-10-21)."""
    by = {}
    for n, v in scored(d):
        by.setdefault((n - 1) % 5, []).append(v)
    return {k: sum(v) / len(v) for k, v in sorted(by.items())}


def fmt(v):
    if v is None:
        return "    -  "
    if v == float("inf"):
        return "   inf "
    return f"{v:7.2f}"


args = [a for a in sys.argv[1:] if not a.startswith("--")]
show_variants = "--variants" in sys.argv
show_min = "--min" in sys.argv          # a worst-frame column per label (2026-10-21)
show_phase = "--phase" in sys.argv      # a per-phase profile per label, printed under the table (2026-10-21)
# THE REGION COLUMN (2026-10-21, the swarm's instruments lane). bench.sh scores the same frames a second time over the
# case's static crop (tests/regions.sh: the object's swept path plus 16 px) into <mode>.region.log. The frame mean
# understates a defect confined to the mover by 10 log10(1 / its share): 15-25 dB on 22 of the 42 cases, measured
# (np-scratch/swarm-20261021/instruments/share.txt), so with the cap a 20 dB fault on L1's box reads 42.5 dB and counts
# for nothing. The region reading of every mode prints beside the whole-frame one, with the same scored-frame rule and a
# capped mean of its own, whenever region logs exist (Gareth, 2026-10-22: "My suggestion is that the region-scored column
# and capped man are retained besides each other"); --no-region suppresses it, and --region is still accepted.
show_region = "--no-region" not in sys.argv


def region_log(d, m):
    return os.path.join(d, m + ".region.log")

if not os.path.isdir(OUTROOT):
    sys.exit(f"no results at {OUTROOT} -- run bench.sh first")

cases = args or sorted(d for d in os.listdir(OUTROOT)
                       if os.path.isdir(os.path.join(OUTROOT, d)))

labels = set()
for c in cases:
    for f in os.listdir(os.path.join(OUTROOT, c)):
        if f.endswith(".log") and not f.endswith(".region.log") and not f.startswith("._"):
            n = f[:-4]
            if n not in BASELINES:
                labels.add(n)
labels = sorted(labels) if show_variants else (["shader"] if "shader" in labels
                                               else sorted(labels)[:1])
if show_region and not any(os.path.exists(region_log(os.path.join(OUTROOT, c), l)) for c in cases for l in labels):
    show_region = False          # a tree rendered before 2026-10-21 has no region logs: print what it always printed

# THE HEADLINE MEAN (2026-10-22, Gareth: "If V2x, V3x, H2x are improvements over the originals then V2, V3, H2 should not
# be included in the mean"). With no cases named, the summary is taken over the headline set (tests/ladder_sets.py) when
# all of it is present, and over the frozen 42 beside it as the record's history; a tree holding only the frozen 42 (any
# render before 2026-10-22) prints the frozen summary alone, as before, with a line saying the headline needs the three.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ladder_sets
if args:
    summary_sets = [(None, cases)]
else:
    h_cases, f_cases, h_full, f_full = ladder_sets.split(cases)
    summary_sets = []
    if h_full:
        summary_sets.append(("HEADLINE (from 2026-10-22: V2x/V3x/H2x in place of V2/V3/H2)", h_cases))
    if f_full:
        summary_sets.append(("FROZEN 42 (the record's mean to 2026-10-21)" if h_full else None, f_cases))
    if not summary_sets:
        summary_sets = [(None, cases)]       # neither set present: a probe's own tree; summarise what is there

w = 22
head = f"{'case':<{w}}{'hold':>8}{'linear':>8} |" + "".join(f"{l:>9}" for l in labels)
if not show_variants and labels:
    head += f"{'vs hold':>9}{'vs linear':>11}"
if show_region:
    head += f" |R{'hold':>8}{'linear':>8} |" + "".join(f"{l:>9}" for l in labels)
    if not show_variants and labels:
        head += f"{'vs linear':>11}"
print()
print(head)
print("-" * len(head))

table = {}
rtable = {}
for c in cases:
    d = os.path.join(OUTROOT, c)
    vals = {m: mean_interp(parse(os.path.join(d, m + ".log")))
            for m in list(BASELINES) + labels}
    table[c] = vals
    row = f"{c:<{w}}{fmt(vals['hold'])}{fmt(vals['linear'])} |"
    row += "".join(fmt(vals[l]) for l in labels)
    if show_min:
        row += " | min" + "".join(fmt(min_interp(parse(os.path.join(d, l + ".log")))) for l in labels)
    if not show_variants and labels:
        s, h, l = vals[labels[0]], vals["hold"], vals["linear"]
        if None in (s, h, l) or float("inf") in (s, h, l):
            row += f"{'  -':>9}{'  -':>11}"
        else:
            row += f"{s - h:>+9.2f}{s - l:>+11.2f}"
    if show_region:
        rvals = {m: mean_interp(parse(region_log(d, m))) for m in list(BASELINES) + labels}
        rtable[c] = rvals
        row += f" |R{fmt(rvals['hold'])}{fmt(rvals['linear'])} |" + "".join(fmt(rvals[l]) for l in labels)
        if not show_variants and labels:
            s, l = rvals[labels[0]], rvals["linear"]
            row += f"{'  -':>11}" if None in (s, l) or float("inf") in (s, l) else f"{s - l:>+11.2f}"
    print(row)


def summarise(title, over, tab, region=False):
    usable = [c for c in over if c in tab and all(tab[c].get(l) not in (None, float("inf")) for l in labels)]
    if not usable:
        return False
    capped = {l: sum(min(tab[c][l], CAP_DB) for c in usable) / len(usable) for l in labels}
    raw = {l: sum(tab[c][l] for c in usable) / len(usable) for l in labels}
    binding = [c for c in usable if min(tab[c][l] for l in labels) < CAP_DB]
    ref = labels[0]
    head = ("REGION, over " if region else "summary over ") + str(len(usable)) + " scoreable cases"
    print()
    if title:
        print(("REGION -- " if region else "") + title)
    print(f"{head:<{w}}{'raw mean':>12}{'capped at ' + str(int(CAP_DB)):>14}{'vs ' + ref:>12}")
    print("-" * (w + 38))
    for l in labels:
        print(f"{l:<{w}}{raw[l]:12.2f}{capped[l]:14.2f}{capped[l] - capped[ref]:+12.2f}")
    print()
    if region:
        print(f"REGION: {len(binding)} of {len(usable)} cases have any variant below {CAP_DB:g} dB on the object's")
        print("swept path (tests/regions.sh). The |R columns score the same frames over that crop, so a fault")
        print("confined to the mover is no longer diluted by the frame's flat majority (10 log10(1 / share)).")
    else:
        print(f"{len(binding)} of {len(usable)} cases have any variant below {CAP_DB:g} dB; only those can")
        print("move the capped mean. The raw mean is kept because the record quotes it,")
        print("but prefer the capped column: it does not average a decibel at 19 dB")
        print("against a decibel at 71 dB as though they were the same quantity.")
    return True


if labels:
    for title, over in summary_sets:
        summarise(title, over, table)
    if not args and not any(t for t, _ in summary_sets if t and t.startswith("HEADLINE")) \
            and ladder_sets.split(cases)[3]:
        print("(the headline mean, from 2026-10-22, needs V2x/V3x/H2x in this tree: bench.sh all renders them)")

if show_region and labels:
    any_r = False
    for title, over in summary_sets:
        any_r = summarise(title, over, rtable, region=True) or any_r
    if not any_r:
        print()
        print("REGION: no case is scoreable on every label (a region reading of inf or a missing log); the |R columns stand.")

if show_phase and labels:
    print()
    print("per output phase (t = 0.4, 0.8, 0.2, 0.6), mean dB; a symmetric shader reads the same at t and 1 - t:")
    for c in cases:
        for l in labels:
            pr = phase_profile(parse(os.path.join(OUTROOT, c, l + ".log")))
            if pr:
                print(f"  {c:<{w}}{l:>9}  " + "  ".join(f"{pr.get(k, float('nan')):6.2f}" for k in (1, 2, 3, 4)))

if SKIP_END:
    print()
    print(f"SKIP_END={SKIP_END}: the last {SKIP_END} outputs (the mixer's, identical for every mode) are not scored.")
    print("These numbers do not compare with the record's, which score them.")

print()
print("PSNR of genuinely interpolated frames only, dB, higher is better.")
print("A motion-compensated shader that does not clearly beat 'linear' is not")
print("earning its complexity. Beating 'linear' by <0 means it is actively")
print("worse than stock libplacebo on that content.")
