# -*- coding: utf-8 -*-
"""Check that the citations in REPORT.md and refs.json agree.

Five checks. Each one has a way to fail, and `--selftest` makes each fail on purpose
before the real run, because a check that has never reported red is not evidence.

  1. Every [n] in the text resolves to an entry, and every entry is cited at least once.
     Entries 1 to 5 are exempt from the second half: they are required by section 4 of the
     data use agreement covering the pretrained weights, and the agreement asks that they
     be cited, not that the text find an argument for each one. The exemption is a list in
     this file, and the run prints which entries actually used it.
  2. The reference list and refs.bib are what refs.json generates, byte for byte. This is
     not a comparison between two maintained copies; it regenerates and diffs, so the two
     cannot be edited into agreeing on something wrong.
  3. An entry conditional on an experiment that has not been run does not appear.
  4. Every entry records where its fields were verified.
  5. A caveat on an entry appears in refs.bib. The caveats are the places where a field
     that looks obvious is wrong, so losing one silently is worse than losing an entry.

Usage:
    python tools/gate_citations.py --selftest    prove the checks can fail, then run
    python tools/gate_citations.py               run
"""
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "REPORT.md"
REFS = ROOT / "refs.json"
BIB = ROOT / "refs.bib"
MAKE = ROOT / "tools" / "make_refs.py"

# Required by the data use agreement rather than by the argument. See check 1.
EXEMPT_FROM_BEING_CITED = {1, 2, 3, 4, 5}


def load(path=None):
    return json.load(io.open(path or REFS, encoding="utf-8"))


def cited_numbers(text):
    body = text.split("## References")[0]
    out = set()
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", body):
        out |= {int(x) for x in re.split(r"\s*,\s*", group)}
    return out


def listed_numbers(text):
    block = text.split("## References", 1)[1]
    return {int(m) for m in re.findall(r"^(\d+)\.\s", block, re.M)}


def check1_markers():
    text = io.open(REPORT, encoding="utf-8").read()
    cited, listed = cited_numbers(text), listed_numbers(text)
    dangling = sorted(cited - listed)
    uncited = sorted(listed - cited - EXEMPT_FROM_BEING_CITED)
    used_exemption = sorted((listed - cited) & EXEMPT_FROM_BEING_CITED)
    ok = not dangling and not uncited
    return ok, ("cited %d, listed %d; markers with no entry %s; entries never cited %s; "
                "exemption used by %s"
                % (len(cited), len(listed), dangling or "none", uncited or "none",
                   used_exemption or "none"))


def check2_generated():
    r = subprocess.run([sys.executable, str(MAKE), "--check", str(REPORT)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [l.strip() for l in (r.stdout or "").split("\n") if l.strip()]
    return r.returncode == 0, (tail[-1] if tail else "make_refs.py produced no output")


def check3_conditional():
    refs = load()
    listed = listed_numbers(io.open(REPORT, encoding="utf-8").read())
    leaked = sorted(r["n"] for r in refs if r.get("conditional_on") and r["n"] in listed)
    held = sorted((r["n"], r["conditional_on"]) for r in refs if r.get("conditional_on"))
    return not leaked, ("conditional entries %s; of those, present in the list: %s"
                        % (held, leaked or "none"))


def check4_verified():
    refs = load()
    bad = sorted(r["n"] for r in refs if not r.get("verified_from"))
    return not bad, "%d entries, %d without verified_from %s" % (
        len(refs), len(bad), bad or "")


def check5_caveats():
    refs = load()
    bib = io.open(BIB, encoding="utf-8").read() if BIB.exists() else ""
    have = [r for r in refs if r.get("caveat") and not r.get("conditional_on")]
    lost = sorted(r["n"] for r in have if r["caveat"] not in bib)
    return not lost, "%d caveats on entries that ship, %d missing from refs.bib %s" % (
        len(have), len(lost), lost or "")


CHECKS = [("1 markers resolve both ways", check1_markers),
          ("2 list and bib are generated", check2_generated),
          ("3 conditional entries held back", check3_conditional),
          ("4 every entry verified", check4_verified),
          ("5 caveats survive into the bib", check5_caveats)]


def run():
    ok_all = True
    for name, fn in CHECKS:
        ok, why = fn()
        ok_all &= ok
        print("  %-34s %-6s %s" % (name, "pass" if ok else "**FAIL**", why))
    return ok_all


def selftest():
    """Break each check on purpose. A check that cannot go red is not a check."""
    print("=" * 96)
    print("self test: each check has to fail when the thing it guards is broken")
    print("=" * 96)
    results = []

    report = io.open(REPORT, encoding="utf-8").read()
    refs_raw = io.open(REFS, encoding="utf-8").read()

    # 1 a marker with no entry behind it
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(
        report.replace("## References", "A sentence citing [99].\n\n## References", 1))
    ok, why = check1_markers()
    results.append(("1 markers", not ok, why))
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(report)

    # 2 the list edited by hand, away from what refs.json generates
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(
        report.replace("1. Jong, M. R.,", "1. Jong, M. Q.,", 1))
    ok, why = check2_generated()
    results.append(("2 generated", not ok, why))
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(report)

    refs = json.loads(refs_raw)

    # 3 a conditional entry that leaked into the list
    n_cond = next(r["n"] for r in refs if r.get("conditional_on"))
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(
        report.replace("<!-- END references -->",
                       "%d. A conditional entry that should not be here.\n"
                       "<!-- END references -->" % n_cond, 1))
    ok, why = check3_conditional()
    results.append(("3 conditional", not ok, why))
    io.open(REPORT, "w", encoding="utf-8", newline="\n").write(report)

    # 4 and 5 break refs.json itself
    for tag, mutate, fn in (
            ("4 verified", lambda d: d[0].update(verified_from=None), check4_verified),
            ("5 caveats", lambda d: next(r for r in d if r.get("caveat"))
                .update(caveat="a caveat that is not in the bib"), check5_caveats)):
        d = json.loads(refs_raw)
        mutate(d)
        io.open(REFS, "w", encoding="utf-8", newline="\n").write(
            json.dumps(d, ensure_ascii=False, indent=1) + "\n")
        ok, why = fn()
        results.append((tag, not ok, why))
        io.open(REFS, "w", encoding="utf-8", newline="\n").write(refs_raw)

    bad = [n for n, red, _ in results if not red]
    for n, red, why in results:
        print("  %-34s %s   %s"
              % (n, "went red" if red else "**STAYED GREEN, so it is not a check**", why))
    if bad:
        print("\nthese checks do not detect what they are supposed to: %s" % bad)
        sys.exit(2)
    print("\n  all five can fail. now the real run.")


def main():
    if "--selftest" in sys.argv:
        selftest()
    print("=" * 96)
    print("real run")
    print("=" * 96)
    if not run():
        sys.exit(1)
    print("\n  all five pass.")


if __name__ == "__main__":
    main()
