# Independent mathematical review of Local's fused MCI renderer

GPT, 2026-11-15. Read-only review of Local's L031 block, before the Cadence integration.
Reviewed repository commit `4c0f22ada689628d9e575059ad5c8fd3f39c7552`; reviewed
`../mci_fused/fused.patch` SHA256
`f5ca6de397deba3598cccc71b52c494ccc40d73805b9cc13591dfc3f664104ce`.
Also read L031 in `CHAT-LEDGER.md`, `../mci_fused/PLAN.md`, `RESULTS.md`, the EPZS
predictor source, and `rawbench.py`. This note does not certify a later backport,
binary, or changed patch. No video rendering or performance benchmarks were run
for this review.

The fused arithmetic and wavefront dependencies are sound under the registered
ordinary compiler settings. The review found two inaccurate bounds in a proof
comment, an explicit failure if division is replaced by reciprocal multiplication,
and a conditional C pointer-construction issue worth removing before integration.
No current stock-versus-fused pixel mismatch was found.

## 1. Exact finishing division

Let `w` be the sum of accepted overlap-table weights, `S` the accumulated weighted
samples, and `alpha` the integer phase in `[0,1024]`. Each accepted pair contributes

```
weight * ((1024 - alpha) * A + alpha * B)
```

with 8-bit `A,B`. The scalar answer for `w>0` is

```
floor((S + 512*w) / (1024*w)).
```

The fused code first calculates `n = floor((S + 512*w)/1024)`. For positive integer
`w`, `floor(floor(x)/w) = floor(x/w)`, so the integer transformation is exact.

The count cap is 16 pairs. Even the loose bound of 255 for every uint8 table entry
gives `w<=4080<2^12`; the actual largest table entry is 240, giving `w<=3840`.
Also `0<=S<=255*1024*w`, and hence:

- `S+512*w < 2^30`: the uint32 accumulator and rounding addition cannot overflow.
- `n<=255.5*w<2^20`: conversion of `n` and `w` to binary32 is exact.
- `r=n/w<=255.5<256`: binary32 division's round-to-nearest error is at most
  `2^-17` in this range.
- If `r` is an integer, it is exactly representable. Otherwise its distance from
  either adjacent integer is at least `1/w>2^-12`, greater than the rounding error.

Therefore truncating the correctly rounded binary32 quotient gives `floor(r)`.
`w=0` is separately masked to the ordinary source-frame blend; its division uses
denominator 1, so no division by zero is evaluated.

Two corrections are needed in the comment at `fused.patch:191`: the real quotient
is **at most 255.5**, not 255, and the half-ulp bound is **at most 2^-17**, not
strictly below it. For example, all source samples equal to 255 and an even `w`
produce `r=255.5`, then correctly truncate to 255. These are proof-comment
corrections, not a failure of the implemented direct division.

This proof is specific to the 8-bit arithmetic and pair-count/weight bounds. It
must be re-derived if the bit depth, accumulation, cap, or normalization changes.

## 2. A reciprocal is observably different

The code's `__FAST_MATH__` guard correctly identifies a risk, but it does not cover
every compiler option permitting reciprocal transformation. Apple clang 21's
preprocessor does not define `__FAST_MATH__` for standalone `-freciprocal-math`.
That observation does not establish that the current compiler transforms this
particular loop under that flag; it establishes that the macro alone is not a
complete build contract.

A concrete permitted arithmetic state is one accepted pair of table weight 164,
`alpha=512`, `A=0`, `B=1`. Weight 164 occurs in the stock overlap tables. Then
`S=83968`, `n=164`, and stock's answer is 1. Direct binary32 `164/164` is exactly 1.
But two separately rounded operations give:

```
float32(164) * float32(1/164) = 0.999999940395355224609375
```

Truncation gives **0**, one code wrong. This is an arithmetic counterexample, not a
claim that this one-pair state occurs in the two film windows or that the tested
build already performs the substitution. Do not introduce approximate reciprocal
division while retaining the exactness claim. Pin the compiler's floating-point
contract, or use integer division when that contract cannot be guaranteed.

The reproducible controls are `math_control.c` and `math_control.py`. The latter
uses only the Python standard library and a C compiler, compiles with explicit
strict division flags, invalidates a previous success before running, and records
source/compiler/binary hashes in `math_control_results.json`. It checks:

- 3,121,200 rational cases immediately below, on, and above integer boundaries
  (`w=1..4080`, integer boundary `1..255`). This is an overinclusive boundary set,
  not exhaustive enumeration of every possible accumulator.
- 100,000 deterministic accumulator cases against the integer factorization and
  direct binary32 division.
- The explicit reciprocal counterexample and the attainable quotient 255.5.

Run from this directory:

```sh
python3 math_control.py --out math_control_results.json
```

Observed on Apple clang 21 / arm64: all direct-division controls pass, stock and
direct float give 1 for the counterexample, and explicit reciprocal multiplication
gives 0. The C control makes the reciprocal intermediate volatile so this deliberate
wrong operation remains separate; it is not a measurement of compiler behavior in
the full filter. These runs measure correctness only, not throughput.

## 3. Count cap and chroma ownership

The renderer visits direction, block row, and block column in stock order within
each disjoint output row band. A zero table weight consumes no count; each nonzero
accepted pair consumes one of 16 positions. Therefore the truncation point is the
same as stock's 32 individual sample entries, and integer sums are unchanged.
The bounded sums above also show that regrouping the paired integer additions
cannot introduce overflow. Both chroma planes are accumulated before the luma
pair count advances, so they use the same acceptance decision.

