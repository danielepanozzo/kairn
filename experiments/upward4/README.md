# A four-limb interval rounded upward (experiment)

**EXPERIMENTAL, NOT VERIFIED, opt-in. No bound stated here is proved.** Since version 0.5.0 its header
is in the library's tree, `include/kairn/experimental/upward4.hpp`, shipped without proofs by the
owner's decision recorded on 2026-11-28 so that clients can experiment while the proofs are worked on:
a file that includes it defines `KAIRN_EXPERIMENTAL_UNVERIFIED` first, nothing else in `include/`
includes it, its exact checks run as ctest tests (label `experimental`), and
[the concept page](../../docs/concepts/experimental.md) describes it. It exists
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
#define KAIRN_EXPERIMENTAL_UNVERIFIED       // the opt-in: no bound of the header is proved
#include <kairn/experimental/upward4.hpp>   // through the CMake targets kairn::upward and kairn::fma
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

## What was measured (2026-11-27, and again 2026-11-28 after the changes below)

**What changed on 2026-11-28** (the reasons in the header's comments):

- **The product's step of level 1 with level 2.** A product of bounds of the sign of the head has a
  positive term in level 2, the product of the second limbs (the square of the second limb, for the
  upper bound of a square). Where it outweighs the level's errors and lies far below the last place of
  level 1, the error of their sum rounded up is not a number of the format; the fast path tested it
  and sent the operation to the exact cold path: 0.7-2.7% of the squares and 0.04-1.3% of the products
  of the checks' classes away from underflow and overflow, 2.1% of the squares on the benchmark's kind
  of operands, at about half a microsecond each (this made the square 1.9 to 3.0 times slower than a
  product). The renormalization now keeps that error exactly as two numbers, $r = c_1 - s_1$ (exact
  when $|c_1| \ge |v|$, tested) and $v$, gathered by one more fast two-sum whose exactness is tested,
  the second of its two terms joining the last step so that no path to the first two limbs gets
  longer. Wherever the earlier version's test passed, the results are the same.
- **The square** chooses its operands by branches on the signs of the first limbs, as the product's form
  `branch` does, instead of computing the lexicographic maximum of its two bounds over the four limbs
  and the lanes by masks for every interval; the maximum is taken only where the two first limbs are
  equal (a symmetric interval). The form without branches on the signs is kept for the measurements
  (`sqr_sel` in `upward4_forms.hpp`).
- **The cold paths' accumulator** uses only the words the terms' range needs (4 to 8 of its 34 for
  quadruples without wide gaps) and builds each limb without a call of the C library: one cold path
  takes about 100-120 ns for a sum and 130-175 ns for a product on the M3 instead of 160-220 and
  180-250.
- **The functions on arrays** (`upward4_arrays.hpp`): `add`, `sub`, `mul` element by element over eight
  plain arrays (the limbs $u_0..u_3$ and $n_0..n_3$, `View`), each function holding its own scope of the
  mode upward, vectorized across elements (four per register on AVX2, two elsewhere) with the type's
  kernels and tests lane by lane, the product's case chosen by masks with the type's pairs (two
  candidates only in packs where an element has both operands containing zero); a pack in which an
  element fails a test, and the remainder, go through the type's operators. Each element is the type's
  result for it, bit for bit (the checks compare them).

`kairn-bench-up-LEVEL` with `KAIRN_BENCH_UPWARD2` and `KAIRN_BENCH_UPWARD4` on, `--reps 31`, three runs
per configuration at `-O2` and three at `-O3`: Apple M3 Max with Apple clang 21 and GCC 16 (not
pinned); AMD EPYC 7452 (Zen 2), one logical CPU of the second socket pinned, its SMT sibling idle, with
GCC 13 and Clang 18. The same operands for every type (the two-limb experiment's intervals of half-width
$2^{-80}$, points). Time per operation, the minimum per run, the range over the six runs of a
configuration (M3 Apple clang | M3 GCC | Zen 2 GCC | Zen 2 Clang); ratios taken within each run. The
"before" of 2026-11-28: the program of the code before the changes, built and run once per level in the
same session, and the three runs per level of 2026-11-27. On the M3 the runs of 2026-11-28 shared the
machine with other work (one-minute load average 2.5 to 3 at their start, each run waiting for it to
fall below 3): code that did not change (the two-limb type, the sums) took up to 10% more time than on
2026-11-27, so there the ratios to the two-limb type within a run are the fairer comparison, given
below.

| ns | 1 limb (`kairn::upward`) | 2 limbs | 4 limbs | 4 limbs / 2 limbs |
|---|---|---|---|---|
| sum, loop | 0.39, 0.39-0.40, 0.60-1.03, 0.60-0.82 | 2.25-2.26, 2.26-2.27, 5.18-5.56, 5.17-5.60 | 11.7-12.8, 12.4-12.5, 27.6-28.2, 27.8-28.4 | 5.2-5.7, 5.5, 5.0-5.4, 5.0-5.4 |
| product, loop | 1.19-1.20, 1.20-1.21, 2.00, 1.98-2.00 | 1.88-1.91, 2.20-2.40, 3.88-4.37, 9.20-9.66 | 12.8, 13.0-13.3, 34.4, 32.5 | 6.7-6.8, 5.6-6.1, 7.9-8.9, 3.4-3.5 |
| sum, chain | 0.78, 0.79-0.82, 1.01-1.02, 1.01 | 8.66-9.38, 9.32-9.37, 10.2-10.3, 10.3-10.8 | 24.2, 23.4-24.0, 28.0-28.6, 26.9-27.2 | 2.6-2.8, 2.5-2.6, 2.7-2.8, 2.5-2.7 |
| product, chain | 4.87-4.96, 4.97-4.98, 3.17-3.43, 3.55-3.77 | 6.32-6.35, 5.50-6.39, 7.59-7.80, 10.2-10.5 | 21.3-21.5, 23.2-23.6, 34.0, 31.3-31.6 | 3.4, 3.7-4.2, 4.4-4.5, 3.0-3.1 |
| 3 by 3 determinant on points | 12.0, 11.7-12.0, 22.1-23.0, 23.2-23.3 | 56.6-56.7, 58.6-60.1, 146-150, 154-156 | 373-389, 406-409, 737-753, 691-695 | 6.6-6.9, 6.8-6.9, 4.9-5.1, 4.4-4.5 |
| Horner of degree 8 | 15.1-15.5, 15.6-16.8, 27.0-27.1, 26.6-27.0 | 84.6-84.7, 82.5-83.5, 143-144, 162 | 355-356, 351-353, 507-508, 472-474 | 4.2, 4.2-4.3, 3.5, 2.9 |

**The square and the product, four limbs** (same runs; the square on X, and on XR whose signs are random
and do not repeat within a call, as the product's):

| | ns | over the product of the same operands |
|---|---|---|
| product, loop | 12.8, 13.0-13.3, 34.4, 32.5 | |
| square, loop | 10.5-10.7, 10.1-10.3, 26.7-26.9, 23.5-23.9 | 0.82-0.84, 0.77-0.78, 0.78, 0.72-0.74 |
| product, random signs | 13.4-13.8, 13.2-14.0, 45.8-46.0, 39.9-40.0 | |
| square, random signs | 12.5-12.6, 10.3-10.7, 32.0-32.1, 28.5-28.9 | 0.91-0.94, 0.74-0.81, 0.70, 0.71-0.72 |
| square without branches on the signs (`sqr_sel`), loop | 13.3, 12.2-12.3, 28.3-28.5, 27.1-28.2 | 1.04, 0.92-0.94, 0.82-0.83, 0.83-0.87 |
| the same, random signs | 13.1-13.2, 12.0-12.1, 28.2-28.4, 27.0-27.8 | 0.95-0.98, 0.86-0.91, 0.62, 0.68-0.70 |

The square is now faster than the product everywhere: 0.72-0.84 of its time in loops, 0.70-0.94 on
random signs (before: 1.9 to 3.0 times). Its form without branches is slower on the usual operands
(1.05-1.26 times the type's) and faster on random signs only on the Zen 2 (0.88-0.98 times; 1.04-1.17 on
the M3), as the product's forms are; the type keeps the branches. The product where both intervals contain zero (two
candidates per bound) is 1.9 to 2.1 times the product of one sign.

**Before and after**, the time of this round over the time of the code before the changes, the range over
every pair of runs of a level (M3 Apple clang | M3 GCC | Zen 2 GCC | Zen 2 Clang):

| | over the code before, run in the same session | over the runs of 2026-11-27 |
|---|---|---|
| sum, loop (unchanged) | 0.89-1.00, 1.00-1.02, 0.99-1.02, 0.98-1.03 | 0.98-1.10, 1.02-1.05, 1.00-1.02, 0.99-1.02 |
| product, loop | 0.68-0.76, 0.62, 0.68-0.69, 0.76-0.77 | 0.73-0.79, 0.60-0.63, 0.68-0.69, 0.77-0.78 |
| product, one sign | 0.67-0.75, 0.58-0.61, 0.68, 0.75-0.78 | 0.71-0.78, 0.59-0.62, 0.68, 0.77-0.79 |
| product, around zero | 0.59-0.68, 0.49-0.50, 0.54-0.55, 0.77-0.79 | 0.63-0.73, 0.50-0.51, 0.54-0.55, 0.77-0.79 |
| product, random signs | 0.83-0.91, 0.79-0.82, 0.90-0.91, 0.92-0.93 | 0.89-0.92, 0.78-0.82, 0.91, 0.91-0.92 |
| square, loop | 0.24-0.29, 0.15-0.16, 0.21, 0.28-0.30 | 0.25-0.31, 0.16, 0.21, 0.28-0.30 |
| product, chain | 0.78-0.84, 0.67-0.69, 0.68-0.69, 0.75-0.77 | 0.82-0.91, 0.68-0.71, 0.68-0.69, 0.76-0.77 |
| product chain, random signs | 0.89-0.94, 0.82-0.86, 0.91-0.92, 0.91 | 0.98-1.02, 0.82-0.90, 0.91, 0.91-0.92 |
| 3 by 3 determinant on points | 0.87-0.95, 0.87-0.89, 0.87-0.89, 0.91-0.92 | 0.93-1.03, 0.88-0.89, 0.83-0.88, 0.91-0.92 |
| Horner of degree 8 | 0.95-0.99, 0.95-1.01, 1.01, 0.99 | 1.08, 0.97-1.01, 1.01, 0.99 |

On the M3 with Apple clang, where the shared machine slowed the unchanged code, the four-limb time over
the two-limb type's in the same run, this round over 2026-11-27: Horner 0.98-0.99, the determinant
0.91-1.01, a product loop 0.71-0.77, a product chain 0.75-0.83, the sum chain 1.00-1.08. Horner did not
gain: its products have the full tails of earlier results, which never took the cold path; a first
version of the change, which added the second error term before the second vector sum (two operations
more on the path to the second limb), made it 3 to 10% slower on the Zen 2, and the version kept is
within 1% there.

**The functions on arrays**, time per element (the same X and Y, 256 elements per call; the loop of the
type's operators over the same eight arrays, element by element inside one scope, is what a client
would write without them; three runs per level after the last change of the header, the functions on
arrays alone with the loops they are measured against):

| ns per element | functions on arrays | loop of the operators over the same arrays | arrays over that loop | arrays over the type's loop on its own layout | 4 limbs over 2 limbs (arrays) |
|---|---|---|---|---|---|
| sum | 14.0-15.9, 11.8-12.3, 13.9, 14.7-14.8 | 15.4-17.4, 14.6-14.7, 34.6-34.7, 29.0 | 0.81-0.92, 0.81-0.84, 0.40, 0.51 | 0.93-1.12, 0.96-0.99, 0.50, 0.53 | 5.1-6.8, 5.1-5.4, 5.7, 5.8-5.9 |
| difference | 13.9-16.0, 11.8-12.4, 13.9-14.0, 14.7-14.8 | 15.8-18.2, 14.9-15.1, 35.5-35.9, 29.8 | 0.81-0.93, 0.79-0.83, 0.39, 0.49-0.50 | 1.03-1.11, 0.93-0.97, 0.49-0.50, 0.51-0.53 | 5.2-5.7, 5.1-5.4, 5.7, 5.9 |
| product | 14.3-16.5, 14.2-15.3, 15.6-16.1, 15.1-17.4 | 15.2-17.5, 15.9-16.1, 40.9-41.3, 34.5-34.9 | 0.86-0.95, 0.89-0.96, 0.38-0.39, 0.43-0.51 | 0.95-1.23, 1.07-1.18, 0.46-0.47, 0.46-0.54 | 3.6-4.3, 4.1-4.5, 4.3-4.4, 3.2-3.8 |

On the Zen 2 (AVX2, four elements per register) the functions take 0.38-0.51 of the loop of the
operators over the same arrays and about half the time of the type's own loop; on the M3 (NEON, two
elements per register, as many as the type's own registers hold) 0.79-0.96 of that loop, and from 0.93
to 1.23 times the type's loop on its own layout: there they save the gathering of each element's limbs,
not arithmetic. GCC 16 at `-O2` kept the header's loops over the four limbs as loops (the arrays of
registers then in memory, the product 1.3 times that loop) until they were marked for complete
unrolling.

