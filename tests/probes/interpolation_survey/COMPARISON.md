# Current High, FFmpeg MCI, and a discriminating benchmark

Read-only source/evidence review, 2026-11-17. Reference commits: n-frame `3a5b785`,
Cadence `fcfbec2`. No new rendering, timing or human viewing is claimed here.
Paths below are relative to the named repository. Current High is
`shaders/bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut.glsl`.
The separately named `-cut-vote.glsl` is the older WARP_VOTE=1 experiment; it is
not the current WARP_VOTE=2 High default.

## The two pipelines make different assumptions

| Component | Current n-frame High | Cadence's FFmpeg MCI backend |
|---|---|---|
| Representation | Spatially dense motion at pyramid resolutions; final base A→B field at half resolution, sampled continuously. Reverse quarter-resolution flow contributes to the final vote. | One integer displacement per 16-pixel block-grid position and direction. Matching and overlap each have a 32×32 footprint at this block size. |
| Matching | Luma pyramid at 1/16, 1/8, 1/4 and 1/2; multiple coarse basins, previous-window seed, dominant global shift, local SAD refinement. | Full-resolution luma SAD over overlapping support, with a penalty for displacement away from a spatial predictor. EPZS searches predictor candidates then a local diamond. It is not an exhaustive search or a variational optical-flow solve. |
| Spatial regularization | Contrast-weighted propagation, edge-weighted variational updates, vector medians; additional alias, outline-adoption and print-lattice machinery. Current forward branch has eight quarter-level and four half-level variational passes. | Spatial predictor and penalty, a piecewise-translating block representation, and fixed overlap windows during reconstruction. There is no separate dense-flow smoothing stage in this active path. |
| History | Previous-window storage seeds and a temporal-distance penalty, accepted only where a forward/backward round trip supports the prior. Two image endpoints does not mean memoryless estimation. | Four AVFrame slots and two previous motion-vector tables. EPZS proposes current left/top/top-right, prior collocated and adjacent vectors, and an extrapolated prior vector. Four buffered pictures does not mean a cubic four-frame trajectory fit. |
| Photometric change | GLOBAL_GAIN=2 estimates accepted global gain/offset for matching; the final picture uses original endpoint colors. | This active SAD path compares the luma values directly; it does not include High's global gain/offset compensation. |
| Reconstruction | Mainly a pull from each endpoint using one A-indexed field read at the output pixel, then a temporal color blend. WARP_VOTE=2 can blend in a different candidate warp, and a coherence gate can blend toward unwarped endpoints. | Fixed-window bidirectional overlapped block compensation accumulates several endpoint contributions, normalized by their total weight. Integer phase-scaled displacements and sample quantization are part of the algorithm. |
| Cut treatment | Global change must also remain unexplained by final motion before the cut branch selects an endpoint. | Its scene-change detector selects an endpoint instead of MCI at declared cuts. Different cut policies are another confound in an uncontrolled comparison. |
| Present app path | Metal graph, with optional animation-cadence preprocessing. | CPU MCI, mask51, decoded YUV into eight-bit YUV420 and NV12 display output. The n-frame animation-cadence stage does not run here. |

Source anchors:

- **High:** its generation declaration at line9; previous-window gate/cost at
  1371–1473; representative edge-weighted variational update at 4463–4505;
  half-level SAD refinement at 5020 onward; coherence at 5465; final vote at
  5539; final reconstruction at 5690–5722. The source comments are historical
  explanations, not a substitute for reading the current executable branches.
- **FFmpeg:** `libavfilter/vf_minterpolate.c`, `get_sad_ob`, `search_mv`,
  `inject_frame`, `bidirectional_obmc`, `ADD_PIXELS`, `set_frame_data`, and
  `interpolate`; `libavfilter/motion_estimation.c`, `ff_me_search_epzs`.
  In the unpatched 9.0.2 release these start at approximately 301,417,733,858,
  842,911,1072 and motion_estimation.c:333. Cadence's release-specific patch is
  `MediaStack/mci-9.0.2.patch`; its preservation claims and repairs are in
  `MediaStack/MCI.md`. The active cost includes
  `64*(abs(mvx-predx)+abs(mvy-predy))` in addition to 32×32 SAD.
