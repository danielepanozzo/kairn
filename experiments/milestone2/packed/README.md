# A vector loop, timed

`dot.cpp` times the dot product of the tutorial
[A vector loop](../../../docs/tutorials/vector-loop.md) written three ways, on the same arrays:

- **plain `T`**: `s += a[i] * b[i]` over the leading limbs, for scale;
- **`Expansion` loop**: `s = s + x.get(i) * y.get(i)` with `Expansion<T, k>`, one number at a
  time, over a `SoAView`;
- **`Packed` loop**: the tutorial's loop, $W$ numbers at a time, with `load_partial` for the tail
  and the lanes added at the end.

For `T` = `double` and `float`, $k$ = 1 and 2, and two lengths: 512 numbers (16 KB of limbs for
`double` and two limbs, in any first-level cache) and $2^{23}$ (up to 268 MB, in none). The
inputs are those of `bench/`: leading limbs $\pm[1, 2) \cdot 2^e$, $e \in [-8, 8]$, tails about $u$
times them, from a fixed seed. Each function is called through a pointer read from a volatile
object, so that no compiler sees what a call computes; a sample is about $2^{24}$ elements (32 768
calls on 512, one on $2^{23}$), and a row is the median of 11 samples, with its spread (the median
over the fastest) in parentheses. Before timing, the program checks that the two loops of $k$ limbs
agree (the last column: their relative difference, which for two limbs is within the bound of
either, and for one limb is the rounding of a sum in another order). It is not part of the library
and not a test.

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

Run on 2026-11-21 at commit `84146c9` (the headers as committed; this directory added after). On
the Mac: Apple M3 Max, macOS 26, no affinity (the thread asks for the user-interactive class,
which runs on performance cores), with other work on the machine (load average 3 to 8). On the
Linux machine: AMD EPYC 7452 (Zen 2), one logical CPU pinned with `taskset`, its SMT sibling idle.
Flags: `-std=c++20 -O2 -DNDEBUG -ffp-contract=off`, and on x86-64 `-mavx2 -mfma` for the AVX2
form. Nanoseconds per element, the median of 11 samples; the largest spread of any row of a run
was 1.10 on the Mac and 1.03 on the Linux machine.

| Machine, compiler, form | T | k | W | 512 elements: plain T | Expansion | Packed | Expansion / Packed | $2^{23}$ elements: plain T | Expansion | Packed | Expansion / Packed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M3 Max, Apple clang 21, NEON | double | 1 | 2 | 0.64 | 0.64 | 0.34 | 1.89 | 0.79 | 0.86 | 0.39 | 2.23 |
| | double | 2 | 2 | 0.64 | 8.73 | 5.33 | 1.64 | 0.82 | 9.05 | 5.52 | 1.64 |
| | float | 1 | 4 | 0.59 | 0.59 | 0.13 | 4.54 | 0.86 | 0.82 | 0.19 | 4.28 |
| | float | 2 | 4 | 0.55 | 8.84 | 2.78 | 3.18 | 0.82 | 8.65 | 2.74 | 3.16 |
| M3 Max, GCC 16, NEON | double | 1 | 2 | 0.70 | 0.69 | 0.30 | 2.31 | 0.84 | 0.85 | 0.40 | 2.10 |
| | double | 2 | 2 | 0.70 | 8.77 | 5.41 | 1.62 | 0.82 | 9.10 | 5.23 | 1.74 |
| | float | 1 | 4 | 0.70 | 0.69 | 0.14 | 5.02 | 0.79 | 0.80 | 0.19 | 4.16 |
| | float | 2 | 4 | 0.69 | 8.99 | 2.76 | 3.26 | 0.80 | 8.88 | 2.62 | 3.38 |
| EPYC 7452, GCC 13, AVX2 | double | 1 | 4 | 0.88 | 0.88 | 0.23 | 3.86 | 1.07 | 1.08 | 0.75 | 1.43 |
| | double | 2 | 4 | 0.88 | 10.35 | 3.08 | 3.36 | 1.43 | 10.83 | 3.67 | 2.95 |
| | float | 1 | 8 | 0.88 | 0.88 | 0.12 | 7.56 | 0.95 | 0.95 | 0.38 | 2.54 |
| | float | 2 | 8 | 0.88 | 10.36 | 1.68 | 6.18 | 0.93 | 10.36 | 1.60 | 6.48 |
| EPYC 7452, Clang 18, AVX2 | double | 1 | 4 | 0.86 | 0.86 | 0.20 | 4.24 | 1.07 | 1.07 | 0.77 | 1.40 |
| | double | 2 | 4 | 0.86 | 10.31 | 2.89 | 3.57 | 1.29 | 10.60 | 3.22 | 3.29 |
| | float | 1 | 8 | 0.86 | 0.86 | 0.10 | 8.80 | 0.94 | 0.93 | 0.38 | 2.45 |
| | float | 2 | 8 | 0.86 | 12.83 | 1.61 | 7.96 | 0.99 | 12.95 | 1.56 | 8.28 |

The form of one lane (`results/*-scalar.md`) costs what the `Expansion` loop costs for two limbs,
within 1% (Expansion over Packed from 0.99 to 1.01): it calls the same scalar kernels. For one
limb the two differ by up to 8% either way (0.92 to 1.12, the largest differences with Clang 18
on the Linux machine, where the form of one lane is the slower): its product is the kernel
`mul_1_1`, $\mathrm{fma}(a, b, +0)$, and that of `Expansion<T, 1>` the product of `T`.

## What the numbers show, and what they do not

- **Each loop is one dependent chain per accumulator.** The `Expansion` loop and the plain loop
  have one sum, so each element waits for the previous sum: they measure the latency of an
  addition (about 0.6 to 0.9 ns for `T`, about 9 to 13 ns for two limbs, whose sum is a chain of
  some twenty operations). The `Packed` loop has $W$ sums, one per lane, so its gain mixes two
  things: $W$ numbers per instruction, and $W$ chains that the processor overlaps. These numbers do
  not separate the two, and a scalar loop written with $W$ accumulators would recover part of the
  gain without SIMD; it is not measured here.
- **The gain is below $W$ for two limbs**: 1.6 to 1.7 of 2 on NEON, 2.9 to 3.6 of 4 and 6.2 to
  8.3 of 8 with AVX2. The packed kernels compute the fix-up of infinities and NaN with selects in every
  lane, where the scalar kernel branches past it, so a packed sum is a longer chain than a scalar
  one (on the Mac, 10.7 ns per step of a register of two lanes against 8.7 for one number).
- **For one limb**, the `Expansion` loop costs what the plain loop costs (the zero cost of
  `Expansion<T, 1>`), and the `Packed` loop gains about $W$ on arrays in the cache.
- **Arrays beyond the caches** change little for two limbs, whose loops are bound by the
  latency of their sums; for one limb the `Packed` loop then reads memory as fast as one core can
  (with AVX2, 16 bytes per element of `double` in 0.75 ns, about 21 GB/s), and gains less.
- **Not shown**: anything about a loop other than this one, other lengths, more than one thread,
  or the `float` limbs of a GPU; whether a compiler would vectorize the plain loop (it may not
  reorder the sum of `T`, so it does not); and the cost of the debug build's checks, which this
  release build does not have.
