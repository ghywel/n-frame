#!/usr/bin/env python3
"""THE HELD TRUST GATE'S ONE UNEXPLAINED RUN, DUMPED (2026-10-22, the swarm's periodic-alias lane, proposal 4a).
ENERGY-TRANSFER.md "Where the per-level trust gate stands": L2 passed on medians, and frame by frame one extract
(Sonic the Hedgehog @4341, odd frames 815-833 of the half-rate test) read -2.4 to -3.0 dB under trust5. Nobody has
looked at those frames. This dumps what the gate did there, cell by cell, and applies a written decision rule.

    dump_masks.py build <work>                                      CPU: generates <work>/high.glsl (the High tier's
                                                                    recipe, no prune) and <work>/trust5.glsl (the same
                                                                    + TRUST_GATE=1 TRUST_UNIQUE=1 TRUST_ALIAS=0.7)
    dump_masks.py run <work> <source video> <t0 s> [first:last=800:840] [run=815:833]
                                                                    GPU (Vulkan): the half-rate graph of halfrate.py on
                                                                    the extract, pictures of both shaders and four taps
                                                                    of trust5, every ffmpeg line printed before it runs;
                                                                    then the reading below
    dump_masks.py read <work> [first:last] [run]                    CPU: the reading again from the saved dumps

THE GRAPH is halfrate.py's, verbatim: scale to 1280 wide, keep the even frames (12 fps), interpolate the odd ones back
at 24 through libplacebo, so output frame k (0-based) is the real frame k's instant and odd k are the interpolated
ones. Only frames first..last are kept from each run (select after the mixer), the shaders having run from the
extract's start so their caches hold the same history as in L2.

THE TAPS (leveltap.py's method: a pass copying one quantity per 1/8 cell into DIAG_TAP right after a named pass, the
reading tail re-pointed to it, read_view 4: 0.5 + px / 64 in R and G, rgb48le inside the graph; decoded at pixel
(8 i + 4, 8 j + 4), which carries a 1/16 bleed of the next cell, harmless for flags and for vectors read to a pixel):
    open    after [trust] apply (AB):  x = the gate's count of 5 x 5 margins under 0.3 (opens at 5 or more),
                                       y = 10 x the aliasing ratio (box range / point range; opens under 0.7; 30 = flat)
    tg      after [trust] apply (AB):  x = 10 where the cell was DECIDED (TG_AB.z), y = |decided vector| px
    tgvec   after [trust] apply (AB):  the decided vector, px
    qpre    after the carry's pick (AB), before the trust passes:  FLOW_Q_AB, px (the flow the decision replaced)

THE READING, per odd frame k in first..last (the run marked): PSNR-Y of each shader's picture against the real frame,
the share of 1/8 cells opened and decided, and for the decided cells the block scores recomputed from the REAL frames
k - 1 and k + 1 at full resolution (the 16 x 16 block the shader used, b0 = 8 cell - 4, bilinear B, no +-0.5 refine):
    r_h  = mean |A(x) - B(x + h)|  at the kept flow h  (the block's own residual: the frames' noise floor there)
    r_b  = the same at the decided vector b
    m    = r_h - r_b                (the margin the decision won by; the shader asked for 1/255 = 0.0039 after refine)
and the share of the two pictures' difference (|trust5 - default| over the frame) that falls within 16 px of a decided
cell (the warp's spread, READ_GATE_R).

THE DECISION RULE, written before the dump ran (the lane's report, proposal 4a; frames in the run against the frames
outside it in the same extract):
  (i)  NOISE-FLOOR DECISION  -> repair with one constant (TG_PICK scaled by r_h, proposal 4b):
       in the run the decided cells' median m is under 0.5 r_h (the margin is inside the block's own residual) with
       median r_h over 2/255, AND over half of the pictures' difference lies within 16 px of decided cells.
  (ii) THE OFFER'S FAULT     -> retire the gate as a tier, keep the switch:
       the decided cells' median m / r_h is over 1 (the block really prefers the alias by more than its residual): the
       content is locally periodic AND aliased, and only a region's consistency could refuse it (lead 3, parked).
  (iii) NOT THE GATE'S DECISIONS -> look downstream (the adoption, the lattice, the cut gate) and at CUT_MOTION:
       under 30 percent of the pictures' difference lies within 16 px of a decided cell, or fewer than 0.2 percent of
       the run's cells are decided while the pictures differ by 2 dB.
  Anything between is reported as such, with the numbers, and decides nothing.
Numbers only; the extract and the dumps stay in <work>. FFMPEG names the binary (default ~/np-build/ffmpeg/ffmpeg).
"""
import os
import pathlib
import re
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
TESTS = HERE.parent.parent
PY = sys.executable
FF = os.environ.get("FFMPEG", os.path.expanduser("~/np-build/ffmpeg/ffmpeg"))
FP = str(pathlib.Path(FF).with_name("ffprobe"))
if sys.platform == "darwin" and os.environ.get("MVK_DETERMINISTIC", "1") != "0":    # tests/mvk-env.sh's two switches
    os.environ.setdefault("MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS", "0")
    os.environ.setdefault("MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE", "1")
