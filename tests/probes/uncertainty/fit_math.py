#!/usr/bin/env python3
"""Fixed-fit uncertainty algebra and adversarial controls; no GPU, no footage.

RUN-ON: cpu
COMMAND: python3 tests/probes/uncertainty/fit_math.py [--out PATH] [--samples 200000]
PREDICTION: MATHS.md and CHAT-LEDGER G003, written before the first run.
REFUTED-BY: any named control fails; the result is not a shader calibration.
COST: one small seeded NumPy Monte Carlo, usually seconds.

This models the six actual points of an interior N:N sext window, including
the exact anchor. The seventh shader-array entry has zero weight (it would
need a seventh frame). A stable float64 least-squares solve verifies the
equations; this does not simulate texture sampling, fp16, branch selection,
or the shader's float32 Gaussian elimination. Those need separate gates.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np


def basis(t, order=0):
    """Rows for the order-th derivative of [1,u,u^2/2,u^3/6,u^4/24]."""
    t = np.asarray(t, dtype=np.float64)
    return np.stack([
        np.zeros_like(t) if j < order else t ** (j - order) / math.factorial(j - order)
        for j in range(5)
    ], axis=-1)


def fit_operator(tau, weights, origin=None):
    """Match the source's centroid calculation, then its strict >0.05 fit mask."""
    tau, weights = np.asarray(tau, dtype=float), np.asarray(weights, dtype=float)
    tc = float(weights @ tau / weights.sum()) if origin is None else float(origin)
    active = weights > 0.05
    t, w = tau[active], weights[active]
    x = basis(t - tc)
    if np.linalg.matrix_rank(x) != 5:
        raise ValueError("five independent polynomial coefficients are required")
    root = np.sqrt(w)
    a = np.linalg.pinv(x * root[:, None]) * root[None, :]
    r = np.eye(len(t)) - x @ a
    return tc, active, x, a, r, w


def source_contract():
    src = Path(__file__).resolve().parents[2] / "gen_sextdirectional.py"
    text = src.read_text()
    for token in ["float A[25]", "float bb[5]", "if (w7[k] <= 0.05) continue;",
                  "tc += w7[k] * tau7[k]", "tc /= max(sw, 1.0e-6)",
                  "tau7[6] = 0.0; d7[6] = vec2(0.0)"]:
        if token not in text:
            raise ValueError(f"source contract changed: missing {token!r}; re-audit the maths")


