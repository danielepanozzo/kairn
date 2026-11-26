"""The oracle's own tests for the round-up interval (docs/developer/design/upward.md, "Claims and the
oracle"): the requirement upward(U, N), the sets named by their stored pair in `intervals` and as
outputs, `numbers`, the kind same_set and the kernel field rounding (upward.py, with the hooks in
intervals.py, enclosure.py, claims.py, extended.py and check.py), the generator's family (genup.py)
and the reference runner's listings (refup.py).

As for the earlier waves, each test compares the oracle with something it does not share code with:

- the rounding upward of the reference runner against a walk over the sorted numbers of toy
  formats, and in binary64 against the hardware's rounding to nearest moved by one step;
- the definitions of the page computed here with Fractions, from the numbers of a format taken in
  order (class Def: no rounding routine of the oracle or of the reference runner): on every input of
  tiny formats, and on special values of binary64 and binary32, the oracle accepts the result the
  definition gives and nothing else (every other output pair, canonical or not, fails), and the
  reference runner's listings give that result;
- the reference runner, the listings of the page, on random streams and on every case of tiny
  formats, with both machine forms of max_nl; planted faults (refup.VARIANTS) that must be caught
  in the statement they are about, in no kernel that does not use them, and on every line whose
  values they change;
- hand-written lines whose verdicts are worked out by hand.

The fixture, oracle/selftest/claims-upward.json, holds the 24 entries written from the page (its two
JSON examples and its table of kernels and claims) before the generator writes them; its shape is
what the integration with the generator's entries is to be matched against.
"""

import bisect
import copy
import json
import math
import os
import random
from fractions import Fraction as Q

from . import check as C
from . import directed as D
from . import fmt as F
from . import gen as G
from . import genup as GU
from . import intervals as IV
from . import refrun
from . import refup as RU
from .claims import Claims, load_claims
from .selftest import test, expect, judge, totals, ORACLE_DIR

FIXTURE = os.path.join(ORACLE_DIR, "selftest", "claims-upward.json")
ARITH = ("upward_add_1", "upward_sub_1", "upward_neg_1", "upward_mul_1", "upward_add_num_1",
         "upward_mul_num_1")
SETOPS = ("upward_hull_1", "upward_intersection_1")
CONV = ("upward_from_interval_1", "upward_to_interval_1")
CERTAIN = ("upward_empty_1", "upward_entire_1", "upward_contains_1", "upward_subset_1",
           "upward_positive_1", "upward_negative_1", "upward_zero_1", "upward_rel_equal_1",
           "upward_rel_interior_1", "upward_rel_disjoint_1")
TRIT = ("upward_less_1", "upward_less_equal_1", "upward_equal_1")
PRED = CERTAIN + TRIT
KERNELS = ARITH + SETOPS + ("upward_make_1",) + CONV + PRED
FORMATS = ("binary64", "binary32", "fp:4:-6:1")
FORMS = RU.MAX_FORMS
INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
EMPTY = ("empty",)


def claims_up(ctx):
    if not hasattr(ctx, "claims_up"):
        ctx.claims_up = load_claims(FIXTURE)
    return ctx.claims_up


def raw_up():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def run_up(lines, variant="correct", form="sel"):
    r = refrun.Runner(variant, max_form=form)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def stream_up(ctx, kernel, fmtname, count, strata=None, seed="selftest-up"):
    key = ("up", kernel, fmtname, count, strata, seed)
    s = ctx._streams.get(key)
    if s is None:
        g = G.RandomGen(claims_up(ctx).get(kernel), F.parse_format(fmtname), seed,
                        strata.split(",") if strata else None)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def body(lines):
    return [ln for ln in lines if ln and not ln.startswith("#")]


def entry_stats(summary, name):
    """{label: [kind, applicable, failures, counts]} of a kernel, summed over its keys."""
    out = {}
    for (k, _f, _t), st in summary.keys.items():
        if k != name:
            continue
        for e in st.entries:
            d = out.setdefault(e.label, [e.kind, 0, 0, {}])
            d[1] += e.applicable
            d[2] += e.failures
            for c, n in e.counts.items():
                d[3][c] = d[3].get(c, 0) + n
    return out


def counts_of(summary, name):
    out = {}
    for _kind, _a, _f, counts in entry_stats(summary, name).values():
        for c, n in counts.items():
            out[c] = out.get(c, 0) + n
    return out


def failed_statements(counts):
    """The statements counted as failed (failed X, failed: X) and the defects of a stored pair."""
    out = set()
    for c, n in counts.items():
        if not n:
            continue
        if c.startswith("failed: "):
            out.add(c[len("failed: "):])
        elif c.startswith("failed "):
            out.add(c[len("failed "):])
        elif c.startswith("not canonical: "):
            out.add(c)
    return out


class LineJudge:
    """The verdict of the oracle on one line at a time: (status, failed statements, reasons),
    status one of pass, fail, invalid.  One Checker (its plans built once); the statistics of a
    line's key are taken out of its summary after each line, so that each line is read alone."""

    def __init__(self, claims):
        self.ck = C.Checker(claims, max_examples=1)

    def __call__(self, line):
        left = line.partition(" -> ")[0].split(" ")
        tag = left[-1][1:].split(":", 1)[0] if left[-1].startswith("#") else ""
        key = (left[0], F.parse_format(left[1]).name, tag)
        self.ck.line(line)
        st = self.ck.summary.keys.pop(key)
        status = ("fail" if st.c["failed"] else "invalid" if st.c["invalid"] else
                  "pass" if st.c["passed"] else "other")
        counts = {}
        for e in st.entries:
            for c, n in e.counts.items():
                counts[c] = counts.get(c, 0) + n
        return status, failed_statements(counts), list(st.reasons)


# ---------------------------------------------------------------------------
# The definitions, with Fractions, from the numbers of a format taken in order

class Def:
    """A format's numbers by index (the k-th nonnegative number, increasing), the roundings of the
    page by a binary search over them, and the definitions of the kernels' results on intervals
    (EMPTY or (L, U), each a Fraction or INF or NINF)."""

    def __init__(self, fmtname):
        f = F.parse_format(fmtname)
        self.fmt = f
        self.eta = Q(2) ** f.qmin
        self.s = 1 << (f.p - 1)
        self.kmax = self.s + (f.qmax - f.qmin + 1) * self.s - 1
        self.omega = self.value(self.kmax)

    def value(self, k):
        if k < self.s:
            return k * self.eta
        b, r = divmod(k - self.s, self.s)
        return (self.s + r) * Q(2) ** b * self.eta

    def _index_ge(self, v):
        """The least k with value(k) >= v, for 0 <= v <= Omega."""
        lo, hi = 0, self.kmax
        while lo < hi:
            mid = (lo + hi) // 2
            if self.value(mid) >= v:
                hi = mid
            else:
                lo = mid + 1
        return lo

    def _index_le(self, v):
        """The greatest k with value(k) <= v, for v >= 0."""
        lo, hi = 0, self.kmax
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.value(mid) <= v:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def ru(self, v):
        """The smallest number of the format not below v, +inf above Omega, -Omega below it."""
        if type(v) is str:
            return v
        if v > self.omega:
            return INF
        if v < -self.omega:
            return -self.omega
        if v >= 0:
            return self.value(self._index_ge(v))
        return -self.value(self._index_le(-v))

    def rd(self, v):
        r = self.ru(_xneg(v))
        return _xneg(r)

    def numbers(self):
        pos = [self.value(k) for k in range(1, self.kmax + 1)]
        return [-v for v in reversed(pos)] + [Q(0)] + pos

    def succ(self, v):
        """The next number above a finite v (INF above Omega)."""
        if v >= self.omega:
            return INF
        if v >= 0:
            k = self._index_le(v)
            return self.value(k + 1)
        k = self._index_ge(-v)
        return -self.value(k - 1)

    def pred(self, v):
        r = self.succ(-v)
        return NINF if r == INF else -r


def _xneg(v):
    return NINF if v == INF else INF if v == NINF else NAN if v == NAN else -v


def _key(v):
    return (-1, 0) if v == NINF else (1, 0) if v == INF else (0, v)


def _xadd(a, b):
    if type(a) is str or type(b) is str:
        if type(a) is str and type(b) is str and a != b:
            raise ValueError("inf - inf in a range")
        return a if type(a) is str else b
    return a + b


def _xmul0(a, b):
    """A product of two bounds in interval arithmetic: 0 * inf = 0."""
    if a == 0 or b == 0:
        return Q(0)
    if type(a) is str or type(b) is str:
        sa = 1 if a == INF or (type(a) is not str and a > 0) else -1
        sb = 1 if b == INF or (type(b) is not str and b > 0) else -1
        return INF if sa == sb else NINF
    return a * b


def tok_value(tok):
    """A limb of a line as an exact value: a Fraction, or INF, NINF, NAN."""
    t = tok.lower()
    if t in ("inf", "+inf"):
        return INF
    if t == "-inf":
        return NINF
    if t in ("nan", "-nan", "+nan"):
        return NAN
    return Q(float.fromhex(tok))


def stored_state(u, n):
    """upward.md, "States", from its table."""
    if u == NAN and n == NAN:
        return EMPTY
    if NAN in (u, n) or NINF in (u, n):
        return None
    lo = _xneg(n)
    if _key(lo) > _key(u):
        return None
    return (lo, u)


def default_state(l, h):
    if l == INF and h == NINF:
        return EMPTY
    if NAN in (l, h) or l == INF or h == NINF or _key(l) > _key(h):
        return None
    return (l, h)


