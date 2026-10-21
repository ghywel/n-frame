# Swarm brief: fresh eyes on the N-frame interpolation shaders (2026-10-21)

You are one lane of a swarm of eight, each a fresh reader of one slice of a research project. The owner, Gareth,
asked for this: "we did a great deal of hard work on our interpolation shaders, which are truly innovative compared to
what was on the market. But i am sure there is more we can do to improve and optimise them ... it would be the first
time a fresh look would have been passed to a swarm, and gives us a great deal of scope for fresh eyes. I am thinking
in particular the synthetic tests, many of which would have been developed early and will be poorly optimised, and
may even not be brilliant candidates for the test they are supposed to represent." Your lane is named in your prompt.

## The project in one paragraph

N-frame temporal interpolation shaders: GLSL run through a patched libplacebo inside FFmpeg (Vulkan), the patch
handing a custom shader a window of 2 to 6 source frames (`PL_HOOK_FRAME_MIX`). The two-frame base
(`shaders/bidirectional-interpolation.glsl`) is a coarse-to-fine block matcher with a flow cache persisted across
frames; generators in `tests/gen_*.py` derive the family from it (variational cascade, propagated bases, 3-6 frame
windows, and generator switches such as the global seed, the cage, the energy channel, the alias carry, the outline
adoption, the print lattice, the cut gate). The recommended picture shader is
`shaders/bidirectional-interpolation-variational-propagated.glsl`; the player's High tier is `...-global-cage-energy-
carry-adopt-lattice-cut.glsl`. The same passes, read out rather than painted, give a per-texel motion FIELD (velocity;
acceleration from 3 frames; jerk from 4-5), which is the project's real product. Correctness is measured on a frozen
ladder of 42 synthetic scenes with exact ground truth (`tests/scenes.sh`, scored by `tests/bench.sh` + `tests/analyze.py`,
PSNR of interpolated frames against a native 60 fps render, hold and linear as baselines, capped at 40 dB) and on real
footage by decimate-and-reconstruct. A Metal port (NFrameDemo, a separate private tree) is held in lockstep; it is not
your concern.

## The repository

Read-only for you: `REPO` (call it REPO).
Start with `REPO/README.md` (skim), then your lane's files. The record is large; the big ones are
`NFRAME-LIMITS.md` (389 KB, the front line: sections 1-9 then dated subsections to 2026-10-04), `ENERGY-TRANSFER.md`
(296 KB, the 2026-09-30 to 10-01 lead-4 work: weave, outline adoption, print lattice, trust gate), `SHADERS.md` (113 KB,
the family and its variants), `PRIOR-ART.md` (92 KB), `REPAIRS.md` (open leads L5-L10), `tests/TESTING.md` (the
ladder and its dated record), `tests/TOOLS.md` (every tool and the trap it avoids), `tests/probes/PROBES.md` (every
one-off measurement). **Do not cat a large file whole.** `grep -n` for headings and terms, then read the sections you
need with offsets. Your lane's prompt names where to start.

## Rules, each from something that went wrong here

1. **Paper only. No GPU.** Do not run `bench.sh`, `realbench.sh`, `gateset.sh`, `lockstep.sh`, any `probes/*/*.sh`, or any
   ffmpeg command with `-init_hw_device vulkan`. One GPU job at a time is a hard rule on this machine and the owner's
   queue owns it tonight. CPU-only ffmpeg (`-f lavfi` sources to a file or `-f null`, no libplacebo) is allowed if a lane
   needs to look at a scene; python with numpy is `$HOME/np-build/venv/bin/python3`.
2. **Write nothing into REPO.** Your only output is your lane's file, named in your prompt, under
   `~/Developer/np-scratch/swarm-20261021/`. Scratch for anything else: a subfolder of that named after
   your lane.
3. **Read the refuted list before proposing anything.** `grep -n -i "refuted" REPO/NFRAME-LIMITS.md` and the
   "REFUTED -- do not retry" paragraphs; also `REPO/ENERGY-TRANSFER.md` steps marked MISSED. A proposal that repeats a
   refuted mechanism without a new cue is a wasted lane. Say which refuted entries you checked against.
4. **Three kinds of sentence.** Every claim is [R] (you read it: cite `file:line` or the heading), [J] (your
   judgement), or [U] (unchecked: you believe it but did not verify). Mark [U] honestly; an unmarked guess costs more
   than a marked one. You will have no [M] (measured) claims tonight unless a CPU-only check gives one; say so.
5. **Every proposal carries:** the mechanism in two sentences; the record's nearest prior attempt and why this is not
   it; a PREDICTION with numbers (which ladder cases move and by roughly how much, or what a new case would read, or
   how many passes/ms are saved); a KILL TEST written first (what outcome kills it, what confirms it, which way an
   inconclusive result tips); the COST to test (GPU minutes on the M5: a full 42-case ladder run is about 6 minutes
   per shader; a generator switch costs an hour of writing); and its RANK among your proposals by certainty of return
   per cost. Cheap steps before leaps: a step whose value is unknown only because nobody looked outranks a leap.
6. **Instinct, logged.** This project runs the instinct rule (`REPO/INSTINCT-STRATEGY.md`, read its first 130 lines).
   When a felt signal shifts your attention (unease, pull, push, surprise, eureka, or a tint), write it at once as one
   line in a "Felt" section of your report: `Felt: <kind>, <object>, <strength>; <first guess>. -> <what you did>.`
   Log only real shifts; a decorative feeling spoils calibration. End with a reasoned verdict and a one-line gut
   verdict; if they disagree, say what would settle it.
7. **Loops of a kind.** If two of your proposals are of the same kind, say so and make the next one differ in kind.
8. **Count before you search.** For any proposal that enumerates (cases, passes, taps), state the size of the
   enumeration first.
9. **Plain prose.** Short sentences, no adjectives of size, every claim scoped. Name files, not "the code". Report
   length: 1,500 to 4,000 words. A table where a table is clearer.
10. **Token discipline.** Read what your lane needs and no more. If a question needs another lane's ground, note it
    as a hand-off ("for the ladder lane: ...") rather than reading it yourself.

## Report shape

```
# Lane <name>: <one-line finding>
## What I read                 (files and sections, with line ranges; what I deliberately did not read)
## Findings                    (numbered; each tagged [R]/[J]/[U]; the ones that change the story first)
## Proposals, ranked           (each with mechanism, prior attempt, prediction, kill test, cost, rank)
## Refuted entries checked     (the list)
## Hand-offs                   (to other lanes or to the owner: decisions that are his)
## Felt                        (the instinct lines)
## Verdicts                    (reasoned; gut)
```

The owner reads renders and reports in mechanisms; he wants a diagnosis done, not discussed. He has ruled some things
already, and they are not yours to reopen: the picture recommendation (variational-propagated, ZERO_SEED on in the
picture bases); the family is not rebuilt from scratch (measured reasons, NFRAME-LIMITS "THE SHADER FAMILY IS NOT
BEING REBUILT", 2026-09-10); a change that costs time ships as a variant or a switch, never over the working file.
