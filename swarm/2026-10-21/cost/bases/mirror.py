"""mirror.py <base.glsl>...: the textual mirror A->B -> B->A, derived from the bases' own names, applied to every pass
whose twin is dead (and to every fused pass's hook() half against its hook_ba). Prints, per twin, IDENTICAL or every
differing line (the mirrored A->B text against the actual B->A text), after folding away the three documented,
value-preserving differences (see normalise)."""
import difflib
import pathlib
import re
import sys

sys.path.insert(0, "REPO/tests")
import prune_passes as PP  # noqa: E402

# The mirror, derived from the bases' text: the pair tag, the frame letter in luma names, the window inputs, the
# per-frame sample coordinates and the words of the descriptions.
SWAPS = [("_AB", "_BA"), ("LUMA_A_", "LUMA_B_"), ("HOOKED", "NEXT"), ("uv_a", "uv_b"), ("A->B", "B->A"),
         ("frame A", "frame B"), ("Frame A", "Frame B"), (" AB ", " BA "), ("(AB)", "(BA)"), (" AB:", " BA:"), ("_ab", "_ba")]
PAT = re.compile("|".join(re.escape(x) for pair in SWAPS for x in pair))
MAP = {}
for a, b in SWAPS:
    MAP[a] = b
    MAP[b] = a


def mirror(s):
    return PAT.sub(lambda m: MAP[m.group(0)], s)


def mirror_code(s):
    """The mirror, with //!WIDTH and //!HEIGHT left alone: the pass size is the hooked frame's in both directions."""
    keep = {}

    def hold(m):
        keep[len(keep)] = m.group(0)
        return f"@@{len(keep) - 1}@@"
    s2 = re.sub(r"(?m)^//!(WIDTH|HEIGHT) .*$", hold, s)
    s2 = mirror(s2)
    return re.sub(r"@@(\d+)@@", lambda m: keep[int(m.group(1))], s2)


def code(s):
    """Code only: comments stripped, blank lines dropped, whitespace normalised, //!BIND lines sorted (a set)."""
    out, binds = [], []
    for ln in s.split("\n"):
        if ln.startswith("//!BIND"):
            binds.append(ln.strip())
            continue
        ln = re.sub(r"//(?!!).*$", "", ln).rstrip()
        if ln.strip():
            out.append(re.sub(r"\s+", " ", ln.strip()))
    return "\n".join(sorted(binds) + out)


def normalise(s):
    """The three documented, value-preserving differences between a pass and its twin, folded away so that what is
    left is a real asymmetry: (1) helper functions renamed per direction -> canonical F0, F1.. by definition order;
    (2) geometry identifiers (_pt/_pos/_size) taken from the other direction's equal-sized texture -> canonical G;
    (3) the fusion transform: a twin reads its inputs with imageLoad(X_ST, floor(size*p)) instead of X_tex(p),
    writes with imageStore+return instead of return, and is void hook_ba() instead of vec4 hook()."""
    s = re.sub(r"void hook_ba\(\)", "vec4 hook()", s)
    s = re.sub(r"\{ imageStore\(\w+_ST\d?, ivec2\(gl_FragCoord\.xy\), (.*)\); return; \}", r"return \1;", s)
    s = re.sub(r"imageLoad\((\w+?)_ST\d?, ivec2\(floor\(\(\w+_size\) \* \((.*?)\)\)\)\)", r"\1_tex(\2)", s)
    s = re.sub(r"(?m)^//!BIND (\w+?)_ST\d?$", r"//!BIND \1", s)
    for b in re.findall(r"(?m)^//!BIND (\w+)$", s):
        uses = re.findall(rf"\b{b}_(\w+)", s) + re.findall(rf"[(,]\s*{b}\b", s)
        if uses and all(u in ("pt", "pos", "size") for u in uses):
            s = re.sub(rf"(?m)^//!BIND {b}\n", "", s)
    s = re.sub(r"\bLUMA_(?:A|B)_([SEQHF])_(pt|pos|size)\b", r"LUMA_G_\1_\2", s)
    s = re.sub(r"\bFLOW_([SEQHF])_(?:AB|BA)(_PROP|_RAW)?(?:_M1)?_(pt|pos|size)\b", r"FLOW_\1_G\2_\3", s)
    s = re.sub(r"\bFLOW_([SEQHF])_(AB|BA)_M1(?=_)", r"FLOW_\1_\2", s)       # the fused first median's storage copy
    s = re.sub(r"\b(\w+)_ba\(", r"\1(", s)                               # the twin's helpers carry a _ba suffix
    # a bind kept only for its geometry identifiers (the fusion reads the twin's storage with the saved texture's size)
    for b in re.findall(r"(?m)^//!BIND (\w+)$", s):
        uses = re.findall(rf"\b{b}_(\w+)", s) + re.findall(rf"[(,]\s*{b}\b", s)
        if uses and all(u in ("pt", "pos", "size") for u in uses):
            s = re.sub(rf"(?m)^//!BIND {b}\n", "", s)
    names = re.findall(r"(?m)^(?:float|vec2|vec3|vec4|int|bool|void) (\w+)\(", s)
    seen = []
    for n in names:
        if n not in seen and n != "hook":
            seen.append(n)
    for i, n in enumerate(seen):
        s = re.sub(rf"\b{n}\b", f"F{i}", s)
    return s


