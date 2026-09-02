# -*- coding: utf-8 -*-
"""Local replica of the RARE26 leaderboard metric: PPV at 90% recall.

An independent implementation, written to reproduce the behavior of
`evaluation_Grand-Challenge.py` from the official baselines repository rather than
copied from it. Three things are added that the official script does not have: an
optional random seed, a noise diagnostic, and self-tests. Use it to check our numbers;
the leaderboard runs the official script, not this one.

Two things to know:

* The official repository contains two implementations that do not agree.
  `metrics.py` reads the precision at the nearest available recall point, while
  `evaluation_Grand-Challenge.py` interpolates linearly. The leaderboard runs the
  interpolating one, which is what is reproduced here.
* The official bootstrap keeps every negative and resamples positives down to
  `n_negatives / 100`, so the metric is evaluated at roughly 1% prevalence. With a
  validation set of the size used here that leaves on the order of a dozen positives
  per round, which is why the metric has a large variance. `--demo` measures it.

Usage:
    python src/scorer.py --demo             self-test, needs no data
    python src/scorer.py --csv scores.csv   csv with `label` and `score` columns
"""
import argparse
import csv
import sys

import numpy as np

try:
    from sklearn.metrics import (roc_auc_score, average_precision_score,
                                 precision_recall_curve)
except ImportError:
    sys.exit("Missing dependency. Run: pip install scikit-learn numpy")


def ppv_at_recall(y_true, y_score, target_recall=0.9):
    """Precision at a target recall, by linear interpolation on the PR curve."""
    p, r, _ = precision_recall_curve(y_true, y_score)
    return float(np.interp(target_recall, r[::-1], p[::-1]))


def official_score(y_true, y_score, n_iterations=1000, imbalance_ratio=100, seed=None):
    """Bootstrap exactly as the official evaluator does.

    Every negative is kept; positives are resampled with replacement down to
    `n_negatives / imbalance_ratio`. The reported value is the median over
    `n_iterations` rounds. The official code sets no seed, so official results vary
    between runs; `seed` is for reproducible comparisons.
    """
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score, dtype=float)
    rng = np.random.default_rng(seed)

    neg = np.where(y_true == 0)[0]
    pos = np.where(y_true == 1)[0]
    if len(pos) == 0 or len(neg) == 0:
        sys.exit("Labels must contain both classes.")

    n_pos_sample = max(1, int(len(neg) / imbalance_ratio))

    boot = []
    for _ in range(n_iterations):
        idx = np.concatenate([neg, rng.choice(pos, size=n_pos_sample, replace=True)])
        yt, ys = y_true[idx], y_score[idx]
        boot.append((roc_auc_score(yt, ys),
                     average_precision_score(yt, ys),
                     ppv_at_recall(yt, ys)))
    boot = np.asarray(boot)

    return {
        "Score": float(np.median(boot[:, 2])),
        "PPV@90RECALL": float(np.median(boot[:, 2])),
        "PPV@90RECALL 95% CI Lower Bound": float(np.percentile(boot[:, 2], 2.5)),
        "PPV@90RECALL 95% CI Upper Bound": float(np.percentile(boot[:, 2], 97.5)),
        "AUROC": float(np.median(boot[:, 0])),
        "AUROC 95% CI Lower Bound": float(np.percentile(boot[:, 0], 2.5)),
        "AUROC 95% CI Upper Bound": float(np.percentile(boot[:, 0], 97.5)),
        "AUPRC": float(np.median(boot[:, 1])),
        "AUPRC 95% CI Lower Bound": float(np.percentile(boot[:, 1], 2.5)),
        "AUPRC 95% CI Upper Bound": float(np.percentile(boot[:, 1], 97.5)),
        "AUROC Full Dataset": float(roc_auc_score(y_true, y_score)),
        "AUPRC Full Dataset": float(average_precision_score(y_true, y_score)),
        "PPV@90RECALL Full Dataset": ppv_at_recall(y_true, y_score),
        "_diag_n_neg": int(len(neg)),
        "_diag_n_pos_unique": int(len(pos)),
        "_diag_n_pos_sampled_per_round": int(n_pos_sample),
    }