There is no default type of four limbs. Against the default `Interval<double, 2>` on the same operands
(same runs), the four-limb round-up type takes 0.75-0.80, 0.80-0.81, 0.57-0.58 and 0.69-0.70 of its
time for the determinant, 0.43-0.72 for Horner and 0.43-0.45 for a product; `Ball<double, 2>` takes
0.88-1.05 of the two-limb round-up type's time for the determinant.

The forms of the product, against `branch` within a run: `table` 1.14-1.22 times in loops (0.91-0.93 on
Zen 2 for random signs, where `branch` mispredicts; 1.13-1.19 on the M3); `sel2` 1.9-2.6 times; `sel4`
(AVX2, Zen 2) 1.23-1.39 times: the 256-bit registers do not pay for the branch-free form. The sloppy sum
takes 0.72-0.79 of the accurate sum's time in loops and chains and 0.82-0.93 in the determinant and
Horner.

The machine code of the loops (x86-64; the widest loop of each function, all its paths): the sum 168-182
instructions, the product 450-482 over all its cases (381-487 before), the square 217-234 (by masks,
`sqr_sel`, 221-250), against 39 and 114-216 for two limbs and 7-18 and 23 for one; nothing is called in
them but the cold paths. The widths, on points (the exact values in integer arithmetic), the same as
before: the four-limb determinant is exact on these points (width 0: its exact value, about 170 bits,
fits in four limbs); Horner of degree 8 has a median width of $6.6\cdot 10^{-63}$ of the value against
$1.5\cdot 10^{-30}$ for two limbs and $1.3\cdot 10^{-14}$ for one.