def run(samples):
    if samples < 10000:
        raise ValueError("at least 10000 samples are needed for the fixed Monte Carlo tolerances")
    source_contract()
    rng = np.random.default_rng(20261022)
    tau = np.arange(-3.0, 3.0)
    weights = np.ones(6)
    tc, active, x, a, r, w = fit_operator(tau, weights)
    checks, details = {}, {}

    # Independent control: the normal-equation expression vs the SVD solve.
    normal = np.linalg.solve(x.T @ (w[:, None] * x), x.T * w)
    diff = float(np.max(np.abs(normal - a)))
    checks["normal_equations_match_stable_reference"] = diff < 1e-10
    details["normal_equations_max_difference"] = diff

    # Any polynomial error in the model's column space is invisible to R.
    # e(tau)=tau also respects the anchor's zero displacement exactly.
    velocity_at_anchor = basis(np.array(-tc), 1) @ a
    base = basis(tau) @ np.array([0.0, 2.0, 0.3, -0.02, 0.001])
    before, after = r @ base, r @ (base + tau)
    nullerr = float(np.max(np.abs(after - before)))
    shift = float(velocity_at_anchor @ tau)
    checks["coherent_wrong_velocity_is_residual_invisible"] = nullerr < 1e-10 and abs(shift - 1) < 1e-10
    details["coherent_error"] = {"residual_change_max": nullerr, "velocity_shift": shift}

    # Primitive errors are OUTWARD, in order -1,-2,-3,+1,+2. At a uniform
    # translation, all composition Jacobians are identity, so shared links add.
    b = np.array([[1, 1, 1, 0, 0], [1, 1, 0, 0, 0], [1, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0], [0, 0, 0, 1, 0], [0, 0, 0, 1, 1]], dtype=float)
    # An illustrative correlated input model; not fitted to real shader dumps.
    s, rho = 0.15, 0.35
    primitive_cov = s * s * ((1 - rho) * np.eye(5) + rho * np.ones((5, 5)))
    sigma = b @ primitive_cov @ b.T
    h = np.stack([basis(np.array(t - tc), k) @ a for t in [0.0, tc] for k in [1, 2, 3]])
    predicted = np.diag(h @ sigma @ h.T)
    primitive = rng.standard_normal((samples, 5)) @ np.linalg.cholesky(primitive_cov).T
    errors = primitive @ b.T
    empirical = np.var(errors @ h.T, axis=0, ddof=1)
    rel = np.abs(empirical / predicted - 1)
    checks["shared_link_covariance_matches_monte_carlo"] = bool(np.max(rel) < 0.05)
    diagonal = np.diag(h @ np.diag(np.diag(sigma)) @ h.T)
    wrong = np.abs(diagonal / predicted - 1)
    checks["diagonal_covariance_counterfactual_is_rejected"] = bool(np.max(wrong) > 0.05)
    details["covariance"] = {
        "query_order": ["anchor v", "anchor a", "anchor j", "centre v", "centre a", "centre j"],
        "primitive_sigma": s, "primitive_equicorrelation": rho,
        "predicted_variance": predicted.tolist(), "monte_carlo_variance": empirical.tolist(),
        "max_relative_monte_carlo_error": float(np.max(rel)),
        "diagonal_over_correct_variance": (diagonal / predicted).tolist(),
        "anchor_input_variance": float(sigma[3, 3]),
    }

    q = r.T @ (w[:, None] * r)
    expected_sse = float(np.trace(q @ sigma))
    residuals = errors @ r.T
    measured_sse = float(np.mean(np.sum(w * residuals * residuals, axis=1)))
    checks["residual_trace_matches_monte_carlo"] = abs(measured_sse / expected_sse - 1) < 0.05
    richer = sigma + np.outer(tau, tau)
    hidden_sse = float(np.trace(q @ richer))
    extra_variance = float(velocity_at_anchor @ (richer - sigma) @ velocity_at_anchor)
    checks["residual_does_not_identify_derivative_covariance"] = (
        abs(hidden_sse - expected_sse) < 1e-10 and abs(extra_variance - 1.0) < 1e-10)
    details["residual"] = {
        "rank": int(np.count_nonzero(np.linalg.svd(r, compute_uv=False) > 1e-10)),
        "expected_sse_one_axis": expected_sse, "measured_sse_one_axis": measured_sse,
        "expected_shader_residual_squared_two_axes": 2 * expected_sse / w.sum(),
        "hidden_covariance_sse_change": hidden_sse - expected_sse,
        "hidden_covariance_velocity_variance_increase": extra_variance,
    }

    drop = weights.copy()
    drop[0] = 0
    _, _, _, _, r4, _ = fit_operator(tau, drop)
    checks["four_links_have_no_residual_dimension"] = np.linalg.norm(r4) < 1e-10

    asymmetric = np.array([1, 1, 1, 1, 1, 0.2])
    tca, maska, xa, aa, ra, wa = fit_operator(tau, asymmetric)
    _, _, _, a0, _, _ = fit_operator(tau, asymmetric, origin=0)
    delta = float(np.max(np.abs(basis(np.array(-tca), 1) @ aa - basis(np.array(0), 1) @ a0)))
    checks["recentring_preserves_anchor_velocity"] = delta < 1e-10
    quintic = tau ** 5 / math.factorial(5)
    acc_bias_sym = float(basis(np.array(0), 2) @ a @ quintic - tc ** 3 / 6)
    acc_bias_asym = float(basis(np.array(0), 2) @ aa @ quintic - tca ** 3 / 6)
    mu3 = float(wa @ (tau[maska] - tca) ** 3)
    checks["weighted_centroid_is_not_a_symmetric_stencil"] = (
        abs(mu3) > 0.01 and abs(acc_bias_sym) < 1e-10 and abs(acc_bias_asym) > 0.001)
    low = weights.copy()
    low[0] = 0.03
    tclow, masklow, _, _, _, wlow = fit_operator(tau, low)
    details["time"] = {
        "symmetric_centre": tc, "asymmetric_centre": tca,
        "same_time_velocity_operator_difference": delta,
        "asymmetric_third_central_moment": mu3,
        "quintic_acceleration_bias_symmetric": acc_bias_sym,
        "quintic_acceleration_bias_asymmetric": acc_bias_asym,
        "low_weight_centre_including_excluded_point": tclow,
        "active_points_centre": float(wlow @ tau[masklow] / wlow.sum()),
    }

    gaussian = rng.standard_normal((samples, 2))
    radius = np.linalg.norm(gaussian, axis=1)
    r68, r95 = math.sqrt(-2 * math.log(0.32)), math.sqrt(-2 * math.log(0.05))
    coverage = float(np.mean(radius <= r68))
    wrong_coverage = float(np.mean(radius <= 1))
    checks["radial_coverage_is_not_per_axis_sigma"] = abs(coverage - 0.68) < 0.01 and wrong_coverage < 0.42
    # Independent scale estimate with two residual degrees of freedom.
    # (||Gaussian_2||^2/2)/(ChiSquare_2/2) has F(2,2) law, CDF x/(1+x).
    scale = np.sqrt(np.sum(rng.standard_normal((samples, 2)) ** 2, axis=1) / 2)
    studentized = radius / scale
    expected_t_ratio = math.sqrt((0.95 / 0.05) / (0.68 / 0.32))
    empirical_t_ratio = float(np.quantile(studentized, 0.95) / np.quantile(studentized, 0.68))
    checks["two_dof_scale_can_fail_design_tail_limit_when_model_is_correct"] = (
        abs(empirical_t_ratio / expected_t_ratio - 1) < 0.05 and empirical_t_ratio > 2.6)
    details["coverage"] = {
        "known_scale_r68_over_axis_sigma": r68, "known_scale_r95_over_axis_sigma": r95,
        "known_scale_r95_over_r68": r95 / r68, "empirical_r68_coverage": coverage,
        "empirical_one_axis_sigma_circle_coverage": wrong_coverage,
        "two_dof_scale_expected_r95_over_r68": expected_t_ratio,
        "two_dof_scale_empirical_r95_over_r68": empirical_t_ratio,
    }
    # With ten bins, rank noise remains even if every bin contains a million
    # shuffled texels. Increasing texels does not increase the number of ranks.
    ranks = np.arange(10.0) - 4.5
    shuffled = np.stack([rng.permutation(ranks) for _ in range(10000)])
    bin_correlations = shuffled @ ranks / (ranks @ ranks)
    null_sd = float(np.std(bin_correlations, ddof=1))
    false_reject = float(np.mean(np.abs(bin_correlations) >= 0.2))
    one_sided_false_reject = float(np.mean(bin_correlations >= 0.2))
    checks["ten_bin_shuffle_needs_a_null_distribution"] = abs(null_sd - 1 / 3) < 0.01 and false_reject > 0.4
    details["ten_bin_shuffle"] = {
        "permutations": 10000, "expected_null_standard_deviation": 1 / 3,
        "empirical_null_standard_deviation": null_sd,
        "false_rejection_rate_at_absolute_rho_0_2": false_reject,
        "false_rejection_rate_at_signed_rho_0_2": one_sided_false_reject,
    }
    checks = {name: bool(value) for name, value in checks.items()}
    return {"seed": 20261022, "samples": samples, "checks": checks, "details": details,
            "passed": sum(checks.values()), "total": len(checks), "all_passed": all(checks.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--samples", type=int, default=200000)
    args = parser.parse_args()
    result = run(args.samples)
    output = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output)
    print(output, end="")
    if not result["all_passed"]:
        raise SystemExit("FAIL: " + ", ".join(k for k, v in result["checks"].items() if not v))


if __name__ == "__main__":
    main()
