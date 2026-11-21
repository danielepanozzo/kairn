"""The folds (docs/developer/design/milestone2.md, "Folds, the extension of the IR").

- Their descriptions and rules: each way of getting a fold wrong is refused, and the zero state is
  evaluated (rules.zero_state), here on every normalized pair of small formats as well.
- The interpreter: its lane order against an implementation of the definition of
  proofs/theories/Folds.v written here (lane, deal, firstn, skipn, the combination from lane 0),
  for every number of lanes; with fewer elements than lanes, with no lane and with one, the
  sequential order; and on toy formats, in exact arithmetic, the claims: the result valid and
  within the bound of fold_error with the heights of each order, the flag and the canonical NaN.
- The compiled C++: F_seq and F_lanes of every build of the runner (test_cxx's), and F_packed of
  every packed build (test_simd's), bit for bit against the interpreter, on lengths 0, 1, W - 1,
  W, W + 1, 2 W and random ones up to a few thousand, non-finite elements among them; F_packed
  prints what F_lanes with the same lanes prints.
- Rule R3 on the arrays the program supplies: a program that stores products into an array and
  sums it in the same function gets the sum of the rounded products from the _entry folds,
  whatever the compiler fuses; the folds of stored arrays, which do not guard, are the control.
- The model and the statements of a fold in Rocq, and the counts of its loops for the object-code
  check.
"""
import json
import math
import os
import random
import re
import subprocess
import unittest
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from fractions import Fraction as F

import common
import test_cxx as cxx
import test_simd as simd_tests
from kairn_gen import cpp, interp, ir, objcode, rocq, rules

FOLDS = ('sum_1', 'sum_1_entry', 'sum_2', 'sum_2_entry', 'sum_fast_2', 'sum_fast_2_entry', 'dot_1', 'dot_2')
# The folds of maxima (architecture.md, "Folds of maxima"): a state of a limb and a mask, and an upper
# bound of the largest magnitude instead of fold_error. ALL: every fold that is not a map.
MAX_FOLDS = ('norm_upper_1', 'norm_upper_2')
ALL = FOLDS + MAX_FOLDS
# The convolutions, which write an array, have tests of their own (test_conv.py).
CONVS = {'conv_1', 'conv_2'}
# The maps, the folds that write an array, have tests of their own (test_maps.py).
MAPS = {'add_1', 'add_1_entry', 'add_2', 'add_2_entry', 'sub_1', 'sub_1_entry', 'sub_2', 'sub_2_entry', 'axpy_1',
        'axpy_1_entry', 'axpy_2', 'axpy_2_entry', 'axpy_2_1', 'axpy_2_1_entry', 'scale_1', 'scale_2',
        'mul_pow2_map_1', 'mul_pow2_map_2'}
# The ball vectors, maps of the centers with the state of a fold of maxima (test_bv.py).
BVS = {'bv_add_1', 'bv_add_2', 'bv_sub_1', 'bv_sub_2', 'bv_scale_1', 'bv_scale_2'}
# And the constructors of a BallVector (test_bv.py).
BVS |= {'bv_make_1', 'bv_make_2'}
# And the negations.
BVS |= {'bv_neg_1', 'bv_neg_2'}
# And the scalings by a power of two, exact under conditions.
BVS |= {'bv_mul_pow2_1', 'bv_mul_pow2_2'}
# The products of two BallVectors, a convolution of the centers with the maxima of both operands
# (test_bv_conv.py).
PRODUCTS = {'bv_conv_1', 'bv_conv_2'}


# ---------------------------------------------------------------------------------------------
# The rules.

BASE = '''
fold:          tf
arrays:        stored x = x0 x1
state:         s = s0 s1
step:          s = add_2_2(s, x)
combine:       s = add_2_2(s, s)
orders:        sequential, lanes
writes:        none
output:        r = r0 r1
output:        mask flag
finish:        (r, flag) = fold_finish_2(s)
value:         x
requires:      canonical x
ensures:       normalized r
ensures:       fold_error r eps=3*u^2/(1-4*u) rel=n-1
ensures:       finite_or_nan r flag=flag
min_precision: 3
status:        unverified
domain:        extended
'''


def refusals(text, *more):
    """The refusals of the fold of `text` among the kernels of gen/kernels and those of `more`."""
    ks = dict(common.kernels())
    for m in more:
        k = ir.parse_kernel(m, 'more.kernel')
        ks[k.name] = k
    fd = ir.parse_fold(text, 'tf.fold')
    kset = ir.ordered(ks, {fd.name: fd})
    return [str(e) for e in rules.fold_rules(fd, kset)]


# A combination whose zero state is not one: 0 + 0 is eta, and 0 + x is x + eta.
BADD = '''
kernel:        badd
input:         x = x0 x1
input:         y = y0 y1
output:        z = z0 z1
value:         x+y
requires:      normalized x
requires:      normalized y
ensures:       normalized z
ensures:       error z R c=3/(1-4*u) k=2 t=0
min_precision: 3
status:        unverified
(a0, a1) = add_2_2(x0, x1, y0, y1)
c        = add(a0, const up(eta))
(z0, z1) = fast_two_sum(c, a1)
'''


# A fold of maxima: norm_upper_2 under another name.
MAXBASE = '''
fold:          tf
arrays:        stored x = x0 x1
state:         m, mask ok
step:          (m, ok) = norm_step_2(m, ok, x)
combine:       (m, ok) = norm_combine(m, ok, m, ok)
orders:        sequential, lanes
writes:        none
output:        r
output:        mask flag
finish:        (r, flag) = norm_finish_2(m, ok)
value:         abs(x)
requires:      canonical x
ensures:       upper r max steps=1
ensures:       finite_or_nan r flag=flag
min_precision: 1
status:        unverified
domain:        extended
'''

# A combination that claims a maximum and returns its second operand: idempotent and associative,
# not commutative.
TMIN = '''
kernel:        tmin
input:         m
input:         mask ok
input:         n
input:         mask okn
output:        r
output:        mask okr
ensures:       maximum r m n
min_precision: 1
status:        unverified
cone_exempt:   a select
c   = lt(m, n)
r   = select(c, n, n)
okr = and(ok, okn)
'''

# The step of norm_upper_2 on tmin.
TSTEP = '''
kernel:        tstep
input:         m
input:         mask ok
input:         x = x0 x1
output:        r
output:        mask okr
ensures:       maximum r m abs(x[0])
min_precision: 1
status:        unverified
unused:        x1 the finish covers it
cone_exempt:   a select
a        = abs(x0)
e        = eq(a, a)
(r, okr) = tmin(m, ok, a, e)
'''

# A finish that does not say that the mask gates its result.
TFIN = '''
kernel:        tfin
input:         m
input:         mask ok
output:        r
output:        mask flag
value:         m
ensures:       finite_or_nan r flag=flag
min_precision: 1
status:        unverified
domain:        extended
ieee_status:   unverified
cone_exempt:   selects
s         = succ(m)
t         = select(ok, s, const nan)
(r, flag) = fold_finish_1(t)
'''


