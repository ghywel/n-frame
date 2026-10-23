"""The sext's fit inputs, exported per pixel for a covariance check (2026-10-22; GPT's specification, MATHS.md "The
smallest next export for a covariance check"; CHAT-LEDGER.md G005 and L003).

    export_links.py mk <mode> <out.glsl> [shader]      build one diagnostic variant (export_links.sh calls this)
    export_links.py hashes <glsl> [<glsl> ...]          every variant's estimator passes must hash identical
    export_links.py pack <outdir> <case> [<case> ...]   decode the renders, run the checks, write <case>.npz + manifest

WHY. GPT showed (MATHS.md, block 1) that the least-squares residual cannot identify the error covariance of the fitted
velocity: an error along a polynomial direction moves the velocity and leaves the residual unchanged. The fixed fit's
covariance is h Sigma h^T over its INPUTS, so the inputs are what must be measured against truth: the six composed link
displacements (one is always absent: the anchor sits at slot 2 or 3 of six), their trust weights and taus, the fit's
centre tc, and its state. The final-field dumps (sext_resid.sh) cannot supply them.

WHAT IS RENDERED. Variants of the shipped sext, each a copy whose ONLY difference is what its final pass returns under
a TRI_DIAG mode; the injected code copies values the pass already computes into outer-scope variables, every
substitution asserted once:
  20..25  link k's displacement d[k] in px (the array the fit is built from, k = 0..5 by tau: the far negative link
          first), split-encoded as the fp16 probe proved: R = fract(dx/4), G = fract(dy/4),
          B = ((floor(dx/4) + 16) * 32 + floor(dy/4) + 16) / 1024; range +-64 px, step under 0.002 px
  26, 27  the trust weights w[0..2], w[3..5] (0..1; the fit uses a link when w > 0.05)
  28, 29  the taus tau[0..2], tau[3..5] in source intervals, as tau / 8 + 0.5 (the anchor's own point is tau 0, d 0)
  30      R = tc / 8 + 0.5 (0.5 where the fit did not run), G = state / 16 with state = cut_ok + 2 * solve_ok +
          4 * snap_ok + 8 * fitted, B = nlinks / 8 (links with w > 0.05)
  31      the fitted velocity at the anchor, d'(0) = v + a u0 + j u0^2/2 + s u0^3/6 with u0 = -tc (sext_resid's m10,
          without its fallback: zero where the fit did not run), split-encoded as 20..25
  32      R = the fit's residual in true px (per axis since 2026-10-22) / 64
The read path: the scene is converted to rgba64le BEFORE libplacebo and libplacebo writes rgba64le (Mesa cannot write
rgb48le: L002), read back as rawvideo, rows 160..559 kept.

CHECKS, before anything is packed (pack prints ALARM and exits 1 on any failure; an empty or short render is refused):
  - every variant's passes other than the final one hash identical (the same estimate in every mode);
  - the calibration of the READ PATH (M2c_period40_v10, a rigid translation at 10 px/frame): inside the object's
    interior (the scene law's box shrunk by 4 px) the fitted velocity's median reads 10 px/frame in x and 0 in y to
    0.01 px; the links are not held to it, since their error is what is being measured (reported per tau). The first
    form of this check held every link to 0.01 px and failed on a sound read: link error median 0.11 px, p90 0.59;
  - the far background (beyond 48 px of the box): the fitted velocity and the live links exactly zero in the median;
  - every tau a whole number of source intervals;
  - the weights lie in [0, 1], the taus are the window's (all multiples of the source interval), nlinks equals the
    count of w > 0.05, and every fitted texel has state bits cut_ok, solve_ok and snap_ok set.
The repeat control (one variant rendered twice, byte-identical) is the driver's, on the warmed deterministic host.

OUTPUT. <case>.npz, all float32, frames F in the order rendered, crop rows 160..559 (y0 = 160 in the full frame):
  d [F,6,400,1280,2] px; w [F,6,400,1280]; tau [F,6,400,1280]; tc [F,400,1280]; state, nlinks [F,400,1280] (int8);
  vfit [F,400,1280,2] px/frame; resid [F,400,1280] px; frames [F] (the output frame numbers). manifest.json says the
  same, with the host, the build, the source shader's hash and the checks' numbers. Truth is GPT's to compute from
  the scene law (sext_resid.py's scene_law reads it from tests/scenes.sh).
"""
import hashlib
import json
import os
import pathlib
import re
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
W, H, Y0 = 1280, 400, 160
LINKS = 6
MODES = list(range(20, 33))
ANCHOR_MARK = ("        if (HOOKED_pos.x < 24.0 * HOOKED_pt.x && HOOKED_pos.y < 24.0 * HOOKED_pt.y)\n"
               "            return tri_diag_marker();")


