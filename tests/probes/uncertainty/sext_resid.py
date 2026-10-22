"""Does the sext's least-squares residual predict the error of its own velocity field? (2026-10-22, step 2 of
swarm/2026-10-21/uncertainty.md section 5: the "free confidence map" measured.)

    sext_resid.py mk <mode> <out.glsl> [shader]     build a diagnostic variant (sext_resid.sh calls this)
    sext_resid.py score <outdir> <case> [<case> ...] score the renders sext_resid.sh left in <outdir>/<case>/

WHAT IT MEASURES. The sext's final pass fits ONE quartic trajectory through up to five composed links and the
anchor (sextdirectional-interpolation-propagated.glsl, "the FIELD: a weighted least-squares quartic") and keeps
the fit's leftover as `resid_px` (TRI_DIAG 6, "computed but never shown"). With five trusted links at N:N the fit
has one degree of freedom, so the residual says how far the links disagree with any smooth path. The question is
whether that number, per texel, ranks the texels by how wrong the field is against exact truth.

WHICH FIELD. No shipped mode returns the field the residual belongs to: TRI_DIAG 7 and read_view 4 return f_fwd,
the half-resolution straddle flow the warp uses, which never enters the fit. So `mk` injects three modes into the
final pass of a COPY (the human-reading tail is left as it is, off at read_view 0), every substitution asserted:
  10  the fit's velocity at the anchor, d'(0) of the fitted quartic (v + a u0 + j u0^2/2 + s u0^3/6, u0 = -tc,
      since SEXT_CENTRED fits about the weighted centre tc); where the fit did not run (fewer than four trusted
      links, a cut, or the snap guard) the quad's cubic velocity, the estimate the pass falls back to.
  11  R = resid_px as mode 6 computes it, G = the same residual in TRUE px, B = (nlinks + 8 * fitted) / 16.
      Until 2026-10-22 the shipped residual divided a uv vector by length(HOOKED_pt), which is not a px scale on a
      non-square frame (x residuals read 0.49x, y residuals 0.87x at 1280x720; the first run, on that form); G
      divides componentwise. The generator now does too, and R = G. Both /64, unsigned,
      so fp16 keeps them to 1/2048 relative.
  12  f_fwd, the straddle flow (mode 7's field), for the second row: does the residual also flag the warp's flow.
Velocities use the split encoding the fp16 probe proved (SWARM-2026-10-21 item 6): R = fract(vx/4), G = fract(vy/4),
B = ((floor(vx/4)+16) * 32 + floor(vy/4)+16) / 1024, every value exact in fp16, range +-64 px, step under 0.002 px;
the single-channel 0.5 + v/(2 FS) would floor at FS/1024 px. Modes 6 and 7 themselves are rendered too, with
RESID_DIAG_FS and VEL_DIAG_FS raised (asserted), as identity checks of the injected modes and the read path.

TRUTH. Each case's left edge x0(T) is read from tests/scenes.sh's own `_rect` line and evaluated (no hand-copied
laws); the box is w x h at y0. Output frame n (24 -> 24, N:N, anchored per phase) is the instant T = n/24.
Truth for the fit (mode 10) is the instantaneous velocity x0'(T)/24 px/frame inside the box, 0 outside; for f_fwd
the forward one-frame displacement x0(T + 1/24) - x0(T). An alignment line per case shows the median error
against the other candidates (one frame either side, the backward secant), so a misread instant shows itself.
Frames 0-5 are the window's start-up and are not scored.

REGIONS. interior = the box shrunk by EDGE px (4); edge = the band within EDGE px of the box's boundary, both
sides (occlusion and disocclusion live here: the residual should be high and the error is the estimator's support,
a separate row); near = interior + edge + the background ring out to 40 px. Far background is reported only as the
zero check. The kill is read on the interior, where the mask cannot do the work.

STATISTICS, per region, over texels where the fit ran (B flag): texel count; |e| median and p90 (|e| = the 2-D
error, px/frame); residual median and p90 (true px); Spearman(residual, |e|) over texels; the decile-bin Spearman
(texels in ten equal bins by residual rank, ties broken at random, Spearman of the bin index against the bins'
median |e| and their p90); gross capture = the share of texels with |e| > 2 px whose residual is in the top 20%.
Then THE COUNTERFACTUAL THAT MUST FAIL: the same numbers with the residual permuted at random across the same
texels (Spearman ~0, capture ~20%). The share of texels with no fit, their error and their gross share, and the
share of exact fits (four links: residual zero by construction) are printed beside, because a residual of zero
there is not a measurement.

HOW TO READ. Calibration first (the ZERO and CAL lines): the textured rigid translation must read its speed to
0.01 px in both fields and the far background exactly zero; mode 7 must sit at 0.5 within 0.0005 off the object;
the injected residual must equal mode 6's. A failed check prints ALARM and the science lines are not to be quoted.
KILL (uncertainty.md step 2): pooled interior Spearman over residual-decile bins < 0.5.
"""
import os
import pathlib
import re
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
W, H = 1280, 720
CROP_Y, CROP_H = 160, 400          # sext_resid.sh crops rows 160..559 (the boxes sit at y 210..509)
SKIP = 6
EDGE = 4.0
RING = 40.0
GROSS = 2.0


