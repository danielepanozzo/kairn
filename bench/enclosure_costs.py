#!/usr/bin/env python3
"""enclosure_costs.py: what the settings of KAIRN_ENCLOSURE_CODE cost and save (include/kairn/config.hpp;
docs/developer/results/costs-milestone2.md, docs/developer/results/bench-milestone2.md).

  enclosure_costs.py source N [--kind KIND]
      Prints a translation unit with N operations in straight-line code, in one function. KIND
      ball2 (the default, the unit of costs-milestone2.md): operations of Ball<double, 2>, a mix of
      +, -, * and the scaling by a double, in turn, each on two of the eight values computed last
      (chosen by a fixed seed), each result stored, so that none is dead. KIND interval1,
      interval2 or mixed: operations of Interval<double, 1>, of Interval<double, 2>, or of the three
      types Ball<double, 2>, Interval<double, 1> and Interval<double, 2> in turn (+, * and - of each,
      and the scaling of a ball), each on one of the eight values of its type computed last and one
      of eight inputs, each result stored: a unit whose values stay bounded, so that it can be run
      (--run) and measures the arithmetic, not the special values of an overflow.
  enclosure_costs.py compile --cxx CXX [--msvc] [--flags "..."] [--kind KIND] [--cpu N]
                     [--sizes 100,1000,10000] [--configs O2,O3]
                     [--settings inline,outlined,external[,calls]] [--reps R] [--timeout S]
                     [--run [--run-reps R]] [--once-from N]
                     --workdir DIR --machine TEXT --commit TEXT --json FILE
      Writes those units into DIR and compiles each (nothing is linked) with each configuration and
      setting, R times in rounds over all of them (once for the units of the largest size, or of N
      operations or more), and records the wall time, the processor time and the peak memory of
      each compilation, and the size of the object; and the same for bench/definitions.cpp, the translation unit that defines
      the operations for the external setting, which a program compiles once. The setting calls is
      the same code without Kairn, the types structures of doubles and the operations functions
      declared only: what the calls themselves cost the compiler. With --run (KIND interval1,
      interval2 or mixed), the object of the first compilation of each unit is linked with a small
      driver (and, external, with the definitions) and run: the time per operation of one call of
      the unit, the minimum and the median over --run-reps samples of about 4 ms.
  enclosure_costs.py report DIR
      The tables of docs/developer/results/costs-milestone2.md from DIR: compile-*.json, written by
      compile, and run-COMPILER-SETTING-LEVEL.json, written by kairn-bench-LEVEL,
      kairn-bench-outlined-LEVEL and kairn-bench-external-LEVEL (bench/README.md).

Measured as bench/compile_time.py measures (its measure()): the largest resident set of the
compiler and the processes it waits for. On a timeout only the process this script started is
terminated, and the compilation is recorded as such. Run from the repository root. --cpu pins the
script, and every compiler and program it starts, to one logical processor (Linux).
"""
import argparse
import datetime
import glob
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import compile_time  # noqa: E402

SETTINGS = {'inline': 'KAIRN_ENCLOSURE_CODE_INLINE', 'outlined': 'KAIRN_ENCLOSURE_CODE_OUTLINED',
            'external': 'KAIRN_ENCLOSURE_CODE_EXTERNAL'}
CONFIGS = {'gnu': {'O2': ['-O2', '-DNDEBUG'], 'O3': ['-O3', '-DNDEBUG']},
           'msvc': {'O2': ['/O2', '/DNDEBUG']}}


def source(n, seed=1, calls=False):
    """A translation unit with n operations of Ball<double, 2> in one function. With calls, the same
    code without Kairn: B is a structure of three doubles and the operations are functions declared
    only, the floor of what any unit of n calls of them costs a compiler."""
    rng = random.Random(seed)
    out = ['// Written by bench/enclosure_costs.py: %d operations of kairn::Ball<double, 2> in straight-line'
           % n,
           '// code, each result stored.' + (' The same calls without Kairn: functions declared only.' if calls else '')]
    if calls:
        out += ['struct B {',
                '    double c0, c1, r;',
                '};',
                'B operator+(const B&, const B&) noexcept;',
                'B operator-(const B&, const B&) noexcept;',
                'B operator*(const B&, const B&) noexcept;',
                'B operator*(const B&, double) noexcept;']
    else:
        out += ['#include <kairn/kairn.hpp>',
                '',
                'using B = kairn::Ball<double, 2>;']
    out += ['',
            'void enclosure_unit(const B* in, const double* s, B* out) {']
    live = []
    for i in range(8):
        out.append('    const B v%d = in[%d];' % (i, i))
        live.append('v%d' % i)
    for i in range(n):
        a = live[-1 - rng.randrange(8)]
        b = live[-1 - rng.randrange(8)]
        op = i % 4
        if op == 0:
            expr = '%s + %s' % (a, b)
        elif op == 1:
            expr = '%s - %s' % (a, b)
        elif op == 2:
            expr = '%s * %s' % (a, b)
        else:
            expr = '%s * s[%d]' % (a, i % 8)
        out.append('    const B t%d = %s;' % (i, expr))
        out.append('    out[%d] = t%d;' % (i, i))
        live.append('t%d' % i)
    out.append('}')
    return '\n'.join(out) + '\n'


