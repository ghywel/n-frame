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
  Outcome: open.
- 2026-10-21 about 20:23, Claude: none felt; a check that the fixed patch applies to the old pin ran after a checkout that
  had failed (`;` let it run on), so it tested the new pin again and printed "applies to c42968d too". Caught by
  reading the raw output, not by any feeling. Outcome: missed. Note: a check chained after a step that can fail is
  chained with `&&`; re-run in a worktree at the old pin, and it does apply.
- 2026-10-21 20:29, Claude: unease (dissonance), the timestamp error checks out on both builds and I do not believe
  it: the readings are exact fp16 values (-0.40234 = 1945/4096, +0.59375 = 1100/2048) and REPAIRS L10 names an fp16
  stage on every readback, high; first guess: the probe's own floor. -> the probe re-encoded (whole part and fraction
  in separate channels), to re-run when the GPU is free. Outcome: open.

## The set-aside pulls

1. **2026-10-21.** **Doing:** reading NFrameDemo's METALPORT.md to refresh on the Metal port. **Pull:** "There is no
   entry for L2 reaching the Metal side. Where were the graphs regenerated, and who checked them?"
2. **2026-10-21.** **Doing:** reading the window probe's first output on the working build. **Pull:** "The straddling
   pair is 0.9959 apart. The hook's `mix_t` is then about 0.404 where the output is at 0.400. Where does the queue
   lose four thousandths, and does the ladder's ceiling feel it?"

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
