"""Pick a deterministic 600-instance subset of the 810 small benchmark instances.

Sampling strategy:
- 30 unique (num_uls, num_des_uls) configurations exist in the benchmark
  (10 grid sizes x 3 desired-UL counts).
- Per-config sample sizes (per actual config sizes in
  `benchmark_solutions/solutions_small_600s/combined_output.txt`):
    - Configs with 60 instances each (96_5/10/15):     45 each ->  3 x 45 = 135
    - Configs with 30 instances each (18 configs):     22 each -> 18 x 22 = 396
    - Configs with 10 instances each (9 configs):       8 each ->  9 x  8 =  72
    Subtotal: 135 + 396 + 72 = 603. The first 3 over-quota are trimmed to
    land at exactly 600 by reducing one of the 60-instance configs by 3.
- Selection within a config: sort by integer suffix of the instance name and
  take a uniform stride. Deterministic and reproducible.

Output: one instance name per line on stdout (or to --out).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_SMALL = (REPO_ROOT / "benchmark_solutions" / "solutions_small_600s"
                   / "combined_output.txt")

NUM_RX = re.compile(r"Instance_(\d+)")

# Per-config quota
PER_CONFIG_LARGE = 45   # 60-instance configs -> 45 each
PER_CONFIG_MED = 22     # 30-instance configs -> 22 each
PER_CONFIG_SMALL = 8    # 10-instance configs -> 8 each

# Target overall count (used only as an assertion below)
TARGET_COUNT = 600


def stride_pick(items: list[str], k: int) -> list[str]:
    """Pick k items from a sorted list using a uniform stride."""
    n = len(items)
    if k >= n:
        return list(items)
    # pick indices that are evenly spaced across [0, n)
    return [items[round(i * (n - 1) / (k - 1))] for i in range(k)]


def load_configs(bench_path: Path) -> dict[tuple[str, str], list[str]]:
    """Return map (num_uls_str, num_des_uls_str) -> sorted list of instance names."""
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    with bench_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or "Instance Name" in line:
                continue
            # fixed 20-char columns; field 0 = name, 5 = num_uls, 6 = num_des_uls
            cols = [line[i*20:(i+1)*20].strip() for i in range(9)]
            name = cols[0]
            if not name:
                continue
            key = (cols[5], cols[6])
            groups[key].append(name)
    # sort each group by the integer suffix
    for k, v in groups.items():
        v.sort(key=lambda s: int(NUM_RX.search(s).group(1)) if NUM_RX.search(s) else 0)
    return groups


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None,
                    help="Output file path (one instance name per line). "
                         "Default: stdout.")
    args = ap.parse_args()

    if not BENCHMARK_SMALL.exists():
        print(f"ERROR: benchmark file not found: {BENCHMARK_SMALL}", file=sys.stderr)
        return 1
    groups = load_configs(BENCHMARK_SMALL)
    if not groups:
        print("ERROR: parsed 0 instances from benchmark file", file=sys.stderr)
        return 1

    selected: list[str] = []
    config_summary: list[tuple[tuple[str, str], int, int]] = []
    for cfg, instances in sorted(groups.items()):
        n = len(instances)
        if n >= 60:
            k = PER_CONFIG_LARGE
        elif n >= 30:
            k = PER_CONFIG_MED
        elif n >= 10:
            k = PER_CONFIG_SMALL
        else:
            k = n
        picked = stride_pick(instances, k)
        config_summary.append((cfg, n, len(picked)))
        selected.extend(picked)

    # Trim down or pad up to exactly TARGET_COUNT.
    # Deduplicate while preserving order first.
    seen = set()
    uniq = []
    for s in selected:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    selected = uniq

    if len(selected) > TARGET_COUNT:
        # Drop the trailing N to land at TARGET_COUNT (deterministic).
        selected = selected[:TARGET_COUNT]
    elif len(selected) < TARGET_COUNT:
        # Pad with the largest 30-instance configs first (more informative).
        pad_priority = [
            ("192", "15"), ("192", "10"), ("192", "5"),
            ("144", "15"), ("144", "10"), ("144", "5"),
            ("128", "15"), ("128", "10"), ("128", "5"),
        ]
        sel_set = set(selected)
        for cfg in pad_priority:
            if cfg not in groups:
                continue
            for inst in groups[cfg]:
                if inst not in sel_set:
                    selected.append(inst)
                    sel_set.add(inst)
                    if len(selected) >= TARGET_COUNT:
                        break
            if len(selected) >= TARGET_COUNT:
                break

    # Diagnostic to stderr
    print(f"# Total unique configs: {len(config_summary)}", file=sys.stderr)
    for cfg, total, k in config_summary:
        print(f"#   {cfg[0]:>4}_{cfg[1]:<2}  pool={total:>2}  picked={k:>2}",
              file=sys.stderr)
    print(f"# Final selected: {len(selected)}", file=sys.stderr)

    output_text = "\n".join(selected) + "\n"
    if args.out:
        Path(args.out).write_text(output_text, encoding="utf-8")
        print(f"# Wrote {len(selected)} names to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(output_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
