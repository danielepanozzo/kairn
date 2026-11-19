"""Request lines.

Random mode is counter-based: case i of (kernel, format, seed, strata) depends only on
those and on i, through a keyed hash, so a run can be split across processes and a case
regenerated from its index (`--start i --count 1`).  The index is written into the tag
(`#stratum:i`), which the checker strips when it groups statistics.

Exhaustive mode enumerates the product of the operand domains in a fixed order; case i
is decoded from i directly.  Restrictions shrink the domains and are written into the
header comment, which the checker turns into the coverage statement of its report.
"""

import bisect
import hashlib
import sys

from . import fmt as F


class GenError(ValueError):
    pass


class CaseRandom:
    """Bits of a keyed hash of the case index, extended by counter when used up."""

    __slots__ = ("key", "index", "pool", "avail", "block")

    def __init__(self, key, index):
        self.key = key
        self.index = index
        self.block = 0
        self.pool = 0
        self.avail = 0

    def _refill(self):
        h = hashlib.blake2b(self.index.to_bytes(16, "little", signed=False)
                            + self.block.to_bytes(4, "little"), key=self.key, digest_size=64)
        self.block += 1
        self.pool |= int.from_bytes(h.digest(), "little") << self.avail
        self.avail += 512

    def bits(self, n):
        while self.avail < n:
            self._refill()
        r = self.pool & ((1 << n) - 1)
        self.pool >>= n
        self.avail -= n
        return r

    def below(self, n):
        if n <= 1:
            return 0
        k = (n - 1).bit_length()
        while True:
            r = self.bits(k)
            if r < n:
                return r

    def between(self, lo, hi):
        """Uniform integer in [lo, hi] (hi < lo gives lo)."""
        return lo + self.below(hi - lo + 1) if hi >= lo else lo

    def sign(self):
        return -1 if self.bits(1) else 1

    def chance(self, num, den):
        return self.below(den) < num


def seed_key(seed, kernel, fmtname, strata):
    return hashlib.blake2b(("kairn-oracle/1|%s|%s|%s|%s" % (seed, kernel, fmtname, ",".join(strata)))
                           .encode(), digest_size=32).digest()


# ---------------------------------------------------------------------------
# Numbers of the format, as fixed values

def in_binade(fmt, rng, e, style="uniform"):
    """A positive number whose leading bit has exponent e (qmin <= e <= emax)."""
    e = max(fmt.qmin, min(fmt.emax, e))
    nb = fmt.p if e >= fmt.emin_normal else e - fmt.qmin + 1   # bits available below e
    if style == "short" and nb > 1:
        # One to three set bits: powers of two, ties and exact products live here.
        m = 1 << (nb - 1)
        for _ in range(rng.below(3)):
            m |= 1 << rng.below(nb - 1)
    elif style == "high" and nb > 1:
        m = (1 << nb) - 1 - rng.below(min(4, 1 << (nb - 1)))
    else:
        m = (1 << (nb - 1)) | rng.bits(nb - 1)
    if e >= fmt.emin_normal:
        return m << (e - fmt.p + 1 - fmt.qmin)
    return m


def binade_of(fmt, n):
    return fmt.binade(n)


