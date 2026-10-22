#!/usr/bin/env python3
"""THE PAIR CACHE SKIPPED, NOT JUST SHORT-CIRCUITED: a switch for the generators (2026-10-22, patch stage 2; Gareth's
decision 4, "Proceed with this one as you see fit").

    sticky_cache.py <in.glsl> <out.glsl>        or, as a module: sticky_cache.add(text) -> (text, n)

The pair cache (since 2026-08) makes a pass whose work depends only on the window of source frames begin
    ivec2 coord = ivec2(X_pos * X_size);
    if (!pair_changed)
        return imageLoad(CACHE, coord);
so on the outputs that reuse the window (60% at 24 -> 60) it does almost no arithmetic. It is still DISPATCHED, and on
this engine a dispatch costs more than the arithmetic of a cheap pass (feedback: the engine's cost is dispatch count).
The patch (frame-mix-hook.patch, 2026-10-22) lets //!WHEN read pair_changed and adds //!STICKY: the pass renders into a
texture of its own and, when its WHEN is false, offers that texture again under its //!SAVE name. Here each such pass
gains both lines, so on a reused window it is not dispatched at all and its readers see the bits it last returned,
which are the bits it would have returned from its cache if the pass returns what it stores (the Arc's identity gate
is what proves that, per file).

A pass qualifies only if all of this holds, asserted, so nothing with a side effect before the test is skipped:
  - its hook() body begins with exactly the coordinate line and the cache test above (nothing runs before them, so a
    fused twin called after the test is skipped with it, as the cache already skipped it);
  - it has a //!SAVE (a sticky texture needs a name to be offered under) and no //!WHEN or //!STICKY of its own.

NEEDS the 2026-10-22 patch. A libplacebo without it rejects the unknown //!STICKY line, the shader fails to load and
libplacebo silently mixes with its own mixer, so a file made with this switch is a variant until every host it ships to
(Cadence's bundled build, the Metal engine's graphs) carries the patch. Apply it after PRUNE: the prune treats every
//!WHEN pass as a liveness root.
"""
import re
import sys

HEAD = re.compile(r"(?ms)^vec4 hook\(\) \{\n    ivec2 coord = ivec2\((\w+)_pos \* \1_size\);\n    if \(!pair_changed\)\n"
                  r"        return imageLoad\(")


def add(text):
    parts = re.split(r"(?m)^(?=//!HOOK )", text)
    n = 0
    for i, p in enumerate(parts):
        if not p.startswith("//!HOOK ") or not HEAD.search(p):
            continue
        lines = p.split("\n")
        header = "\n".join(lines[:next(k for k, l in enumerate(lines) if not l.startswith("//!"))])
        assert "//!SAVE " in header, "a pair-cached pass with no //!SAVE: %r" % header[:120]
        assert "//!WHEN" not in header and "//!STICKY" not in header, "already gated: %r" % header[:120]
        assert p.count("vec4 hook() {") == 1, "two hook() bodies in one pass"
        first = p.index("\n") + 1
        parts[i] = p[:first] + "//!WHEN pair_changed\n//!STICKY\n" + p[first:]
        n += 1
    return "".join(parts), n


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    out, n = add(open(src, encoding="utf-8").read())
    assert n > 0, "no pair-cached pass found"
    open(dst, "w", encoding="utf-8", newline="\n").write(out)
    print("%s: %d pair-cached passes marked //!WHEN pair_changed + //!STICKY" % (dst, n))
