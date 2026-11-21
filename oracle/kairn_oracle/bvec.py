"""Ball vectors and the accumulator: the claims of their kernels, and their judges.

architecture.md, "Ball vectors", "The accumulator", "Claims of Milestone 2" (the forms of `upper`,
`error`, `finite_or_nan` and `rounded` these kernels use, and the requirement `at_most`).  Hooked
into claims.py, check.py and extended.py as intervals.py is; the folds of the ball vectors are in
bvfolds.py.

The kernels of the radii (bv_add_radius_k, bv_scale_radius_k, conv_radius, bv_mul_pow2_radius):

    upper rz value=EXPR                       rz >= EXPR (exactly), whether rz is finite or the
                                              rounding has overflowed to +inf; nothing is said of
                                              how far above.  EXPR may hold abs(NAME) of an input.
    upper rz value=EXPR unless=M              when the mask input M is false, rz >= EXPR; when it
                                              is true, nothing is said.
    upper rz value=EXPR exact_when=[...]      rz >= EXPR, and rz = EXPR exactly when every
                                              condition holds; a condition {"mask": M} holds when
                                              the mask input M is true.
    at_most(NAME, K)                          a requirement: NAME <= K, K a positive integer.

Such a kernel has only such entries and is judged on every line (judge_radius): a NaN or -inf
output fails, +inf passes (and is suspicious where the stated value is below Omega/4).  But
conv_radius (FINITE_RESULTS): by the ruling of 2026-11-21 (architecture.md, "Claims of the
non-finite layer" and "Claims of Milestone 2") its claim is of finite results, and a result that is
not finite claims only that it is +inf or a NaN: either passes and is counted (never suspicious),
-inf fails, a finite result is judged as for every radius kernel.

The steps of the scalings by a power of two (bv_mul_pow2_step_k): `error` with `exact_flag`, the
mask output that is true exactly when every condition of the entry's exact_when holds (where
output limb 0 is finite, as for the rest of the entry).

The finishes (extended domain): `finite_or_nan` with `nonneg` (bv_make_finish: the value must
also not be below zero, either zero is not) and with `if_all` (bv_conv_finish: every mask of the
list true).

The accumulator (acc_add_k, acc_mul_k, acc_merge_k): `rounded` with a value of its own, an
expression of the inputs and their limbs NAME[I]: the output is that expression rounded, where the
leading limb of its own output group is finite (judge_acc, every entry where its group is finite).
"""

from fractions import Fraction

# The fields these kernels add to kinds that exist (claims.Entry.KNOWN), defined before the import
# of claims.py, which imports this module last (as intervals.py) and reads them.
ADDED_FIELDS = {"upper": {"unless", "exact_when"}, "error": {"exact_flag"},
                "finite_or_nan": {"nonneg", "if_all"}, "rounded": {"value"}}

from . import cexpr as CX  # noqa: E402
from . import expr as EX  # noqa: E402
from . import fmt as F  # noqa: E402
from .claims import ClaimsError, EXACT_CONDITIONS, Format, eval_const, format_u_eta  # noqa: E402

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN

# Statistics (the guards read them).
UP_FINITE = "output finite, at least the stated value"
UP_INF = "output +inf"
UP_EXACT = "output the stated value exactly"
UP_UNLESS = "%s true: nothing claimed"
UP_EW_HOLDS = "exact_when holds"
UP_EW_FAILS = "exact_when fails: "
UP_EW_BEYOND = "exact_when holds, the stated value beyond Omega: the equality not judged"
UP_NONFINITE = "output not finite (+inf or a NaN): nothing more claimed"
UP_NAN = "output a NaN"
UP_EXCESS = "(output - value) / value"
UP_GAPS = "excess over a positive stated value, in gaps of the output"
FLAG_TRUE = "exact_flag true"
FLAG_FALSE = "exact_flag false"
FIN_MASK_TRUE = "every mask true"
FIN_MASK_FALSE = "a mask false: %s"
FIN_NEG = "value finite, below zero"
FIN_ZERO = "value zero"
FIN_POS = "value finite, above zero"
FIN_NAN = "value: NaN"
FIN_PINF = "value: +inf"
FIN_NINF = "value: -inf"
ACC_EXACT = "exact"
ACC_TIE = "tie"
ACC_INEXACT = "inexact"
ACC_BEYOND = "the exact value rounds beyond Omega"
GROUP_NONFINITE = "the leading limb of its output is not finite: nothing claimed"
GROUP_TAIL = "a lower limb of its output is not finite: nothing claimed"