def expected(df, kernel, vals):
    """The result the page defines for a kernel on input values, by the definitions: an interval
    (EMPTY or (L, U)) for the kernels with an interval output, a tuple of booleans for the masks."""
    if kernel == "upward_make_1":
        lo, hi = vals
        if NAN in (lo, hi) or (lo == hi and type(lo) is str):
            return (NINF, INF)
        if _key(lo) > _key(hi):
            return EMPTY
        return (lo, hi)
    if kernel == "upward_from_interval_1":
        return default_state(*vals)
    if kernel == "upward_to_interval_1":
        return stored_state(*vals)
    x = stored_state(vals[0], vals[1])
    two = len(vals) == 4
    y = stored_state(vals[2], vals[3]) if two else None
    t = vals[2] if len(vals) == 3 else None
    if kernel in ARITH:
        if x == EMPTY or y == EMPTY:
            return EMPTY
        a, b = x
        if kernel == "upward_neg_1":
            return (_xneg(b), _xneg(a))
        if kernel in ("upward_add_num_1", "upward_mul_num_1"):
            y = (t, t) if type(t) is not str else (NINF, INF)
        c, d = y
        if kernel in ("upward_add_1", "upward_add_num_1"):
            lo, hi = _xadd(a, c), _xadd(b, d)
        elif kernel == "upward_sub_1":
            lo, hi = _xadd(a, _xneg(d)), _xadd(b, _xneg(c))
        else:
            ps = [_xmul0(p, q) for p in (a, b) for q in (c, d)]
            lo, hi = min(ps, key=_key), max(ps, key=_key)
        return (df.rd(lo), df.ru(hi))
    if kernel in SETOPS:
        if kernel == "upward_hull_1":
            ne = [s for s in (x, y) if s != EMPTY]
            if not ne:
                return EMPTY
            return (min((s[0] for s in ne), key=_key), max((s[1] for s in ne), key=_key))
        if x == EMPTY or y == EMPTY:
            return EMPTY
        lo, hi = max((x[0], y[0]), key=_key), min((x[1], y[1]), key=_key)
        return EMPTY if _key(lo) > _key(hi) else (lo, hi)
    ne = lambda s: s != EMPTY  # noqa: E731
    if kernel == "upward_empty_1":
        return (x == EMPTY,)
    if kernel == "upward_entire_1":
        return (x == (NINF, INF),)
    if kernel == "upward_contains_1":
        return (type(t) is not str and ne(x) and _key(x[0]) <= _key(t) <= _key(x[1]),)
    if kernel == "upward_positive_1":
        return (ne(x) and _key(x[0]) > _key(0),)
    if kernel == "upward_negative_1":
        return (ne(x) and _key(x[1]) < _key(0),)
    if kernel == "upward_zero_1":
        return (ne(x) and x[0] == 0 and x[1] == 0,)
    if kernel == "upward_subset_1":
        return (x == EMPTY or (ne(y) and _key(y[0]) <= _key(x[0]) and _key(x[1]) <= _key(y[1])),)
    if kernel == "upward_rel_equal_1":
        return (x == y,)
    if kernel == "upward_rel_interior_1":
        return (x == EMPTY or (ne(y) and (y[0] == NINF or _key(y[0]) < _key(x[0]))
                               and (y[1] == INF or _key(x[1]) < _key(y[1]))),)
    if kernel == "upward_rel_disjoint_1":
        return (x == EMPTY or y == EMPTY or _key(x[1]) < _key(y[0]) or _key(y[1]) < _key(x[0]),)
    both = ne(x) and ne(y)
    if kernel == "upward_less_1":
        return (both and _key(x[1]) < _key(y[0]), both and _key(x[0]) >= _key(y[1]))
    if kernel == "upward_less_equal_1":
        return (both and _key(x[1]) <= _key(y[0]), both and _key(x[0]) > _key(y[1]))
    # upward_equal_1: yes, the same point; no, no common member.
    return (both and x[0] == x[1] == y[0] == y[1],
            both and (_key(x[1]) < _key(y[0]) or _key(y[1]) < _key(x[0])))


OUT_STORED = {k for k in ARITH + SETOPS + ("upward_make_1", "upward_from_interval_1")}


def out_state(kernel, toks):
    """The state of a line's output by the definitions (None when not canonical), or the masks."""
    if kernel in OUT_STORED:
        return stored_state(tok_value(toks[0]), tok_value(toks[1]))
    if kernel == "upward_to_interval_1":
        return default_state(tok_value(toks[0]), tok_value(toks[1]))
    return tuple(t == "1" for t in toks)


def literal(df, v):
    if type(v) is str:
        return v
    if v == 0:
        return "0x0p+0"
    return F.to_hex(int(v / df.eta), df.fmt.qmin)


def encode(df, kernel, state):
    """The output tokens of an interval state (stored, or default for upward_to_interval_1)."""
    if kernel == "upward_to_interval_1":
        return ["inf", "-inf"] if state == EMPTY else [literal(df, state[0]),
                                                       literal(df, state[1])]
    if state == EMPTY:
        return ["nan", "nan"]
    return [literal(df, state[1]), literal(df, _xneg(state[0]))]


def neighbours(df, toks):
    """Output pairs near a pair of lanes: each lane one step up or down, swapped, a NaN lane, the
    lane -inf, the empty set, the whole line, the signs of zeros flipped."""
    out = []
    lanes = []
    for t in toks:
        v = tok_value(t)
        opts = [t]
        if type(v) is not str:
            for w in (df.succ(v), df.pred(v)):
                opts.append(literal(df, w))
            if v == 0:
                opts.append("-0x0p+0" if not t.startswith("-") else "0x0p+0")
        opts += ["nan", "-inf", "inf"]
        lanes.append(opts)
    for a in lanes[0]:
        for b in lanes[1]:
            out.append([a, b])
    out.append([toks[1], toks[0]])
    return out


# ---------------------------------------------------------------------------
# Reading

def _malformed():
    """(kernel of the fixture, a change of its raw claims, what the reason must name)."""
    def ens(f):
        def g(k):
            f(k["ensures"][0])
        return g

    def setf(field, value):
        return ens(lambda e: e.__setitem__(field, value))

    def delf(field):
        return ens(lambda e: e.pop(field))

    def req(i, r):
        def g(k):
            k["requires"][i] = r
        return g

    return [
        # rounding
        ("upward_add_1", lambda k: k.__setitem__("rounding", "downward"),
         'rounding must be "upward"'),
        ("upward_add_1", lambda k: k.__setitem__("rounding", True), 'rounding must be "upward"'),
        ("upward_add_1", lambda k: k.pop("domain"), "rounding belongs to the extended domain"),
        # upward(U, N)
        ("upward_add_1", req(0, "upward(xu, xu)"), "the two lanes are the same input"),
        ("upward_add_1", req(0, "upward(xu, q)"), "q is not a limb input"),
        ("upward_add_1", lambda k: (k["inputs"].__setitem__(0, {"name": "xu", "limbs": 2})),
         "a stored pair is two inputs of one limb each"),
        ("upward_add_1", req(1, "upward(yu, xn)"), "shares an input with another stored pair"),
        ("upward_add_1", lambda k: (k.pop("rounding"), k.pop("domain")),
         "belongs to the extended domain"),
        ("upward_from_interval_1", lambda k: (k["requires"].append("upward(xl, xu)")),
         "shares an input with an interval or a ball"),
        # named sets
        ("upward_add_1", setf("intervals", {"x": {"upper": "xn", "nlower": "xu"},
                                            "y": {"upper": "yu", "nlower": "yn"}}),
         "is not an upward() requirement"),
        ("upward_add_1", setf("intervals", {"x": {"upper": "xu", "nlower": "xn", "lower": "yu"},
                                            "y": {"upper": "yu", "nlower": "yn"}}),
         'must be {"lower": INPUT, "upper": INPUT}'),
        ("upward_add_1", setf("intervals", {"x": {"upper": "xu", "nlower": "xn"},
                                            "y": {"upper": "xu", "nlower": "xn"}}),
         "another name of the same bounds"),
        ("upward_subset_1", setf("intervals", {"x": {"upper": "xu", "nlower": "xn"},
                                               "y": {"lower": "yn", "upper": "yu"}}),
         "is not an interval() requirement"),
        ("upward_hull_1", setf("intervals", {"x": {"upper": "xn", "nlower": "xu"},
                                             "y": {"upper": "yu", "nlower": "yn"}}),
         "is not an upward() requirement"),
        # outputs
        ("upward_add_1", setf("lower", "zn"), "not both"),
        ("upward_add_1", setf("nlower", "zu"), "upper and nlower are the same output"),
        ("upward_add_1", setf("nlower", "xn"), "nlower 'xn' is not a limb output"),
        ("upward_add_1", delf("upper"), "missing upper"),
        ("upward_make_1", setf("nlower", "zu"), "upper and nlower are the same output"),
        ("upward_hull_1", setf("lower", "zn"), "not both"),
        ("upward_mul_1", lambda k: k["outputs"].__setitem__(1, {"name": "zn", "limbs": 2}),
         "a stored pair is two outputs of one limb each"),
        # numbers
        ("upward_add_num_1", setf("numbers", "t"), "numbers must be a nonempty list"),
        ("upward_add_num_1", setf("numbers", []), "numbers must be a nonempty list"),
        ("upward_add_num_1", setf("numbers", ["xu"]), "is an input of a set"),
        ("upward_add_num_1", setf("numbers", ["q"]), "'q' is not a limb input"),
        ("upward_add_num_1", setf("numbers", ["t", "t"]), "t is listed twice"),
        ("upward_add_num_1", delf("numbers"), "set names 't', which is not one of x"),
        ("upward_add_num_1", lambda k: (k["inputs"].append({"name": "s", "limbs": 1}),
                                        k["ensures"][0].__setitem__("numbers", ["t", "s"])),
         "s must occur exactly once in set"),
        ("upward_add_num_1", lambda k: (k["inputs"].__setitem__(2, {"name": "t", "limbs": 2})),
         "t must be an input of one limb"),
        ("upward_mul_num_1", setf("tight", {"kind": "rounded", "when": "product_large"}),
         "needs a set that is a product of two intervals"),
        ("upward_mul_num_1", setf("zero_factor", True),
         "zero_factor needs a set that is a product of two intervals"),
        ("upward_mul_1", setf("tight", {"kind": "rounded", "when": "product_large"}),
         "when product_large is not read over stored pairs"),
        # same_set
        ("upward_to_interval_1", delf("of"), "missing of"),
        ("upward_to_interval_1", delf("from"), "missing from"),
        ("upward_to_interval_1", setf("of", {"upper": "zu"}), "of must be"),
        ("upward_to_interval_1", setf("of", {"lower": "zl", "upper": "zl"}),
         "names the same output twice"),
        ("upward_to_interval_1", setf("of", {"lower": "xu", "upper": "zu"}), "is not a limb output"),
        ("upward_to_interval_1", setf("from", {"upper": "zl", "nlower": "zu"}),
         "is not an upward() requirement"),
        ("upward_to_interval_1", setf("from", {"upper": "xu"}), 'must be {"lower": INPUT'),
        ("upward_from_interval_1", setf("from", {"lower": "xu", "upper": "xl"}),
         "is not an interval() requirement"),
        ("upward_to_interval_1", setf("weight", 1), "unknown fields ['weight']"),
        ("upward_to_interval_1", lambda k: (k.pop("rounding"), k.pop("domain")),
         "belongs to the extended domain"),
        ("upward_from_interval_1", lambda k: (k["outputs"].__setitem__(0, {"name": "zu",
                                                                           "limbs": 2})),
         "must be an output of one limb"),
        # certain and trit over stored pairs
        ("upward_less_1", setf("intervals", {"x": {"upper": "xu", "nlower": "xn"},
                                             "y": {"upper": "yn", "nlower": "yu"}}),
         "is not an upward() requirement"),
        ("upward_contains_1", setf("args", ["xu", "x"]), "the point of member must be"),
    ]


