"""The reference runner's kernels and folds of the ball vectors and of the accumulator, written from
the listings of gen/kernels/ and of architecture.md ("Ball vectors", "The accumulator"), on IEEE
values (refrun.Arith), one operation per line of the listing.  install() adds them to
refrun.Kernels and the dictionaries of refrun.

Their constants are those of the listings, const up(EXPR) rounded up to the format from unit(K)
and tiny(K) of the kernels K the listings name (add_1_1, add_2_2, mul_1_1, mul_2_1, mul_2_2),
whose c, k and t this runner reads from a claims file, the fixture claims-wave8.json by default
(refrun --bv-claims).  Its comparisons are IEEE's (false on a NaN), its steps nextUp of the
definition (refrun.Arith.next_up), its guard RN(a + 0).

Variants plant one fault each (VARIANTS below), for the selftest.
"""

import math
import os
from fractions import Fraction

INF = math.inf
NAN = math.nan

VARIANTS = {
    # The kernels of the radii.
    "bvr-drop-m": "the radius kernels leave out the term of the largest magnitude m",
    "bvr-nan-overflow": "the radius kernels return a NaN where the radius overflows",
    "bvr-pow2-grow-exact": "bv_mul_pow2_radius grows the radius by two steps even when ex and "
                           "its own condition hold",
    "bvr-pow2-unless": "bv_mul_pow2_radius keeps the product rx c without its two steps when ex "
                       "is false",
    "bvr-conv-no-g": "conv_radius leaves out the term g m (1+u)^2 ma mb",
    "bvs-flag-inverted": "the steps of the scalings return the mask e inverted",
    "bvs-flag-true": "the steps of the scalings return the mask e true whatever the operands",
    "bvc-negate-not": "neg_1 returns its operand unchanged",
    "bvc-make-zero": "bv_make_radius returns +0 for every radius",
    "bvc-center2-tail": "bv_center_2 drops the second limb",
    "bvf-nonneg-ignored": "bv_make_finish does not test the sign of the radius",
    "bvf-one-mask": "bv_conv_finish tests its first mask only",
    # The accumulator.
    "acc-b-signed": "the accumulator adds x (x y) to the sum of magnitudes, not its magnitude",
    "acc-b-overflow-omega": "the accumulator's sum of magnitudes gives Omega where it overflows",
    "acc-radius-ok-true": "acc_radius_k returns the mask ok true for every count",
    "acc-radius-no-t": "acc_radius_k leaves out the absolute term t",
}

ORACLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BV_CLAIMS = os.path.join(ORACLE_DIR, "selftest", "claims-wave8.json")

ARITY = {"bv_add_radius_1": 3, "bv_add_radius_2": 3, "bv_scale_radius_1": 3,
         "bv_scale_radius_2": 3, "bv_mul_pow2_radius": 4, "conv_radius": 7,
         "bv_mul_pow2_step_1": 2, "bv_mul_pow2_step_2": 3, "bv_center_entry_1": 1,
         "bv_center_2": 2, "neg_1": 1, "bv_neg_radius": 2, "bv_make_radius": 2,
         "bv_make_finish": 2, "bv_conv_finish": 3,
         "acc_add_1": 3, "acc_add_2": 5, "acc_mul_1": 4, "acc_mul_2": 7, "acc_merge_1": 4,
         "acc_merge_2": 6, "acc_radius_1": 4, "acc_radius_2": 4}
MASK_INPUTS = {"bv_mul_pow2_radius": (1,), "bv_make_finish": (1,), "bv_conv_finish": (1, 2)}


def _lt(a, b):
    """a < b as IEEE compares (ints are numbers, floats the values that are not finite)."""
    if (type(a) is float and a != a) or (type(b) is float and b != b):
        return False
    if type(a) is type(b):
        return a < b
    if type(a) is float:
        return a < 0
    return b > 0


def _le(a, b):
    if (type(a) is float and a != a) or (type(b) is float and b != b):
        return False
    return not _lt(b, a)


def _eq(a, b):
    if (type(a) is float and a != a) or (type(b) is float and b != b):
        return False
    return a == b


def _abs(a):
    return abs(a)


