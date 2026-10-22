# Review of the bars re-decision and sampling arguments

GPT, 2026-10-22. Reply to CHAT-LEDGER L009, source tree a3530bd. Predictions were committed in G006
(760f1b1) before the CPU experiment. This is a review of a variant and its interpretation; no default changes.

The reported C3 gain stands. The new result is a concrete counterexample to unconditional use of the smallest-speed
rule: even a correct fast seed can be replaced with its slow alias. The rotating-Moire explanation also needs a
two-dimensional treatment before a pooled slope can be attributed to a mixture of bars and grain.

## 1. A correct seed destroyed by the last pass

For a translating periodic print I(x,t) = F(x-vt), F(x+P) = F(x), the motions v and v-mP give the same image at
every integer source time. This remains true for any number of equally spaced source frames. At t=1/2 an odd m
shifts the print by half a period, so the correct interpolated pictures can be different. This applies the argument
already recorded in [PRIOR-ART.md](../../../PRIOR-ART.md), "More frames cannot break an exact half-period tie";
it is not a new identifiability theorem.

Use P=9, v=6. In a periodic interior, candidates 6, -3 and 15 all match. BAR_REDECIDE's reach includes all three
from a correct seed of 6, its tensor gate accepts the bars, and the smallest-speed rule chooses -3. An accurate
motion brought in by a boundary, temporal seed or another stage can therefore be discarded at the last pass.

[bar_review.py](bar_review.py) implements the scalar restriction of the actual decision: the imported constants,
seven taps at spacing 2 (the 7x7 SAD reduces exactly for a y-invariant texture), local minima, tie tolerance,
parabolic refinement and the 2 px switch threshold. Source SHA256 is included in the output. It also checks the
half-res tensor gate on the constructed texture. It does not emulate the preceding search, GPU rounding or cache.

**Measured, CPU, 13/13 named checks passed:**

| Truth and correct seed, px/frame | Result of the re-decision | Interpretation |
|---|---|---|
| +6 | -3 | nine-pixel error introduced |
| -6 | +3 | reverse-direction control fails symmetrically |
| +3 | +3 | slow-motion control preserved |

The +6 and -3 integer-time movies differ by at most 2.23e-15 over the tested samples; the half-time movies differ by
0.5 in normalized luma. These numbers use F(x)=0.5+0.25 cos(2 pi x/9), full-resolution integer pixel samples and
linear reconstruction. The periodic impossibility proof does not depend on that particular bar profile.

**A useful non-periodic control:** add a co-moving marker m tanh(x/4). This stays one-dimensional, so the tensor
still accepts it. At this patch the decisions for m=0, .002, .01, .05, .15 are respectively -3, -3.0011, +6, +6, +6.
The marker's mere existence does not suffice: the .002 marker is swallowed by the absolute 1/255 near-best allowance.
These marker values were fixed before the run, but no marker threshold prediction was registered. They describe
this patch, not a universal contrast threshold.

**The GPU test to add next:** a rigidly translating period-9 strip at +6 and -6 px/source-frame, with +3 as control;
use both a periodic interior and a co-moving non-periodic marker/outline. First run an instrumented version of the
last pass with its incoming flow forced to the exact truth, checking that +6 becomes -3 in the periodic interior.
Then run unchanged High and High+BAR_REDECIDE on the same scenes. Score the interior separately from edges, read the
flow before and after this pass, and compare synthesized half-instant pictures against analytic truth. Include
several start phases and an oblique orientation. A regression requires baseline High to be correct there; if both
pipelines already pick the same alias, that is an ambiguity witness, not a regression. No GPU job ran in this block.

Practical implication: retain the current variant status. A replacement should compare evidence for a change of
basin against the provenance of the existing seed. Merely making the small-speed prior stronger cannot resolve the
ambiguous interior. This is a design constraint, not a proposed switch that has passed the ladder.

## 2. The comb has a closed form, but it does not predict the entire matcher

For one complex Fourier mode A(x)=exp(i k x), let B(x)=A(x-d). Store B on the grid js and reconstruct it linearly.
At the **true** displacement d=s(q+alpha), q integer, 0<=alpha<1, the fetched value divided by A(js) is

    H_s(k,d) = exp(-i k alpha s) [(1-alpha) + alpha exp(i k s)].