- **Cadence binding:** `Player/Sources/Cadence/Bridging/CadenceMCI.c:57` sets
  `mi_mode=mci:me_mode=bidir:me=epzs:mb_size=16:search_param=32`;
  `Player/Sources/Cadence/MCIEngine.swift:70` defaults to mask51.
  `MCI-CONTENT-TEST.md` and `MediaStack/tests/MCI-BRIDGE.md` record measured scope.

Two easy misdescriptions should be excluded:

1. Although the command contains `mc_mode=aobmc:vsbmc=1`, **adaptive overlap and
   variable-size subdivision do not execute in this bidirectional path**. Their
   branches belong to bilateral estimation/output. The active overlap weights
   come from fixed `obmc_tab_linear`. See the branch audit in
   [ripple/RESULTS.md](../ripple/RESULTS.md#positive-playback-control-and-next-discriminating-experiment).
2. High's explicit final SAD-valley `SUBPEL_REFINE` is **0**, around line5096.
   It is still capable of fractional flow through coarse fractional search,
   variational updates and field interpolation. Do not attribute its behavior to
   an enabled equiangular/parabolic subpixel fit merely because that code/comment
   is present.

MCI's acceleration changes cost, not the intended motion/reconstruction model:
SIMD SAD, fused overlap accumulation and dependency-preserving EPZS wavefront
jobs retain candidate order, caps and integer output. Exactness is established
on registered cases, not by the option's name. See
[mci_fused/RESULTS.md](../mci_fused/RESULTS.md), and the actual application bridge's
746-frame pixel/PTS/duration/count gate in Cadence's `MediaStack/tests/MCI-BRIDGE.md`.

## Why calmer MCI is plausible, and what is actually established

A larger matching support, fewer independently varying parameters, a predictor
penalty and overlapping rigid contributions can suppress locally changing warp
shape in weakly textured material. High can express finer nonrigid motion, but
also finer errors. Different fractional sampling and temporal state can alter
texture/grain appearance. These are testable mechanisms, **not an identified
cause of the reported film defect**. A calmer picture can also come from loss of
detail; comfort, correspondence accuracy and sharpness need separate readings.

The recorded human result is narrower: Gareth confirmed the native shirt ripple
and found the independent MCI shirt playback noticeably calmer than current High.
There is no corresponding human suit verdict in that block. Both estimator and
renderer changed in this comparison. Exact CPU reproduction and checked midpoint
crops ruled out whole-crop endpoint holds at those samples; they did not prove
accurate motion at every pixel or establish universal superiority.

The attempted **same-field rigid-patch/overlap renderer** is already a negative
control: it improved withheld-truth scores modestly, but Gareth found no clear
native-shirt improvement. It was rejected as a remedy. It is not identical to
FFmpeg's estimator, 16-pixel grid, 32×32 overlap, ordering and cap. Its failure
shows that this particular rendering change was insufficient, not that all
renderer changes fail or that a different estimator is logically necessary.
See [ripple/RESULTS.md](../ripple/RESULTS.md), especially the intervention and
positive-control sections, and [ripple/OBMC.md](../ripple/OBMC.md).

The fixed photographed-plane experiment also remains a useful negative result:
known integer translation plus independent 2-DN grain did not amplify the pooled
Gaussian-2 field-choice error. It did not reproduce the severe film ripple.
Moreover, estimated motion scored better than exact motion against the clean
noisy-image target at raw scale, while the low-pass ranking reversed. Therefore a
better image score is not proof of a better motion field. See
[ripple/RIGID-RESULTS.md](../ripple/RIGID-RESULTS.md).

For a rigid texture with true displacement d but used displacement d+δ, the two
endpoint pulls sample material positions `s−tδ` and `s+(1−t)δ`, separated by δ.
At the midpoint a sinusoid of period P has contrast multiplied by
`cos(πδ/P)`. A shared vector does not guarantee coherent endpoint content.
Independent source grain also loses variance under temporal blending even with
exact flow. These constructions distinguish possible mechanisms; neither alone
identifies the live-film cause. See [ripple/GEOMETRY.md](../ripple/GEOMETRY.md).

## Source-rate motion fields are a separate product

Displaying fewer invented pictures does not make a correspondence field useless.
The field can support measurements, diagnostics and hypotheses independently of
which renderer gives the more comfortable video. Its value must be established
against known motions, observability limits, uncertainty and calibration, rather
than inferred from an interpolation score.

Important scope for this particular High shader:

- `READ_FIELD` at5754–5764 reads `FLOW_H_AB * 2`, in full-resolution pixels per
  source interval, sampled at 1/8 resolution. Its comment explicitly says the
  two-frame family has one flow, so every mode reads velocity. Generic
  `read_view` labels 2/3/5/6 do not manufacture acceleration or jerk in High.
  Derivative claims require the appropriate multi-frame construction and tests.
- This is the **base forward field**, before the phase-dependent final vote and
  color blending. The rendered picture need not correspond to one unique
  displacement field after those mixtures.
- A displacement field is apparent image motion, not automatically physical
  three-dimensional velocity. Aperture, periodic texture, illumination changes,
  occlusion and sampling can leave motion ambiguous. Physical units and temporal
  derivatives require known scale/time conventions and the relevant calibration.
- Source-rate diagnostics must actually execute the estimator. Cadence's ordinary
  Off/1:1 playback bypass is not itself a field-reading pipeline, and MCI playback
  does not currently consume n-frame fields in parallel.

## Benchmark design: two complementary questions

### 1. Picture quality and comfort

Use a small prespecified development set and a separate held-out set. Include:

- Static and slow controls; horizontal/vertical/diagonal bars across several
  periods and subpixel phases; large positive/negative pans; rotating textures.
- A moving face or photographed plane against independent background motion,
  facial features and silhouette scored separately; crossing objects and rails.
- Frozen photographed material under exact translation, then separately registered
  invertible deformation/strain. Cross clean texture, frozen grain and independent
  temporal grain; vary exposure/blur and global/local light independently.
- Cuts, dissolves, large displacement, repeated textures and textureless ramps as
  separate challenge classes. Some are intrinsically ambiguous; retain an unknown
  result rather than redefining the ground truth to favor one algorithm.
- Native short film, television, animation, CG and sports-like motion windows.
  Include the confirmed shirt/suit windows as regressions without making them the
  tuning set for every new method. Cache bounded clips once; no full-film scans.

Existing starting points are [motionstress/scenes.py](../motionstress/scenes.py),
[motionstress/photo.py](../motionstress/photo.py),
[ripple/rigid.py](../ripple/rigid.py), the established ladder and the photometric
fixtures. The photographed-plane/face proxies have continuous resampling truth,
but do not model actual 3D facial movement, cloth visibility or newly exposed
texture. Preserve those limits.

Compare mechanisms, not a list of nearly identical implementations: hold and
linear blend controls; faithful block MCI; a distinct classical flow/phase or
block formulation; learned flow plus warping; learned resampling/kernel/splat
methods; an end-to-end learned interpolator. Pin actual weights, source versions,
precision, resize/padding, cut policy and arbitrary-time capabilities. The survey's
classical/neural research supplies primary-source candidates; none is declared a
winner without the same inputs and viewing gate.

Measure whole-image and ROI error, gradient/edge error, tails and worst localized
tiles. Use exact material-coordinate registration on synthetic scenes and only
source-derived, independently checked registration on real footage. Report
texture interiors and moving boundaries separately. For temporal behavior, use
pixelwise residual/curvature on **all output instants**, including transitions
through retained-source instants. Mean absolute error change can miss a moving
ripple; inserted-only stability can miss constant defective insertions alternating
with intact originals. The existing real-shirt tracker stops when ambiguous;
its later frames must remain unknown. See [ripple/TEMPORAL.md](../ripple/TEMPORAL.md).

Human review should use videos at the intended output rate, repeated with
randomized method labels/order, matched color/scale and an optional smooth truth
reference where one exists. Score temporal shape stability, moving-boundary
artifacts, face/detail preservation and overall comfort separately; allow ties
and inability to judge. Inspect flagged crops as well as the whole frame.
A metric win does not override a reproduced visible defect. Still images alone
cannot establish whether the reported ripple is fixed.

Keep native interpolation separate from leave-one-out reconstruction: selecting
frames1/3 to predict2 doubles the motion interval relative to native playback.
It is a truth-bearing stress test, not a substitute for native-rate human review.
Synthetic ground truth should state whether images are instantaneous or exposure
integrals. Sampling sharp high-frame-rate video is not automatically equivalent
to a film camera's longer exposure.

### 2. Exact timing, scheduling and practical cost

For exact24→60, source time is `2k/5` at output index k. The phase sequence is
`0, 0.4, 0.8, 0.2, 0.6`, repeating across two source intervals. There are no
midpoint outputs, and only every second original frame lies on the output grid.
A finite recursive-midpoint construction cannot exactly produce fifths. Require
native arbitrary-time evaluation or explicitly label the approximation and its
extra interpolation/resampling cost.

`24000/1001→60` is a different schedule: source time advances by `400/1001` and
phases cycle over1001 outputs, about16.68 seconds. `24000/1001→60000/1001` has the
same 2/5 pattern as24→60. Exact doubling and literal fixed48 must likewise not be
conflated for NTSC-rate material. Use rational timestamps and an end-exclusive
presentation interval, with startup, terminal padding and retained-source identity
checked separately. Cadence's bridge already caught and repaired a coarse-time-
base change to FFmpeg's integer alpha; retain that regression.

Test animation cadence independently: actual held drawings, mixed live-action
backgrounds, and periodic movement that resembles repeated frames. Give every
method the same explicitly declared scheduling/preprocessing policy, or report
that policy as a separate pipeline. Do not assume a midpoint model, frame
interpolator or optical-flow field is also a cadence detector.

Report at least three cost levels:

1. Estimation/representation work per source pair, and synthesis cost per requested
   phase, including cache reuse. At24→60, pairs alternate between three and two
   output timestamps; one midpoint timing is not the full schedule.
2. Complete processing pipeline: decode, normalization, transfers, interpolation,
   postprocessing, and output/display conversion. Record memory, CPU work, GPU
   time and wall time separately, warmups and serial interleaved repetitions.
3. Playback: sustained throughput, late/left-out frames, audio gaps, queue depth,
   lookahead/startup latency, seek/retarget interruption, thermal behavior and
   fallback frequency on each target device.

At24 fps a source interval is41.67ms; a60Hz display interval is16.67ms. A reusable
pair estimate need not be recomputed every display tick, while a slow burst can
still miss display deadlines despite a good average. Temporal lookahead also adds
latency independently of arithmetic throughput. FFmpeg currently buffers four
pictures (including the startup clone) and outputs an interval with the following
picture available; that is not the same latency contract as a two-endpoint graph.

Do not compare Local's roughly4.5ms **filter work per source pair** directly to a
High **per-output** graph timing or an app's frame mean. The research FFV1/MD5
pipeline became decode-bound after acceleration. The short Cadence application
runs are stronger integration evidence, but not a sustained all-content claim.
The test app records steady MCI playback without late pictures on the measured M5
clips and separately records interruptions during retarget/stall recovery.

Before scoring, require process success, backend identity, complete frame and
physical-PTS counts, color/range agreement, and source alignment. Negative controls
should include a held-frame impostor, wrong phase/sign, one altered luma/chroma
sample, truncation and a deliberately wrong backend. Preserve failures and exact
input/model/binary/command provenance. No method may gain an apparent quality or
speed advantage by silently dropping outputs, resizing, changing cadence or
substituting a fallback.

## Causal experiments that could discriminate the mechanisms

- Extend the existing rigid oracle-versus-estimated High experiment with one
  registered subpixel translation, then one known invertible deformation. Keep
  exact material coordinates and the same conversion/resampling pipeline; do not
  simultaneously add grain, deformation, occlusion and a new renderer.
- Cross oracle/estimated fields with renderer choices where the representations
  are genuinely compatible. Uniform rigid translation is the cleanest common
  case. Sampling a dense field onto blocks changes the representation; record
  that operation and its oracle approximation error rather than call it an
  unchanged estimator.
- In the block pipeline, change one of support size, predictor penalty/history,
  subpixel representation or overlap policy at a time, with fixed cut/color/
  scheduling rules. In High, separate field estimation from inverse-coordinate
  sampling, phase-dependent voting and coherence fallback. Register expected
  local error/temporal changes before seeing the films.
- Retain the already rejected 8-pixel same-field patch renderer and the grain
  negative result. A new causal story must explain those outcomes, not erase them.

These tests can establish whether a particular change reduces the specific
failure under controlled conditions. A broad architecture comparison by itself
cannot identify the unique cause of the garment ripple.
