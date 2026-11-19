"""A reference runner in pure Python for any binary format, toy formats included.

It evaluates the first-wave kernels as written in docs/developer/architecture.md and the
second-wave and Ball kernels as written in docs/developer/design/milestone1.md, one
rounding per line.  It is part of the oracle only to test the oracle, so it avoids the
checker's code on purpose: rounding is computed from the two neighbors of the exact value
(the checker shifts and inspects the dropped bits), succ and pred from the canonical
significand and exponent (the checker from bit lengths of spacings), literals are read with
float.fromhex and printed with float.hex whenever the format fits in binary64 (the checker
has its own exact parser and printer).  A shared bug would let a wrong result pass; two
different implementations that agree, and that agree with hardware on binary64, make that
unlikely.

The Ball kernels need the constants U and V of their center's kernel.  They are computed
here, exactly, from the error bound of that kernel in a claims file (by default the
oracle's first-wave fixture), as architecture.md defines them: U = RU(unit / (1 - unit)),
V = RU(tiny / (1 - unit)) with unit = c u^k and tiny = t eta.

Named variants inject errors that the checker must catch (see VARIANTS).
"""

import ast
import json
import math
import os
import re
import sys
import zlib
from fractions import Fraction

INF = math.inf
NAN = math.nan

VARIANTS = {
    "correct": "the kernels as specified",
    "ulp-rare": "second output limb one ulp too large in about 1 case in 256",
    "not-normalized": "(z0, z1) replaced by (succ z0, z1 - (succ z0 - z0)) when that is exact: "
                      "same value, not normalized",
    "mul-drop-cross": "mul_2_2 drops the cross term x0*y1; mul_2_1 drops x1*a",
    "add-skip-renorm": "additions return their operands of the last fast_two_sum unrenormalized",
    "subnormal-trunc": "every rounding whose exact result is below lambda truncates instead of "
                       "rounding to nearest",
    "two-sum-zero": "two_sum returns e = eta instead of 0 when the sum is exact",
    "corrupt-input": "about 1 line in 64 has an input altered to violate a requirement (marked by "
                     "a comment line)",
    "fast-end-two-sum": "add_fast_2_2 ends with two_sum instead of fast_two_sum (not an error: "
                        "the alternative the exhaustive test decides between)",
    "trace-fast-two-sum": "correct results; before a line, a comment for every fast_two_sum call "
                          "whose first operand is smaller in magnitude than the second",
    # Second wave.
    "cmp-lead-equal": "comparisons wrong only when the first limbs are equal: lt and le swap "
                      "their test on the second limbs, eq ignores them",
    "down-no-neg-step": "to_down_2 forgets the step when the second limb is negative",
    "down-pow2-wrong-side": "to_down_2 at a leading limb that is a power of two steps by the gap "
                            "on the other side of it",
    "radd-no-step": "radd without its final succ",
    "rmul-nearest": "rmul returns the product rounded to nearest",
    "ball-no-center-error": "Ball radii without the term of the center kernel's own error",
    "ball-no-rr": "ball_mul radii without the product of the two radii",
    "ball-pow2-ulp": "Ball radii one unit in the last place too small when the leading limb of "
                     "the center is a power of two",
    "abs-lead-only": "abs_2 negates only the first limb",
    "trace-mul-pow2": "correct results; before a line, a comment when the pair (h, l) of "
                      "mul_pow2_2 is not normalized before its fast_two_sum",
    # The non-finite layer.
    "full-no-fixup": "the full kernels return their core's output, without the fix-up",
    "full-overflow-sign": "the full kernels give the infinity of the wrong sign when the core "
                          "overflows on finite operands",
    "full-overflow-nan": "the full kernels give (NaN, NaN) when the core overflows on finite "
                         "operands",
    "full-overflow-finite": "the full kernels give (+-Omega, 0) when the core overflows on finite "
                            "operands",
    "full-spurious-overflow": "the full kernels give the infinity of t's sign whenever "
                              "|t| >= 2^(qmax+p-3) on finite operands",
    "full-inf-tail-nan": "an infinite result of a full kernel has a NaN second limb",
    "full-inf-tail-eta": "an infinite result of a full kernel has the second limb eta",
    "full-nan-one-limb": "a NaN result of a full kernel has the second limb 0",
    "full-nan-to-zero": "a NaN result of a full kernel becomes (0, 0)",
    "ball-full-swap": "the full Ball kernels swap the empty set and the whole line",
    "ball-full-zero-inf-empty": "the full Ball kernels take q from the computed radius instead of "
                                "the input radii, so 0 * inf gives the empty set",
    "ball-full-finite-whole": "the full Ball kernels keep a finite center and give the radius "
                              "Omega when the computed radius is not finite",
    "make-negative-radius": "ball_make tests the radius for a NaN only, so a negative radius is "
                            "kept",
    "make-nan-radius": "ball_make does not test the radius, so a NaN radius gives the whole line",
    "make2-inf-nan-tail": "make_2 of an infinity has a NaN second limb",
    # The second radius design (with --radius second).
    "ball2-no-E": "second radius design without E: the center kernel's error is left out",
    "ball2-no-H": "second radius design without H: what underflow loses is left out",
    "ball2-G-pred": "second radius design with G one unit in the last place smaller (not an "
                    "error with respect to the claim where the listing has slack)",
    "ball2-H-half": "second radius design with half of H, rounded up (likewise)",
}

ORACLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CENTER_CLAIMS = os.path.join(ORACLE_DIR, "selftest", "claims-wave1.json")

# The kernel of each Ball kernel's center.  For one limb it is one operation of the format,
# whose bound no claims entry states: |RN(v) - v| <= u|v| + t eta with t = 0 for a sum (sums
# below the normal range are exact) and t = 1/2 for a product.
CENTER_KERNEL = {"ball_add_1": "add", "ball_sub_1": "add", "ball_mul_1": "prod",
                 "ball_scale_1": "prod", "ball_add_2": "add_2_2", "ball_sub_2": "add_2_2",
                 "ball_mul_2": "mul_2_2", "ball_scale_2": "mul_2_1"}
ONE_OPERATION_BOUND = {"add": ("1", 1, Fraction(0)), "prod": ("1", 1, Fraction(1, 2))}

