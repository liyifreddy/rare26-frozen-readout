# -*- coding: utf-8 -*-
"""The classifier that produced every verdict in `docs/` and in the report.

A comparison is never read off a point estimate. It is classified from both
cross-center directions together, using the paired bootstrap interval in each
direction and one threshold.

    detectable(d, lo, hi)  the interval excludes zero
    threshold              0.0165 on the AUROC scale, taken from a power curve
                           measured on this data rather than chosen

    E   the two directions have opposite signs, at least one is detectable, and
        the larger of the two reaches the threshold
    A+  both detectable and positive, and both at or above the threshold
    A-  both detectable and negative, and both at or above it in absolute value
    B+  both detectable and positive, at least one below the threshold
    B-  both detectable and negative, at least one below it in absolute value
    C   both intervals lie wholly inside the threshold band, so the comparison is
        ruled out rather than unmeasured
    D   anything else, including the case where neither direction is detectable

Two details are easy to get wrong and both cost us a published claim before they
were fixed:

* The sign constraint. An earlier version required only that both directions be
  detectable and large enough, without requiring them to agree in sign. It labeled
  configurations that were reliably worse as established.
* E requires at least one direction to be detectable. Without that, two pure noise
  estimates that happen to fall on opposite sides are reported as a reversal with
  the training center, which reads as a substantive finding about instability.

Usage:
    python src/verdict.py --demo
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

THRESHOLD = 0.0165
EPS = 1e-9


def classify(a, b, threshold=THRESHOLD):
    """Classify one comparison. `a` and `b` are (point, lo, hi) per direction."""
    da, la, ha = a
    db, lb, hb = b
    det_a, det_b = la * ha > 0, lb * hb > 0
    big = max(abs(da), abs(db)) >= threshold

    if (abs(da) > EPS and abs(db) > EPS and (da > 0) != (db > 0)
            and big and (det_a or det_b)):
        return "E"
    if det_a and det_b and (da > 0) == (db > 0):
        sign = "+" if da > 0 else "-"
        return ("A" if min(abs(da), abs(db)) >= threshold else "B") + sign
    if (ha < threshold and la > -threshold) and (hb < threshold and lb > -threshold):
        return "C"
    return "D"


# Result files do not all name the difference field the same way, and one of them
# has a field called "d" that is not a difference at all.
DELTA_FIELD = {"b1_backbone_module": "d_tukey", "c4_arm_d": "d_minus_c"}


def count_file(path):
    """Group a result file by cell, keep cells that have both directions, classify."""
    data = json.load(open(path, encoding="utf-8"))
    field = DELTA_FIELD.get(Path(path).stem, "d")
    groups = {}
    for key, v in data.items():
        if not isinstance(v, dict) or "lo" not in v or field not in v:
            continue
        parts = key.split("|")
        direction = next((p for p in parts if "→" in p), None)
        if direction is None:
            continue
        cell = tuple(p for p in parts if p != direction)
        groups.setdefault(cell, {})[direction] = v

    counts = Counter()
    for cell, per_direction in groups.items():
        a = per_direction.get("c2→c1")
        b = per_direction.get("c1→c2")
        if a and b:
            counts[classify((a[field], a["lo"], a["hi"]),
                            (b[field], b["lo"], b["hi"]))] += 1
    return counts


def demo():
    """Reproduce the row for d1_all_backbones in docs/02_backbones.md."""
    path = Path(__file__).resolve().parent.parent / "results" / "d1_all_backbones.json"
    if not path.exists():
        sys.exit("Expected %s. Run this from a checkout that includes results/." % path)
    c = count_file(path)
    order = ["A+", "A-", "B+", "B-", "C", "D", "E"]
    total = sum(c.values())
    print("d1_all_backbones.json")
    print("  cells with both directions: %d" % total)
    print("  " + "  ".join("%s %d" % (k, c[k]) for k in order))

    expected = {"total": 616, "A+": 17, "A-": 51, "B": 14, "C": 397, "D": 124, "E": 13}
    got = {"total": total, "A+": c["A+"], "A-": c["A-"], "B": c["B+"] + c["B-"],
           "C": c["C"], "D": c["D"], "E": c["E"]}
    bad = {k: (expected[k], got[k]) for k in expected if expected[k] != got[k]}
    if bad:
        print("\n  Does not match the published row: %s" % bad)
        sys.exit(1)
    print("\n  Matches the published row in docs/02_backbones.md.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true",
                    help="reproduce a published row from results/")
    ap.add_argument("--file", help="classify one result file and print the counts")
    args = ap.parse_args()
    if args.file:
        c = count_file(args.file)
        print("  ".join("%s %d" % (k, c[k])
                        for k in ["A+", "A-", "B+", "B-", "C", "D", "E"]))
    else:
        demo()