@test
def claims_reading_up(ctx):
    """The fixture of the round-up interval read as the page says, and each malformed entry set
    aside alone with its reason."""
    cl = claims_up(ctx)
    expect(not cl.errors(), "the fixture has claims errors: %s" % cl.errors()[:3])
    expect(sorted(cl.kernels) == sorted(KERNELS), "the fixture's kernels: %s" % sorted(cl.kernels))
    for name in KERNELS:
        k = cl.get(name)
        expect(k.rounding == "upward", "%s: rounding %r" % (name, k.rounding))
        expect(k.unknown_fields == ["ieee_only"], "%s: unknown fields %s" % (name, k.unknown_fields))
    labels = {name: cl.get(name).ensures[0].label for name in KERNELS}
    want = {
        "upward_mul_1": "encloses_interval(upper zu, nlower zn) x*y over x=(upper xu, nlower xn), "
                        "y=(upper yu, nlower yn), I1-I5, tight rounded, bounded exactly when "
                        "|x*y| <= Omega",
        "upward_add_num_1": "encloses_interval(upper zu, nlower zn) x+t over x=(upper xu, nlower "
                            "xn), I1-I5, tight rounded, numbers t (each the members of "
                            "Interval(t)), bounded exactly when |x+t| <= Omega",
        "upward_hull_1": "interval_set(upper zu, nlower zn) union of x=(upper xu, nlower xn), "
                         "y=(upper yu, nlower yn)",
        "upward_make_1": "makes_interval(upper zu, nlower zn) from lower lo, upper hi",
        "upward_to_interval_1": "same_set([zl, zu]) as (upper xu, nlower xn)",
        "upward_from_interval_1": "same_set((upper zu, nlower zn)) as [xl, xu]",
        "upward_less_1": "trit(yes yes, no no) lt(x, y) over x=(upper xu, nlower xn), y=(upper yu, "
                         "nlower yn), exact",
    }
    for name, w in want.items():
        expect(labels[name] == w, "%s: label %r, not %r" % (name, labels[name], w))
    expect(cl.get("upward_add_1").requires == [("upward", "xu", "xn"), ("upward", "yu", "yn")],
           "upward(): %s" % cl.get("upward_add_1").requires)
    raw = raw_up()
    bad = []
    for kname, change, reason in _malformed():
        r = copy.deepcopy(raw)
        k = next(x for x in r["kernels"] if x["name"] == kname)
        change(k)
        c = Claims(r)
        why = c.broken.get(kname)
        others = sorted(set(c.broken) - {kname})
        if why is None or reason not in why or others:
            bad.append("%s / %s: set aside %r, others %s" % (kname, reason, why, others))
    expect(not bad, "malformed entries not set aside as expected:\n  " + "\n  ".join(bad))
    # The field rounding is not required by the stored pairs (a reading the page leaves open).
    r = copy.deepcopy(raw)
    for k in r["kernels"]:
        k.pop("rounding")
    c = Claims(r)
    expect(not c.broken, "without rounding: %s" % sorted(c.broken.items())[:2])
    # The generator's headers carry rounding=upward for these kernels, and only for them.
    g = G.RandomGen(cl.get("upward_add_1"), F.parse_format("binary64"), 0)
    h = list(g.lines(0, 1))[0]
    e = G.ExhaustiveGen(cl.get("upward_neg_1"), F.parse_format("fp:1:0:1"))
    he = list(e.lines(0, 1))[0]
    expect(" rounding=upward " in h and " rounding=upward " in he, "headers %r, %r" % (h, he))
    from .selftest_enc import claims_enc
    g2 = G.RandomGen(claims_enc(ctx).get("interval_less_1"), F.parse_format("binary64"), 0)
    expect("rounding" not in list(g2.lines(0, 1))[0], "an interval kernel's header with rounding")
    return "24 kernels, %d malformed entries set aside" % len(_malformed())


# ---------------------------------------------------------------------------
# Arithmetic

def _brute_ru(nums, omega, v):
    """The smallest number of the sorted list not below v, +inf above Omega, -Omega below -Omega."""
    if v > omega:
        return INF
    if v < -omega:
        return -omega
    return nums[bisect.bisect_left(nums, v)]


