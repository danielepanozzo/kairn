"""A reference runner in pure Python for any binary format, toy formats included.

It evaluates the first-wave kernels as written in docs/developer/architecture.md, one
rounding per line.  It is part of the oracle only to test the oracle, so it avoids the
checker's code on purpose: rounding is computed from the two neighbors of the exact value
(the checker shifts and inspects the dropped bits), literals are read with float.fromhex
and printed with float.hex whenever the format fits in binary64 (the checker has its own
exact parser and printer).  A shared bug would let a wrong result pass; two different
implementations that agree, and that agree with hardware on binary64, make that unlikely.

Named variants inject errors that the checker must catch (see VARIANTS).
"""

import math
import re
import sys
import zlib

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
}

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
    def __init__(self, ar):
        self.A = ar
        self.v = ar.variant
        self.trace = [] if ar.variant == "trace-fast-two-sum" else None

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
        if self.trace is not None and type(a) is int and type(b) is int and abs(a) < abs(b):
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
        sh, sl = self.two_sum(x0, a)
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


ARITY = {"two_sum": 2, "fast_two_sum": 2, "two_prod": 2, "two_prod_dekker": 2, "split": 1,
         "add_2_2": 4, "add_2_1": 3, "mul_2_2": 4, "mul_2_1": 3, "add_fast_2_2": 4}
# Which input limb pairs form a normalized 2-limb operand (for corrupt-input).
PAIRS = {"add_2_2": (0, 2), "add_2_1": (0,), "mul_2_2": (0, 2), "mul_2_1": (0,),
         "add_fast_2_2": (0, 2)}


class Runner:
    def __init__(self, variant="correct"):
        if variant not in VARIANTS:
            raise ValueError("unknown variant %r (known: %s)" % (variant, ", ".join(VARIANTS)))
        self.variant = variant
        self.cache = {}

    def kernels(self, fmtname):
        k = self.cache.get(fmtname)
        if k is None:
            k = self.cache[fmtname] = Kernels(Arith(parse_format_triple(fmtname), self.variant))
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
            pre += ["# refrun trace: fast_two_sum %s with |a| < |b|: a = 0 %s, exponent(a) >= "
                    "exponent(b) %s, error-free %s" % (site, "yes" if z else "no",
                                                       "yes" if eok else "no", "yes" if ex else "no")
                    for site, z, eok, ex in K.trace]
        if self.variant == "ulp-rare" and zlib.crc32(line.encode()) % 256 == 0 and len(out) > 1:
            out[1] = A.succ(out[1])
        if self.variant == "not-normalized" and len(out) == 2:
            z0, z1 = out
            if type(z0) is int and type(z1) is int and z0 != 0:
                n = A.succ(z0)
                if type(n) is int and A.member(z1 - (n - z0)):
                    out = [n, z1 - (n - z0)]
        return pre + [line + " -> " + " ".join(A.write(v) for v in out)]

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
    a = ap.parse_args(argv)
    if a.list_variants:
        for k, v in VARIANTS.items():
            print("%-18s %s" % (k, v))
        return 0
    Runner(a.variant).run(sys.stdin, sys.stdout)
    sys.stdout.flush()
    return 0
