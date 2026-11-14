"""Skladá obrázky 1 ks / 3 ks / 6 ks z fotky produktu (Danis) pre Temu."""
import json, os, sys, io, requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = "https://danistrade.sk"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
S = 1200

def load(path):
    u = f"{BASE}{path}?width=900&height=900&rmode=pad&format=png&bgcolor=white"
    r = requests.get(u, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    return im

def trim(im):
    bg = Image.new("RGB", im.size, (255, 255, 255))
    from PIL import ImageChops
    diff = ImageChops.difference(im, bg).convert("L").point(lambda p: 255 if p > 12 else 0)
    box = diff.getbbox()
    return im.crop(box) if box else im

def fit(im, h):
    w = int(im.width * h / im.height)
    return im.resize((w, h), Image.LANCZOS)

def paste_product(canvas, prod, cx, bottom):
    """vloží produkt so stredom cx a spodnou hranou bottom; biele pozadie sa neprekrýva"""
    mask = prod.convert("L").point(lambda p: 255 if p < 246 else 0).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1))
    x = int(cx - prod.width / 2); y = int(bottom - prod.height)
    canvas.paste(prod, (x, y), mask)

def badge(canvas, text):
    d = ImageDraw.Draw(canvas)
    cx, cy, r = S - 170, 170, 125
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(230, 57, 70))
    f = ImageFont.truetype(FONT, 100)
    bb = d.textbbox((0, 0), text, font=f)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill="white")

def make(prod, n):
    c = Image.new("RGB", (S, S), "white")
    if n == 1:
        p = fit(prod, 940); paste_product(c, p, S / 2, 1070)
    elif n == 3:
        h = 760
        p = fit(prod, h)
        step = min(int(p.width * 0.78), 360)
        xs = [S / 2 - step, S / 2 + step, S / 2]
        for cx in xs[:2]:
            paste_product(c, fit(prod, int(h * 0.92)), cx, 1000)
        paste_product(c, p, xs[2], 1080)
    elif n == 6:
        h = 470
        p = fit(prod, h)
        step = min(int(p.width * 1.05), 380)
        for row, bottom in enumerate((600, 1110)):
            for i in range(3):
                paste_product(c, p, S / 2 + (i - 1) * step, bottom)
    if n > 1:
        badge(c, f"{n} ks")
    return c

def main():
    items = json.load(open("products.json"))
    os.makedirs("images", exist_ok=True)
    for ean, path in items.items():
        try:
            prod = trim(load(path))
        except Exception as e:
            print("CHYBA", ean, e); continue
        for n in (1, 3, 6):
            out = f"images/{ean}-{n}.jpg"
            make(prod, n).save(out, quality=90)
            print("OK", out)

if __name__ == "__main__":
    main()