@test
def up_arithmetic(ctx):
    """The reference runner's rounding upward against a walk over the sorted numbers of seven toy
    formats on every multiple of eta/8 to past twice Omega, and against the checker's
    (directed.round_overflow); its sums and products on every pair of values of three toy formats
    (infinities and NaN included) against IEEE 754's rules as the page states them; both forms of
    max_nl against the property max_nl_ok and their machine definitions; in binary64 the rounding
    upward against the hardware's rounding to nearest moved one step up where it is below."""
    n = 0
    for name in ("fp:1:0:1", "fp:1:-1:1", "fp:2:-2:1", "fp:3:-4:1", "fp:3:-5:2", "fp:4:-6:1",
                 "fp:5:-3:3"):
        df = Def(name)
        fmt = df.fmt
        A = refrun.Arith(refrun.parse_format_triple(name))
        U = RU.UpArith(A, "sel")
        nums = [int(v / df.eta) for v in df.numbers()]
        om = fmt.omega
        for m in range(-(5 * om * 8 // 2), 5 * om * 8 // 2 + 1):
            v = Q(m, 8)
            want = _brute_ru(nums, om, v)
            got = U.ru(m, 3)
            chk = D.round_overflow(fmt, m, fmt.qmin - 3, "up")
            if not (got == want or (want == INF and got == math.inf)):
                raise AssertionError("%s: RU(%s eta) = %s, not %s" % (name, v, got, want))
            if chk != (want if want != INF else INF):
                raise AssertionError("%s: the checker's RU(%s eta) = %s, not %s" % (name, v, chk,
                                                                                    want))
            n += 1
    # Sums and products of every pair of values, the special values by IEEE 754's rules.
    for name in ("fp:1:0:1", "fp:2:-2:1", "fp:3:-4:1"):
        df = Def(name)
        A = refrun.Arith(refrun.parse_format_triple(name))
        U = RU.UpArith(A, "sel")
        vals = [int(v / df.eta) for v in df.numbers()] + [math.inf, -math.inf, math.nan]
        for a in vals:
            for b in vals:
                for op in ("add", "mul"):
                    got = U.add_ru(a, b) if op == "add" else U.mul_ru(a, b)
                    want = _ieee_up(df, op, a, b)
                    same = (got != got and want != want) or got == want
                    if not same:
                        raise AssertionError("%s: %s_ru(%s, %s) = %s, not %s" % (
                            name, op, a, b, got, want))
                    n += 1
                for form in FORMS:
                    m = RU.UpArith(A, form).max_nl(a, b)
                    _max_ok(form, a, b, m, name)
    # binary64 against the hardware: RN, then one step up where RN is below the exact value.
    rnd = random.Random(20261125)
    A = refrun.Arith(refrun.parse_format_triple("binary64"))
    U = RU.UpArith(A, "sel")
    for _ in range(ctx.n(20000, 4000)):
        x, y = _rand_double(rnd), _rand_double(rnd)
        for op in ("add", "mul"):
            exact = Q(x) + Q(y) if op == "add" else Q(x) * Q(y)
            try:
                h = float(exact)
            except OverflowError:
                h = math.inf if exact > 0 else -math.inf
            if math.isinf(h):
                want = math.inf if exact > 0 else -1.7976931348623157e308
            else:
                want = h if Q(h) >= exact else math.nextafter(h, math.inf)
            fx, fy = A.read(x.hex()), A.read(y.hex())
            got = U.add_ru(fx, fy) if op == "add" else U.mul_ru(fx, fy)
            gotf = got if type(got) is float else float(Q(got) * Q(2) ** -1074)
            if gotf != want:
                raise AssertionError("binary64: %s_ru(%s, %s) = %r, not %r" % (
                    op, x.hex(), y.hex(), gotf, want))
            n += 1
    return "%d roundings, sums, products and maxima" % n


def _rand_double(rnd):
    j = rnd.randrange(5)
    if j == 0:
        return rnd.choice([0.0, 5e-324, 2.2250738585072014e-308, 1.7976931348623157e308, 1.0])
    e = rnd.randrange(-1074, 1024) if j == 1 else rnd.randrange(-540, 512)
    m = rnd.getrandbits(53) | (1 << 52)
    try:
        v = math.ldexp(m, e - 52)
    except OverflowError:
        v = 1.7976931348623157e308
    return -v if rnd.random() < 0.5 else v


def _ieee_up(df, op, a, b):
    """IEEE 754's sum or product rounded toward +inf on fixed values (units of eta) and Python's
    infinities and NaN: a NaN for a NaN operand, inf - inf and 0 * inf; the infinity otherwise; the
    exact value rounded by the definition for finite operands."""
    isnan = lambda v: v != v  # noqa: E731
    if isnan(a) or isnan(b):
        return math.nan
    fa, fb = type(a) is int, type(b) is int
    if op == "add":
        if not fa and not fb:
            return a if a == b else math.nan
        if not fa or not fb:
            return a if not fa else b
        v = df.ru((a + b) * df.eta)
    else:
        if not fa or not fb:
            if a == 0 or b == 0:
                return math.nan
            return math.inf if (a > 0) == (b > 0) else -math.inf
        v = df.ru(Q(a) * b * df.eta * df.eta)
    if v == INF:
        return math.inf
    return int(v / df.eta)


def _max_ok(form, a, b, m, name):
    """max_nl_ok (upward.md, "The maximum"): for b not a NaN, b when a is a NaN, otherwise a or b
    and at least both; and each machine form's own definition everywhere."""
    isnan = lambda v: v != v  # noqa: E731
    if not isnan(b):
        if isnan(a):
            ok = m == b
        else:
            ok = (m == a or m == b) and m >= a and m >= b
        if not ok:
            raise AssertionError("%s: max_nl %s(%s, %s) = %s breaks max_nl_ok" % (name, form, a, b,
                                                                                   m))
    if form == "sel":
        want = a if b < a else b
    elif isnan(a) and isnan(b):
        want = math.nan
    else:
        want = b if isnan(a) else a if isnan(b) else max(a, b)
    if not ((isnan(want) and isnan(m)) or want == m):
        raise AssertionError("%s: max_nl %s(%s, %s) = %s, not %s" % (name, form, a, b, m, want))


# ---------------------------------------------------------------------------
# The reference runner: random streams and enumerations

NEEDED = {
    "arith": ("result: empty", "result: bounded", "result: unbounded",
              "operands: an empty operand", "operands: bounded",
              "operands: nonempty, an unbounded operand"),
    "rounds": ("lower: at the directed rounding", "upper: at the directed rounding",
               "lower: range bound not a number of the format",
               "upper: range bound not a number of the format",
               "bounded operands, bounded_when holds", "bounded operands, bounded_when fails",
               "bounded operands, unbounded result"),
    "numbers": ("number t: finite", "number t: infinite", "number t: NaN"),
    "set": ("an operand empty", "nonempty operands, disjoint",
            "nonempty operands, touching (one common point)", "nonempty operands, overlapping",
            "result: empty"),
    "make": tuple(IV.MAKE_CELLS),
    "conv": ("X: empty", "X: whole line", "X: half-line [l, +inf]", "X: half-line [-inf, h]",
             "X: bounded", "result: empty", "result: nonempty"),
    "certain": ("the relation holds", "the relation does not hold", "x: empty", "x: whole line",
                "x: half-line", "x: bounded"),
    "trit": ("the relation holds", "the relation fails for every choice",
             "the relation neither holds nor fails for every choice", "answer yes", "answer no",
             "answer unknown"),
}


def needed(kernel):
    if kernel in ARITH:
        n = NEEDED["arith"]
        if kernel != "upward_neg_1":
            n = n + NEEDED["rounds"]
        if "num" in kernel:
            n = n + NEEDED["numbers"]
        return n
    if kernel in SETOPS:
        return NEEDED["set"]
    if kernel == "upward_make_1":
        return NEEDED["make"]
    if kernel in CONV:
        return NEEDED["conv"]
    return NEEDED["trit"] if kernel in TRIT else NEEDED["certain"]


@test
def up_reference(ctx):
    """The reference runner (the listings of the page) on random streams of every kernel in
    binary64, binary32 and fp:4:-6:1, with both forms of max_nl: no failure, no invalid or
    suspicious case, every entry applied; in binary64 and binary32 every class the claim is about
    reached (empty, bounded and unbounded results, roundings inexact, bounded_when both ways, each
    class of a number, each cell of the constructor's table, each answer)."""
    cl = claims_up(ctx)
    count = ctx.n(1500, 400)
    n = 0
    for fmtname in FORMATS:
        for form in FORMS:
            for k in KERNELS:
                out = run_up(stream_up(ctx, k, fmtname, count), form=form)
                s = judge(out, cl)
                t = totals(s, k)
                expect(t["judged"] == count and t["passed"] == count and not t["invalid"]
                       and not t["suspicious"],
                       "%s %s (%s): %s; %s" % (k, fmtname, form, t, _examples(s)))
                st = entry_stats(s, k)
                expect(all(d[1] for d in st.values()), "%s: an entry never applied" % k)
                if fmtname != "fp:4:-6:1" and form == "sel":
                    cnt = counts_of(s, k)
                    miss = [c for c in needed(k) if not cnt.get(c)]
                    if k in PRED:
                        for nm in ("x", "y") if len(cl.get(k).upward_requires) == 2 else ("x",):
                            miss += [c for c in ("%s: empty" % nm, "%s: whole line" % nm)
                                     if not cnt.get(c)]
                    expect(not miss, "%s %s: never %s" % (k, fmtname, miss))
                n += count
    return "%d lines" % n


def _examples(s, kind="failure"):
    out = []
    for st in s.keys.values():
        out.extend(st.examples.get(kind, [])[:2])
        out.extend(st.examples.get("invalid", [])[:1])
    return "; ".join(str(e) for e in out[:3])


TINY = ("fp:1:0:1", "fp:1:-1:1", "fp:2:-2:1")


def _enum(cl, k, fmtname):
    g = G.ExhaustiveGen(cl.get(k), F.parse_format(fmtname))
    return list(g.lines(0, g.total)), g.total


@test
def up_exhaustive(ctx):
    """The reference runner on every case of the enumerations of tiny formats (every pair of
    canonical states, every value of a number), with both forms of max_nl: every line judged, the
    coverage complete, no failure; and the listings' results those of the definitions (Def) on
    every case; the planted faults caught there in their kernels."""
    cl = claims_up(ctx)
    fmts = TINY if not ctx.quick else TINY[:2]
    n = 0
    for fmtname in fmts:
        df = Def(fmtname)
        for k in KERNELS:
            lines, total = _enum(cl, k, fmtname)
            for form in FORMS:
                out = run_up(lines, form=form)
                s = judge(out, cl)
                t = totals(s, k)
                expect(t["judged"] == total == t["passed"] and not t["invalid"],
                       "%s %s (%s): %s; %s" % (k, fmtname, form, t, _examples(s)))
                cov = s.coverage.describe()
                expect(any("COMPLETE" in c for c in cov), "%s %s: coverage %s" % (k, fmtname, cov))
                for ln in body(out):
                    left, _, right = ln.partition(" -> ")
                    vals = [tok_value(x) for x in left.split()[2:-1]]
                    want = expected(df, k, vals)
                    got = out_state(k, right.split())
                    expect(got == want, "%s %s (%s): the listing gives %s, the definition %s: %s"
                           % (k, fmtname, form, got, want, ln))
                n += total
    # The planted faults, on the enumerations of fp:1:-1:1.
    fmtname = "fp:1:-1:1"
    for v, (ks, required, _allowed) in PLANTED.items():
        if not required:
            continue
        caught = False
        for k in ks:
            lines, _ = _enum(cl, k, fmtname)
            s = judge(run_up(lines, v), cl)
            caught = caught or totals(s, k)["failed"] > 0
        expect(caught, "%s: not caught on the enumeration of %s" % (v, fmtname))
    return "%d cases in %s, both forms of max_nl" % (n, ", ".join(fmts))


# ---------------------------------------------------------------------------
# The definitions: the oracle accepts exactly the result they give

def _all_tokens(df):
    toks = [literal(df, v) for v in df.numbers()] + ["-0x0p+0", "inf", "-inf", "nan"]
    return toks


def _input_lines(cl, k, fmtname):
    lines, _ = _enum(cl, k, fmtname)
    return [ln.rsplit(" #", 1)[0] for ln in body(lines)]


@test
def up_definition(ctx):
    """For every kernel, on every input of fp:1:0:1 the oracle passes the result of the definitions
    and fails every other output (every pair of lanes, canonical or not, the signs of zeros free);
    on every input of fp:1:-1:1 (and fp:2:-2:1 without --quick) and on special values of binary64
    and binary32 it passes that result and fails each output near it (a lane one step off, a NaN
    lane, a lane -inf, the lanes swapped, the empty set, the whole line, the other answers of a
    mask)."""
    cl = claims_up(ctx)
    lj = LineJudge(cl)
    n = 0
    # fp:1:0:1: every output.
    df = Def("fp:1:0:1")
    toks = _all_tokens(df)
    for k in KERNELS:
        for left in _input_lines(cl, k, "fp:1:0:1"):
            n += _check_outputs(lj, df, k, left, _candidates(k, toks))
    # fp:1:-1:1, fp:2:-2:1: the outputs near the expected one, on a sample of the inputs.
    for fmtname in ("fp:1:-1:1",) + (() if ctx.quick else ("fp:2:-2:1",)):
        df = Def(fmtname)
        for k in KERNELS:
            for left in _sample(_input_lines(cl, k, fmtname), ctx.n(400, 120)):
                n += _check_outputs(lj, df, k, left, None)
    # binary64 and binary32: the special values.
    for fmtname in ("binary64", "binary32"):
        df = Def(fmtname)
        for k in KERNELS:
            for left in _special_lines(df, cl, k, ctx.n(18, 10)):
                n += _check_outputs(lj, df, k, left, None)
    return "%d lines judged against the definitions" % n


def _sample(lines, n):
    """Every k-th line, about n of them (all when there are fewer)."""
    step = max(1, len(lines) // n)
    return lines[::step]


def _candidates(k, toks):
    if k in PRED:
        width = 2 if k in TRIT else 1
        return [list(c) for c in ([["0"], ["1"]] if width == 1 else
                                  [["0", "0"], ["0", "1"], ["1", "0"], ["1", "1"]])]
    return [[a, b] for a in toks for b in toks]


def _check_outputs(lj, df, k, left, cands):
    """The expected output passes and every other candidate fails; the number of lines judged."""
    vals = [tok_value(t) for t in left.split()[2:]]
    want = expected(df, k, vals)
    if k in PRED:
        want_toks = ["1" if b else "0" for b in want]
        cands = cands or _candidates(k, None)
    else:
        want_toks = encode(df, k, want)
        cands = cands or neighbours(df, want_toks) + [["nan", "nan"], ["inf", "inf"],
                                                      ["-inf", "-inf"], ["inf", "-inf"]]
    status, _st, why = lj(left + " -> " + " ".join(want_toks))
    expect(status == "pass", "%s: the definition's result %s does not pass: %s" % (
        left, want_toks, why))
    n = 1
    for c in cands:
        got = out_state(k, c)
        if got == want and (k not in PRED or c == want_toks):
            status, _st, why = lj(left + " -> " + " ".join(c))
            expect(status == "pass", "%s -> %s: the same result fails: %s" % (left, c, why))
        else:
            status, _st, why = lj(left + " -> " + " ".join(c))
            expect(status == "fail", "%s -> %s: passes, and the definition gives %s" % (
                left, " ".join(c), want_toks))
        n += 1
    return n


def _special_intervals(df):
    """Special intervals of a format: the empty set, the whole line, half-lines, points, bounds at
    zero, eta, lambda, one, Omega and their neighbours."""
    om, eta = df.omega, df.eta
    lam = df.value(df.s)
    one = Q(1)
    pts = [Q(0), eta, -eta, lam, -lam, one, -one, om, -om, df.pred(om), 3 * eta,
           df.pred(lam), df.succ(one)]
    out = [EMPTY, (NINF, INF), (Q(0), Q(0)), (NINF, Q(0)), (Q(0), INF), (one, INF), (NINF, -one),
           (-eta, eta), (lam, 2 * lam), (-om, om), (om, om), (-om, -om), (one, df.succ(one)),
           (-lam, one), (df.pred(om), om), (Q(0), eta), (-one, Q(0)), (eta, eta), (om, INF),
           (NINF, -om), (3 * eta, one)]
    out += [(p, p) for p in pts]
    return out


def _special_lines(df, cl, k, pairs):
    """Request lines of a kernel on the special values (the first `pairs` special intervals for a
    kernel of two)."""
    name = df.fmt.name
    ivs = _special_intervals(df)

    def stored(iv):
        return ["nan", "nan"] if iv == EMPTY else [literal(df, iv[1]), literal(df, _xneg(iv[0]))]

    nums = [Q(0), df.eta, -df.eta, Q(1), Q(-3), df.omega, -df.omega, Q(1, 2), INF, NINF, NAN,
            df.value(df.s), df.succ(Q(1))]
    lines = []
    if k == "upward_make_1":
        for a in nums:
            for b in nums:
                lines.append("%s %s %s %s" % (k, name, literal(df, a), literal(df, b)))
        return lines
    if k == "upward_from_interval_1":
        for iv in ivs:
            t = ["inf", "-inf"] if iv == EMPTY else [literal(df, iv[0]), literal(df, iv[1])]
            lines.append("%s %s %s" % (k, name, " ".join(t)))
        return lines
    ups = len(cl.get(k).upward_requires)
    has_t = len(cl.get(k).inputs) == 3
    if ups == 1:
        for iv in ivs:
            if has_t:
                for t in nums + ([iv[0], iv[1]] if iv != EMPTY else []):
                    lines.append("%s %s %s %s" % (k, name, " ".join(stored(iv)), literal(df, t)))
            else:
                lines.append("%s %s %s" % (k, name, " ".join(stored(iv))))
        return lines
    for a in ivs[:pairs]:
        for b in ivs[:pairs]:
            lines.append("%s %s %s %s" % (k, name, " ".join(stored(a)), " ".join(stored(b))))
    return lines


# ---------------------------------------------------------------------------
# Planted faults

# variant: (kernels it changes, statements one of which must be counted, statements allowed)
PLANTED = {
    "up-mul-step-small": (("upward_mul_1",), {"I4"}, {"I4"}),
    "up-empty-nonempty": (("upward_add_1", "upward_sub_1"), {"I2"}, {"I2"}),
    "up-hull-one-select": (("upward_hull_1",), {"not canonical: one NaN lane"},
                           {"not canonical", "not canonical: one NaN lane"}),
    "up-lane-neg-inf": (("upward_from_interval_1",), {"not canonical: a lane -inf"},
                        {"canonical", "not canonical: a lane -inf"}),
    "up-crossed": (("upward_intersection_1",), {"not canonical: crossed lanes (-nlower > upper)"},
                   {"not canonical", "not canonical: crossed lanes (-nlower > upper)"}),
    "up-lower-not-negated": (("upward_to_interval_1",), {"members"}, {"members", "canonical"}),
    "up-number-point": (("upward_add_num_1", "upward_mul_num_1"), {"I1", "I3"},
                        {"I1", "I2", "I3", "I4", "not canonical: a lane -inf",
                         "not canonical: one NaN lane"}),
    "up-add-nearest": (("upward_add_1",), {"I3"},
                       {"I1", "I3", "I4", "I5", "not canonical: a lane -inf"}),
    "up-mul-negated": (("upward_mul_1",), {"I3"},
                       {"I1", "I3", "I4", "I5", "not canonical: a lane -inf"}),
    "up-mul-nan-seed": (("upward_mul_1",), {"I1", "I2"},
                        {"I1", "I2", "I3", "I4", "not canonical: one NaN lane"}),
    "up-mul-empty-kept": (("upward_mul_1",), {"I2"}, {"I2"}),
    "up-subset-empty": (("upward_subset_1",), {"exact"}, {"exact"}),
    "up-less-not-negated": (("upward_less_1",), {"yes", "exact", "no"},
                            {"yes", "no", "both", "exact"}),
    "up-contains-infinite": (("upward_contains_1",), {"sound"}, {"sound"}),
    "up-make-crossed": (("upward_make_1",), {"not canonical: crossed lanes (-nlower > upper)"},
                        {"not canonical", "not canonical: a lane -inf",
                         "not canonical: crossed lanes (-nlower > upper)"}),
    "up-zero-signs": (KERNELS, set(), set()),
}


def _values(right):
    """The values of a line's outputs (a NaN equal to a NaN, the sign of a zero dropped)."""
    out = []
    for t in right.split():
        v = tok_value(t) if t not in ("0", "1") else t
        out.append("nan" if v == NAN else v)
    return out


@test
def up_planted(ctx):
    """Each planted fault of refup.VARIANTS caught in the kernels it changes, in a statement it is
    about and in none it is not, in binary64, binary32 and fp:4:-6:1, never seen as an invalid or
    suspicious case; every line whose values it changes failing (every claim of these kernels
    fixes the output's value); the other kernels' outputs unchanged; up-zero-signs, which changes
    only the signs of zeros, passing everywhere; up-hull-one-select invisible with the FMAXNM form
    (the NaN it leaves in lane 1 is MAXPD's)."""
    cl = claims_up(ctx)
    expect(set(PLANTED) == set(RU.VARIANTS), "planted faults without a test: %s"
           % sorted(set(PLANTED) ^ set(RU.VARIANTS)))
    count = ctx.n(1200, 300)
    lj = LineJudge(cl)
    good = {}
    for fmtname in FORMATS:
        for k in KERNELS:
            good[(k, fmtname)] = run_up(stream_up(ctx, k, fmtname, count))
    bad = []
    for v, (ks, required, allowed) in PLANTED.items():
        assert v in RU.VARIANTS, v
        changed_total = 0
        for fmtname in FORMATS:
            hit = False
            for k in KERNELS:
                lines = stream_up(ctx, k, fmtname, count)
                if k not in ks:
                    few = lines[:ctx.n(200, 60)]
                    if body(run_up(few, v)) != body(good[(k, fmtname)][:len(few)]):
                        bad.append("%s changes %s, which it is not about" % (v, k))
                    continue
                outv = run_up(lines, v)
                s = judge(outv, cl)
                t = totals(s, k)
                if t["invalid"] or t["suspicious"]:
                    bad.append("%s %s %s: invalid or suspicious %s" % (v, k, fmtname, t))
                fs = failed_statements(counts_of(s, k))
                if fs - allowed:
                    bad.append("%s %s %s: failed %s, outside %s" % (v, k, fmtname, sorted(fs),
                                                                     sorted(allowed)))
                if required and fs & required:
                    hit = True
                for a, b in zip(body(good[(k, fmtname)]), body(outv)):
                    ra, rb = a.partition(" -> ")[2], b.partition(" -> ")[2]
                    if ra == rb:
                        continue
                    status = lj(b)[0]
                    if _values(ra) == _values(rb):
                        if status != "pass":
                            bad.append("%s: a line that differs in the signs of zeros only "
                                       "fails: %s" % (v, b))
                        continue
                    changed_total += 1
                    if status != "fail":
                        bad.append("%s: a changed line passes: %s (correct: %s)" % (v, b, ra))
            if required and not hit:
                bad.append("%s %s: none of %s counted" % (v, fmtname, sorted(required)))
        if required and not changed_total:
            bad.append("%s: changed no line" % v)
    # MAXPD's NaN: with FMAXNM the hull without its selection of lane 1 is right.
    for fmtname in FORMATS:
        out = run_up(stream_up(ctx, "upward_hull_1", fmtname, count), "up-hull-one-select", "nm")
        t = totals(judge(out, cl), "upward_hull_1")
        if t["failed"]:
            bad.append("up-hull-one-select with FMAXNM fails %d lines" % t["failed"])
    expect(not bad, "planted faults:\n  " + "\n  ".join(bad[:12]))
    return "%d faults, %d lines of each kernel and format" % (len(PLANTED), count)


# ---------------------------------------------------------------------------
# Hand-written lines

OM = "0x1.fffffffffffffp+1023"
ETA = "0x0.0000000000001p-1022"

# (line, status, failed statements): each worked out by hand from the page.
JUDGE = [
    # sum: x = [1, 2] (2, -1), y = [2, 4] (4, -2): [3, 6] (6, -3)
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1.8p+2 -0x1.8p+1", "pass", set()),
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1.8p+2 -0x1p+1", "fail", {"I4"}),
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1.8p+2 -0x1p+2", "fail",
     {"I3", "I4"}),
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1.8p+2 nan", "fail",
     {"I1", "not canonical: one NaN lane"}),
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> nan nan", "fail", {"I2"}),
    # the lower bound read without its negation: (6, 3) is [-3, 6]
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1.8p+2 0x1.8p+1", "fail", {"I4"}),
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1p+0 -0x1p+1", "fail",
     {"I1", "not canonical: crossed lanes (-nlower > upper)"}),
    ("upward_add_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> -inf -0x1.8p+1", "fail",
     {"I1", "not canonical: a lane -inf"}),
    # 1 + eta: RU 1 + 2^-52, RD 1
    ("upward_add_1 binary64 0x1p+0 -0x1p+0 %s -%s -> 0x1.0000000000001p+0 -0x1p+0" % (ETA, ETA),
     "pass", set()),
    ("upward_add_1 binary64 0x1p+0 -0x1p+0 %s -%s -> 0x1p+0 -0x1p+0" % (ETA, ETA), "fail",
     {"I3", "I4"}),
    # overflow: [Omega, Omega] + [Omega, Omega] = [2 Omega, 2 Omega]: (+inf, -Omega)
    ("upward_add_1 binary64 %s -%s %s -%s -> inf -%s" % (OM, OM, OM, OM, OM), "pass", set()),
    ("upward_add_1 binary64 %s -%s %s -%s -> %s -%s" % (OM, OM, OM, OM, OM, OM), "fail",
     {"I3", "I4", "I5"}),
    ("upward_add_1 binary64 -%s %s -%s %s -> -%s inf" % (OM, OM, OM, OM, OM), "pass", set()),
    ("upward_add_1 binary64 nan nan 0x1p+0 -0x1p+0 -> nan nan", "pass", set()),
    ("upward_add_1 binary64 nan nan 0x1p+0 -0x1p+0 -> 0x1p+0 -0x1p+0", "fail", {"I2"}),
    # (-inf, -inf) is not the empty set: the default empty set with its lower bound negated
    ("upward_add_1 binary64 nan nan 0x1p+0 -0x1p+0 -> -inf -inf", "fail",
     {"I1", "not canonical: a lane -inf"}),
    ("upward_add_1 binary64 inf inf 0x1p+0 -0x1p+0 -> inf inf", "pass", set()),
    ("upward_add_1 binary64 0x1p+0 -0x1p+0 -0x1p+0 0x1p+0 -> 0x0p+0 0x0p+0", "pass", set()),
    ("upward_add_1 binary64 0x1p+0 -0x1p+0 -0x1p+0 0x1p+0 -> -0x0p+0 -0x0p+0", "pass", set()),
    # inputs outside the requirements
    ("upward_add_1 binary64 nan 0x1p+0 0x1p+0 -0x1p+0 -> nan nan", "invalid", set()),
    ("upward_add_1 binary64 -inf -inf 0x1p+0 -0x1p+0 -> nan nan", "invalid", set()),
    ("upward_add_1 binary64 0x1p+0 -0x1p+1 0x1p+0 -0x1p+0 -> 0x1p+1 -0x1p+2", "invalid", set()),
    ("upward_add_1 binary64 0x1p+0 -inf 0x1p+0 -0x1p+0 -> inf -inf", "invalid", set()),
    # difference: [1, 2] - [2, 4] = [-3, 0]: (0, 3)
    ("upward_sub_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x0p+0 0x1.8p+1", "pass", set()),
    ("upward_sub_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1.8p+1 -0x0p+0", "fail",
     {"I3", "I4"}),
    # negation: -[1, 2] = [-2, -1]: (-1, 2); -[1, +inf] = [-inf, -1]: (-1, +inf)
    ("upward_neg_1 binary64 0x1p+1 -0x1p+0 -> -0x1p+0 0x1p+1", "pass", set()),
    ("upward_neg_1 binary64 0x1p+1 -0x1p+0 -> 0x1p+1 -0x1p+0", "fail", {"I3", "I4"}),
    ("upward_neg_1 binary64 inf -0x1p+0 -> -0x1p+0 inf", "pass", set()),
    # product: [1, 2] [2, 4] = [2, 8]; [-1, 2] [3, 5] = [-5, 10]
    ("upward_mul_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1p+1 -> 0x1p+3 -0x1p+1", "pass", set()),
    ("upward_mul_1 binary64 0x1p+1 0x1p+0 0x1.4p+2 -0x1.8p+1 -> 0x1.4p+3 0x1.4p+2", "pass",
     set()),
    # 0 * inf: [0, 0] times the whole line is [0, 0]
    ("upward_mul_1 binary64 0x0p+0 -0x0p+0 inf inf -> 0x0p+0 0x0p+0", "pass", set()),
    ("upward_mul_1 binary64 0x0p+0 -0x0p+0 inf inf -> nan nan", "fail", {"I2"}),
    ("upward_mul_1 binary64 0x0p+0 -0x0p+0 inf inf -> inf inf", "fail", {"I4"}),
    # [0, 1] [1, +inf] = [0, +inf]: (+inf, -0)
    ("upward_mul_1 binary64 0x1p+0 -0x0p+0 inf -0x1p+0 -> inf -0x0p+0", "pass", set()),
    ("upward_mul_1 binary64 0x1p+0 -0x0p+0 inf -0x1p+0 -> inf inf", "fail", {"I4"}),
    # a product of bounds below P = 2^-969: a = 1 + 2^-52 at 2^-500, a^2 = (1 + 2^-51 + 2^-104)
    # 2^-1000: RU (1 + 3 2^-52) 2^-1000, RD (1 + 2^-51) 2^-1000, exactly; one step wider fails
    ("upward_mul_1 binary64 0x1.0000000000001p-500 -0x1.0000000000001p-500 0x1.0000000000001p-500 "
     "-0x1.0000000000001p-500 -> 0x1.0000000000003p-1000 -0x1.0000000000002p-1000", "pass", set()),
    ("upward_mul_1 binary64 0x1.0000000000001p-500 -0x1.0000000000001p-500 0x1.0000000000001p-500 "
     "-0x1.0000000000001p-500 -> 0x1.0000000000003p-1000 -0x1.0000000000001p-1000", "fail",
     {"I4"}),
    ("upward_mul_1 binary64 0x1.0000000000001p-500 -0x1.0000000000001p-500 0x1.0000000000001p-500 "
     "-0x1.0000000000001p-500 -> 0x1.0000000000004p-1000 -0x1.0000000000002p-1000", "fail",
     {"I4"}),
    # Omega [2, 2] = [2 Omega, 2 Omega]: (+inf, -Omega); -Omega [2, 2]: (-Omega, +inf)
    ("upward_mul_1 binary64 %s -%s 0x1p+1 -0x1p+1 -> inf -%s" % (OM, OM, OM), "pass", set()),
    ("upward_mul_1 binary64 -%s %s 0x1p+1 -0x1p+1 -> -%s inf" % (OM, OM, OM), "pass", set()),
    # operations with a number: [1, 2] + 1/2 = [3/2, 5/2]
    ("upward_add_num_1 binary64 0x1p+1 -0x1p+0 0x1p-1 -> 0x1.4p+1 -0x1.8p+0", "pass", set()),
    ("upward_add_num_1 binary64 0x1p+1 -0x1p+0 inf -> inf inf", "pass", set()),
    ("upward_add_num_1 binary64 0x1p+1 -0x1p+0 -inf -> inf inf", "pass", set()),
    ("upward_add_num_1 binary64 0x1p+1 -0x1p+0 nan -> inf inf", "pass", set()),
    # t = +inf treated as the point +inf: (+inf, -inf)
    ("upward_add_num_1 binary64 0x1p+1 -0x1p+0 inf -> inf -inf", "fail",
     {"I1", "not canonical: a lane -inf"}),
    ("upward_add_num_1 binary64 0x1p+1 -0x1p+0 nan -> nan nan", "fail", {"I2"}),
    ("upward_add_num_1 binary64 nan nan inf -> nan nan", "pass", set()),
    # [1, Omega] + Omega = [1 + Omega, 2 Omega]: RD(1 + Omega) = Omega, RU(2 Omega) = +inf
    ("upward_add_num_1 binary64 %s -0x1p+0 %s -> inf -%s" % (OM, OM, OM), "pass", set()),
    ("upward_add_num_1 binary64 %s -0x1p+0 %s -> inf -0x1p+0" % (OM, OM), "fail", {"I4"}),
    # [1, 2] (-3) = [-6, -3]: (-3, 6)
    ("upward_mul_num_1 binary64 0x1p+1 -0x1p+0 -0x1.8p+1 -> -0x1.8p+1 0x1.8p+2", "pass", set()),
    ("upward_mul_num_1 binary64 0x0p+0 0x0p+0 inf -> 0x0p+0 -0x0p+0", "pass", set()),
    ("upward_mul_num_1 binary64 0x0p+0 0x0p+0 nan -> 0x0p+0 0x0p+0", "pass", set()),
    ("upward_mul_num_1 binary64 0x0p+0 0x0p+0 inf -> nan nan", "fail", {"I2"}),
    ("upward_mul_num_1 binary64 0x0p+0 0x0p+0 inf -> inf inf", "fail", {"I4"}),
    ("upward_mul_num_1 binary64 0x1p+1 -0x1p+0 inf -> inf inf", "pass", set()),
    # [0, 1] times t = +inf treated as a point: [0, +inf], not the whole line
    ("upward_mul_num_1 binary64 0x1p+0 -0x0p+0 inf -> inf 0x0p+0", "fail", {"I3", "I4"}),
    ("upward_mul_num_1 binary64 inf inf 0x0p+0 -> 0x0p+0 0x0p+0", "pass", set()),
    ("upward_mul_num_1 binary64 inf inf -0x0p+0 -> -0x0p+0 -0x0p+0", "pass", set()),
    # hull and intersection: [1, 2] and [4, 5]
    ("upward_hull_1 binary64 0x1p+1 -0x1p+0 0x1.4p+2 -0x1p+2 -> 0x1.4p+2 -0x1p+0", "pass", set()),
    ("upward_hull_1 binary64 nan nan 0x1.4p+2 -0x1p+2 -> 0x1.4p+2 -0x1p+2", "pass", set()),
    ("upward_hull_1 binary64 nan nan 0x1.4p+2 -0x1p+2 -> 0x1.4p+2 nan", "fail",
     {"not canonical", "not canonical: one NaN lane"}),
    ("upward_hull_1 binary64 nan nan nan nan -> nan nan", "pass", set()),
    ("upward_intersection_1 binary64 0x1p+1 -0x1p+0 0x1.4p+2 -0x1p+2 -> nan nan", "pass", set()),
    ("upward_intersection_1 binary64 0x1p+1 -0x1p+0 0x1.4p+2 -0x1p+2 -> 0x1p+1 -0x1p+2", "fail",
     {"not canonical", "not canonical: crossed lanes (-nlower > upper)"}),
    ("upward_intersection_1 binary64 0x1p+1 -0x1p+0 0x1.4p+2 -0x1p+2 -> -inf -inf", "fail",
     {"not canonical", "not canonical: a lane -inf"}),
    ("upward_intersection_1 binary64 0x1p+2 -0x1p+0 0x1.4p+2 -0x1p+1 -> 0x1p+2 -0x1p+1", "pass",
     set()),
    ("upward_intersection_1 binary64 0x1p+1 -0x1p+0 0x1.8p+1 -0x1p+1 -> 0x1p+1 -0x1p+1", "pass",
     set()),
    # the constructor, one line per kind of given bounds
    ("upward_make_1 binary64 0x1p+0 0x1p+1 -> 0x1p+1 -0x1p+0", "pass", set()),
    ("upward_make_1 binary64 0x1p+1 0x1p+0 -> nan nan", "pass", set()),
    ("upward_make_1 binary64 0x1p+1 0x1p+0 -> 0x1p+0 -0x1p+1", "fail",
     {"not canonical", "not canonical: crossed lanes (-nlower > upper)"}),
    ("upward_make_1 binary64 nan 0x1p+0 -> inf inf", "pass", set()),
    ("upward_make_1 binary64 inf inf -> inf inf", "pass", set()),
    ("upward_make_1 binary64 -inf -inf -> inf inf", "pass", set()),
    ("upward_make_1 binary64 -inf -inf -> nan nan", "fail", {"not the interval of the given bounds"}),
    ("upward_make_1 binary64 0x1p+0 inf -> inf -0x1p+0", "pass", set()),
    ("upward_make_1 binary64 -inf 0x1p+0 -> 0x1p+0 inf", "pass", set()),
    ("upward_make_1 binary64 inf -inf -> nan nan", "pass", set()),
    ("upward_make_1 binary64 inf -inf -> -inf -inf", "fail",
     {"not canonical", "not canonical: a lane -inf"}),
    ("upward_make_1 binary64 0x0p+0 -0x0p+0 -> -0x0p+0 0x0p+0", "pass", set()),
    # conversions
    ("upward_from_interval_1 binary64 0x1p+0 0x1p+1 -> 0x1p+1 -0x1p+0", "pass", set()),
    ("upward_from_interval_1 binary64 0x1p+0 0x1p+1 -> 0x1p+1 0x1p+0", "fail", {"members"}),
    ("upward_from_interval_1 binary64 inf -inf -> nan nan", "pass", set()),
    ("upward_from_interval_1 binary64 inf -inf -> -inf -inf", "fail",
     {"canonical", "not canonical: a lane -inf"}),
    ("upward_from_interval_1 binary64 -inf inf -> inf inf", "pass", set()),
    ("upward_from_interval_1 binary64 nan 0x1p+0 -> nan nan", "invalid", set()),
    ("upward_to_interval_1 binary64 0x1p+1 -0x1p+0 -> 0x1p+0 0x1p+1", "pass", set()),
    ("upward_to_interval_1 binary64 0x1p+1 -0x1p+0 -> -0x1p+0 0x1p+1", "fail", {"members"}),
    ("upward_to_interval_1 binary64 nan nan -> inf -inf", "pass", set()),
    ("upward_to_interval_1 binary64 nan nan -> nan nan", "fail", {"canonical"}),
    ("upward_to_interval_1 binary64 nan nan -> -inf inf", "fail", {"empty"}),
    ("upward_to_interval_1 binary64 inf inf -> -inf inf", "pass", set()),
    # predicates and comparisons
    ("upward_empty_1 binary64 nan nan -> 1", "pass", set()),
    ("upward_empty_1 binary64 nan nan -> 0", "fail", {"exact"}),
    ("upward_empty_1 binary64 -inf -inf -> 1", "invalid", set()),
    ("upward_entire_1 binary64 inf inf -> 1", "pass", set()),
    ("upward_entire_1 binary64 inf -0x1p+0 -> 1", "fail", {"sound"}),
    ("upward_contains_1 binary64 0x1p+1 -0x1p+0 0x1.8p+0 -> 1", "pass", set()),
    ("upward_contains_1 binary64 0x1p+1 -0x1p+0 0x1p-1 -> 0", "pass", set()),
    ("upward_contains_1 binary64 inf -0x1p+0 inf -> 0", "pass", set()),
    ("upward_contains_1 binary64 inf -0x1p+0 inf -> 1", "fail", {"sound"}),
    ("upward_contains_1 binary64 inf inf nan -> 0", "pass", set()),
    ("upward_contains_1 binary64 0x1p+1 -0x1p+0 0x1p+0 -> 1", "pass", set()),
    ("upward_subset_1 binary64 nan nan 0x1p+0 -0x1p+0 -> 1", "pass", set()),
    ("upward_subset_1 binary64 nan nan 0x1p+0 -0x1p+0 -> 0", "fail", {"exact"}),
    ("upward_subset_1 binary64 0x1p+0 -0x1p+0 nan nan -> 0", "pass", set()),
    ("upward_positive_1 binary64 0x1p+1 -0x1p+0 -> 1", "pass", set()),
    ("upward_positive_1 binary64 0x1p+0 -0x0p+0 -> 0", "pass", set()),
    ("upward_positive_1 binary64 0x1p+0 -0x0p+0 -> 1", "fail", {"sound"}),
    ("upward_negative_1 binary64 -0x1p+0 0x1p+1 -> 1", "pass", set()),
    ("upward_zero_1 binary64 -0x0p+0 0x0p+0 -> 1", "pass", set()),
    ("upward_zero_1 binary64 nan nan -> 0", "pass", set()),
    ("upward_less_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1.8p+1 -> 1 0", "pass", set()),
    ("upward_less_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1.8p+1 -> 0 0", "fail", {"exact"}),
    ("upward_less_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1.8p+1 -> 1 1", "fail", {"both", "no"}),
    ("upward_less_1 binary64 nan nan 0x1p+0 -0x1p+0 -> 0 0", "pass", set()),
    ("upward_less_1 binary64 nan nan 0x1p+0 -0x1p+0 -> 0 1", "fail", {"no"}),
    ("upward_less_1 binary64 0x1p+1 -0x1p+0 0x1.8p+1 -0x1p+1 -> 0 0", "pass", set()),
    ("upward_less_equal_1 binary64 0x1p+1 -0x1p+0 0x1.8p+1 -0x1p+1 -> 1 0", "pass", set()),
    ("upward_less_1 binary64 0x1.8p+1 -0x1p+1 0x1p+1 -0x1p+0 -> 0 1", "pass", set()),
    ("upward_equal_1 binary64 0x1p+0 -0x1p+0 0x1p+0 -0x1p+0 -> 1 0", "pass", set()),
    ("upward_equal_1 binary64 0x1p+0 -0x1p+0 0x1p+1 -0x1p+1 -> 0 1", "pass", set()),
    ("upward_equal_1 binary64 0x1p+1 -0x1p+0 0x1p+1 -0x1p+0 -> 0 0", "pass", set()),
    ("upward_rel_equal_1 binary64 nan nan nan nan -> 1", "pass", set()),
    ("upward_rel_equal_1 binary64 0x1p+1 -0x1p+0 0x1p+1 -0x1p+0 -> 1", "pass", set()),
    ("upward_rel_interior_1 binary64 0x1p+1 -0x1p+0 inf inf -> 1", "pass", set()),
    ("upward_rel_interior_1 binary64 0x1p+1 -0x1p+0 0x1.8p+1 -0x1p+0 -> 0", "pass", set()),
    ("upward_rel_interior_1 binary64 inf -0x1p+0 inf 0x0p+0 -> 1", "pass", set()),
    ("upward_rel_disjoint_1 binary64 0x1p+1 -0x1p+0 0x1p+2 -0x1.8p+1 -> 1", "pass", set()),
    ("upward_rel_disjoint_1 binary64 0x1p+1 -0x1p+0 0x1.8p+1 -0x1p+1 -> 0", "pass", set()),
]


