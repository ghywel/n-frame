# Classical and hardware-assisted interpolation survey

Survey date: **2026-11-17**. Targets: Intel Arc A310 on Linux and Apple M5 on
macOS; 24→48/60 and corresponding 24000/1001 rational rates.

This is a primary-source survey, not a benchmark. No candidate was installed,
built or executed for this survey. No source located establishes measured
1080p/4K playback performance on our A310 or M5. Links to moving branches and
current documentation must be pinned to revisions when an experiment begins.

## Working shortlist

| Candidate | Complete interpolator? | Execution path and present evidence | Priority |
|---|---|---|---|
| MVTools FlowFPS / BlockFPS | Yes | CPU; inspectable vectors, masks and synthesis. Current VapourSynth build has x86_64 and aarch64 paths. No local performance result. | First open comparison |
| Classic SVPflow | Yes | CPU block matching plus OpenCL synthesis; closed-source renderer. Official Linux/macOS distributions. | Established hybrid comparison |
| OpenCV DIS / Farneback / TV-L1 | No: flow fields | CPU and conditional OpenCL paths. A synthesis/visibility stage is still required. | New-estimator research |
| Intel VPL classical/AI FRC | Optional API; actual support unknown here | A310/DG2 runtime support does not establish interpolation support. Must query and verify output. | Bounded capability probe |
| NvOFFRUC / FFmpeg fruc_vulkan | Yes, NVIDIA-specific | CUDA-assisted proprietary FRUC or independent Vulkan synthesis using NVIDIA optical-flow hardware. | Reference, not an A310/M5 route |

SVP and MVTools share ancestry. They are useful implementation comparisons,
but should not be counted as completely independent estimator families.

## MVTools: inspectable compensation and visibility controls