# ----------------------------------------------------------------------------------------------- the variants
def mk(mode, out, shader=None):
    src = pathlib.Path(shader) if shader else REPO / "shaders" / "sextdirectional-interpolation-propagated.glsl"
    txt = src.read_text(encoding="utf-8")
    cut = txt.index("// ==== human-reading tail")
    head, tail = txt[:cut], txt[cut:]

    def sub(old, new, where="head"):
        nonlocal head
        n = head.count(old)
        assert n == 1, "%r found %d times in the final pass (want 1)" % (old, n)
        head = head.replace(old, new)

    mode = int(mode)
    sub("const int TRI_DIAG = 0;", "const int TRI_DIAG = %d;" % mode)
    if mode == 6:
        sub("const float RESID_DIAG_FS = 2.0;", "const float RESID_DIAG_FS = 64.0;")
    elif mode == 7:
        sub("const float VEL_DIAG_FS   = 2.0;", "const float VEL_DIAG_FS   = 32.0;")
    elif mode in (10, 11, 12):
        sub("vec2 accel_c = vec2(0.0), jerk_c = vec2(0.0);",
            "vec2 accel_c = vec2(0.0), jerk_c = vec2(0.0);\n    vec2 vel_c_q = vec2(0.0);   // [probe uncertainty]")
        sub("jerk_c  = vec2(sx.z, sy.z);", "jerk_c  = vec2(sx.z, sy.z);\n            vel_c_q = vec2(sx.x, sy.x);")
        sub("float resid_px = 0.0;",
            "float resid_px = 0.0;\n    vec2 vfit_q = vec2(0.0); float fit_ok_q = 0.0, resid_true_q = 0.0; int nlinks_q = 0;")
        sub("for (int k = 0; k < 6; k++) if (w[k] > 0.05) nlinks++;",
            "for (int k = 0; k < 6; k++) if (w[k] > 0.05) nlinks++;\n        nlinks_q = nlinks;")
        sub("float num = 0.0, den = 0.0;", "float num = 0.0, den = 0.0, num_q = 0.0;")
        # Since 2026-10-22 the generator computes the residual in px per axis (r = (d7[k] - m) / HOOKED_pt, the
        # finding of this probe's first run): R and G then agree. Either form of the shader is accepted.
        old_form = "resid_px = sqrt(num / max(den, 1.0e-6)) / length(HOOKED_pt);" in head
        rline = ("resid_px = sqrt(num / max(den, 1.0e-6)) / length(HOOKED_pt);" if old_form
                 else "resid_px = sqrt(num / max(den, 1.0e-6));")
        sub("num += w7[k] * dot(r, r);",
            "num += w7[k] * dot(r, r);\n                        num_q += w7[k] * "
            + ("dot(r / HOOKED_pt, r / HOOKED_pt);" if old_form else "dot(r, r);"))
        sub(rline,
            rline + "\n"
            "                    resid_true_q = sqrt(num_q / max(den, 1.0e-6));\n"
            "                    { float u0 = -tc;\n"
            "                      vfit_q = vec2(sx[1] + sx[2] * u0 + sx[3] * u0 * u0 * 0.5 + sx[4] * u0 * u0 * u0 / 6.0,\n"
            "                                    sy[1] + sy[2] * u0 + sy[3] * u0 * u0 * 0.5 + sy[4] * u0 * u0 * u0 / 6.0);\n"
            "                      fit_ok_q = 1.0; }")
        inj = (
            "        if (TRI_DIAG == 10 || TRI_DIAG == 12) {   // [probe uncertainty] split encoding, 4-px units\n"
            "            vec2 vq = ((TRI_DIAG == 12) ? f_fwd : (fit_ok_q > 0.5 ? vfit_q : vel_c_q)) / HOOKED_pt;\n"
            "            vec2 wq = clamp(floor(vq * 0.25), -16.0, 15.0);\n"
            "            return vec4(vq * 0.25 - wq, ((wq.x + 16.0) * 32.0 + (wq.y + 16.0)) / 1024.0, 1.0);\n"
            "        }\n"
            "        if (TRI_DIAG == 11)\n"
            "            return vec4(clamp(resid_px / 64.0, 0.0, 1.0), clamp(resid_true_q / 64.0, 0.0, 1.0),\n"
            "                        (float(nlinks_q) + 8.0 * fit_ok_q) / 16.0, 1.0);\n")
        anchor = "        if (HOOKED_pos.x < 24.0 * HOOKED_pt.x && HOOKED_pos.y < 24.0 * HOOKED_pt.y)\n            return tri_diag_marker();"
        sub(anchor, inj + anchor)
    else:
        raise SystemExit("mode must be 6, 7, 10, 11 or 12")
    pathlib.Path(out).write_text(head + tail, encoding="utf-8", newline="\n")
    print("variant TRI_DIAG %d -> %s" % (mode, out))


