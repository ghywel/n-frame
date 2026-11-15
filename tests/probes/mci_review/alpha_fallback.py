#!/usr/bin/env python3
"""Generate the bounded YUVA fallback repair after Local's fused.patch.

The input FFmpeg checkout is read-only. Both fused allocation and dispatch use
one predicate. Unsupported plane counts use the original contribution-list
renderer, which already writes the alpha plane. No motion-search code changes.

    alpha_fallback.py --source /path/to/vf_minterpolate.c --out /tmp/alpha-fix
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path


PREDICATE = """/* The fused renderer implements gray and three-plane YUV, not alpha.
 * Use exactly the same predicate for allocation and execution: a fallback must
 * have the original contribution lists available before it renders. */
static int mci_fused_enabled(const MIContext *mi_ctx)
{
    return mi_ctx->me_mode == ME_MODE_BIDIR && (mi_ctx->mci_accel & 16) &&
           (mi_ctx->nb_planes == 1 || mi_ctx->nb_planes == 3);
}

"""


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"expected one exact anchor: {old!r}")
    return text.replace(old, new, 1)


def transform(text):
    if "mci_fused_enabled" in text:
        raise ValueError("fallback repair already present")
    if "static void fused_dispatch(" not in text or "static int search_wave_jobs(" not in text:
        raise ValueError("expected Local's fused/wavefront source")
    text = once(text, "#define OFFSET(x) offsetof(MIContext, x)\n",
                PREDICATE + "#define OFFSET(x) offsetof(MIContext, x)\n")
    text = once(text, "if (mi_ctx->me_mode == ME_MODE_BIDIR && (mi_ctx->mci_accel & 16)) {",
                "if (mci_fused_enabled(mi_ctx)) {")
    text = once(text, "                if (mi_ctx->mci_accel & 16) {",
                "                if (mci_fused_enabled(mi_ctx)) {")
    if text.count("if (mci_fused_enabled(mi_ctx)) {") != 2:
        raise AssertionError("allocation and dispatch must share the predicate")
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    output = a.out / "vf_minterpolate.c"
    if output.resolve() == a.source.resolve():
        raise ValueError("input and generated output must differ")
    before = a.source.read_text()
    after = transform(before)
    try:
        transform(after)
    except ValueError:
        pass
    else:
        raise AssertionError("already-applied source was accepted")
    patch = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="a/libavfilter/vf_minterpolate.c", tofile="b/libavfilter/vf_minterpolate.c"))
    a.out.mkdir(parents=True, exist_ok=True)
    output.write_text(after)
    (a.out / "alpha-fallback.patch").write_text(patch)
    digest = lambda x: hashlib.sha256(x).hexdigest()
    meta = dict(status="generated_not_built", source_sha256=digest(before.encode()),
        fixed_sha256=digest(after.encode()), patch_sha256=digest(patch.encode()),
        generator_sha256=digest(Path(__file__).read_bytes()), allocation_dispatch_predicate="shared",
        acceleration_plane_counts=[1, 3], original_renderer_fallback="all other plane counts")
    (a.out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
