# -*- coding: utf-8 -*-
"""Regenerate the verdict tables from results/.

Nothing here is drawn by hand. Every count is recomputed from the result files by
`src/verdict.py`, the same classifier that produced the tables, and cross-checked
against the published table before anything is plotted. A mismatch is a hard stop.

Output is markdown, not an image. A rendered chart carries a background color and
reads badly in whichever of GitHub's two themes it was not drawn for; a table follows
the reader's theme and can be searched, diffed and copied.

Usage:  python tools/make_tables.py
"""
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from verdict import DELTA_FIELD, classify                         # noqa: E402
from collections import Counter                                   # noqa: E402

OUT = ROOT / "docs"

# name, result file, published counts (A+, A-, B+ plus B-, C, D, E) from the report table.
FAMILIES = [
    ("All backbones, A-class components", "d1_all_backbones",   (17, 51, 14, 397, 124, 13)),
    ("Read-out basis x component",        "e3_basis_component",  (39, 14, 28, 101, 259, 33)),
    ("Normalization family",              "d2_norm_family",       (0, 33,  9,  89,  43,  2)),
    ("Layer 3+4 replication",             "e3b_cnn_layer",        (0,  7,  5,  32, 148,  0)),
    ("Same-backbone head fusion",         "r6_fusion",            (0, 25, 31,  32,   9,  2)),
    ("Backbone x module interaction",     "b1_backbone_module",   (0,  0,  9,  23,  16,  0)),
    ("One-class vs discriminant",         "q1_oneclass_all",      (0, 40,  0,   0,   4,  0)),
    ("Instance selection (MIL)",          "r5_mil",               (3,  0,  0,   7,  22,  1)),
    ("Geometric read-outs",               "q3_geometry_all",      (0,  4,  4,   8,  15,  1)),
    ("TTA and color normalization",       "r8_tta_color",         (0,  1,  0,  15,  12,  2)),
    ("External covariance target",        "r2_extcov",            (0,  4,  9,  13,   1,  0)),
    ("Fit-scope arm D",                   "c4_arm_d",             (0,  4,  2,   0,   9,  1)),
    ("Field-of-view mask",                "c2_fov_mask",          (0,  0,  0,  14,   2,  0)),
    ("Layer choice",                      "r4_layer",             (1,  0,  1,   0,   9,  0)),
    ("Greedy combination search",         "r11_combo",            (1,  3,  0,   0,   2,  5)),
    ("Multi-backbone fusion",             "r7_bbfusion",          (0,  0,  1,   3,   6,  0)),
]

# What each family varied. Taken from the keys in its result file, not from memory.
VARIED = {
    "d1_all_backbones":   "eleven weight sets x the components that had passed an earlier grid",
    "b1_backbone_module": "backbone x field-of-view mask, two-stage resize, pooling operator",
    "r7_bbfusion":        "score-level fusion across backbones",
    "e3_basis_component": "read-out basis x power transform x shrinkage x fit scope x pooling",
    "e3b_cnn_layer":      "the same component menu, on layer 3+4 instead of layer 4",
    "r4_layer":           "which layer the features are taken from",
    "q1_oneclass_all":    "modeling the normal class alone instead of a discriminant",
    "q3_geometry_all":    "kNN density ratio, Ledoit-Wolf and OAS shrinkage, random subspace",
    "r2_extcov":          "an external covariance target, shrinkage swept 0.02 to 0.90",
    "c4_arm_d":           "what data the head is fitted on",
    "r6_fusion":          "fusing two heads on one backbone, weight swept 0.50 to 1.00",
    "r5_mil":             "top-q instance selection, q = 0.50 / 0.25 / 0.10",
    "d2_norm_family":     "per-dimension z, L2, per-position z, none, crossed with shrinkage",
    "r8_tta_color":       "horizontal-flip TTA and white-patch color normalization",
    "c2_fov_mask":        "masking the endoscope's circular field of view",
    "r11_combo":          "building the configuration one component at a time",
}