# The types of the new kinds, their stand-ins without Kairn (setting calls), and the operations of
# each kind in turn: (type, operator), 's' the scaling of a ball by a double.
TYPES = {'B': 'kairn::Ball<double, 2>', 'I': 'kairn::Interval<double, 1>', 'J': 'kairn::Interval<double, 2>'}
STAND_INS = {'B': 'double c0, c1, r;', 'I': 'double lo, hi;', 'J': 'double l0, l1, h0, h1;'}
KINDS = {'interval1': [('I', '+'), ('I', '*'), ('I', '-')],
         'interval2': [('J', '+'), ('J', '*'), ('J', '-')],
         'mixed': [('B', '+'), ('I', '+'), ('J', '+'), ('B', '*'), ('I', '*'), ('J', '*'), ('B', '-'),
                   ('I', '-'), ('J', '-'), ('B', 's')]}
UNIT_SIGNATURE = ('void enclosure_unit(const B* inb, const I* ini, const J* inj, const double* s, B* outb, '
                  'I* outi, J* outj)')


# The kinds of the enclosure interface (the second part of bench-milestone2.md): calls of the
# three-valued comparisons, of contains, and of hull, intersection and split, on Interval<double, 1>
# (I), Interval<double, 2> (J), Ball<double, 1> (C) and Ball<double, 2> (B) in turn. None of these
# returns an operand for the next, so each call takes operands of its own, elements of input arrays,
# and the compiler can merge none of them; each result is stored.
IFACE_TYPES = {'I': 'kairn::Interval<double, 1>', 'J': 'kairn::Interval<double, 2>', 'C': 'kairn::Ball<double, 1>',
               'B': 'kairn::Ball<double, 2>'}
IFACE_STAND_INS = {'I': 'double lo, hi;', 'J': 'double l0, l1, h0, h1;', 'C': 'double c, r;', 'B': 'double c0, c1, r;'}
IFACE_KINDS = {'compare': ['less', 'less_equal', 'equal'], 'contains': ['contains_t', 'contains_set'],
               'setops': ['hull', 'intersection', 'split']}


def source_iface(n, kind, calls=False):
    """A unit of n calls of KIND (compare, contains, setops) in one function, the four types in turn
    and the operations of the kind in turn for each, each call on elements of the inputs that no other
    call reads."""
    ops = [(t, o) for o in IFACE_KINDS[kind] for t in 'IJCB']
    out = ['// Written by bench/enclosure_costs.py: %d calls (%s) in straight-line code, each result stored.'
           % (n, kind) + (' The same calls without Kairn: functions declared only.' if calls else '')]
    if calls:
        out += ['enum class Trit : signed char { no = -1, unknown = 0, yes = 1 };',
                'template <class X>', 'struct Split {', '    X left, right;', '};']
        for t in 'IJCB':
            out += ['struct %s {' % t, '    ' + IFACE_STAND_INS[t],
                    '    bool contains(double) const noexcept;', '    bool contains(const %s&) const noexcept;' % t,
                    '    %s hull(const %s&) const noexcept;' % (t, t),
                    '    %s intersection(const %s&) const noexcept;' % (t, t),
                    '    Split<%s> split() const noexcept;' % t, '};']
            for o in IFACE_KINDS['compare']:
                out.append('Trit %s(const %s&, const %s&) noexcept;' % (o, t, t))
        split, ns = 'Split', ''
    else:
        out += ['#include <kairn/kairn.hpp>', '']
        for t in 'IJCB':
            out.append('using %s = %s;' % (t, IFACE_TYPES[t]))
        split, ns = 'kairn::Split', 'kairn::'
    args = ', '.join('const %s* x%s, const %s* y%s' % (t, t.lower(), t, t.lower()) for t in 'IJCB')
    args += ', const double* t, signed char* o8, ' + ', '.join('%s* o%s' % (t, t.lower()) for t in 'IJCB')
    args += ', ' + ', '.join('%s<%s>* s%s' % (split, t, t.lower()) for t in 'IJCB')
    out += ['', 'void enclosure_unit(%s) {' % args]
    count = {t: 0 for t in 'IJCB'}
    k8 = 0
    for i in range(n):
        t, o = ops[i % len(ops)]
        c = count[t]
        x, y = 'x%s[%d]' % (t.lower(), c), 'y%s[%d]' % (t.lower(), c)
        if o in IFACE_KINDS['compare']:
            out.append('    o8[%d] = static_cast<signed char>(%s%s(%s, %s));' % (k8, ns, o, x, y))
            k8 += 1
        elif o == 'contains_t':
            out.append('    o8[%d] = %s.contains(t[%d]);' % (k8, x, c))
            k8 += 1
        elif o == 'contains_set':
            out.append('    o8[%d] = %s.contains(%s);' % (k8, x, y))
            k8 += 1
        elif o == 'split':
            out.append('    s%s[%d] = %s.split();' % (t.lower(), c, x))
        else:
            out.append('    o%s[%d] = %s.%s(%s);' % (t.lower(), c, x, o, y))
        count[t] += 1
    out.append('}')
    return '\n'.join(out) + '\n'


