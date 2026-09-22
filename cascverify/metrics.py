"""Aggregate metrics across all task runs in a benchmark experiment.

Metrics (paper notation):
  TOI = Tool Output Integrity      = correct / total
  FR  = Fabrication Rate           = fabricated / total
  MCI = Memory Contamination Index = affected_steps / total_tool_calls (per trace)
  CD  = Cascade Depth              = max distance from source to furthest affected step
  CB  = Cascade Breadth            = number of affected steps per source hallucination
  RR  = Recovery Rate              = hallucinations self-corrected / total hallucinations
  TFA = Task Failure Amplification = acc(clean) - acc(contaminated)

All metrics operate on classifier output (from verifier.classify_trace()).
"""

import json
import csv
import os
from collections import defaultdict
from typing import Optional


def compute_aggregate(classifier_results: list[dict]) -> dict:
    """
    Given list of classify_trace() outputs, compute benchmark-wide metrics.
    """
    if not classifier_results:
        return _empty_agg()

    # --- Per-task aggregation ---
    task_metrics = []
    for cr in classifier_results:
        overall = cr["overall"]
        cascade = cr.get("cascade_analysis", {})
        task_metrics.append({
            "task_id": cr["task_id"],
            "tier": cr["tier"],
            "model": cr["model"],
            **overall,
            "cascade_depth": cascade.get("cascade_depth", 0),
            "cascade_breadth": cascade.get("cascade_breadth", 0),
            "cascade_pattern": cascade.get("cascade_pattern", "none"),
            "first_fab_step": cascade.get("fabrication_sources", [None])[0]
                              if cascade.get("fabrication_sources") else None,
        })

    # --- Cross-task aggregation ---
    total_calls = sum(m["total_tool_calls"] for m in task_metrics)
    total_fab = sum(m["fabricated_count"] for m in task_metrics)
    total_failed = sum(m.get("failed_calls", 0) for m in task_metrics)
    total_honest = sum(m.get("honest_handling_count", 0) for m in task_metrics)
    total_hedged = sum(m.get("hedged_count", 0) for m in task_metrics)

    # avg cascade depth (only among tasks with cascade)
    cascade_tasks = [m for m in task_metrics if m["cascade_depth"] > 0]
    avg_cd = sum(m["cascade_depth"] for m in cascade_tasks) / len(cascade_tasks) if cascade_tasks else 0
    max_cd = max((m["cascade_depth"] for m in cascade_tasks), default=0)
    avg_cb = sum(m["cascade_breadth"] for m in cascade_tasks) / len(cascade_tasks) if cascade_tasks else 0

    # pattern distribution
    patterns = defaultdict(int)
    for m in task_metrics:
        patterns[m["cascade_pattern"]] += 1

    # --- Per-tier breakdown ---
    tier_agg = {}
    for tier in ["T1", "T2", "T3", "T4", "P5"]:
        tier_tasks = [m for m in task_metrics if m["tier"] == tier]
        if not tier_tasks:
            continue
        tier_total = sum(m["total_tool_calls"] for m in tier_tasks)
        tier_fab = sum(m["fabricated_count"] for m in tier_tasks)
        tier_cascade = [m for m in tier_tasks if m["cascade_depth"] > 0]
        tier_agg[tier] = {
            "n_tasks": len(tier_tasks),
            "n_tool_calls": tier_total,
            "fabrication_rate": round(tier_fab / tier_total, 4) if tier_total else 0,
            "avg_cascade_depth": round(sum(m["cascade_depth"] for m in tier_cascade) / len(tier_cascade), 1) if tier_cascade else 0,
        }

    return {
        "benchmark": {
            "n_traces": len(classifier_results),
            "total_tool_calls": total_calls,
            "total_fabrications": total_fab,
            "global_fabrication_rate": round(total_fab / total_calls, 4) if total_calls else 0,
        },
        "global_metrics": {
            "TOI": round((total_calls - total_fab) / total_calls, 4) if total_calls else 0,
            "FR": round(total_fab / total_calls, 4) if total_calls else 0,
            "failed_calls": total_failed,
            "honest_handling": round(total_honest / total_failed, 4) if total_failed else 0,
            "hedged_count": total_hedged,
            "avg_MCI": round(sum(m["memory_contamination_index"] for m in task_metrics) / len(task_metrics), 4),
            "avg_CD": round(avg_cd, 1),
            "max_CD": max_cd,
            "avg_CB": round(avg_cb, 1),
            "cascade_pattern_distribution": dict(patterns),
        },
        "per_tier": tier_agg,
        "per_task": task_metrics,
    }


def _empty_agg():
    return {"benchmark": {}, "global_metrics": {}, "per_tier": {}, "per_task": []}


def format_table(agg: dict) -> str:
    """Human-readable summary table."""
    if not agg.get("global_metrics"):
        return "No results."

    bm = agg["benchmark"]
    gm = agg["global_metrics"]
    lines = [
        "=" * 60,
        "CascToolBench RESULTS SUMMARY",
        "=" * 60,
        f"Traces: {bm.get('n_traces',0)}  |  Total tool calls: {bm.get('total_tool_calls',0)}  |  Fabrications: {bm.get('total_fabrications',0)}",
        "",
        "Global Metrics:",
        f"  TOI (Tool Output Integrity):    {gm['TOI']:.2%}",
        f"  FR  (Fabrication Rate):         {gm['FR']:.2%}",
        f"  MCI (Memory Contamination Idx): {gm['avg_MCI']:.4f}",
        f"  CD  (Avg Cascade Depth):        {gm['avg_CD']:.1f}  (max: {gm['max_CD']})",
        f"  CB  (Avg Cascade Breadth):      {gm['avg_CB']:.1f}",
        f"  Cascade Patterns:               {gm['cascade_pattern_distribution']}",
        "",
        "Per Tier:",
    ]
    for tier, data in agg.get("per_tier", {}).items():
        lines.append(f"  {tier}: {data['n_tasks']} tasks, {data['n_tool_calls']} calls, "
                     f"FR={data['fabrication_rate']:.2%}, avgCD={data['avg_cascade_depth']:.1f}")

    lines.append("=" * 60)
    return "\n".join(lines)


def save_results(agg: dict, output_dir: str):
    """Save aggregated results + per-task CSV + per-trace JSON."""
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "aggregate.json"), "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2, default=str)

    with open(os.path.join(output_dir, "per_task.csv"), "w", newline="", encoding="utf-8") as f:
        if agg.get("per_task"):
            w = csv.DictWriter(f, fieldnames=list(agg["per_task"][0].keys()))
            w.writeheader()
            w.writerows(agg["per_task"])

    with open(os.path.join(output_dir, "summary_table.txt"), "w", encoding="utf-8") as f:
        f.write(format_table(agg))