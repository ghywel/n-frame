# Bounded GPU replay after exact CPU acceleration

Registered 2026-11-15 before compiling or dispatching the replay. The CPU block
is measured and merged separately. This block implements the renderer design,
not a new motion estimator or Cadence integration.

Capture a small, declared selection of real scalar FFmpeg render invocations,
including their actual source frames, consumed bidirectional vectors, integer
phase, overlap table and complete output planes. Captures come from pristine
pinned FFmpeg with an opt-in exporter, not the CPU acceleration patch. Process
the full cached input history; select one-based interpolation draw numbers.

Initial matrix: draw 5 of each small fixture, with block16; add selected other
phases from the 24->60 pan and blocks4/8 on the boundary fixtures. For film,
capture shirt draw30 and suit draw60 from the complete cached windows. These
are declared selection indices, not claims that they are worst-case defects.
Validate all captures, compare replay to every scalar Y/U/V output sample,
and repeat at least three warm dispatches per capture. Expand only for an
observed failure or a specifically missing semantic boundary.

Use low-level libplacebo Vulkan compute and integer buffers: no RGB conversion,
filtered texture reads, CPU-computed substitute golden, or golden uploaded to
the GPU. Preserve candidate order/cap, moving supports, clipping, signed
division and last-luma chroma representative. Inputs and the shader are hashed.
Poison the output before correctness iterations so skipped writes cannot pass.

Negative controls must include malformed/truncated input refused before dispatch,
a valid altered golden rejected after actual GPU work, a deliberately altered
shader rejected, and an unwritten poisoned output rejected. CPU formula controls
remain a separate layer of evidence.

Run serially on the M5 after CPU timings finish. If the same portable runner
builds in the NAS's existing research image, repeat selected captures on the
actual Intel Arc A310. Use the research volume read-only and a new scratch mount;
do not modify installed builds, containers or media. No simultaneous GPU jobs.

Report compilation, warm compute, transfer/completion and total replay costs
with explicit boundaries. Capsule replay omits live estimator scheduling,
decode/encode, packing in the filter, frame upload reuse and playback buffering.
Even a fast, exact replay is not a demonstrated real-time end-to-end pipeline.
If correctness fails, preserve the failing capture and counterexample, repair
the implementation if possible, and repeat the affected gate before timing.

## Supplementary shirt-region capture, registered before its run

Review of the completed original selection found that shirt draw30 corresponds
to output59, only `59*1001/48000 = 1.230396` seconds into the normalized cached
sequence. It precedes the owner's reported 202–204 s shirt episode. Preserve the
original 21-capture matrix and its results unchanged.

Add **shirt draw60, block16**, in a separate capture run and result group, then
replay that same capsule on each available target. At exact doubling, the
expected output is 119, at `119*1001/48000 = 2.481646` normalized seconds; verify
the actual capsule/output identity rather than assuming draw numbering. This is
approximately the reported shirt interval, not a preregistered worst-error pixel
or a complete temporal sample.

The [recorded extraction command](../ripple/README.md) uses `-ss 200 -t 5` for the
shirt. **200 s is a seek target, not a verified exact photographed-frame instant.**
A read-only inspection of the cached file's first packet gives PTS 42 at time base
1/1000 (0.042 s); interpolation subsequently assigns source timestamps from frame
number. Thus 202.48 s is a nominal seek-plus-normalized-time label, with a source
frame/seek offset, rather than independently calibrated absolute film time. The
selection is reasonably described as about 202.5 s. No additional original-film
read was made for this registration.

This supplement checks faithful GPU rendering at a selected point in the known
region. It does not demonstrate whole-sequence visual comfort, reproduce a
temporal artifact in one still, test retained/cut bypasses, or validate a new
motion estimator. Root owns the separate capture and replay scheduling.

## Follow-up registered after Arc's slow direct readback

The original Arc renderer is exact but its 1080p CPU readback takes roughly
0.6–0.9 seconds, versus approximately18ms of GPU compute. The original output
buffer forces device-local memory while also permitting direct host reads;
libplacebo's Vulkan implementation performs that read with memcpy from mapped
memory. Its allocator explicitly warns that uncached reads can be very slow.

Preserve those failed performance measurements. Add an optional `staging`
readback mode: keep the original shader, input uploads and output buffer flags,
copy the completed output into a separate host-readable host-memory buffer,
then read it. Charge copy, completion and read to the download stage. Keep
`direct` as the default original path and report the selected mode explicitly.
Predict a large reduction in readback time on Arc, with identical output; this
is a hypothesis until run. Repeat the captured matrix and fault controls for
the changed path, and compare direct/staging film replays using the same binary.
This does not by itself establish sustained playback or optimize uploads.
