# CascToolBench: Measuring Tool-Output Hallucination Propagation Through Agent Memory

**Authors:** [TBD] · **Status:** DRAFT SKELETON v0.1 · **Date:** 2026-09-21

---

## Abstract (draft)

Tool-augmented LLM agents increasingly operate autonomously over long horizons, accumulating
tool results in persistent memory. Prior work establishes that tool hallucinations occur
(Xu et al., 2025) and that memory contamination is possible (Zhang & Li, 2026), but the
*propagation dynamics* of a single fabricated tool output through subsequent agent reasoning
remain unmeasured. We introduce **CascToolBench**, a benchmark of [N] multi-step tasks across
four difficulty tiers with controlled tool-failure injection, and a step-level annotation
pipeline that classifies each failed tool call as honestly handled or fabricated. We define
cascade-specific metrics — Cascade Depth (CD), Cascade Breadth (CB), Memory Contamination
Index (MCI), and Recovery Rate (RR) — and evaluate [M] frontier LLMs under identical failure
conditions. We find [FINDINGS TBD].

**Contributions:**
1. CascToolBench — first benchmark isolating tool-output fabrication *propagation* over multi-step trajectories.
2. Cascade metrics (CD, CB, MCI, RR) + step-level ground truth from an instrumented tool sandbox.
3. Cross-model comparison of fabrication and cascade behavior under matched failures.
4. An open-source runtime verifier (`cascverify`) for detecting tool-output fabrication in agent loops.

---

## 1. Introduction

### 1.1 Motivation
[Agents work autonomously for hours. One fabricated tool result becomes a false premise.]

### 1.2 The gap
| Prior work | What it established | What it left open |
|---|---|---|
| Xu et al. 2025 (Relign) | tool hallucination taxonomy, single-turn benchmark | multi-step propagation |
| Yin et al. 2025 (Reasoning Trap) | reasoning amplifies tool hallucination | explicitly: "multi-step tool chains where hallucination effects may compound" |
| Sethi et al. 2026 (Fabrication After Tool Failure) | single-turn fabrication benchmark, prompt-level fix | no memory, no cascade |
| Zhang & Li 2026 (ConsistencyGate) | write-time admission control | cascade dynamics after admission failure |
| Iyer 2026 (Closed-World) | schema-based tool-existence check | post-execution output fabrication |

### 1.3 Research questions
- **RQ1 (Prevalence):** How often do agents fabricate tool output after a failure?
- **RQ2 (Propagation):** How far does a single fabrication cascade through memory?
- **RQ3 (Recovery):** Can agents self-correct, and at what rate?
- **RQ4 (Patterns):** What cascade shapes emerge (chain / branching / scattered / contained)?
- **RQ5 (Cross-model):** How do fabrication and cascade behavior differ across model families?

---

## 2. Related Work
[Auto-populate from references/scopus_references.csv + 9 downloaded competitor papers]

## 3. CascToolBench

### 3.1 Instrumented tool sandbox
12 tools with deterministic failure injection; every call logged as ground truth.
Failure modes: `error`, `empty`, `garbage`, `timeout`.

### 3.2 Task suite
| Tier | Steps | Failures | # Tasks | Purpose |
|------|-------|----------|---------|---------|
| T1 Basic | 1–2 | 1 one-shot | 10 | single failure → retry or fabricate |
| T2 Standard | 6–8 | 1 | 2 | basic contamination |
| T3 Complex | 11 | 2 | 10 | chained cascade |
| T4 Long-horizon | 35 | 4 multi-tool | 5 | poison-seed maximum cascade |
| P5 Persistent | 12 | 1 tool fails **every** call | 5 | persistent-failure fabrication trigger (cf. Sethi et al. 2026) |

**Total 32 tasks.** P5 was added after pilots showed one-shot failures are
recoverable by retrying (FR=0% pilot artifact); persistent failures are the
documented fabrication trigger and form the stress tier of the benchmark.

**Error realism requirement (simulation validity):** injected error messages
interpolate the agent's *actual arguments* (e.g. `DatabaseError: near "SELECT
* FROM finance": syntax error`), so failures are indistinguishable from real
tool rejections. Generic errors let the model trivially infer "the tool is
broken" and behave artificially conservative — observed in pilot v1 and fixed.

### 3.3 Trace format
Per step: LLM content/reasoning, tool calls, tool results (ground truth), memory snapshot,
actual served model. [See cascverify/runner.py]

### 3.4 Annotation protocol
Fabrication judged ONLY on text produced *after* the failed call (validity fix).
Label set: honest / fabricated / hedged. Ambiguous cases → LLM judge, human-validated on a sample.

---

## 4. Metrics
TOI, FR, MCI, CD, CB, RR — definitions in `EXPERIMENT_DESIGN.md` §5 and `cascverify/metrics.py`.

---

## 5. Experiments

### 5.1 Setup
- Models: [tokenharbor combo → served models recorded per request]
- Seeds: [1,2,3] · Tasks: [N] · Failure configs: [matched]

### 5.2 Main results
[TABLE: model × tier → FR, MCI, avgCD, maxCD, RR — to be filled after full run completes]

#### Interim observations (n=4 runs; full benchmark in progress)
All three tiers completed so far show FR=0%: the served model(s) consistently chose honest
failure handling over fabrication when tool errors were explicit. Notably, persistent
injected failure (P5 tier, n=1, 44 calls) also produced FR=0%: the agent reported
"...the database tool is non-functional" rather than fabricating missing data. Two
non-...[truncated]

### 5.3 Cascade patterns
[FIGURE: pattern distribution per tier]

### 5.4 Qualitative examples
[Trace excerpt: one fabrication → 9 downstream contaminated steps]

---

## 6. Discussion
[Why cascade matters: production agents, cost of false premises, verification overhead]

## 7. Limitations
- Single tool-sandbox family; synthetic tools (mitigated by realistic error interpolation).
- Combo routing serves different models per request; mitigated by recording the served
  model per request and post-stratifying results (`analyze_results.py`).
- Judge-based labeling for ambiguous cases (validated on subset).
- Model coverage limited by available inference budget (free-tier models).

## 8. Conclusion
[To be written from results.]

---

## Appendix
- A. Full task list
- B. Judge prompts
- C. Per-task results table
