# -*- coding: utf-8 -*-
"""Draw the report figures from the files in results/, and refuse to draw a wrong one.

Every number a figure shows is read from `results/` or computed by the same model the
report uses. Nothing is typed in here. Each figure ends with a reconciliation against the
values already published in REPORT.md; a mismatch stops the run rather than producing a
picture that disagrees with the text next to it.

Three figures live here.

  negtail     How far the negative scores reach above the operating threshold, one curve
              per cross-center direction, plus the share the challenge evaluator implies
              for its own validation set. That last one is a line, not a curve, because
              the evaluator returns summary statistics only.
  labelnoise  What a flipped label costs each of the two keys. Four panels, because the
              range the report quotes is measured across two cross-center directions and
              two flip models, and a single pair of curves cannot support it.
  auroc_ppv   The correspondence between AUROC and the ranking metric under an
              equal-variance bi-normal model. This one is a model, not a measurement, and
              the caption says so; the check is that it reproduces the table in section 1
              of the report cell for cell.

**Only the SVG is published.** `.gitignore` excludes `*.png` without exception, because
this repository must never carry an endoscopy frame, and a rule with an exception costs
every future reader a check of whether the file they are looking at is inside the
exception. The PNGs written next to the SVGs are a local preview convenience and are
meant to stay untracked -- do not add an exception to `.gitignore` for them, and do not
add a whitelist to the leak gate. `svg.fonttype = "path"` converts every glyph to a
vector outline, so the SVG carries no font dependency and renders identically anywhere;
the cost is a larger file and text that cannot be selected, which is the right trade for
a published figure.

Each figure is written twice, once per theme. Dark is not an inversion of light: the two
categorical hues are re-stepped for the dark surface from the same ramps, and both sets
were run through the palette validator against their own surface.

Usage:
    python tools/make_figures.py            write SVG (published) and PNG (local) per theme
    python tools/make_figures.py --check    reconcile only, write nothing
"""
import argparse
import io
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "path"
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "figures"

# Both columns are selected against their own surface, not flipped. Values are the
# validated categorical slots 1 and 2 and the chrome tokens for each mode.
THEMES = {
    "light": dict(SURFACE="#fcfcfb", INK="#0b0b0b", INK_2="#52514e", MUTED="#898781",
                  GRID="#e1e0d9", AXIS="#c3c2b7", S1="#2a78d6", S2="#eb6834"),
    "dark": dict(SURFACE="#1a1a19", INK="#ffffff", INK_2="#c3c2b7", MUTED="#898781",
                 GRID="#2c2c2a", AXIS="#383835", S1="#3987e5", S2="#d95926"),
}
C = THEMES["light"]

PREVALENCE = 0.01
SENSITIVITY = 0.90


def load(name):
    return json.load(io.open(RESULTS / ("%s.json" % name), encoding="utf-8"))


def style(ax):
    """Recessive grid and axes; the data is the only thing with weight."""
    ax.set_facecolor(C["SURFACE"])
    ax.grid(True, color=C["GRID"], linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(C["AXIS"])
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=C["MUTED"], labelsize=8, length=3, width=1.0)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_color(C["INK_2"])


def save(fig, stem, write, theme):
    if not write:
        plt.close(fig)
        return []
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    # SVG is the published artifact; PNG is a local preview and stays gitignored.
    for ext, kw in (("svg", {}), ("png", {"dpi": 200})):
        p = OUT / ("%s_%s.%s" % (stem, theme, ext))
        fig.savefig(p, facecolor=C["SURFACE"], edgecolor="none", bbox_inches="tight", **kw)
        made.append(p)
    plt.close(fig)
    return made


