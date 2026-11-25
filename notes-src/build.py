"""Builds the Detailed Banking Notes PDF (A5) from the Markdown chapters in md/.

Two passes: the first print finds the page of every chapter and section (from the PDF
bookmarks), the second print fills those page numbers into the Contents pages.
Also writes toc.json for the in-app reader.
"""
import glob, html, json, os, re, sys
import markdown
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
FONTDIR = os.path.join(ROOT, "fonts")
os.makedirs(OUT, exist_ok=True)
PDF = os.path.join(OUT, "Banking-Notes-2026.pdf")
ASOF = "25 November 2026"

CSS = r"""

@font-face { font-family: "InterT"; src: url("file://{FONTDIR}/Inter-Regular.ttf"); font-weight: 400; font-style: normal; }
@font-face { font-family: "InterT"; src: url("file://{FONTDIR}/Inter-Italic.ttf"); font-weight: 400; font-style: italic; }
@font-face { font-family: "InterT"; src: url("file://{FONTDIR}/Inter-Medium.ttf"); font-weight: 500; }
@font-face { font-family: "InterT"; src: url("file://{FONTDIR}/Inter-SemiBold.ttf"); font-weight: 600; }
@font-face { font-family: "InterT"; src: url("file://{FONTDIR}/Inter-Bold.ttf"); font-weight: 700; }
@font-face { font-family: "InterT"; src: url("file://{FONTDIR}/Inter-ExtraBold.ttf"); font-weight: 800; }
@page { size: 148mm 210mm; margin: 12mm 11mm 14mm 11mm;
  @bottom-left { content: "Lateral Banker Prep · Detailed Banking Notes 2026"; font-family: InterT; font-size: 6.6pt; color: #8A93A6; }
  @bottom-right { content: counter(page) " / " counter(pages); font-family: InterT; font-size: 6.6pt; color: #8A93A6; }
}
@page :first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: InterT, sans-serif; font-size: 9.6pt; line-height: 1.45; color: #1B2333; margin: 0;
  font-feature-settings: "cv11" 1, "ss01" 0; hyphens: auto; }
p { margin: 0 0 2.2mm; }
b, strong { font-weight: 600; color: #101A2E; }
a { color: #1F3B73; text-decoration: none; }
ul, ol { margin: 0 0 2.4mm; padding-left: 4.6mm; }
li { margin: 0 0 1mm; }
li > ul, li > ol { margin-top: 1mm; }
li::marker { color: #F29F1A; }
ol > li::marker { color: #1F3B73; font-weight: 600; }

/* cover */
.cover { width: 148mm; height: 210mm; background: #0F1729; color: #fff; position: relative; overflow: hidden; page-break-after: always; }
.cover .band { position: absolute; left: 0; right: 0; top: 0; height: 74mm; background: linear-gradient(135deg, #1F3B73 0%, #0F1729 100%); }
.cover .disc { position: absolute; right: -28mm; top: 34mm; width: 92mm; height: 92mm; border-radius: 50%; border: 9mm solid rgba(242,159,26,.18); }
.cover .brand { position: absolute; left: 13mm; top: 14mm; font-size: 8.5pt; letter-spacing: .14em; text-transform: uppercase; color: #F29F1A; font-weight: 700; }
.cover .ct { position: absolute; left: 13mm; right: 16mm; top: 86mm; margin: 0; font-size: 27pt; line-height: 1.08; font-weight: 800; color: #fff; letter-spacing: -.01em; }
.cover .sub { position: absolute; left: 13mm; right: 18mm; top: 128mm; font-size: 10.5pt; line-height: 1.45; color: #C9D2E6; }
.cover .chips { position: absolute; left: 13mm; right: 13mm; top: 156mm; }
.cover .chips span { display: inline-block; border: .3mm solid rgba(255,255,255,.28); border-radius: 20mm; padding: 1.1mm 3mm; margin: 0 1.6mm 1.8mm 0; font-size: 7.6pt; color: #E4E9F4; }
.cover .asof { position: absolute; left: 13mm; bottom: 13mm; font-size: 8pt; color: #F29F1A; font-weight: 600; }
.cover .foot { position: absolute; right: 13mm; bottom: 13mm; font-size: 7.4pt; color: #8A93A6; text-align: right; }

/* front matter */
.front h2 { margin-top: 0; }
.legend { display: grid; grid-template-columns: 1fr; gap: 1.6mm; margin: 2mm 0 3mm; }
.toc-title { font-size: 17pt; font-weight: 800; color: #1F3B73; margin: 0 0 3mm; }
.toc { font-size: 8.4pt; }
.toc .tc { break-inside: avoid; }
.toc .c { display: flex; align-items: baseline; margin: 2.3mm 0 .6mm; font-weight: 700; color: #101A2E; font-size: 9pt; break-inside: avoid; }
.toc .c .n { width: 7mm; color: #F29F1A; font-weight: 800; }
.toc .s { display: flex; align-items: baseline; margin: 0 0 .35mm 7mm; color: #3A4458; }
.toc .t { flex: 1 1 auto; }
.toc .dots { flex: 1 1 auto; border-bottom: .25mm dotted #B9C1D3; margin: 0 1.5mm; transform: translateY(-.8mm); min-width: 4mm; }
.toc .pg { flex: 0 0 auto; font-variant-numeric: tabular-nums; color: #1F3B73; font-weight: 600; }
.toc .c .t, .toc .s .t { flex: 0 1 auto; }

/* chapters */
.chapter { page-break-before: always; }
.eyebrow { font-size: 7.6pt; letter-spacing: .16em; text-transform: uppercase; color: #F29F1A; font-weight: 800; margin: 0 0 1mm; }
h1 { font-size: 17pt; line-height: 1.15; font-weight: 800; color: #1F3B73; margin: 0 0 4mm; padding-bottom: 2.4mm; border-bottom: .6mm solid #F29F1A; letter-spacing: -.005em; }
h2 { font-size: 11.6pt; font-weight: 700; color: #1F3B73; margin: 5mm 0 2mm; break-after: avoid; }
h3 { font-size: 10pt; font-weight: 700; color: #101A2E; margin: 3.6mm 0 1.4mm; break-after: avoid; }
h2 + *, h3 + * { break-before: avoid; }

table { width: 100%; border-collapse: collapse; margin: 1mm 0 3.2mm; font-size: 8.1pt; line-height: 1.32; }
thead { display: table-header-group; }
th { background: #1F3B73; color: #fff; font-weight: 600; text-align: left; padding: 1.3mm 1.6mm; vertical-align: bottom; }
td { padding: 1.2mm 1.6mm; border-bottom: .25mm solid #DDE3EE; vertical-align: top; }
tr:nth-child(even) td { background: #F4F6FA; }
tr { break-inside: avoid; }
td:first-child { font-weight: 600; color: #101A2E; }

blockquote { margin: 2mm 0 3.2mm; padding: 2mm 2.8mm 1.2mm; border-radius: 1.8mm; background: #EEF2FA; border-left: 1.1mm solid #1F3B73; break-inside: avoid; }
blockquote p { margin-bottom: 1mm; }
blockquote.tip { background: #EAF6EF; border-left-color: #1E8E5A; }
blockquote.new { background: #FFF4E2; border-left-color: #F29F1A; }
blockquote.warn { background: #FDECEC; border-left-color: #C0392B; }
blockquote.rem { background: #EEF2FA; border-left-color: #1F3B73; }
blockquote strong:first-child { text-transform: uppercase; font-size: 7.2pt; letter-spacing: .08em; margin-right: .8mm; }
blockquote.tip strong:first-child { color: #1E8E5A; }
blockquote.new strong:first-child { color: #B86E00; }
blockquote.warn strong:first-child { color: #C0392B; }
blockquote.rem strong:first-child { color: #1F3B73; }

.recap { margin-top: 5mm; padding: 2.6mm 3mm 1.6mm; border: .4mm solid #1F3B73; border-radius: 2mm; break-inside: avoid; }
.recap h2 { margin: 0 0 1.6mm; font-size: 9pt; text-transform: uppercase; letter-spacing: .1em; color: #F29F1A; }
.recap ul { margin-bottom: 1mm; }
code { font-family: InterT; background: #EEF2FA; padding: 0 .8mm; border-radius: .6mm; }
.endnote { margin-top: 6mm; font-size: 7.6pt; color: #5B6578; }
"""

