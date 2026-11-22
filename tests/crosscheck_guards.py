"""What a cross-check must have checked, beyond the oracle's verdict (tests/crosscheck.py, which
calls run() in its own process, and tests/crosscheck.cmake, which runs this).

    python3 tests/crosscheck_guards.py SUMMARY --kernel K --format F
        (--exhaustive [--restrict R1,R2,...] | --count N --seed S) [--claims FILE] [--emulated]

SUMMARY is the oracle's summary of the run (check --json). The oracle has already passed the
run: no claim violated, no broken stream, no invalid case (the cross-checks pass check
--expect-valid). This fails, with the reason, when the run did not check what it set out to check:

- the stream is not the one asked for: one generator header, for this kernel, format and mode
  (and seed), whose indices were all seen, from 0 to the end;
- an exhaustive run did not cover its whole enumeration, or its domain is not the one asked for:
  every operand when no restriction is given, exactly the restrictions given otherwise;
- a random run has no case of a stratum that the oracle's generator lists in its header for this
  kernel (the strata of the kernel's family), or a case of a stratum it does not list, or the
  list lacks a stratum that every family has;
- no case was judged, or an ensures entry of the kernel applied to no judged case; a comparison
  (predicate) did not see both outcomes; a rounding to nearest saw only exact cases; a rounding
  down or up never differed from the rounding to nearest.

For the kinds of Milestone 2 (architecture.md, "Claims of Milestone 2"), in either domain, also
when the run did not see what their statements are about (m2_needs below):

- a random run's header lacks a stratum of the family the oracle's generator has for the kernel
  (oracle/README.md, "gen": neighbor, dirsum, dirprod, ballpow2);
- neighbor never saw a row of the table of next_up and next_down (in the finite domain, the rows
  that are judged there: not Omega for up, not -Omega for down, not the infinities or NaN), or a
  step toward zero from a power of two above the smallest normal number, or a step between the
  subnormal and the normal range;
- a rounded entry with a when condition never saw it hold, or never saw it fail;
- a rounded entry of a value of two operands (NAME op NAME), in the extended domain, never saw an
  exact result, an overflow above Omega and one below -Omega, a NaN operand, an infinite operand
  without a NaN;
- a bound entry never saw an output at the directed rounding, one step beyond it (when steps is
  at least 1), a value that is not a number of the format; in the extended domain a non-finite
  operand, and for a value of two operands the overflows, a NaN operand and an infinite one;
- an exact_when list never held, or one of its conditions never failed.

For a kernel of the extended domain (the non-finite layer, "domain": "extended" in its claims),
also when the run did not see what that layer is about:

- a random run's header lacks a stratum that the oracle's generator adds for the layer
  (oracle/README.md, "gen"): nonfinite for every kernel, zeroinf where the value or the set has
  a product, edge for extends, threshold where finite_when is not empty, ballstates, zerowhole
  and hugeradius for encloses, badradius for makes_ball;
- an entry of the kernel's own claims never saw one of its classes (EXTENDED_COUNTS below): for
  extends a finite result, an overflow on finite operands and a non-finite operand, and cases
  where every finite_when condition holds when the list is not empty; for encloses each of the
  finite ball, the whole line and the empty set as results (and cases where every finite_when
  condition holds when the list is not empty); for represents a finite, an infinite and a NaN
  value; for makes_ball each of the three given states, and each class of the given radius
  (negative, -inf, NaN, +inf, +0, -0 but in an enumeration, positive) with a finite center and
  with one that is not (MAKE_RADIUS_CLASSES); for the kinds the finite domain has,
  non-finite operands (and, for a comparison, both outcomes on them; for an upper bound, both a
  NaN and an infinity from them).

For the folds' stage of Milestone 2 (oracle/README.md, "The kinds of the folds' stage", "Folds";
docs/developer/testing.md, "What a pass requires"): the bound kernels must have seen their mask
true and false on both sides of the limit of m*unit(K), a count that is not an integer, g close to
its stated value, and in binary64 and binary32 no false mask at or below 1/5 (count_problems);
the finishes every class of their state; a fold (--orders, --max-length: the stream asked for)
every length class and order asked for, both outcomes of its flag and no false one far from
overflow, heavy cancellation, for a dot product the term tau mattering, and an error of at least
1/2 (one limb) or 1/16 (two limbs) of the bound (fold_problems).

A run of the emulated tier (--emulated: the kernels printed for the emulated limb type,
tests/emulated/runner.cpp) also fails when its format is not a format of the statements of
precision 8 to 11, or when the oracle judged fewer than a quarter of its cases (emulated_problems).

Whatever the run, the summary must not exceed SUMMARY_BYTES: what the oracle keeps of a run is a
fixed set of statistics, each with at most one line, whose number the claims and the format bound
whatever the number of lines or elements it judged (the profile of (a) one per distance, some
3 200 in binary64: oracle/README.md, "The size of a summary"); a larger summary means that
something it keeps grows with them, as the profile of a map's step once kept the map's whole line
once per distance (1.7 GB for a run of the full tier).

The claims are those the oracle judged against, the file its summary names (or --claims).

rational_1 and rational_2, kairn::rational<X>(num, den), have no claims: the oracle computes their
answer itself and judges it for equality (oracle/README.md, "rational"). For them the guards read
no claims and fail the run when:

- the stream is not the one asked for (as above; there is no enumeration of them);
- the header lacks one of the strata of RATIONAL_STRATA, a stratum the header lists has no judged
  case, or a line is tagged with a stratum it does not list;
- a request was invalid (the generator writes none: the runner did not echo it);
- no judged case was exact, none inexact, none had den = 0; or, for rational_2, none was a
  near-tie whose naive pair (RN(q), RN(q - RN(q))) is not normalized, so that the renormalization
  was not checked.

Otherwise it prints one line saying what was checked. Python's standard library only, and
nothing from the oracle but the format of its summary (oracle/README.md, "Statistics", "The
extended domain", "The kinds of Milestone 2" and "rational").
"""
import argparse
import decimal
import json
import os
import re
import sys

# The largest summary a run may leave, in bytes. The largest of the full tier are 2.0 to 2.7 MB,
# those of exact operations in binary64, whose profiles keep every distance seen
# (docs/developer/testing.md, "The size of the summaries").
SUMMARY_BYTES = 4 << 20

# The strata of every family of the oracle's generator (oracle/README.md, "gen").
COMMON_STRATA = ("uniform", "underflow", "overflow", "zero", "pow2", "extreme")

# The counts of the oracle's judge of the extended domain (oracle/README.md, "The extended
# domain"; oracle/kairn_oracle/extended.py) that must not be zero, by the kind of an entry of the
# kernel's own claims: the classes of results each statement is about.
EXTENDED_COUNTS = {
    "extends": ("class F2: finite operands, finite result",
                "class F4: finite operands, non-finite result",
                "class F5: a non-finite operand"),
    "encloses": ("result: finite ball", "result: whole line", "result: empty set"),
    "represents": ("value finite", "value infinite", "value NaN"),
    "makes_ball": ("given: finite ball", "given: whole line", "given: empty set"),
    "normalized": ("a non-finite operand",),
    "error": ("a non-finite operand",),
    "leading_rounded": ("a non-finite operand",),
    "predicate": ("a non-finite operand, true", "a non-finite operand, false"),
    "rounded": ("a non-finite operand",),
    "upper": ("value NaN (a NaN operand, or 0 * inf)", "output +inf on a non-finite operand"),
    "finite_or_nan": ("value: finite leading limb, every limb finite", "value: leading limb infinite",
                      "value: leading limb NaN"),
}
# makes_ball from a center and a radius (the rule of 2026-11-20: a negative radius gives the
# empty set whatever the center, a NaN radius the whole line): each class of the given radius with
# a finite center and with one that is not (oracle/kairn_oracle/extended.py, MAKE_RADIUS_CLASSES).
# An enumeration has one zero, +0, so -0 is asked of random runs only.
MAKE_RADIUS_CLASSES = ("negative", "-inf", "NaN", "+inf", "+0", "-0", "positive")
MAKE_CENTER_CLASSES = ("finite", "not finite")


def make_radius_needs(exhaustive):
    return ["given radius %s, center %s" % (r, c) for r in MAKE_RADIUS_CLASSES
            for c in MAKE_CENTER_CLASSES if not (exhaustive and r == "-0")]


# For a finite_or_nan entry of a state of several limbs: a finite leading limb with a lower limb
# that is not finite, which the finish passes on as it is.
FINITE_OR_NAN_TAIL = "value: finite leading limb, a lower limb not finite"
# Where finite_when is not empty: the cases where every condition holds, so that F3 or B4 was
# put to the test.
FINITE_WHEN_COUNTS = {
    "extends": "F3 applies: finite operands, every finite_when condition holds",
    "encloses": "B4 applies: finite operands, every finite_when condition holds",
}

# kairn::rational<X>(num, den): its number of limbs, the strata of the oracle's generator
# (oracle/README.md, "rational"), and the counts of the oracle's judge (on its first entry) that
# must not be zero, with the kernels they are asked of.
RATIONAL = {"rational_1": 1, "rational_2": 2}
RATIONAL_STRATA = ("small", "random", "pow2", "extreme", "den0", "exact", "tie1", "tie2", "tail")
RATIONAL_COUNTS = (("exact", (1, 2)), ("inexact", (1, 2)), ("den = 0", (1, 2)),
                   ("naive pair not normalized", (2,)))


# The kinds of Milestone 2 (architecture.md, "Claims of Milestone 2"): the counts of the oracle's
# judge (oracle/README.md, "check"; oracle/kairn_oracle/directed.py) that must not be zero.
NEIGHBOR_ROWS = ("row: a NaN", "row: +inf", "row: Omega", "row: positive finite", "row: eta",
                 "row: zero", "row: -eta", "row: negative finite", "row: -Omega", "row: -inf")
# The rows that a neighbor entry of the finite domain does not judge: the step outward from
# +-Omega, which is not a number of the format there, and the values that are not finite.
NEIGHBOR_NOT_FINITE = {"up": ("row: a NaN", "row: +inf", "row: -inf", "row: Omega"),
                       "down": ("row: a NaN", "row: +inf", "row: -inf", "row: -Omega")}
NEIGHBOR_STEPS = ("a step toward zero from a power of two above the smallest normal number",
                  "a step between the subnormal and the normal range")
WHEN_COUNTS = ("product_large holds", "product_large does not hold (nothing claimed)")
OVERFLOW_COUNTS = ("overflow: value above Omega", "overflow: value below -Omega")
OPERAND_COUNTS = ("a NaN operand", "an infinite operand, no NaN operand")
BOUND_COUNTS = ("at the directed rounding", "value not a number of the format")
BOUND_ONE = "one step beyond the directed rounding"
EXACT_HOLDS = "exact_when holds"
EXACT_FAILS = "exact_when fails: "
# The strata of the families of Milestone 2 beyond the common ones (oracle/kairn_oracle/gen4.py,
# and gen5.py for the kernels of the folds' stage).
M2_STRATA = {"neighbor": ("special", "binade", "subnormal"),
             "dirsum": ("apart", "cancel", "exact", "close", "beyond", "omega"),
             "dirprod": ("aroundp", "tiny", "exactprod", "beyond"),
             "ballpow2": ("atnormal", "sides", "into", "outof"),
             "count": ("integer", "fraction", "limit", "beyond"),
             "dotstep": ("cancel", "state", "zerostate", "tie", "exactprod"),
             "finish": ("nonfinite", "tails"),
             # The steps of the maps and the kernels of the folds of maxima (gen7.py, gen5.py).
             "maxfinish": ("nonfinite", "top", "smallstep"),
             "axpy": ("cancel", "state", "tie", "exactprod", "tight"),
             "maxof": ("equal", "neighbor", "negative")}
# The kinds of the folds of maxima: a maximum (norm_combine, norm_step_k) saw each argument
# larger and both equal; a finish with a mask input and steps up (norm_finish_k) saw the mask
# both ways, a finite value stepped up to a finite one, a NaN and an infinite value, and, with
# steps, a finite value stepped up to +inf (Omega).
MAXIMUM_COUNTS = ("first argument larger", "second argument larger", "arguments equal")
FINISH_IF_COUNTS = ("mask true", "mask false", "value finite, stepped up finite", "value: NaN",
                    "value: infinite")
FINISH_STEP_COUNT = "value finite, stepped up +inf"
# The steps of axpy (a value a*x+y, an error of form T): the largest error over its bound that a
# run must reach, by the limbs of y (the reference and the interpreter reach about 1 with one limb
# and 4/7 with two, in binary64, from the cases of the tight stratum; see oracle/README.md).
AXPY_FRACTION = {1: (1, 2), 2: (1, 64)}

# The kernels of the bounds (every entry under a mask, a count m): the classes of m * unit(K)
# that the run must have seen (oracle/README.md, "The kinds of the folds' stage"), with the mask
# MASK, and those it must not have seen in binary64 and binary32, where milestone2.md says that
# ok is true for every m with m eps <= 0.24.
COUNT_NEEDS = ("%s true, m*unit(%s) = 0", "%s true, 0 < m*unit(%s) <= 1/5",
               "%s true, 1/5 < m*unit(%s) <= 1/4", "%s false, 1/4 < m*unit(%s) <= 1/2")
