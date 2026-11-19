"""Quantitative silhouette comparison against the orthographic PencilProto views.

    python3 scripts/compare_silhouettes.py <reference_dir> <mask_dir> <private_out_dir>

Reference images are third-party and are NOT stored in this repo. Overlays that contain
reference pixels are written to <private_out_dir> (keep it out of version control);
only the numeric metrics are written to validation/silhouette_metrics.json.
"""
import json, os, sys
import numpy as np
from PIL import Image

ref_dir, mask_dir, priv = sys.argv[1:4]
os.makedirs(priv, exist_ok=True)
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def fill_holes(m):
    """everything not 4-connected to the image border through background is object."""
    from collections import deque
    bg = np.zeros_like(m); h, w = m.shape; q = deque()
    for y in range(h):
        for x in (0, w - 1):
            if not m[y, x] and not bg[y, x]: bg[y, x] = True; q.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if not m[y, x] and not bg[y, x]: bg[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and not m[yy, xx] and not bg[yy, xx]:
                bg[yy, xx] = True; q.append((yy, xx))
    return ~bg

def ref_mask(path):
    im = np.asarray(Image.open(path).convert("RGBA")).astype(int)
    m = (im[..., 3] > 128) & (im[..., :3].min(axis=2) < 235)
    small = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((m.shape[1] // 4, m.shape[0] // 4))) > 127
    small = fill_holes(small)
    return np.asarray(Image.fromarray(small.astype(np.uint8) * 255).resize((m.shape[1], m.shape[0]))) > 127

def our_mask(path):
    return np.asarray(Image.open(path).convert("RGBA"))[..., 3] > 128

def norm(mask, Hpx=800, anchor="left"):
    ys, xs = np.nonzero(mask)
    crop = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    W = round(w * Hpx / h)
    return np.asarray(Image.fromarray(crop.astype(np.uint8) * 255).resize((W, Hpx), Image.BILINEAR)) > 127

def compare(name, refm, ourm, flip=False):
    a = norm(refm); b = norm(ourm)
    if flip: b = b[:, ::-1]
    W = max(a.shape[1], b.shape[1])
    A = np.zeros((800, W), bool); B = np.zeros((800, W), bool)
    A[:, :a.shape[1]] = a; B[:, :b.shape[1]] = b
    iou = (A & B).sum() / (A | B).sum()
    # per-row extents (fraction of height)
    dev = []
    for r in range(0, 800, 4):
        ra, rb = np.nonzero(A[r])[0], np.nonzero(B[r])[0]
        if len(ra) and len(rb):
            dev.append(max(abs(ra.min() - rb.min()), abs(ra.max() - rb.max())) / 800)
    dev = np.array(dev)
    over = np.zeros((800, W, 3), np.uint8) + 255
    over[A & ~B] = (220, 60, 60)      # reference only  (red)
    over[B & ~A] = (40, 110, 230)     # model only      (blue)
    over[A & B] = (170, 170, 170)     # agreement       (grey)
    Image.fromarray(over).save(os.path.join(priv, f"overlay_{name}.png"))
    return {"iou": round(float(iou), 4), "aspect_ref": round(a.shape[1] / 800, 4), "aspect_model": round(b.shape[1] / 800, 4),
            "row_extent_dev_mean_H": round(float(dev.mean()), 4), "row_extent_dev_p95_H": round(float(np.percentile(dev, 95)), 4)}

res = {
    "right_side_vs_img18": compare("right", ref_mask(os.path.join(ref_dir, "img18_e1f51e26.png")), our_mask(os.path.join(mask_dir, "mask_right.png"))),
    "front_vs_img09": compare("front", ref_mask(os.path.join(ref_dir, "img09_514a35c9.png")), our_mask(os.path.join(mask_dir, "mask_front.png"))),
}
res["_note"] = "Silhouettes normalised to equal height. IoU 1.0 = identical outline. Deviations in units of overall height H."
out = os.path.join(ROOT, "validation", "silhouette_metrics.json")
json.dump(res, open(out, "w"), indent=2)
print(json.dumps(res, indent=2))