# Milestone 2, third part (bench-milestone2.md, question 19): calls of the functions on arrays
# (kairn/batch.hpp) and of the operations of ball vectors (kairn/ball_vector.hpp), one and two limbs
# of double, in turn; each call on arrays (or ball vectors) of its own, each result stored. Compiled
# with the flags of packed code (--flags with -mavx2 on x86-64), as a unit that wants their fast
# order is; KAIRN_ENCLOSURE_CODE changes neither (their functions are ordinary inline functions in
# every setting), so only the settings inline and calls are meaningful.
ARRAY_OPS = ['sum1', 'sum2', 'dot1', 'dot2', 'add1', 'add2', 'scale1', 'scale2', 'axpy1', 'axpy2', 'conv1',
             'conv2', 'norm1', 'norm2']
BV_OPS = [(op, k) for op in ('add', 'sub', 'scale', 'axpy', 'conv', 'norm') for k in (1, 2)]
BV_ENTRIES = 8


def source_arrays(n, calls=False):
    """A unit of n calls of the functions on arrays, ARRAY_OPS in turn, on arrays of 64 elements
    (32 coefficients for conv) that no other call reads: p holds pointers to the input limb arrays,
    q to the output ones."""
    out = ['// Written by bench/enclosure_costs.py: %d calls of the functions on arrays in straight-line code, '
           'each result stored.' % n + (' The same calls without Kairn: functions declared only.' if calls else '')]
    if calls:
        out += ['#include <cstddef>', 'namespace k {',
                'struct V1 { const double* x; std::size_t n; };', 'struct V2 { const double *x, *y; std::size_t n; };',
                'struct W1 { double* x; std::size_t n; };', 'struct W2 { double *x, *y; std::size_t n; };',
                'struct R1 { double v; bool f; };', 'struct R2 { double v0, v1; bool f; };',
                'R1 sum(V1) noexcept;', 'R2 sum(V2) noexcept;', 'R1 dot(V1, V1) noexcept;', 'R2 dot(V2, V2) noexcept;',
                'bool add(V1, V1, W1) noexcept;', 'bool add(V2, V2, W2) noexcept;',
                'bool scale(V1, double, W1) noexcept;', 'bool scale(V2, double, W2) noexcept;',
                'bool axpy(double, V1, V1, W1) noexcept;', 'bool axpy(double, V2, V2, W2) noexcept;',
                'bool conv(V1, V1, W1) noexcept;', 'bool conv(V2, V2, W2) noexcept;',
                'R1 norm_upper(V1) noexcept;', 'R1 norm_upper(V2) noexcept;', '}  // namespace k',
                'using k::V1; using k::V2; using k::W1; using k::W2;']
        v0, v1, ns = '.v', '.v1', 'k::'
        first, second = '.v', '.v0'
    else:
        out += ['#include <kairn/batch.hpp>', '', 'using V1 = kairn::SoAView<const double, 1>;',
                'using V2 = kairn::SoAView<const double, 2>;', 'using W1 = kairn::SoAView<double, 1>;',
                'using W2 = kairn::SoAView<double, 2>;']
        ns = 'kairn::'
        first, second, v1 = '.value.limb[0]', '.value.limb[0]', '.value.limb[1]'
    out += ['', 'void arrays_unit(const double* const* p, double* const* q, double a, double* o, bool* f) {']
    ip, iq, io, jf = 0, 0, 0, 0

    def v(k, length='64'):
        nonlocal ip
        if k == 1:
            s = 'V1(p[%d], %s)' % (ip, length)
            ip += 1
        else:
            s = 'V2(p[%d], p[%d], %s)' % (ip, ip + 1, length)
            ip += 2
        return s

    def w(k, length='64'):
        nonlocal iq
        if k == 1:
            s = 'W1(q[%d], %s)' % (iq, length)
            iq += 1
        else:
            s = 'W2(q[%d], q[%d], %s)' % (iq, iq + 1, length)
            iq += 2
        return s

    for i in range(n):
        op = ARRAY_OPS[i % len(ARRAY_OPS)]
        k = int(op[-1])
        name = op[:-1]
        if name in ('sum', 'dot', 'norm'):
            args = v(k) if name != 'dot' else '%s, %s' % (v(k), v(k))
            fn = 'norm_upper' if name == 'norm' else name
            if name == 'norm':
                out.append('    o[%d] = %s%s(%s)%s;' % (io, ns, fn, args, '.v' if calls else '.value'))
                io += 1
            elif k == 1:
                out.append('    o[%d] = %s%s(%s)%s;' % (io, ns, fn, args, first))
                io += 1
            else:
                out.append('    { const auto r = %s%s(%s); o[%d] = r%s; o[%d] = r%s; }'
                           % (ns, fn, args, io, second, io + 1, v1))
                io += 2
        elif name == 'conv':
            out.append('    f[%d] = %sconv(%s, %s, %s);' % (jf, ns, v(k, '32'), v(k, '32'), w(k, '63')))
            jf += 1
        elif name == 'add':
            out.append('    f[%d] = %sadd(%s, %s, %s);' % (jf, ns, v(k), v(k), w(k)))
            jf += 1
        elif name == 'scale':
            out.append('    f[%d] = %sscale(%s, a, %s);' % (jf, ns, v(k), w(k)))
            jf += 1
        else:   # axpy
            out.append('    f[%d] = %saxpy(a, %s, %s, %s);' % (jf, ns, v(k), v(k), w(k)))
            jf += 1
    out.append('}')
    return '\n'.join(out) + '\n'


