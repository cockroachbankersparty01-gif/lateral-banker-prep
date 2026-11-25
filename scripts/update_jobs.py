"""Daily update of data/jobs.json for the Lateral Banker Prep app (runs on GitHub Actions, no AI).

Scope: officer-level / specialist / lateral posts at public sector banks, IBPS (CRP SPL, RRB Scale II/III),
RBI, SIDBI, EXIM Bank, NABARD, SEBI, PFRDA, IRDAI and National Housing Bank.
Source: FreeJobAlert listing pages; each article's Important Links give the official notice and apply links.
Entries are never deleted while recent; finished ones drop off after 6 months.
"""
import datetime as dt
import json
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

DATA = sys.argv[1] if len(sys.argv) > 1 else "data/jobs.json"
FJA = "https://www.freejobalert.com/"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
TODAY = dt.datetime.now(IST).date()
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36 LBP-updater"

# board text pattern -> (display name, id prefix)
BANKS = [
    (r"\bsbi\b|state bank of india", "State Bank of India", "sbi"),
    (r"\bbob\b|bank of baroda", "Bank of Baroda", "bob"),
    (r"union bank", "Union Bank of India", "ubi"),
    (r"\bpnb\b|punjab national bank", "Punjab National Bank", "pnb"),
    (r"canara bank", "Canara Bank", "canara"),
    (r"\bboi\b|bank of india", "Bank of India", "boi"),
    (r"indian bank", "Indian Bank", "indianbank"),
    (r"central bank of india", "Central Bank of India", "cbi"),
    (r"punjab (?:&|and) sind", "Punjab & Sind Bank", "psb"),
    (r"bank of maharashtra", "Bank of Maharashtra", "bom"),
    (r"\biob\b|indian overseas bank", "Indian Overseas Bank", "iob"),
    (r"\buco\b", "UCO Bank", "uco"),
    (r"\bibps\b", "IBPS", "ibps"),
    (r"\brbi\b|reserve bank", "Reserve Bank of India", "rbi"),
    (r"\bsidbi\b", "SIDBI", "sidbi"),
    (r"\bexim\b", "EXIM Bank", "exim"),
    (r"\bnabard\b", "NABARD", "nabard"),
    (r"\bsebi\b", "SEBI", "sebi"),
    (r"\bpfrda\b", "PFRDA", "pfrda"),
    (r"\birdai\b", "IRDAI", "irdai"),
    (r"\bnhb\b|national housing bank", "National Housing Bank", "nhb"),
]
OFFICER = re.compile(r"officer|manager|specialist|\bso\b|\bsco\b|grade ?[ab]\b|scale ?(?:ii|iii|2|3)\b|"
                     r"executive|head|consultant|expert|lateral|\blbo\b|\bcbo\b|chief|analyst|scientist|"
                     r"management trainee|\bgm\b|\bdgm\b|\bagm\b|vice president|\bvp\b", re.I)
HARD_EXCLUDE = re.compile(r"clerk|junior associate|office assistant|apprentice|attendant|development assistant|"
                          r"sub.?staff|peon|driver|guard|probationary officer|\bpo\b|officer scale ?(?:i|1)\b(?!i)|"
                          r"multi.?purpose|retired|pharmacist|doctor|counsellor|medical officer", re.I)
SOFT_EXCLUDE = re.compile(r"\bassistants?\b(?! (?:manager|general|vice|director))", re.I)
GENERIC = {"officer", "officers", "specialist", "manager", "managers", "cadre", "regular", "posts", "post", "various",
           "result", "admit", "card", "exam", "the", "and", "for", "bank", "india", "recruitment", "online", "phase",
           "final", "interview", "score", "marks", "call", "letter", "2026", "2027", "advt"}


def in_scope(text):
    if HARD_EXCLUDE.search(text) or not OFFICER.search(text):
        return False
    return not SOFT_EXCLUDE.search(text) or re.search(r"manager", text, re.I)
SOCIAL = re.compile(r"whatsapp|t\.me|telegram|play\.google|freejobalert\.com|facebook|instagram|youtube|twitter|x\.com")


def get(url):
    for n in range(3):
        try:
            r = S.get(url, timeout=40)
            if r.status_code == 200:
                time.sleep(0.8)
                return BeautifulSoup(r.text, "html.parser")
            print("  ", r.status_code, url)
        except requests.RequestException as e:
            print("  error", e, url)
        time.sleep(3 * (n + 1))
    return None


def pdate(s):
    for f in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime((s or "").strip(), f).date()
        except ValueError:
            pass
    return None


def rows(soup, need):
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if not trs:
            continue
        hdr = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
        if need not in " ".join(hdr):
            continue
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            a = next((x["href"] for x in tr.find_all("a", href=True) if "/articles/" in x["href"]), None)
            if a:
                yield dict(zip(hdr, cells)), a


def bank_of(text):
    for pat, name, slug in BANKS:
        if re.search(pat, text, re.I):
            return name, slug
    return None, None


def links(url):
    soup = get(url)
    if not soup:
        return None, None
    found = []
    for h in soup.find_all(["h2", "h3"]):
        if "important links" in h.get_text(" ", strip=True).lower():
            t = h.find_next("table")
            if t:
                found = [(a.get_text(" ", strip=True), a["href"]) for a in t.find_all("a", href=True)]
            break
    found = [(t, h) for t, h in found if h.startswith("http") and (not SOCIAL.search(h) or "img2.freejobalert" in h)]
    notice = next((h for t, h in found if re.search(r"notification|notice|advertisement|advt|result|admit|pdf", t, re.I)
                   or h.lower().endswith(".pdf")), None)
    other = next((h for t, h in found if h != notice and re.search(r"apply|official|website|login|portal", t, re.I)), None)
    return notice, other or next((h for t, h in found if h != notice), None)