# ----------------------------------------------------------------------------------------------- the variants
def mk(mode, out, shader=None):
    mode = int(mode)
    assert mode in MODES, "mode must be 20..32"
    src = pathlib.Path(shader) if shader else REPO / "shaders" / "sextdirectional-interpolation-propagated.glsl"
    txt = src.read_text(encoding="utf-8")
    cut = txt.index("// ==== human-reading tail")
    head, tail = txt[:cut], txt[cut:]
    # the final pass is the last //!HOOK of the head; every injection goes there and only there
    fp = head.rindex("//!HOOK ")
    pre, fin = head[:fp], head[fp:]

    def sub(old, new):
        nonlocal fin
        n = fin.count(old)
        assert n == 1, "%r found %d times in the final pass (want 1)" % (old[:70], n)
        fin = fin.replace(old, new)

    sub("const int TRI_DIAG = 0;", "const int TRI_DIAG = %d;" % mode)
    sub("    float resid_px = 0.0;\n",
        "    float resid_px = 0.0;\n"
        "    vec2 xd_q[6]; float xw_q[6]; float xt_q[6];   // [probe export_links]\n"
        "    float xtc_q = 0.0, xst_q = 0.0, xnl_q = 0.0, xr_q = 0.0; vec2 xv_q = vec2(0.0);\n")
    sub("        for (int k = 0; k < 6; k++) if (w[k] > 0.05) nlinks++;\n",
        "        for (int k = 0; k < 6; k++) if (w[k] > 0.05) nlinks++;\n"
        "        for (int k = 0; k < 6; k++) { xd_q[k] = d[k]; xw_q[k] = w[k]; xt_q[k] = tau[k]; }\n"
        "        xnl_q = float(nlinks); xst_q = (cut_adj <= SCENE_CUT_DIFF) ? 1.0 : 0.0;\n")
    sub("                tc /= max(sw, 1.0e-6);\n            }\n",
        "                tc /= max(sw, 1.0e-6);\n            }\n            xtc_q = tc;\n")
    sub("            if (ok) {\n", "            if (ok) {\n                xst_q += 2.0;\n")
    sub("                if (snap_px <= SNAP_MAX_PX) {\n",
        "                if (snap_px <= SNAP_MAX_PX) {\n"
        "                    xst_q += 12.0;   // snap_ok (4) and fitted (8): the fit is accepted exactly here\n"
        "                    { float u0 = -tc;\n"
        "                      xv_q = vec2(sx[1] + sx[2] * u0 + sx[3] * u0 * u0 * 0.5 + sx[4] * u0 * u0 * u0 / 6.0,\n"
        "                                  sy[1] + sy[2] * u0 + sy[3] * u0 * u0 * 0.5 + sy[4] * u0 * u0 * u0 / 6.0); }\n")
    rline = ("resid_px = sqrt(num / max(den, 1.0e-6));" if "resid_px = sqrt(num / max(den, 1.0e-6));" in fin
             else None)
    assert rline, "the residual line is not the per-axis form of 2026-10-22: regenerate the sext"
    sub(rline, rline + "\n                    xr_q = resid_px;")
    inj = (
        "        if (TRI_DIAG >= 20 && TRI_DIAG <= 32) {   // [probe export_links]\n"
        "            vec2 vq = vec2(0.0);\n"
        "            if (TRI_DIAG <= 25) vq = xd_q[clamp(TRI_DIAG - 20, 0, 5)] / HOOKED_pt;\n"
        "            if (TRI_DIAG == 31) vq = xv_q / HOOKED_pt;\n"
        "            if (TRI_DIAG <= 25 || TRI_DIAG == 31) {\n"
        "                vec2 wq = clamp(floor(vq * 0.25), -16.0, 15.0);\n"
        "                return vec4(vq * 0.25 - wq, ((wq.x + 16.0) * 32.0 + (wq.y + 16.0)) / 1024.0, 1.0);\n"
        "            }\n"
        "            if (TRI_DIAG == 26) return vec4(xw_q[0], xw_q[1], xw_q[2], 1.0);\n"
        "            if (TRI_DIAG == 27) return vec4(xw_q[3], xw_q[4], xw_q[5], 1.0);\n"
        "            if (TRI_DIAG == 28) return vec4(xt_q[0] / 8.0 + 0.5, xt_q[1] / 8.0 + 0.5, xt_q[2] / 8.0 + 0.5, 1.0);\n"
        "            if (TRI_DIAG == 29) return vec4(xt_q[3] / 8.0 + 0.5, xt_q[4] / 8.0 + 0.5, xt_q[5] / 8.0 + 0.5, 1.0);\n"
        "            if (TRI_DIAG == 30) return vec4(xtc_q / 8.0 + 0.5, xst_q / 16.0, xnl_q / 8.0, 1.0);\n"
        "            return vec4(clamp(xr_q / 64.0, 0.0, 1.0), 0.0, 0.0, 1.0);\n"
        "        }\n")
    sub(ANCHOR_MARK, inj + ANCHOR_MARK)
    pathlib.Path(out).write_text(pre + fin + tail, encoding="utf-8", newline="\n")
    print("variant TRI_DIAG %d -> %s" % (mode, out))


