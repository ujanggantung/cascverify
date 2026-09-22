# Competitive Landscape & Novelty Verdict
## Persistent Tool Hallucinations: Memory Cascade
**Status: VERIFIED — September 21, 2026**
**Source: Scopus API (166 refs) + arXiv (9 full PDFs read) + GitHub (1000+ repos) + HuggingFace (5 datasets)**

---

## 1. Full Competitor Map (9 Papers, All Downloaded + Read)

### Tier 1: DIRECT COMPETITORS (must acknowledge and position against)

#### 1A. "Reducing Tool Hallucination via Reliability Alignment" (Xu et al., PMLR 2025, arXiv:2412.04141)
- **What they do:** Define tool hallucination (2 types, 4 subtypes). Create RelyToolBench + RePR metric. Propose Relign framework (training-time alignment).
- **Limitations (their own + confirmed by reading):**
  - **Single-turn only** — no multi-step chain, no memory accumulation
  - No study of what happens AFTER a hallucinated tool call persists
  - Benchmark is tool-selection + tool-argument correctness, not output fabrication
- **Gap we fill:** Their hallucinated tool call at step 3 → what happens at step 50?

#### 1B. "ConsistencyGate: Preventing Memory Contamination" (Zhang & Li, arXiv:2607.22962)
- **What they do:** Write-time admission control for agent memory. Self-consistency scoring. MemContam dataset (200 samples).
- **Limitations (their own):**
  - Focuses on **whether to admit** facts into memory, not on **how contamination cascades** after admission
  - Their own future work explicitly calls for "multi-hop verification" — this IS our contribution
  - Recall drops on real conversations (0.58) vs synthetic (1.00) — their method is incomplete
- **Gap we fill:** They prevent contamination at write time. We **measure and characterize** what happens when prevention fails — the cascade dynamics.

#### 1C. "Fabrication After Tool Failure" (Sethi et al., arXiv:2609.14758)
- **What they do:** 1024-item benchmark. Labels fabrication after tool failure. Prompt-level defense (retrieval_status flag reduces dishonesty from 14% to 0.87%).
- **Limitations (their own):**
  - **Single-turn only** — no multi-step task
  - No memory mechanism at all
  - No cascade analysis
- **Gap we fill:** They study one step (tool fails → what does agent say). We study N steps (tool fails → memory contamination → step N+1, N+2, ... → cascading failures).

#### 1D. "The Reasoning Trap" (Yin et al., arXiv:2510.22977)
- **What they do:** Show reasoning-focused RL amplifies tool hallucination. SimpleToolHalluBench diagnostic.
- **Limitations (their own, verbatim):**
  > "our benchmark focuses on single-step tool invocation scenarios; real-world agentic systems often involve multi-step tool chains where hallucination effects may compound"
- **Gap we fill:** Exactly what they acknowledge is missing — multi-step compounding.

#### 1E. "Closed-World Resolution Against Tool Hallucination" (Iyer, arXiv:2609.19425)
- **What they do:** 5-class taxonomy (H1-H5). Resolution Rung — schema-based checker that verifies tool existence + argument types.
- **Limitations:**
  - Checks if tool EXISTS and arguments VALID, but does NOT check if the OUTPUT is fabricated
  - Single-turn verification, no memory
- **Gap we fill:** Tool output fabrication (post-execution) + memory contamination, not just schema validation.

### Tier 2: RELATED COMPETITORS

#### 2A. "LexAgentHallu" (Zhou et al., arXiv:2609.09754)
- Legal domain, 3414 instances, dual-layer taxonomy. Domain-specific — doesn't study tool output fabrication or external memory. Relevant for methodology借鉴.

#### 2B. "Remembering More, Risking More" (Al-Tawaha et al., arXiv:2605.17830)
- Longitudinal safety in memory agents — adversarial injection focus, NOT spontaneous hallucination cascade. Relevant for safety framing.

#### 2C. "No Action Without a NOD" (Yang et al., arXiv:2605.12240)
- Output checking for service agents. General reliability framing, not hallucination-specific.

---

## 2. GitHub/HuggingFace Audit (VERIFIED)

### What EXISTS (must not duplicate):

