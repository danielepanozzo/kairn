# Benchmarks, Milestone 1

The measurements Milestone 1 owes ([Plan](../design/phase0/plan.md#performance-targets),
[D5](../design/phase0/decisions.md#d5-non-finite-results)): what the opaque product costs, what the
fix-up for non-finite results costs, what a `Ball` operation costs next to its center's operation,
how Kairn compares with textbook double-word arithmetic, and what `float` limbs change. They time
the final code of Milestone 1 as a client gets it: the public operators of `Expansion` and `Ball`,
`kairn::finite::`, and the generated kernels of `include/kairn/gen/`, scalar and packed. Three
machines, nine compiler configurations, three runs of each, `double` and `float` limbs,
2026-11-19, at commit `f26e4c2`: the library of `6f89054` (whose kernels and headers are those of
`b7a1fbb`) and the harness that times it. The harness and the exact commands are in
[`bench/`](https://github.com/danielepanozzo/kairn/tree/main/bench); the measurements, one JSON
file per run, in
[`results/milestone1/bench/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone1/bench).

This page replaces a first measurement, made several commits earlier, which timed the fix-up and
the second radius design of `Ball` as hand-written props next to the library's first radius design.
[What changed](#what-changed-since-the-first-measurement) says which of its conclusions no longer
hold.

"M3", "Zen 2" and "i5" are the three machines ([How it was measured](#how-it-was-measured)). A
**loop** is a loop of independent operations over arrays in L1, timed per operation; a **chain**
is a dependent chain (a running sum, a running product of factors near 1, or a Horner evaluation
`p = p * h + c[i]`), timed per step. Every time is the minimum over 31 samples of about 4 ms; every
ratio is a ratio of minima within one run; a range is the lowest and highest value over the three
runs of the configurations named, and where a compiler's `-O2` and `-O3` differ by more than 0.05
they are given apart.

## The answers

### 1. The opaque product

Writing $\mathrm{RN}(ab)$ as `fma(a, b, +0.0)` instead of `a * b`:

- **costs nothing on the M3**, where an FMA and a multiplication both take 4 cycles: every ratio
  is between 0.93 and 1.06, except GCC 16's loop of `mul_2_1` (0.63 at -O2, 1.11 at -O3),
  where the vectorizer decides differently for the two twins, not the product;
- **costs 7 to 13% on Zen 2 in a product chain** (`mul_2_2` 8 to 9%, `mul_2_1` 12 to 13%,
  `ball_mul_2` 7%), 2 to 5% in a Horner evaluation, 1 to 12% in vectorized loops (32% in GCC's
  loops of `two_prod`), and 17 to 25% in GCC 13 -O2's scalar loops of `mul_2_1`, `mul_2_2` and
  `ball_mul_2`. An FMA takes 5 cycles there and a multiplication 3; where the product is the
  whole chain the ratio shows it: 1.65 to 1.66 for a chain of one-limb products, 1.56 to 1.59 for
  a chain of `two_prod`;
- **costs 10 to 12% in scalar chains on the i5 with MSVC, 21% in a packed `mul_2_2` loop, and
  nothing in its scalar loops**, where the plain variants are the slower ones (0.67 to 0.98). A
  chain of `two_prod` costs 1.85 to 1.87, which comes from MSVC's code for `fma_rn` rather than
  from the product ([below](#what-the-machine-code-shows)).

| Opaque over plain | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `mul_2_2`, scalar loop | 0.98 to 0.99 | 1.00 to 1.01 | 1.24 to 1.25 (-O2), 1.09 (-O3) | 1.07 (-O2), 1.02 (-O3) | 0.98 |
| `mul_2_2`, packed loop | 1.01 to 1.02 | 1.00 to 1.01 | 1.09 | 1.06 to 1.07 | 1.21 |
| `mul_2_1`, scalar loop | 0.98 to 1.02 | 0.63 (-O2), 1.11 (-O3) | 1.18 (-O2), 1.08 (-O3) | 1.07 to 1.08 | 0.86 |
| `mul_2_1`, packed loop | 0.96 to 1.00 | 1.01 | 1.08 to 1.12 | 1.07 to 1.08 | 0.91 |
| `two_prod`, scalar loop | 0.93 to 0.94 (-O2), 1.00 (-O3) | 0.99 to 1.01 | 1.00 (-O2), 1.32 (-O3) | 1.00 to 1.02 | 0.67 |
| `two_prod`, packed loop | 0.98 to 1.03 | 0.98 to 1.00 | 1.32 to 1.33 | 1.04 to 1.05 | 0.88 to 1.07 |
| `ball_mul_2`, scalar loop | 1.01 to 1.02 | 1.02 | 1.17 (-O2), 1.03 (-O3) | 1.01 to 1.02 | 0.98 |
| `ball_mul_2`, packed loop | 1.02 to 1.06 | 1.01 to 1.02 | 1.04 | 1.01 to 1.02 | 1.01 |
| product chain, `mul_2_2` | 1.00 | 1.00 | 1.08 | 1.09 | 1.10 |
| product chain, `mul_2_1` | 1.00 to 1.02 | 1.00 to 1.03 | 1.12 to 1.13 | 1.12 to 1.13 | 1.12 |
| product chain, `ball_mul_2` | 1.00 | 1.00 | 1.07 | 1.07 | 1.12 |
| packed product chain, `mul_2_2` | 0.97 to 1.06 | 0.99 to 1.06 | 1.08 | 1.08 to 1.09 | 1.00 |
| Horner, 2 limbs | 0.97 to 1.00 | 1.00 | 1.03 to 1.04 | 1.03 | 1.04 |
| Horner, balls | 0.98 to 1.00 | 1.00 | 1.02 | 1.05 | 1.07 |
| chain of `two_prod` | 0.96 to 1.05 | 0.96 to 1.01 | 1.58 to 1.59 | 1.56 | 1.85 to 1.87 |
| chain of one-limb products, `mul_1_1` over `double` | 1.00 to 1.03 | 0.99 to 1.00 | 1.65 to 1.66 | 1.66 | 1.00 |

The cost is small where it is not zero, and it buys the guarantee that no compiler can fuse a
product into a neighbor ([Environment](../design/phase0/environment.md#contraction)).

### 2. The fix-up for non-finite results

The public operators of `Expansion<double, 2>` call the full kernels (core and fix-up);
`kairn::finite::` calls the cores. On the same arrays of numbers, the operator over
`kairn::finite::`:

| Operator over `kairn::finite::` | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `x + y`, loop | 1.65 to 1.68 | 1.14 to 1.18 | 1.18 (-O2), 2.23 to 2.24 (-O3) | 1.18 to 1.19 | 1.08 |
| `x * y`, loop | 1.37 to 1.40 | 1.54 to 1.55 | 1.27 to 1.28 (-O2), 1.96 (-O3) | 1.53 to 1.54 | 1.33 to 1.34 |
| `x + a`, loop | 1.73 to 1.77 | 1.85 to 1.90 | 1.23 to 1.24 (-O2), 2.59 to 2.60 (-O3) | 1.16 to 1.17 | 1.14 |
| `x * a`, loop | 1.39 to 1.43 | 1.52 | 1.50 (-O2), 2.28 to 2.29 (-O3) | 1.48 to 1.49 | 1.52 |
| `add_fast`, loop | 1.53 to 1.56 | 1.43 to 1.49 (-O2), 1.66 to 1.67 (-O3) | 1.23 (-O2), 2.33 to 2.34 (-O3) | 1.32 to 1.33 | 1.13 |
| `x + y`, chain | 1.00 to 1.06 | 1.00 to 1.07 | 1.01 to 1.02 | 1.01 to 1.02 | 1.02 |
| `x * y`, chain | 0.99 | 1.03 | 1.04 | 1.00 | 0.96 |
| `x + a`, chain | 0.98 to 0.99 | 1.01 | 1.00 to 1.01 | 1.00 | 1.04 |
| `x * a`, chain | 1.02 to 1.07 | 1.03 to 1.04 | 1.01 | 1.03 to 1.04 | 0.94 |
| Horner, two-limb `h`, `c` | 0.97 to 0.99 | 1.02 to 1.03 | 1.01 to 1.02 | 1.01 | 1.00 to 1.01 |
| Horner, one-limb `h`, `c` | 0.99 to 1.00 | 1.03 | 1.03 | 0.99 to 1.00 | 0.97 to 0.98 |

- **In a chain the fix-up costs at most 7%**, on every machine and compiler (M3 0.97 to 1.07, Zen 2
  0.99 to 1.04, the i5 0.94 to 1.04). The generator puts it behind a branch that is predicted and
  whose test is off the critical path.
- **In a loop it costs what the compiler's vectorization makes of the two loops.** Where neither
  is vectorized (MSVC, GCC 13 -O2, GCC 16 for `x + y`) it is 8 to 52%; where both are (Clang 18
  for `x + y` and `x * y`, the operator with blends), 18 to 54%; where the core's loop is
  vectorized and the operator's is not (Apple clang, GCC 13 -O3, GCC 16 for `x * y`), 1.37 to
  2.60 times. The other loops lie in between: Clang 18's `x + a` and `x * a` 1.16 to 1.49, GCC
  16's `x + a`, `x * a` and `add_fast` 1.43 to 1.90. [The machine
  code](#what-the-machine-code-shows) says which loop is vectorized where.

Packed code (`avx2.hpp`, `neon.hpp`) has no branch: the full kernels compute the fix-up in every
lane and blend.

| Packed full kernel over packed core | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `add_2_2`, loop | 1.54 | 1.33 to 1.35 | 1.21 | 1.16 to 1.17 | 1.27 |
| `mul_2_2`, loop | 1.96 to 1.98 | 1.70 | 1.97 to 1.98 | 1.74 to 1.75 | 2.05 |
| `add_2_1`, loop | 1.93 to 1.94 | 1.63 | 1.45 | 1.32 to 1.33 | 1.71 to 1.73 |
| `mul_2_1`, loop | 2.35 to 2.40 | 1.88 to 1.89 | 2.22 to 2.27 (-O2), 2.30 to 2.32 (-O3) | 2.04 to 2.05 | 2.33 to 2.34 |
| `add_2_2`, chain | 1.21 to 1.25 | 1.25 to 1.28 | 1.17 | 1.11 | 1.53 |
| `mul_2_2`, chain | 1.23 to 1.36 | 1.13 to 1.20 | 1.08 | 1.06 | 1.53 |
| `add_2_1`, chain | 1.40 to 1.43 | 1.43 to 1.50 | 1.26 to 1.27 | 1.14 | 1.94 to 1.95 |
| `mul_2_1`, chain | 1.49 to 1.53 | 1.63 to 1.64 | 1.45 | 1.26 to 1.27 | 2.06 |
| Horner, 2 limbs | 1.22 to 1.26 | 1.20 to 1.21 | 1.10 | 1.08 | 1.46 |

**D5's estimate, 10 to 20% on a 2-limb addition, per machine:**

| `x + y` over `kairn::finite::add` | M3 | Zen 2 | i5 |
|---|---|---|---|
| scalar, chain | holds: 0 to 7% | holds: 1 to 2% | holds: 2% |
| scalar, loop | holds with GCC 16 (14 to 18%); not with Apple clang (65 to 68%) | holds with GCC 13 -O2 and Clang 18 (18 to 19%); not with GCC 13 -O3 (2.23 to 2.24 times) | holds: 8% |
| packed `add_2_2`, loop | above: 33 to 54% | at the upper edge: 16 to 21% | above: 27% |
| packed `add_2_2`, chain | above: 21 to 28% | holds: 11 to 17% | above: 53% |

So the estimate holds for scalar code in a chain on every machine, for scalar loops where the
compiler treats the operator's loop as it treats the core's, and for packed code on Zen 2 only (at
its upper edge in a loop). A multiplication is shorter than an addition and suffers more: the
packed `mul_2_2` costs 70 to 105% more with the fix-up in a loop and 6 to 53% in a chain, the
scalar `x * y` 27 to 96% in a loop.

**The branch against the listing's selects.** The generator emitted the listing's selects for
scalar code until the first measurement showed what they cost in a chain; it now emits the branch.
On separate arrays of limbs, the generated kernel (branch) and the listing (selects, a prop of the
harness) over the core:

| Scalar, separate arrays: over the core | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `add_2_2` loop, branch (generated) | 2.07 to 2.08 | 2.02 to 2.20 | 1.17 to 1.18 (-O2), 4.65 to 4.68 (-O3) | 1.16 | 4.24 to 4.25 |
| `add_2_2` loop, selects | 1.59 to 1.63 | 2.59 (-O2), 2.40 to 2.44 (-O3) | 1.21 (-O2), 4.69 to 4.71 (-O3) | 1.16 to 1.17 | 6.13 to 6.14 |
| `mul_2_2` loop, branch | 2.03 to 2.11 | 2.20 to 2.22 | 1.27 to 1.28 (-O2), 6.05 to 6.07 (-O3) | 1.72 to 1.74 | 1.38 |
| `mul_2_2` loop, selects | 2.06 to 2.15 | 3.06 to 3.07 (-O2), 2.77 (-O3) | 1.64 (-O2), 7.25 to 7.26 (-O3) | 1.73 to 1.75 | 2.95 to 2.96 |
| `add_2_2` chain, branch | 0.93 to 0.99 | 0.97 to 1.01 | 1.01 to 1.02 | 1.00 to 1.01 | 1.04 |
| `add_2_2` chain, selects | 1.32 to 1.42 | 1.05 to 1.08 | 1.01 | 1.10 | 1.76 |
| `mul_2_2` chain, branch | 0.99 to 1.01 | 1.03 | 1.04 | 1.00 to 1.01 | 1.02 to 1.03 |
| `mul_2_2` chain, selects | 1.35 to 1.37 | 1.01 to 1.02 | 1.01 | 1.01 | 1.54 to 1.55 |
| Horner, branch | 0.99 to 1.02 | 1.02 to 1.03 | 1.01 to 1.02 | 1.01 | 1.04 to 1.05 |
| Horner, selects | 1.32 to 1.35 | 1.04 to 1.06 | 1.00 | 1.05 | 1.61 |
| `ball_add_2` chain, branch | 1.02 to 1.06 | 0.98 to 1.00 | 1.01 | 1.00 to 1.01 | 1.00 |
| `ball_add_2` chain, selects | 1.81 to 1.88 | 1.07 | 1.27 to 1.28 (-O2), 1.00 to 1.01 (-O3) | 1.05 to 1.06 | 2.36 |
| `ball_mul_2` chain, branch | 1.00 to 1.01 | 1.00 to 1.01 | 1.00 to 1.01 | 1.02 | 0.98 |
| `ball_mul_2` chain, selects | 1.91 to 1.92 | 1.11 to 1.14 | 1.32 (-O2), 1.02 to 1.03 (-O3) | 1.03 | 1.78 to 1.79 |

In a chain the selects cost up to 1.92 times the core with Apple clang and 2.36 times with MSVC;
the branch at most 1.06. In a loop the branch is as fast as the selects or faster everywhere
except with Apple clang, which vectorizes the selects of `add_2_2` (1.59 to 1.63) and not the
branch (2.07 to 2.08); MSVC vectorizes the core of `add_2_2` on separate arrays and neither full
form, hence 4.2 and 6.1.

### 3. The cost of a Ball operation

`Ball<double, 2>` and `Ball<double, 1>` with their public operators, over the operation of the
center alone (the public operator of `Expansion<double, 2>`, or one `double` operation for one
limb), on arrays of each type; then the packed kernels.

| Ball over its center | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `X + Y` over `x + y`, loop | 1.29 | 1.27 to 1.30 | 1.35 to 1.36 (-O2), 0.93 (-O3) | 1.12 | 1.31 |
| `X + Y` over `finite::add`, loop | 2.12 to 2.17 | 1.47 to 1.52 | 1.59 to 1.60 (-O2), 2.07 to 2.08 (-O3) | 1.32 to 1.33 | 1.41 |
| `X * Y` over `x * y`, loop | 1.94 to 2.01 | 1.80 to 1.81 | 1.83 to 1.84 (-O2), 1.63 to 1.64 (-O3) | 1.23 to 1.24 | 2.57 to 2.58 |
| `X * Y` over `finite::mul`, loop | 2.72 to 2.76 | 2.79 to 2.80 | 2.34 (-O2), 3.20 (-O3) | 1.90 to 1.91 | 3.43 to 3.45 |
| `X * a` over `x * a`, loop | 1.67 to 1.68 | 1.71 | 1.86 to 1.87 (-O2), 1.41 to 1.42 (-O3) | 1.78 to 1.79 | 2.36 |
| `-X` over `-x`, loop | 1.23 to 1.41 (-O2), 1.67 to 1.68 (-O3) | 1.41 to 1.44 | 1.41 (-O2), 3.29 (-O3) | 2.05 | 1.08 to 1.11 |
| `X + Y` over `x + y`, chain | 0.97 to 1.04 | 0.93 to 1.00 | 1.01 | 1.02 | 1.03 |
| `X * Y` over `x * y`, chain | 1.06 | 1.02 to 1.03 | 0.97 to 0.98 | 1.02 | 1.14 |
| `X * a` over `x * a`, chain | 1.05 to 1.07 | 1.05 to 1.06 | 1.06 to 1.07 | 1.01 | 1.01 |
| Horner, balls over 2 limbs | 1.01 to 1.02 | 1.00 to 1.01 | 1.00 to 1.01 | 1.03 | 1.06 to 1.07 |
| 1 limb, `X + Y` over `double`, loop | 4.92 to 5.01 | 2.42 (-O2), 4.53 to 4.60 (-O3) | 3.25 to 3.26 (-O2), 7.44 (-O3) | 7.70 to 7.84 | 11.22 to 18.52 |
| 1 limb, `X * Y` over `double`, loop | 6.26 to 6.33 | 3.20 (-O2), 5.62 (-O3) | 4.07 (-O2), 9.55 to 9.56 (-O3) | 8.84 to 8.85 (-O2), 8.69 to 8.79 (-O3) | 15.59 to 22.61 |
| 1 limb, `X + Y` over `double`, chain | 7.11 to 7.43 | 5.39 to 5.58 | 4.86 to 4.91 | 4.85 to 4.87 | 11.74 to 11.77 |
| 1 limb, `X * Y` over `double`, chain | 6.53 to 6.65 | 7.14 to 7.15 (-O2), 6.50 (-O3) | 10.13 to 10.17 | 9.59 to 9.62 | 11.85 to 11.86 |
| 1 limb, `X * a` over `double`, chain | 3.94 to 3.97 | 4.52 to 4.53 | 6.04 to 6.06 | 5.65 to 5.69 | 7.32 to 7.33 |
| packed `ball_add_2` over `add_2_2` (full), loop | 1.31 to 1.32 | 1.34 to 1.39 | 1.58 | 1.54 to 1.55 | 1.53 |
| packed `ball_mul_2` over `mul_2_2` (full), loop | 1.61 to 1.63 | 1.71 to 1.72 | 1.79 to 1.80 | 1.93 | 1.88 to 1.89 |
| packed `ball_scale_2` over `mul_2_1` (full), loop | 1.52 | 1.63 to 1.64 | 1.79 to 1.80 | 1.91 | 1.89 |
| packed `ball_neg_2` over `neg_2`, loop | 1.55 to 1.56 | 1.60 (-O2), 2.14 (-O3) | 1.49 (-O2), 1.56 (-O3) | 1.56 to 1.57 | 1.25 to 1.39 |
| packed `ball_add_2` over `add_2_2` (full), chain | 1.30 to 1.39 | 1.20 to 1.29 | 1.34 | 1.33 | 1.40 to 1.41 |
| packed `ball_mul_2` over `mul_2_2` (full), chain | 1.40 to 1.45 | 1.43 to 1.54 | 1.45 to 1.46 | 1.35 to 1.36 | 1.45 |
| packed `ball_mul_2` over `mul_2_2` (core), loop | 3.18 to 3.19 | 2.92 | 3.55 | 3.35 to 3.37 | 3.87 |
| packed `ball_add_1` over `double` addition, loop | 3.74 to 3.76 (-O2), 3.63 to 3.64 (-O3) | 3.06 to 3.07 | 5.73 to 5.78 | 4.01 to 4.05 | 5.40 to 5.45 |
| packed `ball_mul_1` over `double` product, loop | 4.66 to 4.78 | 4.01 | 8.42 to 8.46 (-O2), 6.54 to 6.58 (-O3) | 6.10 to 6.16 | 5.02 to 5.87 |

- **In a chain a ball of two limbs costs what its center costs**: `X + Y` 0.93 to 1.04 times
  `x + y`, `X * Y` 0.97 to 1.14 times `x * y`, `X * a` 1.01 to 1.07 times `x * a`, a Horner
  evaluation 1.00 to 1.07 times. The radius takes three to five operations beside the center; only
  the last two wait for the center's magnitude.
- **In a loop the radius's operations show**: `X + Y` 1.12 to 1.36 times `x + y`, `X * Y` 1.23 to
  2.58 times `x * y`, and more over `kairn::finite::` where the compiler vectorizes the center's
  core and not the ball's operator. GCC 13 -O3 vectorizes the ball's operator and not the center's,
  which makes `X + Y` faster than `x + y` there (0.93).
- **A ball of one limb costs 4 to 12 times one `double` operation in a chain** (`X + Y` 4.9 to 11.8,
  `X * Y` 6.5 to 11.9, `X * a` 3.9 to 7.3): a `double` step is one operation, a ball step a center
  and a radius of four to six operations, and the radius's chain of fused operations is the longer.
  These ratios are upper estimates: the `double` chain step they divide by is measured in a chain
  of 256 steps, which the processor overlaps with the next call's, so it is below the latency of
  the operation (0.39 ns for an addition on the M3, whose latency in a long chain is about 0.75 ns:
  [Compile times and other costs](costs-milestone1.md#the-environment-check-in-detail)). The chains of the
  two-limb operations are 10 to 20 times longer per step and are hardly affected.
- **Packed**, a ball costs 1.3 to 1.6 times its center for a sum and 1.6 to 1.9 times for a
  product, both with the fix-up; 2.9 to 3.9 times the product's core.
- **`-X`** costs 1.08 to 3.29 times `-x` in a loop: a loop of copies with a sign flip, 24 bytes
  per number against 16, whose code differs most with GCC 13 -O3 (a loop of 37 instructions
  against 10). Its chain is not measured (`-(-x)` is no computation).

The full Ball kernels over their cores, the fix-up's share of the above:

| Full Ball kernel over its core | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `X + Y` over `ball_add_2` core, loop | 1.68 to 1.70 | 1.77 (-O2), 1.68 (-O3) | 1.23 (-O2), 1.60 to 1.61 (-O3) | 1.00 to 1.01 | 1.27 |
| `X * Y` over `ball_mul_2` core, loop | 1.61 | 1.62 to 1.64 | 1.29 to 1.30 (-O2), 1.64 (-O3) | 1.19 to 1.20 | 1.40 to 1.42 |
| `X * a` over `ball_scale_2` core, loop | 1.58 to 1.61 | 1.73 to 1.74 | 1.47 (-O2), 1.20 to 1.23 (-O3) | 1.42 to 1.43 | 1.65 |
| `X + Y`, chain | 1.02 to 1.06 | 0.98 to 1.00 | 1.02 | 1.01 | 1.01 |
| `X * Y`, chain | 0.99 to 1.01 | 1.00 to 1.01 | 1.00 to 1.01 | 1.01 to 1.02 | 0.97 |
| `X * a`, chain | 1.02 to 1.04 | 1.03 to 1.04 | 1.04 to 1.05 | 1.01 | 0.89 |
| 1 limb, `X + Y`, loop | 1.40 | 1.55 (-O2), 1.30 to 1.34 (-O3) | 1.89 to 1.90 (-O2), 1.70 (-O3) | 1.82 to 1.84 | 2.59 to 2.60 |
| 1 limb, `X * Y`, loop | 1.78 to 1.81 | 1.36 (-O2), 1.61 (-O3) | 1.55 to 1.57 (-O2), 1.89 (-O3) | 1.37 to 1.38 | 1.64 to 1.65 |
| 1 limb, `X + Y`, chain | 1.20 to 1.21 | 1.15 to 1.16 | 1.02 to 1.03 | 1.03 | 1.24 to 1.25 |
| 1 limb, `X * Y`, chain | 1.08 to 1.10 | 1.15 to 1.16 (-O2), 1.05 to 1.06 (-O3) | 1.09 to 1.10 | 1.04 | 1.01 |
| packed `ball_add_2`, loop | 1.66 to 1.67 | 1.50 to 1.56 | 1.60 to 1.61 | 1.46 to 1.47 | 1.79 |
| packed `ball_mul_2`, loop | 1.80 to 1.81 | 1.63 to 1.64 | 1.93 to 1.94 | 1.83 to 1.84 | 2.62 |
| packed `ball_add_2`, chain | 1.60 to 1.72 | 1.63 to 1.66 | 1.53 to 1.54 | 1.44 to 1.45 | 2.13 to 2.14 |
| packed `ball_mul_2`, chain | 1.71 to 1.77 | 1.57 to 1.63 | 1.50 to 1.51 | 1.39 | 1.98 to 1.99 |

In a chain a full Ball kernel of two limbs takes 0.89 to 1.06 times as long as its core, one of
one limb 1.01 to 1.25 times. In a loop the public operators take 1.00 to 1.77 times as long as
the cores for two limbs and up to 2.60 times for one, and the packed full Ball kernels 1.46 to
2.62 times in a loop and 1.39 to 2.14 times in a chain, where their blends wait for the radius.

In absolute terms:

| Times (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `X + Y`, `Ball<double, 2>`, loop | 1.95 to 1.99 | 2.02 to 2.04 | 4.1 to 6.01 | 3.03 to 3.05 | 3.07 to 3.08 |
| `X * Y`, `Ball<double, 2>`, loop | 1.5 to 1.57 | 1.53 | 3.75 to 4.24 | 2.42 to 2.45 | 3.26 to 3.27 |
| `X + Y`, chain step | 7.3 to 8.12 | 7.09 to 7.16 | 10.4 to 10.5 | 10.2 to 10.3 | 5.23 to 5.24 |
| `X * Y`, chain step | 5.57 to 6.13 | 5.51 to 5.58 | 8.11 to 8.14 | 8.26 to 8.29 | 6.6 |
| packed `ball_add_2`, per ball | 1.41 to 1.48 | 1.27 to 1.29 | 1.81 to 1.82 | 1.71 to 1.72 | 1.06 |
| packed `ball_mul_2`, per ball | 1.14 to 1.19 | 1.02 to 1.03 | 1.34 to 1.35 | 1.28 to 1.29 | 0.885 to 0.886 |
| `x + y`, loop | 1.51 to 1.54 | 1.56 to 1.59 | 4.41 to 4.44 | 2.7 to 2.72 | 2.35 |
| `x * y`, loop | 0.769 to 0.78 | 0.846 to 0.85 | 2.29 to 2.31 | 1.96 to 1.97 | 1.26 to 1.27 |
| `x + y`, chain step | 7.04 to 7.86 | 7.12 to 7.67 | 10.3 to 10.4 | 10 to 10.1 | 5.08 |
| `x * y`, chain step | 5.27 to 5.77 | 5.41 to 5.42 | 8.31 to 8.36 | 8.07 to 8.12 | 5.77 |
| `double` addition, chain step | 0.365 to 0.391 | 0.459 to 0.475 | 0.787 to 0.794 | 0.791 to 0.795 | 0.285 |
| `x + a`, chain step | 4.39 to 4.91 | 4.47 to 4.48 | 6.55 to 6.59 | 6.51 to 6.56 | 3.28 |

On the i5 the chains of `X + Y` and `X * Y` take 5.2 and 6.6 ns per step. Before the last
constant of the radius contained the smallest normal number they took 30 to 35 ns there, from the
assist that a fused operation with a subnormal addend takes on that processor
([the radius, second design](../design/milestone1.md#the-radius-second-design)); the M3 and Zen 2
had no such penalty.

For scale, MPFR's 106-bit multiplication (correctly rounded, not rigorous) takes 7.0 to 7.3 ns on
the M3 and 15.2 to 15.6 ns on Zen 2 in a loop: a loop of `X * Y` is 4.6 to 4.9 and 3.6 to 6.4
times faster, and a chain of `X * Y` 1.2 to 1.4 and 1.9 times faster than a chain of MPFR
products.

### 4. Against textbook double-word arithmetic, and the 1.2× budget

The baseline is DWPlusFP, SloppyDWPlusDW, AccurateDWPlusDW, DWTimesFP3 and DWTimesDW3 with an FMA,
written from the listings of [JMP17](../design/phase0/references.md#jmp17) (the same algorithms as
Kairn's), with a plain multiplication, no guard, no fix-up and contraction off, on the same arrays
of `Expansion<double, 2>`. The brief asks for "within ~1.2× of the fastest" for non-rigorous
operations.

| `kairn::finite::` over textbook, double | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `x + y`, loop | 1.00 to 1.01 | 0.98 to 1.05 | 0.99 to 1.02 | 0.99 to 1.00 | 0.98 to 0.99 |
| `x * y`, loop | 1.01 | 1.00 | 1.26 to 1.27 (-O2), 1.10 (-O3) | 1.04 to 1.05 | 0.91 to 0.92 |
| `x + a`, loop | 1.07 to 1.08 | 0.92 to 0.94 | 1.14 to 1.15 (-O2), 1.05 to 1.06 (-O3) | 1.14 to 1.15 | 1.11 to 1.12 |
| `x * a`, loop | 1.00 to 1.03 | 0.95 to 0.96 (-O2), 1.00 to 1.01 (-O3) | 1.18 (-O2), 1.03 to 1.04 (-O3) | 1.07 | 0.93 to 0.94 |
| `add_fast`, loop | 1.00 | 0.96 to 1.00 | 0.97 to 1.00 | 0.99 to 1.00 | 1.00 |
| `x + y`, chain | 0.99 to 1.01 | 0.99 to 1.05 | 1.00 | 1.00 to 1.01 | 1.00 |
| `x * y`, chain | 1.00 to 1.02 | 1.00 | 1.08 | 1.09 | 1.15 |
| `x + a`, chain | 1.02 to 1.06 | 1.02 | 1.04 to 1.05 | 1.04 to 1.05 | 1.00 to 1.01 |
| `x * a`, chain | 0.99 to 1.00 | 1.00 | 1.12 to 1.13 | 1.13 | 1.20 |
| `add_fast`, chain | 1.02 | 0.99 | 1.00 | 1.00 | 1.00 |
| Horner, two-limb `h`, `c` | 1.00 to 1.01 | 1.00 | 1.05 | 1.03 to 1.04 | 1.08 |
| Horner, one-limb `h`, `c` | 0.99 to 1.01 | 1.01 | 1.05 to 1.06 | 1.06 to 1.07 | 1.14 |

| operator over textbook, double | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `x + y`, loop | 1.66 to 1.68 | 1.15 to 1.19 | 1.19 (-O2), 2.23 to 2.26 (-O3) | 1.17 to 1.19 | 1.05 to 1.06 |
| `x * y`, loop | 1.39 to 1.41 | 1.54 to 1.55 | 1.61 to 1.62 (-O2), 2.14 to 2.15 (-O3) | 1.60 to 1.61 | 1.22 |
| `x + a`, loop | 1.85 to 1.91 | 1.74 to 1.75 | 1.41 to 1.42 (-O2), 2.74 (-O3) | 1.33 to 1.34 | 1.27 |
| `x * a`, loop | 1.43 | 1.45 (-O2), 1.52 to 1.54 (-O3) | 1.77 to 1.78 (-O2), 2.37 (-O3) | 1.59 | 1.42 |
| `add_fast`, loop | 1.53 to 1.56 | 1.43 (-O2), 1.66 to 1.67 (-O3) | 1.23 (-O2), 2.26 to 2.27 (-O3) | 1.31 to 1.32 | 1.13 |
| `x + y`, chain | 1.00 to 1.07 | 0.99 to 1.05 | 1.02 | 1.02 | 1.02 |
| `x * y`, chain | 0.99 to 1.01 | 1.03 | 1.12 | 1.09 | 1.10 |
| `x + a`, chain | 1.01 to 1.05 | 1.03 | 1.05 | 1.04 to 1.05 | 1.04 |
| `x * a`, chain | 1.02 to 1.06 | 1.03 to 1.04 | 1.14 | 1.17 | 1.13 |
| `add_fast`, chain | 1.01 to 1.02 | 1.00 to 1.01 | 0.99 to 1.00 | 1.01 to 1.02 | 1.05 |
| Horner, two-limb `h`, `c` | 0.98 to 0.99 | 1.02 to 1.03 | 1.07 | 1.05 | 1.08 |
| Horner, one-limb `h`, `c` | 0.98 to 1.01 | 1.03 | 1.09 | 1.06 | 1.11 |

- **The cores (`kairn::finite::`) meet 1.2** on every configuration but one, and tie on one: GCC
  13 -O2's loop of `x * y` on Zen 2 is 1.26 to 1.27 (the opaque product's latency, in a loop GCC
  does not vectorize), and the i5's chain of `x * a` is 1.20. On the M3 every ratio is between
  0.92 and 1.08. Where they cost more than the textbook it is the opaque product in a product
  chain (8 to 20% on Zen 2 and the i5) and, for `x + a`, the guard of the one-limb operand (an
  addition of zero: up to 15% in a loop, 6% in a chain).
- **The operators meet 1.2 in chains** (0.98 to 1.17 on every configuration) **and not in
  loops**: 1.05 to 2.74 times the textbook loop. Within 1.2 in a loop are only `x + y` with GCC 16,
  Clang 18 and GCC 13 -O2 (1.15 to 1.19) and `x + y` and `add_fast` with MSVC (1.05 to 1.13). That
  is the price of IEEE-like results in loops of independent operations, and the reason D5 keeps
  the fix-up out of the batch kernels.

MPFR at 106 bits, for scale (installed on the M3 and on Zen 2, not on the i5): in a loop it is 3.7
to 13 times slower than `kairn::finite::`; in a chain 0.85 to 2.0 times, because a two-limb
addition is a long chain of dependent operations while MPFR's integer code is not: on the M3 a
chain of MPFR additions is faster than a chain of `add_2_2` (0.87 to 0.94), and a Horner
evaluation too (0.85 to 0.94).

### 5. `float` limbs

`Expansion<float, 2>`, `Ball<float, 2>` and `Ball<float, 1>`, measured as the `double` ones (the
radii about $2^{-40}$ of the centers):

| `float` limbs | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `x + y` over `finite::`, loop | 3.37 to 3.42 | 1.18 to 1.22 | 1.18 to 1.19 (-O2), 4.67 to 4.68 (-O3) | 1.12 | 1.12 |
| `x * y` over `finite::`, loop | 2.82 to 2.84 | 3.25 to 3.31 | 1.37 (-O2), 3.05 (-O3) | 1.34 | 1.28 |
| `x + y` over `finite::`, chain | 1.00 to 1.06 | 1.00 to 1.04 | 1.02 | 0.99 | 1.05 |
| `x * y` over `finite::`, chain | 0.99 to 1.01 | 1.01 to 1.02 | 1.03 | 1.01 to 1.02 | 1.11 |
| `X + Y` over `x + y`, loop | 1.29 to 1.31 | 1.17 to 1.30 | 1.32 (-O2), 0.92 to 0.93 (-O3) | 1.28 to 1.29 | 1.25 to 1.26 |
| `X * Y` over `x * y`, loop | 1.95 to 2.02 | 1.79 to 1.83 | 1.88 to 1.90 (-O2), 1.93 to 1.94 (-O3) | 1.55 | 2.19 |
| `X + Y` over `x + y`, chain | 0.97 to 1.03 | 0.94 to 1.01 | 1.01 to 1.02 | 1.00 | 0.99 |
| `X * Y` over `x * y`, chain | 1.02 to 1.04 | 1.04 to 1.05 | 0.98 | 0.99 to 1.00 | 1.03 |
| `float` over `double`: `x + y`, loop | 0.99 to 1.01 | 1.01 to 1.06 | 1.00 | 1.57 | 1.04 to 1.05 |
| `float` over `double`: `x * y`, loop | 0.99 to 1.00 | 1.04 to 1.06 | 0.91 | 1.26 | 0.98 |
| `float` over `double`: `x + y`, chain | 0.99 to 1.02 | 0.95 to 1.00 | 1.00 | 1.25 to 1.26 | 1.03 |
| `float` over `double`: `x * y`, chain | 0.97 to 0.99 | 0.96 | 1.00 | 1.16 | 0.94 |
| `float` over `double`: `X + Y`, loop | 1.00 to 1.02 | 0.95 to 1.02 | 0.98 to 1.00 | 1.79 to 1.80 | 1.00 to 1.01 |
| `float` over `double`: `X * Y`, loop | 0.99 to 1.00 | 1.05 | 0.93 (-O2), 1.08 (-O3) | 1.57 to 1.58 | 0.83 to 0.84 |
| `float` over `double`: `X + Y`, chain | 0.96 to 1.00 | 1.01 to 1.02 | 1.00 to 1.01 | 1.23 | 0.99 |
| `float` over `double`: `X * Y`, chain | 0.95 | 0.98 | 1.00 to 1.01 | 1.12 to 1.13 | 0.84 |
| `float` over `double`: textbook `x + y`, chain | 0.99 to 1.03 | 0.98 to 1.00 | 1.00 | 1.27 | 1.00 |

| `kairn::finite::` over textbook, float | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `x + y`, loop | 1.00 to 1.04 | 0.95 to 1.06 | 1.00 (-O2), 0.94 (-O3) | 1.02 | 1.00 |
| `x * y`, loop | 1.01 to 1.02 | 1.01 to 1.02 | 1.09 to 1.10 (-O2), 1.02 to 1.03 (-O3) | 1.18 to 1.19 | 1.06 to 1.07 |
| `x + a`, loop | 1.06 to 1.07 | 0.92 to 0.94 | 1.12 to 1.13 (-O2), 1.01 (-O3) | 1.16 | 1.09 |
| `x * a`, loop | 0.98 to 1.00 | 1.00 | 1.18 (-O2), 0.90 to 0.91 (-O3) | 1.07 to 1.08 | 1.05 |
| `add_fast`, loop | 0.98 to 1.00 | 1.00 to 1.01 | 0.97 to 1.00 | 0.97 | 0.99 |
| `x + y`, chain | 1.00 to 1.05 | 0.99 to 1.02 | 1.00 | 1.01 | 1.00 |
| `x * y`, chain | 0.97 to 0.98 | 0.98 to 0.99 | 1.08 | 1.07 | 1.00 |
| `x + a`, chain | 1.02 to 1.03 | 1.02 | 1.04 to 1.05 | 1.00 | 1.00 |
| `x * a`, chain | 0.98 to 0.99 | 0.98 | 1.12 to 1.13 | 1.10 | 1.00 to 1.01 |
| `add_fast`, chain | 1.00 to 1.02 | 0.99 | 1.00 | 1.00 | 1.00 |
| Horner, two-limb `h`, `c` | 0.99 to 1.01 | 0.99 | 1.05 to 1.06 | 1.04 | 1.00 |
| Horner, one-limb `h`, `c` | 0.97 to 1.01 | 1.00 | 1.05 to 1.06 | 1.05 to 1.06 | 1.00 |

| operator over textbook, float | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `x + y`, loop | 3.37 to 3.50 | 1.16 to 1.28 | 1.18 (-O2), 4.38 to 4.41 (-O3) | 1.14 | 1.12 to 1.13 |
| `x * y`, loop | 2.87 to 2.88 | 3.27 to 3.37 | 1.50 to 1.51 (-O2), 3.13 to 3.15 (-O3) | 1.58 to 1.59 | 1.36 to 1.37 |
| `x + a`, loop | 3.74 to 3.81 | 3.59 to 3.83 | 1.39 to 1.40 (-O2), 5.20 to 5.22 (-O3) | 1.36 to 1.37 | 1.35 |
| `x * a`, loop | 2.88 to 2.95 | 3.38 to 3.39 | 1.66 to 1.67 (-O2), 3.74 (-O3) | 1.58 to 1.59 | 1.56 to 1.57 |
| `add_fast`, loop | 3.09 to 3.14 | 3.50 to 3.60 | 1.23 (-O2), 3.65 (-O3) | 1.15 to 1.16 | 1.18 |
| `x + y`, chain | 0.99 to 1.06 | 0.99 to 1.07 | 1.02 | 1.00 to 1.01 | 1.06 |
| `x * y`, chain | 0.98 | 1.00 | 1.12 | 1.08 to 1.09 | 1.11 |
| `x + a`, chain | 1.00 to 1.01 | 1.03 | 1.05 | 1.00 to 1.01 | 1.06 |
| `x * a`, chain | 0.99 to 1.01 | 1.01 | 1.14 | 1.33 to 1.34 | 1.04 to 1.05 |
| `add_fast`, chain | 0.99 to 1.02 | 1.01 | 0.99 to 1.00 | 1.00 | 1.06 to 1.07 |
| Horner, two-limb `h`, `c` | 0.99 to 1.03 | 1.00 to 1.02 | 1.06 to 1.07 | 1.03 | 1.08 |
| Horner, one-limb `h`, `c` | 0.97 to 1.00 | 1.01 | 1.09 | 1.04 to 1.05 | 1.07 |

| `float` times (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `x + y`, loop | 1.49 to 1.55 | 1.58 to 1.67 | 4.42 to 4.44 | 4.24 to 4.27 | 2.45 to 2.46 |
| `x * y`, loop | 0.768 to 0.771 | 0.877 to 0.894 | 2.08 to 2.1 | 2.47 to 2.49 | 1.24 to 1.25 |
| `X + Y`, loop | 1.95 to 2.03 | 1.93 to 2.07 | 4.09 to 5.87 | 5.45 to 5.47 | 3.09 |
| `X * Y`, loop | 1.5 to 1.56 | 1.6 to 1.61 | 3.93 to 4.06 | 3.83 to 3.85 | 2.72 to 2.73 |
| `x + y`, chain step | 7.07 to 7.86 | 7.13 to 7.66 | 10.3 to 10.4 | 12.6 | 5.23 |
| `x * y`, chain step | 5.11 to 5.71 | 5.18 to 5.21 | 8.28 to 8.32 | 9.34 to 9.4 | 5.41 |
| `X + Y`, chain step | 7.3 to 7.83 | 7.21 to 7.23 | 10.4 to 10.6 | 12.5 to 12.6 | 5.19 to 5.2 |
| `X * Y`, chain step | 5.32 to 5.82 | 5.4 to 5.46 | 8.14 to 8.19 | 9.28 to 9.33 | 5.55 to 5.57 |

- **The conclusions for `double` hold for `float`**: the fix-up costs at most 11% in a chain (one
  exception: Clang 18's chain of `x * a`, 1.21), and more in a loop wherever the compiler
  vectorizes the core and not the operator (2.8 to 4.1 times on the M3, where a vectorized core
  holds four `float` lanes per register; up to 5.2 times with GCC 13 -O3); a ball of two limbs
  costs its center in a chain (0.94 to 1.05); the cores stay within 1.2 of the textbook everywhere
  (0.90 to 1.19).
- **A `float` operation takes as long as a `double` one** in scalar code on the M3, with GCC 13 and
  with MSVC (0.83 to 1.08): it is the same number of operations, of the same latency. With Clang 18
  it takes longer (1.12 to 1.80): Clang keeps a pair of `float` limbs in one vector register and
  shuffles it at every step ([below](#what-the-machine-code-shows)). A `float` limb can gain only
  where twice as many lanes fit in a register: in a loop the compiler vectorizes, or in packed
  code, which is not measured here.

## What the machine code shows

The loops of every timed function were disassembled on every configuration (`objdump`, `dumpbin`)
and summarized by `bench/asm_summary.py`; the counts are stored next to the measurements, and
[a table below](#machine-code-of-the-throughput-loops) lists the main loops.

- **In a loop, the cost of the fix-up is whether the compiler vectorizes.** The cores' loops over
  arrays of `Expansion<double, 2>` are vectorized by Apple clang (128-bit), Clang 18 (128-bit) and
  GCC 13 -O3 (256-bit), and by GCC 16 for `x * y` only; GCC 13 -O2 and MSVC vectorize none of
  them. The operators' loops:
  - GCC 13 -O3 keeps the branch of `x + y`, `x * y`, `x + a` and `x * a` and vectorizes none of
    them, hence 1.96 to 2.60 times the core. Its unlikely path multiplies by $+\infty$, a
    floating-point operation that GCC does not execute speculatively under its default
    `-ftrapping-math`: compiled with `-fno-trapping-math`, the loops of `x + y` and `x + a` are
    vectorized (256-bit, with blends). The full Ball kernels, whose unlikely path is only selects,
    are vectorized by GCC 13 -O3 (256-bit): `X + Y` then takes 0.93 times as long as `x + y`.
  - Clang 18 turns the branch of `x + y` and `x * y` back into blends and vectorizes them (128-bit,
    two blends), hence 1.18 and 1.54; it keeps the branch of `x + a` and `x * a` and vectorizes
    neither (1.17 and 1.48).
  - Apple clang calls the fix-up in a function of its own and vectorizes no operator's loop: 1.37
    to 1.77 times the core.
  - GCC 16 on AArch64 and GCC 13 -O2 keep the branch and vectorize no operator's loop. So does
    MSVC, hence its small ratios over arrays of `Expansion` (1.08 to 1.52), where it vectorizes
    nothing, and its large ones over separate arrays of limbs (`add_2_2`: 4.2 times the core, which
    it vectorizes in 256-bit registers there).
- **In a chain the branch costs almost nothing** (at most 7%). It is predicted, and its
  comparison is off the critical path. The selects of the listing put a comparison and a select
  on it: up to 1.92 times the core with Apple clang and 2.36 times with MSVC.
- **Packed code pays for every blend.** The packed full kernels of `add_2_2` and `mul_2_2` add
  seven instructions to the core (an absolute value, a comparison, a multiplication by
  $+\infty$ and its comparison, three blends), those of the Balls ten (three comparisons, an
  `and`, six blends). Next to the nine operations of `mul_2_2` that is 70 to 105% in a loop; in a
  chain the blends sit on the critical path: 6 to 53%.
- **Clang keeps a pair of `float` limbs in one vector register.** `Expansion<float, 2>` is eight
  bytes; in a chain Clang 18 holds the running value as one 64-bit vector and, every step, extracts
  the second limb (`vmovshdup`) and inserts it back (`vinsertps`). That puts two shuffles on the
  critical path: a `float` sum chain takes 1.25 times the `double` one with Clang 18 (the textbook
  algorithm too), and 1.00 times with GCC 13. Apple clang and GCC 16 on AArch64 do not do this:
  there a `float` chain takes 0.95 to 1.02 times the `double` one.
- **The opaque product is one fused instruction everywhere**, never a call, and its cost is the
  latency of an FMA where the product is on the critical path: 5 cycles against 3 for a
  multiplication on Zen 2 (the chain of one-limb products costs 1.65 to 1.66 times), 4 against 4
  on the i5 and on the M3 (0.99 to 1.03). In packed NEON code it takes one more instruction:
  `fmla` accumulates into its destination, so a zero is rematerialized (`movi`) before each
  product.
- **MSVC's `fma_rn`** (through `_mm_set_sd`) adds a `vmovq` that clears the upper lane of every
  operand of a fused operation, and `fma_rn(a, b, -p)` becomes `vxorpd` and `vfmadd` rather than
  one `vfmsub`. In a chain of `two_prod` the product then costs 1.85 to 1.87 times the plain one,
  against 1.56 to 1.59 on Zen 2, and the radius chain of a `Ball` carries a `vmovq` between its
  two fused operations.

## What the generator could do better

Not acted on here; each item rests on the measurements above, and none has been tried.

1. **Packed fix-up behind a test of all lanes.** The packed full kernels compute the fix-up in
   every lane and blend: 16 to 54% of `add_2_2` and 70 to 105% of `mul_2_2` in a loop, 11 to 53%
   and 6 to 53% in a chain. Testing the finiteness mask once (`vmovmskpd` or `vptest` on AVX2, a
   horizontal reduction on NEON) and branching around the blends when every lane is finite would
   leave a comparison and a predicted branch on the common path, which is what the scalar branch
   costs in a chain (at most 7%). It would make packed code a third emission form, with the same
   outputs on both paths as the scalar rule; it is unmeasured.
2. **A fix-up without floating-point arithmetic on its unlikely path.** GCC does not if-convert,
   and so does not vectorize, a loop whose unlikely path multiplies by $+\infty$, under its default
   `-ftrapping-math`: GCC 13 -O3 runs the loops of `x + y`, `x * y`, `x + a` and `x * a` 1.96 to
   2.60 times as long as the cores, while it vectorizes the full Ball kernels, whose unlikely path
   has only selects, and vectorizes `x + y` and `x + a` when given `-fno-trapping-math`. The
   canonical form of a non-finite $t$ could be built from $t$'s bits (the infinity with $t$'s
   sign, or a NaN when $t$ is one) by selects and integer operations instead of `times_inf`. That
   changes the IR of the fix-up, and the proofs of F1 to F5 that rest on `times_inf`.
3. **MSVC's `fma_rn`**: `fms` spelled with `_mm_fmsub_sd`, and operands wrapped without clearing
   the upper lane, would remove a `vxorpd` and a `vmovq` per fused operation. On the i5, where an
   FMA and a multiplication take the same 4 cycles, a chain of `two_prod` costs 1.85 to 1.87 times
   its plain twin; on Zen 2, where they differ by 2 cycles, 1.56 to 1.59.
4. **Loops of independent operations want the batch kernels.** D5 keeps the fix-up out of the
   batch kernels it plans; the measurements say how much that matters. A public operator in a loop
   takes 1.08 to 2.60 times as long as `kairn::finite::`, and the packed full kernels are faster
   per number than the operators' loops (for `x + y` and `x * y` on arrays of
   `Expansion<double, 2>`: 1.1 to 1.7 times on the M3, 2.4 to 3.9 times on Zen 2 and the i5). This
   is the library's plan rather than the generator's.

## What changed since the first measurement

The first measurement timed the library of commit `82064a4` (`53f80d1` on the i5), in which the
public operators had no fix-up, the Ball kernels had the first radius design (every operation of
the radius rounded up by a step to the next number, done on the bit pattern), and the fix-up and the
second radius design existed only as props of the harness. Its conclusions, against what is
measured now:

- **The opaque product**: its conclusions stand. The ratios above were remeasured and agree with
  the first measurement within a few percent, except for `ball_mul_2`, whose radius now has one
  opaque product instead of four.
- **The fix-up in packed code**: "19 to 58% on an addition, 70 to 106% on a multiplication" was
  measured on props with the listing's blends. The generated packed kernels cost 16 to 54% on an
  addition and 70 to 105% on a multiplication in a loop, and 6 to 53% in a chain.
- **The fix-up in scalar code**: the first measurement compared the listing's selects with a branch
  and recommended the branch, inline on x86-64 and in a function of its own with Clang on AArch64.
  The generator now emits exactly that ("Emission" in
  [Milestone 1 statements](../design/milestone1.md#ieee-like-results)), and the public operators
  call it: in a chain they take 0.94 to 1.07 times as long as `kairn::finite::`. Its loop figures
  (up to 4.9 times a core with GCC 13 -O3, 4.3 to 6.2 times with MSVC) were for separate arrays of
  limbs; on those they still hold (4.65 to 4.68 and 4.24 now, the third table of
  [question 2](#2-the-fix-up-for-non-finite-results)), and a client's arrays of `Expansion` show
  the smaller ratios of the first table.
- **"The radius dominates" a Ball operation**: no longer. With the first design `ball_mul_2` cost
  13.5 to 20 times `mul_2_2` in packed loops and 3.0 to 4.4 times in a scalar product chain; with
  the second it costs 1.6 to 1.9 times a packed `mul_2_2` with its fix-up (2.9 to 3.9 times its
  core) in a loop, and `X * Y` 0.97 to 1.14 times `x * y` in a scalar product chain. A packed
  `ball_mul_2` went from 4.6 to 6.1 ns per ball to 0.89 to 1.35 ns, a packed `ball_add_2` from 2.3
  to 3.6 ns to 1.06 to 1.82 ns.
- **The full Ball kernels cost up to 2.9 times their cores in chains**: that was the listing's
  selects, which made the next center wait for the radius. With the branch the generator emits,
  the full Ball kernels of two limbs take 0.89 to 1.06 times as long as their cores in chains.
- **A scalar `ball_mul_2` is barely faster than MPFR**: no longer. A loop of `X * Y` is 3.6 to 6.4
  times faster than a loop of MPFR multiplications, a chain 1.2 to 1.9 times.
- **What the generator could do better**: item 1 (the branch) was done; item 2 (a cheaper step to
  the next number for nonnegative radii) has no object any more, since no Ball kernel steps to a
  neighbor; item 3 (MSVC's `fma_rn`) stands, above.
- **Not measured then, measured now**: `float` limbs, the public operators themselves, `x + a`,
  `x * a`, `X * a`, `-X`, and the balls of one limb.

## How it was measured

| Machine | Configurations | Conditions |
|---|---|---|
| M3: macOS arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2; `-O2` and `-O3` | macOS has no affinity: the thread asked for the user-interactive class, which runs on performance cores. Other jobs shared the machine: a run was started only when the 1-minute load average was under 10 and at most three processes used more than 30% of a core, and a run whose median spread exceeded 2% was discarded and repeated (16 runs were discarded) |
| Zen 2: Linux x86-64, AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1; `-O2` and `-O3`; `-mfma`, packed code `-mavx2 -mfma` | pinned to one logical CPU of the second socket, away from the jobs that loaded the first; `mpstat` showed its SMT sibling 99.1 to 99.8% idle on average during each run (90.9% in the worst second) |
| i5: Windows 11 x64, Intel Core i5-13500T (6 performance, 8 efficiency cores) | MSVC 19.52, `/O2 /arch:AVX2 /fp:precise` | pinned to one logical processor of a performance core (the same core for two runs, another for the third), on a shared CI machine 6 to 8% busy on average; `typeperf` showed the sibling 15 to 16% busy on average during each run, with peaks of 66 to 86% |

- **Commit**: `f26e4c2` on every machine; the JSON of every run records it.
- **Flags**: hardware FMA as `kairn::fma` gives it, contraction off (`-ffp-contract=off`; MSVC's
  `/fp:precise` does not contract), never `-ffast-math`; `NDEBUG`, so `KAIRN_CHECKS` is 0. The
  scalar fix-up is where `kairn/gen/prelude.hpp` puts it: a function of its own with Apple clang,
  inline with every other compiler.
- **Inputs**: 256 normalized two-limb numbers per operand, leading limbs $\pm[1, 2)\cdot 2^k$ with
  $k \in [-8, 8]$; radii about $2^{-80}$ of the centers ($2^{-40}$ for `float`); factors in
  $[2^{-1/4}, 2^{1/4})$; made at run time from a fixed seed, the same with every compiler. No
  overflow, underflow or subnormal operand in a timed loop. The public operators work on arrays of
  `Expansion<T, 2>`, `Ball<T, 2>`, `Ball<T, 1>` and `T` made by the public constructors; the
  generated kernels, scalar and packed, on separate arrays of limbs.
- **Loops and chains**: each a non-inlined function called through a pointer; the compiler was
  free to vectorize a scalar loop, and [the machine code](#what-the-machine-code-shows) says where
  it did. A packed chain runs one chain per lane, timed per step.
- **Checks before timing**: every timed function against the generated core on the benchmark
  inputs, bit for bit (MPFR within $2^{-100}$ per operation); the full kernels' three forms
  against each other on 8192 random and special operands each, with their results against the
  statements. None failed on any configuration ([Checks](#checks)).
- **Repeatability**: three runs of each configuration. Between two runs of one configuration, the
  minima of the median function agree within 0.5% on Zen 2 and the i5, and those of 90% of the
  functions within 1%. On the M3 the median function agrees within 0.1%, and 90% of the functions
  within 6%, except for one run of Apple clang -O2, which was 4 to 5% slower than the two others
  at the median function though its spread was within 2%; its ratios differ from theirs by 0.02 at
  the median and by more than 0.05 for one in ten (up to 0.13 in a ratio quoted above, the packed
  `mul_2_2` chain with and without the fix-up, 1.36 against 1.23 and 1.24). It is kept, and widens
  the M3's ranges. For the median function, the median of the 31 samples is within 0.3 to 0.8% of
  their minimum on Zen 2, 0.3 to 0.5% on the i5 and 0.3 to 1.7% on the M3
  ([Configurations](#configurations)). On the i5 the loops of one `double` operation over arrays
  take 0.09 to 0.15 ns and differ by up to 1.7 times between runs; a ratio against them (a ball of
  one limb over a `double` operation, in a loop) is good to that much at best.
- **Measured**: the times, the bitwise agreements, the instruction counts. **Inferred**: the
  explanations of the ratios, which are readings of the machine code, not separate measurements;
  the latencies quoted (an FMA in 5 cycles and a multiplication in 3 on Zen 2, both in 4 on the M3
  and the i5) are the vendors' figures, which the measured chains agree with.
- **Not measured**: packed `float` kernels; AVX-512 (no machine has it); GPUs; `KAIRN_CHECKS=1`;
  the fix-up in a function of its own on x86-64, or inline with Apple clang (measured with another
  harness for "Emission" in [Milestone 1 statements](../design/milestone1.md#ieee-like-results));
  subtraction, `ldexp` and comparisons; clang-cl; MPFR on Windows (not installed there); Arb.

## Tables

The tables below are printed by `python3 bench/report.py results/milestone1/bench` from the stored
files; nothing in them was typed by hand. A cell is the lowest and highest value over the three runs
of a configuration.

### Configurations

| Configuration | Machine | Compiler | Flags | Scalar fix-up | Runs | Spread: median, worst | Date, commit |
|---|---|---|---|---|---:|---|---|
| M3, Apple clang -O2 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | a function of its own | 3 | 0.7–1.7%, 8–18% | 2026-11-19, `f26e4c2` |
| M3, Apple clang -O3 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | a function of its own | 3 | 0.4–1.3%, 7–9% | 2026-11-19, `f26e4c2` |
| M3, GCC 16 -O2 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | inline | 3 | 0.3–0.9%, 9–13% | 2026-11-19, `f26e4c2` |
| M3, GCC 16 -O3 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | inline | 3 | 0.6–1.1%, 10–17% | 2026-11-19, `f26e4c2` |
| Zen 2, GCC 13 -O2 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | inline | 3 | 0.4–0.8%, 4% | 2026-11-19, `f26e4c2` |
| Zen 2, GCC 13 -O3 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | inline | 3 | 0.3–0.6%, 5–7% | 2026-11-19, `f26e4c2` |
| Zen 2, Clang 18 -O2 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | inline | 3 | 0.3–0.8%, 9–16% | 2026-11-19, `f26e4c2` |
| Zen 2, Clang 18 -O3 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | inline | 3 | 0.3–0.5%, 4–5% | 2026-11-19, `f26e4c2` |
| i5, MSVC /O2 | Windows 11 x64, Intel Core i5-13500T (6 performance and 8 efficiency cores); one logical processor of a performance core, its sibling mostly idle; a shared CI machine | MSVC 19.52.37029 | `/DWIN32 /D_WINDOWS /EHsc /O2 /Ob2 /DNDEBUG /O2 /fp:precise /arch:AVX2` | inline | 3 | 0.3–0.5%, 38% | 2026-11-19, `f26e4c2` |

### Checks

| Configuration | Functions checked bit for bit, failed | Full kernels: cases; selects vs generated, packed vs scalar; not canonical or against the statement |
|---|---:|---|
| M3, Apple clang -O2 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| M3, Apple clang -O3 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| M3, GCC 16 -O2 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| M3, GCC 16 -O3 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| Zen 2, GCC 13 -O2 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| Zen 2, GCC 13 -O3 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| Zen 2, Clang 18 -O2 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| Zen 2, Clang 18 -O3 | 245, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |
| i5, MSVC /O2 | 240, 0 | `add_2_2_full` 8192: 0, 0; 0; `mul_2_2_full` 8192: 0, 0; 0; `ball_add_2_full` 8192: 0, 0; 0; `ball_mul_2_full` 8192: 0, 0; 0 |

### 1. Opaque product over plain product

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| scalar throughput, `two_prod` | 0.93–0.94 | 1.00 | 1.00 | 0.99–1.01 | 1.00 | 1.32 | 1.01–1.02 | 1.00–1.01 | 0.67 |
| scalar throughput, `mul_2_1` | 0.98–1.02 | 1.01–1.02 | 0.63 | 1.11 | 1.18 | 1.08 | 1.07–1.08 | 1.07–1.08 | 0.86 |
| scalar throughput, `mul_2_2` | 0.99 | 0.98–0.99 | 1.01 | 1.00 | 1.24–1.25 | 1.09 | 1.07 | 1.02 | 0.98 |
| scalar throughput, `ball_mul_2` | 1.01–1.02 | 1.01 | 1.02 | 1.02 | 1.17 | 1.03 | 1.02 | 1.01–1.02 | 0.98 |
| packed throughput, `two_prod` | 0.98–1.03 | 0.98–0.99 | 1.00 | 0.98 | 1.32–1.33 | 1.32–1.33 | 1.04–1.05 | 1.04 | 0.88–1.07 |
| packed throughput, `mul_2_1` | 0.96–1.00 | 1.00 | 1.01 | 1.01 | 1.10–1.12 | 1.08 | 1.07–1.08 | 1.07–1.08 | 0.91 |
| packed throughput, `mul_2_2` | 1.01–1.02 | 1.02 | 1.00–1.01 | 1.01 | 1.09 | 1.09 | 1.07 | 1.06 | 1.21 |
| packed throughput, `ball_mul_2` | 1.02–1.06 | 1.02 | 1.01 | 1.01–1.02 | 1.04 | 1.04 | 1.01 | 1.01–1.02 | 1.01 |
| scalar product chain, `two_prod` | 1.00–1.05 | 0.96–1.01 | 0.96–1.01 | 1.00–1.01 | 1.58–1.59 | 1.59 | 1.56 | 1.56 | 1.85–1.87 |
| scalar product chain, `mul_2_1` | 1.00–1.02 | 1.00–1.02 | 1.00–1.03 | 1.00–1.03 | 1.12–1.13 | 1.12–1.13 | 1.12–1.13 | 1.12–1.13 | 1.12 |
| scalar product chain, `mul_2_2` | 1.00 | 1.00 | 1.00 | 1.00 | 1.08 | 1.08 | 1.09 | 1.09 | 1.10 |
| scalar product chain, `ball_mul_2` | 1.00 | 1.00 | 1.00 | 1.00 | 1.07 | 1.07 | 1.07 | 1.07 | 1.12 |
| packed product chain, `mul_2_2` | 0.97–1.06 | 1.00–1.03 | 0.99–1.03 | 1.00–1.06 | 1.08 | 1.08 | 1.08 | 1.09 | 1.00 |
| packed product chain, `ball_mul_2` | 0.95–1.00 | 0.96–1.00 | 0.98–1.00 | 1.00 | 1.08 | 1.08–1.09 | 1.07 | 1.07–1.08 | 1.00–1.01 |
| scalar Horner, `mul_2_2+add_2_2` | 0.97–1.00 | 1.00 | 1.00 | 1.00 | 1.04 | 1.03–1.04 | 1.03 | 1.03 | 1.04 |
| scalar Horner, `ball_mul_2+ball_add_2` | 0.98–1.00 | 1.00 | 1.00 | 1.00 | 1.02 | 1.02 | 1.05 | 1.05 | 1.07 |
| packed Horner, `mul_2_2+add_2_2` | 0.99–1.02 | 1.00–1.01 | 1.00 | 1.00 | 1.04–1.05 | 1.04 | 1.03 | 1.03 | 1.01 |
| packed Horner, `ball_mul_2+ball_add_2` | 1.00 | 1.00 | 1.00 | 1.00 | 1.04 | 1.04 | 1.05 | 1.05 | 1.00 |
| scalar product chain, one limb: `mul_1_1` over `double` | 1.00–1.03 | 1.00 | 0.99 | 0.99–1.00 | 1.66 | 1.65–1.66 | 1.66 | 1.66 | 1.00 |

### 2. The fix-up

Public operator over `kairn::finite::`, `Expansion<double, 2>` (arrays of numbers):

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, `x + y` | 1.65–1.68 | 1.67–1.68 | 1.15–1.18 | 1.14–1.18 | 1.18 | 2.23–2.24 | 1.18–1.19 | 1.18–1.19 | 1.08 |
| throughput, `x + a` | 1.73–1.77 | 1.73 | 1.85–1.86 | 1.86–1.90 | 1.23–1.24 | 2.59–2.60 | 1.17 | 1.16–1.17 | 1.14 |
| throughput, `add_fast(x, y)` | 1.53–1.56 | 1.53 | 1.43–1.49 | 1.66–1.67 | 1.23 | 2.33–2.34 | 1.32 | 1.32–1.33 | 1.13 |
| throughput, `x * y` | 1.37–1.39 | 1.39–1.40 | 1.55 | 1.54–1.55 | 1.27–1.28 | 1.96 | 1.54 | 1.53–1.54 | 1.33–1.34 |
| throughput, `x * a` | 1.39–1.43 | 1.43 | 1.52 | 1.52 | 1.50 | 2.28–2.29 | 1.48–1.49 | 1.48 | 1.52 |
| sum chain, `s = s + x[i]` | 1.03–1.06 | 1.00–1.04 | 1.00 | 1.01–1.07 | 1.01–1.02 | 1.02 | 1.01 | 1.01–1.02 | 1.02 |
| sum chain, `s = s + a[i]` | 0.99 | 0.98–0.99 | 1.01 | 1.01 | 1.00 | 1.00–1.01 | 1.00 | 1.00 | 1.04 |
| sum chain, `s = add_fast(s, x[i])` | 0.99 | 0.99–1.00 | 1.01 | 1.01 | 1.00 | 0.99–1.00 | 1.01–1.02 | 1.01–1.02 | 1.05 |
| product chain, `p = p * x[i]` | 0.99 | 0.99 | 1.03 | 1.03 | 1.04 | 1.04 | 1.00 | 1.00 | 0.96 |
| product chain, `p = p * a[i]` | 1.02–1.07 | 1.02–1.03 | 1.03–1.04 | 1.03–1.04 | 1.01 | 1.01 | 1.03–1.04 | 1.04 | 0.94 |
| Horner, `p = p * h + c[i]`, two-limb `h`, `c` | 0.97–0.99 | 0.99 | 1.03 | 1.02 | 1.01–1.02 | 1.02 | 1.01 | 1.01 | 1.00–1.01 |
| Horner, `p = p * h + c[i]`, one-limb `h`, `c` | 0.99–1.00 | 1.00 | 1.03 | 1.03 | 1.03 | 1.03 | 0.99–1.00 | 0.99–1.00 | 0.97–0.98 |

Generated full kernel over its core, on separate arrays of limbs (`scalar`) and packed
(`packed`); the listing with selects (`full_sel`) for comparison:

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| scalar throughput, `add_2_2` | 2.07–2.08 | 2.07 | 2.19–2.20 | 2.02–2.17 | 1.17–1.18 | 4.65–4.68 | 1.16 | 1.16 | 4.24–4.25 |
| scalar throughput, `add_2_2`, selects | 1.59–1.63 | 1.59 | 2.59 | 2.40–2.44 | 1.21 | 4.69–4.71 | 1.16–1.17 | 1.16–1.17 | 6.13–6.14 |
| packed throughput, `add_2_2` | 1.54 | 1.54 | 1.33–1.35 | 1.33–1.35 | 1.21 | 1.21 | 1.16–1.17 | 1.17 | 1.27 |
| scalar throughput, `add_2_1` | 2.30 | 2.30 | 2.35 | 2.35–2.36 | 1.23–1.24 | 4.94 | 1.32 | 1.32–1.33 | 4.54–4.56 |
| packed throughput, `add_2_1` | 1.93–1.94 | 1.94 | 1.63 | 1.63 | 1.45 | 1.45 | 1.32–1.33 | 1.33 | 1.71–1.73 |
| scalar throughput, `add_fast_2_2` | 2.27–2.28 | 2.27 | 2.34–2.35 | 2.34 | 1.24–1.25 | 5.00–5.01 | 1.24–1.25 | 1.24–1.25 | 4.35–4.36 |
| packed throughput, `add_fast_2_2` | 1.93–1.94 | 1.93–1.94 | 1.64 | 1.64 | 1.38–1.40 | 1.38–1.39 | 1.24–1.25 | 1.24–1.25 | 1.61 |
| scalar throughput, `mul_2_2` | 2.03–2.11 | 2.10 | 2.20–2.21 | 2.21–2.22 | 1.27–1.28 | 6.05–6.07 | 1.72–1.73 | 1.73–1.74 | 1.38 |
| scalar throughput, `mul_2_2`, selects | 2.06–2.15 | 2.14–2.15 | 3.06–3.07 | 2.77 | 1.64 | 7.25–7.26 | 1.73–1.74 | 1.74–1.75 | 2.95–2.96 |
| packed throughput, `mul_2_2` | 1.96–1.98 | 1.98 | 1.70 | 1.70 | 1.98 | 1.97 | 1.74–1.75 | 1.74–1.75 | 2.05 |
| scalar throughput, `mul_2_1` | 2.41–2.49 | 2.42–2.43 | 2.06 | 2.06–2.07 | 1.50–1.51 | 6.64–6.65 | 2.03–2.04 | 2.03–2.04 | 1.64 |
| packed throughput, `mul_2_1` | 2.35–2.40 | 2.35 | 1.89 | 1.88–1.89 | 2.22–2.27 | 2.30–2.32 | 2.04–2.05 | 2.04–2.05 | 2.33–2.34 |
| scalar sum chain, `add_2_2` | 0.93–0.97 | 0.94–0.99 | 0.97–1.00 | 0.98–1.01 | 1.01–1.02 | 1.01–1.02 | 1.00 | 1.00–1.01 | 1.04 |
| scalar sum chain, `add_2_2`, selects | 1.33–1.42 | 1.32–1.42 | 1.05–1.08 | 1.05–1.08 | 1.01 | 1.01 | 1.10 | 1.10 | 1.76 |
| packed sum chain, `add_2_2` | 1.25 | 1.21–1.25 | 1.26–1.28 | 1.25–1.28 | 1.17 | 1.17 | 1.11 | 1.11 | 1.53 |
| scalar sum chain, `add_2_1` | 0.95–0.98 | 0.95–0.98 | 0.98–1.01 | 0.99–1.01 | 1.00–1.01 | 1.00–1.01 | 1.00 | 1.00–1.01 | 1.05 |
| packed sum chain, `add_2_1` | 1.43 | 1.40–1.43 | 1.44–1.45 | 1.43–1.50 | 1.27 | 1.26–1.27 | 1.14 | 1.14 | 1.94–1.95 |
| scalar product chain, `mul_2_2` | 0.99–1.01 | 0.99 | 1.03 | 1.03 | 1.04 | 1.04 | 1.00–1.01 | 1.00 | 1.02–1.03 |
| scalar product chain, `mul_2_2`, selects | 1.35–1.37 | 1.35 | 1.01 | 1.02 | 1.01 | 1.01 | 1.01 | 1.01 | 1.54–1.55 |
| packed product chain, `mul_2_2` | 1.23–1.36 | 1.27–1.31 | 1.16–1.20 | 1.13–1.20 | 1.08 | 1.08 | 1.06 | 1.06 | 1.53 |
| scalar product chain, `mul_2_1` | 1.00–1.02 | 1.00–1.02 | 1.01–1.04 | 1.01–1.04 | 1.01 | 1.01 | 1.04 | 1.04 | 1.00–1.01 |
| packed product chain, `mul_2_1` | 1.53 | 1.49–1.53 | 1.63–1.64 | 1.64 | 1.45 | 1.45 | 1.26–1.27 | 1.27 | 2.06 |
| scalar Horner, `mul_2_2+add_2_2` | 0.99–1.02 | 0.99 | 1.03 | 1.02 | 1.01–1.02 | 1.01–1.02 | 1.01 | 1.01 | 1.04–1.05 |
| scalar Horner, `mul_2_2+add_2_2`, selects | 1.32–1.35 | 1.32 | 1.04 | 1.06 | 1.00 | 1.00 | 1.05 | 1.05 | 1.61 |
| packed Horner, `mul_2_2+add_2_2` | 1.22–1.26 | 1.23–1.24 | 1.21 | 1.20–1.21 | 1.10 | 1.10 | 1.08 | 1.08 | 1.46 |

### 3. Ball operations

Times, `double` limbs, public types (ns per operation or per step):

| Operation (ns) | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, `X + Y`, `Ball<double, 2>` | 1.95–1.99 | 1.95 | 2.02 | 2.03–2.04 | 5.99–6.01 | 4.1–4.12 | 3.03–3.05 | 3.03–3.04 | 3.07–3.08 |
| throughput, `x + y`, `Expansion<double, 2>` | 1.51–1.54 | 1.51 | 1.57–1.59 | 1.56–1.58 | 4.41–4.44 | 4.42–4.44 | 2.7–2.72 | 2.71–2.72 | 2.35 |
| throughput, `X * Y`, `Ball<double, 2>` | 1.5–1.57 | 1.5 | 1.53 | 1.53 | 4.21–4.24 | 3.75–3.77 | 2.42–2.45 | 2.43–2.44 | 3.26–3.27 |
| throughput, `x * y`, `Expansion<double, 2>` | 0.769–0.78 | 0.769–0.772 | 0.847–0.85 | 0.846–0.849 | 2.29–2.31 | 2.3–2.31 | 1.96–1.97 | 1.97 | 1.26–1.27 |
| throughput, `X * a`, `Ball<double, 2>` | 0.998–1.01 | 0.998–0.999 | 1.08 | 1.08 | 3.43–3.46 | 2.61–2.62 | 2.93–2.95 | 2.93–2.94 | 2.5 |
| throughput, `x * a`, `Expansion<double, 2>` | 0.595–0.607 | 0.596 | 0.631–0.633 | 0.631–0.633 | 1.84–1.85 | 1.84–1.85 | 1.64–1.65 | 1.64–1.65 | 1.06 |
| throughput, `-X`, `Ball<double, 2>` | 0.386–0.421 | 0.504–0.508 | 0.416–0.423 | 0.415–0.423 | 0.679–0.682 | 1.13 | 0.686–0.69 | 0.686–0.689 | 0.379–0.391 |
| throughput, `-x`, `Expansion<double, 2>` | 0.298–0.315 | 0.302 | 0.295 | 0.289–0.295 | 0.48–0.482 | 0.342–0.344 | 0.334–0.336 | 0.335–0.336 | 0.348–0.353 |
| throughput, `X + Y`, `Ball<double, 1>` | 0.771–0.805 | 0.771–0.772 | 0.715–0.716 | 0.699–0.715 | 2.05–2.06 | 1.38–1.39 | 1.45–1.46 | 1.45–1.46 | 1.6 |
| throughput, `X * Y`, `Ball<double, 1>` | 0.981–1.02 | 0.981 | 0.947 | 0.883–0.884 | 2.56–2.57 | 1.77–1.78 | 1.64–1.65 | 1.64 | 2.27 |
| throughput, `X * a`, `Ball<double, 1>` | 0.745–0.759 | 0.745 | 0.684–0.685 | 0.685 | 2.09–2.1 | 1.16–1.17 | 1.59–1.6 | 1.6 | 1.8 |
| throughput, `-X`, `Ball<double, 1>` | 0.281 | 0.28–0.281 | 0.297 | 0.57–0.609 | 0.627–0.63 | 0.6–0.603 | 0.345–0.346 | 0.483–0.485 | 0.225–0.227 |
| throughput, `double` addition | 0.157–0.161 | 0.157 | 0.296 | 0.154–0.155 | 0.629–0.632 | 0.185–0.186 | 0.187–0.19 | 0.186 | 0.0864–0.143 |
| throughput, `double` multiplication | 0.157–0.162 | 0.157 | 0.296 | 0.157 | 0.628–0.631 | 0.185–0.186 | 0.185–0.186 | 0.187–0.189 | 0.1–0.145 |
| sum chain, `ball_add_2` | 7.3–8.12 | 7.3 | 7.09 | 7.15–7.16 | 10.4–10.5 | 10.4–10.5 | 10.2–10.3 | 10.2–10.3 | 5.23–5.24 |
| sum chain, `add_2_2` | 7.42–7.86 | 7.04–7.55 | 7.12–7.64 | 7.16–7.67 | 10.3–10.4 | 10.3–10.4 | 10–10.1 | 10.1 | 5.08 |
| product chain, `ball_mul_2` | 5.57–6.13 | 5.57–5.6 | 5.51 | 5.57–5.58 | 8.11–8.14 | 8.11–8.13 | 8.27–8.29 | 8.26–8.29 | 6.6 |
| product chain, `mul_2_2` | 5.27–5.77 | 5.27–5.28 | 5.41–5.42 | 5.41–5.42 | 8.32–8.36 | 8.31–8.34 | 8.07–8.12 | 8.08–8.1 | 5.77 |
| product chain, `ball_scale_2` | 3.61–4.03 | 3.61–3.65 | 3.64–3.65 | 3.65–3.66 | 5.72–5.74 | 5.71–5.74 | 5.53–5.57 | 5.54–5.56 | 4.81–4.82 |
| product chain, `mul_2_1` | 3.42–3.83 | 3.42 | 3.45 | 3.45 | 5.37–5.39 | 5.37–5.4 | 5.49–5.52 | 5.5–5.51 | 4.79 |
| Horner, `ball_mul_2+ball_add_2` | 12.7–13.8 | 12.7 | 13 | 12.9 | 18.6–18.7 | 18.6–18.8 | 18.8–18.9 | 18.8–18.9 | 12–12.1 |
| Horner, `mul_2_2+add_2_2` | 12.6–13.6 | 12.6 | 12.9 | 12.9 | 18.5–18.6 | 18.6 | 18.3–18.4 | 18.3–18.4 | 11.3 |
| sum chain, `ball_add_1` | 2.6–2.9 | 2.6–2.63 | 2.56 | 2.56 | 3.85–3.87 | 3.85–3.86 | 3.85–3.88 | 3.85–3.86 | 3.35–3.36 |
| sum chain, `double` | 0.365–0.391 | 0.365–0.369 | 0.459–0.475 | 0.466–0.468 | 0.787–0.79 | 0.791–0.794 | 0.791–0.795 | 0.792–0.794 | 0.285 |
| product chain, `ball_mul_1` | 4.69–5.24 | 4.68–4.7 | 5.12–5.13 | 4.66–4.67 | 8.04–8.06 | 8.03–8.07 | 7.6–7.64 | 7.61–7.63 | 6.45–6.46 |
| product chain, `double` | 0.718–0.788 | 0.718 | 0.717–0.718 | 0.717–0.718 | 0.791–0.796 | 0.791–0.794 | 0.791–0.795 | 0.791–0.794 | 0.544–0.545 |
| Horner, `ball_mul_1+ball_add_1` | 7.47–8.22 | 7.46–7.47 | 7.44 | 7.46–7.47 | 12.2 | 12.2–12.3 | 11.4–11.5 | 11.4 | 10.2 |
| Horner, `double` | 1.22–1.35 | 1.22 | 1.22–1.23 | 1.22–1.23 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.23 |

Ball over the center's operation, public types (`op` over `op`, and over `kairn::finite::`):

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 limbs, throughput, `X + Y` over the operator | 1.29 | 1.29 | 1.27–1.29 | 1.28–1.30 | 1.35–1.36 | 0.93 | 1.12 | 1.12 | 1.31 |
| 2 limbs, throughput, `X + Y` over `finite::` | 2.12–2.17 | 2.16–2.17 | 1.47–1.52 | 1.48–1.51 | 1.59–1.60 | 2.07–2.08 | 1.32–1.33 | 1.32–1.33 | 1.41 |
| 2 limbs, throughput, `X * Y` over the operator | 1.95–2.01 | 1.94–1.95 | 1.80–1.81 | 1.80–1.81 | 1.83–1.84 | 1.63–1.64 | 1.24 | 1.23–1.24 | 2.57–2.58 |
| 2 limbs, throughput, `X * Y` over `finite::` | 2.72–2.76 | 2.72 | 2.79–2.80 | 2.79–2.80 | 2.34 | 3.20 | 1.90–1.91 | 1.90 | 3.43–3.45 |
| 2 limbs, throughput, `X * a` over the operator | 1.67–1.68 | 1.68 | 1.71 | 1.71 | 1.86–1.87 | 1.41–1.42 | 1.78–1.79 | 1.78–1.79 | 2.36 |
| 2 limbs, throughput, `X * a` over `finite::` | 2.33–2.40 | 2.39 | 2.59–2.60 | 2.60 | 2.80–2.81 | 3.23–3.25 | 2.64–2.65 | 2.64–2.65 | 3.58–3.59 |
| 2 limbs, sum chain, `X + Y` over the operator | 0.97–1.03 | 0.97–1.04 | 0.93–1.00 | 0.93–1.00 | 1.01 | 1.01 | 1.02 | 1.02 | 1.03 |
| 2 limbs, sum chain, `X + Y` over `finite::` | 1.03–1.06 | 1.00–1.03 | 0.93–1.00 | 0.99–1.01 | 1.03 | 1.03 | 1.03–1.04 | 1.03–1.04 | 1.05 |
| 2 limbs, product chain, `X * Y` over the operator | 1.06 | 1.06 | 1.02 | 1.03 | 0.97–0.98 | 0.97–0.98 | 1.02 | 1.02 | 1.14 |
| 2 limbs, product chain, `X * Y` over `finite::` | 1.05–1.06 | 1.05 | 1.05 | 1.06 | 1.01 | 1.01 | 1.02 | 1.02–1.03 | 1.10 |
| 2 limbs, product chain, `X * a` over the operator | 1.05 | 1.05–1.07 | 1.05–1.06 | 1.06 | 1.06–1.07 | 1.06 | 1.01 | 1.01 | 1.01 |
| 2 limbs, product chain, `X * a` over `finite::` | 1.08–1.13 | 1.08–1.09 | 1.09 | 1.09–1.10 | 1.08 | 1.08 | 1.04 | 1.04 | 0.95 |
| 2 limbs, Horner, `X * H + C` over the operator | 1.01–1.02 | 1.01 | 1.01 | 1.00 | 1.00–1.01 | 1.00–1.01 | 1.03 | 1.03 | 1.06–1.07 |
| 2 limbs, Horner, `X * H + C` over `finite::` | 0.99–1.00 | 1.00 | 1.03 | 1.02 | 1.02 | 1.02–1.03 | 1.04 | 1.04 | 1.06–1.07 |
| 2 limbs, throughput, `-X` over `-x` | 1.23–1.41 | 1.67–1.68 | 1.41–1.43 | 1.43–1.44 | 1.41 | 3.29 | 2.05 | 2.05 | 1.08–1.11 |
| 1 limb, throughput, `X + Y` over `double` | 4.92–5.01 | 4.92–4.93 | 2.42 | 4.53–4.60 | 3.25–3.26 | 7.44 | 7.70–7.81 | 7.81–7.84 | 11.22–18.52 |
| 1 limb, throughput, `X * Y` over `double` | 6.26–6.33 | 6.26 | 3.20 | 5.62 | 4.07 | 9.55–9.56 | 8.84–8.85 | 8.69–8.79 | 15.59–22.61 |
| 1 limb, throughput, `X * a` over `double` | 4.69–4.75 | 4.75 | 2.31 | 4.36 | 3.33 | 6.28–6.31 | 8.56–8.59 | 8.47–8.55 | 12.36–17.92 |
| 1 limb, throughput, `-X` over `double` | 1.76–1.79 | 1.79 | 1.00–1.02 | 3.66–4.06 | 1.00 | 3.46 | 1.98–1.99 | 2.78 | 1.92–2.26 |
| 1 limb, sum chain, `X + Y` over `double` | 7.12–7.43 | 7.11–7.13 | 5.39–5.58 | 5.48–5.49 | 4.88–4.91 | 4.86–4.87 | 4.86–4.87 | 4.85–4.87 | 11.74–11.77 |
| 1 limb, product chain, `X * Y` over `double` | 6.53–6.65 | 6.53–6.54 | 7.14–7.15 | 6.50 | 10.13–10.16 | 10.15–10.17 | 9.60–9.61 | 9.59–9.62 | 11.85–11.86 |
| 1 limb, product chain, `X * a` over `double` | 3.95–3.97 | 3.94–3.97 | 4.53 | 4.52–4.53 | 6.04–6.05 | 6.05–6.06 | 5.65–5.68 | 5.65–5.69 | 7.32–7.33 |
| 1 limb, Horner, `X * H + C` over `double` | 6.06–6.10 | 6.10 | 6.07–6.08 | 6.09–6.10 | 7.21–7.24 | 7.23–7.24 | 6.74–6.76 | 6.75–6.76 | 8.25–8.31 |

Packed Ball kernels over the packed center kernels (full over full, and full over the core):

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, `ball_add_2` over `add_2_2` | 1.32 | 1.31 | 1.36–1.39 | 1.34–1.38 | 1.58 | 1.58 | 1.54–1.55 | 1.54–1.55 | 1.53 |
| throughput, `ball_add_2` over the core `add_2_2` | 2.04 | 2.02 | 1.84 | 1.81–1.84 | 1.90–1.92 | 1.90–1.92 | 1.80–1.81 | 1.80 | 1.93–1.94 |
| throughput, `ball_mul_2` over `mul_2_2` | 1.61–1.63 | 1.61 | 1.72 | 1.71–1.72 | 1.79–1.80 | 1.80 | 1.93 | 1.93 | 1.88–1.89 |
| throughput, `ball_mul_2` over the core `mul_2_2` | 3.18–3.19 | 3.18 | 2.92 | 2.92 | 3.55 | 3.55 | 3.36–3.37 | 3.35–3.37 | 3.87 |
| throughput, `ball_scale_2` over `mul_2_1` | 1.52 | 1.52 | 1.64 | 1.63–1.64 | 1.79–1.80 | 1.79–1.80 | 1.91 | 1.91 | 1.89 |
| throughput, `ball_scale_2` over the core `mul_2_1` | 3.58–3.65 | 3.58 | 3.09 | 3.07–3.09 | 3.99–4.07 | 4.14–4.16 | 3.89–3.91 | 3.89–3.90 | 4.41–4.42 |
| sum chain, `ball_add_2` over `add_2_2` | 1.30–1.39 | 1.30–1.39 | 1.26–1.29 | 1.20–1.29 | 1.34 | 1.34 | 1.33 | 1.33 | 1.40–1.41 |
| sum chain, `ball_add_2` over the core `add_2_2` | 1.63–1.74 | 1.62–1.74 | 1.59–1.65 | 1.54–1.65 | 1.56–1.57 | 1.56–1.57 | 1.47–1.48 | 1.47–1.48 | 2.15 |
| product chain, `ball_mul_2` over `mul_2_2` | 1.40–1.45 | 1.40–1.44 | 1.43–1.54 | 1.43–1.46 | 1.45–1.46 | 1.45–1.46 | 1.35–1.36 | 1.35–1.36 | 1.45 |
| product chain, `ball_mul_2` over the core `mul_2_2` | 1.78–1.90 | 1.82–1.83 | 1.71–1.78 | 1.66–1.72 | 1.57 | 1.57 | 1.43–1.44 | 1.43–1.44 | 2.22 |
| product chain, `ball_scale_2` over `mul_2_1` | 1.64 | 1.64–1.76 | 1.43–1.45 | 1.43 | 1.55–1.56 | 1.56 | 1.59–1.60 | 1.60 | 1.46 |
| product chain, `ball_scale_2` over the core `mul_2_1` | 2.50–2.52 | 2.52–2.63 | 2.35–2.38 | 2.35 | 2.26–2.27 | 2.26 | 2.02 | 2.02 | 3.00–3.01 |
| Horner, `ball_mul_2+ball_add_2` over `mul_2_2+add_2_2` | 1.39 | 1.39 | 1.37 | 1.37 | 1.40 | 1.39–1.40 | 1.33 | 1.33–1.35 | 1.39 |
| Horner, `ball_mul_2+ball_add_2` over the core `mul_2_2+add_2_2` | 1.70–1.75 | 1.70–1.73 | 1.65 | 1.65 | 1.54 | 1.54 | 1.44–1.45 | 1.44–1.46 | 2.03 |
| throughput, `ball_neg_2` over `neg_2` | 1.55–1.56 | 1.56 | 1.60 | 2.14 | 1.49 | 1.56 | 1.56–1.57 | 1.56–1.57 | 1.25–1.39 |
| throughput, `ball_add_1` over a `double` operation | 3.74–3.76 | 3.63–3.64 | 3.06–3.07 | 3.06 | 5.74–5.78 | 5.73–5.76 | 4.01–4.05 | 4.02–4.04 | 5.40–5.45 |
| throughput, `ball_mul_1` over a `double` operation | 4.66–4.78 | 4.68–4.69 | 4.01 | 4.01 | 8.42–8.46 | 6.54–6.58 | 6.10–6.13 | 6.15–6.16 | 5.02–5.87 |
| throughput, `ball_scale_1` over a `double` operation | 3.82–3.91 | 3.73–3.84 | 3.14 | 3.14 | 6.41–6.43 | 4.99–5.01 | 4.57–4.59 | 4.60–4.62 | 4.14–4.84 |
| sum chain, `ball_add_1` over a `double` operation | 12.53–13.05 | 12.73–13.12 | 11.43–11.81 | 11.30–11.80 | 10.57–10.63 | 10.59–10.67 | 11.21–11.24 | 11.23–11.24 | 21.76–21.87 |
| product chain, `ball_mul_1` over a `double` operation | 11.75–12.61 | 11.38–12.11 | 11.13–11.14 | 11.13–11.17 | 15.34–15.36 | 15.31–15.35 | 18.30–18.35 | 18.33–18.35 | 17.16–17.24 |
| product chain, `ball_scale_1` over a `double` operation | 9.24–9.91 | 8.99–9.52 | 8.52–8.54 | 8.50–8.54 | 11.21–11.24 | 11.22–11.23 | 12.55–12.56 | 12.56 | 12.85–12.90 |
| throughput, `ball_neg_1` over a `double` negation | 1.48–1.51 | 1.48–1.49 | 1.47 | 1.47 | 1.88 | 1.10 | 1.96–1.97 | 1.96–1.97 | 1.08–1.31 |

Full Ball kernels over their cores (`public`: the operator over the core on the same arrays;
`scalar` and `packed`: the generated kernels on separate arrays; `selects`: the listing):

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| public, throughput, `ball_add_2` | 1.68–1.70 | 1.70 | 1.77 | 1.68 | 1.23 | 1.60–1.61 | 1.00–1.01 | 1.00 | 1.27 |
| scalar, throughput, `ball_add_2` | 2.23–2.24 | 2.23–2.24 | 2.34–2.36 | 2.34–2.35 | 1.23 | 1.74–1.75 | 1.47–1.48 | 1.48 | 1.25–1.26 |
| scalar, throughput, `ball_add_2`, selects | 1.68–1.69 | 1.68–1.69 | 2.66 | 2.49–2.62 | 1.27 | 5.16–5.18 | 1.46–1.47 | 1.47 | 2.62 |
| packed, throughput, `ball_add_2` | 1.67 | 1.66 | 1.53–1.56 | 1.50–1.53 | 1.60 | 1.60–1.61 | 1.47 | 1.46–1.47 | 1.79 |
| public, throughput, `ball_mul_2` | 1.61 | 1.61 | 1.64 | 1.62 | 1.29–1.30 | 1.64 | 1.20 | 1.19–1.20 | 1.40–1.42 |
| scalar, throughput, `ball_mul_2` | 2.29–2.32 | 2.31 | 2.29–2.35 | 2.28–2.35 | 1.30–1.31 | 2.13 | 1.83 | 1.82–1.83 | 1.41 |
| scalar, throughput, `ball_mul_2`, selects | 1.89–1.93 | 1.89 | 2.62–2.63 | 2.59–2.62 | 1.42 | 6.01–6.06 | 1.83 | 1.83 | 2.68–2.69 |
| packed, throughput, `ball_mul_2` | 1.80 | 1.81 | 1.63 | 1.63–1.64 | 1.93 | 1.93–1.94 | 1.84 | 1.83–1.84 | 2.62 |
| public, throughput, `ball_scale_2` | 1.58–1.61 | 1.58 | 1.73–1.74 | 1.73–1.74 | 1.47 | 1.20–1.23 | 1.42–1.43 | 1.42 | 1.65 |
| scalar, throughput, `ball_scale_2` | 2.42 | 2.43 | 2.36 | 2.37–2.38 | 1.46 | 2.49–2.50 | 2.08 | 2.08–2.09 | 1.75–1.76 |
| packed, throughput, `ball_scale_2` | 2.10–2.14 | 2.14 | 1.87 | 1.86 | 2.27 | 2.27 | 2.09–2.10 | 2.09 | 3.05 |
| public, throughput, `ball_add_1` | 1.40 | 1.40 | 1.55 | 1.30–1.34 | 1.89–1.90 | 1.70 | 1.84 | 1.82–1.83 | 2.59–2.60 |
| scalar, throughput, `ball_add_1` | 3.01–3.23 | 3.29 | 1.09 | 2.35 | 1.80 | 3.08 | 2.05–2.06 | 2.05–2.06 | 2.78–2.79 |
| packed, throughput, `ball_add_1` | 2.45–2.51 | 2.44 | 2.04 | 1.96–1.98 | 2.60–2.61 | 2.60–2.61 | 2.07 | 2.07–2.08 | 2.61 |
| public, throughput, `ball_mul_1` | 1.78–1.81 | 1.78 | 1.36 | 1.61 | 1.55–1.57 | 1.89 | 1.37 | 1.37–1.38 | 1.64–1.65 |
| scalar, throughput, `ball_mul_1` | 2.99–3.02 | 2.93 | 1.11–1.13 | 2.17 | 1.53 | 2.38 | 2.01–2.02 | 2.01 | 1.64–1.66 |
| packed, throughput, `ball_mul_1` | 2.24–2.28 | 2.23–2.24 | 1.95 | 1.94–1.95 | 2.19 | 2.19 | 2.02 | 2.01 | 2.72 |
| public, throughput, `ball_scale_1` | 1.78–1.80 | 1.78 | 1.40–1.41 | 1.64–1.65 | 1.70 | 1.71–1.72 | 1.58–1.59 | 1.60–1.61 | 2.19 |
| scalar, throughput, `ball_scale_1` | 2.98–3.01 | 3.01–3.02 | 1.00 | 1.94 | 2.15–2.17 | 3.08–3.09 | 2.29 | 2.29 | 2.07 |
| packed, throughput, `ball_scale_1` | 2.08 | 2.02–2.08 | 1.69 | 1.69–1.70 | 2.42–2.44 | 2.57–2.58 | 2.23–2.24 | 2.18–2.19 | 2.63–2.64 |
| public, sum chain, `ball_add_2` | 1.02–1.06 | 1.02 | 0.98 | 1.00 | 1.02 | 1.02 | 1.01 | 1.01 | 1.01 |
| scalar, sum chain, `ball_add_2` | 1.02–1.06 | 1.02–1.04 | 0.98 | 1.00 | 1.01 | 1.01 | 1.00–1.01 | 1.00 | 1.00 |
| scalar, sum chain, `ball_add_2`, selects | 1.81–1.88 | 1.81–1.82 | 1.07 | 1.07 | 1.27–1.28 | 1.00–1.01 | 1.05 | 1.05–1.06 | 2.36 |
| packed, sum chain, `ball_add_2` | 1.60–1.72 | 1.70 | 1.63 | 1.63–1.66 | 1.54 | 1.53–1.54 | 1.44–1.45 | 1.44–1.45 | 2.13–2.14 |
| public, product chain, `ball_mul_2` | 0.99–1.01 | 1.01 | 1.00 | 1.01 | 1.00–1.01 | 1.00–1.01 | 1.01–1.02 | 1.02 | 0.97 |
| scalar, product chain, `ball_mul_2` | 1.00–1.01 | 1.01 | 1.01 | 1.00 | 1.00–1.01 | 1.01 | 1.02 | 1.02 | 0.98 |
| scalar, product chain, `ball_mul_2`, selects | 1.91–1.92 | 1.91 | 1.11 | 1.11–1.14 | 1.32 | 1.02–1.03 | 1.03 | 1.03 | 1.78–1.79 |
| packed, product chain, `ball_mul_2` | 1.71–1.76 | 1.71–1.77 | 1.59–1.63 | 1.57–1.60 | 1.50–1.51 | 1.50 | 1.39 | 1.39 | 1.98–1.99 |
| public, product chain, `ball_scale_2` | 1.02–1.03 | 1.03–1.04 | 1.03 | 1.04 | 1.04–1.05 | 1.04–1.05 | 1.01 | 1.01 | 0.89 |
| scalar, product chain, `ball_scale_2` | 1.03–1.06 | 1.03 | 1.03–1.04 | 0.97–1.04 | 1.04–1.05 | 1.04–1.05 | 1.01 | 1.01 | 0.96 |
| packed, product chain, `ball_scale_2` | 2.28–2.31 | 2.30–2.31 | 2.04–2.15 | 2.15 | 2.12 | 2.12 | 1.90 | 1.90 | 2.53 |
| public, sum chain, `ball_add_1` | 1.20–1.21 | 1.20–1.21 | 1.15 | 1.15–1.16 | 1.03 | 1.02–1.03 | 1.03 | 1.03 | 1.24–1.25 |
| scalar, sum chain, `ball_add_1` | 1.20–1.24 | 1.20–1.21 | 1.15 | 1.15 | 1.03 | 1.03 | 1.03 | 1.03 | 1.24 |
| packed, sum chain, `ball_add_1` | 3.12–3.27 | 3.23 | 2.60–2.80 | 2.78–2.80 | 2.02 | 2.02 | 1.66 | 1.66 | 4.08–4.12 |
| public, product chain, `ball_mul_1` | 1.08–1.10 | 1.08 | 1.15–1.16 | 1.05–1.06 | 1.09–1.10 | 1.09–1.10 | 1.04 | 1.04 | 1.01 |
| scalar, product chain, `ball_mul_1` | 1.08 | 1.08 | 1.14–1.16 | 1.05–1.06 | 1.10–1.11 | 1.11 | 1.04–1.05 | 1.04 | 1.02 |
| packed, product chain, `ball_mul_1` | 1.88 | 1.87–1.88 | 1.73 | 1.73 | 1.41 | 1.41 | 1.29 | 1.29 | 2.44 |
| public, product chain, `ball_scale_1` | 1.20–1.21 | 1.20 | 1.34 | 1.34 | 1.10 | 1.10 | 1.04 | 1.03–1.04 | 0.99 |
| scalar, product chain, `ball_scale_1` | 1.20 | 1.20 | 1.34 | 1.33–1.34 | 1.11 | 1.11 | 1.03–1.04 | 1.04 | 0.99 |
| packed, product chain, `ball_scale_1` | 2.84 | 2.84–2.85 | 2.54 | 2.54 | 1.85 | 1.85 | 1.58 | 1.58 | 3.68 |
| public, Horner, `ball_mul_2+ball_add_2` | 0.98–1.00 | 0.98 | 1.01 | 1.00–1.01 | 1.02–1.03 | 1.01 | 1.01–1.02 | 1.01–1.02 | 1.02–1.03 |
| scalar, Horner, `ball_mul_2+ball_add_2` | 0.98–0.99 | 0.98 | 1.01 | 1.01 | 1.02 | 1.02 | 1.01 | 1.01 | 1.04 |
| scalar, Horner, `ball_mul_2+ball_add_2`, selects | 1.86–1.88 | 1.86 | 1.09 | 1.09 | 1.36 | 1.20–1.21 | 1.03–1.04 | 1.03 | 2.17 |
| packed, Horner, `ball_mul_2+ball_add_2` | 1.68–1.69 | 1.67–1.68 | 1.59 | 1.59 | 1.53 | 1.53 | 1.40–1.41 | 1.40–1.41 | 2.05 |
| public, Horner, `ball_mul_1+ball_add_1` | 1.06 | 1.05–1.06 | 1.05 | 1.06 | 1.08–1.09 | 1.09 | 1.01–1.02 | 1.02 | 1.05–1.06 |
| scalar, Horner, `ball_mul_1+ball_add_1` | 1.06 | 1.06 | 1.04 | 1.04 | 1.06–1.07 | 1.06 | 1.02–1.03 | 1.02 | 0.99–1.00 |
| packed, Horner, `ball_mul_1+ball_add_1` | 1.96 | 1.96 | 1.79 | 1.79–1.80 | 1.52 | 1.52 | 1.34 | 1.33–1.34 | 2.29 |

### 4. Kairn over the textbook baseline

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `finite::`, throughput, `x + y` | 1.00–1.01 | 1.00 | 0.99–1.00 | 0.98–1.05 | 1.01–1.02 | 0.99–1.01 | 0.99–1.00 | 1.00 | 0.98–0.99 |
| `finite::`, throughput, `x + a` | 1.07–1.08 | 1.07 | 0.94 | 0.92–0.94 | 1.14–1.15 | 1.05–1.06 | 1.14 | 1.14–1.15 | 1.11–1.12 |
| `finite::`, throughput, `add_fast(x, y)` | 1.00 | 1.00 | 0.96–1.00 | 1.00 | 1.00 | 0.97 | 1.00 | 0.99–1.00 | 1.00 |
| `finite::`, throughput, `x * y` | 1.01 | 1.01 | 1.00 | 1.00 | 1.26–1.27 | 1.10 | 1.04 | 1.04–1.05 | 0.91–0.92 |
| `finite::`, throughput, `x * a` | 1.00–1.03 | 1.00 | 0.95–0.96 | 1.00–1.01 | 1.18 | 1.03–1.04 | 1.07 | 1.07 | 0.93–0.94 |
| `finite::`, sum chain, `s = s + x[i]` | 0.99–1.01 | 1.00–1.01 | 0.99–1.05 | 0.99 | 1.00 | 1.00 | 1.00–1.01 | 1.00 | 1.00 |
| `finite::`, sum chain, `s = s + a[i]` | 1.02–1.06 | 1.02 | 1.02 | 1.02 | 1.04–1.05 | 1.04–1.05 | 1.05 | 1.04–1.05 | 1.00–1.01 |
| `finite::`, sum chain, `s = add_fast(s, x[i])` | 1.02 | 1.02 | 0.99 | 0.99 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `finite::`, product chain, `p = p * x[i]` | 1.00–1.02 | 1.00 | 1.00 | 1.00 | 1.08 | 1.08 | 1.09 | 1.09 | 1.15 |
| `finite::`, product chain, `p = p * a[i]` | 0.99–1.00 | 1.00 | 1.00 | 1.00 | 1.12–1.13 | 1.12–1.13 | 1.13 | 1.13 | 1.20 |
| `finite::`, Horner, `p = p * h + c[i]`, two-limb `h`, `c` | 1.00–1.01 | 1.00 | 1.00 | 1.00 | 1.05 | 1.05 | 1.04 | 1.03 | 1.08 |
| `finite::`, Horner, `p = p * h + c[i]`, one-limb `h`, `c` | 0.99–1.01 | 1.01 | 1.01 | 1.01 | 1.06 | 1.05 | 1.06–1.07 | 1.06–1.07 | 1.14 |
| operator, throughput, `x + y` | 1.66–1.68 | 1.68 | 1.15–1.17 | 1.15–1.19 | 1.19 | 2.23–2.26 | 1.17–1.18 | 1.18–1.19 | 1.05–1.06 |
| operator, throughput, `x + a` | 1.85–1.91 | 1.85 | 1.74–1.75 | 1.75 | 1.41–1.42 | 2.74 | 1.34 | 1.33–1.34 | 1.27 |
| operator, throughput, `add_fast(x, y)` | 1.53–1.56 | 1.53 | 1.43 | 1.66–1.67 | 1.23 | 2.26–2.27 | 1.32 | 1.31–1.32 | 1.13 |
| operator, throughput, `x * y` | 1.39–1.40 | 1.40–1.41 | 1.55 | 1.54–1.55 | 1.61–1.62 | 2.14–2.15 | 1.60 | 1.60–1.61 | 1.22 |
| operator, throughput, `x * a` | 1.43 | 1.43 | 1.45 | 1.52–1.54 | 1.77–1.78 | 2.37 | 1.59 | 1.59 | 1.42 |
| operator, sum chain, `s = s + x[i]` | 1.02–1.07 | 1.00–1.05 | 0.99–1.05 | 1.00–1.05 | 1.02 | 1.02 | 1.02 | 1.02 | 1.02 |
| operator, sum chain, `s = s + a[i]` | 1.01–1.05 | 1.01 | 1.03 | 1.03 | 1.05 | 1.05 | 1.05 | 1.04–1.05 | 1.04 |
| operator, sum chain, `s = add_fast(s, x[i])` | 1.01–1.02 | 1.01–1.02 | 1.00–1.01 | 1.00 | 0.99–1.00 | 0.99–1.00 | 1.01–1.02 | 1.01–1.02 | 1.05 |
| operator, product chain, `p = p * x[i]` | 0.99–1.01 | 0.99–1.00 | 1.03 | 1.03 | 1.12 | 1.12 | 1.09 | 1.09 | 1.10 |
| operator, product chain, `p = p * a[i]` | 1.02–1.06 | 1.03 | 1.03–1.04 | 1.04 | 1.14 | 1.14 | 1.17 | 1.17 | 1.13 |
| operator, Horner, `p = p * h + c[i]`, two-limb `h`, `c` | 0.98–0.99 | 0.99 | 1.03 | 1.02–1.03 | 1.07 | 1.07 | 1.05 | 1.05 | 1.08 |
| operator, Horner, `p = p * h + c[i]`, one-limb `h`, `c` | 0.98–1.01 | 1.01 | 1.03 | 1.03 | 1.09 | 1.09 | 1.06 | 1.06 | 1.11 |
| separate arrays, core, throughput, `add_2_2` | 0.98–1.00 | 1.00 | 1.00 | 1.00 | 1.03 | 0.99–1.00 | 1.02 | 1.02 | 1.00–1.01 |
| separate arrays, full, throughput, `add_2_2` | 2.03–2.08 | 2.07 | 2.19–2.20 | 2.02–2.17 | 1.21 | 4.65–4.66 | 1.19 | 1.18–1.19 | 4.27–4.29 |
| separate arrays, core, throughput, `add_fast_2_2` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00–1.01 | 1.00–1.01 |
| separate arrays, core, throughput, `mul_2_2` | 0.99–1.01 | 0.98 | 1.01 | 1.01 | 1.24 | 1.09 | 1.07 | 1.06 | 0.98 |
| separate arrays, full, throughput, `mul_2_2` | 2.05–2.08 | 2.07 | 2.22 | 2.22–2.23 | 1.58–1.59 | 6.58–6.59 | 1.84–1.85 | 1.84–1.85 | 1.35 |
| separate arrays, core, sum chain, `add_2_2` | 1.00–1.06 | 1.00–1.04 | 0.99–1.02 | 0.99–1.02 | 1.01–1.02 | 1.01 | 1.00 | 1.00 | 1.01 |
| separate arrays, full, sum chain, `add_2_2` | 0.93–1.01 | 0.97–0.99 | 0.98–0.99 | 0.99–1.00 | 1.03 | 1.03 | 1.00 | 1.00 | 1.05 |
| separate arrays, core, sum chain, `add_fast_2_2` | 1.02 | 1.02–1.03 | 0.99 | 0.99 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 |
| separate arrays, core, product chain, `mul_2_2` | 0.99–1.00 | 1.00 | 1.00 | 1.00 | 1.08 | 1.08 | 1.09 | 1.09 | 1.10 |
| separate arrays, full, product chain, `mul_2_2` | 0.99–1.00 | 0.99 | 1.03 | 1.03 | 1.12 | 1.12 | 1.09 | 1.09 | 1.13 |
| separate arrays, core, Horner, `mul_2_2+add_2_2` | 0.99–1.00 | 1.00 | 1.00 | 1.00 | 1.05 | 1.05 | 1.03–1.04 | 1.03–1.04 | 1.04–1.05 |
| separate arrays, full, Horner, `mul_2_2+add_2_2` | 0.99–1.01 | 0.99 | 1.03 | 1.02 | 1.07 | 1.07 | 1.04–1.05 | 1.04–1.05 | 1.09 |

MPFR at 106 bits over Kairn (`kairn::finite::` on the same numbers):

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, addition | 7.16–7.37 | 7.31–7.36 | 4.79–4.94 | 4.80–4.96 | 3.74–3.76 | 7.25–7.27 | 6.14–6.16 | 6.21–6.26 | — |
| throughput, multiplication | 12.70–12.85 | 12.80–13.19 | 12.87–13.02 | 12.89–12.96 | 8.46–8.56 | 13.14–13.20 | 12.10–12.21 | 11.91–11.93 | — |
| sum chain | 0.90–0.94 | 0.91–0.94 | 0.87–0.93 | 0.92–0.94 | 1.37–1.38 | 1.36–1.37 | 1.41–1.43 | 1.39–1.40 | — |
| product chain | 1.31–1.39 | 1.39–1.41 | 1.41 | 1.40–1.42 | 1.94–1.96 | 1.93–1.97 | 1.96–1.99 | 1.90–1.91 | — |
| Horner | 0.85–0.93 | 0.93–0.94 | 0.94 | 0.94 | 1.62–1.63 | 1.60–1.66 | 1.72 | 1.69–1.72 | — |
| throughput, addition over `X + Y` | 3.37–3.41 | 3.38–3.39 | 3.25–3.29 | 3.23–3.28 | 2.34–2.36 | 3.49–3.50 | 4.63–4.64 | 4.70–4.74 | — |
| throughput, multiplication over `X * Y` | 4.60–4.73 | 4.71–4.85 | 4.61–4.67 | 4.62–4.64 | 3.61–3.65 | 4.11–4.13 | 6.35–6.41 | 6.28–6.30 | — |

### 5. Limbs of type `float`

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| operator over `finite::`, throughput, `x + y` | 3.37–3.42 | 3.38–3.41 | 1.18–1.22 | 1.20–1.21 | 1.18–1.19 | 4.67–4.68 | 1.12 | 1.12 | 1.12 |
| operator over `finite::`, throughput, `x + a` | 3.54–3.56 | 3.56 | 4.06–4.14 | 3.84–4.06 | 1.24 | 5.16–5.19 | 1.17–1.18 | 1.18 | 1.24 |
| operator over `finite::`, throughput, `add_fast(x, y)` | 3.14–3.15 | 3.12–3.15 | 3.59–3.60 | 3.48–3.60 | 1.23 | 3.76 | 1.18–1.19 | 1.19 | 1.19 |
| operator over `finite::`, throughput, `x * y` | 2.82–2.84 | 2.83 | 3.31 | 3.25–3.31 | 1.37 | 3.05 | 1.34 | 1.34 | 1.28 |
| operator over `finite::`, throughput, `x * a` | 2.94–2.95 | 2.94 | 3.38–3.39 | 3.38–3.39 | 1.40–1.41 | 4.12–4.14 | 1.47 | 1.47 | 1.48–1.49 |
| operator over `finite::`, sum chain, `s = s + x[i]` | 1.00–1.06 | 1.00–1.01 | 1.00–1.04 | 1.01–1.02 | 1.02 | 1.02 | 0.99 | 0.99 | 1.05 |
| operator over `finite::`, sum chain, `s = s + a[i]` | 0.98–0.99 | 0.98–0.99 | 1.01–1.02 | 1.01–1.02 | 1.01 | 1.01 | 1.00 | 1.00–1.01 | 1.06 |
| operator over `finite::`, sum chain, `s = add_fast(s, x[i])` | 0.99–1.00 | 0.99–1.00 | 1.01–1.02 | 1.01–1.02 | 0.99–1.00 | 0.99–1.00 | 1.00 | 1.00 | 1.06 |
| operator over `finite::`, product chain, `p = p * x[i]` | 0.99–1.01 | 0.99 | 1.01 | 1.02 | 1.03 | 1.03 | 1.02 | 1.01–1.02 | 1.11 |
| operator over `finite::`, product chain, `p = p * a[i]` | 1.02 | 1.02 | 1.03–1.04 | 1.04 | 1.01 | 1.01 | 1.21–1.22 | 1.21–1.22 | 1.04 |
| operator over `finite::`, Horner, `p = p * h + c[i]`, two-limb `h`, `c` | 1.00–1.02 | 1.00 | 1.03 | 1.01 | 1.01 | 1.01 | 0.99 | 0.99 | 1.08 |
| operator over `finite::`, Horner, `p = p * h + c[i]`, one-limb `h`, `c` | 0.99–1.01 | 0.99 | 1.01 | 1.01 | 1.03 | 1.03 | 0.99 | 0.99 | 1.07–1.08 |
| `finite::` over textbook, throughput, `x + y` | 1.00–1.04 | 1.00 | 1.00–1.06 | 0.95–1.03 | 1.00 | 0.94 | 1.02 | 1.02 | 1.00 |
| `finite::` over textbook, throughput, `x + a` | 1.06–1.07 | 1.06 | 0.92–0.94 | 0.94 | 1.12–1.13 | 1.01 | 1.16 | 1.16 | 1.09 |
| `finite::` over textbook, throughput, `add_fast(x, y)` | 0.98–1.00 | 1.00 | 1.00 | 1.00–1.01 | 1.00 | 0.97 | 0.97 | 0.97 | 0.99 |
| `finite::` over textbook, throughput, `x * y` | 1.01–1.02 | 1.01 | 1.01–1.02 | 1.01 | 1.09–1.10 | 1.02–1.03 | 1.18 | 1.19 | 1.06–1.07 |
| `finite::` over textbook, throughput, `x * a` | 0.98–1.00 | 1.00 | 1.00 | 1.00 | 1.18 | 0.90–0.91 | 1.07 | 1.08 | 1.05 |
| `finite::` over textbook, sum chain, `s = s + x[i]` | 1.00–1.03 | 1.00–1.05 | 0.99–1.02 | 0.99–1.00 | 1.00 | 1.00 | 1.01 | 1.01 | 1.00 |
| `finite::` over textbook, sum chain, `s = s + a[i]` | 1.02 | 1.02–1.03 | 1.02 | 1.02 | 1.04–1.05 | 1.04–1.05 | 1.00 | 1.00 | 1.00 |
| `finite::` over textbook, sum chain, `s = add_fast(s, x[i])` | 1.00–1.02 | 1.02 | 0.99 | 0.99 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `finite::` over textbook, product chain, `p = p * x[i]` | 0.97–0.98 | 0.98 | 0.99 | 0.98–0.99 | 1.08 | 1.08 | 1.07 | 1.07 | 1.00 |
| `finite::` over textbook, product chain, `p = p * a[i]` | 0.98–0.99 | 0.98 | 0.98 | 0.98 | 1.12–1.13 | 1.12–1.13 | 1.10 | 1.10 | 1.00–1.01 |
| `finite::` over textbook, Horner, `p = p * h + c[i]`, two-limb `h`, `c` | 0.99–1.01 | 0.99 | 0.99 | 0.99 | 1.05–1.06 | 1.05–1.06 | 1.04 | 1.04 | 1.00 |
| `finite::` over textbook, Horner, `p = p * h + c[i]`, one-limb `h`, `c` | 0.97–1.01 | 1.00 | 1.00 | 1.00 | 1.05 | 1.05–1.06 | 1.05–1.06 | 1.05–1.06 | 1.00 |
| operator over textbook, throughput, `x + y` | 3.38–3.50 | 3.37–3.40 | 1.19–1.28 | 1.16–1.25 | 1.18 | 4.38–4.41 | 1.14 | 1.14 | 1.12–1.13 |
| operator over textbook, throughput, `x + a` | 3.74–3.81 | 3.78–3.79 | 3.79–3.83 | 3.59–3.80 | 1.39–1.40 | 5.20–5.22 | 1.36 | 1.36–1.37 | 1.35 |
| operator over textbook, throughput, `add_fast(x, y)` | 3.09–3.14 | 3.11–3.14 | 3.60 | 3.50–3.60 | 1.23 | 3.65 | 1.15–1.16 | 1.16 | 1.18 |
| operator over textbook, throughput, `x * y` | 2.87–2.88 | 2.87 | 3.34–3.37 | 3.27–3.34 | 1.50–1.51 | 3.13–3.15 | 1.58 | 1.59 | 1.36–1.37 |
| operator over textbook, throughput, `x * a` | 2.88–2.95 | 2.93–2.94 | 3.38–3.39 | 3.38–3.39 | 1.66–1.67 | 3.74 | 1.58 | 1.58–1.59 | 1.56–1.57 |
| operator over textbook, sum chain, `s = s + x[i]` | 0.99–1.06 | 1.00–1.04 | 0.99–1.07 | 1.00–1.02 | 1.02 | 1.02 | 1.00–1.01 | 1.00–1.01 | 1.06 |
| operator over textbook, sum chain, `s = s + a[i]` | 1.00–1.01 | 1.01 | 1.03 | 1.03 | 1.05 | 1.05 | 1.00–1.01 | 1.00 | 1.06 |
| operator over textbook, sum chain, `s = add_fast(s, x[i])` | 0.99–1.02 | 1.01–1.02 | 1.01 | 1.01 | 0.99–1.00 | 0.99–1.00 | 1.00 | 1.00 | 1.06–1.07 |
| operator over textbook, product chain, `p = p * x[i]` | 0.98 | 0.98 | 1.00 | 1.00 | 1.12 | 1.12 | 1.08–1.09 | 1.08–1.09 | 1.11 |
| operator over textbook, product chain, `p = p * a[i]` | 0.99–1.01 | 0.99 | 1.01 | 1.01 | 1.14 | 1.14 | 1.33–1.34 | 1.33–1.34 | 1.04–1.05 |
| operator over textbook, Horner, `p = p * h + c[i]`, two-limb `h`, `c` | 0.99–1.03 | 0.99 | 1.02 | 1.00 | 1.06–1.07 | 1.06–1.07 | 1.03 | 1.03 | 1.08 |
| operator over textbook, Horner, `p = p * h + c[i]`, one-limb `h`, `c` | 0.97–1.00 | 1.00 | 1.01 | 1.01 | 1.09 | 1.09 | 1.04–1.05 | 1.05 | 1.07 |
| `Ball<float, 2>` over the center, throughput, `X + Y` | 1.29–1.31 | 1.30–1.31 | 1.24–1.27 | 1.17–1.30 | 1.32 | 0.92–0.93 | 1.28–1.29 | 1.28–1.29 | 1.25–1.26 |
| `Ball<float, 2>` over the center, throughput, `X * Y` | 1.95–2.02 | 1.95–1.96 | 1.80 | 1.79–1.83 | 1.88–1.90 | 1.93–1.94 | 1.55 | 1.55 | 2.19 |
| `Ball<float, 2>` over the center, throughput, `X * a` | 1.70–1.73 | 1.71 | 1.64–1.65 | 1.62–1.63 | 1.91–1.92 | 1.55 | 1.66–1.67 | 1.66 | 2.15–2.16 |
| `Ball<float, 2>` over the center, sum chain, `X + Y` | 0.97–1.00 | 0.97–1.03 | 0.94–1.01 | 0.99–1.01 | 1.02 | 1.01–1.02 | 1.00 | 1.00 | 0.99 |
| `Ball<float, 2>` over the center, product chain, `X * Y` | 1.02–1.04 | 1.04 | 1.04 | 1.05 | 0.98 | 0.98 | 0.99 | 0.99–1.00 | 1.03 |
| `Ball<float, 2>` over the center, Horner, `X * H + C` | 1.01–1.03 | 1.03 | 1.00 | 1.01 | 1.01 | 1.01 | 1.01–1.02 | 1.02 | 1.06 |
| `Ball<float, 1>` over `float`, throughput, `X + Y` | 10.37–10.64 | 10.35–10.38 | 1.19–1.21 | 4.73–4.84 | 3.15–3.17 | 9.21 | 17.38–17.40 | 20.03–20.13 | 19.11–19.64 |
| `Ball<float, 1>` over `float`, throughput, `X * Y` | 13.07–13.35 | 13.18–13.29 | 1.58 | 6.28–6.60 | 4.05–4.06 | 11.56–11.57 | 25.50–27.25 | 26.49–26.52 | 21.72–23.54 |
| `Ball<float, 1>` over `float`, sum chain, `X + Y` | 6.77–7.01 | 7.00–7.07 | 5.50–5.58 | 5.51–5.85 | 4.90–4.91 | 4.86 | 6.71–6.73 | 6.72–6.74 | 9.23–9.24 |
| `Ball<float, 1>` over `float`, product chain, `X * Y` | 6.30–6.32 | 6.35 | 6.74–6.75 | 6.01 | 9.54–9.56 | 9.56–9.58 | 11.17–11.18 | 11.16–11.17 | 8.26–8.27 |
| `float` over `double` (time per operation), throughput, `add_2_2` | 0.99–1.01 | 0.99–1.00 | 1.03–1.06 | 1.01–1.05 | 1.00 | 1.00 | 1.57 | 1.57 | 1.04–1.05 |
| `float` over `double` (time per operation), throughput, `mul_2_2` | 0.99–1.00 | 1.00 | 1.05–1.06 | 1.04–1.06 | 0.91 | 0.91 | 1.26 | 1.26 | 0.98 |
| `float` over `double` (time per operation), throughput, `ball_add_2` | 1.00–1.02 | 1.00 | 1.02 | 0.95–1.01 | 0.98 | 0.99–1.00 | 1.79–1.80 | 1.80 | 1.00–1.01 |
| `float` over `double` (time per operation), throughput, `ball_mul_2` | 0.99–1.00 | 1.00 | 1.05 | 1.05 | 0.93 | 1.08 | 1.57–1.58 | 1.58 | 0.83–0.84 |
| `float` over `double` (time per operation), sum chain, `add_2_2` | 0.99–1.02 | 1.00–1.01 | 1.00 | 0.95–1.00 | 1.00 | 1.00 | 1.25 | 1.25–1.26 | 1.03 |
| `float` over `double` (time per operation), product chain, `mul_2_2` | 0.97–0.99 | 0.97 | 0.96 | 0.96 | 1.00 | 1.00 | 1.16 | 1.16 | 0.94 |
| `float` over `double` (time per operation), sum chain, `ball_add_2` | 0.96–1.00 | 1.00 | 1.02 | 1.01 | 1.01 | 1.00–1.01 | 1.23 | 1.23 | 0.99 |
| `float` over `double` (time per operation), product chain, `ball_mul_2` | 0.95 | 0.95 | 0.98 | 0.98 | 1.00–1.01 | 1.00 | 1.12–1.13 | 1.12 | 0.84 |

Times, `float` limbs, public operators (ns):

| Operation (ns) | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, `add_2_2` | 1.5–1.55 | 1.49–1.5 | 1.63–1.67 | 1.58–1.66 | 4.42–4.44 | 4.42–4.43 | 4.24–4.27 | 4.25–4.26 | 2.45–2.46 |
| throughput, `mul_2_2` | 0.77–0.771 | 0.768–0.769 | 0.894 | 0.877–0.894 | 2.08–2.09 | 2.09–2.1 | 2.47–2.48 | 2.48–2.49 | 1.24–1.25 |
| throughput, `ball_add_2` | 1.95–2.03 | 1.95 | 2.06–2.07 | 1.93–2.06 | 5.85–5.87 | 4.09–4.1 | 5.45–5.47 | 5.45–5.47 | 3.09 |
| throughput, `ball_mul_2` | 1.5–1.56 | 1.5 | 1.6–1.61 | 1.6–1.61 | 3.93–3.96 | 4.03–4.06 | 3.83–3.85 | 3.84–3.85 | 2.72–2.73 |
| sum chain, `add_2_2` | 7.47–7.86 | 7.07–7.54 | 7.13–7.66 | 7.17–7.29 | 10.3–10.4 | 10.4 | 12.6 | 12.6 | 5.23 |
| product chain, `mul_2_2` | 5.12–5.71 | 5.11–5.12 | 5.18 | 5.21 | 8.29–8.32 | 8.28–8.31 | 9.34–9.4 | 9.34–9.37 | 5.41 |
| sum chain, `ball_add_2` | 7.31–7.83 | 7.3–7.33 | 7.21–7.23 | 7.21 | 10.5–10.6 | 10.4–10.6 | 12.5–12.6 | 12.6 | 5.19–5.2 |
| product chain, `ball_mul_2` | 5.32–5.82 | 5.32–5.34 | 5.4 | 5.46 | 8.14–8.19 | 8.14–8.16 | 9.28–9.33 | 9.29–9.32 | 5.55–5.57 |

### Machine code of the throughput loops

| Function | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---|---|---|---|---|---|---|---|---|
| `kb_a64_tp_add_2_2__finite` | 128-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 29 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 29 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 256-bit, 41 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 35 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 35 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 31 insns; 0 fma, 0 sel, 0 br, 0 call |
| `kb_a64_tp_add_2_2__op` | scalar, 32 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 43 insns; 0 fma, 0 sel, 3 br, 1 call | scalar, 43 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 43 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 34 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 34 insns; 0 fma, 0 sel, 1 br, 0 call | 128-bit, 42 insns; 0 fma, 2 sel, 0 br, 0 call | 128-bit, 42 insns; 0 fma, 2 sel, 0 br, 0 call | scalar, 40 insns; 0 fma, 1 sel, 2 br, 0 call |
| `kb_a64_tp_add_2_2__textbook` | 128-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 29 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 29 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 256-bit, 41 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 35 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 35 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 31 insns; 0 fma, 0 sel, 0 br, 0 call |
| `kb_a64_tp_mul_2_2__finite` | 128-bit, 21 insns; 5 fma, 0 sel, 0 br, 0 call | 128-bit, 21 insns; 5 fma, 0 sel, 0 br, 0 call | 128-bit, 22 insns; 5 fma, 0 sel, 0 br, 0 call | 128-bit, 22 insns; 5 fma, 0 sel, 0 br, 0 call | scalar, 21 insns; 5 fma, 0 sel, 0 br, 0 call | 256-bit, 33 insns; 5 fma, 0 sel, 0 br, 0 call | 128-bit, 26 insns; 5 fma, 0 sel, 0 br, 0 call | 128-bit, 26 insns; 5 fma, 0 sel, 0 br, 0 call | scalar, 25 insns; 5 fma, 0 sel, 0 br, 0 call |
| `kb_a64_tp_mul_2_2__op` | scalar, 21 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 32 insns; 5 fma, 0 sel, 3 br, 1 call | scalar, 32 insns; 5 fma, 1 sel, 2 br, 0 call | scalar, 32 insns; 5 fma, 1 sel, 2 br, 0 call | scalar, 26 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 26 insns; 5 fma, 0 sel, 1 br, 0 call | 128-bit, 33 insns; 5 fma, 2 sel, 0 br, 0 call | 128-bit, 33 insns; 5 fma, 2 sel, 0 br, 0 call | scalar, 34 insns; 5 fma, 1 sel, 2 br, 0 call |
| `kb_a64_tp_mul_2_2__textbook` | 128-bit, 19 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 19 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 20 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 20 insns; 3 fma, 0 sel, 0 br, 0 call | scalar, 19 insns; 3 fma, 0 sel, 0 br, 0 call | 256-bit, 31 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 24 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 24 insns; 3 fma, 0 sel, 0 br, 0 call | scalar, 27 insns; 3 fma, 0 sel, 0 br, 0 call |
| `kb_a64_tp_add_2_1__op` | scalar, 22 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 33 insns; 0 fma, 0 sel, 3 br, 1 call | scalar, 35 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 35 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 22 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 22 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 20 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 20 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 28 insns; 0 fma, 1 sel, 2 br, 0 call |
| `kb_a64_tp_mul_2_1__op` | scalar, 17 insns; 3 fma, 0 sel, 1 br, 0 call | scalar, 28 insns; 3 fma, 0 sel, 3 br, 1 call | scalar, 30 insns; 3 fma, 1 sel, 2 br, 0 call | scalar, 30 insns; 3 fma, 1 sel, 2 br, 0 call | scalar, 19 insns; 3 fma, 0 sel, 1 br, 0 call | scalar, 19 insns; 3 fma, 0 sel, 1 br, 0 call | scalar, 17 insns; 3 fma, 0 sel, 1 br, 0 call | scalar, 17 insns; 3 fma, 0 sel, 1 br, 0 call | scalar, 28 insns; 3 fma, 1 sel, 2 br, 0 call |
| `kb_a64_tp_ball_add_2__kairn` | 128-bit, 30 insns; 2 fma, 0 sel, 0 br, 0 call | 128-bit, 30 insns; 2 fma, 0 sel, 0 br, 0 call | 128-bit, 34 insns; 2 fma, 0 sel, 0 br, 0 call | 128-bit, 34 insns; 2 fma, 0 sel, 0 br, 0 call | scalar, 37 insns; 2 fma, 0 sel, 0 br, 0 call | 256-bit, 73 insns; 2 fma, 10 sel, 0 br, 0 call | 128-bit, 45 insns; 2 fma, 0 sel, 0 br, 0 call | 128-bit, 45 insns; 2 fma, 0 sel, 0 br, 0 call | scalar, 38 insns; 2 fma, 0 sel, 0 br, 0 call |
| `kb_a64_tp_ball_add_2__op` | scalar, 46 insns; 2 fma, 2 sel, 2 br, 0 call | scalar, 58 insns; 2 fma, 2 sel, 4 br, 1 call | scalar, 44 insns; 2 fma, 0 sel, 1 br, 0 call | scalar, 44 insns; 2 fma, 0 sel, 1 br, 0 call | scalar, 60 insns; 2 fma, 0 sel, 5 br, 0 call | 256-bit, 89 insns; 2 fma, 14 sel, 0 br, 0 call | 256-bit, 82 insns; 2 fma, 8 sel, 0 br, 0 call | 256-bit, 82 insns; 2 fma, 8 sel, 0 br, 0 call | scalar, 88 insns; 2 fma, 7 sel, 3 br, 0 call |
| `kb_a64_tp_ball_mul_2__kairn` | 128-bit, 27 insns; 10 fma, 0 sel, 0 br, 0 call | 128-bit, 27 insns; 10 fma, 0 sel, 0 br, 0 call | 128-bit, 32 insns; 10 fma, 0 sel, 0 br, 0 call | 128-bit, 32 insns; 10 fma, 0 sel, 0 br, 0 call | scalar, 39 insns; 10 fma, 0 sel, 0 br, 0 call | 256-bit, 69 insns; 10 fma, 10 sel, 0 br, 0 call | 256-bit, 67 insns; 10 fma, 4 sel, 0 br, 0 call | 256-bit, 67 insns; 10 fma, 4 sel, 0 br, 0 call | scalar, 49 insns; 10 fma, 0 sel, 0 br, 0 call |
| `kb_a64_tp_ball_mul_2__op` | scalar, 40 insns; 10 fma, 2 sel, 2 br, 0 call | scalar, 52 insns; 10 fma, 2 sel, 4 br, 1 call | scalar, 38 insns; 10 fma, 0 sel, 1 br, 0 call | scalar, 40 insns; 10 fma, 0 sel, 1 br, 0 call | scalar, 62 insns; 10 fma, 0 sel, 5 br, 0 call | 256-bit, 84 insns; 10 fma, 14 sel, 0 br, 0 call | 256-bit, 78 insns; 10 fma, 8 sel, 0 br, 0 call | 256-bit, 78 insns; 10 fma, 8 sel, 0 br, 0 call | scalar, 100 insns; 10 fma, 7 sel, 3 br, 0 call |
| `kb_a64_tp_ball_add_1__op` | scalar, 23 insns; 2 fma, 2 sel, 2 br, 0 call | scalar, 32 insns; 2 fma, 2 sel, 4 br, 1 call | 128-bit, 27 insns; 2 fma, 3 sel, 0 br, 0 call | 128-bit, 27 insns; 2 fma, 3 sel, 0 br, 0 call | scalar, 34 insns; 2 fma, 0 sel, 5 br, 0 call | 256-bit, 37 insns; 2 fma, 4 sel, 0 br, 0 call | 128-bit, 29 insns; 2 fma, 3 sel, 0 br, 0 call | 128-bit, 29 insns; 2 fma, 3 sel, 0 br, 0 call | scalar, 209 insns; 8 fma, 20 sel, 12 br, 0 call |
| `kb_a64_tp_ball_mul_1__op` | scalar, 28 insns; 6 fma, 2 sel, 2 br, 0 call | scalar, 37 insns; 6 fma, 2 sel, 4 br, 1 call | 128-bit, 33 insns; 6 fma, 3 sel, 0 br, 0 call | 128-bit, 33 insns; 6 fma, 3 sel, 0 br, 0 call | scalar, 43 insns; 6 fma, 0 sel, 5 br, 0 call | 256-bit, 43 insns; 6 fma, 4 sel, 0 br, 0 call | 256-bit, 50 insns; 6 fma, 3 sel, 0 br, 0 call | 256-bit, 50 insns; 6 fma, 3 sel, 0 br, 0 call | scalar, 73 insns; 6 fma, 5 sel, 3 br, 0 call |
| `kb_tp_add_2_2__kairn` | 128-bit, 28 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 28 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 128-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | scalar, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 256-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 256-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 256-bit, 29 insns; 0 fma, 0 sel, 0 br, 0 call | 256-bit, 30 insns; 0 fma, 0 sel, 0 br, 0 call |
| `kb_tp_add_2_2__full` | scalar, 32 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 51 insns; 0 fma, 0 sel, 3 br, 1 call | scalar, 46 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 46 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 34 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 34 insns; 0 fma, 0 sel, 1 br, 0 call | 256-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | 256-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | scalar, 144 insns; 0 fma, 4 sel, 8 br, 0 call |
| `kb_tp_add_2_2__full_sel` | 128-bit, 39 insns; 0 fma, 1 sel, 0 br, 0 call | 128-bit, 39 insns; 0 fma, 1 sel, 0 br, 0 call | scalar, 35 insns; 0 fma, 1 sel, 1 br, 0 call | scalar, 43 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 40 insns; 0 fma, 1 sel, 1 br, 0 call | scalar, 49 insns; 0 fma, 1 sel, 2 br, 0 call | 256-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | 256-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | scalar, 188 insns; 0 fma, 12 sel, 0 br, 0 call |
| `kb_tp_mul_2_2__kairn` | 128-bit, 38 insns; 10 fma, 0 sel, 0 br, 0 call | 128-bit, 38 insns; 10 fma, 0 sel, 0 br, 0 call | 128-bit, 21 insns; 5 fma, 0 sel, 0 br, 0 call | 128-bit, 21 insns; 5 fma, 0 sel, 0 br, 0 call | scalar, 21 insns; 5 fma, 0 sel, 0 br, 0 call | 256-bit, 19 insns; 5 fma, 0 sel, 0 br, 0 call | 256-bit, 20 insns; 5 fma, 0 sel, 0 br, 0 call | 256-bit, 20 insns; 5 fma, 0 sel, 0 br, 0 call | scalar, 88 insns; 20 fma, 0 sel, 0 br, 0 call |
| `kb_tp_mul_2_2__full` | scalar, 21 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 40 insns; 5 fma, 0 sel, 3 br, 1 call | scalar, 35 insns; 5 fma, 1 sel, 2 br, 0 call | scalar, 35 insns; 5 fma, 1 sel, 2 br, 0 call | scalar, 26 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 26 insns; 5 fma, 0 sel, 1 br, 0 call | 256-bit, 27 insns; 5 fma, 2 sel, 0 br, 0 call | 256-bit, 27 insns; 5 fma, 2 sel, 0 br, 0 call | scalar, 124 insns; 20 fma, 4 sel, 8 br, 0 call |
| `kb_tp_mul_2_2__full_sel` | 128-bit, 31 insns; 5 fma, 1 sel, 0 br, 0 call | 128-bit, 31 insns; 5 fma, 1 sel, 0 br, 0 call | scalar, 24 insns; 5 fma, 1 sel, 1 br, 0 call | scalar, 32 insns; 5 fma, 1 sel, 2 br, 0 call | scalar, 33 insns; 5 fma, 1 sel, 1 br, 0 call | scalar, 41 insns; 5 fma, 1 sel, 2 br, 0 call | 256-bit, 27 insns; 5 fma, 2 sel, 0 br, 0 call | 256-bit, 27 insns; 5 fma, 2 sel, 0 br, 0 call | scalar, 168 insns; 20 fma, 12 sel, 0 br, 0 call |
| `kb_tp_mul_2_2__plain` | 128-bit, 18 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 18 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 19 insns; 3 fma, 0 sel, 0 br, 0 call | 128-bit, 19 insns; 3 fma, 0 sel, 0 br, 0 call | scalar, 19 insns; 3 fma, 0 sel, 0 br, 0 call | 256-bit, 18 insns; 3 fma, 0 sel, 0 br, 0 call | 256-bit, 18 insns; 3 fma, 0 sel, 0 br, 0 call | 256-bit, 18 insns; 3 fma, 0 sel, 0 br, 0 call | scalar, 92 insns; 12 fma, 0 sel, 0 br, 0 call |
| `kb_tp_two_prod__kairn` | 128-bit, 18 insns; 4 fma, 0 sel, 0 br, 0 call | 128-bit, 18 insns; 4 fma, 0 sel, 0 br, 0 call | scalar, 9 insns; 2 fma, 0 sel, 0 br, 0 call | 128-bit, 11 insns; 2 fma, 0 sel, 0 br, 0 call | scalar, 10 insns; 2 fma, 0 sel, 0 br, 0 call | 256-bit, 9 insns; 2 fma, 0 sel, 0 br, 0 call | 256-bit, 17 insns; 4 fma, 0 sel, 0 br, 0 call | 256-bit, 17 insns; 4 fma, 0 sel, 0 br, 0 call | scalar, 36 insns; 8 fma, 0 sel, 0 br, 0 call |
| `kb_tp_two_prod__plain` | 128-bit, 16 insns; 2 fma, 0 sel, 0 br, 0 call | 128-bit, 16 insns; 2 fma, 0 sel, 0 br, 0 call | scalar, 9 insns; 1 fma, 0 sel, 0 br, 0 call | 128-bit, 10 insns; 1 fma, 0 sel, 0 br, 0 call | scalar, 9 insns; 1 fma, 0 sel, 0 br, 0 call | 256-bit, 9 insns; 1 fma, 0 sel, 0 br, 0 call | 256-bit, 15 insns; 2 fma, 0 sel, 0 br, 0 call | 256-bit, 15 insns; 2 fma, 0 sel, 0 br, 0 call | 256-bit, 33 insns; 4 fma, 0 sel, 0 br, 0 call |
| `kb_ptp_add_2_2__full` | 128-bit, 39 insns; 0 fma, 1 sel, 0 br, 0 call | 128-bit, 39 insns; 0 fma, 1 sel, 0 br, 0 call | 128-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | 128-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | 256-bit, 38 insns; 0 fma, 2 sel, 0 br, 0 call | 256-bit, 38 insns; 0 fma, 2 sel, 0 br, 0 call | 256-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | 256-bit, 36 insns; 0 fma, 2 sel, 0 br, 0 call | 256-bit, 38 insns; 0 fma, 3 sel, 0 br, 0 call |
| `kb_ptp_mul_2_2__full` | 128-bit, 31 insns; 5 fma, 1 sel, 0 br, 0 call | 128-bit, 31 insns; 5 fma, 1 sel, 0 br, 0 call | 128-bit, 28 insns; 5 fma, 2 sel, 0 br, 0 call | 128-bit, 28 insns; 5 fma, 2 sel, 0 br, 0 call | 256-bit, 28 insns; 5 fma, 2 sel, 0 br, 0 call | 256-bit, 28 insns; 5 fma, 2 sel, 0 br, 0 call | 256-bit, 27 insns; 5 fma, 2 sel, 0 br, 0 call | 256-bit, 27 insns; 5 fma, 2 sel, 0 br, 0 call | 256-bit, 30 insns; 5 fma, 3 sel, 0 br, 0 call |
| `kb_ptp_ball_add_2__full` | 128-bit, 51 insns; 2 fma, 4 sel, 0 br, 0 call | 128-bit, 51 insns; 2 fma, 4 sel, 0 br, 0 call | 128-bit, 48 insns; 2 fma, 4 sel, 0 br, 0 call | 128-bit, 48 insns; 2 fma, 4 sel, 0 br, 0 call | 256-bit, 48 insns; 2 fma, 4 sel, 0 br, 0 call | 256-bit, 48 insns; 2 fma, 4 sel, 0 br, 0 call | 256-bit, 46 insns; 2 fma, 4 sel, 0 br, 0 call | 256-bit, 46 insns; 2 fma, 4 sel, 0 br, 0 call | 256-bit, 49 insns; 2 fma, 6 sel, 0 br, 0 call |
| `kb_ptp_ball_mul_2__full` | 128-bit, 48 insns; 10 fma, 4 sel, 0 br, 0 call | 128-bit, 48 insns; 10 fma, 4 sel, 0 br, 0 call | 128-bit, 45 insns; 10 fma, 4 sel, 0 br, 0 call | 128-bit, 45 insns; 10 fma, 4 sel, 0 br, 0 call | 256-bit, 44 insns; 10 fma, 4 sel, 0 br, 0 call | 256-bit, 44 insns; 10 fma, 4 sel, 0 br, 0 call | 256-bit, 43 insns; 10 fma, 4 sel, 0 br, 0 call | 256-bit, 43 insns; 10 fma, 4 sel, 0 br, 0 call | 256-bit, 47 insns; 10 fma, 6 sel, 0 br, 0 call |
| `kb_a32_tp_add_2_2__op` | scalar, 32 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 43 insns; 0 fma, 0 sel, 3 br, 1 call | scalar, 42 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 42 insns; 0 fma, 1 sel, 2 br, 0 call | scalar, 34 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 34 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 32 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 32 insns; 0 fma, 0 sel, 1 br, 0 call | scalar, 38 insns; 0 fma, 1 sel, 2 br, 0 call |
| `kb_a32_tp_mul_2_2__op` | scalar, 21 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 32 insns; 5 fma, 0 sel, 3 br, 1 call | scalar, 31 insns; 5 fma, 1 sel, 2 br, 0 call | scalar, 31 insns; 5 fma, 1 sel, 2 br, 0 call | scalar, 26 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 26 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 23 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 23 insns; 5 fma, 0 sel, 1 br, 0 call | scalar, 35 insns; 5 fma, 1 sel, 2 br, 0 call |
| `kb_a32_tp_ball_add_2__op` | scalar, 46 insns; 2 fma, 2 sel, 2 br, 0 call | scalar, 58 insns; 2 fma, 2 sel, 4 br, 1 call | scalar, 43 insns; 2 fma, 0 sel, 1 br, 0 call | scalar, 43 insns; 2 fma, 0 sel, 1 br, 0 call | scalar, 60 insns; 2 fma, 0 sel, 5 br, 0 call | 256-bit, 153 insns; 2 fma, 40 sel, 0 br, 0 call | scalar, 44 insns; 2 fma, 0 sel, 2 br, 0 call | scalar, 44 insns; 2 fma, 0 sel, 2 br, 0 call | scalar, 86 insns; 2 fma, 7 sel, 3 br, 0 call |
| `kb_a32_tp_ball_mul_2__op` | scalar, 40 insns; 10 fma, 2 sel, 2 br, 0 call | scalar, 52 insns; 10 fma, 2 sel, 4 br, 1 call | scalar, 37 insns; 10 fma, 0 sel, 1 br, 0 call | scalar, 37 insns; 10 fma, 0 sel, 1 br, 0 call | scalar, 62 insns; 10 fma, 0 sel, 5 br, 0 call | 256-bit, 152 insns; 10 fma, 40 sel, 0 br, 0 call | scalar, 41 insns; 10 fma, 0 sel, 2 br, 0 call | scalar, 41 insns; 10 fma, 0 sel, 2 br, 0 call | scalar, 97 insns; 10 fma, 7 sel, 3 br, 0 call |

### Every function

| Function (ns) | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `scalar/tp/two_prod/kairn` | 0.173–0.18 | 0.186 | 0.332–0.333 | 0.179–0.18 | 0.632–0.635 | 0.236–0.238 | 0.165 | 0.164 | 0.441 |
| `scalar/tp/two_prod/plain` | 0.186–0.192 | 0.186 | 0.332 | 0.178–0.181 | 0.632–0.634 | 0.179–0.18 | 0.162–0.163 | 0.163 | 0.658 |
| `scalar/tp/mul_2_1/kairn` | 0.244–0.246 | 0.244 | 0.287–0.288 | 0.287 | 1.23 | 0.278–0.279 | 0.275–0.278 | 0.276–0.277 | 0.643 |
| `scalar/tp/mul_2_1/plain` | 0.24–0.251 | 0.24–0.241 | 0.456 | 0.259 | 1.04–1.05 | 0.258–0.259 | 0.256–0.258 | 0.257–0.258 | 0.744–0.745 |
| `scalar/tp/mul_2_1/full` | 0.587–0.612 | 0.592 | 0.592–0.593 | 0.593 | 1.85–1.86 | 1.85–1.86 | 0.561–0.564 | 0.562–0.563 | 1.05 |
| `scalar/tp/mul_2_2/kairn` | 0.346–0.361 | 0.346 | 0.353 | 0.351–0.352 | 1.8–1.81 | 0.38–0.382 | 0.384–0.387 | 0.381–0.384 | 0.977–0.979 |
| `scalar/tp/mul_2_2/plain` | 0.35–0.365 | 0.351–0.352 | 0.349–0.35 | 0.35–0.351 | 1.45–1.46 | 0.348–0.35 | 0.358–0.361 | 0.375–0.378 | 0.997–0.998 |
| `scalar/tp/mul_2_2/textbook` | 0.351–0.357 | 0.352 | 0.35–0.351 | 0.349–0.35 | 1.45–1.46 | 0.349–0.351 | 0.359–0.362 | 0.359–0.361 | 0.997–0.998 |
| `scalar/tp/mul_2_2/full` | 0.729–0.733 | 0.728–0.729 | 0.777–0.779 | 0.776–0.779 | 2.31 | 2.3–2.32 | 0.663–0.667 | 0.663–0.665 | 1.34–1.35 |
| `scalar/tp/mul_2_2/full_sel` | 0.742–0.744 | 0.743–0.744 | 1.08 | 0.975 | 2.96–2.97 | 2.76–2.77 | 0.666–0.669 | 0.666–0.668 | 2.89 |
| `scalar/tp/add_2_2/kairn` | 0.698–0.708 | 0.698–0.699 | 0.702–0.703 | 0.703–0.704 | 3.73–3.78 | 0.948–0.949 | 0.949–0.954 | 0.95–0.953 | 0.551–0.552 |
| `scalar/tp/add_2_2/textbook` | 0.696–0.724 | 0.697–0.698 | 0.7–0.703 | 0.703–0.704 | 3.64–3.67 | 0.947–0.954 | 0.93–0.934 | 0.931–0.935 | 0.546–0.548 |
| `scalar/tp/add_2_2/full` | 1.45–1.47 | 1.45 | 1.54 | 1.42–1.53 | 4.42–4.43 | 4.42–4.44 | 1.1–1.11 | 1.1–1.11 | 2.34 |
| `scalar/tp/add_2_2/full_sel` | 1.11–1.16 | 1.11 | 1.82 | 1.69–1.72 | 4.51–4.55 | 4.44–4.47 | 1.11 | 1.11 | 3.38 |
| `scalar/tp/add_2_1/kairn` | 0.369–0.384 | 0.369 | 0.382–0.383 | 0.381–0.382 | 2.36–2.37 | 0.589–0.592 | 0.586–0.589 | 0.584–0.588 | 0.301–0.302 |
| `scalar/tp/add_2_1/full` | 0.849–0.884 | 0.849–0.85 | 0.897–0.899 | 0.897–0.899 | 2.91–2.92 | 2.91–2.92 | 0.773–0.775 | 0.774–0.78 | 1.37 |
| `scalar/tp/add_fast_2_2/kairn` | 0.369–0.384 | 0.369 | 0.383 | 0.384 | 2.19–2.21 | 0.543–0.546 | 0.544–0.549 | 0.545–0.547 | 0.311 |
| `scalar/tp/add_fast_2_2/textbook` | 0.368–0.384 | 0.368 | 0.383 | 0.384 | 2.18–2.2 | 0.541–0.545 | 0.542–0.549 | 0.542–0.545 | 0.309 |
| `scalar/tp/add_fast_2_2/full` | 0.839–0.875 | 0.839–0.84 | 0.898–0.901 | 0.899–0.9 | 2.72–2.74 | 2.72–2.73 | 0.678–0.682 | 0.679–0.681 | 1.35 |
| `scalar/tp/neg_2/kairn` | 0.186–0.194 | 0.186 | 0.316–0.324 | 0.18 | 0.631–0.633 | 0.161–0.162 | 0.162–0.163 | 0.161–0.162 | 0.113 |
| `scalar/tp/ball_add_2/kairn` | 0.86 | 0.859–0.86 | 0.841–0.843 | 0.847–0.849 | 4.86–4.89 | 1.15–1.16 | 1.17 | 1.17 | 2.41 |
| `scalar/tp/ball_add_2/full` | 1.92 | 1.92 | 1.97–1.98 | 1.98–2 | 5.97–6.02 | 2.01–2.02 | 1.73 | 1.73 | 3.02 |
| `scalar/tp/ball_add_2/full_sel` | 1.45–1.46 | 1.45 | 2.24 | 2.11–2.22 | 6.16–6.19 | 5.96–5.98 | 1.71–1.72 | 1.71–1.72 | 6.31 |
| `scalar/tp/ball_mul_2/kairn` | 0.627–0.635 | 0.63–0.631 | 0.633–0.635 | 0.632–0.633 | 3.26–3.27 | 0.695–0.699 | 0.701–0.704 | 0.701–0.704 | 2.33–2.34 |
| `scalar/tp/ball_mul_2/plain` | 0.623 | 0.624 | 0.622–0.623 | 0.622–0.623 | 2.79–2.8 | 0.677–0.68 | 0.69–0.693 | 0.691–0.693 | 2.39 |
| `scalar/tp/ball_mul_2/full` | 1.46 | 1.46 | 1.45–1.49 | 1.44–1.49 | 4.25–4.28 | 1.48–1.49 | 1.28–1.29 | 1.28–1.29 | 3.3 |
| `scalar/tp/ball_mul_2/full_sel` | 1.18–1.22 | 1.19 | 1.66 | 1.63–1.65 | 4.63–4.65 | 4.2–4.21 | 1.28–1.29 | 1.28–1.29 | 6.28–6.29 |
| `scalar/tp/ball_scale_2/kairn` | 0.437–0.456 | 0.436 | 0.427–0.428 | 0.425–0.426 | 2.35 | 0.505–0.507 | 0.514–0.516 | 0.513–0.515 | 1.49 |
| `scalar/tp/ball_scale_2/full` | 1.06–1.1 | 1.06 | 1.01 | 1.01 | 3.42–3.44 | 1.26–1.27 | 1.07 | 1.07 | 2.6–2.61 |
| `scalar/tp/ball_neg_2/kairn` | 0.27–0.279 | 0.27 | 0.398–0.4 | 0.379–0.38 | 0.697–0.701 | 0.365–0.367 | 0.255–0.256 | 0.255 | 0.168–0.169 |
| `scalar/tp/ball_add_1/kairn` | 0.24–0.255 | 0.233 | 0.502–0.503 | 0.234 | 1.14–1.15 | 0.226 | 0.238–0.239 | 0.239 | 0.581–0.584 |
| `scalar/tp/ball_add_1/full` | 0.767–0.781 | 0.767–0.768 | 0.549 | 0.55 | 2.05–2.06 | 0.695–0.697 | 0.49–0.492 | 0.49–0.492 | 1.62 |
| `scalar/tp/ball_mul_1/kairn` | 0.321–0.322 | 0.321 | 0.62–0.629 | 0.321–0.322 | 1.57–1.58 | 0.415–0.416 | 0.37–0.372 | 0.371–0.372 | 1.38–1.4 |
| `scalar/tp/ball_mul_1/full` | 0.961–0.972 | 0.943 | 0.698 | 0.698 | 2.4–2.42 | 0.987–0.99 | 0.746–0.749 | 0.745–0.747 | 2.29–2.3 |
| `scalar/tp/ball_scale_1/kairn` | 0.255–0.266 | 0.255 | 0.558–0.56 | 0.288 | 0.958–0.969 | 0.251–0.252 | 0.243–0.245 | 0.244 | 0.881–0.882 |
| `scalar/tp/ball_scale_1/full` | 0.768–0.795 | 0.767–0.77 | 0.56–0.561 | 0.559–0.56 | 2.08 | 0.775–0.78 | 0.557–0.562 | 0.559–0.56 | 1.82 |
| `scalar/tp/ball_neg_1/kairn` | 0.175–0.181 | 0.175 | 0.377 | 0.226–0.227 | 0.405–0.406 | 0.178–0.179 | 0.174–0.176 | 0.175–0.176 | 0.112–0.113 |
| `scalar/tp/add_1_1/kairn` | 0.104–0.108 | 0.104 | 0.296 | 0.152–0.155 | 0.628–0.633 | 0.165–0.166 | 0.121–0.124 | 0.121–0.122 | 0.0608–0.0612 |
| `scalar/tp/add_1_1/double` | 0.104–0.106 | 0.104 | 0.296 | 0.155 | 0.629–0.632 | 0.101 | 0.121–0.124 | 0.121–0.122 | 0.061 |
| `scalar/tp/mul_1_1/kairn` | 0.102–0.106 | 0.102–0.103 | 0.296 | 0.155 | 0.333–0.335 | 0.165–0.166 | 0.122–0.125 | 0.122 | 0.0891–0.0903 |
| `scalar/tp/mul_1_1/double` | 0.103–0.107 | 0.103 | 0.296 | 0.155 | 0.629–0.631 | 0.165–0.166 | 0.121–0.124 | 0.121–0.122 | 0.061–0.0611 |
| `scalar/tp/neg_1/kairn` | 0.0896–0.0934 | 0.0895–0.0897 | 0.296 | 0.151–0.155 | 0.631–0.633 | 0.0962–0.0971 | 0.0861–0.0895 | 0.0862–0.0863 | 0.0463–0.0464 |
| `scalar/sum/add_2_2/kairn` | 7.58–7.91 | 7.59 | 7.23–7.64 | 7.33–7.64 | 10.2 | 10.2 | 9.99–10 | 9.99–10.1 | 4.92–4.93 |
| `scalar/sum/add_2_2/textbook` | 7.17–7.79 | 7.31–7.6 | 7.17–7.7 | 7.18–7.7 | 10–10.1 | 10–10.1 | 10 | 10–10.1 | 4.89 |
| `scalar/sum/add_2_2/full` | 7.04–7.66 | 7.11–7.55 | 7.12–7.64 | 7.17–7.68 | 10.3 | 10.3 | 10–10.1 | 10–10.1 | 5.13 |
| `scalar/sum/add_2_2/full_sel` | 10.1–11.2 | 10–10.8 | 7.7–8.27 | 7.68–8.24 | 10.3–10.4 | 10.3 | 11 | 11 | 8.65 |
| `scalar/sum/add_2_1/kairn` | 4.46–4.97 | 4.46–4.64 | 4.43–4.56 | 4.43–4.54 | 6.54–6.57 | 6.51–6.56 | 6.53–6.57 | 6.45–6.56 | 3.15–3.16 |
| `scalar/sum/add_2_1/full` | 4.4–4.73 | 4.39–4.41 | 4.47–4.48 | 4.47–4.48 | 6.56–6.59 | 6.57–6.59 | 6.52–6.56 | 6.48–6.56 | 3.3 |
| `scalar/sum/add_fast_2_2/kairn` | 4.45–4.84 | 4.45–4.5 | 4.44–4.45 | 4.44–4.45 | 6.54–6.57 | 6.54–6.56 | 6.35–6.4 | 6.36–6.38 | 3.1 |
| `scalar/sum/add_fast_2_2/textbook` | 4.36–4.76 | 4.35–4.39 | 4.47–4.48 | 4.47–4.48 | 6.54–6.56 | 6.53–6.56 | 6.36–6.4 | 6.36–6.39 | 3.12 |
| `scalar/sum/add_fast_2_2/full` | 4.42–4.92 | 4.42–4.43 | 4.5 | 4.5 | 6.5–6.52 | 6.51–6.54 | 6.44–6.48 | 6.45–6.47 | 3.27 |
| `scalar/sum/ball_add_2/kairn` | 7.17–7.71 | 7.17–7.21 | 7.24 | 7.18–7.19 | 10.3–10.4 | 10.3–10.4 | 10.2 | 10.2 | 5.17 |
| `scalar/sum/ball_add_2/full` | 7.3–8.15 | 7.29–7.49 | 7.1–7.11 | 7.16–7.17 | 10.4–10.5 | 10.4–10.5 | 10.2–10.3 | 10.2–10.3 | 5.19 |
| `scalar/sum/ball_add_2/full_sel` | 13–14.5 | 12.9–13.2 | 7.73–7.74 | 7.66 | 13.2 | 10.4 | 10.7–10.8 | 10.7–10.8 | 12.2 |
| `scalar/sum/ball_add_1/kairn` | 2.16–2.42 | 2.16–2.17 | 2.23–2.24 | 2.23–2.24 | 3.75–3.77 | 3.75–3.76 | 3.74–3.77 | 3.75 | 2.71 |
| `scalar/sum/ball_add_1/full` | 2.61–2.91 | 2.6–2.61 | 2.57 | 2.57 | 3.85–3.87 | 3.85–3.87 | 3.85–3.88 | 3.85–3.86 | 3.37 |
| `scalar/sum/add_1_1/kairn` | 0.376–0.401 | 0.368–0.373 | 0.469–0.478 | 0.47–0.475 | 0.792–0.798 | 0.794–0.795 | 0.793–0.798 | 0.793–0.795 | 0.281 |
| `scalar/sum/add_1_1/double` | 0.369–0.411 | 0.366–0.377 | 0.468–0.472 | 0.468–0.488 | 0.794–0.797 | 0.793–0.796 | 0.792–0.799 | 0.794–0.797 | 0.281 |
| `scalar/prod/two_prod/kairn` | 0.821–0.917 | 0.821–0.845 | 0.894–0.896 | 0.893–0.959 | 1.72 | 1.71–1.72 | 1.53–1.54 | 1.53–1.54 | 1.55 |
| `scalar/prod/two_prod/plain` | 0.819–0.913 | 0.816–0.877 | 0.888–0.932 | 0.889–0.953 | 1.08–1.09 | 1.07–1.08 | 0.98–0.986 | 0.982–0.984 | 0.828–0.835 |
| `scalar/prod/mul_2_1/kairn` | 3.34–3.67 | 3.34–3.44 | 3.33–3.43 | 3.34–3.43 | 5.31–5.34 | 5.31–5.33 | 5.3–5.33 | 5.3–5.33 | 4.79–4.8 |
| `scalar/prod/mul_2_1/plain` | 3.34–3.61 | 3.34–3.38 | 3.33–3.34 | 3.34 | 4.72–4.74 | 4.71–4.74 | 4.71–4.75 | 4.72–4.73 | 4.29 |
| `scalar/prod/mul_2_1/full` | 3.42–3.71 | 3.42 | 3.45–3.46 | 3.45–3.46 | 5.35–5.37 | 5.35–5.37 | 5.49–5.53 | 5.5–5.52 | 4.82 |
| `scalar/prod/mul_2_2/kairn` | 5.3–5.69 | 5.3–5.32 | 5.26 | 5.25 | 8.01–8.05 | 8–8.04 | 8.07–8.09 | 8.07–8.09 | 5.74–5.75 |
| `scalar/prod/mul_2_2/plain` | 5.3–5.69 | 5.3–5.31 | 5.25–5.26 | 5.25–5.26 | 7.41–7.45 | 7.4–7.43 | 7.41–7.44 | 7.42–7.43 | 5.21–5.22 |
| `scalar/prod/mul_2_2/textbook` | 5.31–5.74 | 5.31–5.32 | 5.26 | 5.26 | 7.41–7.44 | 7.41–7.43 | 7.4–7.45 | 7.41–7.43 | 5.21 |
| `scalar/prod/mul_2_2/full` | 5.27–5.73 | 5.26–5.27 | 5.41–5.42 | 5.42 | 8.32–8.35 | 8.31–8.34 | 8.08–8.13 | 8.07–8.09 | 5.89 |
| `scalar/prod/mul_2_2/full_sel` | 7.16–7.78 | 7.16 | 5.32 | 5.36 | 8.12–8.16 | 8.11–8.12 | 8.16–8.2 | 8.18–8.19 | 8.86–8.87 |
| `scalar/prod/ball_mul_2/kairn` | 5.53–6.17 | 5.52–5.55 | 5.52 | 5.53–5.54 | 8.08–8.11 | 8.06–8.1 | 8.12–8.16 | 8.13–8.15 | 6.8 |
| `scalar/prod/ball_mul_2/plain` | 5.54–6.19 | 5.53–5.54 | 5.51–5.52 | 5.54–5.55 | 7.56–7.59 | 7.55–7.58 | 7.58–7.63 | 7.59–7.61 | 6.07 |
| `scalar/prod/ball_mul_2/full` | 5.58–6.14 | 5.58–5.59 | 5.57–5.58 | 5.55–5.56 | 8.12–8.16 | 8.11–8.15 | 8.26–8.31 | 8.26–8.29 | 6.68–6.7 |
| `scalar/prod/ball_mul_2/full_sel` | 10.6–11.8 | 10.6 | 6.11–6.12 | 6.15–6.3 | 10.7 | 8.27–8.3 | 8.38–8.41 | 8.38–8.41 | 12.1–12.2 |
| `scalar/prod/ball_scale_2/kairn` | 3.5–3.77 | 3.5–3.51 | 3.53–3.55 | 3.51–3.76 | 5.46–5.49 | 5.46–5.49 | 5.47–5.5 | 5.48–5.49 | 5.05 |
| `scalar/prod/ball_scale_2/full` | 3.61–4 | 3.61–3.63 | 3.64–3.69 | 3.65–3.66 | 5.71–5.75 | 5.7–5.73 | 5.53–5.57 | 5.54–5.55 | 4.82–4.85 |
| `scalar/prod/ball_mul_1/kairn` | 4.34–4.76 | 4.34–4.39 | 4.41–4.49 | 4.4–4.46 | 7.33–7.38 | 7.32–7.35 | 7.31–7.35 | 7.32–7.34 | 6.41 |
| `scalar/prod/ball_mul_1/full` | 4.69–5.15 | 4.69–4.73 | 5.12 | 4.67 | 8.11–8.15 | 8.1–8.14 | 7.59–7.68 | 7.62–7.64 | 6.51–6.52 |
| `scalar/prod/ball_scale_1/kairn` | 2.36–2.55 | 2.36–2.37 | 2.42–2.43 | 2.42–2.43 | 4.33–4.34 | 4.32–4.34 | 4.32–4.35 | 4.32–4.33 | 4.04 |
| `scalar/prod/ball_scale_1/full` | 2.84–3.05 | 2.83 | 3.25 | 3.25 | 4.79–4.81 | 4.78–4.82 | 4.48–4.5 | 4.48–4.5 | 4.01 |
| `scalar/prod/mul_1_1/kairn` | 0.715–0.785 | 0.715–0.719 | 0.71–0.711 | 0.711–0.712 | 1.32 | 1.31–1.32 | 1.31–1.32 | 1.31–1.32 | 0.544 |
| `scalar/prod/mul_1_1/double` | 0.717–0.765 | 0.718 | 0.715–0.716 | 0.715–0.717 | 0.794–0.796 | 0.793–0.795 | 0.792–0.796 | 0.792–0.795 | 0.543–0.544 |
| `scalar/horner/mul_2_2+add_2_2/kairn` | 12.7–13.8 | 12.7 | 12.6 | 12.6 | 18.3–18.4 | 18.3 | 18.1–18.2 | 18.2 | 10.8 |
| `scalar/horner/mul_2_2+add_2_2/plain` | 12.7–14.2 | 12.7 | 12.6 | 12.6 | 17.6–17.7 | 17.6–17.7 | 17.6–17.7 | 17.6 | 10.3 |
| `scalar/horner/mul_2_2+add_2_2/textbook` | 12.7–13.9 | 12.7 | 12.6 | 12.6 | 17.4 | 17.3–17.4 | 17.5–17.6 | 17.5–17.6 | 10.3 |
| `scalar/horner/mul_2_2+add_2_2/full` | 12.6–14.1 | 12.6 | 12.9 | 12.9 | 18.6 | 18.5–18.6 | 18.3–18.4 | 18.3–18.4 | 11.3 |
| `scalar/horner/mul_2_2+add_2_2/full_sel` | 16.7–18.7 | 16.7 | 13.1 | 13.3 | 18.3–18.4 | 18.3–18.4 | 19–19.2 | 19.1 | 17.4 |
| `scalar/horner/ball_mul_2+ball_add_2/kairn` | 12.9–14.2 | 12.9 | 12.8–12.9 | 12.8 | 18.3–18.4 | 18.3–18.4 | 18.6–18.7 | 18.6 | 11.4 |
| `scalar/horner/ball_mul_2+ball_add_2/plain` | 12.9–14.4 | 12.9 | 12.8–12.9 | 12.8 | 17.9 | 17.9–18 | 17.7–17.8 | 17.7 | 10.7 |
| `scalar/horner/ball_mul_2+ball_add_2/full` | 12.7–14 | 12.7 | 13 | 12.9 | 18.7 | 18.6–18.7 | 18.8 | 18.8 | 11.9 |
| `scalar/horner/ball_mul_2+ball_add_2/full_sel` | 24–26.7 | 24 | 14 | 14 | 24.8–24.9 | 22–22.1 | 19.2–19.3 | 19.2–19.3 | 24.9 |
| `scalar/horner/ball_mul_1+ball_add_1/kairn` | 7.07–7.91 | 7.07–7.08 | 7.08 | 7.06 | 11.2–11.3 | 11.2–11.3 | 11.2–11.3 | 11.2–11.3 | 9.8–9.82 |
| `scalar/horner/ball_mul_1+ball_add_1/full` | 7.47–8.36 | 7.47 | 7.38 | 7.37–7.38 | 11.9–12 | 11.9 | 11.5–11.6 | 11.5–11.6 | 9.76–9.77 |
| `scalar/horner/mul_1_1+add_1_1/kairn` | 1.23–1.36 | 1.22–1.23 | 1.22 | 1.22 | 2.26–2.27 | 2.25–2.27 | 2.26–2.27 | 2.25–2.26 | 1.23 |
| `scalar/horner/mul_1_1+add_1_1/double` | 1.22–1.37 | 1.22–1.23 | 1.22–1.23 | 1.22 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.23 |
| `packed/tp/two_prod/kairn` | 0.178–0.187 | 0.178 | 0.173–0.174 | 0.178 | 0.237–0.239 | 0.238–0.239 | 0.169–0.17 | 0.167–0.168 | 0.114–0.121 |
| `packed/tp/two_prod/plain` | 0.18–0.182 | 0.179–0.182 | 0.174 | 0.182 | 0.179–0.181 | 0.18 | 0.162–0.164 | 0.161 | 0.114–0.131 |
| `packed/tp/mul_2_1/kairn` | 0.259 | 0.26 | 0.26 | 0.26 | 0.284–0.289 | 0.277–0.279 | 0.275–0.278 | 0.276–0.277 | 0.173 |
| `packed/tp/mul_2_1/plain` | 0.259–0.27 | 0.26 | 0.257–0.258 | 0.258 | 0.257–0.259 | 0.258–0.259 | 0.257–0.258 | 0.256–0.257 | 0.189 |
| `packed/tp/mul_2_1/full` | 0.61–0.622 | 0.61–0.611 | 0.491 | 0.49 | 0.641–0.645 | 0.641–0.643 | 0.564–0.567 | 0.564–0.565 | 0.403–0.404 |
| `packed/tp/mul_2_2/kairn` | 0.36–0.372 | 0.36 | 0.351 | 0.351 | 0.378–0.38 | 0.378–0.38 | 0.382–0.385 | 0.381–0.384 | 0.229 |
| `packed/tp/mul_2_2/plain` | 0.354–0.369 | 0.353–0.355 | 0.349 | 0.349 | 0.347–0.348 | 0.347–0.349 | 0.356–0.36 | 0.361–0.362 | 0.189 |
| `packed/tp/mul_2_2/full` | 0.712–0.73 | 0.712 | 0.595–0.596 | 0.598 | 0.747–0.751 | 0.746–0.75 | 0.666–0.668 | 0.665–0.668 | 0.47 |
| `packed/tp/add_2_2/kairn` | 0.696–0.726 | 0.696–0.697 | 0.702–0.703 | 0.703 | 0.944–0.954 | 0.947–0.953 | 0.949–0.955 | 0.95–0.952 | 0.548–0.549 |
| `packed/tp/add_2_2/full` | 1.07–1.12 | 1.07 | 0.931–0.948 | 0.937–0.949 | 1.15 | 1.15 | 1.11 | 1.11 | 0.695–0.696 |
| `packed/tp/add_2_1/kairn` | 0.385–0.402 | 0.385 | 0.381–0.382 | 0.382 | 0.589–0.593 | 0.589–0.592 | 0.584–0.587 | 0.585–0.587 | 0.274–0.276 |
| `packed/tp/add_2_1/full` | 0.747–0.778 | 0.746 | 0.623–0.624 | 0.624 | 0.853–0.86 | 0.852–0.858 | 0.776–0.779 | 0.777–0.779 | 0.472 |
| `packed/tp/add_fast_2_2/kairn` | 0.384–0.392 | 0.383–0.385 | 0.382–0.383 | 0.383 | 0.543–0.547 | 0.543–0.547 | 0.546–0.549 | 0.546–0.548 | 0.31 |
| `packed/tp/add_fast_2_2/full` | 0.745–0.759 | 0.745 | 0.625–0.628 | 0.627–0.628 | 0.754–0.759 | 0.753–0.758 | 0.679–0.682 | 0.68–0.682 | 0.499–0.501 |
| `packed/tp/neg_2/kairn` | 0.178–0.186 | 0.179 | 0.17–0.171 | 0.18–0.181 | 0.164–0.165 | 0.164–0.165 | 0.16–0.161 | 0.16 | 0.121–0.135 |
| `packed/tp/ball_add_2/kairn` | 0.848–0.884 | 0.847–0.849 | 0.826–0.842 | 0.842–0.848 | 1.13 | 1.13–1.14 | 1.16–1.17 | 1.17 | 0.594–0.595 |
| `packed/tp/ball_add_2/full` | 1.42–1.48 | 1.41 | 1.29 | 1.27–1.29 | 1.81–1.82 | 1.81 | 1.71–1.72 | 1.71–1.72 | 1.06 |
| `packed/tp/ball_mul_2/kairn` | 0.634–0.658 | 0.633–0.634 | 0.628 | 0.628 | 0.695–0.697 | 0.693–0.698 | 0.698–0.702 | 0.7–0.704 | 0.338 |
| `packed/tp/ball_mul_2/plain` | 0.62 | 0.62 | 0.62 | 0.618–0.62 | 0.667–0.67 | 0.666–0.67 | 0.69–0.694 | 0.69–0.692 | 0.335–0.336 |
| `packed/tp/ball_mul_2/full` | 1.14–1.19 | 1.14–1.15 | 1.02 | 1.02–1.03 | 1.34–1.35 | 1.34–1.35 | 1.29 | 1.28–1.29 | 0.885–0.886 |
| `packed/tp/ball_scale_2/kairn` | 0.433–0.452 | 0.433–0.434 | 0.43 | 0.43–0.431 | 0.507–0.509 | 0.508–0.51 | 0.514–0.516 | 0.514–0.515 | 0.25 |
| `packed/tp/ball_scale_2/full` | 0.929–0.947 | 0.929–0.93 | 0.802–0.803 | 0.8–0.803 | 1.15–1.16 | 1.15–1.16 | 1.07–1.08 | 1.07–1.08 | 0.762–0.763 |
| `packed/tp/ball_neg_2/kairn` | 0.278–0.29 | 0.279 | 0.273 | 0.387 | 0.244–0.245 | 0.255–0.257 | 0.25–0.251 | 0.25–0.251 | 0.168 |
| `packed/tp/ball_add_1/kairn` | 0.231–0.241 | 0.231 | 0.232 | 0.238–0.241 | 0.223–0.224 | 0.223–0.224 | 0.236–0.238 | 0.236–0.237 | 0.174 |
| `packed/tp/ball_add_1/full` | 0.578–0.603 | 0.564 | 0.473 | 0.472–0.473 | 0.582–0.585 | 0.582–0.584 | 0.489–0.492 | 0.49–0.491 | 0.454 |
| `packed/tp/ball_mul_1/kairn` | 0.324–0.332 | 0.324–0.325 | 0.317–0.318 | 0.317–0.318 | 0.39–0.391 | 0.39–0.391 | 0.369–0.371 | 0.371–0.372 | 0.204 |
| `packed/tp/ball_mul_1/full` | 0.725–0.757 | 0.725 | 0.619 | 0.618–0.619 | 0.853–0.857 | 0.853–0.855 | 0.746–0.75 | 0.747–0.748 | 0.554–0.555 |
| `packed/tp/ball_scale_1/kairn` | 0.286–0.299 | 0.286 | 0.286 | 0.284–0.286 | 0.267–0.269 | 0.252–0.253 | 0.25–0.252 | 0.256 | 0.174 |
| `packed/tp/ball_scale_1/full` | 0.594–0.62 | 0.578–0.594 | 0.484–0.485 | 0.484–0.485 | 0.649–0.652 | 0.647–0.652 | 0.559–0.562 | 0.559–0.561 | 0.458 |
| `packed/tp/ball_neg_1/kairn` | 0.23–0.239 | 0.23 | 0.226–0.227 | 0.227 | 0.178–0.179 | 0.178–0.179 | 0.169–0.17 | 0.169–0.17 | 0.113 |
| `packed/tp/add_1_1/kairn` | 0.155–0.16 | 0.155 | 0.154 | 0.154 | 0.101–0.102 | 0.101–0.102 | 0.121–0.123 | 0.121–0.122 | 0.0833–0.084 |
| `packed/tp/mul_1_1/kairn` | 0.154–0.158 | 0.155–0.156 | 0.154 | 0.154 | 0.0986–0.0993 | 0.0986–0.0989 | 0.121–0.123 | 0.121 | 0.0886–0.0972 |
| `packed/tp/mul_1_1/double` | 0.155–0.158 | 0.155 | 0.154 | 0.154 | 0.101–0.102 | 0.13–0.131 | 0.122–0.123 | 0.121–0.122 | 0.0945–0.111 |
| `packed/tp/neg_1/kairn` | 0.155–0.158 | 0.154–0.155 | 0.154 | 0.154 | 0.0947–0.0953 | 0.163 | 0.0861–0.0865 | 0.0857–0.0863 | 0.0861–0.104 |
| `packed/sum/add_2_2/kairn` | 7.36–7.67 | 7.12–7.37 | 7.07–7.43 | 6.92–7.42 | 9.91–9.95 | 9.89–9.94 | 9.83–9.89 | 9.84–9.88 | 4.76 |
| `packed/sum/add_2_2/full` | 9.2–9.59 | 8.59–9.21 | 8.88–9.52 | 8.88–9.52 | 11.6 | 11.6 | 10.9 | 10.9 | 7.29–7.3 |
| `packed/sum/add_2_1/kairn` | 4.46–4.65 | 4.17–4.46 | 4.14–4.44 | 4.13–4.36 | 6.33–6.35 | 6.33–6.34 | 6.32–6.37 | 6.32–6.35 | 2.84 |
| `packed/sum/add_2_1/full` | 6.38–6.65 | 5.95–6.39 | 6–6.45 | 6.22–6.24 | 8.03–8.06 | 8–8.05 | 7.22–7.27 | 7.23–7.24 | 5.5–5.52 |
| `packed/sum/ball_add_2/kairn` | 7.47–7.75 | 7–7.52 | 7–7.51 | 7–7.05 | 10.1 | 10.1 | 10–10.1 | 10.1 | 4.79–4.81 |
| `packed/sum/ball_add_2/full` | 12–13.4 | 11.9–12.8 | 11.4–12.2 | 11.4–11.7 | 15.5–15.6 | 15.5–15.6 | 14.5–14.6 | 14.5–14.6 | 10.2 |
| `packed/sum/ball_add_1/kairn` | 1.67–1.81 | 1.65–1.77 | 1.69–1.82 | 1.69–1.7 | 3.27–3.28 | 3.27–3.28 | 3.26–3.28 | 3.26–3.27 | 1.38–1.39 |
| `packed/sum/ball_add_1/full` | 5.34–5.92 | 5.33–5.73 | 4.72–4.73 | 4.72 | 6.61–6.63 | 6.61–6.64 | 5.42–5.45 | 5.43–5.45 | 5.67–5.68 |
| `packed/sum/add_1_1/kairn` | 0.426–0.454 | 0.407–0.436 | 0.4–0.413 | 0.4–0.418 | 0.622–0.628 | 0.619–0.626 | 0.483–0.486 | 0.483–0.485 | 0.259–0.261 |
| `packed/prod/mul_2_2/kairn` | 5.28–5.35 | 4.98–5.32 | 4.95–5.13 | 4.95–5.25 | 7.69–7.72 | 7.68–7.71 | 7.72–7.77 | 7.73–7.75 | 4.19 |
| `packed/prod/mul_2_2/plain` | 4.97–5.5 | 4.96–5.15 | 4.97–4.98 | 4.97 | 7.11–7.14 | 7.11–7.14 | 7.12–7.16 | 7.12–7.14 | 4.18 |
| `packed/prod/mul_2_2/full` | 6.51–7.29 | 6.51–6.75 | 5.94–5.95 | 5.95 | 8.3–8.32 | 8.29–8.32 | 8.17–8.22 | 8.19–8.2 | 6.41–6.42 |
| `packed/prod/mul_2_1/kairn` | 3.49–3.9 | 3.49–3.57 | 3.49–3.5 | 3.49 | 5.02–5.03 | 5.01–5.03 | 5–5.02 | 5–5.01 | 2.78–2.79 |
| `packed/prod/mul_2_1/full` | 5.34–5.97 | 5.33–5.34 | 5.71 | 5.71–5.72 | 7.28–7.31 | 7.28–7.32 | 6.32–6.36 | 6.33–6.34 | 5.73–5.74 |
| `packed/prod/ball_mul_2/kairn` | 5.34–5.95 | 5.33–5.5 | 5.34–5.61 | 5.34–5.53 | 8.01–8.05 | 8.01–8.05 | 7.98–8.01 | 7.98–8 | 4.67–4.71 |
| `packed/prod/ball_mul_2/plain` | 5.44–5.95 | 5.33–5.71 | 5.34–5.74 | 5.35–5.54 | 7.41–7.43 | 7.4–7.42 | 7.43–7.46 | 7.43–7.44 | 4.63–4.66 |
| `packed/prod/ball_mul_2/full` | 9.38–10.2 | 9.09–9.75 | 8.53–9.15 | 8.53–8.7 | 12.1 | 12–12.1 | 11.1 | 11.1 | 9.31 |
| `packed/prod/ball_scale_2/kairn` | 3.8–4.25 | 3.79–4.07 | 3.8–4.08 | 3.8–3.81 | 5.35–5.36 | 5.35–5.37 | 5.32–5.34 | 5.33–5.34 | 3.31 |
| `packed/prod/ball_scale_2/full` | 8.77–9.81 | 8.77–9.38 | 8.18–8.31 | 8.18–8.19 | 11.3–11.4 | 11.3–11.4 | 10.1 | 10.1 | 8.37 |
| `packed/prod/ball_mul_1/kairn` | 3.76–4.21 | 3.76–3.81 | 3.74–3.75 | 3.74–3.75 | 6.77–6.8 | 6.77–6.8 | 6.74–6.76 | 6.74–6.76 | 3.09 |
| `packed/prod/ball_mul_1/full` | 7.08–7.92 | 7.08–7.11 | 6.47–6.49 | 6.48–6.49 | 9.54–9.6 | 9.53–9.57 | 8.68–8.72 | 8.69–8.72 | 7.54 |
| `packed/prod/ball_scale_1/kairn` | 1.96–2.19 | 1.96–1.97 | 1.95 | 1.95 | 3.77–3.79 | 3.77–3.79 | 3.77–3.79 | 3.77–3.78 | 1.53 |
| `packed/prod/ball_scale_1/full` | 5.57–6.23 | 5.56–5.62 | 4.96 | 4.95–4.96 | 6.97–7.01 | 6.98–7.01 | 5.94–5.97 | 5.96–5.97 | 5.64–5.65 |
| `packed/prod/mul_1_1/kairn` | 0.587–0.649 | 0.586–0.616 | 0.58–0.581 | 0.581–0.583 | 1.04 | 1.04–1.05 | 0.772–0.775 | 0.772–0.774 | 0.435–0.438 |
| `packed/prod/mul_1_1/double` | 0.586–0.628 | 0.585–0.625 | 0.581–0.583 | 0.58–0.583 | 0.622–0.625 | 0.622–0.625 | 0.473–0.476 | 0.474–0.475 | 0.437–0.439 |
| `packed/horner/mul_2_2+add_2_2/kairn` | 12.5–13.7 | 12.4–12.6 | 12.2–12.3 | 12.3 | 18.2–18.3 | 18.2–18.3 | 17.9–18 | 18 | 9.69 |
| `packed/horner/mul_2_2+add_2_2/plain` | 12.4–13.8 | 12.4–12.5 | 12.3 | 12.3 | 17.4–17.5 | 17.4–17.5 | 17.4–17.5 | 17.4–17.5 | 9.62–9.63 |
| `packed/horner/mul_2_2+add_2_2/full` | 15.4–17.3 | 15.4 | 14.8 | 14.8 | 20.1 | 20–20.1 | 19.4–19.5 | 19.4–19.5 | 14.2 |
| `packed/horner/ball_mul_2+ball_add_2/kairn` | 12.8–14.2 | 12.8–12.9 | 12.8 | 12.8 | 18.3–18.4 | 18.3–18.4 | 18.4–18.6 | 18.4–18.6 | 9.63 |
| `packed/horner/ball_mul_2+ball_add_2/plain` | 12.8–14.2 | 12.8 | 12.7 | 12.7 | 17.6 | 17.6 | 17.6–17.7 | 17.6–17.8 | 9.6–9.61 |
| `packed/horner/ball_mul_2+ball_add_2/full` | 21.4–24 | 21.4–21.5 | 20.2–20.3 | 20.2–20.3 | 28–28.1 | 27.9–28.1 | 25.9–26.1 | 25.9–26.2 | 19.7 |
| `packed/horner/ball_mul_1+ball_add_1/kairn` | 6.52–7.29 | 6.52–6.53 | 6.49–6.5 | 6.49–6.51 | 10.7 | 10.7 | 10.7–10.8 | 10.7–10.8 | 5.76 |
| `packed/horner/ball_mul_1+ball_add_1/full` | 12.8–14.3 | 12.8 | 11.7 | 11.7 | 16.3 | 16.2–16.3 | 14.3–14.4 | 14.3–14.4 | 13.2 |
| `api/tp/add_2_2/kairn` | 0.892–0.938 | 0.887–0.898 | 1.31–1.36 | 1.3–1.34 | 3.75–3.77 | 1.97–1.99 | 2.29 | 2.29 | 2.18 |
| `api/tp/add_2_2/op` | 1.51–1.54 | 1.51 | 1.57–1.59 | 1.56–1.58 | 4.41–4.44 | 4.42–4.44 | 2.7–2.72 | 2.71–2.72 | 2.35 |
| `api/tp/add_2_2/finite` | 0.899–0.936 | 0.899–0.9 | 1.33–1.37 | 1.34–1.37 | 3.75–3.78 | 1.97–1.99 | 2.28–2.29 | 2.29–2.3 | 2.18 |
| `api/tp/add_2_2/textbook` | 0.897–0.926 | 0.897–0.899 | 1.34–1.37 | 1.31–1.37 | 3.7–3.72 | 1.96–1.98 | 2.29–2.31 | 2.29–2.3 | 2.21–2.23 |
| `api/tp/add_fast_2_2/kairn` | 0.581–0.606 | 0.581–0.582 | 0.68 | 0.559–0.58 | 2.2 | 1.16 | 1.4 | 1.4 | 1.2 |
| `api/tp/add_fast_2_2/op` | 0.89–0.909 | 0.89 | 0.972–0.973 | 0.964–0.965 | 2.7–2.72 | 2.7–2.72 | 1.84–1.85 | 1.84–1.85 | 1.35–1.36 |
| `api/tp/add_fast_2_2/finite` | 0.581–0.582 | 0.581–0.582 | 0.654–0.68 | 0.579–0.58 | 2.2–2.21 | 1.16 | 1.4 | 1.39–1.4 | 1.2 |
| `api/tp/add_fast_2_2/textbook` | 0.581–0.582 | 0.581–0.582 | 0.68–0.681 | 0.577–0.58 | 2.2 | 1.19–1.2 | 1.4 | 1.4 | 1.2 |
| `api/tp/add_2_1/kairn` | 0.514–0.52 | 0.514 | 0.509–0.515 | 0.514 | 2.36–2.37 | 1.12–1.13 | 2.34–2.35 | 2.34 | 1.21 |
| `api/tp/add_2_1/op` | 0.89–0.92 | 0.89–0.891 | 0.951–0.958 | 0.957–0.958 | 2.91–2.92 | 2.92–2.93 | 2.73–2.75 | 2.73–2.74 | 1.39 |
| `api/tp/add_2_1/finite` | 0.514–0.52 | 0.514 | 0.515 | 0.504–0.515 | 2.35–2.37 | 1.12–1.13 | 2.33–2.35 | 2.34–2.35 | 1.22 |
| `api/tp/add_2_1/textbook` | 0.481 | 0.481 | 0.548 | 0.548 | 2.06–2.07 | 1.06–1.07 | 2.04–2.05 | 2.05 | 1.09 |
| `api/tp/mul_2_2/kairn` | 0.552–0.557 | 0.552–0.553 | 0.548 | 0.548 | 1.79 | 1.15–1.16 | 1.27–1.28 | 1.28 | 1.01 |
| `api/tp/mul_2_2/op` | 0.769–0.78 | 0.769–0.772 | 0.847–0.85 | 0.846–0.849 | 2.29–2.31 | 2.3–2.31 | 1.96–1.97 | 1.97 | 1.26–1.27 |
| `api/tp/mul_2_2/finite` | 0.552–0.568 | 0.552–0.553 | 0.548 | 0.548 | 1.8–1.81 | 1.17–1.18 | 1.27–1.28 | 1.28–1.29 | 0.946–0.954 |
| `api/tp/mul_2_2/textbook` | 0.549–0.563 | 0.549 | 0.548 | 0.548 | 1.42–1.43 | 1.07 | 1.22–1.23 | 1.23 | 1.04 |
| `api/tp/mul_2_1/kairn` | 0.417–0.422 | 0.417 | 0.415–0.416 | 0.415 | 1.23 | 0.804–0.807 | 1.11 | 1.11 | 0.694–0.697 |
| `api/tp/mul_2_1/op` | 0.595–0.607 | 0.596 | 0.631–0.633 | 0.631–0.633 | 1.84–1.85 | 1.84–1.85 | 1.64–1.65 | 1.64–1.65 | 1.06 |
| `api/tp/mul_2_1/finite` | 0.416–0.435 | 0.417–0.418 | 0.415–0.416 | 0.415–0.416 | 1.23 | 0.804–0.81 | 1.1–1.11 | 1.11 | 0.695–0.697 |
| `api/tp/mul_2_1/textbook` | 0.417–0.425 | 0.416–0.417 | 0.435 | 0.411–0.415 | 1.04 | 0.778–0.781 | 1.03–1.04 | 1.03–1.04 | 0.744–0.745 |
| `api/tp/neg_2/kairn` | 0.302–0.31 | 0.302 | 0.295 | 0.551–0.557 | 0.48–0.483 | 0.342–0.343 | 0.334–0.336 | 0.342–0.344 | 0.348–0.352 |
| `api/tp/neg_2/op` | 0.298–0.315 | 0.302 | 0.295 | 0.289–0.295 | 0.48–0.482 | 0.342–0.344 | 0.334–0.336 | 0.335–0.336 | 0.348–0.353 |
| `api/tp/ball_add_2/kairn` | 1.14–1.18 | 1.14–1.15 | 1.15 | 1.21 | 4.86–4.87 | 2.55–2.57 | 3.02–3.03 | 3.04 | 2.42 |
| `api/tp/ball_add_2/op` | 1.95–1.99 | 1.95 | 2.02 | 2.03–2.04 | 5.99–6.01 | 4.1–4.12 | 3.03–3.05 | 3.03–3.04 | 3.07–3.08 |
| `api/tp/ball_mul_2/kairn` | 0.931–0.972 | 0.931–0.933 | 0.931–0.933 | 0.946 | 3.25–3.27 | 2.29–2.3 | 2.03–2.04 | 2.03–2.04 | 2.31–2.32 |
| `api/tp/ball_mul_2/op` | 1.5–1.57 | 1.5 | 1.53 | 1.53 | 4.21–4.24 | 3.75–3.77 | 2.42–2.45 | 2.43–2.44 | 3.26–3.27 |
| `api/tp/ball_scale_2/kairn` | 0.63–0.631 | 0.63–0.631 | 0.622 | 0.622–0.623 | 2.34–2.35 | 2.13–2.18 | 2.05–2.06 | 2.06–2.07 | 1.52 |
| `api/tp/ball_scale_2/op` | 0.998–1.01 | 0.998–0.999 | 1.08 | 1.08 | 3.43–3.46 | 2.61–2.62 | 2.93–2.95 | 2.93–2.94 | 2.5 |
| `api/tp/ball_neg_2/kairn` | 0.388–0.42 | 0.508 | 0.416–0.425 | 0.416–0.421 | 0.682–0.687 | 1.13 | 0.684–0.688 | 0.686–0.688 | 0.376–0.377 |
| `api/tp/ball_neg_2/op` | 0.386–0.421 | 0.504–0.508 | 0.416–0.423 | 0.415–0.423 | 0.679–0.682 | 1.13 | 0.686–0.69 | 0.686–0.689 | 0.379–0.391 |
| `api/tp/ball_add_1/kairn` | 0.55–0.574 | 0.55 | 0.46–0.461 | 0.521–0.549 | 1.08–1.09 | 0.811–0.815 | 0.789–0.794 | 0.794–0.798 | 0.617 |
| `api/tp/ball_add_1/op` | 0.771–0.805 | 0.771–0.772 | 0.715–0.716 | 0.699–0.715 | 2.05–2.06 | 1.38–1.39 | 1.45–1.46 | 1.45–1.46 | 1.6 |
| `api/tp/ball_mul_1/kairn` | 0.55–0.566 | 0.55 | 0.694–0.695 | 0.549 | 1.64–1.65 | 0.938–0.942 | 1.2 | 1.19–1.2 | 1.38 |
| `api/tp/ball_mul_1/op` | 0.981–1.02 | 0.981 | 0.947 | 0.883–0.884 | 2.56–2.57 | 1.77–1.78 | 1.64–1.65 | 1.64 | 2.27 |
| `api/tp/ball_scale_1/kairn` | 0.418–0.421 | 0.418–0.419 | 0.487 | 0.416 | 1.23–1.24 | 0.679–0.684 | 0.995–1.01 | 0.996–1 | 0.823 |
| `api/tp/ball_scale_1/op` | 0.745–0.759 | 0.745 | 0.684–0.685 | 0.685 | 2.09–2.1 | 1.16–1.17 | 1.59–1.6 | 1.6 | 1.8 |
| `api/tp/ball_neg_1/kairn` | 0.28–0.287 | 0.28–0.281 | 0.297 | 0.595–0.609 | 0.474–0.477 | 0.601–0.603 | 0.484–0.487 | 0.345–0.346 | 0.228–0.229 |
| `api/tp/ball_neg_1/op` | 0.281 | 0.28–0.281 | 0.297 | 0.57–0.609 | 0.627–0.63 | 0.6–0.603 | 0.345–0.346 | 0.483–0.485 | 0.225–0.227 |
| `api/tp/add_1_1/kairn` | 0.157 | 0.157 | 0.296 | 0.157–0.158 | 0.629–0.632 | 0.185–0.186 | 0.185–0.186 | 0.185–0.186 | 0.0924–0.144 |
| `api/tp/add_1_1/limb` | 0.157–0.161 | 0.157 | 0.296 | 0.154–0.155 | 0.629–0.632 | 0.185–0.186 | 0.187–0.19 | 0.186 | 0.0864–0.143 |
| `api/tp/mul_1_1/kairn` | 0.157–0.163 | 0.153–0.157 | 0.295 | 0.157 | 0.628–0.631 | 0.185–0.187 | 0.19–0.191 | 0.189–0.194 | 0.0991–0.145 |
| `api/tp/mul_1_1/limb` | 0.157–0.162 | 0.157 | 0.296 | 0.157 | 0.628–0.631 | 0.185–0.186 | 0.185–0.186 | 0.187–0.189 | 0.1–0.145 |
| `api/tp/neg_1/kairn` | 0.157–0.16 | 0.157 | 0.29–0.296 | 0.149–0.156 | 0.627–0.629 | 0.174 | 0.173–0.175 | 0.174 | 0.0998–0.118 |
| `api/sum/add_2_2/kairn` | 7.58–7.67 | 7.45–7.57 | 7.29–7.64 | 7.24–7.63 | 10.2 | 10.2 | 9.88–9.95 | 9.92–9.97 | 4.99 |
| `api/sum/add_2_2/op` | 7.42–7.86 | 7.04–7.55 | 7.12–7.64 | 7.16–7.67 | 10.3–10.4 | 10.3–10.4 | 10–10.1 | 10.1 | 5.08 |
| `api/sum/add_2_2/finite` | 7.11–7.67 | 7.06–7.28 | 7.11–7.64 | 7.12–7.2 | 10.2 | 10.2 | 9.91–9.94 | 9.9–9.91 | 4.99 |
| `api/sum/add_2_2/textbook` | 7.07–7.7 | 7.07–7.2 | 7.17–7.28 | 7.16–7.31 | 10.2 | 10.2 | 9.86–9.91 | 9.86–9.9 | 4.96 |
| `api/sum/add_fast_2_2/kairn` | 4.44–4.76 | 4.44–4.54 | 4.44 | 4.44 | 6.54–6.56 | 6.54 | 6.32–6.36 | 6.33–6.34 | 3.18 |
| `api/sum/add_fast_2_2/op` | 4.42–4.92 | 4.41–4.43 | 4.49–4.5 | 4.49 | 6.51–6.53 | 6.48–6.53 | 6.4–6.44 | 6.42–6.43 | 3.35 |
| `api/sum/add_fast_2_2/finite` | 4.44–4.97 | 4.44–4.45 | 4.44 | 4.44 | 6.54–6.55 | 6.52–6.56 | 6.32–6.36 | 6.32–6.35 | 3.18–3.19 |
| `api/sum/add_fast_2_2/textbook` | 4.35–4.87 | 4.35–4.38 | 4.47 | 4.47–4.48 | 6.54–6.56 | 6.53–6.56 | 6.32–6.35 | 6.33–6.34 | 3.18 |
| `api/sum/add_2_1/kairn` | 4.45–4.98 | 4.46–4.47 | 4.43 | 4.43 | 6.52–6.57 | 6.43–6.56 | 6.52–6.55 | 6.52–6.55 | 3.16 |
| `api/sum/add_2_1/op` | 4.39–4.91 | 4.39 | 4.47 | 4.47–4.48 | 6.56–6.57 | 6.55–6.59 | 6.52–6.56 | 6.51–6.54 | 3.28 |
| `api/sum/add_2_1/finite` | 4.45–4.98 | 4.45–4.46 | 4.43–4.44 | 4.43 | 6.53–6.56 | 6.54–6.55 | 6.53–6.56 | 6.53–6.55 | 3.16 |
| `api/sum/add_2_1/textbook` | 4.36–4.68 | 4.36–4.37 | 4.35–4.36 | 4.35–4.36 | 6.26 | 6.24–6.27 | 6.24–6.27 | 6.25–6.26 | 3.14–3.15 |
| `api/sum/ball_add_2/kairn` | 7.17–7.69 | 7.17–7.19 | 7.22–7.23 | 7.17–7.18 | 10.3 | 10.2–10.3 | 10.2 | 10.2 | 5.19 |
| `api/sum/ball_add_2/op` | 7.3–8.12 | 7.3 | 7.09 | 7.15–7.16 | 10.4–10.5 | 10.4–10.5 | 10.2–10.3 | 10.2–10.3 | 5.23–5.24 |
| `api/sum/ball_add_1/kairn` | 2.17–2.42 | 2.17 | 2.23 | 2.22 | 3.75–3.77 | 3.76–3.77 | 3.74–3.77 | 3.75 | 2.69 |
| `api/sum/ball_add_1/op` | 2.6–2.9 | 2.6–2.63 | 2.56 | 2.56 | 3.85–3.87 | 3.85–3.86 | 3.85–3.88 | 3.85–3.86 | 3.35–3.36 |
| `api/sum/add_1_1/kairn` | 0.366–0.409 | 0.365–0.368 | 0.466–0.467 | 0.466–0.468 | 0.791–0.794 | 0.792–0.795 | 0.792–0.796 | 0.792–0.793 | 0.285 |
| `api/sum/add_1_1/limb` | 0.365–0.391 | 0.365–0.369 | 0.459–0.475 | 0.466–0.468 | 0.787–0.79 | 0.791–0.794 | 0.791–0.795 | 0.792–0.794 | 0.285 |
| `api/prod/mul_2_2/kairn` | 5.31–5.71 | 5.3–5.42 | 5.25–5.33 | 5.25–5.26 | 8.01–8.04 | 8–8.04 | 8.05–8.11 | 8.07–8.1 | 6.03 |
| `api/prod/mul_2_2/op` | 5.27–5.77 | 5.27–5.28 | 5.41–5.42 | 5.41–5.42 | 8.32–8.36 | 8.31–8.34 | 8.07–8.12 | 8.08–8.1 | 5.77 |
| `api/prod/mul_2_2/finite` | 5.31–5.8 | 5.31–5.33 | 5.25–5.26 | 5.25–5.26 | 8–8.04 | 8–8.04 | 8.07–8.12 | 8.06–8.1 | 5.99 |
| `api/prod/mul_2_2/textbook` | 5.3–5.69 | 5.3–5.31 | 5.25 | 5.25 | 7.41–7.44 | 7.4–7.43 | 7.41–7.45 | 7.41–7.43 | 5.23 |
| `api/prod/mul_2_1/kairn` | 3.34–3.66 | 3.34 | 3.33 | 3.33 | 5.3–5.32 | 5.29–5.32 | 5.31–5.33 | 5.31–5.32 | 5.09 |
| `api/prod/mul_2_1/op` | 3.42–3.83 | 3.42 | 3.45 | 3.45 | 5.37–5.39 | 5.37–5.4 | 5.49–5.52 | 5.5–5.51 | 4.79 |
| `api/prod/mul_2_1/finite` | 3.34–3.58 | 3.34 | 3.33–3.34 | 3.33–3.34 | 5.3–5.32 | 5.3–5.32 | 5.3–5.33 | 5.31–5.32 | 5.09 |
| `api/prod/mul_2_1/textbook` | 3.34–3.61 | 3.34 | 3.33–3.34 | 3.33 | 4.72–4.73 | 4.71–4.73 | 4.71–4.73 | 4.71–4.72 | 4.24–4.25 |
| `api/prod/ball_mul_2/kairn` | 5.53–6.19 | 5.53–5.54 | 5.51–5.53 | 5.51–5.52 | 8.07–8.1 | 8.07–8.1 | 8.12–8.16 | 8.13–8.15 | 6.82 |
| `api/prod/ball_mul_2/op` | 5.57–6.13 | 5.57–5.6 | 5.51 | 5.57–5.58 | 8.11–8.14 | 8.11–8.13 | 8.27–8.29 | 8.26–8.29 | 6.6 |
| `api/prod/ball_scale_2/kairn` | 3.51–3.92 | 3.51 | 3.52–3.53 | 3.5–3.51 | 5.47–5.49 | 5.46–5.5 | 5.47–5.51 | 5.48–5.5 | 5.41 |
| `api/prod/ball_scale_2/op` | 3.61–4.03 | 3.61–3.65 | 3.64–3.65 | 3.65–3.66 | 5.72–5.74 | 5.71–5.74 | 5.53–5.57 | 5.54–5.56 | 4.81–4.82 |
| `api/prod/ball_mul_1/kairn` | 4.34–4.77 | 4.34–4.35 | 4.41–4.44 | 4.41–4.43 | 7.34–7.36 | 7.33–7.36 | 7.32–7.35 | 7.31–7.34 | 6.41 |
| `api/prod/ball_mul_1/op` | 4.69–5.24 | 4.68–4.7 | 5.12–5.13 | 4.66–4.67 | 8.04–8.06 | 8.03–8.07 | 7.6–7.64 | 7.61–7.63 | 6.45–6.46 |
| `api/prod/ball_scale_1/kairn` | 2.37–2.59 | 2.36–2.37 | 2.42–2.43 | 2.42–2.43 | 4.34–4.36 | 4.34–4.36 | 4.32–4.34 | 4.32–4.34 | 4.04 |
| `api/prod/ball_scale_1/op` | 2.83–3.13 | 2.83–2.85 | 3.25 | 3.24–3.25 | 4.78–4.81 | 4.79–4.81 | 4.47–4.52 | 4.47–4.52 | 3.99 |
| `api/prod/mul_1_1/kairn` | 0.713–0.797 | 0.712–0.717 | 0.712 | 0.712–0.715 | 1.32 | 1.31–1.32 | 1.31–1.32 | 1.31–1.32 | 0.558–0.564 |
| `api/prod/mul_1_1/limb` | 0.718–0.788 | 0.718 | 0.717–0.718 | 0.717–0.718 | 0.791–0.796 | 0.791–0.794 | 0.791–0.795 | 0.791–0.794 | 0.544–0.545 |
| `api/horner/mul_2_2+add_2_2/kairn` | 12.7–13.8 | 12.7 | 12.6 | 12.6 | 18.3 | 18.2–18.3 | 18.1–18.2 | 18.1–18.2 | 11.3 |
| `api/horner/mul_2_2+add_2_2/op` | 12.6–13.6 | 12.6 | 12.9 | 12.9 | 18.5–18.6 | 18.6 | 18.3–18.4 | 18.3–18.4 | 11.3 |
| `api/horner/mul_2_2+add_2_2/finite` | 12.7–14 | 12.7 | 12.6 | 12.6 | 18.3 | 18.2–18.3 | 18.1–18.2 | 18.1–18.2 | 11.3 |
| `api/horner/mul_2_2+add_2_2/textbook` | 12.7–13.9 | 12.7 | 12.6 | 12.6 | 17.4 | 17.4 | 17.5–17.6 | 17.5–17.6 | 10.5 |
| `api/horner/mul_2_1+add_2_1/kairn` | 8.15–9.12 | 8.15 | 8.03 | 8.02–8.03 | 11.6–11.7 | 11.6–11.7 | 11.9 | 11.9 | 8.56 |
| `api/horner/mul_2_1+add_2_1/op` | 8.14–8.75 | 8.14 | 8.25–8.26 | 8.24 | 12 | 12 | 11.8–11.9 | 11.8–11.9 | 8.34–8.35 |
| `api/horner/mul_2_1+add_2_1/finite` | 8.15–8.83 | 8.15–8.16 | 8.03–8.04 | 8.02–8.03 | 11.6–11.7 | 11.6–11.7 | 11.8–11.9 | 11.9 | 8.56 |
| `api/horner/mul_2_1+add_2_1/textbook` | 8.08–8.93 | 8.08 | 7.98 | 7.98 | 11–11.1 | 11–11.1 | 11.1–11.2 | 11.2 | 7.5–7.51 |
| `api/horner/ball_mul_2+ball_add_2/kairn` | 12.9–13.8 | 12.9 | 12.8 | 12.8 | 18.2–18.4 | 18.5 | 18.6 | 18.6 | 11.7 |
| `api/horner/ball_mul_2+ball_add_2/op` | 12.7–13.8 | 12.7 | 13 | 12.9 | 18.6–18.7 | 18.6–18.8 | 18.8–18.9 | 18.8–18.9 | 12–12.1 |
| `api/horner/ball_mul_1+ball_add_1/kairn` | 7.07–7.76 | 7.07–7.08 | 7.07 | 7.07 | 11.2–11.3 | 11.2–11.3 | 11.2–11.3 | 11.2–11.3 | 9.67 |
| `api/horner/ball_mul_1+ball_add_1/op` | 7.47–8.22 | 7.46–7.47 | 7.44 | 7.46–7.47 | 12.2 | 12.2–12.3 | 11.4–11.5 | 11.4 | 10.2 |
| `api/horner/mul_1_1+add_1_1/kairn` | 1.22–1.36 | 1.22–1.23 | 1.23 | 1.22–1.23 | 2.26–2.27 | 2.25–2.27 | 2.25–2.27 | 2.25–2.26 | 1.23 |
| `api/horner/mul_1_1+add_1_1/limb` | 1.22–1.35 | 1.22 | 1.22–1.23 | 1.22–1.23 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.23 |
| `apif/tp/add_2_2/kairn` | 0.436–0.46 | 0.435–0.438 | 1.28–1.35 | 1.28–1.34 | 3.73–3.77 | 0.947–0.952 | 3.73–3.76 | 3.75–3.76 | 2.19 |
| `apif/tp/add_2_2/op` | 1.5–1.55 | 1.49–1.5 | 1.63–1.67 | 1.58–1.66 | 4.42–4.44 | 4.42–4.43 | 4.24–4.27 | 4.25–4.26 | 2.45–2.46 |
| `apif/tp/add_2_2/finite` | 0.441–0.46 | 0.441 | 1.37–1.38 | 1.31–1.38 | 3.73–3.75 | 0.944–0.948 | 3.78–3.81 | 3.78–3.8 | 2.19 |
| `apif/tp/add_2_2/textbook` | 0.443 | 0.442–0.443 | 1.3–1.37 | 1.33–1.37 | 3.74–3.76 | 1–1.01 | 3.72–3.74 | 3.72–3.73 | 2.19 |
| `apif/tp/add_fast_2_2/kairn` | 0.283–0.296 | 0.283–0.284 | 0.283 | 0.278–0.283 | 2.19–2.2 | 0.741–0.744 | 2.08–2.09 | 2.08–2.09 | 1.21 |
| `apif/tp/add_fast_2_2/op` | 0.89–0.909 | 0.884–0.892 | 1.02 | 0.986–1.02 | 2.71–2.72 | 2.71–2.72 | 2.39–2.42 | 2.4–2.41 | 1.43 |
| `apif/tp/add_fast_2_2/finite` | 0.283–0.289 | 0.283 | 0.283–0.284 | 0.283 | 2.19–2.21 | 0.719–0.723 | 2.02–2.03 | 2.02–2.03 | 1.2 |
| `apif/tp/add_fast_2_2/textbook` | 0.284–0.294 | 0.284 | 0.283 | 0.282–0.283 | 2.2–2.21 | 0.742–0.744 | 2.08–2.09 | 2.08–2.09 | 1.21 |
| `apif/tp/add_2_1/kairn` | 0.25–0.258 | 0.25 | 0.251 | 0.248–0.251 | 2.35–2.37 | 0.564–0.566 | 2.27–2.29 | 2.28 | 1.2 |
| `apif/tp/add_2_1/op` | 0.89–0.903 | 0.89 | 1.02 | 0.962–1.02 | 2.91–2.92 | 2.91–2.93 | 2.7–2.72 | 2.71–2.72 | 1.49 |
| `apif/tp/add_2_1/finite` | 0.25–0.255 | 0.25 | 0.246–0.251 | 0.251 | 2.35–2.36 | 0.564–0.565 | 2.3–2.31 | 2.3–2.31 | 1.2 |
| `apif/tp/add_2_1/textbook` | 0.234–0.241 | 0.235 | 0.265–0.268 | 0.268 | 2.08–2.1 | 0.559–0.562 | 1.98–2 | 1.98–1.99 | 1.1 |
| `apif/tp/mul_2_2/kairn` | 0.271–0.276 | 0.271–0.272 | 0.27 | 0.27 | 1.52–1.53 | 0.684–0.687 | 1.59–1.6 | 1.59–1.6 | 0.909–0.912 |
| `apif/tp/mul_2_2/op` | 0.77–0.771 | 0.768–0.769 | 0.894 | 0.877–0.894 | 2.08–2.09 | 2.09–2.1 | 2.47–2.48 | 2.48–2.49 | 1.24–1.25 |
| `apif/tp/mul_2_2/finite` | 0.271–0.274 | 0.271 | 0.27 | 0.27 | 1.51–1.53 | 0.685–0.687 | 1.85 | 1.85 | 0.97 |
| `apif/tp/mul_2_2/textbook` | 0.268 | 0.268 | 0.265–0.268 | 0.268 | 1.39 | 0.663–0.67 | 1.56–1.57 | 1.56 | 0.911–0.912 |
| `apif/tp/mul_2_1/kairn` | 0.202 | 0.202 | 0.202 | 0.202 | 1.23 | 0.419–0.42 | 1.18–1.19 | 1.18–1.19 | 0.685–0.688 |
| `apif/tp/mul_2_1/op` | 0.593–0.595 | 0.592 | 0.682–0.683 | 0.682 | 1.73–1.74 | 1.73–1.74 | 1.81–1.82 | 1.81–1.82 | 1.07–1.08 |
| `apif/tp/mul_2_1/finite` | 0.202 | 0.202 | 0.202 | 0.202 | 1.23 | 0.417–0.419 | 1.23–1.24 | 1.23–1.24 | 0.723 |
| `apif/tp/mul_2_1/textbook` | 0.202–0.206 | 0.202 | 0.202 | 0.202 | 1.04 | 0.462–0.464 | 1.15 | 1.14–1.15 | 0.687–0.689 |
| `apif/tp/neg_2/kairn` | 0.14–0.145 | 0.139–0.14 | 0.295 | 0.155 | 0.376–0.379 | 0.151–0.152 | 0.268–0.271 | 0.248–0.249 | 0.305–0.309 |
| `apif/tp/neg_2/op` | 0.14–0.144 | 0.14 | 0.295 | 0.156 | 0.377–0.379 | 0.151–0.152 | 0.247–0.249 | 0.249 | 0.305–0.309 |
| `apif/tp/ball_add_2/kairn` | 0.574–0.595 | 0.574–0.575 | 0.567–0.568 | 0.573–0.578 | 4.85–4.87 | 3.56–3.58 | 4.64–4.65 | 4.64–4.66 | 2.65 |
| `apif/tp/ball_add_2/op` | 1.95–2.03 | 1.95 | 2.06–2.07 | 1.93–2.06 | 5.85–5.87 | 4.09–4.1 | 5.45–5.47 | 5.45–5.47 | 3.09 |
| `apif/tp/ball_mul_2/kairn` | 0.467–0.479 | 0.467–0.468 | 0.461 | 0.462–0.467 | 2.88–2.89 | 3.29–3.31 | 2.86–2.88 | 2.86–2.87 | 2.06 |
| `apif/tp/ball_mul_2/op` | 1.5–1.56 | 1.5 | 1.6–1.61 | 1.6–1.61 | 3.93–3.96 | 4.03–4.06 | 3.83–3.85 | 3.84–3.85 | 2.72–2.73 |
| `apif/tp/ball_scale_2/kairn` | 0.312–0.318 | 0.311–0.312 | 0.307 | 0.307 | 2.19 | 2.27–2.3 | 2.16–2.17 | 2.16–2.17 | 1.47 |
| `apif/tp/ball_scale_2/op` | 1.01–1.03 | 1.01 | 1.12 | 1.11 | 3.31–3.33 | 2.67–2.69 | 3.01–3.03 | 3.01–3.02 | 2.31 |
| `apif/tp/ball_neg_2/kairn` | 0.251–0.256 | 0.229 | 0.224–0.225 | 0.217–0.225 | 0.662–0.664 | 0.863–0.867 | 0.642–0.651 | 0.643–0.646 | 0.34–0.342 |
| `apif/tp/ball_neg_2/op` | 0.251 | 0.224–0.229 | 0.224–0.225 | 0.224–0.225 | 0.662–0.665 | 0.863–0.867 | 0.644–0.652 | 0.641–0.644 | 0.362–0.363 |
| `apif/tp/ball_add_1/kairn` | 0.269–0.29 | 0.269 | 0.269 | 0.268 | 1.08–1.09 | 0.594–0.598 | 0.954–0.96 | 0.951–0.961 | 0.576 |
| `apif/tp/ball_add_1/op` | 0.772–0.795 | 0.77–0.772 | 0.351 | 0.352 | 1.98–2 | 0.81–0.814 | 1.53–1.54 | 1.53–1.54 | 1.58 |
| `apif/tp/ball_mul_1/kairn` | 0.269–0.273 | 0.269 | 0.269 | 0.268 | 1.56–1.57 | 0.67–0.677 | 1.58–1.6 | 1.59 | 1.31 |
| `apif/tp/ball_mul_1/op` | 0.982 | 0.981 | 0.467 | 0.467 | 2.55–2.56 | 1–1.01 | 2.36–2.37 | 2.36–2.37 | 2.01 |
| `apif/tp/ball_scale_1/kairn` | 0.203–0.205 | 0.203 | 0.203 | 0.203 | 1.23–1.24 | 0.429–0.431 | 1.11–1.12 | 1.11–1.12 | 0.898 |
| `apif/tp/ball_scale_1/op` | 0.744–0.745 | 0.743–0.744 | 0.338 | 0.338–0.339 | 2.09–2.1 | 0.698–0.702 | 1.7 | 1.7–1.71 | 1.77 |
| `apif/tp/ball_neg_1/kairn` | 0.156–0.16 | 0.148–0.156 | 0.135–0.136 | 0.592–0.609 | 0.402–0.404 | 0.344–0.346 | 0.482–0.484 | 0.481–0.483 | 0.223 |
| `apif/tp/ball_neg_1/op` | 0.155–0.158 | 0.155 | 0.135–0.136 | 0.609 | 0.629–0.632 | 0.334–0.344 | 0.482–0.485 | 0.401–0.402 | 0.222–0.223 |
| `apif/tp/add_1_1/kairn` | 0.0744–0.0758 | 0.0736–0.0745 | 0.296 | 0.0738–0.0744 | 0.629–0.632 | 0.0763–0.0766 | 0.0896–0.0901 | 0.0881–0.0883 | 0.0807–0.0808 |
| `apif/tp/add_1_1/limb` | 0.0744–0.0747 | 0.0744–0.0745 | 0.291–0.296 | 0.0727–0.0744 | 0.629–0.631 | 0.0879–0.0884 | 0.088–0.0883 | 0.0763–0.0766 | 0.0807–0.0829 |
| `apif/tp/mul_1_1/kairn` | 0.0735–0.0762 | 0.0744 | 0.283–0.296 | 0.0727–0.0744 | 0.334–0.335 | 0.0762–0.0765 | 0.0762–0.0766 | 0.0763–0.0765 | 0.0841–0.0888 |
| `apif/tp/mul_1_1/limb` | 0.0736–0.0752 | 0.0738–0.0744 | 0.296 | 0.0707–0.0745 | 0.629–0.631 | 0.0868–0.0872 | 0.0871–0.0927 | 0.0892–0.0894 | 0.0855–0.0927 |
| `apif/tp/neg_1/kairn` | 0.0736–0.0767 | 0.0735–0.0744 | 0.296 | 0.0735–0.0744 | 0.627–0.629 | 0.0762–0.0766 | 0.0891–0.0895 | 0.0763–0.0765 | 0.0866–0.0946 |
| `apif/sum/add_2_2/kairn` | 7.57–7.9 | 7.43–7.57 | 7.18–7.64 | 7.3–7.64 | 10.2 | 10.2 | 12.5–12.6 | 12.5–12.6 | 4.97 |
| `apif/sum/add_2_2/op` | 7.47–7.86 | 7.07–7.54 | 7.13–7.66 | 7.17–7.29 | 10.3–10.4 | 10.4 | 12.6 | 12.6 | 5.23 |
| `apif/sum/add_2_2/finite` | 7.07–7.89 | 7.06–7.58 | 7.11–7.35 | 7.12–7.14 | 10.1–10.2 | 10.2 | 12.7 | 12.7–12.8 | 4.96–4.97 |
| `apif/sum/add_2_2/textbook` | 7.07–7.91 | 7.07–7.24 | 7.16–7.18 | 7.16–7.17 | 10.1–10.2 | 10.2 | 12.5–12.6 | 12.5–12.6 | 4.96 |
| `apif/sum/add_fast_2_2/kairn` | 4.44–4.96 | 4.44–4.54 | 4.44 | 4.44 | 6.54–6.57 | 6.54–6.56 | 8.92–8.96 | 8.92–8.95 | 3.05–3.06 |
| `apif/sum/add_fast_2_2/op` | 4.41–4.84 | 4.41–4.45 | 4.5–4.51 | 4.5 | 6.5–6.55 | 6.51–6.54 | 8.94–8.97 | 8.94–8.96 | 3.21–3.24 |
| `apif/sum/add_fast_2_2/finite` | 4.44–4.85 | 4.44–4.45 | 4.44 | 4.44 | 6.54–6.58 | 6.54–6.57 | 8.9–8.95 | 8.9–8.93 | 3.03–3.04 |
| `apif/sum/add_fast_2_2/textbook` | 4.35–4.87 | 4.35 | 4.47–4.48 | 4.47–4.48 | 6.54–6.58 | 6.54–6.57 | 8.92–8.96 | 8.92–8.95 | 3.03 |
| `apif/sum/add_2_1/kairn` | 4.45–4.98 | 4.46 | 4.43 | 4.43–4.44 | 6.53–6.56 | 6.53–6.56 | 8.91–8.94 | 8.9–8.94 | 3.14 |
| `apif/sum/add_2_1/op` | 4.39–4.81 | 4.39 | 4.5 | 4.5 | 6.57–6.61 | 6.58–6.61 | 8.94–8.98 | 8.93–8.97 | 3.32–3.33 |
| `apif/sum/add_2_1/finite` | 4.45–4.9 | 4.45–4.47 | 4.43 | 4.43 | 6.5–6.56 | 6.53–6.56 | 8.92–8.96 | 8.91–8.94 | 3.13 |
| `apif/sum/add_2_1/textbook` | 4.36–4.82 | 4.35–4.36 | 4.35–4.36 | 4.35–4.36 | 6.24–6.28 | 6.24–6.26 | 8.91–8.94 | 8.91–8.93 | 3.14 |
| `apif/sum/ball_add_2/kairn` | 7.17–7.84 | 7.17 | 7.2 | 7.22–7.23 | 10.3–10.4 | 10.3–10.4 | 12.6 | 12.6 | 5.25 |
| `apif/sum/ball_add_2/op` | 7.31–7.83 | 7.3–7.33 | 7.21–7.23 | 7.21 | 10.5–10.6 | 10.4–10.6 | 12.5–12.6 | 12.6 | 5.19–5.2 |
| `apif/sum/ball_add_1/kairn` | 2.17–2.33 | 2.17 | 2.22–2.23 | 2.17 | 3.76 | 3.75–3.77 | 4.41–4.43 | 4.41–4.42 | 2.11 |
| `apif/sum/ball_add_1/op` | 2.6–2.79 | 2.6–2.65 | 2.57 | 2.57–2.58 | 3.85–3.87 | 3.85–3.86 | 5.31–5.35 | 5.32–5.34 | 2.63–2.64 |
| `apif/sum/add_1_1/kairn` | 0.372–0.398 | 0.37–0.376 | 0.466–0.467 | 0.466–0.467 | 0.79–0.795 | 0.79–0.795 | 0.79–0.795 | 0.792–0.794 | 0.285–0.286 |
| `apif/sum/add_1_1/limb` | 0.371–0.411 | 0.371–0.375 | 0.461–0.467 | 0.44–0.467 | 0.785–0.789 | 0.792–0.795 | 0.79–0.795 | 0.791–0.792 | 0.285 |
| `apif/prod/mul_2_2/kairn` | 5.15–5.53 | 5.15–5.16 | 5.12–5.14 | 5.12–5.14 | 8.03–8.07 | 8.01–8.05 | 9.21–9.25 | 9.21–9.24 | 4.87 |
| `apif/prod/mul_2_2/op` | 5.12–5.71 | 5.11–5.12 | 5.18 | 5.21 | 8.29–8.32 | 8.28–8.31 | 9.34–9.4 | 9.34–9.37 | 5.41 |
| `apif/prod/mul_2_2/finite` | 5.15–5.68 | 5.15–5.16 | 5.12–5.13 | 5.13 | 8.02–8.06 | 8.02–8.04 | 9.2–9.25 | 9.21–9.23 | 4.87 |
| `apif/prod/mul_2_2/textbook` | 5.23–5.83 | 5.24 | 5.2 | 5.2–5.21 | 7.41–7.44 | 7.4–7.44 | 8.62–8.65 | 8.62–8.64 | 4.87 |
| `apif/prod/mul_2_1/kairn` | 3.17–3.55 | 3.17–3.18 | 3.17 | 3.17 | 5.3–5.33 | 5.3–5.33 | 6.64–6.67 | 6.64–6.66 | 4.12 |
| `apif/prod/mul_2_1/op` | 3.23–3.53 | 3.23 | 3.28–3.29 | 3.29 | 5.37–5.39 | 5.37–5.39 | 8.07–8.11 | 8.07–8.09 | 4.27–4.28 |
| `apif/prod/mul_2_1/finite` | 3.18–3.48 | 3.18 | 3.17 | 3.17 | 5.31–5.33 | 5.3–5.32 | 6.63–6.67 | 6.63–6.66 | 4.11–4.12 |
| `apif/prod/mul_2_1/textbook` | 3.25–3.5 | 3.25–3.26 | 3.25 | 3.25 | 4.71–4.74 | 4.71–4.72 | 6.04–6.08 | 6.04–6.07 | 4.09 |
| `apif/prod/ball_mul_2/kairn` | 5.37–5.76 | 5.37 | 5.26–5.27 | 5.37 | 8.06–8.1 | 8.06–8.1 | 9.24–9.28 | 9.24–9.28 | 5.09–5.1 |
| `apif/prod/ball_mul_2/op` | 5.32–5.82 | 5.32–5.34 | 5.4 | 5.46 | 8.14–8.19 | 8.14–8.16 | 9.28–9.33 | 9.29–9.32 | 5.55–5.57 |
| `apif/prod/ball_scale_2/kairn` | 3.4–3.81 | 3.4–3.41 | 3.4 | 3.36 | 5.4–5.43 | 5.4–5.43 | 8.02–8.06 | 8.02–8.06 | 4.44 |
| `apif/prod/ball_scale_2/op` | 3.33–3.6 | 3.32–3.33 | 3.46–3.47 | 3.5 | 5.7–5.72 | 5.73–5.76 | 8.07–8.11 | 8.06–8.1 | 4.48–4.5 |
| `apif/prod/ball_mul_1/kairn` | 4.17–4.58 | 4.17–4.2 | 4.21 | 4.15 | 7.33–7.37 | 7.33–7.37 | 8.63–8.67 | 8.63–8.65 | 4.06 |
| `apif/prod/ball_mul_1/op` | 4.53–5.07 | 4.53–4.54 | 4.84–4.85 | 4.31 | 7.54–7.59 | 7.55–7.59 | 8.84–8.88 | 8.84–8.87 | 4.5 |
| `apif/prod/ball_scale_1/kairn` | 2.31–2.56 | 2.31–2.32 | 2.35–2.36 | 2.36 | 4.33–4.34 | 4.33–4.34 | 5.03–5.05 | 5.03–5.04 | 2.31 |
| `apif/prod/ball_scale_1/op` | 2.69–2.94 | 2.69 | 3.22–3.23 | 3.2 | 4.61–4.71 | 4.67–4.69 | 5.97–6 | 6.07–6.08 | 2.8 |
| `apif/prod/mul_1_1/kairn` | 0.718–0.798 | 0.717–0.721 | 0.712–0.714 | 0.712–0.713 | 1.32 | 1.31 | 1.31–1.32 | 1.31–1.32 | 0.564–0.57 |
| `apif/prod/mul_1_1/limb` | 0.718–0.803 | 0.714–0.715 | 0.718 | 0.717 | 0.791–0.794 | 0.79–0.792 | 0.791–0.794 | 0.791–0.794 | 0.544–0.545 |
| `apif/horner/mul_2_2+add_2_2/kairn` | 12.5–13.7 | 12.5 | 12.4 | 12.4 | 18.3–18.4 | 18.3–18.4 | 19.3–19.4 | 19.3 | 9.84–9.85 |
| `apif/horner/mul_2_2+add_2_2/op` | 12.5–13.9 | 12.5 | 12.8 | 12.6 | 18.5–18.6 | 18.5 | 19.3–19.4 | 19.3–19.4 | 10.6 |
| `apif/horner/mul_2_2+add_2_2/finite` | 12.5–13.7 | 12.5 | 12.4 | 12.4 | 18.3–18.4 | 18.3–18.4 | 19.4–19.5 | 19.4–19.5 | 9.84–9.85 |
| `apif/horner/mul_2_2+add_2_2/textbook` | 12.6–13.5 | 12.6 | 12.5 | 12.5 | 17.3–17.4 | 17.3–17.4 | 18.7–18.8 | 18.8 | 9.82 |
| `apif/horner/mul_2_1+add_2_1/kairn` | 8.02–8.79 | 8.02 | 7.9–7.91 | 7.9–7.91 | 11.6–11.7 | 11.6–11.7 | 14.6–14.7 | 14.6 | 7.31–7.32 |
| `apif/horner/mul_2_1+add_2_1/op` | 7.97–8.67 | 7.96–7.97 | 8 | 7.99–8 | 12–12.1 | 12 | 14.5–14.6 | 14.5–14.6 | 7.82–7.87 |
| `apif/horner/mul_2_1+add_2_1/finite` | 8.02–8.63 | 8.01–8.02 | 7.9–7.91 | 7.91 | 11.6–11.7 | 11.6–11.7 | 14.6–14.7 | 14.6 | 7.31–7.32 |
| `apif/horner/mul_2_1+add_2_1/textbook` | 7.98–8.93 | 7.98–7.99 | 7.89 | 7.89 | 11–11.1 | 11–11.1 | 13.8–13.9 | 13.8–13.9 | 7.32 |
| `apif/horner/ball_mul_2+ball_add_2/kairn` | 13–14.2 | 13 | 12.7 | 12.7 | 18.6 | 18.4–18.5 | 19.4–19.5 | 19.5 | 10.2 |
| `apif/horner/ball_mul_2+ball_add_2/op` | 12.8–14.1 | 12.8 | 12.8 | 12.7 | 18.7–18.8 | 18.7–18.8 | 19.6–19.7 | 19.6–19.7 | 11.2 |
| `apif/horner/ball_mul_1+ball_add_1/kairn` | 6.92–7.75 | 6.92 | 6.9–6.91 | 6.85–6.86 | 11.2–11.3 | 11.2–11.3 | 12.6 | 12.6 | 6.46 |
| `apif/horner/ball_mul_1+ball_add_1/op` | 7.21–7.88 | 7.21 | 7.24 | 7.21–7.22 | 11.6 | 11.6 | 12.8–12.9 | 12.8–12.9 | 7.16 |
| `apif/horner/mul_1_1+add_1_1/kairn` | 1.23–1.37 | 1.22–1.23 | 1.22 | 1.22–1.23 | 2.25–2.26 | 2.25–2.27 | 2.25–2.26 | 2.25–2.26 | 1.23 |
| `apif/horner/mul_1_1+add_1_1/limb` | 1.22–1.34 | 1.23 | 1.22–1.23 | 1.22–1.23 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.69–1.7 | 1.23 |
| `mpfr/tp/add_2_2/mpfr` | 6.62–6.7 | 6.58–6.62 | 6.58–6.64 | 6.59–6.66 | 14–14.1 | 14.3–14.4 | 14.1 | 14.3 | — |
| `mpfr/tp/mul_2_2/mpfr` | 7.08–7.21 | 7.08–7.28 | 7.05–7.13 | 7.06–7.1 | 15.2–15.5 | 15.4–15.6 | 15.5–15.6 | 15.3–15.4 | — |
| `mpfr/sum/add_2_2/mpfr` | 6.65–6.91 | 6.63–6.67 | 6.64–6.66 | 6.65–6.66 | 14 | 13.8–14 | 14.1–14.2 | 13.8–13.9 | — |
| `mpfr/prod/mul_2_2/mpfr` | 7.38–7.59 | 7.4–7.47 | 7.42–7.43 | 7.36–7.47 | 15.6–15.7 | 15.4–15.8 | 15.9–16 | 15.3–15.4 | — |
| `mpfr/horner/mul_2_2+add_2_2/mpfr` | 11.8–11.9 | 11.8–11.9 | 11.9 | 11.8–11.9 | 29.5–29.9 | 29.2–30.3 | 31.2–31.4 | 30.8–31.2 | — |
