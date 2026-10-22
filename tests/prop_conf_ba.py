#!/usr/bin/env python3
"""THE PROPAGATION'S B->A HALF WEIGHED BY FRAME B'S CONTRAST: a variant base (2026-10-22, REPAIRS L11).

In the propagated and animation bases the three contrast-weighted propagation passes are fused with their B->A twins,
and both halves share one prop_conf() that reads LUMA_A_E: the B->A half weighs its neighbours by frame A's contrast at
frame B's texels, where its mirror (and the three-way check's own prop_conf_ba) reads LUMA_B_E. This tool gives each
such pass a prop_conf_ba() reading LUMA_B_E and uses it in hook_ba only, asserting the passes and the calls:

    prop_conf_ba.py <base.glsl> <out.glsl> <expected passes>      (3 for -propagated and -animation)

then hand the output to a generator as its base (gen_variational.py's seventh argument, the N-frame generators' second).

MEASURED 2026-10-22, the M5, the 45 cases (headline mean; noise control: the shipped quad twice, within 0.01 on every
case): the High tier does not move (39.080 / region 36.501 -> 36.500; B->A propagation barely reaches its picture);
the quad is a TRADE, flat in the mean (38.225 -> 38.226; region 35.342 -> 35.328) with L2 and M2 -0.44, A2 and L6 -0.35,
L3 and H1 -0.20 against P3 +0.40, L1 and O3 +0.09. Not never-worse, so the shipped bases keep the shared read and this
stays a variant. The Low and Standard tiers prune the B->A propagation entirely (only the unused helper differs).
"""
import re
import sys

src, dst, want = sys.argv[1], sys.argv[2], int(sys.argv[3])
text = open(src).read()
blocks = re.split(r"(?m)^(?=//!HOOK )", text)

CONF_A = re.compile(r"float prop_conf\(vec2 uv\) \{\n(.*?\n)\}\n", re.S)
fixed = 0
calls = 0
for i, b in enumerate(blocks):
    if "void hook_ba()" not in b or "float prop_conf(vec2 uv)" not in b or "prop_conf_ba" in b:
        continue
    assert "//!BIND LUMA_B_E" in b, "a pass to fix does not bind LUMA_B_E"
    m = CONF_A.search(b)
    assert m and m.group(1).count("LUMA_A_E") == 2, "prop_conf is not the expected two LUMA_A_E reads"
    ba = m.group(0).replace("prop_conf(", "prop_conf_ba(").replace("LUMA_A_E", "LUMA_B_E")
    b = b[:m.end()] + "\n// REPAIRS L11 (2026-10-22): the B->A half weighs by frame B's contrast, as its mirror does.\n" + ba + b[m.end():]
    h0 = b.index("void hook_ba()")
    h1 = b.index("\nvec4 hook()", h0)
    body = b[h0:h1]
    n = body.count("prop_conf(")
    assert n == 2, "hook_ba calls prop_conf %d times, expected 2" % n
    calls += n
    b = b[:h0] + body.replace("prop_conf(", "prop_conf_ba(") + b[h1:]
    blocks[i] = b
    fixed += 1

assert fixed == want, "fixed %d passes, expected %d" % (fixed, want)
open(dst, "w").write("".join(blocks))
print("%s: %d passes, %d calls now read LUMA_B_E" % (dst, fixed, calls))