def source_ballvectors(n, calls=False):
    """A unit of n operations of ball vectors of BV_ENTRIES entries, BV_OPS in turn (one and two
    limbs), each on operands of its own (elements of input arrays of ball vectors), each result
    stored."""
    m = BV_ENTRIES
    out = ['// Written by bench/enclosure_costs.py: %d operations of ball vectors in straight-line code, each '
           'result stored.' % n + (' The same calls without Kairn: functions declared only.' if calls else '')]
    if calls:
        out += ['#include <cstddef>', 'namespace k {']
        for kk in (1, 2):
            out += ['struct B%d { double c[%d]; double r; };' % (kk, kk * m),
                    'struct C%d { double c[%d]; double r; };' % (kk, kk * (2 * m - 1)),
                    'void add(const B%d&, const B%d&, B%d&) noexcept;' % (kk, kk, kk),
                    'void sub(const B%d&, const B%d&, B%d&) noexcept;' % (kk, kk, kk),
                    'void scale(const B%d&, double, B%d&) noexcept;' % (kk, kk),
                    'void axpy(double, const B%d&, const B%d&, B%d&) noexcept;' % (kk, kk, kk),
                    'void convolution(const B%d&, const B%d&, C%d&) noexcept;' % (kk, kk, kk),
                    'double norm_upper(const B%d&) noexcept;' % kk]
        out += ['}  // namespace k', 'using k::B1; using k::B2; using k::C1; using k::C2;']
        ns = 'k::'
    else:
        out += ['#include <kairn/ball_vector.hpp>', '']
        for kk in (1, 2):
            out += ['using B%d = kairn::BallVector<double, %d, %d>;' % (kk, kk, m),
                    'using C%d = kairn::BallVector<double, %d, %d>;' % (kk, kk, 2 * m - 1)]
        ns = 'kairn::'
    out += ['', 'void ball_vector_unit(const B1* x1, const B2* x2, B1* z1, B2* z2, C1* c1, C2* c2, double a, double* o) {']
    cnt = {1: 0, 2: 0}
    zc = {1: 0, 2: 0}
    cc = {1: 0, 2: 0}
    io = 0
    for i in range(n):
        op, kk = BV_OPS[i % len(BV_OPS)]
        x, y = 'x%d[%d]' % (kk, cnt[kk]), 'x%d[%d]' % (kk, cnt[kk] + 1)
        cnt[kk] += 2
        if op in ('add', 'sub'):
            out.append('    %s%s(%s, %s, z%d[%d]);' % (ns, op, x, y, kk, zc[kk]))
            zc[kk] += 1
        elif op == 'scale':
            out.append('    %sscale(%s, a, z%d[%d]);' % (ns, x, kk, zc[kk]))
            zc[kk] += 1
        elif op == 'axpy':
            out.append('    %saxpy(a, %s, %s, z%d[%d]);' % (ns, x, y, kk, zc[kk]))
            zc[kk] += 1
        elif op == 'conv':
            out.append('    %sconvolution(%s, %s, c%d[%d]);' % (ns, x, y, kk, cc[kk]))
            cc[kk] += 1
        else:
            out.append('    o[%d] = %snorm_upper(%s);' % (io, ns, x))
            io += 1
    out.append('}')
    return '\n'.join(out) + '\n'


