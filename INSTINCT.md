# INSTINCT: the felt log, the set-aside pulls and the incubator

*Started 2026-10-21 by Claude at Gareth's request, when the instinct technique came over from the prize-problem
project. The method is [INSTINCT-STRATEGY.md](INSTINCT-STRATEGY.md); the rule is `instinct` in
[WORKFLOW-SAVED-MEMORY.md](WORKFLOW-SAVED-MEMORY.md#instinct). A feeling chooses where to look and when to persist. It
never upgrades a status: nothing here is a measurement, and nothing here changes one.*

**What goes here.** Three lists, appended, never rewritten except to add an outcome or a return line.

1. **The felt log.** One line per signal, written when it arises:
   `date time, worker: kind (tint), object, strength; first guess. -> action. Outcome: right / wrong / missed / open.`
   "Missed" records a fault that a test, a reviewer or Gareth found and no feeling flagged. Those lines calibrate the
   rest.
2. **The set-aside pulls.** A pull that goes past unworked is caught here in two fields only, with no judgement:
   **Doing** (what I was doing when it came) and **Pull** (what it was, in the words it came in). A dated **Return**
   line is added when it is picked up; a resolved entry is struck through and left in place.
3. **The incubator.** Hard questions parked for later, one dated line each. Glance down it at the start of a session
   and at each step back, without working it; anything that surfaces goes into the felt log as a eureka.

## The felt log

*The first four lines were written at 20:17 BST on 2026-10-21 from this session's steps; their times are approximate.*

- 2026-10-21 20:01, Claude: none felt; typed `echo ===` under zsh, which expands it and fails (the map's trap G10.4),
  and did it again at 20:09. Outcome: missed. Note: a trap I had just read is still tripped when commands are
  composed fast; separators are written with `printf`.
- 2026-10-21 20:02, Claude: unease (niggle), NFrameDemo's register has no entry for REPAIRS L2 (the snap's
  retirement) reaching the Metal side, yet all 18 graphs match the GLSL by hash, low; first guess: lockstep
  regenerated them on 10-12 without a P-entry. -> set aside (pull 1). Outcome: open.
- 2026-10-21 20:08, Claude: surprise, placego's local clone has none of the instinct files Gareth says were learned
  there, medium; first guess: they were pushed from another clone. -> fetched origin. Found: the seven instinct files and
  AGENTS.md are on origin/main, and the strategy is byte-identical to the copy Gareth put here. Outcome: right.
- 2026-10-21 20:12, Claude: unease (misgiving), libplacebo's change of `pl_frame_mix` timestamps from float to double
  (API 375) touches the window code that frame-mix-hook.patch extends, medium; first guess: it compiles, and could
  move which frames a window of five or more gets where a boundary frame rounds out. -> a five-frame check goes into
  the build gate's pre-registration. Outcome: right. The window probe (probes/window/window_live.sh) found 6 of 63
  windows flipped on the new build, every one a tie (the four-frame window at N:N became [-1, 0, +1, +2]); the
  patch's comparison now takes a tolerance (tests/TESTING.md, "The research build updated (2026-10-21)").
- 2026-10-21 about 20:21, Claude: surprise (startle), on the WORKING build the hook's timestamps away from phase 0 are a few
  thousandths of a frame off, and the pair straddling the output reads 0.9959 apart instead of 1, medium; first
  guess: the queue's own estimate, not our patch. -> measured on both builds: the same. Set aside (pull 2).
  Outcome: wrong: the startle was at the instrument, not the queue (the dissonance below found it).
- 2026-10-21 about 20:23, Claude: none felt; a check that the fixed patch applies to the old pin ran after a checkout that
  had failed (`;` let it run on), so it tested the new pin again and printed "applies to c42968d too". Caught by
  reading the raw output, not by any feeling. Outcome: missed. Note: a check chained after a step that can fail is
  chained with `&&`; re-run in a worktree at the old pin, and it does apply.
- 2026-10-21 20:29, Claude: unease (dissonance), the timestamp error checks out on both builds and I do not believe
  it: the readings are exact fp16 values (-0.40234 = 1945/4096, +0.59375 = 1100/2048) and REPAIRS L10 names an fp16
  stage on every readback, high; first guess: the probe's own floor. -> the probe re-encoded (whole part and fraction
  in separate channels), to re-run when the GPU is free. Outcome: right (20:55): re-encoded, both builds read every
  timestamp within the 0.0005 resolution and the straddling pair exactly 1.0000; the 0.9959 was the probe's fp16 floor.