# The second radius design (milestone1.md, "The radius, second design"): its constants E, G, H
# come from the proved bound of the center kernel, (c, k, t) with rel = c u^k and tiny = t eta,
# as the pages state them: add_1_1 and mul_1_1 for one limb (u/(1+u), and 1/2 eta for the
# product), add_2_2, mul_2_2 and mul_2_1 for two (architecture.md's table).
PROVED_BOUND = {"add": ("1/(1+u)", 1, Fraction(0)), "prod": ("1/(1+u)", 1, Fraction(1, 2)),
                "add_2_2": ("3/(1-4*u)", 2, Fraction(0)), "mul_2_2": ("4", 2, Fraction(3, 2)),
                "mul_2_1": ("2", 2, Fraction(1))}
# The row of the table for each Ball kernel: (center kernel, E has the factor (1+u), the power of
# (1+u) in G, the shape of H).
RADIUS2 = {"ball_add_1": ("add", False, 3, "add"), "ball_sub_1": ("add", False, 3, "add"),
           "ball_add_2": ("add_2_2", True, 3, "add"), "ball_sub_2": ("add_2_2", True, 3, "add"),
           "ball_scale_1": ("prod", False, 3, "scale"), "ball_scale_2": ("mul_2_1", True, 3, "scale"),
           "ball_mul_1": ("prod", False, 5, "mul1"), "ball_mul_2": ("mul_2_2", False, 6, "mul2")}
RADIUS_DESIGNS = ("first", "second")

_NAMED = {"binary64": (53, -1074, 971), "binary32": (24, -149, 104)}


def parse_format_triple(name):
    if name in _NAMED:
        return _NAMED[name]
    m = re.fullmatch(r"fp:(\d+):(-?\d+):(-?\d+)", name)
    if not m:
        raise ValueError("unknown format %r" % name)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