# --------------------------------------------------------------------------- figure 1
def fig_negtail(write, theme):
    d = load("p39_negative_tail")
    platform = load("p31_platform_leaderboard")["RARE26"]
    grid = np.array(d["grid_z"])
    dirs = ["c2→c1", "c1→c2"]
    color = {"c2→c1": C["S1"], "c1→c2": C["S2"]}

    # The evaluator never returns a specificity, only the ranking metric. Inverting it is
    # exact algebra at a fixed recall and prevalence, not a fit: this share is the measured
    # PPV re-expressed, which is why it can be drawn as a line and never as a curve.
    share_platform = (SENSITIVITY * PREVALENCE * (1 - platform["ppv90"])
                      / (platform["ppv90"] * (1 - PREVALENCE)))
    for dn in dirs:
        # Tolerance, not equality: the file stores the share to 6 decimals and the
        # specificity to 7, so an exact test compares two different roundings of one
        # number and fails on a difference that is not there.
        if abs((1 - d[dn]["share_above_threshold"])
               - d[dn]["specificity_at_90_recall"]) > 1e-6:
            sys.exit("**figure 1: tail share and specificity disagree for %s**" % dn)
    if round(d["c2→c1"]["specificity_at_90_recall"], 7) != 0.8935978:
        sys.exit("**figure 1 does not reconcile with the published specificity**")

    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    fig.patch.set_facecolor(C["SURFACE"])
    style(ax)

    # The platform share gets a different visual language on purpose: dotted, neutral, and
    # flat. It is one number, not a distribution, and it must not read as a third curve.
    ax.axhline(share_platform, color=C["MUTED"], linewidth=1.4, linestyle=(0, (2, 3)),
               zorder=2)
    # Right end, above its own line: at the left end both curves are still at 100% and the
    # label landed on top of them.
    ax.annotate("challenge validation set, %.1f%% of negatives above threshold\n"
                "leaderboard summary only — curve not obtainable"
                % (share_platform * 100),
                (grid[-1], share_platform), textcoords="offset points", xytext=(0, 7),
                color=C["MUTED"], fontsize=8.5, ha="right", va="bottom", zorder=5)

    for dn in dirs:
        surv = np.array(d[dn]["survival"])
        m = surv > 0
        ax.plot(grid[m], surv[m], color=color[dn], linewidth=2.0, zorder=3)
        tz, share = d[dn]["threshold_z"], d[dn]["share_above_threshold"]
        ax.plot([tz, tz], [1e-4, share], color=color[dn], linewidth=1.2,
                linestyle=(0, (5, 4)), zorder=2)
        ax.plot([tz], [share], marker="o", markersize=7, color=color[dn],
                markeredgecolor=C["SURFACE"], markeredgewidth=1.5, zorder=4)
        ax.annotate("%s\n%.1f%% above its threshold" % (dn, share * 100), (tz, share),
                    textcoords="offset points", xytext=(9, 4), color=C["INK"], fontsize=9,
                    ha="left", va="bottom", zorder=5)

    ax.set_yscale("log")
    ax.set_xlim(grid[0] - 0.2, grid[-1] + 0.4)
    ax.set_ylim(2e-4, 1.6)
    ax.set_yticks([0.001, 0.01, 0.1, 1.0])
    ax.set_yticklabels(["0.1%", "1%", "10%", "100%"])
    ax.minorticks_off()
    ax.set_xlabel("score, standardized within each direction against its own negatives",
                  color=C["INK_2"], fontsize=9)
    ax.set_ylabel("share of negatives at or above", color=C["INK_2"], fontsize=9)
    ax.set_title("How far the negative scores reach above the operating threshold",
                 color=C["INK"], fontsize=11, loc="left", pad=10)
    note = ("Both curves are measured, from %d and %d negatives. Each is standardized"
            " against its own negatives,"
            % (d["c2→c1"]["n_negatives"], d["c1→c2"]["n_negatives"]) + chr(10) +
            "so the two tails should coincide, and they do: the %.1f%% and the %.1f%%"
            " differ because the thresholds fall at" % (
                d["c2→c1"]["share_above_threshold"] * 100,
                d["c1→c2"]["share_above_threshold"] * 100) + chr(10) +
            "different points on one shared shape, not because the two centers'"
            " negatives are distributed differently." + chr(10) +
            "The flat line is not a curve we chose not to draw: the challenge evaluator"
            " returns summary statistics only," + chr(10) +
            "so its %.1f%% is the measured PPV inverted through the identity in section 1."
            % (share_platform * 100))
    # Below the axes, not inside them: every interior region carries either a curve, a
    # threshold drop line, or the platform line.
    fig.text(0.01, -0.02, note, color=C["INK_2"], fontsize=8.2, ha="left", va="top",
             linespacing=1.5)
    fig.tight_layout()
    return save(fig, "negtail", write, theme), {
        "c2→c1 tail": d["c2→c1"]["share_above_threshold"],
        "c1→c2 tail": d["c1→c2"]["share_above_threshold"],
        "platform share": round(share_platform, 4)}


