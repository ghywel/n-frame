# The bases' sources

The four hand-written bases every generated shader is built from: `bidirectional-interpolation.glsl` (the base),
`-seeded`, `-propagated` and `-animation`. Edit them here, never in `shaders/`. Then:

1. `tests/gen_bases.py` writes the shipped files in `shaders/`, with the passes nothing reads removed (`PRUNE=2`,
   proven byte-identical in output on the Arc, 2026-10-22);
2. the generators rebuild the family (the recipes: [SHADERS.md, "How each file is made"](../../SHADERS.md#how-each-file-is-made-hand-maintained-or-generated));
3. `tests/smoke.sh` checks both (step 2b: the shipped bases are what these make).

Why the split (2026-10-22, [REPAIRS.md](../../REPAIRS.md) L11): a generator needs every pass of a base, while the
shipped two-frame file carries passes nothing reads. Gareth: "The bases are probably the most critical shaders, since
problems in the base are iterated to the procedurally generated."
