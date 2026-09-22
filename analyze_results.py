"""Analyze results/ with per-served-model post-stratification.

The 'tokenharbor' combo routes each request dynamically (glm-5.3-flash,
deepseek-v4.1-flash, mimo-v2.5, ...). Every run records the ACTUAL served
model per step. Honest methodology = group results by the served model
dominant in that run, not by the combo alias.

Outputs:
  results/analysis_per_served_model.json
  results/analysis_table.txt
  results/patterns_breakdown.json
  + prints a ready-to-paste markdown table
"""

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cascverify.metrics import compute_aggregate

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def load_runs():
    runs = []
    for fn in sorted(os.listdir(RESULTS)):
        if fn.endswith(".json") and fn != "aggregate.json":
            p = os.path.join(RESULTS, fn)
            try:
                with open(p, encoding="utf-8") as f:
                    r = json.load(f)
                if isinstance(r, dict) and "task_id" in r:
                    runs.append(r)
            except Exception:
                continue
    return runs


def served_model_of(run):
    """Dominant actual served model across steps of a run."""
    models = [s.get("llm_model") for s in run.get("steps", []) if s.get("llm_model")]
    if not models:
        return "unknown"
    return Counter(models).most_common(1)[0][0]


def run_model_purity(run):
    """Fraction of steps served by the dominant model (data-quality signal)."""
    models = [s.get("llm_model") for s in run.get("steps", []) if s.get("llm_model")]
    if not models:
        return 0.0
    top = Counter(models).most_common(1)[0][1]
    return round(top / len(models), 3)


def main():
    runs = load_runs()
    if not runs:
        print("No result files yet in results/")
        return

    # attach served-model info + re-verify classification is present
    by_served = defaultdict(list)
    skipped = []
    for r in runs:
        cls = r.get("classification")
        if not isinstance(cls, dict) or "overall" not in cls:
            skipped.append(r.get("task_id", "?"))
            continue
        sm = served_model_of(r)
        purity = run_model_purity(r)
        r["_served_model"] = sm
        r["_model_purity"] = purity
        by_served[sm].append(r)

    n_completed_tiers = Counter(r.get("tier", "?") for r in runs)
    print(f"Runs loaded: {len(runs)} | skipped (no classification): {len(skipped)}")
    print(f"Tier coverage: {dict(n_completed_tiers)}")
    print(f"Served models observed: {sorted(by_served)}")
    print()

    # aggregate per served model
    per_model = {}
    for sm, group in sorted(by_served.items()):
        agg = compute_aggregate([g["classification"] for g in group])
        per_model[sm] = {
            "n_runs": len(group),
            "task_ids": [g["task_id"] for g in group],
            "avg_model_purity": round(sum(g["_model_purity"] for g in group) / len(group), 3),
            "benchmark": agg["benchmark"],
            "global_metrics": agg["global_metrics"],
            "per_task": agg["per_task"],
        }

    # global over everything
    global_agg = compute_aggregate([r["classification"] for r in runs
                                    if isinstance(r.get("classification"), dict)])

    # cascade pattern breakdown (only fabricated runs)
    fab_runs = [r for r in runs
                if r.get("classification", {}).get("overall", {}).get("fabricated_count", 0) > 0]
    pattern_counter = Counter(
        r["classification"]["cascade_analysis"].get("cascade_pattern", "?") for r in fab_runs)

    cd_list = [r["classification"]["cascade_analysis"].get("cascade_depth", 0) for r in fab_runs]
    mci_list = [r["classification"]["overall"].get("memory_contamination_index", 0) for r in runs]

    out = {
        "n_runs": len(runs),
        "n_fabricating_runs": len(fab_runs),
        "tier_coverage": dict(n_completed_tiers),
        "global": global_agg["global_metrics"],
        "per_served_model": per_model,
        "cascade_patterns_among_fabricating": dict(pattern_counter),
        "cascade_depths_among_fabricating": cd_list,
        "fabrication_examples": [
            {
                "task_id": r["task_id"], "tier": r.get("tier"),
                "served_model": r["_served_model"],
                "fabricated_values": [
                    {"step": v["step"], "tool": v["tool"], "values": v["fabricated_values"]}
                    for v in r["classification"]["verdicts"] if v["verdict"] == "fabricated"
                ],
                "cascade": r["classification"]["cascade_analysis"],
                "final_untraceable": r["classification"].get("final_grounding", {}).get("untraceable_numbers", []),
            }
            for r in fab_runs[:12]
        ],
    }
    with open(os.path.join(RESULTS, "analysis_per_served_model.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)

    # ------- markdown table (paste-ready for the paper) -------
    lines = []
    lines.append("## Per-served-model results (CascToolBench v0.1)\n")
    lines.append("| Served model | Runs | Purity | Tool calls | FAB | FR | Honest-handling | MCI | AvgCD | MaxCD | Patterns |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for sm, d in sorted(per_model.items(), key=lambda kv: -kv[1]["benchmark"]["total_tool_calls"]):
        gm = d["global_metrics"]
        bm = d["benchmark"]
        pat = gm.get("cascade_pattern_distribution", {})
        pat_s = ", ".join(f"{k}:{v}" for k, v in pat.items()) if pat else "-"
        lines.append(
            f"| {sm} | {d['n_runs']} | {d['avg_model_purity']:.0%} | {bm['total_tool_calls']} "
            f"| {bm['total_fabrications']} | {gm['FR']:.2%} | {gm.get('honest_handling', 0):.0%} "
            f"| {gm['avg_MCI']:.3f} | {gm['avg_CD']} | {gm['max_CD']} | {pat_s} |")
    gm = out["global"]
    lines.append("")
    lines.append(f"**Global:** {len(runs)} runs, TOI={gm['TOI']:.2%}, FR={gm['FR']:.2%}, "
                 f"avgMCI={gm['avg_MCI']:.4f}, avgCD={gm['avg_CD']}, maxCD={gm['max_CD']}, "
                 f"fabricating runs={len(fab_runs)}")
    table = "\n".join(lines)
    print(table)
    with open(os.path.join(RESULTS, "analysis_table.txt"), "w", encoding="utf-8") as f:
        f.write(table + "\n")


if __name__ == "__main__":
    main()