def estimator_hash(path):
    """The hash of every pass but the final one, and of the tail: what must be identical across the variants."""
    txt = pathlib.Path(path).read_text(encoding="utf-8")
    cut = txt.index("// ==== human-reading tail")
    head = txt[:cut]
    fp = head.rindex("//!HOOK ")
    return hashlib.sha256((head[:fp] + txt[cut:]).encode()).hexdigest()


# ----------------------------------------------------------------------------------------------- decoding
def frames_of(path):
    raw = np.fromfile(path, dtype="<u2")
    n = raw.size // (W * H * 4)
    assert n > 0 and raw.size == n * W * H * 4, "%s: not a whole number of %dx%d rgba64le frames" % (path, W, H)
    return raw.reshape(n, H, W, 4).astype(np.float64) / 65535.0


def split_v(fr):
    """Undo the split encoding: px per component."""
    r, g, b = fr[..., 0], fr[..., 1], fr[..., 2]
    code = np.rint(b * 1024.0)
    wx = np.floor(code / 32.0) - 16.0
    wy = np.mod(code, 32.0) - 16.0
    return np.stack([4.0 * (r + wx), 4.0 * (g + wy)], axis=-1)


def pack(outdir, cases):
    outdir = pathlib.Path(outdir)
    alarms, man = [], {"spec": "MATHS.md, the smallest next export (GPT, 2026-10-22)", "crop_y0": Y0, "width": W,
                       "height": H, "cases": {}}
    hpath = outdir / "hashes.txt"
    man["estimator_hashes_identical"] = hpath.exists() and "IDENTICAL" in hpath.read_text()
    if not man["estimator_hashes_identical"]:
        alarms.append("the variants' estimator passes are not shown identical (hashes.txt)")
    for case in cases:
        cd = outdir / case
        fr = {m: frames_of(cd / ("m%d.raw" % m)) for m in MODES}
        nf = {m: len(v) for m, v in fr.items()}
        if len(set(nf.values())) != 1:
            alarms.append("%s: modes rendered different frame counts %s" % (case, nf))
            continue
        F = nf[MODES[0]]
        d = np.stack([split_v(fr[20 + k]) for k in range(LINKS)], axis=1)            # [F,6,H,W,2]
        w = np.concatenate([fr[26][..., :3], fr[27][..., :3]], axis=-1)               # [F,H,W,6]
        tau = (np.concatenate([fr[28][..., :3], fr[29][..., :3]], axis=-1) - 0.5) * 8.0
        tc = (fr[30][..., 0] - 0.5) * 8.0
        state = np.rint(fr[30][..., 1] * 16.0).astype(np.int8)
        nlinks = np.rint(fr[30][..., 2] * 8.0).astype(np.int8)
        vfit = split_v(fr[31])
        resid = fr[32][..., 0] * 64.0
        w = np.moveaxis(w, -1, 1); tau = np.moveaxis(tau, -1, 1)                       # [F,6,H,W]
        frames = [int(x) for x in (cd / "frames.txt").read_text().split()]
        checks = {}
        # sanity of the plain channels
        checks["w_in_0_1"] = bool(np.all((w >= -1e-3) & (w <= 1.0 + 1e-3)))
        checks["nlinks_matches_w"] = float(np.mean(nlinks == np.sum(w > 0.05, axis=1)))
        fitted = (state & 8) != 0
        checks["fitted_share"] = float(np.mean(fitted))
        checks["fitted_have_cut_solve_snap"] = bool(np.all((state[fitted] & 7) == 7))
        checks["fitted_have_4plus_links"] = bool(np.all(nlinks[fitted] >= 4))
        if checks["w_in_0_1"] is False or checks["fitted_have_cut_solve_snap"] is False or checks["nlinks_matches_w"] < 0.999:
            alarms.append("%s: channel sanity failed %s" % (case, checks))
        # The geometry from the scene law, as sext_resid.py proved it: the object's box at T = n / 24 (N:N), its
        # interior (shrunk by 4 px) and the far background (beyond 48 px of the box).
        sys.path.insert(0, str(HERE))
        import sext_resid
        x0, y0, bw, bh, _ = sext_resid.scene_law(case)
        Y = (np.arange(H) + Y0 + 0.5)[:, None]
        X = (np.arange(W) + 0.5)[None, :]
        inside = lambda T, m: (X > x0(T) - m) & (X < x0(T) + bw + m) & (Y > y0 - m) & (Y < y0 + bh + m)
        interior = np.stack([inside(n / 24.0, -4.0) for n in frames])
        far = np.stack([~inside(n / 24.0, 48.0) for n in frames])
        live = w > 0.05
        # The read path (gated): the fitted velocity's median inside the object and the far background's. The
        # links themselves carry the estimator's error, which is what this export exists to measure: reported per
        # tau, never gated. The taus must be the window's (whole source intervals).
        fi = interior & fitted
        checks["interior_fitted_texels"] = int(fi.sum())
        checks["vfit_interior_median"] = [float(np.median(vfit[..., 0][fi])), float(np.median(vfit[..., 1][fi]))]
        ff = far & fitted
        checks["vfit_far_median_abs"] = float(np.median(np.abs(vfit[ff]))) if ff.any() else None
        lf = live & far[:, None]
        checks["links_far_median_abs_px"] = float(np.median(np.abs(d[lf]))) if lf.any() else None
        checks["links_far_p99_abs_px"] = float(np.percentile(np.abs(d[lf]), 99)) if lf.any() else None
        checks["taus_whole_intervals"] = bool(np.all(np.abs(tau[live] - np.rint(tau[live])) < 1e-3))
        law = []
        for k, n in enumerate(frames):
            for kk in range(LINKS):
                m = live[k, kk] & interior[k]
                if not m.any():
                    continue
                t = float(np.median(tau[k, kk][m]))
                truth = x0((n + t) / 24.0) - x0(n / 24.0)        # the object's displacement over tau (x only)
                law.append((t, float(np.median(d[k, kk, ..., 0][m]) - truth), float(np.percentile(np.abs(d[k, kk, ..., 0][m] - truth), 90))))
        by_tau = {}
        for t, med, p90 in law:
            by_tau.setdefault(round(t), []).append((med, p90))
        checks["link_x_error_by_tau_median_p90"] = {str(t): [float(np.median([a for a, _ in v])), float(np.median([b for _, b in v]))]
                                                    for t, v in sorted(by_tau.items())}
        bad = []
        if case == "M2c_period40_v10":                 # the calibration: a rigid translation at 10 px/frame (exact name: M2c_v6 is 6)
            vx, vy = checks["vfit_interior_median"]
            if abs(vx - 10.0) > 0.01 or abs(vy) > 0.01 or checks["interior_fitted_texels"] < 100000:
                bad.append("the translation does not read 10 px/frame to 0.01 inside the object")
        if checks["vfit_far_median_abs"] not in (None, 0.0):
            bad.append("the far background's fitted velocity is not exactly zero in the median")
        if checks["links_far_median_abs_px"] not in (None, 0.0):
            bad.append("the far background's links are not exactly zero in the median")
        if not checks["taus_whole_intervals"]:
            bad.append("a tau is not a whole number of source intervals")
        if bad:
            alarms.append("%s: %s" % (case, "; ".join(bad)))
        np.savez_compressed(outdir / ("%s.npz" % case), d=d.astype(np.float32), w=w.astype(np.float32),
                            tau=tau.astype(np.float32), tc=tc.astype(np.float32), state=state, nlinks=nlinks,
                            vfit=vfit.astype(np.float32), resid=resid.astype(np.float32),
                            frames=np.array(frames, np.int32))
        man["cases"][case] = {"frames": frames, "checks": checks}
        print("%s: %d frames packed; %s" % (case, F, json.dumps(checks)))
    man["alarms"] = alarms
    for k in ("host", "ffmpeg", "shader_sha256", "repeat_control"):
        p = outdir / (k + ".txt")
        man[k] = p.read_text().strip() if p.exists() else None
    if not man["repeat_control"] or "IDENTICAL" not in man["repeat_control"]:
        alarms.append("no passing repeat control (repeat_control.txt)")
    (outdir / "manifest.json").write_text(json.dumps(man, indent=1))
    for a in alarms:
        print("ALARM", a)
    print("EXPORT PACK %s" % ("PASS" if not alarms else "FAIL"))
    return 1 if alarms else 0


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "mk":
        mk(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif len(sys.argv) >= 3 and sys.argv[1] == "hashes":
        hs = {p: estimator_hash(p) for p in sys.argv[2:]}
        same = len(set(hs.values())) == 1
        for p, h in hs.items():
            print(h[:16], os.path.basename(p))
        print("ESTIMATOR PASSES %s" % ("IDENTICAL" if same else "DIFFER"))
        sys.exit(0 if same else 1)
    elif len(sys.argv) >= 4 and sys.argv[1] == "pack":
        sys.exit(pack(sys.argv[2], sys.argv[3:]))
    else:
        print(__doc__.split("WHY.")[0]); sys.exit(2)
