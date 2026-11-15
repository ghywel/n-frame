# Translation ripple diagnosis — 2026-11-15

The owner reports distracting shirt/suit rippling in two specific windows of a supplied film, at 202–204 and
209–211 seconds, seen at 24→48 and believed common to variants. Diagnose the shared cause before claiming a fix.
Baseline is current High `ccfdf74` (WARP_VOTE=2); also render WARP_VOTE=0, the preceding High. The older Nov13
motionstress scores do not describe the current baseline. Media and private source paths remain external.

Cache only 200–205 and 207–213 seconds. Keep full 1920x1080 input for estimator behavior. The file is actually
24000/1001 fps; exact doubling is 48000/1001. Assign exact input PTS and first use that ratio to isolate midpoint
geometry; fixed 48fps is a separate host-phase check. Native insertion has no photographed midpoint truth.
Withheld-frame reconstruction has real truth but doubles displacement and is a separate stress condition.

Initial hypotheses, before GPU renders:

1. Local displacement varies irregularly inside an approximately moving garment, producing spatial compression,
   expansion or folding in the endpoint sampling maps. Read actual fields; inspect gradients and endpoint mismatch.
2. The output-grid interpretation of A-indexed flow or changing support fallback amplifies that variation.
   Separate field quality from final sampling by controlled warp-only ablations and calibrated CPU replay.
3. The newer half-resolution warp vote adds sampling discontinuities. Compare vote-off; independently test the
   weight/vector sampling mismatch in VOTE-SAMPLING.md. This cannot explain defects that predate the vote.
4. Source grain, physical cloth deformation or a host phase/scale issue could masquerade as estimator defects.
   Inspect source endpoints, exact retained frames and true withheld frames, and preserve an unknown outcome.

Refuse failed processes, fallback/compile faults, unexpected frame counts and retained-source misalignment.
Calibrate field decoding with a static and known translation case. A finite PSNR or a smoother-looking field
alone is not evidence of a better picture. Inspect the garment and its boundaries separately. Record losing
ablations and source controls. No shipped shader replacement from these two windows alone.

## Second diagnostic round, before its renders

The field decoder reads zero within 0.002 px on static input and median (31.25,0.13) for known (+32,0)
translation. A CPU midpoint replay using the dumped field/support agrees with prior High within 0.50 DN RMS
on four observed shirt outputs. In the fixed exploratory shirt rectangle, native output 145 has a high flow
gradient and a small set of negative A-sampling Jacobians; this does not by itself prove a wrong physical field.

Now render the two estimator ablations registered in ESTIMATOR-ABLATIONS.md and the unchanged Nov13 inverse2
candidate (hash `18018e164adcaba2168b8561dbda03c5012caa93bbe8738b2b8589eba0d594e7`) on prior High, each alone.
Use both native insertion and even-frame decimation/reconstruction. The latter has actual midpoint truth but
twice the native displacement. Test source-time history, H-level refinement, and the final coordinate approximation
separately; do not combine changes before identifying their effects. Disabling fallback and nearest vote confidence
already have their own isolated renders. No claim that a diagnostic ablation is a safe shipping configuration.

An independent FFmpeg `minterpolate` render (bidir estimation, adaptive overlapped blocks, variable block size)
is a picture counterfactual, not a proposed NAS/Cadence deployment. Use the same native input and exact doubling;
append two cloned source frames only to flush its delayed tail, then require the original doubled output count.
The interior windows precede those clones. Compare retained source alignment before viewing/scoring this baseline.

Post-result source audit (2026-11-15): the command above requested adaptive overlap and variable blocks, but the
selected `me_mode=bidir` branch bypasses both options in FFmpeg `3a5eb94`. The actual control is bidirectional
estimation with ordinary fixed-block overlap. The initial feature description above was mistaken; preserve the
command and results, and use the corrected interpretation in RESULTS.md.