def report(res, title=""):
    print("\n===== %s =====" % title)
    print("PPV@90Recall (median over bootstrap rounds): %.4f" % res["PPV@90RECALL"])
    print("  95%% interval: %.4f to %.4f"
          % (res["PPV@90RECALL 95% CI Lower Bound"],
             res["PPV@90RECALL 95% CI Upper Bound"]))
    print("AUROC %.4f   AUPRC %.4f" % (res["AUROC"], res["AUPRC"]))
    print("Without resampling: PPV %.4f  AUROC %.4f  AUPRC %.4f"
          % (res["PPV@90RECALL Full Dataset"], res["AUROC Full Dataset"],
             res["AUPRC Full Dataset"]))
    print("[diagnostic] %d negatives kept; %d unique positives, of which %d are drawn "
          "with replacement each round"
          % (res["_diag_n_neg"], res["_diag_n_pos_unique"],
             res["_diag_n_pos_sampled_per_round"]))


def self_test():
    """Three properties of this metric."""
    rng = np.random.default_rng(0)
    n_neg, n_pos = 1400, 130
    y = np.r_[np.zeros(n_neg, int), np.ones(n_pos, int)]
    s = np.r_[rng.normal(0.0, 1.0, n_neg), rng.normal(1.6, 1.0, n_pos)]
    s = 1 / (1 + np.exp(-s))

    base = official_score(y, s, seed=1)
    report(base, "synthetic data")

    print("\n--- 1. The metric depends only on the ordering of scores ---")
    print("Any rank-preserving transform must leave it unchanged.")
    for name, t in [("sqrt", np.sqrt(s)),
                    ("cube", s ** 3),
                    ("temperature", 1 / (1 + np.exp(-(np.log(s / (1 - s)) / 2.5)))),
                    ("affine", 0.13 + 0.42 * s)]:
        r = official_score(y, t, seed=1)
        d = r["PPV@90RECALL"] - base["PPV@90RECALL"]
        flag = "unchanged" if abs(d) < 1e-9 else "CHANGED by %+.6f, investigate" % d
        print("  %-12s %.6f   %s" % (name, r["PPV@90RECALL"], flag))
    print("  Consequence: recalibration cannot move this metric.")

    print("\n--- 2. How noisy the metric is ---")
    print("Same scores, seed varied, 20 repeats.")
    v = np.array([official_score(y, s, n_iterations=1000, seed=k)["PPV@90RECALL"]
                  for k in range(20)])
    print("  median %.4f, min %.4f, max %.4f, range %.4f"
          % (np.median(v), v.min(), v.max(), v.max() - v.min()))
    print("  That range is the noise floor. An improvement smaller than it cannot be")
    print("  demonstrated from a single evaluation.")

    print("\n--- 3. Sensitivity compared with AUROC ---")
    for lbl, sep in [("weak", 0.8), ("medium", 1.6), ("strong", 2.6)]:
        ss = np.r_[rng.normal(0.0, 1.0, n_neg), rng.normal(sep, 1.0, n_pos)]
        ss = 1 / (1 + np.exp(-ss))
        r = official_score(y, ss, seed=1)
        print("  %-8s PPV@90R %.4f   AUROC %.4f" % (lbl, r["PPV@90RECALL"], r["AUROC"]))
    print("  AUROC moves gently where PPV@90R moves sharply, which is why model")
    print("  selection on AUROC alone is misleading for this task.")


def from_csv(path):
    y, s = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            y.append(int(float(row["label"])))
            s.append(float(row["score"]))
    return np.array(y), np.array(s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="run the self-test on synthetic data")
    ap.add_argument("--csv", help="csv with `label` and `score` columns")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    if a.demo or not a.csv:
        self_test()
    else:
        y, s = from_csv(a.csv)
        report(official_score(y, s, seed=a.seed), a.csv)
