# The floating-point environment

Every guarantee of Kairn is a theorem about floating-point operations that round to nearest, keep
subnormal numbers, and are executed as written. A two-limb operation is built from *error-free
transformations*, short sequences such as TwoSum whose second result is exactly the rounding error
of the first; they are exact only under those conditions. When one fails, the arithmetic itself
reports nothing: the result still looks like a two-limb number, and its second limb can be wrong
(below, a measurement of exactly that). This page says what the library needs, what a compiler's
contraction and fast-math do to it and what Kairn does about them, and the checks that report a
wrong environment: two that a program calls, one that every function on arrays makes in every build,
and those of a build with `KAIRN_CHECKS`.

## The checks, in a program

```cpp
--8<-- "docs/examples/cpp/concepts_environment.cpp:checks"
```

```text
--8<-- "docs/examples/cpp/concepts_environment.txt::2"
```

The program is
[`docs/examples/cpp/concepts_environment.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/concepts_environment.cpp);
ctest builds it with the build's flags and under each contraction setting of the compiler, and
compares its output with the text on this page each time (`api.example.concepts_environment`).

## What the library needs

The contract ([Environment](../developer/design/phase0/environment.md#the-contract)):

1. **Rounding to nearest, ties to even**, for every operation. Kairn never reads or writes the
   rounding mode to do its work, and never changes the floating-point environment. A result rounded
   down or up, as an interval needs, is computed under rounding to nearest
   ([Building blocks](../getting-started/index.md#building-blocks)).
2. **Subnormal numbers kept**: no flush to zero of results (FTZ) and no reading of subnormal operands
   as zero (DAZ). The bounds' absolute terms, multiples of the smallest subnormal number $\eta$, are
   about that range ([Precision and magnitude](precision.md)).
3. **Each operation executed as written**: no reassociation of sums and no other rewriting that
   changes a value. Contraction of a product and a sum into one fused multiply-add is the one
   transformation Kairn tolerates, by construction (below).
4. **A hardware fused multiply-add.** On x86-64 the headers refuse to compile unless the compiler
   targets a processor with FMA ([Hardware FMA](../getting-started/index.md#hardware-fma));
   AArch64 always has it.

## Contraction and fast-math

**Contraction** is a compiler's computing `a * b + c` as one fused multiply-add,
$\mathrm{RN}(ab + c)$, instead of two rounded operations. GCC does it by default in
C++ (`-ffp-contract=fast`), Clang under `-ffp-contract=on` and `=fast`, MSVC under `/fp:contract`. It
changes the bits of a result, and it can break an error-free transformation: in Phase 0, a textbook
double-word product compiled with Apple clang and `-ffp-contract=fast` or MSVC and `/fp:contract` came
out wrong in all 20 000 cases tested, with a relative error of about $u$ instead of $3u^2$, the low
limb noise, and nothing reported it
([What the experiment showed](../developer/design/phase0/environment.md#what-the-experiment-showed)).

What Kairn does about it:

- **No product feeds an addition inside a kernel.** The generator writes every rounded product as
  `fma(a, b, +0)`, whose result is not a product a compiler could fuse into the next addition, and
  checks this rule on every kernel; a kernel whose correctness allows either execution of a
  multiply-add is proved for both
  ([The rule](../developer/design/phase0/environment.md#the-rule-no-product-feeds-an-addition)).
- **Values the program passes in are guarded.** A product the program computes and passes to an
  operation, as in `x + a * b`, could still be fused into the kernel's first error-free sum by a
  compiler that contracts across statements. So every value of `T` that enters from the program
  passes through a *guard*, an addition of $+0$, before any kernel adds it: a product plus $+0$ is
  at most fused into one FMA that rounds the product
  ([Products the program passes in](../getting-started/guarantees.md#products-the-program-passes-in)).
- **The tests check both** under every contraction setting of each compiler: the kernels' results
  against the oracle, their object code for fused instructions the description did not ask for, and
  each guarded form with the product written in the call against the same operation on the rounded
  product, bit for bit (`api.boundary.*`; [Testing](../developer/testing.md#contraction)).
- **A factor of a fused multiply-add is guarded too.** Nothing can be fused into a product, but a
  compiler that sees the other factor to be 1 turns the fused multiply-add into an addition, and
  fuses the program's product into that: measured with Apple clang 21 and Clang 18 under
  `-ffp-contract=fast` in the dot product and the accumulator's product of one limb, and with Apple
  clang 21 in the products of Milestone 1 (`two_prod`, `mul_down`, `mul_up`, `x * a` of two limbs,
  of `Packed` and of a `Ball`), the convolution of one limb and the scaling of arrays of two limbs.
  So every value of the program that is a factor of a fused multiply-add whose addend is not zero
  passes through the guard first, wherever it was measured or not; a factor of a plain product
  needs none ([Functions on arrays](../reference/batch.md#arrays)).

This program passes a product straight in, and gets the operation on the product rounded:

```cpp
--8<-- "docs/examples/cpp/concepts_environment.cpp:guard"
```

```text
--8<-- "docs/examples/cpp/concepts_environment.txt:3:5"
```

So **a program need not do anything about contraction**: it may compile with any contraction
setting and pass its own products to Kairn ([What is not an error](../getting-started/index.md#what-is-not-an-error)).
Three things remain the program's:

- **A product of two `double`s is a `double`.** In `x += a * b` with `a` and `b` of type `double`,
  the product is rounded before Kairn sees it; to keep its error, make one factor a two-limb number.
- **One-limb numbers behave like `T`**, contraction included: they are not guarded, so `p * q + r` on
  `Expansion<double, 1>` may be one rounding where the compiler contracts, as for `double`
  ([One limb](../getting-started/guarantees.md#one-limb)).
- **Limbs written directly** into `limb[]` are not guarded: such a limb must not be a product the
  compiler can see being computed; `from_limbs` guards what it is given.

**Fast-math** is worse than contraction: `-ffast-math` and its parts let the compiler reassociate
sums, ignore signed zeros or infinities, and replace quotients, and no way of writing C++ survives
them. Including Kairn fails with an `#error` under every such flag that the compiler announces with a
macro: `-ffast-math`, `-Ofast`, `-ffinite-math-only`, with GCC also `-fassociative-math`,
`-funsafe-math-optimizations`, `-fno-signed-zeros` and `-freciprocal-math`, and MSVC's `/fp:fast`; and
under evaluation in a wider format (x87). Clang announces three of those flags with no macro, and
Apple clang does not announce `-ffp-model=fast`: only `kairn::self_test()` can see them, by a result
they change ([When a file is compiled](../getting-started/index.md#when-a-file-is-compiled)).
`-fno-signed-zeros` is not supported with any compiler
([Products the program passes in](../getting-started/guarantees.md#products-the-program-passes-in));
`-frounding-math` is ([Compiler flags](../developer/design/phase0/environment.md#compiler-flags)).

## The checks

| Check | When | What it checks | What it costs |
|---|---|---|---|
| `kairn::self_test()` | once, at startup | with the flags of the file that calls it: rounding to nearest with ties to even, no flush to zero of results or operands, no reassociation, signed zeros respected by the FMA, a fused FMA, correctly rounded quotients and square roots; then every generated kernel, for `float` and `double`, on fixed operands, against the results the generator's exact interpreter computed | its run time is not measured; a file with one call compiled in 0.21 to 1.08 s at `-O2`, against 0.06 to 0.23 s for one that only includes `kairn/kairn.hpp` ([Compile times](../developer/results/costs-milestone1.md#1-compile-times)) |
| `kairn::environment_ok()` | whenever the program may have changed the environment | the control register (MXCSR on x86-64, FPCR on AArch64): rounding to nearest, no FTZ, no DAZ | 0.36 to 0.39 ns on an Apple M3, 1.10 ns on an Intel i5, 6.2 to 6.5 ns on an AMD Zen 2 ([The cost of the environment check](../developer/results/costs-milestone1.md#2-the-cost-of-the-environment-check)) |
| the check of a batch entry, **in every build** | before the loop of every function on arrays (`kairn/batch.hpp`) and of every operation on whole ball vectors (`kairn/ball_vector.hpp`, its constructors from centers and a radius included), `KAIRN_CHECKS` 1 or 0 | the control register, as `kairn::environment_ok()` reads it; `norm_upper` of an array and the negation of a ball vector, which compute no sum, leave the rounding mode out | per call, whatever the length, one read of the register, one test of a mask and a branch; the report of a failure is a function of its own, never inlined (since 2026-11-23). Measured on 2026-11-23: about 5 ns a call on an AMD Zen 2, where reading MXCSR is slow (4.6 to 5.7 ns for one limb up to 16 elements), 62 to 82% of a `sum` or `dot` of up to 8 elements of one limb there, 7 to 27% at 64 and under 5% from 1 024, or from 2 to 16 elements of two limbs; on an Apple M3 at most 0.35 ns a call up to 16 elements of one limb (up to 0.7 with the header before), though chains of short operations of one limb, each on the result of the one before, lose 4.5 to 6.6 ns per operation there; an operation or a constructor of a short ball vector loses about the read (before 2026-11-23 a constructor could lose 11 to 19 ns more, where the compiler stopped inlining it) ([The checks of a debug build](../developer/testing.md#the-checks-of-a-debug-build), the table of 2026-11-21; [Benchmarks, Milestone 2](../developer/results/bench-milestone2.md#the-check-measured-again-on-2026-11-23)) |
| `KAIRN_CHECKS` 1, the default without `NDEBUG` | before every operation of `Expansion`, `Ball` and `Interval` that rounds, of the building blocks and of the accumulator; in the batch entries after their check of the environment | the environment, then that every operand is canonical; in the batch entries the operands, the lengths of the arrays and the arrays that alias | for two-limb operations at most 14% in a chain, 1.26 to 3.00 times for `x + y` and 2.16 to 4.15 times for `x * y` in a loop; for one limb 1.6 to 8.0 times in a chain and 5.2 to 34.8 times in a loop ([The cost of the environment check](../developer/results/costs-milestone1.md#2-the-cost-of-the-environment-check)) |

- **`kairn::self_test()`** returns a `kairn::Status`: `ok()`, and `message()`, the first check that
  failed, with the kernel for a failed kernel; it never aborts and only reads. It tests the flags of
  the file it is compiled in, not those of every file of the program, and a flag only through a
  result the flag changes ([When the program runs](../getting-started/index.md#when-the-program-runs)
  lists its messages and their causes).
- **`kairn::environment_ok()`** says whether the rounding mode and flush to zero are as Kairn assumes,
  now. Kairn never changes them; other code can (an interval library that rounds upward, or flush to
  zero set at startup by any object compiled with `-ffast-math`), and a program that calls such code
  checks and restores the environment before calling Kairn
  ([Troubleshooting](../getting-started/index.md#when-the-program-runs) shows how).
- **The check of a batch entry** is made in every build, with `KAIRN_CHECKS` 1 or 0, with or without
  `NDEBUG`. A *batch entry* is a function that runs a loop over arrays: every function of
  `kairn/batch.hpp` (`sum`, `sum_fast`, `dot`, the maps, `conv`, `norm_upper`) and every operation
  of `kairn/ball_vector.hpp` on whole ball vectors, its constructors from centers and a radius
  included (its accessors and views, which copy, check nothing). Before its loop it reads the
  control register once, as `kairn::environment_ok()` does, and if the environment is not the
  default one calls the library's handler, `KAIRN_ENVIRONMENT_FAILURE`, with the message of a debug
  build, which by default prints it and stops the program. The handler is called from one function
  of the program, which the linker keeps once: a program that defines it defines it the same way in
  every file (`kairn/config.hpp`). The default environment is the
  precondition of each of these functions, and this is that precondition, checked
  ([Functions on arrays](../reference/batch.md#checks),
  [Ball vectors](../reference/ball_vector.md#checks); the tests `api.checks.off.*` build them with
  `KAIRN_CHECKS` 0 and require the stop). `norm_upper` and the negation of a ball vector, which
  compute no sum, leave the rounding mode out (flush to zero still changes their comparisons).
  **The scalar operations, `Packed` and the accumulator**, whose operations take one term at a
  time, are no batch entries: they check the environment only with `KAIRN_CHECKS`
  (`kairn/config.hpp`, `KAIRN_CHECKS`).
- **`KAIRN_CHECKS`**, 1 by default when `NDEBUG` is not defined, as for `assert`, and the same in every
  file of a program: before every operation of `Expansion`, `Ball` and `Interval` that rounds, of
  the building blocks and of the accumulator, it checks the environment, then the operands (canonical
  numbers and sets, a radius that is not negative); in the functions on arrays and the operations on
  ball vectors, after the check of a batch entry, it checks the operands, the lengths of the arrays
  and the arrays that alias. A function whose result cannot depend on the rounding mode (negation,
  the comparisons, the conversions to `T`, the predicates of an interval, and others) does not check
  the rounding mode, so that a program may call it under a directed one
  ([the list](../getting-started/index.md#when-a-check-of-a-build-without-ndebug-fails)).

## When the environment is wrong

Without `KAIRN_CHECKS`, a scalar operation does not report it: an operation under another rounding
mode, under flush to zero, or compiled with a flag that rewrites its arithmetic returns a result with
no guarantee, which can look like any other. A function on arrays and an operation on whole ball
vectors still report it in every build: flush to zero, and, all but the two that compute no sum, a
rounding mode that is not to nearest. A flag that rewrites the arithmetic and that the compiler does not announce to the
headers is reported by no check of an operation: only `kairn::self_test()` can see it. That is why
`kairn::self_test()` is to be called once and its failure taken as a reason not to use Kairn, and why
a program that changes the environment checks it.

With `KAIRN_CHECKS`, and at every batch entry in every build, a wrong environment stops the program
before the operation, with a message that says what is wrong (`kairn: the floating-point
environment: the rounding mode is not to nearest (MXCSR.RC is not zero)`, and the others of
[Troubleshooting](../getting-started/index.md#when-a-check-of-a-build-without-ndebug-fails)), and
`std::abort()`. A program that defines `KAIRN_ENVIRONMENT_FAILURE` to a statement that returns gets
that statement instead; the operation then goes on, without checking its operands, and with no
guarantee for its result. In the default environment, an operand that is not canonical stops the
program with a message of its own, in a build with `KAIRN_CHECKS`.