This follows by substituting B((j+q)s) and B((j+q+1)s) into their weighted sum. The squared mismatch of a unit complex
mode is |H_s-1|^2. For a real sinusoid with independent uniform phase, multiply this by half the squared amplitude.
For a stationary signal with uncorrelated Fourier increments and spectral measure S, the expected squared mismatch
is the integral of |H_s-1|^2 against S. In two dimensions, bilinear interpolation gives the product of the two axis
factors, with alpha_x=d_x/s_x modulo 1 and alpha_y=d_y/s_y modulo 1. A shared lattice origin is assumed here.

Consequences under this model:

- d in s Z makes H=1 at every frequency, so a rigid translation by a whole stored-grid interval is protected at the
  true candidate. Special spectra can have additional exact phases. This is about the candidate's cost, not whether
  the finite search reaches or selects it.
- The response is periodic in displacement modulo s. A positive sum of squared mismatches from pitches 8 and 16
  vanishes exactly when both vanish. Their universal zero sets intersect at 16 Z; taking the better of the two gives
  the union, 8 Z. Neither covers all displacements for all spectra. The period-9 counterexample below breaks both
  at 10 and 12. This does not rule out a more capable estimator combining their data and priors.
- An exact continuous frame fetch at x+d has H=1. An actual full-resolution bilinear fetch instead has the analogous
  pitch-1 reconstruction error at fractional pixel displacements. Calling it unconditionally shift-invariant for
  every real candidate is too strong. At integer shifts of a rigidly translated sampled image it is exact.

| Pitch | d=8 | d=10 | d=12 | d=16 |
|---|---:|---:|---:|---:|
| 8 | 0 | 1.901794 | 3.762407 | 0 |
| 16 | .054735 | 1.663114 | 3.349657 | 0 |

Entries are |H-1|^2 for k=2 pi/9, not shader SADs or PSNR. Across 256 deterministic random frequencies/displacements,
the formula and independent direct interpolation agree within 3.65e-14. Deliberately reversing the leading phase
sign produces a discrepancy of 1.9985: the check detects the wrong formula.

This answers L009(b) for the sampler, with a limit: S(k) alone does not determine the winning basin of a finite SAD
block with deterministic phases, a limited candidate search, a regularizer and cross-level re-scoring. Do not fit
this formula directly to the PSNR comb and call it the matcher's transfer function. The established v12 improvement
and v10 regression still need their respective candidate-cost and selection traces.

## 3. C3 needs a vector alias before a mixture model

Use cycles/pixel here. For instantaneous bar normal n=(cos theta,sin theta), the fundamental spatial frequency is
k=n/9. On a square grid of pitch s the reciprocal aliases are

    k_s = k - m/s,     m in Z^2.

At lattice points exp(2 pi i k.x) and exp(2 pi i k_s.x) coincide. Their temporal phase rate remains k.v, so a local
aliased flow must satisfy

    k_s . v_s = k . v.

That is one constraint on two components. If k_s is not parallel to n, it does not determine n.v_s, the across
component used by the current slope test. One illustrative choice is the minimum-norm normal flow

    v_s = (k.v) k_s / |k_s|^2.

For theta=0, s=8 with m=(1,0), or s=16 with m=(2,0), k_s=(-1/72,0), giving n.v_s=-8 n.v. Thus the registered
-9 error slope is correct in that aligned idealization. The index 2 at pitch 16 is the **second reciprocal-lattice
replica of the fundamental**, not the bar signal's second harmonic. Actual clipped-cosine bars also have harmonics,
and those must each be folded separately.

For a true across speed of one, the illustrative minimum-norm ratios are:

| theta, radians | pitch 8 | pitch 16 |
|---|---:|---:|
| 0 | -8.0000 | -8.0000 |
| .15 | -2.7480 | -2.7480 |
| .30 | -.6438 | -2.4083 |

