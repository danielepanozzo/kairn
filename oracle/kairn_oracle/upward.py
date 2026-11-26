"""The claims of the round-up interval: their reading and their judges.

docs/developer/design/upward.md, "Claims and the oracle", read with "Values" (the states), "The
kernels" and "Statements".  An interval of that type is stored as the pair (u, n) of two one-limb
values, the upper bound and the lower bound negated (upward.md, "States"):

- the empty set is (NaN, NaN), both lanes a NaN;
- a nonempty interval [a, b] is (b, -a): neither lane a NaN, neither -inf (each a number of the
  format or +inf), and -n <= u; the whole line is (+inf, +inf), [a, +inf] is (+inf, -a) and
  [-inf, b] is (b, +inf); its members are the real numbers between -n and u;
- every other pair is not canonical: one NaN lane, a lane -inf, or crossed lanes (-n > u).  The
  pair (-inf, -inf) is not the empty set: it is what the default empty set (+inf, -inf) becomes when
  its lower bound is negated, which the page excludes.

What the vocabulary adds, and where it is read:

- the requirement upward(U, N): the one-limb inputs U and N are the stored pair of a canonical
  state (read here; judged by intervals.requirement_violated);
- a set named by its stored pair, {"upper": U, "nlower": N}, in `intervals` (encloses_interval,
  interval_set, certain, trit; intervals._interval_of), and as the outputs of encloses_interval,
  interval_set and makes_interval, "upper" and "nlower" in place of "lower" and "upper"
  (intervals._bound_outputs): the readings I1 to I5 and the others are on the state the pair stands
  for;
- `numbers` of encloses_interval: one-limb inputs, each ranging over the members of Interval(t),
  {t} for a finite t and every real number otherwise (an infinity or a NaN); never empty, and a
  bounded operand of I5 when finite (read here, judged by intervals.k_encloses_interval);
- the kind same_set (`of` and `from`, each a set named either way): the output is canonical, empty
  exactly when the input is, and has the same members (so the same bounds; the sign of a zero is
  not claimed);
- the kernel field "rounding": "upward" (claims.Kernel): every operation of the kernel rounds
  upward and its runner holds the mode.  It changes no verdict; the generator writes it in the
  header of the request lines of such a kernel (gen.py, genup.py).

Every value is an integer at scale qmin or one of the strings of fmt.py, as everywhere in the
oracle: no floating-point operation takes part in a verdict.
"""

import re

from . import extended as XT
from . import fmt as F
from . import intervals as IV

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
UPWARD_RE = re.compile(r"\s*upward\(\s*(%s)\s*,\s*(%s)\s*\)\s*\Z" % (IV.NAME, IV.NAME))
ROUNDINGS = ("upward",)

KNOWN = {"same_set": {"kind", "of", "from"}}

# Count names (the statistics a cross-check's guards may read).
DEFECT_COUNT = "not canonical: %s"
NUMBER_CLASS = "number %s: %s"            # the name, then finite, infinite or NaN
SAME_EMPTY = "result: empty"
SAME_NONEMPTY = "result: nonempty"


def _error(msg):
    from .claims import ClaimsError
    return ClaimsError(msg)


# ---------------------------------------------------------------------------
# Requirements

def read_requirement(kernel, r, limbs):
    """upward(U, N), of the extended domain: appended to kernel.requires as ("upward", U, N) and to
    kernel.upward_requires; True when r is one."""
    m = UPWARD_RE.match(r)
    if m is None:
        return False
    u, n = m.group(1), m.group(2)
    for name in (u, n):
        if name not in kernel.input_names or name in kernel.masks:
            raise _error("%s: requirement %r: %s is not a limb input" % (kernel.name, r, name))
    if not kernel.extended:
        raise _error("%s: requirement %r belongs to the extended domain" % (kernel.name, r))
    if u == n:
        raise _error("%s: requirement %r: the two lanes are the same input" % (kernel.name, r))
    if limbs[u] != 1 or limbs[n] != 1:
        raise _error("%s: requirement %r: a stored pair is two inputs of one limb each"
                     % (kernel.name, r))
    used = {x for t in kernel.upward_requires for x in t}
    if u in used or n in used:
        raise _error("%s: requirement %r shares an input with another stored pair"
                     % (kernel.name, r))
    kernel.requires.append(("upward", u, n))
    kernel.upward_requires.append((u, n))
    return True


