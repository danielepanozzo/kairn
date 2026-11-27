# A two-limb interval rounded upward (experiment)

**EXPERIMENTAL, NOT VERIFIED, not part of the library. No bound stated here is proved.** Nothing in
`include/` uses it, no test of the library runs it, and no documentation page describes it. It
exists to measure what a two-limb ("double double") interval computed under the rounding mode
upward gains over `kairn::Interval<double, 2>` before anyone decides whether to prove it. No MSVC
and no Windows were part of this experiment (GCC and Clang on Linux x86-64, Apple clang and GCC on
macOS arm64 only).

Requires the rounding mode upward set by `kairn::upward::Scope` and the options of
`docs/concepts/upward.md` (GCC and Clang `-frounding-math`), exactly as `kairn/upward.hpp`, whose
scopes, barriers and conventions it reuses.

## What it is

`kairn::experimental::upward2::Interval` (`include/kairn/experimental/upward2.hpp`), for `double`:

- **Storage.** The interval $[a, b]$ is two *upper pairs*: $(u_h, u_l)$ with $u_h + u_l \ge b$ and
  $(n_h, n_l)$ with $n_h + n_l \ge -a$, so that every rounding goes up. They sit in two registers of
  two lanes, $H = (u_h, n_h)$ and $L = (u_l, n_l)$, lane 0 the upper bound and lane 1 the negated
  lower bound, as in `kairn::upward::Interval<double>`; in memory $u_h, n_h, u_l, n_l$.
- **The invariant** every operation restores: each pair is *upper-normalized*, $h = \mathrm{RU}(h + l)$,
  that is $l \le 0$ and $h + l > \mathrm{pred}(h)$; a head $+\infty$ or $\pm\Omega$ has $l = 0$. Then
  the values of two pairs are ordered as $(h, l)$ lexicographically (the product's maximum relies on
  it), $h \le 0$ exactly when the value is, and $|l| < 2^{-52}|h|$ for a normal $h$.
- **The register forms.** SSE2 with FMA on x86-64 (two `__m128d`; the sum's first stage in one
  256-bit register where the file has AVX2), NEON on AArch64 (two `float64x2_t`; every comparison an
  integer test of the bits, because Clang under strict floating point scalarizes vector comparisons
  of doubles), and four plain doubles elsewhere or where `KAIRN_UPWARD2_FORM` is set to
  `KAIRN_UPWARD2_FORM_NUMBERS`.
- **Operations**: construction from one or two doubles (the cases of `interval_make_2`), the
  conversions from `Interval<double, 2>` (under the mode upward: a Fast2Sum rounded up of each
  bound) and to it (UNDER ROUNDING TO NEAREST: a Fast2Sum rounded to nearest of each pair, exact, so
  the default interval holds the same bounds), `+`, `-`, unary `-`, `*`, the square `sqr`, and the
  same with a `double` operand. Each operation that rounds runs inside a `kairn::upward::Scope`;
  every one has internal linkage and is forced inline; the class has external linkage and only
  exact members.

### The sum

The accurate two-limb sum of Joldes, Muller and Popescu (2017) with every two-sum replaced by one
that is an upper bound under the mode upward without a comparison of magnitudes:
$s = \mathrm{RU}(a + b)$, $t = \min(\mathrm{RU}(\mathrm{RU}(a - s) + b), \mathrm{RU}(\mathrm{RU}(b - s) + a))$.
Both candidates are at least the error $a + b - s$ (each rounding up only increases), and the one
whose first operand is the larger in magnitude is $\mathrm{RU}$ of the error exactly (Fast2Sum's
first two operations are exact in every rounding mode: Boldo, Graillat, Muller 2017, relied on), so
the smaller is $\mathrm{RU}$ of the error: the pair is upper-normalized. The second limbs (not
positive) are ordered by `min` and `max` instead. The branch-free 2Sum of six operations is not
used: under a directed mode it does not give an upper bound of the error in general.

### The product

The leading product $p = \mathrm{RU}(P_h Q_h)$, its error by one fused operation rounded up, the
cross terms by fused operations rounded up, their sum, and a Fast2Sum (whose order $|p| > |w|$
holds for upper-normalized operands when $p$ is normal; below, the sum is exact). Five forms were
built and measured, one per bound and lane of the two registers:

