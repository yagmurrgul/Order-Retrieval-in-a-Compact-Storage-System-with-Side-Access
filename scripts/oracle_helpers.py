"""Independent reference implementation of compute_C_for_stack and
compute_kappa_for_stack, written in Python to cross-check the C++ helpers
via the .lp file.

Parses an instance .txt file in the SACRP grid format and produces:
    - per-stack code-1-indexed target heights
    - per-stack C value
    - per-stack kappa value
    - total_C (sum of C(t) over stacks t = 1..m)  -- matches RHS of Const 21
    - kappa_max (max of kappa(t))                 -- matches RHS of Const 22

Grid format reminder (from CLAUDE.md):
  - `|_0_|`  = non-target bin
  - `|_1_|`  = target bin
  - 4 spaces = empty position
  - First row in file = topmost row of the grid
  - Last row  = bottom (code-height 1 under 1-indexed convention)

Usage:
    python oracle_helpers.py <instance.txt>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CELL_RX = re.compile(r"\|_(\d)_\|")


def parse_grid(path: Path) -> list[list[int | None]]:
    """Parse an instance file into a list of rows (top -> bottom).
    Each row is a list of length max_width with 0 (non-target), 1 (target),
    or None (empty). The output is right-padded to max_width.
    """
    rows: list[list[int | None]] = []
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    # Trim trailing empty lines but preserve the structure.
    while raw_lines and raw_lines[-1].strip() == "":
        raw_lines.pop()
    for line in raw_lines:
        # Walk the line one cell at a time. Cells are 4 chars wide; the trailing
        # `|` of one cell coincides with the leading `|` of the next.
        # Strategy: scan in 4-char strides; if the chunk is exactly 4 spaces,
        # mark the cell empty; otherwise extract the digit between '|_' and '_|'.
        row: list[int | None] = []
        i = 0
        # Pad short lines with spaces so we don't lose trailing empties.
        # Round up to a multiple of 4.
        L = len(line)
        if L % 4 != 0:
            line = line + " " * (4 - L % 4)
            L = len(line)
        while i + 4 <= L:
            chunk = line[i:i+4]
            if chunk == "    ":
                row.append(None)
            else:
                m = re.match(r"\|_(\d)_", chunk)
                if m:
                    row.append(int(m.group(1)))
                else:
                    # Could be the trailing '|' of last cell; ignore
                    row.append(None)
            i += 4
        rows.append(row)
    # Right-pad rows to max width.
    max_w = max(len(r) for r in rows) if rows else 0
    for r in rows:
        while len(r) < max_w:
            r.append(None)
    return rows


def stack_data(grid: list[list[int | None]]) -> dict[int, dict]:
    """Per-stack info keyed by stack index (1-based, code convention).
    Returns: { stack_idx: { 'height': n(t), 'targets': sorted [code-heights] } }
    """
    if not grid:
        return {}
    max_w = len(grid[0])
    rows = len(grid)
    info: dict[int, dict] = {}
    for s in range(max_w):
        targets: list[int] = []
        height = 0
        # Iterate from bottom (code-height 1) upward.
        for code_h in range(1, rows + 1):
            cell = grid[rows - code_h][s]
            if cell is None:
                continue
            # Note: instance builder marks a stack's height as the topmost
            # occupied row. Empty positions above the top are not counted.
            height = max(height, code_h)
            if cell == 1:
                targets.append(code_h)
        targets.sort()
        info[s + 1] = {"height": height, "targets": targets}
    return info


def compute_C(stack_info: dict) -> int:
    h = stack_info["height"]
    tgts = stack_info["targets"]
    if not tgts:
        return 0
    h_min = tgts[0]
    return h - h_min - len(tgts) + 1


def compute_kappa(stack_info: dict) -> int:
    tgts = stack_info["targets"]
    if not tgts:
        return 0
    runs = 1
    for i in range(1, len(tgts)):
        if tgts[i] != tgts[i - 1] + 1:
            runs += 1
    return runs


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: not found: {path}", file=sys.stderr)
        return 1
    grid = parse_grid(path)
    info = stack_data(grid)
    total_C = 0
    kappa_max = 0
    print(f"# {path}")
    print(f"# stacks: {len(info)}  rows: {len(grid)}")
    print("# stack | height | targets (code-h) | C | kappa")
    for s in sorted(info):
        C = compute_C(info[s])
        k = compute_kappa(info[s])
        total_C += C
        kappa_max = max(kappa_max, k)
        print(f"  {s:5d} | {info[s]['height']:6d} | {info[s]['targets']!r:>20s} "
              f"| {C:2d} | {k:2d}")
    print(f"# total_C  (expected RHS of Const 21) = {total_C}")
    print(f"# kappa_max (expected RHS of Const 22) = {kappa_max}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