def source_kind(n, kind, seed=1, calls=False):
    """A unit of n operations of KIND (interval1, interval2, mixed): each on one of the eight values
    of its type computed last and one of the eight inputs of that type, each result stored. The kinds
    of the enclosure interface are written by source_iface, those of the third part by source_arrays
    and source_ballvectors."""
    if kind in IFACE_KINDS:
        return source_iface(n, kind, calls=calls)
    if kind == 'arrays':
        return source_arrays(n, calls=calls)
    if kind == 'ballvectors':
        return source_ballvectors(n, calls=calls)
    rng = random.Random(seed)
    ops = KINDS[kind]
    used = sorted({t for t, _ in ops})
    out = ['// Written by bench/enclosure_costs.py: %d operations (%s) in straight-line code, each result stored.'
           % (n, kind) + (' The same calls without Kairn: functions declared only.' if calls else '')]
    if calls:
        for t in 'BIJ':
            out.append('struct %s {' % t)
            out.append('    ' + STAND_INS[t])
            out.append('};')
        for t in used:
            for o in '+-*':
                out.append('%s operator%s(const %s&, const %s&) noexcept;' % (t, o, t, t))
        if 'B' in used:
            out.append('B operator*(const B&, double) noexcept;')
    else:
        out += ['#include <kairn/kairn.hpp>', '']
        for t in 'BIJ':
            out.append('using %s = %s;' % (t, TYPES[t]))
    out += ['', UNIT_SIGNATURE + ' {']
    live, count = {}, {}
    for t in used:
        live[t] = []
        count[t] = 0
        for i in range(8):
            out.append('    const %s %s%d = in%s[%d];' % (t, t.lower(), i, t.lower(), i))
            live[t].append('%s%d' % (t.lower(), i))
    for i in range(n):
        t, o = ops[i % len(ops)]
        a = live[t][-1 - rng.randrange(8)]
        k = rng.randrange(8)
        expr = '%s * s[%d]' % (a, k) if o == 's' else '%s %s %s%d' % (a, o, t.lower(), k)
        name = 't%d' % i
        out.append('    const %s %s = %s;' % (t, name, expr))
        out.append('    out%s[%d] = %s;' % (t.lower(), count[t], name))
        count[t] += 1
        live[t].append(name)
    out.append('}')
    return '\n'.join(out) + '\n'


# The driver that runs a unit of a new kind: inputs near 1 with small widths and radii, so that every
# value stays a finite enclosure of moderate magnitude; the minimum and the median time per operation
# over the samples, and the number of results that are finite enclosures.
DRIVER = r"""// Written by bench/enclosure_costs.py: runs enclosure_unit and times it.
#include <kairn/kairn.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

using B = kairn::Ball<double, 2>;
using I = kairn::Interval<double, 1>;
using J = kairn::Interval<double, 2>;
using E = kairn::Expansion<double, 2>;
void enclosure_unit(const B* inb, const I* ini, const J* inj, const double* s, B* outb, I* outi, J* outj);

int main(int argc, char** argv) {
    const int n = std::atoi(argv[1]), reps = std::atoi(argv[2]);
    const double sample_ns = 4e6;
    B inb[8];
    I ini[8];
    J inj[8];
    double s[8];
    for (int k = 0; k < 8; ++k) {
        const double v = 0.99 + 0.0025 * k;   // inputs near 1: products by them stay in range
        inb[k] = B(E(v), 0x1p-80);
        ini[k] = I(kairn::Expansion<double, 1>(v), kairn::Expansion<double, 1>(v + v * 0x1p-40));
        inj[k] = J(E(v), E(v) + E(v * 0x1p-80));
        s[k] = 0.5 + 0.0625 * k;
    }
    std::vector<B> ob(std::size_t(n) + 1);
    std::vector<I> oi(std::size_t(n) + 1);
    std::vector<J> oj(std::size_t(n) + 1);
    auto once = [&] { enclosure_unit(inb, ini, inj, s, ob.data(), oi.data(), oj.data()); };
    using clock = std::chrono::steady_clock;
    auto time = [&](long calls) {
        const auto t0 = clock::now();
        for (long c = 0; c < calls; ++c) once();
        return std::chrono::duration<double, std::nano>(clock::now() - t0).count();
    };
    long calls = 1;
    double t = time(calls);
    while (t < 0.25 * sample_ns) t = time(calls *= 2);
    calls = std::max(1L, long(double(calls) * sample_ns / t));
    time(calls);
    std::vector<double> ns;
    for (int r = 0; r < reps; ++r) ns.push_back(time(calls) / (double(calls) * n));
    std::sort(ns.begin(), ns.end());
    long finite = 0, written = 0;
    for (int i = 0; i < n; ++i) {
        const std::size_t j = std::size_t(i);
        // Each type's results fill its array from the start; an untouched element is the point 0.
        finite += std::isfinite(ob[j].radius()) && std::isfinite(oi[j].upper().limb[0] - oi[j].lower().limb[0]) &&
                  std::isfinite(oj[j].upper().limb[0] - oj[j].lower().limb[0]);
        written += ob[j].radius() != 0 || oi[j].upper().limb[0] != oi[j].lower().limb[0] ||
                   oj[j].upper().limb[0] != oj[j].lower().limb[0];
    }
    std::printf("{\"ns_per_op_min\": %.4g, \"ns_per_op_median\": %.4g, \"calls_per_sample\": %ld, \"samples\": %d, "
                "\"finite\": %ld, \"written\": %ld}\n",
                ns.front(), ns[ns.size() / 2], calls, reps, finite, written);
    return 0;
}
"""


