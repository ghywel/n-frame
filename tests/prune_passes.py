#!/usr/bin/env python3
"""prune_passes.py <in.glsl> [out.glsl] [--twins] [--keep-textures] [--check]: remove the passes whose work cannot reach
the output (REPAIRS.md lead L7, swarm 2026-10-21, the cost lane), and print the census.

What it does. A libplacebo user shader is a sequence of //!HOOK passes. A pass's results leave it two ways: its //!SAVE
texture, which only a LATER pass of the same frame can //!BIND (libplacebo's hook_reset empties the saved-name table
every frame), and the //!TEXTURE ... //!STORAGE images it writes with imageStore, which persist and which any other
pass may imageLoad, earlier or later. Liveness starts from the roots -- every pass that produces the hook's output (no
//!SAVE, or //!SAVE of the hooked stage) and every //!WHEN-gated pass (the human-reading tail, and whatever a field
read view needs) -- and runs backwards through both channels to a fixpoint. A pass that is not live is deleted from the
text as a whole element; nothing inside a kept pass changes. A //!TEXTURE declaration that only deleted passes bound goes
with them (memory, not time; --keep-textures leaves them).

The traps it exists to avoid. (1) tests/probes/repairs/dead_passes.py follows //!SAVE and //!BIND only. Its verdicts are
wrong both ways: it called ALIAS_E_AB and ALIAS_Q_AB dead when their imageStores into ALIAS_*_ST feed the live 1/8
refines (cutting them would change the picture), and it called the whole half-res B->A chain live because the fused
first median binds FLOW_H_BA to write FLOW_H_BA_M1_ST, which only the dead second B->A median reads. Here storage writes
count as outputs and storage reads as inputs. (2) An unknown bind is never left behind: libplacebo does not fail on one,
it SILENTLY skips the pass (custom_mpv.c, "Skipping hook due to no texture named"), so after pruning every //!BIND and
every imageLoad/imageStore in a kept pass must still have a producer, or this refuses and names the orphan. (3) The text
must still PARSE as libplacebo parses it (custom_mpv.c): the file is cut at every "//!" marker; a //!TEXTURE block's body
is everything to the next marker and is hex-decoded, so for a //!STORAGE texture it must be blank (a //!PARAM's body is its default value). The first build of
this tool left a removed pass's banner comment behind a kept //!TEXTURE block and libplacebo refused the whole file
("must be a valid hexadecimal sequence"), then fell back to its own mixer without a word (the gate of 2026-10-21 read
42 of 42 not identical). So an element owns the comment preamble above its directives and takes it along when removed,
a comment that would land directly after a kept //!TEXTURE block is hoisted above that block, and parse_check() asserts
the parse before anything is written.

Fused twins. A pass whose body defines `void hook_ba()` carries its B->A twin in one dispatch (NFRAME-LIMITS.md "pass
fusion"). By default the twin is part of its pass: its binds keep their producers live, and the whole pass stays. With
--twins the twin is scored on its own (its imageStores read by no live pass make it dead), its hook_ba() and the binds
only it used are cut from the kept pass, and the chain that fed only the twin is then dead too. That edits the inside of
a kept pass, so it is a separate mode and is reported as such.

The invariant: at every read_view the output is byte-identical, because only work no live pass can observe is removed.
"""
import pathlib
import re
import sys

KINDS = ("HOOK", "TEXTURE", "PARAM", "BUFFER")
START_RE = re.compile(r"(?m)^(?=//!(?:HOOK|TEXTURE|PARAM|BUFFER)\b)")
SUFFIX_RE = re.compile(r"\b([A-Z][A-Z0-9_]*)_(?:tex|texOff|pos|pt|size|map|off|raw|mul)\b")  # bind names are upper-case here
# Textures libplacebo provides without any pass saving them: the hooked frame, the window (the patch), mpv's stages.
INPUTS = {"HOOKED", "NEXT", "PREV", "MAIN", "MAINPRESUB", "LUMA", "CHROMA", "RGB", "NATIVE", "OUTPUT", "LINEAR",
          "SIGMOID", "PREKERNEL", "POSTKERNEL", "SCALED"} | {f"FRAME{i}" for i in range(8)}


