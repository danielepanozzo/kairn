# Getting started

**Kairn is in development, and nothing in it should be relied on yet.** Milestone 1 is complete
([report](../developer/results/milestone1.md)): the first public headers exist, for numbers of one and two limbs of type `float` or
`double` and for balls around them. The claims of all their operations have checked proofs in a
model of arithmetic where nothing overflows, and at overflow and for infinities and NaN they
return results like those of `float` and `double` (balls: the whole line, or the empty set), which
is proved in a model of IEEE 754; [What holds today](guarantees.md) has the details and what is
not proved yet. Milestone 2 is in progress: its first public functions, the building blocks on
`T`, the exact scaling of a ball, a ball from a constant and the signs of a ball, are in version
0.2.0 of the development line. This page shows how to write a first program, choose the limb type
and the number of limbs, write constants such as 1/10, use the building blocks, build and test the
repository, use the CMake package, read what Kairn's checks report when something is wrong, and
build this site.

## A first program

Include `kairn/kairn.hpp`, and call `kairn::self_test()` once at startup: it checks, with the
flags your program was compiled with, that the arithmetic behaves as Kairn's proofs assume, and
says why if it does not.

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:include"

--8<-- "docs/examples/cpp/first_steps.cpp:self_test"
```

`kairn::Expansion<double, 2>` stores a value as the exact sum of two `double`s, its *limbs*: about
106 significant bits instead of 53. Its operations have proved error bounds, which `kairn::traits`
exports as constants:

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:expansion"
```

