# SACRP regression harness for the valid-inequality patch (Const 20/21/22).
#
# Stages the sampled 600 small instances into a working directory next to the
# built .exe, runs the solver, then invokes compare_regression.py to join the
# new combined_output.txt with the benchmark and emit a comparison CSV.
#
# Prerequisites:
#   - The MIP solver has been built (e.g., AuLoKomp_MIP.exe) with the new
#     Const 20/21/22 constraints applied.
#   - Python 3 is on PATH (`py` launcher works on Windows).
#   - At least ~100 CPU-hours of capacity (600 instances * 600 s time limit).
#
# Parameters:
#   -ExePath    : full path to AuLoKomp_MIP.exe (post-build)
#   -WorkDir    : a writeable directory where ./data, ./solution, ./model
#                 live (the exe uses relative paths). Defaults to a sibling
#                 of the exe.
#   -RepoRoot   : path to the SACRP repo. Defaults to the repo containing this
#                 script.
#   -SampleFile : path to a file with one instance name per line. Defaults to
#                 scripts/sampled_600.txt.
#   -OutCsv     : where to write the comparison CSV.
#
# Example:
#   .\run_regression.ps1 `
#       -ExePath  C:\build\AuLoKomp_MIP.exe `
#       -WorkDir  C:\runs\const20_22 `
#       -OutCsv   C:\runs\const20_22\compare.csv

param(
    [Parameter(Mandatory=$true)] [string] $ExePath,
    [string] $WorkDir,
    [string] $RepoRoot,
    [string] $SampleFile,
    [string] $OutCsv
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if (-not $SampleFile) {
    $SampleFile = Join-Path $PSScriptRoot "sampled_600.txt"
}
if (-not $WorkDir) {
    $WorkDir = Join-Path (Split-Path -Parent $ExePath) "regression_run"
}
if (-not $OutCsv) {
    $OutCsv = Join-Path $WorkDir "compare.csv"
}

if (-not (Test-Path $ExePath)) { throw "Exe not found: $ExePath" }
if (-not (Test-Path $SampleFile)) { throw "Sample file not found: $SampleFile" }

$instanceSrc = Join-Path $RepoRoot "benchmark_instances\instances_small"
if (-not (Test-Path $instanceSrc)) { throw "Instances not found: $instanceSrc" }

$benchFile = Join-Path $RepoRoot "benchmark_solutions\solutions_small_600s\combined_output.txt"
if (-not (Test-Path $benchFile)) { throw "Benchmark file not found: $benchFile" }

# Prepare working directory layout: ./data, ./solution, ./model (the exe uses
# relative paths from its own cwd).
$DataDir     = Join-Path $WorkDir "data"
$SolutionDir = Join-Path $WorkDir "solution"
$ModelDir    = Join-Path $WorkDir "model"
New-Item -ItemType Directory -Force -Path $DataDir, $SolutionDir, $ModelDir | Out-Null

Write-Host "Staging instances into $DataDir ..."
$names = Get-Content $SampleFile | Where-Object { $_.Trim() -ne "" }
$staged = 0
foreach ($name in $names) {
    $src = Join-Path $instanceSrc "$name.txt"
    if (-not (Test-Path $src)) {
        Write-Warning "Missing source instance: $src"
        continue
    }
    Copy-Item -Path $src -Destination (Join-Path $DataDir "$name.txt") -Force
    $staged++
}
Write-Host "Staged $staged / $($names.Count) instances."

# Run the solver from $WorkDir so that ./data, ./solution, ./model resolve.
Push-Location $WorkDir
try {
    Write-Host "Running solver: $ExePath  (cwd=$WorkDir)"
    $start = Get-Date
    & $ExePath
    $end = Get-Date
    Write-Host ("Solver finished in {0:N1} minutes." -f ($end - $start).TotalMinutes)
}
finally {
    Pop-Location
}

$newOutput = Join-Path $SolutionDir "combined_output.txt"
if (-not (Test-Path $newOutput)) { throw "Solver did not produce $newOutput" }

# Compare against benchmark.
$pythonExe = "py"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$compareScript = Join-Path $PSScriptRoot "compare_regression.py"
& $pythonExe $compareScript --new $newOutput --baseline $benchFile --out $OutCsv
Write-Host "Comparison CSV: $OutCsv"