def is_directive(line):
    return line.startswith("//!")


def is_blank_or_comment(line):
    s = line.strip()
    return s == "" or (s.startswith("//") and not s.startswith("//!"))


# ----------------------------------------------------------------------------------------------------------------------
# The element model. An element is a run of //! directive lines beginning with //!HOOK, //!TEXTURE, //!PARAM or
# //!BUFFER, plus (a) the PREAMBLE: the run of blank or comment-only lines immediately above it, which in this family
# is its banner, and (b) the BODY: everything after its directives up to the next element's preamble. The file's own
# header before the first element is `pre`. The last element also owns its trailing lines. Removing an element removes
# preamble, directives and body: nothing of it is left behind, and nothing of its neighbours moves.
# ----------------------------------------------------------------------------------------------------------------------
def elements(text):
    lines = text.split("\n")
    starts = [i for i, ln in enumerate(lines) if any(ln.startswith("//!" + k) for k in KINDS)]
    if not starts:
        return text, []
    # the preamble of element k begins after the last line above starts[k] that is neither blank nor comment-only
    pre_start = []
    prev_end = 0
    els = []
    for k, s in enumerate(starts):
        p = s
        while p > prev_end and is_blank_or_comment(lines[p - 1]):
            p -= 1
        pre_start.append(p)
        prev_end = s  # the next element's preamble cannot reach above this element's directives
    pre = "\n".join(lines[:pre_start[0]]) + ("\n" if pre_start[0] > 0 else "")
    for k, s in enumerate(starts):
        d = s
        while d < len(lines) and is_directive(lines[d]):
            d += 1
        body_end = pre_start[k + 1] if k + 1 < len(starts) else len(lines)
        preamble = "\n".join(lines[pre_start[k]:s]) + ("\n" if s > pre_start[k] else "")
        directives = "\n".join(lines[s:d]) + "\n"
        body = "\n".join(lines[d:body_end]) + ("\n" if body_end > d and body_end < len(lines) else "")
        if k + 1 == len(starts):
            body = "\n".join(lines[d:])
        kind = lines[s][3:].split()[0]
        el = dict(kind=kind, preamble=preamble, directives=directives, body=body)
        if kind == "HOOK":
            el.update(parse_hook(directives, body))
        else:
            el["name"] = lines[s].split()[1]
            el["storage"] = bool(re.search(r"(?m)^//!STORAGE\b", directives))
        els.append(el)
    return pre, els


def element_text(e):
    return e["preamble"] + e["directives"] + e["body"]


def parse_hook(directives, body):
    hook = re.search(r"(?m)^//!HOOK\s+(\S+)", directives).group(1)
    save = re.search(r"(?m)^//!SAVE\s+(\S+)", directives)
    desc = re.search(r"(?m)^//!DESC\s+(.*)$", directives)
    width = re.search(r"(?m)^//!WIDTH\s+(.*)$", directives)
    height = re.search(r"(?m)^//!HEIGHT\s+(.*)$", directives)
    return dict(hook=hook, save=save.group(1) if save else None,
                binds=re.findall(r"(?m)^//!BIND\s+(\S+)", directives), when=bool(re.search(r"(?m)^//!WHEN\b", directives)),
                desc=desc.group(1).strip() if desc else "", width=width.group(1).strip() if width else "HOOKED.w",
                height=height.group(1).strip() if height else "HOOKED.h",
                st_w=set(re.findall(r"imageStore\(\s*(\w+)", body)), st_r=set(re.findall(r"imageLoad\(\s*(\w+)", body)),
                twin=twin_split(body))


def strip_comments(s):
    """GLSL text with // comments blanked (same length), so brace matching cannot be fooled by a brace in a comment."""
    return re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), s)


