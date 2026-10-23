# Switch wiring and build audit, 2026-10-23

Run against n-frame e85c1d6; generator/shader sources were not modified. The owner supplied SWITCH-AUDIT.md as the
initial inventory. `audit.py` scans 42 environment reads for 37 distinct controls, then generates 112 counterfactual
variants with the environment cleared of those controls. It compares executable text/directives, excluding comments
and descriptions. **63/63 checks pass.** These are wiring/contract checks, not 63 image-quality gates.

Coverage: every switch and numeric/enumerated knob named in the initial audit, including each N-frame sticky form;
quad/quint/sext foresight scope; source-sensitive ZERO_SEED; latent knobs without their parent feature; invalid
parent/child settings, incompatible BAR variants, invalid PRUNE and incompatible trust modes. A deliberately false
self-difference is rejected. Changing `GLOBAL_SEED` from `0` to `true` changes nothing: flags require literal `1`.

The first run passed 58/62 checks: a mistaken expectation that the seeded base still had ZERO_SEED off, and three
aperture invocations that passed a bare path where that generator requires a literal path. The source audit corrected
the expectation (seeded and propagated both already have it on) and the harness supplied an explicit aperture source
path. A deliberately zero-seed-disabled copy outside the repository then proves force-on changes the implementation.
Neither production source nor a quality threshold was changed to make the checks pass. Both run folders are retained.

`compile.py` validates 43 distinct ON-side representative artifacts. **38 compile successfully**, producing **2,366
per-pass GLSL/SPIR-V/Metal translations**. The **five STICKY artifacts are rejected as expected** by gen_metal.py,
which does not implement `//!STICKY`. This is a host compatibility finding, not an unexplained shader build failure.
No unexpected compilation failures. Arbitrary parameter values/combinations are not covered by this finite matrix.

`rebuild_generated.py`'s unchanged-source control also reproduces **35/35** shipped generated files. No hand edits to
generated source, no source-app rebuild, no installed-device change, and no fresh GPU quality gates in this block.
The quality/default review cites the project's existing recorded experiments with their limits.

## Cadence resource witness

Read-only inspection: Player/Sources/Cadence/Playback.swift selects High by default, then Standard, then Low on
performance fallback. Player/project.yml copies Bench/Resources/graphs. This means generator defaults alone cannot
identify the settings the player executes. At the final inspection all six tier graph source hashes match the
current repo GLSL, including its PRUNE=2 generation. Pass counts include seven read_view-gated reading passes.

| tier | size | graph passes | source SHA256 |
|---|---|---:|---|
| Low | ordinary | 43 | ed99d3fa01a562734abef0a7403a82c6cd06eb483ff35c78df5aa69718da18bd |
| Low | 4K | 43 | 448e77b5018dd5cf6a87b7731b245ee111213f9c2bce5e866735fc311c7135e3 |
| Standard | ordinary | 63 | b6c3a950a725cfdf6d95af9311586c9dcab54d82d555a9b776db077c374f4136 |
| Standard | 4K | 63 | aaa5ff955f9abc5cdcf3a66e421c7117549a9e2436b38c23ccbb48887e492be2 |
| High | ordinary | 82 | 8d8cecce658d570fede309988f2b3478cae9618a5ea3f6741c152dccedb33faa |
| High | 4K | 82 | 07bc2d7fc4cf0a115af6c41a419a581f46beaa881c0840efb48ff828f66ccdb3 |

All six windows are two frames, and read_view/read_alpha/read_plate defaults are 0/0/1. Metadata is a resource-tree
witness, not proof of the contents of every installed app or of compiled-library identity on every device. The
initial audit's pre-PRUNE deployment statement must be updated; do not infer current deployment from the old note.
The original before-pruning hashes appeared in the first inspection, so final conclusions use the later consistent
resource/hash snapshot. No cause for the intervening resource-state difference is inferred.

## Reproduce

    PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/switches/audit.py --out "$NP_SCRATCH/switch-audit" \
        --cadence "$CADENCE_SOURCE"
    PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/switches/compile.py "$NP_SCRATCH/switch-audit"
    PYTHONDONTWRITEBYTECODE=1 PY=python3 python3 tests/probes/repairs/rebuild_generated.py "$NP_SCRATCH/switch-rebuilt"

The Cadence argument is optional. No private app files are copied into the report. Compilation needs glslc and
spirv-cross on PATH; the wiring audit uses the running Python. Run data for this block:
`$NP_SCRATCH/switch-audit-20261023/` (initial run), `v2/` (corrected matrix, results.json, compilation.json, variants and
logs), and `rebuilt/` (unchanged-source control). JSON source constants also record the distinct normal and reading-tail
DIAG_HOLD_ANCHOR values so a grep of the whole file cannot be mistaken for the normal path's default.
