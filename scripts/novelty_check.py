#!/usr/bin/env python3
"""Novelty check: GitHub repo search + HuggingFace datasets + arXiv cross-check."""
import json, time, urllib.request, urllib.parse, os, csv

OUT = r"F:\JURNAL MULAI SEKRANG\01-tool-hallucination-memory-cascade\references"
os.makedirs(OUT, exist_ok=True)

def gh_search(query):
    try:
        url = "https://api.github.com/search/repositories?q=" + urllib.parse.quote(query) + "&per_page=10"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "hermes-research"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        return d.get("total_count", 0), [{"full_name": i["full_name"], "desc": (i.get("description") or "")[:140], "stars": i.get("stargazers_count", 0), "url": i["html_url"]} for i in d.get("items", [])]
    except Exception as ex:
        return -1, [str(ex)[:100]]

QUERIES = [
  "tool hallucination",
  "llm tool hallucination",
  "agent hallucination detection",
  "llm tool use verifier",
  "agent memory contamination",
  "prompt injection defense agent",
  "mcp guard security",
  "llm tool call verification",
  "tool use benchmark llm",
]

rows = []
for q in QUERIES:
    total, items = gh_search(q)
    rows.append({"query": q, "total": total, "items": items})
    print(f"GitHub '{q}': total={total}")
    for it in items[:5]:
        print(f"   - {it['full_name']} ({it['stars']}★) {it['desc'][:80]}")
    time.sleep(7)  # unauth rate limit 10/min

with open(os.path.join(OUT, "github_search.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print("\n=== HUGGINGFACE DATASETS ===")
for term in ["tool hallucination", "agent hallucination", "tool use benchmark", "llm agent memory"]:
    try:
        url = "https://huggingface.co/api/datasets?search=" + urllib.parse.quote(term) + "&limit=10"
        with urllib.request.urlopen(url, timeout=20) as r:
            d = json.load(r)
        print(f"HF '{term}': {len(d)} datasets")
        for ds in d[:8]:
            print(f"   - {ds.get('id')}")
    except Exception as ex:
        print(f"HF '{term}': ERR {str(ex)[:80]}")
    time.sleep(1)

print("\n=== ARXIV CROSS-CHECK ===")
def arxiv(q):
    try:
        url = "https://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q) + "&max_results=8&sortBy=submittedDate&sortOrder=descending"
        with urllib.request.urlopen(url, timeout=25) as r:
            data = r.read().decode()
        import re
        ids = re.findall(r"<id>http://arxiv.org/abs/([\w.\-/]+)</id>", data)
        titles = re.findall(r"<title>(.*?)</title>", data, re.S)
        items = list(zip(ids, [t.strip().replace("\n"," ") for t in titles[1:]]))
        return items
    except Exception as ex:
        return [("ERR", str(ex)[:80])]

for q in ['abs:"tool hallucination"', 'abs:"memory contamination" AND agent', 'abs:"tool call" AND fabrication']:
    items = arxiv(q)
    print(f"arXiv {q}: {len(items)}")
    for i, t in items[:8]:
        print(f"   - {i} {t[:100]}")

with open(os.path.join(OUT, "arxiv_crosscheck.json"), "w", encoding="utf-8") as f:
    json.dump({"queries": QUERIES, "github": rows}, f, ensure_ascii=False, indent=2)

print("\nDONE")