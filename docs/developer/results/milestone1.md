# Milestone 1 report

**Status: complete, with the deviations and open issues listed below.** The first version of
this report said the same too early: an audit of the milestone against the brief, made after it,
found requirements that were neither met nor flagged. Most were then met; the others are recorded
as deviations or open issues ([what the audit found](#what-an-audit-against-the-brief-found)).
Milestone 1 is the vertical slice of the [brief](../design/brief.md): `double`, one and two limbs, scalar code with
AVX2 and NEON, $+$, $-$, $\times$, `Ball`, proofs, the oracle with both test tiers, CI, and the
skeleton of this site. This page says what exists, what is proved, what the tests and the
benchmarks measured, and what is still open. Each section links to the page that has the details.

## In short

- **Every kernel that ships is proved.** 63 generated kernels, 131 theorems checked by Rocq with
  Flocq, four allowed axioms, no admitted statement. The statements are printed by the generator
  from the same descriptions as the C++.
- **Overflow, infinities and NaN have defined results** (decision D5), proved in a model of
  IEEE 754 arithmetic: an operation never returns a finite wrong result.
- **No claim was violated by any test.** The brute-force runs judged 13.8 billion results of the
  compiled kernels and 0.78 billion of the interpreter on every operand of small formats, on
  three machines, with five compilers. An adversarial search then drove most bounds to within
  $10^{-15}$ of the claim without crossing one: the proved bounds are tight.
- **The compiled code is what the descriptions ask for.** Every kernel, under every flag set of
  every compiler of CI, has exactly the fused instructions and the multiplications of its
  description.
- **The finite-only functions are within 1.2 times textbook double-word code** in all but one
  configuration. The libraries the brief names as the reference are timed at Milestone 8, as
  planned; until then the textbook code is the baseline. The default operators, which also handle
  overflow, cost the same in dependent chains and 1.05 to 2.7 times the textbook code in loops of
  independent operations.
- **Not machine-checked**: `ldexp` when $2^n$ is not a number of the limb type, which is composed
  by hand from proved steps (deviation 17). **Proved for gradual underflow only**: the
  flush-to-zero arithmetic of Metal needs proofs of its own in Milestone 3 (deviation 19).
- **Five decisions were for the owner**; they are taken, and listed at the end.

## What is done

| The brief asks for | State |
|---|---|
| `double`, $k = 1$ and $k = 2$ | `Expansion<T, 1>`, `Expansion<T, 2>` for `double` and also `float`: every proof holds for every precision from a stated minimum (at most 4 bits), so `float` came with it |
| scalar, AVX2, NEON | Every kernel is generated for `double` and `float` scalars, for AVX2 (4 doubles, 8 floats) and for NEON (2 doubles, 4 floats), and each backend is tested against the oracle. The public types are scalar; the packed kernels are reachable in `kairn::gen` and become the batch interface in Milestone 2 |
| $+$, $-$, $\times$ | With a two-limb, one-limb or `T` operand; also `add_fast`, negation, absolute value, the six comparisons, the conversions to one limb (nearest, down, up, upper bound of the magnitude), and `ldexp` and `half` |
| `Ball` | `Ball<T, 1>` and `Ball<T, 2>`: $+$, $-$, $\times$, scaling by a `T`, negation, and the three states (finite ball, whole line, empty set) |
| proofs | [Proofs](../../proofs/index.md); the table below |
| the oracle with both test tiers | An independent oracle in exact arithmetic (Python, deviation 13); a quick tier, a full tier and the brute-force tier ([Testing](../testing.md)) |
| CI | Five workflows on hosted runners: the quick tier and the full tier on seven platform and compiler pairs (Linux x86-64 and arm64 with GCC and Clang, macOS arm64 with Apple clang, Windows x64 with MSVC and clang-cl), with the flag sets of a client and the check of the object code; the generator's suite; the proofs with their audit; the generated files and this site |
| website skeleton | Home, Getting started (with how to choose `T` and $k$, and troubleshooting), What holds today, one tutorial, 64 generated reference pages (the 63 kernels and their index), the C++ API reference, Proofs, the developer guide |

Added beyond the brief, because the tests showed they were needed:

- **Rule R3, the guard** ([Architecture](../architecture.md#the-kernel-ir)). With GCC's default
  setting, with `-ffp-contract=fast` and with MSVC's `/fp:contract`, a product written by the
  program in a call such as `x + a * b` was fused into the kernel's first addition, and the result
  was wrong in every one of 200 000 cases chosen to cancel. Every value that enters from the
  program now passes through an addition of zero that the generator emits and checks.
- **The second radius design.** The first design computed a ball's radius by steps to the next
  number; a product of balls cost 13 to 20 times the product of the centers. The radius is now
  computed with ordinary operations and inflated once.
- **A normal constant in the radius.** A constant of a few times the smallest subnormal number
  made every `Ball` operation take 30 to 35 ns on an Intel processor; it is now a normal number,
  and the same operations take 5 to 7 ns there.
- **The scalar fix-up behind a branch**, which removed most of the cost of decision D5 in scalar
  code.

## Bounds proven

All of these are theorems about the generated models, for every precision $p$ from the minimum
shown and every exponent range, with gradual underflow. $u = 2^{-p}$, $\eta$ is the smallest
subnormal number, operands of two limbs are normalized, and $z$ is the result. Sources: the
algorithms of the two-limb arithmetic are those of Joldes, Muller and Popescu
([JMP17](../design/phase0/references.md#jmp17)); their bounds were re-proved here with underflow,
using five files of the Rocq proofs of Muller and Rideau
([MR22](../design/phase0/references.md#mr22), MIT license). Every reference page names the source
and the license of its kernel.

| Operation | Kernel | Proved | $p \ge$ |
|---|---|---|---|
| $x + y$ | `add_2_2` (JMP17 Alg. 6) | $z$ normalized, $\lvert z - (x+y)\rvert \le \frac{3u^2}{1-4u}\lvert x+y\rvert$ | 3 |
| $x + a$ | `add_2_1` (JMP17 Alg. 4) | $z$ normalized, $\lvert z - (x+a)\rvert \le 2u^2\lvert x+a\rvert$ | 3 |
| $x - y$, $x - a$, $a - x$ | `sub_2_2`, `sub_2_1`, `sub_1_2` | those of the additions | 3 |
| `add_fast(x, y)` | `add_fast_2_2` (JMP17 Alg. 5) | $z$ normalized, $\lvert z - (x+y)\rvert \le 3u^2(\lvert x\rvert + \lvert y\rvert)$ | 2 |
| $x \times y$ | `mul_2_2` (JMP17 Alg. 12) | $z$ normalized, $\lvert z - xy\rvert \le 4u^2\lvert xy\rvert + \tfrac32\eta$ | 4 |
| $x \times a$ | `mul_2_1` (JMP17 Alg. 9) | $z$ normalized, $\lvert z - xa\rvert \le 2u^2\lvert xa\rvert + \eta$ | 2 |
| `ldexp(x, n)`, `half(x)` | `mul_pow2_2` | $z$ normalized, $\lvert z - 2^n x\rvert \le \eta$ (one call) | 2 |
| $-x$, $\lvert x\rvert$ | `neg_2`, `abs_2` | exact, normalized | 1 |
| $<$, $\le$, $=$ and the mixed forms | `lt`, `le`, `eq` kernels | the truth about the exact values | 1 |
| conversions to one limb | `to_nearest_2`, `to_down_2`, `to_up_2`, `abs_upper_2` | the exact rounding of $x$ to `T` | 1 |
| one limb: $+$, $\times$ | `add_1_1`, `mul_1_1` | $\lvert z - v\rvert \le \frac{u}{1+u}\lvert v\rvert$, plus $\tfrac12\eta$ for a product | 1 |
| `Ball`: $+$, $-$, $\times$, scaling, negation | `ball_add_k`, `ball_sub_k`, `ball_mul_k`, `ball_scale_k`, `ball_neg_k`, $k = 1, 2$ | containment: $x \circ y$ is in the result for every $x$, $y$ of the operands; the center is normalized | 1 to 4 |
| building blocks | `two_sum`, `fast_two_sum`, `two_prod`, `split`, `two_prod_dekker`, `radd`, `rmul` | exact error terms ($\tfrac12\eta$ for `two_prod`, $\tfrac{13}{8}\eta$ for Dekker's product); the directed steps exceed the exact value by at most $\tfrac32$ gaps | 2 to 4 |

**Proved in Flocq's model of IEEE 754**, where operations overflow and values may be infinite or
NaN, for formats shaped like `binary32` and `binary64`
([statements](../design/milestone1.md#ieee-like-results)):

- **The nine arithmetic operations of two limbs** (statements F1 to F5): the result is canonical;
  if it is finite, every operand is finite and the bound above holds, so an overflow inside a
  kernel never produces a finite wrong result; the result is finite when
  $\lvert x\rvert, \lvert y\rvert \le 2^{e_{\max}-2}$ for sums and
  $\lvert xy\rvert \le 2^{e_{\max}-1}$ for products; an overflow gives the infinity with the sign
  of the exact result; a non-finite operand gives what the operation of `T` gives.
- **The eight `Ball` operations** (B1 to B4): the result is canonical; it is empty exactly when an
  operand is; it contains every $x \circ y$ in every case, the whole line counting as containing
  everything; and for finite operands it is a finite ball when no member of the exact result
  exceeds a quarter of the overflow threshold ($2^{1022}$ for `double`), a sixteenth for the
  product of one-limb balls
  ([conditions](../design/milestone1.md#when-the-result-is-a-finite-ball)).
- **Comparisons, conversions, negation and the four constructors** behave as stated on
  infinities and NaN.

**What the proofs rest on.** 131 theorems pass the audit: 42 about the real model, 39 about the
IEEE model whose statements the generator prints, 35 more about generated statements, and 15
whose statements are written by hand because they say more than the claims can express. 130
depend on exactly the four allowed axioms of Rocq's real numbers and one on two of them. Written
by hand and trusted: the meaning of each operation in Flocq's terms
(`proofs/theories/IeeeOperations.v`), the vocabulary of the statements (`IeeeVocabulary.v`), and
the generator, which must print the Rocq model and the C++ from one description faithfully. The
generator's own tests compare every compiled kernel with its exact interpreter, bit for bit.

**Not proved** (each is stated as such where it appears):

- conditions for a finite result sharper than the ones above: complete enumerations of small
  formats first see an overflow at 0.55 of the overflow threshold for sums and 0.86 for products,
  where the proved conditions are a quarter and a half of it, and a ball that is the whole line
  at 0.55 to 0.81 where the proved condition is a quarter;
- `ldexp` when $2^n$ is not a number of `T`, for one limb and for two (deviation 17);
- anything about arithmetic that flushes subnormal results to zero: the proofs hold for every
  precision and exponent range, with gradual underflow (deviation 19);
- on MSVC, that the compiler keeps the guard: MSVC has been seen to remove an addition of zero,
  so there the guard rests on tests that run on every change.

## Brute-force results

The brute-force tier ran on the final code for 3 to 3.5 hours per machine
([Brute-force results](brute-milestone1.md), which has the cases per stratum, the largest error
over its bound per kernel, format and backend, and the inputs that came closest). The oracle
judged every result in exact arithmetic.

| Machine | Compilers and backends | Runners | Compiled results judged | Enumerated, small formats | Wall time | Judged per second |
|---|---|---|---|---|---|---|
| Linux x86-64, AMD EPYC 7452 | GCC 13, Clang 18; scalar, AVX2 | 24 | 7 790 145 432 | 936 163 801 | 3.5 h | 618 560 |
| macOS arm64, Apple M3 Max | Apple clang 21, GCC 16; scalar, NEON | 24 | 4 707 341 928 | 46 830 458 | 3.0 h | 433 261 |
| Windows x64, Intel Core i5-13500T | MSVC 19.52; scalar, AVX2 | 12 | 1 335 089 988 | none | 3.0 h | 122 412 |

A runner is one build of the kernels: scalar or packed, under each contraction setting, and for
the scalar code with each of the two forms of the fix-up. Every runner of a machine judged the
same cases.

- **No claim was violated.** No failure and no invalid case in 13 832 577 348 judged results of
  compiled kernels (`binary64` and `binary32`, random operands of every stratum, infinite and
  NaN operands included for the 39 kernels that accept them) and in 782 322 659 judged results of
  the interpreter on every operand of 328 small-format domains. On each machine every runner
  gave the same counts and the same extremes.
- **Cases per kernel and format.** All 126 pairs of a kernel and a format got 110 to 122 million
  cases. Counting only the results that were judged, 115 of the 126 reach $10^8$; the other 11
  (85 to 99 million) are products of the finite-only layer, where 16 to 25% of the random cases
  overflow and the claims say nothing.
- **How close the bounds came.** Attained exactly: the bound of `add_1_1`, the term
  $\tfrac12\eta$ of `two_prod`, and the $\tfrac32$ gaps of `radd` and `rmul`. Within
  $10^{-9}$ of the bound, through the underflow terms: `mul_1_1` and `mul_2_1`. Then
  `sub_2_1` at 0.997 of its bound, `add_2_1` at 0.988, `mul_2_2` at 0.977 to 0.981. Far from
  underflow the largest observed constants are 3.49 for `mul_2_2` (4 is proved), 2.30 for
  `add_fast` (3), 2.24 for the two-limb sums and differences ($3/(1-4u)$) and 1.99 for the sums and the product
  with a one-limb operand (2).
- **`Ball` radii.** The closest a returned radius came to the smallest radius that encloses the
  exact set was one gap above it (one-limb sums, differences and scalings); the other `Ball`
  kernels kept 1.25 to 2.5 gaps. No radius was too small, and the closest ones could have lost
  one unit in the last place and no more.
- **Statement B4** was proved after the main runs started, so a supplementary run judged it on the
  eight `Ball` kernels it concerns: 2 260 800 000 compiled results and 151 290 688 enumerated
  ones, no failure. B4 applied to 1 172 390 844 compiled cases and 8 926 458 enumerated ones, and
  every one gave a finite ball.
- **Precision 1.** Twenty-six kernels are claimed from 1 bit of precision, and the plan of the
  main runs started them at 2 bits. A supplementary run enumerated them at 1 bit: 278 652 cases,
  no failure. At that precision the oracle flagged infinite radii of three `Ball` kernels as
  suspicious; an exact check showed that every one is an overflow of the radius, whose constants
  are large when $u = 1/2$
  ([details](brute-milestone1.md#supplementary-run-precision-1)).

Not run: every operand of the quick tier's formats for the two-limb balls with two operands
(140 million to 12.4 billion cases each; smaller complete formats and restricted domains ran in
their place), enumerations on the Windows machine, and clang-cl, which only the CI's tiers cover.

### The adversarial search

The brief asks for a search that tries to make the error large, seeded with the near-misses of
the proofs. It did not exist at the first version of this report; it was built after the audit
([Testing](../testing.md#the-adversarial-search)). `kairn-oracle search` keeps a population of
cases per bounded quantity and mutates them (bits of a limb, a tail at the edge of the
normalization invariant, exponents, signs, moves toward cancellation, ties and the underflow and
overflow thresholds), judged by the oracle's own exact judge. Its seeds are the lines that came
closest in the brute-force runs, the structured cases of the strata, and the tight cases that
[JMP17](../design/phase0/references.md#jmp17) and [MR22](../design/phase0/references.md#mr22)
give, transcribed exactly.

- **No claim was violated** in about 100 million searched cases (one million for each of the 94
  pairs of a kernel and a format, and three runs of 20 000 per pair, one of them through a
  compiled runner).
- **The bounds are tight.** With every seed, the search came closer to the claim than the
  13.8 billion random results on 86 of the 116 quantities that are not exact claims, as close on
  30, and farther on none. The accurate sum and difference reached $1 - 8\times10^{-16}$ of their
  bound in `binary64` (0.67 to 0.75 in the brute-force runs), the sums with a one-limb operand
  $1 - 2\times10^{-16}$, the two-limb product $1 - 2\times10^{-15}$ (0.977), `add_fast`
  $1 - 8\times10^{-16}$ (0.74). The smallest slack of a `Ball` radius went from 1.25 gaps to 1.11
  for the two-limb sums and from 2.5 to 2.2 for the two-limb product.
- **What it does not replace.** From the strata alone, without the seeds, it was farther than the
  random runs on 30 quantities. Of the two planted faults that only the full tier catches, it
  found one no sooner than random cases do and missed the other, which breaks containment only at
  radius zero, where nothing leads a search.
- **A failing case is shrunk** by `kairn-oracle shrink` to a simpler case that fails the same
  claim with the same runner, down to the smallest toy format where a failure of the same kind
  exists; it was tested on the faults the oracle's self-tests inject. The cases that found a
  problem and those closest to a claim, 185 lines, are stored in `tests/regression/cases.txt` and
  run in the quick tier through every runner.

## Benchmarks

Three machines (Apple M3 Max, AMD EPYC 7452 "Zen 2", Intel Core i5-13500T), five compilers, nine
configurations, three runs each, on the final code
([Benchmarks, Milestone 1](bench-milestone1.md)). A *loop* is a loop of independent operations; a
*chain* is a dependent chain or a Horner evaluation. Ratios are of minimum times.

The brief's budget is "within about 1.2 times the fastest of QD, CAMPARY, MultiFloats.jl and CCCL
fpmp2" for operations without rigorous bounds. Those libraries were not timed in this milestone:
the [plan](../design/phase0/plan.md#milestones) does that at Milestone 8. The baseline here,
called *textbook*, is the same algorithms written directly from the listings of
[JMP17](../design/phase0/references.md#jmp17), with a plain product, no guard and no handling of
overflow, compiled with the same flags.

| Question | Answer |
|---|---|
| The opaque product, `fma(a, b, 0)` in place of `a * b` | nothing on the M3; 7 to 13% in a product chain on Zen 2; 10 to 12% in scalar chains with MSVC |
| `kairn::finite::` against textbook double-word code (the 1.2 budget of the brief) | within 1.2 in every configuration except one: the loop of $x \times y$ with GCC 13 at `-O2` on Zen 2 (1.26 to 1.27). On the M3 every ratio is between 0.92 and 1.08 |
| The default operators against `kairn::finite::` (the cost of decision D5) | chains: 0.94 to 1.07 on every machine. Loops: 1.08 to 1.19 for $x + y$ with GCC 16, Clang 18, MSVC and GCC 13 at `-O2`; 1.65 with Apple clang and 2.2 with GCC 13 at `-O3`, where the compiler vectorizes the loop of the core and not the operator's. $x \times y$ in a loop: 1.27 to 1.96 |
| The default operators against textbook code | chains: 0.98 to 1.17. Loops: 1.05 to 2.74; within 1.2 only for $x + y$ with GCC 16, Clang 18, MSVC and GCC 13 at `-O2` |
| Packed kernels with the fix-up against packed cores | sums 1.16 to 1.54 in a loop, products 1.70 to 2.05 |
| A `Ball<double, 2>` operation against its center's operation | chains: 0.93 to 1.14. Loops: $X + Y$ 0.93 to 1.35, $X \times Y$ 1.23 to 2.58 |
| A `Ball<double, 1>` operation against one `double` operation | 3.9 to 11.9 in a chain: a rigorous ball costs about six operations where a `double` costs one. An upper estimate: the `double` step it is divided by was later found to be measured below the latency of the operation, by up to a factor of two ([costs](costs-milestone1.md)) |
| `float` limbs | the same conclusions; a `float` operation takes the time of a `double` one except with Clang 18 (1.12 to 1.80) |

Decision D5 expected the handling of overflow to cost 10 to 20% of a two-limb addition. That
holds in scalar chains everywhere (at most 7%) and in scalar loops with four of the six scalar
configurations; it does not hold where the compiler stops vectorizing the loop, nor in packed code
on the M3 (33 to 54%) and the i5 (27 to 53%).

### Compile times and other costs

Measured after the audit, which found them promised and missing
([Compile times and other costs](costs-milestone1.md)).

- **Compile times.** Including `kairn.hpp` takes 0.06 to 0.23 s, less than `<iostream>` with every
  compiler. A unit that uses every operation of all eight types (389 functions) takes 0.27 to
  3.1 s at `-O2`, MSVC being the slowest. The largest kernels today are the two-limb `Ball` sums
  and differences (36 to 38 operations); no kernel dominates.
- **The environment query** `kairn::environment_ok()` costs about 2 cycles on the M3, 5 on the i5
  and 21 on Zen 2, where reading the control register is slow; Phase 0 had said a few cycles.
- **A debug build's checks** (`KAIRN_CHECKS`) add at most 14% to a chain of two-limb operations
  and make loops 1.3 to 4.2 times as long; a one-limb loop up to 35 times.
- **MSVC's stack cookie**, an open issue of Phase 0: with MSVC at `/O2`, a function using a
  one-limb operator got a stack-protection check that the same code on `double` did not, and one
  operation called once per element took 1.97 times as long. The cause was the array of one
  element passed by value; the one-limb operators now take their operands by reference, the
  cookie is gone at `/O2`, and a test fails if it comes back.

## Tests and CI

- **Quick tier** (`ctest`): the tests of the library with the build's compiler and flags, 288 to
  293 tests in 31 to 44 s on the M3, 47 to 54 s on Zen 2 with GCC 13 and Clang 18, and 63 to 71 s
  with MSVC, with `--parallel 4`. The brief asks for under about two minutes per platform, in CI
  too. On the hosted Windows runners the quick tier took 128 to 202 s; the tools' own tests then
  moved to the full tier, which CI also runs on every change. Since then its test step takes 32
  to 65 s on Linux and 71 to 79 s on macOS; on Windows, where the hosted runners vary most, 71 to
  154 s over the first three runs with MSVC and clang-cl, over two minutes in three of those six
  (open issue 20). Since each cross-check runs in one process (2026-11-20, in Milestone 2), 73
  to 93 s over the first two runs with each compiler.
- **Full tier** (`ctest --test-dir build/tests/full`): 407 to 409 more tests, 5 to 11 minutes; in
  CI on every push, in jobs of its own.
- **The flag sets of a client** ([Testing](../testing.md#flag-sets)). The audit found that the
  compiler-flag matrix of the brief was applied to the generated kernels only, and that nothing
  compiled Kairn without optimization on Windows. The public interface is now built and judged by
  the oracle under `-O0` to `-O3` with contraction off, on and fast and with `-frounding-math`
  (GCC, Clang, Apple clang), under `/Od`, `/O1`, `/O2` with each `/fp:` setting (MSVC), and
  under the clang-cl spellings, and the self-test runs under each. Every configuration gives
  correct results.
- **A debug build that runs the checks** ([Testing](../testing.md#the-checks-of-a-debug-build)).
  With `KAIRN_CHECKS` at 1, each of 29 operations and 8 calls of constructors must stop with
  Kairn's message under a directed rounding mode and under flush-to-zero, `environment_ok()` must say so, and operands that are
  not canonical must be refused. They are. The tests found
  four defects in the hand-written headers, all fixed: a constructor called under a directed
  rounding mode stopped the program with a message that named the operands instead of the
  environment; a failure handler that returned could not let the operation continue, against
  the documentation; the documentation of what the checks accept was wrong for the operators;
  and a program compiled with MSVC's `/W4 /WX` that had a global variable named like a local of
  the headers did not build. Two more were found on the way and fixed: `kairn::finite::ldexp`
  of a marked one-limb number did not compile, and neither did a Windows program that includes
  `<windows.h>` before Kairn.
- **The object-code check** ([Testing](../testing.md#object-code)), which the audit found
  missing. The generator writes, for every kernel, how many fused multiply-adds and plain
  multiplications its code asks for; the check compiles one function per kernel and limb type,
  scalar and packed, with both forms of the fix-up, under 24 flag sets per GCC-style compiler
  (`-O0` to `-O3`, contraction off, on and fast, with and without `-frounding-math`) and 9 for
  MSVC, disassembles the object file and compares the counts. Every kernel has exactly the
  instructions its description asks for, on all seven platform and compiler pairs of CI. As a
  control, the textbook `a * b + c` is put through the same check, which must fail exactly in
  the configurations where the compiler fused it (4 to 14 of the 24 with the GCC-style compilers,
  2 of the 9 with MSVC), and does.
- **Planted faults.** 1 052 one-statement changes of the generated scalar kernels were planted in
  turn ([Testing](../testing.md#time)). The quick tier catches 863, the full tier 2
  more, and the generator's comparison of every compiled kernel with its interpreter, bit for
  bit, 122 more. Of the 65 that nothing caught, 48 cannot change a result, and 17 were blind
  spots: the sign of a zero, an internal splitter constant, or operands outside the domain.
  Special operands added to the generator's tests now catch all 17. No planted fault broke a
  claim without being caught.
- **CI** is green on `main` on Linux x86-64 and arm64 (GCC, Clang), macOS (Apple clang) and
  Windows (MSVC, clang-cl); a job takes 1 to 10 minutes. It keeps two artifacts per run: the
  built site, and what the audit of the proofs printed.

## Documentation added

[Home](../../index.md); [Getting started](../../getting-started/index.md), with how to choose
`T` and $k$ and a troubleshooting section that quotes each message a user can meet today, and
[What holds today](../../getting-started/guarantees.md); the tutorial
[Accurate sums and dot products](../../tutorials/accurate-sums.md); 64
[reference](../../reference/index.md) pages generated from the claims (one per kernel, and their
index), each with the statement in plain mathematics, the same statement as Rocq reads it, its
theorem, the axioms it may depend on, its constants and what the brute-force runs measured; the
C++ API reference, generated by Doxygen from the comments of the public headers;
[Proofs](../../proofs/index.md), with how to check them yourself; the developer guide
([Architecture](../architecture.md), [Testing](../testing.md),
[Documentation](../documentation.md)); the [Milestone 1 statements](../design/milestone1.md);
and the results pages. Every example is a file that the tests compile and run. `mkdocs build
--strict`, Doxygen with warnings as errors and a link check run in CI, which keeps the built site
as an artifact and, since the owner's decision of 2026-11-20, publishes it at
<https://danielepanozzo.github.io/kairn/> from every push to `main`.

## What an audit against the brief found

After the first version of this report, the brief and the Phase 0 plan were read again, line by
line, against the repository, in a separate pass that started from the brief and not from this
report. It found the
requirements below, which had been neither met nor flagged. The table says what was done about
each.

| The brief or the plan asks | Found | Now |
|---|---|---|
| CI checks the disassembly of the kernels for fused instructions the descriptions did not ask for | No such check | Built; every kernel passes on every flag set and platform of CI |
| The flag matrix (`-O0` to `-O3`, `-frounding-math`, `/Od`, `/fp:strict`) on what a client compiles | Applied to the generated kernels only, and not on Windows without optimization | Built for the public interface and the kernels, in both tiers |
| In debug builds the scalar operations check the floating-point environment and fail loudly | Implemented, compiled once and never run by a test | Tested on every operation and state; the tests found four defects, now fixed |
| An adversarial search that maximizes error over bound | None | Built; no claim violated, most bounds reached to within $10^{-15}$ |
| A failing case is shrunk automatically and added to the quick tier | No shrinker, no stored cases | Built; 185 stored cases run in the quick tier |
| The quick tier runs in under about two minutes per platform, in CI | 128 to 202 s on the hosted Windows runners | The tools' own tests moved to the full tier: under two minutes on Linux and macOS; on Windows 71 to 154 s, over two minutes in three of the first six job runs. Since each cross-check runs in one process (2026-11-20): 73 to 93 s on Windows over the first two runs with each compiler |
| Compile times are reported | Not measured | Measured |
| The cost of the environment check is reported in Milestone 1 | Not measured | Measured: 2 to 21 cycles |
| MSVC's stack cookie on one-limb values, an open issue for Milestone 1 | Not followed up | Cause found and fixed |
| The printed assumptions of every theorem are kept as a CI artifact and shown on the reference pages | Printed and discarded | Kept as an artifact; the pages name the allowed axioms and point to it (deviation 21) |
| Getting started covers choosing `T` and $k$, and troubleshooting | Neither section | Written, with tested examples |
| Every claim about a bound links to its reference page | Kernel names without links | Linked |
| The C++ API reference by Doxygen; its warnings fail the build | Doxygen was not run | Run in CI, warnings as errors |
| The license travels with an installation | Not installed | Installed |
| Proofs are parametric in the underflow model | Gradual underflow only; the planned symbolic underflow error was not built | Deviation 19; for Milestone 3 |
| The brute-force tier runs nightly | By hand, before a milestone report | Deviation 20; decided: nightly on the hosted runners |
| Core arithmetic is `constexpr` | Deviation 14 named the two-limb products only | Deviation 14 corrected: also `ldexp` and `half` on two limbs and every `Ball` operation |
| Clang's scoped contraction pragma as extra protection | Deviation 2 said it would be kept; no kernel has it | Deviation 2 corrected: not emitted, and why |
| Shipped code is generated | The one-limb `ldexp` beyond the exponent range is composed by hand too | Deviation 17 extended; the pages say so |
| `Interval` and `Ball` share one enclosure interface (`lower`, `upper`, `contains`, `hull`, ...) | `Ball` has its center, its radius and its three states | Open: with `Interval` in Milestone 2 |
| A small generator, budgeted at 1 500 to 2 000 lines | About 5 000 lines, of which the four printers are 2 000 | Open: recorded |
| Whether the "madd" sum replaces the accurate sum is decided by a Milestone 1 benchmark | Not evaluated | Open: the proved accurate sum stays |
| Windows on AArch64 is compiled in CI | The headers stop the build there with MSVC; no job | Open (deviation 11) |
| Statements in the documentation | Three were stale or said too much | Corrected |

The audit could not decide some points, which are for the owner or for later milestones: whether
the fourth test machine counts for CPU-only runs; the pages beyond the skeleton (concepts, about,
citation, changelog), which the brief asks of later milestones; the building blocks
(`two_sum`, `two_prod`, the directed steps) and the constants from an integer or a rational,
which the brief wants public and no milestone of the plan names; and macOS on x86-64, which no
job tests.

## Deviations flagged in this milestone

Each is recorded in [Decisions](../design/phase0/decisions.md#deviations-from-the-brief-flagged).

| | Deviation | Consequence |
|---|---|---|
| 1b | The guard of rule R3 was added | One addition per value that enters from the program: 7 to 13% on an independent $x + a$, at most 5% in a chain |
| 13 | The oracle uses Python's exact integers and fractions instead of GMP or FLINT | The same exactness, no dependency; slower than a compiled oracle |
| 14 | Not `constexpr` yet: the two-limb products, `ldexp` and `half` on two limbs, and every arithmetic operation of `Ball` | Sums, differences, comparisons, conversions, constructors and everything on one limb are; the others need variant kernels with proofs of their own |
| 15 | Reference pages are generated by a tool and committed, not generated when the site is built | A check in CI fails on a stale page |
| 16 | The fix-up for non-finite results costs more than D5 expected in loops and in packed code | See the benchmarks above; `kairn::finite::` is the opt-out |
| 17 | `ldexp(x, n)` for $2^n$ outside the powers of two of `T` is composed by hand in the header, for one limb and for two, from two or three proved steps | What it returns is argued and tested through the oracle, not machine-checked |
| 18 | The quick tier's random cases are generated from a fixed seed at test time, not stored | The same cases on every run and machine; the cases that found a problem or came closest to a claim are stored and run |
| 19 | The proofs are parametric in the precision and the exponent range, not in the underflow model | `float` and `double` with gradual underflow are covered; Metal's flush-to-zero needs proofs of its own in Milestone 3, and none of that framework exists yet |
| 20 | The brute-force tier ran by hand before the milestone report, not nightly | Decided: a nightly run on the hosted runners, with a smaller budget than the runs on the test machines |
| 21 | The reference pages name the axioms a theorem may depend on and point to the audit's artifact; they do not show the printed list | The printed list is one download away; the pages are written without Rocq |
| | `radd` and `rmul` are claimed for nonnegative operands only | Every use has nonnegative operands; with any sign the excess reaches 2 gaps, which was not claimed |
| | `add_fast` has a bound relative to $\lvert x\rvert + \lvert y\rvert$, not to $\lvert x + y\rvert$ | No bound relative to the sum exists for this algorithm when the operands have opposite signs |

No theorem was weakened and no axiom was added.

## Open issues

Performance:

1. **Loops of independent operations with the default operators** are 1.05 to 2.7 times the
   textbook code, because the fix-up keeps compilers from vectorizing them. Two remedies are
   known: a fix-up without a floating-point operation on its unlikely path (it changes the
   listings and the proofs of F1 to F5), and the batch kernels of Milestone 2, which skip the
   fix-up and canonicalize once.
2. **A `Ball` whose radius is itself subnormal** still takes about 60 ns per operation on Intel
   processors; it needs a ball around zero with a radius near $2^{-1022}$.
3. **The libraries the brief names were not timed** (QD, CAMPARY, MultiFloats.jl, CCCL fpmp2);
   the 1.2 budget was checked against textbook code of the same algorithms. The plan times them
   at Milestone 8.
4. **The `double` chain step of the benchmarks is below the latency of the operation**, so the
   ratios of a one-limb ball to one `double` operation are upper estimates.

Proofs and statements:

5. **Sharper conditions for a finite result** are not proved, and some toy formats of the
   enumerations (those whose largest exponent is not positive) lie outside the family of formats
   the IEEE-model theorems cover: the claims hold on them, but they do not test those theorems.
6. **`ldexp` beyond the exponent range** should become a generated kernel with a proved
   statement, for one limb and for two.
7. **`constexpr`** for the two-limb products, `ldexp` and `half` on two limbs and the `Ball`
   arithmetic needs variant kernels and their proofs.
8. **Flush-to-zero**: no proof (deviation 19) and no toy format with flushing in the exhaustive
   runs; both come with the GPU backends of Milestone 3.
9. **`split` claims less than its description says**: that the two halves sum to the operand,
   not that the high half has half the precision. It is an internal building block, and Dekker's
   product met its claims in every search; the claim should say it.
10. **The "madd" sum** that Phase 0 meant to compare with the accurate sum in this milestone was
    not evaluated; the accurate sum, which is proved, stays.

Compilers and platforms:

11. **MSVC and the guard**: no rule of the language keeps it there; tests do, now also at `/Od`
    and `/O1`.
12. **`-fno-signed-zeros`** is not supported and cannot be detected at compile time with Clang.
    `kairn::self_test()` reports it only where it changes a result the self-test computes (with
    `-ffp-contract=fast` and Apple clang); alone, nothing detects it.
13. **Windows on AArch64** is not supported: the headers stop the build with MSVC there, because
    no FMA primitive has been chosen and measured, and CI has no compile-only job for it.
    **macOS on x86-64** is in no job.
14. **The generator's own C++ tests do not run on Windows**: they drive a GCC-style compiler. The
    flag sets of the two test tiers are the coverage of MSVC and clang-cl.
15. **MSVC at `/Od`** keeps its stack cookie in every function that holds a value with an array,
    as for any such type.

Tests:

16. **Faults were planted in the scalar kernels only**, not in the packed ones.
17. **The contraction setting that fuses with Apple clang** (`-O2`) was in the brute-force
    tier only for the eight `Ball` kernels of the supplementary run: the main runs built the
    contraction runners at the build's `-O3`. The quick and the full tier run every kernel at
    `-O2` on every change, and clang-cl is in those tiers and in no brute-force run.
18. **The oracle's test of a suspicious infinity** does not apply to `ball_mul_1` at 1 bit of
    precision; the exact check `tests/brute/widen.py` stands in its place there.
19. **No stratum is named for long carry chains**, which the brief lists. With two limbs a carry
    goes from one limb to the other, which the strata of cancellation, of ties and of limbs at
    the edge of the invariant exercise; a stratum of its own belongs with three limbs and more.
20. **The quick tier on the hosted Windows runners** took 71 to 154 s (three runs, MSVC and
    clang-cl), over the two-minute budget in half of them; the Linux and macOS jobs are under it,
    and on the Windows test machine it took 63 to 71 s. Since 2026-11-20 each cross-check runs the
    generator of cases, the judge and the guards in one process, without dropping a check
    ([Testing](../testing.md#each-cross-check-in-one-process)): 57 to 58 s on the Windows test
    machine, and on the hosted runners 73 and 80 s with MSVC, 81 and 93 s with clang-cl, in the
    first two runs. A runner as slow as the slowest seen before the change would still be near
    two minutes; what is left of a compiled cross-check is mostly its runners' handling of text.

Scope:

21. **The enclosure interface of `Ball`** (`lower`, `upper`, directed conversions of the bounds,
    `contains`, the certain signs, `hull`, `intersection`, `split`) is not there; it needs
    kernels with proofs and arrives with `Interval` in Milestone 2.
22. **The generator is 4 973 lines** against a budget of 1 500 to 2 000 in Phase 0; the four
    printers that matter for trust are 2 004. It gained a SIMD printer, an IEEE-model printer,
    the rule of the scalar branch and the counts of the object code.
23. **Doxygen describes the public headers only**; the pages beyond the skeleton (concepts,
    about, citation, changelog) come with later milestones.

## Decided by the owner

The first version of this section asked five questions. The owner answered four on 2026-11-20;
the fifth was put as a default and not objected to.

1. **The default for overflow (decision D5): kept.** The default operators handle overflow,
   infinities and NaN; `kairn::finite::` does not, and costs less in loops. A program that
   overflows gets an infinity instead of a number that looks valid, the cost in dependent chains
   is nil, and the loops where it costs are the ones the batch kernels of Milestone 2 are for.
2. **The brute-force tier, nightly** (deviation 20): **on the hosted runners**, with a budget of
   under two hours per platform (`nightly.yml`), and the full runs on the test machines before
   each milestone report, as now.
3. **The site is published** at <https://danielepanozzo.github.io/kairn/>, from every push to
   `main`.
4. **Two items of the brief that had no milestone go into Milestone 2**: the building blocks
   (`two_sum`, `two_prod`, the directed steps) become public, and constants are built at compile
   time from an integer or a rational with their error bound. The enclosure interface of `Ball`
   arrives there too, with `Interval`.
5. **The quick tier on the hosted Windows runners** (open issue 20): each cross-check runs in
   one process since 2026-11-20, which loses no check; the test step of those two jobs took 73
   to 93 s in the first two runs. Faster parsing and printing in the runners is the next step
   if the hosted runs come near the budget again.

Milestone 2 adds `Interval`, `BallVector` and the batch kernels, and ends with a pull request to
the first client; deviation 19 adds work to Milestone 3.
