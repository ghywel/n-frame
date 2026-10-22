#!/usr/bin/env python3
"""WHERE C3's DECIBELS GO: the shaders' flow on the spinning bars against the scene's exact flow, level by level, and
the oracle's warp fed the shaders' flow with the truth substituted class by class (2026-10-22, after c3_oracle.py
found a flow route 7 dB above the blend and 13 above the shipped tiers).

    c3_flow.py run  <work> <shader.glsl> [<shader.glsl> ...]    GPU: per shader, four taps of the A->B flow on C3 at N:N
    c3_flow.py read <work>                                       CPU: the reading below, from the saved taps
    c3_flow.py calib <work> <shader.glsl>                         GPU: the taps' units on M2c_period40_v10 (10 px/frame)

THE TAPS (dump_masks.py's tapped(): a pass after "[high] motion-compensated warp", the reading tail re-pointed to it,
read_view 4, rgb48le inside the graph, decoded at (8 i + 4, 8 j + 4)): the flow in full-resolution px per source frame,
each level's LAST saved texture read by texelFetch at the 1/8 cell's centre: S = FLOW_S_AB.xy x 16 (the 1/16 level's
zero-descent candidate), E = FLOW_E_AB x 8 (the 1/8 level after its propagation and data check), Q = FLOW_Q_AB x 4 (the
quarter level after its variational, medians and, in the High tier, the carry, adoption and lattice), H = FLOW_H_AB x 2
(the half-res flow the warp uses). Units checked on the run: the wall outside the disc moves rigidly too, so every
level's median there must agree with the truth to a pixel, or the reading refuses.

THE TRUTH (scenes.sh C3, the oracle's law): v = (1, 0.5) + (0.15 / 24)(-(Y - cy), X - cx) px per source frame,
cx = 640 + 24 t, cy = 360 + 12 t; the bars vary along the rotated x axis, so the ACROSS-bar unit vector at time t is
(cos 0.15 t, sin 0.15 t) and ALONG is its perpendicular. Output n of the N:N render is read as the pair (n, n + 1);
the truth moves 0.006 px per frame and the bars turn 0.36 degrees per frame, so a one-pair misalignment is invisible
to the error split. The disc: the bars fill radius 300 about the grid's origin; cells within 280 px of the origin at
time t are the disc, cells beyond 330 px and inside the frame less 32 px are the wall.

THE SPLIT (CPU, the oracle's warp exactly: A warped by -f v and B by +(1 - f) v at each OUTPUT pixel, time-weighted,
bilinear, scored on cage.sh's rectangle over the same 89 output instants): v is the shader's H flow, upsampled
bilinearly from the 1/8 grid, of the pair bracketing the instant; then the same with the truth put back on one class
of texels at a time:
    shader         the H flow as tapped                            (instrument: within 1.5 dB of the GPU's disc number)
    fix-gross      truth where |across error| > 2 px                (the period-off texels, a bar or two out)
    fix-across     the across component replaced by the truth's everywhere, the along error kept
    fix-along      the along component replaced everywhere, the across error kept
    fix-fine       truth where |error| <= 2 px only
    fix-period     truth where the across error is within 1.5 px of +-9 or +-18 (a whole bar period or two out); ADDED
                   AFTER THE FIRST READ, exploratory, not pre-registered: what a rival one period away could recover
    truth          the oracle's oracle-flow row (36.47 on the record)

PRE-REGISTERED (before the run):
  P1 THE GROSS TEXELS CARRY THE GAP: fix-gross recovers at least 80% of the dB from shader to truth.
  P2 ALONG IS FREE: fix-along moves the disc under 0.5 dB (the record: the normal-flow projection changed nothing);
     fix-across recovers at least 90% of the gap.
  P3 THE ERROR ENTERS COARSE: the 9 px bars alias at both the 1/16 and the 1/8 pitch (to a 72 px Moire that moves
     about eight times the bars' speed), so the disc's gross fraction is already at least as high at S or E as at H,
     and the finer levels, which nudge by a pixel, do not remove it.
     Killed if S and E are mostly right (gross under half of H's) and the gross appears at Q or H (the variational
     or the median stages would then be making it).
  The instrument fails, and nothing is read, if the shader row is more than 1.5 dB from the GPU's disc number, or a
  level's wall median misses the truth by more than 1 px.
  AMENDED AFTER THE FIRST READ (post hoc, said so): the 1/16 level's wall median missed by 1.65 and 1.20 px and the
  rule refused everything; at C3's 1-2 px wall speeds a 16 px texel's precision alone misses by that much, so the
  median cannot tell wrong units from coarse precision. The units check is now the wall's least-squares slope of the
  tapped flow on the truth (both components pooled; the rotation spreads the truth over about -3..+3 px): a level is
  read only if its slope is within 0.8..1.25; the split, which uses the H flow alone, keeps the original rule for H.
  AMENDED AGAIN (post hoc): every level's wall slope read 0.4-0.7, so the slope cannot separate units from the
  estimator's own under-read on a flat-blocked, slowly rotating wall either. The units are taken from `calib` instead
  (M2c_period40_v10, exactly 10 px/frame: H 9.69, Q 9.63, E 8.00 (one 8 px texel), S 11.75 (0.75 of a 16 px texel):
  the scale is right at every level, the coarse two read at their step); the slopes are printed as data, and the
  split keeps the original rule for H (its wall median within 1 px) and the 1.5 dB picture check.
WHY ALWAYS -9 (`c3_flow.py moire <work>`; pre-registered 2026-10-22 evening, before the computation, from the taps
already saved): the bars' 9 px period sampled at the 1/8 pitch (8 px) and at the 1/16 pitch (16 px, the second
harmonic) aliases in both cases to f' = 1/9 - 1/8 = -1/72 per px: a 72 px Moire moving at -8 times the bars' across
velocity v_a (reversed, eight times as fast). On the disc v_a = v . n runs about -0.7 to +2.9 px (the +1 px translation
plus the rotation's +-1.75), so:
  M1 the 1/16 level's across error is about -9 v_a: its least-squares slope on v_a over the disc lies in [-11, -7];
  M2 the finer levels lock the nearest basin of the true bars to the Moire's reading: at H the across error equals
     -9 round(v_a) within 1.5 px on at least half of the disc's texels, and in each v_a band ((-1, -0.5), (-0.5, 0.5),
     (0.5, 1.5), (1.5, 2.5), (2.5, 3)) the commonest error is that band's -9 round(v_a) (+9, 0, -9, -18, -27);
  so the one-sidedness is v_a's sign, the translation's: killed if the slope at S is outside [-11, -7] or M2 holds on
  under a quarter of the disc.
Numbers only; the taps stay in <work>.
"""
import os
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
TESTS = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "trust"))
import dump_masks                                                                 # noqa: E402  (tapped(), FS)

