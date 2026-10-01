"""Inspect a Gurobi .lp file for Const 20/21/22 valid inequalities.

Reads the LP file and prints:
  - count of `Const 20` rows (expected: num_desired_uls - 1)
  - the RHS of the single `Const 21` row (expected: total_C)
  - the RHS of the single `Const 22` row (expected: kappa_max)

Usage:
    python inspect_lp.py <path-to-lp-file>

Gurobi sanitizes constraint names by replacing spaces/colons with underscores.
We match loosely on the prefix `Const_20`, `Const_21`, `Const_22` (or any
variation thereof) as a substring of the constraint name.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator


# Gurobi LP grammar: constraints appear after the "Subject To" header and before
# "Bounds"/"Binary"/"Generals"/"End". Each constraint starts with `name:`
# followed by a linear expression, an operator (<=, >=, =), and a RHS value.
# Constraints may span multiple lines (continuation lines are indented).
HEADER_RX = re.compile(r"^(Subject\s+To|Bounds|Binary|General|Generals|End)\b",
                       re.IGNORECASE)
# A constraint label is the first non-whitespace token followed by ':'.
LABEL_RX = re.compile(r"^\s*([A-Za-z0-9_.\[\]]+)\s*:")


def iter_constraints(lp_path: Path) -> Iterator[tuple[str, str]]:
    """Yield (constraint_name, full_constraint_body) pairs from the LP file."""
    in_subject_to = False
    current_name: str | None = None
    current_body: list[str] = []
    with lp_path.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip()
            stripped = line.strip()
            if not stripped:
                continue
            # Section transitions
            hdr = HEADER_RX.match(stripped)
            if hdr:
                section = hdr.group(1).lower()
                if section.startswith("subject"):
                    in_subject_to = True
                    continue
                else:
                    # leaving Subject To; flush last constraint
                    if current_name is not None:
                        yield current_name, " ".join(current_body)
                        current_name, current_body = None, []
                    in_subject_to = False
                    continue
            if not in_subject_to:
                continue
            m = LABEL_RX.match(line)
            if m:
                # finish previous
                if current_name is not None:
                    yield current_name, " ".join(current_body)
                current_name = m.group(1)
                # body = remainder after the colon
                rest = line.split(":", 1)[1].strip()
                current_body = [rest] if rest else []
            else:
                if current_name is not None:
                    current_body.append(stripped)
    if current_name is not None:
        yield current_name, " ".join(current_body)


def extract_rhs(body: str) -> float | None:
    """Extract the RHS numeric value from a constraint body."""
    m = re.search(r"(<=|>=|=)\s*(-?\d+(?:\.\d+)?)", body)
    if not m:
        return None
    return float(m.group(2))


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    lp_path = Path(sys.argv[1])
    if not lp_path.exists():
        print(f"ERROR: {lp_path} not found", file=sys.stderr)
        return 1

    const20_count = 0
    const21_rhs: list[float] = []
    const22_rhs: list[float] = []
    const20_examples: list[tuple[str, float | None]] = []

    for name, body in iter_constraints(lp_path):
        norm = name.lower()
        if "const_20" in norm or norm.startswith("const20"):
            const20_count += 1
            if len(const20_examples) < 3:
                const20_examples.append((name, extract_rhs(body)))
        elif "const_21" in norm or norm.startswith("const21"):
            rhs = extract_rhs(body)
            if rhs is not None:
                const21_rhs.append(rhs)
        elif "const_22" in norm or norm.startswith("const22"):
            rhs = extract_rhs(body)
            if rhs is not None:
                const22_rhs.append(rhs)

    print(f"LP file: {lp_path}")
    print(f"Const 20 rows: {const20_count}")
    for nm, rhs in const20_examples:
        print(f"    example: {nm}  rhs={rhs}")
    print(f"Const 21 rows: {len(const21_rhs)}  RHS values: {const21_rhs}")
    print(f"Const 22 rows: {len(const22_rhs)}  RHS values: {const22_rhs}")

    # Exit nonzero if any of the three are completely missing
    missing = []
    if const20_count == 0:
        missing.append("Const 20")
    if not const21_rhs:
        missing.append("Const 21")
    if not const22_rhs:
        missing.append("Const 22")
    if missing:
        print(f"FAIL: missing constraints: {', '.join(missing)}", file=sys.stderr)
        return 1
    print("OK: all three constraint families present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
