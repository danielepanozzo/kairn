"""What a cross-check must have checked, beyond the oracle's verdict (tests/crosscheck.py, which
calls run() in its own process, and tests/crosscheck.cmake, which runs this).

    python3 tests/crosscheck_guards.py SUMMARY --kernel K --format F
        (--exhaustive [--restrict R1,R2,...] | --count N --seed S) [--claims FILE]

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
  value; for makes_ball each of the three given states; for the kinds the finite domain has,
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
import json
import re
import sys

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
             "finish": ("nonfinite", "tails")}

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
# interpreter's g exceeds it by 1.8 to 3.9 gaps of g at least, in binary64, binary32 and
# fp:11:-30:10; a g twice too large would be 2^p gaps away.
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
        return "finish"
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
    if kind in ("error", "encloses") and e.get("exact_when"):
        need.append(EXACT_HOLDS)
        need += [EXACT_FAILS + ew_text(c) for c in e["exact_when"] if isinstance(c, dict)]
    return need


def extended_strata(kernel):
    """The strata the oracle's generator adds for a kernel of the extended domain (gen3.py)."""
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
    1/5; and the first upper entry (g) within CLOSE_GAPS gaps of its stated value somewhere."""
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
            if r is None or r[0] > CLOSE_GAPS * r[1]:
                yield ('the claim "%s" never came within %d gaps of its stated value (smallest '
                       'excess: %s), so a bound far too large would pass'
                       % (label, CLOSE_GAPS, "none" if r is None else "%s/%s" % r))


def fold_problems(fold, summary, a, desc, ranges):
    """The guards of a fold (oracle/README.md, "Folds"; docs/developer/testing.md, "What a pass
    requires")."""
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
                                         "%.3g" % (r[0] / r[1]) if r[1] else "inf", num, den))


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
            if not counts.get("inexact") and not counts.get("tie"):
                yield 'the claim "%s" saw only exact cases' % label
        elif e["kind"] == "rounded":
            if not counts.get("inexact, != RN"):
                yield ('the claim "%s" never differed from the rounding to nearest, so the '
                       'direction was not checked' % label)
    yield from m2_problems(kernel, entries, merged, extended)
    yield from count_problems(kernel, keys, a)
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
        if e.get("kind") == "finite_or_nan":
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
    if fold is not None:
        out = []
        for j, f in enumerate(fold.get("ensures", [])):
            counts = rational_counts(summary["keys"], j)
            if f.get("kind") == "fold_error":
                best = None
                for k in summary["keys"]:
                    r = k["stats"]["entries"][j].get("max_ratio")
                    if r is not None and int(r[1]):
                        v = int(r[0]) / int(r[1])
                        best = v if best is None or v > best else best
                out.append("largest error/allowed %s" % ("-" if best is None else "%.4g" % best))
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
    return p


def run(a):
    """(exit status, lines to print) of the guards on the arguments A (parser()): 0 and what was
    checked, or 1 and the reasons. tests/crosscheck.py calls it in its own process."""
    if not a.exhaustive and (a.count is None or a.seed is None):
        return 2, ["a random run needs --count and --seed"]
    try:
        with open(a.summary, encoding="utf-8") as f:
            summary = json.load(f)
    except (OSError, ValueError) as ex:
        return 1, ["cannot read the oracle's summary %s: %s" % (a.summary, ex)]
    found = list(problems(summary, a))
    if found:
        return 1, found
    return 0, [describe(summary, a)]


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
