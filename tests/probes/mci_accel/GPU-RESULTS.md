# Faithful GPU replay of the stock MCI renderer

2026-11-15. A standalone integer Vulkan compute renderer now consumes the actual
CPU-estimated vectors and source planes used by FFmpeg. This is a first hybrid
component: CPU motion estimation, GPU picture construction. It is not yet an
FFmpeg playback filter or a change to Cadence.

## Correctness and its boundaries

The original registered matrix contains 21 captured scalar render invocations:
13,806,027 Y/U/V sample positions across the captures, each replayed once for
warmup and three measured repetitions. It covers block sizes 4/8/16, 420/444 chroma, odd boundary
dimensions, bars, faces, grain, rigid translation, static frames, panning and
five integer phases 204/409/512/614/819. The complete capture streams also match
the previous scalar reference frame records; only selected inserted frames are
replayed on GPU. Golden images remain exclusively on the CPU.

Both **Apple M5 and Intel Arc A310 pass all 21 original captures and the separate
shirt draw 60**, with byte equality across all planes. Both direct and staging
readback paths pass their full selected matrices and GPU fault controls. Original
CPU reference certifications, raw capture frames, device logs and result hashes
are re-audited in [gpu-measurements.json](gpu-measurements.json); source/build
identities are in [gpu-build-provenance.json](gpu-build-provenance.json).
The supplemental frame brings coverage to 22 captured invocations and 16,916,427
sample positions per hardware/path matrix; repeated replays are not extra frames.

The initial shirt sample, draw 30/output 59, precedes the owner's reported 202–204s
movement. An independent review caught this selection boundary. It remains in
the original matrix, and a separately registered draw 60/output 119 sample adds
the shirt movement at nominally about 202.5s. No frame was substituted or discarded.
The suit sample is draw 60/output 119. These are correctness/portability samples,
not a newly reviewed temporal comfort result or an entire GPU film sequence.

Capture only executes inside the actual MCI drawing branch. Endpoints and scene
cuts bypass it, including in the fixture named `cut`; their GPU handling is
therefore **not validated** by this matrix. The cap/order collision adversary
remains a CPU formula control. The GPU preserves the implemented cap/order, but
this block does not claim a deliberately overflowing GPU cap fixture was run.

## Deliberate failures

The host validators reject malformed lengths, offsets, values, bounds, weights,
PTS/phase relationships and stock-int64 overflow. Real GPU controls require a
valid positive replay, then detect all three interventions:

- A structurally valid changed golden: explicit GPU mismatch after dispatch.
- XOR1 applied to the shader's final sample: explicit GPU mismatch.
- Removed shader output write: the prefilled poison survives and is rejected.

The runner verifies all output words rather than stopping at the first error.
Hardware device identity, actual dispatch count and sample count are required;
a setup failure cannot count as successful fault detection. Output is poisoned
before every positive correctness iteration too.

## Timing interpretation

| Hardware / path | Sample | Upload + poison ms | Dispatch + wait ms | Download ms | Total replay ms (range) |
|---|---|---:|---:|---:|---:|
| M5 / staging | shirt draw 60 | 0.803 | 6.704 | 0.551 | 10.854 (10.159–11.212) |
| M5 / staging | suit draw 60 | 0.772 | 6.219 | 0.959 | 10.734 (10.678–11.432) |
| Arc / direct | shirt draw 60 | 20.478 | 18.620 | 615.339 | 654.764 (628.986–690.415) |
| Arc / direct | suit draw 60 | 20.255 | 19.458 | 619.829 | 659.922 (612.294–690.961) |
| Arc / staging | shirt draw 60 | 13.716 | 8.866 | 4.067 | 30.322 (30.073–43.296) |
| Arc / staging | suit draw 60 | 13.567 | 9.052 | 4.088 | 30.323 (30.145–43.477) |

Medians of three warm repetitions, with one preceding warmup. The per-stage
medians need not sum exactly to the median total. Total includes output packing
and comparison, omitted from this compact table but retained in the evidence.

The original Arc path was a failed performance result: GPU execution was around
18ms, but direct CPU reads took 612–927ms on the two initial film captures. The
runner forced device-local storage and then read the mapped output directly.
libplacebo's allocator prefers cached memory for host reads, but forcing device
memory can constrain that choice; its read function uses memcpy. This motivated
the separately registered staging ablation, not a change to the GLSL algorithm.

The final runner retains `direct` by default and adds `--readback staging`.
Staging copies into a separate host-memory buffer before the CPU read, with the
entire copy/synchronization/read included in download time. The original output
buffer flags, uploads, source data and shader remain unchanged. The original
slow runs are retained, and the same new binary is tested in both modes on the
film captures. The improvement is attributable to this transfer-path change on
these runs; no claim is made that the kernel arithmetic became faster. Device
frequency and short-run variation can change its timings even when unchanged.

Each process creates a device and pipeline before the replay repetitions; those
one-time costs are recorded separately. Each iteration then uploads the same
captured source arrays, vectors and weights, uploads poisoned output, dispatches
three native-plane passes, waits for completion, downloads the output, packs
8-bit samples and compares every sample with CPU golden data. Plane GPU timers
and wall time are separate measurements. Timers missing on a backend are reported
as unavailable rather than invented from wall time.

This is a short repeated-frame replay, not sustained video throughput. It omits
live ME scheduling, initial packing of source AVFrames into uint32 arrays,
decode/encode, ordinary endpoint handling, playback buffering and integration
costs. It also includes validation-only poisoning/comparison work that a deployed
filter would not require. Source pixels currently use four-byte storage for each
8-bit sample, intentionally avoiding an unverified small-integer storage path.
Do not divide these timings into a claimed end-to-end playback FPS or combine
Mac ME timings with Arc rendering timings as if measured on one host.

## Failures, review repairs and reproducibility

The initial NAS invocation failed before GPU dispatch because the scratch mount
did not permit executing its compiled binary. The corrected run compiles and
executes inside the transient research container's `/tmp`, retaining source,
data and results in scratch. The existing research build volume is read-only.
No system toolchain, installed FFmpeg, running service or media was modified.

Independent review found evidence-binding gaps in the first orchestration
wrappers: an empty capsule list could have produced a complete summary, and
matrix rows were not fully cross-checked against their capture manifests. The
wrappers were tightened, and existing evidence re-audited against raw records,
complete CPU certifications and capsule contents. Original executed-script hashes
remain preserved; a later audit is not presented as a rerun of those scripts.

See [GPU-PLAN](GPU-PLAN.md), [capsule contract](CAPSULE.md),
[renderer derivation](GPU-DESIGN.md), `replay.c`, `gather.comp`, `capture.py`,
`run_captures.py`, `run_replays.py` and `gpu_controls.py`. Build commands, source/
executable hashes, per-capture results and timing samples are retained with the
portable GPU evidence. Media and raw film capsules remain external.

`readback.patch` records the change from the original runner to the optional
staging implementation; applying it in reverse reconstructs the original source
whose hash appears in the original build records.

The next engineering step is in-filter integration of this validated renderer
with the exact CPU acceleration, then complete-stream equality and sustained
1080p24->48 measurements on the NAS. A later experiment can substitute our GPU
motion fields while keeping this renderer fixed; that changes the estimator and
needs a new quality comparison. The source-rate sense-organ fields remain useful
and independent throughout.
