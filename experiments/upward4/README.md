# A four-limb interval rounded upward (experiment)

**EXPERIMENTAL, NOT VERIFIED, not part of the library. No bound stated here is proved.** Nothing in
`include/` uses it, no test of the library runs it, and no documentation page describes it. It exists
so that a client can try a four-limb ("quad double") interval computed under the rounding mode upward,
and to measure it next to the one-limb and two-limb round-up intervals, before anyone decides whether
to prove it. No MSVC and no Windows were part of this experiment (GCC and Clang on Linux x86-64, Apple
clang and GCC on macOS arm64 only); the header refuses MSVC with a message.

Requires the rounding mode upward set by `kairn::upward::Scope` and the options of
`docs/concepts/upward.md` (GCC and Clang `-frounding-math`), exactly as `kairn/upward.hpp`, whose scopes,
barriers and conventions it reuses, and an FMA: on x86-64 compile with `-mfma` (and `-mavx2` for the
four-lane form of the measurements); without it the header falls back to its form of plain numbers,
whose fused operation is `std::fma` (correct, slow where it is not an instruction).

```cpp
#include <kairn/experimental/upward4.hpp>   // include paths: include/, experiments/upward2/include,
                                            // experiments/upward4/include
namespace u4 = kairn::experimental::upward4;
u4::Interval x(1.0, 2.0), y(0.1);
u4::Interval z;
{
    kairn::upward::Scope scope;              // every operation that rounds runs inside a Scope
    z = x * y - u4::sqr(x) + 3.0;
}
bool positive = z.certainly_positive();     // exact members: any rounding mode
```

## What it is

`kairn::experimental::upward4::Interval` (`include/kairn/experimental/upward4.hpp`), for `double`:

- **Storage.** The interval $[a, b]$ is two *upper quadruples*: $(u_0, u_1, u_2, u_3)$ with
  $u_0 + u_1 + u_2 + u_3 \ge b$ and $(n_0, \dots, n_3)$ with $\sum n_i \ge -a$, so that every rounding
  goes up; in fact the stored values are the bounds: the interval is exactly $[-N, U]$. They sit in
  four registers of two lanes, $R_i = (u_i, n_i)$, lane 0 the upper bound and lane 1 the negated lower
  bound, as in `kairn::upward::Interval<double>` and the two-limb experiment: one four-limb operation
  rounded up computes both bounds. In memory $u_0, n_0, u_1, n_1, u_2, n_2, u_3, n_3$.