def scale_of(title):
    t = title.lower()
    for pat, s in [(r"grade ?a\b.*grade ?b|grade ?a ?(?:&|and) ?b", "Grade A / B"), (r"grade ?b", "Grade B"),
                   (r"grade ?a", "Grade A"), (r"scale ?(?:ii|2).*(?:iii|3)", "Scale II / III"),
                   (r"scale ?(?:iii|3)", "Scale III"), (r"scale ?(?:ii|2)", "Scale II"),
                   (r"management trainee", "MT"), (r"contract|consultant", "Contract"),
                   (r"specialist|\bso\b|\bsco\b", "Specialist"), (r"local bank officer|\blbo\b", "JMGS-I")]:
        if re.search(pat, t):
            return s
    return "Officer"


def main():
    d = json.load(open(DATA, encoding="utf-8"))
    jobs = d["jobs"]
    by_id = {j["id"]: j for j in jobs}
    have_art = {j.get("src") for j in jobs} - {None}
    now_iso = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = staged = 0

    # 1) new notifications
    seen = set()
    for path in ["bank-jobs/", "latest-notifications/", "government-jobs/"]:
        soup = get(FJA + path)
        if not soup:
            continue
        for c, art in rows(soup, "Last Date"):
            if art in seen or art in have_art:
                continue
            seen.add(art)
            board = c.get("Recruitment Board", "")
            title = c.get("Exam / Post Name", "")
            bank, slug = bank_of(board) if bank_of(board)[0] else bank_of(title)
            if not bank:
                continue
            if not in_scope(title):
                continue
            last, posted = pdate(c.get("Last Date")), pdate(c.get("Post Date"))
            if not last or last < TODAY:
                continue
            m = re.search(r"(\d[\d,]*)\s*Posts?", title, re.I)
            post = re.sub(r"\s*[–-]\s*\d[\d,]*\s*Posts?\s*$", "", title).strip()
            jid = f"{slug}-{re.search(r'(\d+)$', art.rstrip('/')).group(1)}"
            if jid in by_id or any(j["bank"] == bank and j.get("lastDate") == last.isoformat() for j in jobs):
                continue
            notice, site = links(art)
            j = {"id": jid, "addedAt": now_iso, "bank": bank, "post": post, "scale": scale_of(post),
                 "notified": posted.isoformat() if posted else "", "lastDate": last.isoformat(),
                 "link": notice or site or art, "src": art,
                 "note": ("Official notification linked above." + (f" Apply / details: {site}" if site and notice else ""))
                 if notice else "Details from a job-news listing; confirm on the official site."}
            if m:
                j["vacancies"] = m.group(1)
            jobs.append(j)
            by_id[jid] = j
            added += 1
    print("new notifications:", added)

    # 2) progress: admit cards and results for banks already in the list
    for path, need, kind in [("admit-card/", "Post/Exam Name", "admit"), ("exam-results/", "Post/Exam Name", "result")]:
        soup = get(FJA + path)
        if not soup:
            continue
        for c, art in rows(soup, need):
            posted = pdate(c.get("Post Date"))
            if not posted or (TODAY - posted).days > 4:
                continue
            board = c.get("Recruitment Board", "")
            exam = c.get("Post/Exam Name", "")
            bank, _ = bank_of(board) if bank_of(board)[0] else bank_of(exam)
            if not bank or not in_scope(exam):
                continue
            def kw(t):
                return set(re.findall(r"[a-z0-9]{3,}", t.lower())) - GENERIC
            words = kw(exam)
            cands = [j for j in jobs if j["bank"] == bank and j.get("stageType") != "final"]
            best = max(cands, key=lambda j: len(words & kw(j["post"] + " " + j.get("scale", ""))), default=None)
            if not best or len(words & kw(best["post"] + " " + best.get("scale", ""))) < 2:
                continue
            if best.get("resultDate", "") >= posted.isoformat() and best.get("_last") == art:
                continue
            url, _ = links(art)
            ds = posted.strftime("%d.%m.%Y")
            if kind == "admit":
                best["stage"], best["stageType"] = f"Admit card out ({ds}) – {exam}", "in-process"
            else:
                final = re.search(r"final|selection|merit", exam, re.I)
                best["stage"] = f"{'Final result' if final else 'Result'} out ({ds}) – {exam}"
                best["stageType"] = "final" if final else "result"
            best["resultDate"] = posted.isoformat()
            best["resultLink"] = url or art
            best["_last"] = art
            staged += 1
    print("progress updates:", staged)

    # 3) keep the last ~6 months
    cutoff = (TODAY - dt.timedelta(days=180)).isoformat()
    def recent(j):
        latest = max(j.get("resultDate") or "", j.get("lastDate") or "", j.get("notified") or "", j.get("addedAt", "")[:10])
        return latest >= cutoff
    d["jobs"] = sorted([j for j in jobs if recent(j)], key=lambda j: j["id"])
    d["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("total:", len(d["jobs"]))


if __name__ == "__main__":
    main()