# An editorial grouping, for reading only. The sixteen families are the experimental
# units; nothing in the report depends on these six headings. Change them here.
THEMES = [
    ("The choice of pretrained weights, and what it interacts with", ["d1_all_backbones", "b1_backbone_module",
                                           "r7_bbfusion"]),
    ("How features come off the network", ["e3_basis_component", "e3b_cnn_layer",
                                           "r4_layer"]),
    ("How the head is built",             ["q1_oneclass_all", "q3_geometry_all",
                                           "r2_extcov", "c4_arm_d", "r6_fusion"]),
    ("How 49 positions become one score", ["r5_mil"]),
    ("Preprocessing and invariance",      ["d2_norm_family", "r8_tta_color",
                                           "c2_fov_mask"]),
    ("How the configuration is assembled", ["r11_combo"]),
]


# Stack order runs from established improvement, through the neutral middle, to
# established degradation, with the conflict class last.
# Only these two grids are published with duplicates removed; the report annotates
# both as "(96 dup removed)". No other family carries that annotation, so none is
# deduplicated here. docs/07_verdict_counts.md records one consequence of that.
DEDUP = {"e3_basis_component", "e3b_cnn_layer"}

ORDER  = ["A+", "B+", "C", "D", "B-", "A-", "E"]

# The figure does not use the seven letter classes. A reader should not have to learn a
# taxonomy to read a picture, so the figure collapses them into four plain groups and the
# table below it keeps the full breakdown.
GROUPS = [
    ("better", ["A+", "B+"]),
    ("worse", ["A-", "B-"]),
    ("conflict", ["E"]),
    ("could not separate", ["C", "D"]),
]
LABEL  = {"A+": "A+  improved, established", "B+": "B+  improved, below threshold",
          "C":  "C  ruled out",              "D":  "D  tested, not detected",
          "B-": "B-  degraded, below threshold", "A-": "A-  degraded, established",
          "E":  "E  directions conflict"}

# Only these two grids are published with duplicates removed; the report annotates both
# as "(96 dup removed)". On a 7x7 grid the top 2% of the 49 positions is the maximum, so
# the "top2%" and "max" pooling rules are the same operation and produce bit-identical
# numbers. No other family carries that annotation, so none is deduplicated here.
DEDUP = {"e3_basis_component", "e3b_cnn_layer"}


def count_file_dedup(path, dedup):
    data = json.load(open(path, encoding="utf-8"))
    field = DELTA_FIELD.get(Path(path).stem, "d")
    groups = {}
    for key, v in data.items():
        if not isinstance(v, dict) or "lo" not in v or field not in v:
            continue
        parts = key.split("|")
        direction = next((p for p in parts if "\u2192" in p), None)
        if direction is None:
            continue
        groups.setdefault(tuple(p for p in parts if p != direction), {})[direction] = v

    counts, fingerprints, dropped = Counter(), set(), 0
    for cell in sorted(groups):
        a = groups[cell].get("c2\u2192c1")
        b = groups[cell].get("c1\u2192c2")
        if not (a and b):
            continue
        pa = (a[field], a["lo"], a["hi"])
        pb = (b[field], b["lo"], b["hi"])
        fp = (cell[0], cell[1] if len(cell) > 1 else "", pa, pb)
        if dedup and fp in fingerprints:
            dropped += 1
            continue
        fingerprints.add(fp)
        counts[classify(pa, pb)] += 1
    return counts, dropped


def counts():
    rows, problems = [], []
    for name, stem, published in FAMILIES:
        path = ROOT / "results" / f"{stem}.json"
        if not path.exists():
            problems.append(f"{stem}: result file missing"); continue
        c, dropped = count_file_dedup(path, stem in DEDUP)
        got = (c["A+"], c["A-"], c["B+"] + c["B-"], c["C"], c["D"], c["E"])
        if got != published:
            problems.append(f"{stem}: recomputed {got} vs published {published}")
        if dropped:
            print(f"  {stem}: dropped {dropped} duplicate cells (top 2% == max on a 7x7 grid)")
        rows.append((name, c, sum(c.values())))
    return rows, problems


def write_lf(path, text):
    """Write with LF endings on every platform. See the note in inject()."""
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


BEGIN = "<!-- BEGIN %s (generated by tools/make_tables.py; do not edit by hand) -->"
END = "<!-- END %s -->"