FF = os.environ.get("FFMPEG", os.path.expanduser("~/np-build/ffmpeg/ffmpeg"))
W, H = 1280, 720
OMEGA, VX, VY = 0.15, 24.0, 12.0
LEVELS = {"S": ("FLOW_S_AB", 16.0), "E": ("FLOW_E_AB", 8.0), "Q": ("FLOW_Q_AB", 4.0), "H": ("FLOW_H_AB", 2.0)}
for lv, (tex, k) in LEVELS.items():
    dump_masks.TAPS[f"c3{lv}"] = ("[high] motion-compensated warp", [tex], f"""
    vec2 p = (gl_FragCoord.xy * 8.0) / HOOKED_size;
    return vec4(texelFetch({tex}_raw, ivec2(p * {tex}_size), 0).xy * {k:.1f}, 0.0, 0.0);""")


def scene(rate):
    return subprocess.run(["bash", "-c", f". '{TESTS}/scenes.sh'; scene_edge C3_bars_spin_drift {rate}"],
                          capture_output=True, text=True, check=True).stdout.strip()


def run(work, shaders):
    for sh in shaders:
        sh = pathlib.Path(sh); name = sh.stem
        for lv in LEVELS:
            glsl = work / f"_{name}-{lv}.glsl"
            glsl.write_text(dump_masks.tapped(sh.read_text(), f"c3{lv}"))
            dst = work / f"{name}-{lv}.rgb48"
            cmd = [FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "warning", "-init_hw_device", "vulkan=vk",
                   "-filter_hw_device", "vk", "-f", "lavfi", "-i", scene(24) + ",format=rgb48le",
                   "-vf", f"libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path={glsl},format=rgb48le",
                   "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb48le", str(dst)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            e = r.stderr.lower()
            if r.returncode or any(s in e for s in ("compile status", "disabling", "failed to configure", "error reinit")):
                sys.exit(f"{name} {lv}: REFUSED (the shader did not run):\n{r.stderr[:600]}")
            n = os.path.getsize(dst) // (H * W * 6)
            if n < 40: sys.exit(f"{name} {lv}: {n} frames: REFUSED")
            print(f"  {name} {lv}: {n} frames", flush=True)


def tap(path):
    a = np.fromfile(path, np.uint16)
    n = a.size // (H * W * 3)
    return (a[: n * H * W * 3].reshape(n, H, W, 3)[:, 4::8, 4::8, :2].astype(np.float64) / 65535.0 - 0.5) * 2 * dump_masks.FS


CY, CX = np.mgrid[0:H // 8, 0:W // 8].astype(np.float64)
CY, CX = CY * 8 + 4.0, CX * 8 + 4.0


def truth(t, X, Y):
    cx, cy = 640 + VX * t, 360 + VY * t
    return np.stack([1.0 + (OMEGA / 24.0) * (-(Y - cy)), 0.5 + (OMEGA / 24.0) * (X - cx)], -1)


def split(e, t):
    th = OMEGA * t
    n = np.array([np.cos(th), np.sin(th)])
    a = e @ n
    return a, e @ np.array([-n[1], n[0]])


def regions(t):
    r = np.hypot(CX - 640 - VX * t, CY - 360 - VY * t)
    inner = (CX > 32) & (CX < W - 32) & (CY > 32) & (CY < H - 32)
    return r < 280, (r > 330) & inner


def up(f8):
    """a 1/8-grid flow (cells at 8 i + 4) to every pixel, bilinear"""
    fy = (np.arange(H) - 4.0) / 8.0; fx = (np.arange(W) - 4.0) / 8.0
    y0 = np.clip(np.floor(fy).astype(int), 0, f8.shape[0] - 1); x0 = np.clip(np.floor(fx).astype(int), 0, f8.shape[1] - 1)
    y1 = np.minimum(y0 + 1, f8.shape[0] - 1); x1 = np.minimum(x0 + 1, f8.shape[1] - 1)
    wy = np.clip(fy - y0, 0, 1)[:, None, None]; wx = np.clip(fx - x0, 0, 1)[None, :, None]
    return ((f8[y0][:, x0] * (1 - wx) + f8[y0][:, x1] * wx) * (1 - wy) + (f8[y1][:, x0] * (1 - wx) + f8[y1][:, x1] * wx) * wy)


def read(work):
    sys.argv = [sys.argv[0], str(work / "oracle")]
    import importlib
    sys.path.insert(0, str(HERE))
    o = importlib.import_module("c3_oracle")
    names = sorted({p.name.rsplit("-", 1)[0] for p in work.glob("*-H.rgb48") if not p.name.startswith("calib-")})
    src = o.luma(24); tru = o.luma(60)
    sl = (slice(o.RY, o.RY + o.RH), slice(o.RX, o.RX + o.RW))
    for name in names:
        F = {lv: tap(work / f"{name}-{lv}.rgb48") for lv in LEVELS}
        nf = min(len(v) for v in F.values())
        print(f"\n== {name}: {nf} pairs; flow error on the disc (cells within 280 px of the origin), frames 2..{nf - 3}")
        print(f"  {'level':5s} {'wall med err':>12s} {'gross%':>7s} {'across |e| med/p90 (gross)':>27s} {'along |e| med/p90':>18s}")
        refuse = False
        gross_by = {}
        for lv in LEVELS:
            G, A, AL, WALL, TW, FW = [], [], [], [], [], []
            for n in range(2, nf - 2):
                t = n / 24.0
                disc, wall = regions(t)
                e = F[lv][n] - truth(t, CX, CY)
                a, al = split(e, t)
                g = np.hypot(e[..., 0], e[..., 1]) > 2.0
                G.append(g[disc]); A.append(np.abs(a[disc][g[disc]])); AL.append(np.abs(al[disc]))
                WALL.append(np.hypot(*np.median(e[wall], 0)))
                TW.append(truth(t, CX, CY)[wall].ravel()); FW.append(F[lv][n][wall].ravel())
            G = np.concatenate(G); A = np.concatenate(A); AL = np.concatenate(AL)
            wm = float(np.median(WALL)); gross_by[lv] = 100 * G.mean()
            tw, fw = np.concatenate(TW), np.concatenate(FW)
            slope = float(np.polyfit(tw, fw, 1)[0])
            ok = 0.8 <= slope <= 1.25
            if lv == "H": refuse |= wm > 1.0
            print(f"  {lv:5s} {wm:12.2f} {100 * G.mean():7.1f} {np.median(A) if A.size else 0:13.2f} / {np.percentile(A, 90) if A.size else 0:5.2f}"
                  f"        {np.median(AL):6.2f} / {np.percentile(AL, 90):5.2f}   wall slope {slope:5.2f}")
        if refuse:
            print("  REFUSED: the H flow's wall median misses the truth by more than 1 px; no split read")
            continue
        rows = {k: [] for k in ("shader", "fix-gross", "fix-across", "fix-along", "fix-fine", "fix-period", "truth")}
        n60 = min(len(tru), (nf - 1) * 60 // 24)
        XX, YY = o.XX, o.YY
        for n in range(n60):
            if n + 1 <= 5 or (n + 1) % 5 == 1:
                continue
            t = n / 60.0
            k = int(np.floor(t * 24.0 + 1e-9)); f = t * 24.0 - k
            if k + 1 >= len(src) or k >= nf:
                break
            A_, B_ = src[k], src[k + 1]
            T = tru[n]
            vs = up(F["H"][k])                                   # the pair (k, k + 1)'s flow, at every pixel
            vt = np.moveaxis(o.flow_at(t), 0, -1)
            e = vs - vt
            th = OMEGA * t; nn = np.array([np.cos(th), np.sin(th)]); pp = np.array([-nn[1], nn[0]])
            ea = (e @ nn)[..., None] * nn; el = (e @ pp)[..., None] * pp
            gross = (np.abs(e @ nn) > 2.0)[..., None]
            fine = (np.hypot(e[..., 0], e[..., 1]) <= 2.0)[..., None]
            ac = np.abs(e @ nn)
            period = ((np.abs(ac - 9.0) <= 1.5) | (np.abs(ac - 18.0) <= 1.5))[..., None]
            cand = {"shader": vs, "fix-gross": np.where(gross, vt, vs), "fix-across": vs - ea, "fix-along": vs - el,
                    "fix-fine": np.where(fine, vt, vs), "fix-period": np.where(period, vt, vs), "truth": vt}
            for key, v in cand.items():
                wa = o.bilinear(A_, XX - f * v[..., 0], YY - f * v[..., 1])
                wb = o.bilinear(B_, XX + (1 - f) * v[..., 0], YY + (1 - f) * v[..., 1])
                rows[key].append(o.psnr(((1 - f) * wa + f * wb)[sl], T[sl]))
        base, top = np.mean(rows["shader"]), np.mean(rows["truth"])
        print(f"  the split ({len(rows['shader'])} output instants, the disc rectangle, PSNR-Y dB; share of the shader->truth gap)")
        for key, v in rows.items():
            m = np.mean(v)
            print(f"    {key:11s} {m:6.2f}   {100 * (m - base) / (top - base) if top != base else 0:6.1f}%")
        print(f"  P3: gross% by level S {gross_by['S']:.1f}, E {gross_by['E']:.1f}, Q {gross_by['Q']:.1f}, H {gross_by['H']:.1f}")


def calib(work, shader):
    """the units, from a scene the estimator reads cleanly: M2c_period40_v10, a 300 px box of period-40 texture
    translating exactly 10 px per source frame; every level's median inside the box (eroded 48 px) must read (10, 0)
    within 0.5 px"""
    sh = pathlib.Path(shader); s24 = subprocess.run(["bash", "-c", f". '{TESTS}/scenes.sh'; scene M2c_period40_v10 24"],
                                                    capture_output=True, text=True, check=True).stdout.strip()
    bad = 0
    for lv in LEVELS:
        glsl = work / f"_calib-{lv}.glsl"; glsl.write_text(dump_masks.tapped(sh.read_text(), f"c3{lv}"))
        dst = work / f"calib-{lv}.rgb48"
        r = subprocess.run([FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "warning", "-init_hw_device", "vulkan=vk",
                            "-filter_hw_device", "vk", "-f", "lavfi", "-i", s24 + ",format=rgb48le", "-vf",
                            f"libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path={glsl},format=rgb48le",
                            "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb48le", str(dst)],
                           capture_output=True, text=True)
        if r.returncode or "compile status" in r.stderr.lower(): sys.exit(f"calib {lv}: REFUSED\n{r.stderr[:400]}")
        f = tap(dst); v = []
        for n in range(4, min(len(f), 20)):
            x0 = 240 * n / 24.0
            m = (CX >= x0 + 48) & (CX < x0 + 300 - 48) & (CY >= 210 + 48) & (CY < 510 - 48)
            v.append(f[n][m])
        med = np.median(np.concatenate(v), 0)
        ok = abs(med[0] - 10) <= 0.5 and abs(med[1]) <= 0.5; bad += not ok
        print(f"  calib {lv}: median ({med[0]:+.3f}, {med[1]:+.3f}) px/frame against (+10, 0): {'OK' if ok else 'UNITS WRONG'}")
    return bad


def moire(work):
    names = sorted({p.name.rsplit("-", 1)[0] for p in work.glob("*-H.rgb48") if not p.name.startswith("calib-")})
    for name in names:
        print(f"== {name}")
        for lv in ("S", "E", "Q", "H"):
            F = tap(work / f"{name}-{lv}.rgb48")
            VA, EA = [], []
            for n in range(2, len(F) - 2):
                t = n / 24.0
                disc, _ = regions(t)
                tr = truth(t, CX, CY)
                va, _ = split(tr, t); ea, _ = split(F[n] - tr, t)
                VA.append(va[disc]); EA.append(ea[disc])
            va, ea = np.concatenate(VA), np.concatenate(EA)
            slope = float(np.polyfit(va, ea, 1)[0])
            pred = -9.0 * np.round(va)
            hit = 100 * np.mean(np.abs(ea - pred) <= 1.5)
            bands = []
            for lo, hi in ((-1, -0.5), (-0.5, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 3.0)):
                m = (va >= lo) & (va < hi)
                if m.sum() < 50: bands.append(f"[{lo},{hi}) n<50"); continue
                h, e = np.histogram(ea[m], bins=np.arange(-31.5, 32.5, 1.0))
                bands.append(f"[{lo},{hi}) {100 * m.mean():.0f}%: mode {int(e[np.argmax(h)] + 0.5):+d} (pred {int(-9 * round((lo + hi) / 2)):+d})")
            print(f"  {lv}: slope of across error on v_a {slope:+.2f}; error = -9 round(v_a) within 1.5 px on {hit:.1f}%")
            print("     " + "; ".join(bands))


if __name__ == "__main__":
    mode, work = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    if mode == "run":
        run(work, sys.argv[3:])
    elif mode == "moire":
        moire(work)
    elif mode == "calib":
        sys.exit(1 if calib(work, sys.argv[3]) else 0)
    elif mode == "read":
        read(work)
    else:
        sys.exit(__doc__)
