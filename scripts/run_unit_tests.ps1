# Unit-test driver for the Const 20/21/22 valid inequalities.
#
# For each test instance under test/instances/:
#   1. Runs the patched AuLoKomp_MIP.exe on it (cwd = a temp work dir).
#   2. Inspects the resulting ./model/<name>.lp via scripts/inspect_lp.py.
#   3. Compares the extracted RHS of Const 21 / Const 22 against the Python
#      oracle (scripts/oracle_helpers.py).
#   4. For the validation instance, also checks the solved objective == 4.
#
# Prereq: the patched exe is built. Each instance solves in <1 s.
#
# Usage:
#   .\run_unit_tests.ps1 -ExePath C:\path\to\AuLoKomp_MIP.exe

param(
    [Parameter(Mandatory=$true)] [string] $ExePath,
    [string] $WorkDir
)

$ErrorActionPreference = 'Stop'

$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$TestDir    = Join-Path $RepoRoot "test\instances"
if (-not $WorkDir) {
    $WorkDir = Join-Path (Split-Path -Parent $ExePath) "unit_test_run"
}

if (-not (Test-Path $ExePath)) { throw "Exe not found: $ExePath" }
if (-not (Test-Path $TestDir)) { throw "Test instance dir not found: $TestDir" }

# Per the spec, the validation instance's expected objective is 4.
$ExpectedObj = @{
    "validation_fig2"           = 4
    # The synthetic instances aren't asserted on objective -- only on RHS values.
}

$pythonExe = "py"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$DataDir     = Join-Path $WorkDir "data"
$SolutionDir = Join-Path $WorkDir "solution"
$ModelDir    = Join-Path $WorkDir "model"
New-Item -ItemType Directory -Force -Path $DataDir, $SolutionDir, $ModelDir | Out-Null

# Clear previous staging
Get-ChildItem -Path $DataDir -Filter *.txt -ErrorAction SilentlyContinue | Remove-Item -Force

# Stage test instances
$instances = Get-ChildItem -Path $TestDir -Filter *.txt
foreach ($f in $instances) {
    Copy-Item $f.FullName (Join-Path $DataDir $f.Name) -Force
}
Write-Host "Staged $($instances.Count) test instances."

# Run exe
Push-Location $WorkDir
try {
    Write-Host "Running solver..."
    & $ExePath | Out-Null
}
finally {
    Pop-Location
}

$failures = @()
foreach ($f in $instances) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $lpPath = Join-Path $ModelDir "$base.lp"
    $srcInst = $f.FullName

    if (-not (Test-Path $lpPath)) {
        $failures += "[$base] LP file missing: $lpPath"
        continue
    }

    Write-Host "----- $base -----"
    # 1) LP inspector
    & $pythonExe (Join-Path $PSScriptRoot "inspect_lp.py") $lpPath
    if ($LASTEXITCODE -ne 0) {
        $failures += "[$base] inspect_lp.py reported missing constraints."
        continue
    }
    # 2) Oracle for expected values
    & $pythonExe (Join-Path $PSScriptRoot "oracle_helpers.py") $srcInst

    # 3) Cross-check the LP RHS vs oracle by parsing both with Python
    $check = & $pythonExe -c @"
import sys, re
sys.path.insert(0, r'$PSScriptRoot')
from inspect_lp import iter_constraints, extract_rhs
from oracle_helpers import parse_grid, stack_data, compute_C, compute_kappa

lp = r'$lpPath'
inst = r'$srcInst'
c21, c22 = [], []
for name, body in iter_constraints(__import__('pathlib').Path(lp)):
    n = name.lower()
    if 'const_21' in n or n.startswith('const21'):
        c21.append(extract_rhs(body))
    elif 'const_22' in n or n.startswith('const22'):
        c22.append(extract_rhs(body))
info = stack_data(parse_grid(__import__('pathlib').Path(inst)))
oracle_C = sum(compute_C(s) for s in info.values())
oracle_k = max((compute_kappa(s) for s in info.values()), default=0)
print(f'LP    Const 21 RHS: {c21}')
print(f'LP    Const 22 RHS: {c22}')
print(f'Oracle total_C:   {oracle_C}')
print(f'Oracle kappa_max: {oracle_k}')
ok = True
if len(c21) != 1 or abs(c21[0] - oracle_C) > 1e-6:
    print(f'FAIL: Const 21 RHS mismatch'); ok = False
if len(c22) != 1 or abs(c22[0] - oracle_k) > 1e-6:
    print(f'FAIL: Const 22 RHS mismatch'); ok = False
sys.exit(0 if ok else 1)
"@
    if ($LASTEXITCODE -ne 0) {
        $failures += "[$base] LP RHS vs oracle mismatch."
    }

    # 4) For validation instance, parse the per-instance log and check obj == 4
    if ($ExpectedObj.ContainsKey($base)) {
        $expected = $ExpectedObj[$base]
        $logPath = Join-Path $SolutionDir $base
        if (Test-Path $logPath) {
            $logText = Get-Content $logPath -Raw
            if ($logText -match 'Objective.*?(\d+(?:\.\d+)?)') {
                $obj = [double]$Matches[1]
                if ([math]::Abs($obj - $expected) -gt 1e-6) {
                    $failures += "[$base] objective $obj != expected $expected"
                } else {
                    Write-Host "[$base] objective = $obj (matches expected $expected)"
                }
            } else {
                Write-Host "[$base] objective not found in log (check $logPath)"
            }
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "`n=== FAILURES ===" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    exit 1
} else {
    Write-Host "`nAll unit tests PASSED." -ForegroundColor Green
}
