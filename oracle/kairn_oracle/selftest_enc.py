"""The oracle's own tests for the enclosure interface's predicates, comparisons, set operations of a
ball and conversions of two limbs (architecture.md, "Claims of the enclosure interface: predicates
and comparisons", "... the set operations of a ball", "... the conversions of two limbs"): the kinds
certain, trit, ball_set and ball_splits (enclosure.py), and the fields finite_when of
ball_of_interval, the outward tightness and bounded_when of interval_of_ball with bounds of two
limbs, and rel, abs and smallest_radius of makes_ball from an interval (intervals.py).

As for the earlier waves, each test compares the oracle with something it does not share code
with: the relations against a brute-force reading of their definitions on sets of rationals; the
reference runner, written from the listings of gen/kernels/, on random streams and on every case of
tiny formats; planted faults that must be caught in the entry where they belong, in no kernel that
does not use them, and on every line they are about; hand-written lines whose verdicts are worked
out by hand, one per cell of the tables of architecture.md.  The fixture,
oracle/selftest/claims-enclosure.json, holds the 53 kernels, ball_from_interval_2 (judged in full
beside ball_from_interval_1) and add_2_2, whose bounds the constants of ball_to_interval_2 name,
frozen from the claims of 2026-11-21.
"""

import concurrent.futures as cf
import copy
import json
import os
from fractions import Fraction as Q

from . import check as C
from . import enclosure as EN
from . import fmt as F
from . import gen as G
from . import intervals as IV
from . import refrun
from .claims import Claims, load_claims
from .selftest import test, expect, judge, totals, ORACLE_DIR

FIXTURE = os.path.join(ORACLE_DIR, "selftest", "claims-enclosure.json")
IV_PRED = ("interval_empty_1", "interval_entire_1", "interval_contains_1", "interval_subset_1",
           "interval_positive_1", "interval_negative_1", "interval_zero_1", "interval_less_1",
           "interval_less_equal_1", "interval_equal_1", "interval_rel_equal_1",
           "interval_rel_interior_1", "interval_rel_disjoint_1", "interval_empty_2",
           "interval_entire_2", "interval_contains_2", "interval_subset_2", "interval_positive_2",
           "interval_negative_2", "interval_zero_2", "interval_less_2", "interval_less_equal_2",
           "interval_equal_2", "interval_rel_equal_2", "interval_rel_interior_2",
           "interval_rel_disjoint_2")
BALL_PRED_1 = ("ball_contains_point_1", "ball_contains_ball_1", "ball_positive_1",
               "ball_negative_1", "ball_zero_1", "ball_less_1", "ball_less_equal_1",
               "ball_equal_1")
BALL_PRED_2 = ("ball_contains_point_2", "ball_contains_ball_2", "ball_positive_2",
               "ball_negative_2", "ball_zero_2", "ball_less_2", "ball_less_equal_2",
               "ball_equal_2")
BALL_SETS = ("ball_hull_1", "ball_intersection_1", "ball_split_1", "ball_split_2", "ball_hull_2",
             "ball_intersection_2")
CONVERSIONS = ("interval_mid_rad_2", "interval_to_ball_2", "interval_split_2",
               "ball_to_interval_2", "ball_from_interval_1")
FAMILY = IV_PRED + BALL_PRED_1 + BALL_PRED_2 + BALL_SETS + CONVERSIONS
KERNELS = FAMILY + ("ball_from_interval_2",)
# The kernels whose claim fixes every output (exact, or every operand special): a planted fault
# that changes an output of theirs is wrong on that line.
EXACT = IV_PRED + ("ball_contains_point_1", "ball_contains_ball_1", "ball_positive_1",
                   "ball_negative_1", "ball_zero_1", "ball_positive_2", "ball_negative_2",
                   "ball_zero_2")
FORMATS = ("binary64", "binary32", "fp:4:-6:1")
TINY = {1: "fp:2:-2:1", 2: "fp:2:-2:1", 3: "fp:3:-2:-1"}
LOGICAL = ("certain", "trit")


def claims_enc(ctx):
    if not hasattr(ctx, "claims_enc"):
        ctx.claims_enc = load_claims(FIXTURE)
    return ctx.claims_enc


def raw_enc():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def run_enc(lines, variant="correct"):
    r = refrun.Runner(variant)
    out = []
    for ln in lines:
        out.extend(r.complete(ln))
    return out


def stream_enc(ctx, kernel, fmtname, count, strata=None, seed="selftest-enc"):
    key = ("enc", kernel, fmtname, count, strata, seed)
    s = ctx._streams.get(key)
    if s is None:
        g = G.RandomGen(claims_enc(ctx).get(kernel), F.parse_format(fmtname), seed,
                        strata.split(",") if strata else None)
        s = ctx._streams[key] = list(g.lines(0, count))
    return s


def entry_stats(summary, name):
    """{label: [kind, applicable, failures, counts, maxima]} of a kernel, summed over its keys."""
    out = {}
    for (k, _f, _t), st in summary.keys.items():
        if k != name:
            continue
        for e in st.entries:
            d = out.setdefault(e.label, [e.kind, 0, 0, {}, {}])
            d[1] += e.applicable
            d[2] += e.failures
            for c, n in e.counts.items():
                d[3][c] = d[3].get(c, 0) + n
            for c, (r, _l) in e.maxima.items():
                if r[1] and (c not in d[4] or Q(*r) > d[4][c]):
                    d[4][c] = Q(*r)
    return out


def failed_statements(summary, kernel):
    """The statements that failed (the names counted as failed STATEMENT or failed: STATEMENT)."""
    out = set()
    for _kind, _app, fails, counts, _m in entry_stats(summary, kernel).values():
        if fails:
            for c in counts:
                if c.startswith("failed "):
                    out.add(c[len("failed "):])
                elif c.startswith("failed: "):
                    out.add(c[len("failed: "):])
    return out


def failing_kinds(summary, name):
    return {d[0] for d in entry_stats(summary, name).values() if d[2]}


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

    return [
        # certain and trit
        ("interval_subset_1", setf("weight", 1), "unknown fields ['weight']"),
        ("interval_subset_1", delf("rel"), "missing rel"),
        ("interval_subset_1", setf("rel", "below"), "rel must be"),
        ("interval_less_1", setf("rel", "subset"), "rel must be"),
        ("interval_subset_1", setf("args", ["x"]), "takes 2 arguments"),
        ("interval_empty_1", setf("args", ["x", "x"]), "takes 1 argument"),
        ("interval_subset_1", setf("args", ["x", "z"]), "must be a set of the entry"),
        ("interval_subset_1", setf("args", ["x", "x"]), "names the same set twice"),
        ("interval_positive_1", setf("args", ["0", "0"]), "one argument of lt must be a set"),
        ("interval_positive_1", setf("args", ["1", "x"]), "a set of the entry or the integer 0"),
        ("interval_positive_1", setf("args", [False, "x"]), "a set of the entry or the integer 0"),
        ("interval_subset_1", setf("balls", {"b": {"center": "xl", "radius": "xu"}}),
         "intervals or by balls"),
        ("interval_subset_1", delf("intervals"), "intervals or by balls"),
        ("interval_subset_1", setf("intervals", {"x": {"lower": "xl", "upper": "xu"}}),
         "must be a set of the entry"),
        ("interval_empty_1", setf("intervals", {"x": {"lower": "xl", "upper": "xu"},
                                                 "y": {"lower": "xu", "upper": "xl"}}),
         "is not an interval() requirement"),
        ("interval_subset_1", ens(lambda e: (e.__setitem__("rel", "empty"),
                                              e.__setitem__("args", ["x"]))),
         "the set y is named but is not an argument"),
        ("interval_empty_1", lambda k: (k["outputs"].append({"name": "z", "limbs": 1}),
                                        k["ensures"][0].__setitem__("of", "z")),
         "of must name a mask output"),
        ("interval_subset_1", setf("exact", False), "exact is written only when it is true"),
        ("ball_less_1", setf("exact", True), "exact and exact_when together"),
        ("ball_less_1", setf("exact_when", []), "exact_when must be a nonempty list"),
        ("ball_less_1", setf("exact_when", [{"abs_le": "rx+ry", "omega": False}]),
         "must be {\"abs_le\": EXPR, \"omega\": true}"),
        ("ball_less_1", setf("exact_when", [{"abs_le": "rx+ry", "exp": 0}]),
         "must be {\"abs_le\": EXPR, \"omega\": true}"),
        ("ball_less_1", setf("exact_when", [{"abs_le": "rx+rz", "omega": True}]),
         "'rz' is not a limb input"),
        ("ball_less_1", setf("exact_when", [{"abs_le": "rx+", "omega": True}]), "exact_when[0]"),
        ("interval_empty_1", setf("of", "xl"), "of must name a mask output"),
        ("interval_less_1", setf("no", "yes"), "yes and no must be two mask outputs"),
        ("interval_less_1", delf("no"), "missing no"),
        ("interval_contains_1", setf("args", ["xl", "x"]), "the point of member must be"),
        ("interval_contains_1", setf("args", ["t", "t"]), "the second argument of member"),
        ("interval_contains_2", lambda k: k["requires"].remove("canonical(t)"),
         "required canonical()"),
        ("interval_empty_1", lambda k: k.pop("domain"), "belongs to the extended domain"),
        ("ball_positive_1", setf("balls", {"x": {"center": "r", "radius": "c"}}),
         "has no requirement ball(r, c)"),
        # ball_set
        ("ball_hull_1", setf("set", "sum"), "set must be union or intersection"),
        ("ball_hull_1", setf("balls", {"x": {"center": "cx", "radius": "rx"}}),
         "ball_set takes two balls"),
        ("ball_hull_1", setf("radius", "cz"), "the radius must be another output"),
        ("ball_hull_1", setf("center", "cx"), "is not a limb output"),
        ("ball_hull_1", setf("extra", 1), "unknown fields ['extra']"),
        ("ball_hull_1", delf("balls"), "missing balls"),
        ("ball_hull_2", lambda k: (k["outputs"].__setitem__(0, {"name": "cz", "limbs": 1})),
         "the center of"),
        # ball_splits
        ("ball_split_1", setf("parts", [{"center": "ca", "radius": "ra"}]),
         "parts must be a list of two balls"),
        ("ball_split_1", setf("parts", [{"center": "ca", "radius": "ra"},
                                        {"center": "ca", "radius": "rb"}]),
         "is named twice"),
        ("ball_split_1", setf("parts", [{"center": "ca", "radius": "ra"}, {"lower": "cb"}]),
         "part 1 must be"),
        ("ball_split_1", setf("from", {"center": "r", "radius": "c"}), "has no requirement"),
        ("ball_split_2", setf("parts", [{"center": "ra", "radius": "ra"},
                                        {"center": "cb", "radius": "rb"}]),
         "must have the limbs of the ball's center"),
        # finite_when of ball_of_interval
        ("interval_mid_rad_2", setf("finite_when", []), "finite_when must be a nonempty list"),
        ("interval_mid_rad_2", setf("finite_when", {"abs_le": "xl", "exp": -2}),
         "finite_when must be a nonempty list"),
        ("interval_mid_rad_2", setf("finite_when", [{"abs_le": "m", "exp": -2}]),
         "finite_when[0] must be"),
        ("interval_mid_rad_2", setf("finite_when", [{"abs_le": "xl", "exp": "-2"}]),
         "finite_when[0] must be"),
        ("interval_mid_rad_2", setf("finite_when", [{"abs_le": "xl", "exp": True}]),
         "finite_when[0] must be"),
        ("interval_mid_rad_2", setf("finite_when", [{"abs_le": "xl", "omega": True}]),
         "finite_when[0] must be"),
        ("interval_mid_rad_2", setf("smallest_radius", True), "finite_when and smallest_radius"),
        # interval_of_ball of two limbs
        ("ball_to_interval_2", setf("tight", {"kind": "rounded"}), "tight of bounds of two limbs"),
        ("ball_to_interval_2", ens(lambda e: e["tight"].__setitem__("steps", 1)),
         "tight: unknown fields ['steps']"),
        ("ball_to_interval_2", ens(lambda e: e["tight"].pop("abs")), "missing abs"),
        ("ball_to_interval_2", ens(lambda e: e["tight"].__setitem__("exact_when", [])),
         "exact_when must be"),
        ("ball_to_interval_2", setf("bounded_when", []), "bounded_when must be a nonempty list"),
        ("ball_to_interval_2", setf("bounded_when", [{"abs_le": "x+x", "exp": -2}]),
         "bounded_when[0] must be"),
        ("ball_to_interval_2", setf("bounded_when", [{"abs_le": "x", "omega": True}]),
         "bounded_when[0] must be"),
        ("ball_to_interval_2", setf("bounded_when", [{"abs_le": "x", "exp": 1.5}]),
         "bounded_when[0] must be"),
        # makes_ball from an interval
        ("ball_from_interval_1", delf("abs"), "rel and abs come together"),
        ("ball_from_interval_1", ens(lambda e: (e.pop("rel"), e.pop("abs"))),
         "smallest_radius only with rel and abs"),
        ("ball_from_interval_1", setf("smallest_radius", False), "smallest_radius is written only"),
        ("ball_from_interval_1", setf("rel", "u+"), "ball_from_interval_1"),
    ]