COVER = """
<section class="cover">
  <div class="band"></div><div class="disc"></div>
  <div class="brand">Lateral Banker Prep</div>
  <div class="ct">Detailed Banking Notes 2026</div>
  <div class="sub">Banking law, credit, priority sector, schemes, forex, risk management and the latest RBI updates, in one place – rechecked against RBI and Government sources.</div>
  <div class="chips"><span>Bank promotion exams</span><span>Lateral entry</span><span>JAIIB / CAIIB</span><span>RBI Grade B</span><span>NABARD / SIDBI</span><span>Interviews</span></div>
  <div class="asof">Updated to %s</div>
  <div class="foot">Original notes · not for resale</div>
</section>
""" % ASOF

FRONT = """
<section class="front">
<div class="toc-title">About these notes</div>
<p>These are complete study notes for bank promotion and lateral-entry exams. Each chapter starts with the rules and figures that are asked most often, followed by the details, and ends with a quick recap for last-minute revision.</p>
<p><b>Checked against official sources.</b> Rates, limits and dates were rechecked against RBI Master Directions, circulars and press releases and Government notifications as of <b>%s</b>. Where common 2026 study material is outdated or wrong, the correct position is shown and the error is listed in the last chapter.</p>
<p><b>How to read the boxes</b></p>
<div class="legend">
<blockquote class="new"><p><strong>2026 update</strong> A change made in 2025-26 that is likely to be asked.</p></blockquote>
<blockquote class="tip"><p><strong>Exam tip</strong> A point examiners like to test, or an easy way to remember it.</p></blockquote>
<blockquote class="warn"><p><strong>Watch out</strong> A common mistake or an outdated figure still found in many notes.</p></blockquote>
</div>
<p><b>Keep up to date.</b> Rules change often. For news after %s, use the <b>Banking Updates</b> tab in the app, which refreshes every day from RBI, PIB and leading newspapers.</p>
<p class="endnote">These notes are written in our own words for exam preparation. They are not legal advice and do not replace the original RBI or Government documents. Abbreviations used: NDTL – net demand and time liabilities; ANBC – adjusted net bank credit; CEOBE – credit equivalent of off-balance-sheet exposure; RE – regulated entity; AD – authorised dealer; MD – Master Direction.</p>
</section>
""" % (ASOF, ASOF)

