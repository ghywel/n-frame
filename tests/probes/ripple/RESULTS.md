# Garment ripple diagnosis — 2026-11-15

**The reported defect is reproduced, and no verified shader cure is established.** The owner confirmed that the
native shirt comparison shows the same ripple, then judged the independent FFmpeg block-motion interpolator's
shirt **noticeably calmer** than current High. This is a useful positive playback control on the actual failure.
Its estimator and renderer both differ; it does not yet identify which difference reduces the reported ripple.

Eleven conditions were rendered on each of two short 1080p windows, both at native doubling and with odd original
frames withheld: 44 complete renders. A final same-field rigid-patch renderer gives modest, fairly consistent
withheld-truth improvements, but the owner finds **no clear improvement** in its native shirt playback. It fails
to establish the requested visual benefit and is rejected as a remedy in this block. No production shader/default/Cadence graph
has changed. This block contributes a confirmed real regression fixture, sharper measurements, mathematical
counterexamples, and recorded failed interventions—not an assertion that the playback problem is solved.

## Scope and reproducibility

The two reported events are the white shirt leaning back at 202–204 seconds and the standing man's suit at
209–211 seconds. Only 200–205 and 207–213 seconds were cached, with 119/143 original frames. The source is
24000/1001 fps; native exact doubling produces 238/286 frames at 48000/1001. Exact input PTS are assigned before
libplacebo. The owner's confirmation establishes reproduction at this ratio; literal fixed 48 fps is not tested.

Baseline `ccfdf74` includes Local's light vote in High. Current and preceding High regenerate byte-identically:

- Current High, `WARP_VOTE=2`: `692d4af281ffef675040c094b9351dcedf8337a85269069c18d07a63e33eeff0`.
- Preceding High, `WARP_VOTE=0`: `b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece`.

All other interventions except `vote-nearest` act individually on the preceding High. They are not combined with
the light vote. Generated hashes, per-frame results, repeated-baseline checks, counts and controls are retained in
[review-summary.json](review-summary.json), with tables in [review-summary.md](review-summary.md). See
[README.md](README.md) for commands, [PLAN.md](PLAN.md) for initial predictions and the intervention documents for
their preregistrations. Original media, full logs, arrays and previews remain in external scratch under the
experiment name `translation-ripple-20261115`; the repository record contains no private film path.

The withheld condition reconstructs odd originals from half-rate even originals. It therefore has **twice native
endpoint displacement**. Both clips score only the 24 odd original frames 49…95. Fixed ROIs are shirt
`(240,230,700,620)` and suit `(160,80,960,800)`, including garment boundaries. The measured retained-source maximum
MAE is below 0.065 DN in these intervals. Every repeated `prev` baseline matches exactly. Numbers below use
normalized grayscale DN on a 0…255 scale; PSNR pools MSE, not dB. Gaussian σ2 results reduce fine texture energy
but do not remove grain or guarantee that blur is penalized appropriately.

## A temporal measurement was missing the relevant failure class

Local's earlier `occwarp/warpsim.py` statistic named `flicker` measures changes in a **scalar per-frame ROI MAE**.
A spatially moving or sign-changing error can keep that scalar fixed. The stored key is preserved for historical
compatibility; its printed label and documentation now say `scalar-MAE-change`. Earlier reductions remain valid
as reductions in that scalar, but cannot establish reduced local flicker by themselves.

There is a second blind spot even after switching to pixelwise comparisons. If every inserted frame has the same
error in material coordinates, synthesized-only error change is zero. Yet the displayed sequence alternates
between intact source pictures and defective insertions. Both parity classes and their transitions must be tested.
New controlled failures exercise both blind spots, including a constant-error midpoint sequence that visibly
breathes while its synthesized-only stability is perfect.

`temporal.py` measures source-registered pixelwise curvature at both source and inserted centers, spatial error
maps and midpoint-departure changes. Registration uses source frames only, so a candidate cannot validate itself
with its own warped motion. The requested shirt track, frames 48–84, **fails at 55→56**: best correlation 0.91549,
rival 0.90746, peak gap 0.00802 below the fixed 0.01 threshold. Only 48–55 are measured; the rest remain unknown.
Do not quote this short track as coverage of the whole reported episode. [TEMPORAL.md](TEMPORAL.md) gives its
limited results. The rejection is valuable: a smooth-looking numerical answer on an ambiguous track is not evidence.

## A shared vector does not guarantee coherent endpoint pictures

A production comment explains that both endpoint samples remain coherent because a shared wrong flow moves them
wrongly in the same direction. That explanation is false in general. For true rigid translation d and used flow
d+δ, the sampled material coordinates are `s−tδ` and `s+(1−t)δ`: opposite sides of the desired point, separated by δ.
Their weighted centroid is correct, so a linear intensity ramp is reproduced; edges and curved profiles can blur
or double. This does not overturn the historical empirical failures of the three retired fallback implementations.

For a sinusoidal material carrier of period P, a midpoint's contrast is multiplied by `cos(πδ/P)`, while retained frames keep
their full contrast. A four-pixel error on a 16-pixel carrier gives 0.7071 midpoint contrast. A smooth spatial error
can make different patches breathe differently without any occlusion or sampling-map reversal. This is an exact
counterexample and a reproducible CPU video, **not a measurement of δ or the dominant cause in this film**.