| Repository | Stars | What it does | What it doesn't |
|------------|-------|-------------|-----------------|
| exa-labs/exa-hallucination-detector | 332★ | RAG output hallucination check | Not tool-use, no memory, no cascade |
| linghungegeg/Linghun | 459★ | Coding runtime with grounding | Not a benchmark/dataset |
| Tencent/AI-Infra-Guard | 6510★ | Red teaming platform | General, not tool-hallucination specific |
| hashgraph-online/hol-guard | 638★ | Agent risk blocker | Blocks risky tools, doesn't verify output |
| abluva/mcp-trust-plane | 100★ | MCP data security | Privacy, not hallucination |
| Accenture/mcp-bench | 508★ | MCP agent benchmark | Task completion, not hallucination detection |
| zkortam/wingman | 4★ | Tool-using agent review | Verdict: too early, incomplete |
| aaFrostnova/CiteTracer | 12★ | Citation hallucination detection | Domain-specific (citations) |
| happyahluwalia/agent-memory-contamination | 0★ | Memory contamination | Repo exists but EMPTY (0★, no content) |

### What EXISTS on HuggingFace:

| Dataset | What it does | What it doesn't |
|---------|-------------|-----------------|
| marrita/toolace-tool-calling-hallucination-ragtruth | Tool hallucination in RAG | Not multi-step, no memory |
| Chennzi/llm-agent-hallucination | Generic agent hallucination | Not tool-output specific |
| rogue-security/mcp-tool-use-quality-benchmark | MCP tool quality | Quality ≠ hallucination |

### What DOES NOT EXIST (our novelty):

1. **No benchmark** measuring tool-output fabrication across multi-step trajectories
2. **No dataset** with step-level tool call traces + contamination annotations
3. **No metric** for cascade depth (how far one hallucination propagates)
4. **No dataset** combining: tool call log + memory state + contamination labels
5. **No GitHub tool** for real-time tool output verification in agent loops
6. **No cross-model comparison** of hallucination cascade behavior

---

## 3. HONEST NOVELTY STATEMENT

### What is NOVEL (confirmed):
> We propose **CascToolBench**, a benchmark and analysis framework for measuring how tool-output hallucinations propagate through agent memory in multi-step tasks. Unlike prior work that studies tool hallucination in single turns (Xu 2024, Yin 2025, Sethi 2026), we:
> 1. Introduce a **multi-step trace dataset** where each step records tool call, output, memory state, and contamination labels
> 2. Define **cascade-specific metrics**: Cascade Depth (CD), Memory Contamination Index (MCI), Recovery Rate (RR)
> 3. Classify **cascade propagation patterns** (chain, branching, feedback-loop)
> 4. Provide **cross-model comparison** across LLM families under identical tool-failure conditions
> 5. Release a **runtime tool-output verifier** as open-source tool for Hermes/agent frameworks

### What is NOT novel (must acknowledge):
- Tool hallucination as a phenomenon → already documented (Xu, Yin, Sethi)
- Memory contamination in agents → already studied (Zhang, Al-Tawaha)
- Schema-based tool verification → already proposed (Iyer)

### Our exact positioning:
> "Prior work establishes that tool hallucinations exist and that memory contamination is possible. What remains unmeasured is the **propagation dynamics**: given a single hallucinated tool output injected into agent memory, how does the error cascade through subsequent steps, and can agents self-correct? We provide the first systematic study of this question."

---

## 4. RECOMMENDED TARGET VENUES

Based on competitive landscape:

| Venue | Fit | Deadline | Why |
|-------|-----|----------|-----|
| **ACL 2027** | Excellent | ~Jan 2027 | Tool use + agents is main track |
| **EMNLP 2027** | Excellent | ~Jun 2027 | Empirical (benchmark/dataset paper) |
| **NAACL 2026/27** | Good | TBD | NLP + practical agents |
| **COLM 2026** | Good | TBD | Language modeling + agents |
| **NeurIPS 2027 Datasets Track** | Good | ~May 2027 | If benchmark is the main contribution |

---

## 5. REFERENCE COUNTS (Scopus, Sept 2026)

| Search query | Scopus results |
|-------------|----------------|
| "tool hallucination" (TITLE-ABS-KEY) | 4 |
| hallucination + "tool use" + LLM | 36 |
| "agent memory" OR "memory contamination" + LLM | 238 |
| "tool use" + (benchmark) + LLM | 200 |
| "prompt injection" + defense + LLM | 264 |
| "model context protocol" | 588 |
| Total unique references collected | 166 |

All saved in: `references/scopus_references.csv`
All 9 competitor PDFs downloaded in: `references/pdfs/`

---

*Generated from verified Scopus API queries, Semantic Scholar API, GitHub REST API,
HuggingFace API, and full-text PDF analysis of 9 key competitor papers.*
