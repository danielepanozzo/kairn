"""What the generator's tests share: paths, sizes, operands, and the interpreter in parallel."""
import atexit
import itertools
import math
import os
import random
import shutil
import struct
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

TESTS = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(TESTS)
ROOT = os.path.dirname(GEN)
sys.path.insert(0, GEN)

from kairn_gen import build, interp, ir  # noqa: E402

FULL = os.environ.get('KAIRN_GEN_TEST_FULL', '0') == '1'
# Processes and compilers run at once: all cores, unless $KAIRN_GEN_JOBS says otherwise.
JOBS = int(os.environ.get('KAIRN_GEN_JOBS') or os.cpu_count() or 4)
TEST_KERNELS = os.path.join(TESTS, 'kernels')


def size(quick, full):
    return full if FULL else quick


_scratch = []


def scratch(name):
    """A fresh directory for build products, under the system's temporary directory. They are
    removed when the tests end, unless $KAIRN_GEN_KEEP is set."""
    d = tempfile.mkdtemp(prefix=f'kairn-gen-{name}-')
    _scratch.append(d)
    return d


@atexit.register
def _remove_scratch():
    if not os.environ.get('KAIRN_GEN_KEEP'):
        for d in _scratch:
            shutil.rmtree(d, ignore_errors=True)


_cache = {}


def kernels(directory=None):
    """The kernels of gen/kernels (or of another directory); the rules must accept them."""
    directory = directory or os.path.join(GEN, 'kernels')
    if directory not in _cache:
        ks, errors = build.load(ROOT, directory)
        if errors:
            raise AssertionError('\n'.join(map(str, errors)))
        _cache[directory] = ks
    return _cache[directory]


# ---------------------------------------------------------------------------------------------
# Operands. Limbs are Python floats; binary32 limbs are floats that are binary32 numbers.

FORMATS = {'binary64': (53, -1074, 971), 'binary32': (24, -149, 104)}


def number(p, q, m, neg=False):
    v = math.ldexp(m, q)
    return -v if neg else v