COUNT_BEYOND = ("%s false, 1/2 < m*unit(%s) < 1", "%s false, m*unit(%s) >= 1")
COUNT_NEVER = ("%s false, m*unit(%s) = 0", "%s false, 0 < m*unit(%s) <= 1/5")
COUNT_FINE_PRECISION = 8
HARDWARE = ("binary64", "binary32")
# How close the first bound of a bound kernel (g) must come to its stated value somewhere: the
# interpreter's and the compiled kernels' g exceed it by 1.3 to 2.9 gaps of g at least, in
# binary64, binary32 and every count of fp:12:-30:12; a g twice too large would be 2^p gaps away.
CLOSE = "excess over a positive stated value, in gaps of the output"
CLOSE_GAPS = 8

# The folds (architecture.md, "Folds"; oracle/README.md, "Folds"): the strata of the oracle's
# generator (genfold.py), tail only for arrays of two limbs; its default orders; the classes of
# lengths every run asks for; the counts each entry must have seen.
FOLD_STRATA = ("one", "wide", "sign", "cancel", "zeros", "underflow", "overflow", "nonfinite",
               "tight", "pow2")
FOLD_DEFAULT_ORDERS = "seq,seq,lanes:0,lanes:1,lanes:2,lanes:3,lanes:4,lanes:5,lanes:8,lanes:big"
FOLD_DEFAULT_MAX_LENGTH = 256
FOLD_LENGTHS = (0, 1, 2, 3, 4, 5, 7, 8, 9, 16, 17)
FOLD_FLAGS = ("flag true", "flag false: a non-finite element",
              "flag false: finite elements, near overflow")
FOLD_FAR = "flag false: finite elements far from overflow"
FOLD_CANCEL = "heavy cancellation: |sum| <= u * sum of magnitudes"
FOLD_TAU = ("absolute term larger than the relative term", "error above the relative term alone")
# The largest error over its bound that a run must reach: the interpreter reaches 0.83 to 1 of
# the bound with one limb and 0.16 to 1 with two (oracle/README.md, "Folds"), so a bound
# a thousand times too loose cannot pass.
FOLD_FRACTION = {1: (1, 2), 2: (1, 16)}

# The maps, the convolutions and the folds of maxima (architecture.md, "Maps", "Convolutions",
# "Folds of maxima"; oracle/README.md, "Maps", "Convolutions", "Folds of maxima"): the strata of
# the oracle's generator (genmap.py), tail only for groups of two limbs; the counts each entry
# must have seen.
MAP_STRATA = ("one", "wide", "cancel", "tie", "exact", "overflow", "underflow", "zeros",
              "nonfinite", "tight")
MAX_STRATA = ("one", "wide", "ties", "position", "zeros", "underflow", "top", "nonfinite")
MAP_ELEMENTS = ("element: finite operands, finite result",
                "element: finite operands, not finite (an overflow)",
                "element: a non-finite operand")
MAP_FLAGS = ("flag true", "flag false: a non-finite operand",
             "flag false: finite operands, an overflow")
CONV_COEFFICIENTS = ("coefficient: finite terms, finite result",
                     "coefficient: finite terms, not finite (an overflow)",
                     "coefficient: a non-finite term")
CONV_LENGTHS = ("n_x = 0", "n_y = 0", "n_x = 1", "n_y = 1", "n_x != n_y")
MAX_UPPER = ("the largest at the first element", "the largest at the last element",
             "the largest at another element", "the largest attained more than once",
             "every element zero", "no element: V = 0", "result at RU(V)")
MAX_FLAGS = ("flag true", "flag false: a non-finite element")
MAX_TOP = "flag false: finite elements, the bound's top beyond Omega"


def two_operands(kernel):
    """The two operands of a value NAME op NAME (op +, - or *), or None."""
    m = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*([-+*])\s*([A-Za-z_]\w*)\s*", kernel.get("value") or "")
    names = [i.get("name") for i in kernel.get("inputs", [])]
    if not m or m.group(1) == m.group(3) or not {m.group(1), m.group(3)} <= set(names):
        return None
    return m.group(1), m.group(2), m.group(3)


def m2_family(kernel):
    """The family the oracle's generator has for a kernel of Milestone 2 (gen4.family_of), or
    None."""
    if bv_family(kernel):
        # The kernels of the ball vectors and of the accumulator: families of their own, chosen
        # before every other (gen8.py, bv_family).
        return None
    ens = kernel.get("ensures", [])
    kinds = {e.get("kind") for e in ens}
    req = [r.replace(" ", "") for r in kernel.get("requires", [])]
    limbs = {i.get("name"): i.get("limbs", 1) for i in kernel.get("inputs", [])}

    def plain(n):
        return (limbs.get(n) == 1 and "nonneg(%s)" % n not in req
                and "power_of_two(%s)" % n not in req)
    # The folds' stage (gen5.family_of): a count(), a finite_or_nan entry, a value s+x*y.
    if any(r.startswith("count(") for r in req):
        return "count"
    if "finite_or_nan" in kinds:
        if any(e.get("kind") == "finite_or_nan" and ("if" in e or "steps" in e) for e in ens):
            return "maxfinish"
        return "finish"
    # The maps and the folds of maxima (gen7.family_of): a maximum, a value a*x+y.
    if kernel.get("domain", "finite") != "extended":
        if "maximum" in kinds:
            return "maxof"
        m = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*\*\s*([A-Za-z_]\w*)\s*\+\s*([A-Za-z_]\w*)\s*",
                         kernel.get("value") or "")
        if m and len({m.group(1), m.group(2), m.group(3)}) == 3:
            return "axpy"
    if re.fullmatch(r"\s*([A-Za-z_]\w*)\s*\+\s*([A-Za-z_]\w*)\s*\*\s*([A-Za-z_]\w*)\s*",
                    kernel.get("value") or ""):
        return "dotstep"
    two = two_operands(kernel)
    two = two if two and plain(two[0]) and plain(two[2]) else None
    if "neighbor" in kinds:
        return "neighbor"
    directed = any(e.get("kind") == "rounded" and e.get("mode") != "nearest" for e in ens)
    if two and two[1] == "*" and ("bound" in kinds or directed):
        return "dirprod"
    if two and two[1] in "+-" and directed:
        return "dirsum"
    for e in ens:
        if e.get("kind") == "encloses":
            balls = e.get("balls") or {}
            inball = set(balls)
            for b in balls.values():
                inball |= set(b.values() if isinstance(b, dict) else b)
            names = set(re.findall(r"[A-Za-z_]\w*", e.get("set") or "")) - inball - {"abs"}
            if any("power_of_two(%s)" % n in req for n in names):
                return "ballpow2"
    return None


def ew_text(cond):
    """The text the oracle counts a failing exact_when condition under (claims.ew_condition_text)."""
    op = "zero_or_abs_gt" if "zero_or_abs_gt" in cond else "zero_or_abs_ge"
    text = str(cond.get(op, "")).strip()
    return "%s = 0 or |%s| %s %s" % (text, text, ">" if op == "zero_or_abs_gt" else ">=",
                                     cond.get("than"))


def m2_problems(kernel, entries, merged, extended):
    """The guards of the kinds of Milestone 2 on each entry of the kernel's own claims."""
    for j, e in enumerate(kernel.get("ensures", [])):
        if j >= len(entries) or entries[j]["kind"] != e.get("kind"):
            return                  # not the claims' entries: reported below, or not ours
        label, counts = entries[j]["label"], merged[j]
        for name in m2_needs(kernel, e, extended):
            if not counts.get(name):
                yield ('the claim "%s" saw no case of "%s", so its statement was not checked '
                       'there' % (label, name))


def m2_needs(kernel, e, extended):
    """The counts an entry e of the kernel's claims must have seen, for the kinds of Milestone 2
    (none for the other kinds)."""
    two = two_operands(kernel)
    kind = e.get("kind")
    need = []
    if kind == "neighbor":
        skip = () if extended else NEIGHBOR_NOT_FINITE.get(e.get("side"), ())
        need = [r for r in NEIGHBOR_ROWS if r not in skip] + list(NEIGHBOR_STEPS)
    elif kind == "rounded":
        if e.get("when"):
            need += WHEN_COUNTS
        if extended and two:
            need += ("exact",) + OVERFLOW_COUNTS + OPERAND_COUNTS
    elif kind == "bound":
        need += BOUND_COUNTS
        if isinstance(e.get("steps"), int) and e.get("steps") >= 1:
            need.append(BOUND_ONE)
        if extended:
            need.append("a non-finite operand")
            if two:
                need += OVERFLOW_COUNTS + OPERAND_COUNTS
    if two and not_nan_operands(kernel, two) and "a NaN operand" in need:
        # Operands required not_nan() (the interval kernels' mul_dir_1) are never a NaN.
        need.remove("a NaN operand")
    if kind in ("error", "encloses") and e.get("exact_when"):
        need.append(EXACT_HOLDS)
        need += [EXACT_FAILS + ew_text(c) for c in e["exact_when"] if isinstance(c, dict)]
    if kind == "maximum":
        need += MAXIMUM_COUNTS
    if kind == "finite_or_nan" and ("if" in e or "steps" in e) and "nonneg" not in e:
        need += FINISH_IF_COUNTS
        if isinstance(e.get("steps"), int) and e.get("steps") >= 1:
            need.append(FINISH_STEP_COUNT)
    return need


# The kernels of the ball vectors and of the accumulator (architecture.md, "Ball vectors", "The
# accumulator"; oracle/README.md, "Ball vectors and the accumulator"): the families of the
# oracle's generator (gen8.py) with the strata of their own, and the counts of their entries
# (oracle/kairn_oracle/bvec.py).
BV_STRATA = {"radius": ("huge", "zeros", "mixed", "atnormal"),
             "acc": ("cancel", "tie", "apart", "atop", "exactprod"),
             "accradius": ("integer", "limit", "beyond", "abig"),
             "bvfinish": ("nonfinite", "negative", "zeros", "top", "masks")}
BV_UP_FINITE = "output finite, at least the stated value"
BV_UP_INF = "output +inf"
BV_UP_UNLESS = "%s true: nothing claimed"
# A radius kernel whose claim is of finite results (conv_radius, by the ruling of
# 2026-11-21: architecture.md, "Claims of the non-finite layer"): a result that is not finite is
# +inf or a NaN, counted so and judged no further. Such results must stay a small part of a run:
# the finite ones, where the claim is checked, at least BV_FINITE_SHARE of those judged.
BV_UP_NONFINITE = "output not finite (+inf or a NaN): nothing more claimed"
BV_FINITE_SHARE = (3, 4)
BV_FLAG = ("exact_flag true", "exact_flag false")
BV_FIN_VALUES = ("value finite, above zero", "value zero", "value: NaN", "value: +inf",
                 "value: -inf")
BV_FIN_NEG = "value finite, below zero"
BV_GROUP_LOST = "the leading limb of its output is not finite: nothing claimed"


def bv_family(kernel):
    """The family the oracle's generator has for a kernel of the ball vectors or of the
    accumulator (gen8.family_of), or None."""
    ens = kernel.get("ensures", [])
    if ens and all(e.get("kind") == "upper" and "value" in e and "if" not in e for e in ens):
        return "radius"
    if any(e.get("kind") == "rounded" and "value" in e for e in ens):
        return "acc"
    if any(e.get("kind") == "finite_or_nan" and ("nonneg" in e or "if_all" in e) for e in ens):
        return "bvfinish"
    req = [r.replace(" ", "") for r in kernel.get("requires", [])]
    if (ens and all("if" in e for e in ens) and any(r.startswith("count(") for r in req)
            and not any(re.search(r"\b(unit|tiny)\(", str(t)) for e in ens
                        for t in [e.get("value") or ""] + list(e.get("args") or []))):
        return "accradius"
    return None


def identity_value(kernel, e):
    """A rounding to nearest of an input's value, or of its negation (a copy, a negation, a
    guard: bv_center_entry_1, neg_1, bv_neg_radius, bv_make_radius), is exact on every operand:
    no run can see an inexact case."""
    if e.get("kind") != "rounded" or "value" in e:
        return False
    v = (kernel.get("value") or "").replace(" ", "")
    names = {i.get("name") for i in kernel.get("inputs", []) if i.get("type") != "mask"}
    return v in names or (v.startswith("-") and v[1:] in names)