def cmd_source(args):
    sys.stdout.write(source(args.n) if args.kind == 'ball2' else source_kind(args.n, args.kind))
    return 0


def compile_command(args, src, config, setting, obj):
    family = 'msvc' if args.msvc else 'gnu'
    define = 'KAIRN_ENCLOSURE_CODE=' + SETTINGS.get(setting, SETTINGS['inline'])
    include = os.path.join(ROOT, 'include')
    if args.msvc:
        return [args.cxx, '/nologo', '/std:c++20', '/EHsc', '/arch:AVX2', '/I', include, '/D' + define] + \
            CONFIGS[family][config] + ['/c', src, '/Fo' + obj]
    isa = ['-mfma'] if compile_time.x86() else []
    extra = args.flags.split() if args.flags else []
    return [args.cxx, '-std=c++20', '-I', include, '-D' + define] + isa + extra + CONFIGS[family][config] + \
        ['-c', src, '-o', obj]


def link_and_run(args, workdir, n, config, setting, unit_obj, cache):
    """Links the object of a unit with the driver (and the definitions, external) and runs it; the
    driver and the definitions are compiled once per configuration and setting (cache)."""
    def build(name, src):
        key = (name, config, setting)
        if key not in cache:
            path = os.path.join(workdir, '%s.cpp' % name) if src is not None else os.path.join(HERE, 'definitions.cpp')
            if src is not None:
                with open(path, 'w') as f:
                    f.write(src)
            obj = os.path.join(workdir, '%s-%s-%s.o' % (name, config, setting))
            cmd = compile_command(args, path, config, setting, obj)
            status, _, _, _, text = compile_time.measure(cmd, args.timeout, cwd=workdir)
            if status != 0:
                raise SystemExit('failed: %s\n%s' % (' '.join(cmd), text[-3000:]))
            cache[key] = obj
        return cache[key]
    objs = [unit_obj, build('driver', DRIVER)]
    if setting == 'external':
        objs.append(build('definitions', None))
    exe = os.path.join(workdir, 'run-%d-%s-%s' % (n, config, setting))
    extra = args.flags.split() if args.flags else []
    status, _, _, _, text = compile_time.measure([args.cxx] + extra + objs + ['-o', exe], args.timeout, cwd=workdir)
    if status != 0:
        raise SystemExit('link failed:\n' + text[-3000:])
    done = subprocess.run([exe, str(n), str(args.run_reps)], capture_output=True, text=True, timeout=args.timeout)
    if done.returncode != 0:
        raise SystemExit('run failed: %s' % done.stderr[-2000:])
    os.remove(exe)
    return json.loads(done.stdout.strip().splitlines()[-1])