# Result-file keys were written in Chinese during development. This is the only
# hand-written mapping in this script; `write_inventory` stops if it meets a token that
# is not here, so nothing can be silently dropped or left untranslated.
TRANSLATE = {
    "\u5e42\u5f00": "power transform on (alpha = 0.5)",
    "\u5e42\u5173": "power transform off",
    "\u5747\u503c": "global average",
    "\u6700\u5927": "maximum",
    "\u79e9": "rank",
    "GAP(\u5168\u90e8\u5e73\u5747)": "global average pooling",
    "top1(\u540c\u7b97\u5b50)": "top 1 position",
    "LW \u6536\u7f29": "Ledoit-Wolf shrinkage",
    "OAS \u6536\u7f29": "oracle-approximating shrinkage",
    "kNN \u5bc6\u5ea6\u6bd4 k=20": "k-nearest-neighbor density ratio, k = 20",
    "\u968f\u673a\u5b50\u7a7a\u95f4 0.25\u00d720": "random subspace, 25% of dimensions, 20 draws",
    "hflip-TTA(\u5e73\u5747)": "horizontal-flip TTA, averaged",
    "hflip-TTA(\u66ff\u6362)": "horizontal-flip TTA, replaced",
    "white-patch(\u66ff\u6362)": "white-patch color normalization",
    "\u9776=\u03c4I\uff08\u4ea4\u4ed8\uff09": "target: scaled identity (delivered)",
    "\u9776=diag(\u03a3)\u81ea\u5bb6": "target: diagonal of the in-domain covariance",
    "S1 {5M,1M,SWSL}\u5f3a\u5ea6\u76f8\u5f53": "S1: three in-domain CNNs of comparable strength",
    "S2 6\u57df\u5185CNN": "S2: six in-domain CNNs",
    "S3 8CNN(\u542b\u57df\u5916)": "S3: eight CNNs including out-of-domain",
    "S4 \u8de8\u67b6\u6784\u4e09\u5143": "S4: three backbones across architectures",
    "S5 \u5168\u90e811": "S5: all eleven",
}
# Read-out bases. The codes appear in two result files and mean nothing on their own.
# Source: the header of scripts/E1, which defined them before the grid was run.
TRANSLATE.update({
    "A1": "A1: the layer-4 spatial map, 7x7",
    "A2": "A2: layers 3 and 4 together",
    "A3": "A3: the layer-4 map, globally averaged",
    "B1": "B1: last-layer patch grid",
    "B2": "B2: last two blocks, patches concatenated",
    "B3": "B3: class token broadcast into every patch",
    "B4": "B4: last-layer class token alone",
    "B5": "B5: last four blocks, class tokens concatenated",
    "B6": "B6: class token with the patch mean",
})

# Patterns handled by rule rather than by entry.
TRANSLATE_RE = [
    (r"^top(\d+)%\(\u540c\u6bd4\u4f8b,k=(\d+)\)$", r"top \1% of positions (k = \2)"),
    (r"^\u03bb([\d.]+)$", r"shrinkage \1"),
    (r"^q([\d.]+)$", r"fit scope \1"),
    (r"^w=([\d.]+)$", r"weight \1"),
    (r"^q=([\d.]+)$", r"top \1 of positions"),
    (r"^top(\d+)%$", r"top \1% of positions"),
    (r"^\[\u8bca\u65ad\](.+) \u03bb=(.+)$", r"diagnostic: \1, shrinkage \2"),
    (r"^\u7eaf\u03a3_ext\((.+)\)\u03bb=1$", r"external covariance only, \1, no shrinkage"),
    (r"^\u9776=(diag)?\u03a3_ext\((.+)\)$", r"target: \1 external covariance, \2"),
]
CORPUS = {"\u672a\u7b5b": "unfiltered", "\u7b5b\u98df\u7ba1": "esophagus only",
          "EVC\u98df\u7ba1\u57df(\u4ec5100\u56fe)": "EVC esophagus domain, 100 images"}


def english(tok):
    import re as _re
    if tok in TRANSLATE:
        return TRANSLATE[tok]
    for pat, rep in TRANSLATE_RE:
        m = _re.match(pat, tok)
        if m:
            out = _re.sub(pat, rep, tok)
            for cn, en in CORPUS.items():
                out = out.replace(cn, en)
            return " ".join(out.replace("diag ", "diagonal ").split())
    if _re.search(r"[\u4e00-\u9fff]", tok):
        sys.exit(f"[stop] no English for the result-file token {tok!r}. "
                 "Add it to TRANSLATE or TRANSLATE_RE rather than letting it through.")
    return tok