# The radius kernels whose upper entries are claimed of finite results only: the ruling
# of 2026-11-21 on conv_radius (architecture.md, "Claims of the non-finite layer", "Claims of
# Milestone 2").  A result that is not finite claims only that it is +inf or a NaN, never a
# negative number or -inf; the product of BallVectors that calls it turns such a radius into the
# whole space, and its own claim covers that.  The claims file writes the entry as it writes the
# other radius kernels' (upper with a value and no if), so the name comes from the ruling; the
# other radius kernels keep the reading of architecture.md's sentence on them (at least the value,
# finite or +inf).
FINITE_RESULTS = ("conv_radius",)


# ---------------------------------------------------------------------------
# Reading

def check_upper_fields(raw, where):
    """unless and exact_when belong to an upper entry with a value of its own and neither if nor
    gaps (architecture.md, the table of the scaling of a BallVector by a power of two)."""
    if ("unless" in raw or "exact_when" in raw) and (
            "if" in raw or "gaps" in raw or "value" not in raw):
        raise ClaimsError("%s: unless and exact_when belong to an upper entry with a value of its "
                          "own and neither if nor gaps" % where)


def _mask_input(kernel, name, where, what):
    if not isinstance(name, str) or name not in kernel.input_names or name not in kernel.masks:
        raise ClaimsError("%s: %s must name a mask input, got %r" % (where, what, name))
    return name


def read_upper(e, kernel, raw, where):
    """{"kind": "upper", "of": R, "value": EXPR} with, at most one of them, "unless": M or
    "exact_when": [CONDITION, ...]: R >= EXPR exactly, unconditionally (unless: where the mask
    input M is false; exact_when: and R = EXPR where every condition holds)."""
    if "gaps" in raw:
        raise ClaimsError("%s: an upper entry has gaps, or a value of its own, not both" % where)
    if kernel.extended:
        raise ClaimsError("%s: an upper entry with a value of its own is read in the finite "
                          "domain" % where)
    e.gaps = None
    e.cond = None
    e.bv = True
    text = raw["value"]
    try:
        tree = CX.parse(text, abs_ok=True)
    except CX.CExprError as ex:
        raise ClaimsError("%s: value: %s" % (where, ex))
    ins = dict(kernel.inputs)
    outs = dict(kernel.outputs)
    clash = [n for n in list(ins) + list(outs) if n in CX.RESERVED or n == "abs"]
    if clash:
        raise ClaimsError("%s: the kernel has an input or output named %s, which these expressions "
                          "read as a constant or a function" % (where, clash[0]))
    for n in CX.names(tree):
        if n in kernel.masks:
            raise ClaimsError("%s: %r is a mask, not a value" % (where, n))
        if n in ins or (n in outs and outs[n] == 1):
            continue
        raise ClaimsError("%s: %r is not a limb input or a one-limb output" % (where, n))
    for n in _abs_names(tree):
        if n not in ins:
            raise ClaimsError("%s: abs(%s): abs( ) is of an input" % (where, n))
    e.cvalue = tree
    e.cvalue_text = str(text).strip()
    e.unless = None
    e.uexact = None
    if "unless" in raw:
        if "exact_when" in raw:
            raise ClaimsError("%s: an upper entry has unless or exact_when, not both" % where)
        e.unless = _mask_input(kernel, raw["unless"], where, "unless")
    if "exact_when" in raw:
        e.uexact = _read_conditions(kernel, raw["exact_when"], where, masks=True)


def _abs_names(tree, out=None):
    out = [] if out is None else out
    if tree[0] == "abs":
        out.append(tree[1][1])
    elif tree[0] in ("neg", "+", "-", "*", "/", "^"):
        for sub in tree[1:]:
            _abs_names(sub, out)
    return out


