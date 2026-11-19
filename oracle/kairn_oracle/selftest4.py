"""The oracle's own tests of the adversarial search (search.py) and of the shrinker (shrink.py).

Both run the reference runner in this process, correct and with the errors it can inject
(refrun.VARIANTS), against the hand-written fixtures, and every verdict they report is checked
again by a checker of its own (selftest.judge), which shares nothing with them but the checker's
code: a failure the search reports must fail there, a quantity it reports must be the one the
checker computes for its line, and the correct runner must give no failure at all.
"""

from fractions import Fraction as Q

from . import fmt as F
from . import search as S
from . import shrink as SH
from .claims import load_claims
from .selftest import test, expect, judge, FIXTURE, FIXTURE2
from .selftest3 import FIXTURE3

# Planted faults the search must find: (fixture, kernel, format, variant, radius design, a part of
# the label of the entry that must fail). The search keeps to the kernel's requirements, so a
# variant that alters the inputs (corrupt-input) has no place here.
PLANTED = (
    (FIXTURE, "two_sum", "binary64", "ulp-rare", "first", "error"),
    (FIXTURE, "mul_2_1", "binary32", "mul-drop-cross", "first", "error"),
    (FIXTURE, "two_prod", "binary64", "subnormal-trunc", "first", "leading_rounded"),
    (FIXTURE, "add_fast_2_2", "fp:5:-10:5", "add-skip-renorm", "first", "normalized"),
    (FIXTURE2, "radd", "binary64", "radd-no-step", "first", "upper"),
    (FIXTURE2, "ball_mul_1", "binary64", "ball-no-rr", "first", "encloses"),
    (FIXTURE3, "add_2_2_full", "binary32", "full-overflow-sign", "second", "[F4]"),
    (FIXTURE3, "ball_add_1_full", "binary64", "ball2-no-E", "second", "[B3]"),
)
# The correct runner on kernels of every kind the search measures.
CLEAN = (
    (FIXTURE, "add_2_2", "binary64"), (FIXTURE, "mul_2_2", "fp:6:-12:4"),
    (FIXTURE, "two_prod", "binary32"), (FIXTURE2, "rmul", "binary64"),
    (FIXTURE2, "ball_mul_2", "binary64"), (FIXTURE3, "mul_2_1_full", "binary64"),
    (FIXTURE3, "ball_scale_2_full", "binary32"),
)


def _claims(ctx, path):
    cache = ctx.__dict__.setdefault("_s4_claims", {})
    if path not in cache:
        cache[path] = load_claims(path)
    return cache[path]


def _search(ctx, path, kernel, fmtname, variant, radius, evals, seed="selftest4"):
    cl = _claims(ctx, path)
    runner = S.Runner("refrun:%s" % variant, radius)
    s = S.Search(cl, cl.get(kernel), F.parse_format(fmtname), runner, seed, evals, batch=128)
    return s.run()


def _value(summary, obj, p):
    """The quantity of an objective in a checker's summary of one line."""
    (st,) = summary.keys.values()
    es = st.entries[obj.entry]
    if obj.what == "ratio":
        r = es.max_ratio
    elif obj.what == "c":
        a = es.observed_a(p)
        r = None if a is None else a[0]
    elif obj.what == "excess":
        r = es.maxima.get("excess in gaps", (None,))[0]
    else:
        r = es.minima.get("slack in gaps of the radius", (None,))[0]
    return None if r is None else (S.HUGE if r[1] == 0 else Q(r[0], r[1]))


@test
def search_finds_planted(ctx):
    """Each planted fault is found within 2000 cases, failing the entry where it belongs, and the
    line the search reports fails when the checker judges it on its own."""
    res = []
    for path, kernel, fmtname, variant, radius, part in PLANTED:
        s = _search(ctx, path, kernel, fmtname, variant, radius, 2000)
        expect(s.failures, "search: %s %s with %s: no failure in %d cases" % (
            kernel, fmtname, variant, s.evals))
        f = s.failures[0]
        expect(any(part in k for k in f["keys"]), "search: %s %s with %s: failed %s, not %r" % (
            kernel, fmtname, variant, f["keys"], part))
        t = judge([f["line"]], _claims(ctx, path))
        expect(sum(st.c["failed"] for st in t.keys.values()) == 1,
               "search: %s %s with %s: the checker passes the line it reported: %s" % (
                   kernel, fmtname, variant, f["line"]))
        res.append("%s/%s %d" % (kernel, variant, s.evals))
    return "; ".join(res)


@test
def search_correct_runner(ctx):
    """The correct runner: no failure; every quantity reported is what the checker computes for
    the reported line; the same seed gives the same search, another seed another."""
    res = []
    for path, kernel, fmtname in CLEAN:
        s = _search(ctx, path, kernel, fmtname, "correct",
                    "second" if path == FIXTURE3 else "first", 1200)
        expect(not s.failures, "search: the correct runner failed %s %s: %s" % (
            kernel, fmtname, s.failures[:1]))
        expect(s.evals == 1200, "search: %s %s ran %d cases of 1200" % (kernel, fmtname, s.evals))
        p = F.parse_format(fmtname).p
        n = 0
        for o, b in zip(s.judge.objectives, s.best):
            if b is None:
                continue
            got = _value(judge([b.line], _claims(ctx, path)), o, p)
            expect(got == b.score, "search: %s %s %s: reported %s, the checker says %s for %s" % (
                kernel, fmtname, o.what, b.score, got, b.line))
            n += 1
        expect(n > 0, "search: %s %s: no quantity measured" % (kernel, fmtname))
        res.append("%s %d" % (kernel, n))
    a = _search(ctx, FIXTURE, "add_2_1", "binary64", "correct", "first", 600).result()
    b = _search(ctx, FIXTURE, "add_2_1", "binary64", "correct", "first", 600).result()
    c = _search(ctx, FIXTURE, "add_2_1", "binary64", "correct", "first", 600, "other").result()
    for r in (a, b, c):
        del r["seconds"]
    expect(a == b, "search: the same seed gave two searches")
    expect(a != c, "search: two seeds gave the same search")
    return "; ".join(res)


