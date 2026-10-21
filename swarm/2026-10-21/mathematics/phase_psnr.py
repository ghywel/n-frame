# Per-phase PSNR from the owner's own bench logs (tests/bench.sh psnr stats_file):
# output frame n (1-based) at 60 fps from a 24 fps source has phase frac(0.4*(n-1)),
# so (n-1) mod 5 -> phase {0:0.0, 1:0.4, 2:0.8, 3:0.2, 4:0.6}. The mixing shader
# is time-symmetric only if phase 0.4 and 0.6 score alike (0.2 and 0.8 likewise);
# the linear blend is symmetric by construction and serves as the control.
import re, sys, pathlib, math
PH = {0: 0.0, 1: 0.4, 2: 0.8, 3: 0.2, 4: 0.6}
root = pathlib.Path(sys.argv[1])
for case in sorted(p for p in root.iterdir() if p.is_dir()):
    for mode in ("mac_v0", "linear", "hold"):
        f = case / f"{mode}.log"
        if not f.exists(): continue
        by = {v: [] for v in PH.values()}
        for line in f.read_text().splitlines():
            m = re.search(r"n:(\d+) .*mse_y:([\d.inf]+) .*psnr_y:([\d.inf]+)", line)
            if not m: continue
            n, mse = int(m.group(1)), float(m.group(2))
            by[PH[(n - 1) % 5]].append(mse)
        out = []
        for ph in (0.0, 0.2, 0.4, 0.6, 0.8):
            v = by[ph]
            if not v: continue
            mean = sum(v) / len(v)
            psnr = 10 * math.log10(255**2 / mean) if mean > 0 else float("inf")
            out.append(f"t={ph:.1f}: {psnr:6.2f} dB (n={len(v)})")
        print(f"{case.name:16s} {mode:7s} " + "  ".join(out))
    print()