A `kairn::Ball` is a set: a center and a radius, and every operation returns a ball that contains
every result of the operation on points of its operands:

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:ball"
```

An operation whose proof is not checked compiles only with the marker `kairn::unverified` on one
of its operands; [What holds today](guarantees.md#proved-and-unverified) says which operations
those are.

The whole program is
[`docs/examples/cpp/first_steps.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/first_steps.cpp);
ctest builds and runs it (`api.example.first_steps`), and it checks the values it prints. To build
your own program, link `kairn::kairn` and `kairn::fma` ([Use it from CMake](#use-it-from-cmake)).
Next, the tutorial [Accurate sums and dot products](../tutorials/accurate-sums.md) puts these
types to work, and the [reference](../reference/index.md) has a page for every operation.

## Choosing T and k

A k-number has two parameters: the limb type `T`, `float` or `double`, and the number of limbs
$k$, 1 or 2 in this version. Together they fix how many significant bits a value has, and from
which magnitude it has all of them: the last limb is a number of `T`, and for small values it
falls into the subnormal range of `T`, where it has fewer bits of its own.
`kairn::traits<X>::precision` is the number of bits:

```cpp
--8<-- "docs/examples/cpp/choosing.cpp:alias"
```

| Type | Bits (`traits<X>::precision`) | Decimal digits | All bits for $\lvert x\rvert \ge$ | Largest finite value |
|---|---|---|---|---|
| `double`, `Expansion<double, 1>` | 53 | 16.0 | $2^{-1022} \approx 2.2\cdot10^{-308}$ | $\approx 1.8\cdot10^{308}$ |
| `Expansion<double, 2>` | 106 | 31.9 | $2^{-969} \approx 2.0\cdot10^{-292}$ | $\approx 1.8\cdot10^{308}$ |
| `float`, `Expansion<float, 1>` | 24 | 7.2 | $2^{-126} \approx 1.2\cdot10^{-38}$ | $\approx 3.4\cdot10^{38}$ |
| `Expansion<float, 2>` | 48 | 14.4 | $2^{-102} \approx 2.0\cdot10^{-31}$ | $\approx 3.4\cdot10^{38}$ |

These are the rows for one and two limbs of the table in
[Numbers](../developer/design/phase0/numbers.md#precision-depends-on-magnitude), which also covers
more limbs and the arithmetic of GPUs, both planned for later. The magnitude from which a type has
all its bits is $2^{kp - 1}\eta$, where $p$ is the precision of `T` and $\eta$ its smallest
subnormal number; for one limb it is the smallest normal number of `T`. Code templated on its
number type reads the limb type, the number of limbs and the precision from `kairn::traits`, which
answers the same questions for `float`, `double` and every `Expansion`:

```cpp
--8<-- "docs/examples/cpp/choosing.cpp:threshold"
```

Below that magnitude a value has one bit fewer per binade: between $2^E$ and $2^{E+1}$ it has
$E - \log_2\eta + 1$ bits, so `Expansion<float, 2>` has 33 bits at $10^{-35}$, which lies between
$2^{-117}$ and $2^{-116}$. Every error bound accounts for it with its absolute term, a multiple of
$\eta$ next to the relative one ([How to read a page](../reference/reading.md#notation)). Here an exact
product needs 47 bits, which `Expansion<float, 2>` has at $2^{-4}$ and not at $2^{-104}$:

```cpp
--8<-- "docs/examples/cpp/choosing.cpp:below"
```

The program,
[`docs/examples/cpp/choosing.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/choosing.cpp),
checks these results and every number of the table but the decimal digits and the largest values
against `kairn::traits` and `std::numeric_limits` (ctest: `api.example.choosing`). At the top of
the range a k-number overflows where `T` does: each operation's page in the
[reference](../reference/index.md) says up to which magnitudes its result is finite.

**Which to choose.**

- **`double` limbs.** They have all their bits over almost the whole range of `double`. On the CPU,
  which is all Kairn has in this version, `float` limbs give nothing in exchange for their
  narrower range: in the [benchmarks](../developer/results/bench-milestone1.md#5-float-limbs) they
  saved little or no time over `double` limbs, and with Clang 18 they cost more; and
  `Expansion<float, 2>` has fewer bits than a plain `double`. `float` limbs are meant for GPUs,
  where `float` arithmetic is much faster than `double`; Kairn has no GPU code yet
  ([Plan](../developer/design/phase0/plan.md#milestones)).
- **Two limbs** when the 53 bits of `double` are not enough, as in sums that cancel (the
  [tutorial](../tutorials/accurate-sums.md)). An operation on two limbs is a short sequence of
  operations of `T`, listed on its reference page, and takes several times as long as one
  operation of `T`; the [benchmarks](../developer/results/bench-milestone1.md) give the ratios per
  machine and compiler, and the tutorial's [What it costs](../tutorials/accurate-sums.md#what-it-costs)
  those of its loops.
- **One limb**, `Expansion<T, 1>`, is `T` with Kairn's interface: each operation is the IEEE 754
  operation of `T`, and the test `api.k1.zero_cost` finds the same instructions as for `T`, or
  fewer, in the loops it compiles, with the exceptions that [One limb](guarantees.md#one-limb)
  lists. It lets code written for k-numbers run at the precision of `T`, and `Ball<T, 1>` gives a
  guaranteed bound at that precision.
- **A ball**, `Ball<T, k>`, when the program needs a bound on the error rather than only a small
  error: the radius is that bound. In a chain of dependent operations the radius costs almost
  nothing; in loops of independent operations it costs more
  ([Benchmarks](../developer/results/bench-milestone1.md#3-the-cost-of-a-ball-operation)).
- **An interval**, `Interval<T, k>`, when the program computes with sets that are wide or
  unbounded, or needs bounds that are the tightest of `T` ([below](#intervals-and-balls)).

Three and four limbs, and a $k$ chosen at run time, are planned for later milestones
([Plan](../developer/design/phase0/plan.md#milestones)).

## Intervals and balls

Both are sets of real numbers that contain every exact result of the computation that made them,
and both answer for the empty set and the whole line; they differ in how they store the set, and
so in what they are good at
([One enclosure interface](../developer/design/milestone2.md#one-enclosure-interface)).

- **`Interval<T, k>`** stores two bounds. It can be a half-line, $[0, +\infty]$, which a ball cannot
  (a ball that is unbounded is the whole line). For one limb its bounds are the exact roundings
  outward of the exact ones: a sum or a difference is the tightest interval of `T` that contains
  the exact range, and a product too, but very close to zero. It is the type for a set that is wide
  compared with its numbers, such as the domain of a search, and for one limb, where every
  operation costs a few directed roundings.
- **`Ball<T, k>`** stores a center of $k$ limbs and one radius of `T`. It is the type for a value
  known to within a small error, such as the result of a long computation on data with rounding
  errors: the center carries the value at the precision of $k$ limbs, and the radius, which needs
  only a few bits, is computed in `T`. From two limbs on it is the cheap enclosure: a sum of balls
  of two limbs is about 23 rounded operations, a sum of intervals of two limbs about 56, and the
  bounds of an interval of two limbs are not the tightest numbers of two limbs but within about
  $8u^2$ of them ([Bounds of two limbs](../developer/design/milestone2.md#bounds-of-two-limbs)).
- **Neither** removes the *dependency problem*: an expression in which a variable appears twice,
  such as $x^2 - 2x$, is evaluated as if each occurrence could take its own value, and the result
  can be much wider than the exact range. Rewriting the expression and splitting the set are the
  remedies; the [tutorial on intervals](../tutorials/intervals.md) shows both, and how a ball fares
  on the same problem.

`Ball<T, 1>(X)` and `Interval<T, 1>(B)` convert one into the other, each widening the set (so
both are explicit), and `Ball<T, 2>::from_interval(lo, hi)` makes a ball of two limbs whose center
is the exact midpoint of two numbers of `T`. What each function guarantees is in
[What holds today](guarantees.md#intervals).

## Constants from fractions

A constant such as 1/10 or 1/3 is not a `double`, nor the sum of two. `kairn::rational<X>(num,
den)` gives the fraction of two 64-bit integers as a number of type `X`, with a bound of its
error and whether it is exact, in constant expressions and at run time:

```cpp
--8<-- "docs/examples/cpp/constants.cpp:rational"
```

It computes with integers only, so the result is the same, bit for bit, at compile time and at
run time, under every rounding mode. Its result is specified exactly and tested for equality with
the oracle, but, being integer code written by hand rather than a generated kernel, it is not
machine-checked; each constant computed at compile time is checked against its specification
before it compiles ([Constants from fractions](../reference/rational.md)). The program is
[`docs/examples/cpp/constants.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/constants.cpp);
ctest builds and runs it (`api.example.constants`).

## Building blocks

The functions of `float` and `double` that Kairn's operations are made of are public too
(`kairn/blocks.hpp`, which `kairn/kairn.hpp` includes): for a program's own tests of exactness,
its own radius arithmetic, and bounds rounded down or up without changing the rounding mode. Each
is one call of a generated, proved kernel, whose [reference page](../reference/index.md#building-blocks-on-t)
states it, on infinities and NaN too.

| Function | Gives | `constexpr` | Rounds |
|---|---|---|---|
| `two_sum(a, b)` | `SumAndError<T>`: `sum` $= \mathrm{RN}(a + b)$ and `error`, with `sum + error` $= a + b$ exactly | yes, the same values | yes |
| `fast_two_sum(a, b)` | the same in three operations instead of six, for $\lvert a\rvert \ge \lvert b\rvert$ (a debug build checks it) | yes, the same values | yes |
| `two_prod(a, b)` | `ProductAndError<T>`: `product` $= \mathrm{RN}(ab)$ and `error`, with `product + error` $= ab$ exactly when $ab = 0$ or $\lvert ab\rvert \ge 2^{-969}$ for `double` ($2^{-102}$ for `float`), within $\tfrac12\eta$ of it otherwise | yes, by Dekker's product: the same values when exact | yes |
| `next_up(a)`, `next_down(a)` | the next number of `T` above and below, IEEE 754's `nextUp` and `nextDown`, on every value (`next_up(-inf)` is $-\Omega$) | yes, the same bits | no |
| `radd(a, b)`, `rmul(a, b)` | for $a, b \ge 0$, an upper bound of $a + b$ and of $ab$, at most $\tfrac32$ gaps of `T` above it | yes, the same bits | yes |
| `add_down`, `add_up`, `sub_down`, `sub_up` | $a \pm b$ rounded down or up: the nearest number of `T` on that side, exactly | yes, the same values | yes |
| `mul_down(a, b)`, `mul_up(a, b)` | a bound of $ab$ on that side: the exact directed rounding when $ab = 0$ or $\lvert ab\rvert \ge 2^{-969}$, and at most one number of `T` beyond it otherwise | no | yes |

"The same values" means that constant evaluation gives the result of run time, but for the sign of
a zero; "rounds" that the function computes with operations rounded to nearest, so that a debug
build checks the rounding mode before it ([below](#when-a-check-of-a-build-without-ndebug-fails)):
the directed bounds give, under rounding to nearest, what rounding down or up would.
`mul_down` and `mul_up` are not usable in constant expressions: their statement is about the
fused product, whose error term constant evaluation computes otherwise
([Building blocks on T](../developer/design/milestone2.md#building-blocks-on-t)). A test of
exactness, and the exact sum of two doubles as a two-limb number:

```cpp
--8<-- "docs/examples/cpp/building_blocks.cpp:exact"
```

`SumAndError<T>` and `ProductAndError<T>` have two named members rather than being a pair, since
which of the two is the rounded result matters; they are aggregates, so
`auto [s, e] = kairn::two_sum(a, b);` works too. The sum and its error term are a normalized
pair, so the exact sum of two numbers is the two-limb number they make: the conversion of a
`SumAndError` to `Expansion<T, 2>` is explicit, and valid exactly when both members are finite.
They are for finite operands whose sum does not overflow, with one exception for `two_sum`, a
second operand of $\pm\Omega$ (the largest finite number), where the error term can be a NaN
although the sum is finite; a debug build reports a pair that is not canonical. The radius of a
product, in a program's own arithmetic of radii:

```cpp
--8<-- "docs/examples/cpp/building_blocks.cpp:radius"
```

And bounds of a sum and of a product, with the rounding mode left as it is:

```cpp
--8<-- "docs/examples/cpp/building_blocks.cpp:bounds"
```

They are function templates of namespace `kairn` with both operands of the same type: write
`kairn::next_up(a)`. A function of the program's own with the same name is not hidden, and
argument-dependent lookup does not find Kairn's for an operand of type `double` or `float`.

**The exact scaling of a ball.** `kairn::ldexp(X, n)` and `kairn::half(X)` multiply every member
of a ball by $2^n$, exactly when nothing underflows: when each limb of the center and the radius
of the result is zero or above the smallest normal number, the result is $2^n X$ itself, with
nothing added to the radius. A subdivision that halves its balls can count on that. Below, the
ball stays an enclosure and its radius grows by what was lost. `X * 0.5`, the scaling by a `T`,
also covers the rounding of a product that need not be exact, so its radius grows even for a power
of two:

```cpp
--8<-- "docs/examples/cpp/building_blocks.cpp:scaling"
```

**A ball from a constant.** `Ball<T, k>(q)`, for `q` a result of `kairn::rational` or
`kairn::integer` of $k$ limbs, is the ball of center `q.value` and radius `q.error`, which
contains the fraction. It is how a program multiplies a ball by $1/s$, for an integer $s$, and
keeps an enclosure, until Kairn has a division:

```cpp
--8<-- "docs/examples/cpp/building_blocks.cpp:rational"
```

**The sign of a ball.** `X.certainly_positive()`, `X.certainly_negative()` and
`X.certainly_zero()` say whether every member of a ball is positive, negative, or zero, from one
exact comparison of the radius with the center; each is false for the empty set and for the whole
line, so test `X.is_empty()` first where that matters:

```cpp
--8<-- "docs/examples/cpp/building_blocks.cpp:signs"
```

The program is
[`docs/examples/cpp/building_blocks.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/building_blocks.cpp);
ctest builds and runs it (`api.example.building_blocks`). A program that needs these functions,
or `KAIRN_ENCLOSURE_CODE`, can require the version that has them:

```cpp
--8<-- "docs/examples/cpp/building_blocks.cpp:version"
```

The first test is in a group of its own because a version before 0.2.0 has no such macro, and an
undefined function-like macro in an `#if` does not compile; `KAIRN_VERSION`, which every version
defines, can also be compared directly (`#if KAIRN_VERSION >= 200`).

## What you need

- CMake 3.21 or later and a C++20 compiler. A project that only uses the library, through
  `add_subdirectory`, `FetchContent` or `find_package`, needs CMake 3.18; Kairn's own tests need
  3.21.
- On x86-64, a CPU with FMA (Intel Haswell, AMD Piledriver or later) to run the kernels and their
  tests ([Hardware FMA](#hardware-fma)), and with AVX2 too (Intel Haswell, AMD Excavator or
  later) for the tests of the packed kernels.
- Python 3, for the generator's and the oracle's tests and for building the site. Building Kairn
  as a client will never need it ([Architecture](../developer/architecture.md#layout-and-ownership)).

## Configure, build and test

From the repository root:

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Built on its own, Kairn defaults to a `Release` build, because its contraction tests check what an
optimizing compiler does. With a multi-configuration generator (Visual Studio, Xcode), name the
configuration instead: `cmake --build build --config Release` and `ctest --test-dir build -C
Release --output-on-failure`. Add `--parallel N` to both of the last two commands to use N cores;
with four, the tests took 31 to 41 seconds on an Apple M3 Max, 47 to 54 on 16 threads of a 2019
x86-64 server and 63 to 71 on a Windows machine with 8 logical processors, and without, 133
seconds on the first and 189 on the second
([Time](../developer/testing.md#the-tools-tests-leave-the-quick-tier)).

These commands run the quick tier, the tests of the library with your compiler and flags, and
ctest says so when it starts and when it ends. The full tier, everything that left the quick tier
to keep it quick (the same cross-checks on ten times the cases, the enumerations of small formats
by the generator's interpreter, the own tests of the generator, the oracle and the other tools),
is one more command after the same build:

```sh
ctest --test-dir build/tests/full --output-on-failure
```

With `--parallel 4` it took five to six minutes on the Mac, nine and a half on the Linux machine
and eleven on the Windows machine. [Testing](../developer/testing.md#the-full-tier) lists its
tests, and the CI runs both tiers on every push and pull request.

The tests of the quick tier:

| Test | Checks |
|---|---|
| `kairn-gen.check` | `python3 gen/kairn-gen check`: every committed generated file is what the generator writes. |
| `kairn-oracle.claims` | `python3 oracle/kairn-oracle check --claims-only`: the oracle can read every claim in `gen/claims.json`. |
| `docs.reference.check` | `python3 docs/tools/reference.py --check`: the reference pages of this site are what the script writes from the claims and the stored results. |
| `crosscheck.compiled.*` | Each kernel, compiled with the build's compiler and flags, scalar and packed (NEON on AArch64, AVX2 on x86-64, one operand per lane), and again under each contraction setting that matters to the compiler: every one of these builds on the same random `binary64` and `binary32` operands, judged by the oracle against the kernel's claims. |
| `objcode.*` | The fused multiply-adds and plain multiplications in the object code of every kernel, compiled with the build's compiler in a few configurations of its flags, are those its description asks for; a textbook `a * b + c` fails that check where the compiler fuses it. With the operations of `Ball` outlined and external ([below](#compile-time-and-the-operations-of-ball)), each is a call, and the function it calls has the fused operations of its kernel. |
| `regression.cases` | The stored cases that once found a problem or came closest to a claim (`tests/regression/cases.txt`), through every compiled runner, the generator's interpreter and every public form of their kernels, judged by the oracle. |
| `consume.add_subdirectory` | A CMake project that adds Kairn with `add_subdirectory` and links `kairn::kairn` and `kairn::fma` builds, compiles as C++20, and runs a kernel; Kairn prints no line when it is configured there, and its `cmake --install` installs nothing of Kairn's unless `KAIRN_INSTALL` is on. |
| `consume.install` | `cmake --install` of the build tree into a prefix inside the build directory, with the license in it as `share/licenses/kairn/LICENSE`. |
| `consume.find_package` | A CMake project that finds that installed copy with `find_package(kairn)` builds, compiles as C++20, and runs a kernel. |
| `api.oracle.*` | Each public operation, computed through the constructors, operators and functions of `kairn/kairn.hpp`, on random `binary64` and `binary32` operands (infinities, NaN, the empty set and the whole line included, for the kernels that have them), judged by the oracle against the claims of the kernel it calls; built with the build's flags and with contraction forced on. |
| `api.oracle.coverage` | Every kernel of `gen/claims.json` is called by some public operation, or is a building block of others, or is on a short list of entry kernels not public yet, each with its reason. |
| `api.constexpr` | `static_assert`s of every operation usable in constant evaluation, infinities, NaN and the states of a ball included, and the same results at run time. |
| `api.environment` | `kairn::environment_ok()` and `kairn::self_test()` pass, and each detects a changed rounding mode and flush-to-zero. |
| `api.flags.debug.*` | Built as a debug build (CMake's `Debug` flags, no `NDEBUG`): `kairn::self_test()` passes, and so do the constant expressions of `api.constexpr`. |
| `api.checks.*` | With `KAIRN_CHECKS` 1, in a debug build and in an optimized one: under each directed rounding mode and under flush to zero `kairn::environment_ok()` is false and every function that rounds, and every constructor that checks its operands, stops the program with the environment's message; every [function that does not round](#when-a-check-of-a-build-without-ndebug-fails) gives, under each directed rounding mode, the same bits as to nearest without a report, and stops it under flush to zero if it checks anything; every operand that is not canonical and every negative radius stops it; what is canonical passes; with a `KAIRN_ENVIRONMENT_FAILURE` that returns, every function goes on ([Testing](../developer/testing.md#the-checks-of-a-debug-build)). |
| `api.shadow` | A program with a global variable of every name of a parameter or a local variable of Kairn's headers, calling every public operation, compiles with the compiler's strictest warnings about hidden declarations as errors ([Testing](../developer/testing.md#the-programs-names)). |
| `api.platform_macros` | The headers compile and work after a platform header that defines `min`, `max`, `small`, `near`, `far`, `hyper` and `interface` as macros: `<windows.h>` itself on Windows, without `NOMINMAX`, and the same macros defined by the test on every platform. |
| `api.self_test.unsafe.*` | With Clang, programs built with flags that break Kairn and define no macro; `kairn::self_test()` must report a failure. |
| `api.reject.*` | What must not compile: the flags `config.hpp` rejects; a value of `KAIRN_ENCLOSURE_CODE` that is not one of its three; each kind of operation and constructor written without the marker while its kernel is UNVERIFIED (against a copy of the headers in which every kernel is); and an operation whose kernel alone is UNVERIFIED, which must not compile through a conversion to another kernel; with `KAIRN_CHECKS`, a constant expression given an operand the checks refuse; `mul_down` and `mul_up` in a constant expression. |
| `api.link.external.*` | With the operations of `Ball` external, a program whose file of definitions was compiled with another `KAIRN_CHECKS` or another setting, or is missing, does not link; the same program with matching settings links and runs. |
| `api.boundary.*` | A product the program computes and passes into an operation (`x + a * b`, a constructor, `from_limbs`, a ball's center or radius) gives, bit for bit, the result of the same operation on the rounded product, under each contraction setting; `api.boundary.unguarded.*` checks, against a copy of the headers without the generated guard, that the compilers that fuse across statements do change it. |
| `api.k1.zero_cost` | The instructions emitted for loops and single operations over `Expansion<double, 1>` against the same code over `double`; with MSVC, also that none of them has a stack-cookie check. |
| `api.example.*` | The examples of this site, which check their own output; the tutorial's, under each contraction setting, against the output its page shows. |

`ctest -L api` runs only the tests of the public interface. [Testing](../developer/testing.md)
explains the cross-checks, how to run one by hand, and how to rerun one failing case. The entry points of the
[Architecture](../developer/architecture.md#layout-and-ownership) page, the cross-checks and the
full tier are registered only if Python 3 is found, and each entry point only if its script exists
when CMake runs; configuring prints which were registered, and how many tests each tier has. The
consumer checks build with the same generator and compiler as the main build.

Tests are on by default when Kairn is the top-level project and off when another project adds it;
the option `KAIRN_BUILD_TESTS` overrides that. A project that adds Kairn with its tests on gets the
quick tier only, the tests of the library with that project's compiler and flags, which its own
`ctest` runs beside its tests; the tools' own tests are in the full tier, which is registered only
when Kairn is the top-level project.

## Use it from CMake

`kairn::kairn` is an `INTERFACE` target: it adds `include/` to the include path and requires
C++20, and there is nothing to compile. Its headers today:

| Header | Content |
|---|---|
| `kairn/kairn.hpp` | All of the following. |
| `kairn/expansion.hpp` | `kairn::Expansion<T, 1>` and `kairn::Expansion<T, 2>`, `T` = `float` or `double`, and their operations. |
| `kairn/ball.hpp` | `kairn::Ball<T, 1>` and `kairn::Ball<T, 2>`. |
| `kairn/blocks.hpp` | The [building blocks](#building-blocks) on `T`: `two_sum`, `fast_two_sum`, `two_prod`, `next_up`, `next_down`, `radd`, `rmul`, the sums and products rounded down and up. |
| `kairn/rational.hpp` | `kairn::rational`, `kairn::integer` and `kairn::Constant` ([above](#constants-from-fractions)). |
| `kairn/traits.hpp` | `kairn::traits<X>`: limb type, number of limbs, precision, and the error constants of the proved operations. |
| `kairn/environment.hpp` | `kairn::self_test()` and `kairn::environment_ok()`. |
| `kairn/config.hpp` | The checks of the compiler's flags, the marker `kairn::unverified`, and the macros `KAIRN_CHECKS`, `KAIRN_ENVIRONMENT_FAILURE`, `KAIRN_K1_CONTRACT`, `KAIRN_ENCLOSURE_CODE`. |
| `kairn/version.hpp` | `KAIRN_VERSION_MAJOR`, `KAIRN_VERSION_MINOR`, `KAIRN_VERSION_PATCH`, `KAIRN_VERSION_STRING` and `KAIRN_VERSION` (configuring fails if they disagree with the version in `CMakeLists.txt`), and `KAIRN_VERSION_AT_LEAST(major, minor, patch)` ([above](#building-blocks)). |
| `kairn/definitions.hpp` | The definitions of the operations of `Ball`, for one file of a program built with `KAIRN_ENCLOSURE_CODE_EXTERNAL` ([below](#compile-time-and-the-operations-of-ball)); nothing in the other settings. |
| `kairn/ball_operations.hpp`, `kairn/gen/` | The operations of `Ball` that `ball.hpp` and `definitions.hpp` include, and the generated kernels and data the headers above use; not an interface to call directly. |

A project can add the source tree (directly, or through `FetchContent`), as the
`consume.add_subdirectory` test does, with `KAIRN_SOURCE_DIR` the path of the checkout:

```cmake
--8<-- "tests/consume/add_subdirectory/CMakeLists.txt"
```

Or it can install Kairn first, with `cmake --install build --prefix PREFIX`, which installs the
headers, the package under `share/cmake/kairn` and the license as `share/licenses/kairn/LICENSE`
(`share` is `CMAKE_INSTALL_DATADIR`), and find it with `PREFIX` in `CMAKE_PREFIX_PATH`, as the
`consume.find_package` test does:

```cmake
--8<-- "tests/consume/find_package/CMakeLists.txt"
```

The installed package accepts a request for a version with the same major and minor number that is
not newer than itself. The development line of Milestone 2 is 0.2.0.

Added with `add_subdirectory` or `FetchContent`, Kairn keeps to itself: it adds no install rule,
so that `cmake --install` of the project installs the project's files and not Kairn's, unless the
project sets the option `KAIRN_INSTALL` to `ON` (its default is `ON` only when Kairn is the
top-level project), and its configuration prints nothing at the default log level: the line about
the option of `kairn::fma` ([Hardware FMA](#hardware-fma)) is at the `VERBOSE` level there
(`cmake --log-level=VERBOSE`), as it is for a package found with `find_package`. The test
`consume.add_subdirectory` checks both.

## Compile time and the operations of Ball

Every operation of one and two limbs is forced inline into the function that calls it, which is
what makes it fast. A function with thousands of ball operations, a loop unrolled by templates for
example, then becomes one very large function, which the compiler takes long to compile and a lot
of memory to compile. `KAIRN_ENCLOSURE_CODE`, defined the same way before Kairn is included in
every file of a program (or with `target_compile_definitions` on every target), says where the code
of the operations of `Ball` that round (`+`, `-`, `*`, the scaling by a `T`, and `ldexp` and
`half`, one and two limbs) and of the arithmetic of `Interval` (`+`, `-`, `*`, one and two limbs)
is:

| Setting | The operations of `Ball` and `Interval` | When |
|---|---|---|
| `KAIRN_ENCLOSURE_CODE_INLINE`, the default | forced inline into each call, as before | the operations are in loops and chains whose speed matters, and the functions are of ordinary size |
| `KAIRN_ENCLOSURE_CODE_OUTLINED` | ordinary functions that the compiler is asked not to inline: each file compiles each operation once, whatever the number of its calls | a file with many ball operations in a few functions compiles too slowly or uses too much memory, and the build stays as simple as it is; with Clang it saves as much as external |
| `KAIRN_ENCLOSURE_CODE_EXTERNAL` | declared only; one file of the program defines them | the same, when many files use balls and the program would rather compile the operations once in all; with GCC, which compiled an external unit 1.1 to 2.4 times as fast as an outlined one |

```cpp
// In every file of the program, or with -DKAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_EXTERNAL:
#define KAIRN_ENCLOSURE_CODE KAIRN_ENCLOSURE_CODE_EXTERNAL
#include <kairn/kairn.hpp>

// And in exactly one file, compiled with the same settings as the others:
#include <kairn/definitions.hpp>
```

With CMake, the definition can go on the targets
(`target_compile_definitions(app PRIVATE KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_EXTERNAL)`), and the
one file into one of them. `kairn::kairn` builds nothing: the file is the program's own, so that it
is compiled with the program's compiler and flags, `KAIRN_CHECKS` and `KAIRN_ENVIRONMENT_FAILURE`
included, which a library built by Kairn could not know. In the other settings
`kairn/definitions.hpp` defines nothing, so the file can stay.

The three settings compute the same bits: each operation's code is the same, its generated kernel
inside it, and the tests check that every public form gives the same bytes in each
([Testing](../developer/testing.md#the-full-tier)). The negation of a ball and the constructors, a
few instructions each, stay inline in every setting, and so does everything of `Expansion`; so do
the steps of `ldexp`, each a call of the scaling by a power of two of `T`, and of an interval
everything but its arithmetic (the constructors, the negation, the hull and the intersection, the
midpoint, the radius, the split, the conversions, all `constexpr`). An operation that is
outlined is still usable wherever it was (none of these is usable in constant expressions yet,
`ldexp` and `half` of a ball and the sum and the difference of intervals of one limb included,
although their kernels are); an external one cannot be evaluated at compile time. The kernel of the
product of intervals of two limbs, some four hundred operations, is an ordinary inline function in
every setting: the inline setting inlines the product's checks and the call, and the compiler
decides whether to inline the kernel (Apple clang 21 at `-O2` calls it); the outlined and external
settings make the product a function of its own, which calls or inlines the kernel. A call costs time at run
time where the operations are short and many. Measured on an Apple M3 Max ([Compile times and other
costs, Milestone 2](../developer/results/costs-milestone2.md)): a function of 10 000 operations of
`Ball<double, 2>` compiled 6.8 to 7.1 times faster with Apple clang 21 outlined or external (5
seconds instead of 33 to 35), 1.5 to 2.1 times with GCC 16 (44 to 132 seconds instead of 74 to
212), in a third to a fifth of the memory; at run time each operation took 2.4 to 6.2 nanoseconds
more in a chain of dependent operations (a chain of two-limb sums 1.5 times as long with Apple
clang, 1.8 times with GCC), and 1.05 to 1.9 times as long in a loop of independent ones.

If the files of a program disagree: a file compiled inline and one compiled outlined each get what
they asked for, since the outlined operations are functions of a namespace of their own; a file
compiled external whose definitions are missing, or were compiled with another setting or another
`KAIRN_CHECKS`, does not link, with an undefined `kairn::detail::external::...` (or
`external_checked::...` when `KAIRN_CHECKS` is 1); with MSVC and clang-cl a program whose files
disagree in any way does not link (LNK2038, "mismatch detected for 'kairn_enclosure_code'"). Any
other value of the macro does not compile: `KAIRN_ENCLOSURE_CODE must be KAIRN_ENCLOSURE_CODE_INLINE,
KAIRN_ENCLOSURE_CODE_OUTLINED or KAIRN_ENCLOSURE_CODE_EXTERNAL`.

## Hardware FMA

Every kernel assumes that a fused multiply-add is one rounding done by the hardware. On x86-64 the
headers therefore refuse to compile unless the compiler targets a CPU with FMA, with the error
"Kairn needs hardware FMA". AArch64 always has it.

`kairn::kairn` does not choose the instruction set for you: which CPUs a program runs on is the
program's decision, and an option carried by `kairn::kairn` would apply to every file of every
target that links it. Either compile for such a CPU yourself (`-march=x86-64-v3` or `-mfma` with
GCC and Clang, `/arch:AVX2` with MSVC and clang-cl), or also link `kairn::fma`, as the examples
above do. `kairn::fma` adds that option for the compiler of your project, or nothing when your
flags already enable FMA or the target needs no option; configuring Kairn on its own prints a line
when it adds one, and as a subproject or a package found with `find_package` it writes that line at
the `VERBOSE` log level only. Kairn's own tests link it.

## Troubleshooting

Kairn's results depend on every floating-point operation being done as written, rounded to
nearest, with subnormal numbers kept. It checks what it can when a file is compiled, and the rest
when the program runs. Each entry below is a message that Kairn prints, what causes it, and what to
do. The code of this section is part of
[`docs/examples/cpp/troubleshooting.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/troubleshooting.cpp),
which changes the environment on purpose and checks that Kairn reports it with the messages quoted
here (ctest: `api.example.troubleshooting`).

### When a file is compiled

Including `kairn/kairn.hpp` stops the compilation with an `#error` whose text names the cause.
The flags are those of the file that includes Kairn: unless the entry says otherwise, remove the
flag from the files that include it.

- `Kairn needs C++20 (-std=c++20, /std:c++20)`. Compile as C++20 or later; linking `kairn::kairn`
  in CMake requires it.
- `Kairn does not work with -ffast-math, -Ofast or -ffp-model=fast: they let the compiler rewrite
  the error-free transformations that every Kairn kernel is made of`. The flags that define
  `__FAST_MATH__`: `-ffast-math` and `-Ofast` with GCC and Clang, and Clang's
  `-ffp-model=aggressive`. Clang 18 defines it for `-ffp-model=fast` too; Apple clang 21 does
  not, and then the self-test reports that flag ([below](#when-the-program-runs)).
- `Kairn does not work with -ffinite-math-only: Kairn's results can be infinite or NaN, and its
  tests for them would be removed`.
- With GCC, which announces each of these flags with a macro:
  `Kairn does not work with -fassociative-math or -funsafe-math-optimizations: (a + b) - a is not b in floating point, and Kairn's kernels depend on it`,
  `Kairn does not work with -fno-signed-zeros: it lets the compiler turn the product fma(a, b, +0) back into a * b, which can then be contracted`
  and
  `Kairn does not work with -freciprocal-math: it changes the value of quotients`.
- With MSVC: `Kairn does not work with /fp:fast: it lets the compiler rewrite the error-free
  transformations that every Kairn kernel is made of; use /fp:precise (the default), /fp:strict or
  /fp:contract`.
- `Kairn needs every float and double operation rounded to its own type (FLT_EVAL_METHOD == 0): no
  x87 evaluation, no -ffp-eval-method other than source`. Code for 32-bit x86 that evaluates in
  the x87 registers, or Clang's `-ffp-eval-method` set to anything but `source` (`=double` gives
  it). Use SSE2 arithmetic instead of x87, and leave `-ffp-eval-method` at `source`.
- `Kairn needs hardware FMA: compile for an x86 CPU that has it (-mfma, -march=haswell or later)`
  with GCC and Clang (clang-cl included), `Kairn needs hardware FMA: compile with /arch:AVX2 or
  later` with MSVC. Link `kairn::fma`, or compile for such a CPU yourself
  ([Hardware FMA](#hardware-fma)).
- `Kairn: no FMA primitive has been chosen and measured for MSVC on this architecture`. MSVC
  compiling for a target other than x86, such as ARM64, which this version does not support.

### When the program runs

`kairn::self_test()` computes, with the flags of the file that calls it, results that IEEE 754
fixes exactly, then runs every kernel on fixed operands. It returns a `kairn::Status`: `ok()` and
`message()`, the first check that failed, and for a failed kernel `kernel`, its name and limb type.
Print both:

```cpp
--8<-- "docs/examples/cpp/troubleshooting.cpp:report"
```

Its messages, and what causes them:

- `rounding is not to nearest with ties to even`. The rounding mode was changed, by the program
  or a library (an interval library may round upward or downward), and not restored. Restore it
  before calling Kairn (below).
- `subnormal results are flushed to zero` and `subnormal operands are read as zero`. Flush to zero
  is on, which some programs and libraries set for speed. Code compiled or linked with
  `-ffast-math` or `-Ofast` can set it when the program starts, for every part of the program, so
  it can be on in a program whose files including Kairn passed its `#error` checks. Find what sets
  it, or clear it before calling Kairn (below).
- `the compiler reassociates floating-point sums (-fassociative-math)` and
  `TwoSum is not error-free: the compiler rewrites floating-point sums`. Flags that let the compiler
  rearrange sums, which Clang does not announce with a macro. With Apple clang 21 the first message
  came from `-fassociative-math -fno-signed-zeros -fno-trapping-math`, from
  `-funsafe-math-optimizations` and from `-ffp-model=fast`.
- `fma(a, b, +0) is not exact: the compiler ignores the signs of zeros (-fno-signed-zeros)`,
  `quotients are not correctly rounded (-freciprocal-math)` and
  `the square root is not correctly rounded`. A flag that changes those results, for the file that
  calls the self-test.
- `fma is not a fused multiply-add`. A fused multiply-add that is not one rounding: compiled or run
  where it is computed in two steps.
- `a generated kernel computed a result other than the exact one on fixed operands`, with `kernel`
  such as `split (double)`. With Apple clang 21 on AArch64, `-fno-signed-zeros` with
  `-ffp-contract=fast` gives `split (double)`: the compiler turns the kernels' fused products back
  into plain ones and contracts them. With flags that Kairn accepts, it is a fault of the compiler
  or of Kairn: please report it as an [issue](https://github.com/danielepanozzo/kairn/issues),
  with the compiler, its version, the flags and the kernel.

For the messages that name a flag, remove it from the files that include Kairn. The self-test
sees a flag only through a result it changes: with Apple clang 21, `-freciprocal-math` alone and
`-fno-signed-zeros` alone changed none, and the self-test passed. Kairn does not support those
flags either way.

`kairn::environment_ok()` reads the control register (MXCSR on x86-64, FPCR on AArch64) and says
whether the rounding mode and flush to zero are as Kairn assumes. Kairn never changes them; a
program that may find them changed, after a call into a library, can check and put them back:

```cpp
--8<-- "docs/examples/cpp/troubleshooting.cpp:check"
```

with

```cpp
--8<-- "docs/examples/cpp/troubleshooting.cpp:restore"
```

`EXAMPLE_X86` and `EXAMPLE_AARCH64` say which processor the program is compiled for, and
`read_fpcr` and `write_fpcr` read and write FPCR with the builtins of GCC and Clang; all four are
defined in the example.

### When a check of a build without `NDEBUG` fails

In a build without `NDEBUG`, or with `KAIRN_CHECKS` defined to 1 (the same in every file of the
program), every operation, and every constructor that is given limbs or a center (`from_limbs`,
the constructors of `Ball`), checks first the environment and then its operands. A failed check
prints a line on the standard error and stops the program with `std::abort()`; in a wrong
environment the line is the environment's, whatever the operands. In constant evaluation only the
operands are checked, and an operand that fails makes the expression not a constant expression,
which the compiler reports.

**Functions that do not round.** A function whose result is the same under every rounding mode
does not check the rounding mode, so that a program that computes under a directed rounding mode
may call it without switching back to rounding to nearest. It still checks the rest of the
environment (flush to zero, under which a comparison reads a subnormal number as zero), and its
operands, but only under rounding to nearest where that check rounds itself (the test of a
canonical pair, $x_0 + x_1 = x_0$). They are:

| Functions | Why the rounding mode cannot change them |
|---|---|
| `-x` and `kairn::abs(x)`, one and two limbs | a sign bit; for two limbs a comparison and a select |
| `<`, `<=`, `>`, `>=`, `==`, `!=`, one and two limbs, with a `T` or a one-limb number on either side | comparisons of limbs |
| `kairn::to_nearest`, `kairn::to_down`, `kairn::to_up`, `kairn::abs_upper`, one and two limbs, and the narrowing `Expansion<T, 1>(x)` | a limb; or a comparison, a step of the bit pattern and a select |
| `-X` for a `Ball` | sign bits, and the radius as it is |
| `X.certainly_positive()`, `X.certainly_negative()`, `X.certainly_zero()` for a `Ball` | comparisons of the radius with the center |
| `Ball<T, 1>(a)`, `Ball<T, 1>(c)`, `Ball<T, 1>(c, r)`, `Ball<T, 1>(q)`, `Ball<T, 2>(a)`: the constructors of a ball from a `T`, a number of one limb or a constant of one limb | their only rounded operations are the guards `a + 0`, whose value is `a` under every rounding mode; only the sign of a zero can differ, which Kairn leaves unspecified anyway |
| `Expansion<T, 2>(r)` for the result `r` of `two_sum` or `fast_two_sum` | the guards, as above, and a test of the pair that compares and does not round |
| `-X`, `X.hull(Y)`, `X.intersection(Y)` for an `Interval`, and `X.lower_as<T>()`, `X.upper_as<T>()` of an interval of two limbs | sign bits, comparisons and selects of bounds; a bound rounded down or up to `T` as `to_down` and `to_up` round it |
| the constructors of an `Interval`: from two bounds or a point of one limb, from a `T` of two limbs, from numbers of two limbs | the guards, as above; for numbers of two limbs comparisons and selects |
| `kairn::next_up`, `kairn::next_down` | integer operations on the bit pattern, which no state of the environment changes: they check nothing at all |
| `kairn::sign`, `kairn::isfinite`, `kairn::is_normalized` of one limb, `X.center()`, `X.radius()`, `X.midpoint()`, `X.is_finite()`, `X.is_whole()`, `X.is_empty()`, `Ball::empty()`, `Ball::whole()`, `Interval()`, `Interval::empty()`, `Interval::whole()`, `X.lower()` and `X.upper()` of an interval, and `X.lower_as<T>()`, `X.upper_as<T>()` of an interval of one limb, the constants of `kairn::traits`, `kairn::rational`; the constructors of two limbs from a `T` or a one-limb number and `from_limbs_unchecked` (their guard, as above) | tests of bit patterns, stored values and data, integer arithmetic; these check nothing at all, as before |

Every other function rounds and checks the rounding mode: the arithmetic, `ldexp` and `half` (of
numbers and of balls), the functions of `kairn::finite::`, the [building blocks](#building-blocks)
but `next_up` and `next_down` (the directed bounds among them: they compute under rounding to
nearest what rounding down or up gives), `from_limbs` and `kairn::is_normalized` of two limbs (both
test $x_0 + x_1 = x_0$), the constructors of `Ball<T, 2>` from a center of two limbs or a
constant of two limbs (the test of a canonical center), the arithmetic of intervals, and the
functions of the interface of `Interval` and `Ball` that compute a bound or a center: the midpoint,
the radius and the split of an interval, the conversions `Ball<T, 1>(X)` and `Interval<T, 1>(B)`,
`Ball<T, 2>::from_interval`, the bounds of a ball as numbers of `T` and the narrowing of a ball to
one limb (sums, halvings and directed sums computed under rounding to nearest). The header `config.hpp` has the same list, and the reference comment of each of
these functions says "Does not round".

- `kairn: the floating-point environment: ` followed by what is wrong:
  `the rounding mode is not to nearest (MXCSR.RC is not zero)`,
  `results below the normal range are flushed to zero (MXCSR.FTZ is set)` or
  `subnormal operands are read as zero (MXCSR.DAZ is set)` on x86-64;
  `the rounding mode is not to nearest (FPCR.RMode is not zero)`,
  `subnormal numbers are flushed to zero (FPCR.FZ is set)`,
  `alternate floating-point behavior is on (FPCR.AH is set)` or
  `subnormal operands are read as zero (FPCR.FIZ is set)` on AArch64. Restore the environment as
  above. A program that would rather log it can define `KAIRN_ENVIRONMENT_FAILURE` before
  including Kairn; the operation then goes on without checking its operands (in that environment
  the check could refuse a canonical one), with no guarantee for its result:

  ```cpp
  --8<-- "docs/examples/cpp/troubleshooting.cpp:handler"
  ```

- `kairn: an operand: is not canonical (finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN)), so no guarantee applies to the result`,
  or from a function of `kairn::finite::`,
  `kairn: an operand: is not normalized (x0 + x1 is not x0), so no guarantee applies to the result`.
  A two-limb number whose limbs the program wrote, into `limb[]` or with `from_limbs_unchecked`,
  is not a pair that Kairn's operations return; or a result of `kairn::finite::` that is not
  finite, which need not be canonical, was passed to an operator. Build numbers with the
  constructors, with `from_limbs`, or as results of Kairn's operations, and test a result of
  `kairn::finite::` with `kairn::isfinite` first.
- `kairn: from_limbs: the limbs are not a canonical pair (finite with x0 + x1 == x0, an infinity and a zero, or two NaN)`.
  The same, caught when the number is made.
- `kairn: fast_two_sum: |a| < |b|, which its requirement |a| >= |b| excludes (two_sum takes any order)`.
  Without the checks, the sum is still the rounded sum, but the error term need not make it exact:
  use `two_sum`, or put the larger operand first.
- `kairn: SumAndError: the sum and the error term are not a canonical pair (an infinite operand, a sum that overflows, or two_sum with |b| the largest finite number), so the conversion to Expansion<T, 2> has no guarantee`.
  The result of `two_sum` or `fast_two_sum` converted to `Expansion<T, 2>` had an error term that is
  not finite. Test `kairn::isfinite` on the sum, or keep the operands away from the largest finite
  number.
- `kairn: a ball: has a negative radius (Ball::empty() is the empty set)`. Without the checks, such
  a ball is the empty set; write `Ball<T, K>::empty()` for that. Also
  `kairn: a ball: has a center that is not canonical` and
  `kairn: a ball: is not canonical (a finite ball with a canonical center and r >= 0, the whole line or the empty set), so no guarantee applies to the result`,
  for a center or a ball built from limbs the program wrote.

### What is not an error

- **Contraction.** A compiler that fuses products and sums (`-ffp-contract`, `/fp:contract`) does
  not break a two-limb operation: the kernels are written so that no compiler can fuse a product
  into one of their additions, and a product that the program passes in is guarded
  ([Products the program passes in](guarantees.md#products-the-program-passes-in)); the tests
  check both under every contraction setting. A one-limb number behaves like `T`, contraction
  included, so `a * b + c` on `Expansion<double, 1>` can differ from the same on `double` under
  Clang's default; `KAIRN_K1_CONTRACT` makes them agree ([One limb](guarantees.md#one-limb)). And
  in `x += a * b` with `a` and `b` of type `double`, the product is rounded to `double` before
  Kairn sees it: make one factor a k-number to keep its error.
- **An infinite result, or a ball that is the whole line.** An operation that overflows returns
  $(\pm\infty, 0)$, and a ball that cannot be bounded is the whole line, which contains every
  result ([Overflow and non-finite values](guarantees.md#overflow-and-non-finite-values)). Test
  results that may come near the top of the range with `kairn::isfinite(x)` and `X.is_finite()`.
- **UNVERIFIED operations.** An operation whose proof is not checked compiles only with the marker
  `kairn::unverified` on an operand, and does not compile without it
  ([Proved, and UNVERIFIED](guarantees.md#proved-and-unverified)). In this version every kernel is
  proved, so no operation needs the marker.
- **Metal.** Kairn has no GPU code yet, so there is no Metal backend and no Metal self-test.
- **A global variable with the name of one of Kairn's.** A program's global variable may have the
  name of a parameter or a local variable of Kairn's headers (`x`, `a`, `inf`, ...), which MSVC
  reports at `/W4` (C4459, "declaration hides global declaration") and under `/analyze` (C6244),
  and GCC 11 and 13 under `-Wshadow` for the parameters of some constructors. Each header of Kairn
  turns these warnings off for its own declarations, and only there, so that a program built with
  warnings as errors builds; Clang's `-Wshadow` does not report it
  ([Testing](../developer/testing.md#the-programs-names)).

## Build the documentation

```sh
python3 -m venv .venv
.venv/bin/pip install -r docs/requirements.txt
.venv/bin/mkdocs serve
```

The site is then at <http://127.0.0.1:8000>. [Documentation](../developer/documentation.md) has the
rest: the strict build, the link checker and how pages are written.
