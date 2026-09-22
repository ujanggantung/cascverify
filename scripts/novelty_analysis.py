#!/usr/bin/env python3
"""Compile the final competitive landscape analysis from all collected data."""
import json, os

OUT = r"F:\JURNAL MULAI SEKRANG\01-tool-hallucination-memory-cascade\references"

# Load all data
with open(os.path.join(OUT, "scopus_references.csv"), encoding="utf-8") as f:
    scopus = f.read()
with open(os.path.join(OUT, "competitor_papers_arxiv.json"), encoding="utf-8") as f:
    competitors = json.load(f)
with open(os.path.join(OUT, "github_search.json"), encoding="utf-8") as f:
    github = json.load(f)

# Build analysis
print("=" * 80)
print("NOVELTY ANALYSIS — Persistent Tool Hallucinations: Memory Cascade")
print("=" * 80)

print("""
## 1. COMPETITOR LANDSCAPE (9 Key Papers)

### A. NEAREST COMPETITOR: Tool Hallucination (direct)
""")

for c in competitors:
    tag = ""
    title_low = c["title"].lower()
    if "hallucinat" in title_low and "tool" in title_low:
        tag = "⚠️  DIRECT COMPETITOR"
    elif "memory" in title_low and ("contaminat" in title_low or "safety" in title_low):
        tag = "⚠️  DIRECT COMPETITOR"
    elif "fabricat" in title_low:
        tag = "⚠️  NEAR COMPETITOR"
    else:
        tag = "   RELATED"
    print(f"{tag}")
    print(f"  {c['arxiv_id']}: {c['title']}")
    print(f"  Published: {c['published']} | Authors: {', '.join(c['authors'][:3])}")
    print(f"  Abstract: {c['abstract'][:250]}...")
    print()

print("""
## 2. WHAT EACH COMPETITOR DOES vs WHAT WE PLAN

| Paper (arXiv) | Focus | Method | What's Missing (our gap) |
|----------------|-------|--------|--------------------------|
""")

rows = [
    ("2412.04141", "Xu et al. — Reducing Tool Hallucination via Reliability Alignment",
     "Tool call hallucination — training-time alignment",
     "RLHF / reliability score",
     "Memory cascade not studied; single-turn only; no dataset for contamination"),
    ("2510.22977", "Yin et al. — The Reasoning Trap",
     "Reasoning amplifies tool hallucination",
     "Empirical observation across models",
     "No memory propagation analysis; no benchmark; no defense proposed"),
    ("2609.19425", "Iyer — Closed-World Resolution Against Tool Hallucination",
     "LLMs calling nonexistent tools",
     "Closed-world checking (schema validation)",
     "Only checks tool existence, not output fabrication; no memory effect"),
    ("2609.14758", "Sethi et al. — Fabrication After Tool Failure",
     "Post-failure fabrication behavior",
     "Benchmark of 1024 tool-failure items",
     "Single-turn only; no multi-step memory cascade; no long-horizon"),
    ("2607.22962", "Zhang & Li — ConsistencyGate",
     "Memory contamination prevention",
     "Self-consistency admission control",
     "Prevents writes to memory but doesn't measure cascade propagation"),
    ("2605.17830", "Al-Tawaha et al. — Remembering More, Risking More",
     "Longitudinal safety risks in memory-equipped agents",
     "Red-team safety (adversarial injection)",
     "Focus on adversarial attacks, not spontaneous hallucination cascade"),
    ("2609.09754", "Zhou et al. — LexAgentHallu",
     "Legal domain agent hallucination",
     "Hierarchical benchmark",
     "Domain-specific (legal); doesn't study tool output fabrication or memory"),
    ("2609.15319", "Sánchez — Clean Scores, Buried Evidence",
     "Agentic QA audit (receipt-based)",
     "Controlled audit protocol",
     "Doesn't study tool hallucination; focuses on evidence positioning"),
    ("2605.12240", "Yang et al. — No Action Without a NOD",
     "Long-horizon reliability in service agents",
     "Output checking / policy compliance",
     "Doesn't study hallucination specifically; no memory contamination"),
]

for arxiv_id, name, focus, method, missing in rows:
    print(f"| {arxiv_id} | {name} | {focus} | {method} | {missing} |")

print("""
## 3. PRECISE NOVELTY STATEMENT

After reviewing ALL competitor papers, here is EXACTLY what has NOT been done:

### NOT DONE (confirmed by literature review):
1. Multi-step cascade measurement — No paper measures how far one hallucinated
   tool call propagates through memory across N subsequent steps.
2. Tool output fabrication dataset — No benchmark exists where tool call outputs
   are classified as: fabricated, distorted, misattributed, or correct.
   (Fabrication After Tool Failure = 1024 items of failure-response pairs,
   but NOT multi-step cascading contamination).
3. Memory contamination index — No metric exists for "how much of an agent's
   memory is corrupted by one hallucinated tool output."
4. Long-horizon cascade taxonomy — No paper classifies cascade patterns
   (chain, branching, feedback-loop) in tool-using agents.
5. Cross-model comparison — No systematic comparison of hallucination cascade
   behavior across different LLM families (GPT, Claude, Qwen, DeepSeek).
6. Self-correction under cascade — No study measures whether agents can
   RECOVER from cascaded hallucination memory contamination.

### DONE (we must acknowledge and position against):
- Tool hallucination exists (Xu 2024, Yin 2025, Sethi 2026)
- Schema-based checking works (Iyer 2026)
- Memory contamination is possible (Zhang 2026)
- Long-horizon safety is a concern (Al-Tawaha 2026)
- Reasoning amplifies hallucination (Yin 2025)

### OUR POSITIONING:
"We extend beyond existing work by measuring and characterizing the PROPAGATION
DYNAMICS of tool hallucinations through agent memory in multi-step tasks, with
a new benchmark dataset and cascade-specific metrics."
""")

print("""
## 4. GITHUB / HuggingFace LANDSCAPE

### GitHub repos related (top):
""")

for q in github:
    print(f"Query '{q['query']}' → {q['total']} repos")
    for item in q.get("items", [])[:3]:
        print(f"  - {item['full_name']} ({item['stars']}★) {item['desc'][:70]}")
    print()

print("""
### HuggingFace datasets:
- marrita/toolace-tool-calling-hallucination-ragtruth → tool hallucination in RAG context
- Chennzi/llm-agent-hallucination → generic agent hallucination
- cemuluoglakci/hallucination_acceptance_agent_instruction_dataset → acceptance behavior
- rogue-security/mcp-tool-use-quality-benchmark → MCP tool quality

### VERDICT:
NO dataset on HuggingFace specifically for tool-output fabrication + memory cascade.
NO GitHub tool that verifies tool output integrity in agent loops at runtime.
(NOVELTY CONFIRMED — but narrow: the specific contribution is the cascade + memory angle)
""")