"""Skladá obrázky 1 ks / 3 ks / 6 ks z fotky produktu (Danis) pre Temu."""
import json, os, sys, io, requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = "https://danistrade.sk"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
S = 1200

def load(path):
    if path.startswith("http"):
        r = requests.get(path, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, "white")
            bg.alpha_composite(im)
            im = bg
        im = im.convert("RGB")
        im.thumbnail((900, 900), Image.LANCZOS)
        return im
    u = f"{BASE}{path}?width=900&height=900&rmode=pad&format=png&bgcolor=white"
    r = requests.get(u, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    return im

def trim(im):
    """oreže biele okraje; z hornej/dolnej strany odstráni text či URL, ktorý sa dotýka produktu
    (erózia odstráni tenké písmená, ponechajú sa len veľké útvary = produkt)"""
    import numpy as np
    from scipy import ndimage as nd
    a = np.array(im.convert("RGB")).astype(int)
    m = (255 - a.min(axis=2)) > 12
    ys, xs = np.where(m)
    if len(ys) == 0:
        return im
    core = nd.binary_erosion(a.min(axis=2) < 225, structure=np.ones((3, 3)), iterations=2)
    lab, n = nd.label(core, structure=np.ones((3, 3)))
    if n:
        sizes = nd.sum(core, lab, range(1, n + 1))
        big = sizes.max()
        boxes = [sl for i, sl in enumerate(nd.find_objects(lab)) if sizes[i] >= 0.03 * big]
        ytop = min(sl[0].start for sl in boxes) - 2
        ybot = max(sl[0].stop for sl in boxes) + 0
        keep = np.zeros(m.shape, bool)
        keep[max(ytop, 0):ybot, :] = True
        m = m & keep
        ys, xs = np.where(m)
        if len(ys) == 0:
            return im
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

def fit(im, maxw, maxh):
    r = min(maxw / im.width, maxh / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)

def paste_product(canvas, prod, cx, bottom):
    """vloží produkt so stredom cx a spodnou hranou bottom; biele pozadie sa neprekrýva"""
    mask = prod.convert("L").point(lambda p: 255 if p < 246 else 0).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1))
    x = int(cx - prod.width / 2); y = int(bottom - prod.height)
    canvas.paste(prod, (x, y), mask)

def badge(canvas, text):
    d = ImageDraw.Draw(canvas)
    cx, cy, r = S - 125, 115, 90
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(230, 57, 70))
    f = ImageFont.truetype(FONT, 72)
    bb = d.textbbox((0, 0), text, font=f)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill="white")

def watermark(canvas, text="FRESMIO EU"):
    """jemný šikmý vodoznak opakovaný po celom obrázku"""
    f = ImageFont.truetype(FONT, 54)
    layer = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(0, S * 2, 230):
        for x in range(-200 + (y // 230 % 2) * 250, S * 2, 500):
            d.text((x, y), text, font=f, fill=(90, 90, 90, 38))
    layer = layer.rotate(30, resample=Image.BICUBIC)
    off = (S // 2, S // 2)
    layer = layer.crop((off[0], off[1], off[0] + S, off[1] + S))
    base = canvas.convert("RGBA")
    base.alpha_composite(layer)
    return base.convert("RGB")

def make(prod, n):
    c = Image.new("RGB", (S, S), "white")
    if n == 1:
        paste_product(c, fit(prod, 960, 960), S / 2, 1080)
    elif n == 3:
        back = fit(prod, 500, 600)
        front = fit(prod, 600, 680)
        paste_product(c, back, S / 2 - 270, 940)
        paste_product(c, back, S / 2 + 270, 940)
        paste_product(c, front, S / 2, 1110)
    elif n == 6:
        p = fit(prod, 360, 430)
        for bottom in (650, 1140):
            for i in range(3):
                paste_product(c, p, S / 2 + (i - 1) * 390, bottom)
    if n > 1:
        badge(c, f"{n} ks")
    return watermark(c)

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
