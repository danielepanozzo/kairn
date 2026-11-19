"""Operands from the literature for which a double-word algorithm comes close to its error bound.

Each case is transcribed exactly from the paper that gives it, with the page it is on; the search
(search.py) starts from them. Nothing here is a "known worst case" from memory: a case is listed
only where a paper writes its operands, and a kernel gets it only when the kernel's description
names that paper's algorithm (gen/kernels: `source:`), or computes it on negated operands (the
subtractions, which run the sum on -y), or is the full kernel of such a core (whose finite result
is the core's). The relative error each paper reports is in the comment; what the oracle measures
for Kairn's claims is in docs/developer/testing.md ("The adversarial search").

JMP17: M. Joldes, J.-M. Muller, V. Popescu, Tight and rigorous error bounds for basic building
blocks of double-word arithmetic, ACM TOMS 44(2), 2017, hal-01351529.
MR22: J.-M. Muller, L. Rideau, Formalization of double-word arithmetic, and comments on "Tight and
rigorous error bounds for basic building blocks of double-word arithmetic", ACM TOMS 48(1), 2022,
hal-02972245 (page numbers of the HAL version).
"""

from fractions import Fraction as Q

from . import fmt as F


def _pow(p):
    return Q(1, 1 << p)


def _cases(p):
    """(name, algorithm, x, y) for precision p, x and y as tuples of exact values: the cases that
    hold for every p, and those written for p = 53 when p is 53."""
    u = _pow(p)
    out = [
        # JMP17, p. 15res:6, after Theorem 2.2: DWPlusFP (Alg. 4) is asymptotically optimal;
        # relative error 2u^2/(1 + 3u - 2u^2), about 2u^2 - 6u^3 (1.99999999999999933 2^-106 for
        # p = 53).
        ("JMP17 p. 15res:6, DWPlusFP", "dw+fp",
         (Q(1), (2**p - 1) * u * u), (-(1 - u) / 2,)),
        # JMP17, p. 15res:7, after Algorithm 6: the "generic" example of AccurateDWPlusDW, relative
        # error asymptotically 2.25u^2.
        ("JMP17 p. 15res:7, AccurateDWPlusDW (generic)", "dw+dw",
         (Q(2**p - 1), -(2**p - 1) * _pow(p + 1)), (-Q(2**p - 5, 2), -(2**p - 1) * _pow(p + 3))),
        # MR22, p. 6, Property 2.1: the bound 3u^2/(1 - 4u) of AccurateDWPlusDW is asymptotically
        # optimal; relative error (3u^2 - 2u^3)/(1 + 3u - 3u^2 + 2u^3) (2.99999999999999877875 u^2
        # for p = 53). "Obtaining such an example by random testing is hopeless" (p. 7).
        ("MR22 p. 6, Property 2.1, AccurateDWPlusDW", "dw+dw",
         (Q(1), u - u * u), (-Q(1, 2) + u / 2, -u * u / 2 + u**3)),
        # JMP17, p. 15res:6, after Algorithm 5: SloppyDWPlusDW returns 0 for the exact value
        # 2^-2p, a relative error of 1. Kairn's claim of add_fast_2_2 is of form A, relative to
        # |x| + |y|, for this reason; the case is a cancellation, not a tight case of that claim.
        ("JMP17 p. 15res:6, SloppyDWPlusDW (relative error 1)", "dw+dw sloppy",
         (1 + 8 * u, -u), (-1 - 6 * u, -u + u * u)),
    ]
    if p == 53:
        out += [
            # JMP17, p. 15res:7, Equation (2): AccurateDWPlusDW, 2.24999999999999956 2^-106.
            ("JMP17 p. 15res:7, Equation (2), AccurateDWPlusDW", "dw+dw",
             (Q(9007199254740991), Q(-9007199254740991, 2**54)),
             (Q(-9007199254740987, 2), Q(-9007199254740991, 2**56))),
            # JMP17, p. 15res:13, after Theorem 4.3: DWTimesFP3 (Alg. 9), 1.984 2^-106.
            ("JMP17 p. 15res:13, DWTimesFP3", "dw*fp",
             (Q(4505619370757448), Q(-9003265529542491, 2**54)), (Q(4511413997183120),)),
            # JMP17, p. 15res:16, after Theorem 5.4: DWTimesDW3 (Alg. 12), 3.936 2^-106.
            ("JMP17 p. 15res:16, DWTimesDW3", "dw*dw",
             (Q(4510026974538724), Q(4232862152422029, 2**53)),
             (Q(4511576932111935), Q(2250098448199619, 2**52))),
            # MR22, p. 14, after the proof of Theorem 2.8 (Algorithm 8 there is DWTimesDW3): the
            # bound 4u^2 is very tight, 3.997u^2.
            ("MR22 p. 14, Theorem 2.8, DWTimesDW3", "dw*dw",
             (Q(2251799825991851, 2**51), Q(9007199203085987, 2**106)),
             (Q(4503599627471459, 2**52), Q(4503599627284651, 2**105))),
        ]
    return out


def _neg(t):
    return tuple(-v for v in t)


# The kernels that compute each algorithm, with how the paper's x and y become their inputs, in the
# order of the kernel's inputs. The subtractions are the sums on the negated subtrahend
# (gen/kernels: "add_2_1 (JMP17 Alg. 4) on -a", "add_2_1 ... on -y and a", "add_2_2 ... on -y"),
# and each full kernel's finite result is its core's.
KERNELS = {
    "dw+fp": {"add_2_1": lambda x, y: (x, y), "add_2_1_full": lambda x, y: (x, y),
              "sub_2_1": lambda x, y: (x, _neg(y)), "sub_2_1_full": lambda x, y: (x, _neg(y)),
              "sub_1_2": lambda x, y: (y, _neg(x)), "sub_1_2_full": lambda x, y: (y, _neg(x))},
    "dw+dw": {"add_2_2": lambda x, y: (x, y), "add_2_2_full": lambda x, y: (x, y),
              "sub_2_2": lambda x, y: (x, _neg(y)), "sub_2_2_full": lambda x, y: (x, _neg(y))},
    "dw+dw sloppy": {"add_fast_2_2": lambda x, y: (x, y),
                     "add_fast_2_2_full": lambda x, y: (x, y)},
    "dw*fp": {"mul_2_1": lambda x, y: (x, y), "mul_2_1_full": lambda x, y: (x, y)},
    "dw*dw": {"mul_2_2": lambda x, y: (x, y), "mul_2_2_full": lambda x, y: (x, y)},
}


def cases(kernel_name, fmt):
    """[(name, [operand limbs as fixed values, in input order])] for the kernel in the format: the
    cases whose operands are numbers of the format (a case of p = 53 in binary64 only)."""
    out = []
    for name, alg, x, y in _cases(fmt.p):
        f = KERNELS[alg].get(kernel_name)
        if f is None:
            continue
        ops = []
        for t in f(x, y):
            limbs = []
            for v in t:
                n = v * Q(2) ** -fmt.qmin
                if n.denominator != 1 or not F.is_member(fmt, int(n)):
                    limbs = None
                    break
                limbs.append(int(n))
            if limbs is None:
                ops = None
                break
            ops.append(limbs)
        if ops is not None and all(F.normalized_limbs(fmt, o) for o in ops if len(o) > 1):
            out.append((name, ops))
    return out