def bv_needs(kernel, e, a):
    """The counts an entry of a kernel of the ball vectors or of the accumulator must have seen."""
    kind = e.get("kind")
    need = []
    if kind == "upper" and "value" in e and "if" not in e:
        need.append(BV_UP_FINITE)
        if not a.exhaustive:
            need.append(BV_UP_INF)
        if "unless" in e:
            need.append(BV_UP_UNLESS % e["unless"])
        if e.get("exact_when"):
            need.append(EXACT_HOLDS)
            for c in e["exact_when"]:
                if isinstance(c, dict) and "mask" in c:
                    need.append(EXACT_FAILS + "%s true" % c["mask"])
                elif isinstance(c, dict):
                    need.append(EXACT_FAILS + ew_text(c))
    elif kind == "error" and "exact_flag" in e:
        need += BV_FLAG
    elif kind == "finite_or_nan" and ("nonneg" in e or "if_all" in e):
        need.append("every mask true")
        masks = [e["if"]] if "if" in e else list(e.get("if_all") or [])
        need += ["a mask false: %s" % m for m in masks]
        need += BV_FIN_VALUES
        if "nonneg" in e:
            need.append(BV_FIN_NEG)
    elif kind == "rounded" and "value" in e:
        need += ["exact", "inexact"]
        if not a.exhaustive:
            need.append(BV_GROUP_LOST)
    elif "if" in e and bv_family(kernel) == "accradius":
        need.append("%s false: nothing claimed" % e["if"])
        if kind == "holds":
            need.append("holds")
    return need


def bv_problems(kernel, entries, merged, a):
    """The guards of the kernels of the ball vectors and of the accumulator."""
    for j, e in enumerate(kernel.get("ensures", [])):
        if j >= len(entries) or entries[j]["kind"] != e.get("kind"):
            return
        label, counts = entries[j]["label"], merged[j]
        for name in bv_needs(kernel, e, a):
            if not counts.get(name):
                yield ('the claim "%s" saw no case of "%s", so its statement was not checked '
                       'there' % (label, name))
        nonfinite = counts.get(BV_UP_NONFINITE, 0)
        if nonfinite:
            finite = counts.get(BV_UP_FINITE, 0)
            num, den = BV_FINITE_SHARE
            if den * finite < num * (finite + nonfinite):
                yield ('the claim "%s" is of finite results, and only %d of the %d results judged '
                       'were finite (at least %d/%d must be): the run checked its statement on '
                       'too few' % (label, finite, finite + nonfinite, num, den))


def not_nan_operands(kernel, two):
    """Both operands of a value NAME op NAME are required not_nan()."""
    req = [r.replace(" ", "") for r in kernel.get("requires", [])]
    return all("not_nan(%s)" % n in req for n in (two[0], two[2]))


# The interval kernels (architecture.md, "Claims of the interval kernels" and "... two limbs and
# the enclosure interface"; oracle/README.md, "The kinds of the interval kernels";
# oracle/kairn_oracle/intervals.py and gen6.py): the strata of their families beyond the common
# ones, and the counts of the oracle's judge each entry must have seen.
IV_STRATA = {
    ("ivop", "+"): ("special", "point", "threshold", "cancel", "zerosum"),
    ("ivop", "-"): ("special", "point", "threshold", "cancel", "zerosum"),
    ("ivop", "*"): ("special", "point", "threshold", "zeroinf", "aroundp"),
    ("ivop", "neg"): ("special", "point"),
    ("ivset", None): ("special", "point", "disjoint", "touch", "nested"),
    ("ivmake", "interval"): ("nanbound", "reversed", "infinities", "point"),
    ("ivmake", "ball"): ("nanbound", "reversed", "infinities", "point", "oddeta", "top"),
    ("ivmid", None): ("special", "point", "step", "oddeta", "top"),
    ("ballbound", None): ("ballstates", "radii", "cross", "beyond", "exactend"),
    ("outward", "+"): ("cancel", "zerosum", "close", "apart", "tiny"),
    ("outward", "-"): ("cancel", "zerosum", "close", "apart", "tiny"),
    ("outward", "*"): ("close", "tiny", "aroundp", "exactprod"),
    ("dirmul", None): ("aroundp", "tiny", "exactprod", "beyond", "nonfinite", "zeroinf",
                       "zerofactor"),
    # The conversions of two limbs (gen6.py): bounds beyond Omega, at the limit of finite_when and
    # bounded_when, and an end of a ball exactly zero.
    ("ivmid", "two"): ("special", "point", "step", "oddeta", "top", "beyond", "threshold"),
    ("ballbound", "two"): ("ballstates", "radii", "cross", "beyond", "exactend", "threshold",
                           "zeroend"),
}
IV_OUTWARD_EXTENDED = ("nonfinite", "zeroinf", "edge")
IV_OPS = ("operands: an empty operand", "operands: nonempty, an unbounded operand",
          "operands: bounded", "result: empty", "result: bounded", "result: unbounded")
IV_I5 = ("bounded operands, bounded_when holds", "bounded operands, bounded_when fails")
IV_I5_NEAR = ("bounded_when holds: largest max|member| / limit",
              "bounded_when fails: smallest max|member| / limit")
IV_I6 = ("I6 applies: an operand is [0, 0]", "I6 applies: [0, 0] against an unbounded operand")
IV_MAKE = ("given: an interval", "given: a point", "given: an unbounded interval",
           "given: a NaN bound", "given: reversed bounds", "given: equal infinities")
# The constructors of intervals and the ball from an interval (the rule of 2026-11-20: a NaN bound
# or the same infinity twice gives the whole line, reversed bounds the empty set): every cell of
# the table of architecture.md, "The constructors on every pair of values", lo the row and hi the
# column, a and b finite (oracle/kairn_oracle/intervals.py, MAKE_CELLS); for bounds of two limbs
# also reversed bounds with equal leading limbs, and, in a random run (an enumeration has one
# zero), the same infinity with second limbs that are zeros of opposite signs.
IV_MAKE_CELLS = tuple("given lo %s, hi %s%s" % (r, c, t) for r in ("NaN", "-inf", "a", "+inf")
                      for c in ("NaN", "-inf", "b", "+inf")
                      for t in ((", a <= b", ", a > b") if (r, c) == ("a", "b") else ("",)))
IV_MAKE_REVERSED_LEAD = "given reversed bounds, equal leading limbs"
IV_MAKE_INF_TAILS = "given the same infinity, second limbs zeros of opposite signs"


def iv_make_needs(kernel, e, exhaustive):
    """The classes a constructor's entry e must have seen (iv_needs)."""
    need = list(IV_MAKE) + list(IV_MAKE_CELLS)
    limbs = {i.get("name"): i.get("limbs", 1) for i in kernel.get("inputs", [])}
    if e.get("kind") == "makes_interval" and limbs.get((e.get("from") or {}).get("lower")) == 2:
        need.append(IV_MAKE_REVERSED_LEAD)
        if not exhaustive:
            need.append(IV_MAKE_INF_TAILS)
    return need
IV_BALLS = ("ball: empty", "ball: whole line", "ball: finite")
IV_SET = ("an operand empty", "both operands empty", "nonempty operands, disjoint",
          "nonempty operands, touching (one common point)", "nonempty operands, overlapping",
          "result: empty", "result: bounded", "result: unbounded")
IV_X = ("X: empty", "X: whole line", "X: half-line [l, +inf]", "X: half-line [-inf, h]",
        "X: bounded", "X: a point")
IV_ODD = "X: a bound an odd multiple of eta below 2N"
IV_ZF = ("zero_factor: a zero operand", "zero_factor: a zero against an infinite operand")
IV_OUT_EXT = ("a zero operand", "an infinite operand, none zero", "finite operands, finite output",
              "finite operands, infinite output")
# The fractions of the allowed slack a run must reach (oracle/README.md, "The kinds of the
# interval kernels": what the interpreter and the compiled kernels reach): the bounds of two limbs
# come to 0.43 to 0.70 of rel*|v| + abs (0.25 is the floor: a bound four times too loose fails),
# and the midpoint of interval_mid_rad_1 to its bound u*|m| + eta itself (0.5 the floor).
IV_OUTWARD_FLOOR = (1, 4)
IV_MID_FLOOR = (1, 2)
IV_RATIO = "|output - value| / (rel*|value| + abs)"
IV_SIDE_RATIO = "%s: distance from the range bound / (rel*|bound| + abs)"
IV_MID_RATIO = "|center - midpoint| / (rel*|midpoint| + abs)"


def iv_family(kernel):
    """(family, op) of an interval kernel (gen6.family_of), or None."""
    ens = kernel.get("ensures", [])
    kinds = {e.get("kind") for e in ens}

    def op_of(t):
        t = (t or "").replace(" ", "")
        return "neg" if t.startswith("-") else "*" if "*" in t else "-" if "-" in t else "+"
    if "encloses_interval" in kinds:
        e = next(e for e in ens if e.get("kind") == "encloses_interval")
        return "ivop", op_of(e.get("set"))
    if "interval_set" in kinds:
        return "ivset", None
    if "makes_interval" in kinds:
        return "ivmake", "interval"
    if any(e.get("kind") == "makes_ball" and set(e.get("from") or {}) == {"lower", "upper"}
           for e in ens):
        return "ivmake", "ball"
    limbs = {i.get("name"): i.get("limbs", 1) for i in kernel.get("inputs", [])}
    if kinds & {"ball_of_interval", "splits"}:
        e = next(e for e in ens if e.get("kind") in ("ball_of_interval", "splits"))
        two = limbs.get((e.get("from") or {}).get("lower")) == 2
        return "ivmid", "two" if two else None
    if kinds & {"set_bound", "interval_of_ball"}:
        outs = {o.get("name"): o.get("limbs", 1) for o in kernel.get("outputs", [])}
        two = any(e.get("kind") == "interval_of_ball" and outs.get(e.get("lower")) == 2
                  for e in ens)
        return "ballbound", "two" if two else None
    if "outward" in kinds or any(e.get("kind") == "encloses" and e.get("balls") == {}
                                 for e in ens):
        return "outward", op_of(kernel.get("value"))
    if any(e.get("zero_factor") for e in ens if e.get("kind") in ("bound", "rounded")):
        return "dirmul", None
    return None


def iv_strata(kernel):
    fam = iv_family(kernel)
    if fam is None:
        return ()
    own = IV_STRATA[fam]
    if fam[0] == "outward" and kernel.get("domain") == "extended":
        own = own + IV_OUTWARD_EXTENDED
    return own


def _ratio(num, den, digits):
    """num / den (den > 0) to DIGITS significant digits, as %g prints it, also beyond the range
    of a float, where a planted fault's ratio can be (the oracle fails such a run, and the
    drivers run the guards only on runs it passed)."""
    try:
        return "%.*g" % (digits, num / den)
    except OverflowError:
        with decimal.localcontext() as c:
            c.prec, c.Emax = digits, decimal.MAX_EMAX
            q = (decimal.Decimal(num) / decimal.Decimal(den)).normalize()
            return format(q, ".%dg" % digits)


def _iv_ratio(keys, j, name, which="maxima"):
    """The largest (or smallest) named fraction of entry j over the keys, as (num, den)."""
    best = None
    for k in keys:
        ents = k["stats"]["entries"]
        if j >= len(ents):
            continue
        v = ents[j].get(which, {}).get(name)
        if v is None:
            continue
        r = (int(v[0][0]), int(v[0][1]))
        if best is None or ((r[0] * best[1] > best[0] * r[1]) if which == "maxima"
                            else (r[0] * best[1] < best[0] * r[1])):
            best = r
    return best


