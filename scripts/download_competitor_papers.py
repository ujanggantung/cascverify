#!/usr/bin/env python3
"""Download key arXiv papers (competitors + related) + metadata for positioning."""
import urllib.request, urllib.parse, os, json, re, time

OUT = r"F:\JURNAL MULAI SEKRANG\01-tool-hallucination-memory-cascade\references"
PDFDIR = os.path.join(OUT, "pdfs")
os.makedirs(PDFDIR, exist_ok=True)

# arXiv IDs we must study (competitors / nearest work)
PAPERS = [
    ("2412.04141", "Reducing Tool Hallucination via Reliability Alignment (PMLR 2025)"),
    ("2609.19425", "Closed-World Resolution Against Tool Hallucination in LLM Agents"),
    ("2510.22977", "The Reasoning Trap: How Enhancing LLM Reasoning Amplifies Tool Hallucination"),
    ("2609.14758", "Fabrication After Tool Failure: Tool-Augmented Agents Assert Values Their Tools Did Not Return"),
    ("2607.22962", "ConsistencyGate: Preventing Memory Contamination in LLM Agents"),
    ("2605.17830", "Remembering More, Risking More: Longitudinal Safety Risks in Memory-Equipped LLM Agents"),
    ("2609.09754", "LexAgentHallu: Hierarchical Benchmark for Profiling Hallucinations in Legal Agents"),
    ("2605.12240", "No Action Without a NOD: Heterogeneous Multi-Agent for Reliable Service Agents"),
    ("2609.15319", "Clean Scores, Buried Evidence, and Confident Wrong: Receipt-Based Audit of Agentic QA"),
]

def get_meta(arxiv_id):
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    with urllib.request.urlopen(url, timeout=25) as r:
        data = r.read().decode()
    title = re.search(r"<entry>.*?<title>(.*?)</title>", data, re.S)
    title = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
    abstract = re.search(r"<entry>.*?<summary>(.*?)</summary>", data, re.S)
    abstract = re.sub(r"\s+", " ", abstract.group(1)).strip() if abstract else ""
    published = re.search(r"<published>(.*?)</published>", data)
    published = published.group(1)[:10] if published else ""
    authors = re.findall(r"<author>.*?<name>(.*?)</name>", data, re.S)
    return {"arxiv_id": arxiv_id, "title": title, "abstract": abstract, "published": published, "authors": authors}

CLEAN_RE = re.compile(r"[^\w\-]+")

def download_pdf(arxiv_id, fn):
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    path = os.path.join(PDFDIR, fn)
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        return path, "exists"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
        return path, "ok"
    except Exception as ex:
        return path, f"fail: {str(ex)[:80]}"

report = []
for aid, label in PAPERS:
    meta = get_meta(aid)
    fn = f"arxiv_{aid}_{CLEAN_RE.sub('_', meta['title'])[:50]}.pdf"
    path, status = download_pdf(aid, fn)
    meta["pdf"] = path
    meta["pdf_status"] = status
    meta["label"] = label
    report.append(meta)
    print(f"[{status}] {aid} {meta['title'][:80]}")
    print(f"   {meta['published']} | authors: {', '.join(meta['authors'][:4])}")
    print(f"   ABS: {meta['abstract'][:220]}...")
    print()
    time.sleep(3)  # arXiv rate limit

with open(os.path.join(OUT, "competitor_papers_arxiv.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("\n=== FILES ===")
for r in report:
    print(os.path.basename(r["pdf"]), "->", r["pdf_status"])