Grain is a necessary competing control: even with perfect flow, averaging independent equal-variance source noise
halves its variance at a midpoint. Its RMS also becomes 0.7071. Low-pass filtering reduces absolute grain energy
but preserves that variance ratio for independent filtered grain. Apparent contrast breathing alone does not
identify flow error. [GEOMETRY.md](GEOMETRY.md) and `geometry.py` preserve both constructions.

The same audit separates inverse-coordinate error from wrong flow. A-indexed displacement should satisfy
`q+tF(q)=p`; reading F at output p is an approximation. An exact orientation-preserving affine deformation can
make this approximation reverse locally, and a smooth exact field can make it fold. A negative measured Jacobian
therefore does not by itself prove estimator failure. Two fixed-point proposals can diverge even with exact valid
flow; their failure cannot rule out a coordinate problem. Bounded Newton solves the declared affine control but
does not identify the visible correspondence, and its real-film results are mixed.

## What the field read establishes

RGB48 diagnostic decoding was calibrated: static maximum absolute flow 0.001953 px; known (+32,0) translation
reads median (31.2485,0.1270) px in the specified textured interior. CPU replay of the preceding High's shared warp
and support fallback matches four native shirt outputs within 0.4538–0.4910 DN RMS away from the dump boundary.
These checks establish that the instrument reads the relevant field and can reconstruct its picture closely.
The calibrated replay values and legacy provenance are preserved in [field-replay.json](field-replay.json).

The fixed exploratory rectangle `(440,450,140,140)` is not a tracked cloth mask. At native output 145 its x flow
spans approximately −31 to +4.75 px, gradient-norm p99 is about 1.59, and roughly 0.15% of its approximate A sampling
Jacobians reverse orientation. Q→H field difference is about 1.01 px RMS there. Its mean coherence fallback is
0.130, versus 0.000061 at output 97. These locate variation worth investigating; they do not tell us which pixels
are wrong, whether the surface is occluded, or whether cloth deformation is physically real.

## Intervention results, including failures

The table reports **withheld-truth deltas against preceding High**, not a native comfort score. Positive PSNR is
better; negative gradient change is better. Averages cannot overrule a distracting boundary failure.

| Isolated condition | Shirt raw Δ dB | Suit raw Δ dB | Shirt σ2 gradient Δ DN/px | Suit σ2 gradient Δ DN/px |
|---|---:|---:|---:|---:|
| Current High: light vote | +0.0787 | +0.0247 | −0.01110 | −0.00660 |
| Light vote, nearest confidence | +0.0699 | +0.0213 | −0.01060 | −0.00595 |
| Remove coherence fallback | −0.0542 | −0.0003 | +0.01629 | +0.00594 |
| Disable E cached candidate and temporal prior | −0.1600 | −0.1459 | +0.02191 | +0.03112 |
| Bypass H data refinement | −0.0225 | +0.0193 | +0.00456 | −0.00706 |
| Two guarded inverse proposals | +0.0571 | −0.0415 | −0.01371 | +0.01344 |
| Bounded Newton | +0.0218 | −0.0996 | −0.01659 | +0.00606 |
| Cascaded luma box prefilter | +0.0257 | +0.0419 | −0.00268 | −0.00588 |
| Same field, 8-pixel rigid-picture overlap | +0.1458 | +0.0967 | −0.02628 | −0.03645 |
| Linear image blend | −4.4032 | −1.6261 | +0.86902 | +0.41485 |

**Vote confidence leakage is a concrete additional bug.** Light-vote DRAW samples the chosen vector nearest and
its confidence bilinearly. A vector rejected at its own texel can borrow neighboring confidence; a CPU control
reaches weight 7/16 for that rejected vector. Nearest confidence makes the decision and vector agree, but gives
no extra improvement here over current High and can sharpen grid transitions. It cannot explain the preceding
High's reproduced ripple. [VOTE-SAMPLING.md](VOTE-SAMPLING.md) contains the counterexample; no production change
is promoted without the broader gate.

**No single estimator/coordinate ablation removes the truth failures.** Disabling E temporal memory hurts both
clips. Bypassing H refinement trades a small suit gain for a shirt loss. Removing fallback, inverse2 and Newton
have mixed local outcomes. Newton's shirt gradient improves but its σ2 PSNR/tail/worst tile worsen; suit pooled
errors worsen. A smaller inverse residual does not establish visible-surface correctness. Its drawn B coordinate
also differs from `q+F(q)` by `−r/t` if residual r remains, and B is not independently domain-checked.

**Prefiltering is not a new discovery or a demonstrated remedy.** The historical failures in NFRAME-LIMITS §8
remain recorded. The current cascade gives only tiny film mean gains and leaves or increases local maxima. Fresh
current-baseline checks on L0/L6/M1/A4 give whole/interior deltas −0.050/−0.050, +0.297/+0.311, +0.202/+0.212 and
+0.321/+0.337 dB respectively. The old severe losses do not repeat in this four-case modern probe; neither does
this small probe replace the full gate. Luma also feeds support/cut/global statistics, so this intervention does
not isolate the estimator from those consumers. See [AA-PYRAMID.md](AA-PYRAMID.md).

