# Interpolation methods: explanation, survey and experiment queue

**2026-11-17 — GPT research block.** Primary-source research and local source
review; no new interpolation builds, model inference, GPU tests or playback
benchmarks were performed. The objective is comfortable, sustained 1080p
24→48/60 playback on the Linux Arc A310 NAS and the M5 Cadence machine, measured
separately. 4K is a separate target, not an inference from 1080p.

## What MCI does differently

MCI means **motion-compensated interpolation**. In the broad sense our
bidirectional shaders are also MCI. Here the name refers specifically to the
FFmpeg `minterpolate` block-based backend now integrated into the Cadence test
app. CPU versus GPU is an implementation choice, not the defining distinction.

Both systems estimate correspondence between pictures, move source information
toward the requested time, and combine predictions. The major differences are
the granularity of that correspondence and how competing predictions are rendered:

| Stage | Current High shader | Tested FFmpeg MCI bidirectional configuration |
|---|---|---|
| Estimate motion | Multiscale, fractional dense field, with temporal predictors, propagation and spatial refinement | Integer block vectors; 16-pixel block grid, larger matching support, spatial/temporal search predictors |
| Construct the output | Sample fields, pull pixels from the source pictures, apply the shipped phase-dependent vote/fallback rules | Transport overlapping block predictions and accumulate their weighted source-pixel contributions |
| Spatial freedom | Neighboring locations can move differently, useful for fine motion but able to deform a surface when estimates disagree | Many pixels share a block prediction; neighboring predictions overlap, encouraging coherent patches but permitting blocking, ghosts or blurred boundaries |
| Hardware today | GLSL research path via libplacebo; Metal graph in Cadence | Exact CPU optimizations in Cadence; faithful GPU-renderer experiments also exist separately |

The shirt being calmer with MCI is a real human observation. **Block coherence
is a plausible explanation, not an isolated causal finding**: the estimator and
renderer changed together. The earlier fixed-eight-pixel-patch renderer using
our existing field produced no clear human improvement. That failure remains
part of the evidence; simply making our renderer blockier is not an established
fix. Likewise a field with better numerical accuracy need not produce the most
comfortable image sequence when visibility, blending and temporal consistency
differ.

Two implementation details matter for future experiments. The shipped High uses
`WARP_VOTE=2`. In FFmpeg's **bidir** path, the `aobmc` and `vsbmc` options do not
activate their adaptive/subdivision behavior; those belong to its **bilateral**
path. An option printed in a command line is not proof that its algorithm ran.
See [source comparison and evidence](COMPARISON.md).

The motion-field research remains useful independently. Its physical accuracy
must be tested against known motion, while an interpolator is judged by its
rendered sequence. A learned synthesis network's internal motion is not
automatically a calibrated replacement for the sense-organ fields.

## What is already measured here