def edges(fmt):
    p, qmin, qmax = FORMATS[fmt]
    top = number(p, qmax, 2 ** p - 1)                      # the largest finite number
    vals = [0.0, number(p, qmin, 1), number(p, qmin, 2 ** (p - 1) - 1),   # smallest, largest subnormal
            number(p, qmin, 2 ** (p - 1)), number(p, qmin, 2 ** (p - 1) + 1),  # smallest normals
            1.0, number(p, -p + 1, 2 ** p - 1), number(p, -p + 1, 2 ** (p - 1) + 1),  # 1 - u, 1 + 2u
            2.0, 3.0, 0.5, top, number(p, qmax, 2 ** p - 2), number(p, qmax, 2 ** (p - 1)),
            number(p, (qmin + qmax) // 2, 2 ** p - 1), number(p, qmax - p, 1),
            math.inf, math.nan]
    return [s * v for v in vals for s in (1.0, -1.0)]


def wide(rng, fmt):
    """Any finite number: every exponent equally likely, subnormals included."""
    p, qmin, qmax = FORMATS[fmt]
    q = rng.randint(qmin, qmax)
    m = rng.getrandbits(p - 1) | (1 << (p - 1)) if q > qmin else rng.getrandbits(p - 1)
    return number(p, q, m, rng.random() < 0.5)


def near(rng, fmt, center_q, spread):
    p, qmin, qmax = FORMATS[fmt]
    q = max(qmin, min(qmax, center_q + rng.randint(-spread, spread)))
    m = rng.getrandbits(p - 1) | (1 << (p - 1))
    return number(p, q, m, rng.random() < 0.5)


def rn(fmt, x):
    """x (a double) rounded to the format: the identity for binary64."""
    if fmt == 'binary64' or x != x:
        return x
    try:
        return struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def tail(rng, fmt, x0):
    """A second limb for x0 such that (x0, x1) is normalized, often near the extremes."""
    p = FORMATS[fmt][0]
    if x0 == 0 or not math.isfinite(x0):
        return 0.0
    e = math.frexp(x0)[1] - 1                      # x0 in [2^e, 2^(e+1))
    choice = rng.random()
    if choice < 0.15:
        x1 = math.ldexp(1, e - p) * rng.choice((1, -1))   # half an ulp: a tie, broken to even
    elif choice < 0.25:
        x1 = math.ldexp(1, e - p - 1) * rng.choice((1, -1))
    else:
        x1 = rn(fmt, math.ldexp(rng.uniform(-1, 1), e - p - rng.randint(0, 2 * p)))
    x1 = rn(fmt, x1)
    return x1 if rn(fmt, x0 + x1) == x0 else 0.0


def operands(rng, fmt, kernel):
    """Inputs for a kernel, from one of several strata (any inputs are fine for bit identity).
    A mask operand is a Python bool."""
    p, qmin, qmax = FORMATS[fmt]
    stratum = rng.randrange(10)
    groups = []
    lead = None
    for g in kernel.inputs:
        # near() takes the exponent q of m 2^q, |m| in [2^(p-1), 2^p): a value near 2^(q+p-1).
        if g.kind == ir.MASK:
            groups.append(rng.random() < 0.5)
            continue
        if stratum == 0:
            limbs = [rng.choice(edges(fmt)) for _ in g.limbs]
        elif stratum == 1:
            limbs = [wide(rng, fmt) for _ in g.limbs]
        elif stratum == 2:                       # products near the smallest normal
            limbs = [near(rng, fmt, (qmin - p) // 2 + 1, p) for _ in g.limbs]
        elif stratum == 3:                       # products near overflow
            limbs = [near(rng, fmt, (qmax - p) // 2 + 1, 3) for _ in g.limbs]
        elif stratum == 4:                       # sums near overflow
            limbs = [near(rng, fmt, qmax - rng.randint(0, 2), 2) for _ in g.limbs]
        elif stratum == 5:                       # sums in and near the subnormals
            limbs = [wide(rng, fmt) if rng.random() < 0.2 else
                     number(p, qmin + rng.randint(0, 3), rng.getrandbits(p), rng.random() < 0.5)
                     for _ in g.limbs]
        else:                                    # moderate exponents, normalized multi-limb groups
            x0 = near(rng, fmt, 0, 3 * p)
            if stratum >= 8 and lead is not None:    # cancellation against the previous group
                x0 = rn(fmt, -lead * (1 + rng.choice((0, 0, 1, -1)) * math.ldexp(rng.random(), -rng.randint(1, p))))
            limbs = [x0]
            for _ in g.limbs[1:]:
                limbs.append(tail(rng, fmt, limbs[-1]))
        if lead is None:
            lead = limbs[0] if math.isfinite(limbs[0]) and limbs[0] != 0 else 1.0
        groups += limbs
    return groups


def requests(fmt, kernel, n, seed):
    rng = random.Random(f'{seed}:{fmt}:{kernel.name}')
    return [operands(rng, fmt, kernel) for _ in range(n)]


def edge_cases(fmt, kernel, limit):
    """Edge values in every limb position (both values of a mask): all combinations when few, a
    sample otherwise."""
    choices = [(False, True) if kind == ir.MASK else edges(fmt) for kind in kernel.input_kinds]
    if math.prod(len(c) for c in choices) <= limit:
        return [list(c) for c in itertools.product(*choices)]
    rng = random.Random(f'edges:{kernel.name}')
    return [[rng.choice(c) for c in choices] for _ in range(limit)]


# ---------------------------------------------------------------------------------------------
# The interpreter on many cases, in parallel.

def to_value(x):
    if isinstance(x, bool):
        return x
    return interp.parse_limb(x.hex() if math.isfinite(x) else ('nan' if x != x else ('inf' if x > 0 else '-inf')))


def to_float(v):
    """A limb as a float; a mask as 1.0 or 0.0, which is how a runner's 1 and 0 read."""
    if isinstance(v, bool):
        return float(v)
    return float.fromhex(interp.format_limb(v))


def token(x):
    """An operand as the line protocol writes it."""
    return interp.format_mask(x) if isinstance(x, bool) else interp.format_limb(to_value(x))


def same(x, y):
    """Bit identity of two limbs, all NaNs being the same."""
    if x != x or y != y:
        return x != x and y != y
    return struct.pack('<d', x) == struct.pack('<d', y)


_machines = {}


def _run(job):
    directory, fused, consteval, name, fmt, cases = job
    key = (directory, fused, consteval)
    if key not in _machines:
        _machines[key] = interp.Machine(kernels(directory), fused=fused, consteval=consteval)
    m, f = _machines[key], interp.parse_format(fmt)
    return [[to_float(v) for v in m.run(name, f, [to_value(x) for x in case])] for case in cases]


_pool = None


def interpret(directory, name, fmt, cases, fused=True, consteval=False, chunk=1000):
    """The interpreter's outputs for each case, as floats, computed by a pool of processes."""
    global _pool
    jobs = [(directory, fused, consteval, name, fmt, cases[i:i + chunk])
            for i in range(0, len(cases), chunk)]
    if len(jobs) <= 1:
        return [out for job in jobs for out in _run(job)]
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=JOBS)
    return [out for part in _pool.map(_run, jobs) for out in part]
