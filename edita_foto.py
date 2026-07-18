"""Converteix una foto en un RETRAT DE REI MEDIEVAL de manera còmica.

No fa servir IA: és tot composició + processament d'imatge (Pillow + numpy),
reproduïble i sense serveis externs. Manté la cara real (sense deformar) i hi
afegeix: acabat tipus pintura a l'oli, coll d'ermini, capa reial, corona daurada
i un marc ornamentat, sobre un fons de tapís.

Ús:
    python edita_foto.py            # assets/Pablo_original.jpg -> assets/Pablo.jpg
    python edita_foto.py Nom

Torna a executar genera_web.py després per incrustar la nova foto a la web.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ASSETS = Path(__file__).resolve().parent / "assets"
S = 440  # mida del llenç final

GOLD = (232, 190, 78)
GOLD_L = (255, 231, 150)
GOLD_D = (150, 110, 20)
ROBE = (120, 22, 40)       # granate reial
ROBE_D = (86, 12, 26)
TAPIS = (74, 20, 34)       # fons de tapís


def oli(img: Image.Image) -> Image.Image:
    """Acabat 'pintura a l'oli': colors vius, posteritzat suau i to càlid."""
    img = ImageEnhance.Color(img).enhance(1.35)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = img.filter(ImageFilter.SMOOTH_MORE)
    img = ImageOps.posterize(img, 5)
    img = img.filter(ImageFilter.MedianFilter(3))
    # to càlid subtil
    r, g, b = img.split()
    r = r.point(lambda v: min(255, int(v * 1.05 + 6)))
    b = b.point(lambda v: int(v * 0.95))
    return Image.merge("RGB", (r, g, b))


def cara_ovalada(src: Image.Image, w: int, h: int) -> Image.Image:
    """Retalla la cara en un òval amb vores difuminades (per fondre-la al fons)."""
    face = ImageOps.fit(src, (w, h), method=Image.LANCZOS, centering=(0.5, 0.42))
    face = oli(face)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([6, 6, w - 6, h - 6], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(9))
    face.putalpha(mask)
    return face