@test
def up_judge(ctx):
    """Each hand-written line judged as worked out by hand from the page: right answers passing
    in every spelling of a zero; each wrong one failing in its statement and no other (one NaN
    lane, a lane -inf, crossed lanes, (-inf, -inf) for the empty set, a lower bound read without
    its negation, a product one step wide below P, t = +inf as a point, 0 * inf); lines outside
    the requirements invalid."""
    lj = LineJudge(claims_up(ctx))
    bad = []
    for line, status, stmts in JUDGE:
        got, fs, why = lj(line)
        if got != status or (status == "fail" and fs != stmts):
            bad.append("%s: %s %s (%s), not %s %s" % (line, got, sorted(fs), "; ".join(why),
                                                       status, sorted(stmts)))
    expect(not bad, "%d of %d lines:\n  %s" % (len(bad), len(JUDGE), "\n  ".join(bad)))
    return "%d lines" % len(JUDGE)


# ---------------------------------------------------------------------------
# The generator

def _parse(fmtname, line):
    toks = line.partition(" -> ")[0].split()
    tag = toks[-1] if toks[-1].startswith("#") else ""
    return [tok_value(t) for t in toks[2:-1]] if tag else [tok_value(t) for t in toks[2:]], tag


def _sets_of(k, kernel, vals):
    """The intervals of a case (EMPTY or (L, U)) and its numbers."""
    names = [n for n, _ in kernel.inputs]
    v = dict(zip(names, vals))
    ivs = [stored_state(v[u], v[n]) for u, n in kernel.upward_requires]
    ivs += [default_state(v[a], v[b]) for a, b in kernel.interval_requires]
    inset = {n for p in list(kernel.upward_requires) + list(kernel.interval_requires) for n in p}
    nums = [v[n] for n in names if n not in inset]
    return ivs, nums