# ----------------------------------------------------------------------------------------------- the read
class frames:
    """The raw rgb48le render, memory-mapped; frame n comes back as floats in [0, 1]."""
    def __init__(self, path):
        a = np.memmap(path, dtype="<u2", mode="r")
        per = W * CROP_H * 3
        assert a.size % per == 0, (path, a.size, per)
        self.a = a.reshape(-1, CROP_H, W, 3)

    def __len__(self):
        return self.a.shape[0]

    def __getitem__(self, n):
        return self.a[n].astype(np.float64) / 65535.0


PACK_WORST = [0.0]


def split_v(fr):
    k = fr[..., 2] * 1024.0
    kr = np.rint(k)
    PACK_WORST[0] = max(PACK_WORST[0], float(np.abs(k - kr).max()))
    kr = kr.astype(np.int64)
    wx, wy = kr // 32 - 16, kr % 32 - 16
    v = np.stack([4.0 * (wx + fr[..., 0]), 4.0 * (wy + fr[..., 1])], -1)
    clip = (wx <= -16) | (wx >= 15) | (wy <= -16) | (wy >= 15)
    return v, clip


def scene_law(case):
    txt = (REPO / "tests" / "scenes.sh").read_text(encoding="utf-8")
    m = re.search(r"^\s*%s\)\s+_rect\s+'([^']+)'\s+'([^']+)'\s+(\d+)\s+(\d+)\s" % re.escape(case), txt, re.M)
    assert m, "no _rect line for %s in scenes.sh" % case
    xe, ye, w, h = m.group(1), m.group(2), float(m.group(3)), float(m.group(4))
    assert re.fullmatch(r"[0-9.]+", ye), "the scorer assumes a fixed top edge: %s" % ye
    ns = {"sin": np.sin, "cos": np.cos, "__builtins__": {}}
    x0 = lambda T: float(eval(xe, ns, {"T": T}))
    return x0, float(ye), w, h, xe


