# Bounded reconstruction prospecting — 2026-10-23

The owner's request: missing-frame ground truth on several NAS programmes, roughly five minutes near the middle
of each; avoid noise, cuts/transitions and very rapid motion monopolising the shortlist. This complements the older
flow-disagreement prospector; it does not replace that different measurement.

Before any footage render: select the first commercial title in each of Local's existing content manifest's film,
TV, anime, western-cartoon and CG groups (file selection reused, middle windows new). Copy 300 seconds centred at
50% runtime, compressed video only, once. No whole-file hash or decode over the mount. Manifest and footage stay in
external scratch. Scan at width 640 (never upscale), with the shipped High file identified by SHA256. Preserve
native source frame rate; reject interlace and rates outside 23.976/24/25. This is a doubled-motion 12-to-24 type
stress test, not the normal 24-to-60 playback task. Native-size confirmation is required before shader conclusions.

Measurements: luma RMSE, non-overlapping 8x8 SSIM (explicitly `ssim8`, not ffmpeg's overlapping SSIM), a 16x16 grid
of local RMSE, shader against withheld original and GPU linear blend against the same original. Read every frame;
retain even-index input frames as alignment sentinels. Exclude the first/last 0.5 s from rankings. Check frame counts,
retained RMSE <= 2.55 code values (40 dB), and a deliberately shifted reference must fail on a moving control.
A small colour conversion/dither floor is allowed; no claim of bit-exact passthrough.

Primary exclusions, frozen before rendering: scdet >= 8 and +/- 0.25 s guard; either adjacent reference RMS below
1.5 code values marks a hold/near-hold; endpoint RMS < 2 or shader RMS < 2 marks low signal. Extreme endpoint change
is the upper 2.5% of otherwise eligible pairs, or >= 50 code values, and goes to a separate bucket. This is an
unwarped-change proxy, **not** a physical velocity estimate or a perfect cut/fade/hold classifier. Cuts/fades that
escape it must be removed on inspection, with the raw candidate retained. Report exclusion counts, never silently
call excluded pairs defect-free.

Rank within each source using robust median/MAD of log(shader MSE / linear MSE), with a 0.1 log-unit scale floor.
This finds unusual loss of advantage even when High still beats linear. A second lane ranks absolute shader error.
A regression candidate needs >= 1 dB loss to linear and ssim8 lower by >= .005; a local regression witness needs
>= 2 code-value tile RMSE excess and >= 1.25 tile RMSE ratio. Deduplicate events within 1 s and inspect the top three
relative and top two absolute candidates per source. Rankings are discovery heuristics, not calibrated p-values.

Controls before footage: exact midpoint/translation oracle gives zero residual; a deliberately wrong patch must
enter the shortlist; a cut, duplicate drawing and high-change pair must enter their exclusion buckets; constant/low
noise must not rank. Truncated/count-mismatched or shifted inputs must be refused, not scored as quality findings.
Run an actual GPU moving synthetic clip and its retained-frame counterfactual before footage. Repeat native High
on candidates used for conclusions; single-run transients are not established shader defects.

Predictions: (1) a raw absolute-error shortlist will contain cuts/holds/extreme change and shrink materially after
controls; (2) High beats linear on the median eligible pair in every source; (3) at least one non-cut reconstruction
weakness survives native-size inspection, but a reduced scan alone cannot establish it. Record refutations as well
as hits. No switch/default adoption is part of this block.

Implementation amendment **before sampling or footage render**: the five bounded input seeks will decode to local
native-size FFV1 once, rather than packet-copy compressed excerpts. This keeps the midpoint origin exact despite
keyframe pre-roll and preserves native pixels for later confirmation. Compressed source packets still cross the NAS
only for the requested window (plus decoder seek pre-roll); FFV1 expansion is written to the local SSD. No audio or
subtitles copied. The change affects local storage/CPU cost, not sampling or quality decisions. Ties at the 97.5th
percentile are kept (strictly greater than the quantile is extreme); the absolute >= 50 guard remains inclusive.

Boundary handling fixed before the first footage render: if a sampled decode has an odd frame count, drop its
last unpaired frame before decimation, record that one-frame trim, then demand exact reference/render counts.
The last half-second is excluded in all cases. This avoids admitting an EOF replication as a scored prediction.