def iv_needs(kernel, e, a):
    """The counts an entry e of an interval kernel must have seen (none for the other kinds)."""
    kind = e.get("kind")
    need = []
    if kind == "encloses_interval":
        need += IV_OPS
        names = e.get("intervals") or {}
        if e.get("bounded_when"):
            need.append(IV_I5[0])
            if len(names) >= 2:
                need.append(IV_I5[1])
        t = e.get("tight") or {}
        sides = ("lower", "upper")
        if t.get("kind") == "rounded":
            for s in sides:
                need += ["%s: range bound a number of the format" % s,
                         "%s: range bound not a number of the format" % s,
                         "%s: range bound infinite" % s]
                if t.get("steps"):
                    need.append("%s: one step beyond the directed rounding" % s)
                if t.get("when"):
                    need += ["%s: product_large holds" % s,
                             "%s: product_large does not hold (within the steps)" % s]
        elif t.get("kind") == "outward":
            for s in sides:
                need.append("%s: range bound infinite" % s)
                for c in (t.get("exact_when") or {}).get(s, []):
                    need.append("%s: exact_when holds" % s)
                    need.append("%s: exact_when fails: %s" % (s, iv_condition_text(c)))
        if e.get("zero_factor"):
            need += IV_I6
    elif kind == "outward":
        if kernel.get("domain") == "extended":
            need += IV_OUT_EXT if e.get("zero_factor") else IV_OUT_EXT[1:]
        for c in e.get("exact_when") or []:
            need += ["exact_when holds", "exact_when fails: %s" % iv_condition_text(c)]
    elif kind == "makes_interval":
        need += iv_make_needs(kernel, e, getattr(a, "exhaustive", False))
    elif kind == "makes_ball" and set(e.get("from") or {}) == {"lower", "upper"}:
        need += iv_make_needs(kernel, e, getattr(a, "exhaustive", False))
        if e.get("midpoint_when"):
            need += ("midpoint_when holds", "midpoint_when fails")
        if "rel" in e:
            # rel and abs (ball_from_interval_1): a center that is the midpoint and one that is not.
            need += IV_MID_CLASSES
    elif kind == "interval_of_ball" and (e.get("tight") or {}).get("kind") == "outward":
        # Bounds of two limbs (ball_to_interval_2): every state of the ball, each side's exact_when
        # both ways, bounded_when both ways.
        need += IV_BALLS
        for s in ("lower", "upper"):
            for c in ((e.get("tight") or {}).get("exact_when") or {}).get(s, []):
                need.append("%s: exact_when holds" % s)
                need.append("%s: exact_when fails: %s" % (s, iv_condition_text(c)))
        if e.get("bounded_when") and outside_statements(a):
            need.append(IV_I5_RANGE)
        elif e.get("bounded_when"):
            need += IV_I5
    elif kind in ("set_bound", "interval_of_ball"):
        need += IV_BALLS
        sides = ("lower", "upper") if kind == "interval_of_ball" else (
            ("lower",) if e.get("side") == "below" else ("upper",))
        for s in sides:
            need += ["%s: range bound a number of the format" % s,
                     "%s: range bound not a number of the format" % s]
    elif kind == "interval_set":
        need += IV_SET
    elif kind in ("ball_of_interval", "splits"):
        need += IV_X
        if kind == "ball_of_interval":
            need.append(IV_ODD)
        # The midpoint of a bounded interval (ieee1788) and the parts of a split that rest on it,
        # in a format of no statement: the judge's count that they are not claimed there (the
        # second ruling of 2026-11-21).
        if outside_statements(a) and (kind == "splits" or e.get("special") == "ieee1788"):
            need.append(IV_SPLIT_RANGE if kind == "splits" else IV_CENTER_RANGE)
        if e.get("finite_when"):
            # finite_when (the conversions of two limbs): each condition holding and failing, and
            # the radius +inf (the whole line, for a ball) of a bounded interval; in a format of
            # no statement (outside_statements) the judge's count that nothing is claimed there.
            if outside_statements(a):
                need.append(IV_FW_RANGE)
            else:
                need.append(IV_FW_HOLDS)
                for c in e["finite_when"]:
                    need.append(IV_FW_FAILS + iv_bound_condition_text(c))
            need.append(IV_FW_INFINITE if e.get("special") == "ieee1788" else IV_FW_WHOLE)
    elif kind in ("bound", "rounded") and e.get("zero_factor"):
        need += IV_ZF
    return need


IV_MID_CLASSES = ("center the midpoint exactly", "center not the midpoint")
IV_FW_HOLDS = "finite_when holds"
IV_FW_FAILS = "finite_when fails: "
IV_FW_INFINITE = "bounded X, the radius +inf"
IV_FW_WHOLE = "bounded X, the whole line"
IV_FW_RANGE = ("finite_when not claimed: a format of no statement (e_max <= p, or eta above "
               "binary_float's)")
IV_I5_RANGE = ("bounded_when not claimed: a format of no statement (e_max <= p, or eta above "
               "binary_float's)")
IV_CENTER_RANGE = ("a finite center not claimed: a format of no statement (e_max <= p, or eta "
                   "above binary_float's)")
IV_SPLIT_RANGE = ("a split at a point of X not claimed: a format of no statement (e_max <= p, or "
                  "eta above binary_float's)")


def outside_statements(a):
    """Whether the run's format is one of no statement: a toy format fp:p:qmin:qmax with
    q_max < 1 or q_min > 3 - q_max - 2p (the ruling of 2026-11-21, architecture.md, "The
    formats of the statements"), where a clause that promises a finite or bounded result is not
    claimed and the judge counts that (as for V4 of the ball vectors, bv_problems)."""
    m = re.fullmatch(r"fp:(\d+):(-?\d+):(-?\d+)", getattr(a, "format", None) or "")
    return m is not None and not (int(m.group(3)) >= 1 and int(m.group(2)) <= 3 - int(
        m.group(3)) - 2 * int(m.group(1)))


def iv_bound_condition_text(c):
    """The text the oracle counts a failing finite_when condition of ball_of_interval under."""
    x = c.get("exp", 0)
    return "|%s| <= 2^(qmax+p%+d)" % (c.get("abs_le"), x) if x else "|%s| <= 2^(qmax+p)" % (
        c.get("abs_le"),)


def iv_condition_text(c):
    """The text the oracle counts a failing condition under (intervals.condition_text)."""
    if isinstance(c, dict) and set(c) == {"zero"}:
        return "%s = 0" % str(c["zero"]).strip()
    return ew_text(c)


def iv_problems(kernel, entries, merged, keys, a):
    """The guards of the interval kernels on each entry of the kernel's own claims: the classes
    of its statement (iv_needs), results near the limit of bounded_when on each side, and the
    fractions of the allowed slack reached (IV_OUTWARD_FLOOR, IV_MID_FLOOR)."""
    for j, e in enumerate(kernel.get("ensures", [])):
        if j >= len(entries) or entries[j]["kind"] != e.get("kind"):
            return
        label, counts = entries[j]["label"], merged[j]
        for name in iv_needs(kernel, e, a):
            if not counts.get(name):
                yield ('the claim "%s" saw no case of "%s", so its statement was not checked '
                       'there' % (label, name))
        kind = e.get("kind")
        if kind == "encloses_interval" and e.get("bounded_when") and len(e.get("intervals") or
                                                                         {}) >= 2:
            # Results near the limit of bounded_when on each side: within a factor 2 of it.
            hi = _iv_ratio(keys, j, IV_I5_NEAR[0], "maxima")
            lo = _iv_ratio(keys, j, IV_I5_NEAR[1], "minima")
            if hi is None or 2 * hi[0] < hi[1]:
                yield ('the claim "%s" never came within a factor 2 below the limit of '
                       'bounded_when (largest %s)' % (label, "none" if hi is None else
                                                      _ratio(hi[0], hi[1], 3)))
            if lo is None or lo[0] > 2 * lo[1]:
                yield ('the claim "%s" never came within a factor 2 above the limit of '
                       'bounded_when (smallest %s)' % (label, "none" if lo is None else
                                                       _ratio(lo[0], lo[1], 3)))
        ratios = []
        outs = {o.get("name"): o.get("limbs", 1) for o in kernel.get("outputs", [])}
        if kind == "outward" or (kind in ("encloses_interval", "interval_of_ball")
                                 and (e.get("tight") or {}).get("kind") == "outward"):
            names = [IV_RATIO] if kind == "outward" else [IV_SIDE_RATIO % s
                                                          for s in ("lower", "upper")]
            ratios = [(n, IV_OUTWARD_FLOOR) for n in names]
        elif kind == "ball_of_interval" and outs.get(e.get("center")) == 1:
            # (A center of two limbs, interval_mid_rad_2 and interval_to_ball_2: its bound
            # 3u^2/(1-4u)|m| + 2 eta is not claimed tight, and the runs come to 0.08 to 0.5 of it:
            # no floor.)
            ratios = [(IV_MID_RATIO, IV_MID_FLOOR)]
        elif kind == "makes_ball" and "rel" in e:
            # The center of ball_from_interval_1 within u|m| + eta: 0.4 to 0.85 in 2 000 cases.
            ratios = [(IV_MID_RATIO, IV_OUTWARD_FLOOR)]
        for name, (num, den) in ratios:
            r = _iv_ratio(keys, j, name)
            if r is None or r[1] == 0 or r[0] * den < num * r[1]:
                yield ('the claim "%s" came to at most %s of its bound (%s), below %d/%d: a bound '
                       'far too loose would pass' % (label, "nothing" if r is None else
                                                     _ratio(r[0], r[1], 3) if r[1] else "inf",
                                                     name, num, den))


# The predicates, comparisons and set operations of a ball of the enclosure interface
# (architecture.md, "Claims of the enclosure interface: predicates and comparisons" and "... the set
# operations of a ball"; oracle/README.md, "The kinds of the enclosure interface";
# oracle/kairn_oracle/enclosure.py and genenc.py): the strata of their families and the classes
# each entry must have seen. An answer not given (certain and trit without exact, exact_when
# failing) is not claimed (architecture.md: "The band is not claimed"); its distance from the
# boundary is held to the band the documentation gives (ENC_BAND_LIMIT), which is not a claim of
# the kernel but what a pass of its run must look like.
ENC_KINDS = ("certain", "trit", "ball_set", "ball_splits")
ENC_ORDER_RELS = ("lt", "le", "eq")
ENC_CLASSES = {"intervals": ("empty", "whole line", "half-line", "bounded", "a point"),
               "balls": ("empty", "whole line", "finite", "a point")}
ENC_POINT_CLASSES = ("finite", "infinite", "NaN")
ENC_SPECIAL = "an operand not finite: exact (claimed)"
ENC_ALL_FINITE = "every operand finite"
ENC_SET_STATES = ("empty", "whole line", "finite")
ENC_SET_PAIRS = tuple("X %s, Y %s" % (x, y) for x in ENC_SET_STATES for y in ENC_SET_STATES)
ENC_SET_COUNTS = ("Y as it is (claimed)", "X as it is (claimed)", "finite operands, disjoint",
                  "finite operands, overlapping", "finite operands, one inside the other",
                  "finite operands, touching (one common point)")
ENC_SET_ZERO_SIGNS = "both the whole line, centers zeros of different signs in the line"
ENC_SPLIT_COUNTS = ("X: empty", "X: whole line", "X: finite", "X: a point (radius 0)")
# The band of the answers not given (architecture.md: an answer is given unless the margin is
# below 2e + 3G for contains(t), 2e + 4G for the others, e about 3 u^2 times the distance plus twice
# the smallest normal number, G the gap of T at the larger of the radius and the distance): the
# oracle measures the largest margin of an answer not given in units of 2e + G with that estimate
# of e, away from overflow (distance and radius below Omega/4), and the guards hold it to 4, the
# documentation's largest, 2e + 4G <= 4 (2e + G). Measured: 0.67 to 2.5 on 20 000 random cases of
# binary64, binary32 and fp:4:-6:1, 0.17 to 0.42 on the enumerations of the toy formats.
ENC_BAND_UNITS = ("an answer not given: largest margin / (2e + G), e = 3 u^2 distance + 2 lambda, "
                  "G the gap at max(radius, distance), both below Omega/4")
ENC_BAND_LIMIT = 4


def enc_entry(kernel):
    return next((e for e in kernel.get("ensures", []) if e.get("kind") in ENC_KINDS), None)


def enc_family(kernel):
    """The family of a kernel of the enclosure interface (genenc.family_of), or None."""
    e = enc_entry(kernel)
    if e is None:
        return None
    if e.get("kind") in ("certain", "trit"):
        return "ivpred" if "intervals" in e else "ballpred"
    return "ballset" if e.get("kind") == "ball_set" else "ballsplit"


def enc_strata(kernel):
    """The strata of the family beyond the common ones (genenc.own_strata)."""
    fam = enc_family(kernel)
    if fam is None:
        return ()
    e = enc_entry(kernel)
    limbs = {i.get("name"): i.get("limbs", 1) for i in kernel.get("inputs", [])}
    if fam in ("ivpred", "ballpred"):
        sets = e.get("intervals") or e.get("balls") or {}
        point = e.get("rel") == "member"
        first = next(iter(sets.values()), {})
        k = limbs.get(first.get("lower") or first.get("center"), 1)
        if fam == "ivpred":
            s = ["special", "nearzero"]
            s += ["member"] if point else ["point"] if len(sets) == 1 else [
                "touch", "equal", "nested", "disjoint"]
            return tuple(s + (["tails"] if k == 2 else []))
        s = ["ballstates"] + (["nearzero"] if len(sets) == 1 and not point else
                              ["boundary", "near"])
        return tuple(s + ["huge", "points"] + (["wide"] if len(sets) == 2 else []))
    if fam == "ballset":
        return ("ballstates", "bothspecial", "disjoint", "touch", "nested", "overlap", "wide",
                "point")
    return ("ballstates", "radii", "top")


def enc_needs(kernel, e, a):
    """The counts an entry e of the family must have seen (none for the other kinds)."""
    kind = e.get("kind")
    exhaustive = getattr(a, "exhaustive", False)
    need = []
    if kind in ("certain", "trit"):
        rel = e.get("rel")
        need.append("the relation holds")
        if kind == "trit":
            need += ["the relation fails for every choice", "answer yes", "answer no"]
            if rel in ENC_ORDER_RELS:
                need += ["the relation neither holds nor fails for every choice",
                         "answer unknown"]
        else:
            need += ["the relation does not hold", "mask true", "mask false"]
        over = "intervals" if "intervals" in e else "balls"
        for n in e.get(over) or {}:
            need += ["%s: %s" % (n, c) for c in ENC_CLASSES[over]]
        if rel == "member":
            need += ["%s: %s" % (e["args"][0], c) for c in ENC_POINT_CLASSES]
        need += [ENC_SPECIAL, ENC_ALL_FINITE]
        for c in e.get("exact_when") or []:
            need += ["exact_when holds", "exact_when fails: |%s| <= Omega" % c.get("abs_le")]
    elif kind == "ball_set":
        need += list(ENC_SET_PAIRS) + list(ENC_SET_COUNTS)
        if not exhaustive:
            # (An enumeration has one zero.)
            need.append(ENC_SET_ZERO_SIGNS)
    elif kind == "ball_splits":
        need += list(ENC_SPLIT_COUNTS)
    return need


