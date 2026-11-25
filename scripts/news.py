#!/usr/bin/env python3
"""Daily banking-news snapshot for the Lateral Banker Prep app.

Runs in GitHub Actions (no AI involved). Reads RBI and PIB RSS feeds plus Google News
search feeds, keeps exam-relevant banking/finance items, merges them into data/news.json
(last 45 days). The Android app also fetches the same feeds itself on launch and pull-down.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
IST = timezone(timedelta(hours=5, minutes=30))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

FEEDS = [
    {"u": "https://rbi.org.in/pressreleases_rss.xml", "src": "RBI press release", "off": 1, "rbi": 1},
    {"u": "https://rbi.org.in/notifications_rss.xml", "src": "RBI notification", "off": 1, "rbi": 1, "cat": "RBI circulars"},
    {"u": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", "src": "PIB", "off": 1, "pib": 1},
]
GQ = [
    "RBI bank when:3d",
    '"public sector bank" OR SBI OR PNB OR "Bank of Baroda" OR "Canara Bank" OR "Union Bank of India" when:3d',
    'bank appointed "MD & CEO" OR chairman OR "executive director" OR "deputy governor" when:7d',
    'bank MoU OR "ties up" OR partnership OR launches when:3d',
    'RBI penalty OR "cancels licence" OR restrictions bank when:7d',
    'NPCI OR UPI OR "digital payments" OR "e-rupee" when:3d',
    'SEBI OR IRDAI OR PFRDA OR NABARD OR SIDBI OR "EXIM Bank" OR "National Housing Bank" when:3d',
    "bank merger OR acquisition OR stake OR QIP India bank when:7d",
    '"Ministry of Finance" OR "Department of Financial Services" OR Sitharaman bank OR scheme when:3d',
    '"World Bank" OR IMF OR ADB OR "New Development Bank" OR AIIB India when:7d',
]
I = re.I
CATS = [
    ("Appointments", re.compile(r"\b(appoint\w*|re-?appoint\w*|named|takes? (over )?charge|assumes? charge|elevated|tenure extend\w*|to head|new (md|ceo|chairman|chief))\b", I)),
    ("Penalties & licences", re.compile(r"\b(penalt\w*|imposes|fined|monetary penalty|cancels? (the )?licen[cs]e|licen[cs]e cancell\w*|restrictions?|section 35a|supersed\w*)\b", I)),
    ("Mergers & deals", re.compile(r"\b(merger|amalgamat\w*|acqui\w*|stake|takeover|ipo|qip|capital rais\w*|raises? (rs|₹)|bonds? issue|infra bonds?)\b", I)),
    ("MoUs & tie-ups", re.compile(r"\b(mou|ties? up|tie-up|partners? with|partnership|collaborat\w*|joins hands|signs? (an? )?(agreement|pact|deal))\b", I)),
    ("Launches", re.compile(r"\b(launch\w*|unveil\w*|introduc\w*|rolls? out|inaugurat\w*)\b", I)),
    ("Digital & payments", re.compile(r"\b(upi|npci|digital|fintech|payments?|cbdc|e-rupee|cards?|cyber|fraud\w*|aeps|fastag|imps|neft|rtgs|wallets?)\b", I)),
    ("Govt & schemes", re.compile(r"\b(scheme|yojana|mission|cabinet|ministry|government|budget|sitharaman|parliament)\b", I)),
    ("Reports & data", re.compile(r"\b(report|index|survey|ranking|award|data|statistics|bulletin|gdp|inflation|forex reserves?|growth)\b", I)),
]
RBI_ROUTINE = re.compile(r"money market operations|variable rate (reverse )?repo|\bvrrr?\b|treasury bills?|t-bills?|cash management bills?|state government securities|\bsdl\b|government stock|auction|result of|cut-?off|underwriting|reserve money|lendings? and deposits|weekly statistical|sectoral deployment|payment system indicators|liquidity adjustment|\bomo\b|open market operation|switch|conversion of|buyback|calendar for|foreign exchange turnover|money supply|redemption", I)
FIN = re.compile(r"\b(bank\w*|lend\w*|sbi|pnb|bob|hdfc|icici|axis|kotak|idbi|iob|uco|yes bank|rbi|reserve bank|npci|upi|sebi|irdai|pfrda|nabard|sidbi|exim|nhb|financ\w*|credit|loans?|deposits?|payments?|fintech|insurance|pension|mudra|jan dhan|imf|world bank|adb|aiib|ndb|gdp|inflation|economy|rupee|forex|bonds?|msmes?|exports?|gst|investment)\b", I)
JUNK = re.compile(r"\b(share price|shares? (jump|fall|rise|surge|slip|gain|drop|tank|rally|soar|plunge)\w*|stocks? to (buy|watch)|target price|sensex|nifty|brokerage|buy rating|sell rating|multibagger|gmp|q[1-4] (results?|earnings)|quarterly results|net profit|profit (rises|falls|jumps|surges|declines|up|down)|recruitment|vacanc\w*|admit card|exam date|syllabus|answer key|cut off marks|horoscope|cricket|movie)\b", I)


def key(t):
    return re.sub(r"[^a-z0-9]+", "", t.lower())[:80]


def cat_of(t, f=None):
    if f and f.get("cat"):
        return f["cat"]
    for c, r in CATS:
        if r.search(t):
            if f and f.get("rbi") and c not in ("Penalties & licences", "Appointments"):
                return "RBI"
            return c
    return "RBI" if f and f.get("rbi") else "Govt & schemes" if f and f.get("pib") else "Other"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(2_000_000)


def pdate(s):
    s = (s or "").strip()
    if not s:
        return 0
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        return 0
    if d.tzinfo is None:
        d = d.replace(tzinfo=IST)
    return int(d.timestamp() * 1000)


def items(raw):
    root = ET.fromstring(raw)
    out = []
    for it in root.iter("item"):
        g = lambda n: (it.findtext(n) or "").strip()
        t = re.sub(r"\s+", " ", g("title"))
        u = g("link")
        if t and u.startswith("http"):
            out.append({"t": t, "u": u, "d": pdate(g("pubDate")), "srcName": g("source")})
    return out


def official(f):
    res = []
    for i in items(fetch(f["u"])):
        if f.get("rbi") and RBI_ROUTINE.search(i["t"]):
            continue
        if f.get("pib") and not FIN.search(i["t"]):
            continue
        res.append({"t": i["t"], "u": i["u"].replace("http:", "https:", 1), "src": f["src"], "d": i["d"], "cat": cat_of(i["t"], f), "off": 1})
    return res[:40]


def google(q):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en-IN&gl=IN&ceid=IN:en"
    res = []
    for i in items(fetch(url)):
        t, src = i["t"], i["srcName"]
        if src and t.endswith(" - " + src):
            t = t[: -(len(src) + 3)]
        t = t.strip()
        if i["d"] and FIN.search(t) and not JUNK.search(t):
            res.append({"t": t, "u": i["u"], "src": src or "News", "d": i["d"], "cat": cat_of(t)})
    return res


def main():
    now = int(time.time() * 1000)
    try:
        old = json.load(open(OUT, encoding="utf-8")).get("items", [])
    except Exception:
        old = []
    new, ok = [], 0
    for f in FEEDS:
        try:
            new += official(f); ok += 1
        except Exception as e:
            print("feed failed:", f["u"], e, file=sys.stderr)
    for q in GQ:
        try:
            new += google(q); ok += 1
        except Exception as e:
            print("google failed:", q, e, file=sys.stderr)
    if not ok:
        print("No source reachable; keeping old file"); return
    m = {key(i["t"]): i for i in old}
    added = 0
    for i in new:
        k = key(i["t"])
        if k not in m:
            m[k] = {**i, "d": i["d"] or now, "fs": now}; added += 1
        elif i.get("off") and not m[k].get("off"):
            m[k] = {**i, "d": i["d"] or m[k].get("d"), "fs": m[k].get("fs", now)}
    cut = now - 45 * 864e5
    out = sorted((i for i in m.values() if (i.get("d") or i.get("fs", 0)) >= cut), key=lambda i: -(i.get("d") or i.get("fs", 0)))[:800]
    data = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "items": out}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=0)
    print(f"sources ok: {ok}, new items: {added}, total: {len(out)}")


if __name__ == "__main__":
    main()