def _bounds(ivs):
    return [b for iv in ivs if iv not in (EMPTY, None) for b in iv if type(b) is not str]


@test
def up_gen(ctx):
    """Case i alone is case i of its run, a seed matters, every case satisfies the requirements
    (the checker finds no invalid line), every stratum of the header has cases, each stratum has
    what it is for, the requirement's reading by the generator and by the checker agree on every
    pair of lanes of three tiny formats, and an enumeration is every canonical state of the
    definition, its restrictions keeping the infinities, NaN and the empty set."""
    cl = claims_up(ctx)
    bad = []
    count = ctx.n(1400, 560)
    for fmtname in ("binary64", "fp:4:-6:1"):
        fmt = F.parse_format(fmtname)
        df = Def(fmtname)
        for k in KERNELS:
            kern = cl.get(k)
            g = G.RandomGen(kern, fmt, "selftest-up")
            lines = list(g.lines(0, count))
            for i in (0, 7, count - 1):
                if g.case(i) != lines[i + 1]:
                    bad.append("%s: case %d alone differs" % (k, i))
            other = list(G.RandomGen(kern, fmt, "another").lines(0, 40))
            if other[1:-1] == lines[1:41]:
                bad.append("%s: the seed does not matter" % k)
            t = totals(judge(run_up(lines), cl), k)
            if t["invalid"] or t["judged"] != count:
                bad.append("%s %s: %s" % (k, fmtname, t))
            by = {}
            for ln in body(lines):
                vals, tag = _parse(fmtname, ln)
                by.setdefault(tag[1:].split(":")[0], []).append(vals)
            sh = g.shape
            for s in sh.strata:
                cases = by.get(s, [])
                if not cases:
                    bad.append("%s %s: no case of %s" % (k, fmtname, s))
                    continue
                share = _stratum_share(df, sh, k, kern, s, cases)
                if share is not None and share < 0.75:
                    bad.append("%s %s: %s has what it is for in %.2f of its cases" % (
                        k, fmtname, s, share))
            zeros = [ln for ln in body(lines) if " 0x0p+0" in ln]
            nzeros = [ln for ln in body(lines) if " -0x0p+0" in ln]
            if not zeros or not nzeros:
                bad.append("%s %s: zeros of one sign only" % (k, fmtname))
    # The requirement: the generator's reading against the checker's, every pair of lanes.
    for fmtname in ("fp:1:0:1", "fp:2:-2:1", "fp:3:-4:1"):
        df = Def(fmtname)
        lanes = [int(v / df.eta) for v in df.numbers()] + [INF, NINF, NAN]
        for u in lanes:
            for n in lanes:
                a = GU._canonical_stored(u, n)
                b = IV.upward_state(u, n) is not None
                c = stored_state(*(Q(v) * df.eta if type(v) is int else v for v in (u, n)))
                if not (a == b == (c is not None)):
                    bad.append("%s: (%s, %s) canonical: generator %s, checker %s, definition %s"
                               % (fmtname, u, n, a, b, c is not None))
    # The enumerations against the definition.
    for fmtname in ("fp:1:0:1", "fp:2:-2:1"):
        df = Def(fmtname)
        lanes = [literal(df, v) for v in df.numbers()] + ["inf", "-inf", "nan"]
        states = sum(1 for u in lanes for n in lanes
                     if stored_state(tok_value(u), tok_value(n)) is not None)
        values = len(df.numbers()) + 3
        defaults = sum(1 for a in lanes for b in lanes
                       if default_state(tok_value(a), tok_value(b)) is not None)
        for k in KERNELS:
            kern = cl.get(k)
            g = G.ExhaustiveGen(kern, F.parse_format(fmtname))
            want = 1
            for _ in kern.upward_requires:
                want *= states
            for _ in kern.interval_requires:
                want *= defaults
            inset = {n for p in kern.upward_requires + kern.interval_requires for n in p}
            for n, _l in kern.inputs:
                if n not in inset:
                    want *= values
            if g.total != want:
                bad.append("%s %s: %d cases enumerated, %d by the definition" % (
                    k, fmtname, g.total, want))
        r = G.ExhaustiveGen(cl.get("upward_neg_1"), F.parse_format(fmtname), ["xu.sign=+"])
        texts = [ln.split()[2:4] for ln in body(r.lines(0, r.total))]
        for need in (["nan", "nan"], ["inf", "inf"]):
            if need not in texts:
                bad.append("%s: a restriction drops %s" % (fmtname, need))
        if any(tok_value(u) not in (INF, NAN) and tok_value(u) < 0 for u, _n in texts):
            bad.append("%s: the restriction xu.sign=+ not applied" % fmtname)
    expect(not bad, "generator:\n  " + "\n  ".join(bad[:12]))
    return "%d kernels in two formats, %d cases each" % (len(KERNELS), count)