def _read_conditions(kernel, ew, where, masks):
    """[("mask", NAME) or (tree, text, op, K)]: the conditions of an exact_when list, as
    claims.Entry._read_exact_when reads them, and with masks {"mask": NAME} of a mask input."""
    if not isinstance(ew, list) or not ew:
        raise ClaimsError("%s: exact_when must be a nonempty list of conditions (absent when there "
                          "is none)" % where)
    out = []
    ins = dict(kernel.inputs)
    seen = set()
    for j, cond in enumerate(ew):
        w = "%s: exact_when[%d]" % (where, j)
        if masks and isinstance(cond, dict) and "mask" in cond:
            if set(cond) != {"mask"}:
                raise ClaimsError("%s must be {\"mask\": NAME}, got %r" % (w, cond))
            m = _mask_input(kernel, cond["mask"], w, "mask")
            if m in seen:
                raise ClaimsError("%s: the mask %s twice" % (w, m))
            seen.add(m)
            out.append(("mask", m))
            continue
        ops = [k for k in EXACT_CONDITIONS if isinstance(cond, dict) and k in cond]
        if len(ops) != 1 or set(cond) != {ops[0], "than"}:
            raise ClaimsError("%s must be {\"zero_or_abs_gt\": EXPR, \"than\": K}, "
                              "{\"zero_or_abs_ge\": EXPR, \"than\": K}%s, got %r"
                              % (w, " or {\"mask\": NAME}" if masks else "", cond))
        op = ops[0]
        text = cond[op]
        if not isinstance(text, str):
            raise ClaimsError("%s: %s must be an expression" % (w, op))
        try:
            tree = EX.parse(text, limbs=True)
        except EX.ExprError as ex:
            raise ClaimsError("%s: %s" % (w, ex))
        for n in EX.names(tree):
            if n not in ins or n in kernel.masks:
                raise ClaimsError("%s: %r is not a limb input" % (w, n))
        for n, i in EX.limb_refs(tree):
            if i >= ins[n]:
                raise ClaimsError("%s: %s[%d] is not a limb of %s, which has %d" % (
                    w, n, i, n, ins[n]))
        k = cond["than"]
        u, eta = format_u_eta(Format(53, -1074, 971))
        if eval_const(k, u, eta) <= 0:
            raise ClaimsError("%s: than %r is not positive" % (w, k))
        out.append((tree, text.strip(), op, k))
    if masks and all(c[0] == "mask" for c in out):
        raise ClaimsError("%s: exact_when of masks alone states no condition on the values" % where)
    return out


def read_exact_flag(e, kernel, raw, where):
    """"exact_flag": M of an error entry with exact_when: the mask output M is true exactly when
    every condition holds."""
    if "exact_when" not in raw:
        raise ClaimsError("%s: exact_flag belongs to an error entry with exact_when" % where)
    m = raw["exact_flag"]
    if not isinstance(m, str) or m not in dict(kernel.outputs) or m not in kernel.masks:
        raise ClaimsError("%s: exact_flag must name a mask output, got %r" % (where, m))
    e.exact_flag = m


def read_finish_fields(e, kernel, raw, where):
    """"nonneg": true (with if, without steps) and "if_all": [M1, M2, ...] (two mask inputs or more,
    without if, steps or nonneg) of a finite_or_nan entry."""
    e.nonneg = False
    e.if_all = None
    if "nonneg" in raw:
        if raw["nonneg"] is not True:
            raise ClaimsError("%s: nonneg is written only where it is true, got %r"
                              % (where, raw["nonneg"]))
        if "if" not in raw or "steps" in raw:
            raise ClaimsError("%s: nonneg belongs to a finite_or_nan entry with if and without "
                              "steps" % where)
        e.nonneg = True
    if "if_all" in raw:
        lst = raw["if_all"]
        if "if" in raw or "steps" in raw or "nonneg" in raw:
            raise ClaimsError("%s: if_all is written without if, steps or nonneg" % where)
        if not isinstance(lst, list) or len(lst) < 2 or len(set(map(str, lst))) != len(lst):
            raise ClaimsError("%s: if_all must list two distinct mask inputs or more, got %r"
                              % (where, lst))
        e.if_all = [_mask_input(kernel, m, where, "if_all") for m in lst]
    if (e.nonneg or e.if_all) and kernel.limbs_of(e.operand) != 1:
        raise ClaimsError("%s: nonneg and if_all are of a value of one limb" % where)