# ----------------------------------------------------------------------------------------------- statistics
def spearman(a, b):
    from scipy.stats import spearmanr
    if a.size < 3 or np.all(a == a[0]) or np.all(b == b[0]):
        return float("nan")
    return float(spearmanr(a, b).statistic)


def stats(r, e, rng):
    n = r.size
    if n < 100:
        return None
    order = np.lexsort((rng.random(n), r))       # rank by residual, ties at random
    rank = np.empty(n, np.int64); rank[order] = np.arange(n)
    dec = rank * 10 // n
    bmed = np.array([np.median(e[dec == d]) for d in range(10)])
    bp90 = np.array([np.percentile(e[dec == d], 90) for d in range(10)])
    gross = e > GROSS
    top = rank >= 0.8 * n
    return dict(n=n, emed=np.median(e), ep90=np.percentile(e, 90), rmed=np.median(r), rp90=np.percentile(r, 90),
                sp=spearman(r, e), spb=spearman(np.arange(10.0), bmed), spb90=spearman(np.arange(10.0), bp90),
                ng=int(gross.sum()), cap=float(top[gross].mean()) if gross.any() else float("nan"),
                bmed=bmed)


def line(tag, s):
    if s is None:
        return "  %-26s  (too few texels)" % tag
    return ("  %-26s n %8d  |e| med %6.3f p90 %6.3f  resid med %6.3f p90 %6.3f  rho texel %+.3f  rho decile med %+.3f p90 %+.3f"
            "  gross %7d captured %5.1f%%" % (tag, s["n"], s["emed"], s["ep90"], s["rmed"], s["rp90"], s["sp"], s["spb"],
                                             s["spb90"], s["ng"], 100 * s["cap"]))


