"""The reference runner's kernels of the round-up interval: the 24 listings of
docs/developer/design/upward.md ("The kernels"), one operation per statement and a pair line as its
two statements, lane 0 first, on IEEE values (refrun.Arith reads and writes the literals; finite
values are integers N meaning N * eta, the non-finite ones Python's inf and nan).  install() adds
them to refrun.Kernels and their variants to refrun.VARIANTS.

The four operations of the page are computed here, from IEEE 754's rules and exact integers,
without the checker's code:

- add_ru, mul_ru: the exact sum or product rounded toward +inf in the format with overflow: the
  smallest number of the format not below the exact value, +inf above Omega, -Omega below -Omega; a
  NaN for a NaN operand, inf - inf and 0 * inf; an infinite operand otherwise gives the infinity of
  IEEE 754 (the sign of a zero result is not modelled: one zero, which no claim distinguishes);
- unord: a NaN test of either operand;
- max_nl: in the form the runner names (refrun --max): sel, x86's MAXPD, a if b < a else b (the
  second operand when either is a NaN or both are zeros); nm, arm64's FMAXNM on quiet NaNs, the
  other operand when exactly one is a NaN, otherwise the greater.

The comparisons are IEEE's (false on a NaN), the selections are lane by lane.  The rounding is the
smallest number not below the value found from the spacing of the format at the value (the
checker's fmt.rdir shifts and inspects the dropped bits, the selftest's definition walks the sorted
numbers of the format); up_arithmetic compares all three.

Variants plant one fault each (VARIANTS below), for the selftest (selftest_up.py).
"""

import math

INF = math.inf
NINF = -math.inf
NAN = math.nan

VARIANTS = {
    "up-mul-step-small": "upward_mul_1 one step wider on each side where a product of finite "
                         "bounds is nonzero and below P = 2^(2p-1) eta (as wide as the default "
                         "product may be there)",
    "up-empty-nonempty": "upward_add_1 and upward_sub_1 return the empty set when an operand "
                         "has a zero bound",
    "up-hull-one-select": "upward_hull_1 without the selection of lane 1: with the MAXPD form an "
                          "empty x gives one NaN lane",
    "up-lane-neg-inf": "upward_from_interval_1 without its test of the empty set: the default "
                       "empty set (+inf, -inf) becomes (-inf, -inf)",
    "up-crossed": "upward_intersection_1 without the test of crossed lanes",
    "up-lower-not-negated": "upward_to_interval_1 returns the lane n as the lower bound, not "
                            "negated",
    "up-number-point": "upward_add_num_1 and upward_mul_num_1 without the selection of a number "
                       "that is not finite: t = +inf, -inf or NaN treated as a point",
    "up-add-nearest": "upward_add_1 rounds its lanes to nearest",
    "up-mul-negated": "upward_mul_1's lane 1 the negation of the rounded product, -RU(p), in place "
                      "of RU(-p)",
    "up-mul-nan-seed": "upward_mul_1 without the seed's NaN lanes made +0: 0 * inf a NaN "
                       "candidate",
    "up-mul-empty-kept": "upward_mul_1 without its last selection (an empty operand)",
    "up-subset-empty": "upward_subset_1 without the test of an empty x",
    "up-less-not-negated": "upward_less_1 compares xu with yn without its negation",
    "up-contains-infinite": "upward_contains_1 without the test that t is finite",
    "up-make-crossed": "upward_make_1 returns (hi, -lo) for reversed bounds: crossed lanes",
    "up-zero-signs": "every zero output written -0x0p+0 (no claim is about the sign of a zero: "
                     "nothing may fail)",
}

ARITY = {"upward_add_1": 4, "upward_sub_1": 4, "upward_neg_1": 2, "upward_mul_1": 4,
         "upward_add_num_1": 3, "upward_mul_num_1": 3, "upward_hull_1": 4,
         "upward_intersection_1": 4, "upward_make_1": 2, "upward_from_interval_1": 2,
         "upward_to_interval_1": 2, "upward_empty_1": 2, "upward_entire_1": 2,
         "upward_contains_1": 3, "upward_subset_1": 4, "upward_positive_1": 2,
         "upward_negative_1": 2, "upward_zero_1": 2, "upward_less_1": 4, "upward_less_equal_1": 4,
         "upward_equal_1": 4, "upward_rel_equal_1": 4, "upward_rel_interior_1": 4,
         "upward_rel_disjoint_1": 4}
KERNELS = tuple(ARITY)
MAX_FORMS = ("sel", "nm")


def _nan(v):
    return v != v


def _finite(v):
    return type(v) is int


