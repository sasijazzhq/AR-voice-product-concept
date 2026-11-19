"""Generate all textures for the Soundbox asset (run with system Python 3 + Pillow + segno).

    python3 scripts/make_textures.py

Outputs into ../textures/:
  qr_sticker_2048.png   front sticker (hero)
  qr_sticker_1024.png   front sticker (AR)
  button_icons_512.png  4-cell atlas for Top_Controls (background colour baked per cell)
  lcd_screen_512.png    monochrome LCD content for Status_Display

The QR code encodes a plain-text DEMO string. It is NOT a UPI URI (no "upi://pay",
no VPA / payee address) and cannot initiate a payment. The sticker reproduces the
layout and colour language of the reference (cyan/navy frame, white card) using
plain typeset text; no official logo artwork is reproduced.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
import segno

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "textures"))
P = json.load(open(os.path.join(HERE, "params.json")))
os.makedirs(OUT, exist_ok=True)

QR_PAYLOAD = "PAYTM REALITY LAB DEMO - NOT A PAYMENT CODE"
assert "upi:" not in QR_PAYLOAD.lower() and "@" not in QR_PAYLOAD

FONT_DIR = "/usr/share/fonts/opentype/inter"
def font(name, px):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(px))

def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

C = {k: hexrgb(v) for k, v in P["colours_srgb"].items()}
NAVY, CYAN = C["sticker_navy"], C["sticker_cyan"]
WHITE = (250, 250, 250)


def sticker(px_per_mm=40):
    """Draw the sticker in true mm proportions at high resolution."""
    s = P["sticker"]
    W, H = s["width"], s["height"]
    k = px_per_mm
    img = Image.new("RGB", (round(W * k), round(H * k)), WHITE)
    d = ImageDraw.Draw(img)
    # two-tone frame (the sticker outline itself is rounded by geometry; fill to edge)
    split = round(H * s["cyan_fraction"] * k)
    d.rectangle([0, 0, img.width, split], fill=CYAN)
    d.rectangle([0, split, img.width, img.height], fill=NAVY)
    b = s["border"] * k
    d.rounded_rectangle([b, b, img.width - b, img.height - b], radius=s["card_corner_radius"] * k, fill=WHITE)
    cx = img.width / 2
    sy = H / 87.8  # layout was authored for an 87.8 mm tall sticker; scale vertically

    def text_c(y_mm, txt, f, fill):
        bb = d.textbbox((0, 0), txt, font=f)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], y_mm * k - bb[1]), txt, font=f, fill=fill)

    # header: plain typeset brand name + "Accepted Here"
    text_c(7.0 * sy, "Paytm", font("InterDisplay-Bold.otf", 10.5 * k), NAVY)
    text_c(18.6 * sy, "Accepted Here", font("Inter-SemiBold.otf", 4.3 * k), (40, 40, 44))
    # QR (ECC H so the centre DEMO badge does not break decoding)
    qr = segno.make(QR_PAYLOAD, error="h", micro=False)
    n = qr.symbol_size(border=0)[0]
    qr_mm = 43.0
    mod = qr_mm * k / n
    x0 = cx - qr_mm * k / 2
    y0 = 25.0 * sy * k
    for r, row in enumerate(qr.matrix):
        for c, v in enumerate(row):
            if v:
                d.rectangle([x0 + c * mod, y0 + r * mod, x0 + (c + 1) * mod - 1, y0 + (r + 1) * mod - 1], fill=(20, 20, 22))
    # centre badge
    bw, bh = 13 * k, 6.4 * k
    by = y0 + qr_mm * k / 2
    d.rounded_rectangle([cx - bw / 2, by - bh / 2, cx + bw / 2, by + bh / 2], radius=1.2 * k, fill=WHITE,
                        outline=NAVY, width=max(2, int(0.35 * k)))
    f = font("Inter-Bold.otf", 3.6 * k)
    bb = d.textbbox((0, 0), "DEMO", font=f)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], by - (bb[3] - bb[1]) / 2 - bb[1]), "DEMO", font=f, fill=NAVY)
    # footer: unmistakable non-payable label
    text_c(70.6 * sy, "SAMPLE QR • NOT PAYABLE", font("Inter-Bold.otf", 3.7 * k), (200, 30, 60))
    text_c(76.0 * sy, "Illustrative 3D asset – no payment destination", font("Inter-Medium.otf", 2.1 * k), (90, 90, 96))
    return img, qr


def button_atlas(size=512):
    """4 cells side by side in a size x size/4 strip, padded to square for GPU friendliness."""
    cell = size // 4
    img = Image.new("RGB", (size, size), C["cobalt_body"])
    d = ImageDraw.Draw(img)
    bgs = [C["cobalt_body"], C["cobalt_body"], C["cobalt_body"], C["button_cyan"]]
    for i, bg in enumerate(bgs):
        x0 = i * cell
        d.rectangle([x0, 0, x0 + cell - 1, size - 1], fill=bg)
        cx, cy = x0 + cell / 2, cell / 2
        w = max(3, cell // 18)
        col = (235, 240, 248)
        if i == 0:   # volume up
            d.line([cx - cell * .18, cy, cx + cell * .18, cy], fill=col, width=w)
            d.line([cx, cy - cell * .18, cx, cy + cell * .18], fill=col, width=w)
        elif i == 1:  # volume down
            d.line([cx - cell * .18, cy, cx + cell * .18, cy], fill=col, width=w)
        elif i == 2:  # repeat last transaction (circular arrow)
            r = cell * .17
            d.arc([cx - r, cy - r, cx + r, cy + r], 40, 330, fill=col, width=w)
            d.polygon([(cx + r * .95, cy - r * .55), (cx + r * .95 + cell * .07, cy - r * .1),
                       (cx + r * .45, cy - r * .05)], fill=col)
        else:  # power
            r = cell * .17
            d.arc([cx - r, cy - r, cx + r, cy + r], 300, 240, fill=col, width=w)
            d.line([cx, cy - r * 1.25, cx, cy - r * .1], fill=col, width=w)
    return img


def lcd(w=512, h=192):
    bg = (176, 190, 172)
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    ink = (34, 42, 36)
    for i in range(4):  # signal bars
        bh = 14 + i * 9
        d.rectangle([14 + i * 12, 50 - bh, 22 + i * 12, 50], fill=ink)
    d.text((70, 14), "4G", font=font("Inter-Bold.otf", 30), fill=ink)
    d.rectangle([w - 74, 18, w - 22, 44], outline=ink, width=3)  # battery
    d.rectangle([w - 22, 25, w - 16, 37], fill=ink)
    d.rectangle([w - 70, 22, w - 36, 40], fill=ink)
    d.text((18, 72), "DEMO  ₹ 0.00", font=font("Inter-Bold.otf", 58), fill=ink)
    d.text((20, 148), "SIMULATED \u2013 NO MONEY MOVED", font=font("Inter-SemiBold.otf", 24), fill=ink)
    # light plastic window frame; the LCD slab sides sample this frame colour
    out = Image.new("RGB", (w + 48, h + 48), (226, 229, 232))
    out.paste(img, (24, 24))
    return out.resize((512, 256), Image.LANCZOS)


if __name__ == "__main__":
    img, qr = sticker()
    for size in (2048, 1024):
        img.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"qr_sticker_{size}.png"), optimize=True)
    button_atlas().save(os.path.join(OUT, "button_icons_512.png"), optimize=True)
    lcd().save(os.path.join(OUT, "lcd_screen_512.png"), optimize=True)
    info = {"qr_payload": QR_PAYLOAD, "qr_version": qr.version, "qr_error": qr.error,
            "qr_modules": qr.symbol_size(border=0)[0], "qr_mm": 43.0}
    json.dump(info, open(os.path.join(OUT, "qr_info.json"), "w"), indent=2)
    print(info)