def names_in(s):
    return set(SUFFIX_RE.findall(s)) | set(re.findall(r"image(?:Load|Store)\(\s*(\w+)", s)) \
        | set(re.findall(r"\b([A-Z][A-Z0-9_]*)\b", s))


def twin_split(body):
    """For a fused pass (a `void hook_ba()` in the body): the twin's span in the body, the names only it references, and
    its imageStore targets. None for an ordinary pass."""
    m = re.search(r"(?m)^void hook_ba\(\)\s*\{", body)
    if not m:
        return None
    code = strip_comments(body)
    depth, j = 0, m.start()
    while j < len(code):
        if code[j] == "{":
            depth += 1
        elif code[j] == "}":
            depth -= 1
            if depth == 0:
                j += 1
                break
        j += 1
    assert depth == 0 and body[j - 1] == "}", "hook_ba(): unbalanced braces"
    twin_text = body[m.start():j]
    rest = body[:m.start()] + body[j:]
    rest = re.sub(r"(?m)^\s*hook_ba\(\);\s*\n", "", rest)
    return dict(span=(m.start(), j), only=names_in(twin_text) - names_in(rest),
                st_w=set(re.findall(r"imageStore\(\s*(\w+)", twin_text)),
                ab_st_w=set(re.findall(r"imageStore\(\s*(\w+)", rest)))


def liveness(passes, twins):
    """live[i] for every pass; twin_live[i] (None, True or False) for fused passes. Roots: output passes and //!WHEN
    passes. A SAVE is read by a LATER live pass's bind; a storage write by ANY other live pass's imageLoad. In twins
    mode a dead twin's exclusive binds and stores do not count."""
    n = len(passes)

    def reads(j, name, store):
        p = passes[j]
        if not live[j] or name not in (p["st_r"] if store else p["binds"]):
            return False
        if twins and p["twin"] and twin_live[j] is False and name in p["twin"]["only"]:
            return False
        return True

    def writes(i):
        p = passes[i]
        if twins and p["twin"] and twin_live[i] is False:
            return p["twin"]["ab_st_w"]
        return set(p["st_w"])

    twin_live = [True if p["twin"] else None for p in passes]
    while True:
        live = [p["save"] is None or p["save"] == p["hook"] or p["when"] for p in passes]
        changed = True
        while changed:
            changed = False
            for i, p in enumerate(passes):
                if live[i]:
                    continue
                ok = p["save"] is not None and any(reads(j, p["save"], False) for j in range(i + 1, n))
                ok = ok or any(reads(j, w, True) for w in writes(i) for j in range(n) if j != i)
                if ok:
                    live[i] = changed = True
        if not twins:
            return live, twin_live
        killed = False
        for i, p in enumerate(passes):
            if p["twin"] and twin_live[i] and live[i]:
                if not any(reads(j, w, True) for w in p["twin"]["st_w"] for j in range(n) if j != i):
                    twin_live[i] = False
                    killed = True
        if not killed:
            return live, twin_live


def rpn(expr, w, h):
    st = []
    for tok in expr.split():
        if tok in "+-*/":
            b, a = st.pop(), st.pop()
            st.append({"+": a + b, "-": a - b, "*": a * b, "/": a / b}[tok])
        elif tok.endswith(".w"):
            st.append(float(w))
        elif tok.endswith(".h"):
            st.append(float(h))
        else:
            st.append(float(tok))
    return st[-1]