def score(outdir, cases):
    outdir = pathlib.Path(outdir)
    rng = np.random.default_rng(20261022)
    pool = {f: {"interior": ([], []), "edge": ([], []), "near": ([], [])} for f in ("fit", "fwd")}
    alarms = []
    for case in cases:
        d = outdir / case
        x0, y0, bw, bh, xe = scene_law(case)
        fv = frames(d / "m10.raw"); rr = frames(d / "m11.raw"); fw = frames(d / "m12.raw")
        nf = min(len(fv), len(rr), len(fw))
        print("== %s  x0(T) = %s, box %gx%g at y %g; %d frames rendered, %d scored" % (case, xe, bw, bh, y0, nf, nf - SKIP))
        Y = (np.arange(CROP_H) + CROP_Y + 0.5)[:, None]
        X = (np.arange(W) + 0.5)[None, :]

        def inside(T, m):
            x = x0(T)
            return (X > x - m) & (X < x + bw + m) & (Y > y0 - m) & (Y < y0 + bh + m)

        acc = {f: {"interior": ([], []), "edge": ([], []), "near": ([], [])} for f in ("fit", "fwd")}
        cal = {f: ([], []) for f in ("fit", "fwd")}
        nofit = {"e": [], "n": 0, "tot": 0}
        exact = [0, 0]
        align = {k: [] for k in ("fit:inst", "fit:inst-1", "fit:inst+1", "fit:fwd", "fwd:fwd", "fwd:bwd", "fwd:inst", "fwd:fwd-1", "fwd:fwd+1")}
        zero = {"fit": [], "fwd": []}
        clips = 0
        r6diff = []
        for n in range(SKIP, nf):
            T = n / 24.0
            vfit, c1 = split_v(fv[n]); vfwd, c2 = split_v(fw[n])
            clips += int(c1.sum() + c2.sum())
            res_true = rr[n][..., 1] * 64.0
            flag = np.rint(rr[n][..., 2] * 16.0).astype(int)
            fitted = flag >= 8; nlinks = flag % 8
            vin = (x0(T + 1e-6) - x0(T - 1e-6)) / 2e-6 / 24.0
            sec = lambda a, b: x0(b / 24.0) - x0(a / 24.0)
            truth = {"inst": vin, "fwd": sec(n, n + 1), "bwd": sec(n - 1, n),
                     "inst-1": (x0((n - 1) / 24.0 + 1e-6) - x0((n - 1) / 24.0 - 1e-6)) / 2e-6 / 24.0,
                     "inst+1": (x0((n + 1) / 24.0 + 1e-6) - x0((n + 1) / 24.0 - 1e-6)) / 2e-6 / 24.0,
                     "fwd-1": sec(n - 1, n), "fwd+1": sec(n + 1, n + 2)}
            obj = inside(T, 0.0)
            interior = inside(T, -EDGE)
            edge = inside(T, EDGE) & ~interior
            near = inside(T, RING)
            far = ~inside(T, RING + 8)
            for f, v, kind in (("fit", vfit, "inst"), ("fwd", vfwd, "fwd")):
                tv = np.zeros(v.shape); tv[..., 0] = np.where(obj, truth[kind], 0.0)
                e = np.linalg.norm(v - tv, axis=-1)
                zero[f].append(np.linalg.norm(v[far], axis=-1))
                for reg, m in (("interior", interior), ("edge", edge), ("near", near)):
                    mm = m & fitted
                    acc[f][reg][0].append(res_true[mm]); acc[f][reg][1].append(e[mm])
                cal[f][0].append(v[..., 0][interior & fitted]); cal[f][1].append(v[..., 1][interior & fitted])
                if f == "fit":
                    mi = interior & ~fitted
                    nofit["e"].append(e[mi]); nofit["n"] += int(mi.sum()); nofit["tot"] += int(interior.sum())
                    exact[0] += int((interior & fitted & (nlinks == 4)).sum()); exact[1] += int((interior & fitted).sum())
                for k in align:
                    ff, kk = k.split(":")
                    if ff != f:
                        continue
                    vv = vfit if f == "fit" else vfwd
                    tt = np.array([truth[kk], 0.0])
                    align[k].append(np.median(np.linalg.norm(vv[interior] - tt, axis=-1)))
            if (d / "m6.raw").exists():
                m6 = frames(d / "m6.raw")
                if n < len(m6):
                    r6diff.append(np.abs(m6[n][..., 0] * 64.0 - rr[n][..., 0] * 64.0).ravel())
        # --- the instrument lines
        print("  ALIGN median interior |e| (px/frame): " + "  ".join("%s %.3f" % (k, np.median(v)) for k, v in align.items()))
        for f in ("fit", "fwd"):
            z = np.concatenate(zero[f])
            ok = np.median(z) < 0.001
            print("  ZERO %s: far background |v| median %.5f  p99 %.5f  max %.4f px  (%d texels)%s"
                  % (f, np.median(z), np.percentile(z, 99), z.max(), z.size, "" if ok else "   ALARM: background not zero"))
            if not ok:
                alarms.append("%s %s background" % (case, f))
        print("  split packing: worst whole-part distance from an integer %.4f (exact in fp16: must be < 0.05); clipped texels %d"
              % (PACK_WORST[0], clips))
        if PACK_WORST[0] > 0.05:
            alarms.append("%s packing" % case)
        if r6diff:
            r6 = np.concatenate(r6diff)
            print("  mode 6 vs the injected residual (shipped units, px): max |diff| %.4f, p99.99 %.4f" % (r6.max(), np.percentile(r6, 99.99)))
            if np.percentile(r6, 99.99) > 0.01:
                alarms.append("%s mode-6 identity" % case)
        if (d / "m7.raw").exists():
            m7 = frames(d / "m7.raw")
            dif, lev = [], []
            for n in range(SKIP, min(len(m7), nf)):
                T = n / 24.0
                v7 = (m7[n][..., :2] - 0.5) * 64.0
                vf, _ = split_v(fw[n])
                far = ~inside(T, RING + 8)
                far[:, :24] = False
                lev.append(np.median(m7[n][far][:, :2], axis=0))
                dif.append(np.linalg.norm(v7 - vf, axis=-1)[inside(T, RING)])
            dif = np.concatenate(dif); lev = np.array(lev)
            lw = np.abs(lev - 0.5).max()
            print("  mode 7 (VEL_DIAG_FS 32) vs the injected f_fwd: median |diff| %.4f p99 %.4f px (floor 1/32); off-object level worst %.5f from 0.5%s"
                  % (np.median(dif), np.percentile(dif, 99), lw, "" if lw <= 0.0005 else "   ALARM: READ PATH"))
            if lw > 0.0005 or np.percentile(dif, 99) > 0.04:
                alarms.append("%s mode-7 identity" % case)
        # --- the science lines
        ne = np.concatenate(nofit["e"]) if nofit["e"] else np.zeros(0)
        print("  interior texels without a fit: %d of %d (%.2f%%), their |e| median %.3f, gross %.1f%%;  exact fits (4 links, resid 0 by construction) %.2f%% of fitted"
              % (nofit["n"], nofit["tot"], 100.0 * nofit["n"] / max(nofit["tot"], 1), np.median(ne) if ne.size else float("nan"),
                 100.0 * (ne > GROSS).mean() if ne.size else float("nan"), 100.0 * exact[0] / max(exact[1], 1)))
        for f in ("fit", "fwd"):
            for reg in ("interior", "edge", "near"):
                r = np.concatenate(acc[f][reg][0]); e = np.concatenate(acc[f][reg][1])
                if reg == "interior" and case.startswith("M2c"):
                    # calibration: the rigid translation's READ (the median over the interior, every fitted texel
                    # and frame) must sit on its known speed; the per-texel scatter is the science, not the read
                    bx, by = np.median(np.concatenate(cal[f][0])), np.median(np.concatenate(cal[f][1]))
                    sp = (x0(1.0) - x0(0.0)) / 24.0
                    bad = abs(bx - sp) > 0.01 or abs(by) > 0.01
                    print("  CAL %s %s: interior median vx %.4f vy %.4f px/frame against %.4f, 0 (within 0.01)%s"
                          % (case, f, bx, by, sp, "   ALARM: CALIBRATION" if bad else ""))
                    if bad:
                        alarms.append("%s %s calibration" % (case, f))
                print(line("%s %s" % (f, reg), stats(r, e, rng)))
                if reg == "interior":
                    print(line("%s %s PERMUTED" % (f, reg), stats(rng.permutation(r), e, rng)))
                pool[f][reg][0].append(r); pool[f][reg][1].append(e)
    print("== POOLED over %s" % " ".join(cases))
    verdict = None
    for f in ("fit", "fwd"):
        for reg in ("interior", "edge", "near"):
            r = np.concatenate(pool[f][reg][0]); e = np.concatenate(pool[f][reg][1])
            s = stats(r, e, rng)
            print(line("%s %s" % (f, reg), s))
            if reg == "interior":
                sp = stats(rng.permutation(r), e, rng)
                print(line("%s %s PERMUTED" % (f, reg), sp))
                print("    decile medians |e| (low residual -> high): " + " ".join("%.3f" % b for b in s["bmed"]))
                if f == "fit":
                    verdict = s["spb"]
    print("VERDICT (fit field, pooled interior, decile-bin Spearman of median |e|): %+.3f -> %s"
          % (verdict, "KILLED (< 0.5)" if verdict < 0.5 else "survives the kill (>= 0.5)"))
    if alarms:
        print("ALARMS: " + "; ".join(alarms) + " -- do not quote the science lines")
    return 1 if alarms else 0


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "mk":
        mk(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif len(sys.argv) >= 4 and sys.argv[1] == "score":
        sys.exit(score(sys.argv[2], sys.argv[3:]))
    else:
        sys.exit(__doc__)