def read_rounded_value(e, kernel, raw, where):
    """"value": EXPR of a rounded entry: the output is EXPR rounded, EXPR an expression of the
    inputs and their limbs NAME[I] (+ - *, unary minus, abs( )), in the finite domain."""
    if kernel.extended:
        raise ClaimsError("%s: a rounded entry with a value of its own is of the finite domain"
                          % where)
    if e.when is not None:
        raise ClaimsError("%s: a rounded entry has when or a value of its own, not both" % where)
    text = raw["value"]
    if not isinstance(text, str):
        raise ClaimsError("%s: value must be an expression" % where)
    try:
        tree = EX.parse(text, limbs=True)
    except EX.ExprError as ex:
        raise ClaimsError("%s: value: %s" % (where, ex))
    ins = dict(kernel.inputs)
    for n in EX.names(tree):
        if n not in ins or n in kernel.masks:
            raise ClaimsError("%s: value: %r is not a limb input" % (where, n))
    for n, i in EX.limb_refs(tree):
        if i >= ins[n]:
            raise ClaimsError("%s: value: %s[%d] is not a limb of %s, which has %d" % (
                where, n, i, n, ins[n]))
    e.own_tree = tree
    e.own_text = text.strip()


def read_requirement(kernel, r, limbs):
    """at_most(NAME, K): the one-limb input NAME is at most the positive integer K (finite
    domain).  True when r is one."""
    import re
    m = re.match(r"\s*at_most\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([0-9]+)\s*\)\s*\Z", r)
    if m is None:
        return False
    n, k = m.group(1), int(m.group(2))
    if n not in kernel.input_names or n in kernel.masks or limbs[n] != 1:
        raise ClaimsError("%s: requirement %r: at_most() is of a one-limb input" % (kernel.name, r))
    if k < 1:
        raise ClaimsError("%s: requirement %r: the bound of at_most() is a positive integer"
                          % (kernel.name, r))
    if kernel.extended:
        raise ClaimsError("%s: requirement %r: at_most() is read in the finite domain"
                          % (kernel.name, r))
    if any(x[0] == "at_most" and x[1] == n for x in kernel.requires):
        raise ClaimsError("%s: requirement %r: at_most() of %s twice" % (kernel.name, r, n))
    kernel.requires.append(("at_most", n, k))
    return True


def finish_kernel(kernel):
    """A kernel with upper entries of a value of its own and no if (the radius kernels) has only
    such entries, of the finite domain; a rounded entry with a value of its own is of a kernel
    judged entry by entry, each where its group is finite."""
    radius = [e for e in kernel.ensures if getattr(e, "bv", False)]
    if radius and len(radius) != len(kernel.ensures):
        raise ClaimsError("%s: upper entries with a value of their own and no if are read in a "
                          "kernel whose every entry is one" % kernel.name)
    kernel.bv_radius = bool(radius)
    for e in radius:
        e.finite_results = kernel.name in FINITE_RESULTS
    kernel.acc = any(getattr(e, "own_tree", None) is not None for e in kernel.ensures)


def label(e):
    of = "+".join(e.of)
    s = "upper(%s) >= %s" % (of, e.cvalue_text)
    if e.unless is not None:
        s += " unless %s" % e.unless
    if e.uexact is not None:
        s += ", exactly when %s" % " and ".join(
            "%s true" % c[1] if c[0] == "mask" else "(%s = 0 or |%s| %s %s)" % (
                c[1], c[1], ">" if c[2] == "zero_or_abs_gt" else ">=", c[3]) for c in e.uexact)
    return s


def label_suffix(e):
    """What the new fields add to the label of an entry of a kind that exists."""
    s = ""
    if getattr(e, "exact_flag", None):
        s += ", exact_flag %s" % e.exact_flag
    if getattr(e, "nonneg", False):
        s += ", not below zero"
    if getattr(e, "if_all", None):
        s += " if all of %s" % ", ".join(e.if_all)
    if getattr(e, "own_tree", None) is not None:
        s += " of %s" % e.own_text
    return s


# ---------------------------------------------------------------------------
# Plans

