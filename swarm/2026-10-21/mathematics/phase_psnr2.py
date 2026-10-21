import re, sys, pathlib, math
PH = {0: 0.0, 1: 0.4, 2: 0.8, 3: 0.2, 4: 0.6}
def db(m): return 10*math.log10(255**2/m) if m > 0 else float("inf")
root = pathlib.Path(sys.argv[1]); skip = set(int(x) for x in sys.argv[2].split(","))
for case in sorted(p for p in root.iterdir() if p.is_dir()):
    for mode in ("mac_v0", "linear"):
        by = {v: [] for v in PH.values()}
        for line in (case / f"{mode}.log").read_text().splitlines():
            m = re.search(r"n:(\d+) .*mse_y:([\d.]+)", line)
            n, mse = int(m.group(1)), float(m.group(2))
            if n in skip: continue
            by[PH[(n - 1) % 5]].append(mse)
        out = [f"t={ph:.1f}: {db(sum(v)/len(v)):6.2f} (worst {db(max(v)):6.2f}, n={len(v)})"
               for ph, v in ((p, by[p]) for p in (0.2, 0.4, 0.6, 0.8))]
        print(f"{case.name:14s} {mode:7s} " + "  ".join(out))