def top_level_functions(body):
    """(name, start, end) of every top-level function definition, braces matched on comment-blanked text."""
    code_ = PP.strip_comments(body); out = []
    for m in re.finditer(r"(?m)^(?:float|vec2|vec3|vec4|int|bool|void) (\w+)\([^)]*\)\s*\{", code_):
        depth, j = 0, m.end() - 1
        while j < len(code_):
            if code_[j] == "{": depth += 1
            elif code_[j] == "}":
                depth -= 1
                if depth == 0: j += 1; break
            j += 1
        out.append((m.group(1), m.start(), j))
    return out

def twin_helpers(body):
    return [(n, a, b) for n, a, b in top_level_functions(body) if n.endswith("_ba") and n != "hook_ba"]

def strip_hook_ba(body, twin):
    cut = sorted([twin["span"]] + [(a, b) for _, a, b in twin_helpers(body)], reverse=True)
    for a, b in cut:
        body = body[:a] + body[b:]
    return re.sub(r"(?m)^\s*hook_ba\(\);\s*\n", "", body)

def twin_text(body, twin):
    fns = top_level_functions(body); names = {n for n, _, _ in fns}
    cut = sorted([(a, b) for n, a, b in fns if n == "hook" or (n + "_ba") in names], reverse=True)
    for a, b in cut:
        body = body[:a] + body[b:]
    return body


def hook_body(body):
    m = re.search(r"(?m)^vec4 hook\(\)\s*\{", body)
    return body[m.start():] if m else body


def report(name, ab_text, ba_text):
    m = normalise(code(mirror_code(ab_text)))
    b = normalise(code(ba_text))
    if m == b:
        print(f"  {name}: IDENTICAL under the mirror")
        return 0
    d = [l for l in difflib.unified_diff(m.splitlines(), b.splitlines(), "mirror(A->B)", "B->A", n=0, lineterm="")
         if not l.startswith(("---", "+++", "@@"))]
    print(f"  {name}: {len(d)} differing lines")
    for l in d:
        print("     ", l[:170])
    return len(d)


for f in sys.argv[1:]:
    text = pathlib.Path(f).read_text(encoding="utf-8")
    pre, els = PP.elements(text)
    passes = [e for e in els if e["kind"] == "HOOK"]
    live, twin_live = PP.liveness(passes, twins=True)
    print(f"=== {pathlib.Path(f).name}")
    for i, p in enumerate(passes):
        if live[i] or not p["save"] or not p["save"].endswith("_BA"):
            continue
        partner = [j for j, q in enumerate(passes)
                   if q["save"] == p["save"][:-3] + "_AB" and mirror(q["desc"]) == p["desc"]]
        if not partner:
            print(f"  #{i} {p['desc'][:60]}: NO A->B PARTNER found by save+desc")
            continue
        q = passes[partner[0]]
        # the A->B partner may itself be fused: compare its hook() half only
        ab = q["directives"] + (strip_hook_ba(q["body"], q["twin"]) if q["twin"] else q["body"])
        report(f"#{partner[0]}->#{i} {p['desc'][:55]}", ab, p["directives"] + p["body"])
    for i, p in enumerate(passes):
        if p["twin"]:
            a, b = p["twin"]["span"]
            status = "dead twin" if twin_live[i] is False else "live twin"
            ab_side = strip_hook_ba(p["body"], p["twin"])
            report(f"#{i} FUSED ({status}) {p['desc'][:50]}: hook() vs hook_ba()", ab_side, twin_text(p["body"], p["twin"]))
