# Benchmarks, the round-up interval

What the round-up interval of `<kairn/upward.hpp>` costs, measured on the shipped header
([the design page](../design/upward.md), [the concept page](../../concepts/upward.md)):
`kairn::upward::Interval<T>`, one interval of `double` or `float` in one register, computed under the
rounding mode upward; its functions on arrays; and its scopes. It exists only for speed, so every
measurement is next to the default `Interval<T, 1>`, which computes every directed bound under
rounding to nearest, and next to the classical interval with the rounding mode set once around a
loop (the props `fenv_loop` of the [Milestone 2 benchmarks](bench-milestone2.md#how-the-rounding-mode-props-honor-the-mode):
two plain numbers per interval, no special case), on the same operands. Requires the rounding mode
upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang
-frounding-math, MSVC /fp:strict): the files of the harness that include the header are compiled
with the option of the target `kairn::upward`, and no other file is.

Two machines, four compilers, `-O2` and `-O3`, at least three runs of each configuration on the M3
and four on Zen 2, and one short table of MSVC on a third machine, unpinned; 2026-11-27 (UTC), at
commit `e4328d39`, the tree of version 0.4.1 with the harness repaired. The first version of this
page measured a harness that slowed some of its own loops, at `4710839b`; [What changed](#what-changed)
says how, and gives the times before and after. The harness and the commands are in
[`bench/`](https://github.com/danielepanozzo/kairn/tree/main/bench) (its README, "The round-up
interval"); the measurements, one JSON file per run, in
[`results/upward/bench/`](https://github.com/danielepanozzo/kairn/tree/main/results/upward/bench), and
those of the first version in its directory `4710839b/`.

"M3", "Zen 2" and "i5" are the machines ([How it was measured](#how-it-was-measured)). A **loop**
is a loop of 256 independent operations over arrays in L1, timed per operation; a **chain** is a
dependent chain (a running sum, or a running product of factors near 1), timed per step. Each timed
function of the type holds one `kairn::upward::Scope` around its loop or chain, as a program holds
one around a region of many operations; **x16** is the same loop 16 times inside one scope (a chain
16 times as long), where the scope's share is a 16th. Every time is the minimum over 31 samples of
about 4 ms; every ratio or difference is taken within one run; a cell is the lowest and highest value
over the runs of a configuration, with `-O2` and `-O3` given apart where they differ by more than
0.05 or 3% (ratios), 5% (times) or 0.5 ns and 10% (differences). A function named in a table is one of
the harness, `BACKEND/KIND/KERNEL/VARIANT`: `upw` the type with `double`, `upwf` with `float`, `upws`
its scopes, `upwa` and `upwaf` its functions on arrays; `m2` and `m2f` the default types and the
props, `m2p` packed code of Milestone 2; the variants `native` (arrays of the type), `conv` (arrays
of the default `Interval<T, 1>`, converted in the loop), `op` (the default type's operators),
`kairn` (the generated kernel), `packed` (Kairn's packed kernel), `fenv_loop`.

## In short

- **This version replaces the first** ([What changed](#what-changed)). The program of the first
  version loaded the pointers of its arrays again in its loops; repaired, on the M3 the type's sums
  with Apple clang take 0.386 ns where that page gave 0.51 to 0.53, and the functions on arrays 0.92
  to 0.99 of the classical packed loop's time for sums where it gave 0.57 to 0.64. On arm64 a product
  of the type is about 10% faster with the shorter test of an empty operand of version 0.4.1. On Zen
  2 the shortest loops of the type, and a scope that changes the mode, took up to 2.4 times as long in
  one program as in another with the same instructions at other addresses.
- **In loops the type is 2.5 to 11 times faster than the default `Interval<double, 1>`.** A sum
  takes 0.39 to 1.41 ns against 1.8 to 4.5 ns, 2.5 to 7.5 times faster with one scope around each loop
  of 256 operations and 5.5 to 11 times with one scope around 16 such loops; a product 1.2 to 2.7 ns
  against 6.1 to 17 ns, 4.3 to 8.5 and 5.4 to 9.5 times. With MSVC (unpinned) 14 to 25 times, the
  default type being slow there (7.0 ns a sum, 21 a product)
  ([question 1](#1-the-type-against-the-default-interval)).
- **In dependent computations, 2.1 to 22 times.** A chain of sums 3.8 to 8.3 times faster (0.65 to
  1.49 ns a step), a chain of products 2.1 to 6.2 times (3.0 to 4.5 ns a step); Horner of degree 8 6.6
  to 9.2 times on independent arguments and 2.5 to 6.2 times on dependent ones; the 3 by 3 determinant
  of coordinate differences (the sign filter of an orientation test) 8.4 to 22 times, 12 to 24 ns
  against 101 to 492 ns, where `Ball<double, 1>` takes 1.6 to 2.6 times the type and
  `Interval<double, 2>` 37 to 58 times.
- **It runs as fast as the classical interval under a mode set once around the loop, or faster**,
  with every special case that the classical code (two plain numbers) does not handle: 0.37 to 0.96
  of its time for sums, 0.47 to 1.60 for products (slower, 1.1 to 1.6 times, where GCC vectorizes the
  classical loop), 0.92 to 0.98 for a long chain of sums, 0.63 to 0.92 for the determinant.
- **Converting from and to the default layout in the loop makes a loop 1.8 to 6.0 times slower**:
  0.65 to 0.89 ns more per sum (two conversions in, one out) and 0.88 to 1.17 per product on the M3,
  1.5 to 3.0 and 3.1 to 4.1 ns on Zen 2; a conversion alone takes 0.34 to 0.46 ns per interval on the
  M3 and 0.63 to 1.38 on Zen 2; in a chain, off the critical path, 0.08 to 0.11 ns per step on the M3
  ([question 2](#2-what-a-conversion-costs)).
- **The functions on arrays are 3.7 to 6.6 times faster than Kairn's packed interval kernels**: per
  interval 0.26 to 0.30 ns for a sum of `double` and 0.15 to 0.20 of `float`, 0.87 to 1.12 ns and 0.46
  to 0.62 for a product; and 0.18 to 0.29 of the time of the packed classical interval on Zen 2 for
  sums, 0.48 to 0.79 for products (on the M3 0.92 to 0.99 and 1.56 to 1.69)
  ([question 3](#3-the-functions-on-arrays)).
- **A scope that changes the mode costs 21 to 23 ns on the M3, 50 to 51 ns on Zen 2 and 9.5 ns with
  MSVC** (122 ns with GCC 13 at `-O3`, in a program where the code of that call lies elsewhere); the
  register-only scope of the functions on arrays 21 to 23, 19 to 20 and 9.3 ns: on Zen 2 the scope of
  the program also sets glibc's mode, 2.6 times the cost of the register's write. A scope inside
  another (nothing changes) costs nothing measurable on the M3 with Apple clang, 0.5 ns with GCC 16, 12
  to 14 ns on Zen 2 (5.3 to 5.5 the register-only one) and 2.8 ns (1.7) with MSVC; a `NearestScope`
  inside an upward region 26 to 29, 51 and 6.9 ns ([question 5](#5-the-scopes)).
- **A function on arrays pays its scope on every call from code that rounds to nearest**: 23 to 26
  ns on the M3 and 17 to 20 ns on Zen 2 on 4 elements, 72 to 95% of the call. The scope is about 10% of
  a call or less from 256 elements on Zen 2 (sums 2 to 11%, products 5 to 6%), and under 10% on the M3
  from 256 for products (9%) and from 1024 for sums (7 to 9%). Inside an outer `Scope` its scope costs
  at most 0.5 ns on the M3 and 3 to 7 ns a call on Zen 2 on 4 elements
  ([question 4](#4-the-scope-of-a-function-on-arrays-by-length)).
- **`float` costs what `double` costs with the type** (0.84 to 1.38 of its time, 0.96 to 1.06 on the
  M3: one register holds either) **and half on arrays** (0.49 to 0.67: twice the lanes)
  ([question 6](#6-float)).
- **The checked build** (`KAIRN_CHECKS` 1) makes the type's loops of sums 4.4 to 22 times slower and
  of products 2.0 to 5.4 times, its chains of sums 2.4 to 9.9 times and of products 0.94 to 2.7, the
  functions on arrays 2.5 to 35 times: each operation reads the control register and tests its
  operands, which costs more than a sum; the default type's own checks cost its sums 1.7 to 3.6 times
  ([question 7](#7-the-checked-build)).

## What changed

The first version of this page measured the program at `4710839b`. A later measurement found that the
program slowed some of its own loops; the program was repaired, and every run of the page was made
again on 2026-11-27 at `e4328d39`, the tree of version 0.4.1, which also prints a shorter test for an
empty operand on arm64. The owner approved both changes on 2026-11-27
([log](../design/phase0/decisions.md#decisions-log)).

- **The program loaded the pointers of its arrays again in its loops.** Its units reached their arrays
  through pointers held in a structure on the heap. In the machine code of the program of the first
  version, Apple clang 21 and Clang 18 loaded those pointers again in every iteration of the type's
  loops over arrays: three per sum, difference or product, four per determinant, two per conversion,
  and with Apple clang one per step of the chains, which store nothing: as far as the compiler knew,
  a store of a result, or an operation under strict floating point, could have changed them. Every
  compiler loaded the six pointers of the classical packed loops and of Kairn's packed kernels on the
  placed arrays (`fenv_loop` and `packed` of the functions on arrays) in every iteration, after each
  store through an intrinsic, and the six of the calls of the functions on arrays by length before each
  call; every compiler loaded the three of the calls of the scopes after each call. GCC 13 and GCC 16
  kept the pointers of the type's own loops in registers (GCC 13 loaded them once per pass of the
  loops of 16 passes). Now each timed function copies the pointers into locals on entry, as a program's
  loop holds the pointers of its arrays: in the machine code of the four compilers at `-O2` and `-O3`,
  no loop of these units loads a pointer from the structure any more (GCC 13 at `-O2` keeps the six of
  the calls of `mul` by length in its stack frame across the call, as for any loop that keeps more
  values across a call than there are registers to keep them), and the rest of each loop does the same
  operations, its addressing and registers aside. Nothing else that is measured changed. The machine
  code of MSVC was not examined; its loop of sums too ran 1.7 to 1.8 times as fast after the change.
- **The test of an empty operand on arm64** (version 0.4.1, [the design page](../design/upward.md#the-printers)):
  in the NEON form of the kernels, "an operand is empty" (a NaN in a lane of either operand) is now
  the NaN test of the two operands' maximum, one `FMAX`, where it was two NaN tests and their or:
  three instructions where there were four or five, with the same results and the same exception
  flags for every input; the listings, the statements and the claims did not change. Measured alone,
  on two builds of the repaired program with the old test and the new, run alternately (the table
  below; `results/upward/bench/unord/`): the loops of products take 0.86 to 0.93 of their time, the
  products of the functions on arrays 0.87 to 0.96, the determinant 0.88 to 0.95, Horner on
  independent arguments 0.91 to 1.04; the chains, which wait for each product, and the controls (the
  sum, the default type's product) 0.93 to 1.08.
- **On the M3**, the sums and differences of the type with Apple clang went from 0.51 to 0.53 ns to
  0.386 ns, 1.3 to 1.4 times as fast, and their loops of 16 passes from 0.43 to 0.45 ns to 0.30 to 0.31;
  with GCC 16, which did not reload, from 0.39 to 0.386. The products, the determinant and Horner also
  have the shorter test: a product 1.17 ns with both compilers, where it was 1.31 to 1.44. The
  classical packed loops went from 0.52 to 0.56 ns per interval to 0.31 to 0.32 for sums, so that the
  functions on arrays now take 0.92 to 0.99 of their time for sums, where the first version gave 0.57 to
  0.64. On code that did not change, the default type's chains for example, the M3 ran up to 7%
  faster in this campaign than in the first, as its campaigns differ from one another.
- **On Zen 2**, with Clang 18 the loops of 16 passes of sums and differences went from 0.93 to 0.94 ns
  to 0.40 to 0.66 ns, and the classical packed loops of both compilers from 1.13 to 1.15 ns per
  interval to 0.92 to 0.94.
- **What did not come from the repair.** On Zen 2 some times moved in loops whose instructions did
  not change. Run alternately on one CPU with the program of the first version (the last table below;
  `results/upward/bench/placement/`): with GCC 13, which never reloaded a pointer in the type's loops,
  the loop of differences with one scope took 1.89 times as long at `-O2` and the loop of sums 2.37
  times as long at `-O3`, while the loop of sums at `-O2` took 0.73 to 0.92 of its time; and a call
  of one sum in a `Scope` that changes the mode took 2.4 times as long at `-O3` (124 ns a call in the
  runs of this page, 52 ns in the first), the function it calls being the same instructions at
  another address. With Clang 18 the conversion from the default type took 1.22 times as long and the
  converted loop of sums 1.10 times, though each lost two or three loads. In each case the loop is the
  same instructions in both programs, but for its registers, at another address. So on Zen 2 the
  shortest loops of the type, and a scope that changes the mode, can take up to 2.4 times as long in
  one program as in another by where their code lies, a cause not isolated further here (the
  alignment of the code is one candidate). The loops of 16 passes moved less (up to 1.33 times, GCC
  13's differences at `-O2`), the determinant, Horner and the default type's loops by a few percent
  at most; the loops of products with one scope varied from run to run (Clang 18 at `-O3`, 2.10 to
  2.65 ns over the four runs). The tables of this page give what this program measured.

<!-- BEGIN up_report changed -->

| Before and after the repair, times (ns per operation, per call for the calls) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/tp/interval_add_1/native`, at `4710839b` | 0.510 to 0.531 | 0.393 to 0.394 (-O2), 0.386 to 0.426 (-O3) | 0.818 to 0.822 (-O2), 0.593 (-O3) | 1.12 to 1.22 (-O2), 1.22 (-O3) |
| `upw/tp/interval_add_1/native`, now | 0.386 | 0.386 | 0.595 to 0.596 (-O2), 1.41 (-O3) | 0.599 to 0.712 (-O2), 0.821 to 0.979 (-O3) |
| `upw/tp/interval_add_1/native_x16`, at `4710839b` | 0.429 to 0.445 | 0.307 to 0.314 (-O2), 0.308 to 0.340 (-O3) | 0.637 to 0.640 (-O2), 0.399 to 0.426 (-O3) | 0.929 to 0.939 |
| `upw/tp/interval_add_1/native_x16`, now | 0.302 to 0.307 | 0.307 | 0.637 (-O2), 0.400 to 0.418 (-O3) | 0.636 to 0.655 (-O2), 0.402 to 0.430 (-O3) |
| `upw/tp/interval_sub_1/native`, at `4710839b` | 0.514 to 0.529 | 0.394 to 0.395 (-O2), 0.386 to 0.427 (-O3) | 0.674 to 0.676 (-O2), 0.817 to 0.940 (-O3) | 1.13 to 1.23 (-O2), 1.11 to 1.12 (-O3) |
| `upw/tp/interval_sub_1/native`, now | 0.386 | 0.385 to 0.386 | 1.27 (-O2), 1.26 to 1.41 (-O3) | 0.819 to 0.980 (-O2), 0.676 to 0.677 (-O3) |
| `upw/tp/interval_sub_1/native_x16`, at `4710839b` | 0.432 to 0.447 | 0.314 to 0.315 (-O2), 0.309 to 0.340 (-O3) | 0.489 to 0.491 (-O2), 0.637 to 0.664 (-O3) | 0.931 to 0.941 |
| `upw/tp/interval_sub_1/native_x16`, now | 0.297 to 0.307 | 0.307 to 0.308 | 0.637 to 0.650 | 0.637 to 0.638 (-O2), 0.545 to 0.562 (-O3) |
| `upw/tp/interval_mul_1/native`, at `4710839b` | 1.34 to 1.39 | 1.33 (-O2), 1.31 to 1.44 (-O3) | 1.98 to 1.99 (-O2), 1.98 to 2.10 (-O3) | 2.34 to 2.35 (-O2), 2.02 to 2.15 (-O3) |
| `upw/tp/interval_mul_1/native`, now | 1.17 | 1.17 to 1.18 | 2.09 (-O2), 1.98 to 2.27 (-O3) | 1.97 to 1.98 (-O2), 2.10 to 2.65 (-O3) |
| `upw/tp/interval_mul_1/native_x16`, at `4710839b` | 1.23 to 1.28 | 1.23 to 1.24 (-O2), 1.21 to 1.34 (-O3) | 1.79 to 1.80 | 1.84 to 1.86 |
| `upw/tp/interval_mul_1/native_x16`, now | 1.08 | 1.08 | 1.79 to 1.82 | 1.79 to 1.80 |
| `upw/tp/interval_add_1/conv`, at `4710839b` | 1.28 to 1.33 (-O2), 1.30 to 1.35 (-O3) | 1.13 (-O2), 1.04 to 1.15 (-O3) | 2.90 to 2.92 | 3.28 to 3.29 |
| `upw/tp/interval_add_1/conv`, now | 1.24 to 1.27 | 1.10 (-O2), 1.04 (-O3) | 2.91 to 2.92 | 3.60 to 3.61 |
| `upw/tp/det3_i1/native`, at `4710839b` | 13.3 to 13.8 | 12.8 to 13.3 (-O2), 13.0 to 14.4 (-O3) | 22.3 to 22.5 | 23.4 |
| `upw/tp/det3_i1/native`, now | 12.1 | 11.9 | 22.2 to 22.6 | 23.2 to 23.7 |
| `upw/tp/from_interval_1/op`, at `4710839b` | 0.498 to 0.517 | 0.352 to 0.358 (-O2), 0.351 to 0.378 (-O3) | 1.09 to 1.10 | 1.13 to 1.14 |
| `upw/tp/from_interval_1/op`, now | 0.457 to 0.460 | 0.351 | 1.09 | 1.38 |
| `upw/sum/interval_add_1/native`, at `4710839b` | 0.776 to 0.800 | 0.774 to 0.775 (-O2), 0.763 to 0.820 (-O3) | 1.01 to 1.02 | 1.01 to 1.03 |
| `upw/sum/interval_add_1/native`, now | 0.697 to 0.712 (-O2), 0.717 to 0.737 (-O3) | 0.696 to 0.710 | 1.03 to 1.49 (-O2), 1.01 to 1.21 (-O3) | 1.01 to 1.35 (-O2), 1.03 to 1.17 (-O3) |
| `upws/call/scope_add_1/none`, at `4710839b` | 0.907 to 0.935 | 0.907 to 0.910 (-O2), 0.891 to 0.984 (-O3) | 2.16 to 2.18 | 1.98 to 2.00 |
| `upws/call/scope_add_1/none`, now | 0.883 to 0.890 | 0.877 to 0.890 | 1.98 to 2.16 (-O2), 2.10 to 2.13 (-O3) | 1.69 to 1.86 (-O2), 1.69 to 1.80 (-O3) |
| `upwa/call/add_4/none`, at `4710839b` | 1.65 to 1.70 | 1.68 (-O2), 1.63 to 1.82 (-O3) | 2.62 to 2.66 | 2.63 to 2.65 |
| `upwa/call/add_4/none`, now | 1.17 | 1.28 (-O2), 1.18 (-O3) | 1.62 (-O2), 1.63 to 3.46 (-O3) | 1.63 |
| `upwa/tp/interval_add_1/packed`, at `4710839b` | 1.53 to 1.60 | 1.49 (-O2), 1.47 to 1.62 (-O3) | 1.59 to 1.60 | 1.22 |
| `upwa/tp/interval_add_1/packed`, now | 1.50 to 1.54 | 1.40 to 1.47 (-O2), 1.45 to 1.47 (-O3) | 1.59 to 1.60 | 1.21 |
| `upwa/tp/interval_add_1/fenv_loop`, at `4710839b` | 0.535 to 0.548 (-O2), 0.520 to 0.534 (-O3) | 0.534 to 0.535 (-O2), 0.524 to 0.564 (-O3) | 1.14 to 1.15 | 1.13 to 1.14 |
| `upwa/tp/interval_add_1/fenv_loop`, now | 0.312 to 0.318 | 0.316 to 0.317 | 0.923 to 0.931 | 0.920 to 0.935 |
| `upwa/tp/interval_mul_1/fenv_loop`, at `4710839b` | 0.690 to 0.716 | 0.697 to 0.698 (-O2), 0.683 to 0.755 (-O3) | 1.32 to 1.35 | 1.29 to 1.30 |
| `upwa/tp/interval_mul_1/fenv_loop`, now | 0.667 to 0.681 | 0.676 to 0.678 | 1.24 to 1.25 | 1.25 to 1.26 |
| `upw/tp/horner_i1/native`, at `4710839b` | 15.8 to 16.4 | 17.0 to 17.1 (-O2), 16.7 to 18.0 (-O3) | 27.1 to 27.4 | 26.2 to 27.0 |
| `upw/tp/horner_i1/native`, now | 14.1 to 14.7 (-O2), 15.1 (-O3) | 16.4 (-O2), 15.3 (-O3) | 27.0 to 27.1 | 26.4 to 26.7 |
| `upwa/tp/interval_add_1/op`, at `4710839b` | 0.303 to 0.311 | 0.305 to 0.306 (-O2), 0.299 to 0.330 (-O3) | 0.258 to 0.261 | 0.259 to 0.260 |
| `upwa/tp/interval_add_1/op`, now | 0.298 | 0.289 to 0.300 | 0.257 to 0.259 | 0.258 to 0.260 |
| `m2/tp/interval_add_1/op`, at `4710839b` | 1.87 to 1.95 | 1.79 to 1.81 (-O2), 1.78 to 1.90 (-O3) | 3.52 to 3.54 | 4.51 to 4.53 |
| `m2/tp/interval_add_1/op`, now | 1.86 to 1.87 | 1.76 to 1.77 | 3.53 to 3.54 | 4.51 to 4.52 |
| `m2/tp/interval_add_1/fenv_loop`, at `4710839b` | 0.500 to 0.515 | 0.652 to 0.653 (-O2), 0.508 to 0.546 (-O3) | 1.46 to 1.47 | 1.62 to 1.64 |
| `m2/tp/interval_add_1/fenv_loop`, now | 0.494 | 0.640 (-O2), 0.508 (-O3) | 1.45 to 1.47 | 1.62 to 1.63 |

<!-- END up_report changed -->

<!-- BEGIN up_report unord -->

| The new test over the old, the same program (10 pairs) | M3, Apple clang | M3, GCC 16 |
|---|---|---|
| `upw/tp/interval_mul_1/native` | 0.86 to 0.93 (-O2), 0.87 to 0.90 (-O3) | 0.90 to 0.91 |
| `upw/tp/interval_mul_1/native_x16` | 0.88 to 0.89 | 0.89 to 0.90 |
| `upw/tp/interval_mul_1/conv` | 0.94 to 1.01 (-O2), 0.94 to 0.95 (-O3) | 0.94 |
| `upw/prod/interval_mul_1/native` | 1.00 | 1.00 (-O2), 0.93 to 1.03 (-O3) |
| `upw/tp/det3_i1/native` | 0.88 to 0.92 (-O2), 0.91 to 0.95 (-O3) | 0.91 to 0.92 |
| `upw/tp/det3_i1/conv` | 0.92 to 0.95 | 0.93 to 0.94 |
| `upw/tp/horner_i1/native` | 0.91 to 1.00 (-O2), 0.96 to 1.01 (-O3) | 0.93 to 1.04 (-O2), 0.91 (-O3) |
| `upw/lat/horner_i1/native` | 1.00 | 0.96 to 1.01 (-O2), 0.96 to 1.08 (-O3) |
| `upwf/tp/interval_mul_1/native` | 0.95 to 1.01 (-O2), 0.88 to 0.99 (-O3) | 0.89 to 0.97 (-O2), 0.88 to 0.91 (-O3) |
| `upwa/tp/interval_mul_1/op` | 0.90 to 0.91 | 0.87 to 0.90 |
| `upwaf/tp/interval_mul_1/op` | 0.95 (-O2), 0.91 to 0.96 (-O3) | 0.90 |
| `upwa/call/mul_4/none` | 0.88 to 0.91 | 0.90 to 0.91 |
| `upw/tp/interval_add_1/native` | 0.98 to 1.06 (-O2), 0.97 to 1.07 (-O3) | 0.98 to 1.02 (-O2), 0.98 to 1.05 (-O3) |
| `m2/tp/interval_mul_1/op` | 0.99 to 1.02 | 1.00 to 1.06 (-O2), 1.00 (-O3) |

<!-- END up_report unord -->

<!-- BEGIN up_report placement -->

| This program over that of the earlier runs, alternately on one CPU (4 pairs) | Zen 2, GCC 13 | Zen 2, GCC 13, the scopes | Zen 2, Clang 18 |
|---|---|---|---|
| `upw/tp/interval_add_1/native` | 0.73 to 0.92 (-O2), 2.37 to 2.38 (-O3) |  | 0.54 to 0.64 (-O2), 0.46 to 0.80 (-O3) |
| `upw/tp/interval_add_1/native_x16` | 1.00 (-O2), 0.94 to 1.00 (-O3) |  | 0.68 to 0.70 (-O2), 0.43 to 0.46 (-O3) |
| `upw/tp/interval_sub_1/native` | 1.89 (-O2), 1.34 to 1.73 (-O3) |  | 0.73 to 0.87 (-O2), 0.60 to 1.00 (-O3) |
| `upw/tp/interval_sub_1/native_x16` | 1.31 to 1.33 (-O2), 0.96 to 1.00 (-O3) |  | 0.68 (-O2), 0.57 to 0.60 (-O3) |
| `upw/tp/interval_mul_1/native` | 1.06 (-O2), 1.00 to 1.15 (-O3) |  | 0.84 to 0.85 (-O2), 0.97 to 1.31 (-O3) |
| `upw/tp/interval_mul_1/native_x16` | 1.00 to 1.01 |  | 0.96 to 0.98 |
| `upw/tp/interval_add_1/conv` | 1.00 |  | 1.10 |
| `upw/tp/from_interval_1/op` | 0.99 to 1.00 |  | 1.22 |
| `upw/tp/to_interval_1/op` | 0.99 to 1.00 |  | 0.92 |
| `upw/sum/interval_add_1/native` | 0.85 to 1.48 (-O2), 1.00 (-O3) |  | 1.00 to 1.33 (-O2), 0.85 to 1.14 (-O3) |
| `upwa/tp/interval_add_1/fenv_loop` | 0.81 to 0.82 |  | 0.81 to 0.82 |
| `m2/tp/interval_add_1/op` | 1.00 |  | 1.00 |
| `upws/call/scope_add_1/change` |  | 2.38 to 2.40 (-O3) |  |
| `upws/call/scope_add_1/none` |  | 1.06 to 1.13 (-O3) |  |
| `upws/call/regscope_add_1/change` |  | 1.00 (-O3) |  |
| `upws/call/nearest_add_1/change` |  | 0.99 to 1.00 (-O3) |  |

<!-- END up_report placement -->

## The answers

### 1. The type against the default interval

`kairn::upward::Interval<double>` on arrays of the type (`native`; `native_x16` the same loop 16 times
in one scope; `conv` the default layout converted in the loop), next to `Interval<double, 1>`'s
operators (`m2/.../op`) and generated kernels (`kairn`), the classical interval with the mode set
upward once around the loop (`fenv_loop`, and `fenv_loop_x16` the same 16 times between one change of
mode and its reset), and the plain floors of Milestone 2 (two plain additions; the four plain products
with their least and greatest). Every function computes the same bounds as the default kernels on the
same operands ([Runs](#runs)).

<!-- BEGIN up_report type -->

| Loops, times (ns per operation) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/tp/interval_add_1/native` | 0.386 | 0.386 | 0.595 to 0.596 (-O2), 1.41 (-O3) | 0.599 to 0.712 (-O2), 0.821 to 0.979 (-O3) |
| `upw/tp/interval_add_1/native_x16` | 0.302 to 0.307 | 0.307 | 0.637 (-O2), 0.400 to 0.418 (-O3) | 0.636 to 0.655 (-O2), 0.402 to 0.430 (-O3) |
| `upw/tp/interval_add_1/conv` | 1.24 to 1.27 | 1.10 (-O2), 1.04 (-O3) | 2.91 to 2.92 | 3.60 to 3.61 |
| `m2/tp/interval_add_1/op` | 1.86 to 1.87 | 1.76 to 1.77 | 3.53 to 3.54 | 4.51 to 4.52 |
| `m2/tp/interval_add_1/fenv_loop` | 0.494 | 0.640 (-O2), 0.508 (-O3) | 1.45 to 1.47 | 1.62 to 1.63 |
| `m2/tp/interval_add_1/fenv_loop_x16` | 0.395 to 0.405 | 0.552 (-O2), 0.419 (-O3) | 0.805 to 0.819 | 0.959 to 0.962 |
| `upw/tp/interval_sub_1/native` | 0.386 | 0.385 to 0.386 | 1.27 (-O2), 1.26 to 1.41 (-O3) | 0.819 to 0.980 (-O2), 0.676 to 0.677 (-O3) |
| `upw/tp/interval_sub_1/native_x16` | 0.297 to 0.307 | 0.307 to 0.308 | 0.637 to 0.650 | 0.637 to 0.638 (-O2), 0.545 to 0.562 (-O3) |
| `upw/tp/interval_sub_1/conv` | 1.33 | 1.17 (-O2), 1.11 (-O3) | 3.05 to 3.49 (-O2), 3.04 to 3.07 (-O3) | 3.44 to 3.58 |
| `m2/tp/interval_sub_1/op` | 1.85 to 1.87 | 1.78 to 1.84 | 3.64 to 3.66 | 4.51 |
| `m2/tp/interval_sub_1/fenv_loop` | 0.469 to 0.470 (-O2), 0.494 (-O3) | 0.641 (-O2), 0.508 to 0.509 (-O3) | 1.45 to 1.46 | 1.62 to 1.64 |
| `m2/tp/interval_sub_1/fenv_loop_x16` | 0.381 to 0.385 | 0.552 (-O2), 0.419 (-O3) | 0.793 to 0.807 | 0.960 to 0.968 |
| `upw/tp/interval_mul_1/native` | 1.17 | 1.17 to 1.18 | 2.09 (-O2), 1.98 to 2.27 (-O3) | 1.97 to 1.98 (-O2), 2.10 to 2.65 (-O3) |
| `upw/tp/interval_mul_1/native_x16` | 1.08 | 1.08 | 1.79 to 1.82 | 1.79 to 1.80 |
| `upw/tp/interval_mul_1/conv` | 2.34 | 2.06 to 2.12 | 5.63 to 5.65 | 6.03 to 6.05 (-O2), 5.68 to 5.77 (-O3) |
| `m2/tp/interval_mul_1/op` | 6.08 to 6.23 | 7.89 to 8.00 | 9.85 to 9.88 | 16.8 to 16.9 |
| `m2/tp/interval_mul_1/fenv_loop` | 1.44 (-O2), 1.70 (-O3) | 1.06 to 1.07 | 1.78 | 3.47 to 3.61 |
| `m2/tp/interval_mul_1/fenv_loop_x16` | 1.53 to 1.61 (-O2), 1.61 (-O3) | 0.981 to 0.982 | 1.13 to 1.14 | 3.70 to 3.81 (-O2), 3.13 to 3.32 (-O3) |
| `m2/tp/pair_add_1/plain` | 0.287 to 0.294 | 0.295 | 0.323 to 0.324 | 0.614 to 0.615 |
| `m2/tp/plain4_mul_1/plain` | 0.738 to 0.745 | 0.940 (-O2), 1.07 (-O3) | 1.01 to 1.02 | 1.12 |

| Loops, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`: Interval<T, 1> over the type, one scope per loop | 4.81 to 4.85 | 4.57 to 4.59 | 5.92 to 5.95 (-O2), 2.51 (-O3) | 6.33 to 7.54 (-O2), 4.61 to 5.50 (-O3) |
| `X + Y`: Interval<T, 1> over the type, 16 loops per scope | 6.09 to 6.20 | 5.74 to 5.75 | 5.54 to 5.56 (-O2), 8.43 to 8.84 (-O3) | 6.89 to 7.09 (-O2), 10.5 to 11.2 (-O3) |
| `X - Y`: Interval<T, 1> over the type, one scope per loop | 4.81 to 4.86 | 4.77 (-O2), 4.60 to 4.76 (-O3) | 2.85 to 2.86 (-O2), 2.59 to 2.91 (-O3) | 4.60 to 5.50 (-O2), 6.66 to 6.67 (-O3) |
| `X - Y`: Interval<T, 1> over the type, 16 loops per scope | 6.09 to 6.20 (-O2), 6.09 to 6.31 (-O3) | 5.97 (-O2), 5.79 to 5.98 (-O3) | 5.59 to 5.74 | 7.07 to 7.08 (-O2), 8.02 to 8.27 (-O3) |
| `X * Y`: Interval<T, 1> over the type, one scope per loop | 5.20 to 5.32 | 6.68 to 6.81 | 4.72 (-O2), 4.34 to 5.00 (-O3) | 8.50 to 8.53 (-O2), 6.37 to 8.06 (-O3) |
| `X * Y`: Interval<T, 1> over the type, 16 loops per scope | 5.63 to 5.77 | 7.31 to 7.38 | 5.42 to 5.50 | 9.39 to 9.46 |
| `X + Y`: the type over fenv_loop | 0.78 | 0.60 (-O2), 0.76 (-O3) | 0.41 (-O2), 0.95 to 0.96 (-O3) | 0.37 to 0.44 (-O2), 0.50 to 0.60 (-O3) |
| `X + Y`: the type over fenv_loop, 16 loops per change of mode | 0.75 to 0.77 | 0.56 (-O2), 0.73 (-O3) | 0.79 (-O2), 0.49 to 0.51 (-O3) | 0.66 to 0.68 (-O2), 0.42 to 0.45 (-O3) |
| `X - Y`: the type over fenv_loop | 0.78 to 0.82 | 0.60 (-O2), 0.76 (-O3) | 0.88 (-O2), 0.86 to 0.97 (-O3) | 0.50 to 0.60 (-O2), 0.41 to 0.42 (-O3) |
| `X - Y`: the type over fenv_loop, 16 loops per change of mode | 0.77 to 0.80 | 0.56 (-O2), 0.73 (-O3) | 0.79 to 0.82 | 0.66 (-O2), 0.56 to 0.58 (-O3) |
| `X * Y`: the type over fenv_loop | 0.81 (-O2), 0.69 (-O3) | 1.09 to 1.11 | 1.17 to 1.18 (-O2), 1.11 to 1.28 (-O3) | 0.55 to 0.57 (-O2), 0.58 to 0.75 (-O3) |
| `X * Y`: the type over fenv_loop, 16 loops per change of mode | 0.67 to 0.71 | 1.10 | 1.57 to 1.60 | 0.47 to 0.49 (-O2), 0.54 to 0.57 (-O3) |
| `X + Y`: the type, 16 loops per scope, over the plain floor | 1.03 to 1.07 | 1.04 | 1.97 (-O2), 1.24 to 1.30 (-O3) | 1.04 to 1.07 (-O2), 0.65 to 0.70 (-O3) |
| `X * Y`: the type, 16 loops per scope, over the plain floor | 1.45 to 1.46 | 1.15 (-O2), 1.01 (-O3) | 1.77 to 1.80 | 1.59 to 1.60 |
| `X + Y`: converted in the loop over native | 3.21 to 3.30 | 2.86 (-O2), 2.70 (-O3) | 4.88 to 4.89 (-O2), 2.07 (-O3) | 5.06 to 6.03 (-O2), 3.69 to 4.40 (-O3) |
| `X - Y`: converted in the loop over native | 3.45 to 3.46 | 3.04 (-O2), 2.87 (-O3) | 2.39 to 2.74 (-O2), 2.17 to 2.42 (-O3) | 3.51 to 4.26 (-O2), 5.10 to 5.28 (-O3) |
| `X * Y`: converted in the loop over native | 2.00 | 1.75 to 1.80 | 2.70 (-O2), 2.48 to 2.86 (-O3) | 3.04 to 3.06 (-O2), 2.17 to 2.75 (-O3) |

<!-- END up_report type -->

<!-- BEGIN up_report chains -->

| Chains, times (ns per step) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/sum/interval_add_1/native` | 0.697 to 0.712 (-O2), 0.717 to 0.737 (-O3) | 0.696 to 0.710 | 1.03 to 1.49 (-O2), 1.01 to 1.21 (-O3) | 1.01 to 1.35 (-O2), 1.03 to 1.17 (-O3) |
| `upw/sum/interval_add_1/native_x16` | 0.660 to 0.667 | 0.648 to 0.653 | 0.907 to 0.921 | 0.907 to 0.918 |
| `upw/sum/interval_add_1/conv` | 0.790 to 0.826 | 0.802 to 0.806 | 1.36 to 1.49 (-O2), 1.36 to 1.79 (-O3) | 1.55 to 1.73 (-O2), 1.56 (-O3) |
| `m2/sum/interval_add_1/op` | 5.11 to 5.40 (-O2), 5.49 (-O3) | 3.86 | 5.63 to 5.64 | 6.58 to 6.65 |
| `m2/sum/interval_add_1/fenv_loop` | 0.772 to 0.801 (-O2), 0.816 to 0.820 (-O3) | 0.803 to 0.804 | 1.58 to 1.59 | 1.56 to 1.57 |
| `m2/sum/interval_add_1/fenv_loop_x16` | 0.689 to 0.691 | 0.693 to 0.710 | 0.941 to 0.943 | 0.923 to 0.942 |
| `upw/prod/interval_mul_1/native` | 4.54 | 4.54 | 3.25 to 3.51 (-O2), 3.26 (-O3) | 3.42 to 4.17 (-O2), 3.42 to 3.43 (-O3) |
| `upw/prod/interval_mul_1/native_x16` | 4.44 to 4.45 | 4.44 to 4.45 | 3.02 to 3.03 | 3.37 to 3.44 |
| `upw/prod/interval_mul_1/conv` | 4.55 | 4.54 | 4.23 (-O2), 3.88 to 4.35 (-O3) | 3.67 to 3.68 (-O2), 3.68 to 3.98 (-O3) |
| `m2/prod/interval_mul_1/op` | 10.4 to 10.8 | 9.71 to 10.2 | 18.5 to 18.6 | 18.2 to 18.3 |
| `m2/prod/interval_mul_1/fenv_loop` | 3.14 (-O2), 3.08 to 3.29 (-O3) | 3.29 to 3.33 (-O2), 3.54 to 3.61 (-O3) | 3.06 (-O2), 3.69 to 3.70 (-O3) | 3.13 to 3.14 |
| `m2/prod/interval_mul_1/fenv_loop_x16` | 3.02 to 3.05 (-O2), 3.23 to 3.29 (-O3) | 3.25 to 3.44 (-O2), 3.71 (-O3) | 3.05 to 3.10 | 2.47 |

| Chains, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `S + X`: Interval<T, 1> over the type | 7.18 to 7.75 (-O2), 7.45 to 7.65 (-O3) | 5.43 to 5.54 | 3.78 to 5.48 (-O2), 4.66 to 5.58 (-O3) | 4.88 to 6.53 (-O2), 5.68 to 6.47 (-O3) |
| `S + X`: Interval<T, 1> over the type, a chain 16 times as long per scope | 7.67 to 8.10 (-O2), 8.27 to 8.31 (-O3) | 5.91 to 5.96 | 6.11 to 6.21 | 7.17 to 7.32 |
| `P * X`: Interval<T, 1> over the type | 2.29 to 2.35 (-O2), 2.36 to 2.38 (-O3) | 2.23 (-O2), 2.14 to 2.24 (-O3) | 5.27 to 5.70 (-O2), 5.69 to 5.71 (-O3) | 4.37 to 5.34 (-O2), 5.33 (-O3) |
| `P * X`: Interval<T, 1> over the type, a chain 16 times as long per scope | 2.33 to 2.40 (-O2), 2.41 to 2.43 (-O3) | 2.28 (-O2), 2.19 to 2.28 (-O3) | 6.11 to 6.16 | 5.29 to 5.41 |
| `S + X`: the type over fenv_loop | 0.87 to 0.91 | 0.87 to 0.88 | 0.65 to 0.94 (-O2), 0.64 to 0.76 (-O3) | 0.65 to 0.86 (-O2), 0.66 to 0.75 (-O3) |
| `S + X`: the type over fenv_loop, both 16 times as long | 0.96 to 0.97 | 0.92 to 0.94 | 0.96 to 0.98 | 0.96 to 0.98 |
| `P * X`: the type over fenv_loop | 1.45 (-O2), 1.38 to 1.47 (-O3) | 1.36 to 1.38 (-O2), 1.26 to 1.28 (-O3) | 1.06 to 1.15 (-O2), 0.88 to 0.89 (-O3) | 1.09 to 1.33 (-O2), 1.09 (-O3) |
| `P * X`: the type over fenv_loop, both 16 times as long | 1.46 to 1.47 (-O2), 1.35 to 1.37 (-O3) | 1.29 to 1.37 (-O2), 1.20 (-O3) | 0.98 to 0.99 | 1.37 to 1.39 |
| `S + X`: converted over native | 1.11 to 1.14 | 1.13 to 1.16 | 0.91 to 1.45 (-O2), 1.13 to 1.77 (-O3) | 1.15 to 1.71 (-O2), 1.33 to 1.52 (-O3) |
| `P * X`: converted over native | 1.00 | 1.00 | 1.20 to 1.30 (-O2), 1.19 to 1.33 (-O3) | 0.88 to 1.08 (-O2), 1.07 to 1.16 (-O3) |

<!-- END up_report chains -->

<!-- BEGIN up_report poly -->

| Horner and the determinant, times (ns per evaluation) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/tp/horner_i1/native` | 14.1 to 14.7 (-O2), 15.1 (-O3) | 16.4 (-O2), 15.3 (-O3) | 27.0 to 27.1 | 26.4 to 26.7 |
| `upw/tp/horner_i1/conv` | 17.2 to 18.2 (-O2), 18.4 (-O3) | 16.5 to 16.6 | 32.8 to 33.1 | 30.4 to 31.1 |
| `m2/tp/horner_i1/op` | 115 to 124 (-O2), 123 (-O3) | 104 to 108 | 245 to 248 | 178 to 180 |
| `m2/tp/horner_i1/fenv_loop` | 14.6 (-O2), 12.7 to 12.8 (-O3) | 17.7 to 17.8 (-O2), 15.8 (-O3) | 45.3 to 45.5 | 30.8 to 31.9 (-O2), 26.2 to 26.4 (-O3) |
| `upw/lat/horner_i1/native` | 48.6 to 50.7 | 45.4 to 46.2 | 43.8 to 43.9 (-O2), 40.4 to 40.5 (-O3) | 39.6 to 40.3 |
| `upw/lat/horner_i1/conv` | 49.2 to 51.1 (-O2), 52.1 (-O3) | 46.1 to 48.9 (-O2), 48.7 (-O3) | 41.7 to 42.1 | 39.3 to 39.7 |
| `m2/lat/horner_i1/op` | 124 to 125 (-O2), 133 to 134 (-O3) | 116 to 121 | 243 to 250 | 186 to 187 |
| `m2/lat/horner_i1/fenv_loop` | 33.3 (-O2), 28.6 to 28.9 (-O3) | 33.7 to 33.8 (-O2), 31.5 to 31.9 (-O3) | 33.9 | 30.8 to 31.4 (-O2), 28.5 to 28.6 (-O3) |
| `upw/tp/det3_i1/native` | 12.1 | 11.9 | 22.2 to 22.6 | 23.2 to 23.7 |
| `upw/tp/det3_i1/conv` | 16.4 to 16.8 | 15.9 to 16.1 | 33.2 to 33.7 | 40.8 to 41.1 |
| `m2/tp/det3_i1/op` | 102 to 109 (-O2), 109 (-O3) | 101 | 485 to 492 | 223 to 224 |
| `m2/tp/det3_i1/fenv_loop` | 13.2 to 14.1 (-O2), 14.1 (-O3) | 15.7 to 16.4 | 26.3 | 36.2 to 37.0 (-O2), 34.3 to 35.0 (-O3) |
| `m2/tp/det3_i2/op` | 453 to 454 (-O2), 486 to 487 (-O3) | 501 to 506 | 1294 to 1302 | 991 to 994 |
| `m2/tp/det3_b1/op` | 18.8 to 19.2 | 19.5 to 19.9 | 58.2 to 58.6 | 49.2 to 49.3 |
| `m2/tp/det3_b2/op` | 50.6 to 54.1 (-O2), 54.1 to 54.2 (-O3) | 50.2 to 51.1 | 149 | 140 |
| `m2/tp/det3_t/plain` | 1.55 to 1.61 | 1.55 | 3.25 to 3.26 | 3.63 |

| Horner and the determinant, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| Horner, independent: Interval<T, 1> over the type | 7.87 to 8.56 (-O2), 8.15 to 8.16 (-O3) | 6.59 (-O2), 6.78 to 7.05 (-O3) | 9.08 to 9.19 | 6.69 to 6.78 |
| Horner, dependent: Interval<T, 1> over the type | 2.56 to 2.57 (-O2), 2.62 to 2.72 (-O3) | 2.61 to 2.66 (-O2), 2.51 to 2.54 (-O3) | 5.54 to 5.61 (-O2), 6.13 to 6.18 (-O3) | 4.63 to 4.71 |
| Horner, independent: the type over fenv_loop | 0.97 to 1.01 (-O2), 1.18 to 1.19 (-O3) | 0.92 to 0.97 | 0.59 to 0.60 | 0.84 to 0.87 (-O2), 1.01 (-O3) |
| Horner, dependent: the type over fenv_loop | 1.46 (-O2), 1.71 to 1.76 (-O3) | 1.35 to 1.36 (-O2), 1.44 to 1.47 (-O3) | 1.29 (-O2), 1.19 (-O3) | 1.28 to 1.31 (-O2), 1.38 to 1.41 (-O3) |
| Horner, independent: converted over native | 1.22 to 1.25 | 1.01 (-O2), 1.09 (-O3) | 1.21 to 1.22 | 1.14 to 1.17 |
| det3: Interval<T, 1> over the type | 8.43 to 9.02 (-O2), 8.98 to 9.04 (-O3) | 8.48 to 8.53 | 21.8 to 22.1 | 9.46 to 9.63 |
| det3: the type over fenv_loop | 0.86 to 0.92 (-O2), 0.85 to 0.86 (-O3) | 0.72 to 0.76 | 0.85 to 0.86 | 0.63 to 0.65 (-O2), 0.66 to 0.69 (-O3) |
| det3: converted over native | 1.36 to 1.39 | 1.34 to 1.36 | 1.48 to 1.50 | 1.72 to 1.77 |
| det3: Ball<T, 1> over the type | 1.55 to 1.59 | 1.64 to 1.67 | 2.58 to 2.63 | 2.08 to 2.12 |
| det3: Interval<T, 2> over the type | 37.4 to 37.5 (-O2), 40.2 to 40.3 (-O3) | 42.2 to 42.6 | 57.5 to 58.3 | 42.0 to 42.8 |
| det3: Ball<T, 2> over the type | 4.18 to 4.47 (-O2), 4.47 to 4.49 (-O3) | 4.23 to 4.31 | 6.59 to 6.68 | 5.92 to 6.03 |
| det3: the type over plain double | 7.53 to 7.79 (-O2), 7.50 to 7.52 (-O3) | 7.65 to 7.68 | 6.84 to 6.94 | 6.40 to 6.53 |

<!-- END up_report poly -->

- **Loops.** A sum of the type is one vector addition of two lanes, a product four products of two
  lanes and three maxima; the default type's sum is two directed sums of about fifteen operations each,
  its product eight directed products. So the type's sum is 2.5 to 7.5 times faster in a loop of 256
  with its scope, and 5.5 to 11 times with 16 loops per scope; its product 4.3 to 8.5 and 5.4 to 9.5
  times. With 16 loops per scope a sum costs 0.65 to 1.97 times the two plain additions (under 1 with
  Clang 18 at `-O3`, whose loop of plain additions takes 0.61 ns), a product 1.01 to 1.80 times the
  four plain products with their least and greatest.
- **The scope's share of a loop.** A loop of 256 operations under one scope pays the scope once:
  about 22 ns on the M3 and 50 ns on Zen 2 ([question 5](#5-the-scopes)), 0.09 and 0.2 ns per
  operation; on the M3 `native` takes 1.25 to 1.30 times `native_x16` for the sums and 1.08 to 1.10
  for the products. On Zen 2 the loops with one scope per 256 operations took 0.91 to 3.5 times their
  16-pass loops, more than the scope explains, and are where the placement of the code moved the
  times most ([What changed](#what-changed)): GCC 13's sum at `-O3` took 1.41 ns, and 0.40 ns in 16
  passes. They also vary from run to run (Clang 18's sum at `-O3`, 0.82 to 0.98 ns over the four runs,
  its 16-pass loop 0.40 to 0.43). Short work between two changes of mode is what varies most: the
  widest ranges of these runs are calls of one operation in a `NearestScope` (Clang 18 at `-O2`, 57
  to 129 ns; GCC 13 at `-O3`, 56 to 97 ns), calls of the array kernel on 4 elements (GCC 13 at `-O3`,
  1.6 to 3.5 ns) or 16 (GCC 13 at `-O2`, 4.5 to 6.4 ns), and the chain of sums under one scope (GCC 13
  at `-O2`, 1.03 to 1.49 ns).
- **Against the classical interval** under a mode set once: the type's sums take 0.37 to 0.96 of its
  time (the classical loop negates both operands of the lower bound and its result, the type stores
  it negated), its products 0.47 to 1.60: slower where GCC vectorizes the classical loop's four
  products (1.09 to 1.60 with GCC 13 and GCC 16), faster where Clang does not under `FENV_ACCESS`
  (0.47 to 0.81). The classical code here handles no special case (no empty set, no unbounded
  interval, no $0 \cdot \infty$); the type handles all of them.
- **Chains.** A chain of sums waits for one vector addition per step: 0.65 to 1.49 ns, 3.8 to 8.3 times
  faster than the default chain, and the same time as the classical chain under one mode (0.92 to 0.98
  when both run 16 times as long). A chain of products waits for four products and three maxima: 3.0 to
  4.5 ns, 2.1 to 6.2 times faster than the default; on the M3 the default product chain is relatively
  fast (10 to 11 ns), so the gain there is 2.1 to 2.4 times. Against the classical chain of products
  under one mode, 0.88 to 1.47.
- **Horner and the determinant.** Horner of degree 8 (eight products and eight sums of intervals) is
  6.6 to 9.2 times faster than the default on independent arguments and 2.5 to 6.2 times when each
  evaluation waits for the one before. The determinant of coordinate differences (9 differences, 9
  products, 5 sums or differences) takes 12 ns on the M3 and 22 to 24 ns on Zen 2, 8.4 to 9.6 times
  faster than the default type, and 22 times with GCC 13, whose default determinant takes 490 ns: its
  loop has no call, and is 1.6 times as long as Clang 18's with 1.4 times as many accesses to the
  stack (spilled registers; not investigated further). `Ball<double, 1>` takes 1.6 to 2.6 times the
  type, `Ball<double, 2>` 4.2 to 6.7 times, `Interval<double, 2>` 37 to 58 times; plain `double`, which
  encloses nothing, 0.13 to 0.16 of the type's time.

### 2. What a conversion costs

A program that keeps its intervals in the default layout, (lower, upper) in memory, converts each
operand (`kairn::upward::Interval<T>(x)`, the kernel `upward_from_interval_1`: a negation and a
selection) and each result back (`to_interval()`, `upward_to_interval_1`, with the barriers on its
bounds): the variants `conv` of question 1, against `native`, and the conversions alone, in loops
without a scope (they are exact).

<!-- BEGIN up_report conversions -->

| Conversions alone, times | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/tp/from_interval_1/op`, ns per element | 0.457 to 0.460 | 0.351 | 1.09 | 1.38 |
| `upw/tp/to_interval_1/op`, ns per element | 0.388 to 0.416 (-O2), 0.416 to 0.418 (-O3) | 0.341 to 0.357 | 0.630 to 0.638 | 1.13 |

| What the conversions cost (ns per operation) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, converted minus native (two conversions in, one out) | 0.854 to 0.887 | 0.653 to 0.719 | 2.31 to 2.32 (-O2), 1.50 to 1.51 (-O3) | 2.63 to 3.01 |
| `X * Y`, converted minus native | 1.17 | 0.883 to 0.944 | 3.36 to 3.68 | 4.05 to 4.07 (-O2), 3.11 to 3.67 (-O3) |
| `S + X`, converted minus native (one conversion in) | 0.078 to 0.099 | 0.092 to 0.108 | -0.129 to 0.458 (-O2), 0.154 to 0.783 (-O3) | 0.202 to 0.722 (-O2), 0.387 to 0.531 (-O3) |
| det3, converted minus native (12 in, one out) | 4.32 to 4.76 | 4.05 to 4.24 | 10.7 to 11.1 | 17.1 to 17.9 |

| The default type against the type converted in the loop | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`: Interval<T, 1> over the type converted in the loop | 1.47 to 1.51 (-O2), 1.46 to 1.47 (-O3) | 1.60 (-O2), 1.70 (-O3) | 1.21 to 1.22 | 1.25 |
| `X * Y`: Interval<T, 1> over the type converted in the loop | 2.60 to 2.66 | 3.72 to 3.74 (-O2), 3.88 to 3.89 (-O3) | 1.75 | 2.78 to 2.80 (-O2), 2.92 to 2.97 (-O3) |
| `S + X`: Interval<T, 1> over the type converted in the loop | 6.42 to 6.78 (-O2), 6.64 to 6.78 (-O3) | 4.79 to 4.81 | 3.79 to 4.14 (-O2), 3.14 to 4.13 (-O3) | 3.81 to 4.25 (-O2), 4.26 to 4.27 (-O3) |
| det3: Interval<T, 1> over the type converted in the loop | 6.14 to 6.65 (-O2), 6.46 to 6.49 (-O3) | 6.25 to 6.35 | 14.6 to 14.8 | 5.44 to 5.49 |

<!-- END up_report conversions -->

- A loop of sums in the default layout costs 2.1 to 6.0 times the loop on arrays of the type, a loop
  of products 1.8 to 3.1 times: 0.65 to 0.89 ns more per sum and 0.88 to 1.17 per product on the M3,
  1.5 to 3.0 and 3.1 to 4.1 ns on Zen 2, for two conversions in and one out (the ratios on Zen 2 move
  with the loops on arrays of the type, whose times the placement of the code moved: [What
  changed](#what-changed)). The converted sum is then still 1.5 to 1.7 times faster than the default
  type's on the M3 and 1.2 times on Zen 2, the converted product 2.6 to 3.9 and 1.8 to 3.0 times
  faster, the converted chain of sums 3.1 to 6.8 times and the converted determinant 5.4 to 15 times.
- One conversion alone takes 0.35 to 0.46 ns per interval (from the default type) and 0.34 to 0.42
  (back) on the M3, 1.09 to 1.38 and 0.63 to 1.13 ns on Zen 2.
- Where the operation waits for the one before, the conversion of the next operand is off the
  critical path: a chain of sums pays 0.08 to 0.11 ns per step on the M3, and on Zen 2 a difference
  within the variation of its chain under one scope (-0.13 to 0.78 ns); a chain of products 0.88 to
  1.33 of its time. The determinant, with 12 conversions in and one out for 23 interval operations,
  pays 4.1 to 4.8 ns (M3) and 11 to 18 ns (Zen 2), 1.3 to 1.8 times.
- So the type pays where the data stays in its layout: arrays of `kairn::upward::Interval<T>` (the
  layout of `from_limbs` and `to_limbs`, $(u, n)$), or the two arrays of the functions on arrays.

### 3. The functions on arrays

`kairn::upward::add`, `sub` and `mul` on views of two plain arrays (upper bounds, negated lower
bounds) of 256 intervals, one call from code that rounds to nearest, so that each call holds and pays
its own scope: AVX2 on Zen 2 (4 lanes of `double`, 8 of `float`), NEON on the M3 (2 and 4). Next to
them, Kairn's packed interval kernels of `Interval<T, 1>` (`kairn/gen/avx2.hpp`, `neon.hpp`) on the
same intervals as two arrays (lower, upper) placed as these are (`packed`), the same kernels on the
arrays of Milestone 2 (`m2p/.../kairn`), and the packed classical interval with the mode set upward
once around the loop (`fenv_loop`, `m2p/.../fenv_loop`).

<!-- BEGIN up_report arrays -->

| Functions on arrays of 256, times (ns per interval) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upwa/tp/interval_add_1/op` | 0.298 | 0.289 to 0.300 | 0.257 to 0.259 | 0.258 to 0.260 |
| `upwa/tp/interval_add_1/packed` | 1.50 to 1.54 | 1.40 to 1.47 (-O2), 1.45 to 1.47 (-O3) | 1.59 to 1.60 | 1.21 |
| `upwa/tp/interval_add_1/fenv_loop` | 0.312 to 0.318 | 0.316 to 0.317 | 0.923 to 0.931 | 0.920 to 0.935 |
| `upwa/tp/interval_sub_1/op` | 0.298 to 0.299 | 0.298 to 0.299 | 0.258 to 0.265 | 0.259 to 0.267 |
| `upwa/tp/interval_sub_1/packed` | 1.57 to 1.58 | 1.54 to 1.55 | 1.69 to 1.70 | 1.26 to 1.27 |
| `upwa/tp/interval_sub_1/fenv_loop` | 0.314 | 0.313 to 0.314 | 0.921 to 0.931 | 0.921 to 0.932 |
| `upwa/tp/interval_mul_1/op` | 1.12 | 1.11 | 0.973 to 0.983 | 0.867 to 0.874 |
| `upwa/tp/interval_mul_1/packed` | 5.18 to 5.19 | 4.99 (-O2), 5.40 (-O3) | 4.60 to 4.61 | 4.19 to 4.29 |
| `upwa/tp/interval_mul_1/fenv_loop` | 0.667 to 0.681 | 0.676 to 0.678 | 1.24 to 1.25 | 1.25 to 1.26 |
| `upwaf/tp/interval_add_1/op` | 0.193 to 0.198 | 0.192 to 0.195 | 0.145 to 0.146 | 0.145 to 0.147 |
| `upwaf/tp/interval_add_1/packed` | 0.778 | 0.730 | 0.803 to 0.805 | 0.601 to 0.602 |
| `upwaf/tp/interval_add_1/fenv_loop` | 0.206 to 0.208 | 0.202 to 0.203 | 0.815 to 0.818 | 0.801 to 0.819 |
| `upwaf/tp/interval_sub_1/op` | 0.192 to 0.196 | 0.193 to 0.194 | 0.145 to 0.147 | 0.146 to 0.147 |
| `upwaf/tp/interval_sub_1/packed` | 0.801 to 0.802 | 0.769 to 0.770 | 0.861 to 0.863 | 0.626 to 0.627 |
| `upwaf/tp/interval_sub_1/fenv_loop` | 0.203 to 0.205 | 0.196 to 0.201 | 0.809 to 0.815 | 0.802 to 0.822 |
| `upwaf/tp/interval_mul_1/op` | 0.622 to 0.623 | 0.613 | 0.474 to 0.477 | 0.461 to 0.465 |
| `upwaf/tp/interval_mul_1/packed` | 2.59 | 2.45 to 2.49 | 2.31 to 2.32 | 2.03 to 2.10 |
| `upwaf/tp/interval_mul_1/fenv_loop` | 0.394 to 0.397 | 0.393 to 0.394 | 0.955 to 0.960 | 0.960 to 0.971 |
| `m2p/tp/interval_add_1/kairn` | 1.46 to 1.54 | 1.47 to 1.48 | 1.61 | 1.23 to 1.24 |
| `m2p/tp/interval_add_1/fenv_loop` | 0.475 to 0.497 (-O2), 0.475 to 0.508 (-O3) | 0.506 to 0.507 | 1.02 to 1.03 | 1.03 |
| `m2p/tp/interval_mul_1/kairn` | 4.98 to 5.20 | 5.00 (-O2), 5.45 (-O3) | 4.63 to 4.65 | 4.23 to 4.40 |
| `m2p/tp/interval_mul_1/fenv_loop` | 0.712 to 0.718 | 0.716 to 0.717 | 1.29 to 1.30 | 1.30 |

| Functions on arrays, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| double `+`: the packed kernel over the function | 5.03 to 5.16 | 4.66 to 5.07 (-O2), 4.83 to 4.91 (-O3) | 6.17 to 6.22 | 4.66 to 4.68 |
| double `-`: the packed kernel over the function | 5.28 to 5.30 | 5.14 to 5.19 | 6.39 to 6.55 | 4.86 to 4.90 (-O2), 4.72 (-O3) |
| double `*`: the packed kernel over the function | 4.61 | 4.48 to 4.49 (-O2), 4.86 (-O3) | 4.69 to 4.74 | 4.82 to 4.92 |
| float `+`: the packed kernel over the function | 3.93 to 4.04 | 3.75 to 3.80 | 5.50 to 5.54 | 4.10 to 4.14 |
| float `-`: the packed kernel over the function | 4.09 to 4.17 | 3.97 to 3.98 | 5.88 to 5.92 | 4.27 to 4.28 |
| float `*`: the packed kernel over the function | 4.16 | 4.00 to 4.06 | 4.83 to 4.88 | 4.39 to 4.41 (-O2), 4.40 to 4.54 (-O3) |
| double `+`: the function over fenv_loop | 0.94 to 0.95 | 0.92 to 0.95 | 0.28 | 0.28 |
| double `-`: the function over fenv_loop | 0.95 | 0.95 to 0.96 | 0.28 to 0.29 | 0.28 to 0.29 |
| double `*`: the function over fenv_loop | 1.65 to 1.69 | 1.64 to 1.65 | 0.78 to 0.79 | 0.69 to 0.70 |
| float `+`: the function over fenv_loop | 0.93 to 0.96 | 0.95 to 0.96 | 0.18 | 0.18 |
| float `-`: the function over fenv_loop | 0.94 to 0.96 | 0.96 to 0.99 | 0.18 | 0.18 |
| float `*`: the function over fenv_loop | 1.57 to 1.58 | 1.56 | 0.49 to 0.50 | 0.48 |
| double `+`: m2p (the arrays of m2.cpp) over packed (placed) | 0.96 to 1.00 | 1.01 to 1.06 (-O2), 1.00 to 1.02 (-O3) | 1.00 to 1.01 | 1.02 to 1.03 |
| double `+`: m2p fenv_loop over fenv_loop (placed) | 1.51 to 1.56 (-O2), 1.50 to 1.60 (-O3) | 1.60 to 1.61 | 1.11 | 1.10 to 1.12 |
| double `*`: m2p (the arrays of m2.cpp) over packed (placed) | 0.96 to 1.00 | 1.00 to 1.01 | 1.01 | 1.01 to 1.03 |
| double `*`: m2p fenv_loop over fenv_loop (placed) | 1.05 to 1.07 | 1.06 | 1.03 to 1.05 | 1.03 to 1.04 |
| `+`: the function on arrays over the type, 16 loops per scope | 0.97 to 0.99 | 0.94 to 0.97 | 0.41 (-O2), 0.62 to 0.65 (-O3) | 0.39 to 0.41 (-O2), 0.60 to 0.64 (-O3) |
| `+`: float over double, the function on arrays | 0.65 to 0.66 | 0.64 to 0.66 | 0.56 to 0.57 | 0.56 to 0.57 |
| `+`: float over double, the type | 1.00 | 1.00 | 1.38 (-O2), 0.85 (-O3) | 0.84 to 1.00 (-O2), 0.84 to 1.00 (-O3) |
| `*`: the function on arrays over the type, 16 loops per scope | 1.04 | 1.03 | 0.54 to 0.55 | 0.48 to 0.49 |
| `*`: float over double, the function on arrays | 0.55 | 0.55 | 0.48 to 0.49 | 0.53 |
| `*`: float over double, the type | 0.96 to 1.00 | 1.05 to 1.06 | 0.95 (-O2), 0.92 to 1.07 (-O3) | 1.00 to 1.21 (-O2), 0.86 to 1.09 (-O3) |

<!-- END up_report arrays -->

- **Against Kairn's packed kernels**, the functions on arrays are 4.7 to 6.6 times faster for sums and
  differences of `double` and 4.5 to 4.9 times for products (3.7 to 5.9 for `float`): a sum is one
  vector addition per lane of each array, where the default kernel computes two directed sums with
  their error terms and steps.
- **Against the packed classical interval** under one mode: on Zen 2 the functions take 0.18 to 0.29
  of its time for sums and 0.48 to 0.79 for products (its loops, as their compilers compiled them under
  `-frounding-math`, take 0.80 to 1.26 ns per interval there: their sum about 3.5 times the
  functions' sum of `double`, and 5.5 times that of `float`);
  on the M3 0.92 to 0.99 for sums, about the same time, and 1.56 to 1.69 for products: the classical
  product is eight products and six maxima per interval and handles no special case, the type's has
  the same products and maxima and the NaN tests and selections of its special cases. The first
  version of this page gave 0.57 to 0.64 for sums on the M3: the classical loops then loaded their six
  pointers again in every iteration ([What changed](#what-changed)).
- **Arrays against the type in one register**: on Zen 2, with four lanes, a function on arrays takes
  0.40 to 0.65 of the type's 16-pass loop for sums and 0.49 to 0.55 for products; on the M3, two lanes
  as wide as the type's register, 0.94 to 0.99 and 1.03 to 1.04. `float` on arrays takes 0.49 to 0.67
  of `double`'s time (twice the lanes).
- **The placement of the arrays.** The kernels on the arrays of Milestone 2, whose loads fall 32 bytes
  modulo 4 KB from the previous iteration's stores, take 0.96 to 1.06 times the same kernels on the
  placed arrays, and its classical loops 1.03 to 1.61 times: the classical sum 1.5 to 1.6 times on the
  M3 and 1.1 times on Zen 2, the product 1.03 to 1.07. The two classical loops are the same
  operations; what differs is where their arrays lie, so this is the cost of the aliasing that the
  placement avoids, on a loop short enough to show it. The first version of this page saw none (0.90 to
  1.10), the placed loops then being slowed by their own loads of their pointers.

### 4. The scope of a function on arrays, by length

Each function on arrays holds a register-only scope for its call: upward on entry, the mode it found
on exit, the control register written only when it changes. Calls of `kairn::upward::add` and `mul`
on windows of L elements of arrays of 4096 (at least 64 calls per timed function, time per call):
`nearest`, from code that rounds to nearest, so that the scope writes the register twice per call;
`nested`, inside an outer `kairn::upward::Scope`, so that the scope reads it and writes nothing;
`none`, the generated array kernel that the function runs, inside the outer scope: the same call
without its scope. The scope's cost is `nearest` (or `nested`) minus `none`, its share
(`nearest` − `none`) / `nearest`. From 1024 elements of `double` the arrays no longer fit Zen 2's L1
(32 KB), from 4096 not the M3's (128 KB); there the scope is within the noise of calls of 0.2 to 5
µs.

<!-- BEGIN up_report lengths -->

| `kairn::upward::add` by length, times (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `add_4/nearest` | 24.9 | 24.3 to 24.7 | 21.6 | 21.4 |
| `add_4/nested` | 1.25 | 1.67 to 1.74 | 8.04 to 8.06 | 7.78 to 7.79 (-O2), 7.78 to 8.28 (-O3) |
| `add_4/none` | 1.17 | 1.28 (-O2), 1.18 (-O3) | 1.62 (-O2), 1.63 to 3.46 (-O3) | 1.63 |
| `add_16/nearest` | 25.8 to 27.6 (-O2), 26.7 to 26.8 (-O3) | 26.7 to 27.8 | 22.8 to 23.0 | 22.3 to 22.9 |
| `add_16/nested` | 4.17 to 4.21 (-O2), 3.60 to 3.61 (-O3) | 4.54 to 4.55 (-O2), 4.20 (-O3) | 9.55 to 9.60 (-O2), 10.3 to 11.4 (-O3) | 9.27 to 9.29 (-O2), 10.1 (-O3) |
| `add_16/none` | 3.58 to 3.73 | 3.61 to 3.72 | 4.52 to 6.36 (-O2), 4.37 to 4.38 (-O3) | 4.81 to 4.82 (-O2), 4.33 to 6.16 (-O3) |
| `add_64/nearest` | 36.5 to 36.9 | 36.3 to 36.8 | 27.5 to 27.6 | 27.4 to 27.5 (-O2), 51.2 to 51.3 (-O3) |
| `add_64/nested` | 13.7 to 14.2 | 13.8 to 14.0 | 16.5 to 18.5 (-O2), 16.5 (-O3) | 15.5 to 17.1 (-O2), 16.5 to 17.2 (-O3) |
| `add_64/none` | 13.5 to 14.2 | 13.4 | 15.3 to 16.0 | 15.0 to 15.2 |
| `add_256/nearest` | 76.1 to 76.2 | 75.6 to 75.7 | 65.3 to 65.6 | 65.2 to 65.6 |
| `add_256/nested` | 56.8 to 57.0 | 56.6 | 63.2 to 63.8 (-O2), 59.3 to 59.4 (-O3) | 60.2 to 62.5 |
| `add_256/none` | 56.2 | 56.4 to 56.7 | 59.2 to 60.0 | 58.4 to 58.5 (-O2), 63.7 to 63.9 (-O3) |
| `add_1024/nearest` | 226 to 230 | 230 to 231 | 421 to 469 (-O2), 469 (-O3) | 464 to 467 |
| `add_1024/nested` | 210 | 211 | 423 to 469 (-O2), 469 to 470 (-O3) | 465 to 467 |
| `add_1024/none` | 209 | 211 | 415 to 468 (-O2), 468 to 469 (-O3) | 464 |
| `add_4096/nearest` | 3142 to 3167 | 3115 to 3154 | 1847 to 1880 | 1845 to 1893 |
| `add_4096/nested` | 3159 to 3169 | 2981 to 3131 (-O2), 3140 to 3162 (-O3) | 1847 to 1878 | 1845 to 1890 |
| `add_4096/none` | 2972 to 3157 (-O2), 3142 to 3150 (-O3) | 2980 to 3111 (-O2), 3153 to 3161 (-O3) | 1846 to 1877 | 1843 to 1888 |

| `kairn::upward::add`: the scope of a call (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4: called from rounding to nearest, minus without the scope | 23.7 | 23.0 to 23.5 | 20.0 (-O2), 18.1 to 20.0 (-O3) | 19.8 |
| 16: called from rounding to nearest, minus without the scope | 22.0 to 23.9 | 23.1 to 24.1 | 16.5 to 18.3 (-O2), 18.6 (-O3) | 18.1 (-O2), 16.1 to 18.0 (-O3) |
| 64: called from rounding to nearest, minus without the scope | 22.5 to 23.4 | 22.9 to 23.4 | 11.6 to 12.3 | 12.5 (-O2), 36.0 to 36.1 (-O3) |
| 256: called from rounding to nearest, minus without the scope | 19.9 to 20.0 | 19.0 to 19.3 | 5.39 to 6.31 (-O2), 5.76 to 6.32 (-O3) | 6.81 to 7.27 (-O2), 1.50 to 1.81 (-O3) |
| 1024: called from rounding to nearest, minus without the scope | 16.7 to 20.6 (-O2), 20.4 to 20.8 (-O3) | 18.7 to 19.9 | -0.400 to 6.60 (-O2), -0.600 to 1.00 (-O3) | 1.30 to 2.70 (-O2), -0.300 to 3.10 (-O3) |
| 4096: called from rounding to nearest, minus without the scope | -15.0 to 180 (-O2), 14.0 to 20.0 (-O3) | 35.0 to 173 (-O2), -46.0 to -19.0 (-O3) | 1.00 to 4.00 (-O2), 1.00 to 3.00 (-O3) | 2.00 to 3.00 (-O2), 3.00 to 5.00 (-O3) |
| 4: inside an outer Scope, minus without the scope | 0.076 to 0.080 | 0.461 to 0.491 | 6.41 to 6.42 (-O2), 4.58 to 6.43 (-O3) | 6.15 to 6.64 |
| 16: inside an outer Scope, minus without the scope | 0.021 to 0.477 | 0.584 to 0.833 | 3.25 to 5.06 (-O2), 5.95 to 7.08 (-O3) | 4.46 to 4.47 (-O2), 3.89 to 5.75 (-O3) |
| 64: inside an outer Scope, minus without the scope | 0.100 to 0.220 | 0.410 to 0.610 | 0.540 to 2.57 (-O2), 1.11 to 1.17 (-O3) | 0.480 to 2.13 (-O2), 1.28 to 2.06 (-O3) |
| 256: inside an outer Scope, minus without the scope | 0.590 to 0.860 | -0.100 to 0.190 | 3.25 to 4.52 (-O2), -0.520 to 0.110 (-O3) | 1.81 to 1.88 (-O2), -1.54 to -1.17 (-O3) |
| 1024: inside an outer Scope, minus without the scope | 0.500 to 1.10 (-O2), 1.00 (-O3) | -0.300 to 0.000 | 1.00 to 8.40 (-O2), -0.500 to 1.40 (-O3) | 1.20 to 2.10 (-O2), 1.30 to 3.60 (-O3) |
| 4096: inside an outer Scope, minus without the scope | 2.00 to 191 (-O2), 18.0 to 24.0 (-O3) | 1.00 to 22.0 (-O2), -13.0 to 1.00 (-O3) | 1.00 to 4.00 (-O2), -4.00 to 1.00 (-O3) | 0.000 to 5.00 (-O2), 2.00 to 4.00 (-O3) |

| `kairn::upward::add`: the scope's share of a call from rounding to nearest | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4 | 0.95 | 0.95 | 0.92 (-O2), 0.84 to 0.92 (-O3) | 0.92 |
| 16 | 0.86 to 0.87 | 0.86 to 0.87 | 0.72 to 0.80 (-O2), 0.81 (-O3) | 0.79 (-O2), 0.72 to 0.81 (-O3) |
| 64 | 0.61 to 0.63 | 0.63 to 0.64 | 0.42 to 0.44 | 0.45 (-O2), 0.70 (-O3) |
| 256 | 0.26 | 0.25 to 0.26 | 0.08 to 0.10 | 0.10 to 0.11 (-O2), 0.02 to 0.03 (-O3) |
| 1024 | 0.07 to 0.09 | 0.08 to 0.09 | -0.00 to 0.02 | -0.00 to 0.01 |
| 4096 | -0.00 to 0.06 (-O2), 0.00 to 0.01 (-O3) | 0.01 to 0.05 (-O2), -0.01 (-O3) | 0.00 | 0.00 |

| `kairn::upward::mul` by length, times (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `mul_4/nearest` | 29.0 to 30.4 | 30.3 to 30.6 | 23.7 to 23.8 (-O2), 22.5 (-O3) | 22.2 |
| `mul_4/nested` | 4.62 to 4.68 (-O2), 4.44 (-O3) | 5.18 to 5.20 (-O2), 4.47 (-O3) | 12.4 (-O2), 8.94 to 8.96 (-O3) | 8.65 to 9.89 (-O2), 8.68 (-O3) |
| `mul_4/none` | 4.44 to 4.57 | 4.46 to 4.67 | 6.59 to 6.61 (-O2), 4.36 to 4.40 (-O3) | 3.96 to 3.98 (-O2), 3.96 to 5.68 (-O3) |
| `mul_16/nearest` | 40.4 to 43.3 (-O2), 40.5 to 43.3 (-O3) | 43.0 to 43.8 | 27.8 to 28.0 (-O2), 26.1 to 26.2 (-O3) | 26.1 |
| `mul_16/nested` | 16.7 to 17.0 | 16.7 to 17.3 | 17.5 (-O2), 15.9 to 16.0 (-O3) | 14.4 to 15.6 (-O2), 14.4 (-O3) |
| `mul_16/none` | 16.6 to 16.8 | 16.5 to 16.9 | 15.9 to 16.6 (-O2), 15.4 to 16.0 (-O3) | 13.8 (-O2), 13.9 to 14.7 (-O3) |
| `mul_64/nearest` | 93.6 to 93.7 | 91.2 to 92.2 | 72.0 to 73.4 | 64.0 to 65.3 |
| `mul_64/nested` | 65.5 to 65.6 | 63.3 to 64.8 | 60.4 to 61.6 | 53.6 to 55.3 |
| `mul_64/none` | 65.4 to 65.5 | 64.3 to 64.4 | 59.7 to 61.1 | 52.5 to 54.6 |
| `mul_256/nearest` | 290 | 284 | 248 to 250 | 220 to 221 |
| `mul_256/nested` | 263 | 258 to 259 | 236 to 240 | 210 to 212 |
| `mul_256/none` | 264 | 259 | 236 to 238 | 208 to 210 |
| `mul_1024/nearest` | 1072 to 1073 | 1050 to 1051 | 953 to 962 | 847 to 848 |
| `mul_1024/nested` | 1042 to 1043 | 1023 to 1025 | 952 to 956 | 840 to 842 |
| `mul_1024/none` | 1046 | 1024 to 1025 | 951 to 958 | 837 to 839 |
| `mul_4096/nearest` | 4197 to 4210 | 4121 to 4128 | 3795 to 3808 | 3348 to 3356 |
| `mul_4096/nested` | 4172 to 4176 | 4093 to 4102 | 3778 to 3795 | 3337 to 3349 |
| `mul_4096/none` | 4180 to 4187 | 4094 to 4102 | 3785 to 3800 | 3334 to 3345 |

| `kairn::upward::mul`: the scope of a call (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4: called from rounding to nearest, minus without the scope | 24.4 to 26.0 | 25.6 to 26.1 | 17.1 to 18.1 | 18.2 (-O2), 16.5 to 18.3 (-O3) |
| 16: called from rounding to nearest, minus without the scope | 23.8 to 26.6 (-O2), 23.7 to 26.5 (-O3) | 26.5 to 26.9 | 11.3 to 12.1 (-O2), 10.2 to 10.8 (-O3) | 11.4 to 12.4 |
| 64: called from rounding to nearest, minus without the scope | 28.1 to 28.2 | 26.9 to 27.9 | 13.1 to 13.5 (-O2), 11.0 to 12.6 (-O3) | 11.4 to 12.6 (-O2), 10.5 to 10.7 (-O3) |
| 256: called from rounding to nearest, minus without the scope | 25.4 to 25.5 | 24.8 to 25.4 | 12.1 to 12.8 (-O2), 11.7 to 13.2 (-O3) | 11.8 to 13.0 (-O2), 10.7 to 11.0 (-O3) |
| 1024: called from rounding to nearest, minus without the scope | 26.0 to 27.0 | 26.0 to 27.0 | 0.900 to 4.20 (-O2), -1.10 to 3.50 (-O3) | 9.20 to 10.6 (-O2), 9.50 to 10.6 (-O3) |
| 4096: called from rounding to nearest, minus without the scope | 11.0 to 14.0 (-O2), 21.0 to 30.0 (-O3) | 23.0 to 34.0 (-O2), 23.0 to 25.0 (-O3) | 8.00 to 13.0 (-O2), -1.00 to 10.0 (-O3) | 10.0 to 17.0 (-O2), 9.00 to 13.0 (-O3) |
| 4: inside an outer Scope, minus without the scope | 0.003 to 0.114 | 0.516 to 0.535 (-O2), 0.009 to 0.010 (-O3) | 5.79 to 5.82 (-O2), 4.56 to 4.58 (-O3) | 4.68 to 5.91 (-O2), 2.99 to 4.72 (-O3) |
| 16: inside an outer Scope, minus without the scope | -0.010 to 0.260 | 0.180 to 0.440 | 0.930 to 1.58 (-O2), 0.010 to 0.600 (-O3) | 0.560 to 1.80 (-O2), -0.290 to 0.440 (-O3) |
| 64: inside an outer Scope, minus without the scope | 0.050 to 0.130 | 0.370 to 0.390 (-O2), -0.960 to 0.000 (-O3) | 1.29 to 1.75 (-O2), 0.020 to 1.57 (-O3) | 0.980 to 2.82 (-O2), -0.840 to 0.510 (-O3) |
| 256: inside an outer Scope, minus without the scope | -1.50 to -1.10 | -0.200 to 0.200 | 0.200 to 2.10 (-O2), 0.000 to 3.70 (-O3) | 2.20 to 2.60 (-O2), 0.100 to 0.400 (-O3) |
| 1024: inside an outer Scope, minus without the scope | -4.00 to -3.00 (-O2), -4.00 to -3.00 (-O3) | 0.000 to 1.00 (-O2), -2.00 to 0.000 (-O3) | -3.00 to -1.70 (-O2), -1.10 to 2.50 (-O3) | 2.00 to 4.60 (-O2), 2.00 to 2.90 (-O3) |
| 4096: inside an outer Scope, minus without the scope | -14.0 to -10.0 (-O2), -12.0 to -8.00 (-O3) | -1.00 to 8.00 (-O2), -7.00 to -1.00 (-O3) | -11.0 to 2.00 (-O2), -21.0 to 2.00 (-O3) | 3.00 to 5.00 (-O2), 3.00 to 6.00 (-O3) |

| `kairn::upward::mul`: the scope's share of a call from rounding to nearest | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4 | 0.84 to 0.85 | 0.85 | 0.72 (-O2), 0.80 to 0.81 (-O3) | 0.82 (-O2), 0.74 to 0.82 (-O3) |
| 16 | 0.59 to 0.61 | 0.61 to 0.62 | 0.39 to 0.43 | 0.44 to 0.47 |
| 64 | 0.30 | 0.29 to 0.30 | 0.15 to 0.18 | 0.16 to 0.19 |
| 256 | 0.09 | 0.09 | 0.05 | 0.05 to 0.06 |
| 1024 | 0.02 to 0.03 | 0.02 to 0.03 | -0.00 to 0.00 | 0.01 |
| 4096 | 0.00 to 0.01 | 0.01 | -0.00 to 0.00 | 0.00 to 0.01 |

<!-- END up_report lengths -->

- **From rounding to nearest**, a call pays 23 to 26 ns for its scope on the M3 and 17 to 20 ns on
  Zen 2 at 4 elements: 72 to 95% of the call. On the M3 the cost stays about the same up to 256
  elements (19 to 24 ns for sums, 24 to 28 for products), as if a write of FPCR waited for the
  operations before it. On Zen 2 it shrinks with the length of the call, to 12 ns at 64 elements (36
  ns with Clang 18 at `-O3`) and 1.5 to 7.3 ns at 256 for sums (11 to 13 for products), as if the
  writes of MXCSR overlapped the work of a long call (an inference from the times; the machine code
  was not examined for this).
- **The share of the scope is about 10% of a call or less** on Zen 2 from 256 elements (sums 2 to
  11%, products 5 to 6%); on the M3 under 10% from 256 for products (9%) and from 1024 for sums (7 to
  9%; at 256, 25 to 26%). At 64 elements it is 42 to 70% of a sum and 15 to 30% of a product.
- **Inside an outer `Scope`**, where the function's scope only reads the register, a call costs at
  most 0.5 ns more than the kernel on the M3 (with GCC 16; nothing measurable with Apple clang), and
  4.6 to 6.6 ns at 4 elements and 3.3 to 7.1 at 16 for sums on Zen 2 (3.0 to 5.9 and up to 1.8 for
  products), at most about 3 ns from 64: a program that calls the functions on short arrays in a loop
  holds one `Scope` around the loop.

### 5. The scopes

The cost of a scope alone: 256 calls of a function of its own, not inlined, that holds a scope
around one sum (`upws/call/KERNEL/VARIANT`, time per call), minus the same calls without the scope.
`scope_add_1` holds a `kairn::upward::Scope` around a sum of the type, `regscope_add_1` the register-only
scope of the functions on arrays around the same sum, `nearest_add_1` a `kairn::upward::NearestScope`
around a sum of the default `Interval<double, 1>`; `change`, the scope changes the mode (called from
code that rounds to nearest, and for `NearestScope` from inside an upward `Scope`); `nested`, it
changes nothing (inside a `Scope`; `NearestScope` from code that rounds to nearest); `none`, the same
calls without the scope (inside an outer `Scope` for the sums of the type, from code that rounds to
nearest for the default sum).

<!-- BEGIN up_report scopes -->

| Calls of one operation, times (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upws/call/scope_add_1/none` | 0.883 to 0.890 | 0.877 to 0.890 | 1.98 to 2.16 (-O2), 2.10 to 2.13 (-O3) | 1.69 to 1.86 (-O2), 1.69 to 1.80 (-O3) |
| `upws/call/scope_add_1/change` | 22.5 to 23.4 (-O2), 23.8 (-O3) | 22.3 to 23.8 (-O2), 22.8 to 23.8 (-O3) | 52.3 to 52.5 (-O2), 124 (-O3) | 52.5 |
| `upws/call/scope_add_1/nested` | 0.875 to 0.890 | 1.38 to 1.42 | 14.3 | 15.1 to 15.5 |
| `upws/call/regscope_add_1/change` | 22.8 to 23.8 | 22.2 to 23.8 (-O2), 23.1 to 23.8 (-O3) | 21.3 | 21.3 |
| `upws/call/regscope_add_1/nested` | 0.877 to 0.893 | 1.32 to 1.42 (-O2), 1.39 to 1.42 (-O3) | 7.41 to 7.69 | 7.11 to 7.25 |
| `upws/call/nearest_add_1/none` | 2.14 | 2.75 to 3.03 (-O2), 2.78 to 2.97 (-O3) | 5.32 to 5.42 (-O2), 5.54 to 5.67 (-O3) | 5.62 to 5.75 |
| `upws/call/nearest_add_1/change` | 29.4 to 31.3 (-O2), 29.4 to 31.3 (-O3) | 29.2 to 30.3 | 56.1 to 56.3 (-O2), 56.2 to 97.0 (-O3) | 56.5 to 129 (-O2), 56.4 to 56.9 (-O3) |
| `upws/call/nearest_add_1/nested` | 2.56 to 2.60 | 3.75 to 3.79 (-O2), 3.46 to 3.72 (-O3) | 16.5 to 16.6 | 17.4 |

| The cost of a scope (ns per call: the call with it minus without it) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Scope` that changes the mode | 21.6 to 22.9 | 21.4 to 22.9 | 50.1 to 50.4 (-O2), 122 (-O3) | 50.7 to 50.9 |
| `Scope` inside a `Scope` (nothing changes) | -0.012 to 0.000 | 0.487 to 0.529 | 12.1 to 12.3 | 13.4 to 13.7 |
| register-only scope (of the functions on arrays) that changes the mode | 21.9 to 22.9 | 21.4 to 22.9 | 19.2 to 19.3 | 19.5 to 19.6 |
| register-only scope inside a `Scope` | -0.013 to 0.003 | 0.434 to 0.529 | 5.29 to 5.53 | 5.39 to 5.54 |
| `NearestScope` inside a `Scope` (changes the mode) | 27.2 to 29.2 | 26.2 to 27.2 | 50.7 to 51.0 (-O2), 50.5 to 91.3 (-O3) | 50.9 to 124 (-O2), 50.6 to 51.2 (-O3) |
| `NearestScope` where the mode is to nearest | 0.423 to 0.464 | 0.678 to 1.00 | 10.9 to 11.2 | 11.7 to 11.8 |

<!-- END up_report scopes -->

- **A scope that changes the mode** costs 21 to 23 ns on the M3 (two writes of FPCR, the register
  being the C library's mode there), 50 to 51 ns on Zen 2 and 9.5 ns with MSVC on the i5 (unpinned,
  [question 8](#8-msvc-unpinned)). With GCC 13 at `-O3` it cost 122 ns in every run of this program,
  where the program of the first version measured 52 ns: the function that holds the scope is the same
  instructions in both, at another address ([What changed](#what-changed)). The register-only scope
  of the functions on arrays costs the same on the M3 (21 to 23 ns) and with MSVC (9.3 ns), and 19 to
  20 ns on Zen 2: there the user-facing `Scope` also calls glibc's `fegetround` and `fesetround`, which
  read and write the x87 control word and MXCSR, and that costs 2.6 times the register's own read and
  writes.
- **A scope that changes nothing** costs one read of the register (and, for the user-facing scope on
  x86-64, one `fegetround`): nothing measurable on the M3 with Apple clang, 0.5 ns with GCC 16; 12 to
  14 ns on Zen 2 (5.3 to 5.5 for the register-only scope: a read of MXCSR and a test cost more there
  than a sum); 2.8 ns with MSVC (1.7 for the register-only one).
- **A `NearestScope` inside an upward region** costs what a `Scope` costs: 26 to 29 ns on the M3, 51
  ns on Zen 2 (in single runs 91 ns, GCC 13 at `-O3`, and 124 ns, Clang 18 at `-O2`), 6.9 ns with
  MSVC; where the mode is already to nearest, 0.4 to 1.0 ns on the M3, 11 to 12 ns on Zen 2, 0.6 to
  0.7 with MSVC.
- So a scope that changes the mode costs as much as 78 to 126 sums of the type on Zen 2 (305 with
  GCC 13 at `-O3`) and 70 to 76 on the M3, and against the default type it is repaid after 12 to 17
  sums on Zen 2 (39 with GCC 13 at `-O3`) and 14 to 16 on the M3 (each saving 2.9 to 4.1 ns, and about
  1.5). A scope around each operation, as in these calls, makes a call 24 to 31 times as long as
  without it (59 times with GCC 13 at `-O3`).

### 6. `float`

`kairn::upward::Interval<float>` (on x86-64 the two low lanes of an `__m128`, on arm64 a
`float32x2_t`), loops of sums and products, next to `Interval<float, 1>`; the functions on arrays of
`float` are in [question 3](#3-the-functions-on-arrays).

<!-- BEGIN up_report float -->

| `float`, times (ns per operation) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upwf/tp/interval_add_1/native` | 0.386 | 0.385 to 0.386 | 0.820 (-O2), 1.19 (-O3) | 0.598 to 0.599 (-O2), 0.819 to 0.820 (-O3) |
| `upwf/tp/interval_add_1/conv` | 1.27 | 1.10 (-O2), 1.04 (-O3) | 3.01 to 3.17 (-O2), 3.01 to 3.02 (-O3) | 3.56 to 3.57 |
| `m2f/tp/interval_add_1/op` | 1.87 | 0.867 to 0.868 | 1.76 | 5.11 to 5.12 |
| `m2f/tp/interval_add_1/fenv_loop` | 0.474 to 0.488 | 0.355 to 0.356 (-O2), 0.292 to 0.293 (-O3) | 1.22 to 1.24 | 1.62 to 1.64 |
| `upwf/tp/interval_mul_1/native` | 1.13 to 1.17 | 1.23 to 1.24 | 1.98 to 1.99 (-O2), 2.10 to 2.11 (-O3) | 1.98 to 2.40 (-O2), 2.29 (-O3) |
| `upwf/tp/interval_mul_1/conv` | 2.24 to 2.34 (-O2), 2.18 to 2.34 (-O3) | 2.12 to 2.19 | 5.70 to 5.71 (-O2), 5.71 to 6.05 (-O3) | 5.83 to 6.22 (-O2), 5.84 to 6.00 (-O3) |
| `m2f/tp/interval_mul_1/op` | 6.07 to 6.28 | 7.96 to 7.99 | 4.89 to 4.91 | 16.0 to 16.1 |
| `m2f/tp/interval_mul_1/fenv_loop` | 1.34 to 1.44 (-O2), 1.44 (-O3) | 0.583 to 0.594 | 1.47 to 1.48 | 4.19 to 4.43 (-O2), 3.81 to 3.84 (-O3) |

| `float`, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`: Interval<float, 1> over the type | 4.85 | 2.25 | 2.15 (-O2), 1.48 (-O3) | 8.55 to 8.57 (-O2), 6.24 to 6.25 (-O3) |
| `X * Y`: Interval<float, 1> over the type | 5.34 to 5.54 (-O2), 5.18 to 5.39 (-O3) | 6.41 to 6.45 | 2.47 (-O2), 2.32 to 2.34 (-O3) | 6.72 to 8.09 (-O2), 6.98 to 7.00 (-O3) |
| `X + Y`: the type over fenv_loop | 0.79 to 0.81 | 1.08 (-O2), 1.31 to 1.32 (-O3) | 0.66 to 0.67 (-O2), 0.97 to 0.98 (-O3) | 0.37 (-O2), 0.50 (-O3) |
| `X * Y`: the type over fenv_loop | 0.81 to 0.85 (-O2), 0.78 to 0.81 (-O3) | 2.09 to 2.12 | 1.35 to 1.36 (-O2), 1.42 to 1.44 (-O3) | 0.45 to 0.54 (-O2), 0.60 (-O3) |
| `X + Y`: converted over native | 3.30 | 2.87 (-O2), 2.69 to 2.70 (-O3) | 3.67 to 3.86 (-O2), 2.53 to 2.54 (-O3) | 5.97 (-O2), 4.35 to 4.36 (-O3) |
| `X * Y`: converted over native | 1.98 to 2.00 (-O2), 1.93 to 2.06 (-O3) | 1.76 (-O2), 1.71 to 1.72 (-O3) | 2.87 to 2.88 (-O2), 2.71 to 2.86 (-O3) | 2.44 to 3.14 (-O2), 2.55 to 2.62 (-O3) |

<!-- END up_report float -->

- The type with `float` takes 0.84 to 1.38 of its time with `double` (one register either way; 0.96
  to 1.06 on the M3, and on Zen 2 as far apart as the placement of the two loops sets them) and is 1.5
  to 8.6 times faster than `Interval<float, 1>` for sums and 2.3 to 8.1 times for products: less than
  with `double` where the compiler vectorizes the default type's `float` loop with twice the lanes
  (GCC 16 for sums, GCC 13 for sums and products), more where the default `float` loop is slower than
  the `double` one (Clang 18).
- On arrays, `float` takes 0.49 to 0.67 of `double`'s time, twice the lanes; a sum costs 0.15 to 0.20
  ns per interval, a product 0.46 to 0.62.

### 7. The checked build

`kairn-bench-up-checks-LEVEL` is the same program with `KAIRN_CHECKS` 1 in every file: before each
operation that rounds, the header reads the control register (the mode upward, flush to zero off) and
tests that its operands are canonical; before each exact one, flush to zero; on entry of a scope that
writes the mode, the check that the file's build honors it (one call); the functions on arrays check
the lengths, the overlaps and every element. The two programs ran alternately with the same filter on
the same CPU (on Zen 2), and each ratio is of the two runs of one pair; the default type's own checks
(the mode to nearest before an operation) are beside it for scale.

<!-- BEGIN up_report checks -->

| With `KAIRN_CHECKS` 1 over without, the same run order | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/tp/interval_add_1/native` | 4.75 to 5.09 (-O2), 4.44 to 4.79 (-O3) | 5.63 to 5.76 (-O2), 5.08 (-O3) | 13.9 to 14.2 (-O2), 5.90 to 5.92 (-O3) | 12.7 to 15.2 (-O2), 9.2 to 11.2 (-O3) |
| `upw/tp/interval_add_1/native_x16` | 6.08 to 6.28 (-O2), 6.08 to 6.18 (-O3) | 6.94 to 6.96 (-O2), 6.11 to 6.24 (-O3) | 12.7 to 12.8 (-O2), 20.2 to 20.3 (-O3) | 14.0 to 14.1 (-O2), 20.9 to 22.3 (-O3) |
| `upw/tp/interval_add_1/conv` | 3.50 to 3.59 (-O2), 3.45 to 3.48 (-O3) | 4.67 to 4.72 (-O2), 5.00 (-O3) | 4.47 to 4.49 | 8.52 to 8.73 |
| `upw/tp/interval_mul_1/native` | 2.13 | 1.99 to 2.01 | 4.25 to 4.26 (-O2), 3.92 to 4.50 (-O3) | 4.98 to 4.99 (-O2), 3.70 to 4.72 (-O3) |
| `upw/tp/interval_mul_1/native_x16` | 2.23 | 2.10 to 2.11 | 4.78 to 4.85 | 5.32 to 5.42 |
| `upw/tp/interval_mul_1/conv` | 2.20 to 2.21 | 2.54 (-O2), 2.62 (-O3) | 2.46 (-O2), 2.46 to 2.54 (-O3) | 5.16 to 5.17 (-O2), 5.40 to 5.50 (-O3) |
| `upw/sum/interval_add_1/native` | 2.41 to 2.60 (-O2), 2.41 to 2.48 (-O3) | 2.71 to 2.76 (-O2), 2.65 to 2.75 (-O3) | 5.39 to 7.94 (-O2), 6.89 to 8.22 (-O3) | 6.75 to 9.29 (-O2), 8.86 to 8.87 (-O3) |
| `upw/sum/interval_add_1/native_x16` | 2.63 to 2.81 (-O2), 2.65 to 2.84 (-O3) | 2.88 | 8.52 to 8.64 | 9.75 to 9.87 |
| `upw/prod/interval_mul_1/native` | 1.01 to 1.02 (-O2), 0.94 to 1.05 (-O3) | 1.06 to 1.10 | 1.37 to 1.47 (-O2), 1.47 (-O3) | 2.24 to 2.69 (-O2), 2.72 to 2.73 (-O3) |
| `upw/prod/interval_mul_1/native_x16` | 0.99 to 1.01 | 1.02 to 1.09 (-O2), 1.02 to 1.09 (-O3) | 1.51 to 1.52 | 2.66 to 2.72 |
| `upwf/tp/interval_add_1/native` | 4.75 | 5.07 | 9.77 to 9.80 (-O2), 6.73 to 6.75 (-O3) | 15.7 (-O2), 11.1 (-O3) |
| `upwf/tp/interval_mul_1/native` | 2.12 to 2.17 | 2.00 | 4.34 to 4.35 (-O2), 4.09 to 4.17 (-O3) | 4.11 to 4.99 (-O2), 4.29 to 4.36 (-O3) |
| `upwa/tp/interval_add_1/op` | 6.58 to 6.60 | 10.0 | 18.0 to 18.3 (-O2), 17.1 to 17.3 (-O3) | 14.7 to 19.5 (-O2), 19.4 to 19.5 (-O3) |
| `upwa/tp/interval_mul_1/op` | 2.46 to 2.47 | 3.44 to 3.66 (-O2), 3.42 (-O3) | 5.53 to 5.56 (-O2), 5.24 to 5.29 (-O3) | 6.40 to 6.48 |
| `upwaf/tp/interval_add_1/op` | 9.47 to 9.57 | 14.8 to 15.0 | 29.5 to 30.0 | 33.4 to 33.7 (-O2), 33.0 to 34.9 (-O3) |
| `upwaf/tp/interval_mul_1/op` | 3.63 to 3.66 | 5.38 to 5.39 | 9.62 to 9.90 | 11.1 to 11.2 |
| `upws/call/scope_add_1/change` | 1.08 to 1.10 | 1.13 to 1.22 (-O2), 1.13 (-O3) | 2.50 to 2.57 (-O2), 0.50 to 0.97 (-O3) | 1.16 (-O2), 1.15 to 1.78 (-O3) |
| `upws/call/scope_add_1/nested` | 2.79 to 2.83 | 2.68 to 2.84 (-O2), 2.59 to 2.68 (-O3) | 1.55 | 1.47 to 1.51 (-O2), 1.46 to 1.47 (-O3) |
| `upws/call/regscope_add_1/change` | 1.08 | 1.13 (-O2), 1.08 to 1.13 (-O3) | 1.41 to 1.42 | 1.43 |
| `m2/tp/interval_add_1/op` | 1.71 | 2.31 to 2.37 | 2.83 to 2.85 | 3.58 to 3.59 |
| `m2/tp/interval_mul_1/op` | 1.16 to 1.20 (-O2), 1.23 (-O3) | 1.10 | 2.16 to 2.18 | 1.32 to 1.33 |
| `m2/sum/interval_add_1/op` | 0.94 to 0.96 (-O2), 1.01 (-O3) | 1.08 to 1.17 (-O2), 1.08 (-O3) | 1.92 to 1.93 | 2.39 to 2.41 |
| `m2/prod/interval_mul_1/op` | 0.98 to 1.02 | 1.05 to 1.08 | 1.11 to 1.12 | 1.28 to 1.29 |

<!-- END up_report checks -->

- The assertions cost most where an operation costs least: a loop of sums of the type takes 4.4 to 5.8
  times as long on the M3 and 5.9 to 15 times on Zen 2 (with 16 loops per scope 6.1 to 7.0 and 13 to
  22), a loop of products 2.0 to 2.2 and 3.7 to 5.4 times, a chain of sums 2.4 to 2.9 and 5.4 to 9.9, a
  chain of products 0.94 to 1.10 and 1.4 to 2.7 (the checks are off its critical path). A read of MXCSR
  is dear on Zen 2 ([question 5](#5-the-scopes): a scope that only reads it costs 5.3 to 5.5 ns), which
  is what each operation now does.
- The functions on arrays, which test every element, take 6.6 to 10 times as long for sums of `double`
  on the M3 and 15 to 20 on Zen 2, 2.5 to 3.7 and 5.2 to 6.5 for products; with `float` 9.5 to 15 and
  30 to 35, 3.6 to 5.4 and 9.6 to 11.2.
- A call of one sum in a scope that changes the mode takes 1.08 to 1.22 times as long on the M3 and
  1.15 to 2.6 on Zen 2 (the check of the build on the scope's entry, and the sum's own checks; with GCC
  13 at `-O3` 0.50 to 0.97, the program without the checks taking 124 ns for that call: [question
  5](#5-the-scopes)); in a scope that changes nothing, 1.5 to 2.8 times (the sum's checks).
- The default `Interval<T, 1>` pays 1.7 to 3.6 times for its sums with its own checks, and 0.94 to 2.4
  for its chains: the checked build is a build to find mistakes in, not to measure.

### 8. MSVC, unpinned

One short item on the i5 with MSVC 19.52 at `/O2 /arch:AVX2` (the file of the type with `/fp:strict`,
where the barrier of each scope is the refresh and the pin of the design page's section "MSVC"):
the type's sums, products and chains, and the scopes, next to the default type, **unpinned** (the
thread may run on a performance or an efficiency core), on another project's CI machine with no build
running during the runs; three runs, the spread at the median function 1.011 to 1.017.

<!-- BEGIN up_report msvc -->

| MSVC, times (ns per operation or step), unpinned | i5-13500T, MSVC (unpinned) |
|---|---|
| `upw/tp/interval_add_1/native` | 0.301 to 0.312 (-O2) |
| `upw/tp/interval_add_1/native_x16` | 0.276 (-O2) |
| `upw/tp/interval_add_1/conv` | 2.09 to 2.11 (-O2) |
| `m2/tp/interval_add_1/op` | 6.95 to 6.96 (-O2) |
| `m2/tp/interval_add_1/fenv_loop` | 0.512 to 0.513 (-O2) |
| `upw/tp/interval_mul_1/native` | 1.43 (-O2) |
| `upw/tp/interval_mul_1/native_x16` | 1.41 (-O2) |
| `upw/tp/interval_mul_1/conv` | 3.64 (-O2) |
| `m2/tp/interval_mul_1/op` | 20.6 (-O2) |
| `m2/tp/interval_mul_1/fenv_loop` | 1.60 (-O2) |
| `upw/sum/interval_add_1/native` | 0.749 to 0.750 (-O2) |
| `m2/sum/interval_add_1/op` | 9.18 (-O2) |
| `upw/sum/interval_add_1/native_x16` | 0.866 (-O2) |
| `upw/prod/interval_mul_1/native` | 5.10 to 5.11 (-O2) |
| `upw/prod/interval_mul_1/native_x16` | 5.17 (-O2) |
| `upw/prod/interval_mul_1/conv` | 5.22 to 5.24 (-O2) |
| `m2/prod/interval_mul_1/op` | 23.4 (-O2) |
| `m2/prod/interval_mul_1/fenv_loop` | 3.42 (-O2) |

| MSVC, ratios, unpinned | i5-13500T, MSVC (unpinned) |
|---|---|
| `X + Y`: Interval<T, 1> over the type | 22.3 to 23.1 (-O2) |
| `X + Y`: Interval<T, 1> over the type, 16 loops per scope | 25.1 to 25.2 (-O2) |
| `X * Y`: Interval<T, 1> over the type | 14.4 (-O2) |
| `X * Y`: Interval<T, 1> over the type, 16 loops per scope | 14.6 (-O2) |
| `S + X`: Interval<T, 1> over the type | 12.2 (-O2) |
| `P * X`: Interval<T, 1> over the type | 4.59 to 4.60 (-O2) |
| `P * X`: Interval<T, 1> over the type, a chain 16 times as long per scope | 4.54 (-O2) |
| `X + Y`: the type over fenv_loop | 0.59 to 0.61 (-O2) |
| `X * Y`: the type over fenv_loop | 0.90 (-O2) |
| `P * X`: the type over fenv_loop | 1.49 to 1.50 (-O2) |

| Calls of one operation, times (ns per call) | i5-13500T, MSVC (unpinned) |
|---|---|
| `upws/call/scope_add_1/none` | 0.786 (-O2) |
| `upws/call/scope_add_1/change` | 10.3 (-O2) |
| `upws/call/scope_add_1/nested` | 3.60 (-O2) |
| `upws/call/regscope_add_1/change` | 10.1 (-O2) |
| `upws/call/regscope_add_1/nested` | 2.50 to 2.52 (-O2) |
| `upws/call/nearest_add_1/none` | 8.24 (-O2) |
| `upws/call/nearest_add_1/change` | 15.1 (-O2) |
| `upws/call/nearest_add_1/nested` | 8.87 to 8.93 (-O2) |

| The cost of a scope (ns per call: the call with it minus without it) | i5-13500T, MSVC (unpinned) |
|---|---|
| `Scope` that changes the mode | 9.47 to 9.49 (-O2) |
| `Scope` inside a `Scope` (nothing changes) | 2.81 to 2.82 (-O2) |
| register-only scope (of the functions on arrays) that changes the mode | 9.27 to 9.28 (-O2) |
| register-only scope inside a `Scope` | 1.72 to 1.74 (-O2) |
| `NearestScope` inside a `Scope` (changes the mode) | 6.87 to 6.89 (-O2) |
| `NearestScope` where the mode is to nearest | 0.632 to 0.694 (-O2) |

<!-- END up_report msvc -->

- With MSVC the default type is slow (7.0 ns per sum, 21 ns per product, 23 ns per step of a product
  chain), the type not (0.30, 1.43 and 5.1 ns): 14 to 25 times faster in loops (22 to 25 for sums, 14
  to 15 for products), 12 times in a chain of sums, 4.5 to 4.6 times in a chain of products. The type
  is faster than the classical loop under one mode for sums (0.59 to 0.61) and matches it for
  products (0.90); 1.49 for the chain of products. The first version of this page gave 0.53 ns per
  sum: MSVC's loop too was faster with the pointers in locals ([What changed](#what-changed)).
- A scope that changes the mode costs 9.5 ns, the register-only one 9.3 ns, a `NearestScope` in an
  upward region 6.9 ns; a scope that changes nothing 2.8 ns (1.7): the write of MXCSR through a function
  of its own, the refresh of the zero and the C library's mode are cheaper on this machine than on Zen 2.

## How it was measured

| Machine | Configurations | Conditions |
|---|---|---|
| M3: macOS 26.6 arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2; `-O2` and `-O3`; NEON (the functions on arrays and the packed kernels: 2 lanes of `double`, 4 of `float`) | shared with the builds and tests of other authors: each run started when the 1-minute load average was under 6 (`up_run.py --max-load 6`; it was 1.8 to 5.8 at the start and the end of the timing, as recorded); no affinity, the thread in the user-interactive class; a run whose spread at the median function (the median over the functions of the median over the minimum of their 31 samples) was above 5% set aside and made again, up to six times; three kept runs and three kept pairs of the checked build per configuration |
| Zen 2: Linux x86-64 (Ubuntu 24.04), AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1; `-O2` and `-O3`; `-mfma`, the functions on arrays and the packed kernels `-mavx2 -mfma` (4 lanes of `double`, 8 of `float`) | the four configurations at once, each in a core complex of its own of the first socket (logical CPUs 4 to 7, 12 to 15, 20 to 23 and 28 to 31); each run pinned (`taskset`, `--cpu`) to the CPU of its range whose usage and its SMT sibling's (CPU + 64) were the lowest over the 2 s before it, the usage of the two sampled every 5 s from `/proc/stat` during the run; a run whose sibling was busy (above 10% in a sample) or whose spread at the median function was above 5% set aside and made again, up to four times; four kept runs and four kept pairs per configuration; the machine was shared (load average 4.5 to 6.5 at the start and the end of the runs, other users' jobs); the sibling of every kept run was busy at most 2% in a sample |
| i5: Windows 11 x64, Intel Core i5-13500T (6 performance, 8 efficiency cores) | MSVC 19.52, `/O2 /arch:AVX2`, the file of the type `/fp:strict` | not pinned (the thread may run on either kind of core); another project's CI machine, no build running on it during the runs; one item (the sums, the products, the product chain and the scopes, next to the default type), three kept runs, the same rule of 5% |

- **Commit**: `e4328d39` on every machine, recorded in every JSON file: the tree of version 0.4.1,
  with the harness repaired (`5799f44c`) and the shorter test of an empty operand on arm64. The runs
  of the first version, at `4710839b`, are in `results/upward/bench/4710839b/`; the measurements of
  [What changed](#what-changed) made alternately, two programs on one machine, in
  `results/upward/bench/unord/` and `results/upward/bench/placement/`.
- **Flags**: those of `kairn-bench-m2` ([Milestone 2](bench-milestone2.md#how-it-was-measured)):
  hardware FMA as `kairn::fma` gives it, `-ffp-contract=off`, `NDEBUG` (so `KAIRN_CHECKS` is 0 but in
  the checked programs); the two files that include `kairn/upward.hpp` (`bench/up_type.cpp`,
  `bench/up_arrays.cpp`) also the option of `kairn::upward`, `-frounding-math` or `/fp:strict`; the
  props of the rounding mode `-frounding-math` (`/fp:strict`), and with Clang `FENV_ACCESS`; no other
  file gets either option. Recorded in each file (`flags`, `upward_flags`, `fenv_flags`).
- **Inputs**: those of Milestone 2: 256 intervals per array from a fixed seed, centers
  $\pm[1, 2) \cdot 2^k$ with $k \in [-8, 8]$ and half-width $2^{-30}$ (`double`) or $2^{-12}$ (`float`)
  of the center, factors in $[2^{-1/4}, 2^{1/4})$; Horner on $T_8$ at narrow arguments in $[-1, 1]$;
  the determinant's four points the elements $i$, $i + 64$, $i + 128$, $i + 192$ (modulo 256) of the
  arrays X, Y, F as their three coordinates; the functions on arrays by length on arrays of 4096
  elements made of the same intervals. No overflow, no subnormal operand, no product below
  $2^{2p-1}\eta$ (where the default product may be one number wider).
- **Placement**: the arrays of the new loops are placed at offsets modulo 4 KB that keep every
  store at least 1 KB from the loads of the same loop
  ([bench/README.md](https://github.com/danielepanozzo/kairn/tree/main/bench), "The round-up
  interval"). The packed code of Milestone 2 on its own arrays (`m2p`), whose loads fall 32 bytes
  from the previous iteration's stores modulo 4 KB, takes 0.96 to 1.06 times the same kernels on the
  placed arrays, and 1.03 to 1.61 times the same classical loops: the aliasing costs the short
  classical sum 1.5 to 1.6 times on the M3 ([question 3](#3-the-functions-on-arrays)). Each timed
  function holds the pointers of its arrays in locals ([What changed](#what-changed)).
- **Checks before timing**: every timed function, 125 per configuration (32 with MSVC), against
  Kairn's default kernels on the same operands, as [Runs](#runs) counts them: every bound of the
  round-up interval's functions equal to the default's, no zero of the other sign on these operands,
  no product tighter (none below $2^{2p-1}\eta$ here); the determinants of the default types byte for
  byte against their generated kernels. None failed in any run. Of the values compared, 46% differ
  from the same computation rounded to nearest: a function that ignored the mode would have failed.
- **Statistic**: the minimum over 31 samples of about 4 ms; ratios and differences of minima within
  one run (for the checked build, within one pair of programs run one after the other on the same
  CPU); a cell is the lowest and highest value over the runs.
- **Measured**: the times, the agreement with the default kernels. **Inferred**: the explanations,
  which are readings of the tables (and, where said, of the machine code); the cost of a scope, which
  is a difference of two measured times.

## What was set aside

[Runs](#runs) lists, per configuration, every run made, the runs kept, and those set aside with the
reason. At `e4328d39` no run was set aside on the M3 or on Zen 2: every run and pair was kept at its
first attempt; with MSVC, one attempt of the first run (spread 1.066). On the M3 a whole run can be a
few percent faster or slower than another, and one campaign than another (the default type's chains
2% to 7% faster in this one than in the first, on the same code), which moves the times and not the
ratios within a run.

The campaign of the first version of this page, at `4710839b`, is stored in
`results/upward/bench/4710839b/`, its runs and its attempts as that version's tables used them; it
was replaced because its program slowed some of its own loops ([What changed](#what-changed)). In
it, on the M3, runs with a spread above 5% at the median function had been set aside and made again:
5 of Apple clang's at `-O3` and 8 of GCC 16's; of the pairs of the checked build, 57 of Apple clang's
at `-O3` and 3 of GCC 16's; with MSVC, two attempts. Two earlier campaigns of that day are not
stored: one at `d971de5e` on Zen 2 and the M3, before the 16-pass difference and chains were added;
and one at `8f34267d`, whose 16-pass chain of sums of the rounding-mode prop added through an
interval type that negates twice per step, where `m2_fenv.cpp` keeps the lower bound negated and
adds once (on the M3 2.2 times slower than the prop it was meant to repeat).

## Not measured

- The round-up interval with the two-number form forced (`KAIRN_UPWARD_FORM_NUMBERS`), clang-cl, and
  the functions on arrays, the determinant, Horner and `float` with MSVC (one short table only, as
  planned); MSVC pinned to a performance core; the machine code of MSVC's loops.
- The cause of the times that the placement of the code moved on Zen 2 ([What changed](#what-changed)),
  and the arm64 jobs of CI (GCC and Clang on Linux), whose machine code for the shorter test of an
  empty operand was not examined.
- The predicates, comparisons, hull and intersection of the type, and its operations with a number
  (`x + t`, `x * t`); `neg` on arrays and the functions on arrays with a number.
- Threads; a scope in one file and the operations in another; a DLL.
- The array of pairs $(u, n)$ interleaved, which the design serves with the type and
  `from_limbs`/`to_limbs` (the loops `native` read arrays of the type, which is that layout).
- Intel processors other than the i5, AVX-512, GPUs.
- Compile time.

## Runs

<!-- BEGIN up_report configurations -->

| Configuration | CPU | Compiler | Flags | The units of the round-up interval | Runs | Date, commit |
|---|---|---|---|---|---:|---|
| linux-clang-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `e4328d39` |
| linux-clang-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `e4328d39` |
| linux-gcc-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `e4328d39` |
| linux-gcc-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `e4328d39` |
| mac-appleclang-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `e4328d39` |
| mac-appleclang-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `e4328d39` |
| mac-gcc16-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `e4328d39` |
| mac-gcc16-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `e4328d39` |
| windows-msvc-O2 | 13th Gen Intel(R) Core(TM) i5-13500T; not pinned | MSVC 19.52.37029 | `/DWIN32 /D_WINDOWS /EHsc /O2 /Ob2 /DNDEBUG /O2 /arch:AVX2` | `... /fp:strict` | 3 | 2026-11-27, `e4328d39` |

<!-- END up_report configurations -->

<!-- BEGIN up_report counts -->

| Checks of | Functions checked, failed | Of the round-up interval's: compared with the default kernels, values, equal, zero of the other sign, one number tighter; not the value rounded to nearest | Compared byte for byte (the default types' determinant) |
|---|---|---|---|
| linux-clang-O2 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| linux-clang-O3 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| linux-gcc-O2 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| linux-gcc-O3 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| mac-appleclang-O2 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| mac-appleclang-O3 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| mac-gcc16-O2 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| mac-gcc16-O3 | 125, 0 | 96 functions: 99348, 99348, 0, 0; 45343 | 5 functions, 3072 values |
| windows-msvc-O2 | 32, 0 | 24 functions: 8208, 8208, 0, 0; 3392 | 0 functions, 0 values |

<!-- END up_report counts -->

<!-- BEGIN up_report spread -->

| Spread of | Runs | A function over the runs: median, 90th percentile, worst | Worst function |
|---|---:|---|---|
| linux-clang-O2 | 4 | 0.3%, 3.2%, 128.8% | `upws/call/nearest_add_1/change` |
| linux-clang-O3 | 4 | 0.2%, 3.1%, 43.5% | `upwa/call/mul_4/none` |
| linux-gcc-O2 | 4 | 0.3%, 1.8%, 45.0% | `upw/sum/interval_add_1/native` |
| linux-gcc-O3 | 4 | 0.3%, 1.7%, 112.8% | `upwa/call/add_4/none` |
| mac-appleclang-O2 | 3 | 0.4%, 5.3%, 7.4% | `upwa/call/mul_16/nearest` |
| mac-appleclang-O3 | 3 | 0.1%, 1.6%, 7.2% | `upwf/tp/interval_mul_1/conv` |
| mac-gcc16-O2 | 3 | 0.1%, 1.6%, 10.3% | `upws/call/nearest_add_1/none` |
| mac-gcc16-O3 | 3 | 0.1%, 1.7%, 7.6% | `upws/call/nearest_add_1/nested` |
| windows-msvc-O2 | 3 | 0.1%, 0.6%, 3.4% | `upw/tp/interval_add_1/native` |

<!-- END up_report spread -->

<!-- BEGIN up_report attempts -->

| Configuration, item | Runs made | Kept | Set aside: for the spread at the median function; for a busy sibling (its busiest 5 s) |
|---|---:|---:|---|
| linux-clang-O2-checks | 8 | 8 | none |
| linux-clang-O2-main | 4 | 4 | none |
| linux-clang-O3-checks | 8 | 8 | none |
| linux-clang-O3-main | 4 | 4 | none |
| linux-gcc-O2-checks | 8 | 8 | none |
| linux-gcc-O2-main | 4 | 4 | none |
| linux-gcc-O3-checks | 8 | 8 | none |
| linux-gcc-O3-main | 4 | 4 | none |
| mac-appleclang-O2-checks | 6 | 6 | none |
| mac-appleclang-O2-main | 3 | 3 | none |
| mac-appleclang-O3-checks | 6 | 6 | none |
| mac-appleclang-O3-main | 3 | 3 | none |
| mac-gcc16-O2-checks | 6 | 6 | none |
| mac-gcc16-O2-main | 3 | 3 | none |
| mac-gcc16-O3-checks | 6 | 6 | none |
| mac-gcc16-O3-main | 3 | 3 | none |
| windows-msvc-O2-msvc | 4 | 3 | 1, spread 1.066 to 1.066 |

<!-- END up_report attempts -->

<!-- BEGIN up_report runs -->

| Run | CPU, its sibling: busiest 5 s, mean | Spread within the run (median function) | Over the fastest run of its configuration: median, 90th percentile | Load average (1 min) at start, end |
|---|---|---|---|---|
| `main-linux-clang-O2-r1.json` | 21, 85: 0%, 0.0% | 1.005 | 1.002, 1.007 | 4.5, 5.1 |
| `main-linux-clang-O2-r2.json` | 20, 84: 0%, 0.0% | 1.005 | 1.001, 1.005 | 5.1, 5.6 |
| `main-linux-clang-O2-r3.json` | 20, 84: 0%, 0.0% | 1.005 | 1.001, 1.007 | 5.6, 6.0 |
| `main-linux-clang-O2-r4.json` | 20, 84: 0%, 0.1% | 1.004 | 1.000, 1.007 | 5.7, 5.8 |
| `main-linux-clang-O3-r1.json` | 29, 93: 0%, 0.1% | 1.005 | 1.001, 1.009 | 4.5, 5.1 |
| `main-linux-clang-O3-r2.json` | 28, 92: 2%, 0.9% | 1.006 | 1.001, 1.007 | 5.1, 5.6 |
| `main-linux-clang-O3-r3.json` | 28, 92: 0%, 0.0% | 1.006 | 1.001, 1.006 | 5.4, 6.0 |
| `main-linux-clang-O3-r4.json` | 28, 92: 0%, 0.1% | 1.005 | 1.001, 1.007 | 5.7, 5.7 |
| `main-linux-gcc-O2-r1.json` | 6, 70: 1%, 0.3% | 1.006 | 1.001, 1.008 | 4.5, 5.1 |
| `main-linux-gcc-O2-r2.json` | 6, 70: 1%, 0.3% | 1.007 | 1.001, 1.005 | 5.1, 5.6 |
| `main-linux-gcc-O2-r3.json` | 7, 71: 0%, 0.2% | 1.008 | 1.001, 1.009 | 5.4, 6.0 |
| `main-linux-gcc-O2-r4.json` | 5, 69: 0%, 0.1% | 1.005 | 1.000, 1.004 | 5.7, 5.8 |
| `main-linux-gcc-O3-r1.json` | 15, 79: 1%, 0.4% | 1.006 | 1.000, 1.005 | 4.5, 5.1 |
| `main-linux-gcc-O3-r2.json` | 12, 76: 0%, 0.0% | 1.006 | 1.002, 1.005 | 5.1, 5.6 |
| `main-linux-gcc-O3-r3.json` | 12, 76: 0%, 0.0% | 1.006 | 1.002, 1.008 | 5.4, 6.0 |
| `main-linux-gcc-O3-r4.json` | 12, 76: 0%, 0.0% | 1.004 | 1.001, 1.006 | 5.7, 5.8 |
| `main-mac-appleclang-O2-r1.json` | not pinned | 1.007 | 1.000, 1.003 | 5.8, 4.5 |
| `main-mac-appleclang-O2-r2.json` | not pinned | 1.003 | 1.001, 1.037 | 4.5, 3.9 |
| `main-mac-appleclang-O2-r3.json` | not pinned | 1.003 | 1.002, 1.045 | 3.9, 3.3 |
| `main-mac-appleclang-O3-r1.json` | not pinned | 1.003 | 1.000, 1.008 | 4.0, 3.2 |
| `main-mac-appleclang-O3-r2.json` | not pinned | 1.004 | 1.000, 1.004 | 3.2, 3.3 |
| `main-mac-appleclang-O3-r3.json` | not pinned | 1.003 | 1.000, 1.006 | 3.3, 2.9 |
| `main-mac-gcc16-O2-r1.json` | not pinned | 1.003 | 1.000, 1.012 | 4.2, 3.5 |
| `main-mac-gcc16-O2-r2.json` | not pinned | 1.003 | 1.000, 1.004 | 3.5, 3.0 |
| `main-mac-gcc16-O2-r3.json` | not pinned | 1.003 | 1.000, 1.007 | 3.0, 2.5 |
| `main-mac-gcc16-O3-r1.json` | not pinned | 1.003 | 1.000, 1.007 | 1.8, 1.9 |
| `main-mac-gcc16-O3-r2.json` | not pinned | 1.003 | 1.000, 1.004 | 1.9, 3.0 |
| `main-mac-gcc16-O3-r3.json` | not pinned | 1.003 | 1.000, 1.008 | 3.0, 2.9 |
| `msvc-windows-msvc-O2-r1.json` | not pinned | 1.017 | 1.000, 1.002 | -1.0, -1.0 |
| `msvc-windows-msvc-O2-r2.json` | not pinned | 1.011 | 1.000, 1.003 | -1.0, -1.0 |
| `msvc-windows-msvc-O2-r3.json` | not pinned | 1.011 | 1.000, 1.001 | -1.0, -1.0 |
| `checks-linux-clang-O2-c0-r1.json` | 20, 84: 0%, 0.0% | 1.005 | 1.002, 1.006 | 5.7, 5.8 |
| `checks-linux-clang-O2-c0-r2.json` | 20, 84: 0%, 0.0% | 1.004 | 1.000, 1.009 | 6.1, 6.3 |
| `checks-linux-clang-O2-c0-r3.json` | 20, 84: 0%, 0.0% | 1.004 | 1.000, 1.003 | 6.2, 6.4 |
| `checks-linux-clang-O2-c0-r4.json` | 20, 84: 0%, 0.0% | 1.004 | 1.002, 1.018 | 6.4, 6.5 |
| `checks-linux-clang-O2-c1-r1.json` | 20, 84: 0%, 0.0% | 1.004 | 1.002, 1.005 | 5.8, 6.1 |
| `checks-linux-clang-O2-c1-r2.json` | 20, 84: 0%, 0.0% | 1.003 | 1.000, 1.003 | 6.3, 6.2 |
| `checks-linux-clang-O2-c1-r3.json` | 20, 84: 0%, 0.0% | 1.003 | 1.000, 1.003 | 6.4, 6.4 |
| `checks-linux-clang-O2-c1-r4.json` | 20, 84: 0%, 0.0% | 1.004 | 1.001, 1.006 | 6.5, 6.5 |
| `checks-linux-clang-O3-c0-r1.json` | 28, 92: 0%, 0.0% | 1.006 | 1.001, 1.006 | 5.7, 5.8 |
| `checks-linux-clang-O3-c0-r2.json` | 29, 93: 0%, 0.0% | 1.004 | 1.002, 1.008 | 6.1, 6.2 |
| `checks-linux-clang-O3-c0-r3.json` | 28, 92: 0%, 0.2% | 1.004 | 1.000, 1.004 | 6.2, 6.4 |
| `checks-linux-clang-O3-c0-r4.json` | 28, 92: 0%, 0.0% | 1.004 | 1.000, 1.004 | 6.4, 6.5 |
| `checks-linux-clang-O3-c1-r1.json` | 28, 92: 0%, 0.2% | 1.004 | 1.001, 1.014 | 5.8, 6.1 |
| `checks-linux-clang-O3-c1-r2.json` | 29, 93: 0%, 0.0% | 1.004 | 1.001, 1.005 | 6.2, 6.2 |
| `checks-linux-clang-O3-c1-r3.json` | 28, 92: 0%, 0.0% | 1.003 | 1.001, 1.006 | 6.4, 6.4 |
| `checks-linux-clang-O3-c1-r4.json` | 28, 92: 0%, 0.0% | 1.003 | 1.001, 1.009 | 6.5, 6.5 |
| `checks-linux-gcc-O2-c0-r1.json` | 6, 70: 0%, 0.2% | 1.006 | 1.001, 1.005 | 5.7, 5.8 |
| `checks-linux-gcc-O2-c0-r2.json` | 5, 69: 0%, 0.0% | 1.004 | 1.001, 1.015 | 6.1, 6.3 |
| `checks-linux-gcc-O2-c0-r3.json` | 4, 68: 0%, 0.2% | 1.004 | 1.001, 1.003 | 6.2, 6.4 |
| `checks-linux-gcc-O2-c0-r4.json` | 4, 68: 0%, 0.0% | 1.004 | 1.000, 1.002 | 6.4, 6.5 |
| `checks-linux-gcc-O2-c1-r1.json` | 6, 70: 0%, 0.2% | 1.005 | 1.001, 1.005 | 5.8, 6.1 |
| `checks-linux-gcc-O2-c1-r2.json` | 5, 69: 0%, 0.2% | 1.004 | 1.003, 1.013 | 6.3, 6.2 |
| `checks-linux-gcc-O2-c1-r3.json` | 4, 68: 0%, 0.0% | 1.004 | 1.001, 1.008 | 6.4, 6.4 |
| `checks-linux-gcc-O2-c1-r4.json` | 4, 68: 0%, 0.2% | 1.004 | 1.000, 1.004 | 6.5, 6.5 |
| `checks-linux-gcc-O3-c0-r1.json` | 12, 76: 0%, 0.0% | 1.007 | 1.001, 1.006 | 5.7, 5.8 |
| `checks-linux-gcc-O3-c0-r2.json` | 15, 79: 0%, 0.2% | 1.004 | 1.001, 1.006 | 6.1, 6.3 |
| `checks-linux-gcc-O3-c0-r3.json` | 12, 76: 0%, 0.0% | 1.004 | 1.001, 1.004 | 6.2, 6.4 |
| `checks-linux-gcc-O3-c0-r4.json` | 12, 76: 0%, 0.0% | 1.004 | 1.001, 1.005 | 6.4, 6.5 |
| `checks-linux-gcc-O3-c1-r1.json` | 12, 76: 1%, 1.0% | 1.004 | 1.001, 1.027 | 5.8, 6.1 |
| `checks-linux-gcc-O3-c1-r2.json` | 15, 79: 0%, 0.0% | 1.004 | 1.000, 1.006 | 6.3, 6.2 |
| `checks-linux-gcc-O3-c1-r3.json` | 12, 76: 0%, 0.2% | 1.003 | 1.001, 1.009 | 6.4, 6.4 |
| `checks-linux-gcc-O3-c1-r4.json` | 12, 76: 0%, 0.0% | 1.003 | 1.000, 1.014 | 6.5, 6.5 |
| `checks-mac-appleclang-O2-c0-r1.json` | not pinned | 1.003 | 1.000, 1.005 | 3.3, 3.2 |
| `checks-mac-appleclang-O2-c0-r2.json` | not pinned | 1.003 | 1.000, 1.006 | 3.2, 3.1 |
| `checks-mac-appleclang-O2-c0-r3.json` | not pinned | 1.003 | 1.000, 1.011 | 4.3, 4.1 |
| `checks-mac-appleclang-O2-c1-r1.json` | not pinned | 1.010 | 1.000, 1.011 | 3.2, 3.2 |
| `checks-mac-appleclang-O2-c1-r2.json` | not pinned | 1.002 | 1.000, 1.004 | 3.1, 4.3 |
| `checks-mac-appleclang-O2-c1-r3.json` | not pinned | 1.003 | 1.000, 1.004 | 4.1, 4.0 |
| `checks-mac-appleclang-O3-c0-r1.json` | not pinned | 1.003 | 1.000, 1.006 | 2.9, 2.7 |
| `checks-mac-appleclang-O3-c0-r2.json` | not pinned | 1.002 | 1.000, 1.009 | 2.7, 2.8 |
| `checks-mac-appleclang-O3-c0-r3.json` | not pinned | 1.002 | 1.000, 1.012 | 4.2, 4.5 |
| `checks-mac-appleclang-O3-c1-r1.json` | not pinned | 1.002 | 1.000, 1.032 | 2.7, 2.7 |
| `checks-mac-appleclang-O3-c1-r2.json` | not pinned | 1.002 | 1.000, 1.002 | 2.8, 4.2 |
| `checks-mac-appleclang-O3-c1-r3.json` | not pinned | 1.003 | 1.000, 1.022 | 4.5, 4.2 |
| `checks-mac-gcc16-O2-c0-r1.json` | not pinned | 1.003 | 1.000, 1.006 | 2.5, 2.4 |
| `checks-mac-gcc16-O2-c0-r2.json` | not pinned | 1.003 | 1.000, 1.023 | 2.2, 2.1 |
| `checks-mac-gcc16-O2-c0-r3.json` | not pinned | 1.003 | 1.000, 1.004 | 2.0, 1.9 |
| `checks-mac-gcc16-O2-c1-r1.json` | not pinned | 1.002 | 1.000, 1.022 | 2.4, 2.2 |
| `checks-mac-gcc16-O2-c1-r2.json` | not pinned | 1.002 | 1.000, 1.012 | 2.1, 2.0 |
| `checks-mac-gcc16-O2-c1-r3.json` | not pinned | 1.003 | 1.000, 1.001 | 1.9, 1.8 |
| `checks-mac-gcc16-O3-c0-r1.json` | not pinned | 1.002 | 1.000, 1.002 | 2.9, 2.7 |
| `checks-mac-gcc16-O3-c0-r2.json` | not pinned | 1.002 | 1.000, 1.007 | 2.6, 2.6 |
| `checks-mac-gcc16-O3-c0-r3.json` | not pinned | 1.003 | 1.000, 1.003 | 3.0, 2.8 |
| `checks-mac-gcc16-O3-c1-r1.json` | not pinned | 1.001 | 1.000, 1.032 | 2.7, 2.6 |
| `checks-mac-gcc16-O3-c1-r2.json` | not pinned | 1.003 | 1.000, 1.018 | 2.6, 3.0 |
| `checks-mac-gcc16-O3-c1-r3.json` | not pinned | 1.003 | 1.000, 1.003 | 2.8, 2.8 |

<!-- END up_report runs -->
