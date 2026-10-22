#!/usr/bin/env python3
"""CPU audit of BAR_REDECIDE and the fixed-lattice comb; see BAR-REVIEW.md.

RUN-ON: cpu
COMMAND: python3 tests/probes/cage/bar_review.py --out "$NP_SCRATCH/bar-review/results.json"
PREDICTION: registered in CHAT-LEDGER G006 before this run. Correct seeds +6/-6 on
period-9 bars become -3/+3 (within .2 px); +3 is kept. Integer-time movies agree,
half-time movies differ. Direct sampling and the derived response agree to 1e-10;
deliberately wrong phase fails. Marker strength is descriptive, not a fitted gate.
REFUTED-BY: any failed named check. No GPU regression or full shader emulation claimed.
COST: one short CPU run, numpy only. Data goes outside the repository.

The scalar choice below follows tests/bar_redecide.py, including its half-pixel
tie tolerance, parabola and switch threshold. Axis-aligned, y-invariant texture
makes its 7x7 SAD exactly a seven-tap SAD, and its tensor normal exactly (1,0).
Actual shader constants are imported; source SHA256 is recorded. Other stages,
GPU rounding, colour conversion, finite windows and cache behaviour are absent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

TESTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TESTS))
import bar_redecide as bar


def signal(x, marker=0.0):
    return 0.5 + 0.25 * np.cos(2 * np.pi * x / 9) + marker * np.tanh(x / 4)


def pixel_fetch(x, displacement, marker=0.0):
    """B at integer pixel centres, reconstructed linearly, like an axis-aligned tap."""
    lo = np.floor(x)
    a = x - lo
    return (1-a) * signal(lo-displacement, marker) + a * signal(lo+1-displacement, marker)


def decide(speed, seed, marker=0.0):
    taps = np.arange(-3, 4) * 2.0
    costs = np.array([np.mean(np.abs(signal(taps, marker) -
                        pixel_fetch(taps+seed+s, speed, marker)))
                      for s in range(-bar.BAR_REACH, bar.BAR_REACH+1)])
    tie = costs.min() * (1+bar.BAR_TIE_REL) + bar.BAR_TIE_ABS
    best, best_mag = -1, 1e30
    for i in range(1, 2*bar.BAR_REACH):
        if costs[i] > costs[i-1] or costs[i] > costs[i+1] or costs[i] > tie:
            continue
        mag = abs(seed+i-bar.BAR_REACH)
        if mag < best_mag-.5 or (mag < best_mag+.5 and best >= 0 and
                                abs(i-bar.BAR_REACH) < abs(best-bar.BAR_REACH)):
            best_mag, best = min(mag, best_mag), i
    offset = 0.0
    if best >= 0:
        den = costs[best-1]-2*costs[best]+costs[best+1]
        sub = np.clip(.5*(costs[best-1]-costs[best+1])/den, -.5, .5) if den > 1e-9 else 0
        offset = float(best-bar.BAR_REACH+sub)
    chosen = seed+offset if abs(offset) > bar.BAR_SWITCH else seed
    # Half-res central differences: neighbouring half-res samples two source pixels apart.
    u = np.arange(-2, 3)*2.0
    gx = .5*(signal(u+2, marker)-signal(u-2, marker))
    rms = float(np.sqrt(np.mean(gx*gx)))
    active = rms >= bar.BAR_MIN_GRAD
    return {"speed": speed, "seed": seed, "marker": marker,
            "chosen": float(chosen if active else seed), "tensor_active": bool(active),
            "tensor_rms": rms, "tensor_eigenvalue_ratio": 0.0,
            "costs": costs.tolist(), "tie": float(tie)}


def response(k, pitch, displacement, wrong_sign=False):
    alpha = (displacement/pitch) % 1
    return np.exp((1j if wrong_sign else -1j)*k*alpha*pitch) * (
        1-alpha+alpha*np.exp(1j*k*pitch))


def run():
    checks = {}
    def check(name, value):
        checks[name] = bool(value)
    trials = [decide(v, v) for v in (6, -6, 3)]
    check("fast_positive_seed_destroyed", abs(trials[0]["chosen"]+3) < .2)
    check("fast_negative_seed_destroyed", abs(trials[1]["chosen"]-3) < .2)
    check("slow_positive_seed_preserved", trials[2]["chosen"] == 3)
    check("tensor_gate_fires", all(t["tensor_active"] for t in trials))
    x = np.arange(-64, 65, dtype=float)
    integer_error = max(float(np.max(abs(signal(x-6*t)-signal(x+3*t)))) for t in range(8))
    half_error = float(np.max(abs(signal(x-3)-signal(x+1.5))))
    check("integer_movies_identical", integer_error < 1e-12)
    check("half_frame_counterfactual_detected", half_error > .4)
    marker_trials = [decide(6, 6, m) for m in (0, .002, .01, .05, .15)]
    # Independent sampler vs closed form across signs, fractional phases and frequencies.
    rng = np.random.default_rng(20261022)
    max_error, wrong_error = 0.0, 0.0
    for _ in range(256):
        k, d = rng.uniform(-np.pi, np.pi), rng.uniform(-25, 25)
        s = int(rng.choice([8, 16]))
        j = np.arange(-5, 6)
        q = np.floor((j*s+d)/s)
        a = (j*s+d)/s-q
        b = (1-a)*np.exp(1j*k*(q*s-d)) + a*np.exp(1j*k*((q+1)*s-d))
        direct = b / np.exp(1j*k*j*s)
        max_error = max(max_error, float(np.max(abs(direct-response(k, s, d)))))
        wrong_error = max(wrong_error, float(np.max(abs(direct-response(k, s, d, True)))))
    check("response_matches_direct_sampler", max_error < 1e-10)
    check("wrong_phase_sign_rejected", wrong_error > .1)
    comb = [{"pitch": s, "speed": d,
             "unit_complex_squared_error": float(abs(response(2*np.pi/9, s, d)-1)**2)}
            for s in (8, 16) for d in (8, 10, 12, 16)]
    check("both_grids_exact_at_16", all(t["unit_complex_squared_error"] < 1e-20
                                       for t in comb if t["speed"] == 16))
    check("both_grids_biased_at_10_and_12", all(t["unit_complex_squared_error"] > .01
                                               for t in comb if t["speed"] in (10, 12)))
    # 2D reciprocal lattice: an instantaneous translated fundamental, not the full C3 signal.
    alias_rows, lattice_error = [], 0.0
    for theta in (0.0, .15, .30):
        normal = np.array([np.cos(theta), np.sin(theta)])
        k = normal/9
        for s in (8, 16):
            m = np.rint(s*k)
            ka = k-m/s
            normal_flow = (1/9)*ka/np.dot(ka, ka)  # true across speed = 1
            grid = rng.integers(-5, 6, (64, 2))*s
            # include time: temporal frequency remains k.v, not ka.v
            t = .37
            lattice_error = max(lattice_error, float(np.max(abs(
                np.exp(2j*np.pi*(grid@k-t/9)) - np.exp(2j*np.pi*(grid@ka-t/9))))))
            alias_rows.append({"theta": theta, "pitch": s, "reciprocal_index": m.tolist(),
                               "alias_frequency": ka.tolist(),
                               "least_norm_across_ratio": float(normal_flow@normal)})
    check("two_dimensional_alias_samples_identical", lattice_error < 1e-12)
    check("axis_aligned_ratio_minus_8", abs(alias_rows[0]["least_norm_across_ratio"]+8) < 1e-12)
    check("rotation_changes_least_norm_ratio", abs(alias_rows[-1]["least_norm_across_ratio"]+8) > 1)
    old, new, oracle = 23.43, 27.30, 36.47
    db_fraction = (new-old)/(oracle-old)
    # These are equivalent errors from SUMMARY dB values, NOT pooled measured MSE.
    eq = lambda db: 10**(-db/10)
    equivalent_fraction = (eq(old)-eq(new))/(eq(old)-eq(oracle))
    return {"checks": checks, "passed": sum(checks.values()), "total": len(checks),
            "bar_source_sha256": hashlib.sha256(Path(bar.__file__).read_bytes()).hexdigest(),
            "trials": trials, "marker_trials": marker_trials,
            "integer_movie_max_difference": integer_error, "half_movie_max_difference": half_error,
            "response_max_difference": max_error, "wrong_phase_max_difference": wrong_error,
            "comb": comb, "alias_rows": alias_rows, "lattice_max_difference": lattice_error,
            "summary_db_gap_fraction": db_fraction,
            "summary_equivalent_error_gap_fraction_not_pooled_mse": equivalent_fraction}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    result = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: result[k] for k in ("checks", "passed", "total")}, indent=2))
    raise SystemExit(0 if all(result["checks"].values()) else 1)
