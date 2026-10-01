"""Compare a new SACRP MIP run against the benchmark `combined_output.txt`.

Joins by instance name and emits a CSV with columns:
    instance, num_uls, num_des_uls,
    obj_base, obj_new, obj_delta,
    lb_base,  lb_new,  lb_delta,
    gap_base, gap_new, gap_delta,
    runtime_base, runtime_new,
    obj_status, lb_status, gap_status

Status columns are one of:
    OK        - within tolerance / expected direction
    REGRESS   - new value is worse than baseline (objective bigger,
                LB smaller, gap larger) by more than --tol
    BETTER    - new value is strictly better (only possible if baseline was
                non-optimal, e.g. gap > 0)
    MISSING   - value missing in one of the files

Also prints a summary to stderr: regression counts, aggregate LB-delta,
aggregate runtime stats.

Usage:
    python compare_regression.py \\
        --new      path/to/new/combined_output.txt \\
        --baseline path/to/benchmark/combined_output.txt \\
        --out      path/to/compare.csv \\
        [--tol 1e-6]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Reuse parse_combined_output from sibling module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_combined_output import parse_combined_output  # noqa: E402


def _f(v):
    if isinstance(v, (int, float)):
        return float(v)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--new", required=True,
                    help="combined_output.txt produced by the patched solver")
    ap.add_argument("--baseline", required=True,
                    help="benchmark combined_output.txt")
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--tol", type=float, default=1e-6,
                    help="numeric tolerance for equality checks")
    args = ap.parse_args()

    base = parse_combined_output(args.baseline)
    new = parse_combined_output(args.new)

    common = sorted(set(base) & set(new),
                    key=lambda s: int(s.replace("Instance_", "")
                                       .replace("_large", "")))
    only_new = sorted(set(new) - set(base))
    only_base = sorted(set(base) - set(new))

    print(f"# baseline instances: {len(base)}", file=sys.stderr)
    print(f"# new instances:      {len(new)}", file=sys.stderr)
    print(f"# common:             {len(common)}", file=sys.stderr)
    if only_new:
        print(f"# only-in-new (skipped): {len(only_new)} "
              f"(first: {only_new[:3]})", file=sys.stderr)
    if only_base:
        print(f"# only-in-baseline (skipped): {len(only_base)} "
              f"(first: {only_base[:3]})", file=sys.stderr)

    tol = args.tol
    fields = [
        "instance", "num_uls", "num_des_uls",
        "obj_base", "obj_new", "obj_delta",
        "lb_base", "lb_new", "lb_delta",
        "gap_base", "gap_new", "gap_delta",
        "runtime_base", "runtime_new",
        "obj_status", "lb_status", "gap_status",
    ]

    obj_regress = 0
    obj_better = 0
    lb_better = 0
    lb_regress = 0
    gap_better = 0
    gap_regress = 0
    runtime_new_total = 0.0
    runtime_base_total = 0.0
    runtime_count = 0
    lb_delta_sum = 0.0
    lb_delta_count = 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for inst in common:
            b, n = base[inst], new[inst]
            ob, on = _f(b["obj"]), _f(n["obj"])
            lb_b, lb_n = _f(b["lb"]), _f(n["lb"])
            gp_b, gp_n = _f(b["gap"]), _f(n["gap"])
            rt_b, rt_n = _f(b["runtime"]), _f(n["runtime"])

            obj_delta = (on - ob) if (ob is not None and on is not None) else None
            lb_delta = (lb_n - lb_b) if (lb_b is not None and lb_n is not None) else None
            gap_delta = (gp_n - gp_b) if (gp_b is not None and gp_n is not None) else None

            if obj_delta is None:
                obj_status = "MISSING"
            elif obj_delta > tol:
                obj_status = "REGRESS"; obj_regress += 1
            elif obj_delta < -tol:
                obj_status = "BETTER"; obj_better += 1
            else:
                obj_status = "OK"

            if lb_delta is None:
                lb_status = "MISSING"
            elif lb_delta < -tol:
                lb_status = "REGRESS"; lb_regress += 1
            elif lb_delta > tol:
                lb_status = "BETTER"; lb_better += 1
                lb_delta_sum += lb_delta; lb_delta_count += 1
            else:
                lb_status = "OK"

            if gap_delta is None:
                gap_status = "MISSING"
            elif gap_delta > tol:
                gap_status = "REGRESS"; gap_regress += 1
            elif gap_delta < -tol:
                gap_status = "BETTER"; gap_better += 1
            else:
                gap_status = "OK"

            if rt_b is not None and rt_n is not None:
                runtime_base_total += rt_b
                runtime_new_total += rt_n
                runtime_count += 1

            w.writerow({
                "instance": inst,
                "num_uls": b.get("num_uls"),
                "num_des_uls": b.get("num_des_uls"),
                "obj_base": ob, "obj_new": on, "obj_delta": obj_delta,
                "lb_base": lb_b, "lb_new": lb_n, "lb_delta": lb_delta,
                "gap_base": gp_b, "gap_new": gp_n, "gap_delta": gap_delta,
                "runtime_base": rt_b, "runtime_new": rt_n,
                "obj_status": obj_status,
                "lb_status": lb_status,
                "gap_status": gap_status,
            })

    print("# === SUMMARY ===", file=sys.stderr)
    print(f"# obj REGRESS:  {obj_regress}  (must be 0)", file=sys.stderr)
    print(f"# obj BETTER:   {obj_better}   (OK only when baseline gap > 0)",
          file=sys.stderr)
    print(f"# lb  REGRESS:  {lb_regress}   (must be 0; valid ineq. only tighten)",
          file=sys.stderr)
    print(f"# lb  BETTER:   {lb_better}    (expected; this is the point of the cuts)",
          file=sys.stderr)
    print(f"# gap REGRESS:  {gap_regress}", file=sys.stderr)
    print(f"# gap BETTER:   {gap_better}", file=sys.stderr)
    if lb_delta_count:
        print(f"# avg LB improvement (over {lb_delta_count} BETTER cases): "
              f"{lb_delta_sum / lb_delta_count:.4f}", file=sys.stderr)
    if runtime_count:
        print(f"# runtime base total: {runtime_base_total:.1f}s  "
              f"new total: {runtime_new_total:.1f}s  "
              f"delta: {runtime_new_total - runtime_base_total:+.1f}s "
              f"({runtime_count} instances)", file=sys.stderr)

    # Non-zero exit if there is an objective or LB regression.
    if obj_regress > 0 or lb_regress > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