def plan_upper(pl, e, claims):
    """The plan of an upper entry with a value of its own and no if."""
    fmt = pl.fmt
    c = {"bv": True, "tree": e.cvalue, "unless": None, "conds": None,
         "finite_results": getattr(e, "finite_results", False)}
    if e.unless is not None:
        c["unless"] = pl.in_slices[e.unless][0]
    if e.uexact is not None and pl.in_scope:
        conds = []
        for j, cond in enumerate(e.uexact):
            if cond[0] == "mask":
                slot = pl.in_slices[cond[1]][0]
                conds.append((lambda x, slot=slot: x[slot] == 1, "%s true" % cond[1]))
                continue
            tree, text, op, k = cond
            conds.append((_condition(pl, tree, op, k, text), "%s = 0 or |%s| %s %s" % (
                text, text, ">" if op == "zero_or_abs_gt" else ">=", k)))
        c["conds"] = conds
    if pl.in_scope:
        units = {}
        for _f, kn in CX.calls(e.cvalue):
            if claims is None:
                raise ClaimsError("%s: unit(%s) needs the claims" % (pl.kernel.name, kn))
            units[kn] = claims.unit_tiny(kn, fmt)
        c["units"] = units
        c["u"], c["eta"] = format_u_eta(fmt)
    return c


def _condition(pl, tree, op, k, text):
    src, s = EX.compile_tree(tree, pl._leaf)
    fn = EX.make_function(["x"], src)
    u, eta = format_u_eta(pl.fmt)
    K = eval_const(k, u, eta)
    if K <= 0:
        raise ClaimsError("%s: exact_when %s: than %r is not positive in %s" % (
            pl.kernel.name, text, k, pl.fmt.name))
    n, d = K.numerator, K.denominator
    ls, rs = (s, 0) if s >= 0 else (0, -s)
    strict = op == "zero_or_abs_gt"

    def holds(x):
        v = fn(x)
        if v == 0:
            return True
        a, b = (abs(v) * d) << ls, n << rs
        return a > b if strict else a >= b
    return holds


def plan_exact_flag(pl, e):
    return {"exact_flag": pl.out_slices[e.exact_flag][0]}


def plan_finish(pl, e):
    """finite_or_nan with nonneg or if_all."""
    masks = [e.cond_in] if e.cond_in is not None else list(e.if_all or [])
    return {"bvfinish": ([pl.in_slices[m][0] for m in masks], masks, bool(e.nonneg))}


def plan_rounded(pl, e):
    """A rounded entry with a value of its own: the value as a function of the inputs and its
    scale."""
    src, sv = EX.compile_tree(e.own_tree, pl._leaf)
    return {"own": (EX.make_function(["x"], src), sv)}


def plan_requirement(pl, r):
    """at_most(NAME, K): (kind, name, slice, K, qmin) for Checker.violated."""
    return ("at_most", r[1], pl.in_slices[r[1]], r[2], pl.fmt.qmin)


def at_most_violated(r, x):
    """NAME > K, with NAME the fixed value N, N 2^qmin."""
    lo, hi = r[2]
    v, k, q = sum(x[lo:hi]), r[3], r[4]
    return (v << q) > k if q >= 0 else v > (k << -q)


# ---------------------------------------------------------------------------
# Judges of the finite domain

def _out_member(fmt, v):
    return v != F.OUTSIDE and (type(v) is not int or F.is_member(fmt, v))


def _small(pl, x, v=None):
    """Every input limb, every input value and the stated value v (a Fraction) below Omega/4."""
    fmt = pl.fmt
    q4 = fmt.omega
    if not all(4 * abs(t) < q4 for i, t in enumerate(x) if i not in pl.in_masks):
        return False
    if not all(4 * abs(sum(x[lo:hi])) < q4 for lo, hi in pl.groups):
        return False
    if v is not None:
        om = Fraction(fmt.omega) * format_u_eta(fmt)[1]
        return 4 * abs(v) < om
    return True


def small_inputs(pl, x):
    """Every input limb and every input value below Omega/4 (the finite layer's test of a
    suspicious result, oracle/README.md, "check")."""
    return _small(pl, x)


def small_stated(pl, c, x, z):
    """The stated value of an upper entry under a mask below Omega/4 in magnitude, or a value that
    names an output that is not finite (taken as small: no output-free value says otherwise)."""
    if c["kind"] != "upper":
        return True
    eta = format_u_eta(pl.fmt)[1]
    names = {}
    for n, (lo, hi) in pl.in_slices.items():
        if n not in pl.kernel.masks:
            names[n] = sum(x[lo:hi]) * eta
    for n, (lo, hi) in pl.out_slices.items():
        if hi - lo == 1 and lo not in pl.out_masks and type(z[lo]) is int:
            names[n] = z[lo] * eta
    env = {"u": pl.u, "eta": eta, "names": names,
           "unit": lambda k: pl.units[k][0], "tiny": lambda k: pl.units[k][1]}
    try:
        v = CX.evaluate(c["trees"][0], env)
    except (CX.CExprError, KeyError):
        return True
    return 4 * abs(v) < Fraction(pl.fmt.omega) * eta