def inject(path, marker, block):
    """Replace the block between the markers. The README is not a second copy of the
    numbers; it is generated from the same run that writes the long table."""
    text = path.read_text(encoding="utf-8")
    a, b = BEGIN % marker, END % marker
    if a not in text or b not in text:
        sys.exit(f"[stop] {path.name} is missing the {marker} markers")
    i, j = text.index(a) + len(a), text.index(b)
    # newline="\n" is not optional. Python's text mode writes CRLF on Windows, and one
    # run then rewrites every line of the file in git. That is where an unexplained
    # whole-file diff came from once already, in a gate's own self test.
    write_lf(path, text[:i] + "\n" + block + "\n" + text[j:])



# What each column of a result key means, named from the RIGHT because two families
# write a variable number of columns. A family whose keys are wider than its entry here
# stops the script rather than mislabeling an axis.
AXES = {
    "d1_all_backbones":   ["module", "backbone", "shrinkage", "component"],
    "b1_backbone_module": ["backbone", "pooling or module", "shrinkage"],
    "r7_bbfusion":        ["candidate pool", "combination rule"],
    "e3_basis_component": ["backbone", "read-out basis", "component"],
    "e3b_cnn_layer":      ["backbone", "read-out basis", "component"],
    "r4_layer":           ["backbone"],
    "q1_oneclass_all":    ["backbone", "shrinkage"],
    "q3_geometry_all":    ["backbone", "method"],
    "r2_extcov":          ["covariance target"],
    "c4_arm_d":           ["backbone", "shrinkage"],
    "r6_fusion":          ["backbone", "fusion weight"],
    "r5_mil":             ["backbone", "selected fraction"],
    "d2_norm_family":     ["backbone", "shrinkage", "feature normalization"],
    "r8_tta_color":       ["backbone", "method"],
    "c2_fov_mask":        ["backbone", "shrinkage"],
    "r11_combo":          ["backbone"],
}
BACKBONES = {"RN50-gastro5M", "RN50-1M", "RN50-200K", "RN50-SWSL", "RN50-MOCOv2",
             "RN50-SIMCLRv2", "RN50-in1k-sup", "RN50-in1k-dino", "ViTS-gastro",
             "ViTS-in1k-dino", "DINOv2-ViT-B"}


def levels(stem):
    """Distinct levels per axis, read off the result-file keys."""
    import re as _re
    from collections import defaultdict
    data = json.load(open(ROOT / "results" / f"{stem}.json", encoding="utf-8"))
    names, cols, widest = AXES[stem], defaultdict(set), 0
    for key, v in data.items():
        if not isinstance(v, dict) or "lo" not in v:
            continue
        parts = [p for p in key.split("|") if "\u2192" not in p]
        widest = max(widest, len(parts))
        for i, p in enumerate(parts):                 # right-aligned
            cols[names[len(names) - len(parts) + i]].add(p)
    if widest > len(names):
        sys.exit(f"[stop] {stem} keys have {widest} columns but AXES lists {len(names)}")
    out = []
    for n in names:
        if n not in cols:
            continue
        vals = sorted(cols[n])
        if any("\u00b7" in x for x in vals):          # a component is itself a crossing
            sub = defaultdict(set)
            for x in vals:
                for j, y in enumerate(x.split("\u00b7")):
                    sub[j].add(y.strip())
            for j in sorted(sub):
                out.append((f"{n}, part {j + 1}", sorted(english(y) for y in sub[j])))
        else:
            out.append((n, sorted(english(x) for x in vals)))
    return out


