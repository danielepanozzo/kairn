# Compile times and other costs, Milestone 1

Four measurements that Milestone 1 owes beside [the benchmarks](bench-milestone1.md): the compile
times that the [brief](../design/brief.md#delivery-header-only) asks to report "for the largest
networks" and that [Library](../design/phase0/library.md#inlining-and-compile-time) promises per
milestone; the cost of the environment check, of which
[Environment](../design/phase0/environment.md#the-dynamic-environment) says "a few cycles; it will
be reported in Milestone 1"; the `/GS` stack cookie that MSVC put in functions holding
`Expansion<double, 1>`, an open issue in the [table of compiler
hazards](../design/phase0/environment.md#compiler-hazards-found-on-the-way); and the time of the
quick tier on GitHub's hosted runners, which the brief wants
"[under ~2 minutes per platform](../design/brief.md#tiers)". The library is that of commit
`040922c` (its headers last changed in `24f751a`); the tools are in
[`bench/`](https://github.com/danielepanozzo/kairn/tree/main/bench) (`compile_time.py`,
`costs.cpp`, `gs_probe.py`, `ci_times.py`, documented in its README), and the measurements, as
JSON, in
[`results/milestone1/costs/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone1/costs).
All were made on 2026-11-19. "M3", "Zen 2" and "i5" are the three machines of the benchmark page
([How it was measured](#how-it-was-measured)).

## The answers

### 1. Compile times

The wall time of compiling one translation unit, the minimum over seven compilations, at `-O2`
(MSVC `/O2`) with `NDEBUG`, and in a debug build (`-O0 -g`, MSVC `/Od /Z7 /RTC1`, without `NDEBUG`,
so `KAIRN_CHECKS` is 1). Every compilation has `-std=c++20` and the FMA option a client gets from
`kairn::fma`; nothing is linked.

| Seconds, `-O2` (debug build) | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| an empty unit | 0.018 | 0.057 | 0.013 | 0.036 | 0.042 |
| `<iostream>` alone | 0.312 | 0.215 | 0.317 | 0.456 | 0.417 |
| `kairn/kairn.hpp`, nothing used | 0.057 (0.057) | 0.117 (0.134) | 0.142 (0.145) | 0.233 (0.232) | 0.186 (0.187) |
| every operation of `Expansion<double, 2>` and `Ball<double, 2>`, 126 functions | 0.138 (0.182) | 0.393 (0.656) | 0.678 (0.765) | 0.545 (0.660) | 1.24 (0.257) |
| every operation of the eight types, 389 functions | 0.272 (0.395) | 0.900 (1.58) | 1.68 (1.89) | 1.12 (1.44) | 3.06 (0.359) |
| one call of `kairn::self_test()` | 0.211 (0.147) | 0.752 (0.512) | 1.08 (0.544) | 0.772 (0.454) | 1.07 (0.251) |
| `gen/scalar.hpp` alone, all 63 kernels for both limb types | 0.126 (0.115) | 0.324 (0.349) | 0.526 (0.386) | 0.400 (0.307) | 0.892 (0.222) |
| `gen/neon.hpp` or `gen/avx2.hpp` alone, the same | 0.189 (0.221) | 0.432 (0.620) | 0.932 (0.873) | 0.878 (0.993) | 0.767 (0.249) |
| `gen/tests/runner.cpp` (quick tier) | 0.507 (0.432) | 0.740 (0.628) | 1.21 (0.857) | 1.08 (0.856) | 1.75 (0.605) |
| `gen/tests/packed_runner.cpp` (quick tier) | 0.636 (0.565) | 1.06 (0.952) | 1.88 (1.42) | 1.73 (1.60) | 1.84 (0.655) |

- **Including `kairn/kairn.hpp` costs 0.06 to 0.23 s and 39 to 99 MB**, the same at every level,
  and emits no code. That is less than `<iostream>` alone with every compiler. Of it, the standard
  and intrinsics headers that Kairn includes take 0.036 to 0.142 s
  ([baselines](#baselines)): Kairn's own nine thousand lines add 0.02 s (Apple clang) to 0.10 s
  (Clang 18 on Zen 2). Kairn does not include `<cmath>`, and `<cmath>` with those headers costs
  more than `kairn.hpp` with GCC and Clang 18.
- **Using Kairn costs what the optimizer does with it.** Every public operation of
  `Expansion<double, 2>` and `Ball<double, 2>`, each in a function of its own, takes 0.14 s to
  compile with Apple clang and 1.24 s with MSVC at `-O2`; of all eight types, 0.27 to 3.06 s; that
  is 0.6 ms (Apple clang), 4 ms (GCC 13) and 8 ms (MSVC) per function using one operation, beyond
  the include. The back end has 51 to 85% of the time of the first unit and 69 to 93% of the
  second ([phases](#where-the-time-goes)). The peak memory is 60 to 127 MB at `-O2`, 44 to 219 MB in a
  debug build.
- **MSVC at `/O2` is the slowest** (3.06 s for the eight types, against 1.68 s for GCC 13 and 0.27 s
  for Apple clang), and at `/Od` second only to Apple clang (0.33 s against 0.20 s; the others 0.80
  to 1.05 s). Its code generator is multithreaded: these compilations were pinned to one logical
  processor, as a parallel build would leave them; alone and unpinned, the same unit took 1.13 s
  ([MSVC's threads](#msvcs-threads)).
- **`-O3` costs what `-O2` costs**, within 4% for every unit of Kairn; the runners take up to 11%
  (GCC 16) and 20% (GCC 13) more. A debug build, with debug information and the checks of
  `KAIRN_CHECKS`, takes up to 2.0 times as long as `-O0` with GCC and Clang for the units that use
  Kairn, 1.1 times with MSVC.
- **The largest networks today** are the full Ball kernels and the full kernels of the two-limb
  sum and difference: `ball_sub_2_full` (38 operations, 134 lines of `scalar.hpp` for both limb
  types), `ball_add_2_full` (36), `sub_2_2_full` (30), `ball_mul_2_full` (29) and `add_2_2_full`
  (28). Each, called once per limb type, adds 8 to 36 ms to a unit at `-O2` (scalar), against 1 to
  8 ms for the smallest kernel; the five together are 13 to 15% of what the 63 kernels add one at
  a time, 17 to 19% once the cost every kernel has is taken out, for 22% of the operations
  ([per kernel](#the-largest-networks)). No kernel dominates: the time grows with the number of
  operations a unit uses.
- **The packed header costs more to read than its kernels to compile with GCC 13 and Clang 18**:
  with no kernel used, a unit with `avx2.hpp` takes 0.57 s, of which `<immintrin.h>` alone is
  0.51 s with GCC 13; the 63 kernels for both types add 0.32 to 0.37 s.

### 2. The cost of the environment check

`kairn::environment_ok()` reads one control register (`stmxcsr` on x86-64, `mrs` of FPCR on
AArch64) and tests three fields. With `KAIRN_CHECKS` at 1 every scalar operation calls it and
checks that its operands are canonical. Times per call or per operation, at `-O2` (the minimum of
31 samples, three runs):

| | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `environment_ok()`, ns | 0.36 to 0.39 | 0.36 to 0.39 | 6.45 to 6.46 | 6.24 | 1.10 |
| the same, in cycles at most (at the highest clock) | 1.5 to 1.6 | 1.5 to 1.6 | 21.6 | 20.9 | 5.1 |
| `x + y` with checks over without, chain | 1.01 | 1.00 | 1.02 | 1.03 | 1.01 |
| `x + y`, loop | 1.48 to 1.49 | 1.41 to 1.44 | 1.94 | 2.99 to 3.00 | 1.26 to 1.27 |
| `x * y`, chain | 1.06 to 1.14 | 1.02 to 1.09 | 1.00 to 1.02 | 1.03 to 1.04 | 1.03 to 1.05 |
| `x * y`, loop | 2.61 to 2.62 | 2.41 to 2.42 | 3.65 to 3.66 | 4.14 to 4.15 | 2.16 |
| one limb, `x + y`, chain | 2.07 to 2.08 | 1.62 to 1.68 | 7.98 | 7.99 to 8.00 | 2.98 to 2.99 |
| one limb, `x + y`, loop | 5.72 to 5.78 | 5.22 to 5.31 | 34.3 to 34.8 | 33.7 to 33.8 | 7.5 to 12.7 |

- **"A few cycles" holds on the M3 (1.5 to 1.6 cycles) and the i5 (5), not on Zen 2: 6.2 to 6.5 ns,
  about 21 cycles**, for a loop that is nothing but `stmxcsr`, a test and an addition.
- **In a chain the checks cost at most 14%** for the two-limb operators, on every machine: the
  read and the tests are off the critical path. **In a loop they cost 1.26 to 3.00 times for
  `x + y` and 2.16 to 4.15 times for `x * y`**, most on Zen 2, where the read alone (6.2 ns) is
  longer than a two-limb product (2.0 to 2.3 ns).
- **A one-limb operation is one instruction, and the check is many**: with the checks a one-limb
  sum takes 1.6 to 8.0 times as long in a chain and 5.2 to 34.8 times in a loop (6.3 to 6.4 ns per
  addition on Zen 2, against 0.19).
- **Unoptimized** (`-O0`, `/Od`, a debug build as it is), the checks add up to 37% to a two-limb
  operation in a chain and up to 63% in a loop with GCC and Clang, at most 9% with MSVC ([the
  tables](#kairn_checks-in-detail)).

### 3. MSVC and the `/GS` stack cookie

With the headers of today and MSVC 19.52 at `/O2 /arch:AVX2`, from the disassembly:

- **Functions that hold an `Expansion<double, 1>` get the cookie**: 10 of the 11 shapes tried
  (one operation returned by value or through a pointer, loops, chains, a dot product, `axpy`);
  only a Horner evaluation over a `std::array` does not. **No function holding a `double`, an
  `Expansion<double, 2>`, a `Ball<double, 1>` or a `Ball<double, 2>` gets it**, nor any of the 186
  functions of `kairn-bench`'s `api.cpp` ([the shapes](#which-functions-get-it)).
- **What it costs.** The cookie is a load, an exclusive or and a store at the entry, and a load, an
  exclusive or and a call of `__security_check_cookie` at the exit, in a frame of 24 bytes: a
  function of 4 instructions (`*z = x + y`) becomes one of 12. Called once per element, that
  function takes 1.77 ns with `/GS` and 0.90 ns with `/GS-` (1.97 times; with `KAIRN_CHECKS` 1.25
  times, at `/Od` 1.26 to 1.28 times). Over a loop or a chain of 256 operations it is paid once
  per call: a chain of one-limb sums takes 1.03 to 1.04 times as long. The two-limb operators are
  unaffected (1.00 to 1.02), and so is `kairn-bench`: over its 93 functions of `double` limbs,
  `/GS` over `/GS-` is 0.98 to 1.07, median 1.000 ([cost](#what-it-costs)).
- **The cause is an array of one element passed by value.** `Expansion<T, 1>` holds `T limb[1]`,
  and its operators, and the functions of `detail` they call, take it by value. Changing one thing
  at a time ([what triggers it](#what-triggers-it)): with the operators taking `const&`, or with a
  scalar member instead of the array, no function gets the cookie; whether the type is a class
  template, a partial specialization or a plain structure, whether the operators are hidden friends
  or free templates, `noexcept`, constexpr constructors and the default member initializer change
  nothing. Phase 0 found the cookie with the class template and not with the plain structure;
  recompiled with today's MSVC, its plain structure gets it too (`dot_k1`, 40 instructions against
  30 for `double`). `Expansion<double, 2>`, an array of two passed by value in `detail`, does not
  trigger it.
- **The fix is evident and was not applied**: pass `Expansion<T, 1>` by `const&` in its operators
  and in the functions of `expansion.hpp` that take it (81 parameters). Applied to a copy of the
  headers, it removes the cookie from every function of the probe, and the code is that of
  `/GS-` (4 instructions for `*z = x + y`), except the dot product (47 instructions against 40).
  Whether GCC and Clang still compile `Expansion<double, 1>` exactly as `double` with it is for
  `api.k1.zero_cost` to say; it was not run.

### 4. The quick tier on the hosted runners

The last twelve completed runs of the workflow "Build and test" on `main`, of which the last five
(`bd0bee2` to `040922c`) have the quick tier as it is now (the earlier ones ran what is now the
full tier too, 8 to 33 minutes); seconds, minimum, median and maximum over those five (four for
arm64, whose jobs start at `4179d64`), every job a success:

| Job | ctest step | whole job | Configure, Build |
|---|---|---|---|
| Linux x86-64, GCC | 73 / 74 / 75 | 93 / 103 / 110 | 8, 10 |
| Linux x86-64, Clang | 64 / 74 / 126 | 86 / 108 / 155 | 13, 8 |
| Linux arm64, GCC | 55 / 55 / 58 | 72 / 74 / 75 | 4, 9 |
| Linux arm64, Clang | 54 / 56 / 59 | 69 / 74 / 87 | 6, 8 |
| macOS arm64, Apple clang | 69 / 89 / 119 | 87 / 109 / 155 | 4, 8 |
| Windows x64, MSVC | 128 / 168 / 198 | 183 / 231 / 265 | 16, 27 |
| Windows x64, clang-cl | 137 / 174 / 202 | 190 / 266 / 268 | 26, 17 |

- **Linux and macOS are under two minutes, ctest step and whole job, on the median run; Windows is
  not**: its ctest step takes 128 to 202 s, its job 183 to 268 s, of which about 60 s is outside
  ctest (the developer environment, Configure, Build). The slowest Linux x86-64 Clang run (126 s)
  was one job on a runner image of its own, every test about 1.7 times slower.
- **Four tests set the time**, the same on every platform, 37 to 43% of the summed test time:
  `kairn-oracle.selftest` (34 to 105 s), `crosscheck.guards` (23 to 58 s), `kairn-gen.test` (14
  to 36 s) and `docs.reference.test` (8 to 49 s). The 126 `crosscheck.compiled.*` tests are 34 to
  39% of the sum and the 97 `api.oracle.*` tests 16 to 18%, but none of them takes more than 3.6 s.
  ctest runs four at a time, so the wall time is about a quarter of the sum, bounded below by the
  longest test ([the tests](#the-tests-that-take-the-time)).
- **What moving them would save**, replaying each median run's tests on four slots without them:
  without the three Python tests of the tools and `brute.driver.test`, which compile nothing with
  the build's compiler, the Windows ctest step goes from 167 to 128 s (MSVC) and from 172 to 133 s
  (clang-cl), Linux x86-64 from 73 to 55 s; without `kairn-oracle.selftest` as well, to 102 and
  106 s on Windows, 40 s on Linux x86-64, 29 to 30 s on arm64 and 51 s on macOS. Only the second
  brings the Windows ctest step under two minutes; its whole job stays at about 160 to 170 s.
  Halving the cases of the cross-checks would save less than half: about 0.3 s of each Linux
  cross-check is a fixed cost, 40 to 51% of `crosscheck.compiled.*` and 63 to 71% of
  `api.oracle.*`.

## Compile times in detail

### What was compiled

| Unit | What it is |
|---|---|
| `empty` | an empty translation unit |
| `kairn_std` | the standard headers that `kairn.hpp` includes, and its intrinsics header (`<xmmintrin.h>` with GCC and Clang on x86-64, `<immintrin.h>` with MSVC) |
| `std_headers` | the same and `<cmath>` |
| `iostream` | `<iostream>` |
| `include` | `kairn/kairn.hpp`, nothing used |
| `use_e2` | every public operation of `Expansion<double, 2>` and `Ball<double, 2>`, with every order of operands the [Reference](../../reference/index.md) lists, each in a non-inlined function of its own: 126 functions |
| `use_all` | the same for `Expansion` and `Ball` with `float` and `double` limbs, one and two limbs: 389 functions |
| `self_test` | one call of `kairn::self_test()`, which runs every kernel for both limb types |
| `kernels_scalar` | `kairn/gen/scalar.hpp` alone: every kernel of `gen/tests/runner_kernels.inc` (63) called for `double` and `float`, each call in a function of its own, in a table the program could call |
| `kernels_packed` | the same with `gen/neon.hpp` (M3) or `gen/avx2.hpp` (`-mavx2 -mfma`) |
| `runner`, `packed_runner` | `gen/tests/runner.cpp` and `gen/tests/packed_runner.cpp`, the same tables inside the runners of the quick tier, which add `<iostream>`, `<string>`, `<vector>` and the line protocol |

`kernels_scalar` and `kernels_packed` are the largest units of generated code that exist today:
the runners compile the same kernels, `self_test()` calls the same ones, and nothing instantiates
more of them.

### Baselines

At `-O2`, seconds and peak MB. On the M3 and for GCC 13 from a separate run of these five units
(the first runs had no `kairn_std`); Clang 18 and MSVC from their main run.

| Unit | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `empty` | 0.018; 24 | 0.057; 20 | 0.013; 15 | 0.036; 82 | 0.042; 20 |
| `kairn_std` | 0.036; 36 | 0.088; 34 | 0.083; 30 | 0.132; 95 | 0.142; 34 |
| `std_headers` | 0.044; 38 | 0.131; 54 | 0.195; 49 | 0.290; 106 | 0.154; 36 |
| `iostream` | 0.314; 105 | 0.213; 95 | 0.320; 69 | 0.456; 116 | 0.417; 83 |
| `include` | 0.056; 41 | 0.117; 48 | 0.144; 39 | 0.233; 99 | 0.186; 41 |

### By level

**-O0, with NDEBUG (MSVC /Od); seconds**

| Unit | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `include` | 0.057 | 0.118 | 0.135 | 0.230 | 0.185 |
| `use_e2` | 0.109 | 0.393 | 0.456 | 0.424 | 0.242 |
| `use_all` | 0.197 | 0.883 | 1.05 | 0.796 | 0.329 |
| `self_test` | 0.106 | 0.459 | 0.483 | 0.347 | 0.237 |
| `kernels_scalar` | 0.086 | 0.311 | 0.344 | 0.226 | 0.214 |
| `kernels_packed` | 0.178 | 0.559 | 0.800 | 0.903 | 0.238 |
| `runner` | 0.390 | 0.554 | 0.766 | 0.746 | 0.583 |
| `packed_runner` | 0.499 | 0.847 | 1.29 | 1.47 | 0.633 |

**-O2, with NDEBUG (MSVC /O2); seconds**

| Unit | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `include` | 0.057 | 0.117 | 0.142 | 0.233 | 0.186 |
| `use_e2` | 0.138 | 0.393 | 0.678 | 0.545 | 1.24 |
| `use_all` | 0.272 | 0.900 | 1.68 | 1.12 | 3.06 |
| `self_test` | 0.211 | 0.752 | 1.08 | 0.772 | 1.07 |
| `kernels_scalar` | 0.126 | 0.324 | 0.526 | 0.400 | 0.892 |
| `kernels_packed` | 0.189 | 0.432 | 0.932 | 0.878 | 0.767 |
| `runner` | 0.507 | 0.740 | 1.21 | 1.08 | 1.75 |
| `packed_runner` | 0.636 | 1.06 | 1.88 | 1.73 | 1.84 |

**-O3, with NDEBUG; seconds**

| Unit | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `include` | 0.056 | 0.118 | 0.143 | 0.233 | - |
| `use_e2` | 0.140 | 0.405 | 0.683 | 0.547 | - |
| `use_all` | 0.277 | 0.933 | 1.69 | 1.12 | - |
| `self_test` | 0.213 | 0.778 | 1.08 | 0.774 | - |
| `kernels_scalar` | 0.127 | 0.333 | 0.528 | 0.402 | - |
| `kernels_packed` | 0.190 | 0.439 | 0.934 | 0.880 | - |
| `runner` | 0.512 | 0.797 | 1.33 | 1.08 | - |
| `packed_runner` | 0.649 | 1.18 | 2.26 | 1.80 | - |

**Debug: -O0 -g without NDEBUG (MSVC /Od /Z7 /RTC1); seconds**

| Unit | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `include` | 0.057 | 0.134 | 0.145 | 0.232 | 0.187 |
| `use_e2` | 0.182 | 0.656 | 0.765 | 0.660 | 0.257 |
| `use_all` | 0.395 | 1.58 | 1.89 | 1.44 | 0.359 |
| `self_test` | 0.147 | 0.512 | 0.544 | 0.454 | 0.251 |
| `kernels_scalar` | 0.115 | 0.349 | 0.386 | 0.307 | 0.222 |
| `kernels_packed` | 0.221 | 0.620 | 0.873 | 0.993 | 0.249 |
| `runner` | 0.432 | 0.628 | 0.857 | 0.856 | 0.605 |
| `packed_runner` | 0.565 | 0.952 | 1.42 | 1.60 | 0.655 |

The peak memory: the largest resident set of the compiler and of the processes it waits for (GCC's
driver runs `cc1plus` and `as`), and for MSVC the peak working set of `cl.exe`.

**-O2; peak MB**

| Unit | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `include` | 41 | 48 | 39 | 99 | 41 |
| `use_e2` | 64 | 82 | 71 | 116 | 60 |
| `use_all` | 86 | 118 | 106 | 127 | 64 |
| `self_test` | 70 | 90 | 75 | 115 | 57 |
| `kernels_scalar` | 62 | 70 | 56 | 108 | 52 |
| `kernels_packed` | 72 | 119 | 166 | 128 | 50 |
| `runner` | 142 | 154 | 125 | 135 | 93 |
| `packed_runner` | 158 | 213 | 248 | 155 | 96 |

**Debug; peak MB**

| Unit | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `include` | 42 | 51 | 42 | 100 | 41 |
| `use_e2` | 70 | 110 | 95 | 138 | 44 |
| `use_all` | 105 | 219 | 184 | 197 | 48 |
| `self_test` | 61 | 85 | 74 | 123 | 42 |
| `kernels_scalar` | 56 | 70 | 60 | 112 | 47 |
| `kernels_packed` | 70 | 129 | 175 | 127 | 50 |
| `runner` | 133 | 148 | 127 | 135 | 94 |
| `packed_runner` | 150 | 210 | 244 | 156 | 96 |

### The largest networks

The size of every kernel is counted in `include/kairn/gen/scalar.hpp`
([`kernel-sizes.json`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone1/costs/compile)):
the lines of its definitions for both limb types (the fix-up's function included), and the value
statements of its `double` function on the path its inline fix-up takes (the core, the tests and
the fix-up's selects), of which the fused ones. All 63 have 716 operations in 2 811 lines.
`compile_time.py per-kernel` compiles `kernels_scalar.cpp` and `kernels_packed.cpp` with an empty
table and with each kernel alone, at `-O2`, seven times; a cell is the difference of the minima, in
ms. The ten largest kernels by operations, and the smallest:

**Scalar, `kernels_scalar.cpp`; ms**

| Kernel | Operations | Lines | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ball_sub_2_full` | 38 | 134 | +11 | +15 | +25 | +16 | +31 |
| `ball_add_2_full` | 36 | 130 | +9 | +15 | +25 | +16 | +29 |
| `sub_2_2_full` | 30 | 112 | +8 | +10 | +19 | +12 | +30 |
| `ball_mul_2_full` | 29 | 116 | +9 | +15 | +26 | +15 | +36 |
| `add_2_2_full` | 28 | 108 | +9 | +11 | +18 | +11 | +28 |
| `ball_sub_2` | 26 | 62 | +5 | +13 | +18 | +9 | +23 |
| `ball_add_2` | 24 | 58 | +6 | +9 | +17 | +9 | +22 |
| `ball_scale_2_full` | 22 | 102 | +8 | +13 | +22 | +14 | +33 |
| `sub_1_2_full` | 22 | 98 | +7 | +11 | +16 | +10 | +24 |
| `sub_2_2` | 22 | 52 | +5 | +7 | +14 | +8 | +13 |
| `add_1_1` | 1 | 8 | +1 | +4 | +8 | +5 | +8 |
| all 63 (the unit, from the main run) | 716 | 2811 | +76 | +235 | +453 | +277 | +735 |
| none (the empty table) | | | 50 | 89 | 73 | 122 | 157 |
| the five largest: share of the sum of the increments; the same less the smallest's | | | 15%, 17% | 13%, 19% | 13%, 19% | 13%, 19% | 13%, 17% |

**Packed, `kernels_packed.cpp`; ms**

| Kernel | Operations | Lines | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ball_sub_2_full` | 38 | 134 | +7 | +16 | +21 | +17 | +30 |
| `ball_add_2_full` | 36 | 130 | +7 | +13 | +16 | +17 | +27 |
| `sub_2_2_full` | 30 | 112 | +2 | +10 | +17 | +13 | +25 |
| `ball_mul_2_full` | 29 | 116 | +4 | +12 | +19 | +18 | +27 |
| `add_2_2_full` | 28 | 108 | +6 | +9 | +15 | +17 | +21 |
| `ball_sub_2` | 26 | 62 | +10 | +10 | +14 | +16 | +24 |
| `ball_add_2` | 24 | 58 | +7 | +15 | +15 | +14 | +21 |
| `ball_scale_2_full` | 22 | 102 | +8 | +10 | +15 | +19 | +22 |
| `sub_1_2_full` | 22 | 98 | +8 | +13 | +16 | +15 | +21 |
| `sub_2_2` | 22 | 52 | +3 | +9 | +12 | +13 | +19 |
| `add_1_1` | 1 | 8 | +2 | +6 | +7 | +6 | +9 |
| all 63 (the unit, from the main run) | 716 | 2811 | +86 | +192 | +365 | +316 | +594 |
| none (the empty table) | | | 104 | 240 | 568 | 563 | 173 |
| the five largest: share of the sum of the increments; the same less the smallest's | | | 9%, 10% | 10%, 15% | 11%, 16% | 11%, 13% | 13%, 18% |

What one kernel adds is in good part what every kernel costs (two functions and their inlined
bodies) and grows slowly with its size: the largest adds 3 to 5 times what `add_1_1`, one
operation, adds (11 times with Apple clang, whose 1 ms for `add_1_1` is at the resolution of the
measurement). The lines of the packed kernels are not counted; they have the same operations.

### Where the time goes

From the compilers' own reports, at `-O2`, one compilation each: Clang's `-ftime-trace`
(`Frontend` and `Backend`), GCC's `-ftime-report` (`phase parsing` and `phase lang. deferred`,
against `phase opt and generate`) and MSVC's `/Bt+` (`c1xx.dll` against `c2.dll`). These
instruments slow the compilers, GCC 13 on Zen 2 three to five times, so only the shares are given:
the front end's share of front end and back end.

| Front end's share | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---:|---:|---:|---:|---:|
| `include` | 98% | 100% | 100% | 99% | 97% |
| `use_e2` | 41% | 23% | 44% | 49% | 15% |
| `use_all` | 28% | 12% | 23% | 31% | 7% |
| `kernels_scalar` | 31% | 16% | 29% | 36% | 17% |
| `kernels_packed` | 58% | 52% | 75% | 62% | 24% |

### MSVC's threads

MSVC's code generator can compile the functions of a unit on several threads (`/cgthreads`). The
main runs pin every compilation to one logical processor of a performance core, as the other
compilers, which use one thread; five units again at `/O2`, five compilations each:

| Seconds, `/O2` | pinned (the main run) | pinned, `/cgthreads1` | not pinned | not pinned, `/cgthreads1` |
|---|---:|---:|---:|---:|
| `use_e2` | 1.24 | 1.22 | 0.575 | 1.61 |
| `use_all` | 3.06 | 3.06 | 1.13 | 3.49 |
| `self_test` | 1.07 | 1.06 | 0.534 | 1.11 |
| `kernels_scalar` | 0.892 | 0.882 | 0.457 | 0.926 |
| `runner` | 1.75 | 1.75 | 1.29 | 1.83 |

Pinned, MSVC compiles as with one thread; alone on an idle machine it is 1.4 to 2.7 times faster.
Not pinned with one thread, it is slower than pinned, perhaps on the efficiency cores. In a build
of many units at once the pinned figures are the nearer.

### Repeatability

Seven compilations of each unit and level, in rounds over all of them; the tables give the
minimum. The median is within 3% of the minimum for most cells on Zen 2 and the i5; on the M3,
shared with other jobs and without affinity, 8 to 20% for Apple clang.

| Configuration | Runs | Median over minimum | Maximum over minimum |
|---|---|---|---|
| M3, Apple clang | 7 | 8 to 20% (median 12%) | 12 to 24% |
| M3, GCC 16 | 7 | 0 to 6% (median 1%) | 16 to 23% |
| Zen 2, GCC 13 | 7 | 0 to 12% (median 1%) | 52 to 76% |
| Zen 2, Clang 18 | 7 | 0 to 3% (median 0%) | 0 to 43% |
| i5, MSVC | 7 | 0 to 4% (median 1%) | 1 to 15% |

On Zen 2, three of the seven rounds of the GCC 13 run were about 1.5 times slower throughout, all
units alike, most likely from another job on the sibling of the pinned logical CPU (one was
there when it was checked afterwards); the minimum is that of the other four. A first run of the
GCC 13 baselines, with that sibling 40 to 75% busy, was discarded and repeated with it idle.

## The environment check in detail

### `KAIRN_CHECKS` in detail

The `costs.cpp` programs, `kairn-bench-costs-LEVEL` with `KAIRN_CHECKS` 0 and
`kairn-bench-costs-checks-LEVEL` with 1, three runs of each, alternated. A ratio is of the minima
of the two programs of one run; a cell is the lowest and highest over the three runs. Every output
of the two programs was the same, bit for bit (checksums). "One limb" is `Expansion<double, 1>`;
"a call each" is a loop that calls a non-inlined function for each addition.

**The environment check, and the scale (ns)**

| Configuration | `environment_ok()`, loop (ns) | cycles at the highest clock | `double` addition, loop (ns) | `double` addition, chain step (ns) | FMA, chain step (ns) |
|---|---|---|---|---|---|
| M3, Apple clang -O0 | 3.72 to 3.73 | 15.1 | 1.13 | 0.814 | 3.11 to 3.12 |
| M3, Apple clang -O2 | 0.361 to 0.387 | 1.5 to 1.6 | 0.142 | 0.39 to 0.393 | 0.71 to 0.762 |
| M3, Apple clang -O3 | 0.36 to 0.387 | 1.5 to 1.6 | 0.142 | 0.368 to 0.393 | 0.711 to 0.763 |
| M3, GCC 16 -O0 | 3.2 to 3.21 | 13.0 | 0.941 to 0.945 | 0.688 to 0.689 | 2.77 |
| M3, GCC 16 -O2 | 0.36 to 0.387 | 1.5 to 1.6 | 0.155 | 0.5 | 0.721 to 0.767 |
| M3, GCC 16 -O3 | 0.365 to 0.388 | 1.5 to 1.6 | 0.155 | 0.49 | 0.747 to 0.763 |
| Zen 2, GCC 13 -O0 | 11.4 | 38.2 | 2.81 to 2.83 | 3.26 | 6.2 to 6.21 |
| Zen 2, GCC 13 -O2 | 6.45 to 6.46 | 21.6 | 0.158 to 0.159 | 0.79 | 1.31 |
| Zen 2, GCC 13 -O3 | 6.46 | 21.6 | 0.158 to 0.159 | 0.79 to 0.791 | 1.31 to 1.32 |
| Zen 2, Clang 18 -O0 | 10.3 to 10.4 | 34.6 to 35.0 | 3.22 to 3.25 | 3.25 | 6.2 |
| Zen 2, Clang 18 -O2 | 6.24 | 20.9 | 0.151 | 0.79 | 1.31 |
| Zen 2, Clang 18 -O3 | 6.24 to 6.25 | 20.9 | 0.151 | 0.79 to 0.791 | 1.31 |
| i5, MSVC /Od | 2.63 | 12.1 | 0.966 to 0.968 | 1.66 | 7.03 |
| i5, MSVC /O2 | 1.1 | 5.1 | 0.0831 to 0.12 | 0.285 | 0.554 to 0.555 |

**`KAIRN_CHECKS` 1 over 0**

| Configuration | `x + y`, loop | `x + y`, chain | `x * y`, loop | `x * y`, chain | one limb, `x + y`, loop | one limb, `x + y`, chain | one limb, `x + y`, a call each |
|---|---|---|---|---|---|---|---|
| M3, Apple clang -O0 | 1.56 to 1.58 | 1.07 | 1.55 to 1.56 | 1.01 | 1.09 | 0.92 to 0.94 | 1.11 to 1.17 |
| M3, Apple clang -O2 | 1.48 to 1.49 | 1.01 | 2.61 to 2.62 | 1.06 to 1.14 | 5.72 to 5.78 | 2.07 to 2.08 | 1.33 |
| M3, Apple clang -O3 | 1.48 to 1.56 | 1.01 to 1.06 | 2.61 | 1.06 to 1.14 | 5.72 to 5.87 | 2.07 to 2.20 | 1.33 to 1.42 |
| M3, GCC 16 -O0 | 1.49 to 1.50 | 1.16 | 1.38 to 1.42 | 1.13 to 1.14 | 1.50 | 0.69 to 0.70 | 1.40 to 1.41 |
| M3, GCC 16 -O2 | 1.41 to 1.44 | 1.00 | 2.41 to 2.42 | 1.02 to 1.09 | 5.22 to 5.31 | 1.62 to 1.68 | 1.33 |
| M3, GCC 16 -O3 | 1.41 | 1.01 | 2.41 to 2.42 | 1.04 to 1.07 | 5.27 to 5.35 | 1.61 to 1.62 | 1.33 |
| Zen 2, GCC 13 -O0 | 1.62 to 1.63 | 1.27 | 1.62 to 1.63 | 1.26 | 2.10 | 1.04 | 1.63 |
| Zen 2, GCC 13 -O2 | 1.94 | 1.02 | 3.65 to 3.66 | 1.00 to 1.02 | 34.34 to 34.78 | 7.98 | 4.50 to 4.51 |
| Zen 2, GCC 13 -O3 | 1.90 to 1.91 | 1.00 | 3.77 to 3.78 | 0.99 | 33.61 to 34.12 | 7.97 to 7.98 | 4.30 to 4.31 |
| Zen 2, Clang 18 -O0 | 1.33 | 1.37 | 1.44 to 1.45 | 1.33 | 1.40 to 1.41 | 1.03 to 1.04 | 1.29 |
| Zen 2, Clang 18 -O2 | 2.99 to 3.00 | 1.03 | 4.14 to 4.15 | 1.03 to 1.04 | 33.66 to 33.78 | 7.99 to 8.00 | 5.86 |
| Zen 2, Clang 18 -O3 | 3.00 | 1.03 | 4.15 | 1.03 | 33.91 to 34.04 | 7.97 to 7.99 | 5.85 to 5.87 |
| i5, MSVC /Od | 1.05 to 1.09 | 1.05 to 1.07 | 0.98 to 1.00 | 0.97 to 0.98 | 1.86 to 1.93 | 1.04 | 1.78 to 1.80 |
| i5, MSVC /O2 | 1.26 to 1.27 | 1.01 | 2.16 | 1.03 to 1.05 | 7.50 to 12.66 | 2.98 to 2.99 | 1.24 |

**Times (ns)**

| Configuration | `x + y`, loop | `x + y`, chain | `x * y`, loop | `x * y`, chain | one limb, `x + y`, loop | one limb, `x + y`, chain | one limb, `x + y`, a call each |
|---|---|---|---|---|---|---|---|
| M3, Apple clang -O0, checks 0 | 28.7 to 28.9 | 48.9 to 49 | 23.2 to 23.3 | 37.5 to 37.6 | 5.47 | 13.1 | 6.34 to 6.36 |
| M3, Apple clang -O0, checks 1 | 45.1 to 45.2 | 52.4 | 36.2 to 36.3 | 38 to 38.1 | 5.94 to 5.97 | 12.1 to 12.3 | 7.08 to 7.43 |
| M3, Apple clang -O2, checks 0 | 1.43 to 1.44 | 7.53 to 7.54 | 0.718 | 5.26 to 5.65 | 0.141 to 0.142 | 0.392 to 0.393 | 0.81 to 0.811 |
| M3, Apple clang -O2, checks 1 | 2.13 to 2.14 | 7.59 to 7.6 | 1.88 | 5.98 | 0.813 to 0.814 | 0.813 | 1.08 |
| M3, Apple clang -O3, checks 0 | 1.36 to 1.44 | 7.17 to 7.54 | 0.718 | 5.26 to 5.64 | 0.139 to 0.142 | 0.37 to 0.393 | 0.756 to 0.81 |
| M3, Apple clang -O3, checks 1 | 2.12 to 2.14 | 7.59 to 7.6 | 1.88 | 5.97 to 5.98 | 0.813 to 0.814 | 0.813 to 0.814 | 1.08 |
| M3, GCC 16 -O0, checks 0 | 20.3 to 20.4 | 41.3 to 41.4 | 17.2 | 30.4 | 2.66 to 2.67 | 7.75 | 3.6 |
| M3, GCC 16 -O0, checks 1 | 30.5 | 48 to 48.2 | 23.7 to 24.4 | 34.5 | 4 to 4.01 | 5.38 to 5.39 | 5.06 |
| M3, GCC 16 -O2, checks 0 | 1.51 to 1.53 | 7.64 | 0.774 to 0.777 | 5.41 to 5.8 | 0.153 to 0.155 | 0.484 to 0.5 | 0.808 to 0.81 |
| M3, GCC 16 -O2, checks 1 | 2.17 | 7.67 to 7.68 | 1.87 | 5.92 to 5.93 | 0.811 | 0.812 to 0.813 | 1.08 |
| M3, GCC 16 -O3, checks 0 | 1.51 to 1.52 | 7.68 to 7.69 | 0.775 | 5.6 to 5.81 | 0.152 to 0.154 | 0.501 to 0.503 | 0.81 |
| M3, GCC 16 -O3, checks 1 | 2.13 to 2.14 | 7.75 | 1.87 | 6.02 | 0.812 to 0.813 | 0.812 | 1.08 |
| Zen 2, GCC 13 -O0, checks 0 | 35.4 to 35.6 | 44.4 | 32 to 32.2 | 40.4 | 5.55 | 14.6 | 8.16 to 8.19 |
| Zen 2, GCC 13 -O0, checks 1 | 57.5 to 57.6 | 56.3 to 56.4 | 52 to 52.2 | 50.8 to 51 | 11.7 | 15.1 | 13.3 to 13.4 |
| Zen 2, GCC 13 -O2, checks 0 | 4.41 | 10.2 | 2.3 to 2.31 | 8.32 to 8.33 | 0.185 to 0.188 | 0.789 to 0.791 | 1.53 |
| Zen 2, GCC 13 -O2, checks 1 | 8.54 to 8.56 | 10.5 | 8.41 to 8.44 | 8.35 to 8.46 | 6.44 | 6.3 to 6.31 | 6.9 |
| Zen 2, GCC 13 -O3, checks 0 | 4.41 | 10.2 to 10.3 | 2.3 to 2.31 | 8.31 to 8.33 | 0.184 to 0.188 | 0.79 to 0.791 | 1.53 to 1.54 |
| Zen 2, GCC 13 -O3, checks 1 | 8.4 to 8.41 | 10.3 | 8.68 to 8.7 | 8.24 to 8.25 | 6.29 to 6.3 | 6.3 to 6.31 | 6.6 to 6.61 |
| Zen 2, Clang 18 -O0, checks 0 | 51.3 | 54 to 54.1 | 42.7 | 49.8 | 9.76 | 19.6 | 11.8 |
| Zen 2, Clang 18 -O0, checks 1 | 68.3 to 68.4 | 73.9 to 74 | 61.6 to 61.9 | 66 to 66.1 | 13.7 | 20.3 | 15.2 |
| Zen 2, Clang 18 -O2, checks 0 | 2.71 to 2.72 | 10 | 1.97 | 8.07 to 8.08 | 0.187 | 0.79 | 1.53 to 1.54 |
| Zen 2, Clang 18 -O2, checks 1 | 8.13 | 10.3 | 8.17 to 8.18 | 8.36 | 6.3 to 6.31 | 6.31 to 6.32 | 8.99 to 9.01 |
| Zen 2, Clang 18 -O3, checks 0 | 2.71 | 10 | 1.97 | 8.08 to 8.09 | 0.185 to 0.186 | 0.79 to 0.791 | 1.53 to 1.54 |
| Zen 2, Clang 18 -O3, checks 1 | 8.13 to 8.14 | 10.3 | 8.17 to 8.18 | 8.33 to 8.35 | 6.31 | 6.31 to 6.32 | 8.99 to 9 |
| i5, MSVC /Od, checks 0 | 38.3 to 38.8 | 39.2 to 39.8 | 47.8 to 48 | 48.6 to 49.4 | 2.55 to 2.64 | 4.64 to 4.66 | 4.18 to 4.19 |
| i5, MSVC /Od, checks 1 | 40.8 to 41.6 | 41.8 to 42 | 46.6 to 47.7 | 47.7 to 47.9 | 4.9 to 4.91 | 4.84 to 4.85 | 7.47 to 7.53 |
| i5, MSVC /O2, checks 0 | 2.36 to 2.37 | 5.08 | 1.32 | 5.77 to 5.86 | 0.0869 to 0.147 | 0.296 to 0.297 | 1.77 |
| i5, MSVC /O2, checks 1 | 2.99 | 5.11 | 2.85 | 6.02 to 6.03 | 1.1 | 0.884 to 0.885 | 2.19 |

Checksums of KAIRN_CHECKS 1 that differ from those of 0: none

- The read is the whole of `environment_ok()`'s loop: `stmxcsr` to the stack and a test on x86-64,
  `mrs` of FPCR and a test on AArch64 (the disassembly of `kc_env_loop`). Zen 2's 21 cycles per
  call are, then, what one `stmxcsr` costs there, with the store and the load of its stack slot.
- The loops of one `double` addition over arrays on the i5 take 0.083 to 0.15 ns and vary that
  much between runs, as on the benchmark page; the one-limb loop's ratio there (7.5 to 12.7) is
  good to that much only.
- Unoptimized, a one-limb chain is faster with the checks on the M3 (0.69 to 0.94 times), an effect
  of the unoptimized code's stores and loads, not of the checks.
- The two scale rows, one `double` addition and one fused multiply-add in a chain of 256 steps, are
  below those operations' latencies on every machine (0.39 ns for an addition on the M3, whose
  latency is about 0.75 ns when a chain runs long): a chain that short, called again and again, is
  overlapped by the processor with the next call's. They are given for scale only, and the cycles
  above are from the highest clock, not from them. The chains of the two-limb operations are 10 to
  20 times longer per step, and the same overlap at their ends is small.

## MSVC's stack cookie in detail

### Which functions get it

`bench/gs_probe.cpp`, compiled with `cl /O2 /arch:AVX2 /fp:precise /std:c++20 /EHsc`, with the
default `/GS` and with `/GS-`, then `dumpbin /disasm`: whether each function reads
`__security_cookie` and calls `__security_check_cookie`, and its instructions (with `/GS-` in
parentheses where they differ). The plain types are structures with the same members as
`Expansion<double, 1>`, `Expansion<double, 2>` and `Ball<double, 2>`, whose operators take them by
`const&`.

| Shape | `double` | `Expansion<double, 1>` | `Expansion<double, 2>` | `Ball<double, 1>` | `Ball<double, 2>` | plain, `double limb[1]` | plain, `double limb[2]` | plain, a ball of two limbs |
|---|---|---|---|---|---|---|---|---|
| `ret_add` | 3 | **cookie**, 13 (5) | 50 | 66 | 103 | 4 | 5 | 8 |
| `ret_mul` | 3 | **cookie**, 13 (5) | 45 | 88 | 124 | 4 | 5 | 8 |
| `add` | 4 | **cookie**, 12 (4) | 51 | 67 | 101 | 4 | 4 | 7 |
| `mul` | 4 | **cookie**, 12 (4) | 46 | 90 | 123 | 4 | 4 | 7 |
| `tp_add` | 69 | **cookie**, 38 (30) | 64 | 318 | 130 | 29 | 34 | 52 |
| `tp_mul` | 69 | **cookie**, 38 (30) | 60 | 119 | 149 | 29 | 34 | 52 |
| `sum` | 20 | **cookie**, 44 (28) | 69 | 292 | 131 | 26 | 26 | 38 (37) |
| `prod` | 24 | **cookie**, 32 (24) | 59 | 121 | 152 | 24 | 27 | 34 |
| `dot` | 30 | **cookie**, 55 (40) | 99 | 178 | 251 | 43 | 40 | 93 (63) |
| `axpy` | 69 | **cookie**, 40 (32) | 98 | 178 | 245 | 32 | 65 | 85 |
| `horner` | 17 | 17 | 97 | 812 | 245 (244) | 17 | 17 | 37 |

10 of 88 functions read the cookie with /GS, 0 with /GS-.

### What triggers it

`bench/gs_isolate.cpp`: a one-limb type with `+` and `*`, changed one thing at a time from variant
1, which has the members and operators of `Expansion<T, 1>` without Kairn, in four functions.

| Variant | `add` | `add_value` | `dot` | `tp_add` |
|---|---|---|---|---|
| 0: Kairn's own Expansion&lt;double, 1&gt; | **cookie**, 12 | **cookie**, 11 | **cookie**, 55 | **cookie**, 38 |
| 1: class template partial specialization X&lt;T, 1&gt;, T limb[1] = {}, constexpr constructors, hidden friend operators taking V by value | **cookie**, 12 | **cookie**, 11 | **cookie**, 55 | **cookie**, 38 |
| 2: as 1, a plain struct instead of a template | **cookie**, 12 | **cookie**, 11 | **cookie**, 55 | **cookie**, 38 |
| 3: as 1, the primary template X&lt;T&gt; instead of a partial specialization | **cookie**, 12 | **cookie**, 11 | **cookie**, 55 | **cookie**, 38 |
| 4: as 1, the friends take const V& | 4 | 3 | 47 | 30 |
| 5: as 1, free function templates instead of hidden friends, taking V by value | **cookie**, 12 | **cookie**, 11 | **cookie**, 55 | **cookie**, 38 |
| 6: as 1, no default member initializer (T limb[1];) | **cookie**, 12 | **cookie**, 11 | **cookie**, 55 | **cookie**, 38 |
| 7: as 1, a scalar member T limb0 = {} instead of the array | 4 | 3 | 31 | 31 |
| 8: as 1, without the constructor from T (aggregate initialization) | **cookie**, 12 | **cookie**, 11 | **cookie**, 49 | **cookie**, 37 |
| 9: as 1, the friends are function templates of the plain struct of 2 (a template, no class template) | **cookie**, 12 | **cookie**, 11 | **cookie**, 55 | **cookie**, 38 |
| 10: as 6 and 4 together: no initializer, friends by reference | 4 | 3 | 47 | 30 |
| 11: Kairn's Expansion&lt;double, 2&gt;, the leading limb only, for comparison | 51 | 41 | 99 | 64 |
| 12: as 2, without noexcept: the plain structure of Phase 0 (experiments/phase0/k1/k1_layout.cpp) | **cookie**, 12 | **cookie**, 11 | **cookie**, 49 | **cookie**, 37 |
| 13: as 1, without noexcept | **cookie**, 12 | **cookie**, 11 | **cookie**, 49 | **cookie**, 37 |

api.cpp.obj /GS: 186 functions, 0 read the cookie.
api.cpp.obj /GS-: 186 functions, 0 read the cookie.

### The fix, on a copy of the headers

| Shape | `Expansion<double, 1>`, /GS, the headers as they are | the same, by const reference |
|---|---|---|
| `ret_add` | **cookie**, 13 | 5 |
| `ret_mul` | **cookie**, 13 | 5 |
| `add` | **cookie**, 12 | 4 |
| `mul` | **cookie**, 12 | 4 |
| `tp_add` | **cookie**, 38 | 30 |
| `tp_mul` | **cookie**, 38 | 30 |
| `sum` | **cookie**, 44 | 28 |
| `prod` | **cookie**, 32 | 24 |
| `dot` | **cookie**, 55 | 47 |
| `axpy` | **cookie**, 40 | 32 |
| `horner` | 17 | 17 |

With the change, 0 of 88 functions read the cookie.

### What it costs

The `costs.cpp` programs of the i5 built twice, with the default flags and with `/GS-` added to
`CMAKE_CXX_FLAGS`, three runs each; a ratio of the minima of the two builds in one run.

| Program | `k1/loop` | `k1/sum` | `k1/call` | `double/loop` | `double/call` | `add/loop` | `add/sum` | `mul/loop` | `mul/prod` | `env/loop` |
|---|---|---|---|---|---|---|---|---|---|---|
| `KAIRN_CHECKS` 0, `/O2` | 1.02 to 1.72 | 1.03 to 1.04 | 1.97 | 0.66 to 1.15 | 0.90 to 1.02 | 1.00 | 1.00 | 1.00 | 1.00 to 1.02 | 1.00 |
| `KAIRN_CHECKS` 0, `/Od` | 0.97 to 1.00 | 1.00 | 1.26 to 1.28 | 0.99 to 1.00 | 1.00 | 0.99 to 1.01 | 0.99 to 1.01 | 0.99 to 1.00 | 1.00 to 1.02 | 1.00 |
| `KAIRN_CHECKS` 1, `/O2` | 1.00 | 1.00 | 1.25 | 0.88 to 1.23 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| `KAIRN_CHECKS` 1, `/Od` | 1.02 | 1.00 | 1.15 to 1.17 | 0.99 | 0.82 to 1.01 | 0.98 to 1.00 | 0.99 to 1.01 | 0.97 to 1.00 | 0.97 to 0.99 | 1.00 |

`kairn-bench --filter api/` (the public types with `double` limbs), built and run the same way:
over its 93 functions, `/GS` over `/GS-` is 0.98 to 1.07 (the median over the runs of each
function), median 1.000; one function is above 3%, `api/tp/ball_add_1/kairn` (1.064 to 1.069),
which has no cookie: with `/GS` MSVC also lays out the stack frame differently, and 11 of the 186
functions of `api.cpp` differ in a few instructions or in the size of the frame.

## The quick tier in detail

### The tests that take the time

On each job's run with the median ctest total among the five (four for arm64), the seconds of each
test as ctest prints them, summed by family:

| Seconds | x86-64 GCC | x86-64 Clang | arm64 GCC | arm64 Clang | macOS | MSVC | clang-cl |
|---|---:|---:|---:|---:|---:|---:|---:|
| `kairn-oracle.selftest` | 55.4 | 55.4 | 35.0 | 33.9 | 75.3 | 105.2 | 104.9 |
| `crosscheck.guards` | 27.3 | 28.0 | 23.6 | 23.3 | 39.0 | 57.0 | 57.8 |
| `kairn-gen.test` | 19.8 | 19.9 | 14.4 | 14.1 | 16.9 | 36.1 | 34.2 |
| `docs.reference.test` | 12.0 | 9.8 | 7.9 | 10.3 | 16.1 | 41.4 | 48.8 |
| `crosscheck.compiled.*`, 126 tests | 103.8 | 104.3 | 71.2 | 71.5 | 116.4 | 254.2 | 264.4 |
| `api.oracle.*`, 97 tests | 44.6 | 45.6 | 34.4 | 34.4 | 63.4 | 117.2 | 114.5 |
| everything else | 11.9 | 12.5 | 8.8 | 12.6 | 16.0 | 36.7 | 47.4 |
| sum of the tests | 274.8 | 275.5 | 195.3 | 200.1 | 343.1 | 647.8 | 672.0 |
| ctest's total, four at a time | 73.5 | 73.1 | 55.1 | 55.8 | 89.1 | 167.3 | 172.0 |
| the same without `crosscheck.guards`, `kairn-gen.test`, `docs.reference.test` and `brute.driver.test` (replayed) | 55.4 | 55.4 | 37.8 | 38.7 | 75.3 | 128.4 | 132.5 |
| the same without `kairn-oracle.selftest` as well | 40.0 | 41.1 | 29.1 | 30.2 | 51.1 | 102.1 | 106.3 |

By label, the cross-checks (`crosscheck`) are 45 to 49% of the sum, the compiled runners'
(`compiled`) 34 to 39%, the public interface (`api`) 19 to 22%, the oracle's judgement of it
(`oracle`) 16 to 19%, and `docs` 4 to 7%. Everything else is 4 to 7% together; on Windows the two
consumer projects take 4 to 8 s each. The replay puts each test, in the order ctest started it, on
the first of four slots to free up; it reproduces ctest's own total within 0.1 s on all seven jobs.
The four tests of the first rows and `brute.driver.test` (1 to 4 s) are Python:
`kairn-gen.test` runs with `--no-cxx`, `crosscheck.guards` runs CMake scripts,
`docs.reference.test` and `brute.driver.test` the tools' own tests; `kairn-oracle.selftest`
compiles its own runner with the build's compiler, so it alone among them depends on the
compiler, partly.

Before the split from the full tier (`0ac39cf` to `6f89054`), the ctest step took 493 to 1974 s;
in `d0a5b29` `kairn-gen.test` reached its 600 s timeout on Linux x86-64 Clang and macOS, and the
clang-cl job failed to build in `d0a5b29` and `a906647`. The full tables, per job, are printed by
`python3 bench/ci_times.py tables results/milestone1/costs/ci/ci-build-and-test.json`.

## How it was measured

| Machine | Compilers | Conditions |
|---|---|---|
| M3: macOS arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2 | macOS has no affinity; compilations not pinned, benchmarks in the user-interactive class. Other jobs shared the machine: a run was started only when the 1-minute load average was under 10 and at most three processes used more than 30% of a core; a benchmark run whose median spread exceeded 2% was repeated (one) |
| Zen 2: Linux x86-64, AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1 | pinned to one logical CPU of the second socket (compilations of GCC 13 and the benchmarks on one, of Clang 18 on another); `mpstat` showed its SMT sibling idle during every benchmark run, and during most of the compilations ([Repeatability](#repeatability)) |
| i5: Windows 11 x64, Intel Core i5-13500T (6 performance, 8 efficiency cores) | MSVC 19.52 | pinned to one logical processor of a performance core, on a shared CI machine, started when no build or test of another job was running; `typeperf` showed the sibling 0 to 49% busy on average during the benchmark runs |

- **Commits**: the library of `040922c`. The tools: `7a7a5ca` (Zen 2: the GCC 13 compilations and
  the benchmarks), `0f81c17` (the benchmarks of the M3 and the i5, the M3's main compilations),
  `e166ef0` (Zen 2: Clang 18 and the GCC 13 baselines; the i5's compilations), `4696d2d` and `b710964` (the M3's baselines;
  the i5's phases and threads, and the stack cookie). They differ in the reports, in a unit added
  (`kairn_std`), in MSVC's options of the unoptimized benchmarks (`/Ob0`) and in two variants of
  `gs_isolate.cpp`; every JSON file records its commit, compiler, flags and commands.
- **Benchmarks** (`costs.cpp`): as `kairn-bench` ([the benchmark page](bench-milestone1.md#how-it-was-measured)):
  256 operations per call on arrays in L1, inputs from a fixed seed as in `api.cpp`, samples of
  about 4 ms, 31 per function, in rounds; contraction off, hardware FMA as `kairn::fma` gives it;
  `-O2` and `-O3` with GCC and Clang, `/O2` with MSVC, and `-O0` (`/Od /Ob0`).
- **Compile times**: wall time from the start of the compiler to its exit, the minimum of seven
  compilations in rounds over all units and levels, after one round discarded; processor time and
  the object's size are in the JSON too.
- **CI**: `gh run list`, `gh run view --json jobs` and the jobs' logs, read-only, on 2026-11-19
  at 22:27 UTC; step times have the one-second resolution of the API.
- **Not measured**: clang-cl and nvcc compile times; compile times of a whole client project, or
  with precompiled headers or modules; `KAIRN_CHECKS` with `float` limbs, with balls, or in packed
  code (which has no checks); the cookie with clang-cl; the fix of the cookie against
  `api.k1.zero_cost`; CI under QEMU, which the brief mentions and the workflow does not run.