HIGH = "GLOBAL_SEED=1 QZERO_MOIRE=1 COHERENCE_GATE=1 COARSE_ENERGY=1 COARSE_ENERGY_WS=8 COARSE_ENERGY_WE=1 ALIAS_PRIOR=1 " \
       "ALIAS_CARRY=1 OUTLINE_ADOPT=1 PRINT_LATTICE=1 CUT_MOTION=1 ZERO_SEED=1"
TRUST = "TRUST_GATE=1 TRUST_UNIQUE=1 TRUST_ALIAS=0.7"
GEN = ['"0,0,8,4"', "0.3", "0.08", "{out}", "0", '"0,0,2,0"', "bidirectional-interpolation-propagated.glsl"]
W = 1280
FS = 32.0                                                   # read_view 4: 0.5 + px / (2 FS)
R16 = 16                                                    # the warp's spread past a cell, px (READ_GATE_R: 2 texels of 1/8)

TAPS = {
    "open": ("[trust] apply (AB)", ["ALIAS_E_M_ST", "LUMA_A_E", "TG_BOX_A"], """
    ivec2 cell = ivec2(gl_FragCoord.xy);
    ivec2 en = ivec2(LUMA_A_E_size);
    int nlow = 0;
    float plo = 1.0, phi = 0.0, blo = 1.0, bhi = 0.0;
    for (int y = -2; y <= 2; y++)
        for (int x = -2; x <= 2; x++) {
            ivec2 e = cell + ivec2(x, y);
            if (e.x >= 0 && e.y >= 0 && e.x < en.x && e.y < en.y && imageLoad(ALIAS_E_M_ST, e).x < 0.3) nlow++;
            ivec2 ec = clamp(e, ivec2(0), en - 1);
            vec2 uv = (vec2(ec) + 0.5) / vec2(en);
            float pv = LUMA_A_E_tex(uv).r, bv0 = TG_BOX_A_tex(uv).r;
            plo = min(plo, pv); phi = max(phi, pv); blo = min(blo, bv0); bhi = max(bhi, bv0);
        }
    float ratio = (phi - plo < 0.02) ? 3.0 : min((bhi - blo) / max(phi - plo, 1.0e-6), 3.0);
    return vec4(float(nlow), ratio * 10.0, 0.0, 0.0);"""),
    "tg": ("[trust] apply (AB)", ["TG_AB"], """
    vec4 g = texelFetch(TG_AB_raw, ivec2(gl_FragCoord.xy), 0);
    return vec4(g.z * 10.0, min(length(g.xy) * 4.0, 31.0), 0.0, 0.0);"""),
    "tgvec": ("[trust] apply (AB)", ["TG_AB"], """
    vec4 g = texelFetch(TG_AB_raw, ivec2(gl_FragCoord.xy), 0);
    return vec4(g.xy * 4.0, 0.0, 0.0);"""),
    "qpre": ("[alias] each quarter-level cell takes its cheaper hypothesis over the four scans (AB)", ["FLOW_Q_AB"], """
    return vec4(texelFetch(FLOW_Q_AB_raw, ivec2(HOOKED_pos * FLOW_Q_AB_size), 0).xy * 4.0, 0.0, 0.0);"""),
}