# --------------------------------------------------------------------------- figure 3
def fig_labelnoise(write, theme):
    d = load("p16_labelflip")
    dirs = ["c2→c1", "c1→c2"]
    arms = {"A": "labels flipped at random", "B": "labels flipped worst first"}
    SER = {"ranking metric": C["S1"], "AUROC": C["S2"]}

    at5 = {k: v for k, v in d.items() if k.endswith("|0.05")}
    ppv5 = [abs(v["ppv_rel"]) for v in at5.values()]
    auc5 = [abs(v["auroc_rel"]) for v in at5.values()]
    ratio = [p / a for p, a in zip(ppv5, auc5)]
    published = {"ranking metric loss at 5%": (round(min(ppv5) * 100), round(max(ppv5) * 100),
                                               (30, 46)),
                 "AUROC loss at 5%": (round(min(auc5) * 100, 1), round(max(auc5) * 100, 1),
                                      (0.3, 2.5)),
                 "ratio at 5%": (round(min(ratio)), round(max(ratio)), (19, 106))}
    bad = {k: v for k, v in published.items() if (v[0], v[1]) != v[2]}
    if bad:
        sys.exit("**figure 3 does not reconcile with the report: %s**" % bad)

    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.2), sharex=True, sharey=True)
    fig.patch.set_facecolor(C["SURFACE"])
    for r, dn in enumerate(dirs):
        for c, arm in enumerate("AB"):
            ax = axes[r][c]
            style(ax)
            # Keep the rate as the string it is in the file. Round-tripping it through a
            # float and back rebuilds "0.0" as "0" and the lookup misses.
            prefix = "%s|%s|" % (dn, arm)
            rates = sorted((k[len(prefix):] for k in d if k.startswith(prefix)), key=float)
            xs = [float(v) * 100 for v in rates]
            for label, field in (("ranking metric", "ppv_rel"), ("AUROC", "auroc_rel")):
                y = [abs(d[prefix + v][field]) * 100 for v in rates]
                ax.plot(xs, y, color=SER[label], linewidth=2.0, linestyle="-",
                        marker="o", markersize=5, markeredgecolor=C["SURFACE"],
                        markeredgewidth=1.2, zorder=3, clip_on=False)
                # Direct label at the line end, so identity is never color alone.
                ax.annotate(label, (xs[-1], y[-1]), textcoords="offset points",
                            xytext=(6, 0), color=SER[label], fontsize=8.5, va="center",
                            ha="left", zorder=5, annotation_clip=False)
            # The ratio the title claims, written at the three rates the report quotes,
            # computed here rather than typed.
            for rate in ("0.05", "0.1", "0.2"):
                if prefix + rate not in d:
                    continue
                v = d[prefix + rate]
                if not v["auroc_rel"]:
                    continue
                k = abs(v["ppv_rel"]) / abs(v["auroc_rel"])
                # Above its own point, not on a fixed line: at a fixed height the 20%
                # label lands on the line-end label, and in the bottom row the curve is
                # already up there.
                ax.annotate("%d×" % round(k),
                            (float(rate) * 100, abs(v["ppv_rel"]) * 100),
                            textcoords="offset points", xytext=(0, 10),
                            color=C["INK_2"], fontsize=8.5, ha="center", zorder=5)
            ax.set_title("%s, %s" % (dn, arms[arm]), color=C["INK"], fontsize=9, pad=6,
                         loc="left")
    # Pinned explicitly on every panel. Leaving it to matplotlib means a row can silently
    # get its own scale and the four panels stop being comparable.
    for row in axes:
        for ax in row:
            ax.set_ylim(-3, 96)
            ax.set_xlim(-1, 21)
    measured = sorted({float(k.split("|")[2]) * 100 for k in d})
    axes[0][0].set_xticks(measured)
    axes[0][0].set_yticks([0, 20, 40, 60, 80])
    for ax in axes[1]:
        ax.set_xlabel("share of labels flipped (%)", color=C["INK_2"], fontsize=9)
    for ax in (axes[0][0], axes[1][0]):
        ax.set_ylabel("loss vs the same key\nwithout flipping (%)",
                      color=C["INK_2"], fontsize=9)
    handles = [Line2D([0], [0], color=SER[k], linewidth=2.0, linestyle="-", marker="o",
                      markersize=5, markeredgecolor=C["SURFACE"], markeredgewidth=1.2)
               for k in ("ranking metric", "AUROC")]
    leg = fig.legend(handles, ["ranking metric", "AUROC"], loc="upper right",
                     bbox_to_anchor=(0.99, 1.03), frameon=False, ncol=2, fontsize=9)
    for t in leg.get_texts():
        t.set_color(C["INK"])
    fig.suptitle("A flipped label costs the ranking metric one to two orders of magnitude "
                 "more than it costs AUROC", color=C["INK"], fontsize=11, x=0.01,
                 ha="left", y=1.07)
    fig.text(0.01, -0.045,
             "Numbers above the ranking-metric points are the ratio of the two losses at that rate."
             " The worst-first panels flatten or dip between 10% and 15%: the ranking"
             " metric takes"
             + chr(10) +
             "few distinct values, being set by a handful of positives, and across seeds"
             " its median lands on the same value at both rates in c2→c1 while the"
             " c1→c2 dip stays"
             + chr(10) +
             "inside the seed-to-seed spread. AUROC falls monotonically through that"
             " stretch in both directions, so the flatness is the metric, not the data.",
             color=C["INK_2"], fontsize=8.2, ha="left", va="top", linespacing=1.5)
    fig.tight_layout()
    return save(fig, "labelnoise", write, theme), published


