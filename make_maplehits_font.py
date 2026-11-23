"""Builds MapleHits' digit font from Bowlby One (SIL Open Font License), for amounts the game hides (secret values
can't be split into digits, so the font itself carries the style): upright digits packed tight so the white rims
merge between them, each a little up or down. Renamed as the OFL asks of modified versions. Writes
MapleHitsDigits.ttf. Needs: py -m pip install fonttools. Run: py make_maplehits_font.py"""
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ADDON = Path(__file__).parent
SHEAR, GAP, BOB = 0, 0.025, 0.045  # lean (x per y; upright), space between digit fills (em), up/down (em)
NAME = "MapleHits Digits"

font = TTFont(ADDON / "BowlbyOne-Regular.ttf")
upm = font["head"].unitsPerEm
glyphs, glyf, hmtx = font.getGlyphSet(), font["glyf"], font["hmtx"]
cmap = font.getBestCmap()
new = {}
for d in "0123456789":
    name = cmap[ord(d)]
    dy = (BOB if int(d) % 2 == 0 else -BOB) * upm  # even digits up, odd down: they never line up
    bounds = BoundsPen(glyphs)
    glyphs[name].draw(TransformPen(bounds, (1, 0, SHEAR, 1, 0, dy)))
    x0, _, x1, _ = bounds.bounds
    pen = TTGlyphPen(glyphs)
    glyphs[name].draw(TransformPen(pen, (1, 0, SHEAR, 1, -x0 + GAP * upm / 2, dy)))  # ink starts at half the gap
    new[name] = (pen.glyph(), round(x1 - x0 + GAP * upm))
for name, (g, advance) in new.items():
    glyf[name] = g
    hmtx[name] = (advance, round(GAP * upm / 2))

for rec in font["name"].names:  # a new name: the OFL reserves "Bowlby" for the original
    if rec.nameID in (1, 16):
        rec.string = NAME
    elif rec.nameID in (3, 4):
        rec.string = NAME + " Regular"
    elif rec.nameID == 6:
        rec.string = NAME.replace(" ", "") + "-Regular"
out = ADDON / "MapleHitsDigits.ttf"
font.save(out)
print("ok", out.name, {cmap[ord(d)]: new[cmap[ord(d)]][1] for d in "01"})
