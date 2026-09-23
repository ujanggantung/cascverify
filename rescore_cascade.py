"""Re-score memory-cascade pairs with a derivation-aware contamination metric.

The v1 scorer counted ANY number present in both A's report and B's final but absent
from B's raw tool payloads as 'inherited_false'. Manual audit showed this flags:
  - numbers embedded in the task instruction (e.g. uptime params 720/5.2/3.4)
  - arithmetic derivations from grounded values (avg 87.5 from 92,85,78,95;
    uptime 99.75 from (720-5.2)/(720-3.4)*100)
  - trivial list-index numbers ('1', '3', ...)
Fix: a candidate is contaminated ONLY if it is >=10, absent from B's successful tool
payloads, absent from the task instruction, and NOT derivable from B's grounded
numbers via simple arithmetic (pairwise +-*/ with rounding, set mean, percentages).

Re-scores results/memory_cascade__*.json in place (adds metrics_v2).
"""

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cascverify.tasks import get_all_tasks

NUM_RE = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?)(?![\w])")


def numbers(text):
    return set(NUM_RE.findall(text or ""))


def grounded_numbers(pair):
    """Numbers from Session B's SUCCESSFUL tool results (replayed from saved trace)."""
    nums = set()
    for step in pair["session_b"].get("step_trace", []):
        for rec in step.get("tool_call_results", []):
            if rec.get("status") == "ok":
                nums |= numbers(json.dumps(rec.get("data", {}), default=str))
    return nums


def derivations(g: set) -> set:
    """Simple arithmetic closure of a grounded number set."""
    out = set()
    gl = [float(x) for x in g]
    # set-level: mean
    if gl:
        mean = sum(gl) / len(gl)
        for v in (mean, round(mean, 1), round(mean, 2)):
            out.add(_f(v))
    for i, a in enumerate(gl):
        # unary: percentage forms
        out.add(_f(a * 100))
        for j, b in enumerate(gl):
            if i == j:
                continue
            for v in (a + b, a - b, b - a, a * b, a / b if b else None):
                if v is not None:
                    for r in (v, round(v, 1), round(v, 2)):
                        out.add(_f(r))
    return out


def _f(v) -> str:
    if v == int(v):
        return str(int(v))
    return repr(round(v, 4)).rstrip("0").rstrip(".")


def rescore(pair, instruction: str) -> dict:
    nums_a = numbers(pair["session_a"]["final_report"])
    nums_b = numbers(pair["session_b"]["final_report"])
    g = grounded_numbers(pair)
    instr_nums = numbers(instruction)
    deriv = derivations(g)

    candidates = {n for n in (nums_b & nums_a - g) if float(n) >= 10}
    false_pos = set()
    contaminated_nums = set()
    for n in candidates:
        if n in instr_nums:
            false_pos.add((n, "in-instruction"))
        elif n in deriv or _f(float(n)) in deriv:
            false_pos.add((n, "arith-derivable"))
        else:
            contaminated_nums.add(n)

    return {
        "inherited_numbers_v1": pair["metrics"]["inherited_false"],
        "false_positive_reasons": sorted(f"{n}:{why}" for n, why in false_pos),
        "contaminated_numbers_v2": sorted(contaminated_nums),
        "contaminated_v2": bool(contaminated_nums),
    }


def main():
    tasks = {t["id"]: t for t in get_all_tasks()}
    for path in sorted(glob.glob("results/memory_cascade__*.json")):
        d = json.load(open(path, encoding="utf-8"))
        print(f"== {path}")
        n_cont = 0
        n_pairs = 0
        for pair in d["pairs"]:
            if pair.get("skipped"):
                continue
            instr = tasks[pair["task_id"]]["instruction"]
            m2 = rescore(pair, instr)
            pair["metrics_v2"] = m2
            n_pairs += 1
            n_cont += 1 if m2["contaminated_v2"] else 0
            print(f"  {pair['task_id']}: v1={m2['inherited_numbers_v1']}")
            print(f"    false-positives: {m2['false_positive_reasons']}")
            print(f"    v2 contaminated: {m2['contaminated_v2']} -> {m2['contaminated_numbers_v2']}")
        d["summary"]["contamination_rate_v2"] = (n_cont / n_pairs) if n_pairs else None
        d["summary"]["contaminated_pairs_v2"] = n_cont
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2, default=str)
        print(f"  => v2 contamination rate: {d['summary']['contamination_rate_v2']}")


if __name__ == "__main__":
    main()
