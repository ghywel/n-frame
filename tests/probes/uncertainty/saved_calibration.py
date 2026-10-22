#!/usr/bin/env python3
"""Test a residual-to-r68 multiplier on the already rendered sext diagnostics.

RUN-ON: cpu (reads completed synthetic data only; never invokes ffmpeg)
COMMAND: python3 tests/probes/uncertainty/saved_calibration.py DATA --out RESULT.json
PREDICTION: CHAT-LEDGER G004, frozen before reading/fitting the samples.
TRAIN: M2c_period40_v10, A4_accel_tex_a033, O6_osc_tex_gentle.
HOLDOUT: O5_osc_textured, O9_osc_tex_fast, O10_osc_tex_tiny.
REFUTED-BY: any held-out case's coverage outside [0.63,0.73], using one
training multiplier and no held-out refit. This rejects that transfer claim,
not the existing residual/error ranking. No cross-texture validation here.
COST: one memory-mapped read of existing data, no GPU.

Uses the existing scorer for raw layout, split decoding and scene laws. The
true-pixel residual is mode 11 GREEN (legacy red has the old unit error).
Samples all interior states before filtering, so refusals stay visible.
The constant-radius baseline and shuffle within each frame's eligible mask
share the same held-out samples. No independent-texel confidence interval is
claimed. Output 0: gate survives; 3: transfer hypothesis refuted; 1: instrument
or input failure. All results are written before a science rejection exit.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TRAIN = ("M2c_period40_v10", "A4_accel_tex_a033", "O6_osc_tex_gentle")
HOLDOUT = ("O5_osc_textured", "O9_osc_tex_fast", "O10_osc_tex_tiny")


def load_reader():
    spec = importlib.util.spec_from_file_location("existing_sext_reader", HERE / "sext_resid.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank_correlation(a, b):
    def ranks(v):
        _, inverse, counts = np.unique(v, return_inverse=True, return_counts=True)
        ends = np.cumsum(counts)
        return ((ends - counts + ends - 1) * 0.5)[inverse]
    x, y = ranks(a), ranks(b)
    x -= x.mean()
    y -= y.mean()
    den = np.linalg.norm(x) * np.linalg.norm(y)
    return float(x @ y / den) if den > 0 else None


def inputs(data):
    provenance = {}
    for mode in (10, 11, 12):
        path = data / "glsl" / f"m{mode}.glsl"
        code = path.read_text()
        if f"const int TRI_DIAG = {mode};" not in code:
            raise ValueError(f"wrong saved mode: {path}")
        for token in ["float u0 = -tc;", "resid_true_q = sqrt(num_q / max(den, 1.0e-6))",
                      "clamp(resid_true_q / 64.0", "vq * 0.25 - wq"]:
            if token not in code:
                raise ValueError(f"unrecognized saved diagnostic: {path}: missing {token!r}")
        provenance[f"m{mode}_shader_sha256"] = sha(path)
    return provenance


def read_case(reader, data, case, rng, count):
    paths = [data / case / f"m{m}.raw" for m in (10, 11, 12)]
    states = [(p.stat().st_size, p.stat().st_mtime_ns) for p in paths]
    raw = [reader.frames(p) for p in paths]
    nf = [len(a) for a in raw]
    if nf != [60, 60, 60]:
        raise ValueError(f"{case}: expected three complete 60-frame files, got {nf}")
    for mode in (10, 11, 12):
        err = (data / case / f"m{mode}.err").read_text()
        if re.search(r"compile status.*error|disabling|failed executing", err, flags=re.I):
            raise ValueError(f"{case} m{mode}: diagnostic did not run")
    x0, y0, bw, bh, expression = reader.scene_law(case)
    yy = (np.arange(reader.CROP_H) + reader.CROP_Y + 0.5)[:, None]
    xx = (np.arange(reader.W) + 0.5)[None, :]
    error, residual, shuffled, vx, vy, links, fitted = [], [], [], [], [], [], []
    frame_id, pixel_id, far_zero = [], [], []
    fwd_vx, fwd_vy = [], []
    pack_max, flag_max = 0.0, 0.0
    align_error = {d: [] for d in (-1, 0, 1)}
    for n in range(reader.SKIP, 60):
        t = n / 24.0
        left = x0(t)
        mask = ((xx > left + reader.EDGE) & (xx < left + bw - reader.EDGE)
                & (yy > y0 + reader.EDGE) & (yy < y0 + bh - reader.EDGE))
        available = np.flatnonzero(mask)
        ids = rng.choice(available, min(count, available.size), replace=False)
        if ids.size == 0:
            raise ValueError(f"{case} frame {n}: empty interior")
        y, x = ids // reader.W, ids % reader.W
        velocity_raw = raw[0].a[n, y, x].astype(float) / 65535.0
        info = raw[1].a[n, y, x].astype(float) / 65535.0
        fwd_raw = raw[2].a[n, y, x].astype(float) / 65535.0
        velocity, clipped = reader.split_v(velocity_raw)
        forward, fwd_clipped = reader.split_v(fwd_raw)
        if np.any(clipped) or np.any(fwd_clipped):
            raise ValueError(f"{case} frame {n}: clipped split velocity")
        pack = velocity_raw[:, 2] * 1024
        pack_max = max(pack_max, float(np.max(np.abs(pack - np.rint(pack)))))
        fl = info[:, 2] * 16
        flag_max = max(flag_max, float(np.max(np.abs(fl - np.rint(fl)))))
        flag = np.rint(fl).astype(int)
        fit, nl = flag >= 8, flag % 8
        if np.any(flag < 0) or np.any(flag > 13) or np.any(nl > 5) or np.any(fit & (nl < 4)):
            raise ValueError(f"{case}: impossible number of links")
        rho = info[:, 1] * 64
        truth = (x0(t + 1e-6) - x0(t - 1e-6)) / (2e-6 * 24)
        e = np.linalg.norm(velocity - [truth, 0], axis=1)
        eligible = fit & (nl == 5) & (rho > 0)
        rp = rho.copy()
        rp[eligible] = rng.permutation(rho[eligible])  # preserves case, frame and accepted fit state
        for offset in (-1, 0, 1):
            tt = t + offset / 24.0
            tv = (x0(tt + 1e-6) - x0(tt - 1e-6)) / (2e-6 * 24)
            if np.any(eligible):
                align_error[offset].append(float(np.median(np.linalg.norm(velocity[eligible] - [tv, 0], axis=1))))
        # Fixed far-background points at the top of the crop, away from the marker.
        bg = raw[0].a[n, 0, 32::16].astype(float) / 65535.0
        bg_v, bg_clip = reader.split_v(bg)
        if np.any(bg_clip):
            raise ValueError(f"{case}: clipped background read")
        far_zero.append(np.linalg.norm(bg_v, axis=1))
        for target, values in [(error, e), (residual, rho), (shuffled, rp),
                               (vx, velocity[:, 0]), (vy, velocity[:, 1]),
                               (fwd_vx, forward[:, 0]), (fwd_vy, forward[:, 1]),
                               (links, nl), (fitted, fit),
                               (frame_id, np.full(len(ids), n)), (pixel_id, ids)]:
            target.append(values)
    arrays = {k: np.concatenate(v) for k, v in [
        ("error", error), ("residual", residual), ("shuffled", shuffled),
        ("vx", vx), ("vy", vy), ("links", links), ("fitted", fitted),
        ("frame", frame_id), ("pixel", pixel_id)]}
    fit = arrays["fitted"]
    bg = np.concatenate(far_zero)
    instrument = {
        "frames": nf, "scene_law": expression, "packing_worst": pack_max,
        "flag_rounding_worst": flag_max, "background_velocity_median": float(np.median(bg)),
        "background_velocity_max": float(np.max(bg)),
        "alignment_median_errors_at_anchor_offsets": {str(k): float(np.median(v)) for k, v in align_error.items()},
    }
    if case.startswith("M2c"):
        speed = (x0(1.0) - x0(0.0)) / 24.0
        instrument["translation_fit_vx_vy"] = [float(np.median(arrays["vx"][fit])), float(np.median(arrays["vy"][fit]))]
        instrument["translation_fwd_vx_vy"] = [float(np.median(np.concatenate(fwd_vx)[fit])), float(np.median(np.concatenate(fwd_vy)[fit]))]
        for key in ("translation_fit_vx_vy", "translation_fwd_vx_vy"):
            if np.max(np.abs(np.array(instrument[key]) - [speed, 0])) > 0.01:
                raise ValueError(f"translation calibration failed: {instrument}")
    if pack_max >= 0.05 or flag_max >= 0.01 or np.median(bg) >= 0.001:
        raise ValueError(f"{case}: read-path check failed: {instrument}")
    if not all(np.all(np.isfinite(v)) for v in arrays.values()):
        raise ValueError(f"{case}: nonfinite sample")
    if states != [(p.stat().st_size, p.stat().st_mtime_ns) for p in paths]:
        raise ValueError(f"{case}: inputs changed during read")
    instrument["input_sizes_bytes"] = [s[0] for s in states]
    instrument["input_mtime_ns"] = [s[1] for s in states]
    return arrays, instrument


def summarize(a, k, constant):
    e, r, fit, links = (a[key] for key in ("error", "residual", "fitted", "links"))
    eligible = fit & (links == 5) & (r > 0)
    e1, r1, rp = e[eligible], r[eligible], a["shuffled"][eligible]
    gross, excluded = e > 2, ~eligible
    if e1.size == 0:
        raise ValueError("no eligible overdetermined points")
    return {
        "sampled_interior": int(len(e)), "eligible": int(eligible.sum()),
        "no_fit": int((~fit).sum()), "exact_fit": int((fit & (links == 4)).sum()),
        "five_link_zero_residual": int((fit & (links == 5) & (r <= 0)).sum()),
        "eligible_fraction": float(eligible.mean()),
        "total_gross": int(gross.sum()), "excluded_gross": int((gross & excluded).sum()),
        "eligible_gross": int((gross & eligible).sum()),
        "no_fit_gross": int((gross & ~fit).sum()),
        "exact_fit_gross": int((gross & fit & (links == 4)).sum()),
        "five_link_zero_residual_gross": int((gross & fit & (links == 5) & (r <= 0)).sum()),
        "eligible_error_median": float(np.median(e1)),
        "eligible_error_p90": float(np.quantile(e1, 0.9)),
        "eligible_residual_median": float(np.median(r1)),
        "case_k68_diagnostic_only": float(np.quantile(e1 / r1, 0.68)),
        "frozen_multiplier_coverage": float(np.mean(e1 <= k * r1)),
        "frozen_constant_radius_coverage": float(np.mean(e1 <= constant)),
        "within_frame_shuffled_multiplier_coverage": float(np.mean(e1 <= k * rp)),
        "frozen_multiplier_q95_normalized_error": float(np.quantile(e1 / (k * r1), 0.95)),
        "texel_rank_correlation": rank_correlation(r1, e1),
        "within_frame_shuffle_rank_correlation": rank_correlation(rp, e1),
    }


def short_input_control(data, work):
    """The full CLI must refuse a truncated file before writing science."""
    with tempfile.TemporaryDirectory(prefix="short-input-", dir=work) as temp:
        root = Path(temp)
        (root / "glsl").symlink_to((data / "glsl").resolve(), target_is_directory=True)
        case = TRAIN[0]
        (root / case).mkdir()
        with (root / case / "m10.raw").open("wb") as stream:
            stream.truncate(1280 * 400 * 3 * 2)  # one frame, expected sixty
        for mode in (11, 12):
            (root / case / f"m{mode}.raw").symlink_to((data / case / f"m{mode}.raw").resolve())
        output = root / "must-not-exist.json"
        run = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(root),
                              "--out", str(output)], capture_output=True, text=True)
        passed = (run.returncode == 1 and not output.exists()
                  and "expected three complete 60-frame files, got [1, 60, 60]" in run.stderr)
        if not passed:
            raise ValueError(f"short-input counterfactual failed: {run.returncode}, {run.stderr}")
        return {"short_input_control_passed": True, "child_exit_code": run.returncode,
                "science_output_written": output.exists(), "observed_frame_counts": [1, 60, 60]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples-per-frame", type=int, default=4096)
    parser.add_argument("--check-short-input", action="store_true",
                        help="run the truncated-input counterfactual only; no calibration")
    args = parser.parse_args()
    if args.check_short_input:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        result = short_input_control(args.data, args.out.parent)
        text = json.dumps(result, indent=2) + "\n"
        args.out.write_text(text)
        print(text, end="")
        return
    if args.samples_per_frame < 128:
        raise ValueError("at least 128 requested samples per frame")
    reader = load_reader()
    provenance = inputs(args.data)
    rng = np.random.default_rng(20261023)
    cases, instrument = {}, {}
    for case in TRAIN + HOLDOUT:
        cases[case], instrument[case] = read_case(reader, args.data, case, rng, args.samples_per_frame)
        print(f"read {case}: {len(cases[case]['error'])} interior samples", flush=True)
    # Freeze both calibrations on the declared training cases only.
    train_error, train_ratio = [], []
    for case in TRAIN:
        a = cases[case]
        eligible = a["fitted"] & (a["links"] == 5) & (a["residual"] > 0)
        train_error.append(a["error"][eligible])
        train_ratio.append(a["error"][eligible] / a["residual"][eligible])
    k = float(np.quantile(np.concatenate(train_ratio), 0.68))
    constant = float(np.quantile(np.concatenate(train_error), 0.68))
    summaries = {case: summarize(a, k, constant) for case, a in cases.items()}
    gate = all(0.63 <= summaries[c]["frozen_multiplier_coverage"] <= 0.73 for c in HOLDOUT)
    result = {
        "instrument_passed": True, "hypothesis_gate": "SURVIVES" if gate else "REFUTED",
        "seed": 20261023, "samples_per_frame": args.samples_per_frame,
        "training_cases": TRAIN, "heldout_cases": HOLDOUT,
        "frozen_k68": k, "frozen_constant_r68": constant,
        "gate_coverage_range": [0.63, 0.73], "cases": summaries,
        "instrument": instrument, "provenance": provenance,
        "scorer_sha256": sha(HERE / "sext_resid.py"),
        "scene_file_sha256": sha(reader.REPO / "tests/scenes.sh"),
        "limitations": "same existing texture and capture path; motion-regime holdout; no independent-texel CI; eligible points only",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"frozen k68={k:.6f}; constant r68={constant:.6f}")
    for case, s in summaries.items():
        split = "TRAIN" if case in TRAIN else "HELDOUT"
        print(f"{split:7} {case:24} eligible {s['eligible_fraction']:.4%} "
              f"coverage {s['frozen_multiplier_coverage']:.4%} "
              f"constant {s['frozen_constant_radius_coverage']:.4%} "
              f"case k {s['case_k68_diagnostic_only']:.4f} "
              f"gross {s['total_gross']} excluded {s['excluded_gross']}")
    print(f"ONE-FACTOR TRANSFER: {result['hypothesis_gate']}")
    raise SystemExit(0 if gate else 3)


if __name__ == "__main__":
    main()