class UpArith:
    """The operations of the page's IR in one format (an refrun.Arith for its constants)."""

    def __init__(self, A, max_form):
        if max_form not in MAX_FORMS:
            raise ValueError("unknown form of max_nl %r (sel or nm)" % max_form)
        self.A = A
        self.p, self.qmin, self.omega = A.p, A.qmin, A.omega
        self.max_form = max_form

    def ru(self, n, extra):
        """n * 2^(-extra) eta (extra >= 0) rounded toward +inf, in the format with overflow."""
        if n == 0:
            return 0
        a = -n if n < 0 else n
        # The spacing of the format at |v|, in units of 2^(-extra) eta: eta in the subnormal range
        # (and from it to the smallest normal binade), 2^(e - p + 1) eta in the binade of 2^e.
        k = max(a.bit_length() - self.p, extra)
        m = a >> k
        if n > 0:
            if m << k != a:
                m += 1                          # up: away from zero for a positive value
            r = (m << k) >> extra
            return INF if r > self.omega else r
        r = -((m << k) >> extra)                # up: toward zero for a negative value
        return -self.omega if r < -self.omega else r

    def rn(self, n, extra):
        """To nearest, ties to even (the variant up-add-nearest only)."""
        return self.A.round(n, extra)

    def add_ru(self, a, b):
        if _nan(a) or _nan(b):
            return NAN
        if not _finite(a) or not _finite(b):
            if not _finite(a) and not _finite(b) and a != b:
                return NAN
            return a if not _finite(a) else b
        return self.ru(a + b, 0)

    def mul_ru(self, a, b):
        if _nan(a) or _nan(b):
            return NAN
        if not _finite(a) or not _finite(b):
            if a == 0 or b == 0:
                return NAN
            return INF if (a > 0) == (b > 0) else NINF
        if self.qmin < 0:
            return self.ru(a * b, -self.qmin)
        return self.ru((a * b) << self.qmin, 0)

    @staticmethod
    def unord(a, b):
        return _nan(a) or _nan(b)

    def max_nl(self, a, b):
        if self.max_form == "sel":
            return a if b < a else b            # MAXPD a, b: b when either is a NaN
        if _nan(a) and _nan(b):
            return NAN
        if _nan(a):
            return b
        if _nan(b):
            return a
        return a if a > b else b


def _sel(m, a, b):
    return a if m else b


