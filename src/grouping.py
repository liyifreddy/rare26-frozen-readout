# -*- coding: utf-8 -*-
"""Group near-duplicate images so that one examination cannot straddle a split.

The challenge filenames carry no patient identifier, but several images in the set are
different frames of the same examination. If those land on both sides of a
cross-validation split the resulting scores are optimistic. This script recovers
pseudo-patient groups from feature similarity and writes them to `work/groups.npy`,
which `fit_head.py` consumes.

Two constraints:

* No edge may cross a center. Images from different centers are different patients, so
  the constraint costs nothing. Without it, groups chain across centers.
* Neighbors must be mutual. Single-linkage takes the transitive closure, so A
  resembling B and B resembling C merges A with C even when A and C are unrelated.
  Requiring each image to rank the other inside its own top k breaks those chains.

Usage:
    python src/grouping.py
"""
import glob
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import timm
import torch
from PIL import Image
from scipy.sparse.csgraph import connected_components

DATA_GLOB = "data/RARE25-train-data/**/*.png"
OUT = Path("work/groups.npy")
WEIGHTS = os.environ.get(
    "RARE26_BACKBONE",
    "data/Gastronet-5M pretrained models/RN50_GastroNet-5M_DINOv1.pth")
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
THRESHOLD = 0.95
MUTUAL_K = 10


def embeddings(files):
    """Globally pooled layer4 features, which is enough to spot near-duplicates."""
    m = timm.create_model("resnet50", pretrained=False, num_classes=0,
                          features_only=True, out_indices=(4,))
    ck = torch.load(WEIGHTS, map_location="cpu", weights_only=False)
    m.load_state_dict({k.replace("backbone.", "").replace("module.", ""): v
                       for k, v in ck.items() if torch.is_tensor(v)}, strict=False)
    m = m.to(DEV).eval().half()

    def dec(f):
        im = Image.open(f).convert("RGB").resize((512, 512), Image.BILINEAR)
        a = np.asarray(im.resize((224, 224), Image.BILINEAR), np.float32)
        return (a / 255.0 - MEAN) / STD

    out = []
    with ThreadPoolExecutor(16) as ex, torch.no_grad():
        for i in range(0, len(files), 64):
            arr = np.stack(list(ex.map(dec, files[i:i + 64])))
            x = torch.from_numpy(arr).permute(0, 3, 1, 2).to(DEV).half()
            out.append(m(x)[0].mean((2, 3)).float().cpu().numpy())
    return np.concatenate(out)


def group(X, center, thr=THRESHOLD, mutual_k=MUTUAL_K):
    Xn = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    S = Xn @ Xn.T
    np.fill_diagonal(S, -1)

    same_center = center[:, None] == center[None, :]
    topk = np.argsort(-S, axis=1)[:, :mutual_k]
    in_topk = np.zeros_like(S, dtype=bool)
    in_topk[np.repeat(np.arange(len(S)), mutual_k), topk.ravel()] = True
    mutual = in_topk & in_topk.T

    adj = (S >= thr) & same_center & mutual
    n, lab = connected_components(sp.csr_matrix(adj), directed=False)
    return n, lab


def main():
    files = sorted(glob.glob(DATA_GLOB, recursive=True))
    if not files:
        raise SystemExit("No images found under %s" % DATA_GLOB)
    center = np.array([0 if "center_1" in f else 1 for f in files])
    label = np.array([1 if os.sep + "neo" + os.sep in f else 0 for f in files])

    X = embeddings(files)
    n, lab = group(X, center)
    sizes = np.bincount(lab)
    print("%d images -> %d groups; largest %d images, %d singletons"
          % (len(files), n, sizes.max(), int((sizes == 1).sum())))
    print("positives fall in %d groups (center_1 %d, center_2 %d)"
          % (len(set(lab[label == 1])),
             len(set(lab[(label == 1) & (center == 0)])),
             len(set(lab[(label == 1) & (center == 1)]))))

    crossing = [g for g in np.unique(lab) if len(set(center[lab == g])) > 1]
    assert not crossing, "a group crossed centers, which the constraint should prevent"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.save(OUT, lab)
    print("Wrote %s" % OUT)


if __name__ == "__main__":
    main()
