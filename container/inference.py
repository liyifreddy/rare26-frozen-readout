"""RARE26 submission container.

Pipeline:

  1. Read the stacked tiff or mha and return (N, H, W, 3) uint8.
     One case is one file; the platform treats each .tiff as a separate job.
  2. Resize to 512x512, then to 224x224. The platform delivers wide frames already
     squashed to square, verified against the field-of-view mask's second moments.
  3. Frozen ResNet50 (GastroNet-5M, DINOv1 self-supervised), layer4 features, with NO
     global average pooling: the 7x7x2048 spatial map is kept.
  4. Signed power transform, x -> sign(x) * |x|^0.5.
  5. Subtract the training mean and project onto the discriminant vector w, which was
     fitted in closed form as a shrinkage Gaussian discriminant over the 49 positions.
  6. Score every position, then take the highest 2% (the maximum on a 7x7 grid).
  7. Squash to (0, 1). The metric depends only on the ordering, so this step cannot
     change the score; it exists to make the output readable as a likelihood.

CPU only. See the README for measured timing and memory.

Comments and messages here were translated into English for publication. The code is
unchanged from the version that built the submitted container; check it with
`tools/check_ast_identical.py`.
"""
from pathlib import Path
from glob import glob
import json
import os

import numpy as np
import SimpleITK
import torch
import timm

INPUT_PATH = Path("/input")
OUTPUT_PATH = Path("/output")
RESOURCE_PATH = Path("resources")

# The backbone may live inside the image or be mounted by the platform under
# /opt/ml/model/. Both locations are searched.
MODEL_DIRS = [Path("/opt/ml/model"), Path("/opt/ml/models"), RESOURCE_PATH]

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)
SIDE = 224
SQUARE = 512


def find_file(name):
    for d in MODEL_DIRS:
        p = d / name
        if p.is_file():
            return p
    raise FileNotFoundError(f"{name} not found in {[str(d) for d in MODEL_DIRS]}")


def load_stack():
    """Read the stacked tiff or mha and return (N, H, W, 3) uint8."""
    loc = INPUT_PATH / "images/stacked-barretts-esophagus-endoscopy"
    files = sorted(glob(str(loc / "*.tif")) + glob(str(loc / "*.tiff"))
                   + glob(str(loc / "*.mha")))
    if not files:
        raise FileNotFoundError(f"no image under {loc}")
    arr = SimpleITK.GetArrayFromImage(SimpleITK.ReadImage(files[0]))
    arr = np.asarray(arr)
    if arr.ndim == 3:                      # a single grayscale or RGB frame
        arr = arr[None] if arr.shape[-1] == 3 else arr[..., None].repeat(3, -1)[None]
    if arr.shape[-1] == 1:
        arr = arr.repeat(3, -1)
    return arr.astype(np.uint8)


def preprocess(stack):
    """Numerically equivalent to the training path: 512x512, then 224x224.

    Training goes through PIL. Both stages are downscales, so both must anti-alias.
    """
    x = torch.from_numpy(stack).permute(0, 3, 1, 2).float() / 255.0
    # antialias=True is required. PIL.resize(BILINEAR) widens its filter kernel with
    # the scale factor when downscaling; F.interpolate defaults to antialias=False and
    # does not. At 512 -> 224 the two differ by 1.358/255 mean and 81/255 max without
    # it, against 0.258/255 and 1/255 with it. Omitting it applies the head to a
    # different feature distribution from the one it was fitted on.
    x = torch.nn.functional.interpolate(x, size=(SQUARE, SQUARE), mode="bilinear",
                                        align_corners=False, antialias=True)
    x = torch.nn.functional.interpolate(x, size=(SIDE, SIDE), mode="bilinear",
                                        align_corners=False, antialias=True)
    mean = torch.tensor(IMAGENET_MEAN).view(1, 3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(1, 3, 1, 1)
    return (x - mean) / std


def build_backbone():
    m = timm.create_model("resnet50", pretrained=False, num_classes=0,
                          features_only=True, out_indices=(4,))
    ck = torch.load(find_file("backbone.pth"), map_location="cpu", weights_only=False)
    sd = {k.replace("backbone.", "").replace("module.", ""): v
          for k, v in ck.items() if torch.is_tensor(v)}
    r = m.load_state_dict(sd, strict=False)
    missing = [k for k in r.missing_keys if not k.startswith(("fc.", "head."))]
    if missing:
        raise RuntimeError(f"backbone checkpoint is missing keys "
                           f"(timm version mismatch?): {missing[:5]}")
    return m.eval()


def run():
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "8")))
    torch.set_grad_enabled(False)

    # If adapting this for GPU, decide bf16 support from compute capability major >= 8,
    # not from torch.cuda.is_bf16_supported(): since PyTorch 2.4 that defaults to
    # including_emulation=True and returns True on Turing cards with no bf16 cores.
    print(f"[env] torch={torch.__version__} timm={timm.__version__} "
          f"numpy={np.__version__} threads={torch.get_num_threads()} "
          f"cuda={torch.cuda.is_available()}")

    head = np.load(find_file("head.npz"))
    w = torch.from_numpy(head["w"].astype(np.float32))
    mu = torch.from_numpy(head["mu"].astype(np.float32))
    center = float(head["center"])
    scale = float(head["scale"])
    topk = int(head["topk"])

    stack = load_stack()
    print(f"[in ] {stack.shape[0]} frames {stack.shape[1]}x{stack.shape[2]}")

    model = build_backbone()
    x = preprocess(stack)

    scores = []
    for i in range(0, len(x), 4):                       # small batches keep peak memory low
        f = model(x[i:i + 4])[0]                        # (b, 2048, 7, 7)
        f = f.permute(0, 2, 3, 1).reshape(f.shape[0], -1, f.shape[1])   # (b, 49, 2048)
        f = torch.sign(f) * torch.sqrt(torch.abs(f))    # signed power transform
        s = (f - mu) @ w                                # (b, 49)
        k = max(1, min(topk, s.shape[1]))
        s = torch.topk(s, k, dim=1).values.mean(1)      # highest 2% of positions
        scores.append(s)
    s = torch.cat(scores).numpy()

    probs = 1.0 / (1.0 + np.exp(-(s - center) / max(scale, 1e-6)))
    print(f"[out] {len(probs)} scores, range {probs.min():.4f}-{probs.max():.4f}")

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH / "stacked-neoplastic-lesion-likelihoods.json", "w") as f:
        f.write(json.dumps([float(p) for p in probs], indent=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