@test
def search_moves_valid(ctx):
    """Every child the moves make, once repaired, satisfies the kernel's requirements, as the
    checker reads them, for kernels of every role (pairs, radii, powers of two, abs_ge, balls)."""
    from . import gen as G
    n = 0
    for path, kernel, fmtname in ((FIXTURE, "fast_two_sum", "fp:4:-6:3"),
                                  (FIXTURE2, "mul_pow2_2", "binary32"),
                                  (FIXTURE2, "ball_sub_2", "fp:5:-8:4"),
                                  (FIXTURE3, "ball_mul_2_full", "binary64"),
                                  (FIXTURE2, "radd", "fp:3:-4:1")):
        cl = _claims(ctx, path)
        pr = S.Problem(cl.get(kernel), F.parse_format(fmtname))
        rng = G.CaseRandom(b"selftest4", 0)
        base = [pr.random_case(rng) for _ in range(20)]
        lines = []
        for i in range(ctx.n(3000, 1000)):
            vals, negz = base[i % len(base)]
            v = {k: list(x) for k, x in vals.items()}
            nz = set(negz)
            ok = pr.operand_move(rng, v, nz) if i % 2 else pr.case_move(rng, v, nz)
            r = pr.repair(v, nz) if ok else None
            if r is not None:
                lines.append(pr.text(r[0], r[1], "m:%d" % i) + " -> " + " ".join(
                    ["0x0p+0"] * sum(dict(cl.get(kernel).outputs).values())))
        t = judge(lines, cl, ignore_min_precision=True)
        inv = sum(st.c["invalid"] for st in t.keys.values())
        expect(inv == 0, "search moves: %d of %d children of %s outside the requirements: %s" % (
            inv, len(lines), kernel, [e for st in t.keys.values()
                                      for e in st.examples["invalid"]][:2]))
        expect(len(lines) > 100, "search moves: only %d children of %s" % (len(lines), kernel))
        n += len(lines)
    return "%d children" % n


# Planted faults to shrink, and whether a toy format must be found. ulp-rare is not among them: it
# depends on a hash of the line's text, tag included, so the same operands fail or pass by their tag.
SHRINK = (
    (FIXTURE, "mul_2_2", "binary64", "mul-drop-cross", "first", True),
    (FIXTURE, "two_prod", "binary64", "subnormal-trunc", "first", True),
    (FIXTURE2, "radd", "binary64", "radd-no-step", "first", True),
    (FIXTURE3, "ball_add_1_full", "binary64", "ball2-no-E", "second", False),
)


@test
def shrink_planted(ctx):
    """A failing line of each planted fault shrinks to a simpler line that fails the same entry,
    when judged by the checker on its own, the same way twice; where the fault exists in toy
    formats, the shrinker finds one; and it refuses a line that does not fail."""
    res = []
    for path, kernel, fmtname, variant, radius, toy in SHRINK:
        cl = _claims(ctx, path)
        s = _search(ctx, path, kernel, fmtname, variant, radius, 2000)
        expect(s.failures, "shrink: no failing line of %s %s to start from" % (kernel, variant))
        line = s.failures[0]["line"]
        runner = S.Runner("refrun:%s" % variant, radius)
        out = []
        for _ in range(2):
            sh = SH.Shrinker(cl, runner, line, evals=ctx.n(20000, 8000), toy_cases=500)
            out.append(sh.run().result())
        r = out[0]
        expect(out[0] == out[1], "shrink: %s %s: two runs disagree" % (kernel, variant))
        expect(r["same_format"]["measure"] <= r["measure"],
               "shrink: %s: the measure grew" % kernel)
        expect(r["same_format"]["measure"] < r["measure"],
               "shrink: %s %s: nothing shrank in %s" % (kernel, variant, fmtname))
        t = judge([r["completed"]], cl)
        (st,) = t.keys.values()
        expect(st.c["failed"] == 1, "shrink: %s: the checker passes the shrunk line %s" % (
            kernel, r["completed"]))
        keys = S.failure_keys(S.Judge(cl, cl.get(kernel), F.parse_format(
            r["completed"].split(" ")[1])), st)
        expect(r["kept"] in keys, "shrink: %s: the shrunk line fails %s, not %s" % (
            kernel, keys, r["kept"]))
        if toy:
            expect(r["toy"] is not None, "shrink: %s %s: no toy format found: %s" % (
                kernel, variant, r["notes"]))
        res.append("%s/%s %s -> %s" % (kernel, variant, tuple(r["measure"]),
                                       tuple((r["toy"] or r["same_format"])["measure"])))
    cl = _claims(ctx, FIXTURE)
    try:
        SH.Shrinker(cl, S.Runner("refrun"), "two_sum binary64 0x1p+0 0x1p-60").run()
    except SH.ShrinkError:
        pass
    else:
        expect(False, "shrink: a line that passes was shrunk")
    return "; ".join(res)
