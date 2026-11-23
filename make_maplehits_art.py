"""Draws MapleHits' textures from the Bowlby One font (OFL), styled after MapleStory's damage numbers as seen on a
1080p stream (MapleStory Classic, measured frame by frame):
- each digit: upright, a vertical gradient (deep top to bright bottom), a thick white rim, a solid dark outline;
- hits: red-orange to yellow; crits: crimson to pink, with a white-yellow burst; hits on you and the mob's MISS:
  blue-violet to magenta; your MISS: the hit colors. The MISS letters lean right and bob.
Drawn at twice the size they show at, so they stay sharp. Writes art/*.tga (digits 0-9 in a 2048x128
strip of 128-pixel cells) and Art.lua (each digit's ink width and the ink height, as shares of a cell).
Run: py make_maplehits_art.py"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ADDON = Path(__file__).parent
FONT_FILE = str(ADDON / "BowlbyOne-Regular.ttf")
CELL = 128                         # pixels per digit cell (the addon shows them at about 60)
FONT = ImageFont.truetype(FONT_FILE, 72)
RIM, EDGE = 8, 6                   # white rim and dark outline widths, pixels
OUTLINE, WHITE = (0, 0, 0), (255, 255, 255)
STYLES = {  # top, middle, bottom of the fill: the stream's hues at full strength, deep top, bright bottom
    "hit": [(236, 20, 0), (255, 128, 0), (255, 240, 0)],
    "crit": [(226, 0, 40), (255, 28, 128), (255, 150, 236)],
    "taken": [(76, 16, 236), (178, 36, 255), (255, 84, 236)],
    "heal": [(0, 70, 230), (30, 170, 255), (176, 246, 255)],
}


def gradient(w, h, top, mid, bottom):
    col = Image.new("RGBA", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.5:
            a, b, u = top, mid, t / 0.5
        else:
            a, b, u = mid, bottom, (t - 0.5) / 0.5
        col.putpixel((0, y), tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3)) + (255,))
    return col.resize((w, h))


def piece(ch, colors, font=FONT, shear=0.0):
    """One glyph with outline, rim and gradient fill, cropped to its ink; shear leans it right."""
    l, t, r, b = font.getbbox(ch)
    pad = RIM + EDGE + 2
    w, h = r - l + 2 * pad, b - t + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x, y = pad - l, pad - t
    d.text((x, y), ch, font=font, fill=OUTLINE, stroke_width=RIM + EDGE, stroke_fill=OUTLINE)
    d.text((x, y), ch, font=font, fill=WHITE, stroke_width=RIM, stroke_fill=WHITE)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((x, y), ch, font=font, fill=255)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.paste(gradient(w, b - t, *colors), (0, pad))
    img.paste(layer, (0, 0), mask)
    if shear:
        extra = round(h * shear)
        img = img.transform((w + extra, h), Image.AFFINE, (1, shear, -extra, 0, 1, 0), Image.BICUBIC)
    return img.crop(img.getbbox())


def word(text, colors, size):
    """MISS: letters leaning right, the first a bit bigger, the others bobbing, each on top of the one before."""
    pieces = [piece(ch, colors, ImageFont.truetype(FONT_FILE, round(80 * (1.15 if i == 0 else 1))), 0.18)
              for i, ch in enumerate(text)]
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    total = sum(p.width for p in pieces) * 0.74
    x = (size[0] - total) / 2
    for i, p in enumerate(pieces):
        bob = 0 if i == 0 else (4 if i % 2 else -4)
        out.alpha_composite(p, (round(x), size[1] - 12 - p.height + bob))
        x += p.width * 0.74
    return out


def burst():
    """The crit flash: a blown-out white core, a soft yellow glow, short rays, the long ones reaching left."""
    w, h = 256, 192
    cx, cy = 168, 96
    shape = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(shape)
    for i in range(12):
        a = math.pi * 2 * i / 12 + 0.26
        length = 116 if math.cos(a) < -0.4 else 60
        d.polygon([(cx + 18 * math.cos(a + 1.5), cy + 18 * math.sin(a + 1.5)), (cx + length * math.cos(a),
                   cy + length * math.sin(a)), (cx + 18 * math.cos(a - 1.5), cy + 18 * math.sin(a - 1.5))], fill=255)
    d.ellipse((cx - 40, cy - 32, cx + 40, cy + 32), fill=255)
    glow = shape.filter(ImageFilter.GaussianBlur(10))
    alpha = shape.filter(ImageFilter.GaussianBlur(1.6))
    alpha = Image.composite(alpha, glow, alpha)  # sharp shape over its soft halo
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = min(1, math.hypot((x - cx) / 1.5, y - cy) / 68)
            px[x, y] = (255, round(255 - 25 * t), round(255 - 175 * t), 255)  # white core, yellow rays
    img.putalpha(alpha)
    return img


def main():
    art = ADDON / "art"
    art.mkdir(exist_ok=True)
    widths, ink = [], 0
    for name, colors in STYLES.items():
        strip = Image.new("RGBA", (CELL * 16, CELL), (0, 0, 0, 0))
        for n in range(10):
            g = piece(str(n), colors)
            assert g.width <= CELL and g.height <= CELL, (n, g.size)
            strip.alpha_composite(g, (n * CELL + (CELL - g.width) // 2, (CELL - g.height) // 2))
            if name == "hit":
                widths.append(g.width)
                ink = max(ink, g.height)
        strip.save(art / f"{name}.tga")
    word("MISS", STYLES["hit"], (CELL * 4, CELL)).save(art / "miss_hit.tga")
    word("MISS", STYLES["taken"], (CELL * 4, CELL)).save(art / "miss_taken.tga")
    burst().save(art / "burst.tga")
    (ADDON / "Art.lua").write_text(
        "-- generated by make_maplehits_art.py: each digit's ink width and the ink height, as shares of its cell\n"
        "local _, ns = ...\n"
        f"ns.WIDTH = {{{', '.join(f'{w / CELL:.3f}' for w in widths)}}}\n"
        f"ns.INK = {ink / CELL:.3f}\n", encoding="utf-8")
    print("ok", widths, ink)


if __name__ == "__main__":
    main()
