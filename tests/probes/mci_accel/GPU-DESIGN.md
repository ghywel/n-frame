# Faithful moving-support renderer, then a separate motion-field hybrid

2026-11-15. Design only; no GPU implementation or speed claim. Initial CPU profiling
now makes rendering the first target; timings and limits are discussed below. Preserve the exact displayed
stock MCI reference that Gareth finds calmer. The fixed 8-pixel, four-picture
overlap test gave no clear visual improvement; it was not this renderer.

Primary source is the local FFmpeg checkout at
`3a5eb948e76dc6390e4b3cff7becf84bc492b7af`:

- `libavfilter/vf_minterpolate.c`: SHA256
  `42e776a33821d7e08a20371a554513bca17ee427aac123ec0923bc4cbefad8e7`.
- `libavfilter/motion_estimation.c`: SHA256
  `24e7f06be0fd01b470f3bb406a5e6ed78f1d286eb03cb7fa314c43b2d26d352b`.

Relevant definitions are `get_sad_ob` (303), `search_mv` (420),
`inject_frame` (735), `ADD_PIXELS` (847), `bidirectional_obmc` (863),
`set_frame_data` (913), and `interpolate` (1077). EPZS is in
`motion_estimation.c` (334); `COST_P_MV` is at 42. These are line anchors in
the pinned source, not claims about a future upstream revision.

## Active algorithm and the two implementation stages

The recorded `me_mode=bidir` uses default EPZS, 16-pixel block spacing,
32x32 matching and overlap footprints, and integer motion. AOBMC and VSBMC are
inactive on this branch despite their values in the command. The renderer combines
**two source-indexed sets of moving supports**. It is not four stationary output-grid
nodes, bilinear vector interpolation, or the current dense A-indexed warp.

1. **Faithful acceleration:** retain stock CPU estimation, frame history, PTS/alpha,
   scene decisions and source pixels; replace only `bidirectional_obmc` plus
   `set_frame_data` with an equivalent GPU gather. Export the actual maps consumed
   at rendering: `frames[2].blocks[].mvs[0]` (B to A) and
   `frames[1].blocks[].mvs[1]` (A to B). Capture source-pair identity and alpha with
   them; exporting the latest estimated array without those identities is unsafe.
   Require byte equality of every output Y/U/V sample, including boundaries and
   retained frames, before calling this an acceleration of the reference.
2. **Changed quality candidate:** feed the same validated renderer block vectors
   derived from our GPU fields. This replaces the estimator/interface adapter and
   needs a fresh visual comparison. It is not a faithful EPZS port. Keep our raw
   measurement fields and sense-organ outputs available independently: a playback
   renderer does not need to replace the scientific motion-field representation.

The first stage can be tested with externally captured vectors and raw source
planes before integrating the filter. Use integer planar YUV buffers/textures and
integer loads; an ordinary RGB libplacebo hook introduces conversion/sampling
differences and cannot silently inherit the byte-equality claim. Transfer, kernel,
decode and encode costs must be measured separately. At 1080p the three stock
per-luma-pixel candidate arrays occupy about 605 MB (577 MiB, ordinary C layouts);
direct gather avoids materializing them, but this alone predicts no speedup.

## Exact gather formula

Let `M=1024`, integer `alpha` be the stock phase, block size `B=16`, and
`b=(B*mb_x,B*mb_y)`. `T(z)=trunc_toward_zero(z/M)` componentwise. For each block:

| Direction, in CPU visit order | Raw vector m | a | Canonical sampling vector v |
|---|---|---:|---|
| 0 | B-to-A vector indexed in B | M-alpha | m |
| 1 | A-to-B vector indexed in A | alpha | -m |

The support origin is `s=b-B/2+T(m*a)` in **both** cases, using the raw vector
before the direction-1 sign change. Its untrimmed size is `2B` on each axis.
The CPU uses clipped, exclusive ranges

`clip(s.x,0,W-1) <= x < clip(s.x+2B,0,W-1)`

and likewise for y. For a contained output pixel `p`, the block weight is the
exact integer table entry `w=obmc_tab_linear[4-log2(B)][p-s]`, using the **unclipped**
origin to index it. A zero table weight does not consume a candidate slot.

The two source offsets and integer weights contributed by this hypothesis are

`dA=clip(T(v*alpha), -p, image_size-1-p),       wA=w*(M-alpha)`

