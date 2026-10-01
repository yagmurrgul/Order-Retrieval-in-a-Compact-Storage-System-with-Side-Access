"""Byte-for-byte Python replica of the Coder's C++ helpers, plus the
total_C / kappa_max aggregation loops as written in the diff.

We compare the replica's output against scripts/oracle_helpers.py for all
4 unit-test instances.

The C++ aggregation loops are:
    for t in 1..max_width:
        total_C   += compute_C_for_stack(t, stack_heights[t-1], desired)
        kappa_max  = max(kappa_max, compute_kappa_for_stack(t, desired))
where max_width = instance.getMaxWidth() and stack_heights[s] is the
top-most occupied row index of stack s (1-indexed code height).

InstanceBuilder.cpp computes stack_heights from the grid the same way our
oracle parses it: the top-most row in which there is a cell becomes the
stack height; empty (None) cells above contribute 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_helpers import (parse_grid, stack_data,
                            compute_C as oracle_C,
                            compute_kappa as oracle_kappa)


def cpp_compute_C(stack_index: int, stack_height: int,
                  desired: list[dict]) -> int:
    """Mirror of Coder's compute_C_for_stack."""
    INT_MAX = 2**31 - 1
    h_min = INT_MAX
    nb_targets = 0
    for ul in desired:
        if ul["stack"] == stack_index:
            nb_targets += 1
            if ul["initial_height"] < h_min:
                h_min = ul["initial_height"]
    if nb_targets == 0:
        return 0
    return stack_height - h_min - nb_targets + 1


def cpp_compute_kappa(stack_index: int, desired: list[dict]) -> int:
    """Mirror of Coder's compute_kappa_for_stack."""
    heights = []
    for ul in desired:
        if ul["stack"] == stack_index:
            heights.append(ul["initial_height"])
    if not heights:
        return 0
    heights.sort()
    kappa = 1
    for j in range(1, len(heights)):
        if heights[j] != heights[j - 1] + 1:
            kappa += 1
    return kappa


def desired_unit_loads_from_grid(grid) -> list[dict]:
    """Mirror InstanceBuilder: iterate top to bottom, current_line starts at
    max_height and decreases. A cell value == 1 becomes a target with
    initial_height = current_line and stack = column + 1.
    """
    if not grid:
        return []
    max_height = len(grid)
    max_width = len(grid[0])
    desired: list[dict] = []
    current_line = max_height
    for row in grid:
        for col_idx, cell in enumerate(row):
            if cell == 1:
                desired.append({"stack": col_idx + 1,
                                "initial_height": current_line})
        current_line -= 1
    return desired


def stack_heights_from_grid(grid) -> list[int]:
    """Mirror InstanceBuilder's stack_heights: the highest row index (in code
    1-indexed convention) at which the column has any cell."""
    if not grid:
        return []
    max_height = len(grid)
    max_width = len(grid[0])
    heights = [0] * max_width
    found = [False] * max_width
    current_line = max_height
    for row in grid:
        for col_idx, cell in enumerate(row):
            if cell is not None and not found[col_idx]:
                heights[col_idx] = current_line
                found[col_idx] = True
        current_line -= 1
    return heights


def run_for_file(path: Path) -> dict:
    grid = parse_grid(path)
    desired = desired_unit_loads_from_grid(grid)
    stack_heights = stack_heights_from_grid(grid)
    max_width = len(stack_heights)

    # === C++ replica path ===
    cpp_total_C = 0
    cpp_kappa_max = 0
    per_stack_cpp = []
    for t in range(1, max_width + 1):
        C = cpp_compute_C(t, stack_heights[t - 1], desired)
        k = cpp_compute_kappa(t, desired)
        cpp_total_C += C
        cpp_kappa_max = max(cpp_kappa_max, k)
        per_stack_cpp.append((t, stack_heights[t - 1], C, k))

    # === Independent oracle path ===
    info = stack_data(grid)
    per_stack_oracle = []
    or_total_C = 0
    or_kappa_max = 0
    for s in sorted(info):
        C = oracle_C(info[s])
        k = oracle_kappa(info[s])
        or_total_C += C
        or_kappa_max = max(or_kappa_max, k)
        per_stack_oracle.append((s, info[s]["height"], C, k))

    return {
        "file": str(path),
        "max_width": max_width,
        "stack_heights": stack_heights,
        "desired": desired,
        "per_stack_cpp": per_stack_cpp,
        "per_stack_oracle": per_stack_oracle,
        "cpp_total_C": cpp_total_C,
        "cpp_kappa_max": cpp_kappa_max,
        "oracle_total_C": or_total_C,
        "oracle_kappa_max": or_kappa_max,
    }


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    test_dir = repo / "test" / "instances"
    files = sorted(test_dir.glob("*.txt"))

    expected = {
        "validation_fig2":          {"total_C": 2, "kappa_max": 1},
        "synth_kappa_gaps":         {"total_C": 3, "kappa_max": 3},
        "synth_C_one_target":       {"total_C": 2, "kappa_max": 1},
        "synth_empty_target_stack": {"total_C": 0, "kappa_max": 1},
    }

    all_pass = True
    for f in files:
        res = run_for_file(f)
        name = f.stem
        exp = expected.get(name, {})
        print("=" * 72)
        print(f"FILE: {f.name}   (max_width={res['max_width']}, "
              f"stack_heights={res['stack_heights']})")
        print(f"  desired UL list (stack,height): "
              f"{[(d['stack'], d['initial_height']) for d in res['desired']]}")
        print("  per-stack | t | n(t) | C (cpp) | kappa (cpp) || C (oracle) | kappa (oracle)")
        # zip by stack index (oracle may produce extra trailing 'phantom' stacks)
        m = {t: (h, C, k) for (t, h, C, k) in res['per_stack_oracle']}
        for (t, h, C, k) in res['per_stack_cpp']:
            oh, oC, oK = m.get(t, (None, None, None))
            print(f"            | {t} | {h:4d} | {C:7d} | {k:11d} "
                  f"|| {oC if oC is not None else '-':>10} | {oK if oK is not None else '-'}")
        print(f"  cpp     -> total_C={res['cpp_total_C']:3d}  "
              f"kappa_max={res['cpp_kappa_max']}")
        print(f"  oracle  -> total_C={res['oracle_total_C']:3d}  "
              f"kappa_max={res['oracle_kappa_max']}")
        if exp:
            print(f"  hand    -> total_C={exp['total_C']:3d}  "
                  f"kappa_max={exp['kappa_max']}")
            ok_C = res['cpp_total_C'] == exp['total_C']
            ok_K = res['cpp_kappa_max'] == exp['kappa_max']
            verdict = "PASS" if ok_C and ok_K else "FAIL"
            if not (ok_C and ok_K):
                all_pass = False
            print(f"  verdict (cpp vs hand): {verdict}")
        # also compare cpp vs oracle (must always match)
        if (res['cpp_total_C'] != res['oracle_total_C'] or
                res['cpp_kappa_max'] != res['oracle_kappa_max']):
            print(f"  *** MISMATCH between C++ replica and oracle ***")
            all_pass = False

    print()
    print("OVERALL:", "PASS" if all_pass else "FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
