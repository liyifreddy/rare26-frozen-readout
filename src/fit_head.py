# -*- coding: utf-8 -*-
"""Fit the classification head and export it as `head.npz` (about 16 KB).

This is the training code referred to in the method report. No layer of the backbone
is trained; the only learned parameters are one discriminant vector and one mean
vector.

Configuration:
    input      224x224, obtained by first squashing to 512x512
               (the platform delivers square images, so training follows the same path)
    backbone   RN50 pretrained with DINOv1 on GastroNet-5M, frozen
    features   layer4 spatial map, 7x7x2048, with NO global average pooling
    transform  signed power transform, x -> sign(x) * |x|^0.5
    fit        the 49 positions are treated as samples for the within-class scatter;
               closed-form shrinkage GDA, shrinking toward (tr S / d) * I
    lambda     chosen by 8 repeated grouped cross-validation runs on pAUC(85-95)
    pooling    score every position, then take the top 2% (the maximum on a 7x7 grid)

The exported file holds only (w, mu, two calibration constants). Backbone weights are
NOT included; they are obtained separately from the provider (see README).

Prerequisites:
    - the challenge training images under `data/RARE25-train-data/`
    - the backbone checkpoint (see README for how to obtain it)
    - patient groups from `grouping.py`, written to `work/groups.npy`

Usage:
    python src/fit_head.py
"""
import glob
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import timm
import torch
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedGroupKFold

OUT = Path("work/pack")
WEIGHTS = os.environ.get(
    "RARE26_BACKBONE",
    "data/Gastronet-5M pretrained models/RN50_GastroNet-5M_DINOv1.pth")
DATA_GLOB = "data/RARE25-train-data/**/*.png"
GROUPS = "work/groups.npy"

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)
LAMBDAS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
K, C = 49, 2048          # positions per image, feature channels
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def load_index():
    files = sorted(glob.glob(DATA_GLOB, recursive=True))
    if not files:
        raise SystemExit("No images found under %s" % DATA_GLOB)
    center = np.array([0 if "center_1" in f else 1 for f in files])
    label = np.array([1 if os.sep + "neo" + os.sep in f else 0 for f in files])
    groups = np.load(GROUPS)
    return files, center, label, groups


def preprocess(im):
    """Must stay numerically equivalent to `preprocess` in container/inference.py.

    Not identical: training resizes through PIL, the container through
    torch.nn.functional.interpolate with antialias=True, because the container has no
    PIL dependency in the hot path. The two agree to 0.258/255 mean and 1/255 maximum
    absolute difference at 512 -> 224, measured and recorded in `t7_train_serve.json`.
    Without antialias=True the same comparison is 1.358/255 and 81/255, which is a
    different feature distribution from the one the head was fitted on; that is the
    whole reason the flag is there.

    The platform supplies images already squashed to square, so the first resize is
    usually the identity there; it is applied here so that training and inference
    follow the same path.
    """
    im = im.convert("RGB").resize((512, 512), Image.BILINEAR)
    a = np.asarray(im.resize((224, 224), Image.BILINEAR), dtype=np.float32)
    return (a / 255.0 - MEAN) / STD


def backbone():
    m = timm.create_model("resnet50", pretrained=False, num_classes=0,
                          features_only=True, out_indices=(4,))
    ck = torch.load(WEIGHTS, map_location="cpu", weights_only=False)
    r = m.load_state_dict({k.replace("backbone.", "").replace("module.", ""): v
                           for k, v in ck.items() if torch.is_tensor(v)}, strict=False)
    miss = [k for k in r.missing_keys if not k.startswith(("fc.", "head."))]
    assert not miss, "checkpoint is missing keys: %s" % miss[:5]
    return m.to(DEV).eval().half()


def features(m, files, idx):
    out = []
    with ThreadPoolExecutor(16) as ex, torch.no_grad():
        for i in range(0, len(idx), 64):
            sub = [files[j] for j in idx[i:i + 64]]
            arr = np.stack(list(ex.map(lambda f: preprocess(Image.open(f)), sub)))
            x = torch.from_numpy(arr).permute(0, 3, 1, 2).to(DEV).half()
            out.append(m(x)[0].permute(0, 2, 3, 1)
                       .reshape(len(sub), K, C).float().cpu().numpy())
    return np.concatenate(out)


def _tukey(P):
    return np.sign(P) * np.abs(P) ** 0.5


def fit(P, idx, label, lam):
    """Closed-form shrinkage Gaussian discriminant over the 49 positions."""
    A = _tukey(P[idx]).reshape(-1, C)
    mu = A.mean(0, keepdims=True)
    A = A - mu
    yy = np.repeat(label[idx], K)
    S = (A.T.astype(np.float64) @ A.astype(np.float64)) / (len(A) - 1)
    tau = np.trace(S) / C
    d = A[yy == 1].mean(0).astype(np.float64) - A[yy == 0].mean(0).astype(np.float64)
    w = np.linalg.solve((1 - lam) * S + lam * np.eye(C) * tau, d)
    return w, mu.astype(np.float64).ravel()


