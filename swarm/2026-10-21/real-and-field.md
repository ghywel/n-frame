# Lane real-and-field: every real-footage number in the record is a whole-frame mean over a few seconds, and three of the four real defects live below that mean; the tier that would find the next one scores blocks, frames and speeds, keeps the series, and reports extremes

## What I read

- `BRIEF.md`; `INSTINCT-STRATEGY.md` 1-130; `README.md` 1-30; `tests/TESTING.md` 1466-1567, 1929-1994.
- Headers/docstrings: `probes/dig/dig.sh`, `panspeed.py`, `prospect.py`, `flowoutliers.py`, `realanalyze.py`,
  `edgeerror.py`, `bandmetric.py`, `accelprospect.sh`, `accelcheck.py`, `discaccel.py`, `jitter.sh`, `screen.sh`,
  `realbench.sh` (75-102), `probes/twos/cadence.py`, `probes/decimate/decimate.sh`, `probes/pan/pan.sh`,
  `probes/limb/real.sh` 1-33, `masters.py`, `probes/masters/*`, `probes/shear/*`, `probes/verbs/rolling.sh`,
  `probes/weird/*`, `probes/party/*.py` and `PREDICTION.md`, `probes/jerk/jerksweep.sh`.
- `NFRAME-LIMITS.md`: 2313-2345, 2389-2420, 2500-2540, 2620-2640, 2736-2748, 3107-3140, 3213-3260, 3340-3440,
  3595-3660, 3785-3864, 3972-4035, 4110-4125, 4181-4400, 4467-4490, 4918-4972; greps for "refuted", "Real footage",
  "realbench", "SSIM", "twos", "bttf", "avengers", "street", "bluey".
- `WHAT-IT-CAN-MEASURE.md` whole; `QUINTDIRECTIONAL.md` 168-260; `THREEDIMENSIONAL.md` 916-1010; `HANDOVER.md`
  316-334; `WORKFLOW-SAVED-MEMORY.md` 252-264; `ENERGY-TRANSFER.md` 1318-1330, 1566-1580 and its MISSED grep;
  `REPAIRS.md` 97-132, 201-240.
- Local data: `ls` and `ffprobe` metadata of `np-scratch/Cadence/TestShare/` (no render); `party-analysis/motion.txt`
  (numbers only). The ffprobe readings are the only [M] facts here, and they are metadata.
- Not read: `SHADERS.md` beyond a grep, `ENERGY-TRANSFER.md`'s steps, `PRIOR-ART.md`, the generators, `scenes.sh`.

## Findings

1. **[R] Every real-footage result in the record is a mean over whole frames of a few fixed segments, written in prose.**
   The standard set is `probes/limb/real.sh:30-33`: street 2/8/14 s, avengers 10/30/50, bttf 10/30/50, bluey 60/180/300,
   three 3-second segments each; the avengers "record's five segments" at 5/15/21/30/45 s (NFRAME-LIMITS 1305); the second
   4K film's nine fixed 3-s segments at 900-s steps (2627-2630) and twelve random ones (2739-2748); forty film extracts for
   the outline adoption (WHAT-IT-CAN-MEASURE 16-17). Each run reports PSNR and SSIM means per clip. No results file per
   build exists for real footage as `tests/analyze.py` gives the ladder; the numbers live in dated paragraphs. Edge error
   (`edgeerror.sh`), the moving band (`bandmetric.py`) and the chamfer distance exist but were used ad hoc.