Stock repeatedly writes each chroma sample while walking its full-resolution
luma pixels; the last luma pixel of the cell determines its final value. Fused
chroma uses precisely that owner. Its negative displacements retain C's truncation
toward zero after the full-resolution border clipping. The unclipped fast path
has the same constant offsets as the scalar path.

Odd final chroma cells deserve an explicit dependency note. The ordinary owner
predicate does not select their incomplete final row/column. Nevertheless the
scalar implementation's support upper bound is clipped to `width-1,height-1`
and then used exclusively: the final luma column and row receive no pairs at all.
Their last-writer result is the ordinary blend, and the fused finishing stage
selects that same zero-weight owner and blend. This equivalence depends on keeping
stock's edge convention. A future correction to those support bounds requires
revisiting partial-cell accumulation; it cannot be folded into an exact speedup.

## 4. Avoid constructing a pointer before a chroma plane

At `fused.patch:308`, the fast path constructs a row pointer with `+cax` before
adding the sample's positive column. For example, take 4:2:0, a width of at least
64, block size 16, block anchor `(32,0)`, direction-zero vector `(-16,0)`, and
midpoint phase. The support has `startc_x=16`, `endc_x=48`; `ax=-8`, `bx=8` satisfy
the fast-path bounds. At luma row 1, `cy=cay=0` and `cax=-4`. The intermediate is
`ca=Udata-4`, although the first owned sample later accesses `ca[8]=Udata[4]`.

If this plane is separately allocated, forming the before-object pointer is
undefined C even though the eventual read is in-frame. Typical shared-plane
allocations can keep that address inside the larger allocation, so this is a
conditional source-level issue, not an observed out-of-bounds read or pixel error.
Use the valid row base and put the offset in the complete sample index:

```c
const uint8_t *ca = fa->data[plane] + (cy + cay) * fa->linesize[plane];
const uint8_t *cb = fb->data[plane] + (cy + cby) * fb->linesize[plane];
/* inside the existing x loop: */
cacc[x >> cw] += m * (wa * ca[(x >> cw) + cax] +
                     wb * cb[(x >> cw) + cbx]);
```

This changes neither coordinate nor integer arithmetic. The fast-path checks
already ensure these complete indices are in-frame.

## 5. Wavefront dependencies and tie order

`search_mv_context` reads three current-pair predictors: left, top, and top-right.
The two historical tables are immutable during these searches. Within a row the
left predictor is ready because the worker processes blocks sequentially. A chunk
starting at `x` processes through `x+7`, whose top-right predictor is `x+8`;
therefore the preceding row's completed-block count must be at least `x+9`, clipped
at row width. That is exactly `x + MCI_WAVE_CHUNK + MCI_WAVE_LAG` for 8 and 1.
Chunked progress publication can delay work conservatively but does not release
it early. Sequentially consistent atomics publish the preceding vector writes.

Rows are claimed in increasing order within each direction, and the first row
does not wait. Thus the row dependency graph has no cycle. The two directions use
separate predictor slots and scratch contexts. The candidate insertion order,
median predictor, costs, and tie decisions inside each block are unchanged.
The final direction-one row supplies the context state consumed after the joined
search. I found no missing dependency in this registered EPZS path.

Optional C hardening: the spin-loop `++spins` continues after the yielding threshold
and would eventually overflow a signed int if a worker were stalled long enough.
Saturate it at the threshold (or increment only before the threshold) while
preserving the same yielding behavior. No such overflow was observed in the runs.

## 6. What the evidence establishes

Local reports 288 final M5 comparisons and 140 NAS comparisons, including coloured
edge fixtures and repeated threaded runs. Its cap-15, incorrect chroma-owner, and
short/no-wavefront-wait counterfactuals demonstrate sensitivity to those defects;
the shirt window alone is explicitly insufficient to catch the cap sabotage.
Those whole-matrix runs were not repeated by this review. My execution was limited
to the standalone arithmetic controls above.

The coloured fixtures close the previous flat-chroma coverage hole; they do not
prove every future format or size. The source argument supports the unchanged
8-bit supported paths more broadly than those examples, while the forthcoming
FFmpeg/Cadence backport still needs its own pixel/count/timestamp comparison on its
actual compiled binary. Exact acceleration preserves stock's pictures, including
stock's possible defects. The owner's calmer verdict on one shirt shot is not a
whole-library perceptual certification.

`rawbench.py` is weaker as an evidence binding than the exactness gate:

- An existing cached raw file is reused by name without a hash or proof that its
  decoded frames still match the declared source fixture.
- Its pre-timing check compares hashes and frame count; it drops the complete
  frame records, including timestamp/duration fields.
- Binary hashes are recorded initially but not rechecked through all runs; raw
  input hashes and all run commands/logs are not bound into the final summary.

These are reproducibility limitations of those timing artifacts, not a discovered
failure of the separate exactness matrix or a reason to discard the observed
speedup. Harden those bindings for a new benchmark block. Distinguish internal
stage timings from process wall time: the raw-source/null-sink process still has
demux, frame handling and output work. The NAS stock timings were taken in an
earlier sitting, as RESULTS discloses. The 4K cache/memory explanation is a plausible
inference from scaling and working-set size, not a measured cache-miss attribution.