`dB=clip(T(-v*(M-alpha)), -p, image_size-1-p),  wB=w*alpha`.

For luma, sum `wA*A[p+dA] + wB*B[p+dB]` over accepted hypotheses and divide by
the weight sum with stock `ROUNDED_DIV`: for nonnegative values,
`(sum + weight_sum/2) / weight_sum`, using integer division. Each accepted pair's
weights sum to `w*M`. With at most 16 pairs and 8-bit samples, 32-bit integer
accumulation is sufficient (even the conservative w<=255 bound stays below
signed INT_MAX). Do not approximate the table, use bilinear image reads, change
phase rounding, or replace signed division by an arithmetic right shift.

## Cap, order, boundary and chroma semantics

- `NB_PIXEL_MVS=32` means **16 paired hypotheses**, not 32 blocks. Preserve the
  first 16 eligible nonzero-weight blocks in `(direction, mb_y, mb_x)` order.
  Atomic scatter order, strongest-weight selection, or truncating a spatial bin
  before exact per-pixel membership tests changes the picture.
- With no accepted weight, use the unwarped A/B blend with weights
  `M-alpha, alpha`. The clipped exclusive upper bounds above mean the final luma
  row and column receive no block support and use this fallback. Preserve this
  behavior for equivalence; changing it would be a later bug-fix candidate.
- Retained endpoints bypass MCI and copy their source. Scene cuts also bypass it;
  stock chooses A at the exact midpoint (`alpha > M/2` chooses B). Keep the stock
  integer alpha derived from PTS and the same startup/tail behavior.
- `set_frame_data` visits every luma coordinate even when drawing subsampled
  chroma, repeatedly overwriting each chroma pixel. A race-free equivalent assigns
  one GPU invocation per chroma pixel `(cx,cy)`, using the **last** luma visit:
  `x=min((cx+1)*sx-1,W-1)`, `y=min((cy+1)*sy-1,H-1)`, where `sx=2^hsub`,
  `sy=2^vsub`. Gather the candidates belonging to that luma position.
- Clip offsets in luma coordinates first. A chroma source x address is
  `(x >> hsub) + trunc_toward_zero(dx/sx)`, not `floor((x+dx)/sx)`; similarly for y.
  For example x=2, dx=-1, sx=2 gives stock address 1, not 0. Launching all luma
  invocations and letting them race to write chroma is not equivalent.

## Why a bounded gather is valid for stock EPZS

For each search anchor q, `ff_me_search_epzs` sets

`L=max(global_min,q-search_param)`, `U=min(q+search_param,global_max)`.

`search_mv` initializes `mv=q`. The anchor lies within global bounds because the
block grid is `floor(image_size/B)` and the maximum anchor is `(grid_size-1)*B`.
Every possible EPZS update is through `COST_P_MV`: the median predictor, every
candidate in both predictor sets, and every diamond neighbor are checked against
this box before `COST_MV` can replace mv. There is no unguarded update in this
function. Induction therefore proves `|mv-q|<=search_param` in each component.
The always-available zero predictor is in bounds. Acceleration predictors can
exceed the nominal radius, but are rejected if their positions leave the box.
`get_sad_ob` additionally clips its cost-sampling centers; it does not alter the
returned candidate coordinate. Int16 storage preserves the default [-32,32] range.

Thus for a direction with support fraction a, let
`S=floor(search_param*a/M)`. Every support shift component lies in [-S,S]. A
candidate anchor that can contain p must satisfy, independently on each axis,

`p - 3B/2 - S < b <= p + B/2 + S`.

Enumerate integer block indices within this conservative rectangle, intersect it
with the actual block grid, visit them in canonical order, and perform exact
support/table tests. At midpoint with B=16 and search_param=32, S=16: at most
4x4 candidates per direction, or 32 before membership/weight tests. Across all
interior phases the conservative bound is at most 6x6 per direction. A hybrid
field is not automatically bounded by stock search_param: assert its declared
bound or compute a valid larger one. Never silently omit moving supports.

### Dense bounded search versus sorted spatial lists

The bounded loop is the simplest exact first implementation: no atomics, binning,
sorting or inter-workgroup coordination, and a small proved window for this
registered path. Repeated neighboring-pixel tests and divergent early exits may
cost time; workgroup shared-memory caching can be evaluated after correctness.