class Rules(unittest.TestCase):
    def test_the_folds_are_accepted(self):
        ks = common.kernels()
        self.assertEqual(set(ks.folds), set(ALL) | MAPS | CONVS | BVS | PRODUCTS)
        self.assertEqual({n for n, fd in ks.folds.items() if fd.is_max}, set(MAX_FOLDS))
        self.assertEqual({n for n, fd in ks.folds.items() if fd.is_map}, MAPS)
        for fd in ks.folds.values():
            self.assertEqual(rules.fold_rules(fd, ks), [], fd.name)
        self.assertEqual(refusals(BASE), [])

    def refused(self, text, words, *more):
        errors = refusals(text, *more)
        self.assertTrue(any(words in e for e in errors), (words, errors))

    def test_descriptions(self):
        with self.assertRaises(ir.DescriptionError):            # an array is stored or supplied
            ir.parse_fold(BASE.replace('stored x', 'x'), 'tf.fold')
        with self.assertRaises(ir.DescriptionError):            # a fold has no listing
            ir.parse_fold(BASE + 's = add(a, b)\n', 'tf.fold')
        with self.assertRaises(ir.DescriptionError):            # writes: and finish: are said
            ir.parse_fold(BASE.replace('writes:        none\n', ''), 'tf.fold')
        with self.assertRaises(ir.DescriptionError):
            ir.parse_fold(BASE.replace('ensures:       fold_error r eps=3*u^2/(1-4*u) rel=n-1',
                                       'ensures:       fold_error r rel=n-1'), 'tf.fold')

    def test_the_shapes_of_the_state(self):
        self.refused(BASE.replace('stored x = x0 x1', 'stored x').replace('requires:      canonical x\n', ''),
                     'takes y of 2 limbs where the fold passes x of 1')
        self.refused(BASE.replace('step:          s = add_2_2(s, x)', 'step:          s = add_2_2(s, s)'),
                     'its arguments are the state and every array once')
        self.refused(BASE.replace('combine:       s = add_2_2(s, s)', 'combine:       s = add_1_1(s, s)'),
                     'combine: add_1_1 takes two groups and returns one')
        self.refused(BASE.replace('fold_finish_2(s)', 'fold_finish_1(s)'),
                     'finish: fold_finish_1 takes one group of the shape of the state')
        self.refused(BASE.replace('step:          s = add_2_2(s, x)', 'step:          s = nope(s, x)'),
                     'nope is not a kernel')
        self.refused(BASE.replace('combine:       s = add_2_2(s, s)\n', ''),
                     'the lane order combines the lanes')
        # A fold that writes an array is a map, with a state of one mask (test_maps.py).
        self.refused(BASE.replace('writes:        none', 'writes:        z'), 'the state of a map is one mask')
        self.refused(BASE.replace('orders:        sequential, lanes', 'orders:        sequential, sideways'),
                     'orders: some of sequential, lanes')

    def test_r3_on_supplied_arrays(self):
        # add_2_2 takes y as stored limbs: a supplied array cannot be its operand; add_1_1, which
        # adds its operand unguarded, is refused for a supplied array twice over.
        self.refused(BASE.replace('stored x', 'supplied x'),
                     'x is supplied by the program, and the step add_2_2 does not take y')
        one = BASE.replace('stored x = x0 x1', 'supplied x').replace('s = s0 s1', 's').replace(
            'add_2_2', 'add_1_1').replace('r = r0 r1', 'r').replace('fold_finish_2', 'fold_finish_1').replace(
            'requires:      canonical x\n', '').replace('ensures:       normalized r\n', '').replace(
            'eps=3*u^2/(1-4*u)', 'eps=u/(1+u)').replace('min_precision: 3', 'min_precision: 1')
        errors = refusals(one)
        self.assertTrue(any('reaches an operand of add at s in the step add_1_1 without passing through guard' in e
                            for e in errors), errors)
        self.assertEqual(refusals(one.replace('supplied x', 'stored x')), [])
        self.assertEqual(refusals(one.replace('add_1_1(s, x)', 'sum_entry_step_1(s, x)')), [])
        # The steps of the dot products only multiply: supplied arrays need no guard.
        self.assertEqual(rules.fold_rules(common.kernels().folds['dot_2'], common.kernels()), [])

    def test_the_zero_state(self):
        self.refused(BASE.replace('combine:       s = add_2_2(s, s)', 'combine:       s = sub_2_2(s, s)'),
                     'the combination sub_2_2 has no lemma')
        saved = dict(rules.ZERO_LEMMAS)
        rules.ZERO_LEMMAS['badd'] = 'none'
        try:
            errors = refusals(BASE.replace('combine:       s = add_2_2(s, s)', 'combine:       s = badd(s, s)'),
                              BADD)
        finally:
            rules.ZERO_LEMMAS.clear()
            rules.ZERO_LEMMAS.update(saved)
        self.assertTrue(any('badd(0, 0) is not the zero state' in e for e in errors), errors)
        self.assertTrue(any('badd(0, x) does not have the value of x' in e for e in errors), errors)

    def test_claims(self):
        self.refused(BASE.replace('eps=3*u^2/(1-4*u)', 'eps=3*u^2'), 'is not the relative error of the combination')
        self.refused(BASE.replace('rel=n-1', 'rel=n-2'), 'a height is n or n-1')
        self.refused(BASE.replace('ensures:       normalized r', 'ensures:       rounded r nearest'),
                     'a fold claims normalized, fold_error, finite_or_nan')
        self.refused(BASE.replace('canonical x', 'normalized x'), 'requires "canonical ARRAY"')
        self.refused(BASE.replace('min_precision: 3', 'min_precision: 2'),
                     'the claims of add_2_2 hold from precision 3 on')
        self.refused(BASE.replace('value:         x', 'value:         y'), "+ - *, unary minus and abs( ) of the arrays")
        self.refused(BASE.replace('status:        unverified', 'status:        proved'),
                     'not marked unverified and names no theorem')

    def test_names(self):
        with open(os.path.join(common.GEN, 'kernels', 'add_1_1.kernel'), encoding='utf-8') as f:
            tf_seq = f.read().replace('add_1_1', 'tf_seq')
        self.refused(BASE, 'tf_seq is a name the printers make for the fold', tf_seq)
        self.refused(BASE.replace('r = r0 r1', 'r = n r1'), 'n is a name the printers use')

    def test_folds_of_maxima(self):
        """The checks of a fold of maxima (rules.max_rules, _fold_claims): its state, its
        combination and step, the zero state and the laws of the combination by evaluation, its
        finish and its claims."""
        self.assertEqual(refusals(MAXBASE), [])
        self.refused(MAXBASE.replace('state:         m, mask ok', 'state:         m, ok'),
                     'a limb and a mask, for a fold of maxima')
        self.refused(MAXBASE.replace('upper r max steps=1', 'upper r max steps=0'),
                     'as many times as the finish norm_finish_2 steps it (1)')
        self.refused(MAXBASE.replace('value:         abs(x)', 'value:         x'),
                     'the value of an element is its magnitude')
        self.refused(MAXBASE.replace('ensures:       upper r max steps=1\n',
                                     'ensures:       upper r max steps=1\nensures:       normalized r\n'),
                     'a fold claims upper, finite_or_nan')
        # A combination that is a minimum, or whose mask is an or: refused by their claims and
        # listings; one that claims a maximum and computes something else, by evaluation.
        self.refused(MAXBASE.replace('norm_combine', 'tmin'),
                     'claims the maximum of its two limb operands', TMIN.replace('maximum r m n', 'upper r value=m'))
        self.refused(MAXBASE.replace('norm_combine', 'tmin'), 'returns the and of its two masks',
                     TMIN.replace('okr = and(ok, okn)', 'okr = or(ok, okn)'))
        errors = refusals(MAXBASE.replace('norm_combine(m, ok, m, ok)', 'tmin(m, ok, m, ok)'), TMIN)
        self.assertTrue(any('the step norm_step_2 of a fold of maxima is a call of its combination tmin' in e
                            for e in errors), errors)
        errors = refusals(MAXBASE.replace('norm_combine', 'tmin').replace('norm_step_2', 'tstep'), TMIN, TSTEP)
        self.assertTrue(any('tmin is not commutative' in e for e in errors), errors)
        self.assertFalse(any('tmin(0, 0) is not the zero state' in e for e in errors), errors)
        self.refused(MAXBASE.replace('norm_finish_2(m, ok)', 'tfin(m, ok)'), 'claims finite_or_nan with if= its mask',
                     TFIN)

    def test_every_normalized_pair_of_small_formats(self):
        """Property 3 of the zero state (0 + x has the value of x; for these additions it is x,
        limb for limb), on every normalized pair of three formats, and property 4."""
        ks = common.kernels()
        m = interp.Machine(ks)
        for p, qmin, qmax in ((3, -6, 3), (4, -6, 3), (5, -5, 2)):
            f = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
            nums = sorted({interp.canon(s, mm, q) for q in range(qmin, qmax + 1) for mm in range(1, 2 ** p)
                           for s in (False, True)}, key=str) + [(interp.NUM, False, 0, 0)]
            pairs = [(a, b) for a in nums for b in nums if interp.eq(interp.add(f, a, b), a)]
            zero = [(interp.NUM, False, 0, 0)] * 2
            for name in ('add_2_2', 'add_fast_2_2'):
                if p < ks[name].min_precision:
                    continue
                self.assertEqual(m.run(name, f, zero + zero), zero)
                for a, b in pairs:
                    self.assertEqual(m.run(name, f, zero + [a, b]), [a, b], (name, f.name, a, b))
            for a in nums:
                self.assertEqual(m.run('add_1_1', f, [(interp.NUM, False, 0, 0), a]), [a])


# ---------------------------------------------------------------------------------------------
# The interpreter.

