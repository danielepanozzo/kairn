# Brute-force results, Milestone 1

**No claim was violated.** On three machines, the oracle judged 13 832 577 348 results of the
compiled kernels (14 308 800 000 cases through 60 runners: scalar and packed, every contraction
setting, both forms of the scalar fix-ups, five compilers) and 782 322 659 results of the
generator's interpreter, which enumerated every operand of 328 toy-format domains (982 994 259
cases). It found no failure and no invalid case; the only suspicious non-finite results
(11 484 540 in the compiled runs, 1 844 678 in the enumerations) are those of `split` and
`two_prod_dekker`, whose product by the splitter may overflow and which are exempt, as in the
quick tier. Every one of the 7 560 series of one kernel, format and runner and every
enumeration passed the quick tier's guards, every enumeration was complete,
and no pipeline failed or timed out. The code is the final code of Milestone 1: 63 kernels, 39 of
them in the extended domain of infinities and NaN, judged there on infinite and NaN operands too.
A [supplementary run](#supplementary-run-b4-on-the-full-ball-kernels), at a later commit whose
full Ball kernels claim a condition more (B4), judged that condition on those eight kernels, with
no failure either.

**How close the bounds came.** Four claims are attained exactly, by some case of the runs: the
relative bound $u/(1+u)$ of `add_1_1` (a rounding to nearest), the underflow term $\eta/2$ of
`two_prod`, and the $3/2$ gaps of `radd` and of `rmul`. Three come within $10^{-9}$ of their
bound in `binary64`, through their underflow terms: `mul_1_1`, `mul_2_1` and the core of
`mul_2_1_full`. Then `sub_2_1` (0.997 of its bound), `add_2_1` (0.988), the core of
`add_2_1_full` (0.985), the core of `mul_2_2_full` (0.981) and `mul_2_2` (0.977); the farthest
are the core of `sub_2_2_full` (0.667), `add_2_2` (0.689), the core of `add_2_2_full` (0.718),
`add_fast_2_2` (0.743), `sub_2_2` (0.747), `mul_pow2_2` and the core of its full kernel (0.750)
and the core of `add_fast_2_2_full` (0.766). Every claim of exactness held exactly. Far from the
underflow range, the largest observed constants are 3.49 for the core of `mul_2_2_full` and 3.44
for `mul_2_2` (claimed 4), 2.30 for the core of `add_fast_2_2_full` and 2.23 for `add_fast_2_2`
(3), 2.24 for `sub_2_2`, 2.15 for the core of `add_2_2_full` and 2.07 for `add_2_2` (claimed
$3/(1-4u)$), and 1.74 to 1.99 for the kernels with a one-limb operand and their full kernels'
cores (claimed 2: `sub_2_1` 1.99, `add_2_1` 1.98, `mul_2_1` 1.95, `sub_1_2` 1.78). The Ball radius that came closest to the smallest enclosing radius was exactly one
gap above it, for `ball_add_1`, `ball_sub_1` and their full kernels (in `binary64`, `binary32`
and toy formats) and for `ball_scale_1` and its full kernel (toy formats; just above one gap in
`binary64` and `binary32`): there, a radius one unit in the last place smaller would have been the
smallest enclosing radius itself. The other Ball kernels kept 1.25 to 2.5 gaps; the negations are
exact. On each machine, every runner (every compiler, scalar and packed, every contraction
setting, both forms of the fix-ups) gave the same counts and the same extremes, for every kernel
and format.

**The aim of $10^8$ cases per kernel and format was reached**: 110 to 122 million per kernel and
format, summed over the machines and their runners, from 5.0 to 5.6 million distinct cases. Of
those, the judged results (a finite result in the finite domain, any result in the extended
domain) reach $10^8$ for 115 of the 126 kernels and formats; the other 11, 85 to 99 million, are
finite-domain kernels whose random cases often end in a non-finite result, about which their claims
say nothing ([below](#the-aim-a-hundred-million-cases-per-kernel-and-format)).

## What was run

The code under test (kernels, claims, generator, interpreter, oracle) is that of commit
`6f89054`, whose kernels, generator, claims and oracle judge are those of `b7a1fbb`: 63 kernels,
39 of them in the extended domain, with the second design of the Ball radius and its constant $H$
that contains the smallest normal number
([the radius, second design](../design/milestone1.md#the-radius-second-design)). The driver is
that of commit `e226c9e`, and `d619f71` for the first ten minutes of the Linux run (below). Each
stored summary names both commits. The commands are in
[`tests/brute/README.md`](https://github.com/danielepanozzo/kairn/blob/main/tests/brute/README.md),
the stored summaries in
[`results/milestone1/brute/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone1/brute):
one file per machine, with every count, statistic and attaining line of the tables below.

| Machine | Compilers | Runners | Seed | Cases per kernel and format | Judged (compiled) | Enumerated (interpreter) |
|---|---|---|---|---|---|---|
| linux-x86-64: Linux x86_64, AMD EPYC 7452 32-Core Processor | Clang 18.1.3, GNU 13.3.0 | 24 | `m1r2-linux` | 2 600 000 to 2 800 000 | 7 790 145 432 | 936 163 801 |
| macos-arm64: Darwin arm64, Apple M3 Max | AppleClang 21.0.0.21000401, GNU 16.2.0 | 24 | `m1r2-mac` | 1 600 000 to 1 800 000 | 4 707 341 928 | 46 830 458 |
| windows-x64: Windows AMD64, 13th Gen Intel(R) Core(TM) i5-13500T | MSVC 19.52.37029.0 | 12 | `m1r2-windows` | 800 000 to 1 000 000 | 1 335 089 988 | 0 |

The Linux machine ran for 3.5 hours on its first socket, 64 of its 128 hardware threads, with 80
busy processes; the Mac for 3 hours with 8; the Windows machine for 3 hours on 8 logical
processors, which no CI job used that day (a few short test runs did); all at a lower priority. The Linux run started
with the compiled part alone while the plan of the enumerations was settled, and was restarted
after ten minutes with both parts and the budget left. Its enumerations took 48 minutes on 40
interpreter pipelines, so it was restarted once more to take one of the Mac's two bins of the
plan as well, which took another five minutes; the Mac's other bin took three minutes. Each
restart kept what was done; the pipelines it stopped were run again. The rest of each budget went
to the compiled runners.

| Machine | Wall time | Judged per second | Enumerated per second | One check pipeline, cases/s | One generator, cases/s | One interpreter pipeline, cases/s |
|---|---|---|---|---|---|---|
| linux-x86-64 | 12594 s (3.50 h) | 618 560 | 74 334 | 11 154 | 11 203 | 7 810 |
| macos-arm64 | 10865 s (3.02 h) | 433 261 | 4 310 | 59 523 | 59 786 | 67 606 |
| windows-x64 | 10906 s (3.03 h) | 122 412 | 0 | 17 219 | 17 703 | - |

The wall time is the sum of each machine's runs, builds included (a few seconds each), without
the minute or two between the Linux run's restarts; "per second of it" divides each machine's
totals by its whole wall time, enumerations included. A check pipeline is one runner
fed a unit of 200 000 cases, judged by the oracle (Python, exact integer arithmetic); a generator
writes such a unit once for all the runners of the machine; an interpreter pipeline is the
generator's enumeration, the interpreter and the oracle on 500 000 indices. The Mac's pipelines
are the fastest per process; its one bin of enumerations was also mostly cases with non-finite
results, which the oracle judges quickly.

**Compiled runners.** Every kernel of `gen/claims.json`, in `binary64` and `binary32`, through
every runner the quick tier builds (`kairn-gen-runner*`, `kairn-gen-packed-runner*`): the scalar
and the packed kernels, each with the build's flags and under each contraction setting, with
every compiler of the machine; and the scalar runners once more, built with the other form of the
scalar fix-ups of the full kernels and constructors (`KAIRN_GEN_FIXUP_CALL`: the default is a
function of its own with Clang on AArch64, inline elsewhere; the second build defines the other,
`-DKAIRN_GEN_FIXUP_CALL=1` for GCC, Clang on x86-64 and MSVC, `=0` for Apple clang). At this
commit the runners of a contraction setting were built with the build's flags and the setting:
at `-O3` (Release) with GCC and Clang, `/O2` with MSVC (the stored summaries keep every runner's
flags). Cases are the oracle's random ones, every stratum of the kernel's family (for the 39
kernels of the extended domain, strata with infinite and NaN operands among them), from one seed
per machine; every runner of a machine judged the same cases, as in the quick tier.
`--fail-on-suspicious` everywhere except `split` and `two_prod_dekker`, as in the quick tier.

**Interpreter.** The generator's interpreter on every operand of 328 toy-format domains: for each
kernel, the formats of precision `min_precision` and `min_precision + 1` (2 and 3 when
`min_precision` is 1, [below](#what-was-not-run-and-why)) in the quick tier's exponent range
(for the extended domain, the quick tier's number of exponents in the shape
$q_{\min} + q_{\max} = 3 - 2p$ of the IEEE-model statements), the quick tier's format one and two
bits more precise, and one or two other exponent ranges; for the two-limb balls with two
operands, complete enumerations of formats of their `min_precision` with fewer exponents, and
larger restricted domains. The enumerations of the extended domain include the infinite and NaN
values of every operand (for a ball operand, the whole line and the empty set). The plan
(`brute.py plan --bins 20`) was split by size: the Linux machine ran bins 0 and 2 to 19 (319
enumerations), the Mac bin 1 (9); the Windows machine ran none, as before.

Two changes to the plan since the last runs. Every constant of every kernel is now checked in
each of its formats when the plan is made, and a format in which one is not a number of the
format is replaced: `two_prod_dekker` gets `fp:7:-16:-2` in place of `fp:7:-20:-6`, whose largest
number is below the splitter 17, and no other format of the plan needed it. And the Ball formats
were chosen for the share of their cases that end as a finite ball
([below](#finite-balls-in-the-enumerations)): `ball_mul_2` gets
`fp:4:-5:-3` in place of `fp:4:-2:0`, `ball_mul_2_full` a complete enumeration of `fp:4:-4:-1`
(98 million cases) and a restricted one with six exponents, and `ball_mul_1_full` `fp:2:-7:6`.

**What a pass required.** The quick tier's guards (`tests/crosscheck_guards.py`), applied by
`brute.py collect` to every merged series of one kernel, format and runner, and to every
enumeration: the stream is the one asked for and seen whole (cases 0 to N of the machine's seed;
every index of the enumeration, over exactly the domain asked for); every stratum the oracle's
generator lists is present (in the extended domain, those it adds for infinite and NaN operands
too); something was judged; every `ensures` entry applied to a judged case; every comparison was
seen true and false; every rounding to nearest saw an inexact case and every directed rounding a
case where it differs from the rounding to nearest. Every series and every enumeration passed
them, and `collect` exited 0 on each machine.

## How close the claims came

### Error bounds

The largest error over the bound it is allowed, $\lvert\text{err}\rvert / (\mathrm{rel}\,\rho +
\mathrm{abs})$, over every judged case; 1 is the claim itself. A claim with `c=0` and `t=0` says
the result is exact. "(the claim)" marks an extreme equal to the bound, decided exactly. For a
full kernel the entry is that of its core, `F2, core K: ...`, which the oracle applies to the
cases whose operands and result are finite.

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `add_1_1` | `error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:7:-14:2`) (the claim) |
| `mul_1_1` | `error(p) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 0.999939 (`fp:7:-20:-6`) |
| `mul_2_1` | `error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 0.972718 (`fp:6:-8:-2`) |
| `mul_2_1_full` | `F2, core mul_2_1: error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 0.972718 (`fp:6:-7:-2`) |
| `two_prod` | `error(r) form R, c=0, k=2, t=1/2` | 1 (the claim) | 1 (`fp:7:-20:-6`) (the claim) |
| `sub_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.997363 | 0.939450 (`fp:5:-6:3`) |
| `add_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.987720 | 0.939450 (`fp:5:-6:3`) |
| `add_2_1_full` | `F2, core add_2_1: error(z) form R, c=2, k=2, t=0` | 0.984629 | 0.939450 (`fp:5:-8:1`) |
| `mul_2_2_full` | `F2, core mul_2_2: error(z) form R, c=4, k=2, t=3/2` | 0.980949 | 0.838827 (`fp:5:-6:-1`) |
| `mul_2_2` | `error(z) form R, c=4, k=2, t=3/2` | 0.977185 | 0.898829 (`fp:6:-7:-3`) |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=13/8` | 0.925880 | 0.943510 (`fp:7:-16:-2`) |
| `sub_2_1_full` | `F2, core sub_2_1: error(z) form R, c=2, k=2, t=0` | 0.943193 | 0.939450 (`fp:5:-8:1`) |
| `sub_1_2` | `error(z) form R, c=2, k=2, t=0` | 0.892058 | 0.939450 (`fp:5:-6:3`) |
| `sub_1_2_full` | `F2, core sub_1_2: error(z) form R, c=2, k=2, t=0` | 0.916723 | 0.939450 (`fp:5:-8:1`) |
| `add_fast_2_2_full` | `F2, core add_fast_2_2: error(z) form A, c=3, k=2, t=0` | 0.766367 | 0.671916 (`fp:4:-6:1`) |
| `mul_pow2_2` | `error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.746094 (`fp:6:-12:4`) |
| `mul_pow2_2_full` | `F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.746094 (`fp:6:-12:3`) |
| `sub_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.746694 | 0.556176 (`fp:5:-3:2`) |
| `add_fast_2_2` | `error(z) form A, c=3, k=2, t=0` | 0.742791 | 0.671916 (`fp:4:-4:3`) |
| `add_2_2_full` | `F2, core add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.718019 | 0.556176 (`fp:5:-6:-1`) |
| `add_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.688923 | 0.556176 (`fp:5:-3:2`) |
| `sub_2_2_full` | `F2, core sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.556176 (`fp:5:-6:-1`) |
| `abs_2` | `error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:8:-16:3`) |
| `fast_two_sum` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-14:2`) |
| `neg_2` | `error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:8:-16:3`) |
| `split` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:13:-60:40`) |
| `two_prod` | `error(r) form R, c=0, k=2, t=0, when product_large` | 0 (exact) | 0 (exact; `fp:7:-20:-6`) |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=0, when product_large` | 0 (exact) | 0 (exact; `fp:7:-16:-2`) |
| `two_sum` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-14:2`) |

By backend: the largest error over its bound per kernel (operation and number of limbs), format
and backend, over every machine and compiler (scalar: both forms of the fix-ups and every
contraction setting; AVX2 on the Linux and Windows machines, NEON on the Mac). Exact claims are
left out (every one held exactly). The backends of one machine judged the same cases and agreed;
different values between backends come from the machines' different random cases.

| Kernel | Claim | binary64 scalar | binary64 AVX2 | binary64 NEON | binary32 scalar | binary32 AVX2 | binary32 NEON |
|---|---|---|---|---|---|---|---|
| `add_1_1` | `error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `mul_1_1` | `error(p) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999999404 | 0.9999999404 | 0.9999999404 |
| `mul_2_1` | `error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999997616 | 0.9999998510 | 0.9999998510 | 0.9999998212 |
| `mul_2_1_full` | `F2, core mul_2_1: error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999997914 | 0.999999 | 0.9999997914 |
| `two_prod` | `error(r) form R, c=0, k=2, t=1/2` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `sub_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.997363 | 0.957449 | 0.997363 | 0.986186 | 0.986186 | 0.822230 |
| `add_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.983175 | 0.983175 | 0.955754 | 0.987720 | 0.962137 | 0.987720 |
| `add_2_1_full` | `F2, core add_2_1: error(z) form R, c=2, k=2, t=0` | 0.984178 | 0.984178 | 0.704643 | 0.984629 | 0.984629 | 0.958624 |
| `mul_2_2_full` | `F2, core mul_2_2: error(z) form R, c=4, k=2, t=3/2` | 0.980949 | 0.980949 | 0.962862 | 0.968941 | 0.968941 | 0.925216 |
| `mul_2_2` | `error(z) form R, c=4, k=2, t=3/2` | 0.977185 | 0.977185 | 0.968918 | 0.973840 | 0.946950 | 0.973840 |
| `sub_2_1_full` | `F2, core sub_2_1: error(z) form R, c=2, k=2, t=0` | 0.913198 | 0.706034 | 0.913198 | 0.943193 | 0.943193 | 0.858546 |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=13/8` | 0.923852 | 0.923852 | 0.915590 | 0.925880 | 0.925880 | 0.914851 |
| `sub_1_2_full` | `F2, core sub_1_2: error(z) form R, c=2, k=2, t=0` | 0.812210 | 0.812210 | 0.784723 | 0.916723 | 0.916723 | 0.871264 |
| `sub_1_2` | `error(z) form R, c=2, k=2, t=0` | 0.810049 | 0.810049 | 0.736158 | 0.892058 | 0.892058 | 0.833123 |
| `add_fast_2_2_full` | `F2, core add_fast_2_2: error(z) form A, c=3, k=2, t=0` | 0.523704 | 0.523704 | 0.500000 | 0.766367 | 0.766367 | 0.500000 |
| `mul_pow2_2` | `error(z) form R, c=0, k=2, t=1` | 0.738546 | 0.738546 | 0.738447 | 0.750000 | 0.750000 | 0.750000 |
| `mul_pow2_2_full` | `F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1` | 0.748915 | 0.748915 | 0.719796 | 0.750000 | 0.750000 | 0.750000 |
| `sub_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.703127 | 0.703127 | 0.647306 | 0.746694 | 0.746694 | 0.618223 |
| `add_fast_2_2` | `error(z) form A, c=3, k=2, t=0` | 0.742791 | 0.742791 | 0.500000 | 0.595790 | 0.595790 | 0.499974 |
| `add_2_2_full` | `F2, core add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.666667 | 0.666667 | 0.718019 | 0.718019 | 0.666748 |
| `add_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.665531 | 0.645783 | 0.665531 | 0.688923 | 0.688923 | 0.666666 |
| `sub_2_2_full` | `F2, core sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.666667 | 0.666667 | 0.666666 | 0.666666 | 0.666666 |

### Upper bounds

The largest excess of the result over the exact value, in gaps of the result (`upper` claims: at
most `gaps`).

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `radd` | `upper(r) gaps=3/2` | 1.5 (the claim) | 1.5 (`fp:8:-16:3`) (the claim) |
| `rmul` | `upper(r) gaps=3/2` | 1.5 (the claim) | 1.5 (`fp:8:-16:3`) (the claim) |

### Ball radii

The smallest slack of the returned radius over the smallest radius that encloses the exact set, in
gaps of the radius: below 1, a radius one unit in the last place smaller would no longer enclose.
For a full Ball kernel it is measured on the finite balls it returns from finite operands.

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `ball_mul_2` | `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]` | 2.50150 | 2.16797 (`fp:4:-5:1`) |
| `ball_mul_2_full` | `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)` | 2.50000 | 2.16797 (`fp:4:-5:0`) |
| `ball_mul_1` | `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]` | 1.53530 | 1.60547 (`fp:4:-4:1`) |
| `ball_mul_1_full` | `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)` | 1.53354 | 1.85352 (`fp:3:-4:1`) |
| `ball_scale_2` | `encloses(cz, rz) x*a over x=[cx +- rx]` | 1.375 | 1.375 (`fp:3:-6:2`) |
| `ball_scale_2_full` | `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)` | 1.34077 | 1.40625 (`fp:3:-4:1`) |
| `ball_add_2_full` | `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)` | 1.25163 | 1.75 (`fp:3:-3:0`) |
| `ball_sub_2_full` | `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)` | 1.25152 | 1.75 (`fp:3:-3:0`) |
| `ball_add_2` | `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]` | 1.25013 | 1.25 (`fp:3:-3:2`) |
| `ball_sub_2` | `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]` | 1.25003 | 1.25 (`fp:3:-3:2`) |
| `ball_add_1` | `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]` | 1 | 1 (`fp:3:-4:2`) |
| `ball_add_1_full` | `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)` | 1 | 1 (`fp:3:-4:1`) |
| `ball_scale_1` | `encloses(cz, rz) x*a over x=[cx +- rx]` | 1.00000 | 1 (`fp:3:-8:2`) |
| `ball_scale_1_full` | `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)` | 1.00000 | 1 (`fp:3:-6:3`) |
| `ball_sub_1` | `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]` | 1 | 1 (`fp:3:-4:2`) |
| `ball_sub_1_full` | `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)` | 1 | 1 (`fp:3:-4:1`) |
| `ball_neg_1` | `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)` | 0 | 0 (`fp:7:-11:0`) |
| `ball_neg_2` | `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)` | 0 | 0 (`fp:6:-8:-1`) |

### Finite balls in the enumerations

The share of the cases of each enumeration of a Ball kernel that end as a finite ball: in the
finite domain the judged cases (the others overflow, about which the claims say nothing), in the
extended domain the results that are neither the whole line nor the empty set. The constructors
`ball_make_1` and `ball_make_2` have no containment claim and are not listed.

| Kernel | Enumeration | Cases | Finite ball | Share |
|---|---|---|---|---|
| `ball_add_1` | `fp:2:-3:1` | 76 176 | 38 412 | 50.4 % |
| `ball_add_1` | `fp:2:-6:4` | 1 272 384 | 994 044 | 78.1 % |
| `ball_add_1` | `fp:3:-3:1` | 1 272 384 | 807 559 | 63.5 % |
| `ball_add_1` | `fp:3:-4:2` | 4 064 256 | 3 025 751 | 74.4 % |
| `ball_add_1` | `fp:4:-3:1` | 20 793 600 | 14 367 516 | 69.1 % |
| `ball_add_1_full` | `fp:2:-3:2` | 144 400 | 83 664 | 57.9 % |
| `ball_add_1_full` | `fp:2:-5:4` | 898 704 | 677 872 | 75.4 % |
| `ball_add_1_full` | `fp:3:-4:1` | 2 377 764 | 1 656 735 | 69.7 % |
| `ball_add_2` | `fp:3:-2:1` | 5 664 400 | 2 192 431 | 38.7 % |
| `ball_add_2` | `fp:3:-3:1` | 32 901 696 | 15 977 235 | 48.6 % |
| `ball_add_2` | `fp:3:-3:2`, restricted: `cx.lead=-1:0` | 7 295 904 | 5 136 540 | 70.4 % |
| `ball_add_2` | `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` | 8 767 521 | 4 968 972 | 56.7 % |
| `ball_add_2` | `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` | 15 713 296 | 11 654 256 | 74.2 % |
| `ball_add_2_full` | `fp:3:-3:0` | 5 673 924 | 2 417 175 | 42.6 % |
| `ball_add_2_full` | `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` | 2 869 636 | 2 208 432 | 77.0 % |
| `ball_add_2_full` | `fp:4:-3:-2` | 2 149 156 | 389 129 | 18.1 % |
| `ball_mul_1` | `fp:2:-4:1` | 142 884 | 56 255 | 39.4 % |
| `ball_mul_1` | `fp:2:-7:3` | 1 272 384 | 739 313 | 58.1 % |
| `ball_mul_1` | `fp:3:-4:1` | 2 371 600 | 891 164 | 37.6 % |
| `ball_mul_1` | `fp:3:-6:2` | 9 985 600 | 5 328 700 | 53.4 % |
| `ball_mul_1` | `fp:4:-4:1` | 38 638 656 | 10 981 732 | 28.4 % |
| `ball_mul_1_full` | `fp:2:-3:2` | 144 400 | 36 018 | 24.9 % |
| `ball_mul_1_full` | `fp:2:-5:4` | 898 704 | 370 156 | 41.2 % |
| `ball_mul_1_full` | `fp:2:-7:6` | 3 139 984 | 1 536 054 | 48.9 % |
| `ball_mul_1_full` | `fp:3:-4:1` | 2 377 764 | 891 164 | 37.5 % |
| `ball_mul_2` | `fp:4:-5:-3` | 15 492 096 | 5 471 272 | 35.3 % |
| `ball_mul_2` | `fp:4:-5:1`, restricted: `cx.lead=0:0`, `cy.lead=0:0` | 15 745 024 | 8 811 524 | 56.0 % |
| `ball_mul_2` | `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1.8p+0` | 27 342 441 | 4 110 469 | 15.0 % |
| `ball_mul_2` | `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `ry.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `cx.lead=0:0` | 2 701 650 | 1 199 458 | 44.4 % |
| `ball_mul_2` | `fp:5:-4:1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1.8p+0`, `cx.lead=0:0` | 580 320 | 364 016 | 62.7 % |
| `ball_mul_2_full` | `fp:4:-3:-2` | 2 149 156 | 122 038 | 5.7 % |
| `ball_mul_2_full` | `fp:4:-4:-1` | 97 653 924 | 10 316 053 | 10.6 % |
| `ball_mul_2_full` | `fp:4:-4:-1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0` | 980 100 | 301 364 | 30.7 % |
| `ball_mul_2_full` | `fp:4:-5:0`, restricted: `cx.lead=0:0`, `cy.lead=0:0` | 12 068 676 | 6 421 596 | 53.2 % |
| `ball_mul_2_full` | `fp:5:-5:-2`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `cx.lead=0:0` | 503 500 | 305 464 | 60.7 % |
| `ball_neg_1` | `fp:2:-6:5` | 1 328 | 1 326 | 99.8 % |
| `ball_neg_1` | `fp:3:-7:4` | 5 358 | 5 356 | 100.0 % |
| `ball_neg_1` | `fp:5:-13:6` | 225 458 | 225 456 | 100.0 % |
| `ball_neg_1` | `fp:6:-10:1` | 345 698 | 345 696 | 100.0 % |
| `ball_neg_1` | `fp:7:-11:0` | 1 383 618 | 1 383 616 | 100.0 % |
| `ball_neg_2` | `fp:2:-4:3` | 5 888 | 5 886 | 100.0 % |
| `ball_neg_2` | `fp:3:-5:2` | 35 390 | 35 388 | 100.0 % |
| `ball_neg_2` | `fp:4:-8:3` | 971 674 | 971 672 | 100.0 % |
| `ball_neg_2` | `fp:5:-7:0` | 1 018 226 | 1 018 224 | 100.0 % |
| `ball_neg_2` | `fp:6:-8:-1` | 4 681 442 | 4 681 440 | 100.0 % |
| `ball_scale_1` | `fp:2:-5:0` | 10 206 | 9 064 | 88.8 % |
| `ball_scale_1` | `fp:3:-5:0` | 84 700 | 67 922 | 80.2 % |
| `ball_scale_1` | `fp:3:-8:2` | 433 200 | 359 094 | 82.9 % |
| `ball_scale_1` | `fp:4:-5:0` | 689 976 | 489 850 | 71.0 % |
| `ball_scale_1` | `fp:4:-8:2` | 3 502 176 | 2 726 994 | 77.9 % |
| `ball_scale_1` | `fp:5:-5:0` | 5 569 648 | 3 257 050 | 58.5 % |
| `ball_scale_1_full` | `fp:2:-3:2` | 11 400 | 6 812 | 59.8 % |
| `ball_scale_1_full` | `fp:2:-8:7` | 159 600 | 114 342 | 71.6 % |
| `ball_scale_1_full` | `fp:3:-4:1` | 89 436 | 58 050 | 64.9 % |
| `ball_scale_1_full` | `fp:3:-6:3` | 344 700 | 242 226 | 70.3 % |
| `ball_scale_1_full` | `fp:4:-5:0` | 708 852 | 489 850 | 69.1 % |
| `ball_scale_2` | `fp:2:-4:1` | 60 102 | 43 522 | 72.4 % |
| `ball_scale_2` | `fp:2:-8:3` | 1 133 730 | 905 462 | 79.9 % |
| `ball_scale_2` | `fp:3:-4:1` | 651 420 | 374 170 | 57.4 % |
| `ball_scale_2` | `fp:3:-6:2` | 4 294 440 | 2 861 126 | 66.6 % |
| `ball_scale_2` | `fp:4:-4:1` | 6 160 056 | 2 659 714 | 43.2 % |
| `ball_scale_2_full` | `fp:2:-2:1` | 12 144 | 4 934 | 40.6 % |
| `ball_scale_2_full` | `fp:2:-4:3` | 223 744 | 127 466 | 57.0 % |
| `ball_scale_2_full` | `fp:3:-3:0` | 100 044 | 50 478 | 50.5 % |
| `ball_scale_2_full` | `fp:3:-4:1` | 687 068 | 374 170 | 54.5 % |
| `ball_scale_2_full` | `fp:4:-4:-1` | 810 324 | 440 840 | 54.4 % |
| `ball_sub_1` | `fp:2:-3:1` | 76 176 | 38 412 | 50.4 % |
| `ball_sub_1` | `fp:2:-6:4` | 1 272 384 | 994 044 | 78.1 % |
| `ball_sub_1` | `fp:3:-3:1` | 1 272 384 | 807 559 | 63.5 % |
| `ball_sub_1` | `fp:3:-4:2` | 4 064 256 | 3 025 751 | 74.4 % |
| `ball_sub_1` | `fp:4:-3:1` | 20 793 600 | 14 367 516 | 69.1 % |
| `ball_sub_1_full` | `fp:2:-3:2` | 144 400 | 83 664 | 57.9 % |
| `ball_sub_1_full` | `fp:2:-5:4` | 898 704 | 677 872 | 75.4 % |
| `ball_sub_1_full` | `fp:3:-4:1` | 2 377 764 | 1 656 735 | 69.7 % |
| `ball_sub_2` | `fp:3:-2:1` | 5 664 400 | 2 192 431 | 38.7 % |
| `ball_sub_2` | `fp:3:-3:1` | 32 901 696 | 15 977 235 | 48.6 % |
| `ball_sub_2` | `fp:3:-3:2`, restricted: `cx.lead=-1:0` | 7 295 904 | 5 136 540 | 70.4 % |
| `ball_sub_2` | `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` | 8 767 521 | 4 968 972 | 56.7 % |
| `ball_sub_2` | `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` | 15 713 296 | 11 654 256 | 74.2 % |
| `ball_sub_2_full` | `fp:3:-3:0` | 5 673 924 | 2 417 175 | 42.6 % |
| `ball_sub_2_full` | `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` | 2 869 636 | 2 208 432 | 77.0 % |
| `ball_sub_2_full` | `fp:4:-3:-2` | 2 149 156 | 389 129 | 18.1 % |

A product of balls in a format whose numbers lie mostly above 1 mostly overflows: at
`fp:4:-2:0` (numbers $2^{-2}$ to 15, smallest normal 2), the format the last runs used for
`ball_mul_2`, a sample of 10 000 cases put the share of finite balls at 1.3 %, and
more exponents above 1 did not raise it (`fp:4:-3:0` 3.9 %, `fp:4:-3:1` 2.4 %), where the same
number of exponents below 1 did: `fp:4:-5:-3`, of the same size, gives 35.3 % above. The full
product is held to the IEEE shape, where the complete enumerations give 5.7 % (two exponents) and
10.6 % (four, 10 316 053 finite balls); its restricted enumeration with six exponents gives
53.2 %. Every other Ball kernel has a complete enumeration in which at least 35 % of the cases
end as a finite ball. At the quick tier's `fp:3:-2:-1`, which this plan does not use, a sample of
10 000 of the 122 500 cases of `ball_add_2_full` put the share at 5.9 %; here its complete
enumerations give 18.1 % and 42.6 %.

### The runners of a machine

On each machine, every runner gave the same counts and the same extremes, for every kernel and format (378 series of runners compared).

### The aim: a hundred million cases per kernel and format

Per kernel and format, summed over the machines and their runners: 110 400 000 to 122 400 000 cases (median 112 800 000), of which 85 069 980 to 122 400 000 judged (a finite result, or any result in the extended domain), from 5 000 000 to 5 600 000 distinct cases. 126 of 126 kernel and format pairs reach $10^8$ cases.

115 of 126 reach $10^8$ judged results; below it: `ball_mul_2` `binary32` 85 069 980, `ball_scale_2` `binary32` 85 079 340, `ball_mul_2` `binary64` 87 402 624, `ball_scale_2` `binary64` 87 612 192, `ball_scale_1` `binary32` 91 505 196, `ball_mul_1` `binary32` 91 893 636, `ball_mul_1` `binary64` 92 233 392, `ball_scale_1` `binary64` 93 378 468, `mul_1_1` `binary64` 94 270 848, `mul_1_1` `binary32` 94 996 140, `two_prod_dekker` `binary32` 98 852 220.

The last runs missed this aim. These ran 3 to 3.5 hours per machine, and every generated case
was judged by 12 runners (Windows) or 24 (Linux, Mac), since each compiler's scalar runners were
built in both forms of the fix-ups. The eleven kernels and formats below $10^8$ judged results
are of the finite domain, where a non-finite result is not judged. `ball_mul_2`,
`ball_scale_2`, `ball_mul_1`, `ball_scale_1`, `mul_1_1` and `two_prod_dekker` multiply, and their
random operands, whose exponents range over the whole format, overflow in about a tenth to a
third of the cases of most strata and in most of the stratum `overflow`: 16 to 25 % of their
cases end in a non-finite result.

## Per kernel

Each table has one row per format of the compiled runners (every machine and runner together)
and one per enumeration of the interpreter. "Judged" excludes, in the finite domain, the cases
whose result is not finite, about which the claims say nothing; in the extended domain every
case is judged. "Observed c" is the oracle's (a): the largest $\lvert\text{err}\rvert / (u^k \rho)$
over the cases far from the underflow range ($u^k\rho \ge 2^p\eta$), to compare with the claim's
`c`. Below each table, the distinct random cases per stratum and the lines that attain the
extremes, as the oracle reports them: a line's tag (`#STRATUM:INDEX` or `#exhaustive:INDEX`) and
the machine's seed regenerate its case ([Rerunning one case](../testing.md#rerunning-one-case)).
The runner named is the first of a machine's runners to attain it: they all judged the same cases
and agreed.

### `abs_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`; `represents(z)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 0 (exact) | 0 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0 (exact) | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | 0 (exact) | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | 0 (exact) | - |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | 0 (exact) | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 540 000, halfgap 1 080 000, nonfinite 1 080 000, overflow 540 000, pow2 540 000, underflow 540 000, uniform 540 000, zero 540 000; `binary32`: extreme 520 000, halfgap 1 040 000, nonfinite 1 040 000, overflow 520 000, pow2 520 000, underflow 520 000, uniform 520 000, zero 520 000.

### `abs_upper_2`

Claims: `rounded(t) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | exact 25 731 180; inexact, as RN 36 929 940; differs from RN 26 673 708; a non-finite operand 22 560 000; rounds to inf 905 172 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | exact 27 543 312; inexact, as RN 35 892 768; differs from RN 25 894 272; a non-finite operand 22 560 000; rounds to inf 909 648 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact, as RN 2 582 912; differs from RN 2 582 914; a non-finite operand 3; rounds to inf 3 070 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact, as RN 357 760; differs from RN 357 762; a non-finite operand 3; rounds to inf 1 022 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact, as RN 129 600; differs from RN 129 602; a non-finite operand 3; rounds to inf 638 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact, as RN 1 348; differs from RN 1 350; a non-finite operand 3; rounds to inf 70 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact, as RN 382; differs from RN 384; a non-finite operand 3; rounds to inf 38 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 520 000, halfgap 1 040 000, nonfinite 1 040 000, overflow 520 000, pow2 520 000, underflow 520 000, uniform 520 000, zero 520 000; `binary32`: extreme 520 000, halfgap 1 040 000, nonfinite 1 040 000, overflow 520 000, pow2 520 000, underflow 520 000, uniform 520 000, zero 520 000.

### `add_1_1`

Claims: `rounded(s) nearest`; `error(s) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 122 400 000 | 114 970 644 | 0 | exact 35 027 496; inexact 78 570 252; tie 1 372 896 | 1 (the claim) | 1.00000 |
| `binary32`, 60 runners on 3 machines | 122 400 000 | 114 976 932 | 0 | exact 37 940 796; inexact 75 163 260; tie 1 872 876 | 1 (the claim) | 0.9999999404 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | exact 835 201; inexact 3 981 696; tie 454 272 | 1 (the claim) | 0.992248 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | exact 589 441; inexact 1 832 576; tie 310 912 | 1 (the claim) | 0.992248 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | exact 147 265; inexact 457 536; tie 77 632 | 1 (the claim) | 0.984615 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 489 | 0 | exact 2 281; inexact 7 016; tie 1 192 | 1 (the claim) | 0.888889 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 573 | 0 | exact 565; inexact 1 716; tie 292 | 1 (the claim) | 0.8 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 700 000, halfgap 1 400 000, overflow 700 000, pow2 700 000, underflow 700 000, uniform 700 000, zero 700 000; `binary32`: extreme 700 000, halfgap 1 400 000, overflow 700 000, pow2 700 000, underflow 700 000, uniform 700 000, zero 700 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  add_1_1 binary64 0x1p-1022 0x1.0000000000001p-1022 #extreme:1094 -> 0x1p-1021
largest error / bound, interpreter 1 (fp:7:-14:2, every operand):
  add_1_1 fp:7:-14:2 -0x1.fcp+8 0x1.f4p+7 #exhaustive:2236 -> -0x1p+8
```

### `add_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 110 567 088 | 0 | 0.983175 | 1.96635 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 110 540 916 | 0 | 0.987720 | 1.97544 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332; `binary32`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.987720 (clang-fixup-inline/cxx, macos-arm64):
  add_2_1 binary32 -0x1.010004p+11 0x1.fffffep-14 0x1.fda272p+9 #extreme:1064418 -> -0x1.032eccp+10 -0x1p-14
largest error / bound, interpreter 0.939450 (fp:5:-6:3, every operand):
  add_2_1 fp:5:-6:3 -0x1p+7 -0x1.1p+1 0x1.fp+5 #exhaustive:847632 -> -0x1.1p+6 0x0p+0
```

### `add_2_1_full`

Claims: `extends(w) F1-F5, core add_2_1, lead add, finite when |x| <= 2^(qmax+p-2) and |a| <= 2^(qmax+p-2)`; `F2, core add_2_1: normalized(z)`; `F2, core add_2_1: error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0.984178 | 1.96836 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0.984629 | 1.96926 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.939450 | - |
| `fp:4:-9:4`, every operand (p = min_precision + 1, another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.882759 | 1.76552 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0 | - |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0 | - |
| `fp:4:-5:0`, every operand (p = min_precision + 1, the quick tier's format) | 113 316 | 113 316 | 0 | 0.882759 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.780488 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 577 780, close 866 669, edge 577 776, extreme 288 890, nonfinite 577 776, overflow 288 888, pow2 288 890, threshold 577 774, underflow 577 779, uniform 288 890, zero 288 888; `binary32`: cancel 577 780, close 866 669, edge 577 776, extreme 288 890, nonfinite 577 776, overflow 288 888, pow2 288 890, threshold 577 774, underflow 577 779, uniform 288 890, zero 288 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.984629 (clang18-fixup-call/cxx, linux-x86-64):
  add_2_1_full binary32 0x1.0101p+0 -0x1.fffffep-25 -0x1.fc05c2p-2 #extreme:364452 -> 0x1.03ff1cp-1 0x1p-25
largest error / bound, interpreter 0.939450 (fp:5:-8:1, every operand):
  add_2_1_full fp:5:-8:1 -0x1p+5 -0x1.1p-1 0x1.fp+3 #exhaustive:854874 -> -0x1.1p+4 0x0p+0
```

### `add_2_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 110 570 544 | 0 | 0.665531 | 1.99659 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 110 549 700 | 0 | 0.688923 | 2.06677 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332; `binary32`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.688923 (clang18-fixup-call/cxx, linux-x86-64):
  add_2_2 binary32 -0x1.3b894cp+105 -0x1.fffffep+80 0x1.a296d8p+102 -0x1.fffffep+77 #extreme:158586 -> -0x1.073672p+105 -0x1.000008p+78
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  add_2_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 0x1.9p+5 0x1.cp-1 #exhaustive:128359 -> -0x1.1p+6 0x1p+0
```

### `add_2_2_full`

Claims: `extends(w) F1-F5, core add_2_2, lead add, finite when |x| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core add_2_2: normalized(z)`; `F2, core add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0.666667 | 2.00000 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0.718019 | 2.15406 |
| `fp:4:-6:1`, every operand (p = min_precision + 1, another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.536013 | - |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | 0.556176 | - |
| `fp:3:-6:3`, every operand (p = min_precision, another number of exponents) | 3 247 204 | 3 247 204 | 0 | 0.360255 | 2.16153 |
| `fp:4:-5:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 988 036 | 988 036 | 0 | 0.453901 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's format) | 181 476 | 181 476 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 577 780, close 866 669, edge 577 776, extreme 288 890, nonfinite 577 776, overflow 288 888, pow2 288 890, threshold 577 774, underflow 577 779, uniform 288 890, zero 288 888; `binary32`: cancel 577 780, close 866 669, edge 577 776, extreme 288 890, nonfinite 577 776, overflow 288 888, pow2 288 890, threshold 577 774, underflow 577 779, uniform 288 890, zero 288 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.718019 (msvc-fixup-call/cxx, windows-x64):
  add_2_2_full binary32 -0x1.ce0bd6p-22 -0x1.a39a66p-71 0x1.02b4eap-20 0x1.8938b6p-45 #close:858946 -> 0x1.1e63ea0000000p-21 0x1.1271700000000p-46
largest error / bound, interpreter 0.556176 (fp:5:-6:-1, every operand):
  add_2_2_full fp:5:-6:-1 -0x1.ep+3 0x1p-2 0x1.9p+2 0x1.cp-4 #exhaustive:128548 -> -0x1.1p+3 0x1p-3
```

### `add_fast_2_2`

Claims: `normalized(z)`; `error(z) form A, c=3, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 110 569 920 | 0 | 0.742791 | 2.22837 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 110 544 444 | 0 | 0.595790 | 1.78737 |
| `fp:4:-4:3`, every operand (another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.671916 | - |
| `fp:3:-6:4`, every operand (p = min_precision + 1, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.487062 | 1.46119 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.562328 | - |
| `fp:4:-3:2`, every operand (quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.487619 | - |
| `fp:3:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 178 929 | 138 027 | 0 | 0.465793 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's exponent range) | 25 281 | 20 449 | 0 | 0.313725 | 0.941176 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332; `binary32`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.742791 (clang18-fixup-call/cxx, linux-x86-64):
  add_fast_2_2 binary64 0x1.0b615051b21cfp+666 0x1.f4d0405142e95p+612 0x1.1857a9d7fa27ep+664 0x1.8384ecc57285fp+608 #close:309921 -> 0x1.51773ac7b0a6fp+666 0x1.a111e3b3423p+607
largest error / bound, interpreter 0.671916 (fp:4:-4:3, every operand):
  add_fast_2_2 fp:4:-4:3 -0x1.2p+6 0x1.ep+1 -0x1.4p+4 0x1.ep-1 #exhaustive:1228016 -> -0x1.6p+6 0x0p+0
```

### `add_fast_2_2_full`

Claims: `extends(w) F1-F5, core add_fast_2_2, lead add, finite when |x| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core add_fast_2_2: normalized(z)`; `F2, core add_fast_2_2: error(z) form A, c=3, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0.523704 | 1.57111 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0.766367 | 2.29910 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.671916 | - |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | 0.562328 | - |
| `fp:3:-6:3`, every operand (p = min_precision + 1, another number of exponents) | 3 247 204 | 3 247 204 | 0 | 0.487062 | 1.46119 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | 0.487619 | - |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 181 476 | 181 476 | 0 | 0.465793 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | 0.313725 | 0.941176 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 577 780, close 866 669, edge 577 776, extreme 288 890, nonfinite 577 776, overflow 288 888, pow2 288 890, threshold 577 774, underflow 577 779, uniform 288 890, zero 288 888; `binary32`: cancel 577 780, close 866 669, edge 577 776, extreme 288 890, nonfinite 577 776, overflow 288 888, pow2 288 890, threshold 577 774, underflow 577 779, uniform 288 890, zero 288 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.766367 (msvc-fixup-call/cxx, windows-x64):
  add_fast_2_2_full binary32 -0x1p-72 -0x1.e979fcp-97 -0x1.008004p-74 -0x1.6c8fe4p-101 #pow2:473549 -> -0x1.4020020000000p-72 -0x1.0c00000000000p-107
largest error / bound, interpreter 0.671916 (fp:4:-6:1, every operand):
  add_fast_2_2_full fp:4:-6:1 -0x1.2p+4 0x1.ep-1 -0x1.4p+2 0x1.ep-3 #exhaustive:1229354 -> -0x1.6p+4 0x0p+0
```

### `ball_add_1`

Claims: `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 122 400 000 | 112 808 784 | 0 | 1 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 122 400 000 | 112 710 072 | 0 | 1 | 1.000000095 |
| `fp:4:-3:1`, every operand (quick tier + 2 bits) | 20 793 600 | 14 367 516 | 0 | 1.625 | 1.20930 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, another exponent range) | 4 064 256 | 3 025 751 | 0 | 1 | 1.2 |
| `fp:2:-6:4`, every operand (p = min_precision + 1, another exponent range) | 1 272 384 | 994 044 | 0 | 1 | 1.33333 |
| `fp:3:-3:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 1 272 384 | 807 559 | 0 | 1 | 1.2 |
| `fp:2:-3:1`, every operand (p = min_precision + 1, the quick tier's format) | 76 176 | 38 412 | 0 | 1 | 1.33333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 430 770, centerpow2 861 538, exact 430 770, extreme 430 768, overflow 430 768, pow2 430 768, radii 861 540, underflow 430 769, uniform 430 771, wide 430 770, zero 430 768; `binary32`: cancel 430 770, centerpow2 861 538, exact 430 770, extreme 430 768, overflow 430 768, pow2 430 768, radii 861 540, underflow 430 769, uniform 430 771, wide 430 770, zero 430 768.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  ball_add_1 binary64 0x1.ffffffffffffdp+1022 0x1.0035a0aa4d3b9p+1022 -0x1.fffffffffffffp+1023 0x1p+1022 #overflow:413435 -> -0x1p+1023 0x1.001ad055269dep+1023
smallest radius slack, gaps, interpreter 1 (fp:3:-4:2, every operand):
  ball_add_1 fp:3:-4:2 -0x1.cp+4 0x1p+1 0x1.4p+3 0x1p+4 #exhaustive:34076 -> -0x1p+4 0x1.8p+4
```

### `ball_add_1_full`

Claims: `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 122 400 000 | 122 400 000 | 0 | 1 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 122 400 000 | 122 400 000 | 0 | 1 | 1.000000098 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1 | 1.2 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 1 | 1.33333 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 1 | 1.33333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 533 332, cancel 266 667, centerpow2 533 334, exact 266 668, extreme 266 666, hugeradius 533 332, nonfinite 533 332, overflow 266 666, pow2 266 666, radii 533 336, underflow 266 666, uniform 266 669, wide 266 668, zero 266 666, zerowhole 533 332; `binary32`: ballstates 533 332, cancel 266 667, centerpow2 533 334, exact 266 668, extreme 266 666, hugeradius 533 332, nonfinite 533 332, overflow 266 666, pow2 266 666, radii 533 336, underflow 266 666, uniform 266 669, wide 266 668, zero 266 666, zerowhole 533 332.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  ball_add_1_full binary64 -0x1.fffffffffffffp+1023 0x1p+1022 0x1.ffffffffffffdp+1022 0x1.549103e54ff75p+1022 #hugeradius:315167 -> -0x1p+1023 0x1.2a4881f2a7fbcp+1023
smallest radius slack, gaps, interpreter 1 (fp:3:-4:1, every operand):
  ball_add_1_full fp:3:-4:1 -0x1.cp+3 0x1p+0 0x1.4p+2 0x1p+3 #exhaustive:19872 -> -0x1p+3 0x1.8p+3
```

### `ball_add_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 104 519 064 | 0 | 1.25238 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 104 442 504 | 0 | 1.25013 | 1.000000140 |
| `fp:3:-3:1`, every operand (p = min_precision, another exponent range) | 32 901 696 | 15 977 235 | 0 | 1.4375 | 1.31507 |
| `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision + 1, quick tier + 1 bit) | 15 713 296 | 11 654 256 | 0 | 3.75 | 1.5 |
| `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` (p = min_precision, the quick tier's format) | 8 767 521 | 4 968 972 | 0 | 1.46875 | 1.41593 |
| `fp:3:-3:2`, restricted: `cx.lead=-1:0` (p = min_precision, the quick tier's format) | 7 295 904 | 5 136 540 | 0 | 1.25 | 1.31507 |
| `fp:3:-2:1`, every operand (p = min_precision, another exponent range) | 5 664 400 | 2 192 431 | 0 | 1.75 | 1.52381 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 400 000, centerpow2 800 000, exact 400 000, extreme 400 000, overflow 400 000, pow2 400 000, radii 800 000, underflow 400 000, uniform 400 001, wide 400 000, zero 399 999; `binary32`: cancel 400 000, centerpow2 800 000, exact 400 000, extreme 400 000, overflow 400 000, pow2 400 000, radii 800 000, underflow 400 000, uniform 400 001, wide 400 000, zero 399 999.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25013 (clang-fixup-inline/cxx, macos-arm64):
  ball_add_2 binary32 -0x1.aa903cp-57 -0x1.24d484p-82 0x1.fffffep+125 0x1.aa903cp-57 0x1.c5083cp-82 0x1.ffbc92p+100 #cancel:637097 -> 0x1.40677p-83 0x0p+0 0x1.000002p+126
smallest radius slack, gaps, interpreter 1.25 (fp:3:-3:2, restricted: cx.lead=-1:0):
  ball_add_2 fp:3:-3:2 -0x1.cp+0 0x0p+0 0x1.cp-1 0x1p+3 0x1.cp-1 0x1.cp+3 #exhaustive:90827 -> 0x1.cp+2 0x0p+0 0x1.4p+4
```

### `ball_add_2_full`

Claims: `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 1.26022 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 1.25163 | 1.000000142 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 | 1.75 | 1.52381 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 | 2 | 1.52381 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 | 5.5 | 1.76471 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 495 236, cancel 247 620, centerpow2 495 240, exact 247 620, extreme 247 618, hugeradius 495 236, nonfinite 495 236, overflow 247 620, pow2 247 619, radii 495 240, underflow 247 620, uniform 247 621, wide 247 620, zero 247 618, zerowhole 495 236; `binary32`: ballstates 495 236, cancel 247 620, centerpow2 495 240, exact 247 620, extreme 247 618, hugeradius 495 236, nonfinite 495 236, overflow 247 620, pow2 247 619, radii 495 240, underflow 247 620, uniform 247 621, wide 247 620, zero 247 618, zerowhole 495 236.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25163 (clang18-fixup-call/cxx, linux-x86-64):
  ball_add_2_full binary32 -0x1.fffff8p-127 0x0p+0 0x1.fffffep+126 -0x1.e8aac4p+127 -0x1p+103 0x1.fca98p+101 #extreme:1468688 -> -0x1.e8aac4p+127 -0x1p+103 0x1.000002p+127
smallest radius slack, gaps, interpreter 1.75 (fp:3:-3:0, every operand):
  ball_add_2_full fp:3:-3:0 -0x1.cp+2 -0x1.8p-2 0x1p-2 0x1.4p+2 0x1p-3 0x1.8p+1 #exhaustive:6778 -> -0x1p+1 -0x1p-2 0x1.4p+2
```

### `ball_make_1`

Claims: `makes_ball(cw, rw) from center c, radius r`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 476 | 5 476 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 444 | 1 444 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: badradius 899 998, extreme 449 999, halfgap 900 001, nonfinite 899 998, overflow 449 999, pow2 450 002, underflow 450 002, uniform 450 002, zero 449 999; `binary32`: badradius 899 998, extreme 449 999, halfgap 900 001, nonfinite 899 998, overflow 449 999, pow2 450 002, underflow 450 002, uniform 450 002, zero 449 999.

### `ball_make_2`

Claims: `makes_ball(cw, rw) from center c, radius r`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: badradius 866 664, extreme 433 333, halfgap 866 668, nonfinite 866 664, overflow 433 333, pow2 433 335, underflow 433 335, uniform 433 335, zero 433 333; `binary32`: badradius 866 664, extreme 433 333, halfgap 866 668, nonfinite 866 664, overflow 433 333, pow2 433 335, underflow 433 335, uniform 433 335, zero 433 333.

### `ball_mul_1`

Claims: `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 92 233 392 | 0 | 1.55811 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 91 893 636 | 0 | 1.53530 | 1.000000170 |
| `fp:3:-6:2`, every operand (p = min_precision + 2, another exponent range) | 9 985 600 | 5 328 700 | 0 | 1.85352 | 1.47074 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 371 600 | 891 164 | 0 | 1.85352 | 1.50367 |
| `fp:2:-7:3`, every operand (p = min_precision + 1, another exponent range) | 1 272 384 | 739 313 | 0 | 2.05078 | 2.61224 |
| `fp:2:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 142 884 | 56 255 | 0 | 2.05078 | 2.61224 |
| `fp:4:-4:1`, every operand (quick tier + 2 bits) | 38 638 656 | 10 981 732 | 0 | 1.60547 | 1.17089 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 415 385, centerpow2 830 769, exact 415 385, extreme 415 384, overflow 415 384, pow2 415 384, radii 830 770, underflow 415 385, uniform 415 386, wide 415 385, zero 415 383; `binary32`: cancel 415 385, centerpow2 830 769, exact 415 385, extreme 415 384, overflow 415 384, pow2 415 384, radii 830 770, underflow 415 385, uniform 415 386, wide 415 385, zero 415 383.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.53530 (msvc-fixup-call/cxx, windows-x64):
  ball_mul_1 binary32 -0x1.11d222p+122 0x1.fffffep+127 0x1.cc788p-116 0x1.000108p-109 #wide:513268 -> -0x1.ec86780000000p+6 0x1.07e1480000000p+19
smallest radius slack, gaps, interpreter 1.60547 (fp:4:-4:1, every operand):
  ball_mul_1 fp:4:-4:1 -0x1.cp-1 0x1.ep+3 -0x1p-4 0x1.2p+0 #exhaustive:14567129 -> 0x1p-4 0x1.6p+4
```

### `ball_mul_1_full`

Claims: `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.53354 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.68157 | 1.000000177 |
| `fp:2:-7:6`, every operand (p = min_precision, another number of exponents) | 3 139 984 | 3 139 984 | 0 | 2.05078 | 2.61224 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1.85352 | 1.50367 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 2.05078 | 2.61224 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 2.05078 | 2.61224 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 469 564, cancel 234 782, centerpow2 469 566, exact 234 784, extreme 234 782, hugeradius 469 564, nonfinite 469 564, overflow 234 782, pow2 234 782, radii 469 568, underflow 234 782, uniform 234 785, wide 234 785, zero 234 782, zeroinf 469 564, zerowhole 469 564; `binary32`: ballstates 469 564, cancel 234 782, centerpow2 469 566, exact 234 784, extreme 234 782, hugeradius 469 564, nonfinite 469 564, overflow 234 782, pow2 234 782, radii 469 568, underflow 234 782, uniform 234 785, wide 234 785, zero 234 782, zeroinf 469 564, zerowhole 469 564.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.53354 (msvc-fixup-call/cxx, windows-x64):
  ball_mul_1_full binary64 -0x1.fc8dd3592c02ep+732 0x1.9c45a6bfbd92dp+736 0x1p-1074 0x1.4e155fcp-1048 #radii:635353 -> -0x1.fc8dd3592c02ep-342 0x1.21c001ec30986p-311
smallest radius slack, gaps, interpreter 1.85352 (fp:3:-4:1, every operand):
  ball_mul_1_full fp:3:-4:1 -0x1.cp-2 0x1.8p+0 -0x1.4p-2 0x1.8p+1 #exhaustive:885742 -> 0x1p-3 0x1.4p+3
```

### `ball_mul_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 87 402 624 | 0 | 2.50406 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 85 069 980 | 0 | 2.50150 | 1.000000270 |
| `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1.8p+0` (p = min_precision, the quick tier's format) | 27 342 441 | 4 110 469 | 0 | 2.32227 | 1.30925 |
| `fp:4:-5:1`, restricted: `cx.lead=0:0`, `cy.lead=0:0` (p = min_precision, the quick tier's format) | 15 745 024 | 8 811 524 | 0 | 2.16797 | 1.26108 |
| `fp:4:-5:-3`, every operand (p = min_precision, another exponent range) | 15 492 096 | 5 471 272 | 0 | 4.5625 | 1.69724 |
| `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `ry.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `cx.lead=0:0` (p = min_precision, the quick tier's format) | 2 701 650 | 1 199 458 | 0 | 2.19141 | 1.32186 |
| `fp:5:-4:1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1.8p+0`, `cx.lead=0:0` (p = min_precision + 1, another exponent range) | 580 320 | 364 016 | 0 | 3.95312 | 1.26291 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 400 000, centerpow2 800 000, exact 400 000, extreme 400 000, overflow 400 000, pow2 400 000, radii 800 000, underflow 400 000, uniform 400 001, wide 400 000, zero 399 999; `binary32`: cancel 400 000, centerpow2 800 000, exact 400 000, extreme 400 000, overflow 400 000, pow2 400 000, radii 800 000, underflow 400 000, uniform 400 001, wide 400 000, zero 399 999.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 2.50150 (clang-fixup-inline/cxx, macos-arm64):
  ball_mul_2 binary32 -0x1p-104 0x1p-129 0x1.0dab84p-104 0x1p+105 0x1p+81 0x1.e49faap+80 #pow2:381677 -> -0x1p+1 -0x1p-24 0x1.0dab8cp+1
smallest radius slack, gaps, interpreter 2.16797 (fp:4:-5:1, restricted: cx.lead=0:0, cy.lead=0:0):
  ball_mul_2 fp:4:-5:1 -0x1.8p+0 -0x1p-4 0x1.cp+0 -0x1p+0 -0x1p-4 0x1.8p+0 #exhaustive:2914268 -> 0x1.ap+0 0x1p-5 0x1.2p+3
```

### `ball_mul_2_full`

Claims: `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 2.57630 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 2.50000 | 1.000000280 |
| `fp:4:-4:-1`, every operand (p = min_precision, the quick tier's format) | 97 653 924 | 97 653 924 | 0 | 3.125 | 1.43177 |
| `fp:4:-5:0`, restricted: `cx.lead=0:0`, `cy.lead=0:0` (p = min_precision, another number of exponents) | 12 068 676 | 12 068 676 | 0 | 2.16797 | 1.26108 |
| `fp:4:-3:-2`, every operand (p = min_precision, another number of exponents) | 2 149 156 | 2 149 156 | 0 | 6.75 | 2.30769 |
| `fp:4:-4:-1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0` (p = min_precision, the quick tier's format) | 980 100 | 980 100 | 0 | 3.28125 | 1.49416 |
| `fp:5:-5:-2`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `cx.lead=0:0` (p = min_precision + 1, quick tier + 1 bit) | 503 500 | 503 500 | 0 | 5.11719 | 1.27949 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 452 172, cancel 226 087, centerpow2 452 176, exact 226 089, extreme 226 086, hugeradius 452 172, nonfinite 452 172, overflow 226 087, pow2 226 087, radii 452 177, underflow 226 087, uniform 226 089, wide 226 089, zero 226 086, zeroinf 452 172, zerowhole 452 172; `binary32`: ballstates 452 172, cancel 226 087, centerpow2 452 176, exact 226 089, extreme 226 086, hugeradius 452 172, nonfinite 452 172, overflow 226 087, pow2 226 087, radii 452 177, underflow 226 087, uniform 226 089, wide 226 089, zero 226 086, zeroinf 452 172, zerowhole 452 172.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 2.50000 (clang-fixup-inline/cxx, macos-arm64):
  ball_mul_2_full binary32 -0x1p+50 -0x1.fffffep+24 0x1p+50 -0x1p-47 -0x1.fffffep-72 0x1p-71 #pow2:1344866 -> 0x1.000002p+3 -0x1.000004p-22 0x1.000008p+3
smallest radius slack, gaps, interpreter 2.16797 (fp:4:-5:0, restricted: cx.lead=0:0, cy.lead=0:0):
  ball_mul_2_full fp:4:-5:0 -0x1.8p+0 -0x1p-4 0x1.cp+0 -0x1p+0 -0x1p-4 0x1.8p+0 #exhaustive:2245744 -> 0x1.ap+0 0x1p-5 0x1.2p+3
```

### `ball_neg_1`

Claims: `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 0 | 1 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 0 | 1 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 | 0 | 1 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 | 0 | 1 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 | 0 | 1 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 358 | 5 358 | 0 | 0 | 1 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 328 | 1 328 | 0 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 514 284, cancel 257 144, centerpow2 514 287, exact 257 144, extreme 257 142, hugeradius 514 284, nonfinite 514 284, overflow 257 143, pow2 257 142, radii 514 288, underflow 257 143, uniform 257 145, wide 257 144, zero 257 142, zerowhole 514 284; `binary32`: ballstates 514 284, cancel 257 144, centerpow2 514 287, exact 257 144, extreme 257 142, hugeradius 514 284, nonfinite 514 284, overflow 257 143, pow2 257 142, radii 514 288, underflow 257 143, uniform 257 145, wide 257 144, zero 257 142, zerowhole 514 284.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_neg_1 binary64 -0x1.ffffffffffffep-1023 0x1p+1021 #ballstates:15 -> 0x0.fffffffffffffp-1022 0x1p+1021
smallest radius slack, gaps, interpreter 0 (fp:7:-11:0, every operand):
  ball_neg_1 fp:7:-11:0 -0x1.fcp+6 0x0p+0 #exhaustive:0 -> 0x1.fcp+6 0x0p+0
```

### `ball_neg_2`

Claims: `normalized(cz)`; `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0 | 1 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0 | 1 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 | 0 | 1 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 | 0 | 1 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 | 0 | 1 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 35 390 | 35 390 | 0 | 0 | 1 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 888 | 5 888 | 0 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 476 188, cancel 238 096, centerpow2 476 193, exact 238 097, extreme 238 094, hugeradius 476 188, nonfinite 476 188, overflow 238 096, pow2 238 095, radii 476 193, underflow 238 096, uniform 238 097, wide 238 097, zero 238 094, zerowhole 476 188; `binary32`: ballstates 476 188, cancel 238 096, centerpow2 476 193, exact 238 097, extreme 238 094, hugeradius 476 188, nonfinite 476 188, overflow 238 096, pow2 238 095, radii 476 193, underflow 238 096, uniform 238 097, wide 238 097, zero 238 094, zerowhole 476 188.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_neg_2 binary64 -0x1.2cb10863e5393p+858 0x1.03894e8e2b9a2p+802 0x1.b281399aef3c8p+858 #ballstates:36 -> 0x1.2cb10863e5393p+858 -0x1.03894e8e2b9a2p+802 0x1.b281399aef3c8p+858
smallest radius slack, gaps, interpreter 0 (fp:6:-8:-1, every operand):
  ball_neg_2 fp:6:-8:-1 -0x1.f8p+4 -0x1.f8p-3 0x0p+0 #exhaustive:0 -> 0x1.f8p+4 0x1.f8p-3 0x0p+0
```

### `ball_scale_1`

Claims: `encloses(cz, rz) x*a over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 93 378 468 | 0 | 1.00000 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 91 505 196 | 0 | 1.000000119 | 1.000000108 |
| `fp:5:-5:0`, every operand (quick tier + 2 bits) | 5 569 648 | 3 257 050 | 0 | 1.625 | 1.08696 |
| `fp:4:-8:2`, every operand (another exponent range) | 3 502 176 | 2 726 994 | 0 | 1.125 | 1.12676 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 689 976 | 489 850 | 0 | 1.125 | 1.12676 |
| `fp:3:-8:2`, every operand (p = min_precision + 2, another exponent range) | 433 200 | 359 094 | 0 | 1 | 1.2 |
| `fp:3:-5:0`, every operand (p = min_precision + 2, the quick tier's format) | 84 700 | 67 922 | 0 | 1 | 1.2 |
| `fp:2:-5:0`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 206 | 9 064 | 0 | 1.4375 | 1.6 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 415 385, centerpow2 830 769, exact 415 385, extreme 415 384, overflow 415 384, pow2 415 384, radii 830 770, underflow 415 385, uniform 415 386, wide 415 385, zero 415 383; `binary32`: cancel 415 385, centerpow2 830 769, exact 415 385, extreme 415 384, overflow 415 384, pow2 415 384, radii 830 770, underflow 415 385, uniform 415 386, wide 415 385, zero 415 383.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64):
  ball_scale_1 binary64 -0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 0x1.0000000000001p-1022 #extreme:83536 -> -0x1p+2 0x1.0000000000002p+2
smallest radius slack, gaps, interpreter 1 (fp:3:-8:2, every operand):
  ball_scale_1 fp:3:-8:2 -0x1.8p+4 0x1.8p+4 -0x1.8p-1 #exhaustive:8951 -> 0x1p+4 0x1.8p+4
```

### `ball_scale_1_full`

Claims: `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.00000 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.000000119 | 1.000000109 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 708 852 | 708 852 | 0 | 1.125 | 1.12676 |
| `fp:3:-6:3`, every operand (p = min_precision + 1, another number of exponents) | 344 700 | 344 700 | 0 | 1 | 1.2 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 89 436 | 89 436 | 0 | 1 | 1.2 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 11 400 | 11 400 | 0 | 1.4375 | 1.6 |
| `fp:2:-8:7`, every operand (p = min_precision, another number of exponents) | 159 600 | 159 600 | 0 | 1.4375 | 1.6 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 469 564, cancel 234 782, centerpow2 469 566, exact 234 784, extreme 234 782, hugeradius 469 564, nonfinite 469 564, overflow 234 782, pow2 234 782, radii 469 568, underflow 234 782, uniform 234 785, wide 234 785, zero 234 782, zeroinf 469 564, zerowhole 469 564; `binary32`: ballstates 469 564, cancel 234 782, centerpow2 469 566, exact 234 784, extreme 234 782, hugeradius 469 564, nonfinite 469 564, overflow 234 782, pow2 234 782, radii 469 568, underflow 234 782, uniform 234 785, wide 234 785, zero 234 782, zeroinf 469 564, zerowhole 469 564.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64):
  ball_scale_1_full binary64 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 0x1.0000000000001p-1022 #extreme:23287 -> 0x1p+2 0x1.0000000000002p+2
smallest radius slack, gaps, interpreter 1 (fp:3:-6:3, every operand):
  ball_scale_1_full fp:3:-6:3 -0x1.8p+5 0x1.8p+5 -0x1.8p-1 #exhaustive:7765 -> 0x1p+5 0x1.8p+5
```

### `ball_scale_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x*a over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 87 612 192 | 0 | 1.375 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 85 079 340 | 0 | 1.37500 | 1.000000139 |
| `fp:4:-4:1`, every operand (quick tier + 2 bits) | 6 160 056 | 2 659 714 | 0 | 1.53125 | 1.18081 |
| `fp:3:-6:2`, every operand (p = min_precision + 1, another exponent range) | 4 294 440 | 2 861 126 | 0 | 1.375 | 1.29730 |
| `fp:2:-8:3`, every operand (p = min_precision, another exponent range) | 1 133 730 | 905 462 | 0 | 1.46875 | 1.68977 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 651 420 | 374 170 | 0 | 1.40625 | 1.30612 |
| `fp:2:-4:1`, every operand (p = min_precision, the quick tier's format) | 60 102 | 43 522 | 0 | 1.46875 | 1.68977 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 384 615, centerpow2 769 231, exact 384 616, extreme 384 615, overflow 384 615, pow2 384 615, radii 769 232, underflow 384 615, uniform 384 616, wide 384 616, zero 384 614; `binary32`: cancel 384 615, centerpow2 769 231, exact 384 616, extreme 384 615, overflow 384 615, pow2 384 615, radii 769 232, underflow 384 615, uniform 384 616, wide 384 616, zero 384 614.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.375 (clang18-fixup-call/cxx, linux-x86-64):
  ball_scale_2 binary64 0x1.9347fed5e99e2p+415 0x1.ee9211c2a6a68p+361 0x1.f52d679e3f77fp+363 0x1.4p+268 #radii:1633390 -> 0x1.f819fe8b6405bp+683 0x1.a8da58cd414p+627 0x1.393c60c2e7ab1p+632
smallest radius slack, gaps, interpreter 1.375 (fp:3:-6:2, every operand):
  ball_scale_2 fp:3:-6:2 -0x1.8p+4 -0x1p+0 0x1.8p+3 -0x1.8p-1 #exhaustive:163867 -> 0x1.4p+4 -0x1p+0 0x1.8p+3
```

### `ball_scale_2_full`

Claims: `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 1.34077 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 1.37502 | 1.000000135 |
| `fp:4:-4:-1`, every operand (quick tier + 1 bit) | 810 324 | 810 324 | 0 | 2.44531 | 1.28584 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, another number of exponents) | 687 068 | 687 068 | 0 | 1.40625 | 1.30612 |
| `fp:2:-4:3`, every operand (p = min_precision, another number of exponents) | 223 744 | 223 744 | 0 | 1.46875 | 1.68977 |
| `fp:3:-3:0`, every operand (p = min_precision + 1, the quick tier's format) | 100 044 | 100 044 | 0 | 2.26562 | 1.53425 |
| `fp:2:-2:1`, every operand (p = min_precision, the quick tier's number of exponents) | 12 144 | 12 144 | 0 | 1.8125 | 2.46154 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 434 780, cancel 217 392, centerpow2 434 785, exact 217 393, extreme 217 391, hugeradius 434 780, nonfinite 434 781, overflow 217 392, pow2 217 392, radii 434 785, underflow 217 392, uniform 217 393, wide 217 393, zero 217 391, zeroinf 434 780, zerowhole 434 780; `binary32`: ballstates 434 780, cancel 217 392, centerpow2 434 785, exact 217 393, extreme 217 391, hugeradius 434 780, nonfinite 434 781, overflow 217 392, pow2 217 392, radii 434 785, underflow 217 392, uniform 217 393, wide 217 393, zero 217 391, zeroinf 434 780, zerowhole 434 780.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.34077 (clang18-fixup-call/cxx, linux-x86-64):
  ball_scale_2_full binary64 0x1.19a3bcaf90745p+503 0x1.e762b08f1c66bp+449 0x1.ac610605ac53p+451 -0x1.3ccd0120a0a3fp-160 #radii:1241959 -> -0x1.5c87a64457d54p+343 -0x1.70491734c1ep+282 0x1.090f6781e69bbp+292
smallest radius slack, gaps, interpreter 1.40625 (fp:3:-4:1, every operand):
  ball_scale_2_full fp:3:-4:1 -0x1.8p+3 -0x1p-3 0x1.8p+2 -0x1.8p-1 #exhaustive:54885 -> 0x1p+3 0x1p+0 0x1.8p+2
```

### `ball_sub_1`

Claims: `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 108 399 528 | 0 | 1 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 108 291 516 | 0 | 1 | 1.000000099 |
| `fp:4:-3:1`, every operand (quick tier + 2 bits) | 20 793 600 | 14 367 516 | 0 | 1.625 | 1.20930 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, another exponent range) | 4 064 256 | 3 025 751 | 0 | 1 | 1.2 |
| `fp:2:-6:4`, every operand (p = min_precision + 1, another exponent range) | 1 272 384 | 994 044 | 0 | 1 | 1.33333 |
| `fp:3:-3:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 1 272 384 | 807 559 | 0 | 1 | 1.2 |
| `fp:2:-3:1`, every operand (p = min_precision + 1, the quick tier's format) | 76 176 | 38 412 | 0 | 1 | 1.33333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 415 385, centerpow2 830 769, exact 415 385, extreme 415 384, overflow 415 384, pow2 415 384, radii 830 770, underflow 415 385, uniform 415 386, wide 415 385, zero 415 383; `binary32`: cancel 415 385, centerpow2 830 769, exact 415 385, extreme 415 384, overflow 415 384, pow2 415 384, radii 830 770, underflow 415 385, uniform 415 386, wide 415 385, zero 415 383.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  ball_sub_1 binary64 0x1.fffffffffffffp+1023 0x1.000000000001p+1023 0x1.ffffffffffffdp+1022 0x1.b13be48e8ab28p+1019 #overflow:77983 -> 0x1p+1023 0x1.1b13be48e8ac4p+1023
smallest radius slack, gaps, interpreter 1 (fp:3:-4:2, every operand):
  ball_sub_1 fp:3:-4:2 -0x1.cp+4 0x1p+1 -0x1.4p+3 0x1p+4 #exhaustive:32476 -> -0x1p+4 0x1.8p+4
```

### `ball_sub_1_full`

Claims: `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1 | 1.000000095 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1 | 1.2 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 1 | 1.33333 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 1 | 1.33333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 514 284, cancel 257 144, centerpow2 514 287, exact 257 144, extreme 257 142, hugeradius 514 284, nonfinite 514 284, overflow 257 143, pow2 257 142, radii 514 288, underflow 257 143, uniform 257 145, wide 257 144, zero 257 142, zerowhole 514 284; `binary32`: ballstates 514 284, cancel 257 144, centerpow2 514 287, exact 257 144, extreme 257 142, hugeradius 514 284, nonfinite 514 284, overflow 257 143, pow2 257 142, radii 514 288, underflow 257 143, uniform 257 145, wide 257 144, zero 257 142, zerowhole 514 284.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  ball_sub_1_full binary64 0x1.fffffffffffffp+1023 0x1p+1021 0x1.ffffffffffffdp+1022 0x1.ffffffffffffdp+1022 #ballstates:78073 -> 0x1p+1023 0x1.4p+1023
smallest radius slack, gaps, interpreter 1 (fp:3:-4:1, every operand):
  ball_sub_1_full fp:3:-4:1 -0x1.cp+3 0x1p+0 -0x1.4p+2 0x1p+3 #exhaustive:18696 -> -0x1p+3 0x1.8p+3
```

### `ball_sub_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 102 301 560 | 0 | 1.25107 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 102 219 012 | 0 | 1.25003 | 1.000000143 |
| `fp:3:-3:1`, every operand (p = min_precision, another exponent range) | 32 901 696 | 15 977 235 | 0 | 1.4375 | 1.31507 |
| `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision + 1, quick tier + 1 bit) | 15 713 296 | 11 654 256 | 0 | 3.75 | 1.5 |
| `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` (p = min_precision, the quick tier's format) | 8 767 521 | 4 968 972 | 0 | 1.46875 | 1.41593 |
| `fp:3:-3:2`, restricted: `cx.lead=-1:0` (p = min_precision, the quick tier's format) | 7 295 904 | 5 136 540 | 0 | 1.25 | 1.31507 |
| `fp:3:-2:1`, every operand (p = min_precision, another exponent range) | 5 664 400 | 2 192 431 | 0 | 1.75 | 1.52381 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 384 615, centerpow2 769 231, exact 384 616, extreme 384 615, overflow 384 615, pow2 384 615, radii 769 232, underflow 384 615, uniform 384 616, wide 384 616, zero 384 614; `binary32`: cancel 384 615, centerpow2 769 231, exact 384 616, extreme 384 615, overflow 384 615, pow2 384 615, radii 769 232, underflow 384 615, uniform 384 616, wide 384 616, zero 384 614.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25003 (msvc-fixup-call/cxx, windows-x64):
  ball_sub_2 binary32 -0x1.91b96cp+124 -0x1.88d46cp+96 0x1.ffefe8p+101 -0x1.4375aep+103 -0x1.84afd2p+66 0x1.fffffep+126 #radii:38641 -> -0x1.91b9620000000p+124 0x1.9014a00000000p+93 0x1.0000020000000p+127
smallest radius slack, gaps, interpreter 1.25 (fp:3:-3:2, restricted: cx.lead=-1:0):
  ball_sub_2 fp:3:-3:2 -0x1.cp+0 0x0p+0 0x1.cp-1 -0x1p+3 -0x1.cp-1 0x1.cp+3 #exhaustive:86851 -> 0x1.cp+2 0x0p+0 0x1.4p+4
```

### `ball_sub_2_full`

Claims: `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 1.25606 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 1.25152 | 1.000000143 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 | 1.75 | 1.52381 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 | 2 | 1.52381 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 | 5.5 | 1.76471 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 476 188, cancel 238 096, centerpow2 476 193, exact 238 097, extreme 238 094, hugeradius 476 188, nonfinite 476 188, overflow 238 096, pow2 238 095, radii 476 193, underflow 238 096, uniform 238 097, wide 238 097, zero 238 094, zerowhole 476 188; `binary32`: ballstates 476 188, cancel 238 096, centerpow2 476 193, exact 238 097, extreme 238 094, hugeradius 476 188, nonfinite 476 188, overflow 238 096, pow2 238 095, radii 476 193, underflow 238 096, uniform 238 097, wide 238 097, zero 238 094, zerowhole 476 188.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25152 (msvc-fixup-call/cxx, windows-x64):
  ball_sub_2_full binary32 0x1.85e952p+35 0x1p+7 0x1.fffffep+125 0x1.3d35bcp+94 -0x1p+66 0x1.fce59ep+100 #radii:650308 -> -0x1.3d35bc0000000p+94 0x1.0000000000000p+66 0x1.0000020000000p+126
smallest radius slack, gaps, interpreter 1.75 (fp:3:-3:0, every operand):
  ball_sub_2_full fp:3:-3:0 -0x1.cp+2 -0x1.8p-2 0x1p-2 -0x1.cp+2 -0x1.8p-2 0x1.8p+1 #exhaustive:4778 -> 0x0p+0 0x0p+0 0x1.4p+2
```

### `eq_2_1`

Claims: `predicate(m) eq(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 15 900 936; false 94 499 064; a non-finite operand, false 13 034 208; a non-finite operand, true 765 792 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 17 315 232; false 93 084 768; a non-finite operand, false 13 035 492; a non-finite operand, true 764 508 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 353; false 5 743 651; a non-finite operand, false 49 729; a non-finite operand, true 2 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 241; false 3 430 835; a non-finite operand, false 43 249; a non-finite operand, true 2 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 449; false 1 829 251; a non-finite operand, false 13 537; a non-finite operand, true 2 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 225; false 455 843; a non-finite operand, false 6 721; a non-finite operand, true 2 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 57; false 24 651; a non-finite operand, false 1 441; a non-finite operand, true 2 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 29; false 4 831; a non-finite operand, false 565; a non-finite operand, true 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `eq_2_2`

Claims: `predicate(m) eq(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 28 455 684; false 81 944 316; a non-finite operand, false 13 030 764; a non-finite operand, true 769 236 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 29 436 228; false 80 963 772; a non-finite operand, false 13 037 580; a non-finite operand, true 762 420 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | true 2 753; false 7 581 763; a non-finite operand, false 16 513; a non-finite operand, true 2 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | true 2 017; false 4 070 307; a non-finite operand, false 12 097; a non-finite operand, true 2 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 3 247 204 | 3 247 204 | 0 | true 1 801; false 3 245 403; a non-finite operand, false 10 801; a non-finite operand, true 2 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | true 993; false 987 043; a non-finite operand, false 5 953; a non-finite operand, true 2 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 181 476 | 181 476 | 0 | true 425; false 181 051; a non-finite operand, false 2 545; a non-finite operand, true 2 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | true 161; false 26 083; a non-finite operand, false 961; a non-finite operand, true 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `fast_two_sum`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`; `normalized(r)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 114 602 568 | 0 | 0 (exact) | 0 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 114 592 560 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 2 654 207 | 2 637 823 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 1 384 447 | 1 368 063 | 0 | 0 (exact) | - |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 346 111 | 342 015 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 5 407 | 5 343 | 0 | 0 (exact) | 0 |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 1 351 | 1 335 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999; `binary32`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999.

### `le_1_2`

Claims: `predicate(m) le(a, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 68 763 156; false 41 636 844; a non-finite operand, false 9 210 420; a non-finite operand, true 4 589 580 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 69 195 732; false 41 204 268; a non-finite operand, false 9 198 516; a non-finite operand, true 4 601 484 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 889; false 2 880 115; a non-finite operand, false 33 154; a non-finite operand, true 16 577 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 449; false 1 722 627; a non-finite operand, false 28 834; a non-finite operand, true 14 417 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 817; false 916 883; a non-finite operand, false 9 026; a non-finite operand, true 4 513 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 227 025; false 229 043; a non-finite operand, false 4 482; a non-finite operand, true 2 241 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 141; false 12 567; a non-finite operand, false 962; a non-finite operand, true 481 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 349; false 2 511; a non-finite operand, false 378; a non-finite operand, true 189 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `le_2_1`

Claims: `predicate(m) le(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 60 707 172; false 49 692 828; a non-finite operand, false 9 210 828; a non-finite operand, true 4 589 172 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 61 467 456; false 48 932 544; a non-finite operand, false 9 211 032; a non-finite operand, true 4 588 968 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 889; false 2 880 115; a non-finite operand, false 33 154; a non-finite operand, true 16 577 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 449; false 1 722 627; a non-finite operand, false 28 834; a non-finite operand, true 14 417 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 817; false 916 883; a non-finite operand, false 9 026; a non-finite operand, true 4 513 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 227 025; false 229 043; a non-finite operand, false 4 482; a non-finite operand, true 2 241 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 141; false 12 567; a non-finite operand, false 962; a non-finite operand, true 481 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 349; false 2 511; a non-finite operand, false 378; a non-finite operand, true 189 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `le_2_2`

Claims: `predicate(m) le(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 67 028 256; false 43 371 744; a non-finite operand, false 9 201 084; a non-finite operand, true 4 598 916 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 67 514 292; false 42 885 708; a non-finite operand, false 9 209 580; a non-finite operand, true 4 590 420 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | true 3 790 881; false 3 793 635; a non-finite operand, false 11 010; a non-finite operand, true 5 505 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | true 2 035 153; false 2 037 171; a non-finite operand, false 8 066; a non-finite operand, true 4 033 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 3 247 204 | 3 247 204 | 0 | true 1 622 701; false 1 624 503; a non-finite operand, false 7 202; a non-finite operand, true 3 601 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | true 493 521; false 494 515; a non-finite operand, false 3 970; a non-finite operand, true 1 985 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 181 476 | 181 476 | 0 | true 90 525; false 90 951; a non-finite operand, false 1 698; a non-finite operand, true 849 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | true 13 041; false 13 203; a non-finite operand, false 642; a non-finite operand, true 321 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `lt_1_2`

Claims: `predicate(m) lt(a, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 36 915 552; false 73 484 448; a non-finite operand, false 9 963 708; a non-finite operand, true 3 836 292 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 36 505 224; false 73 894 776; a non-finite operand, false 9 968 868; a non-finite operand, true 3 831 132 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 536; false 2 880 468; a non-finite operand, false 33 156; a non-finite operand, true 16 575 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 208; false 1 722 868; a non-finite operand, false 28 836; a non-finite operand, true 14 415 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 368; false 917 332; a non-finite operand, false 9 028; a non-finite operand, true 4 511 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 226 800; false 229 268; a non-finite operand, false 4 484; a non-finite operand, true 2 239 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 084; false 12 624; a non-finite operand, false 964; a non-finite operand, true 479 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 320; false 2 540; a non-finite operand, false 380; a non-finite operand, true 187 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `lt_2_1`

Claims: `predicate(m) lt(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 44 859 432; false 65 540 568; a non-finite operand, false 9 962 280; a non-finite operand, true 3 837 720 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 44 139 288; false 66 260 712; a non-finite operand, false 9 962 760; a non-finite operand, true 3 837 240 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 536; false 2 880 468; a non-finite operand, false 33 156; a non-finite operand, true 16 575 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 208; false 1 722 868; a non-finite operand, false 28 836; a non-finite operand, true 14 415 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 368; false 917 332; a non-finite operand, false 9 028; a non-finite operand, true 4 511 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 226 800; false 229 268; a non-finite operand, false 4 484; a non-finite operand, true 2 239 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 084; false 12 624; a non-finite operand, false 964; a non-finite operand, true 479 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 320; false 2 540; a non-finite operand, false 380; a non-finite operand, true 187 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `lt_2_2`

Claims: `predicate(m) lt(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 38 570 208; false 71 829 792; a non-finite operand, false 9 974 712; a non-finite operand, true 3 825 288 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | true 38 087 208; false 72 312 792; a non-finite operand, false 9 971 532; a non-finite operand, true 3 828 468 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | true 3 788 128; false 3 796 388; a non-finite operand, false 11 012; a non-finite operand, true 5 503 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | true 2 033 136; false 2 039 188; a non-finite operand, false 8 068; a non-finite operand, true 4 031 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 3 247 204 | 3 247 204 | 0 | true 1 620 900; false 1 626 304; a non-finite operand, false 7 204; a non-finite operand, true 3 599 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | true 492 528; false 495 508; a non-finite operand, false 3 972; a non-finite operand, true 1 983 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 181 476 | 181 476 | 0 | true 90 100; false 91 376; a non-finite operand, false 1 700; a non-finite operand, true 847 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | true 12 880; false 13 364; a non-finite operand, false 644; a non-finite operand, true 319 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500; `binary32`: equal 625 000, extreme 312 500, halfgap 312 500, lastplace 625 000, leadequal 312 500, neighbor 312 500, nonfinite 625 000, overflow 312 500, pow2 312 500, straddle 312 500, underflow 312 500, uniform 312 500, zero 312 500.

### `make_2`

Claims: `represents(x)`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 827 394 | 827 394 | 0 |
| `fp:13:-31:8`, every operand (quick tier + 2 bits) | 335 874 | 335 874 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 167 938 | 167 938 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 330 | 330 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 166 | 166 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 540 000, halfgap 1 080 000, nonfinite 1 080 000, overflow 540 000, pow2 540 000, underflow 540 000, uniform 540 000, zero 540 000; `binary32`: extreme 540 000, halfgap 1 080 000, nonfinite 1 080 000, overflow 540 000, pow2 540 000, underflow 540 000, uniform 540 000, zero 540 000.

### `make_2_limbs`

Claims: `represents(x)`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 500 000, halfgap 1 000 000, nonfinite 1 000 000, overflow 500 000, pow2 500 000, underflow 500 000, uniform 500 000, zero 500 000; `binary32`: extreme 500 000, halfgap 1 000 000, nonfinite 1 000 000, overflow 500 000, pow2 500 000, underflow 500 000, uniform 500 000, zero 500 000.

### `mul_1_1`

Claims: `rounded(p) nearest`; `error(p) form R, c=1/(1+u), k=1, t=1/2`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 94 270 848 | 0 | exact 33 998 640; inexact 60 197 760; tie 74 448 | 1 - ε, ε < 10⁻⁹ | 1.00000 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 94 996 140 | 0 | exact 34 209 960; inexact 60 538 632; tie 247 548 | 0.9999999404 | 0.9999998212 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | exact 114 689; inexact 3 989 676; tie 75 928 | 0.999939 | 0.992248 |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | exact 145 697; inexact 1 967 764; tie 84 024 | 0.999756 | 0.992248 |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | exact 118 385; inexact 2 267 576; tie 74 352 | 0.999512 | 0.992248 |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | exact 49 985; inexact 559 608; tie 27 888 | 0.999512 | 0.984615 |
| `fp:3:-12:-1`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 481 | 0 | exact 2 921; inexact 6 128; tie 1 432 | 0.999512 | 0.888889 |
| `fp:2:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 597 | 0 | exact 1 089; inexact 1 364; tie 144 | 0.833333 | 0.444444 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 675 000, halfgap 1 350 000, overflow 675 000, pow2 675 000, underflow 675 000, uniform 675 000, zero 675 000; `binary32`: extreme 675 000, halfgap 1 350 000, overflow 675 000, pow2 675 000, underflow 675 000, uniform 675 000, zero 675 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  mul_1_1 binary64 -0x1p-872 0x1p-203 #pow2:26890 -> -0x0p+0
largest error / bound, interpreter 0.999939 (fp:7:-20:-6, every operand):
  mul_1_1 fp:7:-20:-6 -0x1.8p+0 -0x1.58p-1 #exhaustive:63562 -> 0x1p+0
```

### `mul_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 105 709 800 | 0 | 1 - ε, ε < 10⁻⁹ | 1.95325 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 105 582 588 | 0 | 0.9999998510 | 1.91049 |
| `fp:6:-8:-2`, every operand (quick tier + 2 bits) | 4 152 897 | 2 754 581 | 0 | 0.972718 | - |
| `fp:5:-4:2`, every operand (another exponent range) | 1 027 905 | 304 717 | 0 | 0.907265 | - |
| `fp:3:-8:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 42 273 | 41 241 | 0 | 0.794235 | - |
| `fp:2:-8:-2`, every operand (p = min_precision, the quick tier's exponent range) | 7 285 | 7 285 | 0 | 0.628272 | 0.410256 |
| `fp:5:-8:-2`, every operand (quick tier + 1 bit) | 1 027 905 | 799 453 | 0 | 0.951325 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665; `binary32`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  mul_2_1 binary64 0x1.8p+0 0x1.fffffffffffffp-54 0x1.0000000000001p-1022 #extreme:1754898 -> 0x1.8000000000003p-1022 0x0p+0
largest error / bound, interpreter 0.972718 (fp:6:-8:-2, every operand):
  mul_2_1 fp:6:-8:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-5 #exhaustive:1480613 -> 0x1.4p-3 0x0p+0
```

### `mul_2_1_full`

Claims: `extends(w) F1-F5, core mul_2_1, lead mul, finite when |x*a| <= 2^(qmax+p-1)`; `F2, core mul_2_1: normalized(z)`; `F2, core mul_2_1: error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 1 - ε, ε < 10⁻⁹ | 1.95613 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.9999997914 | 1.91218 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.951325 | - |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.907193 | 1.23671 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0.972718 | - |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0.936776 | - |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.759322 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | 0.579710 | 0.410256 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 500 000, close 750 000, edge 500 000, extreme 250 000, nonfinite 500 000, overflow 250 000, pow2 250 000, threshold 500 000, underflow 500 000, uniform 250 000, zero 250 000, zeroinf 500 000; `binary32`: cancel 500 000, close 750 000, edge 500 000, extreme 250 000, nonfinite 500 000, overflow 250 000, pow2 250 000, threshold 500 000, underflow 500 000, uniform 250 000, zero 250 000, zeroinf 500 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  mul_2_1_full binary64 0x1.8p+0 0x1p-53 0x1.0000000000001p-1022 #extreme:2587066 -> 0x1.8000000000003p-1022 0x0p+0
largest error / bound, interpreter 0.972718 (fp:6:-7:-2, every operand):
  mul_2_1_full fp:6:-7:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-4 #exhaustive:651814 -> 0x1.4p-2 0x0p+0
```

### `mul_2_2`

Claims: `normalized(z)`; `error(z) form R, c=4, k=2, t=3/2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 107 998 392 | 0 | 0.977185 | 3.33614 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 107 886 720 | 0 | 0.973840 | 3.44280 |
| `fp:5:-8:-2`, every operand (p = min_precision + 1, another exponent range) | 16 248 961 | 6 272 821 | 0 | 0.878457 | - |
| `fp:6:-7:-3`, every operand (quick tier + 2 bits) | 4 124 961 | 1 593 537 | 0 | 0.898829 | - |
| `fp:5:-7:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 014 049 | 606 801 | 0 | 0.864716 | - |
| `fp:4:-7:-3`, every operand (p = min_precision, the quick tier's format) | 245 025 | 209 281 | 0 | 0.791964 | - |
| `fp:4:-9:-3`, every operand (p = min_precision, another exponent range) | 3 038 049 | 2 716 377 | 0 | 0.850806 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332; `binary32`: cancel 866 668, close 1 300 000, extreme 433 333, overflow 433 332, pow2 433 333, underflow 866 667, uniform 433 335, zero 433 332.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.977185 (clang18-fixup-call/cxx, linux-x86-64):
  mul_2_2 binary64 -0x1.331f724cedacp-324 -0x1.a104fef6bdf2fp-409 0x1.dc1f283318051p-653 0x1.b7ebb72c19f4cp-707 #underflow:1593068 -> -0x1.1d99ecc80b96cp-976 0x0.01fe08de7a73cp-1022
largest error / bound, interpreter 0.898829 (fp:6:-7:-3, every operand):
  mul_2_2 fp:6:-7:-3 -0x1.2p-1 0x1p-7 -0x1.2p-1 0x1p-7 #exhaustive:1918208 -> 0x1.3p-2 0x0p+0
```

### `mul_2_2_full`

Claims: `extends(w) F1-F5, core mul_2_2, lead mul, finite when |x*y| <= 2^(qmax+p-1)`; `F2, core mul_2_2: normalized(z)`; `F2, core mul_2_2: error(z) form R, c=4, k=2, t=3/2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.980949 | 3.48733 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.968941 | 3.48859 |
| `fp:4:-6:1`, every operand (p = min_precision, another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.791964 | - |
| `fp:5:-6:-1`, every operand (p = min_precision + 1, another number of exponents) | 4 072 324 | 4 072 324 | 0 | 0.838827 | - |
| `fp:6:-6:-3`, every operand (quick tier + 2 bits) | 1 036 324 | 1 036 324 | 0 | 0.816656 | - |
| `fp:5:-5:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 256 036 | 256 036 | 0 | 0.733319 | - |
| `fp:4:-4:-1`, every operand (p = min_precision, the quick tier's format) | 62 500 | 62 500 | 0 | 0.561075 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 500 000, close 750 000, edge 500 000, extreme 250 000, nonfinite 500 000, overflow 250 000, pow2 250 000, threshold 500 000, underflow 500 000, uniform 250 000, zero 250 000, zeroinf 500 000; `binary32`: cancel 500 000, close 750 000, edge 500 000, extreme 250 000, nonfinite 500 000, overflow 250 000, pow2 250 000, threshold 500 000, underflow 500 000, uniform 250 000, zero 250 000, zeroinf 500 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.980949 (msvc-fixup-call/cxx, windows-x64):
  mul_2_2_full binary64 0x1.7b0a8b8c55727p-430 0x1.0ee62f7b612a1p-498 -0x1.a9b8978f1f637p-568 -0x1.761df6c07053ap-638 #underflow:166763 -> -0x1.3b2ae8d3b432dp-997 -0x0.00000001c9726p-1022
largest error / bound, interpreter 0.838827 (fp:5:-6:-1, every operand):
  mul_2_2_full fp:5:-6:-1 -0x1.4p-1 0x1p-6 -0x1.2p-1 0x1p-6 #exhaustive:1954396 -> 0x1.4p-2 0x0p+0
```

### `mul_pow2_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 103 347 468 | 0 | 0.738546 | 5.55112e-17 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 103 653 528 | 0 | 0.750000 | 2.98023e-8 |
| `fp:6:-12:4`, every operand (another exponent range) | 6 021 994 | 4 488 874 | 0 | 0.746094 | 0.00781249 |
| `fp:7:-6:2`, every operand (quick tier + 2 bits) | 979 185 | 521 971 | 0 | 0.734375 | - |
| `fp:6:-6:2`, every operand (quick tier + 1 bit) | 398 706 | 231 604 | 0 | 0.734375 | - |
| `fp:3:-6:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 14 949 | 11 829 | 0 | 0.71875 | 0.0624390 |
| `fp:2:-6:2`, every operand (p = min_precision, the quick tier's exponent range) | 4 350 | 3 766 | 0 | 0.6875 | 0.124031 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 454 544, halfscaled 909 093, into 909 093, outof 454 546, overflow 454 544, pow2 454 545, underflow 454 544, uniform 454 547, zero 454 544; `binary32`: extreme 454 544, halfscaled 909 093, into 909 093, outof 454 546, overflow 454 544, pow2 454 545, underflow 454 544, uniform 454 547, zero 454 544.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.750000 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_2 binary32 -0x1.6f0f42p-38 -0x1.fffffep-63 0x1p-89 #extreme:938111 -> -0x1.6f0f4p-127 -0x0p+0
largest error / bound, interpreter 0.746094 (fp:6:-12:4, every operand):
  mul_pow2_2 fp:6:-12:4 -0x1.f8p+4 0x1.f8p-3 0x1p-12 #exhaustive:2032404 -> -0x1p-7 0x0p+0
```

### `mul_pow2_2_full`

Claims: `extends(w) F1-F5, core mul_pow2_2, lead mul, finite when |x*c| <= 2^(qmax+p-1)`; `F2, core mul_pow2_2: normalized(z)`; `F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.748915 | 4.25138e-17 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.750000 | 2.98023e-8 |
| `fp:6:-12:3`, every operand (another number of exponents) | 4 803 498 | 4 803 498 | 0 | 0.746094 | 0.00781249 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 456 988 | 456 988 | 0 | 0.746094 | - |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 211 354 | 211 354 | 0 | 0.746094 | - |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 9 860 | 9 860 | 0 | 0.71875 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 2 970 | 2 970 | 0 | 0.6875 | 0.124031 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: edge 526 314, extreme 263 158, halfscaled 526 317, into 526 319, nonfinite 526 314, outof 263 159, overflow 263 158, pow2 263 158, threshold 526 314, underflow 263 158, uniform 263 160, zero 263 157, zeroinf 526 314; `binary32`: edge 526 314, extreme 263 158, halfscaled 526 317, into 526 319, nonfinite 526 314, outof 263 159, overflow 263 158, pow2 263 158, threshold 526 314, underflow 263 158, uniform 263 160, zero 263 157, zeroinf 526 314.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.750000 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_2_full binary32 -0x1.a0c816p-54 0x1.fffffep-79 0x1p-73 #extreme:210738 -> -0x1.a0c818p-127 0x0p+0
largest error / bound, interpreter 0.746094 (fp:6:-12:3, every operand):
  mul_pow2_2_full fp:6:-12:3 -0x1.f8p+4 0x1.f8p-3 0x1p-12 #exhaustive:1467606 -> -0x1p-7 0x0p+0
```

### `neg_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`; `represents(z)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0 (exact) | 0 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | 0 (exact) | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | 0 (exact) | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | 0 (exact) | - |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | 0 (exact) | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 520 000, halfgap 1 040 000, nonfinite 1 040 000, overflow 520 000, pow2 520 000, underflow 520 000, uniform 520 000, zero 520 000; `binary32`: extreme 520 000, halfgap 1 040 000, nonfinite 1 040 000, overflow 520 000, pow2 520 000, underflow 520 000, uniform 520 000, zero 520 000.

### `radd`

Claims: `upper(r) gaps=3/2`.

| Run | Cases | Judged | Failed | largest excess, gaps (claim 3/2) |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.5 (the claim) |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.5 (the claim) |
| `fp:8:-16:3`, every operand (another number of exponents) | 7 236 100 | 7 236 100 | 0 | 1.5 (the claim) |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 2 775 556 | 2 775 556 | 0 | 1.5 (the claim) |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 695 556 | 695 556 | 0 | 1.5 (the claim) |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 2 916 | 2 916 | 0 | 1.5 (the claim) |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 784 | 784 | 0 | 1.25 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: close 415 385, extreme 415 384, nonfinite 830 767, nonneg 830 770, overflow 415 384, pow2 415 385, tie 830 770, underflow 415 385, uniform 415 386, zero 415 384; `binary32`: close 415 385, extreme 415 384, nonfinite 830 767, nonneg 830 770, overflow 415 384, pow2 415 385, tie 830 770, underflow 415 385, uniform 415 386, zero 415 384.

Where the extremes are attained (the line as the oracle reports it):

```
largest excess, gaps (claim 3/2), compiled 1.5 (clang18-fixup-call/cxx, linux-x86-64):
  radd binary64 0x1.2601b201f1cdcp+831 0x1.dbb4535e2c909p+832 #close:4631 -> 0x1.375a962f92bbdp+833
largest excess, gaps (claim 3/2), interpreter 1.5 (fp:8:-16:3, every operand):
  radd fp:8:-16:3 0x1p-16 0x1.02p-8 #exhaustive:2947 -> 0x1.06p-8
```

### `rmul`

Claims: `upper(r) gaps=3/2`.

| Run | Cases | Judged | Failed | largest excess, gaps (claim 3/2) |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.5 (the claim) |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 117 600 000 | 0 | 1.5 (the claim) |
| `fp:8:-16:3`, every operand (another number of exponents) | 7 236 100 | 7 236 100 | 0 | 1.5 (the claim) |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 2 775 556 | 2 775 556 | 0 | 1.5 (the claim) |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 695 556 | 695 556 | 0 | 1.5 (the claim) |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 2 916 | 2 916 | 0 | 1.5 (the claim) |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 784 | 784 | 0 | 1.5 (the claim) |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: close 360 001, extreme 360 001, nonfinite 719 996, nonneg 720 002, overflow 360 001, pow2 360 001, tie 720 002, underflow 360 001, uniform 360 001, zero 359 998, zeroinf 719 996; `binary32`: close 360 001, extreme 360 001, nonfinite 719 996, nonneg 720 002, overflow 360 001, pow2 360 001, tie 720 002, underflow 360 001, uniform 360 001, zero 359 998, zeroinf 719 996.

Where the extremes are attained (the line as the oracle reports it):

```
largest excess, gaps (claim 3/2), compiled 1.5 (clang18-fixup-call/cxx, linux-x86-64):
  rmul binary64 0x1.78d96588ea2d8p+432 0x1.5p-1069 #close:111483 -> 0x1.ee9d5543b35bdp-637
largest excess, gaps (claim 3/2), interpreter 1.5 (fp:8:-16:3, every operand):
  rmul fp:8:-16:3 0x1p-16 0x1.8p+0 #exhaustive:4034 -> 0x1.8p-15
```

### `split`

Claims: `error(r) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 104 074 212 | 0 | 0 (exact) | 0 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 101 742 912 | 0 | 0 (exact) | 0 |
| `fp:13:-60:40`, every operand (another exponent range) | 835 583 | 778 111 | 0 | 0 (exact) | 0 |
| `fp:13:-30:10`, every operand (quick tier + 2 bits) | 344 063 | 286 591 | 0 | 0 (exact) | 0 |
| `fp:12:-30:10`, every operand (quick tier + 1 bit) | 172 031 | 147 329 | 0 | 0 (exact) | 0 |
| `fp:5:-30:10`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 343 | 1 239 | 0 | 0 (exact) | 0 |
| `fp:4:-30:10`, every operand (p = min_precision, the quick tier's exponent range) | 671 | 633 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999; `binary32`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999.

### `sub_1_2`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 108 204 516 | 0 | 0.810049 | 1.62010 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 108 192 684 | 0 | 0.892058 | 1.78412 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665; `binary32`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.892058 (msvc-fixup-call/cxx, windows-x64):
  sub_1_2 binary32 0x1.e49bdep+39 0x1.08a3fep+41 0x1.f53576p+16 #close:724612 -> -0x1.1efa0e0000000p+40 -0x1.ea6af00000000p+15
largest error / bound, interpreter 0.939450 (fp:5:-6:3, every operand):
  sub_1_2 fp:5:-6:3 -0x1.fp+5 -0x1p+7 -0x1.1p+1 #exhaustive:521550 -> 0x1.1p+6 0x0p+0
```

### `sub_1_2_full`

Claims: `extends(w) F1-F5, core sub_1_2, lead sub, finite when |a| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core sub_1_2: normalized(z)`; `F2, core sub_1_2: error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.812210 | 1.62442 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.916723 | 1.74253 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.939450 | - |
| `fp:4:-9:4`, every operand (p = min_precision + 1, another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.882759 | 1.76552 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0 | - |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0 | - |
| `fp:4:-5:0`, every operand (p = min_precision + 1, the quick tier's format) | 113 316 | 113 316 | 0 | 0.882759 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.780488 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 555 558, close 833 335, edge 555 554, extreme 277 779, nonfinite 555 554, overflow 277 777, pow2 277 779, threshold 555 552, underflow 555 556, uniform 277 779, zero 277 777; `binary32`: cancel 555 558, close 833 335, edge 555 554, extreme 277 779, nonfinite 555 554, overflow 277 777, pow2 277 779, threshold 555 552, underflow 555 556, uniform 277 779, zero 277 777.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.916723 (clang18-fixup-call/cxx, linux-x86-64):
  sub_1_2_full binary32 0x1.fdbd56p-103 0x1.0b101p-101 0x1.83323ap-126 #underflow:1989363 -> -0x1.174176p-102 -0x1.06647p-127
largest error / bound, interpreter 0.939450 (fp:5:-8:1, every operand):
  sub_1_2_full fp:5:-8:1 -0x1.fp+3 -0x1p+5 -0x1.1p-1 #exhaustive:521646 -> 0x1.1p+4 0x0p+0
```

### `sub_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 108 215 688 | 0 | 0.997363 | 1.99473 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 108 177 144 | 0 | 0.986186 | 1.97237 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665; `binary32`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.997363 (clang-fixup-inline/cxx, macos-arm64):
  sub_2_1 binary64 -0x1.0056a6716d89dp+1022 0x1.9a9fc623a01e7p+968 -0x1.ffffffffffffdp+1020 #overflow:1088806 -> -0x1.00ad4ce2db13bp+1021 0x1.353f8c47403dp+967
largest error / bound, interpreter 0.939450 (fp:5:-6:3, every operand):
  sub_2_1 fp:5:-6:3 -0x1p+7 -0x1.1p+1 -0x1.fp+5 #exhaustive:847346 -> -0x1.1p+6 0x0p+0
```

### `sub_2_1_full`

Claims: `extends(w) F1-F5, core sub_2_1, lead sub, finite when |x| <= 2^(qmax+p-2) and |a| <= 2^(qmax+p-2)`; `F2, core sub_2_1: normalized(z)`; `F2, core sub_2_1: error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.913198 | 1.82640 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.943193 | 1.88639 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.939450 | - |
| `fp:4:-9:4`, every operand (p = min_precision + 1, another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.882759 | 1.76552 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0 | - |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0 | - |
| `fp:4:-5:0`, every operand (p = min_precision + 1, the quick tier's format) | 113 316 | 113 316 | 0 | 0.882759 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.780488 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 555 558, close 833 335, edge 555 554, extreme 277 779, nonfinite 555 554, overflow 277 777, pow2 277 779, threshold 555 552, underflow 555 556, uniform 277 779, zero 277 777; `binary32`: cancel 555 558, close 833 335, edge 555 554, extreme 277 779, nonfinite 555 554, overflow 277 777, pow2 277 779, threshold 555 552, underflow 555 556, uniform 277 779, zero 277 777.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.943193 (clang18-fixup-call/cxx, linux-x86-64):
  sub_2_1_full binary32 0x1.05p+114 -0x1.fffffep+89 0x1.f529bap+112 #extreme:2208552 -> 0x1.0f6b2p+113 0x1p+89
largest error / bound, interpreter 0.939450 (fp:5:-8:1, every operand):
  sub_2_1_full fp:5:-8:1 -0x1p+5 -0x1.1p-1 -0x1.fp+3 #exhaustive:854588 -> -0x1.1p+4 0x0p+0
```

### `sub_2_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 108 220 236 | 0 | 0.703127 | 2.10938 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 108 195 792 | 0 | 0.746694 | 2.24008 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665; `binary32`: cancel 833 335, close 1 250 000, extreme 416 667, overflow 416 665, pow2 416 667, underflow 833 333, uniform 416 668, zero 416 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.746694 (clang18-fixup-call/cxx, linux-x86-64):
  sub_2_2 binary32 -0x1.0e627p+126 -0x1.cca4ap+101 -0x1.fffffep+124 0x1.3ef406p+78 #overflow:1949278 -> -0x1.1cc4e2p+125 -0x1.99494p+100
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  sub_2_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 -0x1.9p+5 -0x1.cp-1 #exhaustive:127545 -> -0x1.1p+6 0x1p+0
```

### `sub_2_2_full`

Claims: `extends(w) F1-F5, core sub_2_2, lead sub, finite when |x| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core sub_2_2: normalized(z)`; `F2, core sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.666667 | 2.00000 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | 0.666666 | 2.00000 |
| `fp:4:-6:1`, every operand (p = min_precision + 1, another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.536013 | - |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | 0.556176 | - |
| `fp:3:-6:3`, every operand (p = min_precision, another number of exponents) | 3 247 204 | 3 247 204 | 0 | 0.360255 | 2.16153 |
| `fp:4:-5:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 988 036 | 988 036 | 0 | 0.453901 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's format) | 181 476 | 181 476 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 555 558, close 833 335, edge 555 554, extreme 277 779, nonfinite 555 554, overflow 277 777, pow2 277 779, threshold 555 552, underflow 555 556, uniform 277 779, zero 277 777; `binary32`: cancel 555 558, close 833 335, edge 555 554, extreme 277 779, nonfinite 555 554, overflow 277 777, pow2 277 779, threshold 555 552, underflow 555 556, uniform 277 779, zero 277 777.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666667 (clang18-fixup-call/cxx, linux-x86-64):
  sub_2_2_full binary64 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+969 0x1.ffffffffffffdp+1022 -0x1.4af87dc1f84ffp+927 #edge:915999 -> 0x1.0000000000001p+1023 0x1.4a387dc1f84ffp+927
largest error / bound, interpreter 0.556176 (fp:5:-6:-1, every operand):
  sub_2_2_full fp:5:-6:-1 -0x1.ep+3 0x1p-2 -0x1.9p+2 -0x1.cp-4 #exhaustive:127734 -> -0x1.1p+3 0x1p-3
```

### `to_down_2`

Claims: `rounded(t) down`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | exact 25 189 860; inexact, as RN 31 577 472; differs from RN 31 110 972; a non-finite operand 22 080 000; rounds to -inf 441 696 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | exact 26 978 256; inexact, as RN 30 652 404; differs from RN 30 241 692; a non-finite operand 22 080 000; rounds to -inf 447 648 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact, as RN 2 584 448; differs from RN 2 582 913; a non-finite operand 3; rounds to -inf 1 535 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact, as RN 358 272; differs from RN 357 761; a non-finite operand 3; rounds to -inf 511 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact, as RN 129 920; differs from RN 129 601; a non-finite operand 3; rounds to -inf 319 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact, as RN 1 384; differs from RN 1 349; a non-finite operand 3; rounds to -inf 35 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact, as RN 402; differs from RN 383; a non-finite operand 3; rounds to -inf 19 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 500 000, halfgap 1 000 000, nonfinite 1 000 000, overflow 500 000, pow2 500 000, underflow 500 000, uniform 500 000, zero 500 000; `binary32`: extreme 500 000, halfgap 1 000 000, nonfinite 1 000 000, overflow 500 000, pow2 500 000, underflow 500 000, uniform 500 000, zero 500 000.

### `to_nearest_2`

Claims: `rounded(t) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | exact 25 186 272; inexact 35 328 576; tie 27 805 152; a non-finite operand 22 080 000 |
| `binary32`, 60 runners on 3 machines | 110 400 000 | 110 400 000 | 0 | exact 27 012 312; inexact 34 114 740; tie 27 192 948; a non-finite operand 22 080 000 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact 5 164 034; tie 4 862; a non-finite operand 3 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact 713 730; tie 2 814; a non-finite operand 3 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact 2 682; tie 86; a non-finite operand 3 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact 762; tie 42; a non-finite operand 3 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact 258 434; tie 1 406; a non-finite operand 3 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 500 000, halfgap 1 000 000, nonfinite 1 000 000, overflow 500 000, pow2 500 000, underflow 500 000, uniform 500 000, zero 500 000; `binary32`: extreme 500 000, halfgap 1 000 000, nonfinite 1 000 000, overflow 500 000, pow2 500 000, underflow 500 000, uniform 500 000, zero 500 000.

### `to_up_2`

Claims: `rounded(t) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | exact 25 746 432; inexact, as RN 32 246 952; differs from RN 31 793 388; a non-finite operand 22 560 000; rounds to inf 453 228 |
| `binary32`, 60 runners on 3 machines | 112 800 000 | 112 800 000 | 0 | exact 27 554 016; inexact, as RN 31 331 112; differs from RN 30 903 540; a non-finite operand 22 560 000; rounds to inf 451 332 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact, as RN 2 584 448; differs from RN 2 582 913; a non-finite operand 3; rounds to inf 1 535 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact, as RN 358 272; differs from RN 357 761; a non-finite operand 3; rounds to inf 511 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact, as RN 129 920; differs from RN 129 601; a non-finite operand 3; rounds to inf 319 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact, as RN 1 384; differs from RN 1 349; a non-finite operand 3; rounds to inf 35 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact, as RN 402; differs from RN 383; a non-finite operand 3; rounds to inf 19 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 520 000, halfgap 1 040 000, nonfinite 1 040 000, overflow 520 000, pow2 520 000, underflow 520 000, uniform 520 000, zero 520 000; `binary32`: extreme 520 000, halfgap 1 040 000, nonfinite 1 040 000, overflow 520 000, pow2 520 000, underflow 520 000, uniform 520 000, zero 520 000.

### `two_prod`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=1/2`; `error(r) form R, c=0, k=2, t=0, when product_large`.

| Run | Cases | Judged | Failed | largest error / bound (c=0, k=2, t=1/2) | observed c | largest error / bound (c=0, k=2, t=0, when product_large) | observed c |
|---|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 112 684 440 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 112 697 664 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:3:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 481 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:2:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 597 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999; `binary32`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound (c=0, k=2, t=1/2), compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  two_prod binary64 0x1p-1074 -0x1.8p+0 #extreme:41322 -> -0x0.0000000000002p-1022 0x0p+0
largest error / bound (c=0, k=2, t=1/2), interpreter 1 (fp:7:-20:-6, every operand):
  two_prod fp:7:-20:-6 -0x1.fcp+0 -0x1.fcp-9 #exhaustive:576 -> 0x1.f8p-8 0x0p+0
```

### `two_prod_dekker`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=13/8`; `error(r) form R, c=0, k=2, t=0, when product_large`.

| Run | Cases | Judged | Failed | largest error / bound (c=0, k=2, t=13/8) | observed c | largest error / bound (c=0, k=2, t=0, when product_large) | observed c |
|---|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 105 132 540 | 0 | 0.923852 | 0 | 0 (exact) | 0 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 98 852 220 | 0 | 0.925880 | 0 | 0 (exact) | 0 |
| `fp:7:-16:-2`, every operand (another exponent range, replaces fp:7:-20:-6, where constant splitter is not a number) | 4 190 209 | 2 307 361 | 0 | 0.943510 | - | 0 (exact) | - |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 1 526 625 | 0 | 0.903846 | - | 0 (exact) | - |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 1 288 225 | 0 | 0.943510 | - | 0 (exact) | - |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 390 625 | 0 | 0.887019 | - | 0 (exact) | - |
| `fp:5:-12:-1`, every operand (p = min_precision + 1, the quick tier's format) | 172 225 | 96 721 | 0 | 0.889423 | - | 0 (exact) | - |
| `fp:4:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 42 849 | 28 561 | 0 | 0.788462 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999; `binary32`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound (c=0, k=2, t=13/8), compiled 0.925880 (clang18-fixup-call/cxx, linux-x86-64):
  two_prod_dekker binary32 0x1.14af1ap-116 -0x1.e2d274p-12 #underflow:1627899 -> -0x1.04ea9p-127 -0x1p-148
largest error / bound (c=0, k=2, t=13/8), interpreter 0.943510 (fp:7:-16:-2, every operand):
  two_prod_dekker fp:7:-16:-2 -0x1.a4p-3 -0x1.a4p-10 #exhaustive:963008 -> 0x1.6p-12 -0x1p-15
```

### `two_sum`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 117 600 000 | 114 594 828 | 0 | 0 (exact) | 0 |
| `binary32`, 60 runners on 3 machines | 117 600 000 | 114 594 804 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 107 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 867 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 487 | 0 | 0 (exact) | 0 |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 573 | 0 | 0 (exact) | 0 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 403 | 0 | 0 (exact) | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999; `binary32`: cancel 900 001, close 1 350 000, extreme 449 999, overflow 449 999, pow2 449 999, underflow 900 001, uniform 450 002, zero 449 999.

## Supplementary run: B4 on the full Ball kernels

After these runs, the claims of the eight full Ball kernels gained a condition: their `encloses`
claim now says when finite operands give a finite ball (`finite_when`, statement B4 of
[the Ball kernels](../design/milestone1.md#ball-kernels)), and the runs above judged them without
it, with no condition claimed. The kernels' code did not change. A supplementary run judged
those eight kernels against the new claims, at commit `f7e0b6d` with the driver of commit
`72f700f`: in `binary64` and `binary32` through every runner of the machines below, and every
enumeration of the plan for them on the Linux machine. **B4 was judged on these cases only**;
every other number on this page is of the runs above. At this commit the runners of a contraction
setting are built at `-O2` with GCC and Clang (the setting's flags end in `-O2`), `/O2` with MSVC.
Its summaries are in
[`results/milestone1/brute/supplementary/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone1/brute/supplementary).

**No failure.** The supplementary run judged 2 260 800 000 results of the compiled kernels
(1 747 200 000 on the Linux machine with 24 runners and all of its 128 hardware threads in 31
minutes, 403 200 000 on the Mac with 24 runners in 21 minutes, 110 400 000 on Windows with 12
runners in 21 minutes; 134 to 146 million per kernel and format) and 151 290 688 of the
interpreter (the 31 enumerations of the plan for these kernels, every one complete, on the Linux
machine), with no failure, no invalid case and no suspicious result; every series and every
enumeration passed the guards. B4 applied, that is the operands were finite and every
`finite_when` condition held, to 1 172 390 844 of the compiled cases (67 to 79 million per kernel
and format, summed over the runners) and to 8 926 458 of the enumerated ones (442 058 for
`ball_scale_2_full` to 3 594 222 for `ball_mul_2_full`), and every one of them gave a finite
ball. The column "B4 applied to" of each table below gives the count per run.

| Machine | Compilers | Runners | Seed | Cases per kernel and format | Judged (compiled) | Enumerated (interpreter) |
|---|---|---|---|---|---|---|
| linux-x86-64-b4: Linux x86_64, AMD EPYC 7452 32-Core Processor | Clang 18.1.3, GNU 13.3.0 | 24 | `m1r2b4-linux` | 4 400 000 to 4 600 000 | 1 747 200 000 | 151 290 688 |
| macos-arm64-b4: Darwin arm64, Apple M3 Max | AppleClang 21.0.0.21000401, GNU 16.2.0 | 24 | `m1r2b4-mac` | 1 000 000 to 1 200 000 | 403 200 000 | 0 |
| windows-x64-b4: Windows AMD64, 13th Gen Intel(R) Core(TM) i5-13500T | MSVC 19.52.37029.0 | 12 | `m1r2b4-windows` | 400 000 to 600 000 | 110 400 000 | 0 |

| Machine | Wall time | Judged per second | Enumerated per second | One check pipeline, cases/s | One generator, cases/s | One interpreter pipeline, cases/s |
|---|---|---|---|---|---|---|
| linux-x86-64-b4 | 1870 s (0.52 h) | 934 382 | 80 908 | 8 616 | 10 356 | 6 002 |
| macos-arm64-b4 | 1234 s (0.34 h) | 326 822 | 0 | 43 133 | 52 731 | - |
| windows-x64-b4 | 1254 s (0.35 h) | 88 059 | 0 | 12 033 | 14 619 | - |

Per kernel and format, summed over the machines and their runners: 134 400 000 to 146 400 000 cases (median 141 600 000), of which 134 400 000 to 146 400 000 judged (a finite result, or any result in the extended domain), from 5 800 000 to 6 400 000 distinct cases. 16 of 16 kernel and format pairs reach $10^8$ cases.

16 of 16 reach $10^8$ judged results.

On each machine, every runner gave the same counts and the same extremes, for every kernel and format (48 series of runners compared).

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `ball_mul_2_full` | `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|(abs(cx)+rx)*(abs(cy)+ry)\| <= 2^(qmax+p-2)` | 2.50000 | 2.16797 (`fp:4:-5:0`) |
| `ball_mul_1_full` | `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|(abs(cx)+rx)*(abs(cy)+ry)\| <= 2^(qmax+p-4)` | 1.59070 | 1.85352 (`fp:3:-4:1`) |
| `ball_scale_2_full` | `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)` | 1.32897 | 1.40625 (`fp:3:-4:1`) |
| `ball_sub_2_full` | `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx-cy)+rx+ry\| <= 2^(qmax+p-2)` | 1.25085 | 1.75 (`fp:3:-3:0`) |
| `ball_add_2_full` | `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx+cy)+rx+ry\| <= 2^(qmax+p-2)` | 1.25005 | 1.75 (`fp:3:-3:0`) |
| `ball_add_1_full` | `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx+cy)+rx+ry\| <= 2^(qmax+p-2)` | 1 | 1 (`fp:3:-4:1`) |
| `ball_scale_1_full` | `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)` | 1.00000 | 1 (`fp:3:-6:3`) |
| `ball_sub_1_full` | `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx-cy)+rx+ry\| <= 2^(qmax+p-2)` | 1 | 1 (`fp:3:-4:1`) |

### `ball_add_1_full`, with B4

Claims: `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx+cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 146 400 000 | 146 400 000 | 0 | 1 | 1.00000 | 76 781 844 |
| `binary32`, 60 runners on 3 machines | 146 400 000 | 146 400 000 | 0 | 1 | 1.000000095 | 75 736 740 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1 | 1.2 | 397 403 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 1 | 1.33333 | 363 535 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 1 | 1.33333 | 27 055 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 556 522, cancel 278 261, centerpow2 556 522, exact 278 261, extreme 278 261, hugeradius 556 519, nonfinite 556 522, overflow 278 261, pow2 278 261, radii 556 522, threshold 556 522, underflow 278 261, uniform 278 261, wide 278 261, zero 278 261, zerowhole 556 522; `binary32`: ballstates 556 522, cancel 278 261, centerpow2 556 522, exact 278 261, extreme 278 261, hugeradius 556 519, nonfinite 556 522, overflow 278 261, pow2 278 261, radii 556 522, threshold 556 522, underflow 278 261, uniform 278 261, wide 278 261, zero 278 261, zerowhole 556 522.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64-b4):
  ball_add_1_full binary64 -0x1p+1023 0x1p+1022 0x1.fffffffffffffp+1021 0x1.ca46ae8131cd4p+1019 #hugeradius:3110496 -> -0x1p+1022 0x1.3948d5d02639cp+1022
smallest radius slack, gaps, interpreter 1 (fp:3:-4:1, every operand):
  ball_add_1_full fp:3:-4:1 -0x1.cp+3 0x1p+0 0x1.4p+2 0x1p+3 #exhaustive:19872 -> -0x1p+3 0x1.8p+3
```

### `ball_add_2_full`, with B4

Claims: `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx+cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 1.25892 | 1.00000 | 79 334 628 |
| `binary32`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 1.25005 | 1.000000142 | 78 091 980 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 | 1.75 | 1.52381 | 176 623 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 | 2 | 1.52381 | 472 949 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 | 5.5 | 1.76471 | 16 725 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 539 130, cancel 269 565, centerpow2 539 131, exact 269 566, extreme 269 565, hugeradius 539 129, nonfinite 539 130, overflow 269 565, pow2 269 565, radii 539 132, threshold 539 130, underflow 269 565, uniform 269 566, wide 269 566, zero 269 565, zerowhole 539 130; `binary32`: ballstates 539 130, cancel 269 565, centerpow2 539 131, exact 269 566, extreme 269 565, hugeradius 539 129, nonfinite 539 130, overflow 269 565, pow2 269 565, radii 539 132, threshold 539 130, underflow 269 565, uniform 269 566, wide 269 566, zero 269 565, zerowhole 539 130.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25005 (clang18-fixup-call/cxx, linux-x86-64-b4):
  ball_add_2_full binary32 0x1.fffffep+127 0x0p+0 0x1.7ff916p+102 0x1p-148 0x0p+0 0x1.fffffcp+125 #extreme:2852241 -> 0x1.fffffep+127 0x1p-148 0x1.000002p+126
smallest radius slack, gaps, interpreter 1.75 (fp:3:-3:0, every operand):
  ball_add_2_full fp:3:-3:0 -0x1.cp+2 -0x1.8p-2 0x1p-2 0x1.4p+2 0x1p-3 0x1.8p+1 #exhaustive:6778 -> -0x1p+1 -0x1p-2 0x1.4p+2
```

### `ball_mul_1_full`, with B4

Claims: `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |(abs(cx)+rx)*(abs(cy)+ry)| <= 2^(qmax+p-4)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 146 400 000 | 146 400 000 | 0 | 1.59872 | 1.00000 | 71 096 832 |
| `binary32`, 60 runners on 3 machines | 146 400 000 | 146 400 000 | 0 | 1.59070 | 1.000000174 | 70 618 524 |
| `fp:2:-7:6`, every operand (p = min_precision, another number of exponents) | 3 139 984 | 3 139 984 | 0 | 2.05078 | 2.61224 | 1 019 219 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1.85352 | 1.50367 | 131 167 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 2.05078 | 2.61224 | 190 319 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 2.05078 | 2.61224 | 9 563 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 512 000, cancel 256 000, centerpow2 512 000, exact 256 000, extreme 256 000, hugeradius 512 000, nonfinite 512 000, overflow 256 000, pow2 256 000, radii 512 000, threshold 512 000, underflow 256 000, uniform 256 000, wide 256 000, zero 256 000, zeroinf 512 000, zerowhole 512 000; `binary32`: ballstates 512 000, cancel 256 000, centerpow2 512 000, exact 256 000, extreme 256 000, hugeradius 512 000, nonfinite 512 000, overflow 256 000, pow2 256 000, radii 512 000, threshold 512 000, underflow 256 000, uniform 256 000, wide 256 000, zero 256 000, zeroinf 512 000, zerowhole 512 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.59070 (clang-fixup-inline/cxx, macos-arm64-b4):
  ball_mul_1_full binary32 -0x1p-36 0x1.0ab96p-12 0x1.02ebe6p+107 0x1.fffffep+126 #hugeradius:953373 -> -0x1.02ebe6p+71 0x1.0ab974p+115
smallest radius slack, gaps, interpreter 1.85352 (fp:3:-4:1, every operand):
  ball_mul_1_full fp:3:-4:1 -0x1.cp-2 0x1.8p+0 -0x1.4p-2 0x1.8p+1 #exhaustive:885742 -> 0x1p-3 0x1.4p+3
```

### `ball_mul_2_full`, with B4

Claims: `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |(abs(cx)+rx)*(abs(cy)+ry)| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 2.50000 | 1.00000 | 68 619 792 |
| `binary32`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 2.56077 | 1.000000279 | 66 945 420 |
| `fp:4:-4:-1`, every operand (p = min_precision, the quick tier's format) | 97 653 924 | 97 653 924 | 0 | 3.125 | 1.43177 | 1 487 636 |
| `fp:4:-5:0`, restricted: `cx.lead=0:0`, `cy.lead=0:0` (p = min_precision, another number of exponents) | 12 068 676 | 12 068 676 | 0 | 2.16797 | 1.26108 | 1 947 624 |
| `fp:4:-3:-2`, every operand (p = min_precision, another number of exponents) | 2 149 156 | 2 149 156 | 0 | 6.75 | 2.30769 | 38 997 |
| `fp:4:-4:-1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0` (p = min_precision, the quick tier's format) | 980 100 | 980 100 | 0 | 3.28125 | 1.49416 | 74 055 |
| `fp:5:-5:-2`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `cx.lead=0:0` (p = min_precision + 1, quick tier + 1 bit) | 503 500 | 503 500 | 0 | 5.11719 | 1.27949 | 45 910 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 496 000, cancel 248 000, centerpow2 496 000, exact 248 000, extreme 248 000, hugeradius 496 000, nonfinite 496 000, overflow 248 000, pow2 248 000, radii 496 000, threshold 496 000, underflow 248 000, uniform 248 000, wide 248 000, zero 248 000, zeroinf 496 000, zerowhole 496 000; `binary32`: ballstates 496 000, cancel 248 000, centerpow2 496 000, exact 248 000, extreme 248 000, hugeradius 496 000, nonfinite 496 000, overflow 248 000, pow2 248 000, radii 496 000, threshold 496 000, underflow 248 000, uniform 248 000, wide 248 000, zero 248 000, zeroinf 496 000, zerowhole 496 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 2.50000 (clang-fixup-inline/cxx, macos-arm64-b4):
  ball_mul_2_full binary64 0x1p+0 -0x1p-54 0x1p+0 -0x1.000000002p-772 -0x1p-825 0x1p-825 #extreme:119561 -> -0x1.000000002p-772 -0x1.ffffffffcp-827 0x1.0000000020004p-772
smallest radius slack, gaps, interpreter 2.16797 (fp:4:-5:0, restricted: cx.lead=0:0, cy.lead=0:0):
  ball_mul_2_full fp:4:-5:0 -0x1.8p+0 -0x1p-4 0x1.cp+0 -0x1p+0 -0x1p-4 0x1.8p+0 #exhaustive:2245744 -> 0x1.ap+0 0x1p-5 0x1.2p+3
```

### `ball_scale_1_full`, with B4

Claims: `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when |(abs(cx)+rx)*a| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 1.00000 | 1.00000 | 74 019 708 |
| `binary32`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 1.000000119 | 1.000000108 | 72 796 860 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 708 852 | 708 852 | 0 | 1.125 | 1.12676 | 291 726 |
| `fp:3:-6:3`, every operand (p = min_precision + 1, another number of exponents) | 344 700 | 344 700 | 0 | 1 | 1.2 | 194 982 |
| `fp:2:-8:7`, every operand (p = min_precision, another number of exponents) | 159 600 | 159 600 | 0 | 1.4375 | 1.6 | 102 984 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 89 436 | 89 436 | 0 | 1 | 1.2 | 36 914 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 11 400 | 11 400 | 0 | 1.4375 | 1.6 | 4 724 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 496 000, cancel 248 000, centerpow2 496 000, exact 248 000, extreme 248 000, hugeradius 496 000, nonfinite 496 000, overflow 248 000, pow2 248 000, radii 496 000, threshold 496 000, underflow 248 000, uniform 248 000, wide 248 000, zero 248 000, zeroinf 496 000, zerowhole 496 000; `binary32`: ballstates 496 000, cancel 248 000, centerpow2 496 000, exact 248 000, extreme 248 000, hugeradius 496 000, nonfinite 496 000, overflow 248 000, pow2 248 000, radii 496 000, threshold 496 000, underflow 248 000, uniform 248 000, wide 248 000, zero 248 000, zeroinf 496 000, zerowhole 496 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64-b4):
  ball_scale_1_full binary64 -0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 -0x1.0000000000001p-1022 #ballstates:3813270 -> 0x1p+2 0x1.0000000000002p+2
smallest radius slack, gaps, interpreter 1 (fp:3:-6:3, every operand):
  ball_scale_1_full fp:3:-6:3 -0x1.8p+5 0x1.8p+5 -0x1.8p-1 #exhaustive:7765 -> 0x1p+5 0x1.8p+5
```

### `ball_scale_2_full`, with B4

Claims: `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when |(abs(cx)+rx)*a| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 136 800 000 | 136 800 000 | 0 | 1.32897 | 1.00000 | 71 616 984 |
| `binary32`, 60 runners on 3 machines | 136 800 000 | 136 800 000 | 0 | 1.37500 | 1.000000140 | 69 814 788 |
| `fp:4:-4:-1`, every operand (quick tier + 1 bit) | 810 324 | 810 324 | 0 | 2.44531 | 1.28584 | 148 004 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, another number of exponents) | 687 068 | 687 068 | 0 | 1.40625 | 1.30612 | 186 026 |
| `fp:2:-4:3`, every operand (p = min_precision, another number of exponents) | 223 744 | 223 744 | 0 | 1.46875 | 1.68977 | 87 040 |
| `fp:3:-3:0`, every operand (p = min_precision + 1, the quick tier's format) | 100 044 | 100 044 | 0 | 2.26562 | 1.53425 | 18 612 |
| `fp:2:-2:1`, every operand (p = min_precision, the quick tier's number of exponents) | 12 144 | 12 144 | 0 | 1.8125 | 2.46154 | 2 376 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 480 000, cancel 240 000, centerpow2 480 000, exact 240 000, extreme 240 000, hugeradius 480 000, nonfinite 480 000, overflow 240 000, pow2 240 000, radii 480 000, threshold 480 000, underflow 240 000, uniform 240 000, wide 240 000, zero 240 000, zeroinf 480 000, zerowhole 480 000; `binary32`: ballstates 480 000, cancel 240 000, centerpow2 480 000, exact 240 000, extreme 240 000, hugeradius 480 000, nonfinite 480 000, overflow 240 000, pow2 240 000, radii 480 000, threshold 480 000, underflow 240 000, uniform 240 000, wide 240 000, zero 240 000, zeroinf 480 000, zerowhole 480 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.32897 (clang18-fixup-call/cxx, linux-x86-64-b4):
  ball_scale_2_full binary64 -0x1.47dac86a8f004p-838 0x1p-891 0x1.96f10e44f0c6fp-890 0x1.5fe00b2fdf899p+1023 #extreme:4274086 -> -0x1.c2a3e68d2d5d9p+185 0x1.1e4c1d07d4f4p+130 0x1.17ac53a2bbd47p+134
smallest radius slack, gaps, interpreter 1.40625 (fp:3:-4:1, every operand):
  ball_scale_2_full fp:3:-4:1 -0x1.8p+3 -0x1p-3 0x1.8p+2 -0x1.8p-1 #exhaustive:54885 -> 0x1p+3 0x1p+0 0x1.8p+2
```

### `ball_sub_1_full`, with B4

Claims: `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx-cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 1 | 1.00000 | 74 273 628 |
| `binary32`, 60 runners on 3 machines | 141 600 000 | 141 600 000 | 0 | 1 | 1.000000096 | 73 266 420 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1 | 1.2 | 397 403 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 1 | 1.33333 | 363 535 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 1 | 1.33333 | 27 055 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 539 130, cancel 269 565, centerpow2 539 131, exact 269 566, extreme 269 565, hugeradius 539 129, nonfinite 539 130, overflow 269 565, pow2 269 565, radii 539 132, threshold 539 130, underflow 269 565, uniform 269 566, wide 269 566, zero 269 565, zerowhole 539 130; `binary32`: ballstates 539 130, cancel 269 565, centerpow2 539 131, exact 269 566, extreme 269 565, hugeradius 539 129, nonfinite 539 130, overflow 269 565, pow2 269 565, radii 539 132, threshold 539 130, underflow 269 565, uniform 269 566, wide 269 566, zero 269 565, zerowhole 539 130.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64-b4):
  ball_sub_1_full binary64 -0x1.ffffffffffffdp+1022 0x1.46cfee5cbfc79p+1022 -0x1.fffffffffffffp+1023 0x1p+1022 #hugeradius:514485 -> 0x1p+1023 0x1.2367f72e5fe3ep+1023
smallest radius slack, gaps, interpreter 1 (fp:3:-4:1, every operand):
  ball_sub_1_full fp:3:-4:1 -0x1.cp+3 0x1p+0 -0x1.4p+2 0x1p+3 #exhaustive:18696 -> -0x1p+3 0x1.8p+3
```

### `ball_sub_2_full`, with B4

Claims: `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx-cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 134 400 000 | 134 400 000 | 0 | 1.25085 | 1.00000 | 75 261 480 |
| `binary32`, 60 runners on 3 machines | 134 400 000 | 134 400 000 | 0 | 1.25134 | 1.000000143 | 74 115 216 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 | 1.75 | 1.52381 | 176 623 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 | 2 | 1.52381 | 472 949 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 | 5.5 | 1.76471 | 16 725 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 504 346, cancel 252 175, centerpow2 504 349, exact 252 176, extreme 252 173, hugeradius 504 346, nonfinite 504 346, overflow 252 173, pow2 252 173, radii 504 352, threshold 504 346, underflow 252 174, uniform 252 176, wide 252 176, zero 252 173, zerowhole 504 346; `binary32`: ballstates 504 346, cancel 252 175, centerpow2 504 349, exact 252 176, extreme 252 173, hugeradius 504 346, nonfinite 504 346, overflow 252 173, pow2 252 173, radii 504 352, threshold 504 346, underflow 252 174, uniform 252 176, wide 252 176, zero 252 173, zerowhole 504 346.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25085 (clang18-fixup-call/cxx, linux-x86-64-b4):
  ball_sub_2_full binary64 0x1.a268601d5beecp-908 0x1p-961 0x1.ffffffffffffep+1022 -0x1.fffffffffffffp+1023 -0x1.fffffffffffffp+969 0x1.7f902601d04ebp+970 #extreme:204642 -> 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+969 0x1.0000000000001p+1023
smallest radius slack, gaps, interpreter 1.75 (fp:3:-3:0, every operand):
  ball_sub_2_full fp:3:-3:0 -0x1.cp+2 -0x1.8p-2 0x1p-2 -0x1.cp+2 -0x1.8p-2 0x1.8p+1 #exhaustive:4778 -> 0x0p+0 0x0p+0 0x1.4p+2
```

## What was not run, and why

- **$10^8$ judged results for eleven kernels and formats**: the aim of $10^8$ cases was reached
  for every kernel and format, but the judged results of `ball_mul_2`, `ball_scale_2`,
  `ball_mul_1`, `ball_scale_1`, `mul_1_1` (both formats) and `two_prod_dekker` (`binary32`) are
  85 to 99 million: their non-finite results are not judged ([above](#the-aim-a-hundred-million-cases-per-kernel-and-format)).
  The driver extends a run where it stopped (`run` again on the same work directory with a larger
  budget).
- **Precision 1.** Twenty-six kernels claim `min_precision` 1. The oracle reads formats of
  precision 1 since commit `2bfe39d`, but the plan of these runs was written before it and
  started their enumerations at precision 2, so their claims at precision 1 were tested in no
  format here. By hand, every operand of `add_1_1` at `fp:1:-4:3` (289 cases) through the
  interpreter and the oracle gave no failure. The driver now plans precision 1 as well (commit
  `9f0577a`); a run of those enumerations was not made for this page.
- **Every operand of the quick tier's formats of the two-limb balls with two operands**: 140
  million combinations each for `ball_add_2` and `ball_sub_2` at `fp:3:-3:2`, 12.4 billion for
  `ball_mul_2` at `fp:4:-5:1`. In their place, every operand of formats of the same precision
  with fewer exponents, and restricted domains of those formats larger than the quick tier's.
  For `ball_mul_2_full` every operand of the quick tier's `fp:4:-4:-1` did run (98 million).
- **Formats three bits above the quick tier's** were sized and left out, to leave the time to
  the compiled runners.
- **Enumerations on Windows**: the interpreter is the same Python on every machine, and the
  Linux machine and the Mac shared the plan; Windows gave its budget to its MSVC runners.
- **Other compilers and targets**: clang-cl is not installed on the Windows machine, no machine
  has AVX-512, and no other backend is part of Milestone 1.
- **The interpreter's variants**: `--muladd unfused` would change nothing (no kernel of
  Milestone 1 has a `muladd`), and `--ce` runs `two_prod_dekker` in place of `two_prod`, whose
  own enumerations are above.
- **Suspicious results of `split` and `two_prod_dekker`** do not fail their runs, as in the quick
  tier: their product by the splitter overflows for operands far below the largest number, which
  their requirement of no intermediate overflow allows. Their runs are still held to the guards.
- **Narrow exponent ranges judge few of their cases.** At `fp:4:-3:-2`, for instance, 5.7 % of
  the cases of `ball_mul_2_full` end as a finite ball, and in the finite domain the share of
  judged cases is as low as 15.0 % (`ball_mul_2` with the quick tier's radii); the tables above
  give it for every enumeration of a Ball kernel, and the column "Judged" of each kernel's table
  for every kernel.