For large motion bounds or sparse moving supports, tile lists may be preferable.
Emit every `(destination_tile, canonical_block_id)` overlap, group/sort by tile
and canonical ID, and gather the full relevant list. Each pixel still applies
exact support and zero-weight tests, accepting only its first 16 pairs. A list
cap requires an overflow path or refusal, not silent dropping. Unsorted atomic
append lists violate order at the cap; sorting only an already truncated list
does not repair it. Count/scan/allocation/sort overhead and pathological support
collisions are additional costs. Neither approach has measured GPU timings here.

## Exact EPZS acceleration has dependencies

EPZS is not independent block matching. Its current-frame predictors include
left, top and **top-right** block vectors; previous-frame tables include the
collocated vector, a two-history acceleration predictor and neighbors. The
32x32 SAD cost adds `64 * L1(candidate_mv - spatial_median_predictor)`.
Preserve the two history tables and the original scene/startup behavior.

A dependency-respecting block wavefront has rank `mb_x + 2*mb_y`: left and
top-right have rank one lower, top rank two lower. The usual `x+y` diagonal is
incorrect because top-right is on the same rank. Directions can use independent
contexts. Parallelize integer SAD reductions and candidate evaluation only while
preserving the sequential search decisions and tie order: median first, predictor
set 0 in insertion order, predictor set 1 in insertion order, then each diamond's
left/up/right/down. Updates use strict `<`, so the first equal-cost candidate wins.
Each diamond iteration is centered on the prior iteration's selected position.

There are many short wavefronts; dispatch, synchronization and occupancy costs
are unmeasured. CPU-orchestrated per-block GPU launches may cost more than they
save. All-block independent search, a changed predictor schedule, exhaustive SAD
search, inserted GPU predictors or a different regularizer are **new algorithms**,
even if their vector costs improve. They need quality gates, not an equivalence
label. Profile before choosing to port this stage.

## Narrowest hybrid comparison after renderer equivalence

Keep two rows: stock CPU vectors -> faithful GPU renderer, and GPU-derived vectors
-> that identical renderer. Keep the exact displayed stock clip alongside both.
Predeclare the dense-to-block adapter (sampling point/region, integer rounding,
search bound, and coordinate units) and calibrate it on known translations before
film. These adapter choices are part of the quality candidate. Actual independent
A-to-B and B-to-A source-indexed fields are required: `-F_AB(p)` is not generally
`F_BA(p)`. Current pruned High omits its unused B-to-A chain; restoring it and
verifying its indexing/cost is explicit work, not a free existing input.

This comparison isolates replacing the motion provider plus its declared adapter
while preserving the renderer. It cannot separate defects within that adapter
from defects in the GPU estimator. If a further minimal renderer ablation is
needed, keep the stock vectors and all arithmetic but freeze only support origins
instead of transporting them; that tests moving support contribution directly.
It is a changed renderer, not the failed 8px four-picture implementation and not
a faithful-acceleration result. No comparison is yet run or visually approved.

## Concrete first prototype after CPU profiling

The initial cached full-1080p shirt profile reports approximately 4.31 s ME,
8.18 s overlap construction and 10.63 s output: rendering accounts for about
81% of these three stage timers. This motivates the renderer split; it does not
measure GPU performance. Even instantaneous rendering would leave ME and all
other pipeline costs. The stage-only ideal ceiling is about 5.4x, before transfers,
packing, synchronization, decoding and output overhead; it is not a forecast.

Read-only local inspection on this date finds an Apple M5 with ten GPU cores,
Metal 4 support, Swift 6.4.2 targeting arm64, and an available Xcode Metal compiler.
The project also has libplacebo 7.377.0 built with Vulkan and shaderc, Vulkan
loader 1.4.357, and MoltenVK 1.4.2. This is toolchain/device inventory only: no new
device allocation, compute dispatch or GPU benchmark was performed for this note.
Eventual Arc execution remains a separate build/device/measurement gate.

### A capture that preserves the real input to the renderer

Add an opt-in exporter to an isolated stock/profiling build, leaving its renderer
active. At `interpolate`, after alpha is known, capture a bounded, explicitly
selected set of outputs. For MCI interior outputs capture immediately before
`bidirectional_obmc`, and retain the original CPU result after `set_frame_data`.
Run the complete short source history so EPZS state stays unchanged; select
records for export rather than truncating the input history.