def _stratum_share(df, sh, k, kern, s, cases):
    """The share of a stratum's cases that have what the stratum is for, or None for a common
    stratum (judged by the earlier waves' tests)."""
    if s in GU.COMMON:
        return None
    fmt = df.fmt
    om_near = df.value(df.kmax - 2) if df.kmax > 2 else df.omega
    lam = df.value(df.s)
    top = Q(2) ** (fmt.emax - 2)
    P = Q(2) ** (2 * fmt.p - 1) * df.eta
    good = 0
    for vals in cases:
        if k == "upward_make_1":
            lo, hi = vals
            fin = [v for v in vals if type(v) is not str]
            ok = {"nanbound": NAN in vals,
                  "reversed": NAN not in vals and _key(lo) > _key(hi),
                  "infinities": INF in vals or NINF in vals,
                  "point": lo == hi,
                  "zerobound": 0 in fin,
                  "omega": any(abs(v) >= top for v in fin),
                  "subnormal": fmt.p == 1 or all(0 < abs(v) < lam for v in fin)}[s]
            good += ok
            continue
        ivs, nums = _sets_of(k, kern, vals)
        bnds = _bounds(ivs)
        if s == "empty":
            ok = EMPTY in ivs
        elif s == "whole":
            ok = (NINF, INF) in ivs
        elif s == "halfline":
            ok = any(iv not in (EMPTY, None) and (iv[0] == NINF) != (iv[1] == INF) for iv in ivs)
        elif s == "point":
            ok = any(iv not in (EMPTY, None) and iv[0] == iv[1] for iv in ivs)
        elif s == "zerobound":
            ok = 0 in bnds
        elif s == "omega":
            ok = any(abs(b) >= min(top, om_near) for b in bnds)
        elif s == "subnormal":
            ok = fmt.p == 1 or any(0 < abs(b) < lam for b in bnds)
        elif s == "crossnear":
            ok = _crossnear_ok(df, sh, ivs)
        elif s == "zeroinf":
            zero = any(iv not in (EMPTY, None) and 0 in iv for iv in ivs)
            unb = any(iv not in (EMPTY, None) and (iv[0] == NINF or iv[1] == INF) for iv in ivs)
            tinf = any(type(t) is str for t in nums)
            tzero = any(t == 0 for t in nums)
            ok = (zero and (unb or tinf)) or (unb and tzero)
        elif s == "aroundp":
            xs = _bounds(ivs[:1])
            ys = _bounds(ivs[1:]) or [t for t in nums if type(t) is not str]
            ok = any(P / 4 <= abs(a * b) <= 4 * P for a in xs for b in ys)
        elif s == "numspecial":
            t = nums[0]
            ok = type(t) is str or t == 0
            if sh.contains and not ok:
                ok = any(abs(t - b) <= 2 * _gap(df, b) for b in bnds)
        else:
            raise AssertionError("no test of the stratum %s" % s)
        good += ok
    return good / len(cases)