def judge_radius(ck, pl, st, x, z, line):
    """Every entry an upper with a value of its own and no if: R >= EXPR exactly (where the mask of
    unless is false), R = EXPR where every condition of exact_when holds; a finite R, or +inf
    (the rounding overflowed: still at least EXPR); a NaN or -inf output fails."""
    fmt = pl.fmt
    for i, v in enumerate(z):
        if i not in pl.out_masks and not _out_member(fmt, v):
            ck._fail(st, line, "output limb not a number of the format")
            return
    st.c["judged"] += 1
    reasons, sus = radius_entries(pl, st.entries, x, z, line)
    if sus:
        st.c["suspicious"] += 1
        st.example("suspicious", line, "; ".join(sus), ck.max_examples)
    if reasons:
        st.c["failed"] += 1
        for r in reasons:
            st.reason(r)
        st.example("failure", line, "; ".join(reasons), ck.max_examples)
    else:
        st.c["passed"] += 1


def radius_reasons(pl, ents, x, z, line):
    """The failures of a radius kernel's claims on its inputs x and output z (the radius of a ball
    vector, V3), with the statistics in ents: its upper entries with a value, or its rounding to
    nearest of its value (bv_neg_radius)."""
    if getattr(pl.kernel, "bv_radius", False):
        reasons, _sus = radius_entries(pl, ents, x, z, line)
        return reasons
    out = []
    fmt = pl.fmt
    for i, c in enumerate(pl.entries):
        es = ents[i]
        es.applicable += 1
        r = F.rn(fmt, pl.value_fn(x), pl.sv)
        es.count(ACC_EXACT if type(r) is int and (r << pl.sh_out) == (pl.value_fn(x) << pl.sh_val)
                 else ACC_INEXACT)
        if z[c["first"]] != r:
            es.failures += 1
            out.append("rounded(%s): the radius is not its value rounded to nearest"
                       % "+".join(pl.kernel.ensures[i].of))
    return out


def radius_entries(pl, ents, x, z, line):
    """(reasons, suspicious) of every entry of a radius kernel (an upper with a value of its own and
    no if), with the statistics in ents."""
    fmt = pl.fmt
    eta = format_u_eta(fmt)[1]
    names = {}
    for n, (lo, hi) in pl.in_slices.items():
        if n not in pl.kernel.masks:
            names[n] = sum(x[lo:hi]) * eta
    for n, (lo, hi) in pl.out_slices.items():
        if hi - lo == 1 and lo not in pl.out_masks and type(z[lo]) is int:
            names[n] = z[lo] * eta
    reasons, sus = [], []
    for i, c in enumerate(pl.entries):
        es = ents[i]
        o = z[c["first"]]
        if c["unless"] is not None and x[c["unless"]] == 1:
            es.count(UP_UNLESS % pl.kernel.ensures[i].unless)
            continue
        es.applicable += 1
        env = {"u": c["u"], "eta": c["eta"], "names": names,
               "unit": lambda k, c=c: c["units"][k][0], "tiny": lambda k, c=c: c["units"][k][1]}
        try:
            v = CX.evaluate(c["tree"], env)
        except (CX.CExprError, KeyError) as ex:
            es.failures += 1
            reasons.append("upper: the stated value does not exist (%s)" % ex)
            continue
        why = None
        conds_hold = None
        if c["conds"] is not None:
            failing = [t for h, t in c["conds"] if not h(x)]
            for t in failing:
                es.count(UP_EW_FAILS + t)
            conds_hold = not failing
            if conds_hold:
                es.count(UP_EW_HOLDS)
                if v > Fraction(fmt.omega) * eta:
                    # No number of the format is the stated value: in the finite domain an exact
                    # result beyond Omega is outside the statement, as everywhere (oracle/README.md,
                    # "Ball vectors and the accumulator").
                    es.count(UP_EW_BEYOND)
                    conds_hold = False
        if c["finite_results"] and o in (INF, NAN):
            # The ruling of 2026-11-21 (FINITE_RESULTS): the claim is of finite results, and one
            # that is not finite claims only that it is +inf or a NaN, which it is.  Counted;
            # never suspicious, whatever the operands.
            es.count(UP_NONFINITE)
            es.count(UP_INF if o == INF else UP_NAN)
        elif o == NAN or o == NINF:
            why = "upper: the output is %s, not at least the stated value %s" % (
                "a NaN" if o == NAN else "-inf", es.label.split(" >= ", 1)[-1].split(",")[0])
            if c["finite_results"]:
                why += " (a result that is not finite is +inf or a NaN)"
        elif o == INF:
            es.count(UP_INF)
            if conds_hold:
                why = "upper: exact_when holds but the output is +inf, not the stated value"
            elif _small(pl, x, v):
                sus.append("upper: +inf where every operand and the stated value are below "
                           "Omega/4")
        else:
            ov = o * eta
            if ov < v:
                es.count("below the stated value")
                why = "upper: the output is below its stated value"
            else:
                es.count(UP_FINITE)
                d = ov - v
                if d == 0:
                    es.count(UP_EXACT)
                if v > 0:
                    r = d / v
                    es.track_max(UP_EXCESS, (r.numerator, r.denominator), line)
                    es.track_min(UP_EXCESS, (r.numerator, r.denominator), line)
                    g = F.gap_below(fmt, o) * eta
                    r = d / g
                    es.track_min(UP_GAPS, (r.numerator, r.denominator), line)
                if conds_hold and d != 0:
                    why = ("upper: exact_when holds but the output is not the stated value "
                           "exactly (it is %s above)" % (d / eta))
                    es.count("failed exact_when")
        if why:
            es.failures += 1
            reasons.append(why)
    return reasons, sus