Each capture needs source A/B identity and PTS, output PTS/time base/alpha,
scene-cut/endpoint decision, width/height/pixel format/chroma shifts, B and search
bound, both consumed block-vector arrays, and the exact selected overlap table.
Serialize fields explicitly with a schema and endianness: do not dump C `Block`
structs, which contain padding and pointers. Copy active source-plane row bytes
using their actual signed linesizes, removing allocation padding; record each
plane's dimensions and byte count. Save the CPU output planes in that same format.
Hash the inputs, vectors, table, output, exporter source and binary. The vectors
and integer table suffice to reconstruct the pixel weights: exporting stock's
hundreds of megabytes of per-pixel lists is unnecessary. A few selected CPU
candidate lists can serve as additional correspondence diagnostics.

The first corpus should include the already inspected shirt pairs, one suit pair,
and the synthetic cap/border/negative-motion controls; then extend to the full
exactness fixtures. Explicitly include non-midpoint alpha, cuts and endpoint
copies before extending the equivalence claim beyond native doubling. Do not
replace the existing source clips or the displayed stock reference.

### Preferred portable runner: C plus libplacebo's low-level compute API

The installed public API already exposes the needed route in
`libplacebo/gpu.h`: `pl_buf_create/write/read`, `PL_DESC_BUF_STORAGE`,
`pl_pass_create` with `PL_PASS_COMPUTE` and GLSL source, `pl_pass_run`, timers and
`pl_gpu_finish`. `libplacebo/vulkan.h` supplies `pl_vulkan_create`; this uses Vulkan
through MoltenVK here and can use native Vulkan on the Arc machine. This route
does **not** call `pl_render_image`, RGB conversion, a FRAME_MIX hook or video
color management. Require a real selected GPU and fail if it is unavailable;
record the device/driver and reject silent software execution.

For the simplest portable proof, represent each 8-bit source/output value as one
uint32 in a storage buffer, with int32 block vectors and uint32 table entries.
This avoids assumptions about 8-bit storage-buffer extensions or R8 integer image
support. It costs four times the plane-buffer traffic and needs explicit host
packing/unpacking; report that cost. It is a correctness-first representation,
not an optimized memory plan. Separate per-plane dispatches give each output
sample one owner, including chroma's required last-luma representative. Validate
buffer/workgroup limits and shader creation; wait for completion, validate all
output words are in [0,255], repack, and require exact CPU-golden bytes.

Compile/create the pipeline once and reuse source/frame/vector buffers. First
measure compilation separately from warm replay, then record pack/upload,
dispatch, completion/download and unpack times as well as end-to-end replay.
The next integration can call this module from the isolated filter at the same
render site, retaining CPU ME and source ownership. Cached source-frame uploads
and GPU encoder integration are later work; offline replay timings omit live
pipeline costs and cannot establish realtime playback.

### Is Swift/Metal a sensible first proof?

Yes, as a bounded native-Mac alternative if the portable runner encounters setup
friction. Swift can create an `MTLDevice`, reusable buffers and a compute pipeline,
submit one integer gather per plane, wait for command completion, and compare the
same captured CPU bytes. Use the same explicit integer buffer layout and corpus.
The available compiler and device make that implementation plausible, not tested.
It would prove the kernel on this Metal path only; translating it to GLSL/Vulkan
and repeating the exactness gate remains necessary for Arc. Given the project's
already installed low-level Vulkan/libplacebo stack, the portable runner is the
recommended first implementation rather than maintaining two kernels immediately.

The next block is therefore exporter plus portable standalone replay, with exact
all-plane equality as its first result. Optimizing the proven renderer and
substituting GPU motion fields come afterward, as separate timing and quality
experiments. Stock CPU estimation remains useful while those stages develop;
none of this retires the motion-field sense organ.

## CPU adversarial controls

`gather_controls.py /path/to/ffmpeg/libavfilter/vf_minterpolate.c` reads the pinned
overlap tables and compares an explicit ordered scatter/list reference with the
bounded gather on small synthetic fields. It checks negative odd motion, several
phases, borders, non-multiple block dimensions, cap collisions, and chroma's last
writer. Its assertions establish the declared CPU formulas on those constructions;
they are not execution of the C filter, GPU validation, film evidence or speed
measurements. A GPU port must additionally pass the captured stock vectors and
full planar-pixel reference, not just this self-contained formula comparison.