def enc_problems(kernel, entries, merged, keys, a):
    """The guards of the family on each entry of the kernel's own claims (enc_needs), and the band
    of the answers not given held to architecture.md's (ENC_BAND_LIMIT)."""
    for j, e in enumerate(kernel.get("ensures", [])):
        if j >= len(entries) or entries[j]["kind"] != e.get("kind"):
            return
        label, counts = entries[j]["label"], merged[j]
        for name in enc_needs(kernel, e, a):
            if not counts.get(name):
                yield ('the claim "%s" saw no case of "%s", so its statement was not checked '
                       'there' % (label, name))
        if e.get("kind") in ("certain", "trit"):
            r = _iv_ratio(keys, j, ENC_BAND_UNITS)
            if r is not None and r[1] and r[0] > ENC_BAND_LIMIT * r[1]:
                yield ('the claim "%s" left an answer %s units of 2e + G from the boundary of its '
                       'relation, beyond the %d of architecture.md\'s band (2e + 4G)'
                       % (label, _ratio(r[0], r[1], 3), ENC_BAND_LIMIT))


def extended_strata(kernel):
    """The strata the oracle's generator adds for a kernel of the extended domain (gen3.py)."""
    if iv_family(kernel) or enc_family(kernel):
        # The interval kernels have families of their own (gen6.py, iv_strata).
        return []
    ensures = kernel.get("ensures", [])
    kinds = {e.get("kind") for e in ensures}
    product = ("*" in (kernel.get("value") or "")
               or any(e.get("kind") == "extends" and e.get("lead") == "mul" for e in ensures)
               or any(e.get("kind") == "encloses" and "*" in (e.get("set") or "") for e in ensures))
    strata = ["nonfinite"]
    if product:
        strata.append("zeroinf")
    if "extends" in kinds:
        strata.append("edge")
    if any(e.get("finite_when") for e in ensures):
        strata.append("threshold")
    if "encloses" in kinds:
        strata += ["ballstates", "zerowhole", "hugeradius"]
    if "makes_ball" in kinds:
        strata.append("badradius")
    return strata


def kernel_claims(summary, a, folds=False):
    """The kernel's entry in the claims the oracle judged against, or a reason why not; with
    folds=True, the fold's entry (the list "folds"), or None and no reason when there is none."""
    path = getattr(a, "claims", None) or summary.get("claims")
    if not path:
        return None, "the oracle's summary names no claims file, and --claims is not given"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        kernels = data["kernels"] if not folds else data.get("folds", [])
    except (OSError, ValueError, KeyError, TypeError) as ex:
        return None, "cannot read the claims %s: %s" % (path, ex)
    for k in kernels:
        if k.get("name") == a.kernel:
            return k, None
    if folds:
        return None, None
    return None, "the claims %s have no kernel %s" % (path, a.kernel)


def count_problems(kernel, keys, a):
    """The guards of the bound kernels (every entry under a mask, a count m): each entry's mask
    seen true at m * unit(K) = 0, at or below 1/5 and between 1/5 and 1/4, and false between 1/4
    and 1/2 and beyond 1/2; m not an integer; in binary64 and binary32 never false at or below
    1/5; and the first upper entry (g) within CLOSE_GAPS gaps of its stated value somewhere (at a
    precision below COUNT_FINE_PRECISION: wherever a positive stated value was met)."""
    if not any(r.replace(" ", "").startswith("count(") for r in kernel.get("requires", [])):
        return
    ens = kernel.get("ensures", [])
    units = set()
    for e in ens:
        for t in [e.get("value") or ""] + list(e.get("args") or []):
            units |= set(re.findall(r"unit\(\s*(\w+)\s*\)", str(t)))
    if len(units) != 1:
        return
    kn = units.pop()
    first_upper = next((j for j, e in enumerate(ens) if e.get("kind") == "upper"), None)
    p = next((k["stats"].get("p") for k in keys if k["stats"].get("p")), None)
    for j, e in enumerate(ens):
        mask = e.get("if")
        if not mask:
            continue
        counts, minima = {}, {}
        for k in keys:
            entries = k["stats"]["entries"]
            if j >= len(entries):
                return
            for name, n in entries[j].get("counts", {}).items():
                counts[name] = counts.get(name, 0) + n
            for name, (r, _line) in entries[j].get("minima", {}).items():
                v = (int(r[0]), int(r[1]))
                if name not in minima or v[0] * minima[name][1] < minima[name][0] * v[1]:
                    minima[name] = v
        label = entries[j]["label"]
        # The classes around the limit need counts placed finely and constants rounded up by
        # little: at a precision of 8 or more (binary64, binary32 and the full tier's
        # fp:12:-30:12). At a lower precision the format may have no count in a class (at p = 1,
        # unit(mul_1_1) = 1/3 and 1 * 1/3 is already beyond 1/4): there, the mask both ways.
        fine = p is None or p >= COUNT_FINE_PRECISION
        needs = COUNT_NEEDS if fine else ("%s true, m*unit(%s) = 0",)
        for t in needs:
            name = t % (mask, kn)
            if not counts.get(name):
                yield 'the claim "%s" saw no case "%s"' % (label, name)
        if not any(counts.get(t % (mask, kn)) for t in COUNT_BEYOND):
            yield ('the claim "%s" saw no count beyond m*unit(%s) = 1/2 with %s false, where the '
                   'statement cannot hold' % (label, kn, mask))
        if (p is None or p >= 2) and not counts.get("m not an integer"):
            yield 'the claim "%s" saw no count that is not an integer, which count() allows' % label
        if a.format in HARDWARE:
            for t in COUNT_NEVER:
                name = t % (mask, kn)
                if counts.get(name):
                    yield ('the claim "%s" saw %d cases "%s": in %s, milestone2.md says, %s is true '
                           'for every m with m*eps <= 0.24' % (label, counts[name], name, a.format,
                                                               mask))
        if j == first_upper:
            r = minima.get(CLOSE)
            # Below COUNT_FINE_PRECISION a format may have no count at all with the mask true
            # and a positive stated value (at p = 1 the mask is true at m = 0 only, where the
            # stated value is zero): there is then nothing to come close to, and the mask both
            # ways, above, is what is asked. Wherever a positive stated value was met, at any
            # precision, the closeness is asked.
            if r is None and not fine:
                continue
            if r is None or r[0] > CLOSE_GAPS * r[1]:
                yield ('the claim "%s" never came within %d gaps of its stated value (smallest '
                       'excess: %s), so a bound far too large would pass'
                       % (label, CLOSE_GAPS, "none" if r is None else "%s/%s" % r))


def axpy_problems(kernel, keys, a):
    """The steps of axpy (gen7's family axpy): the error entry came to at least AXPY_FRACTION of
    its bound somewhere, so that a bound far too loose cannot pass (a random run; an enumeration of
    a toy format is complete by itself)."""
    if m2_family(kernel) != "axpy" or a.exhaustive:
        return
    ky = {i.get("name"): i.get("limbs", 1) for i in kernel.get("inputs", [])}.get(
        re.findall(r"[A-Za-z_]\w*", kernel.get("value") or "")[-1], 1)
    num, den = AXPY_FRACTION[2 if ky >= 2 else 1]
    for j, e in enumerate(kernel.get("ensures", [])):
        if e.get("kind") != "error":
            continue
        best = None
        for k in keys:
            r = k["stats"]["entries"][j].get("max_ratio") if j < len(k["stats"]["entries"]) else None
            if r is not None and int(r[1]):
                v = (int(r[0]), int(r[1]))
                best = v if best is None or v[0] * best[1] > best[0] * v[1] else best
        if best is None or best[0] * den < num * best[1]:
            yield ('the claim "%s" came to at most %s of its bound, below %d/%d: a bound far too '
                   'loose would pass' % (keys[0]["stats"]["entries"][j]["label"] if keys else
                                         e.get("kind"), "nothing" if best is None else
                                         _ratio(best[0], best[1], 3), num, den))


def fold_problems(fold, summary, a, desc, ranges):
    """The guards of a fold (oracle/README.md, "Folds"; docs/developer/testing.md, "What a pass
    requires")."""
    if fold.get("bv") or fold.get("bv_conv"):
        yield from bv_fold_problems(fold, summary, a, desc, ranges)
        return
    if fold.get("map") or fold.get("conv") or any(e.get("kind") == "upper"
                                                  for e in fold.get("ensures", [])):
        yield from other_fold_problems(fold, summary, a, desc, ranges)
        return
    two = max(x.get("limbs", 1) for x in fold.get("arrays", [{}])) >= 2
    maxlen = getattr(a, "max_length", None)
    maxlen = int(maxlen) if maxlen is not None else None
    if a.exhaustive:
        total = int(desc.get("total", -1))
        if ranges != [[0, total]]:
            yield "the enumeration of %d cases was not covered (indices seen: %s)" % (total, ranges)
        if maxlen is None or desc.get("maxlen") != str(maxlen):
            yield ("the enumeration is of arrays up to length %s, not %s"
                   % (desc.get("maxlen"), maxlen))
        strata = ["exhaustive"]
        lengths = list(range((maxlen or 0) + 1))
        orders = ["seq"] + ["lanes:%d" % W for W in range(2, (maxlen or 0) + 1)]
    else:
        if desc.get("seed") != a.seed or ranges != [[0, a.count]]:
            yield ("the stream is indices %s of seed %s, not cases 0 to %d of seed %s"
                   % (ranges, desc.get("seed"), a.count, a.seed))
        want_orders = getattr(a, "orders", None) or FOLD_DEFAULT_ORDERS
        if desc.get("orders") != want_orders:
            yield "the stream's orders are %s, not %s" % (desc.get("orders"), want_orders)
        want_max = maxlen if maxlen is not None else FOLD_DEFAULT_MAX_LENGTH
        if desc.get("maxlen") != str(want_max):
            yield "the stream's largest length is %s, not %s" % (desc.get("maxlen"), want_max)
        strata = [s for s in desc.get("strata", "").split(",") if s]
        for s in FOLD_STRATA + (("tail",) if two else ()):
            if s not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which it writes "
                       "for %s" % (",".join(strata), s, a.kernel))
        lengths = [n for n in FOLD_LENGTHS if n <= want_max]
        orders = sorted(set(want_orders.split(",")))
    keys = [k for k in summary.get("keys", []) if (k["kernel"], k["format"]) == (a.kernel, a.format)]
    if len(keys) != len(summary.get("keys", [])):
        yield "the summary has lines of other kernels or formats"
    tags = {k["tag"] for k in keys}
    for s in strata:
        if s not in tags:
            yield "no case of stratum %s, although the oracle's generator lists it" % s
    for t in sorted(tags - set(strata)):
        yield "lines tagged %s, which the generator's header does not list" % t
    if not sum(k["stats"]["counts"]["judged"] for k in keys):
        yield "the oracle passed it, but judged no case, so nothing was checked"
        return
    ens = fold.get("ensures", [])
    entries = keys[0]["stats"]["entries"]
    if len(entries) != len(ens) or any(e["kind"] != f.get("kind") for e, f in zip(entries, ens)):
        yield ("the summary's entries (%s) are not those of the claims of %s"
               % (", ".join(e["kind"] for e in entries), a.kernel))
        return
    merged = []
    best = [None] * len(ens)
    for j in range(len(ens)):
        counts = {}
        applicable = 0
        for k in keys:
            e = k["stats"]["entries"][j]
            applicable += e["applicable"]
            for name, n in e.get("counts", {}).items():
                counts[name] = counts.get(name, 0) + n
            r = e.get("max_ratio")
            if r is not None:
                v = (int(r[0]), int(r[1]))
                if best[j] is None or v[0] * best[j][1] > best[j][0] * v[1]:
                    best[j] = v
        merged.append(counts)
        if not applicable:
            yield 'the claim "%s" applied to no judged case, so it was not checked' % entries[j]["label"]
    for j, f in enumerate(ens):
        label, counts = entries[j]["label"], merged[j]
        kind = f.get("kind")
        if kind == "finite_or_nan":
            for name in FOLD_FLAGS:
                if not counts.get(name):
                    yield 'the claim "%s" saw no case "%s"' % (label, name)
            if counts.get(FOLD_FAR):
                yield ('the claim "%s" saw %d false flags from finite elements far from overflow'
                       % (label, counts[FOLD_FAR]))
        if kind != "fold_error":
            continue
        for n in lengths:
            if not counts.get("length %d" % n):
                yield 'the claim "%s" saw no judged array of length %d' % (label, n)
        if not a.exhaustive and want_max >= 18 and not any(
                counts.get(c) for c in counts if c.startswith("length ") and " to " in c
                or c.startswith("length above")):
            yield 'the claim "%s" saw no judged array of a random length above 17' % label
        for o in orders:
            if o == "seq":
                name = "order: sequential"
            elif o == "lanes:big":
                name = "order: lanes, more lanes than elements (W > n >= 1)"
            else:
                W = int(o[6:])
                name = ("order: lanes, W = %d" % W if W <= 8 else
                        "order: lanes, W = 9 to 64" if W <= 64 else "order: lanes, W above 64")
            if not counts.get(name):
                yield 'the claim "%s" saw no judged case of "%s"' % (label, name)
        if (not a.exhaustive or (maxlen or 0) >= 2) and not counts.get(FOLD_CANCEL):
            # (An enumeration of arrays of one element cannot cancel.)
            yield 'the claim "%s" saw no judged case of "%s"' % (label, FOLD_CANCEL)
        tau = "*" in (fold.get("value") or "")
        if tau:
            for name in FOLD_TAU:
                if not counts.get(name):
                    yield 'the claim "%s" saw no judged case of "%s"' % (label, name)
        num, den = FOLD_FRACTION[2 if two else 1]
        r = best[j]
        if r is None or r[1] == 0 or r[0] * den < num * r[1]:
            yield ('the claim "%s" came to at most %s of its bound, below %d/%d: a bound far too '
                   'loose would pass' % (label, "nothing" if r is None else
                                         _ratio(r[0], r[1], 3) if r[1] else "inf", num, den))