def by_definition(machine, fd, f, lanes, elements):
    """The lane order as proofs/theories/Folds.v defines it, written here from the definition and
    nothing of interp.run_fold: lane W k xs, deal W, firstn and skipn of W (n / W), each lane
    folded from the zero state, combine_lanes (fold_left of the combination over the tail, from
    the head, or the zero state), the rest folded into it. `elements` are lists of limb values,
    in the order of the fold's arrays and limbs."""
    step, combine = machine.kernels[fd.step[0]], machine.kernels[fd.combine[0]]
    # The zero state: every limb +0, every mask true.
    zero = [True if g.kind == ir.MASK else (interp.NUM, False, 0, 0) for g in fd.states for _ in g.limbs]
    sizes = [len(g.limbs) for g in fd.arrays]

    def apply_step(s, e):
        groups, at = {}, 0
        for g, size in zip(fd.arrays, sizes):
            groups[g.name] = e[at:at + size]
            at += size
        at = 0
        for g in fd.states:
            groups[g.name] = s[at:at + len(g.limbs)]
            at += len(g.limbs)
        args = []
        for a in fd.step[1]:
            args += groups[a]
        return machine.run(step.name, f, args)

    def fold_seq(xs, s):
        for e in xs:
            s = apply_step(s, e)
        return s

    def lane(w, k, xs):              # Fixpoint lane W k xs
        if not xs:
            return []
        if k == 0:
            return [xs[0]] + lane(w, w - 1, xs[1:])
        return lane(w, k - 1, xs[1:])

    def deal(w, xs):
        return [lane(w, j, xs) for j in range(w)]

    n = len(elements)
    cut = lanes * (n // lanes) if lanes else 0       # W * (length xs / W), with n / 0 = 0
    states = [fold_seq(xs, zero) for xs in deal(lanes, elements[:cut])]
    head = states[0] if states else zero              # hd zero states
    for s in states[1:]:                              # fold_left combine (tl states)
        head = machine.run(combine.name, f, head + s)
    return fold_seq(elements[cut:], head)


def elements_for(rng, fd, fmt, n, special=0.0):
    """n elements of the fold's arrays: limb lists in the order of its arrays and limbs, normalized
    pairs for two limbs; near each other or apart, with cancellation; with probability `special`
    an element is not finite (infinite or NaN, in canonical form)."""
    out = []
    for _ in range(n):
        e = []
        for g in fd.arrays:
            if rng.random() < special:
                x0 = rng.choice((math.inf, -math.inf, math.nan))
                e += [x0] + [0.0 if x0 == x0 else math.nan] * (len(g.limbs) - 1)
                continue
            stratum = rng.randrange(4)
            if stratum == 0:
                x0 = common.wide(rng, fmt)
            elif stratum == 1:
                x0 = common.near(rng, fmt, 0, 2 * common.FORMATS[fmt][0])
            elif stratum == 2 and out:
                x0 = -out[-1][0] if math.isfinite(out[-1][0]) else 1.0     # cancellation
            else:
                x0 = common.near(rng, fmt, rng.choice((-30, 0, 20)), 4)
            limbs = [x0]
            for _ in g.limbs[1:]:
                limbs.append(common.tail(rng, fmt, limbs[-1]))
            e += limbs
        out.append(e)
    return out


def arrays_of(elements, fd):
    """The limb arrays of a list of elements, one list per limb array."""
    return [[e[i] for e in elements] for i in range(len(fd.array_limbs()))]


def request(fd, fmt, order, lanes, elements):
    o = 'seq' if order == 'sequential' else f'lanes:{lanes}'
    limbs = [x for arr in arrays_of(elements, fd) for x in arr]
    return f'{fd.name} {fmt} {o} {len(elements)}' + ''.join(' ' + common.token(x) for x in limbs)


_machines = {}


def _run_fold(job):
    name, fmt, order, lanes, arrays = job
    if 'm' not in _machines:
        _machines['m'] = interp.Machine(common.kernels())
    f = interp.parse_format(fmt)
    out = _machines['m'].run_fold(name, f, order, lanes, [[common.to_value(x) for x in a] for a in arrays])
    return [common.to_float(v) for v in out]


def interpret_folds(jobs):
    """The interpreter's outputs of fold requests (name, format, order, lanes, arrays), as floats,
    in parallel."""
    with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
        return list(ex.map(_run_fold, jobs, chunksize=4))


class Interp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()
        cls.m = interp.Machine(cls.ks)

    def test_the_lane_order_is_the_definition(self):
        rng = random.Random('lanes')
        for name in ALL:
            fd = self.ks.folds[name]
            for fmt in ('binary64', 'binary32'):
                f = interp.parse_format(fmt)
                for n in list(range(0, 20)) + [rng.randrange(20, 60) for _ in range(3)]:
                    els = [[common.to_value(x) for x in e] for e in elements_for(rng, fd, fmt, n)]
                    arrays = [[e[i] for e in els] for i in range(len(fd.array_limbs()))]
                    for w in (0, 1, 2, 3, 4, 5, 8, 9):
                        want = by_definition(self.m, fd, f, w, els)
                        self.assertEqual(self._state(fd, f, 'lanes', w, arrays), want, (name, fmt, n, w))
                        finish = self.m.run(fd.finish[0], f, want)
                        self.assertEqual(self.m.run_fold(name, f, 'lanes', w, arrays), finish, (name, fmt, n, w))

    def _state(self, fd, f, order, w, arrays):
        """The final state of a fold (its result before the finish)."""
        saved = fd.finish
        fd.finish = None
        try:
            return self.m.run_fold(fd.name, f, order, w, arrays)
        finally:
            fd.finish = saved

    def test_short_lists_one_lane_and_none_are_the_sequential_order(self):
        """fold_lanes_short, fold_lanes_1 and fold_lanes_0: bit for bit, the sign of a zero too."""
        rng = random.Random('short')
        for name in ALL:
            fd = self.ks.folds[name]
            f = interp.parse_format('binary64')
            for n in range(0, 12):
                arrays = [[common.to_value(x) for x in a] for a in arrays_of(elements_for(rng, fd, 'binary64', n), fd)]
                seq = self.m.run_fold(name, f, 'sequential', 0, arrays)
                for w in [0, 1] + list(range(n + 1, n + 4)):
                    self.assertEqual(self.m.run_fold(name, f, 'lanes', w, arrays), seq, (name, n, w))

    def test_empty_and_non_finite(self):
        f = interp.parse_format('binary32')
        for name in FOLDS:
            fd = self.ks.folds[name]
            limbs = len(fd.array_limbs())
            zero = self.m.run_fold(name, f, 'sequential', 0, [[] for _ in range(limbs)])
            self.assertEqual(zero, [(interp.NUM, False, 0, 0)] * len(fd.state.limbs) + [True], name)
            for bad in ((interp.INF, False), (interp.INF, True), interp.NaN):
                one = interp.canon(False, 1, 0)
                arrays = [[one, one, one] for _ in range(limbs)]
                arrays[0][1] = bad
                for i in range(1, len(fd.arrays[0].limbs)):     # the element in canonical form
                    arrays[i][1] = (interp.NUM, False, 0, 0) if bad != interp.NaN else interp.NaN
                for order, w in (('sequential', 0), ('lanes', 2), ('lanes', 4)):
                    out = self.m.run_fold(name, f, order, w, arrays)
                    self.assertEqual(out[-1], False, (name, bad, order))
                    self.assertTrue(all(v == interp.NaN for v in out[:-1]), (name, bad, order, out))
        # An overflow of finite elements: the flag is false too.
        big = interp.canon(False, 2 ** 24 - 1, 104)
        out = self.m.run_fold('sum_1', f, 'sequential', 0, [[big, big]])
        self.assertEqual(out, [interp.NaN, False])

    def test_folds_of_maxima_empty_and_not_finite(self):
        """norm_upper_k: no element gives 0 for one limb and the step after it, eta, for two, with
        the flag true; an infinite or NaN element anywhere, in every order, the canonical NaN and the
        flag false (the NaN through the mask of the state, which a maximum by comparison would lose);
        and for two limbs a largest leading limb of Omega, whose step up is infinite, too."""
        for fmt in ('binary32', 'fp:4:-6:3'):
            f = interp.parse_format(fmt)
            zero = (interp.NUM, False, 0, 0)
            self.assertEqual(self.m.run_fold('norm_upper_1', f, 'sequential', 0, [[]]), [zero, True])
            self.assertEqual(self.m.run_fold('norm_upper_2', f, 'lanes', 4, [[], []]),
                             [interp.canon(False, 1, f.qmin), True])
            one, two = interp.canon(False, 1, 0), interp.canon(True, 1, 1)
            for name in MAX_FOLDS:
                limbs = len(self.ks.folds[name].array_limbs())
                for bad in ((interp.INF, False), (interp.INF, True), interp.NaN):
                    for at in range(5):
                        arrays = [[one, two, one, two, one]] + [[zero] * 5 for _ in range(limbs - 1)]
                        arrays[0][at] = bad
                        if limbs == 2 and bad == interp.NaN:
                            arrays[1][at] = interp.NaN
                        for order, w in (('sequential', 0), ('lanes', 2), ('lanes', 3), ('lanes', 4)):
                            self.assertEqual(self.m.run_fold(name, f, order, w, arrays), [interp.NaN, False],
                                             (name, fmt, bad, at, order, w))
            omega = interp.canon(False, 2 ** f.p - 1, f.qmax)
            self.assertEqual(self.m.run_fold('norm_upper_2', f, 'sequential', 0, [[one, omega], [zero, zero]]),
                             [interp.NaN, False])
            self.assertEqual(self.m.run_fold('norm_upper_1', f, 'sequential', 0, [[one, omega]]), [omega, True])

    def test_folds_of_maxima_in_exact_arithmetic(self):
        """On toy formats of precision 1 to 6, every fold of maxima in both orders: with the exponent
        range widened, the result is a number of the format at least the largest magnitude of an
        element and at most that magnitude rounded up then stepped up as the claim says; in the format
        itself, the same when the flag is true, the canonical NaN otherwise. Lists of up to 12
        elements, two limbs at the ends of what a normalized pair allows."""
        doc = {fd['name']: fd for fd in json.loads(open(os.path.join(common.GEN, 'claims.json')).read())['folds']}
        jobs = [(name, fmt, doc[name]) for name in MAX_FOLDS
                for fmt in ((1, -6, 3), (2, -6, 3), (3, -8, 4), (4, -10, 4), (5, -12, 5), (6, -12, 5))]
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge_max_fold, jobs))
        bad = [r for r in results if r[2]]
        self.assertEqual(bad, [])
        self.assertGreater(sum(r[1] for r in results), 10000)

    def test_the_line_protocol(self):
        formats = {}
        line = 'dot_1 fp:5:-12:6 lanes:2 3 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p+0 0x1p+0 #t'
        self.assertEqual(interp.complete(self.m, line, formats), line + ' -> 0x1.cp+2 1')
        self.assertEqual(interp.complete(self.m, 'sum_2 binary64 seq 0', formats), 'sum_2 binary64 seq 0 -> 0x0p+0 0x0p+0 1')
        for bad, words in (('sum_2 binary64 seq 1 0x1p+0', 'takes 2 limbs'),
                           ('sum_2 binary64 lanes 1 0x1p+0 0x0p+0', 'not an order'),
                           ('sum_2 binary64 lanes:02 1 0x1p+0 0x0p+0', 'not an order'),
                           ('sum_2 binary64 seq x 0x1p+0 0x0p+0', 'not a length'),
                           ('sum_2 binary64 seq', 'FORMAT ORDER N'),
                           ('sum_1 fp:3:-4:3 seq 1 0x1.1p+0', 'not a number of format')):
            with self.assertRaises(interp.InterpError, msg=bad) as e:
                interp.complete(self.m, bad, formats)
            self.assertIn(words, str(e.exception), bad)

    def test_the_claims_in_exact_arithmetic(self):
        """On toy formats, every fold in both orders and for several numbers of lanes: with nothing
        overflowing (the exponent range widened, as the Rocq statements are), the result is valid
        (normalized for two limbs) and within the bound of fold_error, with the heights of the
        order; in the format itself, the flag is true exactly when the result is finite, and the
        bound holds then. Lists of up to 12 elements, with cancellation."""
        doc = {fd['name']: fd for fd in json.loads(open(os.path.join(common.GEN, 'claims.json')).read())['folds']}
        jobs = []
        for name in FOLDS:
            for p, qmin, qmax in ((3, -8, 4), (4, -10, 4), (5, -12, 5), (6, -12, 5)):
                if p >= self.ks.folds[name].min_precision:
                    jobs.append((name, (p, qmin, qmax), doc[name]))
        with ProcessPoolExecutor(max_workers=common.JOBS) as ex:
            results = list(ex.map(_judge_fold, jobs))
        bad = [r for r in results if r[2]]
        self.assertEqual(bad, [])
        self.assertGreater(sum(r[1] for r in results), 10000)