- 2026-10-21 21:01, Claude: none felt; edited build-macos.sh's header while a background run of it was in its ffmpeg
  stage, and bash, reading the file as it goes, hit "unexpected EOF" at the verify stage (the map's trap G10.2, read
  this evening). The build itself was complete; the verify stage was re-run alone. Outcome: missed. Note: before
  editing any script, check `ps` for a run of it.
- 2026-10-21 21:11, Claude: unease (misgiving), lockstep's painting check read acceleration 32.14 and jerk 43.14 dB
  where 10-04 read 31.89 and 44.44, medium; first guess: the new build's tail render. -> dug one block: the step runs
  inside the Metal app alone, no FFmpeg; repeated twice, identical to the hundredth. Found: a stable app-side change
  since the 10-12 rebuild, not the build, not noise; recorded OPEN in NFrameDemo's register. Outcome: right (something
  was there), wrong about the suspect.
- 2026-10-21 21:25, Claude: pull (curiosity), Gareth's swarm proposal, high; first guess: the first fresh-eyes pass
  over a record only two readers have ever held, and his instinct about the early synthetic cases is the kind of
  thing a fresh reader sees first. -> designed as nine paper lanes with a shared brief, kill tests required, GPU
  withheld until the judging (G6.1); the ninth lane is the random-chaos step (an outsider reading only the lay
  layer). Outcome: right (22:01): nine lanes, six findings that change the story, two of them confirmed by the judge
  from the gate logs and two by GPU the same evening (the stairs' wall: V2x 41 against V2 29).
- 2026-10-21 22:01, Claude: pull (delight), the V2x / H2x / V3x numbers, high; "that is clean": a truth repaired by
  one expression and the alias work's real size appears. -> said plainly in TESTING.md; no extra block taken.
  Outcome: right (the calibration signal that the ladder line is alive).
- 2026-10-21 22:17, Claude: none felt; a loop over `$ALL_CASES` written in the tool shell (zsh) ran once on the whole
  string and rendered "UNKNOWN_CASE", the map's G10.4, read this evening and tripped for the second kind of time (after
  `echo ===`). Caught by reading the log, not by any feeling. Outcome: missed. Note: every loop over a word list goes
  through `bash -c`; the probes are written `#!/bin/bash` for this reason and must be run with `bash` when not
  executable.
- 2026-10-21 22:34, Claude: none felt; typed `cat -A` (GNU) on macOS, where it does not exist (G10.6: `cat -e`), while
  reading the prune gate's failure. The third shell trap of the evening tripped after reading its rule; the pattern is
  speed under a GPU result, not ignorance. Outcome: missed. Note: on this Mac, `cat -e`, `printf`, `bash -c` loops.
- 2026-10-21 22:34, Claude: satisfaction, the prune gate refusing both PRUNE levels on a parse error, medium; "the gate
  did its job before any number was believed": the lane's own [U] (its CPU check does not exercise libplacebo's
  preamble) was the exact hole. -> handed the diff back to the lane with the cause located. Outcome: right (the
  instrument was finer than the fault).
- 2026-10-21 22:41, Claude: none felt; ran compile_all.sh on the pruned files without first running it on a committed
  file, and read "4 fail" as a compile failure twice over. Its default source did not exist here, so every file failed
  on "Error opening input" (G1.5: a check must first be shown to pass on the known-good). The direct render at
  -loglevel warning showed the files compile. Outcome: missed. Fix: compile_all refuses a missing source (committed).
- 2026-10-21 23:41, Claude: none felt; read limb.sh's table with its header truncated and assumed the columns followed
  SHADERS order (the table sorts the log names, the bare recommendation last), and told the reach lane "no change"
  where the energy base had moved +0.5 to +0.9. Caught by the numbers not adding up against the first run, not by any
  feeling; corrected within minutes. Outcome: missed. Note: a probe's column order is read from its script, never
  assumed; print the header untruncated.
