"""Build web fonts for the kiwano Ghost theme.

1. etl16.woff2: ETL 8x16 Latin-1 + Latin-2 bitmaps, traced into pixel outlines.
2. unifont-*.woff2: Unifont split into Unicode-range chunks, so browsers only
   download the chunks a page needs.

Usage: python3 build_fonts.py <lt1-16-etl.bdf> <lt2-16-etl.bdf> <unifont.otf> <outdir>
Prints the @font-face CSS to stdout.
"""
import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

PX = 4          # font units per pixel; matches Unifont (upem 64 = 16px)
UPEM = 64
ASCENT, DESCENT = 14, 2   # pixels, same in ETL and Unifont


def read_bdf(path):
    """Return {encoding: (width_px, bbx, rows)} for every glyph."""
    glyphs, cur, bitmap = {}, None, None
    for line in Path(path).read_text(encoding='latin-1').splitlines():
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        if key == 'STARTCHAR':
            cur = {}
        elif key == 'ENCODING':
            cur['enc'] = int(parts[1])
        elif key == 'DWIDTH':
            cur['dw'] = int(parts[1])
        elif key == 'BBX':
            cur['bbx'] = tuple(int(p) for p in parts[1:5])
        elif key == 'BITMAP':
            bitmap = []
        elif key == 'ENDCHAR':
            cur['rows'] = bitmap
            glyphs[cur['enc']] = cur
            cur = bitmap = None
        elif bitmap is not None:
            bitmap.append(int(key, 16))
    return glyphs