# --------------------------------------------------------------------------- figure 4
def spec_at_sensitivity(auroc):
    """Equal-variance bi-normal: AUROC fixes d', d' fixes specificity at a given recall."""
    d_prime = np.sqrt(2.0) * norm.ppf(auroc)
    return norm.cdf(d_prime - norm.ppf(SENSITIVITY))


def ppv_from_spec(spec):
    num = SENSITIVITY * PREVALENCE
    return num / (num + (1.0 - spec) * (1.0 - PREVALENCE))


def fig_auroc_ppv(write, theme):
    # The table in section 1 of the report, reproduced from the model rather than copied.
    table = [(0.50, 0.100, 0.0100), (0.65, 0.231, 0.0117), (0.77, 0.406, 0.0151),
             (0.84, 0.550, 0.0198), (0.93, 0.790, 0.0414), (0.96, 0.884, 0.0726),
             (0.99, 0.978, 0.2896)]
    for a, s0, p0 in table:
        s, p = spec_at_sensitivity(a), ppv_from_spec(spec_at_sensitivity(a))
        if round(s, 3) != s0 or round(p, 4) != p0:
            sys.exit("**figure 4 model disagrees with the table in section 1 at AUROC %.2f: "
                     "spec %.3f vs %.3f, PPV %.4f vs %.4f**" % (a, s, s0, p, p0))

    platform = load("p31_platform_leaderboard")["RARE26"]
    # The clinical threshold is not a literature number we can cite as a PPV. The cited
    # target is a sensitivity and a specificity; the 0.0435 is our conversion of that pair
    # to a PPV at the prevalence this challenge evaluates at. Both steps are here so the
    # reader can redo them: 0.9 * 0.01 / (0.9 * 0.01 + 0.2 * 0.99) = 0.0435.
    SPEC_TARGET = 0.80
    ppv_clinical = ((SENSITIVITY * PREVALENCE)
                    / (SENSITIVITY * PREVALENCE + (1 - SPEC_TARGET) * (1 - PREVALENCE)))
    spec_clinical = 1 - (SENSITIVITY * PREVALENCE / ppv_clinical
                         - SENSITIVITY * PREVALENCE) / (1 - PREVALENCE)
    auroc_clinical = float(norm.cdf(
        (norm.ppf(SENSITIVITY) - norm.ppf(1 - spec_clinical)) / np.sqrt(2.0)))
    if round(ppv_clinical, 4) != 0.0435 or round(spec_clinical, 6) != round(SPEC_TARGET, 6):
        sys.exit("**the clinical threshold does not round-trip: PPV %.4f, spec %.4f**"
                 % (ppv_clinical, spec_clinical))

    x = np.linspace(0.50, 0.99, 400)
    y = [ppv_from_spec(spec_at_sensitivity(v)) for v in x]

    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    fig.patch.set_facecolor(C["SURFACE"])
    style(ax)

    # The threshold as a line across the whole figure, and the AUROC it demands as a drop
    # line. The figure exists to show the distance between where we are and that line;
    # without them the reader has to trace the curve by eye to find it.
    ax.axhline(ppv_clinical, color=C["INK_2"], linewidth=1.2, linestyle=(0, (6, 4)),
               zorder=2)
    ax.plot([auroc_clinical, auroc_clinical], [0.008, ppv_clinical], color=C["INK_2"],
            linewidth=1.2, linestyle=(0, (6, 4)), zorder=2)
    ax.plot(x, y, color=C["S1"], linewidth=2.0, zorder=3)

    # Chance: neutral, it is a reference not a result. Threshold: open marker, same ink as
    # its line. Our submission: the accent color, and the only mark carrying intervals.
    ax.plot([0.50], [ppv_from_spec(spec_at_sensitivity(0.50))], marker="o", markersize=7,
            color=C["MUTED"], markeredgecolor=C["SURFACE"], markeredgewidth=1.5, zorder=4,
            clip_on=False)
    ax.annotate("chance, 1.00%", (0.50, ppv_from_spec(spec_at_sensitivity(0.50))),
                textcoords="offset points", xytext=(0, 12), color=C["INK_2"], fontsize=9,
                ha="center", zorder=5)
    ax.plot([auroc_clinical], [ppv_clinical], marker="o", markersize=9,
            markerfacecolor=C["SURFACE"], markeredgecolor=C["INK_2"], markeredgewidth=1.8,
            zorder=4)
    ax.annotate("clinical threshold, %.2f%%\n(needs AUROC %.3f)"
                % (ppv_clinical * 100, auroc_clinical),
                (auroc_clinical, ppv_clinical), textcoords="offset points", xytext=(0, 14),
                color=C["INK"], fontsize=9, ha="center", zorder=5)

    # ⚠️ The measured point carries two 95% intervals and both are wide. Drawing it as a
    # bare dot would be a point estimate standing in for knowledge, which is the failure
    # this whole report is written against. Read from the leaderboard file, never typed.
    ax.errorbar([platform["auroc"]], [platform["ppv90"]],
                xerr=[[platform["auroc"] - platform["auroc_lo"]],
                      [platform["auroc_hi"] - platform["auroc"]]],
                yerr=[[platform["ppv90"] - platform["ppv90_lo"]],
                      [platform["ppv90_hi"] - platform["ppv90"]]],
                fmt="o", markersize=8, color=C["S2"], ecolor=C["S2"],
                elinewidth=1.4, capsize=4, capthick=1.4, markeredgecolor=C["SURFACE"],
                markeredgewidth=1.5, zorder=5, clip_on=False)
    # Left of the interval's left cap: directly under the mark would land on the x axis,
    # and above it would land inside the vertical interval.
    ax.annotate("our submission, %.2f%%" % (platform["ppv90"] * 100),
                (platform["auroc_lo"], platform["ppv90"]), textcoords="offset points",
                xytext=(-8, 0), color=C["INK"], fontsize=9, ha="right", va="center",
                zorder=5)

    # Not at ppv90_lo: that is exactly 0.0104 here, and an arrow starting on the lower cap
    # of the interval reads as part of the interval.
    gap_y = 0.0092
    ax.annotate("", xy=(auroc_clinical, gap_y), xytext=(platform["auroc"], gap_y),
                arrowprops=dict(arrowstyle="<->", color=C["INK_2"], linewidth=1.2,
                                shrinkA=0, shrinkB=0), zorder=4)
    ax.annotate("AUROC gap %.3f" % (auroc_clinical - platform["auroc"]),
                ((platform["auroc"] + auroc_clinical) / 2, gap_y),
                textcoords="offset points", xytext=(0, 5), color=C["INK_2"], fontsize=8.5,
                ha="center", zorder=5)

    # ⚠️ Only two things stay inside the frame, and they stay because the figure can be
    # forwarded on its own: what the curve is, and where the threshold comes from. The
    # rest of the reading moved to the prose under the figure in
    # docs/06_domain_shift_attribution.md. Text rendered as vector paths cannot be
    # selected, searched or read aloud, so the frame is the worst place to keep a number
    # a reader might want to check.
    note = ("The curve is a model, not data: equal-variance bi-normal at 90% recall and 1%"
            " prevalence." + chr(10) +
            "The threshold is 90% sensitivity with 80% specificity (ASGE Technology"
            " Committee," + chr(10) +
            "Gastrointest Endosc 2016;83:684-698) converted to that prevalence.")
    ax.text(0.468, 0.62, note, color=C["INK_2"], fontsize=8.2, va="top", linespacing=1.5)

    ax.set_xlabel("AUROC", color=C["INK_2"], fontsize=9)
    ax.set_ylabel("PPV at 90% recall, 1% prevalence", color=C["INK_2"], fontsize=9)
    ax.set_title("What an AUROC is worth on the ranking metric",
                 color=C["INK"], fontsize=11, loc="left", pad=10)
    # Log y. The marks are 1.00% / 1.52% / 4.35% and the figure exists to show the ratios
    # between them; on a linear axis to 0.32 they collapse into one flat line near zero,
    # which hides exactly what the figure is for. The steep climb at high AUROC survives.
    ax.set_yscale("log")
    ax.set_xlim(0.46, 1.005)
    ax.set_ylim(0.008, 0.75)
    ax.set_xticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    # Percent labels: at 1% prevalence a reader compares 1.52% with 4.35% far faster than
    # 0.0152 with 0.0435, and the axis is the place to spend that.
    ax.set_yticks([0.01, 0.015, 0.02, 0.05, 0.1, 0.2, 0.5])
    ax.set_yticklabels(["1.0%", "1.5%", "2%", "5%", "10%", "20%", "50%"])
    ax.minorticks_off()
    fig.tight_layout()
    return save(fig, "auroc_ppv", write, theme), {
        "table rows reproduced": len(table),
        "clinical threshold": round(ppv_clinical, 4),
        "AUROC it needs": round(auroc_clinical, 4),
        "model at measured AUROC": round(
            ppv_from_spec(spec_at_sensitivity(platform["auroc"])), 4),
        "measured": platform["ppv90"]}


def main():
    global C
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="reconcile only, write nothing")
    args = ap.parse_args()
    write = not args.check
    for name, fn in (("negtail", fig_negtail), ("labelnoise", fig_labelnoise),
                     ("auroc_ppv", fig_auroc_ppv)):
        for theme in ("light", "dark"):
            C = THEMES[theme]
            made, facts = fn(write, theme)
            if theme == "light":
                print("  %-11s reconciled %s" % (name, facts))
            for p in made:
                print("               wrote %s" % p.relative_to(ROOT))
    C = THEMES["light"]
    print("  three figures agree with the published numbers, in both themes.")


if __name__ == "__main__":
    main()