def _merged(keys, j):
    """The counts of entry j over the keys, its applicable cases and its largest ratio."""
    counts, applicable, best = {}, 0, None
    for k in keys:
        ents = k["stats"]["entries"]
        if j >= len(ents):
            continue
        e = ents[j]
        applicable += e["applicable"]
        for name, n in e.get("counts", {}).items():
            counts[name] = counts.get(name, 0) + n
        r = e.get("max_ratio")
        if r is not None:
            v = (int(r[0]), int(r[1]))
            if best is None or v[0] * best[1] > best[0] * v[1]:
                best = v
    return counts, applicable, best


def _lengths_orders(counts, label, lengths, orders, a, want_max):
    for n in lengths:
        if not counts.get("length %d" % n):
            yield 'the claim "%s" saw no judged array of length %d' % (label, n)
    if not a.exhaustive and want_max >= 18 and not any(
            counts.get(c) for c in counts if c.startswith("length ") and " to " in c
            or c.startswith("length above")):
        yield 'the claim "%s" saw no judged array of a random length above 17' % label
    for o in orders:
        if o == "seq":
            name = "order: sequential"
        elif o == "lanes:big":
            name = "order: lanes, more lanes than elements (W > n >= 1)"
        else:
            W = int(o[6:])
            name = ("order: lanes, W = %d" % W if W <= 8 else
                    "order: lanes, W = 9 to 64" if W <= 64 else "order: lanes, W above 64")
        if not counts.get(name):
            yield 'the claim "%s" saw no judged case of "%s"' % (label, name)


def _fraction(label, best, num, den):
    if best is None or best[1] == 0 or best[0] * den < num * best[1]:
        yield ('the claim "%s" came to at most %s of its bound, below %d/%d: a bound far too '
               'loose would pass' % (label, "nothing" if best is None else
                                     _ratio(best[0], best[1], 3) if best[1] else "inf", num, den))


def other_fold_problems(fold, summary, a, desc, ranges):
    """The guards of a map, a convolution and a fold of maxima (oracle/README.md, "Maps",
    "Convolutions", "Folds of maxima")."""
    kind = "map" if fold.get("map") else "conv" if fold.get("conv") else "max"
    lim = [x.get("limbs", 1) for x in fold.get("arrays", [])] + [
        x.get("limbs", 1) for x in fold.get("scalars", [])]
    two = max(lim or [1]) >= 2
    maxlen = getattr(a, "max_length", None)
    maxlen = int(maxlen) if maxlen is not None else None
    default_orders = "seq" if kind == "conv" else FOLD_DEFAULT_ORDERS
    if a.exhaustive:
        total = int(desc.get("total", -1))
        if ranges != [[0, total]]:
            yield "the enumeration of %d cases was not covered (indices seen: %s)" % (total, ranges)
        if maxlen is None or desc.get("maxlen") != str(maxlen):
            yield ("the enumeration is of arrays up to length %s, not %s"
                   % (desc.get("maxlen"), maxlen))
        strata = ["exhaustive"]
        want_max = maxlen or 0
        lengths = list(range(want_max + 1))
        orders = ["seq"] + (["lanes:%d" % W for W in range(2, want_max + 1)] if kind != "conv"
                            else [])
    else:
        if desc.get("seed") != a.seed or ranges != [[0, a.count]]:
            yield ("the stream is indices %s of seed %s, not cases 0 to %d of seed %s"
                   % (ranges, desc.get("seed"), a.count, a.seed))
        want_orders = getattr(a, "orders", None) or default_orders
        if desc.get("orders") != want_orders:
            yield "the stream's orders are %s, not %s" % (desc.get("orders"), want_orders)
        want_max = maxlen if maxlen is not None else FOLD_DEFAULT_MAX_LENGTH
        if desc.get("maxlen") != str(want_max):
            yield "the stream's largest length is %s, not %s" % (desc.get("maxlen"), want_max)
        strata = [x for x in desc.get("strata", "").split(",") if x]
        want = {"map": MAP_STRATA, "max": MAX_STRATA, "conv": FOLD_STRATA}[kind]
        for x in want + (("tail",) if two else ()):
            if x not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which it writes "
                       "for %s" % (",".join(strata), x, a.kernel))
        lengths = [n for n in FOLD_LENGTHS if n <= want_max]
        orders = sorted(set(want_orders.split(",")))
    if fold.get("map"):
        yield from inplace_problems(fold, desc, a)
    keys = [k for k in summary.get("keys", []) if (k["kernel"], k["format"]) == (a.kernel, a.format)]
    if len(keys) != len(summary.get("keys", [])):
        yield "the summary has lines of other kernels or formats"
    tags = {k["tag"] for k in keys}
    for x in strata:
        if x not in tags:
            yield "no case of stratum %s, although the oracle's generator lists it" % x
    for t in sorted(tags - set(strata)):
        yield "lines tagged %s, which the generator's header does not list" % t
    if not sum(k["stats"]["counts"]["judged"] for k in keys):
        yield "the oracle passed it, but judged no case, so nothing was checked"
        return
    ens = fold.get("ensures", [])
    entries = keys[0]["stats"]["entries"]
    # The entries of the claims first, then those of the step (a map) or of the fold of the
    # coefficients (a convolution) that the first one applies.
    if kind == "map":
        sub_claims, _ = kernel_claims(summary, argparse.Namespace(kernel=fold.get("step"),
                                                                  claims=getattr(a, "claims", None)))
        sub = list((sub_claims or {}).get("ensures", []))
    elif kind == "conv":
        data_fold, _ = kernel_claims(summary, argparse.Namespace(
            kernel=fold.get("coefficients"), claims=getattr(a, "claims", None)), folds=True)
        sub = [e for e in (data_fold or {}).get("ensures", []) if e.get("kind") != "finite_or_nan"]
    else:
        sub = []
    want_kinds = [e.get("kind") for e in ens] + [e.get("kind") for e in sub]
    if [e["kind"] for e in entries] != want_kinds:
        yield ("the summary's entries (%s) are not those of the claims of %s (%s)"
               % (", ".join(e["kind"] for e in entries), a.kernel, ", ".join(map(str, want_kinds))))
        return
    for j, e in enumerate(entries):
        counts, applicable, best = _merged(keys, j)
        label = e["label"]
        if not applicable:
            yield 'the claim "%s" applied to no judged case, so it was not checked' % label
            continue
        k = e["kind"]
        if k == "entries" and getattr(a, "inplace", False):
            for i in inplace_arrays(fold):
                if not counts.get("in place: array %d" % i):
                    yield 'the claim "%s" saw no request in place of array %d' % (label, i)
        if k == "entries":
            yield from _lengths_orders(counts, label, lengths, orders, a, want_max)
            for name in MAP_ELEMENTS:
                if not counts.get(name) and (not a.exhaustive or want_max >= 1):
                    yield 'the claim "%s" saw no case "%s"' % (label, name)
        elif k == "coefficients":
            need = CONV_COEFFICIENTS + tuple(c for c in CONV_LENGTHS
                                             if not a.exhaustive or want_max >= 1)
            if not a.exhaustive:
                need += ("n_x above 2", "n_y above 2")
            for name in need:
                if not counts.get(name):
                    yield 'the claim "%s" saw no case "%s"' % (label, name)
        elif k == "finite_or_nan":
            for name in (MAX_FLAGS if kind == "max" else MAP_FLAGS):
                if not counts.get(name):
                    yield 'the claim "%s" saw no case "%s"' % (label, name)
            if kind == "max" and two and not counts.get(MAX_TOP):
                yield 'the claim "%s" saw no case "%s"' % (label, MAX_TOP)
        elif k == "upper":
            yield from _lengths_orders(counts, label, lengths, orders, a, want_max)
            steps = next((x.get("steps") for x in ens if x.get("kind") == "upper"), 0)
            need = list(MAX_UPPER) + (["result %d step%s above RU(V)" % (steps, "" if steps == 1
                                                                          else "s")]
                                      if steps else [])
            if two:
                need.append("V not a number of the format")
            if a.exhaustive and want_max < 3:
                # Arrays of one or two elements have no element between the first and the last,
                # and of one element no last one apart from the first, nor a largest twice.
                need.remove("the largest at another element")
                if want_max < 2:
                    need.remove("the largest at the last element")
                    need.remove("the largest attained more than once")
            for name in need:
                if not counts.get(name):
                    yield 'the claim "%s" saw no case "%s"' % (label, name)
        elif k == "rounded" and "nearest" in label:
            if not counts.get("inexact") and not counts.get("tie"):
                yield 'the claim "%s" saw only exact cases' % label
        elif k == "fold_error":
            # The coefficients of a convolution: their terms counted as a dot product's array.
            if not a.exhaustive and not counts.get(FOLD_CANCEL):
                yield 'the claim "%s" saw no judged case of "%s"' % (label, FOLD_CANCEL)
            if not a.exhaustive or want_max >= 2:
                for n in (1, 2):
                    if not counts.get("length %d" % n):
                        yield 'the claim "%s" saw no coefficient of %d terms' % (label, n)
            if "*" in (fold.get("value") or "") and not a.exhaustive:
                for name in FOLD_TAU:
                    if not counts.get(name):
                        yield 'the claim "%s" saw no judged case of "%s"' % (label, name)
            num, den = FOLD_FRACTION[2 if two else 1]
            yield from _fraction(label, best, num, den)
        elif k == "error":
            # The step of a map: as close to its bound as its tight stratum brings it.
            num, den = (1, 2) if not two else (1, 16)
            yield from _fraction(label, best, num, den)


def inplace_arrays(fold):
    """The arrays a map or a ball vector may write: those of the limbs of the array written."""
    w = (fold.get("writes") or [{}])[0].get("limbs", 1)
    return [i for i, x in enumerate(fold.get("arrays", [])) if x.get("limbs", 1) == w]


def inplace_problems(fold, desc, a):
    """A stream asked in place (--inplace) has the generator's header that says so, and only
    then."""
    if getattr(a, "inplace", False) and desc.get("inplace") != "yes":
        yield "the stream is not in place, though --inplace was asked"
    if not getattr(a, "inplace", False) and desc.get("inplace"):
        yield "the stream is in place, though --inplace was not asked"


# The ball vectors (architecture.md, "Ball vectors"; oracle/README.md, "Ball vectors and the
# accumulator"): the strata of the oracle's generator (genbv.py) by shape, and the classes of the
# judge (bvfolds.py).
BV_FOLD_STRATA = ("one", "wide", "zeroradius", "whole", "overflow", "threshold", "cancel",
                  "underflow", "zeros")
BV_MAKE_STRATA = ("one", "badradius", "badcenter", "zeros", "overflow", "underflow")
BV_CONV_STRATA = ("one", "wide", "zeroradius", "whole", "overflow", "threshold", "cancel",
                  "underflow", "zeros", "count")
BV_RESULTS = ("result: finite ball vector", "result: whole space")
BV_OPERANDS = ("operands: a whole-space operand", "operands: finite ball vectors, finite scalars")
BV_RADIUS_CLASSES = ("negative", "-inf", "NaN", "+inf", "+0", "-0", "positive")


