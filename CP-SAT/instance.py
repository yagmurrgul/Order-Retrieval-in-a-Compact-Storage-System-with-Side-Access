"""SACRP instance parser.

Parses the visual ASCII grid format used in benchmark_instances/. The grid is
a column-aligned, fixed-cell-width representation where each cell is
``|_X_|`` (4 chars wide; `|` is shared between adjacent cells). A 4-space
group means "no bin at this (column, row)". Cell value 0 = non-target,
1 = target.

Conventions match the C++ codebase (TxtReader.cpp / InstanceBuilder.cpp):

* The top of the file is the highest row; the bottom row is height 1.
* Heights are global (level 1 at the floor, up to ``max_height``).
* Stacks are 1-indexed left-to-right.
* All bins (targets + non-targets) are numbered, but only target bins
  participate in the CP-SAT formulation, so the parser returns the
  target bins as the primary list and keeps non-target bins implicit
  (counted into ``n_per_stack``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Instance:
    """Parsed instance ready for the CP-SAT model.

    Attributes are paper-symbol names where possible. Stacks are 1-indexed,
    target bins use 0-indexed Python lists.
    """

    name: str
    T: int                 # number of stacks
    n_per_stack: List[int] # n(t) for t in 1..T (index by t-1)
    targets_h: List[int]   # h(b) for b in target set, 0-indexed height
                           # (0 = floor, n(t)-1 = top of stack)
    targets_s: List[int]   # s(b) for b in target set, 1-indexed stack
    max_height: int

    @property
    def n_targets(self) -> int:
        return len(self.targets_h)


def _parse_grid_row(line: str) -> List[int]:
    """Parse one visual row, returning ints per column.

    Returns a list of length ``num_columns`` with -1 for empty cells,
    0/1 for non-target/target bins.

    Mirrors TxtReader.cpp::extractStorageGridContent line by line.
    """
    out: List[int] = []
    empty_run = 0
    i = 0
    cap = ""
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "|" and i + 1 < n and line[i + 1] == "_":
            i += 2
        elif ch == " ":
            empty_run += 1
            i += 4  # one empty cell = 4 spaces
        elif ch != "_":
            cap += ch
            i += 1
        else:
            # ch == '_': end of cell value
            if empty_run:
                out.extend([-1] * empty_run)
                empty_run = 0
            out.append(int(cap))
            cap = ""
            i += 3  # advance over '_|' and start of next cell (`_X_|`)
    return out


def parse_instance(path: str | Path) -> Instance:
    """Parse a SACRP instance file.

    The file may end with a trailing empty line; that's tolerated by
    pre-trimming and by allowing the C++-style row width to be taken
    from the bottom (widest) row.
    """
    path = Path(path)
    raw_lines: List[str] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        # Drop trailing whitespace but keep leading whitespace (positional).
        raw_lines.append(ln.rstrip())
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()

    # Parse each row.
    rows = [_parse_grid_row(ln) for ln in raw_lines]
    max_height = len(rows)
    max_width = max(len(r) for r in rows)
    # Right-pad shorter rows with -1 (defensive; rows from the top are
    # often shorter because no stack reaches that high).
    for r in rows:
        if len(r) < max_width:
            r.extend([-1] * (max_width - len(r)))

    T = max_width
    n_per_stack = [0] * T
    targets_h: List[int] = []
    targets_s: List[int] = []

    # rows[0] is the topmost row (height = max_height); rows[-1] is the floor (height = 1).
    for row_idx, row in enumerate(rows):
        height = max_height - row_idx  # 1-indexed, bottom = 1
        for col_idx, cell in enumerate(row):
            if cell == -1:
                continue
            stack = col_idx + 1  # 1-indexed
            n_per_stack[col_idx] += 1
            if cell == 1:
                # 0-indexed height: bottom row → 0, top → max-1.
                targets_h.append(height - 1)
                targets_s.append(stack)
            elif cell != 0:
                raise ValueError(f"unexpected cell value {cell!r} in {path}")

    return Instance(
        name=path.stem,
        T=T,
        n_per_stack=n_per_stack,
        targets_h=targets_h,
        targets_s=targets_s,
        max_height=max_height,
    )


def total_bins(inst: Instance) -> int:
    return sum(inst.n_per_stack)


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        inst = parse_instance(arg)
        print(
            f"{inst.name}: T={inst.T} max_h={inst.max_height} "
            f"|bins|={total_bins(inst)} |targets|={inst.n_targets} "
            f"n(t)={inst.n_per_stack}"
        )
        print(f"  targets (h, s): {list(zip(inst.targets_h, inst.targets_s))}")
