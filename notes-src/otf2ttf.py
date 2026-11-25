import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

def convert(src, dst):
    f = TTFont(src)
    order = f.getGlyphOrder()
    gs = f.getGlyphSet()
    glyf = newTable("glyf"); glyf.glyphOrder = order; glyf.glyphs = {}
    for name in order:
        pen = TTGlyphPen(gs)
        gs[name].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))
        glyf.glyphs[name] = pen.glyph()
    f["loca"] = newTable("loca"); f["glyf"] = glyf
    del f["CFF "]
    if "VORG" in f: del f["VORG"]
    m = newTable("maxp"); m.tableVersion = 0x00010000
    for k in ("maxZones",): setattr(m, k, 1)
    for k in ("maxTwilightPoints","maxStorage","maxFunctionDefs","maxInstructionDefs","maxStackElements","maxSizeOfInstructions","maxComponentElements"): setattr(m, k, 0)
    f["maxp"] = m
    p = f["post"]; p.formatType = 2.0; p.extraNames = []; p.mapping = {}; p.glyphOrder = order
    f.sfntVersion = "\000\001\000\000"
    f.save(dst)

os.makedirs(os.path.join(HERE, "fonts"), exist_ok=True)
for w in sys.argv[1:]:
    convert(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", os.path.join(HERE, "fonts", f"Inter-{w}.ttf"))
    print("ok", w)