def cmd_compile(args):
    os.makedirs(args.workdir, exist_ok=True)
    pinning = compile_time.pin(args.cpu)
    sizes = [int(x) for x in args.sizes.split(',')]
    configs = args.configs.split(',')
    settings = args.settings.split(',')
    if args.run and (args.kind in ('ball2', 'arrays', 'ballvectors') or args.kind in IFACE_KINDS):
        raise SystemExit('--run needs --kind interval1, interval2 or mixed: the values of the ball2 unit overflow')
    make = (lambda n, calls=False: source(n, calls=calls)) if args.kind == 'ball2' else \
        (lambda n, calls=False: source_kind(n, args.kind, calls=calls))
    units = []
    for n in sizes:
        path = os.path.join(args.workdir, 'unit-%d.cpp' % n)
        with open(path, 'w') as f:
            f.write(make(n))
        calls = os.path.join(args.workdir, 'calls-%d.cpp' % n)
        with open(calls, 'w') as f:
            f.write(make(n, calls=True))
        for config in configs:
            for setting in settings:
                units.append(('unit', n, config, setting, calls if setting == 'calls' else path))
    for config in configs if 'external' in settings else []:
        units.append(('definitions', 0, config, 'external', os.path.join(HERE, 'definitions.cpp')))
    results = {}
    run_cache = {}
    largest = args.once_from or max(sizes)   # units of at least this many operations are compiled once
    for rep in range(args.reps):
        for kind, n, config, setting, path in units:
            if rep > 0 and n >= largest:
                continue
            key = '%s %d %s %s' % (kind, n, config, setting)
            r = results.setdefault(key, {'kind': kind, 'operations': n, 'config': config, 'setting': setting,
                                         'wall': [], 'cpu': [], 'peak_mb': [], 'status': []})
            obj = os.path.join(args.workdir, '%s-%d-%s-%s.%s' % (kind, n, config, setting,
                                                                 'obj' if args.msvc else 'o'))
            cmd = compile_command(args, path, config, setting, obj)
            status, wall, cpu, peak, text = compile_time.measure(cmd, args.timeout, cwd=args.workdir)
            r['wall'].append(round(wall, 3))
            r['cpu'].append(round(cpu, 3))
            r['peak_mb'].append(round(peak, 1))
            r['status'].append(status)
            if status == 0:
                r['object_bytes'] = os.path.getsize(obj)
                if args.run and rep == 0 and kind == 'unit' and setting != 'calls':
                    r['run'] = link_and_run(args, args.workdir, n, config, setting, obj, run_cache)
                    print('%-40s run: %.3g ns per operation, %d of %d finite' % (
                        key, r['run']['ns_per_op_min'], r['run']['finite'], n), flush=True)
            else:
                r['error'] = text[-2000:]
            print('%-40s %8.2f s %8.1f MB %s' % (key, wall, peak, 'ok' if status == 0 else
                                                  ('TIMEOUT' if status == -1 else 'FAILED %s' % status)),
                  flush=True)
    data = {'schema': 1, 'what': 'enclosure compile', 'date': args.date or datetime.date.today().isoformat(),
            'commit': args.commit,
            'machine': {'description': args.machine, 'cpu': compile_time.cpu_brand(), 'pinning': pinning},
            'compiler': compile_time.compiler_version(argparse.Namespace(msvc=args.msvc, cxx=args.cxx,
                                                                         flags=args.flags)),
            'cxx': os.path.basename(args.cxx), 'flags': args.flags, 'kind': args.kind, 'timeout': args.timeout,
            'reps': args.reps, 'run_reps': args.run_reps if args.run else 0,
            'results': list(results.values())}
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, 'w') as f:
        f.write(json.dumps(data, indent=1) + '\n')
    return 0 if all(s == 0 for r in results.values() for s in r['status']) else 1


def fmt_s(v):
    return '%.2f' % v if v < 10 else '%.1f' % v if v < 100 else '%.0f' % v


