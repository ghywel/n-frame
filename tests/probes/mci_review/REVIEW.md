# Cadence integration review of Local's fused MCI block

2026-11-15. Reviewed `n-frame` main `4c0f22a`, ledger L031 and
`tests/probes/mci_fused/fused.patch`. This review does not change Local's patch.
No new timing run is part of this review.

## Required format repair: alpha

The fused branch allocates its replacement arrays for every bidirectional input
with bit 16 enabled. It writes plane 0 and, when present, planes 1 and 2. The
filter also advertises `yuva420p`, `yuva422p` and `yuva444p`; their fourth plane is
never written on inserted frames. This is uninitialized output, not merely a
different interpolation policy. Ordinary three-plane film inputs do not expose it.

`alpha_fallback.py` generates a separate repair. A single `mci_fused_enabled`
predicate permits only the implemented one-plane gray and three-plane YUV cases.
Both allocation and rendering use it. YUVA therefore gets the original lists and
the original renderer, which writes all four planes. Bits 1, 2 and 32 remain
available; bits 4/8 retain their pre-existing behavior. Keeping allocation and
dispatch in agreement prevents falling back through null contribution arrays.

Registered regression, before execution: create short 80x48 raw videos with
nonconstant, changing Y/U/V/alpha. Run stock, the unmodified fused binary, and
the repaired binary for each advertised YUVA format with `scd=none` and 24->48.
Require the unmodified mask-51 binary to differ on inserted alpha samples; require
the repaired masks 16/51/63 to equal every stock Y/U/V/alpha byte, with the exact
output count, at one and four threads. Require retained instants to reproduce the
source, and require stock inserted alpha to differ from both adjacent retained
endpoints in at least one pair. No quality or speed conclusion follows.

## Executed alpha regression and spin repair

The isolated repaired build passed all **18** registered comparisons: three YUVA
formats, masks 16/51/63, at one/four threads. Every raw Y/U/V/alpha byte and every
output PTS/duration/count equals stock. The unmodified fused build differs on
alpha in **all 12 inserted frames of each format**, while its YUV and retained
frames remain exact. Stock inserted alpha differs from both neighboring retained
endpoints, so the test does not merely pass through held frames.

`spin_counter.py` separately saturates the wait counter at 256. Its first yield
remains iteration 257 and every subsequent wait still yields. A 1,000-iteration
control confirms that schedule; the repaired FFmpeg used both repairs above.

[results.json](results.json) records portable hashes and per-format findings.
The exact build commands, logs, generated patches, input arrays, every raw output
and matching framemd5 records remain under
`/Users/kurokendo/np-scratch-int/mci-review-20261115`. The fixed C SHA256 is
`4b0ecfcd6f91cb8c63e53d36a7e17d951b86ad88ade0ec58de736b86f1d566b2`;
the isolated FFmpeg SHA256 is
`63456cdabb91de7e3ef27beed90ce6527b877572c07065c80028c86c2b42155d`.
This is correctness evidence for these repairs, without a timing claim.

## Wavefront concurrency

For a chunk beginning at x and containing up to eight blocks, its last block needs
the above row through x+8 (top-right), i.e. at least x+9 completed blocks. The
implementation waits for `min(x+8+1, b_width)`. Publication happens after chunks;
waiting may therefore be conservative but does not release a dependent block too
early. Small block grids can serialize rows; they remain correct.

The default sequentially consistent atomic stores/loads publish prior writes to
`mv_table[0]` before another row consumes them. Current-row left predecessors are
executed sequentially within the owning job. Prior-pair tables are read-only, and
directions write separate vector elements. Scratch contexts are per job. Only the
owner of direction 1's last row writes `td.last`, which the caller reads after
the synchronous filter executor completes.

Rows are claimed monotonically per direction. Each waiting row depends on a
lower row which has already been claimed; the lowest unfinished row has no
unfinished predecessor that can form a cycle. This avoids a worker-pool dependency
deadlock under ordinary fair scheduling. One job processes both directions;
serial execution of multiple jobs also completes. It is not a wait-free algorithm
or a guarantee under arbitrary thread starvation or externally stopped workers.

Bit 32 execution is nested inside MCI/bidirectional mode and requires EPZS.
Other search methods keep the original path. Bilateral EPZS may allocate an unused
progress array when bit 32 is set, but does not execute wavefront jobs. Endpoints,
scene changes, blend and duplicate modes retain their pre-existing branches.

## Remaining portability and evidence limits

- The unconditional `<sched.h>` and `sched_yield()` are POSIX-specific. They are
  available on the tested macOS/Linux targets; a Windows FFmpeg build needs a
  configured yield abstraction or a guarded fallback.
- The local spin counter increments even after entering its yielding state. An
  indefinitely stalled predecessor can eventually overflow signed `int`; resetting
  or saturating that counter would remove this avoidable robustness risk. It is
  not an observed failure in the registered short tests.
- The float32 finishing argument is sound for ordinary correctly rounded division:
  the reduced numerator is below 2^20, the divisor is at most 4080, and the
  rational result's distance from an integer exceeds float rounding error. The
  comment's bound should say the unfloored quotient is below 256 (it can reach
  255.5), while its integer result is at most 255. Standalone reciprocal/unsafe
  math options are not all identified by `__FAST_MATH__`; retain the tested build
  flags or use the integer path when those assumptions are not assured.
- Local's repeated race controls and colored-edge cases are substantial evidence.
  They are not validation of arbitrary pixel formats, all search methods, or an
  integrated Cadence decode/filter/encode pipeline. The alpha regression closes
  one concrete uncovered advertised-format case.
