#!/usr/bin/env python3
"""Scopus deep-dive: collect references for tool-hallucination / agent-memory research."""
import json, time, urllib.request, urllib.parse, os, csv, sys, re

KEY = "d79b458e969ee11336d851cfd40cf221"
BASE = "https://api.elsevier.com/content/search/scopus"
OUT = r"F:\JURNAL MULAI SEKRANG\01-tool-hallucination-memory-cascade\references"
PDFDIR = os.path.join(OUT, "pdfs")
os.makedirs(OUT, exist_ok=True)
os.makedirs(PDFDIR, exist_ok=True)

QUERIES = {
  "tool_hallucination": 'TITLE-ABS-KEY("tool hallucination")',
  "hallucination_tool_use": 'TITLE-ABS-KEY(hallucination AND "tool use" AND ("LLM" OR "large language model"))',
  "agent_memory": 'TITLE-ABS-KEY(("agent memory" OR "memory contamination" OR "memory poisoning") AND (LLM OR agent))',
  "tool_benchmark": 'TITLE-ABS-KEY("tool use" AND (benchmark OR evaluation) AND ("large language model" OR LLM))',
  "injection_defense": 'TITLE-ABS-KEY(("prompt injection" OR "tool poisoning" OR "indirect prompt injection") AND (LLM OR agent) AND (defense OR protect OR guard OR verify))',
  "mcp": 'TITLE-ABS-KEY("model context protocol")',
  "tool_grounding": 'TITLE-ABS-KEY((grounding OR "tool learning") AND hallucination AND LLM)',
  "tool_agent_survey": 'TITLE-ABS-KEY((survey OR review) AND ("tool learning" OR "tool-augmented") AND LLM)',
}

def fetch(query, count=25):
    params = {"query": query, "count": count, "start": 0, "apiKey": KEY, "sort": "citedby-count"}
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def unpaywall(doi, email="research@protonmail.com"):
    if not doi:
        return None
    try:
        url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={email}"
        with urllib.request.urlopen(url, timeout=12) as r:
            d = json.load(r)
        loc = d.get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url")
    except Exception:
        return None

rows = []
pdf_links = []
summary = {}

for name, q in QUERIES.items():
    try:
        d = fetch(q)
        res = d.get("search-results", {})
        entries = res.get("entry", [])
        total = res.get("opensearch:totalResults", "?")
        summary[name] = {"query": q, "total": total, "fetched": len(entries)}
        for e in entries:
            doi = e.get("prism:doi", "")
            title = re.sub(r"\s+", " ", e.get("dc:title", "")).strip()
            rows.append({
                "query": name,
                "title": title,
                "authors": e.get("dc:creator", ""),
                "year": (e.get("prism:coverDate") or "")[:4],
                "source": e.get("prism:publicationName", "") or e.get("source-title", ""),
                "doi": doi,
                "eid": e.get("eid", ""),
                "citedby": e.get("citedby-count", "0"),
                "openaccess": e.get("openaccess", ""),
            })
            if doi:
                pdf_links.append((doi, title))
        time.sleep(0.4)
    except Exception as ex:
        summary[name] = {"query": q, "error": str(ex)}
        time.sleep(1.0)

# dedupe by title
seen = set()
uniq = []
for r in rows:
    k = r["title"].lower()
    if k not in seen:
        seen.add(k)
        uniq.append(r)
rows = uniq

# CSV
with open(os.path.join(OUT, "scopus_references.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["query","title","authors","year","source","doi","eid","citedby","openaccess"])
    w.writeheader()
    w.writerows(rows)

# Unpaywall check on top ~35 unique DOIs (prioritize related queries)
prio = ["tool_hallucination","hallucination_tool_use","agent_memory","injection_defense"]
ordered = [r for r in rows if r["query"] in prio] + [r for r in rows if r["query"] not in prio]
oi = 0
oa_report = []
for r in ordered:
    if not r["doi"] or oi >= 35:
        continue
    url = unpaywall(r["doi"])
    if url:
        oa_report.append((r["title"], r["doi"], url))
    time.sleep(0.2)
    oi += 1

with open(os.path.join(OUT, "open_access_links.json"), "w", encoding="utf-8") as f:
    json.dump(oa_report, f, ensure_ascii=False, indent=2)

# Download PDFs (cap 15)
downloaded = []
for title, doi, url in oa_report[:15]:
    try:
        fn = re.sub(r"[^\w\-]+", "_", title)[:60] + ".pdf"
        fp = os.path.join(PDFDIR, fn)
        if os.path.exists(fp):
            downloaded.append((title, fp, "exists")); continue
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as r, open(fp, "wb") as f:
            f.write(r.read())
        downloaded.append((title, fp, "ok", os.path.getsize(fp)))
    except Exception as ex:
        downloaded.append((title, "", "fail", str(ex)[:80]))

with open(os.path.join(OUT, "pdf_download_report.json"), "w", encoding="utf-8") as f:
    json.dump(downloaded, f, ensure_ascii=False, indent=2)

print("=== SUMMARY ===")
for k, v in summary.items():
    print(f"{k}: {v}")
print(f"\nTotal unique rows: {len(rows)}")
print(f"OA links found: {len(oa_report)}")
print(f"PDFs: {len([d for d in downloaded if len(d)>2 and d[2]=='ok'])} ok, {len([d for d in downloaded if len(d)>2 and d[2]=='fail'])} failed")
print("\n=== TOP RELEVANT (tool_hallucination + hallucination_tool_use, by cites) ===")
for r in sorted([r for r in rows if r["query"] in ("tool_hallucination","hallucination_tool_use")], key=lambda x: -int(x["citedby"] or 0))[:25]:
    print(f"[{r['citedby']}] {r['title'][:100]} | {r['year']} | {r['source'][:40]} | DOI:{r['doi'] or '-'}")