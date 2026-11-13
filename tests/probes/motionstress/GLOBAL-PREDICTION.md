# Full-resolution witness for a global pan

2026-11-13; registered after the first motionstress baseline, before building or running this candidate.

Current High's global search compares point-sampled coarse images and rejects a frame whose coarse Moire cue
is high. The new pan_detail (+40 px/source frame) and pan_mixed (+48) can therefore lose their global anchor
although full-resolution retained images contain the correspondence. We test an **additional witness**, with
the existing global result as fallback, rather than replacing every global decision.

Add a 17x9 candidate-cost texture over the existing +-64 x +-32 full-pixel / 8-pixel-step displacement grid
(ordinary High). Each candidate compares 256 full-resolution luma samples distributed over the central 70%
of the frame; B uses the existing GLOBAL_GAIN compensation. The direct difference at zero is evaluated on
exactly the same samples. A candidate is eligible only when all of these prechosen conditions hold:

- at least 95% of the taps remain inside both images;
- mean displaced residual is less than 1.5/255;
- mean displaced residual is less than 20% of the zero-displacement residual;
- at least 65% of **all** taps have zero-displacement difference above 2/255 and displaced difference below
  one quarter of their zero difference.

Choose the eligible candidate with the lowest residual plus the original .002-per-coarse-texel magnitude prior.
If none qualifies, keep the original global argmin and Moire gate. An accepted direct witness replaces that
argmin and bypasses the coarse Moire gate; the original previous-pair agreement and amplitude fade still apply.
No per-object field, warp, alias-carry or cut behavior is otherwise changed.

Predictions: both whole-frame pans gain at least 1 dB against High; static/slow controls remain within .1 dB;
small independent faces/bars fail the majority-support criterion and remain near baseline. The original ladder
remains the judge. Reject this candidate if it produces a new-case ROI/feature loss over .5 dB; any eventual
deployment requires the main plan's wider gate and cost measurement.

Risks kept explicit: exactly periodic full-frame textures can admit several exact shifts, so this witness is not
an alias-proof certificate. The unchanged magnitude prior may choose a wrong smaller equivalent shift. Sparse
sampling can still have blind spots; majority support is empirical evidence, not segmentation. A constant
exposure change or GLOBAL_GAIN's own ambiguous motion fit can remove the needed signal; then the new witness
refuses. Whole-scene pans outside the existing search grid, sub-grid shifts and large nonrigid motions may gain
nothing. A newly accepted witness also changes what the existing temporal cache remembers; its transition back
to the old branch may need a pair to settle. The added pass runs at output rate unless the host caches it.

## After the first GPU result: bounded CPU check of off-grid refinement

This is post-result exploration, not part of the original prediction. No third shader was built. Analytic frames
5 and 6, identity GLOBAL_GAIN, the same 256 taps, same eligibility rules and magnitude prior:

| Holdout | Best candidate before eligibility | Mean residual | Truth within a +-4 px box around that candidate? | Best refined result |
|---|---|---:|---|---|
| pan_detail37 | (40, 0) | .017416 | yes | (37, 0), residual below 4e-10, support 93.36% |
| pan_detail43 | (40, 0) | .016103 | yes | (43, 0), residual below 2e-10, support 92.97% |
| pan_mixed45 | (32, 23.4783) | .055827 | **no** | same wrong basin, still refused |

For mixed45, the candidate **(48,0) ranks second**, with residual .058538. Refining that basin by +-4 full pixels
at one-pixel spacing recovers (45,0), residual zero, support 96.09%. Raw residual and prior-penalized argmins have
the same ordering in these three cases. Therefore refining only the single coarse winner would miss one of these
holdouts. A bounded next proposal would preserve multiple separated basins for refinement, then apply the original
verification conditions; this result does not establish that two basins suffice generally or justify weakening
the residual/support thresholds. Cost, other frame phases, noninteger speeds, mixed motion and periodic aliases
still need a fresh registration and gate.

Dimensional control: libplacebo rounds hook sizes (`custom_mpv.c`, `out_h = roundf(out_size[1])`), so at 640x360 the
coarse image is **40x23**, making the global grid's half-texel vertical step **7.8261 full pixels**, not exactly eight.
Using a nominal 8-pixel step incorrectly makes (48,0) win mixed45's coarse ranking. The table uses the actual
40x23 coordinate mapping. Refinement offsets should be expressed in full-pixel `HOOKED_pt` units, while the
returned seed remains in the estimator's actual coarse-texel units. Raw CPU data:
`$NP_SCRATCH/global-offgrid-cpu-20261113.json`. This is not a GPU flow or picture result.