class BvKernels:
    """Methods installed on refrun.Kernels."""

    # -- constants ------------------------------------------------------------------------------
    def _bv_unit(self, kname):
        """(unit, tiny) of kernel K: c u^k and t eta of its error entry in the bv claims."""
        from . import refrun as R
        key = ("bvunit", kname)
        v = self._consts.get(key)
        if v is None:
            path = getattr(self, "bv_claims", None) or DEFAULT_BV_CLAIMS
            cc, k, t = R.center_bound(kname, path)
            A = self.A
            u = Fraction(1, 1 << A.p)
            eta = Fraction(1, 1 << -A.qmin) if A.qmin < 0 else Fraction(1 << A.qmin)
            v = self._consts[key] = (R._eval_rational(cc, u) * u ** k, t * eta)
        return v

    def _up(self, f):
        """const up(f): the smallest number of the format not below the rational value f."""
        return self._const_up(Fraction(f))

    def _uv(self):
        A = self.A
        u = Fraction(1, 1 << A.p)
        eta = Fraction(1, 1 << -A.qmin) if A.qmin < 0 else Fraction(1 << A.qmin)
        return u, eta

    # -- the radii ------------------------------------------------------------------------------
    def _add_radius(self, m, rx, ry, kname, factor):
        A = self.A
        u, eta = self._uv()
        unit = self._bv_unit(kname)[0]
        U = unit / (1 - unit) * ((1 + u) if factor else 1)
        s = A.add(rx, ry)
        t = s if self.v == "bvr-drop-m" else A.fma(m, self._up(U), s)
        rz = A.fma(t, self._up((1 + u) ** 3),
                   self._up((1 + u) * ((1 + u) ** 2 * eta + eta / 2) + eta / (2 * u)))
        return (self._bvr_out(rz),)

    def _bvr_out(self, rz):
        if self.v == "bvr-nan-overflow" and rz == INF:
            return NAN
        return rz

    def bv_add_radius_1(self, m, rx, ry):
        return self._add_radius(m, rx, ry, "add_1_1", False)

    def bv_add_radius_2(self, m, rx, ry):
        return self._add_radius(m, rx, ry, "add_2_2", True)

    def _scale_radius(self, m, rx, a, kname, factor):
        A = self.A
        u, eta = self._uv()
        unit, tiny = self._bv_unit(kname)
        U = unit / (1 - unit) * ((1 + u) if factor else 1)
        V = tiny / (1 - unit)
        aa = _abs(a)
        p = A.prod(aa, rx)
        t = p if self.v == "bvr-drop-m" else A.fma(m, self._up(U), p)
        rz = A.fma(t, self._up((1 + u) ** 3),
                   self._up((1 + u) * ((1 + u) ** 2 * eta + V + eta / 2) + eta / (2 * u)))
        return (self._bvr_out(rz),)

    def bv_scale_radius_1(self, m, rx, a):
        return self._scale_radius(m, rx, a, "mul_1_1", False)

    def bv_scale_radius_2(self, m, rx, a):
        return self._scale_radius(m, rx, a, "mul_2_1", True)

    def bv_mul_pow2_radius(self, m, ex, rx, c):
        A = self.A
        u, eta = self._uv()
        N = self._up(eta / (2 * u))
        rr = A.prod(rx, c)
        br = _lt(N, rr)
        zr = _eq(rx, 0)
        er = br or zr
        q = bool(ex) and er
        su = A.next_up(rr)
        rw = A.next_up(su)
        if self.v == "bvr-pow2-grow-exact":
            q = False
        if self.v == "bvr-pow2-unless" and not ex:
            q = True
        rs = rr if q else rw
        d = A.sub(m, m)
        rz = A.add(rs, d)
        return (self._bvr_out(rz),)

    def conv_radius(self, ma, mb, rx, ry, m, g, t):
        A = self.A
        u, eta = self._uv()
        p = A.prod(rx, ry)
        q = A.fma(mb, rx, p)
        w = A.fma(ma, ry, q)
        ab = A.prod(ma, mb)
        e = w if self.v == "bvr-conv-no-g" else A.fma(ab, g, w)
        if self.v == "bvr-drop-m":
            # The largest magnitudes left out: the radii alone.
            e = p
        s = A.fma(m, e, t)
        hm = A.prod(m, self._up(4 * (1 + u) ** 8 * eta + eta / (2 * u)))
        rz = A.fma(s, self._up((1 + u) ** 7), hm)
        return (self._bvr_out(rz),)

    # -- the steps of the scalings by a power of two ----------------------------------------------
    def _flag(self, e):
        if self.v == "bvs-flag-inverted":
            return not e
        if self.v == "bvs-flag-true":
            return True
        return e

    def bv_mul_pow2_step_1(self, x, c):
        A = self.A
        u, eta = self._uv()
        z = A.prod(x, c)
        am = _abs(z)
        bc = _lt(self._up(eta / (2 * u)), am)
        zc = _eq(x, 0)
        return (z, self._flag(bc or zc))

    def bv_mul_pow2_step_2(self, x0, x1, c):
        A = self.A
        u, eta = self._uv()
        h = A.prod(x0, c)
        lo = A.prod(x1, c)
        z0, z1 = self.fast_two_sum(h, lo)
        ze = _eq(x1, 0)
        mm = h if ze else lo
        am = _abs(mm)
        bc = _lt(self._up(eta / (2 * u)), am)
        zc = _eq(x0, 0)
        return (z0, z1, self._flag(bc or zc))

    # -- the copies, negations and constructors ---------------------------------------------------
    def bv_center_entry_1(self, c):
        return (self.guard(c),)

    def bv_center_2(self, x0, x1):
        if self.v == "bvc-center2-tail":
            return (x0, 0)
        return (x0, x1)

    def neg_1(self, x):
        if self.v == "bvc-negate-not":
            return (x,)
        return (-x if type(x) is int else -x,)

    def bv_neg_radius(self, m, rx):
        return (rx,)

    def bv_make_radius(self, m, r):
        A = self.A
        g = self.guard(r)
        d = A.sub(m, m)
        rz = A.add(g, d)
        if self.v == "bvc-make-zero":
            rz = 0
        return (rz,)

    def bv_make_finish(self, rz, ok):
        p = _le(0, rz)
        if self.v == "bvf-nonneg-ignored":
            p = True
        q = bool(ok) and p
        return self.norm_finish_1(rz, q)

    def bv_conv_finish(self, rz, okc, okg):
        q = bool(okc) and (bool(okg) or self.v == "bvf-one-mask")
        return self.norm_finish_1(rz, q)

    # -- the accumulator -----------------------------------------------------------------------
    def _acc_b(self, a, mag, signed):
        A = self.A
        b = A.add(a, signed if self.v == "acc-b-signed" else mag)
        if self.v == "acc-b-overflow-omega" and b == INF:
            b = A.omega
        return b

    def acc_add_1(self, s, a, x):
        A = self.A
        g = self.guard(x)
        t = A.add(s, g)
        return (t, self._acc_b(a, _abs(g), g))

    def acc_add_2(self, s0, s1, a, x0, x1):
        g0, g1 = self.guard(x0), self.guard(x1)
        t0, t1 = self.add_2_2(s0, s1, g0, g1)
        return (t0, t1, self._acc_b(a, _abs(g0), g0))

    def _acc_mul_b(self, ax, ay, a, x, y):
        A = self.A
        if self.v == "acc-b-signed":
            b = A.fma(x, y, a)
        else:
            b = A.fma(ax, ay, a)
        if self.v == "acc-b-overflow-omega" and b == INF:
            b = A.omega
        return b

    def acc_mul_1(self, s, a, x, y):
        A = self.A
        t = A.fma(x, y, s)
        return (t, self._acc_mul_b(_abs(x), _abs(y), a, x, y))

    def acc_mul_2(self, s0, s1, a, x0, x1, y0, y1):
        t0, t1 = self.dot_step_2(s0, s1, x0, x1, y0, y1)
        return (t0, t1, self._acc_mul_b(_abs(x0), _abs(y0), a, x0, y0))

    def acc_merge_1(self, s, a, v, c):
        A = self.A
        t = A.add(s, v)
        return (t, self._acc_b(a, c, c))

    def acc_merge_2(self, s0, s1, a, v0, v1, c):
        t0, t1 = self.add_2_2(s0, s1, v0, v1)
        return (t0, t1, self._acc_b(a, c, c))

    def acc_radius_1(self, a, m, g, t):
        A = self.A
        u, eta = self._uv()
        N = eta / (2 * u)
        q = A.prod(m, self._up((1 + u) * u + N))
        d = A.prod(q, self._up(2))
        w = A.fma(q, d, q)
        c = A.fma(m, self._up(N), a)
        e = A.fma(c, w, c)
        f = A.prod(e, g)
        s = f if self.v == "acc-radius-no-t" else A.add(f, t)
        r = A.fma(s, self._up((1 + u) ** 8), self._up((1 + u) ** 7 * eta / 2 + N))
        oq = _le(d, self._up(1))
        z = A.sub(a, a)
        fa = _eq(z, z)
        ok = oq and fa
        if self.v == "acc-radius-ok-true":
            ok = True
        return (r, ok)

    def acc_radius_2(self, a, m, g, t):
        return self.acc_radius_1(a, m, g, t)