2. **[R] Whole-frame means cannot separate the family on ordinary footage.** Perfect per-segment selection over eighteen
   real segments is worth 0.04 dB (WHAT-IT-CAN-MEASURE 7-9). The owner's reported defects move the mean by hundredths
   (the outline adoption +0.06 dB over 40 extracts, 16-17) while their regions move by whole decibels (the railing
   25.5 -> 27.1, the wall's pan +5 at its fastest, 13-15). [J] So the instrument the record has for real content is a
   regression guard, not a defect finder, and the two jobs want different statistics: means for "no regression",
   extremes for "where is it wrong".

3. **[R] Correction to the brief: the weave was not found in a film.** It was found on the masters' synthetic `weave`
   texture while moving a rigid rotation (NFRAME-LIMITS 4920-4921) and is "not yet crystallised as a ladder case, and
   not yet looked for in real footage" (4966-4967); the listed next measurement is "a real clip of checked cloth" (4971).
   Three of the four defects were eyes-first; the fourth is synthetic-first with its real witness missing. [J] That is a
   job for the tier before any new hunt: find the weave in real footage, or record that two films do not contain it.

4. **[R] Case by case, what a scored tier would have seen of the four defects.**
   - *The sandstone pan* (3785-3806). Decimate-and-reconstruct on the shot itself: the recommendation's margin over
     linear by wall speed is +2.4, +3.0, +1.5, +1.0, +0.7 dB for 0-8 to 32-40 px/frame, and -2.2 only on two frames at
     42 px doubled. The whole-clip margin is positive. [J] The funnel's ranking (margin over linear per candidate,
     `dig.sh` header) would not have flagged it; a per-frame margin series against a speed covariate (`panspeed.py`)
     would, as a monotone fall of margin with speed. The field statistic is sharper: the share of wall texels within 1.5
     px of the pan goes 100% -> 58% -> 0% as speed rises to 36 px (3828-3832), a coherent snap to zero. [J] The
     prospector is blind to that by design: it scores distance from the neighbourhood median and "largely ignores real
     motion" (`prospect.py` docstring); a whole region at zero is coherent. The detector is global shift (phase
     correlation, which "reads 38 px exactly off the same images", 3853-3855) against the field's own median: their
     disagreement is the reach failure.
   - *The railing / cage* (3972-3986, 4119). On the railing's rectangle the recommendation reads 25.5 against hold 25.3
     and the blend 29.4, a margin of -3.9 dB below linear and level with a hold; the whole frame reads 28.67. The record
     says it in so many words: "a small region's fault vanishes in a frame mean -- which is how his eye found what the
     ladder's mean had not" (3985-3986). [J] A blockwise margin map (shader minus linear per 64x64 block, worst block
     reported) catches this at once: a block below hold is a defect by the record's own criterion ("knowing when not to
     warp", 4014). The prospector may or may not have: 20% of cage texels sat a bar period away (3999-4000), isolated
     enough to deviate from the median, but a railing is a small share of the frame and the relative threshold is set
     by the whole scan.
   - *The stairs* (2389-2397, 2533-2540). Whole-frame reconstruction put the variational at 40.36 dB against linear
     37.15 and the quad 39.19, and even in the moving band 27.56 against 26.57. No margin statistic flags a shot where
     the shader beats linear by 3 dB. What measured the fault was a field statistic: the spread (p90 - p10) of the
     horizontal flow component across a rigid background, 1.2 px at a 1 px/frame pan rising to 8-18 px at 11-20
     (2533-2536), and the local incoherence (cells more than 1 px from their 5x5 median) rising smoothly 0.01 -> 0.37
     with the pan (2529-2531). That second number is the prospector's own statistic; [J] a film-length scan would have
     ranked the shot's last second, and the funnel would then have re-ranked it by margin and discarded it. The visible
     shimmer is temporal, `jitter.sh`'s domain, which no recorded run applied to the shot [U].
   - *The weave*: not in real footage at all (finding 3). From the masters, the family sits at or below the blend on a
     14/28-px two-dimensional print in motion (4927-4938). [J] The detector is on the source, not the output: a
     two-dimensional periodicity test per block (autocorrelation peak at 6-32 px in both axes) selects candidate
     regions; the block margin over the blend scores them.
   - [J] The pattern: three of four defects are region-local, speed-dependent, and sit under a positive whole-frame
     margin. The fourth was never looked for. A tier of means finds none of them. A tier that keeps per-frame, per-block
     series and reports extremes finds three, and the fourth needs a source-side detector.

5. **[R] The decimated bench doubles every motion and the record calls that misleading** (TESTING 1515-1527: "harder than
   production, and by more than it sounds"). Four local files are 60 fps sources (`busy-4k60.mp4` 3840x2160 at 60, 140
   Mbit/s, 36 s; `Demo/Space/Artemis I Launches to the Moon` 1920x1080 at 59.94, 152 s; `Demo/HDR/nature-sdr.mp4`
   1920x1080 at 60, 60 s; ffprobe [M]). [J] Decimating 60 -> 30 -> 60 asks the shader for 30-fps motion, which is less per
   pair than production's 24-fps motion, so the first real-footage measurement at or below production difficulty is
   available tonight without the NAS. `realbench.sh` takes the rate as `$RATE` (line 75); whether the environment sets
   it as `screen.sh` does is [U].

