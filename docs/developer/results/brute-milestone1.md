# Brute-force results, Milestone 1

**No claim was violated.** The oracle judged 5 288 371 976 results of the compiled kernels on
three machines (40 runners: scalar and packed, every contraction setting, five compilers) and
518 547 686 results of the generator's interpreter, which enumerated every operand of 225
toy-format domains (703 386 008 cases). It found no failure, no invalid case and no suspicious
non-finite result where the quick tier would fail on one, and every series and every enumeration
that ran passed the quick tier's guards. One enumeration stopped on its first line, through a
fault of this tier's plan and not of a kernel: `two_prod_dekker` at `fp:7:-20:-6`, a format whose
largest number (127/64) is below the splitter 17, where the interpreter refuses the kernel
([below](#what-was-not-run-and-why)).

**How close the bounds came.** Four claims are attained exactly, by some case of the runs: the
relative bound $u/(1+u)$ of `add_1_1` (a rounding to nearest), the underflow term $\eta/2$ of
`two_prod`, and the $3/2$ gaps of `radd` and of `rmul`. Two come within $10^{-9}$ of their bound
in `binary64`: `mul_1_1` and `mul_2_1`, through their underflow terms. Then `add_2_1` (0.993 of
its bound), `sub_1_2` (0.985), `sub_2_1` (0.981) and `mul_2_2` (0.979); the farthest are
`add_fast_2_2` (0.766), `add_2_2` (0.755), `mul_pow2_2` (0.750) and `sub_2_2` (0.727). Every claim
of exactness held exactly. Far from the underflow range, the largest observed constants are 3.46
for `mul_2_2` (claimed 4), 2.30 for `add_fast_2_2` (3), 2.27 for `add_2_2` and 2.18 for `sub_2_2`
(claimed $3/(1-4u)$), and 1.99 for `add_2_1`, the subtractions with one limb and `mul_2_1` (2). No
Ball radius came closer to the smallest enclosing radius than 1.03 gaps (`ball_add_1` and
`ball_sub_1` at `fp:3:-4:2`; 1.17 to 1.75 gaps in `binary64` and `binary32`), so every radius
returned could have been one unit in the last place smaller and still enclosed; the negations are
exact. On each machine, every runner (every compiler, scalar and packed, every contraction
setting) gave the same counts and the same extremes, for every kernel and format.

**The aim of $10^8$ judged cases per kernel and format was not reached**: 49 to 70 million
(63 million on average) per kernel and format, summed over the machines and their runners, from
4.4 to 5.0 million distinct cases, in about 90 minutes per machine.

## What was run

The code under test (kernels, claims, generator, interpreter, oracle) is that of commit
`e951404`. The runs started from the driver of commit `e5c3c78` and were restarted twice in their
first twenty minutes, keeping what was done, with the scheduling of `e635202` and then
`d7cdd34`, which keeps every slot busy. The commands are in
[`tests/brute/README.md`](https://github.com/danielepanozzo/kairn/blob/main/tests/brute/README.md),
the stored summaries in
[`results/milestone1/brute/`](https://github.com/danielepanozzo/kairn/tree/main/results/milestone1/brute):
one file per machine, with every count, statistic and attaining line of the tables below.

| Machine | Compilers | Runners | Seed | Cases per kernel and format | Judged (compiled) | Enumerated (interpreter) |
|---|---|---|---|---|---|---|
| linux-x86-64: Linux x86_64, AMD EPYC 7452 32-Core Processor | Clang 18.1.3, GNU 13.3.0 | 16 | `m1-linux` | 2 600 000 to 2 800 000 | 3 372 726 832 | 596 613 258 |
| macos-arm64: Darwin arm64, Apple M3 Max | AppleClang 21.0.0.21000401, GNU 16.2.0 | 16 | `m1-mac` | 800 000 to 1 000 000 | 1 262 212 240 | 106 772 750 |
| windows-x64: Windows AMD64, 13th Gen Intel(R) Core(TM) i5-13500T | MSVC 19.52.37029.0 | 8 | `m1-windows` | 1 000 000 to 1 200 000 | 653 432 904 | 0 |

Each machine ran for about 90 minutes: the Linux machine on 64 of its 128 hardware threads with
80 busy processes, the Mac with 6, the Windows machine on 8 logical processors beside its own CI
work, which at times halved its rate; all at a lower priority. A network reset ended the Windows
run fifteen minutes early; the driver stopped its pipelines, and a second run used up the budget.

**Compiled runners.** Every kernel of `gen/claims.json`, in `binary64` and `binary32`, through
every runner the quick tier builds (`kairn-gen-runner*`, `kairn-gen-packed-runner*`): the scalar
and the packed kernels, each with the build's flags and under each contraction setting, with
every compiler of the machine. Cases are the oracle's random ones, every stratum of the kernel's
family, from one seed per machine; every runner of a machine judged the same cases, as in the
quick tier. `--fail-on-suspicious` everywhere except `split` and `two_prod_dekker`, whose
product by the splitter may overflow, as in the quick tier.

**Interpreter.** The generator's interpreter on every operand of 225 toy-format domains: for each
kernel, the formats of precision `min_precision` and `min_precision + 1` in the quick tier's
exponent range, the quick tier's format one and two bits more precise, and one or two other
exponent ranges; for the three two-limb balls with two operands, complete enumerations of
formats of their `min_precision` with fewer exponents, and larger restricted domains. Of the 226
enumerations planned, the Linux machine ran 200 and the Mac 26, split by size
(`brute.py plan --bins 20`, bins 3 to 19 and 0 to 2); one of them stopped on its first line
([below](#what-was-not-run-and-why)).

**What a pass required.** The quick tier's guards (`tests/crosscheck_guards.py`), applied by
`brute.py collect` to every merged series of one kernel, format and runner, and to every
enumeration: the stream is the one asked for and seen whole (cases 0 to N of the machine's seed;
every index of the enumeration, over exactly the domain asked for); every stratum the oracle's
generator lists is present; something was judged; every `ensures` entry applied to a judged case;
every comparison was seen true and false; every rounding to nearest saw an inexact case and every
directed rounding a case where it differs from the rounding to nearest. Every series and every
enumeration that ran passed them.

## How close the claims came

### Error bounds

The largest error over the bound it is allowed, $\lvert\text{err}\rvert / (\mathrm{rel}\,\rho +
\mathrm{abs})$, over every judged case; 1 is the claim itself. A claim with `c=0` and `t=0` says
the result is exact. "(the claim)" marks an extreme equal to the bound, decided exactly.

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `add_1_1` | `error(s) form R, c=1/(1+u), k=1, t=0` | 1 (the claim) | 1 (`fp:7:-14:2`) (the claim) |
| `mul_1_1` | `error(p) form R, c=1/(1+u), k=1, t=1/2` | 1 - ε, ε < 10⁻⁹ | 0.999939 (`fp:7:-20:-6`) |
| `mul_2_1` | `error(z) form R, c=2, k=2, t=1` | 1 - ε, ε < 10⁻⁹ | 0.972718 (`fp:6:-8:-2`) |
| `two_prod` | `error(r) form R, c=0, k=2, t=1/2` | 1 (the claim) | 1 (`fp:7:-20:-6`) (the claim) |
| `add_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.992645 | 0.939450 (`fp:5:-6:3`) |
| `sub_1_2` | `error(z) form R, c=2, k=2, t=0` | 0.985325 | 0.939450 (`fp:5:-6:3`) |
| `sub_2_1` | `error(z) form R, c=2, k=2, t=0` | 0.980874 | 0.939450 (`fp:5:-6:3`) |
| `mul_2_2` | `error(z) form R, c=4, k=2, t=3/2` | 0.979252 | 0.898829 (`fp:6:-7:-3`) |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=13/8` | 0.929436 | 0.943510 (`fp:7:-12:-1`) |
| `add_fast_2_2` | `error(z) form A, c=3, k=2, t=0` | 0.766145 | 0.671916 (`fp:4:-4:3`) |
| `add_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.755381 | 0.556176 (`fp:5:-3:2`) |
| `mul_pow2_2` | `error(z) form R, c=0, k=2, t=1` | 0.750000 | 0.746094 (`fp:6:-12:4`) |
| `sub_2_2` | `error(z) form R, c=3/(1-4*u), k=2, t=0` | 0.726732 | 0.556176 (`fp:5:-3:2`) |
| `abs_2` | `error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:8:-20:2`) |
| `fast_two_sum` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-14:2`) |
| `neg_2` | `error(z) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:8:-20:2`) |
| `split` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:13:-60:40`) |
| `two_prod` | `error(r) form R, c=0, k=2, t=0, when product_large` | 0 (exact) | 0 (exact; `fp:7:-20:-6`) |
| `two_prod_dekker` | `error(r) form R, c=0, k=2, t=0, when product_large` | 0 (exact) | 0 (exact; `fp:7:-8:4`) |
| `two_sum` | `error(r) form R, c=0, k=2, t=0` | 0 (exact) | 0 (exact; `fp:7:-14:2`) |

### Upper bounds

The largest excess of the result over the exact value, in gaps of the result (`upper` claims: at
most `gaps`).

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `radd` | `upper(r) gaps=3/2` | 1.5 (the claim) | 1.5 (`fp:8:-14:2`) (the claim) |
| `rmul` | `upper(r) gaps=3/2` | 1.5 (the claim) | 1.5 (`fp:8:-8:4`) (the claim) |

### Ball radii

The smallest slack of the returned radius over the smallest radius that encloses the exact set, in
gaps of the radius: below 1, a radius one unit in the last place smaller would no longer enclose.
The negations are exact (slack 0).

| Kernel | Claim | Compiled | Interpreter (format) |
|---|---|---|---|
| `ball_mul_2` | `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]` | 1.75000 | 1.91406 (`fp:4:-5:1`) |
| `ball_mul_1` | `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]` | 1.75000 | 1.69678 (`fp:3:-6:2`) |
| `ball_scale_2` | `encloses(cz, rz) x*a over x=[cx +- rx]` | 1.26672 | 1.375 (`fp:4:-4:1`) |
| `ball_add_2` | `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]` | 1.25016 | 1.25 (`fp:3:-3:2`) |
| `ball_sub_2` | `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]` | 1.25199 | 1.25 (`fp:3:-3:2`) |
| `ball_scale_1` | `encloses(cz, rz) x*a over x=[cx +- rx]` | 1.25 | 1.125 (`fp:5:-5:0`) |
| `ball_add_1` | `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]` | 1.25 | 1.03125 (`fp:3:-4:2`) |
| `ball_sub_1` | `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]` | 1.16689 | 1.03125 (`fp:3:-4:2`) |
| `ball_neg_1` | `encloses(cz, rz) -x over x=[cx +- rx]` | 0 | 0 (`fp:7:-14:2`) |
| `ball_neg_2` | `encloses(cz, rz) -x over x=[cx +- rx]` | 0 | 0 (`fp:5:-8:4`) |

## Per kernel

Each table has one row per format of the compiled runners (every machine and runner together)
and one per enumeration of the interpreter. "Judged" excludes the cases whose result is not
finite, about which the claims say nothing. "Observed c" is the oracle's (a): the largest
$\lvert\text{err}\rvert / (u^k \rho)$ over the cases far from the underflow range
($u^k\rho \ge 2^p\eta$), to compare with the claim's `c`. Below each table, the lines that attain
the extremes, as the oracle reports them: a line's tag (`#STRATUM:INDEX` or `#exhaustive:INDEX`)
and the machine's seed regenerate its case
([Rerunning one case](../testing.md#rerunning-one-case)). The runner named is the first of a
machine's runners to attain it: they all judged the same cases and agreed.

### `abs_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | 0 (exact) | 0 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | 0 (exact) | 0 |
| `fp:8:-20:2`, every operand (another exponent range) | 7 926 015 | 7 926 015 | 0 | 0 (exact) | 0 |
| `fp:8:-8:4`, every operand (quick tier + 2 bits) | 1 047 295 | 1 047 295 | 0 | 0 (exact) | - |
| `fp:7:-8:4`, every operand (quick tier + 1 bit) | 359 679 | 359 679 | 0 | 0 (exact) | - |
| `fp:2:-8:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 027 | 1 027 | 0 | 0 (exact) | 0 |
| `fp:3:-8:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 3 503 | 3 503 | 0 | 0 (exact) | 0 |

### `abs_upper_2`

Claims: `rounded(t) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 64 943 808 | 0 | exact 18 687 696, inexact, as RN 26 834 976, differs from RN 19 421 136 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 64 936 384 | 0 | exact 20 036 096, inexact, as RN 26 086 568, differs from RN 18 813 720 |
| `fp:8:-20:2`, every operand (another exponent range) | 7 926 015 | 7 922 177 | 0 | exact 6 143, inexact, as RN 3 958 016, differs from RN 3 958 018 |
| `fp:8:-8:4`, every operand (quick tier + 2 bits) | 1 047 295 | 1 046 017 | 0 | exact 3 583, inexact, as RN 521 216, differs from RN 521 218 |
| `fp:7:-8:4`, every operand (quick tier + 1 bit) | 359 679 | 358 913 | 0 | exact 1 791, inexact, as RN 178 560, differs from RN 178 562 |
| `fp:3:-8:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 3 503 | 3 425 | 0 | exact 111, inexact, as RN 1 656, differs from RN 1 658 |
| `fp:2:-8:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 027 | 985 | 0 | exact 55, inexact, as RN 464, differs from RN 466 |

### `add_1_1`

Claims: `rounded(s) nearest`; `error(s) form R, c=1/(1+u), k=1, t=0`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 70 400 000 | 66 114 464 | 0 | exact 20 101 240, inexact 45 222 344, tie 790 880 | 1 (the claim) | 1.00000 |
| `binary32`, 40 runners on 3 machines | 70 400 000 | 66 119 600 | 0 | exact 21 808 624, inexact 43 232 264, tie 1 078 712 | 1 (the claim) | 0.9999999404 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 169 | 0 | exact 835 201, inexact 3 981 696, tie 454 272 | 1 (the claim) | 0.992248 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 929 | 0 | exact 589 441, inexact 1 832 576, tie 310 912 | 1 (the claim) | 0.992248 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 489 | 0 | exact 2 281, inexact 7 016, tie 1 192 | 1 (the claim) | 0.888889 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 573 | 0 | exact 565, inexact 1 716, tie 292 | 1 (the claim) | 0.8 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 433 | 0 | exact 147 265, inexact 457 536, tie 77 632 | 1 (the claim) | 0.984615 |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 1 (clang18/avx2, linux-x86-64):
  add_1_1 binary64 -0x1p-1022 -0x1.0000000000001p-1022 #extreme:22 -> -0x1p-1021
largest error / bound, interpreter 1 (fp:7:-14:2, every operand):
  add_1_1 fp:7:-14:2 -0x1.fcp+8 0x1.f4p+7 #exhaustive:2236 -> -0x1p+8
```

### `add_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 64 298 000 | 0 | 0.940060 | 1.88012 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 64 285 624 | 0 | 0.992645 | 1.98529 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.992645 (clang/cxx, macos-arm64):
  add_2_1 binary32 0x1.00001p+110 -0x1.fffffep+85 -0x1.fc3502p+108 #extreme:374838 -> 0x1.01e59cp+109 0x1p+85
largest error / bound, interpreter 0.939450 (fp:5:-6:3, every operand):
  add_2_1 fp:5:-6:3 -0x1p+7 -0x1.1p+1 0x1.fp+5 #exhaustive:847632 -> -0x1.1p+6 0x0p+0
```

### `add_2_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 64 296 704 | 0 | 0.746554 | 2.23966 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 64 284 352 | 0 | 0.755381 | 2.26614 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.755381 (msvc/avx2, windows-x64):
  add_2_2 binary32 -0x1.09adc4p+126 -0x1.7fb9f2p+101 0x1.fffffep+124 -0x1.099ee4p+95 #overflow:636838 -> -0x1.135b8a0000000p+125 -0x1.07c0e00000000p+100
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  add_2_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 0x1.9p+5 0x1.cp-1 #exhaustive:128359 -> -0x1.1p+6 0x1p+0
```

### `add_fast_2_2`

Claims: `normalized(z)`; `error(z) form A, c=3, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 64 298 616 | 0 | 0.766145 | 2.29844 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 64 285 512 | 0 | 0.502673 | 1.50802 |
| `fp:4:-4:3`, every operand (another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.671916 | - |
| `fp:3:-6:4`, every operand (p = min_precision + 1, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.487062 | 1.46119 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.562328 | - |
| `fp:4:-3:2`, every operand (quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.487619 | - |
| `fp:3:-3:2`, every operand (p = min_precision + 1, the quick tier's format) | 178 929 | 138 027 | 0 | 0.465793 | - |
| `fp:2:-3:2`, every operand (p = min_precision, the quick tier's exponent range) | 25 281 | 20 449 | 0 | 0.313725 | 0.941176 |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.766145 (clang18/avx2, linux-x86-64):
  add_fast_2_2 binary64 -0x1.0ccccb9505dbap-500 -0x1.fa6bb0fb4cffp-554 -0x1.2bf644ff5e684p-503 -0x1.7114e61b3c196p-557 #close:2407041 -> -0x1.324b9434f1a8bp-500 -0x1.44726df5a41p-557
largest error / bound, interpreter 0.671916 (fp:4:-4:3, every operand):
  add_fast_2_2 fp:4:-4:3 -0x1.2p+6 0x1.ep+1 -0x1.4p+4 0x1.ep-1 #exhaustive:1228016 -> -0x1.6p+6 0x0p+0
```

### `ball_add_1`

Claims: `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 70 400 000 | 64 958 848 | 0 | 1.25 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 70 400 000 | 64 874 584 | 0 | 1.25 | 1.000000075 |
| `fp:4:-3:1`, every operand (quick tier + 2 bits) | 20 793 600 | 15 766 888 | 0 | 1.1875 | 1.09402 |
| `fp:3:-4:2`, every operand (p = min_precision + 1, another exponent range) | 4 064 256 | 3 228 614 | 0 | 1.03125 | 1.18519 |
| `fp:2:-6:4`, every operand (p = min_precision, another exponent range) | 1 272 384 | 1 012 934 | 0 | 1.0625 | 1.45455 |
| `fp:3:-3:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 272 384 | 886 054 | 0 | 1.0625 | 1.18519 |
| `fp:2:-3:1`, every operand (p = min_precision, the quick tier's format) | 76 176 | 41 318 | 0 | 1.0625 | 1.45455 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25 (clang18/avx2, linux-x86-64):
  ball_add_1 binary64 -0x1p+1023 0x1.ffffffffffffep+1022 0x1.ffffffffffffdp+1021 0x1.ffffffffffffep+1021 #overflow:9668 -> -0x1.0000000000002p+1022 0x1.8p+1023
smallest radius slack, gaps, interpreter 1.03125 (fp:3:-4:2, every operand):
  ball_add_1 fp:3:-4:2 -0x1.4p+4 0x1.cp-1 0x1.cp+2 0x1.cp+3 #exhaustive:152955 -> -0x1.8p+3 0x1.4p+4
```

### `ball_add_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x+y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 60 574 056 | 0 | 1.25605 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 60 556 904 | 0 | 1.25016 | 1.000000089 |
| `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision + 1, quick tier + 1 bit) | 15 713 296 | 11 508 304 | 0 | 2 | 1.2 |
| `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` (p = min_precision, the quick tier's format) | 8 767 521 | 4 840 740 | 0 | 1.25 | 1.33333 |
| `fp:3:-3:2`, restricted: `cx.lead=-1:0` (p = min_precision, the quick tier's format) | 7 295 904 | 5 345 206 | 0 | 1.25 | 1.21905 |
| `fp:3:-2:1`, every operand (p = min_precision, another exponent range) | 5 664 400 | 2 481 996 | 0 | 1.375 | 1.23077 |
| `fp:3:-3:1`, every operand (p = min_precision, another exponent range) | 32 901 696 | 17 131 152 | 0 | 1.25 | 1.23077 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25016 (clang18/avx2, linux-x86-64):
  ball_add_2 binary32 -0x1.76e318p-61 0x1.d07d4ap-99 0x1.fffffep+126 0x1.58474ep+124 -0x1.536dfp+97 0x1.ffaa62p+101 #radii:537642 -> 0x1.58474ep+124 -0x1.536dfp+97 0x1.000002p+127
smallest radius slack, gaps, interpreter 1.25 (fp:3:-3:2, restricted: rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4, ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4):
  ball_add_2 fp:3:-3:2 -0x1.4p+3 -0x1.8p-1 0x1.8p-2 0x1.cp+1 0x1p-3 0x1.cp+2 #exhaustive:2598482 -> -0x1.cp+2 0x0p+0 0x1.4p+3
```

### `ball_mul_1`

Claims: `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 70 400 000 | 55 211 440 | 0 | 1.79124 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 70 400 000 | 55 027 416 | 0 | 1.75000 | 1.000000123 |
| `fp:4:-4:0`, every operand (quick tier + 2 bits) | 20 793 600 | 6 566 889 | 0 | 1.78125 | 1.17029 |
| `fp:3:-6:2`, every operand (p = min_precision + 1, another exponent range) | 9 985 600 | 5 446 563 | 0 | 1.69678 | 1.39891 |
| `fp:2:-7:3`, every operand (p = min_precision, another exponent range) | 1 272 384 | 765 990 | 0 | 1.75488 | 2.19979 |
| `fp:3:-4:0`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 272 384 | 544 871 | 0 | 1.87109 | 1.43017 |
| `fp:2:-4:0`, every operand (p = min_precision, the quick tier's format) | 76 176 | 34 959 | 0 | 1.85156 | 2.32727 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.75000 (clang18/avx2, linux-x86-64):
  ball_mul_1 binary32 -0x1.78c59ep+39 0x1.fffffcp+125 -0x1.fffffcp-127 0x1p-101 #wide:2300144 -> 0x1.78c59cp-87 0x1.000002p+25
smallest radius slack, gaps, interpreter 1.69678 (fp:3:-6:2, every operand):
  ball_mul_1 fp:3:-6:2 -0x1.4p-2 0x1.4p+3 -0x1p-6 0x1.4p-1 #exhaustive:3392217 -> 0x0p+0 0x1.4p+3
```

### `ball_mul_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x*y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 50 658 064 | 0 | 1.75000 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 49 318 872 | 0 | 1.75661 | 1.000000122 |
| `fp:4:-5:1`, restricted: `cx.lead=0:0`, `cy.lead=0:0` (p = min_precision, the quick tier's format) | 15 745 024 | 9 067 196 | 0 | 1.91406 | 1.19070 |
| `fp:4:-2:0`, every operand (p = min_precision, another exponent range) | 15 492 096 | 357 055 | 0 | 2.375 | 1.29032 |
| `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `ry.in=0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4`, `cx.lead=0:0` (p = min_precision, the quick tier's format) | 2 701 650 | 1 196 878 | 0 | 2.1875 | 1.24100 |
| `fp:5:-4:1`, restricted: `rx.in=0x0p+0/0x1p-4/0x1.8p+0`, `ry.in=0x0p+0/0x1p-4/0x1.8p+0`, `cx.lead=0:0` (p = min_precision + 1, another exponent range) | 580 320 | 368 568 | 0 | 2.54688 | 1.15081 |
| `fp:4:-5:1`, restricted: `rx.in=0x0p+0/0x1p-5/0x1.8p+0`, `ry.in=0x0p+0/0x1p-5/0x1.8p+0` (p = min_precision, the quick tier's format) | 27 342 441 | 4 060 565 | 0 | 2.3125 | 1.21471 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.75000 (msvc/avx2, windows-x64):
  ball_mul_2 binary64 0x1.0000000000001p-1022 0x0p+0 0x1.ffffffffffffep+1021 0x1.ffffffffffffep-1023 0x0p+0 0x1p-968 #extreme:655497 -> 0x0.0000000000000p+0 0x0.0000000000000p+0 0x1.0000000000001p+54
smallest radius slack, gaps, interpreter 1.91406 (fp:4:-5:1, restricted: cx.lead=0:0, cy.lead=0:0):
  ball_mul_2 fp:4:-5:1 -0x1.8p+0 -0x1p-4 0x1.4p+2 -0x1.4p+0 0x0p+0 0x1p-3 #exhaustive:2961476 -> 0x1p+1 -0x1p-4 0x1.2p+3
```

### `ball_neg_1`

Claims: `encloses(cz, rz) -x over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 70 400 000 | 70 400 000 | 0 | 0 | 1 |
| `binary32`, 40 runners on 3 machines | 70 400 000 | 70 400 000 | 0 | 0 | 1 |
| `fp:7:-14:2`, every operand (another exponent range) | 2 653 056 | 2 653 056 | 0 | 0 | 1 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 1 383 616 | 1 383 616 | 0 | 0 | 1 |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 345 696 | 345 696 | 0 | 0 | 1 |
| `fp:3:-7:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 5 356 | 5 356 | 0 | 0 | 1 |
| `fp:2:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 326 | 1 326 | 0 | 0 | 1 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18/avx2, linux-x86-64):
  ball_neg_1 binary64 0x1.fffffffffffffp+1023 0x1.ffffffffffffep+1023 #cancel:6 -> -0x1.fffffffffffffp+1023 0x1.ffffffffffffep+1023
smallest radius slack, gaps, interpreter 0 (fp:7:-14:2, every operand):
  ball_neg_1 fp:7:-14:2 -0x1.fcp+8 0x0p+0 #exhaustive:0 -> 0x1.fcp+8 0x0p+0
```

### `ball_neg_2`

Claims: `normalized(cz)`; `encloses(cz, rz) -x over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | 0 | 1 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | 0 | 1 |
| `fp:5:-8:4`, every operand (another exponent range) | 8 429 344 | 8 429 344 | 0 | 0 | 1 |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 2 080 512 | 2 080 512 | 0 | 0 | 1 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 515 968 | 515 968 | 0 | 0 | 1 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, the quick tier's exponent range) | 21 472 | 21 472 | 0 | 0 | 1 |
| `fp:2:-4:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 3 760 | 3 760 | 0 | 0 | 1 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 0 (clang18/avx2, linux-x86-64):
  ball_neg_2 binary64 0x1.cdbaf0839ec4dp-572 -0x1.e075c085752fdp-649 0x1.ffffffffffffdp+1023 #cancel:6 -> -0x1.cdbaf0839ec4dp-572 0x1.e075c085752fdp-649 0x1.ffffffffffffdp+1023
smallest radius slack, gaps, interpreter 0 (fp:5:-8:4, every operand):
  ball_neg_2 fp:5:-8:4 -0x1.fp+8 -0x1.fp+2 0x0p+0 #exhaustive:0 -> 0x1.fp+8 0x1.fp+2 0x0p+0
```

### `ball_scale_1`

Claims: `encloses(cz, rz) x*a over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 68 800 000 | 54 637 128 | 0 | 1.25 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 68 800 000 | 53 522 064 | 0 | 1.25 | 1.000000078 |
| `fp:5:-5:0`, every operand (quick tier + 2 bits) | 5 569 648 | 3 295 116 | 0 | 1.125 | 1.04348 |
| `fp:4:-8:2`, every operand (another exponent range) | 3 502 176 | 2 735 014 | 0 | 1.25 | 1.09804 |
| `fp:4:-5:0`, every operand (quick tier + 1 bit) | 689 976 | 493 030 | 0 | 1.25 | 1.09804 |
| `fp:3:-5:0`, every operand (p = min_precision + 1, the quick tier's format) | 84 700 | 69 058 | 0 | 1.25 | 1.24272 |
| `fp:2:-5:0`, every operand (p = min_precision, the quick tier's exponent range) | 10 206 | 9 088 | 0 | 1.375 | 1.72973 |
| `fp:3:-8:2`, every operand (p = min_precision + 1, another exponent range) | 433 200 | 362 382 | 0 | 1.25 | 1.24272 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25 (clang18/avx2, linux-x86-64):
  ball_scale_1 binary64 0x1.0d19d8c07d615p-669 0x1.785c00a86858ep-669 0x1.8p+520 #wide:710894 -> 0x1.93a6c520bc12p-149 0x1.1a45007e4e42cp-148
smallest radius slack, gaps, interpreter 1.125 (fp:5:-5:0, every operand):
  ball_scale_1 fp:5:-5:0 -0x1.2p+4 0x1.9p+4 -0x1.4p-1 #exhaustive:348194 -> 0x1.6p+3 0x1.1p+4
```

### `ball_scale_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x*a over x=[cx +- rx]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 52 062 280 | 0 | 1.26672 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 50 557 536 | 0 | 1.32283 | 1.000000083 |
| `fp:4:-4:1`, every operand (quick tier + 2 bits) | 6 160 056 | 2 655 194 | 0 | 1.375 | 1.11512 |
| `fp:3:-6:2`, every operand (p = min_precision + 1, another exponent range) | 4 294 440 | 2 874 042 | 0 | 1.38086 | 1.25490 |
| `fp:2:-8:3`, every operand (p = min_precision, another exponent range) | 1 133 730 | 895 102 | 0 | 1.41406 | 1.73266 |
| `fp:3:-4:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 651 420 | 376 150 | 0 | 1.41406 | 1.26890 |
| `fp:2:-4:1`, every operand (p = min_precision, the quick tier's format) | 60 102 | 42 378 | 0 | 1.41406 | 1.73559 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.26672 (clang18/avx2, linux-x86-64):
  ball_scale_2 binary64 0x1.0002p-939 -0x1p-992 0x1.9056b1b9f1898p-991 0x1.797dec176ca3dp+1023 #extreme:383901 -> 0x1.7980df1344d2ap+84 -0x1.4227b05db28fp+29 0x1.272a4ba215026p+33
smallest radius slack, gaps, interpreter 1.375 (fp:4:-4:1, every operand):
  ball_scale_2 fp:4:-4:1 -0x1p-1 0x0p+0 0x1.6p+2 -0x1.6p-1 #exhaustive:3031121 -> 0x1.8p-2 -0x0p+0 0x1.2p+2
```

### `ball_sub_1`

Claims: `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 68 800 000 | 63 471 816 | 0 | 1.25 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 68 800 000 | 63 412 408 | 0 | 1.16689 | 1.000000075 |
| `fp:4:-3:1`, every operand (quick tier + 2 bits) | 20 793 600 | 15 766 888 | 0 | 1.1875 | 1.09402 |
| `fp:3:-4:2`, every operand (p = min_precision + 1, another exponent range) | 4 064 256 | 3 228 614 | 0 | 1.03125 | 1.18519 |
| `fp:2:-6:4`, every operand (p = min_precision, another exponent range) | 1 272 384 | 1 012 934 | 0 | 1.0625 | 1.45455 |
| `fp:3:-3:1`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 272 384 | 886 054 | 0 | 1.0625 | 1.18519 |
| `fp:2:-3:1`, every operand (p = min_precision, the quick tier's format) | 76 176 | 41 318 | 0 | 1.0625 | 1.45455 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.16689 (clang18/avx2, linux-x86-64):
  ball_sub_1 binary32 -0x1.586812p+124 0x1.fffffep+126 -0x1.1d1a1p+127 0x1.aa3824p+101 #radii:1688168 -> 0x1.e41a1cp+126 0x1.000002p+127
smallest radius slack, gaps, interpreter 1.03125 (fp:3:-4:2, every operand):
  ball_sub_1 fp:3:-4:2 -0x1.4p+4 0x1.cp-1 -0x1.cp+2 0x1.cp+3 #exhaustive:151483 -> -0x1.8p+3 0x1.4p+4
```

### `ball_sub_2`

Claims: `normalized(cz)`; `encloses(cz, rz) x-y over x=[cx +- rx], y=[cy +- ry]`.

| Run | Cases | Judged | Failed | smallest radius slack, gaps | smallest radius / enclosing |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 60 587 392 | 0 | 1.25202 | 1.00000 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 60 551 720 | 0 | 1.25199 | 1.000000088 |
| `fp:4:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1`, `ry.in=0x0p+0/0x1p-3/0x1p-1/0x1.4p+1` (p = min_precision + 1, quick tier + 1 bit) | 15 713 296 | 11 508 304 | 0 | 2 | 1.2 |
| `fp:3:-3:2`, restricted: `rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4`, `ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4` (p = min_precision, the quick tier's format) | 8 767 521 | 4 840 740 | 0 | 1.25 | 1.33333 |
| `fp:3:-3:2`, restricted: `cx.lead=-1:0` (p = min_precision, the quick tier's format) | 7 295 904 | 5 345 206 | 0 | 1.25 | 1.21905 |
| `fp:3:-2:1`, every operand (p = min_precision, another exponent range) | 5 664 400 | 2 481 996 | 0 | 1.375 | 1.23077 |
| `fp:3:-3:1`, every operand (p = min_precision, another exponent range) | 32 901 696 | 17 131 152 | 0 | 1.25 | 1.23077 |

Where the extremes are attained (the line as the oracle reports it):

```
smallest radius slack, gaps, compiled 1.25199 (clang18/avx2, linux-x86-64):
  ball_sub_2 binary32 -0x1.65bbb2p+102 0x1p+57 0x1.fffffcp+126 0x1.e8156ap+99 0x1.6cae0ap+72 0x1.7efb92p+103 #radii:1997620 -> -0x1.a2be6p+102 0x1.749aap+77 0x1.000002p+127
smallest radius slack, gaps, interpreter 1.25 (fp:3:-3:2, restricted: rx.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4, ry.in=0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4):
  ball_sub_2 fp:3:-3:2 -0x1.4p+3 -0x1.8p-1 0x1.8p-2 -0x1.cp+1 -0x1p-3 0x1.cp+2 #exhaustive:2598076 -> -0x1.cp+2 0x0p+0 0x1.4p+3
```

### `eq_2_1`

Claims: `predicate(m) eq(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 10 258 336, false 55 341 664 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 11 251 448, false 54 348 552 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 694 273 | 0 | true 351, false 5 693 922 |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 4 152 897 | 0 | true 511, false 4 152 386 |
| `fp:4:-7:4`, every operand (another exponent range) | 1 934 001 | 1 934 001 | 0 | true 207, false 1 933 794 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 1 027 905 | 0 | true 255, false 1 027 650 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, the quick tier's exponent range) | 42 273 | 42 273 | 0 | true 63, false 42 210 |
| `fp:2:-4:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 7 285 | 7 285 | 0 | true 31, false 7 254 |

### `eq_2_2`

Claims: `predicate(m) eq(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 18 794 224, false 46 805 776 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 19 469 168, false 46 130 832 |
| `fp:4:-4:3`, every operand (another exponent range) | 7 568 001 | 7 568 001 | 0 | true 2 751, false 7 565 250 |
| `fp:3:-6:4`, every operand (p = min_precision + 2, another exponent range) | 5 303 809 | 5 303 809 | 0 | true 2 303, false 5 301 506 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 4 060 225 | 0 | true 2 015, false 4 058 210 |
| `fp:4:-3:2`, every operand (quick tier + 1 bit) | 982 081 | 982 081 | 0 | true 991, false 981 090 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 25 281 | 25 281 | 0 | true 159, false 25 122 |
| `fp:3:-3:2`, every operand (p = min_precision + 2, the quick tier's format) | 178 929 | 178 929 | 0 | true 423, false 178 506 |

### `fast_two_sum`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`; `normalized(r)`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 68 800 000 | 67 044 240 | 0 | 0 (exact) | 0 |
| `binary32`, 40 runners on 3 machines | 68 800 000 | 67 043 744 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 2 654 207 | 2 637 823 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 1 384 447 | 1 368 063 | 0 | 0 (exact) | - |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 346 111 | 342 015 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 5 407 | 5 343 | 0 | 0 (exact) | 0 |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 1 351 | 1 335 | 0 | 0 (exact) | 0 |

### `le_1_2`

Claims: `predicate(m) le(a, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 43 573 952, false 22 026 048 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 43 853 064, false 21 746 936 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 694 273 | 0 | true 2 847 312, false 2 846 961 |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 4 152 897 | 0 | true 2 076 704, false 2 076 193 |
| `fp:4:-7:4`, every operand (another exponent range) | 1 934 001 | 1 934 001 | 0 | true 967 104, false 966 897 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 1 027 905 | 0 | true 514 080, false 513 825 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, the quick tier's exponent range) | 42 273 | 42 273 | 0 | true 21 168, false 21 105 |
| `fp:2:-4:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 7 285 | 7 285 | 0 | true 3 658, false 3 627 |

### `le_2_1`

Claims: `predicate(m) le(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 38 094 624, false 27 505 376 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 38 592 328, false 27 007 672 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 694 273 | 0 | true 2 847 312, false 2 846 961 |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 4 152 897 | 0 | true 2 076 704, false 2 076 193 |
| `fp:4:-7:4`, every operand (another exponent range) | 1 934 001 | 1 934 001 | 0 | true 967 104, false 966 897 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 1 027 905 | 0 | true 514 080, false 513 825 |
| `fp:2:-4:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 7 285 | 7 285 | 0 | true 3 658, false 3 627 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, the quick tier's exponent range) | 42 273 | 42 273 | 0 | true 21 168, false 21 105 |

### `le_2_2`

Claims: `predicate(m) le(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 42 420 576, false 23 179 424 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 42 724 344, false 22 875 656 |
| `fp:4:-4:3`, every operand (another exponent range) | 7 568 001 | 7 568 001 | 0 | true 3 785 376, false 3 782 625 |
| `fp:3:-6:4`, every operand (p = min_precision + 2, another exponent range) | 5 303 809 | 5 303 809 | 0 | true 2 653 056, false 2 650 753 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 4 060 225 | 0 | true 2 031 120, false 2 029 105 |
| `fp:4:-3:2`, every operand (quick tier + 1 bit) | 982 081 | 982 081 | 0 | true 491 536, false 490 545 |
| `fp:3:-3:2`, every operand (p = min_precision + 2, the quick tier's format) | 178 929 | 178 929 | 0 | true 89 676, false 89 253 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 25 281 | 25 281 | 0 | true 12 720, false 12 561 |

### `lt_1_2`

Claims: `predicate(m) lt(a, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 22 453 624, false 43 146 376 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 22 197 336, false 43 402 664 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 694 273 | 0 | true 2 846 961, false 2 847 312 |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 4 152 897 | 0 | true 2 076 193, false 2 076 704 |
| `fp:4:-7:4`, every operand (another exponent range) | 1 934 001 | 1 934 001 | 0 | true 966 897, false 967 104 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 1 027 905 | 0 | true 513 825, false 514 080 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, the quick tier's exponent range) | 42 273 | 42 273 | 0 | true 21 105, false 21 168 |
| `fp:2:-4:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 7 285 | 7 285 | 0 | true 3 627, false 3 658 |

### `lt_2_1`

Claims: `predicate(m) lt(x, a)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 27 845 784, false 37 754 216 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 27 357 240, false 38 242 760 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 694 273 | 0 | true 2 846 961, false 2 847 312 |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 4 152 897 | 0 | true 2 076 193, false 2 076 704 |
| `fp:4:-7:4`, every operand (another exponent range) | 1 934 001 | 1 934 001 | 0 | true 966 897, false 967 104 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 1 027 905 | 0 | true 513 825, false 514 080 |
| `fp:3:-4:2`, every operand (p = min_precision + 2, the quick tier's exponent range) | 42 273 | 42 273 | 0 | true 21 105, false 21 168 |
| `fp:2:-4:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 7 285 | 7 285 | 0 | true 3 627, false 3 658 |

### `lt_2_2`

Claims: `predicate(m) lt(x, y)`.

| Run | Cases | Judged | Failed | outcomes |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 23 583 648, false 42 016 352 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | true 23 251 400, false 42 348 600 |
| `fp:4:-4:3`, every operand (another exponent range) | 7 568 001 | 7 568 001 | 0 | true 3 782 625, false 3 785 376 |
| `fp:3:-6:4`, every operand (p = min_precision + 2, another exponent range) | 5 303 809 | 5 303 809 | 0 | true 2 650 753, false 2 653 056 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 4 060 225 | 0 | true 2 029 105, false 2 031 120 |
| `fp:4:-3:2`, every operand (quick tier + 1 bit) | 982 081 | 982 081 | 0 | true 490 545, false 491 536 |
| `fp:3:-3:2`, every operand (p = min_precision + 2, the quick tier's format) | 178 929 | 178 929 | 0 | true 89 253, false 89 676 |
| `fp:2:-3:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 25 281 | 25 281 | 0 | true 12 561, false 12 720 |

### `mul_1_1`

Claims: `rounded(p) nearest`; `error(p) form R, c=1/(1+u), k=1, t=1/2`.

| Run | Cases | Judged | Failed | cases by rounding | largest error / bound | observed c |
|---|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 68 800 000 | 55 159 000 | 0 | exact 19 896 480, inexact 35 218 696, tie 43 824 | 1 - ε, ε < 10⁻⁹ | 1.00000 |
| `binary32`, 40 runners on 3 machines | 68 800 000 | 55 580 632 | 0 | exact 20 008 408, inexact 35 423 368, tie 148 856 | 0.9999999404 | 0.9999998212 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | exact 114 689, inexact 3 989 676, tie 75 928 | 0.999939 | 0.992248 |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | exact 118 385, inexact 2 267 576, tie 74 352 | 0.999512 | 0.992248 |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | exact 49 985, inexact 559 608, tie 27 888 | 0.999512 | 0.984615 |
| `fp:3:-12:-1`, every operand (p = min_precision + 2, the quick tier's exponent range) | 10 609 | 10 481 | 0 | exact 2 921, inexact 6 128, tie 1 432 | 0.999512 | 0.888889 |
| `fp:2:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 601 | 2 597 | 0 | exact 1 089, inexact 1 364, tie 144 | 0.833333 | 0.444444 |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | exact 145 697, inexact 1 967 764, tie 84 024 | 0.999756 | 0.992248 |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.9999999404 (clang18/avx2, linux-x86-64):
  mul_1_1 binary32 -0x1p-149 0x1p-1 #halfgap:696988 -> -0x0p+0
largest error / bound, interpreter 0.999939 (fp:7:-20:-6, every operand):
  mul_1_1 fp:7:-20:-6 -0x1.8p+0 -0x1.58p-1 #exhaustive:63562 -> 0x1p+0
```

### `mul_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 62 809 280 | 0 | 1 - ε, ε < 10⁻⁹ | 1.94182 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 62 739 424 | 0 | 0.9999998808 | 1.99343 |
| `fp:6:-8:-2`, every operand (quick tier + 2 bits) | 4 152 897 | 2 754 581 | 0 | 0.972718 | - |
| `fp:5:-4:2`, every operand (another exponent range) | 1 027 905 | 304 717 | 0 | 0.907265 | - |
| `fp:3:-8:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 42 273 | 41 241 | 0 | 0.794235 | - |
| `fp:2:-8:-2`, every operand (p = min_precision, the quick tier's exponent range) | 7 285 | 7 285 | 0 | 0.628272 | 0.410256 |
| `fp:5:-8:-2`, every operand (quick tier + 1 bit) | 1 027 905 | 799 453 | 0 | 0.951325 | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.9999998808 (clang18/avx2, linux-x86-64):
  mul_2_1 binary32 -0x1.8p+0 -0x1.fffffep-25 -0x1.000002p-126 #extreme:1533666 -> 0x1.800006p-126 0x0p+0
largest error / bound, interpreter 0.972718 (fp:6:-8:-2, every operand):
  mul_2_1 fp:6:-8:-2 -0x1.2p+2 -0x1.cp-5 -0x1.2p-5 #exhaustive:1480613 -> 0x1.4p-3 0x0p+0
```

### `mul_2_2`

Claims: `normalized(z)`; `error(z) form R, c=4, k=2, t=3/2`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 62 803 480 | 0 | 0.979252 | 3.45730 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 62 748 408 | 0 | 0.966326 | 3.30371 |
| `fp:5:-8:-2`, every operand (p = min_precision + 1, another exponent range) | 16 248 961 | 6 272 821 | 0 | 0.878457 | - |
| `fp:6:-7:-3`, every operand (quick tier + 2 bits) | 4 124 961 | 1 593 537 | 0 | 0.898829 | - |
| `fp:4:-9:-3`, every operand (p = min_precision, another exponent range) | 3 038 049 | 2 716 377 | 0 | 0.850806 | - |
| `fp:5:-7:-3`, every operand (p = min_precision + 1, quick tier + 1 bit) | 1 014 049 | 606 801 | 0 | 0.864716 | - |
| `fp:4:-7:-3`, every operand (p = min_precision, the quick tier's format) | 245 025 | 209 281 | 0 | 0.791964 | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.979252 (clang/cxx, macos-arm64):
  mul_2_2 binary64 -0x1.9acb06cd2a37ep-538 -0x1p-595 0x1.1b353f20ae742p-462 -0x1.531851cdfa1c3p-518 #underflow:807027 -> -0x1.c673e1d99e233p-1000 0x1.301cp-1055
largest error / bound, interpreter 0.898829 (fp:6:-7:-3, every operand):
  mul_2_2 fp:6:-7:-3 -0x1.2p-1 0x1p-7 -0x1.2p-1 0x1p-7 #exhaustive:1918208 -> 0x1.3p-2 0x0p+0
```

### `mul_pow2_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=1`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 61 402 136 | 0 | 0.749144 | 4.87349e-17 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 61 583 944 | 0 | 0.750000 | 2.98023e-8 |
| `fp:6:-12:4`, every operand (another exponent range) | 6 021 994 | 4 488 874 | 0 | 0.746094 | 0.00781249 |
| `fp:7:-6:2`, every operand (quick tier + 2 bits) | 979 185 | 521 971 | 0 | 0.734375 | - |
| `fp:3:-6:2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 14 949 | 11 829 | 0 | 0.71875 | 0.0624390 |
| `fp:2:-6:2`, every operand (p = min_precision, the quick tier's exponent range) | 4 350 | 3 766 | 0 | 0.6875 | 0.124031 |
| `fp:6:-6:2`, every operand (quick tier + 1 bit) | 398 706 | 231 604 | 0 | 0.734375 | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.750000 (clang18/avx2, linux-x86-64):
  mul_pow2_2 binary32 -0x1.84dc7ep-78 0x1.fffffep-103 0x1p-49 #extreme:940674 -> -0x1.84dc8p-127 0x0p+0
largest error / bound, interpreter 0.746094 (fp:6:-12:4, every operand):
  mul_pow2_2 fp:6:-12:4 -0x1.f8p+4 0x1.f8p-3 0x1p-12 #exhaustive:2032404 -> -0x1p-7 0x0p+0
```

### `neg_2`

Claims: `normalized(z)`; `error(z) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | 0 (exact) | 0 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 600 000 | 0 | 0 (exact) | 0 |
| `fp:8:-20:2`, every operand (another exponent range) | 7 926 015 | 7 926 015 | 0 | 0 (exact) | 0 |
| `fp:7:-8:4`, every operand (quick tier + 1 bit) | 359 679 | 359 679 | 0 | 0 (exact) | - |
| `fp:3:-8:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 3 503 | 3 503 | 0 | 0 (exact) | 0 |
| `fp:2:-8:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 027 | 1 027 | 0 | 0 (exact) | 0 |
| `fp:8:-8:4`, every operand (quick tier + 2 bits) | 1 047 295 | 1 047 295 | 0 | 0 (exact) | - |

### `radd`

Claims: `upper(r) gaps=3/2`.

| Run | Cases | Judged | Failed | largest excess, gaps (claim 3/2) |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 70 400 000 | 64 855 024 | 0 | 1.5 (the claim) |
| `binary32`, 40 runners on 3 machines | 70 400 000 | 64 769 928 | 0 | 1.5 (the claim) |
| `fp:8:-14:2`, every operand (another exponent range) | 5 308 416 | 5 238 911 | 0 | 1.5 (the claim) |
| `fp:8:-8:4`, every operand (quick tier + 2 bits) | 3 211 264 | 3 142 783 | 0 | 1.5 (the claim) |
| `fp:7:-8:4`, every operand (quick tier + 1 bit) | 802 816 | 784 959 | 0 | 1.5 (the claim) |
| `fp:3:-8:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 3 136 | 2 979 | 0 | 1.5 (the claim) |
| `fp:2:-8:4`, every operand (p = min_precision, the quick tier's exponent range) | 784 | 721 | 0 | 1.25 |

Where the extremes are attained (the line as the oracle reports it):

```
largest excess, gaps (claim 3/2), compiled 1.5 (clang18/avx2, linux-x86-64):
  radd binary64 0x1.c36ba8f4842f9p-569 0x1.00c85de086de4p-572 #close:146 -> 0x1.e384b4b0950b7p-569
largest excess, gaps (claim 3/2), interpreter 1.5 (fp:8:-14:2, every operand):
  radd fp:8:-14:2 0x1p-14 0x1.02p-6 #exhaustive:2561 -> 0x1.06p-6
```

### `rmul`

Claims: `upper(r) gaps=3/2`.

| Run | Cases | Judged | Failed | largest excess, gaps (claim 3/2) |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 70 400 000 | 64 545 768 | 0 | 1.5 (the claim) |
| `binary32`, 40 runners on 3 machines | 70 400 000 | 64 186 824 | 0 | 1.5 (the claim) |
| `fp:8:-8:4`, every operand (another exponent range) | 3 211 264 | 2 009 236 | 0 | 1.5 (the claim) |
| `fp:8:-13:-2`, every operand (quick tier + 2 bits) | 2 768 896 | 2 462 794 | 0 | 1.5 (the claim) |
| `fp:7:-13:-2`, every operand (quick tier + 1 bit) | 692 224 | 638 684 | 0 | 1.5 (the claim) |
| `fp:3:-13:-2`, every operand (p = min_precision + 1, the quick tier's exponent range) | 2 704 | 2 694 | 0 | 1.5 (the claim) |
| `fp:2:-13:-2`, every operand (p = min_precision, the quick tier's exponent range) | 676 | 676 | 0 | 1.5 (the claim) |

Where the extremes are attained (the line as the oracle reports it):

```
largest excess, gaps (claim 3/2), compiled 1.5 (clang18/avx2, linux-x86-64):
  rmul binary64 0x1.4p-1072 0x1.20ae101f25516p+627 #close:89290 -> 0x1.68d99426eea5dp-445
largest excess, gaps (claim 3/2), interpreter 1.5 (fp:8:-8:4, every operand):
  rmul fp:8:-8:4 0x1p-8 0x1.8p+0 #exhaustive:2112 -> 0x1.8p-7
```

### `split`

Claims: `error(r) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 68 800 000 | 60 885 344 | 0 | 0 (exact) | 0 |
| `binary32`, 40 runners on 3 machines | 68 800 000 | 59 523 208 | 0 | 0 (exact) | 0 |
| `fp:13:-60:40`, every operand (another exponent range) | 835 583 | 778 111 | 0 | 0 (exact) | 0 |
| `fp:13:-30:10`, every operand (quick tier + 2 bits) | 344 063 | 286 591 | 0 | 0 (exact) | 0 |
| `fp:12:-30:10`, every operand (quick tier + 1 bit) | 172 031 | 147 329 | 0 | 0 (exact) | 0 |
| `fp:5:-30:10`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 343 | 1 239 | 0 | 0 (exact) | 0 |
| `fp:4:-30:10`, every operand (p = min_precision, the quick tier's exponent range) | 671 | 633 | 0 | 0 (exact) | 0 |

### `sub_1_2`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 64 298 792 | 0 | 0.985325 | 1.97065 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 64 288 160 | 0 | 0.828806 | 1.65761 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.985325 (clang/cxx, macos-arm64):
  sub_1_2 binary64 -0x1.fbf18dc0db0cdp+762 -0x1.00e46db61d70ep+764 0x1.0000000000001p+710 #close:804168 -> 0x1.03d0148bcd5b5p+763 0x0p+0
largest error / bound, interpreter 0.939450 (fp:5:-6:3, every operand):
  sub_1_2 fp:5:-6:3 -0x1.fp+5 -0x1p+7 -0x1.1p+1 #exhaustive:521550 -> 0x1.1p+6 0x0p+0
```

### `sub_2_1`

Claims: `normalized(z)`; `error(z) form R, c=2, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 64 300 272 | 0 | 0.980874 | 1.96175 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 64 285 736 | 0 | 0.974543 | 1.94909 |
| `fp:5:-6:3`, every operand (another exponent range) | 5 694 273 | 5 413 403 | 0 | 0.939450 | - |
| `fp:6:-4:2`, every operand (quick tier + 2 bits) | 4 152 897 | 3 760 105 | 0 | 0 | - |
| `fp:4:-7:4`, every operand (p = min_precision + 1, another exponent range) | 1 934 001 | 1 874 893 | 0 | 0.882759 | 1.76552 |
| `fp:5:-4:2`, every operand (quick tier + 1 bit) | 1 027 905 | 929 595 | 0 | 0.939450 | - |
| `fp:4:-4:2`, every operand (p = min_precision + 1, the quick tier's format) | 221 361 | 201 957 | 0 | 0.882759 | - |
| `fp:3:-4:2`, every operand (p = min_precision, the quick tier's exponent range) | 42 273 | 38 935 | 0 | 0.780488 | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.980874 (clang18/avx2, linux-x86-64):
  sub_2_1 binary64 -0x1.027ef03a9a1b9p+1022 0x1.67566a9ef8a43p+968 -0x1.ffffffffffffdp+1020 #overflow:272974 -> -0x1.04fde07534373p+1021 0x1.9d59aa7be291p+966
largest error / bound, interpreter 0.939450 (fp:5:-6:3, every operand):
  sub_2_1 fp:5:-6:3 -0x1p+7 -0x1.1p+1 -0x1.fp+5 #exhaustive:847346 -> -0x1.1p+6 0x0p+0
```

### `sub_2_2`

Claims: `normalized(z)`; `error(z) form R, c=3/(1-4*u), k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 64 292 904 | 0 | 0.663134 | 1.98940 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 64 285 688 | 0 | 0.726732 | 2.18020 |
| `fp:4:-4:3`, every operand (p = min_precision + 1, another exponent range) | 7 568 001 | 6 204 503 | 0 | 0.536013 | - |
| `fp:3:-6:4`, every operand (p = min_precision, another exponent range) | 5 303 809 | 4 882 595 | 0 | 0.360255 | 2.16153 |
| `fp:5:-3:2`, every operand (quick tier + 2 bits) | 4 060 225 | 3 027 339 | 0 | 0.556176 | - |
| `fp:4:-3:2`, every operand (p = min_precision + 1, quick tier + 1 bit) | 982 081 | 728 391 | 0 | 0.453901 | - |
| `fp:3:-3:2`, every operand (p = min_precision, the quick tier's format) | 178 929 | 138 027 | 0 | 0.273504 | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound, compiled 0.726732 (clang/cxx, macos-arm64):
  sub_2_2 binary32 -0x1.7d99cep-50 0x1.fffffep-75 -0x1.d59e1cp-52 -0x1.fffffep-77 #extreme:529578 -> -0x1.083246p-50 0x1.000004p-76
largest error / bound, interpreter 0.556176 (fp:5:-3:2, every operand):
  sub_2_2 fp:5:-3:2 -0x1.ep+6 0x1p+1 -0x1.9p+5 -0x1.cp-1 #exhaustive:127545 -> -0x1.1p+6 0x1p+0
```

### `to_down_2`

Claims: `rounded(t) down`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 270 616 | 0 | exact 18 700 600, inexact, as RN 23 460 688, differs from RN 23 109 328 |
| `binary32`, 40 runners on 3 machines | 62 400 000 | 62 086 904 | 0 | exact 19 077 960, inexact, as RN 21 656 792, differs from RN 21 352 152 |
| `fp:8:-20:2`, every operand (another exponent range) | 7 926 015 | 7 924 096 | 0 | exact 6 143, inexact, as RN 3 959 936, differs from RN 3 958 017 |
| `fp:7:-8:4`, every operand (quick tier + 1 bit) | 359 679 | 359 296 | 0 | exact 1 791, inexact, as RN 178 944, differs from RN 178 561 |
| `fp:3:-8:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 3 503 | 3 464 | 0 | exact 111, inexact, as RN 1 696, differs from RN 1 657 |
| `fp:2:-8:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 027 | 1 006 | 0 | exact 55, inexact, as RN 486, differs from RN 465 |
| `fp:8:-8:4`, every operand (quick tier + 2 bits) | 1 047 295 | 1 046 656 | 0 | exact 3 583, inexact, as RN 521 856, differs from RN 521 217 |

### `to_nearest_2`

Claims: `rounded(t) nearest`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 62 400 000 | 62 400 000 | 0 | exact 17 786 024, inexact 24 959 760, tie 19 654 216 |
| `binary32`, 40 runners on 3 machines | 62 400 000 | 62 400 000 | 0 | exact 19 055 528, inexact 24 124 048, tie 19 220 424 |
| `fp:8:-20:2`, every operand (another exponent range) | 7 926 015 | 7 926 015 | 0 | exact 6 143, inexact 7 914 242, tie 5 630 |
| `fp:8:-8:4`, every operand (quick tier + 2 bits) | 1 047 295 | 1 047 295 | 0 | exact 3 583, inexact 1 040 642, tie 3 070 |
| `fp:7:-8:4`, every operand (quick tier + 1 bit) | 359 679 | 359 679 | 0 | exact 1 791, inexact 356 354, tie 1 534 |
| `fp:3:-8:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 3 503 | 3 503 | 0 | exact 111, inexact 3 298, tie 94 |
| `fp:2:-8:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 027 | 1 027 | 0 | exact 55, inexact 926, tie 46 |

### `to_up_2`

Claims: `rounded(t) up`.

| Run | Cases | Judged | Failed | cases by rounding |
|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 65 271 520 | 0 | exact 18 712 752, inexact, as RN 23 435 616, differs from RN 23 123 152 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 65 268 912 | 0 | exact 20 060 512, inexact, as RN 22 769 720, differs from RN 22 438 680 |
| `fp:8:-20:2`, every operand (another exponent range) | 7 926 015 | 7 924 096 | 0 | exact 6 143, inexact, as RN 3 959 936, differs from RN 3 958 017 |
| `fp:8:-8:4`, every operand (quick tier + 2 bits) | 1 047 295 | 1 046 656 | 0 | exact 3 583, inexact, as RN 521 856, differs from RN 521 217 |
| `fp:7:-8:4`, every operand (quick tier + 1 bit) | 359 679 | 359 296 | 0 | exact 1 791, inexact, as RN 178 944, differs from RN 178 561 |
| `fp:3:-8:4`, every operand (p = min_precision + 2, the quick tier's exponent range) | 3 503 | 3 464 | 0 | exact 111, inexact, as RN 1 696, differs from RN 1 657 |
| `fp:2:-8:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 1 027 | 1 006 | 0 | exact 55, inexact, as RN 486, differs from RN 465 |

### `two_prod`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=1/2`; `error(r) form R, c=0, k=2, t=0, when product_large`.

| Run | Cases | Judged | Failed | largest error / bound (c=0, k=2, t=1/2) | observed c | largest error / bound (c=0, k=2, t=0, when product_large) | observed c |
|---|---|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 68 800 000 | 65 922 192 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 62 859 712 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:7:-20:-6`, every operand (another exponent range) | 4 190 209 | 4 180 293 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 2 197 485 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 2 460 313 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 637 481 | 0 | 1 (the claim) | - | 0 (exact) | - |
| `fp:3:-12:-1`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 481 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |
| `fp:2:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 597 | 0 | 1 (the claim) | 0 | 0 (exact) | 0 |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound (c=0, k=2, t=1/2), compiled 1 (clang18/avx2, linux-x86-64):
  two_prod binary64 0x1.8p+0 0x1p-1074 #extreme:50118 -> 0x0.0000000000002p-1022 -0x0p+0
largest error / bound (c=0, k=2, t=1/2), interpreter 1 (fp:7:-20:-6, every operand):
  two_prod fp:7:-20:-6 -0x1.fcp+0 -0x1.fcp-9 #exhaustive:576 -> 0x1.f8p-8 0x0p+0
```

### `two_prod_dekker`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=13/8`; `error(r) form R, c=0, k=2, t=0, when product_large`.

| Run | Cases | Judged | Failed | largest error / bound (c=0, k=2, t=13/8) | observed c | largest error / bound (c=0, k=2, t=0, when product_large) | observed c |
|---|---|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 58 648 440 | 0 | 0.921384 | 0 | 0 (exact) | 0 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 55 122 824 | 0 | 0.929436 | 0 | 0 (exact) | 0 |
| `fp:7:-20:-6`, every operand (another exponent range) (**stopped by a finding**: the interpreter exited with 2) | 0 | 0 | 0 | - | - | - | - |
| `fp:7:-8:4`, every operand (another exponent range) | 3 207 681 | 1 526 625 | 0 | 0.903846 | - | 0 (exact) | - |
| `fp:7:-12:-1`, every operand (quick tier + 2 bits) | 2 765 569 | 1 288 225 | 0 | 0.943510 | - | 0 (exact) | - |
| `fp:6:-12:-1`, every operand (quick tier + 1 bit) | 690 561 | 390 625 | 0 | 0.887019 | - | 0 (exact) | - |
| `fp:4:-12:-1`, every operand (p = min_precision, the quick tier's exponent range) | 42 849 | 28 561 | 0 | 0.788462 | 0 | 0 (exact) | 0 |
| `fp:5:-12:-1`, every operand (p = min_precision + 1, the quick tier's format) | 172 225 | 96 721 | 0 | 0.889423 | - | 0 (exact) | - |

Where the extremes are attained (the line as the oracle reports it):

```
largest error / bound (c=0, k=2, t=13/8), compiled 0.929436 (msvc/avx2, windows-x64):
  two_prod_dekker binary32 -0x1.642b7p-87 -0x1.1bac52p-41 #underflow:334100 -> 0x1.8aabc80000000p-128 -0x1.0000000000000p-148
largest error / bound (c=0, k=2, t=13/8), interpreter 0.943510 (fp:7:-12:-1, every operand):
  two_prod_dekker fp:7:-12:-1 -0x1.a4p-3 -0x1.a4p-6 #exhaustive:888768 -> 0x1.6p-8 -0x1p-11
```

### `two_sum`

Claims: `leading_rounded(r)`; `error(r) form R, c=0, k=2, t=0`.

| Run | Cases | Judged | Failed | largest error / bound | observed c |
|---|---|---|---|---|---|
| `binary64`, 40 runners on 3 machines | 65 600 000 | 63 919 528 | 0 | 0 (exact) | 0 |
| `binary32`, 40 runners on 3 machines | 65 600 000 | 63 923 800 | 0 | 0 (exact) | 0 |
| `fp:7:-14:2`, every operand (another exponent range) | 5 303 809 | 5 271 107 | 0 | 0 (exact) | 0 |
| `fp:7:-7:4`, every operand (quick tier + 2 bits) | 2 765 569 | 2 732 867 | 0 | 0 (exact) | - |
| `fp:6:-7:4`, every operand (quick tier + 1 bit) | 690 561 | 682 403 | 0 | 0 (exact) | - |
| `fp:3:-7:4`, every operand (p = min_precision + 1, the quick tier's exponent range) | 10 609 | 10 487 | 0 | 0 (exact) | 0 |
| `fp:2:-7:4`, every operand (p = min_precision, the quick tier's exponent range) | 2 601 | 2 573 | 0 | 0 (exact) | 0 |

## What was not run, and why

- **`two_prod_dekker` at `fp:7:-20:-6`**, the one run stopped by a finding, which is a fault of
  this tier's plan: the interpreter refuses the kernel on the first line ("constant splitter = 17
  is not a number of the format (7, -20, -6)"), since the format's largest number, 127/64, is
  below the splitter $2^{\lceil p/2\rceil} + 1 = 17$. The claims, which assume that nothing
  overflows, say nothing about such a format, and the oracle generates its cases all the same.
  The plan now leaves out every format without the splitter for `split` and `two_prod_dekker`;
  the other formats of `two_prod_dekker` ran. To see it:

    ```sh
    python3 oracle/kairn-oracle gen two_prod_dekker fp:7:-20:-6 --exhaustive --count 1 \
      | python3 gen/kairn-gen interp
    ```

- **$10^8$ judged cases per kernel and format.** That was the aim, summed over the machines; the
  runs reached 49 to 70 million (63 million on average). The oracle judges $10^4$ to $10^5$ lines
  per second per process (Python, exact integer arithmetic), the budget was about 90 minutes per
  machine, and the enumerations took about half an hour of the Linux machine and of the Mac. The
  driver extends a run where it stopped (`run` again on the same work directory with a larger
  budget); at the Linux machine's rate here, about one more hour of it would reach $10^8$ for
  every kernel and format.
- **Precision 1.** Eighteen kernels claim `min_precision` 1, but the oracle reads no format of
  precision 1: `python3 oracle/kairn-oracle gen add_1_1 fp:1:-4:3 --exhaustive --total` exits
  with "precision must be at least 2, got 1", and `check` fails a line of such a format as an
  unknown format. Their enumerations start at precision 2. The claims at precision 1 are proved
  but tested nowhere, here as in the quick tier.
- **Every operand of the quick tier's formats of the two-limb balls with two operands**: 140
  million combinations each for `ball_add_2` and `ball_sub_2` at `fp:3:-3:2`, 12.4 billion for
  `ball_mul_2` at `fp:4:-5:1`. In their place, every operand of formats of the same precision
  with fewer exponents, and the restricted domains of their tables, which are larger than the
  quick tier's (148 896 and 64 728 cases).
- **Formats three bits above the quick tier's** were sized and left out, to leave the time to
  the compiled runners.
- **Other compilers and targets**: clang-cl is not installed on the Windows machine, no machine
  has AVX-512, and no other backend is part of Milestone 1.
- **The interpreter's variants**: `--muladd unfused` would change nothing (no kernel of
  Milestone 1 has a `muladd`), and `--ce` runs `two_prod_dekker` in place of `two_prod`, whose
  own enumerations are above.
- **Suspicious results of `split` and `two_prod_dekker`** do not fail their runs, as in the quick
  tier: their product by the splitter overflows for operands far below the largest number, which
  their requirement of no intermediate overflow allows. Their runs are still held to the guards.
- **Narrow exponent ranges judge few of their cases.** At `fp:4:-2:0`, for instance, most
  products of `ball_mul_2` exceed the format and the results are not finite, about which the
  claims say nothing: 357 055 of 15 492 096 cases are judged. The kernel's other
  enumerations judge 15 % to 64 % of theirs, and the column "Judged" of each table shows it for
  every kernel.
