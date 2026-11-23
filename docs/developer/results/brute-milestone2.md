# Brute-force results, Milestone 2

**No claim was violated.** On three machines, the oracle judged 25 107 129 600 results of the
compiled kernels and loops over arrays of commit `5f597fb` (25 608 966 000 cases through 90
runners: scalar and packed, every contraction setting, at `-O1` and in the debug build, both
forms of the scalar fix-ups; five compilers) and 2 340 035 716 results of the generator's
interpreter, which enumerated every operand of the 1 296 toy-format domains of the plan
(2 629 207 744 cases). No case failed a claim and none was invalid. The suspicious non-finite
results are those of `split` and `two_prod_dekker` (exempt, as in every tier) and 376 of
`ball_mul_1` at precision 1 (exempt since Milestone 1); every one of the 50 100 series of one
kernel or loop, format and runner passed the quick tier's guards.

**One finding of the runs and four of their collection, none in the code.** The runs stopped
two enumerations, of `acc_radius_1` and `acc_radius_2` at precision 2, on infinite radii that
the oracle calls suspicious: the radius's constant factor is the format's largest number there,
and the claim, an upper bound, says nothing of finiteness; an exact test shows every one an
overflow ([Findings](#findings)). `collect` failed the guards of four other enumerations, which
did not exercise what the guards ask: the driver's plan had given `bound_sum_2`, `bound_dot_2`
and `acc_merge_2` formats in which no correct kernel can. The six were run again (the plan
changed for the four) and pass; the driver's faults are fixed, each with its test. The other
1 290 enumerations are complete and passed the guards.

**The aim of $10^8$** results per kernel and format, for the kernels new or changed since
Milestone 1, where the budget allowed it: the 116 kernels chosen as the cheapest to judge, 115
of them new or changed and one, `to_nearest_2`, unchanged, reached $10^8$ cases on each of their
232 kernel and format pairs (100.8 to 103.5 million, summed over the machines and their
runners), and 176 of the pairs $10^8$ judged results (the others, finite-domain kernels whose
non-finite results are not judged, 82.9 million or more). **The other 75 new or changed kernels
and the other 42 unchanged ones have their share of phase A only: 7.2 million cases per kernel
and format; the 47 loops 42 000 to 72 000 arrays judged per loop and format** (about 5 000
distinct arrays of up to 4 096 elements, beside their enumerations, 80 000 arrays each of the
emulated tier and 5 000 of `lengths.py`)
([below](#the-aim-a-hundred-million-results-per-kernel-and-format)). The Linux machine ran 9.4
hours (64 of its 128 hardware threads, 80 busy processes), the Mac and the Windows machine 5.9
each. (Corrected on 2026-11-23: this page said 191 kernels new or changed, 21 of them changed,
and 42 unchanged, because the comparison made for the campaign took the loops printed after
`to_nearest_2`, the last kernel of each generated header, as its code; `to_nearest_2` is
unchanged in code and claims, and was run to $10^8$ with the changed kernels. By that comparison,
done right, 190 kernels are new or changed, 170 new and 20 changed, and 43 unchanged; by the code
alone, the rule of the reference pages since that day, 182 and 51, the eight full Ball kernels
having changed their claims only, with the condition B4.)

**How close the bounds came**, for the kernels and loops of this milestone
([tables](#how-close-the-claims-came)). **Attained exactly** (a case on the bound itself): the
error bounds of `acc_add_1`, `acc_merge_1`, `add_1`, `add_1_entry`, `add_entry_step_1`,
`bv_mul_pow2_1`, `bv_mul_pow2_step_1`, `bv_sub_1`, `mul_pow2_map_1`, `mul_pow2_step_1`, `sub_1`,
`sub_1_1`, `sub_1_entry`, `sub_entry_step_1`, `sum_entry_step_1` and `two_prod_entry`, the $3/2$
gaps of `radd`, `radd_entry` and `rmul`, the steps above RU(V) of the folds of maxima
`norm_upper_1` (0) and `norm_upper_2` (1), and the stated value of the radius of `conv_radius`.
The sums of one limb over arrays (`sum_1`, `sum_1_entry`) came within $1.8 \cdot 10^{-4}$ of
their bounds at every length from 2 to 4 096 ([the table of lengths](#the-loops-over-arrays)).
The one-limb conversions of an interval to a ball came within $10^{-5}$ of their allowance; the
dot product of two limbs within $5.3 \cdot 10^{-4}$ of its bound in `binary64`, on arrays of one
element; the
interval kernels of two limbs and their bounds to 0.69 to 0.79 of their allowance. **Far from
attained** (a largest ratio of 0.5 or less): the bounds of the sums of two limbs over arrays
(`sum_2` and `sum_2_entry` 1/3, `sum_fast_2` and `sum_fast_2_entry` 0.49; on long arrays every
loop of two limbs stays near 1/6 of its bound: the [table of lengths](#the-loops-over-arrays))
and the step of the fused dot product of two limbs `acc_mul_entry_2` (0.50; 0.75 in the
search); and among the upper
bounds that state a value, the term of the underflow $t$ of the bounds of a dot product
`bound_dot_1` and `bound_dot_2`, $2^{p-1}$ gaps above the value it must exceed in every case
(8.4 million in `binary32`): its listing makes it about $1/u$ times that value, so that its
constant is a normal number ([below](#the-adversarial-search)). The radii of the ball vectors,
of the accumulator and the other bounds keep one to three gaps.

**The exhaustive tier on emulated formats**, the whole of it at the same commit on the Linux
machine: 1 247 784 868 lines of 1 120 entries, every operand at precision 8 of the 80 kernels of
one or two limbs and at 9 to 11 of the 15 of one limb, 1 216 815 154 judged, none failed, every
guard passed ([below](#the-exhaustive-tier-on-emulated-formats)).

**The adversarial search**, after the runs, on every kernel it takes (109, both formats, 20 000
cases per kernel and format, from the strata alone and with every seed: the attaining lines of
these runs among them), violated no claim. On the 234 quantities of the 71 kernels of this
milestone it takes whose claims are not all exact, with every seed it came closer to the claim than the brute-force runs on 135
and as close on the others: the accurate sums of two limbs in their entry forms to within
$8.1 \cdot 10^{-16}$ of their bounds in `binary64` (0.50 to 0.79 in the runs). It does not take
the loops, nor 118 kernels of this milestone whose kinds it does not climb
([below](#the-adversarial-search)). Its lines closest to a claim and those of the runs, 349,
joined the regression cases.

**A supplementary run** judged, at commit `8ee5ed9`, the twelve kernels and loops that the close
of rule R3 added or changed, on the three machines, with no failure; the other kernels and
loops are the same there ([below](#supplementary-run-the-close-of-rule-r3)).

## What was run

The code under test (kernels, loops over arrays, claims, generator, interpreter, oracle) is that
of commit `5f597fb`: 233 kernels and 47 loops over arrays (folds, maps, folds of maxima,
convolutions, ball vectors). The runs were made, as those of Milestone 1, from copies of the
tree made with `git archive`, of commit `1b37080`, whose code is that of `5f597fb` and whose
driver (`tests/brute/brute.py`) is the one of the runs; the Mac's first twenty minutes of
enumerations (28 chunks of one enumeration, `bound_sum_2` in `fp:20:-50:20`) ran with the driver
of commit `346d283`, whose enumerations are the same. Each stored summary names the commits of
the code and of the driver. The commands are in
[`tests/brute/README.md`](https://github.com/danielepanozzo/kairn/blob/main/tests/brute/README.md),
the stored summaries in
[`results/milestone2/brute/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/brute).
A [supplementary run](#supplementary-run-the-close-of-rule-r3) judged the twelve kernels and
loops that the close of rule R3 added or changed, at commit `8ee5ed9`; **every other number on
this page is of the runs at `5f597fb`**.

The machines are those of Milestone 1: the Linux machine (two AMD EPYC 7452, of whose 128
hardware threads the runs used 64, `--cpus 0-31,64-95`, with 80 busy processes; GCC 13.3 and
Clang 18.1), the Mac (Apple M3 Max, 8 busy processes; Apple clang 21 and GCC 16.2), the Windows
machine (Intel Core i5-13500T, 8 of its 20 logical processors; MSVC 19.52, which is installed
there alone: no clang-cl), all at a lower priority. Each compiler builds 18 runners: the scalar
and the packed kernels (AVX2 on the Linux and Windows machines, NEON on the Mac) with the build's
flags, under each contraction setting, and at `-O1` and in the debug build of the full tier
(`/O1` and `/Od`), and the scalar ones once more with the other form of the scalar fix-ups; 36
runners on the Linux machine and on the Mac, 18 on the Windows machine. One seed per machine:
`m2r1-linux`, `m2r1-mac`, `m2r1-windows`.

| Machine | Compilers | Runners | Seed | Cases per kernel and format | Judged (compiled) | Enumerated (interpreter) |
|---|---|---|---|---|---|---|
| linux-x86-64: Linux x86_64, AMD EPYC 7452 32-Core Processor | Clang 18.1.3, GNU 13.3.0 | 36 | `m2r1-linux` | 1 000 to 2 400 000 | 19 726 731 852 | 1 453 185 491 |
| macos-arm64: Darwin arm64, Apple M3 Max | AppleClang 21.0.0.21000401, GNU 16.2.0 | 36 | `m2r1-mac` | 500 to 350 000 | 3 279 552 456 | 1 176 022 253 |
| windows-x64: Windows AMD64, 13th Gen Intel(R) Core(TM) i5-13500T | MSVC 19.52.37029.0 | 18 | `m2r1-windows` | 500 to 450 000 | 2 100 845 292 | 0 |

| Machine | Wall time | Judged per second | Enumerated per second | One check pipeline, cases/s | One generator, cases/s | One interpreter pipeline, cases/s |
|---|---|---|---|---|---|---|
| linux-x86-64 | 33872 s (9.41 h) | 582 387 | 42 902 | 11 312 | 12 285 | 4 622 |
| macos-arm64 | 21208 s (5.89 h) | 154 639 | 55 452 | 45 513 | 43 189 | 28 478 |
| windows-x64 | 21381 s (5.94 h) | 98 259 | 0 | 13 280 | 13 461 | - |

**How the time was spent.** This milestone has 233 kernels and 47 loops, against 63 kernels in
Milestone 1, and twice the runners per compiler; the interpreter's enumerations are 2.7 times
as many indices, and slower to judge. A pilot of ten minutes on the Linux machine measured the
cost of a case of every kernel and format (units of 20 000 cases, to reach every pair in ten
minutes); a second one, of the loops, found a fault of the driver
([below](#faults-of-the-driver-found-by-the-runs)). From them the run had two phases:

- **Phase A, every kernel and loop, both formats, on every machine**: at least one unit of
  random cases per kernel and format on each machine (100 000 cases on the Linux machine, 50 000
  on the Mac and on the Windows machine), every case judged by every runner of the machine; and
  the enumerations of the interpreter, which come first in a run. Phase A ended when every pair
  had its unit on the machine: on the Linux machine after 3.9 hours and on the Mac after 4.4
  (both with their enumerations), on the Windows machine after 3.0 (the sums of the drivers'
  wall times over the restarts, in the stored summaries).
- **Phase B, the aim of $10^8$ results per kernel and format**, for the new and changed kernels
  only: of the kernels taken as new or changed since the code of Milestone 1's runs (commit
  `6f89054`), the 116 cheapest to judge, chosen from the costs phase A measured, so that each of
  their 232 kernel and format pairs reaches $10^8$ results judged, summed over the machines and
  their runners, within up to 10 hours on the Linux machine and 6 on each of the others; 115 of
  them are new or changed, and `to_nearest_2` is not (below). The other 75 new or changed
  kernels, the other 42 kernels unchanged since Milestone 1 and the 47 loops have their share of
  phase A only ([below](#the-aim-a-hundred-million-results-per-kernel-and-format)).

"New or changed" was decided from the generated code and the claims, not from names: a kernel
is new when `gen/claims.json` of `6f89054` has no entry of its name (170), changed when its claims
entry (without its description) or its definition in any of the generated headers of the scalar,
AVX2 and NEON kernels (comment lines left out) differs (20: the constant-evaluation branch of
`mul_1_1`, `split`, `two_prod_dekker`, `mul_pow2_2` and its full kernel; `next_up_bits` in
`radd`, `rmul`, `abs_upper_2` and the conversions `to_up_2` and `to_down_2`; the constructors
`ball_make_k`; the condition B4 in the claims of the eight full Ball kernels), and unchanged
otherwise (43). Every loop is new. The comparison made for the campaign counted 21 changed and 42
unchanged: it read a kernel's definition from its comment to the next kernel's, and so took the
loops, printed after `to_nearest_2`, the last kernel of each header, as that kernel's code; the
code and the claims of `to_nearest_2` are those of Milestone 1, and it was run to $10^8$ in
phase B (corrected on 2026-11-23, as the top of this page says).

**The interpreter's enumerations**: every operand of the 1 296 toy-format domains of the plan
(`brute.py plan --bins 20`: 2 637 978 164 indices), shared between the Linux machine (bins 0 to
10, 633 enumerations, 1 459 293 939 indices) and the Mac (bins 11 to 19, 663 enumerations,
1 178 684 225 indices). The split was changed twice in the first hour, when the rates were
measured (a Mac pipeline runs the interpreter about eight times as fast as one of the Linux
machine); a restart keeps every finished chunk, and the chunks a machine had finished of a bin
that went to the other were not counted. The plan replaces four formats in which a constant of
the kernel is not a number: `acc_radius_1` and `acc_radius_2` get `fp:2:-1:1` (for `fp:2:-2:0`,
where $\mathrm{up}((1+u)^8)$ is not a number), `ball_scale_1` `fp:1:-3:2` (for `fp:1:-5:0`) and
`two_prod_dekker` `fp:7:-16:-2` (for `fp:7:-20:-6`, as in Milestone 1). Every kernel and loop of
`gen/claims.json` has enumerations; none is on the lists of those the oracle does not judge yet.

**What a pass required**: the quick tier's guards (`tests/crosscheck_guards.py`), applied by
`brute.py collect` to every merged series of one kernel, format and runner and to every
enumeration, as in [Milestone 1](brute-milestone1.md#what-was-run).

## Findings

No claim was violated. The runs stopped two enumerations, and `collect` failed the guards of
four more; each is a fault of a test (the oracle's test of a suspicious result, and the formats
the driver's plan gave a kernel), established below, not of a statement, the generator, the
code, a compiler or a machine.

### The radius of an accumulator at precision 2

The Mac's enumerations of `acc_radius_1` and `acc_radius_2` in `fp:2:-1:1` stopped: 8 results
of each that the oracle calls suspicious, an infinite radius with the mask `ok` true on small
operands, for instance

```
acc_radius_1 fp:2:-1:1 0x0p+0 0x0p+0 0x0p+0 0x1p+0 #exhaustive:2 -> inf 1
```

($a = m = g = 0$, $t = 1$). **No claim was violated**: the claim of `acc_radius_k` is an upper
bound on the radius where `ok` is true, which $+\infty$ is, and no claim says the radius is
finite. The oracle calls a non-finite result suspicious when the operands and the exact value
lie within a quarter of the largest number $\Omega$, which a correct kernel keeps finite if its
constant factors are at most 4. The radius is $r = \mathrm{RN}(sK + C)$ with
$K = \mathrm{up}((1+u)^8)$: at precision 2, $u = 1/4$ and $K = 6$, the largest number of
`fp:2:-1:1`, with $C = 3$; $s = 1$ gives $9$, which rounds to $+\infty$. With a factor of 6, an
$s$ near $\Omega/4$ overflows in any exponent range of precision 2, as the radius of `ball_mul_1`
does at precision 1 ([Milestone 1](brute-milestone1.md#supplementary-run-precision-1)). The case
above is already the smallest: zeros and one, in the smallest format of precision 2 whose
constants are numbers. Not a fault of the statement, the generator, the code, a compiler or a
machine: a test, the oracle's, that does not apply to this kernel at this precision, in a format
the plan chose.

What was done, as for `ball_mul_1` in Milestone 1: the exact test `tests/brute/widen.py`, which
runs every operand of the format through the interpreter in the format and in one with 13 more
exponents above, now compares an output that its claims condition on a mask only where the mask
is true. In `fp:2:-1:1`, of the 3 584 cases of each kernel, `ok` is false in 3 072 (the radius is
a NaN in 96 of them: the product of the count overflows and is multiplied by a zero); of the 512
where it is true, 34 give a finite radius equal to the wide one and 478 an infinite one exactly
where the wide radius exceeds $\Omega$
([`widen-acc-radius.txt`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/brute/supplementary)).
Both kernels at precision 2 joined `RADIUS_OVERFLOW` of the driver (a suspicious result does not
fail their run; commit `0716b84`, with its test), and the two enumerations were run again with
that driver, complete, every guard passed, 3 584 cases each judged, none failed
([`macos-arm64-radius.json`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/brute/supplementary)).
The Mac's stored summary keeps the finding and the two enumerations it stopped, which are
therefore incomplete there.

### Four enumerations whose guards failed

`collect` applies the guards to each enumeration as a whole. Four enumerations of the plan were
complete, every case judged, none failed, but did not exercise what the guards ask:

- **`bound_sum_2` (the Linux machine) and `bound_dot_2` (the Mac) in `fp:16:-30:14`.** The guards
  ask the mask `ok` of a bound to be true somewhere in $1/5 < m\,\mathrm{unit}(K) \le 1/4$. The
  mask's test is $a = \mathrm{RN}(m\,\mathrm{up}((1+u)(\mathrm{unit}(K) + \eta/2))) \le
  \mathrm{up}(1/4)$, and in this format $\eta = 2^{-30}$ is about $\mathrm{unit}(K)$ itself
  ($3u^2$ and $4u^2$ at $p = 16$): the mask turns false near $m\,\mathrm{unit}(K) = 1/6$. Of the
  983 041 counts of `bound_dot_2`, the mask is true in 884 737, all with $m\,\mathrm{unit}(K) \le
  1/5$, and false in all 13 108 of the band. The claim (the mask true only where
  $m\,\mathrm{unit}(K) \le 1/2$) holds; the band is not reached. In `binary64` and `binary32`
  $\eta$ is negligible.
- **`acc_merge_2` in `fp:3:-2:-1` (complete, the Linux machine) and in `fp:4:-3:-1` (restricted to
  the quick tier's values, the Mac).** The guards ask every rounding to nearest to meet an
  inexact case. With two exponents every sum of magnitudes $a + c$ is exact, a tie or beyond the
  largest number, and at precision 4 every sum of those values is exact or a tie ($5/4 + 5$): 272
  322 exact and 30 258 ties, no other inexact case. The same claim met inexact cases in
  `fp:3:-2:0` and in the compiled runs.

The plan now gives those kernels formats in which the guards can pass (commit `68da628`, with two
tests that fail on the old entries): `fp:16:-50:14` for the bounds of two limbs ($\eta$ is
$2^{-20}$ of $\mathrm{unit}(K)$ there), `fp:3:-3:-1` complete and $9/8$ among the values of $a$
at precision 4 for `acc_merge_2`. The four were run on the Mac from the repository at that
commit, whose code of these three kernels is that of `5f597fb` (the generated code, the claims
and the kernel descriptions are the same, and the oracle and the interpreter did not change):
complete, every guard passed, none failed; the mask is true in the band for 8 737 counts of
`bound_sum_2` and 13 107 of `bound_dot_2`, and the roundings of `acc_merge_2` met 125 316 and
15 129 inexact cases
([`macos-arm64-guards.json`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/brute/supplementary)).
The machines' stored summaries keep the four as they were run, with their guards failed.

## Faults of the driver found by the runs

Each fixed in `tests/brute/` with a test in `test_brute.py`; none touches the code under test,
a claim, the oracle or a guard.

- **The products of BallVectors at 4 096 coefficients** (commit `1b37080`). The compiled part
  gave every loop random arrays of up to 4 096 elements. A product of BallVectors (`bv_conv_1`,
  `bv_conv_2`) is judged in a time that grows faster than the product of its two lengths: 200
  requests took the oracle 0.9 seconds at up to 64 coefficients, 8 at 256, more than seven
  minutes at 4 096, so that a unit of the run's size would have passed the timeout of a
  pipeline. Their requests are now of up to 256 coefficients (`PRODUCT_LENGTH`, four times the
  full tier's 64); the convolutions of numbers, whose check took a second at 1 024, and every
  other loop keep 4 096. The second pilot found it, before the runs.
- **`report` and the claims of Milestone 2** (commits `fc02aad`, `2f3b82d`): it read a claimed
  number of gaps out of every `upper` entry (an error on the radii of the ball vectors and the
  bounds of the folds, which state a value), had no headline for the kinds of the loops and of
  the interval kernels, and compared every runner of a loop with every other, where the scalar
  ones judge one stream and the packed ones of each backend another. The tables of this page
  are those of the fixed `report`.
- **The radius of an accumulator at precision 2** (commit `0716b84`), above.

## The aim: a hundred million results per kernel and format

Per kernel and format, summed over the machines and their runners (the counts of `brute.py report` below; a case judged by 36 runners counts 36 times), by group:

| Group | Kernel and format pairs | Cases (least, median, most) | Judged results (least, median, most) | Pairs at $10^8$ cases | Pairs at $10^8$ judged |
|---|---|---|---|---|---|
| Phase B: the 116 kernels of the aim, 115 new or changed and `to_nearest_2` | 232 | 100 800 000, 103 500 000, 103 500 000 | 82 871 478, 103 500 000, 103 500 000 | 232 | 176 |
| The other 75 new or changed kernels (phase A) | 150 | 7 200 000, 7 200 000, 7 200 000 | 5 751 810, 7 200 000, 7 200 000 | 0 | 0 |
| The other 42 kernels unchanged since Milestone 1 (phase A) | 84 | 7 200 000, 7 200 000, 7 200 000 | 5 430 024, 7 200 000, 7 200 000 | 0 | 0 |
| The 47 loops over arrays, in arrays (phase A) | 94 | 42 000, 63 000, 72 000 | 42 000, 63 000, 72 000 | 0 | 0 |

Of the 232 pairs of phase B, 232 reach $10^8$ cases and 176 reach $10^8$ judged results; below it in judged results (a finite-domain kernel whose result is not finite is not judged): `acc_mul_entry_1` `binary64` 82 871 478, `acc_mul_1` `binary64` 82 896 210, `scale_step_1` `binary64` 82 983 672, `mul_1_1` `binary64` 82 997 496, `scale_step_1` `binary32` 83 600 208, `mul_1_1` `binary32` 83 643 858, `two_prod_dekker` `binary32` 86 976 072, `acc_mul_1` `binary32` 88 923 600, `acc_mul_entry_1` `binary32` 88 929 864, `split` `binary32` 89 555 598, `split` `binary64` 91 605 546, `two_prod_dekker` `binary64` 92 547 774, `ball_mul_pow2_1` `binary64` 93 043 386, `ball_mul_pow2_1` `binary32` 93 098 520, `mul_pow2_step_2` `binary64` 94 342 464, `mul_pow2_step_2` `binary32` 94 642 362, `dot_step_1` `binary64` 95 261 706, `dot_entry_step_1` `binary64` 95 282 190, `dot_step_1` `binary32` 95 441 796, `dot_entry_step_1` `binary32` 95 448 006, `axpy_entry_step_1` `binary64` 95 962 122, `axpy_step_1` `binary64` 95 965 758, `mul_pow2_2` `binary64` 96 052 896, `axpy_entry_step_1` `binary32` 96 111 594, `axpy_step_1` `binary32` 96 114 312, `mul_pow2_2` `binary32` 96 303 888, `scale_step_2` `binary32` 96 415 236, `scale_entry_step_2` `binary32` 96 421 788, `scale_step_2` `binary64` 96 503 688, `scale_entry_step_2` `binary64` 96 516 720, `bv_mul_pow2_step_1` `binary64` 96 796 926, `mul_pow2_step_1` `binary64` 96 815 808, `mul_pow2_step_1` `binary32` 97 117 092, `bv_mul_pow2_step_1` `binary32` 97 149 546, `sum_entry_step_1` `binary64` 97 199 838, `sub_1_1` `binary64` 97 203 456, `add_entry_step_1` `binary64` 97 209 720, `sub_1_1` `binary32` 97 210 782, `sub_entry_step_1` `binary32` 97 214 940, `add_entry_step_1` `binary32` 97 215 228, `sum_entry_step_1` `binary32` 97 220 088, `sub_entry_step_1` `binary64` 97 237 800, `acc_merge_1` `binary32` 98 123 778, `acc_merge_1` `binary64` 98 125 272, `mul_2_1_entry` `binary32` 98 134 362, `mul_2_1_entry` `binary64` 98 246 034, `two_prod_entry` `binary32` 98 308 530, `two_prod_entry` `binary64` 98 321 652, `sum_entry_step_2` `binary32` 98 768 880, `sub_entry_step_2` `binary32` 98 778 618, `sum_fast_entry_step_2` `binary32` 98 785 170, `sum_entry_step_2` `binary64` 98 795 970, `sum_fast_entry_step_2` `binary64` 98 813 088, `sub_entry_step_2` `binary64` 98 814 924, `two_sum_entry` `binary64` 99 977 130, `two_sum_entry` `binary32` 99 984 024.

The 116 kernels of phase B, `to_nearest_2` among them, unchanged since Milestone 1 (above): `abs_upper_2`, `acc_add_1`, `acc_merge_1`, `acc_mul_1`, `acc_mul_entry_1`, `add_down_1`, `add_down_entry`, `add_entry_step_1`, `add_entry_step_2`, `add_up_1`, `add_up_entry`, `axpy_entry_step_1`, `axpy_step_1`, `ball_contains_ball_1`, `ball_contains_point_1`, `ball_contains_point_2`, `ball_equal_1`, `ball_equal_2`, `ball_from_interval_1`, `ball_from_interval_2`, `ball_less_1`, `ball_less_equal_1`, `ball_lower_as_1`, `ball_make_1`, `ball_make_2`, `ball_mul_pow2_1`, `ball_narrow_2_1`, `ball_negative_1`, `ball_negative_2`, `ball_positive_1`, `ball_positive_2`, `ball_scale_1_full`, `ball_split_1`, `ball_to_interval_1`, `ball_upper_as_1`, `ball_zero_1`, `ball_zero_2`, `bv_center_2`, `bv_center_entry_1`, `bv_conv_finish`, `bv_make_finish`, `bv_make_radius`, `bv_mul_pow2_step_1`, `bv_neg_radius`, `dot_entry_step_1`, `dot_step_1`, `fast_two_sum_entry`, `fold_finish_1`, `fold_finish_2`, `interval_contains_1`, `interval_empty_1`, `interval_empty_2`, `interval_entire_1`, `interval_entire_2`, `interval_equal_1`, `interval_intersection_1`, `interval_less_1`, `interval_less_equal_1`, `interval_make_1`, `interval_mid_rad_1`, `interval_neg_1`, `interval_negative_1`, `interval_negative_2`, `interval_positive_1`, `interval_positive_2`, `interval_rel_disjoint_1`, `interval_rel_equal_1`, `interval_rel_interior_1`, `interval_split_1`, `interval_subset_1`, `interval_to_ball_1`, `interval_zero_1`, `interval_zero_2`, `mul_1_1`, `mul_2_1_entry`, `mul_dir_1`, `mul_down_1`, `mul_down_entry`, `mul_pow2_2`, `mul_pow2_2_full`, `mul_pow2_step_1`, `mul_pow2_step_2`, `mul_up_1`, `mul_up_entry`, `neg_1`, `next_down`, `next_up`, `norm_combine`, `norm_finish_1`, `norm_finish_2`, `norm_step_1`, `norm_step_2`, `radd`, `radd_entry`, `rmul`, `scale_entry_step_2`, `scale_step_1`, `scale_step_2`, `split`, `sub_1_1`, `sub_down_1`, `sub_down_entry`, `sub_entry_step_1`, `sub_entry_step_2`, `sub_up_1`, `sub_up_entry`, `sum_entry_step_1`, `sum_entry_step_2`, `sum_fast_entry_step_2`, `to_down_2`, `to_nearest_2`, `to_up_2`, `two_prod_dekker`, `two_prod_entry`, `two_sum_entry`, `two_sum_ord`.

The other 75 new or changed kernels, which have their share of phase A only: `acc_add_2`, `acc_merge_2`, `acc_mul_2`, `acc_mul_entry_2`, `acc_radius_1`, `acc_radius_2`, `add_ball_2_2`, `add_down_2_2`, `add_up_2_2`, `axpy_entry_step_2`, `axpy_entry_step_2_1`, `axpy_step_2`, `axpy_step_2_1`, `ball_add_1_full`, `ball_add_2_full`, `ball_contains_ball_2`, `ball_hull_1`, `ball_hull_2`, `ball_intersection_1`, `ball_intersection_2`, `ball_less_2`, `ball_less_equal_2`, `ball_lower_as_2`, `ball_mul_1_full`, `ball_mul_2_full`, `ball_mul_pow2_1_full`, `ball_mul_pow2_2`, `ball_mul_pow2_2_full`, `ball_scale_2_full`, `ball_scale_2_full_entry`, `ball_split_2`, `ball_sub_1_full`, `ball_sub_2_full`, `ball_to_interval_2`, `ball_upper_as_2`, `bound_dot_1`, `bound_dot_2`, `bound_sum_1`, `bound_sum_2`, `bv_add_radius_1`, `bv_add_radius_2`, `bv_mul_pow2_radius`, `bv_mul_pow2_step_2`, `bv_scale_radius_1`, `bv_scale_radius_2`, `conv_radius`, `dot_step_2`, `interval_add_1`, `interval_add_2`, `interval_contains_2`, `interval_equal_2`, `interval_hull_1`, `interval_hull_2`, `interval_intersection_2`, `interval_less_2`, `interval_less_equal_2`, `interval_make_2`, `interval_mid_rad_2`, `interval_mul_1`, `interval_mul_2`, `interval_neg_2`, `interval_rel_disjoint_2`, `interval_rel_equal_2`, `interval_rel_interior_2`, `interval_split_2`, `interval_sub_1`, `interval_sub_2`, `interval_subset_2`, `interval_to_ball_2`, `mul_2_1_full_entry`, `mul_ball_2_2`, `mul_dir_2_2`, `mul_ext_2_2`, `sub_down_2_2`, `sub_up_2_2`.

Per kernel and format, summed over the machines and their runners: 42 000 to 103 500 000 cases (median 7 200 000), of which 42 000 to 103 500 000 judged (a finite result, or any result in the extended domain), from 2 000 to 3 100 000 distinct cases. 232 of 560 kernel and format pairs reach $10^8$ cases; the fewest: `bv_conv_1` `binary32` 42 000, `bv_conv_1` `binary64` 42 000, `bv_conv_2` `binary32` 42 000, `bv_conv_2` `binary64` 42 000, `conv_1` `binary32` 42 000.

176 of 560 reach $10^8$ judged results; below it: `bv_conv_1` `binary32` 42 000, `bv_conv_1` `binary64` 42 000, `bv_conv_2` `binary32` 42 000, `bv_conv_2` `binary64` 42 000, `conv_1` `binary32` 42 000, `conv_1` `binary64` 42 000, `conv_1_entry` `binary32` 42 000, `conv_1_entry` `binary64` 42 000, `conv_2` `binary32` 42 000, `conv_2` `binary64` 42 000, `add_2_entry` `binary32` 63 000, `add_2_entry` `binary64` 63 000, `axpy_1` `binary32` 63 000, `axpy_1` `binary64` 63 000, `axpy_1_entry` `binary32` 63 000, `axpy_1_entry` `binary64` 63 000, `axpy_2` `binary32` 63 000, `axpy_2` `binary64` 63 000, `axpy_2_1` `binary32` 63 000, `axpy_2_1` `binary64` 63 000, `axpy_2_1_entry` `binary32` 63 000, `axpy_2_1_entry` `binary64` 63 000, `axpy_2_entry` `binary32` 63 000, `axpy_2_entry` `binary64` 63 000, `bv_add_1` `binary32` 63 000, `bv_add_1` `binary64` 63 000, `bv_add_2` `binary32` 63 000, `bv_add_2` `binary64` 63 000, `bv_make_1` `binary32` 63 000, `bv_make_1` `binary64` 63 000, `bv_make_2` `binary32` 63 000, `bv_make_2` `binary64` 63 000, `bv_mul_pow2_1` `binary32` 63 000, `bv_mul_pow2_1` `binary64` 63 000, `bv_mul_pow2_2` `binary32` 63 000, `bv_mul_pow2_2` `binary64` 63 000, `bv_neg_1` `binary32` 63 000, `bv_neg_1` `binary64` 63 000, `bv_neg_2` `binary32` 63 000, `bv_neg_2` `binary64` 63 000, `bv_scale_1` `binary32` 63 000, `bv_scale_1` `binary64` 63 000, `bv_scale_2` `binary32` 63 000, `bv_scale_2` `binary64` 63 000, `bv_sub_1` `binary32` 63 000, `bv_sub_1` `binary64` 63 000, `bv_sub_2` `binary32` 63 000, `bv_sub_2` `binary64` 63 000, `dot_1` `binary32` 63 000, `dot_1` `binary64` 63 000, `dot_1_entry` `binary32` 63 000, `dot_1_entry` `binary64` 63 000, `dot_2` `binary32` 63 000, `dot_2` `binary64` 63 000, `mul_pow2_map_1` `binary32` 63 000, `mul_pow2_map_1` `binary64` 63 000, `mul_pow2_map_2` `binary32` 63 000, `mul_pow2_map_2` `binary64` 63 000, `norm_upper_1` `binary32` 63 000, `norm_upper_1` `binary64` 63 000, `norm_upper_2` `binary32` 63 000, `norm_upper_2` `binary64` 63 000, `scale_1` `binary32` 63 000, `scale_1` `binary64` 63 000, `scale_2` `binary32` 63 000, `scale_2` `binary64` 63 000, `scale_2_entry` `binary32` 63 000, `scale_2_entry` `binary64` 63 000, `sub_1` `binary32` 63 000, `sub_1` `binary64` 63 000, `sub_1_entry` `binary32` 63 000, `sub_1_entry` `binary64` 63 000, `sub_2` `binary32` 63 000, `sub_2` `binary64` 63 000, `sub_2_entry` `binary32` 63 000, `sub_2_entry` `binary64` 63 000, `sum_1` `binary32` 63 000, `sum_1` `binary64` 63 000, `sum_1_entry` `binary32` 63 000, `sum_1_entry` `binary64` 63 000, `sum_2` `binary32` 63 000, `sum_2` `binary64` 63 000, `sum_2_entry` `binary32` 63 000, `sum_2_entry` `binary64` 63 000, `sum_fast_2` `binary32` 63 000, `sum_fast_2` `binary64` 63 000, `sum_fast_2_entry` `binary32` 63 000, `sum_fast_2_entry` `binary64` 63 000, `add_1` `binary32` 72 000, `add_1` `binary64` 72 000, `add_1_entry` `binary32` 72 000, `add_1_entry` `binary64` 72 000, `add_2` `binary32` 72 000, `add_2` `binary64` 72 000, `ball_mul_2` `binary32` 5 430 024, `ball_scale_2` `binary32` 5 557 122, `ball_mul_2` `binary64` 5 583 888, `ball_scale_1` `binary32` 5 599 476, `ball_mul_1` `binary32` 5 620 824, `ball_mul_1` `binary64` 5 651 064, `ball_scale_2` `binary64` 5 705 532, `ball_scale_1` `binary64` 5 716 692, `acc_mul_2` `binary64` 5 751 810, `acc_mul_entry_2` `binary64` 5 759 622, `acc_mul_2` `binary32` 6 171 606, `acc_mul_entry_2` `binary32` 6 173 982, `dot_step_2` `binary64` 6 590 862, `dot_step_2` `binary32` 6 598 080, `ball_sub_1` `binary32` 6 628 662, `mul_dir_2_2` `binary32` 6 632 010, `ball_add_1` `binary32` 6 632 478, `ball_add_1` `binary64` 6 633 918, `mul_ball_2_2` `binary32` 6 634 296, `ball_sub_1` `binary64` 6 634 872, `mul_dir_2_2` `binary64` 6 641 298, `mul_ball_2_2` `binary64` 6 643 314, `ball_mul_pow2_2` `binary64` 6 643 890, `ball_mul_pow2_2` `binary32` 6 652 908, `ball_sub_2` `binary32` 6 660 900, `axpy_entry_step_2` `binary64` 6 666 768, `axpy_step_2_1` `binary64` 6 666 768, `axpy_entry_step_2` `binary32` 6 667 254, `axpy_entry_step_2_1` `binary64` 6 667 902, `ball_add_2` `binary32` 6 667 956, `axpy_step_2` `binary64` 6 669 288, `axpy_step_2_1` `binary32` 6 669 342, `ball_add_2` `binary64` 6 670 062, `ball_sub_2` `binary64` 6 670 566, `axpy_step_2` `binary32` 6 671 394, `axpy_entry_step_2_1` `binary32` 6 673 086, `bv_mul_pow2_step_2` `binary64` 6 740 856, `bv_mul_pow2_step_2` `binary32` 6 762 168, `add_1_1` `binary64` 6 765 642, `add_1_1` `binary32` 6 769 008, `mul_2_2` `binary32` 6 883 434, `mul_2_1` `binary32` 6 886 782, `mul_2_2` `binary64` 6 891 426, `mul_2_1` `binary64` 6 892 866, `two_prod` `binary64` 6 897 024, `two_prod` `binary32` 6 897 474, `add_down_2_2` `binary64` 6 987 060, `add_down_2_2` `binary32` 6 987 474, `sub_up_2_2` `binary32` 6 988 302, `sub_down_2_2` `binary32` 6 988 950, `add_ball_2_2` `binary32` 6 989 814, `add_up_2_2` `binary32` 6 991 218, `sub_up_2_2` `binary64` 6 991 326, `sub_down_2_2` `binary64` 6 992 046, `add_up_2_2` `binary64` 6 994 800, `add_ball_2_2` `binary64` 6 995 718, `acc_add_2` `binary32` 6 999 696, `acc_add_2` `binary64` 7 002 594, `acc_merge_2` `binary32` 7 009 452, `acc_merge_2` `binary64` 7 011 252, `two_sum` `binary64` 7 015 698, `fast_two_sum` `binary32` 7 016 400, `two_sum` `binary32` 7 017 066, `fast_two_sum` `binary64` 7 017 354, `sub_1_2` `binary32` 7 053 786, `sub_1_2` `binary64` 7 053 894, `add_2_2` `binary32` 7 054 092, `add_2_2` `binary64` 7 054 200, `sub_2_2` `binary32` 7 054 488, `sub_2_1` `binary32` 7 056 882, `add_2_1` `binary32` 7 057 656, `sub_2_2` `binary64` 7 058 718, `sub_2_1` `binary64` 7 058 772, `add_2_1` `binary64` 7 059 132, `add_fast_2_2` `binary32` 7 060 896, `add_fast_2_2` `binary64` 7 061 616, `abs_2` `binary32` 7 200 000, `abs_2` `binary64` 7 200 000, `acc_radius_1` `binary32` 7 200 000, `acc_radius_1` `binary64` 7 200 000, `acc_radius_2` `binary32` 7 200 000, `acc_radius_2` `binary64` 7 200 000, `add_2_1_full` `binary32` 7 200 000, `add_2_1_full` `binary64` 7 200 000, `add_2_2_full` `binary32` 7 200 000, `add_2_2_full` `binary64` 7 200 000, `add_fast_2_2_full` `binary32` 7 200 000, `add_fast_2_2_full` `binary64` 7 200 000, `ball_add_1_full` `binary32` 7 200 000, `ball_add_1_full` `binary64` 7 200 000, `ball_add_2_full` `binary32` 7 200 000, `ball_add_2_full` `binary64` 7 200 000, `ball_contains_ball_2` `binary32` 7 200 000, `ball_contains_ball_2` `binary64` 7 200 000, `ball_hull_1` `binary32` 7 200 000, `ball_hull_1` `binary64` 7 200 000, `ball_hull_2` `binary32` 7 200 000, `ball_hull_2` `binary64` 7 200 000, `ball_intersection_1` `binary32` 7 200 000, `ball_intersection_1` `binary64` 7 200 000, `ball_intersection_2` `binary32` 7 200 000, `ball_intersection_2` `binary64` 7 200 000, `ball_less_2` `binary32` 7 200 000, `ball_less_2` `binary64` 7 200 000, `ball_less_equal_2` `binary32` 7 200 000, `ball_less_equal_2` `binary64` 7 200 000, `ball_lower_as_2` `binary32` 7 200 000, `ball_lower_as_2` `binary64` 7 200 000, `ball_mul_1_full` `binary32` 7 200 000, `ball_mul_1_full` `binary64` 7 200 000, `ball_mul_2_full` `binary32` 7 200 000, `ball_mul_2_full` `binary64` 7 200 000, `ball_mul_pow2_1_full` `binary32` 7 200 000, `ball_mul_pow2_1_full` `binary64` 7 200 000, `ball_mul_pow2_2_full` `binary32` 7 200 000, `ball_mul_pow2_2_full` `binary64` 7 200 000, `ball_neg_1` `binary32` 7 200 000, `ball_neg_1` `binary64` 7 200 000, `ball_neg_2` `binary32` 7 200 000, `ball_neg_2` `binary64` 7 200 000, `ball_scale_2_full` `binary32` 7 200 000, `ball_scale_2_full` `binary64` 7 200 000, `ball_scale_2_full_entry` `binary32` 7 200 000, `ball_scale_2_full_entry` `binary64` 7 200 000, `ball_split_2` `binary32` 7 200 000, `ball_split_2` `binary64` 7 200 000, `ball_sub_1_full` `binary32` 7 200 000, `ball_sub_1_full` `binary64` 7 200 000, `ball_sub_2_full` `binary32` 7 200 000, `ball_sub_2_full` `binary64` 7 200 000, `ball_to_interval_2` `binary32` 7 200 000, `ball_to_interval_2` `binary64` 7 200 000, `ball_upper_as_2` `binary32` 7 200 000, `ball_upper_as_2` `binary64` 7 200 000, `bound_dot_1` `binary32` 7 200 000, `bound_dot_1` `binary64` 7 200 000, `bound_dot_2` `binary32` 7 200 000, `bound_dot_2` `binary64` 7 200 000, `bound_sum_1` `binary32` 7 200 000, `bound_sum_1` `binary64` 7 200 000, `bound_sum_2` `binary32` 7 200 000, `bound_sum_2` `binary64` 7 200 000, `bv_add_radius_1` `binary32` 7 200 000, `bv_add_radius_1` `binary64` 7 200 000, `bv_add_radius_2` `binary32` 7 200 000, `bv_add_radius_2` `binary64` 7 200 000, `bv_mul_pow2_radius` `binary32` 7 200 000, `bv_mul_pow2_radius` `binary64` 7 200 000, `bv_scale_radius_1` `binary32` 7 200 000, `bv_scale_radius_1` `binary64` 7 200 000, `bv_scale_radius_2` `binary32` 7 200 000, `bv_scale_radius_2` `binary64` 7 200 000, `conv_radius` `binary32` 7 200 000, `conv_radius` `binary64` 7 200 000, `eq_2_1` `binary32` 7 200 000, `eq_2_1` `binary64` 7 200 000, `eq_2_2` `binary32` 7 200 000, `eq_2_2` `binary64` 7 200 000, `interval_add_1` `binary32` 7 200 000, `interval_add_1` `binary64` 7 200 000, `interval_add_2` `binary32` 7 200 000, `interval_add_2` `binary64` 7 200 000, `interval_contains_2` `binary32` 7 200 000, `interval_contains_2` `binary64` 7 200 000, `interval_equal_2` `binary32` 7 200 000, `interval_equal_2` `binary64` 7 200 000, `interval_hull_1` `binary32` 7 200 000, `interval_hull_1` `binary64` 7 200 000, `interval_hull_2` `binary32` 7 200 000, `interval_hull_2` `binary64` 7 200 000, `interval_intersection_2` `binary32` 7 200 000, `interval_intersection_2` `binary64` 7 200 000, `interval_less_2` `binary32` 7 200 000, `interval_less_2` `binary64` 7 200 000, `interval_less_equal_2` `binary32` 7 200 000, `interval_less_equal_2` `binary64` 7 200 000, `interval_make_2` `binary32` 7 200 000, `interval_make_2` `binary64` 7 200 000, `interval_mid_rad_2` `binary32` 7 200 000, `interval_mid_rad_2` `binary64` 7 200 000, `interval_mul_1` `binary32` 7 200 000, `interval_mul_1` `binary64` 7 200 000, `interval_mul_2` `binary32` 7 200 000, `interval_mul_2` `binary64` 7 200 000, `interval_neg_2` `binary32` 7 200 000, `interval_neg_2` `binary64` 7 200 000, `interval_rel_disjoint_2` `binary32` 7 200 000, `interval_rel_disjoint_2` `binary64` 7 200 000, `interval_rel_equal_2` `binary32` 7 200 000, `interval_rel_equal_2` `binary64` 7 200 000, `interval_rel_interior_2` `binary32` 7 200 000, `interval_rel_interior_2` `binary64` 7 200 000, `interval_split_2` `binary32` 7 200 000, `interval_split_2` `binary64` 7 200 000, `interval_sub_1` `binary32` 7 200 000, `interval_sub_1` `binary64` 7 200 000, `interval_sub_2` `binary32` 7 200 000, `interval_sub_2` `binary64` 7 200 000, `interval_subset_2` `binary32` 7 200 000, `interval_subset_2` `binary64` 7 200 000, `interval_to_ball_2` `binary32` 7 200 000, `interval_to_ball_2` `binary64` 7 200 000, `le_1_2` `binary32` 7 200 000, `le_1_2` `binary64` 7 200 000, `le_2_1` `binary32` 7 200 000, `le_2_1` `binary64` 7 200 000, `le_2_2` `binary32` 7 200 000, `le_2_2` `binary64` 7 200 000, `lt_1_2` `binary32` 7 200 000, `lt_1_2` `binary64` 7 200 000, `lt_2_1` `binary32` 7 200 000, `lt_2_1` `binary64` 7 200 000, `lt_2_2` `binary32` 7 200 000, `lt_2_2` `binary64` 7 200 000, `make_2` `binary32` 7 200 000, `make_2` `binary64` 7 200 000, `make_2_limbs` `binary32` 7 200 000, `make_2_limbs` `binary64` 7 200 000, `mul_2_1_full` `binary32` 7 200 000, `mul_2_1_full` `binary64` 7 200 000, `mul_2_1_full_entry` `binary32` 7 200 000, `mul_2_1_full_entry` `binary64` 7 200 000, `mul_2_2_full` `binary32` 7 200 000, `mul_2_2_full` `binary64` 7 200 000, `mul_ext_2_2` `binary32` 7 200 000, `mul_ext_2_2` `binary64` 7 200 000, `neg_2` `binary32` 7 200 000, `neg_2` `binary64` 7 200 000, `sub_1_2_full` `binary32` 7 200 000, `sub_1_2_full` `binary64` 7 200 000, `sub_2_1_full` `binary32` 7 200 000, `sub_2_1_full` `binary64` 7 200 000, `sub_2_2_full` `binary32` 7 200 000, `sub_2_2_full` `binary64` 7 200 000, `acc_mul_entry_1` `binary64` 82 871 478, `acc_mul_1` `binary64` 82 896 210, `scale_step_1` `binary64` 82 983 672, `mul_1_1` `binary64` 82 997 496, `scale_step_1` `binary32` 83 600 208, `mul_1_1` `binary32` 83 643 858, `two_prod_dekker` `binary32` 86 976 072, `acc_mul_1` `binary32` 88 923 600, `acc_mul_entry_1` `binary32` 88 929 864, `split` `binary32` 89 555 598, `split` `binary64` 91 605 546, `two_prod_dekker` `binary64` 92 547 774, `ball_mul_pow2_1` `binary64` 93 043 386, `ball_mul_pow2_1` `binary32` 93 098 520, `mul_pow2_step_2` `binary64` 94 342 464, `mul_pow2_step_2` `binary32` 94 642 362, `dot_step_1` `binary64` 95 261 706, `dot_entry_step_1` `binary64` 95 282 190, `dot_step_1` `binary32` 95 441 796, `dot_entry_step_1` `binary32` 95 448 006, `axpy_entry_step_1` `binary64` 95 962 122, `axpy_step_1` `binary64` 95 965 758, `mul_pow2_2` `binary64` 96 052 896, `axpy_entry_step_1` `binary32` 96 111 594, `axpy_step_1` `binary32` 96 114 312, `mul_pow2_2` `binary32` 96 303 888, `scale_step_2` `binary32` 96 415 236, `scale_entry_step_2` `binary32` 96 421 788, `scale_step_2` `binary64` 96 503 688, `scale_entry_step_2` `binary64` 96 516 720, `bv_mul_pow2_step_1` `binary64` 96 796 926, `mul_pow2_step_1` `binary64` 96 815 808, `mul_pow2_step_1` `binary32` 97 117 092, `bv_mul_pow2_step_1` `binary32` 97 149 546, `sum_entry_step_1` `binary64` 97 199 838, `sub_1_1` `binary64` 97 203 456, `add_entry_step_1` `binary64` 97 209 720, `sub_1_1` `binary32` 97 210 782, `sub_entry_step_1` `binary32` 97 214 940, `add_entry_step_1` `binary32` 97 215 228, `sum_entry_step_1` `binary32` 97 220 088, `sub_entry_step_1` `binary64` 97 237 800, `acc_merge_1` `binary32` 98 123 778, `acc_merge_1` `binary64` 98 125 272, `mul_2_1_entry` `binary32` 98 134 362, `mul_2_1_entry` `binary64` 98 246 034, `two_prod_entry` `binary32` 98 308 530, `two_prod_entry` `binary64` 98 321 652, `sum_entry_step_2` `binary32` 98 768 880, `sub_entry_step_2` `binary32` 98 778 618, `sum_fast_entry_step_2` `binary32` 98 785 170, `sum_entry_step_2` `binary64` 98 795 970, `sum_fast_entry_step_2` `binary64` 98 813 088, `sub_entry_step_2` `binary64` 98 814 924, `two_sum_entry` `binary64` 99 977 130, `two_sum_entry` `binary32` 99 984 024.

On each machine, every runner gave the same counts and the same extremes, for every kernel and format (1680 series of runners compared).

## How close the claims came

### Errors by backend

| Kernel | Claim | binary64 scalar | binary64 AVX2 | binary64 NEON | binary32 scalar | binary32 AVX2 | binary32 NEON |
|---|---|---|---|---|---|---|---|
| `acc_add_1` | `error(t) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `acc_merge_1` | `error(t) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `add_1` | `entries(z), step add_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `add_1_1` | `error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `add_1_entry` | `entries(z), step add_entry_step_1: error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `add_2` | `entries(z), step add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999995430 | 0.9999995430 | 0.9999995430 |
| `add_2_entry` | `entries(z), step add_entry_step_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999995430 | 0.9999995430 | 0.9999995430 |
| `add_entry_step_1` | `error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `axpy_1` | `entries(z), step axpy_step_1: error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999998510 | 0.9999998510 | 0.9999998510 |
| `axpy_1_entry` | `entries(z), step axpy_entry_step_1: error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999998510 | 0.9999998510 | 0.9999998510 |
| `axpy_entry_step_1` | `error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999998510 | 0.9999998510 | 0.9999998510 |
| `axpy_step_1` | `error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999998510 | 0.9999998510 | 0.9999998510 |
| `bv_add_1` | `V3, step add_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 0.999726 | 1 - ε, ε < 10⁻⁹ | 0.999214 | 0.9999998808 | 0.999958 | 0.999173 |
| `bv_mul_pow2_1` | `V3, step bv_mul_pow2_step_1: error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or \|x*c\| > eta/(2*u)), exact_flag e` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `bv_mul_pow2_step_1` | `error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or \|x*c\| > eta/(2*u)), exact_flag e` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `bv_sub_1` | `V3, step sub_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 0.998968 | 0.999062 | 0.998135 | 0.999977 | 1 (the claim) | 0.999959 |
| `mul_1_1` | `error(p) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999999404 | 0.9999999404 | 0.9999999404 |
| `mul_pow2_map_1` | `entries(z), step mul_pow2_step_1: error(z) form R, c=0, k=1, t=1/2` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `mul_pow2_step_1` | `error(z) form R, c=0, k=1, t=1/2` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `scale_1` | `entries(z), step scale_step_1: error(z) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999998808 | 0.9999998808 | 0.9999998808 |
| `scale_entry_step_2` | `error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.992292 | 0.9999998510 | 0.9999998510 | 0.9999998510 |
| `scale_step_1` | `error(z) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999999404 | 0.9999999404 | 0.9999999404 |
| `scale_step_2` | `error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.993076 | 0.9999998212 | 0.9999998212 | 0.979176 |
| `sub_1` | `entries(z), step sub_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `sub_1_1` | `error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `sub_1_entry` | `entries(z), step sub_entry_step_1: error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `sub_2` | `entries(z), step sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999995430 | 0.9999995430 | 0.9999995430 |
| `sub_2_entry` | `entries(z), step sub_entry_step_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 1 - ε, ε < 10⁻⁹ | 0.9999995430 | 0.9999995430 | 0.9999995430 |
| `sub_entry_step_1` | `error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `sum_entry_step_1` | `error(t) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `two_prod` | `error(r) form R, c=0, k=2, t=1/2` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `two_prod_entry` | `error(r) form R, c=0, k=2, t=1/2` | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) | 1 (the claim) |
| `mul_2_1_entry` | `error(z) form R, c=2, k=2, t=1` | 0.9999999998 | 0.9999999998 | 0.988493 | 0.9999998808 | 0.9999998808 | 0.999023 |
| `mul_2_1` | `error(z) form R, c=2, k=2, t=1` | 0.994154 | 0.994154 | 0.971381 | 0.9999998510 | 0.9999998510 | 0.980068 |
| `bv_scale_1` | `V3, step scale_step_1: error(z) form R, c=1/(1+u), k=1, t=1/2` | 0.999978 | 0.999809 | 0.999958 | 0.999968 | 0.999664 | 0.999690 |
| `scale_2_entry` | `entries(z), step scale_entry_step_2: error(z) form R, c=2, k=2, t=1` | 0.992336 | 0.996654 | 0.992336 | 0.990311 | 0.998018 | 0.988851 |
| `bv_scale_2` | `V3, step scale_step_2: error(z) form R, c=2, k=2, t=1` | 0.984738 | 0.994686 | 0.982496 | 0.995902 | 0.984487 | 0.975916 |
| `scale_2` | `entries(z), step scale_step_2: error(z) form R, c=2, k=2, t=1` | 0.992336 | 0.992336 | 0.992336 | 0.991841 | 0.995750 | 0.991693 |
| `mul_2_1_full` | `F2, core mul_2_1: error(z) form R, c=2, k=2, t=1` | 0.995324 | 0.995324 | 0.959697 | 0.978571 | 0.978571 | 0.957348 |
| `mul_2_1_full_entry` | `F2, core mul_2_1_entry: error(z) form R, c=2, k=2, t=1` | 0.991667 | 0.979534 | 0.991667 | 0.991020 | 0.991020 | 0.953579 |
| `add_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.961748 | 0.698096 | 0.961748 | 0.732914 | 0.732914 | 0.640281 |
| `mul_2_2_full` | `F2, core mul_2_2: error(z) form R, c=4, k=2, t=3/2` | 0.933668 | 0.933668 | 0.861497 | 0.950727 | 0.950727 | 0.858762 |
| `mul_ball_2_2` | `error(z) form R, c=4, k=2, t=3/2` | 0.949708 | 0.949708 | 0.907410 | 0.942075 | 0.942075 | 0.907495 |
| `mul_2_2` | `error(z) form R, c=4, k=2, t=3/2` | 0.948314 | 0.948314 | 0.891105 | 0.944221 | 0.944221 | 0.872806 |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=13/8` | 0.923232 | 0.923232 | 0.921920 | 0.947220 | 0.947220 | 0.918119 |
| `add_2_1_full` | `F2, core add_2_1: error(z) form R, c=2, k=2, t=0` | 0.522384 | 0.520271 | 0.522384 | 0.875497 | 0.532474 | 0.875497 |
| `axpy_step_2_1` | `error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.800000 | 0.777974 | 0.800000 | 0.800000 | 0.800000 | 0.799609 |
| `ball_lower_as_2` | `error(l) form A, c=5, k=1, t=3` | 0.800000 | 0.800000 | 0.800000 | 0.800000 | 0.800000 | 0.800000 |
| `ball_upper_as_2` | `error(h) form A, c=5, k=1, t=3` | 0.800000 | 0.800000 | 0.800000 | 0.800000 | 0.800000 | 0.800000 |
| `axpy_2_1` | `entries(z), step axpy_step_2_1: error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.785503 | 0.799644 | 0.755469 | 0.797157 | 0.798986 | 0.787485 |
| `axpy_2_1_entry` | `entries(z), step axpy_entry_step_2_1: error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.785331 | 0.790344 | 0.769914 | 0.789268 | 0.789488 | 0.776685 |
| `sub_entry_step_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.620576 | 0.620576 | 0.477615 | 0.787615 | 0.787615 | 0.546793 |
| `axpy_entry_step_2_1` | `error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.780555 | 0.780555 | 0.744275 | 0.767880 | 0.767880 | 0.736039 |
| `mul_pow2_2` | `error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.750000 | 0.719812 | 0.750000 | 0.750000 | 0.750000 |
| `mul_pow2_map_2` | `entries(z), step mul_pow2_step_2: error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.750000 | 0.750000 | 0.750000 | 0.750000 | 0.750000 |
| `mul_pow2_2_full` | `F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1` | 0.747776 | 0.747776 | 0.745860 | 0.750000 | 0.750000 | 0.750000 |
| `mul_pow2_step_2` | `error(z) form R, c=0, k=2, t=1` | 0.729358 | 0.729358 | 0.654806 | 0.750000 | 0.750000 | 0.749023 |
| `sub_1_2_full` | `F2, core sub_1_2: error(z) form R, c=2, k=2, t=0` | 0.744470 | 0.744470 | 0.500000 | 0.666660 | 0.666660 | 0.500000 |
| `bv_mul_pow2_2` | `V3, step bv_mul_pow2_step_2: error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or \|x[0]*c\| > eta/(2*u)) and (x[1]*c = 0 or \|x[1]*c\| > eta/(2*u)), exact_flag e` | 0.671347 | 0.730516 | 0.722112 | 0.741699 | 0.727149 | 0.731853 |
| `axpy_2_entry` | `entries(z), step axpy_entry_step_2: error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.729670 | 0.669801 | 0.661996 | 0.678190 | 0.694813 | 0.655574 |
| `axpy_2` | `entries(z), step axpy_step_2: error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.645205 | 0.725987 | 0.716071 | 0.681521 | 0.672807 | 0.558191 |
| `sub_2_1_full` | `F2, core sub_2_1: error(z) form R, c=2, k=2, t=0` | 0.502159 | 0.502159 | 0.500075 | 0.722508 | 0.602984 | 0.722508 |
| `bv_mul_pow2_step_2` | `error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or \|x[0]*c\| > eta/(2*u)) and (x[1]*c = 0 or \|x[1]*c\| > eta/(2*u)), exact_flag e` | 0.664108 | 0.664108 | 0.625 | 0.716378 | 0.716378 | 0.625 |
| `sum_fast_entry_step_2` | `error(t) form A, c=3, k=2, t=0` | 0.500000 | 0.500000 | 0.500000 | 0.707872 | 0.707872 | 0.499618 |
| `axpy_step_2` | `error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.631500 | 0.631500 | 0.599849 | 0.700851 | 0.700851 | 0.548542 |
| `dot_step_2` | `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.690771 | 0.690771 | 0.546675 | 0.672771 | 0.672771 | 0.641615 |
| `add_entry_step_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.666667 | 0.483344 | 0.676456 | 0.676456 | 0.667471 |
| `acc_merge_2` | `error(t) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.666667 | 0.666667 | 0.629769 | 0.629769 | 0.495478 |
| `add_2_2_full` | `F2, core add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.666667 | 0.598399 | 0.658694 | 0.658694 | 0.594550 |
| `add_ball_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.666667 | 0.483690 | 0.666666 | 0.666666 | 0.666666 |
| `sub_2_2_full` | `F2, core sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.666667 | 0.500000 | 0.666666 | 0.666666 | 0.500000 |
| `acc_add_2` | `error(t) form R, c=3/(1-4*u), k=2, t=0` | 0.566017 | 0.566017 | 0.421882 | 0.666666 | 0.666666 | 0.666666 |
| `sum_entry_step_2` | `error(t) form R, c=3/(1-4*u), k=2, t=0` | 0.661188 | 0.661188 | 0.588263 | 0.666666 | 0.666666 | 0.581524 |
| `sub_1_2` | `error(z) form R, c=2, k=2, t=0` | 0.568171 | 0.568171 | 0.504008 | 0.666665 | 0.666665 | 0.500000 |
| `sub_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.540731 | 0.540731 | 0.526038 | 0.665474 | 0.665474 | 0.522596 |
| `bv_sub_2` | `V3, step sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.605982 | 0.476386 | 0.461948 | 0.657483 | 0.640643 | 0.520524 |
| `axpy_entry_step_2` | `error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.645231 | 0.618911 | 0.645231 | 0.637695 | 0.637695 | 0.620889 |
| `add_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.473954 | 0.473954 | 0.445314 | 0.623892 | 0.623892 | 0.451168 |
| `bv_add_2` | `V3, step add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.596386 | 0.619937 | 0.418729 | 0.570071 | 0.544294 | 0.488241 |
| `acc_mul_2` | `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.395971 | 0.395971 | 0.375000 | 0.607933 | 0.516887 | 0.607933 |
| `sub_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.528585 | 0.489966 | 0.528585 | 0.582452 | 0.582452 | 0.576249 |
| `add_fast_2_2` | `error(z) form A, c=3, k=2, t=0` | 0.499997 | 0.499990 | 0.499997 | 0.500000 | 0.498457 | 0.500000 |
| `acc_mul_entry_2` | `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.478934 | 0.478934 | 0.356384 | 0.500000 | 0.497235 | 0.500000 |
| `add_fast_2_2_full` | `F2, core add_fast_2_2: error(z) form A, c=3, k=2, t=0` | 0.498875 | 0.498875 | 0.488380 | 0.493425 | 0.493425 | 0.481041 |

### Errors over their bounds

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `acc_add_1` | `error(t) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:4:-6:3`) (the claim) |
| `acc_merge_1` | `error(t) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:1:-5:5`) (the claim) |
| `add_1` | `entries(z), step add_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:2:-2:1`) (the claim) |
| `add_1_1` | `error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:7:-14:2`) (the claim) |
| `add_1_entry` | `entries(z), step add_entry_step_1: error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:2:-2:1`) (the claim) |
| `add_2` | `entries(z), step add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 0.453901 (`fp:4:-5:0`) |
| `add_2_entry` | `entries(z), step add_entry_step_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 0.453901 (`fp:4:-5:0`) |
| `add_entry_step_1` | `error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:3:-7:4`) (the claim) |
| `axpy_1` | `entries(z), step axpy_step_1: error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 0.837750 (`fp:3:-4:1`) |
| `axpy_1_entry` | `entries(z), step axpy_entry_step_1: error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 0.837750 (`fp:3:-4:1`) |
| `axpy_entry_step_1` | `error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 0.851686 (`fp:3:-8:1`) |
| `axpy_step_1` | `error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3` | 1 - ε, ε < 10⁻⁹ | 0.851686 (`fp:3:-8:1`) |
| `bv_add_1` | `V3, step add_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 1 - ε, ε < 10⁻⁹ | 1 (`fp:2:-2:1`) (the claim) |
| `bv_mul_pow2_1` | `V3, step bv_mul_pow2_step_1: error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or \|x*c\| > eta/(2*u)), exact_flag e` | 1 (the claim) | 1 (`fp:3:-4:1`) (the claim) |
| `bv_mul_pow2_step_1` | `error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or \|x*c\| > eta/(2*u)), exact_flag e` | 1 (the claim) | 1 (`fp:8:-14:6`) (the claim) |
| `bv_sub_1` | `V3, step sub_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:2:-2:1`) (the claim) |
| `conv_1` | `coefficients(z), fold dot_1: fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1` | 1 - ε, ε < 10⁻⁹ | 0.9 (`fp:3:-3:0`) |
| `conv_1_entry` | `coefficients(z), fold dot_1_entry: fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1` | 1 - ε, ε < 10⁻⁹ | 0.9 (`fp:3:-3:0`) |
| `mul_1_1` | `error(p) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 0.999939 (`fp:7:-20:-6`) |
| `mul_pow2_map_1` | `entries(z), step mul_pow2_step_1: error(z) form R, c=0, k=1, t=1/2` | 1 (the claim) | 1 (`fp:3:-3:0`) (the claim) |
| `mul_pow2_step_1` | `error(z) form R, c=0, k=1, t=1/2` | 1 (the claim) | 1 (`fp:8:-14:6`) (the claim) |
| `scale_1` | `entries(z), step scale_step_1: error(z) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 0.992248 (`fp:5:-7:0`) |
| `scale_entry_step_2` | `error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 0.972718 (`fp:6:-8:-2`) |
| `scale_step_1` | `error(z) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 0.999939 (`fp:7:-20:-6`) |
| `scale_step_2` | `error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 0.972718 (`fp:6:-8:-2`) |
| `sub_1` | `entries(z), step sub_1_1: error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:2:-2:1`) (the claim) |
| `sub_1_1` | `error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:6:-7:4`) (the claim) |
| `sub_1_entry` | `entries(z), step sub_entry_step_1: error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:2:-1:0`) (the claim) |
| `sub_2` | `entries(z), step sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 0.453901 (`fp:4:-5:0`) |
| `sub_2_entry` | `entries(z), step sub_entry_step_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 1 - ε, ε < 10⁻⁹ | 0.453901 (`fp:4:-5:0`) |
| `sub_entry_step_1` | `error(z) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:7:-14:2`) (the claim) |
| `sum_1` | `fold_error(r) eps=u/(1+u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order lanes)` | 1 - ε, ε < 10⁻⁹ | 1 (`fp:4:-4:-1`) |
| `sum_1` | `fold_error(r) eps=u/(1+u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order sequential)` | 1 - ε, ε < 10⁻⁹ | 1 (`fp:4:-4:-1`) |
| `sum_1_entry` | `fold_error(r) eps=u/(1+u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order lanes)` | 1 - ε, ε < 10⁻⁹ | 1 (`fp:3:-3:0`) |
| `sum_1_entry` | `fold_error(r) eps=u/(1+u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order sequential)` | 1 - ε, ε < 10⁻⁹ | 1 (`fp:3:-3:0`) |
| `sum_entry_step_1` | `error(t) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:7:-14:2`) (the claim) |
| `two_prod` | `error(r) form R, c=0, k=2, t=1/2` | 1 (the claim) | 1 (`fp:7:-8:4`) (the claim) |
| `two_prod_entry` | `error(r) form R, c=0, k=2, t=1/2` | 1 (the claim) | 1 (`fp:7:-20:-6`) (the claim) |
| `mul_2_1_entry` | `error(z) form R, c=2, k=2, t=1` | 0.9999999998 | 0.972718 (`fp:6:-8:-2`) |
| `mul_2_1` | `error(z) form R, c=2, k=2, t=1` | 0.9999998510 | 0.972718 (`fp:6:-8:-2`) |
| `bv_scale_1` | `V3, step scale_step_1: error(z) form R, c=1/(1+u), k=1, t=1/2` | 0.999978 | 0.969697 (`fp:3:-4:1`) |
| `dot_1` | `fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1 (order lanes)` | 0.999756 | 0.609756 (`fp:2:-2:1`) |
| `dot_1_entry` | `fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1 (order sequential)` | 0.999756 | 0.9 (`fp:3:-3:0`) |
| `dot_1_entry` | `fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1 (order lanes)` | 0.999724 | 0.609756 (`fp:2:-2:1`) |
| `conv_2` | `coefficients(z), fold dot_2: fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1` | 0.999476 | 0.764346 (`fp:4:-5:0`) |
| `dot_2` | `fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order lanes)` | 0.999476 | - |
| `dot_1` | `fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1 (order sequential)` | 0.999390 | 0.9 (`fp:3:-3:0`) |
| `bv_conv_1` | `V3, coefficients, fold dot_1: fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1` | 0.999225 | 0.944444 (`fp:4:-4:-1`) |
| `scale_2_entry` | `entries(z), step scale_entry_step_2: error(z) form R, c=2, k=2, t=1` | 0.998018 | 0.759322 (`fp:3:-4:1`) |
| `bv_scale_2` | `V3, step scale_step_2: error(z) form R, c=2, k=2, t=1` | 0.995902 | 0.759322 (`fp:3:-4:1`) |
| `scale_2` | `entries(z), step scale_step_2: error(z) form R, c=2, k=2, t=1` | 0.995750 | 0.759322 (`fp:3:-4:1`) |
| `mul_2_1_full` | `F2, core mul_2_1: error(z) form R, c=2, k=2, t=1` | 0.995324 | 0.972718 (`fp:6:-7:-2`) |
| `mul_2_1_full_entry` | `F2, core mul_2_1_entry: error(z) form R, c=2, k=2, t=1` | 0.991667 | 0.972718 (`fp:6:-7:-2`) |
| `add_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.961748 | 0.939450 (`fp:5:-6:3`) |
| `mul_2_2_full` | `F2, core mul_2_2: error(z) form R, c=4, k=2, t=3/2` | 0.950727 | 0.838827 (`fp:5:-6:-1`) |
| `mul_ball_2_2` | `error(z) form R, c=4, k=2, t=3/2` | 0.949708 | 0.898829 (`fp:6:-7:-3`) |
| `mul_2_2` | `error(z) form R, c=4, k=2, t=3/2` | 0.948314 | 0.898829 (`fp:6:-7:-3`) |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=13/8` | 0.947220 | 0.943510 (`fp:7:-12:-1`) |
| `add_2_1_full` | `F2, core add_2_1: error(z) form R, c=2, k=2, t=0` | 0.875497 | 0.939450 (`fp:5:-8:1`) |
| `sub_1_2` | `error(z) form R, c=2, k=2, t=0` | 0.666665 | 0.939450 (`fp:5:-4:2`) |
| `sub_1_2_full` | `F2, core sub_1_2: error(z) form R, c=2, k=2, t=0` | 0.744470 | 0.939450 (`fp:5:-8:1`) |
| `sub_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.665474 | 0.939450 (`fp:5:-4:2`) |
| `sub_2_1_full` | `F2, core sub_2_1: error(z) form R, c=2, k=2, t=0` | 0.722508 | 0.939450 (`fp:5:-8:1`) |
| `axpy_step_2_1` | `error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.800000 | 0.641498 (`fp:4:-5:-3`) |
| `ball_lower_as_2` | `error(l) form A, c=5, k=1, t=3` | 0.800000 | 0.799044 (`fp:4:-8:3`) |
| `ball_upper_as_2` | `error(h) form A, c=5, k=1, t=3` | 0.800000 | 0.799044 (`fp:4:-8:3`) |
| `axpy_2_1` | `entries(z), step axpy_step_2_1: error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.799644 | 0.467001 (`fp:3:-3:0`) |
| `axpy_2_1_entry` | `entries(z), step axpy_entry_step_2_1: error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.790344 | 0.467001 (`fp:3:-3:0`) |
| `sub_entry_step_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.787615 | 0.556176 (`fp:5:-3:2`) |
| `axpy_entry_step_2_1` | `error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4` | 0.780555 | 0.641498 (`fp:4:-5:-3`) |
| `dot_2` | `fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order sequential)` | 0.571129 | 0.764346 (`fp:4:-5:0`) |
| `mul_pow2_2` | `error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.746094 (`fp:6:-12:4`) |
| `mul_pow2_map_2` | `entries(z), step mul_pow2_step_2: error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.71875 (`fp:4:-5:0`) |
| `mul_pow2_2_full` | `F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.746094 (`fp:6:-12:3`) |
| `mul_pow2_step_2` | `error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.746094 (`fp:6:-12:4`) |
| `bv_mul_pow2_step_2` | `error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or \|x[0]*c\| > eta/(2*u)) and (x[1]*c = 0 or \|x[1]*c\| > eta/(2*u)), exact_flag e` | 0.716378 | 0.746094 (`fp:6:-12:4`) |
| `bv_mul_pow2_2` | `V3, step bv_mul_pow2_step_2: error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or \|x[0]*c\| > eta/(2*u)) and (x[1]*c = 0 or \|x[1]*c\| > eta/(2*u)), exact_flag e` | 0.741699 | 0.6875 (`fp:3:-4:1`) |
| `axpy_2_entry` | `entries(z), step axpy_entry_step_2: error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.729670 | 0.399878 (`fp:4:-4:-1`) |
| `axpy_2` | `entries(z), step axpy_step_2: error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.725987 | 0.399878 (`fp:4:-4:-1`) |
| `bv_conv_2` | `V3, coefficients, fold dot_2: fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1` | 0.725159 | 0.561075 (`fp:4:-4:-1`) |
| `sum_fast_entry_step_2` | `error(t) form A, c=3, k=2, t=0` | 0.707872 | 0.671916 (`fp:4:-4:3`) |
| `axpy_step_2` | `error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.700851 | 0.417584 (`fp:5:-3:-2`) |
| `dot_step_2` | `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.690771 | 0.417584 (`fp:5:-3:-2`) |
| `add_entry_step_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.676456 | 0.556176 (`fp:5:-3:2`) |
| `add_fast_2_2` | `error(z) form A, c=3, k=2, t=0` | 0.500000 | 0.671916 (`fp:4:-4:3`) |
| `add_fast_2_2_full` | `F2, core add_fast_2_2: error(z) form A, c=3, k=2, t=0` | 0.498875 | 0.671916 (`fp:4:-6:1`) |
| `acc_merge_2` | `error(t) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0 (`fp:3:-2:-1`) |
| `add_2_2_full` | `F2, core add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.556176 (`fp:5:-6:-1`) |
| `add_ball_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.556176 (`fp:5:-3:2`) |
| `sub_2_2_full` | `F2, core sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.666667 | 0.556176 (`fp:5:-6:-1`) |
| `acc_add_2` | `error(t) form R, c=3/(1-4*u), k=2, t=0` | 0.666666 | 0.273504 (`fp:3:-3:1`) |
| `sum_entry_step_2` | `error(t) form R, c=3/(1-4*u), k=2, t=0` | 0.666666 | 0.556176 (`fp:5:-3:2`) |
| `bv_sub_2` | `V3, step sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.657483 | 0.273504 (`fp:3:-4:1`) |
| `axpy_entry_step_2` | `error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.645231 | 0.417584 (`fp:5:-3:-2`) |
| `add_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.623892 | 0.556176 (`fp:5:-3:2`) |
| `bv_add_2` | `V3, step add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.619937 | 0.273504 (`fp:3:-4:1`) |
| `acc_mul_2` | `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.607933 | 0.372281 (`fp:4:-3:-2`) |
| `sub_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.582452 | 0.556176 (`fp:5:-3:2`) |
| `acc_mul_entry_2` | `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2` | 0.500000 | 0.372281 (`fp:4:-3:-2`) |
| `sum_fast_2` | `fold_error(r) eps=3*u^2, term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order lanes)` | 0.166667 | 0.487062 (`fp:3:-5:2`) |
| `sum_fast_2` | `fold_error(r) eps=3*u^2, term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order sequential)` | 0.353038 | 0.487062 (`fp:3:-5:2`) |
| `sum_fast_2_entry` | `fold_error(r) eps=3*u^2, term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order lanes)` | 0.298889 | 0.487062 (`fp:3:-5:2`) |
| `sum_fast_2_entry` | `fold_error(r) eps=3*u^2, term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order sequential)` | 0.166667 | 0.487062 (`fp:3:-5:2`) |
| `sum_2` | `fold_error(r) eps=3*u^2/(1-4*u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order lanes)` | 0.333333 | 0.211411 (`fp:3:-5:2`) |
| `sum_2` | `fold_error(r) eps=3*u^2/(1-4*u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order sequential)` | 0.333333 | 0.211411 (`fp:3:-5:2`) |
| `sum_2_entry` | `fold_error(r) eps=3*u^2/(1-4*u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order lanes)` | 0.333333 | 0.211411 (`fp:3:-5:2`) |
| `sum_2_entry` | `fold_error(r) eps=3*u^2/(1-4*u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1 (order sequential)` | 0.189732 | 0.211411 (`fp:3:-5:2`) |
| `abs_2` | `error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:8:-16:3`) |
| `bv_center_2` | `error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-11:0`) |
| `bv_neg_2` | `V3, step neg_2: error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:3:-4:1`) |
| `fast_two_sum` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-14:2`) |
| `fast_two_sum_entry` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-7:4`) |
| `neg_2` | `error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:8:-12:-1`) |
| `split` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:13:-60:40`) |
| `two_prod` | `error(r) form R, c=0, k=2, t=0, when product_large` | 0 (exact) | 0 (exact; `fp:7:-8:4`) |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=0, when product_large` | 0 (exact) | 0 (exact; `fp:7:-8:4`) |
| `two_prod_entry` | `error(r) form R, c=0, k=2, t=0, when product_large` | 0 (exact) | 0 (exact; `fp:7:-20:-6`) |
| `two_sum` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-14:2`) |
| `two_sum_entry` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:6:-7:4`) |
| `two_sum_ord` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-7:4`) |

### Upper bounds in gaps

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `radd` | `upper(r) gaps=3/2` | 1.5 (the claim) | 1.5 (`fp:8:-16:3`) (the claim) |
| `radd_entry` | `upper(r) gaps=3/2` | 1.5 (the claim) | 1.5 (`fp:8:-12:-1`) (the claim) |
| `rmul` | `upper(r) gaps=3/2` | 1.5 (the claim) | 1.5 (`fp:7:-11:0`) (the claim) |

### Folds of maxima

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `norm_upper_2` | `upper(r) over max, steps=1` | 1 | 1 (`fp:3:-5:2`) |
| `norm_upper_1` | `upper(r) over max, steps=0` | 0 | 0 (`fp:2:-2:1`) |

### Upper bounds over a stated value

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `bound_dot_2` | `upper(t) >= m*tiny(mul_2_2)*(1+g) if ok` | 8.38861e+6 | 7.82373 (`fp:4:-30:12`) |
| `bound_dot_1` | `upper(t) >= m*tiny(mul_1_1)*(1+g) if ok` | 8.38861e+6 | 5.60938 (`fp:3:-30:12`) |
| `bound_dot_1` | `upper(g) >= m*unit(mul_1_1)/(1-m*unit(mul_1_1)) if ok` | 2.84385 | 2.83871 (`fp:3:-30:12`) |
| `bound_sum_1` | `upper(g) >= m*unit(add_1_1)/(1-m*unit(add_1_1)) if ok` | 2.84391 | 2.83871 (`fp:3:-30:12`) |
| `acc_radius_1` | `upper(r) >= g*(1+u)^2*(1+m*u+2*m^2*u^2)*(a+m*eta/2)+t if ok` | 2.95408 | 2.34497 (`fp:4:-4:2`) |
| `acc_radius_2` | `upper(r) >= g*(1+u)^2*(1+m*u+2*m^2*u^2)*(a+m*eta/2)+t if ok` | 2.85298 | 2.34497 (`fp:4:-4:2`) |
| `bound_dot_2` | `upper(g) >= m*unit(mul_2_2)/(1-m*unit(mul_2_2)) if ok` | 2.80493 | 1.50781 (`fp:20:-50:20`) |
| `bv_scale_2` | `V3, radius bv_scale_radius_2: upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))` | 1.06904 | 1.14516 (`fp:3:-4:1`) |
| `bound_sum_2` | `upper(g) >= m*unit(add_2_2)/(1-m*unit(add_2_2)) if ok` | 1.76235 | 1.06244 (`fp:16:-30:14`) |
| `bv_add_2` | `V3, radius bv_add_radius_2: upper(rz) >= rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)` | 1.15392 | 1.03448 (`fp:3:-4:1`) |
| `bv_sub_2` | `V3, radius bv_add_radius_2: upper(rz) >= rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)` | 1.12583 | 1.03448 (`fp:3:-4:1`) |
| `bv_scale_radius_2` | `upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))` | 1.00858 | 1.14516 (`fp:3:-5:3`) |
| `bv_add_radius_2` | `upper(rz) >= rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)` | 1.00323 | 1.03448 (`fp:3:-5:3`) |
| `bv_add_1` | `V3, radius bv_add_radius_1: upper(rz) >= rx+ry+m*unit(add_1_1)/(1-unit(add_1_1))` | 1.23242 | 1 (`fp:3:-4:1`) |
| `bv_add_radius_1` | `upper(rz) >= rx+ry+m*unit(add_1_1)/(1-unit(add_1_1))` | 1 | 1 (`fp:4:-8:4`) |
| `bv_sub_1` | `V3, radius bv_add_radius_1: upper(rz) >= rx+ry+m*unit(add_1_1)/(1-unit(add_1_1))` | 1.00467 | 1 (`fp:3:-4:1`) |
| `bv_scale_1` | `V3, radius bv_scale_radius_1: upper(rz) >= abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))` | 1.08114 | 0.964844 (`fp:3:-4:1`) |
| `bv_scale_radius_1` | `upper(rz) >= abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))` | 1.00121 | 0.964844 (`fp:3:-5:3`) |
| `bv_mul_pow2_1` | `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c+eta unless ex` | 0.5 | 0.5 (`fp:3:-4:1`) |
| `bv_mul_pow2_2` | `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c+eta unless ex` | 0.5 | 0.5 (`fp:2:-2:1`) |
| `bv_mul_pow2_radius` | `upper(rz) >= rx*c+eta unless ex` | 0.5 | 0.5 (`fp:2:-4:2`) |
| `bv_mul_pow2_1` | `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:3:-4:1`) |
| `bv_mul_pow2_2` | `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:2:-2:1`) |
| `bv_mul_pow2_radius` | `upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:2:-4:2`) |
| `conv_radius` | `upper(rz) >= m*((1+u)*ma*ry+(1+u)*mb*rx+rx*ry)+g*m*(1+u)^2*ma*mb+t` | 0 | 1 (`fp:3:-5:5`) |

### Ball radii

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `mul_ball_2_2` | `encloses(z, d) x*y over ` | 2.57199e+6 | 7.03516 (`fp:4:-9:-3`) |
| `add_ball_2_2` | `encloses(z, d) x+y over ` | 4.19431e+6 | 4.28125 (`fp:3:-6:4`) |
| `ball_mul_2` | `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]` | 2.57142 | 2.16797 (`fp:4:-5:1`) |
| `ball_mul_2_full` | `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|(abs(cx)+rx)*(abs(cy)+ry)\| <= 2^(qmax+p-2)` | 2.56759 | 2.16797 (`fp:4:-5:0`) |
| `ball_mul_1_full` | `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|(abs(cx)+rx)*(abs(cy)+ry)\| <= 2^(qmax+p-4)` | 1.67533 | 1.85352 (`fp:3:-4:1`) |
| `ball_mul_1` | `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]` | 1.78318 | 1.60547 (`fp:4:-4:1`) |
| `ball_scale_2_full_entry` | `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)` | 1.41014 | 1.40625 (`fp:3:-4:1`) |
| `bv_scale_2` | `encloses_entries(z, r) x*a over x=[x +- rx], V1-V4, flag finite, finite when \|(abs(x)+rx)*a\| <= 2^(qmax+p-2)` | 1.50238 | 1.40625 (`fp:3:-4:1`) |
| `ball_scale_2_full` | `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)` | 1.37500 | 1.40625 (`fp:3:-4:1`) |
| `ball_scale_2` | `encloses(cz, rz) x*a over x=[cx +- rx]` | 1.43810 | 1.375 (`fp:3:-6:2`) |
| `ball_sub_2_full` | `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx-cy)+rx+ry\| <= 2^(qmax+p-2)` | 1.26273 | 1.75 (`fp:3:-3:0`) |
| `ball_add_2_full` | `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx+cy)+rx+ry\| <= 2^(qmax+p-2)` | 1.25026 | 1.75 (`fp:3:-3:0`) |
| `ball_add_2` | `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]` | 1.25548 | 1.25 (`fp:3:-3:2`) |
| `ball_sub_2` | `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]` | 1.25567 | 1.25 (`fp:3:-3:2`) |
| `bv_add_2` | `encloses_entries(z, r) x+y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when \|abs(x+y)+rx+ry\| <= 2^(qmax+p-2)` | 1.46777 | 1.25 (`fp:3:-4:1`) |
| `bv_sub_2` | `encloses_entries(z, r) x-y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when \|abs(x-y)+rx+ry\| <= 2^(qmax+p-2)` | 1.44849 | 1.25 (`fp:3:-4:1`) |
| `ball_add_1` | `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]` | 1 | 1 (`fp:2:-6:4`) |
| `ball_add_1_full` | `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx+cy)+rx+ry\| <= 2^(qmax+p-2)` | 1.25 | 1 (`fp:3:-4:1`) |
| `ball_scale_1` | `encloses(cz, rz) x*a over x=[cx +- rx]` | 1.00000 | 1 (`fp:3:-8:2`) |
| `ball_scale_1_full` | `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)` | 1.00000 | 1 (`fp:3:-4:1`) |
| `ball_sub_1` | `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]` | 1.25 | 1 (`fp:3:-4:2`) |
| `ball_sub_1_full` | `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx-cy)+rx+ry\| <= 2^(qmax+p-2)` | 1 | 1 (`fp:2:-5:4`) |
| `bv_add_1` | `encloses_entries(z, r) x+y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when \|abs(x+y)+rx+ry\| <= 2^(qmax+p-2)` | 1.5 | 1 (`fp:3:-4:1`) |
| `bv_scale_1` | `encloses_entries(z, r) x*a over x=[x +- rx], V1-V4, flag finite, finite when \|(abs(x)+rx)*a\| <= 2^(qmax+p-2)` | 1.50065 | 1 (`fp:3:-4:1`) |
| `bv_sub_1` | `encloses_entries(z, r) x-y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when \|abs(x-y)+rx+ry\| <= 2^(qmax+p-2)` | 1.52344 | 1 (`fp:3:-4:1`) |
| `ball_narrow_2_1` | `encloses(cz, rz) x over x=[c +- r], B1-B4, finite when \|abs(c)+r\| <= 2^(qmax+p-2)` | 0.5 | 0.5 (`fp:6:-8:-1`) |
| `ball_mul_pow2_1` | `encloses(cz, rz) x*c over x=[cx +- rx], exactly the set when (cx*c = 0 or \|cx*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:5:-6:1`) |
| `ball_mul_pow2_1_full` | `encloses(cw, rw) x*c over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*c\| <= 2^(qmax+p-2), exactly the set when (cx*c = 0 or \|cx*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:5:-7:0`) |
| `ball_mul_pow2_2` | `encloses(cz, rz) x*c over x=[cx +- rx], exactly the set when (cx[0]*c = 0 or \|cx[0]*c\| > eta/(2*u)) and (cx[1]*c = 0 or \|cx[1]*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:5:-4:1`) |
| `ball_mul_pow2_2_full` | `encloses(cw, rw) x*c over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*c\| <= 2^(qmax+p-2), exactly the set when (cx[0]*c = 0 or \|cx[0]*c\| > eta/(2*u)) and (cx[1]*c = 0 or \|cx[1]*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:4:-5:0`) |
| `ball_neg_1` | `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)` | 0 | 0 (`fp:6:-10:1`) |
| `ball_neg_2` | `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)` | 0 | 0 (`fp:5:-7:0`) |
| `bv_mul_pow2_1` | `encloses_entries(z, r) x*c over x=[x +- rx], V1-V4, flag finite, finite when \|(abs(x)+rx)*c\| <= 2^(qmax+p-2), exactly the set when (x*c = 0 or \|x*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:3:-4:1`) |
| `bv_mul_pow2_2` | `encloses_entries(z, r) x*c over x=[x +- rx], V1-V4, flag finite, finite when \|(abs(x)+rx)*c\| <= 2^(qmax+p-2), exactly the set when (x[0]*c = 0 or \|x[0]*c\| > eta/(2*u)) and (x[1]*c = 0 or \|x[1]*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))` | 0 | 0 (`fp:2:-2:1`) |
| `bv_neg_1` | `encloses_entries(z, r) -x over x=[x +- rx], V1-V4, flag finite, finite when \|abs(x)+rx\| <= 2^(qmax+p+1), exactly the set` | 0 | 0 (`fp:2:-3:2`) |
| `bv_neg_2` | `encloses_entries(z, r) -x over x=[x +- rx], V1-V4, flag finite, finite when \|abs(x)+rx\| <= 2^(qmax+p+1), exactly the set` | 0 | 0 (`fp:3:-4:1`) |

### The interval kernels and the conversions

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `ball_from_interval_1` | `makes_ball(cw, rw) from the interval of lower lo, upper hi, the center within rel u, abs eta of the midpoint, the smallest radius` | 1.00000 | 0.992248 (`fp:7:-9:-2`) |
| `interval_mid_rad_1` | `ball_of_interval(m, r) of [xl, xu], special ieee1788, rel u, abs eta, the smallest radius` | 1.00000 | 0.984615 (`fp:6:-10:1`) |
| `interval_to_ball_1` | `ball_of_interval(c, r) of [xl, xu], special ball, rel u, abs eta, the smallest radius` | 1.00000 | 0.984615 (`fp:6:-10:1`) |
| `sub_down_2_2` | `outward(l) below, exact when (x-y = 0)` | 0.794263 | 0.474531 (`fp:5:-3:2`) |
| `add_down_2_2` | `outward(l) below, exact when (x+y = 0)` | 0.765624 | 0.474531 (`fp:5:-3:2`) |
| `add_up_2_2` | `outward(h) above, exact when (x+y = 0)` | 0.750000 | 0.474531 (`fp:5:-3:2`) |
| `interval_sub_2` | `encloses_interval(zl, zu) x-y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, exact when lower: xl-yu = 0; upper: xu-yl = 0, bounded when \|x-y\| <= 2^(qmax+p-2) (largest upper-bound distance / allowance)` | 0.750000 | 0.406475 (`fp:4:-3:-2`) |
| `mul_dir_2_2` | `outward(h) above` | 0.729568 | 0.500017 (`fp:5:-8:-2`) |
| `ball_to_interval_2` | `interval_of_ball(zl, zu) x over x=[c +- r], tight outward, exact when lower: c-r = 0; upper: c+r = 0, bounded when \|x\| <= 2^(qmax+p-2) (largest upper-bound distance / allowance)` | 0.723987 | 0.493224 (`fp:6:-8:-1`) |
| `mul_ext_2_2` | `outward(l) below, a zero factor gives zero` | 0.703759 | 0.497170 (`fp:6:-6:-3`) |
| `interval_mul_2` | `encloses_interval(zl, zu) x*y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, bounded when \|x*y\| <= 2^(qmax+p-2), I6: [0, 0] times anything is [0, 0] (largest lower-bound distance / allowance)` | 0.700000 | 0.481953 (`fp:5:-4:-3`) |
| `interval_mul_2` | `encloses_interval(zl, zu) x*y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, bounded when \|x*y\| <= 2^(qmax+p-2), I6: [0, 0] times anything is [0, 0] (largest upper-bound distance / allowance)` | 0.700000 | 0.481953 (`fp:5:-4:-3`) |
| `mul_dir_2_2` | `outward(l) below` | 0.700000 | 0.500017 (`fp:5:-8:-2`) |
| `mul_ext_2_2` | `outward(h) above, a zero factor gives zero` | 0.700000 | 0.497170 (`fp:6:-6:-3`) |
| `interval_add_2` | `encloses_interval(zl, zu) x+y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, exact when lower: xl+yl = 0; upper: xu+yu = 0, bounded when \|x+y\| <= 2^(qmax+p-2) (largest lower-bound distance / allowance)` | 0.687500 | 0.406475 (`fp:4:-3:-2`) |
| `sub_up_2_2` | `outward(h) above, exact when (x-y = 0)` | 0.687499 | 0.474531 (`fp:5:-3:2`) |
| `interval_add_2` | `encloses_interval(zl, zu) x+y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, exact when lower: xl+yl = 0; upper: xu+yu = 0, bounded when \|x+y\| <= 2^(qmax+p-2) (largest upper-bound distance / allowance)` | 0.684558 | 0.406475 (`fp:4:-3:-2`) |
| `interval_sub_2` | `encloses_interval(zl, zu) x-y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, exact when lower: xl-yu = 0; upper: xu-yl = 0, bounded when \|x-y\| <= 2^(qmax+p-2) (largest lower-bound distance / allowance)` | 0.677484 | 0.406475 (`fp:4:-3:-2`) |
| `interval_mid_rad_2` | `ball_of_interval(m, r) of [xl, xu], special ieee1788, rel 3*u^2/(1-4*u), abs 2*eta, finite when \|xl\| <= 2^(qmax+p-2) and \|xu\| <= 2^(qmax+p-2)` | 0.666667 | 0.496124 (`fp:4:-5:0`) |
| `ball_to_interval_2` | `interval_of_ball(zl, zu) x over x=[c +- r], tight outward, exact when lower: c-r = 0; upper: c+r = 0, bounded when \|x\| <= 2^(qmax+p-2) (largest lower-bound distance / allowance)` | 0.645270 | 0.493224 (`fp:6:-8:-1`) |
| `interval_to_ball_2` | `ball_of_interval(c, r) of [xl, xu], special ball, rel 3*u^2/(1-4*u), abs 2*eta, finite when \|xl\| <= 2^(qmax+p-2) and \|xu\| <= 2^(qmax+p-2)` | 0.500000 | 0.477612 (`fp:3:-5:2`) |

### The masks of the bounds

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `bound_dot_1` | `holds le(m*unit(mul_1_1), 1/2) if ok` | 0.250000 | 0.250000 (`fp:20:-50:20`) |
| `bound_dot_2` | `holds le(m*unit(mul_2_2), 1/2) if ok` | 0.250000 | 0.249939 (`fp:20:-50:20`) |
| `bound_sum_1` | `holds le(m*unit(add_1_1), 1/2) if ok` | 0.250000 | 0.250000 (`fp:20:-50:20`) |
| `bound_sum_2` | `holds le(m*unit(add_2_2), 1/2) if ok` | 0.250000 | 0.249920 (`fp:20:-50:20`) |

### Finite balls in the enumerations

| Kernel | Enumeration | Cases | Finite ball | Share |
|---|---|---|---|---|
| `ball_add_1` | `fp:1:-5:5` | 76 176 | 38 639 | 50.7 % |
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
| `ball_mul_1` | `fp:1:-6:5` | 105 625 | 48 733 | 46.1 % |
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
| `ball_mul_pow2_1` | `fp:2:-6:1` | 5 670 | 5 272 | 93.0 % |
| `ball_mul_pow2_1` | `fp:3:-6:1` | 25 560 | 22 548 | 88.2 % |
| `ball_mul_pow2_1` | `fp:4:-9:3` | 399 616 | 336 108 | 84.1 % |
| `ball_mul_pow2_1` | `fp:5:-6:1` | 495 936 | 385 972 | 77.8 % |
| `ball_mul_pow2_1` | `fp:5:-8:2` | 1 103 040 | 891 796 | 80.8 % |
| `ball_mul_pow2_1` | `fp:6:-6:1` | 2 152 800 | 1 565 444 | 72.7 % |
| `ball_mul_pow2_1_full` | `fp:2:-4:3` | 5 688 | 4 478 | 78.7 % |
| `ball_mul_pow2_1_full` | `fp:3:-5:2` | 25 580 | 20 772 | 81.2 % |
| `ball_mul_pow2_1_full` | `fp:4:-8:3` | 322 950 | 264 788 | 82.0 % |
| `ball_mul_pow2_1_full` | `fp:5:-7:0` | 495 960 | 419 172 | 84.5 % |
| `ball_mul_pow2_1_full` | `fp:6:-8:-1` | 2 152 826 | 1 845 672 | 85.7 % |
| `ball_mul_pow2_2` | `fp:2:-4:1` | 15 582 | 12 684 | 81.4 % |
| `ball_mul_pow2_2` | `fp:3:-4:1` | 94 752 | 67 576 | 71.3 % |
| `ball_mul_pow2_2` | `fp:3:-7:3` | 1 437 072 | 1 084 748 | 75.5 % |
| `ball_mul_pow2_2` | `fp:4:-4:1` | 499 464 | 314 216 | 62.9 % |
| `ball_mul_pow2_2` | `fp:4:-6:2` | 3 854 400 | 2 641 976 | 68.5 % |
| `ball_mul_pow2_2` | `fp:5:-4:1` | 2 256 800 | 1 283 056 | 56.9 % |
| `ball_mul_pow2_2_full` | `fp:2:-3:2` | 15 596 | 10 674 | 68.4 % |
| `ball_mul_pow2_2_full` | `fp:3:-4:1` | 94 768 | 67 576 | 71.3 % |
| `ball_mul_pow2_2_full` | `fp:3:-6:3` | 949 896 | 681 292 | 71.7 % |
| `ball_mul_pow2_2_full` | `fp:4:-5:0` | 499 482 | 368 248 | 73.7 % |
| `ball_mul_pow2_2_full` | `fp:5:-6:-1` | 2 256 820 | 1 726 464 | 76.5 % |
| `ball_narrow_2_1` | `fp:2:-4:3` | 5 888 | 5 559 | 94.4 % |
| `ball_narrow_2_1` | `fp:3:-5:2` | 35 390 | 34 405 | 97.2 % |
| `ball_narrow_2_1` | `fp:4:-8:3` | 971 674 | 962 329 | 99.0 % |
| `ball_narrow_2_1` | `fp:5:-7:0` | 1 018 226 | 1 011 153 | 99.3 % |
| `ball_narrow_2_1` | `fp:6:-8:-1` | 4 681 442 | 4 665 185 | 99.7 % |
| `ball_neg_1` | `fp:1:-5:6` | 327 | 325 | 99.4 % |
| `ball_neg_1` | `fp:2:-6:5` | 1 328 | 1 326 | 99.8 % |
| `ball_neg_1` | `fp:3:-7:4` | 5 358 | 5 356 | 100.0 % |
| `ball_neg_1` | `fp:5:-13:6` | 225 458 | 225 456 | 100.0 % |
| `ball_neg_1` | `fp:6:-10:1` | 345 698 | 345 696 | 100.0 % |
| `ball_neg_1` | `fp:7:-11:0` | 1 383 618 | 1 383 616 | 100.0 % |
| `ball_neg_2` | `fp:1:-3:4` | 911 | 909 | 99.8 % |
| `ball_neg_2` | `fp:2:-4:3` | 5 888 | 5 886 | 100.0 % |
| `ball_neg_2` | `fp:3:-5:2` | 35 390 | 35 388 | 100.0 % |
| `ball_neg_2` | `fp:4:-8:3` | 971 674 | 971 672 | 100.0 % |
| `ball_neg_2` | `fp:5:-7:0` | 1 018 226 | 1 018 224 | 100.0 % |
| `ball_neg_2` | `fp:6:-8:-1` | 4 681 442 | 4 681 440 | 100.0 % |
| `ball_scale_1` | `fp:1:-3:2` | 1 183 | 783 | 66.2 % |
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
| `ball_scale_2_full_entry` | `fp:2:-2:1` | 12 144 | 4 934 | 40.6 % |
| `ball_scale_2_full_entry` | `fp:2:-4:3` | 223 744 | 127 466 | 57.0 % |
| `ball_scale_2_full_entry` | `fp:3:-3:0` | 100 044 | 50 478 | 50.5 % |
| `ball_scale_2_full_entry` | `fp:3:-4:1` | 687 068 | 374 170 | 54.5 % |
| `ball_scale_2_full_entry` | `fp:4:-4:-1` | 810 324 | 440 840 | 54.4 % |
| `ball_sub_1` | `fp:1:-5:5` | 76 176 | 38 639 | 50.7 % |
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

## The loops over arrays

The 47 loops of `5f597fb`: the folds (sums and dot products of one and two limbs, the fast
sum), the maps (`add_k`, `sub_k`, `axpy_k`, `scale_k`, `mul_pow2_map_k` and their entry forms),
the folds of maxima (`norm_upper_k`), the convolutions (`conv_k`) and the ball vectors (`bv_*`).
In the compiled part each is judged on random arrays of up to 4 096 elements (the products of
BallVectors up to 256 coefficients), of every length of the oracle's schedule (0 to 9, 16, 17,
the lengths around 2, 4 and 8 lanes, and six random lengths up to the largest, log-uniform), in
every order for the scalar runners (sequential; lanes $W = 0$ to 5, 8, and more lanes than
elements) and in the lane order of its register for the packed ones; the oracle judges each array
against the loop's claims: the error over the bound of the fold as a function of the length and
the order, each entry of a map, the radius of each entry of a ball vector, the flag. Each loop and
format had one unit per machine, two on the Windows machine (1 000 arrays per stream on the
Linux machine, 500 on the Mac and on the Windows machine), judged by every runner of the
machine: 42 000 to 72 000 arrays judged per loop and format, about 5 000 of them distinct. The
interpreter enumerated every array of tiny formats up to a length (`FOLD_SHAPES` of the driver),
and the emulated tier judged 20 000 random arrays of up to 256 elements of each loop at each of
the four precisions. No array failed a claim.

**The error against the length.** The oracle keeps the largest error over its bound of a loop
over every array of a stream, with the order and the line that attains it, not its largest per
length. `lengths.py` ran the first 5 000 arrays of each loop and format of the Mac's scalar
stream again (seed `m2r1-mac`; the run judged the first 500 of them, through its 24 scalar
runners), through the scalar runner of the Apple clang build at `5f597fb`, and had the oracle
judge each length class apart: 470 000 arrays, none failed, every class judged without a problem
([`results/milestone2/brute/lengths/macos-arm64.json`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/brute/lengths)).
For a convolution the length is the number of terms of a coefficient, the shorter of the two
lengths. The table gives, per loop and format, the closest value of each claim's statistic over
groups of lengths: the error over its bound for a fold (per order) and for the step of a map, the
slack of the worst entry's radius for a ball vector, the excess of its radius over the value it
states, the steps above RU(V) for a fold of maxima.

What it shows. The sums of one limb (`sum_1`, `sum_1_entry`) come to their bound at every
length from 2 to 4 096, within $10^{-5}$ of it in `binary64` and $1.8 \cdot 10^{-4}$ in
`binary32`; the dot products of one limb (`dot_1`, `dot_1_entry`) come closer as the arrays
grow, from 0.94 of their bound at lengths 2 to 17 to 0.9998 at 1 025 to 4 096. The folds of
two limbs come closest on the shortest arrays and fall away as they grow: the sums of two limbs
reach 1/3 of their bound at lengths 2 to 17 and stay at 1/6 or below from 18 on, to 4 096, and
the dot product of two limbs reaches $1 - 5.2 \cdot 10^{-4}$ of its bound in `binary64` on
arrays of one element (a single product; 0.44 in `binary32`) and about 1/6 beyond 18. Their
bound grows as $(n - 1)\,\varepsilon$ with $\varepsilon = 3u^2/(1-4u)$ and holds for every order
of every array; the arrays that would come near it at every length are not among these. A map's step is the same kernel at every element, and its largest error over its
bound does not depend on the length. The folds of maxima are at their claim at every length:
`norm_upper_1` at 0 steps above RU(V), `norm_upper_2` at 1.

| Loop | Format | Quantity | length 0 to 1 | length 2 to 17 | length 18 to 64 | length 65 to 256 | length 257 to 1 024 | length 1 025 to 4 096 | Arrays |
|---|---|---|---|---|---|---|---|---|---|
| `add_1` | `binary32` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `add_1` | `binary64` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `add_1_entry` | `binary32` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `add_1_entry` | `binary64` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `add_2` | `binary32` | largest error / bound | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 5 000 |
| `add_2` | `binary64` | largest error / bound | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `add_2_entry` | `binary32` | largest error / bound | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 5 000 |
| `add_2_entry` | `binary64` | largest error / bound | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `axpy_1` | `binary32` | largest error / bound | 0.9999998510 | 0.9999998510 | 0.9999998510 | 0.9999998510 | 0.9999998510 | 0.9999998510 | 5 000 |
| `axpy_1` | `binary64` | largest error / bound | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `axpy_1_entry` | `binary32` | largest error / bound | 0.9999998510 | 0.9999998510 | 0.9999998510 | 0.9999998510 | 0.9999998510 | 0.9999998510 | 5 000 |
| `axpy_1_entry` | `binary64` | largest error / bound | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `axpy_2` | `binary32` | largest error / bound | 0.242697 | 0.686061 | 0.456833 | 0.595371 | 0.650532 | 0.705713 | 5 000 |
| `axpy_2` | `binary64` | largest error / bound | 0.571129 | 0.637650 | 0.631407 | 0.654740 | 0.645385 | 0.725131 | 5 000 |
| `axpy_2_1` | `binary32` | largest error / bound | 0.317578 | 0.688688 | 0.772756 | 0.756600 | 0.775365 | 0.797475 | 5 000 |
| `axpy_2_1` | `binary64` | largest error / bound | 0.396934 | 0.711763 | 0.726783 | 0.713895 | 0.782387 | 0.791096 | 5 000 |
| `axpy_2_1_entry` | `binary32` | largest error / bound | 0.345737 | 0.761722 | 0.632416 | 0.761788 | 0.755978 | 0.792749 | 5 000 |
| `axpy_2_1_entry` | `binary64` | largest error / bound | 0.396934 | 0.746690 | 0.720759 | 0.761524 | 0.782500 | 0.791690 | 5 000 |
| `axpy_2_entry` | `binary32` | largest error / bound | 0.294574 | 0.553131 | 0.608406 | 0.592782 | 0.667680 | 0.700393 | 5 000 |
| `axpy_2_entry` | `binary64` | largest error / bound | 0.571129 | 0.589349 | 0.571129 | 0.659002 | 0.651935 | 0.703585 | 5 000 |
| `bv_add_1` | `binary32` | smallest radius slack, gaps (the worst entry) | 1.87500 | 1.76756 | 1.75091 | 1.82802 | 1.67969 | 1.50000 | 5 000 |
| `bv_add_1` | `binary32` | largest error / bound | 0.858232 | 1 | 0.987117 | 0.999617 | 0.999397 | 0.999931 | 5 000 |
| `bv_add_1` | `binary32` | smallest excess over the stated value, gaps | 1.52133 | 1.27810 | 1.28201 | 1.43559 | 1.27490 | 1.26929 | 5 000 |
| `bv_add_1` | `binary64` | smallest radius slack, gaps (the worst entry) | 1.50586 | 1.53740 | 2.00000 | 1.77441 | 1.99998 | 2.00000 | 5 000 |
| `bv_add_1` | `binary64` | largest error / bound | 1 | 1 | 0.986179 | 0.993264 | 0.992542 | 0.999897 | 5 000 |
| `bv_add_1` | `binary64` | smallest excess over the stated value, gaps | 1.50586 | 1.34449 | 1.50024 | 1.59863 | 1.55845 | 1.5 | 5 000 |
| `bv_add_2` | `binary32` | smallest radius slack, gaps (the worst entry) | 1.50781 | 1.50830 | 1.59644 | 1.52977 | 1.58535 | 1.50000 | 5 000 |
| `bv_add_2` | `binary32` | largest error / bound | 0.295568 | 0.479017 | 0.416616 | 0.572274 | 0.626756 | 0.665548 | 5 000 |
| `bv_add_2` | `binary32` | smallest excess over the stated value, gaps | 1.50781 | 1.09484 | 1.29773 | 1.37268 | 1.31644 | 1.50000 | 5 000 |
| `bv_add_2` | `binary64` | smallest radius slack, gaps (the worst entry) | 1.67778 | 1.56873 | 1.50244 | 1.96094 | 1.63629 | 1.82933 | 5 000 |
| `bv_add_2` | `binary64` | largest error / bound | 0.210364 | 0.485363 | 0.450132 | 0.436082 | 0.469395 | 0.637509 | 5 000 |
| `bv_add_2` | `binary64` | smallest excess over the stated value, gaps | 1.5 | 1.35283 | 1.49144 | 1.13230 | 1.62611 | 1.50195 | 5 000 |
| `bv_conv_1` | `binary32` | largest error / bound, order sequential | 0.995471 | 0.977798 | - | 0.981387 | - | - | 5 000 |
| `bv_conv_1` | `binary64` | largest error / bound, order sequential | 0.994834 | 0.978037 | - | 0.950899 | - | - | 5 000 |
| `bv_conv_2` | `binary32` | largest error / bound, order sequential | 0.656241 | 0.440721 | - | 0.301438 | - | - | 5 000 |
| `bv_conv_2` | `binary64` | largest error / bound, order sequential | 0.650070 | 0.500000 | - | 0.360081 | - | - | 5 000 |
| `bv_mul_pow2_1` | `binary32` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_1` | `binary32` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `bv_mul_pow2_1` | `binary32` | smallest excess over the stated value, gaps | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_1` | `binary32` | smallest excess over the stated value, gaps | 0.997770 | 0.5 | 0.671875 | 0.640625 | 0.665843 | 0.5 | 5 000 |
| `bv_mul_pow2_1` | `binary64` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_1` | `binary64` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `bv_mul_pow2_1` | `binary64` | smallest excess over the stated value, gaps | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_1` | `binary64` | smallest excess over the stated value, gaps | 0.722656 | 0.543633 | 0.995117 | 0.688109 | 0.90625 | 0.625 | 5 000 |
| `bv_mul_pow2_2` | `binary32` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_2` | `binary32` | largest error / bound | 0.5 | 0.625 | 0.625 | 0.625 | 0.737793 | 0.711732 | 5 000 |
| `bv_mul_pow2_2` | `binary32` | smallest excess over the stated value, gaps | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_2` | `binary32` | smallest excess over the stated value, gaps | 0.6875 | 0.5 | 0.5625 | 0.710938 | 0.976562 | 0.561382 | 5 000 |
| `bv_mul_pow2_2` | `binary64` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_2` | `binary64` | largest error / bound | 0.5 | 0.531250 | 0.625 | 0.625 | 0.654429 | 0.736301 | 5 000 |
| `bv_mul_pow2_2` | `binary64` | smallest excess over the stated value, gaps | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_mul_pow2_2` | `binary64` | smallest excess over the stated value, gaps | 0.629585 | 0.5 | 0.998535 | 0.554688 | 0.625 | 0.986328 | 5 000 |
| `bv_neg_1` | `binary32` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_neg_1` | `binary64` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_neg_2` | `binary32` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_neg_2` | `binary32` | largest error / bound | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_neg_2` | `binary64` | smallest radius slack, gaps (the worst entry) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_neg_2` | `binary64` | largest error / bound | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `bv_scale_1` | `binary32` | smallest radius slack, gaps (the worst entry) | 1.98958 | 1.51216 | 2 | 1.70614 | 1.51347 | 1.61493 | 5 000 |
| `bv_scale_1` | `binary32` | largest error / bound | 0.977038 | 0.997328 | 0.989809 | 0.993923 | 0.999968 | 0.999983 | 5 000 |
| `bv_scale_1` | `binary32` | smallest excess over the stated value, gaps | 1.44366 | 1.11061 | 1.12356 | 1.18037 | 1.15479 | 1.16458 | 5 000 |
| `bv_scale_1` | `binary64` | smallest radius slack, gaps (the worst entry) | 1.75159 | 1.50723 | 1.62195 | 1.65115 | 1.62210 | 1.51317 | 5 000 |
| `bv_scale_1` | `binary64` | largest error / bound | 0.833133 | 0.990288 | 0.996739 | 0.997100 | 0.999150 | 0.999978 | 5 000 |
| `bv_scale_1` | `binary64` | smallest excess over the stated value, gaps | 1.51203 | 1.08853 | 1.36616 | 1.08453 | 1.32671 | 1.29626 | 5 000 |
| `bv_scale_2` | `binary32` | smallest radius slack, gaps (the worst entry) | 1.53930 | 1.50308 | 1.50315 | 1.52228 | 1.51482 | 1.46045 | 5 000 |
| `bv_scale_2` | `binary32` | largest error / bound | 0.436551 | 0.907498 | 0.967668 | 0.942901 | 0.958983 | 0.991466 | 5 000 |
| `bv_scale_2` | `binary32` | smallest excess over the stated value, gaps | 1.53930 | 1.04018 | 1.28879 | 1.31498 | 1.51479 | 1.14776 | 5 000 |
| `bv_scale_2` | `binary64` | smallest radius slack, gaps (the worst entry) | 1.64789 | 1.50561 | 1.49811 | 1.50022 | 1.51801 | 1.45172 | 5 000 |
| `bv_scale_2` | `binary64` | largest error / bound | 0.773706 | 0.921444 | 0.939018 | 0.966050 | 0.971150 | 0.995863 | 5 000 |
| `bv_scale_2` | `binary64` | smallest excess over the stated value, gaps | 1.35318 | 1.17397 | 1.25089 | 1.41426 | 1.40382 | 1.30654 | 5 000 |
| `bv_sub_1` | `binary32` | smallest radius slack, gaps (the worst entry) | 1.54889 | 1.56152 | 1.58696 | 1.76270 | 2.00000 | 1.87500 | 5 000 |
| `bv_sub_1` | `binary32` | largest error / bound | 0.821081 | 0.995037 | 0.998356 | 0.998894 | 0.999980 | 0.999977 | 5 000 |
| `bv_sub_1` | `binary32` | smallest excess over the stated value, gaps | 1.50000 | 1.00467 | 1.41524 | 1.26270 | 1.25211 | 1.45312 | 5 000 |
| `bv_sub_1` | `binary64` | smallest radius slack, gaps (the worst entry) | 2.00000 | 1.66521 | 2.00000 | 1.99943 | 1.72125 | 1.50863 | 5 000 |
| `bv_sub_1` | `binary64` | largest error / bound | 0.788455 | 0.987437 | 0.976320 | 0.987413 | 0.995171 | 0.998599 | 5 000 |
| `bv_sub_1` | `binary64` | smallest excess over the stated value, gaps | 1.57823 | 1.50399 | 1.40240 | 1.53295 | 1.54438 | 1.5 | 5 000 |
| `bv_sub_2` | `binary32` | smallest radius slack, gaps (the worst entry) | 1.5 | 1.50000 | 1.75000 | 1.52490 | 1.55544 | 1.60113 | 5 000 |
| `bv_sub_2` | `binary32` | largest error / bound | 0.230133 | 0.476220 | 0.405817 | 0.434204 | 0.585418 | 0.657483 | 5 000 |
| `bv_sub_2` | `binary32` | smallest excess over the stated value, gaps | 1.50000 | 1.09695 | 1.19569 | 1.52478 | 1.55544 | 1.49574 | 5 000 |
| `bv_sub_2` | `binary64` | smallest radius slack, gaps (the worst entry) | 1.99990 | 1.50000 | 1.65868 | 1.89844 | 2.00000 | 1.50000 | 5 000 |
| `bv_sub_2` | `binary64` | largest error / bound | 0.161025 | 0.362774 | 0.315214 | 0.353485 | 0.474816 | 0.491951 | 5 000 |
| `bv_sub_2` | `binary64` | smallest excess over the stated value, gaps | 1.53012 | 1.50000 | 1.50893 | 1.52772 | 1.59341 | 1.50000 | 5 000 |
| `conv_1` | `binary32` | largest error / bound, order sequential | 0.9999999404 | 0.997443 | - | - | - | - | 5 000 |
| `conv_1` | `binary64` | largest error / bound, order sequential | 1.00000 | 0.999999 | - | - | - | - | 5 000 |
| `conv_1_entry` | `binary32` | largest error / bound, order sequential | 0.9999999404 | 0.995850 | - | - | - | - | 5 000 |
| `conv_1_entry` | `binary64` | largest error / bound, order sequential | 1.00000 | 0.995621 | - | - | - | - | 5 000 |
| `conv_2` | `binary32` | largest error / bound, order sequential | 0.934478 | 0.653598 | - | - | - | - | 5 000 |
| `conv_2` | `binary64` | largest error / bound, order sequential | 0.880418 | 0.999476 | - | - | - | - | 5 000 |
| `dot_1` | `binary32` | largest error / bound, order lanes | 0.990170 | 0.941175 | 0.982138 | 0.995394 | 0.998152 | 0.999400 | 5 000 |
| `dot_1` | `binary32` | largest error / bound, order sequential | 0.873734 | 0.941175 | 0.984122 | 0.995264 | 0.998919 | 0.999401 | 5 000 |
| `dot_1` | `binary64` | largest error / bound, order lanes | 0.901409 | 0.941176 | 0.983871 | 0.995935 | 0.998252 | 0.999756 | 5 000 |
| `dot_1` | `binary64` | largest error / bound, order sequential | 0.864093 | 0.941176 | 0.978723 | 0.995595 | 0.998889 | 0.999756 | 5 000 |
| `dot_1_entry` | `binary32` | largest error / bound, order lanes | 0.895220 | 0.941175 | 0.983328 | 0.995476 | 0.998844 | 0.999402 | 5 000 |
| `dot_1_entry` | `binary32` | largest error / bound, order sequential | 0.932746 | 0.941175 | 0.983046 | 0.995330 | 0.998146 | 0.999402 | 5 000 |
| `dot_1_entry` | `binary64` | largest error / bound, order lanes | 0.966557 | 0.941176 | 0.983333 | 0.995935 | 0.998862 | 0.999756 | 5 000 |
| `dot_1_entry` | `binary64` | largest error / bound, order sequential | 0.834193 | 0.941176 | 0.980769 | 0.996047 | 0.998918 | 0.999756 | 5 000 |
| `dot_2` | `binary32` | largest error / bound, order lanes | 0.444377 | 0.205487 | 0.162069 | 0.165441 | 0.166443 | 0.166612 | 5 000 |
| `dot_2` | `binary32` | largest error / bound, order sequential | 0.209168 | 0.277198 | 0.161972 | 0.165734 | 0.166448 | 0.166612 | 5 000 |
| `dot_2` | `binary64` | largest error / bound, order lanes | 0.999476 | 0.571129 | 0.158824 | 0.165474 | 0.166363 | 0.166612 | 5 000 |
| `dot_2` | `binary64` | largest error / bound, order sequential | 0.999476 | 0.571129 | 0.156716 | 0.165306 | 0.166398 | 0.166612 | 5 000 |
| `mul_pow2_map_1` | `binary32` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `mul_pow2_map_1` | `binary64` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `mul_pow2_map_2` | `binary32` | largest error / bound | 0.485462 | 0.625000 | 0.576614 | 0.750000 | 0.750000 | 0.750000 | 5 000 |
| `mul_pow2_map_2` | `binary64` | largest error / bound | 0.446551 | 0.750000 | 0.750000 | 0.550790 | 0.750000 | 0.750000 | 5 000 |
| `norm_upper_1` | `binary32` | largest steps above RU(V) (claim 0) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `norm_upper_1` | `binary64` | largest steps above RU(V) (claim 0) | 0 | 0 | 0 | 0 | 0 | 0 | 5 000 |
| `norm_upper_2` | `binary32` | largest steps above RU(V) (claim 1) | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `norm_upper_2` | `binary64` | largest steps above RU(V) (claim 1) | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `scale_1` | `binary32` | largest error / bound | 0.9999998808 | 0.9999998808 | 0.9999998808 | 0.9999998808 | 0.9999998808 | 0.9999998808 | 5 000 |
| `scale_1` | `binary64` | largest error / bound | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `scale_2` | `binary32` | largest error / bound | 0.812772 | 0.959923 | 0.866479 | 0.959951 | 0.987724 | 0.991485 | 5 000 |
| `scale_2` | `binary64` | largest error / bound | 0.992336 | 0.992336 | 0.992336 | 0.992336 | 0.993148 | 0.999554 | 5 000 |
| `scale_2_entry` | `binary32` | largest error / bound | 0.424196 | 0.942771 | 0.952273 | 0.965312 | 0.990311 | 0.998984 | 5 000 |
| `scale_2_entry` | `binary64` | largest error / bound | 0.992336 | 0.992336 | 0.992336 | 0.992336 | 0.992336 | 0.999526 | 5 000 |
| `sub_1` | `binary32` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `sub_1` | `binary64` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `sub_1_entry` | `binary32` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `sub_1_entry` | `binary64` | largest error / bound | 1 | 1 | 1 | 1 | 1 | 1 | 5 000 |
| `sub_2` | `binary32` | largest error / bound | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 5 000 |
| `sub_2` | `binary64` | largest error / bound | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `sub_2_entry` | `binary32` | largest error / bound | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 0.9999995430 | 5 000 |
| `sub_2_entry` | `binary64` | largest error / bound | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `sum_1` | `binary32` | largest error / bound, order lanes | 0 | 0.9999999404 | 0.999998 | 0.999991 | 0.999966 | 0.999887 | 5 000 |
| `sum_1` | `binary32` | largest error / bound, order sequential | 0 | 0.9999999404 | 0.999998 | 0.999992 | 0.999973 | 0.999888 | 5 000 |
| `sum_1` | `binary64` | largest error / bound, order lanes | 0 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `sum_1` | `binary64` | largest error / bound, order sequential | 0 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `sum_1_entry` | `binary32` | largest error / bound, order lanes | 0 | 0.9999999404 | 0.999999 | 0.999993 | 0.999974 | 0.999907 | 5 000 |
| `sum_1_entry` | `binary32` | largest error / bound, order sequential | 0 | 0.9999999404 | 0.999999 | 0.999994 | 0.999977 | 0.999825 | 5 000 |
| `sum_1_entry` | `binary64` | largest error / bound, order lanes | 0 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `sum_1_entry` | `binary64` | largest error / bound, order sequential | 0 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 5 000 |
| `sum_2` | `binary32` | largest error / bound, order lanes | 0 | 0.333333 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_2` | `binary32` | largest error / bound, order sequential | 0 | 0.333333 | 0.166667 | 0.166667 | 0.166667 | 0.137584 | 5 000 |
| `sum_2` | `binary64` | largest error / bound, order lanes | 0 | 0.333333 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_2` | `binary64` | largest error / bound, order sequential | 0 | 0.333333 | 0.134506 | 0.112932 | 0.160761 | 0.166667 | 5 000 |
| `sum_2_entry` | `binary32` | largest error / bound, order lanes | 0 | 0.333333 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_2_entry` | `binary32` | largest error / bound, order sequential | 0 | 0.333333 | 0.166667 | 0.114013 | 0.166667 | 0.116085 | 5 000 |
| `sum_2_entry` | `binary64` | largest error / bound, order lanes | 0 | 0.333333 | 0.126071 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_2_entry` | `binary64` | largest error / bound, order sequential | 0 | 0.296236 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_fast_2` | `binary32` | largest error / bound, order lanes | 0 | 0.316673 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_fast_2` | `binary32` | largest error / bound, order sequential | 0 | 0.200609 | 0.166667 | 0.166667 | 0.166667 | 0.151879 | 5 000 |
| `sum_fast_2` | `binary64` | largest error / bound, order lanes | 0 | 0.248896 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_fast_2` | `binary64` | largest error / bound, order sequential | 0 | 0.353038 | 0.166667 | 0.110134 | 0.166667 | 0.166667 | 5 000 |
| `sum_fast_2_entry` | `binary32` | largest error / bound, order lanes | 0 | 0.188884 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_fast_2_entry` | `binary32` | largest error / bound, order sequential | 0 | 0.166667 | 0.166667 | 0.137266 | 0.166667 | 0.166667 | 5 000 |
| `sum_fast_2_entry` | `binary64` | largest error / bound, order lanes | 0 | 0.260314 | 0.166667 | 0.166667 | 0.166667 | 0.166667 | 5 000 |
| `sum_fast_2_entry` | `binary64` | largest error / bound, order sequential | 0 | 0.192299 | 0.166667 | 0.166667 | 0.157452 | 0.163733 | 5 000 |

## The exhaustive tier on emulated formats

The kernels and loops printed for the emulated limb type (`tests/emulated/`,
[Testing](../testing.md#the-emulated-formats)), the C++ of the scalar kernels on an integer
arithmetic of the format, through `kairn-emulated-runner` of the GCC 13 build, judged by the
oracle in the formats of the statements of precision 8 to 11 with the smallest exponent range:
the whole of the plan's emulated part (`brute.py run --part emulated`), on the Linux machine, at
`5f597fb`, seed `m2r1-emulated-linux`, 16 busy processes beside the main run, in 11 298 seconds
(3.1 hours), 2 119 pipelines. The full tier of ctest runs the same kernels in `fp:8:-14:1` only,
on fewer cases.

**Every one of the 1 120 entries is complete and passed the guards; no line failed and none was
invalid.** 1 247 784 868 lines, 1 216 815 154 of them judged: 125 enumerations of every operand
(859 447 368 indices, 840 524 868 lines: those of `fast_two_sum` and `fast_two_sum_entry` keep
the pairs of their precondition), at precision 8 the 80 kernels of one or two limbs and at 9, 10
and 11 the 15 of one limb; and 995 random series (407 260 000 cases, among them 3 760 000 arrays
of up to 256 elements of the 47 loops in every order). The 2 768 876 suspicious non-finite
results are of `two_prod_dekker` (2 755 384) and `split` (13 492), which are exempt, as in every
tier; the smallest share of judged lines is 0.52, `two_prod_dekker` in `fp:9:-16:1`. This run
replaces, as the stored evidence of the tier, the earlier whole run on the tree at `37b66b8`
(1 172 199 035 lines, no failure), which had 52 entries fewer. Stored in
[`results/milestone2/brute/emulated/linux-x86-64.json`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/brute/emulated);
`brute.py report` prints its tables:

| Precision | Mode | Entries | Complete, guards passed | Indices or cases covered | Lines | Judged | Failed | Invalid | Seconds of pipelines |
|---|---|---|---|---|---|---|---|---|---|
| 8 | every operand | 80 | 80 | 857 979 889 | 839 057 389 | 818 898 011 | 0 | 0 | 50 761 |
| 8 | random | 200 | 200 | 77 440 000 | 77 440 000 | 75 269 399 | 0 | 0 | 8 409 |
| 9 | every operand | 15 | 15 | 183 325 | 183 325 | 180 733 | 0 | 0 | 17 |
| 9 | random | 265 | 265 | 109 940 000 | 109 940 000 | 107 016 375 | 0 | 0 | 10 040 |
| 10 | every operand | 15 | 15 | 403 485 | 403 485 | 398 303 | 0 | 0 | 28 |
| 10 | random | 265 | 265 | 109 940 000 | 109 940 000 | 107 082 212 | 0 | 0 | 10 324 |
| 11 | every operand | 15 | 15 | 880 669 | 880 669 | 868 317 | 0 | 0 | 51 |
| 11 | random | 265 | 265 | 109 940 000 | 109 940 000 | 107 101 804 | 0 | 0 | 10 748 |
| all | | 1 120 | 1 120 | 1 266 707 368 | 1 247 784 868 | 1 216 815 154 | 0 | 0 | 90 379 |

## The adversarial search

After the runs, `python3 oracle/kairn-oracle search all binary64,binary32`
([Testing](../testing.md#the-adversarial-search)) on the tree of the
[supplementary run](#supplementary-run-the-close-of-rule-r3) (`8ee5ed9`, whose kernels are those
of `5f597fb` but the twelve of that section): every kernel with an `error`, `upper`, `encloses`
or `extends` entry, 109 kernels and 218 kernel and format pairs, 20 000 cases each, seed 0, on
the Mac (`--fail-on-suspicious --suspicious-ok split,two_prod_dekker`). As in Milestone 1:

- **from the strata alone** (`--no-default-seeds --no-literature`), through the generator's
  interpreter, 4 processes: 4 360 000 cases in 5 110 seconds;
- **with every seed**: the attaining lines of the stored brute-force summaries, the regression
  cases, the cases of the literature and those of the strata. The search reads the summaries
  under `results/*/brute/` and `results/*/brute/supplementary/`, a pattern and not a fixed path,
  so that it read the three summaries of this milestone and its supplementary files beside those
  of Milestone 1. Through the scalar runner of the Mac's Apple clang build at `8ee5ed9`
  (`--runner builds/clang/tests/kairn-gen-runner`, the build's flags), 6 processes: 4 360 000
  cases in 74 seconds.
  - **with every seed again, through the generator's interpreter**: the same command without
  `--runner`, 6 processes, 4 360 000 cases in 3 229 seconds. It ended with the same best value
  and the same best line as the run through the compiled runner for every one of the 378
  quantities of the 218 pairs (the table gives them once).

**No claim was violated**, no line failed and none was suspicious but those of the two kernels
exempt in every tier, in any run
([`results/milestone2/search/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone2/search),
the best line of every quantity with its value).

The search takes 77 kernels of this milestone (of the 190 new or changed and the four that the
close of rule R3 added); the claims it climbs of six of them are all exact (`bv_center_2`,
`bv_center_entry_2`, `fast_two_sum_entry`, `split`, `two_sum_entry`, `two_sum_ord`: an error
of zero, which every case of both searches met). The table compares, for the other 71, the
extreme of each quantity in the brute-force runs above (the compiled runners; recomputed exactly from the
attaining lines of every machine, which the summaries keep to ten digits) with that of the two
searches: bold where the search came closer to the claim, ↓ where it stayed farther. Exact claims
($c = 0$, $t = 0$) are left out, as in Milestone 1. Over the 234 quantities (117 per format),
the search with every seed came closer than the brute-force runs on 135, as close on 99 and
farther on none; from the strata alone it came closer on 109, as close on 92 and farther on 33.
The two searches do not order: from the strata alone the search came closer than with every seed
on 40 quantities (of 22 kernels), with every seed on 89; one or the other came closer than the
brute-force runs on 143.

| Kernel | Quantity (claim) | `binary64` brute force | `binary64` from the strata | `binary64` with every seed | `binary32` brute force | `binary32` from the strata | `binary32` with every seed |
|---|---|---|---|---|---|---|---|
| `acc_add_1` | observed c (`error(t) form R, c=1/(1+u), k=1, t=0`) | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `acc_add_1` | error / bound (`error(t) form R, c=1/(1+u), k=1, t=0`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `acc_add_2` | observed c (`error(t) form R, c=3/(1-4*u), k=2, t=0`) | 1.6981 | **2.5000** | **2.5000** | 2.0000 | **2.5000** | **3.0000** |
| `acc_add_2` | error / bound (`error(t) form R, c=3/(1-4*u), k=2, t=0`) | 0.56602 | **0.83333** | **0.83333** | 0.66667 | **0.83333** | **1 − 5.8e-07** |
| `acc_merge_1` | observed c (`error(t) form R, c=1/(1+u), k=1, t=0`) | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `acc_merge_1` | error / bound (`error(t) form R, c=1/(1+u), k=1, t=0`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `acc_merge_2` | observed c (`error(t) form R, c=3/(1-4*u), k=2, t=0`) | 2.0000 | **2.4776** | **3.0000** | 1.8893 | **2.5000** | **2.0000** |
| `acc_merge_2` | error / bound (`error(t) form R, c=3/(1-4*u), k=2, t=0`) | 0.66667 | **0.82586** | **1 − 8.1e-16** | 0.62977 | **0.83333** | **0.66666** |
| `acc_mul_2` | observed c (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 2.7718 | **3.9055** | **3.6075** | 2.9978 | **3.7303** | **3.7344** |
| `acc_mul_2` | error / bound (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 0.39597 | **0.55792** | **0.51535** | 0.60793 | **0.70029** | **0.74556** |
| `acc_mul_entry_2` | observed c (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 2.8670 | **4.7321** | **3.9790** | 2.8904 | **3.7138** | **4.1059** |
| `acc_mul_entry_2` | error / bound (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 0.47893 | **0.67601** | **0.72651** | 0.50000 | **0.74960** | **0.74179** |
| `acc_radius_1` | excess over the stated value, gaps (`upper(r) >= g*(1+u)^2*(1+m*u+2*m^2*u^2)*(a+m*eta/2)+t if ok`) | 2.9750 | **2.4473** | **2.4019** | 2.9541 | **2.3737** | **2.3710** |
| `acc_radius_2` | excess over the stated value, gaps (`upper(r) >= g*(1+u)^2*(1+m*u+2*m^2*u^2)*(a+m*eta/2)+t if ok`) | 2.8530 | **2.4927** | **2.4386** | 2.9068 | **2.4694** | **2.3948** |
| `add_ball_2_2` | slack, gaps (`encloses(z, d) x+y over `) | 2.2518e+15 | **10.5** | **1.1259e+15** | 4.1943e+6 | **2.0972e+6** | **2.0972e+6** |
| `add_ball_2_2` | observed c (`error(z) form R, c=3/(1-4*u), k=2, t=0`) | 2.0000 | **3.0000** | **2.5000** | 2.0000 | **2.5000** | **2.5000** |
| `add_ball_2_2` | error / bound (`error(z) form R, c=3/(1-4*u), k=2, t=0`) | 0.66667 | **1 − 8.5e-16** | **0.83333** | 0.66667 | **0.83333** | **0.83333** |
| `add_entry_step_1` | observed c (`error(z) form R, c=1/(1+u), k=1, t=0`) | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `add_entry_step_1` | error / bound (`error(z) form R, c=1/(1+u), k=1, t=0`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `add_entry_step_2` | observed c (`error(z) form R, c=3/(1-4*u), k=2, t=0`) | 2.0000 | **2.5000** | **3.0000** | 2.0294 | **3.0000** | **3.0000** |
| `add_entry_step_2` | error / bound (`error(z) form R, c=3/(1-4*u), k=2, t=0`) | 0.66667 | **0.83333** | **1 − 8.1e-16** | 0.67646 | **1 − 4.4e-07** | **1 − 4.4e-07** |
| `axpy_entry_step_1` | observed c (`error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`) | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 2.0000 |
| `axpy_entry_step_1` | error / bound (`error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`) | 1 − 2.8e-16 | 1.000000000 ↓ | **1.000000000** | 1 − 1.5e-07 | **0.999999850988** | **0.999999850988** |
| `axpy_entry_step_2` | observed c (`error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 3.9979 | **4.4997** | **5.4127** | 3.0574 | **3.9420** | **4.5968** |
| `axpy_entry_step_2` | error / bound (`error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 0.71557 | 0.64281 ↓ | **0.77324** | 0.70075 | **0.72946** | **0.73914** |
| `axpy_entry_step_2_1` | observed c (`error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`) | 1.9847 | **2.4955** | **2.4913** | 2.2608 | 2.0000 ↓ | **2.4920** |
| `axpy_entry_step_2_1` | error / bound (`error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`) | 0.80000 | 0.79536 ↓ | **0.800000000000** | 0.80000 | **0.799999856949** | **0.799999856949** |
| `axpy_step_1` | observed c (`error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`) | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 2.0000 |
| `axpy_step_1` | error / bound (`error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`) | 1 − 2.8e-16 | 1.000000000 ↓ | **1.000000000** | 1 − 1.5e-07 | 0.999999850988 ↓ | **0.999999850988** |
| `axpy_step_2` | observed c (`error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 3.9979 | **4.4762** | **4.5000** | 2.8612 | **4.0759** | **4.5006** |
| `axpy_step_2` | error / bound (`error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 0.63150 | **0.73254** | **0.74100** | 0.70085 | **0.73178** | **0.71665** |
| `axpy_step_2_1` | observed c (`error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`) | 1.9847 | **2.4912** | **2.4793** | 1.4517 | **2.0654** | **2.4657** |
| `axpy_step_2_1` | error / bound (`error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`) | 0.80000 | 0.49824 ↓ | **0.800000000000** | 0.80000 | 0.79522 ↓ | **0.799999833108** |
| `ball_add_1_full` | slack, gaps (`encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx+cy)+rx+ry\| <= 2^(qmax+p-2)`) | 1.25 | **1.1250** | **1** | 1.25 | **1.1250** | **1** |
| `ball_add_2_full` | slack, gaps (`encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx+cy)+rx+ry\| <= 2^(qmax+p-2)`) | 1.3047 | **1.1602** | **1.1563** | 1.2503 | **1.1094** | **1.1094** |
| `ball_lower_as_2` | observed c (`error(l) form A, c=5, k=1, t=3`) | 4.0000 | **4.00000000000** | **4.00000000000** | 4.0000 | **4.00000000000** | **4.00000000000** |
| `ball_lower_as_2` | error / bound (`error(l) form A, c=5, k=1, t=3`) | 0.80000 | **0.800000000000** | **0.800000000000** | 0.80000 | **0.800000000000** | **0.800000000000** |
| `ball_mul_1_full` | slack, gaps (`encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|(abs(cx)+rx)*(abs(cy)+ry)\| <= 2^(qmax+p-4)`) | 1.6753 | **1.5000** | **1.5012** | 1.7739 | **1.5080** | **1.5000** |
| `ball_mul_2_full` | slack, gaps (`encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|(abs(cx)+rx)*(abs(cy)+ry)\| <= 2^(qmax+p-2)`) | 2.5676 | **2.4482** | **2.4386** | 2.7500 | **2.5000** | **2.4500** |
| `ball_mul_pow2_1` | slack, gaps (`encloses(cz, rz) x*c over x=[cx +- rx], exactly the set when (cx*c = 0 or \|cx*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `ball_mul_pow2_1_full` | slack, gaps (`encloses(cw, rw) x*c over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*c\| <= 2^(qmax+p-2), exactly the set when (cx*c = 0 or \|cx*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `ball_mul_pow2_2` | slack, gaps (`encloses(cz, rz) x*c over x=[cx +- rx], exactly the set when (cx[0]*c = 0 or \|cx[0]*c\| > eta/(2*u)) and (cx[1]*c = 0 or \|cx[1]*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `ball_mul_pow2_2_full` | slack, gaps (`encloses(cw, rw) x*c over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*c\| <= 2^(qmax+p-2), exactly the set when (cx[0]*c = 0 or \|cx[0]*c\| > eta/(2*u)) and (cx[1]*c = 0 or \|cx[1]*c\| > eta/(2*u)) and (rx*c = 0 or \|rx*c\| > eta/(2*u))`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `ball_narrow_2_1` | slack, gaps (`encloses(cz, rz) x over x=[c +- r], B1-B4, finite when \|abs(c)+r\| <= 2^(qmax+p-2)`) | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| `ball_scale_1_full` | slack, gaps (`encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)`) | 1 + 2.2e-16 | 1 + 2.2e-16 | 1 + 2.2e-16 | 1 + 1.2e-07 | 1 + 1.2e-07 | 1 + 1.2e-07 |
| `ball_scale_2_full` | slack, gaps (`encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)`) | 1.3750 | 1.5000 ↓ | **1.25** | 1.4375 | **1.2512** | **1.2502** |
| `ball_scale_2_full_entry` | slack, gaps (`encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when \|(abs(cx)+rx)*a\| <= 2^(qmax+p-2)`) | 1.4101 | **1.3750** | **1.2517** | 1.4796 | **1.3750** | **1.3750** |
| `ball_sub_1_full` | slack, gaps (`encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx-cy)+rx+ry\| <= 2^(qmax+p-2)`) | 1.25 | **1.1250** | **1** | 1 | 1.1250 ↓ | 1 |
| `ball_sub_2_full` | slack, gaps (`encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when \|abs(cx-cy)+rx+ry\| <= 2^(qmax+p-2)`) | 1.3605 | **1.1602** | **1.1563** | 1.2627 | **1.1719** | **1.1094** |
| `ball_upper_as_2` | observed c (`error(h) form A, c=5, k=1, t=3`) | 4.0000 | **4.00000000000** | **4.00000000000** | 4.0000 | **4.00000000000** | **4.00000000000** |
| `ball_upper_as_2` | error / bound (`error(h) form A, c=5, k=1, t=3`) | 0.80000 | **0.800000000000** | **0.800000000000** | 0.80000 | **0.800000000000** | **0.800000000000** |
| `bound_dot_1` | excess over the stated value, gaps (`upper(g) >= m*unit(mul_1_1)/(1-m*unit(mul_1_1)) if ok`) | 2.8439 | **2.8438** | **2.8438** | 2.8438 | **2.84375008708** | **2.84375008708** |
| `bound_dot_1` | excess over the stated value, gaps (`upper(t) >= m*tiny(mul_1_1)*(1+g) if ok`) | 4.5036e+15 | **4.50359962737e+15** | **4.50359962737e+15** | 8.3886e+6 | **8388608.50000** | **8388608.50000** |
| `bound_dot_2` | excess over the stated value, gaps (`upper(g) >= m*unit(mul_2_2)/(1-m*unit(mul_2_2)) if ok`) | 2.8051 | **2.2500** | **2.2500** | 2.8049 | **2.2500** | **2.2500** |
| `bound_dot_2` | excess over the stated value, gaps (`upper(t) >= m*tiny(mul_2_2)*(1+g) if ok`) | 4.5036e+15 | **4.50359962737e+15** | **4.50359962737e+15** | 8.3886e+6 | **8388607.50000** | **8388607.50000** |
| `bound_sum_1` | excess over the stated value, gaps (`upper(g) >= m*unit(add_1_1)/(1-m*unit(add_1_1)) if ok`) | 2.8456 | **2.8438** | **2.8438** | 2.8439 | **2.8438** | **2.8438** |
| `bound_sum_2` | excess over the stated value, gaps (`upper(g) >= m*unit(add_2_2)/(1-m*unit(add_2_2)) if ok`) | 1.7656 | **1.7622** | **1.7622** | 1.7624 | **1.7622** | **1.7622** |
| `bv_add_radius_1` | excess over the stated value, gaps (`upper(rz) >= rx+ry+m*unit(add_1_1)/(1-unit(add_1_1))`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `bv_add_radius_2` | excess over the stated value, gaps (`upper(rz) >= rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)`) | 1.0532 | **1 + 2.0e-13** | **1 + 2.4e-07** | 1.0032 | **1 + 8.9e-08** | **1 + 8.0e-07** |
| `bv_mul_pow2_radius` | excess over the stated value, gaps (`upper(rz) >= rx*c+eta unless ex`) | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| `bv_mul_pow2_radius` | excess over the stated value, gaps (`upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or \|rx*c\| > eta/(2*u))`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `bv_mul_pow2_step_1` | observed c (`error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or \|x*c\| > eta/(2*u)), exact_flag e`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `bv_mul_pow2_step_1` | error / bound (`error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or \|x*c\| > eta/(2*u)), exact_flag e`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `bv_mul_pow2_step_2` | observed c (`error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or \|x[0]*c\| > eta/(2*u)) and (x[1]*c = 0 or \|x[1]*c\| > eta/(2*u)), exact_flag e`) | 1.0163e-18 | **5.5511e-17** | **5.5511e-17** | 1.7205e-8 | **2.9802e-8** | **2.9802e-8** |
| `bv_mul_pow2_step_2` | error / bound (`error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or \|x[0]*c\| > eta/(2*u)) and (x[1]*c = 0 or \|x[1]*c\| > eta/(2*u)), exact_flag e`) | 0.66411 | **0.75000** | **0.75000** | 0.71638 | **0.75000** | **0.75000** |
| `bv_scale_radius_1` | excess over the stated value, gaps (`upper(rz) >= abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))`) | 1.0529 | **1 − 4.9e-209** | **1.0004** | 1.0012 | **1 + 6.0e-08** | **1 − 2.6e-23** |
| `bv_scale_radius_2` | excess over the stated value, gaps (`upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))`) | 1.0684 | **1 + 5.6e-17** | **1 + 9.2e-08** | 1.0086 | **1.000010878** | **1.0001** |
| `bv_scale_radius_entry_2` | excess over the stated value, gaps (`upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))`) | 1.0098 | **1 + 1.7e-16** | **1 + 6.3e-11** | 1.0001 | **1.000001997** | **1.000007659** |
| `bv_scale_step_2` | observed c (`error(z) form R, c=2, k=2, t=1`) | 1.9643 | 1.6595 ↓ | **1.9654** | 1.9988 | 1.8889 ↓ | **1.99878575654** |
| `bv_scale_step_2` | error / bound (`error(z) form R, c=2, k=2, t=1`) | 1 − 2.8e-16 | 0.99923 ↓ | **1 − 1.7e-16** | 1 − 1.2e-07 | 0.99167 ↓ | **1 − 8.9e-08** |
| `conv_radius` | excess over the stated value, gaps (`upper(rz) >= m*((1+u)*ma*ry+(1+u)*mb*rx+rx*ry)+g*m*(1+u)^2*ma*mb+t`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `dot_entry_step_2` | observed c (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 3.0119 | **3.9812** | **3.9006** | 3.3068 | 2.9968 ↓ | **3.7808** |
| `dot_entry_step_2` | error / bound (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 0.69992 | **0.74851** | **0.74631** | 0.72209 | 0.71279 ↓ | **0.73651** |
| `dot_step_2` | observed c (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 2.8663 | **3.8703** | **4.4548** | 2.1745 | **4.7476** | **4.7684** |
| `dot_step_2` | error / bound (`error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`) | 0.69077 | **0.73329** | **0.74641** | 0.67277 | **0.72766** | **0.74818** |
| `mul_1_1` | observed c (`error(p) form R, c=1/(1+u), k=1, t=1/2`) | 1 − 3.3e-16 | 1 − 3.3e-16 | 1 − 3.3e-16 | 1 − 1.8e-07 | 1 − 1.8e-07 | 1 − 1.8e-07 |
| `mul_1_1` | error / bound (`error(p) form R, c=1/(1+u), k=1, t=1/2`) | 1 − 1.1e-16 | 1 − 2.2e-16 ↓ | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `mul_2_1_entry` | observed c (`error(z) form R, c=2, k=2, t=1`) | 1.9487 | **1.9999** | **1.9922** | 1.9927 | 1.8833 ↓ | **1.99266795051** |
| `mul_2_1_entry` | error / bound (`error(z) form R, c=2, k=2, t=1`) | 1 − 2.3e-10 | 0.99995 ↓ | **1 − 1.7e-16** | 1 − 1.2e-07 | 0.99263 ↓ | **1 − 8.9e-08** |
| `mul_2_1_full_entry` | observed c (`F2, core mul_2_1_entry: error(z) form R, c=2, k=2, t=1`) | 1.8611 | 1.8525 ↓ | **1.9550** | 1.9072 | 1.8551 ↓ | **1.9079** |
| `mul_2_1_full_entry` | error / bound (`F2, core mul_2_1_entry: error(z) form R, c=2, k=2, t=1`) | 0.99167 | **1 − 1.7e-16** | **0.99941** | 0.99102 | **0.99999** | **1 − 8.9e-08** |
| `mul_ball_2_2` | slack, gaps (`encloses(z, d) x*y over `) | 2.1267e+15 | **5.6295e+14** | **9.2345e+14** | 2.5720e+6 | **1.0531e+6** | **1.3151e+6** |
| `mul_ball_2_2` | observed c (`error(z) form R, c=4, k=2, t=3/2`) | 2.4826 | **3.5000** | **3.2346** | 2.8000 | **3.4981** | **3.3844** |
| `mul_ball_2_2` | error / bound (`error(z) form R, c=4, k=2, t=3/2`) | 0.94971 | **0.99117** | **0.99306** | 0.94207 | 0.87452 ↓ | **0.99255** |
| `mul_pow2_2` | observed c (`error(z) form R, c=0, k=2, t=1`) | 4.7989e-17 | **5.5511e-17** | **5.5511e-17** | 2.9802e-8 | 2.9802e-8 | 2.9802e-8 |
| `mul_pow2_2` | error / bound (`error(z) form R, c=0, k=2, t=1`) | 0.75000 | 0.75000 | 0.75000 | 0.75000 | 0.75000 | 0.75000 |
| `mul_pow2_2_full` | observed c (`F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1`) | 4.5704e-17 | **5.5511e-17** | **5.5511e-17** | 2.9802e-8 | **2.98023223877e-8** | **2.98023223877e-8** |
| `mul_pow2_2_full` | error / bound (`F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1`) | 0.74778 | 0.74219 ↓ | **0.75000** | 0.75000 | 0.75000 | 0.75000 |
| `mul_pow2_step_1` | observed c (`error(z) form R, c=0, k=1, t=1/2`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `mul_pow2_step_1` | error / bound (`error(z) form R, c=0, k=1, t=1/2`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `mul_pow2_step_2` | observed c (`error(z) form R, c=0, k=2, t=1`) | 4.1491e-17 | **5.5511e-17** | **5.5511e-17** | 2.9802e-8 | **2.98023223877e-8** | **2.98023223877e-8** |
| `mul_pow2_step_2` | error / bound (`error(z) form R, c=0, k=2, t=1`) | 0.72936 | **0.75000** | **0.75000** | 0.75000 | 0.75000 | 0.75000 |
| `radd` | excess, gaps (`upper(r) gaps=3/2`) | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| `radd_entry` | excess, gaps (`upper(r) gaps=3/2`) | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| `rmul` | excess, gaps (`upper(r) gaps=3/2`) | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| `scale_entry_step_2` | observed c (`error(z) form R, c=2, k=2, t=1`) | 1.9359 | 1.8951 ↓ | **1.9956** | 1.9816 | **1.9988** | **1.98162335800** |
| `scale_entry_step_2` | error / bound (`error(z) form R, c=2, k=2, t=1`) | 1 − 2.8e-16 | 0.99667 ↓ | **1 − 1.7e-16** | 1 − 1.5e-07 | 0.99939 ↓ | **1 − 8.9e-08** |
| `scale_step_1` | observed c (`error(z) form R, c=1/(1+u), k=1, t=1/2`) | 1 − 3.3e-16 | 1 − 3.3e-16 | 1 − 3.3e-16 | 1 − 1.8e-07 | 1 − 1.8e-07 | 1 − 1.8e-07 |
| `scale_step_1` | error / bound (`error(z) form R, c=1/(1+u), k=1, t=1/2`) | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `scale_step_2` | observed c (`error(z) form R, c=2, k=2, t=1`) | 1.9768 | **1.9813** | **1.9956** | 1.9116 | 1.7778 ↓ | **1.9714** |
| `scale_step_2` | error / bound (`error(z) form R, c=2, k=2, t=1`) | 1 − 2.2e-16 | 0.99143 ↓ | **1 − 1.7e-16** | 1 − 1.8e-07 | **1 − 8.9e-08** | **1 − 8.9e-08** |
| `sub_1_1` | observed c (`error(s) form R, c=1/(1+u), k=1, t=0`) | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `sub_1_1` | error / bound (`error(s) form R, c=1/(1+u), k=1, t=0`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_entry_step_1` | observed c (`error(z) form R, c=1/(1+u), k=1, t=0`) | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `sub_entry_step_1` | error / bound (`error(z) form R, c=1/(1+u), k=1, t=0`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_entry_step_2` | observed c (`error(z) form R, c=3/(1-4*u), k=2, t=0`) | 1.8617 | 1.5000 ↓ | **3.0000** | 2.3628 | **2.5000** | **3.0000** |
| `sub_entry_step_2` | error / bound (`error(z) form R, c=3/(1-4*u), k=2, t=0`) | 0.62058 | 0.50000 ↓ | **1 − 8.1e-16** | 0.78762 | **0.83333** | **1 − 4.4e-07** |
| `sum_entry_step_1` | observed c (`error(t) form R, c=1/(1+u), k=1, t=0`) | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 1.1e-16 | 1 − 6.0e-08 | 1 − 6.0e-08 | 1 − 6.0e-08 |
| `sum_entry_step_1` | error / bound (`error(t) form R, c=1/(1+u), k=1, t=0`) | 1 | 1 | 1 | 1 | 1 | 1 |
| `sum_entry_step_2` | observed c (`error(t) form R, c=3/(1-4*u), k=2, t=0`) | 1.9836 | **3.0000** | **2.0000** | 2.0000 | **1.99999976158** | **2.5000** |
| `sum_entry_step_2` | error / bound (`error(t) form R, c=3/(1-4*u), k=2, t=0`) | 0.66119 | **1 − 8.1e-16** | **0.66667** | 0.66667 | **0.666666428248** | **0.83333** |
| `sum_fast_entry_step_2` | observed c (`error(t) form A, c=3, k=2, t=0`) | 1.5000 | **1.9558** | **3.0000** | 2.1236 | 1.5000 ↓ | **3.0000** |
| `sum_fast_entry_step_2` | error / bound (`error(t) form A, c=3, k=2, t=0`) | 0.50000 | **0.66577** | **1 − 8.1e-16** | 0.70787 | 0.50000 ↓ | **1 − 4.4e-07** |
| `two_prod_dekker` | observed c (`error(r) form R, c=0, k=2, t=13/8`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `two_prod_dekker` | error / bound (`error(r) form R, c=0, k=2, t=13/8`) | 0.92323 | 0.88499 ↓ | **0.99159** | 0.94722 | 0.90565 ↓ | **0.98551** |
| `two_prod_entry` | observed c (`error(r) form R, c=0, k=2, t=1/2`) | 0 | 0 | 0 | 0 | 0 | 0 |
| `two_prod_entry` | error / bound (`error(r) form R, c=0, k=2, t=1/2`) | 1 | 1 | 1 | 1 | 1 | 1 |

**What it brought closest.** With every seed, each time from an attaining line of this
milestone's runs: the accurate sums of two limbs in their entry forms (`add_entry_step_2`,
`sub_entry_step_2`, `sum_fast_entry_step_2`) to within $8.1 \cdot 10^{-16}$ of their bounds in
`binary64` and $4.4 \cdot 10^{-7}$ in `binary32`, and the merge of two accumulators `acc_merge_2`
to within $8.1 \cdot 10^{-16}$ in `binary64` (0.50 to 0.79 in the brute-force runs); the product
of two limbs as a ball `mul_ball_2_2` to 0.993 (0.94 to 0.95); the products and scalings of two
limbs by one (`mul_2_1_entry`, `scale_step_2`, `bv_scale_step_2`) to within
$1.7 \cdot 10^{-16}$ in `binary64` and $8.9 \cdot 10^{-8}$ in `binary32`; the radii of the full
Ball sums and differences to one gap of slack for one limb and 1.11 to 1.16 for two (1.25 to
1.36 in the brute-force runs, but `ball_sub_1_full` in `binary32`, which they had brought to
one gap). `two_prod_dekker` came to 0.99 (0.92 to 0.95 here) from a
regression case, the line of Milestone 1's longer search (the regression cases the search read
were those of Milestone 1; this milestone's, below, came after it, from its results). From the
strata alone: the sum of two limbs as a ball `add_ball_2_2` in `binary64`, to $1 - 8.5 \cdot
10^{-16}$ of its bound and 10.5 gaps of slack in its radius (0.67 and $2.3 \cdot 10^{15}$ gaps
in the brute-force runs, 0.83 with every seed).

The slack of these radii, `add_ball_2_2` and `mul_ball_2_2`, is counted in gaps of the radius
$d$ itself, the bound of the error of a sum or a product of points: a case whose error is 0.83
of $d$ leaves about $0.17\, d / \mathrm{ulp}(d)$ gaps, $2^{21}$ in `binary32` and $2^{50}$ in
`binary64`. Their listing makes $d$ the bound of the error claim of the same kernel rounded up
(with the smallest normal number added, which matters only near the underflow), so that their
closeness is about that of the row of the error over its bound: 0.83 to 1 for `add_ball_2_2`
and 0.99 for `mul_ball_2_2`.

**What stays far from attained even so.** The term $t$ of `bound_dot_1` and `bound_dot_2`, the
bound of the underflow of a dot product of $m$ terms: $2^{52}$ gaps above the value it states
in `binary64` and $2^{23}$ in `binary32`, the same in both searches and in the brute-force runs,
in every case. Their listing says why (`gen/kernels/bound_dot_1.kernel`): the constant of $t$
holds the smallest normal number $\eta/(2u)$ so as not to be subnormal, which makes $t$ larger
than the value it states, $m\,(\eta/2)\,(1+g)$, by about $m\,\eta/(2u)\,(1+g)$: about $1/u$
times it, an excess of nearly $t$ itself, which is $2^{p-1}$ gaps of $t$. A choice of the
listing, which the claim allows, and not a case the search missed. The steps of the dot products and of `axpy`
of two limbs (`dot_step_2`, `dot_entry_step_2`, `axpy_step_2`, `axpy_entry_step_2` and those of
a one-limb scalar), which both searches took to 0.73 to 0.80 of their bounds of form T; and the
accumulators' products of two limbs (`acc_mul_2`, `acc_mul_entry_2`), 0.56 to 0.75.

**What the search does not take.** The loops over arrays: `kairn-oracle search` searches kernels
only (its moves are those of the operands of one kernel, and a fold's line is an array). And the
118 kernels of this milestone that have none of the entries it climbs: the interval kernels
(`encloses_interval`, the tight bounds of an interval: `interval_add_k`, `interval_sub_k`,
`interval_mul_k`, `interval_neg_k`), the directed bounds of two limbs (`outward`:
`add_down_2_2` and the five like it), the products rounded down and up (`bound` with steps), the
conversions (`ball_of_interval`, `interval_of_ball`, `makes_ball`, `set_bound`), the set
operations (`ball_set`, `ball_splits`, `interval_set`, `splits`, `makes_interval`), and the kinds
with no quantity to climb (`certain`, `trit`, `rounded`, `neighbor`, `maximum`, `normalized`,
`finite_or_nan`). The interval kernels, the conversions and the directed bounds keep a ratio of
their distance to their allowance that the search could climb if it read them; their closest
values are those of the brute-force runs ([above](#how-close-the-claims-came)). A gap of the
search, not patched here.

**The regression cases.** The lines of this milestone joined `tests/regression/cases.txt` as
Milestone 1's did: the attaining lines of the brute-force runs of every claim of a kernel of
this milestone within 2 % of its bound (183 lines: compiled and enumerated; an error or a
distance within 2 % of its allowance, an upper bound in gaps within 2 % of its claim, a radius
slack of at most 1.02 gaps, an excess over a stated value of at most 0.02 gaps), and the
search's best lines where it came at least as close as the brute-force runs (166 lines, from
the run with every seed). Loops are left out: a line holds an array of up to 4 096 elements.
The file has 534 cases (185 before); the quick tier's `regression.cases` passed with them on the
Mac, through every runner of the Apple clang build at `8ee5ed9`, the interpreter and the 208
runs of the public interface (150 before), in 2.8 seconds (2.9 before, on a machine with a load
average of 10: the lines add runs of the same processes).

## Supplementary run: the close of rule R3

After the runs above, the close of rule R3 (the factors of a fused operation; branch
`m2-r3-close`, commit `8ee5ed9`, which contains `main` at `bbcce60`) added eight kernels and
loops and changed the code of four: **new** `bv_center_entry_2`, `bv_make_2_entry`,
`bv_scale_2_entry`, `bv_scale_radius_entry_2`, `bv_scale_step_2`, `conv_2_entry`, `dot_2_entry`,
`dot_entry_step_2`; **code changed** `axpy_entry_step_2`, `axpy_entry_step_2_1`, `axpy_2_entry`,
`axpy_2_1_entry`. A supplementary run judged these twelve at commit `8ee5ed9`, from copies made
with `git archive` of the merge `76ebf33` of that commit into this branch (whose code is that of
`8ee5ed9`), with the method of the runs above: every runner of the three machines (new builds),
seeds `m2r1r3-linux`, `m2r1r3-mac` and `m2r1r3-windows`; the six kernels to the aim of $10^8$
cases per kernel and format (22 units of 100 000 on the Linux machine, 7 of 50 000 on the Mac,
10 of 50 000 on the Windows machine), the six loops to two units on the Linux machine and the
same caps elsewhere; every enumeration of the plan for the twelve (37 domains, 46 931 460
indices) and their 48 entries of the emulated part, on the Mac. **The results of this section are
of `8ee5ed9`; every other result on this page is of `5f597fb`.** The summaries are
`results/milestone2/brute/supplementary/*-r3.json`.

**Why the other results stand at `8ee5ed9`.** Every other kernel and loop was compared between
the two commits: its generated definitions, function by function (the scalar kernel, its loops
`NAME_seq` and `NAME_lanes`, the packed `NAME_packed` of `gen/avx2.hpp` and `gen/neon.hpp`, and
the kernels printed for the emulated limb type), comment lines left out, and its entry of
`gen/claims.json` without its description. 242 are the same in every one; 29 differ in the field
`source` of their claims alone (where a listing comes from), which nothing judges; five loops,
`axpy_2`, `axpy_2_1`, `bv_scale_2`, `conv_2` and `dot_2`, have the same code in all four listings
and claims that differ in the `role` of an array or a scalar alone (`supplied` became `stored`),
which the generator reads for rule R3 and the oracle only checks to be one of the two (its
generator of cases and its judgment do not read it; `oracle/` did not change between the
commits). The kernel descriptions of three steps (`dot_step_2`, `scale_step_2`,
`mul_pow2_step_2`) changed in comments, `source`, `license`, their `supplied` marks and their
`entry` flag, not in the listing the interpreter evaluates. The correction of `axpy` of ball
vectors in `include/kairn/ball_vector.hpp` that `bbcce60` brought is a composition in the public
header, which these runners do not call (they run the generated kernels and loops).

**No failure.** Every series and every enumeration of the supplementary run passed the guards;
no case failed a claim, none was invalid, no finding:

| Machine | Compilers | Runners | Seed | Cases per kernel and format | Judged (compiled) | Enumerated (interpreter) |
|---|---|---|---|---|---|---|
| linux-x86-64-r3: Linux x86_64, AMD EPYC 7452 32-Core Processor | Clang 18.1.3, GNU 13.3.0 | 36 | `m2r1r3-linux` | 2 000 to 2 200 000 | 907 656 180 | 0 |
| macos-arm64-r3: Darwin arm64, Apple M3 Max | AppleClang 21.0.0.21000401, GNU 16.2.0 | 36 | `m2r1r3-mac` | 3 500 to 350 000 | 145 721 076 | 46 931 460 |
| windows-x64-r3: Windows AMD64, 13th Gen Intel(R) Core(TM) i5-13500T | MSVC 19.52.37029.0 | 18 | `m2r1r3-windows` | 5 000 to 500 000 | 104 068 326 | 0 |

| Machine | Wall time | Judged per second | Enumerated per second | One check pipeline, cases/s | One generator, cases/s | One interpreter pipeline, cases/s |
|---|---|---|---|---|---|---|
| linux-x86-64-r3 | 2319 s (0.64 h) | 391 383 | 0 | 6 290 | 4 660 | - |
| macos-arm64-r3 | 2965 s (0.82 h) | 49 147 | 15 828 | 9 713 | 5 862 | 26 732 |
| windows-x64-r3 | 4594 s (1.28 h) | 22 653 | 0 | 3 671 | 2 039 | - |

Per kernel and format, summed over the machines and their runners: 192 000 to 100 800 000 cases (median 100 800 000), of which 192 000 to 100 800 000 judged (a finite result, or any result in the extended domain), from 10 500 to 3 050 000 distinct cases. 12 of 24 kernel and format pairs reach $10^8$ cases; the fewest: `conv_2_entry` `binary32` 192 000, `conv_2_entry` `binary64` 192 000, `axpy_2_1_entry` `binary32` 288 000, `axpy_2_1_entry` `binary64` 288 000, `axpy_2_entry` `binary32` 288 000.

4 of 24 reach $10^8$ judged results; below it: `conv_2_entry` `binary32` 192 000, `conv_2_entry` `binary64` 192 000, `axpy_2_1_entry` `binary32` 288 000, `axpy_2_1_entry` `binary64` 288 000, `axpy_2_entry` `binary32` 288 000, `axpy_2_entry` `binary64` 288 000, `bv_make_2_entry` `binary32` 288 000, `bv_make_2_entry` `binary64` 288 000, `bv_scale_2_entry` `binary32` 288 000, `bv_scale_2_entry` `binary64` 288 000, `dot_2_entry` `binary32` 288 000, `dot_2_entry` `binary64` 288 000, `dot_entry_step_2` `binary64` 92 277 810, `dot_entry_step_2` `binary32` 92 337 390, `axpy_entry_step_2` `binary64` 93 322 098, `axpy_entry_step_2` `binary32` 93 350 052, `axpy_entry_step_2_1` `binary64` 93 350 682, `axpy_entry_step_2_1` `binary32` 93 411 306, `bv_scale_step_2` `binary32` 96 406 758, `bv_scale_step_2` `binary64` 96 525 486.

On each machine, every runner gave the same counts and the same extremes, for every kernel and format (72 series of runners compared).

The entries of the emulated part (the Mac, seed `m2r1r3-mac`):

| Precision | Mode | Entries | Complete, guards passed | Indices or cases covered | Lines | Judged | Failed | Invalid | Seconds of pipelines |
|---|---|---|---|---|---|---|---|---|---|
| 8 | every operand | 1 | 1 | 2 422 786 | 2 422 786 | 2 422 786 | 0 | 0 | 41 |
| 8 | random | 11 | 11 | 2 620 000 | 2 620 000 | 2 420 819 | 0 | 0 | 117 |
| 9 | random | 12 | 12 | 3 120 000 | 3 120 000 | 2 928 599 | 0 | 0 | 123 |
| 10 | random | 12 | 12 | 3 120 000 | 3 120 000 | 2 933 873 | 0 | 0 | 124 |
| 11 | random | 12 | 12 | 3 120 000 | 3 120 000 | 2 938 524 | 0 | 0 | 128 |
| all | | 48 | 48 | 14 402 786 | 14 402 786 | 13 644 601 | 0 | 0 | 534 |

### `axpy_2_1_entry`, at 8ee5ed9

Claims: `entries(z) of the step axpy_entry_step_2_1 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_entry_step_2_1: normalized(z)`; `entries(z), step axpy_entry_step_2_1: error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 0.799771 | 2.27721 |
| `binary32`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 0.799746 | 2.43389 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 625 170 | 625 170 | 0 | 0.467001 | - |
| `fp:3:-2:-1`, every operand (the full tier's format, every array up to 1 elements) | 26 650 | 26 650 | 0 | 0.380528 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 1 401, exact 699, nonfinite 699, one 702, overflow 1 401, tail 699, tie 702, tight 2 100, underflow 699, wide 699, zeros 699; `binary32`: cancel 1 401, exact 699, nonfinite 699, one 702, overflow 1 401, tail 699, tie 702, tight 2 100, underflow 699, wide 699, zeros 699.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.799771 (clang/neon, macos-arm64-r3):
  axpy_entry_step_2_1 binary64 -0x1.6p-1070 0x1.2f44a99728191p+50 -0x1.d166b9db52086p-4 0x1.0a4f7ap-1050 0x0p+0 #axpy_2_1_entry:underflow:365:element:310 -> -0x1.a0fe692bade48p-1020 -0x1p-1073
largest error / bound, interpreter 0.467001 (fp:3:-3:0, every operand):
  axpy_entry_step_2_1 fp:3:-3:0 -0x1.8p-2 -0x1.8p+0 -0x1p-3 0x0p+0 0x0p+0 #axpy_2_1_entry:exhaustive:238240:element:0 -> 0x1p-1 0x0p+0
```

### `axpy_2_entry`, at 8ee5ed9

Claims: `entries(z) of the step axpy_entry_step_2 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_entry_step_2: normalized(z)`; `entries(z), step axpy_entry_step_2: error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 0.729852 | 4.15909 |
| `binary32`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 0.730277 | 3.44766 |
| `fp:4:-4:-1`, every operand (another format, every array up to 1 elements) | 15 625 250 | 15 625 250 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (the full tier's format, every array up to 1 elements) | 262 208 | 262 208 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 1 401, exact 699, nonfinite 699, one 702, overflow 1 401, tail 699, tie 702, tight 2 100, underflow 699, wide 699, zeros 699; `binary32`: cancel 1 401, exact 699, nonfinite 699, one 702, overflow 1 401, tail 699, tie 702, tight 2 100, underflow 699, wide 699, zeros 699.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.730277 (msvc-fixup-call/cxx, windows-x64-r3):
  axpy_entry_step_2 binary32 0x1.810b42p-119 -0x1p-148 -0x1.0d3e84p+8 0x1.50faacp-18 -0x1.245bbp-128 0x0p+0 #axpy_2_entry:underflow:2660:element:2113 -> -0x1.94f76e0000000p-111 0x1.76f0000000000p-136
largest error / bound, interpreter 0.399878 (fp:4:-4:-1, every operand):
  axpy_entry_step_2 fp:4:-4:-1 -0x1.cp-2 0x0p+0 -0x1.8p+0 -0x1p-4 0x0p+0 0x0p+0 #axpy_2_entry:exhaustive:6156116:element:0 -> 0x1.4p-1 0x0p+0
```

### `axpy_entry_step_2`, at 8ee5ed9

Claims: `normalized(z)`; `error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 93 322 098 | 0 | 0.715573 | 3.99790 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 93 350 052 | 0 | 0.700754 | 3.05744 |
| `fp:5:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 953 125 | 602 249 | 0 | 0.417584 | - |
| `fp:4:-4:-2`, every operand (p = min_precision, another exponent range) | 1 860 867 | 902 883 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (p = min_precision, the quick tier's format) | 226 981 | 111 361 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 571 875, exactprod 190 625, extreme 190 625, overflow 190 625, pow2 190 625, state 381 250, tie 190 625, tight 571 875, underflow 190 625, uniform 190 625, zero 190 625; `binary32`: cancel 571 875, exactprod 190 625, extreme 190 625, overflow 190 625, pow2 190 625, state 381 250, tie 190 625, tight 571 875, underflow 190 625, uniform 190 625, zero 190 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.715573 (clang18-fixup-call/cxx, linux-x86-64-r3):
  axpy_entry_step_2 binary64 -0x1.ff795518fc2f2p-431 0x1.d4140f8ed1d8bp-485 0x1.76bb402f71fe2p-564 -0x1.3f6a0847858b6p-621 -0x1.9df06a2fb673p-1015 0x1p-1074 #underflow:1106216 -> -0x1.7658bd07e84e9p-994 -0x0.000000311c053p-1022
largest error / bound, interpreter 0.417584 (fp:5:-3:-2, every operand):
  axpy_entry_step_2 fp:5:-3:-2 -0x1.2p+2 0x1p-3 -0x1.8p-2 0x0p+0 0x0p+0 0x0p+0 #exhaustive:429312 -> 0x1.cp+0 0x0p+0
```

### `axpy_entry_step_2_1`, at 8ee5ed9

Claims: `normalized(z)`; `error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 93 350 682 | 0 | 0.800000 | 1.98467 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 93 411 306 | 0 | 0.800000 | 2.26084 |
| `fp:4:-5:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 953 127 | 765 439 | 0 | 0.641498 | - |
| `fp:3:-6:-3`, every operand (p = min_precision, another exponent range) | 552 279 | 509 443 | 0 | 0.504720 | - |
| `fp:3:-5:-3`, every operand (p = min_precision, the quick tier's format) | 107 911 | 98 303 | 0 | 0.504720 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 571 875, exactprod 190 625, extreme 190 625, overflow 190 625, pow2 190 625, state 381 250, tie 190 625, tight 571 875, underflow 190 625, uniform 190 625, zero 190 625; `binary32`: cancel 571 875, exactprod 190 625, extreme 190 625, overflow 190 625, pow2 190 625, state 381 250, tie 190 625, tight 571 875, underflow 190 625, uniform 190 625, zero 190 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.800000 (clang-fixup-inline/cxx, macos-arm64-r3):
  axpy_entry_step_2_1 binary64 -0x1.0000000000001p-1022 0x1.8p+0 0x1.fffffffffffffp-54 0x1p-1073 0x0p+0 #extreme:51758 -> -0x1.8000000000001p-1022 0x0p+0
largest error / bound, interpreter 0.641498 (fp:4:-5:-3, every operand):
  axpy_entry_step_2_1 fp:4:-5:-3 -0x1.ap-2 -0x1p-1 -0x1p-5 0x0p+0 0x0p+0 #exhaustive:277795 -> 0x1.8p-3 0x0p+0
```

### `bv_center_entry_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`; `represents(z)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 100 800 000 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 100 800 000 | 0 | 0 (exact) | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | 0 (exact) | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | 0 (exact) | - |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | 0 (exact) | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | 0 (exact) | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000; `binary32`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000.

### `bv_make_2_entry`

Claims: `makes_ball_vector(z, rr) from centers c, radius r, flag finite`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 288 000 | 288 000 | 0 |
| `binary32`, 90 runners on 3 machines | 288 000 | 288 000 | 0 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 149 314 | 149 314 | 0 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 24 766 | 24 766 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: badcenter 1 167, badradius 3 501, one 1 168, overflow 1 166, tail 1 165, underflow 1 166, zeros 1 167; `binary32`: badcenter 1 167, badradius 3 501, one 1 168, overflow 1 166, tail 1 165, underflow 1 166, zeros 1 167.

### `bv_scale_2_entry`

Claims: `encloses_entries(z, r) x*a over x=[x +- rx], V1-V4, flag finite, finite when |(abs(x)+rx)*a| <= 2^(qmax+p-2)`; `V3, step bv_scale_step_2: normalized(z)`; `V3, step bv_scale_step_2: error(z) form R, c=2, k=2, t=1`; `V3, radius bv_scale_radius_entry_2: upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | largest error / bound | observed c | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 1.46918 | 0.993950 | 1.92532 | 1.04200 |
| `binary32`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 1.48735 | 0.996039 | 1.88843 | 1.04344 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 1 343 408 | 1 343 408 | 0 | 1.8125 | 0.470588 | - | 1.55357 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 688 692 | 688 692 | 0 | 1.40625 | 0.759322 | - | 1.14516 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 1 elements) | 12 364 | 12 364 | 0 | 1.8125 | 0.470588 | - | 1.55357 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 750, nonfinite 750, one 1 501, overflow 750, tail 749, threshold 2 250, underflow 750, whole 750, wide 750, zeroradius 750, zeros 750; `binary32`: cancel 750, nonfinite 750, one 1 501, overflow 750, tail 749, threshold 2 250, underflow 750, whole 750, wide 750, zeroradius 750, zeros 750.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 1.46918 (clang-fixup-inline/cxx, macos-arm64-r3):
  bv_scale_2_entry binary64 lanes:3 859 0x1.6adcef39995c5p+973 0x1.7f58bfc97141dp-24 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 -0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 ... (1714 more) #threshold:1889 -> 0x1.7f58bfc97141cp+1000 0x1.7f58bfc97141cp+1000 -0x1.7f58bfc97141cp+1000 0x1.7f58bfc97141cp+1000 ... (1716 more)
smallest radius slack, gaps (the worst entry), interpreter 1.40625 (fp:3:-4:1, every operand):
  bv_scale_2_entry fp:3:-4:1 seq 1 0x1.8p+1 -0x1.8p+0 -0x1.8p+2 -0x1p-4 #exhaustive:158877 -> 0x1p+3 0x1p+0 0x1.8p+2 1
largest error / bound, compiled 0.996039 (msvc/avx2, windows-x64-r3):
  bv_scale_step_2 binary32 0x1.26ec8p-94 -0x1p-118 -0x1.8f81p-23 #bv_scale_2_entry:underflow:2906:entry:900 -> -0x1.cc3f38p-117 0x1.c8p-142
largest error / bound, interpreter 0.759322 (fp:3:-4:1, every operand):
  bv_scale_step_2 fp:3:-4:1 -0x1.8p-1 -0x1p-4 -0x1.8p-2 #bv_scale_2_entry:exhaustive:255971:entry:0 -> 0x1p-2 0x0p+0
smallest excess over the stated value, gaps, compiled 1.04200 (clang-fixup-inline/cxx, macos-arm64-r3):
  bv_scale_2_entry binary64 seq 2 0x1.8b997cc64735dp+931 0x1.52d78695381dcp+25 -0x1.d4905e5b94a4ep+993 0x1.4b80fb62e0b63p+997 -0x1.9f42aaa50214dp+934 -0x1.78fdc1294d2bap+916 #threshold:71 -> -0x1.36188c146ca63p+1019 0x1.b6c763826b0e1p+1022 -0x1.4074aa614d9efp+965 0x1.e4a7873716eefp+967 0x1.05ceda4f432acp+957 1
smallest excess over the stated value, gaps, interpreter 1.14516 (fp:3:-4:1, every operand):
  bv_scale_2_entry fp:3:-4:1 seq 1 0x1.8p-2 -0x1.8p+3 -0x1.8p-1 0x0p+0 #exhaustive:19105 -> 0x1p+3 0x1p+0 0x1.8p+2 1
```

### `bv_scale_radius_entry_2`

Claims: `upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 100 800 000 | 0 | 1.00981 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 100 800 000 | 0 | 1.00013 |
| `fp:4:-8:4`, every operand (another exponent range) | 2 797 312 | 2 797 312 | 0 | 1.19636 |
| `fp:4:-5:3`, every operand (quick tier + 1 bit) | 1 017 600 | 1 017 600 | 0 | 1.36688 |
| `fp:3:-5:3`, every operand (p = min_precision + 1, the quick tier's format) | 126 400 | 126 400 | 0 | 1.14516 |
| `fp:2:-5:3`, every operand (p = min_precision, the quick tier's exponent range) | 15 600 | 15 600 | 0 | 1.25 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 435 715, extreme 217 856, huge 435 715, mixed 653 571, overflow 217 857, pow2 217 857, underflow 217 857, uniform 217 858, zero 217 857, zeros 217 857; `binary32`: atnormal 435 715, extreme 217 856, huge 435 715, mixed 653 571, overflow 217 857, pow2 217 857, underflow 217 857, uniform 217 858, zero 217 857, zeros 217 857.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 1.00013 (clang18-fixup-call/cxx, linux-x86-64-r3):
  bv_scale_radius_entry_2 binary32 0x1.b33ffap+40 0x1.d3a29p-59 -0x1.2p+65 #atnormal:1832705 -> 0x1.07124p+7
smallest excess over the stated value, gaps, interpreter 1.14516 (fp:3:-5:3, every operand):
  bv_scale_radius_entry_2 fp:3:-5:3 0x1p+2 0x1.8p-4 -0x1.8p+4 #exhaustive:76082 -> 0x1.8p+1
```

### `bv_scale_step_2`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 96 525 486 | 0 | 1 - ε, ε < 10⁻⁹ | 1.96428 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 96 406 758 | 0 | 0.9999998808 | 1.99878 |
| `fp:6:-8:-2`, every operand (quick tier + 2 bits) | 4 152 897 | 2 754 581 | 0 | 0.972718 | - |
| `fp:5:-4:2`, every operand (another exponent range) | 1 027 905 | 304 717 | 0 | 0.907265 | - |
| `fp:5:-8:-2`, every operand (quick tier + 1 bit) | 1 027 905 | 799 453 | 0 | 0.951325 | - |
| `fp:3:-8:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 42 273 | 41 241 | 0 | 0.794235 | - |
| `fp:2:-8:-2`, every operand (p = min_precision, the quick tier's exponent range) | 7 285 | 7 285 | 0 | 0.628272 | 0.410256 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165; `binary32`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64-r3):
  bv_scale_step_2 binary64 -0x1.8p+0 -0x1p-53 0x1.ffffffffffffep-1023 #extreme:1710894 -> -0x1.7fffffffffffep-1022 -0x0p+0
largest error / bound, interpreter 0.972718 (fp:6:-8:-2, every operand):
  bv_scale_step_2 fp:6:-8:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-5 #exhaustive:1480613 -> 0x1.4p-3 0x0p+0
```

### `conv_2_entry`

Claims: `coefficients(z) of the fold dot_2_entry, sequential`; `finite_or_nan(z) flag finite`; `coefficients(z), fold dot_2_entry: normalized(r)`; `coefficients(z), fold dot_2_entry: fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`.

| Run | Cases | Judged | Failed | largest error / bound, order sequential |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 192 000 | 192 000 | 0 | 0.999476 |
| `binary32`, 60 runners on 3 machines | 192 000 | 192 000 | 0 | 0.937140 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 990 025 | 990 025 | 0 | 0.764346 |
| `fp:4:-4:-1`, every operand (the full tier's format, every array up to 1 elements) | 63 001 | 63 001 | 0 | 0.561075 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 1 617, nonfinite 807, one 809, overflow 808, pow2 806, sign 808, tail 806, tight 1 616, underflow 808, wide 808, zeros 807; `binary32`: cancel 1 617, nonfinite 807, one 809, overflow 808, pow2 806, sign 808, tail 806, tight 1 616, underflow 808, wide 808, zeros 807.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order sequential, compiled 0.999476 (clang18-fixup-call/cxx, linux-x86-64-r3):
  conv_2_entry binary64 seq 5 3 0x1.0000001779156p+112 0x0p+0 0x0p+0 -0x0p+0 0x0p+0 0x1.ffffffcebcea3p+58 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x1.0000000018a63p+112 0x0p+0 0x0p+0 0x1.ffffffffd6156p+58 0x0p+0 0x0p+0 #tight:697 -> 0x1.0000001791bbap+224 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x1.214b71350ep+161 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 1
largest error / bound, order sequential, interpreter 0.764346 (fp:4:-5:0, every operand):
  conv_2_entry fp:4:-5:0 seq 1 1 -0x1.4p-1 0x1p-5 -0x1.4p-1 0x1p-5 #exhaustive:475609 -> 0x1.4p-2 0x0p+0 1
```

### `dot_2_entry`

Claims: `normalized(r)`; `fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 0.999476 | 0.999476 |
| `binary32`, 90 runners on 3 machines | 288 000 | 288 000 | 0 | 0.563468 | 0.280883 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 988 037 | 988 037 | 0 | - | 0.764346 |
| `fp:4:-4:-1`, every operand (the full tier's format, every array up to 1 elements) | 62 501 | 62 501 | 0 | - | 0.561075 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 1 617, nonfinite 807, one 809, overflow 808, pow2 806, sign 808, tail 806, tight 1 616, underflow 808, wide 808, zeros 807; `binary32`: cancel 1 617, nonfinite 807, one 809, overflow 808, pow2 806, sign 808, tail 806, tight 1 616, underflow 808, wide 808, zeros 807.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.999476 (clang18-fixup-call/cxx, linux-x86-64-r3):
  dot_2_entry binary64 lanes:2 1 -0x1.0000001779156p+95 -0x1.ffffffcebcea3p+41 0x1.0000000018a63p+95 0x1.ffffffffd6156p+41 #tight:834 -> -0x1.0000001791bbap+190 -0x1.214b71350ep+127 1
largest error / bound, order sequential, compiled 0.999476 (clang18-fixup-call/cxx, linux-x86-64-r3):
  dot_2_entry binary64 seq 1 -0x1.0000001779156p+100 -0x1.ffffffcebcea3p+46 0x1.0000000018a63p+100 0x1.ffffffffd6156p+46 #tight:1276 -> -0x1.0000001791bbap+200 -0x1.214b71350ep+137 1
largest error / bound, order sequential, interpreter 0.764346 (fp:4:-5:0, every operand):
  dot_2_entry fp:4:-5:0 seq 1 -0x1.4p-1 0x1p-5 -0x1.4p-1 0x1p-5 #exhaustive:473621 -> 0x1.4p-2 0x0p+0 1
```

### `dot_entry_step_2`

Claims: `normalized(t)`; `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 92 277 810 | 0 | 0.699924 | 3.01186 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 92 337 390 | 0 | 0.722091 | 3.30681 |
| `fp:5:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 953 125 | 602 377 | 0 | 0.417584 | - |
| `fp:4:-4:-2`, every operand (p = min_precision, another exponent range) | 1 860 867 | 904 263 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (p = min_precision, the quick tier's format) | 226 981 | 111 453 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 653 572, exactprod 217 857, extreme 217 856, overflow 217 857, pow2 217 857, state 435 715, tie 217 857, underflow 217 857, uniform 217 858, zero 217 856, zerostate 217 858; `binary32`: cancel 653 572, exactprod 217 857, extreme 217 856, overflow 217 857, pow2 217 857, state 435 715, tie 217 857, underflow 217 857, uniform 217 858, zero 217 856, zerostate 217 858.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.722091 (clang18-fixup-call/cxx, linux-x86-64-r3):
  dot_entry_step_2 binary32 -0x1.6a0b2ap-111 -0x1.aa2p-138 -0x1.e67ffap-50 -0x1.49d98cp-78 -0x1.42591p-69 -0x1.69c068p-96 #uniform:896854 -> -0x1.67a694p-111 0x1.2p-141
largest error / bound, interpreter 0.417584 (fp:5:-3:-2, every operand):
  dot_entry_step_2 fp:5:-3:-2 0x0p+0 0x0p+0 -0x1.2p+2 0x1p-3 -0x1.8p-2 0x0p+0 #exhaustive:972184 -> 0x1.cp+0 0x0p+0
```

## Per kernel

### `abs_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`; `represents(z)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 (exact) | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | 0 (exact) | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | 0 (exact) | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | 0 (exact) | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | 0 (exact) | 0 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | 0 (exact) | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000; `binary32`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000.

### `abs_upper_2`

Claims: `rounded(t) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 23 393 574; inexact, as RN 33 608 016; differs from RN 24 253 326; a non-finite operand 20 520 000; rounds to inf 825 084 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 25 087 734; inexact, as RN 32 649 498; differs from RN 23 518 944; a non-finite operand 20 520 000; rounds to inf 823 824 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact, as RN 2 582 912; differs from RN 2 582 914; a non-finite operand 3; rounds to inf 3 070 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact, as RN 129 600; differs from RN 129 602; a non-finite operand 3; rounds to inf 638 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact, as RN 1 348; differs from RN 1 350; a non-finite operand 3; rounds to inf 70 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact, as RN 382; differs from RN 384; a non-finite operand 3; rounds to inf 38 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | exact 25; inexact, as RN 110; differs from RN 90; a non-finite operand 3; rounds to inf 20 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact, as RN 357 760; differs from RN 357 762; a non-finite operand 3; rounds to inf 1 022 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000; `binary32`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000.

### `acc_add_1`

Claims: `rounded(t) nearest`; `error(t) form R, c=1/(1+u), k=1, t=0`; `rounded(b) nearest of a+abs(x)`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c | cases by rounding |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 100 605 834 | 0 | exact 42 240 312; inexact 54 509 040; tie 3 395 358; the leading limb of its output is not finite: nothing claimed 3 355 290 | 1 (the claim) | 1.00000 | exact 19 346 364; inexact 56 447 928; tie 14 863 320; the leading limb of its output is not finite: nothing claimed 12 842 388 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 100 604 952 | 0 | exact 43 394 454; inexact 52 855 722; tie 3 895 812; the leading limb of its output is not finite: nothing claimed 3 354 012 | 1 (the claim) | 0.9999999404 | exact 20 116 980; inexact 55 159 794; tie 15 372 072; the leading limb of its output is not finite: nothing claimed 12 851 154 |
| `fp:4:-6:3`, every operand (another exponent range) | 2 695 000 | 2 686 616 | 0 | exact 671 704; inexact 1 634 688; tie 344 960; the leading limb of its output is not finite: nothing claimed 43 648 | 1 (the claim) | 0.941176 | exact 460 600; inexact 1 750 000; tie 397 600; the leading limb of its output is not finite: nothing claimed 86 800 |
| `fp:4:-3:1`, every operand (quick tier + 1 bit) | 433 200 | 424 816 | 0 | exact 182 064; inexact 146 688; tie 80 640; the leading limb of its output is not finite: nothing claimed 23 808 | 1 (the claim) | - | exact 124 640; inexact 167 200; tie 94 240; the leading limb of its output is not finite: nothing claimed 47 120 |
| `fp:3:-3:1`, every operand (p = min_precision + 2, the quick tier's format) | 53 016 | 52 052 | 0 | exact 22 488; inexact 17 856; tie 9 792; the leading limb of its output is not finite: nothing claimed 2 880 | 1 (the claim) | 0.888889 | exact 15 792; inexact 20 304; tie 11 280; the leading limb of its output is not finite: nothing claimed 5 640 |
| `fp:2:-3:1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 6 348 | 6 244 | 0 | exact 2 748; inexact 2 112; tie 1 152; the leading limb of its output is not finite: nothing claimed 336 | 1 (the claim) | 0.8 | exact 2 024; inexact 2 392; tie 1 288; the leading limb of its output is not finite: nothing claimed 644 |
| `fp:1:-3:1`, every operand (p = min_precision, the quick tier's exponent range) | 726 | 716 | 0 | exact 330; inexact 216; tie 144; the leading limb of its output is not finite: nothing claimed 36 | 1 (the claim) | 0.666667 | exact 264; inexact 264; tie 132; the leading limb of its output is not finite: nothing claimed 66 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 413 334, atop 413 334, cancel 413 334, exactprod 206 666, extreme 206 666, overflow 206 666, pow2 206 666, tie 413 334, underflow 206 666, uniform 206 668, zero 206 666; `binary32`: apart 413 334, atop 413 334, cancel 413 334, exactprod 206 666, extreme 206 666, overflow 206 666, pow2 206 666, tie 413 334, underflow 206 666, uniform 206 668, zero 206 666.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  acc_add_1 binary64 -0x1p-178 0x1.0000000001p-181 -0x1.0000000000001p-178 #exactprod:68380 -> -0x1p-177 0x1.2000000000201p-178
largest error / bound, interpreter 1 (fp:4:-6:3, every operand):
  acc_add_1 fp:4:-6:3 -0x1.ep+6 0x0p+0 0x1.ap+5 #exhaustive:164 -> -0x1p+6 0x1.ap+5
```

### `acc_add_2`

Claims: `normalized(t)`; `error(t) form R, c=3/(1-4*u), k=2, t=0`; `rounded(b) nearest of a+abs(x[0])`.

| Run | Cases | Judged | Failed | largest error / bound | observed c | cases by rounding |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 002 594 | 0 | 0.566017 | 1.69805 | exact 1 203 246; inexact 4 098 618; tie 1 027 494; the leading limb of its output is not finite: nothing claimed 870 642 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 999 696 | 0 | 0.666666 | 2.00000 | exact 1 267 434; inexact 3 991 878; tie 1 061 586; the leading limb of its output is not finite: nothing claimed 879 102 |
| `fp:3:-3:1`, every operand (p = min_precision, another exponent range) | 1 370 904 | 1 243 294 | 0 | 0.273504 | - | exact 279 630; inexact 545 876; tie 210 798; the leading limb of its output is not finite: nothing claimed 334 600 |
| `fp:4:-2:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 484 128 | 423 364 | 0 | 0 | - | exact 143 664; inexact 77 736; tie 96 678; the leading limb of its output is not finite: nothing claimed 166 050 |
| `fp:3:-2:0`, every operand (p = min_precision, the quick tier's format) | 55 696 | 48 684 | 0 | 0 | - | exact 17 464; inexact 8 732; tie 10 502; the leading limb of its output is not finite: nothing claimed 18 998 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665; `binary32`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666666 (clang18-fixup-call/cxx, linux-x86-64):
  acc_add_2 binary32 0x1.fffffep+125 -0x1.46596cp-88 0x1.fffffep+127 -0x1p+127 -0x1.095f0ap+102 #overflow:3024 -> -0x1.000002p+126 -0x1.2be1p+97 inf
largest error / bound, interpreter 0.273504 (fp:3:-3:1, every operand):
  acc_add_2 fp:3:-3:1 -0x1p+3 0x1p-1 0x0p+0 0x1.4p+1 0x1p-3 #exhaustive:338564 -> -0x1.4p+2 0x0p+0 0x1.4p+1
```

### `acc_merge_1`

Claims: `rounded(t) nearest`; `error(t) form R, c=1/(1+u), k=1, t=0`; `rounded(b) nearest of a+c`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c | cases by rounding |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 98 125 272 | 0 | exact 41 141 412; inexact 53 088 822; tie 3 306 978; the leading limb of its output is not finite: nothing claimed 3 262 788 | 1 (the claim) | 1.00000 | exact 32 079 582; inexact 48 643 056; tie 1 613 664; the leading limb of its output is not finite: nothing claimed 18 463 698 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 98 123 778 | 0 | exact 42 283 620; inexact 51 479 118; tie 3 781 692; the leading limb of its output is not finite: nothing claimed 3 255 570 | 1 (the claim) | 0.9999999404 | exact 32 301 468; inexact 47 443 572; tie 2 581 182; the leading limb of its output is not finite: nothing claimed 18 473 778 |
| `fp:1:-5:5`, every operand (p = min_precision, another exponent range) | 76 176 | 76 158 | 0 | exact 18 288; inexact 46 656; tie 10 368; the leading limb of its output is not finite: nothing claimed 864 | 1 (the claim) | 0.666667 | exact 17 457; inexact 47 610; tie 9 522; the leading limb of its output is not finite: nothing claimed 1 587 |
| `fp:4:-3:1`, every operand (quick tier + 2 bits) | 20 793 600 | 20 670 592 | 0 | exact 8 739 072; inexact 7 041 024; tie 3 870 720; the leading limb of its output is not finite: nothing claimed 1 142 784 | 1 (the claim) | - | exact 6 137 000; inexact 7 942 000; tie 4 476 400; the leading limb of its output is not finite: nothing claimed 2 238 200 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, another exponent range) | 4 064 256 | 4 057 056 | 0 | exact 1 352 704; inexact 1 941 504; tie 647 168; the leading limb of its output is not finite: nothing claimed 122 880 | 1 (the claim) | 0.888889 | exact 1 000 188; inexact 2 095 632; tie 730 296; the leading limb of its output is not finite: nothing claimed 238 140 |
| `fp:2:-6:4`, every operand (p = min_precision + 1, another exponent range) | 1 272 384 | 1 271 992 | 0 | exact 297 792; inexact 806 400; tie 152 064; the leading limb of its output is not finite: nothing claimed 16 128 | 1 (the claim) | 0.8 | exact 242 990; inexact 830 584; tie 167 884; the leading limb of its output is not finite: nothing claimed 30 926 |
| `fp:3:-3:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 1 272 384 | 1 265 184 | 0 | exact 539 712; inexact 428 544; tie 235 008; the leading limb of its output is not finite: nothing claimed 69 120 | 1 (the claim) | 0.888889 | exact 397 620; inexact 477 144; tie 265 080; the leading limb of its output is not finite: nothing claimed 132 540 |
| `fp:2:-3:1`, every operand (p = min_precision + 1, the quick tier's format) | 76 176 | 75 784 | 0 | exact 32 976; inexact 25 344; tie 13 824; the leading limb of its output is not finite: nothing claimed 4 032 | 1 (the claim) | 0.8 | exact 26 450; inexact 27 508; tie 14 812; the leading limb of its output is not finite: nothing claimed 7 406 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 380 000, atop 380 001, cancel 380 001, exactprod 189 999, extreme 189 999, overflow 190 000, pow2 189 999, tie 380 001, underflow 190 000, uniform 190 001, zero 189 999; `binary32`: apart 380 000, atop 380 001, cancel 380 001, exactprod 189 999, extreme 189 999, overflow 190 000, pow2 189 999, tie 380 001, underflow 190 000, uniform 190 001, zero 189 999.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  acc_merge_1 binary64 0x1.0000000000001p+469 0x1.04004p+469 0x1p+469 0x1.0001p+471 #exactprod:45580 -> 0x1p+470 0x1.41011p+471
largest error / bound, interpreter 1 (fp:1:-5:5, every operand):
  acc_merge_1 fp:1:-5:5 -0x1p+5 0x0p+0 0x1p+3 0x0p+0 #exhaustive:240 -> -0x1p+5 0x0p+0
```

### `acc_merge_2`

Claims: `normalized(t)`; `error(t) form R, c=3/(1-4*u), k=2, t=0`; `rounded(b) nearest of a+c`.

| Run | Cases | Judged | Failed | largest error / bound | observed c | cases by rounding |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 011 252 | 0 | 0.666667 | 2.00000 | exact 2 284 542; inexact 3 478 554; tie 117 990; the leading limb of its output is not finite: nothing claimed 1 318 914 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 009 452 | 0 | 0.629769 | 1.88931 | exact 2 304 342; inexact 3 388 230; tie 184 896; the leading limb of its output is not finite: nothing claimed 1 322 532 |
| `fp:3:-2:-1`, every operand (p = min_precision, another exponent range) (**INCOMPLETE or guard failed**) | 121 104 | 110 736 | 0 | 0 | - | exact 60 552; tie 20 184; the leading limb of its output is not finite: nothing claimed 40 368 |
| `fp:4:-3:-1`, restricted: `a.in=0x0p+0/0x1p-2/0x1.4p+0/0x1.8p+0`, `c.in=0x0p+0/0x1p-1/0x1.4p+0/0x1.cp+0/0x1.4p+2` (p = min_precision + 1, another exponent range) (**INCOMPLETE or guard failed**) | 302 580 | 302 580 | 0 | 0 | - | exact 272 322; tie 30 258 |
| `fp:3:-2:0`, restricted: `a.in=0x0p+0/0x1p-2/0x1.4p+0/0x1.8p+0`, `c.in=0x0p+0/0x1p-1/0x1.4p+0/0x1.cp+0/0x1.4p+2` (p = min_precision, the quick tier's format) | 69 620 | 69 620 | 0 | 0 | - | exact 52 215; inexact 6 962; tie 10 443 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665; `binary32`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666667 (clang18-fixup-call/cxx, linux-x86-64):
  acc_merge_2 binary64 0x1.fffffffffffffp+1021 -0x1.dfc7187a7a1cp-119 0x1p+1023 -0x1p+1023 -0x1.fffffffffffffp+969 0x1.ffffffffffffcp+1022 #overflow:65994 -> -0x1.0000000000002p+1022 0x1p+969 0x1.ffffffffffffep+1023
largest error / bound, interpreter 0 (fp:3:-2:-1, every operand):
  acc_merge_2 fp:3:-2:-1 -0x1.cp+1 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 #exhaustive:168 -> -0x1.cp+1 0x0p+0 0x0p+0
```

### `acc_mul_1`

Claims: `rounded(t) nearest`; `rounded(b) nearest of a+abs(x)*abs(y)`.

| Run | Cases | Judged | Failed | cases by rounding | cases by rounding |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 82 896 210 | 0 | exact 8 566 776; inexact 74 197 206; tie 93 528; the leading limb of its output is not finite: nothing claimed 20 642 490 | exact 8 457 138; inexact 74 005 686; tie 157 032; the leading limb of its output is not finite: nothing claimed 20 880 144 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 88 923 600 | 0 | exact 11 213 010; inexact 77 332 320; tie 340 722; the leading limb of its output is not finite: nothing claimed 14 613 948 | exact 11 006 856; inexact 76 616 604; tie 411 372; the leading limb of its output is not finite: nothing claimed 15 465 168 |
| `fp:3:-2:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 1 186 380 | 799 180 | 0 | exact 311 500; inexact 299 600; tie 149 440; the leading limb of its output is not finite: nothing claimed 425 840 | exact 202 800; inexact 334 932; tie 130 416; the leading limb of its output is not finite: nothing claimed 518 232 |
| `fp:1:-2:1`, every operand (p = min_precision, the quick tier's exponent range) | 3 645 | 3 441 | 0 | exact 1 845; inexact 820; tie 680; the leading limb of its output is not finite: nothing claimed 300 | exact 1 557; inexact 1 008; tie 648; the leading limb of its output is not finite: nothing claimed 432 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, another exponent range) | 8 001 504 | 6 442 944 | 0 | exact 1 474 912; inexact 4 040 960; tie 801 664; the leading limb of its output is not finite: nothing claimed 1 683 968 | exact 960 372; inexact 4 404 456; tie 715 428; the leading limb of its output is not finite: nothing claimed 1 921 248 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, the quick tier's format) | 68 590 | 56 778 | 0 | exact 26 150; inexact 17 800; tie 10 360; the leading limb of its output is not finite: nothing claimed 14 280 | exact 19 038; inexact 20 900; tie 10 032; the leading limb of its output is not finite: nothing claimed 18 620 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 413 334, atop 413 334, cancel 413 334, exactprod 206 666, extreme 206 666, overflow 206 666, pow2 206 666, tie 413 334, underflow 206 666, uniform 206 668, zero 206 666; `binary32`: apart 413 334, atop 413 334, cancel 413 334, exactprod 206 666, extreme 206 666, overflow 206 666, pow2 206 666, tie 413 334, underflow 206 666, uniform 206 668, zero 206 666.

### `acc_mul_2`

Claims: `normalized(t)`; `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`; `rounded(b) nearest of a+abs(x[0])*abs(y[0])`.

| Run | Cases | Judged | Failed | largest error / bound | observed c | cases by rounding |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 5 751 810 | 0 | 0.395971 | 2.77180 | exact 339 498; inexact 5 393 016; tie 4 752; the leading limb of its output is not finite: nothing claimed 1 462 734 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 171 606 | 0 | 0.607933 | 2.99777 | exact 513 882; inexact 5 576 076; tie 23 184; the leading limb of its output is not finite: nothing claimed 1 086 858 |
| `fp:4:-3:-2`, restricted: `a.in=0x0p+0/0x1p-1/0x1.8p+0`, `s.lead=-1:0` (p = min_precision, the quick tier's format) | 267 912 | 157 540 | 0 | 0.372281 | - | exact 55 656; inexact 62 208; tie 29 184; the leading limb of its output is not finite: nothing claimed 120 864 |
| `fp:4:-3:-2`, restricted: `a.in=0x0p+0/0x1p-1/0x1.8p+0`, `s.lead=-1:0`, `x.lead=-1:0` (p = min_precision, the quick tier's format) | 105 408 | 82 312 | 0 | 0.350004 | - | exact 24 096; inexact 38 592; tie 13 728; the leading limb of its output is not finite: nothing claimed 28 992 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665; `binary32`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.607933 (clang-fixup-inline/cxx, macos-arm64):
  acc_mul_2 binary32 0x1.ep-146 -0x0p+0 0x1.73a89ep-119 -0x1.326cfep-59 0x1.d32fcap-85 0x1.903d4ep-60 -0x1.e4487ap-92 #uniform:7275 -> -0x1.df13aep-119 0x1.88p-144 0x1.a95e26p-118
largest error / bound, interpreter 0.372281 (fp:4:-3:-2, restricted: a.in=0x0p+0/0x1p-1/0x1.8p+0, s.lead=-1:0):
  acc_mul_2 fp:4:-3:-2 -0x1p-1 0x0p+0 0x0p+0 -0x1.4p+1 0x1p-3 -0x1.8p-2 0x0p+0 #exhaustive:123491 -> 0x1p-1 0x0p+0 0x1p+0
```

### `acc_mul_entry_1`

Claims: `rounded(t) nearest`; `rounded(b) nearest of a+abs(x)*abs(y)`.

| Run | Cases | Judged | Failed | cases by rounding | cases by rounding |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 82 871 478 | 0 | exact 8 576 154; inexact 74 164 410; tie 94 248; the leading limb of its output is not finite: nothing claimed 20 665 188 | exact 8 474 544; inexact 73 952 010; tie 154 512; the leading limb of its output is not finite: nothing claimed 20 918 934 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 88 929 864 | 0 | exact 11 205 054; inexact 77 343 264; tie 344 448; the leading limb of its output is not finite: nothing claimed 14 607 234 | exact 11 004 480; inexact 76 627 602; tie 407 340; the leading limb of its output is not finite: nothing claimed 15 460 578 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, another exponent range) | 8 001 504 | 6 442 944 | 0 | exact 1 474 912; inexact 4 040 960; tie 801 664; the leading limb of its output is not finite: nothing claimed 1 683 968 | exact 960 372; inexact 4 404 456; tie 715 428; the leading limb of its output is not finite: nothing claimed 1 921 248 |
| `fp:3:-2:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 1 186 380 | 799 180 | 0 | exact 311 500; inexact 299 600; tie 149 440; the leading limb of its output is not finite: nothing claimed 425 840 | exact 202 800; inexact 334 932; tie 130 416; the leading limb of its output is not finite: nothing claimed 518 232 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, the quick tier's format) | 68 590 | 56 778 | 0 | exact 26 150; inexact 17 800; tie 10 360; the leading limb of its output is not finite: nothing claimed 14 280 | exact 19 038; inexact 20 900; tie 10 032; the leading limb of its output is not finite: nothing claimed 18 620 |
| `fp:1:-2:1`, every operand (p = min_precision, the quick tier's exponent range) | 3 645 | 3 441 | 0 | exact 1 845; inexact 820; tie 680; the leading limb of its output is not finite: nothing claimed 300 | exact 1 557; inexact 1 008; tie 648; the leading limb of its output is not finite: nothing claimed 432 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 413 334, atop 413 334, cancel 413 334, exactprod 206 666, extreme 206 666, overflow 206 666, pow2 206 666, tie 413 334, underflow 206 666, uniform 206 668, zero 206 666; `binary32`: apart 413 334, atop 413 334, cancel 413 334, exactprod 206 666, extreme 206 666, overflow 206 666, pow2 206 666, tie 413 334, underflow 206 666, uniform 206 668, zero 206 666.

### `acc_mul_entry_2`

Claims: `normalized(t)`; `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`; `rounded(b) nearest of a+abs(x[0])*abs(y[0])`.

| Run | Cases | Judged | Failed | largest error / bound | observed c | cases by rounding |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 5 759 622 | 0 | 0.478934 | 2.86698 | exact 334 494; inexact 5 406 894; tie 4 374; the leading limb of its output is not finite: nothing claimed 1 454 238 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 173 982 | 0 | 0.500000 | 2.89042 | exact 512 154; inexact 5 581 764; tie 21 006; the leading limb of its output is not finite: nothing claimed 1 085 076 |
| `fp:4:-3:-2`, restricted: `a.in=0x0p+0/0x1p-1/0x1.8p+0`, `s.lead=-1:0` (p = min_precision, the quick tier's format) | 267 912 | 157 540 | 0 | 0.372281 | - | exact 55 656; inexact 62 208; tie 29 184; the leading limb of its output is not finite: nothing claimed 120 864 |
| `fp:4:-3:-2`, restricted: `a.in=0x0p+0/0x1p-1/0x1.8p+0`, `s.lead=-1:0`, `x.lead=-1:0` (p = min_precision, the quick tier's format) | 105 408 | 82 312 | 0 | 0.350004 | - | exact 24 096; inexact 38 592; tie 13 728; the leading limb of its output is not finite: nothing claimed 28 992 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665; `binary32`: apart 33 333, atop 33 335, cancel 33 335, exactprod 16 665, extreme 16 665, overflow 16 667, pow2 16 665, tie 33 335, underflow 16 667, uniform 16 668, zero 16 665.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.500000 (clang-fixup-inline/cxx, macos-arm64):
  acc_mul_entry_2 binary32 -0x1.fffffcp-127 0x0p+0 0x1p+0 0x1.fffffcp-127 0x0p+0 -0x1.8p+0 -0x1p-24 #extreme:42958 -> -0x1.3ffffcp-125 -0x1p-149 0x1p+0
largest error / bound, interpreter 0.372281 (fp:4:-3:-2, restricted: a.in=0x0p+0/0x1p-1/0x1.8p+0, s.lead=-1:0):
  acc_mul_entry_2 fp:4:-3:-2 -0x1p-1 0x0p+0 0x0p+0 -0x1.4p+1 0x1p-3 -0x1.8p-2 0x0p+0 #exhaustive:123491 -> 0x1p-1 0x0p+0 0x1p+0
```

### `acc_radius_1`

Claims: `upper(r) >= g*(1+u)^2*(1+m*u+2*m^2*u^2)*(a+m*eta/2)+t if ok`; `holds le(m*u, 1/2) if ok`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 2.97499 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 2.95408 |
| `fp:4:-2:0`, every operand (quick tier + 1 bit) | 950 272 | 950 272 | 0 | 4.09326 |
| `fp:3:-2:0`, every operand (p = min_precision + 1, the quick tier's format) | 53 248 | 53 248 | 0 | 3.32617 |
| `fp:4:-4:2`, every operand (another exponent range) | 12 845 056 | 12 845 056 | 0 | 2.34497 |
| `fp:2:-1:1`, every operand (p = min_precision, another exponent range, replaces fp:2:-2:0, where constant up((1+u)^8) is not a number) (**stopped by a finding**: 8 suspicious non-finite results) | 0 | 0 | 0 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: abig 17 857, beyond 17 858, extreme 17 855, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: abig 17 857, beyond 17 858, extreme 17 855, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 2.95408 (msvc-fixup-call/cxx, windows-x64):
  acc_radius_1 binary32 0x1.03d01ep+124 0x1.4acp+10 0x1.0cbcp-13 0x1.4acp-138 #integer:58090 -> 0x1.10c2360000000p+111 1
smallest excess over the stated value, gaps, interpreter 2.34497 (fp:4:-4:2, every operand):
  acc_radius_1 fp:4:-4:2 0x1.cp-2 0x0p+0 0x1.ap+5 0x1.ep-1 #exhaustive:1408847 -> 0x1.2p+5 1
```

### `acc_radius_2`

Claims: `upper(r) >= g*(1+u)^2*(1+m*u+2*m^2*u^2)*(a+m*eta/2)+t if ok`; `holds le(m*u, 1/2) if ok`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 2.85298 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 2.90676 |
| `fp:3:-2:0`, every operand (p = min_precision + 1, the quick tier's format) | 53 248 | 53 248 | 0 | 3.32617 |
| `fp:4:-4:2`, every operand (another exponent range) | 12 845 056 | 12 845 056 | 0 | 2.34497 |
| `fp:4:-2:0`, every operand (quick tier + 1 bit) | 950 272 | 950 272 | 0 | 4.09326 |
| `fp:2:-1:1`, every operand (p = min_precision, another exponent range, replaces fp:2:-2:0, where constant up((1+u)^8) is not a number) (**stopped by a finding**: 8 suspicious non-finite results) | 0 | 0 | 0 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: abig 17 857, beyond 17 858, extreme 17 855, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: abig 17 857, beyond 17 858, extreme 17 855, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 2.85298 (clang18-fixup-call/cxx, linux-x86-64):
  acc_radius_2 binary64 0x1.3cb31265f19f4p+725 0x1.f16p+11 0x1.a23d25805bed5p-290 0x1.ef8d24399ae96p+382 #uniform:5908 -> 0x1.02b4048d425bdp+436 1
smallest excess over the stated value, gaps, interpreter 2.34497 (fp:4:-4:2, every operand):
  acc_radius_2 fp:4:-4:2 0x1.cp-2 0x0p+0 0x1.ap+5 0x1.ep-1 #exhaustive:1408847 -> 0x1.2p+5 1
```

### `add_1`

Claims: `entries(z) of the step add_1_1 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step add_1_1: rounded(s) nearest`; `entries(z), step add_1_1: error(s) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 72 000 | 72 000 | 0 | exact 7 208 940; inexact 13 263 858; tie 6 582 072 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 72 000 | 72 000 | 0 | exact 7 537 890; inexact 13 100 178; tie 6 937 164 | 1 (the claim) | 0.9999999404 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 468 997 | 468 997 | 0 | exact 350 597; inexact 162 708; tie 131 716 | 1 (the claim) | 0.8 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 765 | 1 765 | 0 | exact 745; inexact 360; tie 296 | 1 (the claim) | - |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 77 029 | 77 029 | 0 | exact 66 725; tie 9 420 | 1 (the claim) | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 358, exact 177, nonfinite 178, one 180, overflow 357, tie 180, tight 535, underflow 180, wide 178, zeros 177; `binary32`: cancel 358, exact 177, nonfinite 178, one 180, overflow 357, tie 180, tight 535, underflow 180, wide 178, zeros 177.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  add_1_1 binary64 -0x1p+368 -0x1p+315 #add_1:exact:150:element:543 -> -0x1p+368
largest error / bound, interpreter 1 (fp:2:-2:1, every operand):
  add_1_1 fp:2:-2:1 -0x1.8p+2 0x1p+0 #add_1:exhaustive:14:element:0 -> -0x1p+2
```

### `add_1_1`

Claims: `rounded(s) nearest`; `error(s) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 765 642 | 0 | exact 2 066 112; inexact 4 618 134; tie 81 396 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 769 008 | 0 | exact 2 238 750; inexact 4 420 224; tie 110 034 | 1 (the claim) | 0.9999999404 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | exact 835 201; inexact 3 981 696; tie 454 272 | 1 (the claim) | 0.992248 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 489 | 0 | exact 2 281; inexact 7 016; tie 1 192 | 1 (the claim) | 0.888889 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 573 | 0 | exact 565; inexact 1 716; tie 292 | 1 (the claim) | 0.8 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | exact 589 441; inexact 1 832 576; tie 310 912 | 1 (the claim) | 0.992248 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | exact 147 265; inexact 457 536; tie 77 632 | 1 (the claim) | 0.984615 |
| `fp:1:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 619 | 0 | exact 139; inexact 400; tie 80 | 1 (the claim) | 0.666667 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 31 250, halfgap 62 500, overflow 31 250, pow2 31 250, underflow 31 250, uniform 31 250, zero 31 250; `binary32`: extreme 31 250, halfgap 62 500, overflow 31 250, pow2 31 250, underflow 31 250, uniform 31 250, zero 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  add_1_1 binary64 -0x1p-1022 -0x1.0000000000001p-1022 #extreme:558 -> -0x1p-1021
largest error / bound, interpreter 1 (fp:7:-14:2, every operand):
  add_1_1 fp:7:-14:2 -0x1.fcp+8 0x1.f4p+7 #exhaustive:2236 -> -0x1p+8
```

### `add_1_entry`

Claims: `entries(z) of the step add_entry_step_1 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step add_entry_step_1: rounded(z) nearest`; `entries(z), step add_entry_step_1: error(z) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 72 000 | 72 000 | 0 | exact 7 341 312; inexact 13 944 666; tie 6 533 076 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 72 000 | 72 000 | 0 | exact 8 341 680; inexact 12 929 826; tie 6 332 250 | 1 (the claim) | 0.9999999404 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 468 997 | 468 997 | 0 | exact 350 597; inexact 162 708; tie 131 716 | 1 (the claim) | 0.8 |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 77 029 | 77 029 | 0 | exact 66 725; tie 9 420 | 1 (the claim) | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 765 | 1 765 | 0 | exact 745; inexact 360; tie 296 | 1 (the claim) | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 358, exact 177, nonfinite 178, one 180, overflow 357, tie 180, tight 535, underflow 180, wide 178, zeros 177; `binary32`: cancel 358, exact 177, nonfinite 178, one 180, overflow 357, tie 180, tight 535, underflow 180, wide 178, zeros 177.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  add_entry_step_1 binary64 0x1p-215 0x1p-268 #add_1_entry:exact:192:element:1376 -> 0x1p-215
largest error / bound, interpreter 1 (fp:2:-2:1, every operand):
  add_entry_step_1 fp:2:-2:1 -0x1.8p+2 0x1p+0 #add_1_entry:exhaustive:14:element:0 -> -0x1p+2
```

### `add_2`

Claims: `entries(z) of the step add_2_2 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step add_2_2: normalized(z)`; `entries(z), step add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 72 000 | 72 000 | 0 | 1 - ε, ε < 10⁻⁹ | 3.00000 |
| `binary32`, 90 runners on 3 machines | 72 000 | 72 000 | 0 | 0.9999995430 | 3.00000 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 988 037 | 988 037 | 0 | 0.453901 | - |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 1 elements) | 181 477 | 181 477 | 0 | 0.273504 | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 14 885 | 14 885 | 0 | 0.260163 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 335, exact 165, nonfinite 167, one 168, overflow 333, tail 165, tie 168, tight 500, underflow 167, wide 167, zeros 165; `binary32`: cancel 335, exact 165, nonfinite 167, one 168, overflow 333, tail 165, tie 168, tight 500, underflow 167, wide 167, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  add_2_2 binary64 -0x1p+58 -0x1.fffffffffffffp+4 0x1.fffffffffffffp+56 0x1.ffffffffffffep-50 #add_2:tight:7:element:4 -> -0x1.0000000000002p+57 0x1p+4
largest error / bound, interpreter 0.453901 (fp:4:-5:0, every operand):
  add_2_2 fp:4:-5:0 -0x1.ep+3 0x1.ep-2 0x1.6p+2 0x1.cp-3 #add_2:exhaustive:30499:element:0 -> -0x1.2p+3 0x1p-2
```

### `add_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 059 132 | 0 | 0.961748 | 1.92350 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 057 656 | 0 | 0.732914 | 1.46583 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.961748 (clang-fixup-inline/cxx, macos-arm64):
  add_2_1 binary64 -0x1.00000000001p+16 0x1.fffffffffffffp-38 0x1.eba2ddb8c99d9p+14 #extreme:41922 -> -0x1.0a2e91239b512p+15 -0x1p-38
largest error / bound, interpreter 0.939450 (fp:5:-6:3, every operand):
  add_2_1 fp:5:-6:3 -0x1p+7 -0x1.1p+1 0x1.fp+5 #exhaustive:847632 -> -0x1.1p+6 0x0p+0
```

### `add_2_1_full`

Claims: `extends(w) F1-F5, core add_2_1, lead add, finite when |x| <= 2^(qmax+p-2) and |a| <= 2^(qmax+p-2)`; `F2, core add_2_1: normalized(z)`; `F2, core add_2_1: error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.522384 | 1.04477 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.875497 | 1.75099 |
| `fp:4:-9:4`, every operand (p = min_precision + 1, another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.882759 | 1.76552 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0 | - |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0 | - |
| `fp:4:-5:0`, every operand (p = min_precision + 1, the quick tier's format) | 113 316 | 113 316 | 0 | 0.882759 | - |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.939450 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.780488 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888; `binary32`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.875497 (clang-fixup-inline/cxx, macos-arm64):
  add_2_1_full binary32 0x1.0ab64cp+126 0x1.17535ap+101 -0x1.e209bep+124 #overflow:3808 -> 0x1.2467bap+125 0x1.75358p+97
largest error / bound, interpreter 0.939450 (fp:5:-8:1, every operand):
  add_2_1_full fp:5:-8:1 -0x1p+5 -0x1.1p-1 0x1.fp+3 #exhaustive:854874 -> -0x1.1p+4 0x0p+0
```

### `add_2_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 054 200 | 0 | 0.473954 | 1.42186 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 054 092 | 0 | 0.623892 | 1.87168 |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.623892 (clang18-fixup-call/cxx, linux-x86-64):
  add_2_2 binary32 -0x1.00008p+85 -0x1.fffffep+60 0x1.dce786p+83 0x0p+0 #extreme:14034 -> -0x1.118d4p+84 0x1p+60
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  add_2_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 0x1.9p+5 0x1.cp-1 #exhaustive:128359 -> -0x1.1p+6 0x1p+0
```

### `add_2_2_full`

Claims: `extends(w) F1-F5, core add_2_2, lead add, finite when |x| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core add_2_2: normalized(z)`; `F2, core add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.666667 | 2.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.658694 | 1.97608 |
| `fp:4:-6:1`, every operand (p = min_precision + 1, another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.536013 | - |
| `fp:3:-6:3`, every operand (p = min_precision, another number of exponents) | 3 247 204 | 3 247 204 | 0 | 0.360255 | 2.16153 |
| `fp:4:-5:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 988 036 | 988 036 | 0 | 0.453901 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's format) | 181 476 | 181 476 | 0 | 0.273504 | - |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | 0.556176 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888; `binary32`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666667 (clang18-fixup-call/cxx, linux-x86-64):
  add_2_2_full binary64 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+969 -0x1.ffffffffffffdp+1022 0x1.219036c3b315dp+943 #edge:34629 -> 0x1.0000000000001p+1023 0x1.21903603b315dp+943
largest error / bound, interpreter 0.556176 (fp:5:-6:-1, every operand):
  add_2_2_full fp:5:-6:-1 -0x1.ep+3 0x1p-2 0x1.9p+2 0x1.cp-4 #exhaustive:128548 -> -0x1.1p+3 0x1p-3
```

### `add_2_entry`

Claims: `entries(z) of the step add_entry_step_2 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step add_entry_step_2: normalized(z)`; `entries(z), step add_entry_step_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1 - ε, ε < 10⁻⁹ | 3.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.9999995430 | 3.00000 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 988 037 | 988 037 | 0 | 0.453901 | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 14 885 | 14 885 | 0 | 0.260163 | - |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 1 elements) | 181 477 | 181 477 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  add_entry_step_2 binary64 0x1p+97 0x1.fffffffffffffp+43 -0x1.fffffffffffffp+95 -0x1.ffffffffffffep-11 #add_2_entry:tight:7:element:0 -> 0x1.0000000000002p+96 -0x1p+43
largest error / bound, interpreter 0.453901 (fp:4:-5:0, every operand):
  add_entry_step_2 fp:4:-5:0 -0x1.ep+3 0x1.ep-2 0x1.6p+2 0x1.cp-3 #add_2_entry:exhaustive:30499:element:0 -> -0x1.2p+3 0x1p-2
```

### `add_ball_2_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`; `encloses(z, d) x+y over `.

| Run | Cases | Judged | Failed | largest error / bound | observed c | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 995 718 | 0 | 0.666667 | 2.00000 | 2.25180e+15 | 1.50000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 989 814 | 0 | 0.666666 | 2.00000 | 4.19431e+6 | 1.50000 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - | 8.375 | 11.2 |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 | 4.28125 | 6.95652 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - | 8.75 | 28 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - | 16.875 | 96 |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - | 4.5 | 8 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666667 (msvc-fixup-call/cxx, windows-x64):
  add_ball_2_2 binary64 -0x1.fffffffffffffp+1023 -0x1.fffffffffffffp+969 0x1.ffffffffffffdp+1022 -0x1.1eb7297760093p+929 #overflow:20588 -> -0x1.0000000000001p+1023 -0x1.1e87297760093p+929 0x1.8000000000009p+918
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  add_ball_2_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 0x1.9p+5 0x1.cp-1 #exhaustive:128359 -> -0x1.1p+6 0x1p+0 0x1.8p+3
smallest radius slack, gaps, compiled 4.19431e+6 (clang18-fixup-call/cxx, linux-x86-64):
  add_ball_2_2 binary32 -0x1.fffffap+125 -0x1.0bed04p+90 0x1p+127 -0x1p+102 #overflow:53564 -> 0x1.000002p+126 -0x1.0c0d04p+90 0x1.800012p+79
smallest radius slack, gaps, interpreter 4.28125 (fp:3:-6:4, every operand):
  add_ball_2_2 fp:3:-6:4 -0x1.4p+6 0x1.cp+2 0x1.4p+4 -0x1.cp-2 #exhaustive:439266 -> -0x1.8p+5 -0x1p+2 0x1.4p+3
```

### `add_down_1`

Claims: `rounded(r) down`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 419 168; inexact, as RN 22 113 612; differs from RN 26 570 412; a NaN operand 4 460 256; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 039 656; overflow: value above Omega 8 906 526; overflow: value below -Omega 8 896 896; rounds to -inf 8 896 896; value NaN from operands that are not NaN 634 122 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 080 470; inexact, as RN 21 734 298; differs from RN 26 250 228; a NaN operand 4 469 238; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 030 674; overflow: value above Omega 8 918 046; overflow: value below -Omega 8 935 092; rounds to -inf 8 935 092; value NaN from operands that are not NaN 636 714 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to -inf 36; value NaN from operands that are not NaN 2 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to -inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to -inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to -inf 4 288; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to -inf 100; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `add_down_2_2`

Claims: `normalized(l)`; `outward(l) below, exact when (x+y = 0)`.

| Run | Cases | Judged | Failed | largest |output - value| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 987 060 | 0 | 0.687500 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 987 474 | 0 | 0.765624 |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 129 416 | 0 | 0.384391 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 077 026 | 0 | 0.444810 |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 644 866 | 0 | 0.389454 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 2 880 089 | 0 | 0.474531 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 689 555 | 0 | 0.447941 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest |output - value| / allowance, compiled 0.765624 (msvc-fixup-call/cxx, windows-x64):
  add_down_2_2 binary32 -0x1p+127 -0x1.fffffep+102 0x1.fffffep+125 0x1.0c70f2p+98 #overflow:19740 -> -0x1.0000020000000p+126 -0x1.de71ea0000000p+101
largest |output - value| / allowance, interpreter 0.474531 (fp:5:-3:2, every operand):
  add_down_2_2 fp:5:-3:2 -0x1.fp+4 0x0p+0 0x1.fp+6 0x1.ep+0 #exhaustive:1531399 -> 0x1.4p+6 -0x1p+1
```

### `add_down_entry`

Claims: `rounded(r) down`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 394 310; inexact, as RN 22 082 778; differs from RN 26 617 086; a NaN operand 4 472 982; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 026 930; overflow: value above Omega 8 938 926; overflow: value below -Omega 8 905 914; rounds to -inf 8 905 914; value NaN from operands that are not NaN 648 504 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 078 634; inexact, as RN 21 675 042; differs from RN 26 288 226; a NaN operand 4 484 088; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 015 824; overflow: value above Omega 8 902 818; overflow: value below -Omega 8 958 186; rounds to -inf 8 958 186; value NaN from operands that are not NaN 638 730 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to -inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to -inf 4 288; value NaN from operands that are not NaN 2 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to -inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to -inf 100; value NaN from operands that are not NaN 2 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to -inf 36; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `add_entry_step_1`

Claims: `rounded(z) nearest`; `error(z) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 97 209 720 | 0 | exact 29 600 820; inexact 66 447 882; tie 1 161 018 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 97 215 228 | 0 | exact 32 090 976; inexact 63 529 722; tie 1 594 530 | 1 (the claim) | 0.9999999404 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 489 | 0 | exact 2 281; inexact 7 016; tie 1 192 | 1 (the claim) | 0.888889 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 573 | 0 | exact 565; inexact 1 716; tie 292 | 1 (the claim) | 0.8 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | exact 835 201; inexact 3 981 696; tie 454 272 | 1 (the claim) | 0.992248 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | exact 589 441; inexact 1 832 576; tie 310 912 | 1 (the claim) | 0.992248 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | exact 147 265; inexact 457 536; tie 77 632 | 1 (the claim) | 0.984615 |
| `fp:1:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 619 | 0 | exact 139; inexact 400; tie 80 | 1 (the claim) | 0.666667 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  add_entry_step_1 binary64 0x1p-1022 0x1.0000000000001p-1022 #extreme:110 -> 0x1p-1021
largest error / bound, interpreter 1 (fp:3:-7:4, every operand):
  add_entry_step_1 fp:3:-7:4 -0x1.cp+6 0x1.4p+5 #exhaustive:96 -> -0x1p+6
```

### `add_entry_step_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 100 569 834 | 0 | 0.666667 | 2.00000 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 100 562 022 | 0 | 0.676456 | 2.02937 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165; `binary32`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.676456 (clang18-fixup-call/cxx, linux-x86-64):
  add_entry_step_2 binary32 -0x1.1daf3ap+127 0x1.a9c212p+102 0x1.fffffap+125 0x1.08001p+97 #overflow:1180906 -> -0x1.3b5e76p+126 0x1.64042p+101
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  add_entry_step_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 0x1.9p+5 0x1.cp-1 #exhaustive:128359 -> -0x1.1p+6 0x1p+0
```

### `add_fast_2_2`

Claims: `normalized(z)`; `error(z) form A, c=3, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 061 616 | 0 | 0.499997 | 1.49999 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 060 896 | 0 | 0.500000 | 1.50000 |
| `fp:4:-4:3`, every operand (another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.671916 | - |
| `fp:3:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 178 929 | 138 027 | 0 | 0.465793 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's exponent range) | 25 281 | 20 449 | 0 | 0.313725 | 0.941176 |
| `fp:3:-6:4`, every operand (p = min_precision + 1, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.487062 | 1.46119 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.562328 | - |
| `fp:4:-3:2`, every operand (quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.487619 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.500000 (clang-fixup-inline/cxx, macos-arm64):
  add_fast_2_2 binary32 -0x1p-9 -0x1p-33 -0x1.24aadap-34 -0x1.fffffep-59 #extreme:19770 -> -0x1.000002p-9 0x1.b6aa5p-35
largest error / bound, interpreter 0.671916 (fp:4:-4:3, every operand):
  add_fast_2_2 fp:4:-4:3 -0x1.2p+6 0x1.ep+1 -0x1.4p+4 0x1.ep-1 #exhaustive:1228016 -> -0x1.6p+6 0x0p+0
```

### `add_fast_2_2_full`

Claims: `extends(w) F1-F5, core add_fast_2_2, lead add, finite when |x| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core add_fast_2_2: normalized(z)`; `F2, core add_fast_2_2: error(z) form A, c=3, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.498875 | 1.49662 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.493425 | 1.48027 |
| `fp:3:-6:3`, every operand (p = min_precision + 1, another number of exponents) | 3 247 204 | 3 247 204 | 0 | 0.487062 | 1.46119 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 181 476 | 181 476 | 0 | 0.465793 | - |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.671916 | - |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | 0.562328 | - |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | 0.487619 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | 0.313725 | 0.941176 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888; `binary32`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.498875 (msvc-fixup-call/cxx, windows-x64):
  add_fast_2_2_full binary64 -0x1.00002001p+388 0x1.09acb040cd67bp+334 0x1p+335 -0x1.fc8bbdc63e872p+280 #pow2:24521 -> -0x1.00002000fffffp+388 -0x1.eca69f7e65308p+333
largest error / bound, interpreter 0.671916 (fp:4:-6:1, every operand):
  add_fast_2_2_full fp:4:-6:1 -0x1.2p+4 0x1.ep-1 -0x1.4p+2 0x1.ep-3 #exhaustive:1229354 -> -0x1.6p+4 0x0p+0
```

### `add_up_1`

Claims: `rounded(r) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 374 384; inexact, as RN 22 109 472; differs from RN 26 580 690; a NaN operand 4 464 468; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 035 444; overflow: value above Omega 8 935 542; overflow: value below -Omega 8 887 878; rounds to inf 8 935 542; value NaN from operands that are not NaN 636 588 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 084 412; inexact, as RN 21 701 286; differs from RN 26 285 256; a NaN operand 4 486 482; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 013 430; overflow: value above Omega 8 929 134; overflow: value below -Omega 8 906 454; rounds to inf 8 929 134; value NaN from operands that are not NaN 638 802 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to inf 4 288; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to inf 100; value NaN from operands that are not NaN 2 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to inf 36; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `add_up_2_2`

Claims: `normalized(h)`; `outward(h) above, exact when (x+y = 0)`.

| Run | Cases | Judged | Failed | largest |output - value| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 994 800 | 0 | 0.750000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 991 218 | 0 | 0.665674 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 689 555 | 0 | 0.447941 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 077 026 | 0 | 0.444810 |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 644 866 | 0 | 0.389454 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 2 880 089 | 0 | 0.474531 |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 129 416 | 0 | 0.384391 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest |output - value| / allowance, compiled 0.750000 (clang18-fixup-call/cxx, linux-x86-64):
  add_up_2_2 binary64 0x1p+1023 0x1.fffffffffffffp+969 -0x1.fffffffffffffp+1021 -0x1.54c56403ff609p+133 #overflow:32876 -> 0x1.0000000000002p+1022 -0x1.ffffffffffffcp+968
largest |output - value| / allowance, interpreter 0.474531 (fp:5:-3:2, every operand):
  add_up_2_2 fp:5:-3:2 -0x1.fp+6 -0x1.ep+0 0x1.fp+4 0x0p+0 #exhaustive:1255 -> -0x1.4p+6 0x1p+1
```

### `add_up_entry`

Claims: `rounded(r) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 421 400; inexact, as RN 22 113 036; differs from RN 26 571 168; a NaN operand 4 470 372; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 029 540; overflow: value above Omega 8 894 484; overflow: value below -Omega 8 926 884; rounds to inf 8 894 484; value NaN from operands that are not NaN 644 472 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 095 122; inexact, as RN 21 654 864; differs from RN 26 318 502; a NaN operand 4 475 718; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 024 194; overflow: value above Omega 8 931 600; overflow: value below -Omega 8 915 724; rounds to inf 8 931 600; value NaN from operands that are not NaN 636 516 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to inf 4 288; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to inf 100; value NaN from operands that are not NaN 2 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to inf 36; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `axpy_1`

Claims: `entries(z) of the step axpy_step_1 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_step_1: error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1 - ε, ε < 10⁻⁹ | 2.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.9999998510 | 2.00000 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 195 170 | 195 170 | 0 | 0.837750 | 1.6 |
| `fp:2:-1:0`, every operand (another format, every array up to 2 elements) | 1 078 406 | 1 078 406 | 0 | 0.563910 | - |
| `fp:3:-3:0`, every operand (the full tier's format, every array up to 1 elements) | 74 130 | 74 130 | 0 | 0.796069 | 0.525547 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141; `binary32`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  axpy_step_1 binary64 -0x1.0000000000001p+40 -0x1.fffffffffffffp+979 0x1p+967 #axpy_1:tight:133:element:1572 -> 0x1p+1020
largest error / bound, interpreter 0.837750 (fp:3:-4:1, every operand):
  axpy_step_1 fp:3:-4:1 0x1.8p-1 -0x1.8p+3 -0x1p+0 #axpy_1:exhaustive:4329:element:0 -> -0x1p+3
```

### `axpy_1_entry`

Claims: `entries(z) of the step axpy_entry_step_1 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_entry_step_1: error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1 - ε, ε < 10⁻⁹ | 2.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.9999998510 | 2.00000 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 195 170 | 195 170 | 0 | 0.837750 | 1.6 |
| `fp:3:-3:0`, every operand (the full tier's format, every array up to 1 elements) | 74 130 | 74 130 | 0 | 0.796069 | 0.525547 |
| `fp:2:-1:0`, every operand (another format, every array up to 2 elements) | 1 078 406 | 1 078 406 | 0 | 0.563910 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141; `binary32`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  axpy_entry_step_1 binary64 -0x1.0000000000001p+47 -0x1.fffffffffffffp+972 0x1p+967 #axpy_1_entry:tight:99:element:1148 -> 0x1p+1020
largest error / bound, interpreter 0.837750 (fp:3:-4:1, every operand):
  axpy_entry_step_1 fp:3:-4:1 0x1.8p-1 -0x1.8p+3 -0x1p+0 #axpy_1_entry:exhaustive:4329:element:0 -> -0x1p+3
```

### `axpy_2`

Claims: `entries(z) of the step axpy_step_2 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_step_2: normalized(z)`; `entries(z), step axpy_step_2: error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.725987 | 3.99790 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.681521 | 3.22288 |
| `fp:4:-4:-1`, every operand (another format, every array up to 1 elements) | 15 625 250 | 15 625 250 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (the full tier's format, every array up to 1 elements) | 262 208 | 262 208 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.725987 (msvc/avx2, windows-x64):
  axpy_step_2 binary64 0x1.65e13cf1f27a4p-978 0x1.1754d07a9ep-1035 -0x1.315471513990ep-20 0x1.17f98580a7b98p-75 0x1.ffffffffffffep-1023 0x0p+0 #axpy_2:underflow:215:element:4080 -> -0x1.aad764ee39ebfp-998 -0x0.00000006f3b4dp-1022
largest error / bound, interpreter 0.399878 (fp:4:-4:-1, every operand):
  axpy_step_2 fp:4:-4:-1 -0x1.cp-2 0x0p+0 -0x1.8p+0 -0x1p-4 0x0p+0 0x0p+0 #axpy_2:exhaustive:6156116:element:0 -> 0x1.4p-1 0x0p+0
```

### `axpy_2_1`

Claims: `entries(z) of the step axpy_step_2_1 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_step_2_1: normalized(z)`; `entries(z), step axpy_step_2_1: error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.799644 | 2.10511 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.798986 | 2.22795 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 625 170 | 625 170 | 0 | 0.467001 | - |
| `fp:3:-2:-1`, every operand (the full tier's format, every array up to 1 elements) | 26 650 | 26 650 | 0 | 0.380528 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.799644 (msvc/avx2, windows-x64):
  axpy_step_2_1 binary64 -0x1.3d8a3c944ap-1035 -0x1.2e62a50c07d41p+51 -0x1.6772ee224e06cp-10 -0x0p+0 -0x0p+0 #axpy_2_1:underflow:410:element:539 -> 0x1.77136f1b254c9p-984 0x0.00002b90ddf6ep-1022
largest error / bound, interpreter 0.467001 (fp:3:-3:0, every operand):
  axpy_step_2_1 fp:3:-3:0 -0x1.8p-2 -0x1.8p+0 -0x1p-3 0x0p+0 0x0p+0 #axpy_2_1:exhaustive:238240:element:0 -> 0x1p-1 0x0p+0
```

### `axpy_2_1_entry`

Claims: `entries(z) of the step axpy_entry_step_2_1 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_entry_step_2_1: normalized(z)`; `entries(z), step axpy_entry_step_2_1: error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.790344 | 2.31608 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.789488 | 2.31682 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 625 170 | 625 170 | 0 | 0.467001 | - |
| `fp:3:-2:-1`, every operand (the full tier's format, every array up to 1 elements) | 26 650 | 26 650 | 0 | 0.380528 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.790344 (clang18/avx2, linux-x86-64):
  axpy_entry_step_2_1 binary64 0x1.8a70eaa5cp-1040 0x1.8bba8f4d4304p+45 0x1.4e527301eab09p-10 -0x1p-1074 -0x0p+0 #axpy_2_1_entry:underflow:155:element:1505 -> 0x1.30ddd6722cfc3p-994 0x0.0000002a70447p-1022
largest error / bound, interpreter 0.467001 (fp:3:-3:0, every operand):
  axpy_entry_step_2_1 fp:3:-3:0 -0x1.8p-2 -0x1.8p+0 -0x1p-3 0x0p+0 0x0p+0 #axpy_2_1_entry:exhaustive:238240:element:0 -> 0x1p-1 0x0p+0
```

### `axpy_2_entry`

Claims: `entries(z) of the step axpy_entry_step_2 on a, x, y`; `finite_or_nan(z) flag finite`; `entries(z), step axpy_entry_step_2: normalized(z)`; `entries(z), step axpy_entry_step_2: error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.729670 | 3.99790 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.694813 | 2.94007 |
| `fp:4:-4:-1`, every operand (another format, every array up to 1 elements) | 15 625 250 | 15 625 250 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (the full tier's format, every array up to 1 elements) | 262 208 | 262 208 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.729670 (clang18-fixup-call/cxx, linux-x86-64):
  axpy_entry_step_2 binary64 0x1.9a040e0a7c703p-1016 0x1p-1074 0x1.69651a617d11cp+26 0x1.8fdfa9eefc284p-28 -0x1.ffffffffffffep-1023 0x0p+0 #axpy_2_entry:underflow:5:element:337 -> 0x1.2168d2d2f0721p-989 0x0.0000018eb6d43p-1022
largest error / bound, interpreter 0.399878 (fp:4:-4:-1, every operand):
  axpy_entry_step_2 fp:4:-4:-1 -0x1.cp-2 0x0p+0 -0x1.8p+0 -0x1p-4 0x0p+0 0x0p+0 #axpy_2_entry:exhaustive:6156116:element:0 -> 0x1.4p-1 0x0p+0
```

### `axpy_entry_step_1`

Claims: `error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 95 962 122 | 0 | 1 - ε, ε < 10⁻⁹ | 2.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 96 111 594 | 0 | 0.9999998510 | 2.00000 |
| `fp:4:-6:-1`, every operand (quick tier + 1 bit) | 1 367 631 | 1 206 959 | 0 | 0.849778 | 1.67832 |
| `fp:3:-8:1`, every operand (p = min_precision + 2, another exponent range) | 658 503 | 609 683 | 0 | 0.851686 | 1.6 |
| `fp:1:-6:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 197 | 2 193 | 0 | 0.473684 | 0.666667 |
| `fp:3:-6:-1`, every operand (p = min_precision + 2, the quick tier's format) | 166 375 | 156 755 | 0 | 0.837750 | 1.6 |
| `fp:2:-6:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 19 683 | 19 387 | 0 | 0.609343 | 1.09091 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 581 250, exactprod 193 750, extreme 193 750, overflow 193 750, pow2 193 750, state 387 500, tie 193 750, tight 581 250, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: cancel 581 250, exactprod 193 750, extreme 193 750, overflow 193 750, pow2 193 750, state 387 500, tie 193 750, tight 581 250, underflow 193 750, uniform 193 750, zero 193 750.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  axpy_entry_step_1 binary64 0x1.0000000000001p+340 0x1.fffffffffffffp+678 0x1p+966 #tight:68407 -> 0x1p+1019
largest error / bound, interpreter 0.851686 (fp:3:-8:1, every operand):
  axpy_entry_step_1 fp:3:-8:1 -0x1.8p+3 -0x1.8p-1 0x1p+0 #exhaustive:9119 -> 0x1p+3
```

### `axpy_entry_step_2`

Claims: `normalized(z)`; `error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 666 768 | 0 | 0.645231 | 3.99790 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 667 254 | 0 | 0.637695 | 2.59708 |
| `fp:5:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 953 125 | 602 249 | 0 | 0.417584 | - |
| `fp:4:-4:-2`, every operand (p = min_precision, another exponent range) | 1 860 867 | 902 883 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (p = min_precision, the quick tier's format) | 226 981 | 111 361 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.645231 (clang-fixup-inline/cxx, macos-arm64):
  axpy_entry_step_2 binary64 -0x1.72bb4082fb73dp-159 -0x1.01004p-230 -0x1.23cdcb69c3317p-842 0x1.0000000080004p-902 -0x1.493492d8299p-1030 -0x0p+0 #underflow:40968 -> 0x1.a694e0d0e8b4fp-1001 0x1.e8078p-1055
largest error / bound, interpreter 0.417584 (fp:5:-3:-2, every operand):
  axpy_entry_step_2 fp:5:-3:-2 -0x1.2p+2 0x1p-3 -0x1.8p-2 0x0p+0 0x0p+0 0x0p+0 #exhaustive:429312 -> 0x1.cp+0 0x0p+0
```

### `axpy_entry_step_2_1`

Claims: `normalized(z)`; `error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 667 902 | 0 | 0.780555 | 1.98467 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 673 086 | 0 | 0.767880 | 1.42614 |
| `fp:3:-5:-3`, every operand (p = min_precision, the quick tier's format) | 107 911 | 98 303 | 0 | 0.504720 | - |
| `fp:4:-5:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 953 127 | 765 439 | 0 | 0.641498 | - |
| `fp:3:-6:-3`, every operand (p = min_precision, another exponent range) | 552 279 | 509 443 | 0 | 0.504720 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.780555 (msvc-fixup-call/cxx, windows-x64):
  axpy_entry_step_2_1 binary64 -0x1.4792d0afe3328p-837 0x1.443802278912ap-151 -0x1.1468389279d59p-207 0x1.a2212d228p-1040 -0x0p+0 #underflow:97304 -> -0x1.9edd7afdfe6a1p-988 -0x0.00000b5b3a711p-1022
largest error / bound, interpreter 0.641498 (fp:4:-5:-3, every operand):
  axpy_entry_step_2_1 fp:4:-5:-3 -0x1.ap-2 -0x1p-1 -0x1p-5 0x0p+0 0x0p+0 #exhaustive:277795 -> 0x1.8p-3 0x0p+0
```

### `axpy_step_1`

Claims: `error(z) form T, c=(2+3*u)/((1+u)*(1+u)), k=1, t=2/3`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 95 965 758 | 0 | 1 - ε, ε < 10⁻⁹ | 2.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 96 114 312 | 0 | 0.9999998510 | 2.00000 |
| `fp:3:-6:-1`, every operand (p = min_precision + 2, the quick tier's format) | 166 375 | 156 755 | 0 | 0.837750 | 1.6 |
| `fp:4:-6:-1`, every operand (quick tier + 1 bit) | 1 367 631 | 1 206 959 | 0 | 0.849778 | 1.67832 |
| `fp:3:-8:1`, every operand (p = min_precision + 2, another exponent range) | 658 503 | 609 683 | 0 | 0.851686 | 1.6 |
| `fp:2:-6:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 19 683 | 19 387 | 0 | 0.609343 | 1.09091 |
| `fp:1:-6:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 197 | 2 193 | 0 | 0.473684 | 0.666667 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 581 250, exactprod 193 750, extreme 193 750, overflow 193 750, pow2 193 750, state 387 500, tie 193 750, tight 581 250, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: cancel 581 250, exactprod 193 750, extreme 193 750, overflow 193 750, pow2 193 750, state 387 500, tie 193 750, tight 581 250, underflow 193 750, uniform 193 750, zero 193 750.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  axpy_step_1 binary64 0x1.0000000000001p+38 0x1.fffffffffffffp+980 0x1p+966 #tight:70759 -> 0x1p+1019
largest error / bound, interpreter 0.851686 (fp:3:-8:1, every operand):
  axpy_step_1 fp:3:-8:1 -0x1.8p+3 -0x1.8p-1 0x1p+0 #exhaustive:9119 -> 0x1p+3
```

### `axpy_step_2`

Claims: `normalized(z)`; `error(z) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 669 288 | 0 | 0.631500 | 3.99790 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 671 394 | 0 | 0.700851 | 2.86122 |
| `fp:5:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 953 125 | 602 249 | 0 | 0.417584 | - |
| `fp:4:-4:-2`, every operand (p = min_precision, another exponent range) | 1 860 867 | 902 883 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (p = min_precision, the quick tier's format) | 226 981 | 111 361 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.700851 (clang18-fixup-call/cxx, linux-x86-64):
  axpy_step_2 binary32 -0x1.5ed222p-69 -0x1.4111c8p-94 0x1.3033ccp-41 0x1.abaa7p-66 -0x1.25453ap-124 0x1p-149 #underflow:86168 -> -0x1.a0e51ap-110 -0x1.89dcp-135
largest error / bound, interpreter 0.417584 (fp:5:-3:-2, every operand):
  axpy_step_2 fp:5:-3:-2 -0x1.2p+2 0x1p-3 -0x1.8p-2 0x0p+0 0x0p+0 0x0p+0 #exhaustive:429312 -> 0x1.cp+0 0x0p+0
```

### `axpy_step_2_1`

Claims: `normalized(z)`; `error(z) form T, c=3*(1+2*u*u)/(1-4*u)+2, k=2, t=5/4`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 666 768 | 0 | 0.800000 | 1.98467 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 669 342 | 0 | 0.800000 | 1.45174 |
| `fp:4:-5:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 953 127 | 765 439 | 0 | 0.641498 | - |
| `fp:3:-6:-3`, every operand (p = min_precision, another exponent range) | 552 279 | 509 443 | 0 | 0.504720 | - |
| `fp:3:-5:-3`, every operand (p = min_precision, the quick tier's format) | 107 911 | 98 303 | 0 | 0.504720 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: cancel 46 875, exactprod 15 625, extreme 15 625, overflow 15 625, pow2 15 625, state 31 250, tie 15 625, tight 46 875, underflow 15 625, uniform 15 625, zero 15 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.800000 (clang-fixup-inline/cxx, macos-arm64):
  axpy_step_2_1 binary64 -0x1.ffffffffffffep-1023 0x1.80000000002p+0 0x1p-53 -0x1.0000000000001p-1022 0x0p+0 #extreme:40558 -> -0x1.40000000001p-1021 0x1p-1074
largest error / bound, interpreter 0.641498 (fp:4:-5:-3, every operand):
  axpy_step_2_1 fp:4:-5:-3 -0x1.ap-2 -0x1p-1 -0x1p-5 0x0p+0 0x0p+0 #exhaustive:277795 -> 0x1.8p-3 0x0p+0
```

### `ball_add_1`

Claims: `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 633 918 | 0 | 1.37500 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 632 478 | 0 | 1 | 1.000000101 |
| `fp:2:-6:4`, every operand (p = min_precision + 1, another exponent range) | 1 272 384 | 994 044 | 0 | 1 | 1.33333 |
| `fp:3:-3:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 1 272 384 | 807 559 | 0 | 1 | 1.2 |
| `fp:4:-3:1`, every operand (quick tier + 2 bits) | 20 793 600 | 14 367 516 | 0 | 1.625 | 1.20930 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, another exponent range) | 4 064 256 | 3 025 751 | 0 | 1 | 1.2 |
| `fp:1:-5:5`, every operand (p = min_precision, another exponent range) | 76 176 | 38 639 | 0 | 1.3125 | 2.90909 |
| `fp:2:-3:1`, every operand (p = min_precision + 1, the quick tier's format) | 76 176 | 38 412 | 0 | 1 | 1.33333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang-fixup-inline/cxx, macos-arm64):
  ball_add_1 binary32 -0x1.fffffap+126 0x1.01p+127 0x1.fffffep+127 0x1.6f4608p+124 #overflow:49136 -> 0x1p+127 0x1.2ee8c4p+127
smallest radius slack, gaps, interpreter 1 (fp:2:-6:4, every operand):
  ball_add_1 fp:2:-6:4 -0x1p+5 0x1p+2 0x1.8p+3 0x1p+4 #exhaustive:46148 -> -0x1p+4 0x1p+5
```

### `ball_add_1_full`

Claims: `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx+cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.25 | 1.00000 | 3 776 760 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.25 | 1.000000142 | 3 726 216 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1 | 1.2 | 397 403 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 1 | 1.33333 | 363 535 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 1 | 1.33333 | 27 055 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736; `binary32`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25 (msvc-fixup-call/cxx, windows-x64):
  ball_add_1_full binary64 -0x1.fb9531717489dp+1022 0x1p+1022 0x1.fffffffffffffp+1023 0x1.ffffffffffffdp+1021 #hugeradius:1838 -> 0x1.0235674745bb0p+1023 0x1.0000000000001p+1023
smallest radius slack, gaps, interpreter 1 (fp:3:-4:1, every operand):
  ball_add_1_full fp:3:-4:1 -0x1.cp+3 0x1p+0 0x1.4p+2 0x1p+3 #exhaustive:19872 -> -0x1p+3 0x1.8p+3
```

### `ball_add_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 670 062 | 0 | 1.28825 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 667 956 | 0 | 1.25548 | 1.000000143 |
| `fp:3:-3:1`, every operand (p = min_precision, another exponent range) | 32 901 696 | 15 977 235 | 0 | 1.4375 | 1.31507 |
| `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` (p = min_precision, the quick tier's format) | 8 767 521 | 4 968 972 | 0 | 1.46875 | 1.41593 |
| `fp:3:-3:2`, restricted: `cx.lead=-1:0` (p = min_precision, the quick tier's format) | 7 295 904 | 5 136 540 | 0 | 1.25 | 1.31507 |
| `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision + 1, quick tier + 1 bit) | 15 713 296 | 11 654 256 | 0 | 3.75 | 1.5 |
| `fp:3:-2:1`, every operand (p = min_precision, another exponent range) | 5 664 400 | 2 192 431 | 0 | 1.75 | 1.52381 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25548 (msvc-fixup-call/cxx, windows-x64):
  ball_add_2 binary32 -0x1.57c1a8p+95 0x1.773f2cp+66 0x1.fffffep+125 0x1.57c1a8p+95 -0x1.ad4894p+59 0x1.f4c934p+100 #cancel:71116 -> 0x1.73e49a0000000p+66 0x1.b000000000000p+41 0x1.0000020000000p+126
smallest radius slack, gaps, interpreter 1.25 (fp:3:-3:2, restricted: cx.lead=-1:0):
  ball_add_2 fp:3:-3:2 -0x1.cp+0 0x0p+0 0x1.cp-1 0x1p+3 0x1.cp-1 0x1.cp+3 #exhaustive:90827 -> 0x1.cp+2 0x0p+0 0x1.4p+4
```

### `ball_add_2_full`

Claims: `encloses(cw, rw) x+y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx+cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.30466 | 1.00000 | 4 034 340 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.25026 | 1.000000143 | 3 973 050 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 | 1.75 | 1.52381 | 176 623 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 | 2 | 1.52381 | 472 949 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 | 5.5 | 1.76471 | 16 725 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736; `binary32`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25026 (clang18-fixup-call/cxx, linux-x86-64):
  ball_add_2_full binary32 0x0p+0 0x0p+0 0x1.fffffcp+125 0x1.06faep+127 -0x1p+103 0x1.7fddb8p+102 #extreme:35845 -> 0x1.06faep+127 -0x1p+103 0x1.000002p+126
smallest radius slack, gaps, interpreter 1.75 (fp:3:-3:0, every operand):
  ball_add_2_full fp:3:-3:0 -0x1.cp+2 -0x1.8p-2 0x1p-2 0x1.4p+2 0x1p-3 0x1.8p+1 #exhaustive:6778 -> -0x1p+1 -0x1p-2 0x1.4p+2
```

### `ball_contains_ball_1`

Claims: `certain(m) subset(y, x) over x=[cx +- rx], y=[cy +- ry], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221; `binary32`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221.

### `ball_contains_ball_2`

Claims: `certain(m) subset(y, x) over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 27 780, boundary 27 780, extreme 13 887, huge 27 780, near 27 780, overflow 13 887, points 27 778, pow2 13 887, underflow 13 888, uniform 13 890, wide 27 776, zero 13 887; `binary32`: ballstates 27 780, boundary 27 780, extreme 13 887, huge 27 780, near 27 780, overflow 13 887, points 27 778, pow2 13 887, underflow 13 888, uniform 13 890, wide 27 776, zero 13 887.

### `ball_contains_point_1`

Claims: `certain(m) member(t, x) over x=[c +- r], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 708 852 | 708 852 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 89 436 | 89 436 | 0 |
| `fp:3:-6:3`, every operand (p = min_precision + 1, another number of exponents) | 344 700 | 344 700 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 11 400 | 11 400 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 387 500, boundary 387 500, extreme 193 750, huge 387 500, near 387 500, overflow 193 750, points 387 500, pow2 193 750, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: ballstates 387 500, boundary 387 500, extreme 193 750, huge 387 500, near 387 500, overflow 193 750, points 387 500, pow2 193 750, underflow 193 750, uniform 193 750, zero 193 750.

### `ball_contains_point_2`

Claims: `trit(yes yes, no no) member(t, x) over x=[c +- r]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision, another number of exponents) | 5 046 396 | 5 046 396 | 0 |
| `fp:4:-4:-1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 470 500 | 2 470 500 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision, the quick tier's format) | 290 604 | 290 604 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 381 250, boundary 381 250, extreme 190 625, huge 381 250, near 381 250, overflow 190 625, points 381 250, pow2 190 625, underflow 190 625, uniform 190 625, zero 190 625; `binary32`: ballstates 381 250, boundary 381 250, extreme 190 625, huge 381 250, near 381 250, overflow 190 625, points 381 250, pow2 190 625, underflow 190 625, uniform 190 625, zero 190 625.

### `ball_equal_1`

Claims: `trit(yes yes, no no) eq(x, y) over x=[cx +- rx], y=[cy +- ry], exact when |rx+ry| <= Omega`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221; `binary32`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221.

### `ball_equal_2`

Claims: `trit(yes yes, no no) eq(x, y) over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 338 892, boundary 338 891, extreme 169 443, huge 338 889, near 338 890, overflow 169 443, points 338 888, pow2 169 443, underflow 169 444, uniform 169 446, wide 338 888, zero 169 443; `binary32`: ballstates 338 892, boundary 338 891, extreme 169 443, huge 338 889, near 338 890, overflow 169 443, points 338 888, pow2 169 443, underflow 169 444, uniform 169 446, wide 338 888, zero 169 443.

### `ball_from_interval_1`

Claims: `makes_ball(cw, rw) from the interval of lower lo, upper hi, the center within rel u, abs eta of the midpoint, the smallest radius`.

| Run | Cases | Judged | Failed | largest |center - midpoint| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 0.9999999404 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | 0.992248 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | 0.984615 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | 0.8 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | 0.992248 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | 0.888889 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 172 221, infinities 344 446, nanbound 344 446, oddeta 344 444, overflow 172 221, point 344 445, pow2 172 221, reversed 344 446, top 344 444, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: extreme 172 221, infinities 344 446, nanbound 344 446, oddeta 344 444, overflow 172 221, point 344 445, pow2 172 221, reversed 344 446, top 344 444, underflow 172 222, uniform 172 223, zero 172 221.

Where the extremes are attained (the line as the oracle reports it):

```
largest |center - midpoint| / allowance, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64):
  ball_from_interval_1 binary64 -0x1.0000000000001p-1022 0x1.ffffffffffffep-1023 #extreme:1331 -> 0x0p+0 0x1.0000000000001p-1022
largest |center - midpoint| / allowance, interpreter 0.992248 (fp:7:-9:-2, every operand):
  ball_from_interval_1 fp:7:-9:-2 -0x1.fcp-3 0x1.f4p-3 #exhaustive:517692 -> -0x1p-8 0x1.fcp-3
```

### `ball_from_interval_2`

Claims: `makes_ball(cw, rw) from the interval of lower lo, upper hi, the midpoint when lo/2 is a number of the format and hi/2 is a number of the format`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 172 221, infinities 344 446, nanbound 344 446, oddeta 344 444, overflow 172 221, point 344 445, pow2 172 221, reversed 344 446, top 344 444, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: extreme 172 221, infinities 344 446, nanbound 344 446, oddeta 344 444, overflow 172 221, point 344 445, pow2 172 221, reversed 344 446, top 344 444, underflow 172 222, uniform 172 223, zero 172 221.

### `ball_hull_1`

Claims: `ball_set(cz, rz) union of x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362; `binary32`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362.

### `ball_hull_2`

Claims: `ball_set(cz, rz) union of x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362; `binary32`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362.

### `ball_intersection_1`

Claims: `ball_set(cz, rz) intersection of x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362; `binary32`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362.

### `ball_intersection_2`

Claims: `ball_set(cz, rz) intersection of x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362; `binary32`: ballstates 22 730, bothspecial 22 730, disjoint 22 730, extreme 11 362, nested 22 728, overflow 11 362, overlap 22 726, point 22 725, pow2 11 362, touch 22 730, underflow 11 362, uniform 11 365, wide 22 726, zero 11 362.

### `ball_less_1`

Claims: `trit(yes yes, no no) lt(x, y) over x=[cx +- rx], y=[cy +- ry], exact when |rx+ry| <= Omega`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221; `binary32`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221.

### `ball_less_2`

Claims: `trit(yes yes, no no) lt(x, y) over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 27 780, boundary 27 780, extreme 13 887, huge 27 780, near 27 780, overflow 13 887, points 27 778, pow2 13 887, underflow 13 888, uniform 13 890, wide 27 776, zero 13 887; `binary32`: ballstates 27 780, boundary 27 780, extreme 13 887, huge 27 780, near 27 780, overflow 13 887, points 27 778, pow2 13 887, underflow 13 888, uniform 13 890, wide 27 776, zero 13 887.

### `ball_less_equal_1`

Claims: `trit(yes yes, no no) le(x, y) over x=[cx +- rx], y=[cy +- ry], exact when |rx+ry| <= Omega`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221; `binary32`: ballstates 344 446, boundary 344 446, extreme 172 221, huge 344 445, near 344 446, overflow 172 221, points 344 444, pow2 172 221, underflow 172 222, uniform 172 223, wide 344 444, zero 172 221.

### `ball_less_equal_2`

Claims: `trit(yes yes, no no) le(x, y) over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 27 780, boundary 27 780, extreme 13 887, huge 27 780, near 27 780, overflow 13 887, points 27 778, pow2 13 887, underflow 13 888, uniform 13 890, wide 27 776, zero 13 887; `binary32`: ballstates 27 780, boundary 27 780, extreme 13 887, huge 27 780, near 27 780, overflow 13 887, points 27 778, pow2 13 887, underflow 13 888, uniform 13 890, wide 27 776, zero 13 887.

### `ball_lower_as_1`

Claims: `set_bound(l) below x over x=[c +- r], tight rounded`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 358 | 5 358 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 1 328 | 1 328 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 387 500, beyond 387 500, cross 387 500, exactend 387 500, extreme 193 750, overflow 193 750, pow2 193 750, radii 387 500, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: ballstates 387 500, beyond 387 500, cross 387 500, exactend 387 500, extreme 193 750, overflow 193 750, pow2 193 750, radii 387 500, underflow 193 750, uniform 193 750, zero 193 750.

### `ball_lower_as_2`

Claims: `set_bound(l) below x over x=[c +- r]`; `error(l) form A, c=5, k=1, t=3`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.800000 | 4.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.800000 | 4.00000 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 | 0.785997 | 3.96681 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 | 0.785618 | 3.96488 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 5 888 | 5 888 | 0 | 0.773931 | 3.91753 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 | 0.799044 | 3.99756 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 35 390 | 35 390 | 0 | 0.783346 | 3.95331 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 31 250, beyond 31 250, cross 31 250, exactend 31 250, extreme 15 625, overflow 15 625, pow2 15 625, radii 31 250, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: ballstates 31 250, beyond 31 250, cross 31 250, exactend 31 250, extreme 15 625, overflow 15 625, pow2 15 625, radii 31 250, underflow 15 625, uniform 15 625, zero 15 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.800000 (clang18-fixup-call/cxx, linux-x86-64):
  ball_lower_as_2 binary64 -0x1p+1013 -0x1p-1074 0x1p-1074 #radii:55156 -> -0x1.0000000000002p+1013
largest error / bound, interpreter 0.799044 (fp:4:-8:3, every operand):
  ball_lower_as_2 fp:4:-8:3 -0x1p+6 -0x1p-8 0x1p-8 #exhaustive:99633 -> -0x1.4p+6
```

### `ball_make_1`

Claims: `makes_ball(cw, rw) from center c, radius r`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 |
| `fp:1:-3:4`, every operand (p = min_precision, the quick tier's number of exponents) | 400 | 400 | 0 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 476 | 5 476 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 444 | 1 444 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: badradius 516 664, extreme 258 334, halfgap 516 668, nonfinite 516 664, overflow 258 334, pow2 258 334, underflow 258 334, uniform 258 334, zero 258 334; `binary32`: badradius 516 664, extreme 258 334, halfgap 516 668, nonfinite 516 664, overflow 258 334, pow2 258 334, underflow 258 334, uniform 258 334, zero 258 334.

### `ball_make_2`

Claims: `makes_ball(cw, rw) from center c, radius r`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 896 | 896 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: badradius 508 330, extreme 254 167, halfgap 508 335, nonfinite 508 330, overflow 254 167, pow2 254 168, underflow 254 168, uniform 254 168, zero 254 167; `binary32`: badradius 508 330, extreme 254 167, halfgap 508 335, nonfinite 508 330, overflow 254 167, pow2 254 168, underflow 254 168, uniform 254 168, zero 254 167.

### `ball_mul_1`

Claims: `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 5 651 064 | 0 | 1.78318 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 5 620 824 | 0 | 1.81935 | 1.000000189 |
| `fp:4:-4:1`, every operand (quick tier + 2 bits) | 38 638 656 | 10 981 732 | 0 | 1.60547 | 1.17089 |
| `fp:3:-6:2`, every operand (p = min_precision + 2, another exponent range) | 9 985 600 | 5 328 700 | 0 | 1.85352 | 1.47074 |
| `fp:2:-7:3`, every operand (p = min_precision + 1, another exponent range) | 1 272 384 | 739 313 | 0 | 2.05078 | 2.61224 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 371 600 | 891 164 | 0 | 1.85352 | 1.50367 |
| `fp:2:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 142 884 | 56 255 | 0 | 2.05078 | 2.61224 |
| `fp:1:-6:5`, every operand (p = min_precision, another exponent range) | 105 625 | 48 733 | 0 | 1.625 | 5.33333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.78318 (clang18-fixup-call/cxx, linux-x86-64):
  ball_mul_1 binary64 -0x1.bf2efa49234b1p+1008 0x1.fffffffffffffp+1022 -0x1.276cf7ac91757p-308 0x1.00004p-271 #wide:70033 -> 0x1.0206bd6fd1d4fp+701 0x1.0003be5edd654p+752
smallest radius slack, gaps, interpreter 1.60547 (fp:4:-4:1, every operand):
  ball_mul_1 fp:4:-4:1 -0x1.cp-1 0x1.ep+3 -0x1p-4 0x1.2p+0 #exhaustive:14567129 -> 0x1p-4 0x1.6p+4
```

### `ball_mul_1_full`

Claims: `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |(abs(cx)+rx)*(abs(cy)+ry)| <= 2^(qmax+p-4)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.67533 | 1.00000 | 3 497 706 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.77391 | 1.000000205 | 3 466 476 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1.85352 | 1.50367 | 131 167 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 2.05078 | 2.61224 | 190 319 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 2.05078 | 2.61224 | 9 563 |
| `fp:2:-7:6`, every operand (p = min_precision, another number of exponents) | 3 139 984 | 3 139 984 | 0 | 2.05078 | 2.61224 | 1 019 219 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000; `binary32`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.67533 (clang18-fixup-call/cxx, linux-x86-64):
  ball_mul_1_full binary64 0x1.dbcabc6399729p+525 0x1.1b74ce28b4b7cp+569 -0x1.bb866cea532b1p-934 0x1.d037a40f00f18p-907 #wide:83977 -> -0x1.9c28d54600044p-408 0x1.0100a8d3733b5p-337
smallest radius slack, gaps, interpreter 1.85352 (fp:3:-4:1, every operand):
  ball_mul_1_full fp:3:-4:1 -0x1.cp-2 0x1.8p+0 -0x1.4p-2 0x1.8p+1 #exhaustive:885742 -> 0x1p-3 0x1.4p+3
```

### `ball_mul_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 5 583 888 | 0 | 2.57142 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 5 430 024 | 0 | 2.69528 | 1.000000311 |
| `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1.8p+0` (p = min_precision, the quick tier's format) | 27 342 441 | 4 110 469 | 0 | 2.32227 | 1.30925 |
| `fp:4:-5:-3`, every operand (p = min_precision, another exponent range) | 15 492 096 | 5 471 272 | 0 | 4.5625 | 1.69724 |
| `fp:4:-5:1`, restricted: `cx.lead=0:0`, `cy.lead=0:0` (p = min_precision, the quick tier's format) | 15 745 024 | 8 811 524 | 0 | 2.16797 | 1.26108 |
| `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `ry.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `cx.lead=0:0` (p = min_precision, the quick tier's format) | 2 701 650 | 1 199 458 | 0 | 2.19141 | 1.32186 |
| `fp:5:-4:1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1.8p+0`, `cx.lead=0:0` (p = min_precision + 1, another exponent range) | 580 320 | 364 016 | 0 | 3.95312 | 1.26291 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 2.57142 (clang-fixup-inline/cxx, macos-arm64):
  ball_mul_2 binary64 0x1.00104p+387 -0x1.2930df22f8623p-987 0x1.0000000004p+387 0x1.04p-343 0x1p-396 0x1.3b63d15a2e5dep-394 #extreme:22046 -> 0x1.0410810000001p+44 -0x1.ffdf8p-10 0x1.0400000004108p+44
smallest radius slack, gaps, interpreter 2.16797 (fp:4:-5:1, restricted: cx.lead=0:0, cy.lead=0:0):
  ball_mul_2 fp:4:-5:1 -0x1.8p+0 -0x1p-4 0x1.cp+0 -0x1p+0 -0x1p-4 0x1.8p+0 #exhaustive:2914268 -> 0x1.ap+0 0x1p-5 0x1.2p+3
```

### `ball_mul_2_full`

Claims: `encloses(cw, rw) x*y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |(abs(cx)+rx)*(abs(cy)+ry)| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 2.56759 | 1.00000 | 3 492 270 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 2.74996 | 1.000000319 | 3 405 996 |
| `fp:4:-4:-1`, every operand (p = min_precision, the quick tier's format) | 97 653 924 | 97 653 924 | 0 | 3.125 | 1.43177 | 1 487 636 |
| `fp:4:-4:-1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1p-1/0x1.8p+0` (p = min_precision, the quick tier's format) | 980 100 | 980 100 | 0 | 3.28125 | 1.49416 | 74 055 |
| `fp:4:-5:0`, restricted: `cx.lead=0:0`, `cy.lead=0:0` (p = min_precision, another number of exponents) | 12 068 676 | 12 068 676 | 0 | 2.16797 | 1.26108 | 1 947 624 |
| `fp:4:-3:-2`, every operand (p = min_precision, another number of exponents) | 2 149 156 | 2 149 156 | 0 | 6.75 | 2.30769 | 38 997 |
| `fp:5:-5:-2`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1p-1/0x1.8p+0`, `cx.lead=0:0` (p = min_precision + 1, quick tier + 1 bit) | 503 500 | 503 500 | 0 | 5.11719 | 1.27949 | 45 910 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000; `binary32`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 2.56759 (clang-fixup-inline/cxx, macos-arm64):
  ball_mul_2_full binary64 0x1p+371 -0x1.4f038eae9b936p+179 0x1.0000400000008p+371 -0x1p-1000 -0x1p-1053 0x1.dd64bp-1054 #pow2:3210 -> -0x1p-629 -0x1p-682 0x1.000040000000cp-629
smallest radius slack, gaps, interpreter 2.16797 (fp:4:-5:0, restricted: cx.lead=0:0, cy.lead=0:0):
  ball_mul_2_full fp:4:-5:0 -0x1.8p+0 -0x1p-4 0x1.cp+0 -0x1p+0 -0x1p-4 0x1.8p+0 #exhaustive:2245744 -> 0x1.ap+0 0x1p-5 0x1.2p+3
```

### `ball_mul_pow2_1`

Claims: `encloses(cz, rz) x*c over x=[cx +- rx], exactly the set when (cx*c = 0 or |cx*c| > eta/(2*u)) and (rx*c = 0 or |rx*c| > eta/(2*u))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 93 043 386 | 0 | 0 | 1 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 93 098 520 | 0 | 0 | 1 |
| `fp:5:-6:1`, every operand (quick tier + 1 bit) | 495 936 | 385 972 | 0 | 0 | 1 |
| `fp:3:-6:1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 25 560 | 22 548 | 0 | 0 | 1 |
| `fp:2:-6:1`, every operand (p = min_precision, the quick tier's exponent range) | 5 670 | 5 272 | 0 | 0 | 1 |
| `fp:6:-6:1`, every operand (quick tier + 2 bits) | 2 152 800 | 1 565 444 | 0 | 0 | 1 |
| `fp:5:-8:2`, every operand (another exponent range) | 1 103 040 | 891 796 | 0 | 0 | 1 |
| `fp:4:-9:3`, every operand (another exponent range) | 399 616 | 336 108 | 0 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 712 501, extreme 237 499, into 237 501, outof 237 500, overflow 237 499, pow2 237 499, sides 237 501, underflow 237 500, uniform 237 501, zero 237 499; `binary32`: atnormal 712 501, extreme 237 499, into 237 501, outof 237 500, overflow 237 499, pow2 237 499, sides 237 501, underflow 237 500, uniform 237 501, zero 237 499.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_mul_pow2_1 binary64 0x1.0000000000001p-197 0x0p+0 0x1p-825 #atnormal:19 -> 0x1.0000000000001p-1022 0x0p+0
smallest radius slack, gaps, interpreter 0 (fp:5:-6:1, every operand):
  ball_mul_pow2_1 fp:5:-6:1 -0x1.fp+5 0x0p+0 0x1p-6 #exhaustive:0 -> -0x1.fp-1 0x0p+0
```

### `ball_mul_pow2_1_full`

Claims: `encloses(cw, rw) x*c over x=[cx +- rx], B1-B4, finite when |(abs(cx)+rx)*c| <= 2^(qmax+p-2), exactly the set when (cx*c = 0 or |cx*c| > eta/(2*u)) and (rx*c = 0 or |rx*c| > eta/(2*u))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 | 4 276 962 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 | 4 275 990 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 495 960 | 495 960 | 0 | 0 | 1 | 337 524 |
| `fp:4:-8:3`, every operand (another number of exponents) | 322 950 | 322 950 | 0 | 0 | 1 | 226 062 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 2 152 826 | 2 152 826 | 0 | 0 | 1 | 1 515 524 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 25 580 | 25 580 | 0 | 0 | 1 | 15 968 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 5 688 | 5 688 | 0 | 0 | 1 | 3 364 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 31 254, ballstates 20 830, extreme 10 417, hugeradius 20 830, into 10 418, nonfinite 20 834, outof 10 418, overflow 10 417, pow2 10 417, sides 10 418, threshold 20 830, underflow 10 418, uniform 10 418, zero 10 417, zeroinf 20 834, zerowhole 20 830; `binary32`: atnormal 31 254, ballstates 20 830, extreme 10 417, hugeradius 20 830, into 10 418, nonfinite 20 834, outof 10 418, overflow 10 417, pow2 10 417, sides 10 418, threshold 20 830, underflow 10 418, uniform 10 418, zero 10 417, zeroinf 20 834, zerowhole 20 830.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_mul_pow2_1_full binary64 0x1.0000000000001p-289 0x1.965f6c133f2b1p+220 0x1p-733 #atnormal:49 -> 0x1.0000000000001p-1022 0x1.965f6c133f2b1p-513
smallest radius slack, gaps, interpreter 0 (fp:5:-7:0, every operand):
  ball_mul_pow2_1_full fp:5:-7:0 -0x1.fp+4 0x0p+0 0x1p-7 #exhaustive:0 -> -0x1.fp-3 0x0p+0
```

### `ball_mul_pow2_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x*c over x=[cx +- rx], exactly the set when (cx[0]*c = 0 or |cx[0]*c| > eta/(2*u)) and (cx[1]*c = 0 or |cx[1]*c| > eta/(2*u)) and (rx*c = 0 or |rx*c| > eta/(2*u))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 643 890 | 0 | 0 | 1 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 652 908 | 0 | 0 | 1 |
| `fp:5:-4:1`, every operand (quick tier + 2 bits) | 2 256 800 | 1 283 056 | 0 | 0 | 1 |
| `fp:4:-4:1`, every operand (quick tier + 1 bit) | 499 464 | 314 216 | 0 | 0 | 1 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 94 752 | 67 576 | 0 | 0 | 1 |
| `fp:4:-6:2`, every operand (another exponent range) | 3 854 400 | 2 641 976 | 0 | 0 | 1 |
| `fp:3:-7:3`, every operand (p = min_precision + 1, another exponent range) | 1 437 072 | 1 084 748 | 0 | 0 | 1 |
| `fp:2:-4:1`, every operand (p = min_precision, the quick tier's exponent range) | 15 582 | 12 684 | 0 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 62 501, extreme 20 832, into 20 835, outof 20 833, overflow 20 832, pow2 20 832, sides 20 835, underflow 20 833, uniform 20 835, zero 20 832; `binary32`: atnormal 62 501, extreme 20 832, into 20 835, outof 20 833, overflow 20 832, pow2 20 832, sides 20 835, underflow 20 833, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_mul_pow2_2 binary64 0x1.e252a6ab5cd22p+1022 -0x1.dd8f1980e2613p+555 0x1.0000000000001p-635 0x1p-387 #atnormal:16 -> 0x1.e252a6ab5cd22p+635 -0x1.dd8f1980e2613p+168 0x1.0000000000001p-1022
smallest radius slack, gaps, interpreter 0 (fp:5:-4:1, every operand):
  ball_mul_pow2_2 fp:5:-4:1 -0x1.fp+5 0x0p+0 0x0p+0 0x1p-4 #exhaustive:16800 -> -0x1.fp+1 0x0p+0 0x0p+0
```

### `ball_mul_pow2_2_full`

Claims: `encloses(cw, rw) x*c over x=[cx +- rx], B1-B4, finite when |(abs(cx)+rx)*c| <= 2^(qmax+p-2), exactly the set when (cx[0]*c = 0 or |cx[0]*c| > eta/(2*u)) and (cx[1]*c = 0 or |cx[1]*c| > eta/(2*u)) and (rx*c = 0 or |rx*c| > eta/(2*u))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 | 4 271 220 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 | 4 270 878 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 499 482 | 499 482 | 0 | 0 | 1 | 242 291 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 94 768 | 94 768 | 0 | 0 | 1 | 41 635 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 2 256 820 | 2 256 820 | 0 | 0 | 1 | 1 204 387 |
| `fp:3:-6:3`, every operand (p = min_precision + 1, another number of exponents) | 949 896 | 949 896 | 0 | 0 | 1 | 513 121 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 15 596 | 15 596 | 0 | 0 | 1 | 6 165 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 31 254, ballstates 20 830, extreme 10 417, hugeradius 20 830, into 10 418, nonfinite 20 834, outof 10 418, overflow 10 417, pow2 10 417, sides 10 418, threshold 20 830, underflow 10 418, uniform 10 418, zero 10 417, zeroinf 20 834, zerowhole 20 830; `binary32`: atnormal 31 254, ballstates 20 830, extreme 10 417, hugeradius 20 830, into 10 418, nonfinite 20 834, outof 10 418, overflow 10 417, pow2 10 417, sides 10 418, threshold 20 830, underflow 10 418, uniform 10 418, zero 10 417, zeroinf 20 834, zerowhole 20 830.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_mul_pow2_2_full binary64 -0x1.d52e520475cafp-972 0x1.000000000004p-1028 0x0p+0 0x1p+6 #atnormal:52 -> -0x1.d52e520475cafp-966 0x1.000000000004p-1022 0x0p+0
smallest radius slack, gaps, interpreter 0 (fp:4:-5:0, every operand):
  ball_mul_pow2_2_full fp:4:-5:0 -0x1.ep+3 -0x1.ep-2 0x0p+0 0x1p+0 #exhaustive:5 -> -0x1.ep+3 -0x1.ep-2 0x0p+0
```

### `ball_narrow_2_1`

Claims: `encloses(cz, rz) x over x=[c +- r], B1-B4, finite when |abs(c)+r| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | 0.5 | 1.00000 | 67 127 976 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | 0.5 | 1.000000030 | 66 677 562 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 | 0.5 | 1.008 | 725 217 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 | 0.5 | 1.01638 | 181 873 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 | 0.5 | 1.03434 | 454 425 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 35 390 | 35 390 | 0 | 0.5 | 1.07563 | 10 373 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 5 888 | 5 888 | 0 | 0.5 | 1.18519 | 2 131 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 265 216, cancel 132 610, centerpow2 265 219, exact 132 610, extreme 132 608, hugeradius 265 216, nonfinite 265 216, overflow 132 608, pow2 132 608, radii 265 220, threshold 265 216, underflow 132 609, uniform 132 610, wide 132 610, zero 132 608, zerowhole 265 216; `binary32`: ballstates 265 216, cancel 132 610, centerpow2 265 219, exact 132 610, extreme 132 608, hugeradius 265 216, nonfinite 265 216, overflow 132 608, pow2 132 608, radii 265 220, threshold 265 216, underflow 132 609, uniform 132 610, wide 132 610, zero 132 608, zerowhole 265 216.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0.5 (clang18-fixup-call/cxx, linux-x86-64):
  ball_narrow_2_1 binary64 -0x1.fffffffffffffp+1023 0x1p+969 0x1p+916 #ballstates:2133 -> -0x1.fffffffffffffp+1023 0x1.0000000000001p+969
smallest radius slack, gaps, interpreter 0.5 (fp:6:-8:-1, every operand):
  ball_narrow_2_1 fp:6:-8:-1 -0x1.f8p+4 -0x1.f8p-3 0x1p-7 #exhaustive:2 -> -0x1.f8p+4 0x1.08p-2
```

### `ball_neg_1`

Claims: `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 | 0 | 1 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 | 0 | 1 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 328 | 1 328 | 0 | 0 | 1 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 | 0 | 1 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 358 | 5 358 | 0 | 0 | 1 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 327 | 327 | 0 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 23 810, cancel 11 905, centerpow2 23 810, exact 11 905, extreme 11 905, hugeradius 23 805, nonfinite 23 810, overflow 11 905, pow2 11 905, radii 23 810, underflow 11 905, uniform 11 905, wide 11 905, zero 11 905, zerowhole 23 810; `binary32`: ballstates 23 810, cancel 11 905, centerpow2 23 810, exact 11 905, extreme 11 905, hugeradius 23 805, nonfinite 23 810, overflow 11 905, pow2 11 905, radii 23 810, underflow 11 905, uniform 11 905, wide 11 905, zero 11 905, zerowhole 23 810.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_neg_1 binary64 -0x0p+0 0x0p+0 #ballstates:15 -> 0x0p+0 0x0p+0
smallest radius slack, gaps, interpreter 0 (fp:6:-10:1, every operand):
  ball_neg_1 fp:6:-10:1 -0x1.f8p+6 0x0p+0 #exhaustive:0 -> 0x1.f8p+6 0x0p+0
```

### `ball_neg_2`

Claims: `normalized(cz)`; `encloses(cz, rz) -x over x=[cx +- rx], B1-B4, finite when nothing (no condition claimed)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 1 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 | 0 | 1 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 | 0 | 1 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 888 | 5 888 | 0 | 0 | 1 |
| `fp:1:-3:4`, every operand (p = min_precision, the quick tier's number of exponents) | 911 | 911 | 0 | 0 | 1 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 | 0 | 1 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 35 390 | 35 390 | 0 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 23 810, cancel 11 905, centerpow2 23 810, exact 11 905, extreme 11 905, hugeradius 23 805, nonfinite 23 810, overflow 11 905, pow2 11 905, radii 23 810, underflow 11 905, uniform 11 905, wide 11 905, zero 11 905, zerowhole 23 810; `binary32`: ballstates 23 810, cancel 11 905, centerpow2 23 810, exact 11 905, extreme 11 905, hugeradius 23 805, nonfinite 23 810, overflow 11 905, pow2 11 905, radii 23 810, underflow 11 905, uniform 11 905, wide 11 905, zero 11 905, zerowhole 23 810.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  ball_neg_2 binary64 0x1p+1023 -0x1.23c144a6de424p+967 0x1p+1022 #ballstates:15 -> -0x1p+1023 0x1.23c144a6de424p+967 0x1p+1022
smallest radius slack, gaps, interpreter 0 (fp:5:-7:0, every operand):
  ball_neg_2 fp:5:-7:0 -0x1.fp+4 -0x1.fp-2 0x0p+0 #exhaustive:0 -> 0x1.fp+4 0x1.fp-2 0x0p+0
```

### `ball_negative_1`

Claims: `certain(m) lt(x, 0) over x=[c +- r], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 328 | 1 328 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 358 | 5 358 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 327 | 327 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 442 858, extreme 221 427, huge 442 858, nearzero 442 858, overflow 221 428, points 442 858, pow2 221 427, underflow 221 429, uniform 221 429, zero 221 428; `binary32`: ballstates 442 858, extreme 221 427, huge 442 858, nearzero 442 858, overflow 221 428, points 442 858, pow2 221 427, underflow 221 429, uniform 221 429, zero 221 428.

### `ball_negative_2`

Claims: `certain(m) lt(x, 0) over x=[c +- r], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 888 | 5 888 | 0 |
| `fp:1:-3:4`, every operand (p = min_precision, the quick tier's number of exponents) | 911 | 911 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 35 390 | 35 390 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 435 716, extreme 217 856, huge 435 715, nearzero 435 716, overflow 217 856, points 435 714, pow2 217 856, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: ballstates 435 716, extreme 217 856, huge 435 715, nearzero 435 716, overflow 217 856, points 435 714, pow2 217 856, underflow 217 857, uniform 217 858, zero 217 856.

### `ball_positive_1`

Claims: `certain(m) lt(0, x) over x=[c +- r], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 358 | 5 358 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 328 | 1 328 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 327 | 327 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 442 858, extreme 221 427, huge 442 858, nearzero 442 858, overflow 221 428, points 442 858, pow2 221 427, underflow 221 429, uniform 221 429, zero 221 428; `binary32`: ballstates 442 858, extreme 221 427, huge 442 858, nearzero 442 858, overflow 221 428, points 442 858, pow2 221 427, underflow 221 429, uniform 221 429, zero 221 428.

### `ball_positive_2`

Claims: `certain(m) lt(0, x) over x=[c +- r], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 35 390 | 35 390 | 0 |
| `fp:1:-3:4`, every operand (p = min_precision, the quick tier's number of exponents) | 911 | 911 | 0 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 888 | 5 888 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 435 716, extreme 217 856, huge 435 715, nearzero 435 716, overflow 217 856, points 435 714, pow2 217 856, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: ballstates 435 716, extreme 217 856, huge 435 715, nearzero 435 716, overflow 217 856, points 435 714, pow2 217 856, underflow 217 857, uniform 217 858, zero 217 856.

### `ball_scale_1`

Claims: `encloses(cz, rz) x*a over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 5 716 692 | 0 | 1.00000 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 5 599 476 | 0 | 1.000000119 | 1.000000111 |
| `fp:5:-5:0`, every operand (quick tier + 2 bits) | 5 569 648 | 3 257 050 | 0 | 1.625 | 1.08696 |
| `fp:4:-8:2`, every operand (another exponent range) | 3 502 176 | 2 726 994 | 0 | 1.125 | 1.12676 |
| `fp:3:-8:2`, every operand (p = min_precision + 2, another exponent range) | 433 200 | 359 094 | 0 | 1 | 1.2 |
| `fp:2:-5:0`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 206 | 9 064 | 0 | 1.4375 | 1.6 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 689 976 | 489 850 | 0 | 1.125 | 1.12676 |
| `fp:3:-5:0`, every operand (p = min_precision + 2, the quick tier's format) | 84 700 | 67 922 | 0 | 1 | 1.2 |
| `fp:1:-3:2`, every operand (p = min_precision, another exponent range, replaces fp:1:-5:0, where constant up((1+u)^3) is not a number) | 1 183 | 783 | 0 | 1.46875 | 3.76471 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64):
  ball_scale_1 binary64 -0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 0x1.0000000000001p-1022 #extreme:55196 -> -0x1p+2 0x1.0000000000002p+2
smallest radius slack, gaps, interpreter 1 (fp:3:-8:2, every operand):
  ball_scale_1 fp:3:-8:2 -0x1.8p+4 0x1.8p+4 -0x1.8p-1 #exhaustive:8951 -> 0x1p+4 0x1.8p+4
```

### `ball_scale_1_full`

Claims: `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when |(abs(cx)+rx)*a| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.00000 | 1.00000 | 54 098 280 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.000000119 | 1.000000108 | 53 200 998 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's format) | 89 436 | 89 436 | 0 | 1 | 1.2 | 36 914 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 11 400 | 11 400 | 0 | 1.4375 | 1.6 | 4 724 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 708 852 | 708 852 | 0 | 1.125 | 1.12676 | 291 726 |
| `fp:3:-6:3`, every operand (p = min_precision + 1, another number of exponents) | 344 700 | 344 700 | 0 | 1 | 1.2 | 194 982 |
| `fp:2:-8:7`, every operand (p = min_precision, another number of exponents) | 159 600 | 159 600 | 0 | 1.4375 | 1.6 | 102 984 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 248 000, cancel 124 000, centerpow2 248 000, exact 124 000, extreme 124 000, hugeradius 248 000, nonfinite 248 000, overflow 124 000, pow2 124 000, radii 248 000, threshold 248 000, underflow 124 000, uniform 124 000, wide 124 000, zero 124 000, zeroinf 248 000, zerowhole 248 000; `binary32`: ballstates 248 000, cancel 124 000, centerpow2 248 000, exact 124 000, extreme 124 000, hugeradius 248 000, nonfinite 248 000, overflow 124 000, pow2 124 000, radii 248 000, threshold 248 000, underflow 124 000, uniform 124 000, wide 124 000, zero 124 000, zeroinf 248 000, zerowhole 248 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64):
  ball_scale_1_full binary64 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+1023 0x1.0000000000001p-1022 #ballstates:236319 -> 0x1p+2 0x1.0000000000002p+2
smallest radius slack, gaps, interpreter 1 (fp:3:-4:1, every operand):
  ball_scale_1_full fp:3:-4:1 -0x1.8p+3 0x1.8p+3 -0x1.8p-1 #exhaustive:3149 -> 0x1p+3 0x1.8p+3
```

### `ball_scale_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x*a over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 5 705 532 | 0 | 1.43810 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 5 557 122 | 0 | 1.45374 | 1.000000144 |
| `fp:4:-4:1`, every operand (quick tier + 2 bits) | 6 160 056 | 2 659 714 | 0 | 1.53125 | 1.18081 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 651 420 | 374 170 | 0 | 1.40625 | 1.30612 |
| `fp:2:-4:1`, every operand (p = min_precision, the quick tier's format) | 60 102 | 43 522 | 0 | 1.46875 | 1.68977 |
| `fp:3:-6:2`, every operand (p = min_precision + 1, another exponent range) | 4 294 440 | 2 861 126 | 0 | 1.375 | 1.29730 |
| `fp:2:-8:3`, every operand (p = min_precision, another exponent range) | 1 133 730 | 905 462 | 0 | 1.46875 | 1.68977 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.43810 (clang-fixup-inline/cxx, macos-arm64):
  ball_scale_2 binary64 -0x1.67f0bde5bef57p+253 0x1.41c36602c1d84p+165 0x1.00000048p+202 0x1.002001p+750 #radii:40656 -> -0x1.681dbd656c6b3p+1003 -0x1.1b3d5bffaf852p+949 0x1.0020014809006p+952
smallest radius slack, gaps, interpreter 1.375 (fp:3:-6:2, every operand):
  ball_scale_2 fp:3:-6:2 -0x1.8p+4 -0x1p+0 0x1.8p+3 -0x1.8p-1 #exhaustive:163867 -> 0x1.4p+4 -0x1p+0 0x1.8p+3
```

### `ball_scale_2_full`

Claims: `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when |(abs(cx)+rx)*a| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.37500 | 1.00000 | 3 762 468 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.4375 | 1.000000143 | 3 674 376 |
| `fp:4:-4:-1`, every operand (quick tier + 1 bit) | 810 324 | 810 324 | 0 | 2.44531 | 1.28584 | 148 004 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, another number of exponents) | 687 068 | 687 068 | 0 | 1.40625 | 1.30612 | 186 026 |
| `fp:2:-4:3`, every operand (p = min_precision, another number of exponents) | 223 744 | 223 744 | 0 | 1.46875 | 1.68977 | 87 040 |
| `fp:3:-3:0`, every operand (p = min_precision + 1, the quick tier's format) | 100 044 | 100 044 | 0 | 2.26562 | 1.53425 | 18 612 |
| `fp:2:-2:1`, every operand (p = min_precision, the quick tier's number of exponents) | 12 144 | 12 144 | 0 | 1.8125 | 2.46154 | 2 376 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000; `binary32`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.37500 (clang18-fixup-call/cxx, linux-x86-64):
  ball_scale_2_full binary64 0x1.39d4d8644e31ep-853 0x1p-906 0x1.000000802p-904 0x1.fffffffffffffp+1023 #ballstates:85145 -> 0x1.39d4d8644e31ep+171 -0x1.cea6c322718fp+115 0x1.0000008020001p+120
smallest radius slack, gaps, interpreter 1.40625 (fp:3:-4:1, every operand):
  ball_scale_2_full fp:3:-4:1 -0x1.8p+3 -0x1p-3 0x1.8p+2 -0x1.8p-1 #exhaustive:54885 -> 0x1p+3 0x1p+0 0x1.8p+2
```

### `ball_scale_2_full_entry`

Claims: `encloses(cw, rw) x*a over x=[cx +- rx], B1-B4, finite when |(abs(cx)+rx)*a| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.41014 | 1.00000 | 3 773 412 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.47957 | 1.000000145 | 3 673 620 |
| `fp:2:-4:3`, every operand (p = min_precision, another number of exponents) | 223 744 | 223 744 | 0 | 1.46875 | 1.68977 | 87 040 |
| `fp:2:-2:1`, every operand (p = min_precision, the quick tier's number of exponents) | 12 144 | 12 144 | 0 | 1.8125 | 2.46154 | 2 376 |
| `fp:4:-4:-1`, every operand (quick tier + 1 bit) | 810 324 | 810 324 | 0 | 2.44531 | 1.28584 | 148 004 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, another number of exponents) | 687 068 | 687 068 | 0 | 1.40625 | 1.30612 | 186 026 |
| `fp:3:-3:0`, every operand (p = min_precision + 1, the quick tier's format) | 100 044 | 100 044 | 0 | 2.26562 | 1.53425 | 18 612 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000; `binary32`: ballstates 20 000, cancel 10 000, centerpow2 20 000, exact 10 000, extreme 10 000, hugeradius 20 000, nonfinite 20 000, overflow 10 000, pow2 10 000, radii 20 000, threshold 20 000, underflow 10 000, uniform 10 000, wide 10 000, zero 10 000, zeroinf 20 000, zerowhole 20 000.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.41014 (msvc-fixup-call/cxx, windows-x64):
  ball_scale_2_full_entry binary64 0x1.af7daf26708f3p+219 -0x1.1df6a54dc6b7p+163 0x1.b006d7b797fa3p+168 -0x1.35c99e7fc0952p+292 #radii:72051 -> -0x1.0513449f688c3p+512 -0x1.e00acd6939ed2p+458 0x1.0566419de5905p+461
smallest radius slack, gaps, interpreter 1.40625 (fp:3:-4:1, every operand):
  ball_scale_2_full_entry fp:3:-4:1 -0x1.8p+3 -0x1p-3 0x1.8p+2 -0x1.8p-1 #exhaustive:54885 -> 0x1p+3 0x1p+0 0x1.8p+2
```

### `ball_split_1`

Claims: `ball_splits [ca +- ra], [cb +- rb] of [c +- r]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 1 328 | 1 328 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 358 | 5 358 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 516 668, extreme 258 332, overflow 258 332, pow2 258 332, radii 516 668, top 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: ballstates 516 668, extreme 258 332, overflow 258 332, pow2 258 332, radii 516 668, top 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `ball_split_2`

Claims: `ball_splits [ca +- ra], [cb +- rb] of [c +- r]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-8:3`, every operand (p = min_precision + 1, another number of exponents) | 971 674 | 971 674 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision, the quick tier's number of exponents) | 35 390 | 35 390 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 |
| `fp:4:-6:1`, every operand (p = min_precision + 1, the quick tier's format) | 198 074 | 198 074 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 41 670, extreme 20 832, overflow 20 832, pow2 20 832, radii 41 668, top 41 666, underflow 20 833, uniform 20 835, zero 20 832; `binary32`: ballstates 41 670, extreme 20 832, overflow 20 832, pow2 20 832, radii 41 668, top 41 666, underflow 20 833, uniform 20 835, zero 20 832.

### `ball_sub_1`

Claims: `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 634 872 | 0 | 1.25 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 628 662 | 0 | 1.25 | 1.000000142 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, another exponent range) | 4 064 256 | 3 025 751 | 0 | 1 | 1.2 |
| `fp:2:-6:4`, every operand (p = min_precision + 1, another exponent range) | 1 272 384 | 994 044 | 0 | 1 | 1.33333 |
| `fp:3:-3:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 1 272 384 | 807 559 | 0 | 1 | 1.2 |
| `fp:1:-5:5`, every operand (p = min_precision, another exponent range) | 76 176 | 38 639 | 0 | 1.3125 | 2.90909 |
| `fp:4:-3:1`, every operand (quick tier + 2 bits) | 20 793 600 | 14 367 516 | 0 | 1.625 | 1.20930 |
| `fp:2:-3:1`, every operand (p = min_precision + 1, the quick tier's format) | 76 176 | 38 412 | 0 | 1 | 1.33333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25 (clang18-fixup-call/cxx, linux-x86-64):
  ball_sub_1 binary64 0x1.264a356932ddbp+1021 0x1.0004p+1018 0x1p+1023 0x1.ffffffffffffdp+1022 #overflow:21238 -> -0x1.6cdae54b66912p+1022 0x1.08002p+1023
smallest radius slack, gaps, interpreter 1 (fp:3:-4:2, every operand):
  ball_sub_1 fp:3:-4:2 -0x1.cp+4 0x1p+1 -0x1.4p+3 0x1p+4 #exhaustive:32476 -> -0x1p+4 0x1.8p+4
```

### `ball_sub_1_full`

Claims: `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx-cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.25 | 1.00000 | 3 776 742 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1 | 1.000000102 | 3 723 102 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 898 704 | 898 704 | 0 | 1 | 1.33333 | 363 535 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 144 400 | 144 400 | 0 | 1 | 1.33333 | 27 055 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 377 764 | 2 377 764 | 0 | 1 | 1.2 | 397 403 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736; `binary32`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  ball_sub_1_full binary32 0x1.fffffap+126 0x1.fffffcp+126 0x1.fffffep+127 0x1.616618p+124 #hugeradius:16121 -> -0x1p+127 0x1.2c2cc4p+127
smallest radius slack, gaps, interpreter 1 (fp:2:-5:4, every operand):
  ball_sub_1_full fp:2:-5:4 -0x1p+5 0x1p+2 -0x1.8p+3 0x1p+4 #exhaustive:34234 -> -0x1p+4 0x1p+5
```

### `ball_sub_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 670 566 | 0 | 1.25596 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 660 900 | 0 | 1.25567 | 1.000000143 |
| `fp:3:-3:1`, every operand (p = min_precision, another exponent range) | 32 901 696 | 15 977 235 | 0 | 1.4375 | 1.31507 |
| `fp:3:-3:2`, restricted: `cx.lead=-1:0` (p = min_precision, the quick tier's format) | 7 295 904 | 5 136 540 | 0 | 1.25 | 1.31507 |
| `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision + 1, quick tier + 1 bit) | 15 713 296 | 11 654 256 | 0 | 3.75 | 1.5 |
| `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` (p = min_precision, the quick tier's format) | 8 767 521 | 4 968 972 | 0 | 1.46875 | 1.41593 |
| `fp:3:-2:1`, every operand (p = min_precision, another exponent range) | 5 664 400 | 2 192 431 | 0 | 1.75 | 1.52381 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230; `binary32`: cancel 19 230, centerpow2 38 460, exact 19 232, extreme 19 230, overflow 19 230, pow2 19 230, radii 38 463, underflow 19 230, uniform 19 233, wide 19 232, zero 19 230.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25567 (clang-fixup-inline/cxx, macos-arm64):
  ball_sub_2 binary32 -0x1.e9924cp+89 0x1.0c9faap+64 0x1.fffffep+126 -0x1.f0a12p+124 0x1.0c2054p+99 0x1.f46372p+101 #radii:18188 -> 0x1.f0a12p+124 -0x1.0c9ab8p+99 0x1.000002p+127
smallest radius slack, gaps, interpreter 1.25 (fp:3:-3:2, restricted: cx.lead=-1:0):
  ball_sub_2 fp:3:-3:2 -0x1.cp+0 0x0p+0 0x1.cp-1 -0x1p+3 -0x1.cp-1 0x1.cp+3 #exhaustive:86851 -> 0x1.cp+2 0x0p+0 0x1.4p+4
```

### `ball_sub_2_full`

Claims: `encloses(cw, rw) x-y over x=[cx +- rx], y=[cy +- ry], B1-B4, finite when |abs(cx-cy)+rx+ry| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing | B4 applied to |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.36048 | 1.00000 | 4 028 256 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.26273 | 1.000000143 | 3 978 720 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 149 156 | 2 149 156 | 0 | 5.5 | 1.76471 | 16 725 |
| `fp:3:-3:0`, every operand (p = min_precision, another number of exponents) | 5 673 924 | 5 673 924 | 0 | 1.75 | 1.52381 | 176 623 |
| `fp:3:-4:1`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision, another number of exponents) | 2 869 636 | 2 869 636 | 0 | 2 | 1.52381 | 472 949 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736; `binary32`: ballstates 21 740, cancel 10 870, centerpow2 21 740, exact 10 870, extreme 10 870, hugeradius 21 734, nonfinite 21 740, overflow 10 870, pow2 10 870, radii 21 740, threshold 21 740, underflow 10 870, uniform 10 870, wide 10 870, zero 10 870, zerowhole 21 736.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.26273 (msvc-fixup-call/cxx, windows-x64):
  ball_sub_2_full binary32 0x1.bc133ep+104 -0x1.8e965p+78 0x1.e5ee56p+101 0x1.bc134p+104 -0x1p+78 0x1.fffffep+126 #ballstates:44200 -> -0x1.11d2ca0000000p+81 0x0.0000000000000p+0 0x1.0000020000000p+127
smallest radius slack, gaps, interpreter 1.75 (fp:3:-3:0, every operand):
  ball_sub_2_full fp:3:-3:0 -0x1.cp+2 -0x1.8p-2 0x1p-2 -0x1.cp+2 -0x1.8p-2 0x1.8p+1 #exhaustive:4778 -> 0x0p+0 0x0p+0 0x1.4p+2
```

### `ball_to_interval_1`

Claims: `interval_of_ball(zl, zu) x over x=[c +- r], tight rounded`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 1 328 | 1 328 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 358 | 5 358 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 387 500, beyond 387 500, cross 387 500, exactend 387 500, extreme 193 750, overflow 193 750, pow2 193 750, radii 387 500, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: ballstates 387 500, beyond 387 500, cross 387 500, exactend 387 500, extreme 193 750, overflow 193 750, pow2 193 750, radii 387 500, underflow 193 750, uniform 193 750, zero 193 750.

### `ball_to_interval_2`

Claims: `interval_of_ball(zl, zu) x over x=[c +- r], tight outward, exact when lower: c-r = 0; upper: c+r = 0, bounded when |x| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | largest lower-bound distance / allowance | largest upper-bound distance / allowance |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.644345 | 0.723987 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.645270 | 0.694856 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 | 0.493224 | 0.493224 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 | 0.481965 | 0.481965 |
| `fp:3:-5:2`, every operand (p = min_precision, the quick tier's number of exponents) | 35 390 | 35 390 | 0 | 0.384391 | 0.384391 |
| `fp:4:-8:3`, every operand (p = min_precision + 1, another number of exponents) | 971 674 | 971 674 | 0 | 0.470629 | 0.470629 |
| `fp:4:-6:1`, every operand (p = min_precision + 1, the quick tier's format) | 198 074 | 198 074 | 0 | 0.456138 | 0.456138 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 25 000, beyond 25 000, cross 25 000, exactend 25 000, extreme 12 500, overflow 12 500, pow2 12 500, radii 25 000, threshold 25 000, underflow 12 500, uniform 12 500, zero 12 500, zeroend 25 000; `binary32`: ballstates 25 000, beyond 25 000, cross 25 000, exactend 25 000, extreme 12 500, overflow 12 500, pow2 12 500, radii 25 000, threshold 25 000, underflow 12 500, uniform 12 500, zero 12 500, zeroend 25 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest lower-bound distance / allowance, compiled 0.645270 (msvc-fixup-call/cxx, windows-x64):
  ball_to_interval_2 binary32 0x1.00082p-42 -0x1.fffffep-67 0x1.ad072ap-44 #extreme:47359 -> 0x1.298ca80000000p-43 0x1.fffff80000000p-68 0x1.6b49ea0000000p-42 -0x1.ffffea0000000p-68
largest lower-bound distance / allowance, interpreter 0.493224 (fp:6:-8:-1, every operand):
  ball_to_interval_2 fp:6:-8:-1 0x1.08p+4 -0x1.d8p-3 0x1.a8p+2 #exhaustive:3540309 -> 0x1.3p+3 -0x1.4p-5 0x1.7p+4 0x1.fp-4
largest upper-bound distance / allowance, compiled 0.723987 (msvc-fixup-call/cxx, windows-x64):
  ball_to_interval_2 binary64 -0x1.007d84f5511ep+1023 0x1.fffffffffffffp+969 0x1.ef909cf9cf021p+1021 #beyond:69928 -> -0x1.7c61ac33c4de8p+1023 0x1.ffffffffffff5p+968 -0x1.0932bb6dbabaep+1022 -0x1.ffffffffffffcp+968
largest upper-bound distance / allowance, interpreter 0.493224 (fp:6:-8:-1, every operand):
  ball_to_interval_2 fp:6:-8:-1 -0x1.18p+4 0x1.d8p-3 0x1.e8p+2 #exhaustive:1067549 -> -0x1.9p+4 -0x1.1p-3 -0x1.3p+3 0x1.4p-5
```

### `ball_upper_as_1`

Claims: `set_bound(h) above x over x=[c +- r], tight rounded`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 358 | 5 358 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 1 328 | 1 328 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 387 500, beyond 387 500, cross 387 500, exactend 387 500, extreme 193 750, overflow 193 750, pow2 193 750, radii 387 500, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: ballstates 387 500, beyond 387 500, cross 387 500, exactend 387 500, extreme 193 750, overflow 193 750, pow2 193 750, radii 387 500, underflow 193 750, uniform 193 750, zero 193 750.

### `ball_upper_as_2`

Claims: `set_bound(h) above x over x=[c +- r]`; `error(h) form A, c=5, k=1, t=3`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.800000 | 4.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.800000 | 4.00000 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 | 0.785618 | 3.96488 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 | 0.799044 | 3.99756 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 35 390 | 35 390 | 0 | 0.783346 | 3.95331 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 | 0.785997 | 3.96681 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 5 888 | 5 888 | 0 | 0.773931 | 3.91753 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 31 250, beyond 31 250, cross 31 250, exactend 31 250, extreme 15 625, overflow 15 625, pow2 15 625, radii 31 250, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: ballstates 31 250, beyond 31 250, cross 31 250, exactend 31 250, extreme 15 625, overflow 15 625, pow2 15 625, radii 31 250, underflow 15 625, uniform 15 625, zero 15 625.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.800000 (clang18-fixup-call/cxx, linux-x86-64):
  ball_upper_as_2 binary64 0x1p+1019 0x1p-1074 0x1p-1074 #pow2:70638 -> 0x1.0000000000002p+1019
largest error / bound, interpreter 0.799044 (fp:4:-8:3, every operand):
  ball_upper_as_2 fp:4:-8:3 0x1p+6 0x1p-8 0x1p-8 #exhaustive:871937 -> 0x1.4p+6
```

### `ball_zero_1`

Claims: `certain(m) eq(x, 0) over x=[c +- r], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 327 | 327 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 2 bits) | 1 383 618 | 1 383 618 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 345 698 | 345 698 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 225 458 | 225 458 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 358 | 5 358 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 328 | 1 328 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 442 858, extreme 221 427, huge 442 858, nearzero 442 858, overflow 221 428, points 442 858, pow2 221 427, underflow 221 429, uniform 221 429, zero 221 428; `binary32`: ballstates 442 858, extreme 221 427, huge 442 858, nearzero 442 858, overflow 221 428, points 442 858, pow2 221 427, underflow 221 429, uniform 221 429, zero 221 428.

### `ball_zero_2`

Claims: `certain(m) eq(x, 0) over x=[c +- r], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:4:-8:3`, every operand (another number of exponents) | 971 674 | 971 674 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 35 390 | 35 390 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 888 | 5 888 | 0 |
| `fp:1:-3:4`, every operand (p = min_precision, the quick tier's number of exponents) | 911 | 911 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 2 bits) | 4 681 442 | 4 681 442 | 0 |
| `fp:5:-7:0`, every operand (quick tier + 1 bit) | 1 018 226 | 1 018 226 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: ballstates 435 716, extreme 217 856, huge 435 715, nearzero 435 716, overflow 217 856, points 435 714, pow2 217 856, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: ballstates 435 716, extreme 217 856, huge 435 715, nearzero 435 716, overflow 217 856, points 435 714, pow2 217 856, underflow 217 857, uniform 217 858, zero 217 856.

### `bound_dot_1`

Claims: `holds le(m*unit(mul_1_1), 1/2) if ok`; `upper(g) >= m*unit(mul_1_1)/(1-m*unit(mul_1_1)) if ok`; `upper(t) >= m*tiny(mul_1_1)*(1+g) if ok`.

| Run | Cases | Judged | Failed | largest m*unit(mul_1_1) where ok | smallest excess over the stated value, gaps | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 2.84394 | 4.50360e+15 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 2.84385 | 8.38861e+6 |
| `fp:20:-50:20`, every operand (another exponent range) | 20 971 521 | 20 971 521 | 0 | 0.250000 | 2.84375 | 524288 |
| `fp:13:-30:12`, every operand (quick tier + 1 bit) | 102 401 | 102 401 | 0 | 0.249939 | 2.84393 | 4096.50 |
| `fp:3:-30:12`, every operand (p = min_precision + 2, the quick tier's exponent range) | 61 | 61 | 0 | 0.194444 | 2.83871 | 5.60938 |
| `fp:2:-30:12`, every operand (p = min_precision + 1, the quick tier's exponent range) | 29 | 29 | 0 | 0 | - | - |
| `fp:16:-30:14`, every operand (another exponent range) | 983 041 | 983 041 | 0 | 0.249985 | 2.92187 | 32768.5 |
| `fp:1:-30:12`, every operand (p = min_precision, the quick tier's exponent range) | 14 | 14 | 0 | 0 | - | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
largest m*unit(mul_1_1) where ok, compiled 0.250000 (clang18-fixup-call/cxx, linux-x86-64):
  bound_dot_1 binary64 0x1.fffffffffffffp+50 #extreme:236 -> 0x1.8000000000001p-2 0x1.6000000000002p-971 1
largest m*unit(mul_1_1) where ok, interpreter 0.250000 (fp:20:-50:20, every operand):
  bound_dot_1 fp:20:-50:20 0x1.ffffep+17 #exhaustive:9437184 -> 0x1.80002p-2 0x1.60004p-13 1
smallest excess over the stated value, gaps, compiled 2.84385 (clang-fixup-inline/cxx, macos-arm64):
  bound_dot_1 binary32 0x1.3ff78cp+0 #fraction:13989 -> 0x1.3ff792p-24 0x1.3ff794p-126 1
smallest excess over the stated value, gaps, interpreter 2.83871 (fp:3:-30:12, every operand):
  bound_dot_1 fp:3:-30:12 0x1.4p+0 #exhaustive:2 -> 0x1p-2 0x1.8p-27 1
smallest excess over the stated value, gaps, compiled 2.84385 (clang-fixup-inline/cxx, macos-arm64):
  bound_dot_1 binary32 0x1.3ff78cp+0 #fraction:13989 -> 0x1.3ff792p-24 0x1.3ff794p-126 1
smallest excess over the stated value, gaps, interpreter 2.83871 (fp:3:-30:12, every operand):
  bound_dot_1 fp:3:-30:12 0x1.4p+0 #exhaustive:2 -> 0x1p-2 0x1.8p-27 1
```

### `bound_dot_2`

Claims: `holds le(m*unit(mul_2_2), 1/2) if ok`; `upper(g) >= m*unit(mul_2_2)/(1-m*unit(mul_2_2)) if ok`; `upper(t) >= m*tiny(mul_2_2)*(1+g) if ok`.

| Run | Cases | Judged | Failed | largest m*unit(mul_2_2) where ok | smallest excess over the stated value, gaps | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 2.80509 | 4.50360e+15 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 2.80493 | 8.38861e+6 |
| `fp:13:-30:12`, every operand (quick tier + 1 bit) | 102 401 | 102 401 | 0 | 0.246155 | 1.51562 | 4095.50 |
| `fp:5:-30:12`, every operand (p = min_precision + 1, the quick tier's exponent range) | 273 | 273 | 0 | 0.242188 | 2.29173 | 15.7003 |
| `fp:20:-50:20`, every operand (another exponent range) | 20 971 521 | 20 971 521 | 0 | 0.249939 | 1.50781 | 524288 |
| `fp:16:-30:14`, every operand (another exponent range) (**INCOMPLETE or guard failed**) | 983 041 | 983 041 | 0 | 0.125 | 1.83334 | 32767.5 |
| `fp:4:-30:12`, every operand (p = min_precision, the quick tier's exponent range) | 129 | 129 | 0 | 0.234375 | 2.33066 | 7.82373 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
largest m*unit(mul_2_2) where ok, compiled 0.250000 (clang18-fixup-call/cxx, linux-x86-64):
  bound_dot_2 binary64 0x1.fffffffffffffp+101 #extreme:68 -> 0x1.8000000000003p-2 0x1.6000000000005p-920 1
largest m*unit(mul_2_2) where ok, interpreter 0.249939 (fp:20:-50:20, every operand):
  bound_dot_2 fp:20:-50:20 0x1.ffe02p+35 #exhaustive:18874114 -> 0x1.80182p-2 0x1.5ff0cp+5 1
smallest excess over the stated value, gaps, compiled 2.80493 (clang18-fixup-call/cxx, linux-x86-64):
  bound_dot_2 binary32 0x1.3fcd9p+20 #integer:7071 -> 0x1.3fcd96p-26 0x1.3fcd9ap-106 1
smallest excess over the stated value, gaps, interpreter 1.50781 (fp:20:-50:20, every operand):
  bound_dot_2 fp:20:-50:20 0x1.00f7ep+0 #exhaustive:1984 -> 0x1.011p-38 0x1.00f86p-31 1
smallest excess over the stated value, gaps, compiled 2.80493 (clang18-fixup-call/cxx, linux-x86-64):
  bound_dot_2 binary32 0x1.3fcd9p+20 #integer:7071 -> 0x1.3fcd96p-26 0x1.3fcd9ap-106 1
smallest excess over the stated value, gaps, interpreter 1.50781 (fp:20:-50:20, every operand):
  bound_dot_2 fp:20:-50:20 0x1.00f7ep+0 #exhaustive:1984 -> 0x1.011p-38 0x1.00f86p-31 1
```

### `bound_sum_1`

Claims: `holds le(m*unit(add_1_1), 1/2) if ok`; `upper(g) >= m*unit(add_1_1)/(1-m*unit(add_1_1)) if ok`.

| Run | Cases | Judged | Failed | largest m*unit(add_1_1) where ok | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 2.84562 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 2.84391 |
| `fp:13:-30:12`, every operand (quick tier + 1 bit) | 102 401 | 102 401 | 0 | 0.249939 | 2.84393 |
| `fp:3:-30:12`, every operand (p = min_precision + 2, the quick tier's exponent range) | 61 | 61 | 0 | 0.194444 | 2.83871 |
| `fp:20:-50:20`, every operand (another exponent range) | 20 971 521 | 20 971 521 | 0 | 0.250000 | 2.84375 |
| `fp:16:-30:14`, every operand (another exponent range) | 983 041 | 983 041 | 0 | 0.249985 | 2.92187 |
| `fp:2:-30:12`, every operand (p = min_precision + 1, the quick tier's exponent range) | 29 | 29 | 0 | 0 | - |
| `fp:1:-30:12`, every operand (p = min_precision, the quick tier's exponent range) | 14 | 14 | 0 | 0 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
largest m*unit(add_1_1) where ok, compiled 0.250000 (clang18-fixup-call/cxx, linux-x86-64):
  bound_sum_1 binary64 0x1.fffffffffffffp+50 #extreme:348 -> 0x1.8000000000001p-2 1
largest m*unit(add_1_1) where ok, interpreter 0.250000 (fp:20:-50:20, every operand):
  bound_sum_1 fp:20:-50:20 0x1.ffffep+17 #exhaustive:9437184 -> 0x1.80002p-2 1
smallest excess over the stated value, gaps, compiled 2.84391 (msvc-fixup-call/cxx, windows-x64):
  bound_sum_1 binary32 0x1.3ff228p+0 #fraction:7479 -> 0x1.3ff22e0000000p-24 1
smallest excess over the stated value, gaps, interpreter 2.83871 (fp:3:-30:12, every operand):
  bound_sum_1 fp:3:-30:12 0x1.4p+0 #exhaustive:2 -> 0x1p-2 1
```

### `bound_sum_2`

Claims: `holds le(m*unit(add_2_2), 1/2) if ok`; `upper(g) >= m*unit(add_2_2)/(1-m*unit(add_2_2)) if ok`.

| Run | Cases | Judged | Failed | largest m*unit(add_2_2) where ok | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 1.76561 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.250000 | 1.76235 |
| `fp:16:-30:14`, every operand (another exponent range) (**INCOMPLETE or guard failed**) | 983 041 | 983 041 | 0 | 0.0937557 | 1.06244 |
| `fp:13:-30:12`, every operand (quick tier + 1 bit) | 102 401 | 102 401 | 0 | 0.245023 | 1.50757 |
| `fp:20:-50:20`, every operand (another exponent range) | 20 971 521 | 20 971 521 | 0 | 0.249920 | 1.49023 |
| `fp:4:-30:12`, every operand (p = min_precision + 1, the quick tier's exponent range) | 129 | 129 | 0 | 0.234375 | 2.33066 |
| `fp:3:-30:12`, every operand (p = min_precision, the quick tier's exponent range) | 61 | 61 | 0 | 0.234375 | 1.85981 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: beyond 17 857, extreme 17 855, fraction 17 858, integer 53 571, limit 53 573, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
largest m*unit(add_2_2) where ok, compiled 0.250000 (clang18-fixup-call/cxx, linux-x86-64):
  bound_sum_2 binary64 0x1.5555555555552p+102 #extreme:26 -> 0x1.8000000000003p-2 1
largest m*unit(add_2_2) where ok, interpreter 0.249920 (fp:20:-50:20, every operand):
  bound_sum_2 fp:20:-50:20 0x1.5538ep+36 #exhaustive:19048904 -> 0x1.802p-2 1
smallest excess over the stated value, gaps, compiled 1.76235 (clang18-fixup-call/cxx, linux-x86-64):
  bound_sum_2 binary32 0x1.666p+20 #integer:47671 -> 0x1.0cc808p-26 1
smallest excess over the stated value, gaps, interpreter 1.06244 (fp:16:-30:14, every operand):
  bound_sum_2 fp:16:-30:14 0x1.4p+0 #exhaustive:8193 -> 0x1p-29 1
```

### `bv_add_1`

Claims: `encloses_entries(z, r) x+y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when |abs(x+y)+rx+ry| <= 2^(qmax+p-2)`; `V3, step add_1_1: rounded(s) nearest`; `V3, step add_1_1: error(s) form R, c=1/(1+u), k=1, t=0`; `V3, radius bv_add_radius_1: upper(rz) >= rx+ry+m*unit(add_1_1)/(1-unit(add_1_1))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | cases by rounding | largest error / bound | observed c | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.64605 | exact 4 944 816; inexact 15 945 936; tie 32 280 | 1 - ε, ε < 10⁻⁹ | 1.00000 | 1.45465 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.5 | exact 5 930 814; inexact 15 854 454; tie 229 248 | 0.9999998808 | 0.9999998212 | 1.23242 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 26 115 244 | 26 115 244 | 0 | 1.5 | exact 7 439 445; inexact 2 617 472; tie 2 707 964 | 1 (the claim) | 0.8 | 1.5 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 2 375 522 | 2 375 522 | 0 | 1 | exact 651 659; inexact 705 816; tie 299 260 | 1 (the claim) | 0.888889 | 1 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 1 elements) | 36 602 | 36 602 | 0 | 1.5 | exact 6 657; inexact 2 080; tie 2 380 | 1 (the claim) | 0.8 | 1.5 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 167, one 333, overflow 167, threshold 500, underflow 165, whole 168, wide 168, zeroradius 167, zeros 165; `binary32`: cancel 167, one 333, overflow 167, threshold 500, underflow 165, whole 168, wide 168, zeroradius 167, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 1.5 (msvc/avx2, windows-x64):
  bv_add_1 binary32 lanes:8 1100 0x1.bfc8f2p+53 0x1.7604cp+51 -0x1.509abep+58 0x1.094e62p+57 0x1.d36714p+56 -0x1.971026p+58 0x1.27477cp+56 0x1.86bccep+54 -0x1.e564dep+55 0x1.d1bffap+57 0x1.76fffcp+56 ... (2191 more) #cancel:16 -> -0x1.0000000000000p+35 0x1.0000000000000p+34 0x0.0000000000000p+0 0x1.0000000000000p+35 ... (1098 more)
smallest radius slack, gaps (the worst entry), interpreter 1 (fp:3:-4:1, every operand):
  bv_add_1 fp:3:-4:1 seq 1 0x1p+3 0x1p+0 0x1.4p+2 -0x1.cp+3 #exhaustive:20701 -> -0x1p+3 0x1.8p+3 1
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18/avx2, linux-x86-64):
  add_1_1 binary64 -0x1.ffffffffffffdp+1021 0x1p+1023 #bv_add_1:overflow:77:entry:4 -> 0x1.0000000000002p+1022
largest error / bound, interpreter 1 (fp:2:-2:1, every operand):
  add_1_1 fp:2:-2:1 0x1p+0 -0x1.8p+2 #bv_add_1:exhaustive:251:entry:0 -> -0x1p+2
smallest excess over the stated value, gaps, compiled 1.23242 (clang18/avx2, linux-x86-64):
  bv_add_1 binary32 lanes:8 8 0x1.98cfdp+96 0x1.2ac2p+108 -0x1.68e8bap+121 -0x1.929d8p+124 0x1.9b81aep+124 -0x1.e43dbcp+120 0x1.242d2ap+124 -0x1.dfe518p+122 0x1.6016e4p+120 0x1.e9a6bep+120 ... (8 more) #threshold:707 -> -0x1.02595p+125 0x1.2bcf3p+121 0x1.625638p+124 -0x1.8bffcap+124 0x1.a71344p+124 -0x1.20b646p+125 ... (4 more)
smallest excess over the stated value, gaps, interpreter 1 (fp:3:-4:1, every operand):
  bv_add_1 fp:3:-4:1 seq 1 0x1p+2 0x1p-1 0x1.4p+3 -0x1.cp+3 #exhaustive:14645 -> -0x1p+2 0x1.8p+2 1
```

### `bv_add_2`

Claims: `encloses_entries(z, r) x+y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when |abs(x+y)+rx+ry| <= 2^(qmax+p-2)`; `V3, step add_2_2: normalized(z)`; `V3, step add_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`; `V3, radius bv_add_radius_2: upper(rz) >= rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | largest error / bound | observed c | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.50000 | 0.619937 | 1.44334 | 1.15392 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.46777 | 0.570071 | 1.71021 | 1.21094 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 140 304 866 | 140 304 866 | 0 | 1.25 | 0.273504 | - | 1.03448 |
| `fp:3:-2:-1`, every operand (the full tier's format, every array up to 1 elements) | 121 970 | 121 970 | 0 | 3.5 | 0 | - | 3.44181 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 155, one 308, overflow 155, tail 153, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153; `binary32`: cancel 155, one 308, overflow 155, tail 153, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 1.46777 (clang18/avx2, linux-x86-64):
  bv_add_2 binary32 lanes:8 3605 0x1.244b3ep+105 0x1.ea8be4p+95 0x1.3eda8ep+125 0x1.299b16p+125 0x1.85d8e8p+123 -0x1.632d2p+121 -0x1.2b56f8p+125 0x1.fe8f9cp+123 0x1.09670ep+123 -0x1.0e371cp+122 ... (14412 more) #threshold:521 -> 0x1.3f4292p+125 0x1.2a1388p+125 0x1.83dc2ep+123 -0x1.67beeap+121 -0x1.2aa03ap+125 0x1.fff8dep+123 ... (7206 more)
smallest radius slack, gaps (the worst entry), interpreter 1.25 (fp:3:-4:1, every operand):
  bv_add_2 fp:3:-4:1 seq 1 0x1.cp+2 0x1.cp-2 0x1.cp+0 0x1p-4 -0x1.4p+2 -0x1.8p-2 #exhaustive:41547999 -> -0x1.cp+1 0x0p+0 0x1.4p+3 1
largest error / bound, compiled 0.619937 (msvc/avx2, windows-x64):
  add_2_2 binary64 -0x1.ea1dc5f53e758p-967 0x1.ce22c74edaa7p-1026 0x1.31eddf42f5edep-963 0x1p-1016 #bv_add_2:underflow:385:entry:638 -> 0x1.134c02e3a2069p-963 0x1.ce22c74edae7p-1026
largest error / bound, interpreter 0.273504 (fp:3:-4:1, every operand):
  add_2_2 fp:3:-4:1 0x1.4p+1 0x1.8p-3 -0x1p+3 0x1.cp-2 #bv_add_2:exhaustive:29857353:entry:0 -> -0x1.4p+2 0x0p+0
smallest excess over the stated value, gaps, compiled 1.15392 (clang18-fixup-call/cxx, linux-x86-64):
  bv_add_2 binary64 lanes:4 4096 0x1.bc4bb2d691f1dp+947 0x1.555f9bd620047p+945 -0x1.59a4cf48c5a35p+1019 0x1.ab836915a6d1dp+1019 -0x1.5438298925af5p+1022 -0x1.59369ad47e0a2p+1021 0x1.17ef743b0a5a7p+1022 ... (16379 more) #threshold:813 -> -0x1.59a4cf48c5a32p+1019 0x1.ab836915a6d1ep+1019 -0x1.5438298925af5p+1022 -0x1.59369ad47e0a3p+1021 ... (8190 more)
smallest excess over the stated value, gaps, interpreter 1.03448 (fp:3:-4:1, every operand):
  bv_add_2 fp:3:-4:1 seq 1 0x1p+2 0x1p-1 0x1.4p+3 0x1.4p-2 -0x1.cp+3 -0x1.cp-1 #exhaustive:105925 -> -0x1p+2 -0x1p-1 0x1.8p+2 1
```

### `bv_add_radius_1`

Claims: `upper(rz) >= rx+ry+m*unit(add_1_1)/(1-unit(add_1_1))`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1 |
| `fp:4:-8:4`, every operand (another exponent range) | 1 404 928 | 1 404 928 | 0 | 1 |
| `fp:4:-5:3`, every operand (quick tier + 1 bit) | 512 000 | 512 000 | 0 | 1 |
| `fp:3:-5:3`, every operand (p = min_precision + 2, the quick tier's format) | 64 000 | 64 000 | 0 | 1 |
| `fp:2:-5:3`, every operand (p = min_precision + 1, the quick tier's exponent range) | 8 000 | 8 000 | 0 | 1 |
| `fp:1:-5:3`, every operand (p = min_precision, the quick tier's exponent range) | 1 000 | 1 000 | 0 | 1.25 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858; `binary32`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  bv_add_radius_1 binary64 0x1p+1023 0x1.31e45c90e18dap+1022 0x1.ffffffffffffep+1021 #overflow:5958 -> 0x1.18f22e4870c6ep+1023
smallest excess over the stated value, gaps, interpreter 1 (fp:4:-8:4, every operand):
  bv_add_radius_1 fp:4:-8:4 0x1p+0 0x1p-4 0x1p+0 #exhaustive:603952 -> 0x1.4p+0
```

### `bv_add_radius_2`

Claims: `upper(rz) >= rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.05316 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.00323 |
| `fp:4:-8:4`, every operand (p = min_precision + 1, another exponent range) | 1 404 928 | 1 404 928 | 0 | 1.06324 |
| `fp:3:-5:3`, every operand (p = min_precision, the quick tier's format) | 64 000 | 64 000 | 0 | 1.03448 |
| `fp:4:-5:3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 512 000 | 512 000 | 0 | 1.13914 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858; `binary32`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 1.00323 (msvc-fixup-call/cxx, windows-x64):
  bv_add_radius_2 binary32 0x1.bfdcb2p-2 0x1.2e59ep-31 0x1.f2f312p-29 #mixed:25005 -> 0x1.1f44dc0000000p-28
smallest excess over the stated value, gaps, interpreter 1.03448 (fp:3:-5:3, every operand):
  bv_add_radius_2 fp:3:-5:3 0x1p+1 0x1p-2 0x1p+1 #exhaustive:32340 -> 0x1.8p+1
```

### `bv_center_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`; `represents(z)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | 0 (exact) | 0 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | 0 (exact) | - |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | 0 (exact) | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | 0 (exact) | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | 0 (exact) | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000; `binary32`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000.

### `bv_center_entry_1`

Claims: `rounded(z) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `fp:12:-30:10`, every operand (quick tier + 1 bit) | 172 031 | 172 031 | 0 | exact 172 031 |
| `fp:3:-30:10`, every operand (p = min_precision + 2, the quick tier's exponent range) | 335 | 335 | 0 | exact 335 |
| `fp:2:-30:10`, every operand (p = min_precision + 1, the quick tier's exponent range) | 167 | 167 | 0 | exact 167 |
| `fp:1:-30:10`, every operand (p = min_precision, the quick tier's exponent range) | 83 | 83 | 0 | exact 83 |
| `fp:13:-60:40`, every operand (another exponent range) | 835 583 | 835 583 | 0 | exact 835 583 |
| `fp:13:-30:10`, every operand (quick tier + 2 bits) | 344 063 | 344 063 | 0 | exact 344 063 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

### `bv_conv_1`

Claims: `encloses_coefficients(z, r) x*y over x=[x +- rx], y=[y +- ry], V1-V4, flag flag`; `V3, coefficients, fold dot_1: fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1`.

| Run | Cases | Judged | Failed | largest error / bound, order sequential |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.999225 |
| `binary32`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.991034 |
| `fp:4:-4:-1`, every operand (another format, every array up to 1 elements) | 10 252 804 | 10 252 804 | 0 | 0.944444 |
| `fp:4:-3:-2`, every operand (another format, every array up to 1 elements) | 1 331 716 | 1 331 716 | 0 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 181, count 183, one 183, overflow 181, threshold 364, underflow 181, whole 183, wide 183, zeroradius 181, zeros 180; `binary32`: cancel 181, count 183, one 183, overflow 181, threshold 364, underflow 181, whole 183, wide 183, zeroradius 181, zeros 180.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order sequential, compiled 0.999225 (msvc-fixup-call/cxx, windows-x64):
  bv_conv_1 binary64 seq 9 1 0x1.ced113430decfp-25 0x1.012bab28009e5p-12 -0x1.8879d5fef283dp+24 0x1.3b4e2d2e2ac87p+23 -0x1.25f68c431f4b5p+27 -0x1.c7600064ad941p+26 -0x1.c7f4e9d4e0e66p+24 ... (5 more) #cancel:31 -> -0x1.b97ff46131fc8p+48 0x1.62b0a1103a11dp+47 -0x1.4aae8adc7e60ep+51 -0x1.0020b724abc22p+51 ... (7 more)
largest error / bound, order sequential, interpreter 0.944444 (fp:4:-4:-1, every operand):
  bv_conv_1 fp:4:-4:-1 seq 1 1 0x0p+0 0x0p+0 -0x1p-4 -0x1p-1 #exhaustive:4182043 -> 0x0p+0 0x1.2p+1 1
```

### `bv_conv_2`

Claims: `encloses_coefficients(z, r) x*y over x=[x +- rx], y=[y +- ry], V1-V4, flag flag`; `V3, coefficients, fold dot_2: normalized(r)`; `V3, coefficients, fold dot_2: fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`.

| Run | Cases | Judged | Failed | largest error / bound, order sequential |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.557135 |
| `binary32`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.725159 |
| `fp:4:-4:-1`, every operand (another format, every array up to 1 elements) | 98 446 084 | 98 446 084 | 0 | 0.561075 |
| `fp:4:-3:-2`, every operand (another format, every array up to 1 elements) | 2 220 100 | 2 220 100 | 0 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 165, count 167, one 168, overflow 167, tail 165, threshold 335, underflow 165, whole 168, wide 168, zeroradius 167, zeros 165; `binary32`: cancel 165, count 167, one 168, overflow 167, tail 165, threshold 335, underflow 165, whole 168, wide 168, zeroradius 167, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order sequential, compiled 0.725159 (clang18-fixup-call/cxx, linux-x86-64):
  bv_conv_2 binary32 seq 1 150 0x0p+0 0x0p+0 0x1.c303dcp-23 -0x1.812eecp-48 -0x1.c434d8p-22 0x1.2314e6p-26 0x1.712aa6p-28 0x1.b9448cp-28 -0x1.862ea6p-27 0x1.728c8p-27 -0x1.fa57a6p-23 -0x1.386bf2p-23 ... (292 more) #zeroradius:906 -> -0x1.8e57f4p-44 0x1.00691ap-48 0x1.4531dap-50 0x1.84b534p-50 -0x1.57b508p-49 0x1.46698cp-49 ... (296 more)
largest error / bound, order sequential, interpreter 0.561075 (fp:4:-4:-1, every operand):
  bv_conv_2 fp:4:-4:-1 seq 1 1 0x0p+0 0x0p+0 -0x1.cp-2 0x0p+0 -0x1.8p+0 -0x1p-4 #exhaustive:39550083 -> 0x1.4p-1 0x0p+0 0x1.4p+1 1
```

### `bv_conv_finish`

Claims: `finite_or_nan(r) flag flag if all of okc, okg`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 3 309 576 | 3 309 576 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 671 752 | 671 752 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 664 | 664 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 336 | 336 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 1 320 | 1 320 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 221 427, masks 442 858, negative 442 858, nonfinite 442 858, overflow 221 428, pow2 221 427, top 221 429, underflow 221 429, uniform 221 429, zero 221 428, zeros 221 429; `binary32`: extreme 221 427, masks 442 858, negative 442 858, nonfinite 442 858, overflow 221 428, pow2 221 427, top 221 429, underflow 221 429, uniform 221 429, zero 221 428, zeros 221 429.

### `bv_make_1`

Claims: `makes_ball_vector(z, rr) from centers c, radius r, flag finite`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 |
| `fp:2:-2:1`, every operand (another format, every array up to 3 elements) | 724 570 | 724 570 | 0 |
| `fp:3:-4:1`, every operand (another format, every array up to 2 elements) | 393 646 | 393 646 | 0 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 21 802 | 21 802 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: badcenter 251, badradius 751, one 251, overflow 249, underflow 249, zeros 249; `binary32`: badcenter 251, badradius 751, one 251, overflow 249, underflow 249, zeros 249.

### `bv_make_2`

Claims: `makes_ball_vector(z, rr) from centers c, radius r, flag finite`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 149 314 | 149 314 | 0 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 24 766 | 24 766 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: badcenter 223, badradius 667, one 224, overflow 221, tail 221, underflow 221, zeros 223; `binary32`: badcenter 223, badradius 667, one 224, overflow 221, tail 221, underflow 221, zeros 223.

### `bv_make_finish`

Claims: `finite_or_nan(r) flag flag if ok, not below zero`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 335 876 | 335 876 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 1 654 788 | 1 654 788 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 660 | 660 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 332 | 332 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 168 | 168 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 221 427, masks 442 858, negative 442 858, nonfinite 442 858, overflow 221 428, pow2 221 427, top 221 429, underflow 221 429, uniform 221 429, zero 221 428, zeros 221 429; `binary32`: extreme 221 427, masks 442 858, negative 442 858, nonfinite 442 858, overflow 221 428, pow2 221 427, top 221 429, underflow 221 429, uniform 221 429, zero 221 428, zeros 221 429.

### `bv_make_radius`

Claims: `rounded(rz) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 303 809 | 0 | exact 5 303 809 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 765 569 | 0 | exact 2 765 569 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 690 561 | 0 | exact 690 561 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 609 | 0 | exact 10 609 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 601 | 0 | exact 2 601 |
| `fp:1:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 625 | 0 | exact 625 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

### `bv_mul_pow2_1`

Claims: `encloses_entries(z, r) x*c over x=[x +- rx], V1-V4, flag finite, finite when |(abs(x)+rx)*c| <= 2^(qmax+p-2), exactly the set when (x*c = 0 or |x*c| > eta/(2*u)) and (rx*c = 0 or |rx*c| > eta/(2*u))`; `V3, step bv_mul_pow2_step_1: rounded(z) nearest`; `V3, step bv_mul_pow2_step_1: error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or |x*c| > eta/(2*u)), exact_flag e`; `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or |rx*c| > eta/(2*u))`; `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c+eta unless ex`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | cases by rounding | largest error / bound | observed c | smallest excess over the stated value, gaps | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | exact 18 979 158; inexact 1 364 886; tie 287 742 | 1 (the claim) | 0 | 0 | 0.515625 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | exact 17 471 784; inexact 1 136 640; tie 250 536 | 1 (the claim) | 0 | 0 | 0.5 |
| `fp:3:-4:1`, every operand (another format, every array up to 2 elements) | 1 367 776 | 1 367 776 | 0 | 0 | exact 1 593 660; inexact 297 024; tie 198 016 | 1 (the claim) | 0 | 0 | 0.5 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 37 120 | 37 120 | 0 | 0 | exact 43 392; inexact 3 080; tie 6 160 | 1 (the claim) | 0 | 0 | 0.5 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 155, exact 153, one 308, overflow 155, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153; `binary32`: cancel 155, exact 153, one 308, overflow 155, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_1 binary64 lanes:1 3 0x1.6f7ebbd7607b2p-580 0x1p-40 0x1.6273545dfffp-565 -0x1.3980cb1fb16fep-567 -0x1.7fe9977bb1f91p-566 #cancel:4 -> 0x1.6273545dfffp-605 -0x1.3980cb1fb16fep-607 -0x1.7fe9977bb1f91p-606 0x1.6f7ebbd7607b2p-620 1
smallest radius slack, gaps (the worst entry), interpreter 0 (fp:3:-4:1, every operand):
  bv_mul_pow2_1 fp:3:-4:1 seq 1 0x0p+0 0x1p-4 -0x1.cp+3 #exhaustive:232 -> -0x1.cp-1 0x0p+0 1
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_step_1 binary64 -0x1.fffffffffffffp-985 0x1p-38 #bv_mul_pow2_1:exact:9:entry:0 -> -0x1p-1022 0
largest error / bound, interpreter 1 (fp:3:-4:1, every operand):
  bv_mul_pow2_step_1 fp:3:-4:1 -0x1.cp+1 0x1p-4 #bv_mul_pow2_1:exhaustive:456:entry:0 -> -0x1p-2 0
smallest excess over the stated value, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_1 binary64 lanes:1 3 0x1.6f7ebbd7607b2p-580 0x1p-40 0x1.6273545dfffp-565 -0x1.3980cb1fb16fep-567 -0x1.7fe9977bb1f91p-566 #cancel:4 -> 0x1.6273545dfffp-605 -0x1.3980cb1fb16fep-607 -0x1.7fe9977bb1f91p-606 0x1.6f7ebbd7607b2p-620 1
smallest excess over the stated value, gaps, interpreter 0 (fp:3:-4:1, every operand):
  bv_mul_pow2_1 fp:3:-4:1 seq 0 0x1.4p+2 0x1p-4 #exhaustive:21 -> 0x1.4p-2 1
smallest excess over the stated value, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_1 binary64 lanes:1 3 0x1.6f7ebbd7607b2p-580 0x1p-40 0x1.6273545dfffp-565 -0x1.3980cb1fb16fep-567 -0x1.7fe9977bb1f91p-566 #cancel:4 -> 0x1.6273545dfffp-605 -0x1.3980cb1fb16fep-607 -0x1.7fe9977bb1f91p-606 0x1.6f7ebbd7607b2p-620 1
smallest excess over the stated value, gaps, interpreter 0 (fp:3:-4:1, every operand):
  bv_mul_pow2_1 fp:3:-4:1 seq 0 0x1.4p+2 0x1p-4 #exhaustive:21 -> 0x1.4p-2 1
```

### `bv_mul_pow2_2`

Claims: `encloses_entries(z, r) x*c over x=[x +- rx], V1-V4, flag finite, finite when |(abs(x)+rx)*c| <= 2^(qmax+p-2), exactly the set when (x[0]*c = 0 or |x[0]*c| > eta/(2*u)) and (x[1]*c = 0 or |x[1]*c| > eta/(2*u)) and (rx*c = 0 or |rx*c| > eta/(2*u))`; `V3, step bv_mul_pow2_step_2: normalized(z)`; `V3, step bv_mul_pow2_step_2: error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or |x[0]*c| > eta/(2*u)) and (x[1]*c = 0 or |x[1]*c| > eta/(2*u)), exact_flag e`; `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or |rx*c| > eta/(2*u))`; `V3, radius bv_mul_pow2_radius: upper(rz) >= rx*c+eta unless ex`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | largest error / bound | observed c | smallest excess over the stated value, gaps | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | 0.730516 | 3.79819e-18 | 0 | 0.519531 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | 0.741699 | 2.85508e-8 | 0 | 0.5 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 305 320 | 305 320 | 0 | 0 | 0.5 | - | 0 | 0.5 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 94 992 | 94 992 | 0 | 0 | 0.6875 | - | 0 | 0.5 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 144, exact 143, one 285, overflow 144, tail 141, threshold 428, underflow 143, whole 144, wide 144, zeroradius 143, zeros 141; `binary32`: cancel 144, exact 143, one 285, overflow 144, tail 141, threshold 428, underflow 143, whole 144, wide 144, zeroradius 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_2 binary64 lanes:6 3 0x1.db566ac6d9e1p-875 0x1p-2 0x1.7bc90e0bb34f5p-828 0x1.04af7c4b450e4p-831 -0x1.a2ad90e90fb5bp-828 -0x1.4c441bf9f3124p-913 -0x1.e09a84ddfc9ep-938 0x1.73faac9bd5c7ep-883 #cancel:4 -> 0x1.7bc90e0bb34f5p-830 0x1.04af7c4b450e4p-833 -0x1.a2ad90e90fb5bp-830 -0x1.4c441bf9f3124p-915 -0x1.e09a84ddfc9ep-940 0x1.73faac9bd5c7ep-885 0x1.db566ac6d9e1p-877 1
smallest radius slack, gaps (the worst entry), interpreter 0 (fp:2:-2:1, every operand (the full tier's format, every array up to 2 elements)):
  bv_mul_pow2_2 fp:2:-2:1 seq 1 0x0p+0 0x1p-2 -0x1.8p+2 0x0p+0 #exhaustive:85 -> -0x1.8p+0 0x0p+0 0x0p+0 1
largest error / bound, compiled 0.741699 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_step_2 binary32 -0x1.e83c4ap-116 -0x1.efp-141 0x1p-11 #bv_mul_pow2_2:underflow:8:entry:687 -> -0x1.e83c48p-127 0x0p+0 0
largest error / bound, interpreter 0.6875 (fp:3:-4:1, every operand):
  bv_mul_pow2_step_2 fp:3:-4:1 -0x1.cp+1 0x1.8p-3 0x1p-4 #bv_mul_pow2_2:exhaustive:4656:entry:0 -> -0x1p-2 0x0p+0 0
smallest excess over the stated value, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_2 binary64 lanes:6 3 0x1.db566ac6d9e1p-875 0x1p-2 0x1.7bc90e0bb34f5p-828 0x1.04af7c4b450e4p-831 -0x1.a2ad90e90fb5bp-828 -0x1.4c441bf9f3124p-913 -0x1.e09a84ddfc9ep-938 0x1.73faac9bd5c7ep-883 #cancel:4 -> 0x1.7bc90e0bb34f5p-830 0x1.04af7c4b450e4p-833 -0x1.a2ad90e90fb5bp-830 -0x1.4c441bf9f3124p-915 -0x1.e09a84ddfc9ep-940 0x1.73faac9bd5c7ep-885 0x1.db566ac6d9e1p-877 1
smallest excess over the stated value, gaps, interpreter 0 (fp:2:-2:1, every operand (the full tier's format, every array up to 2 elements)):
  bv_mul_pow2_2 fp:2:-2:1 seq 0 0x1.8p+1 0x1p-2 #exhaustive:7 -> 0x1.8p-1 1
smallest excess over the stated value, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_2 binary64 lanes:6 3 0x1.db566ac6d9e1p-875 0x1p-2 0x1.7bc90e0bb34f5p-828 0x1.04af7c4b450e4p-831 -0x1.a2ad90e90fb5bp-828 -0x1.4c441bf9f3124p-913 -0x1.e09a84ddfc9ep-938 0x1.73faac9bd5c7ep-883 #cancel:4 -> 0x1.7bc90e0bb34f5p-830 0x1.04af7c4b450e4p-833 -0x1.a2ad90e90fb5bp-830 -0x1.4c441bf9f3124p-915 -0x1.e09a84ddfc9ep-940 0x1.73faac9bd5c7ep-885 0x1.db566ac6d9e1p-877 1
smallest excess over the stated value, gaps, interpreter 0 (fp:2:-2:1, every operand (the full tier's format, every array up to 2 elements)):
  bv_mul_pow2_2 fp:2:-2:1 seq 0 0x1.8p+1 0x1p-2 #exhaustive:7 -> 0x1.8p-1 1
```

### `bv_mul_pow2_radius`

Claims: `upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or |rx*c| > eta/(2*u))`; `upper(rz) >= rx*c+eta unless ex`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 0.5 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 | 0.5 |
| `fp:2:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 4 096 | 4 096 | 0 | 0 | 0.5 |
| `fp:5:-8:4`, every operand (another exponent range) | 1 705 984 | 1 705 984 | 0 | 0 | 0.5 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 360 448 | 360 448 | 0 | 0 | 0.5 |
| `fp:3:-4:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 18 432 | 18 432 | 0 | 0 | 0.5 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858; `binary32`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_radius binary64 0x1.0080000000002p-923 1 0x1.2p-1071 0x1p+49 #atnormal:59 -> 0x1.2p-1022
smallest excess over the stated value, gaps, interpreter 0 (fp:2:-4:2, every operand):
  bv_mul_pow2_radius fp:2:-4:2 0x0p+0 1 0x1p-4 0x1p+2 #exhaustive:142 -> 0x1p-2
smallest excess over the stated value, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_radius binary64 0x1.0080000000002p-923 1 0x1.2p-1071 0x1p+49 #atnormal:59 -> 0x1.2p-1022
smallest excess over the stated value, gaps, interpreter 0 (fp:2:-4:2, every operand):
  bv_mul_pow2_radius fp:2:-4:2 0x0p+0 1 0x1p-4 0x1p+2 #exhaustive:142 -> 0x1p-2
```

### `bv_mul_pow2_step_1`

Claims: `rounded(z) nearest`; `error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or |x*c| > eta/(2*u)), exact_flag e`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 96 796 926 | 0 | exact 63 564 768; inexact 26 837 820; tie 6 394 338 | 1 (the claim) | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 97 149 546 | 0 | exact 62 954 226; inexact 27 586 962; tie 6 608 358 | 1 (the claim) | 0 |
| `fp:8:-14:6`, every operand (quick tier + 1 bit) | 157 668 | 134 372 | 0 | exact 107 492; inexact 23 296; tie 3 584 | 1 (the claim) | 0 |
| `fp:1:-14:6`, every operand (p = min_precision, the quick tier's exponent range) | 903 | 861 | 0 | exact 651; inexact 182; tie 28 | 1 (the claim) | 0 |
| `fp:7:-20:10`, every operand (another exponent range) | 151 515 | 134 107 | 0 | exact 107 227; inexact 24 320; tie 2 560 | 1 (the claim) | 0 |
| `fp:3:-14:6`, every operand (p = min_precision + 2, the quick tier's exponent range) | 4 025 | 3 737 | 0 | exact 2 897; inexact 728; tie 112 | 1 (the claim) | 0 |
| `fp:2:-14:6`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 914 | 1 802 | 0 | exact 1 382; inexact 364; tie 56 | 1 (the claim) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 281 818, halfscaled 563 636, into 563 637, outof 281 818, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 817; `binary32`: extreme 281 818, halfscaled 563 636, into 563 637, outof 281 818, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 817.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  bv_mul_pow2_step_1 binary64 0x1p-1074 0x1p-1 #extreme:93575 -> 0x0p+0 0
largest error / bound, interpreter 1 (fp:8:-14:6, every operand):
  bv_mul_pow2_step_1 fp:8:-14:6 -0x1.fep+6 0x1p-14 #exhaustive:25088 -> -0x1p-7 0
```

### `bv_mul_pow2_step_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=1, exact when (x[0]*c = 0 or |x[0]*c| > eta/(2*u)) and (x[1]*c = 0 or |x[1]*c| > eta/(2*u)), exact_flag e`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 740 856 | 0 | 0.664108 | 1.01632e-18 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 762 168 | 0 | 0.716378 | 1.72055e-8 |
| `fp:6:-12:4`, every operand (another exponent range) | 6 021 994 | 4 488 874 | 0 | 0.746094 | 0.00781249 |
| `fp:7:-6:2`, every operand (quick tier + 2 bits) | 979 185 | 521 971 | 0 | 0.734375 | - |
| `fp:6:-6:2`, every operand (quick tier + 1 bit) | 398 706 | 231 604 | 0 | 0.734375 | - |
| `fp:3:-6:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 14 949 | 11 829 | 0 | 0.71875 | 0.0624390 |
| `fp:2:-6:2`, every operand (p = min_precision, the quick tier's exponent range) | 4 350 | 3 766 | 0 | 0.6875 | 0.124031 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 22 727, halfscaled 45 455, into 45 456, outof 22 728, overflow 22 727, pow2 22 727, underflow 22 727, uniform 22 728, zero 22 725; `binary32`: extreme 22 727, halfscaled 45 455, into 45 456, outof 22 728, overflow 22 727, pow2 22 727, underflow 22 727, uniform 22 728, zero 22 725.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.716378 (msvc-fixup-call/cxx, windows-x64):
  bv_mul_pow2_step_2 binary32 0x1.89da22p+11 0x1.bb2486p-14 0x1p-138 #uniform:72028 -> 0x1.89da200000000p-127 0x0.0000000000000p+0 0
largest error / bound, interpreter 0.746094 (fp:6:-12:4, every operand):
  bv_mul_pow2_step_2 fp:6:-12:4 -0x1.f8p+4 0x1.f8p-3 0x1p-12 #exhaustive:2032404 -> -0x1p-7 0x0p+0 0
```

### `bv_neg_1`

Claims: `encloses_entries(z, r) -x over x=[x +- rx], V1-V4, flag finite, finite when |abs(x)+rx| <= 2^(qmax+p+1), exactly the set`; `V3, step neg_1: rounded(z) nearest`; `V3, radius bv_neg_radius: rounded(rz) nearest`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | cases by rounding | cases by rounding |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | exact 24 702 012 | exact 58 122 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | exact 22 809 786 | exact 58 122 |
| `fp:2:-3:2`, every operand (another format, every array up to 3 elements) | 847 497 | 847 497 | 0 | 0 | exact 2 521 260 | exact 847 490 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 7 424 | 7 424 | 0 | 0 | exact 14 630 | exact 7 420 |
| `fp:3:-4:1`, every operand (another format, every array up to 2 elements) | 170 972 | 170 972 | 0 | 0 | exact 340 340 | exact 170 968 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 155, exact 153, one 308, overflow 155, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153; `binary32`: cancel 155, exact 153, one 308, overflow 155, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_neg_1 binary64 lanes:7 3 0x1.38043b72c3557p-508 0x1.58332bd198244p-434 0x1.fd26c36eafd64p-433 0x1.403693c1e74cep-434 #cancel:4 -> -0x1.58332bd198244p-434 -0x1.fd26c36eafd64p-433 -0x1.403693c1e74cep-434 0x1.38043b72c3557p-508 1
smallest radius slack, gaps (the worst entry), interpreter 0 (fp:2:-3:2, every operand):
  bv_neg_1 fp:2:-3:2 seq 1 0x0p+0 -0x1.8p+3 #exhaustive:15 -> 0x1.8p+3 0x0p+0 1
```

### `bv_neg_2`

Claims: `encloses_entries(z, r) -x over x=[x +- rx], V1-V4, flag finite, finite when |abs(x)+rx| <= 2^(qmax+p+1), exactly the set`; `V3, step neg_2: normalized(z)`; `V3, step neg_2: error(z) form R, c=0, k=2, t=0`; `V3, step neg_2: represents(z)`; `V3, radius bv_neg_radius: rounded(rz) nearest`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | largest error / bound | observed c | cases by rounding |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | 0 (exact) | 0 | exact 58 464 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 | 0 (exact) | 0 | exact 58 464 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 11 874 | 11 874 | 0 | 0 | 0 (exact) | - | exact 11 872 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 61 064 | 61 064 | 0 | 0 | 0 (exact) | - | exact 61 060 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 144, exact 143, one 285, overflow 144, tail 141, threshold 428, underflow 143, whole 144, wide 144, zeroradius 143, zeros 141; `binary32`: cancel 144, exact 143, one 285, overflow 144, tail 141, threshold 428, underflow 143, whole 144, wide 144, zeroradius 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  bv_neg_2 binary64 seq 3 0x1.f9dbe15e0ea5cp+632 0x1.936eb8dbefb46p+722 0x1.1db37e0af50dbp+721 -0x1.2620fce88956dp+722 0x1.e0d8b1bf0b81ap+668 0x1.a2e55dfdebf21p+667 -0x1.a4999cc24a3fbp+616 #cancel:4 -> -0x1.936eb8dbefb46p+722 -0x1.1db37e0af50dbp+721 0x1.2620fce88956dp+722 -0x1.e0d8b1bf0b81ap+668 -0x1.a2e55dfdebf21p+667 0x1.a4999cc24a3fbp+616 0x1.f9dbe15e0ea5cp+632 1
smallest radius slack, gaps (the worst entry), interpreter 0 (fp:3:-4:1, every operand):
  bv_neg_2 fp:3:-4:1 seq 1 0x0p+0 -0x1.cp+3 -0x1.cp-1 #exhaustive:29 -> 0x1.cp+3 0x1.cp-1 0x0p+0 1
```

### `bv_neg_radius`

Claims: `rounded(rz) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 303 809 | 0 | exact 5 303 809 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 765 569 | 0 | exact 2 765 569 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 690 561 | 0 | exact 690 561 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 609 | 0 | exact 10 609 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 601 | 0 | exact 2 601 |
| `fp:1:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 625 | 0 | exact 625 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

### `bv_scale_1`

Claims: `encloses_entries(z, r) x*a over x=[x +- rx], V1-V4, flag finite, finite when |(abs(x)+rx)*a| <= 2^(qmax+p-2)`; `V3, step scale_step_1: rounded(z) nearest`; `V3, step scale_step_1: error(z) form R, c=1/(1+u), k=1, t=1/2`; `V3, radius bv_scale_radius_1: upper(rz) >= abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | cases by rounding | largest error / bound | observed c | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.50065 | exact 7 925 094; inexact 12 952 188; tie 12 624 | 0.999978 | 0.997998 | 1.08114 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.51216 | exact 8 259 396; inexact 12 716 016; tie 3 696 | 0.999968 | 0.998879 | 1.11296 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 163 328 | 163 328 | 0 | 1.75 | exact 97 986; inexact 23 908; tie 15 568 | 0.833333 | 0.444444 | 1.54688 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 91 060 | 91 060 | 0 | 1 | exact 25 466; inexact 21 988; tie 10 596 | 0.969697 | 0.888889 | 0.964844 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 155, nonfinite 153, one 308, overflow 155, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153; `binary32`: cancel 155, nonfinite 153, one 308, overflow 155, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 1.50065 (clang18/avx2, linux-x86-64):
  bv_scale_1 binary64 lanes:4 99 0x1.4f0168998b787p+117 -0x1.e7e90a2d36e07p+12 -0x1.cfaca9b1e537p-62 0x1.e08adf9be55c2p-27 0x1.73f7e4e4eef29p-109 0x1.21d9e3358a9bdp-90 0x1.a9e601c3489dep-113 ... (94 more) #wide:419 -> 0x1.b9dbc6b340aa8p-49 -0x1.c9eed070b12fp-14 -0x1.627797ec1c16cp-96 -0x1.1436ad082d5c5p-77 ... (97 more)
smallest radius slack, gaps (the worst entry), interpreter 1 (fp:3:-4:1, every operand):
  bv_scale_1 fp:3:-4:1 seq 1 0x1.8p-1 -0x1.8p+3 -0x1.8p-1 #exhaustive:3709 -> 0x1p+3 0x1.8p+3 1
largest error / bound, compiled 0.999978 (clang-fixup-inline/cxx, macos-arm64):
  scale_step_1 binary64 -0x1.c93b6676766dep-1011 -0x1.55b0ff212a478p-46 #bv_scale_1:underflow:203:entry:1950 -> 0x1.3124p-1056
largest error / bound, interpreter 0.969697 (fp:3:-4:1, every operand):
  scale_step_1 fp:3:-4:1 -0x1.8p-1 -0x1.8p+3 #bv_scale_1:exhaustive:3699:entry:0 -> 0x1p+3
smallest excess over the stated value, gaps, compiled 1.08114 (clang18/avx2, linux-x86-64):
  bv_scale_1 binary64 lanes:4 4 0x1.b5c85f6dd3d0ap+105 -0x1.5c681a58aa509p-4 0x1.5d0a31adbabd3p+133 0x1.ae5deb4496afdp+136 -0x1.1beae91364bccp+136 -0x1.fd933dbbe532dp+133 #cancel:329 -> -0x1.db07cb9845306p+129 -0x1.24db5721b499fp+133 0x1.8266c97d3e20fp+132 0x1.5ac1b016f8e65p+130 0x1.29e738aa728cdp+102 1
smallest excess over the stated value, gaps, interpreter 0.964844 (fp:3:-4:1, every operand):
  bv_scale_1 fp:3:-4:1 seq 1 0x1.8p-2 -0x1.8p+3 -0x1.8p-2 #exhaustive:3817 -> 0x1p+2 0x1.8p+2 1
```

### `bv_scale_2`

Claims: `encloses_entries(z, r) x*a over x=[x +- rx], V1-V4, flag finite, finite when |(abs(x)+rx)*a| <= 2^(qmax+p-2)`; `V3, step scale_step_2: normalized(z)`; `V3, step scale_step_2: error(z) form R, c=2, k=2, t=1`; `V3, radius bv_scale_radius_2: upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | largest error / bound | observed c | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.50238 | 0.994686 | 1.84948 | 1.06904 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.50414 | 0.995902 | 1.73906 | 1.08638 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 688 692 | 688 692 | 0 | 1.40625 | 0.759322 | - | 1.14516 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 1 343 408 | 1 343 408 | 0 | 1.8125 | 0.470588 | - | 1.55357 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 1 elements) | 12 364 | 12 364 | 0 | 1.8125 | 0.470588 | - | 1.55357 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 144, nonfinite 141, one 287, overflow 144, tail 141, threshold 428, underflow 143, whole 144, wide 144, zeroradius 143, zeros 141; `binary32`: cancel 144, nonfinite 141, one 287, overflow 144, tail 141, threshold 428, underflow 143, whole 144, wide 144, zeroradius 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 1.50238 (clang18/avx2, linux-x86-64):
  bv_scale_2 binary64 lanes:4 9 0x1.a1b4b08cd2d5cp+1010 0x1.613d22e423db1p+5 0x1.0fe23298eec69p+1014 -0x1.059c11ab9612fp+1015 0x1.4c8a61f00601dp+1016 0x1.3f0fc764e223ep+1015 0x1.4d7f43d75379cp+1014 ... (13 more) #threshold:539 -> 0x1.7727d5b945f2ap+1019 -0x1.68faae35adcfap+1020 0x1.cada3b58094e8p+1021 0x1.b840f4310e168p+1020 ... (16 more)
smallest radius slack, gaps (the worst entry), interpreter 1.40625 (fp:3:-4:1, every operand):
  bv_scale_2 fp:3:-4:1 seq 1 0x1.8p+1 -0x1.8p+0 -0x1.8p+2 -0x1p-4 #exhaustive:158877 -> 0x1p+3 0x1p+0 0x1.8p+2 1
largest error / bound, compiled 0.995902 (clang18-fixup-call/cxx, linux-x86-64):
  scale_step_2 binary32 0x1.001p-94 -0x1.fffffep-119 0x1.266042p-21 #bv_scale_2:tail:138:entry:707 -> 0x1.2672a6p-115 0x1.bbp-140
largest error / bound, interpreter 0.759322 (fp:3:-4:1, every operand):
  scale_step_2 fp:3:-4:1 -0x1.8p-1 -0x1p-4 -0x1.8p-2 #bv_scale_2:exhaustive:255971:entry:0 -> 0x1p-2 0x0p+0
smallest excess over the stated value, gaps, compiled 1.06904 (msvc/avx2, windows-x64):
  bv_scale_2 binary64 lanes:4 19 0x1.f9a3061dcf691p-750 0x1.336d56f60cc53p+44 -0x1.7a8ede77dc44ep-693 0x1.dd570bcf86162p-695 -0x1.434835b37fc5p-694 0x1.a50c7cc12687ap-694 0x1.eb3c14f2102d9p-696 ... (33 more) #one:322 -> -0x1.c69b04364d17bp-649 0x1.1e9da1aff64acp-650 -0x1.8439abf61934fp-650 0x1.f9a1cef3a05bcp-650 ... (36 more)
smallest excess over the stated value, gaps, interpreter 1.14516 (fp:3:-4:1, every operand):
  bv_scale_2 fp:3:-4:1 seq 1 0x1.8p-2 -0x1.8p+3 -0x1.8p-1 0x0p+0 #exhaustive:19105 -> 0x1p+3 0x1p+0 0x1.8p+2 1
```

### `bv_scale_radius_1`

Claims: `upper(rz) >= abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.05293 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.00121 |
| `fp:4:-8:4`, every operand (another exponent range) | 2 797 312 | 2 797 312 | 0 | 1.04590 |
| `fp:2:-5:3`, every operand (p = min_precision + 1, the quick tier's exponent range) | 15 600 | 15 600 | 0 | 1.17188 |
| `fp:1:-5:3`, every operand (p = min_precision, the quick tier's exponent range) | 1 900 | 1 900 | 0 | 1.32812 |
| `fp:4:-5:3`, every operand (quick tier + 1 bit) | 1 017 600 | 1 017 600 | 0 | 1.04590 |
| `fp:3:-5:3`, every operand (p = min_precision + 2, the quick tier's format) | 126 400 | 126 400 | 0 | 0.964844 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858; `binary32`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 1.00121 (clang18-fixup-call/cxx, linux-x86-64):
  bv_scale_radius_1 binary32 0x1.cadfeep-6 0x1.d7d29cp+41 -0x1.5a5fp-59 #atnormal:42773 -> 0x1.3f3f38p-17
smallest excess over the stated value, gaps, interpreter 0.964844 (fp:3:-5:3, every operand):
  bv_scale_radius_1 fp:3:-5:3 0x1p+1 0x1.8p-4 -0x1.8p+4 #exhaustive:63442 -> 0x1.8p+1
```

### `bv_scale_radius_2`

Claims: `upper(rz) >= abs(a)*rx+m*unit(mul_2_1)/(1-unit(mul_2_1))*(1+u)+tiny(mul_2_1)/(1-unit(mul_2_1))`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.06839 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 1.00858 |
| `fp:3:-5:3`, every operand (p = min_precision + 1, the quick tier's format) | 126 400 | 126 400 | 0 | 1.14516 |
| `fp:2:-5:3`, every operand (p = min_precision, the quick tier's exponent range) | 15 600 | 15 600 | 0 | 1.25 |
| `fp:4:-8:4`, every operand (another exponent range) | 2 797 312 | 2 797 312 | 0 | 1.19636 |
| `fp:4:-5:3`, every operand (quick tier + 1 bit) | 1 017 600 | 1 017 600 | 0 | 1.36688 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858; `binary32`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 1.00858 (clang18-fixup-call/cxx, linux-x86-64):
  bv_scale_radius_2 binary32 0x1.7c1f72p+53 0x1.00802p-104 -0x1.28p+123 #atnormal:2691 -> 0x1.28a008p+19
smallest excess over the stated value, gaps, interpreter 1.14516 (fp:3:-5:3, every operand):
  bv_scale_radius_2 fp:3:-5:3 0x1p+2 0x1.8p-4 -0x1.8p+4 #exhaustive:76082 -> 0x1.8p+1
```

### `bv_sub_1`

Claims: `encloses_entries(z, r) x-y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when |abs(x-y)+rx+ry| <= 2^(qmax+p-2)`; `V3, step sub_1_1: rounded(s) nearest`; `V3, step sub_1_1: error(s) form R, c=1/(1+u), k=1, t=0`; `V3, radius bv_add_radius_1: upper(rz) >= rx+ry+m*unit(add_1_1)/(1-unit(add_1_1))`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | cases by rounding | largest error / bound | observed c | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.52366 | exact 5 095 260; inexact 15 797 352; tie 26 076 | 0.999062 | 0.999062 | 1.19474 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.52344 | exact 5 644 278; inexact 14 566 416; tie 221 664 | 1 (the claim) | 0.9999999404 | 1.00467 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 26 115 244 | 26 115 244 | 0 | 1.5 | exact 7 439 445; inexact 2 617 472; tie 2 707 964 | 1 (the claim) | 0.8 | 1.5 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 2 375 522 | 2 375 522 | 0 | 1 | exact 651 659; inexact 705 816; tie 299 260 | 1 (the claim) | 0.888889 | 1 |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 1 elements) | 36 602 | 36 602 | 0 | 1.5 | exact 6 657; inexact 2 080; tie 2 380 | 1 (the claim) | 0.8 | 1.5 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 167, one 333, overflow 167, threshold 500, underflow 165, whole 168, wide 168, zeroradius 167, zeros 165; `binary32`: cancel 167, one 333, overflow 167, threshold 500, underflow 165, whole 168, wide 168, zeroradius 167, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 1.52344 (msvc/avx2, windows-x64):
  bv_sub_1 binary32 lanes:8 1 0x1.5879e8p+0 0x1.239186p+9 -0x1.d73032p+12 -0x1.d73034p+12 #cancel:52 -> 0x1.0000000000000p-11 0x1.243dc60000000p+9 1
smallest radius slack, gaps (the worst entry), interpreter 1 (fp:3:-4:1, every operand):
  bv_sub_1 fp:3:-4:1 seq 1 0x1p+3 0x1p+0 -0x1.4p+2 -0x1.cp+3 #exhaustive:19525 -> 0x1p+3 0x1.8p+3 1
largest error / bound, compiled 1 (msvc/avx2, windows-x64):
  sub_1_1 binary32 -0x1p+127 -0x1.fffffep+125 #bv_sub_1:overflow:125:entry:3 -> -0x1p+126
largest error / bound, interpreter 1 (fp:2:-2:1, every operand):
  sub_1_1 fp:2:-2:1 -0x1p+0 -0x1.8p+2 #bv_sub_1:exhaustive:171:entry:0 -> 0x1p+2
smallest excess over the stated value, gaps, compiled 1.00467 (clang-fixup-inline/cxx, macos-arm64):
  bv_sub_1 binary32 lanes:1 8 0x1.8fd9c8p+87 0x1.1fa6d4p+107 0x1.f0c8a8p+112 -0x1.754bcp+109 -0x1.566594p+112 0x1.656f58p+108 0x1.48e7d2p+109 0x1.b81d06p+110 0x1.e252fp+108 -0x1.5135bcp+112 ... (8 more) #threshold:163 -> -0x1.a477f4p+126 -0x1.0c5406p+124 -0x1.6713b6p+126 0x1.b08d8ap+125 -0x1.dd85cp+123 0x1.87b00ap+122 ... (4 more)
smallest excess over the stated value, gaps, interpreter 1 (fp:3:-4:1, every operand):
  bv_sub_1 fp:3:-4:1 seq 1 0x1p+2 0x1p-1 -0x1.4p+3 -0x1.cp+3 #exhaustive:13245 -> 0x1p+2 0x1.8p+2 1
```

### `bv_sub_2`

Claims: `encloses_entries(z, r) x-y over x=[x +- rx], y=[y +- ry], V1-V4, flag finite, finite when |abs(x-y)+rx+ry| <= 2^(qmax+p-2)`; `V3, step sub_2_2: normalized(z)`; `V3, step sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`; `V3, radius bv_add_radius_2: upper(rz) >= rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps (the worst entry) | largest error / bound | observed c | smallest excess over the stated value, gaps |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.50000 | 0.605982 | 1.42916 | 1.35448 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.44849 | 0.657483 | 1.97245 | 1.12583 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 140 304 866 | 140 304 866 | 0 | 1.25 | 0.273504 | - | 1.03448 |
| `fp:3:-2:-1`, every operand (the full tier's format, every array up to 1 elements) | 121 970 | 121 970 | 0 | 3.5 | 0 | - | 3.44181 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 155, one 308, overflow 155, tail 153, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153; `binary32`: cancel 155, one 308, overflow 155, tail 153, threshold 460, underflow 153, whole 155, wide 155, zeroradius 153, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps (the worst entry), compiled 1.44849 (clang18-fixup-call/cxx, linux-x86-64):
  bv_sub_2 binary32 lanes:1 93 0x1.6cbe28p+14 0x1.3811dap+28 0x1.b38ec6p+44 0x1.a28bc2p+41 0x1.5746eep+42 0x1.bbb4acp+40 0x1.54148p+44 0x1.6cdcc6p+41 -0x1.07f6a6p+41 0x1.ad04acp+44 -0x1.4dfa18p+42 ... (363 more) #one:195 -> -0x1.a8bfcep+44 -0x1.ac4e18p+48 -0x1.012e7p+48 0x1.00a24cp+46 0x1.ea04b2p+47 0x1.4e75p+46 ... (182 more)
smallest radius slack, gaps (the worst entry), interpreter 1.25 (fp:3:-4:1, every operand):
  bv_sub_2 fp:3:-4:1 seq 1 0x1.cp+2 0x1.cp-2 -0x1.cp+0 -0x1p-4 -0x1.4p+2 -0x1.8p-2 #exhaustive:41546375 -> 0x1.cp+1 0x0p+0 0x1.4p+3 1
largest error / bound, compiled 0.657483 (clang-fixup-inline/cxx, macos-arm64):
  sub_2_2 binary32 -0x1.fad266p+121 -0x1.fcb7e2p+96 -0x1.ee7e1ap+120 0x1.54235cp+93 #bv_sub_2:threshold:14:entry:219 -> -0x1.03935ap+121 -0x1.39e28cp+93
largest error / bound, interpreter 0.273504 (fp:3:-4:1, every operand):
  sub_2_2 fp:3:-4:1 -0x1.4p+1 -0x1.8p-3 -0x1p+3 0x1.cp-2 #bv_sub_2:exhaustive:29854945:entry:0 -> 0x1.4p+2 0x0p+0
smallest excess over the stated value, gaps, compiled 1.12583 (msvc/avx2, windows-x64):
  bv_sub_2 binary32 lanes:8 506 0x1.e92304p-33 0x1.d45986p-35 0x1.3dea76p-12 0x1.b60d6p-12 0x1.c6cc5ep-13 -0x1.6c652p-12 -0x1.94dc84p-10 -0x1.ce747p-9 0x1.24fd0ap-11 0x1.1d1c92p-10 -0x1.d7b47ap-10 ... (2015 more) #one:87 -> 0x1.3dea720000000p-12 0x1.b60d620000000p-12 0x1.c6cc620000000p-13 -0x1.6c65140000000p-12 ... (1010 more)
smallest excess over the stated value, gaps, interpreter 1.03448 (fp:3:-4:1, every operand):
  bv_sub_2 fp:3:-4:1 seq 1 0x1p+2 0x1p-1 -0x1.8p+3 0x1.cp-1 -0x1.cp+3 -0x1.cp-1 #exhaustive:96909 -> 0x1p+2 -0x1p-2 0x1.8p+2 1
```

### `conv_1`

Claims: `coefficients(z) of the fold dot_1, sequential`; `finite_or_nan(z) flag finite`; `coefficients(z), fold dot_1: fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1`.

| Run | Cases | Judged | Failed | largest error / bound, order sequential |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.999999 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 257 049 | 257 049 | 0 | 0.833333 |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 44 521 | 44 521 | 0 | 0.833333 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 849 | 1 849 | 0 | 0.9 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165; `binary32`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order sequential, compiled 1 - ε, ε < 10⁻⁹ (clang-fixup-inline/cxx, macos-arm64):
  conv_1 binary64 seq 1 877 -0x1p-833 -0x1.00010001p+154 0x1.00004p-618 0x1.000001p-1033 0x1p-24 0x1.0002p+219 -0x1.084p+35 -0x1.000001p+372 -0x1p+122 0x1p-633 0x1.0000000201p-663 ... (867 more) #pow2:35 -> 0x1.00010001p-679 -0x0p+0 -0x0p+0 -0x1p-857 -0x1.0002p-614 0x1.084p-798 0x1.000001p-461 0x1p-711 ... (870 more)
largest error / bound, order sequential, interpreter 0.9 (fp:3:-3:0, every operand):
  conv_1 fp:3:-3:0 seq 1 1 -0x1p-1 -0x1p-3 #exhaustive:733 -> 0x0p+0 1
```

### `conv_1_entry`

Claims: `coefficients(z) of the fold dot_1_entry, sequential`; `finite_or_nan(z) flag finite`; `coefficients(z), fold dot_1_entry: fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1`.

| Run | Cases | Judged | Failed | largest error / bound, order sequential |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 1.00000 |
| `binary32`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.9999999404 |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 44 521 | 44 521 | 0 | 0.833333 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 257 049 | 257 049 | 0 | 0.833333 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 849 | 1 849 | 0 | 0.9 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165; `binary32`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order sequential, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  conv_1_entry binary64 seq 1275 1 0x1.0000000002p-471 0x1.8p-460 0x1.00000001p-345 -0x1.00000001p-263 0x1.000000000008p+187 -0x1.0000000000008p-373 -0x1p-75 0x1.000000000208p-951 0x1.0041p-571 -0x1p+57 ... (1266 more) #pow2:959 -> -0x1.0000000002p-832 -0x1.8p-821 -0x1.00000001p-706 0x1.00000001p-624 -0x1.000000000008p-174 ... (1271 more)
largest error / bound, order sequential, interpreter 0.9 (fp:3:-3:0, every operand):
  conv_1_entry fp:3:-3:0 seq 1 1 -0x1p-1 -0x1p-3 #exhaustive:733 -> 0x0p+0 1
```

### `conv_2`

Claims: `coefficients(z) of the fold dot_2, sequential`; `finite_or_nan(z) flag finite`; `coefficients(z), fold dot_2: normalized(r)`; `coefficients(z), fold dot_2: fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`.

| Run | Cases | Judged | Failed | largest error / bound, order sequential |
|---|---|---|---|---|
| `binary64`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.999476 |
| `binary32`, 60 runners on 3 machines | 42 000 | 42 000 | 0 | 0.906448 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 990 025 | 990 025 | 0 | 0.764346 |
| `fp:4:-4:-1`, every operand (the full tier's format, every array up to 1 elements) | 63 001 | 63 001 | 0 | 0.561075 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153; `binary32`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order sequential, compiled 0.999476 (clang18-fixup-call/cxx, linux-x86-64):
  conv_2 binary64 seq 2 4 0x1.0000001779156p+111 0x0p+0 0x1.ffffffcebcea3p+57 -0x0p+0 0x1.0000000018a63p+111 0x0p+0 0x0p+0 0x0p+0 0x1.ffffffffd6156p+57 0x0p+0 -0x0p+0 -0x0p+0 #tight:229 -> 0x1.0000001791bbap+222 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x1.214b71350ep+159 0x0p+0 0x0p+0 0x0p+0 0x0p+0 1
largest error / bound, order sequential, interpreter 0.764346 (fp:4:-5:0, every operand):
  conv_2 fp:4:-5:0 seq 1 1 -0x1.4p-1 0x1p-5 -0x1.4p-1 0x1p-5 #exhaustive:475609 -> 0x1.4p-2 0x0p+0 1
```

### `conv_radius`

Claims: `upper(rz) >= m*((1+u)*ma*ry+(1+u)*mb*rx+rx*ry)+g*m*(1+u)^2*ma*mb+t`.

| Run | Cases | Judged | Failed | smallest excess over the stated value, gaps |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 |
| `fp:3:-5:5`, restricted: `ma.in=0x0p+0/0x1p-5/0x1p-2/0x1p-1/0x1p+0/0x1.8p+1/0x1.8p+2/0x1.cp+7`, `mb.in=0x0p+0/0x1p-5/0x1p-2/0x1p+0/0x1.8p+1/0x1.8p+2`, `rx.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0`, `ry.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0`, `m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1/0x1.4p+2`, `g.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0`, `t.in=0x0p+0/0x1p-5/0x1p-1/0x1p+1` (p = min_precision + 1, another exponent range) | 120 000 | 120 000 | 0 | 1 |
| `fp:3:-4:4`, restricted: `ma.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1/0x1.cp+6`, `mb.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1`, `rx.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0`, `ry.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0`, `m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1`, `g.in=0x0p+0/0x1p-3/0x1p-1/0x1p+0`, `t.in=0x0p+0/0x1p-4/0x1p+0` (p = min_precision + 1, the quick tier's format) | 23 040 | 23 040 | 0 | 1 |
| `fp:4:-4:4`, restricted: `ma.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1/0x1.cp+6`, `mb.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1`, `rx.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0`, `ry.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0`, `m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1`, `g.in=0x0p+0/0x1p-3/0x1p-1/0x1p+0`, `t.in=0x0p+0/0x1p-4/0x1p+0` (quick tier + 1 bit) | 23 040 | 23 040 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858; `binary32`: atnormal 35 715, extreme 17 855, huge 35 715, mixed 53 571, overflow 17 857, pow2 17 857, underflow 17 857, uniform 17 858, zero 17 857, zeros 17 858.

Where the extremes are attained (the line as the oracle reports it):

```
smallest excess over the stated value, gaps, compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  conv_radius binary64 0x1p-1022 -0x0p+0 0x0p+0 0x1.ffffffffffffep-1023 -0x0p+0 0x0p+0 0x1p-1074 #zero:94 -> 0x0.0000000000001p-1022
smallest excess over the stated value, gaps, interpreter 1 (fp:3:-5:5, restricted: ma.in=0x0p+0/0x1p-5/0x1p-2/0x1p-1/0x1p+0/0x1.8p+1/0x1.8p+2/0x1.cp+7, mb.in=0x0p+0/0x1p-5/0x1p-2/0x1p+0/0x1.8p+1/0x1.8p+2, rx.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0, ry.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0, m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1/0x1.4p+2, g.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0, t.in=0x0p+0/0x1p-5/0x1p-1/0x1p+1):
  conv_radius fp:3:-5:5 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x1p-5 #exhaustive:1 -> 0x1p-4
```

### `dot_1`

Claims: `fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.999756 | 0.998825 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.999401 | 0.999390 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 468 997 | 468 997 | 0 | 0.609756 | 0.833333 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 765 | 1 765 | 0 | - | 0.9 |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 77 029 | 77 029 | 0 | 0.609756 | 0.833333 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165; `binary32`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.999756 (msvc-fixup-call/cxx, windows-x64):
  dot_1 binary64 lanes:0 4096 0x1p+833 0x1.fffffffffffffp+779 0x1.fffffffffffffp+779 0x1.fffffffffffffp+779 0x1.fffffffffffffp+779 0x1.fffffffffffffp+779 0x1.fffffffffffffp+779 0x1.fffffffffffffp+779 ... (8184 more) #tight:422 -> 0x1.0000000000000p+833 1
largest error / bound, order lanes, interpreter 0.609756 (fp:2:-2:1, every operand):
  dot_1 fp:2:-2:1 lanes:2 2 -0x1p-1 -0x1p-1 -0x1p-2 -0x1p-2 #exhaustive:157626 -> 0x0p+0 1
largest error / bound, order sequential, compiled 0.999390 (msvc-fixup-call/cxx, windows-x64):
  dot_1 binary32 seq 4096 0x1p+110 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 0x1.fffffep+85 ... (8180 more) #tight:356 -> 0x1.0000000000000p+110 1
largest error / bound, order sequential, interpreter 0.9 (fp:3:-3:0, every operand):
  dot_1 fp:3:-3:0 seq 1 -0x1p-1 -0x1p-3 #exhaustive:649 -> 0x0p+0 1
```

### `dot_1_entry`

Claims: `fold_error(r) eps=u/(1+u), term=0, tau=eta/2; heights sequential rel n abs n-1, lanes rel n abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.999724 | 0.999756 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.999402 | 0.999390 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 468 997 | 468 997 | 0 | 0.609756 | 0.833333 |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 77 029 | 77 029 | 0 | 0.609756 | 0.833333 |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 765 | 1 765 | 0 | - | 0.9 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165; `binary32`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.999724 (msvc-fixup-call/cxx, windows-x64):
  dot_1_entry binary64 lanes:3629 3621 0x1p-28 0x1.fffffffffffffp-82 0x1.fffffffffffffp-82 0x1.fffffffffffffp-82 0x1.fffffffffffffp-82 0x1.fffffffffffffp-82 0x1.fffffffffffffp-82 0x1.fffffffffffffp-82 ... (7234 more) #tight:254 -> 0x1.0000000000000p-28 1
largest error / bound, order lanes, interpreter 0.609756 (fp:2:-2:1, every operand):
  dot_1_entry fp:2:-2:1 lanes:2 2 -0x1p-1 -0x1p-1 -0x1p-2 -0x1p-2 #exhaustive:157626 -> 0x0p+0 1
largest error / bound, order sequential, compiled 0.999756 (msvc-fixup-call/cxx, windows-x64):
  dot_1_entry binary64 seq 4096 -0x1p+614 -0x1.fffffffffffffp+560 -0x1.fffffffffffffp+560 -0x1.fffffffffffffp+560 -0x1.fffffffffffffp+560 -0x1.fffffffffffffp+560 -0x1.fffffffffffffp+560 ... (8185 more) #tight:2 -> -0x1.0000000000000p+614 1
largest error / bound, order sequential, interpreter 0.9 (fp:3:-3:0, every operand):
  dot_1_entry fp:3:-3:0 seq 1 -0x1p-1 -0x1p-3 #exhaustive:649 -> 0x0p+0 1
```

### `dot_2`

Claims: `normalized(r)`; `fold_error(r) eps=3*u^2/(1-4*u), term=4*u^2, tau=3/2*eta; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.999476 | 0.571129 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.701561 | 0.187007 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 988 037 | 988 037 | 0 | - | 0.764346 |
| `fp:4:-4:-1`, every operand (the full tier's format, every array up to 1 elements) | 62 501 | 62 501 | 0 | - | 0.561075 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153; `binary32`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.999476 (clang18-fixup-call/cxx, linux-x86-64):
  dot_2 binary64 lanes:8 1 0x1.0000001779156p+38 0x1.ffffffcebcea3p-16 0x1.0000000018a63p+38 0x1.ffffffffd6156p-16 #tight:749 -> 0x1.0000001791bbap+76 0x1.214b71350ep+13 1
largest error / bound, order sequential, compiled 0.571129 (clang18-fixup-call/cxx, linux-x86-64):
  dot_2 binary64 seq 2 -0x1.0000001779156p+49 0x0p+0 -0x1.ffffffcebcea3p-5 0x0p+0 0x1.0000000018a63p+49 0x0p+0 0x1.ffffffffd6156p-5 0x0p+0 #tight:938 -> -0x1.0000001791bbap+98 -0x1.214b71350ep+35 1
largest error / bound, order sequential, interpreter 0.764346 (fp:4:-5:0, every operand):
  dot_2 fp:4:-5:0 seq 1 -0x1.4p-1 0x1p-5 -0x1.4p-1 0x1p-5 #exhaustive:473621 -> 0x1.4p-2 0x0p+0 1
```

### `dot_entry_step_1`

Claims: `rounded(t) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 95 282 190 | 0 | exact 31 578 840; inexact 57 126 942; tie 6 576 408 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 95 448 006 | 0 | exact 32 437 656; inexact 56 331 234; tie 6 679 116 |
| `fp:2:-6:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 19 683 | 19 399 | 0 | exact 4 435; inexact 12 740; tie 2 224 |
| `fp:1:-6:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 197 | 2 193 | 0 | exact 605; inexact 1 316; tie 272 |
| `fp:4:-6:-1`, every operand (quick tier + 1 bit) | 1 367 631 | 1 216 947 | 0 | exact 175 511; inexact 924 980; tie 116 456 |
| `fp:3:-8:1`, every operand (p = min_precision + 2, another exponent range) | 658 503 | 612 243 | 0 | exact 85 955; inexact 477 116; tie 49 172 |
| `fp:3:-6:-1`, every operand (p = min_precision + 2, the quick tier's format) | 166 375 | 157 723 | 0 | exact 29 155; inexact 111 220; tie 17 348 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 664 287, exactprod 221 429, extreme 221 427, overflow 221 428, pow2 221 428, state 442 858, tie 221 429, underflow 221 429, uniform 221 429, zero 221 427, zerostate 221 429; `binary32`: cancel 664 287, exactprod 221 429, extreme 221 427, overflow 221 428, pow2 221 428, state 442 858, tie 221 429, underflow 221 429, uniform 221 429, zero 221 427, zerostate 221 429.

### `dot_step_1`

Claims: `rounded(t) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 95 261 706 | 0 | exact 31 579 218; inexact 57 102 246; tie 6 580 242 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 95 441 796 | 0 | exact 32 459 004; inexact 56 323 386; tie 6 659 406 |
| `fp:3:-8:1`, every operand (p = min_precision + 2, another exponent range) | 658 503 | 612 243 | 0 | exact 85 955; inexact 477 116; tie 49 172 |
| `fp:3:-6:-1`, every operand (p = min_precision + 2, the quick tier's format) | 166 375 | 157 723 | 0 | exact 29 155; inexact 111 220; tie 17 348 |
| `fp:2:-6:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 19 683 | 19 399 | 0 | exact 4 435; inexact 12 740; tie 2 224 |
| `fp:4:-6:-1`, every operand (quick tier + 1 bit) | 1 367 631 | 1 216 947 | 0 | exact 175 511; inexact 924 980; tie 116 456 |
| `fp:1:-6:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 197 | 2 193 | 0 | exact 605; inexact 1 316; tie 272 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 664 287, exactprod 221 429, extreme 221 427, overflow 221 428, pow2 221 428, state 442 858, tie 221 429, underflow 221 429, uniform 221 429, zero 221 427, zerostate 221 429; `binary32`: cancel 664 287, exactprod 221 429, extreme 221 427, overflow 221 428, pow2 221 428, state 442 858, tie 221 429, underflow 221 429, uniform 221 429, zero 221 427, zerostate 221 429.

### `dot_step_2`

Claims: `normalized(t)`; `error(t) form T, c=3*(1+4*u*u)/(1-4*u)+4, k=2, t=2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 590 862 | 0 | 0.690771 | 2.86631 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 598 080 | 0 | 0.672771 | 2.17447 |
| `fp:5:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 953 125 | 602 377 | 0 | 0.417584 | - |
| `fp:4:-4:-2`, every operand (p = min_precision, another exponent range) | 1 860 867 | 904 263 | 0 | 0.399878 | - |
| `fp:4:-3:-2`, every operand (p = min_precision, the quick tier's format) | 226 981 | 111 453 | 0 | 0.393365 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 53 573, exactprod 17 857, extreme 17 855, overflow 17 857, pow2 17 857, state 35 715, tie 17 858, underflow 17 857, uniform 17 858, zero 17 855, zerostate 17 858; `binary32`: cancel 53 573, exactprod 17 857, extreme 17 855, overflow 17 857, pow2 17 857, state 35 715, tie 17 858, underflow 17 857, uniform 17 858, zero 17 855, zerostate 17 858.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.690771 (clang18-fixup-call/cxx, linux-x86-64):
  dot_step_2 binary64 0x1.0db0c9f46d0eap-994 0x1p-1047 0x1.f8136961741fdp-332 0x1p-386 0x1.21d2264b91c33p-659 0x1.e6ba88438ea33p-718 #underflow:9807 -> 0x1.2e30e744d9016p-990 -0x0.000007a8b8766p-1022
largest error / bound, interpreter 0.417584 (fp:5:-3:-2, every operand):
  dot_step_2 fp:5:-3:-2 0x0p+0 0x0p+0 -0x1.2p+2 0x1p-3 -0x1.8p-2 0x0p+0 #exhaustive:972184 -> 0x1.cp+0 0x0p+0
```

### `eq_2_1`

Claims: `predicate(m) eq(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 1 035 576; false 6 164 424; a non-finite operand, false 850 446; a non-finite operand, true 49 554 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 1 126 170; false 6 073 830; a non-finite operand, false 848 916; a non-finite operand, true 51 084 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 241; false 3 430 835; a non-finite operand, false 43 249; a non-finite operand, true 2 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 57; false 24 651; a non-finite operand, false 1 441; a non-finite operand, true 2 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 896 | 896 | 0 | true 15; false 881; a non-finite operand, false 205; a non-finite operand, true 2 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 353; false 5 743 651; a non-finite operand, false 49 729; a non-finite operand, true 2 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 449; false 1 829 251; a non-finite operand, false 13 537; a non-finite operand, true 2 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 225; false 455 843; a non-finite operand, false 6 721; a non-finite operand, true 2 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 29; false 4 831; a non-finite operand, false 565; a non-finite operand, true 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `eq_2_2`

Claims: `predicate(m) eq(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 1 858 212; false 5 341 788; a non-finite operand, false 851 454; a non-finite operand, true 48 546 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 1 918 134; false 5 281 866; a non-finite operand, false 849 870; a non-finite operand, true 50 130 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | true 2 017; false 4 070 307; a non-finite operand, false 12 097; a non-finite operand, true 2 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 3 136 | 3 136 | 0 | true 55; false 3 081; a non-finite operand, false 325; a non-finite operand, true 2 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | true 2 753; false 7 581 763; a non-finite operand, false 16 513; a non-finite operand, true 2 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 3 247 204 | 3 247 204 | 0 | true 1 801; false 3 245 403; a non-finite operand, false 10 801; a non-finite operand, true 2 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | true 993; false 987 043; a non-finite operand, false 5 953; a non-finite operand, true 2 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 181 476 | 181 476 | 0 | true 425; false 181 051; a non-finite operand, false 2 545; a non-finite operand, true 2 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | true 161; false 26 083; a non-finite operand, false 961; a non-finite operand, true 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `fast_two_sum`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`; `normalized(r)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 017 354 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 016 400 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 2 654 207 | 2 637 823 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 1 384 447 | 1 368 063 | 0 | 0 (exact) | - |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 346 111 | 342 015 | 0 | 0 (exact) | - |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 1 351 | 1 335 | 0 | 0 (exact) | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 5 407 | 5 343 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

### `fast_two_sum_entry`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`; `normalized(r)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 100 850 724 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 100 860 012 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 1 384 447 | 1 368 063 | 0 | 0 (exact) | - |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 346 111 | 342 015 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 5 407 | 5 343 | 0 | 0 (exact) | 0 |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 1 351 | 1 335 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 2 654 207 | 2 637 823 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332; `binary32`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332.

### `fold_finish_1`

Claims: `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 827 394 | 827 394 | 0 |
| `fp:13:-31:8`, every operand (quick tier + 2 bits) | 335 874 | 335 874 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 166 | 166 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 84 | 84 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 167 938 | 167 938 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 330 | 330 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 281 817, nonfinite 845 455, overflow 281 818, pow2 281 818, tails 563 636, underflow 281 818, uniform 281 820, zero 281 818; `binary32`: extreme 281 817, nonfinite 845 455, overflow 281 818, pow2 281 818, tails 563 636, underflow 281 818, uniform 281 820, zero 281 818.

### `fold_finish_2`

Claims: `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 476 | 5 476 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 444 | 1 444 | 0 |
| `fp:6:-12:3`, every operand (another number of exponents) | 1 188 100 | 1 188 100 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 |
| `fp:1:-3:4`, every operand (p = min_precision, the quick tier's number of exponents) | 400 | 400 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 277 271, nonfinite 831 819, overflow 277 273, pow2 277 272, tails 554 546, underflow 277 273, uniform 277 274, zero 277 272; `binary32`: extreme 277 271, nonfinite 831 819, overflow 277 273, pow2 277 272, tails 554 546, underflow 277 273, uniform 277 274, zero 277 272.

### `interval_add_1`

Claims: `encloses_interval(zl, zu) x+y over x=[xl, xu], y=[yl, yu], I1-I5, tight rounded, bounded exactly when |x+y| <= Omega`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 1, another number of exponents) | 739 600 | 739 600 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

### `interval_add_2`

Claims: `encloses_interval(zl, zu) x+y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, exact when lower: xl+yl = 0; upper: xu+yu = 0, bounded when |x+y| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | largest lower-bound distance / allowance | largest upper-bound distance / allowance |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.687500 | 0.683589 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.660835 | 0.684558 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 | 0.406475 | 0.406475 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision, another number of exponents) | 2 206 620 | 2 206 620 | 0 | 0.384391 | 0.384391 |
| `fp:3:-2:-1`, every operand (p = min_precision, the quick tier's format) | 245 025 | 245 025 | 0 | 0.360236 | 0.360236 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest lower-bound distance / allowance, compiled 0.687500 (clang-fixup-inline/cxx, macos-arm64):
  interval_add_2 binary64 -0x1p+1023 -0x1.fffffffffffffp+969 -0x1.fffffffffffffp+1022 -0x1.fffffffffffffp+968 0x1.fffffffffffffp+1021 0x1.fffffffffffffp+967 0x1.ffffffffffffep+1022 -0x1.000022p+966 #overflow:36748 -> -0x1.0000000000001p+1022 -0x1.0000000000004p+968 -0x1.9000022p+970 0x1.0000000000005p+916
largest lower-bound distance / allowance, interpreter 0.406475 (fp:4:-3:-2, every operand):
  interval_add_2 fp:4:-3:-2 -0x1.ep+1 0x0p+0 -0x1.ep+1 0x0p+0 0x1.8p+1 0x1p-3 0x1.8p+1 0x1p-3 #exhaustive:128933 -> -0x1p+1 0x0p+0 0x1.8p-1 0x0p+0
largest upper-bound distance / allowance, compiled 0.684558 (msvc-fixup-call/cxx, windows-x64):
  interval_add_2 binary32 0x1p-126 -0x0p+0 0x1.00002p-22 0x1.fffffep-47 -0x1.00002p-22 -0x1.fffffep-47 -0x1.e7ea4cp-72 0x1.86b51cp-103 #zerosum:96522 -> -0x1.0000220000000p-22 0x1.fffff80000000p-47 0x1.0000220000000p-22 -0x1.fffff80000000p-47
largest upper-bound distance / allowance, interpreter 0.406475 (fp:4:-3:-2, every operand):
  interval_add_2 fp:4:-3:-2 -0x1.ep+1 0x0p+0 -0x1.ep+1 0x0p+0 0x1.8p+0 0x0p+0 0x1.8p+1 0x1p-3 #exhaustive:128764 -> -0x1.ep+1 0x0p+0 0x1.8p-1 0x0p+0
```

### `interval_contains_1`

Claims: `certain(m) member(t, x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 95 816 | 95 816 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 904 | 1 904 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 734 160 | 734 160 | 0 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 360 360 | 360 360 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 13 020 | 13 020 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, member 516 668, nearzero 516 668, overflow 258 332, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, member 516 668, nearzero 516 668, overflow 258 332, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `interval_contains_2`

Claims: `certain(m) member(t, x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, the quick tier's format) | 95 816 | 95 816 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, another number of exponents) | 17 913 720 | 17 913 720 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, quick tier + 1 bit) | 900 360 | 900 360 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, the quick tier's number of exponents) | 6 600 | 6 600 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 17 855, member 35 715, nearzero 35 716, overflow 17 857, pow2 17 855, special 35 716, tails 35 714, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: extreme 17 855, member 35 715, nearzero 35 716, overflow 17 857, pow2 17 855, special 35 716, tails 35 714, underflow 17 857, uniform 17 858, zero 17 857.

### `interval_empty_1`

Claims: `certain(m) empty(x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 377 | 377 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 564 | 5 564 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 430 | 1 430 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `interval_empty_2`

Claims: `certain(m) empty(x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 493 520 | 493 520 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, another number of exponents) | 485 604 | 485 604 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 90 524 | 90 524 | 0 |
| `fp:4:-4:-1`, every operand (another number of exponents) | 31 124 | 31 124 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 13 040 | 13 040 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 539 | 1 539 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856.

### `interval_entire_1`

Claims: `certain(m) entire(x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 564 | 5 564 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 377 | 377 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 430 | 1 430 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `interval_entire_2`

Claims: `certain(m) entire(x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 493 520 | 493 520 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, another number of exponents) | 485 604 | 485 604 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 90 524 | 90 524 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 13 040 | 13 040 | 0 |
| `fp:4:-4:-1`, every operand (another number of exponents) | 31 124 | 31 124 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 539 | 1 539 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856.

### `interval_equal_1`

Claims: `trit(yes yes, no no) eq(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221.

### `interval_equal_2`

Claims: `trit(yes yes, no no) eq(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_hull_1`

Claims: `interval_set(zl, zu) union of x=[xl, xu], y=[yl, yu]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 31 250, extreme 15 625, nested 31 250, overflow 15 625, point 31 250, pow2 15 625, special 31 250, touch 31 250, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: disjoint 31 250, extreme 15 625, nested 31 250, overflow 15 625, point 31 250, pow2 15 625, special 31 250, touch 31 250, underflow 15 625, uniform 15 625, zero 15 625.

### `interval_hull_2`

Claims: `interval_set(zl, zu) union of x=[xl, xu], y=[yl, yu]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 31 250, extreme 15 625, nested 31 250, overflow 15 625, point 31 250, pow2 15 625, special 31 250, touch 31 250, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: disjoint 31 250, extreme 15 625, nested 31 250, overflow 15 625, point 31 250, pow2 15 625, special 31 250, touch 31 250, underflow 15 625, uniform 15 625, zero 15 625.

### `interval_intersection_1`

Claims: `interval_set(zl, zu) intersection of x=[xl, xu], y=[yl, yu]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 387 500, extreme 193 750, nested 387 500, overflow 193 750, point 387 500, pow2 193 750, special 387 500, touch 387 500, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: disjoint 387 500, extreme 193 750, nested 387 500, overflow 193 750, point 387 500, pow2 193 750, special 387 500, touch 387 500, underflow 193 750, uniform 193 750, zero 193 750.

### `interval_intersection_2`

Claims: `interval_set(zl, zu) intersection of x=[xl, xu], y=[yl, yu]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 31 250, extreme 15 625, nested 31 250, overflow 15 625, point 31 250, pow2 15 625, special 31 250, touch 31 250, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: disjoint 31 250, extreme 15 625, nested 31 250, overflow 15 625, point 31 250, pow2 15 625, special 31 250, touch 31 250, underflow 15 625, uniform 15 625, zero 15 625.

### `interval_less_1`

Claims: `trit(yes yes, no no) lt(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221.

### `interval_less_2`

Claims: `trit(yes yes, no no) lt(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_less_equal_1`

Claims: `trit(yes yes, no no) le(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221.

### `interval_less_equal_2`

Claims: `trit(yes yes, no no) le(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_make_1`

Claims: `makes_interval(zl, zu) from lower lo, upper hi`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 476 | 5 476 | 0 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 444 | 1 444 | 0 |
| `fp:1:-3:4`, every operand (p = min_precision, the quick tier's number of exponents) | 400 | 400 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 221 427, infinities 442 858, nanbound 442 858, overflow 221 428, point 442 858, pow2 221 427, reversed 442 858, underflow 221 429, uniform 221 429, zero 221 428; `binary32`: extreme 221 427, infinities 442 858, nanbound 442 858, overflow 221 428, point 442 858, pow2 221 427, reversed 442 858, underflow 221 429, uniform 221 429, zero 221 428.

### `interval_make_2`

Claims: `makes_interval(zl, zu) from lower lo, upper hi`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 3 247 204 | 3 247 204 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 181 476 | 181 476 | 0 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 26 244 | 26 244 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 3 136 | 3 136 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 17 855, infinities 35 715, nanbound 35 716, overflow 17 857, point 35 714, pow2 17 855, reversed 35 716, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: extreme 17 855, infinities 35 715, nanbound 35 716, overflow 17 857, point 35 714, pow2 17 855, reversed 35 716, underflow 17 857, uniform 17 858, zero 17 857.

### `interval_mid_rad_1`

Claims: `ball_of_interval(m, r) of [xl, xu], special ieee1788, rel u, abs eta, the smallest radius`.

| Run | Cases | Judged | Failed | largest |center - midpoint| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 100 800 000 | 0 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 100 800 000 | 0 | 0.9999999404 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 564 | 5 564 | 0 | 0.888889 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 | 0.984615 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 | 0.969697 |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 1 430 | 1 430 | 0 | 0.8 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 178 125, oddeta 356 250, overflow 178 125, point 356 250, pow2 178 125, special 356 250, step 356 250, top 356 250, underflow 178 125, uniform 178 125, zero 178 125; `binary32`: extreme 178 125, oddeta 356 250, overflow 178 125, point 356 250, pow2 178 125, special 356 250, step 356 250, top 356 250, underflow 178 125, uniform 178 125, zero 178 125.

Where the extremes are attained (the line as the oracle reports it):

```
largest |center - midpoint| / allowance, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64):
  interval_mid_rad_1 binary64 -0x1.ffffffffffffep-1023 0x1.0000000000001p-1022 #extreme:511 -> 0x0p+0 0x1.0000000000001p-1022
largest |center - midpoint| / allowance, interpreter 0.984615 (fp:6:-10:1, every operand):
  interval_mid_rad_1 fp:6:-10:1 -0x1.f8p-5 0x1.e8p-5 #exhaustive:232045 -> -0x1p-9 0x1.f8p-5
```

### `interval_mid_rad_2`

Claims: `ball_of_interval(m, r) of [xl, xu], special ieee1788, rel 3*u^2/(1-4*u), abs 2*eta, finite when |xl| <= 2^(qmax+p-2) and |xu| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | largest |center - midpoint| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.666667 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.513361 |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's format) | 90 524 | 90 524 | 0 | 0.477612 |
| `fp:4:-5:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 493 520 | 493 520 | 0 | 0.496124 |
| `fp:3:-5:2`, every operand (p = min_precision, another number of exponents) | 485 604 | 485 604 | 0 | 0.477612 |
| `fp:4:-4:-1`, every operand (p = min_precision + 1, another number of exponents) | 31 124 | 31 124 | 0 | 0.496124 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: beyond 25 000, extreme 12 500, oddeta 25 000, overflow 12 500, point 25 000, pow2 12 500, special 25 000, step 25 000, threshold 25 000, top 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: beyond 25 000, extreme 12 500, oddeta 25 000, overflow 12 500, point 25 000, pow2 12 500, special 25 000, step 25 000, threshold 25 000, top 25 000, underflow 12 500, uniform 12 500, zero 12 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest |center - midpoint| / allowance, compiled 0.666667 (clang18-fixup-call/cxx, linux-x86-64):
  interval_mid_rad_2 binary64 -0x1.ffffffffffffdp+1021 -0x1.0dde933ebbe94p+937 0x1p+1023 -0x1p+969 #overflow:46596 -> 0x1.0000000000001p+1021 -0x1.0dde833ebbe94p+936 0x1.8000000000001p+1022
largest |center - midpoint| / allowance, interpreter 0.496124 (fp:4:-5:0, every operand):
  interval_mid_rad_2 fp:4:-5:0 -0x1.ep+3 -0x1.ep-2 0x1.ep+3 0x1.ap-2 #exhaustive:1981 -> -0x1p-4 0x0p+0 inf
```

### `interval_mul_1`

Claims: `encloses_interval(zl, zu) x*y over x=[xl, xu], y=[yl, yu], I1-I5, tight rounded, steps 1, when product_large, bounded exactly when |x*y| <= Omega`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zeroinf 31 250; `binary32`: aroundp 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zeroinf 31 250.

### `interval_mul_2`

Claims: `encloses_interval(zl, zu) x*y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, bounded when |x*y| <= 2^(qmax+p-2), I6: [0, 0] times anything is [0, 0]`.

| Run | Cases | Judged | Failed | largest lower-bound distance / allowance | largest upper-bound distance / allowance |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.700000 | 0.700000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.670666 | 0.699999 |
| `fp:4:-3:-2`, every operand (p = min_precision, the quick tier's format) | 4 060 225 | 4 060 225 | 0 | 0.437549 | 0.437549 |
| `fp:4:-4:-1`, restricted: `xl.lead=-1:-1`, `xu.lead=-1:-1` (p = min_precision, another number of exponents) | 5 291 080 | 5 291 080 | 0 | 0.456010 | 0.456010 |
| `fp:5:-4:-3`, restricted: `xl.lead=-2:-2`, `xu.lead=-2:-2` (p = min_precision + 1, quick tier + 1 bit) | 438 858 | 438 858 | 0 | 0.481953 | 0.481953 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zeroinf 31 250; `binary32`: aroundp 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zeroinf 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest lower-bound distance / allowance, compiled 0.700000 (msvc-fixup-call/cxx, windows-x64):
  interval_mul_2 binary64 0x1p+221 0x1.fffffffffffffp+167 0x1.b31d01fd3857dp+852 -0x1.1510a0dfdd5e4p-1004 0x1.0000000000001p-1022 0x0p+0 0x1.1a0fe4dc94c48p-686 0x1p-1074 #extreme:639 -> 0x1.0000000000001p-801 0x1.ffffffffffffap-855 0x1.df68f7e0cd750p+166 0x1.3e8f09d0e9ca8p+112
largest lower-bound distance / allowance, interpreter 0.481953 (fp:5:-4:-3, restricted: xl.lead=-2:-2, xu.lead=-2:-2):
  interval_mul_2 fp:5:-4:-3 -0x1.cp-2 0x0p+0 -0x1.cp-2 0x0p+0 -0x1.fp+1 0x0p+0 -0x1.cp+1 -0x1p-4 #exhaustive:81402 -> 0x0p+0 0x0p+0 0x1.ap+1 -0x1p-4
largest upper-bound distance / allowance, compiled 0.700000 (clang18-fixup-call/cxx, linux-x86-64):
  interval_mul_2 binary64 -0x1p+494 -0x1p+441 -0x1p+494 -0x1.ffffffffffffep+440 0x1.000000008p+0 0x1p-53 0x1.000000008p+0 0x1p-53 #point:95812 -> -0x1.0000000080001p+494 -0x1.0000400000003p+408 -0x1.0000000080001p+494 -0x1.fffeffffffffbp+407
largest upper-bound distance / allowance, interpreter 0.481953 (fp:5:-4:-3, restricted: xl.lead=-2:-2, xu.lead=-2:-2):
  interval_mul_2 fp:5:-4:-3 -0x1.cp-2 0x0p+0 -0x1.cp-2 0x0p+0 0x1.cp+1 0x1p-4 0x1.cp+1 0x1p-4 #exhaustive:89370 -> -0x1.8p+1 0x0p+0 0x0p+0 0x0p+0
```

### `interval_neg_1`

Claims: `encloses_interval(zl, zu) -x over x=[xl, xu], I1-I5, tight exact, bounded exactly when |-x| <= Omega`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 564 | 5 564 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 430 | 1 430 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 377 | 377 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 310 000, overflow 310 000, point 620 000, pow2 310 000, special 620 000, underflow 310 000, uniform 310 000, zero 310 000; `binary32`: extreme 310 000, overflow 310 000, point 620 000, pow2 310 000, special 620 000, underflow 310 000, uniform 310 000, zero 310 000.

### `interval_neg_2`

Claims: `encloses_interval(zl, zu) -x over x=[xl, xu], I1-I5, tight exact, bounded exactly when |-x| <= 2^(qmax+p)`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 493 520 | 493 520 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, another number of exponents) | 485 604 | 485 604 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 90 524 | 90 524 | 0 |
| `fp:4:-4:-1`, every operand (another number of exponents) | 31 124 | 31 124 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 13 040 | 13 040 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 539 | 1 539 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 25 000, overflow 25 000, point 50 000, pow2 25 000, special 50 000, underflow 25 000, uniform 25 000, zero 25 000; `binary32`: extreme 25 000, overflow 25 000, point 50 000, pow2 25 000, special 50 000, underflow 25 000, uniform 25 000, zero 25 000.

### `interval_negative_1`

Claims: `certain(m) lt(x, 0) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 564 | 5 564 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 430 | 1 430 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 377 | 377 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `interval_negative_2`

Claims: `certain(m) lt(x, 0) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 13 040 | 13 040 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 539 | 1 539 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 493 520 | 493 520 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, another number of exponents) | 485 604 | 485 604 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 90 524 | 90 524 | 0 |
| `fp:4:-4:-1`, every operand (another number of exponents) | 31 124 | 31 124 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856.

### `interval_positive_1`

Claims: `certain(m) lt(0, x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 564 | 5 564 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 430 | 1 430 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 377 | 377 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `interval_positive_2`

Claims: `certain(m) lt(0, x) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, another number of exponents) | 485 604 | 485 604 | 0 |
| `fp:4:-4:-1`, every operand (another number of exponents) | 31 124 | 31 124 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 493 520 | 493 520 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 90 524 | 90 524 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 13 040 | 13 040 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 539 | 1 539 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856.

### `interval_rel_disjoint_1`

Claims: `certain(m) disjoint(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221.

### `interval_rel_disjoint_2`

Claims: `certain(m) disjoint(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_rel_equal_1`

Claims: `certain(m) equal(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221.

### `interval_rel_equal_2`

Claims: `certain(m) equal(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_rel_interior_1`

Claims: `certain(m) interior(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221.

### `interval_rel_interior_2`

Claims: `certain(m) interior(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_split_1`

Claims: `splits [al, au], [bl, bu] of [xl, xu]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 564 | 5 564 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 1 430 | 1 430 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 193 750, oddeta 387 500, overflow 193 750, point 387 500, pow2 193 750, special 387 500, step 387 500, top 387 500, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: extreme 193 750, oddeta 387 500, overflow 193 750, point 387 500, pow2 193 750, special 387 500, step 387 500, top 387 500, underflow 193 750, uniform 193 750, zero 193 750.

### `interval_split_2`

Claims: `splits [al, au], [bl, bu] of [xl, xu]`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision, another number of exponents) | 485 604 | 485 604 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's format) | 90 524 | 90 524 | 0 |
| `fp:4:-5:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 493 520 | 493 520 | 0 |
| `fp:4:-4:-1`, every operand (p = min_precision + 1, another number of exponents) | 31 124 | 31 124 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: beyond 25 000, extreme 12 500, oddeta 25 000, overflow 12 500, point 25 000, pow2 12 500, special 25 000, step 25 000, threshold 25 000, top 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: beyond 25 000, extreme 12 500, oddeta 25 000, overflow 12 500, point 25 000, pow2 12 500, special 25 000, step 25 000, threshold 25 000, top 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_sub_1`

Claims: `encloses_interval(zl, zu) x-y over x=[xl, xu], y=[yl, yu], I1-I5, tight rounded, bounded exactly when |x-y| <= Omega`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 1, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's format) | 188 356 | 188 356 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

### `interval_sub_2`

Claims: `encloses_interval(zl, zu) x-y over x=[xl, xu], y=[yl, yu], I1-I5, tight outward, exact when lower: xl-yu = 0; upper: xu-yl = 0, bounded when |x-y| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | largest lower-bound distance / allowance | largest upper-bound distance / allowance |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.653874 | 0.750000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.677484 | 0.749999 |
| `fp:4:-3:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 | 0.406475 | 0.406475 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision, another number of exponents) | 2 206 620 | 2 206 620 | 0 | 0.384391 | 0.384391 |
| `fp:3:-2:-1`, every operand (p = min_precision, the quick tier's format) | 245 025 | 245 025 | 0 | 0.360236 | 0.360236 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: cancel 31 250, extreme 15 625, overflow 15 625, point 31 250, pow2 15 625, special 31 250, threshold 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest lower-bound distance / allowance, compiled 0.677484 (clang18-fixup-call/cxx, linux-x86-64):
  interval_sub_2 binary32 0x1.b6153p-51 -0x1p-75 0x1.002p-4 0x1p-28 0x1.b6153p-51 -0x1p-75 0x1.002p-4 0x1p-28 #zerosum:75913 -> -0x1.002002p-4 0x1.fffffcp-29 0x1.002002p-4 -0x1.fffffcp-29
largest lower-bound distance / allowance, interpreter 0.406475 (fp:4:-3:-2, every operand):
  interval_sub_2 fp:4:-3:-2 -0x1.ep+1 0x0p+0 -0x1.ep+1 0x0p+0 -0x1.ep+1 0x0p+0 -0x1.8p+1 -0x1p-3 #exhaustive:127013 -> -0x1p+1 0x0p+0 0x0p+0 0x0p+0
largest upper-bound distance / allowance, compiled 0.750000 (clang-fixup-inline/cxx, macos-arm64):
  interval_sub_2 binary64 -0x1.ffffffffffffcp+1022 0x1p+969 -0x1.fffffffffffffp+1021 0x0p+0 -0x1p+1023 -0x1.fffffffffffffp+969 -0x1p+1023 -0x0p+0 #overflow:25788 -> 0x1.2p+972 -0x1.b000000000007p+867 0x1.0000000000002p+1022 -0x1.ffffffffffffcp+968
largest upper-bound distance / allowance, interpreter 0.406475 (fp:4:-3:-2, every operand):
  interval_sub_2 fp:4:-3:-2 -0x1.ep+1 0x0p+0 -0x1.ep+1 0x0p+0 -0x1.8p+1 -0x1p-3 -0x1.8p+1 -0x1p-3 #exhaustive:127308 -> -0x1p+1 0x0p+0 0x1.8p-1 0x0p+0
```

### `interval_subset_1`

Claims: `certain(m) subset(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, quick tier + 1 bit) | 2 729 104 | 2 729 104 | 0 |
| `fp:2:-5:4`, every operand (p = min_precision + 1, another number of exponents) | 1 069 156 | 1 069 156 | 0 |
| `fp:3:-3:0`, every operand (p = min_precision + 2, another number of exponents) | 739 600 | 739 600 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 188 356 | 188 356 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 14 161 | 14 161 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: disjoint 344 444, equal 344 445, extreme 172 221, nearzero 344 446, nested 344 444, overflow 172 221, pow2 172 221, special 344 446, touch 344 446, underflow 172 222, uniform 172 223, zero 172 221.

### `interval_subset_2`

Claims: `certain(m) subset(x, y) over x=[xl, xu], y=[yl, yu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:3:-3:0`, restricted: `xl.lead=-1:0`, `xu.lead=-1:0` (p = min_precision + 2, another number of exponents) | 2 206 620 | 2 206 620 | 0 |
| `fp:3:-2:-1`, every operand (p = min_precision + 2, the quick tier's format) | 245 025 | 245 025 | 0 |
| `fp:4:-3:-2`, every operand (quick tier + 1 bit) | 4 060 225 | 4 060 225 | 0 |
| `fp:2:-2:1`, every operand (p = min_precision + 1, another number of exponents) | 2 729 104 | 2 729 104 | 0 |
| `fp:1:-1:2`, every operand (p = min_precision, another number of exponents) | 75 625 | 75 625 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: disjoint 25 000, equal 25 000, extreme 12 500, nearzero 25 000, nested 25 000, overflow 12 500, pow2 12 500, special 25 000, tails 25 000, touch 25 000, underflow 12 500, uniform 12 500, zero 12 500.

### `interval_to_ball_1`

Claims: `ball_of_interval(c, r) of [xl, xu], special ball, rel u, abs eta, the smallest radius`.

| Run | Cases | Judged | Failed | largest |center - midpoint| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 0.9999999404 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 | 0.984615 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 | 0.969697 |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 564 | 5 564 | 0 | 0.888889 |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 1 430 | 1 430 | 0 | 0.8 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 193 750, oddeta 387 500, overflow 193 750, point 387 500, pow2 193 750, special 387 500, step 387 500, top 387 500, underflow 193 750, uniform 193 750, zero 193 750; `binary32`: extreme 193 750, oddeta 387 500, overflow 193 750, point 387 500, pow2 193 750, special 387 500, step 387 500, top 387 500, underflow 193 750, uniform 193 750, zero 193 750.

Where the extremes are attained (the line as the oracle reports it):

```
largest |center - midpoint| / allowance, compiled 1.00000 (clang18-fixup-call/cxx, linux-x86-64):
  interval_to_ball_1 binary64 -0x1.ffffffffffffep-1023 0x1.0000000000001p-1022 #extreme:655 -> 0x0p+0 0x1.0000000000001p-1022
largest |center - midpoint| / allowance, interpreter 0.984615 (fp:6:-10:1, every operand):
  interval_to_ball_1 fp:6:-10:1 -0x1.f8p-5 0x1.e8p-5 #exhaustive:232045 -> -0x1p-9 0x1.f8p-5
```

### `interval_to_ball_2`

Claims: `ball_of_interval(c, r) of [xl, xu], special ball, rel 3*u^2/(1-4*u), abs 2*eta, finite when |xl| <= 2^(qmax+p-2) and |xu| <= 2^(qmax+p-2)`.

| Run | Cases | Judged | Failed | largest |center - midpoint| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.500000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.500000 |
| `fp:4:-5:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 493 520 | 493 520 | 0 | - |
| `fp:3:-5:2`, every operand (p = min_precision, another number of exponents) | 485 604 | 485 604 | 0 | 0.477612 |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's format) | 90 524 | 90 524 | 0 | 0.477612 |
| `fp:4:-4:-1`, every operand (p = min_precision + 1, another number of exponents) | 31 124 | 31 124 | 0 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: beyond 25 000, extreme 12 500, oddeta 25 000, overflow 12 500, point 25 000, pow2 12 500, special 25 000, step 25 000, threshold 25 000, top 25 000, underflow 12 500, uniform 12 500, zero 12 500; `binary32`: beyond 25 000, extreme 12 500, oddeta 25 000, overflow 12 500, point 25 000, pow2 12 500, special 25 000, step 25 000, threshold 25 000, top 25 000, underflow 12 500, uniform 12 500, zero 12 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest |center - midpoint| / allowance, compiled 0.500000 (clang18-fixup-call/cxx, linux-x86-64):
  interval_to_ball_2 binary64 -0x1.0000000000001p-1022 0x0p+0 0x1.ffffffffffffep-1023 -0x0p+0 #extreme:1319 -> 0x0p+0 0x0p+0 0x1.0000000000003p-1021
largest |center - midpoint| / allowance, interpreter 0.477612 (fp:3:-5:2, every operand):
  interval_to_ball_2 fp:3:-5:2 -0x1p+3 0x1p-5 0x1p+3 -0x1.8p-4 #exhaustive:229363 -> -0x1p-4 0x0p+0 0x1.8p+3
```

### `interval_zero_1`

Claims: `certain(m) eq(x, 0) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 5 564 | 5 564 | 0 |
| `fp:6:-10:1`, every operand (quick tier + 1 bit) | 347 360 | 347 360 | 0 |
| `fp:5:-13:6`, every operand (another number of exponents) | 226 800 | 226 800 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 1 430 | 1 430 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 377 | 377 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, nearzero 516 668, overflow 258 332, point 516 668, pow2 258 332, special 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `interval_zero_2`

Claims: `certain(m) eq(x, 0) over x=[xl, xu], exact`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:3:-5:2`, every operand (p = min_precision + 2, another number of exponents) | 485 604 | 485 604 | 0 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 90 524 | 90 524 | 0 |
| `fp:4:-4:-1`, every operand (another number of exponents) | 31 124 | 31 124 | 0 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 13 040 | 13 040 | 0 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 493 520 | 493 520 | 0 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 539 | 1 539 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856; `binary32`: extreme 217 856, nearzero 435 716, overflow 217 856, point 435 715, pow2 217 856, special 435 716, tails 435 714, underflow 217 857, uniform 217 858, zero 217 856.

### `le_1_2`

Claims: `predicate(m) le(a, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 4 489 164; false 2 710 836; a non-finite operand, false 601 596; a non-finite operand, true 298 404 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 4 509 396; false 2 690 604; a non-finite operand, false 601 002; a non-finite operand, true 298 998 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 889; false 2 880 115; a non-finite operand, false 33 154; a non-finite operand, true 16 577 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 449; false 1 722 627; a non-finite operand, false 28 834; a non-finite operand, true 14 417 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 817; false 916 883; a non-finite operand, false 9 026; a non-finite operand, true 4 513 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 227 025; false 229 043; a non-finite operand, false 4 482; a non-finite operand, true 2 241 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 141; false 12 567; a non-finite operand, false 962; a non-finite operand, true 481 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 349; false 2 511; a non-finite operand, false 378; a non-finite operand, true 189 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 896 | 896 | 0 | true 420; false 476; a non-finite operand, false 138; a non-finite operand, true 69 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `le_2_1`

Claims: `predicate(m) le(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 3 950 838; false 3 249 162; a non-finite operand, false 598 572; a non-finite operand, true 301 428 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 4 000 806; false 3 199 194; a non-finite operand, false 599 382; a non-finite operand, true 300 618 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 141; false 12 567; a non-finite operand, false 962; a non-finite operand, true 481 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 349; false 2 511; a non-finite operand, false 378; a non-finite operand, true 189 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 896 | 896 | 0 | true 420; false 476; a non-finite operand, false 138; a non-finite operand, true 69 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 889; false 2 880 115; a non-finite operand, false 33 154; a non-finite operand, true 16 577 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 449; false 1 722 627; a non-finite operand, false 28 834; a non-finite operand, true 14 417 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 817; false 916 883; a non-finite operand, false 9 026; a non-finite operand, true 4 513 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 227 025; false 229 043; a non-finite operand, false 4 482; a non-finite operand, true 2 241 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `le_2_2`

Claims: `predicate(m) le(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 4 386 006; false 2 813 994; a non-finite operand, false 598 374; a non-finite operand, true 301 626 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 4 400 946; false 2 799 054; a non-finite operand, false 602 748; a non-finite operand, true 297 252 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | true 493 521; false 494 515; a non-finite operand, false 3 970; a non-finite operand, true 1 985 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 181 476 | 181 476 | 0 | true 90 525; false 90 951; a non-finite operand, false 1 698; a non-finite operand, true 849 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 3 136 | 3 136 | 0 | true 1 540; false 1 596; a non-finite operand, false 218; a non-finite operand, true 109 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | true 3 790 881; false 3 793 635; a non-finite operand, false 11 010; a non-finite operand, true 5 505 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | true 2 035 153; false 2 037 171; a non-finite operand, false 8 066; a non-finite operand, true 4 033 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 3 247 204 | 3 247 204 | 0 | true 1 622 701; false 1 624 503; a non-finite operand, false 7 202; a non-finite operand, true 3 601 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | true 13 041; false 13 203; a non-finite operand, false 642; a non-finite operand, true 321 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `lt_1_2`

Claims: `predicate(m) lt(a, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 2 403 882; false 4 796 118; a non-finite operand, false 647 730; a non-finite operand, true 252 270 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 2 378 502; false 4 821 498; a non-finite operand, false 650 124; a non-finite operand, true 249 876 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 208; false 1 722 868; a non-finite operand, false 28 836; a non-finite operand, true 14 415 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 368; false 917 332; a non-finite operand, false 9 028; a non-finite operand, true 4 511 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 226 800; false 229 268; a non-finite operand, false 4 484; a non-finite operand, true 2 239 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 084; false 12 624; a non-finite operand, false 964; a non-finite operand, true 479 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 896 | 896 | 0 | true 405; false 491; a non-finite operand, false 140; a non-finite operand, true 67 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 536; false 2 880 468; a non-finite operand, false 33 156; a non-finite operand, true 16 575 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 320; false 2 540; a non-finite operand, false 380; a non-finite operand, true 187 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `lt_2_1`

Claims: `predicate(m) lt(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 2 925 522; false 4 274 478; a non-finite operand, false 647 028; a non-finite operand, true 252 972 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 2 864 556; false 4 335 444; a non-finite operand, false 650 052; a non-finite operand, true 249 948 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | true 1 708 208; false 1 722 868; a non-finite operand, false 28 836; a non-finite operand, true 14 415 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | true 226 800; false 229 268; a non-finite operand, false 4 484; a non-finite operand, true 2 239 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | true 2 320; false 2 540; a non-finite operand, false 380; a non-finite operand, true 187 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | true 2 863 536; false 2 880 468; a non-finite operand, false 33 156; a non-finite operand, true 16 575 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | true 912 368; false 917 332; a non-finite operand, false 9 028; a non-finite operand, true 4 511 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | true 12 084; false 12 624; a non-finite operand, false 964; a non-finite operand, true 479 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 896 | 896 | 0 | true 405; false 491; a non-finite operand, false 140; a non-finite operand, true 67 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `lt_2_2`

Claims: `predicate(m) lt(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 2 514 600; false 4 685 400; a non-finite operand, false 648 234; a non-finite operand, true 251 766 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | true 2 494 350; false 4 705 650; a non-finite operand, false 647 424; a non-finite operand, true 252 576 |
| `fp:4:-6:1`, every operand (another number of exponents) | 7 584 516 | 7 584 516 | 0 | true 3 788 128; false 3 796 388; a non-finite operand, false 11 012; a non-finite operand, true 5 503 |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | true 2 033 136; false 2 039 188; a non-finite operand, false 8 068; a non-finite operand, true 4 031 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 988 036 | 988 036 | 0 | true 492 528; false 495 508; a non-finite operand, false 3 972; a non-finite operand, true 1 983 |
| `fp:3:-4:1`, every operand (p = min_precision + 2, the quick tier's format) | 181 476 | 181 476 | 0 | true 90 100; false 91 376; a non-finite operand, false 1 700; a non-finite operand, true 847 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 26 244 | 26 244 | 0 | true 12 880; false 13 364; a non-finite operand, false 644; a non-finite operand, true 319 |
| `fp:3:-6:3`, every operand (p = min_precision + 2, another number of exponents) | 3 247 204 | 3 247 204 | 0 | true 1 620 900; false 1 626 304; a non-finite operand, false 7 204; a non-finite operand, true 3 599 |
| `fp:1:-2:3`, every operand (p = min_precision, the quick tier's number of exponents) | 3 136 | 3 136 | 0 | true 1 485; false 1 651; a non-finite operand, false 220; a non-finite operand, true 107 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625; `binary32`: equal 31 250, extreme 15 625, halfgap 15 625, lastplace 31 250, leadequal 15 625, neighbor 15 625, nonfinite 31 250, overflow 15 625, pow2 15 625, straddle 15 625, underflow 15 625, uniform 15 625, zero 15 625.

### `make_2`

Claims: `represents(x)`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 827 394 | 827 394 | 0 |
| `fp:13:-31:8`, every operand (quick tier + 2 bits) | 335 874 | 335 874 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 167 938 | 167 938 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 166 | 166 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 84 | 84 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 330 | 330 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000; `binary32`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000.

### `make_2_limbs`

Claims: `represents(x)`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000; `binary32`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000.

### `mul_1_1`

Claims: `rounded(p) nearest`; `error(p) form R, c=1/(1+u), k=1, t=1/2`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 82 997 496 | 0 | exact 29 922 966; inexact 53 007 516; tie 67 014 | 1 - ε, ε < 10⁻⁹ | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 83 643 858 | 0 | exact 30 128 220; inexact 53 296 200; tie 219 438 | 0.9999999404 | 0.9999998212 |
| `fp:2:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 597 | 0 | exact 1 089; inexact 1 364; tie 144 | 0.833333 | 0.444444 |
| `fp:1:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 625 | 0 | exact 313; inexact 264; tie 48 | 0.75 | 0 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | exact 114 689; inexact 3 989 676; tie 75 928 | 0.999939 | 0.992248 |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | exact 145 697; inexact 1 967 764; tie 84 024 | 0.999756 | 0.992248 |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | exact 118 385; inexact 2 267 576; tie 74 352 | 0.999512 | 0.992248 |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | exact 49 985; inexact 559 608; tie 27 888 | 0.999512 | 0.984615 |
| `fp:3:-12:-1`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 481 | 0 | exact 2 921; inexact 6 128; tie 1 432 | 0.999512 | 0.888889 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  mul_1_1 binary64 0x1p-201 0x1p-874 #pow2:63570 -> 0x0p+0
largest error / bound, interpreter 0.999939 (fp:7:-20:-6, every operand):
  mul_1_1 fp:7:-20:-6 -0x1.8p+0 -0x1.58p-1 #exhaustive:63562 -> 0x1p+0
```

### `mul_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 892 866 | 0 | 0.994154 | 1.76053 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 886 782 | 0 | 0.9999998510 | 1.75668 |
| `fp:6:-8:-2`, every operand (quick tier + 2 bits) | 4 152 897 | 2 754 581 | 0 | 0.972718 | - |
| `fp:5:-4:2`, every operand (another exponent range) | 1 027 905 | 304 717 | 0 | 0.907265 | - |
| `fp:3:-8:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 42 273 | 41 241 | 0 | 0.794235 | - |
| `fp:5:-8:-2`, every operand (quick tier + 1 bit) | 1 027 905 | 799 453 | 0 | 0.951325 | - |
| `fp:2:-8:-2`, every operand (p = min_precision, the quick tier's exponent range) | 7 285 | 7 285 | 0 | 0.628272 | 0.410256 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.9999998510 (clang18-fixup-call/cxx, linux-x86-64):
  mul_2_1 binary32 0x1.8p+0 0x1p-24 -0x1.fffffcp-127 #extreme:43278 -> -0x1.7ffffcp-126 -0x0p+0
largest error / bound, interpreter 0.972718 (fp:6:-8:-2, every operand):
  mul_2_1 fp:6:-8:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-5 #exhaustive:1480613 -> 0x1.4p-3 0x0p+0
```

### `mul_2_1_entry`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 98 246 034 | 0 | 0.9999999998 | 1.94872 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 98 134 362 | 0 | 0.9999998808 | 1.99267 |
| `fp:6:-8:-2`, every operand (quick tier + 2 bits) | 4 152 897 | 2 754 581 | 0 | 0.972718 | - |
| `fp:2:-8:-2`, every operand (p = min_precision, the quick tier's exponent range) | 7 285 | 7 285 | 0 | 0.628272 | 0.410256 |
| `fp:5:-4:2`, every operand (another exponent range) | 1 027 905 | 304 717 | 0 | 0.907265 | - |
| `fp:5:-8:-2`, every operand (quick tier + 1 bit) | 1 027 905 | 799 453 | 0 | 0.951325 | - |
| `fp:3:-8:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 42 273 | 41 241 | 0 | 0.794235 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165; `binary32`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.9999999998 (msvc-fixup-call/cxx, windows-x64):
  mul_2_1_entry binary64 0x1.80000001p+0 0x1.fffffffffffffp-54 0x1.0000000000001p-1022 #extreme:87366 -> 0x1.8000000100003p-1022 0x0.0000000000000p+0
largest error / bound, interpreter 0.972718 (fp:6:-8:-2, every operand):
  mul_2_1_entry fp:6:-8:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-5 #exhaustive:1480613 -> 0x1.4p-3 0x0p+0
```

### `mul_2_1_full`

Claims: `extends(w) F1-F5, core mul_2_1, lead mul, finite when |x*a| <= 2^(qmax+p-1)`; `F2, core mul_2_1: normalized(z)`; `F2, core mul_2_1: error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.995324 | 1.73305 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.978571 | 1.80132 |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0.972718 | - |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.759322 | - |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.951325 | - |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.907193 | 1.23671 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0.936776 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | 0.579710 | 0.410256 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 25 000, close 37 500, edge 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, threshold 25 000, underflow 25 000, uniform 12 500, zero 12 500, zeroinf 25 000; `binary32`: cancel 25 000, close 37 500, edge 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, threshold 25 000, underflow 25 000, uniform 12 500, zero 12 500, zeroinf 25 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.995324 (clang18-fixup-call/cxx, linux-x86-64):
  mul_2_1_full binary64 -0x1.c20b0911b3b6p-67 -0x1.063ed28cb1132p-121 0x1.c00fc905575a2p-946 #underflow:67303 -> -0x1.89d787f448373p-1012 0x0.00000000001b1p-1022
largest error / bound, interpreter 0.972718 (fp:6:-7:-2, every operand):
  mul_2_1_full fp:6:-7:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-4 #exhaustive:651814 -> 0x1.4p-2 0x0p+0
```

### `mul_2_1_full_entry`

Claims: `extends(w) F1-F5, core mul_2_1_entry, lead mul, finite when |x*a| <= 2^(qmax+p-1)`; `F2, core mul_2_1_entry: normalized(z)`; `F2, core mul_2_1_entry: error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.991667 | 1.86114 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.991020 | 1.90716 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.951325 | - |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0.972718 | - |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0.936776 | - |
| `fp:3:-4:1`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.759322 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's number of exponents) | 4 860 | 4 860 | 0 | 0.579710 | 0.410256 |
| `fp:4:-9:4`, every operand (another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.907193 | 1.23671 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 25 000, close 37 500, edge 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, threshold 25 000, underflow 25 000, uniform 12 500, zero 12 500, zeroinf 25 000; `binary32`: cancel 25 000, close 37 500, edge 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, threshold 25 000, underflow 25 000, uniform 12 500, zero 12 500, zeroinf 25 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.991667 (clang-fixup-inline/cxx, macos-arm64):
  mul_2_1_full_entry binary64 -0x1.a54f32f125a25p-179 0x1.0200000000008p-248 0x1.0b7514d079378p-813 #underflow:44183 -> -0x1.b82a499512488p-992 0x1.61581cep-1047
largest error / bound, interpreter 0.972718 (fp:6:-7:-2, every operand):
  mul_2_1_full_entry fp:6:-7:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-4 #exhaustive:651814 -> 0x1.4p-2 0x0p+0
```

### `mul_2_2`

Claims: `normalized(z)`; `error(z) form R, c=4, k=2, t=3/2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 891 426 | 0 | 0.948314 | 2.99854 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 883 434 | 0 | 0.944221 | 2.88509 |
| `fp:6:-7:-3`, every operand (quick tier + 2 bits) | 4 124 961 | 1 593 537 | 0 | 0.898829 | - |
| `fp:4:-7:-3`, every operand (p = min_precision, the quick tier's format) | 245 025 | 209 281 | 0 | 0.791964 | - |
| `fp:5:-8:-2`, every operand (p = min_precision + 1, another exponent range) | 16 248 961 | 6 272 821 | 0 | 0.878457 | - |
| `fp:4:-9:-3`, every operand (p = min_precision, another exponent range) | 3 038 049 | 2 716 377 | 0 | 0.850806 | - |
| `fp:5:-7:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 014 049 | 606 801 | 0 | 0.864716 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.948314 (clang18-fixup-call/cxx, linux-x86-64):
  mul_2_2 binary64 0x1.44fbe57f84b75p-822 -0x1.4a8845c9bc12fp-902 0x1.83fc2d5cd6408p-161 0x1.f558a1871c35ap-236 #underflow:44012 -> 0x1.ec88ed7bd1022p-983 -0x0.000312b497bcfp-1022
largest error / bound, interpreter 0.898829 (fp:6:-7:-3, every operand):
  mul_2_2 fp:6:-7:-3 -0x1.2p-1 0x1p-7 -0x1.2p-1 0x1p-7 #exhaustive:1918208 -> 0x1.3p-2 0x0p+0
```

### `mul_2_2_full`

Claims: `extends(w) F1-F5, core mul_2_2, lead mul, finite when |x*y| <= 2^(qmax+p-1)`; `F2, core mul_2_2: normalized(z)`; `F2, core mul_2_2: error(z) form R, c=4, k=2, t=3/2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.933668 | 3.03122 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.950727 | 3.35939 |
| `fp:4:-6:1`, every operand (p = min_precision, another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.791964 | - |
| `fp:5:-6:-1`, every operand (p = min_precision + 1, another number of exponents) | 4 072 324 | 4 072 324 | 0 | 0.838827 | - |
| `fp:6:-6:-3`, every operand (quick tier + 2 bits) | 1 036 324 | 1 036 324 | 0 | 0.816656 | - |
| `fp:5:-5:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 256 036 | 256 036 | 0 | 0.733319 | - |
| `fp:4:-4:-1`, every operand (p = min_precision, the quick tier's format) | 62 500 | 62 500 | 0 | 0.561075 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 25 000, close 37 500, edge 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, threshold 25 000, underflow 25 000, uniform 12 500, zero 12 500, zeroinf 25 000; `binary32`: cancel 25 000, close 37 500, edge 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, threshold 25 000, underflow 25 000, uniform 12 500, zero 12 500, zeroinf 25 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.950727 (msvc-fixup-call/cxx, windows-x64):
  mul_2_2_full binary32 0x1.4d3908p-8 0x1.cf03dcp-36 -0x1.c2dddcp-110 -0x1.9278p-136 #underflow:17003 -> -0x1.256f840000000p-117 -0x1.5c00000000000p-142
largest error / bound, interpreter 0.838827 (fp:5:-6:-1, every operand):
  mul_2_2_full fp:5:-6:-1 -0x1.4p-1 0x1p-6 -0x1.2p-1 0x1p-6 #exhaustive:1954396 -> 0x1.4p-2 0x0p+0
```

### `mul_ball_2_2`

Claims: `normalized(z)`; `error(z) form R, c=4, k=2, t=3/2`; `encloses(z, d) x*y over `.

| Run | Cases | Judged | Failed | largest error / bound | observed c | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 643 314 | 0 | 0.949708 | 2.48259 | 2.12668e+15 | 1.61122 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 634 296 | 0 | 0.942075 | 2.80000 | 2.57199e+6 | 1.42857 |
| `fp:4:-7:-3`, every operand (p = min_precision, the quick tier's format) | 245 025 | 209 281 | 0 | 0.791964 | - | 8.40625 | 10.0787 |
| `fp:5:-8:-2`, every operand (p = min_precision + 1, another exponent range) | 16 248 961 | 6 272 821 | 0 | 0.878457 | - | 14.9844 | 8.43411 |
| `fp:6:-7:-3`, every operand (quick tier + 2 bits) | 4 124 961 | 1 593 537 | 0 | 0.898829 | - | 35.6172 | 26.7571 |
| `fp:4:-9:-3`, every operand (p = min_precision, another exponent range) | 3 038 049 | 2 716 377 | 0 | 0.850806 | - | 7.03516 | 4.57435 |
| `fp:5:-7:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 014 049 | 606 801 | 0 | 0.864716 | - | 19.6172 | 15.1864 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 35 715, close 35 716, exactprod 35 714, extreme 17 855, overflow 17 857, pow2 17 855, tiny 35 716, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: aroundp 35 715, close 35 716, exactprod 35 714, extreme 17 855, overflow 17 857, pow2 17 855, tiny 35 716, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.949708 (clang18-fixup-call/cxx, linux-x86-64):
  mul_ball_2_2 binary64 0x1.ef0b3d74f67e7p-554 -0x1.59123ab87ad3ap-611 0x1.f411ff0023f4ep-437 -0x1.8775a5aca663p-521 #tiny:54281 -> 0x1.e3826071fef97p-990 0x0.00000151e04b2p-1022 0x1.0000000000005p-1022
largest error / bound, interpreter 0.898829 (fp:6:-7:-3, every operand):
  mul_ball_2_2 fp:6:-7:-3 -0x1.2p-1 0x1p-7 -0x1.2p-1 0x1p-7 #exhaustive:1918208 -> 0x1.3p-2 0x0p+0 0x1.28p-2
smallest radius slack, gaps, compiled 2.57199e+6 (msvc-fixup-call/cxx, windows-x64):
  mul_ball_2_2 binary32 0x1.95bcbep-27 0x1.fffffep-52 -0x1.49b4c8p+104 -0x1p+80 #extreme:14965 -> -0x1.05470c0000000p+78 -0x1.7cfbe00000000p+52 0x1.0547160000000p+32
smallest radius slack, gaps, interpreter 7.03516 (fp:4:-9:-3, every operand):
  mul_ball_2_2 fp:4:-9:-3 -0x1.8p+0 -0x1p-8 -0x1.2p+0 0x1.cp-5 #exhaustive:287928 -> 0x1.ap+0 0x0p+0 0x1.2p-4
```

### `mul_dir_1`

Claims: `bound(d) below, steps=1, a zero factor gives zero`; `rounded(d) down, when product_large, a zero factor gives zero`; `bound(v) above, steps=1, a zero factor gives zero`; `rounded(v) up, when product_large, a zero factor gives zero`.

| Run | Cases | Judged | Failed | cases by rounding | cases by rounding |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 16 443 216; inexact, as RN 8 310 672; differs from RN 13 910 400; a non-finite operand 6 894 432; an infinite operand, no NaN operand 6 894 432; overflow: value above Omega 5 572 872; overflow: value below -Omega 5 575 104; product_large does not hold (nothing claimed) 23 035 608; product_large holds 44 239 392; rounds to -inf 5 575 104; zero_factor: a zero against an infinite operand 13 805 568; zero_factor: a zero operand 29 330 568 | exact 16 443 216; inexact, as RN 8 337 528; differs from RN 13 885 776; a non-finite operand 6 894 432; an infinite operand, no NaN operand 6 894 432; overflow: value above Omega 5 572 872; overflow: value below -Omega 5 575 104; product_large does not hold (nothing claimed) 23 035 608; product_large holds 44 239 392; rounds to inf 5 572 872; zero_factor: a zero against an infinite operand 13 805 568; zero_factor: a zero operand 29 330 568 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 15 071 112; inexact, as RN 7 772 652; differs from RN 13 338 648; a non-finite operand 6 911 532; an infinite operand, no NaN operand 6 911 532; overflow: value above Omega 5 540 238; overflow: value below -Omega 5 553 072; product_large does not hold (nothing claimed) 25 539 516; product_large holds 41 735 484; rounds to -inf 5 553 072; zero_factor: a zero against an infinite operand 13 788 468; zero_factor: a zero operand 29 313 468 | exact 15 071 112; inexact, as RN 7 798 410; differs from RN 13 325 724; a non-finite operand 6 911 532; an infinite operand, no NaN operand 6 911 532; overflow: value above Omega 5 540 238; overflow: value below -Omega 5 553 072; product_large does not hold (nothing claimed) 25 539 516; product_large holds 41 735 484; rounds to inf 5 540 238; zero_factor: a zero against an infinite operand 13 788 468; zero_factor: a zero operand 29 313 468 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 739 329 | 4 739 329 | 0 | exact 96 368; inexact, as RN 933 046; differs from RN 1 272 328; a non-finite operand 8 700; an infinite operand, no NaN operand 8 700; overflow: value above Omega 339 786; overflow: value below -Omega 339 786; product_large does not hold (nothing claimed) 2 084 748; product_large holds 2 641 528; rounds to -inf 339 786; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 4 353 | exact 96 368; inexact, as RN 933 046; differs from RN 1 272 328; a non-finite operand 8 700; an infinite operand, no NaN operand 8 700; overflow: value above Omega 339 786; overflow: value below -Omega 339 786; product_large does not hold (nothing claimed) 2 084 748; product_large holds 2 641 528; rounds to inf 339 786; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 4 353 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 329 409 | 1 329 409 | 0 | exact 4 208; inexact, as RN 43 382; differs from RN 149 952; a non-finite operand 4 604; an infinite operand, no NaN operand 4 604; overflow: value above Omega 106 850; overflow: value below -Omega 106 850; product_large does not hold (nothing claimed) 1 018 108; product_large holds 304 392; rounds to -inf 106 850; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 2 305 | exact 4 208; inexact, as RN 43 382; differs from RN 149 952; a non-finite operand 4 604; an infinite operand, no NaN operand 4 604; overflow: value above Omega 106 850; overflow: value below -Omega 106 850; product_large does not hold (nothing claimed) 1 018 108; product_large holds 304 392; rounds to inf 106 850; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 2 305 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 332 929 | 332 929 | 0 | exact 4 144; inexact, as RN 22 768; differs from RN 49 218; a non-finite operand 2 300; an infinite operand, no NaN operand 2 300; overflow: value above Omega 26 630; overflow: value below -Omega 26 630; product_large does not hold (nothing claimed) 226 716; product_large holds 102 760; rounds to -inf 26 630; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 1 153 | exact 4 144; inexact, as RN 22 768; differs from RN 49 218; a non-finite operand 2 300; an infinite operand, no NaN operand 2 300; overflow: value above Omega 26 630; overflow: value below -Omega 26 630; product_large does not hold (nothing claimed) 226 716; product_large holds 102 760; rounds to inf 26 630; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 1 153 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 329 | 5 329 | 0 | exact 964; inexact, as RN 606; differs from RN 1 006; a non-finite operand 284; an infinite operand, no NaN operand 284; overflow: value above Omega 400; overflow: value below -Omega 400; product_large does not hold (nothing claimed) 1 924; product_large holds 2 976; rounds to -inf 400; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 145 | exact 964; inexact, as RN 606; differs from RN 1 006; a non-finite operand 284; an infinite operand, no NaN operand 284; overflow: value above Omega 400; overflow: value below -Omega 400; product_large does not hold (nothing claimed) 1 924; product_large holds 2 976; rounds to inf 400; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 145 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 369 | 1 369 | 0 | exact 500; inexact, as RN 78; differs from RN 168; a non-finite operand 140; an infinite operand, no NaN operand 140; overflow: value above Omega 90; overflow: value below -Omega 90; product_large does not hold (nothing claimed) 320; product_large holds 836; rounds to -inf 90; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 73 | exact 500; inexact, as RN 78; differs from RN 168; a non-finite operand 140; an infinite operand, no NaN operand 140; overflow: value above Omega 90; overflow: value below -Omega 90; product_large does not hold (nothing claimed) 320; product_large holds 836; rounds to inf 90; zero_factor: a zero against an infinite operand 4; zero_factor: a zero operand 73 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 310 000, beyond 310 000, exactprod 310 000, extreme 155 000, nonfinite 310 000, overflow 155 000, pow2 155 000, tiny 310 000, underflow 155 000, uniform 155 000, zero 155 000, zerofactor 310 000, zeroinf 310 000; `binary32`: aroundp 310 000, beyond 310 000, exactprod 310 000, extreme 155 000, nonfinite 310 000, overflow 155 000, pow2 155 000, tiny 310 000, underflow 155 000, uniform 155 000, zero 155 000, zerofactor 310 000, zeroinf 310 000.

### `mul_dir_2_2`

Claims: `normalized(l)`; `normalized(h)`; `outward(l) below`; `outward(h) above`.

| Run | Cases | Judged | Failed | largest |output - value| / allowance | largest |output - value| / allowance |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 641 298 | 0 | 0.700000 | 0.700000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 632 010 | 0 | 0.699999 | 0.729568 |
| `fp:4:-9:-3`, every operand (p = min_precision, another exponent range) | 3 038 049 | 2 716 377 | 0 | 0.498847 | 0.498847 |
| `fp:4:-7:-3`, every operand (p = min_precision, the quick tier's format) | 245 025 | 209 281 | 0 | 0.491543 | 0.491543 |
| `fp:5:-8:-2`, every operand (p = min_precision + 1, another exponent range) | 16 248 961 | 6 272 821 | 0 | 0.500017 | 0.500017 |
| `fp:6:-7:-3`, every operand (quick tier + 2 bits) | 4 124 961 | 1 593 537 | 0 | 0.497421 | 0.497421 |
| `fp:5:-7:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 014 049 | 606 801 | 0 | 0.488016 | 0.488016 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 35 715, close 35 716, exactprod 35 714, extreme 17 855, overflow 17 857, pow2 17 855, tiny 35 716, underflow 17 857, uniform 17 858, zero 17 857; `binary32`: aroundp 35 715, close 35 716, exactprod 35 714, extreme 17 855, overflow 17 857, pow2 17 855, tiny 35 716, underflow 17 857, uniform 17 858, zero 17 857.

Where the extremes are attained (the line as the oracle reports it):

```
largest |output - value| / allowance, compiled 0.729568 (clang18-fixup-call/cxx, linux-x86-64):
  mul_dir_2_2 binary32 0x1.959a7p-24 -0x1.fffffep-49 -0x1.536b7cp+66 0x1p+42 #extreme:15651 -> -0x1.0ce2e6p+43 0x1.2acf4ep+17 -0x1.0ce2e6p+43 0x1.2acf72p+17
largest |output - value| / allowance, interpreter 0.500017 (fp:5:-8:-2, every operand):
  mul_dir_2_2 fp:5:-8:-2 -0x1.ap+2 0x1.7p-4 -0x1.7p-1 -0x1p-8 #exhaustive:1509424 -> 0x1.2p+2 -0x1p-6 0x1.3p+2 0x1.8p-7
largest |output - value| / allowance, compiled 0.729568 (clang18-fixup-call/cxx, linux-x86-64):
  mul_dir_2_2 binary32 0x1.959a7p-24 -0x1.fffffep-49 -0x1.536b7cp+66 0x1p+42 #extreme:15651 -> -0x1.0ce2e6p+43 0x1.2acf4ep+17 -0x1.0ce2e6p+43 0x1.2acf72p+17
largest |output - value| / allowance, interpreter 0.500017 (fp:5:-8:-2, every operand):
  mul_dir_2_2 fp:5:-8:-2 -0x1.ap+2 0x1.7p-4 -0x1.7p-1 -0x1p-8 #exhaustive:1509424 -> 0x1.2p+2 -0x1p-6 0x1.3p+2 0x1.8p-7
```

### `mul_down_1`

Claims: `bound(r) below, steps=1`; `rounded(r) down, when product_large`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 22 516 614; inexact, as RN 9 380 538; differs from RN 13 724 244; a NaN operand 5 757 570; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 595 278; overflow: value above Omega 4 319 064; overflow: value below -Omega 4 323 276; product_large does not hold (nothing claimed) 29 202 480; product_large holds 49 944 672; rounds to -inf 4 323 276; value NaN from operands that are not NaN 11 510 712 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 21 502 656; inexact, as RN 8 830 602; differs from RN 13 105 242; a NaN operand 5 747 724; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 605 124; overflow: value above Omega 4 297 878; overflow: value below -Omega 4 301 316; product_large does not hold (nothing claimed) 31 407 336; product_large holds 47 739 816; rounds to -inf 4 301 316; value NaN from operands that are not NaN 11 503 602 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 6 509; inexact, as RN 43 382; differs from RN 149 952; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 106 850; overflow: value below -Omega 106 850; product_large does not hold (nothing claimed) 1 018 108; product_large holds 306 693; rounds to -inf 106 850; value NaN from operands that are not NaN 4 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 105; inexact, as RN 606; differs from RN 1 006; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 400; overflow: value below -Omega 400; product_large does not hold (nothing claimed) 1 924; product_large holds 3 117; rounds to -inf 400; value NaN from operands that are not NaN 4 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 569; inexact, as RN 78; differs from RN 168; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 90; overflow: value below -Omega 90; product_large does not hold (nothing claimed) 320; product_large holds 905; rounds to -inf 90; value NaN from operands that are not NaN 4 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 100 717; inexact, as RN 933 046; differs from RN 1 272 328; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 339 786; overflow: value below -Omega 339 786; product_large does not hold (nothing claimed) 2 084 748; product_large holds 2 645 877; rounds to -inf 339 786; value NaN from operands that are not NaN 4 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 5 293; inexact, as RN 22 768; differs from RN 49 218; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 26 630; overflow: value below -Omega 26 630; product_large does not hold (nothing claimed) 226 716; product_large holds 103 909; rounds to -inf 26 630; value NaN from operands that are not NaN 4 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704; `binary32`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704.

### `mul_down_entry`

Claims: `bound(r) below, steps=1`; `rounded(r) down, when product_large`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 22 464 882; inexact, as RN 9 427 770; differs from RN 13 725 180; a NaN operand 5 738 940; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 613 908; overflow: value above Omega 4 320 720; overflow: value below -Omega 4 310 712; product_large does not hold (nothing claimed) 29 218 608; product_large holds 49 928 544; rounds to -inf 4 310 712; value NaN from operands that are not NaN 11 508 876 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 21 501 684; inexact, as RN 8 822 700; differs from RN 13 121 280; a NaN operand 5 744 772; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 608 076; overflow: value above Omega 4 299 606; overflow: value below -Omega 4 289 184; product_large does not hold (nothing claimed) 31 412 304; product_large holds 47 734 848; rounds to -inf 4 289 184; value NaN from operands that are not NaN 11 509 794 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 6 509; inexact, as RN 43 382; differs from RN 149 952; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 106 850; overflow: value below -Omega 106 850; product_large does not hold (nothing claimed) 1 018 108; product_large holds 306 693; rounds to -inf 106 850; value NaN from operands that are not NaN 4 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 5 293; inexact, as RN 22 768; differs from RN 49 218; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 26 630; overflow: value below -Omega 26 630; product_large does not hold (nothing claimed) 226 716; product_large holds 103 909; rounds to -inf 26 630; value NaN from operands that are not NaN 4 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 105; inexact, as RN 606; differs from RN 1 006; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 400; overflow: value below -Omega 400; product_large does not hold (nothing claimed) 1 924; product_large holds 3 117; rounds to -inf 400; value NaN from operands that are not NaN 4 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 100 717; inexact, as RN 933 046; differs from RN 1 272 328; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 339 786; overflow: value below -Omega 339 786; product_large does not hold (nothing claimed) 2 084 748; product_large holds 2 645 877; rounds to -inf 339 786; value NaN from operands that are not NaN 4 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 569; inexact, as RN 78; differs from RN 168; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 90; overflow: value below -Omega 90; product_large does not hold (nothing claimed) 320; product_large holds 905; rounds to -inf 90; value NaN from operands that are not NaN 4 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704; `binary32`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704.

### `mul_ext_2_2`

Claims: `normalized(l)`; `normalized(h)`; `outward(l) below, a zero factor gives zero`; `outward(h) above, a zero factor gives zero`.

| Run | Cases | Judged | Failed | largest |output - value| / allowance | largest |output - value| / allowance |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.703759 | 0.700000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.699999 | 0.682467 |
| `fp:5:-6:-1`, every operand (p = min_precision + 1, another number of exponents) | 4 068 289 | 4 068 289 | 0 | 0.485805 | 0.485805 |
| `fp:4:-4:-1`, every operand (p = min_precision, the quick tier's format) | 62 001 | 62 001 | 0 | 0.459274 | 0.459274 |
| `fp:4:-6:1`, every operand (p = min_precision, another number of exponents) | 7 579 009 | 7 579 009 | 0 | 0.487404 | 0.487404 |
| `fp:6:-6:-3`, every operand (quick tier + 2 bits) | 1 034 289 | 1 034 289 | 0 | 0.497170 | 0.497170 |
| `fp:5:-5:-2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 255 025 | 255 025 | 0 | 0.485753 | 0.485753 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 25 000, close 25 000, edge 25 000, exactprod 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, tiny 25 000, underflow 12 500, uniform 12 500, zero 12 500, zeroinf 25 000; `binary32`: aroundp 25 000, close 25 000, edge 25 000, exactprod 25 000, extreme 12 500, nonfinite 25 000, overflow 12 500, pow2 12 500, tiny 25 000, underflow 12 500, uniform 12 500, zero 12 500, zeroinf 25 000.

Where the extremes are attained (the line as the oracle reports it):

```
largest |output - value| / allowance, compiled 0.703759 (clang18-fixup-call/cxx, linux-x86-64):
  mul_ext_2_2 binary64 -0x1.015a5adbf43fp+1023 -0x1p+970 -0x1.fffffffffffffp-1 -0x1.cc196e2775179p-55 #overflow:46416 -> 0x1.015a5adbf43fp+1023 0x1.c91e8062c6e37p+968 0x1.015a5adbf43fp+1023 0x1.c91e8062c6e49p+968
largest |output - value| / allowance, interpreter 0.497170 (fp:6:-6:-3, every operand):
  mul_ext_2_2 fp:6:-6:-3 -0x1.48p+1 0x1p-6 0x1.6p+0 0x1p-6 #exhaustive:350444 -> -0x1.1p+2 0x1p-5 -0x1.7p+1 -0x1p-5
largest |output - value| / allowance, compiled 0.703759 (clang18-fixup-call/cxx, linux-x86-64):
  mul_ext_2_2 binary64 -0x1.015a5adbf43fp+1023 -0x1p+970 -0x1.fffffffffffffp-1 -0x1.cc196e2775179p-55 #overflow:46416 -> 0x1.015a5adbf43fp+1023 0x1.c91e8062c6e37p+968 0x1.015a5adbf43fp+1023 0x1.c91e8062c6e49p+968
largest |output - value| / allowance, interpreter 0.497170 (fp:6:-6:-3, every operand):
  mul_ext_2_2 fp:6:-6:-3 -0x1.48p+1 0x1p-6 0x1.6p+0 0x1p-6 #exhaustive:350444 -> -0x1.1p+2 0x1p-5 -0x1.7p+1 -0x1p-5
```

### `mul_pow2_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 96 052 896 | 0 | 0.750000 | 4.79895e-17 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 96 303 888 | 0 | 0.750000 | 2.98023e-8 |
| `fp:6:-12:4`, every operand (another exponent range) | 6 021 994 | 4 488 874 | 0 | 0.746094 | 0.00781249 |
| `fp:3:-6:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 14 949 | 11 829 | 0 | 0.71875 | 0.0624390 |
| `fp:2:-6:2`, every operand (p = min_precision, the quick tier's exponent range) | 4 350 | 3 766 | 0 | 0.6875 | 0.124031 |
| `fp:7:-6:2`, every operand (quick tier + 2 bits) | 979 185 | 521 971 | 0 | 0.734375 | - |
| `fp:6:-6:2`, every operand (quick tier + 1 bit) | 398 706 | 231 604 | 0 | 0.734375 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 277 272, halfscaled 554 546, into 554 547, outof 277 273, overflow 277 272, pow2 277 273, underflow 277 272, uniform 277 274, zero 277 271; `binary32`: extreme 277 272, halfscaled 554 546, into 554 547, outof 277 273, overflow 277 272, pow2 277 273, underflow 277 272, uniform 277 274, zero 277 271.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.750000 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_2 binary64 -0x1.2909e8940c869p-85 -0x1.fffffffffffffp-139 0x1p-938 #extreme:322419 -> -0x0.9484f44a06434p-1022 -0x0p+0
largest error / bound, interpreter 0.746094 (fp:6:-12:4, every operand):
  mul_pow2_2 fp:6:-12:4 -0x1.f8p+4 0x1.f8p-3 0x1p-12 #exhaustive:2032404 -> -0x1p-7 0x0p+0
```

### `mul_pow2_2_full`

Claims: `extends(w) F1-F5, core mul_pow2_2, lead mul, finite when |x*c| <= 2^(qmax+p-1)`; `F2, core mul_pow2_2: normalized(z)`; `F2, core mul_pow2_2: error(z) form R, c=0, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | 0.747776 | 4.57042e-17 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | 0.750000 | 2.98023e-8 |
| `fp:6:-12:3`, every operand (another number of exponents) | 4 803 498 | 4 803 498 | 0 | 0.746094 | 0.00781249 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 456 988 | 456 988 | 0 | 0.746094 | - |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 211 354 | 211 354 | 0 | 0.746094 | - |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 9 860 | 9 860 | 0 | 0.71875 | 0 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 2 970 | 2 970 | 0 | 0.6875 | 0.124031 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: edge 321 050, extreme 160 527, halfscaled 321 054, into 321 054, nonfinite 321 052, outof 160 527, overflow 160 527, pow2 160 527, threshold 321 050, underflow 160 527, uniform 160 528, zero 160 527, zeroinf 321 050; `binary32`: edge 321 050, extreme 160 527, halfscaled 321 054, into 321 054, nonfinite 321 052, outof 160 527, overflow 160 527, pow2 160 527, threshold 321 050, underflow 160 527, uniform 160 528, zero 160 527, zeroinf 321 050.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.750000 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_2_full binary32 -0x1.64298ep+11 0x1.fffffep-14 0x1p-138 #extreme:593132 -> -0x1.64299p-127 0x0p+0
largest error / bound, interpreter 0.746094 (fp:6:-12:3, every operand):
  mul_pow2_2_full fp:6:-12:3 -0x1.f8p+4 0x1.f8p-3 0x1p-12 #exhaustive:1467606 -> -0x1p-7 0x0p+0
```

### `mul_pow2_map_1`

Claims: `entries(z) of the step mul_pow2_step_1 on x, c`; `finite_or_nan(z) flag finite`; `entries(z), step mul_pow2_step_1: rounded(z) nearest`; `entries(z), step mul_pow2_step_1: error(z) form R, c=0, k=1, t=1/2`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 19 150 254; inexact 1 193 430; tie 3 899 700 | 1 (the claim) | 0 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 20 814 408; inexact 1 148 832; tie 4 709 340 | 1 (the claim) | 0 |
| `fp:3:-3:0`, every operand (another format, every array up to 3 elements) | 1 355 010 | 1 355 010 | 0 | exact 2 599 290; inexact 385 080; tie 385 080 | 1 (the claim) | - |
| `fp:5:-7:0`, every operand (another format, every array up to 2 elements) | 2 021 892 | 2 021 892 | 0 | exact 2 586 708; inexact 780 192; tie 260 064 | 1 (the claim) | 0 |
| `fp:4:-5:0`, every operand (the full tier's format, every array up to 2 elements) | 234 963 | 234 963 | 0 | exact 302 991; inexact 73 120; tie 36 560 | 1 (the claim) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141; `binary32`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_step_1 binary64 0x1.ccp-340 0x1p-729 #mul_pow2_map_1:tight:7:element:0 -> 0x0.000000000003ap-1022
largest error / bound, interpreter 1 (fp:3:-3:0, every operand):
  mul_pow2_step_1 fp:3:-3:0 -0x1.cp+1 0x1p-3 #mul_pow2_map_1:exhaustive:30:element:0 -> -0x1p-1
```

### `mul_pow2_map_2`

Claims: `entries(z) of the step mul_pow2_step_2 on x, c`; `finite_or_nan(z) flag finite`; `entries(z), step mul_pow2_step_2: normalized(z)`; `entries(z), step mul_pow2_step_2: error(z) form R, c=0, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.750000 | 5.17214e-17 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.750000 | 2.72416e-8 |
| `fp:3:-4:1`, every operand (another format, every array up to 2 elements) | 2 907 032 | 2 907 032 | 0 | 0.6875 | - |
| `fp:3:-3:0`, every operand (the full tier's format, every array up to 2 elements) | 179 346 | 179 346 | 0 | 0.625 | - |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 8 955 | 8 955 | 0 | 0.71875 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.750000 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_step_2 binary64 -0x1.6f20789c0febbp-526 0x1.fffffffffffffp-580 0x1p-497 #mul_pow2_map_2:tight:31:element:858 -> -0x0.b7903c4e07f5ep-1022 0x0p+0
largest error / bound, interpreter 0.71875 (fp:4:-5:0, every operand):
  mul_pow2_step_2 fp:4:-5:0 -0x1.ep+2 0x1.cp-3 0x1p-5 #mul_pow2_map_2:exhaustive:2367:element:0 -> -0x1p-2 0x0p+0
```

### `mul_pow2_step_1`

Claims: `rounded(z) nearest`; `error(z) form R, c=0, k=1, t=1/2`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 96 815 808 | 0 | exact 63 604 602; inexact 26 824 356; tie 6 386 850 | 1 (the claim) | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 97 117 092 | 0 | exact 62 848 728; inexact 27 641 214; tie 6 627 150 | 1 (the claim) | 0 |
| `fp:8:-14:6`, every operand (quick tier + 1 bit) | 157 668 | 134 372 | 0 | exact 107 492; inexact 23 296; tie 3 584 | 1 (the claim) | 0 |
| `fp:2:-14:6`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 914 | 1 802 | 0 | exact 1 382; inexact 364; tie 56 | 1 (the claim) | 0 |
| `fp:7:-20:10`, every operand (another exponent range) | 151 515 | 134 107 | 0 | exact 107 227; inexact 24 320; tie 2 560 | 1 (the claim) | 0 |
| `fp:3:-14:6`, every operand (p = min_precision + 2, the quick tier's exponent range) | 4 025 | 3 737 | 0 | exact 2 897; inexact 728; tie 112 | 1 (the claim) | 0 |
| `fp:1:-14:6`, every operand (p = min_precision, the quick tier's exponent range) | 903 | 861 | 0 | exact 651; inexact 182; tie 28 | 1 (the claim) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 281 818, halfscaled 563 636, into 563 637, outof 281 818, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 817; `binary32`: extreme 281 818, halfscaled 563 636, into 563 637, outof 281 818, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 817.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_step_1 binary64 0x1p-1022 0x1p-53 #extreme:16487 -> 0x0p+0
largest error / bound, interpreter 1 (fp:8:-14:6, every operand):
  mul_pow2_step_1 fp:8:-14:6 -0x1.fep+6 0x1p-14 #exhaustive:25088 -> -0x1p-7
```

### `mul_pow2_step_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 94 342 464 | 0 | 0.729358 | 4.14911e-17 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 94 642 362 | 0 | 0.750000 | 2.98023e-8 |
| `fp:6:-12:4`, every operand (another exponent range) | 6 021 994 | 4 488 874 | 0 | 0.746094 | 0.00781249 |
| `fp:6:-6:2`, every operand (quick tier + 1 bit) | 398 706 | 231 604 | 0 | 0.734375 | - |
| `fp:3:-6:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 14 949 | 11 829 | 0 | 0.71875 | 0.0624390 |
| `fp:2:-6:2`, every operand (p = min_precision, the quick tier's exponent range) | 4 350 | 3 766 | 0 | 0.6875 | 0.124031 |
| `fp:7:-6:2`, every operand (quick tier + 2 bits) | 979 185 | 521 971 | 0 | 0.734375 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 259 090, halfscaled 518 182, into 518 183, outof 259 091, overflow 259 091, pow2 259 091, underflow 259 091, uniform 259 092, zero 259 089; `binary32`: extreme 259 090, halfscaled 518 182, into 518 183, outof 259 091, overflow 259 091, pow2 259 091, underflow 259 091, uniform 259 092, zero 259 089.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.750000 (clang18-fixup-call/cxx, linux-x86-64):
  mul_pow2_step_2 binary32 -0x1.b1b24ep-19 0x1.fffffep-44 0x1p-108 #extreme:189341 -> -0x1.b1b25p-127 0x0p+0
largest error / bound, interpreter 0.746094 (fp:6:-12:4, every operand):
  mul_pow2_step_2 fp:6:-12:4 -0x1.f8p+4 0x1.f8p-3 0x1p-12 #exhaustive:2032404 -> -0x1p-7 0x0p+0
```

### `mul_up_1`

Claims: `bound(r) above, steps=1`; `rounded(r) up, when product_large`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 22 518 486; inexact, as RN 9 373 050; differs from RN 13 738 698; a NaN operand 5 748 318; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 604 530; overflow: value above Omega 4 317 264; overflow: value below -Omega 4 329 558; product_large does not hold (nothing claimed) 29 199 654; product_large holds 49 947 498; rounds to inf 4 317 264; value NaN from operands that are not NaN 11 503 062 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 21 498 948; inexact, as RN 8 831 646; differs from RN 13 111 128; a NaN operand 5 758 830; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 594 018; overflow: value above Omega 4 288 482; overflow: value below -Omega 4 295 754; product_large does not hold (nothing claimed) 31 416 948; product_large holds 47 730 204; rounds to inf 4 288 482; value NaN from operands that are not NaN 11 511 846 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 5 293; inexact, as RN 22 768; differs from RN 49 218; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 26 630; overflow: value below -Omega 26 630; product_large does not hold (nothing claimed) 226 716; product_large holds 103 909; rounds to inf 26 630; value NaN from operands that are not NaN 4 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 105; inexact, as RN 606; differs from RN 1 006; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 400; overflow: value below -Omega 400; product_large does not hold (nothing claimed) 1 924; product_large holds 3 117; rounds to inf 400; value NaN from operands that are not NaN 4 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 569; inexact, as RN 78; differs from RN 168; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 90; overflow: value below -Omega 90; product_large does not hold (nothing claimed) 320; product_large holds 905; rounds to inf 90; value NaN from operands that are not NaN 4 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 100 717; inexact, as RN 933 046; differs from RN 1 272 328; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 339 786; overflow: value below -Omega 339 786; product_large does not hold (nothing claimed) 2 084 748; product_large holds 2 645 877; rounds to inf 339 786; value NaN from operands that are not NaN 4 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 6 509; inexact, as RN 43 382; differs from RN 149 952; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 106 850; overflow: value below -Omega 106 850; product_large does not hold (nothing claimed) 1 018 108; product_large holds 306 693; rounds to inf 106 850; value NaN from operands that are not NaN 4 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704; `binary32`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704.

### `mul_up_entry`

Claims: `bound(r) above, steps=1`; `rounded(r) up, when product_large`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 22 510 494; inexact, as RN 9 389 790; differs from RN 13 712 292; a NaN operand 5 760 072; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 592 776; overflow: value above Omega 4 322 124; overflow: value below -Omega 4 326 822; product_large does not hold (nothing claimed) 29 212 452; product_large holds 49 934 700; rounds to inf 4 322 124; value NaN from operands that are not NaN 11 507 130 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 21 485 322; inexact, as RN 8 832 564; differs from RN 13 102 542; a NaN operand 5 741 802; a non-finite operand 24 352 848; an infinite operand, no NaN operand 18 611 046; overflow: value above Omega 4 327 830; overflow: value below -Omega 4 294 890; product_large does not hold (nothing claimed) 31 398 894; product_large holds 47 748 258; rounds to inf 4 327 830; value NaN from operands that are not NaN 11 517 642 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 105; inexact, as RN 606; differs from RN 1 006; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 400; overflow: value below -Omega 400; product_large does not hold (nothing claimed) 1 924; product_large holds 3 117; rounds to inf 400; value NaN from operands that are not NaN 4 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 569; inexact, as RN 78; differs from RN 168; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 90; overflow: value below -Omega 90; product_large does not hold (nothing claimed) 320; product_large holds 905; rounds to inf 90; value NaN from operands that are not NaN 4 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 100 717; inexact, as RN 933 046; differs from RN 1 272 328; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 339 786; overflow: value below -Omega 339 786; product_large does not hold (nothing claimed) 2 084 748; product_large holds 2 645 877; rounds to inf 339 786; value NaN from operands that are not NaN 4 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 6 509; inexact, as RN 43 382; differs from RN 149 952; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 106 850; overflow: value below -Omega 106 850; product_large does not hold (nothing claimed) 1 018 108; product_large holds 306 693; rounds to inf 106 850; value NaN from operands that are not NaN 4 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 5 293; inexact, as RN 22 768; differs from RN 49 218; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 26 630; overflow: value below -Omega 26 630; product_large does not hold (nothing claimed) 226 716; product_large holds 103 909; rounds to inf 26 630; value NaN from operands that are not NaN 4 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704; `binary32`: aroundp 547 061, beyond 182 353, exactprod 182 354, extreme 182 352, nonfinite 364 704, overflow 182 353, pow2 182 352, tiny 364 707, underflow 182 353, uniform 182 355, zero 182 352, zeroinf 364 704.

### `neg_1`

Claims: `rounded(z) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 103 500 000 |
| `fp:12:-30:10`, every operand (quick tier + 1 bit) | 172 031 | 172 031 | 0 | exact 172 031 |
| `fp:13:-60:40`, every operand (another exponent range) | 835 583 | 835 583 | 0 | exact 835 583 |
| `fp:13:-30:10`, every operand (quick tier + 2 bits) | 344 063 | 344 063 | 0 | exact 344 063 |
| `fp:3:-30:10`, every operand (p = min_precision + 2, the quick tier's exponent range) | 335 | 335 | 0 | exact 335 |
| `fp:2:-30:10`, every operand (p = min_precision + 1, the quick tier's exponent range) | 167 | 167 | 0 | exact 167 |
| `fp:1:-30:10`, every operand (p = min_precision, the quick tier's exponent range) | 83 | 83 | 0 | exact 83 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

### `neg_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`; `represents(z)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0 (exact) | 0 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | 0 (exact) | - |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | 0 (exact) | 0 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | 0 (exact) | 0 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | 0 (exact) | 0 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000; `binary32`: extreme 25 000, halfgap 50 000, nonfinite 50 000, overflow 25 000, pow2 25 000, underflow 25 000, uniform 25 000, zero 25 000.

### `next_down`

Claims: `neighbor(r) down of a`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 167 938 | 167 938 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 827 394 | 827 394 | 0 |
| `fp:13:-31:8`, every operand (quick tier + 2 bits) | 335 874 | 335 874 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 330 | 330 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 166 | 166 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 84 | 84 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: binade 413 334, extreme 206 666, nonfinite 413 332, overflow 206 666, pow2 206 666, special 620 002, subnormal 413 334, underflow 206 666, uniform 206 668, zero 206 666; `binary32`: binade 413 334, extreme 206 666, nonfinite 413 332, overflow 206 666, pow2 206 666, special 620 002, subnormal 413 334, underflow 206 666, uniform 206 668, zero 206 666.

### `next_up`

Claims: `neighbor(r) up of a`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:13:-31:8`, every operand (quick tier + 2 bits) | 335 874 | 335 874 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 167 938 | 167 938 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 84 | 84 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 827 394 | 827 394 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 330 | 330 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 166 | 166 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: binade 413 334, extreme 206 666, nonfinite 413 332, overflow 206 666, pow2 206 666, special 620 002, subnormal 413 334, underflow 206 666, uniform 206 668, zero 206 666; `binary32`: binade 413 334, extreme 206 666, nonfinite 413 332, overflow 206 666, pow2 206 666, special 620 002, subnormal 413 334, underflow 206 666, uniform 206 668, zero 206 666.

### `norm_combine`

Claims: `maximum(r) of m, n`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:4:-9:4`, every operand (another exponent range) | 228 484 | 228 484 | 0 |
| `fp:2:-6:1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 4 900 | 4 900 | 0 |
| `fp:1:-6:1`, every operand (p = min_precision, the quick tier's exponent range) | 1 156 | 1 156 | 0 |
| `fp:5:-6:1`, every operand (quick tier + 1 bit) | 329 476 | 329 476 | 0 |
| `fp:3:-6:1`, every operand (p = min_precision + 2, the quick tier's exponent range) | 20 164 | 20 164 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 563 637, extreme 281 817, negative 281 818, neighbor 563 636, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 818; `binary32`: equal 563 637, extreme 281 817, negative 281 818, neighbor 563 636, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 818.

### `norm_finish_1`

Claims: `finite_or_nan(r) flag flag if ok`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 1 654 788 | 1 654 788 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 335 876 | 335 876 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 332 | 332 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 660 | 660 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 168 | 168 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, nonfinite 516 668, overflow 258 334, pow2 258 332, smallstep 516 666, top 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, nonfinite 516 668, overflow 258 334, pow2 258 332, smallstep 516 666, top 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `norm_finish_2`

Claims: `finite_or_nan(r) flag flag if ok, stepped up 1`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:1:-19:20`, every operand (p = min_precision, the quick tier's number of exponents) | 168 | 168 | 0 |
| `fp:13:-61:38`, every operand (another number of exponents) | 1 654 788 | 1 654 788 | 0 |
| `fp:12:-30:9`, every operand (quick tier + 1 bit) | 335 876 | 335 876 | 0 |
| `fp:3:-21:18`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 660 | 660 | 0 |
| `fp:2:-20:19`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 332 | 332 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 258 332, nonfinite 516 668, overflow 258 334, pow2 258 332, smallstep 516 666, top 516 668, underflow 258 334, uniform 258 334, zero 258 332; `binary32`: extreme 258 332, nonfinite 516 668, overflow 258 334, pow2 258 332, smallstep 516 666, top 516 668, underflow 258 334, uniform 258 334, zero 258 332.

### `norm_step_1`

Claims: `maximum(r) of m, abs(x)`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 |
| `fp:6:-7:0`, every operand (quick tier + 1 bit) | 661 250 | 661 250 | 0 |
| `fp:5:-10:3`, every operand (another exponent range) | 458 882 | 458 882 | 0 |
| `fp:1:-7:0`, every operand (p = min_precision, the quick tier's exponent range) | 578 | 578 | 0 |
| `fp:3:-7:0`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 082 | 10 082 | 0 |
| `fp:2:-7:0`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 450 | 2 450 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 563 637, extreme 281 817, negative 281 818, neighbor 563 636, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 818; `binary32`: equal 563 637, extreme 281 817, negative 281 818, neighbor 563 636, overflow 281 818, pow2 281 818, underflow 281 818, uniform 281 820, zero 281 818.

### `norm_step_2`

Claims: `maximum(r) of m, abs(x[0])`.

| Run | Cases | Judged | Failed |
|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 |
| `fp:3:-8:4`, every operand (p = min_precision + 2, another exponent range) | 777 666 | 777 666 | 0 |
| `fp:3:-6:2`, every operand (p = min_precision + 2, the quick tier's format) | 214 722 | 214 722 | 0 |
| `fp:1:-6:2`, every operand (p = min_precision, the quick tier's exponent range) | 4 978 | 4 978 | 0 |
| `fp:4:-6:2`, every operand (quick tier + 1 bit) | 1 276 770 | 1 276 770 | 0 |
| `fp:2:-6:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 33 930 | 33 930 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: equal 554 547, extreme 277 271, negative 277 273, neighbor 554 546, overflow 277 272, pow2 277 272, underflow 277 273, uniform 277 274, zero 277 272; `binary32`: equal 554 547, extreme 277 271, negative 277 273, neighbor 554 546, overflow 277 272, pow2 277 272, underflow 277 273, uniform 277 274, zero 277 272.

### `norm_upper_1`

Claims: `upper(r) over max, steps=0`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest steps above RU(V) (claim 0) |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0 |
| `fp:2:-2:1`, every operand (another format, every array up to 4 elements) | 969 959 | 969 959 | 0 | 0 |
| `fp:4:-4:-1`, every operand (another format, every array up to 3 elements) | 1 667 635 | 1 667 635 | 0 | 0 |
| `fp:3:-3:0`, every operand (the full tier's format, every array up to 3 elements) | 225 835 | 225 835 | 0 | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: nonfinite 332, one 168, position 333, ties 335, top 333, underflow 167, wide 167, zeros 165; `binary32`: nonfinite 332, one 168, position 333, ties 335, top 333, underflow 167, wide 167, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest steps above RU(V) (claim 0), compiled 0 (clang18-fixup-call/cxx, linux-x86-64):
  norm_upper_1 binary64 lanes:4 0 #nonfinite:119 -> 0x0p+0 1
largest steps above RU(V) (claim 0), interpreter 0 (fp:2:-2:1, every operand):
  norm_upper_1 fp:2:-2:1 seq 0 #exhaustive:0 -> 0x0p+0 1
```

### `norm_upper_2`

Claims: `upper(r) over max, steps=1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest steps above RU(V) (claim 1) |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1 |
| `fp:3:-5:2`, every operand (another format, every array up to 2 elements) | 1 945 379 | 1 945 379 | 0 | 1 |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 2 elements) | 363 379 | 363 379 | 0 | 1 |
| `fp:3:-3:0`, every operand (another format, every array up to 2 elements) | 29 891 | 29 891 | 0 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: nonfinite 308, one 155, position 308, tail 152, ties 308, top 308, underflow 153, wide 155, zeros 153; `binary32`: nonfinite 308, one 155, position 308, tail 152, ties 308, top 308, underflow 153, wide 155, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
largest steps above RU(V) (claim 1), compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  norm_upper_2 binary64 seq 0 #nonfinite:17 -> 0x0.0000000000001p-1022 1
largest steps above RU(V) (claim 1), interpreter 1 (fp:3:-5:2, every operand):
  norm_upper_2 fp:3:-5:2 seq 0 #exhaustive:0 -> 0x1p-5 1
```

### `radd`

Claims: `upper(r) gaps=3/2`.

| Run | Cases | Judged | Failed | largest excess, gaps (claim 3/2) |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.5 (the claim) |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.5 (the claim) |
| `fp:8:-16:3`, every operand (another number of exponents) | 7 236 100 | 7 236 100 | 0 | 1.5 (the claim) |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 2 775 556 | 2 775 556 | 0 | 1.5 (the claim) |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 695 556 | 695 556 | 0 | 1.5 (the claim) |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 2 916 | 2 916 | 0 | 1.5 (the claim) |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 784 | 784 | 0 | 1.25 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: close 238 462, extreme 238 461, nonfinite 476 922, nonneg 476 923, overflow 238 461, pow2 238 461, tie 476 924, underflow 238 461, uniform 238 464, zero 238 461; `binary32`: close 238 462, extreme 238 461, nonfinite 476 922, nonneg 476 923, overflow 238 461, pow2 238 461, tie 476 924, underflow 238 461, uniform 238 464, zero 238 461.

Where the extremes are attained (the line as the oracle reports it):

```
largest excess, gaps (claim 3/2), compiled 1.5 (clang18-fixup-call/cxx, linux-x86-64):
  radd binary64 0x1.35e1a7c6d393ep-63 0x1.5ba49efcfec91p-63 #close:4072 -> 0x1.48c32361e92e9p-62
largest excess, gaps (claim 3/2), interpreter 1.5 (fp:8:-16:3, every operand):
  radd fp:8:-16:3 0x1p-16 0x1.02p-8 #exhaustive:2947 -> 0x1.06p-8
```

### `radd_entry`

Claims: `upper(r) gaps=3/2`.

| Run | Cases | Judged | Failed | largest excess, gaps (claim 3/2) |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.5 (the claim) |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.5 (the claim) |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 2 775 556 | 2 775 556 | 0 | 1.5 (the claim) |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 784 | 784 | 0 | 1.25 |
| `fp:8:-16:3`, every operand (another number of exponents) | 7 236 100 | 7 236 100 | 0 | 1.5 (the claim) |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 695 556 | 695 556 | 0 | 1.5 (the claim) |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 2 916 | 2 916 | 0 | 1.5 (the claim) |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: close 238 462, extreme 238 461, nonfinite 476 922, nonneg 476 923, overflow 238 461, pow2 238 461, tie 476 924, underflow 238 461, uniform 238 464, zero 238 461; `binary32`: close 238 462, extreme 238 461, nonfinite 476 922, nonneg 476 923, overflow 238 461, pow2 238 461, tie 476 924, underflow 238 461, uniform 238 464, zero 238 461.

Where the extremes are attained (the line as the oracle reports it):

```
largest excess, gaps (claim 3/2), compiled 1.5 (clang18-fixup-call/cxx, linux-x86-64):
  radd_entry binary64 0x1.2de42f32a6b16p-741 0x1.06497099876b4p-739 #close:81 -> 0x1.51c27c663117bp-739
largest excess, gaps (claim 3/2), interpreter 1.5 (fp:8:-12:-1, every operand):
  radd_entry fp:8:-12:-1 0x1p-12 0x1.02p-4 #exhaustive:1923 -> 0x1.06p-4
```

### `rmul`

Claims: `upper(r) gaps=3/2`.

| Run | Cases | Judged | Failed | largest excess, gaps (claim 3/2) |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.5 (the claim) |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | 1.5 (the claim) |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 695 556 | 695 556 | 0 | 1.5 (the claim) |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 2 916 | 2 916 | 0 | 1.5 (the claim) |
| `fp:2:-6:5`, every operand (p = min_precision, the quick tier's number of exponents) | 784 | 784 | 0 | 1.5 (the claim) |
| `fp:8:-16:3`, every operand (another number of exponents) | 7 236 100 | 7 236 100 | 0 | 1.5 (the claim) |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 2 775 556 | 2 775 556 | 0 | 1.5 (the claim) |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: close 206 668, extreme 206 666, nonfinite 413 332, nonneg 413 334, overflow 206 666, pow2 206 666, tie 413 336, underflow 206 666, uniform 206 668, zero 206 666, zeroinf 413 332; `binary32`: close 206 668, extreme 206 666, nonfinite 413 332, nonneg 413 334, overflow 206 666, pow2 206 666, tie 413 336, underflow 206 666, uniform 206 668, zero 206 666, zeroinf 413 332.

Where the extremes are attained (the line as the oracle reports it):

```
largest excess, gaps (claim 3/2), compiled 1.5 (clang18-fixup-call/cxx, linux-x86-64):
  rmul binary64 0x1.cp-1070 0x1.c6be648583824p+257 #close:245268 -> 0x1.8de697f4d3121p-812
largest excess, gaps (claim 3/2), interpreter 1.5 (fp:7:-11:0, every operand):
  rmul fp:7:-11:0 0x1p-11 0x1.8p+0 #exhaustive:1250 -> 0x1.8p-10
```

### `scale_1`

Claims: `entries(z) of the step scale_step_1 on x, a`; `finite_or_nan(z) flag finite`; `entries(z), step scale_step_1: rounded(z) nearest`; `entries(z), step scale_step_1: error(z) form R, c=1/(1+u), k=1, t=1/2`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 8 084 148; inexact 13 344 426; tie 924 258 | 1 - ε, ε < 10⁻⁹ | 1.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 8 013 222; inexact 13 930 098; tie 1 101 564 | 0.9999998808 | 0.9999998212 |
| `fp:2:-2:1`, every operand (another format, every array up to 3 elements) | 724 570 | 724 570 | 0 | exact 1 000 125; inexact 231 140; tie 106 680 | 0.833333 | 0.444444 |
| `fp:3:-3:0`, every operand (the full tier's format, every array up to 2 elements) | 149 982 | 149 982 | 0 | exact 100 217; inexact 68 276; tie 39 884 | 0.9 | - |
| `fp:5:-7:0`, every operand (another format, every array up to 1 elements) | 84 390 | 84 390 | 0 | exact 11 173; inexact 51 900; tie 6 076 | 0.992248 | 0.969697 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141; `binary32`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  scale_step_1 binary64 -0x1.fffffffffffffp+1001 0x1.0000000000001p+18 #scale_1:tight:99:element:2135 -> -0x1p+1020
largest error / bound, interpreter 0.992248 (fp:5:-7:0, every operand):
  scale_step_1 fp:5:-7:0 -0x1.8p+4 -0x1.6p-1 #scale_1:exhaustive:2409:element:0 -> 0x1p+4
```

### `scale_2`

Claims: `entries(z) of the step scale_step_2 on x, a`; `finite_or_nan(z) flag finite`; `entries(z), step scale_step_2: normalized(z)`; `entries(z), step scale_step_2: error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.992336 | 1.98467 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.995750 | 1.82156 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 24 766 | 24 766 | 0 | 0.759322 | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 5 166 | 5 166 | 0 | 0.759322 | - |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 149 314 | 149 314 | 0 | 0.470588 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.995750 (clang18/avx2, linux-x86-64):
  scale_step_2 binary32 -0x1.7461dcp+0 -0x1.e0fd9p-27 -0x1.5f48ep-117 #scale_2:underflow:620:element:2755 -> 0x1.fefc2ep-117 0x1.4cp-143
largest error / bound, interpreter 0.759322 (fp:3:-4:1, every operand):
  scale_step_2 fp:3:-4:1 -0x1.8p+0 -0x1p-3 -0x1.8p-3 #scale_2:exhaustive:10812:element:0 -> 0x1p-2 0x0p+0
```

### `scale_2_entry`

Claims: `entries(z) of the step scale_entry_step_2 on x, a`; `finite_or_nan(z) flag finite`; `entries(z), step scale_entry_step_2: normalized(z)`; `entries(z), step scale_entry_step_2: error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.996654 | 1.98467 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.998018 | 1.79610 |
| `fp:3:-4:1`, every operand (another format, every array up to 1 elements) | 24 766 | 24 766 | 0 | 0.759322 | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 5 166 | 5 166 | 0 | 0.759322 | - |
| `fp:2:-2:1`, every operand (the full tier's format, every array up to 2 elements) | 149 314 | 149 314 | 0 | 0.470588 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.998018 (msvc/avx2, windows-x64):
  scale_entry_step_2 binary32 0x1.d6884p+15 -0x1.f9f6dap-10 0x1.c15p-135 #scale_2_entry:underflow:320:element:546 -> 0x1.9cec000000000p-119 0x1.1000000000000p-144
largest error / bound, interpreter 0.759322 (fp:3:-4:1, every operand):
  scale_entry_step_2 fp:3:-4:1 -0x1.8p+0 -0x1p-3 -0x1.8p-3 #scale_2_entry:exhaustive:10812:element:0 -> 0x1p-2 0x0p+0
```

### `scale_entry_step_2`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 96 516 720 | 0 | 1 - ε, ε < 10⁻⁹ | 1.93585 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 96 421 788 | 0 | 0.9999998510 | 1.98162 |
| `fp:3:-8:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 42 273 | 41 241 | 0 | 0.794235 | - |
| `fp:6:-8:-2`, every operand (quick tier + 2 bits) | 4 152 897 | 2 754 581 | 0 | 0.972718 | - |
| `fp:5:-4:2`, every operand (another exponent range) | 1 027 905 | 304 717 | 0 | 0.907265 | - |
| `fp:5:-8:-2`, every operand (quick tier + 1 bit) | 1 027 905 | 799 453 | 0 | 0.951325 | - |
| `fp:2:-8:-2`, every operand (p = min_precision, the quick tier's exponent range) | 7 285 | 7 285 | 0 | 0.628272 | 0.410256 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499; `binary32`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  scale_entry_step_2 binary64 -0x1.8p+0 -0x1p-53 -0x1.ffffffffffffep-1023 #extreme:923586 -> 0x1.7fffffffffffep-1022 0x0p+0
largest error / bound, interpreter 0.972718 (fp:6:-8:-2, every operand):
  scale_entry_step_2 fp:6:-8:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-5 #exhaustive:1480613 -> 0x1.4p-3 0x0p+0
```

### `scale_step_1`

Claims: `rounded(z) nearest`; `error(z) form R, c=1/(1+u), k=1, t=1/2`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 82 983 672 | 0 | exact 29 932 848; inexact 52 985 286; tie 65 538 | 1 - ε, ε < 10⁻⁹ | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 83 600 208 | 0 | exact 30 134 844; inexact 53 243 730; tie 221 634 | 0.9999999404 | 0.9999998212 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | exact 114 689; inexact 3 989 676; tie 75 928 | 0.999939 | 0.992248 |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | exact 118 385; inexact 2 267 576; tie 74 352 | 0.999512 | 0.992248 |
| `fp:3:-12:-1`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 481 | 0 | exact 2 921; inexact 6 128; tie 1 432 | 0.999512 | 0.888889 |
| `fp:1:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 625 | 0 | exact 313; inexact 264; tie 48 | 0.75 | 0 |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | exact 145 697; inexact 1 967 764; tie 84 024 | 0.999756 | 0.992248 |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | exact 49 985; inexact 559 608; tie 27 888 | 0.999512 | 0.984615 |
| `fp:2:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 597 | 0 | exact 1 089; inexact 1 364; tie 144 | 0.833333 | 0.444444 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  scale_step_1 binary64 -0x1p-934 0x1p-141 #pow2:19554 -> -0x0p+0
largest error / bound, interpreter 0.999939 (fp:7:-20:-6, every operand):
  scale_step_1 fp:7:-20:-6 -0x1.8p+0 -0x1.58p-1 #exhaustive:63562 -> 0x1p+0
```

### `scale_step_2`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 96 503 688 | 0 | 1 - ε, ε < 10⁻⁹ | 1.97681 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 96 415 236 | 0 | 0.9999998212 | 1.91164 |
| `fp:5:-4:2`, every operand (another exponent range) | 1 027 905 | 304 717 | 0 | 0.907265 | - |
| `fp:5:-8:-2`, every operand (quick tier + 1 bit) | 1 027 905 | 799 453 | 0 | 0.951325 | - |
| `fp:2:-8:-2`, every operand (p = min_precision, the quick tier's exponent range) | 7 285 | 7 285 | 0 | 0.628272 | 0.410256 |
| `fp:6:-8:-2`, every operand (quick tier + 2 bits) | 4 152 897 | 2 754 581 | 0 | 0.972718 | - |
| `fp:3:-8:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 42 273 | 41 241 | 0 | 0.794235 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499; `binary32`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  scale_step_2 binary64 0x1.8p+0 0x1.fffffffffffffp-54 0x1.0000000000001p-1022 #extreme:2266206 -> 0x1.8000000000003p-1022 0x0p+0
largest error / bound, interpreter 0.972718 (fp:6:-8:-2, every operand):
  scale_step_2 fp:6:-8:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-5 #exhaustive:1480613 -> 0x1.4p-3 0x0p+0
```

### `split`

Claims: `error(r) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 91 605 546 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 89 555 598 | 0 | 0 (exact) | 0 |
| `fp:13:-60:40`, every operand (another exponent range) | 835 583 | 778 111 | 0 | 0 (exact) | 0 |
| `fp:13:-30:10`, every operand (quick tier + 2 bits) | 344 063 | 286 591 | 0 | 0 (exact) | 0 |
| `fp:12:-30:10`, every operand (quick tier + 1 bit) | 172 031 | 147 329 | 0 | 0 (exact) | 0 |
| `fp:5:-30:10`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 343 | 1 239 | 0 | 0 (exact) | 0 |
| `fp:4:-30:10`, every operand (p = min_precision, the quick tier's exponent range) | 671 | 633 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332; `binary32`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332.

### `sub_1`

Claims: `entries(z) of the step sub_1_1 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step sub_1_1: rounded(s) nearest`; `entries(z), step sub_1_1: error(s) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 5 823 894; inexact 10 855 974; tie 5 416 044 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 6 627 858; inexact 11 373 156; tie 5 839 440 | 1 (the claim) | 0.9999999404 |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 468 997 | 468 997 | 0 | exact 350 597; inexact 162 708; tie 131 716 | 1 (the claim) | 0.8 |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 77 029 | 77 029 | 0 | exact 66 725; tie 9 420 | 1 (the claim) | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 765 | 1 765 | 0 | exact 745; inexact 360; tie 296 | 1 (the claim) | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141; `binary32`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  sub_1_1 binary64 0x1p+110 -0x1p+57 #sub_1:exact:192:element:1327 -> 0x1p+110
largest error / bound, interpreter 1 (fp:2:-2:1, every operand):
  sub_1_1 fp:2:-2:1 -0x1.8p+2 -0x1p+0 #sub_1:exhaustive:6:element:0 -> -0x1p+2
```

### `sub_1_1`

Claims: `rounded(s) nearest`; `error(s) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 97 203 456 | 0 | exact 29 574 342; inexact 66 469 284; tie 1 159 830 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 97 210 782 | 0 | exact 32 083 128; inexact 63 533 232; tie 1 594 422 | 1 (the claim) | 0.9999999404 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | exact 147 265; inexact 457 536; tie 77 632 | 1 (the claim) | 0.984615 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 573 | 0 | exact 565; inexact 1 716; tie 292 | 1 (the claim) | 0.8 |
| `fp:1:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 619 | 0 | exact 139; inexact 400; tie 80 | 1 (the claim) | 0.666667 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | exact 835 201; inexact 3 981 696; tie 454 272 | 1 (the claim) | 0.992248 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | exact 589 441; inexact 1 832 576; tie 310 912 | 1 (the claim) | 0.992248 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 489 | 0 | exact 2 281; inexact 7 016; tie 1 192 | 1 (the claim) | 0.888889 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  sub_1_1 binary64 0x1.0000000000001p-1022 -0x1p-1022 #extreme:622 -> 0x1p-1021
largest error / bound, interpreter 1 (fp:6:-7:4, every operand):
  sub_1_1 fp:6:-7:4 -0x1.f8p+9 -0x1.e8p+8 #exhaustive:34 -> -0x1p+9
```

### `sub_1_2`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 053 894 | 0 | 0.568171 | 1.00802 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 053 786 | 0 | 0.666665 | 1.33333 |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666665 (msvc-fixup-call/cxx, windows-x64):
  sub_1_2 binary32 -0x1.000002p-23 -0x1.00002p-21 0x1.eba73ep-46 #pow2:15389 -> 0x1.80003e0000000p-22 -0x1.d74e800000000p-47
largest error / bound, interpreter 0.939450 (fp:5:-4:2, every operand):
  sub_1_2 fp:5:-4:2 -0x1.fp+4 -0x1p+6 -0x1.1p+0 #exhaustive:129966 -> 0x1.1p+5 0x0p+0
```

### `sub_1_2_full`

Claims: `extends(w) F1-F5, core sub_1_2, lead sub, finite when |a| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core sub_1_2: normalized(z)`; `F2, core sub_1_2: error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.744470 | 1.48894 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.666660 | 1.33332 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.939450 | - |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0 | - |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.780488 | - |
| `fp:4:-9:4`, every operand (p = min_precision + 1, another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.882759 | 1.76552 |
| `fp:4:-5:0`, every operand (p = min_precision + 1, the quick tier's format) | 113 316 | 113 316 | 0 | 0.882759 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888; `binary32`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.744470 (msvc-fixup-call/cxx, windows-x64):
  sub_1_2_full binary64 0x1.ad3d7dd355421p-201 0x1.173e903ba6afdp-199 -0x1.dc9a51cf40f5dp-253 #close:57807 -> -0x1.57de618da2be9p-200 0x1.b934a39e81eb8p-254
largest error / bound, interpreter 0.939450 (fp:5:-8:1, every operand):
  sub_1_2_full fp:5:-8:1 -0x1.fp+3 -0x1p+5 -0x1.1p-1 #exhaustive:521646 -> 0x1.1p+4 0x0p+0
```

### `sub_1_entry`

Claims: `entries(z) of the step sub_entry_step_1 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step sub_entry_step_1: rounded(z) nearest`; `entries(z), step sub_entry_step_1: error(z) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 6 755 046; inexact 11 933 586; tie 5 227 068 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | exact 6 735 504; inexact 10 562 532; tie 5 873 250 | 1 (the claim) | 0.9999999404 |
| `fp:2:-1:0`, every operand (the full tier's format, every array up to 2 elements) | 77 029 | 77 029 | 0 | exact 66 725; tie 9 420 | 1 (the claim) | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 1 765 | 1 765 | 0 | exact 745; inexact 360; tie 296 | 1 (the claim) | - |
| `fp:2:-2:1`, every operand (another format, every array up to 2 elements) | 468 997 | 468 997 | 0 | exact 350 597; inexact 162 708; tie 131 716 | 1 (the claim) | 0.8 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141; `binary32`: cancel 287, exact 141, nonfinite 143, one 144, overflow 285, tie 144, tight 428, underflow 144, wide 143, zeros 141.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  sub_entry_step_1 binary64 0x1p-66 -0x1p-119 #sub_1_entry:exact:178:element:241 -> 0x1p-66
largest error / bound, interpreter 1 (fp:2:-1:0, every operand (the full tier's format, every array up to 2 elements)):
  sub_entry_step_1 fp:2:-1:0 -0x1.8p+1 -0x1p-1 #sub_1_entry:exhaustive:5:element:0 -> -0x1p+1
```

### `sub_2`

Claims: `entries(z) of the step sub_2_2 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step sub_2_2: normalized(z)`; `entries(z), step sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1 - ε, ε < 10⁻⁹ | 3.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.9999995430 | 3.00000 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 988 037 | 988 037 | 0 | 0.453901 | - |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 1 elements) | 181 477 | 181 477 | 0 | 0.273504 | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 14 885 | 14 885 | 0 | 0.260163 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  sub_2_2 binary64 -0x1p+62 -0x1.fffffffffffffp+8 -0x1.fffffffffffffp+60 -0x1.ffffffffffffep-46 #sub_2:tight:7:element:2 -> -0x1.0000000000002p+61 0x1p+8
largest error / bound, interpreter 0.453901 (fp:4:-5:0, every operand):
  sub_2_2 fp:4:-5:0 -0x1.ep+3 0x1.ep-2 -0x1.6p+2 -0x1.cp-3 #sub_2:exhaustive:30133:element:0 -> -0x1.2p+3 0x1p-2
```

### `sub_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 058 772 | 0 | 0.540731 | 1.08146 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 056 882 | 0 | 0.665474 | 1.33095 |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.665474 (msvc-fixup-call/cxx, windows-x64):
  sub_2_1 binary32 -0x1.2a1cf4p+49 0x1.26867ap+24 -0x1.a71352p+47 #close:66564 -> -0x1.80b03e0000000p+48 0x1.3433c00000000p+21
largest error / bound, interpreter 0.939450 (fp:5:-4:2, every operand):
  sub_2_1 fp:5:-4:2 -0x1p+6 -0x1.1p+0 -0x1.fp+4 #exhaustive:248402 -> -0x1.1p+5 0x0p+0
```

### `sub_2_1_full`

Claims: `extends(w) F1-F5, core sub_2_1, lead sub, finite when |x| <= 2^(qmax+p-2) and |a| <= 2^(qmax+p-2)`; `F2, core sub_2_1: normalized(z)`; `F2, core sub_2_1: error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.502159 | 1.00432 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.722508 | 1.44502 |
| `fp:5:-8:1`, every operand (another number of exponents) | 5 744 004 | 5 744 004 | 0 | 0.939450 | - |
| `fp:6:-7:-2`, every operand (quick tier + 2 bits) | 1 829 700 | 1 829 700 | 0 | 0 | - |
| `fp:4:-9:4`, every operand (p = min_precision + 1, another number of exponents) | 3 431 076 | 3 431 076 | 0 | 0.882759 | 1.76552 |
| `fp:5:-6:-1`, every operand (quick tier + 1 bit) | 456 068 | 456 068 | 0 | 0 | - |
| `fp:4:-5:0`, every operand (p = min_precision + 1, the quick tier's format) | 113 316 | 113 316 | 0 | 0.882759 | - |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's number of exponents) | 24 708 | 24 708 | 0 | 0.780488 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888; `binary32`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.722508 (clang-fixup-inline/cxx, macos-arm64):
  sub_2_1_full binary32 0x1.1cf00ap-43 -0x1.cc0cd6p-68 0x1.af1b8ap-45 #close:3802 -> 0x1.62524ep-44 -0x1.9819bp-69
largest error / bound, interpreter 0.939450 (fp:5:-8:1, every operand):
  sub_2_1_full fp:5:-8:1 -0x1p+5 -0x1.1p-1 -0x1.fp+3 #exhaustive:854588 -> -0x1.1p+4 0x0p+0
```

### `sub_2_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 058 718 | 0 | 0.528585 | 1.58576 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 054 488 | 0 | 0.582452 | 1.74736 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.582452 (clang18-fixup-call/cxx, linux-x86-64):
  sub_2_2 binary32 -0x1.20a02p+127 0x1.c2a382p+102 -0x1.fffffap+125 0x1.9d51cep+77 #overflow:9742 -> -0x1.414042p+126 0x1.8546fep+101
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  sub_2_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 -0x1.9p+5 -0x1.cp-1 #exhaustive:127545 -> -0x1.1p+6 0x1p+0
```

### `sub_2_2_full`

Claims: `extends(w) F1-F5, core sub_2_2, lead sub, finite when |x| <= 2^(qmax+p-2) and |y| <= 2^(qmax+p-2)`; `F2, core sub_2_2: normalized(z)`; `F2, core sub_2_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.666667 | 2.00000 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 200 000 | 0 | 0.666666 | 2.00000 |
| `fp:4:-6:1`, every operand (p = min_precision + 1, another number of exponents) | 7 584 516 | 7 584 516 | 0 | 0.536013 | - |
| `fp:5:-6:-1`, every operand (quick tier + 2 bits) | 4 072 324 | 4 072 324 | 0 | 0.556176 | - |
| `fp:3:-6:3`, every operand (p = min_precision, another number of exponents) | 3 247 204 | 3 247 204 | 0 | 0.360255 | 2.16153 |
| `fp:3:-4:1`, every operand (p = min_precision, the quick tier's format) | 181 476 | 181 476 | 0 | 0.273504 | - |
| `fp:4:-5:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 988 036 | 988 036 | 0 | 0.453901 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888; `binary32`: cancel 27 780, close 41 670, edge 27 774, extreme 13 890, nonfinite 27 776, overflow 13 888, pow2 13 890, threshold 27 774, underflow 27 780, uniform 13 890, zero 13 888.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666667 (clang18-fixup-call/cxx, linux-x86-64):
  sub_2_2_full binary64 0x1.fffffffffffffp+1023 0x1.fffffffffffffp+969 0x1.ffffffffffffdp+1022 -0x1.173a5bee1d996p+966 #edge:22568 -> 0x1.0000000000001p+1023 0x1.173a5bee1d97ep+966
largest error / bound, interpreter 0.556176 (fp:5:-6:-1, every operand):
  sub_2_2_full fp:5:-6:-1 -0x1.ep+3 0x1p-2 -0x1.9p+2 -0x1.cp-4 #exhaustive:127734 -> -0x1.1p+3 0x1p-3
```

### `sub_2_entry`

Claims: `entries(z) of the step sub_entry_step_2 on x, y`; `finite_or_nan(z) flag finite`; `entries(z), step sub_entry_step_2: normalized(z)`; `entries(z), step sub_entry_step_2: error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1 - ε, ε < 10⁻⁹ | 3.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.9999995430 | 3.00000 |
| `fp:4:-5:0`, every operand (another format, every array up to 1 elements) | 988 037 | 988 037 | 0 | 0.453901 | - |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 1 elements) | 181 477 | 181 477 | 0 | 0.273504 | - |
| `fp:3:-3:0`, every operand (another format, every array up to 1 elements) | 14 885 | 14 885 | 0 | 0.260163 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132; `binary32`: cancel 268, exact 132, nonfinite 133, one 135, overflow 267, tail 132, tie 135, tight 400, underflow 133, wide 133, zeros 132.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  sub_entry_step_2 binary64 -0x1p+17 -0x1.fffffffffffffp-37 -0x1.fffffffffffffp+15 -0x1.ffffffffffffep-91 #sub_2_entry:tight:1:element:0 -> -0x1.0000000000002p+16 0x1p-37
largest error / bound, interpreter 0.453901 (fp:4:-5:0, every operand):
  sub_entry_step_2 fp:4:-5:0 -0x1.ep+3 0x1.ep-2 -0x1.6p+2 -0x1.cp-3 #sub_2_entry:exhaustive:30133:element:0 -> -0x1.2p+3 0x1p-2
```

### `sub_down_1`

Claims: `rounded(r) down`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 399 872; inexact, as RN 22 121 334; differs from RN 26 577 360; a NaN operand 4 478 778; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 021 134; overflow: value above Omega 8 932 248; overflow: value below -Omega 8 901 522; rounds to -inf 8 901 522; value NaN from operands that are not NaN 636 102 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 072 676; inexact, as RN 21 692 574; differs from RN 26 288 892; a NaN operand 4 477 212; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 022 700; overflow: value above Omega 8 928 090; overflow: value below -Omega 8 945 946; rounds to -inf 8 945 946; value NaN from operands that are not NaN 636 930 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to -inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to -inf 4 288; value NaN from operands that are not NaN 2 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to -inf 36; value NaN from operands that are not NaN 2 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to -inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to -inf 100; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `sub_down_2_2`

Claims: `normalized(l)`; `outward(l) below, exact when (x-y = 0)`.

| Run | Cases | Judged | Failed | largest |output - value| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 992 046 | 0 | 0.794263 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 988 950 | 0 | 0.663346 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 689 555 | 0 | 0.447941 |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 129 416 | 0 | 0.384391 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 077 026 | 0 | 0.444810 |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 644 866 | 0 | 0.389454 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 2 880 089 | 0 | 0.474531 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest |output - value| / allowance, compiled 0.794263 (clang18-fixup-call/cxx, linux-x86-64):
  sub_down_2_2 binary64 0x1p+1023 0x1.fffffffffffffp+969 0x1.fffffffffffffp+1021 0x1.cba4c92956521p+942 #overflow:21724 -> 0x1.0000000000001p+1022 0x1.ffffff8d16cd3p+968
largest |output - value| / allowance, interpreter 0.474531 (fp:5:-3:2, every operand):
  sub_down_2_2 fp:5:-3:2 -0x1.fp+4 0x0p+0 -0x1.fp+6 -0x1.ep+0 #exhaustive:1529385 -> 0x1.4p+6 -0x1p+1
```

### `sub_down_entry`

Claims: `rounded(r) down`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 400 844; inexact, as RN 22 098 438; differs from RN 26 581 392; a NaN operand 4 478 526; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 021 386; overflow: value above Omega 8 902 386; overflow: value below -Omega 8 919 414; rounds to -inf 8 919 414; value NaN from operands that are not NaN 643 050 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 094 762; inexact, as RN 21 672 072; differs from RN 26 310 762; a NaN operand 4 481 514; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 018 398; overflow: value above Omega 8 927 136; overflow: value below -Omega 8 922 492; rounds to -inf 8 922 492; value NaN from operands that are not NaN 633 312 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to -inf 4 288; value NaN from operands that are not NaN 2 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to -inf 36; value NaN from operands that are not NaN 2 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to -inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to -inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to -inf 100; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `sub_entry_step_1`

Claims: `rounded(z) nearest`; `error(z) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 97 237 800 | 0 | exact 29 616 228; inexact 66 454 650; tie 1 166 922 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 97 214 940 | 0 | exact 32 050 980; inexact 63 571 626; tie 1 592 334 | 1 (the claim) | 0.9999999404 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | exact 835 201; inexact 3 981 696; tie 454 272 | 1 (the claim) | 0.992248 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | exact 147 265; inexact 457 536; tie 77 632 | 1 (the claim) | 0.984615 |
| `fp:1:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 619 | 0 | exact 139; inexact 400; tie 80 | 1 (the claim) | 0.666667 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | exact 589 441; inexact 1 832 576; tie 310 912 | 1 (the claim) | 0.992248 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 489 | 0 | exact 2 281; inexact 7 016; tie 1 192 | 1 (the claim) | 0.888889 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 573 | 0 | exact 565; inexact 1 716; tie 292 | 1 (the claim) | 0.8 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  sub_entry_step_1 binary64 -0x1.0000000000001p-1022 0x1p-1022 #extreme:30 -> -0x1p-1021
largest error / bound, interpreter 1 (fp:7:-14:2, every operand):
  sub_entry_step_1 fp:7:-14:2 -0x1.fcp+8 -0x1.f4p+7 #exhaustive:66 -> -0x1p+8
```

### `sub_entry_step_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 98 814 924 | 0 | 0.620576 | 1.86173 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 98 778 618 | 0 | 0.787615 | 2.36285 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499; `binary32`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.787615 (clang18-fixup-call/cxx, linux-x86-64):
  sub_entry_step_2 binary32 0x1.f41506p-30 -0x1.b0950ep-55 0x1.04735p-28 0x1.2fd832p-53 #close:781672 -> -0x1.0edc1ep-29 -0x1.37fafp-54
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  sub_entry_step_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 -0x1.9p+5 -0x1.cp-1 #exhaustive:127545 -> -0x1.1p+6 0x1p+0
```

### `sub_up_1`

Claims: `rounded(r) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 393 842; inexact, as RN 22 111 344; differs from RN 26 584 470; a NaN operand 4 481 964; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 017 948; overflow: value above Omega 8 910 432; overflow: value below -Omega 8 918 442; rounds to inf 8 910 432; value NaN from operands that are not NaN 636 120 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 089 452; inexact, as RN 21 699 846; differs from RN 26 289 900; a NaN operand 4 476 312; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 023 600; overflow: value above Omega 8 920 890; overflow: value below -Omega 8 911 818; rounds to inf 8 920 890; value NaN from operands that are not NaN 641 142 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to inf 4 288; value NaN from operands that are not NaN 2 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to inf 36; value NaN from operands that are not NaN 2 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to inf 100; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `sub_up_2_2`

Claims: `normalized(h)`; `outward(h) above, exact when (x-y = 0)`.

| Run | Cases | Judged | Failed | largest |output - value| / allowance |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 991 326 | 0 | 0.672998 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 988 302 | 0 | 0.687499 |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 644 866 | 0 | 0.389454 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 077 026 | 0 | 0.444810 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 2 880 089 | 0 | 0.474531 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 689 555 | 0 | 0.447941 |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 129 416 | 0 | 0.384391 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250; `binary32`: apart 31 250, cancel 31 250, close 31 250, extreme 15 625, overflow 15 625, pow2 15 625, tiny 31 250, underflow 15 625, uniform 15 625, zero 15 625, zerosum 31 250.

Where the extremes are attained (the line as the oracle reports it):

```
largest |output - value| / allowance, compiled 0.687499 (clang-fixup-inline/cxx, macos-arm64):
  sub_up_2_2 binary32 0x1p+127 0x1.fffffep+102 0x1.fffffep+125 0x1.fffffep+100 #overflow:9948 -> 0x1.000002p+126 0x1.000008p+101
largest |output - value| / allowance, interpreter 0.474531 (fp:5:-3:2, every operand):
  sub_up_2_2 fp:5:-3:2 -0x1.fp+6 -0x1.ep+0 -0x1.fp+4 0x0p+0 #exhaustive:759 -> -0x1.4p+6 0x1p+1
```

### `sub_up_entry`

Claims: `rounded(r) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 34 402 716; inexact, as RN 22 104 576; differs from RN 26 601 696; a NaN operand 4 471 146; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 028 766; overflow: value above Omega 8 891 100; overflow: value below -Omega 8 927 586; rounds to inf 8 891 100; value NaN from operands that are not NaN 639 306 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 103 500 000 | 0 | exact 35 063 982; inexact, as RN 21 694 248; differs from RN 26 312 580; a NaN operand 4 469 904; a non-finite operand 11 499 912; an infinite operand, no NaN operand 7 030 008; overflow: value above Omega 8 929 278; overflow: value below -Omega 8 937 450; rounds to inf 8 929 278; value NaN from operands that are not NaN 637 560 |
| `fp:7:-13:2`, every operand (another number of exponents) | 4 743 684 | 4 743 684 | 0 | exact 786 049; inexact, as RN 1 955 968; differs from RN 1 970 880; a NaN operand 4 355; a non-finite operand 13 059; an infinite operand, no NaN operand 8 704; overflow: value above Omega 17 728; overflow: value below -Omega 17 728; rounds to inf 17 728; value NaN from operands that are not NaN 2 |
| `fp:7:-9:-2`, every operand (quick tier + 2 bits) | 1 331 716 | 1 331 716 | 0 | exact 392 833; inexact, as RN 449 664; differs from RN 465 600; a NaN operand 2 307; a non-finite operand 6 915; an infinite operand, no NaN operand 4 608; overflow: value above Omega 16 704; overflow: value below -Omega 16 704; rounds to inf 16 704; value NaN from operands that are not NaN 2 |
| `fp:3:-5:2`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 5 476 | 5 476 | 0 | exact 1 513; inexact, as RN 1 704; differs from RN 1 724; a NaN operand 147; a non-finite operand 435; an infinite operand, no NaN operand 288; overflow: value above Omega 100; overflow: value below -Omega 100; rounds to inf 100; value NaN from operands that are not NaN 2 |
| `fp:2:-4:3`, every operand (p = min_precision, the quick tier's number of exponents) | 1 444 | 1 444 | 0 | exact 373; inexact, as RN 412; differs from RN 404; a NaN operand 75; a non-finite operand 219; an infinite operand, no NaN operand 144; overflow: value above Omega 36; overflow: value below -Omega 36; rounds to inf 36; value NaN from operands that are not NaN 2 |
| `fp:6:-8:-1`, every operand (quick tier + 1 bit) | 334 084 | 334 084 | 0 | exact 98 113; inexact, as RN 112 192; differs from RN 116 032; a NaN operand 1 155; a non-finite operand 3 459; an infinite operand, no NaN operand 2 304; overflow: value above Omega 4 288; overflow: value below -Omega 4 288; rounds to inf 4 288; value NaN from operands that are not NaN 2 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221; `binary32`: apart 344 446, beyond 344 445, cancel 344 445, close 172 223, exact 172 223, extreme 172 221, nonfinite 344 442, omega 344 445, overflow 172 222, pow2 172 222, underflow 172 222, uniform 172 223, zero 172 221.

### `sum_1`

Claims: `fold_error(r) eps=u/(1+u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.00000 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.9999999404 | 0.9999999404 |
| `fp:4:-4:-1`, every operand (another format, every array up to 3 elements) | 1 667 635 | 1 667 635 | 0 | 1 | 1 |
| `fp:2:-2:1`, every operand (another format, every array up to 4 elements) | 969 959 | 969 959 | 0 | 1 | 1 |
| `fp:3:-3:0`, every operand (the full tier's format, every array up to 3 elements) | 225 835 | 225 835 | 0 | 1 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165; `binary32`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  sum_1 binary64 lanes:8 2 0x1p+720 0x1.fffffffffffffp+666 #tight:20 -> 0x1p+720 1
largest error / bound, order lanes, interpreter 1 (fp:4:-4:-1, every operand):
  sum_1 fp:4:-4:-1 lanes:2 2 -0x1p+2 -0x1p-2 #exhaustive:1302 -> -0x1p+2 1
largest error / bound, order sequential, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  sum_1 binary64 seq 2 -0x1p+129 -0x1.fffffffffffffp+75 #tight:326 -> -0x1p+129 1
largest error / bound, order sequential, interpreter 1 (fp:4:-4:-1, every operand):
  sum_1 fp:4:-4:-1 seq 2 -0x1p+2 -0x1p-2 #exhaustive:1301 -> -0x1p+2 1
```

### `sum_1_entry`

Claims: `fold_error(r) eps=u/(1+u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 1.00000 | 1.00000 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.9999999404 | 0.9999996722 |
| `fp:3:-3:0`, every operand (the full tier's format, every array up to 3 elements) | 225 835 | 225 835 | 0 | 1 | 1 |
| `fp:4:-4:-1`, every operand (another format, every array up to 3 elements) | 1 667 635 | 1 667 635 | 0 | 1 | 1 |
| `fp:2:-2:1`, every operand (another format, every array up to 4 elements) | 969 959 | 969 959 | 0 | 1 | 1 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165; `binary32`: cancel 335, nonfinite 165, one 168, overflow 167, pow2 165, sign 167, tight 333, underflow 167, wide 168, zeros 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  sum_1_entry binary64 lanes:5 2 0x1p-496 0x1.fffffffffffffp-550 #tight:122 -> 0x1p-496 1
largest error / bound, order lanes, interpreter 1 (fp:3:-3:0, every operand (the full tier's format, every array up to 3 elements)):
  sum_1_entry fp:3:-3:0 lanes:2 2 -0x1p+2 -0x1p-1 #exhaustive:326 -> -0x1p+2 1
largest error / bound, order sequential, compiled 1 - ε, ε < 10⁻⁹ (clang18-fixup-call/cxx, linux-x86-64):
  sum_1_entry binary64 seq 2 0x1p-320 0x1.fffffffffffffp-374 #tight:734 -> 0x1p-320 1
largest error / bound, order sequential, interpreter 1 (fp:3:-3:0, every operand (the full tier's format, every array up to 3 elements)):
  sum_1_entry fp:3:-3:0 seq 2 -0x1p+2 -0x1p-1 #exhaustive:325 -> -0x1p+2 1
```

### `sum_2`

Claims: `normalized(r)`; `fold_error(r) eps=3*u^2/(1-4*u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.333333 | 0.333333 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.333333 | 0.250000 |
| `fp:3:-5:2`, every operand (another format, every array up to 2 elements) | 1 945 379 | 1 945 379 | 0 | 0.211411 | 0.211411 |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 2 elements) | 363 379 | 363 379 | 0 | 0.193939 | 0.193939 |
| `fp:3:-3:0`, every operand (another format, every array up to 2 elements) | 29 891 | 29 891 | 0 | 0.187135 | 0.187135 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153; `binary32`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.333333 (clang18/avx2, linux-x86-64):
  sum_2 binary64 lanes:4 2 -0x1p+58 0x1.fffffffffffffp+56 -0x1.fffffffffffffp+4 0x1.ffffffffffffep-50 #tight:275 -> -0x1.0000000000002p+57 0x1p+4 1
largest error / bound, order lanes, interpreter 0.211411 (fp:3:-5:2, every operand):
  sum_2 fp:3:-5:2 lanes:2 2 -0x1p+4 -0x1.4p+1 0x1p+0 0x1.4p-3 #exhaustive:307480 -> -0x1p+4 -0x1p+0 1
largest error / bound, order sequential, compiled 0.333333 (msvc-fixup-call/cxx, windows-x64):
  sum_2 binary64 seq 2 0x1p+2 -0x1.fffffffffffffp+0 0x1.fffffffffffffp-52 -0x1.ffffffffffffep-106 #tight:411 -> 0x1.0000000000002p+1 -0x1.0000000000000p-52 1
largest error / bound, order sequential, interpreter 0.211411 (fp:3:-5:2, every operand):
  sum_2 fp:3:-5:2 seq 2 -0x1p+4 -0x1.4p+1 0x1p+0 0x1.4p-3 #exhaustive:307479 -> -0x1p+4 -0x1p+0 1
```

### `sum_2_entry`

Claims: `normalized(r)`; `fold_error(r) eps=3*u^2/(1-4*u), term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.333333 | 0.189732 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.333333 | 0.166667 |
| `fp:3:-5:2`, every operand (another format, every array up to 2 elements) | 1 945 379 | 1 945 379 | 0 | 0.211411 | 0.211411 |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 2 elements) | 363 379 | 363 379 | 0 | 0.193939 | 0.193939 |
| `fp:3:-3:0`, every operand (another format, every array up to 2 elements) | 29 891 | 29 891 | 0 | 0.187135 | 0.187135 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153; `binary32`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.333333 (clang18-fixup-call/cxx, linux-x86-64):
  sum_2_entry binary64 lanes:8 2 -0x1p+112 0x1.fffffffffffffp+110 -0x1.fffffffffffffp+58 0x1.ffffffffffffep+4 #tight:275 -> -0x1.0000000000002p+111 0x1p+58 1
largest error / bound, order lanes, interpreter 0.211411 (fp:3:-5:2, every operand):
  sum_2_entry fp:3:-5:2 lanes:2 2 -0x1p+4 -0x1.4p+1 0x1p+0 0x1.4p-3 #exhaustive:307480 -> -0x1p+4 -0x1p+0 1
largest error / bound, order sequential, compiled 0.189732 (msvc-fixup-call/cxx, windows-x64):
  sum_2_entry binary64 seq 3 0x1.8bad67cbd861fp+663 0x1.41a16737e7c64p+663 0x1.9fe580ad6b738p+663 -0x1.cd3c86bbcdec3p+602 0x1.87bf8d839cf65p+561 0x1.4998218025e21p-60 #sign:174 -> 0x1.1b4d13ec4ae6fp+665 -0x1.00e69e435de68p+611 1
largest error / bound, order sequential, interpreter 0.211411 (fp:3:-5:2, every operand):
  sum_2_entry fp:3:-5:2 seq 2 -0x1p+4 -0x1.4p+1 0x1p+0 0x1.4p-3 #exhaustive:307479 -> -0x1p+4 -0x1p+0 1
```

### `sum_entry_step_1`

Claims: `rounded(t) nearest`; `error(t) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 97 199 838 | 0 | exact 29 549 016; inexact 66 492 018; tie 1 158 804 | 1 (the claim) | 1.00000 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 97 220 088 | 0 | exact 32 063 652; inexact 63 575 298; tie 1 581 138 | 1 (the claim) | 0.9999999404 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | exact 835 201; inexact 3 981 696; tie 454 272 | 1 (the claim) | 0.992248 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | exact 589 441; inexact 1 832 576; tie 310 912 | 1 (the claim) | 0.992248 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | exact 147 265; inexact 457 536; tie 77 632 | 1 (the claim) | 0.984615 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 489 | 0 | exact 2 281; inexact 7 016; tie 1 192 | 1 (the claim) | 0.888889 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 573 | 0 | exact 565; inexact 1 716; tie 292 | 1 (the claim) | 0.8 |
| `fp:1:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 625 | 619 | 0 | exact 139; inexact 400; tie 80 | 1 (the claim) | 0.666667 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500; `binary32`: extreme 387 500, halfgap 775 000, overflow 387 500, pow2 387 500, underflow 387 500, uniform 387 500, zero 387 500.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  sum_entry_step_1 binary64 0x1.0000000000001p-1022 0x1p-1022 #extreme:438 -> 0x1p-1021
largest error / bound, interpreter 1 (fp:7:-14:2, every operand):
  sum_entry_step_1 fp:7:-14:2 -0x1.fcp+8 0x1.f4p+7 #exhaustive:2236 -> -0x1p+8
```

### `sum_entry_step_2`

Claims: `normalized(t)`; `error(t) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 98 795 970 | 0 | 0.661188 | 1.98356 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 98 768 880 | 0 | 0.666666 | 2.00000 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499; `binary32`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.666666 (clang18-fixup-call/cxx, linux-x86-64):
  sum_entry_step_2 binary32 -0x1.fffffep+127 -0x1.eae94ep+102 0x1.fffffap+126 -0x1.9c86d4p+100 #overflow:1828462 -> -0x1.000002p+127 -0x1.482bfcp+100
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  sum_entry_step_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 0x1.9p+5 0x1.cp-1 #exhaustive:128359 -> -0x1.1p+6 0x1p+0
```

### `sum_fast_2`

Claims: `normalized(r)`; `fold_error(r) eps=3*u^2, term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.166667 | 0.353038 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.166667 | 0.203778 |
| `fp:3:-3:0`, every operand (another format, every array up to 2 elements) | 29 891 | 29 891 | 0 | 0.374269 | 0.374269 |
| `fp:3:-5:2`, every operand (another format, every array up to 2 elements) | 1 945 379 | 1 945 379 | 0 | 0.487062 | 0.487062 |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 2 elements) | 363 379 | 363 379 | 0 | 0.465793 | 0.465793 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153; `binary32`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.166667 (clang18-fixup-call/cxx, linux-x86-64):
  sum_fast_2 binary64 lanes:0 3 -0x1p+749 -0x1.fffffffffffffp+641 -0x1.fffffffffffffp+641 -0x1.fffffffffffffp+695 0x0p+0 0x0p+0 #tight:106 -> -0x1p+749 -0x1.fffffffffffffp+695 1
largest error / bound, order lanes, interpreter 0.487062 (fp:3:-5:2, every operand):
  sum_fast_2 fp:3:-5:2 lanes:2 2 -0x1.4p+3 -0x1.4p+2 0x1.cp-1 0x1.cp-2 #exhaustive:494688 -> -0x1.cp+3 0x0p+0 1
largest error / bound, order sequential, compiled 0.353038 (clang-fixup-inline/cxx, macos-arm64):
  sum_fast_2 binary64 seq 2 -0x1.2066f4012c9f7p+998 -0x1.3be053de556bap+998 -0x1.aeb0e12674876p+942 -0x1.c489418af3b6dp+944 #one:156 -> -0x1.2e23a3efc1059p+999 0x1.cfca862b6f278p+944 1
largest error / bound, order sequential, interpreter 0.487062 (fp:3:-5:2, every operand):
  sum_fast_2 fp:3:-5:2 seq 2 -0x1.4p+3 -0x1.4p+2 0x1.cp-1 0x1.cp-2 #exhaustive:494687 -> -0x1.cp+3 0x0p+0 1
```

### `sum_fast_2_entry`

Claims: `normalized(r)`; `fold_error(r) eps=3*u^2, term=0, tau=0; heights sequential rel n-1 abs n-1, lanes rel n-1 abs n-1`; `finite_or_nan(r) flag flag`.

| Run | Cases | Judged | Failed | largest error / bound, order lanes | largest error / bound, order sequential |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.235829 | 0.166667 |
| `binary32`, 90 runners on 3 machines | 63 000 | 63 000 | 0 | 0.298889 | 0.166667 |
| `fp:3:-5:2`, every operand (another format, every array up to 2 elements) | 1 945 379 | 1 945 379 | 0 | 0.487062 | 0.487062 |
| `fp:3:-4:1`, every operand (the full tier's format, every array up to 2 elements) | 363 379 | 363 379 | 0 | 0.465793 | 0.465793 |
| `fp:3:-3:0`, every operand (another format, every array up to 2 elements) | 29 891 | 29 891 | 0 | 0.374269 | 0.374269 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153; `binary32`: cancel 308, nonfinite 153, one 155, overflow 153, pow2 153, sign 155, tail 152, tight 308, underflow 155, wide 155, zeros 153.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, order lanes, compiled 0.298889 (msvc/avx2, windows-x64):
  sum_fast_2_entry binary32 lanes:8 2 0x1.fffffcp+125 0x1.ed70ep+126 -0x1.8c855ap+98 -0x1.d5aceap+101 #overflow:20 -> 0x1.76b86e0000000p+127 0x1.f8c2700000000p+101 1
largest error / bound, order lanes, interpreter 0.487062 (fp:3:-5:2, every operand):
  sum_fast_2_entry fp:3:-5:2 lanes:2 2 -0x1.4p+3 -0x1.4p+2 0x1.cp-1 0x1.cp-2 #exhaustive:494688 -> -0x1.cp+3 0x0p+0 1
largest error / bound, order sequential, compiled 0.166667 (clang18-fixup-call/cxx, linux-x86-64):
  sum_fast_2_entry binary64 seq 2 0x1.0000000000004p+59 -0x1.0000000000003p+59 -0x1p+6 -0x1.fffffffffffffp+5 #tight:275 -> 0x0p+0 0x0p+0 1
largest error / bound, order sequential, interpreter 0.487062 (fp:3:-5:2, every operand):
  sum_fast_2_entry fp:3:-5:2 seq 2 -0x1.4p+3 -0x1.4p+2 0x1.cp-1 0x1.cp-2 #exhaustive:494687 -> -0x1.cp+3 0x0p+0 1
```

### `sum_fast_entry_step_2`

Claims: `normalized(t)`; `error(t) form A, c=3, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 100 800 000 | 98 813 088 | 0 | 0.500000 | 1.50000 |
| `binary32`, 90 runners on 3 machines | 100 800 000 | 98 785 170 | 0 | 0.707872 | 2.12362 |
| `fp:4:-3:2`, every operand (quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.487619 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's exponent range) | 25 281 | 20 449 | 0 | 0.313725 | 0.941176 |
| `fp:4:-4:3`, every operand (another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.671916 | - |
| `fp:3:-6:4`, every operand (p = min_precision + 1, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.487062 | 1.46119 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.562328 | - |
| `fp:3:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 178 929 | 138 027 | 0 | 0.465793 | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499; `binary32`: cancel 475 001, close 712 500, extreme 237 500, overflow 237 499, pow2 237 500, underflow 475 000, uniform 237 501, zero 237 499.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.707872 (clang18-fixup-call/cxx, linux-x86-64):
  sum_fast_entry_step_2 binary32 0x1.4p+103 0x1.fffffep+78 0x1.69a5b4p+125 0x1.fffffep+100 #extreme:1282326 -> 0x1.69a5bap+125 0x0p+0
largest error / bound, interpreter 0.671916 (fp:4:-4:3, every operand):
  sum_fast_entry_step_2 fp:4:-4:3 -0x1.2p+6 0x1.ep+1 -0x1.4p+4 0x1.ep-1 #exhaustive:1228016 -> -0x1.6p+6 0x0p+0
```

### `to_down_2`

Claims: `rounded(t) down`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 23 397 408; inexact, as RN 29 352 186; differs from RN 28 918 674; a non-finite operand 20 520 000; rounds to -inf 411 732 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 25 084 206; inexact, as RN 28 515 312; differs from RN 28 064 412; a non-finite operand 20 520 000; rounds to -inf 416 070 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact, as RN 358 272; differs from RN 357 761; a non-finite operand 3; rounds to -inf 511 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact, as RN 2 584 448; differs from RN 2 582 913; a non-finite operand 3; rounds to -inf 1 535 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact, as RN 129 920; differs from RN 129 601; a non-finite operand 3; rounds to -inf 319 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact, as RN 1 384; differs from RN 1 349; a non-finite operand 3; rounds to -inf 35 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact, as RN 402; differs from RN 383; a non-finite operand 3; rounds to -inf 19 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | exact 25; inexact, as RN 110; differs from RN 100; a non-finite operand 3; rounds to -inf 10 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000; `binary32`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000.

### `to_nearest_2`

Claims: `rounded(t) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 23 372 406; inexact 32 851 998; tie 25 855 596; a non-finite operand 20 520 000 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 25 075 440; inexact 31 729 320; tie 25 275 240; a non-finite operand 20 520 000 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact 5 164 034; tie 4 862; a non-finite operand 3 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact 258 434; tie 1 406; a non-finite operand 3 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact 2 682; tie 86; a non-finite operand 3 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact 713 730; tie 2 814; a non-finite operand 3 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact 762; tie 42; a non-finite operand 3 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | exact 25; inexact 200; tie 20; a non-finite operand 3 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000; `binary32`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000.

### `to_up_2`

Claims: `rounded(t) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 23 380 470; inexact, as RN 29 314 710; differs from RN 28 971 648; a non-finite operand 20 520 000; rounds to inf 413 172 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 102 600 000 | 0 | exact 25 063 290; inexact, as RN 28 483 686; differs from RN 28 128 960; a non-finite operand 20 520 000; rounds to inf 404 064 |
| `fp:8:-16:3`, every operand (another number of exponents) | 5 174 274 | 5 174 274 | 0 | exact 5 375; inexact, as RN 2 584 448; differs from RN 2 582 913; a non-finite operand 3; rounds to inf 1 535 |
| `fp:7:-11:0`, every operand (quick tier + 1 bit) | 261 506 | 261 506 | 0 | exact 1 663; inexact, as RN 129 920; differs from RN 129 601; a non-finite operand 3; rounds to inf 319 |
| `fp:2:-6:5`, every operand (p = min_precision + 1, the quick tier's number of exponents) | 858 | 858 | 0 | exact 51; inexact, as RN 402; differs from RN 383; a non-finite operand 3; rounds to inf 19 |
| `fp:1:-5:6`, every operand (p = min_precision, the quick tier's number of exponents) | 248 | 248 | 0 | exact 25; inexact, as RN 110; differs from RN 100; a non-finite operand 3; rounds to inf 10 |
| `fp:8:-12:-1`, every operand (quick tier + 2 bits) | 719 874 | 719 874 | 0 | exact 3 327; inexact, as RN 358 272; differs from RN 357 761; a non-finite operand 3; rounds to inf 511 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's number of exponents) | 2 874 | 2 874 | 0 | exact 103; inexact, as RN 1 384; differs from RN 1 349; a non-finite operand 3; rounds to inf 35 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000; `binary32`: extreme 305 000, halfgap 610 000, nonfinite 610 000, overflow 305 000, pow2 305 000, underflow 305 000, uniform 305 000, zero 305 000.

### `two_prod`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=1/2`; `error(r) form R, c=0, k=2, t=0, when product_large`.

| Run | Cases | Judged | Failed | largest error / bound (c=0, k=2, t=1/2) | observed c | largest error / bound (c=0, k=2, t=0, when product_large) | observed c |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 6 897 024 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 6 897 474 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:3:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 481 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:2:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 597 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound (c=0, k=2, t=1/2), compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  two_prod binary64 0x1.0000000000001p-1022 0x1.8p+0 #extreme:10182 -> 0x1.8000000000002p-1022 -0x0p+0
largest error / bound (c=0, k=2, t=1/2), interpreter 1 (fp:7:-8:4, every operand):
  two_prod fp:7:-8:4 -0x1.fcp+5 -0x1.fcp-2 #exhaustive:573888 -> 0x1.f8p+4 0x0p+0
```

### `two_prod_dekker`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=13/8`; `error(r) form R, c=0, k=2, t=0, when product_large`.

| Run | Cases | Judged | Failed | largest error / bound (c=0, k=2, t=13/8) | observed c | largest error / bound (c=0, k=2, t=0, when product_large) | observed c |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 92 547 774 | 0 | 0.923232 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 86 976 072 | 0 | 0.947220 | 0 | 0 (exact) | 0 |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 1 526 625 | 0 | 0.903846 | - | 0 (exact) | - |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 1 288 225 | 0 | 0.943510 | - | 0 (exact) | - |
| `fp:4:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 42 849 | 28 561 | 0 | 0.788462 | 0 | 0 (exact) | 0 |
| `fp:7:-16:-2`, every operand (another exponent range, replaces fp:7:-20:-6, where constant splitter is not a number) | 4 190 209 | 2 307 361 | 0 | 0.943510 | - | 0 (exact) | - |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 390 625 | 0 | 0.887019 | - | 0 (exact) | - |
| `fp:5:-12:-1`, every operand (p = min_precision + 1, the quick tier's format) | 172 225 | 96 721 | 0 | 0.889423 | - | 0 (exact) | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332; `binary32`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound (c=0, k=2, t=13/8), compiled 0.947220 (clang18-fixup-call/cxx, linux-x86-64):
  two_prod_dekker binary32 -0x1.6355c8p-35 0x1.b8542p-93 #underflow:779079 -> -0x1.31981cp-127 0x1p-148
largest error / bound (c=0, k=2, t=13/8), interpreter 0.943510 (fp:7:-12:-1, every operand):
  two_prod_dekker fp:7:-12:-1 -0x1.a4p-3 -0x1.a4p-6 #exhaustive:888768 -> 0x1.6p-8 -0x1p-11
```

### `two_prod_entry`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=1/2`; `error(r) form R, c=0, k=2, t=0, when product_large`.

| Run | Cases | Judged | Failed | largest error / bound (c=0, k=2, t=1/2) | observed c | largest error / bound (c=0, k=2, t=0, when product_large) | observed c |
|---|---|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 98 321 652 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 98 308 530 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:2:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 597 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:3:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 481 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165; `binary32`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165.

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound (c=0, k=2, t=1/2), compiled 1 (clang18-fixup-call/cxx, linux-x86-64):
  two_prod_entry binary64 0x1.0000000000001p-1022 0x1.8p+0 #extreme:21942 -> 0x1.8000000000002p-1022 -0x0p+0
largest error / bound (c=0, k=2, t=1/2), interpreter 1 (fp:7:-20:-6, every operand):
  two_prod_entry fp:7:-20:-6 -0x1.fcp+0 -0x1.fcp-9 #exhaustive:576 -> 0x1.f8p-8 0x0p+0
```

### `two_sum`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 7 200 000 | 7 015 698 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 7 200 000 | 7 017 066 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 107 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 867 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 487 | 0 | 0 (exact) | 0 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 403 | 0 | 0 (exact) | - |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 573 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832; `binary32`: cancel 41 668, close 62 500, extreme 20 833, overflow 20 832, pow2 20 833, underflow 41 667, uniform 20 835, zero 20 832.

### `two_sum_entry`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 102 600 000 | 99 977 130 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 102 600 000 | 99 984 024 | 0 | 0 (exact) | 0 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 403 | 0 | 0 (exact) | - |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 107 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 867 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 487 | 0 | 0 (exact) | 0 |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 573 | 0 | 0 (exact) | 0 |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165; `binary32`: cancel 508 335, close 762 500, extreme 254 167, overflow 254 165, pow2 254 167, underflow 508 333, uniform 254 168, zero 254 165.

### `two_sum_ord`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`; `normalized(r)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 90 runners on 3 machines | 103 500 000 | 100 851 156 | 0 | 0 (exact) | 0 |
| `binary32`, 90 runners on 3 machines | 103 500 000 | 100 854 054 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 489 | 0 | 0 (exact) | 0 |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 573 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | 0 (exact) | 0 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | 0 (exact) | - |

Distinct random cases per stratum, summed over the machines (each judged by every runner of its machine): `binary64`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332; `binary32`: cancel 516 668, close 775 000, extreme 258 334, overflow 258 332, pow2 258 334, underflow 516 666, uniform 258 334, zero 258 332.

## What was not run, and why

- **$10^8$ results for every kernel and loop.** Only the 116 kernels of phase B were run to the
  aim; the 75 other new or changed kernels, the other 42 kernels unchanged since Milestone 1
  (`to_nearest_2`, the 43rd, is among the 116; they reached the aim in
  [Milestone 1's runs](brute-milestone1.md#the-aim-a-hundred-million-cases-per-kernel-and-format),
  at another commit) and the 47 loops have their share of phase A, the counts of each group are
  [above](#the-aim-a-hundred-million-results-per-kernel-and-format). The 75 are the most costly to
  judge: the interval kernels of two limbs, the radii of the ball vectors and of the convolution,
  the bounds of the dot products, the accumulators of two limbs, the steps of `axpy` of two
  limbs; reaching $10^8$ for every one of them would have taken about as long again on the Linux
  machine. A loop's case is an array of up to 4 096 elements, 265 on average: $10^8$ arrays per
  loop and format is out of reach of any such budget. The driver extends a run where it stopped
  (`run` again on the same work directory with a larger `--cases`).
- **More than one unit of the loops.** Each loop and format has one unit of random arrays per
  machine (1 000 arrays per stream on the Linux machine, 500 on the Mac and on the Windows
  machine, two units there), each judged by every runner; `lengths.py` judged the first 5 000 arrays of the Mac's stream
  of each through one runner ([above](#the-loops-over-arrays)).
- **Products of BallVectors of more than 256 coefficients** in the compiled part, where the
  oracle's judgment grows faster than the product of the two lengths
  ([above](#faults-of-the-driver-found-by-the-runs)); the convolutions of numbers have 4 096.
- **Enumerations on Windows**: the interpreter is the same Python on every machine, and the Linux
  machine and the Mac shared the plan; the Windows machine gave its time to its MSVC runners.
- **Other compilers and targets**: clang-cl is not installed on the Windows machine and nothing
  was installed for this run; no machine has AVX-512.
- **The path of constant evaluation.** The emulated part judged the default path of the printed
  kernels; the path of constant evaluation (`kairn-emulated-runner --ce`) is compared and judged
  by the full tier's emulated tests in `fp:8:-14:1` only. The interpreter's `--ce` and
  `--muladd unfused` were not enumerated.
- **The adversarial search does not take the loops over arrays**: `kairn-oracle search` searches
  kernels only, with an `error`, `upper`, `encloses` or `extends` entry; 118 of the 191 new or
  changed kernels have none of these, only kinds it does not climb
  ([above](#the-adversarial-search)).
- **The compositions of the public headers.** The runners run the generated kernels and loops;
  what `include/kairn/` composes from them (among it the correction of `axpy` of ball vectors
  that `bbcce60` brought) is tested by the tests of the public interface and by the regression
  cases' runs of it, not by this run.
- **Suspicious results of `split` and `two_prod_dekker`** do not fail their runs, as in every
  tier, nor those of `acc_radius_1` and `acc_radius_2` at precision 2 since this run
  ([above](#findings)), for which `widen.py` is the test in their place.
- **The first enumerations of the four kernels the guards failed**, and the two enumerations the
  finding stopped, are in the machines' summaries as they were run; their replacements and
  reruns are the supplementary files named above.
- **All 128 hardware threads of the Linux machine**: other work used the others; the runs used 64.