def bv_strata(fold):
    """The strata the oracle's generator lists for a ball vector or a product (genbv.strata_of)."""
    two = (fold.get("writes") or [{}])[0].get("limbs", 1) >= 2
    if fold.get("bv_conv"):
        st = list(BV_CONV_STRATA)
    elif (fold.get("ensures") or [{}])[0].get("kind") == "makes_ball_vector":
        st = list(BV_MAKE_STRATA)
    else:
        st = list(BV_FOLD_STRATA)
        radii = set()
        for r in fold.get("requires", []):
            m = re.match(r"\s*ball_vector\(\s*\w+\s*,\s*(\w+)\s*\)", r)
            if m:
                radii.add(m.group(1))
        pow2 = {m.group(1) for r in fold.get("requires", [])
                for m in [re.match(r"\s*power_of_two\(\s*(\w+)\s*\)", r)] if m}
        if [x for x in fold.get("scalars", []) if x["name"] not in radii | pow2]:
            st.append("nonfinite")
        if "exact_when" in (fold.get("ensures") or [{}])[0]:
            st.append("exact")
    if two:
        st.append("tail")
    return st


def bv_fold_problems(fold, summary, a, desc, ranges):
    """The guards of a ball vector, a constructor and a product of BallVectors: the stream asked
    for, every stratum of the shape, the results finite and the whole space, an operand that is
    the whole space, V4 applying (with no entry too), the conditions of exactness each failing and
    all holding, every class of the radius given of a constructor, the lengths 0 and 1 on each
    side of a product, the lengths and orders of a fold, every array written in place."""
    conv = bool(fold.get("bv_conv"))
    e0 = (fold.get("ensures") or [{}])[0]
    makes = e0.get("kind") == "makes_ball_vector"
    maxlen = getattr(a, "max_length", None)
    maxlen = int(maxlen) if maxlen is not None else None
    default_orders = "seq" if conv else FOLD_DEFAULT_ORDERS
    if a.exhaustive:
        total = int(desc.get("total", -1))
        if ranges != [[0, total]]:
            yield "the enumeration of %d cases was not covered (indices seen: %s)" % (total, ranges)
        if maxlen is None or desc.get("maxlen") != str(maxlen):
            yield ("the enumeration is of arrays up to length %s, not %s"
                   % (desc.get("maxlen"), maxlen))
        strata = ["exhaustive"]
        want_max = maxlen or 0
        lengths = list(range(want_max + 1))
        orders = ["seq"] + (["lanes:%d" % W for W in range(2, want_max + 1)] if not conv else [])
    else:
        if desc.get("seed") != a.seed or ranges != [[0, a.count]]:
            yield ("the stream is indices %s of seed %s, not cases 0 to %d of seed %s"
                   % (ranges, desc.get("seed"), a.count, a.seed))
        want_orders = getattr(a, "orders", None) or default_orders
        if desc.get("orders") != want_orders:
            yield "the stream's orders are %s, not %s" % (desc.get("orders"), want_orders)
        want_max = maxlen if maxlen is not None else FOLD_DEFAULT_MAX_LENGTH
        if desc.get("maxlen") != str(want_max):
            yield "the stream's largest length is %s, not %s" % (desc.get("maxlen"), want_max)
        strata = [x for x in desc.get("strata", "").split(",") if x]
        for x in bv_strata(fold):
            if x not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which it writes "
                       "for %s" % (",".join(strata), x, a.kernel))
        lengths = [n for n in FOLD_LENGTHS if n <= want_max]
        orders = sorted(set(want_orders.split(",")))
    if not conv:
        yield from inplace_problems(fold, desc, a)
    keys = [k for k in summary.get("keys", []) if (k["kernel"], k["format"]) == (a.kernel, a.format)]
    if len(keys) != len(summary.get("keys", [])):
        yield "the summary has lines of other kernels or formats"
    tags = {k["tag"] for k in keys}
    for x in strata:
        if x not in tags:
            yield "no case of stratum %s, although the oracle's generator lists it" % x
    for t in sorted(tags - set(strata)):
        yield "lines tagged %s, which the generator's header does not list" % t
    if not sum(k["stats"]["counts"]["judged"] for k in keys):
        yield "the oracle passed it, but judged no case, so nothing was checked"
        return
    entries = keys[0]["stats"]["entries"]
    if not entries or entries[0]["kind"] != e0.get("kind"):
        yield ("the summary's first entry (%s) is not the claim of %s (%s)"
               % (entries[0]["kind"] if entries else "none", a.kernel, e0.get("kind")))
        return
    counts, applicable, _best = _merged(keys, 0)
    label = entries[0]["label"]
    if not applicable:
        yield 'the claim "%s" applied to no judged case, so it was not checked' % label
        return
    need = list(BV_RESULTS)
    if makes:
        for r in BV_RADIUS_CLASSES:
            if a.exhaustive and r == "-0":
                continue
            need.append("given radius %s, centers finite" % r)
        if not a.exhaustive or want_max >= 1:
            need.append("given radius positive, centers not all finite")
    else:
        need += BV_OPERANDS
        # V4 is claimed from the precision finite_from (when given), in formats of e_max at least
        # p: elsewhere, the judge says so.
        p = next((k["stats"].get("p") for k in keys if k["stats"].get("p")), None)
        below = e0.get("finite_from") is not None and p is not None and p < e0["finite_from"]
        m = re.fullmatch(r"fp:(\d+):(-?\d+):(-?\d+)", a.format)
        narrow = m is not None and not (int(m.group(3)) >= 1 and int(m.group(2)) <= 3 - int(
            m.group(3)) - 2 * int(m.group(1)))
        if e0.get("finite_when") and narrow:
            need.append("V4 not claimed: a format of no statement (e_max <= p, or eta above "
                        "binary_float's)")
        elif e0.get("finite_when") and below:
            need.append("V4 not claimed: below finite_from")
        elif e0.get("finite_when"):
            need.append("V4 applies")
            if not conv:
                need.append("V4 applies, no entry")
        if e0.get("exact_when"):
            need.append("exact: every condition holds")
            for c in e0["exact_when"]:
                need.append("exact_when fails: " + ew_text(c))
        elif "exact_when" in e0:
            need.append("exact: every condition holds")
    if conv:
        need += [c for c in CONV_LENGTHS if not a.exhaustive or want_max >= 1]
        need.append("V3: the radius at least conv_radius's stated value")
        # In a toy format the edge of count_when is within the lengths (the count stratum).
        if not a.exhaustive and a.format.startswith("fp:"):
            need += ["count_when fails: %s <= %s" % (c["le"], c["than"])
                     for c in e0.get("count_when", [])]
    else:
        yield from _lengths_orders(counts, label, lengths, orders, a, want_max)
        if getattr(a, "inplace", False):
            need += ["in place: array %d" % i for i in inplace_arrays(fold)]
    for name in need:
        if not counts.get(name):
            yield 'the claim "%s" saw no case "%s"' % (label, name)


def problems(summary, a):
    what = "%s %s" % (a.kernel, a.format)
    cov = summary.get("coverage", [])
    if len(cov) != 1:
        yield "the oracle saw %d generator headers, not one" % len(cov)
        return
    desc, ranges = cov[0]["desc"], cov[0]["ranges"]
    mode = "exhaustive" if a.exhaustive else "random"
    got = (desc.get("kernel"), desc.get("format"), desc.get("mode"))
    if got != (a.kernel, a.format, mode):
        yield "the stream is of %s %s in mode %s, not of %s in mode %s" % (got + (what, mode))
        return
    if a.kernel in RATIONAL:
        yield from rational_problems(summary, a, desc, ranges)
        return
    fold, why = kernel_claims(summary, a, folds=True)
    if why:
        yield why
        return
    if fold is not None:
        yield from fold_problems(fold, summary, a, desc, ranges)
        return
    if getattr(a, "orders", None) or getattr(a, "max_length", None) is not None:
        yield "--orders and --max-length are for folds; %s is not one" % a.kernel
        return
    kernel, why = kernel_claims(summary, a)
    if kernel is None:
        yield why
        return
    extended = kernel.get("domain", "finite") == "extended"
    if a.exhaustive:
        total = int(desc.get("total", -1))
        restrict = a.restrict or "none"
        if ranges != [[0, total]]:
            yield "the enumeration of %d cases was not covered (indices seen: %s)" % (total, ranges)
        if desc.get("restrict") != restrict:
            yield ("the enumeration was over the domain restricted by %r, not by %r"
                   % (desc.get("restrict"), restrict))
        strata = ["exhaustive"]
    else:
        if desc.get("seed") != a.seed or ranges != [[0, a.count]]:
            yield ("the stream is indices %s of seed %s, not cases 0 to %d of seed %s"
                   % (ranges, desc.get("seed"), a.count, a.seed))
        strata = [s for s in desc.get("strata", "").split(",") if s]
        for s in COMMON_STRATA:
            if s not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which every "
                       "family of kernels has" % (",".join(strata), s))
        if extended:
            for s in extended_strata(kernel):
                if s not in strata:
                    yield ("the oracle's generator lists the strata %s, without %s, which it "
                           "adds for %s in the extended domain" % (",".join(strata), s, a.kernel))
        family = m2_family(kernel)
        for s in M2_STRATA.get(family, ()):
            if s not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which its family "
                       "%s has (Milestone 2)" % (",".join(strata), s, family))
        # The families of the ball vectors and of the accumulator (gen8.py).
        for s in BV_STRATA.get(bv_family(kernel), ()):
            if s not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which its family "
                       "%s has (the ball vectors and the accumulator)"
                       % (",".join(strata), s, bv_family(kernel)))
        # The families of the interval kernels (gen6.py).
        for s in iv_strata(kernel):
            if s not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which its family "
                       "%s has (the interval kernels)" % (",".join(strata), s,
                                                          iv_family(kernel)[0]))
        # The families of the enclosure interface (genenc.py).
        for s in enc_strata(kernel):
            if s not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which its family "
                       "%s has (the enclosure interface)" % (",".join(strata), s,
                                                             enc_family(kernel)))

    keys = [k for k in summary.get("keys", [])
            if (k["kernel"], k["format"]) == (a.kernel, a.format)]
    if len(keys) != len(summary.get("keys", [])):
        yield "the summary has lines of other kernels or formats"
    tags = {k["tag"] for k in keys}
    for s in strata:
        if s in tags:
            continue
        if a.exhaustive:
            yield "no line tagged exhaustive"
        else:
            yield ("no case of stratum %s in %d cases, although the oracle's generator lists it "
                   "for %s" % (s, a.count, a.kernel))
    for t in sorted(tags - set(strata)):
        yield "lines tagged %s, which the generator's header does not list" % t

    judged = sum(k["stats"]["counts"]["judged"] for k in keys)
    if judged == 0:
        yield ("the oracle passed it, but judged no case (every result non-finite or out of "
               "scope), so nothing was checked")
        return
    entries = keys[0]["stats"]["entries"]
    merged = []
    for j, e in enumerate(entries):
        applicable = 0
        counts = {}
        for k in keys:
            ke = k["stats"]["entries"][j]
            if ke["label"] != e["label"]:
                yield "the entries of the claims differ between tags"
                return
            applicable += ke["applicable"]
            for name, n in ke.get("counts", {}).items():
                counts[name] = counts.get(name, 0) + n
        merged.append(counts)
        label = e["label"]
        if applicable == 0:
            yield 'the claim "%s" applied to no judged case, so it was not checked' % label
        elif e["kind"] == "predicate":
            for outcome in ("true", "false"):
                if not counts.get(outcome):
                    yield ('the claim "%s" was never %s, so the comparison was not checked both '
                           'ways' % (label, outcome))
        elif e["kind"] == "rounded" and "nearest" in label:
            own = kernel.get("ensures", [])
            if (not counts.get("inexact") and not counts.get("tie")
                    and not (j < len(own) and identity_value(kernel, own[j]))):
                yield 'the claim "%s" saw only exact cases' % label
        elif e["kind"] == "rounded":
            if not counts.get("inexact, != RN"):
                yield ('the claim "%s" never differed from the rounding to nearest, so the '
                       'direction was not checked' % label)
    yield from m2_problems(kernel, entries, merged, extended)
    yield from bv_problems(kernel, entries, merged, a)
    yield from iv_problems(kernel, entries, merged, keys, a)
    yield from enc_problems(kernel, entries, merged, keys, a)
    yield from count_problems(kernel, keys, a)
    yield from axpy_problems(kernel, keys, a)
    if not extended:
        return

    # The extended domain: each entry of the kernel's own claims (the summary lists them first,
    # then those of the cores that extends applies) saw every class of its statement.
    own = kernel.get("ensures", [])
    if len(entries) < len(own) or any(entries[j]["kind"] != e.get("kind")
                                      for j, e in enumerate(own)):
        yield ("the summary's entries (%s) are not those of the claims of %s (%s)"
               % (", ".join(e["kind"] for e in entries), a.kernel,
                  ", ".join(str(e.get("kind")) for e in own)))
        return
    for j, e in enumerate(own):
        label, counts = entries[j]["label"], merged[j]
        need = list(EXTENDED_COUNTS.get(e.get("kind"), ()))
        if e.get("kind") == "makes_ball" and set(e.get("from") or {}) == {"lower", "upper"}:
            need = []           # a ball from the bounds of an interval: iv_needs
        elif e.get("kind") == "makes_ball":
            need += make_radius_needs(getattr(a, "exhaustive", False))
        if e.get("kind") == "finite_or_nan" and ("if" in e or "steps" in e or "if_all" in e):
            need = []           # with nonneg or if_all: bv_needs
        elif e.get("kind") == "finite_or_nan":
            ins = {i.get("name"): i.get("limbs", 1) for i in kernel.get("inputs", [])}
            if ins.get((kernel.get("value") or "").strip(), 1) > 1:
                need.append(FINITE_OR_NAN_TAIL)
        for name in need:
            if not counts.get(name):
                yield ('the claim "%s" saw no case of "%s", so the extended domain was not '
                       'checked there' % (label, name))
        name = FINITE_WHEN_COUNTS.get(e.get("kind"))
        if name and e.get("finite_when") and not counts.get(name):
            yield ('the claim "%s" saw no case where every finite_when condition holds, so its '
                   'finite_when was not checked' % label)