def score(P, idx, w, mu):
    B = _tukey(P[idx]).reshape(-1, C).astype(np.float64) - mu
    s = (B @ w).reshape(len(idx), K)
    k = max(1, K // 50)                       # top 2%
    return np.sort(s, 1)[:, -k:].mean(1)


def ppv_at_90(y, s):
    o = np.argsort(-s)
    tp = np.cumsum(y[o])
    prec = tp / np.arange(1, len(s) + 1)
    rec = tp / tp[-1]
    return float(np.interp(0.9, rec, prec))


def partial_auc(y, s, lo=0.85, hi=0.95):
    """Specificity averaged over sensitivity in [lo, hi], normalized to [0, 1].

    Lambda is selected on this rather than on PPV@90R, which is set by a handful of
    positives and too noisy to select on, or on AUROC, which is dominated by the easy
    region the operating point never visits.
    """
    fpr, tpr, _ = roc_curve(y, s)
    grid = np.linspace(lo, hi, 21)
    return float(np.trapezoid(np.interp(grid, tpr, 1 - fpr), grid) / (hi - lo))


def _fold_scores(P, label, tr, te, lams):
    """One fold: form the scatter once, eigendecompose once, solve every lambda."""
    A = _tukey(P[tr]).reshape(-1, C)
    mu = A.mean(0, keepdims=True)
    A = A - mu
    yy = np.repeat(label[tr], K)
    At = torch.tensor(A, dtype=torch.float32, device=DEV)
    # accumulate in fp32 and store in fp64: consumer GPUs run fp64 at a small fraction
    # of fp32 throughput, but the eigendecomposition needs the wider type
    S = (At.T @ At).double() / (len(A) - 1)
    tau = torch.trace(S) / C
    e, V = torch.linalg.eigh(S)
    e = e.clamp(min=0)
    Vd = V.T @ torch.tensor(A[yy == 1].mean(0) - A[yy == 0].mean(0),
                            dtype=torch.float64, device=DEV)
    B = _tukey(P[te]).reshape(-1, C) - mu
    BV = (torch.tensor(B, dtype=torch.float32, device=DEV) @ V.float()).double()
    k = max(1, K // 50)
    out = {}
    for l in lams:
        s = (BV @ (Vd / ((1 - l) * e + l * tau))).cpu().numpy().reshape(len(te), K)
        out[l] = np.sort(s, 1)[:, -k:].mean(1)
    del At, S, e, V, Vd, BV
    if DEV == "cuda":
        torch.cuda.empty_cache()
    return out


def pick_lambda(P, idx, label, groups, n_rep=8):
    curves = []
    for seed in range(n_rep):
        oof = {l: np.zeros(len(idx)) for l in LAMBDAS}
        for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=seed).split(
                np.zeros(len(idx)), label[idx], groups[idx]):
            for l, s in _fold_scores(P, label, idx[a], idx[b], LAMBDAS).items():
                oof[l][b] = s
        curves.append([partial_auc(label[idx], oof[l]) for l in LAMBDAS])
        print("    repeat %d/%d: best lambda this run = %.2f"
              % (seed + 1, n_rep, LAMBDAS[int(np.argmax(curves[-1]))]), flush=True)
    mean = np.mean(curves, 0)
    return LAMBDAS[int(np.argmax(mean))], mean


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files, center, label, groups = load_index()
    print("%d images (center_1 %d / center_2 %d), %d positive"
          % (len(files), int((center == 0).sum()), int((center == 1).sum()),
             int(label.sum())))

    m = backbone()
    print("Extracting layer4 spatial maps with the inference preprocessing ...", flush=True)
    P = features(m, files, np.arange(len(files)))
    print("  %s" % (P.shape,))

    print("\nSelecting lambda (8 repeated grouped CV runs on pAUC(85-95)):", flush=True)
    idx = np.arange(len(files))
    lam, curve = pick_lambda(P, idx, label, groups)
    print("  -> lambda = %.2f" % lam)
    print("  pAUC curve: " + "  ".join("%.2f:%.4f" % (l, v)
                                       for l, v in zip(LAMBDAS, curve)))

    print("\nFitting the final head on all images ...", flush=True)
    w, mu = fit(P, idx, label, lam)

    # Calibration maps scores into (0, 1). The metric depends only on ordering, so this
    # cannot change the score. The center is the training-set quantile matching the
    # negative rate, which puts ordinary images below 0.5.
    s = score(P, idx, w, mu)
    center_q = float(np.percentile(s, 100 * (1 - label.mean())))
    iqr = float(np.percentile(s, 75) - np.percentile(s, 25))
    print("  training scores: q%.1f = %.3f, IQR %.3f, range %.2f to %.2f"
          % (100 * (1 - label.mean()), center_q, iqr, s.min(), s.max()))

    np.savez(OUT / "head.npz", w=w.astype(np.float32), mu=mu.astype(np.float32),
             center=np.float32(center_q), scale=np.float32(max(iqr, 1e-6)),
             lam=np.float32(lam), topk=np.int32(max(1, K // 50)))
    print("\nWrote %s (%.1f KiB)"
          % (OUT / "head.npz", (OUT / "head.npz").stat().st_size / 1024))

    json.dump({"lambda": lam,
               "pauc_curve": dict(zip(map(str, LAMBDAS), map(float, curve))),
               "n_train": len(files), "n_pos": int(label.sum()),
               "score_center": center_q, "score_iqr": iqr,
               "auroc_train": float(roc_auc_score(label, s)),
               "ppv90_train": ppv_at_90(label, s)},
              open(OUT / "head_meta.json", "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    main()
