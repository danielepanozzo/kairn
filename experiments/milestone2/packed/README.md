# A vector loop, timed

`dot.cpp` times the dot product of the tutorial
[A vector loop](../../../docs/tutorials/vector-loop.md) written three ways, on the same arrays:

- **plain `T`**: `s += a[i] * b[i]` over the leading limbs, for scale;
- **`Expansion` loop**: `s = s + x.get(i) * y.get(i)` with `Expansion<T, k>`, one number at a
  time, over a `SoAView`;
- **`Packed` loop**: the tutorial's loop with `Packed<T, 2>`, $W$ numbers at a time, with
  `load_partial` for the tail and the lanes added at the end. There is none for one limb:
  `Packed<T, 1>` has no arithmetic ([Packed](../../../docs/reference/packed.md#the-operations)).

For `T` = `double` and `float`, $k$ = 1 and 2, and two lengths: 512 numbers (16 KB of limbs for
`double` and two limbs, in any first-level cache) and $2^{23}$ (up to 268 MB, in none). The
inputs are those of `bench/`: leading limbs $\pm[1, 2) \cdot 2^e$, $e \in [-8, 8]$, tails about $u$
times them, from a fixed seed. Each function is called through a pointer read from a volatile
object, so that no compiler sees what a call computes; a sample is about $2^{24}$ elements (32 768
calls on 512, one on $2^{23}$), and a row is the median of 11 samples, with its spread (the median
over the fastest) in parentheses in `results/`. Before timing, the program checks that the two
loops of two limbs agree (the last column of `results/`: their relative difference, within the
bound of either). It is not part of the library and not a test.

## Build and run

As a release build, so that `KAIRN_CHECKS` is 0, and without contraction, as `bench/` does:

```sh
c++ -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mavx2 -mfma -I include \
    experiments/milestone2/packed/dot.cpp -o dot            # x86-64, AVX2; -mfma alone: one lane
c++ -std=c++20 -O2 -DNDEBUG -ffp-contract=off -I include \
    experiments/milestone2/packed/dot.cpp -o dot            # AArch64, NEON
taskset -c 8 ./dot --machine "..." --compiler "..."         # Linux: pinned, its SMT sibling idle
```

`-DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR` gives the form of one lane anywhere. Options:
`--reps R` (samples, default 11), `--small N`, `--large N` (the lengths, default 512 and
$2^{23}$), `--sample E` (elements per sample, default $2^{24}$). The program prints a Markdown
table; the runs below are in `results/`, one file per machine, compiler and form.

## Results

Run on 2026-11-21 with the headers of the commit that adds this table. On the Mac: Apple M3 Max,
macOS 26, no affinity (the thread asks for the user-interactive class, which runs on performance
cores), with other work on the machine (load average 8 to 10). On the Linux machine: AMD EPYC 7452
(Zen 2), one logical CPU pinned with `taskset`, its SMT sibling idle, while tests ran on the other
socket. Flags: `-std=c++20 -O2 -DNDEBUG -ffp-contract=off`, and on x86-64 `-mavx2 -mfma` for the
AVX2 form. Nanoseconds per element, the median of 11 samples; the largest spread of any row of a
run was 1.03 on both machines.

| Machine, compiler, form | T | k | W | 512 elements: plain T | Expansion | Packed | Expansion / Packed | $2^{23}$ elements: plain T | Expansion | Packed | Expansion / Packed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M3 Max, Apple clang 21, NEON | double | 1 | 2 | 0.596 | 0.594 | - | - | 0.770 | 0.769 | - | - |
|  | double | 2 | 2 | 0.594 | 8.209 | 5.029 | 1.63 | 0.769 | 8.261 | 5.085 | 1.62 |
|  | float | 1 | 4 | 0.558 | 0.561 | - | - | 0.760 | 0.760 | - | - |
|  | float | 2 | 4 | 0.563 | 8.214 | 2.555 | 3.22 | 0.756 | 8.256 | 2.571 | 3.21 |
| M3 Max, GCC 16, NEON | double | 1 | 2 | 0.648 | 0.648 | - | - | 0.755 | 0.753 | - | - |
|  | double | 2 | 2 | 0.648 | 8.296 | 4.970 | 1.67 | 0.752 | 8.372 | 5.023 | 1.67 |
|  | float | 1 | 4 | 0.649 | 0.650 | - | - | 0.757 | 0.749 | - | - |
|  | float | 2 | 4 | 0.656 | 8.295 | 2.491 | 3.33 | 0.747 | 8.368 | 2.507 | 3.34 |
| EPYC 7452, GCC 13, AVX2 | double | 1 | 4 | 0.882 | 0.879 | - | - | 1.165 | 1.164 | - | - |
|  | double | 2 | 4 | 0.879 | 10.337 | 3.091 | 3.34 | 1.426 | 10.676 | 3.464 | 3.08 |
|  | float | 1 | 8 | 0.877 | 0.879 | - | - | 0.931 | 0.938 | - | - |
|  | float | 2 | 8 | 0.879 | 10.385 | 1.680 | 6.18 | 0.985 | 10.446 | 1.665 | 6.27 |
| EPYC 7452, Clang 18, AVX2 | double | 1 | 4 | 0.859 | 0.858 | - | - | 1.037 | 1.038 | - | - |
|  | double | 2 | 4 | 0.857 | 10.301 | 2.883 | 3.57 | 1.251 | 10.514 | 3.210 | 3.27 |
|  | float | 1 | 8 | 0.861 | 0.864 | - | - | 0.963 | 0.959 | - | - |
|  | float | 2 | 8 | 0.860 | 12.822 | 1.602 | 8.00 | 0.933 | 12.937 | 1.519 | 8.52 |

The form of one lane (`results/*-scalar.md`) costs what the `Expansion` loop costs, within 1%
(Expansion over Packed from 0.99 to 1.01 on every row of two limbs): it calls the same scalar
kernels.

## What the numbers show, and what they do not

- **Each loop is one dependent chain per accumulator.** The `Expansion` loop and the plain loop
  have one sum, so each element waits for the previous sum: they measure the latency of an
  addition (about 0.6 to 0.9 ns for `T`, about 8 to 13 ns for two limbs, whose sum is a chain of
  some twenty operations). The `Packed` loop has $W$ sums, one per lane, so its gain mixes two
  things: $W$ numbers per instruction, and $W$ chains that the processor overlaps. These numbers do
  not separate the two, and a scalar loop written with $W$ accumulators would recover part of the
  gain without SIMD; it is not measured here.
- **The gain is below $W$**: 1.6 to 1.7 of 2 on NEON, 3.1 to 3.6 of 4 and 6.2 to 8.5 of 8 with
  AVX2. The packed kernels compute the fix-up of infinities and NaN with selects in every lane,
  where the scalar kernel branches past it, so a packed sum is a longer chain than a scalar one (on
  the Mac, 10.1 ns per step of a register of two lanes against 8.2 for one number).
- **One limb** has no `Packed` loop; its `Expansion` loop costs what the plain loop costs (the
  zero cost of `Expansion<T, 1>`), both a chain of additions of `T`.
- **Arrays beyond the caches** cost the loops of two limbs little (at most 12%, the `Packed` loop of
  `double` with AVX2), since they are bound by the latency of their sums; the plain loop of `T`,
  which does least per element, slows by up to 36% on the Mac and 62% on the Linux machine.
- **Not shown**: anything about a loop other than this one, other lengths, more than one thread,
  or the `float` limbs of a GPU; whether a compiler would vectorize the plain loop (it may not
  reorder the sum of `T`, so it does not); and the cost of the debug build's checks, which this
  release build does not have.