def rational_counts(keys, entry=0):
    """The counts of one entry of the judge of rational_K, summed over the keys."""
    counts = {}
    for k in keys:
        entries = k["stats"]["entries"]
        if len(entries) > entry:
            for name, n in entries[entry].get("counts", {}).items():
                counts[name] = counts.get(name, 0) + n
    return counts


def rational_problems(summary, a, desc, ranges):
    """The guards of rational_K, whose answer the oracle computes and compares for equality."""
    if a.exhaustive:
        yield "the oracle's generator has no enumeration of %s, only random runs" % a.kernel
        return
    if desc.get("seed") != a.seed or ranges != [[0, a.count]]:
        yield ("the stream is indices %s of seed %s, not cases 0 to %d of seed %s"
               % (ranges, desc.get("seed"), a.count, a.seed))
    strata = [s for s in desc.get("strata", "").split(",") if s]
    for s in RATIONAL_STRATA:
        if s not in strata:
            yield ("the oracle's generator lists the strata %s, without %s, which it writes for %s"
                   % (",".join(strata), s, a.kernel))
    keys = [k for k in summary.get("keys", [])
            if (k["kernel"], k["format"]) == (a.kernel, a.format)]
    if len(keys) != len(summary.get("keys", [])):
        yield "the summary has lines of other kernels or formats"
    judged = {}
    for k in keys:
        judged[k["tag"]] = judged.get(k["tag"], 0) + k["stats"]["counts"]["judged"]
    for s in strata:
        if s not in judged:
            yield ("no case of stratum %s in %d cases, although the oracle's generator lists it "
                   "for %s" % (s, a.count, a.kernel))
        elif not judged[s]:
            yield "no case of stratum %s was judged" % s
    for t in sorted(set(judged) - set(strata)):
        yield "lines tagged %s, which the generator's header does not list" % t
    invalid = sum(k["stats"]["counts"]["invalid"] for k in keys)
    if invalid:
        yield ("%d requests were invalid, and the oracle's generator writes none: the runner did "
               "not echo them" % invalid)
    if not sum(judged.values()):
        yield "the oracle passed it, but judged no case, so nothing was checked"
        return
    counts = rational_counts(keys)
    for name, kernels in RATIONAL_COUNTS:
        if RATIONAL[a.kernel] in kernels and not counts.get(name):
            yield ('no judged case "%s", so %s was not checked there'
                   % (name, "the renormalization of the pair" if name.startswith("naive")
                      else a.kernel))


# How describe() names the counts of EXTENDED_COUNTS and FINITE_WHEN_COUNTS.
SHORT = {
    "class F2: finite operands, finite result": "F2 finite",
    "class F4: finite operands, non-finite result": "F4 overflow",
    "class F5: a non-finite operand": "F5 non-finite operand",
    "result: finite ball": "finite ball",
    "result: whole line": "whole line",
    "result: empty set": "empty set",
    "given: finite ball": "given finite ball",
    "given: whole line": "given whole line",
    "given: empty set": "given empty set",
    "a non-finite operand": "non-finite operand",
    "a non-finite operand, true": "non-finite operand true",
    "a non-finite operand, false": "non-finite operand false",
    "value NaN (a NaN operand, or 0 * inf)": "NaN",
    "output +inf on a non-finite operand": "+inf from a non-finite operand",
    FINITE_WHEN_COUNTS["extends"]: "F3 applies",
    FINITE_WHEN_COUNTS["encloses"]: "B4 applies",
}


def describe(summary, a):
    desc = summary["coverage"][0]["desc"]
    judged = sum(k["stats"]["counts"]["judged"] for k in summary["keys"])
    if a.exhaustive:
        if a.restrict:
            what = "every operand of a RESTRICTED domain (%s), %s cases" % (a.restrict, desc["total"])
        else:
            what = "every operand, %s cases" % desc["total"]
    else:
        what = "%d random cases, seed %s, strata %s" % (a.count, a.seed, desc["strata"])
    text = "%d cases judged (%s)" % (judged, what)
    if a.kernel in RATIONAL:
        counts = rational_counts(summary["keys"])
        return text + "; " + ", ".join("%s %d" % (name, counts.get(name, 0)) for name in (
            "exact", "inexact", "den = 0", "first rounding a tie", "second rounding a tie",
            "naive pair not normalized", "second limb subnormal"))
    fold, _ = kernel_claims(summary, a, folds=True)
    if fold is not None and (fold.get("bv") or fold.get("bv_conv")) and summary["keys"]:
        counts, _app, _best = _merged(summary["keys"], 0)
        return text + "; ball vector: " + ", ".join(
            "%s %d" % (n, counts[n]) for n in sorted(counts) if n.startswith((
                "result", "operands", "V4", "exact", "count_when", "in place", "given radius",
                "V3: the radius")))
    if fold is not None and (fold.get("map") or fold.get("conv") or any(
            e.get("kind") == "upper" for e in fold.get("ensures", []))):
        out = []
        entries = summary["keys"][0]["stats"]["entries"] if summary["keys"] else []
        for j, e in enumerate(entries):
            counts, _app, best = _merged(summary["keys"], j)
            if e["kind"] in ("error", "fold_error") and best is not None and best[1]:
                out.append("%s: largest error/allowed %s" % (e["label"].split(":")[0],
                                                             _ratio(best[0], best[1], 4)))
            elif e["kind"] == "finite_or_nan":
                out += ["%s %d" % (n, counts.get(n, 0)) for n in sorted(counts)
                        if n.startswith("flag")]
            elif e["kind"] == "upper":
                out += ["%s %d" % (n, counts.get(n, 0)) for n in sorted(counts)
                        if n.startswith("result")]
        return text + "; " + ", ".join(out)
    if fold is not None:
        out = []
        for j, f in enumerate(fold.get("ensures", [])):
            counts = rational_counts(summary["keys"], j)
            if f.get("kind") == "fold_error":
                best = None
                for k in summary["keys"]:
                    r = k["stats"]["entries"][j].get("max_ratio")
                    if r is not None and int(r[1]):
                        v = (int(r[0]), int(r[1]))
                        best = v if best is None or v[0] * best[1] > best[0] * v[1] else best
                out.append("largest error/allowed %s" % ("-" if best is None else
                                                         _ratio(best[0], best[1], 4)))
                out += ["%s %d" % (n, counts.get(n, 0)) for n in (FOLD_CANCEL,) + FOLD_TAU
                        if counts.get(n)]
            elif f.get("kind") == "finite_or_nan":
                out += ["%s %d" % (n, counts.get(n, 0)) for n in FOLD_FLAGS + (FOLD_FAR,)]
        return text + "; fold: " + ", ".join(out)
    kernel, _ = kernel_claims(summary, a)
    if kernel:
        # The classes of the kinds of Milestone 2 that the guards asked for, with their counts.
        seen = []
        ext = kernel.get("domain") == "extended"
        for j, e in enumerate(kernel.get("ensures", [])):
            items = ["%s %d" % (name, sum(k["stats"]["entries"][j].get("counts", {}).get(name, 0)
                                          for k in summary["keys"]))
                     for name in m2_needs(kernel, e, ext)]
            if items:
                seen.append("%s: %s" % (e.get("kind"), ", ".join(items)))
        if seen:
            text += "; Milestone 2, %s" % "; ".join(seen)
    if kernel and kernel.get("domain") == "extended":
        seen = []
        for j, e in enumerate(kernel.get("ensures", [])):
            names = list(EXTENDED_COUNTS.get(e.get("kind"), ()))
            if e.get("finite_when") and e.get("kind") in FINITE_WHEN_COUNTS:
                names.append(FINITE_WHEN_COUNTS[e["kind"]])
            for name in names:
                n = sum(k["stats"]["entries"][j].get("counts", {}).get(name, 0)
                        for k in summary["keys"])
                item = "%s %d" % (SHORT.get(name, name), n)
                if item not in seen:
                    seen.append(item)
        text += "; extended domain: " + ", ".join(seen)
    return text


def parser():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("summary")
    p.add_argument("--kernel", required=True)
    p.add_argument("--format", required=True)
    p.add_argument("--exhaustive", action="store_true")
    p.add_argument("--restrict", default="")
    p.add_argument("--count", type=int)
    p.add_argument("--seed")
    p.add_argument("--claims", help="the claims file (default: the one the summary names)")
    p.add_argument("--orders", help="a fold: the orders asked of the generator (gen --orders)")
    p.add_argument("--max-length", help="a fold: the largest length asked (gen --max-length)")
    p.add_argument("--inplace", action="store_true",
                   help="a map or a ball vector: the stream asked in place (gen --inplace)")
    p.add_argument("--emulated", action="store_true",
                   help="a run of the emulated tier (emulated_problems)")
    return p


# --- The emulated tier (docs/developer/testing.md, "The emulated formats") -----------------------
#
# A run of the kernels printed for the emulated limb type (tests/emulated/runner.cpp) is the
# exhaustive tier of the brief: the scalar kernels on every operand, or a dense sample, of tiny
# formats of precision 8 to 11 in which the statements hold. So, besides everything above, it fails
# when its format is not such a format (architecture.md, "The formats of the statements": qmax >= 1
# and qmin = 3 - qmax - 2p; in another format the finiteness clauses are not claimed, and a format
# outside 8 to 11 is not the tier's), and when the oracle judged fewer than a quarter of its cases:
# in a format too narrow for the kernel most results overflow or vanish, and the run would put
# little of the claims to the test (in fp:8:-14:1 every kernel and fold has at least 0.56 of its
# cases judged: split and two_prod_dekker, whose product by the splitter overflows).
EMULATED_PRECISIONS = (8, 11)
EMULATED_JUDGED = (1, 4)


def emulated_problems(summary, a):
    m = re.fullmatch(r"fp:(\d+):(-?\d+):(-?\d+)", a.format)
    lo, hi = EMULATED_PRECISIONS
    if not m:
        yield ("a run of the emulated tier is in a toy format of precision %d to %d, not %s"
               % (lo, hi, a.format))
        return
    p, qmin, qmax = (int(g) for g in m.groups())
    if not lo <= p <= hi:
        yield "a run of the emulated tier has precision %d to %d, not %d (%s)" % (lo, hi, p, a.format)
    if qmax < 1 or qmin != 3 - qmax - 2 * p:
        yield ("a run of the emulated tier is in a format of the statements (qmax >= 1, qmin = 3 - qmax - "
               "2p: fp:%d:%d:1 at this precision), not %s" % (p, 2 - 2 * p, a.format))
    cases = sum(k["stats"]["counts"]["cases"] for k in summary.get("keys", []))
    judged = sum(k["stats"]["counts"]["judged"] for k in summary.get("keys", []))
    num, den = EMULATED_JUDGED
    if cases and judged * den < cases * num:
        yield ("the oracle judged %d of the %d cases, fewer than %d/%d: in %s most results are not "
               "finite, and the run puts little of the claims to the test" % (judged, cases, num, den,
                                                                              a.format))


def run(a):
    """(exit status, lines to print) of the guards on the arguments A (parser()): 0 and what was
    checked, or 1 and the reasons. tests/crosscheck.py calls it in its own process."""
    if not a.exhaustive and (a.count is None or a.seed is None):
        return 2, ["a random run needs --count and --seed"]
    try:
        size = os.path.getsize(a.summary)
        if size > SUMMARY_BYTES:
            return 1, ["the oracle's summary %s is %d bytes, above the %d a summary may take: "
                       "something the oracle keeps grows with the number of lines judged"
                       % (a.summary, size, SUMMARY_BYTES)]
        with open(a.summary, encoding="utf-8") as f:
            summary = json.load(f)
    except (OSError, ValueError) as ex:
        return 1, ["cannot read the oracle's summary %s: %s" % (a.summary, ex)]
    found = list(problems(summary, a))
    if getattr(a, "emulated", False):
        found += list(emulated_problems(summary, a))
    if found:
        return 1, found
    text = describe(summary, a)
    if getattr(a, "emulated", False):
        text += "; the emulated tier, %s" % a.format
    return 0, [text]


def main():
    p = parser()
    a = p.parse_args()
    if not a.exhaustive and (a.count is None or a.seed is None):
        p.error("a random run needs --count and --seed")
    status, lines = run(a)
    for line in lines:
        print(line)
    return status


if __name__ == "__main__":
    sys.exit(main())
