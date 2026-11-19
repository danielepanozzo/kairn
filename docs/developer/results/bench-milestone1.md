# Benchmarks, Milestone 1

The measurements Milestone 1 owes ([Plan](../design/phase0/plan.md#performance-targets),
[D5](../design/phase0/decisions.md#d5-non-finite-results)): what the opaque product costs, what the
fix-up for non-finite results costs, what a `Ball` operation costs next to its center kernel and
next to `double`, and how Kairn's kernels compare with textbook double-word arithmetic. Three
machines, nine compiler configurations, `binary64` limbs, 2026-11-19. The harness and the exact
commands are in [`bench/`](https://github.com/danielepanozzo/kairn/tree/main/bench); the stored
measurements, one JSON file per configuration with the commit it measured, in
[`results/milestone1/bench/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone1/bench).

"M3", "Zen 2" and "i5" below are the three machines ([How it was measured](#how-it-was-measured)).
Every time is the minimum over 31 samples of about 4 ms, in ns per operation (throughput) or per
dependent step (latency); every ratio is a ratio of minima; a range is the lowest and highest
value over the configurations of a machine (four on the M3 and on Zen 2, one on the i5).

## The answers

### 1. The opaque product

Writing $\mathrm{RN}(ab)$ as `fma(a, b, +0.0)` instead of `a * b`:

- **costs nothing on the M3**, where an FMA and a multiplication both take 4 cycles: every ratio is
  between 0.96 and 1.04, except three small loops (0.63, 1.10, 1.14) whose difference is a
  vectorizer decision or code placement, not the product ([below](#what-the-machine-code-shows));
- **costs 6 to 13% on Zen 2** for `mul_2_1` and `mul_2_2`, in throughput and in latency, and 17
  and 24% in GCC -O2's unvectorized loops; 2 to 6% for `ball_mul_2`, whose time goes elsewhere. An
  FMA takes 5 cycles there, a multiplication 3, and where the product is the whole dependent chain
  the ratio shows: 1.66 for a chain of one-limb products, 1.53 to 1.57 for a chain of `two_prod`;
- **costs 10 to 12% in chains on the i5 with MSVC, 21% in packed `mul_2_2` throughput, and nothing
  in its scalar throughput loops**, where the plain variants are the slower ones (0.67 to 0.98:
  for `two_prod`, MSVC vectorizes the plain multiplication alone and pays for moving lanes; for
  `mul_2_1` we did not trace it). A `two_prod` chain costs 1.85, which comes from MSVC's code for
  `fma_rn` rather than from the product ([below](#what-the-machine-code-shows)).

| Opaque over plain | M3 | Zen 2 | i5 |
|---|---|---|---|
| `mul_2_1`, `mul_2_2`, throughput (scalar, packed) and product chain | 0.99 to 1.04 (three loops: 0.63, 1.10, 1.14) | 1.06 to 1.24 | 0.86 to 1.21 |
| Horner, `mul_2_2` then `add_2_2` | 0.99 to 1.04 | 1.03 to 1.05 | 1.00 to 1.04 |
| `ball_mul_2`, throughput and chains | 0.96 to 1.01 | 1.02 to 1.06 | 1.00 to 1.01 |
| chain of `two_prod` | 1.00 to 1.01 | 1.53 to 1.57 | 1.85 |
| chain of one-limb products, `mul_1_1` over `double` | 1.00 to 1.01 | 1.66 | 1.00 |

The cost is small where it is not zero, and it buys the guarantee that no compiler can fuse a
product into a neighbor ([Environment](../design/phase0/environment.md#contraction)).

### 2. The fix-up for non-finite results

**Packed code (blends, as listed) costs 19 to 58% on an addition and 70 to 106% on a
multiplication in throughput, and 6 to 54% in a dependent chain.** D5 expected 10 to 20% on a
2-limb addition; that holds only on Zen 2 (19 to 25%), and the M3 (34 to 58%) and the i5 (28%) are
above it. A multiplication suffers most because it is short: `mul_2_2` is 9 operations and the
fix-up adds 7 (an absolute value, two comparisons, an FMA, three blends; the operation on the
leading limbs is the core's own and compilers share it).

**In scalar code the form matters more than the machine.** Form (a) is the listing with its
selects; form (b) branches on "$z_0$ is finite" and does the fix-up in a function of its own. Two
variants test explanations: (b) with the fix-up inline, and (a) with `std::fabs` for `abs_bits`.

| Full over core, scalar | M3, Apple clang | M3, GCC 16 | Zen 2, GCC 13 | Zen 2, Clang 18 | i5, MSVC |
|---|---|---|---|---|---|
| `add_2_2` throughput: (a), (b), (b) inline | 1.60 to 1.63, 2.07 to 2.12, 1.48 to 1.51 | 2.46 to 2.61, 2.18 to 2.20, 2.14 to 2.18 | 1.32 to 4.90, 1.22 to 4.67, 1.21 to 1.22 | 1.19, 4.47 to 4.48, 1.19 | 6.17, 4.30, not run |
| `mul_2_2` throughput: (a), (b), (b) inline | 2.12 to 2.15, 2.07 to 2.11, 1.92 to 1.94 | 2.80 to 3.07, 2.37, 2.21 to 2.22 | 1.75 to 7.79, 1.28 to 6.08, 1.27 to 1.97 | 1.78 to 1.79, 5.57 to 5.60, 1.78 to 1.79 | 3.03, 1.50, not run |
| chains and Horner: (a), (b), (b) inline | 1.31 to 1.47, 0.99 to 1.04, 1.31 to 1.47 | 1.02 to 1.09, 0.97 to 1.06, 1.00 to 1.04 | 1.02 to 1.03, 1.00 to 1.03, 1.01 to 1.04 | 1.01 to 1.11, 1.00 to 1.01, 1.00 to 1.01 | 1.54 to 1.76, 1.01 to 1.05, not run |

(Exact values per configuration are in the [tables](#2-full-kernel-over-its-core).) What the
numbers say:

- **In a dependent chain a branch costs 0 to 6%**: it is predicted, and its test is off the
  critical path. The selects of form (a) put a comparison and a select on the critical path: 31
  to 47% with Apple clang, 54 to 76% with MSVC, 1 to 11% with GCC and with Clang on Zen 2.
- **In a loop of independent operations, what matters is whether the compiler vectorizes.** Clang
  vectorizes form (a), never form (b), whose call it cannot vectorize: hence 1.19 against 4.47 on
  Zen 2. GCC 13 vectorizes neither: it reports "control flow in loop", because it first moves part
  of the work under a branch and then, under its default `-ftrapping-math`, may not execute those
  floating-point operations speculatively (with `-fno-trapping-math` it vectorizes form (a)). GCC
  16 on AArch64 vectorizes no form. MSVC vectorizes the core `add_2_2` and no full form, hence its
  large throughput ratios.
- **The branch with the fix-up inline is the best scalar form on x86.** GCC 13 -O3 and Clang turn
  it back into blends where they vectorize (Zen 2: 1.19 to 1.22 on `add_2_2`, like form (a) at its
  best), and keep the branch in a chain (1.00 to 1.04, like form (b)). Apple clang, on the
  contrary, turns it into selects in the chain too, which makes it form (a) there.
- **`std::fabs` instead of `abs_bits` changes nothing that matters**: LLVM rewrites both into the
  same integer test, and with GCC the times move by at most 3%, either way.

Forms (a) and (b), both variants, and the packed form return the same bits, apart from NaN payloads
and the sign of zeros, on 8192 random and special operands per kernel (infinities, NaN, sums and
products that overflow) in all nine configurations; every result is canonical, and the 2-limb
results satisfy F4 and F5 of [IEEE-like results](../design/milestone1.md#ieee-like-results).

**Recommendation for the generator's scalar code:**

| Backend, compiler | Emit | Why |
|---|---|---|
| x86-64, GCC | the branch, fix-up inline | chains 1.01 to 1.04, like form (b); GCC -O3 vectorizes it (`add_2_2` 1.21 against 4.90 for form (a) and 4.67 for form (b)) |
| x86-64, Clang | the branch, fix-up inline | vectorized like form (a) (1.19), and a branch in chains (1.00 to 1.01), where form (a) costs up to 11% |
| x86-64, MSVC | the branch | chains 1.01 to 1.05 against 1.54 to 1.76 for form (a), and faster in throughput too (neither form is vectorized) |
| AArch64, Apple clang | the branch, fix-up in a function of its own | the only form whose chains cost nothing (0.99 to 1.04 against 1.31 to 1.47); it loses in loops Clang would vectorize (2.07 to 2.12 against 1.48 to 1.63 on `add_2_2`), where the packed kernels are the right tool anyway |
| AArch64, GCC | the branch, inline or not | no form is vectorized; the branch is faster in throughput (2.14 to 2.20 against 2.46 to 2.61) and costs at most 6% in chains |

The listing's selects remain the form for packed code: they are blends there, and there is no
alternative.

### 3. The cost of a Ball operation

| Ball over center, or over one `double` operation | M3 | Zen 2 | i5 |
|---|---|---|---|
| packed throughput, `ball_add_2` over `add_2_2` | 4.2 to 4.4 | 3.7 to 3.8 | 4.2 |
| packed throughput, `ball_mul_2` over `mul_2_2` | 16.0 to 16.4 | 13.5 to 15.0 | 20.3 |
| scalar sum chain, `ball_add_2` over `add_2_2` | 1.23 to 1.27 | 1.19 to 1.34 | 2.26 |
| scalar product chain, `ball_mul_2` over `mul_2_2` | 3.4 to 3.5 | 3.0 to 3.4 | 4.4 |
| scalar Horner, balls over 2 limbs | 2.15 to 2.16 | 1.89 to 2.19 | 3.13 |
| packed throughput, `ball_add_1` over a `double` addition | 8.2 to 8.8 | 10 to 12 | 12 |
| packed throughput, `ball_mul_1` over a `double` multiplication | 22 to 24 | 28 to 32 | 30 |
| scalar sum chain, `ball_add_1` over `double` | 19 to 23 | 13.6 to 14.6 | 26 |
| scalar product chain, `ball_mul_1` over `double` | 25 to 26 | 28 to 32 | 30 |

In absolute terms a packed `ball_add_2` takes 3.1 to 3.2 ns on the M3, 3.5 to 3.6 ns on Zen 2 and
2.3 ns on the i5 per ball; a packed `ball_mul_2` 5.9 to 6.1, 5.3 to 5.7 and 4.6 ns. Scalar loops
of balls are no faster than packed ones on the M3, and 2.2 to 5.3 times slower on the x86
machines, where the compilers vectorize them in 128-bit registers or not at all.

**The radius dominates.** Every `radd`, `rmul` and `abs_upper_2` ends with a step to the next
number up, done on the bit pattern: about ten integer operations in packed code, and in scalar
code a round trip through a general-purpose register. `ball_add_2` has four such steps;
`ball_mul_2` has eleven, next to the nine floating-point operations of its center. A ball sum stays
close to its center in latency because the radius is computed beside the center; a ball product
does not, because its radius waits for the center's magnitude. For scale, MPFR's 106-bit
multiplication (correctly rounded, not rigorous) takes 7.1 to 7.5 ns on the M3 and 15.2 to 15.9 ns
on Zen 2: a scalar `ball_mul_2` is only 1.05 to 1.25 times faster, and with GCC -O2 on Zen 2 slower
(0.67); a packed one is 1.2 times faster on the M3 and 2.8 to 3.0 times on Zen 2.

**The full Ball kernels** (the listing, form (a)) cost 4 to 39% in throughput, scalar or packed. In
chains they cost far more, up to 2.9 times: their selects make the next center wait for the radius
(`f` tests the radius, `e` the operands' radii), so the center and radius chains, which run side by
side in the core, become one. With a branch instead, chains cost 0 to 11% (scalar).

### 4. Against textbook double-word arithmetic, and the 1.2× budget

The baseline is AccurateDWPlusDW, SloppyDWPlusDW and DWTimesDW3 with an FMA, written from the
listings of [JMP17](../design/phase0/references.md#jmp17) (the same algorithms as Kairn's), with a
plain multiplication, no fix-up, and contraction off. With contraction on, such code computes
something else; that is what the opaque product is for.

| Kairn over textbook, scalar | M3 | Zen 2 | i5 | Within 1.2× |
|---|---|---|---|---|
| `add_2_2`, `add_fast_2_2` cores, throughput and chain | 0.96 to 1.04 | 0.96 to 1.02 | 1.00 to 1.01 | yes |
| `mul_2_2` core, throughput | 0.99 to 1.02 | 1.06 to 1.25 | 0.98 | yes, except GCC -O2 on Zen 2 (1.25) |
| `mul_2_2` core, product chain and Horner | 0.99 to 1.04 | 1.04 to 1.09 | 1.04 to 1.10 | yes |
| `add_2_2` full, recommended form, throughput | 2.07 to 2.08 (Apple clang), 2.13 to 2.21 (GCC) | 1.17 to 1.21 | 4.32 | no, except Zen 2 (borderline) |
| `add_2_2` full, recommended form, chain | 0.99 to 1.05 | 1.00 to 1.04 | 1.06 | yes |
| `mul_2_2` full, recommended form, throughput | 2.09 to 2.39 | 1.59 to 2.15 | 1.47 | no |
| `mul_2_2` full, recommended form, chain and Horner | 0.97 to 1.07 | 1.05 to 1.12 | 1.10 to 1.11 | yes |

Packed, against what a packed textbook implementation would compute (the packed core for the
addition, the packed core with a plain multiplication for the product), the full kernels cost
1.34 to 2.04 times on the M3, 1.19 to 2.19 on Zen 2 and 1.28 to 2.49 on the i5.

So: **the cores meet the budget** everywhere except unvectorized GCC -O2 code on Zen 2 (1.25 for a
multiplication); the cores are what `kairn::finite::` and the batch kernels use. **The full
kernels meet it in latency** with a branch, and **miss it in throughput**: a multiplication costs
1.5 to 2.4 times the textbook one, an addition 1.2 times on Zen 2 and 2.1 to 4.3 times elsewhere.
That is the price of IEEE-like results in loops of independent operations, and the reason D5 keeps
the fix-up out of the batch kernels.

MPFR at 106 bits, for scale (installed on the M3 and on Zen 2, not on the Windows machine): in
throughput 9.5 to 15 times slower than `add_2_2` and 20 to 42 times slower than `mul_2_2` (vectorized
loops; 3.9 and 8.8 times against GCC -O2's scalar loops); in a dependent chain only 0.84 to 2.0
times, because a 2-limb addition is eleven dependent floating-point additions while MPFR's integer
code is not one long chain.

## What the machine code shows

The loops of every timed function were disassembled on every configuration (`objdump`, `dumpbin`)
and summarized by `bench/asm_summary.py`; the counts are stored next to the measurements, and the
[last table but one](#machine-code-of-the-throughput-loops) lists the main throughput loops.

- **The opaque product is one fused instruction everywhere**, never a call, never folded into a
  multiplication. It needs one extra instruction: x86's FMA overwrites one of its operands, so each
  product needs a register copy first (and GCC copies with `vmovsd xmm, xmm, xmm`, which, unlike
  `vmovapd`, is not eliminated at renaming); NEON's `fmla` accumulates into its destination, so
  vectorized code rematerializes a zero (`movi`) before each product, and MSVC's packed loops zero
  a register (`vxorpd`) per product. Scalar AArch64 code uses the four-operand `fmadd` with a zero
  register and needs nothing.
- **GCC -O2 on Zen 2 vectorizes nothing.** Its loop of independent `mul_2_2` takes 1.8 ns per
  operation, five times the vectorized loop, and is bound by latency even though the operations
  are independent; there the FMA's extra latency shows in throughput (1.24). GCC 16 -O2 on
  AArch64 vectorizes, and vectorizes the generated `mul_2_1` but not its plain twin: the 0.63 of the
  first table is a cost-model decision.
- **Code placement moves the smallest loops.** On the M3, the `mul_2_1` loop of the generated
  kernel ran 1.14 times slower than its plain twin with GCC 16 -O3, and the packed one 1.10 times
  with Apple clang -O2 (the same instructions at -O3 give 1.00); in an earlier build, GCC 16 -O3's
  `two_prod` loop ran 1.59 times slower. Each pair differs by one `movi`. Built with
  `-falign-loops=64`, the GCC pairs take the same time (`two_prod` 0.242 and 0.243 ns, `mul_2_1`
  0.266 and 0.263 ns). On Zen 2, loops whose body is a handful of instructions (`double` addition
  and multiplication, `mul_1_1`, packed `two_prod`) moved by up to 1.9 times between two builds,
  while every other function reproduced within 3% (median 0.2%). Ratios against those tiny loops
  are good to a factor of two at best.
- **Form (a) is straight-line only on AArch64.** GCC on x86 turns the selects on `f` into a
  conditional branch and computes `r1` with `cmovp` in general-purpose registers; Clang on x86
  blends `w0` (`vblendvpd`) and branches for `w1` in scalar code, and uses only blends where it
  vectorizes; GCC 16 on AArch64 also branches. Apple clang keeps the listing (`fcsel`).
- **`abs_bits` sends the finiteness test through a general-purpose register** with GCC on x86
  (`vmovq`, `and`, `vmovq`) and with Apple clang (`fmov`, `and`, `cmp`, then `fcsel` on the
  integer flags): about 3 ns, a dozen cycles, on the M3's critical path per operation. `std::fabs`
  does not avoid it: LLVM rewrites `fabs(x) < inf` into the same integer test.
- **MSVC's `fma_rn`** (through `_mm_set_sd`) adds a `vmovq` that clears the upper lane of every
  computed operand, and `fma_rn(a, b, -p)` becomes `vxorpd` and `vfmadd` rather than one `vfmsub`.
  In the `two_prod` chain MSVC also keeps the running product in memory across its four-times
  unrolled loop, while the plain chain stays in registers: hence 1.85.

## What the generator could do better

Not acted on here; each item rests on the evidence above.

1. **Emit the scalar fix-up behind a branch**, as the recommendation table says: inline on x86-64,
   in a function of its own for Clang on AArch64.
2. **A step to the next number up for nonnegative operands.** Every radius operand is nonnegative;
   there the step is "add one to the bit pattern unless it is $+\infty$ or a NaN": two or three
   operations instead of about ten, no sign handling. It needs its own statement and proof, and
   care with $-0$, which `abs_2`'s select can return.
3. **MSVC's `fma_rn`**: `fms` spelled with `_mm_fmsub_sd`, and operands wrapped without clearing
   the upper lane, would remove a `vxorpd` and a `vmovq` per fused operation.

## How it was measured

| Machine | Configurations | Conditions |
|---|---|---|
| M3: macOS arm64, Apple M3 Max (12 performance, 4 efficiency cores) | Apple clang 21, GCC 16.2; `-O2` and `-O3` | macOS has no affinity: the thread asked for the user-interactive class, which runs on performance cores; other jobs of this project ran at low priority, so each configuration was run when the load average was under 10 and repeated if its median spread exceeded 2% |
| Zen 2: Linux x86-64, AMD EPYC 7452, 2 × 32 cores | GCC 13.3, Clang 18.1; `-O2` and `-O3`; `-mfma`, packed code `-mavx2 -mfma` | pinned to one logical CPU; `mpstat` showed it and its SMT sibling idle before the runs, and the sibling 99.6 to 100% idle throughout |
| i5: Windows 11 x64, Intel Core i5-13500T (6 performance, 8 efficiency cores) | MSVC 19.52, `/O2 /arch:AVX2 /fp:precise` | pinned to one logical processor of a performance core whose two logical processors were idle at the start, with the machine 5% busy; a shared CI machine |

- **Commits**: the M3 and Zen 2 at `82064a4`; the i5 at `53f80d1`, whose timed functions are the
  same except the two variants of the full kernels, added later and not run there (a second run on
  the i5 at `82064a4` was disturbed by a CI job that started during it, and later the machine
  stayed busy).
- **Flags**: hardware FMA as `kairn::fma` gives it, contraction off (`-ffp-contract=off`; MSVC's
  `/fp:precise` does not contract), never `-ffast-math`. The generated kernels contain no plain
  multiplication, so contraction does not change them.
- **Inputs**: 256 normalized 2-limb numbers per operand, leading limbs $\pm[1, 2)\cdot 2^k$ with
  $k \in [-8, 8]$; radii about $2^{-80}$ of the centers; factors in $[2^{-1/4}, 2^{1/4})$; made at
  run time from a fixed seed, the same with every compiler. No overflow or underflow in a timed loop.
- **Throughput**: independent operations over arrays in L1, in a non-inlined function called
  through a pointer; the compiler was free to vectorize the scalar loop, and the tables say where it
  did. **Latency**: a running sum, a running product of factors near 1, a Horner evaluation; a
  packed chain runs one chain per lane, and its time is per step.
- **Checks before timing**: every timed function against the generated kernel on the benchmark
  inputs, bit for bit (MPFR within $2^{-100}$ per operation); none failed.
- **Spread**: for the median function, the median of the 31 samples was within 1.1% of the minimum
  on the M3, 0.3% on Zen 2 and 0.1% on the i5. A first run on the M3, made while other jobs loaded
  the machine, was discarded for a spread of 7 to 35%. Two complete runs on Zen 2, at two commits,
  agree within 0.2% at the median function; two on the M3 within 0 to 5%, uniformly per
  configuration.
- **Measured**: the times, the bitwise agreements, the instruction counts. **Inferred**: the
  explanations. The latencies of 3, 4 and 5 cycles are the vendors' and agree with the measured
  ratios (5 : 3 on Zen 2, 1 : 1 on the M3); that GCC -O2's scalar loops on Zen 2 are bound by
  latency, and what the register round trips cost, are readings of the code, not separate
  measurements.
- **Not measured**: `float` limbs; AVX-512 (no machine has it); GPUs; the environment check at
  batch entry (it does not exist yet); clang-cl; MPFR on Windows (not installed there); Arb.

## Tables

The tables below are printed by `python3 bench/report.py results/milestone1/bench` from the stored
files; nothing in them was typed by hand.

### Configurations

| Configuration | Machine | Compiler | Flags | Spread: median, worst | Date, commit |
|---|---|---|---|---|---|
| M3, Apple clang -O2 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive; other jobs ran at low priority | Apple clang 21.0.0 (clang-2100.4.1.1) | `-O3 -DNDEBUG -O2 -ffp-contract=off` | 0.9%, 8% | 2026-11-19, `82064a4` |
| M3, Apple clang -O3 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive; other jobs ran at low priority | Apple clang 21.0.0 (clang-2100.4.1.1) | `-O3 -DNDEBUG -O3 -ffp-contract=off` | 1.1%, 6% | 2026-11-19, `82064a4` |
| M3, GCC 16 -O2 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive; other jobs ran at low priority | GCC 16.2.0 | `-O3 -DNDEBUG -O2 -ffp-contract=off` | 1.0%, 7% | 2026-11-19, `82064a4` |
| M3, GCC 16 -O3 | macOS arm64, Apple M3 Max (12 performance and 4 efficiency cores); not pinned (macOS has no affinity), QoS user-interactive; other jobs ran at low priority | GCC 16.2.0 | `-O3 -DNDEBUG -O3 -ffp-contract=off` | 0.9%, 6% | 2026-11-19, `82064a4` |
| Zen 2, GCC 13 -O2 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | GCC 13.3.0 | `-O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 0.3%, 5% | 2026-11-19, `82064a4` |
| Zen 2, GCC 13 -O3 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | GCC 13.3.0 | `-O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 0.3%, 4% | 2026-11-19, `82064a4` |
| Zen 2, Clang 18 -O2 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | Clang 18.1.3 (1ubuntu1) | `-O3 -DNDEBUG -O2 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 0.2%, 3% | 2026-11-19, `82064a4` |
| Zen 2, Clang 18 -O3 | Linux x86-64, AMD EPYC 7452 (Zen 2), two sockets of 32 cores; one logical CPU, its SMT sibling idle | Clang 18.1.3 (1ubuntu1) | `-O3 -DNDEBUG -O3 -ffp-contract=off -mfma (packed code also -mavx2 -mfma)` | 0.2%, 3% | 2026-11-19, `82064a4` |
| i5, MSVC /O2 | Windows 11 x64, Intel Core i5-13500T (6 performance and 8 efficiency cores); one logical processor of a performance core, its sibling idle at the start; a shared CI machine | MSVC 19.52.37029 | `/DWIN32 /D_WINDOWS /EHsc /O2 /Ob2 /DNDEBUG /O2 /fp:precise /arch:AVX2` | 0.1%, 30% | 2026-11-19, `53f80d1` |

### Checks

| Configuration | Functions checked bit for bit | Full kernels: cases; differences (b) vs (a), packed vs scalar (a), variants vs (a); against the statement |
|---|---:|---|
| M3, Apple clang -O2 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| M3, Apple clang -O3 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| M3, GCC 16 -O2 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| M3, GCC 16 -O3 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| Zen 2, GCC 13 -O2 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| Zen 2, GCC 13 -O3 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| Zen 2, Clang 18 -O2 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| Zen 2, Clang 18 -O3 | 96 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |
| i5, MSVC /O2 | 81 (0 failed) | `add_2_2_full` 8192: 0, 0, 0; 0; `mul_2_2_full` 8192: 0, 0, 0; 0; `ball_add_2_full` 8192: 0, 0, 0; 0; `ball_mul_2_full` 8192: 0, 0, 0; 0 |

### 1. Opaque product over plain product

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| scalar throughput, `two_prod` | 1.00 | 1.00 | 1.00 | 0.99 | 1.02 | 1.32 | 1.13 | 0.99 | 0.67 |
| scalar throughput, `mul_2_1` | 1.01 | 1.03 | 0.63 | 1.14 | 1.17 | 1.08 | 1.07 | 1.06 | 0.86 |
| scalar throughput, `mul_2_2` | 0.99 | 0.99 | 1.00 | 1.00 | 1.24 | 1.09 | 1.07 | 1.07 | 0.98 |
| scalar throughput, `ball_mul_2` | 1.00 | 1.01 | 1.00 | 1.00 | 1.03 | 1.05 | 1.04 | 1.04 | 1.00 |
| packed throughput, `two_prod` | 1.03 | 1.00 | 1.00 | 1.00 | 1.44 | 1.15 | 1.04 | 1.04 | 1.00 |
| packed throughput, `mul_2_1` | 1.10 | 1.00 | 1.01 | 1.03 | 1.08 | 1.08 | 1.08 | 1.08 | 0.96 |
| packed throughput, `mul_2_2` | 1.03 | 1.03 | 1.01 | 0.99 | 1.11 | 1.09 | 1.10 | 1.07 | 1.21 |
| packed throughput, `ball_mul_2` | 1.00 | 1.00 | 1.00 | 1.00 | 1.05 | 1.05 | 1.05 | 1.05 | 1.01 |
| scalar product chain, `two_prod` | 1.01 | 1.01 | 1.00 | 1.01 | 1.53 | 1.54 | 1.56 | 1.57 | 1.85 |
| scalar product chain, `mul_2_1` | 1.00 | 1.00 | 1.00 | 1.00 | 1.13 | 1.13 | 1.13 | 1.12 | 1.12 |
| scalar product chain, `mul_2_2` | 1.00 | 1.04 | 0.99 | 1.00 | 1.08 | 1.08 | 1.09 | 1.09 | 1.10 |
| scalar product chain, `ball_mul_2` | 0.96 | 0.96 | 1.00 | 0.99 | 1.05 | 1.05 | 1.03 | 1.02 | 1.01 |
| scalar Horner, `mul_2_2+add_2_2` | 1.01 | 1.00 | 1.00 | 1.04 | 1.04 | 1.03 | 1.03 | 1.03 | 1.04 |
| scalar Horner, `ball_mul_2+ball_add_2` | 1.01 | 1.00 | 1.01 | 1.00 | 1.02 | 1.02 | 1.02 | 1.02 | 1.01 |
| packed product chain, `two_prod` | — | — | — | — | — | — | — | — | — |
| packed product chain, `mul_2_1` | — | — | — | — | — | — | — | — | — |
| packed product chain, `mul_2_2` | 1.00 | 1.00 | 1.00 | 0.99 | 1.08 | 1.08 | 1.09 | 1.09 | 1.00 |
| packed product chain, `ball_mul_2` | 1.00 | 0.97 | 1.00 | 1.00 | 1.06 | 1.05 | 1.06 | 1.06 | 1.00 |
| packed Horner, `mul_2_2+add_2_2` | 0.99 | 1.00 | 1.00 | 1.00 | 1.04 | 1.05 | 1.03 | 1.03 | 1.00 |
| packed Horner, `ball_mul_2+ball_add_2` | 1.01 | 1.00 | 1.00 | 1.00 | 1.02 | 1.02 | 1.03 | 1.03 | 1.00 |
| scalar product chain, one limb: `mul_1_1` over `double` | 1.01 | 1.01 | 1.00 | 1.00 | 1.66 | 1.66 | 1.66 | 1.66 | 1.00 |

### 2. Full kernel over its core

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| scalar throughput, `add_2_2`, (a) selects | 1.60 | 1.63 | 2.61 | 2.46 | 1.32 | 4.90 | 1.19 | 1.19 | 6.17 |
| scalar throughput, `add_2_2`, (b) branch | 2.07 | 2.12 | 2.20 | 2.18 | 1.22 | 4.67 | 4.47 | 4.48 | 4.30 |
| scalar throughput, `add_2_2`, (a') selects, `fabs` | 1.59 | 1.63 | 2.59 | 2.45 | 1.30 | 4.75 | 1.19 | 1.19 | — |
| scalar throughput, `add_2_2`, (b') branch, inline | 1.48 | 1.51 | 2.18 | 2.14 | 1.22 | 1.21 | 1.19 | 1.19 | — |
| scalar sum chain, `add_2_2`, (a) selects | 1.43 | 1.47 | 1.09 | 1.08 | 1.03 | 1.03 | 1.10 | 1.11 | 1.76 |
| scalar sum chain, `add_2_2`, (b) branch | 1.03 | 1.04 | 1.06 | 1.05 | 1.02 | 1.02 | 1.00 | 1.00 | 1.05 |
| scalar sum chain, `add_2_2`, (a') selects, `fabs` | 1.47 | 1.47 | 1.09 | 1.08 | 1.05 | 1.05 | 1.10 | 1.10 | — |
| scalar sum chain, `add_2_2`, (b') branch, inline | 1.47 | 1.47 | 1.00 | 1.00 | 1.01 | 1.01 | 1.00 | 1.00 | — |
| packed throughput, `add_2_2`, (a) blends | 1.58 | 1.55 | 1.35 | 1.34 | 1.25 | 1.24 | 1.20 | 1.19 | 1.28 |
| packed sum chain, `add_2_2`, (a) blends | 1.25 | 1.25 | 1.26 | 1.29 | 1.18 | 1.18 | 1.11 | 1.11 | 1.54 |
| scalar throughput, `mul_2_2`, (a) selects | 2.15 | 2.12 | 3.07 | 2.80 | 1.75 | 7.79 | 1.79 | 1.78 | 3.03 |
| scalar throughput, `mul_2_2`, (b) branch | 2.11 | 2.07 | 2.37 | 2.37 | 1.28 | 6.08 | 5.60 | 5.57 | 1.50 |
| scalar throughput, `mul_2_2`, (a') selects, `fabs` | 2.15 | 2.09 | 3.09 | 2.78 | 1.73 | 7.78 | 1.79 | 1.78 | — |
| scalar throughput, `mul_2_2`, (b') branch, inline | 1.94 | 1.92 | 2.22 | 2.21 | 1.27 | 1.97 | 1.79 | 1.78 | — |
| scalar prod chain, `mul_2_2`, (a) selects | 1.35 | 1.36 | 1.02 | 1.02 | 1.03 | 1.02 | 1.01 | 1.01 | 1.54 |
| scalar prod chain, `mul_2_2`, (b) branch | 0.99 | 1.00 | 1.05 | 1.03 | 1.03 | 1.03 | 1.01 | 1.01 | 1.01 |
| scalar prod chain, `mul_2_2`, (a') selects, `fabs` | 1.35 | 1.36 | 1.02 | 1.02 | 1.02 | 1.02 | 1.01 | 1.01 | — |
| scalar prod chain, `mul_2_2`, (b') branch, inline | 1.34 | 1.36 | 1.04 | 1.03 | 1.04 | 1.04 | 1.00 | 1.00 | — |
| packed throughput, `mul_2_2`, (a) blends | 1.97 | 1.97 | 1.70 | 1.73 | 1.97 | 2.01 | 1.73 | 1.79 | 2.06 |
| packed prod chain, `mul_2_2`, (a) blends | 1.31 | 1.26 | 1.20 | 1.20 | 1.08 | 1.08 | 1.06 | 1.06 | 1.52 |
| scalar Horner, 2 limbs, (a) selects | 1.31 | 1.32 | 1.03 | 1.06 | 1.02 | 1.03 | 1.06 | 1.06 | 1.64 |
| scalar Horner, 2 limbs, (b) branch | 0.99 | 0.99 | 0.97 | 1.03 | 1.00 | 1.00 | 1.01 | 1.01 | 1.05 |
| scalar Horner, 2 limbs, (a') selects, `fabs` | 1.32 | 1.32 | 1.03 | 1.05 | 1.01 | 1.01 | 1.06 | 1.06 | — |
| scalar Horner, 2 limbs, (b') branch, inline | 1.31 | 1.32 | 1.03 | 1.03 | 1.01 | 1.01 | 1.01 | 1.01 | — |
| packed Horner, 2 limbs, (a) blends | 1.25 | 1.24 | 1.20 | 1.20 | 1.10 | 1.10 | 1.08 | 1.08 | 1.45 |

Form (b) over form (a), scalar:

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, `add_2_2` | 1.29 | 1.30 | 0.85 | 0.89 | 0.92 | 0.95 | 3.76 | 3.77 | 0.70 |
| throughput, `mul_2_2` | 0.98 | 0.98 | 0.77 | 0.85 | 0.73 | 0.78 | 3.12 | 3.12 | 0.49 |
| sum chain, `add_2_2` | 0.72 | 0.70 | 0.98 | 0.98 | 1.00 | 1.00 | 0.90 | 0.90 | 0.60 |
| product chain, `mul_2_2` | 0.74 | 0.74 | 1.02 | 1.02 | 1.00 | 1.00 | 1.01 | 1.01 | 0.65 |
| Horner, `mul_2_2+add_2_2` | 0.76 | 0.75 | 0.94 | 0.98 | 0.98 | 0.98 | 0.95 | 0.96 | 0.64 |
| throughput, `ball_add_2` | 1.08 | 1.08 | 1.02 | 1.02 | 0.94 | 1.55 | 1.33 | 1.33 | 0.77 |
| throughput, `ball_mul_2` | 1.21 | 1.21 | 1.29 | 1.29 | 0.96 | 1.81 | 1.16 | 1.16 | 0.86 |
| sum chain, `ball_add_2` | 0.35 | 0.35 | 0.45 | 0.46 | 1.00 | 0.99 | 0.83 | 0.83 | 0.50 |
| product chain, `ball_mul_2` | 0.64 | 0.65 | 0.76 | 0.78 | 1.03 | 1.02 | 1.00 | 1.00 | 0.73 |
| Horner, `ball_mul_2+ball_add_2` | 0.51 | 0.50 | 0.61 | 0.96 | 0.99 | 0.95 | 0.95 | 0.95 | 0.60 |

### 3. Ball operations

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| scalar throughput, `ball_add_2` (ns) | 3.33 | 3.34 | 3.12 | 3.12 | 12.7 | 7.75 | 9.06 | 9.07 | 10.9 |
| scalar throughput, `add_2_2` (ns) | 0.73 | 0.714 | 0.734 | 0.734 | 3.62 | 0.944 | 0.949 | 0.948 | 0.549 |
| scalar throughput, `ball_mul_2` (ns) | 6.4 | 6.41 | 5.96 | 5.99 | 23.6 | 12.8 | 14.5 | 14.5 | 24.4 |
| scalar throughput, `mul_2_2` (ns) | 0.363 | 0.36 | 0.367 | 0.367 | 1.8 | 0.379 | 0.382 | 0.384 | 0.978 |
| scalar throughput, `ball_add_1` (ns) | 1.48 | 1.48 | 1.37 | 1.36 | 7.66 | 2.8 | 3.39 | 3.41 | 4.39 |
| scalar throughput, `ball_mul_1` (ns) | 3.96 | 3.98 | 5.9 | 3.62 | 20.9 | 7.67 | 9.85 | 9.85 | 12.3 |
| scalar throughput, `double` addition (ns) | 0.108 | 0.107 | 0.31 | 0.163 | 0.335 | 0.101 | 0.121 | 0.121 | 0.061 |
| scalar throughput, `double` multiplication (ns) | 0.108 | 0.104 | 0.309 | 0.163 | 0.335 | 0.165 | 0.121 | 0.121 | 0.0611 |
| packed throughput, `ball_add_2` (ns) | 3.17 | 3.2 | 3.1 | 3.14 | 3.56 | 3.56 | 3.55 | 3.55 | 2.29 |
| packed throughput, `add_2_2` (ns) | 0.716 | 0.727 | 0.735 | 0.731 | 0.943 | 0.95 | 0.945 | 0.951 | 0.546 |
| packed throughput, `ball_mul_2` (ns) | 6.13 | 6.1 | 5.88 | 5.97 | 5.67 | 5.67 | 5.34 | 5.34 | 4.63 |
| packed throughput, `mul_2_2` (ns) | 0.378 | 0.377 | 0.368 | 0.363 | 0.387 | 0.378 | 0.396 | 0.383 | 0.228 |
| packed throughput, `ball_add_1` (ns) | 1.39 | 1.41 | 1.32 | 1.36 | 1.19 | 1.19 | 1.23 | 1.23 | 0.994 |
| packed throughput, `ball_mul_1` (ns) | 3.74 | 3.75 | 3.48 | 3.64 | 3.19 | 3.19 | 3.42 | 3.42 | 2.68 |
| packed throughput, `double` addition (ns) | 0.159 | 0.16 | 0.161 | 0.162 | 0.1 | 0.101 | 0.122 | 0.122 | 0.0829 |
| packed throughput, `double` multiplication (ns) | 0.16 | 0.156 | 0.16 | 0.162 | 0.101 | 0.101 | 0.121 | 0.121 | 0.0908 |
| scalar sum chain, `ball_add_2` (ns) | 9.74 | 9.74 | 9.87 | 9.88 | 13.6 | 13.6 | 11.9 | 11.9 | 11.1 |
| scalar sum chain, `add_2_2` (ns) | 7.66 | 7.64 | 7.98 | 8 | 10.2 | 10.2 | 10.1 | 10 | 4.93 |
| scalar prod chain, `ball_mul_2` (ns) | 20.7 | 20.7 | 20.4 | 20 | 27.5 | 27.5 | 24.2 | 24.2 | 25.4 |
| scalar prod chain, `mul_2_2` (ns) | 5.97 | 5.91 | 5.84 | 5.91 | 8.01 | 8.01 | 8.07 | 8.07 | 5.74 |
| scalar horner chain, `ball_mul_2+ball_add_2` (ns) | 30.7 | 30.7 | 30.5 | 30.4 | 39.9 | 39.2 | 34.2 | 34.2 | 33.7 |
| scalar horner chain, `mul_2_2+add_2_2` (ns) | 14.3 | 14.2 | 14.2 | 14.1 | 18.3 | 18.3 | 18.1 | 18.2 | 10.8 |
| scalar sum chain, `ball_add_1` (ns) | 9.69 | 9.63 | 9.75 | 9.81 | 11.6 | 11.6 | 10.8 | 10.8 | 7.36 |
| scalar product chain, `ball_mul_1` (ns) | 20.6 | 20.7 | 20.3 | 20.5 | 24.9 | 24.9 | 22.3 | 22.4 | 16.5 |
| scalar Horner, `ball_mul_1+ball_add_1` (ns) | 30.7 | 29.5 | 30.4 | 30.5 | 36.6 | 36.6 | 32.9 | 32.8 | 23.8 |
| scalar sum chain, `double` (ns) | 0.415 | 0.415 | 0.505 | 0.528 | 0.793 | 0.792 | 0.793 | 0.794 | 0.281 |
| scalar product chain, `double` (ns) | 0.8 | 0.8 | 0.801 | 0.801 | 0.794 | 0.792 | 0.792 | 0.792 | 0.544 |
| scalar Horner, `double` (ns) | 1.38 | 1.38 | 1.38 | 1.38 | 1.69 | 1.69 | 1.7 | 1.69 | 1.23 |

Ratios:

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| scalar throughput, `ball_add_2` / `add_2_2` | 4.57 | 4.68 | 4.25 | 4.25 | 3.51 | 8.21 | 9.54 | 9.57 | 19.90 |
| scalar throughput, `ball_mul_2` / `mul_2_2` | 17.61 | 17.80 | 16.23 | 16.30 | 13.11 | 33.76 | 37.95 | 37.70 | 24.94 |
| scalar throughput, `ball_add_1` / `double` addition | 13.75 | 13.84 | 4.42 | 8.37 | 22.87 | 27.82 | 27.95 | 28.09 | 72.01 |
| scalar throughput, `ball_mul_1` / `double` multiplication | 36.65 | 38.30 | 19.12 | 22.29 | 62.57 | 46.38 | 81.10 | 81.17 | 200.98 |
| scalar throughput, `ball_add_2` / `double` addition | 30.99 | 31.16 | 10.04 | 19.18 | 37.94 | 76.87 | 74.64 | 74.78 | 179.24 |
| scalar throughput, `ball_mul_2` / `double` multiplication | 59.21 | 61.67 | 19.31 | 36.82 | 70.58 | 77.39 | 119.36 | 119.19 | 399.67 |
| packed throughput, `ball_add_2` / `add_2_2` | 4.43 | 4.40 | 4.22 | 4.30 | 3.78 | 3.75 | 3.75 | 3.73 | 4.20 |
| packed throughput, `ball_mul_2` / `mul_2_2` | 16.21 | 16.18 | 15.97 | 16.43 | 14.68 | 15.00 | 13.48 | 13.96 | 20.28 |
| packed throughput, `ball_add_1` / `double` addition | 8.74 | 8.79 | 8.18 | 8.44 | 11.83 | 11.76 | 10.06 | 10.05 | 11.99 |
| packed throughput, `ball_mul_1` / `double` multiplication | 23.32 | 24.02 | 21.76 | 22.51 | 31.70 | 31.53 | 28.26 | 28.34 | 29.54 |
| packed throughput, `ball_add_2` / `double` addition | 19.89 | 20.01 | 19.20 | 19.44 | 35.54 | 35.23 | 29.07 | 29.05 | 27.60 |
| packed throughput, `ball_mul_2` / `double` multiplication | 38.21 | 39.04 | 36.84 | 36.89 | 56.44 | 56.14 | 44.03 | 44.21 | 51.02 |
| scalar sum chain, `ball_add_2` / `add_2_2` | 1.27 | 1.27 | 1.24 | 1.23 | 1.34 | 1.34 | 1.19 | 1.19 | 2.26 |
| scalar product chain, `ball_mul_2` / `mul_2_2` | 3.46 | 3.51 | 3.50 | 3.38 | 3.44 | 3.44 | 3.00 | 3.00 | 4.43 |
| scalar Horner, balls / 2 limbs | 2.15 | 2.15 | 2.15 | 2.16 | 2.19 | 2.15 | 1.89 | 1.89 | 3.13 |
| scalar sum chain, `ball_add_1` / `double` | 23.36 | 23.19 | 19.32 | 18.57 | 14.63 | 14.62 | 13.64 | 13.60 | 26.20 |
| scalar product chain, `ball_mul_1` / `double` | 25.74 | 25.85 | 25.32 | 25.62 | 31.40 | 31.51 | 28.19 | 28.25 | 30.40 |
| scalar tp, `ball_add_2`, full (a) / core | 1.24 | 1.24 | 1.19 | 1.20 | 1.19 | 1.17 | 1.08 | 1.08 | 1.39 |
| scalar tp, `ball_mul_2`, full (a) / core | 1.09 | 1.09 | 1.08 | 1.07 | 1.13 | 1.10 | 1.09 | 1.10 | 1.19 |
| scalar sum, `ball_add_2`, full (a) / core | 2.89 | 2.88 | 2.33 | 2.26 | 1.10 | 1.11 | 1.29 | 1.29 | 2.15 |
| scalar prod, `ball_mul_2`, full (a) / core | 1.56 | 1.55 | 1.31 | 1.29 | 1.00 | 1.01 | 0.95 | 0.95 | 1.38 |
| scalar horner, `ball_mul_2+ball_add_2`, full (a) / core | 1.96 | 1.93 | 1.62 | 1.04 | 1.09 | 1.16 | 1.08 | 1.08 | 1.74 |
| packed tp, `ball_add_2`, full (a) / core | 1.26 | 1.34 | 1.19 | 1.18 | 1.20 | 1.20 | 1.15 | 1.15 | 1.32 |
| packed tp, `ball_mul_2`, full (a) / core | 1.09 | 1.09 | 1.09 | 1.04 | 1.16 | 1.16 | 1.15 | 1.14 | 1.14 |
| packed sum, `ball_add_2`, full (a) / core | 2.72 | 2.72 | 2.34 | 2.33 | 1.75 | 1.75 | 1.63 | 1.63 | 2.05 |
| packed prod, `ball_mul_2`, full (a) / core | 1.48 | 1.51 | 1.70 | 1.72 | 1.33 | 1.32 | 1.27 | 1.27 | 1.43 |
| packed horner, `ball_mul_2+ball_add_2`, full (a) / core | 1.89 | 1.87 | 2.17 | 2.17 | 1.52 | 1.52 | 1.47 | 1.47 | 1.63 |
| scalar tp, `ball_add_2`, full (b) / core | 1.33 | 1.33 | 1.21 | 1.22 | 1.11 | 1.82 | 1.44 | 1.44 | 1.06 |
| scalar tp, `ball_mul_2`, full (b) / core | 1.33 | 1.32 | 1.40 | 1.38 | 1.08 | 2.00 | 1.27 | 1.28 | 1.03 |
| scalar sum, `ball_add_2`, full (b) / core | 1.01 | 1.00 | 1.06 | 1.03 | 1.09 | 1.10 | 1.06 | 1.06 | 1.08 |
| scalar prod, `ball_mul_2`, full (b) / core | 1.00 | 1.00 | 1.00 | 1.01 | 1.03 | 1.03 | 0.95 | 0.95 | 1.01 |
| scalar horner, `ball_mul_2+ball_add_2`, full (b) / core | 1.00 | 0.96 | 0.99 | 1.00 | 1.07 | 1.11 | 1.03 | 1.03 | 1.04 |

### 4. Kairn over the textbook baseline

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, `add_2_2`, core | 1.00 | 0.98 | 1.00 | 0.99 | 0.96 | 1.00 | 1.02 | 1.02 | 1.01 |
| throughput, `add_fast_2_2`, core | 1.04 | 1.00 | 1.01 | 0.97 | 1.00 | 1.00 | 1.00 | 1.01 | 1.00 |
| throughput, `add_2_2`, full (a) | 1.61 | 1.60 | 2.61 | 2.44 | 1.28 | 4.90 | 1.21 | 1.21 | 6.20 |
| throughput, `add_2_2`, full (b) | 2.08 | 2.07 | 2.21 | 2.16 | 1.17 | 4.67 | 4.57 | 4.57 | 4.32 |
| sum chain, `add_2_2`, core | 1.01 | 0.96 | 0.99 | 0.99 | 1.01 | 1.01 | 1.00 | 1.01 | 1.01 |
| sum chain, `add_fast_2_2`, core | 1.02 | 1.02 | 0.99 | 0.99 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| sum chain, `add_2_2`, full (a) | 1.44 | 1.41 | 1.08 | 1.07 | 1.04 | 1.04 | 1.11 | 1.12 | 1.78 |
| sum chain, `add_2_2`, full (b) | 1.03 | 1.00 | 1.05 | 1.04 | 1.04 | 1.04 | 1.00 | 1.01 | 1.06 |
| throughput, `mul_2_2`, core | 0.99 | 1.02 | 1.01 | 1.00 | 1.25 | 1.09 | 1.06 | 1.07 | 0.98 |
| throughput, `mul_2_2`, full (a) | 2.12 | 2.16 | 3.09 | 2.80 | 2.18 | 8.48 | 1.90 | 1.90 | 2.97 |
| throughput, `mul_2_2`, full (b) | 2.09 | 2.12 | 2.39 | 2.37 | 1.59 | 6.62 | 5.94 | 5.93 | 1.47 |
| product chain, `mul_2_2`, core | 1.00 | 1.03 | 0.99 | 1.00 | 1.08 | 1.08 | 1.09 | 1.09 | 1.10 |
| product chain, `mul_2_2`, full (a) | 1.35 | 1.40 | 1.01 | 1.02 | 1.11 | 1.11 | 1.10 | 1.10 | 1.70 |
| product chain, `mul_2_2`, full (b) | 0.99 | 1.03 | 1.03 | 1.03 | 1.11 | 1.11 | 1.10 | 1.10 | 1.11 |
| Horner, core | 1.00 | 1.00 | 1.00 | 1.04 | 1.05 | 1.05 | 1.04 | 1.04 | 1.04 |
| Horner, full (a) | 1.32 | 1.32 | 1.03 | 1.10 | 1.08 | 1.08 | 1.10 | 1.10 | 1.71 |
| Horner, full (b) | 1.00 | 0.99 | 0.97 | 1.07 | 1.05 | 1.05 | 1.05 | 1.05 | 1.10 |

MPFR at 106 bits over Kairn:

| Operation | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput, addition / `add_2_2` | 9.59 | 9.76 | 9.53 | 9.55 | 3.94 | 15.04 | 15.05 | 14.99 | — |
| throughput, multiplication / `mul_2_2` | 20.64 | 19.83 | 19.56 | 20.42 | 8.84 | 41.82 | 41.70 | 39.68 | — |
| sum chain / `add_2_2` | 0.91 | 0.88 | 0.84 | 0.87 | 1.41 | 1.39 | 1.37 | 1.38 | — |
| product chain / `mul_2_2` | 1.30 | 1.30 | 1.32 | 1.32 | 1.99 | 1.95 | 1.91 | 1.92 | — |
| Horner / 2 limbs | 0.87 | 0.87 | 0.88 | 0.88 | 1.64 | 1.69 | 1.63 | 1.62 | — |
| throughput, addition / `ball_add_2` | 2.10 | 2.09 | 2.25 | 2.25 | 1.12 | 1.83 | 1.58 | 1.57 | — |
| throughput, multiplication / `ball_mul_2` | 1.17 | 1.11 | 1.20 | 1.25 | 0.67 | 1.24 | 1.10 | 1.05 | — |

### Machine code of the throughput loops

| Function | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---|---|---|---|---|---|---|---|---|
| `kb_tp_mul_2_2__kairn` | 128-bit; 10 fma, 0 mul, 0 sel, 0 br | 128-bit; 10 fma, 0 mul, 0 sel, 0 br | 128-bit; 5 fma, 0 mul, 0 sel, 0 br | 128-bit; 5 fma, 0 mul, 0 sel, 0 br | scalar; 5 fma, 0 mul, 0 sel, 0 br | 256-bit; 5 fma, 0 mul, 0 sel, 0 br | 256-bit; 5 fma, 0 mul, 0 sel, 0 br | 256-bit; 5 fma, 0 mul, 0 sel, 0 br | scalar; 20 fma, 0 mul, 0 sel, 0 br |
| `kb_tp_mul_2_2__plain` | 128-bit; 3 fma, 2 mul, 0 sel, 0 br | 128-bit; 3 fma, 2 mul, 0 sel, 0 br | 128-bit; 3 fma, 2 mul, 0 sel, 0 br | 128-bit; 3 fma, 2 mul, 0 sel, 0 br | scalar; 3 fma, 2 mul, 0 sel, 0 br | 256-bit; 3 fma, 2 mul, 0 sel, 0 br | 256-bit; 3 fma, 2 mul, 0 sel, 0 br | 256-bit; 3 fma, 2 mul, 0 sel, 0 br | scalar; 12 fma, 8 mul, 0 sel, 0 br |
| `kb_tp_mul_2_2__full_sel` | 128-bit; 6 fma, 0 mul, 1 sel, 0 br | 128-bit; 6 fma, 0 mul, 1 sel, 0 br | scalar; 6 fma, 0 mul, 1 sel, 1 br | scalar; 6 fma, 0 mul, 1 sel, 2 br | scalar; 6 fma, 0 mul, 1 sel, 1 br | scalar; 6 fma, 0 mul, 1 sel, 2 br | 256-bit; 6 fma, 0 mul, 2 sel, 0 br | 256-bit; 6 fma, 0 mul, 2 sel, 0 br | scalar; 24 fma, 0 mul, 12 sel, 0 br |
| `kb_tp_mul_2_2__full_br` | scalar; 5 fma, 0 mul, 0 sel, 1 br | scalar; 5 fma, 0 mul, 0 sel, 4 br | scalar; 5 fma, 0 mul, 0 sel, 3 br | scalar; 5 fma, 0 mul, 0 sel, 3 br | scalar; 5 fma, 0 mul, 0 sel, 1 br | scalar; 5 fma, 0 mul, 0 sel, 1 br | scalar; 5 fma, 0 mul, 0 sel, 1 br | scalar; 5 fma, 0 mul, 0 sel, 1 br | scalar; 5 fma, 0 mul, 0 sel, 3 br |
| `kb_tp_mul_2_2__full_fabs` | 128-bit; 6 fma, 0 mul, 1 sel, 0 br | 128-bit; 6 fma, 0 mul, 1 sel, 0 br | scalar; 6 fma, 0 mul, 1 sel, 1 br | scalar; 6 fma, 0 mul, 1 sel, 2 br | scalar; 6 fma, 0 mul, 1 sel, 1 br | scalar; 6 fma, 0 mul, 1 sel, 2 br | 256-bit; 6 fma, 0 mul, 2 sel, 0 br | 256-bit; 6 fma, 0 mul, 2 sel, 0 br | — |
| `kb_tp_mul_2_2__full_inl` | 128-bit; 6 fma, 0 mul, 1 sel, 0 br | 128-bit; 6 fma, 0 mul, 1 sel, 0 br | scalar; 6 fma, 0 mul, 1 sel, 2 br | scalar; 6 fma, 0 mul, 1 sel, 2 br | scalar; 5 fma, 0 mul, 0 sel, 1 br | 256-bit; 6 fma, 0 mul, 3 sel, 0 br | 256-bit; 6 fma, 0 mul, 2 sel, 0 br | 256-bit; 6 fma, 0 mul, 2 sel, 0 br | — |
| `kb_tp_add_2_2__kairn` | 128-bit; 0 fma, 0 mul, 0 sel, 0 br | 128-bit; 0 fma, 0 mul, 0 sel, 0 br | 128-bit; 0 fma, 0 mul, 0 sel, 0 br | 128-bit; 0 fma, 0 mul, 0 sel, 0 br | scalar; 0 fma, 0 mul, 0 sel, 0 br | 256-bit; 0 fma, 0 mul, 0 sel, 0 br | 256-bit; 0 fma, 0 mul, 0 sel, 0 br | 256-bit; 0 fma, 0 mul, 0 sel, 0 br | 256-bit; 0 fma, 0 mul, 0 sel, 0 br |
| `kb_tp_add_2_2__full_sel` | 128-bit; 1 fma, 0 mul, 1 sel, 0 br | 128-bit; 1 fma, 0 mul, 1 sel, 0 br | scalar; 1 fma, 0 mul, 1 sel, 1 br | scalar; 1 fma, 0 mul, 1 sel, 2 br | scalar; 1 fma, 0 mul, 1 sel, 1 br | scalar; 1 fma, 0 mul, 1 sel, 2 br | 256-bit; 1 fma, 0 mul, 2 sel, 0 br | 256-bit; 1 fma, 0 mul, 2 sel, 0 br | scalar; 4 fma, 0 mul, 12 sel, 0 br |
| `kb_tp_add_2_2__full_br` | scalar; 0 fma, 0 mul, 0 sel, 1 br | scalar; 0 fma, 0 mul, 0 sel, 4 br | scalar; 0 fma, 0 mul, 0 sel, 3 br | scalar; 0 fma, 0 mul, 0 sel, 3 br | scalar; 0 fma, 0 mul, 0 sel, 1 br | scalar; 0 fma, 0 mul, 0 sel, 1 br | scalar; 0 fma, 0 mul, 0 sel, 1 br | scalar; 0 fma, 0 mul, 0 sel, 1 br | scalar; 0 fma, 0 mul, 0 sel, 3 br |
| `kb_tp_add_2_2__full_fabs` | 128-bit; 1 fma, 0 mul, 1 sel, 0 br | 128-bit; 1 fma, 0 mul, 1 sel, 0 br | scalar; 1 fma, 0 mul, 1 sel, 1 br | scalar; 1 fma, 0 mul, 1 sel, 2 br | scalar; 1 fma, 0 mul, 1 sel, 1 br | scalar; 1 fma, 0 mul, 1 sel, 2 br | 256-bit; 1 fma, 0 mul, 2 sel, 0 br | 256-bit; 1 fma, 0 mul, 2 sel, 0 br | — |
| `kb_tp_add_2_2__full_inl` | 128-bit; 1 fma, 0 mul, 1 sel, 0 br | 128-bit; 1 fma, 0 mul, 1 sel, 0 br | scalar; 1 fma, 0 mul, 1 sel, 2 br | scalar; 1 fma, 0 mul, 1 sel, 2 br | scalar; 0 fma, 0 mul, 0 sel, 1 br | 256-bit; 1 fma, 0 mul, 3 sel, 0 br | 256-bit; 1 fma, 0 mul, 2 sel, 0 br | 256-bit; 1 fma, 0 mul, 2 sel, 0 br | — |
| `kb_tp_ball_add_2__kairn` | 128-bit; 1 fma, 0 mul, 7 sel, 0 br | 128-bit; 1 fma, 0 mul, 7 sel, 0 br | 128-bit; 1 fma, 0 mul, 11 sel, 0 br | 128-bit; 1 fma, 0 mul, 11 sel, 0 br | scalar; 1 fma, 0 mul, 8 sel, 2 br | 128-bit; 1 fma, 0 mul, 11 sel, 0 br | 128-bit; 1 fma, 0 mul, 10 sel, 0 br | 128-bit; 1 fma, 0 mul, 10 sel, 0 br | scalar; 1 fma, 0 mul, 7 sel, 0 br |
| `kb_tp_ball_add_2__full_sel` | 128-bit; 1 fma, 0 mul, 11 sel, 0 br | 128-bit; 1 fma, 0 mul, 11 sel, 0 br | 128-bit; 1 fma, 0 mul, 15 sel, 0 br | 128-bit; 1 fma, 0 mul, 15 sel, 0 br | scalar; 1 fma, 0 mul, 11 sel, 5 br | 128-bit; 1 fma, 0 mul, 15 sel, 0 br | 128-bit; 1 fma, 0 mul, 14 sel, 0 br | 128-bit; 1 fma, 0 mul, 14 sel, 0 br | scalar; 1 fma, 0 mul, 13 sel, 2 br |
| `kb_tp_ball_add_2__full_br` | scalar; 1 fma, 0 mul, 8 sel, 4 br | scalar; 1 fma, 0 mul, 8 sel, 4 br | scalar; 1 fma, 0 mul, 6 sel, 5 br | scalar; 1 fma, 0 mul, 6 sel, 5 br | scalar; 1 fma, 0 mul, 8 sel, 4 br | scalar; 1 fma, 0 mul, 8 sel, 4 br | scalar; 1 fma, 0 mul, 8 sel, 2 br | scalar; 1 fma, 0 mul, 8 sel, 2 br | scalar; 1 fma, 0 mul, 7 sel, 2 br |
| `kb_tp_ball_mul_2__kairn` | 128-bit; 9 fma, 0 mul, 20 sel, 0 br | 128-bit; 9 fma, 0 mul, 20 sel, 0 br | 128-bit; 9 fma, 0 mul, 31 sel, 0 br | 128-bit; 9 fma, 0 mul, 31 sel, 0 br | scalar; 9 fma, 0 mul, 22 sel, 6 br | 128-bit; 9 fma, 0 mul, 31 sel, 0 br | 128-bit; 9 fma, 0 mul, 28 sel, 0 br | 128-bit; 9 fma, 0 mul, 28 sel, 0 br | scalar; 9 fma, 0 mul, 20 sel, 0 br |

### Every function

| Function | M3, Apple clang -O2 | M3, Apple clang -O3 | M3, GCC 16 -O2 | M3, GCC 16 -O3 | Zen 2, GCC 13 -O2 | Zen 2, GCC 13 -O3 | Zen 2, Clang 18 -O2 | Zen 2, Clang 18 -O3 | i5, MSVC /O2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `scalar/tp/two_prod/kairn` | 0.193 (1%) | 0.187 (4%) | 0.348 (1%) | 0.188 (1%) | 0.634 (0%) | 0.236 (0%) | 0.183 (3%) | 0.165 (0%) | 0.441 (0%) |
| `scalar/tp/two_prod/plain` | 0.193 (0%) | 0.187 (3%) | 0.347 (1%) | 0.19 (1%) | 0.62 (0%) | 0.179 (1%) | 0.162 (0%) | 0.166 (0%) | 0.659 (1%) |
| `scalar/tp/mul_2_1/kairn` | 0.256 (1%) | 0.256 (1%) | 0.301 (1%) | 0.298 (2%) | 1.22 (1%) | 0.278 (1%) | 0.276 (0%) | 0.274 (2%) | 0.644 (1%) |
| `scalar/tp/mul_2_1/plain` | 0.252 (1%) | 0.248 (2%) | 0.478 (1%) | 0.261 (5%) | 1.04 (0%) | 0.258 (1%) | 0.257 (0%) | 0.258 (0%) | 0.745 (1%) |
| `scalar/tp/mul_2_2/kairn` | 0.363 (1%) | 0.36 (2%) | 0.367 (1%) | 0.367 (1%) | 1.8 (0%) | 0.379 (1%) | 0.382 (1%) | 0.384 (1%) | 0.978 (0%) |
| `scalar/tp/mul_2_2/plain` | 0.366 (1%) | 0.364 (1%) | 0.367 (1%) | 0.367 (1%) | 1.45 (1%) | 0.349 (0%) | 0.358 (1%) | 0.36 (1%) | 0.997 (1%) |
| `scalar/tp/mul_2_2/textbook` | 0.368 (1%) | 0.352 (5%) | 0.365 (1%) | 0.367 (1%) | 1.45 (1%) | 0.348 (1%) | 0.36 (1%) | 0.36 (1%) | 0.997 (1%) |
| `scalar/tp/mul_2_2/full_sel` | 0.781 (1%) | 0.762 (4%) | 1.13 (1%) | 1.03 (1%) | 3.15 (0%) | 2.95 (0%) | 0.684 (0%) | 0.684 (0%) | 2.96 (0%) |
| `scalar/tp/mul_2_2/full_br` | 0.768 (1%) | 0.746 (4%) | 0.871 (1%) | 0.87 (1%) | 2.3 (0%) | 2.31 (0%) | 2.14 (0%) | 2.14 (0%) | 1.46 (0%) |
| `scalar/tp/mul_2_2/full_fabs` | 0.78 (1%) | 0.754 (4%) | 1.13 (1%) | 1.02 (1%) | 3.11 (0%) | 2.95 (0%) | 0.684 (0%) | 0.683 (0%) | — |
| `scalar/tp/mul_2_2/full_inl` | 0.706 (1%) | 0.691 (3%) | 0.817 (1%) | 0.811 (1%) | 2.3 (0%) | 0.749 (0%) | 0.682 (0%) | 0.682 (0%) | — |
| `scalar/tp/add_2_2/kairn` | 0.73 (1%) | 0.714 (3%) | 0.734 (1%) | 0.734 (1%) | 3.62 (4%) | 0.944 (1%) | 0.949 (0%) | 0.948 (0%) | 0.549 (1%) |
| `scalar/tp/add_2_2/textbook` | 0.727 (1%) | 0.731 (1%) | 0.733 (1%) | 0.739 (1%) | 3.76 (0%) | 0.944 (1%) | 0.93 (1%) | 0.93 (2%) | 0.546 (1%) |
| `scalar/tp/add_2_2/full_sel` | 1.17 (1%) | 1.17 (1%) | 1.91 (0%) | 1.8 (1%) | 4.8 (1%) | 4.63 (1%) | 1.13 (0%) | 1.12 (1%) | 3.39 (0%) |
| `scalar/tp/add_2_2/full_br` | 1.51 (1%) | 1.51 (1%) | 1.62 (1%) | 1.6 (1%) | 4.41 (0%) | 4.41 (0%) | 4.25 (0%) | 4.25 (0%) | 2.36 (0%) |
| `scalar/tp/add_2_2/full_fabs` | 1.16 (1%) | 1.17 (1%) | 1.9 (1%) | 1.8 (1%) | 4.7 (1%) | 4.48 (0%) | 1.13 (0%) | 1.12 (1%) | — |
| `scalar/tp/add_2_2/full_inl` | 1.08 (1%) | 1.08 (1%) | 1.6 (2%) | 1.57 (3%) | 4.41 (0%) | 1.15 (1%) | 1.13 (0%) | 1.13 (0%) | — |
| `scalar/tp/add_fast_2_2/kairn` | 0.399 (1%) | 0.386 (1%) | 0.404 (1%) | 0.389 (4%) | 2.19 (1%) | 0.542 (1%) | 0.544 (1%) | 0.546 (1%) | 0.311 (1%) |
| `scalar/tp/add_fast_2_2/textbook` | 0.383 (2%) | 0.385 (1%) | 0.402 (1%) | 0.402 (1%) | 2.19 (0%) | 0.541 (1%) | 0.544 (1%) | 0.542 (1%) | 0.31 (0%) |
| `scalar/tp/ball_add_2/kairn` | 3.33 (1%) | 3.34 (1%) | 3.12 (1%) | 3.12 (0%) | 12.7 (0%) | 7.75 (0%) | 9.06 (0%) | 9.07 (0%) | 10.9 (0%) |
| `scalar/tp/ball_add_2/full_sel` | 4.13 (1%) | 4.13 (1%) | 3.69 (1%) | 3.73 (1%) | 15.1 (0%) | 9.09 (1%) | 9.83 (0%) | 9.81 (0%) | 15.2 (0%) |
| `scalar/tp/ball_add_2/full_br` | 4.44 (1%) | 4.45 (1%) | 3.76 (2%) | 3.81 (1%) | 14.1 (0%) | 14.1 (0%) | 13 (0%) | 13 (0%) | 11.6 (0%) |
| `scalar/tp/ball_mul_2/kairn` | 6.4 (1%) | 6.41 (1%) | 5.96 (1%) | 5.99 (1%) | 23.6 (0%) | 12.8 (0%) | 14.5 (0%) | 14.5 (0%) | 24.4 (0%) |
| `scalar/tp/ball_mul_2/plain` | 6.37 (1%) | 6.37 (1%) | 5.93 (1%) | 5.98 (1%) | 23.1 (0%) | 12.1 (0%) | 13.9 (0%) | 13.9 (0%) | 24.4 (0%) |
| `scalar/tp/ball_mul_2/full_sel` | 7 (1%) | 7 (1%) | 6.44 (1%) | 6.41 (1%) | 26.6 (0%) | 14.1 (0%) | 15.9 (0%) | 15.9 (0%) | 29.1 (0%) |
| `scalar/tp/ball_mul_2/full_br` | 8.5 (1%) | 8.49 (1%) | 8.32 (1%) | 8.29 (2%) | 25.5 (0%) | 25.5 (0%) | 18.5 (0%) | 18.5 (0%) | 25.1 (0%) |
| `scalar/tp/ball_add_1/kairn` | 1.48 (1%) | 1.48 (1%) | 1.37 (2%) | 1.36 (2%) | 7.66 (0%) | 2.8 (0%) | 3.39 (0%) | 3.41 (0%) | 4.39 (0%) |
| `scalar/tp/ball_mul_1/kairn` | 3.96 (1%) | 3.98 (1%) | 5.9 (1%) | 3.62 (1%) | 20.9 (0%) | 7.67 (0%) | 9.85 (0%) | 9.85 (0%) | 12.3 (0%) |
| `scalar/tp/add_1_1/kairn` | 0.109 (1%) | 0.109 (1%) | 0.309 (1%) | 0.162 (1%) | 0.336 (3%) | 0.165 (0%) | 0.121 (0%) | 0.121 (0%) | 0.0605 (2%) |
| `scalar/tp/add_1_1/double` | 0.108 (2%) | 0.107 (2%) | 0.31 (1%) | 0.163 (1%) | 0.335 (1%) | 0.101 (2%) | 0.121 (0%) | 0.121 (0%) | 0.061 (0%) |
| `scalar/tp/mul_1_1/kairn` | 0.107 (1%) | 0.105 (3%) | 0.31 (1%) | 0.163 (1%) | 0.632 (1%) | 0.1 (2%) | 0.122 (0%) | 0.121 (0%) | 0.103 (18%) |
| `scalar/tp/mul_1_1/double` | 0.108 (1%) | 0.104 (6%) | 0.309 (1%) | 0.163 (1%) | 0.335 (2%) | 0.165 (0%) | 0.121 (0%) | 0.121 (0%) | 0.0611 (0%) |
| `scalar/sum/add_2_2/kairn` | 7.66 (5%) | 7.64 (5%) | 7.98 (1%) | 8 (1%) | 10.2 (0%) | 10.2 (0%) | 10.1 (0%) | 10 (0%) | 4.93 (0%) |
| `scalar/sum/add_2_2/textbook` | 7.61 (5%) | 7.95 (1%) | 8.05 (1%) | 8.05 (1%) | 10 (0%) | 10 (0%) | 10 (0%) | 9.94 (0%) | 4.88 (0%) |
| `scalar/sum/add_2_2/full_sel` | 10.9 (3%) | 11.2 (1%) | 8.67 (1%) | 8.61 (1%) | 10.4 (0%) | 10.4 (0%) | 11.1 (0%) | 11.1 (0%) | 8.67 (0%) |
| `scalar/sum/add_2_2/full_br` | 7.87 (1%) | 7.92 (1%) | 8.49 (1%) | 8.41 (1%) | 10.4 (0%) | 10.4 (0%) | 10 (0%) | 10 (0%) | 5.18 (0%) |
| `scalar/sum/add_2_2/full_fabs` | 11.3 (1%) | 11.3 (1%) | 8.7 (1%) | 8.65 (1%) | 10.7 (0%) | 10.7 (0%) | 11.1 (0%) | 11.1 (0%) | — |
| `scalar/sum/add_2_2/full_inl` | 11.2 (1%) | 11.3 (1%) | 7.99 (1%) | 8.04 (1%) | 10.3 (0%) | 10.3 (0%) | 10 (0%) | 10 (0%) | — |
| `scalar/sum/add_fast_2_2/kairn` | 5.01 (1%) | 4.98 (1%) | 4.99 (1%) | 4.99 (1%) | 6.54 (0%) | 6.53 (0%) | 6.36 (0%) | 6.36 (0%) | 3.11 (0%) |
| `scalar/sum/add_fast_2_2/textbook` | 4.89 (1%) | 4.87 (1%) | 5.01 (1%) | 5.03 (1%) | 6.53 (0%) | 6.54 (0%) | 6.37 (0%) | 6.37 (0%) | 3.11 (0%) |
| `scalar/sum/ball_add_2/kairn` | 9.74 (1%) | 9.74 (1%) | 9.87 (1%) | 9.88 (1%) | 13.6 (0%) | 13.6 (0%) | 11.9 (0%) | 11.9 (0%) | 11.1 (0%) |
| `scalar/sum/ball_add_2/full_sel` | 28.2 (1%) | 28.1 (1%) | 23 (1%) | 22.4 (3%) | 14.9 (0%) | 15.1 (0%) | 15.4 (0%) | 15.3 (0%) | 24 (0%) |
| `scalar/sum/ball_add_2/full_br` | 9.8 (1%) | 9.76 (1%) | 10.4 (1%) | 10.2 (3%) | 14.8 (0%) | 14.9 (0%) | 12.7 (0%) | 12.7 (0%) | 12 (0%) |
| `scalar/sum/ball_add_1/kairn` | 9.69 (1%) | 9.63 (1%) | 9.75 (2%) | 9.81 (1%) | 11.6 (0%) | 11.6 (0%) | 10.8 (0%) | 10.8 (0%) | 7.36 (0%) |
| `scalar/sum/add_1_1/kairn` | 0.412 (1%) | 0.411 (1%) | 0.505 (5%) | 0.528 (1%) | 0.794 (0%) | 0.794 (0%) | 0.793 (0%) | 0.795 (0%) | 0.281 (0%) |
| `scalar/sum/add_1_1/double` | 0.415 (1%) | 0.415 (1%) | 0.505 (5%) | 0.528 (1%) | 0.793 (0%) | 0.792 (0%) | 0.793 (0%) | 0.794 (0%) | 0.281 (0%) |
| `scalar/prod/two_prod/kairn` | 0.923 (1%) | 0.923 (1%) | 0.996 (2%) | 0.993 (2%) | 1.67 (3%) | 1.7 (0%) | 1.53 (0%) | 1.53 (0%) | 1.54 (0%) |
| `scalar/prod/two_prod/plain` | 0.917 (1%) | 0.917 (1%) | 0.999 (1%) | 0.988 (2%) | 1.1 (1%) | 1.1 (0%) | 0.982 (0%) | 0.975 (1%) | 0.834 (1%) |
| `scalar/prod/mul_2_1/kairn` | 3.73 (1%) | 3.73 (1%) | 3.75 (1%) | 3.74 (1%) | 5.3 (0%) | 5.31 (0%) | 5.31 (0%) | 5.3 (0%) | 4.81 (0%) |
| `scalar/prod/mul_2_1/plain` | 3.75 (1%) | 3.74 (1%) | 3.74 (1%) | 3.75 (1%) | 4.71 (0%) | 4.71 (0%) | 4.72 (0%) | 4.72 (0%) | 4.29 (0%) |
| `scalar/prod/mul_2_2/kairn` | 5.97 (1%) | 5.91 (2%) | 5.84 (2%) | 5.91 (1%) | 8.01 (0%) | 8.01 (0%) | 8.07 (0%) | 8.07 (0%) | 5.74 (0%) |
| `scalar/prod/mul_2_2/plain` | 5.97 (1%) | 5.7 (5%) | 5.89 (1%) | 5.91 (1%) | 7.4 (0%) | 7.41 (0%) | 7.41 (0%) | 7.41 (0%) | 5.21 (0%) |
| `scalar/prod/mul_2_2/textbook` | 5.98 (1%) | 5.74 (5%) | 5.92 (1%) | 5.92 (1%) | 7.41 (0%) | 7.41 (0%) | 7.41 (0%) | 7.41 (0%) | 5.21 (0%) |
| `scalar/prod/mul_2_2/full_sel` | 8.07 (1%) | 8.02 (1%) | 5.97 (1%) | 6.01 (1%) | 8.21 (0%) | 8.2 (0%) | 8.13 (0%) | 8.13 (0%) | 8.85 (0%) |
| `scalar/prod/mul_2_2/full_br` | 5.93 (1%) | 5.91 (1%) | 6.11 (2%) | 6.1 (1%) | 8.22 (0%) | 8.22 (0%) | 8.18 (0%) | 8.17 (0%) | 5.78 (0%) |
| `scalar/prod/mul_2_2/full_fabs` | 8.04 (1%) | 8.06 (1%) | 5.96 (1%) | 6.01 (1%) | 8.16 (0%) | 8.15 (0%) | 8.13 (0%) | 8.13 (0%) | — |
| `scalar/prod/mul_2_2/full_inl` | 8.01 (1%) | 8.05 (1%) | 6.07 (1%) | 6.09 (1%) | 8.31 (0%) | 8.3 (0%) | 8.07 (0%) | 8.08 (0%) | — |
| `scalar/prod/ball_mul_2/kairn` | 20.7 (1%) | 20.7 (1%) | 20.4 (1%) | 20 (3%) | 27.5 (0%) | 27.5 (0%) | 24.2 (0%) | 24.2 (0%) | 25.4 (0%) |
| `scalar/prod/ball_mul_2/plain` | 21.5 (1%) | 21.5 (1%) | 20.4 (1%) | 20.3 (2%) | 26.3 (0%) | 26.3 (0%) | 23.6 (0%) | 23.6 (0%) | 25.1 (0%) |
| `scalar/prod/ball_mul_2/full_sel` | 32.2 (1%) | 32 (1%) | 26.8 (1%) | 25.8 (5%) | 27.6 (0%) | 27.8 (0%) | 23 (0%) | 23 (0%) | 35.1 (0%) |
| `scalar/prod/ball_mul_2/full_br` | 20.7 (1%) | 20.7 (1%) | 20.5 (3%) | 20.1 (5%) | 28.4 (0%) | 28.3 (0%) | 23 (0%) | 23 (0%) | 25.6 (0%) |
| `scalar/prod/ball_mul_1/kairn` | 20.6 (1%) | 20.7 (1%) | 20.3 (1%) | 20.5 (1%) | 24.9 (0%) | 24.9 (0%) | 22.3 (0%) | 22.4 (0%) | 16.5 (0%) |
| `scalar/prod/mul_1_1/kairn` | 0.804 (1%) | 0.805 (1%) | 0.8 (1%) | 0.804 (1%) | 1.32 (0%) | 1.31 (0%) | 1.31 (0%) | 1.31 (0%) | 0.544 (0%) |
| `scalar/prod/mul_1_1/double` | 0.8 (2%) | 0.8 (2%) | 0.801 (1%) | 0.801 (1%) | 0.794 (0%) | 0.792 (0%) | 0.792 (0%) | 0.792 (0%) | 0.544 (0%) |
| `scalar/horner/mul_2_2+add_2_2/kairn` | 14.3 (1%) | 14.2 (1%) | 14.2 (1%) | 14.1 (1%) | 18.3 (0%) | 18.3 (0%) | 18.1 (0%) | 18.2 (0%) | 10.8 (0%) |
| `scalar/horner/mul_2_2+add_2_2/plain` | 14.2 (1%) | 14.2 (1%) | 14.2 (1%) | 13.5 (5%) | 17.6 (0%) | 17.6 (0%) | 17.6 (0%) | 17.6 (0%) | 10.3 (0%) |
| `scalar/horner/mul_2_2+add_2_2/textbook` | 14.2 (1%) | 14.3 (1%) | 14.2 (1%) | 13.5 (6%) | 17.4 (0%) | 17.3 (0%) | 17.5 (0%) | 17.5 (0%) | 10.3 (0%) |
| `scalar/horner/mul_2_2+add_2_2/full_sel` | 18.7 (1%) | 18.8 (1%) | 14.6 (2%) | 14.9 (1%) | 18.7 (0%) | 18.7 (0%) | 19.2 (0%) | 19.2 (0%) | 17.7 (0%) |
| `scalar/horner/mul_2_2+add_2_2/full_br` | 14.2 (1%) | 14.1 (1%) | 13.8 (6%) | 14.5 (1%) | 18.3 (0%) | 18.3 (0%) | 18.3 (0%) | 18.3 (0%) | 11.3 (0%) |
| `scalar/horner/mul_2_2+add_2_2/full_fabs` | 18.8 (1%) | 18.8 (1%) | 14.6 (3%) | 14.7 (1%) | 18.5 (0%) | 18.5 (1%) | 19.2 (0%) | 19.2 (0%) | — |
| `scalar/horner/mul_2_2+add_2_2/full_inl` | 18.7 (1%) | 18.8 (1%) | 14.6 (1%) | 14.5 (1%) | 18.5 (0%) | 18.5 (0%) | 18.3 (0%) | 18.3 (0%) | — |
| `scalar/horner/ball_mul_2+ball_add_2/kairn` | 30.7 (1%) | 30.7 (1%) | 30.5 (1%) | 30.4 (1%) | 39.9 (0%) | 39.2 (0%) | 34.2 (0%) | 34.2 (0%) | 33.7 (0%) |
| `scalar/horner/ball_mul_2+ball_add_2/plain` | 30.5 (2%) | 30.8 (1%) | 30.2 (2%) | 30.5 (1%) | 39.3 (0%) | 38.6 (0%) | 33.6 (0%) | 33.6 (0%) | 33.3 (0%) |
| `scalar/horner/ball_mul_2+ball_add_2/full_sel` | 60.1 (1%) | 59.4 (2%) | 49.5 (2%) | 31.7 (1%) | 43.4 (0%) | 45.6 (0%) | 37 (0%) | 37.1 (0%) | 58.5 (0%) |
| `scalar/horner/ball_mul_2+ball_add_2/full_br` | 30.8 (1%) | 29.4 (5%) | 30.2 (2%) | 30.5 (1%) | 42.8 (0%) | 43.4 (0%) | 35.4 (0%) | 35.4 (0%) | 35.1 (0%) |
| `scalar/horner/ball_mul_1+ball_add_1/kairn` | 30.7 (1%) | 29.5 (5%) | 30.4 (1%) | 30.5 (1%) | 36.6 (0%) | 36.6 (0%) | 32.9 (0%) | 32.8 (0%) | 23.8 (0%) |
| `scalar/horner/mul_1_1+add_1_1/kairn` | 1.38 (1%) | 1.38 (1%) | 1.38 (1%) | 1.37 (1%) | 2.26 (0%) | 2.26 (0%) | 2.26 (0%) | 2.26 (0%) | 1.23 (0%) |
| `scalar/horner/mul_1_1+add_1_1/double` | 1.38 (1%) | 1.38 (1%) | 1.38 (1%) | 1.38 (1%) | 1.69 (0%) | 1.69 (0%) | 1.7 (0%) | 1.69 (0%) | 1.23 (0%) |
| `packed/tp/two_prod/kairn` | 0.194 (1%) | 0.189 (1%) | 0.184 (3%) | 0.189 (1%) | 0.258 (0%) | 0.237 (0%) | 0.167 (0%) | 0.168 (0%) | 0.114 (18%) |
| `packed/tp/two_prod/plain` | 0.189 (1%) | 0.189 (1%) | 0.184 (7%) | 0.19 (1%) | 0.179 (1%) | 0.207 (3%) | 0.16 (0%) | 0.161 (1%) | 0.113 (5%) |
| `packed/tp/mul_2_1/kairn` | 0.299 (1%) | 0.272 (1%) | 0.273 (1%) | 0.272 (1%) | 0.277 (1%) | 0.278 (1%) | 0.276 (1%) | 0.276 (1%) | 0.173 (6%) |
| `packed/tp/mul_2_1/plain` | 0.272 (1%) | 0.272 (1%) | 0.27 (1%) | 0.264 (3%) | 0.257 (1%) | 0.258 (0%) | 0.257 (0%) | 0.256 (1%) | 0.18 (5%) |
| `packed/tp/mul_2_2/kairn` | 0.378 (1%) | 0.377 (1%) | 0.368 (1%) | 0.363 (2%) | 0.387 (3%) | 0.378 (0%) | 0.396 (3%) | 0.383 (1%) | 0.228 (0%) |
| `packed/tp/mul_2_2/plain` | 0.369 (2%) | 0.365 (1%) | 0.364 (1%) | 0.366 (1%) | 0.347 (1%) | 0.347 (0%) | 0.359 (1%) | 0.359 (1%) | 0.189 (0%) |
| `packed/tp/mul_2_2/full_sel` | 0.745 (1%) | 0.745 (1%) | 0.626 (1%) | 0.628 (1%) | 0.76 (1%) | 0.759 (1%) | 0.684 (0%) | 0.684 (0%) | 0.471 (0%) |
| `packed/tp/add_2_2/kairn` | 0.716 (3%) | 0.727 (1%) | 0.735 (1%) | 0.731 (2%) | 0.943 (1%) | 0.95 (0%) | 0.945 (1%) | 0.951 (0%) | 0.546 (0%) |
| `packed/tp/add_2_2/full_sel` | 1.13 (1%) | 1.12 (1%) | 0.991 (1%) | 0.981 (3%) | 1.18 (0%) | 1.18 (1%) | 1.13 (0%) | 1.13 (0%) | 0.7 (0%) |
| `packed/tp/add_fast_2_2/kairn` | 0.402 (1%) | 0.401 (1%) | 0.398 (1%) | 0.387 (4%) | 0.544 (1%) | 0.542 (1%) | 0.543 (1%) | 0.547 (1%) | 0.31 (0%) |
| `packed/tp/ball_add_2/kairn` | 3.17 (1%) | 3.2 (1%) | 3.1 (2%) | 3.14 (1%) | 3.56 (1%) | 3.56 (1%) | 3.55 (0%) | 3.55 (0%) | 2.29 (0%) |
| `packed/tp/ball_add_2/full_sel` | 4 (8%) | 4.3 (1%) | 3.69 (1%) | 3.71 (1%) | 4.29 (0%) | 4.29 (0%) | 4.09 (0%) | 4.1 (0%) | 3.02 (0%) |
| `packed/tp/ball_mul_2/kairn` | 6.13 (1%) | 6.1 (1%) | 5.88 (2%) | 5.97 (1%) | 5.67 (0%) | 5.67 (0%) | 5.34 (0%) | 5.34 (0%) | 4.63 (0%) |
| `packed/tp/ball_mul_2/plain` | 6.13 (1%) | 6.1 (1%) | 5.88 (1%) | 5.94 (1%) | 5.38 (0%) | 5.38 (0%) | 5.07 (0%) | 5.08 (0%) | 4.6 (0%) |
| `packed/tp/ball_mul_2/full_sel` | 6.66 (1%) | 6.66 (1%) | 6.39 (1%) | 6.23 (4%) | 6.56 (0%) | 6.56 (0%) | 6.11 (0%) | 6.11 (0%) | 5.26 (0%) |
| `packed/tp/ball_add_1/kairn` | 1.39 (2%) | 1.41 (1%) | 1.32 (5%) | 1.36 (2%) | 1.19 (1%) | 1.19 (1%) | 1.23 (0%) | 1.23 (0%) | 0.994 (0%) |
| `packed/tp/ball_mul_1/kairn` | 3.74 (2%) | 3.75 (1%) | 3.48 (6%) | 3.64 (1%) | 3.19 (0%) | 3.19 (0%) | 3.42 (0%) | 3.42 (0%) | 2.68 (1%) |
| `packed/tp/add_1_1/kairn` | 0.159 (3%) | 0.16 (2%) | 0.161 (2%) | 0.162 (1%) | 0.1 (1%) | 0.101 (1%) | 0.122 (0%) | 0.122 (1%) | 0.0829 (28%) |
| `packed/tp/mul_1_1/kairn` | 0.159 (4%) | 0.156 (6%) | 0.162 (1%) | 0.162 (1%) | 0.163 (0%) | 0.0995 (1%) | 0.121 (0%) | 0.122 (0%) | 0.0983 (20%) |
| `packed/tp/mul_1_1/double` | 0.16 (2%) | 0.156 (4%) | 0.16 (2%) | 0.162 (1%) | 0.101 (1%) | 0.101 (1%) | 0.121 (0%) | 0.121 (0%) | 0.0908 (30%) |
| `packed/sum/add_2_2/kairn` | 7.68 (1%) | 7.71 (1%) | 7.75 (1%) | 7.79 (1%) | 9.89 (0%) | 9.9 (0%) | 9.85 (0%) | 9.85 (0%) | 4.74 (0%) |
| `packed/sum/add_2_2/full_sel` | 9.61 (1%) | 9.63 (1%) | 9.81 (3%) | 10 (1%) | 11.6 (0%) | 11.7 (0%) | 10.9 (0%) | 11 (0%) | 7.32 (0%) |
| `packed/sum/ball_add_2/kairn` | 9.38 (1%) | 9.37 (1%) | 9.26 (2%) | 9.31 (1%) | 14.1 (0%) | 14.1 (0%) | 13.5 (0%) | 13.5 (0%) | 9.83 (0%) |
| `packed/sum/ball_add_2/full_sel` | 25.5 (1%) | 25.5 (1%) | 21.6 (1%) | 21.7 (1%) | 24.8 (0%) | 24.7 (0%) | 21.9 (1%) | 21.9 (1%) | 20.1 (0%) |
| `packed/sum/add_1_1/kairn` | 0.454 (1%) | 0.454 (1%) | 0.448 (1%) | 0.455 (1%) | 0.622 (1%) | 0.622 (1%) | 0.483 (0%) | 0.483 (0%) | 0.259 (2%) |
| `packed/prod/mul_2_2/kairn` | 5.59 (0%) | 5.55 (1%) | 5.55 (1%) | 5.54 (1%) | 7.68 (0%) | 7.69 (0%) | 7.73 (0%) | 7.74 (0%) | 4.19 (0%) |
| `packed/prod/mul_2_2/plain` | 5.58 (1%) | 5.55 (1%) | 5.57 (1%) | 5.58 (1%) | 7.11 (0%) | 7.11 (0%) | 7.12 (0%) | 7.12 (0%) | 4.18 (0%) |
| `packed/prod/mul_2_2/full_sel` | 7.34 (1%) | 7 (6%) | 6.65 (2%) | 6.67 (1%) | 8.3 (0%) | 8.29 (0%) | 8.2 (0%) | 8.2 (0%) | 6.37 (0%) |
| `packed/prod/ball_mul_2/kairn` | 19.1 (1%) | 18.4 (4%) | 13.4 (1%) | 13.4 (1%) | 22.4 (0%) | 22.4 (0%) | 20.7 (0%) | 20.8 (0%) | 19 (0%) |
| `packed/prod/ball_mul_2/plain` | 19.1 (1%) | 19 (1%) | 13.4 (1%) | 13.4 (1%) | 21.2 (0%) | 21.2 (0%) | 19.5 (0%) | 19.5 (0%) | 18.9 (0%) |
| `packed/prod/ball_mul_2/full_sel` | 28.2 (1%) | 27.8 (2%) | 22.8 (1%) | 23.1 (1%) | 29.7 (0%) | 29.7 (0%) | 26.3 (0%) | 26.3 (0%) | 27.2 (0%) |
| `packed/prod/mul_1_1/kairn` | 0.647 (3%) | 0.645 (3%) | 0.655 (1%) | 0.653 (1%) | 0.925 (0%) | 0.925 (0%) | 0.772 (0%) | 0.772 (0%) | 0.434 (1%) |
| `packed/prod/mul_1_1/double` | 0.642 (3%) | 0.656 (1%) | 0.653 (1%) | 0.66 (2%) | 0.622 (1%) | 0.624 (4%) | 0.474 (0%) | 0.474 (0%) | 0.437 (1%) |
| `packed/horner/mul_2_2+add_2_2/kairn` | 13.8 (2%) | 14 (1%) | 13.8 (1%) | 13.8 (1%) | 18.2 (0%) | 18.2 (0%) | 17.9 (0%) | 17.9 (0%) | 9.62 (1%) |
| `packed/horner/mul_2_2+add_2_2/plain` | 14 (1%) | 13.9 (1%) | 13.8 (1%) | 13.8 (1%) | 17.4 (0%) | 17.4 (0%) | 17.4 (0%) | 17.4 (0%) | 9.62 (0%) |
| `packed/horner/mul_2_2+add_2_2/full_sel` | 17.3 (1%) | 17.3 (1%) | 16.6 (1%) | 16.6 (1%) | 20 (0%) | 20 (0%) | 19.5 (0%) | 19.5 (0%) | 14 (0%) |
| `packed/horner/ball_mul_2+ball_add_2/kairn` | 28.6 (1%) | 28.7 (1%) | 20.4 (1%) | 20.3 (1%) | 34.8 (0%) | 34.7 (0%) | 31.9 (0%) | 31.9 (0%) | 29.2 (0%) |
| `packed/horner/ball_mul_2+ball_add_2/plain` | 28.4 (2%) | 28.7 (1%) | 20.3 (1%) | 20.3 (1%) | 34.2 (0%) | 34.2 (0%) | 31 (0%) | 31 (0%) | 29.3 (0%) |
| `packed/horner/ball_mul_2+ball_add_2/full_sel` | 54 (1%) | 53.7 (1%) | 44.1 (1%) | 44.1 (0%) | 52.9 (0%) | 52.9 (0%) | 46.9 (0%) | 46.9 (0%) | 47.6 (0%) |
| `mpfr/tp/add_2_2/mpfr` | 7 (1%) | 6.97 (2%) | 6.99 (1%) | 7.01 (1%) | 14.3 (5%) | 14.2 (3%) | 14.3 (2%) | 14.2 (1%) | — |
| `mpfr/tp/mul_2_2/mpfr` | 7.5 (1%) | 7.14 (6%) | 7.18 (6%) | 7.5 (1%) | 15.9 (3%) | 15.9 (2%) | 15.9 (2%) | 15.2 (3%) | — |
| `mpfr/sum/add_2_2/mpfr` | 7 (1%) | 6.71 (6%) | 6.69 (5%) | 6.97 (1%) | 14.3 (3%) | 14.1 (2%) | 13.8 (2%) | 13.8 (1%) | — |
| `mpfr/prod/mul_2_2/mpfr` | 7.77 (1%) | 7.65 (3%) | 7.74 (2%) | 7.83 (1%) | 15.9 (1%) | 15.6 (2%) | 15.4 (3%) | 15.5 (2%) | — |
| `mpfr/horner/mul_2_2+add_2_2/mpfr` | 12.4 (1%) | 12.4 (1%) | 12.4 (1%) | 12.4 (1%) | 30 (3%) | 30.9 (2%) | 29.6 (2%) | 29.4 (1%) | — |