# ---------------------------------------------------------------------------
# The ball vectors (architecture.md, "Ball vectors"): a map of the centers whose state is that of
# a fold of maxima of the centers written, its finish the one radius; when the flag is false a
# second pass writes every center zero and the radius is +inf, the whole space.

# name: (step, its operands by position (("s", i) scalar i, ("a", 0) the entry), limbs, the
# scalars, the radius kernel, its arguments after m (("ex",) the mask of exactness, ("s", i)), the
# finish).
BVS = {
    "bv_add_1": ("add_1_1", (("a", 0), ("a", 1)), 1, 2, "bv_add_radius_1", (("s", 0), ("s", 1)),
                 "norm_finish_1"),
    "bv_add_2": ("add_2_2", (("a", 0), ("a", 1)), 2, 2, "bv_add_radius_2", (("s", 0), ("s", 1)),
                 "norm_finish_1"),
    "bv_sub_1": ("sub_1_1", (("a", 0), ("a", 1)), 1, 2, "bv_add_radius_1", (("s", 0), ("s", 1)),
                 "norm_finish_1"),
    "bv_sub_2": ("sub_2_2", (("a", 0), ("a", 1)), 2, 2, "bv_add_radius_2", (("s", 0), ("s", 1)),
                 "norm_finish_1"),
    "bv_scale_1": ("scale_step_1", (("a", 0), ("s", 1)), 1, 2, "bv_scale_radius_1",
                   (("s", 0), ("s", 1)), "norm_finish_1"),
    "bv_scale_2": ("scale_step_2", (("a", 0), ("s", 1)), 2, 2, "bv_scale_radius_2",
                   (("s", 0), ("s", 1)), "norm_finish_1"),
    "bv_neg_1": ("neg_1", (("a", 0),), 1, 1, "bv_neg_radius", (("s", 0),), "norm_finish_1"),
    "bv_neg_2": ("neg_2", (("a", 0),), 2, 1, "bv_neg_radius", (("s", 0),), "norm_finish_1"),
    "bv_mul_pow2_1": ("bv_mul_pow2_step_1", (("a", 0), ("s", 1)), 1, 2, "bv_mul_pow2_radius",
                      (("ex",), ("s", 0), ("s", 1)), "norm_finish_1"),
    "bv_mul_pow2_2": ("bv_mul_pow2_step_2", (("a", 0), ("s", 1)), 2, 2, "bv_mul_pow2_radius",
                      (("ex",), ("s", 0), ("s", 1)), "norm_finish_1"),
    "bv_make_1": ("bv_center_entry_1", (("a", 0),), 1, 1, "bv_make_radius", (("s", 0),),
                  "bv_make_finish"),
    "bv_make_2": ("bv_center_2", (("a", 0),), 2, 1, "bv_make_radius", (("s", 0),),
                  "bv_make_finish"),
}
# The number of arrays read of each.
BV_ARRAYS = {k: 1 + any(a == ("a", 1) for a in v[1]) for k, v in BVS.items()}
BVCONVS = {"bv_conv_1": ("conv_1", "bound_dot_1", 1), "bv_conv_2": ("conv_2", "bound_dot_2", 2)}