def finish_requirements(kernel):
    """Once every requirement is read: an input of a stored pair is in no interval() and no
    ball()."""
    others = {x for t in kernel.interval_requires for x in t}
    others |= {x for t in kernel.ball_requires for x in t}
    for u, n in kernel.upward_requires:
        if u in others or n in others:
            raise _error("%s: upward(%s, %s) shares an input with an interval or a ball"
                         % (kernel.name, u, n))


def read_rounding(kernel, raw):
    """The kernel field rounding: "upward" only, in the extended domain; None when absent."""
    if "rounding" not in raw:
        return None
    r = raw["rounding"]
    if r not in ROUNDINGS:
        raise _error("%s: rounding must be \"upward\" (a field written only in the kernels of the "
                     "round-up interval), got %r" % (kernel.name, r))
    if not kernel.extended:
        raise _error("%s: rounding belongs to the extended domain" % kernel.name)
    return r


# ---------------------------------------------------------------------------
# Named sets

def stored_pair(kernel, spec, where, what):
    """IV.Stored((U, N)) of {"upper": U, "nlower": N}, the inputs of an upward() requirement."""
    pair = (spec["upper"], spec["nlower"])
    if pair not in kernel.upward_requires:
        raise _error("%s: %s (upper %s, nlower %s) is not an upward() requirement of the kernel"
                     % (where, what, pair[0], pair[1]))
    return IV.Stored(pair)


def stored_outputs(e, kernel, raw, where):
    """upper and nlower: the outputs of a stored pair, in place of lower and upper; their limbs."""
    if "lower" in raw:
        raise _error("%s: the outputs are lower and upper, or upper and nlower (a stored pair), "
                     "not both" % where)
    IV._require(raw, ("upper", "nlower"), where)
    e.lower, e.upper, e.nlower = None, raw["upper"], raw["nlower"]
    ul = IV._limb_output(kernel, e.upper, where, "upper")
    nl = IV._limb_output(kernel, e.nlower, where, "nlower")
    if e.upper == e.nlower:
        raise _error("%s: upper and nlower are the same output" % where)
    if ul != 1 or nl != 1:
        raise _error("%s: a stored pair is two outputs of one limb each" % where)
    return ul, nl


def read_numbers(kernel, nums, intervals, where):
    """numbers of encloses_interval: one-limb inputs outside every set (the bounds of an interval,
    a stored pair, a ball), each listed once."""
    if not isinstance(nums, list) or not nums:
        raise _error("%s: numbers must be a nonempty list of inputs (absent when there is none)"
                     % where)
    ins = dict(kernel.inputs)
    bounds = {n for pair in intervals.values() for n in pair}
    bounds |= {n for r in kernel.requires if r[0] in ("interval", "upward", "ball")
               for n in r[1:3]}
    out = []
    for n in nums:
        if not isinstance(n, str) or n not in ins or n in kernel.masks:
            raise _error("%s: numbers: %r is not a limb input" % (where, n))
        if ins[n] != 1:
            raise _error("%s: numbers: %s must be an input of one limb" % (where, n))
        if n in bounds:
            raise _error("%s: numbers: %s is an input of a set, not a number" % (where, n))
        if n in out:
            raise _error("%s: numbers: %s is listed twice" % (where, n))
        out.append(n)
    return out


def _output_set(kernel, spec, where, what):
    """The outputs of a set: {"lower": L, "upper": U}, or {"upper": U, "nlower": N} (a stored pair,
    IV.Stored), all of one limb."""
    if isinstance(spec, dict) and set(spec) == {"upper", "nlower"}:
        pair = IV.Stored((spec["upper"], spec["nlower"]))
    elif isinstance(spec, dict) and set(spec) == {"lower", "upper"}:
        pair = (spec["lower"], spec["upper"])
    else:
        raise _error("%s: %s must be {\"lower\": OUTPUT, \"upper\": OUTPUT} or {\"upper\": OUTPUT, "
                     "\"nlower\": OUTPUT}" % (where, what))
    for f, n in zip(("upper", "nlower") if isinstance(pair, IV.Stored) else ("lower", "upper"),
                    pair):
        if IV._limb_output(kernel, n, where, "%s %s" % (what, f)) != 1:
            raise _error("%s: %s %s must be an output of one limb" % (where, what, f))
    if pair[0] == pair[1]:
        raise _error("%s: %s names the same output twice" % (where, what))
    return pair


def set_text(pair):
    """A set as its label shows it."""
    if isinstance(pair, IV.Stored):
        return "(upper %s, nlower %s)" % pair
    return "[%s, %s]" % pair


