# Two and four limbs rounded upward (experimental)

!!! warning "EXPERIMENTAL, NOT VERIFIED: no bound stated by these headers is proved"

    Kairn's rule is that every bound it ships is machine-checked. The headers on this page are the
    stated exception: by the owner's decision recorded on 2026-11-28
    ([decisions log](../developer/design/phase0/decisions.md#decisions-log)) they ship **without
    proofs**, so that clients can experiment with them while the proofs are worked on. What protects
    a user meanwhile is the banner at the top of each header, the opt-in that each file which
    includes one must write, and the exact checks of their tests, which are tests, not proofs.
    Their interface may change or disappear in any version. GCC and Clang only: MSVC is refused, and
    no Windows build was ever tested. Nothing in `kairn/kairn.hpp` or `kairn/upward.hpp` includes
    them, no claim of `gen/claims.json` and no page of the [reference](../reference/index.md) covers
    them, and `kairn::unverified` does not apply to them.

`kairn/experimental/upward2.hpp` and `kairn/experimental/upward4.hpp` hold an interval of two limbs
and an interval of four limbs of `double`, `kairn::experimental::upward2::Interval` and
`kairn::experimental::upward4::Interval`, computed under the rounding mode upward as the
[round-up interval](upward.md) of one limb is: each bound is a sum of two or four `double`s (about
106 or 212 bits), the upper bound and the lower bound negated, so that every rounding goes the same
way and one operation on registers of two lanes computes both bounds. They are the multi-limb
counterparts of `kairn::upward::Interval<double>`, and use its scopes, its options and its
conventions. `kairn/experimental/upward2_arrays.hpp` has the sum, the difference and the product
of two-limb intervals element by element on four plain arrays, each function holding its own scope,
as the round-up interval's functions on arrays do.
<!-- After the merge with the four-limb work: kairn/experimental/upward4_arrays.hpp, the same for
four limbs; name it here and in "What a program can do" once it is in include/kairn/experimental/. -->

They are not the numbers of three and four limbs of [Milestone 4](../developer/design/phase0/plan.md#milestones):
those are `Expansion`, `Ball` and `Interval` of three and four limbs under rounding to nearest,
generated and proved as the rest of the library is, and they are not built. These two types are
written by hand, round upward, are intervals only, and have no proof.

## How to use them

The rules of the [round-up interval](upward.md#what-the-program-guarantees) hold as they are: every
file that includes a header is compiled with `-frounding-math`, which the CMake target
`kairn::upward` adds; every operation that rounds runs inside a `kairn::upward::Scope`; the mode
is never set by hand. They also need hardware fused multiply-add, which `kairn::fma` gives on
x86-64 (on AArch64 every compiler has it): without it the headers fall back to a form of plain
numbers whose fused operation is `std::fma`, right and slow. On x86-64 with AVX2 (`-mavx2`) the
functions on arrays use 256-bit registers. And the file defines `KAIRN_EXPERIMENTAL_UNVERIFIED`
before it includes the first experimental header, or the header stops the build:

```cpp
--8<-- "docs/examples/cpp/concepts_experimental.cpp:opt_in"
```

The headers are installed with the library, and the targets are the round-up interval's; there is
no target of their own, so that the opt-in stays in the program's code:

```cmake
--8<-- "tests/consume/experimental/CMakeLists.txt:12:13"
```

A typical use is the one of the round-up interval, a filter that decides a sign, where one limb
cannot. The value below is exactly $2^{-156}$, but on the way the cube
$x^3 = 1 + 3 \cdot 2^{-52} + 3 \cdot 2^{-104} + 2^{-156}$ needs 157 bits, which one and two limbs
cannot hold, so their intervals contain zero; four limbs hold it, and give the value exactly.

```cpp
--8<-- "docs/examples/cpp/concepts_experimental.cpp:sign"
```

```cpp
--8<-- "docs/examples/cpp/concepts_experimental.cpp:sign_call"
```

```text
--8<-- "docs/examples/cpp/concepts_experimental.txt:1:3"
```

The conversions from and to the default `Interval<double, 2>` keep the set, and each needs its
mode: from it under the mode upward, to it under rounding to nearest, outside the scope.

```cpp
--8<-- "docs/examples/cpp/concepts_experimental.cpp:convert"
```

```text
--8<-- "docs/examples/cpp/concepts_experimental.txt:4:5"
```

The program is
[`docs/examples/cpp/concepts_experimental.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/concepts_experimental.cpp),
which ctest builds with `kairn::upward` and `kairn::fma` and whose output it compares with the text
on this page each time (`experimental.example`).

## What a program can do with them, and what it cannot yet

Both types have: construction from one or two `double`s, with the cases of `Interval<double, 2>`
(the empty set when `hi < lo`, the whole line for a NaN or the same infinity twice); `empty()`,
`whole()`, `is_empty()`; `from_limbs` and `to_limbs`, the stored numbers; `+`, `-`, unary `-`,
`*`, `sqr`, and the same with a `double` operand; `lower()` and `upper()`, the bounds rounded
outward to `double`s; `certainly_positive()`, `certainly_negative()` and `contains_zero()`, the
predicates of a filter; `width(x)` and `radius(x)`, rounded up, under the mode upward; the
conversions `from_upward1` and `to_upward1` from and to `kairn::upward::Interval<double>`
(exact, in any mode), `from_interval` from `Interval<double, 2>` (under the mode upward) and
`to_interval` to it (under rounding to nearest). The four-limb type also has `from_upward2` and
`to_upward2` (exact, in any mode), and `upper_limb(i)` and `neg_lower_limb(i)`. The members of the
classes are exact and the same in every mode; every function that rounds needs a scope, except the
functions on arrays, which hold their own. Those of two limbs, `kairn::experimental::upward2::add`,
`sub` and `mul`, take views `View<double>` and `View<const double>` of four plain arrays (the
upper pairs' heads and tails, then the negated lower pairs'), each element a state as an operation
returns it; the views have the same length, and the result is written into an operand's arrays or
into arrays that overlap neither. They are called by their qualified names.

They do not have: division, square root, hull, intersection, comparisons beyond the three sign
predicates, `float` limbs, `constexpr`, MSVC or any Windows build, and a checked build's reports on
operands (`KAIRN_CHECKS` asserts the mode, and checks nothing else).

**Special values** follow `Interval<double, 2>`: the empty set, unbounded intervals,
$0 \cdot \infty = 0$, and an infinite or NaN number operand of an operation with a number is the
whole line. They differ at the overflow threshold only, always containing the exact range: a bound
$-\Omega$, the largest finite number negated, stays finite where the default type would make the
result the whole line, and a bound just above $\Omega$ becomes infinite. The two READMEs list each
difference:
[two limbs](https://github.com/danielepanozzo/kairn/blob/main/experiments/upward2/README.md),
[four limbs](https://github.com/danielepanozzo/kairn/blob/main/experiments/upward4/README.md).

## How they work, in short

**Two limbs.** Each bound is an *upper pair* $(h, l)$ with $h + l$ at least the bound, kept
*upper-normalized*: $h = \mathrm{RU}(h + l)$, so that $l \le 0$ and $h$ alone is the tightest
`double` above the bound, which gives the sign of the bound from $h$ and the order of two pairs as
the lexicographic order of $(h, l)$. The sum is the accurate double-word sum of Joldes, Muller and
Popescu (2017) with every two-sum replaced by one that is an upper bound under the mode upward; the
product decides the case from the signs of the heads and computes one pair product per bound, or
two and the greater where both intervals contain zero.

**Four limbs.** Each bound is an *upper quadruple*, every adjacent pair of limbs upper-normalized.
Each operation computes the four limbs by a fixed sequence of two-sums rounded up, following the
shape of the quad-double algorithms of Hida, Li and Bailey (2001), with one rule: **a term is never
dropped, only rounded up**. It then tests its own result in a few instructions (the invariant, and
the exactness of the few steps whose error might not be a number); where a test fails it returns an
exact result instead, computed as an integer in a fixed-point accumulator and rounded up limb by
limb. So every result keeps the invariant by construction, and what is argued but only tested is
how tight the fast sequences are and how rarely they leave the fast path.

Every rounding step of both headers has its reason in a comment; the experiments' READMEs say what
is argued, what is relied on from the literature, and what is only tested.

## What is tested

The exact checks of each type, the programs of the experiments (`experiments/upward2/tests/`,
`experiments/upward4/tests/`), run as ctest tests with the label `experimental`. For each class of
operands (the benchmark's, points, narrow and wide intervals, around zero, zeros, values whose later
limbs underflow, values near overflow, heavy cancellation, limbs with gaps, results of earlier
operations) and for each operation, every result must contain the exact range, computed in exact
integer arithmetic, and keep the type's invariant; then every pair of a list of special values,
against the exact range in the extended reals. A result that does not contain the exact range fails
the test.

- The quick tier runs them with the build's flags on 20 000 cases per class
  (`experimental.upward2.check`, `experimental.upward4.check`), with a test that each header
  refuses to compile without the opt-in (`experimental.opt_in.*`), a test that reads the tree
  (`experimental.headers`: every experimental header starts with the banner and the guard, nothing
  of the library includes one, no claim and no reference page names them), the example above, and
  a consumer project, through `add_subdirectory` and through `find_package`.
- The full tier runs them in every variant (the target's form of the registers, the form of plain
  numbers, a checked build, and on x86-64 FMA without AVX2) at `-O2` and `-O3`, on 100 000 cases per
  class.
- The CI runs both tiers on Linux x86-64 and arm64 with GCC and Clang and on macOS arm64 with Apple
  clang. With MSVC and clang-cl the tests are not registered.

Before they came to the library the experiments ran the same checks on 2 million cases per class,
with Apple clang 21 and GCC 16 on an Apple M3 and GCC 13 and Clang 18 on an x86-64 machine, at
`-O2` and `-O3` ([Testing](../developer/testing.md#the-experimental-headers)).

**What none of this shows**: that a result contains the exact range on operands the checks did not
try. Tests sample; a proof covers every operand. The tightness of the bounds is measured, never
stated as a bound.

## What is machine-checked so far

Only part of the two-limb type, and none of the four-limb one. A proof probe, in Rocq, under
`experiments/upward2/proofs/`, proves in the library's model of real numbers (every precision from
a small minimum, with gradual underflow, and **without overflow, infinities or NaN**):

- **the sum**: the two-sums rounded up (each result an upper bound of the exact sum and
  upper-normalized, for any operands, with no condition on their magnitudes, and the exactness of
  Fast2Sum's first two operations in a directed mode), the type's sum (an upper pair of the exact
  sum, upper-normalized, with an excess of at most $64 u^2 |x + y| + 16\eta$), and the sum with a
  finite number;
- **the product**: the order of upper-normalized pairs, the pair product (an upper bound,
  upper-normalized, with an excess of at most $40 u^2 |PQ| + 8\eta$), and the interval product's
  fast path in all nine cases of the signs, which contains the exact range.

What it does not cover: the special values and the slow path of the product, overflow, the signed
zeros, the product by a number, the square, the conversions, `width` and `radius`, the functions on
arrays, and the four-limb type entirely. Its definitions are transcribed from the
header by hand, operation by operation, not generated from one description as the library's proofs
are, and nothing checks that the two stay the same (the line numbers its comments give are those of
the header before it moved here; the operations it transcribes have not changed since). **The CI
does not build it**; its files are kept so that the proofs can continue from them, and its
`Makefile` says how to build it with the library's proofs.

## How fast they are

<!-- The table and the four-limb numbers of the paragraph after it are copied from
experiments/upward4/README.md ("What was measured"), and the two-limb comparisons from
experiments/upward2/README.md: refresh them together when those READMEs' measurements change. -->

Measured with the benchmark program of the round-up interval (`kairn-bench-up-LEVEL` with
`KAIRN_BENCH_UPWARD2` and `KAIRN_BENCH_UPWARD4` on, both off by default), on 2026-11-27, `--reps 31`,
three runs per configuration at `-O2` and three at `-O3`: an Apple M3 Max with Apple clang 21 and
GCC 16 (not pinned), and an AMD EPYC 7452 (Zen 2), one logical CPU pinned with its SMT sibling idle,
with GCC 13 and Clang 18. The same operands for every type (intervals of half-width $2^{-80}$, and
points); the time per operation in nanoseconds, the minimum of each run, as the range over the six
runs of a configuration, in the order M3 Apple clang | M3 GCC | Zen 2 GCC | Zen 2 Clang; the ratio
taken within each run:

| ns | 1 limb (`kairn::upward`) | 2 limbs | 4 limbs | 4 limbs / 2 limbs |
|---|---|---|---|---|
| sum, loop | 0.37-0.38, 0.38-0.39, 0.59-0.60, 0.60 | 2.21, 2.21-2.22, 5.19-5.51, 5.17-5.34 | 11.6-12.0, 11.9-12.2, 27.6-27.7, 27.8-28.4 | 5.3-5.4, 5.4-5.5, 5.0-5.3, 5.2-5.5 |
| product, loop | 1.17, 1.17-1.18, 1.99-2.00, 1.99-2.00 | 1.84-1.85, 2.16-2.23, 3.88-3.92, 4.35-9.23 | 16.3-17.6, 21.4-21.7, 50.1-50.8, 41.6-42.3 | 8.8-9.5, 9.6-10, 12.9-13.1, 4.5-9.6 |
| sum, chain | 0.71, 0.73-0.79, 1.01-1.19, 1.01 | 8.57, 8.52-8.55, 10.2, 10.2-10.8 | 22.1, 22.0-23.4, 28.0-28.2, 26.9-27.1 | 2.6, 2.6-2.7, 2.7-2.8, 2.5-2.6 |
| product, chain | 4.67-4.87, 4.79-4.87, 3.17-3.54, 3.55-4.05 | 5.77-5.80, 5.64-6.24, 7.61-8.12, 10.0-10.2 | 23.6-25.9, 32.8-34.4, 49.5-49.9, 40.7-41.5 | 4.1-4.5, 5.4-5.9, 6.1-6.6, 4.1 |
| 3 by 3 determinant on points | 11.8, 11.7, 22.5, 23.2-23.4 | 53.6-55.5, 57.3-58.7, 147-150, 154-156 | 379-401, 458-461, 853-890, 754-764 | 6.8-7.2, 7.8-8.0, 5.8-6.0, 4.8-4.9 |
| Horner of degree 8 | 15.1-15.2, 14.4-16.5, 27.0-27.1, 27.0-27.1 | 77.3-78.0, 81.4-81.7, 143-144, 161-162 | 330, 348-362, 502-503, 478 | 4.2-4.3, 4.3-4.5, 3.5, 3.0 |

In the two-limb experiment's own runs, the two-limb type was 6.4 to 8.8 times faster than the
default `Interval<double, 2>` on the determinant, and its median width over the exact value about 6
times smaller there (10 times on Horner); in the runs above, `Ball<double, 2>` took 0.85 to 1.05 of
its time on the determinant. There is no default type of four limbs to compare with; against
`Interval<double, 2>`, the four-limb type took 0.65 to 0.94 of its time on the determinant, and its
determinant on these points was exact. The experiments' READMEs have the other measurements: the
forms of the product that were rejected, the tightness of each operation in units of $u^2$ and
$u^4$, and how often the four-limb operations take their exact path.