CALLOUT = [("2026 update", "new"), ("new", "new"), ("exam tip", "tip"), ("tip", "tip"),
           ("watch out", "warn"), ("caution", "warn"), ("remember", "rem"), ("note", "rem")]


def chapters_html():
    files = sorted(glob.glob(os.path.join(ROOT, "md", "*.md")))
    md = markdown.Markdown(extensions=["tables", "sane_lists", "smarty", "attr_list"])
    parts = []
    for f in files:
        text = open(f, encoding="utf-8").read()
        # split a file into chapters at each top-level heading
        for chunk in re.split(r"(?m)^(?=# )", text):
            if chunk.strip():
                md.reset()
                parts.append(md.convert(chunk))
    return parts


def build_html(toc_pages=None):
    parts = chapters_html()
    body, toc_items = [], []
    sec_i = 0
    for n, frag in enumerate(parts, 1):
        soup = BeautifulSoup(frag, "html.parser")
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True)
        h1["id"] = f"ch{n}"
        eb = soup.new_tag("div", attrs={"class": "eyebrow"})
        eb.string = f"Chapter {n}"
        h1.insert_before(eb)
        toc_items.append((1, n, title))
        for h2 in soup.find_all("h2"):
            t = h2.get_text(" ", strip=True)
            if t.lower() == "quick recap":
                # wrap recap heading + following list in a box; keep it out of the contents
                box = soup.new_tag("div", attrs={"class": "recap"})
                nxt = h2.find_next_sibling()
                h2.insert_before(box)
                box.append(h2.extract())
                if nxt is not None:
                    box.append(nxt.extract())
                h2["data-skip"] = "1"
                continue
            sec_i += 1
            h2["id"] = f"s{sec_i}"
            toc_items.append((2, n, t))
        # consecutive callouts end up in one blockquote: split them at each labelled paragraph
        for bq in soup.find_all("blockquote"):
            groups = []
            for p in bq.find_all("p", recursive=False):
                first = next((c for c in p.contents if not (isinstance(c, str) and not c.strip())), None)
                lab = first.get_text(strip=True).rstrip(":").lower() if getattr(first, "name", None) == "strong" else ""
                if not groups or any(lab.startswith(k) for k, _ in CALLOUT):
                    groups.append([p])
                else:
                    groups[-1].append(p)
            prev = bq
            for g in groups[1:]:
                nb = soup.new_tag("blockquote")
                for p in g:
                    nb.append(p.extract())
                prev.insert_after(nb)
                prev = nb
        for bq in soup.find_all("blockquote"):
            st = bq.find("strong")
            key = st.get_text(strip=True).rstrip(":").lower() if st else ""
            cls = next((c for k, c in CALLOUT if key.startswith(k)), "rem")
            bq["class"] = cls
            if st and st.string and st.string.endswith(":"):
                st.string = st.string[:-1]
        body.append(f'<section class="chapter">{soup}</section>')

    # contents
    rows, k = [], 0
    for lvl, n, t in toc_items:
        pg = toc_pages[k] if toc_pages else "00"
        k += 1
        tt = html.escape(t)
        if lvl == 1:
            if rows:
                rows.append('</div>')
            rows.append('<div class="tc">')
            rows.append(f'<a class="c" href="#ch{n}"><span class="n">{n}</span><span class="t">{tt}</span><span class="dots"></span><span class="pg">{pg}</span></a>')
        else:
            rows.append(f'<div class="s"><span class="t">{tt}</span><span class="dots"></span><span class="pg">{pg}</span></div>')
    toc = '<section class="chapter tocsec"><div class="toc-title">Contents</div><div class="toc">' + "".join(rows) + "</div></div></section>"
    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Detailed Banking Notes 2026 – Lateral Banker Prep</title>