**How often each operation takes the cold path**, per class of the checks (the share of results; the same
with every compiler and level, the classes' operands differing slightly between compilers), before the
changes (100 000 cases per class, Apple clang `-O2`) and after (2 million per class):

| class | square, before | square, after | product, before | product, after | sum (unchanged) |
|---|---|---|---|---|---|
| as the benchmark (two limbs, $2^{-80}$, $2^{\pm 8}$) | 2.1% | 0 | 0.12% | 0 | 0 |
| points, $2^{\pm 60}$ | 1.5% | 0 | 0.05% | 0 | 30% |
| narrow, $2^{-20}..2^{-200}$ | 1.8% | 0 | 0.10% | 0 | 30% |
| wide (unrelated bounds) | 1.5% | 0 | 0.09% | 0 | 32% |
| around zero | 1.4% | 0 | 0.15% | 0 | 46% |
| zeros (a bound 0, [0, 0]) | 0.72% | 0 | 0.04% | 0 | 7.6-7.8% |
| cancellation (30..210 bits) | 1.9% | 0 | 1.3% | 0 | 38% |
| limbs with gaps | 1.8% | 0 | 0.23% | 0 | 35% |
| magnitudes apart (up to $2^{300}$) | 1.7% | 0 | 0.19% | 0 | 82% |
| results of earlier operations | 2.7% | 0 | 0.50% | 0 | 2.1-2.2% |
| any kind, $2^{\pm 500}$ | 7.3% | 5.6-5.7% | 1.4% | 1.2% | 83% |
| tiny (later limbs underflow) | 100% | 100% | 87% | 87% | 76% |
| huge (near overflow) | 100% | 100% | 73% | 73% | 63% |

What remains for the square and the product is by design: below $2^{-860}$ (tiny values, and the
squares and products of $2^{\pm 500}$ that fall there) and at the overflow threshold the fast path does
not hold. **The sum takes the cold path far more often than the product** wherever the two operands'
magnitudes differ by more than about $2^{53}$ (30% of the pairs of numbers spread over $2^{\pm 60}$,
82-83% over $2^{\pm 300}$ or $2^{\pm 500}$): one of its two lanes then adds a positive head far below the
other, whose error rounded up is not a number of the format, and the test of the heads' two-sum sends
it to the exact path (100-120 ns on the M3 now). The benchmark's operands (magnitudes within $2^{\pm 8}$)
never meet it; a fast path for sums of very different magnitudes was not part of this work.

The excess of a bound over the exact one (units of $u^4 = 2^{-212}$ relative; 2 million cases per class on
the Zen 2 for every program, and on the M3 for the form of the target at `-O2`, fewer for the others),
away from underflow: the accurate sum and the difference at most 2 in every class (cancellations
included); the sloppy sum up to $9\cdot 10^{11}$ at the 99th percentile and $4\cdot 10^{15}$ under
cancellation; the product median 3.0-4.8, 99th percentile 19-37, largest 148; the square median 1.9-2.9,
99th percentile up to 33, largest 93; the product by a number 37. Against the checks of 2026-11-27 with
the same cases (the programs that ran as many), no largest excess grew but that of the measured form
`sel2` (76.5 to 79.2 in one class at `-O3`); the 99th percentiles of the square and of the type's product
grew by at most 0.2 (the cases that took the exact path before now take the fast one), those of `sel2` by
at most 1.8. Below about $2^{-860}$ (the classes of tiny values and of $2^{\pm 500}$) a product's result
has fewer than 212 bits of the format below it, and the excess is that of the best upper quadruple, which
the cold path gives.

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
