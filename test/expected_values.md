# Expected hand-computed values for valid-inequality tests

All values are in the **1-indexed code convention** (floor = height 1), matching the
C++ implementation. Paper R1 uses 0-indexed heights; convert by +1 when comparing.

Helper definitions (per `Solver.cpp` static helpers, code convention):
- `C(t) = stack_height(t) - h_min(t) - |targets in stack t| + 1`, 0 if no targets.
- `kappa(t)` = number of maximal runs of consecutive target code-heights in stack t.

## Test 1 — Validation instance (R1 Figure 2)
File: `test/instances/validation_fig2.txt`
Grid: 4 stacks, heights n = (5, 4, 2, 4); 6 targets (paper 0-idx coords → code 1-idx coords)
- (1,3)→(1,4), (4,3)→(4,4), (1,2)→(1,3), (2,2)→(2,3), (4,2)→(4,3), (1,1)→(1,2)

Per-stack expected:
| stack | n(t) | target code-heights | h_min | #tgt | C(t) | kappa(t) |
|------:|-----:|--------------------:|------:|-----:|-----:|---------:|
| 1     | 5    | {2, 3, 4}           | 2     | 3    | 5-2-3+1 = 1 | 1 (one run {2,3,4})        |
| 2     | 4    | {3}                 | 3     | 1    | 4-3-1+1 = 1 | 1                          |
| 3     | 2    | {}                  | -     | 0    | 0           | 0                          |
| 4     | 4    | {3, 4}              | 3     | 2    | 4-3-2+1 = 0 | 1 (one run {3,4})          |

**total_C = 1 + 1 + 0 + 0 = 2.** Expected `Const 21` RHS = 2.
**kappa_max = max(1,1,0,1) = 1.**  Expected `Const 22` RHS = 1.
**Optimal objective = 4** (paper). Const 21 (energy >= 2) and Const 22 (cycles >= 1)
must not cut off this optimum.

## Test 2 — Synthetic kappa with gaps (single stack)
File: `test/instances/synth_kappa_gaps.txt`
Stack 1, n=10, targets at code-heights {3, 5, 6, 7, 10}.
Sorted target heights: 3, 5, 6, 7, 10. Runs: {3}, {5,6,7}, {10}.
**kappa_1 = 3**, kappa_max = 3.
C_1 = 10 - 3 - 5 + 1 = 3. **total_C = 3.**

## Test 3 — Synthetic C with one target (single stack)
File: `test/instances/synth_C_one_target.txt`
Stack 1, n=5, target at code-height 3.
**C_1 = 5 - 3 - 1 + 1 = 2.** total_C = 2.
**kappa_1 = 1.** kappa_max = 1.

## Test 4 — Empty target stack
File: `test/instances/synth_empty_target_stack.txt`
Two stacks. Stack 1 n=3 with target at code-height 3; Stack 2 n=3 no targets.
- Stack 1: C = 3 - 3 - 1 + 1 = 0; kappa = 1.
- Stack 2: C = 0; kappa = 0  (verifies empty-stack short-circuit).
**total_C = 0**, **kappa_max = 1**. Both helpers must handle the zero-target case.

## How to verify from generated `.lp`
After building the model (no need to solve), look in `./model/<name>.lp`:
- `Const 20`: appears for each c in 0..n-2; an inequality of the form
  `y(c,*,*) - y(c+1,*,*) >= 0`. Expect `n-1` such rows (n = number of targets).
- `Const 21`: one row of the form `e(0) + e(1) + ... + e(n-1) >= total_C`.
- `Const 22`: one row of the form `y(0,*,*) + ... + y(n-1,*,*) >= kappa_max`.

Use `scripts/inspect_lp.py` to extract these RHS values and compare against the
expected numbers above.
