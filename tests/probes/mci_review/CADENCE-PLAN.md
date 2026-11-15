# Local review and Cadence content-testing integration

Registered 2026-11-15 before the application adapter is exercised. Local L031
changes the priority: CPU mask 51 is the first practical 1080p playback candidate.
The GPU replay remains independent work for 4K and CPU load, not a prerequisite.

## Independent review

Re-audit the six final Mac evidence matrices against actual binaries, inputs,
raw records, timestamps, dimensions, profile counts and commands. Review the
float32 quotient and wavefront ordering mathematically. Test a reciprocal-math
counterexample and the newly found YUVA missing-alpha case. Preserve Local's
original patch and add repairs separately. Acknowledge the earlier gray-chroma
fixture gap; Local's colored-border matrix closes it for the measured formats.

## Application contract

Cadence uses native Metal interpolation, not an FFmpeg process for rendering.
Add a persistent in-process libavfilter adapter and a visible MCI/n-frame choice.
First MCI scope: eight-bit SDR, bidirectional EPZS, 16-pixel blocks, search 32,
mask 51, two-times source rate or explicit 60 fps. Auto uses two-times, without
borrowing the Metal capability cache. HDR/Dolby Vision must report a deliberate
fallback rather than silently pass through an eight-bit graph.

Feed decoded YUV frames with source timestamps, maintain sequential temporal
history when display frames are skipped, rebuild on seeks/rate changes, and
hold endpoints only within known stream bounds. Preserve audio scheduling and
color attachments. Identify the active backend and any fallback in logs/UI.
Do not silently replace an overloaded MCI run with the Metal shader under test.

MediaStack FFmpeg 9.0.2 differs from the research revision. Vendor a hashed,
release-specific patch including the separate-stride changes, acceleration and
review repairs. Build dynamic libraries without reciprocal/unsafe math. Test
this actual library and adapter against the original CLI pixels/counts/PTS;
prior research certification does not certify the new integration.

## Gates and delivery

1. Reference versus integrated adapter: full YUV, output count and PTS on the
   cached shirt/suit windows and colored/edge synthetic fixtures, at 2x and 60.
   Include reset/seek and deliberately wrong reference refusal.
2. Actual app: require backend identity and meaningful playback progress, then
   seek, rate changes, end handling, and audio/clock observations. Keep compile
   activity separate from any timing claim.
3. Produce a separately named Mac test app, without replacing the installed
   Cadence. Document supported scope and remaining device/content checks.
4. Merge completed review/integration blocks to main and report through ledger.

No new visual-quality claim follows from output equivalence. The owner's calmer
shirt verdict applies to the earlier independent MCI clip; sustained comfort
across content still needs viewing in the application.
