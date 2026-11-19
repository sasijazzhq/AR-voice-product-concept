"""Contact sheet of the six renders (committed) + reference side-by-sides (PRIVATE, never committed)
+ QR decode check on the final renders.

    python3 scripts/make_sheets.py [<reference_dir> <private_out_dir>]
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
R = os.path.join(ROOT, "renders")
F = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 28)
views = ["front", "left", "right", "rear", "top", "threequarter"]

sheet = Image.new("RGB", (3 * 800, 2 * 640), "white")
d = ImageDraw.Draw(sheet)
for i, v in enumerate(views):
    im = Image.open(os.path.join(R, f"{v}.png")).convert("RGB").resize((800, 600), Image.LANCZOS)
    x, y = (i % 3) * 800, (i // 3) * 640
    sheet.paste(im, (x, y + 40)); d.text((x + 16, y + 6), v.upper(), font=F, fill=(40, 40, 50))
sheet.save(os.path.join(R, "contact_sheet.jpg"), quality=90)

# QR decode on final renders
try:
    import cv2
    res = {}
    for f in ["textures/qr_sticker_2048.png", "textures/qr_sticker_1024.png", "renders/front.png", "renders/threequarter.png", "renders/hero.png"]:
        im = cv2.imread(os.path.join(ROOT, f))
        txt = cv2.QRCodeDetector().detectAndDecode(im)[0]
        res[f] = txt or None
    res["_expected"] = "PAYTM REALITY LAB DEMO - NOT A PAYMENT CODE"
    res["_is_upi_uri"] = any(t and t.lower().startswith("upi:") for t in res.values() if isinstance(t, str))
    json.dump(res, open(os.path.join(ROOT, "validation", "qr_decode.json"), "w"), indent=2)
    print(json.dumps(res, indent=2))
except ImportError:
    print("opencv not installed; skipping QR decode check")

if len(sys.argv) >= 3:   # private reference comparisons (third-party pixels -> never commit)
    ref, priv = sys.argv[1], sys.argv[2]
    os.makedirs(priv, exist_ok=True)
    pairs = {
        "front": ("img09_514a35c9.png", None),
        "right": ("img18_e1f51e26.png", None),
        "threequarter": ("img00_0bd7aa37.png", (150, 250, 1250, 1100)),
        "rear": ("img00_0bd7aa37.png", (1250, 330, 1900, 1050)),
        "left": ("img17_dd661387.jpg", (2050, 500, 3450, 1700)),
        "top": ("img04_27c8f655.jpg", (0, 0, 2560, 1440)),
    }
    for v, (f, crop) in pairs.items():
        a = Image.open(os.path.join(ref, f)).convert("RGB")
        if crop: a = a.crop(crop)
        b = Image.open(os.path.join(R, f"{v}.png")).convert("RGB")
        a.thumbnail((900, 700)); b.thumbnail((900, 700))
        c = Image.new("RGB", (1820, 760), "white"); dd = ImageDraw.Draw(c)
        c.paste(a, (0, 50)); c.paste(b, (920, 50))
        dd.text((10, 8), f"REFERENCE ({f}) — third-party, analysis only", font=F, fill=(160, 30, 30))
        dd.text((930, 8), f"MODEL render: {v}", font=F, fill=(30, 60, 160))
        c.save(os.path.join(priv, f"compare_{v}.jpg"), quality=88)
    print("private comparisons ->", priv)