@test
def claims_reading_enc(ctx):
    """The fixture of the enclosure interface reads whole, its kinds and fields as architecture.md
    writes them; malformed kernels are set aside with a reason that names the kernel, the entry and
    the field, without making the others unreadable; the new fields of the kinds that exist are
    refused where they do not belong."""
    cl = claims_enc(ctx)
    expect(not cl.broken, "the fixture does not read: %s" % cl.broken)
    for k in FAMILY:
        expect(cl.get(k) is not None, "%s is not in the fixture" % k)
    e = cl.get("ball_less_1").ensures[0]
    expect(e.kind == "trit" and e.rel == "lt" and e.args == ["x", "y"] and not e.exact
           and [t for _tr, t in e.exact_when_abs] == ["rx+ry"],
           "ball_less_1 read otherwise: %s" % e.label)
    e = cl.get("interval_contains_2").ensures[0]
    expect(e.kind == "certain" and e.point == "t" and e.exact and e.over == "intervals",
           "interval_contains_2 read otherwise: %s" % e.label)
    e = cl.get("interval_positive_1").ensures[0]
    expect(e.args == ["0", "x"], "the integer 0 read otherwise: %s" % e.args)
    e = cl.get("ball_hull_2").ensures[0]
    expect(e.kind == "ball_set" and e.op == "union", "ball_hull_2: %s" % e.label)
    e = cl.get("interval_mid_rad_2").ensures[0]
    expect(e.radius_finite_when == [("xl", -2), ("xu", -2)], "finite_when read otherwise")
    e = cl.get("ball_to_interval_2").ensures[0]
    expect(e.two and e.bounded_when == [("exp", -2)] and set(e.tight_exact) == {"lower", "upper"},
           "ball_to_interval_2 read otherwise: %s" % e.label)
    e = cl.get("ball_from_interval_1").ensures[0]
    expect(e.mid_consts and e.smallest_radius and not e.midpoint_when,
           "ball_from_interval_1 read otherwise: %s" % e.label)
    raw = raw_enc()
    by = {k["name"]: k for k in raw["kernels"]}
    n = 0
    for name, change, why in _malformed():
        data = copy.deepcopy(raw)
        k = next(x for x in data["kernels"] if x["name"] == name)
        change(k)
        c = Claims(data, "<malformed>")
        expect(name in c.broken, "%s (%s) was not set aside" % (name, why))
        msg = c.broken[name]
        expect(why in msg and name in msg, "%s: the reason %r does not say %r" % (name, msg, why))
        if "ensures entry" in msg:
            expect("ensures entry 0 (%s)" % by[name]["ensures"][0]["kind"] in msg,
                   "%s: the reason does not name the entry: %r" % (name, msg))
        others = sorted(set(c.broken) - {name})
        expect(not others, "%s made %s unreadable too" % (name, others))
        n += 1
    # The fields new to makes_ball are refused on a ball from a center and a radius.
    data = {"schema": 1, "kernels": [{
        "name": "ball_make_1", "domain": "extended", "inputs": [
            {"name": "c", "limbs": 1}, {"name": "r", "limbs": 1}],
        "outputs": [{"name": "cw", "limbs": 1}, {"name": "rw", "limbs": 1}], "requires": [],
        "ensures": [{"kind": "makes_ball", "center": "cw", "radius": "rw",
                     "from": {"center": "c", "radius": "r"}, "rel": "u", "abs": "eta"}],
        "min_precision": 1}]}
    c = Claims(data, "<makes_ball>")
    expect("ball_make_1" in c.broken and "rel, abs and smallest_radius" in c.broken["ball_make_1"],
           "rel and abs on a ball from a center: %s" % c.broken)
    # The kinds of the enclosure interface belong to the extended domain.
    data = copy.deepcopy(raw)
    k = next(x for x in data["kernels"] if x["name"] == "ball_hull_1")
    k.pop("domain")
    k["requires"] = []
    c = Claims(data, "<finite>")
    expect("ball_hull_1" in c.broken, "ball_set in the finite domain was read")
    return "%d malformed kernels set aside, %d kernels read" % (n + 2, len(cl.kernels))


# ---------------------------------------------------------------------------
# The relations, against their definitions on sets of rationals

def _members(s, pts):
    """The candidate points of pts that are members of the set s (None: empty; (lo, hi) with lo or
    hi None for an infinite end)."""
    if s is None:
        return []
    lo, hi = s
    return [p for p in pts if (lo is None or lo <= p) and (hi is None or p <= hi)]


def _brute(rel, sets, point, pts, delta):
    """(R, N) of a relation from its definition, the quantifiers over the candidate points: the
    bounds, the points between them, and points beyond every bound (enough for sets of real numbers
    that are closed intervals: an extremum is a bound or no member)."""
    ms = [_members(s, pts) for s in sets]
    if rel in ("lt", "le", "eq"):
        if any(not m for m in ms) or any(s is None for s in sets):
            return False, False
        op = {"lt": lambda a, b: a < b, "le": lambda a, b: a <= b, "eq": lambda a, b: a == b}[rel]
        A, B = ms
        r = all(op(a, b) for a in A for b in B)
        n = all(not op(a, b) for a in A for b in B)
        return r, n
    if rel == "member":
        r = point is not None and point in _members(sets[0], [point])
        return r, not r
    if rel == "empty":
        return sets[0] is None, None
    if rel == "entire":
        return sets[0] is not None and sets[0] == (None, None), None
    X_, Y_ = ms
    inY = set(Y_)
    if rel == "subset":
        return all(p in inY for p in X_), None
    if rel == "equal":
        return set(X_) == inY, None
    if rel == "disjoint":
        return not (set(X_) & inY), None
    # interior: a neighbourhood of every member: x - delta and x + delta members of Y.
    def mem(p):
        return bool(_members(sets[1], [p]))
    return all(mem(p - delta) and mem(p + delta) for p in X_), None


def _as_set(s):
    """The set of the brute force as the oracle writes it: EMPTY or ("nonempty", L, U)."""
    if s is None:
        return EN.EMPTY
    lo, hi = s
    return ("nonempty", F.NEG_INF if lo is None else lo, F.POS_INF if hi is None else hi)


@test
def enc_relations(ctx):
    """enclosure.relation, the judges' reading of every relation, against the definitions of
    architecture.md's table of rel quantified over the members of the sets: every pair of sets of
    bounds among -inf, -2..2 and +inf and the empty set, every relation, and for member every point
    of -3..3, an infinity and a NaN."""
    vals = [None] + list(range(-2, 3)) + ["+"]
    sets = [None]
    for lo in vals[:-1]:
        for hi in vals[1:]:
            a = -10 ** 9 if lo is None else lo
            b = 10 ** 9 if hi == "+" else hi
            if lo is None or hi == "+" or a <= b:
                sets.append((lo, None if hi == "+" else hi))
    sets = [s for s in sets if s is None or s[0] is not None or True]
    pts = [Q(n, 2) for n in range(-12, 13)]
    delta = Q(1, 4)
    n = 0
    for rel in ("lt", "le", "eq", "subset", "equal", "interior", "disjoint"):
        for A in sets:
            for B in sets:
                want = _brute(rel, [A, B], None, pts, delta)
                got = EN.relation(rel, [_as_set(A), _as_set(B)])
                expect(got == want, "%s(%s, %s): %s, by the definition %s" % (rel, A, B, got,
                                                                              want))
                n += 1
    for rel in ("empty", "entire"):
        for A in sets:
            got = EN.relation(rel, [_as_set(A)])
            expect(got == _brute(rel, [A], None, pts, delta), "%s(%s): %s" % (rel, A, got))
            n += 1
    for A in sets:
        for t in list(range(-3, 4)) + [F.POS_INF, F.NEG_INF, F.NAN]:
            want = _brute("member", [A], t if type(t) is int else None, pts, delta)
            got = EN.relation("member", [t, _as_set(A)])
            expect(got == want, "member(%s, %s): %s, by the definition %s" % (t, A, got, want))
            n += 1
    # A "0" argument is the set {0}.
    for A in sets:
        for rel in ("lt", "le", "eq"):
            got = EN.relation(rel, [("nonempty", 0, 0), _as_set(A)])
            expect(got == _brute(rel, [(0, 0), A], None, pts, delta), "%s(0, %s)" % (rel, A))
            n += 1
    return "%d relations of %d sets" % (n, len(sets))


# ---------------------------------------------------------------------------
# The reference runner on random streams and on enumerations

def _ref_one(args):
    kernel, fmtname, count = args
    claims = load_claims(FIXTURE)
    g = G.RandomGen(claims.get(kernel), F.parse_format(fmtname), "selftest-enc")
    lines = list(g.lines(0, count))
    s = judge(run_enc(lines), claims)
    tags = {t for (_k, _f, t) in s.keys}
    return kernel, fmtname, totals(s), entry_stats(s, kernel), sorted(tags), g.strata


# The classes the streams of binary64 and binary32 must reach, per kernel family: a selection of
# what the cross-checks' guards ask for (tests/crosscheck_guards.py).
def _needs(kernel, e):
    if e.kind in LOGICAL:
        want = [EN.HOLDS]
        if e.kind == "trit":
            want += [EN.FAILS_ALL, EN.ANS_YES, EN.ANS_NO]
            # member fails for every choice exactly when it does not hold.
            if e.rel != "member":
                want += [EN.NEITHER, EN.ANS_UNKNOWN]
        else:
            want += [EN.NOT_HOLDS, EN.MASK_TRUE, EN.MASK_FALSE]
        for n in e.sets:
            want += [EN.CLASS % (n, c) for c in ("empty", "whole line")]
        if e.point:
            want += [EN.CLASS % (e.point, c) for c in EN.POINT_CLASSES]
        if e.exact_when_abs:
            want += [EN.EW_HOLDS] + [EN.EW_FAILS + "|%s| <= Omega" % t for _tr, t in e.exact_when_abs]
        return want
    if e.kind == "ball_set":
        return list(EN.SET_PAIRS) + [EN.SET_Y_AS_IS, EN.SET_X_AS_IS, EN.SET_ZERO_SIGNS,
                                     EN.SET_DISJOINT, EN.SET_OVERLAP, EN.SET_NESTED]
    if e.kind == "ball_splits":
        return [EN.SPLIT_X % s for s in ("empty", "whole line", "finite")] + [EN.SPLIT_ZERO]
    if e.kind == "ball_of_interval" and e.radius_finite_when:
        return [IV.FW_HOLDS, IV.X_BOUNDED, IV.X_EMPTY, IV.X_WHOLE, IV.X_ABOVE, IV.X_BELOW] + [
            IV.FW_FAILS + "|%s| <= 2^(qmax+p%+d)" % (n, x) for n, x in e.radius_finite_when]
    if e.kind == "interval_of_ball" and e.two:
        return [IV.BALL_EMPTY, IV.BALL_WHOLE, IV.BALL_FINITE, IV.SIDE_EW_HOLDS % "lower",
                IV.SIDE_EW_HOLDS % "upper", IV.I5_HOLDS, IV.I5_FAILS]
    if e.kind == "makes_ball":
        return list(IV.MAKE_CELLS) + ([IV.MID_EXACT, IV.MID_INEXACT] if e.mid_consts else [])
    if e.kind == "splits":
        return [IV.X_EMPTY, IV.X_WHOLE, IV.X_ABOVE, IV.X_BELOW, IV.X_BOUNDED]
    return []