def judge_exact_flag(ck, pl, e, es, x, z):
    """The mask output exact_flag is true exactly when every condition of exact_when holds."""
    holds = all(h(x) for h, _t in e["exact"])
    f = z[e["exact_flag"]]
    es.count(FLAG_TRUE if f == 1 else FLAG_FALSE)
    if f != (1 if holds else 0):
        es.count("failed exact_flag")
        return ("exact_flag: the mask %s is %d although the conditions of exact_when %s"
                % (_out_name(pl, e["exact_flag"]), f, "hold" if holds else "do not all hold"))
    return None


def _out_name(pl, slot):
    for n, (lo, _hi) in pl.out_slices.items():
        if lo == slot:
            return n
    return "?"


def judge_acc(ck, pl, st, x, z, line):
    """A kernel with a rounded entry of a value of its own (the accumulator): each entry holds
    where the requirements hold and the leading limb of its own output group is finite (every
    limb of the group finite); an entry whose group is not finite claims nothing (counted).  A
    rounded entry is the rounding of its value (its own, or the kernel's) in the format unbounded
    above: a finite group whose exact value rounds beyond Omega fails it.  The line is judged when
    one entry is, non-finite otherwise; a group not finite on operands and values below Omega/4
    is suspicious."""
    fmt = pl.fmt
    for v in z:
        if not _out_member(fmt, v):
            ck._fail(st, line, "output limb not a number of the format")
            return
    V = pl.value_fn(x) if pl.value_fn is not None else None
    judged, lost, tail = [], [], False
    for i, c in enumerate(pl.entries):
        es = st.entries[i]
        rg = c["ranges"]
        if type(z[rg[0][0]]) is not int:
            es.count(GROUP_NONFINITE)
            lost.append(i)
        elif any(type(z[j]) is not int for lo, hi in rg for j in range(lo, hi)):
            es.count(GROUP_TAIL)
            lost.append(i)
            tail = True
        else:
            judged.append(i)
    if lost:
        small = _small(pl, x)
        if small:
            for i in lost:
                c = pl.entries[i]
                fn, sv = c["own"] if "own" in c else (pl.value_fn, pl.sv)
                w = fn(x)
                d = sv - fmt.qmin
                if ((4 * abs(w)) << d if d >= 0 else 4 * abs(w)) >= (
                        fmt.omega if d >= 0 else fmt.omega << -d):
                    small = False
        if small:
            st.c["suspicious"] += 1
            st.example("suspicious", line, "an output group not finite with operands and exact "
                       "values below Omega/4 (%s)" % ", ".join(pl.kernel.ensures[i].label
                                                             for i in lost), ck.max_examples)
    if not judged:
        st.c["nonfinite_tail" if tail and all(type(z[c["ranges"][0][0]]) is int
                                              for c in pl.entries) else "nonfinite"] += 1
        return
    st.c["judged"] += 1
    reasons = []
    expected = {}
    rest = []
    for i in judged:
        c = pl.entries[i]
        es = st.entries[i]
        if c["kind"] == "rounded" and "own" in c:
            why = _rounded_own(pl, c, es, x, z)
            if why:
                es.failures += 1
                reasons.append(why)
            continue
        if c["kind"] == "rounded":
            r = F.rn(fmt, V, pl.sv)
            if type(r) is not int:
                es.applicable += 1
                es.count(ACC_BEYOND)
                es.failures += 1
                reasons.append("rounded(%s): the output is finite, and the exact value rounds "
                               "beyond Omega" % "+".join(pl.kernel.ensures[i].of))
                continue
            expected[i] = r
        rest.append(i)
    if rest:
        reasons += ck._judge(pl, st.entries, x, z, V, expected, line, only=set(rest))
    if reasons:
        st.c["failed"] += 1
        for r in reasons:
            st.reason(r)
        st.example("failure", line, "; ".join(reasons), ck.max_examples)
    else:
        st.c["passed"] += 1


