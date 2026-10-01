"""CP-SAT formulation of the SACRP-Optimization.

Implements Appendix A of the R1 paper (Side-Access Compact Retrieval
Problem). Three configurations (selectable via :class:`ModelConfig`):

1. Base   : Appendix A variables + state updates + accessibility +
            gravity-aware constraint disabled.
2. Gravity: Configuration 1 plus the gravity-aware consecutive-height
            constraint.
3. Cuts   : Configuration 2 plus cycle-symmetry breaking, energy lower
            bound, and (paper-intent) cycle lower bound.

Notation matches the brief verbatim. Targets are 0-indexed in Python
arrays; cycles and stacks are 1-indexed in paper notation and stored in
arrays indexed 1..n (cycles) and 1..T (stacks) so the index matches the
paper symbol directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from instance import Instance


@dataclass
class ModelConfig:
    """Selects which of the three ablation configurations to build."""

    gravity_aware: bool = False     # Configuration 2 toggle
    symmetry_break: bool = False    # Configuration 3 part 1
    energy_lb: bool = False         # Configuration 3 part 2
    cycle_lb: bool = False          # Configuration 3 part 3

    @classmethod
    def base(cls) -> "ModelConfig":
        return cls()

    @classmethod
    def with_gravity(cls) -> "ModelConfig":
        return cls(gravity_aware=True)

    @classmethod
    def with_cuts(cls) -> "ModelConfig":
        return cls(
            gravity_aware=True,
            symmetry_break=True,
            energy_lb=True,
            cycle_lb=True,
        )

    @property
    def label(self) -> str:
        if not (self.gravity_aware or self.symmetry_break or self.energy_lb or self.cycle_lb):
            return "base"
        if self.gravity_aware and not (self.symmetry_break or self.energy_lb or self.cycle_lb):
            return "gravity"
        if self.gravity_aware and self.symmetry_break and self.energy_lb and self.cycle_lb:
            return "cuts"
        return "custom"


@dataclass
class BuiltModel:
    """Bundle of the CP-SAT model and the handles needed for inspection."""

    model: cp_model.CpModel
    instance: Instance
    config: ModelConfig

    # Variables (kept for debugging / counts; not needed at solve time).
    gamma: List[cp_model.IntVar] = field(default_factory=list)
    alpha: Dict[Tuple[int, int], cp_model.IntVar] = field(default_factory=dict)
    beta: Dict[Tuple[int, int], cp_model.IntVar] = field(default_factory=dict)
    ell: Dict[Tuple[int, int], cp_model.IntVar] = field(default_factory=dict)
    e_var: Dict[Tuple[int, int], cp_model.IntVar] = field(default_factory=dict)
    n_var: Dict[Tuple[int, int], cp_model.IntVar] = field(default_factory=dict)
    h_c: Dict[Tuple[int, int], cp_model.IntVar] = field(default_factory=dict)

    # Pre-computed instance attributes.
    n_cycles: int = 0
    T: int = 0

    def proto_counts(self) -> Tuple[int, int, int]:
        """Return (#bool vars, #int vars, #constraints) from the model proto.

        OR-Tools represents Booleans as IntVars with domain [0, 1]. Counts
        are pre-presolve.
        """
        proto = self.model.Proto()
        n_bool = 0
        n_int = 0
        for v in proto.variables:
            dom = list(v.domain)
            if dom == [0, 1]:
                n_bool += 1
            else:
                n_int += 1
        return n_bool, n_int, len(proto.constraints)


def _maximal_runs_of_target_heights(target_heights: List[int]) -> int:
    """Number of maximal runs of consecutive heights among a set of target heights.

    Example: [1, 2, 4, 5, 6] -> 2 (runs {1,2} and {4,5,6}).
    """
    if not target_heights:
        return 0
    hs = sorted(set(target_heights))
    runs = 1
    for i in range(1, len(hs)):
        if hs[i] != hs[i - 1] + 1:
            runs += 1
    return runs


def build(instance: Instance, config: ModelConfig) -> BuiltModel:
    """Build the CP-SAT model for the given instance + configuration.

    Returns a :class:`BuiltModel` whose ``.model`` is ready to solve.
    """
    inst = instance
    n = inst.n_targets               # number of cycles in paper notation
    T = inst.T
    n_per_stack = inst.n_per_stack   # n(t), 0-indexed
    h_of_b = inst.targets_h          # h(b) for b in 0..n-1
    s_of_b = inst.targets_s          # s(b) for b in 0..n-1, 1-indexed stack

    if n == 0:
        raise ValueError(f"{inst.name}: no targets — formulation undefined")

    model = cp_model.CpModel()

    # ---- Index helpers ---------------------------------------------------
    cycles = range(1, n + 1)         # 1..n
    stacks = range(1, T + 1)         # 1..T
    targets = range(n)               # 0..n-1
    n_t = lambda t: n_per_stack[t - 1]   # n(t) for 1-indexed t

    # Group targets by stack (1-indexed key) for fast iteration.
    targets_in_stack: Dict[int, List[int]] = {t: [] for t in stacks}
    for b in targets:
        targets_in_stack[s_of_b[b]].append(b)

    # ---- Integer variables ----------------------------------------------
    # γ(b) ∈ {1, ..., n}
    gamma = [model.NewIntVar(1, n, f"gamma_b{b}") for b in targets]

    # ℓ(c, t), e(c, t), n_var(c, t) ∈ {0, ..., n(t)} for each c, t.
    ell: Dict[Tuple[int, int], cp_model.IntVar] = {}
    e_var: Dict[Tuple[int, int], cp_model.IntVar] = {}
    n_var: Dict[Tuple[int, int], cp_model.IntVar] = {}
    for c in cycles:
        for t in stacks:
            ell[(c, t)] = model.NewIntVar(0, n_t(t), f"ell_c{c}_t{t}")
            e_var[(c, t)] = model.NewIntVar(0, n_t(t), f"e_c{c}_t{t}")
            n_var[(c, t)] = model.NewIntVar(0, n_t(t), f"n_c{c}_t{t}")

    # h_c(b) ∈ {0, ..., h(b)} for each c, b.
    h_c: Dict[Tuple[int, int], cp_model.IntVar] = {}
    for c in cycles:
        for b in targets:
            h_c[(c, b)] = model.NewIntVar(0, h_of_b[b], f"hc_c{c}_b{b}")

    # ---- Reified Booleans -----------------------------------------------
    # α(c, b) ⇔ [γ(b) = c]
    # β(c, b) ⇔ [γ(b) < c]
    alpha: Dict[Tuple[int, int], cp_model.IntVar] = {}
    beta: Dict[Tuple[int, int], cp_model.IntVar] = {}
    for c in cycles:
        for b in targets:
            a = model.NewBoolVar(f"alpha_c{c}_b{b}")
            model.Add(gamma[b] == c).OnlyEnforceIf(a)
            model.Add(gamma[b] != c).OnlyEnforceIf(a.Not())
            alpha[(c, b)] = a

            bb = model.NewBoolVar(f"beta_c{c}_b{b}")
            model.Add(gamma[b] < c).OnlyEnforceIf(bb)
            model.Add(gamma[b] >= c).OnlyEnforceIf(bb.Not())
            beta[(c, b)] = bb

    # δ(c, b, b') ⇔ [h_c(b') ≥ h_c(b)] — defined only for s(b') < s(b).
    delta: Dict[Tuple[int, int, int], cp_model.IntVar] = {}
    for c in cycles:
        for b in targets:
            for bp in targets:
                if s_of_b[bp] < s_of_b[b]:
                    d = model.NewBoolVar(f"delta_c{c}_b{b}_bp{bp}")
                    model.Add(h_c[(c, bp)] >= h_c[(c, b)]).OnlyEnforceIf(d)
                    model.Add(h_c[(c, bp)] < h_c[(c, b)]).OnlyEnforceIf(d.Not())
                    delta[(c, b, bp)] = d

    # αδ(c, b, b') = α(c, b') ∧ δ(c, b, b') — only for s(b') < s(b).
    ad: Dict[Tuple[int, int, int], cp_model.IntVar] = {}
    for (c, b, bp), d in delta.items():
        ab = model.NewBoolVar(f"ad_c{c}_b{b}_bp{bp}")
        a_bp = alpha[(c, bp)]
        # ad ⇔ a_bp ∧ d
        model.AddBoolAnd([a_bp, d]).OnlyEnforceIf(ab)
        model.AddBoolOr([a_bp.Not(), d.Not()]).OnlyEnforceIf(ab.Not())
        ad[(c, b, bp)] = ab

    # ---- State updates ---------------------------------------------------
    # n_var(1, t) = n(t)
    for t in stacks:
        model.Add(n_var[(1, t)] == n_t(t))

    # n_var(c+1, t) = n_var(c, t) - Σ_{b: s(b)=t} α(c, b)
    for c in range(1, n):
        for t in stacks:
            alphas_in_t = [alpha[(c, b)] for b in targets_in_stack[t]]
            if alphas_in_t:
                model.Add(n_var[(c + 1, t)] == n_var[(c, t)] - sum(alphas_in_t))
            else:
                model.Add(n_var[(c + 1, t)] == n_var[(c, t)])

    # e(c, t) ≥ n_var(c, t) - ℓ(c, t)  and  ℓ(c, t) ≤ n_var(c, t)
    for c in cycles:
        for t in stacks:
            model.Add(e_var[(c, t)] >= n_var[(c, t)] - ell[(c, t)])
            model.Add(ell[(c, t)] <= n_var[(c, t)])

    # h_c(b) = h(b) - Σ_{b': s(b')=s(b), h(b')<h(b)} β(c, b')
    for c in cycles:
        for b in targets:
            below = [
                beta[(c, bp)]
                for bp in targets_in_stack[s_of_b[b]]
                if h_of_b[bp] < h_of_b[b]
            ]
            if below:
                model.Add(h_c[(c, b)] == h_of_b[b] - sum(below))
            else:
                model.Add(h_c[(c, b)] == h_of_b[b])

    # ---- Accessibility (own stack), enforced when α(c, b) = 1 ----------
    # Heights are 0-indexed in the parser, so h(b) ∈ [0, n(s(b))-1]. With that,
    # the brief's "+1" is consistent with the domain ℓ ∈ [0, n(t)]: for a
    # target at the top of its own stack (h = n(t)-1), h_c+1 = n(t), exactly
    # the upper bound. Keep the brief verbatim.
    for c in cycles:
        for b in targets:
            sb = s_of_b[b]
            a = alpha[(c, b)]
            # ℓ(c, s(b)) ≥ h_c(b) + 1
            model.Add(ell[(c, sb)] >= h_c[(c, b)] + 1).OnlyEnforceIf(a)
            # ℓ(c, s(b)) ≤ h_c(b) + 1 + Σ_{b': s(b')=s(b), h(b')>h(b)} α(c, b')
            higher_in_same = [
                alpha[(c, bp)]
                for bp in targets_in_stack[sb]
                if h_of_b[bp] > h_of_b[b]
            ]
            if higher_in_same:
                model.Add(
                    ell[(c, sb)] <= h_c[(c, b)] + 1 + sum(higher_in_same)
                ).OnlyEnforceIf(a)
            else:
                model.Add(ell[(c, sb)] <= h_c[(c, b)] + 1).OnlyEnforceIf(a)
            # n_var(c, s(b)) ≥ h_c(b) + 1
            model.Add(n_var[(c, sb)] >= h_c[(c, b)] + 1).OnlyEnforceIf(a)

    # ---- Accessibility (tunnel stacks t < s(b)), enforced when α(c, b) = 1
    # Strict two-sided ℓ pinning per the brief and paper Section 2.1.
    # ("Tunnel relaxation reverted — strict equality is correct under the
    # paper's Section 2.1 model. Relaxation was directed in error during
    # debugging; correct behavior is two-sided ℓ pinning per the brief.")
    for c in cycles:
        for b in targets:
            a = alpha[(c, b)]
            sb = s_of_b[b]
            for t in range(1, sb):
                ads = [ad[(c, b, bp)] for bp in targets_in_stack[t]]
                if ads:
                    rhs = h_c[(c, b)] + sum(ads)
                else:
                    rhs = h_c[(c, b)]
                model.Add(ell[(c, t)] <= rhs).OnlyEnforceIf(a)
                model.Add(ell[(c, t)] >= rhs).OnlyEnforceIf(a)
                model.Add(n_var[(c, t)] >= h_c[(c, b)]).OnlyEnforceIf(a)

    # ---- Gravity-aware consecutive-height constraint (Config 2+) -------
    if config.gravity_aware:
        for t in stacks:
            ts = targets_in_stack[t]
            if len(ts) < 3:
                continue
            # All ordered triples (b1, b2, b3) with h(b1) < h(b3) < h(b2),
            # all in stack t. Enumerate all C(k, 3) unordered triples and
            # pick the middle one by sorted h.
            ts_sorted_by_h = sorted(ts, key=lambda b: h_of_b[b])
            k = len(ts_sorted_by_h)
            for i in range(k):
                for j in range(i + 1, k):
                    for m in range(j + 1, k):
                        b1 = ts_sorted_by_h[i]
                        b3 = ts_sorted_by_h[j]
                        b2 = ts_sorted_by_h[m]
                        assert h_of_b[b1] < h_of_b[b3] < h_of_b[b2]
                        for c in cycles:
                            # α(c,b1) ∧ α(c,b2) → α(c,b3) ∨ β(c,b3)
                            model.AddBoolOr([
                                alpha[(c, b1)].Not(),
                                alpha[(c, b2)].Not(),
                                alpha[(c, b3)],
                                beta[(c, b3)],
                            ])

    # ---- Active-cycle indicators z[c] = OR_b α(c, b) -------------------
    # Used by both the sym-break and the (paper-intent) cycle LB cut.
    z: List[cp_model.IntVar] = []
    if config.symmetry_break or config.cycle_lb:
        z = [model.NewBoolVar(f"z_c{c}") for c in cycles]
        for idx, c in enumerate(cycles):
            # α(c, b) = 1 → z[c] = 1
            for b in targets:
                model.AddImplication(alpha[(c, b)], z[idx])
            # z[c] = 1 → at least one α(c, b) = 1
            model.AddBoolOr([alpha[(c, b)] for b in targets]).OnlyEnforceIf(z[idx])

    # ---- Cycle-symmetry breaking (Config 3) ----------------------------
    # Paper §4.3: "Active cycles must precede empty ones."
    # MIP form: Σ_{b,i} y(c,b,i) ≥ Σ_{b,i} y(c+1,b,i) where y is the
    # *anchoring indicator* (≤1 per cycle, per constraint (15) in Model 1).
    # The brief's literal "Σ α(c,b) ≥ Σ α(c+1,b)" reads as "bigger batch
    # first" — that's a strictly tighter, *invalid* cut in this model
    # because n_var[c] depends on previous-cycle retrievals (confirmed on
    # Instance_1/3/4/28: brief's literal yields obj > MIP optimum). Use
    # the active-cycle form: z[c] ≥ z[c+1].
    if config.symmetry_break:
        for c_idx in range(n - 1):
            model.Add(z[c_idx] >= z[c_idx + 1])

    # ---- Energy lower bound (Config 3) ---------------------------------
    # C_t = # non-targets in stack t strictly above the lowest target.
    # With 0-indexed heights, heights > h_min in stack t are
    # {h_min+1, ..., n(t)-1}, i.e. n(t) - 1 - h_min positions.
    if config.energy_lb:
        total_C = 0
        for t in stacks:
            ts = targets_in_stack[t]
            if not ts:
                continue
            h_min = min(h_of_b[b] for b in ts)
            positions_above = n_t(t) - 1 - h_min
            targets_above = sum(1 for b in ts if h_of_b[b] > h_min)
            C_t = positions_above - targets_above
            total_C += C_t
        if total_C > 0:
            model.Add(
                sum(e_var[(c, t)] for c in cycles for t in stacks) >= total_C
            )

    # ---- Cycle lower bound (Config 3) — paper-intent: # used cycles ≥ max κ
    # Brief literally states "Σ_c Σ_b α(c, b) ≥ max_t κ(t)" which is
    # vacuous in CP-SAT (LHS = n always). User directed: use paper intent
    # (number of non-empty cycles ≥ max_t κ(t)). z[c] reused from above.
    if config.cycle_lb:
        max_kappa = max(
            (_maximal_runs_of_target_heights([h_of_b[b] for b in targets_in_stack[t]])
             for t in stacks),
            default=0,
        )
        if max_kappa > 0:
            model.Add(sum(z) >= max_kappa)

    # ---- Objective -------------------------------------------------------
    model.Minimize(sum(e_var[(c, t)] for c in cycles for t in stacks))

    return BuiltModel(
        model=model,
        instance=inst,
        config=config,
        gamma=gamma,
        alpha=alpha,
        beta=beta,
        ell=ell,
        e_var=e_var,
        n_var=n_var,
        h_c=h_c,
        n_cycles=n,
        T=T,
    )


# ----------------------------------------------------------------------------
# Solve helper
# ----------------------------------------------------------------------------

@dataclass
class SolveResult:
    instance: str
    config_label: str
    status: str           # OPTIMAL / FEASIBLE / INFEASIBLE / MODEL_INVALID / UNKNOWN
    objective: float      # NaN if no feasible solution
    best_bound: float     # solver's best objective bound (LB for minimization); NaN if no solution
    gap: float            # (objective - best_bound)/objective, matching MIP's Gap; NaN if no solution
    runtime_s: float
    wall_time_s: float
    num_bool_vars: int
    num_int_vars: int
    num_constraints: int
    num_search_workers_param: str = "num_search_workers"  # for the summary log


def solve(built: BuiltModel, time_limit_s: float = 600.0, log_path: str | None = None,
          wall_clock_backstop_s: float | None = None,
          ) -> SolveResult:
    """Solve a built model. Single-threaded by construction.

    Two cap mechanisms:
      1. ``solver.parameters.max_time_in_seconds = time_limit_s`` — the
         primary cap. This is what OR-Tools' own scheduler uses; it's
         checked between search nodes / propagation rounds.
      2. **Wall-clock backstop** (``wall_clock_backstop_s``, default
         ``time_limit_s + 50``): a ``threading.Timer`` fires
         ``solver.StopSearch()`` after this many seconds. Catches the
         rare case where the primary cap isn't checked during a long
         propagation phase (observed once on Instance_287/gravity, which
         overran to 1153 s with the primary cap alone in OR-Tools 9.15).
         Pass ``0`` to disable the backstop.
    """
    import math
    import threading
    import time

    if wall_clock_backstop_s is None:
        wall_clock_backstop_s = time_limit_s + 50.0

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 1  # OR-Tools 9.15 name
    if log_path is not None:
        solver.parameters.log_search_progress = True
        solver.log_callback = _LogCapture(log_path).write  # type: ignore[assignment]

    n_bool, n_int, n_cons = built.proto_counts()

    timer: threading.Timer | None = None
    backstop_fired = False
    if wall_clock_backstop_s > 0:
        def _fire():
            nonlocal backstop_fired
            backstop_fired = True
            solver.StopSearch()
        timer = threading.Timer(wall_clock_backstop_s, _fire)
        timer.daemon = True
        timer.start()

    t0 = time.perf_counter()
    try:
        status_int = solver.Solve(built.model)
    finally:
        if timer is not None:
            timer.cancel()
    wall = time.perf_counter() - t0

    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }
    status = status_map.get(status_int, str(status_int))
    if backstop_fired and status not in ("OPTIMAL", "INFEASIBLE", "MODEL_INVALID"):
        # Tag overrun-killed solves so the summary can distinguish them
        # from natural primary-cap returns.
        status = f"{status}_BACKSTOP"
    if status.startswith("OPTIMAL") or status.startswith("FEASIBLE"):
        obj = solver.ObjectiveValue()
        bound = solver.BestObjectiveBound()
        # Match MIP's Gap definition: (obj - LB)/obj. max(0,.) guards tiny
        # numerical overshoot; obj==0 guards division by zero.
        gap = 0.0 if obj == 0 else max(0.0, (obj - bound) / abs(obj))
    else:
        obj = math.nan
        bound = math.nan
        gap = math.nan

    return SolveResult(
        instance=built.instance.name,
        config_label=built.config.label,
        status=status,
        objective=obj,
        best_bound=bound,
        gap=gap,
        runtime_s=solver.WallTime(),
        wall_time_s=wall,
        num_bool_vars=n_bool,
        num_int_vars=n_int,
        num_constraints=n_cons,
    )


class _LogCapture:
    """Tiny helper to redirect CP-SAT log callback output to a file."""

    def __init__(self, path: str):
        self._path = path
        # Truncate / create.
        with open(path, "w", encoding="utf-8") as fp:
            fp.write("")

    def write(self, line: str) -> None:
        with open(self._path, "a", encoding="utf-8") as fp:
            fp.write(line)
            if not line.endswith("\n"):
                fp.write("\n")