def tail_for(fmt, rng, x0, mode):
    """A second limb x1 with (x0, x1) normalized.  mode: 'near' (x1 within a few binades of
    half an ulp of x0), 'any' (anywhere below), or an extreme: 'half+', 'half-', 'quarter-',
    'max', 'eta', 'tiny', 'zero'."""
    if x0 == 0 or mode == "zero":
        return 0
    u0 = F.ulp(fmt, x0)
    if u0 == 1:
        return 0                     # |x1| <= eta/2 forces x1 = 0
    eu = binade_of(fmt, u0)
    s = 1 if x0 > 0 else -1
    if mode == "half+":
        cand = [s * (u0 >> 1)]
    elif mode == "half-":
        cand = [-s * (u0 >> 1), -s * (u0 >> 2)]
    elif mode == "quarter-":
        cand = [-s * (u0 >> 2)]
    elif mode == "max":
        h = u0 >> 1
        cand = [rng.sign() * F.pred(fmt, h), rng.sign() * F.pred(fmt, h >> 1)]
    elif mode == "eta":
        cand = [rng.sign()]
    elif mode == "tiny":
        e1 = rng.between(fmt.qmin, min(eu - 2, fmt.qmin + 2 * fmt.p))
        cand = [rng.sign() * in_binade(fmt, rng, e1)]
    else:
        if mode == "near":
            # Mostly within a few binades of half an ulp, where the tail carries a full
            # second word; sometimes anywhere in the next p binades.
            e1 = eu - 2 - (rng.below(4) if rng.bits(1) else rng.below(fmt.p + 2))
        else:
            e1 = rng.between(fmt.qmin, eu - 2)
        e1 = max(e1, fmt.qmin)
        style = "short" if rng.chance(1, 8) else "uniform"
        v = rng.sign() * in_binade(fmt, rng, e1, style)
        # Below a power of two the spacing halves: a negative tail must then stay under a
        # quarter ulp, so the fallback halves the candidate.
        cand = [v, v >> 1 if v > 0 else -((-v) >> 1)]
    for c in cand:
        if c != 0 and F.normalized_limbs(fmt, [x0, c]):
            return c
    return 0


