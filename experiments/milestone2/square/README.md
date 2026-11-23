# A square of the program loses its guard

Every value of `T` that a program passes to Kairn goes through a *guard*, `a + 0`, before a
kernel adds it (rule R3): a product of the program is then rounded on its own and cannot be fused
into the kernel's error-free sums. The guard rests on the compiler keeping `a + 0`, which differs
from `a` for `a = -0` only. LLVM removes `x + 0.0` when it can prove `x` is never `-0`, and it
proves that for a square `x * x`; under `-ffp-contract=fast` it then fuses the square into the
kernel's first addition, and the operation computes with the exact square in place of the
rounded one. The programs here measure which expressions, which compilers and which public
operations of Kairn are affected, and what the flags that the headers refuse or accept do to it.
They were written and run on 2026-11-23; nothing in the library, the generator or the tests was
changed for them.

| File | What it is |
|---|---|
| `square_plain.cpp` | No Kairn header: the guard and a two-sum written out as the generated kernels write them, in scalar code and with AVX2 or AArch64 intrinsics; a list of expressions passed straight in, each against the same expression rounded first. Builds with GCC, Clang and MSVC. |
| `run_plain.sh OUTDIR CXX [FLAGS]` | `square_plain.cpp` at `-O1`, `-O2`, `-O3` under each contraction setting (default, off, on, fast): one line per build with the expressions that differed. |
| `square_kairn.cpp` | Every public route by which a value of `T` enters Kairn, with a square written in the call against the same call on the rounded square, on three families of operands; the differing cases printed for `check.py`. |
| `check.py` | Judges each printed case in exact arithmetic (Python `fractions`): does the result with the square in place violate what the operation claims of the values the program passed, or only differ in bits? The rounded-first result is judged too, as a control. |
| `run_kairn.sh OUTDIR INCLUDE CXX [FLAGS]` | `square_kairn.cpp` and `check.py` over the same matrix of levels and contraction settings. |
| `self_test.cpp`, `run_flags.sh OUTDIR INCLUDE CXX [FLAGS]` | For `-fno-signed-zeros`, `-fassociative-math`, `-funsafe-math-optimizations`, `-ffast-math` (alone and with `-ffp-contract=fast`): whether the headers refuse the flag, what `kairn::self_test()` says, and what the two probes show. |

## Running them

```
sh run_plain.sh out c++                        # and g++, clang++ -mavx2 -mfma, ...
sh run_kairn.sh out ../../../include c++       # add -DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR for the scalar form
sh run_flags.sh out ../../../include c++
```

With MSVC (not run here; the commands for it):

```
cl /std:c++20 /EHsc /O2 /fp:precise  square_plain.cpp && square_plain
cl /std:c++20 /EHsc /O2 /fp:contract square_plain.cpp && square_plain
cl /std:c++20 /EHsc /O2 /fp:fast     square_plain.cpp && square_plain
```

each also with `/arch:AVX2`, which adds the AVX2 rows. A line `differs in 0 of 20000` means the
guard held for that expression; any other count means the product was fused into the sum (the
first such case is printed after it). The last line sums them.

## Which expressions lose the guard (`square_plain.cpp`)

Measured with Apple clang 21.0.0 and Homebrew GCC 16.2.0 on an Apple M3 Max (AArch64, the NEON
rows), and with GCC 13.3.0 and Clang 18.1.3 on an AMD EPYC (Zen 2, x86-64), with `-mfma` and with
`-mavx2 -mfma` (the AVX2 rows); 20000 cases per row, double and float.

| Expression passed to `two_sum(c, p)` | Apple clang 21 | Clang 18 (x86-64) | GCC 13, GCC 16 |
|---|---|---|---|
| `a * a`, `pow(a, 2)`, `(a - b) * (a - b)` | fused, double and float, scalar and NEON, at `-O1` and `-O2` under `-ffp-contract=fast`; not at `-O3`, not under default, `off` or `on` | not fused into the two-sum (but see below) | never |
| `a * b`; `fabs(a) * fabs(b)`; `a * b` under `if (a > 0 && b > 0)`; `0.75 * fabs(a)`; `0.75 * a` under `if (a > 0)`; `T(ua) * T(ub)` of unsigned integers, `T(ia) * T(ib)` of signed; `sqrt(a) * sqrt(b)`; `(a * a) * (b * b)`; `(a * a) * b`; `exp(a - 1) * exp(b - 1)` | never | never | never |

