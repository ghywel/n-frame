"""fp16floor.sh's decoder: fp16floor_decode.py <out.raw>  (rgb48le, 512x8, 32 bands; see fp16floor.sh's header).

Band j carries the constant f = (4.0 if j < 16 else 5.9) + (j % 16) / 128 px in two encodings:
  R = 0.5 + f * (0.5 / 32)                      single channel (the existing read_view 4 encoding, FS 32)
  G = fract(f / 2), B = packed whole parts / 1024  two-channel (readview10.md's design; y = 0)
Verdict: PASS (single on the 1/32 px grid, <= 5 distinct per set; two-channel within 1/1024 px, wrap right),
KILL (single reads every constant to 1/1000 px: L10 false for the output stage), FAIL (two-channel design wrong),
INCONCLUSIVE otherwise. Exit 0 only on PASS. Tested CPU-only against simulated fp16 and fp32 readbacks
(fp16floor_sim.py), not yet against a GPU render.
"""
import struct, sys

W, H, BANDS = 512, 8, 32
raw = open(sys.argv[1], "rb").read()
size = W * H * 3 * 2
nf = len(raw) // size
if nf == 0:
    sys.exit("no frames decoded")
consts = [(4.0 if j < 16 else 5.9) + (j % 16) / 128.0 for j in range(BANDS)]


def band(fr, j):
    x = 16 * j + 8
    i = (4 * W + x) * 3                      # row 4, the band's centre column
    return struct.unpack_from("<3H", raw, fr * size + i * 2)


if all(all(v % 257 == 0 for v in band(0, j)) for j in range(BANDS)):
    sys.exit("READ PATH BROKEN: every level is a multiple of 257 (an 8-bit intermediate); the probe refuses to judge")
for fr in range(1, nf):
    if any(band(fr, j) != band(0, j) for j in range(BANDS)):
        print("WARNING: frame %d differs from frame 0; the readings below are frame 0's" % fr)

print("band set  k    f (px)     R16   single x1   |x1 - f|  grid resid    two-ch x2   |x2 - f|  whole(x,y)")
res_single, err_two, near_exact = [], [], []
x1s = {0: [], 1: []}
wrap_ok = True


def clusters(vals, gap=0.003):
    """Distinct readings, 16-bit noise allowed for: a new cluster when the sorted gap exceeds three 16-bit levels
    (64/65535 px each). fp16 gives <= 5 clusters per set (inputs 1/128 px apart on a 1/32 grid); fp32 gives 16."""
    v = sorted(vals); n = 1
    for a, b in zip(v, v[1:]):
        if b - a > gap: n += 1
    return n
for j in range(BANDS):
    f = consts[j]
    R, G, B = band(0, j)
    r, g, b = R / 65535.0, G / 65535.0, B / 65535.0
    x1 = (r - 0.5) * 64.0
    code = round(b * 1024.0)
    wx, wy = code // 32 - 16, code % 32 - 16
    x2 = 2.0 * wx + 2.0 * g
    grid = x1 - round(x1 * 32.0) / 32.0
    res_single.append(abs(grid)); err_two.append(abs(x2 - f)); near_exact.append(abs(x1 - f))
    x1s[j // 16].append(x1)
    if wy != 0 or abs(code - b * 1024.0) > 0.1:
        wrap_ok = False
    print("%3d   %d %2d  %9.5f  %6d  %10.5f  %9.5f  %10.5f  %11.5f  %9.6f   (%+d, %+d)"
          % (j, j // 16, j % 16, f, R, x1, abs(x1 - f), grid, x2, abs(x2 - f), wx, wy))
print()
d0, d1 = clusters(x1s[0]), clusters(x1s[1])
single_on_grid = max(res_single) < 0.004
single_quantised = d0 <= 5 and d1 <= 5
two_exact = max(err_two) < 1.0 / 1024.0 and wrap_ok
EXACT = 0.002                                               # two 16-bit levels in px: "reads the constant itself"
print("single channel: %d distinct of 16 (set A), %d of 16 (set B); largest residual to the 1/32 px grid %.5f px"
      % (d0, d1, max(res_single)))
print("two-channel:    largest |x2 - f| %.6f px (limit 1/1024 = 0.000977); whole parts %s"
      % (max(err_two), "decode exactly" if wrap_ok else "WRONG (packing or wrap)"))
if single_on_grid and single_quantised and two_exact:
    verdict = "PASS: the readback floor is fp16 at 1/32 px (L10 holds for the output stage) and the split encoding reads under 1/1024 px"
elif not single_quantised and max(near_exact) < EXACT:
    verdict = "KILL: the single channel reads every constant to within two 16-bit levels; L10 does not hold for the output stage"
elif single_quantised and not single_on_grid:
    verdict = "INCONCLUSIVE: quantised, but not on the 1/32 grid (another format than fp16); rerun with DITHER=none"
elif not two_exact:
    verdict = "FAIL (design): the two-channel decode misses 1/1024 px or the whole part; readview10.md must not ship as written"
else:
    verdict = "INCONCLUSIVE: see the table"
print("fp16floor: " + verdict)
sys.exit(0 if verdict.startswith("PASS") else 1)
