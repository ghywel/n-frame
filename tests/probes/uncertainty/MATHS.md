# Uncertainty calibration: the quantity, the covariance, and what a residual cannot see

2026-10-22, GPT, following CHAT-LEDGER G003 and Local L002. **CPU mathematical audit; no shader changes.**
The existing residual/error ranking is not retracted. This asks what additional assumptions would turn it into an
error bar, and what that error bar would mean. Sources, proofs, numerical controls and observations are distinguished.

## Predictions before running the controls

G003 pre-registers the nullspace, covariance, recentering and radial Gaussian checks. Additional check registered here
before execution: in an ideal Gaussian regression with one residual degree of freedom **per image axis**, estimating
the common noise scale from those two residuals gives a bivariate t reference with two scale degrees of freedom.
Its radial 95th/68th percentile ratio is about 2.99, exceeding the design's proposed 2.6 upper limit even with a correct
model. A seeded Monte Carlo must agree within 5 percent. This is a control distribution, not an assertion that the
shader follows it. Failure of any control is reported before adopting the accompanying conclusion.

Additional control registered after the first eleven passed, before its execution: the rank correlation of ten
exchangeable, shuffled decile medians has null standard deviation 1/3, irrespective of how many texels formed those
medians (assuming no ties). Ten thousand random rank permutations must reproduce this within 0.01. A hard absolute
correlation limit of 0.2 must falsely reject more than 40 percent of these legitimate shuffled controls. This tests
the proposed counterfactual's interpretation, not the existing non-shuffled ranking result.

