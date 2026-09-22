#!/usr/bin/env python3
"""cascverify CLI — verify tool-output integrity of agent traces.

Standalone usage (no benchmark run required): point it at one or more trace
JSON files in run-result shape and it reports, per failed tool call, whether the
agent FABRICATED values, handled the failure HONESTLY, or HEDGED — plus the
cascade analysis (depth/breadth/MCI) and final-answer grounding.

    python -m cascverify.cli results/T1_01__tokenharbor__s1.json
    python -m cascverify.cli results/*.json --json
    python -m cascverify.cli results/ --summary

Exit code: 0 if no fabrication found in any trace, 2 if any fabrication found
(useful in CI / as a gate on agent-produced reports).
"""

import argparse
import glob
import json
import os
import sys

from .verifier import classify_trace


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files.extend(sorted(glob.glob(os.path.join(p, "*.json"))))
        else:
            files.extend(sorted(glob.glob(p)) or [p])
    out = []
    for fn in files:
        base = os.path.basename(fn)
        if base.startswith(("aggregate", "analysis")) or "__" not in base:
            continue
        try:
            r = _load(fn)
        except Exception as e:
            print(f"[skip] {fn}: {e}", file=sys.stderr)
            continue
        if isinstance(r, dict) and "task_id" in r and "steps" in r:
            out.append((fn, r))
    return out


def _print_human(fn, cl):
    ov = cl["overall"]
    ca = cl["cascade_analysis"]
    fg = cl["final_grounding"]
    print(f"\n=== {os.path.basename(fn)} ===")
    print(f"  task={cl['task_id']}  tier={cl['tier']}  model={cl.get('model')}")
    print(f"  calls={ov['total_tool_calls']}  failed={ov['failed_calls']}  "
          f"fabricated={ov['fabricated_count']}  honest={ov['honest_handling_count']}  "
          f"hedged={ov['hedged_count']}")
    print(f"  FR={ov['fabrication_rate']:.2%}  MCI={ov['memory_contamination_index']:.3f}  "
          f"pattern={ca['cascade_pattern']}  CD={ca['cascade_depth']}  CB={ca['cascade_breadth']}")
    print(f"  final answer grounded: {fg['grounded']}"
          + (f"  untraceable={fg['untraceable_numbers']}" if fg.get("untraceable_numbers") else ""))
    for v in cl["verdicts"]:
        if v["verdict"] == "fabricated":
            print(f"    [FAB] step {v['step']} {v['tool']}: values={v['fabricated_values']}")


def main():
    ap = argparse.ArgumentParser(description="Verify tool-output integrity of agent traces.")
    ap.add_argument("paths", nargs="+", help="trace JSON file(s), glob(s), or directory")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--summary", action="store_true", help="one-line-per-trace table only")
    args = ap.parse_args()

    traces = _collect(args.paths)
    if not traces:
        print("no valid trace files found", file=sys.stderr)
        return 1

    results = []
    for fn, r in traces:
        cl = classify_trace(r)
        results.append((fn, cl))

    if args.json:
        print(json.dumps([{"file": fn, "classification": cl} for fn, cl in results], indent=2))
    else:
        if args.summary:
            print(f"{'trace':44s} {'calls':>6s} {'fail':>5s} {'fab':>4s} {'FR':>7s} {'MCI':>7s} {'CD':>3s} {'pattern':>11s}")
            for fn, cl in results:
                ov, ca = cl["overall"], cl["cascade_analysis"]
                print(f"{os.path.basename(fn):44s} {ov['total_tool_calls']:6d} {ov['failed_calls']:5d} "
                      f"{ov['fabricated_count']:4d} {ov['fabrication_rate']:7.2%} "
                      f"{ov['memory_contamination_index']:7.3f} {ca['cascade_depth']:3d} {ca['cascade_pattern']:>11s}")
        else:
            for fn, cl in results:
                _print_human(fn, cl)

    total_fab = sum(cl["overall"]["fabricated_count"] for _, cl in results)
    if not args.json:
        print(f"\n{len(results)} trace(s) verified | total fabrications: {total_fab}")
    return 2 if total_fab else 0


if __name__ == "__main__":
    sys.exit(main())
