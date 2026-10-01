"""Parse the fixed-width `combined_output.txt` produced by the SACRP MIP runner.

Returns a dict keyed by instance name -> dict of columns. Columns:
    runtime, obj, lb, gap, num_uls, num_des_uls, grid_occ, ul_occ

Each line is 9 fields, each 20-char wide left-aligned (see GlobalLogger.cpp).
Header rows (containing "Instance Name") are skipped.
"""
from __future__ import annotations

import sys
from pathlib import Path

COL_WIDTH = 20
FIELDS = ["instance", "runtime", "obj", "lb", "gap",
          "num_uls", "num_des_uls", "grid_occ", "ul_occ"]


def _coerce(value: str) -> float | str | None:
    v = value.strip()
    if v == "":
        return None
    if v == "-" or v.lower() == "infeasible":
        return v
    try:
        return float(v)
    except ValueError:
        return v


def parse_combined_output(path: str | Path) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    p = Path(path)
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if "Instance Name" in line:
                continue
            # split by fixed widths
            cols = [line[i*COL_WIDTH:(i+1)*COL_WIDTH] for i in range(len(FIELDS))]
            inst = cols[0].strip()
            if not inst:
                continue
            row: dict[str, object] = {"instance": inst}
            for fname, raw_val in zip(FIELDS[1:], cols[1:]):
                row[fname] = _coerce(raw_val)
            out[inst] = row
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    data = parse_combined_output(sys.argv[1])
    print(f"Parsed {len(data)} instances.")
    # show first 3
    for k in list(data)[:3]:
        print(f"  {k}: {data[k]}")
