# CascToolBench v0.1.1

## What's New

### Input-Granding Verifier (F8)
- `check_input_grounding(run_result, {instruction})` — detects **hallucinated tool INPUTS**
  (invented parameters), the class invisible to output-side verifiers.
- Stats: FR=0/247 (0% output fab) vs IFR=3/54 (5.6% input fab)
- `--pressure` arm rate: 2/22 (9.1%) vs no-pressure 1/32 (3.1%)
- Derivation-aware: ±-closure absorbs arithmetic premises like 75=100-25.

### RQ2 Cross-Session Memory Cascade
- `run_memory_cascade.py` — two-session handoff protocol (Session A broken → B healthy).
- `--append` flag accumulates pairs without overwriting previous runs.
- `rescore_cascade.py` — derivation-aware v2 scorer (fixes v1 over-flagging).
- Key finding: invented uptime parameter (720/5.2/3.4) propagated through a
  verify-first Session B that made 27 healthy tool calls.

### Bug Fixes
- Void detection: `[AGENT_ERROR step 0: ...]` now caught (previously escaped prefix check).
- Model slug sanitization: `/` in model names no longer creates broken file paths.
- T3_07-10 pressure runs re-executed (previously void but marked done).

### Tests
- 9/9 verifier tests pass (was 5/5):
  - 4 new: `test_input_grounding_flags_invented_parameter`,
    `test_input_grounding_allows_grounded_values`,
    `test_input_grounding_allows_benign_and_instruction`,
    `test_input_grounding_allows_arithmetic_derivation`
- Positive-control trace: FR=0.67, cascade pattern "chain" (verifier fires correctly).

## Dataset
- 54 main-benchmark runs (32 no-pressure + 22 pressure), 915 tool calls
- 6 RQ2 handoff pairs (P5_01-P5_05 x seed1 + P5_03 x seed2), audited carry = 1/6 (P5_03 s1); v2 scorer flags 3/6 with 2 known FP

## Paper Status
- §5.2 final results table, §5.5 failure-mode distribution
- §7.2 RQ2 cross-session cascade (worked example with manual audit trail)
- §7.3 RQ1 pressure condition (22/22 matched pairs, 0 fabrication events)
- §8 conclusion written