The Nov15 Cadence adapter comparison matched stock on **746 selected output
frames**, including YUV pixels, physical timestamps, duration and count.
The actual M5 player's short Bond runs averaged **6.2 ms per output** in both
native doubling and 60-fps modes, with no steady-state skipped/late pictures or
audio gaps. These are existing short-run results, not new measurements or a
general comfort certification. The NAS CPU filter also exceeded real time at
1080p in raw-input tests; its 4K result and a complete streaming pipeline are
separate questions. [G042](../../../CHAT-LEDGER.md#g042--gpt-to-local-cadence-now-runs-exact-accelerated-mci-content-testing-app-installed-2026-11-15),
[review records](../mci_review/REVIEW.md),
[Local's raw-filter results](../mci_fused/RESULTS.md).

MCI is consequently the practical baseline to beat, while the n-frame shader
remains a valuable alternative and diagnostic source. Neither is declared the
eventual winner.

## Candidate pool and suggested order

These are experiments, **not promises of A310/M5 real-time performance**.
Published speeds on different GPUs and resolutions are recorded with their
scope in the linked subreports, rather than combined into a leaderboard.

| Candidate | What it adds to the comparison | Initial disposition |
|---|---|---|
| MCI bilateral / block-size variants | Different search, overlap and subdivision behavior within the existing family | Low integration cost; preserve stock reference and recheck correctness/speed for each supported mode |
| MVTools FlowFPS and BlockFPS | Inspectable CPU motion analysis, visibility masks and two compensation styles | First classical challenger; hold analysis vectors fixed when comparing renderers |
| Classic SVPflow | Established CPU block search plus OpenCL synthesis, including cover/uncover handling | Practical hybrid challenger if available; uniform and adaptive modes are distinct tests |
| RIFE 4.6 and Practical RIFE 4.25/lite | Learned intermediate flow and synthesis | First neural challenger; portable Vulkan baseline plus current lighter model through a verified matching runtime/export |
| IFRNet GoPro | Compact learned joint feature/flow refinement; a second Vulkan implementation | Next neural challenger; verify architecture/export and arbitrary-time checkpoint |
| EMA-VFI-small_t | Inter-frame attention and a multiple-target-time API | Attention challenger; export and actual device placement remain work |
| AMT-S GoPro | Correlation matching and several flow hypotheses | Ambiguous-motion/occlusion challenger; high-resolution correlation cost and noncommercial terms matter |
| M2M / softmax splatting | Forward transport with overlap/conflict handling; motion work reusable across target times | Particularly relevant to 60 fps; cross-vendor port required for the published implementation |
| DIS, then Farneback/TV-L1 hybrids | Independent classical dense-flow estimators | Research components; require an audited visibility/synthesis stage before comparing complete playback |
| FILM | Large-motion learned fusion | Midpoint quality reference for 2×; the released model does not implement exact arbitrary-time 60-fps synthesis |
| GIMM-VFI | Continuous motion functions queried at different times | Motion-model and quality reference; heavier dependencies/memory and restricted license |
| Adaptive kernels: SepConv / AdaCoF | Learn resampling kernels or several offsets and weights rather than one displacement per output pixel | Distinct synthesis-family reference; older CUDA implementations, not a ready Arc/Mac route |
| GMFSS Fortuna | Anime-oriented learned matching/fusion | Animation-specific challenger; not assumed to generalize best to live-action clothing |
| Diffusion: SPEED / RDVFI | Learned image generation or trajectory generation | Research watchlist/quality reference; no verified target-device real-time implementation |

The goal is broad **algorithmic coverage**, followed by depth on promising
methods. Ten RIFE checkpoints are not ten independent approaches. SVP and
MVTools share ancestry; most neural entries still use motion-guided synthesis.

Implementation and primary-source details:

- [Classical methods, GPU APIs and hardware capability checks](CLASSICAL.md)
- [Neural methods, precise checkpoints, runtime routes and published timings](NEURAL.md)
- [Splatting, learned kernels, animation and diffusion](SYNTHESIS.md)
- [Proposed experiment protocol](EXPERIMENTS.md)

Intel VPL interpolation is worth a bounded capability probe, but API/runtime
availability is not evidence that the A310 actually implements it. NVIDIA's
optical-flow engine and NVIDIA-specific FFmpeg `fruc_vulkan` do not supply a
route on our present devices. Details and primary references are in CLASSICAL.

## A consequential 60-fps scheduling distinction

With aligned, exact constant-rate clocks, **24→48 needs 24 synthesized pictures
per second; 24→60 needs 48**, not 36. On a uniform 60-fps grid only 12 of the
original 24 timestamps coincide with output timestamps. Relative positions
within source intervals cycle through `0, 2/5, 4/5, 1/5, 3/5`.

| Exact source → target | Original pictures reusable per second | Newly synthesized pictures per second |
|---|---:|---:|
| 24 → 48 | 24 | 24 |
| 24 → 60 | 12 | 48 |
| 24000/1001 → 48000/1001 | ≈23.976 | ≈23.976 |
| 24000/1001 → 60000/1001 | ≈11.988 | ≈47.952 |
| 24000/1001 → 60 | ≈0.060 | ≈59.940 |

The last row has a 1001-output phase cycle. Changing 60 to 60000/1001 changes the
workload; silently relabeling one as the other is not an acceptable comparison.
These are ideal long-run counts, excluding finite-clip boundaries/cut bypasses,
and assume a shared time origin. They are **not inference counts or GPU costs**:
some models can reuse expensive pair features, and endpoints themselves still
need decoding/presentation. See [exact arithmetic](schedule.py) and its
[generated table](schedule.json).

Midpoint-only models can produce exact doubling. Finite recursive halving
cannot produce the fifths needed by 24→60. A CLI `--fps 60` option may only
change playback speed; source inspection found this in SPEED's current video
runner. FILM also ignores its nominal time argument. Both can still serve as
useful 2× quality references, but must not silently pass a 60-fps timing gate.

## Decision rule

First require the output to represent the right pictures at the right times.
Then assess temporal comfort on the reported Bond actions, translating faces,
bars, pans, occlusions, grain and scene changes, with synthetic ground truth and
blind moving comparisons. A distracting recurring facial or clothing defect is
a rejection even when mean PSNR improves.

Finally require sustained **decode → interpolate → display** on Cadence, or
**decode → interpolate → encode** on the NAS, including transfers and queues.
Averages alone are insufficient: report deadline misses, tail latency, memory,
backlog and sustained behavior. Native 1080p synthesis, downscaled motion
estimation, and downscaled final output are different settings and must be
labeled. Slow but promising methods can motivate optimization, as MCI did;
they are not called deployable before that work succeeds.

The narrow first execution batch is **current MCI + High baselines, MVTools,
RIFE, and IFRNet**. SVP joins if available; attention, correlation, splatting,
kernel and generative methods then expand the coverage. No player default is
changed by this research block.