@test
def enc_reference(ctx):
    """The reference runner (the listings of gen/kernels/) on random streams of every kernel of the
    family in binary64, binary32 and a toy format: no failure, no invalid case, nothing
    suspicious, a case of every stratum the generator lists, every entry applied; in binary64 and
    binary32 the classes the guards ask for reached."""
    cl = claims_enc(ctx)
    n = ctx.n(1500, 500)
    tasks = [(k, f, n) for k in KERNELS for f in FORMATS]
    with cf.ProcessPoolExecutor(ctx.jobs) as ex:
        results = list(ex.map(_ref_one, tasks))
    missing = []
    for kernel, fname, t, ents, tags, strata in results:
        expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0,
               "%s %s: %s" % (kernel, fname, t))
        expect(t["judged"] == t["cases"] == n, "%s %s: %s" % (kernel, fname, t))
        expect(sorted(strata) == tags, "%s %s: strata %s, tags %s" % (kernel, fname, strata, tags))
        for label, (_kind, app, _f, _c, _m) in ents.items():
            expect(app > 0, "%s %s: %s applied to nothing" % (kernel, fname, label))
        if fname == "fp:4:-6:1":
            continue
        e = cl.get(kernel).ensures[0]
        counts = next(iter(ents.values()))[3]
        for c in _needs(kernel, e):
            if not counts.get(c):
                missing.append("%s %s: %s" % (kernel, fname, c))
    expect(not missing, "classes never reached: %s" % "; ".join(missing[:12]))
    return "%d streams of %d cases" % (len(tasks), n)


def _enum_one(args):
    kernel, fmtname, restrict, variant = args
    claims = load_claims(FIXTURE)
    g = G.ExhaustiveGen(claims.get(kernel), F.parse_format(fmtname), restrict)
    lines = list(g.lines(0, g.total))
    s = judge(run_enc(lines, variant), claims)
    differs = None
    if variant != "correct":
        good = run_enc(lines)
        bad = run_enc(lines, variant)
        changed = [b for a, b in zip(good, bad) if a != b and not a.startswith("#")]
        differs = (len(changed), totals(judge(changed, claims))["failed"])
    counts = {}
    for d in entry_stats(s, kernel).values():
        for c, m in d[3].items():
            counts[c] = counts.get(c, 0) + m
    return kernel, variant, g.total, totals(s), failing_kinds(s, kernel), counts, differs


ENUM_RESTRICT = {
    # Two intervals of two limbs: their bounds' leading limbs in a few values.
    2: ("xl.in=0x0p+0/0x1p+0/-0x1p-1", "xu.in=0x0p+0/0x1p+0/0x1.8p+0"),
}
ENUM_FAULTS = {"en-empty-whole": "interval_empty_1", "en-contains-inf": "interval_contains_1",
               "en-subset-strict": "interval_subset_1", "en-less-no-empty": "interval_less_1",
               "en-equal-yes-ends": "interval_equal_1", "en-interior-no-inf":
               "interval_rel_interior_1", "en-disjoint-no-empty": "interval_rel_disjoint_1",
               "enb-point-lt": "ball_contains_point_1", "enb-ball-no-empty": "ball_contains_ball_1",
               "enb-less-touch": "ball_less_1", "enb-equal-no-le": "ball_equal_1",
               "ens-hull-no-y": "ball_hull_1", "ens-int-empty-none": "ball_intersection_1",
               "ens-split-empty-whole": "ball_split_1",
               "enc-fromint1-inf-empty": "ball_from_interval_1",
               "en2-lead-only": "interval_less_2"}


def _enum_tasks(cl, quick):
    tasks = []
    for k in KERNELS:
        kern = cl.get(k)
        p = max(kern.min_precision, 1)
        two_ivs = len(kern.interval_requires) == 2 and kern.limbs_of(kern.interval_requires[0][0]) == 2
        restrict = ()
        if two_ivs:
            restrict = ENUM_RESTRICT[2]
        elif kern.ball_requires and len(kern.ball_requires) == 2 and p >= 3:
            restrict = ("rx.in=0x0p+0/0x1p-1/0x1p+0", "ry.in=0x0p+0/0x1p-1/0x1p+0")
            if quick:
                restrict += ("cx.lead=-1:0",)
        tasks.append((k, TINY[min(p, 3)], restrict, "correct"))
    return tasks


@test
def enc_exhaustive(ctx):
    """The reference runner on every case of tiny formats for every kernel of the family (two
    intervals of two limbs and two balls of two limbs on a restricted domain): no failure, invalid
    or suspicious case, every line judged; the cells of the table of the constructors met by
    ball_from_interval_1; and planted faults caught there, in their entries only, on every line of
    a kernel whose claim fixes its output where the fault changes it."""
    cl = claims_enc(ctx)
    tasks = _enum_tasks(cl, ctx.quick)
    for v, k in ENUM_FAULTS.items():
        p = max(cl.get(k).min_precision, 1)
        two = k.endswith("_2") and k.startswith("interval") and len(cl.get(k).interval_requires) == 2
        tasks.append((k, TINY[min(p, 3)], ENUM_RESTRICT[2] if two else (), v))
    with cf.ProcessPoolExecutor(ctx.jobs) as ex:
        results = list(ex.map(_enum_one, tasks))
    cases = 0
    for kernel, variant, total, t, kinds, counts, differs in results:
        cases += total
        if variant == "correct":
            expect(t["failed"] == 0 and t["invalid"] == 0 and t["suspicious"] == 0,
                   "%s: %s" % (kernel, t))
            expect(t["judged"] == t["cases"] == total > 0, "%s: %d of %d judged" % (
                kernel, t["judged"], total))
            if kernel in ("ball_from_interval_1", "ball_from_interval_2"):
                missing = [c for c in IV.MAKE_CELLS if not counts.get(c)]
                expect(not missing, "%s: never %s" % (kernel, missing))
        else:
            allowed = PLANTED[variant][0][kernel]
            expect(t["failed"] > 0 and kinds <= allowed,
                   "%s on %s: failed %d, in %s" % (variant, kernel, t["failed"], kinds))
            if kernel in EXACT:
                expect(differs[0] > 0 and differs[1] == differs[0],
                       "%s on %s: %d of the %d lines it changes failed" % (
                           variant, kernel, differs[1], differs[0]))
    return "%d enumerations, %d cases" % (len(results), cases)


# ---------------------------------------------------------------------------
# Planted faults