These are **computed model examples**, not a fit to C3's taps. The principal reciprocal index's y component at pitch
16 changes near theta=asin(9/32), within C3's two-second sweep. C3 additionally rotates between frames, mixes bar
harmonics and grain, and is matched on a finite block, so a local frozen-frequency treatment is an approximation.
The elementary two-dimensional sample identity is checked to 1e-12 in the CPU probe.

There is a second causal limitation in the saved probe: `c3_flow.py` samples `FLOW_S_AB.xy`, the **zero-descent
candidate**. The shader writes the ring candidate to `.zw` and the temporal candidate to `FLOW_S_AB_CACHE2`, then
refines and selects among all three at E. A change between S.xy and E is not necessarily the same trajectory being
nudged out of an alias. The probe's docstring correctly identifies xy; interpretations of the readout must preserve
that qualification.

Therefore the -5/-4.4 pooled slopes and the -17 modal band are evidence consistent with aliasing, but do not establish
a two-component mixture fraction, or prove that E undid exactly one period of that particular coarse seed.
Even in a scalar mixture e=-9 Z v+noise, the fitted slope is -9 Cov(v,Zv)/Var(v), not generally -9 E[Z]; component
membership can correlate with speed, angle and position.

**Next discriminating read:** stratify by frame angle and velocity; compare phase residual k_s.F-k.v alongside k.F-k.v
for each coarse candidate, and record the E winner's candidate identity. Evaluate several harmonics and independently
measured bar/grain contrast before fitting mixture weights. A mixture fit to the same pooled slope would be
circular. The existing saved xy taps alone do not contain the missing candidate identity. This review has not fitted
the mixture or claimed to explain its measured slope.

## 4. The grain bound and the units of the gain

For an exactly periodic patch, a shift of one period leaves every sample unchanged. No block-SAD rule restricted to
that patch can identify which physical displacement occurred. Aperiodic grain may break the tie, but its support
fraction alone is not an upper bound on the recoverable image error: contrast, match margin, the near-best tolerance,
candidate availability and warp influence also matter. External anchors can resolve locally ambiguous patches.

For this specific decision the observable is whether a rival's cost exceeds 1.25 C_min+1/255, together with its
speed and reach. Measure the margin map at the true displacement and each reachable alias. Separate "uniquely ranked
by this sampled cost", "truth present but admitted alongside aliases", and "truth outside the candidates". Propagate
those masks through the actual warp before making a bound on picture recovery; a 13 px block is not a 13 px output
footprint. The marker control in section 1 illustrates why detecting any grain is insufficient.

The registered score is a **dB-gap fraction**: (27.30-23.43)/(36.47-23.43)=29.68%. Keep that wording. Converting these
three summary dB numbers to equivalent errors gives 62.06% of the equivalent error gap, a different quantity. Since
`c3_flow.py` averages per-frame PSNR, those equivalent errors correspond to geometric means; they are not the pooled
arithmetic MSE. Actual fraction of squared image error removed requires the frame SSEs and pixel counts. The same
qualification applies to "98-99 percent of the gap": valid in its registered dB metric, not a measured energy share.

## Reproduction and disposition

    PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/cage/bar_review.py --out "$NP_SCRATCH/bar-review/results.json"

numpy is required. Results stay outside git. The JSON records each check, complete scalar cost curves, the marker
control, sampler formula controls and the reviewed bar module's SHA256. CPU restrictions are explicit; no new GPU
results, no adoption decision and no change to existing reported wins. Reasoned verdict: promising variant with a
proved prior failure and an incomplete alias-mechanism account. Gut verdict: the last pass can erase useful upstream
information; test that interaction before strengthening its preference for small motion.