def even_lead(fmt, x0):
    """x0 or a neighbor with an even significand, so that a tie toward it is allowed."""
    u0 = F.ulp(fmt, x0)
    if (abs(x0) // u0) % 2 == 0:
        return x0
    n = F.succ(fmt, x0)
    return n if type(n) is int else F.pred(fmt, x0)


EXTREME_LEADS = ("omega", "lambda", "pred_lambda", "succ_lambda", "eta", "top_binade", "one")


def extreme_lead(fmt, rng):
    k = EXTREME_LEADS[rng.below(len(EXTREME_LEADS))]
    if k == "omega":
        v = fmt.omega
    elif k == "lambda":
        v = fmt.lam
    elif k == "pred_lambda":
        v = fmt.lam - 1
    elif k == "succ_lambda":
        v = fmt.lam + 1
    elif k == "eta":
        v = 1
    elif k == "top_binade":
        v = in_binade(fmt, rng, fmt.emax)
    else:
        v = in_binade(fmt, rng, min(max(0, fmt.qmin), fmt.emax), "short")
    return rng.sign() * v


# ---------------------------------------------------------------------------
# Strata

STRATA = ("uniform", "close", "cancel", "overflow", "underflow", "pow2", "extreme", "zero")
# The order in which strata take turns; close and cancel stress the relative bound and
# underflow the absolute term, so they come round more often.
SCHEDULE = ("close", "uniform", "cancel", "underflow", "close", "pow2", "extreme", "cancel",
            "underflow", "close", "overflow", "zero")


class Shape:
    """What the generator needs to know about a kernel: its operands (two, in the order of
    the value expression, or one when the value is the input itself), their limb counts,
    the operation and the requirements."""

    def __init__(self, kernel):
        self.kernel = kernel
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        op, a, b = kernel.value
        if op == "=" and self.names == [a]:
            b = None
        elif len(self.names) != 2 or {a, b} != set(self.names):
            raise GenError("%s: the generator handles kernels of two operands that both appear "
                           "in the value, or of one operand that is the value" % kernel.name)
        self.op = op
        self.a, self.b = a, b
        for n, l in kernel.inputs:
            if l > 2:
                raise GenError("%s: inputs of more than two limbs are not generated yet" % kernel.name)
            if l == 2 and ("normalized", n) not in kernel.requires:
                raise GenError("%s: a 2-limb input without normalized() is not generated" % kernel.name)
        self.abs_ge = [(r[1], r[2]) for r in kernel.requires if r[0] == "abs_ge"]
        self.maxlimbs = max(self.limbs.values())


def _split_exponent(fmt, rng, et):
    """Binade exponents (ea, eb), both in range, with ea + eb = et when possible."""
    lo = max(fmt.qmin, et - fmt.emax)
    hi = min(fmt.emax, et - fmt.qmin)
    if lo > hi:
        ea = max(fmt.qmin, min(fmt.emax, et // 2))
        return ea, max(fmt.qmin, min(fmt.emax, et - ea))
    ea = rng.between(lo, hi)
    return ea, et - ea


def _mid(fmt, margin_lo, margin_hi):
    lo = fmt.emin_normal + margin_lo
    hi = fmt.emax - margin_hi
    if lo > hi:
        lo, hi = fmt.qmin, fmt.emax
    return lo, hi


def leads(fmt, sh, rng, stratum):
    """Leading limbs (a0, b0) and the tail mode for each operand."""
    p = fmt.p
    K = sh.maxlimbs
    mul = sh.op == "*"
    tails = ("near" if rng.chance(3, 4) else "any",) * 2
    if stratum == "uniform":
        if mul and rng.bits(1):
            ea, eb = _split_exponent(fmt, rng, rng.between(fmt.qmin - 1, fmt.emax))
        else:
            ea = rng.between(fmt.qmin, fmt.emax)
            eb = rng.between(fmt.qmin, fmt.emax)
        tails = ("near" if rng.bits(1) else "any", "near" if rng.bits(1) else "any")
        return rng.sign() * in_binade(fmt, rng, ea), rng.sign() * in_binade(fmt, rng, eb), tails
    if stratum == "close":
        if mul:
            lo, hi = _mid(fmt, (K + 1) * p, 2)
            ea, eb = _split_exponent(fmt, rng, rng.between(lo, hi))
        else:
            lo, hi = _mid(fmt, K * p + 2, 2)
            ea = rng.between(lo, hi)
            eb = ea - rng.between(-(K * p + 2), K * p + 2)
        return rng.sign() * in_binade(fmt, rng, ea), rng.sign() * in_binade(fmt, rng, eb), tails
    if stratum == "cancel" and not mul:
        lo, hi = _mid(fmt, K * p + 2, 2)
        a0 = rng.sign() * in_binade(fmt, rng, rng.between(lo, hi))
        j = rng.between(-3, 3)
        b0 = -a0
        for _ in range(abs(j)):
            nb = F.succ(fmt, b0) if j > 0 else F.pred(fmt, b0)
            if type(nb) is not int:
                break
            b0 = nb
        if sh.op == "-":
            b0 = -b0
        return a0, b0, ("near", "cancel")
    if stratum == "cancel":
        lo, hi = _mid(fmt, (K + 1) * p, 2)
        ea, eb = _split_exponent(fmt, rng, rng.between(lo, hi))
        return (rng.sign() * in_binade(fmt, rng, ea), rng.sign() * in_binade(fmt, rng, eb),
                ("near", "cross"))
    if stratum == "overflow":
        if mul:
            ea, eb = _split_exponent(fmt, rng, rng.between(fmt.emax - 3, fmt.emax + 1))
            a0 = in_binade(fmt, rng, ea, "high" if rng.bits(1) else "uniform")
            b0 = in_binade(fmt, rng, eb, "high" if rng.bits(1) else "uniform")
        else:
            a0 = fmt.omega if rng.chance(1, 4) else in_binade(
                fmt, rng, rng.between(fmt.emax - 1, fmt.emax), "high" if rng.bits(1) else "uniform")
            b0 = in_binade(fmt, rng, rng.between(fmt.emax - p - 2, fmt.emax),
                           "high" if rng.bits(1) else "uniform")
        return rng.sign() * a0, rng.sign() * b0, tails
    if stratum == "underflow":
        if mul:
            # Results from below eta through lambda up to the TwoProd exactness threshold
            # 2^(2p-1) eta and the double-word full-precision threshold 2^(2p-1+p) eta.
            et = rng.between(fmt.qmin - p - 1, fmt.emin_normal + 2 * p + 2)
            ea, eb = _split_exponent(fmt, rng, et)
        else:
            ea = rng.between(fmt.qmin, fmt.emin_normal + K * p + 1)
            eb = rng.between(fmt.qmin, fmt.emin_normal + K * p + 1)
        return rng.sign() * in_binade(fmt, rng, ea), rng.sign() * in_binade(fmt, rng, eb), tails
    if stratum == "pow2":
        lo, hi = _mid(fmt, K * p + 2, 2)
        if mul:
            lo, hi = _mid(fmt, (K + 1) * p, 2)
            ea, eb = _split_exponent(fmt, rng, rng.between(lo, hi))
            return (rng.sign() * in_binade(fmt, rng, ea, "short"),
                    rng.sign() * in_binade(fmt, rng, eb, "short"), ("pow2", "pow2"))
        a0 = rng.sign() * in_binade(fmt, rng, rng.between(lo, hi), "short")
        if rng.bits(1):
            # An odd multiple of half an ulp of a0: the sum a0 + b0 is a tie.
            u0 = F.ulp(fmt, a0)
            b0 = rng.sign() * (2 * rng.below(4) + 1) * u0
            b0 = b0 // 2 if u0 > 1 else b0
            if not F.is_member(fmt, b0):
                b0 = rng.sign() * u0
        else:
            b0 = rng.sign() * in_binade(fmt, rng, binade_of(fmt, a0) - rng.between(-2, p + 2),
                                        "short")
        return a0, b0, ("pow2", "pow2")
    if stratum == "extreme":
        lo, hi = _mid(fmt, K * p + 2, 2)
        modes = ("half+", "half-", "quarter-", "max", "eta", "tiny", "zero")
        if K == 1 or rng.chance(1, 4):
            a0 = extreme_lead(fmt, rng)
        else:
            a0 = rng.sign() * in_binade(fmt, rng, rng.between(lo, hi),
                                        "short" if rng.bits(1) else "uniform")
        if mul:
            et = rng.between(*_mid(fmt, (K + 1) * p, 2))
            eb = max(fmt.qmin, min(fmt.emax, et - binade_of(fmt, a0) if a0 else et))
        else:
            eb = binade_of(fmt, a0) - rng.between(-(K * p + 2), K * p + 2) if a0 else lo
        b0 = extreme_lead(fmt, rng) if rng.chance(1, 4) else rng.sign() * in_binade(fmt, rng, eb)
        return a0, b0, (modes[rng.below(len(modes))], modes[rng.below(len(modes))])
    if stratum == "zero":
        lo, hi = _mid(fmt, K * p + 2, 2)
        a0 = rng.sign() * in_binade(fmt, rng, rng.between(lo, hi))
        b0 = rng.sign() * in_binade(fmt, rng, rng.between(lo, hi))
        k = rng.below(4)
        if k == 0:
            a0 = 0
        elif k == 1:
            b0 = 0
        elif k == 2:
            a0 = b0 = 0
        return a0, b0, ("zero" if rng.bits(1) else "near", "zero" if rng.bits(1) else "near")
    raise GenError("unknown stratum %r" % stratum)


def make_case(fmt, sh, rng, stratum):
    """Operand limbs {name: [fixed, ...]} and the set of (name, limb) that are -0."""
    a0, b0, (ta, tb) = leads(fmt, sh, rng, stratum)
    vals = {sh.a: [a0]}
    if sh.b is not None:
        vals[sh.b] = [b0]
    if sh.limbs[sh.a] == 2:
        vals[sh.a].append(tail_for(fmt, rng, a0, ta if ta in _TAIL_MODES else "near"))
    if sh.b is not None and sh.limbs[sh.b] == 2:
        if tb == "cancel" and sh.limbs[sh.a] == 2 and vals[sh.a][1] != 0:
            # The second limbs nearly cancel as well.
            t = -vals[sh.a][1] if sh.op == "+" else vals[sh.a][1]
            for _ in range(rng.below(3)):
                nt = F.succ(fmt, t) if rng.bits(1) else F.pred(fmt, t)
                t = nt if type(nt) is int else t
            vals[sh.b].append(t if type(t) is int and F.normalized_limbs(fmt, [b0, t])
                              else tail_for(fmt, rng, b0, "near"))
        elif tb == "cross" and sh.limbs[sh.a] == 2 and a0 != 0 and b0 != 0:
            # b1 chosen so that a0*b1 nearly cancels a1*b0.
            t = F.rn_fixed(fmt, -(vals[sh.a][1] * b0) // a0)
            vals[sh.b].append(t if type(t) is int and t != 0 and F.normalized_limbs(fmt, [b0, t])
                              else tail_for(fmt, rng, b0, "near"))
        else:
            vals[sh.b].append(tail_for(fmt, rng, b0, tb if tb in _TAIL_MODES else "near"))
    if stratum == "extreme":
        # A tie toward x0 in the tail is allowed only when x0's significand is even.
        for n, mode in ((sh.a, ta), (sh.b, tb)):
            if n is not None and len(vals[n]) == 2 and vals[n][1] == 0 and vals[n][0] != 0 and mode == "half+":
                x0 = even_lead(fmt, vals[n][0])
                if type(x0) is int:
                    vals[n] = [x0, tail_for(fmt, rng, x0, "half+")]
    negz = set()
    if stratum == "zero":
        for n in vals:
            for i, v in enumerate(vals[n]):
                if v == 0 and rng.bits(1):
                    negz.add((n, i))
    for big, small in sh.abs_ge:
        if abs(sum(vals[big])) < abs(sum(vals[small])) and sh.limbs[big] == sh.limbs[small]:
            vals[big], vals[small] = vals[small], vals[big]
            negz = {(big if n == small else small if n == big else n, i) for n, i in negz}
    return vals, negz


_TAIL_MODES = ("near", "any", "half+", "half-", "quarter-", "max", "eta", "tiny", "zero")


def valid(fmt, kernel, vals):
    for name, limbs in vals.items():
        if name in kernel.masks:
            if limbs not in ([0], [1]):
                return False
            continue
        for v in limbs:
            if type(v) is not int or not F.is_member(fmt, v):
                return False
    for r in kernel.requires:
        if r[0] == "normalized":
            if not F.normalized_limbs(fmt, vals[r[1]]):
                return False
        elif r[0] == "nonneg":
            if sum(vals[r[1]]) < 0:
                return False
        elif r[0] == "power_of_two":
            v = sum(vals[r[1]])
            if v <= 0 or v & (v - 1):
                return False
        elif abs(sum(vals[r[1]])) < abs(sum(vals[r[2]])):
            return False
    return True


def limb_text(fmt, v, neg):
    if type(v) is not int:
        return v                     # inf, -inf, nan (the extended domain)
    if v == 0:
        return "-0x0p+0" if neg else "0x0p+0"
    return F.to_hex(v, fmt.qmin)


def first_wave_shape(kernel):
    """True when the first-wave generator handles the kernel: two operands that appear in a
    value of the form NAME op NAME (or one that is the value), limbs and no masks, the first
    requirements and kinds only."""
    return (kernel.value is not None and not kernel.masks
            and all(r[0] in ("normalized", "abs_ge") for r in kernel.requires)
            and all(e.kind in ("normalized", "error", "leading_rounded") for e in kernel.ensures))


class RandomGen:
    def __init__(self, kernel, fmt, seed, strata=None, index_tags=True):
        self.kernel = kernel
        self.fmt = fmt
        self.valid = valid
        if getattr(kernel, "extended", False):
            # The non-finite layer (gen3.py): the family's strata and strata of its own.
            from . import gen3
            self.shape = gen3.ExtShape(kernel)
            known, schedule = self.shape.strata, self.shape.schedule
            self.make = gen3.make_case
            self.valid = gen3.valid_ext
        elif first_wave_shape(kernel):
            self.shape = Shape(kernel)
            known, schedule, self.make = STRATA, SCHEDULE, make_case
        else:
            # The kernels of the second wave have generators of their own (gen2.py).
            from . import gen2
            self.shape = gen2.Shape2(kernel)
            known, schedule = self.shape.strata, self.shape.schedule
            self.make = gen2.make_case
        self.seed = seed
        if strata:
            for s in strata:
                if s not in known:
                    raise GenError("unknown stratum %r for %s (known: %s)"
                                   % (s, kernel.name, ", ".join(known)))
            self.schedule = tuple(s for s in schedule if s in strata) or tuple(strata)
            self.strata = list(strata)
        else:
            self.schedule = schedule
            self.strata = list(known)
        self.key = seed_key(seed, kernel.name, fmt.name, self.strata)
        self.index_tags = index_tags

    def case(self, i):
        stratum = self.schedule[i % len(self.schedule)]
        rng = CaseRandom(self.key, i)
        for _attempt in range(16):
            vals, negz = self.make(self.fmt, self.shape, rng, stratum)
            if self.valid(self.fmt, self.kernel, vals):
                break
        else:
            raise GenError("could not generate a valid case %d (%s)" % (i, stratum))
        toks = [self.kernel.name, self.fmt.name]
        for n, _ in self.kernel.inputs:
            if n in self.kernel.masks:
                toks.append(str(vals[n][0]))
                continue
            for j, v in enumerate(vals[n]):
                toks.append(limb_text(self.fmt, v, (n, j) in negz))
        toks.append("#%s:%d" % (stratum, i) if self.index_tags else "#" + stratum)
        return " ".join(toks)

    def header(self, start, count):
        return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=random seed=%s strata=%s "
                "start=%d count=%d" % (self.kernel.name, self.fmt.name, self.seed,
                                       ",".join(self.strata), start, count))

    def lines(self, start, count):
        yield self.header(start, count)
        for i in range(start, start + count):
            yield self.case(i)
        yield "# kairn-oracle gen event=end lines=%d" % count


# ---------------------------------------------------------------------------
# Exhaustive enumeration

class Restriction:
    """NAME.lead=LO:HI keeps operands whose leading limb lies in binades LO..HI (2^LO <= |x0|
    < 2^(HI+1); this excludes zero); NAME.sign=+ or - keeps x0 >= 0 or x0 <= 0;
    NAME.in=V1/V2/... keeps operands whose leading limb is one of the listed literals."""

    def __init__(self, spec):
        self.spec = spec
        try:
            lhs, val = spec.split("=", 1)
            name, what = lhs.split(".", 1)
        except ValueError:
            raise GenError("bad restriction %r (NAME.lead=LO:HI, NAME.sign=+|- or "
                           "NAME.in=V1/V2/...)" % spec)
        self.name = name
        self.what = what
        if what == "lead":
            try:
                lo, hi = val.split(":")
                self.lo, self.hi = int(lo), int(hi)
            except ValueError:
                raise GenError("bad lead range in %r" % spec)
        elif what == "sign":
            if val not in ("+", "-"):
                raise GenError("bad sign in %r" % spec)
            self.sign = val
        elif what == "in":
            self.literals = val.split("/")
            if not val or "" in self.literals:
                raise GenError("bad value list in %r" % spec)
        else:
            raise GenError("unknown restriction %r" % spec)
        self._values = {}

    def keep(self, fmt, x0):
        if self.what == "lead":
            return x0 != 0 and self.lo <= fmt.binade(x0) <= self.hi
        if self.what == "in":
            vs = self._values.get(fmt.triple)
            if vs is None:
                try:
                    vs = {F.parse_limb(fmt, t) for t in self.literals}
                except F.LimbError as ex:
                    raise GenError("%s: %s" % (self.spec, ex))
                if any(type(v) is not int for v in vs):
                    raise GenError("%s: a listed value is not a number of %s" % (self.spec, fmt.name))
                self._values[fmt.triple] = vs
            return x0 in vs
        return x0 >= 0 if self.sign == "+" else x0 <= 0


_DOMAIN_CACHE = {}


def normalized_pairs(fmt):
    key = (fmt.triple, "pairs")
    d = _DOMAIN_CACHE.get(key)
    if d is not None:
        return d
    vals = F.all_values(fmt)
    out = []
    for x0 in vals:
        if x0 == 0:
            out.append((0, 0))
            continue
        h = F.ulp(fmt, x0) >> 1
        lo = bisect.bisect_left(vals, -h)
        hi = bisect.bisect_right(vals, h)
        for x1 in vals[lo:hi]:
            if F.normalized_limbs(fmt, [x0, x1]):
                out.append((x0, x1))
    _DOMAIN_CACHE[key] = out
    return out


def domain(fmt, limbs, restrictions, requires=(), mask=False):
    """Every operand of one input: all numbers of the format for one limb, every normalized
    pair for two, (0,) and (1,) for a mask; requirements on that input alone (nonneg,
    power_of_two) and restrictions remove operands."""
    if mask:
        return [(0,), (1,)]
    if limbs == 1:
        base = [(v,) for v in F.all_values(fmt)]
    elif limbs == 2:
        base = normalized_pairs(fmt)
    else:
        raise GenError("exhaustive enumeration of %d-limb operands is not supported" % limbs)
    if "nonneg" in requires:
        base = [t for t in base if sum(t) >= 0]
    if "power_of_two" in requires:
        base = [t for t in base if sum(t) > 0 and sum(t) & (sum(t) - 1) == 0]
    return [t for t in base if all(r.keep(fmt, t[0]) for r in restrictions)]


class ExhaustiveGen:
    def __new__(cls, kernel, *args, **kw):
        # A kernel of the extended domain has domains with non-finite values and balls as one
        # operand: its enumeration is gen3.ExtExhaustiveGen, a subclass, whose __init__ runs.
        if cls is ExhaustiveGen and getattr(kernel, "extended", False):
            from . import gen3
            cls = gen3.ExtExhaustiveGen
        return super().__new__(cls)

    def __init__(self, kernel, fmt, restrictions=(), index_tags=True):
        self.kernel = kernel
        self.fmt = fmt
        self.restrictions = [Restriction(r) if isinstance(r, str) else r for r in restrictions]
        names = [n for n, _ in kernel.inputs]
        for r in self.restrictions:
            if r.name not in names:
                raise GenError("restriction on %r, which is not an input of %s" % (r.name, kernel.name))
        self.doms = []
        self.texts = []
        for n, l in kernel.inputs:
            if l == 2 and ("normalized", n) not in kernel.requires:
                raise GenError("%s: exhaustive mode needs normalized() on 2-limb inputs" % kernel.name)
            mask = n in kernel.masks
            d = domain(fmt, l, [r for r in self.restrictions if r.name == n],
                       [r[0] for r in kernel.requires if len(r) == 2 and r[1] == n], mask)
            self.doms.append(d)
            self.texts.append([str(t[0]) if mask else " ".join(F.to_hex(v, fmt.qmin) for v in t)
                               for t in d])
        self.total = 1
        for d in self.doms:
            self.total *= len(d)
        self.index = {n: i for i, (n, _) in enumerate(kernel.inputs)}
        self.coupled = [(self.index[r[1]], self.index[r[2]]) for r in kernel.requires
                        if r[0] == "abs_ge"]
        self.index_tags = index_tags
        self.restrict_text = ",".join(r.spec for r in self.restrictions) or "none"

    def decode(self, i):
        idx = []
        for d in reversed(self.doms):
            i, r = divmod(i, len(d))
            idx.append(r)
        return idx[::-1]

    def case(self, i):
        """The line of enumeration index i, or None when a coupled requirement (abs_ge)
        excludes it."""
        idx = self.decode(i)
        for a, b in self.coupled:
            if abs(sum(self.doms[a][idx[a]])) < abs(sum(self.doms[b][idx[b]])):
                return None
        parts = [self.kernel.name, self.fmt.name]
        parts.extend(self.texts[j][k] for j, k in enumerate(idx))
        parts.append("#exhaustive:%d" % i if self.index_tags else "#exhaustive")
        return " ".join(parts)

    def header(self, start, count):
        return ("# kairn-oracle gen event=begin kernel=%s format=%s mode=exhaustive total=%d "
                "restrict=%s skip=%s start=%d count=%d" % (
                    self.kernel.name, self.fmt.name, self.total, self.restrict_text,
                    "abs_ge" if self.coupled else "none", start, count))

    def lines(self, start, count):
        count = max(0, min(count, self.total - start))
        yield self.header(start, count)
        n = 0
        for i in range(start, start + count):
            ln = self.case(i)
            if ln is not None:
                n += 1
                yield ln
        yield "# kairn-oracle gen event=end lines=%d" % n


def write_lines(lines, out=None):
    out = out or sys.stdout
    w = out.write
    for ln in lines:
        w(ln)
        w("\n")