Command, from the repository root, with a NumPy Python:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/uncertainty/fit_math.py --out "$NP_SCRATCH/uncertainty/maths.json"
```

## Result of block 1

**The residual is a useful ranking cue, but it does not identify derivative uncertainty.** There are coherent
trajectory errors that it cannot see. A calibrated covariance needs an error model or independent truth; multiplying
the residual by one constant is a candidate to test, not an error-propagation theorem.

Measured, CPU float64 controls, 2026-10-22: **12 of 12 pass**, seed 20261022, 200,000 Monte Carlo samples.
The first execution reached JSON serialization and failed on a NumPy boolean; that output conversion was fixed.
No numerical prediction was weakened. Outputs are under `$NP_SCRATCH/uncertainty/maths-20261022/`,
`controls.json` (the initial 11 controls) and `controls-v2.json` (the additional ten-bin shuffle check).

| Control | Outcome |
|---|---|
| Add displacement error e(tau)=tau | Velocity moves +1; residual changes by less than 4e-15 |
| Add the corresponding covariance component | Velocity variance grows by 1; expected residual SSE unchanged to 1e-15 |
| Propagate shared-link covariance vs Monte Carlo | All six queried derivative variances agree within 0.65 percent |
| Deliberately discard displacement cross-covariances | Predicted variances become 1.71 to 5.32 times the correct ones |
| Four trusted links plus anchor | Zero residual dimensions, as required |
| Change polynomial origin but query the same physical instant | Velocity operator changes by less than 2e-15 |
| Unequal weights on an otherwise symmetric six-point set | Centre moves from -0.5 to -0.884615; first-moment centring does not restore reflection symmetry |
| Gaussian vector, known per-axis scale | The correct radial 68 percent circle covers 68.07 percent; a one-sigma circle covers 39.39 percent |
| Gaussian vector, scale estimated from two independent residuals | Radial 95th/68th ratio 2.971; theoretical 2.990 |
| Ten-bin shuffled rank correlations | Null SD 0.3343; the signed 0.2 limit rejects 29.93 percent of valid shuffles (absolute limit: 59.07 percent) |

These are mathematical controls on stated models. None is a new GPU measurement or evidence that matcher errors
are Gaussian, equicorrelated or small enough to linearize everywhere.

## 1. Say what the reported number measures

For a vector derivative estimate q, at a specified anchor pixel, timestamp, source-interval duration and derivative
order, define error e = q_hat - q_true. Three quantities have different meanings:

- **Covariance C**, a 2x2 matrix of centred errors, with units squared. A filter needs this together with an estimate
  of systematic bias. In an aperture case the uncertainty can be large along one direction and small along the other.
- **Per-axis sigma**, meaningful as one scalar only under an isotropic covariance model C = sigma^2 I.
- **Radial coverage radius r68**, satisfying P(||e|| <= r68) = 0.68 in a stated population. This can be calibrated
  empirically without a Gaussian claim. It is not automatically a covariance or an inverse-variance weight.

For zero-mean isotropic Gaussian errors, polar integration gives

```math
P(\|e\|\le r)=1-\exp[-r^2/(2\sigma^2)],\quad
r_{68}=1.509592\sigma,\quad r_{95}=2.447747\sigma,\quad r_{95}/r_{68}=1.621462.
```

Thus the design's rule Q68(||e||/(k sigma))=1 actually defines a radial radius, unless the conversion is explicitly
included. I propose naming that scalar **r68** in the calibration record, even if the eventual implementation keeps
the old parameter name. Report r95 separately. Do not impose the Gaussian ratio on a map whose scale estimate is
itself noisy. An ideal independent two-degree-of-freedom scale estimate produces a reference squared radius
`2 F(2,2)`, with quantile `2p/(1-p)`, hence r95/r68 = 2.99018. That alone refutes the proposed tail ceiling as a
universal correctness test. The shipped heuristic-weight fit is not asserted to have this exact t law.

For a validated positive-definite covariance and zero-mean Gaussian reference, squared Mahalanobis error
`e^T C^-1 e` has a chi-square-two reference: Q68=2.278869 and Q95=5.991465. If covariance scale is learned from finite
residuals or errors have bias/heavy tails, validate the appropriate reference or empirical coverage instead.
Calibration against a deterministic truth measures total error, including bias and truncation; reporting a centred
covariance alone does not account for either.

## 2. The estimator actually implemented

Source-read: [gen_sextdirectional.py](../../gen_sextdirectional.py), the `LSQ` block; the independent velocity
readout in [sext_resid.py](sext_resid.py), `mk`; existing calibration in [the design](../../../swarm/2026-10-21/uncertainty.md).

At an interior N:N window there are **six real points**, not seven independent observations: taus -3,-2,-1,0,1,2.
The shader has seven array slots because it reserves both +/-3; only one can exist in a six-frame window. The anchor
displacement at tau=0 is identically zero. Its noise variance and cross-covariances are zero in this coordinate
system, even though it is assigned a finite fitting weight of one.

The five polynomial coefficients are `(c,v,a,j,snap)` about `tc`, using factorial basis
`b(u)=(1,u,u^2/2,u^3/6,u^4/24)`. With frozen timestamps, weights and accepted branch, let X contain rows b(tau_i-tc),
W be the diagonal fitting weights, and y one image component's displacements **in pixels**. Define

```math
A=(X^T W X)^{-1}X^T W,\quad \widehat\beta=Ay,\quad R=I-XA.
```

These equations describe the estimator; use a stable solve rather than an explicit inverse in the CPU reference.
With five trusted links plus anchor, `rank(R)=1`. With four trusted links plus anchor, five points determine five
coefficients and `R=0`: no residual-based local scale exists. Such an exact fit can still have covariance if its
input error model is known independently. Fewer links, a cut, a failed solve or snap rejection take the fallback;
`resid_px=0` there means **no residual measurement**, not zero uncertainty.

For a physical query tau_q, put u=tau_q-tc. The derivative rows are

```math
l_v(u)=(0,1,u,u^2/2,u^3/6),\quad
l_a(u)=(0,0,1,u,u^2/2),\quad l_j(u)=(0,0,0,1,u).
```

For component input covariance Sigma, the variance at that query is

```math
h=lA,\qquad \operatorname{Var}(\widehat q)=h\Sigma h^T.
```

For two image components, stack per-point x/y errors, use `A tensor I_2`, and retain all cross-axis blocks to obtain
a 2x2 output covariance. Convert normalized UV displacements per axis before applying this model. A derivative
reported per source interval converts to per second by dividing by L^order; its covariance divides by L^(2 order).
That unit conversion does not remove temporal-fit truncation bias.

**The weights are not inverse variances.** They are smoothstep functions of round-trip consistency, with a hard
0.05 selection threshold. No calibration currently identifies them with `1/variance`. Therefore the familiar
`s^2 (X^T W X)^-1` shortcut has no warrant here. The general covariance propagation above applies for fixed W, or
conditionally with the covariance of errors *given* the selection and W. An unconditional covariance plugged in
after data-dependent gating need not be correct. Clamp, snap, cut and model-selection effects also need empirical
coverage; a local linear calculation covers the accepted, unclipped branch only.

## 3. Shared links: model the dependence before fitting a scale

For a rigid translation, define outward adjacent-link errors z in order (-1,-2,-3,+1,+2). With these orientations,
displacement errors at taus (-3,-2,-1,0,+1,+2) satisfy e_y=Bz, where

```math
B=\begin{pmatrix}
1&1&1&0&0\\1&1&0&0&0\\1&0&0&0&0\\0&0&0&0&0\\0&0&0&1&0\\0&0&0&1&1
\end{pmatrix},\qquad \Sigma=B\Sigma_z B^T.
```

Even independent primitive link errors produce correlated displacement observations. The project's earlier measured
correlations, [NFRAME-LIMITS.md, section 8](../../../NFRAME-LIMITS.md#8-2026-09-03-the-prefilter-built-and-refuted-and-two-leads-closed),
already show why independence is insufficient; this is not a new discovery about the matcher. The new audit carries
that dependence through the **actual sext fit and the residual**. The control's `sigma=0.15, rho=0.35` is illustrative,
not a fitted five-link covariance and not a proposed default.

For non-uniform flow, a two-link composition is `d=f1(x)+f2(x+f1(x))`. First-order perturbation gives

```math
\delta d\simeq (I+\nabla f_2)\,\delta f_1+\delta f_2.
```

The landing-point error is multiplied by the next flow's Jacobian. Longer paths repeat this rule and propagate cross
terms. The simple cumulative B is exact for the stated additive translation-error model, not a general deformation
model. Near occlusions or a switched alias, a Taylor approximation need not describe the error at all.

## 4. The residual's trace, and its blind subspace

The shader's squared residual is weighted vector SSE divided by `sum(w)`, not a regression variance estimate.
For one component with zero mean and covariance Sigma,

```math
E[\mathrm{SSE}]=\operatorname{tr}(R^T W R\Sigma).
```

Add the corresponding y-component trace for the vector SSE. Model bias m contributes the additional nonnegative
term `m^T R^T W R m`; the two-axis residual also cannot separate x and y noise scales by itself.
If a covariance **shape** Sigma0 is independently known and Sigma=s^2 Sigma0, a scale estimate is
`SSE / trace(R^T W R Sigma0)` per component, not SSE/sum(w). With identical, independent component shapes and a common
scale, divide the combined SSE by twice that trace. This is an expectation identity, not a promise of a stable local
scale: a single residual direction is intrinsically sparse information.

**Proof of non-identifiability.** Since `RX=0`, add any error `X delta_beta` to the displacement samples. The residual
does not change; the reported derivative changes by `l delta_beta`. In particular, `e_i=b tau_i` respects the exact
anchor, leaves the residual unchanged, and biases velocity by b. Similarly, adding covariance `lambda g g^T`, with
`g_i=tau_i`, leaves expected SSE unchanged while adding lambda to anchor velocity variance. No residual-only rule
can supply a universally valid finite derivative bound over this class of errors. A prior/model or independent cues
can constrain it. The existing empirical ranking remains valuable within its measured population.

For an efficient fixed Gaussian fit, coefficient noise and residual noise can even be independent. A spatial ranking
from the residual may then depend on heterogeneity of noise scale or departures from the ideal model. Do not confuse
good pooled ranking with a proof that each local residual is a precise local variance measurement.

## 5. Centring is a coordinate choice; symmetry is an additional property

A free-constant degree-four polynomial describes the same fitted trajectory under a change of origin, in exact
arithmetic. Evaluating its derivative at the **same physical timestamp** gives the same answer. This validates the
existing probe's `u0=-tc` transformation back to the anchor. Recentring alone does not improve that anchor estimate.

The shipped acceleration and jerk instead read coefficient rows at `u=0`, hence at tc. With equal weights and the
complete six-point stencil, tc=-0.5 and reflection symmetry cancels the omitted odd term's contribution to an even
derivative at that centre. Trust weighting or missing links can break this symmetry: zero first central moment does
not force zero third or fifth moment, or the relevant polynomial projection coefficients. In the explicit control,
weights (1,1,1,1,1,0.2) give tc=-0.884615 and a nonzero acceleration bias from `tau^5/120`, where symmetric weights
cancel it at the centre. This does not contradict the recorded equal-trust O9 benefit.

Source detail: tc currently includes weights <=0.05, whereas the solve excludes those points. For a -3 point of weight
0.03 with the other five weights one, tc=-0.017893 even though the active-point weighted centre is zero. This is not
a new shader repair proposal: it emphasizes that the exact tc must be reported or used when scoring centre-derived
quantities. A nominal fixed half-interval timestamp is not the complete contract under arbitrary trust.

## 6. A calibration protocol that can reject a wrong map

1. **Define the target first.** Field (fitted anchor velocity vs straddle chord vs centre acceleration), physical
   timestamp, units, accepted branch, support mask and estimator version are part of every record. A mode calibrated
   against one field does not automatically calibrate the other. Existing m10 targets fitted anchor velocity.
2. **Keep status separate.** At minimum record no fit, exact fit/no residual dimension, overdetermined fit, clipping,
   and ambiguity. All requested texels enter the coverage/refusal accounting. A map cannot improve its score silently
   by dropping the largest errors. Conditional coverage on accepted texels and coverage of the whole request both print.
3. **Start with an empirical scalar baseline.** Fit `r68=k*residual` only on overdetermined fits with positive
   readable residual. Count excluded zeros and exact fits, and count gross errors separately. This is a calibrated
   score only if it transfers to held-out groups; it is not covariance. Choose floors on training/control data, never
   by looking at the held-out errors. A flat, independently fitted radius is a useful baseline too.
4. **Use independent groups.** Freeze calibration before holding out scenes, motion laws, textures, and eventually
   captures. Randomly splitting neighboring texels leaks correlated errors. Report coverage per group and fit state,
   x/y bias, radial median/p90/p95, gross capture, and the accepted fraction. Millions of neighboring texels are not
   millions of independent replications; uncertainty on a coverage result needs frame/scene-block resampling.
5. **Separate ranking from coverage.** Pooled decile monotonicity, within-case monotonicity and held-out radial coverage
   answer different questions. A scalar can rank perfectly but have the wrong scale. Training Q68=1 after fitting k
   is true by construction. Require held-out coverage and show the coverage curve, not just one fitted quantile.
6. **Use a permutation distribution.** The design's signed `rho<0.2` requirement for ten decile medians is not a calibrated
   null test. Under exchangeable continuous ranks, Var(rho)=1/(10-1), regardless of bin population; 29.93 percent of
   the control shuffles exceed +0.2; an absolute 0.2 limit rejects 59.07 percent. The old log itself has a legitimate shuffled M2 decile rho=+0.503 with texel rho
   rounded to zero. Compare the observed statistic to repeated shuffles, report its null quantiles/p-value, and keep
   texel-level and ten-bin rho distinct. Shuffle within case/frame/support strata as well as across the pool, so a cue
   cannot succeed solely by identifying the scene. Treat spatial clustering when making significance claims.
7. **Challenge coherent errors too.** The `e=b tau` control must fool residual-only confidence. Add a separate
   ambiguity/out-of-support indication; do not relabel low residual as truth. Calibrate on genuine alias/reach cases
   before exposing a numerical confidence promise there.
8. **Then propagate covariance.** Export accepted displacements, timestamps, weights, tc and state at matched pixels
   on exact synthetic truth. Estimate bias and joint input covariance on training groups, propagate with h, and check
   held-out derivative errors. Compare full covariance to the diagonal counterfactual. A frozen polynomial fit needs
   no shader solver replacement for this check. The current m10/m11/m12 dumps do not contain those joint inputs.

Suggested export contract: derivative vector; actual query timestamp and interval duration; fit state and ambiguity
flags; independently validated `(Cxx,Cxy,Cyy)` if available; otherwise an empirically validated `r68` explicitly named
as such. Missing information is missing, not encoded as zero. No new painting or shader mode is adopted by this audit.

## Sources and scope

The existing stencil-covariance work in NFRAME-LIMITS section 8 was read before designing the controls. The project
already connects the N-frame family to Savitzky-Golay fits and PIV in PRIOR-ART.md. This is an application of standard
uncertainty propagation to this estimator, not a novelty claim.

- [JCGM 102:2011, sections 6.2.1 and 6.5](https://www.bipm.org/documents/20126/2071204/JCGM_102_2011_E.pdf):
  the covariance propagation formula and the distinction between vector covariance and coverage regions were checked
  against the primary guide. The estimator-specific operators, exact-anchor treatment and counterexamples above are
  derived here from the code.
- [NIST, Weighted Least Squares](https://www.itl.nist.gov/div898/handbook/pmd/section1/pmd143.htm): inverse-variance
  weights and known-weight assumptions were checked. The shader's trust weights have not been given that interpretation
  by a calibration, so the general sandwich propagation is retained.
- Sciacchitano's 2019 PIV uncertainty review is already cited in PRIOR-ART.md. Retrieval of its full PDF failed during
  this block; no new theorem or quantitative claim here is attributed to that unread PDF.
