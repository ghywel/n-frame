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