- 2026-10-21 23:41, Claude: disappointment, LOCAL_CENTRE killed on the ladder by the aperture series (P1 -6.8), medium;
  "the guess was wrong, and the fall is exact and small": the witness (P1/P5 against F2/L8 up) fixes where the centre
  is not. -> the switch stays as a documented trade; the question (an aperture gate on the centre) goes to the lane on
  paper. Outcome: right (a refuted candidate is the day's best data).
- 2026-10-21 23:52, Claude: satisfaction, the prune's eight identity gates on the Arc, high; "closed honestly": the
  prediction (byte-identical, time down by the dispatch share) held on the host that can judge it, after two refusals
  that were the instruments'. Outcome: right.
- 2026-10-21 23:52, Claude: surprise (startle), PHASE_FETCH moving L7 by +19.7 dB while leaving the comb at 12 untouched
  and costing the period-24 family 2.5 to 6.7, high; first guess: the point-sampled Moire is the lock at one coarse
  texel and the match at one and a half. -> written into NFRAME-LIMITS as a trade along the period; the gate form goes
  to the lane on paper. Outcome: open (the mechanism is a reading, not yet a measurement).
- 2026-10-22 00:06, Claude: none felt; the tick's `git add -A` swept the periodic lane's in-progress files (two D1 scenes,
  a regions row, c3_oracle.py) into a pushed commit before the lane had reported. One writer per file set is my own
  rule, and the coordinator commits only reviewed deliverables. Caught on reading the commit's file list; the files
  checked sound after the fact (scenes parse, both D1 scenes bit-identical under scenecheck). Outcome: missed. Fix:
  stage by name on every tick while a lane is writing.
- 2026-10-22 00:13, Claude: delight, the region column confirming the re-ranking with its control to the hundredth,
  high; "that is clean": a prediction from the saved logs, a calibrated instrument, a render, the order as predicted.
  -> said plainly in TESTING.md; the headline column is Gareth's. Outcome: right.
- 2026-10-22 00:18, Claude: satisfaction, D1's field read, medium; "closed honestly": the undecidable case the record
  named on 2026-09-28 is a measured one, the first pair's coin and persistence, and the lane's two-domain guess fell to
  its own kill test within the hour. Outcome: right.
- 2026-10-22 11:30, Claude: unease (niggle), "who else parses analyze.py's rows?" while making the region column the
  default, medium; first guess: a gate table splits on whitespace. -> dug: probes/limb/gatetable.py kept 0 of 45 rows of
  the new output, and would already have done so with last night's `--min`, silently. Found and fixed (first column
  group only; a stderr line on any mismatch). Outcome: right.
- 2026-10-22 11:41, Claude: none felt; the sticky probe's first run reported "identical on all 240 outputs" for a shader
  that had never compiled (a blank line inside a pass header ends the header; libplacebo then mixed with its own mixer,
  and compared the fallback with itself). Caught only because the counterfactual (the skip without STICKY) also came
  back identical. Outcome: missed. Note: the bench guards against a silent fallback, a new probe must too; it now
  refuses any render whose hook did not run. The counterfactual earned its place.
- 2026-10-22 11:45, Claude: unease (niggle), the cost lane's mirror comparison: three propagation twins that do not match
  their mirrors, in a family whose other eleven twins all do, high; first guess: a shared helper read the wrong frame's
  luma since the fusion. -> confirmed by the lane (`prop_conf()` reads LUMA_A_E for both directions); REPAIRS L11, a
  variant and a ladder gate next. Outcome: right that it was a defect in form; the gate (same day) found no effect on
  High and a trade on the quad, so it stays a variant, and why the wrong read helps L2 and M2 is a new question.