ALL_FMT = FORMATS
B2 = ("binary64", "binary32")
_IV1 = {k: {"certain", "trit"} for k in IV_PRED}
PLANTED = {
    "en-empty-whole": ({"interval_empty_1": {"certain"}, "interval_empty_2": {"certain"}}, ALL_FMT),
    "en-entire-lower": ({"interval_entire_1": {"certain"}, "interval_entire_2": {"certain"}},
                        ALL_FMT),
    "en-contains-inf": ({"interval_contains_1": {"certain"}, "interval_contains_2": {"certain"}},
                        ALL_FMT),
    "en-subset-strict": ({"interval_subset_1": {"certain"}, "interval_subset_2": {"certain"}},
                         ALL_FMT),
    "en-positive-le": ({"interval_positive_1": {"certain"}, "interval_positive_2": {"certain"}},
                       ALL_FMT),
    "en-negative-empty": ({"interval_negative_1": {"certain"},
                           "interval_negative_2": {"certain"}}, ALL_FMT),
    "en-zero-lower": ({"interval_zero_1": {"certain"}, "interval_zero_2": {"certain"}}, ALL_FMT),
    "en-less-no-empty": ({"interval_less_1": {"trit"}, "interval_less_2": {"trit"}}, ALL_FMT),
    "en-less-touch": ({"interval_less_1": {"trit"}, "interval_less_2": {"trit"}}, ALL_FMT),
    "en-le-no-strict": ({"interval_less_equal_1": {"trit"}, "interval_less_equal_2": {"trit"}},
                        ALL_FMT),
    "en-equal-yes-ends": ({"interval_equal_1": {"trit"}, "interval_equal_2": {"trit"}}, ALL_FMT),
    "en-equal-no-touch": ({"interval_equal_1": {"trit"}, "interval_equal_2": {"trit"}}, ALL_FMT),
    "en-trit-unknown-no": ({"interval_less_1": {"trit"}, "interval_less_2": {"trit"}}, ALL_FMT),
    "en-trit-both": ({"interval_equal_1": {"trit"}, "interval_equal_2": {"trit"}}, ALL_FMT),
    "en-releq-lower": ({"interval_rel_equal_1": {"certain"}, "interval_rel_equal_2": {"certain"}},
                       ALL_FMT),
    "en-interior-closed": ({"interval_rel_interior_1": {"certain"},
                            "interval_rel_interior_2": {"certain"}}, ALL_FMT),
    "en-interior-no-inf": ({"interval_rel_interior_1": {"certain"},
                            "interval_rel_interior_2": {"certain"}}, ALL_FMT),
    "en-disjoint-no-empty": ({"interval_rel_disjoint_1": {"certain"},
                              "interval_rel_disjoint_2": {"certain"}}, ALL_FMT),
    "en-disjoint-touch": ({"interval_rel_disjoint_1": {"certain"},
                           "interval_rel_disjoint_2": {"certain"}}, ALL_FMT),
    "en2-lead-only": ({k: {"certain", "trit"} for k in IV_PRED if k.endswith("_2")
                       and k not in ("interval_empty_2", "interval_entire_2", "interval_positive_2",
                                     "interval_negative_2", "interval_zero_2")}, ALL_FMT),
    "enb-point-lt": ({"ball_contains_point_1": {"certain"}}, ALL_FMT),
    "enb-point-inf-whole": ({"ball_contains_point_1": {"certain"},
                             "ball_contains_point_2": {"trit"}}, ALL_FMT),
    # (Of two limbs the test of X the whole line changes nothing: radd(hi, ry) <= +inf holds, and
    # an empty Y has its own test.)
    "enb-ball-no-whole": ({"ball_contains_ball_1": {"certain"}}, ALL_FMT),
    "enb-ball-no-empty": ({"ball_contains_ball_1": {"certain"},
                           "ball_contains_ball_2": {"certain"}}, ALL_FMT),
    "enb-ball-strict": ({"ball_contains_ball_1": {"certain"}}, ALL_FMT),
    "enb-positive-le": ({"ball_positive_1": {"certain"}, "ball_positive_2": {"certain"}}, ALL_FMT),
    "enb-negative-sign": ({"ball_negative_1": {"certain"}}, ALL_FMT),
    "enb-zero-radius": ({"ball_zero_1": {"certain"}, "ball_zero_2": {"certain"}}, ALL_FMT),
    "enb-less-touch": ({"ball_less_1": {"trit"}}, ALL_FMT),
    "enb-less-no-swap": ({"ball_less_1": {"trit"}}, ALL_FMT),
    "enb-le-no-strict": ({"ball_less_equal_1": {"trit"}}, ALL_FMT),
    "enb-equal-yes-radius": ({"ball_equal_1": {"trit"}, "ball_equal_2": {"trit"}}, ALL_FMT),
    "enb-equal-no-le": ({"ball_equal_1": {"trit"}}, ALL_FMT),
    "enb-less-unknown-large": ({"ball_less_1": {"trit"}}, ALL_FMT),
    "enb2-no-from-yes": ({"ball_less_2": {"trit"}, "ball_less_equal_2": {"trit"}}, ALL_FMT),
    "enb2-both": ({"ball_equal_2": {"trit"}}, ALL_FMT),
    "enb2-point-no-swap": ({"ball_contains_point_2": {"trit"}}, ALL_FMT),
    "enb2-point-no-special": ({"ball_contains_point_2": {"trit"}}, ALL_FMT),
    "enb2-less-whole-yes": ({"ball_less_2": {"trit"}}, ALL_FMT),
    "ens-hull-no-y": ({"ball_hull_1": {"ball_set"}, "ball_hull_2": {"ball_set"}}, ALL_FMT),
    "ens-hull-no-x": ({"ball_hull_1": {"ball_set"}, "ball_hull_2": {"ball_set"}}, ALL_FMT),
    "ens-int-no-y": ({"ball_intersection_1": {"ball_set"}, "ball_intersection_2": {"ball_set"}},
                     ALL_FMT),
    "ens-int-no-x": ({"ball_intersection_1": {"ball_set"}, "ball_intersection_2": {"ball_set"}},
                     ALL_FMT),
    "ens-int-swapped": ({"ball_intersection_1": {"ball_set"},
                         "ball_intersection_2": {"ball_set"}}, ALL_FMT),
    "ens-hull-radius-small": ({"ball_hull_1": {"ball_set"}, "ball_hull_2": {"ball_set"}},
                              ALL_FMT),
    "ens-int-empty-none": ({"ball_intersection_1": {"ball_set"},
                            "ball_intersection_2": {"ball_set"}}, ALL_FMT),
    "ens-int-radius-small": ({"ball_intersection_1": {"ball_set"},
                              "ball_intersection_2": {"ball_set"}}, ALL_FMT),
    "ens-sign-lost": ({k: {"ball_set"} for k in ("ball_hull_1", "ball_hull_2",
                                                 "ball_intersection_1", "ball_intersection_2")},
                      ALL_FMT),
    "ens-split-first-short": ({"ball_split_1": {"ball_splits"}, "ball_split_2": {"ball_splits"}},
                              ALL_FMT),
    "ens-split-whole-empty": ({"ball_split_1": {"ball_splits"}, "ball_split_2": {"ball_splits"}},
                              ALL_FMT),
    "ens-split-empty-whole": ({"ball_split_1": {"ball_splits"}, "ball_split_2": {"ball_splits"}},
                              ALL_FMT),
    "ens-split-second-shift": ({"ball_split_1": {"ball_splits"},
                                "ball_split_2": {"ball_splits"}}, ALL_FMT),
    "enc-mid2-radius-small": ({"interval_mid_rad_2": {"ball_of_interval"},
                               "interval_to_ball_2": {"ball_of_interval"}}, ALL_FMT),
    "enc-mid2-no-inf": ({"interval_mid_rad_2": {"ball_of_interval"},
                         "interval_to_ball_2": {"ball_of_interval"}}, ALL_FMT),
    "enc-mid2-no-move": ({"interval_mid_rad_2": {"ball_of_interval"},
                          "interval_to_ball_2": {"ball_of_interval"},
                          "ball_hull_2": {"ball_set"}, "ball_intersection_2": {"ball_set"}},
                         ALL_FMT),
    "enc-mid2-whole-tail": ({"interval_mid_rad_2": {"ball_of_interval"},
                             "interval_split_2": {"splits"}}, ALL_FMT),
    "enc-tball2-halfline": ({"interval_to_ball_2": {"ball_of_interval"}}, ALL_FMT),
    "enc-mid2-finite-inf": ({"interval_mid_rad_2": {"ball_of_interval"},
                             "interval_to_ball_2": {"ball_of_interval"}}, ALL_FMT),
    "enc-btoi2-nearest": ({"ball_to_interval_2": {"interval_of_ball"}}, ALL_FMT),
    "enc-btoi2-zero-eta": ({"ball_to_interval_2": {"interval_of_ball"}}, ALL_FMT),
    "enc-btoi2-inf-bounded": ({"ball_to_interval_2": {"interval_of_ball"}}, ALL_FMT),
    "enc-fromint1-nan-empty": ({"ball_from_interval_1": {"makes_ball"}}, ALL_FMT),
    "enc-fromint1-inf-empty": ({"ball_from_interval_1": {"makes_ball"}}, ALL_FMT),
    "enc-fromint1-reversed-whole": ({"ball_from_interval_1": {"makes_ball"}}, ALL_FMT),
    "enc-fromint1-radius-large": ({"ball_from_interval_1": {"makes_ball"}}, ALL_FMT),
    "enc-fromint1-center-off": ({"ball_from_interval_1": {"makes_ball"}}, ALL_FMT),
    "enc-split2-no-move": ({"interval_split_2": {"splits"}}, ALL_FMT),
    "enc-split2-gap": ({"interval_split_2": {"splits"}}, ALL_FMT),
}
# The kernels whose listing a fault reaches through a kernel it changes (interval_split_2 takes the
# midpoint of interval_mid_rad_2's listing; the hull and intersection of two limbs the conversions).
PLANTED["enc-mid2-whole-tail"][0].pop("interval_split_2")
for _v in ("enc-mid2-radius-small", "enc-mid2-no-inf", "enc-mid2-finite-inf",
           "enc-tball2-halfline"):
    PLANTED[_v][0].update({"ball_hull_2": {"ball_set"}, "ball_intersection_2": {"ball_set"}})
PLANTED["enc-btoi2-nearest"][0].update({"ball_hull_2": {"ball_set"},
                                        "ball_intersection_2": {"ball_set"}})
PLANTED["enc-btoi2-zero-eta"][0].update({"ball_hull_2": {"ball_set"},
                                         "ball_intersection_2": {"ball_set"}})
PLANTED["enc-btoi2-inf-bounded"][0].update({"ball_hull_2": {"ball_set"},
                                            "ball_intersection_2": {"ball_set"}})
# Where a fault must be caught when not in every kernel it may fail in: the kernels whose listing it
# changes directly (the hull and the intersection of two limbs meet it through the conversions, on
# the lines where it breaks their claim).
MUST_CATCH = {v: {k for k in PLANTED[v][0] if k not in ("ball_hull_2", "ball_intersection_2")}
              for v in ("enc-mid2-radius-small", "enc-mid2-no-inf", "enc-mid2-finite-inf",
                        "enc-mid2-no-move",
                        "enc-tball2-halfline", "enc-btoi2-nearest", "enc-btoi2-zero-eta",
                        "enc-btoi2-inf-bounded")}
MUST_CATCH.update({v: {"ball_hull_1", "ball_intersection_1"} & set(PLANTED[v][0])
                   for v in ("ens-hull-no-y", "ens-hull-no-x", "ens-hull-radius-small",
                             "ens-int-radius-small")})
# The strata that reach a fault that the default strata reach rarely.
PLANTED_STRATA = {"enb-less-unknown-large": "huge", "enc-mid2-no-move": "point,step,oddeta",
                  "enc-btoi2-zero-eta": "zeroend,cross,exactend", "ens-int-swapped": "bothspecial",
                  "ens-sign-lost": "bothspecial,ballstates", "enc-split2-no-move": "beyond,top",
                  "enc-mid2-no-inf": "beyond", "enc-mid2-finite-inf": "threshold,beyond",
                  "enc-btoi2-inf-bounded": "threshold,beyond"}


def _inputs(line):
    return [t for t in line.partition(" -> ")[0].split()[2:] if not t.startswith("#")]


def _vals(fmt, line):
    return [F.parse_limb(fmt, t) for t in _inputs(line)]


def _both_whole_signs(fmt, line):
    t = _inputs(line)
    k = len(t) // 2 - 1
    x, y = t[:k + 1], t[k + 1:]
    whole = lambda b: b[-1] == "inf" and all(F.parse_limb(fmt, c) == 0 for c in b[:-1])
    sign = lambda b: any(c.startswith("-") for c in b[:-1])
    return whole(x) and whole(y) and sign(x) != sign(y)


def _passed_zero(fmt, line):
    """An operand returned as it is (Y when X is special, X when Y is special) has a zero limb of a
    minus sign."""
    t = _inputs(line)
    k = len(t) // 2 - 1
    x, y = t[:k + 1], t[k + 1:]
    union = line.split()[0].startswith("ball_hull")
    special = (lambda b: b[-1] in ("nan", "-nan")) if union else (lambda b: b[-1] == "inf")
    out = y if special(x) else x if special(y) else None
    return out is not None and any(c in ("-0x0p+0", "-0x0.0p+0") for c in out)