def write_inventory(rows):
    """docs/08: what was actually compared, axis by axis, read off the result files."""
    by_stem = {f[1]: (f[0], r[2]) for f, r in zip(FAMILIES, rows)}
    L = ["# What was tested", "",
         "Regenerated by `tools/make_tables.py` from the keys of the files in `results/`. "
         "Nothing here is transcribed by hand; the only hand-written part is the English "
         "for names that were written in Chinese during development, and the script stops "
         "if it meets a name it has no English for.", "",
         "`07_verdict_counts.md` says how each comparison came out. This page says what was "
         "compared.", "",
         "## The eleven sets of pretrained weights", "",
         "These are an axis inside most families, not a family of their own. That is why a "
         "row in the README covering three families can hold several hundred comparisons: "
         "each family crosses these eleven with something else.", "",
         "| Weights | Architecture | Corpus | Pretraining |", "|---|---|---|---|",
         "| RN50-gastro5M | ResNet-50 | GastroNet-5M | DINOv1 |",
         "| RN50-1M | ResNet-50 | 1M subset | DINOv1 |",
         "| RN50-200K | ResNet-50 | 200K subset | DINOv1 |",
         "| RN50-SWSL | ResNet-50 | GastroNet-5M | billion-scale semi-supervised init, then DINOv1 |",
         "| RN50-MOCOv2 | ResNet-50 | in domain | MoCo v2 |",
         "| RN50-SIMCLRv2 | ResNet-50 | in domain | SimCLR v2 |",
         "| ViTS-gastro | ViT-S/16 | in domain | DINOv1 |",
         "| DINOv2-ViT-B | ViT-B | in domain | DINOv2 |",
         "| RN50-in1k-sup | ResNet-50 | ImageNet-1k | supervised |",
         "| RN50-in1k-dino | ResNet-50 | ImageNet-1k | DINO |",
         "| ViTS-in1k-dino | ViT-S/16 | ImageNet-1k | DINO |", "",
         "The first eight are the provider's listing; the last three are out-of-domain "
         "baselines carried for contrast. Provenance is in `deliver`-side notes and in "
         "section 3 of the report.", ""]
    for theme, stems in THEMES:
        L += [f"## {theme}", ""]
        for st in sorted(stems, key=lambda x: -by_stem[x][1]):
            name, n = by_stem[st]
            L += [f"### {name}", "",
                  f"{VARIED[st]}. {n} comparisons, from `results/{st}.json`.", "",
                  "| Axis | Levels tested |", "|---|---|"]
            for axis, vals in levels(st):
                if axis == "backbone" and set(vals) <= BACKBONES:
                    shown = f"the {len(vals)} sets above" if len(vals) == 11 else \
                            f"{len(vals)} of the eleven: " + ", ".join(f"`{v}`" for v in vals)
                else:
                    shown = ", ".join(f"`{v}`" for v in vals)
                L += [f"| {axis} ({len(vals)}) | {shown} |"]
            L += [""]
    write_lf(OUT / "08_what_was_tested.md", "\n".join(L) + "\n")


