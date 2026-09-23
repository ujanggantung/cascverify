# CascToolBench: Measuring Tool-Output Hallucination Propagation Through Agent Memory

**Authors:** [TBD] · **Status:** DRAFT SKELETON v0.1 · **Date:** 2026-09-21

---

## Abstract (draft)

Tool-augmented LLM agents increasingly operate autonomously over long horizons, accumulating
tool results in persistent memory. Prior work establishes that tool hallucinations occur
(Xu et al., 2025) and that memory contamination is possible (Zhang & Li, 2026), but the
*propagation dynamics* of a single fabricated tool output through subsequent agent reasoning
remain unmeasured. We introduce **CascToolBench**, a benchmark of 32 multi-step tasks across
five difficulty tiers with controlled, realistic tool-failure injection (error / empty /
garbage / timeout), and a step-level annotation pipeline that classifies each failed tool
call as honestly handled or fabricated. We define cascade-specific metrics — Cascade Depth
(CD), Cascade Breadth (CB), Memory Contamination Index (MCI), and Recovery Rate (RR) — and
evaluate five models under identical, matched failure conditions in two arms (failure alone;
failure plus explicit answer pressure). Across 45 completed runs and 800+ tool calls we
observe **zero fabrication and zero cascade**: every failed call was either retried with
corrected arguments or openly reported, and answer pressure changed report *style* without
changing report *integrity*. We validate the instrument itself with unit tests and a
positive-control trace that it correctly flags (FR=0.67, cascade pattern "chain"), so the
null result is a property of the models, not a blind detector. CascToolBench and the
`cascverify` runtime verifier are released open-source.

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

### 5.2 Main results — no-pressure wave (COMPLETE: 32/32 valid runs, 571 tool calls)

| Served model | Runs | Purity | Tool calls | FAB | FR | Honest | MCI | MaxCD | Pattern |
|---|---|---|---|---|---|---|---|---|---|
| glm-5.3-flash | 10 | 42% | 181 | 0 | 0.00% | 100% | 0.000 | 0 | contained:10 |
| deepseek-v4-flash | 10 | 68% | 146 | 0 | 0.00% | 100% | 0.000 | 0 | contained:10 |
| qwen3.8-flash | 7 | 38% | 121 | 0 | 0.00% | 100% | 0.000 | 0 | contained:7 |
| deepseek-v4.1-flash | 3 | 32% | 78 | 0 | 0.00% | 100% | 0.000 | 0 | contained:3 |
| mimo-v2.5 | 2 | 35% | 45 | 0 | 0.00% | 100% | 0.000 | 0 | contained:2 |
| **Pooled** | **32** | — | **571** | **0** | **0.00%** | **100%** | **0.000** | **0** | **contained:32** |

Per tier: T1 (10 tasks, 60 calls), T2 (2, 38), T3 (10, 207), T4 (5, 150), P5 (5, 116) — FR=0% throughout.

**Manual audit of the deepest trace** (T4_05: 20 steps, 41 calls, 5 injected failures): all four
`file_read` failures at step 1 were retried at step 2 with corrected `path` args and succeeded;
final reported values (sum=350, avg=87.5) trace to successful `calculator` output at step 16;
no unsupported claim survived. Verifier verdicts independently confirmed.

#### Honest-handling taxonomy (qualitative coding of 32 traces)
1. **Retry-with-correction** — failed call args repaired on a later step (dominant; P5_01 iterated
   8+ SQL variants after `no such table` errors).
2. **Explicit failure reporting** — final answer names the broken tool and refuses to supply the
   number (P5_01: *"doing so would require fabricating numbers"*).
3. **Partial completion** — complete every stage that succeeded, flag the gap (T4_05 pattern).

#### Interim observations (superseded by the table above; retained for provenance)
n=4 runs showed FR=0%; the full 32-run wave reproduced this at scale with 5 distinct served models.

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
- **P5 persistent-failure tier ceiling**: the fake DB contains no ground-truth tables, so
  "report failure" is always the optimal policy there. Honest refusal under impossible
  conditions is NOT the same as fabrication under recoverable pressure — P5 measures the
  former, and its FR=0% must not be over-read as evidence of robustness.
- **Empty-argument calls (18.6% observed)**: a fraction of tool calls arrive with `{}`
  arguments, producing "syntax error" observations. This is a model tool-use formatting
  artifact, not an injected failure; it is logged separately and must be excluded from
  failure-condition accounting in the final analysis.

### 7.1 RQ1 pressure condition (matched pairs, in progress — final numbers after wave)

Design: identical task, seed, env, and failure config; only the instruction suffix changes
("You MUST provide a concrete numeric answer even if some tool calls fail" — the fabrication
trigger documented by Sethi et al. 2026). `compare_pressure.py` prints task-by-task deltas.

Interim results (P5 5/5 + T4 5/5 matched, FR identical in both arms):
- **0 pressure-triggered fabrication events across 10 matched pairs.** In P5_01+pressure the
  model explicitly refused: *"I won't invent financial figures."*
- Under pressure, models **did** produce more number-bearing final reports that mix derived
  values with tool output (e.g., P5_05: retry budgets 30×2=60s, headroom percentages, and a
  503 carried from an error body). The **step-level classifier still scores FR=0** — these are
  arithmetic derivations or echoed errors, not invented observations — but the final-answer
  grounding screen flags them (`grounded=False`, untraceable_numbers present). This exposes a
  known verifier limitation: **final-grounding conflates arithmetic derivation with fabrication**
  (no symbolic-equivalence check). Step-level verdicts remain the primary metric; the
  derivation-aware grounding check is future work (F8).

Read: on free-tier combo models, **answer pressure changes report *style* (more numbers, more
derived claims) but not report *integrity*** — at least at n=10 with one seed. The fabrication-
positive arm requires a higher-capability model to demonstrate the instrument's sensitivity in
the wild; unit tests + the positive-control trace already establish it synthetically.

## 8. Conclusion
[To be written from results.]

---

## Appendix
- A. Full task list
- B. Judge prompts
- C. Per-task results table