def say(cmd):
    print("  $ " + " ".join(cmd), flush=True)


def build(work):
    work.mkdir(parents=True, exist_ok=True)
    for name, env in (("high", HIGH), (f"trust5", HIGH + " " + TRUST)):
        out = work / f"{name}.glsl"
        cmd = ["env"] + env.split() + [PY, str(TESTS / "gen_variational.py")] + [a.format(out=out).strip('"') for a in GEN]
        say(cmd)
        subprocess.run(cmd, cwd=TESTS, check=True, stdout=subprocess.DEVNULL)
    a, b = (work / "high.glsl").read_text(), (work / "trust5.glsl").read_text()
    nt = b.count("//!DESC [trust]")
    assert nt >= 4 and a.count("//!DESC [trust]") == 0, nt
    print(f"built {work}/high.glsl and {work}/trust5.glsl ({nt} trust passes added; the shipped High tier differs from "
          f"high.glsl by the byte-identical prune only)")


def tapped(text, label):
    desc, binds, body = TAPS[label]
    t, n = re.subn(r"(//!PARAM read_view\n(?://!.*\n)+)0\n", r"\g<1>4\n", text); assert n == 1, "read_view's default"
    hits = [m.start() for m in re.finditer(re.escape("//!DESC " + desc), t)]
    assert hits, f"no pass '{desc}' in the shader"
    nxt = t.index("\n//!HOOK", hits[-1]) + 1
    tap = ("//!HOOK FRAME_MIX\n//!BIND HOOKED\n" + "".join(f"//!BIND {b}\n" for b in binds) +
           "//!SAVE DIAG_TAP\n//!WIDTH HOOKED.w 8 /\n//!HEIGHT HOOKED.h 8 /\n//!COMPONENTS 2\n"
           f"//!DESC [diag] tap {label}\nvec4 hook() {{{body}\n}}\n\n")
    t = t[:nxt] + tap + t[nxt:]
    a = "//!BIND HOOKED\n//!BIND FLOW_H_AB\n//!SAVE READ_FIELD\n"
    assert t.count(a) == 1, "the reading tail's READ_FIELD binding"
    t = t.replace(a, "//!BIND HOOKED\n//!BIND DIAG_TAP\n//!SAVE READ_FIELD\n")
    b = "    return vec4(FLOW_H_AB_tex(HOOKED_pos).xy * 2.0, 0.0, 1.0);\n"
    assert t.count(b) == 1, "the reading tail's READ_FIELD body"
    return t.replace(b, "    return vec4(texelFetch(DIAG_TAP_raw, ivec2(gl_FragCoord.xy), 0).xy, 0.0, 1.0);\n")


def height(video):
    wh = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h = int(wh[0]), int(wh[1])
    return (round(W * h / w / 2)) * 2


