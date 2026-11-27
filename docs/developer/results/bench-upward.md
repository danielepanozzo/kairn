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
commit `4710839b`, the tree of the feature with the harness. The harness and the commands are in
[`bench/`](https://github.com/danielepanozzo/kairn/tree/main/bench) (its README, "The round-up
interval"); the measurements, one JSON file per run, in
[`results/upward/bench/`](https://github.com/danielepanozzo/kairn/tree/main/results/upward/bench).

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

- **In loops the type is 3.6 to 9.2 times faster than the default `Interval<double, 1>`.** A sum
  takes 0.39 to 1.22 ns against 1.8 to 4.5 ns, 3.6 to 6.0 times faster with one scope around each loop
  of 256 operations and 4.3 to 8.9 times with one scope around 16 such loops; a product 1.3 to 2.4 ns
  against 6.4 to 17 ns, 4.7 to 8.4 and 5.1 to 9.2 times. With MSVC (unpinned) 13 to 15 times, the
  default type being slow there (7.0 ns a sum, 21 a product)
  ([question 1](#1-the-type-against-the-default-interval)).
- **In dependent computations, 2.1 to 22 times.** A chain of sums 5.1 to 7.2 times faster (0.76 to
  1.03 ns a step), a chain of products 2.1 to 5.9 times (3.2 to 5.2 ns a step); Horner of degree 8 6.3
  to 9.2 times on independent arguments and 2.4 to 6.2 times on dependent ones; the 3 by 3 determinant
  of coordinate differences (the sign filter of an orientation test) 7.8 to 22 times, 13 to 23 ns
  against 102 to 491 ns, where `Ball<double, 1>` takes 1.5 to 2.6 times the type and
  `Interval<double, 2>` 36 to 59 times.
- **It runs at the speed of the classical interval under a mode set once around the loop**, with
  every special case that the classical code (two plain numbers) does not handle: 0.40 to 1.09 of its
  time for sums, 0.58 to 1.59 for products (slower, 1.1 to 1.6 times, where GCC vectorizes the
  classical loop), 0.92 to 1.01 for a long chain of sums, 0.63 to 0.94 for the determinant.
- **Converting from and to the default layout in the loop makes a loop 1.7 to 4.9 times slower**:
  0.66 to 0.82 ns more per sum (two conversions in, one out) and 0.87 to 1.25 per product on the M3,
  2.1 to 2.3 and 3.2 to 4.0 ns on Zen 2; a conversion alone takes 0.34 to 0.52 ns per interval on the
  M3 and 0.63 to 1.24 on Zen 2; in a chain, off the critical path, 0.09 to 0.54 ns per step
  ([question 2](#2-what-a-conversion-costs)).
- **The functions on arrays are 3.6 to 6.4 times faster than Kairn's packed interval kernels**: per
  interval 0.26 to 0.33 ns for a sum of `double` and 0.15 to 0.22 of `float`, 0.87 to 1.38 ns and 0.46
  to 0.75 for a product; and 0.15 to 0.23 of the time of the packed classical interval on Zen 2 for
  sums, 0.46 to 0.74 for products (on the M3 0.57 to 0.64 and 1.58 to 1.86)
  ([question 3](#3-the-functions-on-arrays)).
- **A scope that changes the mode costs 23 to 25 ns on the M3, 50 to 51 ns on Zen 2 and 9.4 ns with
  MSVC**; the register-only scope of the functions on arrays 23 to 26, 19 and 9.2 ns: on Zen 2 the
  scope of the program also sets glibc's mode, 2.6 times the cost of the register's write. A scope
  inside another (nothing changes) costs nothing measurable on the M3 with Apple clang, 0.5 ns with
  GCC 16, 12 ns on Zen 2 (5.4 to 5.8 the register-only one) and 2.8 ns (1.7) with MSVC; a
  `NearestScope` inside an upward region 24 to 30, 50 to 51 and 6.9 ns
  ([question 5](#5-the-scopes)).
- **A function on arrays pays its scope on every call from code that rounds to nearest**: 23 to 28
  ns on the M3 and 15 to 19 ns on Zen 2 on 4 elements, 61 to 93% of the call. The scope is under 10%
  of a call from 256 elements on Zen 2 (sums 4 to 10%, products 4 to 7%), and on the M3 from 256 for
  products (8 to 11%, at the limit) and from 1024 for sums (1 to 10%). Inside an outer `Scope` its scope
  costs nothing measurable on the M3 and 3 to 6 ns a call on Zen 2 on 4 elements
  ([question 4](#4-the-scope-of-a-function-on-arrays-by-length)).
- **`float` costs what `double` costs with the type** (0.72 to 1.15 of its time: one register holds
  either) **and half on arrays** (0.48 to 0.68: twice the lanes) ([question 6](#6-float)).
- **The checked build** (`KAIRN_CHECKS` 1) makes the type's loops of sums 3.8 to 20 times slower and
  of products 1.9 to 5.5 times, its chains of sums 2.4 to 10 times and of products 1.0 to 2.7, the
  functions on arrays 2.3 to 35 times: each operation reads the control register and tests its
  operands, which costs more than a sum; the default type's own checks cost its sums 1.6 to 3.6 times
  ([question 7](#7-the-checked-build)).

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
| `upw/tp/interval_add_1/native` | 0.510 to 0.531 | 0.393 to 0.394 (-O2), 0.386 to 0.426 (-O3) | 0.818 to 0.822 (-O2), 0.593 (-O3) | 1.12 to 1.22 (-O2), 1.22 (-O3) |
| `upw/tp/interval_add_1/native_x16` | 0.429 to 0.445 | 0.307 to 0.314 (-O2), 0.308 to 0.340 (-O3) | 0.637 to 0.640 (-O2), 0.399 to 0.426 (-O3) | 0.929 to 0.939 |
| `upw/tp/interval_add_1/conv` | 1.28 to 1.33 (-O2), 1.30 to 1.35 (-O3) | 1.13 (-O2), 1.04 to 1.15 (-O3) | 2.90 to 2.92 | 3.28 to 3.29 |
| `m2/tp/interval_add_1/op` | 1.87 to 1.95 | 1.79 to 1.81 (-O2), 1.78 to 1.90 (-O3) | 3.52 to 3.54 | 4.51 to 4.53 |
| `m2/tp/interval_add_1/fenv_loop` | 0.500 to 0.515 | 0.652 to 0.653 (-O2), 0.508 to 0.546 (-O3) | 1.46 to 1.47 | 1.62 to 1.64 |
| `m2/tp/interval_add_1/fenv_loop_x16` | 0.409 to 0.422 | 0.562 to 0.563 (-O2), 0.420 to 0.464 (-O3) | 0.810 to 0.821 | 0.961 to 0.969 |
| `upw/tp/interval_sub_1/native` | 0.514 to 0.529 | 0.394 to 0.395 (-O2), 0.386 to 0.427 (-O3) | 0.674 to 0.676 (-O2), 0.817 to 0.940 (-O3) | 1.13 to 1.23 (-O2), 1.11 to 1.12 (-O3) |
| `upw/tp/interval_sub_1/native_x16` | 0.432 to 0.447 | 0.314 to 0.315 (-O2), 0.309 to 0.340 (-O3) | 0.489 to 0.491 (-O2), 0.637 to 0.664 (-O3) | 0.931 to 0.941 |
| `upw/tp/interval_sub_1/conv` | 1.34 to 1.40 | 1.19 (-O2), 1.11 to 1.22 (-O3) | 3.04 to 3.06 (-O2), 3.04 to 3.22 (-O3) | 3.36 to 3.67 (-O2), 3.35 to 3.48 (-O3) |
| `m2/tp/interval_sub_1/op` | 1.88 to 1.95 | 1.87 to 1.88 (-O2), 1.84 to 1.98 (-O3) | 3.65 to 3.66 | 4.52 to 4.53 |
| `m2/tp/interval_sub_1/fenv_loop` | 0.479 to 0.490 | 0.653 to 0.654 (-O2), 0.509 to 0.547 (-O3) | 1.45 to 1.46 | 1.62 to 1.64 |
| `m2/tp/interval_sub_1/fenv_loop_x16` | 0.393 to 0.404 | 0.562 to 0.563 (-O2), 0.419 to 0.464 (-O3) | 0.806 to 0.808 | 0.967 to 0.970 |
| `upw/tp/interval_mul_1/native` | 1.34 to 1.39 | 1.33 (-O2), 1.31 to 1.44 (-O3) | 1.98 to 1.99 (-O2), 1.98 to 2.10 (-O3) | 2.34 to 2.35 (-O2), 2.02 to 2.15 (-O3) |
| `upw/tp/interval_mul_1/native_x16` | 1.23 to 1.28 | 1.23 to 1.24 (-O2), 1.21 to 1.34 (-O3) | 1.79 to 1.80 | 1.84 to 1.86 |
| `upw/tp/interval_mul_1/conv` | 2.54 to 2.61 | 2.37 (-O2), 2.19 to 2.42 (-O3) | 5.64 to 5.78 (-O2), 6.00 (-O3) | 5.52 to 5.71 |
| `m2/tp/interval_mul_1/op` | 6.35 to 6.55 | 8.12 to 8.13 (-O2), 8.00 to 8.85 (-O3) | 9.86 to 9.89 | 16.9 to 17.0 |
| `m2/tp/interval_mul_1/fenv_loop` | 1.47 to 1.50 | 1.10 (-O2), 1.07 to 1.16 (-O3) | 1.78 to 1.79 | 3.49 to 3.65 |
| `m2/tp/interval_mul_1/fenv_loop_x16` | 1.61 to 1.68 | 1.00 (-O2), 0.981 to 1.08 (-O3) | 1.13 to 1.14 | 2.97 to 3.11 |
| `m2/tp/pair_add_1/plain` | 0.290 to 0.302 | 0.301 to 0.302 (-O2), 0.295 to 0.327 (-O3) | 0.323 to 0.324 | 0.615 to 0.617 |
| `m2/tp/plain4_mul_1/plain` | 0.760 to 0.788 | 0.931 to 0.959 (-O2), 1.07 to 1.19 (-O3) | 1.01 to 1.02 | 1.12 to 1.13 |

| Loops, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`: Interval<T, 1> over the type, one scope per loop | 3.73 to 3.77 (-O2), 3.57 to 3.72 (-O3) | 4.56 to 4.60 (-O2), 4.47 to 4.61 (-O3) | 4.30 to 4.31 (-O2), 5.95 to 5.97 (-O3) | 3.70 to 4.05 (-O2), 3.70 to 3.71 (-O3) |
| `X + Y`: Interval<T, 1> over the type, 16 loops per scope | 4.44 to 4.45 (-O2), 4.25 to 4.44 (-O3) | 5.75 to 5.84 (-O2), 5.59 to 5.78 (-O3) | 5.52 to 5.55 (-O2), 8.30 to 8.87 (-O3) | 4.81 to 4.86 |
| `X - Y`: Interval<T, 1> over the type, one scope per loop | 3.70 to 3.72 (-O2), 3.55 to 3.70 (-O3) | 4.75 to 4.76 (-O2), 4.64 to 4.81 (-O3) | 5.40 to 5.42 (-O2), 3.89 to 4.48 (-O3) | 3.67 to 4.01 (-O2), 4.04 to 4.05 (-O3) |
| `X - Y`: Interval<T, 1> over the type, 16 loops per scope | 4.42 (-O2), 4.20 to 4.42 (-O3) | 5.83 to 5.98 | 7.45 to 7.47 (-O2), 5.51 to 5.74 (-O3) | 4.80 to 4.85 |
| `X * Y`: Interval<T, 1> over the type, one scope per loop | 4.73 to 4.77 | 6.09 to 6.13 | 4.97 to 4.99 (-O2), 4.69 to 4.98 (-O3) | 7.18 to 7.21 (-O2), 7.87 to 8.36 (-O3) |
| `X * Y`: Interval<T, 1> over the type, 16 loops per scope | 5.12 to 5.24 | 6.57 to 6.61 | 5.49 to 5.51 | 9.05 to 9.17 |
| `X + Y`: the type over fenv_loop | 1.00 to 1.02 (-O2), 1.02 to 1.06 (-O3) | 0.60 (-O2), 0.76 to 0.78 (-O3) | 0.56 (-O2), 0.40 (-O3) | 0.69 to 0.75 (-O2), 0.75 (-O3) |
| `X + Y`: the type over fenv_loop, 16 loops per change of mode | 1.04 to 1.09 | 0.55 to 0.56 (-O2), 0.73 (-O3) | 0.78 (-O2), 0.49 to 0.52 (-O3) | 0.96 to 0.98 |
| `X - Y`: the type over fenv_loop | 1.07 to 1.10 | 0.60 (-O2), 0.76 to 0.78 (-O3) | 0.46 (-O2), 0.56 to 0.64 (-O3) | 0.69 to 0.76 (-O2), 0.68 to 0.69 (-O3) |
| `X - Y`: the type over fenv_loop, 16 loops per change of mode | 1.07 to 1.12 | 0.56 (-O2), 0.73 to 0.74 (-O3) | 0.61 (-O2), 0.79 to 0.82 (-O3) | 0.96 to 0.97 |
| `X * Y`: the type over fenv_loop | 0.91 to 0.94 | 1.21 to 1.25 | 1.11 (-O2), 1.11 to 1.18 (-O3) | 0.66 to 0.67 (-O2), 0.58 to 0.59 (-O3) |
| `X * Y`: the type over fenv_loop, 16 loops per change of mode | 0.74 to 0.75 (-O2), 0.75 to 0.79 (-O3) | 1.23 to 1.24 | 1.58 to 1.59 | 0.59 to 0.63 |
| `X + Y`: the type, 16 loops per scope, over the plain floor | 1.44 to 1.49 (-O2), 1.43 to 1.54 (-O3) | 1.02 to 1.04 (-O2), 1.04 to 1.08 (-O3) | 1.97 (-O2), 1.23 to 1.32 (-O3) | 1.51 to 1.53 |
| `X * Y`: the type, 16 loops per scope, over the plain floor | 1.59 to 1.63 | 1.29 to 1.33 (-O2), 1.13 to 1.18 (-O3) | 1.76 to 1.77 | 1.63 to 1.66 |
| `X + Y`: converted in the loop over native | 2.51 to 2.57 | 2.86 to 2.87 (-O2), 2.70 (-O3) | 3.54 to 3.55 (-O2), 4.91 (-O3) | 2.69 to 2.94 (-O2), 2.69 to 2.70 (-O3) |
| `X - Y`: converted in the loop over native | 2.61 to 2.65 | 3.03 (-O2), 2.87 to 2.89 (-O3) | 4.50 to 4.54 (-O2), 3.24 to 3.94 (-O3) | 2.73 to 3.25 (-O2), 3.00 to 3.12 (-O3) |
| `X * Y`: converted in the loop over native | 1.88 to 1.92 | 1.78 (-O2), 1.66 to 1.68 (-O3) | 2.84 to 2.91 (-O2), 2.85 to 3.03 (-O3) | 2.35 to 2.44 (-O2), 2.58 to 2.74 (-O3) |

<!-- END up_report type -->

<!-- BEGIN up_report chains -->

| Chains, times (ns per step) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/sum/interval_add_1/native` | 0.776 to 0.800 | 0.774 to 0.775 (-O2), 0.763 to 0.820 (-O3) | 1.01 to 1.02 | 1.01 to 1.03 |
| `upw/sum/interval_add_1/native_x16` | 0.699 to 0.714 (-O2), 0.720 to 0.744 (-O3) | 0.723 to 0.729 (-O2), 0.711 to 0.756 (-O3) | 0.907 to 0.910 | 0.906 to 0.912 |
| `upw/sum/interval_add_1/conv` | 0.870 to 0.900 | 0.896 to 0.898 (-O2), 0.860 to 0.916 (-O3) | 1.36 | 1.55 to 1.56 |
| `m2/sum/interval_add_1/op` | 5.49 to 5.72 | 3.93 to 3.94 (-O2), 3.92 to 4.16 (-O3) | 5.63 to 5.66 | 6.59 to 6.67 |
| `m2/sum/interval_add_1/fenv_loop` | 0.832 to 0.864 | 0.819 to 0.820 (-O2), 0.805 to 0.885 (-O3) | 1.59 | 1.55 to 1.57 |
| `m2/sum/interval_add_1/fenv_loop_x16` | 0.742 to 0.774 | 0.757 to 0.758 (-O2), 0.744 to 0.821 (-O3) | 0.942 to 0.946 | 0.900 to 0.907 |
| `upw/prod/interval_mul_1/native` | 4.87 to 5.08 | 4.96 to 4.97 (-O2), 4.87 to 5.24 (-O3) | 3.17 to 3.33 | 3.43 |
| `upw/prod/interval_mul_1/native_x16` | 4.86 to 4.97 | 4.86 to 4.88 (-O2), 4.77 to 5.13 (-O3) | 3.02 to 3.05 | 3.42 to 3.47 |
| `upw/prod/interval_mul_1/conv` | 4.89 to 5.09 | 4.97 to 4.98 (-O2), 4.87 to 5.37 (-O3) | 3.90 to 4.10 (-O2), 3.89 to 3.90 (-O3) | 3.67 to 4.11 (-O2), 3.66 to 3.68 (-O3) |
| `m2/prod/interval_mul_1/op` | 10.9 to 11.1 (-O2), 11.4 to 11.5 (-O3) | 10.3 (-O2), 10.1 to 10.9 (-O3) | 18.5 to 18.7 | 18.2 to 18.3 |
| `m2/prod/interval_mul_1/fenv_loop` | 3.36 to 3.51 | 3.58 to 3.59 (-O2), 3.80 to 4.20 (-O3) | 3.06 to 3.70 (-O2), 3.69 to 3.70 (-O3) | 3.13 to 3.15 |
| `m2/prod/interval_mul_1/fenv_loop_x16` | 3.33 to 3.47 | 3.50 to 3.52 (-O2), 3.71 to 4.10 (-O3) | 3.05 to 3.08 | 2.47 to 2.48 |

| Chains, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `S + X`: Interval<T, 1> over the type | 7.17 to 7.20 (-O2), 6.86 to 7.21 (-O3) | 5.07 to 5.14 | 5.56 to 5.57 | 6.46 to 6.55 |
| `S + X`: Interval<T, 1> over the type, a chain 16 times as long per scope | 8.01 to 8.02 (-O2), 7.37 to 7.77 (-O3) | 5.39 to 5.51 | 6.20 to 6.21 | 7.23 to 7.34 |
| `P * X`: Interval<T, 1> over the type | 2.18 to 2.19 (-O2), 2.30 to 2.35 (-O3) | 2.07 to 2.08 | 5.75 to 5.85 (-O2), 5.59 to 5.75 (-O3) | 5.31 to 5.34 |
| `P * X`: Interval<T, 1> over the type, a chain 16 times as long per scope | 2.23 to 2.24 (-O2), 2.32 to 2.36 (-O3) | 2.11 to 2.15 | 6.09 to 6.15 | 5.27 to 5.33 |
| `S + X`: the type over fenv_loop | 0.93 to 0.96 | 0.92 to 0.95 | 0.64 | 0.65 to 0.66 |
| `S + X`: the type over fenv_loop, both 16 times as long | 0.93 to 0.97 | 0.92 to 0.96 | 0.96 to 0.97 | 1.00 to 1.01 |
| `P * X`: the type over fenv_loop | 1.45 (-O2), 1.41 to 1.48 (-O3) | 1.38 to 1.39 (-O2), 1.24 to 1.28 (-O3) | 0.87 to 1.05 (-O2), 0.88 to 0.90 (-O3) | 1.09 to 1.10 |
| `P * X`: the type over fenv_loop, both 16 times as long | 1.42 to 1.46 | 1.39 (-O2), 1.22 to 1.29 (-O3) | 0.98 to 0.99 | 1.38 to 1.40 |
| `S + X`: converted over native | 1.11 to 1.12 | 1.12 to 1.16 | 1.34 to 1.35 | 1.51 to 1.54 |
| `P * X`: converted over native | 0.98 to 1.01 | 1.00 to 1.04 | 1.21 to 1.29 (-O2), 1.17 to 1.20 (-O3) | 1.07 to 1.20 (-O2), 1.07 (-O3) |

<!-- END up_report chains -->

<!-- BEGIN up_report poly -->

| Horner and the determinant, times (ns per evaluation) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/tp/horner_i1/native` | 15.8 to 16.4 | 17.0 to 17.1 (-O2), 16.7 to 18.0 (-O3) | 27.1 to 27.4 | 26.2 to 27.0 |
| `upw/tp/horner_i1/conv` | 18.9 to 19.3 (-O2), 19.5 to 20.0 (-O3) | 17.2 to 17.3 (-O2), 16.8 to 18.1 (-O3) | 32.8 to 33.5 | 30.5 to 31.3 |
| `m2/tp/horner_i1/op` | 126 to 130 | 108 to 110 (-O2), 110 to 117 (-O3) | 246 to 249 | 179 to 180 |
| `m2/tp/horner_i1/fenv_loop` | 15.9 to 16.3 (-O2), 12.8 to 12.9 (-O3) | 18.5 (-O2), 16.0 to 17.3 (-O3) | 44.9 to 45.6 | 30.7 to 31.6 (-O2), 26.2 to 26.3 (-O3) |
| `upw/lat/horner_i1/native` | 52.4 to 54.3 | 49.6 (-O2), 48.5 to 53.6 (-O3) | 43.8 to 44.0 (-O2), 40.4 to 40.5 (-O3) | 39.5 to 39.6 |
| `upw/lat/horner_i1/conv` | 51.8 to 54.3 | 49.0 to 49.8 (-O2), 48.8 to 53.8 (-O3) | 41.7 to 41.9 | 39.4 to 39.6 |
| `m2/lat/horner_i1/op` | 134 to 139 (-O2), 136 to 141 (-O3) | 123 (-O2), 118 to 126 (-O3) | 243 to 249 | 187 to 188 |
| `m2/lat/horner_i1/fenv_loop` | 36.5 to 37.2 (-O2), 31.0 to 31.8 (-O3) | 35.4 to 36.3 (-O2), 33.8 to 36.4 (-O3) | 33.9 to 34.0 | 30.9 to 31.3 (-O2), 28.6 to 28.7 (-O3) |
| `upw/tp/det3_i1/native` | 13.3 to 13.8 | 12.8 to 13.3 (-O2), 13.0 to 14.4 (-O3) | 22.3 to 22.5 | 23.4 |
| `upw/tp/det3_i1/conv` | 18.0 to 18.8 | 17.8 (-O2), 17.3 to 18.5 (-O3) | 33.3 to 33.4 | 36.5 to 37.1 |
| `m2/tp/det3_i1/op` | 111 to 116 | 103 to 104 (-O2), 102 to 112 (-O3) | 486 to 491 | 223 to 225 |
| `m2/tp/det3_i1/fenv_loop` | 14.4 to 14.7 | 16.0 (-O2), 16.4 to 18.1 (-O3) | 25.7 to 26.3 | 35.7 to 37.2 |
| `m2/tp/det3_i2/op` | 488 to 508 | 514 to 516 (-O2), 505 to 549 (-O3) | 1292 to 1309 | 992 to 996 |
| `m2/tp/det3_b1/op` | 19.5 to 20.2 | 20.3 (-O2), 19.7 to 21.3 (-O3) | 58.4 to 58.7 | 49.3 to 49.4 |
| `m2/tp/det3_b2/op` | 55.2 to 56.4 | 51.2 to 51.4 (-O2), 51.3 to 55.2 (-O3) | 149 | 140 |
| `m2/tp/det3_t/plain` | 1.61 to 1.68 | 1.58 to 1.59 (-O2), 1.57 to 1.69 (-O3) | 3.25 to 3.26 | 3.63 to 3.65 |

| Horner and the determinant, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| Horner, independent: Interval<T, 1> over the type | 7.93 to 7.98 | 6.32 to 6.49 (-O2), 6.48 to 6.57 (-O3) | 8.95 to 9.19 | 6.61 to 6.80 (-O2), 6.77 to 6.85 (-O3) |
| Horner, dependent: Interval<T, 1> over the type | 2.56 (-O2), 2.56 to 2.69 (-O3) | 2.48 (-O2), 2.35 to 2.44 (-O3) | 5.52 to 5.60 (-O2), 6.07 to 6.15 (-O3) | 4.72 to 4.74 |
| Horner, independent: the type over fenv_loop | 0.99 (-O2), 1.23 to 1.28 (-O3) | 0.92 (-O2), 1.04 to 1.08 (-O3) | 0.60 to 0.61 | 0.83 to 0.86 (-O2), 1.00 to 1.01 (-O3) |
| Horner, dependent: the type over fenv_loop | 1.44 to 1.46 (-O2), 1.65 to 1.71 (-O3) | 1.37 to 1.40 (-O2), 1.43 to 1.48 (-O3) | 1.29 (-O2), 1.19 (-O3) | 1.26 to 1.28 (-O2), 1.38 (-O3) |
| Horner, independent: converted over native | 1.19 to 1.23 | 1.00 to 1.01 | 1.21 to 1.22 | 1.15 to 1.18 |
| det3: Interval<T, 1> over the type | 8.20 to 8.32 (-O2), 8.28 to 8.60 (-O3) | 7.78 to 8.05 (-O2), 7.83 to 8.20 (-O3) | 21.8 to 21.9 | 9.54 to 9.59 |
| det3: the type over fenv_loop | 0.93 to 0.94 | 0.80 to 0.83 (-O2), 0.76 to 0.79 (-O3) | 0.85 to 0.87 | 0.63 to 0.66 |
| det3: converted over native | 1.35 to 1.37 | 1.34 to 1.39 (-O2), 1.29 to 1.38 (-O3) | 1.48 to 1.50 | 1.56 to 1.58 |
| det3: Ball<T, 1> over the type | 1.45 to 1.47 (-O2), 1.45 to 1.51 (-O3) | 1.53 to 1.58 (-O2), 1.48 to 1.54 (-O3) | 2.61 to 2.63 | 2.10 to 2.11 |
| det3: Interval<T, 2> over the type | 36.4 to 37.0 | 38.9 to 40.1 (-O2), 38.2 to 41.0 (-O3) | 58.0 to 58.6 | 42.4 to 42.5 |
| det3: Ball<T, 2> over the type | 4.09 to 4.13 | 3.88 to 3.99 (-O2), 3.85 to 4.13 (-O3) | 6.63 to 6.69 | 5.99 to 6.00 |
| det3: the type over plain double | 8.13 to 8.32 | 8.11 to 8.36 (-O2), 8.18 to 8.51 (-O3) | 6.84 to 6.90 | 6.43 to 6.45 |

<!-- END up_report poly -->

- **Loops.** A sum of the type is one vector addition of two lanes, a product four products of two
  lanes and three maxima; the default type's sum is two directed sums of about fifteen operations each,
  its product eight directed products. So the type's sum is 3.6 to 6.0 times faster in a loop of 256
  with its scope, and 4.3 to 8.9 times with 16 loops per scope; its product 4.7 to 8.4 and 5.1 to 9.2
  times. With 16 loops per scope a sum costs 1.02 to 1.97 times the two plain additions, a product 1.13
  to 1.77 times the four plain products with their least and greatest.
- **The scope's share of a loop.** A loop of 256 operations under one scope pays the scope once: on
  Zen 2 about 50 ns ([question 5](#5-the-scopes)), 0.2 ns per operation, which is why `native` takes
  1.2 to 1.5 times `native_x16` there for the sums; 16 loops per scope bring it to a sixteenth. The
  loops with one scope per 256 operations also vary more from run to run on Zen 2 (the sum of Clang 18
  at `-O2`, 1.12 to 1.22 ns over the four runs) than the 16-pass loops (0.93 to 0.94 ns); in the
  campaign set aside ([What was set aside](#what-was-set-aside)), the same sum of Clang 18 at `-O3`
  took 1.22 to 1.79 ns over four runs, and its 16-pass loop 0.93 to 0.94 ns. Short work between two
  changes of mode is what varies: the widest ranges of these runs are calls of one operation in a
  `NearestScope` (Clang 18 at `-O2`, 56 to 129 ns, one run of four) and calls of `kairn::upward::add` on
  64 elements from code that rounds to nearest (GCC 13 at `-O3`, 28 to 65 ns, one run of four).
- **Against the classical interval** under a mode set once: the type's sums take 0.40 to 1.09 of its
  time (the classical loop negates both operands of the lower bound and its result, the type stores
  it negated), its
  products 0.58 to 1.59: slower where GCC vectorizes the classical loop's four products (1.11 to 1.59
  with GCC 13 and GCC 16), faster where Clang does not under `FENV_ACCESS` (0.58 to 0.94). The classical
  code here handles no special case (no empty set, no unbounded interval, no $0 \cdot \infty$); the
  type handles all of them.
- **Chains.** A chain of sums waits for one vector addition per step: 0.70 to 1.03 ns, 5.1 to 8.0 times
  faster than the default chain, and the same time as the classical chain under one mode (0.92 to 1.01
  when both run 16 times as long). A chain of products waits for four products and three maxima: 3.0 to
  5.2 ns, 2.1 to 6.2 times faster than the default; on the M3 the default product chain is relatively
  fast (10 to 11 ns), so the gain there is 2.1 to 2.4 times. Against the classical chain of products
  under one mode, 0.87 to 1.48.
- **Horner and the determinant.** Horner of degree 8 (eight products and eight sums of intervals) is
  6.3 to 9.2 times faster than the default on independent arguments and 2.4 to 6.2 times when each
  evaluation waits for the one before. The determinant of coordinate differences (9 differences, 9
  products, 5 sums or differences) takes 13 to 14 ns on the M3 and 22 to 23 ns on Zen 2, 7.8 to 9.6
  times faster than the default type, and 22 times with GCC 13, whose default determinant takes 490
  ns: its loop has no call, and is 1.6 times as long as Clang 18's with 1.4 times as many accesses to
  the stack (spilled registers; not investigated further). `Ball<double, 1>` takes 1.5 to 2.6 times the
  type, `Ball<double, 2>` 3.9 to 6.7 times, `Interval<double, 2>` 36 to 59 times; plain `double`, which
  encloses nothing, 0.12 to 0.16 of the type's time.

### 2. What a conversion costs

A program that keeps its intervals in the default layout, (lower, upper) in memory, converts each
operand (`kairn::upward::Interval<T>(x)`, the kernel `upward_from_interval_1`: a negation and a
selection) and each result back (`to_interval()`, `upward_to_interval_1`, with the barriers on its
bounds): the variants `conv` of question 1, against `native`, and the conversions alone, in loops
without a scope (they are exact).

<!-- BEGIN up_report conversions -->

| Conversions alone, times | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upw/tp/from_interval_1/op`, ns per element | 0.498 to 0.517 | 0.352 to 0.358 (-O2), 0.351 to 0.378 (-O3) | 1.09 to 1.10 | 1.13 to 1.14 |
| `upw/tp/to_interval_1/op`, ns per element | 0.427 to 0.442 | 0.364 to 0.366 (-O2), 0.342 to 0.377 (-O3) | 0.630 to 0.638 | 1.23 to 1.24 |

| What the conversions cost (ns per operation) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`, converted minus native (two conversions in, one out) | 0.769 to 0.816 | 0.655 to 0.735 | 2.08 to 2.32 | 2.06 to 2.17 |
| `X * Y`, converted minus native | 1.20 to 1.25 | 0.874 to 1.04 | 3.66 to 4.02 | 3.17 to 3.52 |
| `S + X`, converted minus native (one conversion in) | 0.089 to 0.099 | 0.096 to 0.124 | 0.348 to 0.351 | 0.524 to 0.543 |
| det3, converted minus native (12 in, one out) | 4.68 to 5.05 | 4.55 to 4.96 (-O2), 4.18 to 4.91 (-O3) | 10.9 to 11.2 | 13.1 to 13.6 |

| The default type against the type converted in the loop | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`: Interval<T, 1> over the type converted in the loop | 1.47 to 1.49 (-O2), 1.41 to 1.46 (-O3) | 1.59 to 1.60 (-O2), 1.66 to 1.71 (-O3) | 1.21 to 1.22 | 1.37 to 1.38 |
| `X * Y`: Interval<T, 1> over the type converted in the loop | 2.48 to 2.52 | 3.43 (-O2), 3.65 to 3.66 (-O3) | 1.71 to 1.75 (-O2), 1.64 to 1.65 (-O3) | 2.95 to 3.05 (-O2), 3.04 to 3.07 (-O3) |
| `S + X`: Interval<T, 1> over the type converted in the loop | 6.42 to 6.45 (-O2), 6.10 to 6.43 (-O3) | 4.38 to 4.39 (-O2), 4.47 to 4.55 (-O3) | 4.14 to 4.15 | 4.24 to 4.28 |
| det3: Interval<T, 1> over the type converted in the loop | 6.01 to 6.16 (-O2), 6.08 to 6.31 (-O3) | 5.79 to 5.81 (-O2), 5.89 to 6.06 (-O3) | 14.5 to 14.7 | 6.07 to 6.14 |

<!-- END up_report conversions -->

- A loop of sums in the default layout costs 2.5 to 4.9 times the loop on arrays of the type, a loop
  of products 1.7 to 3.0 times: 0.66 to 0.82 ns more per sum and 0.87 to 1.25 per product on the M3,
  2.1 to 2.3 and 3.2 to 4.0 ns on Zen 2, for two conversions in and one out. The converted sum is then
  still 1.4 to 1.7 times faster than the default type's on the M3 and 1.2 to 1.4 times on Zen 2, the
  converted product 2.5 to 3.7 and 1.6 to 3.1 times faster, the converted chain of sums 4.1 to 6.5
  times and the converted determinant 5.8 to 15 times.
- One conversion alone takes 0.35 to 0.52 ns per interval (from the default type) and 0.34 to 0.44
  (back) on the M3, 1.09 to 1.14 and 0.63 to 1.24 ns on Zen 2.
- Where the operation waits for the one before, the conversion of the next operand is off the
  critical path: a chain of sums pays 0.09 to 0.12 ns per step on the M3 and 0.35 to 0.54 on Zen 2, a
  chain of products 0.98 to 1.29 of its time. The determinant, with 12 conversions in and one out for
  23 interval operations, pays 4.2 to 5.1 ns (M3) and 11 to 14 ns (Zen 2), 1.3 to 1.6 times.
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
| `upwa/tp/interval_add_1/op` | 0.303 to 0.311 | 0.305 to 0.306 (-O2), 0.299 to 0.330 (-O3) | 0.258 to 0.261 | 0.259 to 0.260 |
| `upwa/tp/interval_add_1/packed` | 1.53 to 1.60 | 1.49 (-O2), 1.47 to 1.62 (-O3) | 1.59 to 1.60 | 1.22 |
| `upwa/tp/interval_add_1/fenv_loop` | 0.535 to 0.548 (-O2), 0.520 to 0.534 (-O3) | 0.534 to 0.535 (-O2), 0.524 to 0.564 (-O3) | 1.14 to 1.15 | 1.13 to 1.14 |
| `upwa/tp/interval_sub_1/op` | 0.304 to 0.315 | 0.305 (-O2), 0.300 to 0.332 (-O3) | 0.259 to 0.260 | 0.258 to 0.259 |
| `upwa/tp/interval_sub_1/packed` | 1.61 to 1.67 | 1.57 (-O2), 1.55 to 1.71 (-O3) | 1.65 to 1.66 | 1.26 to 1.27 |
| `upwa/tp/interval_sub_1/fenv_loop` | 0.534 to 0.553 | 0.531 to 0.535 (-O2), 0.525 to 0.577 (-O3) | 1.26 to 1.27 | 1.15 to 1.16 |
| `upwa/tp/interval_mul_1/op` | 1.25 to 1.30 | 1.26 to 1.27 (-O2), 1.25 to 1.38 (-O3) | 0.969 to 0.986 | 0.868 to 0.872 |
| `upwa/tp/interval_mul_1/packed` | 5.29 to 5.41 | 5.02 to 5.09 (-O2), 5.40 to 5.99 (-O3) | 4.63 to 4.65 | 4.34 to 4.40 |
| `upwa/tp/interval_mul_1/fenv_loop` | 0.690 to 0.716 | 0.697 to 0.698 (-O2), 0.683 to 0.755 (-O3) | 1.32 to 1.35 | 1.29 to 1.30 |
| `upwaf/tp/interval_add_1/op` | 0.197 to 0.206 | 0.198 to 0.199 (-O2), 0.195 to 0.217 (-O3) | 0.146 to 0.147 | 0.145 to 0.149 (-O2), 0.155 (-O3) |
| `upwaf/tp/interval_add_1/packed` | 0.794 to 0.823 | 0.742 (-O2), 0.727 to 0.804 (-O3) | 0.803 to 0.810 | 0.611 to 0.613 |
| `upwaf/tp/interval_add_1/fenv_loop` | 0.315 to 0.327 | 0.314 to 0.318 (-O2), 0.312 to 0.345 (-O3) | 0.907 to 0.915 | 0.903 to 0.912 |
| `upwaf/tp/interval_sub_1/op` | 0.195 to 0.202 | 0.198 to 0.199 (-O2), 0.198 to 0.213 (-O3) | 0.146 to 0.147 | 0.145 to 0.147 |
| `upwaf/tp/interval_sub_1/packed` | 0.818 to 0.848 | 0.780 to 0.783 (-O2), 0.767 to 0.854 (-O3) | 0.838 to 0.843 | 0.634 to 0.637 |
| `upwaf/tp/interval_sub_1/fenv_loop` | 0.314 to 0.323 | 0.317 to 0.319 (-O2), 0.311 to 0.339 (-O3) | 0.967 to 0.974 | 0.912 to 0.918 |
| `upwaf/tp/interval_mul_1/op` | 0.667 to 0.681 | 0.692 to 0.693 (-O2), 0.678 to 0.750 (-O3) | 0.474 to 0.480 | 0.462 to 0.465 |
| `upwaf/tp/interval_mul_1/packed` | 2.60 to 2.70 | 2.55 (-O2), 2.50 to 2.68 (-O3) | 2.36 to 2.37 | 2.14 to 2.17 |
| `upwaf/tp/interval_mul_1/fenv_loop` | 0.410 to 0.424 | 0.405 to 0.406 (-O2), 0.398 to 0.438 (-O3) | 1.02 to 1.03 | 0.989 to 0.997 |
| `m2p/tp/interval_add_1/kairn` | 1.57 to 1.60 | 1.51 (-O2), 1.47 to 1.58 (-O3) | 1.61 to 1.62 | 1.23 to 1.24 |
| `m2p/tp/interval_add_1/fenv_loop` | 0.520 to 0.531 | 0.516 to 0.517 (-O2), 0.507 to 0.545 (-O3) | 1.03 | 1.03 |
| `m2p/tp/interval_mul_1/kairn` | 5.31 to 5.47 | 5.10 to 5.11 (-O2), 5.45 to 5.87 (-O3) | 4.64 to 4.66 | 4.23 to 4.24 |
| `m2p/tp/interval_mul_1/fenv_loop` | 0.733 to 0.749 | 0.731 to 0.732 (-O2), 0.717 to 0.782 (-O3) | 1.30 | 1.29 to 1.30 |

| Functions on arrays, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| double `+`: the packed kernel over the function | 5.07 to 5.14 | 4.88 to 4.90 (-O2), 4.74 to 4.91 (-O3) | 6.12 to 6.19 | 4.70 to 4.71 |
| double `-`: the packed kernel over the function | 5.21 to 5.30 | 5.14 to 5.16 | 6.36 to 6.38 | 4.90 to 4.91 |
| double `*`: the packed kernel over the function | 4.15 to 4.23 | 3.96 to 4.04 (-O2), 4.33 to 4.48 (-O3) | 4.70 to 4.79 | 4.98 to 5.06 |
| float `+`: the packed kernel over the function | 4.00 to 4.05 | 3.71 to 3.78 | 5.48 to 5.52 | 4.13 to 4.21 (-O2), 3.94 to 3.95 (-O3) |
| float `-`: the packed kernel over the function | 4.17 to 4.20 | 3.93 to 3.94 (-O2), 3.85 to 4.05 (-O3) | 5.72 to 5.77 | 4.33 to 4.36 |
| float `*`: the packed kernel over the function | 3.89 to 3.97 | 3.68 (-O2), 3.58 to 3.73 (-O3) | 4.93 to 4.97 | 4.62 to 4.69 |
| double `+`: the function over fenv_loop | 0.57 to 0.59 | 0.57 to 0.58 | 0.23 | 0.23 |
| double `-`: the function over fenv_loop | 0.57 | 0.57 | 0.21 | 0.22 |
| double `*`: the function over fenv_loop | 1.81 to 1.82 | 1.80 to 1.82 (-O2), 1.82 to 1.86 (-O3) | 0.73 to 0.74 | 0.67 |
| float `+`: the function over fenv_loop | 0.62 to 0.63 | 0.61 to 0.63 | 0.16 | 0.16 to 0.17 |
| float `-`: the function over fenv_loop | 0.62 to 0.64 | 0.62 to 0.64 | 0.15 | 0.16 |
| float `*`: the function over fenv_loop | 1.63 (-O2), 1.58 to 1.63 (-O3) | 1.66 to 1.71 | 0.46 to 0.47 | 0.47 |
| double `+`: m2p (the arrays of m2.cpp) over packed (placed) | 1.00 to 1.04 | 0.98 to 1.01 | 1.00 to 1.01 | 1.01 to 1.02 |
| double `+`: m2p fenv_loop over fenv_loop (placed) | 0.97 to 1.00 | 0.96 to 0.97 | 0.90 to 0.91 | 0.90 to 0.91 |
| double `*`: m2p (the arrays of m2.cpp) over packed (placed) | 1.00 to 1.03 | 1.00 to 1.02 (-O2), 0.96 to 1.01 (-O3) | 1.00 to 1.01 | 0.96 to 0.98 |
| double `*`: m2p fenv_loop over fenv_loop (placed) | 1.04 to 1.08 | 1.05 (-O2), 1.03 to 1.10 (-O3) | 0.97 to 0.99 | 1.00 to 1.01 |
| `+`: the function on arrays over the type, 16 loops per scope | 0.68 to 0.71 | 0.95 to 0.99 | 0.41 (-O2), 0.61 to 0.65 (-O3) | 0.28 |
| `+`: float over double, the function on arrays | 0.65 to 0.68 | 0.64 to 0.66 | 0.56 to 0.57 | 0.56 to 0.60 |
| `+`: float over double, the type | 0.97 to 1.01 | 1.00 (-O2), 0.95 to 1.00 (-O3) | 0.72 to 0.88 (-O2), 1.01 (-O3) | 0.91 to 1.15 (-O2), 0.91 (-O3) |
| `*`: the function on arrays over the type, 16 loops per scope | 1.03 to 1.05 (-O2), 0.98 to 1.03 (-O3) | 1.00 to 1.03 | 0.54 to 0.55 | 0.47 |
| `*`: float over double, the function on arrays | 0.52 to 0.53 | 0.54 to 0.55 | 0.48 to 0.49 | 0.53 |
| `*`: float over double, the type | 0.93 to 0.95 | 1.02 to 1.05 | 1.00 (-O2), 0.94 to 1.00 (-O3) | 0.86 to 0.99 (-O2), 0.94 to 1.00 (-O3) |

<!-- END up_report arrays -->

- **Against Kairn's packed kernels**, the functions on arrays are 4.7 to 6.4 times faster for sums and
  differences of `double` and 4.0 to 5.1 times for products (3.6 to 5.8 for `float`): a sum is one
  vector addition per lane of each array, where the default kernel computes two directed sums with
  their error terms and steps.
- **Against the packed classical interval** under one mode: on Zen 2 the functions take 0.15 to 0.23
  of its time for sums and 0.46 to 0.74 for products (its loops, as their compilers compiled them under
  `-frounding-math`, take 0.9 to 1.35 ns per interval there, about four times the functions' sum); on
  the M3 0.57 to 0.64 for sums, and 1.58 to 1.86 for products: the classical product is eight products
  and six maxima per interval and handles no special case, the type's has the same products and maxima
  and the NaN tests and selections of its special cases.
- **Arrays against the type in one register**: on Zen 2, with four lanes, a function on arrays takes
  0.28 to 0.65 of the type's 16-pass loop for sums and 0.47 to 0.55 for products; on the M3, two lanes
  as wide as the type's register, 0.68 to 0.99 and 0.98 to 1.05. `float` on arrays takes 0.48 to 0.68
  of `double`'s time (twice the lanes).
- **The placement of the arrays.** The kernels on the arrays of Milestone 2, whose loads fall 32 bytes
  modulo 4 KB from the previous iteration's stores, take 0.96 to 1.04 times the same kernels on the
  placed arrays, and its classical loops 0.90 to 1.10 times: the aliasing changes nothing beyond the
  noise here (it is avoided in the new loops all the same).

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
| `add_4/nearest` | 24.6 to 25.4 | 24.4 to 24.8 (-O2), 24.8 to 27.3 (-O3) | 21.6 to 21.7 | 21.6 to 21.7 |
| `add_4/nested` | 1.66 to 1.72 | 1.76 to 1.77 (-O2), 1.61 to 1.77 (-O3) | 8.04 to 8.08 | 8.05 to 8.07 (-O2), 8.61 to 8.64 (-O3) |
| `add_4/none` | 1.65 to 1.70 | 1.68 (-O2), 1.63 to 1.82 (-O3) | 2.62 to 2.66 | 2.63 to 2.65 |
| `add_16/nearest` | 28.7 to 29.3 (-O2), 27.1 to 28.0 (-O3) | 27.8 (-O2), 27.0 to 29.7 (-O3) | 22.8 to 23.0 | 22.8 to 23.3 |
| `add_16/nested` | 5.12 to 5.17 (-O2), 4.27 to 4.29 (-O3) | 4.48 to 4.57 (-O2), 4.16 to 4.52 (-O3) | 9.62 to 10.1 (-O2), 9.22 to 9.24 (-O3) | 9.80 to 10.3 (-O2), 9.25 to 9.27 (-O3) |
| `add_16/none` | 5.00 to 5.03 (-O2), 4.19 to 4.24 (-O3) | 4.37 to 4.43 (-O2), 4.08 to 4.51 (-O3) | 5.44 to 7.17 (-O2), 4.98 to 6.73 (-O3) | 5.92 to 5.94 (-O2), 5.55 to 5.58 (-O3) |
| `add_64/nearest` | 37.5 to 38.8 | 37.0 to 37.1 (-O2), 36.5 to 39.1 (-O3) | 27.6 to 27.7 (-O2), 27.6 to 65.2 (-O3) | 27.8 |
| `add_64/nested` | 15.3 to 16.0 | 14.2 to 14.5 (-O2), 14.2 to 14.9 (-O3) | 16.4 to 18.1 (-O2), 16.4 (-O3) | 16.8 to 17.3 |
| `add_64/none` | 15.3 to 16.0 | 14.1 to 14.4 (-O2), 14.2 to 15.3 (-O3) | 16.1 to 16.2 | 16.4 to 16.8 |
| `add_256/nearest` | 76.4 to 79.4 | 77.3 to 77.6 (-O2), 75.9 to 83.9 (-O3) | 65.3 to 65.6 | 65.9 to 67.2 |
| `add_256/nested` | 59.0 to 61.0 | 58.1 (-O2), 57.1 to 64.0 (-O3) | 59.4 to 59.6 | 59.7 to 60.4 (-O2), 64.1 to 64.4 (-O3) |
| `add_256/none` | 59.7 to 61.9 | 57.3 (-O2), 56.6 to 63.3 (-O3) | 59.3 to 60.0 | 59.7 to 60.6 (-O2), 63.9 to 64.3 (-O3) |
| `add_1024/nearest` | 234 to 245 | 234 to 236 (-O2), 235 to 257 (-O3) | 465 to 471 | 466 to 470 |
| `add_1024/nested` | 220 to 225 (-O2), 215 to 229 (-O3) | 215 (-O2), 211 to 233 (-O3) | 465 to 471 | 464 to 469 |
| `add_1024/none` | 228 to 237 | 215 (-O2), 211 to 233 (-O3) | 467 to 470 | 463 to 469 |
| `add_4096/nearest` | 3212 to 3290 | 3215 to 3233 (-O2), 3153 to 3570 (-O3) | 1849 to 1858 | 1851 to 1857 |
| `add_4096/nested` | 3192 to 3284 | 3127 to 3148 (-O2), 3169 to 3561 (-O3) | 1845 to 1855 | 1849 to 1855 |
| `add_4096/none` | 3206 to 3291 | 3155 to 3164 (-O2), 3150 to 3526 (-O3) | 1827 to 1852 | 1847 to 1854 |

| `kairn::upward::add`: the scope of a call (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4: called from rounding to nearest, minus without the scope | 22.9 to 23.7 | 22.7 to 23.1 (-O2), 23.1 to 25.5 (-O3) | 19.0 | 19.0 |
| 16: called from rounding to nearest, minus without the scope | 22.9 to 24.2 | 23.4 to 23.5 (-O2), 22.8 to 25.2 (-O3) | 15.7 to 17.5 (-O2), 16.3 to 18.0 (-O3) | 17.2 to 17.3 |
| 64: called from rounding to nearest, minus without the scope | 21.9 to 23.1 | 22.2 to 23.8 | 11.5 (-O2), 11.4 to 49.0 (-O3) | 11.1 to 11.3 |
| 256: called from rounding to nearest, minus without the scope | 16.5 to 18.1 | 20.0 to 20.3 (-O2), 16.4 to 20.6 (-O3) | 6.00 to 6.12 (-O2), 5.32 to 6.19 (-O3) | 5.52 to 6.31 (-O2), 2.82 to 3.14 (-O3) |
| 1024: called from rounding to nearest, minus without the scope | 1.60 to 6.10 (-O2), 6.70 to 8.80 (-O3) | 19.3 to 21.5 (-O2), 20.7 to 24.6 (-O3) | 0.300 to 1.10 (-O2), -2.80 to 1.70 (-O3) | -0.200 to 6.60 (-O2), -2.60 to 4.20 (-O3) |
| 4096: called from rounding to nearest, minus without the scope | -15.0 to 14.0 (-O2), -11.0 to 40.0 (-O3) | 51.0 to 78.0 (-O2), 3.00 to 116 (-O3) | 1.00 to 31.0 (-O2), -1.00 to 4.00 (-O3) | 1.00 to 2.00 (-O2), 3.00 to 5.00 (-O3) |
| 4: inside an outer Scope, minus without the scope | -0.004 to 0.039 | -0.042 to 0.089 | 5.39 to 5.44 | 5.40 to 5.43 (-O2), 5.98 to 6.00 (-O3) |
| 16: inside an outer Scope, minus without the scope | 0.037 to 0.136 | -0.007 to 0.228 | 2.93 to 4.18 (-O2), 2.51 to 4.26 (-O3) | 3.87 to 4.39 (-O2), 3.69 to 3.71 (-O3) |
| 64: inside an outer Scope, minus without the scope | -0.050 to 0.110 | -0.400 to 0.100 | 0.250 to 1.95 (-O2), 0.160 to 0.180 (-O3) | 0.080 to 0.550 |
| 256: inside an outer Scope, minus without the scope | -0.890 to -0.510 (-O2), -1.01 to -0.120 (-O3) | 0.750 to 0.840 (-O2), -0.670 to 0.710 (-O3) | 0.090 to 0.130 (-O2), -0.620 to 0.120 (-O3) | -0.140 to 0.610 (-O2), 0.030 to 0.220 (-O3) |
| 1024: inside an outer Scope, minus without the scope | -13.8 to -3.40 (-O2), -13.6 to -3.20 (-O3) | -0.100 to 0.700 (-O2), 0.400 to 0.500 (-O3) | 0.100 to 1.50 (-O2), -3.20 to 2.20 (-O3) | -1.60 to 5.30 (-O2), -3.40 to 3.30 (-O3) |
| 4096: inside an outer Scope, minus without the scope | -26.0 to 8.00 (-O2), -14.0 to -7.00 (-O3) | -33.0 to -13.0 (-O2), 19.0 to 49.0 (-O3) | 1.00 to 18.0 (-O2), -2.00 to 3.00 (-O3) | -1.00 to 1.00 (-O2), 0.000 to 3.00 (-O3) |

| `kairn::upward::add`: the scope's share of a call from rounding to nearest | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4 | 0.93 | 0.93 | 0.88 | 0.88 |
| 16 | 0.83 to 0.85 | 0.84 to 0.86 | 0.69 to 0.76 (-O2), 0.71 to 0.78 (-O3) | 0.74 to 0.76 |
| 64 | 0.58 to 0.60 | 0.60 to 0.62 | 0.42 (-O2), 0.41 to 0.75 (-O3) | 0.40 to 0.41 |
| 256 | 0.22 to 0.23 | 0.22 to 0.26 | 0.08 to 0.09 | 0.08 to 0.10 (-O2), 0.04 to 0.05 (-O3) |
| 1024 | 0.01 to 0.04 | 0.08 to 0.10 | -0.01 to 0.00 | -0.01 to 0.01 |
| 4096 | -0.00 to 0.01 | 0.00 to 0.04 | -0.00 to 0.02 | 0.00 |

| `kairn::upward::mul` by length, times (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `mul_4/nearest` | 30.1 to 31.4 | 32.2 to 32.3 (-O2), 31.2 to 33.3 (-O3) | 23.8 to 23.9 (-O2), 22.5 (-O3) | 22.9 |
| `mul_4/nested` | 5.33 to 5.45 (-O2), 5.01 to 5.12 (-O3) | 5.82 (-O2), 4.99 to 5.36 (-O3) | 12.3 (-O2), 8.95 to 8.96 (-O3) | 8.95 to 8.98 |
| `mul_4/none` | 5.07 to 5.29 | 5.65 to 5.66 (-O2), 5.00 to 5.42 (-O3) | 9.28 to 9.31 (-O2), 4.38 to 4.42 (-O3) | 3.96 to 5.28 (-O2), 3.96 to 3.98 (-O3) |
| `mul_16/nearest` | 46.2 to 47.9 | 46.4 to 46.5 (-O2), 45.8 to 49.8 (-O3) | 28.4 to 28.6 (-O2), 26.2 (-O3) | 26.4 to 26.5 |
| `mul_16/nested` | 19.2 to 19.9 | 19.8 (-O2), 19.2 to 20.8 (-O3) | 17.3 (-O2), 16.0 (-O3) | 14.4 to 14.5 (-O2), 14.4 to 16.2 (-O3) |
| `mul_16/none` | 18.7 to 19.5 | 19.6 (-O2), 18.7 to 20.6 (-O3) | 15.9 to 17.7 (-O2), 15.4 to 15.5 (-O3) | 13.8 to 15.6 (-O2), 13.8 (-O3) |
| `mul_64/nearest` | 101 to 105 | 102 (-O2), 100 to 111 (-O3) | 72.2 to 73.3 | 65.7 to 66.3 |
| `mul_64/nested` | 74.5 to 76.2 | 74.6 to 74.8 (-O2), 72.8 to 78.3 (-O3) | 60.4 to 61.7 | 53.6 to 53.9 |
| `mul_64/none` | 74.5 to 76.1 (-O2), 73.0 to 77.0 (-O3) | 74.4 to 74.5 (-O2), 73.1 to 78.2 (-O3) | 59.7 to 61.7 | 52.6 to 54.5 |
| `mul_256/nearest` | 325 to 332 | 324 (-O2), 319 to 352 (-O3) | 248 to 251 | 221 to 223 |
| `mul_256/nested` | 293 to 306 | 299 (-O2), 293 to 315 (-O3) | 237 to 239 | 210 to 212 |
| `mul_256/none` | 294 to 306 | 298 to 299 (-O2), 293 to 314 (-O3) | 237 to 238 | 207 to 210 |
| `mul_1024/nearest` | 1189 to 1240 | 1209 to 1215 (-O2), 1187 to 1312 (-O3) | 954 to 968 | 848 to 851 |
| `mul_1024/nested` | 1163 to 1212 | 1182 to 1183 (-O2), 1175 to 1314 (-O3) | 949 to 961 | 842 to 847 |
| `mul_1024/none` | 1186 to 1212 | 1181 to 1183 (-O2), 1182 to 1281 (-O3) | 950 to 956 | 841 to 844 |
| `mul_4096/nearest` | 4762 to 4938 | 4752 to 4762 (-O2), 4667 to 5151 (-O3) | 3800 to 3826 | 3352 to 3364 |
| `mul_4096/nested` | 4737 to 4910 | 4725 to 4744 (-O2), 4629 to 5121 (-O3) | 3790 to 3811 | 3344 to 3353 |
| `mul_4096/none` | 4645 to 4845 | 4680 to 4729 (-O2), 4648 to 5129 (-O3) | 3784 to 3815 | 3341 to 3355 |

| `kairn::upward::mul`: the scope of a call (ns per call) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4: called from rounding to nearest, minus without the scope | 24.8 to 26.1 | 26.2 to 27.9 | 14.5 to 14.6 (-O2), 18.1 to 18.2 (-O3) | 17.6 to 18.9 |
| 16: called from rounding to nearest, minus without the scope | 27.2 to 28.6 | 26.8 to 29.1 | 10.9 to 12.6 (-O2), 10.7 to 10.8 (-O3) | 10.8 to 12.6 (-O2), 12.6 (-O3) |
| 64: called from rounding to nearest, minus without the scope | 28.5 to 29.1 (-O2), 23.9 to 30.1 (-O3) | 27.8 to 28.0 (-O2), 27.2 to 32.4 (-O3) | 11.6 to 13.5 (-O2), 11.0 to 11.3 (-O3) | 11.2 to 13.4 (-O2), 12.7 to 12.8 (-O3) |
| 256: called from rounding to nearest, minus without the scope | 25.4 to 26.0 (-O2), 25.4 to 30.8 (-O3) | 24.8 to 25.7 (-O2), 25.4 to 37.1 (-O3) | 11.2 to 13.7 (-O2), 11.0 to 12.1 (-O3) | 13.2 to 15.1 (-O2), 11.5 to 12.4 (-O3) |
| 1024: called from rounding to nearest, minus without the scope | 26.0 to 28.0 (-O2), -20.0 to 28.0 (-O3) | 27.0 to 34.0 (-O2), 5.00 to 31.0 (-O3) | 9.60 to 12.7 (-O2), 2.90 to 9.00 (-O3) | 6.60 to 8.20 (-O2), 6.40 to 6.90 (-O3) |
| 4096: called from rounding to nearest, minus without the scope | 23.0 to 25.0 (-O2), 16.0 to 293 (-O3) | 24.0 to 82.0 (-O2), 19.0 to 26.0 (-O3) | 3.00 to 17.0 (-O2), 9.00 to 16.0 (-O3) | 9.00 to 14.0 (-O2), 9.00 to 13.0 (-O3) |
| 4: inside an outer Scope, minus without the scope | -0.228 to 0.165 | -0.117 to 0.168 | 2.98 to 3.03 (-O2), 4.53 to 4.56 (-O3) | 3.67 to 4.99 (-O2), 4.98 to 5.01 (-O3) |
| 16: inside an outer Scope, minus without the scope | 0.200 to 0.540 (-O2), 0.120 to 0.700 (-O3) | 0.150 to 0.490 | -0.440 to 1.36 (-O2), 0.520 to 0.580 (-O3) | -1.16 to 0.640 (-O2), 0.630 to 2.35 (-O3) |
| 64: inside an outer Scope, minus without the scope | 0.040 to 0.100 (-O2), -0.770 to 1.56 (-O3) | 0.180 to 0.410 (-O2), -0.290 to 0.090 (-O3) | -0.090 to 1.74 (-O2), -0.730 to 0.510 (-O3) | -0.700 to 1.15 (-O2), 0.330 to 0.490 (-O3) |
| 256: inside an outer Scope, minus without the scope | -0.400 (-O2), -0.700 to -0.100 (-O3) | -0.100 to 0.800 (-O2), -0.600 to 0.400 (-O3) | 0.400 to 1.30 (-O2), -0.500 to 0.500 (-O3) | 1.70 to 2.40 (-O2), 0.700 to 1.30 (-O3) |
| 1024: inside an outer Scope, minus without the scope | -1.00 to 0.000 (-O2), -46.0 to 0.000 (-O3) | -1.00 to 2.00 (-O2), -7.00 to 33.0 (-O3) | 1.10 to 4.90 (-O2), -2.00 to -1.20 (-O3) | 1.00 to 3.60 (-O2), -0.100 to 1.70 (-O3) |
| 4096: inside an outer Scope, minus without the scope | -7.00 to -2.00 (-O2), -9.00 to 265 (-O3) | -4.00 to 48.0 (-O2), -19.0 to -8.00 (-O3) | -9.00 to 2.00 (-O2), -6.00 to 7.00 (-O3) | -3.00 to 7.00 (-O2), 3.00 to 7.00 (-O3) |

| `kairn::upward::mul`: the scope's share of a call from rounding to nearest | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| 4 | 0.83 to 0.84 | 0.82 to 0.84 | 0.61 (-O2), 0.80 to 0.81 (-O3) | 0.77 to 0.83 (-O2), 0.83 (-O3) |
| 16 | 0.59 to 0.60 | 0.58 to 0.59 | 0.38 to 0.44 (-O2), 0.41 (-O3) | 0.41 to 0.48 (-O2), 0.48 (-O3) |
| 64 | 0.28 (-O2), 0.24 to 0.29 (-O3) | 0.27 to 0.29 | 0.15 to 0.18 | 0.17 to 0.20 |
| 256 | 0.08 to 0.09 | 0.08 to 0.11 | 0.04 to 0.05 | 0.05 to 0.07 |
| 1024 | -0.02 to 0.02 | 0.00 to 0.03 | 0.00 to 0.01 | 0.01 |
| 4096 | 0.00 to 0.01 (-O2), 0.00 to 0.06 (-O3) | 0.00 to 0.02 | 0.00 | 0.00 |

<!-- END up_report lengths -->

- **From rounding to nearest**, a call pays 23 to 28 ns for its scope on the M3 and 15 to 19 ns on
  Zen 2 at 4 elements: 61 to 93% of the call. On the M3 the cost stays about the same up to 256
  elements (16 to 21 ns for sums, 25 to 37 for products), as if a write of FPCR waited for the
  operations before it. On Zen 2 it shrinks with the length of the call, to 11 ns at 64 elements and 3
  to 6 ns at 256 for sums (11 to 15 for products), as if the writes of MXCSR overlapped the work of a
  long call (an inference from the times; the machine code was not examined).
- **The share of the scope is under 10% of a call** on Zen 2 from 256 elements (sums 4 to 10%,
  products 4 to 7%); on the M3 from 256 for products (8 to 11%, at the limit) and from 1024 for sums (1
  to 10%; at 256, 22 to 26%). At 64 elements it is 40 to 75% of a sum and 15 to 29% of a product.
- **Inside an outer `Scope`**, where the function's scope only reads the register, a call costs
  nothing measurable more than the kernel on the M3, and 5.4 to 6.0 ns at 4 elements and 2.5 to 4.4 at
  16 for sums on Zen 2 (3.0 to 5.0 and up to 2.4 for products), nothing measurable from 64: a program
  that calls the functions on short arrays in a loop holds one `Scope` around the loop.

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
| `upws/call/scope_add_1/none` | 0.907 to 0.935 | 0.907 to 0.910 (-O2), 0.891 to 0.984 (-O3) | 2.16 to 2.18 | 1.98 to 2.00 |
| `upws/call/scope_add_1/change` | 23.9 to 24.9 | 24.2 to 24.4 (-O2), 24.0 to 25.8 (-O3) | 52.2 to 52.5 | 52.8 to 53.0 |
| `upws/call/scope_add_1/nested` | 0.919 to 0.944 (-O2), 0.896 to 0.947 (-O3) | 1.45 (-O2), 1.42 to 1.56 (-O3) | 14.3 to 14.5 | 14.3 to 14.6 |
| `upws/call/regscope_add_1/change` | 24.3 to 25.0 | 24.4 to 24.5 (-O2), 24.0 to 26.5 (-O3) | 21.3 to 21.4 | 21.3 to 21.4 |
| `upws/call/regscope_add_1/nested` | 0.913 to 0.943 | 1.45 (-O2), 1.42 to 1.53 (-O3) | 7.96 to 7.98 | 7.41 to 7.45 |
| `upws/call/nearest_add_1/none` | 2.14 to 2.24 | 3.01 to 3.07 (-O2), 3.08 to 3.37 (-O3) | 5.65 to 5.81 | 5.79 to 6.05 |
| `upws/call/nearest_add_1/change` | 31.4 to 32.7 | 27.7 to 27.8 (-O2), 27.2 to 29.3 (-O3) | 56.6 to 57.0 | 55.9 to 129 (-O2), 55.9 to 56.6 (-O3) |
| `upws/call/nearest_add_1/nested` | 2.63 to 2.74 | 3.80 to 3.84 (-O2), 3.81 to 4.07 (-O3) | 16.6 to 16.7 | 17.3 to 17.4 |

| The cost of a scope (ns per call: the call with it minus without it) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `Scope` that changes the mode | 23.0 to 23.9 | 23.1 to 24.8 | 50.1 to 50.3 | 50.8 to 51.0 |
| `Scope` inside a `Scope` (nothing changes) | -0.012 to 0.016 | 0.508 to 0.572 | 12.1 to 12.3 | 12.3 to 12.6 |
| register-only scope (of the functions on arrays) that changes the mode | 23.4 to 24.0 | 23.5 to 23.6 (-O2), 23.1 to 25.5 (-O3) | 19.1 to 19.2 | 19.3 to 19.4 |
| register-only scope inside a `Scope` | 0.002 to 0.015 | 0.508 to 0.546 | 5.79 to 5.81 | 5.41 to 5.45 |
| `NearestScope` inside a `Scope` (changes the mode) | 29.3 to 30.4 | 24.1 to 25.9 | 50.9 to 51.4 | 50.1 to 124 (-O2), 49.9 to 50.6 (-O3) |
| `NearestScope` where the mode is to nearest | 0.487 to 0.515 | 0.706 to 0.815 | 10.8 to 11.0 | 11.3 to 11.5 |

<!-- END up_report scopes -->

- **A scope that changes the mode** costs 23 to 25 ns on the M3 (two writes of FPCR, the register
  being the C library's mode there), 50 to 51 ns on Zen 2 and 9.4 ns with MSVC on the i5 (unpinned,
  [question 8](#8-msvc-unpinned)). The register-only scope of the functions on arrays costs the same on
  the M3 (23 to 26 ns) and with MSVC (9.2 ns), and 19 ns on Zen 2: there the user-facing `Scope` also
  calls glibc's `fegetround` and `fesetround`, which read and write the x87 control word and MXCSR, and
  that costs 2.6 times the register's own read and writes.
- **A scope that changes nothing** costs one read of the register (and, for the user-facing scope on
  x86-64, one `fegetround`): nothing measurable on the M3 with Apple clang, 0.5 ns with GCC 16; 12 ns on
  Zen 2 (5.4 to 5.8 for the register-only scope: a read of MXCSR and a test cost more there than a
  sum); 2.8 ns with MSVC (1.7 for the register-only one).
- **A `NearestScope` inside an upward region** costs what a `Scope` costs: 24 to 30 ns on the M3, 50 to
  51 ns on Zen 2 (in one run of four with Clang 18 at `-O2`, 124 ns), 6.9 ns with MSVC; where the mode
  is already to nearest, 0.5 to 0.8 ns on the M3, 11 ns on Zen 2, 0.5 to 0.6 with MSVC.
- So a scope that changes the mode costs as much as 55 to 125 sums of the type on Zen 2 and 50 to 75
  on the M3, and against the default type it is repaid after 14 to 20 sums on Zen 2 and about 16 on
  the M3 (each saving 2.6 to 3.6 ns, and about 1.4). A scope around each operation, as in these calls,
  makes a call 10 to 27 times as long as without it.

### 6. `float`

`kairn::upward::Interval<float>` (on x86-64 the two low lanes of an `__m128`, on arm64 a
`float32x2_t`), loops of sums and products, next to `Interval<float, 1>`; the functions on arrays of
`float` are in [question 3](#3-the-functions-on-arrays).

<!-- BEGIN up_report float -->

| `float`, times (ns per operation) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `upwf/tp/interval_add_1/native` | 0.509 to 0.519 | 0.393 to 0.394 (-O2), 0.386 to 0.426 (-O3) | 0.593 to 0.720 (-O2), 0.598 to 0.599 (-O3) | 1.11 to 1.41 (-O2), 1.11 (-O3) |
| `upwf/tp/interval_add_1/conv` | 1.30 to 1.35 | 1.13 (-O2), 1.04 to 1.15 (-O3) | 3.04 (-O2), 3.03 to 3.31 (-O3) | 3.54 to 3.67 |
| `m2f/tp/interval_add_1/op` | 1.91 to 1.95 | 0.871 to 0.886 (-O2), 0.871 to 0.933 (-O3) | 1.76 to 1.77 | 5.12 to 5.14 |
| `m2f/tp/interval_add_1/fenv_loop` | 0.504 to 0.522 | 0.369 (-O2), 0.299 to 0.320 (-O3) | 1.22 to 1.24 | 1.62 to 1.64 |
| `upwf/tp/interval_mul_1/native` | 1.27 to 1.30 | 1.38 to 1.40 (-O2), 1.38 to 1.48 (-O3) | 1.98 to 1.99 | 2.02 to 2.32 (-O2), 2.02 to 2.03 (-O3) |
| `upwf/tp/interval_mul_1/conv` | 2.46 to 2.56 | 2.44 to 2.45 (-O2), 2.39 to 2.65 (-O3) | 5.69 to 5.72 | 6.13 to 6.15 (-O2), 5.80 to 5.81 (-O3) |
| `m2f/tp/interval_mul_1/op` | 6.46 to 6.53 (-O2), 6.12 to 6.24 (-O3) | 8.10 to 8.12 (-O2), 7.98 to 8.50 (-O3) | 4.89 to 4.92 | 16.0 to 16.1 |
| `m2f/tp/interval_mul_1/fenv_loop` | 1.47 to 1.50 | 0.605 (-O2), 0.593 to 0.638 (-O3) | 1.47 to 1.48 | 4.19 to 4.38 (-O2), 3.76 to 3.89 (-O3) |

| `float`, ratios | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 |
|---|---|---|---|---|
| `X + Y`: Interval<float, 1> over the type | 3.72 to 3.79 | 2.22 to 2.25 (-O2), 2.19 to 2.32 (-O3) | 2.46 to 2.98 (-O2), 2.94 to 2.95 (-O3) | 3.65 to 4.61 (-O2), 4.60 to 4.63 (-O3) |
| `X * Y`: Interval<float, 1> over the type | 5.02 to 5.08 (-O2), 4.73 to 4.91 (-O3) | 5.76 to 5.91 | 2.46 to 2.48 | 6.93 to 7.93 (-O2), 7.92 to 7.95 (-O3) |
| `X + Y`: the type over fenv_loop | 0.99 to 1.02 | 1.07 (-O2), 1.27 to 1.33 (-O3) | 0.48 to 0.58 (-O2), 0.49 (-O3) | 0.69 to 0.86 (-O2), 0.68 (-O3) |
| `X * Y`: the type over fenv_loop | 0.87 | 2.28 to 2.32 | 1.34 to 1.35 | 0.46 to 0.53 (-O2), 0.52 to 0.54 (-O3) |
| `X + Y`: converted over native | 2.53 to 2.56 (-O2), 2.53 to 2.61 (-O3) | 2.86 to 2.87 (-O2), 2.70 to 2.82 (-O3) | 4.22 to 5.13 (-O2), 5.07 to 5.52 (-O3) | 2.52 to 3.27 (-O2), 3.18 to 3.20 (-O3) |
| `X * Y`: converted over native | 1.94 to 1.98 | 1.74 to 1.77 (-O2), 1.69 to 1.79 (-O3) | 2.87 to 2.88 | 2.65 to 3.03 (-O2), 2.86 to 2.87 (-O3) |

<!-- END up_report float -->

- The type with `float` takes 0.72 to 1.15 of its time with `double` (one register either way) and is
  2.2 to 4.6 times faster than `Interval<float, 1>` for sums and 2.5 to 7.9 times for products: less
  than with `double` where the compiler vectorizes the default type's `float` loop with twice the lanes
  (GCC 16 for sums, GCC 13 for sums and products), more where the default `float` loop is slower than
  the `double` one (Clang 18).
- On arrays, `float` takes 0.48 to 0.68 of `double`'s time, twice the lanes; a sum costs 0.15 to 0.22
  ns per interval, a product 0.46 to 0.75.

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
| `upw/tp/interval_add_1/native` | 3.77 to 3.85 | 5.75 to 5.96 (-O2), 4.98 to 5.08 (-O3) | 10.2 (-O2), 9.4 to 14.1 (-O3) | 8.96 to 9.05 (-O2), 8.18 to 8.19 (-O3) |
| `upw/tp/interval_add_1/native_x16` | 4.24 to 4.55 (-O2), 4.32 to 4.35 (-O3) | 6.97 to 7.23 (-O2), 5.97 to 6.11 (-O3) | 12.7 to 12.8 (-O2), 19.1 to 20.4 (-O3) | 10.6 to 10.8 |
| `upw/tp/interval_add_1/conv` | 3.55 to 3.82 (-O2), 3.53 to 3.54 (-O3) | 4.88 to 5.06 (-O2), 5.18 to 5.19 (-O3) | 4.49 to 4.59 (-O2), 4.46 to 4.60 (-O3) | 9.49 to 9.65 |
| `upw/tp/interval_mul_1/native` | 1.92 to 2.01 (-O2), 1.90 to 1.91 (-O3) | 1.85 to 1.91 (-O2), 1.86 to 1.91 (-O3) | 4.50 to 4.51 (-O2), 4.25 to 4.57 (-O3) | 4.35 to 4.39 (-O2), 4.76 to 5.03 (-O3) |
| `upw/tp/interval_mul_1/native_x16` | 1.95 to 2.07 (-O2), 1.95 to 1.99 (-O3) | 1.95 to 1.99 | 4.82 to 4.88 | 5.41 to 5.46 |
| `upw/tp/interval_mul_1/conv` | 2.11 to 2.22 (-O2), 2.09 to 2.15 (-O3) | 2.44 to 2.46 (-O2), 2.53 to 2.59 (-O3) | 2.39 to 2.45 (-O2), 2.30 to 2.32 (-O3) | 5.47 to 5.52 (-O2), 5.59 to 5.70 (-O3) |
| `upw/sum/interval_add_1/native` | 2.39 to 2.61 (-O2), 2.49 to 2.53 (-O3) | 2.52 to 2.67 (-O2), 2.57 to 2.61 (-O3) | 6.62 to 8.28 (-O2), 5.56 to 8.26 (-O3) | 9.02 to 9.10 (-O2), 6.14 to 7.52 (-O3) |
| `upw/sum/interval_add_1/native_x16` | 2.66 to 2.87 (-O2), 2.55 to 2.61 (-O3) | 2.63 to 2.76 (-O2), 2.58 to 2.66 (-O3) | 8.34 to 8.67 (-O2), 8.59 to 8.66 (-O3) | 9.71 to 9.98 |
| `upw/prod/interval_mul_1/native` | 0.96 to 1.07 (-O2), 1.02 (-O3) | 1.02 to 1.06 | 1.50 to 1.52 (-O2), 1.41 to 1.47 (-O3) | 2.47 to 2.70 (-O2), 2.68 (-O3) |
| `upw/prod/interval_mul_1/native_x16` | 0.98 to 1.06 (-O2), 1.02 (-O3) | 1.01 to 1.06 (-O2), 1.02 to 1.11 (-O3) | 1.50 to 1.53 | 2.65 to 2.68 |
| `upwf/tp/interval_add_1/native` | 3.76 to 3.91 (-O2), 3.78 to 3.81 (-O3) | 5.07 to 5.14 (-O2), 5.58 to 5.76 (-O3) | 11.2 to 13.6 (-O2), 13.6 to 13.7 (-O3) | 6.97 to 9.00 (-O2), 8.77 to 8.82 (-O3) |
| `upwf/tp/interval_mul_1/native` | 1.91 to 2.11 (-O2), 2.00 to 2.01 (-O3) | 1.91 to 1.98 (-O2), 1.87 to 1.91 (-O3) | 4.33 to 4.38 | 4.42 to 5.05 (-O2), 5.04 to 5.07 (-O3) |
| `upwa/tp/interval_add_1/op` | 6.55 to 6.84 (-O2), 6.55 to 6.60 (-O3) | 10.0 to 10.3 (-O2), 9.8 to 10.0 (-O3) | 18.1 to 18.4 (-O2), 17.1 to 17.3 (-O3) | 19.4 to 19.6 |
| `upwa/tp/interval_mul_1/op` | 2.27 to 2.33 | 3.13 to 3.17 | 5.51 to 5.57 (-O2), 5.28 to 5.35 (-O3) | 6.43 to 6.50 |
| `upwaf/tp/interval_add_1/op` | 9.17 to 9.90 (-O2), 9.50 to 9.55 (-O3) | 14.8 to 15.3 (-O2), 14.5 to 14.8 (-O3) | 29.5 to 30.3 | 34.0 to 34.9 (-O2), 31.1 to 31.4 (-O3) |
| `upwaf/tp/interval_mul_1/op` | 3.34 to 3.71 (-O2), 3.51 to 3.53 (-O3) | 4.91 to 5.11 (-O2), 4.86 to 4.97 (-O3) | 9.80 to 9.91 | 11.0 to 11.2 |
| `upws/call/scope_add_1/change` | 1.03 to 1.11 (-O2), 1.08 (-O3) | 1.13 to 1.18 (-O2), 1.11 to 1.17 (-O3) | 1.16 to 1.17 (-O2), 1.15 to 2.50 (-O3) | 1.15 (-O2), 1.15 to 1.82 (-O3) |
| `upws/call/scope_add_1/nested` | 2.69 to 2.78 (-O2), 2.79 to 2.80 (-O3) | 2.68 to 2.77 (-O2), 2.67 (-O3) | 1.54 to 1.55 | 1.62 to 1.70 (-O2), 1.67 (-O3) |
| `upws/call/regscope_add_1/change` | 1.03 to 1.08 | 1.10 to 1.13 (-O2), 1.11 to 1.17 (-O3) | 1.46 to 1.47 | 1.49 to 1.53 |
| `m2/tp/interval_add_1/op` | 1.64 to 1.71 (-O2), 1.69 to 1.73 (-O3) | 2.29 to 2.34 | 2.82 to 2.86 | 3.58 to 3.61 |
| `m2/tp/interval_mul_1/op` | 1.14 to 1.26 (-O2), 1.20 to 1.21 (-O3) | 1.08 to 1.11 | 2.16 to 2.18 | 1.32 to 1.33 |
| `m2/sum/interval_add_1/op` | 0.97 to 1.03 (-O2), 1.01 (-O3) | 1.08 to 1.11 (-O2), 1.06 to 1.09 (-O3) | 1.92 to 1.94 | 2.38 to 2.42 |
| `m2/prod/interval_mul_1/op` | 1.01 to 1.04 (-O2), 0.98 (-O3) | 1.04 to 1.08 | 1.11 to 1.13 | 1.28 to 1.30 |

<!-- END up_report checks -->

- The assertions cost most where an operation costs least: a loop of sums of the type takes 3.8 to 6.0
  times as long on the M3 and 8.2 to 14 times on Zen 2 (with 16 loops per scope 4.2 to 7.2 and 10.6 to
  20), a loop of products 1.8 to 2.1 and 4.2 to 5.5 times, a chain of sums 2.4 to 2.9 and 5.6 to 10, a
  chain of products 0.96 to 1.11 and 1.4 to 2.7 (the checks are off its critical path). A read of MXCSR
  is dear on Zen 2 ([question 5](#5-the-scopes): a scope that only reads it costs 5.4 to 5.8 ns), which
  is what each operation now does.
- The functions on arrays, which test every element, take 6.6 to 10 times as long for sums of `double`
  on the M3 and 17 to 20 on Zen 2, 2.3 to 3.2 and 5.3 to 6.5 for products; with `float` 9.2 to 15 and
  30 to 35, 3.3 to 5.1 and 9.8 to 11.2.
- A call of one sum in a scope that changes the mode takes 1.03 to 1.18 times as long on the M3 and
  1.15 to 2.5 on Zen 2 (the check of the build on the scope's entry, and the sum's own checks); in a
  scope that changes nothing, 1.5 to 2.8 times (the sum's checks).
- The default `Interval<T, 1>` pays 1.6 to 3.6 times for its sums with its own checks, and 1.0 to 2.4
  for its chains: the checked build is a build to find mistakes in, not to measure.

### 8. MSVC, unpinned

One short item on the i5 with MSVC 19.52 at `/O2 /arch:AVX2` (the file of the type with `/fp:strict`,
where the barrier of each scope is the refresh and the pin of the design page's section "MSVC"):
the type's sums, products and chains, and the scopes, next to the default type, **unpinned** (the
thread may run on a performance or an efficiency core), on another project's CI machine with no build
running during the runs; three runs, the spread at the median function 1.006 to 1.011.

<!-- BEGIN up_report msvc -->

| MSVC, times (ns per operation or step), unpinned | i5-13500T, MSVC (unpinned) |
|---|---|
| `upw/tp/interval_add_1/native` | 0.527 to 0.542 (-O2) |
| `upw/tp/interval_add_1/native_x16` | 0.475 to 0.505 (-O2) |
| `upw/tp/interval_add_1/conv` | 2.19 to 2.20 (-O2) |
| `m2/tp/interval_add_1/op` | 6.95 to 6.96 (-O2) |
| `m2/tp/interval_add_1/fenv_loop` | 0.512 (-O2) |
| `upw/tp/interval_mul_1/native` | 1.49 (-O2) |
| `upw/tp/interval_mul_1/native_x16` | 1.43 (-O2) |
| `upw/tp/interval_mul_1/conv` | 3.72 (-O2) |
| `m2/tp/interval_mul_1/op` | 20.6 (-O2) |
| `m2/tp/interval_mul_1/fenv_loop` | 1.60 (-O2) |
| `upw/sum/interval_add_1/native` | 0.749 to 0.753 (-O2) |
| `m2/sum/interval_add_1/op` | 9.18 (-O2) |
| `upw/sum/interval_add_1/native_x16` | 0.866 to 0.867 (-O2) |
| `upw/prod/interval_mul_1/native` | 5.09 (-O2) |
| `upw/prod/interval_mul_1/native_x16` | 5.17 (-O2) |
| `upw/prod/interval_mul_1/conv` | 5.20 (-O2) |
| `m2/prod/interval_mul_1/op` | 23.4 to 23.5 (-O2) |
| `m2/prod/interval_mul_1/fenv_loop` | 3.42 (-O2) |

| MSVC, ratios, unpinned | i5-13500T, MSVC (unpinned) |
|---|---|
| `X + Y`: Interval<T, 1> over the type | 12.8 to 13.2 (-O2) |
| `X + Y`: Interval<T, 1> over the type, 16 loops per scope | 13.7 to 14.6 (-O2) |
| `X * Y`: Interval<T, 1> over the type | 13.8 (-O2) |
| `X * Y`: Interval<T, 1> over the type, 16 loops per scope | 14.4 (-O2) |
| `S + X`: Interval<T, 1> over the type | 12.2 to 12.3 (-O2) |
| `P * X`: Interval<T, 1> over the type | 4.60 to 4.61 (-O2) |
| `P * X`: Interval<T, 1> over the type, a chain 16 times as long per scope | 4.53 to 4.54 (-O2) |
| `X + Y`: the type over fenv_loop | 1.03 to 1.06 (-O2) |
| `X * Y`: the type over fenv_loop | 0.93 (-O2) |
| `P * X`: the type over fenv_loop | 1.49 (-O2) |

| Calls of one operation, times (ns per call) | i5-13500T, MSVC (unpinned) |
|---|---|
| `upws/call/scope_add_1/none` | 0.836 to 0.863 (-O2) |
| `upws/call/scope_add_1/change` | 10.3 (-O2) |
| `upws/call/scope_add_1/nested` | 3.62 to 3.67 (-O2) |
| `upws/call/regscope_add_1/change` | 10.1 (-O2) |
| `upws/call/regscope_add_1/nested` | 2.52 to 2.54 (-O2) |
| `upws/call/nearest_add_1/none` | 8.53 to 8.54 (-O2) |
| `upws/call/nearest_add_1/change` | 15.4 (-O2) |
| `upws/call/nearest_add_1/nested` | 9.05 to 9.15 (-O2) |

| The cost of a scope (ns per call: the call with it minus without it) | i5-13500T, MSVC (unpinned) |
|---|---|
| `Scope` that changes the mode | 9.40 to 9.43 (-O2) |
| `Scope` inside a `Scope` (nothing changes) | 2.75 to 2.83 (-O2) |
| register-only scope (of the functions on arrays) that changes the mode | 9.21 to 9.23 (-O2) |
| register-only scope inside a `Scope` | 1.66 to 1.70 (-O2) |
| `NearestScope` inside a `Scope` (changes the mode) | 6.83 to 6.91 (-O2) |
| `NearestScope` where the mode is to nearest | 0.519 to 0.617 (-O2) |

<!-- END up_report msvc -->

- With MSVC the default type is slow (7.0 ns per sum, 21 ns per product, 23 ns per step of a product
  chain), the type not (0.53, 1.49 and 5.1 ns): 13 to 15 times faster in loops, 12 times in a chain of
  sums, 4.5 to 4.6 times in a chain of products. The type matches the classical loop under one mode
  (1.03 to 1.06 for sums, 0.93 for products; 1.49 for the chain of products).
- A scope that changes the mode costs 9.4 ns, the register-only one 9.2 ns, a `NearestScope` in an
  upward region 6.9 ns; a scope that changes nothing 2.8 ns (1.7): the write of MXCSR through a function
  of its own, the refresh of the zero and the C library's mode are cheaper on this machine than on Zen 2.

## How it was measured

| Machine | Configurations | Conditions |
|---|---|---|
| M3: macOS 26.6 arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2; `-O2` and `-O3`; NEON (the functions on arrays and the packed kernels: 2 lanes of `double`, 4 of `float`) | shared with the builds and tests of three other authors: each run started when the 1-minute load average was under 6 (it was 2.0 to 8.2 at the start and the end of the timing, as recorded); no affinity, the thread in the user-interactive class; a run whose spread at the median function (the median over the functions of the median over the minimum of their 31 samples) was above 5% set aside and made again, up to six times; three kept runs and three kept pairs of the checked build per configuration |
| Zen 2: Linux x86-64 (Ubuntu 24.04), AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1; `-O2` and `-O3`; `-mfma`, the functions on arrays and the packed kernels `-mavx2 -mfma` (4 lanes of `double`, 8 of `float`) | the four configurations at once, each in a core complex of its own of the first socket (logical CPUs 4 to 7, 12 to 15, 20 to 23 and 28 to 31); each run pinned (`taskset`, `--cpu`) to the CPU of its range whose usage and its SMT sibling's (CPU + 64) were the lowest over the 2 s before it, the usage of the two sampled every 5 s from `/proc/stat` during the run; a run whose sibling was busy (above 10% in a sample) or whose spread at the median function was above 5% set aside and made again, up to four times; four kept runs and four kept pairs per configuration; the machine was shared (load average 28 to 31 during the runs: another author's brute-force campaign and tests on the second socket and, at times, on the first); the sibling of every kept run was busy at most 2% in a sample |
| i5: Windows 11 x64, Intel Core i5-13500T (6 performance, 8 efficiency cores) | MSVC 19.52, `/O2 /arch:AVX2`, the file of the type `/fp:strict` | not pinned (the thread may run on either kind of core); another project's CI machine, no build running on it during the runs; one item (the sums, the products, the product chain and the scopes, next to the default type), three kept runs, the same rule of 5% |

- **Commit**: `4710839b` on every machine, recorded in every JSON file: the tree of the feature
  (`41ee1bd6`, `include/` untouched since) with the harness of this page.
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
  interval"). The packed kernels of Milestone 2 on its own arrays (`m2p`), whose loads fall 32 bytes
  from the previous iteration's stores modulo 4 KB, take 0.90 to 1.10 times the same loops on the
  placed arrays: the aliasing costs those loops nothing measurable on these two machines.
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
reason. On Zen 2 none was set aside at this commit. On the M3, where other authors built and tested
while these ran, runs with a spread above 5% at the median function were set aside and made again:
5 of Apple clang's at `-O3` (spreads 1.054 to 1.213) and 8 of GCC 16's (1.050 to 1.128); of the pairs
of the checked build, 57 of Apple clang's at `-O3` (1.070 to 1.224, the short runs of that item
bimodal, either about 1.003 or above 1.07, at load averages of 2 to 6) and 3 of GCC 16's, with the
runs of their pairs; every kept run came within its six attempts but the first pair of Apple clang at
`-O3`, made again after them. With MSVC, two attempts of the second run (spread 1.07). On the M3 a
whole run can be a few percent faster or slower than another (GCC 16 at `-O3`: the median function
10% apart over its three runs), which moves the times and not the ratios within a run.

Two earlier campaigns of the same day are not stored: one at `d971de5e` on Zen 2 and the M3, before the
16-pass difference and chains were added; and one at `8f34267d`, whose 16-pass chain of sums of the rounding-mode prop added through an interval type that
negates twice per step, where `m2_fenv.cpp` keeps the lower bound negated and adds once (on the M3
2.2 times slower than the prop it was meant to repeat). The prop was rewritten and every machine
measured again at `4710839b`.

## Not measured

- The round-up interval with the two-number form forced (`KAIRN_UPWARD_FORM_NUMBERS`), clang-cl, and
  the functions on arrays, the determinant, Horner and `float` with MSVC (one short table only, as
  planned); MSVC pinned to a performance core.
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
| linux-clang-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `4710839b` |
| linux-clang-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | Clang 18.1.3 (1ubuntu1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `4710839b` |
| linux-gcc-O2 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `4710839b` |
| linux-gcc-O3 | AMD EPYC 7452 32-Core Processor; pinned to one logical CPU | GCC 13.3.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | `... -frounding-math` | 4 | 2026-11-27, `4710839b` |
| mac-appleclang-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `4710839b` |
| mac-appleclang-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | Apple clang 21.0.0 (clang-2100.4.1.1) | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `4710839b` |
| mac-gcc16-O2 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O2 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `4710839b` |
| mac-gcc16-O3 | Apple M3 Max; not pinned (no affinity on macOS); QoS user-interactive | GCC 16.2.0 | `-Wall -Wextra -Werror -O3 -DNDEBUG -O3 -ffp-contract=off` | `... -frounding-math` | 3 | 2026-11-27, `4710839b` |
| windows-msvc-O2 | 13th Gen Intel(R) Core(TM) i5-13500T; not pinned | MSVC 19.52.37029 | `/DWIN32 /D_WINDOWS /EHsc /O2 /Ob2 /DNDEBUG /O2 /arch:AVX2` | `... /fp:strict` | 3 | 2026-11-27, `4710839b` |

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
| linux-clang-O2 | 4 | 0.4%, 2.9%, 131.1% | `upws/call/nearest_add_1/change` |
| linux-clang-O3 | 4 | 0.3%, 0.9%, 12.0% | `upwa/call/mul_16/nested` |
| linux-gcc-O2 | 4 | 0.4%, 1.3%, 31.9% | `upwa/call/add_16/none` |
| linux-gcc-O3 | 4 | 0.2%, 1.3%, 136.5% | `upwa/call/add_64/nearest` |
| mac-appleclang-O2 | 3 | 2.2%, 3.1%, 4.3% | `upw/tp/det3_i1/conv` |
| mac-appleclang-O3 | 3 | 2.2%, 3.7%, 8.0% | `m2/tp/pair_add_1/kairn` |
| mac-gcc16-O2 | 3 | 0.2%, 1.4%, 3.2% | `upw/tp/det3_i1/native` |
| mac-gcc16-O3 | 3 | 9.9%, 10.6%, 13.2% | `upwa/call/add_4096/nearest` |
| windows-msvc-O2 | 3 | 0.1%, 1.5%, 6.5% | `upw/tp/interval_add_1/native_x16` |

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
| mac-appleclang-O3-checks | 76 | 6 | 57, spread 1.070 to 1.224; 13 kept alone, set aside with the other run of their pair |
| mac-appleclang-O3-main | 8 | 3 | 5, spread 1.054 to 1.213 |
| mac-gcc16-O2-checks | 6 | 6 | none |
| mac-gcc16-O2-main | 3 | 3 | none |
| mac-gcc16-O3-checks | 10 | 6 | 3, spread 1.070 to 1.219; 1 kept alone, set aside with the other run of their pair |
| mac-gcc16-O3-main | 11 | 3 | 8, spread 1.050 to 1.128 |
| windows-msvc-O2-msvc | 5 | 3 | 2, spread 1.070 to 1.073 |

<!-- END up_report attempts -->

<!-- BEGIN up_report runs -->

| Run | CPU, its sibling: busiest 5 s, mean | Spread within the run (median function) | Over the fastest run of its configuration: median, 90th percentile | Load average (1 min) at start, end |
|---|---|---|---|---|
| `main-linux-clang-O2-r1.json` | 22, 86: 0%, 0.1% | 1.006 | 1.001, 1.005 | 27.8, 28.5 |
| `main-linux-clang-O2-r2.json` | 22, 86: 0%, 0.1% | 1.005 | 1.000, 1.006 | 28.1, 28.8 |
| `main-linux-clang-O2-r3.json` | 21, 85: 0%, 0.0% | 1.004 | 1.000, 1.005 | 28.6, 29.4 |
| `main-linux-clang-O2-r4.json` | 20, 84: 0%, 0.1% | 1.005 | 1.004, 1.014 | 29.4, 29.7 |
| `main-linux-clang-O3-r1.json` | 28, 92: 0%, 0.2% | 1.006 | 1.000, 1.003 | 27.8, 28.5 |
| `main-linux-clang-O3-r2.json` | 28, 92: 0%, 0.2% | 1.006 | 1.003, 1.006 | 28.1, 28.8 |
| `main-linux-clang-O3-r3.json` | 28, 92: 0%, 0.1% | 1.005 | 1.001, 1.004 | 28.6, 29.4 |
| `main-linux-clang-O3-r4.json` | 30, 94: 0%, 0.0% | 1.004 | 1.001, 1.005 | 29.4, 29.7 |
| `main-linux-gcc-O2-r1.json` | 5, 69: 0%, 0.0% | 1.006 | 1.003, 1.007 | 27.8, 28.5 |
| `main-linux-gcc-O2-r2.json` | 4, 68: 0%, 0.0% | 1.005 | 1.000, 1.004 | 28.1, 28.8 |
| `main-linux-gcc-O2-r3.json` | 5, 69: 0%, 0.1% | 1.006 | 1.003, 1.007 | 28.6, 29.4 |
| `main-linux-gcc-O2-r4.json` | 4, 68: 0%, 0.0% | 1.005 | 1.000, 1.003 | 29.4, 29.7 |
| `main-linux-gcc-O3-r1.json` | 15, 79: 0%, 0.3% | 1.006 | 1.001, 1.005 | 27.8, 28.5 |
| `main-linux-gcc-O3-r2.json` | 12, 76: 0%, 0.2% | 1.005 | 1.001, 1.005 | 28.1, 28.8 |
| `main-linux-gcc-O3-r3.json` | 12, 76: 0%, 0.1% | 1.005 | 1.001, 1.008 | 28.6, 29.4 |
| `main-linux-gcc-O3-r4.json` | 12, 76: 0%, 0.1% | 1.004 | 1.001, 1.006 | 29.4, 29.7 |
| `main-mac-appleclang-O2-r1.json` | not pinned | 1.005 | 1.000, 1.000 | 3.9, 3.6 |
| `main-mac-appleclang-O2-r2.json` | not pinned | 1.003 | 1.022, 1.031 | 3.6, 4.2 |
| `main-mac-appleclang-O2-r3.json` | not pinned | 1.002 | 1.022, 1.028 | 4.2, 4.2 |
| `main-mac-appleclang-O3-r1.json` | not pinned | 1.032 | 1.018, 1.036 | 5.8, 6.4 |
| `main-mac-appleclang-O3-r2.json` | not pinned | 1.028 | 1.002, 1.020 | 4.9, 4.5 |
| `main-mac-appleclang-O3-r3.json` | not pinned | 1.032 | 1.002, 1.019 | 4.0, 3.8 |
| `main-mac-gcc16-O2-r1.json` | not pinned | 1.006 | 1.001, 1.004 | 2.0, 2.7 |
| `main-mac-gcc16-O2-r2.json` | not pinned | 1.005 | 1.001, 1.007 | 2.7, 3.9 |
| `main-mac-gcc16-O2-r3.json` | not pinned | 1.012 | 1.000, 1.006 | 3.9, 3.9 |
| `main-mac-gcc16-O3-r1.json` | not pinned | 1.025 | 1.043, 1.056 | 3.9, 4.6 |
| `main-mac-gcc16-O3-r2.json` | not pinned | 1.044 | 1.099, 1.106 | 6.5, 6.3 |
| `main-mac-gcc16-O3-r3.json` | not pinned | 1.045 | 1.000, 1.000 | 7.1, 8.2 |
| `msvc-windows-msvc-O2-r1.json` | not pinned | 1.006 | 1.000, 1.001 | -1.0, -1.0 |
| `msvc-windows-msvc-O2-r2.json` | not pinned | 1.011 | 1.000, 1.005 | -1.0, -1.0 |
| `msvc-windows-msvc-O2-r3.json` | not pinned | 1.011 | 1.000, 1.006 | -1.0, -1.0 |
| `checks-linux-clang-O2-c0-r1.json` | 22, 86: 0%, 0.0% | 1.005 | 1.003, 1.008 | 29.7, 29.6 |
| `checks-linux-clang-O2-c0-r2.json` | 23, 87: 0%, 0.0% | 1.007 | 1.003, 1.006 | 30.0, 30.3 |
| `checks-linux-clang-O2-c0-r3.json` | 22, 86: 0%, 0.0% | 1.006 | 1.000, 1.002 | 30.2, 30.1 |
| `checks-linux-clang-O2-c0-r4.json` | 21, 85: 0%, 0.2% | 1.010 | 1.001, 1.004 | 30.1, 30.5 |
| `checks-linux-clang-O2-c1-r1.json` | 22, 86: 0%, 0.0% | 1.004 | 1.001, 1.003 | 29.5, 30.0 |
| `checks-linux-clang-O2-c1-r2.json` | 23, 87: 0%, 0.2% | 1.004 | 1.001, 1.006 | 30.3, 30.2 |
| `checks-linux-clang-O2-c1-r3.json` | 22, 86: 0%, 0.0% | 1.004 | 1.001, 1.012 | 30.1, 30.1 |
| `checks-linux-clang-O2-c1-r4.json` | 21, 85: 0%, 0.2% | 1.003 | 1.009, 1.015 | 30.5, 30.8 |
| `checks-linux-clang-O3-c0-r1.json` | 30, 94: 0%, 0.2% | 1.005 | 1.001, 1.005 | 29.7, 29.5 |
| `checks-linux-clang-O3-c0-r2.json` | 28, 92: 0%, 0.0% | 1.007 | 1.000, 1.003 | 30.0, 30.3 |
| `checks-linux-clang-O3-c0-r3.json` | 30, 94: 0%, 0.0% | 1.006 | 1.001, 1.007 | 30.1, 30.1 |
| `checks-linux-clang-O3-c0-r4.json` | 28, 92: 2%, 1.8% | 1.009 | 1.005, 1.009 | 30.2, 30.5 |
| `checks-linux-clang-O3-c1-r1.json` | 30, 94: 0%, 0.0% | 1.004 | 1.001, 1.006 | 29.5, 30.0 |
| `checks-linux-clang-O3-c1-r2.json` | 28, 92: 0%, 0.0% | 1.003 | 1.000, 1.002 | 30.3, 30.2 |
| `checks-linux-clang-O3-c1-r3.json` | 30, 94: 0%, 0.0% | 1.005 | 1.001, 1.004 | 30.1, 30.1 |
| `checks-linux-clang-O3-c1-r4.json` | 28, 92: 0%, 0.0% | 1.008 | 1.004, 1.010 | 30.5, 30.8 |
| `checks-linux-gcc-O2-c0-r1.json` | 7, 71: 0%, 0.2% | 1.006 | 1.001, 1.005 | 29.7, 29.5 |
| `checks-linux-gcc-O2-c0-r2.json` | 4, 68: 0%, 0.2% | 1.006 | 1.000, 1.004 | 30.0, 30.3 |
| `checks-linux-gcc-O2-c0-r3.json` | 4, 68: 0%, 0.2% | 1.007 | 1.001, 1.005 | 30.2, 30.1 |
| `checks-linux-gcc-O2-c0-r4.json` | 4, 68: 1%, 0.6% | 1.009 | 1.003, 1.010 | 30.1, 30.5 |
| `checks-linux-gcc-O2-c1-r1.json` | 7, 71: 0%, 0.0% | 1.004 | 1.000, 1.000 | 29.5, 30.0 |
| `checks-linux-gcc-O2-c1-r2.json` | 4, 68: 0%, 0.2% | 1.004 | 1.003, 1.005 | 30.3, 30.2 |
| `checks-linux-gcc-O2-c1-r3.json` | 4, 68: 0%, 0.0% | 1.004 | 1.003, 1.005 | 30.1, 30.1 |
| `checks-linux-gcc-O2-c1-r4.json` | 4, 68: 0%, 0.2% | 1.002 | 1.008, 1.014 | 30.5, 30.8 |
| `checks-linux-gcc-O3-c0-r1.json` | 12, 76: 0%, 0.0% | 1.006 | 1.000, 1.002 | 29.7, 29.6 |
| `checks-linux-gcc-O3-c0-r2.json` | 12, 76: 0%, 0.2% | 1.006 | 1.000, 1.003 | 30.0, 30.3 |
| `checks-linux-gcc-O3-c0-r3.json` | 14, 78: 0%, 0.2% | 1.006 | 1.003, 1.022 | 30.2, 30.1 |
| `checks-linux-gcc-O3-c0-r4.json` | 14, 78: 0%, 0.4% | 1.010 | 1.004, 1.009 | 30.1, 30.5 |
| `checks-linux-gcc-O3-c1-r1.json` | 12, 76: 0%, 0.2% | 1.004 | 1.003, 1.015 | 29.5, 30.0 |
| `checks-linux-gcc-O3-c1-r2.json` | 12, 76: 0%, 0.2% | 1.004 | 1.000, 1.007 | 30.3, 30.2 |
| `checks-linux-gcc-O3-c1-r3.json` | 14, 78: 0%, 0.2% | 1.004 | 1.000, 1.003 | 30.1, 30.1 |
| `checks-linux-gcc-O3-c1-r4.json` | 14, 78: 0%, 0.4% | 1.004 | 1.008, 1.012 | 30.5, 30.8 |
| `checks-mac-appleclang-O2-c0-r1.json` | not pinned | 1.009 | 1.027, 1.042 | 4.2, 4.2 |
| `checks-mac-appleclang-O2-c0-r2.json` | not pinned | 1.037 | 1.013, 1.045 | 4.4, 4.6 |
| `checks-mac-appleclang-O2-c0-r3.json` | not pinned | 1.032 | 1.014, 1.046 | 5.0, 5.0 |
| `checks-mac-appleclang-O2-c1-r1.json` | not pinned | 1.044 | 1.002, 1.040 | 4.2, 4.4 |
| `checks-mac-appleclang-O2-c1-r2.json` | not pinned | 1.042 | 1.011, 1.041 | 4.6, 5.0 |
| `checks-mac-appleclang-O2-c1-r3.json` | not pinned | 1.018 | 1.028, 1.055 | 5.0, 5.2 |
| `checks-mac-appleclang-O3-c0-r1.json` | not pinned | 1.007 | 1.000, 1.005 | 3.2, 3.7 |
| `checks-mac-appleclang-O3-c0-r2.json` | not pinned | 1.002 | 1.000, 1.006 | 5.2, 5.1 |
| `checks-mac-appleclang-O3-c0-r3.json` | not pinned | 1.004 | 1.001, 1.004 | 3.9, 3.8 |
| `checks-mac-appleclang-O3-c1-r1.json` | not pinned | 1.004 | 1.003, 1.018 | 3.7, 3.6 |
| `checks-mac-appleclang-O3-c1-r2.json` | not pinned | 1.002 | 1.000, 1.011 | 5.1, 4.9 |
| `checks-mac-appleclang-O3-c1-r3.json` | not pinned | 1.003 | 1.000, 1.003 | 3.8, 3.7 |
| `checks-mac-gcc16-O2-c0-r1.json` | not pinned | 1.025 | 1.000, 1.004 | 3.9, 3.7 |
| `checks-mac-gcc16-O2-c0-r2.json` | not pinned | 1.002 | 1.023, 1.024 | 3.7, 3.6 |
| `checks-mac-gcc16-O2-c0-r3.json` | not pinned | 1.036 | 1.000, 1.022 | 3.7, 3.7 |
| `checks-mac-gcc16-O2-c1-r1.json` | not pinned | 1.024 | 1.000, 1.004 | 3.7, 3.7 |
| `checks-mac-gcc16-O2-c1-r2.json` | not pinned | 1.002 | 1.023, 1.036 | 3.6, 3.7 |
| `checks-mac-gcc16-O2-c1-r3.json` | not pinned | 1.004 | 1.035, 1.037 | 3.7, 3.9 |
| `checks-mac-gcc16-O3-c0-r1.json` | not pinned | 1.006 | 1.021, 1.023 | 5.8, 5.4 |
| `checks-mac-gcc16-O3-c0-r2.json` | not pinned | 1.004 | 1.000, 1.005 | 5.2, 4.9 |
| `checks-mac-gcc16-O3-c0-r3.json` | not pinned | 1.004 | 1.000, 1.004 | 4.0, 3.9 |
| `checks-mac-gcc16-O3-c1-r1.json` | not pinned | 1.005 | 1.000, 1.008 | 5.4, 5.2 |
| `checks-mac-gcc16-O3-c1-r2.json` | not pinned | 1.003 | 1.001, 1.010 | 4.9, 4.5 |
| `checks-mac-gcc16-O3-c1-r3.json` | not pinned | 1.003 | 1.001, 1.008 | 3.9, 3.7 |

<!-- END up_report runs -->