FOLD_VARIANTS = {
    "bv-radius-no-m": "the ball vectors compute their radius at the largest magnitude +0",
    "bv-whole-omega": "the ball vectors return the whole space as zero centers and the radius Omega",
    "bv-flag-true": "the ball vectors return the flag true whatever the radius",
    "bv-no-second-pass": "the ball vectors keep their centers as computed when the flag is false",
    "bv-drop-last": "the ball vectors leave their last center zero",
    "bv-lanes-swap": "the ball vectors in a lane order of two lanes or more write the centers of "
                     "lanes 0 and 1 of each block in each other's place",
    "bv-spurious-whole": "the ball vectors return the whole space when a center written is above "
                         "2^(emax-8) in magnitude",
    "bv-not-exact": "bv_neg_k and bv_mul_pow2_k return their radius one step up",
    "bv-make-negative": "the constructors keep a negative radius",
    "bv-make-nan-finite": "the constructors keep a NaN radius with finite centers",
    "bvc-drop-term": "each coefficient of a product of BallVectors leaves out its last term",
    "bvc-radius-no-rr": "the product of BallVectors computes its radius with ry = 0",
    "bvc-bound-false": "the product of BallVectors takes the bound's mask false for every count",
    "bvc-flag-true": "the product of BallVectors returns the flag true whatever the radius",
}


