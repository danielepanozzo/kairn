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
    # Milestone 2: the building blocks on T and the scaling of a ball by a power of two.
    "next-up-neg-away": "next_up of a negative finite number moves away from zero",
    "next-up-ninf": "next_up(-inf) is -inf instead of -Omega",
    "next-down-zero": "next_down of a zero is -0 (no step) instead of -eta",
    "dir-sum-nearest": "the directed sums return the sum rounded to nearest",
    "dir-sum-overflow-inf": "the directed sums return the infinity of the rounded sum on finite "
                            "operands that overflow (+inf for rounding down above the range)",
    "mul-bound-wrong-side": "the directed products step the other way: one number on the wrong "
                            "side",
    "mul-bound-two-beyond": "the directed products step twice where they cannot decide (below P, "
                            "computed error zero)",
    "mul-large-step": "the directed products step whenever the computed error is zero, above P "
                      "too",
    "pow2-radius-small": "the scaling of a ball by a power of two returns a radius one number "
                         "smaller",
    "pow2-grow-exact": "the scaling of a ball by a power of two grows the radius by two steps even "
                       "where it is exact",
    "pow2-zero-radius-grows": "the scaling of a ball by a power of two takes a zero radius as not "
                              "exact",
    "pow2-center-off": "the scaling of a ball by a power of two moves the center by one unit where "
                       "it is exact, and widens the radius to keep the set enclosed",
    "pow2-scale-eta": "mul_pow2_2 adds eta to its second limb where both limb products are zero "
                      "or at least N, keeping the error within eta",
    # The folds' stage of Milestone 2: the folds, their steps, finishes and bounds.
    "fold-drop-last": "every fold leaves out its last element",
    "fold-lanes-reverse": "the lane order combines the lanes from the last one down (other bits, "
                          "not an error: the claim is a bound for every order)",
    "fold-lanes-skip-lane": "the lane order leaves the last lane out of the combination",
    "dot-single-product": "dot_step_2, and so dot_2, multiplies the leading limbs only, rounded",
    "flag-true-nan": "the finishes return the state with the flag true, whatever its leading limb",
    "flag-false-finite": "the finishes return a negative finite state as it is, with the flag "
                         "false",
    "fold-not-normalized": "the folds of two limbs return (succ z0, z1 - (succ z0 - z0)) when that "
                           "is exact: the same value, not normalized",
    "bound-g-pred": "the bound kernels return g one number of the format smaller when ok is true",
    "bound-ok-beyond": "the bound kernels return ok true for every count",
    # The interval kernels.
    "iv-sum-nearest": "interval_add_1 and interval_sub_1 round their bounds to nearest",
    "iv-empty-whole": "the interval sums and products of one limb give the whole line for an empty "
                      "operand",
    "iv-mul-zero-nan": "mul_dir_1 without the zero factor: 0 * inf is a NaN, a zero factor the "
                       "rounded product stepped",
    "iv-mul-step-large": "mul_dir_1 steps outward whenever the computed error is zero, above P too",
    "iv-neg-not-swapped": "the negations of intervals negate each bound without exchanging them",
    "iv-make-nan-empty": "the constructors of intervals give the empty set for a NaN bound (the "
                         "rule of IEEE 1788, not Kairn's)",
    "iv-make-reversed": "the constructors of intervals keep reversed bounds",
    "iv2-no-zero-rule": "the bounds of two-limb sums move a sum that is zero by d (no select)",
    "iv2-wrong-side": "the bounds of two limbs move the second limb to the wrong side",
    "iv2-wide": "the bounds of two limbs move by 4 d instead of d (valid, not tight)",
    "iv2-keep-nonfinite": "the interval sums of two limbs keep a bound that is not finite as the "
                          "core returned it",
    "iv-mulext-inf-sign": "mul_ext_2_2 gives the infinity of the wrong sign for an infinite operand",
    "iv-hull-as-intersection": "the hulls return the intersection",
    "iv-intersection-no-empty": "the intersections keep crossed bounds instead of the empty set",
    "iv-mid-no-move": "interval_mid_rad_1 without the moves into [l, h]",
    "iv-mid-radius-small": "interval_mid_rad_1 returns the radius one number smaller",
    "iv-mid-radius-large": "interval_mid_rad_1 returns the radius one number larger",
    "iv-tball-halfline": "interval_to_ball_1 keeps the center +-Omega of a half-line",
    "iv-split-gap": "interval_split_1 starts the second part one number after the split point",
    "iv-ballbound-nearest": "the bounds of a ball round c - r and c + r to nearest",
    "iv-ballbound-empty-nan": "the bounds of a ball give a NaN for the empty ball",
    "iv-fromint-no-step": "ball_from_interval_2 does not step the radius when a halving is inexact",
    "iv-fromint-nan-empty": "ball_from_interval_2 gives the empty set for a NaN bound",
    "iv-narrow-no-tail": "ball_narrow_2_1 keeps the radius without the second limb of the center",
    "iv-ball-no-term": "add_ball_2_2 and mul_ball_2_2 return d = H, without the center's error",
    "iv-to-interval-nearest": "ball_to_interval_1 rounds c - r and c + r to nearest",
    # kairn::rational<X>(num, den) (rational_1, rational_2).
    "rat-lead-ulp": "rational: the first limb one unit in the last place too large, in about 1 "
                    "line in 4",
    "rat-tail-ulp": "rational_2: the second limb one unit in the last place too large, in about 1 "
                    "line in 4",
    "rat-naive-pair": "rational_2: the pair (RN(q), RN(q - RN(q))), not normalized near some ties",
    "rat-error-small": "rational: the error one number of the format too small when not zero",
    "rat-error-large": "rational: the error one number of the format too large",
    "rat-exact-flip": "rational: the flag exact wrong in about 1 line in 4",
    "rat-den0-finite": "rational: zero limbs for den = 0 instead of NaN",
    "rat-tie-away": "rational: ties rounded away from zero instead of to even",
    "rat-truncate": "rational: every rounding to nearest truncates instead",
}

ORACLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CENTER_CLAIMS = os.path.join(ORACLE_DIR, "selftest", "claims-wave1.json")
# The bounds of the folds' stage take unit(K) and tiny(K) of add_1_1, add_2_2, mul_1_1 and mul_2_2
# from a claims file: the fixture of that stage unless --bound-claims says otherwise.
DEFAULT_BOUND_CLAIMS = os.path.join(ORACLE_DIR, "selftest", "claims-wave5.json")
BOUND_KERNEL = {"bound_sum_1": "add_1_1", "bound_sum_2": "add_2_2", "bound_dot_1": "mul_1_1",
                "bound_dot_2": "mul_2_2"}
# The folds of architecture.md, "Folds": step, combination, finish and the limbs of the state.
FOLDS = {"sum_1": ("add_1_1", "add_1_1", "fold_finish_1", 1),
         "sum_1_entry": ("sum_entry_step_1", "add_1_1", "fold_finish_1", 1),
         "sum_2": ("add_2_2", "add_2_2", "fold_finish_2", 2),
         "sum_2_entry": ("sum_entry_step_2", "add_2_2", "fold_finish_2", 2),
         "sum_fast_2": ("add_fast_2_2", "add_fast_2_2", "fold_finish_2", 2),
         "sum_fast_2_entry": ("sum_fast_entry_step_2", "add_fast_2_2", "fold_finish_2", 2),
         "dot_1": ("dot_step_1", "add_1_1", "fold_finish_1", 1),
         "dot_2": ("dot_step_2", "add_2_2", "fold_finish_2", 2)}