**Rigid-picture overlap is the most consistent small truth gain.** It uses the exact same estimated field, samples
four nodes on a fixed 8-pixel grid and blends their independently warped pictures rather than their vectors.
Every scored raw-PSNR frame improves in both clips. Raw worst-1% RMS decreases 47.128→45.897 DN (shirt) and
74.742→73.643 DN (suit); σ2 gradient RMS decreases about 1.9% in both. Worst σ2 tiles improve only
63.588→62.899 and 96.617→96.190 DN. Relative to **current** High its raw gain is +0.0671/+0.0721 dB; shirt σ2
PSNR is slightly lower (−0.0087 dB). Local shirt σ2 losses still occur, worst −0.0272 dB at frame 53 against `prev`.
Picture averaging can hide a geometric defect through blur or double edges, so these numbers do not demonstrate
the requested comfort improvement. [OBMC.md](OBMC.md) includes a deliberate case where this construction worsens
the picture. Native side-by-side previews were prepared for both scenes. The owner reports **no clear improvement**
in the shirt comparison. Its numerical gain therefore does not pass the visual-benefit gate; no suit verdict is recorded.

The dominant baseline withheld tile is shirt frame 73 at `(752,774)`: the **lower sleeve/cuff/wrist boundary above
the glass**, not garment interior. Suit frame 83 at `(544,240)` is a **tie/light-jacket boundary overlapping a seated
head**. These source locations were inspected. Their high errors must not be relabeled as a quantitative measure
of torso ripple or averaged away. Other variants can move the maximum to a different tile.

## Positive playback control and next discriminating experiment

The independent FFmpeg MCI control uses bidirectional motion estimation, adaptive overlapped blocks and
variable-size blocks. Output counts match native doubling and four retained instants in each clip are grayscale
exact. The owner reports the displayed **shirt is noticeably calmer than current High**. That is stronger evidence
about this complaint than a favorable average PSNR; it also establishes that the source itself does not force
every interpolator to show the same apparent ripple. There is no equivalent human suit verdict recorded here.
The explicit CPU reproduction subsequently matches every decoded grayscale sample of both displayed MCI files.
None of the eight checked garment midpoint crops equals either source endpoint, ruling out whole-crop frame holds
at those samples. [mci-recheck.json](mci-recheck.json) preserves the exact reproducible command, hashes and indices;
it does not claim that all individual pixels or untested frames use accurate motion.

The same-field overlap comparison supplied the next separation: its lack of a clear visual benefit shows this
particular rendering intervention was insufficient. It does not prove that changing the estimator is necessary,
or that other rendering methods cannot help. The independent comparison still does not separate estimator from
renderer. Do not equate our fixed 8-pixel renderer with FFmpeg's complete adaptive-block method. The failure is
retained precisely because an across-the-board raw PSNR gain did not deliver the improvement the owner requested.

The narrowest further synthetic test is a frozen garment texture with **known rigid translation**, tested as oracle
versus estimated flow crossed with no added grain versus known independent grain. Keep one fixed motion, the same
sampling, both output parities, exact material-coordinate truth, and no tuning on these films. This can distinguish
estimator-induced deformation from rendering/noise contrast cycling before adding physical deformation or occlusion.
It is a proposed next experiment, not a result in this block. The separate boundary/visibility failures remain open.

## Instrument checks and evidence limits

CPU controls cover translation calibration, ambiguous/flat rejection, both temporal blind spots, exact withheld
truth, localized faults, brightness-only faults, inverse geometry, singular/refused Newton steps, picture-versus-
vector averaging, vote leakage and cascade sampling. Tiny FFV1 counterfactuals reject wrong output counts and
corrupted retained frames. Aggregation rejects altered baselines, frame indices, arithmetic, shader hashes,
incomplete renderer markers and private paths. Failed reruns invalidate stale success metadata. Independent
source/maths reviews checked the transforms and prompted additional dump metadata and phase validation.

Original successful render sidecars predate the new completion marker; they remain explicitly labeled legacy,
not retrospectively stamped complete. Process calls were checked during execution, and decoded counts, hashes
and retained alignment were independently checked. Historical logs alone do not prove process exit status.
All 13 generated shader copies reproduce their rendered hashes. No runtime/Arc claim is made from these diagnostic
jobs. No full replacement gate was run because no replacement has passed the native visual gate.

## Subsequent fixed-motion control

The proposed frozen-plane experiment was then executed, with four additional short GPU renders. See
[RIGID-RESULTS.md](RIGID-RESULTS.md). Both instrument gates pass; adding the fixed 2 DN grain does not increase
the pooled low-pass estimated-versus-oracle error in this rigid integer-motion case. The test also supplies a
concrete counterexample where a lower raw clean-image error accompanies greater temporal error and a departure
from the known exact-motion picture. This narrows the simple grain-amplification hypothesis under its stated
conditions; it does not identify the live-film cause or invalidate the owner's visual judgments.