- **The invariant**, of each quadruple: every adjacent pair of limbs is upper-normalized,
  $a_i = \mathrm{RU}(a_i + a_{i+1})$ for $i = 0, 1, 2$ (the two-limb invariant on each pair: each later
  limb is not positive and smaller in magnitude than the gap below the limb before); a first limb
  $+\infty$ or $\pm\Omega$ has zero later limbs. It is equivalent to the strong form
  $a_i = \mathrm{RU}(a_i + \dots + a_3)$ (the header's comment gives the induction), which gives: the
  sign of the value from the first limb alone; the order of two quadruples as the lexicographic order
  of their limbs (the product takes the greater of two candidates by it); $a_0$ the tightest number
  above the value and $(a_0, a_1)$ the tightest two-limb upper pair, so that the conversions to fewer
  limbs are truncations.
- **How it is kept, by construction.** Each operation computes four limbs by a fixed sequence of
  two-sums rounded up and then tests, in both lanes, a few things in a few instructions: the invariant
  itself ($\mathrm{RU}(z_i + z_{i+1}) = z_i$, $|z_0| < \Omega$); that the steps whose error could fail to
  be a number of the format had an exact error (below); for a sum, that the result is not more than 48
  bits below the operands (a deep cancellation); for a product, that its first limb is not near
  underflow. Where a test fails, the operation returns its **cold path, which is exact**: the limbs,
  or the products of limbs, added as integers in a fixed-point accumulator of 2176 bits, from which the
  four limbs are taken out each rounded up, the best upper quadruple of the exact value; it also
  handles every special value. So every result satisfies the invariant whatever the fixed sequences
  do; what is argued (and only tested) of the sequences is their tightness and how rarely they leave
  the fast path.
- **The rule that makes every result an upper bound: a term is never dropped, only rounded up.** Every
  operation is rounded up; a two-sum $(s, t)$ rounded up has $s + t \ge a + b$ for every pair; the error
  of a product, one fused operation rounded up, is the exact error when nothing underflows and at least
  it in every case; the products of limbs that are not kept exactly (levels 3 to 6) are computed by
  fused operations rounded up, an upper bound of them whatever their signs; the only terms left out are
  errors of additions rounded up, which are not positive.
- **The register forms**: the two-limb experiment's register layer (`KAIRN_UPWARD2_FORM`): SSE2 with FMA
  on x86-64 (`__m128d`; the measured four-lane product form `sel4` on AVX2), NEON on AArch64
  (`float64x2_t`; every comparison an integer test of the bits, as the two-limb header does, because
  Clang under strict floating point scalarizes vector comparisons of doubles), two plain doubles
  elsewhere.

### The sum

The shape of the *sloppy* addition of quad-double arithmetic (Hida, Li and Bailey, "Algorithms for
Quad-Double Precision Floating Point Arithmetic", ARITH 15, 2001): the limbs of each level added by a
two-sum, each level gathered with the errors of the level above, then a renormalization. Under rounding
upward it differs in three ways:

- Every two-sum is one rounded up (the two-limb experiment's `two_sum`, the smaller of the two orders of
  Fast2Sum's last steps, and `two_sum_nonpos` for operands that are not positive), and every error that
  the published algorithm drops as below its error bound is either kept or, being not positive, rounded
  up instead.
- **The error of a sum rounded up is not always a number of the format**: when the smaller operand is
  positive and more than about half a unit of the larger's last place below it, $\mathrm{RU}(a + b)$
  steps up and the error is $b - \mathrm{ulp}$, a run of ones that may need more than 53 bits; the
  two-sum then returns its rounding up, losing up to $2^{-53}$ of it, which at the heads costs
  $2^{-105}$ of the result, far more than the last of four limbs. In a sum of two upper quadruples every
  later limb and every error is not positive, so only the heads' two-sum can meet it (a sum with a much
  smaller positive number); it tests its exactness (`two_sum_x`: in the order whose first operand is the
  larger, $r = \mathrm{RU}(a - s)$ is exact, so $t$ is the exact error exactly when
  $\mathrm{RU}(t - r) = b$), and the sum takes the exact cold path where the test fails. Before this
  test, 15% of the bounds of sums of numbers spread over $2^{\pm 60}$ lost $2^{-105}$.
- The heads are added to level 1 before the renormalization, so that when they cancel (a difference of
  close numbers) the new head is the small exact sum and what remains is two levels below it.

Two forms: **accurate** (the type's): every error kept down to the fifth level and the renormalization
exact until the last limb, so that the result is within a few units of its own fourth limb's last
place for cancellations up to 48 bits (beyond, the exact cold path); **sloppy**
(`KAIRN_UPWARD4_SUM_SLOPPY`): the fourth limbs' error and the third level's errors rounded up, whose
excess is relative to the operands rather than to the result. Their times and tightness are below.

### The product

The shape of the accurate multiplication of quad-double arithmetic: the products $p_i q_j$ by level
$i + j$; levels 0 to 2 with their errors (one fused operation each, exact when nothing underflows),
level 3 by a chain of fused operations rounded up, and levels 4 to 6, which the published algorithm
drops, also computed by fused operations rounded up (each can be positive: leaving one out would be a
bug). Each level is gathered by two-sums rounded up, and a renormalization ends it.

The inexact errors of sums rounded up meet the product where a positive term of one level is added to
a larger term of the level above. The products of the interval case table pair operands whose tails
have the same sign relative to their heads, so level 1 is never positive and its two-sums are exact;
level 2's $p_1 q_1$ has the sign of the head, so the renormalization's step of levels 1 and 2 and its
first step test their exactness, and the product takes the exact cold path where they fail (about 1
product in 1000 on the measured operands). The square has its own network (14 products instead of 22).

**The interval product** decides the case from the signs of the bounds' first limbs, one quadruple
product per bound except where both intervals contain zero (two candidates per bound, the
lexicographic greater; only the chosen candidate's exactness matters). Forms (`upward4_forms.hpp`):
`branch` (the type's: the cases by branches, every case sharing one product network), `table` (the
lanes of each case by a table of permutations, a branch only to the case of two zeros), `sel2`
(branch-free: two candidates per bound always), `sel4` (AVX2: `sel2`'s two candidates in the four lanes
of 256-bit registers). The forms that compute every candidate also test level 1's two-sums (their
other pairs mix the signs).

### What a client has

Construction from one or two numbers (the cases of `Interval<double, 2>`: the empty set when
`hi < lo`, the whole line for a NaN or the same infinity twice), `empty()`, `whole()`, `from_limbs` and
`to_limbs` (the eight numbers), `upper_limb(i)` and `neg_lower_limb(i)` (exact access); `+`, `-`,
unary `-`, `*`, `sqr`, the same with a `double`; `lower()` and `upper()`, the bounds rounded outward to
numbers (exact: the first limbs); `certainly_positive()`, `certainly_negative()`, `contains_zero()`,
`is_empty()`; `width(x)` and `radius(x)`, rounded up (under the mode upward). Conversions, each
containing its operand: `from_upward2` and `to_upward2` (the two-limb round-up type: exact, any mode;
to it a truncation), `from_upward1` and `to_upward1` (`kairn::upward::Interval<double>`: exact, any
mode), `from_interval` (`Interval<double, 2>`, **under the mode upward**: each bound peeled exactly into
an upper quadruple) and `to_interval` (**under rounding to nearest**: the first two limbs, exactly).
The exact members are the same in every mode and under every option; every operation that rounds needs
a `kairn::upward::Scope`.

The two-limb type (`experiments/upward2`) has the same members added: `lower()`, `upper()`, the three
predicates, `width`, `radius`, `from_upward1`, `to_upward1`.

**Missing**: division, square root, hull, intersection, comparisons beyond the sign predicates, `float`,
MSVC, Windows; the functions on arrays (the second stage of the work, not done); a checked build's
reports (`KAIRN_CHECKS` asserts the mode, as `kairn/upward.hpp`, and checks nothing of the operands).

### Special values

As the two-limb experiment (which follows `Interval<double, 2>`): the empty set (NaN first limbs), the
unbounded intervals (a first limb $+\infty$), $0 \cdot \infty = 0$, an infinite or NaN number operand of
an operation with a number is the whole line; a first limb $-\Omega$ is a finite bound (a value below
$-\Omega$ rounds up to it); a bound above $\Omega$ becomes $+\infty$. Checked on every pair of a list of
38 special intervals (the two-limb experiment's list converted, and quadruples with near-full tails,
subnormal limbs and a first limb next to $\Omega$) against the exact range in the extended reals; the
structure of every answer (empty, which bounds are infinite) compared with the two-limb type's: equal on
all but 79 of 9576 cases, all at the overflow threshold, where four limbs keep a finite bound that two
limbs make infinite (listed by the check program).

## What was measured (2026-11-27)

`kairn-bench-up-LEVEL` with `KAIRN_BENCH_UPWARD2` and `KAIRN_BENCH_UPWARD4` on, `--reps 31`, three runs
per configuration at `-O2` and three at `-O3`: Apple M3 Max with Apple clang 21 and GCC 16 (not
pinned); AMD EPYC 7452 (Zen 2), one logical CPU of the second socket pinned, its SMT sibling idle, with
GCC 13 and Clang 18. The same operands for every type (the two-limb experiment's intervals of half-width
$2^{-80}$, points). Time per operation, the minimum per run, the range over the six runs of a
configuration (M3 Apple clang | M3 GCC | Zen 2 GCC | Zen 2 Clang); ratios taken within each run.

| ns | 1 limb (`kairn::upward`) | 2 limbs | 4 limbs | 4 limbs / 2 limbs |
|---|---|---|---|---|
| sum, loop | 0.37-0.38, 0.38-0.39, 0.59-0.60, 0.60 | 2.21, 2.21-2.22, 5.19-5.51, 5.17-5.34 | 11.6-12.0, 11.9-12.2, 27.6-27.7, 27.8-28.4 | 5.3-5.4, 5.4-5.5, 5.0-5.3, 5.2-5.5 |
| product, loop | 1.17, 1.17-1.18, 1.99-2.00, 1.99-2.00 | 1.84-1.85, 2.16-2.23, 3.88-3.92, 4.35-9.23 | 16.3-17.6, 21.4-21.7, 50.1-50.8, 41.6-42.3 | 8.8-9.5, 9.6-10, 12.9-13.1, 4.5-9.6 |
| sum, chain | 0.71, 0.73-0.79, 1.01-1.19, 1.01 | 8.57, 8.52-8.55, 10.2, 10.2-10.8 | 22.1, 22.0-23.4, 28.0-28.2, 26.9-27.1 | 2.6, 2.6-2.7, 2.7-2.8, 2.5-2.6 |
| product, chain | 4.67-4.87, 4.79-4.87, 3.17-3.54, 3.55-4.05 | 5.77-5.80, 5.64-6.24, 7.61-8.12, 10.0-10.2 | 23.6-25.9, 32.8-34.4, 49.5-49.9, 40.7-41.5 | 4.1-4.5, 5.4-5.9, 6.1-6.6, 4.1 |
| 3 by 3 determinant on points | 11.8, 11.7, 22.5, 23.2-23.4 | 53.6-55.5, 57.3-58.7, 147-150, 154-156 | 379-401, 458-461, 853-890, 754-764 | 6.8-7.2, 7.8-8.0, 5.8-6.0, 4.8-4.9 |
| Horner of degree 8 | 15.1-15.2, 14.4-16.5, 27.0-27.1, 27.0-27.1 | 77.3-78.0, 81.4-81.7, 143-144, 161-162 | 330, 348-362, 502-503, 478 | 4.2-4.3, 4.3-4.5, 3.5, 3.0 |

There is no default type of four limbs. Against the default `Interval<double, 2>` on the same operands
(same runs), the four-limb round-up type takes 0.79-0.84, 0.93-0.94, 0.65-0.68 and 0.76-0.77 of its
time for the determinant, 0.43-0.78 for Horner and 0.56-0.75 for a product; `Ball<double, 2>` takes
0.85-1.05 of the two-limb round-up type's time for the determinant. The product where both intervals
contain zero (two candidates per bound) is 2.0 to 2.5 times the product of one sign. The square measured 1.9 to 3.0 times the product, because on these
operands (short tails, and a square's correlated limbs) 5% of squares fail the exactness test of the
product's levels 1 and 2 and take the exact cold path, which costs about half a microsecond (0.6% of
the products of independent operands do).

The forms of the product, against `branch` within a run: `table` 1.09-1.21 times in loops (0.92-0.94 on
Zen 2 for random signs, where `branch` mispredicts); `sel2` 1.3-3.1 times; `sel4` (AVX2, Zen 2) 1.15-2.2
times: the 256-bit registers do not pay for the branch-free form. The sloppy sum takes 0.72-0.79 of the
accurate sum's time in loops and chains and 0.82-0.91 in the determinant and Horner.

The machine code of the loops: the sum 158-182 instructions (one path; the cold path a call), the
product 381-487 over all its cases (the case of two zeros has two product networks), against 38-39 and
114-245 for two limbs and 7 and 22 for one; nothing is called but the cold paths. The widths, on points
(the exact values in integer arithmetic): the four-limb determinant is exact on these points (width 0:
its exact value, about 170 bits, fits in four limbs); Horner of degree 8 has a median width of
$6.6\cdot 10^{-63}$ of the value against $1.5\cdot 10^{-30}$ for two limbs and $1.3\cdot 10^{-14}$ for one.

The excess of a bound over the exact one (2 million cases per class at `-O2`, units of $u^4 = 2^{-212}$
relative): the accurate sum and the difference at most 2 in every class (cancellations included); the
sloppy sum up to $9\cdot 10^4$ outside cancellation and up to $3\cdot 10^{15}$ under it; the product
median 2-5, 99th percentile 17-37, largest 128; the square largest 91; away from underflow. Below about
$2^{-860}$ (the classes of tiny values and of $2^{\pm 500}$) a product's result has fewer than 212 bits
of the format below it, and the excess is that of the best upper quadruple, which the cold path gives.

## What is argued, and what is only tested

Every rounding step has its reason in a comment of the header; none is proved. Relied on and not
reproved: that Fast2Sum's first two operations are exact in a directed mode when the first operand is
the larger in magnitude (Boldo, Graillat and Muller, "On the robustness of the 2Sum and Fast2Sum
algorithms", ACM TOMS 44(1), 2017: its bibliographic data checked, its text not read here); every result
is an upper bound without it, and only the exactness tests and the tightness depend on it. Argued and
tested: that the invariant holds on every result (it is tested at the end of each fast path, and the
cold path's limbs are by construction the best upper quadruple); that the sign patterns of the case
table keep level 1 of a product non-positive. Tested only: that the fixed sequences are tight (the
excess measured below), how often they leave the fast path, and that the error of a two-sum rounded up
whose smaller operand is not positive is a number of the format (assumed by the tests that are not
made). The accumulator of the cold path is exact integer arithmetic; it is checked against exact
arithmetic, and so is every result.

## The checks

`tests/check.cpp` (`x4-check-VARIANT-LEVEL`, built by `CMakeLists.txt` here): 13 classes of operands
(2 million cases per class at `-O2` by default: the benchmark's, points, narrow and wide intervals,
around zero, zeros, any kind over $2^{\pm 500}$, tiny values whose later limbs underflow, huge values
near overflow, cancellation of 30 to 210 bits, limbs with gaps, magnitudes up to $2^{300}$ apart,
results of earlier operations), each operation (both sums, the difference, the four products, the
square, the operations with a number, the negation, the conversions, the members); every result must
contain the exact range (exact integer arithmetic, `../upward2/tests/exact.hpp`, extended for these
checks) and satisfy the invariant; the excess of each bound over the exact one is printed relative, in
units of $u^4 = 2^{-212}$; the exact cold path is compared with the best quadruple of exact arithmetic.
Then every pair of the special values.

```sh
cmake -S experiments/upward4 -B build-x4 -DCMAKE_BUILD_TYPE=Release [-DCMAKE_CXX_COMPILER=g++]
cmake --build build-x4
build-x4/x4-check-native-O2 2000000      # [cases per class] [seed] [threads]
```

## The benchmark

The units `bench/x4_*.cpp`, added to `kairn-bench-up-LEVEL` by `-DKAIRN_BENCH_UPWARD4=ON` (default off;
needs `-DKAIRN_BENCH_UPWARD2=ON`): the type (backend `x4`, with its forms), the one-limb round-up
interval (`x4u`), `Interval` and `Ball` of one and two limbs (`x4d`) and plain `double` (`x4f`), all on
the two-limb experiment's operands converted outside the timed functions; the two-limb round-up type is
the backend `x2` on the same operands. Every function is checked before it is timed: bit for bit against
the same kernels on operands read through volatile objects, and in exact arithmetic.

```sh
cmake -S . -B build-bench -DCMAKE_BUILD_TYPE=Release -DKAIRN_BUILD_TESTS=OFF -DKAIRN_BUILD_BENCHMARKS=ON \
      -DKAIRN_BENCH_UPWARD2=ON -DKAIRN_BENCH_UPWARD4=ON
cmake --build build-bench --target kairn-bench-up-O2 kairn-bench-up-O3
build-bench/bench/kairn-bench-up-O2 --check-only --filter x4
```
