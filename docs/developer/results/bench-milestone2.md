# Benchmarks, Milestone 2

What the parts of Milestone 2 that are on `main` cost
([Milestone 2 statements](../design/milestone2.md)): the building blocks that round down and up
without a rounding mode, `Interval<T, 1>` and `Interval<T, 2>`, the additions to `Ball`, a Horner
evaluation in each enclosure with the width of its result, `kairn::rational`, and the three settings
of `KAIRN_ENCLOSURE_CODE`. Kairn never changes the rounding mode: a sum or a product rounded down
or up is computed in round-to-nearest, as the rounded result, the sign of its exact error and one
step to the neighbor, so that an interval operation is straight-line code that vectorizes and runs
on a GPU. The price is more operations than one instruction under a directed mode; this page
measures it, against the classical way of changing the mode, against plain floors of `T`, and
against `Ball`. Two machines, four compilers, `-O2` and `-O3`, three runs of each, `double` and
`float` limbs, 2026-11-21, at commit `dee8ecd`. The harness and the exact commands are in
[`bench/`](https://github.com/danielepanozzo/kairn/tree/main/bench) (its README, "Milestone 2"); the
measurements, one JSON file per run, in
[`results/milestone2/bench/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/bench).
It is the first part of the milestone's benchmarks: [what is still to come](#still-to-come) is
measured later.

"M3" and "Zen 2" are the two machines ([How it was measured](#how-it-was-measured)). A **loop** is a
loop of independent operations over arrays in L1, timed per operation; a **chain** is a dependent
chain (a running sum, or a running product of factors near 1), timed per step. Every time is the
minimum over 41 (M3) or 31 (Zen 2) samples of about 4 ms; every ratio is a ratio of minima within
one run; a cell is the lowest and highest value over the three runs of a configuration, with
`-O2` and `-O3` given apart where they differ by more than 0.05 or 3%. **fenv** is
`std::fesetround` around each operation, **csr** a direct write of the control register (`FPCR`,
`MXCSR`) around each operation, **fenv_loop** the mode set once around a whole loop or chain
([below](#how-the-rounding-mode-props-honor-the-mode)). A function named in a table is one of the
harness, `BACKEND/KIND/KERNEL/VARIANT`: `m2` for `double` limbs, `m2f` for `float`, `m2p` packed;
`tp` a loop, `sum`, `prod`, `step` a chain, `lat` dependent evaluations; `op` the public operation,
`kairn` the generated kernel called on the limbs, `plain` the same values in plain arithmetic of
`T` ([bench/README.md](https://github.com/danielepanozzo/kairn/tree/main/bench), "Milestone 2").

## In short

- **A directed sum or product without a rounding mode costs 0.7 to 1.6 ns in a loop and 3.6 to 7.3
  ns per step of a dependent chain**, 4.5 to 11 and 4.8 to 16 times one plain operation. Changing
  the mode with `fesetround` around each operation costs about 25 ns per operation on both
  machines, 15 to 37 times Kairn in a loop. But a directed mode, once set, costs nothing:
  arithmetic under it runs as fast as under rounding to nearest on both machines, so a classical
  loop under one mode can be 4.5 to 11 times faster than Kairn (the props here that set the mode
  once around a loop, as their compilers compiled them, are 0.9 to 3.6 times faster).
  On Zen 2 even a direct write of `MXCSR` around each operation (1.3 to 1.6 ns) is cheaper than
  Kairn's step, 0.2 to 0.3 of its time in a chain; on the M3 a write of `FPCR` costs about 10 ns.
- **An `Interval<double, 1>` costs 2.3 to 3.2 times a `Ball<double, 1>` for a sum and 5.6 to 10
  times for a product (a Horner evaluation of degree 8: 2.4 to 6.6 times); with two limbs 3.5 to
  6.3 and 18 to 31 times (Horner: 5.8 to 8.1 times).** What the interval gives back in tightness is
  small: when the argument is wider than a few units in its last place, the dependency problem sets
  the width, and intervals are 0 to 11% narrower than balls; only at a point, or within a few units
  of the last place, is a ball of one limb wider (3.3 times, and 19%), and with two limbs the two
  are as tight.
- **The product of intervals of two limbs costs 29 to 81 ns**, 3.6 to 8.0 times that of one limb and
  18 to 31 times a product of balls of two limbs. Every compiler calls it rather than inlining it;
  the call costs about 1% of it in a loop and 3 to 7% in a chain.
- **The settings of `KAIRN_ENCLOSURE_CODE`: inline is what large functions cannot afford.** A
  function with 1 000 operations of intervals and balls compiles inline in 3.4 s (Apple clang) to
  140 s (GCC 13), one with 10 000 in 85 s to more than an hour, in up to 12.8 GB (GCC 16);
  outlined or external, in 0.3 to 1.8 s and 4.6 to 28 s. The price is a call per operation: 0.9 to
  1.2 times inline in a loop with Apple clang, 2 to 4 times where the compiler had vectorized the
  inline loop, 1.1 to 2.8 times in a chain. And a function of 10 000 inlined operations runs twice
  as slow as outlined on Zen 2 (Clang 18): its 5.9 MB of code no longer fits a core's caches.

## The answers

### 1. Rounding down and up without a rounding mode

`kairn::add_down`, `add_up`, `sub_down`, `sub_up`, `mul_down`, `mul_up` (`blocks.hpp`) on `double`,
against one plain operation of `double`, and against the same directed result obtained by changing
the rounding mode: around each operation with `std::fesetround` (fenv) or by writing the control
register (csr), or once around the whole loop or chain (fenv_loop). The props compute exactly
Kairn's results, bit for bit ([below](#how-the-rounding-mode-props-honor-the-mode)).

| Times (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/add/plain` | 0.147 to 0.152 | 0.156 to 0.162 | 0.154 to 0.155 | 0.153 to 0.154 |
| `m2/tp/add_down/op` | 0.688 to 0.717 | 0.789 to 0.822 | 1.56 to 1.57 | 1.05 to 1.06 |
| `m2/tp/add_down/fenv` | 24.6 to 25.3 | 24.7 to 25.7 | 25 to 25.3 | 25 to 25.1 |
| `m2/tp/add_down/csr` | 19.4 to 20 | 21.7 to 22.9 (-O2), 21.9 to 22.1 (-O3) | 1.27 to 1.28 | 1.56 to 1.57 |
| `m2/tp/add_down/fenv_loop` | 0.398 to 0.41 | 0.246 to 0.257 | 0.854 to 0.869 | 1.15 to 1.16 |
| `m2/tp/mul_down/op` | 0.776 to 0.81 | 0.778 to 0.794 | 1.36 to 1.38 | 1.05 to 1.06 |
| `m2/tp/mul_down/fenv` | 24.6 to 25.4 | 24.8 to 25.7 | 25.1 to 25.2 | 25 to 25.1 |
| `m2/sum/add/plain` | 0.366 to 0.401 (-O2), 0.399 to 0.409 (-O3) | 0.499 to 0.519 (-O2), 0.465 to 0.501 (-O3) | 0.804 to 0.811 | 0.803 to 0.807 |
| `m2/sum/add_down/op` | 5.83 to 5.95 (-O2), 5.44 to 6.09 (-O3) | 3.9 to 4.06 | 4.79 to 4.8 | 6.22 to 6.24 |
| `m2/sum/add_down/fenv` | 24.6 to 25.1 | 24.6 to 25.7 | 24.4 to 24.6 | 24.4 to 24.5 |
| `m2/sum/add_down/csr` | 16.6 to 18.2 (-O2), 17.8 to 18.2 (-O3) | 21.3 to 22.9 (-O2), 19.3 to 21 (-O3) | 1.27 to 1.28 | 1.27 |
| `m2/sum/add_down/fenv_loop` | 0.714 to 0.783 (-O2), 0.75 to 0.767 (-O3) | 0.782 to 0.798 (-O2), 0.715 to 0.78 (-O3) | 1.58 to 1.61 | 1.58 to 1.59 |
| `m2/prod/mul_down/op` | 5.73 to 6.27 (-O2), 6.14 to 6.4 (-O3) | 3.84 to 4.01 (-O2), 3.58 to 3.9 (-O3) | 5.99 to 6.01 | 7.21 to 7.31 |

| Kairn over the plain operation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add_down` over one `add` of T, loop | 4.64 to 4.71 | 5.06 to 5.28 (-O2), 5.05 (-O3) | 10.1 to 10.2 | 6.85 to 6.86 |
| `mul_down` over one `mul` of T, loop | 5.31 to 5.40 (-O2), 5.15 to 5.32 (-O3) | 4.85 to 5.01 (-O2), 5.01 to 5.02 (-O3) | 8.87 to 8.94 | 6.86 to 6.90 |
| `add_down` over one `add` of T, chain | 14.9 to 15.9 (-O2), 13.6 to 15.0 (-O3) | 7.55 to 7.83 (-O2), 7.81 to 8.42 (-O3) | 5.92 to 5.95 | 7.73 to 7.74 |
| `mul_down` over one `mul` of T, chain | 8.01 to 8.18 (-O2), 8.01 to 8.31 (-O3) | 4.93 to 5.16 (-O2), 5.02 to 5.38 (-O3) | 7.44 to 7.50 | 8.97 to 9.08 |

| Against a change of the rounding mode | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add_down`, loop: fenv over Kairn | 35.8 to 36.4 (-O2), 35.3 to 35.8 (-O3) | 31.0 to 31.8 | 16.0 to 16.1 | 23.7 to 23.8 |
| `add_down`, loop: csr over Kairn | 28.2 to 28.6 (-O2), 27.7 to 28.9 (-O3) | 26.4 to 27.9 (-O2), 27.3 to 28.0 (-O3) | 0.81 to 0.82 | 1.48 |
| `add_down`, loop: Kairn over fenv_loop | 1.70 to 1.73 (-O2), 1.69 to 1.76 (-O3) | 3.19 to 3.25 | 1.81 to 1.83 | 0.91 to 0.92 |
| `mul_down`, loop: fenv over Kairn | 31.7 to 32.3 (-O2), 31.3 to 31.7 (-O3) | 31.7 to 32.4 | 18.2 to 18.4 | 23.7 |
| `mul_down`, loop: csr over Kairn | 23.6 to 25.4 (-O2), 24.5 to 24.9 (-O3) | 27.6 to 28.4 (-O2), 27.4 to 27.6 (-O3) | 0.93 (-O2), 1.19 to 1.20 (-O3) | 1.48 |
| `mul_down`, loop: Kairn over fenv_loop | 1.91 to 1.97 (-O2), 1.94 to 2.00 (-O3) | 3.08 to 3.24 (-O2), 3.15 to 3.19 (-O3) | 1.58 to 1.60 | 0.91 to 0.92 |
| `add_down`, chain: fenv over Kairn | 4.21 to 4.26 (-O2), 4.13 to 4.61 (-O3) | 6.32 to 6.51 (-O2), 6.29 to 6.33 (-O3) | 5.09 to 5.14 | 3.92 to 3.93 |
| `add_down`, chain: csr over Kairn | 2.85 to 3.08 (-O2), 2.99 to 3.34 (-O3) | 5.46 to 5.64 (-O2), 4.85 to 5.39 (-O3) | 0.26 to 0.27 | 0.20 |
| `add_down`, chain: Kairn over fenv_loop | 7.56 to 8.17 (-O2), 7.12 to 7.95 (-O3) | 4.89 to 5.09 (-O2), 5.10 to 5.47 (-O3) | 2.99 to 3.02 | 3.92 to 3.93 |
| `mul_down`, chain: fenv over Kairn | 3.95 to 4.01 (-O2), 3.95 to 4.09 (-O3) | 6.26 to 6.53 (-O2), 6.28 to 6.80 (-O3) | 4.07 to 4.08 | 3.35 to 3.39 |
| `mul_down`, chain: csr over Kairn | 2.84 to 2.91 (-O2), 2.85 to 2.96 (-O3) | 4.87 to 5.12 (-O2), 5.34 to 5.82 (-O3) | 0.21 | 0.17 to 0.18 |
| `mul_down`, chain: Kairn over fenv_loop | 5.36 to 5.41 (-O2), 5.26 to 5.48 (-O3) | 3.27 to 3.43 (-O2), 3.19 to 3.34 (-O3) | 3.78 to 3.79 (-O2), 7.15 to 7.20 (-O3) | 4.58 to 4.63 |

- **Kairn's directed sum or product costs 0.7 to 1.6 ns in a loop**, 4.5 to 10.7 times one plain
  operation of `double`, which the compilers vectorize. Each is a short listing of about fifteen
  operations (the sum and its error by `two_sum_ord`, a test of the error's sign, a step to the
  neighbor on the bit pattern, a select) that the processor overlaps across iterations. **In a
  chain** the step and the select wait for the error term: 3.6 to 7.3 ns per step, 4.8 to 16 times
  a plain addition or product.
- **Changing the mode with `fesetround` around each operation costs about 25 ns per operation on
  both machines**: 15 to 37 times Kairn in a loop, 3.2 to 6.9 times in a chain. That is two calls
  of the C library, each reading and writing the control register (glibc's also the x87 control
  word).
- **Writing the control register directly is cheap on Zen 2 and dear on the M3.** On Zen 2,
  `vldmxcsr` around each operation costs 1.3 to 1.6 ns per operation: 0.74 to 1.5 times Kairn in a
  loop, and 0.17 to 0.27 times in a chain, where the two writes are not on the critical path and
  Kairn's step is. On the M3 it costs 19 to 23 ns per operation (22 to 29 times Kairn in a loop, 2.8
  to 6.2 in a chain): about 10 ns per write of `FPCR`, as if each waited for the operations before
  it.
- **Where the mode can stay set for a whole loop, the classical way is faster.** The props that set
  it once around the loop take 0.25 to 1.2 ns per operation: Kairn takes 1.6 to 3.6 times as long
  with Apple clang, GCC 16 and GCC 13, and 0.9 to 1.2 times with Clang 18, which does not vectorize
  under `FENV_ACCESS` ([below](#what-the-machine-code-shows)); in a chain 3.0 to 8.2 times, the
  latency of Kairn's step against that of one addition. And the props are not the limit:
  **arithmetic under a directed mode runs exactly as fast as under rounding to nearest** on both
  machines (the same loop of additions or products under each of the four modes, within 1%, with
  every compiler: the table below), so a loop that a compiler emits as it emits the plain one runs at
  the speed of one plain operation, 4.5 to 11 times faster than Kairn. That is the trade measured:
  Kairn's directed rounding costs a few operations where a mode, once set, costs nothing, and saves
  the change of mode wherever one would be needed for each operation.

The loop under each mode (`bench/m2_modes.cpp`) is compiled as plain code, without the FMA option
of the harness, so its absolute times are those of 128-bit or scalar loops; what matters is that
the four rows of an operation agree. That the loops did compute under the mode set is checked: of
their 1 024 directed results, 512 differ from the results rounded to nearest, every one on the
right side.

| Loop under the mode, ns per element | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | M3, Apple clang -O2 | M3, GCC 16 -O2 |
|---|---|---|---|---|---|---|
| `add`, nearest | 0.233 | 0.233 | 0.333 | 0.332 | 0.106 | 0.308 |
| `add`, downward | 0.233 | 0.233 | 0.333 | 0.332 | 0.106 | 0.308 |
| `add`, upward | 0.233 | 0.233 | 0.332 | 0.332 | 0.106 | 0.308 |
| `add`, towardzero | 0.232 | 0.233 | 0.333 | 0.331 | 0.106 | 0.308 |
| `mul`, nearest | 0.232 | 0.233 | 0.333 | 0.21 | 0.105 | 0.308 |
| `mul`, downward | 0.233 | 0.234 | 0.333 | 0.212 | 0.106 | 0.308 |
| `mul`, upward | 0.232 | 0.233 | 0.333 | 0.21 | 0.106 | 0.308 |
| `mul`, towardzero | 0.233 | 0.233 | 0.333 | 0.21 | 0.106 | 0.307 |

| The other blocks | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `next_up`, loop, over `std::nextafter` | 0.17 to 0.19 | 0.18 | 0.07 to 0.08 | 0.09 to 0.10 |
| `next_up`, chain, over `std::nextafter` | 0.43 to 0.46 | 0.36 to 0.37 | 0.50 to 0.54 | 0.43 to 0.45 |
| `next_up`, loop, over one addition | 2.68 to 2.73 | 2.44 to 2.55 (-O2), 2.44 to 2.45 (-O3) | 3.82 to 3.84 | 4.71 to 4.76 |
| `radd`, loop, over one addition | 3.49 to 3.54 | 3.07 to 3.08 | 6.30 to 6.33 | 7.48 to 7.50 |
| `rmul`, loop, over one product | 3.06 to 3.11 (-O2), 2.99 to 3.05 (-O3) | 2.57 to 2.68 (-O2), 2.67 (-O3) | 5.35 to 5.36 | 6.40 to 6.48 |
| `two_sum`, loop, over one addition | 2.28 to 2.30 | 2.21 to 2.29 (-O2), 2.23 (-O3) | 3.88 to 3.93 | 10.2 to 10.4 |
| `two_prod`, loop, over one product | 1.37 to 1.40 (-O2), 1.34 to 1.37 (-O3) | 1.75 to 1.82 (-O2), 1.83 (-O3) | 2.97 to 2.98 | 4.04 to 4.14 |
| the public block over the generated kernel, `add_down`, loop | 1.17 to 1.20 | 1.09 to 1.11 | 1.15 to 1.17 | 1.19 |
| the public block over the generated kernel, `mul_down`, loop | 1.00 | 0.98 to 1.01 | 0.99 to 1.00 | 1.00 |

`next_up` and `next_down`, integer operations on the bit pattern, are 5 to 14 times faster than
`std::nextafter` in a loop and two to three times as fast in a chain. A public block that adds its
operands guards them first (rule R3: two additions), which costs 9 to 20% of `add_down` in a loop;
the products have no guard (1.00).

### 2. `Interval<T, 1>`

The public operators of `Interval<double, 1>` on arrays of intervals, against (a) two plain
operations of `double` on the bounds (no outward rounding, not an enclosure), and the four products
of bounds with their least and greatest, rounded to nearest; (b) the classical interval operation
with the mode changed: down for the lower bound, up for the upper bound, and for the product the
four products of bounds under each mode, the least of the four rounded down and the greatest of
the four rounded up; (c) `Ball<double, 1>` for the same operation, on the balls of the same
intervals.

**Why the four products.** They are what Kairn's `interval_mul_1` computes, with the same least and
greatest, so the prop computes the same function and differs from Kairn only in how it rounds; and
the product has no branch, like Kairn's. The usual case analysis on the signs of the bounds needs
two products under each mode for most cases instead of four, and branches. Where the mode is
changed around each operation, the changes dominate (three per product) and the number of products
matters little; where it is set once around a loop, a case analysis on operands of predictable signs
could, by the count of its products, be up to about twice as fast as the four products (not
measured), so fenv_loop is a conservative baseline for the product, and a fair one for the sum and
the difference, which have no choice.

| Times (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/interval_add_1/op` | 1.87 to 1.92 | 1.77 to 1.84 | 3.6 to 3.63 | 4.59 to 4.7 |
| `m2/tp/interval_mul_1/op` | 6.08 to 6.3 | 7.97 to 8.29 | 10 to 10.1 | 17.2 to 17.4 |
| `m2/tp/pair_add_1/plain` | 0.29 to 0.301 | 0.295 to 0.308 | 0.329 to 0.332 | 0.633 to 0.635 |
| `m2/tp/plain4_mul_1/plain` | 0.746 to 0.777 | 0.961 to 0.981 (-O2), 1.07 to 1.09 (-O3) | 1.03 to 1.04 | 1.14 to 1.15 |
| `m2/tp/interval_add_1/fenv` | 34.6 to 37.8 (-O2), 36.8 to 37.5 (-O3) | 36.9 to 38.4 (-O2), 36.2 to 37.5 (-O3) | 37.3 to 37.8 | 37.2 to 37.3 |
| `m2/tp/interval_mul_1/fenv` | 37.1 to 38 | 36.8 to 38.4 | 38.4 to 38.5 (-O2), 117 to 118 (-O3) | 39.1 to 39.4 |
| `m2/tp/interval_mul_1/csr` | 29.6 to 30.6 | 34.6 to 34.7 (-O2), 32.2 to 34.6 (-O3) | 4 to 4.03 | 4.67 to 4.85 |
| `m2/tp/interval_add_1/fenv_loop` | 0.493 to 0.505 | 0.64 to 0.667 (-O2), 0.505 to 0.517 (-O3) | 1.47 to 1.49 | 1.64 to 1.66 |
| `m2/tp/interval_mul_1/fenv_loop` | 1.44 to 1.47 | 1.07 to 1.12 | 1.82 to 1.85 | 3.86 to 3.88 (-O2), 4.12 to 4.21 (-O3) |
| `m2/tp/ball_add_1/op` | 0.774 to 0.807 | 0.752 to 0.782 | 1.4 to 1.42 | 1.47 to 1.48 |
| `m2/tp/ball_mul_1/op` | 0.981 to 1.02 | 0.966 to 1.01 (-O2), 0.92 to 0.938 (-O3) | 1.8 to 1.82 | 1.66 |
| `m2/sum/interval_add_1/op` | 5.49 to 5.72 | 3.86 to 4.03 | 5.73 to 5.78 | 6.74 to 6.8 |
| `m2/prod/interval_mul_1/op` | 10.5 to 11.1 (-O2), 11.4 to 11.6 (-O3) | 10.3 to 10.6 | 18.8 to 19 | 18.4 to 18.6 |
| `m2/prod/interval_mul_1/fenv_loop` | 3.07 to 3.36 (-O2), 3.37 to 3.42 (-O3) | 3.67 (-O2), 3.65 to 3.85 (-O3) | 3.74 to 3.79 | 3.18 to 3.19 |
| `m2/sum/ball_add_1/op` | 2.6 to 2.84 (-O2), 2.83 to 2.9 (-O3) | 2.83 to 2.86 (-O2), 2.54 to 2.73 (-O3) | 3.91 to 3.95 | 3.91 to 3.92 |
| `m2/prod/ball_mul_1/op` | 4.69 to 5.13 (-O2), 5.13 to 5.25 (-O3) | 5.45 to 5.69 (-O2), 4.63 to 4.97 (-O3) | 8.23 to 8.37 | 7.71 to 7.75 |

| Interval<T, 1> over the floor | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop, over two plain operations | 6.24 to 6.37 (-O2), 6.37 to 6.58 (-O3) | 5.95 to 6.13 | 10.9 to 11.0 | 7.24 to 7.40 |
| `interval_mul_1`, loop, over two plain operations | 20.5 to 21.0 | 26.3 to 26.9 (-O2), 26.9 to 27.3 (-O3) | 30.4 to 30.5 | 27.9 to 28.1 |
| `interval_mul_1`, loop, over the four products rounded to nearest | 8.11 to 8.20 | 8.29 to 8.46 (-O2), 7.42 to 7.51 (-O3) | 9.70 to 9.77 | 15.1 to 15.2 |
| `interval_add_1`, chain, over two plain additions | 9.6 to 10.4 (-O2), 9.57 to 9.78 (-O3) | 7.21 to 7.30 (-O2), 7.69 to 8.33 (-O3) | 7.10 to 7.14 | 8.38 to 8.46 |
| `interval_mul_1`, chain, over the four products rounded to nearest | 4.73 to 4.89 (-O2), 4.30 to 4.37 (-O3) | 3.84 to 3.95 (-O2), 4.05 to 4.33 (-O3) | 8.70 to 8.82 | 3.76 to 3.80 |

| Interval<T, 1> against a change of the rounding mode | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop: fenv over Kairn | 18.5 to 20.2 (-O2), 19.2 to 19.7 (-O3) | 20.2 to 20.8 (-O2), 20.5 to 20.9 (-O3) | 10.4 to 10.5 | 7.93 to 8.12 |
| `interval_add_1`, loop: csr over Kairn | 14.0 to 15.3 (-O2), 14.7 to 15.1 (-O3) | 16.8 to 18.0 (-O2), 16.3 to 17.4 (-O3) | 0.60 to 0.61 (-O2), 0.69 (-O3) | 0.53 to 0.54 |
| `interval_add_1`, loop: Kairn over fenv_loop | 3.72 to 3.80 (-O2), 3.78 to 3.86 (-O3) | 2.76 to 2.87 (-O2), 3.47 to 3.50 (-O3) | 2.42 to 2.46 | 2.84 to 2.85 (-O2), 2.76 to 2.77 (-O3) |
| `interval_mul_1`, loop: fenv over Kairn | 5.95 to 6.11 | 4.54 to 4.71 (-O2), 4.54 to 4.63 (-O3) | 3.81 to 3.83 (-O2), 11.7 (-O3) | 2.26 to 2.28 |
| `interval_mul_1`, loop: csr over Kairn | 4.92 to 4.94 (-O2), 4.75 to 4.85 (-O3) | 4.18 to 4.35 (-O2), 4.03 to 4.26 (-O3) | 0.40 | 0.27 to 0.28 |
| `interval_mul_1`, loop: Kairn over fenv_loop | 4.22 to 4.30 | 7.34 to 7.55 | 5.45 to 5.51 | 4.43 to 4.48 (-O2), 4.10 to 4.21 (-O3) |
| `interval_add_1`, chain: fenv over Kairn | 6.58 to 6.71 | 9.31 to 9.70 (-O2), 9.53 to 9.63 (-O3) | 6.44 to 6.50 | 5.42 to 5.49 |
| `interval_add_1`, chain: csr over Kairn | 4.51 to 4.84 (-O2), 4.74 to 4.84 (-O3) | 7.80 to 8.25 (-O2), 8.11 to 8.27 (-O3) | 0.33 | 0.32 |
| `interval_add_1`, chain: Kairn over fenv_loop | 6.69 to 7.19 (-O2), 6.73 to 6.84 (-O3) | 4.77 to 4.95 (-O2), 4.79 to 5.07 (-O3) | 3.55 to 3.57 | 4.24 to 4.28 |
| `interval_mul_1`, chain: fenv over Kairn | 3.32 to 3.41 (-O2), 3.23 to 3.28 (-O3) | 3.66 to 3.75 (-O2), 3.45 to 3.57 (-O3) | 2.03 to 2.05 | 2.10 to 2.14 |
| `interval_mul_1`, chain: csr over Kairn | 2.54 to 2.59 (-O2), 2.48 to 2.51 (-O3) | 3.30 to 3.34 (-O2), 3.15 to 3.27 (-O3) | 0.19 to 0.20 | 0.23 to 0.24 |
| `interval_mul_1`, chain: Kairn over fenv_loop | 3.28 to 3.41 (-O2), 3.34 to 3.40 (-O3) | 2.81 to 2.88 (-O2), 2.73 to 2.85 (-O3) | 5.02 to 5.07 | 5.78 to 5.83 |

| Interval<T, 1> over Ball<T, 1> | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, loop: interval over ball | 2.37 to 2.43 | 2.35 to 2.41 (-O2), 2.28 to 2.33 (-O3) | 2.55 to 2.58 | 3.12 to 3.18 |
| `X * Y`, loop: interval over ball | 6.19 to 6.22 (-O2), 6.16 to 6.36 (-O3) | 7.95 to 8.39 (-O2), 8.65 to 8.75 (-O3) | 5.56 to 5.57 | 10.4 |
| `S + X`, chain: interval over ball | 1.97 to 2.11 (-O2), 1.97 to 1.98 (-O3) | 1.35 to 1.43 (-O2), 1.42 to 1.53 (-O3) | 1.46 to 1.48 | 1.72 to 1.74 |
| `P * X`, chain: interval over ball | 2.15 to 2.23 (-O2), 2.17 to 2.23 (-O3) | 1.81 to 1.91 (-O2), 2.09 to 2.24 (-O3) | 2.26 to 2.31 | 2.38 to 2.41 |

| The other functions of Interval<T, 1>, loops | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `-X` over two negations | 0.55 to 0.60 | 1.00 to 1.02 | 0.59 | 0.50 |
| `hull` over a min and a max | 0.98 to 1.00 | 1.00 | 1.00 | 1.00 |
| `intersection` over a max, a min and a test | 1.01 to 1.03 | 0.97 to 1.00 | 1.01 | 1.00 |
| `midpoint` and `radius` over (l + h)/2, (h - l)/2 | 21.1 to 22.2 (-O2), 21.6 to 21.8 (-O3) | 25.5 to 26.0 (-O2), 11.1 to 11.2 (-O3) | 52.1 to 52.2 (-O2), 22.2 to 22.3 (-O3) | 19.7 |
| `split` over (l + h)/2, (h - l)/2 | 10.6 to 11.3 (-O2), 11.1 to 11.5 (-O3) | 8.42 to 8.58 | 24.2 to 24.8 | 15.8 to 15.9 |
| `Ball<T, 1>(X)` over (l + h)/2, (h - l)/2 | 14.0 to 14.7 (-O2), 14.4 to 14.7 (-O3) | 11.8 to 12.2 (-O2), 8.83 to 8.97 (-O3) | 32.4 to 32.5 (-O2), 23.4 to 23.5 (-O3) | 15.0 to 15.1 |
| `Interval<T, 1>(B)` over c - r, c + r | 5.10 to 5.23 | 5.64 to 5.79 (-O2), 5.79 to 5.81 (-O3) | 10.8 to 11.1 | 7.27 to 7.29 |

- **A sum of intervals costs 1.8 ns (M3) to 4.7 ns (Zen 2, Clang 18) in a loop, a product 6.1 to
  17.4 ns**: 4.4 to 11 times two plain additions, 20 to 31 times two plain products, and 7.4 to 15
  times the four products with their least and greatest rounded to nearest. A sum is two directed
  sums, a product eight directed products ([Interval kernels](../design/milestone2.md#one-limb)),
  each a few operations more than the operation it rounds. In a chain a sum costs 7.1 to 10 times two
  plain additions, a product 3.8 to 8.8 times the four plain products.
- **Against the classical interval with a change of mode around each operation, Kairn is faster
  everywhere with `fesetround`** (7.9 to 21 times for a sum, 2.3 to 12 for a product in a loop, 2.0
  to 9.7 in a chain), and on the M3 also against a direct write of `FPCR` (14 to 18 times for a sum,
  4.0 to 4.9 for a product). **On Zen 2 the classical interval that writes `MXCSR` around each bound
  is faster than Kairn**: it takes 0.53 to 0.69 of Kairn's time for a sum, 0.27 to 0.40 for a
  product, 0.19 to 0.33 in a chain. A write of `MXCSR` costs less there than Kairn's step and test.
- **Where the mode stays set for a whole loop**, upward only, the lower bound as the negation of
  the upward rounding of the negated value, the classical interval is 2.4 to 4.0 times faster than
  Kairn for a sum and 4.1 to 7.6 times for a product in a loop, 2.7 to 7.2 times in a chain. And
  since a mode, once set, costs nothing ([question 1](#1-rounding-down-and-up-without-a-rounding-mode)),
  the floors are what such a loop reaches when its compiler emits the plain code for it: two plain
  additions, 4.4 to 11 times faster than Kairn's sum, and the four plain products with their least
  and greatest, 7.4 to 15 times faster than Kairn's product.
- **Against `Ball<double, 1>`**, an interval costs 2.3 to 3.2 times as much for a sum and 5.6 to 10.4
  times for a product in a loop, 1.4 to 2.1 and 1.8 to 2.4 times in a chain. A ball's product is one
  product of the centers and a radius of three fused operations; the interval's is eight directed
  products.
- **The other functions.** Negation, hull and intersection cost what their plain forms cost (the
  hull and the intersection are comparisons and selects; the negation 0.50 to 1.02 of the plain
  prop). The midpoint and the radius, `split` and the conversion to a ball cost 8 to 52 times their
  plain forms ((l + h)/2 and (h − l)/2), because the listing handles the special values, halves
  before adding, moves the midpoint into the interval and rounds the radius up; and `midpoint()`
  with `radius()` computes the kernel twice ([finding 1](#what-the-machine-code-shows)). The
  conversion of a ball to an interval costs 5 to 11 times $c - r$ and $c + r$.

### 3. `Interval<T, 2>`

The public operators of `Interval<double, 2>`, against the operation of `Expansion<double, 2>` (its
public operator, with the fix-up) done twice, on the lower bounds and on the upper ones (the floor:
no outward move); against the four products of `Expansion<double, 2>` and their least and greatest;
and against `Ball<double, 2>`. The product of two limbs, `interval_mul_2`, is an ordinary inline
function and not forced inline, so it is measured as the compilers compile it, and again in a
function compiled with `__attribute__((flatten))`, which asks the compiler to inline every call in
it; the cost of a call itself is measured on a function of the same signature (eight limbs in,
four out through references) with almost no body, called and not inlined.

| Times (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/interval_add_2/op` | 8.5 to 8.83 | 7.23 to 7.45 (-O2), 7.59 to 7.69 (-O3) | 24.7 to 24.9 | 18.7 to 18.9 |
| `m2/tp/interval_mul_2/op` | 29.2 to 30.5 | 29.4 to 30.1 | 79.8 to 80.9 | 73.8 to 75.1 |
| `m2/tp/interval_mul_2/flat` | 29.3 to 30.5 | 27.8 to 29 | 72.9 to 74.4 | 74.3 to 75.1 |
| `m2/tp/pair_add_2/op` | 3.08 to 3.18 | 3.31 to 3.39 (-O2), 3.21 to 3.27 (-O3) | 8.8 to 8.9 | 4.01 to 4.04 |
| `m2/tp/pair_mul_2/op` | 1.56 to 1.63 | 1.72 to 1.8 | 4.96 to 5.02 | 2.76 to 2.78 |
| `m2/tp/ball_add_2/op` | 1.96 to 2.05 | 2.06 to 2.13 | 4.16 to 4.2 | 3.01 to 3.04 |
| `m2/tp/ball_mul_2/op` | 1.51 to 1.57 | 1.54 to 1.6 | 3.79 to 3.85 | 2.4 to 2.41 |
| `m2/sum/interval_add_2/op` | 20.6 to 21.4 | 16.1 to 16.7 | 28.7 to 29 | 26.1 to 26.2 |
| `m2/prod/interval_mul_2/op` | 42.2 to 43.7 | 43.9 to 45.9 | 87.3 to 88.2 | 82.7 to 83.2 |
| `m2/sum/ball_add_2/op` | 7.31 to 8 (-O2), 7.99 to 8.18 (-O3) | 7.79 to 7.95 (-O2), 7.17 to 7.7 (-O3) | 10.6 to 10.7 | 10.4 |
| `m2/prod/ball_mul_2/op` | 5.56 to 6.08 (-O2), 6.08 to 6.1 (-O3) | 6.18 to 6.19 (-O2), 5.64 to 6.02 (-O3) | 8.23 to 8.33 | 8.33 to 8.35 |
| `m2/tp/call_8_4/plain` | 0.812 to 0.846 | 0.812 to 0.846 | 1.86 to 1.88 | 1.55 to 1.56 (-O2), 2.17 to 2.18 (-O3) |
| `m2/tp/call_8_4/kairn` | 0.609 to 0.635 | 0.496 to 0.62 (-O2), 0.495 to 0.625 (-O3) | 0.962 to 0.97 | 0.961 to 0.965 |
| `m2/prod/call_8_4/plain` | 1.92 to 2.77 (-O2), 1.89 to 2.74 (-O3) | 1.92 to 1.97 (-O2), 1.85 to 1.88 (-O3) | 2.48 to 2.51 | 2.45 to 2.46 |

| Interval<T, 2> | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, loop, over `Expansion<T, 2>` twice | 2.75 to 2.78 | 2.13 to 2.23 (-O2), 2.35 to 2.36 (-O3) | 2.80 to 2.81 | 4.62 to 4.68 |
| `X * Y`, loop, over `Expansion<T, 2>` twice | 18.5 to 18.7 (-O2), 18.2 to 18.7 (-O3) | 16.4 to 17.5 (-O2), 16.9 to 17.0 (-O3) | 16.0 to 16.2 | 26.7 to 27.2 |
| `X * Y`, loop, over the four products of `Expansion<T, 2>` | 4.31 to 4.40 | 5.00 to 5.11 | 5.72 to 5.87 | 14.1 to 14.2 (-O2), 13.9 to 14.3 (-O3) |
| `S + X`, chain, over `Expansion<T, 2>` twice | 2.60 to 2.78 (-O2), 2.60 to 2.71 (-O3) | 1.93 to 2.03 (-O2), 2.01 to 2.17 (-O3) | 2.60 | 2.42 to 2.44 |
| `P * X`, chain, over `Expansion<T, 2>` twice | 7.10 to 7.65 (-O2), 7.06 to 7.25 (-O3) | 7.29 to 7.68 (-O2), 7.36 to 7.89 (-O3) | 10.3 to 10.4 | 9.90 to 9.98 |
| `X + Y`, loop: interval over ball | 4.31 to 4.41 | 3.45 to 3.50 (-O2), 3.67 to 3.69 (-O3) | 5.92 to 5.95 | 6.17 to 6.25 |
| `X * Y`, loop: interval over ball | 19.1 to 19.5 | 18.4 to 18.8 (-O2), 18.9 to 19.0 (-O3) | 20.9 to 21.1 | 30.8 to 31.2 |
| `S + X`, chain: interval over ball | 2.62 to 2.82 (-O2), 2.58 to 2.62 (-O3) | 2.02 to 2.10 (-O2), 2.09 to 2.26 (-O3) | 2.70 to 2.71 | 2.51 to 2.52 |
| `P * X`, chain: interval over ball | 7.05 to 7.59 (-O2), 7.01 to 7.19 (-O3) | 7.34 to 7.43 (-O2), 7.32 to 7.79 (-O3) | 10.6 | 9.90 to 9.99 |
| `X + Y` of two limbs over one limb, loop | 4.54 to 4.61 (-O2), 4.43 to 4.62 (-O3) | 3.94 to 4.07 (-O2), 4.28 to 4.30 (-O3) | 6.85 to 6.89 | 4.01 to 4.09 |
| `X * Y` of two limbs over one limb, loop | 4.71 to 4.82 (-O2), 4.69 to 4.84 (-O3) | 3.63 to 3.77 (-O2), 3.62 to 3.68 (-O3) | 7.92 to 8.02 | 4.28 to 4.33 |
| `X * Y`, loop: as called over flattened | 0.98 to 1.00 | 1.04 to 1.08 | 1.08 to 1.10 | 0.99 to 1.00 |
| `P * X`, chain: as called over flattened | 0.98 to 1.02 | 1.09 to 1.11 | 1.08 | 0.99 to 1.00 |
| a call of the same signature, loop: its time over that of `X * Y` | 0.01 | 0.01 | 0.01 | 0.01 to 0.02 |
| a call of the same signature, chain: its time over that of `P * X` | 0.04 to 0.07 | 0.04 | 0.03 | 0.03 |
| `hull`, loop, over `X + Y` of `Expansion<T, 2>` twice | 0.42 | 0.38 to 0.40 | 0.35 | 0.38 |

- **A sum of intervals of two limbs costs 7.2 ns (M3) to 25 ns (Zen 2, GCC 13) in a loop, a product
  29 to 81 ns.** A sum is 2.1 to 4.7 times the sum of `Expansion<double, 2>` done twice, and in a
  chain 1.9 to 2.8 times; a product 16 to 27 times the product done twice, and 4.3 to 14 times the
  four products of `Expansion<double, 2>` with their least and greatest, which is what it computes
  before moving each bound outward (four `mul_ext_2_2`, each a product of two limbs, its error
  bound, two directed sums and two renormalizations, and the selects of the special values). It is
  3.9 to 6.9 times the sum, and 3.6 to 8.0 times the product, of intervals of one limb.
- **Against `Ball<double, 2>`**, an interval of two limbs costs 3.5 to 6.3 times as much for a sum
  and 18 to 31 times for a product in a loop; 2.0 to 2.8 and 7.0 to 10.6 times in a chain.
- **The product is called, not inlined, by every compiler at `-O2` and `-O3`**, as
  [Inlining and compile time](../design/milestone2.md#inlining-and-compile-time) allows: its loop
  holds a call of `kairn::gen::interval_mul_2`. **The call costs about 1% of the product in a loop
  and 3 to 7% in a chain.** A function of the same signature with no body takes 0.2 (M3) to 1.2 ns
  more than the same copies inline in a loop, where the product takes 29 to 81 ns; in a chain the
  call takes 1.9 to 2.8 ns, where a step of the product takes 42 to 88 ns. Where GCC inlines the
  body anyway (`flatten`), the product is 4 to 11% faster, more than the call itself (presumably
  because the body is then scheduled with the loop around it). Forcing it inline would buy little
  and cost compile time ([question 7](#7-the-settings-of-kairn_enclosure_code)).
- **The hull and the intersection** are comparisons and selects: 1.3 to 4.3 ns, about a third of
  the sum of `Expansion<double, 2>` done twice.

### 4. A polynomial: cost and tightness

The Chebyshev polynomial $T_8(x) = 128x^8 - 256x^6 + 160x^4 - 32x^2 + 1$ evaluated by Horner's rule,
$p = c_8$, $p = p\,x + c_k$, written once as a template for every type, as
[the tutorial](../../tutorials/intervals.md#a-polynomial-over-an-interval) writes its polynomials,
the coefficients sets of one point made once outside the loop. Its coefficients are integers, so
every width below comes from the arithmetic and from the dependency problem, and its range is known
exactly: on $[a, b] \subseteq [-1, 1]$ it is spanned by $T_8(a)$, $T_8(b)$ and the extrema $\pm 1$
at the points $\cos(k\pi/8)$ inside, computed in `Expansion<double, 2>` arithmetic (within about
$10^{-28}$). The time is per evaluation, in a loop of 256 independent evaluations on narrow
arguments (half-width $2^{-30}$ of $\max(\lvert x\rvert, 1/16)$ for `double`, $x$ in $[-1, 1]$),
and dependent ones (each argument made to depend on the previous result through a zero, which adds a
product and an addition per evaluation).

| Horner, independent evaluations: ns per evaluation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| Interval<T, 1> | 124 to 126 (-O2), 120 to 128 (-O3) | 109 to 114 | 250 to 258 | 182 |
| Interval<T, 1>, fenv | 554 to 606 (-O2), 597 to 616 (-O3) | 617 to 618 (-O2), 566 to 592 (-O3) | 601 to 608 | 1260 to 1270 (-O2), 1280 to 1364 (-O3) |
| Interval<T, 1>, csr | 416 to 454 (-O2), 442 to 452 (-O3) | 542 to 567 (-O2), 511 to 541 (-O3) | 48.2 to 48.6 | 55.9 to 57 |
| Interval<T, 1>, fenv_loop | 16.1 to 16.9 (-O2), 12.7 to 13 (-O3) | 17.3 to 17.6 (-O2), 15.9 to 16.3 (-O3) | 46.3 to 46.5 (-O2), 44.4 to 46.7 (-O3) | 31.1 to 31.4 (-O2), 26.9 (-O3) |
| Interval<T, 2> | 466 to 509 (-O2), 492 to 521 (-O3) | 474 to 521 (-O2), 500 to 521 (-O3) | 1189 to 1211 | 844 to 850 |
| Ball<T, 1> | 26.7 to 27.9 | 27.6 to 28.9 (-O2), 25.8 to 28.1 (-O3) | 77.8 to 78.5 | 76 to 76.2 (-O2), 27.6 to 27.7 (-O3) |
| Ball<T, 2> | 64 to 69.8 (-O2), 68.6 to 71.4 (-O3) | 68.7 to 71.7 (-O2), 64.6 to 70 (-O3) | 147 to 149 | 144 to 145 |
| Expansion<T, 2>, a point | 49.6 to 54.3 (-O2), 53.2 to 54.2 (-O3) | 54.5 to 56.3 (-O2), 51 to 55.1 (-O3) | 139 to 140 | 135 to 136 |
| T, a point | 0.646 to 0.676 | 2.73 to 2.78 (-O2), 0.648 to 0.66 (-O3) | 4.26 to 4.35 (-O2), 0.83 to 0.835 (-O3) | 0.828 to 0.832 |

| Horner, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| tp: `Interval<T, 1>` over `Ball<T, 1>` | 4.62 to 4.67 (-O2), 4.40 to 4.61 (-O3) | 3.89 to 3.98 (-O2), 3.95 to 4.25 (-O3) | 3.20 to 3.30 | 2.39 (-O2), 6.56 to 6.59 (-O3) |
| tp: `Interval<T, 2>` over `Ball<T, 2>` | 7.27 to 7.30 (-O2), 7.05 to 7.60 (-O3) | 6.89 to 7.26 (-O2), 7.45 to 7.73 (-O3) | 8.02 to 8.14 | 5.84 to 5.86 |
| tp: `Ball<T, 2>` over `Expansion<T, 2>` | 1.29 to 1.32 (-O2), 1.29 to 1.34 (-O3) | 1.26 to 1.32 (-O2), 1.26 to 1.27 (-O3) | 1.06 to 1.07 | 1.07 |
| tp: `Interval<T, 1>`, fenv over Kairn | 4.48 to 4.82 (-O2), 4.65 to 5.07 (-O3) | 5.41 to 5.61 (-O2), 5.14 to 5.39 (-O3) | 2.33 to 2.40 (-O2), 2.40 to 2.42 (-O3) | 6.93 to 6.99 (-O2), 7.03 to 7.50 (-O3) |
| tp: `Interval<T, 1>`, Kairn over fenv_loop | 7.45 to 7.65 (-O2), 9.3 to 10.1 (-O3) | 6.36 to 6.49 (-O2), 6.83 to 6.86 (-O3) | 5.42 to 5.55 (-O2), 5.43 to 5.62 (-O3) | 5.79 to 5.84 (-O2), 6.75 to 6.77 (-O3) |
| lat: `Interval<T, 1>` over `Ball<T, 1>` | 5.01 to 5.04 | 4.11 to 4.29 (-O2), 4.08 to 4.42 (-O3) | 3.22 to 3.28 (-O2), 3.16 to 3.19 (-O3) | 2.49 to 2.51 |
| lat: `Interval<T, 2>` over `Ball<T, 2>` | 4.74 (-O2), 4.54 to 4.81 (-O3) | 4.30 to 4.54 (-O2), 4.76 to 5.03 (-O3) | 7.60 to 7.70 | 5.62 to 5.64 |

**Tightness.** The width of the enclosure of $p(X)$ over the width of the exact range, for 256
arguments in each of four regimes: a point ($X = [x, x]$; the width over $\lvert p(x)\rvert$
instead, the exact range being one point); a value known to a few units in its last place
(half-width $2^{-50}$ relative for `double`, $2^{-21}$ for `float`); the narrow sets of the timing;
and wide sets of half-width $1/32$, as a search has. Every enclosure is the same set of arguments:
`Interval<T, 1>` and `Interval<T, 2>` of the two bounds, `Ball<T, 1>(X)` of the interval of one
limb, and `Ball<T, 2>::from_interval`, whose center is the exact midpoint when $lo/2$ and $hi/2$
are numbers of `T` (that is the condition of its claim). The width of a ball is
its diameter $2r$. These numbers do not depend on the compiler: every configuration gives the same
ones, and every enclosure contained the exact range.

| Limbs | Regime | Type | Width over the reference: median, 90th percentile, max | Median width | Not contained |
|---|---|---|---|---|---:|
| double | point | `Interval<double, 1>` | 1.05e-14, 9.55e-14, 2.15e-11 (of \|p(x)\|) | 4e-15 | 0 |
| double | point | `Interval<double, 2>` | 1.45e-29, 1.01e-28, 2.03e-26 (of \|p(x)\|) | 4.35e-30 | 0 |
| double | point | `Ball<double, 1>` | 3.49e-14, 2.46e-13, 4.77e-11 (of \|p(x)\|) | 1.06e-14 | 0 |
| double | point | `Ball<double, 2>` | 1.36e-29, 9.64e-29, 1.87e-26 (of \|p(x)\|) | 4.13e-30 | 0 |
| double | ulp | `Interval<double, 1>` | 9.89, 64.2, 2.6e+03 (of the width of the exact range) | 3.98e-14 | 0 |
| double | ulp | `Interval<double, 2>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 3.31e-14 | 0 |
| double | ulp | `Ball<double, 1>` | 11.8, 79.5, 3.26e+03 (of the width of the exact range) | 4.68e-14 | 0 |
| double | ulp | `Ball<double, 2>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 3.31e-14 | 0 |
| double | narrow | `Interval<double, 1>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 3.66e-08 | 0 |
| double | narrow | `Interval<double, 2>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 3.66e-08 | 0 |
| double | narrow | `Ball<double, 1>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 3.66e-08 | 0 |
| double | narrow | `Ball<double, 2>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 3.66e-08 | 0 |
| double | wide | `Interval<double, 1>` | 9.38, 52.3, 147 (of the width of the exact range) | 2.99 | 0 |
| double | wide | `Interval<double, 2>` | 9.38, 52.3, 147 (of the width of the exact range) | 2.99 | 0 |
| double | wide | `Ball<double, 1>` | 10.5, 58.4, 162 (of the width of the exact range) | 3.61 | 0 |
| double | wide | `Ball<double, 2>` | 10.5, 58.4, 162 (of the width of the exact range) | 3.61 | 0 |
| float | point | `Interval<float, 1>` | 6.2e-06, 4.83e-05, 0.00799 (of \|p(x)\|) | 2.15e-06 | 0 |
| float | point | `Interval<float, 2>` | 4.17e-12, 3.04e-11, 5.93e-09 (of \|p(x)\|) | 1.23e-12 | 0 |
| float | point | `Ball<float, 1>` | 1.87e-05, 0.000132, 0.0256 (of \|p(x)\|) | 5.71e-06 | 0 |
| float | point | `Ball<float, 2>` | 3.93e-12, 2.78e-11, 5.4e-09 (of \|p(x)\|) | 1.19e-12 | 0 |
| float | ulp | `Interval<float, 1>` | 10.1, 65.2, 2.69e+03 (of the width of the exact range) | 2.08e-05 | 0 |
| float | ulp | `Interval<float, 2>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 1.78e-05 | 0 |
| float | ulp | `Ball<float, 1>` | 11.8, 79.5, 3.26e+03 (of the width of the exact range) | 2.52e-05 | 0 |
| float | ulp | `Ball<float, 2>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 1.78e-05 | 0 |
| float | narrow | `Interval<float, 1>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 0.00961 | 0 |
| float | narrow | `Interval<float, 2>` | 8.62, 56.7, 2.24e+03 (of the width of the exact range) | 0.0096 | 0 |
| float | narrow | `Ball<float, 1>` | 8.63, 56.8, 2.24e+03 (of the width of the exact range) | 0.00962 | 0 |
| float | narrow | `Ball<float, 2>` | 8.63, 56.7, 2.24e+03 (of the width of the exact range) | 0.00961 | 0 |
| float | wide | `Interval<float, 1>` | 9.38, 52.3, 147 (of the width of the exact range) | 2.99 | 0 |
| float | wide | `Interval<float, 2>` | 9.38, 52.3, 147 (of the width of the exact range) | 2.99 | 0 |
| float | wide | `Ball<float, 1>` | 10.5, 58.4, 162 (of the width of the exact range) | 3.61 | 0 |
| float | wide | `Ball<float, 2>` | 10.5, 58.4, 162 (of the width of the exact range) | 3.61 | 0 |

**Cost.** An evaluation on `Interval<double, 1>` takes 109 to 258 ns, on `Ball<double, 1>` 26 to 79
ns: the interval costs 3.2 to 4.9 times the ball (2.4 with Clang 18 at `-O2`, and 6.6 at `-O3`,
where Clang vectorizes the balls' loop across evaluations, 256-bit, its branches turned into
selects). With two limbs, 466 to 1 211 ns for the interval and 64 to 149 ns for the ball, 5.8 to
8.1 times; the ball of two limbs costs 1.06 to 1.34 times the evaluation of the same polynomial at
the midpoint in `Expansion<double, 2>`. Each of the eight steps is a product and a sum of
intervals, and the products take most of the time. The classical interval that changes the mode
around each operation takes 2.3 to 7.5 times as long as Kairn's with `fesetround` (556 to 1 364
ns), and on the M3 also with direct writes of `FPCR` (412 to 567 ns), but 0.19 to 0.31 times on
Zen 2 with direct writes of `MXCSR` (48 to 57 ns); the one that sets the mode once for the whole
loop is 5.4 to 10 times faster than Kairn (12 to 47 ns).

**Tightness.** Wherever the argument is wider than a few units in the last place, **the width is set
by the dependency problem, and intervals and balls agree**: for the narrow sets all four
enclosures are 8.6 times the exact range at the median (57 times at the 90th percentile, where an
argument lies near a critical point and the exact range is small), and for the wide sets the
intervals are 9.4 times and the balls 10.5 times it. Why they agree: to first order in the width of
the argument, both propagate widths by the same rule (a sum adds them, a product by a narrow set
multiplies them by magnitudes), so both give Horner's form the width of the argument times a sum of
magnitudes of its terms, while the exact range is that width times $\lvert p'(x)\rvert$, much
smaller where the terms cancel. **At a point, the arithmetic shows**: one limb gives
$1.0 \times 10^{-14}$ of $\lvert p(x)\rvert$ for the interval and $3.5 \times 10^{-14}$ for the ball
(the ball's radius covers each operation's error by its bound, the interval's bounds are the exact
roundings), and two limbs $1.4 \times 10^{-29}$ for both; at a few units in the last place the one
limb types are 15% (interval) and 37% (ball) wider than the two limb types, which are 8.6 times the
exact range there too. `float` gives the same ratios.

### 5. The additions to `Ball`

`lower_as<T>()` and `upper_as<T>()` (one and two limbs), `Ball<T, 2>::from_interval(lo, hi)`, the
narrowing `Ball<T, 1>(X)` of a ball of two limbs, and `half(X)` and `ldexp(X, n)`, exact when nothing
underflows, against the ordinary scaling of a ball by the same power of two (`X * 0.5`, `X * 2^n`,
the operator of Milestone 1, which rounds the radius up); and plain floors.

| Times (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/ball_bounds_1/op` | 1.87 to 1.95 | 1.64 to 1.71 | 3.65 to 3.67 | 4.41 to 4.44 |
| `m2/tp/ball_bounds_2/op` | 3 to 3.09 | 2.48 to 2.58 | 5.44 to 5.55 | 8.33 to 8.37 |
| `m2/tp/ball_from_interval_2/op` | 3.06 to 3.19 | 3.38 to 3.42 (-O2), 2.44 to 2.48 (-O3) | 11.8 to 11.9 (-O2), 6.65 to 6.7 (-O3) | 11.6 to 11.7 |
| `m2/tp/ball_narrow_2_1/op` | 0.746 to 0.778 | 0.68 to 0.709 | 1.48 | 2.75 to 2.77 |
| `m2/tp/ball_half_1/op` | 2 to 2.06 (-O2), 2.12 to 2.17 (-O3) | 1.58 to 1.65 | 3.46 to 3.51 | 3.69 to 3.7 |
| `m2/tp/ball_scale_half_1/op` | 0.705 to 0.732 | 0.651 to 0.679 | 1.15 to 1.16 | 1.08 to 1.09 |
| `m2/tp/ball_half_2/op` | 2.16 to 2.25 | 1.37 to 1.42 (-O2), 1.6 to 1.64 (-O3) | 4.46 to 4.5 | 4.15 to 4.17 |
| `m2/tp/ball_scale_half_2/op` | 0.998 to 1.04 | 0.988 to 1.03 | 2.73 to 2.75 | 1.94 to 1.96 |
| `m2/tp/ball_ldexp_2/op` | 3.73 to 3.8 (-O2), 3.58 to 3.81 (-O3) | 2.33 to 2.4 | 6.56 to 6.72 | 8.14 to 8.19 |

| The additions to Ball | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `lower_as`, `upper_as`, one limb, over c - r, c + r | 5.52 to 5.62 | 5.70 to 5.79 | 10.8 to 11.1 | 6.98 to 7.01 |
| `lower_as`, `upper_as`, two limbs, over c0 - r, c0 + r | 8.97 to 9.22 (-O2), 8.92 to 9.09 (-O3) | 8.46 to 8.80 (-O2), 8.46 to 8.61 (-O3) | 8.52 to 8.53 (-O2), 15.9 to 16.0 (-O3) | 9.00 to 9.05 |
| `from_interval` over (l + h)/2, (h - l)/2 | 10.1 to 10.6 (-O2), 10.4 to 10.6 (-O3) | 11.0 to 11.2 (-O2), 8.12 to 8.22 (-O3) | 34.8 to 34.9 (-O2), 19.6 to 19.7 (-O3) | 16.8 |
| `Ball<T, 1>(X)` of two limbs over c0, r + abs(c1) | 2.55 to 2.56 | 2.32 to 2.36 | 1.83 to 1.85 | 4.30 to 4.32 |
| `half(X)` over `X * 0.5`, one limb, loop | 2.80 to 2.91 (-O2), 2.97 to 2.98 (-O3) | 2.37 to 2.44 (-O2), 2.43 to 2.45 (-O3) | 2.99 to 3.03 | 3.40 |
| `half(X)` over `X * 0.5`, two limbs, loop | 2.14 to 2.17 | 1.37 to 1.39 (-O2), 1.62 to 1.63 (-O3) | 1.63 to 1.64 | 2.12 to 2.14 |
| `ldexp(X, n)` over `X * 2^n`, one limb, loop | 4.45 to 4.64 (-O2), 4.55 to 4.84 (-O3) | 3.07 to 3.21 (-O2), 3.15 to 3.16 (-O3) | 4.23 to 4.27 | 4.84 to 4.86 |
| `ldexp(X, n)` over `X * 2^n`, two limbs, loop | 3.56 to 3.60 (-O2), 3.34 to 3.57 (-O3) | 2.10 to 2.16 (-O2), 2.16 to 2.18 (-O3) | 2.55 to 2.61 | 2.74 |
| `ldexp(X, +-1)` over `X * 2^+-1`, one limb, chain | 2.43 to 2.61 (-O2), 2.40 to 2.48 (-O3) | 0.66 to 0.67 (-O2), 0.66 to 0.72 (-O3) | 1.08 to 1.11 | 2.20 to 2.21 |
| `ldexp(X, +-1)` over `X * 2^+-1`, two limbs, chain | 1.91 to 2.04 (-O2), 1.91 (-O3) | 0.77 to 0.81 | 1.17 to 1.18 | 1.80 to 1.81 |

- **`lower_as` and `upper_as`** of a ball of one limb, the exact roundings $\mathrm{RD}(c - r)$ and
  $\mathrm{RU}(c + r)$, cost 1.6 to 4.4 ns for the pair, 5.5 to 11 times $c - r$ and $c + r$ in plain
  arithmetic; of a ball of two limbs, the center rounded to `T` and then the radius, 2.5 to 8.4 ns.
- **`Ball<T, 2>::from_interval(lo, hi)`**, the ball whose center is the exact midpoint when both
  halvings are exact, costs 2.4 to 11.9 ns, 8 to 35 times the plain midpoint and half-width;
  **the narrowing** `Ball<T, 1>(X)` of a ball of two limbs 0.68 to 2.8 ns, 1.8 to 4.3 times its
  plain form.
- **`half(X)` costs 2.4 to 3.4 times `X * 0.5` for one limb and 1.4 to 2.2 times for two**, and
  `ldexp(X, n)` 3.1 to 4.9 and 2.1 to 3.6 times `X * 2^n`, in a loop. The exact scaling tests whether
  nothing underflowed and steps the radius twice otherwise, which the ordinary scaling, a product of
  the center and a radius rounded up, does not ([finding 2](#what-the-machine-code-shows)); `ldexp`
  adds the clamping of `n` and the making of $2^n$ (1.6 ns on the M3 over the kernel alone). In a
  chain of scalings by $2^{\pm 1}$ it is 1.1 to 2.6 times the ordinary scaling, except with GCC 16,
  where it is faster (0.66 to 0.81; not examined).
  What it buys is a radius that does not grow; what it costs in a loop is this.

### 6. `kairn::rational`

At run time, one call of `rational<Expansion<double, 1>>(num, den)` and of
`rational<Expansion<double, 2>>(num, den)` per element, on 256 fractions with small terms
($\lvert num\rvert \le 1000$, $1 \le \lvert den\rvert \le 1000$) and with random 64-bit terms;
`is_rational_result`, the check that a build with `KAIRN_CHECKS` makes after each call; and one
`double` division for scale. Every result was accepted by `is_rational_result` before the timing.

| kairn::rational, ns per call | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `rational<Expansion<T, 1>>`, small terms | 114 to 119 | 94.8 to 98.5 | 369 to 376 | 348 to 352 |
| `rational<Expansion<T, 1>>`, 64-bit terms | 115 to 119 (-O2), 119 to 121 (-O3) | 98.3 to 102 | 437 to 444 | 429 to 435 |
| `rational<Expansion<T, 2>>`, small terms | 176 to 181 | 142 to 148 (-O2), 147 to 149 (-O3) | 568 to 592 | 597 to 610 |
| `rational<Expansion<T, 2>>`, 64-bit terms | 172 to 188 (-O2), 186 to 191 (-O3) | 148 to 155 | 666 to 688 | 704 to 717 |
| `is_rational_result`, two limbs, 64-bit terms | 57.9 to 59 (-O2), 55.5 to 56.5 (-O3) | 83.6 to 86.6 (-O2), 48.3 to 49 (-O3) | 219 to 222 (-O2), 151 to 153 (-O3) | 158 to 161 |
| `T(num) / T(den)`, for scale | 0.165 to 0.169 | 0.155 to 0.162 | 1.52 to 1.54 | 0.764 to 0.799 |

At compile time, a translation unit with $N$ `constexpr` constants of distinct random 64-bit terms,
for $N$ = 10, 100 and 1000, with the check of every constant in constant evaluation
(`KAIRN_RATIONAL_CHECK`, 1 by default) and without it, against the same unit without a constant
(`bench/rational_cost.py compile`, five compilations of each, the median): seconds, and what one
constant adds, in milliseconds.

| Compiler | Include only, s | Constants | `Expansion<double, 1>`: s, ms per constant (check 0; check 1) | `Expansion<double, 2>`: s, ms per constant (check 0; check 1) |
|---|---:|---:|---|---|
| linux-clang (Ubuntu clang version 18.1.3 (1ubuntu1)) | 0.48 | 10 | 0.50, 1.34; 0.51, 2.23 | 0.50, 1.67; 0.52, 3.27 |
| linux-clang (Ubuntu clang version 18.1.3 (1ubuntu1)) | 0.48 | 100 | 0.56, 0.74; 0.65, 1.66 | 0.58, 1.01; 0.73, 2.52 |
| linux-clang (Ubuntu clang version 18.1.3 (1ubuntu1)) | 0.48 | 1000 | 1.16, 0.68; 2.15, 1.67 | 1.46, 0.98; 2.92, 2.43 |
| linux-gcc (g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0) | 0.34 | 10 | 0.34, -0.53; 0.37, 2.75 | 0.33, -1.51; 0.33, -0.93 |
| linux-gcc (g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0) | 0.34 | 100 | 0.35, 0.08; 0.40, 0.55 | 0.37, 0.27; 0.43, 0.91 |
| linux-gcc (g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0) | 0.34 | 1000 | 0.71, 0.37; 1.10, 0.75 | 0.92, 0.57; 1.53, 1.18 |
| mac-appleclang (Apple clang version 21.0.0 (clang-2100.4.1.1)) | 0.11 | 10 | 0.12, 0.56; 0.12, 0.78 | 0.11, 0.36; 0.12, 0.98 |
| mac-appleclang (Apple clang version 21.0.0 (clang-2100.4.1.1)) | 0.11 | 100 | 0.12, 0.15; 0.15, 0.41 | 0.14, 0.30; 0.18, 0.69 |
| mac-appleclang (Apple clang version 21.0.0 (clang-2100.4.1.1)) | 0.11 | 1000 | 0.27, 0.16; 0.50, 0.39 | 0.34, 0.23; 0.71, 0.60 |
| mac-gcc16 (g++-16 (Homebrew GCC 16.2.0) 16.2.0) | 0.22 | 10 | 0.22, -0.06; 0.23, 0.58 | 0.22, 0.35; 0.23, 0.87 |
| mac-gcc16 (g++-16 (Homebrew GCC 16.2.0) 16.2.0) | 0.22 | 100 | 0.24, 0.18; 0.25, 0.35 | 0.25, 0.30; 0.28, 0.61 |
| mac-gcc16 (g++-16 (Homebrew GCC 16.2.0) 16.2.0) | 0.22 | 1000 | 0.44, 0.22; 0.63, 0.41 | 0.55, 0.33; 0.85, 0.63 |

- **At run time a call costs 95 to 125 ns on the M3 for one limb and 142 to 195 ns for two; 348 to
  444 and 568 to 717 ns on Zen 2.** Large terms cost 3 to 18% more than small ones. That is several
  hundred times a division of `double` (0.16 to 1.5 ns), the price of an exact result by integer
  arithmetic only (the quotient one bit at a time, as [the design](../design/milestone2.md#constants-at-compile-time)
  describes); `rational` is for constants, which a program makes once. The check
  `is_rational_result`, which a build with `KAIRN_CHECKS` adds after every call, costs another 48 to
  222 ns.
- **At compile time** a constant of two limbs adds 0.2 (Apple clang) to 1.0 ms (Clang 18) without
  the check and 0.6 to 2.4 ms with it, the default (GCC 16: 0.3 and 0.6 ms; GCC 13: 0.6 and 1.2);
  one of one limb about two thirds of that. A unit with 1 000 constants of two limbs compiles in
  0.7 s (Apple clang) to 2.9 s (Clang 18) with the check, against 0.1 to 0.5 s for the unit without
  constants. With 10 constants the difference from that unit is within the noise of the
  compilations (a few tens of milliseconds; hence the negative values of the table).

### 7. The settings of `KAIRN_ENCLOSURE_CODE`

[Compile times and other costs, Milestone 2](costs-milestone2.md) measured the three settings on
units of `Ball<double, 2>` on the M3. Here the unit is one of intervals and balls, in one function:
`enclosure_costs.py --kind mixed`, $N$ operations of `Ball<double, 2>`, `Interval<double, 1>` and
`Interval<double, 2>` in turn (`+`, `*`, `-` of each and the scaling of a ball), each on one of the
eight values of its type computed last and one of eight inputs, each result stored; and the same
with intervals of two limbs only (`--kind interval2`), whose product is the one kernel not forced
inline in any setting. "The calls alone" is the same unit without Kairn, the types structures of
`double`s and the operations functions declared only. Each unit is compiled three times (once for
$N$ = 10 000, and with GCC 16 at `-O2` only), with a limit of an hour; the compile time is the
median of the compiler's processor time. The object of a compilation is linked with a driver (and,
external, with the definitions) and run: the minimum over 21 (Zen 2) or 41 (M3) samples of about
4 ms of the time per operation of one call of the unit, inputs near 1, so that every value stays
a finite enclosure; most units were compiled and run once or twice more, for the spread of the
run times (the tables say where a cell is one run). Nothing else changes between the settings: the three compute the same bits
([config.hpp](https://github.com/danielepanozzo/kairn/blob/main/include/kairn/config.hpp)).

| mixed: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 0.39; 0.39 | 1.24; 1.34 | 3.51; 3.66 | 1.05; 1.05 |
| 100, outlined | 0.19; 0.20 | 0.39; 0.41 | 0.65; 0.68 | 0.64; 0.64 |
| 100, external | 0.12; 0.14 | 0.25; 0.26 | 0.41; 0.41 | 0.53; 0.53 |
| 100, calls | 0.04; 0.04 | 0.11; 0.12 | 0.09; 0.09 | 0.08; 0.08 |
| 1000, inline | 3.40; 3.42 | 11.1; 15.6 | 129; 140 | 8.49; 8.49 |
| 1000, outlined | 0.39; 0.39 | 1.30; 1.84 | 1.45; 1.44 | 1.12; 1.12 |
| 1000, external | 0.32; 0.33 | 0.98; 1.53 | 1.12; 1.16 | 1.01; 1.00 |
| 1000, calls | 0.21; 0.22 | 0.73; 1.20 | 0.68; 0.70 | 0.48; 0.47 |
| 10000, inline | 85.1; 84.3 | 434; – | stopped at 3600; stopped at 3600 | 524; 566 |
| 10000, outlined | 4.59; 4.84 | 23.7; – | 22.2; 24.1 | 14.0; 14.1 |
| 10000, external | 4.56; 4.72 | 25.1; – | 26.7; 27.5 | 14.0; 14.8 |
| 10000, calls | 4.29; 4.29 | 14.4; – | 20.7; 22.6 | 12.5; 12.5 |

| mixed: peak memory, MB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 79; 79 | 216; 219 | 152; 150 | 122; 121 |
| 100, outlined | 66; 66 | 99; 100 | 85; 85 | 122; 122 |
| 100, external | 59; 59 | 88; 88 | 76; 76 | 118; 118 |
| 100, calls | 38; 38 | 37; 37 | 32; 31 | 96; 96 |
| 1000, inline | 260; 260 | 941; 989 | 755; 756 | 223; 223 |
| 1000, outlined | 89; 89 | 183; 186 | 124; 125 | 128; 128 |
| 1000, external | 83; 83 | 170; 173 | 117; 116 | 125; 125 |
| 1000, calls | 64; 64 | 112; 114 | 70; 70 | 110; 110 |
| 10000, inline | 2257; 2263 | 12777; – |  | 5045; 5044 |
| 10000, outlined | 376; 388 | 1217; – | 544; 544 | 256; 258 |
| 10000, external | 368; 372 | 1212; – | 556; 556 | 256; 256 |
| 10000, calls | 330; 330 | 949; – | 471; 472 | 244; 244 |

| mixed: object, KB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 40; 40 | 49; 49 | 79; 79 | 67; 67 |
| 100, outlined | 13; 13 | 15; 15 | 26; 26 | 27; 27 |
| 100, external | 5; 5 | 7; 7 | 11; 11 | 10; 10 |
| 100, calls | 5; 5 | 6; 6 | 10; 10 | 9; 9 |
| 1000, inline | 358; 358 | 461; 465 | 779; 779 | 604; 607 |
| 1000, outlined | 57; 57 | 70; 69 | 96; 96 | 95; 95 |
| 1000, external | 50; 50 | 62; 61 | 80; 80 | 78; 78 |
| 1000, calls | 50; 50 | 54; 54 | 79; 79 | 78; 78 |
| 10000, inline | 3512; 3512 | 4767; – |  | 5876; 5894 |
| 10000, outlined | 485; 485 | 921; – | 789; 789 | 776; 777 |
| 10000, external | 478; 478 | 913; – | 773; 773 | 760; 760 |
| 10000, calls | 477; 477 | 812; – | 772; 772 | 759; 759 |

| mixed: run time of the unit, ns per operation (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 6.41 to 7.57; 6.37 to 7.93 | 5.87 to 6.03; 5.79 to 5.96 | 18.7 to 20.9; 18.9 to 19 | 16.1 to 16.2; 16.1 to 16.3 |
| 100, outlined | 6.56 to 8.71; 6.53 to 8.17 | 6.55 to 6.68; 6.57 to 6.58 | 20.2; 20 to 20.3 | 17.4 to 17.5; 17.4 to 17.5 |
| 100, external | 6.8 to 9.1; 6.58 to 8.25 | 6.55 to 6.69; 6.55 to 6.7 | 20.2; 20 to 20.2 | 17.4 to 17.5; 17.6 |
| 1000, inline | 6.37 to 7.36; 6.26 to 7.75 | 6.91 to 7.33; 7.04 to 7.22 | 20.1 to 21.2; 20.2 to 20.8 | 15.9 to 16; 16.1 to 16.2 |
| 1000, outlined | 6.75 to 8.27; 6.67 to 8.26 | 6.15 to 6.29; 6.19 to 6.32 | 19.2 to 19.6; 19.2 to 19.4 | 17.5; 17.5 |
| 1000, external | 6.58 to 8.36; 6.69 to 7.93 | 6.15 to 6.43; 6.19 to 6.21 | 19.3 to 19.5; 19.3 to 19.5 | 17.5; 17.5 to 17.6 |
| 10000, inline | 7.68 (one run); 6.43 (one run) | 8.9 (one run); – |  | 39.3 (one run); 38.9 (one run) |
| 10000, outlined | 6.82 (one run); 6.82 (one run) | 6.63 (one run); – | 22.2 (one run); 22.7 (one run) | 19.5 (one run); 19.8 (one run) |
| 10000, external | 6.86 (one run); 6.86 (one run) | 10.1 (one run); – | 23 (one run); 22.3 (one run) | 20.8 (one run); 19.4 (one run) |

- **Compile time and memory: inline is what large functions cannot afford, and with GCC 13 not
  even medium ones.** For 1 000 operations in one function, the inline unit takes 3.4 s of
  processor time with Apple clang, 8.5 s with Clang 18, 11 to 16 s with GCC 16 and 129 to 140 s
  with GCC 13; outlined or external, 0.3 to 1.8 s. For 10 000 operations, Apple clang takes 84 to
  85 s and 2.3 GB inline, Clang 18 524 to 566 s and 5.0 GB, GCC 16 434 s and 12.8 GB (`-O2`, the
  one level measured), and GCC 13 had not finished after an hour at either level, where the
  measurement stops it (a second compilation at `-O2` was stopped at 59 minutes); outlined or
  external, 4.6 to 4.8 s, 14 to 15 s, 24 to 25 s and 22 to 28 s, within 7 to 30% of the calls
  alone, and 65 to 75% with GCC 16. External compiles 10 to 25% faster than outlined at 1 000
  operations, since the file does not compile the operations' bodies, and no faster at 10 000,
  where the calls take most of the time; the file of the definitions, which a program compiles
  once, takes 0.2 s (Apple clang) to 0.9 s (GCC 13). The unit of intervals of two limbs, whose
  product is a call in every setting, compiles 9 to 15 times faster outlined at 1 000 operations
  with the Clangs and GCC 16 (Clang 18: 1.0 s against 9.2; Apple clang 0.37 against 5.1; GCC 16 1.5
  to 2.2 against 15 to 24), and 220 times faster with GCC 13 (1.1 s against 234 to 244).
- **Object size.** Inline, 0.36 (Apple clang) to 0.78 MB (GCC 13) per 1 000 operations, 3.5 to 5.9
  MB at 10 000; outlined or external, about what the calls alone take (0.05 to 0.08 MB per 1 000),
  plus the operations' bodies once in the outlined object.
- **Run time of the same unit, up to 1 000 operations: within 15%.** Inline is a little faster with
  Clang 18 (16 ns per operation against 17.5) and no faster with GCC 13 (19 to 21 against 19 to
  20); on the M3, Apple clang's runs vary by up to 30% (6.3 to 7.9 ns inline, 6.5 to 9.1 outlined
  or external), and GCC 16's inline unit is faster at 100 operations (5.8 to 6.0 against 6.6 to
  6.7 ns) and slower at 1 000 (6.9 to 7.3 against 6.2 to 6.4).
- **With 10 000 operations, inline is twice as slow as outlined on Zen 2**: 39 ns per operation
  against 19.5 to 20.8 with Clang 18, at both levels, each compiled and run on an idle core complex
  (GCC 13's outlined and external units take 22 to 23 ns). The 5.9 MB of straight-line code is
  fetched from the L3 for every call. On the M3 the difference is smaller: Apple clang 6.4 to 7.7
  ns inline against 6.8 to 6.9, GCC 16 8.9 against 6.6 outlined and 10.1 external (one run each).
- **On Zen 2, once a unit's code is larger than the 512 KB L2 of a core, its run time depends on what
  else runs on the cores that share its L3.** The inline unit of intervals of two limbs at 1 000
  operations, 615 KB (Clang 18) and 992 KB (GCC 13), took 38 or 83 ns per operation in different
  runs with Clang 18 and 50 to 101 ns with GCC 13, where its outlined and external units (69 to 78
  KB) took 38 to 39 and 44 to 55. One repeat showed the cause directly: the outlined unit of 10 000
  operations of GCC 13 took 52 ns per operation while a compilation of this measurement ran on
  another core of the same complex, and 22.7 ns when the complex was idle; that repeat is set
  aside. Other repeated compilations and runs of one unit agree within 2% in most cells. The first
  runs of Linux, made on cores of the busier socket during the timed compilations, varied more and
  are in [Tables](#tables) only.

And the harness itself, every translation unit built in each setting: the public operations of
this page, outlined or external over inline, in the same loops and chains (two runs of each
program, one with GCC 16; the control is a generated kernel called directly, which no setting
changes).

| Outlined over inline | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop | 1.08 (-O2), 1.08 (-O3) | 1.99 (-O2), 2.04 (-O3) | 2.78 (-O2), 2.80 (-O3) | 1.07 (-O2), 1.08 (-O3) |
| `interval_mul_1`, loop | 1.09 (-O2), 1.05 (-O3) | 1.10 (-O2), 1.09 (-O3) | 2.15 (-O2), 2.16 (-O3) | 0.94 (-O2), 0.94 (-O3) |
| `interval_add_2`, loop | 0.91 (-O2), 0.99 (-O3) | 1.32 (-O2), 1.55 (-O3) | 1.10 (-O2), 1.08 (-O3) | 0.99 (-O2), 1.00 (-O3) |
| `interval_mul_2`, loop | 0.94 (-O2), 1.03 (-O3) | 1.03 (-O2), 1.03 (-O3) | 1.06 (-O2), 1.05 (-O3) | 0.99 (-O2), 1.00 (-O3) |
| `ball_add_2`, loop | 1.05 (-O2), 1.07 (-O3) | 1.05 (-O2), 1.13 (-O3) | 2.24 (-O2), 2.23 (-O3) | 1.91 (-O2), 2.99 (-O3) |
| `ball_mul_2`, loop | 1.11 (-O2), 1.12 (-O3) | 1.20 (-O2), 1.27 (-O3) | 2.45 (-O2), 2.44 (-O3) | 1.73 (-O2), 3.76 (-O3) |
| `interval_add_1`, chain | 1.56 (-O2), 1.64 (-O3) | 2.77 (-O2), 2.78 (-O3) | 1.95 (-O2), 1.96 (-O3) | 1.28 (-O2), 1.29 (-O3) |
| `interval_mul_1`, chain | 1.28 (-O2), 1.29 (-O3) | 1.72 (-O2), 1.70 (-O3) | 1.33 (-O2), 1.32 (-O3) | 1.17 (-O2), 1.17 (-O3) |
| `interval_mul_2`, chain | 1.01 (-O2), 1.09 (-O3) | 1.11 (-O2), 1.13 (-O3) | 1.21 (-O2), 1.21 (-O3) | 1.13 (-O2), 1.12 (-O3) |
| Horner, `Interval<T, 1>` | 1.32 (-O2), 1.48 (-O3) | 1.74 (-O2), 1.74 (-O3) | 1.88 (-O2), 1.59 (-O3) | 1.37 (-O2), 1.37 (-O3) |
| Horner, `Interval<T, 2>` | 1.09 (-O2), 1.13 (-O3) | 1.40 (-O2), 1.19 (-O3) | 1.10 (-O2), 1.08 (-O3) | 1.11 (-O2), 1.11 (-O3) |
| Horner, `Ball<T, 2>` | 1.54 (-O2), 1.54 (-O3) | 1.65 (-O2), 1.73 (-O3) | 1.84 (-O2), 1.84 (-O3) | 1.70 (-O2), 1.38 (-O3) |
| control: the kernel `interval_mul_1`, loop | 1.00 (-O2), 1.04 (-O3) | 0.98 (-O2), 1.00 (-O3) | 0.98 (-O2), 0.98 (-O3) | 0.99 (-O2), 0.99 (-O3) |

- **With Apple clang each operation becomes a call that costs little in a loop** (0.91 to 1.12 times
  inline outlined, up to 1.22 external, as
  [Compile times and other costs, Milestone 2](costs-milestone2.md#2-run-time) found for balls) and
  1.3 to 1.7 times in a chain of intervals of one limb; the product of two limbs was a call already
  (0.94 to 1.09).
- **Where the inline loop was vectorized, a loop of calls costs 2 to 4 times as much**: on Zen 2 the
  loops of balls of two limbs, and with GCC 13 those of intervals of one limb, are vectorized
  (256-bit), and a loop of calls is not (balls 1.7 to 3.8 times inline, GCC 13's intervals of one
  limb 2.2 to 2.8 times); on the M3, GCC 16's loop of sums of intervals of one limb (128-bit, 2.0
  times). Intervals of two limbs, whose product is a call in every setting, change by 0 to 10% on
  Zen 2 and up to 55% with GCC 16. Chains take 1.1 to 2.8 times as long, a Horner evaluation 1.1
  to 1.9 times.
- **External costs about what outlined costs** (within 15%; a loop of sums of intervals of one limb
  with Apple clang, 1.22 against 1.08).
- The control, a generated kernel called directly, takes the same time in every program (0.93 to
  1.04; GCC 16's settings were run once, the others twice).

| External over inline | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop | 1.22 (-O2), 1.19 (-O3) | 1.85 (-O2), 2.05 (-O3) | 2.82 (-O2), 2.84 (-O3) | 1.06 (-O2), 1.08 (-O3) |
| `interval_mul_1`, loop | 1.06 (-O2), 1.04 (-O3) | 1.10 (-O2), 1.09 (-O3) | 2.20 (-O2), 2.19 (-O3) | 0.94 (-O2), 0.94 (-O3) |
| `interval_add_2`, loop | 1.00 (-O2), 1.00 (-O3) | 1.29 (-O2), 1.23 (-O3) | 1.09 (-O2), 1.10 (-O3) | 0.99 (-O2), 0.99 (-O3) |
| `interval_mul_2`, loop | 1.00 (-O2), 0.94 (-O3) | 1.02 (-O2), 1.03 (-O3) | 1.06 (-O2), 1.07 (-O3) | 0.99 (-O2), 1.00 (-O3) |
| `ball_add_2`, loop | 1.09 (-O2), 1.09 (-O3) | 1.06 (-O2), 1.13 (-O3) | 2.26 (-O2), 2.26 (-O3) | 1.93 (-O2), 2.99 (-O3) |
| `ball_mul_2`, loop | 1.19 (-O2), 1.18 (-O3) | 1.20 (-O2), 1.27 (-O3) | 2.47 (-O2), 2.48 (-O3) | 1.74 (-O2), 3.77 (-O3) |
| `interval_add_1`, chain | 1.67 (-O2), 1.61 (-O3) | 2.48 (-O2), 2.56 (-O3) | 1.98 (-O2), 1.99 (-O3) | 1.28 (-O2), 1.28 (-O3) |
| `interval_mul_1`, chain | 1.37 (-O2), 1.27 (-O3) | 1.62 (-O2), 1.61 (-O3) | 1.35 (-O2), 1.34 (-O3) | 1.16 (-O2), 1.15 (-O3) |
| `interval_mul_2`, chain | 1.08 (-O2), 1.01 (-O3) | 1.11 (-O2), 1.13 (-O3) | 1.22 (-O2), 1.21 (-O3) | 1.13 (-O2), 1.12 (-O3) |
| Horner, `Interval<T, 1>` | 1.41 (-O2), 1.39 (-O3) | 1.58 (-O2), 1.56 (-O3) | 1.89 (-O2), 1.92 (-O3) | 1.36 (-O2), 1.36 (-O3) |
| Horner, `Interval<T, 2>` | 1.10 (-O2), 1.04 (-O3) | 1.24 (-O2), 1.27 (-O3) | 1.11 (-O2), 1.12 (-O3) | 1.10 (-O2), 1.11 (-O3) |
| Horner, `Ball<T, 2>` | 1.54 (-O2), 1.44 (-O3) | 1.65 (-O2), 1.77 (-O3) | 1.86 (-O2), 1.86 (-O3) | 1.37 (-O2), 1.37 (-O3) |
| control: the kernel `interval_mul_1`, loop | 1.00 (-O2), 1.02 (-O3) | 0.93 (-O2), 1.00 (-O3) | 0.99 (-O2), 1.00 (-O3) | 0.99 (-O2), 0.98 (-O3) |

### Packed code and `float` limbs

| Packed code (binary64) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add_down_1`: packed over scalar | 0.99 to 1.03 | 0.90 to 0.93 | 0.56 | 0.63 to 0.64 |
| `add_up_1`: packed over scalar | 0.95 to 0.97 | 0.85 to 0.88 | 0.53 | 0.47 |
| `mul_down_1`: packed over scalar | 1.07 to 1.10 | 1.06 to 1.10 | 0.52 | 0.66 |
| `mul_up_1`: packed over scalar | 1.01 to 1.05 | 1.02 to 1.05 | 0.51 | 0.51 |
| `next_up`: packed over scalar | 1.37 to 1.40 | 0.98 to 1.01 | 0.53 | 0.40 |
| `interval_add_1`: packed over scalar | 0.82 to 0.85 | 0.93 to 0.95 | 0.54 | 0.48 |
| `interval_mul_1`: packed over scalar | 0.82 to 0.84 | 0.61 to 0.63 (-O2), 0.68 to 0.69 (-O3) | 0.50 | 0.48 to 0.51 |
| `interval_add_2`: packed over scalar | 0.65 | 0.73 to 0.74 (-O2), 0.67 (-O3) | 0.30 | 0.60 to 0.61 |
| `interval_mul_2`: packed over scalar | 0.57 to 0.58 | 0.59 to 0.60 (-O2), 0.51 (-O3) | 0.29 | 0.26 |
| `ball_add_1`: packed over scalar | 0.76 to 0.77 | 0.84 to 0.89 | 0.83 to 0.85 | 0.99 to 1.00 |
| `ball_mul_1`: packed over scalar | 0.75 to 0.76 | 0.88 to 0.93 | 0.87 to 0.88 | 1.00 |
| `ball_add_2`: packed over scalar | 0.77 to 0.78 | 0.65 to 0.69 | 0.89 to 0.90 | 0.99 to 1.00 |
| `ball_mul_2`: packed over scalar | 0.82 to 0.83 | 0.70 to 0.73 | 0.90 | 1.00 to 1.01 |
| `add_down_1`: packed over packed fenv_loop | 2.36 to 2.43 | 2.65 to 2.73 (-O2), 2.67 to 2.70 (-O3) | 0.88 (-O2), 0.87 to 1.06 (-O3) | 0.64 to 0.65 |
| `mul_down_1`: packed over packed fenv_loop | 3.45 to 3.54 | 3.40 to 3.49 | 0.83 to 0.84 | 0.80 |
| `interval_add_1`: packed over packed fenv_loop | 3.03 (-O2), 3.01 to 3.13 (-O3) | 2.81 to 2.97 (-O2), 2.90 to 2.95 (-O3) | 1.56 to 1.58 | 1.19 to 1.21 |
| `interval_mul_1`: packed over packed fenv_loop | 7.23 to 7.27 | 6.69 to 6.99 (-O2), 7.61 to 7.70 (-O3) | 3.57 to 3.59 | 3.26 to 3.29 |
| `interval_add_1`: packed over packed `ball_add_1` | 2.58 to 2.63 (-O2), 2.57 to 2.67 (-O3) | 3.17 to 3.23 | 2.61 to 2.62 | 2.34 to 2.36 |
| `interval_mul_1`: packed over packed `ball_mul_1` | 7.15 to 7.29 | 7.80 to 8.08 (-O2), 8.86 to 8.91 (-O3) | 5.18 to 5.22 | 5.31 to 5.33 |
| `interval_add_2`: packed over packed `ball_add_2` | 3.47 to 3.55 | 3.75 to 3.86 (-O2), 3.86 to 3.88 (-O3) | 3.88 to 3.90 | 3.39 to 3.43 |
| `interval_mul_2`: packed over packed `ball_mul_2` | 14.0 to 14.3 | 16.3 to 16.5 (-O2), 14.0 to 14.1 (-O3) | 16.0 to 16.2 | 14.0 to 14.2 |
| `add_down_1`: packed over packed plain addition | 3.75 to 3.79 | 4.15 to 4.26 | 4.87 to 4.89 | 3.65 to 3.66 |
| `interval_add_1`: packed over packed plain addition | 10.0 to 10.1 | 9.18 to 9.54 (-O2), 9.48 to 9.49 (-O3) | 10.6 to 10.7 | 8.14 to 8.18 |

- **Packed** (`avx2.hpp`, `neon.hpp`, binary64, one interval or ball per lane, against the same
  generated kernels in scalar loops on the same arrays): on Zen 2, with four lanes, the packed
  interval kernels take 0.26 to 0.6 of the scalar time; on the M3, with two, 0.51 to 0.95, and some
  packed blocks are no faster than the scalar loops, which the compilers vectorize at the same width
  ([finding 4](#what-the-machine-code-shows)). A packed interval product costs 4.3 to 5.6 ns per
  interval, 5.2 to 8.9 times a packed ball product; the classical packed product under one mode set
  around the loop 0.72 to 1.33 ns, 3.3 to 7.7 times faster than Kairn's, and the classical packed sum
  1.2 to 3.1 times faster. That is the price of the steps in packed code, about ten integer
  operations each, which [Interval kernels](../design/milestone2.md#one-limb) foresaw.
- **`float` limbs** cost about what `double` limbs cost in scalar code (0.83 to 1.08 for the
  intervals and balls of two limbs and for Horner), and half where the compiler vectorizes a loop
  with twice the lanes (0.48 to 0.52 for the directed blocks, and the loops of intervals of one limb
  with GCC); with Clang 18 some `float` loops take 1.1 to 2.8 times the `double` ones (Milestone 1
  traced the same pattern to Clang keeping a pair of `float` limbs in one register; not re-examined
  here). The [`float` table](#float-limbs) has them.

## What the machine code shows

The loops of the timed functions were disassembled (`objdump`) on every configuration and
summarized by `bench/asm_summary.py` (the summaries are stored next to the measurements,
`asm-*.json`). What a user would not expect from the documentation:

1. **`midpoint()` and `radius()` of an `Interval<T, 1>` compute their kernel twice, each through a
   call**, with Apple clang and Clang 18 at both levels and with GCC at `-O2`: both call the private
   member `mid_rad`, which runs `interval_mid_rad_1`, and the compilers do not inline it (it is
   `constexpr` but not forced inline, and the kernel inlined into it makes it about a hundred
   instructions). The loop of `kb_m2_64_tp_interval_midrad_1__op` holds two calls of
   `Interval<double, 1>::mid_rad`. A program that wants both pays two kernels and two calls: 6.4
   to 17.8 ns, 2.1 to 3.2 times the kernel alone. GCC at `-O3` inlines it and computes the kernel
   once (1.0 to 1.3 times the kernel's time). The conversion `Ball<T, 1>(X)`, which runs the same
   listing with two selects more, is likewise a call (`Ball<double, 1>::Ball(const Interval&)`)
   wherever `mid_rad` is one.
   `include/kairn/config.hpp` says that these functions stay inline in every setting; they are
   inline functions, and the compilers choose to call them. Not changed here: the library is not
   this page's to change.
2. **`half(X)` and `ldexp(X, n)` of a ball cost 1.4 to 4.9 times the ordinary scaling by the same
   power of two.** The exact scaling (`ball_mul_pow2_k_full`) tests whether the scaled center and radius are exact
   and takes two steps of the radius otherwise, with its fix-up: 52 to 65 instructions in the loop
   of one limb against 22 to 36 for `ball_scale_1_full` (Apple clang, GCC 13). A program that halves
   for speed should know that it halves for exactness.
3. **`flatten` inlines `interval_mul_2` with GCC and not with Clang.** With GCC 13 and GCC 16 the
   function compiled with `__attribute__((flatten))` has the product's body in its loop; with Apple
   clang and Clang 18 the loop still calls `kairn::gen::interval_mul_2`, so their `flat` variants
   are the called product again (1.00). The cost of the call is measured directly instead
   ([question 3](#3-intervalt-2)).
4. **Some packed kernels are slower than the scalar ones on the M3.** The packed `next_up` takes
   1.32 to 1.39 times the scalar loop with Apple clang, which vectorizes the scalar kernel's loop
   into a shorter sequence (58 instructions for eight numbers, against 22 for two in the generated
   NEON kernel); `mul_down_1` and `mul_up_1` take 1.01 to 1.10 times it with both compilers. NEON has
   two lanes of `double`, as the compilers' own vectorization, so a packed kernel gains only where
   the compiler does not vectorize the scalar loop: the intervals and balls take 0.51 to 0.95 of the
   scalar time on the M3. On Zen 2 the packed blocks and intervals take 0.26 to 0.66 of the time of
   the scalar loop (`next_up` 0.40 to 0.53), and the packed balls 0.83 to 1.01, the compilers
   vectorizing the scalar loops of balls themselves (256-bit).
5. **Under `FENV_ACCESS`, Clang does not vectorize.** The fenv_loop props compiled by Apple clang
   and Clang 18 are scalar loops (constrained operations are not vectorized); GCC 13 and GCC 16
   vectorize them (256-bit and 128-bit) under `-frounding-math`. Neither reaches the plain loop
   under a mode
   ([question 1](#1-rounding-down-and-up-without-a-rounding-mode)), which is what a classical library
   gets only when its compiler emits the plain code for it.
6. **Some rounding-mode props are three to six times slower at `-O3` than at `-O2` on Zen 2**
   (GCC 13: `interval_mul_1` fenv 117 ns against 38, the dependent Horner csr 278 ns against 45;
   Clang 18: the dependent Horner fenv 1 600 ns against 606), with the same instructions in the
   loop of `interval_mul_1` at both levels. Not investigated: these are baselines, and the page
   compares Kairn with the faster level of each.

## How the rounding-mode props honor the mode

The classical baselines are props of the harness (`bench/m2_fenv.cpp`, `bench/m2_fenv_packed.cpp`),
not part of the library, and they do not include Kairn. Each must really compute under the mode it
sets, which a compiler is free to ignore: without being told, it may compute an operation before
the call that sets the mode or after the one that resets it, fold it, or merge two operations on
the same operands under two modes into one. Three things prevent that, and one checks it.

- **Flags.** Both files are compiled with `-frounding-math` (with MSVC it would be `/fp:strict`),
  which tells the compiler that the rounding mode can change at run time, so that it neither folds
  nor reorders on the assumption of rounding to nearest. With Clang (Apple clang 21, Clang 18) the
  pragma `STDC FENV_ACCESS ON` is in force for the whole file, which makes every operation a
  constrained one, ordered with respect to calls. GCC does not implement the pragma, so the file
  states it for Clang only, and with GCC the next point is what keeps each operation in place.
- **Opaque operands and results.** Each operation that runs under a mode set around it has its
  operands and its result passed through an empty `asm volatile` statement that the compiler must
  assume reads and changes the value (`KB_OPAQUE`, `bench/m2_data.hpp`), placed after the change of
  mode and before the change back. The operation can then move across neither, and the four
  products of an interval computed under two modes cannot be merged. The variants that set the mode
  once around a loop have none of these inside the loop, so that the compiler may vectorize it:
  their loads come after the call that sets the mode and their stores before the call that resets
  it, which every compiler must respect for memory that a call may read or write.
- **The machine code.** The disassembly of every compiler shows the arithmetic instruction between
  the two calls of `fesetround`, or between the two writes of the control register
  (`msr FPCR` on the M3, `vldmxcsr` on Zen 2), in every per-operation prop looked at
  (`kb_m2_64_tp_add_down__fenv`, `__csr`, `kb_m2_64_tp_interval_mul_1__fenv`, `__csr`, with
  `bench/asm_summary.py` and a listing of the loops). On x86-64 the operands are spilled to the
  stack around each call, because no vector register survives a call there: a real library that
  calls `fesetround` pays that too.
- **The check.** Before anything is timed, every prop (51 for each limb type, and 4 packed ones) is
  compared with Kairn's result for the same operation, bit for bit, on the benchmark's numbers (1 to
  512 values per prop); and the props of the six directed blocks also on a wide sample of $2^{16}$
  pairs per operation, limb type and variant, half of them drawn over every finite value of the
  format. The counts are in [Checks](#checks). Of the props whose operation the harness also has
  rounded to nearest (15 per variant and limb type: the blocks, their chains, the intervals of one
  limb and their chains), 1 309 of the 3 080 values of each variant for `double`, and 1 368 of
  3 080 for `float`, are not the result rounded to nearest: a prop that ignored the mode would have
  failed on those. On the wide
  sample, 1 522 984 of the 1 572 864 results are equal bit for bit, 1 664 are zeros of the other
  sign (the sign of an exact zero, which Kairn does not claim: $a + (-a)$ is $-0$ rounded down
  under IEEE 754), 48 216 are products below $2^{2p-1}\eta$ where Kairn's bound is the number
  beyond the exact rounding, as the statement of `mul_down` allows, and none fails; 820 986 of them
  are not the result rounded to nearest. The same counts on every configuration.

## Still to come

This page measures what `main` held at commit `dee8ecd`. Measured later, with the same harness,
which takes them as new rows of its tables (`bench/README.md`, "Milestone 2"):

- what reached `main` after that commit and is not measured here: the predicates and comparisons
  of `Interval` and `Ball` (`is_empty`, `contains`, the signs, the three-valued comparisons, the
  relations of IEEE 1788), the midpoint, radius, split and conversions of intervals of two limbs,
  the hull, intersection and split of balls, and `Packed` and the containers;
- what is not on `main` yet, in review: the functions on arrays (sum, dot product, `axpy`,
  convolution, norm), `BallVector` and the accumulator.

(State on 2026-11-21. The paragraph first written here, at `dee8ecd`, listed all of these as not
on `main` yet.)

## How it was measured

| Machine | Configurations | Conditions |
|---|---|---|
| M3: macOS 26.6 arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2; `-O2` and `-O3`; packed code NEON | macOS has no affinity: the thread asked for the user-interactive class, which runs on performance cores. Shared with other jobs: a run was started only when the 1-minute load average was under 20 (it was 3 to 19, other jobs running), and a run whose median spread (the median over the minimum of a function's 41 samples, at the median function) exceeded 5% was set aside and repeated, until three passed: Apple clang 3 of 3 attempts at each level, GCC 16 3 of 6 at `-O2` and 3 of 4 at `-O3`; a first set of Apple clang runs, made at a load of 5 to 12 with median spreads up to 14%, was set aside whole |
| Zen 2: Linux x86-64, AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1; `-O2` and `-O3`; `-mfma`, packed code `-mavx2 -mfma` | each run pinned to one logical CPU of the second socket whose SMT sibling was idle (`taskset`, and `--cpu`), the two levels on two cores of different core complexes, the settings of question 7 on a third; `mpstat` of the CPU and its sibling recorded every 5 s during each run, and two runs whose sibling had been busy repeated on another core; the machine was shared (load average 19 to 45 during the runs), but no other job ran on those cores (the sibling of one kept run was busy for a few seconds) |

- **Commit**: `dee8ecd` on both machines, recorded in every JSON file of `kairn-bench-m2` and of the
  compile measurements; the mode test is of `76cfd02`, which adds it and changes nothing else that is
  timed.
- **Flags**: those of Milestone 1: hardware FMA as `kairn::fma` gives it, contraction off
  (`-ffp-contract=off`), never `-ffast-math`, `NDEBUG` (so `KAIRN_CHECKS` is 0); the props of
  `m2_fenv*.cpp` also `-frounding-math`. The scalar code has `-mfma` on x86-64, which allows the
  compilers 256-bit vectors in the loops they vectorize; the packed code `-mavx2 -mfma`.
- **Inputs**: 256 elements per array, from a fixed seed, the same with every compiler: numbers
  $\pm[1, 2) \cdot 2^k$ with $k \in [-8, 8]$; intervals of one limb of half-width $2^{-30}$ (`double`)
  or $2^{-12}$ (`float`) of their center, of two limbs $2^{-80}$ or $2^{-40}$; the balls of the same
  intervals, and balls of two limbs of radius about $2^{-80}$ (`double`) of the center, as in
  Milestone 1; factors in $[2^{-1/4}, 2^{1/4})$ for products; no overflow, underflow or subnormal
  operand in a timed loop, no product below $2^{2p-1}\eta$.
- **Loops and chains**: each a non-inlined function called through a pointer; the compilers were
  free to vectorize a loop.
- **Checks before timing**: every timed function against its reference, bit for bit (359 functions
  of each configuration), the rounding-mode props also on the wide sample
  ([Checks](#checks)). None failed on any configuration.
- **Repeatability**: three runs of each configuration of the inline setting, two of each of the
  outlined and external ones (one with GCC 16). On Zen 2 the runs of a configuration agree within
  1% at the median function and within 1.2% for nine functions in ten; a few functions vary more
  (up to 89% for one rounding-mode prop of `float`, a chain under one mode), and are named in
  [Runs](#runs). On the M3
  the kept runs agree within 1.9 to 3.3% at the median function and within 4 to 9% for nine
  functions in ten; a run as a whole can be a few percent faster or slower than another (the core's
  clock), which moves the times and not the ratios within a run.
- **Compile times**: on Zen 2, one compiler per core, pinned (`--cpu`) to idle cores of the first
  socket, each unit three times in rounds (once for 10 000 operations), with a timeout of an hour;
  the repeated compilations and runs of the units on idle cores of the second socket. On the M3 one
  compilation at a time, each set started under a load of 20. The tables give the compiler's
  processor time, which was its wall time within 1% wherever the core was its own (the JSON files
  keep both): on Zen 2 a compilation stopped at the hour left its compiler running on the same
  core for an hour more, unnoticed, and the wall times of the three compilations that followed it
  there (10 000 operations at `-O2`, outlined, external and the calls alone) are about twice their
  processor times. Every unit's run checks that its results are finite.
- **Measured**: the times, the bitwise agreements, the widths, the instruction counts.
  **Inferred**: the explanations, which are readings of the machine code; the cost of a write of
  `FPCR` or `MXCSR`, which is the difference of two measured times.
- **Not measured**: Intel processors (the i5 of Milestone 1 was not used here: changing `MXCSR` may
  cost there what it does not on Zen 2), Windows and MSVC, clang-cl; GPUs; packed code of `float`
  limbs; `KAIRN_CHECKS=1`; AVX-512; a classical interval library itself (the props are the
  operations such a library performs, not its code); the product of intervals by a case analysis on
  signs (see [question 2](#2-intervalt-1)).

## Tables

The tables below are printed by `python3 bench/m2_report.py results/milestone2/bench` from the
stored files, and those of the answers are rows of them, put into this page by the same script
(`--fill`); no number in a table was typed by hand. The compile times are those of
`results/milestone2/bench/compile-*.json` and `rational-compile-*.json`.

### Configurations

| Configuration | CPU | Compiler | Flags | Rounding-mode props | Runs | Date, commit |
|---|---|---|---|---|---:|---|
| linux-clang-inline-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror --gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13 -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |
| linux-clang-inline-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror --gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13 -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |
| linux-gcc-inline-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |
| linux-gcc-inline-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |
| mac-appleclang-inline-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |
| mac-appleclang-inline-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |
| mac-gcc16-inline-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |
| mac-gcc16-inline-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-21, `dee8ecd` |

### Checks

| Checks of | Runs | Functions checked, failed | Wide sample: compared, equal, zero of the other sign, below P one number wider, failed; not the result rounded to nearest | Load average (1 min) at start, end of each run |
|---|---:|---|---|---|
| linux-clang-inline-O2 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 38.4, 28.7; 22.9, 19.6; 18.7, 18.8 |
| linux-clang-inline-O3 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 36.5, 28.3; 22.4, 19.6; 18.8, 18.7 |
| linux-gcc-inline-O2 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 44.9, 38.4; 28.7, 22.9; 19.6, 18.7 |
| linux-gcc-inline-O3 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 44.9, 36.5; 28.3, 22.4; 19.6, 18.8 |
| mac-appleclang-inline-O2 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 19.1, 10.4; 10.4, 4.7; 4.7, 4.4 |
| mac-appleclang-inline-O3 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 4.4, 6.4; 6.4, 3.6; 3.6, 7.5 |
| mac-gcc16-inline-O2 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 15.3, 11.3; 11.3, 12.0; 10.1, 7.7 |
| mac-gcc16-inline-O3 | 3 | 359, 0 | 1572864, 1522984, 1664, 48216, 0; 820986 | 8.2, 3.4; 3.4, 3.7; 3.7, 2.9 |

| Props of | Variant | Props | Values compared with Kairn, bit for bit | Of them not the result rounded to nearest | Configurations |
|---|---|---:|---:|---:|---:|
| double | `csr` | 15 | 3080 | 1309 | 8 |
| double | `fenv` | 15 | 3080 | 1309 | 8 |
| double | `fenv_loop` | 15 | 3080 | 1309 | 8 |
| float | `csr` | 15 | 3080 | 1368 | 8 |
| float | `fenv` | 15 | 3080 | 1368 | 8 |
| float | `fenv_loop` | 15 | 3080 | 1368 | 8 |

### Runs

| Run | Over the fastest run: median, 90th percentile | Median over minimum within the run (median function) | Load average (1, 5 min) at start, end |
|---|---|---|---|
| `linux-clang-O2-r1.json` | 1.004, 1.008 | 1.011 | 38.4 36.2, 28.7 33.9 |
| `linux-clang-O2-r2.json` | 1.000, 1.002 | 1.004 | 22.9 31.1, 19.6 28.2 |
| `linux-clang-O2-r3.json` | 1.000, 1.002 | 1.008 | 18.7 26.0, 18.8 24.4 |
| `linux-clang-O3-r1.json` | 1.001, 1.005 | 1.011 | 36.5 35.9, 28.3 33.6 |
| `linux-clang-O3-r2.json` | 1.001, 1.004 | 1.004 | 22.4 30.7, 19.6 27.9 |
| `linux-clang-O3-r3.json` | 1.001, 1.003 | 1.008 | 18.8 25.8, 18.7 24.2 |
| `linux-gcc-O2-r1.json` | 1.008, 1.011 | 1.010 | 44.9 36.4, 38.4 36.2 |
| `linux-gcc-O2-r2.json` | 1.003, 1.006 | 1.010 | 28.7 33.9, 22.9 31.1 |
| `linux-gcc-O2-r3.json` | 1.000, 1.000 | 1.007 | 19.6 28.2, 18.7 26.0 |
| `linux-gcc-O3-r1.json` | 1.008, 1.011 | 1.010 | 44.9 36.4, 36.5 35.9 |
| `linux-gcc-O3-r2.json` | 1.000, 1.001 | 1.009 | 28.3 33.6, 22.4 30.7 |
| `linux-gcc-O3-r3.json` | 1.001, 1.004 | 1.008 | 19.6 27.9, 18.8 25.8 |
| `mac-appleclang-O2-r1.json` | 1.020, 1.093 | 1.031 | 19.1 26.3, 10.4 21.7 |
| `mac-appleclang-O2-r2.json` | 1.000, 1.000 | 1.025 | 10.4 21.7, 4.7 16.5 |
| `mac-appleclang-O2-r3.json` | 1.020, 1.093 | 1.024 | 4.7 16.5, 4.4 13.0 |
| `mac-appleclang-O3-r1.json` | 1.020, 1.040 | 1.022 | 4.4 13.0, 6.4 11.1 |
| `mac-appleclang-O3-r2.json` | 1.007, 1.019 | 1.003 | 6.4 11.1, 3.6 8.8 |
| `mac-appleclang-O3-r3.json` | 1.000, 1.024 | 1.049 | 3.6 8.8, 7.5 8.7 |
| `mac-gcc16-O2-r1.json` | 1.001, 1.029 | 1.038 | 15.3 10.1, 11.3 10.2 |
| `mac-gcc16-O2-r2.json` | 1.000, 1.035 | 1.041 | 11.3 10.2, 12.0 10.6 |
| `mac-gcc16-O2-r3.json` | 1.031, 1.043 | 1.018 | 10.1 11.5, 7.7 10.6 |
| `mac-gcc16-O3-r1.json` | 1.001, 1.072 | 1.020 | 8.2 9.8, 3.4 7.7 |
| `mac-gcc16-O3-r2.json` | 1.019, 1.065 | 1.003 | 3.4 7.7, 3.7 6.5 |
| `mac-gcc16-O3-r3.json` | 1.000, 1.011 | 1.021 | 3.7 6.5, 2.9 5.5 |

| Spread of | Runs | Spread of a function over the runs: median, 90th percentile, worst | Worst function |
|---|---:|---|---|
| linux-clang-inline-O2 | 3 | 0.4%, 0.8%, 2.6% | `m2/tp/divide_large/plain` |
| linux-clang-inline-O3 | 3 | 0.2%, 0.6%, 11.3% | `m2f/lat/horner_i1/fenv` |
| linux-gcc-inline-O2 | 3 | 0.8%, 1.2%, 88.6% | `m2f/prod/mul_up/fenv_loop` |
| linux-gcc-inline-O3 | 3 | 0.8%, 1.1%, 22.6% | `m2p/tp/add_down_1/fenv_loop` |
| mac-appleclang-inline-O2 | 3 | 2.1%, 9.4%, 43.9% | `m2/prod/call_8_4/plain` |
| mac-appleclang-inline-O3 | 3 | 2.2%, 4.0%, 45.2% | `m2/prod/call_8_4/plain` |
| mac-gcc16-inline-O2 | 3 | 3.3%, 4.3%, 24.9% | `m2/tp/call_8_4/kairn` |
| mac-gcc16-inline-O3 | 3 | 1.9%, 7.5%, 26.1% | `m2/tp/call_8_4/kairn` |

### Question 1: building blocks

| Kairn over the plain operation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add_down` over one `add` of T, loop | 4.64 to 4.71 | 5.06 to 5.28 (-O2), 5.05 (-O3) | 10.1 to 10.2 | 6.85 to 6.86 |
| `add_up` over one `add` of T, loop | 5.08 to 5.11 | 5.30 to 5.41 | 10.6 to 10.7 | 8.80 to 8.82 |
| `sub_down` over one `sub` of T, loop | 4.58 to 4.71 (-O2), 4.45 to 4.67 (-O3) | 5.31 to 5.52 (-O2), 5.31 to 5.34 (-O3) | 10.5 to 10.7 | 6.95 to 6.96 |
| `mul_down` over one `mul` of T, loop | 5.31 to 5.40 (-O2), 5.15 to 5.32 (-O3) | 4.85 to 5.01 (-O2), 5.01 to 5.02 (-O3) | 8.87 to 8.94 | 6.86 to 6.90 |
| `mul_up` over one `mul` of T, loop | 5.75 to 5.79 (-O2), 5.59 to 5.78 (-O3) | 5.21 to 5.24 | 9.08 to 9.18 | 8.91 to 8.93 |
| `add_down` over one `add` of T, chain | 14.9 to 15.9 (-O2), 13.6 to 15.0 (-O3) | 7.55 to 7.83 (-O2), 7.81 to 8.42 (-O3) | 5.92 to 5.95 | 7.73 to 7.74 |
| `add_up` over one `add` of T, chain | 14.9 to 15.4 (-O2), 14.8 to 15.0 (-O3) | 7.98 to 8.04 (-O2), 7.98 to 8.58 (-O3) | 6.06 to 6.11 | 8.23 to 8.24 |
| `mul_down` over one `mul` of T, chain | 8.01 to 8.18 (-O2), 8.01 to 8.31 (-O3) | 4.93 to 5.16 (-O2), 5.02 to 5.38 (-O3) | 7.44 to 7.50 | 8.97 to 9.08 |
| `mul_up` over one `mul` of T, chain | 8.04 to 8.19 (-O2), 7.95 to 8.49 (-O3) | 4.80 to 5.04 (-O2), 4.88 to 5.24 (-O3) | 7.47 to 7.51 | 9.40 to 9.41 |

| Against a change of the rounding mode | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add_down`, loop: fenv over Kairn | 35.8 to 36.4 (-O2), 35.3 to 35.8 (-O3) | 31.0 to 31.8 | 16.0 to 16.1 | 23.7 to 23.8 |
| `add_down`, loop: csr over Kairn | 28.2 to 28.6 (-O2), 27.7 to 28.9 (-O3) | 26.4 to 27.9 (-O2), 27.3 to 28.0 (-O3) | 0.81 to 0.82 | 1.48 |
| `add_down`, loop: Kairn over fenv_loop | 1.70 to 1.73 (-O2), 1.69 to 1.76 (-O3) | 3.19 to 3.25 | 1.81 to 1.83 | 0.91 to 0.92 |
| `add_up`, loop: fenv over Kairn | 32.3 to 33.0 (-O2), 32.4 to 33.7 (-O3) | 29.8 to 31.0 (-O2), 29.8 (-O3) | 15.2 to 15.4 | 18.4 to 18.5 |
| `add_up`, loop: csr over Kairn | 25.1 to 25.5 (-O2), 25.3 to 27.0 (-O3) | 25.0 to 26.1 (-O2), 26.6 to 26.9 (-O3) | 0.77 to 0.78 | 1.15 |
| `add_up`, loop: Kairn over fenv_loop | 1.88 to 1.91 | 3.24 to 3.39 (-O2), 3.34 to 3.38 (-O3) | 1.90 to 1.92 | 1.17 to 1.18 |
| `sub_down`, loop: fenv over Kairn | 36.1 to 36.8 (-O2), 35.3 to 36.1 (-O3) | 29.6 to 30.4 | 15.4 to 15.5 | 23.3 to 23.4 |
| `sub_down`, loop: csr over Kairn | 27.1 to 29.0 (-O2), 27.8 to 28.5 (-O3) | 25.1 to 26.8 (-O2), 24.6 to 25.3 (-O3) | 1.00 (-O2), 0.78 to 0.79 (-O3) | 1.46 |
| `sub_down`, loop: Kairn over fenv_loop | 1.69 to 1.73 (-O2), 1.71 to 1.78 (-O3) | 3.38 to 3.44 | 1.89 to 1.90 | 0.92 to 0.93 |
| `sub_up`, loop: fenv over Kairn | 33.1 to 33.7 (-O2), 32.4 to 33.4 (-O3) | 28.5 to 28.8 | 14.6 to 14.7 | 18.1 to 18.2 |
| `sub_up`, loop: csr over Kairn | 24.8 to 26.5 (-O2), 25.5 to 26.2 (-O3) | 24.1 to 25.7 (-O2), 23.5 to 24.0 (-O3) | 0.74 to 0.75 | 1.12 to 1.14 |
| `sub_up`, loop: Kairn over fenv_loop | 1.84 to 1.88 (-O2), 1.86 to 1.90 (-O3) | 3.37 to 3.56 (-O2), 3.49 to 3.55 (-O3) | 1.99 to 2.00 (-O2), 1.97 to 2.14 (-O3) | 1.19 to 1.20 |
| `mul_down`, loop: fenv over Kairn | 31.7 to 32.3 (-O2), 31.3 to 31.7 (-O3) | 31.7 to 32.4 | 18.2 to 18.4 | 23.7 |
| `mul_down`, loop: csr over Kairn | 23.6 to 25.4 (-O2), 24.5 to 24.9 (-O3) | 27.6 to 28.4 (-O2), 27.4 to 27.6 (-O3) | 0.93 (-O2), 1.19 to 1.20 (-O3) | 1.48 |
| `mul_down`, loop: Kairn over fenv_loop | 1.91 to 1.97 (-O2), 1.94 to 2.00 (-O3) | 3.08 to 3.24 (-O2), 3.15 to 3.19 (-O3) | 1.58 to 1.60 | 0.91 to 0.92 |
| `mul_up`, loop: fenv over Kairn | 29.2 to 29.7 (-O2), 28.6 to 29.3 (-O3) | 29.9 to 30.5 | 17.8 to 18.0 | 18.3 |
| `mul_up`, loop: csr over Kairn | 21.6 to 23.4 (-O2), 22.0 to 22.9 (-O3) | 25.8 to 27.3 (-O2), 26.5 to 27.3 (-O3) | 0.90 (-O2), 1.17 (-O3) | 1.14 |
| `mul_up`, loop: Kairn over fenv_loop | 2.08 to 2.15 (-O2), 2.12 to 2.21 (-O3) | 3.30 to 3.33 | 1.62 to 1.65 | 1.19 |
| `add_down`, chain: fenv over Kairn | 4.21 to 4.26 (-O2), 4.13 to 4.61 (-O3) | 6.32 to 6.51 (-O2), 6.29 to 6.33 (-O3) | 5.09 to 5.14 | 3.92 to 3.93 |
| `add_down`, chain: csr over Kairn | 2.85 to 3.08 (-O2), 2.99 to 3.34 (-O3) | 5.46 to 5.64 (-O2), 4.85 to 5.39 (-O3) | 0.26 to 0.27 | 0.20 |
| `add_down`, chain: Kairn over fenv_loop | 7.56 to 8.17 (-O2), 7.12 to 7.95 (-O3) | 4.89 to 5.09 (-O2), 5.10 to 5.47 (-O3) | 2.99 to 3.02 | 3.92 to 3.93 |
| `add_up`, chain: fenv over Kairn | 4.20 to 4.21 (-O2), 4.08 to 4.21 (-O3) | 6.18 to 6.30 (-O2), 5.80 to 6.18 (-O3) | 4.96 to 5.02 | 3.67 to 3.69 |
| `add_up`, chain: csr over Kairn | 2.98 to 3.05 | 5.23 to 5.52 (-O2), 5.25 to 5.52 (-O3) | 0.26 | 0.19 |
| `add_up`, chain: Kairn over fenv_loop | 7.64 to 7.85 | 5.09 to 5.33 (-O2), 5.19 to 5.60 (-O3) | 3.09 to 3.41 (-O2), 3.07 to 3.08 (-O3) | 4.18 to 4.19 |
| `mul_down`, chain: fenv over Kairn | 3.95 to 4.01 (-O2), 3.95 to 4.09 (-O3) | 6.26 to 6.53 (-O2), 6.28 to 6.80 (-O3) | 4.07 to 4.08 | 3.35 to 3.39 |
| `mul_down`, chain: csr over Kairn | 2.84 to 2.91 (-O2), 2.85 to 2.96 (-O3) | 4.87 to 5.12 (-O2), 5.34 to 5.82 (-O3) | 0.21 | 0.17 to 0.18 |
| `mul_down`, chain: Kairn over fenv_loop | 5.36 to 5.41 (-O2), 5.26 to 5.48 (-O3) | 3.27 to 3.43 (-O2), 3.19 to 3.34 (-O3) | 3.78 to 3.79 (-O2), 7.15 to 7.20 (-O3) | 4.58 to 4.63 |
| `mul_up`, chain: fenv over Kairn | 3.99 to 4.00 (-O2), 3.95 to 4.07 (-O3) | 6.46 to 6.79 (-O2), 6.61 to 6.90 (-O3) | 4.06 to 4.09 | 3.23 to 3.24 |
| `mul_up`, chain: csr over Kairn | 2.85 to 2.93 | 5.26 to 5.53 (-O2), 5.59 to 6.16 (-O3) | 0.21 | 0.17 |
| `mul_up`, chain: Kairn over fenv_loop | 5.37 to 5.39 (-O2), 5.28 to 5.46 (-O3) | 3.17 to 3.34 (-O2), 3.09 to 3.25 (-O3) | 3.79 to 7.10 (-O2), 3.78 (-O3) | 4.80 to 4.82 |

| The other blocks | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `next_up`, loop, over `std::nextafter` | 0.17 to 0.19 | 0.18 | 0.07 to 0.08 | 0.09 to 0.10 |
| `next_up`, chain, over `std::nextafter` | 0.43 to 0.46 | 0.36 to 0.37 | 0.50 to 0.54 | 0.43 to 0.45 |
| `next_up`, loop, over one addition | 2.68 to 2.73 | 2.44 to 2.55 (-O2), 2.44 to 2.45 (-O3) | 3.82 to 3.84 | 4.71 to 4.76 |
| `radd`, loop, over one addition | 3.49 to 3.54 | 3.07 to 3.08 | 6.30 to 6.33 | 7.48 to 7.50 |
| `radd`, chain, over one addition | 13.6 to 13.7 (-O2), 13.3 to 13.8 (-O3) | 10.4 to 10.6 | 8.31 to 8.33 | 7.80 to 7.83 |
| `rmul`, loop, over one product | 3.06 to 3.11 (-O2), 2.99 to 3.05 (-O3) | 2.57 to 2.68 (-O2), 2.67 (-O3) | 5.35 to 5.36 | 6.40 to 6.48 |
| `rmul`, chain, over one product | 6.61 to 6.74 (-O2), 6.57 to 7.00 (-O3) | 6.20 to 6.51 (-O2), 6.11 to 6.79 (-O3) | 7.97 to 7.99 | 7.44 to 7.46 |
| `two_sum`, loop, over one addition | 2.28 to 2.30 | 2.21 to 2.29 (-O2), 2.23 (-O3) | 3.88 to 3.93 | 10.2 to 10.4 |
| `two_prod`, loop, over one product | 1.37 to 1.40 (-O2), 1.34 to 1.37 (-O3) | 1.75 to 1.82 (-O2), 1.83 (-O3) | 2.97 to 2.98 | 4.04 to 4.14 |
| the public block over the generated kernel, `add_down`, loop | 1.17 to 1.20 | 1.09 to 1.11 | 1.15 to 1.17 | 1.19 |
| the public block over the generated kernel, `mul_down`, loop | 1.00 | 0.98 to 1.01 | 0.99 to 1.00 | 1.00 |

| Times of the blocks (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/add/plain` | 0.147 to 0.152 | 0.156 to 0.162 | 0.154 to 0.155 | 0.153 to 0.154 |
| `m2/tp/add_down/op` | 0.688 to 0.717 | 0.789 to 0.822 | 1.56 to 1.57 | 1.05 to 1.06 |
| `m2/tp/add_down/fenv` | 24.6 to 25.3 | 24.7 to 25.7 | 25 to 25.3 | 25 to 25.1 |
| `m2/tp/add_down/csr` | 19.4 to 20 | 21.7 to 22.9 (-O2), 21.9 to 22.1 (-O3) | 1.27 to 1.28 | 1.56 to 1.57 |
| `m2/tp/add_down/fenv_loop` | 0.398 to 0.41 | 0.246 to 0.257 | 0.854 to 0.869 | 1.15 to 1.16 |
| `m2/tp/mul_down/op` | 0.776 to 0.81 | 0.778 to 0.794 | 1.36 to 1.38 | 1.05 to 1.06 |
| `m2/tp/mul_down/fenv` | 24.6 to 25.4 | 24.8 to 25.7 | 25.1 to 25.2 | 25 to 25.1 |
| `m2/sum/add/plain` | 0.366 to 0.401 (-O2), 0.399 to 0.409 (-O3) | 0.499 to 0.519 (-O2), 0.465 to 0.501 (-O3) | 0.804 to 0.811 | 0.803 to 0.807 |
| `m2/sum/add_down/op` | 5.83 to 5.95 (-O2), 5.44 to 6.09 (-O3) | 3.9 to 4.06 | 4.79 to 4.8 | 6.22 to 6.24 |
| `m2/sum/add_down/fenv` | 24.6 to 25.1 | 24.6 to 25.7 | 24.4 to 24.6 | 24.4 to 24.5 |
| `m2/sum/add_down/csr` | 16.6 to 18.2 (-O2), 17.8 to 18.2 (-O3) | 21.3 to 22.9 (-O2), 19.3 to 21 (-O3) | 1.27 to 1.28 | 1.27 |
| `m2/sum/add_down/fenv_loop` | 0.714 to 0.783 (-O2), 0.75 to 0.767 (-O3) | 0.782 to 0.798 (-O2), 0.715 to 0.78 (-O3) | 1.58 to 1.61 | 1.58 to 1.59 |
| `m2/prod/mul_down/op` | 5.73 to 6.27 (-O2), 6.14 to 6.4 (-O3) | 3.84 to 4.01 (-O2), 3.58 to 3.9 (-O3) | 5.99 to 6.01 | 7.21 to 7.31 |
| `m2/prod/mul_down/fenv` | 22.9 to 25.1 (-O2), 25.1 to 25.6 (-O3) | 24.7 to 25.7 (-O2), 24.3 to 24.7 (-O3) | 24.4 to 24.5 | 24.4 to 24.5 |

### Question 2: `Interval<T, 1>`

| Interval<T, 1> over the floor | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop, over two plain operations | 6.24 to 6.37 (-O2), 6.37 to 6.58 (-O3) | 5.95 to 6.13 | 10.9 to 11.0 | 7.24 to 7.40 |
| `interval_sub_1`, loop, over two plain operations | 4.66 to 4.79 | 4.41 to 4.54 | 11.2 to 11.3 | 7.29 to 7.36 |
| `interval_mul_1`, loop, over two plain operations | 20.5 to 21.0 | 26.3 to 26.9 (-O2), 26.9 to 27.3 (-O3) | 30.4 to 30.5 | 27.9 to 28.1 |
| `interval_mul_1`, loop, over the four products rounded to nearest | 8.11 to 8.20 | 8.29 to 8.46 (-O2), 7.42 to 7.51 (-O3) | 9.70 to 9.77 | 15.1 to 15.2 |
| `interval_add_1`, chain, over two plain additions | 9.6 to 10.4 (-O2), 9.57 to 9.78 (-O3) | 7.21 to 7.30 (-O2), 7.69 to 8.33 (-O3) | 7.10 to 7.14 | 8.38 to 8.46 |
| `interval_mul_1`, chain, over two plain products | 14.1 to 14.6 (-O2), 14.6 to 14.7 (-O3) | 13.0 to 13.5 (-O2), 13.6 to 14.6 (-O3) | 22.1 to 22.3 | 22.9 to 23.1 |
| `interval_mul_1`, chain, over the four products rounded to nearest | 4.73 to 4.89 (-O2), 4.30 to 4.37 (-O3) | 3.84 to 3.95 (-O2), 4.05 to 4.33 (-O3) | 8.70 to 8.82 | 3.76 to 3.80 |

| Interval<T, 1> against a change of the rounding mode | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop: fenv over Kairn | 18.5 to 20.2 (-O2), 19.2 to 19.7 (-O3) | 20.2 to 20.8 (-O2), 20.5 to 20.9 (-O3) | 10.4 to 10.5 | 7.93 to 8.12 |
| `interval_add_1`, loop: csr over Kairn | 14.0 to 15.3 (-O2), 14.7 to 15.1 (-O3) | 16.8 to 18.0 (-O2), 16.3 to 17.4 (-O3) | 0.60 to 0.61 (-O2), 0.69 (-O3) | 0.53 to 0.54 |
| `interval_add_1`, loop: Kairn over fenv_loop | 3.72 to 3.80 (-O2), 3.78 to 3.86 (-O3) | 2.76 to 2.87 (-O2), 3.47 to 3.50 (-O3) | 2.42 to 2.46 | 2.84 to 2.85 (-O2), 2.76 to 2.77 (-O3) |
| `interval_sub_1`, loop: fenv over Kairn | 19.6 to 19.9 (-O2), 19.2 to 19.8 (-O3) | 19.9 to 20.5 (-O2), 20.0 to 20.2 (-O3) | 10.0 to 10.2 | 8.10 to 8.13 |
| `interval_sub_1`, loop: csr over Kairn | 14.7 to 15.1 (-O2), 14.7 to 15.2 (-O3) | 17.7 to 17.9 | 0.58 to 0.59 | 0.54 |
| `interval_sub_1`, loop: Kairn over fenv_loop | 3.95 to 4.04 (-O2), 3.92 to 4.04 (-O3) | 2.83 to 2.87 (-O2), 3.60 to 3.61 (-O3) | 2.48 to 2.51 | 2.76 to 2.79 |
| `interval_mul_1`, loop: fenv over Kairn | 5.95 to 6.11 | 4.54 to 4.71 (-O2), 4.54 to 4.63 (-O3) | 3.81 to 3.83 (-O2), 11.7 (-O3) | 2.26 to 2.28 |
| `interval_mul_1`, loop: csr over Kairn | 4.92 to 4.94 (-O2), 4.75 to 4.85 (-O3) | 4.18 to 4.35 (-O2), 4.03 to 4.26 (-O3) | 0.40 | 0.27 to 0.28 |
| `interval_mul_1`, loop: Kairn over fenv_loop | 4.22 to 4.30 | 7.34 to 7.55 | 5.45 to 5.51 | 4.43 to 4.48 (-O2), 4.10 to 4.21 (-O3) |
| `interval_add_1`, chain: fenv over Kairn | 6.58 to 6.71 | 9.31 to 9.70 (-O2), 9.53 to 9.63 (-O3) | 6.44 to 6.50 | 5.42 to 5.49 |
| `interval_add_1`, chain: csr over Kairn | 4.51 to 4.84 (-O2), 4.74 to 4.84 (-O3) | 7.80 to 8.25 (-O2), 8.11 to 8.27 (-O3) | 0.33 | 0.32 |
| `interval_add_1`, chain: Kairn over fenv_loop | 6.69 to 7.19 (-O2), 6.73 to 6.84 (-O3) | 4.77 to 4.95 (-O2), 4.79 to 5.07 (-O3) | 3.55 to 3.57 | 4.24 to 4.28 |
| `interval_mul_1`, chain: fenv over Kairn | 3.32 to 3.41 (-O2), 3.23 to 3.28 (-O3) | 3.66 to 3.75 (-O2), 3.45 to 3.57 (-O3) | 2.03 to 2.05 | 2.10 to 2.14 |
| `interval_mul_1`, chain: csr over Kairn | 2.54 to 2.59 (-O2), 2.48 to 2.51 (-O3) | 3.30 to 3.34 (-O2), 3.15 to 3.27 (-O3) | 0.19 to 0.20 | 0.23 to 0.24 |
| `interval_mul_1`, chain: Kairn over fenv_loop | 3.28 to 3.41 (-O2), 3.34 to 3.40 (-O3) | 2.81 to 2.88 (-O2), 2.73 to 2.85 (-O3) | 5.02 to 5.07 | 5.78 to 5.83 |

| Interval<T, 1> over Ball<T, 1> | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, loop: interval over ball | 2.37 to 2.43 | 2.35 to 2.41 (-O2), 2.28 to 2.33 (-O3) | 2.55 to 2.58 | 3.12 to 3.18 |
| `X - Y`, loop: interval over ball | 2.41 to 2.46 | 2.39 to 2.48 (-O2), 2.41 to 2.43 (-O3) | 2.58 to 2.61 | 3.11 to 3.13 |
| `X * Y`, loop: interval over ball | 6.19 to 6.22 (-O2), 6.16 to 6.36 (-O3) | 7.95 to 8.39 (-O2), 8.65 to 8.75 (-O3) | 5.56 to 5.57 | 10.4 |
| `S + X`, chain: interval over ball | 1.97 to 2.11 (-O2), 1.97 to 1.98 (-O3) | 1.35 to 1.43 (-O2), 1.42 to 1.53 (-O3) | 1.46 to 1.48 | 1.72 to 1.74 |
| `P * X`, chain: interval over ball | 2.15 to 2.23 (-O2), 2.17 to 2.23 (-O3) | 1.81 to 1.91 (-O2), 2.09 to 2.24 (-O3) | 2.26 to 2.31 | 2.38 to 2.41 |

| The other functions of Interval<T, 1>, loops | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `-X` over two negations | 0.55 to 0.60 | 1.00 to 1.02 | 0.59 | 0.50 |
| `hull` over a min and a max | 0.98 to 1.00 | 1.00 | 1.00 | 1.00 |
| `intersection` over a max, a min and a test | 1.01 to 1.03 | 0.97 to 1.00 | 1.01 | 1.00 |
| `midpoint` and `radius` over (l + h)/2, (h - l)/2 | 21.1 to 22.2 (-O2), 21.6 to 21.8 (-O3) | 25.5 to 26.0 (-O2), 11.1 to 11.2 (-O3) | 52.1 to 52.2 (-O2), 22.2 to 22.3 (-O3) | 19.7 |
| `split` over (l + h)/2, (h - l)/2 | 10.6 to 11.3 (-O2), 11.1 to 11.5 (-O3) | 8.42 to 8.58 | 24.2 to 24.8 | 15.8 to 15.9 |
| `Ball<T, 1>(X)` over (l + h)/2, (h - l)/2 | 14.0 to 14.7 (-O2), 14.4 to 14.7 (-O3) | 11.8 to 12.2 (-O2), 8.83 to 8.97 (-O3) | 32.4 to 32.5 (-O2), 23.4 to 23.5 (-O3) | 15.0 to 15.1 |
| `Interval<T, 1>(B)` over c - r, c + r | 5.10 to 5.23 | 5.64 to 5.79 (-O2), 5.79 to 5.81 (-O3) | 10.8 to 11.1 | 7.27 to 7.29 |

| Times of Interval<T, 1> (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/interval_add_1/op` | 1.87 to 1.92 | 1.77 to 1.84 | 3.6 to 3.63 | 4.59 to 4.7 |
| `m2/tp/interval_mul_1/op` | 6.08 to 6.3 | 7.97 to 8.29 | 10 to 10.1 | 17.2 to 17.4 |
| `m2/tp/interval_neg_1/op` | 0.166 to 0.172 | 0.284 to 0.296 | 0.194 to 0.195 | 0.166 |
| `m2/tp/interval_hull_1/op` | 0.465 to 0.485 | 0.548 to 0.569 (-O2), 0.415 to 0.422 (-O3) | 0.762 to 0.769 | 0.637 to 0.642 |
| `m2/tp/interval_intersection_1/op` | 0.547 to 0.572 | 0.547 to 0.57 | 0.831 to 0.839 | 0.746 to 0.75 |
| `m2/tp/interval_midrad_1/op` | 6.4 to 6.68 | 7.86 to 7.96 (-O2), 3.32 to 3.38 (-O3) | 17.7 to 17.8 (-O2), 7.52 to 7.57 (-O3) | 13.6 to 13.7 |
| `m2/tp/interval_split_1/op` | 3.21 to 3.33 (-O2), 3.33 to 3.45 (-O3) | 2.54 to 2.63 | 8.2 to 8.48 | 10.9 to 11 |
| `m2/tp/interval_to_ball_1/op` | 4.25 to 4.43 | 3.62 to 3.71 (-O2), 2.65 to 2.71 (-O3) | 11 to 11.1 (-O2), 7.97 to 7.98 (-O3) | 10.4 |
| `m2/tp/ball_to_interval_1/op` | 1.74 to 1.81 | 1.64 to 1.71 | 3.63 to 3.67 | 4.6 to 4.62 |
| `m2/tp/ball_add_1/op` | 0.774 to 0.807 | 0.752 to 0.782 | 1.4 to 1.42 | 1.47 to 1.48 |
| `m2/tp/ball_mul_1/op` | 0.981 to 1.02 | 0.966 to 1.01 (-O2), 0.92 to 0.938 (-O3) | 1.8 to 1.82 | 1.66 |
| `m2/tp/interval_add_1/fenv` | 34.6 to 37.8 (-O2), 36.8 to 37.5 (-O3) | 36.9 to 38.4 (-O2), 36.2 to 37.5 (-O3) | 37.3 to 37.8 | 37.2 to 37.3 |
| `m2/tp/interval_mul_1/fenv` | 37.1 to 38 | 36.8 to 38.4 | 38.4 to 38.5 (-O2), 117 to 118 (-O3) | 39.1 to 39.4 |
| `m2/tp/interval_mul_1/csr` | 29.6 to 30.6 | 34.6 to 34.7 (-O2), 32.2 to 34.6 (-O3) | 4 to 4.03 | 4.67 to 4.85 |
| `m2/tp/interval_add_1/fenv_loop` | 0.493 to 0.505 | 0.64 to 0.667 (-O2), 0.505 to 0.517 (-O3) | 1.47 to 1.49 | 1.64 to 1.66 |
| `m2/tp/interval_mul_1/fenv_loop` | 1.44 to 1.47 | 1.07 to 1.12 | 1.82 to 1.85 | 3.86 to 3.88 (-O2), 4.12 to 4.21 (-O3) |
| `m2/tp/pair_add_1/plain` | 0.29 to 0.301 | 0.295 to 0.308 | 0.329 to 0.332 | 0.633 to 0.635 |
| `m2/tp/plain4_mul_1/plain` | 0.746 to 0.777 | 0.961 to 0.981 (-O2), 1.07 to 1.09 (-O3) | 1.03 to 1.04 | 1.14 to 1.15 |
| `m2/sum/interval_add_1/op` | 5.49 to 5.72 | 3.86 to 4.03 | 5.73 to 5.78 | 6.74 to 6.8 |
| `m2/prod/interval_mul_1/op` | 10.5 to 11.1 (-O2), 11.4 to 11.6 (-O3) | 10.3 to 10.6 | 18.8 to 19 | 18.4 to 18.6 |
| `m2/prod/interval_mul_1/fenv` | 34.8 to 37.5 (-O2), 37 to 37.6 (-O3) | 38.6 to 38.7 (-O2), 35.9 to 37.1 (-O3) | 38.6 to 39 | 39 to 39.5 |
| `m2/prod/interval_mul_1/fenv_loop` | 3.07 to 3.36 (-O2), 3.37 to 3.42 (-O3) | 3.67 (-O2), 3.65 to 3.85 (-O3) | 3.74 to 3.79 | 3.18 to 3.19 |
| `m2/sum/ball_add_1/op` | 2.6 to 2.84 (-O2), 2.83 to 2.9 (-O3) | 2.83 to 2.86 (-O2), 2.54 to 2.73 (-O3) | 3.91 to 3.95 | 3.91 to 3.92 |
| `m2/prod/ball_mul_1/op` | 4.69 to 5.13 (-O2), 5.13 to 5.25 (-O3) | 5.45 to 5.69 (-O2), 4.63 to 4.97 (-O3) | 8.23 to 8.37 | 7.71 to 7.75 |

### Question 3: `Interval<T, 2>`

| Interval<T, 2> | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, loop, over `Expansion<T, 2>` twice | 2.75 to 2.78 | 2.13 to 2.23 (-O2), 2.35 to 2.36 (-O3) | 2.80 to 2.81 | 4.62 to 4.68 |
| `X - Y`, loop, over `Expansion<T, 2>` twice | 2.59 (-O2), 2.49 to 2.59 (-O3) | 2.00 to 2.06 (-O2), 2.26 to 2.32 (-O3) | 2.83 to 2.87 | 4.67 to 4.71 |
| `X * Y`, loop, over `Expansion<T, 2>` twice | 18.5 to 18.7 (-O2), 18.2 to 18.7 (-O3) | 16.4 to 17.5 (-O2), 16.9 to 17.0 (-O3) | 16.0 to 16.2 | 26.7 to 27.2 |
| `X * Y`, loop, over the four products of `Expansion<T, 2>` | 4.31 to 4.40 | 5.00 to 5.11 | 5.72 to 5.87 | 14.1 to 14.2 (-O2), 13.9 to 14.3 (-O3) |
| `S + X`, chain, over `Expansion<T, 2>` twice | 2.60 to 2.78 (-O2), 2.60 to 2.71 (-O3) | 1.93 to 2.03 (-O2), 2.01 to 2.17 (-O3) | 2.60 | 2.42 to 2.44 |
| `P * X`, chain, over `Expansion<T, 2>` twice | 7.10 to 7.65 (-O2), 7.06 to 7.25 (-O3) | 7.29 to 7.68 (-O2), 7.36 to 7.89 (-O3) | 10.3 to 10.4 | 9.90 to 9.98 |
| `X + Y`, loop: interval over ball | 4.31 to 4.41 | 3.45 to 3.50 (-O2), 3.67 to 3.69 (-O3) | 5.92 to 5.95 | 6.17 to 6.25 |
| `X - Y`, loop: interval over ball | 4.02 to 4.08 | 3.13 to 3.27 (-O2), 3.57 to 3.63 (-O3) | 5.32 to 5.46 | 6.11 to 6.14 |
| `X * Y`, loop: interval over ball | 19.1 to 19.5 | 18.4 to 18.8 (-O2), 18.9 to 19.0 (-O3) | 20.9 to 21.1 | 30.8 to 31.2 |
| `S + X`, chain: interval over ball | 2.62 to 2.82 (-O2), 2.58 to 2.62 (-O3) | 2.02 to 2.10 (-O2), 2.09 to 2.26 (-O3) | 2.70 to 2.71 | 2.51 to 2.52 |
| `P * X`, chain: interval over ball | 7.05 to 7.59 (-O2), 7.01 to 7.19 (-O3) | 7.34 to 7.43 (-O2), 7.32 to 7.79 (-O3) | 10.6 | 9.90 to 9.99 |
| `X * Y`, loop: as called over flattened | 0.98 to 1.00 | 1.04 to 1.08 | 1.08 to 1.10 | 0.99 to 1.00 |
| `P * X`, chain: as called over flattened | 0.98 to 1.02 | 1.09 to 1.11 | 1.08 | 0.99 to 1.00 |
| a call of the same signature, loop: its time over that of `X * Y` | 0.01 | 0.01 | 0.01 | 0.01 to 0.02 |
| a call of the same signature, chain: its time over that of `P * X` | 0.04 to 0.07 | 0.04 | 0.03 | 0.03 |
| `X * Y` of two limbs over one limb, loop | 4.71 to 4.82 (-O2), 4.69 to 4.84 (-O3) | 3.63 to 3.77 (-O2), 3.62 to 3.68 (-O3) | 7.92 to 8.02 | 4.28 to 4.33 |
| `X + Y` of two limbs over one limb, loop | 4.54 to 4.61 (-O2), 4.43 to 4.62 (-O3) | 3.94 to 4.07 (-O2), 4.28 to 4.30 (-O3) | 6.85 to 6.89 | 4.01 to 4.09 |
| `hull`, loop, over `X + Y` of `Expansion<T, 2>` twice | 0.42 | 0.38 to 0.40 | 0.35 | 0.38 |

| Times of Interval<T, 2> (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/interval_add_2/op` | 8.5 to 8.83 | 7.23 to 7.45 (-O2), 7.59 to 7.69 (-O3) | 24.7 to 24.9 | 18.7 to 18.9 |
| `m2/tp/interval_sub_2/op` | 8.4 to 8.76 | 6.98 to 7.27 (-O2), 7.78 to 7.85 (-O3) | 25.2 to 25.5 | 18.9 |
| `m2/tp/interval_mul_2/op` | 29.2 to 30.5 | 29.4 to 30.1 | 79.8 to 80.9 | 73.8 to 75.1 |
| `m2/tp/interval_hull_2/op` | 1.29 to 1.34 | 1.29 to 1.34 | 3.07 to 3.11 | 1.53 to 1.54 |
| `m2/tp/interval_intersection_2/op` | 1.77 to 1.84 | 1.6 to 1.67 | 4.26 to 4.3 | 1.9 to 1.92 |
| `m2/tp/pair_add_2/op` | 3.08 to 3.18 | 3.31 to 3.39 (-O2), 3.21 to 3.27 (-O3) | 8.8 to 8.9 | 4.01 to 4.04 |
| `m2/tp/pair_mul_2/op` | 1.56 to 1.63 | 1.72 to 1.8 | 4.96 to 5.02 | 2.76 to 2.78 |
| `m2/tp/plain4_mul_2/op` | 6.66 to 6.95 | 5.77 to 6.02 | 13.7 to 14 | 5.24 to 5.32 |
| `m2/tp/ball_add_2/op` | 1.96 to 2.05 | 2.06 to 2.13 | 4.16 to 4.2 | 3.01 to 3.04 |
| `m2/tp/ball_mul_2/op` | 1.51 to 1.57 | 1.54 to 1.6 | 3.79 to 3.85 | 2.4 to 2.41 |
| `m2/tp/interval_mul_2/flat` | 29.3 to 30.5 | 27.8 to 29 | 72.9 to 74.4 | 74.3 to 75.1 |
| `m2/sum/interval_add_2/op` | 20.6 to 21.4 | 16.1 to 16.7 | 28.7 to 29 | 26.1 to 26.2 |
| `m2/prod/interval_mul_2/op` | 42.2 to 43.7 | 43.9 to 45.9 | 87.3 to 88.2 | 82.7 to 83.2 |
| `m2/prod/interval_mul_2/flat` | 41.5 to 43.4 (-O2), 42.7 to 44.4 (-O3) | 40.2 to 42.1 | 80.6 to 81.6 | 83 to 83.4 |
| `m2/sum/ball_add_2/op` | 7.31 to 8 (-O2), 7.99 to 8.18 (-O3) | 7.79 to 7.95 (-O2), 7.17 to 7.7 (-O3) | 10.6 to 10.7 | 10.4 |
| `m2/prod/ball_mul_2/op` | 5.56 to 6.08 (-O2), 6.08 to 6.1 (-O3) | 6.18 to 6.19 (-O2), 5.64 to 6.02 (-O3) | 8.23 to 8.33 | 8.33 to 8.35 |
| `m2/sum/pair_add_2/op` | 7.4 to 8.07 (-O2), 7.92 to 8.07 (-O3) | 8.03 to 8.3 (-O2), 7.46 to 8.03 (-O3) | 11 to 11.2 | 10.7 to 10.8 |
| `m2/prod/pair_mul_2/op` | 5.52 to 6.04 (-O2), 6.04 to 6.17 (-O3) | 5.98 to 6.23 (-O2), 5.57 to 5.97 (-O3) | 8.45 to 8.53 | 8.34 to 8.36 |
| `m2/tp/call_8_4/plain` | 0.812 to 0.846 | 0.812 to 0.846 | 1.86 to 1.88 | 1.55 to 1.56 (-O2), 2.17 to 2.18 (-O3) |
| `m2/tp/call_8_4/kairn` | 0.609 to 0.635 | 0.496 to 0.62 (-O2), 0.495 to 0.625 (-O3) | 0.962 to 0.97 | 0.961 to 0.965 |
| `m2/prod/call_8_4/plain` | 1.92 to 2.77 (-O2), 1.89 to 2.74 (-O3) | 1.92 to 1.97 (-O2), 1.85 to 1.88 (-O3) | 2.48 to 2.51 | 2.45 to 2.46 |
| `m2/prod/call_8_4/kairn` | 0.0031 to 0.00323 | 0.0031 to 0.00323 | 0.00715 to 0.00718 | 0.00715 to 0.00716 (-O2), 0.00596 to 0.00597 (-O3) |

### Question 4: Horner

| Horner, independent evaluations: ns per evaluation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| Interval<T, 1> | 124 to 126 (-O2), 120 to 128 (-O3) | 109 to 114 | 250 to 258 | 182 |
| Interval<T, 1>, fenv | 554 to 606 (-O2), 597 to 616 (-O3) | 617 to 618 (-O2), 566 to 592 (-O3) | 601 to 608 | 1260 to 1270 (-O2), 1280 to 1364 (-O3) |
| Interval<T, 1>, csr | 416 to 454 (-O2), 442 to 452 (-O3) | 542 to 567 (-O2), 511 to 541 (-O3) | 48.2 to 48.6 | 55.9 to 57 |
| Interval<T, 1>, fenv_loop | 16.1 to 16.9 (-O2), 12.7 to 13 (-O3) | 17.3 to 17.6 (-O2), 15.9 to 16.3 (-O3) | 46.3 to 46.5 (-O2), 44.4 to 46.7 (-O3) | 31.1 to 31.4 (-O2), 26.9 (-O3) |
| Interval<T, 2> | 466 to 509 (-O2), 492 to 521 (-O3) | 474 to 521 (-O2), 500 to 521 (-O3) | 1189 to 1211 | 844 to 850 |
| Interval<T, 2>, flattened | 466 to 509 (-O2), 466 to 522 (-O3) | 403 to 430 (-O2), 404 to 411 (-O3) | 1124 to 1144 | 845 to 849 |
| Ball<T, 1> | 26.7 to 27.9 | 27.6 to 28.9 (-O2), 25.8 to 28.1 (-O3) | 77.8 to 78.5 | 76 to 76.2 (-O2), 27.6 to 27.7 (-O3) |
| Ball<T, 2> | 64 to 69.8 (-O2), 68.6 to 71.4 (-O3) | 68.7 to 71.7 (-O2), 64.6 to 70 (-O3) | 147 to 149 | 144 to 145 |
| Expansion<T, 2>, a point | 49.6 to 54.3 (-O2), 53.2 to 54.2 (-O3) | 54.5 to 56.3 (-O2), 51 to 55.1 (-O3) | 139 to 140 | 135 to 136 |
| T, a point | 0.646 to 0.676 | 2.73 to 2.78 (-O2), 0.648 to 0.66 (-O3) | 4.26 to 4.35 (-O2), 0.83 to 0.835 (-O3) | 0.828 to 0.832 |

| Horner, dependent evaluations: ns per evaluation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| Interval<T, 1> | 134 to 139 | 118 to 124 | 252 to 262 | 189 to 191 |
| Interval<T, 1>, fenv | 582 to 606 (-O2), 594 to 620 (-O3) | 593 to 617 | 605 to 610 (-O2), 1899 to 1917 (-O3) | 606 (-O2), 1590 to 1601 (-O3) |
| Interval<T, 1>, csr | 417 to 454 (-O2), 450 to 461 (-O3) | 526 to 564 (-O2), 523 to 539 (-O3) | 44.5 to 44.9 (-O2), 277 to 279 (-O3) | 54.5 to 57 |
| Interval<T, 1>, fenv_loop | 34.7 to 37.7 (-O2), 31.4 to 32.2 (-O3) | 35 to 35.7 (-O2), 32.1 to 34 (-O3) | 34.5 to 34.8 | 31.6 to 31.9 (-O2), 29 to 29.1 (-O3) |
| Interval<T, 2> | 483 to 529 (-O2), 518 to 531 (-O3) | 485 to 513 (-O2), 519 to 539 (-O3) | 1190 to 1212 | 854 to 858 |
| Interval<T, 2>, flattened | 484 to 529 (-O2), 524 to 529 (-O3) | 412 to 434 (-O2), 412 to 420 (-O3) | 1126 to 1139 | 854 to 858 |
| Ball<T, 1> | 26.6 to 27.7 | 28.8 to 30 (-O2), 26.9 to 29.3 (-O3) | 79.4 to 80.1 | 75.9 to 76.3 |
| Ball<T, 2> | 102 to 112 (-O2), 110 to 114 (-O3) | 113 to 118 (-O2), 104 to 112 (-O3) | 156 to 158 | 152 |
| Expansion<T, 2>, a point | 102 to 112 (-O2), 112 to 114 (-O3) | 113 to 117 (-O2), 104 to 112 (-O3) | 150 to 151 | 146 to 147 |
| T, a point | 15 to 16.4 (-O2), 16.4 to 16.8 (-O3) | 16.3 to 16.8 (-O2), 15.1 to 16.2 (-O3) | 16.4 | 16.3 to 16.4 |

| Horner, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| tp: `Interval<T, 1>` over `Ball<T, 1>` | 4.62 to 4.67 (-O2), 4.40 to 4.61 (-O3) | 3.89 to 3.98 (-O2), 3.95 to 4.25 (-O3) | 3.20 to 3.30 | 2.39 (-O2), 6.56 to 6.59 (-O3) |
| tp: `Interval<T, 2>` over `Ball<T, 2>` | 7.27 to 7.30 (-O2), 7.05 to 7.60 (-O3) | 6.89 to 7.26 (-O2), 7.45 to 7.73 (-O3) | 8.02 to 8.14 | 5.84 to 5.86 |
| tp: `Ball<T, 1>` over T | 40.6 to 41.2 (-O2), 41.2 to 43.2 (-O3) | 9.9 to 10.6 (-O2), 39.8 to 42.6 (-O3) | 18.0 to 18.2 (-O2), 93.8 to 94.0 (-O3) | 91.6 to 91.8 (-O2), 33.2 to 33.3 (-O3) |
| tp: `Ball<T, 2>` over `Expansion<T, 2>` | 1.29 to 1.32 (-O2), 1.29 to 1.34 (-O3) | 1.26 to 1.32 (-O2), 1.26 to 1.27 (-O3) | 1.06 to 1.07 | 1.07 |
| tp: `Interval<T, 1>`, fenv over Kairn | 4.48 to 4.82 (-O2), 4.65 to 5.07 (-O3) | 5.41 to 5.61 (-O2), 5.14 to 5.39 (-O3) | 2.33 to 2.40 (-O2), 2.40 to 2.42 (-O3) | 6.93 to 6.99 (-O2), 7.03 to 7.50 (-O3) |
| tp: `Interval<T, 1>`, Kairn over fenv_loop | 7.45 to 7.65 (-O2), 9.3 to 10.1 (-O3) | 6.36 to 6.49 (-O2), 6.83 to 6.86 (-O3) | 5.42 to 5.55 (-O2), 5.43 to 5.62 (-O3) | 5.79 to 5.84 (-O2), 6.75 to 6.77 (-O3) |
| lat: `Interval<T, 1>` over `Ball<T, 1>` | 5.01 to 5.04 | 4.11 to 4.29 (-O2), 4.08 to 4.42 (-O3) | 3.22 to 3.28 (-O2), 3.16 to 3.19 (-O3) | 2.49 to 2.51 |
| lat: `Interval<T, 2>` over `Ball<T, 2>` | 4.74 (-O2), 4.54 to 4.81 (-O3) | 4.30 to 4.54 (-O2), 4.76 to 5.03 (-O3) | 7.60 to 7.70 | 5.62 to 5.64 |
| lat: `Ball<T, 1>` over T | 1.65 to 1.77 (-O2), 1.61 to 1.65 (-O3) | 1.73 to 1.79 (-O2), 1.79 to 1.81 (-O3) | 4.85 to 4.89 | 4.64 to 4.67 |
| lat: `Ball<T, 2>` over `Expansion<T, 2>` | 0.99 to 1.02 | 0.96 to 1.00 | 1.04 to 1.05 | 1.03 to 1.04 |
| lat: `Interval<T, 1>`, fenv over Kairn | 4.36 to 4.47 | 4.94 to 5.20 (-O2), 4.98 to 5.04 (-O3) | 2.33 to 2.37 (-O2), 7.52 to 7.55 (-O3) | 3.18 to 3.19 (-O2), 8.33 to 8.43 (-O3) |
| lat: `Interval<T, 1>`, Kairn over fenv_loop | 3.60 to 3.85 (-O2), 4.25 to 4.32 (-O3) | 3.38 to 3.53 (-O2), 3.50 to 3.71 (-O3) | 7.40 to 7.53 (-O2), 7.28 to 7.33 (-O3) | 5.99 to 6.02 (-O2), 6.53 to 6.59 (-O3) |

### Question 5: the additions to `Ball`

| Times of the additions to Ball (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/ball_bounds_1/op` | 1.87 to 1.95 | 1.64 to 1.71 | 3.65 to 3.67 | 4.41 to 4.44 |
| `m2/tp/ball_bounds_2/op` | 3 to 3.09 | 2.48 to 2.58 | 5.44 to 5.55 | 8.33 to 8.37 |
| `m2/tp/ball_from_interval_2/op` | 3.06 to 3.19 | 3.38 to 3.42 (-O2), 2.44 to 2.48 (-O3) | 11.8 to 11.9 (-O2), 6.65 to 6.7 (-O3) | 11.6 to 11.7 |
| `m2/tp/ball_narrow_2_1/op` | 0.746 to 0.778 | 0.68 to 0.709 | 1.48 | 2.75 to 2.77 |
| `m2/tp/ball_half_1/op` | 2 to 2.06 (-O2), 2.12 to 2.17 (-O3) | 1.58 to 1.65 | 3.46 to 3.51 | 3.69 to 3.7 |
| `m2/tp/ball_half_2/op` | 2.16 to 2.25 | 1.37 to 1.42 (-O2), 1.6 to 1.64 (-O3) | 4.46 to 4.5 | 4.15 to 4.17 |
| `m2/tp/ball_scale_half_1/op` | 0.705 to 0.732 | 0.651 to 0.679 | 1.15 to 1.16 | 1.08 to 1.09 |
| `m2/tp/ball_scale_half_2/op` | 0.998 to 1.04 | 0.988 to 1.03 | 2.73 to 2.75 | 1.94 to 1.96 |
| `m2/tp/ball_ldexp_1/op` | 3.53 to 3.71 (-O2), 3.53 to 3.75 (-O3) | 2.19 to 2.29 (-O2), 2.16 to 2.2 (-O3) | 4.98 to 5.02 | 7.88 to 7.9 |
| `m2/tp/ball_ldexp_2/op` | 3.73 to 3.8 (-O2), 3.58 to 3.81 (-O3) | 2.33 to 2.4 | 6.56 to 6.72 | 8.14 to 8.19 |
| `m2/prod/ball_ldexp_2/op` | 7.37 to 7.54 | 3.04 to 3.17 | 6.81 to 6.89 | 10.2 |
| `m2/prod/ball_scale_pow2_2/op` | 3.61 to 3.94 (-O2), 3.87 to 3.95 (-O3) | 3.96 to 4.07 (-O2), 3.77 to 3.94 (-O3) | 5.8 to 5.85 | 5.62 to 5.64 |

### Question 6: `rational`

| kairn::rational, ns per call | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `rational<Expansion<T, 1>>`, small terms | 114 to 119 | 94.8 to 98.5 | 369 to 376 | 348 to 352 |
| `rational<Expansion<T, 1>>`, 64-bit terms | 115 to 119 (-O2), 119 to 121 (-O3) | 98.3 to 102 | 437 to 444 | 429 to 435 |
| `rational<Expansion<T, 2>>`, small terms | 176 to 181 | 142 to 148 (-O2), 147 to 149 (-O3) | 568 to 592 | 597 to 610 |
| `rational<Expansion<T, 2>>`, 64-bit terms | 172 to 188 (-O2), 186 to 191 (-O3) | 148 to 155 | 666 to 688 | 704 to 717 |
| `is_rational_result`, two limbs, 64-bit terms | 57.9 to 59 (-O2), 55.5 to 56.5 (-O3) | 83.6 to 86.6 (-O2), 48.3 to 49 (-O3) | 219 to 222 (-O2), 151 to 153 (-O3) | 158 to 161 |
| `T(num) / T(den)`, for scale | 0.165 to 0.169 | 0.155 to 0.162 | 1.52 to 1.54 | 0.764 to 0.799 |

### Question 7: the settings of `KAIRN_ENCLOSURE_CODE`

| mixed: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 0.39; 0.39 | 1.24; 1.34 | 3.51; 3.66 | 1.05; 1.05 |
| 100, outlined | 0.19; 0.20 | 0.39; 0.41 | 0.65; 0.68 | 0.64; 0.64 |
| 100, external | 0.12; 0.14 | 0.25; 0.26 | 0.41; 0.41 | 0.53; 0.53 |
| 100, calls | 0.04; 0.04 | 0.11; 0.12 | 0.09; 0.09 | 0.08; 0.08 |
| 1000, inline | 3.40; 3.42 | 11.1; 15.6 | 129; 140 | 8.49; 8.49 |
| 1000, outlined | 0.39; 0.39 | 1.30; 1.84 | 1.45; 1.44 | 1.12; 1.12 |
| 1000, external | 0.32; 0.33 | 0.98; 1.53 | 1.12; 1.16 | 1.01; 1.00 |
| 1000, calls | 0.21; 0.22 | 0.73; 1.20 | 0.68; 0.70 | 0.48; 0.47 |
| 10000, inline | 85.1; 84.3 | 434; – | stopped at 3600; stopped at 3600 | 524; 566 |
| 10000, outlined | 4.59; 4.84 | 23.7; – | 22.2; 24.1 | 14.0; 14.1 |
| 10000, external | 4.56; 4.72 | 25.1; – | 26.7; 27.5 | 14.0; 14.8 |
| 10000, calls | 4.29; 4.29 | 14.4; – | 20.7; 22.6 | 12.5; 12.5 |

| mixed: peak memory, MB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 79; 79 | 216; 219 | 152; 150 | 122; 121 |
| 100, outlined | 66; 66 | 99; 100 | 85; 85 | 122; 122 |
| 100, external | 59; 59 | 88; 88 | 76; 76 | 118; 118 |
| 100, calls | 38; 38 | 37; 37 | 32; 31 | 96; 96 |
| 1000, inline | 260; 260 | 941; 989 | 755; 756 | 223; 223 |
| 1000, outlined | 89; 89 | 183; 186 | 124; 125 | 128; 128 |
| 1000, external | 83; 83 | 170; 173 | 117; 116 | 125; 125 |
| 1000, calls | 64; 64 | 112; 114 | 70; 70 | 110; 110 |
| 10000, inline | 2257; 2263 | 12777; – |  | 5045; 5044 |
| 10000, outlined | 376; 388 | 1217; – | 544; 544 | 256; 258 |
| 10000, external | 368; 372 | 1212; – | 556; 556 | 256; 256 |
| 10000, calls | 330; 330 | 949; – | 471; 472 | 244; 244 |

| mixed: object, KB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 40; 40 | 49; 49 | 79; 79 | 67; 67 |
| 100, outlined | 13; 13 | 15; 15 | 26; 26 | 27; 27 |
| 100, external | 5; 5 | 7; 7 | 11; 11 | 10; 10 |
| 100, calls | 5; 5 | 6; 6 | 10; 10 | 9; 9 |
| 1000, inline | 358; 358 | 461; 465 | 779; 779 | 604; 607 |
| 1000, outlined | 57; 57 | 70; 69 | 96; 96 | 95; 95 |
| 1000, external | 50; 50 | 62; 61 | 80; 80 | 78; 78 |
| 1000, calls | 50; 50 | 54; 54 | 79; 79 | 78; 78 |
| 10000, inline | 3512; 3512 | 4767; – |  | 5876; 5894 |
| 10000, outlined | 485; 485 | 921; – | 789; 789 | 776; 777 |
| 10000, external | 478; 478 | 913; – | 773; 773 | 760; 760 |
| 10000, calls | 477; 477 | 812; – | 772; 772 | 759; 759 |

| mixed: run time of the unit, ns per operation (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 6.41 to 7.57; 6.37 to 7.93 | 5.87 to 6.03; 5.79 to 5.96 | 18.7 to 20.9; 18.9 to 19 | 16.1 to 16.2; 16.1 to 16.3 |
| 100, outlined | 6.56 to 8.71; 6.53 to 8.17 | 6.55 to 6.68; 6.57 to 6.58 | 20.2; 20 to 20.3 | 17.4 to 17.5; 17.4 to 17.5 |
| 100, external | 6.8 to 9.1; 6.58 to 8.25 | 6.55 to 6.69; 6.55 to 6.7 | 20.2; 20 to 20.2 | 17.4 to 17.5; 17.6 |
| 1000, inline | 6.37 to 7.36; 6.26 to 7.75 | 6.91 to 7.33; 7.04 to 7.22 | 20.1 to 21.2; 20.2 to 20.8 | 15.9 to 16; 16.1 to 16.2 |
| 1000, outlined | 6.75 to 8.27; 6.67 to 8.26 | 6.15 to 6.29; 6.19 to 6.32 | 19.2 to 19.6; 19.2 to 19.4 | 17.5; 17.5 |
| 1000, external | 6.58 to 8.36; 6.69 to 7.93 | 6.15 to 6.43; 6.19 to 6.21 | 19.3 to 19.5; 19.3 to 19.5 | 17.5; 17.5 to 17.6 |
| 10000, inline | 7.68 (one run); 6.43 (one run) | 8.9 (one run); – |  | 39.3 (one run); 38.9 (one run) |
| 10000, outlined | 6.82 (one run); 6.82 (one run) | 6.63 (one run); – | 22.2 (one run); 22.7 (one run) | 19.5 (one run); 19.8 (one run) |
| 10000, external | 6.86 (one run); 6.86 (one run) | 10.1 (one run); – | 23 (one run); 22.3 (one run) | 20.8 (one run); 19.4 (one run) |

| mixed: run time of the unit, first runs, ns per operation (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 6.41; 6.37 | 5.99; 5.88 | 30.5; 19.1 | 15.9; 16.1 |
| 100, outlined | 6.56; 6.53 | 6.68; 6.57 | 20.4; 35.9 | 18.1; 17.4 |
| 100, external | 6.8; 6.58 | 6.69; 6.55 | 20.2; 20.4 | 17.8; 17.4 |
| 1000, inline | 6.37; 6.26 | 6.91; 7.04 | 45; 21.7 | 35.5; 17.5 |
| 1000, outlined | 6.75; 6.67 | 6.15; 6.19 | 25.4; 19.7 | 17.5; 17.4 |
| 1000, external | 6.88; 6.69 | 6.15; 6.19 | 19.4; 19.6 | 19.7; 30.1 |
| 10000, inline | 7.68; 6.43 | 8.9; – |  | 38.3; 16.8 |
| 10000, outlined | 6.82; 6.82 | 6.63; – | 23.7; 26.6 | 20.1; 42.7 |
| 10000, external | 6.86; 6.86 | 10.1; – | 23.7; 25.8 | 67.1; 43.2 |

| interval2: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 0.44; 0.44 | 1.69; 1.86 | 4.41; 4.54 | 1.05; 1.06 |
| 100, outlined | 0.16; 0.16 | 0.40; 0.41 | 0.50; 0.51 | 0.58; 0.58 |
| 100, external | 0.13; 0.13 | 0.28; 0.29 | 0.36; 0.36 | 0.52; 0.52 |
| 100, calls | 0.04; 0.04 | 0.12; 0.13 | 0.07; 0.07 | 0.07; 0.07 |
| 1000, inline | 5.14; 5.09 | 15.1; 23.8 | 244; 234 | 9.18; 9.15 |
| 1000, outlined | 0.37; 0.34 | 1.50; 2.20 | 1.12; 1.06 | 1.01; 1.02 |
| 1000, external | 0.32; 0.31 | 1.20; 1.84 | 1.05; 1.03 | 0.93; 0.94 |
| 1000, calls | 0.20; 0.20 | 0.79; 1.41 | 0.71; 0.67 | 0.38; 0.39 |

| interval2: peak memory, MB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 83; 82 | 280; 275 | 161; 161 | 120; 120 |
| 100, outlined | 64; 64 | 97; 97 | 81; 81 | 120; 120 |
| 100, external | 59; 59 | 88; 88 | 75; 75 | 117; 117 |
| 100, calls | 38; 38 | 37; 38 | 31; 31 | 96; 96 |
| 1000, inline | 295; 294 | 1078; 1133 | 834; 835 | 227; 227 |
| 1000, outlined | 93; 93 | 198; 200 | 117; 117 | 126; 126 |
| 1000, external | 88; 87 | 189; 200 | 111; 112 | 122; 122 |
| 1000, calls | 70; 70 | 119; 122 | 67; 67 | 107; 107 |

| interval2: object, KB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 45; 45 | 66; 66 | 101; 101 | 70; 70 |
| 100, outlined | 9; 9 | 11; 11 | 18; 18 | 18; 18 |
| 100, external | 5; 5 | 6; 6 | 9; 9 | 8; 8 |
| 100, calls | 5; 5 | 5; 5 | 8; 8 | 8; 8 |
| 1000, inline | 413; 413 | 612; 614 | 992; 992 | 615; 615 |
| 1000, outlined | 54; 54 | 83; 75 | 78; 78 | 78; 78 |
| 1000, external | 50; 50 | 78; 70 | 69; 69 | 69; 69 |
| 1000, calls | 50; 50 | 52; 52 | 69; 69 | 68; 68 |

| interval2: run time of the unit, ns per operation (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 100, inline | 17.2 (one run); 16.6 (one run) | 13.7 (one run); 13.5 (one run) | 43.4 to 44.3; 43.2 to 44.6 | 37.8; 37.6 to 39 |
| 100, outlined | 18.2 (one run); 18.2 (one run) | 15.6 (one run); 15.5 (one run) | 44.9 to 45.2; 44.4 to 44.9 | 38.2 to 67.7; 38.4 to 39 |
| 100, external | 17.3 (one run); 17.3 (one run) | 15.9 (one run); 15.4 (one run) | 44.4 to 48.4; 44.5 to 45.3 | 38.3 to 38.9; 38.2 to 39 |
| 1000, inline | 17.1 (one run); 16.8 (one run) | 13.6 (one run); 13.8 (one run) | 52.7 to 101; 50 to 66.3 | 82.6 to 82.8; 37.7 to 82.8 |
| 1000, outlined | 17.9 (one run); 17.2 (one run) | 14.6 (one run); 15.1 (one run) | 43.8 to 43.9; 43.5 to 44 | 38.4 to 38.6; 38.3 to 39 |
| 1000, external | 17 (one run); 17.7 (one run) | 14.7 (one run); 15.1 (one run) | 44.3 to 54.8; 44 to 46.5 | 38.1 to 38.5; 38.3 to 38.4 |

| Outlined over inline | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop | 1.08 (-O2), 1.08 (-O3) | 1.99 (-O2), 2.04 (-O3) | 2.78 (-O2), 2.80 (-O3) | 1.07 (-O2), 1.08 (-O3) |
| `interval_mul_1`, loop | 1.09 (-O2), 1.05 (-O3) | 1.10 (-O2), 1.09 (-O3) | 2.15 (-O2), 2.16 (-O3) | 0.94 (-O2), 0.94 (-O3) |
| `interval_add_2`, loop | 0.91 (-O2), 0.99 (-O3) | 1.32 (-O2), 1.55 (-O3) | 1.10 (-O2), 1.08 (-O3) | 0.99 (-O2), 1.00 (-O3) |
| `interval_mul_2`, loop | 0.94 (-O2), 1.03 (-O3) | 1.03 (-O2), 1.03 (-O3) | 1.06 (-O2), 1.05 (-O3) | 0.99 (-O2), 1.00 (-O3) |
| `ball_add_2`, loop | 1.05 (-O2), 1.07 (-O3) | 1.05 (-O2), 1.13 (-O3) | 2.24 (-O2), 2.23 (-O3) | 1.91 (-O2), 2.99 (-O3) |
| `ball_mul_2`, loop | 1.11 (-O2), 1.12 (-O3) | 1.20 (-O2), 1.27 (-O3) | 2.45 (-O2), 2.44 (-O3) | 1.73 (-O2), 3.76 (-O3) |
| `interval_add_1`, chain | 1.56 (-O2), 1.64 (-O3) | 2.77 (-O2), 2.78 (-O3) | 1.95 (-O2), 1.96 (-O3) | 1.28 (-O2), 1.29 (-O3) |
| `interval_mul_1`, chain | 1.28 (-O2), 1.29 (-O3) | 1.72 (-O2), 1.70 (-O3) | 1.33 (-O2), 1.32 (-O3) | 1.17 (-O2), 1.17 (-O3) |
| `interval_mul_2`, chain | 1.01 (-O2), 1.09 (-O3) | 1.11 (-O2), 1.13 (-O3) | 1.21 (-O2), 1.21 (-O3) | 1.13 (-O2), 1.12 (-O3) |
| Horner, `Interval<T, 1>` | 1.32 (-O2), 1.48 (-O3) | 1.74 (-O2), 1.74 (-O3) | 1.88 (-O2), 1.59 (-O3) | 1.37 (-O2), 1.37 (-O3) |
| Horner, `Interval<T, 2>` | 1.09 (-O2), 1.13 (-O3) | 1.40 (-O2), 1.19 (-O3) | 1.10 (-O2), 1.08 (-O3) | 1.11 (-O2), 1.11 (-O3) |
| Horner, `Ball<T, 2>` | 1.54 (-O2), 1.54 (-O3) | 1.65 (-O2), 1.73 (-O3) | 1.84 (-O2), 1.84 (-O3) | 1.70 (-O2), 1.38 (-O3) |
| control: the kernel `interval_mul_1`, loop | 1.00 (-O2), 1.04 (-O3) | 0.98 (-O2), 1.00 (-O3) | 0.98 (-O2), 0.98 (-O3) | 0.99 (-O2), 0.99 (-O3) |

| External over inline | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `interval_add_1`, loop | 1.22 (-O2), 1.19 (-O3) | 1.85 (-O2), 2.05 (-O3) | 2.82 (-O2), 2.84 (-O3) | 1.06 (-O2), 1.08 (-O3) |
| `interval_mul_1`, loop | 1.06 (-O2), 1.04 (-O3) | 1.10 (-O2), 1.09 (-O3) | 2.20 (-O2), 2.19 (-O3) | 0.94 (-O2), 0.94 (-O3) |
| `interval_add_2`, loop | 1.00 (-O2), 1.00 (-O3) | 1.29 (-O2), 1.23 (-O3) | 1.09 (-O2), 1.10 (-O3) | 0.99 (-O2), 0.99 (-O3) |
| `interval_mul_2`, loop | 1.00 (-O2), 0.94 (-O3) | 1.02 (-O2), 1.03 (-O3) | 1.06 (-O2), 1.07 (-O3) | 0.99 (-O2), 1.00 (-O3) |
| `ball_add_2`, loop | 1.09 (-O2), 1.09 (-O3) | 1.06 (-O2), 1.13 (-O3) | 2.26 (-O2), 2.26 (-O3) | 1.93 (-O2), 2.99 (-O3) |
| `ball_mul_2`, loop | 1.19 (-O2), 1.18 (-O3) | 1.20 (-O2), 1.27 (-O3) | 2.47 (-O2), 2.48 (-O3) | 1.74 (-O2), 3.77 (-O3) |
| `interval_add_1`, chain | 1.67 (-O2), 1.61 (-O3) | 2.48 (-O2), 2.56 (-O3) | 1.98 (-O2), 1.99 (-O3) | 1.28 (-O2), 1.28 (-O3) |
| `interval_mul_1`, chain | 1.37 (-O2), 1.27 (-O3) | 1.62 (-O2), 1.61 (-O3) | 1.35 (-O2), 1.34 (-O3) | 1.16 (-O2), 1.15 (-O3) |
| `interval_mul_2`, chain | 1.08 (-O2), 1.01 (-O3) | 1.11 (-O2), 1.13 (-O3) | 1.22 (-O2), 1.21 (-O3) | 1.13 (-O2), 1.12 (-O3) |
| Horner, `Interval<T, 1>` | 1.41 (-O2), 1.39 (-O3) | 1.58 (-O2), 1.56 (-O3) | 1.89 (-O2), 1.92 (-O3) | 1.36 (-O2), 1.36 (-O3) |
| Horner, `Interval<T, 2>` | 1.10 (-O2), 1.04 (-O3) | 1.24 (-O2), 1.27 (-O3) | 1.11 (-O2), 1.12 (-O3) | 1.10 (-O2), 1.11 (-O3) |
| Horner, `Ball<T, 2>` | 1.54 (-O2), 1.44 (-O3) | 1.65 (-O2), 1.77 (-O3) | 1.86 (-O2), 1.86 (-O3) | 1.37 (-O2), 1.37 (-O3) |
| control: the kernel `interval_mul_1`, loop | 1.00 (-O2), 1.02 (-O3) | 0.93 (-O2), 1.00 (-O3) | 0.99 (-O2), 1.00 (-O3) | 0.99 (-O2), 0.98 (-O3) |

### Packed code

| Packed times (ns per number, interval or ball) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2p/tp/add_down_1/kairn` | 0.577 to 0.594 | 0.661 to 0.689 | 0.751 to 0.756 | 0.561 to 0.564 |
| `m2p/tp/mul_down_1/kairn` | 0.846 to 0.868 | 0.844 to 0.88 | 0.713 to 0.721 | 0.697 to 0.701 |
| `m2p/tp/next_up/kairn` | 0.546 to 0.557 | 0.382 to 0.397 | 0.311 to 0.314 | 0.292 to 0.294 |
| `m2p/tp/interval_add_1/kairn` | 1.54 to 1.59 | 1.47 to 1.54 | 1.64 to 1.65 | 1.25 to 1.26 |
| `m2p/tp/interval_mul_1/kairn` | 5.2 to 5.32 | 5 to 5.22 (-O2), 5.46 to 5.56 (-O3) | 4.72 to 4.76 | 4.3 to 4.33 |
| `m2p/tp/interval_add_2/kairn` | 5.26 to 5.36 | 5.21 to 5.29 (-O2), 5.03 to 5.12 (-O3) | 7.37 to 7.45 | 6.09 to 6.19 |
| `m2p/tp/interval_mul_2/kairn` | 17 to 17.4 | 17.4 to 18.2 (-O2), 15 to 15.3 (-O3) | 22.9 to 23.1 | 18.9 to 19.1 |
| `m2p/tp/ball_add_2/kairn` | 1.48 to 1.54 | 1.36 to 1.39 (-O2), 1.3 to 1.32 (-O3) | 1.9 to 1.92 | 1.79 to 1.8 |
| `m2p/tp/ball_mul_2/kairn` | 1.2 to 1.24 | 1.06 to 1.11 | 1.43 to 1.44 | 1.34 to 1.35 |
| `m2p/tp/interval_add_1/fenv_loop` | 0.508 to 0.518 | 0.507 to 0.528 | 1.04 to 1.05 | 1.05 |
| `m2p/tp/interval_mul_1/fenv_loop` | 0.719 to 0.733 | 0.717 to 0.747 | 1.32 to 1.33 | 1.31 to 1.32 |
| `m2p/tp/add/plain` | 0.154 to 0.157 | 0.155 to 0.162 | 0.154 to 0.155 | 0.153 to 0.154 |

### `float` limbs

| float limbs: float over double, and float ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add_down`, tp | 0.48 to 0.49 | 0.50 to 0.52 | 0.50 | 0.50 |
| `mul_down`, tp | 0.49 to 0.52 | 0.49 to 0.50 | 0.49 to 0.50 | 0.50 to 0.51 |
| `interval_add_1`, tp | 0.98 to 1.02 | 0.48 to 0.49 | 0.50 | 1.11 to 1.14 |
| `interval_mul_1`, tp | 1.03 to 1.04 (-O2), 0.99 to 1.01 (-O3) | 0.98 to 1.02 | 0.50 | 0.94 to 0.95 |
| `interval_add_2`, tp | 0.84 to 0.86 | 0.96 to 0.98 | 0.97 to 0.98 | 0.97 to 0.98 |
| `interval_mul_2`, tp | 0.97 to 1.01 | 0.99 to 1.02 | 0.94 to 0.95 | 1.05 to 1.08 |
| `ball_add_2`, tp | 0.98 to 1.02 | 1.01 to 1.04 | 0.99 to 1.00 | 1.83 to 1.84 |
| `ball_mul_2`, tp | 0.98 to 1.01 | 1.02 to 1.05 | 1.06 to 1.07 | 1.62 to 1.63 |
| `interval_add_1`, sum | 0.98 to 1.00 | 0.97 to 0.99 | 0.94 to 0.95 | 1.12 (-O2), 1.19 to 1.21 (-O3) |
| `interval_mul_1`, prod | 0.99 to 1.03 (-O2), 0.95 to 0.99 (-O3) | 0.98 to 1.01 | 0.98 to 1.00 | 1.15 to 1.16 |
| `horner_i1`, tp | 1.03 (-O2), 0.99 to 1.05 (-O3) | 1.00 to 1.02 | 0.96 to 0.98 | 1.00 to 1.01 |
| `horner_b1`, tp | 0.97 to 1.00 | 0.94 to 0.99 (-O2), 0.98 to 1.00 (-O3) | 0.95 to 0.96 | 1.22 (-O2), 2.76 to 2.77 (-O3) |
| `horner_i2`, tp | 1.00 to 1.05 | 1.02 to 1.08 (-O2), 1.00 to 1.03 (-O3) | 0.98 to 1.00 | 1.16 |
| `horner_b2`, tp | 0.97 to 1.01 | 0.95 to 0.99 (-O2), 0.95 to 1.00 (-O3) | 0.97 to 0.99 | 1.04 |
| `add_down`, loop: fenv over Kairn | 67.5 to 73.8 (-O2), 72.4 to 74.0 (-O3) | 60.0 to 62.0 (-O2), 55.6 to 59.9 (-O3) | 31.9 to 32.2 | 47.4 to 47.5 |
| `interval_mul_1`, loop: fenv over Kairn | 5.71 to 5.93 (-O2), 6.07 to 6.11 (-O3) | 4.49 to 4.63 (-O2), 4.61 to 4.64 (-O3) | 7.66 to 7.71 | 2.38 to 2.41 |
| `interval_mul_1`, loop: Kairn over fenv_loop | 4.38 to 4.51 (-O2), 3.08 to 3.16 (-O3) | 13.2 to 13.5 | 3.31 to 3.34 | 4.54 to 4.58 (-O2), 4.01 to 4.07 (-O3) |
| `interval_mul_1`, loop: interval over ball | 6.38 to 6.49 (-O2), 6.19 to 6.39 (-O3) | 17.6 to 18.6 (-O2), 18.3 (-O3) | 4.87 to 4.90 | 6.77 to 6.81 |