def run(work, video, t0, first, last, lo, hi):
    work.mkdir(parents=True, exist_ok=True)
    H = height(video)
    (work / "H").write_text(str(H))
    secs = (last + 8) / 24.0
    sel = f"select='between(n\\,{first}\\,{last})'"
    # the real frames first - 1 .. last + 1, gray, 1280 wide (the frames the odd ones are interpolated between)
    cmd = [FF, "-y", "-v", "error", "-ss", f"{t0:.2f}", "-t", f"{secs:.2f}", "-i", str(video), "-vf",
           f"scale={W}:-2,setpts=N/24/TB,select='between(n\\,{first - 1}\\,{last + 1})',format=gray", "-fps_mode",
           "passthrough", "-f", "rawvideo", str(work / "real.gray")]
    say(cmd); subprocess.run(cmd, check=True)
    for name in ("high", "trust5"):
        (work / f"_{name}.glsl").write_text((work / f"{name}.glsl").read_text())
        fc = (f"[0:v]scale={W}:-2,setpts=N/24/TB,select='not(mod(n\\,2))',setpts=N/12/TB,format=yuv420p,"
              f"libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path=_{name}.glsl,{sel},format=gray")
        cmd = [FF, "-y", "-v", "error", "-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk", "-ss", f"{t0:.2f}",
               "-t", f"{secs:.2f}", "-i", str(video), "-filter_complex", fc, "-fps_mode", "passthrough", "-f", "rawvideo",
               str(work / f"pic-{name}.gray")]
        say(cmd); subprocess.run(cmd, cwd=work, check=True)
    for label in TAPS:
        (work / f"_tap-{label}.glsl").write_text(tapped((work / "trust5.glsl").read_text(), label))
        fc = (f"[0:v]scale={W}:-2,setpts=N/24/TB,select='not(mod(n\\,2))',setpts=N/12/TB,format=rgb48le,"
              f"libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path=_tap-{label}.glsl,{sel},format=rgb48le")
        cmd = [FF, "-y", "-v", "error", "-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk", "-ss", f"{t0:.2f}",
               "-t", f"{secs:.2f}", "-i", str(video), "-filter_complex", fc, "-fps_mode", "passthrough", "-f", "rawvideo",
               "-pix_fmt", "rgb48le", str(work / f"tap-{label}.rgb48")]
        say(cmd); subprocess.run(cmd, cwd=work, check=True)
    read(work, first, last, lo, hi)


def gray(path, H):
    a = np.fromfile(path, np.uint8)
    return a.reshape(-1, H, W).astype(np.float32) / 255.0


def field(path, H):
    a = np.fromfile(path, np.uint16).reshape(-1, H, W, 3).astype(np.float64) / 65535.0
    return (a[:, 4::8, 4::8, :2] - 0.5) * 2 * FS          # per 1/8 cell (one sample at its centre), px or flag units


def bilinear(img, x, y):
    H = img.shape[0]
    x = np.clip(x, 0, W - 1); y = np.clip(y, 0, H - 1)
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
    x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) + (img[y1, x0] * (1 - fx) + img[y1, x1] * fx) * fy


def block_cost(A, B, cell_y, cell_x, v):
    y0, x0 = 8 * cell_y - 4, 8 * cell_x - 4
    yy, xx = np.mgrid[y0:y0 + 16, x0:x0 + 16].astype(np.float64)
    yy = np.clip(yy, 0, A.shape[0] - 1); xx = np.clip(xx, 0, W - 1)
    a = A[yy.astype(int), xx.astype(int)]
    return float(np.mean(np.abs(a - bilinear(B, xx + v[0], yy + v[1]))))


def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else 10 * np.log10(1.0 / mse)


