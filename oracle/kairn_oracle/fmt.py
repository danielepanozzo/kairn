"""Binary formats and exact arithmetic on their numbers.

A format (p, qmin, qmax) holds the numbers m * 2^q with integers |m| < 2^p and
qmin <= q <= qmax.  Every number of a format is an integer multiple of
eta = 2^qmin, so the oracle stores a finite limb as that integer (a *fixed* value:
N stands for N * eta).  Sums of limbs stay integers at the same scale and products
are integers at scale 2*qmin, which is why no verdict ever needs Fraction or a float.

Non-finite limbs are the three string constants POS_INF, NEG_INF and NAN; callers
test `type(v) is int` to separate them from finite values.
"""

import re

POS_INF = "inf"
NEG_INF = "-inf"
NAN = "nan"

NAMED_FORMATS = {
    "binary64": (53, -1074, 971),
    "binary32": (24, -149, 104),
}


class FormatError(ValueError):
    pass


class LimbError(ValueError):
    pass


class Format:
    """One binary format.  All magnitudes below are fixed values (multiples of eta)."""

    __slots__ = ("p", "qmin", "qmax", "name", "omega", "lam", "emin_normal", "emax")

    def __init__(self, p, qmin, qmax):
        # Precision 1 is a format too: its numbers are zero and the powers of two (eighteen
        # kernels are proved from it).
        if p < 1:
            raise FormatError("precision must be at least 1, got %d" % p)
        if qmin > qmax:
            raise FormatError("qmin %d is above qmax %d" % (qmin, qmax))
        self.p = p
        self.qmin = qmin
        self.qmax = qmax
        self.name = canonical_name(p, qmin, qmax)
        self.omega = ((1 << p) - 1) << (qmax - qmin)
        self.lam = 1 << (p - 1)
        # Exponents of the leading bit: smallest normal binade and top binade.
        self.emin_normal = qmin + p - 1
        self.emax = qmax + p - 1

    def __repr__(self):
        return "Format(%s)" % self.name

    def __eq__(self, other):
        return isinstance(other, Format) and (self.p, self.qmin, self.qmax) == (
            other.p, other.qmin, other.qmax)

    def __hash__(self):
        return hash((self.p, self.qmin, self.qmax))

    @property
    def triple(self):
        return (self.p, self.qmin, self.qmax)

    def fits_binary64(self):
        """True when every number of this format is a double."""
        return self.p <= 53 and self.qmin >= -1074 and self.qmax + self.p <= 1024

    def binade(self, n):
        """Exponent e of the leading bit of a nonzero fixed value: 2^e <= |n| * eta < 2^(e+1)."""
        return self.qmin + abs(n).bit_length() - 1


def canonical_name(p, qmin, qmax):
    for name, t in NAMED_FORMATS.items():
        if t == (p, qmin, qmax):
            return name
    return "fp:%d:%d:%d" % (p, qmin, qmax)


_FORMAT_CACHE = {}


