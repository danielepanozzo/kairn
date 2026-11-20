"""What the kinds of Milestone 2 need from a format, shared by the finite judge (check.py) and the
judge of the extended domain (extended.py): the classes of an operand of `neighbor` (the rows of
the table of next_up and next_down, milestone2.md, "next_up and next_down on every input"), the
steps of a format with overflow, and the count names the statistics and the guards share.

Finite limbs are fixed values (integers N meaning N * eta) and the non-finite ones the strings of
fmt.py, as everywhere in the oracle.
"""

from . import fmt as F

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN

# The rows of the table, in its order (architecture.md, "Claims of Milestone 2"). The rows of
# Omega, eta, the zeros, -eta and -Omega come before the general ones: "positive finite" is a
# positive finite number other than Omega and eta.
ROW_NAN = "row: a NaN"
ROW_PINF = "row: +inf"
ROW_OMEGA = "row: Omega"
ROW_POS = "row: positive finite"
ROW_ETA = "row: eta"
ROW_ZERO = "row: zero"
ROW_NETA = "row: -eta"
ROW_NEG = "row: negative finite"
ROW_NOMEGA = "row: -Omega"
ROW_NINF = "row: -inf"
NEIGHBOR_ROWS = (ROW_NAN, ROW_PINF, ROW_OMEGA, ROW_POS, ROW_ETA, ROW_ZERO, ROW_NETA, ROW_NEG,
                 ROW_NOMEGA, ROW_NINF)
# Two classes of a step between finite numbers where the spacing of the format changes: from a
# power of two above the smallest normal number toward zero (the gap below is half the gap
# above), and between the subnormal and the normal range.
STEP_POW2 = "a step toward zero from a power of two above the smallest normal number"
STEP_SUBNORMAL = "a step between the subnormal and the normal range"
NEIGHBOR_STEPS = (STEP_POW2, STEP_SUBNORMAL)


def neighbor_row(fmt, a):
    """The row of the table for the operand a."""
    if a == NAN:
        return ROW_NAN
    if a == INF:
        return ROW_PINF
    if a == NINF:
        return ROW_NINF
    if a == 0:
        return ROW_ZERO
    if a == fmt.omega:
        return ROW_OMEGA
    if a == -fmt.omega:
        return ROW_NOMEGA
    if a == 1:
        return ROW_ETA
    if a == -1:
        return ROW_NETA
    return ROW_POS if a > 0 else ROW_NEG


def neighbor_steps(fmt, a, r, up):
    """The classes of NEIGHBOR_STEPS that the step from a to r (its expected neighbor) is in."""
    out = []
    if type(a) is not int or type(r) is not int:
        return out
    m = abs(a)
    toward_zero = (a < 0) == up and a != 0
    if toward_zero and m > fmt.lam and m & (m - 1) == 0:
        out.append(STEP_POW2)
    if (m >= fmt.lam) != (abs(r) >= fmt.lam):
        out.append(STEP_SUBNORMAL)
    return out


def neighbor(fmt, a, up):
    """The next number of the format above a (up) or below it, on every value of the format: the
    table of next_up and next_down (a NaN gives a NaN, next_up(-inf) = -Omega, next_down(+inf) =
    Omega, the infinities stay where the step goes outward, and a step outward from +-Omega is the
    infinity)."""
    if a == NAN:
        return NAN
    if a == INF:
        return INF if up else fmt.omega
    if a == NINF:
        return -fmt.omega if up else NINF
    return F.succ(fmt, a) if up else F.pred(fmt, a)


def step_unbounded(fmt, t, down):
    """The next number below (down) or above a fixed value t in the format unbounded above (the
    real model's format: the number after Omega is 2^(qmax+p))."""
    if down:
        return t - F.gap_below(fmt, t)
    return t + F.gap_below(fmt, -t)


def round_overflow(fmt, v, s, mode):
    """v * 2^s rounded in the format with overflow (architecture.md, "Claims of Milestone 2"):
    nearest is RN with the infinity beyond the threshold; down is the largest number not above,
    Omega above Omega and -inf below -Omega; up likewise."""
    om = fmt.omega
    if mode == "nearest":
        return F.rn(fmt, v, s)
    r = F.rdir(fmt, v, s, mode == "up")
    if mode == "down":
        return NINF if r < -om else om if r > om else r
    return INF if r > om else -om if r < -om else r


# Count names of the classes the guards read (tests/crosscheck_guards.py).
EXACT_HOLDS = "exact_when holds"
EXACT_FAILS = "exact_when fails: "              # followed by the condition's text
WHEN_HOLDS = "product_large holds"
WHEN_FAILS = "product_large does not hold (nothing claimed)"
BOUND_AT = "at the directed rounding"
BOUND_ONE = "one step beyond the directed rounding"
BOUND_EXACT = "value a number of the format"
BOUND_INEXACT = "value not a number of the format"
OVER_ABOVE = "overflow: value above Omega"
OVER_BELOW = "overflow: value below -Omega"
NAN_OPERAND = "a NaN operand"
INF_OPERAND = "an infinite operand, no NaN operand"
NAN_FROM_INF = "value NaN from operands that are not NaN"


def steps_text(k):
    if k == 0:
        return BOUND_AT
    if k == 1:
        return BOUND_ONE
    return "%d steps beyond the directed rounding" % k


def overflow_class(fmt, v, s):
    """OVER_ABOVE, OVER_BELOW or None for a finite value v * 2^s."""
    q = fmt.qmin
    if s >= q:
        a = abs(v) << (s - q)
        over = a > fmt.omega
    else:
        over = abs(v) > (fmt.omega << (q - s))
    if not over:
        return None
    return OVER_ABOVE if v > 0 else OVER_BELOW