class BvFolds:
    """The folds of the ball vectors, installed on refrun.Kernels."""

    def ball_vector(self, name, order, scalars, elems):
        """(centers written, radius, flag) of a ball vector in an order (None for the sequential
        one, W for the lanes): the step on each entry, the record of the largest magnitude of a
        leading limb written (and the and of the step's masks), the radius, the finish."""
        step, args, k, _ns, radius, rargs, finish = BVS[name]
        v = self.v
        A = self.A
        out, masks = [], []
        for e in elems:
            ops = []
            for where, j in args:
                ops.extend([scalars[j]] if where == "s" else e[j])
            res = list(getattr(self, step)(*ops))
            out.append(res[:k])
            masks.append(bool(res[k]) if len(res) > k else True)
        if v == "bv-drop-last" and out:
            out[-1] = [0] * k
        if v == "bv-lanes-swap" and order is not None and order >= 2:
            for b in range(0, order * (len(out) // order), order):
                out[b], out[b + 1] = out[b + 1], out[b]
        rec = self.norm_step_1 if k == 1 else (lambda m, ok, *z: self.norm_step_2(m, ok, *z))

        def run(state, zs):
            m, ok, ex = state
            for z, e in zs:
                m, ok = rec(m, ok, *z)
                ex = ex and e
            return (m, ok, ex)
        pairs = list(zip(out, masks))
        n = len(pairs)
        zero = (0, True, True)
        if order is None or order <= 1:
            m, ok, ex = run(zero, pairs)
        else:
            W = order
            full = W * (n // W)
            lanes = [run(zero, pairs[j:full:W]) for j in range(W)]
            s = lanes[0]
            for l in lanes[1:]:
                mm, oo = self.norm_combine(s[0], s[1], l[0], l[1])
                s = (mm, oo, s[2] and l[2])
            m, ok, ex = run(s, pairs[full:])
        if v == "bv-radius-no-m":
            m = 0
        ra = [m]
        for a in rargs:
            ra.append(ex if a == ("ex",) else scalars[a[1]])
        rz = getattr(self, radius)(*ra)[0]
        if v == "bv-not-exact" and name.startswith(("bv_neg", "bv_mul_pow2")) and type(rz) is int:
            rz = A.next_up(rz)
        r, flag = getattr(self, finish)(rz, ok)
        if v == "bv-spurious-whole" and any(type(z[0]) is int and abs(z[0]) > 1 << max(
                0, A.qmax + A.p - 1 - 8 - A.qmin) for z in out):
            flag = False
        if v == "bv-make-negative" and name.startswith("bv_make") and type(scalars[0]) is int \
                and scalars[0] < 0 and ok:
            r, flag = scalars[0], True
        if v == "bv-make-nan-finite" and name.startswith("bv_make") and scalars[0] != scalars[0] \
                and ok:
            r, flag = NAN, True
        if not flag:
            if v == "bv-whole-omega":
                return [[0] * k for _ in out], A.omega, True
            if v != "bv-no-second-pass":
                out = [[0] * k for _ in out]
            r = INF
        if v == "bv-flag-true":
            flag = True
        return out, r, flag

    def bv_product(self, name, rx, ry, xs, ys):
        """(coefficients, radius, flag) of a product of two BallVectors: the convolution of the
        centers (its mask), the maxima of the operands' leading limbs, the count rounded up, the
        bound of dot, conv_radius, the finish."""
        conv, bound, k = BVCONVS[name]
        v = self.v
        A = self.A
        nx, ny = len(xs), len(ys)
        nz = nx + ny - 1 if nx and ny else 0
        fold = "dot_1" if k == 1 else "dot_2"
        check = self.fold_finish_1 if k == 1 else self.fold_finish_2
        out = []
        for j in range(nz):
            terms = [(i, j - i) for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1)]
            if v == "bvc-drop-term" and terms:
                terms = terms[:-1]
            out.append(list(self.fold(fold, None, [tuple(xs[i]) + tuple(ys[t]) for i, t in terms],
                                      raw=True)))
        finite = True
        for z in out:
            finite = check(*z)[-1] and finite
        rec = self.norm_step_1 if k == 1 else (lambda m, ok, *z: self.norm_step_2(m, ok, *z))
        ma, oka = 0, True
        for x in xs:
            ma, oka = rec(ma, oka, *x)
        mb, okb = 0, True
        for y in ys:
            mb, okb = rec(mb, okb, *y)
        n = min(nx, ny)
        per = Fraction(1 << -A.qmin) if A.qmin < 0 else Fraction(1, 1 << A.qmin)
        m = A.round_up_fraction(Fraction(n) * per) if n else 0
        g, t, okg = self._bound(bound, m)
        if v == "bvc-bound-false":
            okg = False
        rz = self.conv_radius(ma, mb, rx, 0 if v == "bvc-radius-no-rr" else ry, m, g, t)[0]
        r, flag = self.bv_conv_finish(rz, finite, okg)
        if not flag:
            out = [[0] * k for _ in out]
            r = INF
        if v == "bvc-flag-true":
            flag = True
        return out, r, flag


def bv_line(R, line, toks, tag):
    """BV FORMAT ORDER N [inplace=I] SCALAR... LIMB... [#TAG] -> Z... R FLAG (the in-place field
    changes nothing that is computed)."""
    name, fname, order, n = toks[0], toks[1], toks[2], int(toks[3])
    K = R.kernels(fname)
    A = K.A
    rest = toks[4:]
    if rest and rest[0].startswith("inplace="):
        rest = rest[1:]
    _step, _args, k, ns, _r, _ra, _f = BVS[name]
    na = BV_ARRAYS[name]
    if len(rest) != ns + n * na * k:
        raise ValueError("cannot run %r with %d limbs for %d entries" % (name, len(rest), n))
    vals = [A.read(t) for t in rest]
    scalars = vals[:ns]
    cols = [vals[ns + j * n:ns + (j + 1) * n] for j in range(na * k)]
    elems = [[[cols[a * k + t][i] for t in range(k)] for a in range(na)] for i in range(n)]
    W = None if order == "seq" else int(order[6:])
    out, r, flag = K.ball_vector(name, W, scalars, elems)
    res = [A.write(z[t]) for t in range(k) for z in out] + [A.write(r), "1" if flag else "0"]
    return [line + " -> " + " ".join(res)]


def bvconv_line(R, line, toks, tag):
    """BV_CONV FORMAT seq N_X N_Y RX RY LIMB... [#TAG] -> Z... R FLAG."""
    name, fname, nx, ny = toks[0], toks[1], int(toks[3]), int(toks[4])
    K = R.kernels(fname)
    A = K.A
    k = BVCONVS[name][2]
    vals = [A.read(t) for t in toks[5:]]
    rx, ry = vals[0], vals[1]
    base = 2
    xs = [[vals[base + t * nx + i] for t in range(k)] for i in range(nx)]
    base += nx * k
    ys = [[vals[base + t * ny + i] for t in range(k)] for i in range(ny)]
    out, r, flag = K.bv_product(name, rx, ry, xs, ys)
    res = [A.write(z[t]) for t in range(k) for z in out] + [A.write(r), "1" if flag else "0"]
    return [line + " -> " + " ".join(res)]


def install(R):
    """Add the kernels and folds to refrun.Kernels, their arities and mask inputs to refrun's
    tables, and the variants to refrun.VARIANTS."""
    for cls in (BvKernels, BvFolds):
        for name, fn in vars(cls).items():
            if callable(fn) and not name.startswith("__"):
                setattr(R.Kernels, name, fn)
    R.ARITY.update(ARITY)
    R.MASK_INPUTS.update(MASK_INPUTS)
    R.VARIANTS.update(VARIANTS)
    R.VARIANTS.update(FOLD_VARIANTS)
