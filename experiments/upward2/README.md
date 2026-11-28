# A two-limb interval rounded upward (experiment)

**EXPERIMENTAL, NOT VERIFIED, opt-in. No bound stated here is proved.** Since version 0.5.0 its
header is in the library's tree, `include/kairn/experimental/upward2.hpp` (with
`upward2_arrays.hpp`), shipped without proofs by the owner's decision recorded on 2026-11-28 so
that clients can experiment while the proofs are worked on: a file that includes it defines
`KAIRN_EXPERIMENTAL_UNVERIFIED` first, nothing else in `include/` includes it, its exact checks run
as ctest tests (label `experimental`), and
[the concept page](../../docs/concepts/experimental.md) describes it. It began as a measurement of
what a two-limb ("double double") interval computed under the rounding mode upward gains over
`kairn::Interval<double, 2>`. No MSVC and no Windows were part of this experiment (GCC and Clang on
Linux x86-64, Apple clang and GCC on macOS arm64 only).

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
- **Added on 2026-11-27 with the four-limb experiment** (`experiments/upward4/README.md`), so that the
  two types are used alike: `lower()` and `upper()` (the bounds rounded outward to numbers: the heads,
  exact), `certainly_positive()`, `certainly_negative()`, `contains_zero()`; `width(x)` and `radius(x)`
  rounded up (under the mode upward: the head of the type's sum of the two pairs); `from_upward1` and
  `to_upward1`, the conversions from and to `kairn::upward::Interval<double>` (exact, any mode). They
  are checked by `tests/check.cpp` on every fourth case of every class (the bounds the tightest
  numbers, each predicate its definition on the exact bounds, the width at least the exact one and at
  most one number above its rounding up). The header refuses MSVC with a message.

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

## What was measured (2026-11-27)

`kairn-bench-up-LEVEL` with the units above, `--reps 31`, three runs per configuration at `-O2`
and three at `-O3`: Apple M3 Max with Apple clang 21 and GCC 16; AMD EPYC 7452 (Zen 2), one logical
CPU pinned, its SMT sibling idle, with GCC 13 and Clang 18. Times are the minimum per operation; a
range is over the six runs of a configuration (M3 Apple clang | M3 GCC | Zen 2 GCC | Zen 2 Clang).

| | the type | `Interval<double, 2>` | `Ball<double, 2>` |
|---|---|---|---|
| sum, loop (ns) | 2.07-2.22, 2.23-2.24, 5.15-5.34, 5.15-5.25 | 7.88-7.89, 6.67-7.28, 24.2-24.3, 18.4-18.5 | 1.83, 2.04-2.06, 4.08-4.09, 2.95-2.96 |
| product, loop (ns) | 1.84-1.94, 2.17-2.19, 3.86-3.90, 4.12-4.18 | 27.2-27.3, 28.7-29.3, 77.6-78.3, 72.3-73.6 | 1.40-1.49, 1.52-1.54, 3.71-3.74, 2.35-2.37 |
| 3 by 3 determinant on points (ns) | 51.7-51.8, 56.5-58.6, 146-149, 155 | 454, 459-493, 1270-1277, 989-993 | 49.0-50.3, 47.3-51.5, 147, 139 |
| Horner of degree 8 (ns) | 77.3-77.4, 77.0-78.9, 143-144, 161-162 | 464-465, 413-418, 1162-1170, 834-836 | 63.8, 64.0, 145-146, 142 |

(The product row is the form `branch`, the type's kernel timed under its own name; the operator
itself, the same kernel, measured 5.0 to 9.2 ns between runs of one binary with Clang on Zen 2,
cause not established.) The product's forms against `branch`, the same runs: `table` 1.01-1.14
times slower on the M3 and 1.41-1.48 on Zen 2 in loops, 1.53-1.86 in chains, but 2.4-2.7 times
faster on Zen 2 for independent products of random signs (16384 per call), where `branch`
mispredicts; on the M3 `branch` stayed as fast there. The arrays form: 2.2-2.9 times faster than
Kairn's packed `Interval<double, 2>` kernels for sums, 4.0-6.2 times for products.

The widths, on points (exact values computed in integer arithmetic): the determinant's median
width over the exact value about 6 times smaller than `Interval<double, 2>`'s, Horner's about 10
times. The excess of a bound over the exact one, relative, in $u^2$: sums median 0.46 (default
3.16), largest 6.0 over every class (default up to $10^7$ on cancellation); products median 2.2
(default 4.2), largest 16 (default 8.2): the type's product is tighter in median and up to twice
as loose in the worst case, its second limbs reaching a full step of the first instead of half.

## What is argued, and what is only tested

Every rounding step has its reason in a comment of the header; none is proved. Relied on and not
reproved: the exactness of Fast2Sum's first two operations in a directed mode when the first
operand is the larger in magnitude (Boldo, Graillat, Muller 2017); every result is an upper bound
without it, and only the normalization (hence the product's comparison of candidates) depends on
it. Argued informally, and tested only: that the pair product's final Fast2Sum has its operands in
order for upper-normalized operands, near the underflow threshold included; that the fast path's
check catches every special case (the forms that compute one candidate per lane compute only the
corners they need); the arithmetic of a head at $\pm\Omega$ in the overflow range; that the sum
form `lean` keeps the normalization (it gave the accurate sum's results on every case checked).
The tightness of the bounds is measured, not stated.

## The checks

`tests/check.cpp` (`x2-check-VARIANT-LEVEL`, built by `CMakeLists.txt` here, a project of its own):
for each class of operands (2 million cases per class at `-O2` by default: the benchmark's,
points, narrow and wide intervals, around zero, zeros, tiny values whose second limbs underflow,
huge values near overflow, cancellation, results of earlier operations) and each operation, the
result must contain the exact range (exact integer arithmetic, `tests/exact.hpp`) and be
upper-normalized; the same operands through `Interval<double, 2>` are checked the same way, and the
excess of each bound over the exact one is printed for both, relative, in units of $u^2 = 2^{-106}$.
Then every pair of a list of special values, against the exact range in the extended reals and
against `Interval<double, 2>`'s answer. The functions on arrays are checked on every class too.

Kairn's own tests run this program (`tests/experimental/`, label `experimental`):
`experimental.upward2.check` in the quick tier, on 20 000 cases per class with the build's flags, and
`full.experimental.upward2.VARIANT.LEVEL` in the full tier, on 100 000 per class in each variant of
this project at `-O2` and `-O3`. This project builds the same programs for longer runs:

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