- `eight`: the eight products of bounds (four per lane), the greatest per lane;
- `sel2`: operands selected by the signs of the bounds with blends, two candidates per lane;
- `sel4` (AVX2): `sel2`'s two candidates in one 256-bit register;
- `table`: one candidate per lane, its lanes chosen by a table of permutations indexed by the
  case of the signs (a branch only to the case where both operands contain zero);
- `branch`: the same cases by branches.

Every form takes a fast path when every leading product is finite and below $\Omega$, and otherwise
calls the slow path `mul_special`, the eight candidates with the special cases of
`Interval<double, 2>` (0 times infinity is 0; an infinite factor gives the IEEE product; an empty
operand gives the empty set). The form the type uses is chosen in the header; the others are in
`upward2_forms.hpp`, for the measurements only.

### Special values and where they differ from `Interval<double, 2>`

The empty set (NaN heads), unbounded intervals (a head $+\infty$), 0 times infinity, NaN operands
of the operations with a number (the whole line), as the default type answers them, checked on
every pair of a list of special values. The differences, all at the overflow threshold, each
containing the exact range:

- Under the mode upward a value below $-\Omega$ rounds to $-\Omega$, which is still an upper
  bound of it: a head $-\Omega$ is kept as a finite bound (an upper bound $-\Omega$, a lower bound
  $+\Omega$). Where a product of bounds overflows, `Interval<double, 2>` makes that candidate
  $[-\infty, +\infty]$ and its result the whole line; this type keeps the finite bound on the other
  side (for example $[-\Omega, -\Omega] \cdot [-2, -2]$ gives $[\Omega, +\infty]$ here and the whole
  line there).
- `Interval<double, 2>` can hold a finite bound just beyond $\Omega$ (a first limb $\Omega$ and a
  positive second one); an upper-normalized pair cannot, and such a bound becomes infinite here
  (for example the upper bound of $[1, \Omega] + [0, 2]$: $+\infty$ here, $\Omega + 2$ there), also
  in the conversion from the default type.
- A bound whose head is $\pm\Omega$ loses its second limb (at most one step of the last limb).

## The checks

`tests/check.cpp` (`x2-check-VARIANT-LEVEL`, built by `CMakeLists.txt` here, a project of its own):
for each class of operands (2 million cases per class at `-O2` by default: the benchmark's,
points, narrow and wide intervals, around zero, zeros, tiny values whose second limbs underflow,
huge values near overflow, cancellation, results of earlier operations) and each operation, the
result must contain the exact range (exact integer arithmetic, `tests/exact.hpp`) and be
upper-normalized; the same operands through `Interval<double, 2>` are checked the same way, and the
excess of each bound over the exact one is printed for both, relative, in units of $u^2 = 2^{-106}$.
Then every pair of a list of special values, against the exact range in the extended reals and
against `Interval<double, 2>`'s answer.

```sh
cmake -S experiments/upward2 -B build-x2 -DCMAKE_BUILD_TYPE=Release [-DCMAKE_CXX_COMPILER=g++]
cmake --build build-x2
build-x2/x2-check-native-O2 2000000      # [cases per class] [seed] [threads]
```

## The benchmark

The units `bench/x2_*.cpp`, added to `kairn-bench-up-LEVEL` by `-DKAIRN_BENCH_UPWARD2=ON` (default
off): the type (backend `x2`) with every form of the product and of the sum, on the benchmark's
operands, on operands of one sign, around zero and of random signs; chains; Horner on intervals and
on points; the 3 by 3 determinant of coordinate differences on points; the earlier scalar prototype
(`x2p`); `Interval<double, 2>` and `Ball<double, 2>` on the new operands (`x2d`); the one-limb
round-up interval on the same points (`x2u`). Every function is checked before it is timed: bit for
bit against the same kernels on operands read through volatile objects, and in exact arithmetic.

```sh
cmake -S . -B build-bench -DCMAKE_BUILD_TYPE=Release -DKAIRN_BUILD_TESTS=OFF -DKAIRN_BUILD_BENCHMARKS=ON \
      -DKAIRN_BENCH_UPWARD2=ON
cmake --build build-bench --target kairn-bench-up-O2 kairn-bench-up-O3
build-bench/bench/kairn-bench-up-O2 --check-only --filter x2
```
