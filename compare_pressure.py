#!/usr/bin/env python3
"""RQ1 matched-pair comparison: no-pressure vs pressure, task-by-task.

The two waves share identical tasks, seeds, env, and failure configs — they
differ ONLY in the injected answer-pressure suffix. So each task is its own
control. This prints, per task: tool calls, failed calls, fabrications, FR,
and whether the final answer asserted a concrete number despite tool failure.

Usage: python compare_pressure.py
"""
import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")


def load():
    """Return {task_id: {'plain': run, 'pressure': run}}."""
    pairs = defaultdict(dict)
    for fn in glob.glob(os.path.join(RESULTS, "*__*.json")):
        if "legacy" in fn:
            continue
        try:
            r = json.load(open(fn, encoding="utf-8"))
        except Exception:
            continue
        tid = r.get("task_id")
        if not tid:
            continue
        cond = "pressure" if r.get("pressure") else "plain"
        pairs[tid][cond] = r
    return pairs


def summarize(r):
    cl = r.get("classification", {})
    o = cl.get("overall", {})
    fg = cl.get("final_grounding", {})
    # does the final answer assert a concrete number NOT traceable to a tool?
    untrace = fg.get("untraceable_numbers", []) or []
    # filter out task-id-ish / year-like noise the same way the verifier does
    hard = [n for n in untrace if not str(n).startswith(("T1", "T2", "T3", "T4", "P5"))]
    return {
        "calls": o.get("total_tool_calls", 0),
        "failed": o.get("failed_calls", 0),
        "fab": o.get("fabricated_count", 0),
        "fr": o.get("fabrication_rate", 0.0),
        "mci": o.get("memory_contamination_index", 0.0),
        "cd": cl.get("cascade_analysis", {}).get("cascade_depth", 0),
        "untrace": len(hard),
    }


def main():
    pairs = load()
    both = sorted(t for t, d in pairs.items() if "plain" in d and "pressure" in d)
    only_plain = sorted(t for t, d in pairs.items() if "plain" in d and "pressure" not in d)
    only_press = sorted(t for t, d in pairs.items() if "pressure" in d and "plain" not in d)

    print("=" * 78)
    print(" RQ1 MATCHED PAIR: no-pressure vs pressure (same task/seed/env/failures)")
    print("=" * 78)
    print(f"matched pairs: {len(both)} | pressure-only (pending): {len(only_press)} "
          f"| plain-only (pending): {len(only_plain)}")
    print()
    hdr = (f"{'task':8s} | {'calls p/pr':11s} | {'fail p/pr':9s} | "
           f"{'fab p/pr':8s} | {'FR p→pr':11s} | {'CD p/pr':7s} | Δuntrace")
    print(hdr)
    print("-" * len(hdr))

    agg = {"plain": defaultdict(float), "pressure": defaultdict(float)}
    n_fab_flip = 0  # tasks where pressure turned a fabrication on but plain had none
    for tid in both:
        a = summarize(pairs[tid]["plain"])
        b = summarize(pairs[tid]["pressure"])
        for k in ("calls", "failed", "fab", "fr", "mci", "cd", "untrace"):
            agg["plain"][k] += a[k]
            agg["pressure"][k] += b[k]
        flip = " <== PRESSURE-TRIGGERED FAB" if (b["fab"] > 0 and a["fab"] == 0) else ""
        if flip:
            n_fab_flip += 1
        print(f"{tid:8s} | {a['calls']:4d}/{b['calls']:<5d} | {a['failed']:3d}/{b['failed']:<4d} | "
              f"{a['fab']:3d}/{b['fab']:<4d} | {a['fr']:.2f}→{b['fr']:.2f} | "
              f"{a['cd']:2d}/{b['cd']:<4d} | {b['untrace'] - a['untrace']:+d}{flip}")

    n = max(len(both), 1)
    print("-" * len(hdr))
    print(f"{'POOLED':8s} | {agg['plain']['calls']/n:4.1f}/{agg['pressure']['calls']/n:<5.1f} | "
          f"{agg['plain']['failed']/n:3.1f}/{agg['pressure']['failed']/n:<4.1f} | "
          f"{agg['plain']['fab']/n:3.1f}/{agg['pressure']['fab']/n:<4.1f} | "
          f"FR {agg['plain']['fab']/max(agg['plain']['calls'],1):.3f}→"
          f"{agg['pressure']['fab']/max(agg['pressure']['calls'],1):.3f} | "
          f"{'':7s} | meanΔ={agg['pressure']['untrace']/n - agg['plain']['untrace']/n:+.2f}")
    print()
    print(f"pressure-triggered fabrication events: {n_fab_flip} / {len(both)} matched tasks")
    if n_fab_flip == 0 and len(both) > 0:
        print("=> HONEST NULL: answer pressure did not raise fabrication in this model set.")
        print("   Caveat for write-up: needs a high-capability model as the fabrication-positive")
        print("   arm; free-tier combo models appear robust (refuse-to-invent) at this scale.")


if __name__ == "__main__":
    main()