# ---------------------------------------------------------------------------
# same_set

def read_entry(e, kernel, raw, where):
    """same_set: of (the outputs) and from (the inputs of an interval() or an upward()
    requirement), each a set named either way, of one limb."""
    if not kernel.extended:
        raise _error("%s: this kind belongs to the extended domain, and the kernel has no "
                     "\"domain\": \"extended\"" % where)
    e.iv = True
    e.up = True
    e.consts = {}
    IV._require(raw, ("of", "from"), where)
    e.from_set = IV._interval_of(kernel, raw["from"], where, "from", stored=True)
    for n in e.from_set:
        if kernel.limbs_of(n) != 1:
            raise _error("%s: same_set is read for sets of one limb; %s has %d"
                         % (where, n, kernel.limbs_of(n)))
    e.of_set = _output_set(kernel, raw["of"], where, "of")
    e.of = list(e.of_set)
    e.label = "same_set(%s) as %s" % (set_text(e.of_set), set_text(e.from_set))


def plan_entry(pl, e, claims):
    """The fields of the plan entry of a same_set entry (check.Plan)."""
    return {"from": IV._pair_sl(pl.in_slices, e.from_set),
            "of": IV._pair_sl(pl.out_slices, e.of_set)}


def defect(u, n):
    """What makes the stored pair (u, n) not canonical, or None when it is canonical (upward.md,
    "States")."""
    if u == NAN and n == NAN:
        return None
    if u == NAN or n == NAN:
        return "one NaN lane"
    if u == NINF or n == NINF:
        return "a lane -inf"
    if XT.x_cmp(XT.x_neg(n), 0, u, 0) > 0:
        return "crossed lanes (-nlower > upper)"
    return None


def defect_text(fmt, es, u, n):
    """The defect of a stored pair that is not canonical, counted, as the end of a reason."""
    d = defect(u, n)
    if d is None:
        return ""
    es.count(DEFECT_COUNT % d)
    return ": the stored pair (%s, %s) has %s" % (F.fixed_hex(fmt, u), F.fixed_hex(fmt, n), d)


def number_env(es, x, nums, q):
    """{name: (lo, hi, q)}: each number the members of Interval(t), {t} for a finite t and every
    real number otherwise, its class counted."""
    env = {}
    for name, j in nums.items():
        v = x[j]
        es.count(NUMBER_CLASS % (name, "finite" if type(v) is int else
                                 "NaN" if v == NAN else "infinite"))
        env[name] = (v, v, q) if type(v) is int else (NINF, INF, q)
    return env


def k_same_set(ck, pl, ep, i, c, es, st, x, z, fin, V, line, sus):
    """The output canonical, empty exactly when the input is, with the same members (the same
    bounds as extended real numbers; the sign of a zero is not claimed)."""
    fmt = pl.fmt
    es.applicable += 1
    out = []
    fail = XT._failer(es, out)
    given = IV._state_of(fmt, x, c["from"])
    es.count(IV.interval_class(given))
    got = IV._state_of(fmt, z, c["of"])
    if got is None:
        so = c["of"]
        why = (defect_text(fmt, es, z[so[0][0]], z[so[1][0]]) if isinstance(so, IV.Stored)
               else "")
        fail("canonical", "the result is not a canonical interval" + why)
        return out
    es.count(SAME_EMPTY if got[0] == "empty" else SAME_NONEMPTY)
    if (got[0] == "empty") != (given[0] == "empty"):
        fail("empty", "the result is %s and the input %s" % (
            IV._iv_show(fmt, got), IV._iv_show(fmt, given)))
        return out
    if got != given:
        fail("members", "the result is %s, not the input's %s" % (
            IV._iv_show(fmt, got), IV._iv_show(fmt, given)))
    return out


def is_upward_kernel(kernel):
    """A kernel of the round-up interval: rounding upward, an upward() requirement, or a set named
    by its stored pair in an entry."""
    if getattr(kernel, "rounding", None) == "upward" or getattr(kernel, "upward_requires", None):
        return True
    for e in kernel.ensures:
        if getattr(e, "up", False) or getattr(e, "nlower", None):
            return True
        sets = getattr(e, "intervals", None) or getattr(e, "sets", None) or {}
        if any(isinstance(p, IV.Stored) for p in sets.values()):
            return True
    return False


XT.KINDS["same_set"] = k_same_set