def fons_tapis(d: ImageDraw.ImageDraw):
    """Fons de tapís granate amb flors de lis daurades i vinyeta."""
    d.rectangle([0, 0, S, S], fill=TAPIS)
    # patró de rombes / flors de lis molt subtil
    step = 74
    for gy in range(0, S + step, step):
        for gx in range(0, S + step, step):
            ox = 0 if (gy // step) % 2 == 0 else step // 2
            cx, cy = gx + ox, gy
            d.polygon([(cx, cy - 9), (cx + 6, cy), (cx, cy + 9), (cx - 6, cy)],
                      fill=(96, 30, 46))
            d.ellipse([cx - 3, cy - 14, cx + 3, cy - 6], fill=(96, 30, 46))


def dibuixa_corona(d: ImageDraw.ImageDraw):
    """Corona daurada clàssica reposant sobre el cap."""
    left, right = int(S * 0.30), int(S * 0.70)
    span = right - left
    band_top = int(S * 0.165)
    band_bot = band_top + int(S * 0.055)
    tips_y = [0.10, 0.05, 0.08, 0.05, 0.10]
    xs = [left + span * f for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
    pts = [(left, band_top)]
    for i, x in enumerate(xs):
        pts.append((x, int(S * tips_y[i])))
        if i < len(xs) - 1:
            vx = (x + xs[i + 1]) / 2
            pts.append((vx, band_top - S * 0.012))
    pts.append((right, band_top))
    d.polygon(pts, fill=GOLD, outline=GOLD_D)
    d.rectangle([left, band_top, right, band_bot], fill=GOLD, outline=GOLD_D)
    d.line([(left, band_top + 2), (right, band_top + 2)], fill=GOLD_L, width=2)
    for i, x in enumerate(xs):
        ty = int(S * tips_y[i]); rr = S * 0.018
        d.ellipse([x - rr, ty - rr, x + rr, ty + rr], fill=GOLD_L, outline=GOLD_D)
    for fx, col in [(0.30, (210, 50, 70)), (0.5, (60, 120, 240)), (0.70, (60, 180, 120))]:
        jx = left + span * fx; by = (band_top + band_bot) / 2; rr = S * 0.02
        d.ellipse([jx - rr, by - rr, jx + rr, by + rr], fill=col, outline=GOLD_D)
        d.ellipse([jx - rr * 0.4, by - rr * 0.5, jx, by], fill=(255, 255, 255))


def dibuixa_capa_ermini(d: ImageDraw.ImageDraw):
    """Capa granate amb coll d'ermini blanc (amb taquetes) sobre les espatlles."""
    y = int(S * 0.66)
    # capa als dos costats, amb obertura en V al centre (coll)
    d.polygon([(0, y), (S, y), (S, S), (0, S)], fill=ROBE)
    d.polygon([(int(S * 0.5), y), (int(S * 0.62), S), (int(S * 0.38), S)], fill=ROBE_D)
    # coll d'ermini: dues masses blanques amb forma de pell
    for cx in (int(S * 0.33), int(S * 0.67)):
        d.ellipse([cx - int(S * 0.20), y - int(S * 0.06),
                   cx + int(S * 0.20), y + int(S * 0.14)], fill=(245, 245, 240))
    # cobreix el centre perquè el coll segueixi la V
    d.polygon([(int(S * 0.5), y - int(S * 0.02)),
               (int(S * 0.66), y + int(S * 0.16)),
               (int(S * 0.34), y + int(S * 0.16))], fill=ROBE)
    # taquetes d'ermini
    spots = [(0.24, 0.70), (0.31, 0.74), (0.20, 0.75), (0.69, 0.70),
             (0.76, 0.74), (0.80, 0.71), (0.28, 0.69), (0.72, 0.75)]
    for fx, fy in spots:
        sx, sy = int(S * fx), int(S * fy)
        d.ellipse([sx - 3, sy - 4, sx + 3, sy + 4], fill=(40, 30, 30))
        d.line([(sx, sy + 3), (sx, sy + 9)], fill=(40, 30, 30), width=2)
    # galó daurat vertical de la capa
    d.rectangle([int(S * 0.47), y, int(S * 0.53), S], fill=GOLD)
    d.line([(int(S * 0.5), y), (int(S * 0.5), S)], fill=GOLD_D, width=1)


def marc(d: ImageDraw.ImageDraw):
    """Marc daurat ornamentat amb caironets a les cantonades."""
    d.rectangle([0, 0, S - 1, S - 1], outline=GOLD_D, width=3)
    for off, col in [(4, GOLD), (11, GOLD_L), (18, GOLD_D)]:
        d.rectangle([off, off, S - 1 - off, S - 1 - off], outline=col, width=2)
    for cx, cy in [(14, 14), (S - 14, 14), (14, S - 14), (S - 14, S - 14)]:
        d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=GOLD, outline=GOLD_D)
        d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(210, 50, 70))


def vinyeta(img: Image.Image) -> Image.Image:
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([-S * 0.15, -S * 0.15, S * 1.15, S * 1.15], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(60))
    dark = ImageEnhance.Brightness(img).enhance(0.55)
    return Image.composite(img, dark, mask)


def edita(nom: str = "Pablo") -> Path:
    src_path = ASSETS / f"{nom}_original.jpg"
    if not src_path.exists():
        src_path = ASSETS / f"{nom}.jpg"
    src = Image.open(src_path).convert("RGB")

    canvas = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(canvas)
    fons_tapis(d)

    # cara real, centrada a la part superior
    fw, fh = int(S * 0.52), int(S * 0.60)
    face = cara_ovalada(src, fw, fh)
    canvas.paste(face, ((S - fw) // 2, int(S * 0.11)), face)

    canvas = vinyeta(canvas)
    d = ImageDraw.Draw(canvas)
    dibuixa_capa_ermini(d)
    dibuixa_corona(d)
    marc(d)

    dest = ASSETS / f"{nom}.jpg"
    canvas.save(dest, "JPEG", quality=90)
    print(f"Retrat de rei generat: {dest}")
    return dest


if __name__ == "__main__":
    edita(sys.argv[1] if len(sys.argv) > 1 else "Pablo")