The analysis is LLVM's floating-point class inference (`computeKnownFPClass`, in
`llvm/lib/Analysis/ValueTracking.cpp`), which InstSimplify consults to fold `fadd X, +0.0` to `X`
when `X` cannot be `-0` (`cannotBeNegativeZero`). Of the products, it knows only `fmul X, X` (the
same operand twice) to be never negative; it does not combine the signs of two factors, so a
product of two values known positive keeps its guard, in Apple clang 21 as in Clang 18. A
conversion from an integer is known never `-0` too, so its guard goes as well; that is harmless,
since it is not a product and nothing can be fused into it. In a compiled `x * x + 0.0` alone only
the multiplication is left, with both compilers.

The fused multiply-add is formed later, by the instruction selector, which fuses a product into
an addition when contraction is `fast` (contraction `on` fuses only within one expression, and the
guard and the kernel's sum are other expressions). On x86-64 Clang 18 fuses a product into an
addition only when the product has no other use, which is why `two_sum`, whose operand is used four
times, keeps a separate multiplication there; on AArch64 Apple clang fuses a product that has
several uses too, once into each addition (`fmadd` and `fmsub` from one square). A two-line check
shows both: `double p = x * x + 0.0; double s = c + p; return s - p;` is `fmadd`, `fmsub` with Apple
clang and `vmulsd`, `vaddsd`, `vsubsd` with Clang 18; `return c + (x * x + 0.0)` is one FMA with
both.

## Which operations of Kairn are reached (`square_kairn.cpp`)

The same matrix (four compilers, `-O1`/`-O2`/`-O3`, the four contraction settings, double and
float), in the native form of `Packed` (NEON, AVX2) and in the scalar form
(`KAIRN_PACKED_FORM_SCALAR`). Each row runs 4000 cases in each of three families of operands:
*cancel* (`c` within a few units of `-RN(a*a)`), *same* (`c` within a few units of `+RN(a*a)`) and
*mixed* (`c` of either sign, within a factor 4 of the square); the first 25 differing cases of
each family are judged by `check.py`. GCC 13 and GCC 16 never differ, in any build; nothing differs
under contraction default, `off` or `on`, with any compiler. Every difference below is under
`-ffp-contract=fast`; the control (the rounded square) never violates.

| Form | Fused by (under `-ffp-contract=fast`, levels) | One case (double): p = RN(a*a), c | Squares in place | Rounded first | Claim; can the fused result violate it? |
|---|---|---|---|---|---|
| `two_sum(c, a*a)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.babb1400d98d3p-1, c = -0x1.babb1407c4798p-1 | -0x1.babb13e80368cp-31, 0x1.7fc9739d452p-59 | -0x1.babb14p-31, 0x0p+0 | the pair is exact: yes |
| `two_sum(a*a, c)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.22f0b95c8b989p-1, c = -0x1.22f0b961175b7p-1 | -0x1.22f0b8584683cp-31, -0x1.611a0f00ac9ep-57 | -0x1.22f0b8p-31, 0x0p+0 | the pair is exact: yes |
| `fast_two_sum(c, a*a)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.e91dc7937f561p-2, c = -0x1.e91dc79b23cd3p-2 | -0x1.e91dc700d4b95p-32, 0x1.fe568d6cdac8p-57 | -0x1.e91dc8p-32, 0x0p+0 | the pair is exact: yes |
| `add_down(c, a*a)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.1024fb91b8642p-1, c = -0x1.1024fb95f8f81p-1 | -0x1.1024fb0295f8dp-31 | -0x1.1024fcp-31 | rounded down: yes |
| `add_up(c, a*a)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.eef49fadfdcecp-2, c = -0x1.eef49fb5b9a14p-2 | -0x1.eef4a13f04929p-32 | -0x1.eef4ap-32 | rounded up: yes |
| `two_prod(a*a, 1)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.64a65a908f8fep-1, c = -0x1.64a65a9622295p-1 | 0x1.64a65a908f8fep-1, -0x1.54579b7c559cp-56 | 0x1.64a65a908f8fep-1, 0x0p+0 | the pair is exact: yes |
| `mul_down(a*a, 1)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.856cfc4a2809fp-2, c = -0x1.856cfc503dbdep-2 | 0x1.856cfc4a2809ep-2 | 0x1.856cfc4a2809fp-2 | rounded down: not in the cases judged |
| `mul_up(a*a, 1)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.6b1320b670e53p-2, c = -0x1.6b1320c1c97e3p-2 | 0x1.6b1320b670e54p-2 | 0x1.6b1320b670e53p-2 | rounded up: not in the cases judged |
| `Expansion<T, 2>(c) + a*a` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.07f267b423327p-2, c = -0x1.07f267b842fc1p-2 | -0x1.07f26ab8fc42ap-32, 0x1.02a91p-86 | -0x1.07f268p-32, 0x0p+0 | error bound: yes |
| `a*a + Expansion<T, 2>(c)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.97c237bb1075p-1, c = -0x1.97c237c16f7dep-1 | -0x1.97c237e52437ep-31, 0x1.ff4c8p-85 | -0x1.97c238p-31, 0x0p+0 | error bound: yes |
| `Expansion<T, 2>(c) - a*a` | none | | | | |
| `x += a*a` (two limbs) | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.96767a0cba898p-2, c = -0x1.96767a1314637p-2 | -0x1.96767807b1f9ep-32, -0x1.0287p-86 | -0x1.96767cp-32, 0x0p+0 | error bound: yes |
| `finite::add(x, a*a)` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.bad778f2276e7p-2, c = -0x1.bad778f912cc5p-2 | -0x1.bad777b7c7ff6p-32, 0x1.5e488p-87 | -0x1.bad778p-32, 0x0p+0 | error bound: yes |
| `Expansion<T, 2>(a*a) + y` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.8ab11bbdbeeeap-1, c = -0x1.8ab11bc3e9b31p-1 | -0x1.8ab11e9da35dep-31, -0x1.c04378p-85 | -0x1.8ab11cp-31, 0x0p+0 | error bound: yes |
| `Expansion<T, 2>::from_limbs({a*a, 0}) + y` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.dbc24b5371059p-1, c = -0x1.dbc24b5ae00ecp-1 | -0x1.dbc24d9ce0f02p-31, 0x1.ca52p-85 | -0x1.dbc24cp-31, 0x0p+0 | error bound: yes |
| `Expansion<T, 2>(1) * (a*a) + y` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.1990f01e04e9bp-2, c = -0x1.1990f0226b2d7p-2 | -0x1.1990f18fc300cp-32, 0x1.b8c8p-86 | -0x1.1990fp-32, 0x0p+0 | error bound: yes |
| `Interval<T, 1>(a*a, a*a) + Y` | none | | | | |
| `Interval<T, 2>(a*a, a*a) + Y` | none | | | | |
| `Ball<T, 1>(a*a, 0) + Y` | none | | | | |
| `Ball<T, 1>(0, a*a) + Y` (a radius) | none | | | | |
| `Ball<T, 2>(a*a, 0) + Y` | none | | | | |
| `Ball<T, 1>(c, 0) + a*a` | none | | | | |
| `Ball<T, 2>(c, 0) + a*a` | none | | | | |
| `Ball<T, 2>(1, 0) * (a*a) + Y` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.114ef31f43334p-1, c = -0x1.114ef323886f1p-1 | -0x1.114ef61ab6dcfp-31 + -0x1.ceep-90, r 0x1.114ef325ab0d4p-106 | -0x1.114ef4p-31 + 0x0p+0, r 0x1.114ef325ab0d5p-106 | enclosure: yes |
| `Packed<T, 1>::load(c) + Packed<T, 1>::load(squares)` | Apple clang 21, NEON form -O2/3; Apple clang 21, scalar form -O1/2/3; Clang 18, AVX2 form -O2/3; Clang 18, scalar form -O1/2/3 | p = 0x1.55625000f2df3p-1, c = -0x1.5562500648687p-1 | -0x1.55624fe9fc766p-31 | -0x1.55625p-31 | rounded to nearest: yes |
| `Packed<T, 1>::broadcast(c) + Packed<T, 1>::broadcast(a*a)` | Apple clang 21, NEON form -O1/2/3; Apple clang 21, scalar form -O1/2/3; Clang 18, AVX2 form -O1/2/3; Clang 18, scalar form -O1/2/3 | p = 0x1.239b17c15d07ap-1, c = -0x1.239b17c5eb74p-1 | -0x1.239b183289607p-31 | -0x1.239b18p-31 | rounded to nearest: yes |
| `Packed<T, 2> + Packed<T, 1>::load(squares)` | Apple clang 21, scalar form -O1/2 | p = 0x1.e5effa1a15ea9p-1, c = -0x1.e5effa21adaa8p-1 | -0x1.e5effe80d60f2p-31, -0x1.e0ep-89 | -0x1.e5effcp-31, 0x0p+0 | error bound: yes |
| `Accumulator<T, 1>`: `add(a*a)`, `add(c)`, `ball()` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.1e408d2854717p-1, c = -0x1.1e408d2ccd73ap-1 | -0x1.1e408d27b85a8p-31 + 0x0p+0, r 0x1.1e408d2a90f33p-52 | -0x1.1e408cp-31 + 0x0p+0, r 0x1.1e408d2a90f33p-52 | enclosure: not in the cases judged |
| `Accumulator<T, 2>`: `add(a*a)`, `add(c)`, `ball()` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.f6f7036ecebdap-1, c = -0x1.f6f70376aa99bp-1 | -0x1.f6f7038ad8af3p-31 + -0x1.14d7p-86, r 0x1.f6f70372bcaccp-103 | -0x1.f6f704p-31 + 0x0p+0, r 0x1.f6f70372bcaccp-103 | enclosure: yes |
| `Accumulator<T, 1>`: `add_product(a*a, 1)`, `add(c)`, `ball()` | Apple clang 21, NEON form -O1/2; Apple clang 21, scalar form -O1/2 | p = 0x1.3e9ae931336bep-2, c = -0x1.3e9ae9362dd78p-2 | -0x1.3e9ae643f19d8p-32 + 0x0p+0, r 0x1.3e9ae933b0a27p-53 | -0x1.3e9ae8p-32 + 0x0p+0, r 0x1.3e9ae933b0a27p-53 | enclosure: not in the cases judged |
| `sum` of 8 (squares and c), one limb | Apple clang 21, scalar form -O2/3; Clang 18, scalar form -O2/3 | p = 0x1.e9302e815008p-1, c = -0x1.e9302e983e4a3p-1 (and three more pairs) | -0x1.90d497p-27 | -0x1.90d4974p-27 | error bound of the sum: not in the cases judged |
| `sum(sequential, ...)`, one limb | Apple clang 21, NEON form -O2/3; Apple clang 21, scalar form -O2/3; Clang 18, AVX2 form -O2/3; Clang 18, scalar form -O2/3 | p = 0x1.53655d161b158p-1, c = -0x1.53655d20b6407p-1 (and three more pairs) | -0x1.035db1p-27 | -0x1.035db0cp-27 | error bound of the sum: not in the cases judged |
| `sum`, two limbs | none | | | | |
| `add(squares, c, z)` on arrays | Apple clang 21, scalar form -O2/3; Clang 18, AVX2 form -O2/3; Clang 18, scalar form -O2/3 | p = 0x1.c6dcb84110147p-1, c = -0x1.c6dcb8482b875p-1 | -0x1.c6dcb674c5508p-31 | -0x1.c6dcb8p-31 | rounded to nearest: yes |
| `dot(squares and c, ones)` | Clang 18, scalar form -O2/3 | p = 0x1.9107c0a4a07b4p-1, c = -0x1.9107c0b128b94p-1 (and three more pairs) | -0x1.31217cp-27 | -0x1.31217c4p-27 | error bound of the sum: not in the cases judged |
| `axpy(1, c, squares, z)` | Apple clang 21, scalar form -O2/3; Clang 18, AVX2 form -O2/3; Clang 18, scalar form -O2/3 | p = 0x1.f3381cbf2afc3p-1, c = -0x1.f3381cc6f7dcap-1 | -0x1.f3381b5f54665p-31 | -0x1.f3381cp-31 | rounded to nearest: yes |
| `BallVector<T, 1, 4>(squares, 0) + Y` | none | | | | |
| `BallVector<T, 2, 4>(squares, 0) + Y` | none | | | | |

What the table shows:

- **Apple clang 21** at `-O1` and `-O2` drops the guard of a square in every route of the building
  blocks, of `Expansion<T, 2>` with a `T`, of its constructors and `from_limbs`, of a product by a
  number whose value the compiler sees (the factor of a fused operation: `two_prod(a*a, 1)`,
  `Expansion<T, 2>(1) * (a*a)`, `Ball<T, 2>(1) * (a*a)`, `add_product(a*a, 1)`), and of both
  accumulators; at `-O3` only the sums of `Packed<T, 1>` and the functions on arrays. In the
  scalar form of `Packed` it also reaches `Packed<T, 2> + Packed<T, 1>`, and the functions on arrays
  (`sum`, `add`, `axpy`) over an array the program filled with squares in the same function.
- **Clang 18 on x86-64** fuses only where the square has one use in the kernel: `x + y` of
  `Packed<T, 1>` (loaded or broadcast), the sums of one limb, `dot` of one limb by ones in the scalar
  form, and the element-by-element `add` and `axpy`; in the AVX2 form those two only for float,
  where the four elements of the test are fewer than a register's eight lanes and go through the
  scalar loop that finishes an array.
- **Violated claims**: the exact pairs (`two_sum`, `fast_two_sum`, `two_prod`), the directed sums
  (`add_down`, `add_up`: in a third to two thirds of the differing cases judged the result is on
  the wrong side of the sum), rounding to nearest (`Packed<T, 1>`, `add`, `axpy`), every error bound of `Expansion<T, 2>`
  (by a factor up to 10^25 in the cancelling family: the result keeps the rounding error of the
  square, which the bound relative to the cancelled sum cannot hold), and the **enclosures** of
  `Ball<T, 2>(1) * (a*a) + Y` and of `Accumulator<T, 2>::ball()`, whose radius, of order `u^2`, does
  not cover the square's rounding error of order `u`. The ball of `Accumulator<T, 1>` and the bounds
  of the one-limb `sum` and `dot` held in every case judged: their radius or bound is of order `n u`
  times the magnitudes, which covers one more rounding error of a term in these cases; that they
  always hold is not shown. `mul_down(a*a, 1)` and `mul_up(a*a, 1)` round the exact square in the
  claimed direction, and the exact square and its rounding lie on the same side of the result, so
  they stay right.
- **Not reached** in any build: `Expansion<T, 2>(c) - a*a` (the kernel negates the operand before
  its guard, and `-(a*a)` can be `-0`), the constructors of `Interval` and `Ball` from a square (as
  a bound, a center or a radius), `Ball + a*a`, the ball vectors, and the sum of two limbs. These
  were not seen to fuse here; nothing shows they cannot.

## The flags (`run_flags.sh`, at `-O2`)

| Flags | GCC 13, 16 | Clang (Apple 21, 18): headers | `kairn::self_test()` with Clang | Kairn probe with Clang |
|---|---|---|---|---|
| `-fno-signed-zeros` | refused (`__NO_SIGNED_ZEROS__`) | accepted (no macro) | ok | nothing differs (no contraction) |
| `-fno-signed-zeros -ffp-contract=fast` | refused | accepted | Apple clang: fails, the kernel `split`; Clang 18: **ok** | Apple clang: every product, not only squares, in nearly every route; Clang 18: the routes of the table above |
| `-fassociative-math` alone | accepted: no effect without the next two flags | accepted: no effect | ok | nothing differs |
| `-fassociative-math -fno-signed-zeros -fno-trapping-math` | refused (`__ASSOCIATIVE_MATH__`) | accepted | fails: reassociation | Apple clang: nothing; Clang 18: the sums, and the two-limb sum violates its bound (reassociation, not the guard) |
| `-funsafe-math-optimizations`, alone or with `-ffp-contract=fast` | refused | accepted | Apple clang: fails, reassociation; Clang 18: fails, results flushed to zero (it links the start-up code that sets FTZ and DAZ), `environment_ok()` false, and the probe stops at the first check of the environment | Apple clang: every product, every route that contracts (Clang's `-funsafe-math-optimizations` implies `-ffp-contract=fast`) |
| `-ffast-math` | refused (`__FAST_MATH__`) | refused | - | - |

MSVC's `/fp:fast` is refused by `_M_FP_FAST`; whether clang-cl defines that macro under
`/fp:fast` was not checked. Under the flags that Clang accepts silently, `self_test()` catches
reassociation and flushing, and the loss of signed zeros under contraction only through a kernel
it happens to fuse (it did with Apple clang, not with Clang 18). It does not look for a square of
the program: under plain `-ffp-contract=fast` it reports ok with the four compilers at `-O1`,
`-O2` and `-O3`.