def parse_format(name):
    f = _FORMAT_CACHE.get(name)
    if f is not None:
        return f
    if name in NAMED_FORMATS:
        f = Format(*NAMED_FORMATS[name])
    else:
        m = re.fullmatch(r"fp:(\d+):(-?\d+):(-?\d+)", name)
        if m is None:
            raise FormatError("unknown format %r (expected binary64, binary32 or fp:P:QMIN:QMAX)"
                              % name)
        f = Format(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    _FORMAT_CACHE[name] = f
    return f


# ---------------------------------------------------------------------------
# Literals

_HEX_RE = re.compile(r"([+-]?)0[xX]([0-9a-fA-F]*)(?:\.([0-9a-fA-F]*))?[pP]([+-]?[0-9]+)\Z")
_NONFINITE = {
    "inf": POS_INF, "+inf": POS_INF, "infinity": POS_INF, "+infinity": POS_INF,
    "-inf": NEG_INF, "-infinity": NEG_INF,
    "nan": NAN, "+nan": NAN, "-nan": NAN,
}


def parse_dyadic(tok):
    """Exact value of a C99 hexadecimal literal: (M, E) meaning M * 2^E, or a non-finite
    constant.  Raises LimbError on anything else.  The sign of a zero is dropped, because
    the sign of a zero limb carries no meaning in Kairn."""
    m = _HEX_RE.match(tok)
    if m is None:
        v = _NONFINITE.get(tok.lower())
        if v is None:
            raise LimbError("not a hexadecimal floating-point literal: %r" % tok)
        return v
    sign, ip, frac, ex = m.groups()
    frac = frac or ""
    digits = ip + frac
    if not digits:
        raise LimbError("no digits in %r" % tok)
    M = int(digits, 16)
    if sign == "-":
        M = -M
    return (M, int(ex) - 4 * len(frac))


# Returned by to_fixed for a finite literal that is not a multiple of eta or is far
# outside the format's range: such a literal is certainly not a number of the format.
OUTSIDE = "outside"


def to_fixed(fmt, d):
    """Fixed value of an exact dyadic (M, E), or OUTSIDE when it is not a multiple of eta
    or is too large to be in range (the guard keeps a hostile exponent from allocating
    a huge integer)."""
    M, E = d
    if M == 0:
        return 0
    if E + abs(M).bit_length() - 1 > fmt.emax + 1:
        return OUTSIDE
    if E >= fmt.qmin:
        return M << (E - fmt.qmin)
    sh = fmt.qmin - E
    if sh > abs(M).bit_length():
        return OUTSIDE
    if M % (1 << sh):
        return OUTSIDE
    return M >> sh


def parse_limb(fmt, tok):
    """Fixed value, a non-finite constant, or OUTSIDE.  Raises LimbError when malformed."""
    d = parse_dyadic(tok)
    if type(d) is str:
        return d
    return to_fixed(fmt, d)


def is_member(fmt, n):
    """True when the fixed value n is a finite number of the format."""
    a = -n if n < 0 else n
    if a == 0:
        return True
    if a > fmt.omega:
        return False
    return (a >> ((a & -a).bit_length() - 1)).bit_length() <= fmt.p


def to_hex(n, scale):
    """C99 hexadecimal literal of n * 2^scale (exact; normalized as by printf("%a"))."""
    if n == 0:
        return "0x0p+0"
    sign = "-" if n < 0 else ""
    a = -n if n < 0 else n
    tz = (a & -a).bit_length() - 1
    a >>= tz
    e = scale + tz
    b = a.bit_length()
    top = e + b - 1
    if b == 1:
        return "%s0x1p%+d" % (sign, top)
    nd = (b + 2) // 4
    frac = (a - (1 << (b - 1))) << (4 * nd - (b - 1))
    return "%s0x1.%0*xp%+d" % (sign, nd, frac, top)


def fixed_hex(fmt, v):
    """Literal of a fixed value or a non-finite constant."""
    if type(v) is int:
        return to_hex(v, fmt.qmin)
    return v


# ---------------------------------------------------------------------------
# Rounding (the checker's implementation; the reference runner has its own)

def rn(fmt, n, s):
    """Round n * 2^s to nearest, ties to even, with gradual underflow.  Returns a fixed
    value, or POS_INF / NEG_INF when the rounding in unbounded range exceeds Omega."""
    if n == 0:
        return 0
    a = -n if n < 0 else n
    q = s + a.bit_length() - fmt.p
    if q < fmt.qmin:
        q = fmt.qmin
    if q <= s:
        r = a << (s - fmt.qmin)
    else:
        sh = q - s
        m = a >> sh
        rem = a - (m << sh)
        half = 1 << (sh - 1)
        if rem > half or (rem == half and m & 1):
            m += 1
        r = m << (q - fmt.qmin)
    if r > fmt.omega:
        return NEG_INF if n < 0 else POS_INF
    return -r if n < 0 else r


def rn_fixed(fmt, n):
    """RN of a fixed value (a sum of limbs)."""
    return rn(fmt, n, fmt.qmin)


def rdir(fmt, n, s, up):
    """n * 2^s rounded toward +infinity (up) or -infinity, with gradual underflow and the
    exponent range unbounded above: the fixed value returned may exceed Omega, and the
    caller decides what that means."""
    if n == 0:
        return 0
    a = -n if n < 0 else n
    # The exponent of the last place kept: p bits, or the subnormal grid.
    q = max(s + a.bit_length() - fmt.p, fmt.qmin)
    if q <= s:
        return n << (s - fmt.qmin)
    sh = q - s
    m = a >> sh
    # Inexact: the magnitude grows when rounding toward the infinity of the value's sign.
    if (m << sh) != a and (n > 0) == up:
        m += 1
    r = m << (q - fmt.qmin)
    return -r if n < 0 else r


def gap_below(fmt, n):
    """n - pred(n) for a fixed value n, with the exponent range unbounded above (so that
    pred(-Omega) is the next number of the unbounded format, not -infinity)."""
    if n > 0:
        # Below a power of two the spacing is that of the binade underneath.
        return 1 << max((n - 1).bit_length() - fmt.p, 0)
    return ulp(fmt, n)


def ulp(fmt, n):
    """ulp of a fixed value as a fixed value; ulp(0) = eta."""
    b = abs(n).bit_length()
    return 1 << (b - fmt.p) if b > fmt.p else 1


def succ(fmt, n):
    """Next number of the format above the fixed value n (POS_INF above Omega)."""
    if n >= 0:
        r = n + ulp(fmt, n)
        return POS_INF if r > fmt.omega else r
    # Below a positive a the spacing is ulp(a - 1): half of ulp(a) when a is a power of two
    # in the normal range.
    a = -n
    b = (a - 1).bit_length()
    return -(a - (1 << max(b - fmt.p, 0)))


def pred(fmt, n):
    s = succ(fmt, -n)
    if s == POS_INF:
        return NEG_INF
    return -s


def normalized_limbs(fmt, limbs):
    """The invariant x_i = RN(x_i + x_{i+1}) on fixed limbs (all assumed finite)."""
    for i in range(len(limbs) - 1):
        if rn(fmt, limbs[i] + limbs[i + 1], fmt.qmin) != limbs[i]:
            return False
    return True


def all_values(fmt, positive_only=False):
    """Every finite number of the format as a fixed value, in increasing order (one zero)."""
    pos = list(range(1, 1 << (fmt.p - 1)))
    for q in range(fmt.qmin, fmt.qmax + 1):
        sh = q - fmt.qmin
        pos.extend(m << sh for m in range(1 << (fmt.p - 1), 1 << fmt.p))
    if positive_only:
        return pos
    return [-v for v in reversed(pos)] + [0] + pos