def cmd_report(args):
    for path in sorted(glob.glob(os.path.join(args.dir, 'compile-*.json'))):
        d = json.load(open(path))
        print('\n%s (%s), compile: the median wall time in seconds, and the peak memory in MB (of %d runs, '
              'one for the largest units); timeout %d s\n' % (d['compiler'], d['cxx'], d['reps'], d['timeout']))
        rows = [r for r in d['results'] if r['kind'] == 'unit']
        configs = sorted({r['config'] for r in rows})
        sizes = sorted({r['operations'] for r in rows})
        present = [s for s in list(SETTINGS) + ['calls'] if any(r['setting'] == s for r in rows)]
        print('| Operations | ' + ' | '.join('%s %s' % (c, s) for c in configs for s in present) + ' |')
        print('|---' * (1 + len(configs) * len(present)) + '|')
        for n in sizes:
            cells = []
            for c in configs:
                for s in present:
                    r = next((x for x in rows if x['operations'] == n and x['config'] == c and x['setting'] == s), None)
                    if r is None:
                        cells.append('')
                    elif any(st != 0 for st in r['status']):
                        cells.append('> %d s' % d['timeout'] if -1 in r['status'] else 'failed')
                    else:
                        w = sorted(r['wall'])[len(r['wall']) // 2]
                        m = sorted(r['peak_mb'])[len(r['peak_mb']) // 2]
                        cells.append('%s s, %d MB' % (fmt_s(w), round(m)))
            print('| %d | ' % n + ' | '.join(cells) + ' |')
        for r in d['results']:
            if r['kind'] == 'definitions':
                w = sorted(r['wall'])[len(r['wall']) // 2]
                print('\nbench/definitions.cpp (the external definitions), %s: %s s, %d MB, object %d bytes'
                      % (r['config'], fmt_s(w), round(sorted(r['peak_mb'])[len(r['peak_mb']) // 2]),
                         r.get('object_bytes', 0)))
        print('\nObject sizes in bytes: ' + '; '.join(
            '%d %s %s: %d' % (r['operations'], r['config'], r['setting'], r.get('object_bytes', 0)) for r in rows))
        if any('run' in r for r in rows):
            print('\nKind %s, run: ns per operation (the minimum over %d samples), and the object in KB\n'
                  % (d.get('kind', 'ball2'), d.get('run_reps', 0)))
            run_settings = [s for s in SETTINGS if s in present]
            print('| Operations | ' + ' | '.join('%s %s' % (c, s) for c in configs for s in run_settings) + ' |')
            print('|---' * (1 + len(configs) * len(run_settings)) + '|')
            for n in sizes:
                cells = []
                for c in configs:
                    for s in run_settings:
                        r = next((x for x in rows if x['operations'] == n and x['config'] == c and x['setting'] == s), None)
                        if r is None or 'run' not in r:
                            cells.append('')
                        else:
                            cells.append('%.3g ns, %d KB%s' % (r['run']['ns_per_op_min'], round(r['object_bytes'] / 1024),
                                                             '' if r['run']['finite'] == n else ' (not finite)'))
                print('| %d | ' % n + ' | '.join(cells) + ' |')
    # run-COMPILER-SETTING-LEVEL[-rN].json: the minimum over the runs of each function's minimum,
    # and the largest ratio of one run's minimum to that, the spread.
    runs, spread = {}, {}
    for path in sorted(glob.glob(os.path.join(args.dir, 'run-*.json'))):
        stem = os.path.basename(path)[len('run-'):-len('.json')]
        parts = stem.split('-')
        if parts[-1].startswith('r') and parts[-1][1:].isdigit():
            parts = parts[:-1]
        compiler, setting, level = '-'.join(parts[:-2]), parts[-2], parts[-1]
        d = json.load(open(path))
        by = runs.setdefault((compiler, level), {}).setdefault(setting, {})
        for r in d['results']:
            if r['name'] in by:
                lo = min(by[r['name']]['ns_min'], r['ns_min'])
                hi = max(by[r['name']]['ns_min'], r['ns_min'])
                spread[(compiler, level, setting, r['name'])] = hi / lo
                by[r['name']] = dict(r, ns_min=lo)
            else:
                by[r['name']] = dict(r)
    if spread:
        worst = max(spread.items(), key=lambda kv: kv[1])
        print('\nThe largest spread between two runs of one function: %.3f (%s)' % (worst[1], ' '.join(worst[0])))
    names = ['api/tp/ball_add_2/op', 'api/tp/ball_mul_2/op', 'api/tp/ball_scale_2/op', 'api/tp/ball_neg_2/op',
             'api/sum/ball_add_2/op', 'api/prod/ball_mul_2/op', 'api/prod/ball_scale_2/op',
             'api/horner/ball_mul_2+ball_add_2/op',
             'api/tp/ball_add_1/op', 'api/tp/ball_mul_1/op', 'api/tp/ball_scale_1/op', 'api/sum/ball_add_1/op',
             'api/prod/ball_mul_1/op', 'api/prod/ball_scale_1/op', 'api/horner/ball_mul_1+ball_add_1/op',
             # The generated cores called directly, which no setting changes: a control.
             'api/tp/ball_add_2/kairn', 'api/sum/ball_add_2/kairn', 'api/prod/ball_mul_2/kairn']
    for (compiler, level), by in sorted(runs.items()):
        print('\n%s %s, run time: the minimum time per operation or step in ns, inline, outlined, external\n'
              % (compiler, level))
        print('| Function | inline | outlined | external | outlined / inline | external / inline |')
        print('|---|---|---|---|---|---|')
        for name in names:
            if not all(name in by.get(s, {}) for s in SETTINGS):
                continue
            v = [by[s][name]['ns_min'] for s in SETTINGS]
            print('| `%s` | %.2f | %.2f | %.2f | %.2f | %.2f |' % (name, v[0], v[1], v[2], v[1] / v[0], v[2] / v[0]))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('source')
    s.add_argument('n', type=int)
    kinds = ['ball2'] + sorted(KINDS) + sorted(IFACE_KINDS) + ['arrays', 'ballvectors']
    s.add_argument('--kind', default='ball2', choices=kinds)
    c = sub.add_parser('compile')
    c.add_argument('--cxx', required=True)
    c.add_argument('--msvc', action='store_true')
    c.add_argument('--flags', default='')
    c.add_argument('--kind', default='ball2', choices=kinds)
    c.add_argument('--cpu', type=int)
    c.add_argument('--run', action='store_true')
    c.add_argument('--run-reps', type=int, default=21)
    c.add_argument('--sizes', default='100,1000,10000')
    c.add_argument('--configs', default='O2,O3')
    c.add_argument('--settings', default='inline,outlined,external')
    c.add_argument('--reps', type=int, default=3)
    c.add_argument('--once-from', type=int, help='compile units of at least this many operations once (default: the largest size)')
    c.add_argument('--timeout', type=int, default=3600)
    c.add_argument('--workdir', required=True)
    c.add_argument('--machine', required=True)
    c.add_argument('--commit', required=True)
    c.add_argument('--date')
    c.add_argument('--json', required=True)
    r = sub.add_parser('report')
    r.add_argument('dir')
    args = p.parse_args()
    return {'source': cmd_source, 'compile': cmd_compile, 'report': cmd_report}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