def _gap(df, v):
    s = df.succ(v)
    return (s - v) if type(s) is not str else df.omega


def _crossnear_ok(df, sh, ivs):
    lam = df.value(df.s)
    small = max(4 * lam, 8 * df.eta)
    if len(ivs) == 1:
        iv = ivs[0]
        return iv not in (EMPTY, None) and iv[0] <= 0 <= iv[1] and -small <= iv[0] and iv[1] <= small
    x, y = ivs
    if EMPTY in (x, y) or None in (x, y):
        return False
    if sh.op in ("+", "-"):
        (a, b), (c, d) = x, y
        pairs = [(b, d), (a, c)] if sh.op == "+" else [(b, -c), (-a, d)]
        for p, q in pairs:
            if type(p) is str or type(q) is str:
                continue
            if abs(p + q) <= 2 * max(_gap(df, abs(p)), _gap(df, abs(q))):
                return True
        return False
    bnds = [b for iv in (x, y) for b in iv]
    return all(type(b) is not str and abs(b) <= small for b in bnds)


@test
def up_merging(ctx):
    """The merge of the summaries of two halves of streams of six kernels of the round-up interval
    is the summary of the whole."""
    cl = claims_up(ctx)
    ks = ("upward_add_1", "upward_mul_num_1", "upward_intersection_1", "upward_make_1",
          "upward_to_interval_1", "upward_less_1")
    for k in ks:
        lines = body(run_up(stream_up(ctx, k, "binary64", ctx.n(600, 200))))
        whole = judge(lines, cl)
        a = judge(lines[:len(lines) // 2], cl)
        b = judge(lines[len(lines) // 2:], cl)
        m = C.Summary()
        m.merge(a)
        m.merge(b)
        expect(json.dumps(m.to_json()["keys"], sort_keys=True)
               == json.dumps(whole.to_json()["keys"], sort_keys=True), "%s: merge differs" % k)
    return "%d kernels" % len(ks)