- 2026-10-22 16:12, Claude: none felt; the sticky probe's first Arc run printed "DIFFERENT (0 frames)" and "the
  counterfactual failed", a verdict over nothing: Mesa cannot configure libplacebo's rgb48le output, every render
  failed, and the guard I added at 11:41 looked only for compile errors. Caught because the line read absurd, not by
  the probe. Outcome: missed (second time today in the same probe). Fix: rgba64le, and the probe refuses a render that
  failed to configure or produced no frame. Note: a guard against one way of rendering nothing is not a guard against
  rendering nothing; count the frames.
- 2026-10-22 19:45, Claude: unease (niggle), writing PHASE_GATE's pre-registration: on exact synthetic periods both
  coarse basins can match at near-zero SAD, so "cost_b within 10 percent of cost_a" may never fire where the fetch
  loses, medium. Named in PREREG.md before the render, with a firing tap built while the ladder ran. -> confirmed: the
  V-family's gap sat at the tap's +3.1 ceiling (an exact zero basin), P1's was decisive at -0.68, and the gate opened
  only on P5, where the fetch was right. Outcome: right. Note: a relative cost test needs a floor where the cost can
  be zero; and a gate's cue should be checked on the one pair that differs only in the variable it must see (P1/P5).
- 2026-10-22 20:40, Claude: none felt; C3's probe registered a units check (the wall's median within 1 px) on a wall the
  estimator itself cannot read (flat 32 px blocks turning at 1-2 px a frame); it refused, and the slope test I put in
  its place refused for the same reason. Outcome: missed twice, caught by the refusals, mended by a clean calibration
  scene (10 px/frame, read 9.69) and both amendments marked post hoc. Note: an instrument's check must run on content
  the instrument is known to read; calibrate on a clean case, then measure the hard one.
- 2026-10-22 20:22, Claude: none felt; the zsh word-splitting trap again: `env $HI` passed the High tier's whole
  switch string as one word, and the "High" I built was the plain recommendation. Caught by the identity check against
  the shipped High file, which is why it is there. Outcome: missed, caught. Note: `${=VAR}` in zsh, or bash -c.
- 2026-10-22 20:38, Claude: delight, medium-high, BAR_REDECIDE passing with nothing on the ladder lost and C1 rising
  unasked; and a check on it: the rule is a prior that wins because C3's truth is the slowest basin. Named in L009 as
  the review target.
- 2026-10-23 05:24, Claude: unease (niggle), reading GPT's guard: "the incoming vector refined over +-1 px, the
  proposal at its exact minimum" read as a comparison of unequals, medium-high. Checked on GPT's own raw outputs before
  building anything: the guard's flips sit at the broad extrema where High was 1.7 px off its comb, and GPT's count
  missed them by counting only seeds within .5 px. -> confirmed: BAR_BASIN, the like-for-like comparison, takes the
  flips to zero. Outcome: right. Note: when a guard compares two candidates, refine them the same way.
- 2026-10-23 05:30, Claude: none felt; the Arc export ALARMED on M2c_period40_v6 because my own calibration check
  matched every case named M2c. Outcome: missed (my tool), caught by the alarm. Note: a calibration gate keys on the
  exact case it calibrates, never a prefix.
- 2026-10-23 05:47, Claude: surprise, high, the random draws: the plain pass gaining +10 dB on a print where High has
  no correct seed at all, by choosing one wrong alias everywhere. I had predicted the guard's cost would be nil; my
  guess that the snap would recover it was wrong too. Measured instead: coherence (seams halved). Outcome: missed,
  found by the draw. Note: on a pure period the picture rewards a consistent alias, not the true one; a tie rule
  should look at the neighbourhood.
- 2026-10-23 08:25, Claude: none felt; writing the content-type table I typed a "linear" row and two animation deltas
  from my head instead of from scores.json (32.35 where the data says 30.84; +0.07 where it says +0.05). Caught by
  recomputing every cell before the commit. Outcome: missed, caught. Note: a table row is copied from the run's own
  output or computed by a script, never composed; check every cell against the JSON before it is committed.