def write_tables(rows):
    """Two tables. The README gets six themes; the long table keeps all sixteen families
    with the seven classes and what each one varied."""
    OUT.mkdir(parents=True, exist_ok=True)
    by_stem = {stem: (name, c, n) for (name, _, _), (stem, _), (_, c, n)
               in zip(FAMILIES, [(f[1], None) for f in FAMILIES], rows)}

    listed = [st for _, stems in THEMES for st in stems]
    if sorted(listed) != sorted(by_stem):
        sys.exit("[stop] THEMES does not partition FAMILIES exactly: "
                 f"missing {sorted(set(by_stem) - set(listed))}, "
                 f"extra {sorted(set(listed) - set(by_stem))}, "
                 f"duplicated {sorted({x for x in listed if listed.count(x) > 1})}")

    def cells(counter):
        return {g: sum(counter[k] for k in ks) for g, ks in GROUPS}

    # --- README: six themes ---
    L = ["| What was varied | families | comparisons | better | worse | conflict | could not separate |",
         "|---|---:|---:|---:|---:|---:|---:|"]
    grand = Counter()
    for theme, stems in THEMES:
        acc, n = Counter(), 0
        for st in stems:
            acc.update(by_stem[st][1]); n += by_stem[st][2]
        grand.update(acc)
        c = cells(acc)
        L.append(f"| {theme} | {len(stems)} | {n} | " + " | ".join(
            str(c[g]) if c[g] else "&mdash;" for g, _ in GROUPS[:3])
            + f" | {c['could not separate']} ({100*c['could not separate']/n:.0f}%) |")
    n_all = sum(r[2] for r in rows)
    c = cells(grand)
    L.append(f"| **All of it** | **{len(rows)}** | **{n_all}** | " + " | ".join(
        f"**{c[g]}**" for g, _ in GROUPS[:3])
        + f" | **{c['could not separate']} ({100*c['could not separate']/n_all:.0f}%)** |")
    inject(ROOT / "README.md", "verdict-table", "\n".join(L))

    # --- docs/07: all sixteen, grouped, with what each varied ---
    M = []
    for theme, stems in THEMES:
        M.append(f"\n### {theme}\n")
        M.append("| Experiment family | What it varied | n | "
                 + " | ".join(ORDER) + " |")
        M.append("|---|---|---:" + "|---:" * len(ORDER) + "|")
        for st in sorted(stems, key=lambda x: -by_stem[x][2]):
            name, cc, n = by_stem[st]
            M.append(f"| {name} | {VARIED[st]} | {n} | "
                     + " | ".join(str(cc[k]) if cc[k] else "&mdash;" for k in ORDER) + " |")
    tot = Counter()
    for _, cc, _ in rows:
        tot.update(cc)
    M.append("\n### All families\n")
    M.append("| | n | " + " | ".join(ORDER) + " |")
    M.append("|---|---:" + "|---:" * len(ORDER) + "|")
    M.append(f"| **Total** | **{n_all}** | "
             + " | ".join(f"**{tot[k]}**" for k in ORDER) + " |")

    body = ("# Verdict counts, family by family\n\n"
            "Regenerated by `tools/make_tables.py`. Every count is recomputed from "
            "`results/` by `src/verdict.py` and checked against the tables in the report "
            "before it is written here; a mismatch stops the script.\n\n"
            "The six headings are an editorial grouping, for reading only. The sixteen "
            "families are the experimental units, and nothing in the report depends on how "
            "they are grouped here.\n\n"
            "| Class | Meaning |\n|---|---|\n"
            "| A+ / A- | detectable in both cross-center directions, same sign, both at or "
            "above the practical threshold |\n"
            "| B+ / B- | detectable in both directions, same sign, at least one below the "
            "threshold |\n"
            "| C | both intervals lie wholly inside the threshold band, so the comparison "
            "is ruled out rather than unmeasured. The band is defined on the AUROC scale, "
            "so this rules the comparison out on that scale and says nothing about the "
            "ranking metric; see `00_evaluation_protocol.md` |\n"
            "| D | tested, nothing detected |\n"
            "| E | the two directions disagree in sign |\n\n"
            "The classes are defined in `00_evaluation_protocol.md` and implemented in "
            "`src/verdict.py`. The README folds them into four groups: `better` is A+ and "
            "B+, `worse` is A- and B-, `could not separate` is C and D.\n"
            + "\n".join(M) + "\n\n"
            "## Two notes on the counts\n\n"
            "Two grids are counted after removing duplicates, as the report annotates. On a "
            "7x7 grid the top 2% of the 49 positions is the maximum, so the `top2%` and "
            "`max` pooling rules are the same operation and produce bit-identical numbers; "
            "96 such cells are removed from each of those two grids.\n\n"
            "`d1_all_backbones.json` contains 65 cells whose paired differences are "
            "identically zero in all six numbers. Their keys are `top1(same operator)` and "
            "`top2%(same ratio, k=1)`: the baseline operator compared with itself, so the "
            "difference cannot be anything but zero and does not depend on the shrinkage. "
            "This is not the duplication the two annotated grids remove, where two names "
            "denote one operator; it is a cell comparing a configuration to itself. The "
            "published table counts all 616, and removing them moves only class C, from "
            "397 to 332. We have not changed "
            "the published number, because the same rule applied inconsistently is worse than "
            "one rule applied openly, and no class that carries a claim in the report is "
            "affected. It is recorded here and in `05_what_we_got_wrong.md` rather than "
            "quietly corrected.\n")
    write_lf(OUT / "07_verdict_counts.md", body)


if __name__ == "__main__":
    rows, problems = counts()
    if problems:
        print("[STOP] recomputed counts do not match the published table:")
        for p in problems:
            print("   -", p)
        sys.exit(1)
    write_tables(rows)
    write_inventory(rows)
    print(f"{len(rows)} families, {sum(r[2] for r in rows)} comparisons, "
          "all matching the published table.")
    print("injected the README table; wrote docs/07_verdict_counts.md and "
          "docs/08_what_was_tested.md")
