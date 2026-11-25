# Detailed Banking Notes 2026 – source

Original notes (our own words) for the in-app PDF `app/src/main/assets/notes/banking-notes-2026.pdf`.
Each file in `md/` holds one or more chapters (a chapter starts with `# Title`).

To rebuild the PDF after editing:

1. `python3 otf2ttf.py Regular Medium SemiBold Bold ExtraBold Italic` (once – converts the Inter font to TrueType into `fonts/`)
2. `python3 build.py` (needs Playwright + Chromium, pypdf, markdown, beautifulsoup4 and qpdf) – writes `out/Banking-Notes-2026.pdf` and `out/toc.json`
3. Copy `out/Banking-Notes-2026.pdf` to `app/src/main/assets/notes/banking-notes-2026.pdf` and `out/toc.json` to `app/src/main/assets/notes/banking-notes-2026.json`, update the page count in `NOTES` in `index.html`, and bump `versionCode`.

Box syntax: `> **2026 update:** …`, `> **Exam tip:** …`, `> **Watch out:** …`, `> **Remember:** …`. A `## Quick recap` section becomes the boxed recap at the end of a chapter.