# The limbs of an element of each fold: those of its arrays, in order.
FOLD_WIDTH = {"sum_1": 1, "sum_1_entry": 1, "sum_2": 2, "sum_2_entry": 2, "sum_fast_2": 2,
              "sum_fast_2_entry": 2, "dot_1": 2, "dot_2": 4}

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
        H = (1+u)((1+u)^2 eta + 1/2 eta) + N            for sums,
            (1+u)((1+u)^2 eta + V_q + 1/2 eta) + N      for scalings,
            (1+u)(2(1+u)^4 eta + V_q + 1/2 eta) + N     for ball_mul_1,
            (1+u)(2(1+u)^5 eta + V_q + 1/2 eta) + N     for ball_mul_2,
    with U_q = rel/(1 - rel) and V_q = tiny/(1 - rel) of the center kernel's proved bound, and
    N = 2^(p-1) eta the smallest normal number, which no bound needs: it makes H a normal number
    (the page's "Why H contains N")."""
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
    H += Fraction(1 << (p - 1))                # N, in units of eta
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
    def __init__(self, ar, center_claims=DEFAULT_CENTER_CLAIMS, radius="first",
                 bound_claims=None):
        self.A = ar
        self.v = ar.variant
        self.bound_claims = bound_claims or DEFAULT_BOUND_CLAIMS
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
        z = self.fast_two_sum(h, l, "final")
        # A rounded product above N comes from an exact one above N, which was exact: the result
        # is exact there, and eta more is within the bound of eta.
        if (self.v == "pow2-scale-eta" and self._finite(h, l, *z) and z[0]
                and abs(h) > A.lam and (x1 == 0 or abs(l) > A.lam)):
            t = z[1] + 1
            if A.member(t) and A.add(z[0], t) == z[0]:
                z = (z[0], t)
        return z

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

    # -- Milestone 2 (milestone2.md, "Building blocks on T", "Scaling a ball by a power of two"),
    # as listed, on IEEE values: the neighbors, the directed sums and products, the entry forms,
    # the scaling of a ball by a power of two and its full form -------------------------------
    def next_up(self, a):
        A = self.A
        if self.v == "next-up-ninf" and a == -INF:
            return (-INF,)
        if self.v == "next-up-neg-away" and type(a) is int and a < 0:
            return (A.next_down(a),)
        return (A.next_up(a),)

    def next_down(self, a):
        if self.v == "next-down-zero" and a == 0:
            return (NEG_ZERO,)
        return (self.A.next_down(a),)

    # The same kernels as claims of the finite domain (the oracle's fixture only).
    next_up_real = next_up
    next_down_real = next_down

    def two_sum_ord(self, a, b):
        """Fast2Sum on the operands ordered by magnitude, the comparison as two selects."""
        m = abs(a) < abs(b)
        h = b if m else a
        l = a if m else b
        return self.fast_two_sum(h, l)

    def _directed_sum(self, a, b, up):
        A = self.A
        s, e = self.two_sum_ord(a, b)
        if self.v == "dir-sum-nearest":
            return (s,)
        n = (0 < e) if up else (e < 0)
        t = A.next_up(s) if up else A.next_down(s)
        r = t if n else s
        if self.v == "dir-sum-overflow-inf" and self._finite(a, b) and type(s) is float:
            r = s
        return (r,)

    def add_down_1(self, a, b):
        return self._directed_sum(a, b, False)

    def add_up_1(self, a, b):
        return self._directed_sum(a, b, True)

    def sub_down_1(self, a, b):
        return self._directed_sum(a, -b, False)

    def sub_up_1(self, a, b):
        return self._directed_sum(a, -b, True)

    def _const_P(self):
        """const up(eta/(2*u^2)) = 2^(2p-1) eta, rounded up to the format (+inf beyond Omega)."""
        return self.A.round_up_fraction(Fraction(1 << (2 * self.A.p - 1)))

    def _directed_prod(self, a, b, up):
        A = self.A
        p, e = self.two_prod(a, b)
        ap = abs(p)
        bd = ap < self._const_P()
        if self.v == "mul-large-step":
            bd = True
        ez = e == 0
        un = bd and ez
        n = (0 < e) if up else (e < 0)
        sd = n or un
        out = A.next_up if up else A.next_down
        if self.v == "mul-bound-wrong-side":
            out = A.next_down if up else A.next_up
        step = out(p)
        if self.v == "mul-bound-two-beyond" and un:
            step = out(step)
        d = step if sd else p
        zz = a == 0 or b == 0
        return (p if zz else d,)

    def mul_down_1(self, a, b):
        return self._directed_prod(a, b, False)

    def mul_up_1(self, a, b):
        return self._directed_prod(a, b, True)

    mul_down_real = mul_down_1
    mul_up_real = mul_up_1
    mul_down_bound_real = mul_down_1

    # The entry forms: both operands guarded, then the kernel of the same name.
    def two_sum_entry(self, a, b):
        return self.two_sum(self.guard(a), self.guard(b))

    def fast_two_sum_entry(self, a, b):
        return self.fast_two_sum(self.guard(a), self.guard(b))

    def radd_entry(self, a, b):
        return self.radd(self.guard(a), self.guard(b))

    def add_down_entry(self, a, b):
        return self.add_down_1(self.guard(a), self.guard(b))

    def add_up_entry(self, a, b):
        return self.add_up_1(self.guard(a), self.guard(b))

    def sub_down_entry(self, a, b):
        return self.sub_down_1(self.guard(a), self.guard(b))

    def sub_up_entry(self, a, b):
        return self.sub_up_1(self.guard(a), self.guard(b))

    def _ball_mul_pow2(self, cx, rx, c):
        A = self.A
        N = A.lam                                  # const up(eta/(2*u)), exact
        h = A.prod(cx[0], c)
        if len(cx) == 2:
            l = A.prod(cx[1], c)
            cz = self.fast_two_sum(h, l)
            m = h if cx[1] == 0 else l             # the scaled last nonzero limb
        else:
            cz = (h,)
            m = h
        rr = A.prod(rx, c)
        ec = N < abs(m) or cx[0] == 0              # the center was scaled exactly
        zr = rx == 0
        if self.v == "pow2-zero-radius-grows":
            zr = False
        er = N < rr or zr                          # the radius was scaled exactly
        ex = ec and er
        if self.v == "pow2-grow-exact":
            ex = False
        rz = rr if ex else A.next_up(A.next_up(rr))
        if self.v == "pow2-radius-small" and type(rz) is int and rz > 0:
            rz = A.next_down(rz)
        if self.v == "pow2-center-off" and ex and self._finite(rz, *cz):
            cz, rz = self._center_off(cz, rz)
        return cz + (rz,)

    def _center_off(self, cz, rz):
        """The center moved by one unit (eta in the second limb of a pair, when the pair stays
        normalized; the next number for one limb) and the radius widened by as much, rounded
        up, so that the set stays enclosed."""
        A = self.A
        if len(cz) == 2:
            t = cz[1] + 1
            if not (A.member(t) and A.add(cz[0], t) == cz[0]):
                return cz, rz
            new, shift = (cz[0], t), 1
        else:
            n = A.next_up(cz[0])
            if type(n) is not int:
                return cz, rz
            new, shift = (n,), n - cz[0]
        r = A.round_up_fraction(Fraction(rz + shift))
        return (new, r) if type(r) is int else (cz, rz)

    def ball_mul_pow2_1(self, cx, rx, c):
        return self._ball_mul_pow2((cx,), rx, c)

    def ball_mul_pow2_2(self, cx0, cx1, rx, c):
        return self._ball_mul_pow2((cx0, cx1), rx, c)

    def ball_mul_pow2_1_full(self, cx, rx, c):
        return self._ball_fixup(self.ball_mul_pow2_1(cx, rx, c), 1, rx)

    def ball_mul_pow2_2_full(self, cx0, cx1, rx, c):
        return self._ball_fixup(self.ball_mul_pow2_2(cx0, cx1, rx, c), 2, rx)

    # -- the folds' stage of Milestone 2 (architecture.md, "Folds"; milestone2.md, "Batch
    # kernels"), as listed there ----------------------------------------------------------------
    def dot_step_1(self, s, x, y):
        """t = fma(x, y, s)."""
        return (self.A.fma(x, y, s),)

    def dot_step_2(self, s0, s1, x0, x1, y0, y1):
        """p = mul_2_2(x, y); t = add_2_2(s, p)."""
        if self.v == "dot-single-product":
            p = (self.A.prod(x0, y0), 0)
        else:
            p = self.mul_2_2(x0, x1, y0, y1)
        return self.add_2_2(s0, s1, p[0], p[1])

    def sum_entry_step_1(self, s, x):
        return self.add_1_1(s, self.guard(x))

    def sum_entry_step_2(self, s0, s1, x0, x1):
        return self.add_2_2(s0, s1, self.guard(x0), self.guard(x1))

    def sum_fast_entry_step_2(self, s0, s1, x0, x1):
        return self.add_fast_2_2(s0, s1, self.guard(x0), self.guard(x1))

    def _finish(self, s):
        """The state with the flag true when its leading limb is finite; otherwise the canonical
        NaN, every limb a NaN, with the flag false."""
        f = type(s[0]) is int
        if self.v == "flag-true-nan":
            return tuple(s) + (True,)
        if self.v == "flag-false-finite" and f and s[0] < 0:
            return tuple(s) + (False,)
        if f:
            return tuple(s) + (True,)
        return (NAN,) * len(s) + (False,)

    def fold_finish_1(self, s):
        return self._finish((s,))

    def fold_finish_2(self, s0, s1):
        return self._finish((s0, s1))

    def _const_up(self, f):
        """const up(EXPR): the smallest number of the format not below the rational f."""
        A = self.A
        per_eta = Fraction(1 << -A.qmin) if A.qmin < 0 else Fraction(1, 1 << A.qmin)
        return A.round_up_fraction(f * per_eta)

    def _bound_constants(self, kname):
        """unit and tiny of the kernel K the bound is for (c u^k and t eta of its error entry in
        the bound claims, by default the fixture claims-wave5.json), and the constants of the
        listing of milestone2.md, "The bound as a function of n", rounded up to the format."""
        key = ("bound", kname)
        c = self._consts.get(key)
        if c is None:
            K = BOUND_KERNEL[kname]
            cc, k, t = center_bound(K, self.bound_claims)
            A = self.A
            u = Fraction(1, 1 << A.p)
            eta = Fraction(1, 1 << -A.qmin) if A.qmin < 0 else Fraction(1 << A.qmin)
            unit = _eval_rational(cc, u) * u ** k
            tiny = t * eta
            up = self._const_up
            c = self._consts[key] = {
                "a": up((1 + u) * (unit + eta / 2)), "aa": up((1 + u) ** 2 * (unit + eta)),
                "w": up(1 + 2 * u), "quarter": up(Fraction(1, 4)), "one": up(Fraction(1)),
                "tm": up((1 + u) ** 2 * (tiny + eta))}
        return c

    def _bound(self, kname, m):
        A = self.A
        c = self._bound_constants(kname)
        a = A.prod(m, c["a"])
        aa = A.prod(m, c["aa"])
        d = A.add(a, a)
        w = A.add(d, c["w"])
        g = A.prod(aa, w)
        ok = a <= c["quarter"]
        out = [g]
        if kname.startswith("bound_dot"):
            tm = A.prod(m, c["tm"])
            wg = A.add(g, c["w"])
            t = A.prod(tm, wg)
            ok = ok and g <= c["one"]
            out.append(t)
        if self.v == "bound-ok-beyond":
            ok = True
        if self.v == "bound-g-pred" and ok and type(g) is int:
            out[0] = A.next_down(g)
        return tuple(out) + (bool(ok),)

    def bound_sum_1(self, m):
        return self._bound("bound_sum_1", m)

    def bound_sum_2(self, m):
        return self._bound("bound_sum_2", m)

    def bound_dot_1(self, m):
        return self._bound("bound_dot_1", m)

    def bound_dot_2(self, m):
        return self._bound("bound_dot_2", m)

    def fold(self, name, order, elems):
        """A fold of architecture.md, "Folds", in an order: None for the sequential one (the step
        element after element from the zero state), W for the lane order (the first W floor(n/W)
        elements dealt to W lanes, element i to lane i mod W; each lane folded from the zero
        state; the lanes combined from lane 0 upward; the remaining n mod W folded into the
        result).  Returns the finish's outputs."""
        step, combine, finish, k = FOLDS[name]
        step, combine, finish = getattr(self, step), getattr(self, combine), getattr(self, finish)
        v = self.v
        zero = (0,) * k
        if v == "fold-drop-last" and elems:
            elems = elems[:-1]

        def run(state, xs):
            for x in xs:
                state = step(*(tuple(state) + tuple(x)))
            return state

        n = len(elems)
        if order is None or order <= 1:
            s = run(zero, elems)
        else:
            W = order
            full = W * (n // W)
            lanes = [run(zero, elems[j:full:W]) for j in range(W)]
            if v == "fold-lanes-reverse":
                lanes = lanes[::-1]
            if v == "fold-lanes-skip-lane" and full:
                lanes = lanes[:-1]
            s = lanes[0]
            for l in lanes[1:]:
                s = combine(*(tuple(s) + tuple(l)))
            s = run(s, elems[full:])
        out = list(finish(*s))
        if v == "fold-not-normalized" and k == 2 and out[-1] and type(out[0]) is int and out[0]:
            z0, z1 = out[0], out[1]
            nb = self.A.succ(z0)
            if type(nb) is int and self.A.member(z1 - (nb - z0)):
                out[0], out[1] = nb, z1 - (nb - z0)
        return out

    # -- the interval kernels (milestone2.md, "Interval kernels", "One enclosure interface"), as
    # listed there, on IEEE values; a ball of two limbs to one limb by its own listing below ------
    def _half(self):
        """const up(1/2)."""
        return self._const_up(Fraction(1, 2))

    def _iv_consts(self, kname):
        """E, G, H of the Ball kernel kname (the second radius design), rounded up."""
        key = ("iv", kname)
        c = self._consts.get(key)
        if c is None:
            c = self._consts[key] = radius2_constants(self.A, kname)
        return c

    def mul_dir_1(self, a, b):
        """The lines of mul_down_1 and mul_up_1 on one two_prod; a zero factor gives the literal
        zero (0 * inf = 0)."""
        A = self.A
        p, e = self.two_prod(a, b)
        ap = abs(p)
        bd = ap < self._const_P()
        if self.v == "iv-mul-step-large":
            bd = True
        ez = e == 0
        un = bd and ez
        sd = (e < 0) or un
        su = (0 < e) or un
        dz = A.next_down(p) if sd else p
        vz = A.next_up(p) if su else p
        zz = a == 0 or b == 0
        if self.v == "iv-mul-zero-nan":
            return dz, vz
        return (0 if zz else dz), (0 if zz else vz)

    def _iv_empty(self, ne, l, h):
        if self.v == "iv-empty-whole" and not ne:
            return -INF, INF
        return (l if ne else INF), (h if ne else -INF)

    def interval_neg_1(self, xl, xu):
        if self.v == "iv-neg-not-swapped":
            return -xl, -xu
        return -xu, -xl

    def interval_add_1(self, xl, xu, yl, yu):
        (l,) = self.add_down_1(xl, yl)
        (h,) = self.add_up_1(xu, yu)
        if self.v == "iv-sum-nearest":
            l, h = self.A.add(xl, yl), self.A.add(xu, yu)
        return self._iv_empty(xl < INF and yl < INF, l, h)

    def interval_sub_1(self, xl, xu, yl, yu):
        (l,) = self.sub_down_1(xl, yu)
        (h,) = self.sub_up_1(xu, yl)
        if self.v == "iv-sum-nearest":
            l, h = self.A.sub(xl, yu), self.A.sub(xu, yl)
        return self._iv_empty(xl < INF and yl < INF, l, h)

    def interval_mul_1(self, xl, xu, yl, yu):
        d1, v1 = self.mul_dir_1(xl, yl)
        d2, v2 = self.mul_dir_1(xl, yu)
        d3, v3 = self.mul_dir_1(xu, yl)
        d4, v4 = self.mul_dir_1(xu, yu)
        da = d2 if d2 < d1 else d1
        db = d4 if d4 < d3 else d3
        l = db if db < da else da
        va = v2 if v1 < v2 else v1
        vb = v4 if v3 < v4 else v3
        h = vb if va < vb else va
        return self._iv_empty(xl < INF and yl < INF, l, h)

    def interval_make_1(self, lo, hi):
        gl, gu = self.guard(lo), self.guard(hi)
        ok = gl <= gu
        v = ok and gl < INF and -INF < gu
        nn = gl == gl and gu == gu
        if self.v == "iv-make-nan-empty":
            nn = True
        if self.v == "iv-make-reversed" and nn and not ok:
            v = True
        el = INF if nn else -INF
        eu = -INF if nn else INF
        return (gl if v else el), (gu if v else eu)

    def add_ball_2_2(self, x0, x1, y0, y1):
        A = self.A
        E, G, H = self._iv_consts("ball_add_2")
        z0, z1 = self.add_2_2(x0, x1, y0, y1)
        t = A.prod(abs(z0), E)
        d = H if self.v == "iv-ball-no-term" else A.fma(t, G, H)
        return z0, z1, d

    def mul_ball_2_2(self, x0, x1, y0, y1):
        A = self.A
        E, G, H = self._iv_consts("ball_mul_2")
        z0, z1 = self.mul_2_2(x0, x1, y0, y1)
        t = A.prod(abs(z0), E)
        d = H if self.v == "iv-ball-no-term" else A.fma(t, G, H)
        return z0, z1, d

    def _add_dir_2_2(self, x0, x1, y0, y1, up):
        A = self.A
        z0, z1, d = self.add_ball_2_2(x0, x1, y0, y1)
        dd = 0 if z0 == 0 and self.v != "iv2-no-zero-rule" else d
        if self.v == "iv2-wide" and type(dd) is int:
            dd = A.prod(dd, self._const_up(Fraction(4)))
        if self.v == "iv2-wrong-side":
            up = not up
        (w,) = self.add_up_1(z1, dd) if up else self.sub_down_1(z1, dd)
        return self.two_sum_ord(z0, w)

    def add_down_2_2(self, x0, x1, y0, y1):
        return self._add_dir_2_2(x0, x1, y0, y1, False)

    def add_up_2_2(self, x0, x1, y0, y1):
        return self._add_dir_2_2(x0, x1, y0, y1, True)

    def sub_down_2_2(self, x0, x1, y0, y1):
        return self._add_dir_2_2(x0, x1, -y0, -y1, False)

    def sub_up_2_2(self, x0, x1, y0, y1):
        return self._add_dir_2_2(x0, x1, -y0, -y1, True)

    def mul_dir_2_2(self, x0, x1, y0, y1):
        A = self.A
        z0, z1, d = self.mul_ball_2_2(x0, x1, y0, y1)
        if self.v == "iv2-wide" and type(d) is int:
            d = A.prod(d, self._const_up(Fraction(4)))
        lo_up, hi_up = (True, False) if self.v == "iv2-wrong-side" else (False, True)
        (wl,) = self.add_up_1(z1, d) if lo_up else self.sub_down_1(z1, d)
        (wu,) = self.add_up_1(z1, d) if hi_up else self.sub_down_1(z1, d)
        return self.two_sum_ord(z0, wl) + self.two_sum_ord(z0, wu)

    def _ball_bound_1(self, c, r, up):
        A = self.A
        (b,) = self.add_up_1(c, r) if up else self.sub_down_1(c, r)
        if self.v == "iv-ballbound-nearest":
            b = A.add(c, r) if up else A.sub(c, r)
        if self.v == "iv-ballbound-empty-nan":
            return b
        return b if r == r else (-INF if up else INF)

    def ball_lower_as_1(self, c, r):
        return (self._ball_bound_1(c, r, False),)

    def ball_upper_as_1(self, c, r):
        return (self._ball_bound_1(c, r, True),)

    def ball_lower_as_2(self, c0, c1, r):
        (t,) = self.to_down_2(c0, c1)
        return (self._ball_bound_1(t, r, False),)

    def ball_upper_as_2(self, c0, c1, r):
        (t,) = self.to_up_2(c0, c1)
        return (self._ball_bound_1(t, r, True),)

    def ball_narrow_2_1(self, c0, c1, r):
        """A ball of two limbs as a ball of one: the leading limb as the center, the radius grown
        by the magnitude of the second limb and stepped up (radd); the special states as they
        are, and the whole line when the radius is not finite."""
        A = self.A
        if r != r:
            return NAN, NAN
        if r == INF:
            return 0, INF
        rz = r if c1 == 0 or self.v == "iv-narrow-no-tail" else A.next_up(A.add(r, abs(c1)))
        if not rz < INF:
            return 0, INF
        return c0, rz

    def ball_from_interval_2(self, lo, hi):
        A = self.A
        gl, gu = self.guard(lo), self.guard(hi)
        half = self._half()
        hl, hu = A.prod(gl, half), A.prod(gu, half)
        c0, c1 = self.two_sum_ord(hl, hu)
        (d,) = self.sub_up_1(hu, hl)
        xx = A.add(hl, hl) == gl and A.add(hu, hu) == gu
        r = d if xx or self.v == "iv-fromint-no-step" else A.next_up(d)
        v = gl <= gu and gl < INF and -INF < gu
        f = -INF < gl and gu < INF
        k0, k1, s = (c0, c1, r) if f else (0, 0, INF)
        nn = gl == gl and gu == gu
        if self.v == "iv-fromint-nan-empty":
            nn = True
        wc, wr = (NAN, NAN) if nn else (0, INF)
        return (k0, k1, s) if v else (wc, wc, wr)

    def _iv2_finish(self, l, h, ne):
        l0, l1 = l
        h0, h1 = h
        fl, fh = abs(l0) < INF, abs(h0) < INF
        a0, a1 = (l0, l1) if fl else (-INF, 0)
        b0, b1 = (h0, h1) if fh else (INF, 0)
        if self.v == "iv2-keep-nonfinite":
            a0, a1, b0, b1 = l0, l1, h0, h1
        return (a0, a1, b0, b1) if ne else (INF, 0, -INF, 0)

    def interval_add_2(self, xl0, xl1, xu0, xu1, yl0, yl1, yu0, yu1):
        l = self.add_down_2_2(xl0, xl1, yl0, yl1)
        h = self.add_up_2_2(xu0, xu1, yu0, yu1)
        return self._iv2_finish(l, h, xl0 < INF and yl0 < INF)

    def interval_sub_2(self, xl0, xl1, xu0, xu1, yl0, yl1, yu0, yu1):
        l = self.sub_down_2_2(xl0, xl1, yu0, yu1)
        h = self.sub_up_2_2(xu0, xu1, yl0, yl1)
        return self._iv2_finish(l, h, xl0 < INF and yl0 < INF)

    def interval_neg_2(self, xl0, xl1, xu0, xu1):
        if self.v == "iv-neg-not-swapped":
            return -xl0, -xl1, -xu0, -xu1
        return -xu0, -xu1, -xl0, -xl1

    def interval_make_2(self, lo0, lo1, hi0, hi1):
        ok = lo0 < hi0 or (lo0 == hi0 and lo1 <= hi1)
        v = ok and lo0 < INF and -INF < hi0
        nn = lo0 == lo0 and hi0 == hi0
        if self.v == "iv-make-nan-empty":
            nn = True
        if self.v == "iv-make-reversed" and nn and not ok:
            v = True
        el = (INF, 0) if nn else (-INF, 0)
        eu = (-INF, 0) if nn else (INF, 0)
        return ((lo0, lo1) if v else el) + ((hi0, hi1) if v else eu)

    def mul_ext_2_2(self, x0, x1, y0, y1):
        A = self.A
        c0, c1, e0, e1 = self.mul_dir_2_2(x0, x1, y0, y1)
        t = A.prod(x0, y0)
        if self.v == "iv-mulext-inf-sign":
            t = -t
        fo = abs(x0) < INF and abs(y0) < INF
        nz = not (x0 == 0 or y0 == 0)
        p = (c0, c1) if abs(c0) < INF else (-INF, 0)
        q = (e0, e1) if abs(e0) < INF else (INF, 0)
        r = p if fo else (t, 0)
        s = q if fo else (t, 0)
        return (r if nz else (0, 0)) + (s if nz else (0, 0))

    def _lt2(self, a, b):
        return self.lt_2_2(a[0], a[1], b[0], b[1])[0]

    def interval_mul_2(self, xl0, xl1, xu0, xu1, yl0, yl1, yu0, yu1):
        xl, xu, yl, yu = (xl0, xl1), (xu0, xu1), (yl0, yl1), (yu0, yu1)
        m = [self.mul_ext_2_2(*(a + b)) for a, b in ((xl, yl), (xl, yu), (xu, yl), (xu, yu))]
        L = [t[:2] for t in m]
        H = [t[2:] for t in m]
        la = L[1] if self._lt2(L[1], L[0]) else L[0]
        lb = L[3] if self._lt2(L[3], L[2]) else L[2]
        l = lb if self._lt2(lb, la) else la
        ha = H[1] if self._lt2(H[0], H[1]) else H[0]
        hb = H[3] if self._lt2(H[2], H[3]) else H[2]
        h = hb if self._lt2(ha, hb) else ha
        ne = xl0 < INF and yl0 < INF
        return (l + h) if ne else (INF, 0, -INF, 0)

    def interval_hull_1(self, xl, xu, yl, yu):
        if self.v == "iv-hull-as-intersection":
            return self.interval_intersection_1(xl, xu, yl, yu)
        return (yl if yl < xl else xl), (yu if xu < yu else xu)

    def interval_hull_2(self, xl0, xl1, xu0, xu1, yl0, yl1, yu0, yu1):
        if self.v == "iv-hull-as-intersection":
            return self.interval_intersection_2(xl0, xl1, xu0, xu1, yl0, yl1, yu0, yu1)
        xl, xu, yl, yu = (xl0, xl1), (xu0, xu1), (yl0, yl1), (yu0, yu1)
        return (yl if self._lt2(yl, xl) else xl) + (yu if self._lt2(xu, yu) else xu)

    def interval_intersection_1(self, xl, xu, yl, yu):
        zl = yl if xl < yl else xl
        zu = yu if yu < xu else xu
        if zu < zl and self.v != "iv-intersection-no-empty":
            return INF, -INF
        return zl, zu

    def interval_intersection_2(self, xl0, xl1, xu0, xu1, yl0, yl1, yu0, yu1):
        xl, xu, yl, yu = (xl0, xl1), (xu0, xu1), (yl0, yl1), (yu0, yu1)
        zl = yl if self._lt2(xl, yl) else xl
        zu = yu if self._lt2(yu, xu) else xu
        if self._lt2(zu, zl) and self.v != "iv-intersection-no-empty":
            return INF, 0, -INF, 0
        return zl + zu

    def interval_mid_rad_1(self, xl, xu):
        A = self.A
        om = A.next_down(INF)
        mo = -om
        ml = xl < mo
        l = mo if ml else xl
        mu = om < xu
        h = om if mu else xu
        half = self._half()
        hl, hu = A.prod(l, half), A.prod(h, half)
        ma = A.add(hl, hu)
        mb = l if ma < l else ma
        mc = h if h < mb else mb
        if self.v == "iv-mid-no-move":
            mc = ma
        (ra,) = self.sub_up_1(mc, l)
        (rb,) = self.sub_up_1(h, mc)
        rc = rb if ra < rb else ra
        if self.v == "iv-mid-radius-small" and type(rc) is int and rc > 0:
            rc = A.next_down(rc)
        if self.v == "iv-mid-radius-large" and type(rc) is int:
            rc = A.next_up(rc)
        md = mo if ml else mc
        me = om if mu else md
        mf = 0 if ml and mu else me
        rd = INF if ml or mu else rc
        ne = xl < INF
        return (mf if ne else NAN), (rd if ne else NAN)

    def interval_to_ball_1(self, xl, xu):
        m, r = self.interval_mid_rad_1(xl, xu)
        if r == INF and self.v != "iv-tball-halfline":
            m = 0
        return m, r

    def ball_to_interval_1(self, c, r):
        A = self.A
        (l,) = self.sub_down_1(c, r)
        (h,) = self.add_up_1(c, r)
        if self.v == "iv-to-interval-nearest":
            l, h = A.sub(c, r), A.add(c, r)
        ne = r == r
        return (l if ne else INF), (h if ne else -INF)

    def interval_split_1(self, xl, xu):
        m = self.interval_mid_rad_1(xl, xu)[0]
        ne = xl < INF
        bl = m
        if self.v == "iv-split-gap" and type(m) is int:
            bl = self.A.next_up(m)
        return xl, (m if ne else -INF), (bl if ne else INF), xu


# A negative zero as an output (next-down-zero): the fixed values have one zero.
NEG_ZERO = "-0x0p+0"


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
         "ball_make_2": 3, "add_1_1": 2, "mul_1_1": 2,
         # Milestone 2.
         "next_up": 1, "next_down": 1, "next_up_real": 1, "next_down_real": 1, "two_sum_ord": 2,
         "add_down_1": 2, "add_up_1": 2, "sub_down_1": 2, "sub_up_1": 2, "mul_down_1": 2,
         "mul_up_1": 2, "mul_down_real": 2, "mul_up_real": 2, "mul_down_bound_real": 2,
         "two_sum_entry": 2,
         "fast_two_sum_entry": 2, "radd_entry": 2, "add_down_entry": 2, "add_up_entry": 2,
         "sub_down_entry": 2, "sub_up_entry": 2, "ball_mul_pow2_1": 3, "ball_mul_pow2_2": 4,
         "ball_mul_pow2_1_full": 3, "ball_mul_pow2_2_full": 4,
         # The folds' stage.
         "dot_step_1": 3, "dot_step_2": 6, "sum_entry_step_1": 2, "sum_entry_step_2": 4,
         "sum_fast_entry_step_2": 4, "fold_finish_1": 1, "fold_finish_2": 2, "bound_sum_1": 1,
         "bound_sum_2": 1, "bound_dot_1": 1, "bound_dot_2": 1,
         # The interval kernels.
         "mul_dir_1": 2, "interval_make_1": 2, "interval_neg_1": 2, "interval_add_1": 4,
         "interval_sub_1": 4, "interval_mul_1": 4, "add_ball_2_2": 4, "mul_ball_2_2": 4,
         "add_down_2_2": 4, "add_up_2_2": 4, "sub_down_2_2": 4, "sub_up_2_2": 4, "mul_dir_2_2": 4,
         "ball_lower_as_1": 2, "ball_upper_as_1": 2, "ball_lower_as_2": 3, "ball_upper_as_2": 3,
         "ball_narrow_2_1": 3, "ball_from_interval_2": 2, "interval_add_2": 8, "interval_neg_2": 4,
         "interval_sub_2": 8, "interval_make_2": 4, "mul_ext_2_2": 4, "interval_mul_2": 8,
         "interval_hull_1": 4, "interval_hull_2": 8, "interval_intersection_1": 4,
         "interval_intersection_2": 8, "interval_mid_rad_1": 2, "interval_to_ball_1": 2,
         "ball_to_interval_1": 2, "interval_split_1": 2}
FIRST_WAVE = frozenset(("two_sum", "fast_two_sum", "two_prod", "two_prod_dekker", "split",
                        "add_2_2", "add_2_1", "mul_2_2", "mul_2_1", "add_fast_2_2"))
# kairn::rational<X>(num, den), with its number of limbs.
RATIONAL = {"rational_1": 1, "rational_2": 2}
# Which input limb pairs form a normalized 2-limb operand (for corrupt-input).
PAIRS = {"add_2_2": (0, 2), "add_2_1": (0,), "mul_2_2": (0, 2), "mul_2_1": (0,),
         "add_fast_2_2": (0, 2)}


class Runner:
    def __init__(self, variant="correct", center_claims=None, radius="first", bound_claims=None):
        if variant not in VARIANTS:
            raise ValueError("unknown variant %r (known: %s)" % (variant, ", ".join(VARIANTS)))
        if radius not in RADIUS_DESIGNS:
            raise ValueError("unknown radius design %r (first or second)" % radius)
        self.variant = variant
        self.center_claims = center_claims or DEFAULT_CENTER_CLAIMS
        self.bound_claims = bound_claims or DEFAULT_BOUND_CLAIMS
        self.radius = radius
        self.cache = {}

    def kernels(self, fmtname):
        k = self.cache.get(fmtname)
        if k is None:
            k = self.cache[fmtname] = Kernels(Arith(parse_format_triple(fmtname), self.variant),
                                              self.center_claims, self.radius, self.bound_claims)
        return k

    def fold_line(self, line, toks, tag):
        """FOLD FORMAT ORDER N LIMB ... [#TAG]: the arrays, limb by limb, N entries each."""
        name, fname, order, n = toks[0], toks[1], toks[2], int(toks[3])
        K = self.kernels(fname)
        A = K.A
        width = FOLD_WIDTH[name]
        limbs = toks[4:]
        if len(limbs) != n * width:
            raise ValueError("cannot run %r with %d limbs for %d elements" % (name, len(limbs), n))
        cols = [[A.read(t) for t in limbs[j * n:(j + 1) * n]] for j in range(width)]
        elems = list(zip(*cols)) if n else []
        if order == "seq":
            W = None
        elif order.startswith("lanes:"):
            W = int(order[6:])
        else:
            raise ValueError("unknown order %r" % order)
        out = K.fold(name, W, elems)
        return [line + " -> " + " ".join(("1" if v else "0") if type(v) is bool else A.write(v)
                                         for v in out)]

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
        if kname in RATIONAL:
            return [line + " -> " + self.rational(kname, fname, args, line)]
        if kname in FOLDS:
            return self.fold_line(line, toks, tag)
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
            ("1" if v else "0") if type(v) is bool else v if v is NEG_ZERO else A.write(v)
            for v in out)]

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

    # -- kairn::rational<X>(num, den) ----------------------------------------------------------
    #
    # From the specification (docs/developer/design/milestone2.md, "Constants at compile time"),
    # without the checker's code (rational.py), which divides and inspects the remainder: here
    # the rounding to nearest takes the smallest number not below |x| and the one before it and
    # compares the two distances, and the pair of rational_2 is the one of the three candidates
    # (z0, V - z0), z0 = RN(q) or a neighbour, that is normalized by this runner's own addition.

    def _nearest(self, A, x):
        """x (a Fraction, in units of eta) rounded to nearest, ties to even (the variants:
        away from zero, or truncated), with the IEEE overflow threshold."""
        if x == 0:
            return 0
        ax = abs(x)
        up = A.round_up_fraction(ax)
        if up == INF:
            # Beyond Omega: Omega below Omega + ulp(Omega)/2, the infinity from there on.
            half = Fraction(A.spacing_above(A.omega), 2)
            r = A.omega if self.variant == "rat-truncate" or ax < A.omega + half else INF
        elif up == ax:
            r = up
        else:
            down = A.next_down(up)
            below, above = ax - down, up - ax
            if self.variant == "rat-truncate":
                r = down
            elif below != above:
                r = down if below < above else up
            elif self.variant == "rat-tie-away":
                r = up
            else:
                r = down if A._canonical(down)[0] % 2 == 0 else up
        return r if x > 0 else -r

    def rational(self, kname, fname, args, line):
        k = RATIONAL[kname]
        A = self.cache.get(("rational", fname))
        if A is None:
            A = self.cache[("rational", fname)] = Arith(parse_format_triple(fname))
        if len(args) != 2:
            raise ValueError("cannot run %r with %d terms" % (kname, len(args)))
        num, den = int(args[0]), int(args[1])
        v = self.variant
        rare = zlib.crc32(line.encode()) % 4 == 0
        if den == 0:
            limbs = [0] * k if v == "rat-den0-finite" else [NAN] * k
            return " ".join([A.write(z) for z in limbs] + ["inf", "0"])
        # q in units of eta.
        q = Fraction(num << -A.qmin, den) if A.qmin < 0 else Fraction(num, den << A.qmin)
        a = self._nearest(A, q)
        if type(a) is float:
            limbs = [a] + [0] * (k - 1)
            return " ".join([A.write(z) for z in limbs] + ["inf", "0"])
        if k == 1:
            limbs = [a]
        else:
            b = self._nearest(A, q - a)
            value = a + b
            pairs = []
            if v in ("rat-tie-away", "rat-truncate"):
                # The faulty rounding renormalizes too, as one rounding routine would: at an
                # exact tie V = q whichever neighbour the first rounding took.
                z0 = self._nearest(A, Fraction(value))
                if type(z0) is int:
                    pairs.append([z0, value - z0])
            else:
                for z0 in (a, A.next_up(a), A.next_down(a)):
                    if type(z0) is int and A.member(value - z0) and A.add(z0, value - z0) == z0:
                        pairs.append([z0, value - z0])
            if not pairs and abs(value) > A.omega:
                # No normalized pair of this value: beyond the range.
                return " ".join([A.write(INF if value > 0 else -INF), A.write(0), "inf", "0"])
            if len(pairs) != 1:
                raise ValueError("%d normalized pairs of value %s in %s"
                                 % (len(pairs), value, fname))
            limbs = [a, b] if v == "rat-naive-pair" else pairs[0]
        d = abs(sum(limbs) - q)              # the naive pair has the same value
        error = A.round_up_fraction(d) if d else 0
        exact = d == 0
        if v == "rat-lead-ulp" and rare:
            limbs[0] = A.next_up(limbs[0])
        if v == "rat-tail-ulp" and rare and k == 2:
            limbs[1] = A.next_up(limbs[1])
        if v == "rat-error-small" and type(error) is int and error > 0:
            error = A.next_down(error)
        if v == "rat-error-large" and type(error) is int:
            error = A.next_up(error)
        if v == "rat-exact-flip" and rare:
            exact = not exact
        return " ".join([A.write(z) for z in limbs] + [A.write(error), "1" if exact else "0"])

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
    ap.add_argument("--bound-claims",
                    help="claims file whose bounds of add_1_1, add_2_2, mul_1_1 and mul_2_2 give "
                         "the constants of the bound kernels of the folds (default: the oracle's "
                         "fixture of the folds' stage, claims-wave5.json)")
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
        # Below a center kernel's precision its bound may not exist (3/(1 - 4u) at p = 2).
        for center in sorted(set(CENTER_KERNEL.values())):
            try:
                U, V = ball_constants(ar, center, a.center_claims or DEFAULT_CENTER_CLAIMS)
            except (ValueError, ZeroDivisionError) as ex:
                print("%s.%s: no constants (%s)" % (a.print_constants, center, ex))
                continue
            print("%s.%s.U=%s" % (a.print_constants, center, ar.write(U)))
            print("%s.%s.V=%s" % (a.print_constants, center, ar.write(V)))
        for kname in sorted(RADIUS2):
            try:
                consts = radius2_constants(ar, kname)
            except (ValueError, ZeroDivisionError) as ex:
                print("%s.%s: no constants (%s)" % (a.print_constants, kname, ex))
                continue
            for which, v in zip("EGH", consts):
                print("%s.%s.%s=%s" % (a.print_constants, kname, which, ar.write(v)))
        return 0
    Runner(a.variant, a.center_claims, a.radius, a.bound_claims).run(sys.stdin, sys.stdout)
    sys.stdout.flush()
    return 0