def level(p, w=1280, h=720):
    try:
        pw, ph = int(round(rpn(p["width"], w, h))), int(round(rpn(p["height"], w, h)))
    except Exception:
        return "?"
    if (pw, ph) == (w, h):
        return "full"
    for d in (2, 4, 8, 16, 32, 64):
        if (pw, ph) == (w // d, h // d):
            return f"1/{d}"
    return f"{pw}x{ph}"


def cut_twin(e):
    """The fused pass with its dead twin removed: hook_ba() and its call gone, the binds only it used gone. Returns
    (directives, body, dropped binds)."""
    a, b = e["twin"]["span"]
    body = e["body"][:a] + e["body"][b:]
    body = re.sub(r"(?m)^\s*hook_ba\(\);\s*\n", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    assert "hook_ba" not in strip_comments(body), "hook_ba still referenced after the cut"
    used = names_in(body)
    gone = [x for x in e["binds"] if x in e["twin"]["only"] and x not in used]
    directives = "".join(ln + "\n" for ln in e["directives"].rstrip("\n").split("\n")
                         if not (ln.startswith("//!BIND ") and ln.split()[1] in gone))
    return directives, body, gone


def directive_counts(text):
    c = {}
    for m in re.finditer(r"(?m)^//!([A-Z]+)\b", text):
        c[m.group(1)] = c.get(m.group(1), 0) + 1
    return c


# ----------------------------------------------------------------------------------------------------------------------
# The two checks. check(): producers and macro names (the silent-skip trap). parse_check(): the text parses as
# custom_mpv.c parses it (the hexadecimal trap).
# ----------------------------------------------------------------------------------------------------------------------
def check(pre, els, stage_inputs=INPUTS):
    """Every bind and every imageLoad/imageStore in a kept pass has a producer: an input, the hook stage, a declared
    //!TEXTURE, or a //!SAVE of an earlier pass. Every NAME_tex/_pos/_pt/_size in a body is a bound name. Returns the
    list of orphans (empty when sound)."""
    orphans = []
    textures = {e["name"] for e in els if e["kind"] == "TEXTURE"}
    saved = set()
    for k, e in enumerate(els):
        if e["kind"] != "HOOK":
            continue
        ok_names = stage_inputs | {e["hook"]} | textures | saved
        for b in e["binds"]:
            if b not in ok_names:
                orphans.append(f"pass {k} ({e['desc'][:60]}): //!BIND {b} has no producer")
        for s in e["st_w"] | e["st_r"]:
            if s not in e["binds"]:
                orphans.append(f"pass {k} ({e['desc'][:60]}): image op on {s}, which the pass does not bind")
        bound = set(e["binds"]) | ({"HOOKED"} if e["hook"] in e["binds"] or "HOOKED" in e["binds"] else set())
        for name in set(SUFFIX_RE.findall(e["body"])):
            if name not in bound and name != "HOOKED":
                orphans.append(f"pass {k} ({e['desc'][:60]}): {name}_* used but {name} is not bound")
        if e["save"]:
            saved.add(e["save"])
    return orphans


def parse_check(text):
    """The text as custom_mpv.c reads it: it cuts at every "//!" marker (split_magic), anywhere in a line. A //!TEXTURE
    block's body (to the next marker) is stripped and hex-decoded, so a //!STORAGE texture's body must be blank. Every
    block of directives must begin with HOOK, TEXTURE, PARAM or BUFFER (a stray //!BIND would start a block libplacebo
    cannot type). A "//!" that is not at a line start would cut a pass body in two. Returns a list of faults."""
    faults = []
    for m in re.finditer(r"//!", text):
        if m.start() > 0 and text[m.start() - 1] != "\n":
            ln = text.count("\n", 0, m.start()) + 1
            faults.append(f"line {ln}: '//!' not at a line start would cut the block here")
    lines = text.split("\n")
    i = 0
    seen_first = False
    while i < len(lines):
        if is_directive(lines[i]):
            kind = lines[i][3:].split()[0] if lines[i][3:].split() else ""
            if kind not in KINDS:
                faults.append(f"line {i + 1}: block begins with //!{kind}, not HOOK/TEXTURE/PARAM/BUFFER")
            seen_first = True
            j = i
            while j < len(lines) and is_directive(lines[j]):
                j += 1
            k = j
            while k < len(lines) and not is_directive(lines[k]):
                k += 1
            body = "\n".join(lines[j:k])
            if kind == "TEXTURE":
                storage = any(ln.startswith("//!STORAGE") for ln in lines[i:j])
                if storage and body.strip():
                    faults.append(f"line {j + 1}: //!STORAGE texture {lines[i].split()[1]} has a body "
                                  f"('{body.strip().splitlines()[0][:50]}'): not a hexadecimal sequence")
                elif not storage and not re.fullmatch(r"[0-9a-fA-F\s]*", body):
                    faults.append(f"line {j + 1}: texture {lines[i].split()[1]} body is not hexadecimal")
            if kind == "PARAM" and not re.fullmatch(r"\s*[-+0-9.eE]*\s*", body):   # a PARAM's body is its default value
                faults.append(f"line {j + 1}: //!PARAM {lines[i].split()[1]} has a body that is not a number")
            i = k
        else:
            i += 1
    return faults


# ----------------------------------------------------------------------------------------------------------------------
def prune(text, twins=False, keep_textures=False, report=None):
    """Return (pruned text, census dict). Raises SystemExit on an orphan or a parse fault."""
    faults0 = parse_check(text)
    if faults0:
        raise SystemExit("prune_passes.py REFUSES: the INPUT does not parse: " + "; ".join(faults0))
    pre, els = elements(text)
    assert pre + "".join(element_text(e) for e in els) == text, "the element model does not reproduce the text"
    passes = [e for e in els if e["kind"] == "HOOK"]
    live, twin_live = liveness(passes, twins)
    index = {id(p): i for i, p in enumerate(passes)}
    removed, removed_els, cut = [], [], []
    for i, p in enumerate(passes):
        if not live[i]:
            why = []
            if p["save"]:
                why.append(f"its save {p['save']} is bound by no later live pass")
            if p["st_w"]:
                why.append(f"its stores ({', '.join(sorted(p['st_w']))}) are loaded by no live pass")
            removed.append((i, level(p), p["desc"], "; ".join(why) or "no outputs"))
    halves = [(i, p["desc"]) for i, p in enumerate(passes) if p["twin"] and twin_live[i] is False]
    out, bound_after, dropped_binds = [], set(), 0
    for e in els:
        if e["kind"] == "HOOK":
            i = index[id(e)]
            if not live[i]:
                removed_els.append(e)
                continue
            if twins and e["twin"] and twin_live[i] is False:
                directives, body, gone = cut_twin(e)
                e = dict(kind="HOOK", preamble=e["preamble"], directives=directives, body=body, **parse_hook(directives, body))
                cut.append((i, gone))
                dropped_binds += len(gone)
            bound_after |= set(e["binds"])
        out.append(e)
    dropped_tex = []
    if not keep_textures:
        kept = []
        for e in out:
            if e["kind"] == "TEXTURE" and e["name"] not in bound_after:
                dropped_tex.append(e["name"])
                removed_els.append(e)
                continue
            kept.append(e)
        out = kept
    # a comment preamble that now follows a kept //!TEXTURE block directly would be read as the texture's body: hoist
    # it above the run of texture blocks it follows (it is then GLSL comment inside the previous pass's body, or header)
    hoisted = 0
    for k in range(1, len(out)):
        if out[k - 1]["kind"] == "TEXTURE" and out[k]["preamble"].strip():
            j = k - 1
            while j > 0 and out[j - 1]["kind"] == "TEXTURE":
                j -= 1
            comment = out[k]["preamble"]
            out[k]["preamble"] = "\n"            # one blank line between //!STORAGE and the next directive, as the files have
            out[j]["preamble"] = (out[j]["preamble"].rstrip("\n") + "\n" + comment) if out[j]["preamble"].strip() else comment
            hoisted += 1
    new_text = pre + "".join(element_text(e) for e in out)
    # the accounting: the output's directive lines are the input's minus the removed elements' minus the cut binds
    expect = directive_counts(text)
    for e in removed_els:
        for kind, n in directive_counts(e["directives"]).items():
            expect[kind] -= n
    expect["BIND"] = expect.get("BIND", 0) - dropped_binds
    got = directive_counts(new_text)
    expect = {k: v for k, v in expect.items() if v}
    accounting_ok = got == expect
    faults = parse_check(new_text)
    _, els2 = elements(new_text)
    orphans = check(pre, els2)
    kept_passes = [e for e in els2 if e["kind"] == "HOOK"]
    census = dict(before=len(passes), after=len(kept_passes),
                  before_rv0=sum(1 for p in passes if not p["when"]), after_rv0=sum(1 for p in kept_passes if not p["when"]),
                  removed=removed, halves_left=[] if twins else halves, halves_cut=cut if twins else [],
                  textures_dropped=dropped_tex, hoisted=hoisted, orphans=orphans, parse_faults=faults,
                  accounting=(got, expect, accounting_ok),
                  by_level_removed=count_levels([passes[i] for i, _, _, _ in removed]),
                  by_level_after=count_levels(kept_passes))
    if report is not None:
        print_census(census, file=report)
    problems = orphans + faults + ([] if accounting_ok else [f"directive accounting: got {got}, expected {expect}"])
    if problems:
        raise SystemExit("prune_passes.py REFUSES: " + "; ".join(problems))
    return new_text, census


def count_levels(ps):
    c = {}
    for p in ps:
        c[level(p)] = c.get(level(p), 0) + 1
    return dict(sorted(c.items()))


def print_census(c, file=sys.stdout):
    print(f"PRUNE: {c['before']} passes -> {c['after']} ({c['before_rv0']} -> {c['after_rv0']} at read_view 0); "
          f"removed {len(c['removed'])} by level {c['by_level_removed']}; kept by level {c['by_level_after']}", file=file)
    for i, lv, desc, why in c["removed"]:
        print(f"  - #{i:3d} {lv:6s} {desc[:70]}: {why}", file=file)
    if c["halves_left"]:
        print(f"  fused twins left in place (dead work, not removed): {len(c['halves_left'])}", file=file)
        for i, desc in c["halves_left"]:
            print(f"      #{i:3d} {desc[:90]}", file=file)
    if c["halves_cut"]:
        print(f"  fused twins cut from kept passes: {len(c['halves_cut'])}", file=file)
        for i, gone in c["halves_cut"]:
            print(f"      #{i:3d} binds dropped: {', '.join(gone) or 'none'}", file=file)
    if c["textures_dropped"]:
        print(f"  storage textures dropped (nothing binds them now): {', '.join(c['textures_dropped'])}", file=file)
    if c["hoisted"]:
        print(f"  comment preambles hoisted above a kept //!TEXTURE block: {c['hoisted']}", file=file)
    got, expect, ok = c["accounting"]
    print(f"  directive accounting {'OK' if ok else 'FAILED'}: {got}", file=file)
    print(f"  parse check: {'OK' if not c['parse_faults'] else 'FAULTS: ' + '; '.join(c['parse_faults'])}", file=file)
    if c["orphans"]:
        print("  ORPHANS: " + "; ".join(c["orphans"]), file=file)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    src = pathlib.Path(args[0])
    text = src.read_text(encoding="utf-8")
    if "--check" in sys.argv:   # the control: the file as it stands must pass both checks untouched
        faults = parse_check(text)
        pre, els = elements(text)
        orphans = check(pre, els)
        n = len([e for e in els if e["kind"] == "HOOK"])
        print(f"CHECK {src.name}: {n} passes, {len(faults)} parse fault(s), {len(orphans)} orphan(s)"
              + "".join("; " + f for f in faults + orphans))
        sys.exit(1 if faults or orphans else 0)
    new, census = prune(text, twins="--twins" in sys.argv, keep_textures="--keep-textures" in sys.argv, report=sys.stdout)
    if len(args) > 1:
        pathlib.Path(args[1]).write_text(new, encoding="utf-8", newline="\n")
        print(f"wrote {args[1]}")