class Arith:
    """IEEE operations of one format on fixed values (integers N meaning N * 2^qmin), with
    non-finite values as Python floats."""

    def __init__(self, triple, variant="correct"):
        self.p, self.qmin, self.qmax = triple
        self.omega = ((1 << self.p) - 1) << (self.qmax - self.qmin)
        self.lam = 1 << (self.p - 1)
        self.variant = variant
        self.fits = self.p <= 53 and self.qmin >= -1074 and self.qmax + self.p <= 1024

    # -- rounding --------------------------------------------------------
    def round(self, n, extra):
        """Nearest number of the format to n * 2^(qmin - extra), ties to the even
        significand; +-inf beyond the IEEE overflow threshold."""
        if n == 0:
            return 0
        a = -n if n < 0 else n
        qexp = max(a.bit_length() - self.p, extra)       # spacing around a, in units
        lower = (a >> qexp) << qexp
        if lower != a:
            if self.variant == "subnormal-trunc" and a < (self.lam << extra):
                pass
            else:
                upper = lower + (1 << qexp)
                below, above = a - lower, upper - a
                if above < below or (above == below and (lower >> qexp) & 1):
                    lower = upper
        r = lower >> extra
        if r > self.omega:
            return -INF if n < 0 else INF
        return -r if n < 0 else r

    # -- operations ------------------------------------------------------
    @staticmethod
    def _proxy(x):
        # For non-finite arithmetic only the class of a finite operand matters (zero, or
        # its sign), so a float stand-in gives IEEE's answer.
        if type(x) is float:
            return x
        return 1.0 if x > 0 else -1.0 if x < 0 else 0.0

    def add(self, a, b):
        if type(a) is int and type(b) is int:
            return self.round(a + b, 0)
        return self._proxy(a) + self._proxy(b)

    def sub(self, a, b):
        if type(a) is int and type(b) is int:
            return self.round(a - b, 0)
        return self._proxy(a) - self._proxy(b)

    def _fused(self, a, b, c, sp, sc):
        # RN(sp*a*b + sc*c) with one rounding.
        if type(a) is int and type(b) is int and type(c) is int:
            if self.qmin < 0:
                return self.round(sp * a * b + sc * (c << -self.qmin), -self.qmin)
            return self.round(((sp * a * b) << self.qmin) + sc * c, 0)
        return sp * self._proxy(a) * self._proxy(b) + sc * self._proxy(c)

    def prod(self, a, b):
        if type(a) is int and type(b) is int:
            if self.qmin < 0:
                return self.round(a * b, -self.qmin)
            return self.round((a * b) << self.qmin, 0)
        return self._proxy(a) * self._proxy(b) + 0.0

    def fma(self, a, b, c):
        return self._fused(a, b, c, 1, 1)

    def fms(self, a, b, c):
        return self._fused(a, b, c, 1, -1)

    def fnma(self, a, b, c):
        return self._fused(a, b, c, -1, 1)

    def times_inf(self, a):
        """a times +infinity: a NaN for a NaN or a zero, otherwise the infinity of a's sign."""
        if type(a) is int:
            return NAN if a == 0 else INF if a > 0 else -INF
        return a * INF

    def const_splitter(self):
        """2^ceil(p/2) + 1 as a fixed value."""
        if self.qmin > 0:
            raise ValueError("the splitter is not a number of a format with qmin > 0")
        return ((1 << ((self.p + 1) // 2)) + 1) << -self.qmin

    # -- format helpers used by the variants ------------------------------
    def spacing_above(self, a):
        b = abs(a).bit_length()
        return 1 << max(b - self.p, 0)

    def succ(self, a):
        if type(a) is not int:
            return a
        if a >= 0:
            r = a + self.spacing_above(a)
            return INF if r > self.omega else r
        m = -a
        return -(m - (1 << max((m - 1).bit_length() - self.p, 0)))

    def member(self, a):
        if a == 0:
            return True
        m = abs(a)
        return m <= self.omega and (m >> ((m & -m).bit_length() - 1)).bit_length() <= self.p

    # -- neighbors, from the definition ------------------------------------
    def _canonical(self, a):
        """(m, e) with a = m * 2^e * eta, 2^(p-1) <= m < 2^p, or e = 0 for a subnormal."""
        e = max(a.bit_length() - self.p, 0)
        return a >> e, e

    def _above_positive(self, a):
        # The next number above a >= 0 is m + 1 units of the same exponent (when m + 1 = 2^p
        # this is the first number of the next binade, the same value).
        if a == 0:
            return 1
        m, e = self._canonical(a)
        r = (m + 1) << e
        return INF if r > self.omega else r

    def _below_positive(self, a):
        # The number below a > 0: one unit less, except at the bottom of a normal binade,
        # where the binade underneath has units of half the size.
        m, e = self._canonical(a)
        if m == 1 << (self.p - 1) and e > 0:
            return ((1 << self.p) - 1) << (e - 1)
        return (m - 1) << e

    def next_up(self, a):
        """succ: the smallest number of the format above a (IEEE nextUp)."""
        if type(a) is float:
            if a != a or a > 0:
                return a
            return -self.omega
        if a >= 0:
            return self._above_positive(a)
        return -self._below_positive(-a)

    def next_down(self, a):
        """pred: the largest number of the format below a."""
        return -self.next_up(-a)

    def round_up_fraction(self, f):
        """The smallest number of the format not below the positive rational f * eta."""
        num, den = f.numerator, f.denominator
        if num <= 0:
            raise ValueError("round_up_fraction of a nonpositive number")
        e = num.bit_length() - den.bit_length()
        if (num << max(-e, 0)) < (den << max(e, 0)):
            e -= 1
        unit = 1 << max(e - self.p + 1, 0)
        r = -((-num) // (den * unit)) * unit
        return INF if r > self.omega else r

    # -- literals --------------------------------------------------------
    def read(self, tok):
        t = tok.lower()
        if t in ("inf", "+inf"):
            return INF
        if t == "-inf":
            return -INF
        if t in ("nan", "-nan", "+nan"):
            return NAN
        try:
            if not self.fits:
                raise OverflowError
            num, den = float.fromhex(tok).as_integer_ratio()
        except OverflowError:
            # Beyond double range only a literal outside the format can get here.
            num, den = _exact_hex(tok)
        # value num/den with den a power of two; express in units of 2^qmin, rounding an
        # input that is not a number of the format (the checker reports those as invalid).
        if self.qmin < 0:
            num <<= -self.qmin
        else:
            den <<= self.qmin
        if num % den == 0:
            v = num // den
            return v if self.member(v) else self.round(v, 0)
        return self.round(num, den.bit_length() - 1)

    def write(self, v):
        if type(v) is float:
            if v != v:
                return "nan"
            return "inf" if v > 0 else "-inf"
        if v == 0:
            return "0x0p+0"
        if self.fits:
            tz = (v & -v).bit_length() - 1
            return math.ldexp(float(v >> tz), self.qmin + tz).hex()
        return _exact_hex_out(v, self.qmin)


def _eval_rational(text, u):
    """A rational expression in u (integers, u, + - * /, ^ or ** with an integer exponent),
    evaluated exactly with Python's own parser; the checker has its own evaluator."""

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and type(n.value) is int:
            return Fraction(n.value)
        if isinstance(n, ast.Name) and n.id == "u":
            return u
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b
            if isinstance(n.op, ast.Pow) and b.denominator == 1:
                return a ** int(b)
        raise ValueError("cannot evaluate %r" % text)

    return ev(ast.parse(str(text).replace("^", "**"), mode="eval"))


def center_bound(center, claims_path):
    """(c, k, t) of the error bound of a center kernel: for one operation the bound of a
    rounding, otherwise the first unconditional error entry of that kernel in the claims."""
    if center in ONE_OPERATION_BOUND:
        return ONE_OPERATION_BOUND[center]
    with open(claims_path, encoding="utf-8") as fh:
        data = json.load(fh)
    for k in data["kernels"]:
        if k.get("name") == center:
            for e in k["ensures"]:
                if e.get("kind") == "error" and e.get("when") is None:
                    return str(e["c"]), int(e["k"]), Fraction(str(e["t"]))
    raise ValueError("no error bound for %s in %s" % (center, claims_path))


def ball_constants(ar, center, claims_path):
    """(U, V) as fixed values of the format: unit/(1 - unit) and tiny/(1 - unit) rounded up,
    with unit = c u^k and tiny = t eta."""
    c, k, t = center_bound(center, claims_path)
    u = Fraction(1, 1 << ar.p)
    unit = _eval_rational(c, u) * u ** k
    if not 0 <= unit < 1:
        raise ValueError("unit %s of %s is not in [0, 1)" % (unit, center))
    per_eta = Fraction(1 << -ar.qmin) if ar.qmin < 0 else Fraction(1, 1 << ar.qmin)
    U = ar.round_up_fraction(unit / (1 - unit) * per_eta) if unit else 0
    V = ar.round_up_fraction(t / (1 - unit)) if t else 0
    return U, V


def radius2_exact(p, qmin, kname):
    """(E, G, H) of the second radius design for a Ball kernel, as exact Fractions (H in units of
    eta), from milestone1.md's table:
        E = U_q, or U_q (1+u) for the 2-limb sums and scaling;
        G = (1+u)^3, ^5 (ball_mul_1) or ^6 (ball_mul_2);
        H = (1+u)((1+u)^2 eta + 1/2 eta)            for sums,
            (1+u)((1+u)^2 eta + V_q + 1/2 eta)      for scalings,
            (1+u)(2(1+u)^4 eta + V_q + 1/2 eta)     for ball_mul_1,
            (1+u)(2(1+u)^5 eta + V_q + 1/2 eta)     for ball_mul_2,
    with U_q = rel/(1 - rel) and V_q = tiny/(1 - rel) of the center kernel's proved bound."""
    center, e_factor, g_power, h_shape = RADIUS2[kname]
    c, k, t = PROVED_BOUND[center]
    u = Fraction(1, 1 << p)
    rel = _eval_rational(c, u) * u ** k
    uq = rel / (1 - rel)
    vq = t / (1 - rel)                         # in units of eta
    one = 1 + u
    E = uq * one if e_factor else uq
    G = one ** g_power
    if h_shape == "add":
        H = one * (one ** 2 + Fraction(1, 2))
    elif h_shape == "scale":
        H = one * (one ** 2 + vq + Fraction(1, 2))
    elif h_shape == "mul1":
        H = one * (2 * one ** 4 + vq + Fraction(1, 2))
    else:
        H = one * (2 * one ** 5 + vq + Fraction(1, 2))
    return E, G, H


def radius2_constants(ar, kname):
    """(E, G, H) rounded up to the format, as fixed values (+inf beyond Omega)."""
    E, G, H = radius2_exact(ar.p, ar.qmin, kname)
    per_eta = Fraction(1 << -ar.qmin) if ar.qmin < 0 else Fraction(1, 1 << ar.qmin)
    up = lambda f: ar.round_up_fraction(f) if f else 0
    return up(E * per_eta), up(G * per_eta), up(H)


def _exact_hex(tok):
    m = re.fullmatch(r"([+-]?)0[xX]([0-9a-fA-F]*)\.?([0-9a-fA-F]*)[pP]([+-]?\d+)", tok)
    if not m:
        raise ValueError("bad literal %r" % tok)
    s, ip, fp, e = m.groups()
    v = int((ip + fp) or "0", 16) * (-1 if s == "-" else 1)
    e = int(e) - 4 * len(fp)
    return (v << e, 1) if e >= 0 else (v, 1 << -e)


def _exact_hex_out(v, scale):
    s = "-" if v < 0 else ""
    v = abs(v)
    return "%s0x%xp%+d" % (s, v, scale)


# ---------------------------------------------------------------------------
# Kernels, value names as in architecture.md

class Kernels:
    def __init__(self, ar, center_claims=DEFAULT_CENTER_CLAIMS, radius="first"):
        self.A = ar
        self.v = ar.variant
        self.trace = [] if ar.variant in ("trace-fast-two-sum", "trace-mul-pow2") else None
        self.center_claims = center_claims
        self.radius = radius
        self._consts = {}

    def two_sum(self, a, b):
        A = self.A
        s = A.add(a, b)
        bb = A.sub(s, a)
        t0 = A.sub(s, bb)
        t1 = A.sub(a, t0)
        t2 = A.sub(b, bb)
        e = A.add(t1, t2)
        if self.v == "two-sum-zero" and e == 0 and type(e) is int:
            e = 1
        return s, e

    def fast_two_sum(self, a, b, site="fast_two_sum"):
        A = self.A
        s = A.add(a, b)
        z = A.sub(s, a)
        e = A.sub(b, z)
        if (self.v == "trace-fast-two-sum" and type(a) is int and type(b) is int
                and abs(a) < abs(b)):
            # The documented precondition is |a| >= |b|, or exponent(a) >= exponent(b) with
            # IEEE exponents (clamped at the smallest normal binade).
            ea = max(abs(a).bit_length(), A.p) if a else A.p
            eb = max(abs(b).bit_length(), A.p)
            exact = type(s) is int and type(e) is int and s + e == a + b
            self.trace.append((site, a == 0, ea >= eb, exact))
        return s, e

    def two_prod(self, a, b):
        A = self.A
        p = A.prod(a, b)
        e = A.fms(a, b, p)
        return p, e

    def split(self, a):
        A = self.A
        g = A.prod(A.const_splitter(), a)
        d = A.sub(a, g)
        ah = A.add(g, d)
        al = A.sub(a, ah)
        return ah, al

    def two_prod_dekker(self, a, b):
        A = self.A
        ah, al = self.split(a)
        bh, bl = self.split(b)
        p = A.prod(a, b)
        q0 = A.prod(ah, bh)
        t1 = A.sub(q0, p)
        q1 = A.prod(ah, bl)
        t2 = A.add(t1, q1)
        q2 = A.prod(al, bh)
        t3 = A.add(t2, q2)
        q3 = A.prod(al, bl)
        e = A.add(t3, q3)
        return p, e

    def add_2_2(self, x0, x1, y0, y1):
        A = self.A
        sh, sl = self.two_sum(x0, y0)
        th, tl = self.two_sum(x1, y1)
        c = A.add(sl, th)
        vh, vl = self.fast_two_sum(sh, c, "inner")
        w = A.add(tl, vl)
        if self.v == "add-skip-renorm":
            return vh, w
        return self.fast_two_sum(vh, w, "final")

    def add_2_1(self, x0, x1, a):
        A = self.A
        g = self.guard(a)
        sh, sl = self.two_sum(x0, g)
        v = A.add(x1, sl)
        if self.v == "add-skip-renorm":
            return sh, v
        return self.fast_two_sum(sh, v, "final")

    def mul_2_2(self, x0, x1, y0, y1):
        A = self.A
        ch, cl1 = self.two_prod(x0, y0)
        tl0 = A.prod(x1, y1)
        tl1 = tl0 if self.v == "mul-drop-cross" else A.fma(x0, y1, tl0)
        cl2 = A.fma(x1, y0, tl1)
        cl3 = A.add(cl1, cl2)
        return self.fast_two_sum(ch, cl3, "final")

    def mul_2_1(self, x0, x1, a):
        A = self.A
        ch, cl1 = self.two_prod(x0, a)
        cl3 = cl1 if self.v == "mul-drop-cross" else A.fma(x1, a, cl1)
        return self.fast_two_sum(ch, cl3, "final")

    def add_fast_2_2(self, x0, x1, y0, y1):
        A = self.A
        sh, sl = self.two_sum(x0, y0)
        v = A.add(x1, y1)
        w = A.add(sl, v)
        if self.v == "add-skip-renorm":
            return sh, w
        if self.v == "fast-end-two-sum":
            return self.two_sum(sh, w)
        return self.fast_two_sum(sh, w, "final")

    # -- second wave: sign changes and subtraction -------------------------------------------
    def neg_2(self, x0, x1):
        return -x0, -x1

    def abs_2(self, x0, x1):
        m = x0 < 0
        n0 = -x0
        n1 = x1 if self.v == "abs-lead-only" else -x1
        z0 = n0 if m else x0
        z1 = n1 if m else x1
        return z0, z1

    def sub_2_2(self, x0, x1, y0, y1):
        return self.add_2_2(x0, x1, -y0, -y1)

    def sub_2_1(self, x0, x1, a):
        return self.add_2_1(x0, x1, -a)

    def sub_1_2(self, a, y0, y1):
        return self.add_2_1(-y0, -y1, a)

    # -- comparisons, limbs in order ---------------------------------------------------------
    def _lt(self, x0, x1, y0, y1, strict):
        h = x0 < y0
        e = x0 == y0
        # The injected error: when the first limbs are equal, lt and le swap tests.
        if self.v == "cmp-lead-equal" and e:
            strict = not strict
        l = x1 < y1 if strict else x1 <= y1
        t = e and l
        return (h or t,)

    def _eq(self, x0, x1, y0, y1):
        h = x0 == y0
        l = x1 == y1
        if self.v == "cmp-lead-equal" and h:
            l = True
        return (h and l,)

    def lt_2_2(self, x0, x1, y0, y1):
        return self._lt(x0, x1, y0, y1, True)

    def le_2_2(self, x0, x1, y0, y1):
        return self._lt(x0, x1, y0, y1, False)

    def eq_2_2(self, x0, x1, y0, y1):
        return self._eq(x0, x1, y0, y1)

    def lt_2_1(self, x0, x1, a):
        return self._lt(x0, x1, a, 0, True)

    def le_2_1(self, x0, x1, a):
        return self._lt(x0, x1, a, 0, False)

    def eq_2_1(self, x0, x1, a):
        return self._eq(x0, x1, a, 0)

    def lt_1_2(self, a, y0, y1):
        return self._lt(a, 0, y0, y1, True)

    def le_1_2(self, a, y0, y1):
        return self._lt(a, 0, y0, y1, False)

    # -- conversions to one limb -------------------------------------------------------------
    def to_nearest_2(self, x0, x1):
        return (x0,)

    def to_down_2(self, x0, x1):
        A = self.A
        m = x1 < 0
        p = A.next_down(x0)
        if self.v == "down-no-neg-step":
            m = False
        if (self.v == "down-pow2-wrong-side" and type(x0) is int and x0
                and abs(x0) & (abs(x0) - 1) == 0):
            s = A.next_up(x0)
            p = x0 - (s - x0) if type(s) is int else p
        t = p if m else x0
        return (t,)

    def to_up_2(self, x0, x1):
        m = 0 < x1
        s = self.A.next_up(x0)
        t = s if m else x0
        return (t,)

    def abs_upper_2(self, x0, x1):
        a0, a1 = self.abs_2(x0, x1)
        return self.to_up_2(a0, a1)

    # -- the one-limb operations as kernels ----------------------------------------------------
    def add_1_1(self, a, b):
        return (self.A.add(a, b),)

    def mul_1_1(self, a, b):
        return (self.A.prod(a, b),)

    # -- directed steps, scaling --------------------------------------------------------------
    def radd(self, a, b):
        s = self.A.add(a, b)
        r = s if self.v == "radd-no-step" else self.A.next_up(s)
        return (r,)

    def rmul(self, a, b):
        p = self.A.prod(a, b)
        r = p if self.v == "rmul-nearest" else self.A.next_up(p)
        return (r,)

    def mul_pow2_2(self, x0, x1, c):
        A = self.A
        h = A.prod(x0, c)
        l = A.prod(x1, c)
        if self.v == "trace-mul-pow2" and type(h) is int and type(l) is int and A.add(h, l) != h:
            self.trace.append("mul_pow2_2: (h, l) = (%s, %s) is not normalized"
                              % (A.write(h), A.write(l)))
        return self.fast_two_sum(h, l, "final")

    # -- Ball kernels ---------------------------------------------------------------------------
    def consts(self, kname):
        c = self._consts.get(kname)
        if c is None:
            c = self._consts[kname] = ball_constants(self.A, CENTER_KERNEL[kname],
                                                     self.center_claims)
        return c

    def _abs_upper(self, cz):
        return (abs(cz[0]),) if len(cz) == 1 else self.abs_upper_2(*cz)

    def _rz(self, cz, rz):
        c0 = cz[0]
        if (self.v == "ball-pow2-ulp" and type(c0) is int and c0 and type(rz) is int
                and abs(c0) & (abs(c0) - 1) == 0):
            return self.A.next_down(rz)
        return rz

    # -- the second radius design: ordinary operations, then one inflation ------------------------
    def consts2(self, kname):
        """(E, G, H) of a Ball kernel, rounded up; the variants change one of them."""
        key = ("radius2", kname)
        c = self._consts.get(key)
        if c is None:
            A = self.A
            E, G, H = radius2_constants(A, kname)
            if self.v == "ball2-no-E":
                E = 0
            elif self.v == "ball2-no-H":
                H = 0
            elif self.v == "ball2-G-pred" and type(G) is int:
                G = A.next_down(G)
            elif self.v == "ball2-H-half" and type(H) is int:
                H = A.round_up_fraction(Fraction(H, 2))
            c = self._consts[key] = (E, G, H)
        return c

    def _ball_add2(self, kname, cx, rx, cy, ry):
        A = self.A
        E, G, H = self.consts2(kname)
        cz = (A.add(cx[0], cy[0]),) if len(cx) == 1 else self.add_2_2(*(cx + cy))
        az = abs(cz[0])
        s = A.add(rx, ry)
        t = A.fma(az, E, s)
        rz = A.fma(t, G, H)
        return cz + (rz,)

    def _ball_mul2(self, kname, cx, rx, cy, ry):
        A = self.A
        E, G, H = self.consts2(kname)
        cz = (A.prod(cx[0], cy[0]),) if len(cx) == 1 else self.mul_2_2(*(cx + cy))
        ax = abs(cx[0])
        ay = abs(cy[0])
        az = abs(cz[0])
        p = A.prod(rx, ry)
        q = A.fma(ay, rx, p)
        w = A.fma(ax, ry, q)
        t = A.fma(az, E, w)
        rz = A.fma(t, G, H)
        return cz + (rz,)

    def _ball_scale2(self, kname, cx, rx, a):
        A = self.A
        E, G, H = self.consts2(kname)
        cz = (A.prod(cx[0], a),) if len(cx) == 1 else self.mul_2_1(cx[0], cx[1], a)
        aa = abs(a)
        az = abs(cz[0])
        p = A.prod(aa, rx)
        t = A.fma(az, E, p)
        rz = A.fma(t, G, H)
        return cz + (rz,)

    def _ball_add(self, kname, cx, rx, cy, ry):
        if self.radius == "second":
            return self._ball_add2(kname, cx, rx, cy, ry)
        A = self.A
        U, _ = self.consts(kname)
        cz = (A.add(cx[0], cy[0]),) if len(cx) == 1 else self.add_2_2(*(cx + cy))
        (mz,) = self._abs_upper(cz)
        (d,) = self.rmul(U, mz)
        (r0,) = self.radd(rx, ry)
        (rz,) = (r0,) if self.v == "ball-no-center-error" else self.radd(r0, d)
        return cz + (self._rz(cz, rz),)

    def _ball_mul(self, kname, cx, rx, cy, ry):
        if self.radius == "second":
            return self._ball_mul2(kname, cx, rx, cy, ry)
        A = self.A
        U, V = self.consts(kname)
        cz = (A.prod(cx[0], cy[0]),) if len(cx) == 1 else self.mul_2_2(*(cx + cy))
        (ax,) = self._abs_upper(cx)
        (ay,) = self._abs_upper(cy)
        (t1,) = self.rmul(ax, ry)
        (t2,) = self.rmul(ay, rx)
        (t3,) = self.rmul(rx, ry)
        (s1,) = self.radd(t1, t2)
        (s2,) = (s1,) if self.v == "ball-no-rr" else self.radd(s1, t3)
        (mz,) = self._abs_upper(cz)
        (d0,) = self.rmul(U, mz)
        (d,) = self.radd(d0, V)
        (rz,) = (s2,) if self.v == "ball-no-center-error" else self.radd(s2, d)
        return cz + (self._rz(cz, rz),)

    def _ball_scale(self, kname, cx, rx, a):
        if self.radius == "second":
            return self._ball_scale2(kname, cx, rx, a)
        A = self.A
        U, V = self.consts(kname)
        cz = (A.prod(cx[0], a),) if len(cx) == 1 else self.mul_2_1(cx[0], cx[1], a)
        aa = abs(a)
        (t1,) = self.rmul(aa, rx)
        (mz,) = self._abs_upper(cz)
        (d0,) = self.rmul(U, mz)
        (d,) = self.radd(d0, V)
        (rz,) = (t1,) if self.v == "ball-no-center-error" else self.radd(t1, d)
        return cz + (self._rz(cz, rz),)

    def ball_add_1(self, cx, rx, cy, ry):
        return self._ball_add("ball_add_1", (cx,), rx, (cy,), ry)

    def ball_add_2(self, cx0, cx1, rx, cy0, cy1, ry):
        return self._ball_add("ball_add_2", (cx0, cx1), rx, (cy0, cy1), ry)

    def ball_sub_1(self, cx, rx, cy, ry):
        return self._ball_add("ball_sub_1", (cx,), rx, (-cy,), ry)

    def ball_sub_2(self, cx0, cx1, rx, cy0, cy1, ry):
        return self._ball_add("ball_sub_2", (cx0, cx1), rx, (-cy0, -cy1), ry)

    def ball_neg_1(self, cx, rx):
        return -cx, rx

    def ball_neg_2(self, cx0, cx1, rx):
        return -cx0, -cx1, rx

    def ball_mul_1(self, cx, rx, cy, ry):
        return self._ball_mul("ball_mul_1", (cx,), rx, (cy,), ry)

    def ball_mul_2(self, cx0, cx1, rx, cy0, cy1, ry):
        return self._ball_mul("ball_mul_2", (cx0, cx1), rx, (cy0, cy1), ry)

    def ball_scale_1(self, cx, rx, a):
        return self._ball_scale("ball_scale_1", (cx,), rx, a)

    def ball_scale_2(self, cx0, cx1, rx, a):
        return self._ball_scale("ball_scale_2", (cx0, cx1), rx, a)

    # -- the non-finite layer (milestone1.md, "IEEE-like results", "Values that enter from the
    # program", "Ball kernels"), as listed: the core, then the fix-up on the leading limbs ------
    def guard(self, a):
        """RN(a + 0): a itself (a zero comes out positive, which the integers cannot show)."""
        return self.A.add(a, 0)

    def _fixup(self, z, t, fin):
        """The fix-up of a full kernel.  z = (z0, z1) is the core's result and t the operation
        of T on the leading limbs; fin (every operand finite) is read by injected errors only."""
        A = self.A
        v = self.v
        z0, z1 = z
        if v == "full-no-fixup":
            return z0, z1
        a = abs(z0)
        f = a < INF                    # z0 is finite
        r0 = A.times_inf(t)            # a NaN or a zero gives a NaN; any other t the infinity of its sign
        n = r0 == r0                   # r0 is not a NaN
        r1 = 0 if n else r0
        if v == "full-inf-tail-nan" and n:
            r1 = NAN
        elif v == "full-inf-tail-eta" and n:
            r1 = 1
        elif v == "full-nan-one-limb" and not n:
            r1 = 0
        if not f and fin:
            if v == "full-overflow-sign":
                r0 = -r0
            elif v == "full-overflow-nan":
                r0 = r1 = NAN
            elif v == "full-overflow-finite":
                r0, r1 = (A.omega if r0 > 0 else -A.omega), 0
        if (v == "full-spurious-overflow" and f and fin and type(t) is int
                and abs(t) >= 1 << (A.qmax + A.p - 3 - A.qmin)):
            return (INF if t > 0 else -INF), 0
        w0 = z0 if f else r0
        w1 = z1 if f else r1
        if v == "full-nan-to-zero" and w0 != w0:
            return 0, 0
        return w0, w1

    @staticmethod
    def _finite(*vals):
        return all(type(v) is int for v in vals)

    def add_2_2_full(self, x0, x1, y0, y1):
        z = self.add_2_2(x0, x1, y0, y1)
        return self._fixup(z, self.A.add(x0, y0), self._finite(x0, x1, y0, y1))

    def add_fast_2_2_full(self, x0, x1, y0, y1):
        z = self.add_fast_2_2(x0, x1, y0, y1)
        return self._fixup(z, self.A.add(x0, y0), self._finite(x0, x1, y0, y1))

    def sub_2_2_full(self, x0, x1, y0, y1):
        z = self.sub_2_2(x0, x1, y0, y1)
        return self._fixup(z, self.A.sub(x0, y0), self._finite(x0, x1, y0, y1))

    def add_2_1_full(self, x0, x1, a):
        g = self.guard(a)
        z = self.add_2_1(x0, x1, a)
        return self._fixup(z, self.A.add(x0, g), self._finite(x0, x1, a))

    def sub_2_1_full(self, x0, x1, a):
        g = self.guard(a)
        z = self.sub_2_1(x0, x1, a)
        return self._fixup(z, self.A.sub(x0, g), self._finite(x0, x1, a))

    def sub_1_2_full(self, a, y0, y1):
        g = self.guard(a)
        z = self.sub_1_2(a, y0, y1)
        return self._fixup(z, self.A.sub(g, y0), self._finite(a, y0, y1))

    def mul_2_2_full(self, x0, x1, y0, y1):
        z = self.mul_2_2(x0, x1, y0, y1)
        return self._fixup(z, self.A.prod(x0, y0), self._finite(x0, x1, y0, y1))

    def mul_2_1_full(self, x0, x1, a):
        z = self.mul_2_1(x0, x1, a)
        return self._fixup(z, self.A.prod(x0, a), self._finite(x0, x1, a))

    def mul_pow2_2_full(self, x0, x1, c):
        z = self.mul_pow2_2(x0, x1, c)
        return self._fixup(z, self.A.prod(x0, c), self._finite(x0, x1, c))

    def _ball_fixup(self, out, k, q):
        """The fix-up of a full Ball kernel: out = (cz..., rz) from the core, q a NaN exactly
        when an operand is empty."""
        A = self.A
        v = self.v
        cz, rz = out[:k], out[k]
        if v == "ball-full-zero-inf-empty":
            q = rz
        e = q == q
        a = abs(cz[0])
        f1 = a < INF                   # the center is finite
        f2 = rz < INF                  # the radius is finite (false for a NaN)
        f = f1 and f2
        c = [ci if f else 0 for ci in cz]
        r = rz if f else INF
        if v == "ball-full-finite-whole" and f1 and not f2:
            c, r = list(cz), A.omega
        if v == "ball-full-swap":
            if not e:
                return tuple([0] * k + [INF])
            if not f:
                return tuple([NAN] * (k + 1))
        return tuple(ci if e else q for ci in c) + (r if e else q,)

    def ball_add_1_full(self, cx, rx, cy, ry):
        return self._ball_fixup(self.ball_add_1(cx, rx, cy, ry), 1, self.A.add(rx, ry))

    def ball_add_2_full(self, cx0, cx1, rx, cy0, cy1, ry):
        return self._ball_fixup(self.ball_add_2(cx0, cx1, rx, cy0, cy1, ry), 2, self.A.add(rx, ry))

    def ball_sub_1_full(self, cx, rx, cy, ry):
        return self._ball_fixup(self.ball_sub_1(cx, rx, cy, ry), 1, self.A.add(rx, ry))

    def ball_sub_2_full(self, cx0, cx1, rx, cy0, cy1, ry):
        return self._ball_fixup(self.ball_sub_2(cx0, cx1, rx, cy0, cy1, ry), 2, self.A.add(rx, ry))

    def ball_mul_1_full(self, cx, rx, cy, ry):
        return self._ball_fixup(self.ball_mul_1(cx, rx, cy, ry), 1, self.A.add(rx, ry))

    def ball_mul_2_full(self, cx0, cx1, rx, cy0, cy1, ry):
        return self._ball_fixup(self.ball_mul_2(cx0, cx1, rx, cy0, cy1, ry), 2, self.A.add(rx, ry))

    def ball_scale_1_full(self, cx, rx, a):
        return self._ball_fixup(self.ball_scale_1(cx, rx, a), 1, rx)

    def ball_scale_2_full(self, cx0, cx1, rx, a):
        return self._ball_fixup(self.ball_scale_2(cx0, cx1, rx, a), 2, rx)

    def make_2(self, a):
        x0 = self.guard(a)
        n = x0 == x0
        x1 = 0 if n else x0
        if self.v == "make2-inf-nan-tail" and n:
            x1 = self.A.sub(x0, x0)
        return x0, x1

    def make_2_limbs(self, h, l):
        return self.guard(h), self.guard(l)

    def _ball_make(self, c, r):
        g = self.guard(r)
        e = 0 <= g                     # le(0, g): false for a NaN or a negative radius
        if self.v == "make-negative-radius":
            e = g == g
        elif self.v == "make-nan-radius":
            e = True
        a = abs(c[0])
        f1 = a < INF
        f2 = g < INF
        f = f1 and f2
        k = [ci if f else 0 for ci in c]
        s = g if f else INF
        return tuple(ki if e else NAN for ki in k) + (s if e else NAN,)

    def ball_make_1(self, c, r):
        return self._ball_make((self.guard(c),), r)

    def ball_make_2(self, c0, c1, r):
        return self._ball_make((c0, c1), r)


ARITY = {"two_sum": 2, "fast_two_sum": 2, "two_prod": 2, "two_prod_dekker": 2, "split": 1,
         "add_2_2": 4, "add_2_1": 3, "mul_2_2": 4, "mul_2_1": 3, "add_fast_2_2": 4,
         "neg_2": 2, "abs_2": 2, "sub_2_2": 4, "sub_2_1": 3, "sub_1_2": 3,
         "lt_2_2": 4, "le_2_2": 4, "eq_2_2": 4, "lt_2_1": 3, "le_2_1": 3, "eq_2_1": 3,
         "lt_1_2": 3, "le_1_2": 3, "to_nearest_2": 2, "to_down_2": 2, "to_up_2": 2,
         "abs_upper_2": 2, "radd": 2, "rmul": 2, "mul_pow2_2": 3,
         "ball_add_1": 4, "ball_add_2": 6, "ball_sub_1": 4, "ball_sub_2": 6, "ball_neg_1": 2,
         "ball_neg_2": 3, "ball_mul_1": 4, "ball_mul_2": 6, "ball_scale_1": 3,
         "ball_scale_2": 4,
         # The non-finite layer.
         "add_2_2_full": 4, "add_fast_2_2_full": 4, "sub_2_2_full": 4, "add_2_1_full": 3,
         "sub_2_1_full": 3, "sub_1_2_full": 3, "mul_2_2_full": 4, "mul_2_1_full": 3,
         "mul_pow2_2_full": 3, "ball_add_1_full": 4, "ball_add_2_full": 6, "ball_sub_1_full": 4,
         "ball_sub_2_full": 6, "ball_mul_1_full": 4, "ball_mul_2_full": 6, "ball_scale_1_full": 3,
         "ball_scale_2_full": 4, "make_2": 1, "make_2_limbs": 2, "ball_make_1": 2,
         "ball_make_2": 3, "add_1_1": 2, "mul_1_1": 2}
FIRST_WAVE = frozenset(("two_sum", "fast_two_sum", "two_prod", "two_prod_dekker", "split",
                        "add_2_2", "add_2_1", "mul_2_2", "mul_2_1", "add_fast_2_2"))
# Which input limb pairs form a normalized 2-limb operand (for corrupt-input).
PAIRS = {"add_2_2": (0, 2), "add_2_1": (0,), "mul_2_2": (0, 2), "mul_2_1": (0,),
         "add_fast_2_2": (0, 2)}


class Runner:
    def __init__(self, variant="correct", center_claims=None, radius="first"):
        if variant not in VARIANTS:
            raise ValueError("unknown variant %r (known: %s)" % (variant, ", ".join(VARIANTS)))
        if radius not in RADIUS_DESIGNS:
            raise ValueError("unknown radius design %r (first or second)" % radius)
        self.variant = variant
        self.center_claims = center_claims or DEFAULT_CENTER_CLAIMS
        self.radius = radius
        self.cache = {}

    def kernels(self, fmtname):
        k = self.cache.get(fmtname)
        if k is None:
            k = self.cache[fmtname] = Kernels(Arith(parse_format_triple(fmtname), self.variant),
                                              self.center_claims, self.radius)
        return k

    def complete(self, line):
        """The completed line(s) for one request line."""
        line = line.rstrip("\r\n")
        if not line or line[0] == "#":
            return [line]
        toks = line.split(" ")
        tag = []
        if toks[-1].startswith("#"):
            tag = [toks[-1]]
            toks = toks[:-1]
        kname, fname, args = toks[0], toks[1], toks[2:]
        K = self.kernels(fname)
        A = K.A
        if ARITY.get(kname) != len(args):
            raise ValueError("cannot run %r with %d limbs" % (kname, len(args)))
        pre = []
        if self.variant == "corrupt-input" and zlib.crc32(line.encode()) % 64 == 0:
            args = self.corrupt(kname, A, args)
            line = " ".join([kname, fname] + args + tag)
            pre = ["# refrun: corrupted input"]
        vals = [A.read(t) for t in args]
        if K.trace is not None:
            del K.trace[:]
        out = list(getattr(K, kname)(*vals))
        if K.trace:
            pre += ["# refrun trace: " + t if isinstance(t, str) else
                    "# refrun trace: fast_two_sum %s with |a| < |b|: a = 0 %s, exponent(a) >= "
                    "exponent(b) %s, error-free %s" % (t[0], "yes" if t[1] else "no",
                                                       "yes" if t[2] else "no",
                                                       "yes" if t[3] else "no")
                    for t in K.trace]
        first = kname in FIRST_WAVE
        if (self.variant == "ulp-rare" and first and zlib.crc32(line.encode()) % 256 == 0
                and len(out) > 1):
            out[1] = A.succ(out[1])
        if self.variant == "not-normalized" and first and len(out) == 2:
            z0, z1 = out
            if type(z0) is int and type(z1) is int and z0 != 0:
                n = A.succ(z0)
                if type(n) is int and A.member(z1 - (n - z0)):
                    out = [n, z1 - (n - z0)]
        return pre + [line + " -> " + " ".join(
            ("1" if v else "0") if type(v) is bool else A.write(v) for v in out)]

    def corrupt(self, kname, A, args):
        args = list(args)
        pairs = PAIRS.get(kname)
        if pairs:
            i = pairs[0]
            # (x0, x0) is not normalized unless x0 = 0, and (lambda, lambda) is not either.
            if A.read(args[i]) == 0:
                args[i] = A.write(A.lam)
            args[i + 1] = args[i]
            return args
        if kname == "fast_two_sum":
            a, b = A.read(args[0]), A.read(args[1])
            if type(a) is int and type(b) is int and abs(a) != abs(b):
                if abs(a) > abs(b):
                    args[0], args[1] = args[1], args[0]
                return args
        # No requirement to break: write v + spacing/2 (or eta/2 for a zero), which has one
        # bit more than the format holds, so the operand itself is outside the format.
        v = A.read(args[0])
        if type(v) is int and v != 0:
            s = A.spacing_above(v)
            args[0] = _exact_hex_out(2 * v + (s if v > 0 else -s), A.qmin - 1)
        else:
            args[0] = _exact_hex_out(1, A.qmin - 1)
        return args

    def run(self, inp, out):
        w = out.write
        for line in inp:
            for o in self.complete(line):
                w(o)
                w("\n")


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="kairn-oracle refrun",
                                 description="Reference runner (pure Python, any binary format).")
    ap.add_argument("--variant", default="correct", help="one of: " + ", ".join(VARIANTS))
    ap.add_argument("--list-variants", action="store_true")
    ap.add_argument("--center-claims",
                    help="claims file whose bounds of add_2_2, mul_2_2 and mul_2_1 give the Ball "
                         "constants U and V (default: the oracle's first-wave fixture)")
    ap.add_argument("--print-constants", metavar="FORMAT",
                    help="print U and V of every center kernel, and E, G and H of every Ball "
                         "kernel (second radius design), for FORMAT and stop")
    ap.add_argument("--radius", default="first", choices=RADIUS_DESIGNS,
                    help="the Ball cores' radius: the first design (steps to the next number up) "
                         "or the second (one inflation at the end); default first")
    a = ap.parse_args(argv)
    if a.list_variants:
        for k, v in VARIANTS.items():
            print("%-24s %s" % (k, v))
        return 0
    if a.print_constants:
        ar = Arith(parse_format_triple(a.print_constants))
        for center in sorted(set(CENTER_KERNEL.values())):
            U, V = ball_constants(ar, center, a.center_claims or DEFAULT_CENTER_CLAIMS)
            print("%s.%s.U=%s" % (a.print_constants, center, ar.write(U)))
            print("%s.%s.V=%s" % (a.print_constants, center, ar.write(V)))
        for kname in sorted(RADIUS2):
            for which, v in zip("EGH", radius2_constants(ar, kname)):
                print("%s.%s.%s=%s" % (a.print_constants, kname, which, ar.write(v)))
        return 0
    Runner(a.variant, a.center_claims, a.radius).run(sys.stdin, sys.stdout)
    sys.stdout.flush()
    return 0
