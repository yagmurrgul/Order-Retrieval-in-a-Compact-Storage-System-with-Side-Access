"""SACRP CP-SAT runner.

Usage:

    python run.py --start 1 --end 600 [--set small] [--time-limit 600]
                  [--out results.csv] [--configs base,gravity,cuts]
                  [--log-dir logs/]

Runs every instance in ``[start, end]`` (inclusive) under the selected
configurations and writes one CSV row per (instance, configuration) pair.
Designed so the remaining instances can be re-launched on another
workstation with a different ``--start``/``--end`` and the same code.

Single-threaded by construction (``num_search_workers = 1``).
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from instance import parse_instance
from cpsat_model import build, solve, ModelConfig


CONFIG_FACTORIES = {
    "base": ModelConfig.base,
    "gravity": ModelConfig.with_gravity,
    "cuts": ModelConfig.with_cuts,
}


def instance_path(set_name: str, idx: int, data_dir: Path) -> Path:
    """Map (set, idx) -> file path. ``data_dir`` holds the instance files;
    the filename pattern is fixed by ``set_name``."""
    if set_name == "small":
        return data_dir / f"Instance_{idx}.txt"
    if set_name == "large":
        return data_dir / f"Instance_{idx}_large.txt"
    raise ValueError(f"unknown set: {set_name!r}")


def instance_id(set_name: str, idx: int) -> str:
    """ID format that matches combined_output.txt: Instance_<n> or Instance_<n>_large."""
    return f"Instance_{idx}" if set_name == "small" else f"Instance_{idx}_large"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, required=True, help="First instance index (inclusive).")
    p.add_argument("--end", type=int, required=True, help="Last instance index (inclusive).")
    p.add_argument("--set", choices=["small", "large"], default="small")
    p.add_argument("--data-dir", default=None,
                   help="Directory holding the instance files. Defaults to the repo's "
                        "benchmark_instances/instances_<set>. Pass an absolute path on "
                        "other machines, e.g. the workstation's data_small / data_large.")
    p.add_argument("--time-limit", type=float, default=600.0)
    p.add_argument("--out", default=None, help="Output CSV path (defaults to CP-SAT/results_<set>_<start>-<end>.csv).")
    p.add_argument("--configs", default="base,gravity,cuts",
                   help="Comma-separated subset of base,gravity,cuts.")
    p.add_argument("--log-dir", default=None, help="If set, write CP-SAT search log per (instance, config) here.")
    p.add_argument("--resume", action="store_true",
                   help="If set, skip rows already present in the output CSV (match on instance+config).")
    args = p.parse_args()

    configs_in_order = [c.strip() for c in args.configs.split(",") if c.strip()]
    for c in configs_in_order:
        if c not in CONFIG_FACTORIES:
            raise SystemExit(f"unknown config: {c!r} (allowed: {list(CONFIG_FACTORIES)})")

    if args.data_dir is not None:
        data_dir = Path(args.data_dir)
    else:
        sub = "instances_small" if args.set == "small" else "instances_large"
        data_dir = ROOT / "benchmark_instances" / sub
    if not data_dir.exists():
        raise SystemExit(f"data dir not found: {data_dir}")

    out_path = Path(args.out) if args.out else (
        ROOT / "CP-SAT" / f"results_{args.set}_{args.start}-{args.end}.csv"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    log_dir = Path(args.log_dir) if args.log_dir else None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)

    # CSV columns: per-instance results as required by the brief.
    fieldnames = [
        "instance_id", "configuration", "objective", "best_bound", "gap", "status",
        "runtime_s", "wall_time_s", "num_bool_vars", "num_int_vars",
        "num_constraints", "n_targets", "T", "max_height",
    ]

    # Resume support.
    already_done: set[tuple[str, str]] = set()
    if args.resume and out_path.exists():
        with out_path.open("r", newline="", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                already_done.add((row["instance_id"], row["configuration"]))

    mode = "a" if (args.resume and out_path.exists()) else "w"
    with out_path.open(mode, newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        fp.flush()

        total_pairs = (args.end - args.start + 1) * len(configs_in_order)
        done = 0
        t_run_start = time.perf_counter()

        for idx in range(args.start, args.end + 1):
            iid = instance_id(args.set, idx)
            ipath = instance_path(args.set, idx, data_dir)
            if not ipath.exists():
                print(f"  [skip] {iid}: file not found at {ipath}")
                continue
            inst = parse_instance(ipath)

            for cfg_name in configs_in_order:
                key = (iid, cfg_name)
                if key in already_done:
                    done += 1
                    continue

                cfg = CONFIG_FACTORIES[cfg_name]()
                built = build(inst, cfg)
                log_path = None
                if log_dir is not None:
                    log_path = str(log_dir / f"{iid}_{cfg_name}.log")
                res = solve(built, time_limit_s=args.time_limit, log_path=log_path)

                row = {
                    "instance_id": iid,
                    "configuration": cfg_name,
                    "objective": "" if res.objective != res.objective else f"{res.objective:.0f}",
                    "best_bound": "" if res.best_bound != res.best_bound else f"{res.best_bound:.6f}",
                    "gap": "" if res.gap != res.gap else f"{res.gap:.6f}",
                    "status": res.status,
                    "runtime_s": f"{res.runtime_s:.6f}",
                    "wall_time_s": f"{res.wall_time_s:.6f}",
                    "num_bool_vars": res.num_bool_vars,
                    "num_int_vars": res.num_int_vars,
                    "num_constraints": res.num_constraints,
                    "n_targets": inst.n_targets,
                    "T": inst.T,
                    "max_height": inst.max_height,
                }
                writer.writerow(row)
                fp.flush()

                done += 1
                if done % 10 == 0 or done == total_pairs:
                    elapsed = time.perf_counter() - t_run_start
                    rate = done / elapsed if elapsed > 0 else 0
                    remaining = total_pairs - done
                    eta = remaining / rate if rate > 0 else 0
                    print(f"  [{done}/{total_pairs}] {iid}/{cfg_name}: "
                          f"{res.status} obj={row['objective']} runtime={res.runtime_s:.2f}s  "
                          f"(elapsed={elapsed:.0f}s, ETA={eta:.0f}s)")

    print(f"\nDone. {done}/{total_pairs} solved. Results -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