def _value(v):
    return F(v[2]) * F(2) ** v[3] * (-1 if v[1] else 1)


def _judge_fold(job):
    """(name, cases judged, failures) of one fold on one toy format."""
    name, (p, qmin, qmax), claim = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    rng = random.Random(f'claims:{name}:{p}')
    tight = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
    wide = interp.Format(f'fp:{p}:{qmin}:{qmax + 200}', p, qmin, qmax + 200)
    u, eta = F(1, 2 ** p), F(2) ** qmin
    err = next(e for e in claim['ensures'] if e['kind'] == 'fold_error')
    from kairn_gen import consts, expr
    eps, term, tau = (consts.evaluate(expr.parse(err[k]), ks, p, qmin) for k in ('eps', 'term', 'tau'))
    nums = sorted({interp.canon(s, mm, q) for q in range(qmin, qmax + 1) for mm in range(1, 2 ** p)
                   for s in (False, True)}, key=str)
    tails = {}
    for x0, x1 in rules._operands(tight, 2):
        tails.setdefault(x0, []).append(x1)
    failures, count = [], 0
    for case in range(400):
        n = rng.randrange(0, 13)
        els = []
        for _ in range(n):
            e = []
            for g in fd.arrays:
                x0 = rng.choice(nums) if rng.random() < 0.8 or not els else interp.neg(els[-1][0])
                limbs = [x0]
                for _ in g.limbs[1:]:
                    # a second limb near the ends of what a normalized pair allows, or zero
                    cands = [y for y in tails.get(x0, []) if interp.eq(interp.add(tight, x0, y), x0)]
                    limbs.append(rng.choice(cands or [(interp.NUM, False, 0, 0)]))
                e += limbs
            els.append(e)
        arrays = [[e[i] for e in els] for i in range(len(fd.array_limbs()))]
        sizes = [len(g.limbs) for g in fd.arrays]

        def value(e):
            env, at = {}, 0
            for g, size in zip(fd.arrays, sizes):
                env[g.name] = sum(_value(v) for v in e[at:at + size])
                at += size
            return expr.evaluate(expr.parse(fd.value), env)
        exact = [value(e) for e in els]
        total, magnitude = sum(exact), sum(abs(t) for t in exact)
        for order, w in (('sequential', 0), ('lanes', 2), ('lanes', 3), ('lanes', 4), ('lanes', 8)):
            h = err['heights'][order]
            rel_h = n if h['rel'] == 'n' else max(n - 1, 0)
            abs_h = n if h['abs'] == 'n' else max(n - 1, 0)
            bound = ((1 + term) * (1 + eps) ** rel_h - 1) * magnitude + (1 + eps) ** abs_h * n * tau
            for f, reading in ((wide, 'statement'), (tight, 'format')):
                out = m.run_fold(name, f, order, w, arrays)
                r, flag = out[:-1], out[-1]
                count += 1
                if flag != (r[0][0] == interp.NUM):
                    failures.append((reading, order, w, 'flag'))
                    continue
                if not flag:
                    if reading == 'statement' or not all(v == interp.NaN for v in r):
                        failures.append((reading, order, w, 'not finite'))
                    continue
                if len(r) == 2 and not interp.eq(interp.add(f, r[0], r[1]), r[0]):
                    failures.append((reading, order, w, 'normalized'))
                if abs(sum(_value(v) for v in r) - total) > bound:
                    failures.append((reading, order, w, 'bound', n))
    return name, count, failures[:3]