6. **[R] The field on real content stands at: velocity gain 0.71-0.75 in the middle band, a reach cliff from 24 px/frame
   that is a snap to zero (4219-4226); curl 0.9, divergence about 0.6 with the mechanism open (THREEDIMENSIONAL 937-957);
   acceleration and jerk unmeasured, the 30-fps skeleton's 0.4-px floor cannot resolve them** (WHAT-IT-CAN-MEASURE,
   last line). The owner's proposal is on the books as HANDOVER.md item 17: "A dropped ball against a scale bar reads
   g; a turntable reads rpm. The calibration script ... is an afternoon; the footage needs the owner's camera."
   [J] A dropped ball is the wrong motion for this estimator: at 1 m per 1000 px and 60 fps it passes 23 px/frame
   after 0.3 m of fall (v = 4.4 m/s at 1 m is 73 px/frame), so most of the drop is past the reach. A turntable or a
   pendulum stays in reach for ever.

7. **[R] Real limb motion is not smooth at the five-frame scale.** Vision bone midpoints: arms turn a median 15-19
   degrees per moving frame and 6-11% of moving frames reverse (NFRAME-LIMITS 4286-4289; `party-analysis/motion.txt`
   TURNING rows, 10.3-18.0% over 90 degrees). [J] A quartic through five frames at 24 fps spans 167 ms; one window in
   nine to fifteen contains a reversal, and its jerk coefficient is then a fit artefact, not a derivative of a smooth
   path. Any real-content jerk reading needs a smoothness gate (the quint's own fit residual, which the six-frame
   shader exposes per texel, WHAT-IT-CAN-MEASURE "Crackle") before it is believed.

8. **[R] The quint's 118:1 was measured where truncation matters: 6-8 samples per period** (QUINTDIRECTIONAL 208-214;
   O6 at 24 samples per period: "none, as predicted"). [J] So a real test of the fifth frame's advantage must put the
   known motion at 6-10 samples per period at the rate the shader sees. A 2-s pendulum at 60 fps is 120 samples per
   period and would show the quad and quint reading alike. The fix is the bench's own trick turned on the field: film
   at 60 fps, drop frames by integer factors, and the physics stays true while samples per period sweep 60/k.

9. **[R] Local files tonight** (ffprobe [M]): `Films/Back to the Future (1985).mkv` 1920x1038 HEVC 23.976, 116 min at
   1.69 Mbit/s; `Films/Avengers clip.mp4` 1920x808 HEVC 60 s; `Films/WALL-E.mp4` 1920x800 H.264 98 min at 1.76 Mbit/s;
   `Films/Film 4K 30s.mp4` 10-bit HEVC; `Films/sample-1080p.mp4` 19 s; the Fate/stay night episode 1080p 23.7 min;
   `Apollo 11 - Saturn V Launch (1969)` 1080p at exactly 24; the 60-fps files of finding 5. The record's standard clips
   (streetpeople, bluey, avengersclip, backtothefuture60sec24fps) are not under `np-scratch` to depth 3 [M], so no local
   number compares with the record's (same file or nothing, TESTING 1535-1541). The two low-bitrate films carry the
   2.3-dB "poor stream" floor (TESTING 1528-1535).

## Proposals, ranked

Count first: the tier below enumerates 24 segments per film x 3 local films (BTTF, WALL-E, the anime episode) + 6
short clips + 3 sixty-fps sources = 81 segments; four modes each (hold, linear, recommendation, candidate) = 324
renders of 72 frames.

**P1. Freeze a real-content tier with a segments file and a results file per build (rank 1: the step nobody took).**
Mechanism: a `realtier-segments.txt` (file hash, start, 3 s, cadence verdict from `screen.sh`/`cadence.py`, the
draw seed) chosen per film as 12 at fixed stride + 12 random with a recorded seed, because the random draw found two
segments the nine fixed ones had not (NFRAME-LIMITS 2739-2745). Per build and shader, `realtier-<build>-<shader>.tsv`:
one row per segment with PSNR-Y, SSIM, edge error, moving-band PSNR, and the extremes of P2-P3; the per-frame series
saved beside it as `prospect.py` saves scans. A `realcompare.py` like `analyze.py` reads two files: means within
+/-0.10 dB for regression, extremes for discovery. Prior attempt: `real.sh` and the 4K film's nine + twelve; neither
frozen, neither with extremes. Prediction: every shader within 0.3 dB of each other on film segments (the 0.04-dB
finding), SSIM above linear on every moving segment. Kill test: a passthrough failure stops the run (TESTING
1497-1502); the recommendation below linear on SSIM on more than two segments of a film is a find the record does not
predict, which is the point. Cost: a tool-writing hour; GPU [U] 30-60 s per 3-s 1080p render on the M5, so 324 renders
is 3-5 h in the owner's queue; the 60-fps files first (P4).