- 2026-10-23 11:58, Claude: unease (niggle), medium, reading F1's first good fade numbers: "a global fit on a coarse grid
  will be fooled by something moving"; I had registered a ramp control and no periodic one. -> confirmed by the ladder an
  hour later: moving stairs read as a gain of 1.2, H2x -4.6 dB; GPT's attack (G025) had named the class. Outcome: right,
  but I did not act on it before the long run. Note: when a reviewer names an identifiability hole, add the control
  for it before the run, not after the kill.
- 2026-10-25 17:32, Claude: none felt; the imports record's section times from D1b on (16:40 to 19:20) ran ahead of the
  clock, written without `date`, and L021/L022 said BST on the day the clocks went back to GMT. Caught when `date` read
  17:32 while I was about to write 20:10. Outcome: missed, caught; corrected to the commit times. Note: a time in a
  record comes from `date` or the commit, never from a sense of how long the work took.
- 2026-10-25 20:20, Claude: none felt; two instrument slips on Form Q, both caught before a result was read: the cost
  script took `time.perf_counter()` in separate Python processes (meaningless across them; the first table read zero for
  every shader), and the pre-registration said QUAD_MODE 1 gates by its residual, which its code computes but never
  applies. Outcome: missed, caught (re-timed from one process; the record corrected). Note: a timer must live in the
  process that spans the timed work; a mechanism named in a registration is read in the code first, not from the
  design document's description of it.

## The set-aside pulls

Review return, GPT, 2026-10-22: while reading L009, the pooled scalar Moire slope did not seem sufficient to identify
the proposed mixture. The bounded paper/CPU check found the omitted orientation dependence and that S.xy is one of
three coarse candidates, not the selected flow. Outcome: right about the missing premise; the actual mixture remains
open. This is a retrospective attention record, not a pre-registered prediction. See
[the review](tests/probes/cage/BAR-REVIEW.md).

1. ~~**2026-10-21.** **Doing:** reading NFrameDemo's METALPORT.md to refresh on the Metal port. **Pull:** "There is no
   entry for L2 reaching the Metal side. Where were the graphs regenerated, and who checked them?"~~
   **Return, 2026-10-21 21:11.** Investigated: the 10-12 lockstep regenerated the stale graphs after L2 (PASS in
   3 min 19 s) and wrote no register entry; today's hash step shows every graph on the post-L2 GLSL. Closed by the
   2026-10-21 entry in NFrameDemo's METALPORT.md.
2. ~~**2026-10-21.** **Doing:** reading the window probe's first output on the working build. **Pull:** "The straddling
   pair is 0.9959 apart. The hook's `mix_t` is then about 0.404 where the output is at 0.400. Where does the queue
   lose four thousandths, and does the ladder's ceiling feel it?"~~
   **Return, 2026-10-21 20:56.** Already resolved: by the probe's own repair. Its first encoding put the timestamp
   through the readback's fp16 stage at a scale where the step is 0.004-0.008 of a frame; split into a whole part and
   a fraction, both builds read the pair exactly 1.0000 apart. The queue loses nothing.

## The incubator

*Parked from the record on 2026-10-21. Each points to where the question is written up; none was re-checked today.*

- 2026-10-21: C3, bars rotating about a translating origin. The across-bar error at 1-2 px/frame, a period out,
  where the zero descent has no ridge and the coherence gate is rightly closed (NFRAME-LIMITS.md, "The cage").
- 2026-10-21: the rotating cube, the one synthetic case where linear beats every shader: per-face affine motion
  with self-occlusion at the turning edges. Affine matching and occlusion reasoning are still on paper
  (NFRAME-LIMITS.md, "The cube").
- 2026-10-21: a print drifting behind a still window, the undecidable case, never built (NFRAME-LIMITS.md, "The
  aperture in the carry").
- 2026-10-21: smooth non-affine strain on single-frequency content near the coarse level's Nyquist reverses in the
  coarse search; the zero seed rescues rigid motion there, not strain (NFRAME-LIMITS.md, "The non-affine failure").
- 2026-10-21: on real bodies divergence reads about 0.6 of its magnitude while curl reads 0.9; the mechanism is open
  (THREEDIMENSIONAL.md 9.8).
- 2026-10-21: Gareth's Newton's-cradle question, whether the field can infer energy it cannot see
  (ENERGY-TRANSFER.md).