def _rounded_own(pl, c, es, x, z):
    """The output (a finite limb) is the entry's own value rounded to nearest, ties to even."""
    fmt = pl.fmt
    fn, sv = c["own"]
    w = fn(x)
    es.applicable += 1
    r = F.rn(fmt, w, sv)
    o = z[c["first"]]
    if type(r) is not int:
        es.count(ACC_BEYOND)
        return ("rounded(%s): the output is finite, and its value rounds beyond Omega"
                % _out_name(pl, c["first"]))
    d = sv - fmt.qmin
    # Exactness and ties at the value's scale: r (at eta) against w (at 2^sv).
    if d >= 0:
        exact = r == w << d
        lo, hi = F.rdir(fmt, w, sv, False), F.rdir(fmt, w, sv, True)
        tie = not exact and (lo + hi) == 2 * (w << d)
    else:
        exact = r << -d == w
        lo, hi = F.rdir(fmt, w, sv, False), F.rdir(fmt, w, sv, True)
        tie = not exact and (lo + hi) << -d == 2 * w
    es.count(ACC_EXACT if exact else ACC_TIE if tie else ACC_INEXACT)
    if o != r:
        return "rounded(%s): the output is not its value rounded to nearest" % _out_name(
            pl, c["first"])
    return None


# ---------------------------------------------------------------------------
# The extended domain: finite_or_nan with nonneg or if_all

def k_finish(pl, c, es, x, s, w, f):
    """The flag is true exactly when every mask (if, or each of if_all) is true, the value is
    finite and, with nonneg, not below zero (either zero is not); the output is then the value;
    otherwise a NaN."""
    slots, names, nonneg = c["bvfinish"]
    off = [n for n, i in zip(names, slots) if x[i] != 1]
    if off:
        for n in off:
            es.count(FIN_MASK_FALSE % n)
    else:
        es.count(FIN_MASK_TRUE)
    v = s[0]
    if v == NAN:
        es.count(FIN_NAN)
    elif v == INF:
        es.count(FIN_PINF)
    elif v == NINF:
        es.count(FIN_NINF)
    elif v == 0:
        es.count(FIN_ZERO)
    else:
        es.count(FIN_NEG if v < 0 else FIN_POS)
    want = not off and type(v) is int and (not nonneg or v >= 0)
    out = []
    if f != (1 if want else 0):
        out.append("finite_or_nan: the flag is %d although %s" % (
            f, "every mask is true and the value is finite%s" % (" and not below zero"
                                                                 if nonneg else "")
            if want else "the mask %s is false" % off[0] if off
            else "the value is %s" % ("below zero" if type(v) is int else F.fixed_hex(pl.fmt, v))))
    if want:
        if len(w) != 1 or w[0] != v:
            out.append("finite_or_nan: the output is not the value")
    elif not all(t == NAN for t in w):
        out.append("finite_or_nan: the flag is false, and the output is not a NaN")
    return out