<style>{CSS.replace("{FONTDIR}", FONTDIR)}</style></head><body>{COVER}{FRONT}{toc}{''.join(body)}</body></html>"""
    return doc, toc_items


def print_pdf(doc, path):
    src = os.path.join(OUT, "notes.html")
    open(src, "w", encoding="utf-8").write(doc)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("file://" + src)
        pg.wait_for_timeout(300)
        pg.pdf(path=path, prefer_css_page_size=True, print_background=True, outline=True, tagged=True)
        b.close()


def outline_pages(path):
    r = PdfReader(path)
    out = []

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                out.append((it.title.strip(), r.get_destination_page_number(it) + 1))
    walk(r.outline)
    return out, len(r.pages)


def norm(s):
    return re.sub(r"\W+", "", s.lower())


def match_pages(toc_items, outline):
    """Find each contents entry in the bookmark list, in order."""
    pages, j = [], 0
    for lvl, n, t in toc_items:
        key = norm(t)
        while j < len(outline) and norm(outline[j][0]) != key:
            j += 1
        if j == len(outline):
            raise SystemExit(f"heading not found in PDF outline: {t}")
        pages.append(outline[j][1])
        j += 1
    return pages


if __name__ == "__main__":
    doc, items = build_html()
    print_pdf(doc, PDF)
    ol, n1 = outline_pages(PDF)
    pages = match_pages(items, ol)
    doc, items = build_html(pages)
    print_pdf(doc, PDF)
    ol, n2 = outline_pages(PDF)
    pages2 = match_pages(items, ol)
    if pages2 != pages:
        print("page numbers moved between passes; re-running once more")
        doc, items = build_html(pages2)
        print_pdf(doc, PDF)
        ol, n2 = outline_pages(PDF)
        pages = match_pages(items, ol)
        assert pages == pages2, "contents page numbers unstable"
    toc = [{"t": (f"{n}. " if lvl == 1 else "") + t, "p": p - 1, "l": lvl} for (lvl, n, t), p in zip(items, pages2)]
    # smaller file: object streams + max compression (keeps bookmarks and tags)
    import subprocess, shutil
    subprocess.run(["qpdf", "--object-streams=generate", "--compress-streams=y", "--recompress-flate",
                    "--compression-level=9", PDF, PDF + ".tmp"], check=True)
    shutil.move(PDF + ".tmp", PDF)
    json.dump({"title": "Detailed Banking Notes 2026", "asof": ASOF, "pages": n2, "toc": toc},
              open(os.path.join(OUT, "toc.json"), "w"), ensure_ascii=False, indent=0)
    words = sum(len(open(f, encoding="utf-8").read().split()) for f in glob.glob(os.path.join(ROOT, "md", "*.md")))
    print(f"pages: {n2}, chapters: {sum(1 for i in items if i[0] == 1)}, sections: {sum(1 for i in items if i[0] == 2)}, words: {words}, size: {os.path.getsize(PDF)//1024} KB")
