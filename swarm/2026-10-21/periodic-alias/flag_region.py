#!/usr/bin/env python3
"""The 1/8 level's ambiguity flag (tests/probes/limb/ambiguity.py, read-only import) restricted to the cage's rectangle
(C1) and the bars' disc (C3), plus V3's patch as the control. CPU only (lavfi sources, numpy). Swarm lane periodic-alias,
2026-10-21. Prints the share of textured cells in the region with a rival basin under margin 0.05 / 0.15 / 0.30, and
the best shift's magnitude histogram in the region (in 1/8 texels)."""
import sys, pathlib
import numpy as np
REPO = pathlib.Path("REPO")
sys.path.insert(0, str(REPO / "tests" / "probes" / "limb"))
import ambiguity as AM  # noqa: E402

TAUS = (0.05, 0.15, 0.30)

def region_mask(case, k, shape):
    hh, ww = shape
    yy, xx = np.mgrid[0:hh, 0:ww]
    if case.startswith("C1"):
        return (xx >= 390 // 8 + 1) & (xx < 910 // 8 - 1) & (yy >= 145 // 8 + 1) & (yy < 505 // 8 - 1)
    if case.startswith("C3"):
        t = k / 24.0
        cx, cy = (640 + 24 * t) / 8.0, (360 + 12 * t) / 8.0
        return (xx - cx) ** 2 + (yy - cy) ** 2 < (300 / 8.0 - 2) ** 2
    if case.startswith("V3"):
        ya = 100 + 12 * k
        return (xx >= (490 + 40) // 8) & (xx < (490 + 260) // 8) & (yy >= (ya + 24) // 8) & (yy < (ya + 276) // 8)
    raise SystemExit(case)

for case in sys.argv[1:]:
    fr = AM.frames(AM.scene(case))
    n = np.zeros(len(TAUS)); tot = 0; mags = np.zeros(8)
    for k in range(2, 19, 2):
        m, rg, d1y, d1x = AM.analyse(fr, k)
        tex = (rg >= 0.02) & region_mask(case, k, m.shape)
        tot += tex.sum()
        for j, t in enumerate(TAUS):
            n[j] += (m[tex] < t).sum()
        mag = np.maximum(np.abs(d1y), np.abs(d1x))[tex]
        for v in range(0, 4):
            mags[v] += (mag == v).sum()
    print(f"{case:24}" + "".join(f"  <{t:.2f}: {100 * n[j] / max(tot, 1):5.1f}%" for j, t in enumerate(TAUS))
          + f"   cells {tot:6d}   best |shift| 0/1/2/3 texels: " + " ".join(f"{100 * mags[v] / max(tot, 1):4.1f}%" for v in range(4)))