`FlowFPS` uses bidirectional pixel compensation with occlusion masks.
Its modes are easy to misdescribe: `mask=0` already uses simple occlusion
masks; mode 1 adds zero-motion substitution; mode 2 incorporates adjacent-frame
vectors. `BlockFPS` uses partial block compensation, documented as generally
faster but susceptible to blocking and blended uncovered borders.
`Mask(kind=1)` exposes SAD; `kind=2` estimates occlusion from positive neighboring
motion differences. These are diagnostic heuristics, not calibrated certainty.
The output rate accepts a rational numerator/denominator.
[Author's filter documentation](https://github.com/pinterf/mvtools/blob/mvtools-pfmod/Documentation/mvtools2.html).

The VapourSynth port is multithreaded and its current build includes an aarch64
path. This makes a native M5 test plausible; it does not establish that a
specific binary works or meets real-time deadlines.
[VapourSynth MVTools](https://github.com/dubhatervapoursynth/vapoursynth-mvtools),
[build configuration](https://raw.githubusercontent.com/dubhatervapoursynth/vapoursynth-mvtools/master/meson.build).

Useful experiment: hold the analysis/vector clips fixed, compare FlowFPS
`mask=0` versus `mask=2`, then BlockFPS. This separates synthesis/visibility
behavior from changes to the estimator.

## SVPflow: a practical CPU/GPU hybrid

Classic `SVAnalyse` performs hierarchical block matching. Ordinary GPU
acceleration concerns rendering; NVIDIA optical-flow mode replaces the search
through a separate API. `SVSmoothFps` supports rational rates. Algorithms 13,
21 and 23 add dynamic median handling, cover/uncover masks and adjacent-frame
vectors respectively. Its adaptive scene mode can intentionally reduce
interpolation when vectors look unreliable. Register uniform and adaptive modes
separately: calmer clothing could partly reflect endpoint copying.
`svpflow1` is GPL; `svpflow2` is a closed-source renderer.
[Official SVPflow specification](https://www.svp-team.com/wiki/Manual:SVPflow).

Official desktop distributions support Linux and macOS. No primary evidence
found here establishes a Vulkan backend for classic **desktop** SVPflow:
documented Vulkan fallbacks concern Android; RIFE is a separate engine. Current
Linux distribution requires a license. Compatibility and advertised 60 fps
playback are not measurements on our hardware or resolution.
[Linux](https://www.svp-team.com/docs/linux/),
[Mac](https://www.svp-team.com/docs/mac/),
[release history](https://www.svp-team.com/news/).

## Dense flow: useful components, incomplete playback systems

OpenCV DIS has an OpenCL dispatch when the output is a `UMat`, patch size is 8,
and spatial propagation is enabled. Farneback also has a conditional OpenCL
path. TV-L1's OpenCL dispatch is explicitly excluded under `__APPLE__`.
Record the actual backend/device and detect CPU fallback; requesting `UMat`
does not itself prove GPU execution.
[DIS source](https://raw.githubusercontent.com/opencv/opencv/4.x/modules/video/src/dis_flow.cpp),
[Farneback source](https://raw.githubusercontent.com/opencv/opencv/4.x/modules/video/src/optflowgf.cpp),
[TV-L1 source](https://raw.githubusercontent.com/opencv/opencv_contrib/4.x/modules/optflow/src/tvl1flow.cpp).

**Published measurement, not local extrapolation:** the DIS paper reports
1.65 ms and 3.32 ms at 1024×436 for two operating points on one i7-3770K core
at 3.50 GHz. Training-set timing excludes disk access, pyramid/gradient
construction and initialization; the fast operating point finishes at a coarse
scale. These are flow-estimation timings, not 1080p interpolation, M5 results,
or complete 24→60 playback.
[DIS paper, §3.1 and supplement C](https://arxiv.org/pdf/1603.03590).

Inference: DIS is a worthwhile independent estimator experiment because it
combines inverse-compositional patch search, normalization and variational
refinement. Making playback still requires bidirectional fields, visibility,
source-grid transport, hole/conflict resolution, chroma/range handling and exact
temporal scheduling. Simply scaling a forward field at output coordinates is
not a complete or generally correct renderer. Compare field accuracy before
attributing any synthesis improvement to the estimator.

## Intel: test capability before promising acceleration

The VPL GPU runtime lists DG2/Alchemist among supported platforms.
That does not establish support for motion interpolation.
The classical FRC contract allows `MFX_FRCALGM_FRAME_INTERPOLATION` to be
replaced with simple conversion, returning
`MFX_WRN_INCOMPATIBLE_VIDEO_PARAM`. Inspect both status and the returned
algorithm; fail the interpolation capability test if the requested algorithm
was changed.
[Runtime support](https://github.com/intel/vpl-gpu-rt),
[FRC query contract](https://intel.github.io/libvpl/v2.10/API_ref/VPL_structs_vpp.html#mfxextvppframerateconversion).

Current VPL also defines `mfxExtVPPAIFrameInterpolation`, whose separate query
can return unsupported. No primary source found here confirms working support
on the A310 Linux stack. Nor was a confirmed public A310 equivalent of NVIDIA's
dedicated optical-flow-vector API located. These are unresolved availability
questions, not proof that all Intel hardware lacks such functionality.
[Current API structures](https://github.com/intel/vpl-gpu-rt/blob/main/api/vpl/mfxstructures.h).

## NVIDIA: distinguish the engine, proprietary FRUC and open Vulkan synthesis

NvOFFRUC combines the optical-flow engine with CUDA synthesis, but NVOFA itself
also exposes Vulkan. Current upstream FFmpeg has an independent `fruc_vulkan`
renderer requiring `VK_NV_optical_flow`; its source rejects devices lacking
that extension. Thus “all NVIDIA interpolation is CUDA-only” is outdated.
These NVIDIA-specific routes do not provide an A310/M5 implementation, though
the open synthesis code is a useful reference.
[NvOFFRUC](https://docs.nvidia.com/video-technologies/optical-flow-sdk/nvfruc-programming-guide/index.html),
[NVOFA interfaces](https://docs.nvidia.com/video-technologies/optical-flow-sdk/nvofa-programming-guide/index.html),
[FFmpeg implementation](https://ffmpeg.org/doxygen/trunk/vf__fruc__vulkan_8c_source.html).

## Prioritized proof plan

1. **MVTools:** fixed analysis; FlowFPS masks 0/2 and BlockFPS. Save vector,
   SAD and occlusion diagnostics with the output.
2. **SVP classic:** export exact settings and device selection; compare
   algorithms 13/21/23, with uniform and adaptive interpolation distinguished.
3. **A310 VPL:** query classical and AI interpolation first. If accepted,
   render known translating geometry and prove inserted frames are correctly
   located rather than duplicated endpoints or ordinary blends.
4. **DIS hybrid:** test known translations and nonrigid motion fields first;
   add synthesis only after field/coordinate controls pass. Keep this separate
   from rankings of complete interpolators.

Reuse shirt/suit, translating faces, bars, fast pans, occlusions and cuts.
Pre-register settings before inspecting holdouts. Validate process success,
decoded sample counts, exact rational timestamps, pixel format/range and source
alignment. Test 24→48, 24→60, 24000/1001→48000/1001 and the intended 60/60000/1001
choice explicitly; those schedules are not interchangeable.

Record endpoint-copy fractions alongside quality so “less rippling” cannot
silently mean less interpolation. Warm the pipeline and report estimation,
synthesis, transfer and total time separately, together with actual input and
output resolutions/rates, unique synthesized frames and the selected device.
Do not convert flow-pair throughput or vendor compatibility into a claim of
real-time playback.
