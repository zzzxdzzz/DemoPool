#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Semi-automatic college essay requirement collector
1) Search phase: for each school, query web search API to find candidate URLs.
2) Review phase: user selects the best URL in candidates.csv (set chosen=1).
3) Fetch phase: script downloads chosen pages and extracts essay prompts.
Outputs: essays.csv (tidy table) + raw_html/ (cached)
"""

import os, re, time, json, csv, math, glob
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import pandas as pd
from slugify import slugify
import tldextract
from rapidfuzz import fuzz
from io import BytesIO
from pdfminer.high_level import extract_text as pdf_extract_text

# ========== CONFIG ==========
SEARCH_ENGINE = os.getenv("SEARCH_ENGINE", "google")  # 'google' or 'serpapi'
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

QUERY_TEMPLATES = [
    "{school} admissions supplemental essay prompts site:.edu",
    "{school} supplemental essay prompts site:admissions.*",
    "{school} writing supplement 2025 prompts site:.edu",
    "{school} application essay requirements site:.edu",
    "{school} personal statement requirements site:.edu",
]

MAX_RESULTS_PER_SCHOOL = 8
RATE_LIMIT_SECONDS = 1.1  # be nice
OUTPUT_DIR = "output"
RAW_DIR = os.path.join(OUTPUT_DIR, "raw_html")
CANDIDATES_CSV = os.path.join(OUTPUT_DIR, "candidates.csv")
ESSAYS_CSV = os.path.join(OUTPUT_DIR, "essays.csv")

KEYWORDS_HINTS = [
    "supplemental essay", "supplemental essays", "supplement", "essay prompt",
    "prompts", "writing supplement", "personal statement", "short answer",
    "why us", "why this college", "字数", "word limit", "words", "字数限制"
]

HEADER_HINTS = [
    "essay", "prompt", "writing", "supplement", "question", "短文", "题目", "要求"
]

WORD_LIMIT_PAT = re.compile(r"(\b[\d]{2,4}\s*(?:words?|字|字数))", re.I)
PROMPT_LEAD_PAT = re.compile(r"^(?:prompt\s*#?\d*|question\s*#?\d*|topic\s*#?\d*|essay\s*#?\d*)[:.\-\s]", re.I)

SAFE_UA = {
    "User-Agent": "Mozilla/5.0 (compatible; EssayCollector/1.0; +https://example.org)"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

@dataclass
class SearchHit:
    school: str
    title: str
    url: str
    snippet: str
    score: float

# --------- Utilities ---------
def norm_domain(url: str) -> str:
    try:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"
    except Exception:
        return ""

def likely_official(school: str, url: str, title: str) -> float:
    """
    Heuristic scoring: prefer .edu admissions/writing pages and school name mentions.
    """
    score = 0.0
    d = norm_domain(url)
    if d.endswith(".edu"):
        score += 30
    if "admission" in url.lower() or "admissions" in url.lower():
        score += 15
    if "writing" in url.lower() or "essay" in url.lower() or "supplement" in url.lower():
        score += 10
    # title similarity
    score += 0.2 * fuzz.partial_ratio(school.lower(), title.lower())
    return score

def google_search(query: str) -> List[Dict]:
    base = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": GOOGLE_CSE_ID,
        "key": GOOGLE_API_KEY,
        "num": 10
    }
    r = requests.get(base, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", []) or []
    results = []
    for it in items:
        results.append({
            "title": it.get("title", ""),
            "link": it.get("link", ""),
            "snippet": it.get("snippet", "")
        })
    return results

def serpapi_search(query: str) -> List[Dict]:
    base = "https://serpapi.com/search.json"
    params = {"q": query, "engine": "google", "api_key": SERPAPI_KEY, "num": 10}
    r = requests.get(base, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("organic_results", []) or []
    results = []
    for it in items:
        results.append({
            "title": it.get("title", ""),
            "link": it.get("link", ""),
            "snippet": it.get("snippet", "")
        })
    return results

def search_school(school: str) -> List[SearchHit]:
    hits: List[SearchHit] = []
    for tmpl in QUERY_TEMPLATES:
        q = tmpl.format(school=school)
        try:
            if SEARCH_ENGINE == "google":
                raw = google_search(q)
            else:
                raw = serpapi_search(q)
        except Exception as e:
            print(f"[WARN] search failed: {e} for {school}")
            raw = []
        for it in raw:
            title, url, snippet = it.get("title",""), it.get("link",""), it.get("snippet","")
            if not url: 
                continue
            sc = likely_official(school, url, title)
            hits.append(SearchHit(school, title, url, snippet, sc))
        time.sleep(RATE_LIMIT_SECONDS)
    # de-dup by url
    uniq: Dict[str, SearchHit] = {}
    for h in sorted(hits, key=lambda x: -x.score):
        if h.url not in uniq:
            uniq[h.url] = h
    hits = list(uniq.values())
    return hits[:MAX_RESULTS_PER_SCHOOL]

def fetch_url(url: str) -> Tuple[str, str]:
    """
    Returns (content_type, text)
    """
    r = requests.get(url, headers=SAFE_UA, timeout=30)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type","").lower()
    if "application/pdf" in ctype or url.lower().endswith(".pdf"):
        text = pdf_extract_text(BytesIO(r.content))
        return ("pdf", text or "")
    else:
        html = r.text
        return ("html", html)

def html_to_text_blocks(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    # remove scripts/styles/nav/footer
    for bad in soup(["script","style","noscript","svg","nav","footer","header","form","iframe"]):
        bad.decompose()
    blocks: List[str] = []
    # capture headers+lists+paragraphs
    for el in soup.find_all(["h1","h2","h3","h4","p","li"]):
        txt = el.get_text(" ", strip=True)
        if txt:
            blocks.append(txt)
    return blocks

def is_prompt_line(line: str) -> bool:
    if PROMPT_LEAD_PAT.search(line): 
        return True
    # list-like prompt or question mark
    if len(line) < 500 and (line.endswith("?") or ":" in line[:120]):
        # not too generic
        if any(k in line.lower() for k in ["essay","prompt","supplement","statement","question","why"]):
            return True
    return False

def extract_prompts(text_blocks: List[str]) -> List[Dict]:
    """
    Very simple heuristic: scan blocks for keywords; group nearby lines as one prompt.
    """
    prompts = []
    for i, line in enumerate(text_blocks):
        low = line.lower()
        if any(k in low for k in KEYWORDS_HINTS) or is_prompt_line(line):
            # build a window around it
            window = [line]
            # include next 2 lines if short
            for j in range(1,3):
                if i+j < len(text_blocks) and len(text_blocks[i+j]) < 500:
                    window.append(text_blocks[i+j])
            blob = " ".join(window).strip()
            # find word limit hint
            m = WORD_LIMIT_PAT.search(blob)
            word_limit = m.group(1) if m else ""
            # de-duplicate similar blobs
            if not any(fuzz.ratio(blob, p["prompt_text"]) > 90 for p in prompts):
                prompts.append({
                    "prompt_text": blob,
                    "word_limit_hint": word_limit
                })
    return prompts

def save_raw(name: str, content: str):
    fp = os.path.join(RAW_DIR, f"{slugify(name)[:80]}.txt")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    return fp

# --------- Main Pipeline ---------
def phase_search(schools_csv: str):
    df = pd.read_csv(schools_csv)
    rows = []
    for school in df["school"].dropna().tolist():
        hits = search_school(school)
        for rank, h in enumerate(sorted(hits, key=lambda x: -x.score), start=1):
            rows.append({
                "school": school,
                "rank": rank,
                "title": h.title,
                "url": h.url,
                "snippet": h.snippet,
                "score": round(h.score, 2),
                "chosen": 0
            })
    out = pd.DataFrame(rows)
    out.to_csv(CANDIDATES_CSV, index=False)
    print(f"[OK] Wrote candidates to {CANDIDATES_CSV}")
    print("Next: open it and set chosen=1 for the correct URL per school.")

def phase_fetch_and_extract(candidates_csv: str):
    cand = pd.read_csv(candidates_csv)
    chosen = cand[cand["chosen"] == 1].copy()
    if chosen.empty:
        print("[WARN] No chosen rows. Edit candidates.csv first (set chosen=1).")
        return
    results = []
    for _, row in chosen.iterrows():
        school, url, title = row["school"], row["url"], row.get("title","")
        name = f"{school}__{title}"
        try:
            ctype, content = fetch_url(url)
        except Exception as e:
            print(f"[ERR] fetch failed for {school}: {url} :: {e}")
            continue

        if ctype == "html":
            blocks = html_to_text_blocks(content)
            raw_path = save_raw(name, "\n".join(blocks))
        else:
            # pdf
            text = content
            blocks = [b.strip() for b in text.splitlines() if b.strip()]
            raw_path = save_raw(name, text)

        prompts = extract_prompts(blocks)
        if not prompts:
            # fallback: add a generic row to review manually
            prompts = [{"prompt_text": "(No obvious prompts found — please review raw)", "word_limit_hint": ""}]

        for p in prompts:
            results.append({
                "school": school,
                "source_url": url,
                "prompt_text": p["prompt_text"],
                "word_limit_hint": p["word_limit_hint"],
                "raw_cache": raw_path
            })
        time.sleep(RATE_LIMIT_SECONDS)

    out = pd.DataFrame(results)
    out.to_csv(ESSAYS_CSV, index=False)
    print(f"[OK] Extracted {len(results)} prompt rows → {ESSAYS_CSV}")
    print(f"Raw caches are in: {RAW_DIR}")
    print("Note: always verify against the official admissions page; prompts may update each cycle.")

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Semi-automatic essay prompt collector")
    ap.add_argument("--schools", default="schools.csv", help="CSV with a 'school' column")
    ap.add_argument("--phase", choices=["search","fetch"], required=True,
                    help="search: build candidates.csv; fetch: download chosen=1 and extract")
    args = ap.parse_args()

    if args.phase == "search":
        if SEARCH_ENGINE == "google" and (not GOOGLE_API_KEY or not GOOGLE_CSE_ID):
            raise SystemExit("Set GOOGLE_API_KEY and GOOGLE_CSE_ID env vars or switch SEARCH_ENGINE=serpapi")
        if SEARCH_ENGINE == "serpapi" and not SERPAPI_KEY:
            raise SystemExit("Set SERPAPI_KEY env var or switch SEARCH_ENGINE=google")
        phase_search(args.schools)
    else:
        phase_fetch_and_extract(CANDIDATES_CSV)

if __name__ == "__main__":
    main()
