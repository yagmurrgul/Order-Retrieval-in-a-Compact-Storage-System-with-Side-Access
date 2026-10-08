# Order Retrieval in a Compact Storage System with Side Access

Code for the MIP model, the retrieval heuristic and the dynamic program (DP)
for the Side-Access Compact Retrieval Problem (SACRP).

## Requirements

- Windows with **Visual Studio 2022** (C++ desktop workload).
- **Gurobi 12.0.1** installed at `C:\gurobi1201` and a **valid Gurobi license**
  (free academic licenses: https://www.gurobi.com/academia/).
  If Gurobi is installed elsewhere, update the include/library paths in
  *Project → Properties → C/C++ / Linker*.
- DP only: the **.NET Core 2.1 SDK** (the project targets `netcoreapp2.1`);
  no Gurobi needed.

## Build

```bat
git clone https://github.com/yagmurrgul/Order-Retrieval-in-a-Compact-Storage-System-with-Side-Access.git
cd Order-Retrieval-in-a-Compact-Storage-System-with-Side-Access\AuLoKomp_MIP_Pinning
msbuild AuLoKomp_MIP.sln /p:Configuration=Release /p:Platform=x64
```

(or open `AuLoKomp_MIP_Pinning\AuLoKomp_MIP.sln` in Visual Studio and build **Release | x64**).

## Run

The program solves every instance in `.\data` and needs three folders in the
directory it is started from:

```bat
mkdir data solution model
copy <your instances>\*.txt data\
x64\Release\AuLoKomp_MIP.exe
```

When started from Visual Studio, the working directory is `AuLoKomp_MIP_Pinning\`,
so create the three folders there.

**MIP vs. heuristic.** Which method runs is set in `AuLoKomp_MIP.cpp` (`main`):

```cpp
bool mip_heur = 1;   // 1 = Gurobi MIP, 0 = heuristic
```

Set it to `0` and rebuild to run the heuristic instead. The MIP uses one thread
and a 600 s time limit (`runGurobi` in the same file).

**DP.** The DP is a separate C# project in `Aulokomp_IISE\`. It solves
`Instance_1.txt` … `Instance_810.txt` and then `Instance_1_large.txt` …
`Instance_810_large.txt` from the directory it is started from:

```bat
cd Aulokomp_IISE\Aulokomp
copy <Instance_small>\*.txt .
copy <Instance_large>\*.txt .
dotnet run -c Release
```

(or open `Aulokomp_IISE\Aulokomp.sln` in Visual Studio and run **Release**; the
instance files must then be in the working directory of the run).
The DP has a 600 s time limit per instance (`new cDP(600)` in `Program.cs`).

## Input format

One `.txt` file per instance. Each line is one level of the storage grid (top
line = highest level), each cell is `|_X_|` with `X = 1` for a requested
(target) unit load and `X = 0` for any other unit load; an empty position is
written as four spaces. Example (4 stacks, 3 levels, 3 requested unit loads):

```
|_1_|_0_|_0_|_0_|
|_0_|_0_|_1_|_0_|
|_1_|_0_|_0_|_0_|
```

## Output

- `solution\combined_output.txt` — one row per instance: instance name, runtime
  (ms), objective value, lower bound, gap, number of unit loads, number of
  requested unit loads, grid occupancy, requested-load share, node count, root
  LP bound, cuts added, time to best solution.
- `solution\<instance>` — per-instance log.
- `model\<instance>.lp` / `.mps` — the generated MIP (MIP mode only).
- DP: `Results.txt` (small) and `Results_large.txt` (large), appended, one row
  per instance: instance number, objective value (`-1` = time limit reached),
  number of states, runtime (s).

## Repository layout

| Path | Contents |
|---|---|
| `AuLoKomp_MIP_Pinning/` | C++ MIP model and heuristic (Visual Studio project) |
| `Aulokomp_IISE/` | C# dynamic program (.NET project) |
| `Instance_small.zip`, `Instance_large.zip` | The 810 small and 810 large instances |
| `CP-SAT/` | Alternative CP-SAT model (Python, OR-Tools): `python CP-SAT/run.py --start 1 --end 10 --data-dir <instances>`; result CSVs of the reported runs |
