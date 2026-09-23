# CascToolBench: Measuring Tool-Output Hallucination Propagation Through Agent Memory

**Status:** ⚠️ NOVELTY VERIFIED + Infrastructure complete — benchmark running
**Start:** 2026-09-21
**Current:** Smoke-testing P5 (persistent-failure tier)
**Project dir:** `F:\JURNAL MULAI SEKRANG\01-tool-hallucination-memory-cascade`

## Quick Start

```bash
# Full run (all 32 tasks, 3 seeds, ~8h on free API)
bash run_all.sh tokenharbor 1,2,3

# Single tier
python run_benchmark.py --tasks T1 --seeds 1 --timeout 200

# Persistent-failure (fabrication trigger tier)
python run_benchmark.py --tasks P5 --seeds 1 --timeout 200

# Analysis (per-served-model post-stratification)
python analyze_results.py
```

## Key Design Decision: P5 tier

Tier P5 was added because pilot runs (T1, T2) showed **0% fabrication rate** —
not because of the research hypothesis, but because one-shot failures are
recoverable by retrying. Sethi et al. (2026) showed that persistent failures
(never-resolving) are the documented fabrication trigger. P5 tier implements
this: one tool fails on EVERY call for the entire task.

## Tier overview

| Tier | Tasks | Steps | Failures | Cascade design |
|------|-------|-------|----------|----------------|
| T1 | 10 | 1–2 | 1 (one-shot) | Basic: failure → retry → success |
| T2 | 2 | 6–8 | 1 | Standard contamination |
| T3 | 10 | 11 | 2 | Complex cascade |
| T4 | 5 | 35 | 4 (multi-tool) | Long-horizon, early/mid/late poison |
| **P5** | **5** | **12** | **1 persistent** | **Fabrication trigger (Sethi 2026)** |

## Known API issue (9router)

- `HERMES_CUSTOM_HERMES_API_KEY` env var = auth to localhost:20128
- `tokenharbor` combo: routes dynamically (glm-5.3-flash/deepseek/mimo/qwen), no deterministic model
- C2PA `_manifest` prefix in responses: `strip_manifest()` handles it
- Free routes flaky (429, timeouts): `LLMClient` retries 5x with exponential backoff

## Methodology

- Model served per request recorded via `response.model` → post-stratification possible
- Classifier validated: 9/9 unit tests pass (synthetic traces, known ground truth)
- Pressure condition via `--pressure` flag (Sethi 2026 prompt-level treatment)
- Persistent failure via `persistent: true` in failure_plan (env support)
- Two verifier axes: **FR** (output-side, fabricated tool results) and **IFR**
  (input-side, hallucinated tool parameters via `check_input_grounding`)
- RQ2 cross-session handoff: `run_memory_cascade.py` (Session A broken env → report →
  Session B fresh agent, healthy env, verify-first prompt)