class UpKernels:
    """The listings of upward.md, methods of refrun.Kernels (install)."""

    def _upw_arith(self):
        U = getattr(self, "_uparith", None)
        form = getattr(self, "max_form", "sel")
        if U is None or U.max_form != form:
            U = self._uparith = UpArith(self.A, form)
        return U

    # -- sum, difference, negation -----------------------------------------------------------
    def upward_add_1(self, xu, xn, yu, yn):
        U = self._upw_arith()
        if self.v == "up-add-nearest" and all(_finite(v) for v in (xu, xn, yu, yn)):
            return U.rn(xu + yu, 0), U.rn(xn + yn, 0)
        zu, zn = U.add_ru(xu, yu), U.add_ru(xn, yn)
        if self.v == "up-empty-nonempty" and 0 in (xu, xn, yu, yn) and not U.unord(zu, zn):
            return NAN, NAN
        return zu, zn

    def upward_sub_1(self, xu, xn, yu, yn):
        U = self._upw_arith()
        zu, zn = U.add_ru(xu, yn), U.add_ru(xn, yu)
        if self.v == "up-empty-nonempty" and 0 in (xu, xn, yu, yn) and not U.unord(zu, zn):
            return NAN, NAN
        return zu, zn

    def upward_neg_1(self, xu, xn):
        return xn, xu

    # -- the product -------------------------------------------------------------------------
    def upward_mul_1(self, xu, xn, yu, yn):
        U = self._upw_arith()
        v = self.v
        nyu, nyn = -yu, -yn
        q1u, q1n = U.mul_ru(xu, yu), U.mul_ru(xn, yu)
        q2u, q2n = U.mul_ru(xn, yn), U.mul_ru(xu, yn)
        q3u, q3n = U.mul_ru(xn, nyu), U.mul_ru(xu, nyu)
        q4u, q4n = U.mul_ru(xu, nyn), U.mul_ru(xn, nyn)
        if v == "up-mul-negated":
            # -RU(p) for the products of lane 1 (rule U3's fault): RU(a d) negated, ...
            q1n, q2n = _neg(U.mul_ru(_neg(xn), yu)), _neg(U.mul_ru(_neg(xu), yn))
            q3n, q4n = _neg(U.mul_ru(_neg(xu), nyu)), _neg(U.mul_ru(_neg(xn), nyn))
        e1u, e1n = U.unord(q1u, q1u), U.unord(q1n, q1n)
        if v == "up-mul-nan-seed":
            m1u, m1n = q1u, q1n
        else:
            m1u, m1n = _sel(e1u, 0, q1u), _sel(e1n, 0, q1n)
        m2u, m2n = U.max_nl(q2u, m1u), U.max_nl(q2n, m1n)
        m3u, m3n = U.max_nl(q3u, m2u), U.max_nl(q3n, m2n)
        m4u, m4n = U.max_nl(q4u, m3u), U.max_nl(q4n, m3n)
        eu, en = U.unord(xu, yu), U.unord(xn, yn)
        if v == "up-mul-empty-kept":
            zu, zn = m4u, m4n
        else:
            zu, zn = _sel(eu, NAN, m4u), _sel(en, NAN, m4n)
        if v == "up-mul-step-small" and _finite(zu) and _finite(zn) and self._upw_small_product(
                xu, xn, yu, yn):
            # One step outward on each side (next_up of a lane), where both stay finite: the
            # result is as bounded as before, one number wider.
            wu, wn = self.A.next_up(zu), self.A.next_up(zn)
            if _finite(wu) and _finite(wn):
                zu, zn = wu, wn
        return zu, zn

    def _upw_small_product(self, xu, xn, yu, yn):
        """Some product of a finite bound of x and a finite bound of y is nonzero and below
        P = 2^(2p-1) eta in magnitude (the region where the default product may be wider)."""
        A = self.A
        xs = [b for b in (xu, _neg(xn)) if _finite(b)]
        ys = [b for b in (yu, _neg(yn)) if _finite(b)]
        # Products of fixed values are in units of eta^2: P = 2^(2p-1) eta = 2^(2p-1-qmin) of
        # them (below 1 when qmin > 2p - 1: no nonzero product is then below P).
        e = 2 * A.p - 1 - A.qmin
        if e < 0:
            return False
        return any(a * b != 0 and abs(a * b) < (1 << e) for a in xs for b in ys)

    # -- operations with a number -----------------------------------------------------------
    def upward_add_num_1(self, xu, xn, t):
        U = self._upw_arith()
        nt = _neg(t)
        su, sn = U.add_ru(xu, t), U.add_ru(xn, nt)
        wu, wn = U.add_ru(xu, INF), U.add_ru(xn, INF)
        at = abs(t)
        ft = at < INF
        if self.v == "up-number-point":
            ft = True
        return _sel(ft, su, wu), _sel(ft, sn, wn)

    def upward_mul_num_1(self, xu, xn, t):
        U = self._upw_arith()
        nt = _neg(t)
        p1u, p1n = U.mul_ru(xu, t), U.mul_ru(xn, t)
        p2u, p2n = U.mul_ru(xn, nt), U.mul_ru(xu, nt)
        e1u, e1n = U.unord(p1u, p1u), U.unord(p1n, p1n)
        m1u, m1n = _sel(e1u, 0, p1u), _sel(e1n, 0, p1n)
        mu, mn = U.max_nl(p2u, m1u), U.max_nl(p2n, m1n)
        eu, en = U.unord(xu, xu), U.unord(xn, xn)
        fu, fn = _sel(eu, NAN, mu), _sel(en, NAN, mn)
        axu, axn = abs(xu), abs(xn)
        su, sn = U.add_ru(axu, axn), U.add_ru(axn, axu)
        gu, gn = 0 < su, 0 < sn
        wu, wn = _sel(gu, INF, su), _sel(gn, INF, sn)
        at = abs(t)
        ft = at < INF
        if self.v == "up-number-point":
            ft = True
        return _sel(ft, fu, wu), _sel(ft, fn, wn)

    # -- hull and intersection --------------------------------------------------------------
    def upward_hull_1(self, xu, xn, yu, yn):
        U = self._upw_arith()
        eu, en = U.unord(xu, xu), U.unord(xn, xn)
        tu, tn = U.max_nl(yu, xu), U.max_nl(yn, xn)
        if self.v == "up-hull-one-select":
            return _sel(eu, yu, tu), tn
        return _sel(eu, yu, tu), _sel(en, yn, tn)

    def upward_intersection_1(self, xu, xn, yu, yn):
        U = self._upw_arith()
        mu, mn = yu < xu, yn < xn
        lu, ln = _sel(mu, yu, xu), _sel(mn, yn, xn)
        nu, nn = _neg(lu), _neg(ln)
        cu, cn = lu < nn, ln < nu
        eu, en = U.unord(xu, yu), U.unord(xn, yn)
        if self.v == "up-crossed":
            cu = cn = False
        bu, bn = eu or cu, en or cn
        return _sel(bu, NAN, lu), _sel(bn, NAN, ln)

    # -- constructor and conversions --------------------------------------------------------
    def upward_make_1(self, lo, hi):
        ok = lo <= hi
        nl = lo < INF
        mi = _neg(INF)
        nu = mi < hi
        va = ok and nl
        v = va and nu
        rv = hi < lo
        nlo = _neg(lo)
        ou, on = _sel(rv, NAN, INF), _sel(rv, NAN, INF)
        if self.v == "up-make-crossed" and rv:
            return hi, nlo
        return _sel(v, hi, ou), _sel(v, nlo, on)

    def upward_from_interval_1(self, xl, xu):
        e = xl == INF
        nl = _neg(xl)
        if self.v == "up-lane-neg-inf":
            e = False
        return _sel(e, NAN, xu), _sel(e, NAN, nl)

    def upward_to_interval_1(self, xu, xn):
        U = self._upw_arith()
        e = U.unord(xu, xu)
        nl = _neg(xn)
        if self.v == "up-lower-not-negated":
            nl = xn
        mi = _neg(INF)
        return _sel(e, INF, nl), _sel(e, mi, xu)

    # -- predicates and comparisons ---------------------------------------------------------
    def upward_empty_1(self, xu, xn):
        return self._upw_arith().unord(xu, xu)

    def upward_entire_1(self, xu, xn):
        return xu == INF and xn == INF

    def upward_contains_1(self, xu, xn, t):
        a = t <= xu
        nt = _neg(t)
        b = nt <= xn
        ft = abs(t) < INF
        if self.v == "up-contains-infinite":
            ft = True
        return a and b and ft

    def upward_subset_1(self, xu, xn, yu, yn):
        ex = self._upw_arith().unord(xu, xu)
        if self.v == "up-subset-empty":
            ex = False
        a = xn <= yn
        b = xu <= yu
        return ex or (a and b)

    def upward_positive_1(self, xu, xn):
        return xn < 0

    def upward_negative_1(self, xu, xn):
        return xu < 0

    def upward_zero_1(self, xu, xn):
        return xn == 0 and xu == 0

    def upward_less_1(self, xu, xn, yu, yn):
        ny, nx = _neg(yn), _neg(xn)
        if self.v == "up-less-not-negated":
            ny = yn
        return xu < ny, yu <= nx

    def upward_less_equal_1(self, xu, xn, yu, yn):
        ny, nx = _neg(yn), _neg(xn)
        return xu <= ny, yu < nx

    def upward_equal_1(self, xu, xn, yu, yn):
        nx, ny = _neg(xn), _neg(yn)
        ea, eb, ec = nx == xu, xu == ny, ny == yu
        yes = ea and eb and ec
        no = xu < ny or yu < nx
        return yes, no

    def upward_rel_equal_1(self, xu, xn, yu, yn):
        U = self._upw_arith()
        c = xu == yu and xn == yn
        ee = U.unord(xu, xu) and U.unord(yu, yu)
        return c or ee

    def upward_rel_interior_1(self, xu, xn, yu, yn):
        ex = self._upw_arith().unord(xu, xu)
        lo = xn < yn or (yn == INF and xn == INF)
        hi = xu < yu or (xu == INF and yu == INF)
        return ex or (lo and hi)

    def upward_rel_disjoint_1(self, xu, xn, yu, yn):
        ee = self._upw_arith().unord(xu, yu)
        nx, ny = _neg(xn), _neg(yn)
        return ee or xu < ny or yu < nx


def _neg(v):
    return -v


def _outputs(fn, neg_zero):
    """A kernel as refrun.Runner calls it: its outputs a tuple (a mask a bool), and with the
    variant up-zero-signs every zero written -0x0p+0."""
    def kernel(self, *args):
        out = fn(self, *args)
        out = out if isinstance(out, tuple) else (out,)
        if self.v == "up-zero-signs":
            out = tuple(neg_zero if type(o) is int and o == 0 else o for o in out)
        return out
    kernel.__name__ = fn.__name__
    kernel.__doc__ = fn.__doc__
    return kernel


def install(R):
    """Add the kernels to refrun.Kernels, their arities to refrun.ARITY and the variants to
    refrun.VARIANTS."""
    for name, fn in vars(UpKernels).items():
        if not callable(fn) or name.startswith("__"):
            continue
        # Nothing of refrun.Kernels is replaced (its helpers and refbv's keep their names).
        if hasattr(R.Kernels, name):
            raise RuntimeError("refup: refrun.Kernels already has %s" % name)
        setattr(R.Kernels, name, _outputs(fn, R.NEG_ZERO) if name in ARITY else fn)
    R.ARITY.update(ARITY)
    R.VARIANTS.update(VARIANTS)