def _x_whole(fmt, line):
    v = _vals(fmt, line)
    return v[0] == F.NEG_INF and v[len(v) // 2] == F.POS_INF


def _x_halfline(fmt, line):
    v = _vals(fmt, line)
    lo, hi = v[0], v[len(v) // 2]
    return (lo == F.NEG_INF) != (hi == F.POS_INF) and lo != F.POS_INF


def _ball_whole(fmt, line):
    return _vals(fmt, line)[-1] == F.POS_INF


def _ball_empty(fmt, line):
    return _vals(fmt, line)[-1] == F.NAN


def _zero_lower(fmt, line):
    v = _vals(fmt, line)
    return all(type(a) is int for a in v) and sum(v[:-1]) - v[-1] == 0


def _a_nan(fmt, line):
    return F.NAN in _vals(fmt, line)


def _same_inf(fmt, line):
    a, b = _vals(fmt, line)
    return a == b and type(a) is not int and a != F.NAN


def _reversed(fmt, line):
    a, b = _vals(fmt, line)
    return F.NAN not in (a, b) and not (a == b) and IV.make_given(a, b) == IV.MAKE_REVERSED


# A fault and the lines of its kernel it is about: every one of them must fail.
TARGETED = {
    "ens-int-swapped": [("ball_intersection_1", _both_whole_signs),
                        ("ball_intersection_2", _both_whole_signs)],
    "ens-sign-lost": [(k, _passed_zero) for k in ("ball_hull_1", "ball_hull_2",
                                                  "ball_intersection_1", "ball_intersection_2")],
    "enc-mid2-whole-tail": [("interval_mid_rad_2", _x_whole)],
    "enc-tball2-halfline": [("interval_to_ball_2", _x_halfline)],
    "ens-split-whole-empty": [("ball_split_1", _ball_whole), ("ball_split_2", _ball_whole)],
    "ens-split-empty-whole": [("ball_split_1", _ball_empty), ("ball_split_2", _ball_empty)],
    "enc-btoi2-zero-eta": [("ball_to_interval_2", _zero_lower)],
    "enc-fromint1-nan-empty": [("ball_from_interval_1", _a_nan)],
    "enc-fromint1-inf-empty": [("ball_from_interval_1", _same_inf)],
    "enc-fromint1-reversed-whole": [("ball_from_interval_1", _reversed)],
}


def _planted_one(args):
    variant, fname, count = args
    claims = load_claims(FIXTURE)
    expected, formats = PLANTED[variant]
    strata = PLANTED_STRATA.get(variant)
    fmt = F.parse_format(fname)
    out = []
    targeted = []
    changed = []
    for k in KERNELS:
        kern = claims.get(k)
        if fmt.p < kern.min_precision:
            continue
        st = strata.split(",") if strata and k in expected else None
        if st:
            known = G.RandomGen(kern, fmt, "selftest-enc").strata
            st = [s for s in st if s in known] or None
        g = G.RandomGen(kern, fmt, "selftest-enc", st)
        lines = list(g.lines(0, count))
        bad = run_enc(lines, variant)
        s = judge(bad, claims)
        t = totals(s)
        out.append((k, t["failed"] + t["invalid"] + t["suspicious"], t["invalid"],
                    t["suspicious"], failing_kinds(s, k)))
        if k in EXACT and k in expected:
            good = run_enc(lines)
            diff = [b for a, b in zip(good, bad) if a != b and not a.startswith("#")]
            changed.append((k, len(diff), totals(judge(diff, claims))["failed"]))
        for tk, pred in TARGETED.get(variant, ()):
            if tk == k:
                aimed = [ln for ln in lines if not ln.startswith("#") and pred(fmt, ln)]
                targeted.append((k, pred.__name__.strip("_"), len(aimed),
                                 totals(judge(run_enc(aimed, variant), claims))["failed"]))
    return variant, fname, out, targeted, changed


@test
def enc_planted(ctx):
    """Every planted fault of the family (refrun VARIANTS en-, enb-, ens-, enc-) caught in the
    kernels and entries where it belongs, in every format where it must be (PLANTED), and in no other
    kernel; never as an invalid or a suspicious case; on every line it changes of a kernel whose
    claim fixes the output (EXACT); and on every line of the class it is about (TARGETED: two whole
    lines of different signs, a zero passed through as it is, the whole line, a half-line, the empty
    set, an exact zero bound, a NaN bound, the same infinity twice, reversed bounds)."""
    n = ctx.n(1200, 400)
    tasks = [(v, f, n) for v in PLANTED for f in FORMATS]
    with cf.ProcessPoolExecutor(ctx.jobs) as ex:
        results = list(ex.map(_planted_one, tasks))
    aimed = changed_n = 0
    for variant, fname, out, targeted, changed in results:
        for k, what, n_aimed, n_failed in targeted:
            expect(n_failed == n_aimed and (n_aimed > 0 or fname not in PLANTED[variant][1]),
                   "%s %s: %s, %d of the %d lines of %s failed" % (variant, fname, k, n_failed,
                                                                  n_aimed, what))
            aimed += n_aimed
        for k, n_diff, n_failed in changed:
            expect(n_failed == n_diff, "%s %s: %s, %d of the %d lines it changes failed"
                   % (variant, fname, k, n_failed, n_diff))
            changed_n += n_diff
        expected, formats = PLANTED[variant]
        for k, bad, inv, sus, kinds in out:
            expect(not inv and not sus, "%s %s: %s gave %d invalid, %d suspicious"
                   % (variant, fname, k, inv, sus))
            if k not in expected:
                expect(not bad, "%s %s: %s, which does not use it, failed %d (%s)"
                       % (variant, fname, k, bad, kinds))
                continue
            expect(kinds <= expected[k], "%s %s: %s failed in %s, not only %s"
                   % (variant, fname, k, kinds, expected[k]))
        caught = {k for k, bad, _i, _s, _k in out if bad}
        if fname in formats:
            need = set(MUST_CATCH.get(variant, expected)) & {o[0] for o in out}
            expect(need <= caught, "%s %s: not caught in %s" % (variant, fname,
                                                                sorted(need - caught)))
    return ("%d planted faults in %d formats; %d lines they change of kernels whose claim fixes the "
            "output, %d lines of the classes they are about, each failed" % (
                len(PLANTED), len(FORMATS), changed_n, aimed))


# ---------------------------------------------------------------------------
# Hand-written lines: (line, the statements that must fail, or () for a pass), worked out by hand
# from architecture.md: one or more per cell of the table of rel, of the special states of a ball,
# of the clauses of ball_set and ball_splits, and of the conversions of two limbs.

OM = "0x1.fffffffffffffp+1023"
H = "0x1p+1023"                      # 2^1023: Omega/2 rounded up
ONE, TWO, THREE, FOUR = "0x1p+0", "0x1p+1", "0x1.8p+1", "0x1p+2"
HALF, ONEH = "0x1p-1", "0x1.8p+0"
Z, NZ, ETA = "0x0p+0", "-0x0p+0", "0x1p-1074"


def _l(kernel, ins, outs):
    return "%s binary64 %s -> %s" % (kernel, ins, outs)


HAND = [
    # empty, entire (certain, exact).
    (_l("interval_empty_1", "inf -inf", "1"), ()),
    (_l("interval_empty_1", "inf -inf", "0"), ("exact",)),
    (_l("interval_empty_1", "%s %s" % (ONE, TWO), "0"), ()),
    (_l("interval_empty_1", "%s %s" % (ONE, TWO), "1"), ("sound",)),
    (_l("interval_empty_1", "-inf inf", "0"), ()),
    (_l("interval_entire_1", "-inf inf", "1"), ()),
    (_l("interval_entire_1", "-inf %s" % ONE, "0"), ()),
    (_l("interval_entire_1", "-inf %s" % ONE, "1"), ("sound",)),
    (_l("interval_entire_1", "inf -inf", "0"), ()),
    # member: a finite point between the bounds; +inf is not a member of [1, +inf].
    (_l("interval_contains_1", "%s %s %s" % (ONE, TWO, ONE), "1"), ()),
    (_l("interval_contains_1", "%s %s %s" % (ONE, TWO, ONE), "0"), ("exact",)),
    (_l("interval_contains_1", "%s %s %s" % (ONE, TWO, THREE), "0"), ()),
    (_l("interval_contains_1", "%s inf inf" % ONE, "0"), ()),
    (_l("interval_contains_1", "%s inf inf" % ONE, "1"), ("sound",)),
    (_l("interval_contains_1", "-inf inf nan", "0"), ()),
    (_l("interval_contains_1", "-inf inf %s" % NZ, "1"), ()),
    (_l("interval_contains_1", "inf -inf %s" % Z, "0"), ()),
    # subset, IEEE 1788's: the empty set is a subset of every set.
    (_l("interval_subset_1", "inf -inf %s %s" % (ONE, TWO), "1"), ()),
    (_l("interval_subset_1", "inf -inf inf -inf", "1"), ()),
    (_l("interval_subset_1", "%s %s inf -inf" % (ONE, TWO), "0"), ()),
    (_l("interval_subset_1", "%s %s inf -inf" % (ONE, TWO), "1"), ("sound",)),
    (_l("interval_subset_1", "%s %s %s %s" % (ONE, TWO, ONE, TWO), "1"), ()),
    (_l("interval_subset_1", "-inf %s -inf inf" % ONE, "1"), ()),
    (_l("interval_subset_1", "-inf %s %s inf" % (ONE, Z), "0"), ()),
    (_l("interval_subset_1", "-inf %s %s inf" % (ONE, Z), "1"), ("sound",)),
    # The signs: lt with 0 on either side, eq with 0 (the empty set is neither).
    (_l("interval_positive_1", "%s %s" % (Z, ONE), "0"), ()),
    (_l("interval_positive_1", "%s %s" % (Z, ONE), "1"), ("sound",)),
    (_l("interval_positive_1", "%s inf" % ETA, "1"), ()),
    (_l("interval_positive_1", "%s inf" % ETA, "0"), ("exact",)),
    (_l("interval_positive_1", "inf -inf", "0"), ()),
    (_l("interval_positive_1", "-inf inf", "0"), ()),
    (_l("interval_negative_1", "-%s -%s" % (ONE, ETA), "1"), ()),
    (_l("interval_negative_1", "-%s %s" % (ONE, NZ), "0"), ()),
    (_l("interval_negative_1", "inf -inf", "1"), ("sound",)),
    (_l("interval_zero_1", "%s %s" % (Z, NZ), "1"), ()),
    (_l("interval_zero_1", "%s %s" % (Z, ETA), "0"), ()),
    (_l("interval_zero_1", "inf -inf", "0"), ()),
    # lt, le, eq (trit): for every choice; the empty set and the whole line give unknown.
    (_l("interval_less_1", "%s %s %s %s" % (ONE, TWO, THREE, FOUR), "1 0"), ()),
    (_l("interval_less_1", "%s %s %s %s" % (ONE, TWO, THREE, FOUR), "0 0"), ("exact",)),
    (_l("interval_less_1", "%s %s %s %s" % (ONE, TWO, TWO, FOUR), "0 0"), ()),
    # (A wrong yes where the relation neither holds nor fails for every choice fails yes alone:
    # the exactness is about the answers due.)
    (_l("interval_less_1", "%s %s %s %s" % (ONE, TWO, TWO, FOUR), "1 0"), ("yes",)),
    (_l("interval_less_1", "%s %s %s %s" % (TWO, FOUR, ONE, TWO), "0 1"), ()),
    (_l("interval_less_1", "inf -inf %s %s" % (ONE, TWO), "0 0"), ()),
    (_l("interval_less_1", "inf -inf %s %s" % (ONE, TWO), "0 1"), ("no",)),
    (_l("interval_less_1", "-inf inf %s %s" % (ONE, TWO), "0 0"), ()),
    (_l("interval_less_1", "%s %s %s %s" % (ONE, TWO, THREE, FOUR), "1 1"), ("both", "no")),
    (_l("interval_less_equal_1", "%s %s %s %s" % (ONE, TWO, TWO, FOUR), "1 0"), ()),
    (_l("interval_less_equal_1", "%s %s %s %s" % (TWO, FOUR, ONE, TWO), "0 0"), ()),
    (_l("interval_less_equal_1", "%s %s %s %s" % (TWO, FOUR, ONE, TWO), "0 1"), ("no",)),
    (_l("interval_equal_1", "%s %s %s %s" % (ONE, ONE, ONE, ONE), "1 0"), ()),
    (_l("interval_equal_1", "%s %s %s %s" % (ONE, TWO, ONE, TWO), "0 0"), ()),
    (_l("interval_equal_1", "%s %s %s %s" % (ONE, TWO, ONE, TWO), "1 0"), ("yes",)),
    (_l("interval_equal_1", "%s %s %s %s" % (ONE, TWO, THREE, FOUR), "0 1"), ()),
    (_l("interval_equal_1", "%s %s %s %s" % (ONE, TWO, TWO, FOUR), "0 0"), ()),
    (_l("interval_equal_1", "%s %s %s %s" % (ONE, TWO, TWO, FOUR), "0 1"), ("no",)),
    # The relations of IEEE 1788 that are not one of those: equal, interior, disjoint.
    (_l("interval_rel_equal_1", "inf -inf inf -inf", "1"), ()),
    (_l("interval_rel_equal_1", "inf -inf %s %s" % (ONE, TWO), "0"), ()),
    (_l("interval_rel_equal_1", "%s %s %s %s" % (ONE, TWO, ONE, TWO), "1"), ()),
    (_l("interval_rel_equal_1", "-inf inf -inf inf", "1"), ()),
    (_l("interval_rel_equal_1", "%s %s %s %s" % (ONE, TWO, ONE, THREE), "0"), ()),
    (_l("interval_rel_equal_1", "%s %s %s %s" % (ONE, TWO, ONE, THREE), "1"), ("sound",)),
    (_l("interval_rel_interior_1", "inf -inf inf -inf", "1"), ()),
    (_l("interval_rel_interior_1", "%s %s %s %s" % (ONE, TWO, Z, THREE), "1"), ()),
    (_l("interval_rel_interior_1", "%s %s %s %s" % (ONE, TWO, ONE, THREE), "0"), ()),
    (_l("interval_rel_interior_1", "%s %s %s %s" % (ONE, TWO, ONE, THREE), "1"), ("sound",)),
    (_l("interval_rel_interior_1", "-inf inf -inf inf", "1"), ()),
    (_l("interval_rel_interior_1", "-inf %s -inf %s" % (ONE, TWO), "1"), ()),
    (_l("interval_rel_interior_1", "%s %s inf -inf" % (ONE, TWO), "0"), ()),
    (_l("interval_rel_disjoint_1", "inf -inf -inf inf", "1"), ()),
    (_l("interval_rel_disjoint_1", "%s %s %s %s" % (ONE, TWO, TWO, FOUR), "0"), ()),
    (_l("interval_rel_disjoint_1", "%s %s %s %s" % (ONE, TWO, THREE, FOUR), "1"), ()),
    (_l("interval_rel_disjoint_1", "%s %s %s %s" % (ONE, TWO, THREE, FOUR), "0"), ("exact",)),
    (_l("interval_rel_disjoint_1", "-inf %s %s inf" % (ONE, TWO), "1"), ()),
    # Two limbs: the second limbs decide.
    (_l("interval_less_2", "%s %s %s 0x1p-60 %s 0x1p-59 %s %s" % (ONE, Z, ONE, ONE, TWO, Z),
        "1 0"), ()),
    (_l("interval_less_2", "%s %s %s 0x1p-60 %s 0x1p-59 %s %s" % (ONE, Z, ONE, ONE, TWO, Z),
        "0 0"), ("exact",)),
    (_l("interval_less_2", "%s %s %s 0x1p-60 %s 0x1p-60 %s %s" % (ONE, Z, ONE, ONE, TWO, Z),
        "0 0"), ()),
    (_l("interval_contains_2", "%s %s %s 0x1p-60 %s 0x1p-61" % (ONE, Z, ONE, ONE), "1"), ()),
    (_l("interval_contains_2", "%s %s %s 0x1p-60 %s 0x1p-59" % (ONE, Z, ONE, ONE), "0"), ()),
    (_l("interval_contains_2", "%s %s inf %s inf %s" % (ONE, Z, Z, NZ), "0"), ()),
    (_l("interval_empty_2", "inf %s -inf %s" % (Z, NZ), "1"), ()),
    (_l("interval_subset_2", "%s 0x1p-60 %s %s %s %s %s %s" % (ONE, TWO, Z, ONE, Z, TWO, Z),
        "1"), ()),
    (_l("interval_subset_2", "%s %s %s %s %s 0x1p-60 %s %s" % (ONE, Z, TWO, Z, ONE, TWO, Z),
        "1"), ("sound",)),
    # A ball, one limb, exact: [c - r, c + r] of exact pairs.
    (_l("ball_contains_point_1", "%s %s %s" % (ONE, HALF, ONEH), "1"), ()),
    (_l("ball_contains_point_1", "%s %s %s" % (ONE, HALF, ONEH), "0"), ("exact",)),
    (_l("ball_contains_point_1", "%s %s 0x1.8000000000001p+0" % (ONE, HALF), "0"), ()),
    (_l("ball_contains_point_1", "%s inf %s" % (Z, ONE), "1"), ()),
    (_l("ball_contains_point_1", "%s inf inf" % Z, "0"), ()),
    (_l("ball_contains_point_1", "%s inf inf" % Z, "1"), ("sound",)),
    (_l("ball_contains_point_1", "nan nan %s" % Z, "0"), ()),
    (_l("ball_contains_ball_1", "%s %s %s %s" % (Z, TWO, ONE, ONE), "1"), ()),
    (_l("ball_contains_ball_1", "%s %s %s 0x1.0000000000001p+0" % (Z, TWO, ONE), "0"), ()),
    (_l("ball_contains_ball_1", "%s %s %s 0x1.0000000000001p+0" % (Z, TWO, ONE), "1"),
     ("sound",)),
    (_l("ball_contains_ball_1", "%s inf %s %s" % (Z, ONE, ONE), "1"), ()),
    (_l("ball_contains_ball_1", "%s %s nan nan" % (ONE, Z), "1"), ()),
    (_l("ball_contains_ball_1", "%s %s nan nan" % (ONE, Z), "0"), ("exact",)),
    (_l("ball_contains_ball_1", "nan nan %s %s" % (ONE, Z), "0"), ()),
    (_l("ball_contains_ball_1", "%s inf %s inf" % (Z, Z), "1"), ()),
    (_l("ball_positive_1", "%s %s" % (ONE, ONE), "0"), ()),
    (_l("ball_positive_1", "%s %s" % (ONE, ONE), "1"), ("sound",)),
    (_l("ball_positive_1", "%s 0x1.fffffffffffffp-1" % ONE, "1"), ()),
    (_l("ball_positive_1", "%s inf" % Z, "0"), ()),
    (_l("ball_positive_1", "nan nan", "0"), ()),
    (_l("ball_negative_1", "-%s 0x1.fffffffffffffp-1" % ONE, "1"), ()),
    (_l("ball_negative_1", "-%s %s" % (ONE, ONE), "0"), ()),
    (_l("ball_zero_1", "%s %s" % (NZ, Z), "1"), ()),
    (_l("ball_zero_1", "%s %s" % (Z, ETA), "0"), ()),
    (_l("ball_zero_1", "%s %s" % (Z, ETA), "1"), ("sound",)),
    # ball_less_1, exact when rx + ry <= Omega.
    (_l("ball_less_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "1 0"), ()),
    (_l("ball_less_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "0 0"), ("exact_when",)),
    (_l("ball_less_1", "%s %s %s %s" % (Z, ONE, TWO, ONE), "0 0"), ()),
    (_l("ball_less_1", "%s %s %s %s" % (Z, ONE, TWO, ONE), "1 0"), ("yes",)),
    (_l("ball_less_1", "%s %s %s %s" % (FOUR, ONE, Z, ONE), "0 1"), ()),
    (_l("ball_less_1", "%s inf %s %s" % (Z, ONE, Z), "0 0"), ()),
    (_l("ball_less_1", "%s inf %s %s" % (Z, ONE, Z), "1 0"), ("yes",)),
    (_l("ball_less_1", "nan nan %s %s" % (ONE, Z), "0 0"), ()),
    # rx + ry = 2^1024 > Omega: exact_when fails, an unknown is not claimed wrong; a no still is.
    (_l("ball_less_1", "-%s %s %s %s" % (OM, H, OM, H), "0 0"), ()),
    (_l("ball_less_1", "-%s %s %s %s" % (OM, H, OM, H), "1 0"), ()),
    (_l("ball_less_1", "-%s %s %s %s" % (OM, H, OM, H), "0 1"), ("no",)),
    # rx + ry = 2^1023, between Omega/2 and Omega: exact_when holds.
    (_l("ball_less_1", "-%s 0x1p+1022 %s 0x1p+1022" % (OM, OM), "0 0"), ("exact_when",)),
    (_l("ball_less_1", "-%s 0x1p+1022 %s 0x1p+1022" % (OM, OM), "1 0"), ()),
    (_l("ball_less_equal_1", "%s %s %s %s" % (Z, ONE, TWO, ONE), "1 0"), ()),
    (_l("ball_less_equal_1", "%s %s %s %s" % (Z, ONE, TWO, ONE), "0 0"), ("exact_when",)),
    (_l("ball_equal_1", "%s %s %s %s" % (ONE, Z, ONE, Z), "1 0"), ()),
    (_l("ball_equal_1", "%s %s %s %s" % (ONE, HALF, ONE, HALF), "0 0"), ()),
    (_l("ball_equal_1", "%s %s %s %s" % (ONE, HALF, ONE, HALF), "1 0"), ("yes",)),
    (_l("ball_equal_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "0 1"), ()),
    (_l("ball_equal_1", "%s %s %s %s" % (Z, ONE, TWO, ONE), "0 0"), ()),
    # A ball, two limbs: sound, exact on the special states only.
    (_l("ball_contains_point_2", "%s %s %s 0x1.4p+0 %s" % (ONE, Z, HALF, Z), "1 0"), ()),
    (_l("ball_contains_point_2", "%s %s %s 0x1.4p+0 %s" % (ONE, Z, HALF, Z), "0 0"), ()),
    (_l("ball_contains_point_2", "%s %s %s 0x1.4p+0 %s" % (ONE, Z, HALF, Z), "0 1"), ("no",)),
    (_l("ball_contains_point_2", "%s %s %s inf %s" % (ONE, Z, HALF, Z), "0 1"), ()),
    (_l("ball_contains_point_2", "%s %s %s inf %s" % (ONE, Z, HALF, Z), "0 0"), ("special",)),
    (_l("ball_contains_point_2", "nan nan nan %s %s" % (ONE, Z), "0 1"), ()),
    (_l("ball_contains_point_2", "nan nan nan %s %s" % (ONE, Z), "1 0"), ("yes", "special")),
    (_l("ball_contains_point_2", "%s %s inf %s %s" % (Z, Z, ONE, Z), "1 0"), ()),
    (_l("ball_contains_point_2", "%s %s inf %s %s" % (Z, Z, ONE, Z), "0 0"), ("special",)),
    (_l("ball_contains_ball_2", "%s %s inf %s %s %s" % (Z, Z, ONE, Z, ONE), "1"), ()),
    (_l("ball_contains_ball_2", "%s %s inf %s %s %s" % (Z, Z, ONE, Z, ONE), "0"), ("special",)),
    (_l("ball_contains_ball_2", "%s %s %s %s %s %s" % (Z, Z, TWO, ONE, Z, HALF), "0"), ()),
    (_l("ball_contains_ball_2", "%s %s %s %s %s %s" % (Z, Z, ONE, ONE, Z, ONE), "1"), ("sound",)),
    (_l("ball_positive_2", "%s 0x1p-60 %s" % (ONE, ONE), "1"), ()),
    (_l("ball_positive_2", "%s 0x1p-60 %s" % (ONE, ONE), "0"), ("exact",)),
    (_l("ball_positive_2", "%s -0x1p-60 %s" % (ONE, ONE), "0"), ()),
    (_l("ball_less_2", "%s %s %s %s %s %s" % (Z, Z, ONE, FOUR, Z, ONE), "1 0"), ()),
    (_l("ball_less_2", "%s %s %s %s %s %s" % (Z, Z, ONE, FOUR, Z, ONE), "0 0"), ()),
    (_l("ball_less_2", "%s %s %s %s %s %s" % (Z, Z, ONE, FOUR, Z, ONE), "0 1"), ("no",)),
    (_l("ball_less_2", "%s %s inf %s %s %s" % (Z, Z, FOUR, Z, ONE), "0 0"), ()),
    (_l("ball_less_2", "%s %s inf %s %s %s" % (Z, Z, FOUR, Z, ONE), "1 0"), ("yes",)),
    (_l("ball_equal_2", "%s 0x1p-60 %s %s 0x1p-60 %s" % (ONE, Z, ONE, Z), "1 0"), ()),
    # (Its yes is exact, architecture.md says, but the claim does not: unknown is not claimed.)
    (_l("ball_equal_2", "%s 0x1p-60 %s %s 0x1p-60 %s" % (ONE, Z, ONE, Z), "0 0"), ()),
    (_l("ball_equal_2", "%s 0x1p-60 %s %s 0x1p-60 %s" % (ONE, Z, ONE, Z), "1 1"), ("both",
                                                                                   "no")),
    # ball_set, union: Y as it is when X is empty, X as it is when Y is empty and X is not.
    (_l("ball_hull_1", "nan nan %s %s" % (ONE, HALF), "%s %s" % (ONE, HALF)), ()),
    (_l("ball_hull_1", "nan nan %s %s" % (ONE, HALF), "%s %s" % (ONE, ONE)), ("Y as it is",)),
    (_l("ball_hull_1", "%s %s nan nan" % (ONE, HALF), "%s %s" % (ONE, HALF)), ()),
    (_l("ball_hull_1", "%s %s nan nan" % (ONE, HALF), "%s %s" % (ONE, ONE)), ("X as it is",)),
    (_l("ball_hull_1", "nan nan nan nan", "nan nan"), ()),
    (_l("ball_hull_1", "nan nan nan nan", "%s inf" % Z), ("Y as it is", "empty")),
    (_l("ball_hull_1", "nan nan %s inf" % NZ, "%s inf" % NZ), ()),
    (_l("ball_hull_1", "nan nan %s inf" % NZ, "%s inf" % Z), ("Y as it is",)),
    (_l("ball_hull_1", "%s inf nan nan" % NZ, "%s inf" % NZ), ()),
    (_l("ball_hull_1", "%s inf %s %s" % (Z, ONE, Z), "%s inf" % NZ), ()),
    (_l("ball_hull_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "%s %s" % (TWO, THREE)), ()),
    (_l("ball_hull_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "%s %s" % (TWO, TWO)),
     ("containment",)),
    (_l("ball_hull_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "%s inf" % Z), ()),
    (_l("ball_hull_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "nan nan"), ("empty",
                                                                          "containment")),
    (_l("ball_hull_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "%s -%s" % (ONE, ONE)),
     ("canonical",)),
    # ball_set, intersection: Y as it is when X is the whole line, X when Y is and X is not.
    (_l("ball_intersection_1", "%s inf %s %s" % (Z, ONE, HALF), "%s %s" % (ONE, HALF)), ()),
    (_l("ball_intersection_1", "%s inf %s %s" % (Z, ONE, HALF), "%s %s" % (ONE, ONE)),
     ("Y as it is",)),
    (_l("ball_intersection_1", "%s %s %s inf" % (ONE, HALF, Z), "%s %s" % (ONE, HALF)), ()),
    (_l("ball_intersection_1", "%s %s %s inf" % (ONE, HALF, Z), "%s %s" % (ONE, ONE)),
     ("X as it is",)),
    (_l("ball_intersection_1", "%s inf %s inf" % (Z, NZ), "%s inf" % NZ), ()),
    (_l("ball_intersection_1", "%s inf %s inf" % (Z, NZ), "%s inf" % Z), ("Y as it is",)),
    (_l("ball_intersection_1", "nan nan %s inf" % Z, "nan nan"), ()),
    (_l("ball_intersection_1", "nan nan %s inf" % Z, "%s inf" % Z), ("X as it is", "empty")),
    (_l("ball_intersection_1", "%s inf nan nan" % Z, "nan nan"), ()),
    (_l("ball_intersection_1", "nan nan %s %s" % (ONE, Z), "nan nan"), ()),
    (_l("ball_intersection_1", "nan nan %s %s" % (ONE, Z), "%s %s" % (ONE, Z)), ("empty",)),
    (_l("ball_intersection_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "nan nan"), ()),
    (_l("ball_intersection_1", "%s %s %s %s" % (Z, ONE, FOUR, ONE), "%s %s" % (Z, Z)), ()),
    (_l("ball_intersection_1", "%s %s %s %s" % (Z, TWO, TWO, TWO), "%s %s" % (ONE, ONE)), ()),
    (_l("ball_intersection_1", "%s %s %s %s" % (Z, TWO, TWO, TWO), "%s %s" % (ONE, HALF)),
     ("containment",)),
    (_l("ball_intersection_1", "%s %s %s %s" % (Z, TWO, TWO, TWO), "nan nan"),
     ("containment",)),
    # ball_splits.
    (_l("ball_split_1", "%s %s" % (ONE, ONE), "%s %s %s %s" % (HALF, HALF, ONEH, HALF)), ()),
    (_l("ball_split_1", "%s %s" % (ONE, ONE), "%s 0x1.fffffffffffffp-2 %s %s" % (HALF, ONEH,
                                                                                   HALF)),
     ("first part",)),
    (_l("ball_split_1", "%s %s" % (ONE, ONE), "%s %s %s 0x1.fffffffffffffp-2" % (HALF, HALF,
                                                                                   ONEH)),
     ("second part",)),
    (_l("ball_split_1", "%s %s" % (ONE, ONE), "%s inf %s %s" % (Z, ONEH, HALF)), ()),
    (_l("ball_split_1", "nan nan", "nan nan nan nan"), ()),
    (_l("ball_split_1", "nan nan", "%s inf %s inf" % (Z, Z)), ("empty",)),
    (_l("ball_split_1", "%s inf" % Z, "%s inf %s inf" % (Z, Z)), ()),
    (_l("ball_split_1", "%s inf" % Z, "nan nan nan nan"), ("whole line",)),
    (_l("ball_split_1", "%s %s" % (ONE, ONE), "%s %s %s -%s" % (HALF, HALF, ONEH, HALF)),
     ("canonical",)),
    # The midpoint of two limbs: the special values of 1788, a canonical center, finite_when.
    (_l("interval_mid_rad_2", "inf %s -inf %s" % (Z, Z), "nan nan nan"), ()),
    (_l("interval_mid_rad_2", "-inf %s inf %s" % (Z, Z), "%s %s inf" % (Z, Z)), ()),
    (_l("interval_mid_rad_2", "-inf %s inf %s" % (Z, Z), "%s %s inf" % (Z, ETA)), ("canonical",)),
    (_l("interval_mid_rad_2", "%s %s inf %s" % (ONE, Z, Z), "%s %s inf" % (OM, Z)), ()),
    (_l("interval_mid_rad_2", "%s %s inf %s" % (ONE, Z, Z), "%s %s inf" % (ONE, Z)), ("special",)),
    (_l("interval_mid_rad_2", "%s %s %s %s" % (ONE, Z, TWO, Z), "%s %s %s" % (ONEH, Z, HALF)), ()),
    (_l("interval_mid_rad_2", "%s %s %s %s" % (ONE, Z, TWO, Z), "%s %s inf" % (ONEH, Z)),
     ("finite_when",)),
    (_l("interval_mid_rad_2", "%s %s %s %s" % (ONE, Z, TWO, Z), "%s %s %s" % (TWO, Z, ONE)),
     ("midpoint",)),
    (_l("interval_mid_rad_2", "%s %s %s %s" % (ONE, Z, TWO, Z), "%s %s 0x1p-2" % (ONEH, Z)),
     ("containment",)),
    (_l("interval_mid_rad_2", "-%s %s %s %s" % (OM, Z, OM, Z), "%s %s inf" % (Z, Z)), ()),
    (_l("interval_mid_rad_2", "-%s %s %s %s" % (OM, Z, OM, Z), "%s %s %s" % (Z, Z, OM)), ()),
    # The center of 1788 is claimed whether or not finite_when holds.
    (_l("interval_mid_rad_2", "-%s %s %s %s" % (OM, Z, OM, Z), "0x1p+1000 %s inf" % Z),
     ("midpoint",)),
    # The limit 2^(qmax+p-2) = 2^1022: at it the radius is claimed finite, beyond it not.
    (_l("interval_mid_rad_2", "-0x1p+1022 %s 0x1p+1022 %s" % (Z, Z), "%s %s inf" % (Z, Z)),
     ("finite_when",)),
    (_l("interval_mid_rad_2", "-0x1p+1023 %s 0x1p+1023 %s" % (Z, Z), "%s %s inf" % (Z, Z)), ()),
    (_l("interval_mid_rad_2", "-0x1p+1022 %s 0x1.0000000000001p+1022 %s" % (Z, Z),
        "0x1p+969 %s inf" % Z), ()),
    (_l("interval_to_ball_2", "-%s %s %s %s" % (OM, Z, OM, Z), "%s %s inf" % (Z, Z)), ()),
    (_l("interval_to_ball_2", "%s %s %s %s" % (ONE, Z, TWO, Z), "%s %s inf" % (Z, Z)),
     ("finite_when",)),
    (_l("interval_to_ball_2", "%s %s inf %s" % (ONE, Z, Z), "%s %s inf" % (Z, Z)), ()),
    (_l("interval_to_ball_2", "%s %s inf %s" % (ONE, Z, Z), "%s %s inf" % (OM, Z)), ("special",)),
    # interval_of_ball of two limbs: an exact zero end, the tightness, bounded_when.
    (_l("ball_to_interval_2", "%s %s %s" % (ONE, Z, ONE), "%s %s %s %s" % (Z, Z, TWO, Z)), ()),
    (_l("ball_to_interval_2", "%s %s %s" % (ONE, Z, ONE), "-%s %s %s %s" % (ETA, Z, TWO, Z)),
     ("exact_when",)),
    (_l("ball_to_interval_2", "%s %s %s" % (ONE, Z, HALF), "%s %s %s %s" % (HALF, Z, ONEH, Z)), ()),
    (_l("ball_to_interval_2", "%s %s %s" % (ONE, Z, HALF), "0x1p-2 %s %s %s" % (Z, ONEH, Z)),
     ("tight",)),
    (_l("ball_to_interval_2", "%s %s %s" % (ONE, Z, HALF), "0x1.0000000000001p-1 %s %s %s"
        % (Z, ONEH, Z)), ("containment",)),
    (_l("ball_to_interval_2", "%s %s %s" % (ONE, Z, HALF), "-inf %s %s %s" % (Z, ONEH, Z)),
     ("bounded_when",)),
    (_l("ball_to_interval_2", "nan nan nan", "inf %s -inf %s" % (Z, Z)), ()),
    (_l("ball_to_interval_2", "nan nan nan", "-inf %s inf %s" % (Z, Z)), ("empty",)),
    (_l("ball_to_interval_2", "%s %s inf" % (Z, Z), "-inf %s inf %s" % (Z, Z)), ()),
    (_l("ball_to_interval_2", "%s %s inf" % (Z, Z), "%s %s inf %s" % (OM, Z, Z)),
     ("containment",)),
    (_l("ball_to_interval_2", "%s %s %s" % (OM, Z, OM), "%s %s inf %s" % (Z, Z, Z)), ()),
    # makes_ball from an interval with rel, abs and smallest_radius (ball_from_interval_1).
    (_l("ball_from_interval_1", "%s %s" % (ONE, TWO), "%s %s" % (ONEH, HALF)), ()),
    (_l("ball_from_interval_1", "%s %s" % (ONE, TWO), "%s %s" % (ONEH, ONE)), ("smallest_radius",)),
    (_l("ball_from_interval_1", "%s %s" % (ONE, TWO), "0x1.8000000000001p+0 0x1.0000000000002p-1"),
     ("midpoint",)),
    (_l("ball_from_interval_1", "%s %s" % (ONE, TWO), "%s %s" % (TWO, ONE)), ("midpoint",)),
    (_l("ball_from_interval_1", "%s %s" % (ONE, TWO), "%s %s" % (ONEH, "0x1.fffffffffffffp-2")),
     ("does not contain the interval",)),
    # [eta, eta] with the center 2 eta: within u|m| + eta of the midpoint, outside [lo, hi].
    (_l("ball_from_interval_1", "%s %s" % (ETA, ETA), "0x1p-1073 %s" % ETA), ("center",)),
    (_l("ball_from_interval_1", "%s %s" % (ETA, ETA), "%s %s" % (ETA, Z)), ()),
]


@test
def enc_judge(ctx):
    """Hand-written lines judged as worked out by hand, each failure in its statement: one or more
    per cell of the table of rel and of the special states of the predicates and comparisons of an
    interval and a ball, per clause of ball_set and ball_splits (the operands as they are, the sign
    of a zero compared there and nowhere else), per case of the conversions of two limbs; and every
    cell of the table of the constructors for ball_from_interval_1 with its right result, counted in
    its cell, its wrong results failing; lines outside the requirements invalid."""
    cl = claims_enc(ctx)
    n = 0
    for line, want in HAND:
        kernel = line.split()[0]
        s = judge([line], cl)
        t = totals(s)
        expect(t["invalid"] == 0 and t["judged"] == 1, "%s: not judged (%s)" % (line, t))
        got = failed_statements(s, kernel)
        if not want:
            expect(t["failed"] == 0, "%s failed: %s" % (line, got))
        else:
            expect(t["failed"] == 1 and got == set(want),
                   "%s: failed %s, not %s" % (line, sorted(got), list(want)))
        n += 1
    for line in INVALID:
        t = totals(judge([line], cl))
        expect(t["invalid"] == 1, "%s: not invalid (%s)" % (line, t))
    cells = _cells(cl)
    return "%d hand-written lines, %d invalid ones, %d lines of the cells of the constructors" % (
        n, len(INVALID), cells)


INVALID = [
    _l("interval_empty_1", "%s %s" % (TWO, ONE), "0"),
    _l("interval_less_1", "nan %s %s %s" % (ONE, ONE, TWO), "0 0"),
    _l("interval_empty_2", "%s %s %s %s" % (ONE, ONE, TWO, Z), "0"),
    _l("interval_contains_2", "%s %s %s %s %s %s" % (ONE, Z, TWO, Z, ONE, ONE), "0"),
    _l("ball_positive_1", "%s -%s" % (ONE, ONE), "0"),
    _l("ball_contains_point_2", "%s %s %s %s %s" % (ONE, ONE, ONE, ONE, Z), "0 0"),
    _l("ball_hull_1", "%s inf %s %s" % (ONE, ONE, Z), "%s inf" % Z),
    _l("ball_split_2", "nan %s nan" % Z, "nan nan nan nan nan nan"),
    _l("interval_mid_rad_2", "%s %s %s %s" % (TWO, Z, ONE, Z), "nan nan nan"),
    _l("ball_to_interval_2", "%s %s %s" % (ONE, ONE, ONE), "%s %s %s %s" % (Z, Z, TWO, Z)),
]

# The table of the constructors (architecture.md, "The constructors on every pair of values") for a
# ball from an interval: lo (row) and hi (column) each a NaN, -inf, a finite number or +inf.
_BALL_CELL = {"NaN": "nan", "-inf": "-inf", "+inf": "inf"}


def _cells(cl):
    n = 0
    vals = {"NaN": "nan", "-inf": "-inf", "a": ONE, "b": TWO, "+inf": "inf"}
    for r in ("NaN", "-inf", "a", "+inf"):
        for c in ("NaN", "-inf", "b", "+inf"):
            for order in ((("<=", ONE, TWO), (">", TWO, ONE)) if (r, c) == ("a", "b") else
                          ((None, vals[r], vals[c]),)):
                rel, lo, hi = order
                L, U = (F.parse_limb(F.parse_format("binary64"), t) for t in (lo, hi))
                given = IV.make_given(L, U)
                if given == IV.MAKE_REVERSED:
                    right, wrong = "nan nan", "%s inf" % Z
                elif given in (IV.MAKE_INTERVAL, IV.MAKE_POINT):
                    right, wrong = "%s %s" % (ONEH, HALF), "nan nan"
                else:
                    right, wrong = "%s inf" % Z, "nan nan"
                cell = IV.MAKE_CELL % (r, c) + ("" if rel is None else
                                                ", a <= b" if rel == "<=" else ", a > b")
                s = judge([_l("ball_from_interval_1", "%s %s" % (lo, hi), right)], cl)
                es = entry_stats(s, "ball_from_interval_1")
                counts = next(iter(es.values()))[3]
                expect(totals(s)["failed"] == 0 and counts.get(cell) == 1,
                       "the cell %s: %s passed? %s" % (cell, right, counts))
                s = judge([_l("ball_from_interval_1", "%s %s" % (lo, hi), wrong)], cl)
                expect(totals(s)["failed"] == 1, "the cell %s: %s passed" % (cell, wrong))
                n += 2
    return n


# ---------------------------------------------------------------------------

@test
def enc_gen(ctx):
    """The generator of the family: case i alone is case i of its run, the seed matters, every case
    satisfies the requirements (gen6.valid6, from the definitions), every stratum of the header has
    a case, in two formats; signs of zeros written both ways where the operands pass through as they
    are."""
    cl = claims_enc(ctx)
    n = ctx.n(400, 150)
    for k in KERNELS:
        kern = cl.get(k)
        for fname in ("binary64", "fp:4:-6:1"):
            fmt = F.parse_format(fname)
            g = G.RandomGen(kern, fmt, 3)
            lines = list(g.lines(0, n))
            body = lines[1:-1]
            expect(len(body) == n, "%s: %d lines" % (k, len(body)))
            for i in (0, n // 2, n - 1):
                one = list(G.RandomGen(kern, fmt, 3).lines(i, 1))[1]
                expect(one == body[i], "%s %s: case %d alone differs" % (k, fname, i))
            other = list(G.RandomGen(kern, fmt, 4).lines(0, n))[1:-1]
            expect(other != body, "%s: the seed does not matter" % k)
            tags = {ln.rsplit("#", 1)[1].split(":")[0] for ln in body}
            expect(tags == set(g.strata), "%s %s: strata %s, cases of %s" % (
                k, fname, sorted(g.strata), sorted(tags)))
            t = totals(judge(run_enc(lines), cl))
            expect(t["invalid"] == 0, "%s %s: %d invalid cases" % (k, fname, t["invalid"]))
            if k.startswith("ball_hull") or k.startswith("ball_intersection"):
                expect(any("-0x0p+0 inf" in ln for ln in body), "%s: no -0 center" % k)
    return "%d kernels in two formats" % len(KERNELS)


def _case_values(kernel, fmt, line):
    """{input: [values]} of a request line."""
    toks = _inputs(line)
    out, i = {}, 0
    for n, l in kernel.inputs:
        out[n] = [F.parse_limb(fmt, t) for t in toks[i:i + l]]
        i += l
    return out


def _v(limbs):
    return IV.bound_value(None, limbs) if len(limbs) == 1 else (
        sum(limbs) if all(type(t) is int for t in limbs) else limbs[0])


def _sets_of(kernel, vals):
    """The interval and ball operands of a case as ("empty",) or (lo, hi), and the point."""
    e = kernel.ensures[0]
    out = []
    pairs = list(kernel.interval_requires) or list(kernel.ball_requires)
    for a, b in pairs:
        if kernel.interval_requires:
            L, U = _v(vals[a]), _v(vals[b])
            out.append(("empty",) if L == F.POS_INF and U == F.NEG_INF else (L, U))
        else:
            c, r = _v(vals[a]), vals[b][0]
            out.append(("empty",) if r == F.NAN else (F.NEG_INF, F.POS_INF) if r == F.POS_INF
                       else (c - r, c + r, c, r))
    point = _v(vals[e.point]) if getattr(e, "point", None) else None
    return out, point


def _special_set(s):
    return s[0] == "empty" or (s[0] == F.NEG_INF and s[1] == F.POS_INF)


def _finite(*vs):
    return all(type(v) is int for v in vs)


def _p_special(fmt, sets, point):
    return any(_special_set(s) for s in sets)


def _p_touch(fmt, sets, point):
    (a, b), (c, d) = sets[0][:2], sets[1][:2]
    return b == c or d == a


def _p_equal_bound(fmt, sets, point):
    return sets[0][0] == sets[1][0] or sets[0][1] == sets[1][1]


def _p_nested(fmt, sets, point):
    (a, b), (c, d) = sets[0][:2], sets[1][:2]
    le = lambda x, y: IV.XT.x_cmp(x, 0, y, 0) <= 0
    return (le(a, c) and le(d, b)) or (le(c, a) and le(b, d))


def _p_disjoint(fmt, sets, point):
    (a, b), (c, d) = sets[0][:2], sets[1][:2]
    lt = lambda x, y: IV.XT.x_cmp(x, 0, y, 0) < 0
    return lt(b, c) or lt(d, a)


def _p_two_balls_boundary(fmt, sets, point):
    if point is not None:
        s = sets[0]
        return len(s) == 4 and _finite(point) and abs(point - s[2]) == s[3]
    x, y = sets
    if len(x) != 4 or len(y) != 4:
        return False
    d = abs(y[2] - x[2])
    return d == x[3] + y[3] or d + y[3] == x[3] or d + x[3] == y[3] or (d == 0 and x[3] == y[3] == 0)


def _p_huge(fmt, sets, point):
    return any(len(s) == 4 and (32 * s[3] >= fmt.omega or 32 * abs(s[2]) >= fmt.omega)
               for s in sets)


def _p_point_radius(fmt, sets, point):
    return any(len(s) == 4 and s[3] == 0 for s in sets)


def _p_both_special(fmt, sets, point):
    return all(_special_set(s) or s[0] == "empty" for s in sets)


def _p_top_center(fmt, sets, point):
    return len(sets[0]) == 4 and 8 * abs(sets[0][2]) >= fmt.omega


def _p_beyond(fmt, sets, point):
    return any(len(s) >= 2 and any(_finite(v) and abs(v) > fmt.omega for v in s[:2]) for s in sets)


def _p_threshold(fmt, sets, point):
    T = 1 << (fmt.qmax + fmt.p - 2 - fmt.qmin)
    vs = [abs(v) for s in sets for v in s[:2] if _finite(v)]
    return any(T // 2 <= v <= 2 * T for v in vs)


def _p_zero_end(fmt, sets, point):
    s = sets[0]
    return len(s) == 4 and (s[0] == 0 or s[1] == 0)


# (family, stratum): (the property of the cases of that stratum, the fraction that must have it).
STRATA_CHECKS = {
    ("ivpred", "special"): (_p_special, 1), ("ivpred", "touch"): (_p_touch, 1),
    ("ivpred", "equal"): (_p_equal_bound, 1), ("ivpred", "nested"): (_p_nested, 1),
    ("ivpred", "disjoint"): (_p_disjoint, Q(3, 4)),
    ("ballpred", "ballstates"): (_p_special, 1),
    ("ballpred", "boundary"): (_p_two_balls_boundary, Q(1, 2)),
    ("ballpred", "huge"): (_p_huge, 1), ("ballpred", "points"): (_p_point_radius, 1),
    ("ballset", "bothspecial"): (_p_both_special, 1), ("ballset", "point"): (_p_point_radius, 1),
    ("ballset", "touch"): (_p_two_balls_boundary, Q(1, 2)),
    ("ballset", "nested"): (_p_nested, Q(1, 2)), ("ballset", "disjoint"): (_p_disjoint, Q(1, 2)),
    ("ballsplit", "ballstates"): (_p_special, 1), ("ballsplit", "top"): (_p_top_center, 1),
    ("ivmid", "beyond"): (_p_beyond, Q(3, 4)), ("ivmid", "threshold"): (_p_threshold, 1),
    ("ballbound", "threshold"): (_p_threshold, Q(3, 4)), ("ballbound", "zeroend"): (_p_zero_end, 1),
}


@test
def enc_strata(ctx):
    """The strata of the family's generator (genenc.py) and the strata gen6.py has for the
    conversions of two limbs are what they are for: every case, or the fraction given, of a stratum
    has its property (an operand special, intervals touching, nested, disjoint or with an equal
    bound, balls on the boundary of the relation, huge, of radius zero, both special, a center near
    Omega, a bound beyond Omega, at the limit of finite_when or bounded_when, an end exactly zero),
    in binary64 and a toy format."""
    cl = claims_enc(ctx)
    n = ctx.n(400, 160)
    checked = 0
    for k in KERNELS:
        kern = cl.get(k)
        g = G.RandomGen(kern, F.parse_format("binary64"), "strata")
        fam = g.shape.family
        for fname in ("binary64", "fp:4:-6:1"):
            fmt = F.parse_format(fname)
            if fmt.p < kern.min_precision:
                continue
            for st in g.strata:
                chk = STRATA_CHECKS.get((fam, st))
                if chk is None:
                    continue
                if fam in ("ivmid", "ballbound") and kern.limbs_of(
                        (kern.interval_requires or kern.ball_requires)[0][0]) != 2:
                    continue
                pred, frac = chk
                lines = list(G.RandomGen(kern, fmt, "strata", [st]).lines(0, n))[1:-1]
                good = 0
                for ln in lines:
                    sets, point = _sets_of(kern, _case_values(kern, fmt, ln))
                    good += bool(pred(fmt, sets, point))
                expect(good >= frac * len(lines), "%s %s, stratum %s: %d of %d cases %s" % (
                    k, fname, st, good, len(lines), pred.__name__[3:]))
                checked += 1
    return "%d streams of a stratum" % checked


@test
def enc_merging(ctx):
    """The merge of the summaries of two halves of streams of the family is the summary of the
    whole."""
    cl = claims_enc(ctx)
    ks = ("interval_less_2", "ball_less_2", "ball_hull_1", "ball_split_2", "interval_mid_rad_2",
          "ball_to_interval_2", "ball_from_interval_1")
    for k in ks:
        lines = run_enc(stream_enc(ctx, k, "binary64", ctx.n(600, 200)))
        body = [ln for ln in lines if not ln.startswith("#")]
        whole = judge(body, cl)
        a = judge(body[:len(body) // 2], cl)
        b = judge(body[len(body) // 2:], cl)
        m = C.Summary()
        m.merge(a)
        m.merge(b)
        expect(json.dumps(m.to_json()["keys"], sort_keys=True)
               == json.dumps(whole.to_json()["keys"], sort_keys=True), "%s: merge differs" % k)
    return "%d kernels" % len(ks)