**P2. A block-margin map per frame: the detector for the cage's kind (rank 2).** Mechanism: PSNR per 64x64 block on
every synthesised frame for shader and linear and hold; report per segment the minimum of (shader - linear), the 5th
percentile, and the count of blocks below hold. Prior attempt: `bandmetric.py` (one band per frame, the moving band),
`edgeerror.py` (edge pixels pooled). Neither localises. Prediction: on BTTF at least one segment whose whole-frame
margin is above +1 dB has a block 3 dB or more below linear (the record's own case: both shaders beat linear by 2.5 dB
on a segment where they were worse than linear at edges, TOOLS.md:60); the cage's mechanism predicts such blocks on fine
vertical prints under slow drift. Kill: if the minimum block margin is within 1 dB of the frame margin on every
segment, local faults do not exist on this material and the mean suffices. Inconclusive tips toward keeping it: the
cost is CPU only, after the renders exist. Cost: an afternoon of python; no GPU beyond P1.

**P3. The reach statistic: global shift against the field (rank 3; same kind as P2, so the next proposal differs).**
Mechanism: per frame, the frame's dominant shift by phase correlation (`panspeed.py`'s `shift`, already written) and,
from a flowvis render of the field, the share of texels within 1.5 px of that shift and the share near zero; report
the worst frame per segment. Prior attempt: `prospect.py` (median deviation, blind to coherent snaps by design), the
pan's reading by hand on W3 (3828-3832). Prediction: on panning segments the near-zero share exceeds 20% wherever the
decimated shift exceeds 24 px/frame (the party cliff 4219-4226, W3 at 36 px), and is under 5% below 16 px. Kill: a
snap share under 10% at shifts over 30 px means the global seed has closed the real cliff and the statistic is
retired as a detector. Cost: CPU, an afternoon; needs one flowvis render per segment (GPU, a second render of each
segment, +25% on P1).

**P4. Production-rate decimation on the 60-fps sources (rank 4: cheap, unknown value).** Mechanism: `busy-4k60`,
Artemis 1080p60 and nature-sdr decimated 60 -> 30 -> 60, so the per-pair motion is below production's; and 60 -> 20 ->
60 if `realbench.sh` can keep one frame in three (it keeps even frames, line 78; a one-in-three needs a change [U]).
Prior attempt: none; every real number is 24 -> 12 -> 24 and the record warns the absolute picture misleads (TESTING
1515-1527). Prediction: the mode order is unchanged (hold < linear < shaders on SSIM) and the shaders' margin over linear
shrinks by 0.5-1.5 dB against the same content at 24 -> 12, since less motion gives the blend less to lose [U]. Kill: if
at production-rate motion the recommendation is within 0.1 dB of linear on SSIM across all three sources, the family's
real-content margin is an artefact of the doubled motion, which would change the story. Cost: 3 sources x 8 segments x
4 modes = 96 renders; the 4K file is slow [U].

**P5. The weave hunt: a source-side periodicity detector (rank 5; differs in kind: it reads the source, not the output).**
Mechanism: per 64x64 block of a source frame, the 2-D autocorrelation's first off-centre peak; a block is a print when
the peak is above 0.5 at a lag of 6-32 px in both axes. Candidate blocks are then scored by P2's block margin against
the blend. Prior attempt: the weave on the masters only (4918-4972); the record names "a real clip of checked cloth" as
the next step. Prediction: BTTF and WALL-E together hold at least ten print blocks in motion at 3-11 px/frame, and on
them the recommendation's margin over the blend is at or below zero, as on the masters (`bounce-oscillating` 27.47
against 28.82, 4931). Kill: if every print block in motion reads 1 dB or more above the blend, the weave is a
synthetic-only case and its ladder crystallisation is a lower priority. Count: 1038/64 x 1920/64 = 480 blocks per
frame, 72 frames, 24 segments per film: 830k block tests per film, CPU, minutes. Cost: an afternoon; no GPU beyond P1.

