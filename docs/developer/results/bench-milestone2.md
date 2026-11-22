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
It is the first part of the milestone's benchmarks; [the second part](#the-second-part)
(2026-11-22, commit `cbe3bb1`, the same machines and compilers) measures what reached `main` after it,
and [the third part](#the-third-part) (2026-11-22, on the tree of `25cde04`, on Zen 2 with GCC 13 and Clang 18) the
functions on arrays, the accumulator and the ball vectors, which reached `main` last
([Still to come](#still-to-come) says what no part measures).

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

- **Second part: `Packed` pays where the compiler does not vectorize the scalar loop itself.** A
  packed sum or product of two-limb `double` takes 0.25 to 0.37 of the scalar loop with GCC 13 on
  Zen 2 (4 lanes) and 0.59 to 0.89 on the M3 (2 lanes), of `float` 0.12 to 0.45; Clang 18
  vectorizes the scalar loop over arrays of limbs itself, and the two take the same time. One lane
  costs nothing, and the views and the element proxy nothing over raw pointers (both read an
  element through `from_limbs`, whose guards cost 8 to 34% of a loop of the kernel). Beyond the
  last-level cache Zen 2's packed loops are bound by memory, about 2.0 ns per element
  ([question 8](#8-packed-and-the-containers)).

- **Second part: a question to a ball costs more than the same question to an interval, and the
  set operations of balls are dear.** The three-valued comparisons take 0.7 to 3.3 ns for
  `Interval<double, 1>` and 1.7 to 7.0 for `Ball<double, 1>`, 1.0 to 7.0 and 3.8 to 19.6 with two
  limbs; the predicates 0.2 to 1.9 ns for every type. The hull and the intersection of balls, two
  conversions to intervals and one back, take 41 to 104 ns with two limbs, 32 to 55 times those of
  intervals. `midpoint()` and `radius()` together cost 1.0 to 1.6 times `mid_rad()` where the
  compiler inlines them, 2.0 to 2.2 times with Apple clang ([question 9](#9-the-enclosure-interface)).

- **Second part: for a generic client, `Ball<double, 1>`.** The tutorial's bisection finds the four
  zeros fastest with it on both machines, 3.2 to 8.8 µs to a width of $10^{-6}$; `Interval<double, 1>`
  takes 1.6 to 3.9 times as long, for final zeros at most six times narrower; `Ball<double, 2>` 3.5
  to 4.3 times as long as far as it goes, for 30 digits; `Interval<double, 2>` 21 to 31 times, for
  zeros three to four times narrower than those of `Ball<double, 2>`
  ([question 10](#10-one-algorithm-over-four-types)).

- **Second part: `self_test()` costs 2.5 to 8.8 µs at startup and 1.2 to 6.5 s to compile.** GCC 13
  compiles a unit with one call in 6.40 s at `-O2` and 6.50 s at `-O3`, which confirms the 6.6 s a
  downstream user measured (Milestone 1: 1.08 s); Clang 18 and GCC 16 in 3.9 to 4.0 s, Apple clang
  in 1.2 s; the generated header it compiles has grown four times. `KAIRN_CHECKS=1` multiplies the
  cheapest functions most: an interval's `contains(t)` takes 3.8 to 16.6 times as long (7.5 ns
  instead of 0.5 on Zen 2), a sum of intervals of one limb 2.1 to 3.5 times, a product of two limbs
  1.1 to 1.2 ([question 11](#11-self_test-and-the-checks)).

- **Second part: a function with thousands of comparisons of enclosures compiles slowly in every
  setting.** 1 000 calls of the three-valued comparisons take 4.5 s (Apple clang) to 62 s (GCC 13);
  10 000 take 134 s (GCC 16) to 26 minutes (Clang 18), and more than 30 minutes with GCC 13. The
  comparisons are forced inline and stay so in every setting of `KAIRN_ENCLOSURE_CODE`, which moves
  only the arithmetic; `hull`, `intersection` and `split()` compile in 5 to 25 s at 10 000
  ([question 12](#12-compile-time-of-the-enclosure-interface)).

- **Third part: an accurate sum costs 1.7 to 1.8 times Sum2, in the default order.** On Zen 2 a
  `sum` or `dot` of two limbs takes 2.6 to 2.9 ns per element; on data of `double` it costs 1.7 to
  1.8 times Sum2 (1.5 to 1.7 times Dot2), 7 times with `kairn::sequential`, and beyond a condition of
  $10^{15}$ its error is 4 to 500 times smaller than theirs. One limb costs what the loop of `double`
  in the same order costs (0.87 to 1.13 times), a quarter of the naive loop of one chain; the
  sequential order, the same bits on every machine, costs 3.7 to 4.5 times the default for `double`
  and 7 to 9 for `float` ([question 13](#13-the-functions-on-arrays),
  [question 17](#17-accuracy-for-the-price)).

- **Third part: the check at entry costs a call of a short array 5 to 6 ns on Zen 2, and a short
  ball vector more where it changes what the compiler inlines.** It is 64 to 82% of a `sum` or
  `dot` of one limb up to 8 elements, under 5% from 1 024 elements and under 1% from about 1 500 to
  2 700 (two limbs: under 5% from 4 to 16 elements). On the short ball vectors of a downstream
  user's report it costs most operations the read or less (1.01 to 1.26 times for `x + y` of two
  limbs, where the report has 1.2 to 3.0); more only for constructors whose body the compiler stops
  inlining with it (Clang 18: +18 to +20 ns, 4 times, for `BallVector<double, 1, 3>`; GCC 13 at
  `-O3` in a unit of many operations: +7 to +14 ns) or whose loops it places differently. A report
  of the check out of line and cold removes GCC's excess, and with the constructors forced inline
  Clang's (tried in a copy of the headers, not made)
  ([question 14](#14-short-arrays-and-the-check-at-entry)).

- **Third part: the guards of the factors a program supplies cost 0 to 17%**, nothing where the
  loop waits for a chain (`dot` of one limb 0.98 to 1.02, `add_product` 1.00 to 1.01), 14 to 17% for
  `scale` of two limbs, up to 15% for the product of short polynomials
  ([question 15](#15-the-guards-of-supplied-factors)). The accumulator costs what the sequential
  `sum` and `dot` cost, term by term ([question 16](#16-the-accumulator)).

- **Third part: a ball vector pays from about 16 entries.** At 16 entries an operation on a
  `BallVector` is 2 to 4 times faster than on as many balls on Zen 2, at 64 3.3 to 6.2 times, in
  0.53 to 0.75 of the bytes, and as wide where the entries have the same radius; at 4 entries it is
  no faster. Where the entries' radii differ, the one radius is the worst entry's: 1 to 2 times the
  largest ball's radius after a sum, up to 118 times after a product, and up to $10^6$ times the
  median ball's ([question 18](#18-one-radius-for-many-centers)). Each of the three
  headers costs a unit about a second to compile, and 1 000 calls 2.4 to 12 s
  ([question 19](#19-compile-time-of-the-functions-on-arrays-and-the-ball-vectors)).

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
   *Note (2026-11-22, second part):* on `main` at `aa168ee`, where `mid_rad()` is public and the
   kernel's call is forced inline into it, the two together cost 1.05 to 1.63 times `mid_rad()`
   with GCC 13, GCC 16 and Clang 18, which inline `midpoint()` and drop the radius's part, and 1.96
   to 2.20 times with Apple clang, which still calls each ([question 9](#9-the-enclosure-interface)).
   The figures above are those of `dee8ecd`, and stand for it.
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

## The second part

What reached `main` after the first part and was not measured there ([Still to
come](#still-to-come)), at commit `cbe3bb1` (`main` at `aa168ee` and the harness of this part, which
changes nothing under `include/`), 2026-11-22, on the same two machines and four compilers, `-O2`
and `-O3`, three runs of each configuration: `Packed` and the containers of `soa.hpp`
([question 8](#8-packed-and-the-containers)); the interface that `Interval` and `Ball` share
([question 9](#9-the-enclosure-interface)); one algorithm, the bisection of the tutorial, over
four enclosure types ([question 10](#10-one-algorithm-over-four-types)); `kairn::self_test()` and
the checks of `KAIRN_CHECKS` ([question 11](#11-self_test-and-the-checks)); and the compile time of
the interface ([question 12](#12-compile-time-of-the-enclosure-interface)). The harness is that of
the first part, four files more (`bench/m2_soa.cpp`, `m2_soa_scalar.cpp`, `m2_enc.cpp`,
`m2_run.cpp`; [bench/README.md](https://github.com/danielepanozzo/kairn/tree/main/bench),
"Milestone 2"), with the same driver, statistic and checks; the runs are the files
`soa-*`, `enc-*`, `bisect-*`, `checks-*`, `selftest-compile-*` and `compile-*-{compare,contains,setops}*`
of [`results/milestone2/bench/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/bench),
and every table below is printed from them by `python3 bench/m2_report.py --part 2
results/milestone2/bench` (the compile tables by the same script without `--part`). Names of
functions are those of the harness: `m2v` and `m2vf` the loops of `Packed` and the containers for
`double` and `float`, `m2v1` and `m2vf1` the same packed loops in the scalar form of `Packed` (one
lane), `m2e` and `m2ef` the enclosure interface, `m2r` whole computations; KIND `mem` a loop over
arrays that do not fit the last-level cache, `run` one call of a whole computation; variants `view`
(through `SoAView` and its element proxy), `packed` (`Packed<T, 2>` through `SoAView`), `aos` (an
array of `Expansion<T, 2>`).

### 8. `Packed` and the containers

Is the packed type worth it against the same loop in scalar code, and what do the views and the
element proxy cost? Loops over arrays of two-limb numbers held as `SoA<T, 2>` holds them, one array
per limb: $z = x + y$, $z = xy$, $z = xa$ with $a$ of one limb, the dot product of
[the tutorial](../../tutorials/vector-loop.md) (W sums, the lanes added in order at the end),
$z = x + ab$ with $a$ and $b$ of one limb, and a copy; in L1 (512 elements) and over arrays that do
not fit the last-level cache (4 Mi elements of `double`, 8 Mi of `float`: 192 MB for a sum, against
the 16 MB L3 of a Zen 2 core complex and the caches of the M3 Max); the time per element. The scalar
loop (`op`) reads each element with `from_limbs` through raw pointers, computes with
`Expansion<T, 2>` and stores the limbs; `view` is the same through `SoAView` and its element proxy;
`packed` loads and stores `Packed<T, 2>` through `SoAView`, the tail by `load_partial` and
`store_partial`. The controls are the same loop on `T` (one `+` or `*` of the leading limbs) and the
generated kernel called on the limbs (`kairn`). Everything is compiled with the flags of packed code
(`-mavx2 -mfma` on Zen 2), so that a compiler may vectorize the scalar loops at the same width as
`Packed`. W, the lanes of `Packed<T, 2>`, is 2 for `double` and 4 for `float` on the M3 (NEON), 4 and
8 on Zen 2 (AVX2).

| Packed over the scalar loop (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `x + y`, double, L1 | 0.71 to 0.72 | 0.59 to 0.61 | 0.25 | 1.00 to 1.01 |
| `x * y`, double, L1 | 0.89 | 0.70 to 0.71 | 0.32 | 1.00 to 1.01 |
| `x * a`, double, L1 | 1.07 to 1.08 | 0.81 | 0.37 | 1.00 |
| dot, W sums, over one sum in scalar code, double, L1 | 0.59 to 0.63 | 0.57 to 0.61 | 0.30 | 0.28 |
| dot, W sums, over the same in scalar code, double, L1 | 1.12 to 1.16 | 0.74 to 0.75 (-O2), 1.13 to 1.20 (-O3) | 0.31 | 0.68 (-O2), 0.31 (-O3) |
| `x + y`, float, L1 | 0.36 | 0.29 to 0.30 | 0.12 to 0.13 | 1.00 |
| `x * y`, float, L1 | 0.44 to 0.45 | 0.33 to 0.34 | 0.16 to 0.17 | 1.00 to 1.01 |
| `x + y`, double, memory | 0.70 | 0.59 | 0.36 to 0.37 | 1.00 to 1.01 |
| `x * y`, double, memory | 0.85 to 0.86 | 0.67 to 0.68 | 0.61 to 0.62 | 1.00 |
| `x + a * b`, two passes, double, L1 | 0.88 | 0.87 (-O2), 0.75 to 0.78 (-O3) | 0.38 (-O2), 0.31 (-O3) | 1.09 |
| `x + a * b`, two passes, double, memory | 0.90 | 0.78 to 0.79 (-O2), 0.74 to 0.75 (-O3) | 0.72 to 0.75 (-O2), 0.74 to 0.77 (-O3) | 1.34 to 1.42 (-O2), 1.35 to 1.39 (-O3) |
| `x + E2(a) * b` packed, one pass, over `x + a * b` scalar, double, L1 | 1.98 | 1.70 to 1.75 (-O2), 1.57 to 1.62 (-O3) | 0.92 (-O2), 0.81 (-O3) | 2.87 |

| Times of Packed and the containers, ns per element (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2v/tp/add11/plain` | 0.102 to 0.106 | 0.28 (-O2), 0.151 (-O3) | 0.318 to 0.321 (-O2), 0.0996 to 0.0998 (-O3) | 0.119 to 0.121 |
| `m2v/tp/add22/op` | 1.7 to 1.71 | 1.77 to 1.79 | 5.37 to 5.41 | 1.31 to 1.33 |
| `m2v/tp/add22/packed` | 1.22 | 1.06 to 1.09 | 1.35 to 1.36 | 1.32 to 1.33 |
| `m2v/tp/mul22/op` | 0.953 to 0.954 | 1.02 | 2.91 to 2.93 | 0.825 to 0.835 |
| `m2v/tp/mul22/packed` | 0.844 to 0.845 | 0.717 to 0.72 | 0.919 to 0.928 | 0.829 to 0.84 |
| `m2v/tp/dot22/op` | 7.62 to 7.81 | 7.74 to 7.9 | 10.3 to 10.4 | 10.2 to 10.4 |
| `m2v/tp/dotw/op` | 4.02 to 4.16 | 6.37 (-O2), 3.92 to 4.2 (-O3) | 9.9 to 9.99 | 4.22 to 4.27 (-O2), 9.29 to 9.38 (-O3) |
| `m2v/tp/dotw/packed` | 4.52 to 4.81 (-O2), 4.8 (-O3) | 4.7 to 4.75 (-O2), 4.45 to 4.75 (-O3) | 3.05 to 3.08 | 2.86 to 2.9 |
| `m2v/mem/add22/op` | 1.78 | 1.86 | 5.58 to 5.62 | 2.02 to 2.09 |
| `m2v/mem/add22/packed` | 1.25 | 1.09 to 1.11 | 2.02 to 2.09 | 2.02 to 2.1 |
| `m2v/mem/copy/kairn` | 0.279 to 0.289 | 1.26 to 1.33 (-O2), 0.278 to 0.29 (-O3) | 1.4 to 1.41 | 1.42 to 1.44 |

| The interfaces over the kernel on the limbs, L1 (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `x + y`, raw pointers, double | 1.17 (-O2), 1.17 to 1.26 (-O3) | 1.16 to 1.17 | 1.21 to 1.22 | 1.18 |
| `x + y`, view and proxy, double | 1.18 (-O2), 1.18 to 1.27 (-O3) | 1.17 | 1.21 to 1.22 | 1.18 |
| `x + y`, array of Expansion, double | 1.02 (-O2), 1.02 to 1.10 (-O3) | 0.98 to 0.99 | 1.00 | 3.81 to 3.83 |
| `x * y`, raw pointers, double | 1.32 to 1.34 | 1.32 | 1.27 | 1.22 to 1.23 |
| `x * y`, view and proxy, double | 1.32 to 1.34 | 1.32 | 1.27 | 1.22 to 1.23 |
| `x * y`, array of Expansion, double | 1.01 to 1.06 | 1.00 | 1.00 | 3.01 to 3.05 |
| copy, view and proxy, double | 1.00 to 1.01 | 1.04 to 1.06 (-O2), 0.99 to 1.00 (-O3) | 1.00 to 1.01 | 1.00 |

- **With GCC and Apple clang the packed type is worth it; with Clang 18 it gains nothing over the
  scalar loop, which Clang vectorizes itself.** In L1, the packed loop of a sum or a product of
  `double` takes 0.25 to 0.37 of the scalar loop on Zen 2 with GCC 13 (4 lanes), and 0.59 to 0.89 on
  the M3 (2 lanes); of `float`, 0.12 to 0.18 and 0.29 to 0.45 (8 and 4 lanes). The product by a
  number of one limb gains least: 0.37 with GCC 13, 0.81 with GCC 16, and 1.07 to 1.08 with Apple
  clang, whose scalar loop of that product is short (21 instructions per element) and already fast
  (0.63 ns). With Clang 18 the packed and the scalar loops take the same time (1.00 to 1.01): Clang
  vectorizes the scalar loop over the arrays of limbs, 256-bit, the generated kernel and
  `Expansion`'s operator alike, so a sum of `double` takes 1.3 ns per element in either form, where
  GCC 13's scalar loop, which stays scalar, takes 5.4 ns. GCC 13, GCC 16 and Apple clang vectorize
  none of the scalar loops ([machine code](#what-the-machine-code-shows-second-part)).
- **One lane costs nothing; the gain is the lanes.** `Packed` in its scalar form
  (`KAIRN_PACKED_FORM_SCALAR`, [Packed of one lane](#question-8-packed-and-the-containers)) takes
  0.94 to 1.07 of the scalar loop in every configuration. Where the scalar loop is not vectorized,
  W lanes give 2.7 to 4.0 times on Zen 2 with W = 4 and 5.6 to 8.3 with W = 8 (GCC 13), and 0.93 to 1.7
  times on the M3 with W = 2 and 1.9 to 3.4 with W = 4.
- **The tutorial's dot product** takes 0.28 to 0.31 of the scalar loop with one sum on Zen 2 and
  0.57 to 0.63 on the M3 (`float`: 0.12 to 0.16 and 0.30 to 0.33): W sums break the chain of the
  one-sum loop, whose step (7.6 to 10.4 ns) waits for the sum before. Against the same W sums written
  in scalar code, it gains on Zen 2 (0.31; 0.68 with Clang 18 at `-O2`) and **loses on the M3**: 1.12
  to 1.16 with Apple clang, 1.13 to 1.20 with GCC 16 at `-O3`. There the packed loop is one dependent
  chain of packed sums, 8.9 to 9.6 ns a step for two elements, longer than the 7.6 to 7.9 ns of a
  scalar chain for one; and the scalar loop's two chains run side by side, 3.9 to 4.2 ns per element.
- **Beyond the last-level cache** the M3 stays compute-bound (every loop of two limbs within 1.02 to
  1.10 of its time in L1), and so do the scalar loops of GCC 13 (1.04 to 1.14). The packed loops of
  Zen 2 meet the memory: a sum or a product of `double` takes 2.0 to 2.1 ns per element with both
  compilers, 1.5 to 2.4 times its time in L1, about what one core's stream of 48 bytes per element
  allows there (a copy of two limbs takes 1.4 ns); packed over scalar becomes 0.36 for the sum and
  0.61 for the product with GCC 13. A packed copy gains only where the compiler left the scalar copy
  scalar (GCC at `-O2`).
- **The views cost nothing over raw pointers; reading an element costs its guards.** A loop through
  `SoAView` and its proxy takes what the same loop through raw pointers takes, within 1%, and both
  1.08 to 1.34 times the generated kernel on the limbs: each read of an element is `from_limbs`,
  which guards each limb (an addition of $+0$, rule R3 of `expansion.hpp`), four additions more per
  sum of two elements. An array of `Expansion<T, 2>`, whose elements are not read through
  `from_limbs`, takes 0.98 to 1.10 times the kernel with GCC and Apple clang, and 3.0 to 7.7 times
  with Clang 18, which does not vectorize that loop. A copy through the proxy costs what a copy of
  the limbs costs (0.93 to 1.06).
- **`Packed<T, 1>` has no arithmetic**, and what that costs a loop that mixes one-limb and
  two-limb data depends on what the loop computes. For $z = x + ab$ with the product rounded to `T`,
  as `Expansion<T, 1>` computes it, a packed loop computes the products in a plain loop of `T` first
  and the packed sums after: for `double`, 0.74 to 0.90 of the scalar loop on the M3, 0.31 to 0.38 with GCC 13 in
  L1 and 0.72 to 0.77 beyond the cache, but 1.08 to 1.10 with Clang 18 in L1 and 1.33 to 1.42 beyond
  the cache, where the second pass is a second stream through memory. In one pass a packed loop can
  only make $a$ a number of two limbs, $x + \mathrm{Expansion}(a)\,b$: a product of two limbs by one,
  more accurate and dearer, 1.45 to 1.98 times the scalar loop of the rounded product on the M3 and
  1.4 to 2.9 times with Clang 18 (0.81 to 0.97 with GCC 13).

### 9. The enclosure interface

What does a question about an interval or a ball cost, the same question for each of the four types
a generic client may pick, and what do the set operations cost? Each function of the shared
interface ([One enclosure interface](../../reference/enclosure.md)) in a loop over 256 operands (KIND
`tp`) for `Interval<T, 1>`, `Interval<T, 2>`, `Ball<T, 1>` and `Ball<T, 2>`, `double` limbs (`float`
in [the tables](#question-9-the-enclosure-interface)), and in a dependent chain for those that return
a set (KIND `step`: a running hull, a running intersection, `x = x.split().left` started again every
32 steps, and the conversion to the other kind and back). The operands make every answer occur: of a
comparison, yes, no and unknown in turn (Y shifted from X by 6 or 1 half-widths, or not at all); of
`contains`, a point or a set inside X for half of them. The controls: the generated kernel called on
the limbs (`kairn`), and, for one limb, the same question in plain arithmetic of `T` (`plain`: a
comparison of bounds, and $c - r$, $c + r$ rounded to nearest for a ball); the set operations of a
ball, whose plain forms compute other values, against plain kernels of their own (the hull and the
intersection of $c \pm r$, the split at the center), and the midpoint, `split()` and the conversions
of an interval against $(l + h)/2$, $(h - l)/2$ (`m2/tp/plain_midrad_1` of the first part).

| Predicates and comparisons of `Interval<T, 1>`, ns per operation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.164 | 0.317 (-O2), 0.179 to 0.18 (-O3) | 1.02 to 1.03 (-O2), 0.225 (-O3) | 0.507 to 0.515 |
| `is_whole()` | 0.224 to 0.234 | 0.234 (-O2), 0.248 to 0.267 (-O3) | 0.376 to 0.38 | 0.629 to 0.639 |
| `certainly_positive()` | 0.573 to 0.579 | 0.332 to 0.335 (-O2), 0.236 to 0.246 (-O3) | 1.31 to 1.32 (-O2), 0.334 (-O3) | 1.34 to 1.37 |
| `certainly_zero()` | 0.234 | 0.227 to 0.234 (-O2), 0.266 (-O3) | 0.375 to 0.379 | 0.629 to 0.639 |
| `contains(t)` | 0.35 to 0.351 | 0.336 to 0.351 | 0.529 to 0.535 | 0.5 to 0.511 |
| `contains(Y)` | 0.306 | 0.367 (-O2), 0.333 (-O3) | 0.607 to 0.614 | 0.925 to 0.938 |
| `less` | 0.662 | 0.801 to 0.811 | 1.94 to 1.97 | 1.99 to 2.01 |
| `less_equal` | 0.662 | 0.787 to 0.808 | 1.94 to 1.97 | 1.99 to 2.02 |
| `equal` | 0.827 to 0.83 | 0.937 to 0.939 | 3.28 to 3.32 | 2.17 to 2.2 |
| `member(t, X)` | 0.368 | 0.306 to 0.31 (-O2), 0.32 to 0.335 (-O3) | 0.493 to 0.498 | 0.505 to 0.512 |
| `ieee1788::equal` | 0.185 | 0.367 (-O2), 0.333 (-O3) | 0.609 to 0.614 | 0.579 to 0.587 |
| `ieee1788::interior` | 0.664 | 0.715 to 0.716 (-O2), 0.666 to 0.667 (-O3) | 1.21 to 1.22 | 1.25 to 1.27 |
| `ieee1788::disjoint` | 0.465 | 0.51 to 0.533 (-O2), 0.467 (-O3) | 0.758 to 0.766 | 1.23 to 1.24 |

| Predicates and comparisons of `Interval<T, 2>`, ns per operation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.319 | 0.317 (-O2), 0.345 (-O3) | 0.999 to 1.03 | 0.505 to 0.514 (-O2), 0.488 to 0.497 (-O3) |
| `is_whole()` | 0.382 to 0.391 | 0.297 (-O2), 0.416 (-O3) | 1.85 to 1.87 (-O2), 0.536 to 0.537 (-O3) | 0.628 to 0.637 |
| `certainly_positive()` | 1.03 (-O2), 0.961 to 1.03 (-O3) | 0.333 to 0.335 (-O2), 0.412 (-O3) | 1.32 to 1.34 | 1.35 to 1.36 |
| `certainly_zero()` | 0.38 to 0.39 | 0.298 to 0.299 (-O2), 0.415 to 0.416 (-O3) | 1.39 to 1.4 (-O2), 0.503 to 0.504 (-O3) | 0.627 to 0.638 |
| `contains(t)` | 0.88 | 0.903 to 0.907 | 1.59 to 1.6 | 0.919 to 0.935 |
| `contains(Y)` | 0.994 | 0.988 to 0.999 | 2.09 to 2.11 | 2.21 to 2.26 |
| `less` | 1.09 | 0.988 to 0.996 | 3.87 to 3.92 | 2.43 to 2.47 |
| `less_equal` | 1.09 | 0.988 to 0.998 | 3.87 to 3.92 | 3.07 to 3.12 |
| `equal` | 1.66 to 1.74 | 1.84 to 1.86 | 6.9 to 6.98 | 4.73 to 4.84 |
| `member(t, X)` | 0.904 to 0.905 | 1.06 to 1.08 | 3.61 to 3.66 | 0.905 to 0.917 |
| `ieee1788::equal` | 0.56 to 0.561 (-O2), 0.522 to 0.56 (-O3) | 0.843 to 0.86 | 1.98 to 2 | 0.5 to 0.51 |
| `ieee1788::interior` | 1.47 | 1.33 to 1.34 | 2.45 to 2.47 | 3.1 to 3.15 |
| `ieee1788::disjoint` | 1.07 | 1.12 to 1.14 | 2.24 to 2.26 | 2.68 to 2.72 |

| Predicates and comparisons of `Ball<T, 1>`, ns per operation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.16 to 0.164 | 0.309 to 0.313 (-O2), 0.18 (-O3) | 0.629 to 0.635 (-O2), 0.225 to 0.226 (-O3) | 0.496 to 0.51 |
| `is_whole()` | 0.157 to 0.164 | 0.335 (-O2), 0.173 to 0.18 (-O3) | 1.11 to 1.13 (-O2), 0.225 (-O3) | 0.512 to 0.523 |
| `certainly_positive()` | 0.167 | 0.167 (-O2), 0.178 to 0.183 (-O3) | 0.318 to 0.322 | 0.605 to 0.615 |
| `certainly_zero()` | 0.234 | 0.234 (-O2), 0.266 (-O3) | 0.375 to 0.379 | 0.63 to 0.639 |
| `contains(t)` | 0.705 to 0.731 | 0.823 to 0.864 | 1.74 to 1.76 | 0.897 to 0.907 |
| `contains(Y)` | 2.01 to 2.13 (-O2), 2 to 2.13 (-O3) | 1.36 to 1.38 | 2.73 to 2.76 | 3.06 to 3.1 |
| `less` | 2.06 to 2.13 | 2.03 (-O2), 2.37 to 2.38 (-O3) | 6.74 to 6.96 | 4.03 to 4.07 |
| `less_equal` | 2.13 | 2.07 to 2.09 | 6.32 to 6.48 | 4.08 to 4.13 |
| `equal` | 2.39 (-O2), 2.24 to 2.39 (-O3) | 1.68 to 1.72 | 5.79 to 5.88 | 3.94 to 3.99 |
| `member(t, X)` | 0.715 to 0.731 | 0.778 to 0.819 (-O2), 0.814 (-O3) | 1.7 to 1.72 | 0.908 to 0.919 |

| Predicates and comparisons of `Ball<T, 2>`, ns per operation | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.175 to 0.18 | 0.3 (-O2), 0.196 (-O3) | 0.23 to 0.232 | 0.51 to 0.52 |
| `is_whole()` | 0.163 to 0.166 | 0.299 (-O2), 0.196 (-O3) | 0.239 to 0.242 | 0.506 to 0.523 |
| `certainly_positive()` | 0.303 to 0.317 | 0.331 to 0.334 | 0.625 to 0.632 | 0.936 to 0.955 |
| `certainly_zero()` | 0.304 | 0.33 (-O2), 0.349 (-O3) | 0.586 to 0.593 | 1.33 to 1.35 |
| `contains(t)` | 2.6 | 2.46 (-O2), 2.24 to 2.25 (-O3) | 8.51 to 8.6 (-O2), 5.55 to 5.56 (-O3) | 7.92 to 8.02 |
| `contains(Y)` | 4.52 (-O2), 4.11 to 4.26 (-O3) | 3.65 (-O2), 3.13 to 3.14 (-O3) | 14.3 to 14.4 (-O2), 6.93 to 6.94 (-O3) | 15 to 15.2 |
| `less` | 6.21 to 6.23 | 4.94 to 5.03 | 16.3 to 16.5 | 19.3 to 19.6 |
| `less_equal` | 6.22 to 6.23 | 4.93 to 5 | 16 to 16.2 | 19.5 to 19.7 |
| `equal` | 4.78 to 4.94 | 3.76 to 3.77 | 13.3 to 13.6 | 13.1 to 13.3 |
| `member(t, X)` | 4.2 to 4.21 | 4.09 to 4.2 | 14.5 to 14.7 | 10.9 to 11.1 |

| Ball over interval, two limbs over one (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `contains(t)`, `Ball<T, 1>` over `Interval<T, 1>` | 2.06 to 2.09 (-O2), 2.01 to 2.09 (-O3) | 2.50 to 2.53 (-O2), 2.34 to 2.46 (-O3) | 3.28 to 3.29 | 1.78 to 1.79 |
| `contains(t)`, `Ball<T, 2>` over `Interval<T, 2>` | 2.95 to 2.96 | 2.71 to 2.72 (-O2), 2.48 (-O3) | 5.36 to 5.37 (-O2), 3.47 to 3.50 (-O3) | 8.57 to 8.62 |
| `less`, `Ball<T, 1>` over `Interval<T, 1>` | 3.22 (-O2), 3.11 to 3.22 (-O3) | 2.52 to 2.53 (-O2), 2.92 to 2.95 (-O3) | 3.46 to 3.55 | 2.02 to 2.03 |
| `less`, `Ball<T, 2>` over `Interval<T, 2>` | 5.69 to 5.71 | 4.97 to 5.09 | 4.16 to 4.22 | 7.92 to 7.98 |
| `less`, `Interval<T, 2>` over `Interval<T, 1>` | 1.65 | 1.22 to 1.24 | 1.99 to 2.02 | 1.22 to 1.23 |
| `less`, `Ball<T, 2>` over `Ball<T, 1>` | 2.91 to 2.92 (-O2), 2.92 to 3.02 (-O3) | 2.44 (-O2), 2.11 to 2.12 (-O3) | 2.37 to 2.42 | 4.78 to 4.82 |
| `hull`, `Ball<T, 1>` over `Interval<T, 1>` | 16.6 | 12.9 to 13.5 (-O2), 13.9 to 15.5 (-O3) | 31.1 to 31.5 | 28.0 to 28.2 |
| `hull`, `Ball<T, 2>` over `Interval<T, 2>` | 33.4 to 33.8 | 32.5 to 34.8 (-O2), 31.9 to 32.1 (-O3) | 32.4 to 34.1 (-O2), 32.3 to 32.6 (-O3) | 54.5 to 54.8 |
| `split()`, `Ball<T, 1>` over `Interval<T, 1>` | 1.14 (-O2), 1.05 to 1.06 (-O3) | 0.62 to 0.64 (-O2), 0.74 to 0.75 (-O3) | 0.44 to 0.45 (-O2), 0.51 to 0.52 (-O3) | 0.86 to 0.87 |
| `split()`, `Ball<T, 2>` over `Interval<T, 2>` | 0.91 to 0.95 | 0.71 to 0.75 | 0.87 to 0.88 (-O2), 0.57 (-O3) | 0.85 |

| midpoint() and radius() against mid_rad() (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<T, 1>`: `midpoint()` over `mid_rad()` | 1.00 to 1.07 (-O2), 1.00 (-O3) | 0.22 to 0.23 (-O2), 0.31 (-O3) | 0.27 to 0.31 | 0.29 |
| `Interval<T, 1>`: `radius()` over `mid_rad()` | 1.00 to 1.08 (-O2), 0.98 (-O3) | 0.96 to 0.98 | 1.30 to 1.31 (-O2), 1.13 to 1.14 (-O3) | 0.96 |
| `Interval<T, 1>`: both over `mid_rad()` | 2.05 to 2.20 (-O2), 1.96 (-O3) | 1.05 to 1.06 (-O2), 1.25 (-O3) | 1.61 to 1.63 (-O2), 1.07 (-O3) | 1.22 to 1.23 |
| `Interval<T, 2>`: `midpoint()` over `mid_rad()` | 0.37 to 0.39 | 0.38 to 0.40 (-O2), 0.22 to 0.23 (-O3) | 0.38 (-O2), 0.18 (-O3) | 0.31 |
| `Interval<T, 2>`: `radius()` over `mid_rad()` | 0.97 to 1.02 | 0.97 to 1.00 (-O2), 1.00 to 1.08 (-O3) | 0.91 | 0.98 |
| `Interval<T, 2>`: both over `mid_rad()` | 1.31 to 1.32 | 1.30 to 1.34 (-O2), 1.01 to 1.08 (-O3) | 1.31 to 1.33 | 1.26 to 1.27 |

- **A predicate costs a comparison or two**: `is_empty()`, `is_whole()` and the signs take 0.16 to
  1.9 ns for every type (for a ball, `is_empty()` and `is_whole()` are tests of the radius, with no
  kernel), and so does `contains(t)` but for a ball of two limbs, which computes $t - c$ as a
  two-limb difference (2.2 to 8.6 ns; one limb 0.7 to 1.8, intervals 0.3 to 1.6). Against the same
  question asked in plain arithmetic of `T`, an interval's exact predicates take 0.37 to 3.5 times as
  long, and are often faster: the plain forms, written with `&&` and `||`, branch on answers that
  change from one element to the next, where the kernels compare and select. A ball's tests that
  need its bounds, $c - r$ and $c + r$ as exact pairs, take 1.9 to 7.4 times their plain forms.
- **The three-valued comparisons**: `less`, `less_equal` and `equal` take 0.66 to 3.3 ns for
  `Interval<T, 1>`, 1.0 to 7.0 for `Interval<T, 2>`, 1.7 to 7.0 for `Ball<T, 1>` and 3.8 to 19.6 for
  `Ball<T, 2>`. A ball costs 1.8 to 3.6 times an interval of the same limbs with one limb and 1.9 to
  8.0 with two; two limbs cost 1.2 to 2.2 times one for intervals and 2.0 to 4.8 for balls. An
  interval's comparison is comparisons of bounds, exact; a ball's computes its bounds as exact pairs
  (one limb) or rounds them outward (two limbs), and for two limbs is only certain.
- **`hull` and `intersection` of balls are dear**: 5.7 to 24 ns for one limb and 41 to 104 ns for
  two, 13 to 31 and 32 to 55 times the same operation on intervals (0.40 to 0.82 and 1.2 to 4.2 ns,
  which take what a min and a max take), and 9 to 29 times the plain hull of $c \pm r$. Their kernel
  is what the documentation says it is: both balls converted to intervals, the operation, and the
  result converted back, three conversions; the public function costs what its kernel costs (0.92 to
  1.14, but 1.70 and 2.26 with Clang 18, which calls it). In a chain, a step of the hull of balls of
  two limbs takes 66 to 116 ns. `split()` is the other way round: a ball's, two sums of balls,
  costs 0.44 to 1.14 times an interval's, which computes the midpoint (one limb 1.6 to 10.9 ns, two
  limbs 4.7 to 23.5).
- **`midpoint()` and `radius()` each run the kernel of both, as documented, but what each costs
  depends on whether the compiler inlines it.** GCC 13, GCC 16 and Clang 18 inline `midpoint()`
  and drop the radius's part: it takes 0.18 to 0.40 of `mid_rad()`; `radius()` takes 0.91 to 1.31 of
  it, and the two together 1.01 to 1.63 times `mid_rad()`. Apple clang calls
  `midpoint()` and `radius()`, one call of each per element, and for one limb each call costs the
  whole kernel: together 1.96 to 2.20 times `mid_rad()` (for two limbs 1.31 to 1.32).
  `mid_rad()` costs its kernel (0.89 to 1.32). For a ball the three read stored limbs (0.18 to
  0.94 ns).
- **The conversions**: an interval to a ball 2.8 to 11 ns (one limb) and 12 to 32 ns (two); a ball
  to an interval 1.6 to 4.6 and 6.7 to 32 ns.
- **The public functions cost their kernels**: over every loop of `m2e` that has both, the median
  ratio is 1.00 in every configuration; the largest, 2.0 to 2.3, are members that a compiler calls
  rather than inlines in a loop whose kernel it vectorizes or schedules better
  ([machine code](#what-the-machine-code-shows-second-part)).
- **`float`** costs about what `double` costs for the comparisons, the splits and the conversions
  (0.69 to 1.14; GCC's conversion of a ball of one limb 0.49 to 0.50), and about half where a
  compiler vectorizes the loop with twice the lanes: about half for `contains(t)` (0.44 to 0.57, but 0.76 to 1.00 in three cells) and
  the hull of intervals (0.48 to 0.71, but 1.26 to 1.60 with the two Linux compilers for two limbs),
  and Apple clang's `less` of intervals of one limb (0.48) ([float over double](#question-9-the-enclosure-interface)).

### 10. One algorithm over four types

Which enclosure type should a generic client pick, and at which number of limbs? The bisection of
[Zeros of a polynomial by bisection](../../tutorials/bisection.md), its program
`docs/examples/cpp/bisection.cpp` compiled into the harness as it is (its `main` renamed;
`bench/m2_run.cpp`): the zeros of $x^4 - 10x^2 + 1$ in $[-4, 4]$, down to the tutorial's two widths,
$10^{-6}$ and 0 (as far as each type's test of progress lets it go), with the tutorial's three types
and `Interval<double, 2>`, which the same template accepts. What it ran is the tutorial's `zeros()`
and `clusters()`, its vectors and its allocations included; the time is that of one call, to
solution; before timing, each run is checked by the tutorial's own `verify()` (four zeros, in
order, each near one of $\pm\sqrt2 \pm\sqrt3$, $p$ not of one sign on any). The tutorial's run
finishes in 3 to 520 µs, timed in samples of about 4 ms like every function of the harness.

| Bisection: what each type found | Width | Evaluations | Parts kept | Not narrowed by split() | Zeros | Radius of the zeros |
|---|---|---:|---:|---:|---:|---|
| `Interval<double, 1>` | 1e-06 | 167 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Interval<double, 1>` | 0 | 435 | 6 | 6 | 4 | 1.11e-16 to 4.44e-16 |
| `Interval<double, 2>` | 1e-06 | 167 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Interval<double, 2>` | 0 | 943 | 44 | 44 | 4 | 3.39e-32 to 2.71e-31 |
| `Ball<double, 1>` | 1e-06 | 179 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Ball<double, 1>` | 0 | 443 | 10 | 10 | 4 | 2.78e-16 to 2.67e-15 |
| `Ball<double, 2>` | 1e-06 | 179 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Ball<double, 2>` | 0 | 875 | 16 | 16 | 4 | 1.17e-31 to 1.01e-30 |

| Bisection: time to solution, microseconds | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<double, 1>`, width 1e-6 | 12.5 to 12.8 | 8.36 to 8.37 (-O2), 7.85 to 8.05 (-O3) | 15.6 to 15.9 (-O2), 14.1 to 14.2 (-O3) | 22.3 to 22.9 |
| `Interval<double, 2>`, width 1e-6 | 45.9 to 49.5 (-O2), 46 to 48.7 (-O3) | 38.6 to 41 (-O2), 37.9 to 40.6 (-O3) | 85.6 to 87.2 | 82 to 84.7 |
| `Ball<double, 1>`, width 1e-6 | 3.25 to 3.36 (-O2), 3.19 to 3.24 (-O3) | 3.72 to 3.85 (-O2), 3.9 to 3.98 (-O3) | 8.58 to 8.82 | 8.25 to 8.6 |
| `Ball<double, 2>`, width 1e-6 | 6.67 to 7 (-O2), 6.57 to 6.92 (-O3) | 7.13 to 7.61 (-O2), 6.99 to 7.56 (-O3) | 16.5 to 16.8 | 15.4 to 15.7 |
| `Interval<double, 1>`, width 0 | 32.2 to 33.2 | 22.2 to 22.3 (-O2), 20.7 to 21.3 (-O3) | 46.8 to 48 (-O2), 42.2 to 42.5 (-O3) | 58.2 to 59.8 |
| `Interval<double, 2>`, width 0 | 257 to 281 (-O2), 257 to 276 (-O3) | 219 to 235 (-O2), 218 to 229 (-O3) | 506 to 516 | 461 to 476 |
| `Ball<double, 1>`, width 0 | 9.1 to 9.37 (-O2), 8.83 to 8.88 (-O3) | 9.44 to 10.1 (-O2), 10.3 to 10.4 (-O3) | 22.2 to 22.7 | 21.5 to 21.8 (-O2), 20.7 to 21 (-O3) |
| `Ball<double, 2>`, width 0 | 35.2 to 37.9 (-O2), 35.1 to 37.8 (-O3) | 36.8 to 39.5 (-O2), 36.1 to 39.5 (-O3) | 84 to 85.5 | 78.3 to 79.8 |

| Bisection: time to solution over that of Ball<double, 1> | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<double, 1>` over `Ball<double, 1>`, width 1e-6 | 3.80 to 3.90 | 2.17 to 2.25 (-O2), 2.01 to 2.03 (-O3) | 1.81 to 1.83 (-O2), 1.61 to 1.62 (-O3) | 2.63 to 2.64 (-O2), 2.73 (-O3) |
| `Interval<double, 2>` over `Ball<double, 1>`, width 1e-6 | 14.0 to 14.7 (-O2), 14.4 to 15.0 (-O3) | 10.4 to 11.0 (-O2), 9.7 to 10.2 (-O3) | 9.81 to 9.98 | 9.66 to 9.68 (-O2), 10.1 (-O3) |
| `Ball<double, 1>` over `Ball<double, 1>`, width 1e-6 | 1.00 | 1.00 | 1.00 | 1.00 |
| `Ball<double, 2>` over `Ball<double, 1>`, width 1e-6 | 2.05 to 2.08 (-O2), 2.06 to 2.16 (-O3) | 1.91 to 1.98 (-O2), 1.79 to 1.90 (-O3) | 1.88 to 1.94 | 1.82 to 1.87 |
| `Interval<double, 2>` over `Ball<double, 2>`, width 1e-6 | 6.79 to 7.08 (-O2), 6.77 to 7.05 (-O3) | 5.40 to 5.75 (-O2), 5.36 to 5.43 (-O3) | 5.15 to 5.20 | 5.30 to 5.41 |
| `Interval<double, 1>` over `Ball<double, 1>`, width 0 | 3.54 to 3.58 (-O2), 3.63 to 3.66 (-O3) | 2.20 to 2.36 (-O2), 2.02 to 2.04 (-O3) | 2.09 to 2.13 (-O2), 1.87 to 1.88 (-O3) | 2.71 (-O2), 2.84 to 2.85 (-O3) |
| `Interval<double, 2>` over `Ball<double, 1>`, width 0 | 28.2 to 30.0 (-O2), 29.0 to 31.2 (-O3) | 23.2 to 23.3 (-O2), 21.3 to 22.0 (-O3) | 22.6 to 22.9 | 21.5 (-O2), 22.6 to 22.7 (-O3) |
| `Ball<double, 1>` over `Ball<double, 1>`, width 0 | 1.00 | 1.00 | 1.00 | 1.00 |
| `Ball<double, 2>` over `Ball<double, 1>`, width 0 | 3.87 to 4.04 (-O2), 3.96 to 4.28 (-O3) | 3.65 to 3.90 (-O2), 3.52 to 3.79 (-O3) | 3.73 to 3.80 | 3.66 to 3.67 (-O2), 3.78 to 3.79 (-O3) |
| `Interval<double, 2>` over `Ball<double, 2>`, width 0 | 7.24 to 7.43 | 5.96 to 6.38 (-O2), 5.80 to 6.04 (-O3) | 6.01 to 6.08 | 5.85 to 6.00 |

| Bisection: ns per evaluation of p | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<double, 1>`, width 1e-6 | 74.6 to 76.5 | 50.1 (-O2), 47 to 48.2 (-O3) | 93.3 to 95.4 (-O2), 84.4 to 85.2 (-O3) | 134 to 137 |
| `Interval<double, 2>`, width 1e-6 | 275 to 297 (-O2), 276 to 291 (-O3) | 231 to 246 (-O2), 227 to 243 (-O3) | 513 to 522 | 491 to 507 |
| `Ball<double, 1>`, width 1e-6 | 18.2 to 18.8 (-O2), 17.8 to 18.1 (-O3) | 20.8 to 21.5 (-O2), 21.8 to 22.2 (-O3) | 48 to 49.3 | 46.1 to 48.1 |
| `Ball<double, 2>`, width 1e-6 | 37.3 to 39.1 (-O2), 36.7 to 38.6 (-O3) | 39.8 to 42.5 (-O2), 39 to 42.2 (-O3) | 92.2 to 94 | 86.1 to 87.6 |
| `Interval<double, 1>`, width 0 | 74.1 to 76.2 | 51.1 to 51.2 (-O2), 47.6 to 49 (-O3) | 107 to 110 (-O2), 97.1 to 97.7 (-O3) | 134 to 137 |
| `Interval<double, 2>`, width 0 | 273 to 298 (-O2), 273 to 292 (-O3) | 232 to 249 (-O2), 231 to 243 (-O3) | 537 to 548 | 489 to 505 |
| `Ball<double, 1>`, width 0 | 20.6 to 21.1 (-O2), 19.9 to 20 (-O3) | 21.3 to 22.8 (-O2), 23.2 to 23.6 (-O3) | 50.1 to 51.3 | 48.5 to 49.2 (-O2), 46.6 to 47.3 (-O3) |
| `Ball<double, 2>`, width 0 | 40.3 to 43.3 (-O2), 40.2 to 43.2 (-O3) | 42 to 45.1 (-O2), 41.3 to 45.2 (-O3) | 96 to 97.7 | 89.5 to 91.2 |

- **`Ball<double, 1>` finds the zeros fastest**, on both machines and at both widths: 3.2 to 8.8 µs
  to a width of $10^{-6}$ and 8.8 to 23 µs as far as it goes, with 179 and 443 evaluations of $p$
  against the interval's 167 and 435. `Interval<double, 1>` takes 1.6 to 3.9 times as long: each
  evaluation costs 1.8 to 4.1 times a ball's (47 to 137 ns against 18 to 51), because a product of
  intervals is eight directed products ([question 2](#2-intervalt-1)) where a ball's is one product
  and a radius.
- **Two limbs**: `Ball<double, 2>` takes 1.8 to 2.2 times `Ball<double, 1>` to a width of $10^{-6}$
  (the same 179 evaluations, each 1.8 to 2.2 times dearer), and 3.5 to 4.3 times as far as it goes, where it
  makes 875 evaluations and narrows the zeros to a radius of $1.2 \times 10^{-31}$ to
  $1.0 \times 10^{-30}$, 30 digits, against $2.8 \times 10^{-16}$ to $2.7 \times 10^{-15}$ for one limb.
  `Interval<double, 2>` narrows them most, to $3.4 \times 10^{-32}$ to $2.7 \times 10^{-31}$, three to
  four times the ball's, with 943 evaluations; it costs 5.2 to 7.4 times `Ball<double, 2>`, and 21 to
  31 times `Ball<double, 1>` as far as each goes (9.7 to 15 times to $10^{-6}$), a product of intervals of two limbs being some four hundred operations.
- **The answer for a generic client**: `Ball<double, 1>` where `double`'s precision is enough
  (its zeros are at most six times wider than the interval's at the end, $2.7 \times 10^{-15}$
  against $4.4 \times 10^{-16}$, and found in a quarter to two thirds of the time); `Ball<double, 2>`
  for thirty digits at about four times its cost; `Interval<double, 2>` only where enclosures three or
  four times narrower than the ball's of two limbs are worth five to seven times its time.
  `Interval<double, 1>` is never the fastest here; what it gives is the tightest enclosure of one
  limb, and the guarantees an interval has that a ball does not (half-lines, the empty set, exact
  comparisons). These are one polynomial's figures, with narrow sets near the end of the search; on
  wide sets the dependency problem sets the width for every type
  ([question 4](#4-a-polynomial-cost-and-tightness)).

### 11. `self_test()` and the checks

What does `kairn::self_test()` cost a program at startup and at compile time, and what do the
checks of `KAIRN_CHECKS=1` cost the intervals and the enclosure interface? The run time is one
call, timed by the harness (`m2r/run/self_test/op`), with its two parts: the checks of the
environment and of the compiler's flags on `T` (`detail::self_test_limb` for both limb types), and
the generated kernels on their fixed operands (`gen::selftest::run()`, 330 kernels for each limb
type). The compile time is that of `bench/compile_time/self_test.cpp`, `kairn/kairn.hpp` and one call
of `self_test()`, as [Compile times and other costs, Milestone 1](costs-milestone1.md#1-compile-times)
measured it (`compile_time.py run`, the minimum wall time over seven compilations in rounds, with an
empty unit and the include alone; on Zen 2 pinned). It compiles the generated header
`kairn/gen/selftest.hpp`, now 310 943 bytes, 7 941 lines, 330 tests per limb type; at the end of
Milestone 1 (commit `040922c`) it was 76 497 bytes, 2 036 lines, 84 tests per limb type. The checks
are measured as Milestone 1 measured them (`costs.cpp`): the same functions in two programs, the
harness with `KAIRN_CHECKS` 0 and `kairn-bench-m2-checks-LEVEL` with 1, run one after the other,
three pairs per configuration; a ratio is of the two programs' minima in one pair, and the controls
are generated kernels called directly, which no check reaches.

| self_test(), microseconds per call | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `self_test()` | 2.76 to 2.98 (-O2), 3 to 3.08 (-O3) | 2.53 to 2.59 (-O2), 2.58 to 2.66 (-O3) | 8.38 to 8.78 (-O2), 7.49 to 7.58 (-O3) | 6.76 to 6.95 (-O2), 6.97 to 7.16 (-O3) |
| the checks of the environment and the flags, both limb types | 0.00838 to 0.00863 (-O2), 0.00899 to 0.009 (-O3) | 0.00899 (-O2), 0.00778 to 0.00836 (-O3) | 0.0603 to 0.0615 (-O2), 0.058 to 0.0586 (-O3) | 0.0418 to 0.0427 |
| the generated kernels on their fixed operands | 2.71 to 2.93 (-O2), 2.98 to 3.04 (-O3) | 2.54 to 2.63 | 7.99 to 8.36 (-O2), 7.24 to 7.5 (-O3) | 6.47 to 6.73 (-O2), 6.29 to 6.47 (-O3) |

| Compile time, s (minimum wall time; -O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| an empty unit | 0.02; 0.02 | 0.06; 0.05 | 0.02; 0.01 | 0.04; 0.04 |
| `kairn/kairn.hpp`, nothing used | 0.14; 0.14 | 0.26; 0.26 | 0.43; 0.43 | 0.67; 0.67 |
| one call of `kairn::self_test()` | 1.19; 1.21 | 3.85; 4.02 | 6.40; 6.50 | 3.88; 3.89 |
| one call of `kairn::self_test()`, over the include alone | 1.05; 1.07 | 3.59; 3.76 | 5.97; 6.07 | 3.21; 3.21 |
| peak memory of `self_test`, MB | 143; 143 | 258; 262 | 236; 238 | 151; 151 |

| KAIRN_CHECKS 1 over 0 (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, `Interval<T, 1>`, loop | 2.13 | 2.58 to 2.75 (-O2), 2.56 to 2.60 (-O3) | 2.96 to 3.01 | 3.46 to 3.53 |
| `X * Y`, `Interval<T, 1>`, loop | 1.33 to 1.36 | 1.12 to 1.15 | 2.19 to 2.22 | 1.26 to 1.29 |
| `X + Y`, `Interval<T, 2>`, loop | 1.16 to 1.20 | 2.00 (-O2), 1.87 to 1.91 (-O3) | 1.36 to 1.38 | 1.30 to 1.34 |
| `X * Y`, `Interval<T, 2>`, loop | 1.06 to 1.09 | 1.12 to 1.15 | 1.17 to 1.18 | 1.19 to 1.22 (-O2), 1.18 to 1.24 (-O3) |
| `S + X`, `Interval<T, 1>`, chain | 0.99 to 1.02 | 1.17 to 1.22 (-O2), 1.10 to 1.13 (-O3) | 1.97 to 2.00 | 2.40 to 2.45 |
| `P * X`, `Interval<T, 2>`, chain | 1.00 to 1.02 | 1.04 to 1.07 (-O2), 1.00 to 1.01 (-O3) | 1.09 to 1.11 | 1.03 to 1.05 |
| Horner, `Interval<T, 1>` | 1.05 (-O2), 0.98 to 1.05 (-O3) | 0.95 to 1.01 (-O2), 1.06 to 1.10 (-O3) | 1.52 to 1.56 | 1.72 to 1.75 |
| Horner, `Interval<T, 2>` | 1.00 to 1.01 | 1.28 to 1.38 (-O2), 1.23 to 1.25 (-O3) | 1.04 to 1.06 | 1.06 to 1.08 |
| `less`, `Interval<T, 1>` | 4.70 to 4.97 (-O2), 4.83 to 4.84 (-O3) | 3.83 to 3.86 (-O2), 4.08 to 4.15 (-O3) | 4.25 to 4.29 | 6.87 to 7.03 |
| `contains(t)`, `Interval<T, 1>` | 4.50 to 4.60 | 3.91 to 4.00 (-O2), 3.76 to 3.83 (-O3) | 14.1 to 14.3 | 16.3 to 16.6 (-O2), 15.3 to 16.6 (-O3) |
| `hull`, `Interval<T, 1>` | 6.20 to 6.32 | 4.40 to 4.44 (-O2), 5.71 to 5.83 (-O3) | 11.1 to 11.3 | 25.3 to 25.7 |
| `less`, `Ball<T, 1>` | 1.71 to 1.76 | 1.96 (-O2), 2.20 to 2.27 (-O3) | 1.70 to 1.73 | 4.19 to 4.30 |
| `certainly_positive()`, `Ball<T, 1>` | 7.85 to 8.03 | 9.61 (-O2), 8.56 to 8.57 (-O3) | 22.6 to 22.7 (-O2), 24.3 to 24.5 (-O3) | 12.0 to 13.7 (-O2), 12.4 to 13.4 (-O3) |
| `less`, `Ball<T, 2>` | 1.36 to 1.39 | 1.86 to 1.97 (-O2), 1.96 to 2.06 (-O3) | 1.74 (-O2), 1.66 to 1.68 (-O3) | 1.24 to 1.28 |
| `hull`, `Ball<T, 2>` | 1.01 to 1.05 | 1.09 to 1.13 (-O2), 1.05 to 1.08 (-O3) | 1.07 to 1.12 | 1.04 to 1.06 |
| control: the kernel `interval_mul_1`, loop | 0.97 to 1.00 | 0.98 to 1.02 | 1.00 to 1.01 | 0.99 to 1.01 |
| control: the kernel `ball_less_2`, loop | 0.97 to 1.00 (-O2), 0.99 to 1.03 (-O3) | 1.00 to 1.06 (-O2), 0.95 to 1.00 (-O3) | 0.99 to 1.00 | 0.99 to 1.01 |

| Times with KAIRN_CHECKS 0; 1 (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/interval_add_1/op` | 1.87; 3.99 (-O2), 1.87; 3.99 (-O3) | 1.74; 4.57 (-O2), 1.76; 4.52 (-O3) | 3.52; 10.5 (-O2), 3.53; 10.6 (-O3) | 4.51; 15.8 (-O2), 4.51; 15.8 (-O3) |
| `m2/tp/interval_mul_1/op` | 6.07; 8.19 (-O2), 6.03; 8.21 (-O3) | 7.94; 9.04 (-O2), 8.05; 9.02 (-O3) | 9.86; 21.7 (-O2), 9.87; 21.7 (-O3) | 16.9; 21.8 (-O2), 17; 21.8 (-O3) |
| `m2/tp/interval_add_2/op` | 8.43; 10.2 (-O2), 8.43; 9.76 (-O3) | 7.13; 14.2 (-O2), 7.54; 14.1 (-O3) | 24.3; 33.5 (-O2), 24.3; 33.1 (-O3) | 18.5; 24.4 (-O2), 18.5; 24.4 (-O3) |
| `m2e/tp/i1_less/op` | 0.644; 3.11 (-O2), 0.662; 3.2 (-O3) | 0.799; 3.08 (-O2), 0.805; 3.3 (-O3) | 1.95; 8.31 (-O2), 1.94; 8.29 (-O3) | 1.99; 13.8 (-O2), 1.99; 13.8 (-O3) |
| `m2e/tp/i1_contains_t/op` | 0.347; 1.59 (-O2), 0.347; 1.56 (-O3) | 0.333; 1.31 (-O2), 0.35; 1.32 (-O3) | 0.53; 7.5 (-O2), 0.531; 7.5 (-O3) | 0.508; 8.34 (-O2), 0.507; 7.86 (-O3) |
| `m2e/tp/b2_less/op` | 6.17; 8.61 (-O2), 6.22; 8.61 (-O3) | 4.67; 9.22 (-O2), 5.02; 9.84 (-O3) | 16.3; 28.4 (-O2), 16.2; 27.2 (-O3) | 19.3; 24.4 (-O2), 19.4; 24.4 (-O3) |
| `m2e/tp/i2_split/op` | 7.32; 11.2 (-O2), 7.85; 10.6 (-O3) | 6.73; 9.32 (-O2), 6.33; 8.8 (-O3) | 16.2; 26.4 (-O2), 23.5; 26.3 (-O3) | 16.4; 18.6 (-O2), 16.4; 18.6 (-O3) |
| `m2/tp/interval_mul_1/kairn` | 6.34; 6.14 (-O2), 6.31; 6.28 (-O3) | 7.77; 7.91 (-O2), 7.97; 7.92 (-O3) | 9.85; 9.86 (-O2), 9.86; 9.87 (-O3) | 16.9; 17 (-O2), 17; 16.9 (-O3) |

- **At run time `self_test()` costs 2.5 to 3.1 µs on the M3 and 6.8 to 8.8 µs on Zen 2**, once at
  startup; 8 to 62 ns of it are the checks of the environment and the flags, the rest the 660
  kernels on their operands.
- **At compile time it costs 1.2 s (Apple clang) to 6.5 s (GCC 13)**: a unit with one call of
  `self_test()` compiles in 6.40 s at `-O2` and 6.50 s at `-O3` with GCC 13, which confirms the
  6.6 s that a downstream user measured at `-O3`; 3.9 s with Clang 18 and GCC 16 (4.0 at `-O3`);
  1.19 to 1.21 s with Apple clang. At the end of Milestone 1 the same unit took 1.08 s with GCC 13,
  0.77 s with Clang 18, 0.75 s with GCC 16 and 0.21 s with Apple clang at `-O2`
  ([Milestone 1](costs-milestone1.md#1-compile-times)): 5.0 to 5.9 times less, the generated header
  being then a quarter of its size, with a quarter of the tests. `-O3` costs what `-O2` costs (within
  5%).
  Beyond the call, the include alone has grown too: `kairn/kairn.hpp` with nothing used takes 0.14 s
  (Apple clang) to 0.67 s (Clang 18), against 0.06 to 0.23 s in Milestone 1. A program pays this in
  the one translation unit that calls `self_test()`.
- **The checks cost most where an operation is cheapest.** With `KAIRN_CHECKS=1` a sum of intervals
  of one limb takes 2.1 to 3.5 times as long in a loop, a product 1.1 to 2.2 times; with two limbs
  1.2 to 2.0 and 1.1 to 1.2; in chains 0.95 to 2.5; a Horner evaluation 0.95 to 1.8. Each operation
  first checks the environment, a read of the control register and three tests, which Milestone 1
  measured at 0.36 to 0.39 ns on the M3 and 6.2 to 6.5 ns on Zen 2, and then its operands.
- **The functions that do not round are checked too, and they are the cheapest**: they skip the test
  of the rounding mode but not the rest of the environment (`config.hpp`, "Functions that do not
  round"). An interval's `contains(t)` takes 0.35 ns and 1.3 to 1.6 ns with the checks on the M3,
  0.51 to 0.53 ns and 7.5 to 8.3 ns on Zen 2 (3.8 to 16.6 times); its `less` 3.8 to 7.0 times, its
  `hull` 4.2 to 26 times, a ball's `certainly_positive()` 6.1 to 24.5 times. A ball's operations
  that round, dearer to begin with, take 1.1 to 10 times as long for one limb (`contains(t)` most) and
  1.0 to 2.4 times for two (`less` 1.2 to 2.1; the hull 1.0 to 1.1, its time being its three
  conversions). The controls, kernels called directly, take 0.98 to
  1.01 of their time without the checks.

### 12. Compile time of the enclosure interface

What does a large function full of the interface's calls cost the compiler, and does
`KAIRN_ENCLOSURE_CODE` change it? A translation unit of 1 000 or 10 000 calls in one function, in
straight-line code (`bench/enclosure_costs.py`, `--kind compare`, `contains` or `setops`): the
three-valued comparisons `less`, `less_equal`, `equal`; `contains` of a point and of a set; `hull`,
`intersection`, `split()`; each on `Interval<double, 1>`, `Interval<double, 2>`, `Ball<double, 1>`
and `Ball<double, 2>` in turn, each call on operands of its own (elements of input arrays that no
other call reads, so that no call can be merged with another) and each result stored. Compiled in
the three settings the first part measured for the arithmetic ([question 7](#7-the-settings-of-kairn_enclosure_code)),
and as "calls", the same unit without Kairn, the types structures of `double`s and the functions
declared only. The units of 1 000 calls three times in rounds at `-O2` and `-O3`, those of 10 000
once at `-O2` (as the first part did for GCC 16's largest units), with a limit of 30 minutes; the
compiler's processor time, as in the first part, and its peak memory and object.

| The comparisons: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 4.50; 4.56 | 5.54; 8.41 | 62.3; 62.7 | 8.05; 8.15 |
| 1000, outlined | 4.41; 4.50 | 5.54; 8.42 | 62.4; 62.4 | 8.04; 8.04 |
| 1000, external | 4.47; 4.49 | 5.52; 8.38 | 62.9; 62.5 | 8.00; 7.97 |
| 1000, calls | 0.08; 0.08 | 0.33; 0.67 | 0.33; 0.33 | 0.38; 0.38 |
| 10000, inline | 730; – | 140; – | stopped at 1800; – | 1435; – |
| 10000, outlined | 681; – | 143; – | stopped at 1800; – | 1513; – |
| 10000, external | 673; – | 134; – | stopped at 1800; – | 1579; – |
| 10000, calls | 2.68; – | 3.80; – | 4.49; – | 12.2; – |

| contains: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 0.53; 1.77 | 1.54; 1.96 | 2.67; 2.77 | 2.37; 2.37 |
| 1000, calls | 0.10; 0.10 | 0.32; 0.66 | 0.35; 0.36 | 0.40; 0.40 |
| 10000, inline | 9.35; – | 22.3; – | 107; – | 72.1; – |
| 10000, calls | 2.36; – | 4.08; – | 5.30; – | 10.8; – |

| hull, intersection, split: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 0.47; 0.54 | 2.06; 2.71 | 2.99; 3.13 | 1.75; 1.75 |
| 1000, calls | 0.22; 0.22 | 0.50; 1.04 | 0.55; 0.56 | 0.45; 0.45 |
| 10000, inline | 5.31; – | 14.2; – | 24.4; – | 17.8; – |
| 10000, calls | 6.85; – | 6.43; – | 8.49; – | 16.4; – |

| The comparisons: peak memory, MB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 426; 432 | 558; 582 | 583; 583 | 209; 209 |
| 10000, inline | 3283; – | 4334; – |  | 1090; – |

- **The setting changes nothing here, as the design says**: the comparisons, `contains`, `hull`,
  `intersection` and `split()` stay inline in every setting of `KAIRN_ENCLOSURE_CODE`
  (`config.hpp`), so the three settings compile the same code: every object has the same size to
  the byte in the three, and the medians of the times agree within 2% for the units of 1 000 calls (7% for Apple clang's
  shortest, half a second), within 9% (Apple clang) and 10% (Clang 18, while the machine's load rose from 3 to 76) for the single
  compilations of 10 000. A large function of these calls compiles as slowly in the outlined and
  external settings as inline.
- **The comparisons are what is slow, and they are slow with every compiler at 10 000.** A function
  with 1 000 calls of `less`, `less_equal` and `equal` takes 4.5 s with Apple clang, 5.5 s with
  GCC 16 (8.4 at `-O3`), 8.0 s with Clang 18 and 62 s with GCC 13, against 0.08 to 0.67 s for the
  same calls without Kairn; with 10 000 calls, 134 to 143 s with GCC 16 (4.3 GB), 673 to 730 s with
  Apple clang (3.3 GB), 1 435 to 1 579 s with Clang 18 (1.1 GB), and GCC 13 had not finished after
  30 minutes in any setting, where the measurement stops it. The same function with `contains` takes
  0.5 to 2.8 s and 8.6 to 108 s, with `hull`, `intersection` and `split()` 0.5 to 3.2 s and 5.3 to
  24.5 s.
- **Why the comparisons**: `kairn::less` and its kin are free functions forced inline
  (`KAIRN_FORCEINLINE`), so each of the calls becomes its kernel in the function, where `hull`,
  `intersection` and `split()` are ordinary inline members that Apple clang and GCC 13 emit once and
  call (the objects define `Ball<double, 2>::hull`, `intersection`, `split` and `Interval::split`);
  the comparison unit's object is 2.2 to 3.4 MB at 10 000 calls. Where the time goes differs by
  compiler: Apple clang spends 70% of a unit of 3 000 comparisons in its SLP vectorizer and 13% in
  instruction scheduling, both of which grow faster than the function; GCC 13 spends 58% of a unit
  of 1 000 in its inlining heuristics and 18% in partial redundancy elimination, a cost GCC 16 does
  not have (5.5 s against 62).
- **What a program should do**: keep the comparisons of enclosures in functions of modest size (a
  thousand calls compile in 4.5 to 62 s); the setting of `KAIRN_ENCLOSURE_CODE` does not help, since
  it moves the arithmetic only.

### What the machine code shows (second part)

The loops of the new timed functions were disassembled on every configuration and summarized by
`bench/asm_summary.py`, as in the first part (`asm2-*.json` beside the runs). What explains the
tables:

1. **Clang 18 vectorizes the scalar loops over the arrays of limbs, and no other compiler does.**
   The loop of `kb_m2_v64_tp_add22__op` (a sum of `Expansion<double, 2>` read through raw pointers)
   is, with Clang 18, 143 instructions on 256-bit registers for four elements, as long as the packed
   loop's 142; the generated kernel on the limbs (`__kairn`) gives the same loop. The loop over an
   array of `Expansion<double, 2>` (`__aos`) stays scalar, 33 instructions per element, hence its 3.0
   to 7.7 times. With GCC 13, GCC 16 and Apple clang every scalar loop of question 8 is scalar, 34
   to 50 instructions per element for a sum.
2. **The tutorial's dot product is one chain.** With Apple clang its loop is 67 instructions on
   128-bit registers per step of two elements, each step waiting for the packed sum before; the
   scalar loop with two sums is 101 instructions per two elements in two independent chains, which
   the M3 overlaps (question 8).

3. **The members of the interface are inline functions, not forced inline, and the compilers often
   call them.** At `-O2`, the loops of `mid_rad()` and of the conversion of an interval of one limb
   are 7 to 10 instructions around a call with every compiler (GCC 13 inlines both at `-O3`), and
   Apple clang's loop of `midpoint()` of an `Interval<double, 1>` calls
   `kairn::Interval<double, 1>::midpoint()`, which runs the whole kernel. Clang 18's loop of
   `Ball<double, 2>::intersection` is a call per element, where the kernel called directly is a loop
   of 809 instructions on 256-bit registers: hence its 2.26 times. The free functions of the
   interface, `kairn::less` and the others, are forced inline ([question 12](#12-compile-time-of-the-enclosure-interface)).

### How the second part was measured

| Machine | Configurations | Conditions |
|---|---|---|
| M3: macOS 26.6 arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2; `-O2` and `-O3`; `Packed` in its NEON form (2 lanes of `double`, 4 of `float`) | no affinity: the thread asks for the user-interactive class; shared with other jobs; a run started only when the 1-minute load average was under 20, and, as in the first part, a run whose median spread (the median over the functions of each one's median over its minimum, the loops of `mem` left out) exceeded 5% was set aside and repeated |
| Zen 2: Linux x86-64, AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1; `-O2` and `-O3`; `-mfma`, the files of `Packed` and of the containers `-mavx2 -mfma` (`Packed` in its AVX2 form: 4 lanes of `double`, 8 of `float`) | each run pinned to the logical CPU of the second socket whose usage and that of its SMT sibling were the lowest over the 2 s before it (under 2%), `taskset` and `--cpu`; `mpstat` of the CPU and its sibling every 5 s during the run, kept with the runs' logs; one measurement at a time |

- **Commit**: `cbe3bb1`, which adds the harness of the second part to `main` at `aa168ee` and
  changes nothing under `include/`; the compile measurements of questions 11 and 12 at `e2f497c`,
  which adds an option to `enclosure_costs.py` (`--once-from`) and changes nothing else; recorded in
  every file.
- **Flags**: those of the first part; the checks of question 11 with `KAIRN_CHECKS=1` in every
  translation unit (`kairn-bench-m2-checks-LEVEL`).
- **Statistic**: as in the first part, the minimum over 41 (M3) or 31 (Zen 2) samples of about 4 ms;
  a sample of a loop over arrays beyond the last-level cache is one call (10 to 40 ms); ratios are of
  minima within one run (for question 11, of the two programs' runs made one after the other), and a
  cell is the lowest and highest value over the three runs of a configuration.
- **Checks before timing**: every timed function against its reference, byte for byte, in every run
  ([Checks of the second part](#checks-of-the-second-part)); none failed.
- **Windows**: this part has no Windows machine; the Windows figures of Milestone 2 are those of the
  first part where it has them (it has none: Windows and MSVC were not measured in Milestone 2).
- **Not measured in the second part**: Windows and MSVC, Intel processors, AVX-512, GPUs; the
  functions on arrays, `BallVector` and the accumulator, which are not on `main` (2026-11-22: they
  reached `main` since, and [the third part](#the-third-part) measures them); the run time of
  the units of question 12 (their compile time only), and those units of 10 000 calls at `-O3`;
  `KAIRN_CHECKS` on `Packed` and the containers; a bisection on another polynomial (the tutorial's
  finishes in 3 to 520 µs, which the harness times by repeating it).
- **Noise**: on Zen 2 a function's spread over the three runs of a configuration is 0.2 to 2.0% at
  the median function and 1.0 to 5.8% at the 90th percentile; on the M3 0.0 to 4.9% and 3.9 to 9.4%,
  a whole M3 run being a few percent faster or slower than another, which moves times and not ratios
  within a run ([Runs of the second part](#runs-of-the-second-part)). The loops beyond the last-level
  cache are left out of the 5% rule of the M3 runs: their spread is that of the memory system, not
  of a disturbance. Of 21 M3 runs set aside by the rule, one (GCC 16, `-O3`, with the checks, third
  round) passed at its sixth attempt, five having had a median spread of 5.4 to 5.7%. On Zen 2 five
  runs whose SMT sibling was busy for 1 to 4 samples of 5 s were kept, being within 1.0% of their
  configuration's fastest run at the median function and 1.6% at the 90th percentile; the runs of
  2 s (the bisections) are shorter than `mpstat`'s interval and have no sample. A cell's range
  includes this noise; differences within it are not differences.

## The third part

What reached `main` after the second part ([Still to come](#still-to-come)): the functions on arrays
of `kairn/batch.hpp`, the accumulator of `kairn/accumulator.hpp` and the ball vectors of
`kairn/ball_vector.hpp`, on the tree of `25cde04` and the harness of this part (commits `9e114bb`,
`dae16be` and `be95dbb`, which change nothing under `include/`), 2026-11-22, on the same two machines and four compilers as the earlier parts (the M3 under load, [below](#how-the-third-part-was-measured)), `-O2` and
`-O3`, three runs of each configuration: the functions on arrays against plain loops of `T` and the
code a numerical programmer writes instead ([question 13](#13-the-functions-on-arrays)); short
arrays, short ball vectors and the check of the environment at entry
([question 14](#14-short-arrays-and-the-check-at-entry)); the guards of the factors a program
supplies ([question 15](#15-the-guards-of-supplied-factors)); the accumulator
([question 16](#16-the-accumulator)); the error made against the condition number and the stated
bound ([question 17](#17-accuracy-for-the-price)); `BallVector` against arrays of `Ball`
([question 18](#18-one-radius-for-many-centers)); and the compile time of the three headers
([question 19](#19-compile-time-of-the-functions-on-arrays-and-the-ball-vectors)). The harness is
that of the earlier parts, three files more and a program of its own (`bench/m2_batch.cpp`,
`m2_bv.cpp`, `m2_bvs.cpp`, `m2_exact.hpp`, `m2_accuracy.cpp`, and `entry_check.py` for the copy of
the headers without the check; [bench/README.md](https://github.com/danielepanozzo/kairn/tree/main/bench),
"Milestone 2", the third part), with the same driver, statistic and checks; the runs are the files
`arrays-*`, `short-*`, `entry-*`, `entryx-*`, `acc-*`, `bv-*`, `accuracy-*`, `asm3-*`,
`headers-compile-*` and `compile-*-{arrays,ballvectors}*` of
[`results/milestone2/bench/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/bench),
and every table below is printed from them by `python3 bench/m2_report.py --part 3
results/milestone2/bench`. Names of functions are those of the harness: `m2a` and `m2af` the
functions on arrays for `double` and `float`, `m2k` the short arrays, `m2c` the accumulator, `m2w`
the ball vectors, `m2x` and `m2y` the short ball vectors (every size in one unit, and one operation
and size per unit); KIND `tp` in L1 (512 elements) or many independent calls, `llc` in the
last-level cache (128 Ki elements of `double`, 256 Ki of `float`: 1 to 6 MB, within the 16 MB of an
L3 of Zen 2 and of the L2 of the M3's performance cores), `mem` in no cache (4 Mi and 8 Mi
elements, 32 to 192 MB) and `lat` a chain of calls, each on the result of the one before; variants
`op` (the public function, default order), `seq` (with `kairn::sequential`), `kairn` (the generated
loop `op` calls, called directly on the limbs), `kseq` (the generated sequential loop), `bare` (the
generated loop on stored arrays, the same steps without the guards), `plain` and `plainw` (the same
loop on `T`, element after element and in the lane order), `textbook` (the code a numerical
programmer writes instead) and `balls` (an array of `Ball`).


### 13. The functions on arrays

What does an accurate sum or dot product cost against the loop a program writes on `T`, and against
the compensated or double-word code a numerical programmer writes instead, and what does the order
cost? Each function of `kairn/batch.hpp` (`bench/m2_batch.cpp`), one and two limbs, `double` and
`float`, one call over arrays in L1 (512 elements), in the last-level cache (128 Ki elements of
`double`, 256 Ki of `float`) and in no cache (4 Mi and 8 Mi elements), the time per element (per
term for the product of polynomials, $N^2$ terms for two polynomials of $N$ coefficients); numbers
$\pm[1, 2)\,2^k$, $k \in [-8, 8]$, the second limb about $u$ times the first, the scalar `a` near 1.
Beside each: the same loop on `T` (`plain`, element after element, one chain for a reduction, with
a fused multiply-add for `dot` and `conv` as Kairn's step; `plainw`, the same in the lane order of
the default, $W$ chains, whose results are those of the generated one-limb loop byte for byte,
checked); for one-limb data the compensated Sum2 and Dot2 of Ogita, Rump and Oishi, against Kairn's
`sum` and `dot` of two limbs on the same data with zero second limbs (`sum2z`, `dot2z`): two ways of
an accurate sum of doubles; for two-limb data the double-word arithmetic of Joldes, Muller and
Popescu written out element after element (`props.hpp`: AccurateDWPlusDW for `sum` and `add`,
SloppyDWPlusDW for `sum_fast`, DWTimesFP3 for `scale`, DWTimesDW3 for the products). And the default
order against `kairn::sequential`: for `sum`, `sum_fast` and `dot` the public functions; for the
maps, which take no order, the generated loop of one lane (`kseq`) against the default's (`kairn`).
Everything is compiled as packed code, so that the default order is the lane order of `Packed` (4
lanes of `double` and 8 of `float` with AVX2, 2 and 4 with NEON): the sequential loop is the loop of
one lane.

| The functions on arrays, double: ns per element (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, L1 | 0.229 to 0.236 (-O2), 0.215 to 0.231 (-O3) | 0.195 to 0.199 |
| `sum`, two limbs, L1 | 2.6 to 2.67 | 2.58 to 2.62 |
| `sum`, two limbs, memory | 2.58 to 2.63 | 2.56 to 2.6 |
| `sum_fast`, two limbs, L1 | 1.67 to 1.71 | 1.66 to 1.75 (-O2), 1.66 to 1.72 (-O3) |
| `dot`, one limb, L1 | 0.35 to 0.358 (-O2), 0.335 to 0.356 (-O3) | 0.323 to 0.33 |
| `dot`, two limbs, L1 | 2.61 to 2.68 | 2.62 to 2.69 |
| `add`, one limb, L1 | 0.214 to 0.219 (-O2), 0.214 to 0.226 (-O3) | 0.202 to 0.207 |
| `add`, two limbs, L1 | 1.23 to 1.25 | 1.28 to 1.31 |
| `scale`, two limbs, L1 | 0.505 to 0.522 | 0.499 to 0.512 |
| `axpy`, two limbs, a of T, L1 | 1.74 to 1.79 | 1.77 to 1.81 |
| `norm_upper`, two limbs, L1 | 0.184 to 0.188 (-O2), 0.176 to 0.181 (-O3) | 0.113 to 0.129 (-O2), 0.113 to 0.129 (-O3) |
| `sum`, one limb, memory | 0.434 to 0.453 | 0.422 to 0.434 |
| a plain sum of T, one chain, L1 | 0.846 to 0.868 | 0.846 to 0.863 |
| the plain sum of T in the lane order, L1 | 0.209 to 0.214 (-O2), 0.244 to 0.246 (-O3) | 0.18 to 0.183 |

| Over the same loop of T, double (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, over the plain sum in the same order, L1 | 1.09 to 1.13 (-O2), 0.87 to 0.95 (-O3) | 1.08 to 1.09 |
| `sum`, one limb, over the plain sum, one chain, L1 | 0.25 to 0.28 | 0.23 |
| `sum`, two limbs, over the plain sum of T in the same order, L1 | 12.5 (-O2), 10.6 to 10.9 (-O3) | 14.3 |
| `dot`, one limb, over the plain dot product in the same order, L1 | 1.06 to 1.09 (-O2), 0.91 to 0.97 (-O3) | 1.07 |
| `dot`, two limbs, over the plain dot product of T in the same order, L1 | 7.91 to 8.11 (-O2), 7.11 to 7.28 (-O3) | 8.70 to 8.73 |
| `add`, one limb, over `x + y` of T, L1 | 0.67 (-O2), 1.83 to 2.09 (-O3) | 1.55 to 1.69 (-O2), 1.67 to 1.68 (-O3) |
| `add`, two limbs, over `x + y` of T, L1 | 3.84 to 3.86 (-O2), 10.2 to 12.0 (-O3) | 9.8 to 10.7 (-O2), 10.6 to 10.7 (-O3) |
| `axpy`, two limbs, over `a x + y` of T, L1 | 5.40 to 5.45 (-O2), 15.0 to 16.8 (-O3) | 14.6 to 14.8 |
| `sum`, two limbs, over the plain sum of T in the same order, memory | 5.64 to 5.66 (-O2), 4.02 to 4.06 (-O3) | 5.52 to 5.62 |
| `add`, two limbs, over `x + y` of T, memory | 1.75 to 1.84 (-O2), 1.83 to 1.84 (-O3) | 1.81 to 1.84 (-O2), 1.79 to 1.90 (-O3) |

| Over the textbook code, double (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum` of two limbs of one-limb data, default, over Sum2, L1 | 1.83 | 1.78 to 1.80 |
| `sum` of two limbs of one-limb data, sequential, over Sum2, L1 | 7.13 to 7.18 | 7.05 to 7.06 |
| `dot` of two limbs of one-limb data, default, over Dot2, L1 | 1.66 to 1.67 (-O2), 1.66 to 1.72 (-O3) | 1.71 to 1.73 |
| `sum`, two limbs, sequential, over double-word sums written out, L1 | 1.00 | 1.02 to 1.03 |
| `sum`, two limbs, default, over double-word sums written out, L1 | 0.25 to 0.26 | 0.26 |
| `dot`, two limbs, sequential, over the double-word dot product written out, L1 | 1.00 to 1.01 | 1.01 to 1.02 |
| `dot`, two limbs, default, over the double-word dot product written out, L1 | 0.26 | 0.26 |
| `add`, two limbs, over AccurateDWPlusDW written out, L1 | 0.33 (-O2), 1.28 to 1.30 (-O3) | 1.32 to 1.35 |
| `scale`, two limbs, over DWTimesFP3 written out, L1 | 0.49 (-O2), 1.83 to 1.84 (-O3) | 2.05 to 2.06 |
| `axpy`, two limbs, a of T, over the same written out, L1 | 0.30 (-O2), 1.17 to 1.18 (-O3) | 1.20 |

| kairn::sequential over the default order (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, L1 | 3.77 to 3.86 (-O2), 3.71 to 4.00 (-O3) | 4.40 to 4.43 |
| `sum`, two limbs, L1 | 3.83 to 3.93 | 3.93 to 3.94 |
| `dot`, one limb, L1 | 4.16 to 4.17 (-O2), 4.11 to 4.36 (-O3) | 4.42 to 4.45 |
| `dot`, two limbs, L1 | 3.84 to 3.94 | 3.91 to 3.95 |
| `add`, two limbs, one lane over the default, L1 | 4.34 to 4.36 | 0.99 to 1.00 |
| `axpy`, two limbs, one lane over the default, L1 | 4.37 to 4.42 | 0.87 |
| `sum`, one limb, memory | 2.10 to 2.15 | 2.17 to 2.26 (-O2), 2.15 to 2.19 (-O3) |
| `sum`, two limbs, memory | 3.95 to 3.99 | 3.98 to 4.00 |

| kairn::sequential over the default order, float (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, L1 | 7.38 to 7.42 (-O2), 7.00 to 7.40 (-O3) | 8.87 to 8.93 |
| `sum`, two limbs, L1 | 7.21 to 7.31 | 7.29 to 7.33 |
| `dot`, two limbs, L1 | 7.20 to 7.26 | 7.24 to 7.33 |

| The product of polynomials, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `conv`, one limb, 16 coefficients: ns per term | 0.84 to 0.87 (-O2), 0.80 to 0.82 (-O3) | 0.77 to 0.78 (-O2), 0.69 to 0.70 (-O3) |
| `conv`, two limbs, 16 coefficients: ns per term | 9.54 to 9.75 (-O2), 9.44 to 9.46 (-O3) | 9.46 to 9.68 |
| `conv`, one limb, 16, over the plain loop of T (FMA) | 1.29 to 1.33 | 1.31 to 1.32 (-O2), 1.19 to 1.20 (-O3) |
| `conv`, two limbs, 16, over the plain loop of T (FMA) | 14.6 (-O2), 15.2 to 15.6 (-O3) | 16.2 to 16.4 |
| `conv`, two limbs, 16, over the double-word loop written out | 1.03 to 1.04 | 1.04 |
| `conv`, one limb, 64 coefficients: ns per term | 0.97 to 1.01 | 0.95 to 0.97 (-O2), 0.83 to 0.84 (-O3) |
| `conv`, two limbs, 64 coefficients: ns per term | 10.0 to 10.3 | 10.0 to 10.2 |
| `conv`, one limb, 64, over the plain loop of T (FMA) | 1.07 to 1.10 | 1.38 to 1.40 (-O2), 1.21 (-O3) |
| `conv`, two limbs, 64, over the plain loop of T (FMA) | 10.9 to 11.1 | 14.6 to 14.7 |
| `conv`, two limbs, 64, over the double-word loop written out | 1.00 to 1.01 | 1.02 |
| `conv`, one limb, 512 coefficients: ns per term | 1.38 to 1.41 | 1.35 to 1.40 |
| `conv`, two limbs, 512 coefficients: ns per term | 10.2 to 10.4 | 10.2 to 10.4 |
| `conv`, one limb, 512, over the plain loop of T (FMA) | 1.00 to 1.01 | 1.02 to 1.04 |
| `conv`, two limbs, 512, over the plain loop of T (FMA) | 7.38 to 7.42 | 7.69 to 7.75 |
| `conv`, two limbs, 512, over the double-word loop written out | 1.00 | 1.01 to 1.02 |

- **One limb costs what the loop of `T` in the same order costs; the order is what makes it fast.**
  On Zen 2, `sum` of one limb takes 0.20 to 0.24 ns per element in L1 and `dot` 0.32 to 0.36, 0.87
  to 1.13 times the plain loop of `double` written in the same lane order (the guards cost nothing
  measurable there, [question 15](#15-the-guards-of-supplied-factors)), and 0.23 to 0.28 of the
  naive loop of one chain, which waits for each addition.
- **Two limbs: a sum or a dot product costs 2.6 to 2.9 ns per element**, 11 to 14 times the loop of
  `double` in the same order for `sum`, 7 to 9 times for `dot`. Against the code written instead it
  is cheap: with `kairn::sequential` it costs what the double-word loop written out from the
  listings costs (0.99 to 1.03, the same additions in the same chain), in the default order 0.25 to
  0.28 of it (four chains). As an accurate sum of doubles, `sum` of two limbs takes 1.7 to 1.8 times
  Sum2's time in the default order and 6.8 to 7.2 times sequentially (`dot`: 1.5 to 1.7 and 5.7 to
  6.8 times Dot2's), for a result of two limbs where Sum2's is one `double`
  ([question 17](#17-accuracy-for-the-price)); for `float`, with eight lanes, the default order
  takes 0.96 to 0.98 of Sum2's time and 0.91 to 0.93 of Dot2's. `sum_fast` takes 0.62 to 0.68 of
  the time of `sum`.
- **The maps** (`add`, `scale`, `axpy`) cost 0.15 to 0.23 ns per element of one limb and 0.5 to
  2.0 of two in L1 on Zen 2. Against the plain loop of `T` it depends on whether the compiler
  vectorizes that loop: GCC 13 at `-O2` does not, and Kairn's packed loop is faster (0.56 to 0.68 of
  `x + y`, `x a` and `a x + y` of one limb, 0.29 to 0.49 of the double-word maps written out);
  GCC 13 at `-O3` and Clang 18 do, and Kairn's maps then take 0.9 to 2.1 times the loop of `T` for
  one limb and 1.2 to 2.1 times the double-word maps written out: the guards (18 to 44% of `add`,
  [question 15](#15-the-guards-of-supplied-factors)) and the test of every element written for the
  flag `finite` that a map returns. Beyond the cache every map of one limb is bound by memory (0.78
  to 1.09 ns per element, 0.85 to 0.99 of the loop of `T`).
- **The price of `kairn::sequential`: 3.7 to 4.5 times the default order for `sum` and `dot` in L1
  and the last-level cache on Zen 2, 7.0 to 9.0 times for `float`**, about the number of lanes (4
  and 8); beyond the cache 2.1 to 2.3 for one limb, which is then bound by memory, and 3.6 to 4.0
  for two. For the maps, whose order changes no bit, the loop of one lane costs 4.3 to 5.1 times
  the default with GCC 13 and 0.87 to 1.26 with Clang 18, which vectorizes the sequential loop of a
  map itself. A program that asks for the same bits on every machine pays that factor on its
  reductions.
- **The product of polynomials**: 0.69 to 1.41 ns per term for one limb on Zen 2 (1.0 to 1.4 times
  the plain loop with an FMA; the guards of both factors cost up to 15% for short polynomials,
  [question 15](#15-the-guards-of-supplied-factors)), 9.4 to 10.4 ns for two limbs, 1.00 to 1.04
  times the double-word loop written out: each coefficient is a dot product in the sequential order,
  one chain, so the lanes do not help.
- **`norm_upper`** costs 0.11 to 0.19 ns per element in L1, 0.27 to 0.56 of a plain loop of the
  largest magnitude.

### 14. Short arrays and the check at entry

What does a call of `sum` or `dot` on a short array cost, and how much of it is the check of the
floating-point environment that every function on arrays makes at entry, in every build? The check
is `detail::check_batch_environment` (`include/kairn/environment.hpp`): one read of the control
register (`stmxcsr` and a load on x86-64, `mrs` of `FPCR` on AArch64) and three tests (four on AArch64),
then, on a failure, `KAIRN_ENVIRONMENT_FAILURE` with the message; the headers have a macro for what
a failure does, none to leave the check out. So the comparison is of two programs built from the same sources:
`kairn-bench-m2-LEVEL`, and `kairn-bench-m2-nocheck-LEVEL`, compiled against a copy of `include/`
made by `bench/entry_check.py`, in which the body of that one function is `return true;` (the copy
differs from `include/` in those lines only, and is not committed). The two were run one after the
other, three pairs per configuration, with the same filter (`m2k/`, `m2w/`, `m2a/tp/`); "the check"
is the time of a function in the first minus its time in the second, and its share is that difference
over the time with the check. The machine code was looked at: in every configuration the read of the
register is inside the loop of the calls, once per call (the compilers do not move it out). The
functions (`m2k`, `bench/m2_batch.cpp`): 256 calls of `sum` or `dot` of one or two limbs, each on a
window of $n$ = 1, 2, 4, 8, 16, 64 or 1024 elements of one array in L1 (the window of call $j$ starts
at element $j$), each result stored; independent calls (KIND `tp`), and dependent ones (`lat`), in
which the window of a call starts at an index computed from the result of the call before it (always
the next one, but the address waits for the result), so that the calls cannot overlap. The control
is the generated loop called directly (variant `kairn`), the same in both programs. The length is
read at run time (kernel `NAME_nN`), as a program's is; the same calls with the length known to the
compiler (`NAME_kN`) are timed beside them.

| Short arrays, independent calls: ns per call, with the check (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 1.42 to 1.62 (-O2), 1.11 to 1.3 (-O3) | 1.49 to 1.61 (-O2), 1.42 to 1.61 (-O3) | 6.91 to 7.22 | 6.95 to 7.27 |
| `sum`, one limb, n = 16 | 3.66 to 3.84 (-O2), 3.11 to 3.53 (-O3) | 3.94 to 4.47 (-O2), 4.12 to 4.16 (-O3) | 7.71 to 7.83 | 7.53 to 7.68 |
| `sum`, one limb, n = 64 | 10.7 to 12.1 (-O2), 10.2 to 11.5 (-O3) | 11.2 to 12.8 (-O2), 11.9 to 12.4 (-O3) | 14.4 (-O2), 13 to 13.1 (-O3) | 8.82 to 8.88 (-O2), 13.3 (-O3) |
| `sum`, one limb, n = 1024 | 363 to 391 (-O2), 343 to 390 (-O3) | 340 to 382 (-O2), 364 to 385 (-O3) | 223 to 226 | 213 to 219 |
| `sum`, two limbs, n = 1 | 4.56 to 4.62 (-O2), 4.24 to 4.62 (-O3) | 2.82 to 3.21 (-O2), 1.96 to 2.19 (-O3) | 32 to 32.2 (-O2), 8.11 to 8.12 (-O3) | 30.4 to 30.7 |
| `sum`, two limbs, n = 4 | 7.57 to 8.48 (-O2), 7.87 to 8.51 (-O3) | 7.11 to 7.75 (-O2), 7.89 to 8.25 (-O3) | 33 to 33.2 (-O2), 29.5 (-O3) | 31.6 to 31.9 |
| `sum`, two limbs, n = 64 | 220 to 245 (-O2), 225 to 245 (-O3) | 216 to 244 (-O2), 218 to 246 (-O3) | 182 to 188 | 184 to 185 |
| `dot`, one limb, n = 1 | 1.42 to 1.61 (-O2), 1.17 to 1.3 (-O3) | 1.5 to 1.62 (-O2), 1.52 to 1.62 (-O3) | 6.91 to 7.23 | 6.92 to 7.26 |
| `dot`, two limbs, n = 1 | 4.67 to 5.31 (-O2), 4.79 to 5.31 (-O3) | 3.52 to 3.84 (-O2), 3.02 to 3.28 (-O3) | 34.2 to 34.5 (-O2), 9.16 (-O3) | 30.4 to 30.6 |

| The check at entry, independent calls: ns per call (with the check minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.524 to 0.657 (-O2), 0.514 to 0.604 (-O3) | 0.477 to 0.734 (-O2), 0.491 to 0.542 (-O3) | 5.27 to 5.39 | 5.69 to 5.73 |
| `sum`, one limb, n = 2 | 0.65 to 0.721 (-O2), 0.5 to 0.546 (-O3) | 0.278 to 0.35 (-O2), 0.193 to 0.3 (-O3) | 5.03 to 5.08 | 5.38 to 5.51 |
| `sum`, one limb, n = 4 | 1.03 to 1.09 (-O2), 0.202 to 0.285 (-O3) | 0.235 to 0.44 (-O2), 0.254 to 0.292 (-O3) | 5.33 to 5.49 | 5.23 to 5.41 |
| `sum`, one limb, n = 8 | 0.269 to 0.438 (-O2), -0.359 to -0.278 (-O3) | 0.14 to 0.806 (-O2), -0.219 to 0.004 (-O3) | 5.1 to 5.28 | 5.36 to 5.5 |
| `sum`, one limb, n = 16 | 0.208 to 0.507 (-O2), -0.35 to 0.046 (-O3) | -0.058 to 1.01 (-O2), -0.03 to 0.081 (-O3) | 4.89 to 4.92 (-O2), 4.55 to 4.59 (-O3) | 5.05 to 5.15 |
| `sum`, one limb, n = 64 | 0.16 to 0.323 (-O2), -0.39 to 0.09 (-O3) | -0.09 to 1.55 (-O2), -0.43 to 0.27 (-O3) | 4.15 to 4.16 (-O2), 2.39 to 2.44 (-O3) | 1.86 to 1.91 (-O2), 3.56 to 3.69 (-O3) |
| `sum`, one limb, n = 1024 | 17.8 to 27.4 (-O2), -2.5 to 2.5 (-O3) | -34.4 to 40.2 (-O2), -31.3 to -4.6 (-O3) | 9.5 to 10.2 (-O2), 5.8 to 6.4 (-O3) | 1.7 to 2.8 (-O2), 2.9 to 3.9 (-O3) |
| `sum`, two limbs, n = 1 | 0.043 to 0.33 (-O2), -0.149 to 0.229 (-O3) | 0.283 to 0.667 (-O2), 0.023 to 0.05 (-O3) | 1.4 to 1.54 (-O2), 3.2 to 3.22 (-O3) | 1.57 to 1.9 (-O2), 1.77 to 1.97 (-O3) |
| `sum`, two limbs, n = 2 | 0.148 to 0.468 (-O2), -0.184 to 0.471 (-O3) | -0.009 to 0.634 (-O2), -0.013 to 0.32 (-O3) | 0.27 to 0.44 (-O2), 0.77 to 0.82 (-O3) | 1.37 to 1.83 (-O2), 1.58 to 1.82 (-O3) |
| `sum`, two limbs, n = 4 | 0.092 to 0.74 (-O2), -0.197 to 0.743 (-O3) | -0.457 to 0.978 (-O2), 0.387 to 0.485 (-O3) | 1.66 to 1.84 (-O2), 0.91 to 1.01 (-O3) | 1.44 to 2.37 (-O2), 1.61 to 2.35 (-O3) |
| `sum`, two limbs, n = 8 | -1.28 to 0.06 (-O2), -0.59 to 0.73 (-O3) | 0.24 to 1.2 (-O2), -0.26 to 0.56 (-O3) | 2.24 to 2.38 (-O2), 0.41 to 0.51 (-O3) | 0.77 to 1.31 (-O2), 0.84 to 1.43 (-O3) |
| `sum`, two limbs, n = 16 | 0.21 to 1.27 (-O2), -2.05 to 1.13 (-O3) | -1.63 to 4.58 (-O2), 0.42 to 0.46 (-O3) | 1.06 to 1.26 (-O2), 1.18 to 1.33 (-O3) | 0.94 to 1.18 (-O2), 0.97 to 1.43 (-O3) |
| `sum`, two limbs, n = 64 | -0.4 to 2.5 (-O2), -3.8 to 0.2 (-O3) | -2.8 to 30.4 (-O2), -3.4 to 0.3 (-O3) | 1.7 to 2.6 (-O2), 1 to 1.4 (-O3) | 0.5 to 1.5 (-O2), 0.8 to 1.6 (-O3) |
| `sum`, two limbs, n = 1024 | 5 to 371 (-O2), -168 to 99 (-O3) | -41 to 611 (-O2), -150 to 4 (-O3) | 1 to 6 (-O2), 0 to 7 (-O3) | -24 to 9 (-O2), -5 to 13 (-O3) |
| `dot`, one limb, n = 1 | 0.588 to 0.712 (-O2), 0.438 to 0.485 (-O3) | -0.016 to 0.21 (-O2), -0.013 to 0.007 (-O3) | 5.37 to 5.39 (-O2), 5.09 to 5.11 (-O3) | 5.38 to 5.41 |
| `dot`, one limb, n = 2 | 0.558 to 0.726 (-O2), 0.373 to 0.433 (-O3) | 0.233 to 0.374 (-O2), 0.277 to 0.36 (-O3) | 5.08 to 5.1 (-O2), 5.39 to 5.4 (-O3) | 5.37 to 5.4 (-O2), 4.69 to 5.39 (-O3) |
| `dot`, one limb, n = 4 | 0.389 to 0.569 (-O2), 0.156 to 0.231 (-O3) | 0.502 to 0.769 (-O2), 0.525 to 0.616 (-O3) | 5.24 to 5.41 | 5.09 to 5.33 |
| `dot`, one limb, n = 8 | 0.27 to 0.387 (-O2), 0.224 to 0.28 (-O3) | 0.388 to 0.698 (-O2), 0.414 to 0.539 (-O3) | 4.85 to 5.08 | 4.81 to 4.99 |
| `dot`, one limb, n = 16 | 0.27 to 0.278 (-O2), 0.211 to 0.388 (-O3) | 0.539 to 1.28 (-O2), 0.286 to 0.538 (-O3) | 4.26 to 4.41 | 4.5 to 4.53 (-O2), 4.17 to 4.25 (-O3) |
| `dot`, one limb, n = 64 | -0.7 to 0.26 (-O2), -0.67 to 0.16 (-O3) | -0.75 to 1.7 (-O2), -0.15 to 0.49 (-O3) | 2.15 to 2.24 | 3.84 to 4.21 (-O2), 1.11 to 1.19 (-O3) |
| `dot`, one limb, n = 1024 | -36 to -0.2 (-O2), -8.5 to 44.1 (-O3) | -43.9 to 41.4 (-O2), -21.2 to 0.9 (-O3) | 14.2 to 15.4 (-O2), 11.5 to 12.1 (-O3) | 6.5 to 11.9 (-O2), 7 to 8.8 (-O3) |
| `dot`, two limbs, n = 1 | -0.321 to 0.091 (-O2), 0.031 to 0.112 (-O3) | 0.368 to 1 (-O2), 0.121 to 0.213 (-O3) | 2.56 to 2.71 (-O2), 1.11 to 1.15 (-O3) | 1.32 to 1.64 (-O2), 1.46 to 1.74 (-O3) |
| `dot`, two limbs, n = 2 | -0.403 to 0.122 (-O2), -0.036 to 0.537 (-O3) | -0.475 to 1.12 (-O2), 0.469 to 0.77 (-O3) | 2.51 to 2.91 (-O2), 0.85 to 0.9 (-O3) | 1.87 to 2.38 (-O2), 2.02 to 2.45 (-O3) |
| `dot`, two limbs, n = 4 | -0.873 to 0.139 (-O2), -0.349 to 0.851 (-O3) | -0.494 to 2.08 (-O2), 0.314 to 0.452 (-O3) | 1.56 to 1.78 (-O2), -0.2 to -0.12 (-O3) | 0.85 to 1.18 (-O2), 0.92 to 1.26 (-O3) |
| `dot`, two limbs, n = 8 | -0.86 to 0.07 (-O2), -0.29 to 0.89 (-O3) | 0 to 2.61 (-O2), 0.66 to 1.22 (-O3) | 1.49 to 1.65 (-O2), 1.04 to 1.19 (-O3) | 1.24 to 1.82 (-O2), 1.5 to 1.98 (-O3) |
| `dot`, two limbs, n = 16 | 0.05 to 0.68 (-O2), -0.91 to 1.81 (-O3) | -0.73 to 5.69 (-O2), 1.41 to 2.15 (-O3) | 1.23 to 1.34 (-O2), 0.95 to 1.22 (-O3) | 0.89 to 1.2 (-O2), 0.78 to 1.34 (-O3) |
| `dot`, two limbs, n = 64 | -0.2 to 3.1 (-O2), -3.4 to 30.9 (-O3) | -15.9 to 23 (-O2), 0.8 to 4.7 (-O3) | 1.6 to 2.3 (-O2), 0.9 to 1.4 (-O3) | 0.7 to 2.2 (-O2), 1.4 to 2.8 (-O3) |
| `dot`, two limbs, n = 1024 | -7 to 51 (-O2), -77 to 458 (-O3) | -124 to 596 (-O2), -4 to 2 (-O3) | 2 to 6 (-O2), -5 to 5 (-O3) | -7 to 6 (-O2), -9 to 9 (-O3) |

| The check at entry, independent calls: its share of the call (1 - without over with) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.39 to 0.43 (-O2), 0.47 to 0.49 (-O3) | 0.34 to 0.47 (-O2), 0.34 to 0.40 (-O3) | 0.73 to 0.78 | 0.79 to 0.82 |
| `sum`, one limb, n = 2 | 0.46 to 0.51 (-O2), 0.44 to 0.48 (-O3) | 0.20 to 0.25 (-O2), 0.13 to 0.22 (-O3) | 0.69 to 0.70 | 0.76 to 0.78 |
| `sum`, one limb, n = 4 | 0.52 to 0.55 (-O2), 0.18 to 0.25 (-O3) | 0.14 to 0.25 (-O2), 0.16 to 0.18 (-O3) | 0.74 to 0.76 | 0.72 (-O2), 0.77 (-O3) |
| `sum`, one limb, n = 8 | 0.13 to 0.18 (-O2), -0.20 to -0.16 (-O3) | 0.05 to 0.25 (-O2), -0.09 to 0.00 (-O3) | 0.70 to 0.71 | 0.71 to 0.74 |
| `sum`, one limb, n = 16 | 0.06 to 0.14 (-O2), -0.12 to 0.01 (-O3) | -0.01 to 0.23 (-O2), -0.01 to 0.02 (-O3) | 0.63 (-O2), 0.58 to 0.59 (-O3) | 0.67 |
| `sum`, one limb, n = 64 | 0.02 to 0.03 (-O2), -0.04 to 0.01 (-O3) | -0.01 to 0.13 (-O2), -0.04 to 0.03 (-O3) | 0.29 (-O2), 0.18 to 0.19 (-O3) | 0.21 to 0.22 (-O2), 0.27 to 0.28 (-O3) |
| `sum`, one limb, n = 1024 | 0.05 to 0.08 (-O2), -0.01 to 0.01 (-O3) | -0.10 to 0.11 (-O2), -0.09 to -0.01 (-O3) | 0.03 to 0.05 | 0.01 to 0.02 |
| `sum`, two limbs, n = 1 | 0.01 to 0.07 (-O2), -0.04 to 0.06 (-O3) | 0.10 to 0.22 (-O2), 0.01 to 0.03 (-O3) | 0.04 to 0.05 (-O2), 0.39 to 0.40 (-O3) | 0.05 to 0.06 |
| `sum`, two limbs, n = 2 | 0.03 to 0.10 (-O2), -0.04 to 0.10 (-O3) | -0.00 to 0.14 (-O2), -0.00 to 0.08 (-O3) | 0.01 (-O2), 0.06 to 0.07 (-O3) | 0.03 to 0.04 |
| `sum`, two limbs, n = 4 | 0.01 to 0.09 (-O2), -0.03 to 0.10 (-O3) | -0.07 to 0.13 (-O2), 0.05 to 0.07 (-O3) | 0.03 to 0.06 | 0.05 to 0.07 |
| `sum`, two limbs, n = 8 | -0.09 to 0.00 (-O2), -0.04 to 0.05 (-O3) | 0.02 to 0.09 (-O2), -0.02 to 0.04 (-O3) | 0.01 to 0.05 | 0.02 to 0.03 |
| `sum`, two limbs, n = 16 | 0.01 to 0.04 (-O2), -0.06 to 0.03 (-O3) | -0.05 to 0.13 (-O2), 0.01 (-O3) | 0.02 | 0.02 |
| `sum`, two limbs, n = 64 | -0.02 to 0.01 | -0.01 to 0.13 (-O2), -0.02 to 0.00 (-O3) | 0.01 | 0.00 to 0.01 |
| `sum`, two limbs, n = 1024 | 0.00 to 0.08 (-O2), -0.04 to 0.02 (-O3) | -0.01 to 0.13 (-O2), -0.03 to 0.00 (-O3) | 0.00 | -0.01 to 0.00 |
| `dot`, one limb, n = 1 | 0.44 to 0.46 (-O2), 0.38 to 0.43 (-O3) | -0.01 to 0.14 (-O2), -0.01 to 0.01 (-O3) | 0.78 (-O2), 0.70 (-O3) | 0.74 to 0.78 |
| `dot`, one limb, n = 2 | 0.42 to 0.47 (-O2), 0.33 to 0.38 (-O3) | 0.16 to 0.26 (-O2), 0.20 to 0.24 (-O3) | 0.70 to 0.72 | 0.71 to 0.72 (-O2), 0.65 to 0.74 (-O3) |
| `dot`, one limb, n = 4 | 0.28 to 0.36 (-O2), 0.13 to 0.20 (-O3) | 0.29 to 0.41 (-O2), 0.32 to 0.33 (-O3) | 0.72 | 0.70 to 0.74 |
| `dot`, one limb, n = 8 | 0.13 to 0.17 (-O2), 0.09 to 0.12 (-O3) | 0.14 to 0.25 (-O2), 0.14 to 0.20 (-O3) | 0.64 to 0.67 | 0.64 (-O2), 0.68 to 0.69 (-O3) |
| `dot`, one limb, n = 16 | 0.07 to 0.10 | 0.14 to 0.29 (-O2), 0.07 to 0.14 (-O3) | 0.54 to 0.55 | 0.55 to 0.58 |
| `dot`, one limb, n = 64 | -0.05 to 0.02 (-O2), -0.05 to 0.01 (-O3) | -0.05 to 0.12 (-O2), -0.01 to 0.04 (-O3) | 0.13 to 0.14 | 0.26 to 0.28 (-O2), 0.07 to 0.08 (-O3) |
| `dot`, one limb, n = 1024 | -0.07 to -0.00 (-O2), -0.02 to 0.08 (-O3) | -0.09 to 0.08 (-O2), -0.04 to 0.00 (-O3) | 0.03 to 0.04 | 0.02 to 0.03 |
| `dot`, two limbs, n = 1 | -0.07 to 0.02 (-O2), 0.01 to 0.02 (-O3) | 0.11 to 0.27 (-O2), 0.04 to 0.08 (-O3) | 0.07 to 0.08 (-O2), 0.12 (-O3) | 0.04 to 0.06 |
| `dot`, two limbs, n = 2 | -0.06 to 0.02 (-O2), -0.01 to 0.08 (-O3) | -0.08 to 0.17 (-O2), 0.08 to 0.12 (-O3) | 0.05 to 0.07 | 0.05 to 0.06 |
| `dot`, two limbs, n = 4 | -0.09 to 0.01 (-O2), -0.04 to 0.08 (-O3) | -0.05 to 0.19 (-O2), 0.03 to 0.05 (-O3) | 0.04 to 0.05 (-O2), -0.01 to -0.00 (-O3) | 0.02 to 0.03 |
| `dot`, two limbs, n = 8 | -0.05 to 0.00 (-O2), -0.02 to 0.04 (-O3) | 0.00 to 0.13 (-O2), 0.04 to 0.07 (-O3) | 0.02 to 0.03 | 0.03 to 0.04 |
| `dot`, two limbs, n = 16 | 0.00 to 0.02 (-O2), -0.02 to 0.04 (-O3) | -0.02 to 0.14 (-O2), 0.04 to 0.05 (-O3) | 0.01 to 0.02 | 0.01 to 0.02 |
| `dot`, two limbs, n = 64 | -0.00 to 0.01 (-O2), -0.02 to 0.12 (-O3) | -0.07 to 0.10 (-O2), 0.00 to 0.02 (-O3) | 0.00 to 0.01 | 0.00 to 0.01 |
| `dot`, two limbs, n = 1024 | -0.00 to 0.01 (-O2), -0.02 to 0.10 (-O3) | -0.03 to 0.13 (-O2), -0.00 to 0.00 (-O3) | -0.00 to 0.00 | -0.00 to 0.00 |

| The check at entry, dependent calls: ns per call (with the check minus without) (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.457 to 0.5 (-O2), 0.335 to 0.367 (-O3) | 0.157 to 0.507 (-O2), 0.222 to 0.27 (-O3) | 0.846 to 0.862 (-O2), 1.29 to 1.3 (-O3) | 0.07 to 0.112 (-O2), 0.031 to 0.081 (-O3) |
| `sum`, one limb, n = 16 | 0.02 to 0.19 (-O2), -1.73 to 0.11 (-O3) | -0.13 to 1.75 (-O2), -0.73 to 0.31 (-O3) | 0.19 to 0.23 (-O2), 0.11 to 0.15 (-O3) | 0.12 to 0.21 (-O2), 0.17 to 0.19 (-O3) |
| `sum`, two limbs, n = 1 | 0.25 to 1.33 (-O2), 2.07 to 15.6 (-O3) | -4.31 to -2.37 (-O2), -3.6 to -1.71 (-O3) | 1.18 to 1.45 (-O2), 0.2 to 0.22 (-O3) | 1.25 to 1.58 (-O2), 1.42 to 1.56 (-O3) |
| `dot`, one limb, n = 1 | 0.835 to 3.96 (-O2), 5.08 to 5.36 (-O3) | 0.056 to 0.5 (-O2), 0.987 to 1.05 (-O3) | 0.07 to 0.103 (-O2), 0.322 to 0.332 (-O3) | 0.149 to 0.272 (-O2), 0.04 to 0.108 (-O3) |
| `dot`, two limbs, n = 1 | 0.04 to 0.18 (-O2), -0.18 to 0.41 (-O3) | -0.44 to 3.1 (-O2), -0.41 to -0.05 (-O3) | 2.28 to 2.36 (-O2), 0.05 to 0.15 (-O3) | 0.42 to 0.78 (-O2), 0.62 to 0.95 (-O3) |

| The check at entry is under 5%; 1% of the call from n = | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, independent | > 1024; > 1024 (-O2), 8; 64 (-O3) | > 1024; > 1024 (-O2), 8; 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) |
| `sum`, two limbs, independent | > 1024; > 1024 (-O2), 16; > 1024 (-O3) | > 1024; > 1024 (-O2), 8; 64 (-O3) | 16; 1024 (-O2), 4; 64 (-O3) | 8; 64 (-O2), 8; 64 (-O3) |
| `dot`, one limb, independent | 64; 1024 (-O2), > 1024; > 1024 (-O3) | > 1024; > 1024 (-O2), 64; 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) |
| `dot`, two limbs, independent | 1; > 1024 (-O2), > 1024; > 1024 (-O3) | > 1024; > 1024 (-O2), 64; 1024 (-O3) | 4; 1024 (-O2), 4; 64 (-O3) | 4; 1024 (-O2), 4; 1024 (-O3) |
| `sum`, one limb, dependent | 16; > 1024 (-O2), 4; > 1024 (-O3) | > 1024; > 1024 (-O2), 4; 64 (-O3) | 2; 64 (-O2), 4; 64 (-O3) | 1; 1024 (-O2), 1; 64 (-O3) |
| `sum`, two limbs, dependent | 8; > 1024 (-O2), 64; 1024 (-O3) | > 1024; > 1024 (-O2), 1; 64 (-O3) | 1; 4 (-O2), 1; 16 (-O3) | 1; 4 (-O2), 1; 8 (-O3) |
| `dot`, one limb, dependent | 16; 1024 (-O2), 64; > 1024 (-O3) | > 1024; > 1024 (-O2), 2; 2 (-O3) | 1; 16 (-O2), 1; 8 (-O3) | 1; 64 (-O2), 1; 64 (-O3) |
| `dot`, two limbs, dependent | 64; > 1024 (-O2), > 1024; > 1024 (-O3) | > 1024; > 1024 (-O2), 1; 1024 (-O3) | 2; 4 (-O2), 1; 1 (-O3) | 4; 4 (-O2), 4; 4 (-O3) |

| The check at entry: with over without, controls and longer arrays | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| control: the generated loop of `sum`, one limb, n = 1, with over without | 1.00 to 1.13 (-O2), 0.98 to 1.01 (-O3) | 0.92 to 1.15 (-O2), 0.93 to 1.01 (-O3) | 1.00 (-O2), 0.88 (-O3) | 1.00 |
| control: the generated loop of `sum`, one limb, n = 16, with over without | 1.00 to 1.01 (-O2), 0.89 to 1.01 (-O3) | 0.94 to 1.20 (-O2), 0.92 to 1.00 (-O3) | 1.00 to 1.01 (-O2), 1.09 to 1.13 (-O3) | 0.99 to 1.01 |
| control: the generated loop of `sum`, one limb, n = 1024, with over without | 0.99 to 1.02 (-O2), 0.96 to 1.00 (-O3) | 0.92 to 1.15 (-O2), 0.94 to 1.00 (-O3) | 0.98 to 1.02 | 1.00 to 1.01 |
| `sum`, one limb, 512 elements, with over without | 0.96 to 1.02 (-O2), 0.98 to 1.08 (-O3) | 1.02 to 1.08 (-O2), 1.00 to 1.03 (-O3) | 1.04 to 1.05 | 1.01 to 1.02 |
| `add`, one limb, 512 elements, with over without | 1.00 to 1.01 (-O2), 0.98 to 1.04 (-O3) | 0.97 to 1.06 (-O2), 0.92 to 1.01 (-O3) | 1.02 to 1.03 | 1.03 to 1.04 |
| `dot`, two limbs, 512 elements, with over without | 0.98 to 1.01 | 0.95 to 1.06 (-O2), 0.98 to 1.00 (-O3) | 1.00 | 1.00 to 1.01 |

- **On Zen 2 the check costs 4.8 to 5.7 ns per call of `sum` or `dot` of one limb up to 16
  elements, 64 to 82% of the call up to 8**: the call takes 6.9 to 7.7 ns, the loop alone 1.2 to
  2.7. That confirms the about 6 ns that [Functions on arrays](../../reference/batch.md#checks)
  states. From 64 elements the loop's work overlaps the read in part (1.1 to 4.2 ns, 7 to 29% of
  the call); at 1 024 elements the difference, 1.7 to 15 ns of a call of 213 to 368 ns (1 to 5%), is
  of the size by which the two programs differ on the same loop (the generated loop called
  directly: 0.98 to 1.02 times in the other program, 0.88 to 1.13 with GCC 13 at `-O3`). **So the
  check is under 5% of an independent call of one limb from 1 024 elements, and under 1% from about
  1 500 (`dot`) to 2 700 (`sum`) elements**: the read's 5 to 6 ns over the loop's 0.21 to 0.36 ns per
  element at 1 024, inferred from the two measurements, not measured at those lengths. For two
  limbs, whose loop is longer, it costs 0.4 to 3.2 ns per call up to 64 elements: under 5% from 4 to
  16 elements, under 1% from 64 or 1 024. In dependent calls, where the read is off the chain of the
  results, it costs 0 to 2.4 ns, under 5% from 1 to 4 elements.
- **On the M3 the read is cheap: 0.5 to 0.7 ns per call of one limb at one element, 34 to 49% of
  a call of 1.1 to 1.6 ns** (`dot` with GCC 16 0 to 0.2 ns), and from 8 elements it is within the
  noise of the pairs of programs (-0.4 to +1.6 ns up to 64 elements, up to ±44 ns at 1 024 elements,
  where the same loop called directly differs by up to 15% between the two programs: the machine
  was loaded by another author's campaign, [below](#how-the-third-part-was-measured)). The
  thresholds of the table are therefore the noise's on the M3, not the check's: from the read's
  0.5 to 0.7 ns and the M3's times per call, the check is under 5% of a call of one limb from about
  64 elements and under 1% from about 200, of two limbs under 5% from 8 and under 1% from 64
  (inferred, not measured).
- **[Functions on arrays](../../reference/batch.md#checks) also says that the check is "within the
  noise of the loop from about 64 elements of one limb"; measured, at 64 elements of one limb it is
  7 to 29% of an independent call on Zen 2**, and within the noise only from about 1 024.
- **What a short call costs besides the check.** A `sum` of two limbs of one element takes 30 to 32
  ns on Zen 2 with the length read at run time, 8.1 with GCC 13 at `-O3`: the lane order adds the
  four lane states, zero but for the elements, with three two-limb additions in a chain, about 24
  ns, which GCC 13 at `-O3` alone removes, by following the path on which no packed step ran and
  folding the additions of zeros ([below](#what-the-machine-code-shows-third-part)). A length the
  compiler knows changes a call by 0 to 13% (up to 41% for one limb at 64 elements with Clang 18 at
  `-O3`).
- **The controls**: the generated loops called directly, the same in both programs, take 0.98 to
  1.02 times their time in the other (0.88 to 1.13 with GCC 13 at `-O3`, for one limb at 1 and 16
  elements); the functions on arrays of 512 elements 1.00 to 1.05 times with the check.

**Short ball vectors of fixed length.** A downstream user of the ball vectors measured, with GCC 13
on x86-64 and `NDEBUG`, that a sum of two `BallVector<double, 2, N>` of N = 3, 7, 13, 18 took 1.2
to 3.0 times as long once the check was in every build (0.029 to 0.086 µs at N = 13), the
constructor at N = 13 42.0 ns instead of 10.1, their de Casteljau split 11 to 16% and their searches
6 to 21% more, where `kairn::environment_ok()` alone took 6.3 ns: more than one read of the register
explains. Their programs are not here; the operations they are made of are. The harness measures
the same operations (`bench/m2_bvs.cpp`, the variant `op`, with the generated loops on arrays as the control): `add(x, y, z)`, `z = x + y`, `sub`, `scale`, `half` and the
constructor from an `std::array` of centers and a radius, of `BallVector<double, k, N>` for k = 1, 2
and N = 3, 7, 13, 18, 80, on many vectors whose operands are in L1 (KIND `tp`) and in a chain of 256
operations each on the result of the one before (KIND `lat`), the time per operation; compiled twice:
all of them in one unit (backend `m2x`), and each operation of each size in a unit of its own
(`m2y`), as a client's file holds a few, since a compiler's decisions to inline depend on the size of
the unit. Three programs per configuration, run one after the other, three rounds: with the check,
without it (the copy of the headers above), and with a candidate change of the header, the
**cold variant** (`bench/entry_check.py copy --variant cold`): the hot path one read of the register
and one test of a mask (`stmxcsr`, `testl $0xe040`, a branch), the message and the call of
`KAIRN_ENVIRONMENT_FAILURE` moved into a function of their own marked `[[gnu::cold, gnu::noinline]]`.

| Short ball vectors, one operation per unit, many vectors: the check, ns per operation (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 0.221 to 0.287 (-O2), 0.238 to 0.41 (-O3) | 0.836 to 0.978 (-O2), 0.931 to 1.08 (-O3) | 2.01 to 2.24 (-O2), 4.26 to 4.31 (-O3) | 3.69 to 3.78 |
| `add(x, y, z)`, 2 limbs, N = 3 | -0.404 to 0.036 (-O2), 0.113 to 0.172 (-O3) | -0.57 to -0.043 (-O2), 0.17 to 0.338 (-O3) | 2.72 to 2.87 (-O2), 2.78 to 2.91 (-O3) | 1.68 to 1.89 (-O2), 1.73 to 1.84 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | -0.98 to 0.19 (-O2), 0.01 to 1.11 (-O3) | -1.97 to 0.68 (-O2), 0.22 to 0.32 (-O3) | 2.77 to 2.87 (-O2), 2.48 to 2.65 (-O3) | 2.02 to 2.21 (-O2), 2.03 to 2.16 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -1.75 to 0.11 (-O2), 0.06 to 1.17 (-O3) | -2.37 to 0.91 (-O2), 0.03 to 0.25 (-O3) | 4.53 to 4.64 (-O2), 4.37 to 4.47 (-O3) | 4.02 to 4.28 (-O2), 3.98 to 4.36 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -4.96 to 1.4 (-O2), 0.25 to 0.56 (-O3) | -7.12 to 0.28 (-O2), -4.11 to 0.45 (-O3) | 4.21 to 5.42 (-O2), 2.37 to 3.66 (-O3) | 2.62 to 4.31 (-O2), 3.6 to 4.65 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | -0.73 to 1.58 (-O2), -0.41 to 0.01 (-O3) | -1.42 to -0.63 (-O2), 1.81 to 2.15 (-O3) | 2.27 to 3.04 (-O2), 2.36 to 3.07 (-O3) | 0.44 to 3.77 (-O2), 2.01 to 2.34 (-O3) |
| `scale`, 2 limbs, N = 13 | -0.15 to 0.488 (-O2), -0.587 to 0.368 (-O3) | -0.029 to 0.17 (-O2), 0.36 to 0.96 (-O3) | 2.83 to 2.85 (-O2), 2.31 to 2.47 (-O3) | 2.82 to 2.98 (-O2), 2.84 to 2.96 (-O3) |
| `half`, 2 limbs, N = 13 | -0.21 to 0.32 (-O2), 0.19 to 0.88 (-O3) | -0.71 to 0.34 (-O2), -0.09 to 0.74 (-O3) | 1.6 to 1.78 (-O2), 3.33 to 3.53 (-O3) | 2.57 to 2.71 (-O2), 2.63 to 2.91 (-O3) |
| the constructor, 1 limb, N = 3 | 2.21 to 3.29 (-O2), 3.15 to 4.44 (-O3) | 1.07 to 1.26 (-O2), 0.617 to 0.987 (-O3) | 5.6 to 6.62 (-O2), 5.95 to 7.52 (-O3) | 18.2 to 18.6 |
| the constructor, 2 limbs, N = 3 | 2.81 to 11.4 (-O2), 4 to 12.8 (-O3) | 0.003 to 0.373 (-O2), 0.959 to 1.14 (-O3) | 5.45 to 6.32 (-O2), 5.8 to 6.36 (-O3) | 2.59 to 7.39 (-O2), 7.33 to 7.46 (-O3) |
| the constructor, 2 limbs, N = 13 | -0.01 to 0.72 (-O2), -0.17 to 1.91 (-O3) | -2.43 to 0.01 (-O2), -0.53 to 0.35 (-O3) | 1.66 to 2.06 (-O2), 5.05 to 5.55 (-O3) | 0.15 to 0.87 (-O2), 0.74 to 2.14 (-O3) |

| Short ball vectors, one operation per unit, many vectors: with the check over without (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 1.09 to 1.10 (-O2), 1.09 to 1.14 (-O3) | 1.33 (-O2), 1.31 to 1.39 (-O3) | 1.22 to 1.25 (-O2), 1.75 to 1.76 (-O3) | 1.78 to 1.80 |
| `add(x, y, z)`, 2 limbs, N = 3 | 0.93 to 1.01 (-O2), 1.02 to 1.03 (-O3) | 0.92 to 0.99 (-O2), 1.03 to 1.05 (-O3) | 1.11 to 1.12 (-O2), 1.16 to 1.17 (-O3) | 1.11 to 1.12 |
| `add(x, y, z)`, 2 limbs, N = 13 | 0.94 to 1.01 (-O2), 1.00 to 1.06 (-O3) | 0.89 to 1.04 (-O2), 1.01 to 1.02 (-O3) | 1.10 to 1.12 | 1.09 to 1.10 |
| `add(x, y, z)`, 2 limbs, N = 80 | 0.94 to 1.02 (-O2), 1.00 to 1.01 (-O3) | 0.92 to 1.00 (-O2), 0.96 to 1.01 (-O3) | 1.03 to 1.06 | 1.03 to 1.05 |
| `half`, 1 limb, N = 3 | 1.07 to 1.09 (-O2), 1.06 to 1.16 (-O3) | 1.06 (-O2), 1.10 to 1.14 (-O3) | 1.15 (-O2), 1.45 to 1.47 (-O3) | 1.37 to 1.39 |
| the constructor, 1 limb, N = 3 | 1.65 to 1.96 (-O2), 1.81 to 2.30 (-O3) | 1.25 to 1.33 (-O2), 1.20 to 1.31 (-O3) | 1.50 to 1.65 (-O2), 1.55 to 1.76 (-O3) | 4.02 to 4.10 |
| the constructor, 2 limbs, N = 13 | 1.00 to 1.03 (-O2), 0.99 to 1.06 (-O3) | 0.92 to 1.00 (-O2), 0.96 to 1.03 (-O3) | 1.04 to 1.06 (-O2), 1.29 to 1.32 (-O3) | 1.01 to 1.04 (-O2), 1.03 to 1.09 (-O3) |

| Short ball vectors, every size in one unit, many vectors: the check, ns per operation (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 2 limbs, N = 13 | -0.36 to 0.36 (-O2), 0.11 to 0.56 (-O3) | 0.06 to 0.21 (-O2), -0.18 to 1.45 (-O3) | 2.81 to 3 (-O2), 2.93 to 3.18 (-O3) | 1.96 to 2.12 (-O2), 1.96 to 2.23 (-O3) |
| the constructor, 1 limb, N = 7 | -1.85 to 0.16 (-O2), -1.19 to 3.56 (-O3) | 0.25 to 0.435 (-O2), 6.85 to 8.23 (-O3) | 4.71 to 4.82 (-O2), 7.58 to 8.06 (-O3) | -0.15 to 1.17 (-O2), -1.26 to 1.75 (-O3) |
| the constructor, 2 limbs, N = 3 | 1.7 to 3.01 (-O2), 1.81 to 2.91 (-O3) | -0.003 to 0.034 (-O2), 3.56 to 4.27 (-O3) | 5.44 to 6.32 (-O2), 8.98 to 10.3 (-O3) | 2.58 to 7.48 (-O2), 7.48 to 7.51 (-O3) |
| the constructor, 2 limbs, N = 7 | -0.38 to 0.63 (-O2), 0.84 to 1.44 (-O3) | -0.25 to 1.42 (-O2), 8.89 to 10.2 (-O3) | 2.51 to 2.95 (-O2), 10.9 to 11.8 (-O3) | -0.84 to 1.25 (-O2), 1.71 to 1.91 (-O3) |
| the constructor, 2 limbs, N = 13 | -0.59 to 0.01 (-O2), -1.3 to 0.09 (-O3) | -1.98 to 0.09 (-O2), 20.4 to 21.6 (-O3) | -1.15 to -0.98 (-O2), 12 to 12.4 (-O3) | 0.24 to 0.76 (-O2), 0.45 to 2.1 (-O3) |

| The same with the cold variant (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 2 limbs, N = 13 | -0.98 to -0.29 (-O2), -0.83 to 1.04 (-O3) | -1.23 to 1.82 (-O2), -4.89 to 1.21 (-O3) | 2.73 to 2.93 (-O2), 2.5 to 2.71 (-O3) | 2.18 to 2.29 (-O2), 2.15 to 2.43 (-O3) |
| the constructor, 1 limb, N = 7 | -0.39 to 2.27 (-O2), -0.47 to 1.63 (-O3) | 0.846 to 1.23 (-O2), -0.869 to 0.14 (-O3) | 5.04 to 5.12 (-O2), 5.66 to 6.27 (-O3) | -0.03 to 1.76 (-O2), -1.17 to 1.81 (-O3) |
| the constructor, 2 limbs, N = 3 | 1.92 to 3.19 (-O2), 1.79 to 2.17 (-O3) | -0.161 to 0.536 (-O2), -0.976 to 0.011 (-O3) | 5.46 to 6.36 (-O2), 5.63 to 6.28 (-O3) | 7.57 to 7.81 |
| the constructor, 2 limbs, N = 7 | -4.48 to 0.29 (-O2), -2.54 to -1.53 (-O3) | -0.29 to 2.24 (-O2), -0.812 to 0.805 (-O3) | 2.72 to 2.97 (-O2), 6.07 to 6.91 (-O3) | 1.22 to 1.63 (-O2), -0.13 to 1.93 (-O3) |
| the constructor, 2 limbs, N = 13 | -0.85 to 0.89 (-O2), -3.68 to 1.14 (-O3) | -2.14 to 3.01 (-O2), -2.88 to 0.09 (-O3) | 1.3 to 1.36 (-O2), 3.29 to 3.78 (-O3) | 0.95 to 2.06 (-O2), 0.54 to 6.13 (-O3) |

- **On Zen 2 the check costs most operations of short ball vectors the read or less, up to 7 ns**:
  1.2 to 1.8 times as long for one limb and N = 3 (operations of 8 to 20 ns), 1.01 to 1.27 for
  two limbs (operations of 10 to 210 ns), in both units and at both levels. **The downstream user's
  1.2 to 3.0 times for `x + y` of two limbs is not reproduced here**: `z = x + y` of
  `BallVector<double, 2, N>`, N = 3 to 18, costs 0.5 to 5.4 ns more with the check, 1.01 to 1.26
  times as long (at N = 13 26.7 to 50.9 ns with the check), in the units of one operation and in the
  unit of every size.
- **Where the check costs more than the read, the compiler changed what it inlines.** Of the 120
  operations, sizes and kinds of each compiler, level and unit, the check cost more than 7 ns in every pair of
  runs only for constructors, in three groups: (1) with Clang 18, at both levels and in both units,
  the constructor of `BallVector<double, 1, 3>` (+18 to +20 ns, 4.0 to 4.1 times) and at `-O3` of
  `BallVector<double, 2, 3>` (+7 to +9); (2) with GCC 13 at `-O3`, in the unit of every size, the
  constructors of N = 3 to 80 (+7 to +14 ns, 1.1 to 1.6 times); (3) one chain, below. The machine
  code: without the check
  Clang inlines the constructor's body (`BallVector::make`) into the loop and unrolls the constructor's
  loop for the three entries; with it, the loop calls `BallVector<double, 1, 3>::make` for every
  vector (it no longer fits Clang's cost of inlining), and the vector goes through memory around the
  call: three stores of 8 bytes into the object and a load of 32 after the call
  (`vmovsd %xmm1,(%rsp)` ... `call ...4makeEd` ... `vmovups (%rsp),%ymm0`). GCC 13 tells why it
  declines (`-fopt-info-inline-missed`): `--param inline-unit-growth limit reached` for 56 call sites
  of `BallVector::make` in the unit of every size with the check, 20 without it, and "will not early
  inline ... call is cold and code would grow at least by 26" with the check only: the check's
  inline code (the read, three tests, two addresses of strings and the call of `detail::fail` at every
  operation, and at `-O3` sometimes `fail`'s own `fprintf` inlined) is counted against the unit's
  budget, which runs out sooner. In a client's unit with many operations this is what makes more
  than the read: which calls stay calls depends on the whole unit, and the cost moves with it.
  And where the code is the same but for the check, where it falls in memory can move a loop by
  more than the read: the chain of constructors of `BallVector<double, 2, 80>` with GCC 13 at `-O2`
  (+21 to +25 ns, 13%; at `-O3` -2 to -5) has the same 128 instructions with the check as 117
  without, but its three loops cross 32-byte boundaries with it and fit within them without it; the
  product of `BallVector<double, 1, 64>` with GCC 13 at `-O3` in `m2_bv.cpp` (+455 to +543 ns, 12 to
  14%) has the same six instructions in its inner loop, which starts 16 bytes past a 32-byte
  boundary with the check and on one without it (inferred from the addresses, not measured).
- **The cold variant removes the excess of GCC and part of Clang's.** With the report out of line and
  cold, GCC 13 at `-O3` inlines the constructor again (`bv_make_1_seq` and `bv_make_2_seq` inlined as
  without the check: 226 and 264 instructions against 86 and 127 with the check as it is), and its
  excess drops to +1 to +7 ns, the read; Clang 18 still calls `make` for one limb and N = 3 (+18
  to +20 ns at `-O2`, +12 to +14 at `-O3`) and for two limbs and N = 3 (+7 to +10); the chain of
  constructors of `BallVector<double, 2, 80>` with GCC 13 at `-O2` keeps its +19 to +22, a matter of
  where its loops fall. Where nothing was inlined differently, the cold variant costs what the
  check costs (1 to 6 ns). Tried on the copy too, not
  timed: with the cold report **and** `KAIRN_FORCEINLINE` on `BallVector::make` and on the
  constructor from an `std::array`, Clang 18 inlines the whole constructor at both levels (87
  instructions, no call but the loop's end and the cold report); with the forced inlining alone, the
  constructor is called instead of `make`, which moves the call and the store through memory one
  level up. A change of the header that removes the excess measured here is therefore the pair: the
  report cold and out of line (`environment.hpp`), and the constructors and `make` forced inline
  (`ball_vector.hpp`); it is not made here.
- **On the M3 something beyond the read shows too.** In many independent operations the check
  costs most of them nothing measurable (within ±3 ns, the noise of the loaded machine), but for the
  same two causes as on Zen 2: with the check, Apple clang calls `BallVector<double, 1, 3>::make`, which
  without it is inlined (the object of the unit has no copy of it), and with the cold variant calls
  the constructor instead (+2 to +13 ns for N = 3, 1.6 to 3.6 times); GCC 16 at `-O3`, in the unit
  of every size, stops inlining constructors (+3 to +22 ns for N = 3 to 18; the loop of N = 13 of two
  limbs 98 instructions with the check, 237 without it and 265 with the cold variant). And in chains, where each operation waits for the
  one before, the check costs short operations of one limb 4 to 9 ns, consistently over the three
  rounds and with the cold variant as well: the chain of `scale` of `BallVector<double, 1, 3>` with
  Apple clang takes 1.57 to 1.71 times as long with the check (15 to 20 ns), and of
  `add(x, y, z)` with GCC 16 1.9 to 2.6 times (11 to 14 ns). There the two loops are the same
  instructions but for the read and its four tests (`mrs x8, FPCR`, `tst`, `b.ne`, three `tbnz`):
  the read of FPCR costs a chain on the M3 several nanoseconds where it costs a loop of independent
  calls half of one. Why the core makes the chain wait was not measured.

### 15. The guards of supplied factors

What do the guards of rule R3 cost, those of the factors a program supplies in particular
([Architecture](../architecture.md#the-kernel-ir), "The factors of a fused operation")? Every
function on arrays calls its loop on supplied arrays, whose steps pass each value they add, and the
factors of their fused operations, through the guard $a + 0$: `dot` of one limb is three operations
per term (two guards and the fused multiply-add) where the loop on stored arrays has one; `scale` of
two limbs guards the two limbs and `a`; `conv` of one limb both factors of each term;
`Accumulator::add_product` both factors (one limb) or every limb (two). The loops on stored arrays of
the generated headers are the same steps without the guards (`dot_1`, `scale_2`, `conv_1`, `sum_1`,
`add_k`, `axpy_k`, the kernels `acc_mul_1`, `acc_mul_2`): this question calls them directly, as a
control only (variant `bare`; no function of the library calls them), against the loop the public
function calls (`kairn`, the public function without its check at entry), on the same arrays. Where
nothing is guarded the two are the same loop: `scale` of one limb, `dot`, `axpy` (but for `y`) and
`conv` of two limbs, whose factors are on the pending list of the factor rule. The data and the
sizes are those of question 13.

| The guards: the loop with them over the same loop without, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `dot`, one limb (3 operations per term against 1), L1 | 1.01 to 1.02 (-O2), 0.83 to 1.01 (-O3) | 0.99 to 1.00 |
| `axpy`, one limb (y guarded), L1 | 1.09 to 1.13 | 1.15 to 1.16 |
| `axpy`, two limbs, a of T (y guarded), L1 | 1.00 | 1.00 |
| `axpy`, two limbs, a of two limbs (y guarded), L1 | 0.99 to 1.00 | 1.00 |
| `scale`, two limbs (the limbs and a guarded), L1 | 1.16 | 1.16 |
| `sum`, one limb (the element guarded), L1 | 1.02 (-O2), 0.97 to 0.99 (-O3) | 1.01 to 1.02 |
| `sum`, two limbs (the limbs guarded), L1 | 1.01 | 1.01 to 1.02 |
| `add`, one limb (both guarded), L1 | 1.19 to 1.20 (-O2), 1.19 to 1.45 (-O3) | 1.43 to 1.44 |
| `add`, two limbs (every limb guarded), L1 | 1.19 | 1.20 to 1.21 |
| `dot`, one limb (3 operations per term against 1), LLC | 1.00 to 1.01 | 0.99 to 1.00 |
| `axpy`, one limb (y guarded), LLC | 0.98 to 0.99 | 0.98 to 0.99 |
| `axpy`, two limbs, a of T (y guarded), LLC | 0.99 to 1.00 | 0.99 to 1.01 |
| `axpy`, two limbs, a of two limbs (y guarded), LLC | 0.99 to 1.00 | 0.99 to 1.00 |
| `scale`, two limbs (the limbs and a guarded), LLC | 1.14 to 1.15 | 1.14 to 1.15 |
| `sum`, one limb (the element guarded), LLC | 1.00 to 1.01 | 0.99 to 1.00 |
| `sum`, two limbs (the limbs guarded), LLC | 1.01 to 1.02 | 1.02 to 1.03 |
| `add`, one limb (both guarded), LLC | 0.96 to 0.97 | 0.97 to 0.98 |
| `add`, two limbs (every limb guarded), LLC | 1.19 | 1.19 to 1.20 |
| `conv`, one limb, 16 coefficients (both factors guarded) | 1.06 to 1.10 (-O2), 1.13 to 1.15 (-O3) | 1.02 to 1.03 |
| `conv`, one limb, 64 coefficients (both factors guarded) | 1.13 to 1.14 (-O2), 0.90 to 1.02 (-O3) | 1.14 to 1.15 |
| `conv`, one limb, 512 coefficients (both factors guarded) | 1.00 to 1.02 | 1.01 |

| The guards against the control of T, double (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `dot`, one limb, with the guards, over the plain FMA loop in the same order, L1 | 1.00 to 1.03 (-O2), 0.89 to 0.91 (-O3) | 1.04 to 1.05 |
| `dot`, one limb, without them, over the same, L1 | 0.99 to 1.01 (-O2), 0.89 to 1.10 (-O3) | 1.05 to 1.06 |
| `scale`, two limbs, with them, over `x a` of T, L1 | 1.56 to 1.57 (-O2), 2.88 to 2.96 (-O3) | 5.98 to 6.02 |
| `scale`, two limbs, without them, over the same, L1 | 1.34 to 1.35 (-O2), 2.49 to 2.54 (-O3) | 5.15 to 5.18 |
| `conv`, one limb, 16, with them, over the plain FMA loop | 1.20 to 1.25 (-O2), 1.26 to 1.30 (-O3) | 1.16 to 1.17 |
| `conv`, one limb, 16, without them, over the same | 1.10 to 1.15 | 1.13 to 1.15 |

| The guards of the accumulator: with over without, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add_product`, one limb (both factors guarded), L1 | 1.01 | 1.00 |
| `add_product`, two limbs (every limb guarded), L1 | 1.00 | 1.00 |
| `add_product`, one limb, the public member over the kernels without the guards, L1 | 1.03 to 1.04 | 1.00 |
| `add_product`, two limbs, the same, L1 | 1.00 | 1.00 |
| `add_product`, one limb (both factors guarded), LLC | 1.00 | 1.00 |
| `add_product`, two limbs (every limb guarded), LLC | 1.00 | 1.00 |
| `add_product`, one limb, the public member over the kernels without the guards, LLC | 1.00 to 1.01 | 1.00 |
| `add_product`, two limbs, the same, LLC | 1.00 | 1.00 |

- **The guards of supplied factors cost nothing where the loop waits for a chain, and up to 17%
  where it is bound by its throughput.** `dot` of one limb, three operations per term where the loop
  on stored arrays has one, takes 0.98 to 1.02 times that loop on Zen 2: each lane waits for its fused
  multiply-add, and the two guards are off that chain; `add_product` of the accumulator, one and two
  limbs, 1.00 to 1.01 for the same reason. `scale` of two limbs, whose loop has no chain, takes 1.14
  to 1.17 times the loop without the guards; `conv` of one limb 1.02 to 1.15 for polynomials of 16
  and 64 coefficients and 1.00 to 1.02 for 512, where the coefficients' long chains dominate.
- **Which of it is the guards**: against the loop of `T`, `scale` of two limbs costs 1.4 to 6.0
  times `x a` of `double` with its guards and 1.3 to 5.2 without them: the guards are the 14 to 17%
  between the two, the double-word product and the test of each element the rest; `dot` of one
  limb costs the plain loop with an FMA in the same order with and without them (0.89 to 1.06).
- **The guards of the additions** (rule R3 for the values added, not the factors), for comparison:
  `add` 1.18 to 1.44 in L1, `axpy` 1.08 to 1.16 for one limb and 0.99 to 1.02 for two, `sum` 0.97 to
  1.03; in the last-level cache, where the maps of one limb wait for the memory, 0.96 to 0.99.
- Where nothing is guarded the two loops are the same: `scale` of one limb, and `dot`, `axpy` (but
  for `y`) and `conv` of two limbs, whose factors are on the pending list of the factor rule.

### 16. The accumulator

What does an `Accumulator` cost per term against `sum` and `dot` over the same array, and what do
partial sums cost, as a program makes them across threads? `add` and `add_product` in a loop over
the arrays of question 13 (in L1 and in the last-level cache), one accumulator, element after
element; a two-limb accumulator fed values of `double` (`add(double)`, `add_product(double, double)`:
an accurate sum and dot product of doubles); the array cut into 4 or 16 contiguous parts, one
accumulator for each, one after another, then merged in order (single-threaded here: the cost of the
partial accumulators and the merges, not of threads); element $i$ to accumulator $i \bmod W$, as the
lane order deals them, merged from the first; and `merge` of 256 accumulators into one, `sum()`,
`error_bound()` and `ball()` of each of 256 accumulators, the time per call. Each accumulator's state
is checked against the generated kernels called directly on a state of plain `T` (variant `kairn`)
byte for byte, and its running sum against the exact sum of its terms within its own
`error_bound()`. The sums and dot products it is compared with are in the same runs.

| The accumulator: ns per element (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, one limb, L1 | 1.3 to 1.31 | 0.884 to 0.897 |
| `add_product`, one limb, L1 | 1.53 | 1.48 to 1.5 |
| `add`, two limbs, L1 | 10.2 | 10.1 to 10.2 |
| `add_product`, two limbs, L1 | 10.2 | 10.2 to 10.3 |
| `add` of a value of T, two limbs, L1 | 10.1 to 10.2 | 10.1 to 10.3 |
| `add` into 16 accumulators merged, two limbs, L1 | 12.2 to 12.3 | 9.98 to 10.1 |
| `add` into W accumulators in the lane order, two limbs, L1 | 4.82 to 4.83 | 3.99 to 4.05 |

| The accumulator over the functions on arrays (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, one limb, over `sum` sequential, L1 | 1.47 (-O2), 1.52 (-O3) | 1.03 |
| `add`, one limb, over `sum`, L1 | 5.50 to 5.65 | 4.50 to 4.51 |
| `add_product`, one limb, over `dot` sequential, L1 | 1.05 | 1.03 |
| `add`, two limbs, over `sum` sequential, L1 | 1.00 | 1.00 |
| `add`, two limbs, over `sum`, L1 | 3.82 to 3.92 | 3.91 to 3.92 |
| `add_product`, two limbs, over `dot` sequential, L1 | 1.00 | 0.98 to 0.99 |
| `add` of T into two limbs, over `sum` of two limbs of the same data, sequential, L1 | 1.00 | 1.00 |
| 4 accumulators merged over one, one limb, L1 | 2.38 to 2.44 (-O2), 2.37 to 2.43 (-O3) | 0.92 to 0.93 |
| 16 accumulators merged over one, two limbs, L1 | 1.20 to 1.21 | 0.99 |
| W accumulators in the lane order over one, one limb, L1 | 3.20 to 3.37 (-O2), 0.45 to 0.46 (-O3) | 0.47 |
| W accumulators in the lane order over one, two limbs, L1 | 0.47 | 0.39 to 0.40 |
| W accumulators in the lane order over `sum`, two limbs, L1 | 1.80 to 1.85 | 1.54 to 1.56 |

| The accumulator: ns per call | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `merge`, 1 limb | 0.902 to 0.91 | 0.811 to 0.825 |
| `merge`, 2 limbs | 10.2 | 10.1 to 10.3 |
| `sum()`, 1 limb | 1.21 (-O2), 0.933 to 0.934 (-O3) | 0.826 to 0.843 |
| `sum()`, 2 limbs | 1.34 (-O2), 1.25 to 1.26 (-O3) | 1.18 to 1.2 |
| `error_bound()`, 1 limb | 6.35 (-O2), 4.72 (-O3) | 6 to 6.17 |
| `error_bound()`, 2 limbs | 6.64 to 6.66 (-O2), 5.53 to 5.55 (-O3) | 6.48 to 6.6 |
| `ball()`, 1 limb | 7.28 to 7.34 (-O2), 6.62 to 6.63 (-O3) | 8.04 to 8.18 |
| `ball()`, 2 limbs | 7.97 to 7.99 (-O2), 7.29 to 7.32 (-O3) | 8.54 to 8.68 |

- **An accumulator fed term by term costs what the sequential `sum` and `dot` cost**: on Zen 2 1.00
  to 1.05 times them for two limbs (10.1 to 10.3 ns per term) and for `add_product` of one limb (1.5
  ns), 1.00 to 1.52 for `add` of one limb (0.88 to 1.31 ns), and 3.8 to 5.8 times the default order
  of the functions on arrays, which runs four chains. A two-limb accumulator fed values of `double`,
  an accurate sum of doubles, costs what `sum` of two limbs of the same data costs sequentially
  (1.00).
- **Partial sums, as threads would make them** (one after another here, in one thread: what the
  partial accumulators and the merges cost, not the threads): 4 or 16 contiguous parts, one
  accumulator for each, merged in order, cost 1.00 times one accumulator with Clang 18 for two limbs
  and 1.20 to 1.23 with GCC 13; for one limb 0.70 to 1.00 with Clang 18 and 1.7 to 2.6 with GCC 13.
  W accumulators fed in the lane order, as a program would write the lane order by hand, take 0.39
  to 0.47 of one for two limbs, 1.5 to 1.9 times `sum` of two limbs, and for one limb 0.45 to 0.47
  but with GCC 13 at `-O2` 3.2 to 3.4 times one accumulator (17.6 to 19.2 times `sum`): GCC keeps the
  array of accumulators in memory there, each addition loading and storing its running sum, and
  compiles the saturating count into 128-bit integer operations (`vpsubq`, `vpunpcklqdq`); at `-O3`
  the states stay in registers.
- **The results**: a `merge` costs a two-limb addition (10.1 to 10.3 ns in a chain; 0.8 to 0.9 for
  one limb); `sum()` 0.8 to 1.3 ns; `error_bound()` 4.7 to 6.6 ns, the two kernels of the bound and of
  the radius; `ball()` 6.6 to 8.7 ns, the radius and the constructor of the ball.
- **The guards of `add_product`** cost nothing (1.00 to 1.01, [question 15](#15-the-guards-of-supplied-factors)),
  and the public member costs what its kernels without the guards cost (1.00 to 1.04).

### 17. Accuracy for the price

How much more accurate are the sums and dot products of two limbs than those of one, and than the
compensated sum a numerical programmer writes, and how far above the error actually made is the bound
the library states? `kairn-bench-m2-accuracy` (`bench/m2_accuracy.cpp`) makes data of `double` of a
chosen condition as Ogita, Rump and Oishi make it ("Accurate sum and dot product", 2005, Algorithm
6.1, GenDot): for a dot product of $n$ terms, the first half with random signs and exponents spread
over $[0, b/2]$, $b = \log_2$ of the condition, the second half with exponents falling from $b/2$ to
0, each $y_i$ chosen so that the dot product so far nearly cancels (from the exact dot product of the
terms before it, rounded), then shuffled; for a sum of $n$ numbers, the two parts $p_i + e_i$ (by an
FMA) of the $n/2$ products of such a dot product, shuffled. Ten targets from $10^4$ to $10^{40}$, and
two regimes without cancellation by construction: numbers uniform in $[-1, 1]$ ("random signs") and
in $[1, 2)$ ("positive", condition 1); lengths 10 to $10^6$, 20 trials of each up to $10^3$, 10 at
$10^4$, 4 beyond. The exact results are computed by an exact sum of the harness's own
(`bench/m2_exact.hpp`: a fixed-point number of 2240 bits that holds every `double` and every sum of
them exactly; a product enters as its two parts by an FMA), not by the project's oracle; the error of
a result of two limbs is its exact difference with that sum. The condition is
$\kappa = \sum\lvert x_i\rvert / \lvert\sum x_i\rvert$ (for a dot product of the products), computed
exactly; the targets of GenDot are approximate, so the tables group the trials by the condition they
reached. Methods: the naive loop of `double` (`s = s + x[i]`, `s = s + x[i] * y[i]`, contraction off);
`sum` and `dot` of one limb, default and `kairn::sequential`; the same of two limbs on the same data
(the second limbs zero: an accurate sum of doubles with Kairn); Sum2 and Dot2 of the same authors,
whose result is one `double`; and an `Accumulator` of one and of two limbs fed the numbers or pairs
in order. The bounds: `traits<Expansion<double, k>>::sum(n).unit` times $\sum\lvert x_i\rvert$ (for a
dot product `dot(n)`, `unit` times $\sum\lvert x_i y_i\rvert$ plus `tiny`), and the accumulators'
`error_bound()`. No error made was above its bound, in any trial of any configuration. The errors do
not depend on the compiler or the level: the four configurations of Zen 2 give the same numbers,
which the tables give once.

| Sums, linux (4 lanes): relative error, median over the trials, by condition | naive loop | Kairn, one limb | Sum2 | Kairn, two limbs | Accumulator, two limbs |
|---|---|---|---|---|---|
| n = 1000, condition 1e0 to 1e3 (40 trials) | 6.8e-16 | 1.9e-16 | 4.2e-17 | 0.0e+00 | 0.0e+00 |
| n = 1000, condition 1e4 to 1e7 (20 trials) | 1.9e-11 | 1.8e-11 | 4.1e-17 | 1.3e-27 | 1.8e-27 |
| n = 1000, condition 1e8 to 1e11 (20 trials) | 7.2e-08 | 6.0e-08 | 4.0e-17 | 5.7e-24 | 6.6e-24 |
| n = 1000, condition 1e12 to 1e15 (20 trials) | 1.1e-03 | 4.3e-04 | 4.0e-17 | 5.5e-20 | 4.0e-20 |
| n = 1000, condition 1e16 to 1e19 (20 trials) | 8.2e+00 | 7.1e+00 | 5.3e-15 | 4.1e-16 | 1.9e-16 |
| n = 1000, condition 1e20 to 1e23 (20 trials) | 3.1e+04 | 1.8e+04 | 7.7e-12 | 1.1e-12 | 3.2e-12 |
| n = 1000, condition 1e24 to 1e27 (20 trials) | 5.7e+08 | 4.0e+08 | 2.9e-07 | 4.1e-08 | 7.0e-08 |
| n = 1000, condition 1e28 to 1e31 (20 trials) | 5.5e+12 | 5.2e+12 | 1.1e-03 | 2.4e-04 | 4.3e-04 |
| n = 1000, condition 1e32 to 1e35 (22 trials) | 7.3e+16 | 2.4e+16 | 3.1e+01 | 7.2e+00 | 1.8e+00 |
| n = 1000, condition 1e36 to 1e39 (20 trials) | 4.8e+20 | 3.3e+20 | 2.4e+05 | 1.5e+04 | 3.7e+04 |
| n = 1000, condition 1e40 to 1e43 (18 trials) | 2.5e+24 | 2.7e+24 | 1.3e+09 | 1.8e+08 | 1.4e+08 |
| n = 1000000, condition 1e0 to 1e3 (8 trials) | 4.5e-14 | 1.2e-14 | 2.0e-17 | 0.0e+00 | 0.0e+00 |
| n = 1000000, condition 1e8 to 1e11 (5 trials) | 2.5e-08 | 4.8e-08 | 2.6e-17 | 3.7e-24 | 1.6e-23 |
| n = 1000000, condition 1e12 to 1e15 (6 trials) | 2.5e-01 | 3.3e-01 | 6.4e-15 | 1.7e-17 | 7.2e-18 |
| n = 1000000, condition 1e16 to 1e19 (3 trials) | 1.9e+02 | 1.1e+04 | 2.6e-11 | 2.0e-13 | 2.8e-13 |
| n = 1000000, condition 1e20 to 1e23 (6 trials) | 4.9e+07 | 5.7e+07 | 1.8e-06 | 3.5e-09 | 4.7e-09 |
| n = 1000000, condition 1e24 to 1e27 (3 trials) | 4.1e+11 | 7.1e+10 | 6.1e-03 | 1.8e-05 | 4.7e-05 |
| n = 1000000, condition 1e28 to 1e31 (5 trials) | 4.0e+14 | 1.7e+15 | 7.2e+00 | 1.1e-01 | 1.5e-01 |
| n = 1000000, condition 1e32 to 1e35 (4 trials) | 5.9e+18 | 1.2e+19 | 8.1e+05 | 3.0e+03 | 1.7e+03 |
| n = 1000000, condition 1e36 to 1e39 (4 trials) | 1.0e+23 | 1.2e+23 | 2.6e+09 | 3.7e+07 | 4.2e+07 |
| n = 1000000, condition 1e40 to 1e43 (4 trials) | 1.7e+27 | 1.3e+27 | 9.4e+12 | 6.9e+10 | 1.5e+11 |

| Sums, linux: the stated bound over the error made, median (smallest) over the trials | Kairn, one limb | one limb, sequential | two limbs | two limbs, sequential | Accumulator, one limb | Accumulator, two limbs |
|---|---|---|---|---|---|---|
| positive, n = 10 | 17 (5.2), exact in 2 of 20 | 16 (5.5), exact in 1 of 20 | –, exact in 20 of 20 | –, exact in 20 of 20 | 18 (6.1), exact in 1 of 20 | –, exact in 20 of 20 |
| positive, n = 100 | 2.2e+02 (55) | 64 (15) | –, exact in 20 of 20 | –, exact in 20 of 20 | 65 (15) | –, exact in 20 of 20 |
| positive, n = 1000 | 1.2e+03 (3e+02) | 2.2e+02 (67) | –, exact in 20 of 20 | –, exact in 20 of 20 | 2.2e+02 (67) | –, exact in 20 of 20 |
| positive, n = 10000 | 2.5e+03 (1.4e+03) | 5.3e+02 (2.5e+02) | –, exact in 10 of 10 | –, exact in 10 of 10 | 5.3e+02 (2.5e+02) | –, exact in 10 of 10 |
| positive, n = 100000 | 5.6e+03 (4.6e+03) | 3.1e+03 (7.7e+02) | –, exact in 4 of 4 | –, exact in 4 of 4 | 3.1e+03 (7.7e+02) | –, exact in 4 of 4 |
| positive, n = 1000000 | 2.2e+04 (9.6e+03) | 5.9e+03 (2.4e+03) | –, exact in 4 of 4 | –, exact in 4 of 4 | 5.9e+03 (2.4e+03) | –, exact in 4 of 4 |
| random signs, n = 10 | 19 (8.7), exact in 14 of 20 | 24 (13), exact in 15 of 20 | –, exact in 20 of 20 | –, exact in 20 of 20 | 27 (14), exact in 15 of 20 | –, exact in 20 of 20 |
| random signs, n = 100 | 6.5e+02 (2.8e+02), exact in 5 of 20 | 6.5e+02 (1.5e+02), exact in 1 of 20 | –, exact in 20 of 20 | –, exact in 20 of 20 | 6.5e+02 (1.5e+02), exact in 1 of 20 | –, exact in 20 of 20 |
| random signs, n = 1000 | 1e+04 (1.6e+03) | 3.7e+03 (1.3e+03) | –, exact in 20 of 20 | –, exact in 20 of 20 | 3.7e+03 (1.3e+03) | –, exact in 20 of 20 |
| random signs, n = 10000 | 5.5e+04 (2.8e+04) | 5.7e+04 (1.4e+04) | –, exact in 10 of 10 | –, exact in 10 of 10 | 5.7e+04 (1.4e+04) | –, exact in 10 of 10 |
| random signs, n = 100000 | 8.5e+05 (5.6e+05) | 1.9e+06 (6.7e+05) | –, exact in 4 of 4 | –, exact in 4 of 4 | 1.9e+06 (6.7e+05) | –, exact in 4 of 4 |
| random signs, n = 1000000 | 1.1e+07 (2.3e+06) | 4.3e+06 (3.6e+06) | –, exact in 4 of 4 | –, exact in 4 of 4 | 4.3e+06 (3.6e+06) | –, exact in 4 of 4 |
| condition 1e4 to 1e40, n = 10 | 1.1e+02 (9.3) | 56 (10) | 1.2e+03 (37), exact in 14 of 200 | 6.6e+02 (43), exact in 9 of 200 | 62 (11) | 9.8e+02 (64), exact in 9 of 200 |
| condition 1e4 to 1e40, n = 100 | 3.4e+02 (39) | 2.6e+02 (41) | 1.5e+03 (2.7e+02) | 1.1e+03 (1.4e+02) | 2.6e+02 (41) | 1.5e+03 (1.9e+02) |
| condition 1e4 to 1e40, n = 1000 | 1.7e+03 (2.9e+02) | 1.5e+03 (1.8e+02) | 8.2e+03 (1.3e+03) | 7.2e+03 (7.3e+02) | 1.5e+03 (1.8e+02) | 9.6e+03 (9.8e+02) |
| condition 1e4 to 1e40, n = 10000 | 1.3e+04 (2.1e+03) | 1.3e+04 (1.5e+03) | 5.7e+04 (1.3e+04) | 5.2e+04 (7.6e+03) | 1.3e+04 (1.5e+03) | 7e+04 (1e+04) |
| condition 1e4 to 1e40, n = 100000 | 1.5e+05 (1.7e+04) | 1.4e+05 (1.9e+04) | 5.2e+05 (3.9e+04) | 4.8e+05 (1.2e+05) | 1.4e+05 (1.9e+04) | 6.4e+05 (1.6e+05) |
| condition 1e4 to 1e40, n = 1000000 | 1.5e+06 (1.6e+05) | 1.3e+06 (2.9e+05) | 6.1e+06 (7.5e+05) | 3.7e+06 (5.6e+05) | 1.3e+06 (2.9e+05) | 5e+06 (7.5e+05) |

| Dot products, linux (4 lanes): relative error, median over the trials, by condition | naive loop | Kairn, one limb | Dot2 | Kairn, two limbs | Accumulator, two limbs |
|---|---|---|---|---|---|
| n = 1000, condition 1e0 to 1e3 (40 trials) | 8.5e-16 | 3.7e-16 | 4.8e-17 | 1.7e-32 | 4.6e-32 |
| n = 1000, condition 1e4 to 1e7 (20 trials) | 2.8e-11 | 2.8e-11 | 3.0e-17 | 2.6e-27 | 2.5e-27 |
| n = 1000, condition 1e8 to 1e11 (20 trials) | 2.1e-07 | 2.2e-07 | 4.9e-17 | 7.6e-24 | 1.8e-23 |
| n = 1000, condition 1e12 to 1e15 (20 trials) | 3.1e-03 | 1.8e-03 | 4.4e-17 | 7.3e-20 | 1.2e-19 |
| n = 1000, condition 1e16 to 1e19 (20 trials) | 9.6e+00 | 9.8e+00 | 7.7e-15 | 1.4e-15 | 1.2e-15 |
| n = 1000, condition 1e20 to 1e23 (20 trials) | 8.1e+04 | 8.6e+04 | 7.7e-11 | 3.1e-12 | 2.7e-12 |
| n = 1000, condition 1e24 to 1e27 (20 trials) | 1.4e+09 | 1.6e+09 | 1.1e-06 | 9.3e-08 | 1.6e-07 |
| n = 1000, condition 1e28 to 1e31 (20 trials) | 7.4e+12 | 7.1e+12 | 5.7e-03 | 7.0e-04 | 6.3e-04 |
| n = 1000, condition 1e32 to 1e35 (20 trials) | 6.8e+16 | 7.4e+16 | 3.1e+01 | 3.0e+00 | 8.2e+00 |
| n = 1000, condition 1e36 to 1e39 (20 trials) | 4.5e+20 | 3.4e+20 | 7.0e+05 | 4.7e+04 | 1.6e+05 |
| n = 1000, condition 1e40 to 1e43 (20 trials) | 4.0e+24 | 5.0e+24 | 3.7e+09 | 4.0e+08 | 2.2e+08 |
| n = 1000000, condition 1e0 to 1e3 (8 trials) | 1.8e-14 | 1.4e-14 | 2.8e-17 | 5.8e-31 | 1.8e-30 |
| n = 1000000, condition 1e8 to 1e11 (5 trials) | 6.3e-08 | 4.3e-08 | 3.7e-17 | 1.5e-24 | 6.4e-24 |
| n = 1000000, condition 1e12 to 1e15 (5 trials) | 3.3e-04 | 1.0e-03 | 2.4e-17 | 3.7e-20 | 2.4e-20 |
| n = 1000000, condition 1e16 to 1e19 (4 trials) | 1.0e+03 | 1.8e+03 | 2.5e-10 | 2.1e-13 | 8.2e-14 |
| n = 1000000, condition 1e20 to 1e23 (3 trials) | 9.6e+04 | 2.2e+04 | 3.9e-09 | 7.0e-12 | 5.9e-12 |
| n = 1000000, condition 1e24 to 1e27 (6 trials) | 6.8e+10 | 1.0e+11 | 6.9e-04 | 2.3e-05 | 8.0e-06 |
| n = 1000000, condition 1e28 to 1e31 (3 trials) | 1.6e+15 | 2.7e+14 | 1.1e+01 | 2.1e-01 | 4.5e-02 |
| n = 1000000, condition 1e32 to 1e35 (6 trials) | 2.3e+19 | 7.6e+19 | 3.7e+05 | 5.5e+03 | 3.8e+03 |
| n = 1000000, condition 1e36 to 1e39 (4 trials) | 1.9e+23 | 6.3e+22 | 4.3e+09 | 1.1e+07 | 4.2e+07 |
| n = 1000000, condition 1e40 to 1e43 (4 trials) | 2.7e+27 | 4.3e+27 | 1.1e+14 | 4.5e+11 | 2.6e+11 |

| Dot products, linux: the stated bound over the error made, median (smallest) over the trials | Kairn, one limb | one limb, sequential | two limbs | two limbs, sequential | Accumulator, one limb | Accumulator, two limbs |
|---|---|---|---|---|---|---|
| positive, n = 10 | 19 (6.1) | 27 (6.1) | 1e+02 (35), exact in 6 of 20 | 98 (35), exact in 3 of 20 | 27 (6.1) | 98 (35), exact in 3 of 20 |
| positive, n = 100 | 1.7e+02 (55) | 1.2e+02 (16) | 2e+03 (4.8e+02), exact in 1 of 20 | 4.7e+02 (1e+02) | 1.2e+02 (16) | 4.7e+02 (1e+02) |
| positive, n = 1000 | 6.4e+02 (2.2e+02) | 1.9e+02 (50) | 5.1e+03 (1.3e+03) | 1.2e+03 (3.8e+02) | 1.9e+02 (50) | 1.2e+03 (3.8e+02) |
| positive, n = 10000 | 4.5e+03 (9.6e+02) | 5.7e+02 (2.6e+02) | 1.4e+04 (6.8e+03) | 3.9e+03 (8.7e+02) | 5.7e+02 (2.6e+02) | 3.9e+03 (8.7e+02) |
| positive, n = 100000 | 5.7e+03 (3.1e+03) | 1.8e+03 (1.5e+03) | 2.9e+05 (3.4e+04) | 1.6e+05 (1.1e+04) | 1.8e+03 (1.5e+03) | 1.6e+05 (1.1e+04) |
| positive, n = 1000000 | 1.3e+05 (6e+03) | 9.7e+03 (3.1e+03) | 1e+05 (5.8e+04) | 2.8e+04 (2e+04) | 9.7e+03 (3.1e+03) | 2.8e+04 (2e+04) |
| random signs, n = 10 | 56 (7.2) | 68 (20) | –, exact in 20 of 20 | –, exact in 20 of 20 | 68 (20) | –, exact in 20 of 20 |
| random signs, n = 100 | 6.7e+02 (2.9e+02) | 6.2e+02 (1.2e+02) | 2.5e+03 (2.1e+03), exact in 16 of 20 | 2.3e+03 (1.3e+03), exact in 15 of 20 | 6.2e+02 (1.2e+02) | 2.3e+03 (1.3e+03), exact in 15 of 20 |
| random signs, n = 1000 | 6.3e+03 (2e+03) | 5.8e+03 (1.5e+03) | 8.4e+04 (1.9e+04), exact in 2 of 20 | 4.9e+04 (6.7e+03), exact in 2 of 20 | 5.8e+03 (1.5e+03) | 4.9e+04 (6.7e+03), exact in 2 of 20 |
| random signs, n = 10000 | 1.9e+05 (2e+04) | 4.1e+04 (7.9e+03) | 8.6e+05 (1.5e+05) | 5.4e+05 (1.5e+05) | 4.1e+04 (7.9e+03) | 5.4e+05 (1.5e+05) |
| random signs, n = 100000 | 2.8e+06 (6.1e+05) | 4.6e+05 (1e+05) | 3.1e+06 (2.6e+06) | 2e+06 (8.3e+05) | 4.6e+05 (1e+05) | 2e+06 (8.3e+05) |
| random signs, n = 1000000 | 3.7e+06 (2.2e+06) | 9.4e+06 (2e+06) | 9.1e+07 (1.7e+07) | 5.6e+07 (1.2e+07) | 9.4e+06 (2e+06) | 5.6e+07 (1.2e+07) |
| condition 1e4 to 1e40, n = 10 | 46 (9.3) | 47 (10) | 3.8e+02 (36), exact in 1 of 200 | 3.9e+02 (42) | 47 (10) | 3.9e+02 (42) |
| condition 1e4 to 1e40, n = 100 | 3e+02 (40) | 2.4e+02 (30) | 1.5e+03 (2e+02) | 1.3e+03 (1.9e+02) | 2.4e+02 (30) | 1.3e+03 (1.9e+02) |
| condition 1e4 to 1e40, n = 1000 | 1.4e+03 (1.8e+02) | 1.3e+03 (1.5e+02) | 9.5e+03 (8.6e+02) | 7.2e+03 (8e+02) | 1.3e+03 (1.5e+02) | 7.2e+03 (8e+02) |
| condition 1e4 to 1e40, n = 10000 | 1.3e+04 (2.2e+03) | 1.1e+04 (1.8e+03) | 8.7e+04 (9.6e+03) | 6.1e+04 (8.1e+03) | 1.1e+04 (1.8e+03) | 6.1e+04 (8.1e+03) |
| condition 1e4 to 1e40, n = 100000 | 1.6e+05 (3.2e+04) | 1.5e+05 (3.4e+04) | 7.1e+05 (1.8e+05) | 4.9e+05 (1.3e+05) | 1.5e+05 (3.4e+04) | 4.9e+05 (1.3e+05) |
| condition 1e4 to 1e40, n = 1000000 | 2.2e+06 (3.1e+05) | 1.3e+06 (2.4e+05) | 7.4e+06 (1.8e+06) | 5.2e+06 (7e+05) | 1.3e+06 (2.4e+05) | 5.2e+06 (7e+05) |

- **One limb is as accurate as the naive loop; two limbs move the limit by sixteen digits.** The
  error of `sum` and `dot` of one limb, in either order, is that of the loop of `double`, about the
  condition number times $u$ (a relative error of $6 \times 10^{-8}$ at a condition of $10^8$ to
  $10^{11}$, no correct digit from about $10^{16}$); with two limbs, and with the accumulator of two
  limbs, about the condition times $u^2$: $2$ to $4 \times 10^{-16}$ at $10^{16}$ to $10^{19}$, no
  correct digit from about $10^{32}$.
- **Against Sum2 and Dot2**, whose result is one `double`: they give every digit of a `double` (a
  relative error of about $u/2$) up to a condition of about $10^{15}$ at $10^3$ terms and $10^{11}$
  at $10^6$, as Kairn's two limbs do once rounded; beyond, their error grows with the length faster
  than Kairn's: at $10^6$ terms and a condition of $10^{16}$ to $10^{31}$ Sum2's is 65 to 500 times
  that of Kairn's two limbs, at $10^3$ terms 4 to 13 times. Kairn's two limbs take 1.7 to 1.8 times
  Sum2's time in the default order and 7 times sequentially
  ([question 13](#13-the-functions-on-arrays)).
- **How far above the error made the stated bound is, as a function of the length**: for positive
  numbers, where the bound is closest, the median ratio of the bound to the error grows from 16 to
  27 at 10 terms to $5.9 \times 10^3$ to $1.3 \times 10^5$ at $10^6$, the smallest seen 5.2 (10
  terms, one limb, the default order); for random signs from 19 to 68 at 10 terms to $4 \times 10^6$
  to $9 \times 10^7$ at $10^6$; for the conditioned data from 46 to 110 at 10 terms to $1.3$ to
  $2.2 \times 10^6$ at $10^6$ with one limb, and from 380 to 1 200 to $3.7$ to $7.4 \times 10^6$ with
  two. The bound grows as the length, $\gamma_{n-1}(e)\sum\lvert x_i\rvert$; the error made grew
  more slowly in every regime. The accumulators' `error_bound()` is within a factor of two of the
  bound of `sum` and `dot` of the same limbs in the sequential order. No error was above its bound.
  Sums of two limbs of numbers without cancellation were exact in every trial (the exact sum fits in
  two limbs).

### 18. One radius for many centers

When is one radius per polynomial worth it? `BallVector<double, k, N>` against
`std::array<Ball<double, k>, N>` for N = 4, 8, 16, 64 and k = 1, 2 (`bench/m2_bv.cpp`): the time of
`add`, `sub`, `scale` (by a `double` that is not a power of two), `axpy`, the product of polynomials
(`convolution`, $2N - 1$ coefficients) and `norm_upper`, each applied to $256/N$ ball vectors whose
operands are in L1, the time per operation on a whole vector; the ball vector by the free functions
of `ball_vector.hpp`, the result written into a `BallVector`, in the default order and with
`kairn::sequential`; the balls by the operators of `Ball`, entry by entry (the product as each
coefficient's sum of products from its first term, the bound of the entries as the largest of
`max(upper_as(), -lower_as())`); and, as a control, the generated loop of each operation called
directly on arrays of the same values. Before timing, the ball vector's centers are checked against
the balls' byte for byte (the product of one limb, whose terms the loop fuses and a product of balls
rounds, within $8Nu$ times the largest product), and its one radius equal to the largest of the
balls' radii for `add`, `sub` and `scale` and at least it for `axpy`, which is what
[Ball vectors](../../reference/ball_vector.md#the-operations) says they compute and not a claim.

The widths (`ball_vector_widths` in the JSON, the same in every run of a compiler): three sets of
entries, each as one ball vector, whose radius is then the largest of the entries', and as $N$ balls:
radius 0 (exact data, the radii only rounding), one radius $2^{-22}$ for every entry (the centers
$\pm[1, 2)\,2^k$, $k \in [-8, 8]$: $2^{-30}$ of the largest), and radii spread from $2^{-50}$ to
$2^{-20}$ of each center's magnitude, log-uniformly (data known to different accuracies). Then one
operation, and two chains: Horner-like, $z \leftarrow 0.6875\,z + x$ by `axpy` with $X$ and $Y$ in
turn, 10 and 100 operations; de Casteljau-like, $z \leftarrow \tfrac12(z + \mathrm{shift}(z))$, each
entry averaged with its neighbour (the shift a rotation of the centers, exact, the radius kept; a sum
and a halving are two operations), 10 and 100 operations. The table gives the one radius over the
largest and over the median of the balls' radii.

| BallVector: ns per operation on the whole vector (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, 1 limb, N = 4 | 9.79 to 9.97 (-O2), 9.37 to 9.57 (-O3) | 8.44 to 8.63 |
| `add`, 1 limb, N = 64 | 28 to 28.9 (-O2), 20.1 to 20.6 (-O3) | 19.6 to 20 (-O2), 17.8 to 18.1 (-O3) |
| `add`, 2 limbs, N = 4 | 20.9 to 21.1 (-O2), 13 to 13.3 (-O3) | 10.5 to 10.7 |
| `add`, 2 limbs, N = 64 | 84.6 to 87.2 | 81.1 to 83.1 |
| `axpy`, 2 limbs, N = 16 | 56.5 to 57.4 (-O2), 44.9 to 46.1 (-O3) | 36.3 to 37.5 |
| `conv`, 2 limbs, N = 16 | 2455 to 2509 | 2432 to 2495 |
| `norm`, 2 limbs, N = 64 | 23.2 to 23.6 (-O2), 15.7 to 16 (-O3) | 15.3 to 15.6 |

| N balls over one BallVector (selection) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, 1 limb, N = 4 | 0.84 (-O2), 1.54 (-O3) | 0.77 |
| `add`, 1 limb, N = 16 | 2.50 to 2.51 (-O2), 2.66 to 2.67 (-O3) | 2.99 to 3.02 |
| `add`, 1 limb, N = 64 | 4.49 to 4.55 (-O2), 5.83 to 5.85 (-O3) | 5.77 to 5.78 (-O2), 6.09 to 6.12 (-O3) |
| `add`, 2 limbs, N = 4 | 1.15 to 1.16 (-O2), 1.84 to 1.85 (-O3) | 2.05 to 2.09 |
| `add`, 2 limbs, N = 16 | 3.08 to 3.11 (-O2), 2.70 to 2.71 (-O3) | 3.73 to 3.76 |
| `add`, 2 limbs, N = 64 | 4.46 to 4.48 (-O2), 4.14 to 4.18 (-O3) | 4.29 to 4.35 |
| `scale`, 2 limbs, N = 16 | 2.49 to 2.50 (-O2), 3.33 to 3.34 (-O3) | 3.50 to 3.56 |
| `axpy`, 2 limbs, N = 16 | 2.95 (-O2), 2.55 to 2.56 (-O3) | 4.21 to 4.26 |
| `conv`, 1 limb, N = 16 | 4.05 to 4.09 (-O2), 5.81 to 5.84 (-O3) | 5.05 to 5.11 |
| `conv`, 2 limbs, N = 16 | 1.07 to 1.08 | 1.01 to 1.02 |
| `norm`, 2 limbs, N = 16 | 7.94 to 8.00 (-O2), 8.70 to 8.85 (-O3) | 13.6 |

| Bytes | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---:|---:|---:|---:|
| `BallVector<double, 1, N>` | 40 | 72 | 136 | 520 |
| `std::array<Ball<double, 1>, N>` | 64 | 128 | 256 | 1024 |
| `BallVector<double, 2, N>` | 72 | 136 | 264 | 1032 |
| `std::array<Ball<double, 2>, N>` | 96 | 192 | 384 | 1536 |

| The one radius over the largest of the balls' radii, exact data (radius 0) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 2 limbs | 1 | 1 | 1 | 1 |
| `a x + y`, 2 limbs | 1 to 1.04 | 1 to 1.21 | 1.01 to 1.13 | 1.25 to 1.46 |
| product, 2 limbs | 6.39 to 6.4 | 15.3 to 36.5 | 29.6 to 118 | 86.7 to 106 |
| Horner-like, 100, 2 limbs | 1 | 1 to 1.16 | 1 to 1.09 | 1.1 to 1.18 |
| de Casteljau-like, 100, 2 limbs | 1.05 to 1.06 | 1.65 to 1.75 | 1.49 to 1.8 | 1.31 to 1.48 |

| The one radius over the median of the balls' radii, exact data (radius 0) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 2 limbs | 22.2 to 579 | 2.85 to 4.43 | 7.97 to 45.7 | 22 to 23.1 |
| `x a`, 2 limbs | 3.38 to 6.34 | 4.23 to 6.08 | 20.2 to 35.2 | 228 to 579 |
| product, 2 limbs | 95.4 to 282 | 305 to 1.92e+03 | 808 to 1.74e+03 | 1.81e+03 to 3.37e+03 |
| de Casteljau-like, 100, 2 limbs | 1.05 to 1.06 | 1.75 to 1.85 | 2.28 to 2.62 | 10.8 to 13.1 |

| The one radius over the largest of the balls' radii, radii spread from 2^-50 to 2^-20 of each center | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 2 limbs | 1 to 1.04 | 1 to 1.66 | 1.01 to 1.83 | 1.14 to 1.33 |
| `x a`, 2 limbs | 1 | 1 | 1 | 1 |
| product, 2 limbs | 4 to 4.47 | 9.91 to 10.7 | 16 to 21.2 | 57 to 57.6 |
| Horner-like, 100, 2 limbs | 1 to 1.06 | 1 to 1.95 | 1.01 to 1.82 | 1.09 to 1.47 |
| de Casteljau-like, 100, 2 limbs | 3.96 to 4 | 7.69 to 7.7 | 5.74 to 7.7 | 8.21 to 8.77 |

| The one radius over the median of the balls' radii, radii spread from 2^-50 to 2^-20 of each center | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 2 limbs | 45.4 to 69.1 | 2.7e+03 to 1.73e+04 | 1.21e+03 to 4.55e+03 | 5.5e+04 to 1.5e+05 |
| product, 2 limbs | 51.5 to 3.38e+03 | 1.17e+03 to 5.86e+03 | 553 to 2.43e+03 | 1.86e+03 to 3.17e+03 |
| Horner-like, 100, 2 limbs | 31.8 to 49.8 | 2.94e+03 to 2.1e+04 | 1.1e+03 to 4.37e+03 | 5.23e+04 to 1.44e+05 |
| de Casteljau-like, 100, 2 limbs | 3.96 to 4 | 7.99 | 9.09 to 13.8 | 35.8 to 75.5 |

- **Time: one radius pays from about 16 entries, and by four to six times at 64.** On Zen 2, an
  operation on a whole `BallVector` of 64 entries takes 0.16 to 0.30 of the same operation on 64
  balls (`add`, `sub`, `scale`, `axpy`: 3.3 to 6.2 times faster), 0.03 to 0.07 for `norm_upper`, and
  0.18 to 0.22 for the product of one limb; at 16 entries 2 to 4 times faster; at 4 entries the two
  cost about the same (0.71 to 2.1 times, the balls faster in a third of the configurations), the
  check at entry and the radius's few operations being then a large part of a vector's operation. The product of two limbs costs the same in both forms (0.85 to 1.09): it is a
  dot product per coefficient, sequential either way. The fast order gains over `kairn::sequential`
  only from about 16 entries (2.0 to 4.5 times at 64), and the public operations cost 0.8 to 1.4
  times their loops at 64 entries, 1.0 to 2.3 times at 4, the check included.
- **Bytes: 0.53 to 0.63 of the balls' for one limb, 0.67 to 0.75 for two** ($kN + 1$ numbers
  against $(k + 1)N$).
- **Width: nothing is lost where the entries have the same radius.** Started from one radius for
  every entry, the one radius after `add`, `sub`, `scale`, `axpy` and chains of 10 and 100 of them
  equals the largest and the median of the balls' radii (1.00), every entry's error having grown alike.
- **Exact data: the one radius is the largest rounding, and the median entry's is smaller.** From
  radius 0, the one radius equals the largest of the balls' radii after a sum, a difference and a
  scaling (1.00, as [Ball vectors](../../reference/ball_vector.md#the-operations) says they compute),
  1.0 to 1.6 times it after `axpy` and Horner-like chains; but it is 2 to 600 times the median
  entry's, whose center is smaller (the rounding of a center is relative to it, and the centers here
  span $2^{\pm 8}$).
- **Spread radii: the one radius is the widest entry's, up to twice it, and thousands of times the
  median's.** With radii from $2^{-50}$ to $2^{-20}$ of each center, the one radius after a sum or an
  `axpy` is 1.0 to 2.0 times the largest ball's radius (the two operands' largest radii, from
  different entries, add) and $30$ to $10^6$ times the median's.
- **The product of polynomials takes the largest centers for every coefficient**: 5 to 118 times
  the largest of the balls' radii, and $10^2$ to $10^4$ times the median's, from radius 0; 2.7 to 12
  times the largest from one radius for all, 4 to 86 times from spread radii. The de Casteljau-like chain averages neighbours: the
  balls' radii approach their mean while the one radius keeps the largest, 1.1 to 1.8 times the
  largest ball's after 100 operations from radius 0 and 3.8 to 8.8 times from spread radii.
  `norm_upper` gives the balls' largest bound in every case (1.00).
- **When is one radius per polynomial worth it**: when the coefficients are known to about the same
  accuracy and have comparable magnitudes, as those of a polynomial in the Bernstein basis, from
  about 16 coefficients (2 to 6 times faster, a third to a half less memory, the same width);
  not for few coefficients (no faster), nor for coefficients whose errors or magnitudes differ much,
  nor for products of polynomials whose coefficients differ much in size, where the one radius is
  that of the worst entry, as the reference page says.
- The centers of the widths were drawn with two calls of the harness's generator in one expression,
  whose order the compilers choose: GCC and Clang drew different centers of the same distribution,
  and each cell of the width tables is the range over the compilers.

### 19. Compile time of the functions on arrays and the ball vectors

What do the three headers cost a translation unit, alone and beside `kairn/kairn.hpp`, and what does
a function with many calls of them cost? The include units as question 11 measured `self_test()`
(`compile_time.py run`, the minimum wall time over seven compilations in rounds, `-O2` and `-O3`; on
Zen 2 pinned to an idle core of the second socket), each unit nothing but its includes:
`kairn/accumulator.hpp` alone (scalar code: `kairn/kairn.hpp` includes it), `kairn/batch.hpp` and
`kairn/ball_vector.hpp` alone and beside `kairn/kairn.hpp`, compiled as packed code (`-mavx2 -mfma`
on x86-64), as a unit that wants their fast order is, and `kairn/kairn.hpp` alone with the same flags
for comparison. And units of 100 and 1 000 calls in one function, in straight-line code, as question
12 measured the enclosure interface (`enclosure_costs.py compile`, the compiler's processor time, the
median of three compilations, its peak memory and the object): `--kind arrays`, the functions on
arrays of one and two limbs in turn (`sum`, `dot`, `add`, `scale`, `axpy`, `conv`, `norm_upper`),
each on arrays of 64 elements (32 coefficients) that no other call reads, each result stored;
`--kind ballvectors`, the operations of `BallVector<double, k, 8>` of one and two limbs in turn
(`add`, `sub`, `scale`, `axpy`, `convolution`, `norm_upper`), each on ball vectors of its own; and
"calls", the same units without Kairn, the views and ball vectors structures of `double`s and the
functions declared only. The setting `KAIRN_ENCLOSURE_CODE` changes neither header (their functions
are ordinary inline functions in every setting), so only the inline setting was compiled.

| Compile time of the headers, s (minimum wall time; -O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| an empty unit | 0.01; 0.01 | 0.04; 0.04 |
| `kairn/kairn.hpp` | 0.45; 0.45 | 0.70; 0.70 |
| `kairn/kairn.hpp`, as packed code | 0.44; 0.44 | 0.70; 0.70 |
| `kairn/accumulator.hpp` | 0.44; 0.44 | 0.70; 0.70 |
| `kairn/batch.hpp`, as packed code | 1.21; 1.21 | 1.57; 1.57 |
| `kairn/ball_vector.hpp`, as packed code | 1.26; 1.26 | 1.66; 1.66 |
| `kairn/kairn.hpp` and `kairn/batch.hpp`, as packed code | 1.24; 1.23 | 1.61; 1.61 |
| `kairn/kairn.hpp` and `kairn/ball_vector.hpp`, as packed code | 1.27; 1.26 | 1.66; 1.66 |

| arrays: compile time, s of processor time (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 1.60; 1.66 | 2.31; 2.52 |
| 100, calls | 0.22; 0.22 | 0.23; 0.23 |
| 1000, inline | 2.77; 2.85 | 8.85; 12.2 |
| 1000, calls | 3.49; 3.48 | 1.56; 1.58 |

| ballvectors: compile time, s of processor time (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 1.72; 1.91 | 2.12; 2.12 |
| 100, calls | 0.05; 0.05 | 0.06; 0.06 |
| 1000, inline | 2.40; 3.12 | 4.37; 4.36 |
| 1000, calls | 0.31; 0.31 | 0.21; 0.20 |

| The functions on arrays: object, KB (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 1000, inline | 88; 89 | 461; 652 |
| 1000, calls | 97; 97 | 111; 111 |

- **Each of the two headers costs a unit about a second.** On Zen 2 a unit that includes
  `kairn/batch.hpp` or `kairn/ball_vector.hpp` compiles in 1.21 to 1.27 s with GCC 13 and 1.57 to
  1.66 s with Clang 18, against 0.44 to 0.45 and 0.70 s for `kairn/kairn.hpp`; beside
  `kairn/kairn.hpp` they cost the same (1.23 to 1.27, 1.61 to 1.66): what they add is `soa.hpp` and
  `packed.hpp`, whose packed form includes the generated `gen/avx2.hpp` (1.3 MB; inferred from the
  includes, that header alone not timed here). `kairn/accumulator.hpp` alone costs what
  `kairn/kairn.hpp` costs, which includes it.
- **A function with many calls compiles quickly.** 1 000 calls of the functions on arrays in one
  function compile in 2.8 to 2.9 s with GCC 13 and 8.9 to 12.2 s with Clang 18 (1.6 to 2.5 s for
  100), the operations of ball vectors in 2.4 to 3.1 and 4.4 s (1.7 to 2.1 for 100), in 0.2 to 0.3 GB.
  The functions are ordinary inline functions, and GCC 13 calls them (an object of 88 KB for 1 000
  calls, about what the unit without Kairn makes) where Clang 18 inlines them (461 to 652 KB).
  Nothing here approaches the comparisons of enclosures of
  [question 12](#12-compile-time-of-the-enclosure-interface) (8 to 62 s for 1 000 calls). The
  unit of 1 000 calls without Kairn took 3.5 s with GCC 13, longer than with it; not investigated.

### What the machine code shows (third part)

The loops of the new timed functions were summarized by `bench/asm_summary.py` as in the earlier
parts (`asm3-*.json` beside the runs), and the functions named below were read in full. What explains
the tables:

1. **GCC 13 calls the generated loops of the functions on arrays; Clang 18 inlines them.** The
   public function of GCC 13 is a call of `kairn::gen::sum_1_entry_packed` and its kin after the
   check; Clang 18 inlines the loop. Neither changes the time over arrays of 512 elements and more
   (the public function over its loop: 1.00 to 1.05).
2. **GCC 13 at `-O2` does not vectorize the plain loops of `T`** (`x + y`, `x a`, `a x + y`, and the
   double-word maps written out: scalar code), which Kairn's packed loops beat by 1.5 to 3.4 times;
   at `-O3`, and with Clang 18 at both levels, they are 256-bit loops. Clang 18 also vectorizes the
   sequential loop of a map (`kseq`, on 256-bit registers), which is why one lane costs it what the
   default order costs.
3. **GCC 13 at `-O3` removes the lane order's combination of zero states on short arrays**: when no
   packed step ran, the four lane states are the zero state, and their three two-limb additions fold
   away: 8.1 ns for a sum of two limbs of one element against 30 to 32 in the other configurations.
4. **The check at entry is read once in every call** of the loops of question 14, inside the loop of
   the calls, in every configuration: `vstmxcsr`, a load, three tests and branches to the reports,
   whose strings and call of `detail::fail` are laid out inline (with GCC 13 at `-O3`, sometimes
   `fail`'s own call of `fprintf` too). In the cold variant the hot path is `vstmxcsr`, one
   `testl $0xe040` and one branch to `.text.unlikely`. What the check changes beyond the read is what
   the compilers inline and where the code falls ([question 14](#14-short-arrays-and-the-check-at-entry)).
5. **GCC 13 at `-O2` keeps an array of accumulators in memory**, each addition loading and storing
   its state, and compiles the saturating count of four accumulators into 128-bit integer
   operations ([question 16](#16-the-accumulator)); at `-O3` and with Clang 18 the states stay in
   registers.

### How the third part was measured

| Machine | Configurations | Conditions |
|---|---|---|
| M3: macOS 26.6 arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2; `-O2` and `-O3`; the files of the third part as packed code (NEON: 2 lanes of `double`, 4 of `float`) | shared with another author's test campaign (8 processes at full load, and builds): a run was to start when the 1-minute load average was under 4, waiting up to four hours in all; the four hours passed without it (10 to 18 in the last of them), and the runs were made after them, from 10:25, at loads of 3.5 to 21; no affinity, the thread asks for the user-interactive class; each run made once, whatever its median spread (the median over the functions of each one's median over its minimum: 1.002 to 1.315, against 1.002 to 1.03 on Zen 2) |
| Zen 2: Linux x86-64, AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1; `-O2` and `-O3`; `-mfma`, the files of the third part `-mavx2 -mfma` (4 lanes of `double`, 8 of `float`) | a test campaign held the first socket, and builds of another author ran on the second with up to 16 jobs (load average 57 to 101 during the runs); each run pinned to the logical CPU of the second socket whose usage and its sibling's were the lowest over the 2 s before it, among those within 2% of the lowest the one in the least busy core complex; `mpstat` of the two every 5 s during the run; a run whose sibling was busy in more than 4 samples, or whose median function was more than 3% slower than in the fastest run of its configuration, set aside and repeated (six runs of the functions on arrays, made before the choice by core complex, of which one twice); the pairs and triplets of programs of question 14 run one after the other on the same CPU, and repeated whole |

- **Commits**: the functions on arrays at `9e114bb` (the harness of this part on the tree of
  `25cde04`; their six repeated runs at `be95dbb`), the short arrays and the pairs of programs of the
  check at entry at `dae16be` (which reads the lengths of the short arrays at run time and changes
  nothing else that is timed), the short ball vectors, the accumulator, the ball vectors and the
  errors at `be95dbb` (which adds the units of one operation and changes nothing else that is
  timed); recorded in every file. None changes anything under `include/`.
- **Flags**: those of the earlier parts; `m2_batch.cpp`, `m2_bv.cpp`, `m2_bvs.cpp` and
  `m2_accuracy.cpp` with the flags of packed code, so that the default order is the lane order of
  `Packed` (the speed-up over one lane is that of this order over `kairn::sequential`, whose loop is
  the loop of one lane).
- **Statistic**: as in the earlier parts, the minimum over 41 (M3) or 31 (Zen 2) samples of about 4
  ms; a sample of a loop over arrays beyond the last-level cache is one call (4 to 30 ms); ratios of
  minima within one run, and for the check at entry of the programs' runs made one after the other;
  a cell is the lowest and highest value over the three runs (or rounds of programs) of a
  configuration.
- **Checks before timing**: every timed function, 1 472 of them in each configuration, against its
  reference byte for byte, and the references and the textbook loops against exact sums
  (`m2_exact.hpp`) within their stated bounds ([Runs of the third part](#runs-of-the-third-part));
  none failed in any run.
- **Windows**: no Windows machine in this part; Milestone 2 has no Windows figures.
- **Noise**: on Zen 2 a function's spread over the three runs of a configuration is 0.1 to 2.4% at
  the median function and 0.4 to 7.3% at the 90th percentile; [Runs of the third
  part](#runs-of-the-third-part) has every run. The differences of question 14 are of two programs,
  whose code falls at other addresses: the same loop called directly in both differs by up to 2%,
  and by up to 13% with GCC 13 at `-O3`. A difference within a cell's range is not a difference.
- **Not measured in the third part**: threads (the partial accumulators are made one after another
  in one thread), `KAIRN_CHECKS` on the functions on arrays, Intel processors, AVX-512, GPUs,
  Windows and MSVC; the downstream user's own programs (their operations are); the time of the
  forced inlining of the constructors, whose machine code only was read.

## Still to come

This page measures what `main` held at commit `dee8ecd` (the first part), at `aa168ee` (the
second part, [above](#the-second-part)) and on the tree of `25cde04` (the third part,
[above](#the-third-part)): nothing on `main` on 2026-11-22 is left out. What no part measures, and
why, is in each part's list of what it did not measure: Windows and MSVC (no Windows machine in
Milestone 2), Intel processors, AVX-512 and GPUs (none available), threads (the partial
accumulators of question 16 are made in one thread), and `KAIRN_CHECKS` on `Packed`, the containers
and the functions on arrays.

(State on 2026-11-22, the third part. The paragraph first written here, at `dee8ecd`, listed all of
these as not on `main` yet; the one of 2026-11-21 listed what had reached `main` since, the
predicates and comparisons of `Interval` and `Ball`, the midpoint, radius, split and conversions of
intervals of two limbs, the hull, intersection and split of balls, and `Packed` and the containers,
which the second part measures; the one of the second part, the functions on arrays (sum, dot
product, `axpy`, convolution, norm), `BallVector` and the accumulator, which the third part
measures.)

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

### Second part

The tables of the second part are printed by `python3 bench/m2_report.py --part 2
results/milestone2/bench` from the stored files, and those of the answers are rows of them.

#### Configurations of the second part

| Configuration (second part) | CPU | Compiler | Flags | Runs per item (soa, enc, bisect, checks pairs) | Date, commit |
|---|---|---|---|---|---|
| linux-clang-inline-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror --gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13 -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |
| linux-clang-inline-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror --gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13 -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |
| linux-gcc-inline-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |
| linux-gcc-inline-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |
| mac-appleclang-inline-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |
| mac-appleclang-inline-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |
| mac-gcc16-inline-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |
| mac-gcc16-inline-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | 3, 3, 3, 3 | 2026-11-22, `cbe3bb1` |

#### Checks of the second part

| Checks of (second part) | Functions checked, failed, per run |
|---|---|
| soa linux-clang-O2 | 172, 0; 172, 0; 172, 0 |
| soa linux-clang-O3 | 172, 0; 172, 0; 172, 0 |
| soa linux-gcc-O2 | 172, 0; 172, 0; 172, 0 |
| soa linux-gcc-O3 | 172, 0; 172, 0; 172, 0 |
| soa mac-appleclang-O2 | 172, 0; 172, 0; 172, 0 |
| soa mac-appleclang-O3 | 172, 0; 172, 0; 172, 0 |
| soa mac-gcc16-O2 | 172, 0; 172, 0; 172, 0 |
| soa mac-gcc16-O3 | 172, 0; 172, 0; 172, 0 |
| enc linux-clang-O2 | 446, 0; 446, 0; 446, 0 |
| enc linux-clang-O3 | 446, 0; 446, 0; 446, 0 |
| enc linux-gcc-O2 | 446, 0; 446, 0; 446, 0 |
| enc linux-gcc-O3 | 446, 0; 446, 0; 446, 0 |
| enc mac-appleclang-O2 | 446, 0; 446, 0; 446, 0 |
| enc mac-appleclang-O3 | 446, 0; 446, 0; 446, 0 |
| enc mac-gcc16-O2 | 446, 0; 446, 0; 446, 0 |
| enc mac-gcc16-O3 | 446, 0; 446, 0; 446, 0 |
| bisect linux-clang-O2 | 11, 0; 11, 0; 11, 0 |
| bisect linux-clang-O3 | 11, 0; 11, 0; 11, 0 |
| bisect linux-gcc-O2 | 11, 0; 11, 0; 11, 0 |
| bisect linux-gcc-O3 | 11, 0; 11, 0; 11, 0 |
| bisect mac-appleclang-O2 | 11, 0; 11, 0; 11, 0 |
| bisect mac-appleclang-O3 | 11, 0; 11, 0; 11, 0 |
| bisect mac-gcc16-O2 | 11, 0; 11, 0; 11, 0 |
| bisect mac-gcc16-O3 | 11, 0; 11, 0; 11, 0 |
| checks linux-clang-O2 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |
| checks linux-clang-O3 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |
| checks linux-gcc-O2 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |
| checks linux-gcc-O3 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |
| checks mac-appleclang-O2 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |
| checks mac-appleclang-O3 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |
| checks mac-gcc16-O2 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |
| checks mac-gcc16-O3 | 265, 0; 265, 0; 265, 0; 265, 0; 265, 0; 265, 0 |

#### Runs of the second part

| Run (second part) | Over the fastest run: median, 90th percentile | Median over minimum within the run (median function) | Load average (1 min) at start, end |
|---|---|---|---|
| `soa-linux-clang-O2-r1.json` | 1.000, 1.035 | 1.005 | 3.2, 2.8 |
| `soa-linux-clang-O2-r2.json` | 1.010, 1.020 | 1.010 | 19.4, 20.9 |
| `soa-linux-clang-O2-r3.json` | 1.002, 1.042 | 1.006 | 7.3, 5.3 |
| `soa-linux-clang-O3-r1.json` | 1.001, 1.029 | 1.005 | 2.7, 3.3 |
| `soa-linux-clang-O3-r2.json` | 1.010, 1.016 | 1.010 | 21.7, 21.6 |
| `soa-linux-clang-O3-r3.json` | 1.000, 1.024 | 1.005 | 16.8, 9.3 |
| `soa-linux-gcc-O2-r1.json` | 1.000, 1.001 | 1.005 | 9.8, 5.5 |
| `soa-linux-gcc-O2-r2.json` | 1.002, 1.017 | 1.011 | 8.9, 12.6 |
| `soa-linux-gcc-O2-r3.json` | 1.009, 1.016 | 1.008 | 21.8, 19.9 |
| `soa-linux-gcc-O3-r1.json` | 1.001, 1.012 | 1.004 | 3.2, 2.7 |
| `soa-linux-gcc-O3-r2.json` | 1.001, 1.012 | 1.006 | 6.7, 10.7 |
| `soa-linux-gcc-O3-r3.json` | 1.002, 1.016 | 1.005 | 21.3, 19.2 |
| `soa-mac-appleclang-O2-r1.json` | 1.005, 1.066 | 1.027 | 9.2, 6.3 |
| `soa-mac-appleclang-O2-r2.json` | 1.000, 1.013 | 1.005 | 3.3, 2.0 |
| `soa-mac-appleclang-O2-r3.json` | 1.000, 1.006 | 1.005 | 1.7, 1.5 |
| `soa-mac-appleclang-O3-r1.json` | 1.006, 1.072 | 1.022 | 6.2, 4.9 |
| `soa-mac-appleclang-O3-r2.json` | 1.000, 1.027 | 1.006 | 1.5, 2.2 |
| `soa-mac-appleclang-O3-r3.json` | 1.000, 1.005 | 1.006 | 1.9, 1.6 |
| `soa-mac-gcc16-O2-r1.json` | 1.004, 1.060 | 1.021 | 3.9, 3.8 |
| `soa-mac-gcc16-O2-r2.json` | 1.000, 1.010 | 1.006 | 1.5, 1.5 |
| `soa-mac-gcc16-O2-r3.json` | 1.000, 1.010 | 1.006 | 2.1, 2.0 |
| `soa-mac-gcc16-O3-r1.json` | 1.001, 1.060 | 1.006 | 2.7, 3.6 |
| `soa-mac-gcc16-O3-r2.json` | 1.000, 1.012 | 1.004 | 1.9, 1.5 |
| `soa-mac-gcc16-O3-r3.json` | 1.001, 1.011 | 1.005 | 1.7, 1.5 |
| `enc-linux-clang-O2-r1.json` | 1.000, 1.001 | 1.003 | 2.7, 3.2 |
| `enc-linux-clang-O2-r2.json` | 1.013, 1.019 | 1.009 | 20.9, 21.4 |
| `enc-linux-clang-O2-r3.json` | 1.000, 1.004 | 1.013 | 5.1, 11.6 |
| `enc-linux-clang-O3-r1.json` | 1.001, 1.003 | 1.004 | 3.3, 3.3 |
| `enc-linux-clang-O3-r2.json` | 1.010, 1.015 | 1.010 | 21.4, 21.6 |
| `enc-linux-clang-O3-r3.json` | 1.000, 1.002 | 1.004 | 9.3, 8.8 |
| `enc-linux-gcc-O2-r1.json` | 1.000, 1.000 | 1.003 | 5.3, 4.0 |
| `enc-linux-gcc-O2-r2.json` | 1.004, 1.011 | 1.011 | 12.9, 16.3 |
| `enc-linux-gcc-O2-r3.json` | 1.010, 1.016 | 1.010 | 19.9, 20.6 |
| `enc-linux-gcc-O3-r1.json` | 1.000, 1.002 | 1.003 | 2.6, 2.7 |
| `enc-linux-gcc-O3-r2.json` | 1.001, 1.006 | 1.012 | 10.7, 14.1 |
| `enc-linux-gcc-O3-r3.json` | 1.001, 1.006 | 1.016 | 19.2, 18.6 |
| `enc-mac-appleclang-O2-r1.json` | 1.001, 1.073 | 1.024 | 7.2, 6.6 |
| `enc-mac-appleclang-O2-r2.json` | 1.000, 1.018 | 1.002 | 2.0, 1.8 |
| `enc-mac-appleclang-O2-r3.json` | 1.000, 1.001 | 1.002 | 1.5, 1.6 |
| `enc-mac-appleclang-O3-r1.json` | 1.000, 1.071 | 1.020 | 4.9, 7.4 |
| `enc-mac-appleclang-O3-r2.json` | 1.000, 1.007 | 1.002 | 2.2, 1.8 |
| `enc-mac-appleclang-O3-r3.json` | 1.000, 1.004 | 1.002 | 1.6, 1.6 |
| `enc-mac-gcc16-O2-r1.json` | 1.000, 1.030 | 1.003 | 3.8, 3.2 |
| `enc-mac-gcc16-O2-r2.json` | 1.000, 1.015 | 1.003 | 1.5, 1.5 |
| `enc-mac-gcc16-O2-r3.json` | 1.000, 1.011 | 1.003 | 2.0, 1.4 |
| `enc-mac-gcc16-O3-r1.json` | 1.000, 1.035 | 1.003 | 3.6, 2.5 |
| `enc-mac-gcc16-O3-r2.json` | 1.000, 1.005 | 1.002 | 1.5, 2.2 |
| `enc-mac-gcc16-O3-r3.json` | 1.000, 1.012 | 1.003 | 1.5, 3.9 |
| `bisect-linux-clang-O2-r1.json` | 1.000, 1.026 | 1.003 | 3.2, 3.1 |
| `bisect-linux-clang-O2-r2.json` | 1.014, 1.028 | 1.009 | 21.4, 21.4 |
| `bisect-linux-clang-O2-r3.json` | 1.010, 1.011 | 1.004 | 11.6, 12.1 |
| `bisect-linux-clang-O3-r1.json` | 1.001, 1.002 | 1.004 | 3.3, 3.3 |
| `bisect-linux-clang-O3-r2.json` | 1.018, 1.027 | 1.005 | 21.6, 21.7 |
| `bisect-linux-clang-O3-r3.json` | 1.000, 1.002 | 1.003 | 8.2, 8.2 |
| `bisect-linux-gcc-O2-r1.json` | 1.000, 1.004 | 1.005 | 4.1, 4.1 |
| `bisect-linux-gcc-O2-r2.json` | 1.000, 1.006 | 1.005 | 16.3, 15.2 |
| `bisect-linux-gcc-O2-r3.json` | 1.020, 1.042 | 1.009 | 20.6, 20.6 |
| `bisect-linux-gcc-O3-r1.json` | 1.000, 1.000 | 1.003 | 2.7, 2.7 |
| `bisect-linux-gcc-O3-r2.json` | 1.008, 1.011 | 1.008 | 14.8, 14.8 |
| `bisect-linux-gcc-O3-r3.json` | 1.009, 1.011 | 1.006 | 18.6, 18.6 |
| `bisect-mac-appleclang-O2-r1.json` | 1.049, 1.084 | 1.026 | 10.1, 10.1 |
| `bisect-mac-appleclang-O2-r2.json` | 1.001, 1.037 | 1.012 | 1.8, 1.8 |
| `bisect-mac-appleclang-O2-r3.json` | 1.000, 1.002 | 1.019 | 1.6, 1.8 |
| `bisect-mac-appleclang-O3-r1.json` | 1.014, 1.073 | 1.009 | 7.4, 7.0 |
| `bisect-mac-appleclang-O3-r2.json` | 1.003, 1.021 | 1.006 | 1.8, 1.8 |
| `bisect-mac-appleclang-O3-r3.json` | 1.000, 1.000 | 1.012 | 1.6, 1.6 |
| `bisect-mac-gcc16-O2-r1.json` | 1.033, 1.073 | 1.002 | 3.2, 3.2 |
| `bisect-mac-gcc16-O2-r2.json` | 1.003, 1.071 | 1.003 | 1.5, 1.5 |
| `bisect-mac-gcc16-O2-r3.json` | 1.000, 1.000 | 1.021 | 1.4, 1.4 |
| `bisect-mac-gcc16-O3-r1.json` | 1.022, 1.063 | 1.004 | 2.5, 2.5 |
| `bisect-mac-gcc16-O3-r2.json` | 1.000, 1.000 | 1.016 | 2.2, 2.1 |
| `bisect-mac-gcc16-O3-r3.json` | 1.034, 1.082 | 1.002 | 3.9, 3.8 |
| `checks-linux-clang-O2-c0-r1.json` | 1.001, 1.003 | 1.003 | 3.1, 2.9 |
| `checks-linux-clang-O2-c0-r2.json` | 1.011, 1.016 | 1.009 | 21.4, 21.7 |
| `checks-linux-clang-O2-c0-r3.json` | 1.000, 1.003 | 1.004 | 12.1, 10.1 |
| `checks-linux-clang-O2-c1-r1.json` | 1.000, 1.000 | 1.003 | 2.8, 2.8 |
| `checks-linux-clang-O2-c1-r2.json` | 1.010, 1.015 | 1.010 | 21.7, 21.6 |
| `checks-linux-clang-O2-c1-r3.json` | 1.010, 1.012 | 1.006 | 11.2, 14.8 |
| `checks-linux-clang-O3-c0-r1.json` | 1.011, 1.015 | 1.007 | 3.3, 9.8 |
| `checks-linux-clang-O3-c0-r2.json` | 1.010, 1.015 | 1.010 | 21.7, 21.8 |
| `checks-linux-clang-O3-c0-r3.json` | 1.000, 1.000 | 1.004 | 8.2, 6.6 |
| `checks-linux-clang-O3-c1-r1.json` | 1.000, 1.000 | 1.004 | 9.8, 6.5 |
| `checks-linux-clang-O3-c1-r2.json` | 1.009, 1.014 | 1.009 | 21.8, 22.0 |
| `checks-linux-clang-O3-c1-r3.json` | 1.002, 1.010 | 1.011 | 6.6, 10.7 |
| `checks-linux-gcc-O2-c0-r1.json` | 1.000, 1.003 | 1.003 | 3.9, 3.3 |
| `checks-linux-gcc-O2-c0-r2.json` | 1.000, 1.003 | 1.004 | 15.2, 10.1 |
| `checks-linux-gcc-O2-c0-r3.json` | 1.012, 1.018 | 1.011 | 20.5, 21.0 |
| `checks-linux-gcc-O2-c1-r1.json` | 1.000, 1.004 | 1.003 | 3.2, 3.3 |
| `checks-linux-gcc-O2-c1-r2.json` | 1.000, 1.004 | 1.004 | 9.5, 6.6 |
| `checks-linux-gcc-O2-c1-r3.json` | 1.010, 1.014 | 1.006 | 21.0, 21.6 |
| `checks-linux-gcc-O3-c0-r1.json` | 1.000, 1.000 | 1.003 | 2.7, 3.8 |
| `checks-linux-gcc-O3-c0-r2.json` | 1.006, 1.009 | 1.010 | 14.8, 16.4 |
| `checks-linux-gcc-O3-c0-r3.json` | 1.005, 1.008 | 1.009 | 18.5, 18.9 |
| `checks-linux-gcc-O3-c1-r1.json` | 1.000, 1.002 | 1.003 | 3.6, 3.4 |
| `checks-linux-gcc-O3-c1-r2.json` | 1.010, 1.015 | 1.009 | 16.4, 18.9 |
| `checks-linux-gcc-O3-c1-r3.json` | 1.000, 1.002 | 1.004 | 9.5, 7.8 |
| `checks-mac-appleclang-O2-c0-r1.json` | 1.020, 1.094 | 1.024 | 10.1, 6.7 |
| `checks-mac-appleclang-O2-c0-r2.json` | 1.000, 1.012 | 1.002 | 1.8, 1.6 |
| `checks-mac-appleclang-O2-c0-r3.json` | 1.000, 1.007 | 1.001 | 1.8, 2.0 |
| `checks-mac-appleclang-O2-c1-r1.json` | 1.011, 1.073 | 1.043 | 7.5, 6.2 |
| `checks-mac-appleclang-O2-c1-r2.json` | 1.000, 1.018 | 1.003 | 1.6, 1.5 |
| `checks-mac-appleclang-O2-c1-r3.json` | 1.000, 1.009 | 1.002 | 2.0, 2.0 |
| `checks-mac-appleclang-O3-c0-r1.json` | 1.000, 1.045 | 1.004 | 7.0, 4.7 |
| `checks-mac-appleclang-O3-c0-r2.json` | 1.000, 1.009 | 1.003 | 1.8, 1.5 |
| `checks-mac-appleclang-O3-c0-r3.json` | 1.000, 1.016 | 1.002 | 1.6, 1.3 |
| `checks-mac-appleclang-O3-c1-r1.json` | 1.000, 1.040 | 1.010 | 4.7, 3.9 |
| `checks-mac-appleclang-O3-c1-r2.json` | 1.000, 1.023 | 1.003 | 1.5, 1.5 |
| `checks-mac-appleclang-O3-c1-r3.json` | 1.000, 1.009 | 1.002 | 1.3, 2.2 |
| `checks-mac-gcc16-O2-c0-r1.json` | 1.000, 1.062 | 1.003 | 3.2, 2.8 |
| `checks-mac-gcc16-O2-c0-r2.json` | 1.000, 1.009 | 1.006 | 1.5, 1.7 |
| `checks-mac-gcc16-O2-c0-r3.json` | 1.001, 1.039 | 1.004 | 1.4, 1.6 |
| `checks-mac-gcc16-O2-c1-r1.json` | 1.001, 1.055 | 1.003 | 2.8, 2.5 |
| `checks-mac-gcc16-O2-c1-r2.json` | 1.000, 1.011 | 1.005 | 1.7, 2.0 |
| `checks-mac-gcc16-O2-c1-r3.json` | 1.000, 1.037 | 1.004 | 1.6, 1.7 |
| `checks-mac-gcc16-O3-c0-r1.json` | 1.000, 1.032 | 1.003 | 2.5, 2.0 |
| `checks-mac-gcc16-O3-c0-r2.json` | 1.000, 1.007 | 1.003 | 2.1, 1.7 |
| `checks-mac-gcc16-O3-c0-r3.json` | 1.001, 1.073 | 1.020 | 7.0, 4.6 |
| `checks-mac-gcc16-O3-c1-r1.json` | 1.000, 1.036 | 1.003 | 2.0, 3.3 |
| `checks-mac-gcc16-O3-c1-r2.json` | 1.000, 1.003 | 1.004 | 1.7, 1.8 |
| `checks-mac-gcc16-O3-c1-r3.json` | 1.012, 1.075 | 1.024 | 7.4, 6.8 |

| Spread of (second part) | Runs | Spread of a function over the runs: median, 90th percentile, worst | Worst function |
|---|---:|---|---|
| soa linux-clang-O2 | 3 | 1.7%, 5.8%, 12.2% | `m2vf/tp/copy/packed` |
| soa linux-clang-O3 | 3 | 1.2%, 3.6%, 11.8% | `m2v/mem/dot11/plain` |
| soa linux-gcc-O2 | 3 | 0.9%, 2.0%, 10.4% | `m2v/mem/dot11/plain` |
| soa linux-gcc-O3 | 3 | 0.4%, 2.3%, 10.1% | `m2v/mem/dot11/plain` |
| soa mac-appleclang-O2 | 3 | 0.6%, 6.6%, 7.5% | `m2v/mem/dot22/op` |
| soa mac-appleclang-O3 | 3 | 0.7%, 7.2%, 12.2% | `m2vf/mem/copy/view` |
| soa mac-gcc16-O2 | 3 | 0.5%, 6.5%, 10.1% | `m2vf/mem/dot11/plain` |
| soa mac-gcc16-O3 | 3 | 0.4%, 6.0%, 10.5% | `m2vf/mem/copy/op` |
| enc linux-clang-O2 | 3 | 1.3%, 1.9%, 27.9% | `m2e/tp/b1_intersection/kairn` |
| enc linux-clang-O3 | 3 | 1.0%, 1.6%, 15.8% | `m2ef/step/b2_split/op` |
| enc linux-gcc-O2 | 3 | 1.1%, 1.7%, 18.6% | `m2e/tp/i1_zero/plain` |
| enc linux-gcc-O3 | 3 | 0.2%, 1.0%, 8.9% | `m2e/tp/i2_neg/op` |
| enc mac-appleclang-O2 | 3 | 0.1%, 7.3%, 7.6% | `m2e/step/i2_intersection/kairn` |
| enc mac-appleclang-O3 | 3 | 0.0%, 7.1%, 7.4% | `m2ef/step/i1_intersection/op` |
| enc mac-gcc16-O2 | 3 | 0.1%, 3.9%, 8.9% | `m2e/tp/i1_split/kairn` |
| enc mac-gcc16-O3 | 3 | 0.1%, 4.2%, 11.2% | `m2e/tp/b1_hull/op` |
| bisect linux-clang-O2 | 3 | 1.4%, 2.8%, 4.0% | `m2r/run/self_test_kernels/op` |
| bisect linux-clang-O3 | 3 | 1.8%, 2.7%, 2.9% | `m2r/run/self_test_kernels/op` |
| bisect linux-gcc-O2 | 3 | 2.0%, 4.7%, 4.7% | `m2r/run/self_test/op` |
| bisect linux-gcc-O3 | 3 | 1.0%, 1.1%, 3.7% | `m2r/run/self_test_kernels/op` |
| bisect mac-appleclang-O2 | 3 | 4.9%, 8.4%, 9.4% | `m2r/run/bisect_i2_w0/op` |
| bisect mac-appleclang-O3 | 3 | 2.1%, 7.3%, 7.5% | `m2r/run/bisect_b2_w0/op` |
| bisect mac-gcc16-O2 | 3 | 3.3%, 7.3%, 7.4% | `m2r/run/bisect_b2_w0/op` |
| bisect mac-gcc16-O3 | 3 | 3.4%, 8.2%, 9.3% | `m2r/run/bisect_b2_w0/op` |
| checks linux-clang-O2 checks 0 | 3 | 1.1%, 1.7%, 5.5% | `m2e/step/b2_intersection/op` |
| checks linux-clang-O2 checks 1 | 3 | 1.0%, 1.6%, 16.7% | `m2e/tp/b1_neg/op` |
| checks linux-clang-O3 checks 0 | 3 | 1.2%, 1.7%, 5.2% | `m2e/tp/i1_whole/plain` |
| checks linux-clang-O3 checks 1 | 3 | 0.9%, 1.7%, 69.5% | `m2e/tp/b1_split/op` |
| checks linux-gcc-O2 checks 0 | 3 | 1.2%, 1.8%, 23.1% | `m2e/tp/i1_zero/plain` |
| checks linux-gcc-O2 checks 1 | 3 | 1.0%, 1.7%, 16.9% | `m2e/tp/b2_zero/op` |
| checks linux-gcc-O3 checks 0 | 3 | 0.7%, 1.0%, 19.1% | `m2e/tp/i2_neg/op` |
| checks linux-gcc-O3 checks 1 | 3 | 1.0%, 1.5%, 7.1% | `m2e/tp/i2_whole/op` |
| checks mac-appleclang-O2 checks 0 | 3 | 2.0%, 9.4%, 9.9% | `m2e/step/i1_intersection/op` |
| checks mac-appleclang-O2 checks 1 | 3 | 1.1%, 7.3%, 7.6% | `m2/prod/interval_mul_1/fenv_loop` |
| checks mac-appleclang-O3 checks 0 | 3 | 0.1%, 4.6%, 7.3% | `m2e/tp/b1_equal/kairn` |
| checks mac-appleclang-O3 checks 1 | 3 | 0.1%, 4.5%, 8.2% | `m2e/tp/i1_rel_equal/plain` |
| checks mac-gcc16-O2 checks 0 | 3 | 0.4%, 6.2%, 12.3% | `m2/tp/interval_sub_1/csr` |
| checks mac-gcc16-O2 checks 1 | 3 | 0.3%, 5.9%, 11.8% | `m2e/tp/i2_whole/op` |
| checks mac-gcc16-O3 checks 0 | 3 | 0.3%, 7.3%, 10.3% | `m2/tp/interval_sub_1/csr` |
| checks mac-gcc16-O3 checks 1 | 3 | 1.3%, 7.5%, 9.7% | `m2/sum/interval_add_1/csr` |

#### Question 8: `Packed` and the containers

| Packed over the scalar loop | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `x + y`, double, L1 | 0.71 to 0.72 | 0.59 to 0.61 | 0.25 | 1.00 to 1.01 |
| `x * y`, double, L1 | 0.89 | 0.70 to 0.71 | 0.32 | 1.00 to 1.01 |
| `x * a`, double, L1 | 1.07 to 1.08 | 0.81 | 0.37 | 1.00 |
| dot, W sums, over the same in scalar code, double, L1 | 1.12 to 1.16 | 0.74 to 0.75 (-O2), 1.13 to 1.20 (-O3) | 0.31 | 0.68 (-O2), 0.31 (-O3) |
| dot, W sums, over one sum in scalar code, double, L1 | 0.59 to 0.63 | 0.57 to 0.61 | 0.30 | 0.28 |
| `x + a * b`, two passes, double, L1 | 0.88 | 0.87 (-O2), 0.75 to 0.78 (-O3) | 0.38 (-O2), 0.31 (-O3) | 1.09 |
| `x + E2(a) * b`, double, L1 | 0.82 to 0.83 | 0.73 to 0.75 (-O2), 0.67 to 0.68 (-O3) | 0.28 to 0.31 | 1.00 |
| `x + E2(a) * b` packed, one pass, over `x + a * b` scalar, double, L1 | 1.98 | 1.70 to 1.75 (-O2), 1.57 to 1.62 (-O3) | 0.92 (-O2), 0.81 (-O3) | 2.87 |
| copy, double, L1 | 0.99 to 1.00 | 0.60 (-O2), 1.10 (-O3) | 0.28 (-O2), 1.00 to 1.01 (-O3) | 1.00 to 1.01 |
| `x + y`, double, memory | 0.70 | 0.59 | 0.36 to 0.37 | 1.00 to 1.01 |
| `x * y`, double, memory | 0.85 to 0.86 | 0.67 to 0.68 | 0.61 to 0.62 | 1.00 |
| `x * a`, double, memory | 1.03 to 1.04 | 0.78 to 0.79 | 0.69 to 0.71 | 0.98 to 0.99 |
| dot, W sums, over the same in scalar code, double, memory | 1.11 to 1.16 (-O2), 1.10 to 1.17 (-O3) | 0.74 to 0.75 (-O2), 1.09 to 1.14 (-O3) | 0.31 to 0.33 | 0.70 (-O2), 0.32 to 0.33 (-O3) |
| dot, W sums, over one sum in scalar code, double, memory | 0.61 to 0.65 | 0.60 to 0.61 | 0.30 to 0.31 | 0.29 |
| `x + a * b`, two passes, double, memory | 0.90 | 0.78 to 0.79 (-O2), 0.74 to 0.75 (-O3) | 0.72 to 0.75 (-O2), 0.74 to 0.77 (-O3) | 1.34 to 1.42 (-O2), 1.35 to 1.39 (-O3) |
| `x + E2(a) * b`, double, memory | 0.81 to 0.82 | 0.74 (-O2), 0.66 (-O3) | 0.37 (-O2), 0.30 to 0.32 (-O3) | 0.98 to 1.00 |
| `x + E2(a) * b` packed, one pass, over `x + a * b` scalar, double, memory | 1.82 to 1.84 | 1.62 to 1.64 (-O2), 1.45 to 1.46 (-O3) | 0.97 (-O2), 0.82 to 0.83 (-O3) | 1.38 to 1.45 (-O2), 1.37 to 1.48 (-O3) |
| copy, double, memory | 0.95 to 1.00 (-O2), 0.98 to 1.00 (-O3) | 0.20 to 0.21 (-O2), 0.97 to 1.00 (-O3) | 1.05 to 1.07 (-O2), 1.00 (-O3) | 1.00 to 1.01 |
| `x + y`, float, L1 | 0.36 | 0.29 to 0.30 | 0.12 to 0.13 | 1.00 |
| `x * y`, float, L1 | 0.44 to 0.45 | 0.33 to 0.34 | 0.16 to 0.17 | 1.00 to 1.01 |
| `x * a`, float, L1 | 0.53 to 0.54 | 0.37 to 0.38 | 0.18 | 0.99 to 1.01 |
| dot, W sums, over the same in scalar code, float, L1 | 0.72 (-O2), 0.88 to 0.90 (-O3) | 0.68 to 0.71 | 0.17 | 0.16 |
| dot, W sums, over one sum in scalar code, float, L1 | 0.31 to 0.33 | 0.30 to 0.32 | 0.16 | 0.12 |
| `x + a * b`, two passes, float, L1 | 0.45 | 0.54 to 0.55 (-O2), 0.36 (-O3) | 0.33 (-O2), 0.16 (-O3) | 1.08 to 1.10 |
| `x + E2(a) * b`, float, L1 | 0.43 | 0.33 to 0.37 | 0.13 to 0.16 | 1.01 to 1.02 |
| `x + E2(a) * b` packed, one pass, over `x + a * b` scalar, float, L1 | 1.01 to 1.03 | 0.78 to 0.81 (-O2), 0.75 to 0.76 (-O3) | 0.46 (-O2), 0.39 (-O3) | 2.89 to 2.91 |
| copy, float, L1 | 1.03 to 1.04 | 0.28 to 0.29 (-O2), 0.99 to 1.00 (-O3) | 0.13 to 0.14 (-O2), 1.05 to 1.06 (-O3) | 1.02 to 1.04 |
| `x + y`, float, memory | 0.36 | 0.29 to 0.30 | 0.19 | 1.00 |
| `x * y`, float, memory | 0.45 | 0.34 | 0.34 to 0.35 | 1.00 to 1.05 |
| `x * a`, float, memory | 0.52 to 0.53 | 0.37 | 0.39 to 0.40 | 0.99 |
| dot, W sums, over the same in scalar code, float, memory | 0.68 to 0.73 (-O2), 0.86 to 0.90 (-O3) | 0.67 to 0.71 (-O2), 0.68 to 0.72 (-O3) | 0.16 | 0.15 to 0.16 |
| dot, W sums, over one sum in scalar code, float, memory | 0.31 to 0.33 | 0.30 to 0.32 | 0.15 to 0.16 | 0.12 |
| `x + a * b`, two passes, float, memory | 0.48 | 0.51 (-O2), 0.37 to 0.38 (-O3) | 0.41 to 0.46 | 1.33 to 1.41 (-O2), 1.34 to 1.40 (-O3) |
| `x + E2(a) * b`, float, memory | 0.41 to 0.42 | 0.32 to 0.36 | 0.15 to 0.19 | 0.98 to 1.00 |
| `x + E2(a) * b` packed, one pass, over `x + a * b` scalar, float, memory | 0.96 to 0.98 | 0.80 (-O2), 0.73 to 0.74 (-O3) | 0.53 (-O2), 0.44 to 0.45 (-O3) | 1.40 to 1.45 (-O2), 1.38 to 1.46 (-O3) |
| copy, float, memory | 0.96 to 1.00 | 0.42 to 0.44 (-O2), 0.98 to 1.00 (-O3) | 0.88 to 0.89 (-O2), 1.00 to 1.01 (-O3) | 0.99 to 1.01 |

| Packed of one lane over the scalar loop | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `x + y`, double, L1 | 1.00 to 1.01 | 1.00 to 1.01 | 1.00 | 1.01 |
| `x * y`, double, L1 | 1.00 | 1.00 | 1.00 | 1.01 |
| `x * a`, double, L1 | 1.00 | 1.00 | 1.00 | 1.00 to 1.01 |
| dot, double, L1 | 1.00 to 1.02 | 0.99 to 1.02 | 1.00 | 1.00 to 1.01 |
| `x + y`, double, memory | 1.00 | 0.99 to 1.00 | 1.00 | 0.99 to 1.00 |
| `x * y`, double, memory | 0.99 to 1.00 | 0.99 to 1.01 | 0.99 to 1.01 | 1.00 |
| `x * a`, double, memory | 0.98 to 0.99 | 1.00 to 1.01 | 1.00 to 1.03 | 0.99 to 1.00 |
| dot, double, memory | 1.00 to 1.01 | 0.99 to 1.02 | 1.00 to 1.01 | 1.01 |
| `x + y`, float, L1 | 1.00 (-O2), 0.94 to 1.00 (-O3) | 0.96 to 1.02 (-O2), 0.99 to 1.00 (-O3) | 1.00 | 0.99 to 1.01 |
| `x * y`, float, L1 | 0.99 to 1.00 | 0.96 to 1.00 | 1.00 to 1.01 | 1.00 |
| `x * a`, float, L1 | 1.00 | 1.00 | 1.00 | 1.00 to 1.01 |
| dot, float, L1 | 1.00 to 1.04 (-O2), 1.00 to 1.06 (-O3) | 1.03 to 1.07 (-O2), 1.00 to 1.05 (-O3) | 1.00 | 1.01 |
| `x + y`, float, memory | 0.98 to 1.01 | 1.00 to 1.02 | 1.00 | 0.98 to 1.00 |
| `x * y`, float, memory | 0.99 to 1.00 | 1.00 to 1.02 | 1.00 to 1.01 | 1.00 to 1.01 |
| `x * a`, float, memory | 0.99 to 1.00 | 1.00 | 1.01 to 1.02 | 0.99 to 1.01 |
| dot, float, memory | 1.00 to 1.01 | 0.99 to 1.03 | 1.00 | 1.00 |

| The interfaces over the kernel on the limbs, L1 | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `x + y`, raw pointers, double | 1.17 (-O2), 1.17 to 1.26 (-O3) | 1.16 to 1.17 | 1.21 to 1.22 | 1.18 |
| `x + y`, view and proxy, double | 1.18 (-O2), 1.18 to 1.27 (-O3) | 1.17 | 1.21 to 1.22 | 1.18 |
| `x + y`, array of Expansion, double | 1.02 (-O2), 1.02 to 1.10 (-O3) | 0.98 to 0.99 | 1.00 | 3.81 to 3.83 |
| `x * y`, raw pointers, double | 1.32 to 1.34 | 1.32 | 1.27 | 1.22 to 1.23 |
| `x * y`, view and proxy, double | 1.32 to 1.34 | 1.32 | 1.27 | 1.22 to 1.23 |
| `x * y`, array of Expansion, double | 1.01 to 1.06 | 1.00 | 1.00 | 3.01 to 3.05 |
| `x * a`, raw pointers, double | 1.12 to 1.13 | 1.13 | 1.08 to 1.09 | 1.12 to 1.13 |
| `x * a`, view and proxy, double | 1.10 | 1.13 | 1.08 | 1.12 to 1.13 |
| copy, raw pointers, double | 1.00 to 1.01 | 1.03 to 1.06 (-O2), 0.99 to 1.00 (-O3) | 1.00 | 1.00 |
| copy, view and proxy, double | 1.00 to 1.01 | 1.04 to 1.06 (-O2), 0.99 to 1.00 (-O3) | 1.00 to 1.01 | 1.00 |
| copy, packed, double | 1.00 | 0.62 to 0.63 (-O2), 1.09 to 1.10 (-O3) | 0.28 (-O2), 1.00 to 1.01 (-O3) | 1.00 to 1.01 |
| `x + y`, raw pointers, float | 1.17 to 1.19 | 1.15 to 1.17 | 1.21 to 1.22 | 1.18 to 1.20 |
| `x + y`, view and proxy, float | 1.18 to 1.19 | 1.15 to 1.18 | 1.21 to 1.22 | 1.18 to 1.20 |
| `x + y`, array of Expansion, float | 1.02 to 1.04 | 0.98 to 1.01 | 1.00 | 7.64 to 7.74 |
| `x * y`, raw pointers, float | 1.34 | 1.30 | 1.32 to 1.33 | 1.22 to 1.23 |
| `x * y`, view and proxy, float | 1.34 | 1.30 | 1.32 to 1.33 | 1.22 to 1.23 |
| `x * y`, array of Expansion, float | 1.06 to 1.07 | 0.99 to 1.00 | 0.99 to 1.00 | 7.28 to 7.47 |
| `x * a`, raw pointers, float | 1.12 to 1.13 | 1.21 to 1.24 | 1.16 | 1.12 |
| `x * a`, view and proxy, float | 1.10 | 1.21 to 1.24 | 1.16 | 1.12 |
| copy, raw pointers, float | 0.97 to 0.99 | 1.02 to 1.04 | 1.00 (-O2), 0.93 (-O3) | 0.98 to 1.00 |
| copy, view and proxy, float | 0.97 to 0.99 | 1.02 to 1.04 | 0.99 (-O2), 0.93 (-O3) | 0.98 to 1.00 |
| copy, packed, float | 1.00 to 1.02 | 0.29 to 0.30 (-O2), 1.01 (-O3) | 0.13 to 0.14 (-O2), 0.98 (-O3) | 1.01 to 1.04 |

| Two limbs over plain T | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `x + y` scalar over one `+` of T, double, L1 | 16.0 to 16.7 (-O2), 16.6 to 16.7 (-O3) | 6.33 to 6.39 (-O2), 11.8 (-O3) | 16.9 (-O2), 53.8 to 54.0 (-O3) | 10.9 to 11.0 |
| `x + y` packed over one `+` of T, double, L1 | 11.5 to 11.9 (-O2), 11.9 (-O3) | 3.86 to 3.88 (-O2), 7.01 to 7.13 (-O3) | 4.24 to 4.25 (-O2), 13.6 to 13.7 (-O3) | 11.0 |
| `x * y` scalar over one `*` of T, double, L1 | 8.96 to 9.37 (-O2), 9.30 to 9.31 (-O3) | 3.63 to 3.64 (-O2), 6.74 to 6.76 (-O3) | 9.07 to 9.14 (-O2), 29.2 to 29.3 (-O3) | 6.90 to 6.93 |
| `x * y` packed over one `*` of T, double, L1 | 7.94 to 8.30 (-O2), 8.23 to 8.24 (-O3) | 2.57 (-O2), 4.75 to 4.76 (-O3) | 2.87 to 2.88 (-O2), 9.23 to 9.29 (-O3) | 6.93 to 6.95 |
| dot, packed, over the dot of T, double, L1 | 8.48 to 9.05 (-O2), 8.47 to 9.09 (-O3) | 7.64 to 8.15 (-O2), 7.64 to 8.05 (-O3) | 3.49 to 3.50 (-O2), 3.59 to 3.60 (-O3) | 3.36 to 3.38 |
| `x + y` scalar over one `+` of T, double, memory | 8.27 to 8.58 (-O2), 8.32 to 8.61 (-O3) | 6.83 to 7.05 (-O2), 8.60 to 8.70 (-O3) | 4.92 to 5.10 (-O2), 5.00 to 5.12 (-O3) | 1.85 to 1.90 |
| `x + y` packed over one `+` of T, double, memory | 5.81 to 6.01 (-O2), 5.85 to 6.04 (-O3) | 4.06 to 4.19 (-O2), 5.08 to 5.13 (-O3) | 1.81 to 1.85 (-O2), 1.81 to 1.90 (-O3) | 1.85 to 1.89 |
| `x * y` scalar over one `*` of T, double, memory | 4.84 to 4.98 | 4.02 to 4.10 (-O2), 5.13 to 5.15 (-O3) | 2.88 to 2.95 (-O2), 2.90 to 2.99 (-O3) | 1.78 to 1.81 |
| `x * y` packed over one `*` of T, double, memory | 4.14 to 4.25 (-O2), 4.13 to 4.27 (-O3) | 2.75 to 2.76 (-O2), 3.47 to 3.49 (-O3) | 1.77 to 1.80 (-O2), 1.77 to 1.83 (-O3) | 1.78 to 1.82 |
| dot, packed, over the dot of T, double, memory | 6.57 to 6.98 (-O2), 6.60 to 6.68 (-O3) | 6.84 to 6.95 | 2.63 to 2.86 (-O2), 3.07 to 3.24 (-O3) | 2.81 to 3.12 (-O2), 2.77 to 3.05 (-O3) |
| `x + y` scalar over one `+` of T, float, L1 | 32.6 to 33.8 (-O2), 32.5 to 32.8 (-O3) | 6.46 to 6.71 (-O2), 23.3 to 23.4 (-O3) | 8.72 to 8.75 (-O2), 65.5 to 65.6 (-O3) | 10.4 to 10.5 |
| `x + y` packed over one `+` of T, float, L1 | 11.8 to 12.2 (-O2), 11.8 to 11.9 (-O3) | 1.95 to 1.96 (-O2), 6.76 to 6.81 (-O3) | 1.09 to 1.10 (-O2), 8.18 to 8.20 (-O3) | 10.3 to 10.4 |
| `x * y` scalar over one `*` of T, float, L1 | 18.2 to 18.6 | 3.86 to 3.88 (-O2), 13.9 (-O3) | 8.66 to 8.67 (-O2), 33.7 (-O3) | 6.44 to 6.55 |
| `x * y` packed over one `*` of T, float, L1 | 8.06 to 8.14 (-O2), 8.12 to 8.31 (-O3) | 1.29 to 1.30 (-O2), 4.61 (-O3) | 1.43 (-O2), 5.55 to 5.57 (-O3) | 6.50 to 6.59 |
| dot, packed, over the dot of T, float, L1 | 4.55 to 4.89 (-O2), 4.61 to 4.95 (-O3) | 3.82 to 4.04 (-O2), 4.66 to 4.99 (-O3) | 1.89 (-O2), 1.95 (-O3) | 1.82 to 1.87 |
| `x + y` scalar over one `+` of T, float, memory | 16.2 to 16.8 (-O2), 16.7 to 17.2 (-O3) | 6.95 to 6.96 (-O2), 17.5 to 18.0 (-O3) | 7.41 to 7.71 (-O2), 9.73 to 9.96 (-O3) | 1.86 to 1.90 (-O2), 1.85 to 1.88 (-O3) |
| `x + y` packed over one `+` of T, float, memory | 5.78 to 6.01 (-O2), 6.00 to 6.14 (-O3) | 2.04 to 2.05 (-O2), 5.12 to 5.37 (-O3) | 1.41 to 1.44 (-O2), 1.83 to 1.92 (-O3) | 1.85 to 1.89 |
| `x * y` scalar over one `*` of T, float, memory | 9.11 to 9.43 (-O2), 9.41 to 9.60 (-O3) | 4.04 to 4.12 (-O2), 10.4 to 10.9 (-O3) | 4.74 to 4.99 (-O2), 5.18 to 5.25 (-O3) | 1.79 to 1.81 |
| `x * y` packed over one `*` of T, float, memory | 4.09 to 4.25 (-O2), 4.24 to 4.34 (-O3) | 1.39 to 1.40 (-O2), 3.50 to 3.68 (-O3) | 1.68 to 1.74 (-O2), 1.79 to 1.85 (-O3) | 1.79 to 1.89 (-O2), 1.81 to 1.83 (-O3) |
| dot, packed, over the dot of T, float, memory | 3.39 to 3.59 (-O2), 3.39 to 3.49 (-O3) | 3.40 to 3.52 (-O2), 3.42 to 3.66 (-O3) | 1.57 to 1.60 (-O2), 1.69 to 1.70 (-O3) | 1.56 to 1.61 (-O2), 1.55 to 1.61 (-O3) |

| Beyond the last-level cache over L1 | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add11/plain`, double | 2.02 to 2.08 | 0.94 to 0.97 (-O2), 1.42 to 1.43 (-O3) | 3.44 to 3.56 (-O2), 11.0 to 11.2 (-O3) | 9.02 to 9.39 (-O2), 9.04 to 9.41 (-O3) |
| `copy/kairn`, double | 1.58 to 1.64 (-O2), 1.60 to 1.63 (-O3) | 4.26 to 4.47 (-O2), 1.65 to 1.74 (-O3) | 2.29 to 2.32 (-O2), 8.25 to 8.30 (-O3) | 8.99 to 9.21 |
| `add22/op`, double | 1.04 to 1.05 | 1.04 to 1.05 | 1.04 to 1.05 | 1.54 to 1.59 (-O2), 1.53 to 1.60 (-O3) |
| `add22/packed`, double | 1.02 to 1.03 | 1.02 to 1.04 | 1.49 to 1.52 (-O2), 1.48 to 1.54 (-O3) | 1.53 to 1.59 (-O2), 1.52 to 1.59 (-O3) |
| `mul22/op`, double | 1.08 to 1.09 | 1.08 to 1.10 | 1.12 to 1.14 | 2.37 to 2.44 (-O2), 2.37 to 2.43 (-O3) |
| `mul22/packed`, double | 1.04 | 1.04 | 2.17 to 2.21 (-O2), 2.15 to 2.21 (-O3) | 2.36 to 2.43 (-O2), 2.37 to 2.43 (-O3) |
| `dotw/packed`, double | 1.00 to 1.01 (-O2), 0.95 to 1.01 (-O3) | 0.95 to 1.01 (-O2), 0.95 to 1.01 (-O3) | 1.02 to 1.07 | 1.04 to 1.07 |
| `add11/plain`, float | 1.99 to 2.07 (-O2), 1.93 to 2.00 (-O3) | 0.96 to 0.98 (-O2), 1.29 to 1.36 (-O3) | 1.15 to 1.19 (-O2), 6.69 to 6.83 (-O3) | 8.56 to 8.89 (-O2), 8.59 to 8.87 (-O3) |
| `copy/kairn`, float | 1.52 to 1.58 (-O2), 1.43 to 1.50 (-O3) | 1.07 to 1.08 (-O2), 1.57 to 1.70 (-O3) | 1.29 (-O2), 8.08 to 8.13 (-O3) | 8.09 to 8.85 (-O2), 8.68 to 8.80 (-O3) |
| `add22/op`, float | 1.01 to 1.03 | 0.99 to 1.03 | 1.01 to 1.02 | 1.55 to 1.60 (-O2), 1.53 to 1.59 (-O3) |
| `add22/packed`, float | 1.01 | 1.01 to 1.03 | 1.50 to 1.54 (-O2), 1.53 to 1.57 (-O3) | 1.54 to 1.60 (-O2), 1.53 to 1.59 (-O3) |
| `mul22/op`, float | 1.02 to 1.03 | 1.00 to 1.02 | 1.04 to 1.05 | 2.39 to 2.46 (-O2), 2.40 to 2.45 (-O3) |
| `mul22/packed`, float | 1.03 to 1.05 | 1.03 to 1.04 | 2.19 to 2.23 | 2.42 to 2.49 (-O2), 2.41 to 2.47 (-O3) |
| `dotw/packed`, float | 0.95 to 1.00 (-O2), 0.96 to 1.01 (-O3) | 0.96 to 1.01 (-O2), 0.94 to 1.01 (-O3) | 0.95 to 1.00 | 0.94 to 0.99 |

| Times of Packed and the containers (ns per element) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2v/tp/add11/plain` | 0.102 to 0.106 | 0.28 (-O2), 0.151 (-O3) | 0.318 to 0.321 (-O2), 0.0996 to 0.0998 (-O3) | 0.119 to 0.121 |
| `m2v/tp/add22/op` | 1.7 to 1.71 | 1.77 to 1.79 | 5.37 to 5.41 | 1.31 to 1.33 |
| `m2v/tp/add22/packed` | 1.22 | 1.06 to 1.09 | 1.35 to 1.36 | 1.32 to 1.33 |
| `m2v/tp/mul22/op` | 0.953 to 0.954 | 1.02 | 2.91 to 2.93 | 0.825 to 0.835 |
| `m2v/tp/mul22/packed` | 0.844 to 0.845 | 0.717 to 0.72 | 0.919 to 0.928 | 0.829 to 0.84 |
| `m2v/tp/mul21/op` | 0.634 to 0.635 | 0.686 to 0.687 | 2 to 2.01 | 0.636 to 0.645 |
| `m2v/tp/mul21/packed` | 0.682 to 0.684 | 0.553 to 0.556 | 0.732 to 0.74 | 0.635 to 0.644 |
| `m2v/tp/dot22/op` | 7.62 to 7.81 | 7.74 to 7.9 | 10.3 to 10.4 | 10.2 to 10.4 |
| `m2v/tp/dotw/op` | 4.02 to 4.16 | 6.37 (-O2), 3.92 to 4.2 (-O3) | 9.9 to 9.99 | 4.22 to 4.27 (-O2), 9.29 to 9.38 (-O3) |
| `m2v/tp/dotw/packed` | 4.52 to 4.81 (-O2), 4.8 (-O3) | 4.7 to 4.75 (-O2), 4.45 to 4.75 (-O3) | 3.05 to 3.08 | 2.86 to 2.9 |
| `m2v/tp/mix/op` | 1.04 | 1.08 to 1.12 | 3.24 to 3.28 | 0.884 to 0.898 |
| `m2v/tp/mix/packed` | 0.912 | 0.969 (-O2), 0.841 (-O3) | 1.23 to 1.25 (-O2), 1 to 1.01 (-O3) | 0.962 to 0.979 |
| `m2v/tp/mixp/packed` | 2.06 | 1.89 to 1.94 (-O2), 1.75 (-O3) | 2.98 to 3 (-O2), 2.63 to 2.64 (-O3) | 2.54 to 2.58 |
| `m2v/tp/copy/kairn` | 0.176 to 0.177 | 0.289 to 0.298 (-O2), 0.167 to 0.168 (-O3) | 0.607 to 0.615 (-O2), 0.17 (-O3) | 0.156 to 0.158 |
| `m2v/mem/add11/plain` | 0.207 to 0.216 | 0.264 to 0.273 (-O2), 0.214 to 0.216 (-O3) | 1.09 to 1.14 | 1.09 to 1.12 |
| `m2v/mem/add22/op` | 1.78 | 1.86 | 5.58 to 5.62 | 2.02 to 2.09 |
| `m2v/mem/add22/packed` | 1.25 | 1.09 to 1.11 | 2.02 to 2.09 | 2.02 to 2.1 |
| `m2v/mem/mul22/op` | 1.03 to 1.04 | 1.1 to 1.12 | 3.25 to 3.31 | 1.98 to 2.01 |
| `m2v/mem/mul22/packed` | 0.88 to 0.882 | 0.747 to 0.75 | 1.99 to 2.04 | 1.98 to 2.02 |
| `m2v/mem/mul21/op` | 0.666 to 0.668 | 0.713 to 0.715 | 2.41 to 2.45 (-O2), 2.33 to 2.4 (-O3) | 1.66 to 1.71 |
| `m2v/mem/mul21/packed` | 0.686 to 0.693 | 0.554 to 0.561 | 1.66 to 1.7 | 1.63 to 1.69 |
| `m2v/mem/dot22/op` | 7.35 to 7.9 (-O2), 7.35 to 7.92 (-O3) | 7.43 to 7.97 (-O2), 7.43 to 7.93 (-O3) | 10.3 to 10.5 | 10.3 to 10.6 |
| `m2v/mem/dotw/op` | 4.05 to 4.17 | 6.06 to 6.42 (-O2), 3.98 to 4.2 (-O3) | 9.96 to 10.1 | 4.31 to 4.43 (-O2), 9.35 to 9.44 (-O3) |
| `m2v/mem/dotw/packed` | 4.52 to 4.84 (-O2), 4.56 to 4.85 (-O3) | 4.47 to 4.8 (-O2), 4.48 to 4.8 (-O3) | 3.12 to 3.26 | 2.98 to 3.11 |
| `m2v/mem/mix/op` | 1.15 to 1.16 | 1.22 to 1.23 | 3.71 to 3.78 (-O2), 3.58 to 3.75 (-O3) | 1.98 to 2.13 (-O2), 2.03 to 2.12 (-O3) |
| `m2v/mem/mix/packed` | 1.03 | 0.962 to 0.965 (-O2), 0.903 to 0.911 (-O3) | 2.7 to 2.78 | 2.77 to 2.86 |
| `m2v/mem/mixp/packed` | 2.1 to 2.12 | 1.99 to 2 (-O2), 1.78 (-O3) | 3.59 to 3.65 (-O2), 2.95 to 3.09 (-O3) | 2.76 to 3 (-O2), 2.78 to 3.03 (-O3) |
| `m2v/mem/copy/kairn` | 0.279 to 0.289 | 1.26 to 1.33 (-O2), 0.278 to 0.29 (-O3) | 1.4 to 1.41 | 1.42 to 1.44 |
| `m2vf/tp/add11/plain` | 0.0505 to 0.0525 | 0.276 to 0.28 (-O2), 0.0787 to 0.0788 (-O3) | 0.614 to 0.62 (-O2), 0.082 (-O3) | 0.0631 to 0.0639 |
| `m2vf/tp/add22/op` | 1.71 | 1.81 to 1.85 | 5.37 to 5.42 | 0.655 to 0.666 |
| `m2vf/tp/add22/packed` | 0.617 | 0.532 to 0.548 | 0.671 to 0.68 | 0.654 to 0.664 |
| `m2vf/tp/mul22/op` | 0.953 to 0.954 | 1.08 to 1.09 | 2.76 to 2.79 | 0.408 to 0.413 |
| `m2vf/tp/mul22/packed` | 0.422 to 0.426 | 0.361 to 0.363 | 0.456 to 0.461 | 0.41 to 0.417 |
| `m2vf/tp/mul21/op` | 0.634 to 0.636 | 0.746 | 2 to 2.02 | 0.314 to 0.319 |
| `m2vf/tp/mul21/packed` | 0.34 to 0.341 | 0.276 to 0.281 | 0.365 to 0.369 | 0.312 to 0.319 |
| `m2vf/tp/dot22/op` | 7.5 to 7.81 (-O2), 7.28 to 7.82 (-O3) | 7.4 to 7.53 (-O2), 7.48 to 7.93 (-O3) | 10.3 to 10.4 | 12.7 to 12.9 |
| `m2vf/tp/dotw/op` | 3.39 to 3.4 (-O2), 2.69 to 2.73 (-O3) | 3.34 to 3.42 | 9.99 to 10.1 | 9.78 to 10 |
| `m2vf/tp/dotw/packed` | 2.38 to 2.44 | 2.28 to 2.38 | 1.65 to 1.67 | 1.55 to 1.6 |
| `m2vf/tp/mix/op` | 1.02 to 1.04 | 1.15 to 1.17 | 3.24 to 3.27 | 0.437 to 0.443 |
| `m2vf/tp/mix/packed` | 0.464 | 0.632 to 0.633 (-O2), 0.422 to 0.423 (-O3) | 1.06 to 1.07 (-O2), 0.504 to 0.505 (-O3) | 0.471 to 0.484 |
| `m2vf/tp/mixp/packed` | 1.05 to 1.06 | 0.915 to 0.943 (-O2), 0.879 (-O3) | 1.49 to 1.5 (-O2), 1.26 to 1.27 (-O3) | 1.27 to 1.29 |
| `m2vf/tp/copy/kairn` | 0.0919 to 0.0931 | 0.295 to 0.296 (-O2), 0.0842 to 0.0843 (-O3) | 0.614 to 0.619 (-O2), 0.0872 to 0.0873 (-O3) | 0.0803 to 0.0881 (-O2), 0.0815 to 0.0821 (-O3) |
| `m2vf/mem/add11/plain` | 0.104 to 0.108 (-O2), 0.102 to 0.104 (-O3) | 0.269 to 0.27 (-O2), 0.102 to 0.107 (-O3) | 0.707 to 0.736 (-O2), 0.549 to 0.56 (-O3) | 0.545 to 0.562 |
| `m2vf/mem/add22/op` | 1.73 to 1.75 | 1.83 to 1.88 | 5.45 to 5.49 | 1.01 to 1.05 |
| `m2vf/mem/add22/packed` | 0.621 to 0.626 | 0.545 to 0.552 | 1.02 to 1.05 | 1.01 to 1.05 |
| `m2vf/mem/mul22/op` | 0.975 to 0.983 | 1.09 to 1.11 | 2.87 to 2.91 | 0.986 to 1.01 |
| `m2vf/mem/mul22/packed` | 0.44 to 0.441 | 0.373 to 0.376 | 0.999 to 1.02 | 1 to 1.04 |
| `m2vf/mem/mul21/op` | 0.636 to 0.638 | 0.748 to 0.752 | 2.11 to 2.13 | 0.829 to 0.855 |
| `m2vf/mem/mul21/packed` | 0.334 to 0.34 | 0.277 to 0.281 | 0.831 to 0.851 | 0.817 to 0.844 |
| `m2vf/mem/dot22/op` | 7.36 to 7.91 (-O2), 7.36 to 7.91 (-O3) | 7.46 to 7.77 | 10.4 to 10.5 | 12.8 to 13.1 |
| `m2vf/mem/dotw/op` | 3.33 to 3.37 (-O2), 2.65 to 2.73 (-O3) | 3.26 to 3.39 | 9.91 to 10 | 9.81 to 10 |
| `m2vf/mem/dotw/packed` | 2.31 to 2.45 (-O2), 2.32 to 2.46 (-O3) | 2.25 to 2.4 (-O2), 2.24 to 2.4 (-O3) | 1.57 to 1.64 | 1.49 to 1.55 |
| `m2vf/mem/mix/op` | 1.09 to 1.1 | 1.21 to 1.22 | 3.35 to 3.44 | 0.986 to 1.05 (-O2), 1.01 to 1.06 (-O3) |
| `m2vf/mem/mix/packed` | 0.524 to 0.526 | 0.616 to 0.622 (-O2), 0.453 to 0.456 (-O3) | 1.52 to 1.55 (-O2), 1.39 to 1.4 (-O3) | 1.38 to 1.43 |
| `m2vf/mem/mixp/packed` | 1.05 to 1.07 | 0.969 to 0.977 (-O2), 0.878 to 0.889 (-O3) | 1.79 to 1.83 (-O2), 1.47 to 1.53 (-O3) | 1.38 to 1.5 (-O2), 1.39 to 1.5 (-O3) |
| `m2vf/mem/copy/kairn` | 0.14 to 0.145 (-O2), 0.132 to 0.139 (-O3) | 0.316 to 0.319 (-O2), 0.132 to 0.143 (-O3) | 0.789 to 0.8 (-O2), 0.706 to 0.709 (-O3) | 0.71 to 0.718 |

#### Question 9: the enclosure interface

| Predicates and comparisons of `Interval<T, 1>`, ns per operation (float) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.132 | 0.125 (-O2), 0.101 (-O3) | 0.784 to 0.8 (-O2), 0.149 (-O3) | 0.373 to 0.377 |
| `is_whole()` | 0.101 | 0.113 to 0.117 | 0.198 to 0.2 | 0.649 to 0.667 |
| `certainly_positive()` | 0.291 to 0.299 | 0.19 to 0.191 (-O2), 0.122 (-O3) | 0.927 to 0.939 (-O2), 0.19 (-O3) | 1.2 to 1.21 |
| `certainly_zero()` | 0.101 | 0.113 to 0.117 | 0.198 to 0.199 | 0.647 to 0.66 |
| `contains(t)` | 0.167 | 0.167 (-O2), 0.183 (-O3) | 0.277 to 0.279 | 0.283 to 0.287 |
| `contains(Y)` | 0.141 | 0.167 | 0.285 to 0.289 | 0.776 to 0.785 |
| `less` | 0.316 | 0.832 to 0.851 | 1.88 to 1.95 | 1.88 to 1.9 |
| `less_equal` | 0.316 | 0.842 to 0.85 | 1.87 to 1.96 | 1.86 to 1.91 |
| `equal` | 0.415 to 0.416 | 0.926 to 0.938 | 3.29 to 3.39 | 2.08 to 2.12 |
| `member(t, X)` | 0.168 to 0.169 | 0.148 to 0.151 | 0.267 to 0.27 | 0.315 to 0.318 |
| `ieee1788::equal` | 0.0926 to 0.0928 | 0.167 to 0.168 | 0.286 to 0.289 | 0.477 to 0.483 |
| `ieee1788::interior` | 0.332 to 0.334 | 0.303 to 0.317 | 0.53 to 0.536 | 1.23 to 1.24 |
| `ieee1788::disjoint` | 0.234 | 0.233 to 0.234 | 0.361 to 0.364 | 1.23 to 1.24 |

| Predicates and comparisons of `Interval<T, 2>`, ns per operation (float) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.163 | 0.317 (-O2), 0.171 to 0.173 (-O3) | 0.889 to 0.899 (-O2), 0.21 (-O3) | 0.503 to 0.514 |
| `is_whole()` | 0.201 to 0.203 | 0.279 to 0.296 (-O2), 0.21 (-O3) | 1.4 to 1.41 (-O2), 0.278 to 0.279 (-O3) | 0.628 to 0.64 |
| `certainly_positive()` | 0.577 to 0.594 | 0.335 (-O2), 0.206 (-O3) | 1.31 to 1.34 (-O2), 0.247 to 0.248 (-O3) | 1.25 to 1.26 |
| `certainly_zero()` | 0.193 to 0.202 | 0.298 (-O2), 0.209 (-O3) | 1.38 to 1.39 (-O2), 0.27 to 0.273 (-O3) | 0.628 to 0.636 |
| `contains(t)` | 0.498 | 0.444 to 0.445 | 0.74 to 0.746 | 0.702 to 0.712 |
| `contains(Y)` | 0.689 to 0.701 | 0.466 to 0.488 | 1.04 to 1.05 | 2.22 to 2.27 |
| `less` | 1.1 to 1.11 | 1.01 to 1.03 | 4 to 4.04 | 2.43 to 2.46 |
| `less_equal` | 1.1 to 1.11 | 1.01 to 1.02 | 3.99 to 4.03 | 3.14 to 3.18 (-O2), 3.39 to 3.42 (-O3) |
| `equal` | 2 | 1.85 | 6.91 to 6.98 | 4.94 to 5 |
| `member(t, X)` | 0.515 | 1.08 | 3.59 to 3.64 | 0.713 to 0.723 |
| `ieee1788::equal` | 0.265 | 0.413 to 0.419 | 0.942 to 0.953 | 0.553 to 0.562 (-O2), 0.478 to 0.481 (-O3) |
| `ieee1788::interior` | 1.47 | 0.649 to 0.658 | 1.22 to 1.24 | 2.6 to 2.65 |
| `ieee1788::disjoint` | 1.07 | 0.553 to 0.558 | 1.08 to 1.09 | 2.21 to 2.25 (-O2), 2.13 to 2.15 (-O3) |

| Predicates and comparisons of `Ball<T, 1>`, ns per operation (float) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.129 to 0.132 | 0.125 (-O2), 0.0985 to 0.101 (-O3) | 0.581 to 0.586 (-O2), 0.148 (-O3) | 0.372 to 0.378 |
| `is_whole()` | 0.131 to 0.132 | 0.125 (-O2), 0.0994 to 0.101 (-O3) | 0.73 to 0.746 (-O2), 0.149 (-O3) | 0.373 to 0.377 |
| `certainly_positive()` | 0.0866 to 0.0878 (-O2), 0.0827 (-O3) | 0.0835 to 0.0848 (-O2), 0.1 (-O3) | 0.173 to 0.175 | 0.622 to 0.634 |
| `certainly_zero()` | 0.101 | 0.113 to 0.117 | 0.197 to 0.2 | 0.636 to 0.658 |
| `contains(t)` | 0.362 to 0.367 | 0.39 to 0.399 | 0.765 to 0.772 | 0.72 to 0.73 |
| `contains(Y)` | 2.02 to 2.13 (-O2), 2.02 to 2.13 (-O3) | 0.649 to 0.665 | 1.14 to 1.15 | 3.06 to 3.1 |
| `less` | 2.1 to 2.13 | 2.23 to 2.24 (-O2), 2.09 to 2.24 (-O3) | 6.6 to 6.77 | 4.07 to 4.13 |
| `less_equal` | 2.07 to 2.13 | 2.21 to 2.28 | 6.54 to 6.76 | 4.12 to 4.17 |
| `equal` | 2.4 (-O2), 2.24 to 2.4 (-O3) | 1.71 to 1.72 | 6.27 to 6.34 | 3.78 to 3.83 |
| `member(t, X)` | 0.365 to 0.367 | 0.382 | 0.742 to 0.749 | 0.741 to 0.749 |

| Predicates and comparisons of `Ball<T, 2>`, ns per operation (float) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()` | 0.101 | 0.124 to 0.125 (-O2), 0.101 (-O3) | 0.324 to 0.327 (-O2), 0.21 (-O3) | 0.505 to 0.514 |
| `is_whole()` | 0.102 | 0.124 to 0.125 (-O2), 0.102 (-O3) | 0.324 to 0.327 (-O2), 0.21 (-O3) | 0.508 to 0.517 |
| `certainly_positive()` | 0.152 | 0.161 to 0.166 | 0.439 to 0.443 | 0.941 to 0.958 |
| `certainly_zero()` | 0.148 to 0.152 | 0.163 to 0.166 | 0.441 to 0.445 | 1.33 to 1.35 |
| `contains(t)` | 1.32 | 1.17 to 1.22 | 8.47 to 8.56 (-O2), 2.7 to 2.71 (-O3) | 3.92 to 3.96 |
| `contains(Y)` | 4.46 to 4.59 | 3.69 to 3.7 (-O2), 1.51 (-O3) | 14.5 to 14.7 (-O2), 3.46 (-O3) | 14.4 to 14.6 |
| `less` | 6.49 to 6.65 | 5.03 to 5.12 | 15.7 to 15.9 | 19.4 to 19.7 |
| `less_equal` | 6.51 to 6.67 | 5 to 5.07 | 15.9 to 16.1 | 19.6 to 19.9 |
| `equal` | 5.07 to 5.11 | 3.86 to 3.87 | 13.5 to 13.9 | 12.8 to 13.1 |
| `member(t, X)` | 2.13 | 4.16 to 4.27 | 15.8 to 16 (-O2), 15 to 15.1 (-O3) | 5.59 to 5.66 |

| The questions over the same in plain T | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `is_empty()`, `Interval<T, 1>` | 0.98 | 1.89 to 1.90 (-O2), 0.98 (-O3) | 3.16 to 3.23 (-O2), 0.70 to 0.71 (-O3) | 0.96 to 0.98 |
| `is_whole()`, `Interval<T, 1>` | 0.63 to 0.65 (-O2), 0.77 (-O3) | 0.42 (-O2), 0.44 to 0.48 (-O3) | 0.57 to 0.59 | 1.13 to 1.15 |
| `certainly_positive()`, `Interval<T, 1>` | 3.49 to 3.53 | 1.05 to 1.06 (-O2), 1.31 to 1.37 (-O3) | 1.70 to 1.71 (-O2), 1.48 (-O3) | 2.38 to 2.46 (-O2), 2.39 to 2.48 (-O3) |
| `certainly_zero()`, `Interval<T, 1>` | 0.65 (-O2), 0.75 (-O3) | 0.42 to 0.44 (-O2), 0.47 to 0.51 (-O3) | 0.50 to 0.59 (-O2), 0.59 (-O3) | 0.81 (-O2), 0.99 (-O3) |
| `contains(t)`, `Interval<T, 1>` | 0.78 to 0.79 | 0.41 to 0.44 (-O2), 0.63 to 0.66 (-O3) | 0.47 (-O2), 0.84 (-O3) | 0.51 |
| `contains(Y)`, `Interval<T, 1>` | 0.72 to 0.73 (-O2), 0.67 to 0.68 (-O3) | 0.43 to 0.45 (-O2), 0.52 (-O3) | 0.63 to 0.64 (-O2), 0.74 to 0.75 (-O3) | 0.97 to 0.98 (-O2), 1.06 to 1.08 (-O3) |
| `less`, `Interval<T, 1>` | 1.99 | 1.87 to 1.91 | 0.95 to 0.96 (-O2), 1.88 to 1.89 (-O3) | 1.74 to 1.78 |
| `less_equal`, `Interval<T, 1>` | 1.99 | 1.85 to 1.88 | 1.79 to 1.80 (-O2), 1.22 to 1.26 (-O3) | 1.33 to 1.34 |
| `equal`, `Interval<T, 1>` | 1.39 | 1.45 (-O2), 1.65 to 1.66 (-O3) | 2.57 to 2.58 | 1.42 to 1.43 (-O2), 1.26 (-O3) |
| `member(t, X)`, `Interval<T, 1>` | 0.82 to 0.85 | 0.38 to 0.41 | 0.53 (-O2), 0.40 to 0.41 (-O3) | 0.37 |
| `ieee1788::equal`, `Interval<T, 1>` | 0.42 to 0.44 (-O2), 0.37 to 0.38 (-O3) | 0.51 to 0.54 | 0.59 to 0.60 (-O2), 0.79 to 0.80 (-O3) | 0.62 to 0.64 (-O2), 0.67 to 0.68 (-O3) |
| `ieee1788::interior`, `Interval<T, 1>` | 1.27 to 1.30 (-O2), 1.17 to 1.20 (-O3) | 0.80 to 0.86 (-O2), 0.94 to 0.95 (-O3) | 1.36 to 1.37 (-O2), 0.54 (-O3) | 0.96 to 1.02 (-O2), 1.17 to 1.20 (-O3) |
| `ieee1788::disjoint`, `Interval<T, 1>` | 1.20 to 1.22 (-O2), 1.10 to 1.11 (-O3) | 1.19 to 1.25 (-O2), 1.08 to 1.09 (-O3) | 0.77 to 0.78 (-O2), 0.86 (-O3) | 1.07 |
| `is_empty()`, `Ball<T, 1>` | 0.90 to 0.92 (-O2), 0.99 to 1.00 (-O3) | 0.94 to 0.95 (-O2), 1.00 (-O3) | 1.00 | 0.97 to 0.99 |
| `is_whole()`, `Ball<T, 1>` | 1.00 | 1.01 to 1.02 (-O2), 0.96 to 1.00 (-O3) | 1.10 (-O2), 1.00 (-O3) | 1.01 to 1.04 |
| `certainly_positive()`, `Ball<T, 1>` | 1.00 to 1.01 | 0.77 to 0.79 | 0.93 to 0.94 | 0.96 to 1.01 |
| `certainly_zero()`, `Ball<T, 1>` | 0.65 (-O2), 0.75 (-O3) | 0.42 (-O2), 0.47 to 0.48 (-O3) | 0.59 | 0.99 to 1.01 |
| `contains(t)`, `Ball<T, 1>` | 3.33 to 3.37 (-O2), 3.25 to 3.37 (-O3) | 3.58 to 3.85 (-O2), 3.29 to 3.45 (-O3) | 3.78 to 3.79 | 1.89 to 1.90 |
| `contains(Y)`, `Ball<T, 1>` | 6.96 to 7.40 (-O2), 6.94 to 7.40 (-O3) | 3.72 to 3.80 | 4.47 to 4.48 | 3.28 to 3.30 (-O2), 4.17 to 4.24 (-O3) |
| `less`, `Ball<T, 1>` | 4.59 to 4.72 (-O2), 4.43 to 4.59 (-O3) | 4.26 to 4.45 (-O2), 4.99 to 5.04 (-O3) | 5.81 to 5.83 (-O2), 6.00 to 6.04 (-O3) | 3.18 to 3.26 |
| `less_equal`, `Ball<T, 1>` | 4.59 | 4.32 to 4.41 | 5.36 to 5.39 (-O2), 5.67 to 5.71 (-O3) | 3.05 to 3.09 |
| `equal`, `Ball<T, 1>` | 3.43 to 3.44 (-O2), 3.21 to 3.44 (-O3) | 2.10 to 2.12 | 2.36 to 2.38 | 2.12 to 2.14 |
| `member(t, X)`, `Ball<T, 1>` | 3.29 to 3.36 | 3.88 to 4.09 (-O2), 4.06 (-O3) | 4.31 to 4.33 | 1.89 to 1.92 |

| Ball over interval, two limbs over one | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `contains(t)`, `Ball<T, 1>` over `Interval<T, 1>` | 2.06 to 2.09 (-O2), 2.01 to 2.09 (-O3) | 2.50 to 2.53 (-O2), 2.34 to 2.46 (-O3) | 3.28 to 3.29 | 1.78 to 1.79 |
| `contains(t)`, `Ball<T, 2>` over `Interval<T, 2>` | 2.95 to 2.96 | 2.71 to 2.72 (-O2), 2.48 (-O3) | 5.36 to 5.37 (-O2), 3.47 to 3.50 (-O3) | 8.57 to 8.62 |
| `contains(t)`, `Interval<T, 2>` over `Interval<T, 1>` | 2.51 | 2.70 (-O2), 2.57 (-O3) | 2.99 to 3.02 | 1.82 to 1.84 |
| `contains(t)`, `Ball<T, 2>` over `Ball<T, 1>` | 3.56 to 3.60 (-O2), 3.56 to 3.69 (-O3) | 2.90 to 2.93 (-O2), 2.60 to 2.73 (-O3) | 4.89 (-O2), 3.19 (-O3) | 8.82 to 8.84 |
| `contains(Y)`, `Ball<T, 1>` over `Interval<T, 1>` | 6.56 to 6.97 (-O2), 6.53 to 6.97 (-O3) | 3.75 (-O2), 4.09 (-O3) | 4.50 to 4.51 | 3.30 to 3.31 |
| `contains(Y)`, `Ball<T, 2>` over `Interval<T, 2>` | 4.54 to 4.55 (-O2), 4.13 to 4.28 (-O3) | 3.65 to 3.66 (-O2), 3.17 to 3.18 (-O3) | 6.82 to 6.86 (-O2), 3.31 to 3.32 (-O3) | 6.72 to 6.78 |
| `contains(Y)`, `Interval<T, 2>` over `Interval<T, 1>` | 3.25 | 2.72 (-O2), 2.97 (-O3) | 3.44 to 3.45 | 2.39 to 2.42 |
| `contains(Y)`, `Ball<T, 2>` over `Ball<T, 1>` | 2.12 to 2.25 (-O2), 1.97 to 2.05 (-O3) | 2.65 (-O2), 2.30 to 2.31 (-O3) | 5.21 to 5.24 (-O2), 2.53 to 2.54 (-O3) | 4.90 to 4.92 |
| `less`, `Ball<T, 1>` over `Interval<T, 1>` | 3.22 (-O2), 3.11 to 3.22 (-O3) | 2.52 to 2.53 (-O2), 2.92 to 2.95 (-O3) | 3.46 to 3.55 | 2.02 to 2.03 |
| `less`, `Ball<T, 2>` over `Interval<T, 2>` | 5.69 to 5.71 | 4.97 to 5.09 | 4.16 to 4.22 | 7.92 to 7.98 |
| `less`, `Interval<T, 2>` over `Interval<T, 1>` | 1.65 | 1.22 to 1.24 | 1.99 to 2.02 | 1.22 to 1.23 |
| `less`, `Ball<T, 2>` over `Ball<T, 1>` | 2.91 to 2.92 (-O2), 2.92 to 3.02 (-O3) | 2.44 (-O2), 2.11 to 2.12 (-O3) | 2.37 to 2.42 | 4.78 to 4.82 |
| `less_equal`, `Ball<T, 1>` over `Interval<T, 1>` | 3.22 | 2.56 to 2.63 | 3.26 to 3.30 | 2.05 to 2.06 |
| `less_equal`, `Ball<T, 2>` over `Interval<T, 2>` | 5.71 to 5.72 | 4.94 to 5.06 | 4.12 to 4.14 | 6.32 to 6.36 |
| `less_equal`, `Interval<T, 2>` over `Interval<T, 1>` | 1.65 | 1.22 to 1.27 | 1.99 to 2.02 | 1.54 to 1.55 |
| `less_equal`, `Ball<T, 2>` over `Ball<T, 1>` | 2.92 | 2.38 to 2.39 | 2.50 to 2.55 | 4.77 to 4.79 |
| `equal`, `Ball<T, 1>` over `Interval<T, 1>` | 2.89 (-O2), 2.70 to 2.90 (-O3) | 1.79 to 1.83 | 1.76 to 1.77 | 1.81 to 1.82 |
| `equal`, `Ball<T, 2>` over `Interval<T, 2>` | 2.84 (-O2), 2.75 to 2.94 (-O3) | 2.03 to 2.04 | 1.93 to 1.96 | 2.75 to 2.77 |
| `equal`, `Interval<T, 2>` over `Interval<T, 1>` | 2.09 (-O2), 2.01 to 2.10 (-O3) | 1.97 to 1.98 | 2.09 to 2.10 | 2.18 to 2.19 |
| `equal`, `Ball<T, 2>` over `Ball<T, 1>` | 2.06 (-O2), 2.00 to 2.18 (-O3) | 2.19 to 2.25 | 2.28 to 2.34 | 3.32 to 3.34 |
| `member(t, X)`, `Ball<T, 1>` over `Interval<T, 1>` | 1.94 to 1.98 | 2.54 to 2.64 (-O2), 2.43 to 2.54 (-O3) | 3.45 to 3.46 | 1.80 |
| `member(t, X)`, `Ball<T, 2>` over `Interval<T, 2>` | 4.64 to 4.65 | 3.78 to 3.79 (-O2), 3.89 to 3.97 (-O3) | 4.00 to 4.05 | 12.0 to 12.1 |
| `member(t, X)`, `Interval<T, 2>` over `Interval<T, 1>` | 2.46 | 3.49 to 3.54 (-O2), 3.16 to 3.37 (-O3) | 7.29 to 7.35 | 1.79 |
| `member(t, X)`, `Ball<T, 2>` over `Ball<T, 1>` | 5.75 to 5.88 | 4.99 to 5.27 (-O2), 5.16 (-O3) | 8.50 to 8.59 | 12.0 |
| `hull`, `Ball<T, 1>` over `Interval<T, 1>` | 16.6 | 12.9 to 13.5 (-O2), 13.9 to 15.5 (-O3) | 31.1 to 31.5 | 28.0 to 28.2 |
| `hull`, `Ball<T, 2>` over `Interval<T, 2>` | 33.4 to 33.8 | 32.5 to 34.8 (-O2), 31.9 to 32.1 (-O3) | 32.4 to 34.1 (-O2), 32.3 to 32.6 (-O3) | 54.5 to 54.8 |
| `hull`, `Interval<T, 2>` over `Interval<T, 1>` | 2.74 to 2.75 | 2.30 to 2.33 (-O2), 3.06 to 3.17 (-O3) | 4.02 to 4.21 (-O2), 4.05 to 4.10 (-O3) | 2.50 to 2.51 |
| `hull`, `Ball<T, 2>` over `Ball<T, 1>` | 5.52 to 5.59 | 5.88 to 5.91 (-O2), 6.39 to 7.08 (-O3) | 4.38 to 4.40 (-O2), 4.20 to 4.23 (-O3) | 4.86 to 4.88 |
| `split()`, `Ball<T, 1>` over `Interval<T, 1>` | 1.14 (-O2), 1.05 to 1.06 (-O3) | 0.62 to 0.64 (-O2), 0.74 to 0.75 (-O3) | 0.44 to 0.45 (-O2), 0.51 to 0.52 (-O3) | 0.86 to 0.87 |
| `split()`, `Ball<T, 2>` over `Interval<T, 2>` | 0.91 to 0.95 | 0.71 to 0.75 | 0.87 to 0.88 (-O2), 0.57 (-O3) | 0.85 |
| `split()`, `Interval<T, 2>` over `Interval<T, 1>` | 2.27 to 2.40 (-O2), 2.40 (-O3) | 2.64 to 2.68 | 1.49 to 1.51 (-O2), 2.73 to 2.76 (-O3) | 2.22 to 2.24 |
| `split()`, `Ball<T, 2>` over `Ball<T, 1>` | 1.89 to 1.98 (-O2), 2.09 to 2.14 (-O3) | 3.11 to 3.18 (-O2), 2.50 to 2.61 (-O3) | 2.95 to 3.02 | 2.19 to 2.20 |

| Set operations of `Interval<T, 1>`, ns | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `hull` | 0.465 | 0.518 to 0.546 (-O2), 0.401 to 0.414 (-O3) | 0.749 to 0.758 | 0.61 to 0.617 |
| `intersection` | 0.545 to 0.546 | 0.547 | 0.818 to 0.825 | 0.739 to 0.747 |
| `split()` | 3.27 | 2.51 | 10.8 to 10.9 (-O2), 8.53 to 8.58 (-O3) | 7.38 to 7.46 |
| `Ball<T, k>(X)` | 4.25 | 3.44 to 3.49 (-O2), 2.77 (-O3) | 11 to 11.1 (-O2), 8.4 to 8.42 (-O3) | 8.24 to 8.37 |
| `midpoint()` | 3.24 to 3.26 | 0.781 to 0.811 | 2.01 to 2.04 | 1.88 to 1.91 |
| `radius()` | 3.2 to 3.25 | 3.4 (-O2), 2.54 (-O3) | 8.32 to 8.72 | 6.21 to 6.3 |
| `midpoint()` and `radius()` | 6.37 to 6.64 | 3.67 to 3.68 (-O2), 3.3 to 3.31 (-O3) | 10.6 to 10.8 (-O2), 7.81 to 7.86 (-O3) | 7.89 to 8.03 |
| `mid_rad()` | 3.02 to 3.23 (-O2), 3.26 (-O3) | 3.49 (-O2), 2.63 to 2.64 (-O3) | 6.59 to 6.67 (-O2), 7.33 to 7.37 (-O3) | 6.47 to 6.54 |
| chain of `hull` | 1.36 to 1.43 | 0.49 to 0.504 (-O2), 0.472 to 0.504 (-O3) | 0.628 to 0.634 (-O2), 0.395 to 0.397 (-O3) | 0.886 to 0.903 |
| chain of `intersection` | 1.45 to 1.56 (-O2), 1.45 to 1.56 (-O3) | 0.53 to 0.556 (-O2), 0.525 to 0.556 (-O3) | 1.32 to 1.34 | 1.2 to 1.23 |
| chain of `split().left` | 7.4 to 7.94 (-O2), 7.4 to 7.94 (-O3) | 6.24 to 6.41 | 9.64 to 9.76 (-O2), 6.53 to 6.54 (-O3) | 21.2 to 21.5 |
| chain of the conversion there and back | 23.4 to 25.1 (-O2), 23.4 to 25.1 (-O3) | 14.7 (-O2), 6.83 to 6.85 (-O3) | 16.4 to 16.6 (-O2), 15.8 to 15.9 (-O3) | 22.9 to 23.2 |

| Set operations of `Interval<T, 2>`, ns | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `hull` | 1.28 | 1.19 to 1.27 (-O2), 1.27 (-O3) | 3.01 to 3.18 (-O2), 3.04 to 3.08 (-O3) | 1.52 to 1.55 |
| `intersection` | 1.74 | 1.57 to 1.58 | 4.17 to 4.22 | 1.9 to 1.92 |
| `split()` | 7.43 to 7.85 (-O2), 7.85 (-O3) | 6.62 to 6.73 | 16.2 to 16.3 (-O2), 23.4 to 23.5 (-O3) | 16.5 to 16.7 |
| `Ball<T, k>(X)` | 15.9 to 17.1 (-O2), 16 to 17.1 (-O3) | 12.9 to 13.4 (-O2), 12.1 to 13 (-O3) | 28.4 to 28.6 | 31.6 to 32.1 |
| `midpoint()` | 5.14 to 5.44 (-O2), 5.44 (-O3) | 4.79 (-O2), 2.66 (-O3) | 10.6 to 10.8 (-O2), 5.16 to 5.17 (-O3) | 9.37 to 9.58 |
| `radius()` | 13.5 to 14.5 (-O2), 13.5 to 14.5 (-O3) | 12.1 to 12.3 | 25.6 to 25.8 | 29.8 to 30.1 |
| `midpoint()` and `radius()` | 18.3 to 19.6 (-O2), 18.3 to 19.6 (-O3) | 15.8 to 16.3 (-O2), 11.5 to 12.4 (-O3) | 36.9 to 37.7 | 38.5 to 39 |
| `mid_rad()` | 13.9 to 14.9 (-O2), 13.9 to 14.9 (-O3) | 12.1 to 12.5 (-O2), 11.4 to 12.2 (-O3) | 28 to 28.3 | 30.5 to 30.8 |
| chain of `hull` | 3.66 to 3.91 (-O2), 3.66 to 3.91 (-O3) | 0.896 to 0.915 (-O2), 0.923 to 0.948 (-O3) | 2.5 to 2.55 | 3.1 to 3.15 |
| chain of `intersection` | 3.81 to 4.09 (-O2), 3.81 to 4.09 (-O3) | 1.51 (-O2), 1.44 to 1.5 (-O3) | 3.65 to 3.77 | 2.22 to 2.25 (-O2), 2.31 to 2.33 (-O3) |
| chain of `split().left` | 28.7 to 30.8 (-O2), 28.7 to 29.9 (-O3) | 21.9 to 22.1 | 20.5 to 20.7 | 29.2 to 30.1 |
| chain of the conversion there and back | 65.8 to 70.5 (-O2), 65.8 (-O3) | 59.6 (-O2), 50.5 (-O3) | 75.9 to 77.1 (-O2), 72.9 to 73 (-O3) | 71.4 to 72.5 |

| Set operations of `Ball<T, 1>`, ns | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `hull` | 7.72 to 7.73 | 7.01 to 7.04 (-O2), 5.74 to 6.38 (-O3) | 23.4 to 23.6 | 17.1 to 17.4 |
| `intersection` | 7.49 to 7.78 | 7.04 to 7.05 (-O2), 6.01 to 6.42 (-O3) | 20.2 to 20.4 | 16.7 to 17 |
| `split()` | 3.73 (-O2), 3.42 to 3.46 (-O3) | 1.56 to 1.61 (-O2), 1.87 (-O3) | 4.79 to 4.85 (-O2), 4.4 to 4.41 (-O3) | 6.38 to 6.45 |
| `Interval<T, k>(X)` | 1.61 | 1.64 | 3.57 to 3.62 | 4.53 to 4.6 |
| `midpoint()` and `radius()` | 0.2 to 0.212 (-O2), 0.199 to 0.2 (-O3) | 0.178 | 0.3 to 0.302 | 0.625 to 0.634 |
| `mid_rad()` | 0.199 to 0.2 | 0.178 | 0.3 to 0.302 | 0.631 to 0.639 |
| chain of `hull` | 20.9 to 21.5 | 20.4 to 21.5 (-O2), 16.4 to 17.2 (-O3) | 25.2 to 25.5 | 25.9 to 26.2 |
| chain of `intersection` | 20.1 to 21.6 (-O2), 20.7 to 21.9 (-O3) | 17.7 to 18.9 (-O2), 13.1 to 14.1 (-O3) | 28.4 to 28.8 (-O2), 30.4 to 30.6 (-O3) | 21.9 to 22.1 |
| chain of `split().left` | 12.3 to 13.2 (-O2), 8.21 to 8.28 (-O3) | 4.62 to 4.64 | 9.43 to 9.54 | 6.89 to 7 |
| chain of the conversion there and back | 23.4 to 25.1 (-O2), 23.4 (-O3) | 14.7 (-O2), 10.2 (-O3) | 16 to 16.2 (-O2), 11.4 (-O3) | 28.8 to 29.2 |

| Set operations of `Ball<T, 2>`, ns | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `hull` | 42.6 to 43.2 | 40.6 to 41.4 | 99 to 104 | 83.4 to 84.4 |
| `intersection` | 40.6 to 43.6 (-O2), 40.6 to 43.6 (-O3) | 39 to 42 (-O2), 38.8 to 41.4 (-O3) | 95.5 to 98.5 | 84.1 to 85.2 |
| `split()` | 7.05 to 7.39 | 4.97 to 5.05 (-O2), 4.67 to 4.88 (-O3) | 14.1 to 14.3 (-O2), 13.3 (-O3) | 14 to 14.2 |
| `Interval<T, k>(X)` | 8.7 to 8.71 | 15.2 to 15.3 (-O2), 6.68 (-O3) | 32 to 32.3 (-O2), 25.2 (-O3) | 20.1 to 20.3 |
| `midpoint()` and `radius()` | 0.256 to 0.265 | 0.284 | 0.675 to 0.682 | 0.917 to 0.934 |
| `mid_rad()` | 0.265 | 0.284 | 0.906 to 0.915 (-O2), 0.835 to 0.838 (-O3) | 0.61 to 0.633 |
| chain of `hull` | 67.8 to 71.8 (-O2), 67.5 to 71.9 (-O3) | 66 to 69.1 | 113 to 116 | 97.6 to 98.6 |
| chain of `intersection` | 66.4 to 71.3 (-O2), 66.4 to 71.2 (-O3) | 63.5 to 63.8 | 112 to 116 | 98.6 to 99.6 (-O2), 93.6 to 99.7 (-O3) |
| chain of `split().left` | 19.8 to 21.2 (-O2), 19.8 to 21.2 (-O3) | 13.6 (-O2), 11 (-O3) | 26.5 to 30.9 (-O2), 21.4 (-O3) | 24.2 to 28.4 (-O2), 28.1 to 28.4 (-O3) |
| chain of the conversion there and back | 65.8 to 70.7 (-O2), 65.8 to 66.7 (-O3) | 59.5 (-O2), 50.8 to 50.9 (-O3) | 81.4 to 82.2 (-O2), 73 to 73.1 (-O3) | 71.5 to 74.6 (-O2), 70.3 to 75.5 (-O3) |

| midpoint() and radius() against mid_rad() | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<T, 1>`: `midpoint()` over `mid_rad()` | 1.00 to 1.07 (-O2), 1.00 (-O3) | 0.22 to 0.23 (-O2), 0.31 (-O3) | 0.27 to 0.31 | 0.29 |
| `Interval<T, 1>`: `radius()` over `mid_rad()` | 1.00 to 1.08 (-O2), 0.98 (-O3) | 0.96 to 0.98 | 1.30 to 1.31 (-O2), 1.13 to 1.14 (-O3) | 0.96 |
| `Interval<T, 1>`: both over `mid_rad()` | 2.05 to 2.20 (-O2), 1.96 (-O3) | 1.05 to 1.06 (-O2), 1.25 (-O3) | 1.61 to 1.63 (-O2), 1.07 (-O3) | 1.22 to 1.23 |
| `Interval<T, 1>`: `mid_rad()` over the kernel | 0.99 to 1.01 (-O2), 1.10 (-O3) | 1.32 (-O2), 0.95 (-O3) | 0.89 (-O2), 0.99 to 1.00 (-O3) | 1.00 |
| `Interval<T, 1>`: `midpoint()` over the kernel writing the midpoint only | 1.01 (-O2), 1.10 (-O3) | 0.96 to 1.00 | 1.00 | 1.00 |
| `Interval<T, 2>`: `midpoint()` over `mid_rad()` | 0.37 to 0.39 | 0.38 to 0.40 (-O2), 0.22 to 0.23 (-O3) | 0.38 (-O2), 0.18 (-O3) | 0.31 |
| `Interval<T, 2>`: `radius()` over `mid_rad()` | 0.97 to 1.02 | 0.97 to 1.00 (-O2), 1.00 to 1.08 (-O3) | 0.91 | 0.98 |
| `Interval<T, 2>`: both over `mid_rad()` | 1.31 to 1.32 | 1.30 to 1.34 (-O2), 1.01 to 1.08 (-O3) | 1.31 to 1.33 | 1.26 to 1.27 |
| `Interval<T, 2>`: `mid_rad()` over the kernel | 0.99 to 1.00 | 0.99 to 1.03 | 0.97 | 1.01 |
| `Interval<T, 2>`: `midpoint()` over the kernel writing the midpoint only | 1.01 to 1.03 | 1.80 (-O2), 1.00 (-O3) | 2.18 to 2.19 (-O2), 1.06 (-O3) | 0.99 to 1.00 |
| `Ball<T, 1>`: both over `mid_rad()` | 1.00 to 1.06 (-O2), 1.00 (-O3) | 1.00 | 1.00 | 0.99 to 1.00 |
| `Ball<T, 2>`: both over `mid_rad()` | 0.97 to 1.00 | 1.00 | 0.75 (-O2), 0.81 (-O3) | 1.46 to 1.47 (-O2), 1.52 (-O3) |

| Set operations over the plain forms and the kernels | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `hull`, `Interval<T, 1>`, over a min and a max | 1.00 | 0.97 to 1.00 (-O2), 0.97 to 1.04 (-O3) | 0.93 to 0.94 | 1.00 |
| `intersection`, `Interval<T, 1>`, over a max, a min and a test | 1.03 | 1.00 to 1.01 | 1.01 | 0.51 to 0.52 |
| `split()`, `Interval<T, 1>`, over (l + h)/2, (h - l)/2 | 11.1 to 11.3 | 8.48 (-O2), 8.49 to 8.83 (-O3) | 32.3 to 32.8 (-O2), 25.6 to 25.8 (-O3) | 10.9 |
| `mid_rad()`, `Interval<T, 1>`, over (l + h)/2, (h - l)/2 | 10.4 to 11.0 (-O2), 11.0 to 11.1 (-O3) | 11.8 (-O2), 8.91 to 9.27 (-O3) | 19.8 (-O2), 22.0 to 22.1 (-O3) | 9.54 to 9.58 |
| `Ball<T, 1>(X)` over (l + h)/2, (h - l)/2 | 14.4 to 14.7 | 11.6 to 11.8 (-O2), 9.37 to 9.74 (-O3) | 32.7 to 33.2 (-O2), 25.2 to 25.3 (-O3) | 12.2 |
| `hull`, `Ball<T, 1>`, over the plain hull of c - r, c + r | 12.6 | 10.3 to 10.4 (-O2), 9.4 to 10.4 (-O3) | 28.9 to 29.1 | 12.3 to 12.4 |
| `intersection`, `Ball<T, 1>`, over the plain intersection | 12.2 to 12.3 (-O2), 12.7 (-O3) | 10.4 (-O2), 9.8 to 10.5 (-O3) | 24.9 to 25.0 | 12.0 to 12.1 |
| `split()`, `Ball<T, 1>`, over c -+ r/2, r/2 | 8.01 to 8.03 (-O2), 7.35 to 7.43 (-O3) | 3.46 to 3.56 (-O2), 4.13 to 4.14 (-O3) | 2.72 (-O2), 2.49 to 2.50 (-O3) | 5.24 to 5.27 |
| `Interval<T, 1>(B)` over c - r, c + r | 4.83 | 5.79 to 5.87 | 10.8 to 10.9 | 7.16 to 7.37 |
| `hull`, `Interval<T, 1>`, over the kernel | 1.00 | 0.97 to 1.00 (-O2), 0.99 to 1.02 (-O3) | 1.00 | 0.97 to 0.98 |
| chain of `hull`, `Interval<T, 1>`, over the kernel | 1.00 to 1.04 | 1.04 to 1.07 (-O2), 1.01 to 1.07 (-O3) | 1.59 to 1.60 (-O2), 0.63 (-O3) | 0.99 to 1.01 |
| `split()`, `Interval<T, 1>`, over the kernel | 1.00 | 0.97 to 1.06 (-O2), 1.00 (-O3) | 1.28 to 1.29 (-O2), 1.01 (-O3) | 1.07 |
| chain of `split()`, `Interval<T, 1>`, over the kernel | 1.66 to 1.69 | 0.99 to 1.01 | 1.48 to 1.49 (-O2), 1.00 (-O3) | 3.24 to 3.26 |
| the conversion, `Interval<T, 1>`, over the kernel | 1.49 to 1.50 | 1.30 to 1.32 (-O2), 1.00 (-O3) | 1.33 to 1.34 (-O2), 1.01 to 1.02 (-O3) | 1.88 |
| chain of the conversion, `Interval<T, 1>`, over the kernel | 1.38 to 1.41 | 2.17 (-O2), 1.00 (-O3) | 1.00 to 1.05 | 1.24 to 1.25 |
| `hull`, `Interval<T, 2>`, over the kernel | 1.00 | 0.93 to 1.00 (-O2), 1.00 (-O3) | 0.99 to 1.01 | 1.00 |
| chain of `hull`, `Interval<T, 2>`, over the kernel | 1.00 to 1.01 (-O2), 1.00 to 1.07 (-O3) | 0.98 to 1.00 (-O2), 1.04 to 1.05 (-O3) | 0.99 to 1.03 | 1.00 |
| `split()`, `Interval<T, 2>`, over the kernel | 1.01 to 1.02 (-O2), 1.01 to 1.07 (-O3) | 1.00 to 1.03 | 0.68 (-O2), 1.00 (-O3) | 1.13 to 1.14 |
| chain of `split()`, `Interval<T, 2>`, over the kernel | 1.18 to 1.23 | 1.04 | 1.00 | 1.91 to 1.95 |
| the conversion, `Interval<T, 2>`, over the kernel | 1.67 to 1.73 (-O2), 1.64 to 1.73 (-O3) | 1.01 to 1.08 (-O2), 1.00 (-O3) | 1.01 | 1.01 to 1.03 |
| chain of the conversion, `Interval<T, 2>`, over the kernel | 1.06 | 1.18 (-O2), 1.00 (-O3) | 1.03 to 1.07 | 1.06 to 1.07 |
| `hull`, `Ball<T, 1>`, over the kernel | 0.98 to 1.03 | 1.14 (-O2), 0.92 to 1.02 (-O3) | 1.12 to 1.13 | 1.70 to 1.71 |
| chain of `hull`, `Ball<T, 1>`, over the kernel | 1.19 to 1.27 (-O2), 1.21 to 1.24 (-O3) | 1.27 to 1.34 (-O2), 0.99 to 1.04 (-O3) | 0.99 to 1.00 | 1.31 to 1.32 |
| `split()`, `Ball<T, 1>`, over the kernel | 1.08 (-O2), 1.00 to 1.06 (-O3) | 1.00 to 1.01 | 1.09 (-O2), 0.96 (-O3) | 0.99 to 1.00 |
| chain of `split()`, `Ball<T, 1>`, over the kernel | 1.50 (-O2), 1.00 (-O3) | 1.00 | 1.00 | 1.00 to 1.01 |
| the conversion, `Ball<T, 1>`, over the kernel | 1.00 | 1.00 | 1.00 | 1.00 |
| chain of the conversion, `Ball<T, 1>`, over the kernel | 1.38 to 1.41 | 1.44 (-O2), 1.00 (-O3) | 1.35 (-O2), 0.96 to 0.97 (-O3) | 1.58 |
| `hull`, `Ball<T, 2>`, over the kernel | 1.01 to 1.07 (-O2), 1.00 to 1.07 (-O3) | 1.07 to 1.11 (-O2), 1.05 to 1.06 (-O3) | 1.01 to 1.05 | 2.25 to 2.26 |
| chain of `hull`, `Ball<T, 2>`, over the kernel | 1.04 to 1.06 (-O2), 1.05 to 1.12 (-O3) | 1.10 to 1.14 (-O2), 1.10 to 1.15 (-O3) | 1.12 to 1.14 | 1.09 to 1.10 |
| `split()`, `Ball<T, 2>`, over the kernel | 1.08 to 1.13 (-O2), 1.10 to 1.13 (-O3) | 1.01 to 1.03 (-O2), 0.96 to 1.00 (-O3) | 1.06 to 1.07 (-O2), 1.00 (-O3) | 1.20 |
| chain of `split()`, `Ball<T, 2>`, over the kernel | 1.35 (-O2), 1.35 to 1.45 (-O3) | 1.23 (-O2), 1.00 (-O3) | 1.25 to 1.44 (-O2), 1.01 (-O3) | 1.51 to 1.75 (-O2), 1.76 (-O3) |
| the conversion, `Ball<T, 2>`, over the kernel | 0.99 | 2.28 to 2.30 (-O2), 1.00 (-O3) | 1.27 (-O2), 1.00 (-O3) | 1.05 |
| chain of the conversion, `Ball<T, 2>`, over the kernel | 1.13 to 1.15 | 1.17 (-O2), 1.00 (-O3) | 1.24 (-O2), 1.11 (-O3) | 1.14 to 1.21 (-O2), 1.14 to 1.21 (-O3) |

| The public function over the kernel, every loop of m2e | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| -O2: median, largest | 1.00, 2.23 (`i1_midrad2`) | 1.00, 2.28 (`b2_convert`) | 1.00, 2.18 (`i2_midpoint`) | 1.00, 2.27 (`b2_intersection`) |
| -O3: median, largest | 1.00, 2.00 (`i1_midrad2`) | 1.00, 1.25 (`i1_midrad2`) | 1.00, 1.28 (`i2_midrad2`) | 1.00, 2.26 (`b2_intersection`) |

| The enclosure interface, float over double | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `less`, `Interval<T, 1>` | 0.48 | 1.04 to 1.05 | 0.97 to 0.99 | 0.94 |
| `contains_t`, `Interval<T, 1>` | 0.48 | 0.50 to 0.52 | 0.52 | 0.56 to 0.57 |
| `hull`, `Interval<T, 1>` | 0.50 | 0.48 to 0.51 | 0.70 to 0.71 | 0.49 to 0.50 |
| `split`, `Interval<T, 1>` | 0.93 to 1.00 (-O2), 1.00 (-O3) | 1.11 (-O2), 1.06 (-O3) | 1.06 to 1.08 (-O2), 0.80 to 0.81 (-O3) | 0.88 |
| `convert`, `Interval<T, 1>` | 0.96 to 1.00 | 1.01 to 1.04 | 0.99 to 1.00 (-O2), 0.85 to 0.86 (-O3) | 0.95 |
| `less`, `Interval<T, 2>` | 1.01 to 1.02 | 1.03 | 1.03 | 1.00 |
| `contains_t`, `Interval<T, 2>` | 0.57 | 0.49 | 0.46 to 0.47 | 0.76 to 0.77 |
| `hull`, `Interval<T, 2>` | 0.50 | 0.50 to 0.53 | 1.52 to 1.60 (-O2), 1.58 to 1.59 (-O3) | 1.26 to 1.27 |
| `split`, `Interval<T, 2>` | 1.03 to 1.09 (-O2), 1.03 (-O3) | 0.94 to 0.99 (-O2), 1.00 (-O3) | 1.10 to 1.11 (-O2), 0.76 (-O3) | 1.00 |
| `convert`, `Interval<T, 2>` | 1.01 to 1.05 | 0.94 to 1.02 (-O2), 1.00 (-O3) | 0.96 | 0.95 to 0.97 |
| `less`, `Ball<T, 1>` | 0.98 to 1.03 | 1.10 (-O2), 0.88 to 0.94 (-O3) | 0.96 to 1.00 | 1.01 to 1.02 |
| `contains_t`, `Ball<T, 1>` | 0.50 to 0.52 | 0.46 to 0.48 | 0.44 | 0.80 |
| `hull`, `Ball<T, 1>` | 1.00 to 1.02 | 0.97 to 1.00 (-O2), 1.02 to 1.14 (-O3) | 0.93 to 0.95 | 0.94 |
| `split`, `Ball<T, 1>` | 0.94 (-O2), 0.94 to 1.00 (-O3) | 1.00 to 1.04 (-O2), 0.86 (-O3) | 0.85 (-O2), 0.93 (-O3) | 0.76 |
| `convert`, `Ball<T, 1>` | 1.08 (-O2), 0.99 to 1.00 (-O3) | 0.50 | 0.49 to 0.50 | 0.99 to 1.00 |
| `less`, `Ball<T, 2>` | 1.04 to 1.07 | 1.01 to 1.02 | 0.96 to 0.97 | 1.00 to 1.01 |
| `contains_t`, `Ball<T, 2>` | 0.51 | 0.49 to 0.54 | 0.99 to 1.00 (-O2), 0.49 (-O3) | 0.49 to 0.50 |
| `hull`, `Ball<T, 2>` | 0.98 to 1.00 | 0.99 to 1.00 | 0.97 | 0.98 to 0.99 |
| `split`, `Ball<T, 2>` | 1.01 to 1.02 (-O2), 0.97 to 1.00 (-O3) | 1.04 to 1.05 (-O2), 0.97 to 1.02 (-O3) | 0.94 to 0.97 | 0.91 to 0.92 |
| `convert`, `Ball<T, 2>` | 0.79 to 0.84 | 0.69 to 0.71 (-O2), 1.06 (-O3) | 0.95 to 0.96 | 0.97 |

#### Question 10: the bisection

| Bisection: time to solution, microseconds | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<double, 1>`, width 1e-6 | 12.5 to 12.8 | 8.36 to 8.37 (-O2), 7.85 to 8.05 (-O3) | 15.6 to 15.9 (-O2), 14.1 to 14.2 (-O3) | 22.3 to 22.9 |
| `Interval<double, 2>`, width 1e-6 | 45.9 to 49.5 (-O2), 46 to 48.7 (-O3) | 38.6 to 41 (-O2), 37.9 to 40.6 (-O3) | 85.6 to 87.2 | 82 to 84.7 |
| `Ball<double, 1>`, width 1e-6 | 3.25 to 3.36 (-O2), 3.19 to 3.24 (-O3) | 3.72 to 3.85 (-O2), 3.9 to 3.98 (-O3) | 8.58 to 8.82 | 8.25 to 8.6 |
| `Ball<double, 2>`, width 1e-6 | 6.67 to 7 (-O2), 6.57 to 6.92 (-O3) | 7.13 to 7.61 (-O2), 6.99 to 7.56 (-O3) | 16.5 to 16.8 | 15.4 to 15.7 |
| `Interval<double, 1>`, width 0 | 32.2 to 33.2 | 22.2 to 22.3 (-O2), 20.7 to 21.3 (-O3) | 46.8 to 48 (-O2), 42.2 to 42.5 (-O3) | 58.2 to 59.8 |
| `Interval<double, 2>`, width 0 | 257 to 281 (-O2), 257 to 276 (-O3) | 219 to 235 (-O2), 218 to 229 (-O3) | 506 to 516 | 461 to 476 |
| `Ball<double, 1>`, width 0 | 9.1 to 9.37 (-O2), 8.83 to 8.88 (-O3) | 9.44 to 10.1 (-O2), 10.3 to 10.4 (-O3) | 22.2 to 22.7 | 21.5 to 21.8 (-O2), 20.7 to 21 (-O3) |
| `Ball<double, 2>`, width 0 | 35.2 to 37.9 (-O2), 35.1 to 37.8 (-O3) | 36.8 to 39.5 (-O2), 36.1 to 39.5 (-O3) | 84 to 85.5 | 78.3 to 79.8 |

| Bisection: time to solution over that of Ball<double, 1> | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<double, 1>` over `Ball<double, 1>`, width 1e-6 | 3.80 to 3.90 | 2.17 to 2.25 (-O2), 2.01 to 2.03 (-O3) | 1.81 to 1.83 (-O2), 1.61 to 1.62 (-O3) | 2.63 to 2.64 (-O2), 2.73 (-O3) |
| `Interval<double, 2>` over `Ball<double, 1>`, width 1e-6 | 14.0 to 14.7 (-O2), 14.4 to 15.0 (-O3) | 10.4 to 11.0 (-O2), 9.7 to 10.2 (-O3) | 9.81 to 9.98 | 9.66 to 9.68 (-O2), 10.1 (-O3) |
| `Ball<double, 1>` over `Ball<double, 1>`, width 1e-6 | 1.00 | 1.00 | 1.00 | 1.00 |
| `Ball<double, 2>` over `Ball<double, 1>`, width 1e-6 | 2.05 to 2.08 (-O2), 2.06 to 2.16 (-O3) | 1.91 to 1.98 (-O2), 1.79 to 1.90 (-O3) | 1.88 to 1.94 | 1.82 to 1.87 |
| `Interval<double, 2>` over `Ball<double, 2>`, width 1e-6 | 6.79 to 7.08 (-O2), 6.77 to 7.05 (-O3) | 5.40 to 5.75 (-O2), 5.36 to 5.43 (-O3) | 5.15 to 5.20 | 5.30 to 5.41 |
| `Interval<double, 1>` over `Ball<double, 1>`, width 0 | 3.54 to 3.58 (-O2), 3.63 to 3.66 (-O3) | 2.20 to 2.36 (-O2), 2.02 to 2.04 (-O3) | 2.09 to 2.13 (-O2), 1.87 to 1.88 (-O3) | 2.71 (-O2), 2.84 to 2.85 (-O3) |
| `Interval<double, 2>` over `Ball<double, 1>`, width 0 | 28.2 to 30.0 (-O2), 29.0 to 31.2 (-O3) | 23.2 to 23.3 (-O2), 21.3 to 22.0 (-O3) | 22.6 to 22.9 | 21.5 (-O2), 22.6 to 22.7 (-O3) |
| `Ball<double, 1>` over `Ball<double, 1>`, width 0 | 1.00 | 1.00 | 1.00 | 1.00 |
| `Ball<double, 2>` over `Ball<double, 1>`, width 0 | 3.87 to 4.04 (-O2), 3.96 to 4.28 (-O3) | 3.65 to 3.90 (-O2), 3.52 to 3.79 (-O3) | 3.73 to 3.80 | 3.66 to 3.67 (-O2), 3.78 to 3.79 (-O3) |
| `Interval<double, 2>` over `Ball<double, 2>`, width 0 | 7.24 to 7.43 | 5.96 to 6.38 (-O2), 5.80 to 6.04 (-O3) | 6.01 to 6.08 | 5.85 to 6.00 |

| Bisection: ns per evaluation of p | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Interval<double, 1>`, width 1e-6 | 74.6 to 76.5 | 50.1 (-O2), 47 to 48.2 (-O3) | 93.3 to 95.4 (-O2), 84.4 to 85.2 (-O3) | 134 to 137 |
| `Interval<double, 2>`, width 1e-6 | 275 to 297 (-O2), 276 to 291 (-O3) | 231 to 246 (-O2), 227 to 243 (-O3) | 513 to 522 | 491 to 507 |
| `Ball<double, 1>`, width 1e-6 | 18.2 to 18.8 (-O2), 17.8 to 18.1 (-O3) | 20.8 to 21.5 (-O2), 21.8 to 22.2 (-O3) | 48 to 49.3 | 46.1 to 48.1 |
| `Ball<double, 2>`, width 1e-6 | 37.3 to 39.1 (-O2), 36.7 to 38.6 (-O3) | 39.8 to 42.5 (-O2), 39 to 42.2 (-O3) | 92.2 to 94 | 86.1 to 87.6 |
| `Interval<double, 1>`, width 0 | 74.1 to 76.2 | 51.1 to 51.2 (-O2), 47.6 to 49 (-O3) | 107 to 110 (-O2), 97.1 to 97.7 (-O3) | 134 to 137 |
| `Interval<double, 2>`, width 0 | 273 to 298 (-O2), 273 to 292 (-O3) | 232 to 249 (-O2), 231 to 243 (-O3) | 537 to 548 | 489 to 505 |
| `Ball<double, 1>`, width 0 | 20.6 to 21.1 (-O2), 19.9 to 20 (-O3) | 21.3 to 22.8 (-O2), 23.2 to 23.6 (-O3) | 50.1 to 51.3 | 48.5 to 49.2 (-O2), 46.6 to 47.3 (-O3) |
| `Ball<double, 2>`, width 0 | 40.3 to 43.3 (-O2), 40.2 to 43.2 (-O3) | 42 to 45.1 (-O2), 41.3 to 45.2 (-O3) | 96 to 97.7 | 89.5 to 91.2 |

| Bisection: what each type found | Width | Evaluations | Parts kept | Not narrowed by split() | Zeros | Radius of the zeros |
|---|---|---:|---:|---:|---:|---|
| `Interval<double, 1>` | 1e-06 | 167 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Interval<double, 1>` | 0 | 435 | 6 | 6 | 4 | 1.11e-16 to 4.44e-16 |
| `Interval<double, 2>` | 1e-06 | 167 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Interval<double, 2>` | 0 | 943 | 44 | 44 | 4 | 3.39e-32 to 2.71e-31 |
| `Ball<double, 1>` | 1e-06 | 179 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Ball<double, 1>` | 0 | 443 | 10 | 10 | 4 | 2.78e-16 to 2.67e-15 |
| `Ball<double, 2>` | 1e-06 | 179 | 4 | 0 | 4 | 9.54e-07 to 9.54e-07 |
| `Ball<double, 2>` | 0 | 875 | 16 | 16 | 4 | 1.17e-31 to 1.01e-30 |

#### Question 11: `self_test()` and the checks

| self_test(), microseconds per call | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `self_test()` | 2.76 to 2.98 (-O2), 3 to 3.08 (-O3) | 2.53 to 2.59 (-O2), 2.58 to 2.66 (-O3) | 8.38 to 8.78 (-O2), 7.49 to 7.58 (-O3) | 6.76 to 6.95 (-O2), 6.97 to 7.16 (-O3) |
| the checks of the environment and the flags, both limb types | 0.00838 to 0.00863 (-O2), 0.00899 to 0.009 (-O3) | 0.00899 (-O2), 0.00778 to 0.00836 (-O3) | 0.0603 to 0.0615 (-O2), 0.058 to 0.0586 (-O3) | 0.0418 to 0.0427 |
| the generated kernels on their fixed operands | 2.71 to 2.93 (-O2), 2.98 to 3.04 (-O3) | 2.54 to 2.63 | 7.99 to 8.36 (-O2), 7.24 to 7.5 (-O3) | 6.47 to 6.73 (-O2), 6.29 to 6.47 (-O3) |

| Compile time, s (minimum wall time; -O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| an empty unit | 0.02; 0.02 | 0.06; 0.05 | 0.02; 0.01 | 0.04; 0.04 |
| `kairn/kairn.hpp`, nothing used | 0.14; 0.14 | 0.26; 0.26 | 0.43; 0.43 | 0.67; 0.67 |
| one call of `kairn::self_test()` | 1.19; 1.21 | 3.85; 4.02 | 6.40; 6.50 | 3.88; 3.89 |
| one call of `kairn::self_test()`, over the include alone | 1.05; 1.07 | 3.59; 3.76 | 5.97; 6.07 | 3.21; 3.21 |
| peak memory of `self_test`, MB | 143; 143 | 258; 262 | 236; 238 | 151; 151 |

| KAIRN_CHECKS 1 over 0 | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, `Interval<T, 1>`, loop | 2.13 | 2.58 to 2.75 (-O2), 2.56 to 2.60 (-O3) | 2.96 to 3.01 | 3.46 to 3.53 |
| `X * Y`, `Interval<T, 1>`, loop | 1.33 to 1.36 | 1.12 to 1.15 | 2.19 to 2.22 | 1.26 to 1.29 |
| `X + Y`, `Interval<T, 2>`, loop | 1.16 to 1.20 | 2.00 (-O2), 1.87 to 1.91 (-O3) | 1.36 to 1.38 | 1.30 to 1.34 |
| `X * Y`, `Interval<T, 2>`, loop | 1.06 to 1.09 | 1.12 to 1.15 | 1.17 to 1.18 | 1.19 to 1.22 (-O2), 1.18 to 1.24 (-O3) |
| `S + X`, `Interval<T, 1>`, chain | 0.99 to 1.02 | 1.17 to 1.22 (-O2), 1.10 to 1.13 (-O3) | 1.97 to 2.00 | 2.40 to 2.45 |
| `P * X`, `Interval<T, 1>`, chain | 1.00 to 1.01 (-O2), 0.95 to 1.02 (-O3) | 1.06 (-O2), 1.04 to 1.10 (-O3) | 1.08 to 1.11 | 1.22 to 1.25 |
| `S + X`, `Interval<T, 2>`, chain | 1.00 to 1.02 | 1.19 to 1.25 (-O2), 1.21 to 1.25 (-O3) | 1.11 to 1.15 | 1.16 to 1.20 |
| `P * X`, `Interval<T, 2>`, chain | 1.00 to 1.02 | 1.04 to 1.07 (-O2), 1.00 to 1.01 (-O3) | 1.09 to 1.11 | 1.03 to 1.05 |
| `hull`, `Interval<T, 1>`, loop | 6.19 to 6.32 (-O2), 6.10 to 6.32 (-O3) | 4.20 to 4.40 (-O2), 5.80 (-O3) | 11.2 (-O2), 11.6 (-O3) | 24.6 to 25.2 |
| `split()`, `Interval<T, 1>`, loop | 1.20 to 1.23 (-O2), 1.25 to 1.27 (-O3) | 2.10 to 2.14 (-O2), 1.44 to 1.45 (-O3) | 2.02 to 2.03 (-O2), 1.69 (-O3) | 1.59 to 1.61 (-O2), 1.57 to 1.65 (-O3) |
| Horner, `Interval<T, 1>` | 1.05 (-O2), 0.98 to 1.05 (-O3) | 0.95 to 1.01 (-O2), 1.06 to 1.10 (-O3) | 1.52 to 1.56 | 1.72 to 1.75 |
| Horner, `Interval<T, 2>` | 1.00 to 1.01 | 1.28 to 1.38 (-O2), 1.23 to 1.25 (-O3) | 1.04 to 1.06 | 1.06 to 1.08 |
| `less`, `Interval<T, 1>` | 4.70 to 4.97 (-O2), 4.83 to 4.84 (-O3) | 3.83 to 3.86 (-O2), 4.08 to 4.15 (-O3) | 4.25 to 4.29 | 6.87 to 7.03 |
| `contains(t)`, `Interval<T, 1>` | 4.50 to 4.60 | 3.91 to 4.00 (-O2), 3.76 to 3.83 (-O3) | 14.1 to 14.3 | 16.3 to 16.6 (-O2), 15.3 to 16.6 (-O3) |
| `certainly_positive()`, `Interval<T, 1>` | 2.72 to 2.75 | 4.01 to 4.03 (-O2), 5.46 to 5.47 (-O3) | 5.47 to 5.49 (-O2), 21.5 to 21.7 (-O3) | 6.25 to 6.48 (-O2), 5.78 to 6.49 (-O3) |
| `hull`, `Interval<T, 1>` | 6.20 to 6.32 | 4.40 to 4.44 (-O2), 5.71 to 5.83 (-O3) | 11.1 to 11.3 | 25.3 to 25.7 |
| `split()`, `Interval<T, 1>` | 1.20 to 1.23 (-O2), 1.25 (-O3) | 2.06 to 2.15 (-O2), 1.32 to 1.40 (-O3) | 1.46 to 1.48 (-O2), 1.60 to 1.62 (-O3) | 1.42 to 1.45 |
| the conversion, `Interval<T, 1>` | 1.10 to 1.12 (-O2), 1.12 to 1.20 (-O3) | 1.58 to 1.69 (-O2), 1.21 to 1.24 (-O3) | 1.59 to 1.63 | 1.20 to 1.22 |
| `less`, `Interval<T, 2>` | 5.08 to 5.12 (-O2), 4.84 to 5.16 (-O3) | 6.05 to 6.09 | 4.35 to 4.39 (-O2), 4.02 to 4.05 (-O3) | 12.7 to 12.9 |
| `contains(t)`, `Interval<T, 2>` | 3.28 to 3.34 (-O2), 3.34 to 3.43 (-O3) | 3.52 (-O2), 3.10 (-O3) | 7.16 to 7.18 (-O2), 7.35 to 7.43 (-O3) | 18.5 to 18.9 |
| `certainly_positive()`, `Interval<T, 2>` | 2.55 to 2.60 | 7.90 to 7.97 (-O2), 6.47 (-O3) | 7.16 to 7.21 (-O2), 7.66 to 7.73 (-O3) | 11.4 to 11.6 (-O2), 11.2 to 11.5 (-O3) |
| `hull`, `Interval<T, 2>` | 4.17 (-O2), 3.91 to 4.17 (-O3) | 4.38 to 4.39 (-O2), 4.18 to 4.48 (-O3) | 5.37 to 5.44 (-O2), 4.81 to 4.88 (-O3) | 20.0 to 20.5 |
| `split()`, `Interval<T, 2>` | 1.40 to 1.53 (-O2), 1.34 to 1.42 (-O3) | 1.35 to 1.39 | 1.63 (-O2), 1.12 (-O3) | 1.11 to 1.14 |
| the conversion, `Interval<T, 2>` | 1.05 to 1.11 (-O2), 1.03 to 1.11 (-O3) | 1.11 to 1.16 | 1.34 (-O2), 1.17 to 1.19 (-O3) | 1.10 to 1.13 |
| `less`, `Ball<T, 1>` | 1.71 to 1.76 | 1.96 (-O2), 2.20 to 2.27 (-O3) | 1.70 to 1.73 | 4.19 to 4.30 |
| `contains(t)`, `Ball<T, 1>` | 2.87 to 2.92 (-O2), 2.91 to 3.09 (-O3) | 2.46 to 2.47 (-O2), 2.71 to 2.77 (-O3) | 5.04 to 5.06 (-O2), 5.66 to 5.71 (-O3) | 9.9 to 10.1 |
| `certainly_positive()`, `Ball<T, 1>` | 7.85 to 8.03 | 9.61 (-O2), 8.56 to 8.57 (-O3) | 22.6 to 22.7 (-O2), 24.3 to 24.5 (-O3) | 12.0 to 13.7 (-O2), 12.4 to 13.4 (-O3) |
| `hull`, `Ball<T, 1>` | 1.20 to 1.23 | 1.29 to 1.30 (-O2), 1.37 to 1.44 (-O3) | 1.21 (-O2), 1.14 to 1.16 (-O3) | 1.44 to 1.47 |
| `split()`, `Ball<T, 1>` | 1.10 to 1.14 (-O2), 1.23 to 1.26 (-O3) | 2.15 (-O2), 1.85 (-O3) | 2.29 to 2.31 (-O2), 2.22 to 2.24 (-O3) | 1.60 to 1.62 (-O2), 1.58 to 2.68 (-O3) |
| the conversion, `Ball<T, 1>` | 1.63 to 1.67 | 2.00 to 2.02 (-O2), 1.86 to 1.92 (-O3) | 2.86 to 2.92 | 2.31 to 2.36 |
| `less`, `Ball<T, 2>` | 1.36 to 1.39 | 1.86 to 1.97 (-O2), 1.96 to 2.06 (-O3) | 1.74 (-O2), 1.66 to 1.68 (-O3) | 1.24 to 1.28 |
| `contains(t)`, `Ball<T, 2>` | 1.91 to 1.99 (-O2), 1.99 to 2.00 (-O3) | 1.75 to 1.80 | 1.75 to 1.76 (-O2), 2.37 to 2.40 (-O3) | 1.72 to 1.75 |
| `certainly_positive()`, `Ball<T, 2>` | 6.62 to 6.75 (-O2), 6.75 to 6.89 (-O3) | 6.14 to 6.48 (-O2), 6.41 (-O3) | 14.0 to 15.8 (-O2), 14.3 to 14.4 (-O3) | 17.1 to 17.3 (-O2), 16.3 to 17.0 (-O3) |
| `hull`, `Ball<T, 2>` | 1.01 to 1.05 | 1.09 to 1.13 (-O2), 1.05 to 1.08 (-O3) | 1.07 to 1.12 | 1.04 to 1.06 |
| `split()`, `Ball<T, 2>` | 1.15 to 1.19 (-O2), 1.11 to 1.19 (-O3) | 1.30 to 1.35 (-O2), 1.22 to 1.26 (-O3) | 1.32 (-O2), 1.17 to 1.18 (-O3) | 1.18 to 1.20 |
| the conversion, `Ball<T, 2>` | 1.07 to 1.15 (-O2), 1.07 to 1.08 (-O3) | 0.84 to 0.88 (-O2), 1.62 to 1.66 (-O3) | 1.07 to 1.09 (-O2), 1.14 to 1.15 (-O3) | 1.07 to 1.09 |
| control: the kernel `interval_mul_1`, loop | 0.97 to 1.00 | 0.98 to 1.02 | 1.00 to 1.01 | 0.99 to 1.01 |
| control: the kernel `ball_less_2`, loop | 0.97 to 1.00 (-O2), 0.99 to 1.03 (-O3) | 1.00 to 1.06 (-O2), 0.95 to 1.00 (-O3) | 0.99 to 1.00 | 0.99 to 1.01 |
| control: the kernel `interval_split_2`, loop | 0.93 to 0.99 (-O2), 0.97 to 0.99 (-O3) | 0.97 to 1.01 | 1.00 | 0.98 to 1.00 |

| Times with KAIRN_CHECKS 0; 1 (ns) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `m2/tp/interval_add_1/op` | 1.87; 3.99 (-O2), 1.87; 3.99 (-O3) | 1.74; 4.57 (-O2), 1.76; 4.52 (-O3) | 3.52; 10.5 (-O2), 3.53; 10.6 (-O3) | 4.51; 15.8 (-O2), 4.51; 15.8 (-O3) |
| `m2/tp/interval_mul_1/op` | 6.07; 8.19 (-O2), 6.03; 8.21 (-O3) | 7.94; 9.04 (-O2), 8.05; 9.02 (-O3) | 9.86; 21.7 (-O2), 9.87; 21.7 (-O3) | 16.9; 21.8 (-O2), 17; 21.8 (-O3) |
| `m2/tp/interval_add_2/op` | 8.43; 10.2 (-O2), 8.43; 9.76 (-O3) | 7.13; 14.2 (-O2), 7.54; 14.1 (-O3) | 24.3; 33.5 (-O2), 24.3; 33.1 (-O3) | 18.5; 24.4 (-O2), 18.5; 24.4 (-O3) |
| `m2e/tp/i1_less/op` | 0.644; 3.11 (-O2), 0.662; 3.2 (-O3) | 0.799; 3.08 (-O2), 0.805; 3.3 (-O3) | 1.95; 8.31 (-O2), 1.94; 8.29 (-O3) | 1.99; 13.8 (-O2), 1.99; 13.8 (-O3) |
| `m2e/tp/i1_contains_t/op` | 0.347; 1.59 (-O2), 0.347; 1.56 (-O3) | 0.333; 1.31 (-O2), 0.35; 1.32 (-O3) | 0.53; 7.5 (-O2), 0.531; 7.5 (-O3) | 0.508; 8.34 (-O2), 0.507; 7.86 (-O3) |
| `m2e/tp/b2_less/op` | 6.17; 8.61 (-O2), 6.22; 8.61 (-O3) | 4.67; 9.22 (-O2), 5.02; 9.84 (-O3) | 16.3; 28.4 (-O2), 16.2; 27.2 (-O3) | 19.3; 24.4 (-O2), 19.4; 24.4 (-O3) |
| `m2e/tp/i2_split/op` | 7.32; 11.2 (-O2), 7.85; 10.6 (-O3) | 6.73; 9.32 (-O2), 6.33; 8.8 (-O3) | 16.2; 26.4 (-O2), 23.5; 26.3 (-O3) | 16.4; 18.6 (-O2), 16.4; 18.6 (-O3) |
| `m2/tp/interval_mul_1/kairn` | 6.34; 6.14 (-O2), 6.31; 6.28 (-O3) | 7.77; 7.91 (-O2), 7.97; 7.92 (-O3) | 9.85; 9.86 (-O2), 9.86; 9.87 (-O3) | 16.9; 17 (-O2), 17; 16.9 (-O3) |

#### Question 12: compile time of the enclosure interface

| compare: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 4.50; 4.56 | 5.54; 8.41 | 62.3; 62.7 | 8.05; 8.15 |
| 1000, outlined | 4.41; 4.50 | 5.54; 8.42 | 62.4; 62.4 | 8.04; 8.04 |
| 1000, external | 4.47; 4.49 | 5.52; 8.38 | 62.9; 62.5 | 8.00; 7.97 |
| 1000, calls | 0.08; 0.08 | 0.33; 0.67 | 0.33; 0.33 | 0.38; 0.38 |
| 10000, inline | 730; – | 140; – | stopped at 1800; – | 1435; – |
| 10000, outlined | 681; – | 143; – | stopped at 1800; – | 1513; – |
| 10000, external | 673; – | 134; – | stopped at 1800; – | 1579; – |
| 10000, calls | 2.68; – | 3.80; – | 4.49; – | 12.2; – |

| compare: peak memory, MB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 426; 432 | 558; 582 | 583; 583 | 209; 209 |
| 1000, outlined | 430; 423 | 556; 583 | 582; 582 | 209; 210 |
| 1000, external | 430; 419 | 558; 584 | 582; 582 | 209; 209 |
| 1000, calls | 47; 47 | 66; 67 | 53; 52 | 107; 107 |
| 10000, inline | 3283; – | 4334; – |  | 1090; – |
| 10000, outlined | 3269; – | 4292; – |  | 1090; – |
| 10000, external | 3298; – | 4336; – |  | 1090; – |
| 10000, calls | 184; – | 503; – | 300; – | 214; – |

| compare: object, KB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 212; 212 | 255; 256 | 387; 387 | 325; 325 |
| 1000, outlined | 212; 212 | 255; 256 | 387; 387 | 325; 325 |
| 1000, external | 212; 212 | 255; 256 | 387; 387 | 325; 325 |
| 1000, calls | 25; 25 | 25; 29 | 53; 53 | 56; 56 |
| 10000, inline | 2111; – | 2638; – |  | 3332; – |
| 10000, outlined | 2111; – | 2638; – |  | 3332; – |
| 10000, external | 2111; – | 2638; – |  | 3332; – |
| 10000, calls | 285; – | 270; – | 519; – | 548; – |

| contains: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 0.53; 1.77 | 1.54; 1.96 | 2.67; 2.77 | 2.37; 2.37 |
| 1000, outlined | 0.57; 1.77 | 1.55; 1.97 | 2.67; 2.77 | 2.37; 2.37 |
| 1000, external | 0.54; 1.77 | 1.55; 1.96 | 2.67; 2.77 | 2.37; 2.37 |
| 1000, calls | 0.10; 0.10 | 0.32; 0.66 | 0.35; 0.36 | 0.40; 0.40 |
| 10000, inline | 9.35; – | 22.3; – | 107; – | 72.1; – |
| 10000, outlined | 8.99; – | 22.1; – | 108; – | 71.0; – |
| 10000, external | 8.60; – | 22.3; – | 106; – | 71.2; – |
| 10000, calls | 2.36; – | 4.08; – | 5.30; – | 10.8; – |

| contains: peak memory, MB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 118; 349 | 260; 256 | 176; 174 | 152; 152 |
| 1000, outlined | 121; 354 | 262; 277 | 177; 174 | 152; 152 |
| 1000, external | 119; 351 | 273; 256 | 176; 174 | 152; 152 |
| 1000, calls | 53; 53 | 75; 82 | 54; 55 | 107; 106 |
| 10000, inline | 622; – | 1848; – | 916; – | 552; – |
| 10000, outlined | 604; – | 1847; – | 915; – | 552; – |
| 10000, external | 613; – | 1713; – | 916; – | 552; – |
| 10000, calls | 221; – | 649; – | 308; – | 216; – |

| contains: object, KB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 103; 139 | 60; 59 | 119; 117 | 171; 171 |
| 1000, outlined | 103; 139 | 60; 59 | 119; 117 | 171; 171 |
| 1000, external | 103; 139 | 60; 59 | 119; 117 | 171; 171 |
| 1000, calls | 25; 25 | 25; 29 | 53; 53 | 55; 55 |
| 10000, inline | 1032; – | 397; – | 832; – | 1860; – |
| 10000, outlined | 1032; – | 397; – | 832; – | 1860; – |
| 10000, external | 1032; – | 397; – | 832; – | 1860; – |
| 10000, calls | 282; – | 295; – | 516; – | 539; – |

| setops: compile time, s of processor time (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 0.47; 0.54 | 2.06; 2.71 | 2.99; 3.13 | 1.75; 1.75 |
| 1000, outlined | 0.47; 0.54 | 2.04; 2.66 | 2.98; 3.13 | 1.75; 1.75 |
| 1000, external | 0.47; 0.54 | 1.99; 2.69 | 2.98; 3.16 | 1.75; 1.75 |
| 1000, calls | 0.22; 0.22 | 0.50; 1.04 | 0.55; 0.56 | 0.45; 0.45 |
| 10000, inline | 5.31; – | 14.2; – | 24.4; – | 17.8; – |
| 10000, outlined | 5.88; – | 14.3; – | 24.5; – | 17.7; – |
| 10000, external | 5.78; – | 14.3; – | 24.5; – | 17.8; – |
| 10000, calls | 6.85; – | 6.43; – | 8.49; – | 16.4; – |

| setops: peak memory, MB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 92; 98 | 286; 298 | 196; 200 | 133; 133 |
| 1000, outlined | 92; 99 | 277; 300 | 195; 200 | 133; 133 |
| 1000, external | 92; 106 | 283; 291 | 196; 182 | 133; 133 |
| 1000, calls | 68; 68 | 93; 100 | 69; 69 | 113; 113 |
| 10000, inline | 469; – | 1204; – | 619; – | 381; – |
| 10000, outlined | 447; – | 1204; – | 616; – | 381; – |
| 10000, external | 460; – | 1202; – | 614; – | 382; – |
| 10000, calls | 339; – | 841; – | 451; – | 266; – |

| setops: object, KB (-O2; -O3) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 1000, inline | 68; 92 | 68; 68 | 139; 138 | 155; 156 |
| 1000, outlined | 68; 92 | 68; 68 | 139; 138 | 155; 156 |
| 1000, external | 68; 92 | 68; 68 | 139; 138 | 155; 156 |
| 1000, calls | 39; 39 | 36; 36 | 80; 80 | 77; 77 |
| 10000, inline | 623; – | 628; – | 1057; – | 1369; – |
| 10000, outlined | 623; – | 628; – | 1057; – | 1369; – |
| 10000, external | 623; – | 628; – | 1057; – | 1369; – |
| 10000, calls | 416; – | 374; – | 781; – | 753; – |

### Third part

The tables of the third part are printed by `python3 bench/m2_report.py --part 3
results/milestone2/bench` from the stored files, and those of the answers are rows of them.

#### Configurations of the third part

| Configuration (third part) | CPU | Compiler | Flags | Runs per item (arrays, short, entry pairs, short ball vectors triplets, acc, bv) | Dates, commits |
|---|---|---|---|---|---|
| linux-clang-inline-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror --gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13 -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3, 3, 3 | 2026-11-22, `9e114bb`, `be95dbb`, `dae16be` |
| linux-clang-inline-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror --gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13 -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3, 3, 3 | 2026-11-22, `9e114bb`, `be95dbb`, `dae16be` |
| linux-gcc-inline-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3, 3, 3 | 2026-11-22, `9e114bb`, `be95dbb`, `dae16be` |
| linux-gcc-inline-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 3, 3, 3, 3, 3, 3 | 2026-11-22, `9e114bb`, `be95dbb`, `dae16be` |
| mac-appleclang-inline-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | 0, 3, 3, 3, 0, 0 | 2026-11-22, `be95dbb` |
| mac-appleclang-inline-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | 0, 3, 3, 3, 0, 0 | 2026-11-22, `be95dbb` |
| mac-gcc16-inline-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | 0, 3, 3, 3, 0, 0 | 2026-11-22, `be95dbb` |
| mac-gcc16-inline-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | 0, 3, 3, 3, 0, 0 | 2026-11-22, `be95dbb` |

#### Runs of the third part

| Run (third part) | Functions checked, failed | Over the fastest run: median, 90th percentile | Median over minimum within the run (median function) | Load average (1 min) at start, end |
|---|---|---|---|---|
| `arrays-linux-clang-O2-r1.json` | 528, 0 | 1.003, 1.011 | 1.005 | 64.8, 63.6 |
| `arrays-linux-clang-O2-r2.json` | 528, 0 | 1.022, 1.033 | 1.010 | 72.7, 77.3 |
| `arrays-linux-clang-O2-r3.json` | 528, 0 | 1.000, 1.010 | 1.005 | 94.8, 90.8 |
| `arrays-linux-clang-O3-r1.json` | 528, 0 | 1.004, 1.018 | 1.006 | 63.4, 65.6 |
| `arrays-linux-clang-O3-r2.json` | 528, 0 | 1.003, 1.009 | 1.018 | 97.3, 97.5 |
| `arrays-linux-clang-O3-r3.json` | 528, 0 | 1.000, 1.014 | 1.019 | 82.0, 98.4 |
| `arrays-linux-gcc-O2-r1.json` | 528, 0 | 1.024, 1.038 | 1.030 | 68.8, 75.4 |
| `arrays-linux-gcc-O2-r2.json` | 528, 0 | 1.000, 1.015 | 1.018 | 66.9, 66.1 |
| `arrays-linux-gcc-O2-r3.json` | 528, 0 | 1.001, 1.009 | 1.019 | 93.5, 97.7 |
| `arrays-linux-gcc-O3-r1.json` | 528, 0 | 1.002, 1.014 | 1.009 | 73.1, 61.7 |
| `arrays-linux-gcc-O3-r2.json` | 528, 0 | 1.001, 1.023 | 1.008 | 99.7, 91.5 |
| `arrays-linux-gcc-O3-r3.json` | 528, 0 | 1.001, 1.017 | 1.007 | 99.2, 84.5 |
| `short-linux-clang-O2-r1.json` | 224, 0 | 1.001, 1.002 | 1.005 | 60.0, 58.9 |
| `short-linux-clang-O2-r2.json` | 224, 0 | 1.007, 1.009 | 1.006 | 64.2, 66.2 |
| `short-linux-clang-O2-r3.json` | 224, 0 | 1.000, 1.000 | 1.002 | 65.2, 64.6 |
| `short-linux-clang-O3-r1.json` | 224, 0 | 1.002, 1.004 | 1.006 | 59.0, 60.6 |
| `short-linux-clang-O3-r2.json` | 224, 0 | 1.004, 1.007 | 1.006 | 66.7, 66.8 |
| `short-linux-clang-O3-r3.json` | 224, 0 | 1.000, 1.001 | 1.005 | 64.7, 65.5 |
| `short-linux-gcc-O2-r1.json` | 224, 0 | 1.000, 1.000 | 1.003 | 56.9, 58.0 |
| `short-linux-gcc-O2-r2.json` | 224, 0 | 1.005, 1.006 | 1.005 | 60.5, 60.5 |
| `short-linux-gcc-O2-r3.json` | 224, 0 | 1.007, 1.009 | 1.007 | 67.3, 67.9 |
| `short-linux-gcc-O3-r1.json` | 224, 0 | 1.000, 1.001 | 1.003 | 58.0, 60.4 |
| `short-linux-gcc-O3-r2.json` | 224, 0 | 1.002, 1.003 | 1.009 | 60.5, 63.4 |
| `short-linux-gcc-O3-r3.json` | 224, 0 | 1.000, 1.002 | 1.004 | 67.4, 65.4 |
| `short-mac-appleclang-O2-r1.json` | 224, 0 | 1.119, 1.139 | 1.052 | 9.6, 10.4 |
| `short-mac-appleclang-O2-r2.json` | 224, 0 | 1.000, 1.000 | 1.139 | 9.5, 9.8 |
| `short-mac-appleclang-O2-r3.json` | 224, 0 | 1.119, 1.139 | 1.053 | 11.4, 11.4 |
| `short-mac-appleclang-O3-r1.json` | 224, 0 | 1.116, 1.137 | 1.040 | 10.4, 9.9 |
| `short-mac-appleclang-O3-r2.json` | 224, 0 | 1.000, 1.000 | 1.140 | 9.8, 10.4 |
| `short-mac-appleclang-O3-r3.json` | 224, 0 | 1.087, 1.137 | 1.053 | 11.4, 10.5 |
| `short-mac-gcc16-O2-r1.json` | 224, 0 | 1.104, 1.137 | 1.035 | 9.9, 9.6 |
| `short-mac-gcc16-O2-r2.json` | 224, 0 | 1.000, 1.048 | 1.126 | 10.4, 10.2 |
| `short-mac-gcc16-O2-r3.json` | 224, 0 | 1.032, 1.098 | 1.097 | 10.4, 10.0 |
| `short-mac-gcc16-O3-r1.json` | 224, 0 | 1.016, 1.102 | 1.072 | 9.5, 9.5 |
| `short-mac-gcc16-O3-r2.json` | 224, 0 | 1.092, 1.137 | 1.052 | 10.2, 11.4 |
| `short-mac-gcc16-O3-r3.json` | 224, 0 | 1.000, 1.072 | 1.112 | 10.0, 9.7 |
| `acc-linux-clang-O2-r1.json` | 138, 0 | 1.000, 1.002 | 1.004 | 98.6, 95.8 |
| `acc-linux-clang-O2-r2.json` | 138, 0 | 1.001, 1.003 | 1.024 | 92.5, 93.8 |
| `acc-linux-clang-O2-r3.json` | 138, 0 | 1.000, 1.002 | 1.003 | 89.7, 88.6 |
| `acc-linux-clang-O3-r1.json` | 138, 0 | 1.000, 1.001 | 1.005 | 95.5, 93.8 |
| `acc-linux-clang-O3-r2.json` | 138, 0 | 1.001, 1.003 | 1.004 | 93.5, 91.8 |
| `acc-linux-clang-O3-r3.json` | 138, 0 | 1.016, 1.018 | 1.004 | 88.6, 90.6 |
| `acc-linux-gcc-O2-r1.json` | 138, 0 | 1.002, 1.005 | 1.025 | 99.3, 100.3 |
| `acc-linux-gcc-O2-r2.json` | 138, 0 | 1.001, 1.004 | 1.005 | 93.3, 92.5 |
| `acc-linux-gcc-O2-r3.json` | 138, 0 | 1.000, 1.001 | 1.004 | 92.5, 89.9 |
| `acc-linux-gcc-O3-r1.json` | 138, 0 | 1.002, 1.003 | 1.006 | 100.9, 99.0 |
| `acc-linux-gcc-O3-r2.json` | 138, 0 | 1.001, 1.003 | 1.004 | 92.5, 91.9 |
| `acc-linux-gcc-O3-r3.json` | 138, 0 | 1.000, 1.001 | 1.007 | 89.8, 89.6 |
| `bv-linux-clang-O2-r1.json` | 192, 0 | 1.019, 1.023 | 1.006 | 92.1, 92.5 |
| `bv-linux-clang-O2-r2.json` | 192, 0 | 1.020, 1.025 | 1.008 | 94.6, 94.5 |
| `bv-linux-clang-O2-r3.json` | 192, 0 | 1.000, 1.000 | 1.005 | 91.2, 91.5 |
| `bv-linux-clang-O3-r1.json` | 192, 0 | 1.017, 1.020 | 1.009 | 92.5, 91.9 |
| `bv-linux-clang-O3-r2.json` | 192, 0 | 1.007, 1.013 | 1.021 | 94.5, 95.5 |
| `bv-linux-clang-O3-r3.json` | 192, 0 | 1.000, 1.000 | 1.005 | 91.5, 90.3 |
| `bv-linux-gcc-O2-r1.json` | 192, 0 | 1.018, 1.023 | 1.012 | 90.6, 92.0 |
| `bv-linux-gcc-O2-r2.json` | 192, 0 | 1.000, 1.004 | 1.023 | 91.9, 92.8 |
| `bv-linux-gcc-O2-r3.json` | 192, 0 | 1.000, 1.006 | 1.024 | 95.5, 93.7 |
| `bv-linux-gcc-O3-r1.json` | 192, 0 | 1.022, 1.026 | 1.007 | 92.0, 92.1 |
| `bv-linux-gcc-O3-r2.json` | 192, 0 | 1.020, 1.027 | 1.010 | 92.8, 94.0 |
| `bv-linux-gcc-O3-r3.json` | 192, 0 | 1.000, 1.000 | 1.007 | 93.7, 91.2 |
| `entry-linux-clang-O2-c1-r1.json` | 518, 0 | 1.001, 1.004 | 1.004 | 60.7, 65.7 |
| `entry-linux-clang-O2-c1-r2.json` | 518, 0 | 1.002, 1.004 | 1.019 | 63.9, 66.3 |
| `entry-linux-clang-O2-c1-r3.json` | 518, 0 | 1.000, 1.002 | 1.004 | 71.3, 69.2 |
| `entry-linux-clang-O2-c0-r1.json` | 518, 0 | 1.000, 1.001 | 1.006 | 65.7, 74.2 |
| `entry-linux-clang-O2-c0-r2.json` | 518, 0 | 1.008, 1.014 | 1.022 | 66.6, 72.5 |
| `entry-linux-clang-O2-c0-r3.json` | 518, 0 | 1.001, 1.005 | 1.004 | 69.0, 67.0 |
| `entry-linux-clang-O3-c1-r1.json` | 518, 0 | 1.001, 1.003 | 1.005 | 73.7, 71.0 |
| `entry-linux-clang-O3-c1-r2.json` | 518, 0 | 1.005, 1.011 | 1.022 | 73.0, 70.8 |
| `entry-linux-clang-O3-c1-r3.json` | 518, 0 | 1.000, 1.002 | 1.005 | 67.0, 67.6 |
| `entry-linux-clang-O3-c0-r1.json` | 518, 0 | 1.001, 1.005 | 1.004 | 70.9, 64.4 |
| `entry-linux-clang-O3-c0-r2.json` | 518, 0 | 1.000, 1.003 | 1.007 | 70.6, 64.8 |
| `entry-linux-clang-O3-c0-r3.json` | 518, 0 | 1.002, 1.008 | 1.004 | 67.6, 66.5 |
| `entry-linux-gcc-O2-c1-r1.json` | 518, 0 | 1.003, 1.006 | 1.005 | 65.5, 63.1 |
| `entry-linux-gcc-O2-c1-r2.json` | 518, 0 | 1.003, 1.008 | 1.004 | 63.9, 61.0 |
| `entry-linux-gcc-O2-c1-r3.json` | 518, 0 | 1.000, 1.000 | 1.003 | 64.6, 65.8 |
| `entry-linux-gcc-O2-c0-r1.json` | 518, 0 | 1.000, 1.002 | 1.006 | 63.0, 62.6 |
| `entry-linux-gcc-O2-c0-r2.json` | 518, 0 | 1.003, 1.007 | 1.004 | 61.5, 61.4 |
| `entry-linux-gcc-O2-c0-r3.json` | 518, 0 | 1.000, 1.009 | 1.005 | 65.5, 64.0 |
| `entry-linux-gcc-O3-c1-r1.json` | 518, 0 | 1.002, 1.005 | 1.004 | 62.8, 63.3 |
| `entry-linux-gcc-O3-c1-r2.json` | 518, 0 | 1.000, 1.002 | 1.004 | 61.4, 62.0 |
| `entry-linux-gcc-O3-c1-r3.json` | 518, 0 | 1.000, 1.003 | 1.004 | 63.5, 66.8 |
| `entry-linux-gcc-O3-c0-r1.json` | 518, 0 | 1.003, 1.006 | 1.004 | 63.2, 61.1 |
| `entry-linux-gcc-O3-c0-r2.json` | 518, 0 | 1.002, 1.005 | 1.005 | 62.2, 64.3 |
| `entry-linux-gcc-O3-c0-r3.json` | 518, 0 | 1.000, 1.004 | 1.005 | 66.0, 71.3 |
| `entry-mac-appleclang-O2-c1-r1.json` | 518, 0 | 1.138, 1.176 | 1.139 | 11.3, 12.6 |
| `entry-mac-appleclang-O2-c1-r2.json` | 518, 0 | 1.000, 1.000 | 1.043 | 5.9, 6.0 |
| `entry-mac-appleclang-O2-c1-r3.json` | 518, 0 | 1.055, 1.057 | 1.025 | 6.4, 6.3 |
| `entry-mac-appleclang-O2-c0-r1.json` | 518, 0 | 1.100, 1.157 | 1.163 | 13.2, 11.5 |
| `entry-mac-appleclang-O2-c0-r2.json` | 518, 0 | 1.000, 1.000 | 1.048 | 6.0, 5.4 |
| `entry-mac-appleclang-O2-c0-r3.json` | 518, 0 | 1.044, 1.056 | 1.075 | 6.3, 6.8 |
| `entry-mac-appleclang-O3-c1-r1.json` | 518, 0 | 1.147, 1.188 | 1.116 | 11.5, 11.4 |
| `entry-mac-appleclang-O3-c1-r2.json` | 518, 0 | 1.000, 1.000 | 1.057 | 5.4, 6.9 |
| `entry-mac-appleclang-O3-c1-r3.json` | 518, 0 | 1.055, 1.058 | 1.060 | 6.8, 6.5 |
| `entry-mac-appleclang-O3-c0-r1.json` | 518, 0 | 1.129, 1.180 | 1.103 | 11.4, 10.5 |
| `entry-mac-appleclang-O3-c0-r2.json` | 518, 0 | 1.000, 1.000 | 1.002 | 6.9, 3.5 |
| `entry-mac-appleclang-O3-c0-r3.json` | 518, 0 | 1.036, 1.043 | 1.053 | 6.5, 6.8 |
| `entry-mac-gcc16-O2-c1-r1.json` | 518, 0 | 1.128, 1.180 | 1.103 | 10.5, 11.0 |
| `entry-mac-gcc16-O2-c1-r2.json` | 518, 0 | 1.000, 1.000 | 1.023 | 3.5, 5.3 |
| `entry-mac-gcc16-O2-c1-r3.json` | 518, 0 | 1.037, 1.047 | 1.088 | 6.8, 7.8 |
| `entry-mac-gcc16-O2-c0-r1.json` | 518, 0 | 1.000, 1.000 | 1.043 | 11.0, 6.8 |
| `entry-mac-gcc16-O2-c0-r2.json` | 518, 0 | 1.019, 1.020 | 1.008 | 5.3, 6.4 |
| `entry-mac-gcc16-O2-c0-r3.json` | 518, 0 | 1.114, 1.150 | 1.080 | 7.8, 8.5 |
| `entry-mac-gcc16-O3-c1-r1.json` | 518, 0 | 1.000, 1.000 | 1.057 | 6.8, 6.2 |
| `entry-mac-gcc16-O3-c1-r2.json` | 518, 0 | 1.018, 1.022 | 1.038 | 6.4, 6.3 |
| `entry-mac-gcc16-O3-c1-r3.json` | 518, 0 | 1.064, 1.108 | 1.137 | 8.5, 9.9 |
| `entry-mac-gcc16-O3-c0-r1.json` | 518, 0 | 1.000, 1.000 | 1.057 | 6.2, 5.7 |
| `entry-mac-gcc16-O3-c0-r2.json` | 518, 0 | 1.018, 1.021 | 1.004 | 6.3, 6.4 |
| `entry-mac-gcc16-O3-c0-r3.json` | 518, 0 | 1.142, 1.151 | 1.090 | 9.9, 10.8 |
| `entryx-linux-clang-O2-c0-r1.json` | 460, 0 | 1.001, 1.010 | 1.005 | 70.8, 75.6 |
| `entryx-linux-clang-O2-c0-r2.json` | 460, 0 | 1.008, 1.014 | 1.007 | 68.5, 70.0 |
| `entryx-linux-clang-O2-c0-r3.json` | 460, 0 | 1.000, 1.003 | 1.005 | 78.6, 84.8 |
| `entryx-linux-clang-O2-c1-r1.json` | 460, 0 | 1.001, 1.009 | 1.004 | 64.9, 70.8 |
| `entryx-linux-clang-O2-c1-r2.json` | 460, 0 | 1.002, 1.007 | 1.014 | 66.7, 68.5 |
| `entryx-linux-clang-O2-c1-r3.json` | 460, 0 | 1.001, 1.008 | 1.011 | 81.2, 78.6 |
| `entryx-linux-clang-O2-cv-r1.json` | 460, 0 | 1.000, 1.007 | 1.005 | 76.6, 77.7 |
| `entryx-linux-clang-O2-cv-r2.json` | 460, 0 | 1.009, 1.015 | 1.008 | 70.0, 72.5 |
| `entryx-linux-clang-O2-cv-r3.json` | 460, 0 | 1.000, 1.007 | 1.007 | 85.4, 91.4 |
| `entryx-linux-clang-O3-c0-r1.json` | 460, 0 | 1.000, 1.005 | 1.004 | 71.1, 71.1 |
| `entryx-linux-clang-O3-c0-r2.json` | 460, 0 | 1.001, 1.019 | 1.011 | 72.9, 72.5 |
| `entryx-linux-clang-O3-c0-r3.json` | 460, 0 | 1.008, 1.017 | 1.018 | 96.0, 97.2 |
| `entryx-linux-clang-O3-c1-r1.json` | 460, 0 | 1.000, 1.004 | 1.005 | 77.7, 71.3 |
| `entryx-linux-clang-O3-c1-r2.json` | 460, 0 | 1.009, 1.017 | 1.008 | 72.5, 73.0 |
| `entryx-linux-clang-O3-c1-r3.json` | 460, 0 | 1.002, 1.007 | 1.025 | 91.4, 95.5 |
| `entryx-linux-clang-O3-cv-r1.json` | 460, 0 | 1.000, 1.006 | 1.006 | 71.1, 72.1 |
| `entryx-linux-clang-O3-cv-r2.json` | 460, 0 | 1.008, 1.026 | 1.005 | 72.5, 72.0 |
| `entryx-linux-clang-O3-cv-r3.json` | 460, 0 | 1.005, 1.021 | 1.024 | 97.2, 98.8 |
| `entryx-linux-gcc-O2-c0-r1.json` | 460, 0 | 1.002, 1.009 | 1.005 | 66.8, 65.8 |
| `entryx-linux-gcc-O2-c0-r2.json` | 460, 0 | 1.001, 1.009 | 1.005 | 65.6, 63.1 |
| `entryx-linux-gcc-O2-c0-r3.json` | 460, 0 | 1.000, 1.007 | 1.005 | 69.0, 70.4 |
| `entryx-linux-gcc-O2-c1-r1.json` | 460, 0 | 1.003, 1.012 | 1.005 | 71.4, 67.2 |
| `entryx-linux-gcc-O2-c1-r2.json` | 460, 0 | 1.000, 1.007 | 1.006 | 71.3, 65.6 |
| `entryx-linux-gcc-O2-c1-r3.json` | 460, 0 | 1.002, 1.009 | 1.006 | 72.2, 69.0 |
| `entryx-linux-gcc-O2-cv-r1.json` | 460, 0 | 1.002, 1.010 | 1.006 | 65.8, 64.6 |
| `entryx-linux-gcc-O2-cv-r2.json` | 460, 0 | 1.000, 1.008 | 1.006 | 63.1, 62.6 |
| `entryx-linux-gcc-O2-cv-r3.json` | 460, 0 | 1.001, 1.006 | 1.005 | 70.6, 70.5 |
| `entryx-linux-gcc-O3-c0-r1.json` | 460, 0 | 1.000, 1.005 | 1.004 | 63.1, 60.6 |
| `entryx-linux-gcc-O3-c0-r2.json` | 460, 0 | 1.001, 1.007 | 1.004 | 61.9, 63.4 |
| `entryx-linux-gcc-O3-c0-r3.json` | 460, 0 | 1.016, 1.024 | 1.013 | 74.0, 80.7 |
| `entryx-linux-gcc-O3-c1-r1.json` | 460, 0 | 1.001, 1.008 | 1.005 | 64.5, 63.1 |
| `entryx-linux-gcc-O3-c1-r2.json` | 460, 0 | 1.000, 1.007 | 1.006 | 62.9, 61.9 |
| `entryx-linux-gcc-O3-c1-r3.json` | 460, 0 | 1.002, 1.009 | 1.005 | 70.5, 73.2 |
| `entryx-linux-gcc-O3-cv-r1.json` | 460, 0 | 1.001, 1.006 | 1.004 | 60.6, 65.0 |
| `entryx-linux-gcc-O3-cv-r2.json` | 460, 0 | 1.000, 1.008 | 1.006 | 63.6, 66.7 |
| `entryx-linux-gcc-O3-cv-r3.json` | 460, 0 | 1.004, 1.012 | 1.026 | 80.7, 81.2 |
| `entryx-mac-appleclang-O2-c0-r1.json` | 460, 0 | 1.047, 1.093 | 1.126 | 10.4, 10.7 |
| `entryx-mac-appleclang-O2-c0-r2.json` | 460, 0 | 1.277, 1.359 | 1.078 | 16.3, 16.0 |
| `entryx-mac-appleclang-O2-c0-r3.json` | 460, 0 | 1.000, 1.000 | 1.016 | 8.0, 6.0 |
| `entryx-mac-appleclang-O2-c1-r1.json` | 460, 0 | 1.032, 1.087 | 1.114 | 10.8, 10.4 |
| `entryx-mac-appleclang-O2-c1-r2.json` | 460, 0 | 1.282, 1.369 | 1.076 | 18.1, 16.3 |
| `entryx-mac-appleclang-O2-c1-r3.json` | 460, 0 | 1.000, 1.014 | 1.047 | 14.5, 8.0 |
| `entryx-mac-appleclang-O2-cv-r1.json` | 460, 0 | 1.066, 1.101 | 1.142 | 10.7, 11.4 |
| `entryx-mac-appleclang-O2-cv-r2.json` | 460, 0 | 1.274, 1.346 | 1.084 | 16.0, 15.0 |
| `entryx-mac-appleclang-O2-cv-r3.json` | 460, 0 | 1.000, 1.000 | 1.022 | 6.0, 5.4 |
| `entryx-mac-appleclang-O3-c0-r1.json` | 460, 0 | 1.089, 1.134 | 1.103 | 11.8, 13.2 |
| `entryx-mac-appleclang-O3-c0-r2.json` | 460, 0 | 1.273, 1.346 | 1.091 | 16.8, 16.9 |
| `entryx-mac-appleclang-O3-c0-r3.json` | 460, 0 | 1.000, 1.000 | 1.090 | 5.9, 8.0 |
| `entryx-mac-appleclang-O3-c1-r1.json` | 460, 0 | 1.089, 1.127 | 1.167 | 11.4, 11.8 |
| `entryx-mac-appleclang-O3-c1-r2.json` | 460, 0 | 1.277, 1.370 | 1.076 | 15.0, 16.8 |
| `entryx-mac-appleclang-O3-c1-r3.json` | 460, 0 | 1.000, 1.000 | 1.027 | 5.4, 5.9 |
| `entryx-mac-appleclang-O3-cv-r1.json` | 460, 0 | 1.097, 1.148 | 1.144 | 13.2, 13.5 |
| `entryx-mac-appleclang-O3-cv-r2.json` | 460, 0 | 1.198, 1.266 | 1.142 | 16.9, 15.6 |
| `entryx-mac-appleclang-O3-cv-r3.json` | 460, 0 | 1.000, 1.000 | 1.145 | 8.0, 9.0 |
| `entryx-mac-gcc16-O2-c0-r1.json` | 460, 0 | 1.000, 1.000 | 1.101 | 14.4, 12.7 |
| `entryx-mac-gcc16-O2-c0-r2.json` | 460, 0 | 1.165, 1.210 | 1.114 | 14.4, 17.2 |
| `entryx-mac-gcc16-O2-c0-r3.json` | 460, 0 | 1.046, 1.089 | 1.053 | 9.2, 10.8 |
| `entryx-mac-gcc16-O2-c1-r1.json` | 460, 0 | 1.000, 1.000 | 1.122 | 13.5, 14.4 |
| `entryx-mac-gcc16-O2-c1-r2.json` | 460, 0 | 1.152, 1.251 | 1.142 | 15.6, 14.4 |
| `entryx-mac-gcc16-O2-c1-r3.json` | 460, 0 | 1.046, 1.136 | 1.053 | 9.0, 9.2 |
| `entryx-mac-gcc16-O2-cv-r1.json` | 460, 0 | 1.000, 1.055 | 1.315 | 12.7, 15.4 |
| `entryx-mac-gcc16-O2-cv-r2.json` | 460, 0 | 1.171, 1.276 | 1.075 | 17.2, 19.2 |
| `entryx-mac-gcc16-O2-cv-r3.json` | 460, 0 | 1.034, 1.118 | 1.053 | 10.8, 9.9 |
| `entryx-mac-gcc16-O3-c0-r1.json` | 460, 0 | 1.253, 1.304 | 1.081 | 17.5, 21.3 |
| `entryx-mac-gcc16-O3-c0-r2.json` | 460, 0 | 1.121, 1.179 | 1.095 | 15.4, 14.6 |
| `entryx-mac-gcc16-O3-c0-r3.json` | 460, 0 | 1.000, 1.000 | 1.095 | 9.5, 9.8 |
| `entryx-mac-gcc16-O3-c1-r1.json` | 460, 0 | 1.202, 1.211 | 1.086 | 15.4, 17.5 |
| `entryx-mac-gcc16-O3-c1-r2.json` | 460, 0 | 1.092, 1.132 | 1.132 | 19.2, 15.4 |
| `entryx-mac-gcc16-O3-c1-r3.json` | 460, 0 | 1.000, 1.000 | 1.053 | 9.9, 9.5 |
| `entryx-mac-gcc16-O3-cv-r1.json` | 460, 0 | 1.367, 1.467 | 1.080 | 21.3, 18.1 |
| `entryx-mac-gcc16-O3-cv-r2.json` | 460, 0 | 1.000, 1.000 | 1.282 | 14.6, 14.5 |
| `entryx-mac-gcc16-O3-cv-r3.json` | 460, 0 | 1.138, 1.153 | 1.053 | 9.8, 9.6 |

| Spread of (third part) | Runs | Spread of a function over the runs: median, 90th percentile, worst | Worst function |
|---|---:|---|---|
| arrays linux-clang-O2 | 3 | 2.2%, 3.7%, 28.4% | `m2a/tp/norm1/kairn` |
| arrays linux-clang-O3 | 3 | 0.6%, 3.1%, 25.8% | `m2a/tp/norm1/kairn` |
| arrays linux-gcc-O2 | 3 | 2.4%, 4.3%, 103.1% | `m2af/llc/norm1/plain` |
| arrays linux-gcc-O3 | 3 | 0.4%, 3.7%, 88.1% | `m2af/tp/norm1/plain` |
| short linux-clang-O2 | 3 | 0.7%, 0.9%, 1.7% | `m2k/tp/sdot1_k1/kairn` |
| short linux-clang-O3 | 3 | 0.4%, 0.7%, 3.5% | `m2k/tp/ssum1_k2/kairn` |
| short linux-gcc-O2 | 3 | 0.7%, 0.9%, 3.6% | `m2k/tp/ssum1_k16/kairn` |
| short linux-gcc-O3 | 3 | 0.2%, 0.4%, 1.7% | `m2k/tp/ssum1_k64/kairn` |
| short mac-appleclang-O2 | 3 | 13.2%, 15.6%, 188.8% | `m2k/lat/ssum2_k2/op` |
| short mac-appleclang-O3 | 3 | 11.7%, 13.8%, 207.5% | `m2k/lat/ssum1_k1/kairn` |
| short mac-gcc16-O2 | 3 | 10.4%, 13.7%, 220.9% | `m2k/lat/ssum1_k4/kairn` |
| short mac-gcc16-O3 | 3 | 9.3%, 13.7%, 74.6% | `m2k/lat/sdot1_k4/kairn` |
| acc linux-clang-O2 | 3 | 0.1%, 0.4%, 0.9% | `m2c/tp/acc1part16/op` |
| acc linux-clang-O3 | 3 | 1.6%, 1.8%, 2.1% | `m2c/tp/acc2ball/kairn` |
| acc linux-gcc-O2 | 3 | 0.3%, 0.6%, 5.6% | `m2c/llc/acc1lanes/op` |
| acc linux-gcc-O3 | 3 | 0.2%, 0.4%, 3.1% | `m2a/llc/sum1/textbook` |
| bv linux-clang-O2 | 3 | 2.1%, 2.6%, 6.5% | `m2w/tp/axpy_1_4/op` |
| bv linux-clang-O3 | 3 | 1.7%, 2.4%, 119.2% | `m2w/tp/norm_1_64/op` |
| bv linux-gcc-O2 | 3 | 1.8%, 2.3%, 12.3% | `m2w/tp/sub_1_64/kairn` |
| bv linux-gcc-O3 | 3 | 2.3%, 2.7%, 4.7% | `m2w/tp/axpy_1_8/kairn` |
| entry linux-clang-O2 inline | 3 | 0.2%, 0.5%, 8.8% | `m2w/tp/axpy_1_16/op` |
| entry linux-clang-O2 nocheck | 3 | 0.8%, 1.5%, 5.9% | `m2w/tp/norm_1_16/seq` |
| entry linux-clang-O3 inline | 3 | 0.5%, 1.1%, 18.9% | `m2w/tp/scale_1_64/op` |
| entry linux-clang-O3 nocheck | 3 | 0.3%, 1.2%, 38.2% | `m2k/tp/sdot1_n2/op` |
| entry linux-gcc-O2 inline | 3 | 0.4%, 1.2%, 219.4% | `m2w/tp/norm_1_4/kairn` |
| entry linux-gcc-O2 nocheck | 3 | 0.3%, 1.2%, 219.4% | `m2w/tp/norm_1_4/kairn` |
| entry linux-gcc-O3 inline | 3 | 0.2%, 0.6%, 4.4% | `m2w/tp/norm_2_64/seq` |
| entry linux-gcc-O3 nocheck | 3 | 0.4%, 0.8%, 3.8% | `m2w/tp/add_2_16/op` |
| entry mac-appleclang-O2 inline | 3 | 13.8%, 17.8%, 98.2% | `m2k/lat/sdot1_n2/kairn` |
| entry mac-appleclang-O2 nocheck | 3 | 10.4%, 16.0%, 159.0% | `m2k/lat/sdot1_k1/kairn` |
| entry mac-appleclang-O3 inline | 3 | 14.8%, 18.9%, 190.4% | `m2k/lat/ssum2_n2/op` |
| entry mac-appleclang-O3 nocheck | 3 | 12.9%, 18.0%, 336.7% | `m2k/lat/ssum2_n1/op` |
| entry mac-gcc16-O2 inline | 3 | 12.8%, 18.0%, 371.0% | `m2k/lat/ssum1_k4/kairn` |
| entry mac-gcc16-O2 nocheck | 3 | 11.4%, 15.0%, 158.0% | `m2k/lat/sdot1_k2/op` |
| entry mac-gcc16-O3 inline | 3 | 6.4%, 10.9%, 117.2% | `m2k/lat/ssum1_k4/kairn` |
| entry mac-gcc16-O3 nocheck | 3 | 14.2%, 15.1%, 109.6% | `m2k/lat/ssum1_k2/kairn` |
| entryx linux-clang-O2 cold | 3 | 0.9%, 1.9%, 35.9% | `m2y/lat/sub_1_18/op` |
| entryx linux-clang-O2 inline | 3 | 0.3%, 2.5%, 49.1% | `m2x/lat/make_2_3/op` |
| entryx linux-clang-O2 nocheck | 3 | 0.9%, 1.7%, 58.2% | `m2x/lat/scale_1_13/op` |
| entryx linux-clang-O3 cold | 3 | 0.9%, 7.3%, 64.6% | `m2y/lat/scale_1_18/kairn` |
| entryx linux-clang-O3 inline | 3 | 1.0%, 2.0%, 66.2% | `m2x/lat/scale_1_80/op` |
| entryx linux-clang-O3 nocheck | 3 | 0.9%, 5.0%, 62.3% | `m2x/lat/scale_1_13/op` |
| entryx linux-gcc-O2 cold | 3 | 0.4%, 2.2%, 82.6% | `m2x/tp/addop_1_7/op` |
| entryx linux-gcc-O2 inline | 3 | 0.5%, 1.9%, 49.6% | `m2x/lat/make_2_3/kairn` |
| entryx linux-gcc-O2 nocheck | 3 | 0.4%, 1.6%, 48.7% | `m2y/lat/make_2_3/kairn` |
| entryx linux-gcc-O3 cold | 3 | 0.5%, 2.3%, 75.4% | `m2y/tp/scale_2_18/kairn` |
| entryx linux-gcc-O3 inline | 3 | 0.4%, 1.9%, 33.8% | `m2x/lat/make_2_80/kairn` |
| entryx linux-gcc-O3 nocheck | 3 | 1.6%, 2.6%, 30.1% | `m2x/lat/scale_1_18/kairn` |
| entryx mac-appleclang-O2 cold | 3 | 27.4%, 34.6%, 170.3% | `m2x/tp/make_1_3/op` |
| entryx mac-appleclang-O2 inline | 3 | 28.2%, 36.9%, 232.5% | `m2y/lat/half_2_18/kairn` |
| entryx mac-appleclang-O2 nocheck | 3 | 27.7%, 35.9%, 80.1% | `m2y/lat/half_1_80/kairn` |
| entryx mac-appleclang-O3 cold | 3 | 19.8%, 26.7%, 209.8% | `m2y/lat/addop_2_7/op` |
| entryx mac-appleclang-O3 inline | 3 | 27.7%, 37.5%, 85.5% | `m2y/tp/make_2_3/op` |
| entryx mac-appleclang-O3 nocheck | 3 | 27.3%, 35.0%, 63.1% | `m2x/lat/add_1_18/op` |
| entryx mac-gcc16-O2 cold | 3 | 17.1%, 27.6%, 42.9% | `m2y/lat/half_1_3/op` |
| entryx mac-gcc16-O2 inline | 3 | 15.2%, 25.1%, 93.0% | `m2x/lat/sub_1_3/op` |
| entryx mac-gcc16-O2 nocheck | 3 | 16.6%, 21.1%, 45.5% | `m2y/lat/sub_1_3/kairn` |
| entryx mac-gcc16-O3 cold | 3 | 36.7%, 46.7%, 102.4% | `m2x/lat/make_1_3/kairn` |
| entryx mac-gcc16-O3 inline | 3 | 20.2%, 21.3%, 69.7% | `m2x/lat/scale_1_7/kairn` |
| entryx mac-gcc16-O3 nocheck | 3 | 25.3%, 30.6%, 79.7% | `m2x/lat/make_2_3/kairn` |

#### Question 13: the functions on arrays

| The functions on arrays, double: ns per element | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, L1 | 0.229 to 0.236 (-O2), 0.215 to 0.231 (-O3) | 0.195 to 0.199 |
| `sum`, one limb, LLC | 0.229 to 0.233 | 0.228 to 0.235 |
| `sum`, one limb, memory | 0.434 to 0.453 | 0.422 to 0.434 |
| `sum`, two limbs, L1 | 2.6 to 2.67 | 2.58 to 2.62 |
| `sum`, two limbs, LLC | 2.56 to 2.62 | 2.54 to 2.61 |
| `sum`, two limbs, memory | 2.58 to 2.63 | 2.56 to 2.6 |
| `sum_fast`, two limbs, L1 | 1.67 to 1.71 | 1.66 to 1.75 (-O2), 1.66 to 1.72 (-O3) |
| `sum_fast`, two limbs, LLC | 1.66 to 1.68 | 1.64 to 1.66 |
| `sum_fast`, two limbs, memory | 1.71 to 1.73 | 1.68 to 1.72 |
| `dot`, one limb, L1 | 0.35 to 0.358 (-O2), 0.335 to 0.356 (-O3) | 0.323 to 0.33 |
| `dot`, one limb, LLC | 0.379 to 0.39 | 0.38 to 0.382 |
| `dot`, one limb, memory | 0.7 to 0.727 | 0.707 to 0.718 |
| `dot`, two limbs, L1 | 2.61 to 2.68 | 2.62 to 2.69 |
| `dot`, two limbs, LLC | 2.57 to 2.64 | 2.58 to 2.65 |
| `dot`, two limbs, memory | 2.85 to 2.9 | 2.79 to 2.89 |
| `add`, one limb, L1 | 0.214 to 0.219 (-O2), 0.214 to 0.226 (-O3) | 0.202 to 0.207 |
| `add`, one limb, LLC | 0.288 to 0.303 | 0.289 to 0.299 |
| `add`, one limb, memory | 1.02 to 1.05 | 1.02 to 1.03 |
| `add`, two limbs, L1 | 1.23 to 1.25 | 1.28 to 1.31 |
| `add`, two limbs, LLC | 1.23 to 1.27 | 1.25 to 1.27 |
| `add`, two limbs, memory | 2 to 2.1 (-O2), 2.04 to 2.07 (-O3) | 2.02 to 2.09 |
| `scale`, one limb, L1 | 0.177 to 0.181 (-O2), 0.153 to 0.183 (-O3) | 0.145 to 0.149 |
| `scale`, one limb, LLC | 0.197 to 0.205 | 0.197 to 0.204 |
| `scale`, one limb, memory | 0.777 to 0.794 | 0.785 to 0.791 |
| `scale`, two limbs, L1 | 0.505 to 0.522 | 0.499 to 0.512 |
| `scale`, two limbs, LLC | 0.5 to 0.516 | 0.501 to 0.513 |
| `scale`, two limbs, memory | 1.35 to 1.41 (-O2), 1.34 to 1.38 (-O3) | 1.33 to 1.39 |
| `axpy`, one limb, L1 | 0.217 to 0.228 | 0.209 to 0.214 |
| `axpy`, one limb, LLC | 0.286 to 0.3 (-O2), 0.287 to 0.288 (-O3) | 0.285 to 0.294 |
| `axpy`, one limb, memory | 1.06 to 1.09 | 1.07 to 1.08 |
| `axpy`, two limbs, a of T, L1 | 1.74 to 1.79 | 1.77 to 1.81 |
| `axpy`, two limbs, a of T, LLC | 1.74 to 1.8 | 1.74 to 1.79 |
| `axpy`, two limbs, a of T, memory | 2.15 to 2.25 | 2.16 to 2.27 (-O2), 2.15 to 2.21 (-O3) |
| `axpy`, two limbs, a of two limbs, L1 | 1.91 to 1.96 | 1.96 to 2.01 |
| `axpy`, two limbs, a of two limbs, LLC | 1.91 to 1.97 | 1.92 to 1.97 |
| `axpy`, two limbs, a of two limbs, memory | 2.22 to 2.33 (-O2), 2.28 to 2.35 (-O3) | 2.26 to 2.37 (-O2), 2.25 to 2.33 (-O3) |
| `norm_upper`, one limb, L1 | 0.164 to 0.184 (-O2), 0.177 to 0.179 (-O3) | 0.11 to 0.128 (-O2), 0.11 to 0.128 (-O3) |
| `norm_upper`, one limb, LLC | 0.153 to 0.156 | 0.121 to 0.126 |
| `norm_upper`, one limb, memory | 0.481 to 0.513 (-O2), 0.504 to 0.509 (-O3) | 0.487 to 0.49 |
| `norm_upper`, two limbs, L1 | 0.184 to 0.188 (-O2), 0.176 to 0.181 (-O3) | 0.113 to 0.129 (-O2), 0.113 to 0.129 (-O3) |
| `norm_upper`, two limbs, LLC | 0.152 to 0.156 | 0.121 to 0.126 (-O2), 0.118 to 0.126 (-O3) |
| `norm_upper`, two limbs, memory | 0.491 to 0.51 | 0.483 to 0.492 |
| a plain sum of T, one chain, L1 | 0.846 to 0.868 | 0.846 to 0.863 |
| a plain sum of T, one chain, LLC | 0.903 to 0.926 | 0.903 to 0.924 |
| a plain sum of T, one chain, memory | 0.92 to 0.945 | 0.924 to 0.939 |
| a plain dot product of T (FMA), one chain, L1 | 1.41 to 1.44 | 1.41 to 1.44 |
| a plain dot product of T (FMA), one chain, LLC | 1.5 to 1.54 | 1.5 to 1.54 |
| a plain dot product of T (FMA), one chain, memory | 1.54 to 1.58 | 1.55 to 1.58 |
| a plain `x + y` of T, L1 | 0.319 to 0.325 (-O2), 0.103 to 0.123 (-O3) | 0.121 to 0.131 (-O2), 0.12 to 0.121 (-O3) |
| a plain `x + y` of T, LLC | 0.392 to 0.403 (-O2), 0.261 to 0.298 (-O3) | 0.269 to 0.289 (-O2), 0.258 to 0.274 (-O3) |
| a plain `x + y` of T, memory | 1.13 to 1.17 (-O2), 1.11 to 1.13 (-O3) | 1.1 to 1.13 |
| a plain `x a` of T, L1 | 0.319 to 0.327 (-O2), 0.169 to 0.175 (-O3) | 0.0833 to 0.085 |
| a plain `x a` of T, LLC | 0.346 to 0.607 (-O2), 0.206 to 0.207 (-O3) | 0.207 to 0.212 (-O2), 0.173 to 0.208 (-O3) |
| a plain `x a` of T, memory | 0.833 to 0.928 (-O2), 0.836 to 0.837 (-O3) | 0.893 to 0.897 |
| a plain `a x + y` of T, L1 | 0.322 to 0.328 (-O2), 0.104 to 0.117 (-O3) | 0.121 to 0.124 |
| a plain `a x + y` of T, LLC | 0.395 to 0.406 (-O2), 0.257 to 0.26 (-O3) | 0.26 to 0.265 (-O2), 0.26 to 0.304 (-O3) |
| a plain `a x + y` of T, memory | 1.13 to 1.18 (-O2), 1.11 to 1.13 (-O3) | 1.09 to 1.12 |
| the plain sum of T in the lane order, L1 | 0.209 to 0.214 (-O2), 0.244 to 0.246 (-O3) | 0.18 to 0.183 |
| the plain sum of T in the lane order, LLC | 0.226 to 0.233 (-O2), 0.244 to 0.245 (-O3) | 0.226 to 0.232 |
| the plain sum of T in the lane order, memory | 0.459 to 0.464 (-O2), 0.635 to 0.642 (-O3) | 0.458 to 0.465 |
| the plain dot product of T in the lane order, L1 | 0.322 to 0.331 (-O2), 0.367 to 0.372 (-O3) | 0.3 to 0.308 |
| the plain dot product of T in the lane order, LLC | 0.378 to 0.388 | 0.377 to 0.386 |
| the plain dot product of T in the lane order, memory | 0.727 to 0.757 (-O2), 0.778 to 0.866 (-O3) | 0.75 to 0.759 |

| The functions on arrays over the same loop of T, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, over the plain sum in the same order, L1 | 1.09 to 1.13 (-O2), 0.87 to 0.95 (-O3) | 1.08 to 1.09 |
| `sum`, one limb, over the plain sum, one chain, L1 | 0.25 to 0.28 | 0.23 |
| `sum`, two limbs, over the plain sum of T in the same order, L1 | 12.5 (-O2), 10.6 to 10.9 (-O3) | 14.3 |
| `dot`, one limb, over the plain dot product in the same order, L1 | 1.06 to 1.09 (-O2), 0.91 to 0.97 (-O3) | 1.07 |
| `dot`, two limbs, over the plain dot product of T in the same order, L1 | 7.91 to 8.11 (-O2), 7.11 to 7.28 (-O3) | 8.70 to 8.73 |
| `add`, one limb, over `x + y` of T, L1 | 0.67 (-O2), 1.83 to 2.09 (-O3) | 1.55 to 1.69 (-O2), 1.67 to 1.68 (-O3) |
| `add`, two limbs, over `x + y` of T, L1 | 3.84 to 3.86 (-O2), 10.2 to 12.0 (-O3) | 9.8 to 10.7 (-O2), 10.6 to 10.7 (-O3) |
| `scale`, one limb, over `x a` of T, L1 | 0.56 (-O2), 0.91 to 1.05 (-O3) | 1.73 to 1.75 |
| `scale`, two limbs, over `x a` of T, L1 | 1.60 (-O2), 2.93 to 2.99 (-O3) | 5.99 to 6.05 |
| `axpy`, one limb, over `a x + y` of T, L1 | 0.67 to 0.68 (-O2), 1.95 to 2.10 (-O3) | 1.73 to 1.75 |
| `axpy`, two limbs, over `a x + y` of T, L1 | 5.40 to 5.45 (-O2), 15.0 to 16.8 (-O3) | 14.6 to 14.8 |
| `norm_upper`, one limb, over a plain largest magnitude, L1 | 0.27 to 0.56 (-O2), 0.54 to 0.55 (-O3) | 0.36 to 0.42 (-O2), 0.36 to 0.42 (-O3) |
| `sum`, one limb, over the plain sum in the same order, LLC | 1.00 to 1.01 (-O2), 0.94 (-O3) | 1.01 |
| `sum`, one limb, over the plain sum, one chain, LLC | 0.25 | 0.25 |
| `sum`, two limbs, over the plain sum of T in the same order, LLC | 11.3 (-O2), 10.5 (-O3) | 11.2 to 11.3 |
| `dot`, one limb, over the plain dot product in the same order, LLC | 1.00 to 1.01 | 0.99 to 1.01 |
| `dot`, two limbs, over the plain dot product of T in the same order, LLC | 6.78 to 6.82 | 6.83 to 6.88 |
| `add`, one limb, over `x + y` of T, LLC | 0.74 to 0.75 (-O2), 0.97 to 1.12 (-O3) | 1.01 to 1.11 (-O2), 1.06 to 1.13 (-O3) |
| `add`, two limbs, over `x + y` of T, LLC | 3.14 to 3.15 (-O2), 4.14 to 4.72 (-O3) | 4.34 to 4.75 (-O2), 4.57 to 4.86 (-O3) |
| `scale`, one limb, over `x a` of T, LLC | 0.33 to 0.58 (-O2), 0.97 to 0.98 (-O3) | 0.95 to 0.97 (-O2), 0.96 to 1.17 (-O3) |
| `scale`, two limbs, over `x a` of T, LLC | 0.83 to 1.46 (-O2), 2.42 (-O3) | 2.41 to 2.42 (-O2), 2.41 to 2.91 (-O3) |
| `axpy`, one limb, over `a x + y` of T, LLC | 0.72 to 0.74 (-O2), 1.11 to 1.12 (-O3) | 1.09 to 1.11 (-O2), 0.95 to 1.10 (-O3) |
| `axpy`, two limbs, over `a x + y` of T, LLC | 4.43 (-O2), 6.71 to 6.81 (-O3) | 6.66 to 6.76 (-O2), 5.74 to 6.72 (-O3) |
| `norm_upper`, one limb, over a plain largest magnitude, LLC | 0.50 to 0.51 | 0.40 to 0.42 |
| `sum`, one limb, over the plain sum in the same order, memory | 0.96 to 0.98 (-O2), 0.68 to 0.70 (-O3) | 0.91 to 0.94 |
| `sum`, one limb, over the plain sum, one chain, memory | 0.47 to 0.48 | 0.45 to 0.47 |
| `sum`, two limbs, over the plain sum of T in the same order, memory | 5.64 to 5.66 (-O2), 4.02 to 4.06 (-O3) | 5.52 to 5.62 |
| `dot`, one limb, over the plain dot product in the same order, memory | 0.96 to 0.97 (-O2), 0.84 to 0.91 (-O3) | 0.94 to 0.95 |
| `dot`, two limbs, over the plain dot product of T in the same order, memory | 3.83 to 3.91 (-O2), 3.30 to 3.67 (-O3) | 3.72 to 3.82 (-O2), 3.69 to 3.82 (-O3) |
| `add`, one limb, over `x + y` of T, memory | 0.90 to 0.92 | 0.91 to 0.93 |
| `add`, two limbs, over `x + y` of T, memory | 1.75 to 1.84 (-O2), 1.83 to 1.84 (-O3) | 1.81 to 1.84 (-O2), 1.79 to 1.90 (-O3) |
| `scale`, one limb, over `x a` of T, memory | 0.85 to 0.93 (-O2), 0.94 to 0.95 (-O3) | 0.88 to 0.89 |
| `scale`, two limbs, over `x a` of T, memory | 1.52 to 1.62 (-O2), 1.61 to 1.65 (-O3) | 1.50 to 1.55 (-O2), 1.50 to 1.51 (-O3) |
| `axpy`, one limb, over `a x + y` of T, memory | 0.93 to 0.97 | 0.95 to 0.99 |
| `axpy`, two limbs, over `a x + y` of T, memory | 1.88 to 1.96 (-O2), 1.96 to 2.01 (-O3) | 1.94 to 2.02 (-O2), 1.92 to 2.02 (-O3) |
| `norm_upper`, one limb, over a plain largest magnitude, memory | 0.72 to 0.75 | 0.74 to 0.76 |

| The functions on arrays over the textbook code, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum` of two limbs of one-limb data, sequential, over Sum2, L1 | 7.13 to 7.18 | 7.05 to 7.06 |
| `sum` of two limbs of one-limb data, default, over Sum2, L1 | 1.83 | 1.78 to 1.80 |
| `dot` of two limbs of one-limb data, sequential, over Dot2, L1 | 6.51 to 6.57 | 6.72 to 6.78 |
| `dot` of two limbs of one-limb data, default, over Dot2, L1 | 1.66 to 1.67 (-O2), 1.66 to 1.72 (-O3) | 1.71 to 1.73 |
| `sum`, two limbs, sequential, over double-word sums written out, L1 | 1.00 | 1.02 to 1.03 |
| `sum`, two limbs, default, over double-word sums written out, L1 | 0.25 to 0.26 | 0.26 |
| `sum_fast`, sequential, over SloppyDWPlusDW written out, L1 | 1.00 | 1.02 to 1.03 |
| `dot`, two limbs, sequential, over the double-word dot product written out, L1 | 1.00 to 1.01 | 1.01 to 1.02 |
| `dot`, two limbs, default, over the double-word dot product written out, L1 | 0.26 | 0.26 |
| `add`, two limbs, over AccurateDWPlusDW written out, L1 | 0.33 (-O2), 1.28 to 1.30 (-O3) | 1.32 to 1.35 |
| `scale`, two limbs, over DWTimesFP3 written out, L1 | 0.49 (-O2), 1.83 to 1.84 (-O3) | 2.05 to 2.06 |
| `axpy`, two limbs, a of T, over the same written out, L1 | 0.30 (-O2), 1.17 to 1.18 (-O3) | 1.20 |
| `axpy`, two limbs, a of two limbs, over the same written out, L1 | 0.29 (-O2), 1.19 to 1.21 (-O3) | 1.19 to 1.20 |
| `sum` of two limbs of one-limb data, sequential, over Sum2, LLC | 6.94 to 7.05 | 6.94 to 6.97 |
| `sum` of two limbs of one-limb data, default, over Sum2, LLC | 1.74 to 1.76 | 1.74 |
| `dot` of two limbs of one-limb data, sequential, over Dot2, LLC | 6.53 to 6.55 | 6.72 to 6.75 |
| `dot` of two limbs of one-limb data, default, over Dot2, LLC | 1.63 to 1.64 | 1.68 to 1.69 |
| `sum`, two limbs, sequential, over double-word sums written out, LLC | 0.99 to 1.00 | 1.02 |
| `sum`, two limbs, default, over double-word sums written out, LLC | 0.25 | 0.25 to 0.26 |
| `sum_fast`, sequential, over SloppyDWPlusDW written out, LLC | 0.99 to 1.00 | 1.02 |
| `dot`, two limbs, sequential, over the double-word dot product written out, LLC | 1.00 to 1.01 | 1.01 to 1.02 |
| `dot`, two limbs, default, over the double-word dot product written out, LLC | 0.25 | 0.25 to 0.26 |
| `add`, two limbs, over AccurateDWPlusDW written out, LLC | 0.33 (-O2), 1.28 to 1.29 (-O3) | 1.30 to 1.31 |
| `scale`, two limbs, over DWTimesFP3 written out, LLC | 0.48 to 0.49 (-O2), 1.29 to 1.30 (-O3) | 1.30 to 1.32 |
| `axpy`, two limbs, a of T, over the same written out, LLC | 0.30 (-O2), 1.17 to 1.18 (-O3) | 1.17 to 1.18 |
| `axpy`, two limbs, a of two limbs, over the same written out, LLC | 0.29 (-O2), 1.19 (-O3) | 1.16 |
| `sum` of two limbs of one-limb data, sequential, over Sum2, memory | 6.76 to 6.91 | 6.76 to 6.88 |
| `sum` of two limbs of one-limb data, default, over Sum2, memory | 1.70 to 1.75 (-O2), 1.72 to 1.75 (-O3) | 1.70 to 1.74 |
| `dot` of two limbs of one-limb data, sequential, over Dot2, memory | 5.83 to 6.29 (-O2), 5.67 to 6.24 (-O3) | 6.15 to 6.46 (-O2), 5.86 to 6.21 (-O3) |
| `dot` of two limbs of one-limb data, default, over Dot2, memory | 1.50 to 1.59 (-O2), 1.48 to 1.59 (-O3) | 1.60 to 1.63 (-O2), 1.53 to 1.60 (-O3) |
| `sum`, two limbs, sequential, over double-word sums written out, memory | 1.00 to 1.01 | 1.02 |
| `sum`, two limbs, default, over double-word sums written out, memory | 0.25 | 0.25 to 0.26 |
| `sum_fast`, sequential, over SloppyDWPlusDW written out, memory | 1.00 | 1.02 |
| `dot`, two limbs, sequential, over the double-word dot product written out, memory | 1.00 to 1.01 | 1.01 to 1.02 |
| `dot`, two limbs, default, over the double-word dot product written out, memory | 0.27 to 0.28 | 0.27 to 0.28 |
| `add`, two limbs, over AccurateDWPlusDW written out, memory | 0.49 to 0.50 (-O2), 1.02 to 1.03 (-O3) | 1.01 to 1.04 |
| `scale`, two limbs, over DWTimesFP3 written out, memory | 0.91 to 0.94 (-O2), 0.95 to 0.97 (-O3) | 0.94 to 0.98 |
| `axpy`, two limbs, a of T, over the same written out, memory | 0.36 (-O2), 1.07 (-O3) | 1.06 to 1.08 |
| `axpy`, two limbs, a of two limbs, over the same written out, memory | 0.33 to 0.34 (-O2), 1.07 to 1.09 (-O3) | 1.07 to 1.08 |

| kairn::sequential over the default order, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, L1 | 3.77 to 3.86 (-O2), 3.71 to 4.00 (-O3) | 4.40 to 4.43 |
| `sum`, two limbs, L1 | 3.83 to 3.93 | 3.93 to 3.94 |
| `sum_fast`, two limbs, L1 | 3.93 to 3.94 | 3.77 to 3.94 (-O2), 3.80 to 3.94 (-O3) |
| `dot`, one limb, L1 | 4.16 to 4.17 (-O2), 4.11 to 4.36 (-O3) | 4.42 to 4.45 |
| `dot`, two limbs, L1 | 3.84 to 3.94 | 3.91 to 3.95 |
| `add`, one limb, one lane over the default, L1 | 5.04 to 5.07 (-O2), 4.91 to 5.04 (-O3) | 1.25 to 1.26 |
| `add`, two limbs, one lane over the default, L1 | 4.34 to 4.36 | 0.99 to 1.00 |
| `scale`, two limbs, one lane over the default, L1 | 4.27 to 4.33 | 1.07 |
| `axpy`, one limb, one lane over the default, L1 | 4.99 to 5.04 (-O2), 4.86 to 4.97 (-O3) | 1.21 to 1.23 |
| `axpy`, two limbs, one lane over the default, L1 | 4.37 to 4.42 | 0.87 |
| `norm_upper`, two limbs, one lane over the default, L1 | 4.94 to 5.02 (-O2), 4.78 to 5.00 (-O3) | 4.05 to 5.02 (-O2), 4.04 to 4.89 (-O3) |
| `sum`, one limb, LLC | 3.95 to 3.98 | 3.95 to 3.97 |
| `sum`, two limbs, LLC | 3.97 to 4.00 | 3.98 to 4.00 |
| `sum_fast`, two limbs, LLC | 3.98 to 4.00 | 3.99 to 4.03 |
| `dot`, one limb, LLC | 3.94 to 3.97 | 3.96 to 4.03 |
| `dot`, two limbs, LLC | 3.95 to 4.00 | 3.97 to 3.99 |
| `add`, one limb, one lane over the default, LLC | 3.59 to 3.68 | 1.01 to 1.02 |
| `add`, two limbs, one lane over the default, LLC | 4.35 to 4.39 | 1.00 to 1.01 |
| `scale`, two limbs, one lane over the default, LLC | 4.26 to 4.28 | 1.08 to 1.09 |
| `axpy`, one limb, one lane over the default, LLC | 3.59 to 3.69 | 1.01 to 1.03 |
| `axpy`, two limbs, one lane over the default, LLC | 4.40 to 4.42 | 0.88 |
| `norm_upper`, two limbs, one lane over the default, LLC | 5.25 to 5.32 | 3.92 to 4.03 (-O2), 3.92 to 4.05 (-O3) |
| `sum`, one limb, memory | 2.10 to 2.15 | 2.17 to 2.26 (-O2), 2.15 to 2.19 (-O3) |
| `sum`, two limbs, memory | 3.95 to 3.99 | 3.98 to 4.00 |
| `sum_fast`, two limbs, memory | 3.89 to 3.93 | 3.90 to 3.93 |
| `dot`, one limb, memory | 2.23 to 2.26 | 2.19 to 2.23 (-O2), 2.18 to 2.25 (-O3) |
| `dot`, two limbs, memory | 3.62 to 3.66 | 3.63 to 3.72 |
| `add`, one limb, one lane over the default, memory | 1.22 to 1.29 (-O2), 1.19 to 1.22 (-O3) | 0.99 to 1.01 |
| `add`, two limbs, one lane over the default, memory | 2.75 to 2.80 | 0.99 to 1.01 |
| `scale`, two limbs, one lane over the default, memory | 1.64 to 1.68 | 1.00 |
| `axpy`, one limb, one lane over the default, memory | 1.23 to 1.26 | 1.02 to 1.04 |
| `axpy`, two limbs, one lane over the default, memory | 3.57 to 3.65 (-O2), 3.50 to 3.60 (-O3) | 0.94 to 0.97 |
| `norm_upper`, two limbs, one lane over the default, memory | 1.84 to 1.85 (-O2), 1.81 to 1.86 (-O3) | 1.52 to 1.53 |

| The product of polynomials, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `conv`, one limb, 16 coefficients: ns per term | 0.84 to 0.87 (-O2), 0.80 to 0.82 (-O3) | 0.77 to 0.78 (-O2), 0.69 to 0.70 (-O3) |
| `conv`, two limbs, 16 coefficients: ns per term | 9.54 to 9.75 (-O2), 9.44 to 9.46 (-O3) | 9.46 to 9.68 |
| `conv`, one limb, 16, over the plain loop of T (FMA) | 1.29 to 1.33 | 1.31 to 1.32 (-O2), 1.19 to 1.20 (-O3) |
| `conv`, two limbs, 16, over the plain loop of T (FMA) | 14.6 (-O2), 15.2 to 15.6 (-O3) | 16.2 to 16.4 |
| `conv`, two limbs, 16, over the double-word loop written out | 1.03 to 1.04 | 1.04 |
| `conv`, one limb, 64 coefficients: ns per term | 0.97 to 1.01 | 0.95 to 0.97 (-O2), 0.83 to 0.84 (-O3) |
| `conv`, two limbs, 64 coefficients: ns per term | 10.0 to 10.3 | 10.0 to 10.2 |
| `conv`, one limb, 64, over the plain loop of T (FMA) | 1.07 to 1.10 | 1.38 to 1.40 (-O2), 1.21 (-O3) |
| `conv`, two limbs, 64, over the plain loop of T (FMA) | 10.9 to 11.1 | 14.6 to 14.7 |
| `conv`, two limbs, 64, over the double-word loop written out | 1.00 to 1.01 | 1.02 |
| `conv`, one limb, 512 coefficients: ns per term | 1.38 to 1.41 | 1.35 to 1.40 |
| `conv`, two limbs, 512 coefficients: ns per term | 10.2 to 10.4 | 10.2 to 10.4 |
| `conv`, one limb, 512, over the plain loop of T (FMA) | 1.00 to 1.01 | 1.02 to 1.04 |
| `conv`, two limbs, 512, over the plain loop of T (FMA) | 7.38 to 7.42 | 7.69 to 7.75 |
| `conv`, two limbs, 512, over the double-word loop written out | 1.00 | 1.01 to 1.02 |

| The functions on arrays, float: ns per element | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, L1 | 0.119 to 0.122 (-O2), 0.116 to 0.123 (-O3) | 0.0967 to 0.0989 |
| `sum`, one limb, LLC | 0.114 to 0.117 | 0.114 to 0.116 |
| `sum`, one limb, memory | 0.215 to 0.225 | 0.213 to 0.217 |
| `sum`, two limbs, L1 | 1.4 to 1.43 | 1.39 to 1.42 |
| `sum`, two limbs, LLC | 1.28 to 1.31 | 1.27 to 1.3 |
| `sum`, two limbs, memory | 1.29 to 1.31 | 1.28 to 1.31 |
| `sum_fast`, two limbs, L1 | 0.892 to 0.919 | 0.885 to 0.908 |
| `sum_fast`, two limbs, LLC | 0.826 to 0.844 | 0.819 to 0.842 |
| `sum_fast`, two limbs, memory | 0.85 to 0.863 | 0.838 to 0.86 |
| `dot`, one limb, L1 | 0.162 to 0.17 | 0.159 to 0.163 |
| `dot`, one limb, LLC | 0.19 to 0.195 | 0.19 to 0.194 |
| `dot`, one limb, memory | 0.351 to 0.365 | 0.352 to 0.358 |
| `dot`, two limbs, L1 | 1.41 to 1.45 | 1.42 to 1.45 |
| `dot`, two limbs, LLC | 1.28 to 1.32 | 1.29 to 1.33 |
| `dot`, two limbs, memory | 1.41 to 1.46 | 1.39 to 1.47 (-O2), 1.39 to 1.41 (-O3) |
| `add`, one limb, L1 | 0.105 to 0.108 (-O2), 0.106 to 0.111 (-O3) | 0.105 to 0.109 |
| `add`, one limb, LLC | 0.143 to 0.151 (-O2), 0.144 to 0.147 (-O3) | 0.144 to 0.15 |
| `add`, one limb, memory | 0.508 to 0.523 | 0.509 to 0.518 |
| `add`, two limbs, L1 | 0.614 to 0.626 | 0.662 to 0.674 |
| `add`, two limbs, LLC | 0.615 to 0.635 | 0.626 to 0.642 |
| `add`, two limbs, memory | 1.01 to 1.05 (-O2), 1 to 1.04 (-O3) | 0.997 to 1.04 |
| `scale`, one limb, L1 | 0.0804 to 0.0955 (-O2), 0.0811 to 0.0973 (-O3) | 0.0809 to 0.0831 |
| `scale`, one limb, LLC | 0.1 to 0.102 | 0.0998 to 0.101 |
| `scale`, one limb, memory | 0.374 to 0.382 (-O2), 0.387 to 0.395 (-O3) | 0.393 to 0.399 |
| `scale`, two limbs, L1 | 0.251 to 0.258 | 0.249 to 0.255 |
| `scale`, two limbs, LLC | 0.251 to 0.258 | 0.251 to 0.257 |
| `scale`, two limbs, memory | 0.67 to 0.696 | 0.673 to 0.691 |
| `axpy`, one limb, L1 | 0.109 to 0.114 | 0.112 to 0.115 |
| `axpy`, one limb, LLC | 0.142 to 0.15 (-O2), 0.143 to 0.145 (-O3) | 0.143 to 0.147 |
| `axpy`, one limb, memory | 0.532 to 0.539 | 0.534 to 0.541 |
| `axpy`, two limbs, a of T, L1 | 0.875 to 0.897 | 0.91 to 0.93 |
| `axpy`, two limbs, a of T, LLC | 0.871 to 0.89 | 0.871 to 0.895 |
| `axpy`, two limbs, a of T, memory | 1.08 to 1.14 (-O2), 1.07 to 1.11 (-O3) | 1.06 to 1.11 |
| `axpy`, two limbs, a of two limbs, L1 | 0.962 to 0.978 | 1 to 1.02 |
| `axpy`, two limbs, a of two limbs, LLC | 0.952 to 0.983 | 0.965 to 0.978 |
| `axpy`, two limbs, a of two limbs, memory | 1.15 to 1.18 (-O2), 1.12 to 1.17 (-O3) | 1.12 to 1.18 (-O2), 1.11 to 1.16 (-O3) |
| `norm_upper`, one limb, L1 | 0.0909 to 0.0999 (-O2), 0.0888 to 0.0895 (-O3) | 0.0673 to 0.0721 (-O2), 0.0671 to 0.0714 (-O3) |
| `norm_upper`, one limb, LLC | 0.0757 to 0.0775 | 0.06 to 0.0636 (-O2), 0.0594 to 0.0629 (-O3) |
| `norm_upper`, one limb, memory | 0.238 to 0.246 (-O2), 0.253 to 0.254 (-O3) | 0.242 to 0.246 |
| `norm_upper`, two limbs, L1 | 0.118 to 0.121 (-O2), 0.1 to 0.106 (-O3) | 0.0697 to 0.0733 (-O2), 0.069 to 0.0736 (-O3) |
| `norm_upper`, two limbs, LLC | 0.0762 to 0.0779 | 0.0598 to 0.0633 (-O2), 0.0603 to 0.0633 (-O3) |
| `norm_upper`, two limbs, memory | 0.236 to 0.246 (-O2), 0.254 to 0.255 (-O3) | 0.23 to 0.244 (-O2), 0.226 to 0.246 (-O3) |
| a plain sum of T, one chain, L1 | 0.845 to 0.863 | 0.846 to 0.867 |
| a plain sum of T, one chain, LLC | 0.903 to 0.925 | 0.902 to 0.921 |
| a plain sum of T, one chain, memory | 0.923 to 0.947 | 0.918 to 0.937 |
| a plain dot product of T (FMA), one chain, L1 | 1.41 to 1.44 | 1.41 to 1.44 |
| a plain dot product of T (FMA), one chain, LLC | 1.5 to 1.53 | 1.5 to 1.54 |
| a plain dot product of T (FMA), one chain, memory | 1.51 to 1.56 | 1.51 to 1.56 |
| a plain `x + y` of T, L1 | 0.321 to 0.331 (-O2), 0.052 to 0.0593 (-O3) | 0.0646 to 0.0661 |
| a plain `x + y` of T, LLC | 0.344 to 0.351 (-O2), 0.13 to 0.137 (-O3) | 0.132 to 0.152 (-O2), 0.131 to 0.151 (-O3) |
| a plain `x + y` of T, memory | 0.73 to 0.753 (-O2), 0.553 to 0.558 (-O3) | 0.55 to 0.572 |
| a plain `x a` of T, L1 | 0.32 to 0.632 (-O2), 0.049 to 0.0895 (-O3) | 0.0448 to 0.0464 |
| a plain `x a` of T, LLC | 0.31 to 0.317 (-O2), 0.103 (-O3) | 0.104 to 0.106 (-O2), 0.0869 to 0.104 (-O3) |
| a plain `x a` of T, memory | 0.519 to 0.69 (-O2), 0.4 to 0.402 (-O3) | 0.444 to 0.449 |
| a plain `a x + y` of T, L1 | 0.323 to 0.332 (-O2), 0.0606 to 0.0837 (-O3) | 0.0642 to 0.0659 |
| a plain `a x + y` of T, LLC | 0.346 to 0.354 (-O2), 0.128 to 0.141 (-O3) | 0.129 to 0.133 |
| a plain `a x + y` of T, memory | 0.6 to 0.621 (-O2), 0.552 to 0.559 (-O3) | 0.548 to 0.569 |
| the plain sum of T in the lane order, L1 | 0.0943 to 0.11 (-O2), 0.203 to 0.204 (-O3) | 0.0824 to 0.0844 |
| the plain sum of T in the lane order, LLC | 0.113 to 0.116 (-O2), 0.199 (-O3) | 0.113 to 0.115 |
| the plain sum of T in the lane order, memory | 0.217 to 0.232 (-O2), 0.325 to 0.341 (-O3) | 0.215 to 0.219 (-O2), 0.218 to 0.226 (-O3) |
| the plain dot product of T in the lane order, L1 | 0.14 to 0.148 (-O2), 0.208 to 0.21 (-O3) | 0.134 to 0.137 |
| the plain dot product of T in the lane order, LLC | 0.189 to 0.193 | 0.189 to 0.193 |
| the plain dot product of T in the lane order, memory | 0.358 to 0.373 (-O2), 0.397 to 0.414 (-O3) | 0.358 to 0.377 (-O2), 0.359 to 0.378 (-O3) |

| The functions on arrays over the same loop of T, float | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, over the plain sum in the same order, L1 | 1.11 to 1.27 (-O2), 0.57 to 0.60 (-O3) | 1.17 to 1.18 |
| `sum`, one limb, over the plain sum, one chain, L1 | 0.14 to 0.15 | 0.11 |
| `sum`, two limbs, over the plain sum of T in the same order, L1 | 13.0 to 15.0 (-O2), 6.86 to 6.87 (-O3) | 16.8 to 16.9 |
| `dot`, one limb, over the plain dot product in the same order, L1 | 1.10 to 1.19 (-O2), 0.78 to 0.79 (-O3) | 1.19 |
| `dot`, two limbs, over the plain dot product of T in the same order, L1 | 9.6 to 10.1 (-O2), 6.71 to 6.75 (-O3) | 10.5 to 10.6 |
| `add`, one limb, over `x + y` of T, L1 | 0.32 to 0.33 (-O2), 1.85 to 2.04 (-O3) | 1.62 to 1.65 |
| `add`, two limbs, over `x + y` of T, L1 | 1.89 to 1.92 (-O2), 10.4 to 11.8 (-O3) | 10.2 to 10.3 |
| `scale`, one limb, over `x a` of T, L1 | 0.13 to 0.30 (-O2), 1.09 to 1.66 (-O3) | 1.78 to 1.82 |
| `scale`, two limbs, over `x a` of T, L1 | 0.41 to 0.79 (-O2), 2.85 to 5.14 (-O3) | 5.49 to 5.59 |
| `axpy`, one limb, over `a x + y` of T, L1 | 0.33 to 0.34 (-O2), 1.31 to 1.87 (-O3) | 1.72 to 1.76 |
| `axpy`, two limbs, over `a x + y` of T, L1 | 2.69 to 2.73 (-O2), 10.5 to 14.4 (-O3) | 14.0 to 14.2 |
| `norm_upper`, one limb, over a plain largest magnitude, L1 | 0.16 to 0.28 (-O2), 0.14 to 0.27 (-O3) | 0.22 to 0.23 |
| `sum`, one limb, over the plain sum in the same order, LLC | 1.01 (-O2), 0.57 to 0.58 (-O3) | 1.01 |
| `sum`, one limb, over the plain sum, one chain, LLC | 0.13 | 0.12 to 0.13 |
| `sum`, two limbs, over the plain sum of T in the same order, LLC | 11.2 to 11.3 (-O2), 6.44 to 6.45 (-O3) | 11.2 to 11.3 |
| `dot`, one limb, over the plain dot product in the same order, LLC | 1.00 to 1.01 | 1.00 to 1.01 |
| `dot`, two limbs, over the plain dot product of T in the same order, LLC | 6.78 to 6.85 | 6.83 to 6.88 |
| `add`, one limb, over `x + y` of T, LLC | 0.42 to 0.43 (-O2), 1.05 to 1.13 (-O3) | 0.96 to 1.11 (-O2), 0.96 to 1.10 (-O3) |
| `add`, two limbs, over `x + y` of T, LLC | 1.78 to 1.81 (-O2), 4.50 to 4.72 (-O3) | 4.15 to 4.76 (-O2), 4.14 to 4.81 (-O3) |
| `scale`, one limb, over `x a` of T, LLC | 0.32 (-O2), 0.97 to 0.98 (-O3) | 0.95 to 0.96 (-O2), 0.96 to 1.16 (-O3) |
| `scale`, two limbs, over `x a` of T, LLC | 0.81 (-O2), 2.43 (-O3) | 2.40 to 2.42 (-O2), 2.42 to 2.89 (-O3) |
| `axpy`, one limb, over `a x + y` of T, LLC | 0.41 to 0.42 (-O2), 1.03 to 1.13 (-O3) | 1.09 to 1.11 |
| `axpy`, two limbs, over `a x + y` of T, LLC | 2.51 to 2.52 (-O2), 6.23 to 6.80 (-O3) | 6.59 to 6.78 |
| `norm_upper`, one limb, over a plain largest magnitude, LLC | 0.13 to 0.25 (-O2), 0.25 (-O3) | 0.20 to 0.21 |
| `sum`, one limb, over the plain sum in the same order, memory | 0.96 to 1.03 (-O2), 0.65 to 0.67 (-O3) | 0.96 to 0.99 |
| `sum`, one limb, over the plain sum, one chain, memory | 0.23 to 0.24 | 0.23 |
| `sum`, two limbs, over the plain sum of T in the same order, memory | 5.67 to 5.94 (-O2), 3.78 to 3.98 (-O3) | 5.88 to 6.09 (-O2), 5.67 to 5.90 (-O3) |
| `dot`, one limb, over the plain dot product in the same order, memory | 0.97 to 0.98 (-O2), 0.87 to 0.90 (-O3) | 0.93 to 0.99 (-O2), 0.95 to 1.00 (-O3) |
| `dot`, two limbs, over the plain dot product of T in the same order, memory | 3.89 to 3.97 (-O2), 3.46 to 3.55 (-O3) | 3.73 to 4.06 (-O2), 3.73 to 3.90 (-O3) |
| `add`, one limb, over `x + y` of T, memory | 0.69 to 0.70 (-O2), 0.92 (-O3) | 0.90 to 0.93 |
| `add`, two limbs, over `x + y` of T, memory | 1.37 to 1.40 (-O2), 1.79 to 1.87 (-O3) | 1.79 to 1.89 (-O2), 1.78 to 1.86 (-O3) |
| `scale`, one limb, over `x a` of T, memory | 0.54 to 0.73 (-O2), 0.97 to 0.98 (-O3) | 0.88 to 0.89 |
| `scale`, two limbs, over `x a` of T, memory | 0.99 to 1.31 (-O2), 1.68 to 1.70 (-O3) | 1.51 to 1.54 |
| `axpy`, one limb, over `a x + y` of T, memory | 0.87 to 0.89 (-O2), 0.96 to 0.97 (-O3) | 0.95 to 0.98 |
| `axpy`, two limbs, over `a x + y` of T, memory | 1.80 to 1.84 (-O2), 1.91 to 2.01 (-O3) | 1.90 to 2.01 (-O2), 1.91 to 2.00 (-O3) |
| `norm_upper`, one limb, over a plain largest magnitude, memory | 0.51 to 0.53 (-O2), 0.36 to 0.37 (-O3) | 0.49 to 0.53 |

| The functions on arrays over the textbook code, float | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum` of two limbs of one-limb data, sequential, over Sum2, L1 | 7.08 to 7.11 | 7.06 to 7.11 |
| `sum` of two limbs of one-limb data, default, over Sum2, L1 | 0.97 to 0.98 | 0.96 to 0.97 |
| `dot` of two limbs of one-limb data, sequential, over Dot2, L1 | 6.58 to 6.68 | 6.69 to 6.77 |
| `dot` of two limbs of one-limb data, default, over Dot2, L1 | 0.91 to 0.93 | 0.93 |
| `sum`, two limbs, sequential, over double-word sums written out, L1 | 1.00 | 1.02 to 1.03 |
| `sum`, two limbs, default, over double-word sums written out, L1 | 0.14 | 0.14 |
| `sum_fast`, sequential, over SloppyDWPlusDW written out, L1 | 1.00 | 1.02 to 1.03 |
| `dot`, two limbs, sequential, over the double-word dot product written out, L1 | 1.00 | 1.01 to 1.02 |
| `dot`, two limbs, default, over the double-word dot product written out, L1 | 0.14 | 0.14 |
| `add`, two limbs, over AccurateDWPlusDW written out, L1 | 0.16 (-O2), 1.28 to 1.29 (-O3) | 1.39 to 1.41 |
| `scale`, two limbs, over DWTimesFP3 written out, L1 | 0.24 (-O2), 1.88 to 1.90 (-O3) | 1.84 to 2.00 (-O2), 1.99 to 2.01 (-O3) |
| `axpy`, two limbs, a of T, over the same written out, L1 | 0.15 (-O2), 1.18 to 1.19 (-O3) | 1.23 to 1.24 |
| `axpy`, two limbs, a of two limbs, over the same written out, L1 | 0.15 (-O2), 1.19 to 1.20 (-O3) | 1.21 to 1.22 |
| `sum` of two limbs of one-limb data, sequential, over Sum2, LLC | 6.98 to 7.06 | 6.95 to 7.12 |
| `sum` of two limbs of one-limb data, default, over Sum2, LLC | 0.87 to 0.89 | 0.87 to 0.89 |
| `dot` of two limbs of one-limb data, sequential, over Dot2, LLC | 6.66 to 6.71 | 6.72 to 6.75 |
| `dot` of two limbs of one-limb data, default, over Dot2, LLC | 0.84 | 0.84 to 0.85 |
| `sum`, two limbs, sequential, over double-word sums written out, LLC | 1.00 | 1.02 |
| `sum`, two limbs, default, over double-word sums written out, LLC | 0.13 | 0.13 |
| `sum_fast`, sequential, over SloppyDWPlusDW written out, LLC | 1.00 | 1.02 to 1.03 |
| `dot`, two limbs, sequential, over the double-word dot product written out, LLC | 1.00 | 1.01 to 1.02 |
| `dot`, two limbs, default, over the double-word dot product written out, LLC | 0.13 | 0.13 |
| `add`, two limbs, over AccurateDWPlusDW written out, LLC | 0.17 (-O2), 1.28 to 1.29 (-O3) | 1.31 to 1.32 |
| `scale`, two limbs, over DWTimesFP3 written out, LLC | 0.24 (-O2), 1.30 to 1.31 (-O3) | 1.30 to 1.32 |
| `axpy`, two limbs, a of T, over the same written out, LLC | 0.15 (-O2), 1.17 to 1.18 (-O3) | 1.17 to 1.19 |
| `axpy`, two limbs, a of two limbs, over the same written out, LLC | 0.15 (-O2), 1.19 (-O3) | 1.16 to 1.17 |
| `sum` of two limbs of one-limb data, sequential, over Sum2, memory | 6.87 to 6.99 | 6.88 to 7.03 (-O2), 6.80 to 6.88 (-O3) |
| `sum` of two limbs of one-limb data, default, over Sum2, memory | 0.87 to 0.88 | 0.86 to 0.89 |
| `dot` of two limbs of one-limb data, sequential, over Dot2, memory | 6.31 to 6.51 (-O2), 6.33 to 6.45 (-O3) | 6.44 to 6.59 (-O2), 6.30 to 6.57 (-O3) |
| `dot` of two limbs of one-limb data, default, over Dot2, memory | 0.82 to 0.84 | 0.83 to 0.84 |
| `sum`, two limbs, sequential, over double-word sums written out, memory | 1.00 | 1.02 |
| `sum`, two limbs, default, over double-word sums written out, memory | 0.13 | 0.13 |
| `sum_fast`, sequential, over SloppyDWPlusDW written out, memory | 1.00 | 1.02 |
| `dot`, two limbs, sequential, over the double-word dot product written out, memory | 1.00 | 1.01 |
| `dot`, two limbs, default, over the double-word dot product written out, memory | 0.14 | 0.14 |
| `add`, two limbs, over AccurateDWPlusDW written out, memory | 0.26 (-O2), 1.00 to 1.03 (-O3) | 1.01 to 1.04 |
| `scale`, two limbs, over DWTimesFP3 written out, memory | 0.57 to 0.58 (-O2), 0.95 to 0.96 (-O3) | 0.96 to 0.97 |
| `axpy`, two limbs, a of T, over the same written out, memory | 0.18 to 0.19 (-O2), 1.06 to 1.08 (-O3) | 1.05 to 1.07 |
| `axpy`, two limbs, a of two limbs, over the same written out, memory | 0.17 to 0.18 (-O2), 1.09 (-O3) | 1.07 to 1.08 |

| kairn::sequential over the default order, float | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `sum`, one limb, L1 | 7.38 to 7.42 (-O2), 7.00 to 7.40 (-O3) | 8.87 to 8.93 |
| `sum`, two limbs, L1 | 7.21 to 7.31 | 7.29 to 7.33 |
| `sum_fast`, two limbs, L1 | 7.30 to 7.38 | 7.34 to 7.37 |
| `dot`, one limb, L1 | 8.76 to 8.97 | 8.95 to 9.02 |
| `dot`, two limbs, L1 | 7.20 to 7.26 | 7.24 to 7.33 |
| `add`, one limb, one lane over the default, L1 | 10.4 to 10.5 (-O2), 10.1 to 10.4 (-O3) | 1.24 to 1.26 |
| `add`, two limbs, one lane over the default, L1 | 8.69 to 8.84 | 0.99 to 1.00 |
| `scale`, two limbs, one lane over the default, L1 | 8.07 to 8.11 | 1.09 to 1.10 |
| `axpy`, one limb, one lane over the default, L1 | 10.3 (-O2), 9.8 to 10.3 (-O3) | 1.21 to 1.22 |
| `axpy`, two limbs, one lane over the default, L1 | 8.44 to 8.51 | 0.86 to 0.87 |
| `norm_upper`, two limbs, one lane over the default, L1 | 8.11 to 8.42 (-O2), 8.68 to 9.38 (-O3) | 7.01 to 8.52 (-O2), 7.02 to 8.52 (-O3) |
| `sum`, one limb, LLC | 7.88 to 7.93 | 7.91 to 7.94 |
| `sum`, two limbs, LLC | 7.97 to 8.01 | 7.98 to 8.01 |
| `sum_fast`, two limbs, LLC | 7.96 to 8.03 | 7.97 to 8.01 |
| `dot`, one limb, LLC | 7.92 to 7.93 | 7.92 to 7.95 |
| `dot`, two limbs, LLC | 7.90 to 7.96 | 7.91 to 7.97 |
| `add`, one limb, one lane over the default, LLC | 7.16 to 7.36 | 1.00 to 1.02 |
| `add`, two limbs, one lane over the default, LLC | 8.65 to 8.76 | 1.00 to 1.01 |
| `scale`, two limbs, one lane over the default, LLC | 7.92 to 7.99 | 1.08 to 1.09 |
| `axpy`, one limb, one lane over the default, LLC | 7.09 to 7.37 (-O2), 7.19 to 7.29 (-O3) | 1.01 to 1.02 |
| `axpy`, two limbs, one lane over the default, LLC | 8.45 to 8.50 | 0.88 to 0.89 |
| `norm_upper`, two limbs, one lane over the default, LLC | 10.5 to 10.6 | 7.72 to 8.19 (-O2), 7.65 to 8.22 (-O3) |
| `sum`, one limb, memory | 4.20 to 4.30 (-O2), 4.14 to 4.29 (-O3) | 4.34 to 4.44 (-O2), 4.30 to 4.33 (-O3) |
| `sum`, two limbs, memory | 7.97 to 8.00 | 7.95 to 7.98 |
| `sum_fast`, two limbs, memory | 7.75 to 7.85 | 7.80 to 7.83 |
| `dot`, one limb, memory | 4.25 to 4.34 | 4.29 to 4.38 (-O2), 4.24 to 4.29 (-O3) |
| `dot`, two limbs, memory | 7.16 to 7.30 | 7.24 to 7.45 (-O2), 7.36 to 7.48 (-O3) |
| `add`, one limb, one lane over the default, memory | 2.03 to 2.13 (-O2), 2.06 to 2.13 (-O3) | 0.99 to 1.02 |
| `add`, two limbs, one lane over the default, memory | 5.37 to 5.47 (-O2), 5.28 to 5.49 (-O3) | 0.99 to 1.01 |
| `scale`, two limbs, one lane over the default, memory | 2.99 to 3.04 | 0.99 to 1.00 |
| `axpy`, one limb, one lane over the default, memory | 2.12 to 2.18 | 1.02 to 1.04 |
| `axpy`, two limbs, one lane over the default, memory | 6.79 to 6.89 (-O2), 6.76 to 7.01 (-O3) | 0.95 to 0.97 |
| `norm_upper`, two limbs, one lane over the default, memory | 3.61 to 3.80 (-O2), 3.43 to 3.47 (-O3) | 2.40 to 2.47 (-O2), 2.45 to 2.48 (-O3) |

| The product of polynomials, float | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `conv`, one limb, 16 coefficients: ns per term | 0.83 to 0.88 | 0.76 to 0.78 (-O2), 0.69 to 0.70 (-O3) |
| `conv`, two limbs, 16 coefficients: ns per term | 9.34 to 9.59 | 9.45 to 9.59 |
| `conv`, one limb, 16, over the plain loop of T (FMA) | 1.02 to 1.05 (-O2), 1.36 to 1.42 (-O3) | 1.31 to 1.32 (-O2), 1.19 to 1.20 (-O3) |
| `conv`, two limbs, 16, over the plain loop of T (FMA) | 11.5 to 11.7 (-O2), 15.2 to 15.4 (-O3) | 16.1 to 16.4 |
| `conv`, two limbs, 16, over the double-word loop written out | 1.02 to 1.03 | 1.03 to 1.04 |
| `conv`, one limb, 64 coefficients: ns per term | 0.97 to 1.01 | 0.95 to 0.97 (-O2), 0.83 to 0.84 (-O3) |
| `conv`, two limbs, 64 coefficients: ns per term | 10.0 to 10.2 | 10.0 to 10.3 |
| `conv`, one limb, 64, over the plain loop of T (FMA) | 0.95 to 0.96 (-O2), 0.98 to 1.10 (-O3) | 1.38 (-O2), 1.21 to 1.22 (-O3) |
| `conv`, two limbs, 64, over the plain loop of T (FMA) | 9.76 to 9.88 (-O2), 9.7 to 11.0 (-O3) | 14.6 to 14.7 |
| `conv`, two limbs, 64, over the double-word loop written out | 1.00 to 1.01 | 1.02 |
| `conv`, one limb, 512 coefficients: ns per term | 1.38 to 1.41 | 1.38 to 1.41 (-O2), 1.35 (-O3) |
| `conv`, two limbs, 512 coefficients: ns per term | 10.2 to 10.3 | 10.2 to 10.5 |
| `conv`, one limb, 512, over the plain loop of T (FMA) | 0.99 to 1.01 | 1.02 to 1.05 |
| `conv`, two limbs, 512, over the plain loop of T (FMA) | 7.25 to 7.41 | 7.72 to 7.76 |
| `conv`, two limbs, 512, over the double-word loop written out | 0.99 to 1.00 | 1.01 to 1.02 |

#### Question 14: short arrays and the check at entry

| Short arrays, independent calls: ns per call | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 1.42 to 1.62 (-O2), 1.11 to 1.3 (-O3) | 1.49 to 1.61 (-O2), 1.42 to 1.61 (-O3) | 6.91 to 7.22 | 6.95 to 7.27 |
| `sum`, one limb, n = 2 | 1.44 to 1.61 (-O2), 1.13 to 1.3 (-O3) | 1.43 to 1.62 (-O2), 1.46 to 1.63 (-O3) | 7.21 to 7.24 | 6.93 to 7.26 |
| `sum`, one limb, n = 4 | 2.06 to 2.25 (-O2), 1.15 to 1.3 (-O3) | 1.86 to 1.94 (-O2), 1.82 to 1.93 (-O3) | 7.21 to 7.26 | 6.99 to 7.25 |
| `sum`, one limb, n = 8 | 2.46 to 2.57 (-O2), 1.7 to 1.93 (-O3) | 2.88 to 3.2 (-O2), 2.69 to 2.89 (-O3) | 7.21 to 7.56 | 7.63 to 7.68 (-O2), 7.23 to 7.26 (-O3) |
| `sum`, one limb, n = 16 | 3.66 to 3.84 (-O2), 3.11 to 3.53 (-O3) | 3.94 to 4.47 (-O2), 4.12 to 4.16 (-O3) | 7.71 to 7.83 | 7.53 to 7.68 |
| `sum`, one limb, n = 64 | 10.7 to 12.1 (-O2), 10.2 to 11.5 (-O3) | 11.2 to 12.8 (-O2), 11.9 to 12.4 (-O3) | 14.4 (-O2), 13 to 13.1 (-O3) | 8.82 to 8.88 (-O2), 13.3 (-O3) |
| `sum`, one limb, n = 1024 | 363 to 391 (-O2), 343 to 390 (-O3) | 340 to 382 (-O2), 364 to 385 (-O3) | 223 to 226 | 213 to 219 |
| `sum`, two limbs, n = 1 | 4.56 to 4.62 (-O2), 4.24 to 4.62 (-O3) | 2.82 to 3.21 (-O2), 1.96 to 2.19 (-O3) | 32 to 32.2 (-O2), 8.11 to 8.12 (-O3) | 30.4 to 30.7 |
| `sum`, two limbs, n = 2 | 4.52 to 5.14 (-O2), 4.75 to 5.1 (-O3) | 4.06 to 4.58 (-O2), 4.67 to 4.88 (-O3) | 41.5 to 41.8 (-O2), 12.2 to 12.3 (-O3) | 40.9 to 41.4 |
| `sum`, two limbs, n = 4 | 7.57 to 8.48 (-O2), 7.87 to 8.51 (-O3) | 7.11 to 7.75 (-O2), 7.89 to 8.25 (-O3) | 33 to 33.2 (-O2), 29.5 (-O3) | 31.6 to 31.9 |
| `sum`, two limbs, n = 8 | 14.4 to 16.4 (-O2), 15.1 to 16.4 (-O3) | 13.9 to 15.5 (-O2), 15.3 to 16 (-O3) | 43.4 to 43.7 (-O2), 39.2 (-O3) | 41.9 to 42.3 |
| `sum`, two limbs, n = 16 | 33.8 to 38.4 (-O2), 33.9 to 38.4 (-O3) | 35 to 36.6 (-O2), 33.9 to 37.5 (-O3) | 63.6 to 63.9 (-O2), 59.5 to 59.6 (-O3) | 62.2 to 62.7 |
| `sum`, two limbs, n = 64 | 220 to 245 (-O2), 225 to 245 (-O3) | 216 to 244 (-O2), 218 to 246 (-O3) | 182 to 188 | 184 to 185 |
| `sum`, two limbs, n = 1024 | 4274 to 4851 (-O2), 4377 to 4641 (-O3) | 4354 to 4842 (-O2), 4293 to 4876 (-O3) | 2632 to 2655 | 2615 to 2631 |
| `dot`, one limb, n = 1 | 1.42 to 1.61 (-O2), 1.17 to 1.3 (-O3) | 1.5 to 1.62 (-O2), 1.52 to 1.62 (-O3) | 6.91 to 7.23 | 6.92 to 7.26 |
| `dot`, one limb, n = 2 | 1.42 to 1.61 (-O2), 1.23 to 1.3 (-O3) | 1.47 to 1.63 (-O2), 1.43 to 1.62 (-O3) | 7.22 to 7.53 | 7.24 to 7.56 |
| `dot`, one limb, n = 4 | 1.44 to 1.66 (-O2), 1.17 to 1.31 (-O3) | 1.76 to 1.94 (-O2), 1.86 to 1.95 (-O3) | 7.24 to 7.52 | 7.52 to 7.53 (-O2), 6.93 to 6.95 (-O3) |
| `dot`, one limb, n = 8 | 2.46 to 2.57 | 2.79 to 3.21 (-O2), 2.87 to 3.21 (-O3) | 7.52 to 7.58 | 7.21 to 7.57 |
| `dot`, one limb, n = 16 | 3.54 to 3.85 (-O2), 3.68 to 3.84 (-O3) | 3.94 to 4.48 (-O2), 4.01 to 4.48 (-O3) | 7.82 to 8.13 | 7.54 to 7.9 |
| `dot`, one limb, n = 64 | 15.5 to 16.2 (-O2), 14.6 to 16.1 (-O3) | 14.8 to 16.1 (-O2), 15.3 to 16 (-O3) | 16.4 to 16.8 | 15 to 15.2 (-O2), 15.8 to 15.9 (-O3) |
| `dot`, one limb, n = 1024 | 480 to 572 (-O2), 523 to 572 (-O3) | 506 to 575 (-O2), 550 to 576 (-O3) | 365 to 368 | 362 to 365 |
| `dot`, two limbs, n = 1 | 4.67 to 5.31 (-O2), 4.79 to 5.31 (-O3) | 3.52 to 3.84 (-O2), 3.02 to 3.28 (-O3) | 34.2 to 34.5 (-O2), 9.16 (-O3) | 30.4 to 30.6 |
| `dot`, two limbs, n = 2 | 6.2 to 6.93 (-O2), 6.34 to 6.99 (-O3) | 5.86 to 6.42 (-O2), 6.23 to 6.97 (-O3) | 43 to 43.7 (-O2), 16.3 to 16.4 (-O3) | 40.5 to 40.8 |
| `dot`, two limbs, n = 4 | 9.97 to 11.3 (-O2), 10.2 to 11.4 (-O3) | 10.3 to 10.7 (-O2), 9.86 to 11 (-O3) | 38.2 to 38.5 (-O2), 33.7 to 33.9 (-O3) | 36.8 to 37.1 |
| `dot`, two limbs, n = 8 | 19.3 to 21.4 (-O2), 19 to 21.3 (-O3) | 19.4 to 20.3 (-O2), 18.5 to 20.7 (-O3) | 48.3 to 48.9 (-O2), 44.8 to 44.9 (-O3) | 47.1 to 47.4 |
| `dot`, two limbs, n = 16 | 43.4 to 45.4 (-O2), 40.1 to 45.4 (-O3) | 38.7 to 43.9 (-O2), 40.2 to 44.5 (-O3) | 68.9 to 69.5 (-O2), 65.1 to 65.2 (-O3) | 67.2 to 67.7 |
| `dot`, two limbs, n = 64 | 243 to 254 (-O2), 224 to 254 (-O3) | 222 to 253 (-O2), 241 to 254 (-O3) | 187 to 192 | 191 to 193 |
| `dot`, two limbs, n = 1024 | 4685 to 4773 (-O2), 4201 to 4773 (-O3) | 4458 to 4785 (-O2), 4398 to 4784 (-O3) | 2629 to 2645 | 2655 to 2664 |

| Short arrays, dependent calls: ns per call | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 1.69 to 1.7 (-O2), 1.24 to 1.41 (-O3) | 1.85 to 1.93 (-O2), 1.7 to 1.93 (-O3) | 7.21 to 7.26 | 7.49 to 7.55 (-O2), 8.02 to 8.04 (-O3) |
| `sum`, one limb, n = 2 | 1.62 to 1.7 (-O2), 1.27 to 1.49 (-O3) | 1.72 to 1.94 (-O2), 1.86 to 1.93 (-O3) | 7.51 to 7.58 | 8.46 to 8.52 (-O2), 8.94 to 8.97 (-O3) |
| `sum`, one limb, n = 4 | 10.4 to 10.9 (-O2), 9.66 to 10.8 (-O3) | 7.2 to 8.18 (-O2), 7.71 to 8.24 (-O3) | 10 to 10.3 | 11.3 to 11.9 |
| `sum`, one limb, n = 8 | 12.4 to 13 (-O2), 11.4 to 13 (-O3) | 9.79 to 10.2 (-O2), 9.39 to 10.1 (-O3) | 11.1 to 11.3 | 12.2 to 12.8 |
| `sum`, one limb, n = 16 | 15.7 to 16.4 (-O2), 14.4 to 16.4 (-O3) | 12.7 to 14 (-O2), 12.3 to 14 (-O3) | 12.8 to 12.9 | 14 to 14.1 |
| `sum`, one limb, n = 64 | 34.5 to 37.3 (-O2), 33 to 37.6 (-O3) | 30.7 to 34.9 (-O2), 33.7 to 35.2 (-O3) | 23.6 to 23.8 | 24.8 to 25 |
| `sum`, one limb, n = 1024 | 439 (-O2), 408 to 463 (-O3) | 431 to 462 (-O2), 458 to 462 (-O3) | 240 to 241 | 241 to 243 |
| `sum`, two limbs, n = 1 | 21.3 to 22.3 (-O2), 19.6 to 22.3 (-O3) | 9.28 to 9.62 (-O2), 9.17 to 9.69 (-O3) | 32.9 to 33.3 (-O2), 15.7 (-O3) | 31.9 to 32.2 |
| `sum`, two limbs, n = 2 | 9.89 to 12.4 (-O2), 10.1 to 10.8 (-O3) | 14.3 to 14.7 (-O2), 13.1 to 13.7 (-O3) | 43.5 to 43.8 (-O2), 25.5 to 25.6 (-O3) | 42.2 to 42.5 |
| `sum`, two limbs, n = 4 | 37.4 to 42.5 (-O2), 39.9 to 42.5 (-O3) | 35.1 to 38.7 (-O2), 32.1 to 34.5 (-O3) | 52.1 to 52.5 (-O2), 47.3 (-O3) | 49.6 to 50.1 |
| `sum`, two limbs, n = 8 | 53.9 to 61.3 (-O2), 56.5 to 61.3 (-O3) | 51.6 to 57.7 (-O2), 48.6 to 52.8 (-O3) | 62.2 to 62.6 (-O2), 57.4 to 57.5 (-O3) | 59.7 to 60.2 |
| `sum`, two limbs, n = 16 | 87.1 to 99.1 (-O2), 88.7 to 99.1 (-O3) | 88.3 to 95.4 (-O2), 87 to 90.8 (-O3) | 82.7 to 83.3 (-O2), 77.5 to 77.8 (-O3) | 80.1 to 80.8 |
| `sum`, two limbs, n = 64 | 287 to 326 (-O2), 290 to 326 (-O3) | 286 to 324 (-O2), 295 to 321 (-O3) | 200 to 207 | 202 to 203 |
| `sum`, two limbs, n = 1024 | 4332 to 4926 (-O2), 4484 to 4719 (-O3) | 4544 to 4927 (-O2), 4363 to 4961 (-O3) | 2650 to 2677 | 2634 to 2656 |
| `dot`, one limb, n = 1 | 4.05 to 5.73 (-O2), 9.25 to 9.58 (-O3) | 6.76 to 7.21 (-O2), 5.67 to 5.97 (-O3) | 7.22 to 7.52 | 8.46 to 8.5 (-O2), 8.93 to 8.94 (-O3) |
| `dot`, one limb, n = 2 | 4.77 to 9.18 (-O2), 3.13 to 3.39 (-O3) | 8.1 to 8.45 (-O2), 4.5 to 6.29 (-O3) | 8.65 to 8.9 | 9.91 to 9.98 (-O2), 10.4 to 10.5 (-O3) |
| `dot`, one limb, n = 4 | 12.9 (-O2), 13 to 13.8 (-O3) | 10.2 to 10.6 (-O2), 9.32 to 10.5 (-O3) | 10.9 to 11 | 12.1 to 12.2 |
| `dot`, one limb, n = 8 | 15 to 16.3 (-O2), 15.6 to 16.3 (-O3) | 11.6 to 13.2 (-O2), 11.8 to 13.1 (-O3) | 12.3 to 12.8 | 13.6 to 13.8 |
| `dot`, one limb, n = 16 | 19.5 to 21.5 (-O2), 20.6 to 21.5 (-O3) | 16.2 to 18.3 (-O2), 16.7 to 18.3 (-O3) | 15.3 to 15.5 | 16.6 to 16.7 |
| `dot`, one limb, n = 64 | 46 to 52.3 (-O2), 48 to 52.3 (-O3) | 45.3 to 49 (-O2), 46.9 to 49 (-O3) | 33.2 to 33.5 | 34.5 to 34.8 |
| `dot`, one limb, n = 1024 | 583 to 663 (-O2), 603 to 663 (-O3) | 606 to 660 (-O2), 631 to 660 (-O3) | 394 to 397 | 395 to 398 |
| `dot`, two limbs, n = 1 | 26.9 to 30.5 (-O2), 28.3 to 30.5 (-O3) | 21.8 to 24.7 (-O2), 18.8 to 20.4 (-O3) | 34.5 to 34.8 (-O2), 21.4 (-O3) | 31.6 to 31.8 |
| `dot`, two limbs, n = 2 | 33.7 to 38.3 (-O2), 36.7 to 38.3 (-O3) | 31.6 to 34.9 (-O2), 27 to 30.2 (-O3) | 43.6 to 44.2 (-O2), 31.3 (-O3) | 42.5 to 42.7 |
| `dot`, two limbs, n = 4 | 44.3 to 50 (-O2), 44 to 50 (-O3) | 44.3 to 46.3 (-O2), 36.7 to 41 (-O3) | 58.2 to 58.5 (-O2), 52.5 to 52.7 (-O3) | 55.6 to 56.1 |
| `dot`, two limbs, n = 8 | 63.2 to 68.7 (-O2), 60.4 to 68.7 (-O3) | 61.9 to 64.6 (-O2), 54.4 to 60.7 (-O3) | 68.3 to 68.9 (-O2), 62.7 to 62.8 (-O3) | 66 to 66.5 |
| `dot`, two limbs, n = 16 | 94.3 to 107 (-O2), 94.3 to 107 (-O3) | 90.5 to 103 (-O2), 91 to 98.4 (-O3) | 88.6 to 89.5 (-O2), 83.6 (-O3) | 86.4 to 87.1 |
| `dot`, two limbs, n = 64 | 319 to 333 (-O2), 293 to 333 (-O3) | 290 to 329 (-O2), 286 to 325 (-O3) | 206 to 212 | 210 to 212 |
| `dot`, two limbs, n = 1024 | 4325 to 4850 (-O2), 4264 to 4850 (-O3) | 4361 to 4859 (-O2), 4419 to 4853 (-O3) | 2649 to 2678 | 2677 to 2694 |

| Short arrays, independent calls: the length known to the compiler over read at run time | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.61 to 0.67 (-O2), 0.75 to 0.78 (-O3) | 0.57 to 0.60 (-O2), 0.80 to 0.87 (-O3) | 0.92 to 0.96 | 0.89 to 0.93 |
| `sum`, one limb, n = 2 | 0.61 to 0.65 (-O2), 0.76 to 0.83 (-O3) | 0.53 to 0.61 (-O2), 0.79 to 0.86 (-O3) | 0.93 to 0.97 | 0.92 to 0.96 |
| `sum`, one limb, n = 4 | 0.42 to 0.45 (-O2), 0.75 (-O3) | 0.45 to 0.51 (-O2), 0.63 to 0.70 (-O3) | 0.96 | 0.92 to 0.95 |
| `sum`, one limb, n = 8 | 0.39 to 0.41 (-O2), 0.52 to 0.53 (-O3) | 0.78 to 0.81 (-O2), 0.43 to 0.45 (-O3) | 0.92 to 0.96 | 0.88 to 0.89 (-O2), 0.93 to 0.94 (-O3) |
| `sum`, one limb, n = 16 | 0.38 to 0.43 | 0.86 to 0.95 (-O2), 0.40 to 0.42 (-O3) | 0.98 (-O2), 0.89 (-O3) | 0.91 to 0.92 |
| `sum`, one limb, n = 64 | 0.90 to 0.96 (-O2), 0.74 to 0.76 (-O3) | 0.90 to 0.96 (-O2), 0.90 to 0.98 (-O3) | 0.87 (-O2), 0.66 (-O3) | 0.89 (-O2), 0.59 (-O3) |
| `sum`, one limb, n = 1024 | 0.99 to 1.04 | 0.96 to 1.15 (-O2), 0.97 to 1.05 (-O3) | 0.98 to 1.00 | 0.97 to 1.00 |
| `sum`, two limbs, n = 1 | 0.96 to 1.00 | 1.00 to 1.14 (-O2), 0.71 to 0.80 (-O3) | 1.00 (-O2), 0.89 (-O3) | 1.00 |
| `sum`, two limbs, n = 2 | 0.96 to 1.00 (-O2), 0.97 to 1.01 (-O3) | 1.00 to 1.09 (-O2), 0.87 to 0.90 (-O3) | 0.99 to 1.00 (-O2), 0.87 to 0.88 (-O3) | 1.00 |
| `sum`, two limbs, n = 4 | 0.96 to 1.00 | 1.00 to 1.05 (-O2), 0.84 to 0.88 (-O3) | 1.00 (-O2), 0.95 (-O3) | 1.00 |
| `sum`, two limbs, n = 8 | 0.99 to 1.01 | 0.98 to 1.07 (-O2), 0.94 to 0.98 (-O3) | 0.97 to 1.00 | 1.00 |
| `sum`, two limbs, n = 16 | 1.00 to 1.04 (-O2), 0.96 to 1.03 (-O3) | 0.96 to 1.03 (-O2), 0.93 to 0.98 (-O3) | 0.98 to 1.00 | 1.00 |
| `sum`, two limbs, n = 64 | 0.98 to 1.00 (-O2), 0.98 to 1.04 (-O3) | 0.97 to 1.00 (-O2), 0.95 to 1.07 (-O3) | 1.00 | 1.00 |
| `sum`, two limbs, n = 1024 | 0.96 to 1.00 (-O2), 1.02 to 1.05 (-O3) | 1.00 to 1.02 | 1.00 | 1.00 |
| `dot`, one limb, n = 1 | 0.61 (-O2), 0.75 to 0.80 (-O3) | 0.60 to 0.63 (-O2), 0.80 to 0.83 (-O3) | 0.96 | 0.92 to 0.96 |
| `dot`, one limb, n = 2 | 0.58 to 0.64 (-O2), 0.70 to 0.76 (-O3) | 0.58 to 0.64 (-O2), 0.79 to 0.82 (-O3) | 0.92 to 0.94 | 0.88 to 0.92 |
| `dot`, one limb, n = 4 | 0.59 to 0.60 (-O2), 0.75 to 0.77 (-O3) | 0.50 to 0.63 (-O2), 0.62 to 0.70 (-O3) | 0.92 to 0.96 | 0.90 (-O2), 0.97 to 0.98 (-O3) |
| `dot`, one limb, n = 8 | 0.51 to 0.56 | 0.80 to 0.86 (-O2), 0.50 to 0.54 (-O3) | 0.92 to 0.95 | 0.93 to 0.98 |
| `dot`, one limb, n = 16 | 0.68 to 0.71 | 0.86 to 0.87 (-O2), 0.59 to 0.63 (-O3) | 0.96 (-O2), 0.91 (-O3) | 0.92 to 0.96 |
| `dot`, one limb, n = 64 | 0.99 to 1.00 (-O2), 0.95 to 0.97 (-O3) | 0.89 to 1.01 (-O2), 1.37 (-O3) | 1.00 (-O2), 0.95 (-O3) | 1.00 (-O2), 0.95 (-O3) |
| `dot`, one limb, n = 1024 | 1.00 to 1.05 | 0.99 to 1.14 (-O2), 0.96 to 1.00 (-O3) | 1.00 | 1.00 |
| `dot`, two limbs, n = 1 | 1.00 to 1.01 | 0.96 to 1.00 (-O2), 0.87 to 0.91 (-O3) | 1.00 (-O2), 0.93 (-O3) | 1.00 |
| `dot`, two limbs, n = 2 | 0.98 to 1.01 | 1.00 to 1.05 (-O2), 0.86 to 0.93 (-O3) | 1.00 (-O2), 0.94 to 0.95 (-O3) | 0.99 to 1.00 |
| `dot`, two limbs, n = 4 | 1.00 to 1.08 (-O2), 0.99 to 1.03 (-O3) | 0.97 (-O2), 0.87 to 0.93 (-O3) | 0.98 to 1.00 | 1.01 |
| `dot`, two limbs, n = 8 | 0.99 to 1.05 (-O2), 1.00 (-O3) | 0.93 to 1.00 (-O2), 0.93 to 0.95 (-O3) | 0.98 to 1.01 | 1.00 |
| `dot`, two limbs, n = 16 | 0.92 to 1.00 (-O2), 1.00 (-O3) | 0.99 to 1.04 (-O2), 0.98 to 0.99 (-O3) | 0.97 to 1.01 | 1.00 |
| `dot`, two limbs, n = 64 | 0.92 to 1.00 (-O2), 0.88 to 1.00 (-O3) | 1.00 to 1.09 (-O2), 0.88 to 1.00 (-O3) | 0.99 to 1.00 | 1.00 |
| `dot`, two limbs, n = 1024 | 0.98 to 1.00 (-O2), 0.88 to 1.00 (-O3) | 0.95 to 1.00 (-O2), 0.95 to 1.00 (-O3) | 1.00 to 1.01 | 1.00 |

| The public function minus the generated loop called directly, ns per call | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1, independent | 0.513 to 0.628 (-O2), 0.534 to 0.63 (-O3) | 0.509 to 0.638 (-O2), 0.552 to 0.638 (-O3) | 5.37 to 5.41 (-O2), 5.06 to 5.07 (-O3) | 5.67 to 5.75 |
| `sum`, one limb, n = 16, independent | 0.136 to 0.32 (-O2), 0.29 to 0.324 (-O3) | 0.227 to 0.32 (-O2), 0 to 0.457 (-O3) | 4.86 to 4.9 (-O2), 4.14 to 4.16 (-O3) | 5.03 to 5.16 |
| `sum`, one limb, n = 1024, independent | -14.3 to 7.2 (-O2), -0.3 to 3.1 (-O3) | -15.5 to -4.7 (-O2), -14 to -2.3 (-O3) | 5.4 to 6.2 (-O2), 5.8 to 6.1 (-O3) | 1.9 to 2.1 (-O2), 3.2 to 3.6 (-O3) |
| `sum`, two limbs, n = 1, independent | 0.234 to 0.463 (-O2), 0.219 to 0.366 (-O3) | 0.208 to 0.323 (-O2), -0.002 to 0.059 (-O3) | 1.25 to 1.46 (-O2), 3.21 (-O3) | 1.78 to 1.87 (-O2), 1.75 to 1.85 (-O3) |
| `sum`, two limbs, n = 16, independent | 0.87 to 1.05 (-O2), 0.42 to 0.97 (-O3) | 0.01 to 0.81 (-O2), -3.02 to 1.96 (-O3) | 1.01 to 1.33 (-O2), 0.88 to 1.07 (-O3) | 0.97 to 1.08 (-O2), 1.04 to 1.24 (-O3) |
| `sum`, two limbs, n = 1024, independent | -5 to 7 (-O2), -2 to 5 (-O3) | -8 to 1 (-O2), 0 to 7 (-O3) | -4 to 21 (-O2), 0 to 5 (-O3) | -2 to 3 (-O2), -1 to 0 (-O3) |
| `dot`, one limb, n = 1, independent | 0.619 to 0.707 (-O2), 0.496 to 0.561 (-O3) | 0.006 to 0.015 (-O2), 0.007 to 0.078 (-O3) | 5.08 to 5.09 | 5.08 to 5.1 (-O2), 5.38 to 5.39 (-O3) |
| `dot`, one limb, n = 16, independent | 0.222 to 0.324 (-O2), 0.319 to 0.413 (-O3) | 0.54 to 0.683 (-O2), 0.574 to 0.633 (-O3) | 4.26 to 4.38 | 4.5 to 4.53 (-O2), 4.23 to 4.24 (-O3) |
| `dot`, one limb, n = 1024, independent | -13.6 to 0.2 (-O2), -20.1 to 0.9 (-O3) | -0.8 to 10.4 (-O2), 0.8 (-O3) | 14.2 to 14.8 (-O2), 12.2 to 13.6 (-O3) | 11.1 to 12.4 (-O2), 9.2 to 10.8 (-O3) |
| `dot`, two limbs, n = 1, independent | 0.309 to 0.351 (-O2), 0.088 to 0.35 (-O3) | 0.634 to 0.683 (-O2), 0.158 to 0.168 (-O3) | 2.63 to 2.7 (-O2), 1.07 to 1.09 (-O3) | 1.89 to 2.07 (-O2), 1.9 to 1.95 (-O3) |
| `dot`, two limbs, n = 16, independent | 1.35 to 3.5 (-O2), 1.23 to 1.5 (-O3) | -2.58 to 0.56 (-O2), 1.56 to 2.61 (-O3) | 1.33 to 1.43 (-O2), 0.89 to 0.99 (-O3) | 0.93 to 1.01 (-O2), 0.88 to 1.1 (-O3) |
| `dot`, two limbs, n = 1024, independent | -1 to 239 (-O2), 0 to 4 (-O3) | 0 to 178 (-O2), -300 to 202 (-O3) | -5 to 3 (-O2), -4 to -1 (-O3) | -11 to 1 (-O2), -2 to 6 (-O3) |
| `sum`, one limb, n = 1, dependent | -0.187 to 0.506 (-O2), 0.31 to 0.396 (-O3) | 0.319 to 0.455 (-O2), -0.127 to 0.052 (-O3) | 0.87 to 0.888 (-O2), 1.28 to 1.29 (-O3) | 0.082 to 0.102 (-O2), 0.033 to 0.04 (-O3) |
| `sum`, one limb, n = 16, dependent | 0.04 to 0.06 (-O2), 0.03 to 0.04 (-O3) | -0.72 to -0.1 (-O2), -0.18 to 0.4 (-O3) | 0.18 to 0.22 (-O2), 0.11 to 0.13 (-O3) | 0.11 to 0.14 (-O2), 0.13 to 0.19 (-O3) |
| `sum`, one limb, n = 1024, dependent | -21.9 to -17.7 (-O2), -0.4 to 1.8 (-O3) | -12.9 to 18 (-O2), -3.8 to 17 (-O3) | -0.6 to 0.2 (-O2), -0.1 to 0.2 (-O3) | 0.3 to 0.4 (-O2), 0.3 to 0.8 (-O3) |
| `sum`, two limbs, n = 1, dependent | 6.26 to 7.16 (-O2), 5.89 to 7.98 (-O3) | -4.47 to -4.11 (-O2), -2.52 to -2.14 (-O3) | 1.02 to 1.56 (-O2), 0.15 to 0.18 (-O3) | 1.33 to 1.38 (-O2), 1.29 to 1.53 (-O3) |
| `sum`, two limbs, n = 16, dependent | 4.57 to 6.03 (-O2), 5.49 to 6.05 (-O3) | 0 to 0.07 (-O2), 0.32 to 0.41 (-O3) | -0.4 to -0.15 (-O2), -0.03 to 0.05 (-O3) | 0.11 to 0.12 (-O2), 0.11 to 0.55 (-O3) |
| `sum`, two limbs, n = 1024, dependent | -5 to 128 (-O2), -203 to 13 (-O3) | 1 to 6 (-O2), 4 to 14 (-O3) | 0 to 5 (-O2), 1 to 3 (-O3) | -2 to 8 (-O2), 0 to 9 (-O3) |
| `dot`, one limb, n = 1, dependent | 0.49 to 1.5 (-O2), 5.68 to 6.09 (-O3) | 0.081 to 0.228 (-O2), 0.826 to 0.984 (-O3) | 0.074 to 0.088 (-O2), 0.321 to 0.327 (-O3) | 0.198 to 0.215 (-O2), 0.038 to 0.067 (-O3) |
| `dot`, one limb, n = 16, dependent | -0.98 to 0 (-O2), -0.01 to 0.47 (-O3) | -0.22 to 0.69 (-O2), -0.81 to 0.02 (-O3) | 0.01 to 0.06 (-O2), -0.06 to -0.03 (-O3) | 0.11 to 0.18 (-O2), 0.2 to 0.24 (-O3) |
| `dot`, one limb, n = 1024, dependent | 0 (-O2), -2.8 to 0 (-O3) | -16.5 to 0 (-O2), -0.2 to 11.7 (-O3) | -1.1 to 0.7 (-O2), 0.2 to 0.6 (-O3) | -0.1 to 0.4 (-O2), 0 to 2.1 (-O3) |
| `dot`, two limbs, n = 1, dependent | 5.24 to 5.92 (-O2), 5.14 to 5.87 (-O3) | -0.09 to 0.01 (-O2), -0.03 to 0.12 (-O3) | 2.17 to 2.27 (-O2), 0.18 to 0.19 (-O3) | 1.03 to 1.12 (-O2), 1.05 to 1.09 (-O3) |
| `dot`, two limbs, n = 16, dependent | 5.02 to 5.7 (-O2), 5.12 to 10.6 (-O3) | -0.5 to 0.15 (-O2), 0.5 to 2.7 (-O3) | 0.09 to 0.89 (-O2), 0.26 to 0.37 (-O3) | 0.13 to 0.21 (-O2), 0.04 to 0.29 (-O3) |
| `dot`, two limbs, n = 1024, dependent | -514 to 5 (-O2), 1 to 492 (-O3) | -14 to 220 (-O2), 0 to 146 (-O3) | -3 to 15 (-O2), -8 to -6 (-O3) | -8 to 2 (-O2), -4 to 12 (-O3) |

| The check at entry, independent calls: ns per call (with the check minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.524 to 0.657 (-O2), 0.514 to 0.604 (-O3) | 0.477 to 0.734 (-O2), 0.491 to 0.542 (-O3) | 5.27 to 5.39 | 5.69 to 5.73 |
| `sum`, one limb, n = 2 | 0.65 to 0.721 (-O2), 0.5 to 0.546 (-O3) | 0.278 to 0.35 (-O2), 0.193 to 0.3 (-O3) | 5.03 to 5.08 | 5.38 to 5.51 |
| `sum`, one limb, n = 4 | 1.03 to 1.09 (-O2), 0.202 to 0.285 (-O3) | 0.235 to 0.44 (-O2), 0.254 to 0.292 (-O3) | 5.33 to 5.49 | 5.23 to 5.41 |
| `sum`, one limb, n = 8 | 0.269 to 0.438 (-O2), -0.359 to -0.278 (-O3) | 0.14 to 0.806 (-O2), -0.219 to 0.004 (-O3) | 5.1 to 5.28 | 5.36 to 5.5 |
| `sum`, one limb, n = 16 | 0.208 to 0.507 (-O2), -0.35 to 0.046 (-O3) | -0.058 to 1.01 (-O2), -0.03 to 0.081 (-O3) | 4.89 to 4.92 (-O2), 4.55 to 4.59 (-O3) | 5.05 to 5.15 |
| `sum`, one limb, n = 64 | 0.16 to 0.323 (-O2), -0.39 to 0.09 (-O3) | -0.09 to 1.55 (-O2), -0.43 to 0.27 (-O3) | 4.15 to 4.16 (-O2), 2.39 to 2.44 (-O3) | 1.86 to 1.91 (-O2), 3.56 to 3.69 (-O3) |
| `sum`, one limb, n = 1024 | 17.8 to 27.4 (-O2), -2.5 to 2.5 (-O3) | -34.4 to 40.2 (-O2), -31.3 to -4.6 (-O3) | 9.5 to 10.2 (-O2), 5.8 to 6.4 (-O3) | 1.7 to 2.8 (-O2), 2.9 to 3.9 (-O3) |
| `sum`, two limbs, n = 1 | 0.043 to 0.33 (-O2), -0.149 to 0.229 (-O3) | 0.283 to 0.667 (-O2), 0.023 to 0.05 (-O3) | 1.4 to 1.54 (-O2), 3.2 to 3.22 (-O3) | 1.57 to 1.9 (-O2), 1.77 to 1.97 (-O3) |
| `sum`, two limbs, n = 2 | 0.148 to 0.468 (-O2), -0.184 to 0.471 (-O3) | -0.009 to 0.634 (-O2), -0.013 to 0.32 (-O3) | 0.27 to 0.44 (-O2), 0.77 to 0.82 (-O3) | 1.37 to 1.83 (-O2), 1.58 to 1.82 (-O3) |
| `sum`, two limbs, n = 4 | 0.092 to 0.74 (-O2), -0.197 to 0.743 (-O3) | -0.457 to 0.978 (-O2), 0.387 to 0.485 (-O3) | 1.66 to 1.84 (-O2), 0.91 to 1.01 (-O3) | 1.44 to 2.37 (-O2), 1.61 to 2.35 (-O3) |
| `sum`, two limbs, n = 8 | -1.28 to 0.06 (-O2), -0.59 to 0.73 (-O3) | 0.24 to 1.2 (-O2), -0.26 to 0.56 (-O3) | 2.24 to 2.38 (-O2), 0.41 to 0.51 (-O3) | 0.77 to 1.31 (-O2), 0.84 to 1.43 (-O3) |
| `sum`, two limbs, n = 16 | 0.21 to 1.27 (-O2), -2.05 to 1.13 (-O3) | -1.63 to 4.58 (-O2), 0.42 to 0.46 (-O3) | 1.06 to 1.26 (-O2), 1.18 to 1.33 (-O3) | 0.94 to 1.18 (-O2), 0.97 to 1.43 (-O3) |
| `sum`, two limbs, n = 64 | -0.4 to 2.5 (-O2), -3.8 to 0.2 (-O3) | -2.8 to 30.4 (-O2), -3.4 to 0.3 (-O3) | 1.7 to 2.6 (-O2), 1 to 1.4 (-O3) | 0.5 to 1.5 (-O2), 0.8 to 1.6 (-O3) |
| `sum`, two limbs, n = 1024 | 5 to 371 (-O2), -168 to 99 (-O3) | -41 to 611 (-O2), -150 to 4 (-O3) | 1 to 6 (-O2), 0 to 7 (-O3) | -24 to 9 (-O2), -5 to 13 (-O3) |
| `dot`, one limb, n = 1 | 0.588 to 0.712 (-O2), 0.438 to 0.485 (-O3) | -0.016 to 0.21 (-O2), -0.013 to 0.007 (-O3) | 5.37 to 5.39 (-O2), 5.09 to 5.11 (-O3) | 5.38 to 5.41 |
| `dot`, one limb, n = 2 | 0.558 to 0.726 (-O2), 0.373 to 0.433 (-O3) | 0.233 to 0.374 (-O2), 0.277 to 0.36 (-O3) | 5.08 to 5.1 (-O2), 5.39 to 5.4 (-O3) | 5.37 to 5.4 (-O2), 4.69 to 5.39 (-O3) |
| `dot`, one limb, n = 4 | 0.389 to 0.569 (-O2), 0.156 to 0.231 (-O3) | 0.502 to 0.769 (-O2), 0.525 to 0.616 (-O3) | 5.24 to 5.41 | 5.09 to 5.33 |
| `dot`, one limb, n = 8 | 0.27 to 0.387 (-O2), 0.224 to 0.28 (-O3) | 0.388 to 0.698 (-O2), 0.414 to 0.539 (-O3) | 4.85 to 5.08 | 4.81 to 4.99 |
| `dot`, one limb, n = 16 | 0.27 to 0.278 (-O2), 0.211 to 0.388 (-O3) | 0.539 to 1.28 (-O2), 0.286 to 0.538 (-O3) | 4.26 to 4.41 | 4.5 to 4.53 (-O2), 4.17 to 4.25 (-O3) |
| `dot`, one limb, n = 64 | -0.7 to 0.26 (-O2), -0.67 to 0.16 (-O3) | -0.75 to 1.7 (-O2), -0.15 to 0.49 (-O3) | 2.15 to 2.24 | 3.84 to 4.21 (-O2), 1.11 to 1.19 (-O3) |
| `dot`, one limb, n = 1024 | -36 to -0.2 (-O2), -8.5 to 44.1 (-O3) | -43.9 to 41.4 (-O2), -21.2 to 0.9 (-O3) | 14.2 to 15.4 (-O2), 11.5 to 12.1 (-O3) | 6.5 to 11.9 (-O2), 7 to 8.8 (-O3) |
| `dot`, two limbs, n = 1 | -0.321 to 0.091 (-O2), 0.031 to 0.112 (-O3) | 0.368 to 1 (-O2), 0.121 to 0.213 (-O3) | 2.56 to 2.71 (-O2), 1.11 to 1.15 (-O3) | 1.32 to 1.64 (-O2), 1.46 to 1.74 (-O3) |
| `dot`, two limbs, n = 2 | -0.403 to 0.122 (-O2), -0.036 to 0.537 (-O3) | -0.475 to 1.12 (-O2), 0.469 to 0.77 (-O3) | 2.51 to 2.91 (-O2), 0.85 to 0.9 (-O3) | 1.87 to 2.38 (-O2), 2.02 to 2.45 (-O3) |
| `dot`, two limbs, n = 4 | -0.873 to 0.139 (-O2), -0.349 to 0.851 (-O3) | -0.494 to 2.08 (-O2), 0.314 to 0.452 (-O3) | 1.56 to 1.78 (-O2), -0.2 to -0.12 (-O3) | 0.85 to 1.18 (-O2), 0.92 to 1.26 (-O3) |
| `dot`, two limbs, n = 8 | -0.86 to 0.07 (-O2), -0.29 to 0.89 (-O3) | 0 to 2.61 (-O2), 0.66 to 1.22 (-O3) | 1.49 to 1.65 (-O2), 1.04 to 1.19 (-O3) | 1.24 to 1.82 (-O2), 1.5 to 1.98 (-O3) |
| `dot`, two limbs, n = 16 | 0.05 to 0.68 (-O2), -0.91 to 1.81 (-O3) | -0.73 to 5.69 (-O2), 1.41 to 2.15 (-O3) | 1.23 to 1.34 (-O2), 0.95 to 1.22 (-O3) | 0.89 to 1.2 (-O2), 0.78 to 1.34 (-O3) |
| `dot`, two limbs, n = 64 | -0.2 to 3.1 (-O2), -3.4 to 30.9 (-O3) | -15.9 to 23 (-O2), 0.8 to 4.7 (-O3) | 1.6 to 2.3 (-O2), 0.9 to 1.4 (-O3) | 0.7 to 2.2 (-O2), 1.4 to 2.8 (-O3) |
| `dot`, two limbs, n = 1024 | -7 to 51 (-O2), -77 to 458 (-O3) | -124 to 596 (-O2), -4 to 2 (-O3) | 2 to 6 (-O2), -5 to 5 (-O3) | -7 to 6 (-O2), -9 to 9 (-O3) |

| The check at entry, independent calls: its share of the call (1 - without over with) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.39 to 0.43 (-O2), 0.47 to 0.49 (-O3) | 0.34 to 0.47 (-O2), 0.34 to 0.40 (-O3) | 0.73 to 0.78 | 0.79 to 0.82 |
| `sum`, one limb, n = 2 | 0.46 to 0.51 (-O2), 0.44 to 0.48 (-O3) | 0.20 to 0.25 (-O2), 0.13 to 0.22 (-O3) | 0.69 to 0.70 | 0.76 to 0.78 |
| `sum`, one limb, n = 4 | 0.52 to 0.55 (-O2), 0.18 to 0.25 (-O3) | 0.14 to 0.25 (-O2), 0.16 to 0.18 (-O3) | 0.74 to 0.76 | 0.72 (-O2), 0.77 (-O3) |
| `sum`, one limb, n = 8 | 0.13 to 0.18 (-O2), -0.20 to -0.16 (-O3) | 0.05 to 0.25 (-O2), -0.09 to 0.00 (-O3) | 0.70 to 0.71 | 0.71 to 0.74 |
| `sum`, one limb, n = 16 | 0.06 to 0.14 (-O2), -0.12 to 0.01 (-O3) | -0.01 to 0.23 (-O2), -0.01 to 0.02 (-O3) | 0.63 (-O2), 0.58 to 0.59 (-O3) | 0.67 |
| `sum`, one limb, n = 64 | 0.02 to 0.03 (-O2), -0.04 to 0.01 (-O3) | -0.01 to 0.13 (-O2), -0.04 to 0.03 (-O3) | 0.29 (-O2), 0.18 to 0.19 (-O3) | 0.21 to 0.22 (-O2), 0.27 to 0.28 (-O3) |
| `sum`, one limb, n = 1024 | 0.05 to 0.08 (-O2), -0.01 to 0.01 (-O3) | -0.10 to 0.11 (-O2), -0.09 to -0.01 (-O3) | 0.03 to 0.05 | 0.01 to 0.02 |
| `sum`, two limbs, n = 1 | 0.01 to 0.07 (-O2), -0.04 to 0.06 (-O3) | 0.10 to 0.22 (-O2), 0.01 to 0.03 (-O3) | 0.04 to 0.05 (-O2), 0.39 to 0.40 (-O3) | 0.05 to 0.06 |
| `sum`, two limbs, n = 2 | 0.03 to 0.10 (-O2), -0.04 to 0.10 (-O3) | -0.00 to 0.14 (-O2), -0.00 to 0.08 (-O3) | 0.01 (-O2), 0.06 to 0.07 (-O3) | 0.03 to 0.04 |
| `sum`, two limbs, n = 4 | 0.01 to 0.09 (-O2), -0.03 to 0.10 (-O3) | -0.07 to 0.13 (-O2), 0.05 to 0.07 (-O3) | 0.03 to 0.06 | 0.05 to 0.07 |
| `sum`, two limbs, n = 8 | -0.09 to 0.00 (-O2), -0.04 to 0.05 (-O3) | 0.02 to 0.09 (-O2), -0.02 to 0.04 (-O3) | 0.01 to 0.05 | 0.02 to 0.03 |
| `sum`, two limbs, n = 16 | 0.01 to 0.04 (-O2), -0.06 to 0.03 (-O3) | -0.05 to 0.13 (-O2), 0.01 (-O3) | 0.02 | 0.02 |
| `sum`, two limbs, n = 64 | -0.02 to 0.01 | -0.01 to 0.13 (-O2), -0.02 to 0.00 (-O3) | 0.01 | 0.00 to 0.01 |
| `sum`, two limbs, n = 1024 | 0.00 to 0.08 (-O2), -0.04 to 0.02 (-O3) | -0.01 to 0.13 (-O2), -0.03 to 0.00 (-O3) | 0.00 | -0.01 to 0.00 |
| `dot`, one limb, n = 1 | 0.44 to 0.46 (-O2), 0.38 to 0.43 (-O3) | -0.01 to 0.14 (-O2), -0.01 to 0.01 (-O3) | 0.78 (-O2), 0.70 (-O3) | 0.74 to 0.78 |
| `dot`, one limb, n = 2 | 0.42 to 0.47 (-O2), 0.33 to 0.38 (-O3) | 0.16 to 0.26 (-O2), 0.20 to 0.24 (-O3) | 0.70 to 0.72 | 0.71 to 0.72 (-O2), 0.65 to 0.74 (-O3) |
| `dot`, one limb, n = 4 | 0.28 to 0.36 (-O2), 0.13 to 0.20 (-O3) | 0.29 to 0.41 (-O2), 0.32 to 0.33 (-O3) | 0.72 | 0.70 to 0.74 |
| `dot`, one limb, n = 8 | 0.13 to 0.17 (-O2), 0.09 to 0.12 (-O3) | 0.14 to 0.25 (-O2), 0.14 to 0.20 (-O3) | 0.64 to 0.67 | 0.64 (-O2), 0.68 to 0.69 (-O3) |
| `dot`, one limb, n = 16 | 0.07 to 0.10 | 0.14 to 0.29 (-O2), 0.07 to 0.14 (-O3) | 0.54 to 0.55 | 0.55 to 0.58 |
| `dot`, one limb, n = 64 | -0.05 to 0.02 (-O2), -0.05 to 0.01 (-O3) | -0.05 to 0.12 (-O2), -0.01 to 0.04 (-O3) | 0.13 to 0.14 | 0.26 to 0.28 (-O2), 0.07 to 0.08 (-O3) |
| `dot`, one limb, n = 1024 | -0.07 to -0.00 (-O2), -0.02 to 0.08 (-O3) | -0.09 to 0.08 (-O2), -0.04 to 0.00 (-O3) | 0.03 to 0.04 | 0.02 to 0.03 |
| `dot`, two limbs, n = 1 | -0.07 to 0.02 (-O2), 0.01 to 0.02 (-O3) | 0.11 to 0.27 (-O2), 0.04 to 0.08 (-O3) | 0.07 to 0.08 (-O2), 0.12 (-O3) | 0.04 to 0.06 |
| `dot`, two limbs, n = 2 | -0.06 to 0.02 (-O2), -0.01 to 0.08 (-O3) | -0.08 to 0.17 (-O2), 0.08 to 0.12 (-O3) | 0.05 to 0.07 | 0.05 to 0.06 |
| `dot`, two limbs, n = 4 | -0.09 to 0.01 (-O2), -0.04 to 0.08 (-O3) | -0.05 to 0.19 (-O2), 0.03 to 0.05 (-O3) | 0.04 to 0.05 (-O2), -0.01 to -0.00 (-O3) | 0.02 to 0.03 |
| `dot`, two limbs, n = 8 | -0.05 to 0.00 (-O2), -0.02 to 0.04 (-O3) | 0.00 to 0.13 (-O2), 0.04 to 0.07 (-O3) | 0.02 to 0.03 | 0.03 to 0.04 |
| `dot`, two limbs, n = 16 | 0.00 to 0.02 (-O2), -0.02 to 0.04 (-O3) | -0.02 to 0.14 (-O2), 0.04 to 0.05 (-O3) | 0.01 to 0.02 | 0.01 to 0.02 |
| `dot`, two limbs, n = 64 | -0.00 to 0.01 (-O2), -0.02 to 0.12 (-O3) | -0.07 to 0.10 (-O2), 0.00 to 0.02 (-O3) | 0.00 to 0.01 | 0.00 to 0.01 |
| `dot`, two limbs, n = 1024 | -0.00 to 0.01 (-O2), -0.02 to 0.10 (-O3) | -0.03 to 0.13 (-O2), -0.00 to 0.00 (-O3) | -0.00 to 0.00 | -0.00 to 0.00 |

| The check at entry, dependent calls: ns per call (with the check minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.457 to 0.5 (-O2), 0.335 to 0.367 (-O3) | 0.157 to 0.507 (-O2), 0.222 to 0.27 (-O3) | 0.846 to 0.862 (-O2), 1.29 to 1.3 (-O3) | 0.07 to 0.112 (-O2), 0.031 to 0.081 (-O3) |
| `sum`, one limb, n = 2 | 0.447 to 0.513 (-O2), 0.23 to 0.331 (-O3) | 0.193 to 0.514 (-O2), 0.169 to 0.296 (-O3) | 0.321 to 0.344 (-O2), 0.398 to 0.429 (-O3) | 0.127 to 0.189 (-O2), 0.019 to 0.043 (-O3) |
| `sum`, one limb, n = 4 | 0.014 to 0.467 (-O2), -0.696 to 0.126 (-O3) | -0.757 to 0.975 (-O2), -0.529 to -0.01 (-O3) | 0.09 to 0.12 (-O2), 0.085 to 0.142 (-O3) | 0.01 to 0.07 (-O2), 0.19 to 0.26 (-O3) |
| `sum`, one limb, n = 8 | 0.02 to 0.68 (-O2), -0.92 to -0.02 (-O3) | -0.465 to 1.69 (-O2), -0.879 to -0.089 (-O3) | 0.15 to 0.19 (-O2), 0.41 to 0.45 (-O3) | -0.02 to 0.11 (-O2), 0.11 to 0.19 (-O3) |
| `sum`, one limb, n = 16 | 0.02 to 0.19 (-O2), -1.73 to 0.11 (-O3) | -0.13 to 1.75 (-O2), -0.73 to 0.31 (-O3) | 0.19 to 0.23 (-O2), 0.11 to 0.15 (-O3) | 0.12 to 0.21 (-O2), 0.17 to 0.19 (-O3) |
| `sum`, one limb, n = 64 | -0.72 to -0.42 (-O2), -1.16 to -0.45 (-O3) | -2.66 to 3.58 (-O2), -2.25 to -0.1 (-O3) | 0.15 to 0.23 (-O2), 0.09 to 0.21 (-O3) | -0.05 to 0.3 (-O2), 0.09 to 0.22 (-O3) |
| `sum`, one limb, n = 1024 | 0.3 to 16.3 (-O2), -5 to 4.4 (-O3) | -20.4 to 60.7 (-O2), -24.3 to 0.9 (-O3) | 0.1 to 0.4 (-O2), -0.2 to 0.6 (-O3) | -1.3 to 0.9 (-O2), 0.1 to 1.2 (-O3) |
| `sum`, two limbs, n = 1 | 0.25 to 1.33 (-O2), 2.07 to 15.6 (-O3) | -4.31 to -2.37 (-O2), -3.6 to -1.71 (-O3) | 1.18 to 1.45 (-O2), 0.2 to 0.22 (-O3) | 1.25 to 1.58 (-O2), 1.42 to 1.56 (-O3) |
| `sum`, two limbs, n = 2 | -8.89 to -8.56 (-O2), -4.26 to 12.8 (-O3) | -4.35 to -2.18 (-O2), -9.34 to -7.21 (-O3) | 1.11 to 1.25 (-O2), -0.07 to 0.03 (-O3) | 1.18 to 1.51 (-O2), 1.3 to 1.61 (-O3) |
| `sum`, two limbs, n = 4 | 0.04 to 3.32 (-O2), 2.7 to 6.53 (-O3) | -2.35 to 3.59 (-O2), -0.61 to 0.03 (-O3) | -0.19 to 0.09 (-O2), 0.55 to 0.62 (-O3) | -0.11 to 0.47 (-O2), 0.19 to 0.54 (-O3) |
| `sum`, two limbs, n = 8 | -2.26 to 0.63 (-O2), 3.91 to 5.13 (-O3) | -0.06 to 5.77 (-O2), -2.88 to 0.07 (-O3) | -0.36 to -0.04 (-O2), 0.44 to 0.91 (-O3) | -0.24 to 0.16 (-O2), -0.19 to 0.09 (-O3) |
| `sum`, two limbs, n = 16 | 0.04 to 3.7 (-O2), -1.99 to 5.42 (-O3) | -0.88 to 11.9 (-O2), -3.46 to 1.61 (-O3) | -0.17 to -0.03 (-O2), 0.05 to 0.12 (-O3) | -0.67 to 0.41 (-O2), 0.03 to 0.54 (-O3) |
| `sum`, two limbs, n = 64 | 0.6 to 14 (-O2), -0.2 to 5.6 (-O3) | -4.3 to 40.4 (-O2), -9.7 to 0.7 (-O3) | -0.3 to 0.2 (-O2), 0.1 to 0.4 (-O3) | -2 to 0 (-O2), -0.4 to 0.6 (-O3) |
| `sum`, two limbs, n = 1024 | 7 to 103 (-O2), -75 to 3 (-O3) | 0 to 613 (-O2), -414 to 11 (-O3) | -2 to 8 (-O2), 2 to 6 (-O3) | -30 to 8 (-O2), -3 to 14 (-O3) |
| `dot`, one limb, n = 1 | 0.835 to 3.96 (-O2), 5.08 to 5.36 (-O3) | 0.056 to 0.5 (-O2), 0.987 to 1.05 (-O3) | 0.07 to 0.103 (-O2), 0.322 to 0.332 (-O3) | 0.149 to 0.272 (-O2), 0.04 to 0.108 (-O3) |
| `dot`, one limb, n = 2 | 0.545 to 3.21 (-O2), 0.123 to 0.331 (-O3) | 1.54 to 2.62 (-O2), -2.16 to -0.175 (-O3) | 0.231 to 0.251 (-O2), 0.335 to 0.384 (-O3) | 0.247 to 0.304 (-O2), 0.21 to 0.22 (-O3) |
| `dot`, one limb, n = 4 | -0.8 to 0.38 (-O2), -0.38 to -0.03 (-O3) | -1.16 to 1.17 (-O2), -0.977 to -0.237 (-O3) | 0.17 to 0.2 (-O2), 0.22 to 0.24 (-O3) | 0.2 to 0.25 (-O2), 0.12 to 0.22 (-O3) |
| `dot`, one limb, n = 8 | 0.05 to 1.5 (-O2), -0.16 to 0.7 (-O3) | -0.17 to 1.44 (-O2), -0.73 to -0.03 (-O3) | 0.24 to 0.31 (-O2), -0.05 to -0.02 (-O3) | 0.38 to 0.44 (-O2), 0.11 to 0.25 (-O3) |
| `dot`, one limb, n = 16 | -0.02 to 0.12 (-O2), -0.35 to 1.31 (-O3) | 0.06 to 2.38 (-O2), -0.54 to 0.02 (-O3) | 0.05 to 0.12 (-O2), -0.07 to -0.01 (-O3) | 0.09 to 0.21 (-O2), 0.19 to 0.34 (-O3) |
| `dot`, one limb, n = 64 | 0 to 0.94 (-O2), -0.84 to 0.47 (-O3) | -2.98 to 4.36 (-O2), -0.04 to -0.02 (-O3) | -0.14 to -0.04 (-O2), -0.07 to -0.02 (-O3) | -0.05 to 0.2 (-O2), 0.01 to 0.19 (-O3) |
| `dot`, one limb, n = 1024 | -0.4 to 2.3 (-O2), -10.4 to 7.2 (-O3) | -57.1 to 57.9 (-O2), -40.8 to 0.5 (-O3) | -0.3 to 0 (-O2), -0.5 to 1.7 (-O3) | 0.9 to 1.6 (-O2), -0.7 to 2.4 (-O3) |
| `dot`, two limbs, n = 1 | 0.04 to 0.18 (-O2), -0.18 to 0.41 (-O3) | -0.44 to 3.1 (-O2), -0.41 to -0.05 (-O3) | 2.28 to 2.36 (-O2), 0.05 to 0.15 (-O3) | 0.42 to 0.78 (-O2), 0.62 to 0.95 (-O3) |
| `dot`, two limbs, n = 2 | -3.26 to 0.21 (-O2), -0.39 to 3.12 (-O3) | -0.19 to 5.88 (-O2), -0.33 to 0.75 (-O3) | 1.91 to 2.12 (-O2), -0.16 to -0.08 (-O3) | 1.36 to 2.17 (-O2), 1.84 to 2.23 (-O3) |
| `dot`, two limbs, n = 4 | -3.76 to 2.08 (-O2), -0.83 to 4.05 (-O3) | -1.93 to 7.86 (-O2), -2.2 to 0.04 (-O3) | -0.16 to -0.02 (-O2), -0.31 to 0.17 (-O3) | -0.47 to 0.14 (-O2), -0.05 to 0.33 (-O3) |
| `dot`, two limbs, n = 8 | -1.73 to -0.11 (-O2), -1.68 to 2.31 (-O3) | -2.29 to 8.34 (-O2), -0.45 to 1.29 (-O3) | 0.17 to 0.37 (-O2), -0.21 to 0.04 (-O3) | 0.02 to 0.59 (-O2), 0.21 to 0.55 (-O3) |
| `dot`, two limbs, n = 16 | 0.42 to 5.96 (-O2), -1.12 to 0.76 (-O3) | -0.93 to 12.3 (-O2), 0.42 to 1.91 (-O3) | 0.14 to 0.37 (-O2), 0.19 to 0.49 (-O3) | 0.31 to 0.72 (-O2), 0.18 to 0.68 (-O3) |
| `dot`, two limbs, n = 64 | -0.1 to 4.6 (-O2), -4.6 to 40.8 (-O3) | -23.1 to 28.3 (-O2), 0.8 to 5.6 (-O3) | -0.1 to 0.6 (-O2), -0.4 to 0.5 (-O3) | -1.7 to 1.2 (-O2), 0 to 1.8 (-O3) |
| `dot`, two limbs, n = 1024 | -8 to 50 (-O2), -78 to 568 (-O3) | -83 to 612 (-O2), -371 to 6 (-O3) | 1 to 3 (-O2), -7 to -1 (-O3) | -17 to 6 (-O2), -4 to 16 (-O3) |

| The check at entry, dependent calls: its share of the call (1 - without over with) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, n = 1 | 0.29 to 0.34 (-O2), 0.25 to 0.30 (-O3) | 0.09 to 0.27 (-O2), 0.13 to 0.17 (-O3) | 0.12 (-O2), 0.18 (-O3) | 0.00 to 0.01 |
| `sum`, one limb, n = 2 | 0.30 to 0.36 (-O2), 0.19 to 0.23 (-O3) | 0.11 to 0.28 (-O2), 0.10 to 0.18 (-O3) | 0.04 to 0.06 | 0.00 to 0.02 |
| `sum`, one limb, n = 4 | 0.00 to 0.05 (-O2), -0.07 to 0.01 (-O3) | -0.11 to 0.12 (-O2), -0.07 to -0.00 (-O3) | 0.01 | 0.00 to 0.02 |
| `sum`, one limb, n = 8 | 0.00 to 0.06 (-O2), -0.08 to -0.00 (-O3) | -0.05 to 0.17 (-O2), -0.10 to -0.01 (-O3) | 0.01 to 0.04 | -0.00 to 0.02 |
| `sum`, one limb, n = 16 | 0.00 to 0.01 (-O2), -0.12 to 0.01 (-O3) | -0.01 to 0.13 (-O2), -0.06 to 0.03 (-O3) | 0.01 to 0.02 | 0.01 |
| `sum`, one limb, n = 64 | -0.03 to -0.01 | -0.09 to 0.11 (-O2), -0.07 to -0.00 (-O3) | 0.00 to 0.01 | -0.00 to 0.01 |
| `sum`, one limb, n = 1024 | 0.00 to 0.04 (-O2), -0.01 to 0.01 (-O3) | -0.05 to 0.14 (-O2), -0.06 to 0.00 (-O3) | -0.00 to 0.00 | -0.01 to 0.00 |
| `sum`, two limbs, n = 1 | 0.01 to 0.06 (-O2), 0.11 to 0.79 (-O3) | -0.51 to -0.26 (-O2), -0.51 to -0.21 (-O3) | 0.01 to 0.04 | 0.04 to 0.05 |
| `sum`, two limbs, n = 2 | -1.22 to -1.06 (-O2), -0.46 to 0.49 (-O3) | -0.33 to -0.15 (-O2), -0.77 to -0.63 (-O3) | -0.00 to 0.03 | 0.03 to 0.04 |
| `sum`, two limbs, n = 4 | 0.00 to 0.08 (-O2), 0.07 to 0.17 (-O3) | -0.07 to 0.10 (-O2), -0.02 to 0.00 (-O3) | -0.00 to 0.01 | -0.00 to 0.01 |
| `sum`, two limbs, n = 8 | -0.04 to 0.01 (-O2), 0.08 to 0.10 (-O3) | -0.00 to 0.11 (-O2), -0.06 to 0.00 (-O3) | -0.01 to 0.02 | -0.00 to 0.00 |
| `sum`, two limbs, n = 16 | 0.00 to 0.04 (-O2), -0.02 to 0.06 (-O3) | -0.01 to 0.13 (-O2), -0.04 to 0.02 (-O3) | -0.00 to 0.00 | -0.01 to 0.01 |
| `sum`, two limbs, n = 64 | -0.00 to 0.04 | -0.02 to 0.13 (-O2), -0.03 to 0.00 (-O3) | -0.00 to 0.00 | -0.01 to 0.00 |
| `sum`, two limbs, n = 1024 | -0.02 to 0.02 | 0.00 to 0.13 (-O2), -0.10 to 0.00 (-O3) | -0.00 to 0.00 | -0.01 to 0.01 |
| `dot`, one limb, n = 1 | 0.20 to 0.59 (-O2), 0.59 to 0.64 (-O3) | 0.01 to 0.08 (-O2), 0.19 to 0.20 (-O3) | 0.01 to 0.04 | 0.00 to 0.03 |
| `dot`, one limb, n = 2 | 0.10 to 0.41 (-O2), 0.04 to 0.11 (-O3) | 0.21 to 0.34 (-O2), -0.53 to -0.03 (-O3) | 0.03 to 0.04 | 0.02 to 0.03 |
| `dot`, one limb, n = 4 | -0.07 to 0.03 (-O2), -0.03 to -0.00 (-O3) | -0.13 to 0.11 (-O2), -0.11 to -0.03 (-O3) | 0.02 | 0.01 to 0.02 |
| `dot`, one limb, n = 8 | 0.00 to 0.10 (-O2), -0.01 to 0.04 (-O3) | -0.01 to 0.12 (-O2), -0.06 to -0.00 (-O3) | -0.00 to 0.02 | 0.01 to 0.03 |
| `dot`, one limb, n = 16 | -0.00 to 0.01 (-O2), -0.02 to 0.06 (-O3) | 0.00 to 0.14 (-O2), -0.03 to 0.00 (-O3) | -0.00 to 0.01 | 0.01 to 0.02 |
| `dot`, one limb, n = 64 | -0.02 to 0.02 | -0.07 to 0.10 (-O2), -0.00 (-O3) | -0.00 | -0.00 to 0.01 |
| `dot`, one limb, n = 1024 | -0.02 to 0.01 | -0.10 to 0.10 (-O2), -0.07 to 0.00 (-O3) | -0.00 to 0.00 | -0.00 to 0.01 |
| `dot`, two limbs, n = 1 | -0.01 to 0.02 | -0.02 to 0.13 (-O2), -0.02 to -0.00 (-O3) | 0.07 (-O2), 0.00 to 0.01 (-O3) | 0.01 to 0.03 |
| `dot`, two limbs, n = 2 | -0.10 to 0.01 (-O2), -0.01 to 0.09 (-O3) | -0.01 to 0.17 (-O2), -0.01 to 0.03 (-O3) | 0.04 to 0.05 (-O2), -0.01 to -0.00 (-O3) | 0.03 to 0.05 |
| `dot`, two limbs, n = 4 | -0.09 to 0.05 (-O2), -0.02 to 0.08 (-O3) | -0.05 to 0.17 (-O2), -0.06 to 0.00 (-O3) | -0.01 to 0.00 | -0.01 to 0.01 |
| `dot`, two limbs, n = 8 | -0.03 to -0.00 (-O2), -0.03 to 0.03 (-O3) | -0.04 to 0.13 (-O2), -0.01 to 0.03 (-O3) | -0.00 to 0.01 | 0.00 to 0.01 |
| `dot`, two limbs, n = 16 | 0.00 to 0.06 (-O2), -0.01 to 0.01 (-O3) | -0.01 to 0.12 (-O2), 0.01 to 0.02 (-O3) | 0.00 to 0.01 | 0.00 to 0.01 |
| `dot`, two limbs, n = 64 | -0.00 to 0.02 (-O2), -0.02 to 0.12 (-O3) | -0.08 to 0.09 (-O2), 0.00 to 0.02 (-O3) | -0.00 to 0.00 | -0.01 to 0.01 |
| `dot`, two limbs, n = 1024 | -0.00 to 0.01 (-O2), -0.02 to 0.12 (-O3) | -0.02 to 0.13 (-O2), -0.09 to 0.00 (-O3) | -0.00 to 0.00 | -0.01 to 0.01 |

| The check at entry: with over without (selection) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| control: the generated loop of `sum`, one limb, n = 1, with over without | 1.00 to 1.13 (-O2), 0.98 to 1.01 (-O3) | 0.92 to 1.15 (-O2), 0.93 to 1.01 (-O3) | 1.00 (-O2), 0.88 (-O3) | 1.00 |
| control: the generated loop of `sum`, one limb, n = 16, with over without | 1.00 to 1.01 (-O2), 0.89 to 1.01 (-O3) | 0.94 to 1.20 (-O2), 0.92 to 1.00 (-O3) | 1.00 to 1.01 (-O2), 1.09 to 1.13 (-O3) | 0.99 to 1.01 |
| control: the generated loop of `sum`, one limb, n = 1024, with over without | 0.99 to 1.02 (-O2), 0.96 to 1.00 (-O3) | 0.92 to 1.15 (-O2), 0.94 to 1.00 (-O3) | 0.98 to 1.02 | 1.00 to 1.01 |
| control: the generated loop of `dot`, two limbs, n = 1, with over without | 0.98 to 1.00 | 0.98 to 1.15 (-O2), 0.97 to 1.00 (-O3) | 1.00 | 1.00 to 1.01 |
| control: the generated loop of `dot`, two limbs, n = 16, with over without | 0.98 to 1.02 | 0.99 to 1.15 (-O2), 1.00 to 1.02 (-O3) | 1.00 | 1.00 |
| control: the generated loop of `dot`, two limbs, n = 1024, with over without | 1.00 (-O2), 0.98 to 1.10 (-O3) | 0.98 to 1.15 (-O2), 1.00 (-O3) | 1.00 | 0.99 to 1.00 |
| `sum`, one limb, 512 elements, with over without | 0.96 to 1.02 (-O2), 0.98 to 1.08 (-O3) | 1.02 to 1.08 (-O2), 1.00 to 1.03 (-O3) | 1.04 to 1.05 | 1.01 to 1.02 |
| `sum`, two limbs, 512 elements, with over without | 1.00 to 1.01 (-O2), 0.98 to 1.09 (-O3) | 0.97 to 1.06 (-O2), 0.92 to 1.00 (-O3) | 1.00 to 1.03 | 1.00 to 1.01 |
| `dot`, one limb, 512 elements, with over without | 0.99 to 1.02 | 0.96 to 1.15 (-O2), 0.99 to 1.01 (-O3) | 1.00 to 1.04 | 1.02 to 1.03 |
| `dot`, two limbs, 512 elements, with over without | 0.98 to 1.01 | 0.95 to 1.06 (-O2), 0.98 to 1.00 (-O3) | 1.00 | 1.00 to 1.01 |
| `add`, one limb, 512 elements, with over without | 1.00 to 1.01 (-O2), 0.98 to 1.04 (-O3) | 0.97 to 1.06 (-O2), 0.92 to 1.01 (-O3) | 1.02 to 1.03 | 1.03 to 1.04 |
| `add`, two limbs, 512 elements, with over without | 0.94 to 1.01 (-O2), 0.98 to 1.08 (-O3) | 0.95 to 1.06 (-O2), 0.93 to 1.01 (-O3) | 1.00 to 1.01 | 1.02 to 1.03 |
| `axpy`, two limbs, 512 elements, with over without | 1.00 to 1.07 (-O2), 0.99 to 1.00 (-O3) | 0.99 to 1.15 (-O2), 0.92 to 1.00 (-O3) | 1.00 to 1.02 | 0.99 to 1.03 |
| ball vectors: `add`, 1 limb, 4 entries, with over without | 1.09 to 1.19 (-O2), 0.97 to 1.10 (-O3) | 1.27 to 1.41 (-O2), 1.28 to 1.30 (-O3) | 1.24 (-O2), 1.40 (-O3) | 1.56 to 1.60 |
| ball vectors: `add`, 1 limb, 64 entries, with over without | 1.00 to 1.08 (-O2), 1.00 to 1.06 (-O3) | 0.90 to 1.20 (-O2), 1.03 to 1.05 (-O3) | 1.06 to 1.07 (-O2), 1.12 to 1.17 (-O3) | 1.19 to 1.20 (-O2), 1.13 to 1.18 (-O3) |
| ball vectors: `add`, 2 limbs, 4 entries, with over without | 1.02 to 1.06 (-O2), 1.00 to 1.02 (-O3) | 0.99 to 1.21 (-O2), 1.02 to 1.07 (-O3) | 1.13 to 1.14 (-O2), 1.26 (-O3) | 1.20 to 1.21 |
| ball vectors: `add`, 2 limbs, 64 entries, with over without | 1.00 to 1.01 (-O2), 0.93 to 1.01 (-O3) | 0.93 to 1.16 (-O2), 1.03 to 1.07 (-O3) | 1.07 to 1.10 | 1.07 to 1.09 |
| ball vectors: `scale`, 1 limb, 4 entries, with over without | 1.12 to 1.16 (-O2), 0.98 to 1.12 (-O3) | 1.17 to 1.36 (-O2), 1.14 to 1.24 (-O3) | 1.24 (-O2), 1.39 (-O3) | 1.59 to 1.63 (-O2), 1.58 to 1.62 (-O3) |
| ball vectors: `scale`, 1 limb, 64 entries, with over without | 1.00 to 1.10 (-O2), 0.97 to 1.01 (-O3) | 0.91 to 1.21 (-O2), 0.98 to 1.03 (-O3) | 1.09 to 1.12 | 1.19 (-O2), 0.97 to 1.20 (-O3) |
| ball vectors: `scale`, 2 limbs, 4 entries, with over without | 0.99 to 1.08 (-O2), 1.00 to 1.09 (-O3) | 0.97 to 1.21 (-O2), 1.10 to 1.16 (-O3) | 1.16 to 1.20 | 1.38 to 1.40 |
| ball vectors: `scale`, 2 limbs, 64 entries, with over without | 0.88 to 1.01 (-O2), 1.00 to 1.03 (-O3) | 0.93 to 1.17 (-O2), 0.99 to 1.01 (-O3) | 1.09 to 1.11 | 1.07 to 1.09 |
| ball vectors: `axpy`, 1 limb, 4 entries, with over without | 1.00 to 1.10 (-O2), 0.92 to 1.03 (-O3) | 0.96 to 1.17 (-O2), 1.10 to 1.17 (-O3) | 1.15 to 1.17 (-O2), 1.23 to 1.24 (-O3) | 1.13 to 1.19 (-O2), 1.13 to 1.18 (-O3) |
| ball vectors: `axpy`, 1 limb, 64 entries, with over without | 1.00 to 1.01 (-O2), 0.92 to 1.01 (-O3) | 0.91 to 1.20 (-O2), 0.89 to 0.98 (-O3) | 1.03 to 1.55 (-O2), 1.19 to 1.22 (-O3) | 1.13 to 1.16 (-O2), 1.05 to 1.09 (-O3) |
| ball vectors: `axpy`, 2 limbs, 4 entries, with over without | 0.92 to 1.02 (-O2), 0.99 to 1.01 (-O3) | 1.04 to 1.33 (-O2), 1.06 to 1.08 (-O3) | 1.21 to 1.23 | 1.10 to 1.13 |
| ball vectors: `axpy`, 2 limbs, 64 entries, with over without | 0.93 to 1.04 (-O2), 0.98 to 1.04 (-O3) | 1.00 to 1.12 (-O2), 1.03 to 1.12 (-O3) | 1.01 to 1.04 | 1.03 |
| ball vectors: `conv`, 1 limb, 4 entries, with over without | 0.99 to 1.01 (-O2), 0.89 to 1.01 (-O3) | 0.89 to 1.06 (-O2), 1.13 to 1.17 (-O3) | 1.11 to 1.15 (-O2), 1.21 (-O3) | 1.11 (-O2), 1.15 to 1.16 (-O3) |
| ball vectors: `conv`, 1 limb, 64 entries, with over without | 0.99 to 1.02 | 0.93 to 1.22 (-O2), 0.97 to 1.01 (-O3) | 0.99 to 1.00 (-O2), 1.12 to 1.14 (-O3) | 1.00 to 1.01 |
| ball vectors: `conv`, 2 limbs, 4 entries, with over without | 0.94 to 1.02 (-O2), 0.98 to 1.00 (-O3) | 0.92 to 1.15 (-O2), 0.94 to 1.00 (-O3) | 1.01 to 1.02 | 1.00 to 1.01 |
| ball vectors: `conv`, 2 limbs, 64 entries, with over without | 0.88 to 1.01 (-O2), 0.98 to 1.00 (-O3) | 0.92 to 1.06 (-O2), 0.92 to 1.00 (-O3) | 1.00 | 1.00 to 1.01 |
| ball vectors: `norm`, 1 limb, 4 entries, with over without | 1.05 to 1.08 (-O2), 0.94 to 1.05 (-O3) | 0.92 to 1.16 (-O2), 0.99 to 1.07 (-O3) | 0.60 to 1.92 (-O2), 2.25 (-O3) | 2.10 to 2.12 |
| ball vectors: `norm`, 1 limb, 64 entries, with over without | 1.01 to 1.03 (-O2), 1.00 to 1.06 (-O3) | 0.94 to 1.23 (-O2), 0.89 to 1.01 (-O3) | 0.91 to 1.27 (-O2), 1.17 to 1.18 (-O3) | 1.16 to 1.18 |
| ball vectors: `norm`, 2 limbs, 4 entries, with over without | 1.02 to 1.07 (-O2), 1.04 to 1.06 (-O3) | 1.03 to 1.30 (-O2), 1.16 to 1.21 (-O3) | 0.49 to 1.44 (-O2), 1.63 to 1.64 (-O3) | 1.41 to 1.42 |
| ball vectors: `norm`, 2 limbs, 64 entries, with over without | 0.90 to 1.03 (-O2), 0.98 to 1.01 (-O3) | 1.04 to 1.14 (-O2), 0.93 to 1.00 (-O3) | 1.14 to 1.15 (-O2), 1.19 to 1.20 (-O3) | 1.22 to 1.24 |

| The check at entry of a ball vector operation: ns per operation (with minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| ball vectors: `add`, 1 limb, 4 entries | 0.215 to 0.461 (-O2), -0.088 to 0.265 (-O3) | 0.671 to 0.929 (-O2), 0.628 to 0.702 (-O3) | 1.9 to 1.92 (-O2), 2.7 to 2.71 (-O3) | 3.03 to 3.16 |
| ball vectors: `add`, 1 limb, 64 entries | 0.08 to 2.04 (-O2), -0.03 to 1.52 (-O3) | -3.11 to 5.3 (-O2), 0.6 to 1.15 (-O3) | 1.54 to 1.6 (-O2), 2.3 to 2.98 (-O3) | 3.15 to 3.28 (-O2), 2.12 to 2.81 (-O3) |
| ball vectors: `add`, 2 limbs, 4 entries | 0.102 to 0.33 (-O2), -0.014 to 0.127 (-O3) | -0.084 to 1.36 (-O2), 0.105 to 0.302 (-O3) | 2.35 to 2.49 (-O2), 2.66 to 2.74 (-O3) | 1.77 to 1.82 (-O2), 1.75 to 1.86 (-O3) |
| ball vectors: `add`, 2 limbs, 64 entries | 0.19 to 0.65 (-O2), -4.69 to 0.9 (-O3) | -5.34 to 10.2 (-O2), 2.32 to 4.44 (-O3) | 5.27 to 6.01 (-O2), 7.13 to 7.69 (-O3) | 5.69 to 6.46 (-O2), 5.56 to 5.75 (-O3) |
| ball vectors: `scale`, 1 limb, 4 entries | 0.267 to 0.408 (-O2), -0.046 to 0.282 (-O3) | 0.443 to 0.846 (-O2), 0.372 to 0.559 (-O3) | 1.92 to 1.93 (-O2), 2.61 to 2.65 (-O3) | 3.17 to 3.28 (-O2), 3.1 to 3.28 (-O3) |
| ball vectors: `scale`, 1 limb, 64 entries | 0.03 to 2.23 (-O2), -0.77 to 0.18 (-O3) | -2.55 to 5.36 (-O2), -0.3 to 0.54 (-O3) | 2.26 to 2.6 (-O2), 2.01 to 2.2 (-O3) | 3.03 to 3.05 (-O2), -0.59 to 3.75 (-O3) |
| ball vectors: `scale`, 2 limbs, 4 entries | -0.039 to 0.287 (-O2), 0.012 to 0.304 (-O3) | -0.172 to 1.03 (-O2), 0.336 to 0.474 (-O3) | 2.39 to 2.56 (-O2), 1.7 to 1.71 (-O3) | 2.5 to 2.61 |
| ball vectors: `scale`, 2 limbs, 64 entries | -4.57 to 0.35 (-O2), -0.08 to 1.07 (-O3) | -2.66 to 5.65 (-O2), -0.37 to 0.16 (-O3) | 3.69 to 4.15 (-O2), 3.98 to 4.11 (-O3) | 2.32 to 2.56 (-O2), 2.85 to 2.88 (-O3) |
| ball vectors: `axpy`, 1 limb, 4 entries | -0.01 to 0.605 (-O2), -0.502 to 0.156 (-O3) | -0.232 to 0.806 (-O2), 0.536 to 0.826 (-O3) | 2.38 to 2.62 (-O2), 3.15 to 3.27 (-O3) | 1.66 to 2.38 (-O2), 1.63 to 2.18 (-O3) |
| ball vectors: `axpy`, 1 limb, 64 entries | 0.14 to 0.26 (-O2), -4.21 to 0.42 (-O3) | -5.26 to 10.5 (-O2), -5.31 to -0.87 (-O3) | 1.28 to 26.9 (-O2), 6.71 to 7.67 (-O3) | 4.12 to 4.88 (-O2), 1.61 to 2.94 (-O3) |
| ball vectors: `axpy`, 2 limbs, 4 entries | -0.819 to 0.19 (-O2), -0.101 to 0.137 (-O3) | 0.53 to 3.67 (-O2), 0.525 to 0.677 (-O3) | 7.51 to 7.82 (-O2), 4.11 to 4.38 (-O3) | 1.82 to 2.39 (-O2), 2.29 to 2.35 (-O3) |
| ball vectors: `axpy`, 2 limbs, 64 entries | -7.7 to 3.51 (-O2), -1.97 to 4.5 (-O3) | -0.4 to 11.5 (-O2), 3.5 to 11.5 (-O3) | 4 to 4.9 (-O2), 1.7 to 2.1 (-O3) | 3.3 to 3.7 (-O2), 3.1 to 3.6 (-O3) |
| ball vectors: `conv`, 1 limb, 4 entries | -0.049 to 0.053 (-O2), -0.969 to 0.052 (-O3) | -2.19 to 1.18 (-O2), 0.842 to 1.08 (-O3) | 3.35 to 4.3 (-O2), 5.29 to 5.32 (-O3) | 4.06 to 4.23 (-O2), 2.63 to 2.85 (-O3) |
| ball vectors: `conv`, 1 limb, 64 entries | -20 to 5 (-O2), -5 to 44 (-O3) | -148 to 406 (-O2), -53 to 20 (-O3) | -25 to -7 (-O2), 455 to 543 (-O3) | 11 to 21 (-O2), 1 to 20 (-O3) |
| ball vectors: `conv`, 2 limbs, 4 entries | -3.93 to 0.85 (-O2), -0.86 to 0.05 (-O3) | -5.08 to 8.06 (-O2), -3.56 to 0.2 (-O3) | 1.9 to 2.5 (-O2), 1 to 1.5 (-O3) | -0.5 to 1.1 (-O2), 0.5 to 1.3 (-O3) |
| ball vectors: `conv`, 2 limbs, 64 entries | -3.76e+03 to 410 (-O2), -540 to 140 (-O3) | -2.52e+03 to 1490 (-O2), -2.51e+03 to -30 (-O3) | -70 to 70 (-O2), -190 to -40 (-O3) | 10 to 190 (-O2), -40 to 360 (-O3) |
| ball vectors: `norm`, 1 limb, 4 entries | 0.103 to 0.168 (-O2), -0.124 to 0.11 (-O3) | -0.148 to 0.262 (-O2), -0.011 to 0.109 (-O3) | -5.65 to 4.08 (-O2), 4.69 to 4.71 (-O3) | 4.45 to 4.5 |
| ball vectors: `norm`, 1 limb, 64 entries | 0.22 to 0.61 (-O2), -0.08 to 1.22 (-O3) | -1.37 to 4.61 (-O2), -2.54 to 0.1 (-O3) | -1.64 to 3.46 (-O2), 2.01 to 2.12 (-O3) | 2.13 to 2.28 (-O2), 2 to 2.21 (-O3) |
| ball vectors: `norm`, 2 limbs, 4 entries | 0.056 to 0.174 (-O2), 0.096 to 0.17 (-O3) | 0.058 to 0.525 (-O2), 0.32 to 0.37 (-O3) | -9.74 to 2.91 (-O2), 3.52 to 3.55 (-O3) | 2.74 to 2.79 |
| ball vectors: `norm`, 2 limbs, 64 entries | -2.43 to 0.52 (-O2), -0.36 to 0.26 (-O3) | 0.94 to 3 (-O2), -1.73 to -0.05 (-O3) | 2.75 to 3.02 (-O2), 2.56 to 2.69 (-O3) | 2.82 to 2.9 (-O2), 2.78 to 2.98 (-O3) |

| The check at entry is under 5%; 1% of the call from n = | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `sum`, one limb, independent | > 1024; > 1024 (-O2), 8; 64 (-O3) | > 1024; > 1024 (-O2), 8; 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) |
| `sum`, two limbs, independent | > 1024; > 1024 (-O2), 16; > 1024 (-O3) | > 1024; > 1024 (-O2), 8; 64 (-O3) | 16; 1024 (-O2), 4; 64 (-O3) | 8; 64 (-O2), 8; 64 (-O3) |
| `dot`, one limb, independent | 64; 1024 (-O2), > 1024; > 1024 (-O3) | > 1024; > 1024 (-O2), 64; 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) | 1024; > 1024 (-O2), 1024; > 1024 (-O3) |
| `dot`, two limbs, independent | 1; > 1024 (-O2), > 1024; > 1024 (-O3) | > 1024; > 1024 (-O2), 64; 1024 (-O3) | 4; 1024 (-O2), 4; 64 (-O3) | 4; 1024 (-O2), 4; 1024 (-O3) |
| `sum`, one limb, dependent | 16; > 1024 (-O2), 4; > 1024 (-O3) | > 1024; > 1024 (-O2), 4; 64 (-O3) | 2; 64 (-O2), 4; 64 (-O3) | 1; 1024 (-O2), 1; 64 (-O3) |
| `sum`, two limbs, dependent | 8; > 1024 (-O2), 64; 1024 (-O3) | > 1024; > 1024 (-O2), 1; 64 (-O3) | 1; 4 (-O2), 1; 16 (-O3) | 1; 4 (-O2), 1; 8 (-O3) |
| `dot`, one limb, dependent | 16; 1024 (-O2), 64; > 1024 (-O3) | > 1024; > 1024 (-O2), 2; 2 (-O3) | 1; 16 (-O2), 1; 8 (-O3) | 1; 64 (-O2), 1; 64 (-O3) |
| `dot`, two limbs, dependent | 64; > 1024 (-O2), > 1024; > 1024 (-O3) | > 1024; > 1024 (-O2), 1; 1024 (-O3) | 2; 4 (-O2), 1; 1 (-O3) | 4; 4 (-O2), 4; 4 (-O3) |

| Short ball vectors, one operation per unit, many vectors: ns per operation, with the check | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 2.6 to 3.33 (-O2), 2.61 to 3.26 (-O3) | 3.37 to 3.94 (-O2), 3.45 to 4.13 (-O3) | 11.1 to 11.3 (-O2), 9.95 to 9.97 (-O3) | 8.42 to 8.49 |
| `add(x, y, z)`, 1 limb, N = 7 | 3.27 to 4.19 (-O2), 3.28 to 4.19 (-O3) | 4.92 to 5.57 (-O2), 4.15 to 5.03 (-O3) | 12.5 (-O2), 11.4 to 11.5 (-O3) | 9.45 to 9.56 |
| `add(x, y, z)`, 1 limb, N = 13 | 5.02 to 6.4 (-O2), 5.03 to 6.07 (-O3) | 5.88 to 6.53 (-O2), 5.35 to 6.46 (-O3) | 12.4 to 12.6 (-O2), 11.4 to 11.6 (-O3) | 9.59 to 9.67 |
| `add(x, y, z)`, 1 limb, N = 18 | 6.38 to 8.72 (-O2), 6.78 to 7.69 (-O3) | 7.24 to 8.48 (-O2), 6.55 to 7.8 (-O3) | 14.2 to 14.5 (-O2), 12.8 to 13 (-O3) | 10.6 to 10.7 |
| `add(x, y, z)`, 1 limb, N = 80 | 31.9 to 40.6 (-O2), 31.4 to 40 (-O3) | 34.5 to 41.1 (-O2), 32.9 to 39.5 (-O3) | 27.4 to 27.5 (-O2), 25.3 to 25.5 (-O3) | 22 to 22.2 (-O2), 20 to 20.1 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | 5.27 to 6.71 (-O2), 5.27 to 6.35 (-O3) | 6.78 to 7.94 (-O2), 5.82 to 7.02 (-O3) | 26.9 to 27 (-O2), 19.6 to 19.7 (-O3) | 17.3 to 17.5 |
| `add(x, y, z)`, 2 limbs, N = 7 | 9.64 to 12.4 (-O2), 9.45 to 11.3 (-O3) | 10.3 to 13 (-O2), 10.3 to 12.4 (-O3) | 31.6 to 31.8 (-O2), 25.7 to 25.8 (-O3) | 22.1 to 22.3 |
| `add(x, y, z)`, 2 limbs, N = 13 | 15.9 to 20.3 (-O2), 15.5 to 19.9 (-O3) | 16.6 to 19.9 (-O2), 17.1 to 20.5 (-O3) | 30.7 to 30.8 (-O2), 25.3 to 25.4 (-O3) | 23.3 to 23.4 |
| `add(x, y, z)`, 2 limbs, N = 18 | 20.9 to 26.7 (-O2), 20.3 to 25.1 (-O3) | 21.7 to 25.6 (-O2), 21.8 to 26.2 (-O3) | 40 to 40.2 (-O2), 36.7 to 37 (-O3) | 34.3 to 34.6 |
| `add(x, y, z)`, 2 limbs, N = 80 | 81.4 to 104 (-O2), 80.6 to 96.4 (-O3) | 86.2 to 98.6 (-O2), 87.5 to 105 (-O3) | 101 to 102 (-O2), 95.8 to 96 (-O3) | 94.9 to 95.9 |
| `z = x + y`, 1 limb, N = 3 | 2.61 to 3.31 (-O2), 2.61 to 3.35 (-O3) | 3 to 3.59 (-O2), 3.67 to 4.39 (-O3) | 17.1 to 17.8 (-O2), 16 to 16.9 (-O3) | 8.51 to 8.57 |
| `z = x + y`, 1 limb, N = 7 | 3.69 to 4.71 (-O2), 3.68 to 4.73 (-O3) | 4.67 to 5.5 (-O2), 4.71 to 5.71 (-O3) | 17.6 to 18.3 (-O2), 16.9 to 17.8 (-O3) | 9.71 to 9.81 |
| `z = x + y`, 1 limb, N = 13 | 7.58 to 9.73 (-O2), 7.53 to 9.06 (-O3) | 7.76 to 8.66 (-O2), 6.52 to 7.83 (-O3) | 16.9 to 17.4 | 10.1 to 10.2 |
| `z = x + y`, 1 limb, N = 18 | 10.2 to 13 (-O2), 9.71 to 12.4 (-O3) | 12.9 to 14.7 (-O2), 9.45 to 11.3 (-O3) | 17.8 to 18.6 | 11.6 to 11.9 |
| `z = x + y`, 1 limb, N = 80 | 42.2 to 55 (-O2), 43.8 to 55.9 (-O3) | 50.3 to 61.8 (-O2), 48.5 to 56.2 (-O3) | 85.3 to 87.8 | 35.8 to 40.2 (-O2), 40.5 to 43.7 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 5.84 to 7.46 (-O2), 5.74 to 7.4 (-O3) | 9.12 to 10.1 (-O2), 6.45 to 7.76 (-O3) | 30.5 to 30.7 (-O2), 22.7 to 22.9 (-O3) | 18.7 to 20.9 (-O2), 20.4 to 20.6 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 10.9 to 13.9 (-O2), 10.8 to 13.5 (-O3) | 12.9 to 15.2 (-O2), 11.1 to 13.4 (-O3) | 35.6 to 35.9 (-O2), 28.5 to 28.7 (-O3) | 25.3 to 27.2 (-O2), 27.1 to 27.5 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 17.9 to 24.5 (-O2), 18 to 22.6 (-O3) | 19.3 to 23.2 (-O2), 19.8 to 23.7 (-O3) | 50.5 to 50.9 (-O2), 29 to 29.2 (-O3) | 26.7 to 28.4 (-O2), 28.4 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 24.3 to 30.9 (-O2), 23.9 to 30.4 (-O3) | 28.5 to 31.3 (-O2), 27 to 33.1 (-O3) | 63.3 to 63.5 (-O2), 55.5 to 55.8 (-O3) | 39.7 to 42 (-O2), 41.3 to 41.9 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 109 to 140 (-O2), 110 to 140 (-O3) | 123 to 135 (-O2), 119 to 143 (-O3) | 168 to 174 (-O2), 161 to 164 (-O3) | 131 to 136 |
| `sub`, 1 limb, N = 3 | 2.6 to 3.32 (-O2), 2.6 to 3.32 (-O3) | 3.06 to 3.95 (-O2), 3.61 to 4 (-O3) | 11 to 11.2 (-O2), 9.95 to 9.96 (-O3) | 8.44 to 8.5 |
| `sub`, 1 limb, N = 7 | 3.35 to 4.17 (-O2), 3.28 to 4.18 (-O3) | 4.46 to 5.75 (-O2), 4.2 to 5.03 (-O3) | 12.3 to 12.5 (-O2), 11.4 (-O3) | 9.38 to 9.47 |
| `sub`, 1 limb, N = 13 | 5.19 to 6.47 (-O2), 5.05 to 6.46 (-O3) | 6.67 to 8.29 (-O2), 5.28 to 5.97 (-O3) | 12.4 to 13.5 (-O2), 11.3 to 11.4 (-O3) | 9.67 to 9.75 |
| `sub`, 1 limb, N = 18 | 6.5 to 8.22 (-O2), 6.68 to 8.15 (-O3) | 6.7 to 8.48 (-O2), 6.47 to 7.29 (-O3) | 14.2 to 14.3 (-O2), 12.7 to 12.9 (-O3) | 10.5 to 10.6 |
| `sub`, 1 limb, N = 80 | 32.3 to 41.5 (-O2), 31.2 to 39.4 (-O3) | 33.9 to 43.7 (-O2), 32.6 to 39.5 (-O3) | 26.4 to 26.6 (-O2), 25.2 to 25.4 (-O3) | 21.9 to 22 (-O2), 20 to 20.2 (-O3) |
| `sub`, 2 limbs, N = 3 | 5.58 to 7.13 (-O2), 5.77 to 7.35 (-O3) | 6.67 to 8.16 (-O2), 6.08 to 7.31 (-O3) | 27.3 (-O2), 19.9 (-O3) | 18 to 18.2 |
| `sub`, 2 limbs, N = 7 | 10.4 to 13.2 (-O2), 10.4 to 13.3 (-O3) | 10.8 to 12.9 (-O2), 11 to 13.2 (-O3) | 32.1 to 32.4 (-O2), 26.7 (-O3) | 24.1 to 24.3 |
| `sub`, 2 limbs, N = 13 | 17 to 21.7 (-O2), 17 to 21.4 (-O3) | 17.2 to 20.9 (-O2), 18 to 21.7 (-O3) | 31 (-O2), 25.4 to 25.5 (-O3) | 24.3 to 24.5 |
| `sub`, 2 limbs, N = 18 | 22.2 to 28.3 (-O2), 21.4 to 27.4 (-O3) | 22.1 to 26.8 (-O2), 23.7 to 28 (-O3) | 40.3 to 40.4 (-O2), 37 to 37.1 (-O3) | 35.1 to 35.8 |
| `sub`, 2 limbs, N = 80 | 85.5 to 117 (-O2), 85.2 to 109 (-O3) | 94.2 to 104 (-O2), 93 to 112 (-O3) | 103 to 104 (-O2), 97.9 to 98.4 (-O3) | 97.1 to 98.3 |
| `scale`, 1 limb, N = 3 | 2.57 to 3.28 (-O2), 2.5 to 3.27 (-O3) | 3.37 to 3.71 (-O2), 3.32 to 3.99 (-O3) | 11.3 to 11.4 (-O2), 10.1 (-O3) | 8.42 to 8.49 |
| `scale`, 1 limb, N = 7 | 3.23 to 4.05 (-O2), 3.13 to 4.06 (-O3) | 4.52 to 5.41 (-O2), 3.87 to 4.68 (-O3) | 12.4 (-O2), 11.5 to 11.6 (-O3) | 9.38 to 9.5 |
| `scale`, 1 limb, N = 13 | 4.47 to 5.69 (-O2), 4.47 to 5.7 (-O3) | 5.79 to 6.47 (-O2), 5.19 to 5.81 (-O3) | 12.7 (-O2), 11.7 (-O3) | 9.53 to 9.61 |
| `scale`, 1 limb, N = 18 | 5.93 to 7.57 (-O2), 5.88 to 7.97 (-O3) | 7.12 to 7.84 (-O2), 6.78 to 7.59 (-O3) | 13.9 to 14.1 (-O2), 12.9 to 13.1 (-O3) | 10.5 to 10.7 |
| `scale`, 1 limb, N = 80 | 30.3 to 38 (-O2), 28.3 to 36.1 (-O3) | 31.6 to 40.2 (-O2), 30.1 to 36 (-O3) | 27.9 to 28 (-O2), 26.2 to 26.4 (-O3) | 20.2 to 20.3 (-O2), 27.6 to 28.1 (-O3) |
| `scale`, 2 limbs, N = 3 | 3.37 to 4.04 (-O2), 3.31 to 4.23 (-O3) | 5.14 to 6.4 (-O2), 3.87 to 4.65 (-O3) | 19.7 (-O2), 12 to 12.1 (-O3) | 9.97 to 10.1 |
| `scale`, 2 limbs, N = 7 | 5.39 to 6.23 (-O2), 5.17 to 6.6 (-O3) | 6.65 to 7.96 (-O2), 5.8 to 6.97 (-O3) | 22.2 (-O2), 15.9 (-O3) | 13.6 to 13.7 |
| `scale`, 2 limbs, N = 13 | 8.06 to 10.2 (-O2), 7.61 to 10 (-O3) | 9.64 to 11.5 (-O2), 9.03 to 10.5 (-O3) | 22.4 to 22.5 (-O2), 15.9 (-O3) | 13.8 to 13.9 |
| `scale`, 2 limbs, N = 18 | 10.3 to 13.1 (-O2), 10.2 to 13 (-O3) | 11.7 to 14.4 (-O2), 11.3 to 13.5 (-O3) | 25.4 to 25.5 (-O2), 19.3 to 19.4 (-O3) | 16.2 to 16.3 |
| `scale`, 2 limbs, N = 80 | 42.4 to 52.8 (-O2), 42.2 to 54.3 (-O3) | 42.3 to 50.7 (-O2), 46.1 to 55.4 (-O3) | 53.5 to 54.6 (-O2), 47.8 to 48 (-O3) | 43.7 to 44.5 |
| `half`, 1 limb, N = 3 | 3.69 to 4.98 (-O2), 3.69 to 4.7 (-O3) | 5.5 to 6.06 (-O2), 3.53 to 4.24 (-O3) | 19.7 to 19.8 (-O2), 12.6 (-O3) | 12.1 to 12.2 |
| `half`, 1 limb, N = 7 | 5.08 to 6.47 (-O2), 5.08 to 6.47 (-O3) | 5.92 to 7.16 (-O2), 5.14 to 6.18 (-O3) | 21.1 to 21.2 (-O2), 15.6 (-O3) | 14.1 to 14.3 |
| `half`, 1 limb, N = 13 | 7.52 to 9.58 (-O2), 7.47 to 9.52 (-O3) | 8.61 to 9.47 (-O2), 7.41 to 8.91 (-O3) | 20 to 20.3 (-O2), 14.2 to 14.3 (-O3) | 14.1 to 14.3 |
| `half`, 1 limb, N = 18 | 9.13 to 12.5 (-O2), 9.07 to 11.6 (-O3) | 10.1 to 11.5 (-O2), 9.35 to 11.2 (-O3) | 22.8 to 22.9 (-O2), 17.9 to 18 (-O3) | 17.1 to 17.3 |
| `half`, 1 limb, N = 80 | 36 to 47.7 (-O2), 35 to 46.1 (-O3) | 41.4 to 47.5 (-O2), 40.3 to 48.4 (-O3) | 39.4 to 39.6 (-O2), 35.1 to 35.3 (-O3) | 36.2 to 36.4 |
| `half`, 2 limbs, N = 3 | 4.51 to 6.16 (-O2), 4.5 to 5.73 (-O3) | 6.11 to 6.73 (-O2), 4.47 to 5.35 (-O3) | 23.4 to 23.5 (-O2), 17.5 to 17.6 (-O3) | 14.7 to 14.8 |
| `half`, 2 limbs, N = 7 | 7.49 to 10.2 (-O2), 7.45 to 9.48 (-O3) | 8.26 to 9.87 (-O2), 7.34 to 8.82 (-O3) | 26.6 to 26.7 (-O2), 22.7 to 22.8 (-O3) | 18.6 to 18.7 |
| `half`, 2 limbs, N = 13 | 11.2 to 14.1 (-O2), 11.1 to 14 (-O3) | 11.6 to 13.9 (-O2), 11.4 to 13.7 (-O3) | 24.9 to 25 (-O2), 19.9 (-O3) | 19 to 19.2 |
| `half`, 2 limbs, N = 18 | 13.8 to 17.7 (-O2), 13.8 to 17.7 (-O3) | 14.9 to 17 (-O2), 14.2 to 17.1 (-O3) | 29.9 to 30 (-O2), 24.9 (-O3) | 22.7 to 23.2 |
| `half`, 2 limbs, N = 80 | 51.1 to 65.2 (-O2), 50.1 to 64.8 (-O3) | 52.3 to 61.6 (-O2), 57.1 to 68.6 (-O3) | 60.3 to 60.9 (-O2), 54.4 to 55 (-O3) | 55.2 to 55.6 |
| the constructor, 1 limb, N = 3 | 5.61 to 7.52 (-O2), 6.86 to 7.85 (-O3) | 4.9 to 5.39 (-O2), 3.49 to 4.23 (-O3) | 16.8 to 17.5 | 24.2 to 24.6 |
| the constructor, 1 limb, N = 7 | 21.5 to 22.6 (-O2), 19.1 to 21.4 (-O3) | 9.91 to 11.9 (-O2), 5.48 to 6.58 (-O3) | 19.1 to 19.2 (-O2), 17.8 (-O3) | 26.9 to 28.1 (-O2), 26.9 to 28.8 (-O3) |
| the constructor, 1 limb, N = 13 | 27 to 33.6 (-O2), 25.8 to 34.4 (-O3) | 18.5 to 22.2 (-O2), 8.85 to 10.6 (-O3) | 24.1 to 24.2 (-O2), 22 to 22.1 (-O3) | 33 to 33.4 |
| the constructor, 1 limb, N = 18 | 19.7 to 25.4 (-O2), 28.1 to 33 (-O3) | 25.9 to 30.9 (-O2), 29.7 to 35.4 (-O3) | 28.9 to 29.9 | 24.5 to 25 (-O2), 36.1 to 37.1 (-O3) |
| the constructor, 1 limb, N = 80 | 72.4 to 93.3 (-O2), 76.7 to 97.7 (-O3) | 238 to 281 (-O2), 251 to 281 (-O3) | 145 to 151 | 71.3 to 72.6 |
| the constructor, 2 limbs, N = 3 | 7.61 to 16.2 (-O2), 9.69 to 18 (-O3) | 4.5 to 5.26 (-O2), 4.73 to 5.69 (-O3) | 16 to 16.3 | 11.2 to 16.1 (-O2), 16 (-O3) |
| the constructor, 2 limbs, N = 7 | 21.3 to 27 (-O2), 21.8 to 25.8 (-O3) | 14.5 to 15.7 (-O2), 7.78 to 8.72 (-O3) | 20.1 to 20.6 (-O2), 18.8 to 19.7 (-O3) | 15.7 to 17.4 (-O2), 17.7 to 18 (-O3) |
| the constructor, 2 limbs, N = 13 | 25.2 to 32.5 (-O2), 25 to 32.1 (-O3) | 28.8 to 34.3 (-O2), 10.7 to 12 (-O3) | 39.1 to 39.2 (-O2), 22.5 to 22.9 (-O3) | 22.9 to 23.5 (-O2), 23.5 to 24.8 (-O3) |
| the constructor, 2 limbs, N = 18 | 24.3 to 31.4 (-O2), 22.1 to 29.2 (-O3) | 43.4 to 51.8 (-O2), 41.4 to 51.2 (-O3) | 48.9 to 49.1 (-O2), 31 to 31.1 (-O3) | 36 to 36.8 |
| the constructor, 2 limbs, N = 80 | 96.7 to 123 (-O2), 95.7 to 122 (-O3) | 317 to 365 (-O2), 324 to 362 (-O3) | 210 to 211 (-O2), 158 to 164 (-O3) | 106 to 108 |

| Short ball vectors, one operation per unit, many vectors: the check, ns per operation (with minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 0.221 to 0.287 (-O2), 0.238 to 0.41 (-O3) | 0.836 to 0.978 (-O2), 0.931 to 1.08 (-O3) | 2.01 to 2.24 (-O2), 4.26 to 4.31 (-O3) | 3.69 to 3.78 |
| `add(x, y, z)`, 1 limb, N = 7 | -0.002 to 0.24 (-O2), 0.134 to 0.429 (-O3) | 0.149 to 0.313 (-O2), 0.914 to 0.978 (-O3) | 2.02 to 2.07 (-O2), 2.25 to 2.39 (-O3) | 2.57 to 2.67 (-O2), 2.75 to 2.77 (-O3) |
| `add(x, y, z)`, 1 limb, N = 13 | 0.268 to 0.328 (-O2), 0.261 to 0.503 (-O3) | -0.086 to 0.25 (-O2), 0.484 to 0.895 (-O3) | 2.03 to 2.22 (-O2), 2.62 to 2.63 (-O3) | 2.4 to 2.53 (-O2), 2.47 to 2.53 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | -0.022 to 0.558 (-O2), -0.454 to 0.077 (-O3) | 0.146 to 0.52 (-O2), 0.31 to 0.694 (-O3) | 2.01 to 2.32 (-O2), 2.23 to 2.28 (-O3) | 2.33 to 2.57 (-O2), 2.37 to 2.5 (-O3) |
| `add(x, y, z)`, 1 limb, N = 80 | -2.73 to 0.09 (-O2), -0.01 to 2.23 (-O3) | -5.21 to -0.52 (-O2), -0.25 to 1.29 (-O3) | 1.84 to 2.03 (-O2), 2.68 to 3.61 (-O3) | 3.36 to 3.7 (-O2), 2.37 to 2.5 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | -0.404 to 0.036 (-O2), 0.113 to 0.172 (-O3) | -0.57 to -0.043 (-O2), 0.17 to 0.338 (-O3) | 2.72 to 2.87 (-O2), 2.78 to 2.91 (-O3) | 1.68 to 1.89 (-O2), 1.73 to 1.84 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | -0.489 to 0.09 (-O2), -0.182 to -0.08 (-O3) | -0.87 to 0.09 (-O2), -0.42 to 0.17 (-O3) | 2.33 to 2.66 (-O2), 2.59 to 2.89 (-O3) | 1.53 to 1.66 (-O2), 1.47 to 1.81 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | -0.98 to 0.19 (-O2), 0.01 to 1.11 (-O3) | -1.97 to 0.68 (-O2), 0.22 to 0.32 (-O3) | 2.77 to 2.87 (-O2), 2.48 to 2.65 (-O3) | 2.02 to 2.21 (-O2), 2.03 to 2.16 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -1.75 to 0.11 (-O2), 0.06 to 1.17 (-O3) | -2.37 to 0.91 (-O2), 0.03 to 0.25 (-O3) | 4.53 to 4.64 (-O2), 4.37 to 4.47 (-O3) | 4.02 to 4.28 (-O2), 3.98 to 4.36 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -4.96 to 1.4 (-O2), 0.25 to 0.56 (-O3) | -7.12 to 0.28 (-O2), -4.11 to 0.45 (-O3) | 4.21 to 5.42 (-O2), 2.37 to 3.66 (-O3) | 2.62 to 4.31 (-O2), 3.6 to 4.65 (-O3) |
| `z = x + y`, 1 limb, N = 3 | 0.061 to 0.15 (-O2), 0.152 to 0.22 (-O3) | 0.387 to 0.664 (-O2), 0.967 to 1.21 (-O3) | 5.46 to 6.12 (-O2), 5.34 to 7.18 (-O3) | 2.84 to 2.92 |
| `z = x + y`, 1 limb, N = 7 | -0.003 to 0.023 (-O2), -0.004 to 0.317 (-O3) | 0.196 to 0.582 (-O2), 0.963 to 1.03 (-O3) | 5.14 to 5.77 (-O2), 5.38 to 6.95 (-O3) | 2.4 to 2.47 |
| `z = x + y`, 1 limb, N = 13 | 2.08 to 2.73 (-O2), 2.03 to 2.42 (-O3) | 0.172 to 0.671 (-O2), 0.63 to 0.715 (-O3) | 4.48 to 4.58 (-O2), 5.6 to 5.74 (-O3) | 1.41 to 2.29 (-O2), 2.03 to 2.31 (-O3) |
| `z = x + y`, 1 limb, N = 18 | -0.01 to 0.56 (-O2), -0.835 to 0.73 (-O3) | 2.76 to 2.99 (-O2), 1.85 to 2.09 (-O3) | 3.59 to 3.82 (-O2), 4.67 to 5.13 (-O3) | 1.95 to 2.36 (-O2), 1.97 to 2.15 (-O3) |
| `z = x + y`, 1 limb, N = 80 | -1.33 to -0.76 (-O2), -0.16 to 3.11 (-O3) | -2.11 to 0.54 (-O2), 0.23 to 2.01 (-O3) | -0.71 to 1.74 (-O2), -0.52 to 3.87 (-O3) | -4.27 to -0.19 (-O2), -0.45 to 2.97 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -0.046 to 0.12 (-O2), -0.029 to 0.51 (-O3) | -0.39 to 0.237 (-O2), 0.052 to 0.519 (-O3) | 2.92 to 3.24 (-O2), 3.77 to 4.09 (-O3) | 1.12 to 4.28 (-O2), 2.54 to 2.98 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 0.23 to 0.39 (-O2), -0.01 to 0.06 (-O3) | -0.63 to -0.39 (-O2), -0.15 to 0.57 (-O3) | 2.42 to 2.79 (-O2), 2.84 to 3.24 (-O3) | 0.75 to 4.24 (-O2), 2.45 to 2.95 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | -0.73 to 1.58 (-O2), -0.41 to 0.01 (-O3) | -1.42 to -0.63 (-O2), 1.81 to 2.15 (-O3) | 2.27 to 3.04 (-O2), 2.36 to 3.07 (-O3) | 0.44 to 3.77 (-O2), 2.01 to 2.34 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -0.26 to 0.79 (-O2), -0.09 to 1.38 (-O3) | -2.88 to 0.2 (-O2), -0.39 to 0.14 (-O3) | 0.7 to 0.88 (-O2), 1.94 to 2.9 (-O3) | 1.73 to 5.06 (-O2), 2.82 to 3.52 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | -3.5 to 0.3 (-O2), 0.4 to 0.9 (-O3) | -8.5 to 1.1 (-O2), 0 to 0.2 (-O3) | 1.2 to 6.8 (-O2), -6.5 to 4.4 (-O3) | -3.5 to 1.9 (-O2), 1.4 to 5.9 (-O3) |
| `sub`, 1 limb, N = 3 | 0.269 to 0.381 (-O2), 0.268 to 0.328 (-O3) | 0.514 to 1.16 (-O2), 0.86 to 1.07 (-O3) | 1.95 to 2.17 (-O2), 4.21 to 4.31 (-O3) | 3.72 to 3.79 |
| `sub`, 1 limb, N = 7 | 0.136 to 0.268 (-O2), 0.181 to 0.233 (-O3) | -0.142 to 0.451 (-O2), 0.847 to 1.14 (-O3) | 1.84 to 1.96 (-O2), 2.25 to 2.4 (-O3) | 2.59 to 2.72 |
| `sub`, 1 limb, N = 13 | -0.011 to 0.43 (-O2), 0.069 to 0.314 (-O3) | 1.02 to 2.07 (-O2), 0.029 to 0.752 (-O3) | 1.92 to 3.07 (-O2), 2.27 to 2.52 (-O3) | 2.48 to 2.57 (-O2), 2.4 to 2.54 (-O3) |
| `sub`, 1 limb, N = 18 | -0.248 to 0.08 (-O2), -0.205 to 0.051 (-O3) | -0.156 to 0.862 (-O2), -0.287 to 0.701 (-O3) | 2.1 to 2.3 (-O2), 2.02 to 2.36 (-O3) | 2.29 to 2.4 |
| `sub`, 1 limb, N = 80 | -0.34 to 1.03 (-O2), -1.17 to 0.09 (-O3) | -3.86 to -0.26 (-O2), -0.92 to -0.15 (-O3) | 1.27 to 1.65 (-O2), 2.94 to 3.4 (-O3) | 3.42 to 3.68 (-O2), 2.23 to 2.61 (-O3) |
| `sub`, 2 limbs, N = 3 | -0.03 to 0.166 (-O2), 0.114 to 0.134 (-O3) | -0.532 to 0.099 (-O2), -0.02 to 0.558 (-O3) | 2.72 to 2.78 (-O2), 2.65 to 2.97 (-O3) | 1.88 to 2.02 (-O2), 1.98 to 2.15 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.21 to -0.07 (-O2), -0.25 to 0.03 (-O3) | -0.83 to 0.11 (-O2), -0.36 to 0.76 (-O3) | 2.07 to 2.33 (-O2), 2.44 to 2.88 (-O3) | 2.6 to 2.77 (-O2), 2.61 to 2.75 (-O3) |
| `sub`, 2 limbs, N = 13 | -0.79 to -0.05 (-O2), -0.25 to -0.01 (-O3) | -1.63 to 0.18 (-O2), -0.98 to 0.36 (-O3) | 2.53 to 2.57 (-O2), 2.28 to 2.54 (-O3) | 2.57 to 2.68 (-O2), 2.38 to 2.55 (-O3) |
| `sub`, 2 limbs, N = 18 | -0.23 to 0.7 (-O2), -0.09 to 0.07 (-O3) | -2.12 to 0.14 (-O2), -1.15 to 1.51 (-O3) | 3.88 to 4.15 (-O2), 3.79 to 4.21 (-O3) | 4.22 to 4.48 (-O2), 4.25 to 4.66 (-O3) |
| `sub`, 2 limbs, N = 80 | 0.17 to 7.9 (-O2), 0 to 1.94 (-O3) | -6.5 to 0.67 (-O2), -5.67 to 4.37 (-O3) | 3.78 to 5.27 (-O2), 1.19 to 3.62 (-O3) | 3.84 to 4.14 (-O2), 3.96 to 5.25 (-O3) |
| `scale`, 1 limb, N = 3 | 0.191 to 0.343 (-O2), 0.198 to 0.338 (-O3) | 0.654 to 0.796 (-O2), 0.509 to 0.774 (-O3) | 2.42 to 2.45 (-O2), 4.03 to 4.13 (-O3) | 3.87 to 3.95 |
| `scale`, 1 limb, N = 7 | -0.187 to 0.155 (-O2), 0.114 to 0.207 (-O3) | -0.084 to 0.402 (-O2), 0.368 to 0.68 (-O3) | 1.81 to 1.85 (-O2), 2.39 to 2.59 (-O3) | 2.61 to 2.67 (-O2), 2.64 to 2.75 (-O3) |
| `scale`, 1 limb, N = 13 | -0.076 to 0.107 (-O2), 0.002 to 0.086 (-O3) | -0.057 to 0.308 (-O2), 0.203 to 0.703 (-O3) | 2.35 to 2.48 (-O2), 2.52 to 2.62 (-O3) | 2.44 to 2.51 |
| `scale`, 1 limb, N = 18 | -0.126 to 0.101 (-O2), 0.064 to 0.509 (-O3) | -0.12 to 0.345 (-O2), 0.317 to 0.728 (-O3) | 1.83 to 2.13 (-O2), 2.07 to 2.15 (-O3) | 2.61 to 2.67 (-O2), 2.61 to 2.76 (-O3) |
| `scale`, 1 limb, N = 80 | -3.18 to 0.7 (-O2), 0.18 to 0.25 (-O3) | -2.25 to 0.54 (-O2), -0.29 to 1.62 (-O3) | 1.35 to 1.65 (-O2), 1.5 to 1.78 (-O3) | 2.58 to 2.86 (-O2), 4.24 to 5.34 (-O3) |
| `scale`, 2 limbs, N = 3 | -0.51 to 0.066 (-O2), 0.087 to 0.111 (-O3) | -0.016 to 0.717 (-O2), 0.568 to 0.668 (-O3) | 2.93 to 2.95 (-O2), 2.43 to 2.52 (-O3) | 2.59 to 2.63 (-O2), 2.45 to 2.55 (-O3) |
| `scale`, 2 limbs, N = 7 | -0.497 to 0.5 (-O2), 0.272 to 0.386 (-O3) | -0.452 to 0.137 (-O2), 0.123 to 0.677 (-O3) | 2.93 to 3.02 (-O2), 1.96 to 2.2 (-O3) | 2.75 to 2.83 (-O2), 2.73 to 2.88 (-O3) |
| `scale`, 2 limbs, N = 13 | -0.15 to 0.488 (-O2), -0.587 to 0.368 (-O3) | -0.029 to 0.17 (-O2), 0.36 to 0.96 (-O3) | 2.83 to 2.85 (-O2), 2.31 to 2.47 (-O3) | 2.82 to 2.98 (-O2), 2.84 to 2.96 (-O3) |
| `scale`, 2 limbs, N = 18 | -0.62 to 0.1 (-O2), -0.23 to -0.07 (-O3) | -0.49 to 1.01 (-O2), 0.2 to 0.69 (-O3) | 2.89 to 3.02 (-O2), 2.2 to 2.3 (-O3) | 1.62 to 1.84 (-O2), 1.66 to 1.81 (-O3) |
| `scale`, 2 limbs, N = 80 | -4.44 to 0.49 (-O2), -0.26 to 0.4 (-O3) | -3.67 to 0.04 (-O2), 0.44 to 0.66 (-O3) | 3 to 4.19 (-O2), 0.24 to 0.67 (-O3) | 1.51 to 1.89 (-O2), 0.99 to 1.85 (-O3) |
| `half`, 1 limb, N = 3 | 0.307 to 0.346 (-O2), 0.22 to 0.645 (-O3) | 0.305 to 0.332 (-O2), 0.321 to 0.473 (-O3) | 2.5 to 2.58 (-O2), 3.91 to 4.03 (-O3) | 3.37 to 3.43 (-O2), 3.26 to 3.35 (-O3) |
| `half`, 1 limb, N = 7 | -0.006 to 0.34 (-O2), 0.311 to 0.766 (-O3) | -0.214 to 0.398 (-O2), 0.33 to 0.389 (-O3) | 2.2 to 2.25 (-O2), 2.62 to 2.86 (-O3) | 2.24 to 2.29 (-O2), 2.34 to 2.41 (-O3) |
| `half`, 1 limb, N = 13 | -0.028 to 0.237 (-O2), 0.132 to 0.739 (-O3) | -0.483 to 0.156 (-O2), 0.334 to 0.398 (-O3) | 2.52 to 2.88 (-O2), 1.89 to 2.07 (-O3) | 2.08 to 2.14 (-O2), 2.11 to 2.24 (-O3) |
| `half`, 1 limb, N = 18 | 0.336 to 1.63 (-O2), 0.285 to 1.02 (-O3) | -0.11 to 0.32 (-O2), 0.637 to 1.3 (-O3) | 2.5 to 2.65 (-O2), 2.81 to 3.19 (-O3) | 3.53 to 3.61 (-O2), 3.33 to 3.63 (-O3) |
| `half`, 1 limb, N = 80 | -0.22 to 1.61 (-O2), -1.39 to 2.59 (-O3) | 0 to 1.17 (-O2), -0.54 to 1.2 (-O3) | 3.68 to 3.84 (-O2), 4.11 to 4.46 (-O3) | 5.01 to 5.22 (-O2), 5.45 to 5.83 (-O3) |
| `half`, 2 limbs, N = 3 | 0.064 to 0.708 (-O2), 0.246 to 0.616 (-O3) | 0.305 to 0.335 (-O2), 0.551 to 0.86 (-O3) | 2.28 to 2.39 (-O2), 3.49 to 3.7 (-O3) | 2.14 to 2.24 (-O2), 2.03 to 2.29 (-O3) |
| `half`, 2 limbs, N = 7 | 0.115 to 0.937 (-O2), 0.148 to 0.736 (-O3) | -0.416 to 0.312 (-O2), 0.453 to 0.511 (-O3) | 1.12 to 1.25 (-O2), 2.78 to 2.96 (-O3) | 2.47 to 2.65 (-O2), 2.52 to 2.74 (-O3) |
| `half`, 2 limbs, N = 13 | -0.21 to 0.32 (-O2), 0.19 to 0.88 (-O3) | -0.71 to 0.34 (-O2), -0.09 to 0.74 (-O3) | 1.6 to 1.78 (-O2), 3.33 to 3.53 (-O3) | 2.57 to 2.71 (-O2), 2.63 to 2.91 (-O3) |
| `half`, 2 limbs, N = 18 | -0.48 to 0.2 (-O2), 0.19 to 1.27 (-O3) | -0.38 to 0.16 (-O2), 0.02 to 0.2 (-O3) | 1.11 to 1.14 (-O2), 2.66 to 2.92 (-O3) | 2.48 to 2.73 (-O2), 2.61 to 2.94 (-O3) |
| `half`, 2 limbs, N = 80 | -1.88 to 0.2 (-O2), -0.59 to 3.95 (-O3) | -3.31 to 0.44 (-O2), 0.43 to 0.53 (-O3) | 3.57 to 4.22 (-O2), 3.39 to 4.44 (-O3) | 4.78 to 5.5 (-O2), 4.71 to 5.07 (-O3) |
| the constructor, 1 limb, N = 3 | 2.21 to 3.29 (-O2), 3.15 to 4.44 (-O3) | 1.07 to 1.26 (-O2), 0.617 to 0.987 (-O3) | 5.6 to 6.62 (-O2), 5.95 to 7.52 (-O3) | 18.2 to 18.6 |
| the constructor, 1 limb, N = 7 | -1.23 to 0.81 (-O2), -2.38 to -1.33 (-O3) | -9.37 to -4.54 (-O2), 1.25 to 1.69 (-O3) | 4.63 to 4.88 (-O2), 5.01 to 5.3 (-O3) | -0.14 to 1.22 (-O2), -1.31 to 1.79 (-O3) |
| the constructor, 1 limb, N = 13 | -1.22 to 1.48 (-O2), -0.54 to 2.53 (-O3) | -2.07 to -0.16 (-O2), 1.41 to 1.71 (-O3) | 2.22 to 2.72 (-O2), 2.99 to 3.31 (-O3) | -0.4 to 0.23 (-O2), -0.39 to 0.32 (-O3) |
| the constructor, 1 limb, N = 18 | -2.72 to -1.14 (-O2), -0.8 to -0.23 (-O3) | -2.28 to 0.17 (-O2), 0.61 to 0.74 (-O3) | 2.23 to 3.15 (-O2), 2.48 to 3.18 (-O3) | -0.91 to -0.61 (-O2), 0.78 to 2.27 (-O3) |
| the constructor, 1 limb, N = 80 | -2.39 to -0.75 (-O2), -0.51 to 5.64 (-O3) | -2.1 to 3 (-O2), -13.5 to 0.9 (-O3) | 2.4 to 6.8 (-O2), -2.3 to -1.2 (-O3) | 1.87 to 3.02 (-O2), 2.33 to 2.74 (-O3) |
| the constructor, 2 limbs, N = 3 | 2.81 to 11.4 (-O2), 4 to 12.8 (-O3) | 0.003 to 0.373 (-O2), 0.959 to 1.14 (-O3) | 5.45 to 6.32 (-O2), 5.8 to 6.36 (-O3) | 2.59 to 7.39 (-O2), 7.33 to 7.46 (-O3) |
| the constructor, 2 limbs, N = 7 | -0.48 to 0.85 (-O2), -1.17 to 0.95 (-O3) | -0.67 to 0.54 (-O2), 0.804 to 1.55 (-O3) | 2.45 to 2.81 (-O2), 7.17 to 8.08 (-O3) | -0.77 to 1.31 (-O2), 1.81 to 1.93 (-O3) |
| the constructor, 2 limbs, N = 13 | -0.01 to 0.72 (-O2), -0.17 to 1.91 (-O3) | -2.43 to 0.01 (-O2), -0.53 to 0.35 (-O3) | 1.66 to 2.06 (-O2), 5.05 to 5.55 (-O3) | 0.15 to 0.87 (-O2), 0.74 to 2.14 (-O3) |
| the constructor, 2 limbs, N = 18 | -0.36 to 0.64 (-O2), -1.73 to -0.48 (-O3) | -3.08 to -0.1 (-O2), -1.42 to 1.6 (-O3) | 1.08 to 1.27 (-O2), -9.03 to -8.59 (-O3) | 2.03 to 2.69 (-O2), 1.9 to 4.96 (-O3) |
| the constructor, 2 limbs, N = 80 | 1.27 to 3.23 (-O2), 0.22 to 0.4 (-O3) | -22.5 to -0.4 (-O2), -25.5 to 20.8 (-O3) | 4.6 to 6 (-O2), -0.8 to 10 (-O3) | 2.8 to 6.61 (-O2), 4.5 to 8.34 (-O3) |

| Short ball vectors, one operation per unit, many vectors: the check with its report cold, ns per operation (minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 0.024 to 0.238 (-O2), 0.034 to 0.056 (-O3) | 0.197 to 0.352 (-O2), -0.381 to 0.203 (-O3) | 2 to 2.06 (-O2), 3.48 to 3.52 (-O3) | 3.86 to 3.91 |
| `add(x, y, z)`, 1 limb, N = 7 | 0.021 to 0.181 (-O2), 0.051 to 0.328 (-O3) | 0.007 to 0.479 (-O2), -0.779 to 0.188 (-O3) | 1.92 to 1.99 (-O2), 1.88 to 1.99 (-O3) | 2.6 to 2.64 (-O2), 2.63 to 2.74 (-O3) |
| `add(x, y, z)`, 1 limb, N = 13 | 0.115 to 0.535 (-O2), 0.007 to 0.205 (-O3) | -0.04 to 0.258 (-O2), -0.782 to 0.081 (-O3) | 2.14 to 2.24 (-O2), 1.95 to 2.12 (-O3) | 2.44 to 2.56 |
| `add(x, y, z)`, 1 limb, N = 18 | -0.343 to 0.565 (-O2), -0.315 to 0.253 (-O3) | -0.09 to 0.26 (-O2), -1.17 to 0.063 (-O3) | 1.93 to 2.04 (-O2), 2.24 to 2.29 (-O3) | 2.25 to 2.34 |
| `add(x, y, z)`, 1 limb, N = 80 | 0.21 to 0.35 (-O2), 0.29 to 0.78 (-O3) | -0.8 to 2.8 (-O2), -8.25 to 1.05 (-O3) | 4.91 to 5.09 (-O2), 3.78 to 4.6 (-O3) | 3.65 to 3.8 (-O2), 2.44 to 3.56 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | -0.339 to 0.035 (-O2), 0.027 to 0.288 (-O3) | 0.151 to 0.228 (-O2), -1.26 to 0.078 (-O3) | 2.68 to 2.72 (-O2), 1.96 to 2.08 (-O3) | 1.91 to 2.13 (-O2), 1.93 to 2.02 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | -0.27 to 0.12 (-O2), 0.052 to 0.26 (-O3) | -0.05 to 0.09 (-O2), -2.42 to -0.04 (-O3) | 2.17 to 2.43 (-O2), 1.2 to 1.48 (-O3) | 1.78 to 1.8 (-O2), 1.62 to 1.87 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | -1.21 to -0.2 (-O2), 0.1 to 1.36 (-O3) | -0.06 to 0.76 (-O2), -4.06 to 0.31 (-O3) | 2.75 to 2.85 (-O2), 1.82 to 2.04 (-O3) | 2.2 to 2.25 (-O2), 2.08 to 2.39 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -1.87 to -0.36 (-O2), 0 to 1.2 (-O3) | -0.93 to 1.03 (-O2), -5.21 to 0.99 (-O3) | 4.5 to 4.82 (-O2), 4.34 to 4.74 (-O3) | 4.14 to 4.31 (-O2), 4.03 to 4.39 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -2.27 to 0.1 (-O2), 0.07 to 0.19 (-O3) | -0.36 to 0 (-O2), -20.8 to 0.4 (-O3) | 3.67 to 5.11 (-O2), 2.93 to 4.62 (-O3) | 3.12 to 4.51 (-O2), 3.51 to 5.69 (-O3) |
| `z = x + y`, 1 limb, N = 3 | 0.02 to 0.057 (-O2), -0.059 to 0.111 (-O3) | 0.261 to 0.392 (-O2), -0.489 to 0.201 (-O3) | 5.19 to 5.22 (-O2), 5.57 to 7.55 (-O3) | 2.88 to 2.95 |
| `z = x + y`, 1 limb, N = 7 | 0.005 to 0.082 (-O2), 0.003 to 0.02 (-O3) | 0.095 to 0.209 (-O2), -0.853 to 0.465 (-O3) | 5.58 to 5.67 (-O2), 5.29 to 7.1 (-O3) | 2.34 to 2.42 (-O2), 2.41 to 2.51 (-O3) |
| `z = x + y`, 1 limb, N = 13 | -0.33 to 0.202 (-O2), -0.06 to 0.074 (-O3) | 0.129 to 0.187 (-O2), -1.34 to 0.084 (-O3) | 4.23 to 4.27 (-O2), 6.07 to 6.2 (-O3) | 1.43 to 2.15 (-O2), 2.15 to 2.22 (-O3) |
| `z = x + y`, 1 limb, N = 18 | 0.18 to 0.94 (-O2), -0.68 to 0.33 (-O3) | -0.01 to 0 (-O2), -1.73 to 0.211 (-O3) | 3.68 to 4.04 (-O2), 3.89 to 4.8 (-O3) | 1.63 to 1.89 (-O2), 1.59 to 1.76 (-O3) |
| `z = x + y`, 1 limb, N = 80 | -1.9 to -0.29 (-O2), 0.59 to 0.91 (-O3) | 0.23 to 5.02 (-O2), -11.9 to 0.13 (-O3) | 1.46 to 2.12 (-O2), -1.01 to 0.4 (-O3) | -3.27 to 1.96 (-O2), 0.93 to 6.03 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -0.582 to -0.083 (-O2), -0.151 to -0.05 (-O3) | -0.508 to 0.26 (-O2), -1.23 to 0.336 (-O3) | 3.13 to 3.26 (-O2), 3.01 to 3.43 (-O3) | 2.79 to 3.75 (-O2), 2.63 to 2.9 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | -0.7 to 0.2 (-O2), -0.68 to 0.59 (-O3) | -0.83 to 0.42 (-O2), -2.53 to 0.23 (-O3) | 2.48 to 2.6 (-O2), 1.85 to 2.43 (-O3) | 2.45 to 4.14 (-O2), 2.43 to 2.75 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 0.11 to 1.11 (-O2), -1.19 to 1.34 (-O3) | -1.09 to 0.74 (-O2), -3.84 to 0.76 (-O3) | 2.31 to 2.9 (-O2), 2.45 to 3.34 (-O3) | 2.16 to 4 (-O2), 2.27 to 2.8 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -0.06 to 1.24 (-O2), -0.2 to 0.29 (-O3) | -1.19 to -0.18 (-O2), -6.5 to 0.09 (-O3) | 0.53 to 0.89 (-O2), 2.08 to 2.82 (-O3) | 3.86 to 5.39 (-O2), 3.39 to 16.7 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | -0.5 to -0.1 (-O2), -7.7 to 1.4 (-O3) | -3.5 to 1.4 (-O2), -28.6 to 0 (-O3) | 0.2 to 1.6 (-O2), -5.1 to 2.5 (-O3) | -5.1 to 5.1 (-O2), 1 to 1.8 (-O3) |
| `sub`, 1 limb, N = 3 | 0.041 to 0.138 (-O2), -0.089 to 0.124 (-O3) | 0.111 to 0.299 (-O2), -0.505 to 0.17 (-O3) | 1.86 to 1.9 (-O2), 3.44 to 3.56 (-O3) | 3.91 to 4 |
| `sub`, 1 limb, N = 7 | 0.09 to 0.187 (-O2), -0.177 to 0.235 (-O3) | 0.082 to 0.115 (-O2), -0.679 to 0.066 (-O3) | 1.78 to 1.79 (-O2), 1.87 to 1.98 (-O3) | 2.6 to 2.68 |
| `sub`, 1 limb, N = 13 | -0.401 to 0.025 (-O2), -0.419 to -0.229 (-O3) | -0.275 to 0.535 (-O2), -0.901 to 0.165 (-O3) | 2.11 to 2.23 (-O2), 2.21 to 2.26 (-O3) | 2.38 to 2.48 |
| `sub`, 1 limb, N = 18 | -0.24 to 0.394 (-O2), -0.276 to 0.337 (-O3) | -0.475 to 0.394 (-O2), -1.18 to 0.16 (-O3) | 2.18 to 2.23 (-O2), 1.87 to 2.13 (-O3) | 2.14 to 2.3 (-O2), 2.18 to 2.22 (-O3) |
| `sub`, 1 limb, N = 80 | -2.84 to 0.04 (-O2), -2.06 to 0.5 (-O3) | -2.99 to 3.08 (-O2), -7.83 to -0.2 (-O3) | 5.25 to 5.47 (-O2), 3.6 to 4.19 (-O3) | 3.62 to 3.78 (-O2), 2.65 to 3.14 (-O3) |
| `sub`, 2 limbs, N = 3 | -0.404 to 0.048 (-O2), -0.561 to 0.408 (-O3) | -0.352 to 0.512 (-O2), -1.28 to 0.339 (-O3) | 2.63 to 2.68 (-O2), 1.94 to 2.22 (-O3) | 2.15 to 2.18 (-O2), 2.14 to 2.25 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.84 to -0.17 (-O2), -1.01 to 0.5 (-O3) | -0.15 to 0.13 (-O2), -2.59 to 0.46 (-O3) | 1.82 to 1.91 (-O2), 1.3 to 1.67 (-O3) | 3.03 to 3.18 (-O2), 2.96 to 3.02 (-O3) |
| `sub`, 2 limbs, N = 13 | -1.62 to -0.08 (-O2), -1 to -0.04 (-O3) | 0.12 to 1.77 (-O2), -4.29 to 0.31 (-O3) | 2.49 to 2.58 (-O2), 1.9 to 2.23 (-O3) | 2.97 to 3.03 (-O2), 2.86 to 3.02 (-O3) |
| `sub`, 2 limbs, N = 18 | -0.38 to 0.02 (-O2), -1.03 to 0.59 (-O3) | -0.7 to 2.09 (-O2), -5.53 to 0.95 (-O3) | 3.85 to 4.1 (-O2), 3.67 to 4.07 (-O3) | 4.73 to 4.92 (-O2), 4.63 to 4.94 (-O3) |
| `sub`, 2 limbs, N = 80 | 0.39 to 1.96 (-O2), -6.5 to 4.29 (-O3) | -1.19 to 2.6 (-O2), -21.8 to 4.01 (-O3) | 4.02 to 4.77 (-O2), 1.45 to 3.55 (-O3) | 4.22 to 4.74 (-O2), 4.18 to 4.95 (-O3) |
| `scale`, 1 limb, N = 3 | 0.054 to 0.136 (-O2), -0.033 to 0.233 (-O3) | -0.046 to 0.11 (-O2), -0.548 to 0.127 (-O3) | 2.25 to 2.33 (-O2), 3.01 to 3.09 (-O3) | 3.88 to 3.95 |
| `scale`, 1 limb, N = 7 | -0.312 to -0.002 (-O2), -0.177 to 0.207 (-O3) | -0.001 to 0.002 (-O2), -0.676 to 0.287 (-O3) | 1.72 to 1.73 (-O2), 2.24 to 2.34 (-O3) | 2.62 to 2.67 (-O2), 2.54 to 2.72 (-O3) |
| `scale`, 1 limb, N = 13 | -0.283 to 0.01 (-O2), -0.362 to 0.126 (-O3) | -0.069 to -0.016 (-O2), -0.64 to 0.193 (-O3) | 2.21 to 2.44 (-O2), 2.2 to 2.36 (-O3) | 2.41 to 2.5 |
| `scale`, 1 limb, N = 18 | 0.141 to 0.771 (-O2), -0.258 to 0.62 (-O3) | -0.069 to 0.157 (-O2), -1.29 to 0.132 (-O3) | 2.22 to 2.32 (-O2), 1.87 to 2.06 (-O3) | 2.4 to 2.51 |
| `scale`, 1 limb, N = 80 | -3.35 to 0.03 (-O2), -1.69 to 1.82 (-O3) | -0.19 to 0.3 (-O2), -6.91 to 1.32 (-O3) | 3.73 to 4.1 (-O2), 1.17 to 1.47 (-O3) | 2.78 to 3.1 (-O2), 2.31 to 17.7 (-O3) |
| `scale`, 2 limbs, N = 3 | -0.398 to -0.067 (-O2), -0.13 to 0.045 (-O3) | 0.09 to 0.479 (-O2), -0.706 to 0.231 (-O3) | 2.86 to 2.88 (-O2), 1.01 to 1.1 (-O3) | 2.61 to 2.7 |
| `scale`, 2 limbs, N = 7 | -0.606 to -0.052 (-O2), -0.572 to -0.023 (-O3) | -0.413 to 0.645 (-O2), -1.24 to 0.268 (-O3) | 2.75 to 2.85 (-O2), 1.83 to 2.1 (-O3) | 1.94 to 2.02 (-O2), 1.92 to 2 (-O3) |
| `scale`, 2 limbs, N = 13 | -0.248 to 0.109 (-O2), -0.553 to 0.074 (-O3) | -0.123 to 0.19 (-O2), -1.97 to 0.362 (-O3) | 2.71 to 2.85 (-O2), 1.86 to 1.99 (-O3) | 2.93 to 2.98 (-O2), 2.84 to 3.15 (-O3) |
| `scale`, 2 limbs, N = 18 | -0.05 to 0 (-O2), -0.88 to -0.04 (-O3) | -0.56 to 1.01 (-O2), -2.7 to 0.38 (-O3) | 2.87 to 2.91 (-O2), 1.52 to 1.71 (-O3) | 1.77 to 1.93 (-O2), 1.72 to 2.18 (-O3) |
| `scale`, 2 limbs, N = 80 | -3.81 to 0.34 (-O2), -3.48 to 0.08 (-O3) | -1.51 to 2.45 (-O2), -7.92 to -0.03 (-O3) | 3.01 to 3.46 (-O2), 0.16 to 0.89 (-O3) | 1.8 to 2.6 (-O2), 1.27 to 2.44 (-O3) |
| `half`, 1 limb, N = 3 | -0.199 to 0.094 (-O2), -0.007 to 0.121 (-O3) | -0.038 to 0.364 (-O2), -0.681 to -0.026 (-O3) | 2.29 to 2.34 (-O2), 2.69 to 2.77 (-O3) | 2.47 to 2.5 (-O2), 2.36 to 2.51 (-O3) |
| `half`, 1 limb, N = 7 | -0.323 to 0.091 (-O2), 0.09 to 0.112 (-O3) | -0.488 to 0.746 (-O2), -1.16 to 0.001 (-O3) | 1.85 to 1.95 (-O2), 1.91 to 2.09 (-O3) | 2.36 to 2.43 (-O2), 2.32 to 2.44 (-O3) |
| `half`, 1 limb, N = 13 | 0.14 to 0.453 (-O2), 0.294 to 0.348 (-O3) | -0.614 to 0.051 (-O2), -1.64 to 0.089 (-O3) | 2.35 to 2.46 (-O2), 1.43 to 1.64 (-O3) | 2.2 to 2.36 (-O2), 2.11 to 2.16 (-O3) |
| `half`, 1 limb, N = 18 | -0.219 to 0.07 (-O2), -0.24 to 0.283 (-O3) | -0.43 to 0.6 (-O2), -1.49 to 0.021 (-O3) | 2.2 to 2.55 (-O2), 1.9 to 2.2 (-O3) | 3.39 to 3.44 (-O2), 3.44 to 3.69 (-O3) |
| `half`, 1 limb, N = 80 | -0.82 to 0.18 (-O2), -0.03 to 0.29 (-O3) | -3.53 to 1.08 (-O2), -8.43 to 0.23 (-O3) | 3.49 to 4 (-O2), 3.9 to 4.35 (-O3) | 5.2 to 5.25 (-O2), 5.61 to 6.03 (-O3) |
| `half`, 2 limbs, N = 3 | -0.231 to 0.081 (-O2), 0.088 to 0.29 (-O3) | 0.305 to 0.938 (-O2), -0.543 to 0.154 (-O3) | 1.91 to 1.99 (-O2), 1.76 to 2 (-O3) | 1.91 to 1.98 (-O2), 1.81 to 2.03 (-O3) |
| `half`, 2 limbs, N = 7 | -0.234 to 0.152 (-O2), 0.111 to 0.749 (-O3) | -0.426 to 0.58 (-O2), -1.87 to 0.171 (-O3) | 0.98 to 1.13 (-O2), 2.31 to 2.47 (-O3) | 2.38 to 2.46 (-O2), 2.4 to 2.6 (-O3) |
| `half`, 2 limbs, N = 13 | -0.75 to 0.28 (-O2), -0.02 to 0.53 (-O3) | -0.74 to 0.34 (-O2), -2.5 to 0.14 (-O3) | 1.47 to 1.75 (-O2), 2.32 to 2.5 (-O3) | 2.76 to 2.78 (-O2), 2.78 to 3.07 (-O3) |
| `half`, 2 limbs, N = 18 | -1.13 to 0.24 (-O2), 0.15 to 0.83 (-O3) | 0.21 to 1.02 (-O2), -3.37 to 0 (-O3) | 1.12 to 1.24 (-O2), 2.18 to 2.47 (-O3) | 2.86 to 3.01 (-O2), 2.75 to 2.88 (-O3) |
| `half`, 2 limbs, N = 80 | -5.98 to 0.05 (-O2), 0.04 to 2.68 (-O3) | -3.48 to 0.24 (-O2), -16.1 to 0.18 (-O3) | 3.56 to 4.1 (-O2), 3.97 to 4.1 (-O3) | 4.78 to 5.18 (-O2), 4.61 to 5.5 (-O3) |
| the constructor, 1 limb, N = 3 | 2.56 to 11.7 (-O2), 3.53 to 11.4 (-O3) | 0.127 to 0.234 (-O2), -0.505 to 0.299 (-O3) | 5.32 to 6.33 (-O2), 5.38 to 7.31 (-O3) | 18.3 to 18.4 (-O2), 12.3 to 12.4 (-O3) |
| the constructor, 1 limb, N = 7 | -1.59 to -0.25 (-O2), -1.18 to 1.55 (-O3) | -8.41 to -4.47 (-O2), -0.848 to 0.177 (-O3) | 4.92 to 5.15 (-O2), 5.64 to 6.29 (-O3) | 0 to 1.79 (-O2), -1.22 to 1.92 (-O3) |
| the constructor, 1 limb, N = 13 | -0.96 to -0.42 (-O2), 0.18 to 1.66 (-O3) | -1.62 to -0.06 (-O2), -0.854 to 0.595 (-O3) | 2.15 to 2.74 (-O2), 3.6 to 3.82 (-O3) | -0.55 to 0.51 (-O2), -0.38 to 0.3 (-O3) |
| the constructor, 1 limb, N = 18 | -4.12 to -0.76 (-O2), -0.85 to 0.87 (-O3) | -3.74 to -0.07 (-O2), -4.85 to 0.31 (-O3) | 4.95 to 5.05 (-O2), 4.66 to 5.65 (-O3) | -0.83 to 0.93 (-O2), 0.17 to 2.28 (-O3) |
| the constructor, 1 limb, N = 80 | -1.38 to -0.01 (-O2), 0.07 to 0.25 (-O3) | -8.1 to 3.3 (-O2), -59.2 to 0.9 (-O3) | 4.8 to 7.4 (-O2), -0.4 to 0.9 (-O3) | -0.46 to -0.03 (-O2), 2.21 to 11.8 (-O3) |
| the constructor, 2 limbs, N = 3 | 2.79 to 14.5 (-O2), 3.12 to 3.56 (-O3) | 0.382 to 0.468 (-O2), -0.717 to 0.025 (-O3) | 5.46 to 6.36 (-O2), 5.67 to 6.34 (-O3) | 7.68 to 7.83 (-O2), 7.43 to 7.72 (-O3) |
| the constructor, 2 limbs, N = 7 | -1.33 to 1.11 (-O2), -2.96 to -0.61 (-O3) | -0.31 to 0.27 (-O2), -1.21 to 0.356 (-O3) | 2.61 to 3.03 (-O2), 6.22 to 6.96 (-O3) | 1.27 to 1.65 (-O2), 0.13 to 1.92 (-O3) |
| the constructor, 2 limbs, N = 13 | 0.38 to 0.77 (-O2), 0 to 0.09 (-O3) | -1.88 to 0.15 (-O2), -2.55 to -0.02 (-O3) | 1.08 to 1.58 (-O2), 3.27 to 3.68 (-O3) | 0.73 to 2.2 (-O2), 0.6 to 6.3 (-O3) |
| the constructor, 2 limbs, N = 18 | -1.84 to 0.15 (-O2), -0.79 to 0.08 (-O3) | 0.06 to 0.87 (-O2), -8.66 to 0.24 (-O3) | 5.34 to 5.52 (-O2), -11.7 to -11.2 (-O3) | 2.11 to 2.19 (-O2), 1.44 to 4.86 (-O3) |
| the constructor, 2 limbs, N = 80 | 1.59 to 2.2 (-O2), -7.1 to 4.7 (-O3) | -2 to 0.8 (-O2), -57.6 to -0.6 (-O3) | -18.5 to -11.9 (-O2), -3.5 to 4.9 (-O3) | 5.3 to 6.51 (-O2), 2.1 to 8.53 (-O3) |

| Short ball vectors, one operation per unit, many vectors: with the check over without | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 1.09 to 1.10 (-O2), 1.09 to 1.14 (-O3) | 1.33 (-O2), 1.31 to 1.39 (-O3) | 1.22 to 1.25 (-O2), 1.75 to 1.76 (-O3) | 1.78 to 1.80 |
| `add(x, y, z)`, 1 limb, N = 7 | 1.00 to 1.06 (-O2), 1.04 to 1.11 (-O3) | 1.03 to 1.07 (-O2), 1.24 to 1.29 (-O3) | 1.19 to 1.20 (-O2), 1.24 to 1.26 (-O3) | 1.37 to 1.41 |
| `add(x, y, z)`, 1 limb, N = 13 | 1.05 to 1.10 | 0.99 to 1.04 (-O2), 1.10 to 1.17 (-O3) | 1.19 to 1.21 (-O2), 1.29 to 1.30 (-O3) | 1.33 to 1.36 |
| `add(x, y, z)`, 1 limb, N = 18 | 1.00 to 1.07 (-O2), 0.94 to 1.01 (-O3) | 1.02 to 1.07 (-O2), 1.04 to 1.11 (-O3) | 1.16 to 1.19 (-O2), 1.21 to 1.22 (-O3) | 1.28 to 1.32 |
| `add(x, y, z)`, 1 limb, N = 80 | 0.92 to 1.00 (-O2), 1.00 to 1.06 (-O3) | 0.87 to 0.99 (-O2), 0.99 to 1.04 (-O3) | 1.07 to 1.08 (-O2), 1.12 to 1.17 (-O3) | 1.18 to 1.20 (-O2), 1.13 to 1.14 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | 0.93 to 1.01 (-O2), 1.02 to 1.03 (-O3) | 0.92 to 0.99 (-O2), 1.03 to 1.05 (-O3) | 1.11 to 1.12 (-O2), 1.16 to 1.17 (-O3) | 1.11 to 1.12 |
| `add(x, y, z)`, 2 limbs, N = 7 | 0.95 to 1.01 (-O2), 0.98 to 0.99 (-O3) | 0.93 to 1.01 (-O2), 0.96 to 1.02 (-O3) | 1.08 to 1.13 | 1.07 to 1.09 |
| `add(x, y, z)`, 2 limbs, N = 13 | 0.94 to 1.01 (-O2), 1.00 to 1.06 (-O3) | 0.89 to 1.04 (-O2), 1.01 to 1.02 (-O3) | 1.10 to 1.12 | 1.09 to 1.10 |
| `add(x, y, z)`, 2 limbs, N = 18 | 0.92 to 1.00 (-O2), 1.00 to 1.06 (-O3) | 0.90 to 1.04 (-O2), 1.00 to 1.01 (-O3) | 1.13 to 1.14 | 1.13 to 1.14 |
| `add(x, y, z)`, 2 limbs, N = 80 | 0.94 to 1.02 (-O2), 1.00 to 1.01 (-O3) | 0.92 to 1.00 (-O2), 0.96 to 1.01 (-O3) | 1.03 to 1.06 | 1.03 to 1.05 |
| `z = x + y`, 1 limb, N = 3 | 1.02 to 1.07 | 1.15 to 1.23 (-O2), 1.33 to 1.38 (-O3) | 1.47 to 1.52 (-O2), 1.50 to 1.74 (-O3) | 1.50 to 1.52 |
| `z = x + y`, 1 limb, N = 7 | 1.00 (-O2), 1.00 to 1.07 (-O3) | 1.04 to 1.13 (-O2), 1.22 to 1.26 (-O3) | 1.41 to 1.46 (-O2), 1.47 to 1.64 (-O3) | 1.33 to 1.34 |
| `z = x + y`, 1 limb, N = 13 | 1.36 to 1.39 | 1.02 to 1.09 (-O2), 1.10 to 1.11 (-O3) | 1.35 to 1.36 (-O2), 1.50 to 1.51 (-O3) | 1.16 to 1.29 (-O2), 1.25 to 1.29 (-O3) |
| `z = x + y`, 1 limb, N = 18 | 1.00 to 1.04 (-O2), 0.92 to 1.07 (-O3) | 1.26 to 1.29 (-O2), 1.23 to 1.24 (-O3) | 1.25 to 1.26 (-O2), 1.35 to 1.40 (-O3) | 1.20 to 1.25 |
| `z = x + y`, 1 limb, N = 80 | 0.97 to 0.99 (-O2), 1.00 to 1.06 (-O3) | 0.96 to 1.01 (-O2), 1.00 to 1.04 (-O3) | 0.99 to 1.02 (-O2), 0.99 to 1.05 (-O3) | 0.89 to 1.00 (-O2), 0.99 to 1.07 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 0.99 to 1.02 (-O2), 0.99 to 1.07 (-O3) | 0.96 to 1.03 (-O2), 1.01 to 1.07 (-O3) | 1.11 to 1.12 (-O2), 1.20 to 1.22 (-O3) | 1.06 to 1.26 (-O2), 1.14 to 1.17 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 1.00 to 1.03 | 0.95 to 0.97 (-O2), 0.99 to 1.05 (-O3) | 1.07 to 1.08 (-O2), 1.11 to 1.13 (-O3) | 1.03 to 1.18 (-O2), 1.10 to 1.12 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 0.96 to 1.07 (-O2), 0.98 to 1.00 (-O3) | 0.93 to 0.97 (-O2), 1.10 (-O3) | 1.05 to 1.06 (-O2), 1.09 to 1.12 (-O3) | 1.02 to 1.15 (-O2), 1.08 to 1.09 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 0.99 to 1.03 (-O2), 1.00 to 1.05 (-O3) | 0.92 to 1.01 (-O2), 0.99 to 1.00 (-O3) | 1.01 to 1.05 | 1.05 to 1.14 (-O2), 1.07 to 1.09 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 0.97 to 1.01 | 0.94 to 1.01 (-O2), 1.00 (-O3) | 1.01 to 1.04 (-O2), 0.96 to 1.03 (-O3) | 0.97 to 1.01 (-O2), 1.01 to 1.05 (-O3) |
| `sub`, 1 limb, N = 3 | 1.11 to 1.16 (-O2), 1.10 to 1.12 (-O3) | 1.20 to 1.41 (-O2), 1.27 to 1.41 (-O3) | 1.22 to 1.24 (-O2), 1.73 to 1.76 (-O3) | 1.79 to 1.80 |
| `sub`, 1 limb, N = 7 | 1.04 to 1.09 | 0.97 to 1.09 (-O2), 1.25 to 1.32 (-O3) | 1.18 to 1.19 (-O2), 1.25 to 1.27 (-O3) | 1.38 to 1.40 |
| `sub`, 1 limb, N = 13 | 1.00 to 1.09 (-O2), 1.01 to 1.05 (-O3) | 1.18 to 1.33 (-O2), 1.00 to 1.14 (-O3) | 1.18 to 1.29 (-O2), 1.25 to 1.28 (-O3) | 1.33 to 1.36 |
| `sub`, 1 limb, N = 18 | 0.96 to 1.01 | 0.98 to 1.11 (-O2), 0.96 to 1.11 (-O3) | 1.17 to 1.19 (-O2), 1.19 to 1.22 (-O3) | 1.28 to 1.30 |
| `sub`, 1 limb, N = 80 | 0.99 to 1.03 (-O2), 0.97 to 1.00 (-O3) | 0.90 to 0.99 (-O2), 0.97 to 1.00 (-O3) | 1.05 to 1.07 (-O2), 1.13 to 1.15 (-O3) | 1.19 to 1.20 (-O2), 1.13 to 1.15 (-O3) |
| `sub`, 2 limbs, N = 3 | 0.99 to 1.02 | 0.93 to 1.01 (-O2), 1.00 to 1.10 (-O3) | 1.11 (-O2), 1.15 to 1.17 (-O3) | 1.12 to 1.13 |
| `sub`, 2 limbs, N = 7 | 0.98 to 1.00 | 0.93 to 1.01 (-O2), 0.97 to 1.07 (-O3) | 1.07 to 1.08 (-O2), 1.10 to 1.12 (-O3) | 1.12 to 1.13 |
| `sub`, 2 limbs, N = 13 | 0.96 to 1.00 | 0.91 to 1.01 (-O2), 0.95 to 1.02 (-O3) | 1.09 to 1.11 | 1.11 to 1.12 |
| `sub`, 2 limbs, N = 18 | 0.99 to 1.03 | 0.91 to 1.01 (-O2), 0.96 to 1.07 (-O3) | 1.11 to 1.13 | 1.13 to 1.15 |
| `sub`, 2 limbs, N = 80 | 1.00 to 1.07 (-O2), 1.00 to 1.02 (-O3) | 0.94 to 1.01 (-O2), 0.95 to 1.05 (-O3) | 1.01 to 1.05 | 1.04 to 1.06 |
| `scale`, 1 limb, N = 3 | 1.08 to 1.12 | 1.21 to 1.29 (-O2), 1.17 to 1.24 (-O3) | 1.27 (-O2), 1.66 to 1.69 (-O3) | 1.85 to 1.87 |
| `scale`, 1 limb, N = 7 | 0.96 to 1.05 (-O2), 1.04 to 1.05 (-O3) | 0.98 to 1.08 (-O2), 1.10 to 1.21 (-O3) | 1.17 to 1.18 (-O2), 1.26 to 1.29 (-O3) | 1.38 to 1.41 |
| `scale`, 1 limb, N = 13 | 0.98 to 1.02 | 0.99 to 1.05 (-O2), 1.04 to 1.14 (-O3) | 1.23 to 1.24 (-O2), 1.28 to 1.29 (-O3) | 1.34 to 1.36 |
| `scale`, 1 limb, N = 18 | 0.98 to 1.02 (-O2), 1.01 to 1.07 (-O3) | 0.98 to 1.05 (-O2), 1.04 to 1.12 (-O3) | 1.15 to 1.20 | 1.33 to 1.35 |
| `scale`, 1 limb, N = 80 | 0.92 to 1.02 (-O2), 1.01 (-O3) | 0.93 to 1.01 (-O2), 0.99 to 1.06 (-O3) | 1.05 to 1.07 | 1.15 to 1.16 (-O2), 1.18 to 1.24 (-O3) |
| `scale`, 2 limbs, N = 3 | 0.89 to 1.02 (-O2), 1.03 (-O3) | 1.00 to 1.13 (-O2), 1.14 to 1.21 (-O3) | 1.17 to 1.18 (-O2), 1.25 to 1.27 (-O3) | 1.33 to 1.35 |
| `scale`, 2 limbs, N = 7 | 0.93 to 1.10 (-O2), 1.04 to 1.07 (-O3) | 0.94 to 1.02 (-O2), 1.02 to 1.13 (-O3) | 1.14 to 1.16 | 1.25 to 1.27 |
| `scale`, 2 limbs, N = 13 | 0.98 to 1.06 (-O2), 0.93 to 1.04 (-O3) | 1.00 to 1.02 (-O2), 1.04 to 1.12 (-O3) | 1.14 to 1.18 | 1.26 to 1.27 |
| `scale`, 2 limbs, N = 18 | 0.94 to 1.01 (-O2), 0.98 to 0.99 (-O3) | 0.96 to 1.08 (-O2), 1.02 to 1.07 (-O3) | 1.13 to 1.14 | 1.11 to 1.13 |
| `scale`, 2 limbs, N = 80 | 0.92 to 1.01 (-O2), 0.99 to 1.01 (-O3) | 0.92 to 1.00 (-O2), 1.01 (-O3) | 1.06 to 1.08 (-O2), 1.01 (-O3) | 1.02 to 1.04 |
| `half`, 1 limb, N = 3 | 1.07 to 1.09 (-O2), 1.06 to 1.16 (-O3) | 1.06 (-O2), 1.10 to 1.14 (-O3) | 1.15 (-O2), 1.45 to 1.47 (-O3) | 1.37 to 1.39 |
| `half`, 1 limb, N = 7 | 1.00 to 1.07 (-O2), 1.06 to 1.13 (-O3) | 0.97 to 1.06 (-O2), 1.07 (-O3) | 1.12 (-O2), 1.20 to 1.22 (-O3) | 1.19 to 1.20 |
| `half`, 1 limb, N = 13 | 1.00 to 1.03 (-O2), 1.02 to 1.08 (-O3) | 0.95 to 1.02 (-O2), 1.05 (-O3) | 1.14 to 1.17 | 1.17 to 1.19 |
| `half`, 1 limb, N = 18 | 1.04 to 1.15 (-O2), 1.03 to 1.10 (-O3) | 0.99 to 1.03 (-O2), 1.07 to 1.14 (-O3) | 1.12 to 1.13 (-O2), 1.19 to 1.22 (-O3) | 1.24 to 1.26 |
| `half`, 1 limb, N = 80 | 0.99 to 1.03 (-O2), 0.96 to 1.06 (-O3) | 0.99 to 1.03 | 1.10 to 1.14 | 1.16 to 1.19 |
| `half`, 2 limbs, N = 3 | 1.01 to 1.13 (-O2), 1.05 to 1.12 (-O3) | 1.05 (-O2), 1.14 to 1.21 (-O3) | 1.11 (-O2), 1.25 to 1.27 (-O3) | 1.16 to 1.18 |
| `half`, 2 limbs, N = 7 | 1.01 to 1.10 (-O2), 1.02 to 1.08 (-O3) | 0.95 to 1.03 (-O2), 1.06 to 1.07 (-O3) | 1.04 to 1.05 (-O2), 1.14 to 1.15 (-O3) | 1.15 to 1.17 |
| `half`, 2 limbs, N = 13 | 0.99 to 1.03 (-O2), 1.02 to 1.07 (-O3) | 0.94 to 1.03 (-O2), 0.99 to 1.06 (-O3) | 1.07 to 1.08 (-O2), 1.20 to 1.22 (-O3) | 1.16 to 1.18 |
| `half`, 2 limbs, N = 18 | 0.97 to 1.01 (-O2), 1.01 to 1.08 (-O3) | 0.98 to 1.01 | 1.04 (-O2), 1.12 to 1.13 (-O3) | 1.12 to 1.15 |
| `half`, 2 limbs, N = 80 | 0.97 to 1.00 (-O2), 0.99 to 1.06 (-O3) | 0.94 to 1.01 (-O2), 1.01 (-O3) | 1.06 to 1.09 | 1.09 to 1.11 |
| the constructor, 1 limb, N = 3 | 1.65 to 1.96 (-O2), 1.81 to 2.30 (-O3) | 1.25 to 1.33 (-O2), 1.20 to 1.31 (-O3) | 1.50 to 1.65 (-O2), 1.55 to 1.76 (-O3) | 4.02 to 4.10 |
| the constructor, 1 limb, N = 7 | 0.95 to 1.04 (-O2), 0.89 to 0.94 (-O3) | 0.51 to 0.72 (-O2), 1.27 to 1.35 (-O3) | 1.32 to 1.34 (-O2), 1.39 to 1.43 (-O3) | 0.99 to 1.05 (-O2), 0.95 to 1.07 (-O3) |
| the constructor, 1 limb, N = 13 | 0.96 to 1.06 (-O2), 0.98 to 1.08 (-O3) | 0.90 to 0.99 (-O2), 1.19 to 1.20 (-O3) | 1.10 to 1.13 (-O2), 1.16 to 1.18 (-O3) | 0.99 to 1.01 |
| the constructor, 1 limb, N = 18 | 0.89 to 0.95 (-O2), 0.97 to 0.99 (-O3) | 0.92 to 1.01 (-O2), 1.02 to 1.03 (-O3) | 1.08 to 1.12 | 0.96 to 0.98 (-O2), 1.02 to 1.07 (-O3) |
| the constructor, 1 limb, N = 80 | 0.97 to 0.99 (-O2), 0.99 to 1.06 (-O3) | 0.99 to 1.01 (-O2), 0.95 to 1.00 (-O3) | 1.02 to 1.05 (-O2), 0.98 to 0.99 (-O3) | 1.03 to 1.04 |
| the constructor, 2 limbs, N = 3 | 1.58 to 3.43 (-O2), 1.70 to 3.59 (-O3) | 1.00 to 1.08 (-O2), 1.24 to 1.26 (-O3) | 1.50 to 1.63 (-O2), 1.57 to 1.64 (-O3) | 1.30 to 1.86 (-O2), 1.85 to 1.87 (-O3) |
| the constructor, 2 limbs, N = 7 | 0.98 to 1.03 (-O2), 0.96 to 1.05 (-O3) | 0.96 to 1.04 (-O2), 1.10 to 1.25 (-O3) | 1.14 to 1.16 (-O2), 1.62 to 1.69 (-O3) | 0.95 to 1.08 (-O2), 1.11 to 1.12 (-O3) |
| the constructor, 2 limbs, N = 13 | 1.00 to 1.03 (-O2), 0.99 to 1.06 (-O3) | 0.92 to 1.00 (-O2), 0.96 to 1.03 (-O3) | 1.04 to 1.06 (-O2), 1.29 to 1.32 (-O3) | 1.01 to 1.04 (-O2), 1.03 to 1.09 (-O3) |
| the constructor, 2 limbs, N = 18 | 0.99 to 1.02 (-O2), 0.93 to 0.98 (-O3) | 0.93 to 1.00 (-O2), 0.97 to 1.03 (-O3) | 1.02 to 1.03 (-O2), 0.77 to 0.78 (-O3) | 1.06 to 1.08 (-O2), 1.06 to 1.16 (-O3) |
| the constructor, 2 limbs, N = 80 | 1.00 to 1.03 | 0.94 to 1.00 (-O2), 0.93 to 1.06 (-O3) | 1.02 to 1.03 (-O2), 0.99 to 1.06 (-O3) | 1.03 to 1.07 (-O2), 1.04 to 1.09 (-O3) |

| Short ball vectors, one operation per unit, a dependent chain: ns per operation, with the check | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 14.9 to 19.1 (-O2), 14.5 to 19.3 (-O3) | 10.9 to 13 (-O2), 12.3 to 13.9 (-O3) | 11.6 (-O2), 9.96 to 9.98 (-O3) | 8.78 to 8.86 |
| `add(x, y, z)`, 1 limb, N = 7 | 15.2 to 19.2 (-O2), 15.1 to 19.5 (-O3) | 6.19 to 8.28 (-O2), 12 to 13.4 (-O3) | 13.5 to 15.1 (-O2), 12 to 12.1 (-O3) | 9.65 to 9.77 |
| `add(x, y, z)`, 1 limb, N = 13 | 10.2 to 13.1 (-O2), 10.1 to 13.2 (-O3) | 6.45 to 7.56 (-O2), 11.3 to 15.2 (-O3) | 13.1 to 13.2 (-O2), 11.9 (-O3) | 10.3 to 10.5 |
| `add(x, y, z)`, 1 limb, N = 18 | 9.21 to 13 (-O2), 9.31 to 13.4 (-O3) | 7.32 to 8.49 (-O2), 7.99 to 8.94 (-O3) | 14.8 (-O2), 13.3 (-O3) | 11.2 to 11.3 |
| `add(x, y, z)`, 1 limb, N = 80 | 31.1 to 39.8 (-O2), 31 to 39.7 (-O3) | 37.1 to 40.1 (-O2), 32.2 to 36 (-O3) | 30.4 to 30.5 (-O2), 25.9 to 26 (-O3) | 21.9 to 22.1 (-O2), 20.2 to 20.4 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | 19.7 to 25.5 (-O2), 20.1 to 25.9 (-O3) | 11 to 13.6 (-O2), 11.7 to 13.8 (-O3) | 27 to 27.1 (-O2), 19.6 (-O3) | 17.5 to 17.7 |
| `add(x, y, z)`, 2 limbs, N = 7 | 11.5 to 14.7 (-O2), 11.5 to 15.4 (-O3) | 13.9 to 15.1 (-O2), 13.1 to 15.4 (-O3) | 32.2 to 32.4 (-O2), 25.8 to 25.9 (-O3) | 22.8 to 23.2 |
| `add(x, y, z)`, 2 limbs, N = 13 | 16.2 to 20.9 (-O2), 16.2 to 20.5 (-O3) | 16.9 to 20.4 (-O2), 17.9 to 20 (-O3) | 32.4 to 32.7 (-O2), 25.4 to 25.5 (-O3) | 24.5 to 24.7 |
| `add(x, y, z)`, 2 limbs, N = 18 | 20.8 to 26.6 (-O2), 20.1 to 26 (-O3) | 23.7 to 25.4 (-O2), 21.9 to 24.5 (-O3) | 40.6 to 41.4 (-O2), 36.9 to 37.5 (-O3) | 34.2 to 34.7 |
| `add(x, y, z)`, 2 limbs, N = 80 | 80 to 102 (-O2), 79.4 to 102 (-O3) | 88.9 to 98.9 (-O2), 86.6 to 97.1 (-O3) | 100 to 101 (-O2), 95.7 to 96.2 (-O3) | 95 to 96.1 |
| `z = x + y`, 1 limb, N = 3 | 16.4 to 20.9 (-O2), 16.4 to 21.2 (-O3) | 12.7 to 14.7 (-O2), 12.8 to 15.6 (-O3) | 23.9 to 24.8 | 19.8 to 19.9 |
| `z = x + y`, 1 limb, N = 7 | 16.5 to 21 (-O2), 16.5 to 20.7 (-O3) | 12.6 to 15 (-O2), 11.6 to 15.8 (-O3) | 23.9 to 25 | 21.4 to 21.6 |
| `z = x + y`, 1 limb, N = 13 | 16.8 to 20.2 (-O2), 16.8 to 21.8 (-O3) | 12.5 to 14.7 (-O2), 13.9 to 16 (-O3) | 22.4 to 22.6 | 23.1 to 23.3 |
| `z = x + y`, 1 limb, N = 18 | 12.9 to 15.5 (-O2), 12.6 to 16.5 (-O3) | 12.7 to 14 (-O2), 9.7 to 11.7 (-O3) | 29.5 to 29.6 (-O2), 26.3 to 27.9 (-O3) | 23.2 to 23.6 |
| `z = x + y`, 1 limb, N = 80 | 42.3 to 55.1 (-O2), 43.7 to 55.6 (-O3) | 50.2 to 57.4 (-O2), 46.5 to 52.4 (-O3) | 85.5 to 86.7 | 34.1 to 38.4 (-O2), 38.3 to 38.5 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 21.8 to 27.8 (-O2), 21.9 to 28 (-O3) | 16.2 to 17.8 (-O2), 19.8 to 23.7 (-O3) | 36.5 to 37.5 | 26.2 to 28.8 (-O2), 27.5 to 27.7 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 15.3 to 19.4 (-O2), 15.3 to 19.4 (-O3) | 15.4 to 18.3 (-O2), 18.7 to 23.5 (-O3) | 38.1 to 46.9 (-O2), 36.6 to 37.1 (-O3) | 29.6 to 30.2 |
| `z = x + y`, 2 limbs, N = 13 | 18.6 to 23.6 (-O2), 18.6 to 23.6 (-O3) | 25.8 to 28.5 (-O2), 22.6 to 26.8 (-O3) | 48.6 to 48.7 (-O2), 41.7 to 42 (-O3) | 33.1 to 36.6 (-O2), 36.8 to 42.5 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 24.6 to 31.3 (-O2), 24.1 to 31.7 (-O3) | 29.2 to 33.8 (-O2), 27.8 to 33.5 (-O3) | 63.4 to 63.8 (-O2), 56 to 56.7 (-O3) | 50 to 53.5 (-O2), 53.4 to 53.5 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 109 to 139 (-O2), 107 to 138 (-O3) | 111 to 141 (-O2), 116 to 130 (-O3) | 167 to 168 (-O2), 159 to 160 (-O3) | 129 to 134 |
| `sub`, 1 limb, N = 3 | 14 to 18.7 (-O2), 14.5 to 18.6 (-O3) | 10.8 to 12.3 (-O2), 12.3 to 14.6 (-O3) | 11.6 (-O2), 9.95 to 9.97 (-O3) | 8.81 to 8.86 |
| `sub`, 1 limb, N = 7 | 14.2 to 18.8 (-O2), 14.6 to 18.8 (-O3) | 5.83 to 8.36 (-O2), 11.9 to 14.4 (-O3) | 13.4 to 13.5 (-O2), 12.1 (-O3) | 9.66 to 9.78 |
| `sub`, 1 limb, N = 13 | 10.2 to 12.9 (-O2), 9.04 to 13.6 (-O3) | 6.78 to 8.64 (-O2), 11.6 to 14.8 (-O3) | 13.2 to 13.4 (-O2), 11.9 (-O3) | 10.3 to 10.5 |
| `sub`, 1 limb, N = 18 | 10.2 to 13 (-O2), 9.33 to 15.1 (-O3) | 7.34 to 9.03 (-O2), 6.88 to 8.26 (-O3) | 14.8 (-O2), 13.3 (-O3) | 11.2 to 11.3 |
| `sub`, 1 limb, N = 80 | 31.2 to 39.6 (-O2), 30.7 to 39.4 (-O3) | 36 to 40.1 (-O2), 32.1 to 38.7 (-O3) | 30.3 to 30.5 (-O2), 25.7 to 25.8 (-O3) | 21.5 to 21.6 (-O2), 19.5 to 19.7 (-O3) |
| `sub`, 2 limbs, N = 3 | 20.3 to 25.8 (-O2), 20.3 to 24.1 (-O3) | 11.1 to 13.5 (-O2), 11.6 to 14 (-O3) | 27.3 to 27.4 (-O2), 20 (-O3) | 18.2 to 18.3 |
| `sub`, 2 limbs, N = 7 | 11.7 to 14.9 (-O2), 11.9 to 14.2 (-O3) | 13.5 to 14.9 (-O2), 13 to 15.7 (-O3) | 32.4 to 32.6 (-O2), 26.9 (-O3) | 24.2 to 24.4 |
| `sub`, 2 limbs, N = 13 | 17.3 to 22.1 (-O2), 17.2 to 21.9 (-O3) | 19.4 to 21.8 (-O2), 18.4 to 22.4 (-O3) | 32.8 to 33 (-O2), 25.8 to 26 (-O3) | 24.9 to 25.3 |
| `sub`, 2 limbs, N = 18 | 22 to 28 (-O2), 21.6 to 27.4 (-O3) | 24 to 26.6 (-O2), 22.9 to 28 (-O3) | 41 to 42.9 (-O2), 37.2 to 38.1 (-O3) | 35.5 to 36 |
| `sub`, 2 limbs, N = 80 | 85.6 to 109 (-O2), 85 to 102 (-O3) | 94.5 to 103 (-O2), 92.1 to 111 (-O3) | 97.3 to 102 | 96.7 to 98.4 |
| `scale`, 1 limb, N = 3 | 15.3 to 19.7 (-O2), 15.3 to 19.7 (-O3) | 11.2 to 13.3 (-O2), 12.2 to 14.7 (-O3) | 11.6 to 11.7 (-O2), 10 to 13.3 (-O3) | 9.41 to 9.53 |
| `scale`, 1 limb, N = 7 | 15.6 to 19.8 (-O2), 15.6 to 19.8 (-O3) | 6.4 to 8.18 (-O2), 12.3 to 14.8 (-O3) | 12.3 (-O2), 10.8 to 11.2 (-O3) | 9.35 to 9.42 |
| `scale`, 1 limb, N = 13 | 14 to 18.7 (-O2), 13.7 to 19.8 (-O3) | 5.71 to 7.69 (-O2), 11.6 to 14.8 (-O3) | 12.1 (-O2), 10.9 to 11 (-O3) | 9.49 to 9.57 |
| `scale`, 1 limb, N = 18 | 9.21 to 13.3 (-O2), 11.4 to 14.9 (-O3) | 7.43 to 8.31 (-O2), 6.55 to 8.31 (-O3) | 13.7 to 13.8 (-O2), 12.3 to 12.4 (-O3) | 10.1 (-O2), 10.1 to 13.7 (-O3) |
| `scale`, 1 limb, N = 80 | 27.9 to 35.6 (-O2), 27.4 to 36.1 (-O3) | 31.2 to 37.3 (-O2), 29.5 to 35.7 (-O3) | 24.9 to 25.5 | 19.4 (-O2), 23.1 to 37.9 (-O3) |
| `scale`, 2 limbs, N = 3 | 16.4 to 21.1 (-O2), 16.3 to 21.1 (-O3) | 7.8 to 9.52 (-O2), 7.43 to 8.93 (-O3) | 19.3 to 19.4 (-O2), 12 (-O3) | 10.7 to 11.2 |
| `scale`, 2 limbs, N = 7 | 10.2 to 13.5 (-O2), 10.6 to 15.1 (-O3) | 8.71 to 9.84 (-O2), 7.95 to 9.62 (-O3) | 21.8 to 21.9 (-O2), 15.2 (-O3) | 13.7 to 13.8 |
| `scale`, 2 limbs, N = 13 | 10.2 to 13.1 (-O2), 10.7 to 15.2 (-O3) | 10.8 to 11.4 (-O2), 9.7 to 11.7 (-O3) | 24.4 to 24.5 (-O2), 17.6 to 17.7 (-O3) | 17.5 to 17.7 |
| `scale`, 2 limbs, N = 18 | 10.9 to 13.8 (-O2), 10.7 to 15.2 (-O3) | 11.5 to 13.2 (-O2), 11.2 to 13.4 (-O3) | 24.4 (-O2), 18 (-O3) | 15.4 to 15.5 |
| `scale`, 2 limbs, N = 80 | 41.6 to 53.2 (-O2), 42.1 to 51.2 (-O3) | 46.2 to 51 (-O2), 45.5 to 55 (-O3) | 52.3 to 52.4 (-O2), 47 to 47.1 (-O3) | 43.1 to 43.5 |
| `half`, 1 limb, N = 3 | 16.7 to 20 (-O2), 16.6 to 21.2 (-O3) | 5.76 to 7.5 (-O2), 11.3 to 12.7 (-O3) | 19.5 (-O2), 12.1 to 12.2 (-O3) | 15.9 to 16.1 |
| `half`, 1 limb, N = 7 | 16.7 to 20.6 (-O2), 16.7 to 21.2 (-O3) | 7 to 8.05 (-O2), 11.4 to 13.7 (-O3) | 20.9 to 21 (-O2), 14.8 to 14.9 (-O3) | 15.7 to 15.9 |
| `half`, 1 limb, N = 13 | 15.8 to 20.3 (-O2), 15.8 to 21 (-O3) | 8.03 to 10.2 (-O2), 10.8 to 13.8 (-O3) | 19.4 to 19.6 (-O2), 13.8 to 14.8 (-O3) | 15.7 to 19.7 (-O2), 15.7 to 15.8 (-O3) |
| `half`, 1 limb, N = 18 | 15.1 to 18.9 (-O2), 15.1 to 19.9 (-O3) | 10.5 to 12.3 (-O2), 9.3 to 10.4 (-O3) | 22.5 to 22.6 (-O2), 16.5 to 17.1 (-O3) | 16.7 to 16.9 |
| `half`, 1 limb, N = 80 | 36.2 to 46.1 (-O2), 36.6 to 46.6 (-O3) | 40 to 47.3 (-O2), 38.5 to 46.5 (-O3) | 38.4 to 38.7 (-O2), 34.4 to 34.6 (-O3) | 35.9 to 36.4 |
| `half`, 2 limbs, N = 3 | 16.8 to 21.4 (-O2), 16.8 to 21.4 (-O3) | 6.81 to 8.03 (-O2), 5.82 to 6.52 (-O3) | 23.4 to 23.6 (-O2), 18 to 18.1 (-O3) | 16 to 16.2 |
| `half`, 2 limbs, N = 7 | 15.5 to 20.6 (-O2), 16.1 to 21.4 (-O3) | 8.8 to 9.91 (-O2), 7.29 to 8.17 (-O3) | 26.3 to 27.4 (-O2), 22.1 to 22.2 (-O3) | 18.1 to 18.3 |
| `half`, 2 limbs, N = 13 | 16.2 to 21.3 (-O2), 16.1 to 21.2 (-O3) | 11.9 to 14.1 (-O2), 11.3 to 13.6 (-O3) | 24.3 to 24.4 (-O2), 18.8 to 18.9 (-O3) | 18.6 to 18.8 |
| `half`, 2 limbs, N = 18 | 14.9 to 21.2 (-O2), 15.2 to 21.1 (-O3) | 15.4 to 17 (-O2), 14.4 to 16.2 (-O3) | 29.1 to 29.2 (-O2), 24 to 24.1 (-O3) | 21.4 to 21.6 |
| `half`, 2 limbs, N = 80 | 50.9 to 61.3 (-O2), 50.9 to 65 (-O3) | 55.6 to 61.2 (-O2), 56.9 to 63.7 (-O3) | 58.1 to 58.4 (-O2), 52.6 to 52.8 (-O3) | 53.5 to 54.5 |
| the constructor, 1 limb, N = 3 | 16.8 to 18.5 (-O2), 14.7 to 18.6 (-O3) | 7.45 to 9.9 (-O2), 8.26 to 9.72 (-O3) | 17.8 to 18.7 (-O2), 17.8 (-O3) | 25.9 to 26.1 |
| the constructor, 1 limb, N = 7 | 21.1 to 23.1 (-O2), 21.2 to 21.8 (-O3) | 9.33 to 11.4 (-O2), 8.66 to 10.5 (-O3) | 20.4 to 21.1 | 28.1 to 29.3 (-O2), 28.1 to 30.3 (-O3) |
| the constructor, 1 limb, N = 13 | 26.3 to 34.9 (-O2), 26.1 to 33.5 (-O3) | 19.3 to 23.1 (-O2), 9.65 to 10.3 (-O3) | 26.5 to 26.6 (-O2), 23.7 (-O3) | 33 to 33.9 |
| the constructor, 1 limb, N = 18 | 21.1 to 27.3 (-O2), 25.8 to 35.2 (-O3) | 26.2 to 31.4 (-O2), 29.9 to 35.9 (-O3) | 30.9 to 31.7 | 25.2 to 25.5 (-O2), 36.2 to 37.3 (-O3) |
| the constructor, 1 limb, N = 80 | 74 to 90.4 (-O2), 78.5 to 102 (-O3) | 221 to 265 (-O2), 252 to 302 (-O3) | 148 to 151 | 72 to 75.2 |
| the constructor, 2 limbs, N = 3 | 15.5 to 17.8 (-O2), 13.8 to 18.4 (-O3) | 7.61 to 8.89 (-O2), 8.25 to 9.36 (-O3) | 17.4 to 17.8 | 11.9 to 17.8 (-O2), 17.2 to 17.4 (-O3) |
| the constructor, 2 limbs, N = 7 | 21.1 to 27 (-O2), 21.6 to 27.7 (-O3) | 14.4 to 15.8 (-O2), 8.07 to 9.45 (-O3) | 22 to 22.1 (-O2), 20.2 to 21.9 (-O3) | 15.2 to 19 (-O2), 18.7 to 18.9 (-O3) |
| the constructor, 2 limbs, N = 13 | 23.6 to 32.2 (-O2), 24.8 to 31 (-O3) | 28.3 to 33.8 (-O2), 11.9 to 14.4 (-O3) | 40.9 to 42 (-O2), 23.6 to 24 (-O3) | 22.3 to 23.2 |
| the constructor, 2 limbs, N = 18 | 23.2 to 29.6 (-O2), 23.5 to 28.1 (-O3) | 42.9 to 51.6 (-O2), 41.5 to 51.4 (-O3) | 49.2 to 49.3 (-O2), 33.7 to 34 (-O3) | 34.3 to 36.5 (-O2), 35.8 to 36.2 (-O3) |
| the constructor, 2 limbs, N = 80 | 99.6 to 119 (-O2), 96.2 to 122 (-O3) | 305 to 365 (-O2), 324 to 380 (-O3) | 209 to 212 (-O2), 160 to 161 (-O3) | 100 to 105 |

| Short ball vectors, one operation per unit, a dependent chain: the check, ns per operation (with minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | -0.59 to 0.33 (-O2), -0.08 to 1.06 (-O3) | 5.22 to 8.05 (-O2), 6.61 to 7.21 (-O3) | 2.13 to 2.19 (-O2), 3.15 to 3.27 (-O3) | -0.235 to -0.151 (-O2), -0.287 to -0.158 (-O3) |
| `add(x, y, z)`, 1 limb, N = 7 | -0.42 to 0.74 (-O2), 0 to 1.7 (-O3) | 0.418 to 1.53 (-O2), 5.9 to 6.22 (-O3) | 1.9 to 3.54 (-O2), 1.2 to 1.28 (-O3) | 0.572 to 0.679 (-O2), 0.606 to 0.755 (-O3) |
| `add(x, y, z)`, 1 limb, N = 13 | -5.05 to -4.86 (-O2), -5.09 to -4.12 (-O3) | -0.03 to 0.278 (-O2), 6.14 to 7.87 (-O3) | 1.75 to 1.76 (-O2), 1.31 to 1.58 (-O3) | 1.26 to 1.33 (-O2), -0.53 to 1.37 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | -0.241 to 0.89 (-O2), -0.3 to 1.14 (-O3) | 0.139 to 0.222 (-O2), 1.07 to 1.71 (-O3) | 1.86 to 1.9 (-O2), 1.75 to 1.87 (-O3) | 2 to 2.04 (-O2), 1.87 to 1.96 (-O3) |
| `add(x, y, z)`, 1 limb, N = 80 | -0.34 to 2.18 (-O2), -0.12 to 3.92 (-O3) | -1.57 to 1.31 (-O2), -1.99 to 0.78 (-O3) | 5.49 to 5.63 (-O2), 3.67 to 4.03 (-O3) | 3.31 to 3.42 (-O2), 2.52 to 2.87 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | -0.32 to 0.78 (-O2), -0.59 to 3.01 (-O3) | -0.31 to 0.24 (-O2), -1.86 to 0.15 (-O3) | 2.69 to 2.82 (-O2), 1.37 to 1.66 (-O3) | 1.75 to 1.87 (-O2), 1.8 to 2.03 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | 0.09 to 0.57 (-O2), -0.49 to 2.32 (-O3) | -0.11 to 0.58 (-O2), -1.05 to 0.23 (-O3) | 2.19 to 2.55 (-O2), -0.25 to 0.07 (-O3) | 1.7 to 1.9 (-O2), 1.36 to 1.69 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | 0.31 to 1.57 (-O2), -0.13 to 1.59 (-O3) | -1.12 to 0.36 (-O2), -0.59 to 0.5 (-O3) | 2.26 to 2.67 (-O2), -1.01 to -0.3 (-O3) | 2.29 to 2.46 (-O2), 2.12 to 2.5 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -0.05 to 1.9 (-O2), -0.3 to 2.67 (-O3) | -0.55 to 2.32 (-O2), -1.11 to 0.6 (-O3) | 3.42 to 3.73 (-O2), 3.78 to 3.99 (-O3) | 3.66 to 4.21 (-O2), 3.79 to 4.36 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -0.26 to 3.87 (-O2), 0.03 to 6.3 (-O3) | -5.08 to 1.5 (-O2), -5.44 to 1.81 (-O3) | 4.81 to 5.58 (-O2), 3.91 to 5.54 (-O3) | 5.03 to 5.83 (-O2), 4.42 to 6.11 (-O3) |
| `z = x + y`, 1 limb, N = 3 | -0.22 to 1.12 (-O2), -0.25 to 2.14 (-O3) | 7.92 to 8.53 (-O2), 7.46 to 8.92 (-O3) | -0.04 to 0.36 (-O2), 0.73 to 1.27 (-O3) | 0.07 to 0.19 (-O2), -0.01 to 0.2 (-O3) |
| `z = x + y`, 1 limb, N = 7 | 0 to 1.42 (-O2), 0 to 0.96 (-O3) | -1.18 to -0.18 (-O2), -2.42 to -1.42 (-O3) | 0.05 to 0.21 (-O2), 0.39 to 1.04 (-O3) | -0.1 to 0.02 (-O2), -0.27 to -0.03 (-O3) |
| `z = x + y`, 1 limb, N = 13 | -0.77 to 1.48 (-O2), -0.45 to 1.81 (-O3) | -2.44 to -0.08 (-O2), -1.17 to 0 (-O3) | -0.07 to 0.03 (-O2), -1.23 to -0.93 (-O3) | -0.15 to 0.03 (-O2), -0.21 to 0.12 (-O3) |
| `z = x + y`, 1 limb, N = 18 | -0.53 to 0.44 (-O2), -0.67 to 1.69 (-O3) | 1.18 to 1.85 (-O2), -0.46 to -0.118 (-O3) | -0.3 to 0.02 (-O2), -1.75 to -0.58 (-O3) | 0.31 to 0.63 (-O2), 0.48 to 0.81 (-O3) |
| `z = x + y`, 1 limb, N = 80 | -0.01 to 5.38 (-O2), -0.31 to 5.46 (-O3) | -0.87 to 0.02 (-O2), -3.4 to 0.35 (-O3) | 4.12 to 4.69 (-O2), 5.09 to 6.39 (-O3) | -4.64 to 0.84 (-O2), 0.77 to 3.55 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -0.14 to 1.51 (-O2), -0.63 to 1.66 (-O3) | -1.15 to -0.02 (-O2), 3.58 to 3.89 (-O3) | 0.1 to 0.73 (-O2), -0.53 to 0.56 (-O3) | -0.49 to 1.79 (-O2), 0.42 to 2.85 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 0.08 to 0.99 (-O2), -0.09 to 1.04 (-O3) | -1.29 to -0.1 (-O2), -0.17 to 1.68 (-O3) | 0.53 to 9.31 (-O2), 0.16 to 1.06 (-O3) | -13 to 1.05 (-O2), 0.87 to 1.09 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 0.1 to 0.21 (-O2), 0.08 to 2.55 (-O3) | 0.74 to 1.77 (-O2), -0.14 to 1.5 (-O3) | -0.45 to 0.88 (-O2), -1.28 to 1.43 (-O3) | -3.06 to 0.11 (-O2), -0.97 to 7.95 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -0.77 to -0.43 (-O2), -0.83 to 1.94 (-O3) | -2.04 to 0.38 (-O2), -0.87 to 1.4 (-O3) | 0.33 to 0.66 (-O2), 0.21 to 1.71 (-O3) | -3.09 to -0.21 (-O2), 0.01 to 3.38 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 0.7 to 2.2 (-O2), -1.4 to 8.8 (-O3) | -9 to 0.4 (-O2), -11.2 to 3.7 (-O3) | 1.1 to 2.1 (-O2), -2.4 to 0.7 (-O3) | -1.2 to 2.2 (-O2), 0.5 to 7.2 (-O3) |
| `sub`, 1 limb, N = 3 | -0.51 to 0.23 (-O2), -0.61 to 1.05 (-O3) | 5.73 to 6.41 (-O2), 6.69 to 7.48 (-O3) | 2.11 to 2.13 (-O2), 3.15 to 3.25 (-O3) | -0.184 to -0.163 (-O2), -0.195 to -0.154 (-O3) |
| `sub`, 1 limb, N = 7 | -0.66 to 0.21 (-O2), -0.64 to 1.14 (-O3) | 0.115 to 1.61 (-O2), 6.03 to 7.2 (-O3) | 1.8 to 1.91 (-O2), 1.19 to 1.25 (-O3) | 0.69 to 0.76 (-O2), 0.688 to 0.768 (-O3) |
| `sub`, 1 limb, N = 13 | -5.79 to -2.75 (-O2), -4.74 to -4.02 (-O3) | 0.3 to 1.4 (-O2), 6.2 to 7.54 (-O3) | -0.1 to 2.03 (-O2), 1.46 to 1.56 (-O3) | 1.28 to 1.36 (-O2), -0.74 to 1.34 (-O3) |
| `sub`, 1 limb, N = 18 | -1.7 to 0.28 (-O2), -1.47 to 1.38 (-O3) | 0.191 to 0.676 (-O2), -0.04 to 0.604 (-O3) | 1.75 to 1.77 (-O2), 1.72 to 1.86 (-O3) | -0.42 to 2.06 (-O2), 0.72 to 1.94 (-O3) |
| `sub`, 1 limb, N = 80 | 0.41 to 0.84 (-O2), -1.87 to 2.25 (-O3) | -1.67 to 0.25 (-O2), -1.77 to 1.62 (-O3) | 5.11 to 5.26 (-O2), 1.45 to 1.87 (-O3) | 3.24 to 3.34 (-O2), 2.25 to 2.74 (-O3) |
| `sub`, 2 limbs, N = 3 | -0.03 to 0.99 (-O2), -0.23 to 0.86 (-O3) | -0.74 to -0.19 (-O2), -1.31 to 0.38 (-O3) | 2.69 to 2.82 (-O2), 1.84 to 2.05 (-O3) | 2.09 to 2.23 (-O2), 2.1 to 2.27 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.51 to 0 (-O2), -0.6 to 0.6 (-O3) | -0.91 to 0.15 (-O2), -0.94 to -0.05 (-O3) | 1.81 to 2.11 (-O2), 0.55 to 0.84 (-O3) | 2.34 to 2.53 (-O2), 2.36 to 2.58 (-O3) |
| `sub`, 2 limbs, N = 13 | 0.09 to 0.11 (-O2), -1.21 to 1.19 (-O3) | -0.66 to 0.42 (-O2), -0.59 to 1.09 (-O3) | 2.38 to 2.65 (-O2), -0.74 to -0.32 (-O3) | 2.26 to 2.58 (-O2), 2.26 to 2.64 (-O3) |
| `sub`, 2 limbs, N = 18 | -0.42 to 0.98 (-O2), -0.05 to 1.57 (-O3) | -0.91 to 0.6 (-O2), -0.55 to 1.39 (-O3) | 2.64 to 4.63 (-O2), 3.56 to 3.9 (-O3) | 4.06 to 4.5 (-O2), 4.55 to 4.69 (-O3) |
| `sub`, 2 limbs, N = 80 | 1 to 3.44 (-O2), -0.7 to 5.48 (-O3) | -5.3 to 2.21 (-O2), 1.8 to 7.68 (-O3) | 2.95 to 4.24 (-O2), 3.08 to 4.4 (-O3) | 5.23 to 5.9 (-O2), 5.34 to 5.88 (-O3) |
| `scale`, 1 limb, N = 3 | 5.52 to 8.2 (-O2), 5.56 to 8.02 (-O3) | 5.71 to 8.96 (-O2), 6.54 to 7.57 (-O3) | -0.22 to 2.83 (-O2), 2.65 to 5.86 (-O3) | 2.49 to 2.6 |
| `scale`, 1 limb, N = 7 | 5.72 to 7.27 (-O2), 5.71 to 8.01 (-O3) | 1.13 to 2.37 (-O2), 6.26 to 7.57 (-O3) | 1.9 to 1.98 (-O2), 1.78 to 2 (-O3) | 2.34 to 2.43 |
| `scale`, 1 limb, N = 13 | 4.81 to 6.97 (-O2), 3.79 to 7.94 (-O3) | 0.027 to 0.457 (-O2), 6.54 to 7.07 (-O3) | 2.1 to 2.11 (-O2), 1.86 to 2.02 (-O3) | 2.46 to 2.57 |
| `scale`, 1 limb, N = 18 | -0.785 to 0.591 (-O2), 1.73 to 2.93 (-O3) | 0.422 to 1.65 (-O2), 0.364 to 0.597 (-O3) | 2.2 to 2.24 (-O2), 2.18 to 2.37 (-O3) | 2.91 to 2.92 (-O2), 2.84 to 6.46 (-O3) |
| `scale`, 1 limb, N = 80 | 0.61 to 0.65 (-O2), -0.69 to 2.08 (-O3) | -1.41 to 0.79 (-O2), 0.43 to 2.6 (-O3) | 1.99 to 2.08 (-O2), 3.64 to 4.09 (-O3) | 3.58 to 3.69 (-O2), 1.86 to 16.6 (-O3) |
| `scale`, 2 limbs, N = 3 | 6.26 to 8.27 (-O2), 6.18 to 8.99 (-O3) | -0.293 to 1.43 (-O2), -0.998 to 0.355 (-O3) | 2.39 to 2.54 (-O2), 1.5 to 1.64 (-O3) | 2.67 to 2.77 (-O2), 0.16 to 2.35 (-O3) |
| `scale`, 2 limbs, N = 7 | 0.01 to 0.86 (-O2), -0.1 to 2.94 (-O3) | -0.081 to 0.241 (-O2), -0.756 to -0.013 (-O3) | 2.72 to 2.81 (-O2), 0.43 to 0.62 (-O3) | 4.17 to 4.21 (-O2), 3.98 to 4.14 (-O3) |
| `scale`, 2 limbs, N = 13 | -0.56 to 0.08 (-O2), -0.7 to 1.63 (-O3) | -0.57 to 1.41 (-O2), 0.08 to 0.488 (-O3) | 3.57 to 3.62 (-O2), 2.12 to 2.3 (-O3) | 4.11 to 4.25 |
| `scale`, 2 limbs, N = 18 | -0.52 to 0.35 (-O2), -0.8 to 1.33 (-O3) | -0.64 to 0.12 (-O2), -0.35 to 0.85 (-O3) | 2.35 to 2.45 (-O2), 0.8 to 1.01 (-O3) | -0.62 to 1.78 (-O2), -0.62 to 1.79 (-O3) |
| `scale`, 2 limbs, N = 80 | 0.86 to 4.49 (-O2), -0.15 to 0.15 (-O3) | -2.83 to 1.07 (-O2), 1.03 to 2.44 (-O3) | 3.74 to 3.93 (-O2), -0.03 to 0.63 (-O3) | 1.36 to 1.72 (-O2), 1.41 to 1.81 (-O3) |
| `half`, 1 limb, N = 3 | -0.07 to 0.94 (-O2), 0.99 to 3.22 (-O3) | -1.73 to -0.475 (-O2), 6.21 to 7.01 (-O3) | 2.41 to 2.43 (-O2), 2.9 to 3.1 (-O3) | 1.02 to 1.1 (-O2), 0.91 to 1.16 (-O3) |
| `half`, 1 limb, N = 7 | 0.82 to 1.52 (-O2), 0.8 to 3.17 (-O3) | -1.19 to 0.121 (-O2), 6.37 to 7.62 (-O3) | 2.44 to 2.48 (-O2), 2.59 to 2.81 (-O3) | 0.36 to 0.47 (-O2), 0.21 to 0.52 (-O3) |
| `half`, 1 limb, N = 13 | -0.54 to 0.16 (-O2), -0.17 to 1.93 (-O3) | -0.366 to 0.354 (-O2), 4.05 to 5.3 (-O3) | 1.94 to 2.57 (-O2), 2.38 to 3.14 (-O3) | -0.03 to 3.84 (-O2), -0.19 to 0.07 (-O3) |
| `half`, 1 limb, N = 18 | -1.23 to 0 (-O2), -0.18 to 0.93 (-O3) | 0.27 to 0.36 (-O2), -0.32 to 0.762 (-O3) | 3.18 to 3.21 (-O2), 2.38 to 3.17 (-O3) | -1.11 to -1.03 (-O2), -1.27 to -0.98 (-O3) |
| `half`, 1 limb, N = 80 | 0.11 to 2.8 (-O2), -0.13 to 2.57 (-O3) | -0.81 to 2.33 (-O2), -0.84 to 1.36 (-O3) | 3.33 to 3.74 (-O2), 4.17 to 4.85 (-O3) | 5.26 to 6.05 (-O2), 4.15 to 5.57 (-O3) |
| `half`, 2 limbs, N = 3 | 1.37 to 2.91 (-O2), 1.48 to 3.79 (-O3) | -0.832 to -0.383 (-O2), -1.83 to 0.345 (-O3) | 2.48 to 2.68 (-O2), 3.93 to 4.1 (-O3) | 0.55 to 0.71 (-O2), 0.54 to 0.8 (-O3) |
| `half`, 2 limbs, N = 7 | -0.5 to 1.47 (-O2), -0.12 to 3.22 (-O3) | 0.1 to 0.32 (-O2), -0.967 to 0.579 (-O3) | 1.32 to 2.49 (-O2), 3 to 3.28 (-O3) | 2.46 to 2.52 (-O2), 1.9 to 2.18 (-O3) |
| `half`, 2 limbs, N = 13 | 0 to 1.91 (-O2), -0.66 to 2.06 (-O3) | -0.49 to 0.47 (-O2), 0.15 to 1.01 (-O3) | 1.49 to 1.71 (-O2), 3.04 to 3.35 (-O3) | 2.48 to 2.73 (-O2), 2.21 to 2.52 (-O3) |
| `half`, 2 limbs, N = 18 | 0.01 to 2.17 (-O2), 0.38 to 4.17 (-O3) | 0.13 to 0.17 (-O2), -1.03 to 0.63 (-O3) | 1.43 to 1.52 (-O2), 1.98 to 3.47 (-O3) | 2.54 to 2.74 (-O2), 2.31 to 2.67 (-O3) |
| `half`, 2 limbs, N = 80 | 0.18 to 0.61 (-O2), 0.14 to 7.29 (-O3) | 0.15 to 0.19 (-O2), -3.79 to 3.18 (-O3) | 3.31 to 3.53 (-O2), 4.03 to 5.04 (-O3) | 5.53 to 6.25 (-O2), 4.97 to 6.3 (-O3) |
| the constructor, 1 limb, N = 3 | 5.22 to 6.13 (-O2), 4.39 to 5.8 (-O3) | -1.49 to 0.117 (-O2), -0.058 to 0.576 (-O3) | 2.7 to 3.62 (-O2), 2.68 to 3.02 (-O3) | 19.6 to 19.9 |
| the constructor, 1 limb, N = 7 | -0.63 to 1.06 (-O2), -1.13 to 0.1 (-O3) | -8.37 to -5.55 (-O2), -0.032 to 0.376 (-O3) | 4.36 to 4.5 (-O2), 5.23 to 5.53 (-O3) | -0.16 to 1.29 (-O2), -1.26 to 2.06 (-O3) |
| the constructor, 1 limb, N = 13 | -0.16 to 2.68 (-O2), -0.23 to 3.03 (-O3) | -1.91 to 0.08 (-O2), -0.21 to 1.33 (-O3) | 2.67 to 2.75 (-O2), 3.5 to 3.73 (-O3) | -0.28 to 0.27 (-O2), 0.11 to 0.62 (-O3) |
| the constructor, 1 limb, N = 18 | -3.53 to -1.66 (-O2), -3.33 to 1.43 (-O3) | -2.02 to 0.28 (-O2), -0.55 to 1.66 (-O3) | 2.13 to 2.84 (-O2), 2.34 to 3.05 (-O3) | 0.2 to 0.86 (-O2), 0.51 to 2.45 (-O3) |
| the constructor, 1 limb, N = 80 | -1.83 to 2.12 (-O2), -2.1 to 10.9 (-O3) | -18.7 to 0.8 (-O2), -13.5 to 14.3 (-O3) | 1.7 to 4.9 (-O2), 1.5 to 3.5 (-O3) | 4.25 to 7.59 (-O2), 3.45 to 7.44 (-O3) |
| the constructor, 2 limbs, N = 3 | 4.27 to 4.39 (-O2), 2.55 to 6.97 (-O3) | -0.749 to 0.026 (-O2), -0.4 to 0.355 (-O3) | 2.73 to 3 (-O2), 1.87 to 2.66 (-O3) | 3.58 to 9.46 (-O2), 8.98 to 9.14 (-O3) |
| the constructor, 2 limbs, N = 7 | 0.29 to 0.98 (-O2), -0.59 to 3.05 (-O3) | -0.23 to -0.11 (-O2), -1.09 to -0.023 (-O3) | 0.97 to 3.91 (-O2), 4.8 to 6.76 (-O3) | -1.68 to 3.65 (-O2), 1.85 to 2.98 (-O3) |
| the constructor, 2 limbs, N = 13 | -1.74 to 1.4 (-O2), -0.4 to 4.27 (-O3) | -2.34 to 0.19 (-O2), 0.15 to 1.26 (-O3) | 0.7 to 1.48 (-O2), 1.07 to 1.58 (-O3) | 1.14 to 1.35 (-O2), 0.16 to 2.14 (-O3) |
| the constructor, 2 limbs, N = 18 | -0.55 to 1.01 (-O2), -0.25 to 1.05 (-O3) | -3.36 to 0.57 (-O2), -0.16 to 1.61 (-O3) | 0.97 to 1.79 (-O2), -7.4 to -7.09 (-O3) | 0.24 to 2.23 (-O2), 1.72 to 4.58 (-O3) |
| the constructor, 2 limbs, N = 80 | -3.1 to 7.38 (-O2), -2.71 to 12.8 (-O3) | -24 to 0.6 (-O2), -8 to 14.2 (-O3) | 20.7 to 25.1 (-O2), -4.6 to -2.2 (-O3) | 0.33 to 4.5 (-O2), 2.6 to 8.94 (-O3) |

| Short ball vectors, one operation per unit, a dependent chain: the check with its report cold, ns per operation (minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | -1.24 to 0.55 (-O2), -0.32 to 0.87 (-O3) | 5.87 to 8.87 (-O2), 4.43 to 7.71 (-O3) | 1.87 to 1.89 (-O2), 2.26 to 2.38 (-O3) | -0.18 to -0.135 (-O2), -0.261 to -0.145 (-O3) |
| `add(x, y, z)`, 1 limb, N = 7 | -1 to 0.61 (-O2), 0.26 to 0.76 (-O3) | -0.028 to 0.749 (-O2), 4.13 to 7.58 (-O3) | 1.73 to 2.64 (-O2), 1.03 to 1.17 (-O3) | 0.678 to 0.731 (-O2), 0.673 to 0.746 (-O3) |
| `add(x, y, z)`, 1 limb, N = 13 | -0.76 to 1.34 (-O2), -0.17 to 2.07 (-O3) | 0.264 to 1.39 (-O2), 4.28 to 7.2 (-O3) | 1.7 to 1.73 (-O2), 1.52 to 1.69 (-O3) | 1.19 to 1.35 (-O2), -0.66 to 1.25 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | 0.52 to 1.32 (-O2), -0.95 to 1.15 (-O3) | 0.215 to 0.76 (-O2), -0.896 to 0.699 (-O3) | 1.68 to 1.69 (-O2), 1.56 to 1.67 (-O3) | 1.78 to 1.88 (-O2), 1.71 to 1.83 (-O3) |
| `add(x, y, z)`, 1 limb, N = 80 | -0.7 to 1.96 (-O2), 0.38 to 1.98 (-O3) | 0.92 to 3.21 (-O2), -6.96 to 0.69 (-O3) | 5.49 to 5.58 (-O2), 3.64 to 3.75 (-O3) | 3.28 to 3.39 (-O2), 3.14 to 3.32 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | -0.2 to 0.83 (-O2), -0.02 to 1.15 (-O3) | -0.15 to 0.88 (-O2), -4.28 to 0.12 (-O3) | 2.65 to 2.69 (-O2), 0.24 to 0.55 (-O3) | 1.97 to 2.01 (-O2), 1.88 to 2.11 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | -0.01 to 0.81 (-O2), -0.33 to 0.69 (-O3) | 0 to 0.4 (-O2), -3.86 to 0.08 (-O3) | 2.26 to 2.88 (-O2), -0.86 to -0.43 (-O3) | 1.72 to 1.74 (-O2), 1.73 to 1.97 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | 0.03 to 1.57 (-O2), 0.03 to 1.55 (-O3) | 0.27 to 0.36 (-O2), -4.05 to 0.2 (-O3) | 1.86 to 2.24 (-O2), -1.39 to -0.63 (-O3) | 2.2 to 2.37 (-O2), 2.12 to 2.54 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -0.18 to 1.36 (-O2), 0.25 to 1.38 (-O3) | 0.83 to 1.47 (-O2), -5.94 to 0.45 (-O3) | 3.11 to 4.21 (-O2), 3.94 to 4.22 (-O3) | 3.89 to 4.34 (-O2), 4.19 to 4.79 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -0.27 to 4.37 (-O2), -0.26 to 0.15 (-O3) | 0.3 to 4.52 (-O2), -24.1 to 0.47 (-O3) | 4.37 to 4.97 (-O2), 3.59 to 5.11 (-O3) | 5.49 to 5.89 (-O2), 4.42 to 5.53 (-O3) |
| `z = x + y`, 1 limb, N = 3 | 0 to 1.49 (-O2), 0 to 0.86 (-O3) | 8.08 to 8.46 (-O2), 3.66 to 8.77 (-O3) | 0.06 to 0.48 (-O2), -0.18 to 0.75 (-O3) | 0.15 to 0.21 (-O2), 0.08 to 0.24 (-O3) |
| `z = x + y`, 1 limb, N = 7 | 0 to 1.44 (-O2), 0 to 0.82 (-O3) | 0.02 to 0.99 (-O2), -3.37 to -0.04 (-O3) | 0.32 to 0.5 (-O2), -0.61 to 0.14 (-O3) | -0.2 to 0.02 (-O2), -0.26 to -0.14 (-O3) |
| `z = x + y`, 1 limb, N = 13 | 0.12 to 1.23 (-O2), -2.16 to 0.01 (-O3) | -1.54 to 0.02 (-O2), -3.37 to -1.17 (-O3) | -0.15 to -0.08 (-O2), -0.48 to -0.18 (-O3) | 0.11 to 0.2 (-O2), 0.01 to 0.24 (-O3) |
| `z = x + y`, 1 limb, N = 18 | -0.33 to 0.66 (-O2), -0.69 to 0.69 (-O3) | -0.38 to -0.07 (-O2), -2.4 to -0.7 (-O3) | -0.23 to 0.1 (-O2), -0.29 to 0.3 (-O3) | 0.64 to 0.7 (-O2), 0.26 to 0.6 (-O3) |
| `z = x + y`, 1 limb, N = 80 | 0.75 to 4.61 (-O2), -0.04 to 4.31 (-O3) | -0.26 to 3.71 (-O2), -11.6 to -0.02 (-O3) | 4.93 to 5.51 (-O2), 4.41 to 27.5 (-O3) | -3.71 to -0.61 (-O2), 1.27 to 3.94 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -0.02 to 1.79 (-O2), -1.1 to 1.29 (-O3) | -0.03 to 0.69 (-O2), -2.89 to 0.69 (-O3) | 0.03 to 0.6 (-O2), -0.44 to 0.83 (-O3) | 0.39 to 0.83 (-O2), 0.41 to 2.55 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | -0.01 to 1.35 (-O2), -0.49 to 27.4 (-O3) | -0.01 to 0.66 (-O2), -3.86 to 0.47 (-O3) | 0.42 to 6.85 (-O2), -0.27 to 0.83 (-O3) | -12.7 to 0.99 (-O2), 0.7 to 1.14 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 0.11 to 1.71 (-O2), 0.23 to 3.12 (-O3) | 0.18 to 3.09 (-O2), -5.52 to 0.1 (-O3) | -0.89 to 0.7 (-O2), -2.31 to 0.38 (-O3) | -0.22 to 0.67 (-O2), -0.05 to 3.11 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -0.3 to 1.61 (-O2), 0.05 to 1.34 (-O3) | -0.16 to 0.56 (-O2), -6.09 to 1.22 (-O3) | 0.63 to 1.06 (-O2), 0 to 0.74 (-O3) | 0.03 to 0.21 (-O2), -0.13 to 3.63 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 0.8 to 9.9 (-O2), 0.4 to 8.7 (-O3) | 0.2 to 0.6 (-O2), -29 to 3.9 (-O3) | -0.1 to 0.8 (-O2), -1.1 to 1.6 (-O3) | -0.2 to 2 (-O2), 1.2 to 5.3 (-O3) |
| `sub`, 1 limb, N = 3 | -0.91 to 0.49 (-O2), -0.22 to 0.72 (-O3) | 6.14 to 7.16 (-O2), 4.21 to 6.68 (-O3) | 1.71 to 1.84 (-O2), 2.27 to 2.37 (-O3) | -0.175 to -0.143 (-O2), -0.222 to -0.15 (-O3) |
| `sub`, 1 limb, N = 7 | -0.89 to 0.62 (-O2), -0.19 to 0.47 (-O3) | -0.528 to 1.08 (-O2), 4.12 to 6.83 (-O3) | 1.76 to 1.77 (-O2), 1.04 to 1.14 (-O3) | 0.687 to 0.758 (-O2), 0.728 to 0.775 (-O3) |
| `sub`, 1 limb, N = 13 | -1.13 to 2 (-O2), -0.24 to 0.81 (-O3) | 0.002 to 0.887 (-O2), 4.07 to 7.57 (-O3) | -0.25 to 1.67 (-O2), 1.39 to 1.52 (-O3) | 1.21 to 1.26 (-O2), -0.51 to 2.76 (-O3) |
| `sub`, 1 limb, N = 18 | -1.04 to 0.06 (-O2), -2.2 to 0.413 (-O3) | 0.188 to 0.765 (-O2), -1.33 to 1.39 (-O3) | 1.56 to 1.61 (-O2), 1.5 to 1.65 (-O3) | -0.67 to 5.7 (-O2), 0.6 to 1.83 (-O3) |
| `sub`, 1 limb, N = 80 | -1.7 to 1.39 (-O2), -0.12 to 0.21 (-O3) | 1.51 to 2.41 (-O2), -7.27 to 1.78 (-O3) | 4.89 to 4.95 (-O2), 1.4 to 1.79 (-O3) | 3.16 to 3.25 (-O2), 2.75 to 3.21 (-O3) |
| `sub`, 2 limbs, N = 3 | -0.34 to 1.87 (-O2), 0.23 to 1.89 (-O3) | -0.18 to 0.13 (-O2), -3.89 to 0.46 (-O3) | 2.53 to 2.63 (-O2), 0.89 to 1.08 (-O3) | 2.3 to 2.35 (-O2), 2.27 to 2.41 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.07 to 0.32 (-O2), -0.67 to 0.9 (-O3) | -0.21 to 0.01 (-O2), -3.8 to 0.06 (-O3) | 1.87 to 1.9 (-O2), 0.28 to 0.46 (-O3) | 2.76 to 2.79 (-O2), 2.67 to 2.88 (-O3) |
| `sub`, 2 limbs, N = 13 | -0.22 to 0.85 (-O2), 0.13 to 0.31 (-O3) | -0.42 to 0.18 (-O2), -4.17 to 0.94 (-O3) | 1.85 to 2.37 (-O2), -1.23 to -0.7 (-O3) | 2.65 to 2.94 (-O2), 2.62 to 2.96 (-O3) |
| `sub`, 2 limbs, N = 18 | -0.59 to 1.69 (-O2), 0.21 to 0.6 (-O3) | 0.9 to 2.08 (-O2), -5.28 to 1.07 (-O3) | 2.97 to 4.12 (-O2), 3.42 to 3.73 (-O3) | 4.98 to 5.25 (-O2), 4.87 to 5.26 (-O3) |
| `sub`, 2 limbs, N = 80 | 0.3 to 3.58 (-O2), -0.6 to 5.52 (-O3) | 2.54 to 4.26 (-O2), -16.5 to 3.07 (-O3) | 2.85 to 5.24 (-O2), 2.91 to 4.25 (-O3) | 5.63 to 5.9 (-O2), 4.77 to 5.26 (-O3) |
| `scale`, 1 limb, N = 3 | 5.55 to 8.28 (-O2), 5.55 to 6.63 (-O3) | 6.77 to 9.8 (-O2), 4.95 to 7.61 (-O3) | -0.76 to 2.36 (-O2), 2.55 to 5.56 (-O3) | 2.42 to 2.48 |
| `scale`, 1 limb, N = 7 | 5.74 to 7.27 (-O2), 5.71 to 6.82 (-O3) | 0.564 to 2.36 (-O2), 4.49 to 7.03 (-O3) | 1.5 to 1.58 (-O2), 1.82 to 1.93 (-O3) | 2.37 to 2.43 |
| `scale`, 1 limb, N = 13 | 5.47 to 6.92 (-O2), 5.23 to 6.85 (-O3) | 0.27 to 2.23 (-O2), 4.42 to 7.44 (-O3) | 1.91 to 2.03 (-O2), 1.83 to 5.28 (-O3) | 2.41 to 2.55 (-O2), 2.36 to 2.47 (-O3) |
| `scale`, 1 limb, N = 18 | -1.18 to 0.581 (-O2), 0.487 to 2.47 (-O3) | 0.428 to 1.67 (-O2), -0.747 to 2.21 (-O3) | 1.99 to 2.06 (-O2), 2.11 to 2.22 (-O3) | 2.61 to 2.71 |
| `scale`, 1 limb, N = 80 | 0.41 to 2.92 (-O2), 0.12 to 0.72 (-O3) | 0.49 to 3.14 (-O2), -4.85 to 1.62 (-O3) | 4.49 to 5.34 (-O2), 3.23 to 3.64 (-O3) | 3.42 to 3.5 (-O2), 1.69 to 2.83 (-O3) |
| `scale`, 2 limbs, N = 3 | 6.49 to 7.64 (-O2), 6.59 to 7.71 (-O3) | -0.368 to 1.86 (-O2), -2.06 to 0.422 (-O3) | 2.21 to 2.42 (-O2), -0.22 to -0.09 (-O3) | 2.89 to 2.91 (-O2), 0.82 to 5.7 (-O3) |
| `scale`, 2 limbs, N = 7 | 6.45 to 7.97 (-O2), 6.48 to 8.29 (-O3) | -0.026 to 0.394 (-O2), -2.04 to 0.045 (-O3) | 2.48 to 2.73 (-O2), 0.23 to 0.41 (-O3) | 2.06 to 2.17 (-O2), 1.96 to 2.11 (-O3) |
| `scale`, 2 limbs, N = 13 | -2.23 to 1.47 (-O2), -2.09 to 0.54 (-O3) | 0.02 to 0.86 (-O2), -2.14 to 0.406 (-O3) | 3.94 to 4.12 (-O2), 5.43 to 5.67 (-O3) | 4.61 to 4.67 (-O2), 4.57 to 8.13 (-O3) |
| `scale`, 2 limbs, N = 18 | -0.18 to 1.39 (-O2), -0.76 to 0.06 (-O3) | 0.16 to 0.72 (-O2), -3.15 to 0.45 (-O3) | 2.29 to 2.39 (-O2), 0.58 to 0.86 (-O3) | -0.55 to 3.93 (-O2), -0.52 to 1.88 (-O3) |
| `scale`, 2 limbs, N = 80 | -2.15 to 4.32 (-O2), 0.11 to 0.87 (-O3) | 0.34 to 0.41 (-O2), -7.33 to 2.5 (-O3) | 3.38 to 3.42 (-O2), 0.07 to 0.65 (-O3) | 1.57 to 1.72 (-O2), 1.39 to 1.9 (-O3) |
| `half`, 1 limb, N = 3 | 0.86 to 1.97 (-O2), 1.18 to 1.89 (-O3) | -1.38 to 0.086 (-O2), 3.92 to 7.45 (-O3) | 2.26 to 2.32 (-O2), 2.3 to 2.43 (-O3) | 0.45 to 0.48 (-O2), 0.42 to 0.48 (-O3) |
| `half`, 1 limb, N = 7 | 0.71 to 2.17 (-O2), 0.72 to 1.79 (-O3) | -0.638 to 0.54 (-O2), 4.27 to 7.5 (-O3) | 2.14 to 2.43 (-O2), 2.17 to 2.31 (-O3) | -0.02 to 0.03 (-O2), -0.11 to 0.09 (-O3) |
| `half`, 1 limb, N = 13 | -0.52 to 0.6 (-O2), -0.43 to 0.8 (-O3) | 0.15 to 0.174 (-O2), 3.01 to 6.36 (-O3) | 1.67 to 2.49 (-O2), 2.1 to 2.57 (-O3) | -0.26 to -0.17 (-O2), -0.33 to -0.28 (-O3) |
| `half`, 1 limb, N = 18 | -0.2 to 1.32 (-O2), 0.65 to 1.14 (-O3) | -0.03 to 0.01 (-O2), -1.87 to 0.71 (-O3) | 2.89 to 2.96 (-O2), 1.96 to 2.02 (-O3) | -1.1 to -0.68 (-O2), -1.37 to -1.11 (-O3) |
| `half`, 1 limb, N = 80 | 0.18 to 2.97 (-O2), -0.07 to 1.89 (-O3) | -0.12 to 2.63 (-O2), -8.62 to 0.74 (-O3) | 3.27 to 3.99 (-O2), 4.93 to 5.23 (-O3) | 5.23 to 5.55 (-O2), 4.24 to 5.51 (-O3) |
| `half`, 2 limbs, N = 3 | 1.56 to 2.9 (-O2), 2.32 to 2.56 (-O3) | -0.56 to 0.133 (-O2), -2.12 to 0.797 (-O3) | 2.24 to 2.64 (-O2), 2.15 to 2.27 (-O3) | 0.5 to 0.62 (-O2), 0.72 to 0.81 (-O3) |
| `half`, 2 limbs, N = 7 | -0.15 to 1.59 (-O2), -0.26 to 1.28 (-O3) | 0.162 to 0.78 (-O2), -2.32 to 0.204 (-O3) | 1.23 to 1.32 (-O2), 2.81 to 3.1 (-O3) | 2.29 to 2.49 (-O2), 1.89 to 2.1 (-O3) |
| `half`, 2 limbs, N = 13 | -0.6 to 1.05 (-O2), -0.59 to 1.66 (-O3) | 0.15 to 1.02 (-O2), -2.04 to 0.75 (-O3) | 1.36 to 1.65 (-O2), 3.12 to 3.32 (-O3) | 2.73 to 3.2 (-O2), 2.66 to 2.91 (-O3) |
| `half`, 2 limbs, N = 18 | -0.25 to 2.04 (-O2), 0.45 to 1.53 (-O3) | -0.17 to 0.89 (-O2), -2.34 to 0.79 (-O3) | 1.46 to 1.54 (-O2), 1.87 to 3.36 (-O3) | 2.44 to 2.83 (-O2), 2.4 to 5.57 (-O3) |
| `half`, 2 limbs, N = 80 | -0.45 to 4.33 (-O2), 0.31 to 3.3 (-O3) | -0.3 to 3.61 (-O2), -13.4 to 2.53 (-O3) | 3.09 to 3.32 (-O2), 5.21 to 5.3 (-O3) | 5.72 to 6.72 (-O2), 5.27 to 6.01 (-O3) |
| the constructor, 1 limb, N = 3 | 7.15 to 10.9 (-O2), 5.69 to 9.86 (-O3) | -0.264 to 0.42 (-O2), -1.54 to 0.329 (-O3) | 3.6 to 3.92 (-O2), 3 to 4.53 (-O3) | 19.7 (-O2), 12.7 to 13.7 (-O3) |
| the constructor, 1 limb, N = 7 | -0.67 to 1.59 (-O2), -0.29 to 3.66 (-O3) | -7.05 to -4.04 (-O2), -1.76 to 0.383 (-O3) | 4.43 to 4.52 (-O2), 4.76 to 5.84 (-O3) | -0.01 to 1.69 (-O2), -1.3 to 1.68 (-O3) |
| the constructor, 1 limb, N = 13 | 0.86 to 2.71 (-O2), 0.66 to 2.74 (-O3) | -0.02 to 1.2 (-O2), -1.74 to 0.61 (-O3) | 2.96 to 3.05 (-O2), 4.17 to 4.28 (-O3) | 0.38 to 0.8 (-O2), 0.17 to 0.64 (-O3) |
| the constructor, 1 limb, N = 18 | -3.42 to -1.6 (-O2), 0.15 to 2.61 (-O3) | 0.14 to 2.18 (-O2), -5.96 to 1.47 (-O3) | 4.63 to 4.67 (-O2), 4.64 to 5.03 (-O3) | 0.05 to 1.85 (-O2), -0.04 to 2.59 (-O3) |
| the constructor, 1 limb, N = 80 | -0.91 to 6.22 (-O2), 4.69 to 7.97 (-O3) | 0 to 16.8 (-O2), -58 to 13.4 (-O3) | 5.2 to 6.2 (-O2), 1.7 to 3.4 (-O3) | -2.71 to 1.14 (-O2), 2.67 to 7.03 (-O3) |
| the constructor, 2 limbs, N = 3 | 3.24 to 5.29 (-O2), 4.46 to 8.39 (-O3) | 0.197 to 0.794 (-O2), -1.62 to 0.457 (-O3) | 3.29 to 3.58 (-O2), 1.29 to 2.39 (-O3) | 9.45 to 9.86 |
| the constructor, 2 limbs, N = 7 | 0.05 to 0.62 (-O2), 1.61 to 2.71 (-O3) | -0.21 to 0.67 (-O2), -1.92 to -0.054 (-O3) | 1.51 to 4.47 (-O2), 4.76 to 5.13 (-O3) | 1.78 to 3.39 (-O2), 1.81 to 3.31 (-O3) |
| the constructor, 2 limbs, N = 13 | -0.42 to 0.92 (-O2), 0.65 to 4.33 (-O3) | 0.09 to 2.01 (-O2), -2.15 to 1.14 (-O3) | 0.18 to 0.73 (-O2), 0.5 to 1.15 (-O3) | 1.46 to 2.1 (-O2), 0.05 to 5.93 (-O3) |
| the constructor, 2 limbs, N = 18 | -0.58 to 1.33 (-O2), -0.22 to 1.4 (-O3) | 0.32 to 4.12 (-O2), -8.6 to 1.59 (-O3) | 5.28 to 6.1 (-O2), -11.5 to -10.8 (-O3) | 1.52 to 2.22 (-O2), -0.44 to 4.18 (-O3) |
| the constructor, 2 limbs, N = 80 | -4.3 to 2.67 (-O2), -1.37 to 8.5 (-O3) | -0.2 to 41.9 (-O2), -56.5 to 13.4 (-O3) | -1.4 to 1.1 (-O2), -12.6 to -10.2 (-O3) | 1.2 to 6.6 (-O2), 1.9 to 8.54 (-O3) |

| Short ball vectors, one operation per unit, a dependent chain: with the check over without | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 0.96 to 1.02 (-O2), 0.99 to 1.06 (-O3) | 1.92 to 2.64 (-O2), 1.97 to 2.15 (-O3) | 1.23 (-O2), 1.46 to 1.49 (-O3) | 0.97 to 0.98 |
| `add(x, y, z)`, 1 limb, N = 7 | 0.97 to 1.05 (-O2), 1.00 to 1.10 (-O3) | 1.07 to 1.23 (-O2), 1.86 to 2.00 (-O3) | 1.16 to 1.31 (-O2), 1.11 to 1.12 (-O3) | 1.06 to 1.08 |
| `add(x, y, z)`, 1 limb, N = 13 | 0.68 to 0.72 | 1.00 to 1.04 (-O2), 2.08 to 2.19 (-O3) | 1.12 to 1.15 | 1.14 to 1.15 (-O2), 0.95 to 1.15 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | 0.97 to 1.09 (-O2), 0.98 to 1.11 (-O3) | 1.02 to 1.03 (-O2), 1.14 to 1.27 (-O3) | 1.14 to 1.16 | 1.20 to 1.22 |
| `add(x, y, z)`, 1 limb, N = 80 | 0.99 to 1.06 (-O2), 1.00 to 1.11 (-O3) | 0.96 to 1.04 (-O2), 0.95 to 1.02 (-O3) | 1.22 to 1.23 (-O2), 1.17 to 1.18 (-O3) | 1.14 to 1.18 |
| `add(x, y, z)`, 2 limbs, N = 3 | 0.98 to 1.04 (-O2), 0.97 to 1.13 (-O3) | 0.97 to 1.02 (-O2), 0.87 to 1.01 (-O3) | 1.07 to 1.12 | 1.11 to 1.13 |
| `add(x, y, z)`, 2 limbs, N = 7 | 1.01 to 1.05 (-O2), 0.96 to 1.18 (-O3) | 0.99 to 1.04 (-O2), 0.93 to 1.02 (-O3) | 1.07 to 1.09 (-O2), 0.99 to 1.00 (-O3) | 1.06 to 1.09 |
| `add(x, y, z)`, 2 limbs, N = 13 | 1.02 to 1.08 (-O2), 0.99 to 1.08 (-O3) | 0.94 to 1.02 (-O2), 0.97 to 1.03 (-O3) | 1.08 to 1.09 (-O2), 0.96 to 0.99 (-O3) | 1.09 to 1.11 |
| `add(x, y, z)`, 2 limbs, N = 18 | 1.00 to 1.09 (-O2), 0.99 to 1.11 (-O3) | 0.98 to 1.11 (-O2), 0.96 to 1.03 (-O3) | 1.09 to 1.12 | 1.12 to 1.14 |
| `add(x, y, z)`, 2 limbs, N = 80 | 1.00 to 1.04 (-O2), 1.00 to 1.07 (-O3) | 0.95 to 1.02 (-O2), 0.95 to 1.02 (-O3) | 1.04 to 1.06 | 1.05 to 1.07 |
| `z = x + y`, 1 limb, N = 3 | 0.99 to 1.07 (-O2), 0.99 to 1.11 (-O3) | 2.21 to 2.77 (-O2), 2.04 to 2.56 (-O3) | 1.00 to 1.02 (-O2), 1.03 to 1.05 (-O3) | 1.00 to 1.01 |
| `z = x + y`, 1 limb, N = 7 | 1.00 to 1.09 (-O2), 1.00 to 1.05 (-O3) | 0.92 to 0.99 (-O2), 0.83 to 0.92 (-O3) | 1.00 to 1.04 | 0.99 to 1.00 |
| `z = x + y`, 1 limb, N = 13 | 0.96 to 1.10 (-O2), 0.98 to 1.09 (-O3) | 0.86 to 0.99 (-O2), 0.93 to 1.00 (-O3) | 1.00 (-O2), 0.95 to 0.96 (-O3) | 0.99 to 1.01 |
| `z = x + y`, 1 limb, N = 18 | 0.97 to 1.03 (-O2), 0.95 to 1.11 (-O3) | 1.09 to 1.17 (-O2), 0.96 to 0.99 (-O3) | 0.99 to 1.00 (-O2), 0.94 to 0.98 (-O3) | 1.01 to 1.04 |
| `z = x + y`, 1 limb, N = 80 | 1.00 to 1.11 (-O2), 0.99 to 1.11 (-O3) | 0.98 to 1.00 (-O2), 0.94 to 1.01 (-O3) | 1.05 to 1.08 | 0.88 to 1.02 (-O2), 1.02 to 1.10 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 0.99 to 1.06 (-O2), 0.97 to 1.06 (-O3) | 0.94 to 1.00 (-O2), 1.19 to 1.25 (-O3) | 0.99 to 1.02 | 0.98 to 1.07 (-O2), 1.02 to 1.11 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 1.01 to 1.05 (-O2), 0.99 to 1.06 (-O3) | 0.92 to 0.99 (-O2), 0.99 to 1.08 (-O3) | 1.01 to 1.25 (-O2), 1.00 to 1.03 (-O3) | 0.69 to 1.04 (-O2), 1.03 to 1.04 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 1.00 to 1.01 (-O2), 1.00 to 1.12 (-O3) | 1.03 to 1.07 (-O2), 0.99 to 1.07 (-O3) | 0.99 to 1.02 (-O2), 0.97 to 1.04 (-O3) | 0.92 to 1.00 (-O2), 0.97 to 1.23 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 0.98 (-O2), 0.97 to 1.07 (-O3) | 0.94 to 1.01 (-O2), 0.97 to 1.05 (-O3) | 1.00 to 1.03 | 0.94 to 1.00 (-O2), 1.00 to 1.07 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 1.01 to 1.02 (-O2), 0.99 to 1.07 (-O3) | 0.92 to 1.00 (-O2), 0.92 to 1.03 (-O3) | 0.99 to 1.01 | 0.99 to 1.02 (-O2), 1.00 to 1.06 (-O3) |
| `sub`, 1 limb, N = 3 | 0.96 to 1.01 (-O2), 0.96 to 1.06 (-O3) | 1.87 to 2.19 (-O2), 2.05 to 2.18 (-O3) | 1.22 to 1.23 (-O2), 1.46 to 1.48 (-O3) | 0.98 |
| `sub`, 1 limb, N = 7 | 0.96 to 1.01 (-O2), 0.96 to 1.06 (-O3) | 1.02 to 1.24 (-O2), 1.90 to 2.15 (-O3) | 1.15 to 1.16 (-O2), 1.11 to 1.12 (-O3) | 1.08 to 1.09 |
| `sub`, 1 limb, N = 13 | 0.69 to 0.80 (-O2), 0.66 to 0.77 (-O3) | 1.05 to 1.19 (-O2), 1.91 to 2.14 (-O3) | 0.99 to 1.18 (-O2), 1.14 to 1.15 (-O3) | 1.14 to 1.15 (-O2), 0.93 to 1.15 (-O3) |
| `sub`, 1 limb, N = 18 | 0.88 to 1.03 (-O2), 0.87 to 1.10 (-O3) | 1.03 to 1.08 (-O2), 0.99 to 1.10 (-O3) | 1.13 to 1.16 | 0.96 to 1.22 (-O2), 1.07 to 1.21 (-O3) |
| `sub`, 1 limb, N = 80 | 1.01 to 1.03 (-O2), 0.94 to 1.06 (-O3) | 0.96 to 1.01 (-O2), 0.95 to 1.05 (-O3) | 1.20 to 1.21 (-O2), 1.06 to 1.08 (-O3) | 1.18 (-O2), 1.13 to 1.16 (-O3) |
| `sub`, 2 limbs, N = 3 | 1.00 to 1.05 (-O2), 0.99 to 1.04 (-O3) | 0.94 to 0.99 (-O2), 0.91 to 1.03 (-O3) | 1.10 to 1.11 | 1.13 to 1.14 |
| `sub`, 2 limbs, N = 7 | 0.97 to 1.00 (-O2), 0.96 to 1.05 (-O3) | 0.94 to 1.01 (-O2), 0.94 to 1.00 (-O3) | 1.02 to 1.07 | 1.11 to 1.12 |
| `sub`, 2 limbs, N = 13 | 1.01 (-O2), 0.94 to 1.06 (-O3) | 0.97 to 1.02 (-O2), 0.97 to 1.06 (-O3) | 1.08 to 1.09 (-O2), 0.97 to 0.99 (-O3) | 1.10 to 1.12 |
| `sub`, 2 limbs, N = 18 | 0.99 to 1.04 (-O2), 1.00 to 1.06 (-O3) | 0.97 to 1.03 (-O2), 0.98 to 1.06 (-O3) | 1.07 to 1.12 (-O2), 1.11 (-O3) | 1.13 to 1.15 |
| `sub`, 2 limbs, N = 80 | 1.01 to 1.04 (-O2), 0.99 to 1.06 (-O3) | 0.95 to 1.02 (-O2), 1.02 to 1.08 (-O3) | 1.03 to 1.05 | 1.06 |
| `scale`, 1 limb, N = 3 | 1.57 to 1.71 (-O2), 1.57 to 1.69 (-O3) | 2.05 to 3.25 (-O2), 1.98 to 2.32 (-O3) | 0.98 to 1.32 (-O2), 1.36 to 1.79 (-O3) | 1.36 to 1.37 |
| `scale`, 1 limb, N = 7 | 1.58 to 1.62 (-O2), 1.58 to 1.68 (-O3) | 1.21 to 1.41 (-O2), 1.96 to 2.15 (-O3) | 1.18 to 1.22 | 1.33 to 1.35 |
| `scale`, 1 limb, N = 13 | 1.52 to 1.60 (-O2), 1.38 to 1.67 (-O3) | 1.00 to 1.06 (-O2), 1.92 to 2.30 (-O3) | 1.20 to 1.23 | 1.35 to 1.37 |
| `scale`, 1 limb, N = 18 | 0.92 to 1.06 (-O2), 1.17 to 1.28 (-O3) | 1.06 to 1.27 (-O2), 1.06 to 1.08 (-O3) | 1.19 to 1.24 | 1.40 to 1.41 (-O2), 1.39 to 1.89 (-O3) |
| `scale`, 1 limb, N = 80 | 1.02 (-O2), 0.98 to 1.06 (-O3) | 0.96 to 1.03 (-O2), 1.01 to 1.08 (-O3) | 1.08 to 1.09 (-O2), 1.17 to 1.20 (-O3) | 1.23 (-O2), 1.09 to 1.78 (-O3) |
| `scale`, 2 limbs, N = 3 | 1.62 to 1.65 (-O2), 1.61 to 1.74 (-O3) | 0.96 to 1.18 (-O2), 0.90 to 1.05 (-O3) | 1.14 to 1.16 | 1.31 to 1.33 (-O2), 1.02 to 1.28 (-O3) |
| `scale`, 2 limbs, N = 7 | 1.00 to 1.07 (-O2), 0.99 to 1.24 (-O3) | 0.99 to 1.03 (-O2), 0.93 to 1.00 (-O3) | 1.14 to 1.15 (-O2), 1.03 to 1.04 (-O3) | 1.41 to 1.44 |
| `scale`, 2 limbs, N = 13 | 0.95 to 1.01 (-O2), 0.94 to 1.12 (-O3) | 0.95 to 1.15 (-O2), 1.01 to 1.05 (-O3) | 1.14 to 1.17 | 1.31 to 1.32 |
| `scale`, 2 limbs, N = 18 | 0.96 to 1.03 (-O2), 0.93 to 1.10 (-O3) | 0.95 to 1.01 (-O2), 0.97 to 1.08 (-O3) | 1.11 (-O2), 1.05 to 1.06 (-O3) | 0.96 to 1.13 (-O2), 0.96 to 1.13 (-O3) |
| `scale`, 2 limbs, N = 80 | 1.02 to 1.11 (-O2), 1.00 (-O3) | 0.95 to 1.02 (-O2), 1.02 to 1.06 (-O3) | 1.08 (-O2), 1.00 to 1.01 (-O3) | 1.03 to 1.04 |
| `half`, 1 limb, N = 3 | 1.00 to 1.06 (-O2), 1.06 to 1.18 (-O3) | 0.81 to 0.93 (-O2), 2.09 to 2.65 (-O3) | 1.14 (-O2), 1.32 to 1.34 (-O3) | 1.06 to 1.08 |
| `half`, 1 limb, N = 7 | 1.05 to 1.08 (-O2), 1.05 to 1.18 (-O3) | 0.87 to 1.02 (-O2), 2.12 to 2.34 (-O3) | 1.13 (-O2), 1.21 to 1.23 (-O3) | 1.01 to 1.03 |
| `half`, 1 limb, N = 13 | 0.97 to 1.01 (-O2), 0.99 to 1.10 (-O3) | 0.96 to 1.04 (-O2), 1.53 to 1.63 (-O3) | 1.11 to 1.15 (-O2), 1.21 to 1.27 (-O3) | 1.00 to 1.24 (-O2), 0.99 to 1.00 (-O3) |
| `half`, 1 limb, N = 18 | 0.94 to 1.00 (-O2), 0.99 to 1.05 (-O3) | 1.03 (-O2), 0.97 to 1.09 (-O3) | 1.16 to 1.17 (-O2), 1.17 to 1.23 (-O3) | 0.93 to 0.95 |
| `half`, 1 limb, N = 80 | 1.00 to 1.06 (-O2), 1.00 to 1.06 (-O3) | 0.98 to 1.05 (-O2), 0.98 to 1.04 (-O3) | 1.09 to 1.11 (-O2), 1.14 to 1.16 (-O3) | 1.17 to 1.20 (-O2), 1.13 to 1.18 (-O3) |
| `half`, 2 limbs, N = 3 | 1.09 to 1.16 (-O2), 1.09 to 1.22 (-O3) | 0.89 to 0.95 (-O2), 0.78 to 1.06 (-O3) | 1.12 to 1.13 (-O2), 1.28 to 1.29 (-O3) | 1.03 to 1.05 |
| `half`, 2 limbs, N = 7 | 0.97 to 1.08 (-O2), 0.99 to 1.18 (-O3) | 1.01 to 1.04 (-O2), 0.89 to 1.09 (-O3) | 1.05 to 1.10 (-O2), 1.16 to 1.17 (-O3) | 1.12 to 1.16 |
| `half`, 2 limbs, N = 13 | 1.00 to 1.10 (-O2), 0.96 to 1.11 (-O3) | 0.96 to 1.04 (-O2), 1.01 to 1.10 (-O3) | 1.07 to 1.08 (-O2), 1.19 to 1.22 (-O3) | 1.13 to 1.17 |
| `half`, 2 limbs, N = 18 | 1.00 to 1.11 (-O2), 1.03 to 1.25 (-O3) | 1.01 (-O2), 0.94 to 1.05 (-O3) | 1.05 to 1.06 (-O2), 1.09 to 1.17 (-O3) | 1.12 to 1.15 |
| `half`, 2 limbs, N = 80 | 1.00 to 1.01 (-O2), 1.00 to 1.13 (-O3) | 1.00 (-O2), 0.94 to 1.06 (-O3) | 1.06 to 1.11 | 1.10 to 1.13 |
| the constructor, 1 limb, N = 3 | 1.39 to 1.55 (-O2), 1.39 to 1.45 (-O3) | 0.83 to 1.01 (-O2), 0.99 to 1.06 (-O3) | 1.18 to 1.24 (-O2), 1.18 to 1.20 (-O3) | 4.10 to 4.18 |
| the constructor, 1 limb, N = 7 | 0.97 to 1.05 (-O2), 0.95 to 1.00 (-O3) | 0.53 to 0.67 (-O2), 1.00 to 1.05 (-O3) | 1.26 to 1.27 (-O2), 1.34 to 1.37 (-O3) | 0.99 to 1.05 (-O2), 0.96 to 1.07 (-O3) |
| the constructor, 1 limb, N = 13 | 0.99 to 1.08 (-O2), 0.99 to 1.10 (-O3) | 0.91 to 1.00 (-O2), 0.98 to 1.16 (-O3) | 1.11 to 1.12 (-O2), 1.17 to 1.19 (-O3) | 0.99 to 1.02 |
| the constructor, 1 limb, N = 18 | 0.86 to 0.94 (-O2), 0.89 to 1.05 (-O3) | 0.93 to 1.01 (-O2), 0.98 to 1.06 (-O3) | 1.07 to 1.11 | 1.01 to 1.03 (-O2), 1.01 to 1.07 (-O3) |
| the constructor, 1 limb, N = 80 | 0.98 to 1.03 (-O2), 0.97 to 1.12 (-O3) | 0.92 to 1.00 (-O2), 0.95 to 1.06 (-O3) | 1.01 to 1.03 | 1.06 to 1.11 (-O2), 1.05 to 1.12 (-O3) |
| the constructor, 2 limbs, N = 3 | 1.32 to 1.39 (-O2), 1.23 to 1.61 (-O3) | 0.91 to 1.00 (-O2), 0.96 to 1.04 (-O3) | 1.18 to 1.20 (-O2), 1.12 to 1.18 (-O3) | 1.43 to 2.14 (-O2), 2.09 to 2.10 (-O3) |
| the constructor, 2 limbs, N = 7 | 1.01 to 1.05 (-O2), 0.97 to 1.12 (-O3) | 0.99 (-O2), 0.90 to 1.00 (-O3) | 1.05 to 1.22 (-O2), 1.31 to 1.45 (-O3) | 0.90 to 1.24 (-O2), 1.11 to 1.19 (-O3) |
| the constructor, 2 limbs, N = 13 | 0.93 to 1.05 (-O2), 0.98 to 1.16 (-O3) | 0.92 to 1.01 (-O2), 1.01 to 1.12 (-O3) | 1.02 to 1.04 (-O2), 1.05 to 1.07 (-O3) | 1.05 to 1.06 (-O2), 1.01 to 1.10 (-O3) |
| the constructor, 2 limbs, N = 18 | 0.98 to 1.04 (-O2), 0.99 to 1.04 (-O3) | 0.93 to 1.01 (-O2), 1.00 to 1.04 (-O3) | 1.02 to 1.04 (-O2), 0.82 to 0.83 (-O3) | 1.01 to 1.07 (-O2), 1.05 to 1.14 (-O3) |
| the constructor, 2 limbs, N = 80 | 0.97 to 1.08 (-O2), 0.97 to 1.12 (-O3) | 0.94 to 1.00 (-O2), 0.98 to 1.05 (-O3) | 1.11 to 1.13 (-O2), 0.97 to 0.99 (-O3) | 1.00 to 1.04 (-O2), 1.03 to 1.09 (-O3) |

| Short ball vectors, every size in one unit, many vectors: ns per operation, with the check | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 2.62 to 3.56 (-O2), 2.61 to 3.32 (-O3) | 4.8 to 5.05 (-O2), 4.92 to 5.91 (-O3) | 15.4 to 15.5 (-O2), 14.7 (-O3) | 8.42 to 8.49 |
| `add(x, y, z)`, 1 limb, N = 7 | 3.25 to 4.16 (-O2), 3.32 to 4.24 (-O3) | 5.16 to 6.09 (-O2), 5.84 to 7.01 (-O3) | 15.7 to 16.3 | 9.39 to 9.46 |
| `add(x, y, z)`, 1 limb, N = 13 | 4.97 to 6.44 (-O2), 5.03 to 6.35 (-O3) | 6.81 to 8.18 (-O2), 7.75 to 9.36 (-O3) | 15.9 to 16.5 | 9.61 to 9.77 |
| `add(x, y, z)`, 1 limb, N = 18 | 6.15 to 8.14 (-O2), 7.1 to 8.67 (-O3) | 9.41 to 9.97 (-O2), 9.22 to 11.1 (-O3) | 17.9 to 18.1 (-O2), 17.2 to 17.7 (-O3) | 10.4 to 10.6 |
| `add(x, y, z)`, 1 limb, N = 80 | 32 to 40.8 (-O2), 29.5 to 39.9 (-O3) | 40.8 to 44.9 (-O2), 35.2 to 42.4 (-O3) | 31.8 to 32.6 (-O2), 29.8 to 30.7 (-O3) | 22.4 to 22.5 (-O2), 20.7 to 21.2 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | 5.36 to 6.83 (-O2), 5.36 to 6.82 (-O3) | 7.39 to 8.12 (-O2), 8.06 to 9.69 (-O3) | 26.1 to 27 | 17.4 to 17.5 |
| `add(x, y, z)`, 2 limbs, N = 7 | 9.57 to 12.3 (-O2), 9.18 to 12.2 (-O3) | 11 to 12.3 (-O2), 12.2 to 14.7 (-O3) | 31 to 31.7 | 22.1 to 22.3 |
| `add(x, y, z)`, 2 limbs, N = 13 | 15.9 to 20.3 (-O2), 15.7 to 19.8 (-O3) | 17.8 to 20.6 (-O2), 19.2 to 23 (-O3) | 30.4 to 31 | 23.2 to 23.4 |
| `add(x, y, z)`, 2 limbs, N = 18 | 21 to 26.8 (-O2), 20.2 to 26 (-O3) | 22.4 to 25.6 (-O2), 24.7 to 27.8 (-O3) | 39.8 to 40 | 34.3 to 34.6 |
| `add(x, y, z)`, 2 limbs, N = 80 | 81.1 to 104 (-O2), 80.2 to 102 (-O3) | 90.8 to 99 (-O2), 93.5 to 112 (-O3) | 99.7 to 104 | 94.8 to 95.9 |
| `z = x + y`, 1 limb, N = 3 | 2.61 to 3.56 (-O2), 2.6 to 3.32 (-O3) | 4.61 to 5.52 (-O2), 5.23 to 6.27 (-O3) | 19.9 to 20.5 | 8.48 to 8.59 |
| `z = x + y`, 1 limb, N = 7 | 3.67 to 4.78 (-O2), 3.66 to 4.76 (-O3) | 6.31 to 7.8 (-O2), 7.51 to 9.02 (-O3) | 21 to 21.2 (-O2), 19.9 to 20.6 (-O3) | 9.69 to 9.78 |
| `z = x + y`, 1 limb, N = 13 | 7.3 to 9.73 (-O2), 7.43 to 9.6 (-O3) | 9.28 to 12 (-O2), 9.99 to 12 (-O3) | 20.2 to 21.2 | 10.1 to 10.2 |
| `z = x + y`, 1 limb, N = 18 | 9.38 to 12.6 (-O2), 10.4 to 13 (-O3) | 16 to 17.4 (-O2), 15.7 to 18.9 (-O3) | 22.2 to 23.2 | 11.5 to 11.9 |
| `z = x + y`, 1 limb, N = 80 | 42 to 54.6 (-O2), 43.8 to 56.1 (-O3) | 57.3 to 63.2 (-O2), 51.1 to 61.5 (-O3) | 86.4 to 90.2 | 34.6 to 40.4 (-O2), 40.7 to 42.1 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 5.74 to 7.41 (-O2), 5.74 to 7.35 (-O3) | 9.08 to 10 (-O2), 9.79 to 11.8 (-O3) | 29.6 to 30.8 | 18.6 to 20.6 (-O2), 20.4 to 20.7 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 10.8 to 13.8 (-O2), 10.8 to 13.8 (-O3) | 13.5 to 15.2 (-O2), 15.2 to 18.2 (-O3) | 35 to 35.9 | 25.3 to 27.3 (-O2), 27.1 to 27.6 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 18.1 to 23.5 (-O2), 18 to 23 (-O3) | 21.5 to 22.8 (-O2), 22 to 26.5 (-O3) | 50.5 to 51.5 | 26.8 to 28.5 (-O2), 28.4 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 24.3 to 30.9 (-O2), 23.9 to 30.6 (-O3) | 29.7 to 31.4 (-O2), 29.9 to 35 (-O3) | 63.1 to 63.6 | 39.9 to 42.1 (-O2), 41.4 to 42 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 109 to 140 (-O2), 110 to 140 (-O3) | 128 to 145 (-O2), 127 to 152 (-O3) | 167 to 169 | 130 to 134 |
| `sub`, 1 limb, N = 3 | 2.6 to 3.32 (-O2), 2.6 to 3.31 (-O3) | 4.59 to 5.06 (-O2), 4.92 to 5.91 (-O3) | 15.4 to 15.5 (-O2), 9.97 to 9.99 (-O3) | 8.43 to 8.5 |
| `sub`, 1 limb, N = 7 | 3.32 to 4.32 (-O2), 3.27 to 4.18 (-O3) | 5.32 to 6.09 (-O2), 5.86 to 7.05 (-O3) | 16.2 to 16.3 (-O2), 11.4 (-O3) | 9.38 to 9.47 |
| `sub`, 1 limb, N = 13 | 4.9 to 6.47 (-O2), 4.98 to 6.44 (-O3) | 7.43 to 8.71 (-O2), 7.76 to 9.37 (-O3) | 16.4 to 16.6 (-O2), 11.5 to 11.6 (-O3) | 9.59 to 9.77 |
| `sub`, 1 limb, N = 18 | 6.18 to 8.13 (-O2), 7.1 to 8.66 (-O3) | 9.01 to 9.98 (-O2), 9.22 to 11.1 (-O3) | 17.9 to 18.2 (-O2), 12.7 to 12.9 (-O3) | 10.4 to 10.6 |
| `sub`, 1 limb, N = 80 | 31.8 to 40.5 (-O2), 30.9 to 39.4 (-O3) | 40.8 to 44.8 (-O2), 35 to 42.5 (-O3) | 31.9 to 32.4 (-O2), 25.3 to 26 (-O3) | 22.4 (-O2), 20.2 to 20.4 (-O3) |
| `sub`, 2 limbs, N = 3 | 5.67 to 7.21 (-O2), 5.66 to 7.17 (-O3) | 7.5 to 8.25 (-O2), 6.17 to 7.42 (-O3) | 27.2 to 27.3 (-O2), 19.9 to 20 (-O3) | 18 to 18.2 |
| `sub`, 2 limbs, N = 7 | 10.5 to 13.3 (-O2), 10.4 to 13.3 (-O3) | 11.8 to 12.9 (-O2), 11 to 13.2 (-O3) | 31.9 (-O2), 26.7 (-O3) | 24.1 to 24.2 |
| `sub`, 2 limbs, N = 13 | 17 to 23.2 (-O2), 17 to 21.7 (-O3) | 19.5 to 20.6 (-O2), 17.8 to 21.4 (-O3) | 31 to 31.3 (-O2), 25.5 to 25.6 (-O3) | 24.3 to 24.6 |
| `sub`, 2 limbs, N = 18 | 22.2 to 28.2 (-O2), 21.6 to 27.5 (-O3) | 23 to 26.8 (-O2), 23.2 to 28 (-O3) | 40.2 to 40.4 (-O2), 36.8 to 37 (-O3) | 35.2 to 35.8 |
| `sub`, 2 limbs, N = 80 | 85 to 109 (-O2), 85.2 to 109 (-O3) | 98.9 to 109 (-O2), 92.9 to 111 (-O3) | 105 (-O2), 98 to 99 (-O3) | 96.7 to 97.8 |
| `scale`, 1 limb, N = 3 | 2.57 to 3.28 (-O2), 2.59 to 3.3 (-O3) | 4.94 to 5.38 (-O2), 4.96 to 5.97 (-O3) | 15.2 to 15.6 | 8.41 to 8.47 |
| `scale`, 1 limb, N = 7 | 3.17 to 4.34 (-O2), 3.17 to 4.04 (-O3) | 5.43 to 6.42 (-O2), 5.8 to 6.99 (-O3) | 16 to 16.5 | 9.38 to 9.46 |
| `scale`, 1 limb, N = 13 | 4.3 to 5.73 (-O2), 4.45 to 5.69 (-O3) | 7.23 to 8.01 (-O2), 7.58 to 9.1 (-O3) | 16.2 to 16.7 | 9.51 to 9.65 |
| `scale`, 1 limb, N = 18 | 5.75 to 7.91 (-O2), 6.34 to 7.49 (-O3) | 8.5 to 9.78 (-O2), 8.91 to 10.7 (-O3) | 17.7 to 18.2 | 10.4 to 10.6 |
| `scale`, 1 limb, N = 80 | 29.8 to 39.6 (-O2), 28.2 to 36.2 (-O3) | 39.8 to 47.1 (-O2), 33.7 to 40.5 (-O3) | 32.1 to 32.3 (-O2), 30.3 to 31 (-O3) | 20.3 to 20.4 (-O2), 26.3 to 28.1 (-O3) |
| `scale`, 2 limbs, N = 3 | 3.31 to 4.23 (-O2), 3.31 to 4.21 (-O3) | 5.42 to 5.97 (-O2), 5.84 to 7.01 (-O3) | 19.6 (-O2), 12 to 12.1 (-O3) | 9.98 to 10.1 |
| `scale`, 2 limbs, N = 7 | 5.34 to 6.83 (-O2), 5.31 to 6.73 (-O3) | 6.95 to 7.96 (-O2), 8.12 to 9.76 (-O3) | 22.2 (-O2), 15.9 to 16 (-O3) | 13.6 to 13.7 |
| `scale`, 2 limbs, N = 13 | 7.92 to 9.94 (-O2), 7.88 to 10 (-O3) | 9.07 to 10.8 (-O2), 11.4 to 13.6 (-O3) | 22.4 to 22.6 (-O2), 15.8 to 15.9 (-O3) | 13.7 to 13.9 |
| `scale`, 2 limbs, N = 18 | 10.2 to 13.6 (-O2), 10.3 to 13.1 (-O3) | 12.8 to 13.5 (-O2), 13.7 to 16.4 (-O3) | 25.3 to 25.4 (-O2), 19.2 to 19.4 (-O3) | 16.1 to 16.2 |
| `scale`, 2 limbs, N = 80 | 41.9 to 53.8 (-O2), 42.5 to 54.3 (-O3) | 48.2 to 50.9 (-O2), 54.2 to 60.7 (-O3) | 55.7 to 57.3 (-O2), 47.4 to 48.5 (-O3) | 43.8 to 44.3 |
| `half`, 1 limb, N = 3 | 3.7 to 5.05 (-O2), 3.69 to 4.7 (-O3) | 5.75 to 6.06 (-O2), 5.75 to 6.92 (-O3) | 19.7 to 19.8 (-O2), 18.1 (-O3) | 12.1 to 12.2 |
| `half`, 1 limb, N = 7 | 5.08 to 6.95 (-O2), 5.08 to 6.47 (-O3) | 6.43 to 7.09 (-O2), 6.91 to 8.29 (-O3) | 20.3 to 21.1 | 14 to 14.2 |
| `half`, 1 limb, N = 13 | 7.27 to 9.59 (-O2), 7.47 to 9.52 (-O3) | 8.61 to 10.1 (-O2), 9.47 to 11.4 (-O3) | 19.3 to 20.2 | 14.2 |
| `half`, 1 limb, N = 18 | 8.84 to 11.6 (-O2), 9.32 to 11.6 (-O3) | 10.8 to 11.7 (-O2), 11.4 to 13.7 (-O3) | 22.1 to 22.7 | 16.9 to 17.2 |
| `half`, 1 limb, N = 80 | 36.4 to 46.3 (-O2), 36 to 46 (-O3) | 40.8 to 45 (-O2), 41.8 to 50.1 (-O3) | 40.5 to 40.7 (-O2), 38 to 38.8 (-O3) | 36.4 to 36.8 |
| `half`, 2 limbs, N = 3 | 4.5 to 6.15 (-O2), 4.5 to 5.73 (-O3) | 5.7 to 6.73 (-O2), 6.72 to 8.07 (-O3) | 23.4 to 23.5 (-O2), 22.2 (-O3) | 14.7 to 14.8 |
| `half`, 2 limbs, N = 7 | 7.58 to 9.66 (-O2), 7.54 to 9.6 (-O3) | 8.96 to 10.5 (-O2), 9.72 to 11.7 (-O3) | 25.9 to 26.6 | 18.5 to 18.8 |
| `half`, 2 limbs, N = 13 | 11.2 to 14.1 (-O2), 11.2 to 14.2 (-O3) | 12.9 to 13.9 (-O2), 13.8 to 16.6 (-O3) | 25.1 to 25.2 (-O2), 23.9 to 24.1 (-O3) | 19 to 19.2 |
| `half`, 2 limbs, N = 18 | 13.8 to 17.6 (-O2), 13.9 to 17.6 (-O3) | 15.6 to 17.1 (-O2), 16.7 to 20.1 (-O3) | 29.3 to 29.9 | 22.8 to 23.1 |
| `half`, 2 limbs, N = 80 | 51 to 65.1 (-O2), 50.8 to 64.8 (-O3) | 58.7 to 61.8 (-O2), 67.1 to 75.3 (-O3) | 61 to 61.8 (-O2), 58 to 58.8 (-O3) | 54.9 to 55.6 |
| the constructor, 1 limb, N = 3 | 6.17 to 7.54 (-O2), 6.68 to 11.7 (-O3) | 4.5 to 5.38 (-O2), 5.69 to 6.83 (-O3) | 16.8 to 17.5 (-O2), 17.2 to 17.8 (-O3) | 24.6 to 24.9 |
| the constructor, 1 limb, N = 7 | 20.4 to 21.2 (-O2), 20.8 to 24.9 (-O3) | 9.31 to 10.4 (-O2), 10.9 to 13.1 (-O3) | 19.1 to 19.2 (-O2), 20.5 (-O3) | 26.9 to 28.1 (-O2), 26.9 to 28.7 (-O3) |
| the constructor, 1 limb, N = 13 | 26 to 33.9 (-O2), 24.1 to 32.5 (-O3) | 20 to 23.4 (-O2), 21.6 to 26 (-O3) | 24.2 to 24.3 (-O2), 25.5 to 25.6 (-O3) | 32.9 to 33.4 |
| the constructor, 1 limb, N = 18 | 18.9 to 25.2 (-O2), 26.3 to 36.1 (-O3) | 29 to 30.8 (-O2), 31.4 to 37.8 (-O3) | 28.9 to 29.7 (-O2), 32.7 to 33.1 (-O3) | 24.4 to 24.8 (-O2), 36 to 37.2 (-O3) |
| the constructor, 1 limb, N = 80 | 72.3 to 92.9 (-O2), 76.7 to 98.5 (-O3) | 224 to 263 (-O2), 250 to 296 (-O3) | 151 (-O2), 141 to 142 (-O3) | 71.7 to 72.7 |
| the constructor, 2 limbs, N = 3 | 6.48 to 9.01 (-O2), 6.92 to 8.98 (-O3) | 4.3 to 4.83 (-O2), 7.3 to 8.73 (-O3) | 16.1 to 16.3 (-O2), 19.3 to 20.5 (-O3) | 11.2 to 16 (-O2), 15.9 to 16 (-O3) |
| the constructor, 2 limbs, N = 7 | 20.9 to 26.1 (-O2), 21.1 to 28.3 (-O3) | 14.8 to 15.7 (-O2), 14.7 to 17.7 (-O3) | 20.1 to 20.6 (-O2), 22.7 to 23.4 (-O3) | 15.6 to 17.5 (-O2), 17.7 to 18 (-O3) |
| the constructor, 2 limbs, N = 13 | 24.2 to 31.9 (-O2), 23.6 to 31.2 (-O3) | 31.3 to 34.4 (-O2), 30.6 to 34.3 (-O3) | 38.3 to 38.4 (-O2), 29.3 to 29.6 (-O3) | 23 to 23.4 (-O2), 23.5 to 24.9 (-O3) |
| the constructor, 2 limbs, N = 18 | 23.9 to 32.4 (-O2), 22.2 to 29.2 (-O3) | 43.6 to 55.2 (-O2), 41.4 to 51.2 (-O3) | 48.6 to 49.1 (-O2), 34.5 to 34.6 (-O3) | 36 to 37 |
| the constructor, 2 limbs, N = 80 | 96.7 to 123 (-O2), 95.8 to 122 (-O3) | 336 to 367 (-O2), 324 to 364 (-O3) | 207 to 208 (-O2), 169 to 171 (-O3) | 106 to 109 |

| Short ball vectors, every size in one unit, many vectors: the check, ns per operation (with minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 0.305 to 0.586 (-O2), 0.264 to 0.416 (-O3) | -0.318 to 0.39 (-O2), 0.035 to 0.53 (-O3) | 2.59 to 2.6 (-O2), 2.38 to 2.54 (-O3) | 3.67 to 3.76 |
| `add(x, y, z)`, 1 limb, N = 7 | 0.162 to 0.235 (-O2), -0.018 to 0.246 (-O3) | -0.387 to 0.017 (-O2), 0.356 to 0.403 (-O3) | 2.37 to 2.51 (-O2), 2.14 to 2.32 (-O3) | 2.59 to 2.71 |
| `add(x, y, z)`, 1 limb, N = 13 | 0.141 to 0.38 (-O2), 0.089 to 0.313 (-O3) | -0.151 to 0.083 (-O2), 0.782 to 1.49 (-O3) | 1.79 to 2.09 (-O2), 2.26 to 2.32 (-O3) | 2.51 to 2.57 (-O2), 2.42 to 2.61 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | -0.567 to 0.032 (-O2), -0.136 to 0.173 (-O3) | 0.054 to 0.401 (-O2), 0.52 to 1.08 (-O3) | 1.86 to 2.02 (-O2), 2.66 to 2.89 (-O3) | 2.45 to 2.56 (-O2), 2.23 to 2.5 (-O3) |
| `add(x, y, z)`, 1 limb, N = 80 | -0.94 to 0.46 (-O2), -1.82 to 0.02 (-O3) | 0.13 to 0.87 (-O2), -0.25 to 1.29 (-O3) | 4.88 to 5.39 (-O2), 3.65 to 5.17 (-O3) | 3.53 to 3.64 (-O2), 2.72 to 3.25 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | 0.134 to 0.163 (-O2), 0.123 to 0.14 (-O3) | 0.088 to 0.209 (-O2), 0.441 to 0.747 (-O3) | 2.73 to 2.84 (-O2), 2.86 to 3.29 (-O3) | 1.73 to 1.91 (-O2), 1.54 to 1.82 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | -0.121 to 0.13 (-O2), -0.477 to -0.08 (-O3) | -0.1 to 0.15 (-O2), 0.13 to 0.66 (-O3) | 1.54 to 1.69 (-O2), 3.05 to 3.74 (-O3) | 1.52 to 1.73 (-O2), 1.54 to 1.77 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | -0.36 to 0.36 (-O2), 0.11 to 0.56 (-O3) | 0.06 to 0.21 (-O2), -0.18 to 1.45 (-O3) | 2.81 to 3 (-O2), 2.93 to 3.18 (-O3) | 1.96 to 2.12 (-O2), 1.96 to 2.23 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -0.41 to 0.47 (-O2), -0.17 to 0.16 (-O3) | -1.42 to 0.09 (-O2), -1.89 to 1.09 (-O3) | 4.28 to 4.4 (-O2), 4.49 to 4.83 (-O3) | 4.15 to 4.23 (-O2), 3.89 to 4.37 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -5.71 to 1.64 (-O2), -3.02 to 0.62 (-O3) | -5.35 to 1.92 (-O2), -1.82 to 4.29 (-O3) | 4.74 to 6.46 (-O2), 3.17 to 6.19 (-O3) | 3.34 to 4.26 (-O2), 3.33 to 4.57 (-O3) |
| `z = x + y`, 1 limb, N = 3 | 0.206 to 0.433 (-O2), 0.053 to 0.238 (-O3) | -0.116 to 0.303 (-O2), 0.063 to 0.23 (-O3) | 3.69 to 4.35 (-O2), 4.41 to 5.32 (-O3) | 3.13 to 3.25 |
| `z = x + y`, 1 limb, N = 7 | -0.127 to 0.095 (-O2), -0.322 to -0.017 (-O3) | -0.553 to 0 (-O2), 0.441 to 0.697 (-O3) | 3.48 to 3.94 (-O2), 3.53 to 3.91 (-O3) | 2.37 to 2.41 (-O2), 2.32 to 2.48 (-O3) |
| `z = x + y`, 1 limb, N = 13 | 1.32 to 2.63 (-O2), 1.94 to 2.51 (-O3) | -0.086 to 0.56 (-O2), 0.15 to 0.96 (-O3) | 3.17 to 3.27 (-O2), 2.95 to 3.35 (-O3) | 2.24 to 2.36 (-O2), 2.04 to 2.36 (-O3) |
| `z = x + y`, 1 limb, N = 18 | -0.779 to 0.019 (-O2), -0.17 to 0.25 (-O3) | 0.46 to 0.56 (-O2), 0.32 to 1.3 (-O3) | 2.06 to 2.76 (-O2), 2.83 to 3.32 (-O3) | 1.93 to 2.33 (-O2), 1.88 to 2.13 (-O3) |
| `z = x + y`, 1 limb, N = 80 | -1.54 to 1.17 (-O2), -0.35 to -0.18 (-O3) | 0.51 to 0.85 (-O2), -0.2 to 2.22 (-O3) | 2.79 to 3.83 (-O2), 1.89 to 6.36 (-O3) | -4.88 to 1.05 (-O2), 1.16 to 2.18 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -0.219 to 0.121 (-O2), -0.014 to 0.138 (-O3) | 0.264 to 0.355 (-O2), 0.596 to 0.68 (-O3) | 2.96 to 3.33 (-O2), 2.84 to 3.34 (-O3) | 0.89 to 3.87 (-O2), 2.47 to 2.89 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | -0.1 to 0.17 (-O2), -0.01 to 0.22 (-O3) | 0.3 to 0.58 (-O2), 1.25 to 1.76 (-O3) | 2.25 to 2.86 (-O2), 2.17 to 2.84 (-O3) | 0.71 to 4.3 (-O2), 2.34 to 3.03 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | -0.78 to 1.93 (-O2), 0.03 to 0.4 (-O3) | 0.25 to 1.19 (-O2), 0.52 to 1.57 (-O3) | 2.52 to 3.32 (-O2), 2.72 to 3.86 (-O3) | 0.54 to 3.75 (-O2), 2.05 to 2.35 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -0.36 to 0.5 (-O2), -0.43 to 0.37 (-O3) | -1.25 to 1.34 (-O2), -1.78 to 0.9 (-O3) | 0.54 to 1.01 (-O2), -0.11 to 0.65 (-O3) | 1.65 to 5.38 (-O2), 2.6 to 3.91 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | -7.8 to 0.4 (-O2), -0.7 to 0.7 (-O3) | 1.5 to 6.5 (-O2), 0.3 to 5.5 (-O3) | 1.9 to 2.6 (-O2), -0.2 to 3.8 (-O3) | -1.2 to 0.7 (-O2), -1.4 to 3.3 (-O3) |
| `sub`, 1 limb, N = 3 | 0.144 to 0.39 (-O2), 0.194 to 0.336 (-O3) | 0.002 to 0.412 (-O2), 0.089 to 0.395 (-O3) | 2.52 to 2.62 (-O2), 4.24 to 4.32 (-O3) | 3.67 to 3.78 |
| `sub`, 1 limb, N = 7 | -0.093 to 0.325 (-O2), -0.106 to 0.228 (-O3) | -0.205 to 0.016 (-O2), 0.364 to 0.435 (-O3) | 2.32 to 2.49 (-O2), 2.28 to 2.42 (-O3) | 2.61 to 2.74 |
| `sub`, 1 limb, N = 13 | -0.192 to 0.421 (-O2), 0.207 to 0.379 (-O3) | 0.493 to 0.549 (-O2), 1.07 to 1.46 (-O3) | 1.84 to 2.26 (-O2), 2.54 to 2.56 (-O3) | 2.55 to 2.6 (-O2), 2.44 to 2.59 (-O3) |
| `sub`, 1 limb, N = 18 | -0.407 to 0.018 (-O2), -0.083 to 0.179 (-O3) | 0.01 to 0.105 (-O2), 0.58 to 1.1 (-O3) | 2.04 to 2.24 (-O2), 2.28 to 2.36 (-O3) | 2.44 to 2.59 (-O2), 2.27 to 2.42 (-O3) |
| `sub`, 1 limb, N = 80 | 0.23 to 2.99 (-O2), -0.16 to -0.09 (-O3) | 0.62 to 0.69 (-O2), -0.23 to 1.31 (-O3) | 5.09 to 5.51 (-O2), 3 to 3.66 (-O3) | 3.5 to 3.64 (-O2), 2.25 to 2.5 (-O3) |
| `sub`, 2 limbs, N = 3 | -0.14 to 0.134 (-O2), 0.102 to 0.404 (-O3) | 0.139 to 0.184 (-O2), 0.294 to 0.368 (-O3) | 2.62 to 2.78 (-O2), 2.68 to 2.94 (-O3) | 1.89 to 2.1 (-O2), 1.92 to 2.26 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.46 to 0.05 (-O2), 0.04 to 0.1 (-O3) | 0.05 to 0.12 (-O2), 0.29 to 0.71 (-O3) | 2.03 to 2.27 (-O2), 2.53 to 2.82 (-O3) | 2.68 to 2.79 (-O2), 2.44 to 2.78 (-O3) |
| `sub`, 2 limbs, N = 13 | -0.11 to 2.67 (-O2), 0.1 to 0.32 (-O3) | 0.15 to 1.01 (-O2), 0.04 to 0.81 (-O3) | 2.43 to 2.75 (-O2), 2.4 to 2.68 (-O3) | 2.51 to 2.54 (-O2), 2.3 to 2.64 (-O3) |
| `sub`, 2 limbs, N = 18 | -0.26 to 2.06 (-O2), -0.07 to 0.17 (-O3) | 0.1 to 0.13 (-O2), -1.66 to 0.93 (-O3) | 4.06 to 4.18 (-O2), 3.86 to 4.14 (-O3) | 4.37 to 4.52 (-O2), 4.16 to 4.84 (-O3) |
| `sub`, 2 limbs, N = 80 | -5.78 to 0.3 (-O2), 0.2 to 0.33 (-O3) | -1.4 to 4.74 (-O2), 0.1 to 1.32 (-O3) | 5.3 to 6.41 (-O2), 2.95 to 4.33 (-O3) | 3.78 to 4.21 (-O2), 3.15 to 4.57 (-O3) |
| `scale`, 1 limb, N = 3 | 0.193 to 0.345 (-O2), 0.197 to 0.318 (-O3) | 0.356 to 1.08 (-O2), 0.323 to 0.386 (-O3) | 2.47 to 2.5 (-O2), 2.52 to 2.84 (-O3) | 3.84 to 3.93 |
| `scale`, 1 limb, N = 7 | -0.109 to 0.474 (-O2), 0.194 to 0.331 (-O3) | 0.201 to 0.664 (-O2), 0.336 to 0.416 (-O3) | 2.7 to 2.83 (-O2), 2.13 to 2.39 (-O3) | 2.63 to 2.75 |
| `scale`, 1 limb, N = 13 | -0.157 to 0.04 (-O2), 0.014 to 0.129 (-O3) | 0.102 to 0.147 (-O2), 0.603 to 1.04 (-O3) | 2.22 to 2.34 (-O2), 2.5 to 2.84 (-O3) | 2.52 to 2.57 (-O2), 2.44 to 2.58 (-O3) |
| `scale`, 1 limb, N = 18 | -0.046 to 0.451 (-O2), -0.331 to 0.18 (-O3) | -0.281 to 0.092 (-O2), 0.5 to 1.06 (-O3) | 2.1 to 2.17 (-O2), 2.5 to 2.74 (-O3) | 2.7 to 2.75 (-O2), 2.53 to 2.63 (-O3) |
| `scale`, 1 limb, N = 80 | 0.16 to 1.82 (-O2), 0.11 to 0.38 (-O3) | 1.03 to 4.47 (-O2), 1.12 to 1.99 (-O3) | 4.74 to 4.97 (-O2), 3.72 to 4.98 (-O3) | 2.76 to 2.84 (-O2), 2.08 to 5.56 (-O3) |
| `scale`, 2 limbs, N = 3 | 0.102 to 0.149 (-O2), 0.087 to 0.104 (-O3) | 0.256 to 0.287 (-O2), 0.311 to 0.386 (-O3) | 2.83 to 2.85 (-O2), -4.09 to -3.9 (-O3) | 2.57 to 2.62 (-O2), 2.43 to 2.53 (-O3) |
| `scale`, 2 limbs, N = 7 | 0.375 to 0.518 (-O2), 0.328 to 0.398 (-O3) | 0.089 to 0.141 (-O2), 0.38 to 0.86 (-O3) | 2.85 to 2.98 (-O2), -3.54 to -3.25 (-O3) | 2.76 to 2.82 (-O2), 2.63 to 2.77 (-O3) |
| `scale`, 2 limbs, N = 13 | 0.265 to 0.774 (-O2), 0.025 to 0.406 (-O3) | -0.581 to 0.14 (-O2), -0.2 to 0.97 (-O3) | 2.82 to 2.99 (-O2), -3.63 to -3.41 (-O3) | 2.77 to 2.83 (-O2), 2.71 to 2.92 (-O3) |
| `scale`, 2 limbs, N = 18 | 0.07 to 1.28 (-O2), -0.19 to 0.24 (-O3) | -0.65 to 1.6 (-O2), 0.06 to 0.88 (-O3) | 2.79 to 2.87 (-O2), -3.02 to -3 (-O3) | 1.49 to 1.73 (-O2), 1.6 to 1.81 (-O3) |
| `scale`, 2 limbs, N = 80 | -0.46 to 0.41 (-O2), 0.28 to 0.54 (-O3) | -2.86 to 2.32 (-O2), -2.87 to 2.87 (-O3) | 5.69 to 7.47 (-O2), -1.7 to -1.37 (-O3) | 1.51 to 1.77 (-O2), 1.47 to 1.89 (-O3) |
| `half`, 1 limb, N = 3 | 0.234 to 0.695 (-O2), 0.174 to 0.389 (-O3) | 0.226 to 0.559 (-O2), 0.319 to 0.389 (-O3) | 2.46 to 2.55 (-O2), 2.61 to 2.94 (-O3) | 3.35 to 3.46 (-O2), 3.24 to 3.37 (-O3) |
| `half`, 1 limb, N = 7 | 0.102 to 0.87 (-O2), 0.343 to 0.402 (-O3) | -0.096 to 0.322 (-O2), 0.494 to 0.578 (-O3) | 2.18 to 2.35 (-O2), 2.59 to 2.89 (-O3) | 2.18 to 2.25 (-O2), 2.21 to 2.41 (-O3) |
| `half`, 1 limb, N = 13 | -0.44 to 0.186 (-O2), -0.163 to 0.177 (-O3) | 0.289 to 0.929 (-O2), 0.96 to 1.47 (-O3) | 2.57 to 2.61 (-O2), 2.43 to 2.85 (-O3) | 2.15 to 2.22 (-O2), 1.99 to 2.19 (-O3) |
| `half`, 1 limb, N = 18 | -0.093 to 0.61 (-O2), 0.386 to 0.546 (-O3) | -0.41 to 0.44 (-O2), 0.74 to 1.43 (-O3) | 2.5 to 2.55 (-O2), 2.7 to 2.9 (-O3) | 3.57 to 3.67 (-O2), 3.29 to 3.51 (-O3) |
| `half`, 1 limb, N = 80 | -3.14 to 0.03 (-O2), -0.38 to -0.32 (-O3) | 0.35 to 0.62 (-O2), 0.09 to 2.21 (-O3) | 4.32 to 4.55 (-O2), 2.79 to 4.18 (-O3) | 4.93 to 5.21 (-O2), 5.38 to 5.95 (-O3) |
| `half`, 2 limbs, N = 3 | 0.229 to 0.698 (-O2), 0.199 to 0.286 (-O3) | -0.111 to 0.329 (-O2), 0.723 to 0.915 (-O3) | 2.32 to 2.42 (-O2), 1.82 to 2.1 (-O3) | 2.1 to 2.22 (-O2), 2.07 to 2.34 (-O3) |
| `half`, 2 limbs, N = 7 | 0.177 to 0.238 (-O2), 0.128 to 0.164 (-O3) | 0.001 to 0.629 (-O2), 0.77 to 1.32 (-O3) | 1.13 to 1.28 (-O2), 0.95 to 1.33 (-O3) | 2.53 to 2.7 (-O2), 2.6 to 2.83 (-O3) |
| `half`, 2 limbs, N = 13 | 0.24 to 1.08 (-O2), 0.2 to 0.41 (-O3) | -0.52 to 0.61 (-O2), 0.15 to 1.51 (-O3) | 1.93 to 1.98 (-O2), 0.86 to 1.2 (-O3) | 2.6 to 2.72 (-O2), 2.71 to 2.91 (-O3) |
| `half`, 2 limbs, N = 18 | 0.09 to 1.08 (-O2), -0.02 to 0.28 (-O3) | -0.64 to 0.48 (-O2), 0.95 to 1.51 (-O3) | 1.08 to 1.18 (-O2), 1.14 to 1.26 (-O3) | 2.68 to 2.81 (-O2), 2.54 to 3.08 (-O3) |
| `half`, 2 limbs, N = 80 | 0.01 to 4.44 (-O2), 0.07 to 2.03 (-O3) | -3.1 to 4.53 (-O2), 5.44 to 11.5 (-O3) | 4.17 to 5.14 (-O2), 2.99 to 4.06 (-O3) | 4.78 to 5.31 (-O2), 4.23 to 5.65 (-O3) |
| the constructor, 1 limb, N = 3 | 2.56 to 3.29 (-O2), 3.34 to 7.31 (-O3) | 0.807 to 1.06 (-O2), 3.12 to 3.59 (-O3) | 5.54 to 6.59 (-O2), 6.29 to 7.83 (-O3) | 18.5 to 19 |
| the constructor, 1 limb, N = 7 | -1.85 to 0.16 (-O2), -1.19 to 3.56 (-O3) | 0.25 to 0.435 (-O2), 6.85 to 8.23 (-O3) | 4.71 to 4.82 (-O2), 7.58 to 8.06 (-O3) | -0.15 to 1.17 (-O2), -1.26 to 1.75 (-O3) |
| the constructor, 1 limb, N = 13 | 0.09 to 2.28 (-O2), 0.72 to 1.98 (-O3) | -0.33 to 0.17 (-O2), 14.2 to 16.7 (-O3) | 2.7 to 2.81 (-O2), 6.5 to 6.75 (-O3) | -0.45 to 0.28 (-O2), -0.44 to 0.24 (-O3) |
| the constructor, 1 limb, N = 18 | -5.81 to -2.13 (-O2), 0.64 to 1.23 (-O3) | -0.36 to 0.71 (-O2), 3.01 to 4.76 (-O3) | 2.16 to 2.95 (-O2), 5.8 to 6.66 (-O3) | -0.96 to -0.68 (-O2), 0.91 to 2.27 (-O3) |
| the constructor, 1 limb, N = 80 | -2.77 to -2.67 (-O2), -0.23 to -0.01 (-O3) | -13.9 to 1.8 (-O2), -3.6 to 17.6 (-O3) | -0.2 to 0 (-O2), -7.8 to -6 (-O3) | 2.41 to 2.8 (-O2), 2.65 to 3.58 (-O3) |
| the constructor, 2 limbs, N = 3 | 1.7 to 3.01 (-O2), 1.81 to 2.91 (-O3) | -0.003 to 0.034 (-O2), 3.56 to 4.27 (-O3) | 5.44 to 6.32 (-O2), 8.98 to 10.3 (-O3) | 2.58 to 7.48 (-O2), 7.48 to 7.51 (-O3) |
| the constructor, 2 limbs, N = 7 | -0.38 to 0.63 (-O2), 0.84 to 1.44 (-O3) | -0.25 to 1.42 (-O2), 8.89 to 10.2 (-O3) | 2.51 to 2.95 (-O2), 10.9 to 11.8 (-O3) | -0.84 to 1.25 (-O2), 1.71 to 1.91 (-O3) |
| the constructor, 2 limbs, N = 13 | -0.59 to 0.01 (-O2), -1.3 to 0.09 (-O3) | -1.98 to 0.09 (-O2), 20.4 to 21.6 (-O3) | -1.15 to -0.98 (-O2), 12 to 12.4 (-O3) | 0.24 to 0.76 (-O2), 0.45 to 2.1 (-O3) |
| the constructor, 2 limbs, N = 18 | -1.11 to 0.55 (-O2), -1.2 to -1.08 (-O3) | -1.88 to 0.68 (-O2), 0.47 to 1.6 (-O3) | -0.63 to -0.09 (-O2), -5.4 to -4.84 (-O3) | 2.58 to 3.17 (-O2), 1.74 to 5.09 (-O3) |
| the constructor, 2 limbs, N = 80 | 1.27 to 9.29 (-O2), 0.31 to 5.2 (-O3) | -24.1 to -0.6 (-O2), -24.5 to 14.9 (-O3) | -15.4 to -13.6 (-O2), -5.7 to 0.1 (-O3) | 3.4 to 7.19 (-O2), 6 to 8.58 (-O3) |

| Short ball vectors, every size in one unit, many vectors: the check with its report cold, ns per operation (minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 0.042 to 0.069 (-O2), -0.19 to 0.205 (-O3) | -0.04 to 0.006 (-O2), -0.918 to 0.413 (-O3) | 2.41 to 2.5 (-O2), 2.18 to 2.41 (-O3) | 3.84 to 3.92 |
| `add(x, y, z)`, 1 limb, N = 7 | -0.169 to 0.128 (-O2), -0.173 to 0.364 (-O3) | 0 to 0.002 (-O2), -1.06 to 0.338 (-O3) | 2.59 to 2.75 (-O2), 2.01 to 2.31 (-O3) | 2.63 to 2.65 (-O2), 2.53 to 2.71 (-O3) |
| `add(x, y, z)`, 1 limb, N = 13 | -0.317 to 0.075 (-O2), -0.3 to 0.057 (-O3) | 0.038 to 0.581 (-O2), -0.725 to 0.472 (-O3) | 2.25 to 2.68 (-O2), 2.04 to 2.47 (-O3) | 2.49 to 2.53 (-O2), 2.41 to 2.5 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | -0.404 to 0 (-O2), -0.558 to -0.125 (-O3) | 0.1 to 0.674 (-O2), -1.4 to 0.485 (-O3) | 1.75 to 2.24 (-O2), 2.52 to 2.78 (-O3) | 2.27 to 2.41 (-O2), 2.19 to 2.22 (-O3) |
| `add(x, y, z)`, 1 limb, N = 80 | -2.91 to 0.34 (-O2), -2.29 to 0.63 (-O3) | 0.3 to 4.3 (-O2), -9.81 to 0.06 (-O3) | 3.51 to 4.5 (-O2), 4.02 to 4.92 (-O3) | 3.66 to 3.82 (-O2), 2.54 to 2.93 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | -0.307 to 0.028 (-O2), -0.432 to 0.008 (-O3) | 0.12 to 0.886 (-O2), -1.22 to 0.438 (-O3) | 2.62 to 2.7 (-O2), 2.59 to 2.95 (-O3) | 1.92 to 2.03 (-O2), 1.77 to 1.94 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | -0.55 to 0.026 (-O2), -0.62 to 0.068 (-O3) | -0.06 to 1.07 (-O2), -2.18 to 0.44 (-O3) | 1.58 to 1.6 (-O2), 2.5 to 3 (-O3) | 1.7 to 1.84 (-O2), 1.67 to 1.89 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | -0.98 to -0.29 (-O2), -0.83 to 1.04 (-O3) | -1.23 to 1.82 (-O2), -4.89 to 1.21 (-O3) | 2.73 to 2.93 (-O2), 2.5 to 2.71 (-O3) | 2.18 to 2.29 (-O2), 2.15 to 2.43 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -0.26 to -0.1 (-O2), -1.49 to 1.16 (-O3) | -2.6 to 1.37 (-O2), -5.96 to 1.06 (-O3) | 4.6 to 4.83 (-O2), 4.36 to 4.85 (-O3) | 4.22 to 4.41 (-O2), 4.12 to 4.41 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | 0.2 to 0.58 (-O2), -0.3 to 0.41 (-O3) | -6.26 to 4.24 (-O2), -18.1 to 4.15 (-O3) | 2.34 to 3.76 (-O2), 3.67 to 4.06 (-O3) | 4.08 to 4.33 (-O2), 3.25 to 4.21 (-O3) |
| `z = x + y`, 1 limb, N = 3 | 0.107 to 0.295 (-O2), -0.227 to 0.128 (-O3) | 0.108 to 0.495 (-O2), -1.07 to 0.15 (-O3) | 4.52 to 4.78 (-O2), 4 to 4.78 (-O3) | 3.21 to 3.35 |
| `z = x + y`, 1 limb, N = 7 | -0.112 to 0.081 (-O2), -0.357 to 0.328 (-O3) | -0.025 to 0.327 (-O2), -1.68 to -0.016 (-O3) | 3.31 to 20.3 (-O2), 4.11 to 4.35 (-O3) | 2.36 to 2.38 (-O2), 2.32 to 2.49 (-O3) |
| `z = x + y`, 1 limb, N = 13 | -0.564 to -0.187 (-O2), -0.496 to 0.004 (-O3) | -0.08 to 1.04 (-O2), -1.77 to 0.348 (-O3) | 3.12 to 3.58 (-O2), 2.92 to 3.18 (-O3) | 2.16 to 2.25 (-O2), 2.12 to 2.25 (-O3) |
| `z = x + y`, 1 limb, N = 18 | -0.46 to 0.121 (-O2), -0.391 to -0.3 (-O3) | -0.85 to 1.58 (-O2), -2.61 to 0.76 (-O3) | 2.11 to 2.77 (-O2), 2.87 to 3.16 (-O3) | 1.69 to 1.77 (-O2), 1.5 to 1.86 (-O3) |
| `z = x + y`, 1 limb, N = 80 | -0.36 to -0.18 (-O2), -2.84 to 0.09 (-O3) | 0.18 to 5.95 (-O2), -12.9 to 1.14 (-O3) | 0.99 to 2.06 (-O2), 5.41 to 6.81 (-O3) | -2.34 to 2.06 (-O2), 2.02 to 6.97 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -0.326 to 0.179 (-O2), -0.516 to 0.146 (-O3) | 0.246 to 1.28 (-O2), -1.49 to 0.18 (-O3) | 2.94 to 3.26 (-O2), 2.61 to 3.17 (-O3) | 2.71 to 3.71 (-O2), 2.61 to 2.76 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | -0.55 to 0.13 (-O2), -0.77 to 0.68 (-O3) | 0.6 to 2.06 (-O2), -2.42 to 0.6 (-O3) | 2.23 to 2.65 (-O2), 2.53 to 2.96 (-O3) | 2.37 to 4.19 (-O2), 2.41 to 2.71 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | -0.33 to 0.3 (-O2), 0.19 to 0.92 (-O3) | 0.31 to 2.36 (-O2), -3.39 to 1.6 (-O3) | 2.57 to 3.5 (-O2), 0.83 to 1.45 (-O3) | 2.17 to 3.82 (-O2), 2.23 to 2.71 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -1.48 to 0.6 (-O2), -1.58 to 0.56 (-O3) | -0.06 to 4.26 (-O2), -7.41 to 1.31 (-O3) | 0.42 to 0.86 (-O2), -0.13 to 0.47 (-O3) | 3.66 to 5.31 (-O2), 3.37 to 16.6 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | -0.2 to 2.8 (-O2), 0.8 to 4.5 (-O3) | -7.2 to 6.9 (-O2), -21.8 to 5.4 (-O3) | -0.4 to 2.3 (-O2), -1.1 to 3 (-O3) | 0.7 to 3.5 (-O2), -3.1 to 3.4 (-O3) |
| `sub`, 1 limb, N = 3 | 0.048 to 0.057 (-O2), -0.168 to 0.144 (-O3) | 0.04 to 0.54 (-O2), -0.918 to 0.253 (-O3) | 2.43 to 2.55 (-O2), 3.38 to 3.51 (-O3) | 3.84 to 3.92 |
| `sub`, 1 limb, N = 7 | -0.202 to 0.08 (-O2), -0.123 to 0.347 (-O3) | -0.445 to 0.381 (-O2), -1.07 to 0.335 (-O3) | 2.48 to 2.63 (-O2), 1.79 to 1.91 (-O3) | 2.62 (-O2), 2.54 to 2.73 (-O3) |
| `sub`, 1 limb, N = 13 | -0.353 to -0.018 (-O2), -0.389 to 0.04 (-O3) | 0.05 to 1.14 (-O2), -0.728 to 0.864 (-O3) | 2.62 to 2.81 (-O2), 2.05 to 2.09 (-O3) | 2.51 to 2.54 (-O2), 2.37 to 2.53 (-O3) |
| `sub`, 1 limb, N = 18 | -0.394 to 0.21 (-O2), -0.556 to 0.342 (-O3) | -0.687 to 1.47 (-O2), -1.44 to 0.55 (-O3) | 2 to 2.3 (-O2), 2.14 to 2.23 (-O3) | 2.23 to 2.36 (-O2), 2.2 to 2.24 (-O3) |
| `sub`, 1 limb, N = 80 | 0.32 to 0.38 (-O2), -2.33 to -0.01 (-O3) | -0.03 to 3.94 (-O2), -9.73 to 0 (-O3) | 3.71 to 4.47 (-O2), 3.38 to 3.57 (-O3) | 3.65 to 3.75 (-O2), 2.48 to 2.79 (-O3) |
| `sub`, 2 limbs, N = 3 | -0.225 to 0.264 (-O2), -0.459 to 0.33 (-O3) | 0.209 to 0.962 (-O2), -1.01 to 0.072 (-O3) | 2.57 to 2.63 (-O2), 2.15 to 2.42 (-O3) | 2.09 to 2.25 (-O2), 2.11 to 2.32 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.47 to 0.06 (-O2), -0.74 to 0.59 (-O3) | 0.09 to 1.33 (-O2), -1.9 to 0.41 (-O3) | 2.01 to 2.1 (-O2), 1.4 to 1.69 (-O3) | 3.02 to 3.11 (-O2), 2.86 to 3.11 (-O3) |
| `sub`, 2 limbs, N = 13 | -0.53 to 0.9 (-O2), 0 to 0.83 (-O3) | 0.06 to 2.05 (-O2), -3.17 to 0.75 (-O3) | 2.45 to 2.66 (-O2), 1.9 to 2.16 (-O3) | 2.89 to 2.99 (-O2), 2.73 to 3.02 (-O3) |
| `sub`, 2 limbs, N = 18 | -0.23 to 0.67 (-O2), 0.53 to 1.26 (-O3) | -0.67 to 3.1 (-O2), -5.84 to 0.72 (-O3) | 3.94 to 4.24 (-O2), 3.63 to 4.07 (-O3) | 4.83 to 5 (-O2), 4.67 to 5.13 (-O3) |
| `sub`, 2 limbs, N = 80 | -0.08 to 2.43 (-O2), 0.6 to 4.77 (-O3) | -8.2 to 3.32 (-O2), -15.7 to 0.85 (-O3) | 2.6 to 3.81 (-O2), 2.92 to 3.57 (-O3) | 4.44 to 4.83 (-O2), 3.9 to 4.84 (-O3) |
| `scale`, 1 limb, N = 3 | -0.133 to 0.089 (-O2), -0.231 to 0.35 (-O3) | 0.375 to 0.546 (-O2), -0.977 to 0.186 (-O3) | 2.64 to 2.71 (-O2), 1.68 to 1.94 (-O3) | 3.87 to 3.94 |
| `scale`, 1 limb, N = 7 | -0.064 to 0.057 (-O2), -0.181 to 0.5 (-O3) | -0.316 to 0.534 (-O2), -1.18 to 0.182 (-O3) | 2.96 to 3.04 (-O2), 1.94 to 2.14 (-O3) | 2.6 to 2.72 |
| `scale`, 1 limb, N = 13 | -0.63 to -0.057 (-O2), -0.355 to 0.145 (-O3) | -0.172 to 0.541 (-O2), -1.12 to 0.418 (-O3) | 2.46 to 2.91 (-O2), 2.6 to 3 (-O3) | 2.53 to 2.56 (-O2), 2.33 to 2.57 (-O3) |
| `scale`, 1 limb, N = 18 | -0.227 to 0.669 (-O2), -0.61 to 0.187 (-O3) | -0.486 to 0.47 (-O2), -1.4 to 0.499 (-O3) | 2 to 2.29 (-O2), 2.59 to 2.87 (-O3) | 2.37 to 2.44 (-O2), 2.31 to 2.39 (-O3) |
| `scale`, 1 limb, N = 80 | -1.61 to 0.19 (-O2), 0.23 to 1.81 (-O3) | 0.26 to 4.13 (-O2), -7.05 to 1.93 (-O3) | 3.76 to 4.29 (-O2), 3.31 to 3.7 (-O3) | 2.97 to 3.05 (-O2), 1.97 to 17.5 (-O3) |
| `scale`, 2 limbs, N = 3 | 0.053 to 0.064 (-O2), 0.011 to 0.15 (-O3) | 0.105 to 0.624 (-O2), -0.76 to 0.292 (-O3) | 2.84 to 2.92 (-O2), -5.48 to -5.34 (-O3) | 2.64 to 2.71 (-O2), 2.58 to 2.69 (-O3) |
| `scale`, 2 limbs, N = 7 | -0.004 to 0.025 (-O2), -0.375 to 0.202 (-O3) | 0.124 to 1.08 (-O2), -1.31 to 0.39 (-O3) | 2.63 to 2.77 (-O2), -3.7 to -3.39 (-O3) | 1.91 to 2.01 (-O2), 1.86 to 1.95 (-O3) |
| `scale`, 2 limbs, N = 13 | -0.491 to 0.736 (-O2), -0.055 to 0.561 (-O3) | 0.03 to 1.83 (-O2), -2.37 to 0.74 (-O3) | 2.72 to 2.92 (-O2), -4.16 to -3.92 (-O3) | 2.81 to 2.94 (-O2), 2.82 to 3.05 (-O3) |
| `scale`, 2 limbs, N = 18 | 0.1 to 0.37 (-O2), -0.04 to 0.9 (-O3) | -0.73 to 1.61 (-O2), -2.96 to 0.83 (-O3) | 2.71 to 2.8 (-O2), -3.88 to -3.74 (-O3) | 1.76 to 1.83 (-O2), 1.72 to 2.04 (-O3) |
| `scale`, 2 limbs, N = 80 | 0.39 to 3.51 (-O2), -3.36 to 2.32 (-O3) | 0.05 to 2.19 (-O2), -11.6 to 2.44 (-O3) | 2.9 to 3.64 (-O2), -2.24 to -1.34 (-O3) | 1.81 to 1.9 (-O2), 1.44 to 2 (-O3) |
| `half`, 1 limb, N = 3 | 0.016 to 0.097 (-O2), -0.143 to 0.145 (-O3) | 0.316 to 0.612 (-O2), -1.03 to 0.381 (-O3) | 2.25 to 2.32 (-O2), 2.33 to 2.61 (-O3) | 2.43 to 2.47 (-O2), 2.35 to 2.51 (-O3) |
| `half`, 1 limb, N = 7 | -0.035 to 0.114 (-O2), -0.255 to 0.57 (-O3) | -0.164 to 0.382 (-O2), -1.54 to 0.003 (-O3) | 1.78 to 1.93 (-O2), 2.06 to 2.39 (-O3) | 2.25 to 2.32 (-O2), 2.04 to 2.24 (-O3) |
| `half`, 1 limb, N = 13 | -1.08 to 0.14 (-O2), -0.017 to 0.418 (-O3) | 0.196 to 0.814 (-O2), -1.25 to 0.672 (-O3) | 2.36 to 2.57 (-O2), 2.34 to 2.81 (-O3) | 2.31 to 2.38 (-O2), 1.97 to 2.16 (-O3) |
| `half`, 1 limb, N = 18 | -0.1 to 0.06 (-O2), -0.84 to 0.274 (-O3) | -0.831 to -0.08 (-O2), -1.96 to 0.37 (-O3) | 2.06 to 2.26 (-O2), 2.19 to 2.36 (-O3) | 3.42 to 3.6 (-O2), 3.42 to 3.59 (-O3) |
| `half`, 1 limb, N = 80 | -3.6 to -0.43 (-O2), -1.81 to 1.55 (-O3) | -0.48 to 3.61 (-O2), -8.05 to 1.53 (-O3) | 3.37 to 3.8 (-O2), 2.72 to 3.22 (-O3) | 4.91 to 5.12 (-O2), 5.65 to 5.9 (-O3) |
| `half`, 2 limbs, N = 3 | 0.07 to 0.249 (-O2), -0.198 to 0.245 (-O3) | 0.318 to 0.921 (-O2), -0.773 to 0.583 (-O3) | 1.91 to 1.98 (-O2), 1.12 to 1.35 (-O3) | 1.9 to 1.97 (-O2), 1.91 to 2.02 (-O3) |
| `half`, 2 limbs, N = 7 | -0.399 to 0.14 (-O2), -0.181 to 0.108 (-O3) | 0.005 to 0.906 (-O2), -1.3 to 0.723 (-O3) | 0.96 to 1.12 (-O2), 0.72 to 1.05 (-O3) | 2.48 to 2.57 (-O2), 2.4 to 2.55 (-O3) |
| `half`, 2 limbs, N = 13 | -0.65 to 1.05 (-O2), -0.66 to 0.7 (-O3) | -0.56 to 1.55 (-O2), -2.81 to 0.88 (-O3) | 1.68 to 1.87 (-O2), 0.76 to 1.11 (-O3) | 2.79 to 2.84 (-O2), 2.84 to 3 (-O3) |
| `half`, 2 limbs, N = 18 | 0.03 to 0.64 (-O2), -0.87 to 1.18 (-O3) | -0.74 to 1 (-O2), -3.63 to 0.87 (-O3) | 1.06 to 1.11 (-O2), 1.14 to 1.43 (-O3) | 2.94 to 3.03 (-O2), 2.59 to 2.94 (-O3) |
| `half`, 2 limbs, N = 80 | -0.11 to 4.25 (-O2), -1.82 to 2.62 (-O3) | 0.19 to 4.03 (-O2), -9.54 to 7.73 (-O3) | 3.2 to 3.89 (-O2), 3.21 to 4.18 (-O3) | 4.72 to 5.34 (-O2), 5.02 to 5.95 (-O3) |
| the constructor, 1 limb, N = 3 | 2.31 to 10.9 (-O2), 3.07 to 11.4 (-O3) | 0.211 to 0.709 (-O2), -0.391 to 0.369 (-O3) | 5.33 to 6.35 (-O2), 5.41 to 7.23 (-O3) | 18.6 to 18.8 (-O2), 12.3 to 12.5 (-O3) |
| the constructor, 1 limb, N = 7 | -0.39 to 2.27 (-O2), -0.47 to 1.63 (-O3) | 0.846 to 1.23 (-O2), -0.869 to 0.14 (-O3) | 5.04 to 5.12 (-O2), 5.66 to 6.27 (-O3) | -0.03 to 1.76 (-O2), -1.17 to 1.81 (-O3) |
| the constructor, 1 limb, N = 13 | -1.38 to 1.74 (-O2), 2.24 to 3.59 (-O3) | -1.07 to 0.3 (-O2), -1.15 to 0.554 (-O3) | 2.62 to 2.68 (-O2), 3.57 to 3.8 (-O3) | -0.6 to 0.69 (-O2), -0.37 to 0.23 (-O3) |
| the constructor, 1 limb, N = 18 | -4.53 to -1.29 (-O2), -1.41 to 3.42 (-O3) | -2.47 to 1.63 (-O2), -4.68 to 1.61 (-O3) | 5.01 to 5.12 (-O2), 5.4 to 5.74 (-O3) | -0.89 to 0.93 (-O2), 0.16 to 2.24 (-O3) |
| the constructor, 1 limb, N = 80 | -5.74 to -0.28 (-O2), -6.39 to -0.82 (-O3) | 0.8 to 24.7 (-O2), -42.6 to 11.4 (-O3) | -2.7 to -2.2 (-O2), 0 to 0.9 (-O3) | -1.03 to 1.1 (-O2), 2.52 to 11.9 (-O3) |
| the constructor, 2 limbs, N = 3 | 1.92 to 3.19 (-O2), 1.79 to 2.17 (-O3) | -0.161 to 0.536 (-O2), -0.976 to 0.011 (-O3) | 5.46 to 6.36 (-O2), 5.63 to 6.28 (-O3) | 7.57 to 7.81 |
| the constructor, 2 limbs, N = 7 | -4.48 to 0.29 (-O2), -2.54 to -1.53 (-O3) | -0.29 to 2.24 (-O2), -0.812 to 0.805 (-O3) | 2.72 to 2.97 (-O2), 6.07 to 6.91 (-O3) | 1.22 to 1.63 (-O2), -0.13 to 1.93 (-O3) |
| the constructor, 2 limbs, N = 13 | -0.85 to 0.89 (-O2), -3.68 to 1.14 (-O3) | -2.14 to 3.01 (-O2), -2.88 to 0.09 (-O3) | 1.3 to 1.36 (-O2), 3.29 to 3.78 (-O3) | 0.95 to 2.06 (-O2), 0.54 to 6.13 (-O3) |
| the constructor, 2 limbs, N = 18 | -3.33 to -1.6 (-O2), -0.95 to 1.68 (-O3) | -3.08 to 3.83 (-O2), -8.71 to 0.49 (-O3) | -1.34 to -0.96 (-O2), -11.9 to -11.3 (-O3) | 2.5 to 2.61 (-O2), 1.18 to 4.81 (-O3) |
| the constructor, 2 limbs, N = 80 | 1.87 to 10.4 (-O2), -2.3 to 4.7 (-O3) | -0.4 to 15.1 (-O2), -78.4 to 13.3 (-O3) | -0.3 to 1.2 (-O2), -18 to -11 (-O3) | 4 to 8 (-O2), 2.9 to 8.18 (-O3) |

| Short ball vectors, every size in one unit, many vectors: with the check over without | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 1.13 to 1.20 (-O2), 1.10 to 1.19 (-O3) | 0.94 to 1.09 (-O2), 1.01 to 1.12 (-O3) | 1.19 to 1.21 | 1.77 to 1.80 |
| `add(x, y, z)`, 1 limb, N = 7 | 1.05 to 1.08 (-O2), 0.99 to 1.07 (-O3) | 0.93 to 1.00 (-O2), 1.06 (-O3) | 1.16 to 1.18 | 1.38 to 1.40 |
| `add(x, y, z)`, 1 limb, N = 13 | 1.02 to 1.07 | 0.98 to 1.01 (-O2), 1.10 to 1.21 (-O3) | 1.12 to 1.17 | 1.34 to 1.37 |
| `add(x, y, z)`, 1 limb, N = 18 | 0.92 to 1.01 (-O2), 0.98 to 1.02 (-O3) | 1.01 to 1.04 (-O2), 1.05 to 1.12 (-O3) | 1.11 to 1.13 (-O2), 1.18 to 1.20 (-O3) | 1.27 to 1.32 |
| `add(x, y, z)`, 1 limb, N = 80 | 0.97 to 1.01 (-O2), 0.94 to 1.00 (-O3) | 0.99 to 1.04 | 1.18 to 1.20 (-O2), 1.14 to 1.20 (-O3) | 1.15 to 1.19 |
| `add(x, y, z)`, 2 limbs, N = 3 | 1.02 to 1.03 | 1.01 to 1.03 (-O2), 1.05 to 1.10 (-O3) | 1.11 to 1.14 | 1.10 to 1.12 |
| `add(x, y, z)`, 2 limbs, N = 7 | 0.99 to 1.01 (-O2), 0.95 to 0.99 (-O3) | 0.99 to 1.01 (-O2), 1.01 to 1.06 (-O3) | 1.05 to 1.06 (-O2), 1.11 to 1.14 (-O3) | 1.07 to 1.09 |
| `add(x, y, z)`, 2 limbs, N = 13 | 0.98 to 1.02 (-O2), 1.01 to 1.03 (-O3) | 1.00 to 1.01 (-O2), 0.99 to 1.08 (-O3) | 1.10 to 1.12 | 1.09 to 1.11 |
| `add(x, y, z)`, 2 limbs, N = 18 | 0.98 to 1.02 | 0.95 to 1.00 (-O2), 0.94 to 1.05 (-O3) | 1.12 to 1.14 | 1.13 to 1.14 |
| `add(x, y, z)`, 2 limbs, N = 80 | 0.93 to 1.02 (-O2), 0.97 to 1.01 (-O3) | 0.95 to 1.02 (-O2), 0.98 to 1.05 (-O3) | 1.03 to 1.07 | 1.04 to 1.05 |
| `z = x + y`, 1 limb, N = 3 | 1.09 to 1.16 (-O2), 1.02 to 1.10 (-O3) | 0.98 to 1.06 (-O2), 1.01 to 1.05 (-O3) | 1.23 to 1.27 (-O2), 1.28 to 1.36 (-O3) | 1.58 to 1.61 |
| `z = x + y`, 1 limb, N = 7 | 0.97 to 1.02 (-O2), 0.92 to 1.00 (-O3) | 0.92 to 1.00 (-O2), 1.05 to 1.09 (-O3) | 1.20 to 1.23 | 1.31 to 1.34 |
| `z = x + y`, 1 limb, N = 13 | 1.22 to 1.38 (-O2), 1.35 to 1.36 (-O3) | 0.99 to 1.05 (-O2), 1.01 to 1.09 (-O3) | 1.17 to 1.20 | 1.25 to 1.30 |
| `z = x + y`, 1 limb, N = 18 | 0.92 to 1.00 (-O2), 0.98 to 1.02 (-O3) | 1.03 to 1.04 (-O2), 1.02 to 1.08 (-O3) | 1.10 to 1.14 (-O2), 1.15 to 1.17 (-O3) | 1.20 to 1.25 (-O2), 1.19 to 1.22 (-O3) |
| `z = x + y`, 1 limb, N = 80 | 0.96 to 1.03 (-O2), 0.99 to 1.00 (-O3) | 1.00 to 1.05 | 1.03 to 1.04 (-O2), 1.02 to 1.08 (-O3) | 0.88 to 1.03 (-O2), 1.03 to 1.06 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 0.96 to 1.02 (-O2), 1.00 to 1.02 (-O3) | 1.03 to 1.07 | 1.11 to 1.13 | 1.05 to 1.23 (-O2), 1.14 to 1.16 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 0.99 to 1.02 | 1.02 to 1.04 (-O2), 1.08 to 1.13 (-O3) | 1.07 to 1.09 | 1.03 to 1.19 (-O2), 1.09 to 1.12 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 0.96 to 1.09 (-O2), 1.00 to 1.02 (-O3) | 1.01 to 1.06 (-O2), 1.02 to 1.08 (-O3) | 1.05 to 1.08 | 1.02 to 1.15 (-O2), 1.08 to 1.09 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 0.98 to 1.02 | 0.96 to 1.05 (-O2), 0.95 to 1.03 (-O3) | 1.00 to 1.02 | 1.04 to 1.15 (-O2), 1.07 to 1.10 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 0.93 to 1.00 (-O2), 0.99 to 1.01 (-O3) | 1.01 to 1.05 (-O2), 1.00 to 1.05 (-O3) | 1.00 to 1.02 | 0.99 to 1.03 |
| `sub`, 1 limb, N = 3 | 1.06 to 1.14 (-O2), 1.08 to 1.13 (-O3) | 1.00 to 1.09 (-O2), 1.02 to 1.07 (-O3) | 1.20 (-O2), 1.74 to 1.76 (-O3) | 1.77 to 1.80 |
| `sub`, 1 limb, N = 7 | 0.97 to 1.08 (-O2), 0.97 to 1.06 (-O3) | 0.96 to 1.00 (-O2), 1.07 (-O3) | 1.17 to 1.18 (-O2), 1.25 to 1.27 (-O3) | 1.38 to 1.41 |
| `sub`, 1 limb, N = 13 | 0.96 to 1.07 (-O2), 1.04 to 1.06 (-O3) | 1.06 to 1.08 (-O2), 1.13 to 1.20 (-O3) | 1.13 to 1.16 (-O2), 1.28 to 1.29 (-O3) | 1.34 to 1.37 |
| `sub`, 1 limb, N = 18 | 0.94 to 1.00 (-O2), 0.99 to 1.02 (-O3) | 1.00 to 1.01 (-O2), 1.05 to 1.12 (-O3) | 1.13 to 1.14 (-O2), 1.22 (-O3) | 1.28 to 1.32 |
| `sub`, 1 limb, N = 80 | 1.01 to 1.09 (-O2), 1.00 (-O3) | 0.99 to 1.04 | 1.19 to 1.21 (-O2), 1.13 to 1.16 (-O3) | 1.18 to 1.19 (-O2), 1.12 to 1.14 (-O3) |
| `sub`, 2 limbs, N = 3 | 0.98 to 1.02 (-O2), 1.01 to 1.08 (-O3) | 1.02 to 1.06 | 1.11 (-O2), 1.16 to 1.17 (-O3) | 1.12 to 1.14 |
| `sub`, 2 limbs, N = 7 | 0.96 to 1.00 (-O2), 1.00 to 1.01 (-O3) | 1.00 to 1.01 (-O2), 1.02 to 1.07 (-O3) | 1.07 to 1.08 (-O2), 1.10 to 1.12 (-O3) | 1.11 to 1.13 |
| `sub`, 2 limbs, N = 13 | 0.99 to 1.13 (-O2), 1.01 to 1.02 (-O3) | 1.01 to 1.05 (-O2), 1.00 to 1.05 (-O3) | 1.09 to 1.12 | 1.10 to 1.12 |
| `sub`, 2 limbs, N = 18 | 0.99 to 1.08 (-O2), 1.00 to 1.01 (-O3) | 1.00 to 1.01 (-O2), 0.94 to 1.04 (-O3) | 1.11 to 1.13 | 1.13 to 1.16 |
| `sub`, 2 limbs, N = 80 | 0.94 to 1.00 (-O2), 1.00 (-O3) | 0.99 to 1.05 (-O2), 1.00 to 1.01 (-O3) | 1.03 to 1.06 | 1.03 to 1.05 |
| `scale`, 1 limb, N = 3 | 1.08 to 1.13 (-O2), 1.06 to 1.14 (-O3) | 1.08 to 1.27 (-O2), 1.07 (-O3) | 1.19 to 1.23 | 1.84 to 1.86 |
| `scale`, 1 limb, N = 7 | 0.97 to 1.12 (-O2), 1.05 to 1.12 (-O3) | 1.04 to 1.12 (-O2), 1.06 (-O3) | 1.20 to 1.21 (-O2), 1.15 to 1.18 (-O3) | 1.39 to 1.41 |
| `scale`, 1 limb, N = 13 | 0.97 to 1.01 (-O2), 1.00 to 1.02 (-O3) | 1.01 to 1.02 (-O2), 1.07 to 1.14 (-O3) | 1.15 to 1.16 (-O2), 1.18 to 1.21 (-O3) | 1.34 to 1.37 |
| `scale`, 1 limb, N = 18 | 0.99 to 1.06 (-O2), 0.96 to 1.03 (-O3) | 0.97 to 1.01 (-O2), 1.05 to 1.12 (-O3) | 1.13 to 1.14 (-O2), 1.16 to 1.18 (-O3) | 1.32 to 1.35 |
| `scale`, 1 limb, N = 80 | 1.00 to 1.05 | 1.03 to 1.10 (-O2), 1.03 to 1.06 (-O3) | 1.17 to 1.18 (-O2), 1.14 to 1.19 (-O3) | 1.16 (-O2), 1.09 to 1.25 (-O3) |
| `scale`, 2 limbs, N = 3 | 1.03 to 1.04 | 1.05 to 1.07 | 1.17 (-O2), 0.75 to 0.76 (-O3) | 1.32 to 1.35 |
| `scale`, 2 limbs, N = 7 | 1.06 to 1.08 | 1.01 to 1.02 (-O2), 1.04 to 1.10 (-O3) | 1.15 to 1.16 (-O2), 0.82 to 0.83 (-O3) | 1.24 to 1.26 |
| `scale`, 2 limbs, N = 13 | 1.03 to 1.11 (-O2), 1.00 to 1.04 (-O3) | 0.94 to 1.01 (-O2), 0.98 to 1.09 (-O3) | 1.14 to 1.15 (-O2), 0.81 to 0.82 (-O3) | 1.25 to 1.27 |
| `scale`, 2 limbs, N = 18 | 1.01 to 1.10 (-O2), 0.98 to 1.02 (-O3) | 0.95 to 1.14 (-O2), 1.00 to 1.07 (-O3) | 1.12 to 1.13 (-O2), 0.86 to 0.87 (-O3) | 1.10 to 1.13 |
| `scale`, 2 limbs, N = 80 | 0.99 to 1.01 | 0.95 to 1.05 (-O2), 0.95 to 1.06 (-O3) | 1.11 to 1.15 (-O2), 0.97 (-O3) | 1.03 to 1.04 |
| `half`, 1 limb, N = 3 | 1.06 to 1.16 (-O2), 1.05 to 1.09 (-O3) | 1.04 to 1.11 (-O2), 1.06 (-O3) | 1.14 to 1.15 (-O2), 1.17 to 1.19 (-O3) | 1.37 to 1.39 |
| `half`, 1 limb, N = 7 | 1.02 to 1.14 (-O2), 1.07 (-O3) | 0.99 to 1.05 (-O2), 1.07 to 1.08 (-O3) | 1.12 to 1.13 (-O2), 1.15 to 1.17 (-O3) | 1.18 to 1.20 |
| `half`, 1 limb, N = 13 | 0.96 to 1.03 (-O2), 0.98 to 1.02 (-O3) | 1.03 to 1.10 (-O2), 1.09 to 1.16 (-O3) | 1.14 to 1.17 | 1.16 to 1.19 |
| `half`, 1 limb, N = 18 | 0.99 to 1.07 (-O2), 1.04 to 1.06 (-O3) | 0.97 to 1.04 (-O2), 1.06 to 1.13 (-O3) | 1.12 to 1.15 | 1.24 to 1.27 |
| `half`, 1 limb, N = 80 | 0.92 to 1.00 (-O2), 0.99 (-O3) | 1.00 to 1.05 | 1.08 to 1.13 | 1.16 to 1.19 |
| `half`, 2 limbs, N = 3 | 1.05 to 1.13 (-O2), 1.04 to 1.05 (-O3) | 0.98 to 1.05 (-O2), 1.11 to 1.16 (-O3) | 1.09 to 1.11 | 1.16 to 1.19 |
| `half`, 2 limbs, N = 7 | 1.02 to 1.03 | 1.00 to 1.06 (-O2), 1.07 to 1.14 (-O3) | 1.04 to 1.05 | 1.16 to 1.18 |
| `half`, 2 limbs, N = 13 | 1.02 to 1.10 (-O2), 1.02 to 1.03 (-O3) | 0.96 to 1.05 (-O2), 1.01 to 1.12 (-O3) | 1.04 to 1.09 | 1.16 to 1.18 |
| `half`, 2 limbs, N = 18 | 1.01 to 1.08 (-O2), 1.00 to 1.02 (-O3) | 0.96 to 1.03 (-O2), 1.05 to 1.10 (-O3) | 1.04 | 1.13 to 1.15 |
| `half`, 2 limbs, N = 80 | 1.00 to 1.09 (-O2), 1.00 to 1.03 (-O3) | 0.95 to 1.08 (-O2), 1.08 to 1.21 (-O3) | 1.05 to 1.09 | 1.08 to 1.11 |
| the constructor, 1 limb, N = 3 | 1.71 to 2.00 (-O2), 2.00 to 2.87 (-O3) | 1.22 to 1.26 (-O2), 2.10 to 2.21 (-O3) | 1.49 to 1.64 (-O2), 1.58 to 1.78 (-O3) | 4.09 to 4.17 (-O2), 4.05 to 4.11 (-O3) |
| the constructor, 1 limb, N = 7 | 0.92 to 1.01 (-O2), 0.95 to 1.17 (-O3) | 1.02 to 1.05 (-O2), 2.68 (-O3) | 1.33 (-O2), 1.59 to 1.65 (-O3) | 0.99 to 1.04 (-O2), 0.96 to 1.06 (-O3) |
| the constructor, 1 limb, N = 13 | 1.00 to 1.10 (-O2), 1.03 to 1.08 (-O3) | 0.98 to 1.01 (-O2), 2.80 to 2.97 (-O3) | 1.13 (-O2), 1.34 to 1.36 (-O3) | 0.99 to 1.01 |
| the constructor, 1 limb, N = 18 | 0.77 to 0.90 (-O2), 1.02 to 1.05 (-O3) | 0.99 to 1.03 (-O2), 1.09 to 1.16 (-O3) | 1.08 to 1.11 (-O2), 1.22 to 1.25 (-O3) | 0.96 to 0.97 (-O2), 1.03 to 1.07 (-O3) |
| the constructor, 1 limb, N = 80 | 0.96 to 1.00 | 0.94 to 1.01 (-O2), 0.99 to 1.07 (-O3) | 1.00 (-O2), 0.95 to 0.96 (-O3) | 1.03 to 1.05 |
| the constructor, 2 limbs, N = 3 | 1.36 to 1.50 (-O2), 1.34 to 1.48 (-O3) | 1.00 to 1.01 (-O2), 1.85 to 1.99 (-O3) | 1.50 to 1.63 (-O2), 1.86 to 2.01 (-O3) | 1.30 to 1.88 (-O2), 1.88 to 1.89 (-O3) |
| the constructor, 2 limbs, N = 7 | 0.98 to 1.03 (-O2), 1.04 to 1.06 (-O3) | 0.98 to 1.11 (-O2), 2.35 to 2.54 (-O3) | 1.14 to 1.17 (-O2), 1.93 to 2.02 (-O3) | 0.95 to 1.08 (-O2), 1.11 to 1.12 (-O3) |
| the constructor, 2 limbs, N = 13 | 0.96 to 1.00 | 0.95 to 1.00 (-O2), 2.69 to 3.01 (-O3) | 0.97 to 0.98 (-O2), 1.69 to 1.72 (-O3) | 1.01 to 1.03 (-O2), 1.02 to 1.09 (-O3) |
| the constructor, 2 limbs, N = 18 | 0.96 to 1.02 (-O2), 0.95 to 0.96 (-O3) | 0.96 to 1.01 (-O2), 1.01 to 1.03 (-O3) | 0.99 to 1.00 (-O2), 0.86 to 0.88 (-O3) | 1.08 to 1.09 (-O2), 1.05 to 1.16 (-O3) |
| the constructor, 2 limbs, N = 80 | 1.01 to 1.10 (-O2), 1.00 to 1.04 (-O3) | 0.94 to 1.00 (-O2), 0.94 to 1.05 (-O3) | 0.93 to 0.94 (-O2), 0.97 to 1.00 (-O3) | 1.03 to 1.07 (-O2), 1.06 to 1.09 (-O3) |

| Short ball vectors, every size in one unit, a dependent chain: ns per operation, with the check | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 14.3 to 19.4 (-O2), 14.2 to 19.4 (-O3) | 5.25 to 6.57 (-O2), 5.73 to 7.52 (-O3) | 15.4 to 15.7 (-O2), 14.6 to 14.7 (-O3) | 8.76 to 8.84 |
| `add(x, y, z)`, 1 limb, N = 7 | 14.2 to 20 (-O2), 14.3 to 19.5 (-O3) | 5.65 to 7.73 (-O2), 6.61 to 8.17 (-O3) | 16.8 (-O2), 15.9 to 16 (-O3) | 9.65 to 9.79 |
| `add(x, y, z)`, 1 limb, N = 13 | 8.58 to 12.2 (-O2), 8.88 to 13.1 (-O3) | 8 to 9.86 (-O2), 8.85 to 10.7 (-O3) | 16.9 to 17.3 (-O2), 15.8 to 16 (-O3) | 10.3 to 10.4 |
| `add(x, y, z)`, 1 limb, N = 18 | 8.93 to 12.2 (-O2), 8.84 to 14.9 (-O3) | 9.22 to 10.4 (-O2), 9.58 to 11.5 (-O3) | 17.5 to 18.2 | 11 to 11.1 |
| `add(x, y, z)`, 1 limb, N = 80 | 30.5 to 39.9 (-O2), 30.3 to 39.6 (-O3) | 39 to 43.9 (-O2), 34.5 to 41.5 (-O3) | 30 to 31.7 (-O2), 29.7 to 30.3 (-O3) | 22 to 22.2 (-O2), 20.2 to 20.4 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | 19.8 to 27.2 (-O2), 19.4 to 25.6 (-O3) | 11.5 to 13.8 (-O2), 13 to 15.6 (-O3) | 25.9 to 27.1 | 17.5 to 17.7 |
| `add(x, y, z)`, 2 limbs, N = 7 | 11.4 to 15.6 (-O2), 11.4 to 15.4 (-O3) | 13.9 to 14.7 (-O2), 14.1 to 17 (-O3) | 31.7 to 32.2 | 22.8 to 23.2 |
| `add(x, y, z)`, 2 limbs, N = 13 | 16 to 21.1 (-O2), 16 to 20.5 (-O3) | 18.8 to 20.2 (-O2), 24.4 to 27.5 (-O3) | 31.4 to 32.5 | 24.5 to 24.7 |
| `add(x, y, z)`, 2 limbs, N = 18 | 20.6 to 28.6 (-O2), 20.1 to 26.1 (-O3) | 23.7 to 26.6 (-O2), 24.5 to 29.4 (-O3) | 39.8 to 41.3 | 34.2 to 34.7 |
| `add(x, y, z)`, 2 limbs, N = 80 | 79.4 to 103 (-O2), 79.7 to 102 (-O3) | 82.7 to 98.1 (-O2), 91.6 to 102 (-O3) | 98.1 to 101 | 94.4 to 94.9 |
| `z = x + y`, 1 limb, N = 3 | 16.4 to 21.2 (-O2), 16.4 to 21.2 (-O3) | 12 to 16.6 (-O2), 13.5 to 16.2 (-O3) | 24.1 to 24.4 | 19.8 to 19.9 |
| `z = x + y`, 1 limb, N = 7 | 16.5 to 21.4 (-O2), 16.4 to 21.3 (-O3) | 11.3 to 15.2 (-O2), 11.7 to 14.1 (-O3) | 23.8 to 24.2 | 21.4 to 21.6 |
| `z = x + y`, 1 limb, N = 13 | 15.6 to 21.8 (-O2), 15.9 to 21.5 (-O3) | 12.9 to 16.1 (-O2), 12 to 15.2 (-O3) | 22.4 to 22.7 | 23.1 to 23.3 |
| `z = x + y`, 1 limb, N = 18 | 12.1 to 16.5 (-O2), 12.2 to 16.8 (-O3) | 15.1 to 17.3 (-O2), 15.6 to 18.7 (-O3) | 25.8 to 30.2 (-O2), 24.9 to 27.5 (-O3) | 22.3 to 22.6 |
| `z = x + y`, 1 limb, N = 80 | 42.2 to 54.9 (-O2), 43.1 to 55.6 (-O3) | 55.8 to 61.5 (-O2), 50.1 to 60.3 (-O3) | 87.3 to 87.7 | 34.4 to 38.7 (-O2), 38.5 to 39.4 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 21.9 to 28.1 (-O2), 21.9 to 27.9 (-O3) | 15.3 to 18.1 (-O2), 17.1 to 20.5 (-O3) | 36.5 to 36.9 (-O2), 32.2 to 36.4 (-O3) | 26.3 to 27.6 (-O2), 27.5 to 27.7 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 15.2 to 19.5 (-O2), 15.2 to 19.3 (-O3) | 17.3 to 18.4 (-O2), 17.4 to 19.5 (-O3) | 44.3 to 44.8 (-O2), 40.2 to 43.4 (-O3) | 34.7 to 37.1 (-O2), 37.3 to 37.8 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 18.5 to 24 (-O2), 18.4 to 23.6 (-O3) | 24.9 to 27.7 (-O2), 24.7 to 28.4 (-O3) | 48.5 to 49.4 | 38.3 to 42.1 (-O2), 42.5 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 24.1 to 33.7 (-O2), 23.6 to 31.8 (-O3) | 30.2 to 35.2 (-O2), 29.6 to 36.5 (-O3) | 63.4 to 64.1 | 51.6 to 54.6 (-O2), 54.9 to 55 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 108 to 149 (-O2), 107 to 137 (-O3) | 125 to 133 (-O2), 125 to 140 (-O3) | 164 to 168 | 128 to 134 |
| `sub`, 1 limb, N = 3 | 15 to 19 (-O2), 14.1 to 18.6 (-O3) | 4.75 to 9.17 (-O2), 6.57 to 7.52 (-O3) | 15.4 to 15.6 (-O2), 9.94 to 9.97 (-O3) | 8.76 to 8.86 |
| `sub`, 1 limb, N = 7 | 14.6 to 19.1 (-O2), 14.6 to 18.8 (-O3) | 5.9 to 7.72 (-O2), 6.75 to 7.99 (-O3) | 16.7 to 16.9 (-O2), 12 to 12.1 (-O3) | 9.64 to 9.76 |
| `sub`, 1 limb, N = 13 | 9.86 to 13.9 (-O2), 10.2 to 13.5 (-O3) | 8.01 to 9.27 (-O2), 8.58 to 10.3 (-O3) | 16.9 to 17 (-O2), 11.9 to 12 (-O3) | 10.2 to 10.4 |
| `sub`, 1 limb, N = 18 | 10.2 to 14 (-O2), 10 to 14.9 (-O3) | 9.31 to 10.2 (-O2), 9.59 to 11.6 (-O3) | 18.2 to 18.3 (-O2), 13.3 to 13.4 (-O3) | 11 to 11.1 |
| `sub`, 1 limb, N = 80 | 30.8 to 39.5 (-O2), 30.2 to 38.4 (-O3) | 39.3 to 43.9 (-O2), 34.6 to 41.6 (-O3) | 30.1 to 30.6 (-O2), 25.2 to 25.3 (-O3) | 22 to 22.1 (-O2), 20.2 to 20.4 (-O3) |
| `sub`, 2 limbs, N = 3 | 20.4 to 25.9 (-O2), 20 to 25.9 (-O3) | 10.9 to 13.7 (-O2), 10.7 to 13.7 (-O3) | 27.4 (-O2), 19.9 to 20 (-O3) | 18.1 to 18.3 |
| `sub`, 2 limbs, N = 7 | 11.6 to 15.8 (-O2), 11.2 to 15.6 (-O3) | 12.5 to 14.9 (-O2), 12.9 to 14.6 (-O3) | 32.4 to 32.6 (-O2), 26.8 (-O3) | 24.2 to 24.4 |
| `sub`, 2 limbs, N = 13 | 17.2 to 23 (-O2), 17.2 to 22 (-O3) | 18.5 to 21.3 (-O2), 18.1 to 21.3 (-O3) | 32.6 to 33 (-O2), 25.7 to 26 (-O3) | 25.3 to 25.5 |
| `sub`, 2 limbs, N = 18 | 22.1 to 30.1 (-O2), 21.4 to 27.4 (-O3) | 23.6 to 26.6 (-O2), 22.6 to 26.3 (-O3) | 41.2 to 41.9 (-O2), 37.3 to 38 (-O3) | 35.3 to 36.1 |
| `sub`, 2 limbs, N = 80 | 85.2 to 116 (-O2), 85.4 to 109 (-O3) | 93.2 to 105 (-O2), 91.1 to 100 (-O3) | 101 to 103 (-O2), 97.7 to 97.8 (-O3) | 96.8 to 97.4 |
| `scale`, 1 limb, N = 3 | 14.6 to 18.5 (-O2), 14.4 to 19.2 (-O3) | 5.09 to 6.34 (-O2), 5.38 to 6.9 (-O3) | 15.7 (-O2), 14.6 to 14.7 (-O3) | 9.55 to 9.63 |
| `scale`, 1 limb, N = 7 | 15.6 to 19.9 (-O2), 15.6 to 19.8 (-O3) | 6.26 to 8.06 (-O2), 6.24 to 7.75 (-O3) | 15.8 to 16.4 | 9.34 to 9.46 |
| `scale`, 1 limb, N = 13 | 12.9 to 18.7 (-O2), 13.3 to 18.6 (-O3) | 7.25 to 9.74 (-O2), 7.47 to 9.46 (-O3) | 16 to 16.5 | 9.58 to 9.69 |
| `scale`, 1 limb, N = 18 | 8.55 to 11.7 (-O2), 9.98 to 14.9 (-O3) | 8.48 to 9.68 (-O2), 8.48 to 10.4 (-O3) | 17.3 to 17.6 | 10 to 10.2 |
| `scale`, 1 limb, N = 80 | 27.3 to 35.8 (-O2), 27.6 to 35.9 (-O3) | 38.5 to 42.5 (-O2), 33.6 to 40.5 (-O3) | 28.9 to 30.2 | 19.2 to 19.3 (-O2), 23.2 to 38.5 (-O3) |
| `scale`, 2 limbs, N = 3 | 15.6 to 21.1 (-O2), 15.6 to 20.9 (-O3) | 6.37 to 9.37 (-O2), 8.49 to 10.2 (-O3) | 19.3 to 19.5 (-O2), 12 (-O3) | 11.1 to 11.2 (-O2), 10.5 to 10.7 (-O3) |
| `scale`, 2 limbs, N = 7 | 9.35 to 12.8 (-O2), 9.47 to 15 (-O3) | 8.69 to 9.82 (-O2), 9.52 to 10.7 (-O3) | 21.8 to 21.9 (-O2), 15.2 (-O3) | 13.7 to 13.8 |
| `scale`, 2 limbs, N = 13 | 8.6 to 12.5 (-O2), 8.82 to 14 (-O3) | 10.8 to 11.6 (-O2), 12.7 to 15.2 (-O3) | 21.9 to 22 (-O2), 14.8 (-O3) | 13.6 to 13.8 |
| `scale`, 2 limbs, N = 18 | 10.2 to 16.1 (-O2), 10 to 13.8 (-O3) | 11.9 to 13.2 (-O2), 14 to 16.5 (-O3) | 24.5 to 24.6 (-O2), 18.1 (-O3) | 15.4 to 15.5 |
| `scale`, 2 limbs, N = 80 | 41.4 to 56.5 (-O2), 41.7 to 54.2 (-O3) | 47.6 to 52.5 (-O2), 51.9 to 61.5 (-O3) | 51.7 to 51.8 (-O2), 47 to 47.1 (-O3) | 42.9 to 43.2 |
| `half`, 1 limb, N = 3 | 15.9 to 21.3 (-O2), 15.9 to 20 (-O3) | 5.8 to 7.88 (-O2), 5.76 to 8.3 (-O3) | 19.5 to 19.7 | 15.9 to 16.1 |
| `half`, 1 limb, N = 7 | 15.2 to 21.3 (-O2), 15.1 to 20.8 (-O3) | 7.48 to 8.23 (-O2), 7.19 to 8.64 (-O3) | 20.8 to 21.6 | 15.7 to 15.8 |
| `half`, 1 limb, N = 13 | 14.3 to 21 (-O2), 15.7 to 21 (-O3) | 9.31 to 10.3 (-O2), 9.58 to 11.5 (-O3) | 19.8 to 19.9 (-O2), 20.7 to 20.8 (-O3) | 15.6 to 15.8 |
| `half`, 1 limb, N = 18 | 14.8 to 20.6 (-O2), 14.6 to 20.9 (-O3) | 10.6 to 12.7 (-O2), 11 to 13.2 (-O3) | 22.3 to 23 | 16.7 to 16.9 |
| `half`, 1 limb, N = 80 | 35.8 to 47.4 (-O2), 36.1 to 46.5 (-O3) | 38.9 to 45.2 (-O2), 42.2 to 50.4 (-O3) | 38.1 to 38.8 | 35.8 to 36.3 |
| `half`, 2 limbs, N = 3 | 16.1 to 21.4 (-O2), 16.1 to 20.4 (-O3) | 8.1 to 8.9 (-O2), 7.83 to 9.41 (-O3) | 25 to 25.1 (-O2), 23.5 to 23.8 (-O3) | 15.8 to 16.1 |
| `half`, 2 limbs, N = 7 | 15.4 to 21.3 (-O2), 15.9 to 20.6 (-O3) | 11 to 12.2 (-O2), 10.4 to 12.5 (-O3) | 27.4 to 28.1 | 18.1 to 18.3 |
| `half`, 2 limbs, N = 13 | 15.2 to 21.6 (-O2), 15.5 to 20.4 (-O3) | 14.1 to 15.9 (-O2), 14.5 to 17.4 (-O3) | 25.6 to 26.5 | 18.6 to 18.9 |
| `half`, 2 limbs, N = 18 | 14.2 to 21.1 (-O2), 13.9 to 19 (-O3) | 18 to 19 (-O2), 17.7 to 20.6 (-O3) | 30.5 to 30.9 | 21.4 to 21.6 |
| `half`, 2 limbs, N = 80 | 50.8 to 69.4 (-O2), 51.1 to 65 (-O3) | 59 to 62.9 (-O2), 59.4 to 66.6 (-O3) | 57.2 to 59.4 | 52.7 to 53.5 |
| the constructor, 1 limb, N = 3 | 15 to 19.5 (-O2), 13.9 to 18.5 (-O3) | 7.1 to 9.59 (-O2), 5.21 to 7.58 (-O3) | 17.7 to 18.7 (-O2), 19.1 to 19.9 (-O3) | 25.9 to 26.1 |
| the constructor, 1 limb, N = 7 | 21.8 to 22 (-O2), 20.9 to 21.3 (-O3) | 9.75 to 11.4 (-O2), 11.2 to 13.3 (-O3) | 21 to 21.1 (-O2), 23.1 to 23.2 (-O3) | 28.1 to 29.3 (-O2), 28.1 to 30.3 (-O3) |
| the constructor, 1 limb, N = 13 | 25.3 to 33.9 (-O2), 24.7 to 33.4 (-O3) | 21.1 to 23.1 (-O2), 22.5 to 27 (-O3) | 26.6 to 26.7 (-O2), 28.8 to 28.9 (-O3) | 33 to 33.9 |
| the constructor, 1 limb, N = 18 | 21 to 27.2 (-O2), 25.8 to 35.5 (-O3) | 26.6 to 31.4 (-O2), 31.6 to 37.9 (-O3) | 31.1 to 31.8 (-O2), 34.6 to 34.9 (-O3) | 24.8 to 24.9 (-O2), 34.9 to 36 (-O3) |
| the constructor, 1 limb, N = 80 | 73.1 to 96.9 (-O2), 78.7 to 102 (-O3) | 236 to 264 (-O2), 252 to 300 (-O3) | 150 | 71.7 to 72.5 |
| the constructor, 2 limbs, N = 3 | 13.6 to 18.2 (-O2), 14.2 to 18.3 (-O3) | 6.91 to 8.93 (-O2), 7.29 to 8.77 (-O3) | 17.5 to 17.8 (-O2), 21.3 to 22.6 (-O3) | 11.9 to 17.8 (-O2), 17.3 to 17.4 (-O3) |
| the constructor, 2 limbs, N = 7 | 19.8 to 27.3 (-O2), 20.8 to 26.5 (-O3) | 14.7 to 15.8 (-O2), 15.1 to 18 (-O3) | 22 (-O2), 25.1 to 25.7 (-O3) | 15.5 to 19 (-O2), 18.7 to 18.8 (-O3) |
| the constructor, 2 limbs, N = 13 | 24 to 31.7 (-O2), 24 to 31.6 (-O3) | 32.1 to 33.8 (-O2), 30.7 to 34.4 (-O3) | 42.5 to 42.8 (-O2), 31.1 to 31.2 (-O3) | 23.1 (-O2), 23.5 to 25 (-O3) |
| the constructor, 2 limbs, N = 18 | 23.3 to 31.4 (-O2), 23.4 to 29.8 (-O3) | 48 to 54.6 (-O2), 41.5 to 51.4 (-O3) | 51.9 to 52.2 (-O2), 35.5 to 35.8 (-O3) | 34.4 to 36.5 (-O2), 36.1 to 36.3 (-O3) |
| the constructor, 2 limbs, N = 80 | 99.6 to 135 (-O2), 96.2 to 122 (-O3) | 347 to 365 (-O2), 324 to 381 (-O3) | 185 to 187 (-O2), 165 to 167 (-O3) | 100 to 105 |

| Short ball vectors, every size in one unit, a dependent chain: the check, ns per operation (with minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | -0.51 to 0.16 (-O2), -0.72 to -0.05 (-O3) | -1.78 to -1.57 (-O2), -1.13 to -0.127 (-O3) | 2.74 to 2.96 (-O2), 2.28 to 2.6 (-O3) | -0.23 to -0.153 (-O2), -0.3 to -0.156 (-O3) |
| `add(x, y, z)`, 1 limb, N = 7 | -1.34 to 1.36 (-O2), -0.47 to 0.01 (-O3) | -0.734 to 0.205 (-O2), 0.042 to 0.795 (-O3) | 2.19 to 2.22 (-O2), 1.64 to 1.93 (-O3) | 0.673 to 0.753 (-O2), 0.628 to 0.786 (-O3) |
| `add(x, y, z)`, 1 limb, N = 13 | -7.02 to -5.39 (-O2), -6.58 to -5.13 (-O3) | -0.043 to 0.629 (-O2), 0.43 to 1.44 (-O3) | 2.18 to 2.64 (-O2), 2.3 to 2.36 (-O3) | 1.4 to 1.5 (-O2), -0.66 to 1.4 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | 0 to 0.86 (-O2), -0.084 to 0.331 (-O3) | -0.02 to 0.36 (-O2), 0.52 to 0.994 (-O3) | 1.49 to 1.52 (-O2), 1.65 to 1.99 (-O3) | 1.76 to 1.84 (-O2), 1.69 to 1.8 (-O3) |
| `add(x, y, z)`, 1 limb, N = 80 | -0.17 to 0.67 (-O2), -0.32 to 0.05 (-O3) | -0.05 to 0.52 (-O2), -0.97 to 1.29 (-O3) | 3.3 to 5.04 (-O2), 3.75 to 4.97 (-O3) | 3.27 to 3.34 (-O2), 2.67 to 2.92 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | -0.93 to 2.47 (-O2), 0 to 0.05 (-O3) | 0.06 to 1.01 (-O2), 0.04 to 1.21 (-O3) | 2.6 to 2.83 (-O2), 2.58 to 2.9 (-O3) | 1.76 to 1.94 (-O2), 1.67 to 2.04 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | -0.97 to 1.07 (-O2), -0.26 to 0.17 (-O3) | -0.01 to 1.13 (-O2), 0.02 to 1.14 (-O3) | 2.27 to 2.34 (-O2), 2.07 to 2.62 (-O3) | 1.7 to 1.9 (-O2), 1.48 to 1.65 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | -1.47 to 0.5 (-O2), -0.22 to 0.17 (-O3) | -0.75 to 0.94 (-O2), -2.36 to 0.57 (-O3) | 2.18 to 2.39 (-O2), 2.37 to 2.81 (-O3) | 2.04 to 2.36 (-O2), 2.43 to 2.51 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -0.42 to 2.15 (-O2), 0 to 0.5 (-O3) | 1.54 to 3.14 (-O2), -0.24 to 0.93 (-O3) | 3.37 to 3.89 (-O2), 4.03 to 4.37 (-O3) | 3.52 to 4.09 (-O2), 3.4 to 4.58 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -0.22 to 6.37 (-O2), -0.23 to 5.84 (-O3) | -4.9 to 0.02 (-O2), -9.5 to 0.02 (-O3) | 4.53 to 5.61 (-O2), 3.22 to 4.86 (-O3) | 4.94 to 5.62 (-O2), 4.62 to 5.28 (-O3) |
| `z = x + y`, 1 limb, N = 3 | -0.22 to 0.55 (-O2), 0.46 to 1.56 (-O3) | -1.26 to 1.13 (-O2), -1.46 to 0.96 (-O3) | 0.05 to 0.31 (-O2), -0.05 to 0.34 (-O3) | 0.06 to 0.2 (-O2), 0.06 to 0.21 (-O3) |
| `z = x + y`, 1 limb, N = 7 | -1.44 to 0.31 (-O2), -0.71 to 0.23 (-O3) | -0.24 to 0.94 (-O2), -3.55 to -1.5 (-O3) | -0.26 to -0.04 (-O2), -0.35 to 0 (-O3) | -0.16 to -0.01 (-O2), -0.3 to 0 (-O3) |
| `z = x + y`, 1 limb, N = 13 | -1.95 to 1 (-O2), -1.17 to 0.61 (-O3) | -0.17 to 0.02 (-O2), -1.23 to 0.83 (-O3) | -0.15 to 0.15 (-O2), -0.06 to 0.17 (-O3) | -0.11 to 0.02 (-O2), -0.22 to 0.11 (-O3) |
| `z = x + y`, 1 limb, N = 18 | -0.6 to 0.02 (-O2), -0.04 to 0.37 (-O3) | -0.61 to 0.03 (-O2), 0.23 to 0.88 (-O3) | -3.77 to 0.5 (-O2), -4.47 to -0.44 (-O3) | 0.18 to 0.29 (-O2), 0.01 to 0.4 (-O3) |
| `z = x + y`, 1 limb, N = 80 | -3.06 to 1.73 (-O2), -0.72 to -0.33 (-O3) | -0.23 to 0.43 (-O2), 0.05 to 3.35 (-O3) | 0.38 to 1.43 (-O2), 1.31 to 2.69 (-O3) | -3.86 to 0.67 (-O2), -0.37 to 3.81 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -2.09 to 0.08 (-O2), -0.22 to -0.16 (-O3) | -1.01 to 0.02 (-O2), -0.13 to 0.11 (-O3) | -0.1 to 0.57 (-O2), -5.07 to -0.34 (-O3) | -0.42 to 0.6 (-O2), 0.5 to 2.64 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | -1.35 to 0 (-O2), -0.13 to 0 (-O3) | -1.06 to 1.73 (-O2), -1.36 to 1.78 (-O3) | -0.22 to 0.18 (-O2), -5.87 to -0.87 (-O3) | -1.93 to 0.15 (-O2), 0.77 to 3.1 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | -0.69 to 1.81 (-O2), -0.19 to 0.26 (-O3) | 0.16 to 1.5 (-O2), -0.46 to 1.84 (-O3) | 0.67 to 1.23 (-O2), 0.09 to 1.38 (-O3) | -3.71 to -0.29 (-O2), -1.8 to 3.39 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -0.86 to 1.57 (-O2), -0.52 to 0.29 (-O3) | -0.17 to 0.53 (-O2), -1.57 to 0.16 (-O3) | 0.37 to 0.62 (-O2), -0.74 to 0.58 (-O3) | -3.09 to -0.34 (-O2), -0.08 to 3.2 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 0.3 to 10.9 (-O2), -1.3 to 6.7 (-O3) | -4.2 to 4 (-O2), -10 to 0.2 (-O3) | 0.7 to 2.7 (-O2), -2.2 to 2.6 (-O3) | -1.6 to 3.1 (-O2), 0.5 to 6.7 (-O3) |
| `sub`, 1 limb, N = 3 | 0.29 to 1.48 (-O2), -0.08 to 0.81 (-O3) | -2.44 to 1.12 (-O2), -2.74 to 0.247 (-O3) | 2.63 to 2.83 (-O2), 3.2 to 3.26 (-O3) | -0.225 to -0.131 (-O2), -0.27 to -0.148 (-O3) |
| `sub`, 1 limb, N = 7 | -0.43 to 0.55 (-O2), -1.18 to 0.03 (-O3) | -0.662 to 0.336 (-O2), -0.422 to 0.429 (-O3) | 2.17 to 2.36 (-O2), 1.09 to 1.3 (-O3) | 0.691 to 0.75 (-O2), 0.635 to 0.75 (-O3) |
| `sub`, 1 limb, N = 13 | -4.82 to -4.35 (-O2), -5.19 to -4.36 (-O3) | -0.026 to 0.038 (-O2), 0.53 to 1.41 (-O3) | 2.39 to 2.48 (-O2), 1.5 to 1.6 (-O3) | 1.42 to 1.51 (-O2), -0.7 to 1.36 (-O3) |
| `sub`, 1 limb, N = 18 | -0.01 to 1.26 (-O2), -0.08 to 0.3 (-O3) | -0.12 to 0.117 (-O2), 0.54 to 1.01 (-O3) | 1.51 to 1.58 (-O2), 1.68 to 1.89 (-O3) | 1.8 to 1.83 (-O2), 1.73 to 1.85 (-O3) |
| `sub`, 1 limb, N = 80 | -2.74 to 0.02 (-O2), -1.17 to -0.12 (-O3) | 0.79 to 1.71 (-O2), 0.04 to 1.7 (-O3) | 3.49 to 3.83 (-O2), 0.7 to 1.17 (-O3) | 3.17 to 3.44 (-O2), 2.67 to 2.92 (-O3) |
| `sub`, 2 limbs, N = 3 | -1.53 to 0.33 (-O2), -0.35 to -0.26 (-O3) | -0.27 to 1.14 (-O2), -1.34 to -0.89 (-O3) | 2.59 to 2.79 (-O2), 1.77 to 2.06 (-O3) | 2.11 to 2.2 (-O2), 1.96 to 2.25 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.11 to 0.83 (-O2), -0.32 to 0.23 (-O3) | -0.91 to 0.04 (-O2), -1.16 to 0.56 (-O3) | 1.84 to 1.99 (-O2), 0.55 to 0.81 (-O3) | 2.39 to 2.56 (-O2), 2.2 to 2.48 (-O3) |
| `sub`, 2 limbs, N = 13 | -0.19 to 2.06 (-O2), -0.1 to 0.18 (-O3) | -0.14 to 0.81 (-O2), -0.18 to 1.06 (-O3) | 2.13 to 3.01 (-O2), -0.53 to -0.05 (-O3) | 2.41 to 2.7 (-O2), 2.78 to 2.85 (-O3) |
| `sub`, 2 limbs, N = 18 | 0.15 to 2.92 (-O2), -0.12 to 0.14 (-O3) | -0.29 to 0.74 (-O2), -0.65 to 1.07 (-O3) | 3.28 to 3.35 (-O2), 3.29 to 3.73 (-O3) | 4.03 to 4.8 (-O2), 4.11 to 4.92 (-O3) |
| `sub`, 2 limbs, N = 80 | 0.08 to 7.8 (-O2), -0.26 to 6.2 (-O3) | -3.4 to 1.72 (-O2), -8.8 to 1.28 (-O3) | 4.13 to 5.51 (-O2), 3.35 to 4.98 (-O3) | 5.25 to 5.86 (-O2), 4.63 to 5.64 (-O3) |
| `scale`, 1 limb, N = 3 | 5.42 to 6.16 (-O2), 6.25 to 6.8 (-O3) | -1.25 to -0.569 (-O2), -2.37 to 1.69 (-O3) | 2.76 to 2.78 (-O2), 2.16 to 2.43 (-O3) | 2.6 to 2.67 |
| `scale`, 1 limb, N = 7 | 6.31 to 8.28 (-O2), 6.67 to 7.27 (-O3) | -0.144 to 0.299 (-O2), -0.846 to 0.759 (-O3) | 2.64 to 2.77 (-O2), 2.24 to 2.53 (-O3) | 2.35 to 2.38 (-O2), 2.27 to 2.46 (-O3) |
| `scale`, 1 limb, N = 13 | 4.32 to 6.97 (-O2), 4.66 to 7.45 (-O3) | -0.202 to 0.049 (-O2), 0.273 to 1.73 (-O3) | 2.75 to 2.8 (-O2), 2.52 to 2.93 (-O3) | -1.51 to 2.59 (-O2), -1.74 to 2.54 (-O3) |
| `scale`, 1 limb, N = 18 | -0.496 to 0.69 (-O2), 0.672 to 2.8 (-O3) | 0.073 to 0.188 (-O2), -0.291 to 0.601 (-O3) | 2.41 to 2.52 (-O2), 2.71 to 3.1 (-O3) | 2.85 to 2.88 (-O2), 2.77 to 3.08 (-O3) |
| `scale`, 1 limb, N = 80 | -2.18 to 1.12 (-O2), -0.76 to -0.2 (-O3) | 0.23 to 0.41 (-O2), 0.57 to 2.05 (-O3) | 3.63 to 3.8 (-O2), 3.07 to 3.89 (-O3) | 3.41 to 3.56 (-O2), 1.8 to 17.3 (-O3) |
| `scale`, 2 limbs, N = 3 | 6.54 to 10 (-O2), 6.88 to 8.14 (-O3) | -0.503 to 1.76 (-O2), 0.598 to 1.57 (-O3) | 2.49 to 2.65 (-O2), -4.05 to -3.83 (-O3) | 2.65 to 2.79 (-O2), 2.03 to 2.18 (-O3) |
| `scale`, 2 limbs, N = 7 | 0.612 to 2.31 (-O2), 0.718 to 3.05 (-O3) | 0.384 to 0.724 (-O2), -0.41 to 1.24 (-O3) | 2.74 to 2.89 (-O2), -4.08 to -3.76 (-O3) | 4.18 to 4.24 (-O2), 3.99 to 4.18 (-O3) |
| `scale`, 2 limbs, N = 13 | -0.227 to 0.124 (-O2), -0.472 to 0.41 (-O3) | 0.11 to 1.39 (-O2), -0.42 to 0.82 (-O3) | 2.63 to 2.74 (-O2), -4.52 to -4.21 (-O3) | 3.11 to 3.21 (-O2), 2.87 to 3.08 (-O3) |
| `scale`, 2 limbs, N = 18 | -0.03 to 3.8 (-O2), -1.38 to 0.23 (-O3) | -0.65 to 0.09 (-O2), -0.89 to 0.01 (-O3) | 2.38 to 2.41 (-O2), -5.12 to -3.62 (-O3) | 1.7 to 1.82 (-O2), 1.69 to 1.83 (-O3) |
| `scale`, 2 limbs, N = 80 | 0.56 to 5.01 (-O2), 0.05 to 3.12 (-O3) | -1.48 to 1.94 (-O2), -1.63 to 1.17 (-O3) | 3.15 to 3.59 (-O2), -0.78 to -0.22 (-O3) | 1.1 to 1.36 (-O2), 0.99 to 1.52 (-O3) |
| `half`, 1 limb, N = 3 | -0.18 to 1.63 (-O2), -0.73 to 1.01 (-O3) | 0.443 to 1.61 (-O2), 0.161 to 1.04 (-O3) | 2.37 to 2.49 (-O2), 4.3 to 4.56 (-O3) | 1.04 to 1.13 (-O2), 0.88 to 1.18 (-O3) |
| `half`, 1 limb, N = 7 | -0.08 to 0.57 (-O2), -0.44 to -0.01 (-O3) | 0.477 to 1.08 (-O2), -0.015 to 0.823 (-O3) | 2.46 to 2.49 (-O2), 4.17 to 4.54 (-O3) | 0.34 to 0.49 (-O2), 0.14 to 0.49 (-O3) |
| `half`, 1 limb, N = 13 | -0.88 to -0.09 (-O2), -0.45 to 0.62 (-O3) | 0.438 to 0.942 (-O2), 0.718 to 1.32 (-O3) | 2.69 to 2.76 (-O2), 4.35 to 4.69 (-O3) | -0.17 to -0.02 (-O2), -0.22 to 0.43 (-O3) |
| `half`, 1 limb, N = 18 | -0.9 to 0.42 (-O2), -0.31 to 0.35 (-O3) | 0.25 to 1.26 (-O2), 0.37 to 0.78 (-O3) | 2.92 to 3.02 (-O2), 3.95 to 4.28 (-O3) | -1.07 to -0.94 (-O2), -1.39 to -0.98 (-O3) |
| `half`, 1 limb, N = 80 | -1.17 to 1.07 (-O2), -0.07 to 0.24 (-O3) | -0.98 to 0.65 (-O2), -0.61 to 3.23 (-O3) | 3.39 to 3.73 (-O2), 4.28 to 5.16 (-O3) | 5.43 to 5.79 (-O2), 4.87 to 5.24 (-O3) |
| `half`, 2 limbs, N = 3 | 0.95 to 3 (-O2), -0.31 to 1.74 (-O3) | 1.98 to 2.26 (-O2), -0.255 to 1.79 (-O3) | 1.94 to 1.97 (-O2), 0.93 to 1.65 (-O3) | 0.55 to 0.76 (-O2), 0.36 to 0.68 (-O3) |
| `half`, 2 limbs, N = 7 | -0.54 to 2.23 (-O2), -0.5 to 0.63 (-O3) | 1.91 to 2.57 (-O2), 0.67 to 2.18 (-O3) | 1.2 to 1.36 (-O2), 0.86 to 1.14 (-O3) | 2.06 to 2.28 (-O2), 1.76 to 2.12 (-O3) |
| `half`, 2 limbs, N = 13 | -0.26 to 0.94 (-O2), -0.98 to 0.33 (-O3) | 0.53 to 1.16 (-O2), 0.65 to 1.98 (-O3) | 1.24 to 1.47 (-O2), 0.92 to 1.42 (-O3) | 2.56 to 2.68 (-O2), 2.28 to 2.73 (-O3) |
| `half`, 2 limbs, N = 18 | 0.19 to 3.14 (-O2), -1 to 0.87 (-O3) | 0.04 to 1.86 (-O2), 1.44 to 2.44 (-O3) | 0.76 to 0.96 (-O2), 0.7 to 1.47 (-O3) | 2.49 to 2.71 (-O2), 2.42 to 2.85 (-O3) |
| `half`, 2 limbs, N = 80 | 0.13 to 8.87 (-O2), 0.4 to 4.78 (-O3) | 1.12 to 2.91 (-O2), -14.3 to -4.82 (-O3) | 3.03 to 3.46 (-O2), 2.7 to 3.34 (-O3) | 5.24 to 5.81 (-O2), 5.16 to 5.49 (-O3) |
| the constructor, 1 limb, N = 3 | 5.08 to 6.25 (-O2), 4.02 to 6.2 (-O3) | -1.72 to -0.079 (-O2), -3.71 to -1.05 (-O3) | 2.68 to 3.58 (-O2), 4.16 to 5.14 (-O3) | 19.6 to 19.9 |
| the constructor, 1 limb, N = 7 | -0.69 to 1.98 (-O2), -2.26 to 0.65 (-O3) | -8.15 to -5.69 (-O2), 4.26 to 4.83 (-O3) | 4.36 to 4.54 (-O2), 7.9 to 8.27 (-O3) | -0.17 to 1.15 (-O2), -1.39 to 2.03 (-O3) |
| the constructor, 1 limb, N = 13 | -2.07 to 0.05 (-O2), -1.52 to -0.28 (-O3) | -0.34 to 0.15 (-O2), 14.7 to 17 (-O3) | 2.75 to 2.87 (-O2), 8.58 to 8.86 (-O3) | -0.14 to 0.23 (-O2), 0.04 to 0.59 (-O3) |
| the constructor, 1 limb, N = 18 | -2.88 to -0.15 (-O2), -2.55 to -0.02 (-O3) | -1.72 to 0.26 (-O2), 2.24 to 3.28 (-O3) | 2.32 to 2.98 (-O2), 5.53 to 6.14 (-O3) | 0.88 to 1.15 (-O2), 0.43 to 2.04 (-O3) |
| the constructor, 1 limb, N = 80 | -1.91 to 0.82 (-O2), -0.1 to 0.44 (-O3) | -3.9 to 0 (-O2), 1.5 to 11.6 (-O3) | 1.9 to 2.2 (-O2), -2 to 2 (-O3) | 2.92 to 2.97 (-O2), 1.99 to 6.4 (-O3) |
| the constructor, 2 limbs, N = 3 | 2.76 to 5.53 (-O2), 4.27 to 5.36 (-O3) | -0.718 to 0.572 (-O2), -0.946 to -0.105 (-O3) | 2.7 to 2.97 (-O2), 5.76 to 7.21 (-O3) | 3.6 to 9.48 (-O2), 9.05 to 9.17 (-O3) |
| the constructor, 2 limbs, N = 7 | -1.06 to 0.96 (-O2), -0.51 to 0.55 (-O3) | -0.87 to 0.28 (-O2), 6.6 to 8.06 (-O3) | 3.78 to 3.87 (-O2), 9.73 to 10.6 (-O3) | -2.03 to 3.1 (-O2), 1.16 to 2.42 (-O3) |
| the constructor, 2 limbs, N = 13 | -1.43 to -0.52 (-O2), 0.86 to 4.1 (-O3) | -2.02 to 1.49 (-O2), 19.3 to 20.5 (-O3) | 4.46 to 4.81 (-O2), 8.32 to 8.91 (-O3) | 0.05 to 0.41 (-O2), 0.07 to 2.16 (-O3) |
| the constructor, 2 limbs, N = 18 | -0.5 to 0.89 (-O2), -0.43 to -0.34 (-O3) | 0.15 to 1.91 (-O2), -3.02 to 1.56 (-O3) | -0.54 to -0.17 (-O2), -6.2 to -5.21 (-O3) | 0.41 to 2.26 (-O2), 1.67 to 5.66 (-O3) |
| the constructor, 2 limbs, N = 80 | 3.67 to 19.9 (-O2), 0.13 to 8.65 (-O3) | -0.7 to 15.7 (-O2), -21.8 to 0.1 (-O3) | -4 to -1 (-O2), 11 to 13.8 (-O3) | -4 to 5.22 (-O2), 3.7 to 9.38 (-O3) |

| Short ball vectors, every size in one unit, a dependent chain: the check with its report cold, ns per operation (minus without) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | -1.39 to 0.16 (-O2), -1.46 to 0.45 (-O3) | -0.917 to -0.751 (-O2), -2.13 to 1.39 (-O3) | 2.56 to 3.85 (-O2), 2.16 to 2.53 (-O3) | -0.158 to -0.088 (-O2), -0.169 to 2.65 (-O3) |
| `add(x, y, z)`, 1 limb, N = 7 | -0.62 to 0.02 (-O2), -1.41 to 1.55 (-O3) | -0.557 to 0.375 (-O2), -1.81 to 0.771 (-O3) | 2.26 to 2.35 (-O2), 1.75 to 2.03 (-O3) | 0.727 to 0.745 (-O2), 0.644 to 0.737 (-O3) |
| `add(x, y, z)`, 1 limb, N = 13 | -2.08 to 0.01 (-O2), -0.9 to 0.23 (-O3) | 0.17 to 0.938 (-O2), -1.73 to 0.22 (-O3) | 2.13 to 2.33 (-O2), 2.02 to 2.4 (-O3) | 1.31 to 1.44 (-O2), -0.88 to 1.32 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | -0.991 to -0.215 (-O2), -3.55 to 0.321 (-O3) | -0.882 to 0.69 (-O2), -2.67 to -0.143 (-O3) | 1.56 to 1.59 (-O2), 1.66 to 1.89 (-O3) | 2.01 to 2.22 (-O2), 1.92 to 2.18 (-O3) |
| `add(x, y, z)`, 1 limb, N = 80 | -1.31 to 0.13 (-O2), -2.87 to 1.15 (-O3) | 0.35 to 3.68 (-O2), -8.09 to 1.2 (-O3) | 3.77 to 4.04 (-O2), 3.74 to 4.35 (-O3) | 3.04 to 3.1 (-O2), 3.32 to 3.59 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 3 | -1.46 to 0.02 (-O2), -1.32 to -0.1 (-O3) | -0.38 to 0.98 (-O2), -3.06 to 0.61 (-O3) | 2.45 to 2.74 (-O2), 2.28 to 2.72 (-O3) | 1.98 to 2.03 (-O2), 1.84 to 4.73 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 7 | -1 to 0.83 (-O2), -1.46 to 0.34 (-O3) | 0.02 to 1.91 (-O2), -1.76 to 1.88 (-O3) | 2.24 to 2.68 (-O2), 1.66 to 2.25 (-O3) | 1.71 to 1.75 (-O2), 1.64 to 1.85 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 13 | -0.91 to 0.09 (-O2), -0.09 to 0.72 (-O3) | -1.18 to 3.04 (-O2), -4.74 to 0.29 (-O3) | 1.91 to 2.31 (-O2), 2.55 to 2.76 (-O3) | 2.17 to 2.35 (-O2), 2.3 to 2.54 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 18 | -0.6 to -0.02 (-O2), -1.54 to 1.71 (-O3) | -0.13 to 3.16 (-O2), -4.93 to 0.36 (-O3) | 3.14 to 4.21 (-O2), 4.11 to 5.45 (-O3) | 4.04 to 4.19 (-O2), 3.73 to 4.8 (-O3) |
| `add(x, y, z)`, 2 limbs, N = 80 | -0.49 to 6.27 (-O2), -1.34 to 2.84 (-O3) | 0.27 to 4.15 (-O2), -19.9 to -0.73 (-O3) | 3.71 to 4.32 (-O2), 2.81 to 4.55 (-O3) | 4.95 to 5.42 (-O2), 4.34 to 5.27 (-O3) |
| `z = x + y`, 1 limb, N = 3 | -0.47 to 0.34 (-O2), -0.79 to 2.57 (-O3) | -0.5 to 0.23 (-O2), -4.25 to -0.44 (-O3) | -0.28 to 3.02 (-O2), -0.2 to 0.57 (-O3) | 0.14 to 0.2 (-O2), 0.05 to 0.2 (-O3) |
| `z = x + y`, 1 limb, N = 7 | -0.31 to 0 (-O2), -1.33 to 1.66 (-O3) | 1.25 to 1.77 (-O2), -4.54 to -0.34 (-O3) | -0.11 to 13.9 (-O2), -0.41 to 0.17 (-O3) | -0.17 to -0.15 (-O2), -0.37 to -0.15 (-O3) |
| `z = x + y`, 1 limb, N = 13 | -1 to 0.7 (-O2), -2.04 to 0.72 (-O3) | -0.75 to 0.43 (-O2), -3.83 to 1.92 (-O3) | -0.05 to 0.61 (-O2), -0.18 to 0.04 (-O3) | 0.1 to 0.22 (-O2), -0.02 to 0.17 (-O3) |
| `z = x + y`, 1 limb, N = 18 | -1.02 to 0.62 (-O2), -1.88 to 0.26 (-O3) | -1.36 to 0.97 (-O2), -3.78 to 0.54 (-O3) | -0.61 to 0.41 (-O2), -2.18 to 1.14 (-O3) | 0.22 to 0.42 (-O2), 0.13 to 0.33 (-O3) |
| `z = x + y`, 1 limb, N = 80 | -2.7 to 1.64 (-O2), -2.99 to 2.69 (-O3) | 0.12 to 5.36 (-O2), -8.45 to 2.43 (-O3) | 0.98 to 2.38 (-O2), 5.11 to 6.09 (-O3) | -2.58 to -0.18 (-O2), 0.41 to 3.79 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | -1.86 to 0.04 (-O2), -1.95 to 0.02 (-O3) | -0.12 to 1.66 (-O2), -4 to -0.07 (-O3) | 0.29 to 3.62 (-O2), -0.68 to 0.19 (-O3) | 0.36 to 0.81 (-O2), 1.04 to 10.8 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | -1.13 to -0.01 (-O2), 0.09 to 0.79 (-O3) | -1.14 to 2.26 (-O2), -3.1 to 1.69 (-O3) | -0.76 to 3.84 (-O2), -1.84 to 4.82 (-O3) | 0.3 to 0.83 (-O2), 0.48 to 3.04 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 0.05 to 1.85 (-O2), -0.1 to 1.03 (-O3) | -0.9 to 2.81 (-O2), -3.32 to 2.5 (-O3) | 1.04 to 1.19 (-O2), 0.52 to 1.44 (-O3) | -0.3 to 0.37 (-O2), -1.85 to 3.29 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | -0.62 to 1.55 (-O2), -3.19 to 1.07 (-O3) | -2.38 to 1.42 (-O2), -7.52 to 0.59 (-O3) | 0.63 to 0.83 (-O2), 0.47 to 1.12 (-O3) | -0.22 to 0.21 (-O2), -0.27 to 3.52 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | -1.4 to 4.4 (-O2), -1.4 to 4 (-O3) | -0.2 to 4.9 (-O2), -22.5 to -0.3 (-O3) | 0.7 to 1.1 (-O2), -1.1 to 1.6 (-O3) | -1.3 to 7 (-O2), 2.1 to 5.4 (-O3) |
| `sub`, 1 limb, N = 3 | -0.76 to -0.01 (-O2), -1.35 to 1.62 (-O3) | -1.07 to -0.204 (-O2), -1.68 to -0.01 (-O3) | 2.35 to 4.1 (-O2), 2.32 to 2.36 (-O3) | -0.17 to -0.106 (-O2), -0.184 to 2.66 (-O3) |
| `sub`, 1 limb, N = 7 | -0.07 to 0.78 (-O2), -1.29 to 1.31 (-O3) | 0.022 to 0.545 (-O2), -2.87 to 2.43 (-O3) | 2.26 to 2.27 (-O2), 0.97 to 1.18 (-O3) | 0.715 to 0.748 (-O2), 0.679 to 0.741 (-O3) |
| `sub`, 1 limb, N = 13 | -0.43 to -0.18 (-O2), -1.36 to -0.53 (-O3) | -0.206 to 0.335 (-O2), -1.68 to 0.72 (-O3) | 2.3 to 2.45 (-O2), 1.34 to 1.54 (-O3) | 1.29 to 1.47 (-O2), -0.84 to 1.32 (-O3) |
| `sub`, 1 limb, N = 18 | -0.3 to 1.36 (-O2), -2.05 to 1.79 (-O3) | -0.971 to 0.41 (-O2), -2.86 to 0 (-O3) | 1.62 to 1.66 (-O2), 1.55 to 1.69 (-O3) | 2.02 to 2.17 (-O2), 2.01 to 2.21 (-O3) |
| `sub`, 1 limb, N = 80 | -3 to -0.14 (-O2), -2.54 to 1.59 (-O3) | 0.6 to 4.25 (-O2), -6.68 to 1.55 (-O3) | 3.81 to 4.17 (-O2), 1.23 to 1.71 (-O3) | 3.07 to 3.14 (-O2), 3.37 to 3.55 (-O3) |
| `sub`, 2 limbs, N = 3 | -1.51 to 0.27 (-O2), -2.27 to -0.13 (-O3) | -0.3 to 1.28 (-O2), -3.83 to 0.4 (-O3) | 2.24 to 2.58 (-O2), 0.83 to 1.07 (-O3) | 2.26 to 2.33 (-O2), 2.13 to 4.5 (-O3) |
| `sub`, 2 limbs, N = 7 | -0.04 to 0.69 (-O2), -0.69 to 0.59 (-O3) | -0.92 to 1.87 (-O2), -3.19 to 0.67 (-O3) | 1.83 to 2.35 (-O2), 0.61 to 0.79 (-O3) | 2.72 to 2.76 (-O2), 2.53 to 2.7 (-O3) |
| `sub`, 2 limbs, N = 13 | -0.22 to 1.25 (-O2), -1.02 to 0.67 (-O3) | -0.27 to 2.17 (-O2), -3.51 to 1.21 (-O3) | 2.11 to 2.62 (-O2), -1.01 to -0.59 (-O3) | 2.74 to 2.85 (-O2), 2.74 to 3 (-O3) |
| `sub`, 2 limbs, N = 18 | -0.07 to 1.92 (-O2), -1.08 to 1.75 (-O3) | -0.28 to 2.32 (-O2), -4.17 to 0.68 (-O3) | 3.11 to 4.13 (-O2), 3.27 to 3.72 (-O3) | 4.76 to 5 (-O2), 4.54 to 5.38 (-O3) |
| `sub`, 2 limbs, N = 80 | -3.6 to 0.24 (-O2), -5.21 to 4.26 (-O3) | 3.2 to 7.65 (-O2), -15.8 to -0.11 (-O3) | 3.33 to 4.23 (-O2), 2.85 to 4.3 (-O3) | 5.57 to 5.86 (-O2), 4.43 to 5.31 (-O3) |
| `scale`, 1 limb, N = 3 | 6.49 to 7.47 (-O2), 5.03 to 7.87 (-O3) | 0.032 to 0.806 (-O2), -0.887 to -0.254 (-O3) | 2.62 to 4.12 (-O2), 2.11 to 2.41 (-O3) | 2.44 to 2.46 (-O2), 2.41 to 4.92 (-O3) |
| `scale`, 1 limb, N = 7 | 5.69 to 7.27 (-O2), 5.54 to 6.85 (-O3) | 0.217 to 0.782 (-O2), -1.3 to 2.18 (-O3) | 2.48 to 2.54 (-O2), 2.18 to 2.37 (-O3) | 2.37 to 2.42 (-O2), 2.3 to 2.4 (-O3) |
| `scale`, 1 limb, N = 13 | 5.86 to 6.67 (-O2), 5.81 to 7.06 (-O3) | -0.921 to 0.116 (-O2), -1.41 to 2.17 (-O3) | 2.67 to 2.76 (-O2), 2.55 to 2.87 (-O3) | -1.63 to 2.62 (-O2), -1.86 to 2.47 (-O3) |
| `scale`, 1 limb, N = 18 | -0.027 to 0.01 (-O2), -0.93 to 1.28 (-O3) | 0.124 to 0.516 (-O2), -2.53 to 0.921 (-O3) | 2.34 to 2.38 (-O2), 2.68 to 2.87 (-O3) | 2.65 to 2.69 (-O2), 2.58 to 2.77 (-O3) |
| `scale`, 1 limb, N = 80 | -2.15 to 1.04 (-O2), -2.29 to 0.75 (-O3) | 0.14 to 3.96 (-O2), -6.06 to 1.36 (-O3) | 3.79 to 3.94 (-O2), 3.13 to 3.93 (-O3) | 3.38 to 3.53 (-O2), 1.51 to 2.86 (-O3) |
| `scale`, 2 limbs, N = 3 | 6.81 to 10 (-O2), 6.28 to 7.47 (-O3) | 0.022 to 0.738 (-O2), -2.43 to 0.124 (-O3) | 2.61 to 2.64 (-O2), -5.73 to -5.55 (-O3) | 2.84 to 2.9 (-O2), 2.87 to 7.45 (-O3) |
| `scale`, 2 limbs, N = 7 | 7.1 to 10.6 (-O2), 7.34 to 8.51 (-O3) | -0.124 to 1.22 (-O2), -1.1 to 1.55 (-O3) | 3.02 to 3.32 (-O2), -4.24 to -3.91 (-O3) | 2.07 to 2.16 (-O2), 2 to 2.1 (-O3) |
| `scale`, 2 limbs, N = 13 | 0.135 to 0.484 (-O2), -3.51 to -0.089 (-O3) | -0.06 to 1.85 (-O2), -3.1 to 0.24 (-O3) | 2.38 to 2.5 (-O2), -4.89 to -4.65 (-O3) | 3.27 to 3.31 (-O2), 3.14 to 3.29 (-O3) |
| `scale`, 2 limbs, N = 18 | -0.549 to 0.5 (-O2), -3.14 to 0.05 (-O3) | -0.82 to 0.52 (-O2), -3.93 to -0.95 (-O3) | 2.53 to 2.6 (-O2), -5.33 to -3.93 (-O3) | 1.86 to 1.92 |
| `scale`, 2 limbs, N = 80 | -0.13 to 3.83 (-O2), -0.66 to 2.16 (-O3) | 0.01 to 0.9 (-O2), -13.9 to 0.36 (-O3) | 3.08 to 3.47 (-O2), -0.54 to -0.11 (-O3) | 1.33 to 1.53 (-O2), 1.05 to 1.51 (-O3) |
| `half`, 1 limb, N = 3 | 0.25 to 0.98 (-O2), -1.81 to 2.26 (-O3) | -0.325 to 0.224 (-O2), -1.35 to 1.9 (-O3) | 2.18 to 2.36 (-O2), 2.39 to 2.64 (-O3) | 0.32 to 0.48 (-O2), 0.29 to 0.44 (-O3) |
| `half`, 1 limb, N = 7 | -0.38 to 1.58 (-O2), -1.87 to 0.67 (-O3) | 0.005 to 0.501 (-O2), -1.19 to 0.293 (-O3) | 2.15 to 2.16 (-O2), 2.53 to 2.75 (-O3) | -0.06 to -0.03 (-O2), -0.13 to 0.05 (-O3) |
| `half`, 1 limb, N = 13 | -1.36 to 0.06 (-O2), -1.57 to 0.65 (-O3) | 0.15 to 0.178 (-O2), -1.41 to 0.238 (-O3) | 2.31 to 2.47 (-O2), 2.43 to 2.67 (-O3) | -0.28 to -0.13 (-O2), -0.34 to 0.18 (-O3) |
| `half`, 1 limb, N = 18 | -0.53 to 1.43 (-O2), -2.08 to 1.67 (-O3) | -0.17 to 0.69 (-O2), -2.57 to 0.67 (-O3) | 2.89 to 2.95 (-O2), 2.61 to 2.89 (-O3) | -1.11 to -1.07 (-O2), -1.43 to -1.15 (-O3) |
| `half`, 1 limb, N = 80 | -2.68 to -0.18 (-O2), -2.7 to 0.7 (-O3) | 0 to 3.99 (-O2), -9.55 to 1.08 (-O3) | 3.85 to 3.95 (-O2), 3.55 to 4.21 (-O3) | 5.48 to 5.67 (-O2), 5.21 to 5.65 (-O3) |
| `half`, 2 limbs, N = 3 | 1.62 to 2.97 (-O2), -0.57 to 2.34 (-O3) | 1.15 to 1.79 (-O2), -2.34 to 0.567 (-O3) | 2.21 to 5.98 (-O2), 0.64 to 1.08 (-O3) | 0.68 to 0.72 (-O2), 0.68 to 1.54 (-O3) |
| `half`, 2 limbs, N = 7 | 0.08 to 2.01 (-O2), -2.4 to 0.6 (-O3) | 0.959 to 2.49 (-O2), -2.25 to 0.903 (-O3) | 1.09 to 4.64 (-O2), 0.67 to 1.56 (-O3) | 2 to 2.36 (-O2), 1.73 to 2.08 (-O3) |
| `half`, 2 limbs, N = 13 | -1.1 to -0.25 (-O2), -3.02 to 0.62 (-O3) | 0.14 to 1.36 (-O2), -3.28 to 0.39 (-O3) | 1.5 to 6.03 (-O2), 0.86 to 1.16 (-O3) | 2.77 to 2.82 (-O2), 2.45 to 2.69 (-O3) |
| `half`, 2 limbs, N = 18 | 0.01 to 0.91 (-O2), -3.31 to 1.34 (-O3) | -0.92 to 0.91 (-O2), -2.9 to 0.53 (-O3) | 1.34 to 3.55 (-O2), 0.64 to 1.3 (-O3) | 2.59 to 2.63 (-O2), 2.72 to 5.34 (-O3) |
| `half`, 2 limbs, N = 80 | -0.13 to 4.45 (-O2), 3.99 to 7.11 (-O3) | 0.15 to 4.13 (-O2), -22.3 to -6.41 (-O3) | 3.71 to 6.63 (-O2), 2.45 to 3.33 (-O3) | 5.65 to 5.97 (-O2), 5.61 to 5.74 (-O3) |
| the constructor, 1 limb, N = 3 | 5.25 to 10.9 (-O2), 4.5 to 9.96 (-O3) | -1.18 to -0.496 (-O2), -1.76 to 0.329 (-O3) | 3.57 to 3.92 (-O2), 3.01 to 4.52 (-O3) | 19.6 to 19.8 (-O2), 12.7 to 13.8 (-O3) |
| the constructor, 1 limb, N = 7 | -2.05 to 1.39 (-O2), 0.1 to 2.5 (-O3) | -7.46 to -4.54 (-O2), -1.39 to 1.46 (-O3) | 4.37 to 4.51 (-O2), 4.74 to 5.86 (-O3) | -0.07 to 1.59 (-O2), -1.21 to 1.63 (-O3) |
| the constructor, 1 limb, N = 13 | -0.75 to -0.46 (-O2), -4.01 to 1.94 (-O3) | -0.8 to 1.73 (-O2), -2.14 to 0.43 (-O3) | 2.97 to 3.13 (-O2), 4.01 to 4.2 (-O3) | 0.21 to 0.76 (-O2), 0.12 to 0.61 (-O3) |
| the constructor, 1 limb, N = 18 | -3.88 to -0.17 (-O2), -1.12 to 0.26 (-O3) | 1.1 to 2.19 (-O2), -7.22 to 1.42 (-O3) | 4.6 to 4.76 (-O2), 4.27 to 4.69 (-O3) | 0.37 to 1.61 (-O2), -0.04 to 2.13 (-O3) |
| the constructor, 1 limb, N = 80 | -5.7 to 4.77 (-O2), -6.24 to -0.17 (-O3) | 0.7 to 24.6 (-O2), -43.5 to 10.7 (-O3) | 1.7 to 2.2 (-O2), -1.7 to 2.1 (-O3) | -1.03 to 0.09 (-O2), 3.08 to 6.31 (-O3) |
| the constructor, 2 limbs, N = 3 | 3.78 to 5.12 (-O2), 3.81 to 5.65 (-O3) | 0.041 to 0.829 (-O2), -2.26 to -0.153 (-O3) | 3.29 to 3.62 (-O2), 1.67 to 2.39 (-O3) | 9.45 to 9.75 |
| the constructor, 2 limbs, N = 7 | -1.1 to 0.56 (-O2), -1.36 to 1.36 (-O3) | -1.03 to 1.31 (-O2), -2.86 to -0.153 (-O3) | 3.82 to 4.38 (-O2), 4.84 to 5.72 (-O3) | 1.14 to 2.82 (-O2), 1.15 to 2.61 (-O3) |
| the constructor, 2 limbs, N = 13 | -4.47 to -2.28 (-O2), 1.73 to 5.1 (-O3) | -2.06 to 3.25 (-O2), -3.06 to 0.2 (-O3) | 2.93 to 3.04 (-O2), 0.71 to 1.31 (-O3) | 0.64 to 2.19 (-O2), 0.06 to 5.71 (-O3) |
| the constructor, 2 limbs, N = 18 | -1.28 to 0.59 (-O2), -2.16 to 0.87 (-O3) | -2.06 to 3.3 (-O2), -11.6 to 0.4 (-O3) | -0.3 to 0.76 (-O2), -11.7 to -10.9 (-O3) | 2.18 to 2.47 (-O2), 0.95 to 5.41 (-O3) |
| the constructor, 2 limbs, N = 80 | 2.52 to 10.3 (-O2), -2.5 to 13.2 (-O3) | -0.5 to 23.2 (-O2), -78.4 to 0 (-O3) | 19.3 to 22.4 (-O2), -0.9 to 1.8 (-O3) | -0.7 to 6.32 (-O2), 3.3 to 8.78 (-O3) |

| Short ball vectors, every size in one unit, a dependent chain: with the check over without | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add(x, y, z)`, 1 limb, N = 3 | 0.97 to 1.01 (-O2), 0.96 to 1.00 (-O3) | 0.75 to 0.81 (-O2), 0.87 to 0.98 (-O3) | 1.18 to 1.23 | 0.97 to 0.98 |
| `add(x, y, z)`, 1 limb, N = 7 | 0.91 to 1.07 (-O2), 0.97 to 1.00 (-O3) | 0.88 to 1.03 (-O2), 1.01 to 1.11 (-O3) | 1.11 to 1.15 | 1.07 to 1.09 |
| `add(x, y, z)`, 1 limb, N = 13 | 0.55 to 0.63 (-O2), 0.59 to 0.72 (-O3) | 0.99 to 1.07 (-O2), 1.04 to 1.17 (-O3) | 1.15 to 1.18 | 1.16 to 1.17 (-O2), 0.94 to 1.16 (-O3) |
| `add(x, y, z)`, 1 limb, N = 18 | 1.00 to 1.08 (-O2), 0.99 to 1.03 (-O3) | 1.00 to 1.04 (-O2), 1.05 to 1.12 (-O3) | 1.09 to 1.13 | 1.18 to 1.20 |
| `add(x, y, z)`, 1 limb, N = 80 | 0.99 to 1.02 | 1.00 to 1.01 (-O2), 0.98 to 1.04 (-O3) | 1.12 to 1.19 (-O2), 1.14 to 1.20 (-O3) | 1.15 to 1.18 |
| `add(x, y, z)`, 2 limbs, N = 3 | 0.96 to 1.10 (-O2), 1.00 (-O3) | 1.00 to 1.08 (-O2), 1.00 to 1.10 (-O3) | 1.11 to 1.13 | 1.11 to 1.13 |
| `add(x, y, z)`, 2 limbs, N = 7 | 0.92 to 1.07 (-O2), 0.98 to 1.01 (-O3) | 1.00 to 1.09 (-O2), 1.00 to 1.09 (-O3) | 1.07 to 1.09 | 1.07 to 1.09 |
| `add(x, y, z)`, 2 limbs, N = 13 | 0.92 to 1.02 (-O2), 0.99 to 1.01 (-O3) | 0.96 to 1.05 (-O2), 0.92 to 1.02 (-O3) | 1.07 to 1.10 | 1.09 to 1.11 |
| `add(x, y, z)`, 2 limbs, N = 18 | 0.98 to 1.08 (-O2), 1.00 to 1.02 (-O3) | 1.06 to 1.15 (-O2), 0.99 to 1.04 (-O3) | 1.09 to 1.12 | 1.11 to 1.15 |
| `add(x, y, z)`, 2 limbs, N = 80 | 1.00 to 1.07 (-O2), 1.00 to 1.06 (-O3) | 0.94 to 1.00 (-O2), 0.92 to 1.00 (-O3) | 1.03 to 1.06 | 1.05 to 1.06 |
| `z = x + y`, 1 limb, N = 3 | 0.99 to 1.03 (-O2), 1.02 to 1.11 (-O3) | 0.90 to 1.07 (-O2), 0.92 to 1.06 (-O3) | 1.00 to 1.01 | 1.00 to 1.01 |
| `z = x + y`, 1 limb, N = 7 | 0.92 to 1.01 (-O2), 0.96 to 1.01 (-O3) | 0.98 to 1.07 (-O2), 0.80 to 0.90 (-O3) | 0.99 to 1.00 | 0.99 to 1.00 |
| `z = x + y`, 1 limb, N = 13 | 0.89 to 1.05 (-O2), 0.94 to 1.03 (-O3) | 0.99 to 1.00 (-O2), 0.92 to 1.06 (-O3) | 0.99 to 1.01 | 0.99 to 1.00 |
| `z = x + y`, 1 limb, N = 18 | 0.95 to 1.00 (-O2), 1.00 to 1.02 (-O3) | 0.96 to 1.00 (-O2), 1.01 to 1.06 (-O3) | 0.87 to 1.02 (-O2), 0.85 to 0.98 (-O3) | 1.00 to 1.02 |
| `z = x + y`, 1 limb, N = 80 | 0.93 to 1.03 (-O2), 0.98 to 0.99 (-O3) | 1.00 to 1.01 (-O2), 1.00 to 1.06 (-O3) | 1.00 to 1.03 | 0.90 to 1.02 (-O2), 0.99 to 1.11 (-O3) |
| `z = x + y`, 2 limbs, N = 3 | 0.91 to 1.00 (-O2), 0.99 (-O3) | 0.94 to 1.00 (-O2), 0.99 to 1.01 (-O3) | 1.00 to 1.02 (-O2), 0.86 to 0.99 (-O3) | 0.98 to 1.02 (-O2), 1.02 to 1.11 (-O3) |
| `z = x + y`, 2 limbs, N = 7 | 0.92 to 1.00 (-O2), 0.99 to 1.00 (-O3) | 0.95 to 1.11 (-O2), 0.93 to 1.11 (-O3) | 1.00 (-O2), 0.87 to 0.98 (-O3) | 0.95 to 1.00 (-O2), 1.02 to 1.09 (-O3) |
| `z = x + y`, 2 limbs, N = 13 | 0.96 to 1.08 (-O2), 0.99 to 1.01 (-O3) | 1.01 to 1.06 (-O2), 0.98 to 1.08 (-O3) | 1.00 to 1.03 | 0.91 to 0.99 (-O2), 0.96 to 1.09 (-O3) |
| `z = x + y`, 2 limbs, N = 18 | 0.97 to 1.05 (-O2), 0.98 to 1.01 (-O3) | 0.99 to 1.02 (-O2), 0.95 to 1.01 (-O3) | 0.99 to 1.01 | 0.94 to 0.99 (-O2), 1.00 to 1.06 (-O3) |
| `z = x + y`, 2 limbs, N = 80 | 1.00 to 1.09 (-O2), 0.99 to 1.05 (-O3) | 0.97 to 1.03 (-O2), 0.93 to 1.00 (-O3) | 0.99 to 1.02 | 0.99 to 1.02 (-O2), 1.00 to 1.05 (-O3) |
| `sub`, 1 limb, N = 3 | 1.02 to 1.10 (-O2), 1.00 to 1.05 (-O3) | 0.66 to 1.14 (-O2), 0.73 to 1.03 (-O3) | 1.21 to 1.22 (-O2), 1.47 to 1.49 (-O3) | 0.97 to 0.99 |
| `sub`, 1 limb, N = 7 | 0.97 to 1.03 (-O2), 0.93 to 1.00 (-O3) | 0.90 to 1.05 (-O2), 0.95 to 1.07 (-O3) | 1.15 to 1.16 (-O2), 1.10 to 1.12 (-O3) | 1.07 to 1.08 |
| `sub`, 1 limb, N = 13 | 0.67 to 0.74 (-O2), 0.70 to 0.72 (-O3) | 1.00 (-O2), 1.05 to 1.16 (-O3) | 1.14 to 1.17 | 1.16 to 1.17 (-O2), 0.94 to 1.15 (-O3) |
| `sub`, 1 limb, N = 18 | 1.00 to 1.14 (-O2), 0.99 to 1.02 (-O3) | 0.99 to 1.01 (-O2), 1.05 to 1.12 (-O3) | 1.09 (-O2), 1.14 to 1.16 (-O3) | 1.19 to 1.20 |
| `sub`, 1 limb, N = 80 | 0.92 to 1.00 (-O2), 0.97 to 1.00 (-O3) | 1.02 to 1.04 (-O2), 1.00 to 1.05 (-O3) | 1.13 to 1.14 (-O2), 1.03 to 1.05 (-O3) | 1.15 to 1.18 |
| `sub`, 2 limbs, N = 3 | 0.93 to 1.02 (-O2), 0.99 (-O3) | 0.98 to 1.09 (-O2), 0.91 to 0.93 (-O3) | 1.10 to 1.11 | 1.12 to 1.14 |
| `sub`, 2 limbs, N = 7 | 0.99 to 1.06 (-O2), 0.97 to 1.02 (-O3) | 0.94 to 1.00 (-O2), 0.93 to 1.05 (-O3) | 1.02 to 1.07 | 1.10 to 1.12 |
| `sub`, 2 limbs, N = 13 | 0.99 to 1.10 (-O2), 0.99 to 1.01 (-O3) | 0.99 to 1.04 (-O2), 0.99 to 1.06 (-O3) | 1.07 to 1.10 (-O2), 0.98 to 1.00 (-O3) | 1.11 to 1.13 |
| `sub`, 2 limbs, N = 18 | 1.01 to 1.11 (-O2), 0.99 to 1.01 (-O3) | 0.99 to 1.03 (-O2), 0.98 to 1.05 (-O3) | 1.09 to 1.11 | 1.13 to 1.16 |
| `sub`, 2 limbs, N = 80 | 1.00 to 1.09 (-O2), 1.00 to 1.06 (-O3) | 0.97 to 1.02 (-O2), 0.92 to 1.01 (-O3) | 1.04 to 1.06 | 1.05 to 1.06 |
| `scale`, 1 limb, N = 3 | 1.50 to 1.73 (-O2), 1.55 to 1.80 (-O3) | 0.80 to 0.90 (-O2), 0.74 to 1.33 (-O3) | 1.17 to 1.21 | 1.37 to 1.39 |
| `scale`, 1 limb, N = 7 | 1.68 to 1.83 (-O2), 1.58 to 1.83 (-O3) | 0.98 to 1.05 (-O2), 0.90 to 1.11 (-O3) | 1.17 to 1.20 | 1.32 to 1.35 |
| `scale`, 1 limb, N = 13 | 1.50 to 1.59 (-O2), 1.54 to 1.67 (-O3) | 0.98 to 1.01 (-O2), 1.03 to 1.22 (-O3) | 1.19 to 1.22 | 0.86 to 1.37 (-O2), 0.85 to 1.36 (-O3) |
| `scale`, 1 limb, N = 18 | 0.95 to 1.06 (-O2), 1.07 to 1.23 (-O3) | 1.01 to 1.02 (-O2), 0.97 to 1.07 (-O3) | 1.16 to 1.17 (-O2), 1.19 to 1.21 (-O3) | 1.39 to 1.40 (-O2), 1.38 to 1.43 (-O3) |
| `scale`, 1 limb, N = 80 | 0.93 to 1.03 (-O2), 0.98 to 0.99 (-O3) | 1.01 (-O2), 1.01 to 1.06 (-O3) | 1.12 to 1.16 | 1.22 to 1.23 (-O2), 1.08 to 1.81 (-O3) |
| `scale`, 2 limbs, N = 3 | 1.72 to 1.90 (-O2), 1.64 to 1.79 (-O3) | 0.93 to 1.23 (-O2), 1.07 to 1.23 (-O3) | 1.15 to 1.16 (-O2), 0.75 to 0.76 (-O3) | 1.31 to 1.33 (-O2), 1.24 to 1.26 (-O3) |
| `scale`, 2 limbs, N = 7 | 1.07 to 1.22 (-O2), 1.08 to 1.25 (-O3) | 1.04 to 1.09 (-O2), 0.96 to 1.15 (-O3) | 1.14 to 1.15 (-O2), 0.79 to 0.80 (-O3) | 1.41 to 1.44 |
| `scale`, 2 limbs, N = 13 | 0.98 to 1.01 (-O2), 0.95 to 1.03 (-O3) | 1.01 to 1.15 (-O2), 0.97 to 1.07 (-O3) | 1.14 (-O2), 0.77 to 0.78 (-O3) | 1.27 to 1.30 |
| `scale`, 2 limbs, N = 18 | 1.00 to 1.31 (-O2), 0.91 to 1.02 (-O3) | 0.95 to 1.01 (-O2), 0.95 to 1.00 (-O3) | 1.11 (-O2), 0.78 to 0.83 (-O3) | 1.12 to 1.13 |
| `scale`, 2 limbs, N = 80 | 1.01 to 1.10 (-O2), 1.00 to 1.06 (-O3) | 0.97 to 1.04 (-O2), 0.97 to 1.02 (-O3) | 1.06 to 1.07 (-O2), 0.98 to 1.00 (-O3) | 1.02 to 1.04 |
| `half`, 1 limb, N = 3 | 0.99 to 1.08 (-O2), 0.96 to 1.07 (-O3) | 1.08 to 1.26 (-O2), 1.03 to 1.14 (-O3) | 1.14 to 1.15 (-O2), 1.28 to 1.30 (-O3) | 1.06 to 1.08 |
| `half`, 1 limb, N = 7 | 0.99 to 1.03 (-O2), 0.97 to 1.00 (-O3) | 1.06 to 1.17 (-O2), 1.00 to 1.11 (-O3) | 1.13 to 1.14 (-O2), 1.24 to 1.27 (-O3) | 1.01 to 1.03 |
| `half`, 1 limb, N = 13 | 0.94 to 1.00 (-O2), 0.97 to 1.03 (-O3) | 1.04 to 1.11 (-O2), 1.07 to 1.14 (-O3) | 1.16 (-O2), 1.27 to 1.29 (-O3) | 0.99 to 1.03 |
| `half`, 1 limb, N = 18 | 0.94 to 1.02 (-O2), 0.98 to 1.02 (-O3) | 1.02 to 1.11 (-O2), 1.03 to 1.08 (-O3) | 1.15 to 1.16 (-O2), 1.21 to 1.23 (-O3) | 0.92 to 0.95 |
| `half`, 1 limb, N = 80 | 0.97 to 1.02 (-O2), 1.00 to 1.01 (-O3) | 0.98 to 1.02 (-O2), 0.99 to 1.08 (-O3) | 1.10 to 1.11 (-O2), 1.13 to 1.16 (-O3) | 1.16 to 1.19 |
| `half`, 2 limbs, N = 3 | 1.06 to 1.16 (-O2), 0.99 to 1.11 (-O3) | 1.32 to 1.34 (-O2), 0.97 to 1.30 (-O3) | 1.04 to 1.09 | 1.02 to 1.05 |
| `half`, 2 limbs, N = 7 | 0.97 to 1.12 (-O2), 0.98 to 1.04 (-O3) | 1.20 to 1.31 (-O2), 1.07 to 1.27 (-O3) | 1.03 to 1.05 | 1.11 to 1.14 |
| `half`, 2 limbs, N = 13 | 0.98 to 1.05 (-O2), 0.95 to 1.02 (-O3) | 1.04 to 1.08 (-O2), 1.04 to 1.16 (-O3) | 1.04 to 1.06 | 1.14 to 1.17 |
| `half`, 2 limbs, N = 18 | 1.01 to 1.18 (-O2), 0.95 to 1.06 (-O3) | 1.00 to 1.12 (-O2), 1.08 to 1.16 (-O3) | 1.02 to 1.05 | 1.13 to 1.15 |
| `half`, 2 limbs, N = 80 | 1.00 to 1.15 (-O2), 1.01 to 1.09 (-O3) | 1.02 to 1.05 (-O2), 0.82 to 0.92 (-O3) | 1.05 to 1.06 | 1.11 to 1.12 |
| the constructor, 1 limb, N = 3 | 1.47 to 1.62 (-O2), 1.37 to 1.58 (-O3) | 0.81 to 0.99 (-O2), 0.63 to 0.88 (-O3) | 1.18 to 1.24 (-O2), 1.28 to 1.35 (-O3) | 4.11 to 4.20 |
| the constructor, 1 limb, N = 7 | 0.97 to 1.10 (-O2), 0.90 to 1.03 (-O3) | 0.56 to 0.67 (-O2), 1.52 to 1.63 (-O3) | 1.26 to 1.27 (-O2), 1.52 to 1.55 (-O3) | 0.99 to 1.04 (-O2), 0.95 to 1.07 (-O3) |
| the constructor, 1 limb, N = 13 | 0.92 to 1.00 (-O2), 0.95 to 0.99 (-O3) | 0.99 to 1.01 (-O2), 2.70 to 2.89 (-O3) | 1.12 (-O2), 1.42 to 1.44 (-O3) | 1.00 to 1.02 |
| the constructor, 1 limb, N = 18 | 0.90 to 0.99 (-O2), 0.91 to 1.00 (-O3) | 0.94 to 1.01 (-O2), 1.06 to 1.12 (-O3) | 1.08 to 1.10 (-O2), 1.19 to 1.21 (-O3) | 1.01 to 1.06 |
| the constructor, 1 limb, N = 80 | 0.97 to 1.01 | 0.98 to 1.00 (-O2), 1.01 to 1.05 (-O3) | 0.99 to 1.01 | 1.04 (-O2), 1.03 to 1.10 (-O3) |
| the constructor, 2 limbs, N = 3 | 1.26 to 1.44 (-O2), 1.34 to 1.50 (-O3) | 0.91 to 1.07 (-O2), 0.89 to 0.99 (-O3) | 1.18 to 1.20 (-O2), 1.37 to 1.47 (-O3) | 1.43 to 2.14 (-O2), 2.08 to 2.11 (-O3) |
| the constructor, 2 limbs, N = 7 | 0.95 to 1.04 (-O2), 0.98 to 1.02 (-O3) | 0.95 to 1.02 (-O2), 1.71 to 1.93 (-O3) | 1.21 (-O2), 1.63 to 1.70 (-O3) | 0.88 to 1.19 (-O2), 1.07 to 1.15 (-O3) |
| the constructor, 2 limbs, N = 13 | 0.95 to 0.98 (-O2), 1.03 to 1.20 (-O3) | 0.94 to 1.05 (-O2), 2.47 to 2.76 (-O3) | 1.12 to 1.13 (-O2), 1.36 to 1.40 (-O3) | 1.00 to 1.02 (-O2), 1.00 to 1.09 (-O3) |
| the constructor, 2 limbs, N = 18 | 0.98 to 1.03 (-O2), 0.99 (-O3) | 1.00 to 1.04 (-O2), 0.94 to 1.03 (-O3) | 0.99 to 1.00 (-O2), 0.85 to 0.87 (-O3) | 1.01 to 1.07 (-O2), 1.05 to 1.19 (-O3) |
| the constructor, 2 limbs, N = 80 | 1.04 to 1.17 (-O2), 1.00 to 1.09 (-O3) | 1.00 to 1.05 (-O2), 0.94 to 1.00 (-O3) | 0.98 to 0.99 (-O2), 1.07 to 1.09 (-O3) | 0.96 to 1.05 (-O2), 1.04 to 1.10 (-O3) |

#### Question 15: the guards

| The guards: the loop with them over the same loop without, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `dot`, one limb (3 operations per term against 1), L1 | 1.01 to 1.02 (-O2), 0.83 to 1.01 (-O3) | 0.99 to 1.00 |
| `axpy`, one limb (y guarded), L1 | 1.09 to 1.13 | 1.15 to 1.16 |
| `axpy`, two limbs, a of T (y guarded), L1 | 1.00 | 1.00 |
| `axpy`, two limbs, a of two limbs (y guarded), L1 | 0.99 to 1.00 | 1.00 |
| `scale`, two limbs (the limbs and a guarded), L1 | 1.16 | 1.16 |
| `sum`, one limb (the element guarded), L1 | 1.02 (-O2), 0.97 to 0.99 (-O3) | 1.01 to 1.02 |
| `sum`, two limbs (the limbs guarded), L1 | 1.01 | 1.01 to 1.02 |
| `add`, one limb (both guarded), L1 | 1.19 to 1.20 (-O2), 1.19 to 1.45 (-O3) | 1.43 to 1.44 |
| `add`, two limbs (every limb guarded), L1 | 1.19 | 1.20 to 1.21 |
| `dot`, one limb (3 operations per term against 1), LLC | 1.00 to 1.01 | 0.99 to 1.00 |
| `axpy`, one limb (y guarded), LLC | 0.98 to 0.99 | 0.98 to 0.99 |
| `axpy`, two limbs, a of T (y guarded), LLC | 0.99 to 1.00 | 0.99 to 1.01 |
| `axpy`, two limbs, a of two limbs (y guarded), LLC | 0.99 to 1.00 | 0.99 to 1.00 |
| `scale`, two limbs (the limbs and a guarded), LLC | 1.14 to 1.15 | 1.14 to 1.15 |
| `sum`, one limb (the element guarded), LLC | 1.00 to 1.01 | 0.99 to 1.00 |
| `sum`, two limbs (the limbs guarded), LLC | 1.01 to 1.02 | 1.02 to 1.03 |
| `add`, one limb (both guarded), LLC | 0.96 to 0.97 | 0.97 to 0.98 |
| `add`, two limbs (every limb guarded), LLC | 1.19 | 1.19 to 1.20 |
| `conv`, one limb, 16 coefficients (both factors guarded) | 1.06 to 1.10 (-O2), 1.13 to 1.15 (-O3) | 1.02 to 1.03 |
| `conv`, one limb, 64 coefficients (both factors guarded) | 1.13 to 1.14 (-O2), 0.90 to 1.02 (-O3) | 1.14 to 1.15 |
| `conv`, one limb, 512 coefficients (both factors guarded) | 1.00 to 1.02 | 1.01 |

| The guards against the control of T, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `dot`, one limb, with the guards, over the plain FMA loop in the same order, L1 | 1.00 to 1.03 (-O2), 0.89 to 0.91 (-O3) | 1.04 to 1.05 |
| `dot`, one limb, without them, over the same, L1 | 0.99 to 1.01 (-O2), 0.89 to 1.10 (-O3) | 1.05 to 1.06 |
| `axpy`, one limb, with them, over `a x + y` of T, L1 | 0.66 (-O2), 1.89 to 2.07 (-O3) | 1.65 to 1.67 |
| `axpy`, one limb, without them, over the same, L1 | 0.59 to 0.60 (-O2), 1.71 to 1.88 (-O3) | 1.43 to 1.44 |
| `scale`, two limbs, with them, over `x a` of T, L1 | 1.56 to 1.57 (-O2), 2.88 to 2.96 (-O3) | 5.98 to 6.02 |
| `scale`, two limbs, without them, over the same, L1 | 1.34 to 1.35 (-O2), 2.49 to 2.54 (-O3) | 5.15 to 5.18 |
| `dot`, one limb, with the guards, over the plain FMA loop in the same order, LLC | 0.99 to 1.00 | 0.99 to 1.00 |
| `dot`, one limb, without them, over the same, LLC | 1.00 | 1.00 |
| `axpy`, one limb, with them, over `a x + y` of T, LLC | 0.72 to 0.73 (-O2), 1.10 to 1.12 (-O3) | 1.08 to 1.11 (-O2), 0.96 to 1.10 (-O3) |
| `axpy`, one limb, without them, over the same, LLC | 0.73 to 0.74 (-O2), 1.12 to 1.14 (-O3) | 1.11 to 1.13 (-O2), 0.97 to 1.11 (-O3) |
| `scale`, two limbs, with them, over `x a` of T, LLC | 0.83 to 1.44 (-O2), 2.41 to 2.42 (-O3) | 2.41 to 2.42 (-O2), 2.41 to 2.91 (-O3) |
| `scale`, two limbs, without them, over the same, LLC | 0.72 to 1.26 (-O2), 2.11 to 2.12 (-O3) | 2.09 to 2.11 (-O2), 2.10 to 2.53 (-O3) |
| `conv`, one limb, 16, with them, over the plain FMA loop | 1.20 to 1.25 (-O2), 1.26 to 1.30 (-O3) | 1.16 to 1.17 |
| `conv`, one limb, 16, without them, over the same | 1.10 to 1.15 | 1.13 to 1.15 |
| `conv`, one limb, 64, with them, over the plain FMA loop | 1.18 to 1.19 (-O2), 1.06 (-O3) | 1.21 to 1.22 |
| `conv`, one limb, 64, without them, over the same | 1.04 (-O2), 1.04 to 1.18 (-O3) | 1.06 to 1.07 |
| `conv`, one limb, 512, with them, over the plain FMA loop | 1.00 to 1.01 | 1.02 |
| `conv`, one limb, 512, without them, over the same | 1.00 | 1.01 |

| The guards of the accumulator: with over without, double | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add_product`, one limb (both factors guarded), L1 | 1.01 | 1.00 |
| `add_product`, two limbs (every limb guarded), L1 | 1.00 | 1.00 |
| `add_product`, one limb, the public member over the kernels without the guards, L1 | 1.03 to 1.04 | 1.00 |
| `add_product`, two limbs, the same, L1 | 1.00 | 1.00 |
| `add_product`, one limb (both factors guarded), LLC | 1.00 | 1.00 |
| `add_product`, two limbs (every limb guarded), LLC | 1.00 | 1.00 |
| `add_product`, one limb, the public member over the kernels without the guards, LLC | 1.00 to 1.01 | 1.00 |
| `add_product`, two limbs, the same, LLC | 1.00 | 1.00 |

#### Question 16: the accumulator

| The accumulator: ns per element | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, one limb, L1 | 1.3 to 1.31 | 0.884 to 0.897 |
| `add_product`, one limb, L1 | 1.53 | 1.48 to 1.5 |
| `add`, two limbs, L1 | 10.2 | 10.1 to 10.2 |
| `add_product`, two limbs, L1 | 10.2 | 10.2 to 10.3 |
| `add` of a value of T, two limbs, L1 | 10.1 to 10.2 | 10.1 to 10.3 |
| `add_product` of two values of T, two limbs, L1 | 10.2 | 10.2 to 10.4 |
| `add` into 4 accumulators merged, one limb, L1 | 3.09 to 3.17 | 0.819 to 0.833 |
| `add` into 16 accumulators merged, two limbs, L1 | 12.2 to 12.3 | 9.98 to 10.1 |
| `add` into W accumulators in the lane order, two limbs, L1 | 4.82 to 4.83 | 3.99 to 4.05 |
| `add`, one limb, LLC | 1.3 to 1.31 | 0.901 to 0.919 |
| `add_product`, one limb, LLC | 1.51 to 1.52 | 1.5 to 1.53 |
| `add`, two limbs, LLC | 10.2 | 10.1 to 10.3 |
| `add_product`, two limbs, LLC | 10.2 | 10.2 to 10.4 |
| `add` of a value of T, two limbs, LLC | 10.2 | 10.2 to 10.3 |
| `add_product` of two values of T, two limbs, LLC | 10.2 to 10.3 | 10.2 to 10.4 |
| `add` into 4 accumulators merged, one limb, LLC | 3.31 to 3.39 | 0.902 to 0.917 |
| `add` into 16 accumulators merged, two limbs, LLC | 12.5 | 10.1 to 10.3 |
| `add` into W accumulators in the lane order, two limbs, LLC | 4.77 to 4.78 | 3.96 to 4.02 |

| The accumulator over the functions on arrays | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, one limb, over `sum` sequential, L1 | 1.47 (-O2), 1.52 (-O3) | 1.03 |
| `add`, one limb, over `sum`, L1 | 5.50 to 5.65 | 4.50 to 4.51 |
| `add_product`, one limb, over `dot` sequential, L1 | 1.05 | 1.03 |
| `add_product`, one limb, over `dot`, L1 | 4.32 to 4.37 | 4.57 to 4.58 |
| `add`, two limbs, over `sum` sequential, L1 | 1.00 | 1.00 |
| `add`, two limbs, over `sum`, L1 | 3.82 to 3.92 | 3.91 to 3.92 |
| `add_product`, two limbs, over `dot` sequential, L1 | 1.00 | 0.98 to 0.99 |
| `add_product`, two limbs, over `dot`, L1 | 3.83 to 3.92 | 3.87 to 3.90 |
| `add` of T into two limbs, over `sum` of two limbs of the same data, sequential, L1 | 1.00 | 1.00 |
| `add_product` of T into two limbs, over `dot` of two limbs of the same data, sequential, L1 | 1.00 | 0.99 to 1.00 |
| 4 accumulators merged over one, one limb, L1 | 2.38 to 2.44 (-O2), 2.37 to 2.43 (-O3) | 0.92 to 0.93 |
| 16 accumulators merged over one, one limb, L1 | 1.74 to 1.77 | 0.70 to 0.71 |
| W accumulators in the lane order over one, one limb, L1 | 3.20 to 3.37 (-O2), 0.45 to 0.46 (-O3) | 0.47 |
| W accumulators in the lane order over `sum`, one limb, L1 | 17.6 to 18.6 (-O2), 2.56 (-O3) | 2.11 to 2.12 |
| 4 accumulators merged over one, two limbs, L1 | 1.21 to 1.22 | 1.00 |
| 16 accumulators merged over one, two limbs, L1 | 1.20 to 1.21 | 0.99 |
| W accumulators in the lane order over one, two limbs, L1 | 0.47 | 0.39 to 0.40 |
| W accumulators in the lane order over `sum`, two limbs, L1 | 1.80 to 1.85 | 1.54 to 1.56 |
| the public members over the kernels, `add`, two limbs, L1 | 1.00 | 1.00 |
| the public members over the kernels, `add_product`, two limbs, L1 | 1.00 | 1.00 |
| `add`, one limb, over `sum` sequential, LLC | 1.44 to 1.45 | 1.00 |
| `add`, one limb, over `sum`, LLC | 5.73 to 5.76 | 3.98 to 4.00 |
| `add_product`, one limb, over `dot` sequential, LLC | 1.00 to 1.01 | 1.00 |
| `add_product`, one limb, over `dot`, LLC | 3.99 to 4.01 | 3.97 to 3.99 |
| `add`, two limbs, over `sum` sequential, LLC | 1.00 | 1.00 |
| `add`, two limbs, over `sum`, LLC | 3.99 to 4.00 | 3.98 to 3.99 |
| `add_product`, two limbs, over `dot` sequential, LLC | 1.00 | 0.99 to 1.00 |
| `add_product`, two limbs, over `dot`, LLC | 3.98 to 4.00 | 3.96 to 3.97 |
| `add` of T into two limbs, over `sum` of two limbs of the same data, sequential, LLC | 1.00 | 1.00 |
| `add_product` of T into two limbs, over `dot` of two limbs of the same data, sequential, LLC | 1.00 | 0.99 to 1.00 |
| 4 accumulators merged over one, one limb, LLC | 2.54 to 2.60 | 1.00 |
| 16 accumulators merged over one, one limb, LLC | 2.56 to 2.57 | 1.00 |
| W accumulators in the lane order over one, one limb, LLC | 3.17 to 3.34 (-O2), 0.45 (-O3) | 0.45 |
| W accumulators in the lane order over `sum`, one limb, LLC | 18.1 to 19.2 (-O2), 2.60 to 2.61 (-O3) | 1.78 to 1.79 |
| 4 accumulators merged over one, two limbs, LLC | 1.22 to 1.23 | 1.00 |
| 16 accumulators merged over one, two limbs, LLC | 1.22 | 1.00 |
| W accumulators in the lane order over one, two limbs, LLC | 0.47 | 0.39 |
| W accumulators in the lane order over `sum`, two limbs, LLC | 1.86 to 1.87 | 1.56 to 1.57 |
| the public members over the kernels, `add`, two limbs, LLC | 1.00 | 1.00 |
| the public members over the kernels, `add_product`, two limbs, LLC | 1.00 | 1.00 |

| The accumulator: ns per call | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `merge`, 1 limb | 0.902 to 0.91 | 0.811 to 0.825 |
| `merge`, 2 limbs | 10.2 | 10.1 to 10.3 |
| `sum()`, 1 limb | 1.21 (-O2), 0.933 to 0.934 (-O3) | 0.826 to 0.843 |
| `sum()`, 2 limbs | 1.34 (-O2), 1.25 to 1.26 (-O3) | 1.18 to 1.2 |
| `error_bound()`, 1 limb | 6.35 (-O2), 4.72 (-O3) | 6 to 6.17 |
| `error_bound()`, 2 limbs | 6.64 to 6.66 (-O2), 5.53 to 5.55 (-O3) | 6.48 to 6.6 |
| `ball()`, 1 limb | 7.28 to 7.34 (-O2), 6.62 to 6.63 (-O3) | 8.04 to 8.18 |
| `ball()`, 2 limbs | 7.97 to 7.99 (-O2), 7.29 to 7.32 (-O3) | 8.54 to 8.68 |

#### Question 17: accuracy

| Sums, linux (4 lanes): relative error, median over the trials, by condition | naive loop | Kairn, one limb | Sum2 | Kairn, two limbs | Accumulator, two limbs |
|---|---|---|---|---|---|
| n = 1000, condition 1e0 to 1e3 (40 trials) | 6.8e-16 | 1.9e-16 | 4.2e-17 | 0.0e+00 | 0.0e+00 |
| n = 1000, condition 1e4 to 1e7 (20 trials) | 1.9e-11 | 1.8e-11 | 4.1e-17 | 1.3e-27 | 1.8e-27 |
| n = 1000, condition 1e8 to 1e11 (20 trials) | 7.2e-08 | 6.0e-08 | 4.0e-17 | 5.7e-24 | 6.6e-24 |
| n = 1000, condition 1e12 to 1e15 (20 trials) | 1.1e-03 | 4.3e-04 | 4.0e-17 | 5.5e-20 | 4.0e-20 |
| n = 1000, condition 1e16 to 1e19 (20 trials) | 8.2e+00 | 7.1e+00 | 5.3e-15 | 4.1e-16 | 1.9e-16 |
| n = 1000, condition 1e20 to 1e23 (20 trials) | 3.1e+04 | 1.8e+04 | 7.7e-12 | 1.1e-12 | 3.2e-12 |
| n = 1000, condition 1e24 to 1e27 (20 trials) | 5.7e+08 | 4.0e+08 | 2.9e-07 | 4.1e-08 | 7.0e-08 |
| n = 1000, condition 1e28 to 1e31 (20 trials) | 5.5e+12 | 5.2e+12 | 1.1e-03 | 2.4e-04 | 4.3e-04 |
| n = 1000, condition 1e32 to 1e35 (22 trials) | 7.3e+16 | 2.4e+16 | 3.1e+01 | 7.2e+00 | 1.8e+00 |
| n = 1000, condition 1e36 to 1e39 (20 trials) | 4.8e+20 | 3.3e+20 | 2.4e+05 | 1.5e+04 | 3.7e+04 |
| n = 1000, condition 1e40 to 1e43 (18 trials) | 2.5e+24 | 2.7e+24 | 1.3e+09 | 1.8e+08 | 1.4e+08 |
| n = 1000000, condition 1e0 to 1e3 (8 trials) | 4.5e-14 | 1.2e-14 | 2.0e-17 | 0.0e+00 | 0.0e+00 |
| n = 1000000, condition 1e8 to 1e11 (5 trials) | 2.5e-08 | 4.8e-08 | 2.6e-17 | 3.7e-24 | 1.6e-23 |
| n = 1000000, condition 1e12 to 1e15 (6 trials) | 2.5e-01 | 3.3e-01 | 6.4e-15 | 1.7e-17 | 7.2e-18 |
| n = 1000000, condition 1e16 to 1e19 (3 trials) | 1.9e+02 | 1.1e+04 | 2.6e-11 | 2.0e-13 | 2.8e-13 |
| n = 1000000, condition 1e20 to 1e23 (6 trials) | 4.9e+07 | 5.7e+07 | 1.8e-06 | 3.5e-09 | 4.7e-09 |
| n = 1000000, condition 1e24 to 1e27 (3 trials) | 4.1e+11 | 7.1e+10 | 6.1e-03 | 1.8e-05 | 4.7e-05 |
| n = 1000000, condition 1e28 to 1e31 (5 trials) | 4.0e+14 | 1.7e+15 | 7.2e+00 | 1.1e-01 | 1.5e-01 |
| n = 1000000, condition 1e32 to 1e35 (4 trials) | 5.9e+18 | 1.2e+19 | 8.1e+05 | 3.0e+03 | 1.7e+03 |
| n = 1000000, condition 1e36 to 1e39 (4 trials) | 1.0e+23 | 1.2e+23 | 2.6e+09 | 3.7e+07 | 4.2e+07 |
| n = 1000000, condition 1e40 to 1e43 (4 trials) | 1.7e+27 | 1.3e+27 | 9.4e+12 | 6.9e+10 | 1.5e+11 |

| Sums, linux: the stated bound over the error made, median (smallest) over the trials | Kairn, one limb | one limb, sequential | two limbs | two limbs, sequential | Accumulator, one limb | Accumulator, two limbs |
|---|---|---|---|---|---|---|
| positive, n = 10 | 17 (5.2), exact in 2 of 20 | 16 (5.5), exact in 1 of 20 | –, exact in 20 of 20 | –, exact in 20 of 20 | 18 (6.1), exact in 1 of 20 | –, exact in 20 of 20 |
| positive, n = 100 | 2.2e+02 (55) | 64 (15) | –, exact in 20 of 20 | –, exact in 20 of 20 | 65 (15) | –, exact in 20 of 20 |
| positive, n = 1000 | 1.2e+03 (3e+02) | 2.2e+02 (67) | –, exact in 20 of 20 | –, exact in 20 of 20 | 2.2e+02 (67) | –, exact in 20 of 20 |
| positive, n = 10000 | 2.5e+03 (1.4e+03) | 5.3e+02 (2.5e+02) | –, exact in 10 of 10 | –, exact in 10 of 10 | 5.3e+02 (2.5e+02) | –, exact in 10 of 10 |
| positive, n = 100000 | 5.6e+03 (4.6e+03) | 3.1e+03 (7.7e+02) | –, exact in 4 of 4 | –, exact in 4 of 4 | 3.1e+03 (7.7e+02) | –, exact in 4 of 4 |
| positive, n = 1000000 | 2.2e+04 (9.6e+03) | 5.9e+03 (2.4e+03) | –, exact in 4 of 4 | –, exact in 4 of 4 | 5.9e+03 (2.4e+03) | –, exact in 4 of 4 |
| random signs, n = 10 | 19 (8.7), exact in 14 of 20 | 24 (13), exact in 15 of 20 | –, exact in 20 of 20 | –, exact in 20 of 20 | 27 (14), exact in 15 of 20 | –, exact in 20 of 20 |
| random signs, n = 100 | 6.5e+02 (2.8e+02), exact in 5 of 20 | 6.5e+02 (1.5e+02), exact in 1 of 20 | –, exact in 20 of 20 | –, exact in 20 of 20 | 6.5e+02 (1.5e+02), exact in 1 of 20 | –, exact in 20 of 20 |
| random signs, n = 1000 | 1e+04 (1.6e+03) | 3.7e+03 (1.3e+03) | –, exact in 20 of 20 | –, exact in 20 of 20 | 3.7e+03 (1.3e+03) | –, exact in 20 of 20 |
| random signs, n = 10000 | 5.5e+04 (2.8e+04) | 5.7e+04 (1.4e+04) | –, exact in 10 of 10 | –, exact in 10 of 10 | 5.7e+04 (1.4e+04) | –, exact in 10 of 10 |
| random signs, n = 100000 | 8.5e+05 (5.6e+05) | 1.9e+06 (6.7e+05) | –, exact in 4 of 4 | –, exact in 4 of 4 | 1.9e+06 (6.7e+05) | –, exact in 4 of 4 |
| random signs, n = 1000000 | 1.1e+07 (2.3e+06) | 4.3e+06 (3.6e+06) | –, exact in 4 of 4 | –, exact in 4 of 4 | 4.3e+06 (3.6e+06) | –, exact in 4 of 4 |
| condition 1e4 to 1e40, n = 10 | 1.1e+02 (9.3) | 56 (10) | 1.2e+03 (37), exact in 14 of 200 | 6.6e+02 (43), exact in 9 of 200 | 62 (11) | 9.8e+02 (64), exact in 9 of 200 |
| condition 1e4 to 1e40, n = 100 | 3.4e+02 (39) | 2.6e+02 (41) | 1.5e+03 (2.7e+02) | 1.1e+03 (1.4e+02) | 2.6e+02 (41) | 1.5e+03 (1.9e+02) |
| condition 1e4 to 1e40, n = 1000 | 1.7e+03 (2.9e+02) | 1.5e+03 (1.8e+02) | 8.2e+03 (1.3e+03) | 7.2e+03 (7.3e+02) | 1.5e+03 (1.8e+02) | 9.6e+03 (9.8e+02) |
| condition 1e4 to 1e40, n = 10000 | 1.3e+04 (2.1e+03) | 1.3e+04 (1.5e+03) | 5.7e+04 (1.3e+04) | 5.2e+04 (7.6e+03) | 1.3e+04 (1.5e+03) | 7e+04 (1e+04) |
| condition 1e4 to 1e40, n = 100000 | 1.5e+05 (1.7e+04) | 1.4e+05 (1.9e+04) | 5.2e+05 (3.9e+04) | 4.8e+05 (1.2e+05) | 1.4e+05 (1.9e+04) | 6.4e+05 (1.6e+05) |
| condition 1e4 to 1e40, n = 1000000 | 1.5e+06 (1.6e+05) | 1.3e+06 (2.9e+05) | 6.1e+06 (7.5e+05) | 3.7e+06 (5.6e+05) | 1.3e+06 (2.9e+05) | 5e+06 (7.5e+05) |

| Dot products, linux (4 lanes): relative error, median over the trials, by condition | naive loop | Kairn, one limb | Dot2 | Kairn, two limbs | Accumulator, two limbs |
|---|---|---|---|---|---|
| n = 1000, condition 1e0 to 1e3 (40 trials) | 8.5e-16 | 3.7e-16 | 4.8e-17 | 1.7e-32 | 4.6e-32 |
| n = 1000, condition 1e4 to 1e7 (20 trials) | 2.8e-11 | 2.8e-11 | 3.0e-17 | 2.6e-27 | 2.5e-27 |
| n = 1000, condition 1e8 to 1e11 (20 trials) | 2.1e-07 | 2.2e-07 | 4.9e-17 | 7.6e-24 | 1.8e-23 |
| n = 1000, condition 1e12 to 1e15 (20 trials) | 3.1e-03 | 1.8e-03 | 4.4e-17 | 7.3e-20 | 1.2e-19 |
| n = 1000, condition 1e16 to 1e19 (20 trials) | 9.6e+00 | 9.8e+00 | 7.7e-15 | 1.4e-15 | 1.2e-15 |
| n = 1000, condition 1e20 to 1e23 (20 trials) | 8.1e+04 | 8.6e+04 | 7.7e-11 | 3.1e-12 | 2.7e-12 |
| n = 1000, condition 1e24 to 1e27 (20 trials) | 1.4e+09 | 1.6e+09 | 1.1e-06 | 9.3e-08 | 1.6e-07 |
| n = 1000, condition 1e28 to 1e31 (20 trials) | 7.4e+12 | 7.1e+12 | 5.7e-03 | 7.0e-04 | 6.3e-04 |
| n = 1000, condition 1e32 to 1e35 (20 trials) | 6.8e+16 | 7.4e+16 | 3.1e+01 | 3.0e+00 | 8.2e+00 |
| n = 1000, condition 1e36 to 1e39 (20 trials) | 4.5e+20 | 3.4e+20 | 7.0e+05 | 4.7e+04 | 1.6e+05 |
| n = 1000, condition 1e40 to 1e43 (20 trials) | 4.0e+24 | 5.0e+24 | 3.7e+09 | 4.0e+08 | 2.2e+08 |
| n = 1000000, condition 1e0 to 1e3 (8 trials) | 1.8e-14 | 1.4e-14 | 2.8e-17 | 5.8e-31 | 1.8e-30 |
| n = 1000000, condition 1e8 to 1e11 (5 trials) | 6.3e-08 | 4.3e-08 | 3.7e-17 | 1.5e-24 | 6.4e-24 |
| n = 1000000, condition 1e12 to 1e15 (5 trials) | 3.3e-04 | 1.0e-03 | 2.4e-17 | 3.7e-20 | 2.4e-20 |
| n = 1000000, condition 1e16 to 1e19 (4 trials) | 1.0e+03 | 1.8e+03 | 2.5e-10 | 2.1e-13 | 8.2e-14 |
| n = 1000000, condition 1e20 to 1e23 (3 trials) | 9.6e+04 | 2.2e+04 | 3.9e-09 | 7.0e-12 | 5.9e-12 |
| n = 1000000, condition 1e24 to 1e27 (6 trials) | 6.8e+10 | 1.0e+11 | 6.9e-04 | 2.3e-05 | 8.0e-06 |
| n = 1000000, condition 1e28 to 1e31 (3 trials) | 1.6e+15 | 2.7e+14 | 1.1e+01 | 2.1e-01 | 4.5e-02 |
| n = 1000000, condition 1e32 to 1e35 (6 trials) | 2.3e+19 | 7.6e+19 | 3.7e+05 | 5.5e+03 | 3.8e+03 |
| n = 1000000, condition 1e36 to 1e39 (4 trials) | 1.9e+23 | 6.3e+22 | 4.3e+09 | 1.1e+07 | 4.2e+07 |
| n = 1000000, condition 1e40 to 1e43 (4 trials) | 2.7e+27 | 4.3e+27 | 1.1e+14 | 4.5e+11 | 2.6e+11 |

| Dot products, linux: the stated bound over the error made, median (smallest) over the trials | Kairn, one limb | one limb, sequential | two limbs | two limbs, sequential | Accumulator, one limb | Accumulator, two limbs |
|---|---|---|---|---|---|---|
| positive, n = 10 | 19 (6.1) | 27 (6.1) | 1e+02 (35), exact in 6 of 20 | 98 (35), exact in 3 of 20 | 27 (6.1) | 98 (35), exact in 3 of 20 |
| positive, n = 100 | 1.7e+02 (55) | 1.2e+02 (16) | 2e+03 (4.8e+02), exact in 1 of 20 | 4.7e+02 (1e+02) | 1.2e+02 (16) | 4.7e+02 (1e+02) |
| positive, n = 1000 | 6.4e+02 (2.2e+02) | 1.9e+02 (50) | 5.1e+03 (1.3e+03) | 1.2e+03 (3.8e+02) | 1.9e+02 (50) | 1.2e+03 (3.8e+02) |
| positive, n = 10000 | 4.5e+03 (9.6e+02) | 5.7e+02 (2.6e+02) | 1.4e+04 (6.8e+03) | 3.9e+03 (8.7e+02) | 5.7e+02 (2.6e+02) | 3.9e+03 (8.7e+02) |
| positive, n = 100000 | 5.7e+03 (3.1e+03) | 1.8e+03 (1.5e+03) | 2.9e+05 (3.4e+04) | 1.6e+05 (1.1e+04) | 1.8e+03 (1.5e+03) | 1.6e+05 (1.1e+04) |
| positive, n = 1000000 | 1.3e+05 (6e+03) | 9.7e+03 (3.1e+03) | 1e+05 (5.8e+04) | 2.8e+04 (2e+04) | 9.7e+03 (3.1e+03) | 2.8e+04 (2e+04) |
| random signs, n = 10 | 56 (7.2) | 68 (20) | –, exact in 20 of 20 | –, exact in 20 of 20 | 68 (20) | –, exact in 20 of 20 |
| random signs, n = 100 | 6.7e+02 (2.9e+02) | 6.2e+02 (1.2e+02) | 2.5e+03 (2.1e+03), exact in 16 of 20 | 2.3e+03 (1.3e+03), exact in 15 of 20 | 6.2e+02 (1.2e+02) | 2.3e+03 (1.3e+03), exact in 15 of 20 |
| random signs, n = 1000 | 6.3e+03 (2e+03) | 5.8e+03 (1.5e+03) | 8.4e+04 (1.9e+04), exact in 2 of 20 | 4.9e+04 (6.7e+03), exact in 2 of 20 | 5.8e+03 (1.5e+03) | 4.9e+04 (6.7e+03), exact in 2 of 20 |
| random signs, n = 10000 | 1.9e+05 (2e+04) | 4.1e+04 (7.9e+03) | 8.6e+05 (1.5e+05) | 5.4e+05 (1.5e+05) | 4.1e+04 (7.9e+03) | 5.4e+05 (1.5e+05) |
| random signs, n = 100000 | 2.8e+06 (6.1e+05) | 4.6e+05 (1e+05) | 3.1e+06 (2.6e+06) | 2e+06 (8.3e+05) | 4.6e+05 (1e+05) | 2e+06 (8.3e+05) |
| random signs, n = 1000000 | 3.7e+06 (2.2e+06) | 9.4e+06 (2e+06) | 9.1e+07 (1.7e+07) | 5.6e+07 (1.2e+07) | 9.4e+06 (2e+06) | 5.6e+07 (1.2e+07) |
| condition 1e4 to 1e40, n = 10 | 46 (9.3) | 47 (10) | 3.8e+02 (36), exact in 1 of 200 | 3.9e+02 (42) | 47 (10) | 3.9e+02 (42) |
| condition 1e4 to 1e40, n = 100 | 3e+02 (40) | 2.4e+02 (30) | 1.5e+03 (2e+02) | 1.3e+03 (1.9e+02) | 2.4e+02 (30) | 1.3e+03 (1.9e+02) |
| condition 1e4 to 1e40, n = 1000 | 1.4e+03 (1.8e+02) | 1.3e+03 (1.5e+02) | 9.5e+03 (8.6e+02) | 7.2e+03 (8e+02) | 1.3e+03 (1.5e+02) | 7.2e+03 (8e+02) |
| condition 1e4 to 1e40, n = 10000 | 1.3e+04 (2.2e+03) | 1.1e+04 (1.8e+03) | 8.7e+04 (9.6e+03) | 6.1e+04 (8.1e+03) | 1.1e+04 (1.8e+03) | 6.1e+04 (8.1e+03) |
| condition 1e4 to 1e40, n = 100000 | 1.6e+05 (3.2e+04) | 1.5e+05 (3.4e+04) | 7.1e+05 (1.8e+05) | 4.9e+05 (1.3e+05) | 1.5e+05 (3.4e+04) | 4.9e+05 (1.3e+05) |
| condition 1e4 to 1e40, n = 1000000 | 2.2e+06 (3.1e+05) | 1.3e+06 (2.4e+05) | 7.4e+06 (1.8e+06) | 5.2e+06 (7e+05) | 1.3e+06 (2.4e+05) | 5.2e+06 (7e+05) |

#### Question 18: ball vectors

| BallVector: ns per operation on the whole vector | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, 1 limb, N = 4 | 9.79 to 9.97 (-O2), 9.37 to 9.57 (-O3) | 8.44 to 8.63 |
| `add`, 1 limb, N = 8 | 10.5 to 10.7 (-O2), 9.91 to 10.1 (-O3) | 8.96 to 9.14 |
| `add`, 1 limb, N = 16 | 12.8 to 13 (-O2), 11.2 to 11.4 (-O3) | 9.47 to 9.72 |
| `add`, 1 limb, N = 64 | 28 to 28.9 (-O2), 20.1 to 20.6 (-O3) | 19.6 to 20 (-O2), 17.8 to 18.1 (-O3) |
| `add`, 2 limbs, N = 4 | 20.9 to 21.1 (-O2), 13 to 13.3 (-O3) | 10.5 to 10.7 |
| `add`, 2 limbs, N = 8 | 23.1 to 23.6 (-O2), 15.9 to 16.3 (-O3) | 15.2 to 15.5 |
| `add`, 2 limbs, N = 16 | 31 to 31.7 (-O2), 25.2 to 25.7 (-O3) | 23.2 to 23.9 |
| `add`, 2 limbs, N = 64 | 84.6 to 87.2 | 81.1 to 83.1 |
| `sub`, 1 limb, N = 4 | 9.78 to 9.95 (-O2), 9.41 to 9.63 (-O3) | 8.44 to 8.63 |
| `sub`, 1 limb, N = 8 | 10.4 to 10.6 (-O2), 9.91 to 10.1 (-O3) | 8.96 to 9.17 |
| `sub`, 1 limb, N = 16 | 12.7 to 12.9 (-O2), 11.1 to 11.4 (-O3) | 9.47 to 9.68 |
| `sub`, 1 limb, N = 64 | 25.7 to 26 (-O2), 20.2 to 20.6 (-O3) | 19.6 to 20 (-O2), 17.8 to 18.1 (-O3) |
| `sub`, 2 limbs, N = 4 | 20.8 to 21 (-O2), 13.1 to 13.4 (-O3) | 10.7 to 11 |
| `sub`, 2 limbs, N = 8 | 23.3 to 23.6 (-O2), 16 to 16.4 (-O3) | 15.7 to 16.1 |
| `sub`, 2 limbs, N = 16 | 31.4 to 31.9 (-O2), 25.4 to 25.9 (-O3) | 25.7 to 26.2 (-O2), 24.3 to 24.7 (-O3) |
| `sub`, 2 limbs, N = 64 | 87.4 to 88.9 (-O2), 83.3 to 85.5 (-O3) | 83.1 to 85.3 |
| `scale`, 1 limb, N = 4 | 9.9 to 10.1 (-O2), 9.37 to 9.59 (-O3) | 8.48 to 8.66 |
| `scale`, 1 limb, N = 8 | 11.3 to 11.6 (-O2), 9.96 to 10.2 (-O3) | 9 to 9.17 |
| `scale`, 1 limb, N = 16 | 13 to 13.2 (-O2), 11.1 to 11.5 (-O3) | 9.48 to 9.74 |
| `scale`, 1 limb, N = 64 | 26.1 to 26.7 (-O2), 20.9 to 21.5 (-O3) | 18.5 to 18.9 (-O2), 18.4 to 22.5 (-O3) |
| `scale`, 2 limbs, N = 4 | 17.1 to 17.3 (-O2), 9.99 to 10.2 (-O3) | 8.99 to 9.19 |
| `scale`, 2 limbs, N = 8 | 18.6 to 19 (-O2), 11.9 to 12.1 (-O3) | 9.92 to 10.1 |
| `scale`, 2 limbs, N = 16 | 21.6 to 21.9 (-O2), 14.8 to 15.2 (-O3) | 13 to 13.5 |
| `scale`, 2 limbs, N = 64 | 45.9 to 46.7 (-O2), 43.3 to 44.1 (-O3) | 37.4 to 38.4 |
| `axpy`, 1 limb, N = 4 | 18 to 18.7 (-O2), 16.5 to 16.9 (-O3) | 14.1 to 15 (-O2), 14.1 to 14.6 (-O3) |
| `axpy`, 1 limb, N = 8 | 25.4 to 25.9 (-O2), 18 to 18.4 (-O3) | 15.6 to 16.3 |
| `axpy`, 1 limb, N = 16 | 32.4 to 33.3 (-O2), 22.1 to 22.6 (-O3) | 17.3 to 18.1 (-O2), 18.1 to 18.3 (-O3) |
| `axpy`, 1 limb, N = 64 | 50.3 to 51.3 (-O2), 43 to 44.2 (-O3) | 33.9 to 34.6 (-O2), 34.2 to 36.4 (-O3) |
| `axpy`, 2 limbs, N = 4 | 41.8 to 42.3 (-O2), 23.6 to 24.2 (-O3) | 20.7 to 21.1 (-O2), 20 to 20.5 (-O3) |
| `axpy`, 2 limbs, N = 8 | 45.8 to 46.4 (-O2), 31.9 to 32.5 (-O3) | 25.1 to 26.1 |
| `axpy`, 2 limbs, N = 16 | 56.5 to 57.4 (-O2), 44.9 to 46.1 (-O3) | 36.3 to 37.5 |
| `axpy`, 2 limbs, N = 64 | 131 to 133 (-O2), 125 to 128 (-O3) | 113 to 116 |
| `conv`, 1 limb, N = 4 | 33.4 to 33.9 (-O2), 30.5 to 31.2 (-O3) | 41.3 to 42.3 (-O2), 20.2 to 20.4 (-O3) |
| `conv`, 1 limb, N = 8 | 86.9 to 89.7 (-O2), 62.8 to 64.3 (-O3) | 75.4 to 77.8 |
| `conv`, 1 limb, N = 16 | 277 to 281 (-O2), 194 to 198 (-O3) | 193 to 198 |
| `conv`, 1 limb, N = 64 | 3913 to 4036 | 3023 to 3089 |
| `conv`, 2 limbs, N = 4 | 138 to 143 | 142 to 146 |
| `conv`, 2 limbs, N = 8 | 575 to 588 | 583 to 597 |
| `conv`, 2 limbs, N = 16 | 2455 to 2509 | 2432 to 2495 |
| `conv`, 2 limbs, N = 64 | 41060 to 42030 | 41160 to 42080 |
| `norm`, 1 limb, N = 4 | 8.43 to 8.65 | 8.46 to 8.66 |
| `norm`, 1 limb, N = 8 | 8.79 to 9.18 | 8.61 to 8.84 |
| `norm`, 1 limb, N = 16 | 9.5 to 9.71 (-O2), 9.09 to 9.32 (-O3) | 8.87 to 9.07 |
| `norm`, 1 limb, N = 64 | 15.1 to 15.3 (-O2), 13.3 to 13.6 (-O3) | 14.3 to 14.7 (-O2), 14.5 to 31.9 (-O3) |
| `norm`, 2 limbs, N = 4 | 9.41 to 9.57 (-O2), 9.06 to 9.23 (-O3) | 9.4 to 9.62 |
| `norm`, 2 limbs, N = 8 | 9.41 to 9.74 | 9.4 to 9.6 |
| `norm`, 2 limbs, N = 16 | 10.9 to 11.1 (-O2), 10 to 10.1 (-O3) | 9.84 to 10.1 |
| `norm`, 2 limbs, N = 64 | 23.2 to 23.6 (-O2), 15.7 to 16 (-O3) | 15.3 to 15.6 |

| N balls over one BallVector | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, 1 limb, N = 4 | 0.84 (-O2), 1.54 (-O3) | 0.77 |
| `add`, 1 limb, N = 8 | 1.53 (-O2), 1.47 to 1.50 (-O3) | 1.61 to 1.62 (-O2), 1.44 (-O3) |
| `add`, 1 limb, N = 16 | 2.50 to 2.51 (-O2), 2.66 to 2.67 (-O3) | 2.99 to 3.02 |
| `add`, 1 limb, N = 64 | 4.49 to 4.55 (-O2), 5.83 to 5.85 (-O3) | 5.77 to 5.78 (-O2), 6.09 to 6.12 (-O3) |
| `add`, 2 limbs, N = 4 | 1.15 to 1.16 (-O2), 1.84 to 1.85 (-O3) | 2.05 to 2.09 |
| `add`, 2 limbs, N = 8 | 2.06 to 2.08 (-O2), 2.78 to 2.80 (-O3) | 2.88 to 2.89 |
| `add`, 2 limbs, N = 16 | 3.08 to 3.11 (-O2), 2.70 to 2.71 (-O3) | 3.73 to 3.76 |
| `add`, 2 limbs, N = 64 | 4.46 to 4.48 (-O2), 4.14 to 4.18 (-O3) | 4.29 to 4.35 |
| `sub`, 1 limb, N = 4 | 0.84 (-O2), 1.54 to 1.55 (-O3) | 0.77 |
| `sub`, 1 limb, N = 8 | 1.53 to 1.54 (-O2), 1.47 to 1.49 (-O3) | 1.60 to 1.61 (-O2), 1.44 to 1.45 (-O3) |
| `sub`, 1 limb, N = 16 | 2.51 to 2.52 (-O2), 2.66 to 2.67 (-O3) | 3.00 to 3.03 |
| `sub`, 1 limb, N = 64 | 4.95 to 4.97 (-O2), 5.86 to 5.89 (-O3) | 5.75 to 5.77 (-O2), 6.18 to 6.19 (-O3) |
| `sub`, 2 limbs, N = 4 | 1.18 (-O2), 1.86 to 1.87 (-O3) | 2.09 to 2.10 |
| `sub`, 2 limbs, N = 8 | 2.08 to 2.09 (-O2), 2.41 to 2.45 (-O3) | 2.84 to 2.87 |
| `sub`, 2 limbs, N = 16 | 3.09 (-O2), 2.69 (-O3) | 3.51 to 3.52 (-O2), 3.70 to 3.71 (-O3) |
| `sub`, 2 limbs, N = 64 | 4.44 to 4.45 (-O2), 3.29 to 3.30 (-O3) | 4.30 to 4.33 |
| `scale`, 1 limb, N = 4 | 0.85 (-O2), 1.21 (-O3) | 0.72 |
| `scale`, 1 limb, N = 8 | 1.45 to 1.46 (-O2), 1.37 to 1.38 (-O3) | 1.35 to 1.36 |
| `scale`, 1 limb, N = 16 | 2.55 to 2.56 (-O2), 2.44 to 2.47 (-O3) | 2.72 to 2.75 |
| `scale`, 1 limb, N = 64 | 5.14 to 5.17 (-O2), 5.24 to 5.31 (-O3) | 5.58 to 5.60 (-O2), 4.48 to 5.42 (-O3) |
| `scale`, 2 limbs, N = 4 | 0.78 to 0.79 (-O2), 1.33 (-O3) | 1.27 to 1.28 |
| `scale`, 2 limbs, N = 8 | 1.44 (-O2), 1.99 to 2.00 (-O3) | 2.31 to 2.32 |
| `scale`, 2 limbs, N = 16 | 2.49 to 2.50 (-O2), 3.33 to 3.34 (-O3) | 3.50 to 3.56 |
| `scale`, 2 limbs, N = 64 | 4.65 to 4.68 (-O2), 4.18 to 4.20 (-O3) | 4.90 to 4.96 |
| `axpy`, 1 limb, N = 4 | 0.89 to 0.91 (-O2), 0.71 (-O3) | 0.88 to 0.92 |
| `axpy`, 1 limb, N = 8 | 1.27 to 1.31 | 1.65 to 1.66 (-O2), 1.58 to 1.65 (-O3) |
| `axpy`, 1 limb, N = 16 | 1.98 to 2.00 (-O2), 2.11 to 2.21 (-O3) | 2.91 to 2.98 (-O2), 2.81 to 2.89 (-O3) |
| `axpy`, 1 limb, N = 64 | 5.16 to 5.18 (-O2), 4.38 to 4.43 (-O3) | 6.09 to 6.11 (-O2), 5.69 to 6.09 (-O3) |
| `axpy`, 2 limbs, N = 4 | 0.99 to 1.00 (-O2), 1.19 to 1.23 (-O3) | 1.86 to 1.90 (-O2), 1.92 to 1.93 (-O3) |
| `axpy`, 2 limbs, N = 8 | 1.81 to 1.82 (-O2), 1.88 to 1.89 (-O3) | 3.03 to 3.09 |
| `axpy`, 2 limbs, N = 16 | 2.95 (-O2), 2.55 to 2.56 (-O3) | 4.21 to 4.26 |
| `axpy`, 2 limbs, N = 64 | 5.07 to 5.08 (-O2), 3.76 to 3.77 (-O3) | 5.46 to 5.47 |
| `conv`, 1 limb, N = 4 | 2.16 to 2.17 (-O2), 2.37 (-O3) | 1.44 to 1.45 (-O2), 2.94 to 2.97 (-O3) |
| `conv`, 1 limb, N = 8 | 3.20 to 3.36 (-O2), 4.57 to 4.58 (-O3) | 3.14 to 3.18 |
| `conv`, 1 limb, N = 16 | 4.05 to 4.09 (-O2), 5.81 to 5.84 (-O3) | 5.05 to 5.11 |
| `conv`, 1 limb, N = 64 | 4.60 to 4.63 | 5.41 to 5.44 |
| `conv`, 2 limbs, N = 4 | 0.96 to 0.98 | 0.85 to 0.86 |
| `conv`, 2 limbs, N = 8 | 1.05 to 1.06 | 0.97 |
| `conv`, 2 limbs, N = 16 | 1.07 to 1.08 | 1.01 to 1.02 |
| `conv`, 2 limbs, N = 64 | 1.09 | 1.02 to 1.03 |
| `norm`, 1 limb, N = 4 | 1.67 to 1.71 | 2.08 to 2.09 (-O2), 2.14 to 2.15 (-O3) |
| `norm`, 1 limb, N = 8 | 3.20 to 3.27 | 3.99 to 4.02 |
| `norm`, 1 limb, N = 16 | 5.87 to 5.98 (-O2), 6.25 to 6.27 (-O3) | 7.68 to 7.73 |
| `norm`, 1 limb, N = 64 | 14.6 to 15.2 (-O2), 17.2 to 17.4 (-O3) | 19.4 to 19.5 (-O2), 8.8 to 19.5 (-O3) |
| `norm`, 2 limbs, N = 4 | 2.35 to 2.36 (-O2), 2.44 to 2.45 (-O3) | 3.59 to 3.61 |
| `norm`, 2 limbs, N = 8 | 4.55 to 4.63 | 7.11 to 7.18 |
| `norm`, 2 limbs, N = 16 | 7.94 to 8.00 (-O2), 8.70 to 8.85 (-O3) | 13.6 |
| `norm`, 2 limbs, N = 64 | 14.7 to 14.9 (-O2), 22.0 to 22.1 (-O3) | 35.2 to 35.6 (-O2), 34.5 to 34.8 (-O3) |

| BallVector: kairn::sequential over the default order | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, 1 limb, N = 4 | 1.00 to 1.03 | 1.07 to 1.11 |
| `add`, 1 limb, N = 64 | 2.62 to 2.65 (-O2), 3.72 to 3.73 (-O3) | 2.25 to 2.26 (-O2), 2.45 to 2.46 (-O3) |
| `add`, 2 limbs, N = 4 | 1.11 (-O2), 1.76 (-O3) | 2.44 to 2.46 |
| `add`, 2 limbs, N = 64 | 3.42 to 3.48 | 3.48 to 3.50 |
| `scale`, 1 limb, N = 4 | 1.02 | 0.99 to 1.00 |
| `scale`, 1 limb, N = 64 | 2.82 to 2.86 (-O2), 3.50 to 3.53 (-O3) | 2.45 to 2.46 (-O2), 2.02 to 2.45 (-O3) |
| `scale`, 2 limbs, N = 4 | 0.80 to 0.81 (-O2), 1.29 to 1.30 (-O3) | 1.26 to 1.27 (-O2), 1.21 to 1.22 (-O3) |
| `scale`, 2 limbs, N = 64 | 2.93 to 2.95 (-O2), 3.11 to 3.12 (-O3) | 3.22 to 3.25 |
| `axpy`, 1 limb, N = 4 | 1.00 to 1.01 | 0.92 to 0.96 |
| `axpy`, 1 limb, N = 64 | 2.85 to 2.86 (-O2), 3.36 to 3.39 (-O3) | 2.45 to 2.46 (-O2), 2.27 to 2.44 (-O3) |
| `axpy`, 2 limbs, N = 4 | 1.12 to 1.14 (-O2), 1.52 to 1.55 (-O3) | 2.21 to 2.26 (-O2), 2.27 to 2.29 (-O3) |
| `axpy`, 2 limbs, N = 64 | 3.29 (-O2), 3.43 to 3.44 (-O3) | 3.57 to 3.58 |
| `norm`, 1 limb, N = 4 | 1.04 to 1.06 | 1.00 |
| `norm`, 1 limb, N = 64 | 3.62 to 3.65 (-O2), 4.35 to 4.52 (-O3) | 2.72 to 2.75 (-O2), 1.21 to 2.66 (-O3) |
| `norm`, 2 limbs, N = 4 | 1.06 to 1.10 | 1.06 to 1.07 |
| `norm`, 2 limbs, N = 64 | 2.52 to 2.57 (-O2), 3.98 to 4.03 (-O3) | 2.74 to 2.81 |

| BallVector: the public operation over its generated loop called directly | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| `add`, 1 limb, N = 4 | 1.24 (-O2), 1.37 (-O3) | 1.56 to 1.59 |
| `add`, 1 limb, N = 64 | 1.08 to 1.17 (-O2), 0.94 to 0.95 (-O3) | 0.95 to 0.99 |
| `add`, 2 limbs, N = 4 | 1.72 to 1.73 (-O2), 1.21 (-O3) | 1.20 to 1.21 |
| `add`, 2 limbs, N = 64 | 1.06 to 1.10 | 1.07 to 1.08 |
| `scale`, 1 limb, N = 4 | 1.25 (-O2), 1.40 (-O3) | 1.58 to 1.62 (-O2), 1.35 to 1.59 (-O3) |
| `scale`, 1 limb, N = 64 | 1.04 to 1.05 (-O2), 0.95 to 0.96 (-O3) | 0.92 to 0.95 (-O2), 0.77 to 1.17 (-O3) |
| `scale`, 2 limbs, N = 4 | 1.81 to 1.84 (-O2), 1.18 to 1.19 (-O3) | 1.38 to 1.40 |
| `scale`, 2 limbs, N = 64 | 1.10 to 1.15 | 1.05 to 1.07 |
| `axpy`, 1 limb, N = 4 | 1.12 to 1.13 (-O2), 1.17 to 1.18 (-O3) | 1.25 to 1.30 (-O2), 1.18 to 1.28 (-O3) |
| `axpy`, 1 limb, N = 64 | 1.00 to 1.07 (-O2), 1.11 to 1.12 (-O3) | 0.96 to 0.97 (-O2), 0.98 to 1.09 (-O3) |
| `axpy`, 2 limbs, N = 4 | 1.83 to 1.86 (-O2), 1.19 to 1.23 (-O3) | 1.24 to 1.26 (-O2), 1.17 to 1.23 (-O3) |
| `axpy`, 2 limbs, N = 64 | 1.05 to 1.09 | 1.01 to 1.02 |
| `conv`, 1 limb, N = 4 | 1.20 to 1.22 | 1.11 to 1.12 (-O2), 1.18 to 1.19 (-O3) |
| `conv`, 1 limb, N = 64 | 0.99 to 1.00 | 1.00 |
| `conv`, 2 limbs, N = 4 | 1.00 to 1.01 | 1.01 |
| `conv`, 2 limbs, N = 64 | 1.00 | 1.00 |
| `norm`, 1 limb, N = 4 | 1.92 to 1.94 (-O2), 2.29 to 2.30 (-O3) | 2.09 to 2.11 |
| `norm`, 1 limb, N = 64 | 1.03 to 1.08 (-O2), 1.15 (-O3) | 1.16 to 1.17 (-O2), 1.16 to 1.23 (-O3) |
| `norm`, 2 limbs, N = 4 | 1.43 to 1.44 (-O2), 1.64 to 1.65 (-O3) | 1.41 to 1.42 |
| `norm`, 2 limbs, N = 64 | 1.43 (-O2), 1.19 to 1.20 (-O3) | 1.20 to 1.23 |

| Bytes | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---:|---:|---:|---:|
| `BallVector<double, 1, N>` | 40 | 72 | 136 | 520 |
| `std::array<Ball<double, 1>, N>` | 64 | 128 | 256 | 1024 |
| `BallVector<double, 2, N>` | 72 | 136 | 264 | 1032 |
| `std::array<Ball<double, 2>, N>` | 96 | 192 | 384 | 1536 |

| The one radius over the largest of the balls' radii (radius 0) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 1 limb | 1 | 1 | 1 | 1 |
| `x - y`, 1 limb | 1 | 1 | 1 | 1 |
| `x a`, 1 limb | 1 | 1 | 1 | 1 |
| `a x + y`, 1 limb | 1 | 1.18 to 1.63 | 1 | 1.34 |
| product, 1 limb | 5.3 to 5.33 | 23 to 32 | 31.6 to 51.2 | 96.4 to 96.5 |
| Horner-like, 10, 1 limb | 1 | 1.09 to 1.12 | 1 to 1.16 | 1.16 to 1.17 |
| Horner-like, 100, 1 limb | 1 | 1.01 to 1.15 | 1 to 1.22 | 1.1 |
| de Casteljau-like, 10, 1 limb | 1.21 to 1.22 | 1.22 to 1.31 | 1.28 to 1.29 | 1.17 to 1.25 |
| de Casteljau-like, 100, 1 limb | 1.06 | 1.5 to 1.52 | 1.39 to 1.77 | 1.36 to 1.51 |
| `x + y`, 2 limbs | 1 | 1 | 1 | 1 |
| `x - y`, 2 limbs | 1 | 1 | 1 | 1 |
| `x a`, 2 limbs | 1 | 1 | 1 | 1 |
| `a x + y`, 2 limbs | 1 to 1.04 | 1 to 1.21 | 1.01 to 1.13 | 1.25 to 1.46 |
| product, 2 limbs | 6.39 to 6.4 | 15.3 to 36.5 | 29.6 to 118 | 86.7 to 106 |
| Horner-like, 10, 2 limbs | 1 | 1 to 1.12 | 1 to 1.07 | 1.15 to 1.17 |
| Horner-like, 100, 2 limbs | 1 | 1 to 1.16 | 1 to 1.09 | 1.1 to 1.18 |
| de Casteljau-like, 10, 2 limbs | 1.21 to 1.23 | 1.32 to 1.37 | 1.24 to 1.34 | 1.1 to 1.11 |
| de Casteljau-like, 100, 2 limbs | 1.05 to 1.06 | 1.65 to 1.75 | 1.49 to 1.8 | 1.31 to 1.48 |

| The one radius over the median of the balls' radii (radius 0) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 1 limb | 2.21 to 68.5 | 7.31 to 53.3 | 7.86 to 13.9 | 15.4 to 37.2 |
| `x - y`, 1 limb | 2.15 to 60.1 | 14 to 56.2 | 11.4 to 107 | 15.2 to 43.2 |
| `x a`, 1 limb | 2.18 to 3.38 | 104 to 165 | 12.3 to 75.4 | 210 to 308 |
| `a x + y`, 1 limb | 2.2 to 57.6 | 9.34 to 66 | 13.5 to 16.6 | 19 to 48.7 |
| product, 1 limb | 140 to 3.93e+03 | 142 to 1.32e+04 | 1.03e+03 to 3.74e+03 | 1.9e+03 to 2.88e+03 |
| Horner-like, 10, 1 limb | 2.21 to 67.2 | 7.37 to 61.1 | 9.6 to 13.8 | 17.2 to 41.6 |
| Horner-like, 100, 1 limb | 2.21 to 68.6 | 7.45 to 61.1 | 9.57 to 13.9 | 17.1 to 41.1 |
| de Casteljau-like, 10, 1 limb | 1.47 to 1.51 | 4 to 4.32 | 3.61 to 4.93 | 4.71 to 19.5 |
| de Casteljau-like, 100, 1 limb | 1.06 | 1.56 to 1.58 | 2.01 to 2.99 | 2.15 to 6.99 |
| `x + y`, 2 limbs | 22.2 to 579 | 2.85 to 4.43 | 7.97 to 45.7 | 22 to 23.1 |
| `x - y`, 2 limbs | 10.8 to 529 | 4.27 to 8.23 | 7.81 to 52.5 | 26.1 to 34.8 |
| `x a`, 2 limbs | 3.38 to 6.34 | 4.23 to 6.08 | 20.2 to 35.2 | 228 to 579 |
| `a x + y`, 2 limbs | 14.9 to 513 | 2.97 to 5.37 | 9.64 to 42.7 | 30.8 to 32.8 |
| product, 2 limbs | 95.4 to 282 | 305 to 1.92e+03 | 808 to 1.74e+03 | 1.81e+03 to 3.37e+03 |
| Horner-like, 10, 2 limbs | 18.1 to 546 | 2.91 to 4.98 | 8.8 to 44.1 | 25.5 to 28.4 |
| Horner-like, 100, 2 limbs | 19.9 to 592 | 2.82 to 5.14 | 8.59 to 46.4 | 24.2 to 26.7 |
| de Casteljau-like, 10, 2 limbs | 1.41 to 1.52 | 1.74 to 3.74 | 3.46 to 4.21 | 18.7 to 20.2 |
| de Casteljau-like, 100, 2 limbs | 1.05 to 1.06 | 1.75 to 1.85 | 2.28 to 2.62 | 10.8 to 13.1 |

| The one radius over the largest of the balls' radii (one radius 2^-22 for every entry) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 1 limb | 1 | 1 | 1 | 1 |
| `x - y`, 1 limb | 1 | 1 | 1 | 1 |
| `x a`, 1 limb | 1 | 1 | 1 | 1 |
| `a x + y`, 1 limb | 1 | 1 | 1 | 1 |
| product, 1 limb | 2.67 to 3.98 | 4.38 to 5.55 | 7.07 to 7.99 | 8.55 to 12.1 |
| Horner-like, 10, 1 limb | 1 | 1 | 1 | 1 |
| Horner-like, 100, 1 limb | 1 | 1 | 1 | 1 |
| de Casteljau-like, 10, 1 limb | 1 | 1 | 1 | 1 |
| de Casteljau-like, 100, 1 limb | 1 | 1 | 1 | 1 |
| `x + y`, 2 limbs | 1 | 1 | 1 | 1 |
| `x - y`, 2 limbs | 1 | 1 | 1 | 1 |
| `x a`, 2 limbs | 1 | 1 | 1 | 1 |
| `a x + y`, 2 limbs | 1 | 1 | 1 | 1 |
| product, 2 limbs | 2.38 to 3.86 | 5.23 to 6.55 | 5.38 to 7.88 | 8.08 to 9.29 |
| Horner-like, 10, 2 limbs | 1 | 1 | 1 | 1 |
| Horner-like, 100, 2 limbs | 1 | 1 | 1 | 1 |
| de Casteljau-like, 10, 2 limbs | 1 | 1 | 1 | 1 |
| de Casteljau-like, 100, 2 limbs | 1 | 1 | 1 | 1 |

| The one radius over the median of the balls' radii (one radius 2^-22 for every entry) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 1 limb | 1 | 1 | 1 | 1 |
| `x - y`, 1 limb | 1 | 1 | 1 | 1 |
| `x a`, 1 limb | 1 | 1 | 1 | 1 |
| `a x + y`, 1 limb | 1 | 1 | 1 | 1 |
| product, 1 limb | 4 to 4.74 | 8.41 to 10.8 | 14 to 14.1 | 16.7 to 23.6 |
| Horner-like, 10, 1 limb | 1 | 1 | 1 | 1 |
| Horner-like, 100, 1 limb | 1 | 1 | 1 | 1 |
| de Casteljau-like, 10, 1 limb | 1 | 1 | 1 | 1 |
| de Casteljau-like, 100, 1 limb | 1 | 1 | 1 | 1 |
| `x + y`, 2 limbs | 1 | 1 | 1 | 1 |
| `x - y`, 2 limbs | 1 | 1 | 1 | 1 |
| `x a`, 2 limbs | 1 | 1 | 1 | 1 |
| `a x + y`, 2 limbs | 1 | 1 | 1 | 1 |
| product, 2 limbs | 4 to 4.17 | 7.29 to 8.56 | 9.1 to 12.4 | 16 to 18.4 |
| Horner-like, 10, 2 limbs | 1 | 1 | 1 | 1 |
| Horner-like, 100, 2 limbs | 1 | 1 | 1 | 1 |
| de Casteljau-like, 10, 2 limbs | 1 | 1 | 1 | 1 |
| de Casteljau-like, 100, 2 limbs | 1 | 1 | 1 | 1 |

| The one radius over the largest of the balls' radii (radii from 2^-50 to 2^-20 of each center) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 1 limb | 1 | 1 | 1.09 to 1.28 | 1.04 to 1.49 |
| `x - y`, 1 limb | 1 | 1 | 1.09 to 1.28 | 1.04 to 1.49 |
| `x a`, 1 limb | 1 | 1 | 1 | 1 |
| `a x + y`, 1 limb | 1 | 1 | 1.06 to 1.19 | 1.02 to 1.71 |
| product, 1 limb | 4 | 8 to 8.28 | 16.8 to 18.6 | 65.6 to 85.6 |
| Horner-like, 10, 1 limb | 1 | 1 | 1.06 to 1.2 | 1.03 to 1.7 |
| Horner-like, 100, 1 limb | 1 | 1 | 1.06 to 1.19 | 1.02 to 1.71 |
| de Casteljau-like, 10, 1 limb | 3.09 to 3.2 | 3.16 to 3.19 | 3.16 to 3.19 | 3.19 |
| de Casteljau-like, 100, 1 limb | 3.83 to 4 | 7.42 to 7.61 | 8.04 to 8.67 | 8.06 to 8.62 |
| `x + y`, 2 limbs | 1 to 1.04 | 1 to 1.66 | 1.01 to 1.83 | 1.14 to 1.33 |
| `x - y`, 2 limbs | 1 to 1.04 | 1 to 1.66 | 1.01 to 1.83 | 1.14 to 1.33 |
| `x a`, 2 limbs | 1 | 1 | 1 | 1 |
| `a x + y`, 2 limbs | 1 to 1.06 | 1 to 1.95 | 1.01 to 1.82 | 1.09 to 1.47 |
| product, 2 limbs | 4 to 4.47 | 9.91 to 10.7 | 16 to 21.2 | 57 to 57.6 |
| Horner-like, 10, 2 limbs | 1 to 1.06 | 1 to 1.93 | 1.01 to 1.83 | 1.1 to 1.46 |
| Horner-like, 100, 2 limbs | 1 to 1.06 | 1 to 1.95 | 1.01 to 1.82 | 1.09 to 1.47 |
| de Casteljau-like, 10, 2 limbs | 3.17 to 3.2 | 3.2 | 2.94 to 3.01 | 2.97 to 3.2 |
| de Casteljau-like, 100, 2 limbs | 3.96 to 4 | 7.69 to 7.7 | 5.74 to 7.7 | 8.21 to 8.77 |

| The one radius over the median of the balls' radii (radii from 2^-50 to 2^-20 of each center) | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| `x + y`, 1 limb | 47.7 to 3.39e+03 | 1.77e+03 to 1.87e+06 | 5.08e+04 to 1e+05 | 1.05e+04 to 5.59e+04 |
| `x - y`, 1 limb | 47.7 to 3.39e+03 | 1.77e+03 to 1.87e+06 | 5.08e+04 to 1e+05 | 1.05e+04 to 5.59e+04 |
| `x a`, 1 limb | 47.8 to 6.12e+03 | 137 to 4.14e+03 | 2.46e+06 to 2.6e+07 | 9.11e+05 to 2.61e+06 |
| `a x + y`, 1 limb | 47.7 to 2.82e+03 | 1.77e+03 to 1.92e+06 | 4.74e+04 to 1.1e+05 | 9.6e+03 to 7.49e+04 |
| product, 1 limb | 78.5 to 302 | 1.04e+03 to 3.35e+03 | 2.8e+03 to 8.45e+03 | 1.38e+03 to 5.16e+03 |
| Horner-like, 10, 1 limb | 47.7 to 2.85e+03 | 1.77e+03 to 1.92e+06 | 4.75e+04 to 1.1e+05 | 9.64e+03 to 7.36e+04 |
| Horner-like, 100, 1 limb | 47.7 to 2.82e+03 | 1.77e+03 to 1.92e+06 | 4.74e+04 to 1.1e+05 | 9.6e+03 to 7.49e+04 |
| de Casteljau-like, 10, 1 limb | 3.83 to 4 | 10.1 to 10.4 | 72.9 to 118 | 251 to 283 |
| de Casteljau-like, 100, 1 limb | 3.83 to 4 | 7.69 to 7.89 | 14.2 to 15.7 | 44.2 to 50.1 |
| `x + y`, 2 limbs | 45.4 to 69.1 | 2.7e+03 to 1.73e+04 | 1.21e+03 to 4.55e+03 | 5.5e+04 to 1.5e+05 |
| `x - y`, 2 limbs | 45.4 to 69.1 | 2.7e+03 to 1.73e+04 | 1.21e+03 to 4.55e+03 | 5.5e+04 to 1.5e+05 |
| `x a`, 2 limbs | 210 to 2.94e+03 | 4.09e+04 to 5.45e+04 | 4.18e+03 to 1.5e+04 | 1.39e+06 to 9.45e+06 |
| `a x + y`, 2 limbs | 31.8 to 49.8 | 2.94e+03 to 2.1e+04 | 1.1e+03 to 4.37e+03 | 5.23e+04 to 1.44e+05 |
| product, 2 limbs | 51.5 to 3.38e+03 | 1.17e+03 to 5.86e+03 | 553 to 2.43e+03 | 1.86e+03 to 3.17e+03 |
| Horner-like, 10, 2 limbs | 32.3 to 50.6 | 2.93e+03 to 2.08e+04 | 1.1e+03 to 4.38e+03 | 5.24e+04 to 1.44e+05 |
| Horner-like, 100, 2 limbs | 31.8 to 49.8 | 2.94e+03 to 2.1e+04 | 1.1e+03 to 4.37e+03 | 5.23e+04 to 1.44e+05 |
| de Casteljau-like, 10, 2 limbs | 3.96 to 4 | 10.6 to 10.7 | 22.9 to 158 | 279 to 1.82e+03 |
| de Casteljau-like, 100, 2 limbs | 3.96 to 4 | 7.99 | 9.09 to 13.8 | 35.8 to 75.5 |

| The bound of every entry, `norm_upper`, over the balls' largest bound | N = 4 | N = 8 | N = 16 | N = 64 |
|---|---|---|---|---|
| exact, 1 limb | 1 | 1 | 1 | 1 |
| exact, 2 limbs | 1 | 1 | 1 | 1 |
| same, 1 limb | 1 | 1 | 1 | 1 |
| same, 2 limbs | 1 | 1 | 1 | 1 |
| spread, 1 limb | 1 | 1 | 1 | 1 |
| spread, 2 limbs | 1 | 1 | 1 | 1 |

#### Question 19: compile time

| Compile time of the headers, s (minimum wall time; -O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| an empty unit | 0.01; 0.01 | 0.04; 0.04 |
| `kairn/kairn.hpp` | 0.45; 0.45 | 0.70; 0.70 |
| `kairn/kairn.hpp`, as packed code | 0.44; 0.44 | 0.70; 0.70 |
| `kairn/accumulator.hpp` | 0.44; 0.44 | 0.70; 0.70 |
| `kairn/batch.hpp`, as packed code | 1.21; 1.21 | 1.57; 1.57 |
| `kairn/ball_vector.hpp`, as packed code | 1.26; 1.26 | 1.66; 1.66 |
| `kairn/kairn.hpp` and `kairn/batch.hpp`, as packed code | 1.24; 1.23 | 1.61; 1.61 |
| `kairn/kairn.hpp` and `kairn/ball_vector.hpp`, as packed code | 1.27; 1.26 | 1.66; 1.66 |

| arrays: compile time, s of processor time (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 1.60; 1.66 | 2.31; 2.52 |
| 100, calls | 0.22; 0.22 | 0.23; 0.23 |
| 1000, inline | 2.77; 2.85 | 8.85; 12.2 |
| 1000, calls | 3.49; 3.48 | 1.56; 1.58 |

| arrays: peak memory, MB (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 245; 247 | 159; 159 |
| 100, calls | 35; 35 | 103; 103 |
| 1000, inline | 304; 305 | 237; 279 |
| 1000, calls | 100; 101 | 129; 129 |

| arrays: object, KB (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 28; 28 | 59; 76 |
| 100, calls | 11; 11 | 13; 13 |
| 1000, inline | 88; 89 | 461; 652 |
| 1000, calls | 97; 97 | 111; 111 |

| ballvectors: compile time, s of processor time (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 1.72; 1.91 | 2.12; 2.12 |
| 100, calls | 0.05; 0.05 | 0.06; 0.06 |
| 1000, inline | 2.40; 3.12 | 4.37; 4.36 |
| 1000, calls | 0.31; 0.31 | 0.21; 0.20 |

| ballvectors: peak memory, MB (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 254; 264 | 164; 164 |
| 100, calls | 28; 29 | 97; 97 |
| 1000, inline | 287; 324 | 202; 202 |
| 1000, calls | 50; 51 | 106; 106 |

| ballvectors: object, KB (-O2; -O3) | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|
| 100, inline | 36; 43 | 47; 48 |
| 100, calls | 7; 7 | 7; 7 |
| 1000, inline | 112; 113 | 268; 276 |
| 1000, calls | 51; 51 | 52; 52 |
