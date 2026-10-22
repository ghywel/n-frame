#!/usr/bin/env python3
"""ledger_check.py: the chat ledger carries each entry once, and none that is already archived.

    python3 tests/ledger_check.py              after merging, and before pushing
    python3 tests/ledger_check.py --branch     after a fetch, before merging origin/main into a branch

Ported 2026-10-22 from the placego project's tests/probes/ledger_check.py, with the chat ledger (CHAT-LEDGER.md),
which Claude and GPT both append to. Why: the ledger rotates like a log (`git mv CHAT-LEDGER.md CHAT-LEDGER.N.md` and a
fresh file) and merges by union (.gitattributes). A branch begun before a rotation that appended an entry then merges
without any conflict and re-imports the archived text into the live file. This fails if an entry heading of the live
file appears in an archive, or twice in the live file. --branch says, before a merge, whether a rotation happened since
the branch began (fewer archives here than on origin/main): then re-append your new entries onto main's live file
instead of merging it. The controls below run first: a live file that repeats an archived entry must fail, and one
with only new entries must pass.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "CHAT-LEDGER"
HEADING = re.compile(r"^## [A-Z]+\d+(\.\d+)* ")      # entry headings: "## L001 ...", "## G012 ...", "## CL003 ..."


def entries(text):
    return [l.strip() for l in text.split("\n") if HEADING.match(l)]


def problems(live, archives):
    archived = {h for a in archives for h in entries(a)}
    seen, out = set(), []
    for h in entries(live):
        if h in archived:
            out.append(f"archived entry in the live file: {h[:90]}")
        if h in seen:
            out.append(f"entry repeated in the live file: {h[:90]}")
        seen.add(h)
    return out


def control():
    assert problems("## L001 x\n", ["## L001 x\n"]) and not problems("## G013 y\n", ["## L001 x\n"])
    assert problems("## L002 a\n## L002 a\n", [])                       # a repeat in the live file
    assert not problems("## Rotation\n", ["## Rotation\n"])              # the preamble's headings are not entries
    assert problems("## G5.3 x\n", ["## G5.3 x\n"])                      # dotted sub-entries count too


def archives_in(ref):
    out = subprocess.run(["git", "ls-tree", "--name-only", ref], cwd=ROOT, capture_output=True, text=True, check=True)
    return sum(1 for n in out.stdout.split() if re.fullmatch(re.escape(BASE) + r"\.\d+\.md", n))


def main():
    control()
    if "--branch" in sys.argv[1:]:
        mine, theirs = archives_in("HEAD"), archives_in("origin/main")
        if mine < theirs:
            print(f"STOP: this branch has {mine} {BASE} archive(s) and origin/main has {theirs}: a rotation happened "
                  f"since the branch began. Do not merge {BASE}.md; re-append your new entries onto main's live file.")
            sys.exit(1)
        print(f"BRANCH CHECK PASSES ({mine} archive(s) here, {theirs} on origin/main)")
        return
    live_path = ROOT / f"{BASE}.md"
    if not live_path.exists():
        print(f"no {BASE}.md")
        return
    archives = [p.read_text(encoding="utf-8") for p in sorted(ROOT.glob(f"{BASE}.*.md"))]
    found = problems(live_path.read_text(encoding="utf-8"), archives)
    for p in found[:10]:
        print("FAIL ", p)
    n = len(entries(live_path.read_text(encoding="utf-8")))
    print(f"{'LEDGER CHECK PASSES' if not found else f'{len(found)} PROBLEM(S): merge the archived copy out'}"
          f" ({n} live entries, {len(archives)} archive(s))")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