**P6. A turntable filmed at 60 fps, decimated by integer factors: the first acceleration and jerk on real content, with
truth from physics (rank 6 among proposals, rank 1 among field gaps; the owner's camera).** Mechanism: a turntable at 33
1/3 or 78 rpm carries a textured disc (printed noise, the ladder's `TEX_M2` scaled) with a scale bar; its field has
constant speed omega r, centripetal acceleration omega^2 r, jerk magnitude omega^3 r, curl 2 omega, divergence and
shear zero, all from rpm and the bar. Film at 60 fps; drop frames by k = 1..8 so the rate the shader sees is 60/k and
samples per revolution sweep 46 -> 5.8 at 78 rpm. Picture kept: no people are in it, so "numbers only" is not needed.
Prior attempt: the disc scenes with analytic truth (`discaccel.py`, the pendulum render 2504-2512), synthetic only;
HANDOVER item 17 proposed, not done. Prediction (the record's own numbers transferred): the two-frame velocity reads
at gain 0.9-1.0 on the disc interior at speeds under 20 px/frame; the tri's acceleration reads at better than 20:1
across the sweep; the quad's jerk reads at 3-5:1 flat across the sweep with its gain following [2 sin(w/2)/w]^3 (0.87 at
6 samples per period, 3107-3140); the quint's jerk reads at better than 20:1 at 8 or more samples per period. Kill: if
the quint's jerk is under 10:1 at 8 samples per period on the real disc (118:1 synthetic), the fifth frame's advantage
does not transfer to real texture and lighting; if the quad's gain does not follow the truncation formula, the
mechanism claimed at 3107 is wrong on real content. Inconclusive (both poor) tips toward the rig: check the speed
first (the velocity must read 0.9 before any derivative is believed; WORKFLOW-SAVED-MEMORY 258). Cost: an afternoon
of rig and script (the owner); GPU minutes: 8 decimations x 4 shaders x 20 s = a few minutes per shader. Rotation
also tests curl magnitude on a real surface at known 2 omega, the second real tensor number after the party's 0.9.

**P7. The divergence mechanism at 0.6: three cheap splits of data already on disk (rank 7; CPU only; data local).**
Mechanism: `depth2.py`'s truth includes the head joints (THREEDIMENSIONAL 925-927); re-score with a torso-only similarity
fit (shoulders, root, hips) and the raw torso fit (b). Then split (b)'s rows by the torso's own texture proxy: the
field's local spread inside the torso (a plain shirt propagates one vector; a patterned one does not), since the
recording holds the field but not the picture. Prior attempt: body size (refuted as the cause, 950-951); the two
candidates left are the record's own (plain clothing, the nodding head, 953-956), neither tested. Prediction: dropping
the head moves the gain from 0.55-0.64 to 0.65-0.75 (the head is a fifth of the fitted points and nods against the
torso); splitting by field spread shows the low-spread half at under 0.5 and the high-spread half at 0.8 or more. Kill:
if both splits leave the gain within 0.05 of 0.6, neither candidate is the mechanism and the rendered-children bench
(exact truth, textured against plain costume) is the next step, which needs the private Metal tree (hand-off).
Cost: an hour of python on `np-scratch/lillys` and `party-analysis/depth2.npz`; no GPU; could run tonight on CPU, but a
probe copy must live in the lane's scratch, not REPO.

**P8. A real strain census from the skeleton (rank 8; CPU only).** Mechanism: the non-affine cliff sits at a velocity
gradient of 0.013 per frame, reversing the majority at 0.015 (NFRAME-LIMITS 3400-3418). Real bodies' limb strain is
readable from Vision alone: d ln L / dt of each bone's 2-D length per frame (foreshortening and reach), a lower bound on
the image strain rate the field saw. Prior attempt: none on real content; the cliff was drawn on the jelly and vortex.
Prediction: at 1280x960 and 30 fps, 2-5% of moving forearm frames exceed 0.013 per frame; scaled to 1080p24 (x1.875 in
px, x1.25 in time) the share rises to 5-10%. Kill: under 1% means smooth non-affine strain is a rare real case and the
cliff is a documented limit, not a lead; over 10% makes it the field's second real-content loss after the reach. Cost:
an hour of python on `velocity.npz`'s joints; no GPU.

Loops of a kind: P2, P3 and P5 are all "a new per-block statistic on the real tier"; P5 differs in reading the source.
P6, P7 and P8 are each a different kind (a rig, a re-score, a census).

## Refuted entries checked

NFRAME-LIMITS: the prefilter (section 8, 545-564; 5010-5018); P6/P7/PB/PC/PE (494-518); the tensor fill, twice
(2716-2728); the temporal seed as the pan's term (3838-3841); the local-agreement blend (4031-4035, 4099-4106); "size is
the cause" of the limb cliff (4232); EDGE_PROP (4368); the party's P1 torso, P2 mechanism and P4 divergence gain
(4320-4330); the weave's W1 (4983). ENERGY-TRANSFER's MISSED steps by grep (216, 315, 413, 506-526, 565, 604, 680,
797-800, 863, 917-920, 1111-1113, 2058, 2118, 2202, 2350-2356). None of P1-P8 proposes a shader mechanism; P7's
candidates are the record's own open ones (THREEDIMENSIONAL 953-956), not refuted ones.

## Hand-offs

- **To the owner (NAS):** the film with the sandstone wall (6:29-6:34) and the market-cross railing (10:16) is not among the
  local files as far as I can tell [U]; the tier's first validation is to re-score those two shots with P2 and P3 and
  confirm they come out as the worst block and the worst snap share of their segments. Also: the standard clips
  (street, bluey) for continuity with the record's numbers; checked cloth or a grille in motion for P5.
- **To the owner (camera):** P6's turntable, 60 fps, textured disc, scale bar, rpm known. A pendulum is the second rig
  (sinusoidal, period from length alone), weaker because jerk is welded to acceleration (3107-3115).
- **To the owner (decision):** whether the tier's segments file and results files live in REPO beside the ladder's, and
  whether low-bitrate local films (BTTF at 1.69 Mbit/s) are admitted with their floor noted or excluded.
- **For the instruments lane:** P2's block map and P3's reach statistic are tools; `bandmetric.py` and `panspeed.py` are
  the starting points.
- **For the ladder lane:** the four crystallisations (V-series, W-series, C-series, the weave sweep) are the ladder's; the
  tier's job is to say whether real footage still shows each after the fix.
- **Private tree:** the rendered-children bench with exact flow (P7's fallback) and the field recorder.

## Felt

- Felt: surprise, the weave's provenance, medium; the brief says eyes-in-films, the record may not. -> Read 4918-4921
  and 4966-4971: found, synthetic-first, never looked for in real footage. Became finding 3 and P5. Outcome: right.
- Felt: unease, "margin over linear" as the funnel's ranking, medium; the stairs shot beat linear and was still wrong.
  -> Dug 2389-2397 and 2529-2540: found, three of four defects sit under a positive whole-frame margin. Became finding 4
  and the tier's centre. Outcome: right.
- Felt: pull, the decimation trick turned on the field (drop frames from a 60-fps film of a turntable to sweep samples
  per period with physics as truth), high; it answers "how to test 118:1 on real content" which a plain pendulum
  cannot. -> Wrote P6 with the record's numbers as predictions. Outcome: open.
- Felt: push, reading more party probes for a fourth field proposal, low; the lane was circling. -> Stopped at P8.

## Verdicts

Reasoned: the record has a real-footage benchmark but not a real-footage tier. What exists reports whole-frame means
over a few fixed seconds, and the record's own numbers show those means cannot see three of the four real defects it
knows about (the stairs under a +3 dB margin, the railing under a +0.2 dB whole-frame change, the pan positive except
at its two fastest frames) and never looked for the fourth. A tier that freezes segments (fixed plus random), scores
blocks and frames, keeps the series and reports extremes would have ranked the cage and the pan without eyes, would have
ranked the stairs by its field spread rather than its picture, and can look for the weave with a source-side test; the
local files allow it tonight at production-rate motion for the first time (the 60-fps sources). On the field, the
single largest gap is a real derivative of any order, and the cheapest instrument is a turntable at known rpm filmed at
60 fps and decimated, which puts the quint's 118:1 claim in front of real texture with physics as the key. Nothing here
is measured; everything is a design with a kill test.

Gut: the block map will find something in BTTF the first evening it runs; the turntable will show the quint's jerk
transferring at half its synthetic ratio, and that half will still be ten times the quad's.