def read(work, first, last, lo, hi):
    H = int((work / "H").read_text())
    real = gray(work / "real.gray", H)                      # frames first - 1 .. last + 1
    pic = {n: gray(work / f"pic-{n}.gray", H) for n in ("high", "trust5")}
    tap = {l: field(work / f"tap-{l}.rgb48", H) for l in TAPS}
    n = min(len(pic["high"]), len(pic["trust5"]), *(len(t) for t in tap.values()))
    print(f"\n{'k':>4s} {'run':3s} {'high':>6s} {'trust5':>7s} {'d dB':>6s} | {'opened':>6s} {'decided':>7s} | "
          f"{'r_h':>6s} {'m':>7s} {'m/r_h':>6s} {'|b-h|':>6s} | {'diff near decided':>17s}")
    stats = {"run": [], "out": []}
    for i in range(n):
        k = first + i
        if k % 2 == 0 or k - 1 < first - 1 or k + 1 > last + 1:
            continue                                      # odd (interpolated) frames with both real neighbours in hand
        A, B = real[k - 1 - (first - 1)], real[k + 1 - (first - 1)]
        T = real[k - (first - 1)]
        ph, pt = psnr(pic["high"][i], T), psnr(pic["trust5"][i], T)
        op = tap["open"][i]; tg = tap["tg"][i]; tv = tap["tgvec"][i]; qp = tap["qpre"][i]
        opened = (op[..., 0] >= 4.5) & (op[..., 1] < 7.0)
        decided = tg[..., 0] > 5.0
        cells = np.argwhere(decided)
        rh, m, dist = [], [], []
        for cy, cx in cells:
            h = qp[cy, cx]; b = tv[cy, cx]
            c_h = block_cost(A, B, cy, cx, h); c_b = block_cost(A, B, cy, cx, b)
            rh.append(c_h); m.append(c_h - c_b); dist.append(float(np.hypot(*(b - h))))
        diff = np.abs(pic["trust5"][i] - pic["high"][i])
        near = np.zeros_like(diff, dtype=bool)
        for cy, cx in cells:
            near[max(0, 8 * cy - R16):8 * cy + 8 + R16, max(0, 8 * cx - R16):8 * cx + 8 + R16] = True
        share = float(diff[near].sum() / max(diff.sum(), 1e-9)) if cells.size else 0.0
        inrun = lo <= k <= hi
        rec = dict(k=k, dpsnr=pt - ph, opened=opened.mean(), decided=decided.mean(), rh=np.median(rh) if rh else np.nan,
                   m=np.median(m) if m else np.nan, ratio=np.median(np.array(m) / np.maximum(rh, 1e-6)) if rh else np.nan,
                   dist=np.median(dist) if dist else np.nan, share=share)
        stats["run" if inrun else "out"].append(rec)
        print(f"{k:4d} {'RUN' if inrun else '   '} {ph:6.2f} {pt:7.2f} {pt - ph:+6.2f} | {100 * rec['opened']:5.1f}% "
              f"{100 * rec['decided']:6.2f}% | {rec['rh'] * 255:6.2f} {rec['m'] * 255:+7.3f} {rec['ratio']:6.2f} "
              f"{rec['dist']:6.1f} | {100 * share:16.0f}%")
    print("\n(r_h and m in 1/255 units; |b-h| the replacement's size in px; medians over the decided cells of the frame)")
    for grp in ("run", "out"):
        s = stats[grp]
        if not s: continue
        med = lambda key: np.nanmedian([r[key] for r in s])
        print(f"{grp:4s}: frames {len(s)}, median dPSNR {med('dpsnr'):+.2f} dB, opened {100 * med('opened'):.1f}%, decided "
              f"{100 * med('decided'):.2f}%, r_h {255 * med('rh'):.2f}/255, m {255 * med('m'):+.3f}/255, m/r_h {med('ratio'):.2f}, "
              f"diff within 16 px of decided cells {100 * med('share'):.0f}%")
    s = stats["run"]
    if s:
        med = lambda key: np.nanmedian([r[key] for r in s])
        verdict = "between the rules: reported, decides nothing"
        if med("share") < 0.30 or (med("decided") < 0.002 and med("dpsnr") < -2.0):
            verdict = "(iii) NOT THE GATE'S DECISIONS: look downstream (adoption, lattice, cut gate)"
        elif med("ratio") < 0.5 and med("rh") > 2 / 255 and med("share") > 0.5:
            verdict = "(i) NOISE-FLOOR DECISION: repair with TG_PICK scaled by the block's residual (proposal 4b)"
        elif med("ratio") > 1.0:
            verdict = "(ii) THE OFFER'S FAULT: retire the gate as a tier, keep the switch"
        print(f"\nverdict on the run: {verdict}")


def span(s, d):
    a, b = (s or d).split(":"); return int(a), int(b)


if __name__ == "__main__":
    mode = sys.argv[1]
    work = pathlib.Path(sys.argv[2])
    if mode == "build":
        build(work)
    elif mode == "run":
        first, last = span(sys.argv[5] if len(sys.argv) > 5 else "", "800:840")
        lo, hi = span(sys.argv[6] if len(sys.argv) > 6 else "", "815:833")
        run(work, pathlib.Path(sys.argv[3]), float(sys.argv[4]), first, last, lo, hi)
    elif mode == "read":
        first, last = span(sys.argv[3] if len(sys.argv) > 3 else "", "800:840")
        lo, hi = span(sys.argv[4] if len(sys.argv) > 4 else "", "815:833")
        read(work, first, last, lo, hi)
    else:
        sys.exit(__doc__)