def pixels(g):
    """Set of (x, y) pixels with y measured up from the baseline."""
    w, h, xoff, yoff = g['bbx']
    nbits = ((w + 7) // 8) * 8
    out = set()
    for r, bits in enumerate(g['rows']):
        y = yoff + h - 1 - r
        for c in range(w):
            if bits & (1 << (nbits - 1 - c)):
                out.add((xoff + c, y))
    return out


def trace(px):
    """Trace the union of unit squares into clockwise outer contours."""
    edges = {}
    for x, y in px:
        # clockwise square (y up): left up, top right, right down, bottom left
        for a, b in (((x, y), (x, y + 1)), ((x, y + 1), (x + 1, y + 1)),
                     ((x + 1, y + 1), (x + 1, y)), ((x + 1, y), (x, y))):
            if (b, a) in edges:          # shared with a neighbour: cancel
                del edges[(b, a)]
            else:
                edges[(a, b)] = True
    out_from = {}
    for a, b in edges:
        out_from.setdefault(a, []).append(b)
    contours = []
    while out_from:
        start = next(iter(out_from))
        pts, p, prev = [start], start, None
        while True:
            nxt = out_from[p]
            if len(nxt) > 1 and prev is not None:
                # diagonal pinch: take the right turn so shapes stay separate
                dx, dy = p[0] - prev[0], p[1] - prev[1]
                right = (p[0] + dy, p[1] - dx)
                q = right if right in nxt else nxt[0]
            else:
                q = nxt[0]
            nxt.remove(q)
            if not nxt:
                del out_from[p]
            prev, p = p, q
            if p == start:
                break
            pts.append(p)
        # drop collinear points
        simple = []
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
                simple.append(b)
        contours.append(simple)
    return contours


def build_etl(lt1, lt2, out):
    g1, g2 = read_bdf(lt1), read_bdf(lt2)
    chars = {}   # unicode -> bdf glyph
    for enc, g in g1.items():
        if 0x20 <= enc <= 0x7E or 0xA0 <= enc <= 0xFF:
            chars[enc] = g
    for enc, g in g2.items():
        if 0xA0 <= enc <= 0xFF:
            u = ord(bytes([enc]).decode('iso8859_2'))
            chars.setdefault(u, g)   # Latin-1's glyph wins where both have it

    order = ['.notdef'] + [f'uni{u:04X}' for u in sorted(chars)]
    cmap = {u: f'uni{u:04X}' for u in chars}
    glyf, hmtx = {}, {}
    pen = TTGlyphPen(None)
    pen.moveTo((PX, 0)); pen.lineTo((PX, 12 * PX)); pen.lineTo((7 * PX, 12 * PX))
    pen.lineTo((7 * PX, 0)); pen.closePath()
    glyf['.notdef'] = pen.glyph()
    hmtx['.notdef'] = (8 * PX, PX)
    for u, g in chars.items():
        pen = TTGlyphPen(None)
        for c in trace(pixels(g)):
            pen.moveTo((c[0][0] * PX, c[0][1] * PX))
            for x, y in c[1:]:
                pen.lineTo((x * PX, y * PX))
            pen.closePath()
        name = cmap[u]
        glyf[name] = pen.glyph()
        xmin = min((x for x, _ in pixels(g)), default=0)
        hmtx[name] = (g['dw'] * PX, xmin * PX)

    fb = FontBuilder(UPEM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(hmtx)
    fb.setupHorizontalHeader(ascent=ASCENT * PX, descent=-DESCENT * PX)
    fb.setupNameTable({
        'familyName': 'ETL Fixed 16',
        'styleName': 'Regular',
        'copyright': 'Copyright (C) 1994 Electrotechnical Laboratory, Japan. '
                     'Freely usable (GNU intlfonts). Outlines traced from BDF.',
    })
    fb.setupOS2(sTypoAscender=ASCENT * PX, sTypoDescender=-DESCENT * PX,
                sTypoLineGap=0, usWinAscent=ASCENT * PX, usWinDescent=DESCENT * PX,
                fsType=0)
    fb.setupPost(isFixedPitch=1)
    fb.font.flavor = 'woff2'
    fb.save(out)
    return sorted(chars)


def ranges(codes):
    """Compress sorted code points into CSS unicode-range terms."""
    out, start, prev = [], None, None
    for c in codes:
        if start is None:
            start = prev = c
        elif c == prev + 1:
            prev = c
        else:
            out.append((start, prev)); start = prev = c
    if start is not None:
        out.append((start, prev))
    return ', '.join(f'U+{a:X}' if a == b else f'U+{a:X}-{b:X}' for a, b in out)


# Unifont chunks: (file suffix, first, last code point)
CHUNKS = [
    ('latin', 0x0000, 0x02FF),
    ('scripts', 0x0300, 0x1FFF),
    ('symbols', 0x2000, 0x2FFF),
    ('cjk', 0x3000, 0x9FFF),
    ('hangul-misc', 0xA000, 0xFFFF),
]


def build_unifont(src, outdir):
    cmap = TTFont(src).getBestCmap()
    faces = []
    for suffix, lo, hi in CHUNKS:
        codes = sorted(c for c in cmap if lo <= c <= hi)
        if not codes:
            continue
        f = TTFont(src)
        opts = Options()
        opts.flavor = 'woff2'
        opts.layout_features = ['*']
        opts.name_IDs = ['*']
        opts.notdef_outline = True
        s = Subsetter(opts)
        s.populate(unicodes=codes)
        s.subset(f)
        name = f'unifont-{suffix}.woff2'
        f.flavor = 'woff2'
        f.save(Path(outdir) / name)
        faces.append((name, ranges(codes)))
    return faces


def main():
    lt1, lt2, uni, outdir = sys.argv[1:5]
    Path(outdir).mkdir(parents=True, exist_ok=True)
    etl_codes = build_etl(lt1, lt2, str(Path(outdir) / 'etl16.woff2'))
    css = ["/* ETL Fixed 16 (Latin-1 + Latin-2); Unifont covers everything else. */",
           "@font-face {\n  font-family: 'ETL Fixed 16';\n"
           "  src: url('../fonts/etl16.woff2') format('woff2');\n"
           "  font-display: swap;\n"
           f"  unicode-range: {ranges(etl_codes)};\n}}"]
    for name, rng in build_unifont(uni, outdir):
        css.append("@font-face {\n  font-family: 'Unifont';\n"
                   f"  src: url('../fonts/{name}') format('woff2');\n"
                   "  font-display: swap;\n"
                   f"  unicode-range: {rng};\n}}")
    print('\n'.join(css))


if __name__ == '__main__':
    main()