def _round_up(f, x):
    """The smallest number of format f (without its top: an unbounded exponent) not below the
    nonnegative rational x, as an interpreter value."""
    if x == 0:
        return (interp.NUM, False, 0, 0)
    q = max(f.qmin, x.numerator.bit_length() - x.denominator.bit_length() - f.p - 1)
    while x >= F(2 ** f.p) * F(2) ** q:            # the exponent at which x has p digits or fewer
        q += 1
    m = -(-x // (F(2) ** q))                         # ceil(x / 2^q)
    return interp.canon(False, int(m), q)


def _judge_max_fold(job):
    """(name, cases judged, failures) of one fold of maxima on one toy format: the claim
    upper r max steps=S, max_i |x_i| <= r <= RU(max_i |x_i|) stepped up S times, with the exponent
    range widened (the Rocq statement) and in the format itself (the flag)."""
    name, (p, qmin, qmax), claim = job
    ks = common.kernels()
    fd = ks.folds[name]
    m = interp.Machine(ks)
    rng = random.Random(f'max:{name}:{p}')
    tight = interp.Format(f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax)
    wide = interp.Format(f'fp:{p}:{qmin}:{qmax + 200}', p, qmin, qmax + 200)
    steps = next(e['steps'] for e in claim['ensures'] if e['kind'] == 'upper')
    omega = F(2 ** p - 1) * F(2) ** qmax
    nums = sorted({interp.canon(s, mm, q) for q in range(qmin, qmax + 1) for mm in range(1, 2 ** p)
                   for s in (False, True)}, key=str) + [(interp.NUM, False, 0, 0), (interp.NUM, True, 0, 0)]
    tails = {}
    for x0, x1 in rules._operands(tight, 2):
        tails.setdefault(x0, []).append(x1)
    failures, count = [], 0
    for case in range(400):
        n = rng.randrange(0, 13)
        els = []
        for _ in range(n):
            x0 = rng.choice(nums)
            limbs = [x0]
            if len(fd.arrays[0].limbs) == 2:
                cands = [y for y in tails.get(x0, []) if interp.eq(interp.add(tight, x0, y), x0)]
                limbs.append(rng.choice(cands or [(interp.NUM, False, 0, 0)]))
            els.append(limbs)
        arrays = [[e[i] for e in els] for i in range(len(fd.array_limbs()))]
        big = max([abs(sum(_value(v) for v in e)) for e in els], default=F(0))
        for order, w in (('sequential', 0), ('lanes', 2), ('lanes', 3), ('lanes', 4), ('lanes', 8)):
            r_wide = None
            for f, reading in ((wide, 'statement'), (tight, 'format')):
                out = m.run_fold(name, f, order, w, arrays)
                r, flag = out[0], out[1]
                count += 1
                if reading == 'statement':
                    if not flag or r[0] != interp.NUM:
                        failures.append((reading, order, w, 'not finite'))
                        break
                    r_wide = _value(r)
                elif flag != (r_wide <= omega):
                    failures.append((reading, order, w, 'flag', r_wide))
                    continue
                if not flag:
                    if r != interp.NaN:
                        failures.append((reading, order, w, 'not the NaN'))
                    continue
                limit = _round_up(f, big)
                for _ in range(steps):
                    limit = interp.succ(f, limit)             # a step from Omega is +infinity
                top = _value(limit) if limit[0] == interp.NUM else None
                if not (big <= _value(r) and (top is None or _value(r) <= top)) or not interp.member(f, r):
                    failures.append((reading, order, w, 'upper', n, big, _value(r)))
    return name, count, failures[:3]


# ---------------------------------------------------------------------------------------------
# The compiled C++.

def lengths(rng):
    """The lengths of the C++ tests: 0, 1, W - 1, W, W + 1, 2 W for every W of the packed types
    (2, 4, 8), and random ones up to a few thousand."""
    out = sorted({0, 1} | {x for w in (2, 4, 8) for x in (w - 1, w, w + 1, 2 * w)})
    return out + [rng.randrange(17, 100) for _ in range(4)] + [rng.randrange(100, common.size(3000, 20000))
                                                              for _ in range(2)]


def fold_corpus(fmt, orders, seed):
    """[(fold, format, order, lanes, elements, request line)] for every fold."""
    ks = common.kernels()
    rng = random.Random(f'{seed}:{fmt}')
    out = []
    for name in ALL:
        fd = ks.folds[name]
        for n in lengths(rng):
            for special in (0.0, 0.0, 0.02 if n else 0.0):
                els = elements_for(rng, fd, fmt, n, special)
                for order, w in orders:
                    out.append((name, fmt, order, w, els, request(fd, fmt, order, w, els)))
    return out


def expected(cases):
    ks = common.kernels()
    return interpret_folds([(name, fmt, order, w, arrays_of(els, ks.folds[name])) for name, fmt, order, w, els, _ in cases])


class Cxx(unittest.TestCase):
    """F_seq and F_lanes of every build of the runner, bit for bit against the interpreter."""

    @classmethod
    def setUpClass(cls):
        if not cxx.COMPILERS:
            raise unittest.SkipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        cls.builds = cxx.shared_builds()
        orders = [('sequential', 0)] + [('lanes', w) for w in (0, 1, 2, 3, 4, 8)]
        cls.cases = fold_corpus('binary64', orders, 'cxx') + fold_corpus('binary32', orders, 'cxx')
        cls.want = expected(cls.cases)
        cls.text = ''.join(c[5] + '\n' for c in cls.cases)

    def test_every_build(self):
        reference = None
        for i, (label, _) in enumerate(self.builds.configs):
            with self.subTest(build=label):
                status, err = self.builds.results[i]
                self.assertEqual(status, 0, err)
                code, out, err = self.builds.run(i, self.text)
                self.assertEqual(code, 0, err)
                if out == reference:
                    continue
                bad = cxx.differences([(c[0], c[1], None, c[5]) for c in self.cases], self.want, out)
                self.assertEqual([b[0][:200] for b in bad[:3]], [], f'{len(bad)} of {len(self.cases)} differ')
                reference = out

    def test_the_lengths(self):
        ns = {len(c[4]) for c in self.cases}
        self.assertTrue({0, 1, 2, 3, 4, 5, 7, 8, 9, 16} <= ns)
        self.assertTrue(any(n >= 100 for n in ns))
        self.assertTrue(any(not math.isfinite(x) for c in self.cases for e in c[4] for x in e))

    def test_runner_protocol(self):
        code, out, err = self.builds.run(0, '# c\nsum_2 binary64 seq 0\ndot_1 binary32 lanes:2 3 0x1p+0 0x1p+1 0x1p+2 '
                                            '0x1p+0 0x1p+0 0x1p+0 #t\n')
        self.assertEqual(code, 0, err)
        self.assertEqual(out, '# c\nsum_2 binary64 seq 0 -> 0x0p+0 0x0p+0 1\n'
                              'dot_1 binary32 lanes:2 3 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p+0 0x1p+0 #t -> 0x1.cp+2 1\n')
        for line, words in (('sum_2 binary64 seq 1 0x1p+0', 'takes 2 limbs'), ('sum_2 binary64 lanes 0', 'not an order'),
                            ('sum_2 binary64 seq x', 'not a length'), ('sum_2 fp:4:-6:3 seq 0', 'binary64 and binary32'),
                            ('sum_1 binary32 seq 1 0x1p+200', 'not a binary32')):
            code, out, err = self.builds.run(0, '# fine\n' + line + '\n')
            self.assertEqual(code, 2, line)
            self.assertIn('line 2:', err)
            self.assertIn(words, err)


class Packed(unittest.TestCase):
    """F_packed of every packed build: what F_lanes of the scalar build with the same flags prints
    with the lanes of the register, and the interpreter's lane order, bit for bit."""

    @classmethod
    def setUpClass(cls):
        why = simd_tests.no_packed_backend()
        if why:
            raise unittest.SkipTest(why)
        cls.builds = simd_tests.shared_builds()
        cls.cases = {}
        for i, (label, _) in enumerate(cls.builds.configs):
            native = {'binary64': 2, 'binary32': 4} if simd_tests.ARM64 and 'x86_64' not in label else \
                {'binary64': 4, 'binary32': 8}
            key = tuple(sorted(native.items()))
            if key not in cls.cases:
                cases = []
                for fmt, w in native.items():
                    cases += fold_corpus(fmt, [('lanes', w)], 'packed')
                cls.cases[key] = (cases, expected(cases))

    def test_lane_by_lane(self):
        for i, (label, _) in enumerate(self.builds.configs):
            native = {'binary64': 2, 'binary32': 4} if simd_tests.ARM64 and 'x86_64' not in label else \
                {'binary64': 4, 'binary32': 8}
            cases, want = self.cases[tuple(sorted(native.items()))]
            text = ''.join(c[5] + '\n' for c in cases)
            with self.subTest(build=label):
                for status, err in self.builds.results[i]:
                    self.assertEqual(status, 0, err)
                code, packed, err = self.builds.run(i, 'packed', text)
                self.assertEqual(code, 0, err)
                code, scalar, err = self.builds.run(i, 'scalar', text)
                self.assertEqual(code, 0, err)
                p, s = packed.splitlines(), scalar.splitlines()
                differ = [(a[:120], b[:120]) for a, b in zip(p, s) if a != b]
                self.assertEqual(differ[:3], [], f'{len(differ)} of {len(p)} lines differ from F_lanes')
                bad = cxx.differences([(c[0], c[1], None, c[5]) for c in cases], want, packed)
                self.assertEqual([b[0][:200] for b in bad[:3]], [], f'{len(bad)} of {len(cases)} differ')

    def test_only_the_lanes_of_the_register(self):
        code, out, err = self.builds.run(0, 'packed', '# fine\nsum_2 binary64 seq 0\n')
        self.assertEqual(code, 2)
        self.assertIn('the lanes of its register only', err)


# ---------------------------------------------------------------------------------------------
# Rule R3: arrays the program fills.

def supplied_program(ctype):
    """The program of Supplied for one limb type. A program that stores a product into an element
    of an array and sums the array in the same function, the fold inlined there: for each sum of
    one and two limbs, stored and supplied, the sum of [c, a * b] so computed, and the sum of
    [c, RN(a b)] with the product rounded by a function that is not inlined, c = -RN(a b), so that
    the sum cancels and a product fused into the second addition shows. Prints, per fold, in how
    many of the cases the two differ."""
    lines = ['#include <cstdio>', '#include "kairn/gen/scalar.hpp"',
             '#if defined(_MSC_VER) && !defined(__clang__)', '#define NOINLINE __declspec(noinline)', '#else',
             '#define NOINLINE __attribute__((noinline))', '#endif',
             f'NOINLINE {ctype} rounded({ctype} a, {ctype} b) {{ volatile {ctype} p = a * b; return p; }}']
    folds = [('sum_1', 1), ('sum_1_entry', 1), ('sum_2', 2), ('sum_2_entry', 2), ('sum_fast_2', 2),
             ('sum_fast_2_entry', 2)]
    for name, limbs in folds:
        zero = '0' if ctype == 'double' else '0.0f'
        for form, product in (('inline', 'a * b'), ('ref', 'rounded(a, b)')):
            lines.append(f'NOINLINE {ctype} {name}_{form}({ctype} a, {ctype} b, {ctype} c) {{')
            lines.append(f'    {ctype} x0[2];')
            lines.append('    x0[0] = c;')
            lines.append(f'    x0[1] = {product};')
            args = ['x0']
            if limbs == 2:
                lines.append(f'    const {ctype} x1[2] = {{{zero}, {zero}}};')
                args.append('x1')
            outs = ['r0'] + (['r1'] if limbs == 2 else [])
            lines.append(f'    {ctype} {", ".join(o + " = 0" for o in outs)};')
            lines.append('    bool f = false;')
            lines.append(f'    kairn::gen::{name}_seq({", ".join(args)}, 2, {", ".join(outs)}, f);')
            lines.append('    return r0;')
            lines.append('}')
    utype = 'unsigned long long' if ctype == 'double' else 'unsigned'
    lines += ['int main() {',
              f'    {ctype} a = 1, b = 1, c = 0;',
              '    unsigned long long seed = 12345;']
    for name, _ in folds:
        lines.append(f'    long differ_{name} = 0;')
    p = 53 if ctype == 'double' else 24
    lines += ['    for (int i = 0; i < 20000; ++i) {',
              '        seed = seed * 6364136223846793005ull + 1442695040888963407ull;',
              f'        const {utype} m = ({utype})((seed >> 11) & ((1ull << {p - 1}) - 1)) | (({utype})1 << {p - 1});',
              f'        a = ({ctype})m / ({ctype})(1ull << {p - 1});              // in [1, 2)',
              f'        b = ({ctype})1 + ({ctype})((seed >> 7) & 1023) / ({ctype})(1 << 10);',
              '        c = -rounded(a, b);                                         // the sum cancels']
    for name, _ in folds:
        lines.append(f'        differ_{name} += {name}_inline(a, b, c) != {name}_ref(a, b, c);')
    lines.append('    }')
    for name, _ in folds:
        lines.append(f'    std::printf("{name} %ld\\n", differ_{name});')
    lines += ['    return 0;', '}']
    return '\n'.join(lines) + '\n'


class Supplied(unittest.TestCase):
    """Rule R3 on the arrays the program supplies. With every compiler and contraction setting at
    -O2: the _entry folds give the sum of the rounded products in every case; where the compiler
    fuses (GCC and Apple clang with -ffp-contract=fast), the folds of stored arrays, which do not
    guard, differ in some case, so that the test could fail."""

    def test_a_product_stored_into_a_supplied_array(self):
        if not cxx.COMPILERS:
            self.skipTest('no C++ compiler (set KAIRN_GEN_CXX)')
        d = common.scratch('supplied')
        jobs = []
        for ctype in ('double', 'float'):
            src = os.path.join(d, f'supplied_{ctype}.cpp')
            with open(src, 'w') as f:
                f.write(supplied_program(ctype))
            for c in cxx.COMPILERS:
                for contract in ('off', 'on', 'fast'):
                    exe = os.path.join(d, f'supplied_{ctype}_{len(jobs)}')
                    jobs.append((c, ctype, contract, [c, '-std=c++20', '-O2', f'-ffp-contract={contract}'] +
                                 (['-mfma'] if cxx.X86 else []) + ['-I', cxx.INCLUDE, src, '-o', exe], exe))
        with ThreadPoolExecutor(common.JOBS) as ex:
            built = list(ex.map(cxx.compile_, [j[3] for j in jobs]))
        controls = {}
        for (c, ctype, contract, _, exe), (status, err) in zip(jobs, built):
            with self.subTest(compiler=c, type=ctype, contract=contract):
                self.assertEqual(status, 0, err)
                out = subprocess.run([exe], capture_output=True, text=True, check=True).stdout
                differ = dict((line.split()[0], int(line.split()[1])) for line in out.splitlines())
                for name in ('sum_1_entry', 'sum_2_entry', 'sum_fast_2_entry'):
                    self.assertEqual(differ[name], 0, (name, out))
                controls[(c, ctype, contract)] = sum(differ[n] for n in ('sum_1', 'sum_2', 'sum_fast_2'))
        # The control: some compiler and setting here fuses into an unguarded fold, or the test
        # proves nothing about this machine's compilers. Printed either way.
        fused = sorted(k for k, v in controls.items() if v)
        print(f'\n  folds of stored arrays (no guard) fused by: {fused or "none"}', flush=True)
        if any('fast' in k for k in controls) and any(('clang' in c or c == 'c++' or 'g++' in c) for c, _, _ in controls):
            self.assertTrue(fused, controls)


# ---------------------------------------------------------------------------------------------
# Rocq and the object-code counts.

class Printers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = common.kernels()

    def test_the_model(self):
        m = rocq.fold_model(self.ks)
        self.assertIn('From Kairn Require Import Folds.', m)
        self.assertIn('Definition dot_2_step (s : R * R) (xy : (R * R) * (R * R)) : R * R :=\n'
                      '  dot_step_2 emin prec choice (fst s) (snd s) (fst (fst xy)) (snd (fst xy)) (fst (snd xy)) '
                      '(snd (snd xy)).', m)
        self.assertIn('Definition dot_2_combine (a b : R * R) : R * R :=\n'
                      '  add_2_2 emin prec choice (fst a) (snd a) (fst b) (snd b).', m)
        self.assertIn('Definition dot_2_seq (xs : list ((R * R) * (R * R))) : R * R :=\n'
                      '  fold_seq dot_2_step (0, 0) xs.', m)
        self.assertIn('Definition dot_2_lanes (W : nat) (xs : list ((R * R) * (R * R))) : R * R :=\n'
                      '  fold_lanes dot_2_step dot_2_combine (0, 0) W xs.', m)
        self.assertIn('Definition sum_1_seq (xs : list R) : R :=\n  fold_seq sum_1_step 0 xs.', m)
        # A fold of maxima: a state of a limb and a mask, from (0, true); no section variable,
        # since nothing in its step or combination rounds.
        self.assertIn('(* norm_upper_2: arrays stored x; state m (a limb), ok (a mask); step norm_step_2, combination '
                      'norm_combine. *)\n'
                      'Definition norm_upper_2_step (mok : R * bool) (x : R * R) : R * bool :=\n'
                      '  norm_step_2 (fst mok) (snd mok) (fst x) (snd x).\n\n'
                      'Definition norm_upper_2_combine (a b : R * bool) : R * bool :=\n'
                      '  norm_combine (fst a) (snd a) (fst b) (snd b).\n\n'
                      'Definition norm_upper_2_seq (xs : list (R * R)) : R * bool :=\n'
                      '  fold_seq norm_upper_2_step (0, true) xs.\n\n'
                      'Definition norm_upper_2_lanes (W : nat) (xs : list (R * R)) : R * bool :=\n'
                      '  fold_lanes norm_upper_2_step norm_upper_2_combine (0, true) W xs.', m)
        # Without folds the files say nothing but their header.
        empty = rocq.fold_model(common.kernels(common.TEST_KERNELS))
        self.assertNotIn('Definition', empty)

    def test_the_statements(self):
        s = rocq.fold_statements(self.ks)
        self.assertIn('From Kairn Require Import Folds Summation.', s)
        self.assertIn('Definition sum_2_lanes_spec : Prop :=\n'
                      '  forall emin prec : Z, (3 <= prec)%Z ->\n'
                      '  forall (W : nat) (xs : list (R * R)),\n'
                      '  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->\n'
                      '  let s := sum_2_lanes emin prec tie_even W xs in\n'
                      '  normalized_2 emin prec (fst s) (snd s) /\\\n'
                      '  Rabs ((fst s + snd s) - sumR (map (fun x => (fst x + snd x)) xs)) <=\n'
                      '    ((1 + ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))) ^ (length xs - 1) - 1) * '
                      'sumabs (map (fun x => (fst x + snd x)) xs).', s)
        self.assertIn('    (1 + ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))) ^ (length xys - 1) * (INR (length xys) * '
                      '((3 / 2) * eta emin)).', s)
        self.assertIn('    ((1 + (u prec / (1 + u prec))) ^ length xys - 1) * sumabs', s)
        # And three of conv_terms, which every convolution shares (rocq.conv_terms_statements).
        self.assertEqual(s.count('_spec : Prop'), 2 * len(ALL) + len(MAPS) + len(CONVS) + len(BVS) + len(PRODUCTS) + 3)
        self.assertIn('Definition conv_terms_eq_spec : Prop :=\n'
                      '  forall (A B : Type) (xs : list A) (ys : list B) (j : nat) (a : A) (b : B),\n'
                      '  conv_terms xs ys j =\n'
                      '  map (fun i => (nth i xs a, nth (j - i)%nat ys b))\n'
                      '      (seq (j - (length ys - 1))%nat (length (conv_terms xs ys j))).', s)
        self.assertIn('  (0 < length ys)%nat ->\n'
                      '  length (conv_terms xs ys j) = (Nat.min (S j) (length xs) - (j - (length ys - 1)))%nat.', s)
        self.assertIn('  (length (conv_terms xs ys j) <= Nat.min (length xs) (length ys))%nat.', s)
        # Without a convolution, not those three.
        self.assertNotIn('conv_terms', rocq.fold_statements(common.kernels(common.TEST_KERNELS)))
        # A fold of maxima: its result is the limb of the state stepped up as the finish does, a
        # number of the format between the largest magnitude and that rounded up and stepped up.
        self.assertIn('Definition norm_upper_2_seq_spec : Prop :=\n'
                      '  forall emin prec : Z, (1 <= prec)%Z ->\n'
                      '  forall xs : list (R * R),\n'
                      '  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->\n'
                      '  let mok := norm_upper_2_seq xs in\n'
                      '  let r_ := succ radix2 (FLT_exp emin prec) (fst mok) in\n'
                      '  let v_ := fold_right Rmax 0 (map (fun x => (Rabs (fst x + snd x))) xs) in\n'
                      '  fmt emin prec r_ /\\\n'
                      '  v_ <= r_ /\\\n'
                      '  r_ <= succ radix2 (FLT_exp emin prec) (RU emin prec v_).', s)
        self.assertIn('  let mok := norm_upper_1_lanes W xs in\n'
                      '  let r_ := fst mok in\n'
                      '  let v_ := fold_right Rmax 0 (map (fun x => (Rabs x)) xs) in\n'
                      '  fmt emin prec r_ /\\\n'
                      '  v_ <= r_ /\\\n'
                      '  r_ <= RU emin prec v_.', s)

    def test_the_ieee_model(self):
        """IeeeFoldModel.v: every fold in both orders, in the shape of FoldModel.v over floats, the
        finish on the final state; the section of IeeeModel.v."""
        from kairn_gen import ieee
        m = ieee.fold_model(self.ks)
        for name in ALL:
            for d in ('step', 'combine', 'seq', 'lanes'):
                self.assertIn(f'Definition {name}_{d} ', m)
        self.assertIn('Definition norm_upper_1_lanes (W : nat) (xs : list float) : float * bool :=\n'
                      '  let s := fold_lanes norm_upper_1_step norm_upper_1_combine (pzero, true) W xs in\n'
                      '  IeeeModel.norm_finish_1 prec emax nan_abs nan_const (fst s) (snd s).', m)
        self.assertIn('Definition dot_2_step (s : float * float) (xy : (float * float) * (float * float)) : float * float :=\n'
                      '  IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma (fst s) (snd s) (fst (fst xy)) '
                      '(snd (fst xy)) (fst (snd xy)) (snd (snd xy)).', m)
        self.assertIn('Definition sum_2_seq (xs : list (float * float)) : float * float * bool :=\n'
                      '  let s := fold_seq sum_2_step (pzero, pzero) xs in\n'
                      '  IeeeModel.fold_finish_2 prec emax nan_abs nan_const (fst s) (snd s).', m)
        self.assertIn('Definition sum_1_lanes (W : nat) (xs : list float) : float * bool :=\n'
                      '  let s := fold_lanes sum_1_step sum_1_combine pzero W xs in\n'
                      '  IeeeModel.fold_finish_1 prec emax nan_abs nan_const s.', m)
        section = m.split('Section IeeeFolds.\n', 1)[1]
        self.assertEqual([x for x in section.splitlines() if x.startswith(('Variable', 'Context'))],
                         [x for x in ieee.model(self.ks).split('Section IeeeKernels.\n', 1)[1].splitlines()
                          if x.startswith(('Variable', 'Context'))])

    def test_the_ieee_statements(self):
        """IeeeFoldStatements.v: per fold and order, the flag; and the lead statement of every step
        and combination of a fold."""
        from kairn_gen import ieee
        s = ieee.fold_statements(self.ks)
        for name in ALL:
            self.assertIn(f'Definition {name}_seq_ieee_spec : Prop :=', s)
            self.assertIn(f'Definition {name}_lanes_ieee_spec : Prop :=', s)
        # A fold of maxima has two more (ieee.max_orders_statement, ieee.max_flag_statement): its lane
        # order computes the state of the sequential order, and when exactly its flag is true.
        self.assertEqual(set(re.findall(r'^Definition (\w+)_orders_ieee_spec', s, flags=re.M)), set(MAX_FOLDS))
        self.assertEqual(set(re.findall(r'^Definition (\w+)_flag_ieee_spec', s, flags=re.M)), set(MAX_FOLDS))
        self.assertIn('  forall (W : nat) (xs : list (binary_float prec emax * binary_float prec emax)),\n'
                      '  fold_lanes (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) '
                      '(IeeeFoldModel.norm_upper_2_combine prec emax) (IeeeOperations.pzero prec emax, true) W xs =\n'
                      '  fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) '
                      '(IeeeOperations.pzero prec emax, true) xs.', s)
        self.assertIn('  snd (IeeeFoldModel.norm_upper_1_seq prec emax nan_abs nan_const xs) = true <->\n'
                      '  Forall (fun x => finite x) xs.', s)
        self.assertIn('  snd (IeeeFoldModel.norm_upper_2_seq prec emax nan_abs nan_const xs) = true <->\n'
                      '  Forall (fun x => finite (fst x)) xs /\\\n'
                      '  finite (IeeeOperations.succ prec emax (fst (fold_seq (IeeeFoldModel.norm_upper_2_step prec emax '
                      'nan_abs) (IeeeOperations.pzero prec emax, true) xs))).', s)
        # Not the steps and the combination of the folds of maxima, whose maximum keeps a finite
        # state for a NaN element (their mask says it instead).
        parts = {self.ks.folds[n].step[0] for n in FOLDS} | {self.ks.folds[n].combine[0] for n in FOLDS}
        # And the steps of the maps (their combination is the operation and).
        parts |= {self.ks.folds[n].step[0] for n in MAPS}
        # And the steps of the ball vectors (most are steps of maps).
        parts |= {self.ks.folds[n].step[0] for n in BVS}
        self.assertIn('   let s := FoldModel.norm_upper_2_lanes W vs in\n'
                      '   let r_ := succ radix2 (FLT_exp (ieee_emin prec emax) prec) (fst s) in\n'
                      '   let v_ := fold_right Rmax 0 (map (fun x => (Rabs (fst x + snd x))) vs) in\n'
                      '   val r = r_ /\\\n'
                      '   fmt (ieee_emin prec emax) prec r_ /\\\n'
                      '   v_ <= r_ /\\\n'
                      '   r_ <= succ radix2 (FLT_exp (ieee_emin prec emax) prec) (RU (ieee_emin prec emax) prec v_)) /\\\n'
                      '  (flag = false -> nan r).', s)
        self.assertEqual(set(re.findall(r'^Definition (\w+)_ieee_lead_spec', s, flags=re.M)), parts)
        self.assertIn('  let \'(t0, t1) := IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1 x0 x1 '
                      'y0 y1 in\n  finite t0 -> finite s0 /\\ finite x0 /\\ finite y0.', s)
        self.assertIn('  Forall (fun x => canonical_2 (fst x) (snd x)) xs ->\n'
                      "  let '(r0, r1, flag) := IeeeFoldModel.sum_2_seq prec emax nan_plus nan_minus nan_abs nan_const xs in\n"
                      '  (flag = true ->\n'
                      '   Forall (fun x => finite (fst x) /\\ finite (snd x)) xs /\\\n'
                      '   finite r0 /\\ finite r1 /\\\n'
                      '   let vs := map (fun x => (val (fst x), val (snd x))) xs in\n'
                      '   let s := FoldModel.sum_2_seq (ieee_emin prec emax) prec tie_even vs in\n'
                      '   (val r0, val r1) = s /\\\n'
                      '   normalized_2 (ieee_emin prec emax) prec (fst s) (snd s) /\\\n', s)
        self.assertIn('  (flag = false -> nan r0 /\\ nan r1).', s)
        # One limb: no requirement on an element, any value of the format.
        self.assertIn('  forall xs : list (binary_float prec emax),\n'
                      "  let '(r, flag) := IeeeFoldModel.sum_1_seq prec emax nan_plus nan_abs nan_const xs in\n", s)
        # The bound is the real model's, with emin = ieee_emin prec emax.
        self.assertNotRegex(s.split('Open Scope R_scope.', 1)[1], r'\bemin\b')

    def test_the_audit_of_a_proved_fold(self):
        import copy
        ks = copy.deepcopy(self.ks)
        for fd in ks.folds.values():        # the folds of the library are proved (FoldSums.v)
            fd.status, fd.theorem = 'unverified', None
        # Without a proved fold the audit neither imports the folds' statements nor checks a fold's
        # theorem (a kernel's theorem may be in a file of any name).
        audit = rocq.audit(ks)
        self.assertNotIn('Require Import FoldStatements.', audit)
        for name in ks.folds:
            self.assertNotIn(f'{name}_seq_correct', audit)
            self.assertNotIn(f'{name}_lanes_correct', audit)
        ks.folds['dot_2'].status = 'proved'
        ks.folds['dot_2'].theorem = 'proofs/theories/FoldDot.v'
        audit = rocq.audit(ks)
        self.assertIn('From Kairn.Gen Require Import Statements.\nFrom Kairn.Gen Require Import FoldStatements.\n', audit)
        self.assertIn('From Kairn Require Import FoldDot.\n', audit)
        self.assertIn('Definition dot_2_seq_audit : dot_2_seq_spec := dot_2_seq_correct.\n'
                      'Print Assumptions dot_2_seq_correct.', audit)
        self.assertIn('Print Assumptions dot_2_lanes_correct.', audit)

    def test_the_audit_of_a_proved_map(self):
        """A map has one statement, F_spec (FoldStatements.v), not one per order: the audit checks
        F_correct against it, and names no theorem of an order."""
        import copy
        ks = copy.deepcopy(self.ks)
        fd = ks.folds['axpy_1']
        self.assertTrue(fd.is_map)
        self.assertIn('Definition axpy_1_spec : Prop :=', rocq.fold_statements(ks))
        fd.status, fd.theorem = 'unverified', None      # the maps of the library are proved (FoldMaps.v)
        without = rocq.audit(ks)
        fd.status = 'proved'
        fd.theorem = 'proofs/theories/FoldAxpy.v'
        audit = rocq.audit(ks)
        self.assertIn('From Kairn.Gen Require Import Statements.\nFrom Kairn.Gen Require Import FoldStatements.\n', audit)
        self.assertIn('From Kairn Require Import FoldAxpy.\n', audit)
        self.assertIn('\nDefinition axpy_1_audit : axpy_1_spec := axpy_1_correct.\n'
                      'Print Assumptions axpy_1_correct.\n', audit)
        for order in fd.orders:
            self.assertNotIn(f'axpy_1_{ir.ORDER_SUFFIX[order]}', audit)
        # Exactly the one theorem of the map is audited among the folds.
        self.assertEqual(audit.count('_audit : '), without.count('_audit : ') + 1)

    def test_the_counts_of_the_loops(self):
        """gen/objcode.json gives each fold's functions as parts (objcode.py): the step at least
        once in F_seq, twice in F_lanes, packed and scalar in F_packed; each part's counts are those
        of its kernel's listing, the step's fused operations those of the step kernel."""
        doc = json.loads(objcode.objcode(self.ks))
        self.assertEqual(doc['fold_forms'], ['seq', 'lanes', 'packed'])
        self.assertEqual(set(doc['folds']), set(ALL) | MAPS | CONVS | BVS | PRODUCTS)
        names = doc['fold_parts']
        for name in ALL:
            fd = self.ks.folds[name]
            step = self.ks[fd.step[0]]
            want = objcode.kernel_counts(step, self.ks)['packed']
            for form, least in (('seq', {'step': 1}), ('lanes', {'step': 2, 'combine': 1}),
                                ('packed', {'packed step': 1, 'combine': 1, 'step': 1})):
                for t in objcode.LIMB_TYPES:
                    parts = {p[0]: dict(zip(names, p)) for p in doc['folds'][name][form][t]}
                    self.assertEqual({k: v['least'] for k, v in parts.items() if k != 'finish'}, least)
                    self.assertEqual(parts['finish']['least'], 1)
                    for part in ('step', 'packed step'):
                        if part in parts:
                            self.assertEqual(parts[part]['fma'], want[t]['fma'], (name, form, t))
                            self.assertEqual(parts[part]['mul'], 0)
        dot2 = dict(zip(names, doc['folds']['dot_2']['lanes']['double'][0]))
        self.assertEqual((dot2['fma'], dot2['fma_distinct']), (5, 5))
        self.assertEqual(dict(zip(names, doc['folds']['dot_1']['seq']['float'][0]))['fma'], 1)
        self.assertEqual(sum(dict(zip(names, p))['fma'] for p in doc['folds']['sum_2_entry']['packed']['double']), 0)
        # Without folds, the file has the shape it had.
        self.assertNotIn('folds', json.loads(objcode.objcode(common.kernels(common.TEST_KERNELS))))

    def test_the_cxx_of_a_fold(self):
        text = cpp.scalar(self.ks)
        self.assertIn('#include <cstddef>', text)
        self.assertIn('inline void sum_2_seq(const double* x0_in, const double* x1_in, std::size_t n, double& r0_out, '
                      'double& r1_out, bool& flag_out) noexcept {', text)
        self.assertIn('inline void dot_1_lanes(const float* x_in, const float* y_in, std::size_t n, std::size_t lanes, '
                      'float& r_out, bool& flag_out) noexcept {', text)
        # Ordinary inline functions, not forced inline; the step inlined, its values step_V.
        self.assertNotIn('KAIRN_GEN_FORCEINLINE void sum_2_seq', text)
        self.assertIn('            const double step_t = fma_rn(x, y, s_lane_);', text)
        self.assertIn('        const double step_g0 = x0 + 0.0;', text)        # the guard of sum_entry_step_2
        from kairn_gen import simd
        avx = simd.header(simd.AVX2, self.ks)
        self.assertIn('inline void dot_2_packed(const double* x0_in', avx)
        self.assertIn('    const std::size_t full_ = n - n % 4;', avx)
        self.assertIn('    const std::size_t full_ = n - n % 8;', avx)
        self.assertIn('        const __m256d x0 = _mm256_loadu_pd(x0_in + i_);', avx)
        neon = simd.header(simd.NEON, self.ks)
        self.assertIn('    const std::size_t full_ = n - n % 2;', neon)
        self.assertIn('vst1q_f32(s_lanes_, s_lane_);', neon)
        # Test kernels without folds: the headers they had.
        tks = common.kernels(common.TEST_KERNELS)
        self.assertNotIn('cstddef', cpp.scalar(tks) + simd.header(simd.AVX2, tks))


if __name__ == '__main__':
    unittest.main()
