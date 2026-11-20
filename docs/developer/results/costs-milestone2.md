# Compile times and other costs, Milestone 2

What the settings of `KAIRN_ENCLOSURE_CODE` cost and save
([Milestone 2 statements](../design/milestone2.md#inlining-and-compile-time); [Getting
started](../../getting-started/index.md#compile-time-and-the-operations-of-ball)): the operations of
`Ball` that round forced inline into their callers (the default), outlined as functions of their
own, or external, defined in one file of the program. The library is that of commit `009fb78`; the
tools are `bench/enclosure_costs.py` and the benchmark harness of `bench/` built in each setting
(documented in its [README](https://github.com/danielepanozzo/kairn/tree/main/bench)), and the
measurements, as JSON, are in
[`results/milestone2/costs/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/costs).
All were made on 2026-11-20 on the Mac of [How it was measured](#how-it-was-measured).

In short:

- **Compile time.** A function with 1 000 to 10 000 ball operations compiles 3.5 to 7.1 times
  faster with Apple clang 21 when they are outlined or external, in a third to a half of the
  memory; with GCC 16, 1.5 to 2.3 times faster outlined and 1.7 to 4.3 times external, in a fourth
  to a fifth of the memory. Apple clang then compiles the function about as fast as the same calls
  of functions declared only, without Kairn; GCC takes longer, and at 10 000 operations 43% (at
  `-O2`) to 76% (at `-O3`) of what the external unit takes is what the same calls without Kairn
  take, GCC's own handling of one function with thousands of calls.
- **Run time.** Each operation becomes a call. In a loop of independent operations of two limbs,
  `X + Y` and `X * Y` take 1.05 to 1.3 times as long as inline, the scaling and the operations of
  one limb 1.3 to 1.9 times; in a chain of dependent operations each operation takes 2.4 to 6.2
  nanoseconds more, which makes a chain 1.4 to 2.5 times as long. Outlined and external cost the
  same within 2% in a chain; in a loop external is up to 20% slower than outlined with Apple
  clang, within 3% with GCC.
- So the default stays inline, and a program sets the other settings where compile time or memory
  is what it runs out of: for files with many ball operations in a few large functions, external
  with GCC, either with Apple clang.

## The answers

### 1. Compile time

One translation unit with N operations of `Ball<double, 2>` in straight-line code, in one function:
`+`, `-`, `*` and the scaling by a `double` in turn, each on two of the eight values computed last,
each result stored, so that none is dead (`enclosure_costs.py source N`); with `NDEBUG`, so
`KAIRN_CHECKS` is 0. The median wall time of three compilations (one for N = 10 000), and the peak
memory of the compiler; nothing is linked.

"The calls alone" is the same unit without Kairn: `B` a structure of three `double`s and the four
operations functions declared only (`--settings calls`), what the program's own straight-line code
of N calls costs the compiler, whatever the library. Seconds, and the peak memory in MB:

| Apple clang 21 | inline | outlined | external | the calls alone |
|---|---:|---:|---:|---:|
| 100, `-O2` | 0.15, 64 | 0.10, 55 | 0.08, 52 | 0.04, 38 |
| 100, `-O3` | 0.15, 64 | 0.10, 55 | 0.08, 52 | 0.05, 38 |
| 1 000, `-O2` | 1.09, 181 | 0.30, 83 | 0.28, 81 | 0.26, 67 |
| 1 000, `-O3` | 1.10, 182 | 0.31, 84 | 0.29, 81 | 0.27, 67 |
| 10 000, `-O2` | 33.1, 1 309 | 4.83, 394 | 4.85, 391 | 5.14, 362 |
| 10 000, `-O3` | 35.0, 1 312 | 5.01, 395 | 4.95, 391 | 5.30, 362 |

| GCC 16 | inline | outlined | external | the calls alone |
|---|---:|---:|---:|---:|
| 100, `-O2` | 0.55, 112 | 0.27, 69 | 0.19, 65 | 0.12, 37 |
| 100, `-O3` | 0.59, 114 | 0.31, 69 | 0.20, 65 | 0.13, 37 |
| 1 000, `-O2` | 4.83, 708 | 2.08, 170 | 1.17, 164 | 0.80, 117 |
| 1 000, `-O3` | 8.56, 720 | 4.76, 171 | 1.97, 167 | 1.37, 119 |
| 10 000, `-O2` | 74.2, 6 039 | 48.8, 1 316 | 44.5, 1 287 | 19.2, 1 236 |
| 10 000, `-O3` | 212, 6 114 | 132, 1 277 | 103, 1 252 | 78.2, 1 015 |

- **With Apple clang, taking the operations out of line is what a large function needs.** At
  10 000 operations the unit compiles 6.8 to 7.1 times faster (4.8 to 5.0 seconds instead of 33 to
  35) in a third of the memory (391 to 395 MB instead of 1.31 GB); at 1 000, 3.5 to 3.8 times
  faster; at 100, 1.6 to 1.8 times. Outlined and external are within 7% of each other at 1 000 and
  10 000 operations (at 100 the external unit takes 0.08 seconds and the outlined one 0.10): once
  the operations are calls, compiling their bodies once in the file costs almost nothing, and both
  are at the floor of the calls alone (at 10 000 even 5 to 7% below it). The object is 4.8 times
  smaller at 10 000 (0.57 MB instead of 2.77 MB).
- **With GCC 16 it helps less, and external helps more than outlined.** At 1 000 operations the
  outlined unit compiles 1.8 to 2.3 times faster and the external one 4.1 to 4.3 times; at
  10 000, 1.5 to 1.6 times (outlined) and 1.7 to 2.1 times (external), in 4.6 to 4.9 times less
  memory (1.25 to 1.32 GB instead of 6.0 to 6.1). The outlined unit, in which GCC sees the bodies
  it is not to inline, costs more than the external one (at `-O3`, 29 seconds more at 10 000).
  Much of what is left is GCC's handling of one function with 10 000 calls: the calls alone take
  19 seconds at `-O2` (43% of the external unit) and 78 at `-O3` (76%). GCC's own report (`-ftime-report`, at
  `-O2`) puts 23 of the external unit's 48 seconds in "expand vars", the placing of the function's
  ten thousand objects in stack slots, and 9.9 in points-to analysis, against 5.9 and 7.2 of 67 for
  the inline unit, whose time is spread over the optimizer's passes; the front end, which resolves
  the overloads of every operator, takes 5.1 and 4.5 seconds. Passing the balls by value instead of
  by reference, tried on a copy of the headers, changed nothing measurable (46 seconds at `-O2`).
- **The file that defines the operations** for the external setting, `bench/definitions.cpp`, the
  16 operations for `float` and `double`, one and two limbs, compiles in 0.09 seconds with Apple
  clang and 0.2 with GCC 16, once per program.

### 2. Run time

The benchmark harness of Milestone 1 ([Benchmarks, Milestone 1](bench-milestone1.md)), built once
per setting, every translation unit with it: the public operators of `Ball<double, 2>` and
`Ball<double, 1>` in a loop of independent operations over arrays in L1, timed per operation, and
in dependent chains, timed per step (a running sum, a running product of factors near 1 or by a
`double`, a Horner evaluation, one product and one sum per step). The minimum time in
nanoseconds, of two runs of 31 samples each; "kairn" is the generated core called on the limbs
directly, which no setting changes: a control of the machine.

| Apple clang 21, ns (over inline) | `-O2` inline | outlined | external | `-O3` inline | outlined | external |
|---|---:|---:|---:|---:|---:|---:|
| loop: `X + Y`, two limbs | 1.99 | 2.10 (1.05) | 2.10 (1.06) | 1.95 | 2.06 (1.06) | 2.14 (1.10) |
| loop: `X * Y`, two limbs | 1.54 | 1.70 (1.11) | 1.82 (1.18) | 1.50 | 1.67 (1.11) | 1.79 (1.19) |
| loop: `X * a`, two limbs | 1.03 | 1.43 (1.39) | 1.64 (1.59) | 1.00 | 1.41 (1.41) | 1.61 (1.61) |
| loop: `X + Y`, one limb | 0.79 | 1.17 (1.48) | 1.37 (1.74) | 0.77 | 1.15 (1.49) | 1.34 (1.74) |
| loop: `X * Y`, one limb | 1.02 | 1.37 (1.34) | 1.64 (1.60) | 0.98 | 1.34 (1.37) | 1.61 (1.64) |
| chain: `S + X`, two limbs | 8.17 | 12.28 (1.50) | 12.09 (1.48) | 7.84 | 12.05 (1.54) | 12.08 (1.54) |
| chain: `P * X`, two limbs | 6.24 | 9.33 (1.50) | 9.39 (1.51) | 5.98 | 9.21 (1.54) | 9.21 (1.54) |
| chain: `P * a`, two limbs | 4.03 | 8.38 (2.08) | 8.36 (2.07) | 3.87 | 8.22 (2.13) | 8.20 (2.12) |
| chain: `P * H + C`, two limbs | 14.18 | 21.56 (1.52) | 21.80 (1.54) | 13.59 | 21.48 (1.58) | 21.38 (1.57) |
| chain: `S + X`, one limb | 2.90 | 6.47 (2.23) | 6.48 (2.23) | 2.79 | 6.33 (2.27) | 6.35 (2.28) |
| chain: `P * X`, one limb | 5.24 | 8.44 (1.61) | 8.45 (1.61) | 5.03 | 8.28 (1.65) | 8.29 (1.65) |
| chain: `P * H + C`, one limb | 8.36 | 14.90 (1.78) | 15.19 (1.82) | 8.01 | 14.90 (1.86) | 14.90 (1.86) |
| control: the core of `X + Y`, two limbs, a loop | 1.17 | 1.17 (0.99) | 1.17 (1.00) | 1.15 | 1.15 (1.00) | 1.15 (1.00) |
| control: the core of `S + X`, two limbs, a chain | 8.02 | 7.84 (0.98) | 7.69 (0.96) | 7.69 | 7.69 (1.00) | 7.69 (1.00) |

| GCC 16, ns (over inline) | `-O2` inline | outlined | external | `-O3` inline | outlined | external |
|---|---:|---:|---:|---:|---:|---:|
| loop: `X + Y`, two limbs | 2.02 | 2.21 (1.09) | 2.26 (1.12) | 2.08 | 2.36 (1.14) | 2.36 (1.14) |
| loop: `X * Y`, two limbs | 1.53 | 1.92 (1.25) | 1.95 (1.28) | 1.56 | 2.00 (1.28) | 2.00 (1.28) |
| loop: `X * a`, two limbs | 1.08 | 1.61 (1.49) | 1.64 (1.52) | 1.10 | 1.64 (1.49) | 1.64 (1.49) |
| loop: `X + Y`, one limb | 0.72 | 1.34 (1.88) | 1.37 (1.91) | 0.73 | 1.37 (1.88) | 1.34 (1.84) |
| loop: `X * Y`, one limb | 0.95 | 1.61 (1.70) | 1.64 (1.73) | 0.90 | 1.64 (1.82) | 1.62 (1.80) |
| chain: `S + X`, two limbs | 7.61 | 13.61 (1.79) | 13.88 (1.82) | 7.83 | 13.98 (1.79) | 13.98 (1.79) |
| chain: `P * X`, two limbs | 5.91 | 10.76 (1.82) | 10.76 (1.82) | 6.23 | 11.00 (1.77) | 11.00 (1.77) |
| chain: `P * a`, two limbs | 3.90 | 9.80 (2.51) | 9.82 (2.52) | 4.03 | 10.00 (2.48) | 10.00 (2.48) |
| chain: `P * H + C`, two limbs | 13.98 | 24.56 (1.76) | 24.72 (1.77) | 14.24 | 25.25 (1.77) | 25.25 (1.77) |
| chain: `S + X`, one limb | 2.75 | 5.99 (2.18) | 6.10 (2.22) | 2.80 | 6.12 (2.18) | 6.12 (2.18) |
| chain: `P * X`, one limb | 5.49 | 7.89 (1.44) | 8.00 (1.46) | 5.10 | 8.05 (1.58) | 8.05 (1.58) |
| chain: `P * H + C`, one limb | 7.98 | 14.25 (1.79) | 14.25 (1.79) | 8.17 | 14.60 (1.79) | 14.59 (1.79) |
| control: the core of `X + Y`, two limbs, a loop | 1.15 | 1.15 (1.00) | 1.17 (1.02) | 1.26 | 1.23 (0.98) | 1.23 (0.98) |
| control: the core of `S + X`, two limbs, a chain | 7.75 | 7.76 (1.00) | 7.79 (1.00) | 7.86 | 7.85 (1.00) | 7.85 (1.00) |

- **Outlining costs a call per operation, and the numbers say so.** In a chain, where each step
  waits for the one before, each operation takes 2.4 to 6.2 nanoseconds more than inline: with
  Apple clang 3.1 to 4.4 (a two-limb sum 4.1 to 4.2, a product 3.1 to 3.2, a scaling 4.3 to 4.4), with
  GCC 2.4 to 6.2 (a sum 6.0 to 6.2, a product 4.8 to 4.9, a scaling 5.9 to 6.0); a Horner step,
  two operations, 7.4 to 7.9 and 10.6 to 11.0. So a chain of two-limb sums or products takes 1.5
  times as long with Apple clang and 1.8 times with GCC, and the short operations more: a chain of
  scalings 2.1 and 2.5 times, a chain of one-limb sums 2.2 to 2.3 times.
- **In a loop of independent operations the processor hides most of it.** A two-limb `X + Y`
  takes 1.05 to 1.14 times as long as inline and `X * Y` 1.11 to 1.28 times; the scaling, whose
  body is short, 1.4 to 1.6 times, and the operations of one limb 1.3 to 1.9 times.
- **Outlined and external cost the same in a chain**, within 2%. In a loop, with Apple clang,
  external is up to 20% slower than outlined (a one-limb product: 1.64 ns against 1.37 at `-O2`);
  with GCC within 3%. The compiler can read the body of an outlined operation and knows nothing of
  an external one; that the difference comes from what it learns there was not examined.
- **The control**, the generated core called directly, which no setting changes, took the same
  time in every program to within 5%. The two runs of a function were within 2% of each other for
  82% of the 1 620 functions and configurations timed (the median 0.2%), and within 11.3% at worst
  (`api/tp/ball_neg_2/kairn`, a loop of 0.4 ns per operation).

## How it was measured

- **Machine**: macOS 26.6 on arm64, an Apple M3 Max (12 performance and 4 efficiency cores,
  128 GB), shared with other jobs: the 1-minute load average was 4 to 6 during the compilations and
  5 to 10 during the benchmark runs. macOS has no affinity: compilations were not pinned, one at a
  time, and the benchmarks ran in the user-interactive class, which runs on performance cores.
- **Compilers**: Apple clang 21.0.0 (clang-2100.4.1.1) as `c++`, and GCC 16.2.0 of Homebrew as
  `g++-16`.
- **Compile times**: `python3 bench/enclosure_costs.py compile --cxx CXX --reps 3` (and
  `--settings calls` for the calls alone), which compiles each unit with `-std=c++20 -I include
  -DKAIRN_ENCLOSURE_CODE=...` and `-O2 -DNDEBUG` or `-O3 -DNDEBUG`, `-c`, nothing linked (AArch64
  needs no FMA option), three times in rounds over all units and levels, once for the units of
  10 000 operations; the wall time from the start of the compiler to its exit, the median of the
  three, and the largest resident set of the compiler and the processes it waited for
  (`os.wait4`), as `compile_time.py` measures it. The JSON files have every compilation, the
  processor times and the sizes of the objects. The time reports: the 10 000-operation unit with
  `-ftime-report` at `-O2`, once.
- **Run times**: `kairn-bench-LEVEL`, `kairn-bench-outlined-LEVEL` and `kairn-bench-external-LEVEL`
  (`bench/CMakeLists.txt`, a `Release` build with `KAIRN_BUILD_BENCHMARKS=ON`), `--filter ball
  --reps 31`, two runs of each configuration, one after the other; samples of about 4 ms, in rounds
  over all functions, 256 operations per call on arrays in L1, inputs from a fixed seed, as on
  [the benchmark page](bench-milestone1.md#how-it-was-measured); contraction off. A number is the
  minimum over the two runs of the minimum time per operation (a loop) or per step (a chain).
  Before it times anything, each program checks every function against the generated kernels, bit
  for bit: 245 functions, none failed, in each of the 12 programs.
- **Not measured**: Linux, Windows, MSVC, clang-cl; compile times of a client's whole project, or
  of a debug build; the operations of `Ball` of `float` limbs at compile time (their run times are
  in the JSON files, `apif/...`).