Background checked during this review: [MIT, Foundations of Computer Vision, Image Sampling and Aliasing](https://visionbook.mit.edu/sampling_and_aliasing.html),
sections 20.3-20.4 and 20.6, for spectral replication, reconstruction and spatiotemporal sampling. The transfer factor,
specific counterexample and restrictions above are derived here; no novelty claim is made.

## 5. Follow-up: the actual GLSL pass run on the GPU

The owner clarified that GPT should run GPU work directly. [bar_gpu.py](bar_gpu.py) now supplies the exact seed and
the half-res luma to the **unmodified** `bar_redecide.PASS`, then split-encodes its output flow. This is a newly
generated diagnostic shader, with no change to the shipped sources. Eight short sequential M5/Vulkan renders,
256x128, 24->24, ten scored outputs per run (source frames 3-12 of 16), reading `rgba64le` inside the filter graph.
The two repository MoltenVK settings are enabled; dithering is disabled explicitly. The lower flat strip is still
with zero seeded motion, and the bar interior excludes the strip boundary and image edges.

**Measured, 2026-10-22, predictions held:**

| Truth, px/frame | Bypass median x | Actual bars pass median x | Bars pass x, p5 to p95 |
|---|---:|---:|---:|
| +6 | 6.000000 | -2.999985 | -3.029282 to -2.968765 |
| -6 | -6.000000 | 3.000015 | 2.968765 to 3.029282 |
| +3 | 3.000015 | 3.000015 | 3.000015 to 3.000015 |

All eight instrument checks pass: three bypass calibrations, deliberately truncated output refused by the same
decoder, three flat-background checks (exact zero), and the +6 bars repeat byte-identical. All three registered
velocity predictions pass. A .15 co-moving marker preserves +6 at every sampled point within four pixels of the
marker's centre across the ten outputs; far from it the periodic interior still takes -3. This marker fraction is
descriptive, not a new general calibration claim.

This upgrades the prior failure from a CPU restriction to a measured failure of the actual GLSL decision with a
known-correct input flow. It still does not establish how frequently the complete High pipeline supplies the correct
seed in this regime, or a picture-score regression of High against High+BAR_REDECIDE. Those require the paired
full-pipeline experiment described above. The current result is enough to show that the last pass can erase valid
incoming motion, even while every input and output of the test is calibrated.

    PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/cage/bar_gpu.py --out "$NP_SCRATCH/bar-review/gpu"

`FFMPEG` selects the patched executable; numpy is required. `results.json` records source-pass, executable, generated
shader and output hashes, the eight run summaries, all controls and the verdict. The inputs, shaders, logs and raw
outputs are retained beside it outside git. A compile/fallback error or wrong frame count refuses the measurement.

## 6. Ordinary High now supplies the counterexample (reply to L010)

Local reproduced section 5 byte for byte, then killed BAR_KEEP: preserving every near-best incoming seed retains
only 0.44 of C3's 3.87 dB gain and loses 0.68 dB on C2. Local's C4 case instead improved: High supplied a +15 lock,
and the pass's limited reach could recover +6 without reaching -3. Those outcomes stand.

**G009, before this run:** add a broad sinusoid underneath the fine bars. Predict that at least one of three guided
cases has over 1% of matched interior samples where ordinary High reads +6 within .5 px and the bars variant reads
-3 within .5 px. The hypothesis concerns local destruction of correct flow, not a whole-picture loss.

[bar_pipeline.py](bar_pipeline.py) generates both shaders using the official generator. The unchanged High must
reproduce the shipped file byte for byte. Only a diagnostic tail is appended to read the final H flow; the separate
picture renders use the generated shaders without that tail. No exact flow is injected. The rigid source at 24 fps is

    I(x,y,n) = .5 + a cos(2 pi ((x+.5-6n) mod 9)/9) + b cos(2 pi (x+.5-6n)/P).

It is constant along y, fills the frame and never clips. These are new 512x128 signals, not C4 and not real footage.
All four tuples were fixed before the run. Frames 3-12 are read, crop x=48..463, y=24..103. The listed fractions pool
ten frames; adjacent pixels/frames are correlated and no independent-sample confidence interval is claimed.

| fine a | broad b | period P | High within .5 of +6 | High correct, variant within .5 of -3 |
|---|---|---|---:|---:|
| .15 | 0 | 256 (unused) | 2.7404% | 2.7404% |
| .15 | .25 | 256 | 6.9892% | .5120% |
| .15 | .25 | 512 | .8870% | .8822% |
| .08 | .30 | 512 | 12.4567% | **1.1587%** |

**Prediction held**, narrowly above its 1% threshold on the last guided case. The pure-period control also has
correct seeds destroyed. This settles L010's occurrence question: correct fast seeds do occur in the ordinary
pipeline, and the pass can erase them. It does not prove that the broad component guided the coarse/global seed;
that causal account needs coarse candidate/selection taps. The non-monotonic table warns against claiming it.

**Picture measurement, triggered by the flow witness:** render each unchanged interpolation shader at 24->48 and
score only the ten synthesized half-instants against the analytic scene at those instants. The same crop gives:

| case | High PSNR | High + bars PSNR | change |
|---|---:|---:|---:|
| pure period | 14.7226 | 17.2590 | +2.5364 dB |
| .08 fine, .30 broad, P=512 | 21.0036 | 29.8133 | **+8.8097 dB** |

The pass helps these full crops. **Exploratory local measurement after seeing the flow result:** select pixels only
by the correct-to-alias field predicate, not image error. On the guided case's corresponding image coordinates the
MSE changes 0.000007748 -> 0.01040676 (-31.28 dB). Moving that mask +3 pixels to follow the known half-interval motion
gives 0.000081417 -> 0.00744811 (-19.61 dB); moving it -3 gives -18.74 dB. Thus the local picture loss survives this
alignment sensitivity check. These masks are diagnostic subsets, not independent scene gates or pre-registered
image thresholds. The pure-period control does not have the same robust local loss (mask shifts 0/+3/-3 give
+0.0015/+5.82/-1.73 dB); do not use its vector predicate alone to claim picture damage.

**Instrument checks:** the constant +6 bypass reads exactly +6 and the flat background exactly zero at the new
dimensions. A deliberately eight-byte-short export is refused by the same reader. Both full High and bars witnesses
repeat identically; compiler/fallback warnings and wrong frame counts refuse the measurement. Passthrough output
instants are compared with the analytic source too: maximum luma error .000335 (pure) and .000491 (guided), below
the explicit .001 readback/alignment gate. These small errors include conversion/precision; no exact byte identity
to analytic floating-point truth is claimed. The final run reproduces every originally reported flow fraction and
full-crop MSE. Additional controls/local scoring were added after the first run and are marked as such in the tool.

Reproduce with numpy and the patched FFmpeg:

    PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/cage/bar_pipeline.py --out "$NP_SCRATCH/bar-pipeline"

The script retains the first-run JSON separately when the operator copies it before a rerun; it does not silently
version output directories. For this block `results-first.json` and final `results.json` are both retained. Logs,
generated shaders, raw input/output and hashes are outside git. No default or source shader changed.

**Disposition:** keep this scene as an adversarial local regression alongside C3's recovery gate. A simple keep
rule is already killed; the next candidate needs to distinguish reliable incoming fast motion from a wrong
period-fast lock. A whole-frame average alone cannot judge that repair, since it would hide this measured loss.
Reasoned verdict: occurrence proved on the ordinary pipeline; overall benefit and local harm coexist. Gut verdict:
the failure is now concrete enough to constrain a repair, while the proposed broad-guide mechanism remains open.

## 7. A broader-support evidence guard, first kill test

G011 fixed the design and thresholds before rendering: score the selected candidate and the incoming basin on a
7x7 grid at spacing 8 (48 px footprint). Refine the incoming candidate over {-1,-.5,0,.5,1} px along the normal for
the comparison only. Change basin only if the new candidate improves that broader SAD by over 1/255. If refused,
retain the incoming vector exactly. The original fine search and small-speed choice are otherwise unchanged.
`bar_guard.py` generates this diagnostic variant by asserted substitution of the complete original pass.

The registered kill test required guided corruption below .2% and C3 gain over High at least 3 dB. **Survives:**
corruption .04808% (from 1.15865%); guard repeat identical. C3 High / bars / guard read 23.2379 / 27.2978 / 27.1597 dB
on cage.sh's rectangle, 92 scored outputs from 120. Guard gains 3.9217 dB, against bars' 4.0599 in this run. The
High baseline differs from Local's 23.43; these comparisons use the same run's baseline. A repeat is required before
calling this deterministic. Data: `$NP_SCRATCH/bar-guard/results.json`; exact inputs are the previous block's guided
source and scenes.sh's C3. This is a surviving candidate, not an adoption or a completed regression gate.
