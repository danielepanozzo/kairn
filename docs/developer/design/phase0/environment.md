# The floating-point environment and the backends

Kairn's theorems are about round-to-nearest-even IEEE operations executed one at a time. This
page says what stands between those theorems and the instructions a client's compiler emits, what
Phase 0 measured on the test machines, and how the library protects itself. Every table cell that
reports a behavior comes from a run recorded under
[`experiments/phase0/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0);
documentation quotes are in [References](references.md#backends).

## The contract

1. All arithmetic is round-to-nearest-even. Kairn never reads or writes the rounding mode to do
   its work, and never changes the floating-point environment.
2. Subnormals behave as IEEE says (no FTZ, no DAZ), except on Metal, which has its own model.
3. Each operation of a kernel is executed as written: no reassociation, no value-changing
   rewriting. FMA contraction is the one transformation Kairn tolerates, by construction.
4. `fma` is a hardware fused multiply-add.

Violations are detected at three levels, each covering what the previous cannot see:

| Level | When | Detects |
|---|---|---|
| `#error` in `kairn/config.hpp` | compile time | fast-math and its sub-flags where the compiler defines a macro; missing hardware FMA; x87 evaluation |
| `kairn::self_test()` | once at startup, compiled with the client's flags | everything a flag can do that has no macro; the device's actual rounding and underflow behavior |
| `kairn::environment_ok()` | every batch-API entry; every scalar operation in debug builds | the *dynamic* state: rounding mode, FTZ, DAZ |

## Contraction

### What the experiment showed

The same double-word product (TwoProd on the high limbs with an explicit `fma`, two FMAs for the
cross terms, Fast2Sum) was written five ways and compiled under 23 configurations. An independent
script recomputed every result with exact rationals
([`contraction/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/contraction)).

- **textbook**: `p = a * b; e = fma(a, b, -p);` and then `p` feeds `p + c` and `s - p`.
- **intrinsics**: the same with `_mm256_mul_pd` / `vmulq_f64`.
- **scoped**: textbook plus the compiler's scoped "no contraction" switch.
- **opaque**: `p = fma(a, b, 0.0)`.

| Compiler, target | Contraction setting | textbook | intrinsics | scoped switch | opaque |
|---|---|---|---|---|---|
| Apple clang 21, arm64 | `-ffp-contract=off`, `on` (default) | correct | correct | correct | correct |
| | **`-ffp-contract=fast`** | **wrong in 20 000 of 20 000 cases** | **wrong** | **wrong: `#pragma clang fp contract(off)` is ignored** | correct |
| GCC 16, arm64 | `off`, `fast` (default) | correct | correct | correct, but the function is no longer inlined | correct |
| GCC 13, x86-64 | `off`, `fast` (default) | correct | correct | correct, not inlined | correct |
| Clang 18, x86-64 | `off`, `on` (default), `fast` | correct | correct | correct | correct |
| MSVC 19.52, x64 | `/fp:precise` (default), `/fp:strict` | correct | correct | correct | correct |
| | **`/fp:contract`** | **wrong in 20 000 of 20 000** | **wrong** | correct, not inlined | correct |

"Wrong" means the compiler duplicated the product into its consumers (`p + c` became
`fma(a, b, c)`, `s - p` became `fma(-a, b, s)`), which breaks Fast2Sum. The result still looks
like a double-word number, but **its relative error is about $u$ instead of $3u^2$: the low limb
is noise.** Nothing crashes and no assertion fires.

Three conclusions:

- **An explicit `fma` in TwoProd is not enough.** The brief assumed that TwoSum, Fast2Sum and
  TwoProd-with-`fma` are patterns contraction cannot change. That is true of each in isolation
  and false once they are inlined together, because the rounded product is an ordinary
  multiplication whose value flows into additions.
- **Raw SIMD intrinsics are contracted too.** `vmulq_f64` followed by `vaddq_f64`, and
  `_mm256_mul_pd` followed by `_mm256_add_pd`, are fused by the same compilers under the same
  settings. Emitting intrinsics does not protect a kernel.
- **Scoped switches are not a defense.** Clang documents, and the experiment confirms, that
  `-ffp-contract=fast` overrides the pragma. GCC's `optimize` attribute and MSVC's
  `#pragma fp_contract(off)` work but stop the function from being inlined, which is the one thing
  a 9-flop kernel must not lose.

GCC and x86-64 Clang produced correct code in every configuration. My reading, which the
experiment does not prove, is that their optimizers fuse a product only when it has no other use,
and here the product is also an operand of the explicit `fma`. That is an implementation detail,
not a guarantee, and nothing in their documentation promises it.

### The rule: no product feeds an addition

The generator enforces two syntactic rules on every kernel
([Verification](verification.md#generator)):

- **R1.** The result of a multiplication never reaches an operand of an addition or subtraction,
  directly or through a negation. A product whose rounded value is needed is written as
  `fma(a, b, +0.0)`: an FMA's result is not a multiplication, so there is nothing left to
  contract. TwoProd is therefore two FMAs.
- **R2.** No kernel returns a bare product, so no contraction can happen *across* kernels after
  the client's compiler inlines two of them.

The single exception is a *declared contractable* multiply-add, used for low-order terms where
only a magnitude bound is needed. The kernel's theorem is then stated and proved for both
executions, $\mathrm{RN}(ab + c)$ and $\mathrm{RN}(\mathrm{RN}(ab) + c)$, which is the brief's
"every other proof covers each $a\cdot b + c$ both fused and unfused". The constant-evaluation
path needs this anyway, because it has no FMA.

With R1 and R2 the set of computations a contracting compiler can produce from Kairn's code is
exactly the set the theorems cover. CI then checks the object code: for every kernel, on every
compiler and flag set of the matrix, the number of fused instructions equals the number of FMA
nodes in the IR (the experiment's `count_fma.sh` is the prototype of that check).

Cost: an FMA where a multiplication would do. On the CPUs of the test machines both have the same
throughput and nearly the same latency; the effect on kernel speed is to be measured in
Milestone 1 and is not known yet. On MSVC the scalar code must use `_mm_fmadd_sd`: `std::fma` is
a library call there under `/fp:strict` and `/Od` (measured).

### What contraction is not

`fma(a, b, +0.0)` equals $\mathrm{RN}(ab)$ except for the sign of a zero, so a compiler told that
signs of zeros do not matter may fold it back to `a * b` and then contract it. Apple clang with
`-ffp-contract=fast -fno-signed-zeros` does exactly that and breaks the opaque variant
([`results/macos-arm64-nsz.txt`](https://github.com/danielepanozzo/kairn/blob/main/experiments/phase0/contraction/results/macos-arm64-nsz.txt)).
`-fassociative-math` breaks TwoSum itself. These are value-changing flags of the fast-math family,
not contraction, and no way of writing C++ survives them. They are rejected, as follows.

## Compiler flags

Measured with [`flags/macros.sh`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/flags).

| Flag | GCC 13, 16 | Clang 18, Apple clang 21 | MSVC | Kairn's response |
|---|---|---|---|---|
| `-ffast-math`, `-Ofast`, `/fp:fast` | `__FAST_MATH__` | `__FAST_MATH__` | `_M_FP_FAST` | `#error` |
| `-ffinite-math-only` | `__FINITE_MATH_ONLY__` = 1 | same | — | `#error` |
| `-funsafe-math-optimizations`, `-fassociative-math` | `__ASSOCIATIVE_MATH__` | **no macro** | — | `#error` on GCC; self-test on Clang |
| `-fno-signed-zeros` | `__NO_SIGNED_ZEROS__` | **no macro** | — | `#error` on GCC; self-test on Clang |
| `-freciprocal-math` | `__RECIPROCAL_MATH__` | **no macro** | — | `#error` on GCC; self-test on Clang |
| `-ffp-model=fast` | not accepted | **no macro** on Apple clang 21 (`__FAST_MATH__` on Clang 18) | — | self-test |
| x86 without FMA (`-mavx2` alone does not enable it on GCC) | `__FMA__` undefined | `__FMA__` undefined | `__AVX2__` undefined | `#error` |
| `-frounding-math`, `/fp:strict` | `__ROUNDING_MATH__` | no macro | `_M_FP_STRICT` | supported: see [constexpr](library.md#constant-evaluation) |
| any contraction setting | no macro | no macro | `_M_FP_CONTRACT` | supported by construction |

On Clang three unsafe flag families are invisible to the preprocessor, and nvcc documents no
macro for `--use_fast_math` or `-ftz`. **The self-test is therefore not a courtesy; on those
compilers it is the only detector.**

## The self-test

`kairn::self_test()` is an inline function, compiled in the client's translation unit with the
client's flags, that returns a status with a message and never aborts by itself. Its operands are
read through `volatile` objects (from a buffer on GPUs), so the compiler cannot evaluate it at
compile time with correct semantics while compiling the real code differently. It checks:

| Check | Catches |
|---|---|
| $1 + u$, $1 + 3u$, their negatives, and a tie | a rounding mode other than nearest-even |
| $\lambda \cdot \tfrac12 \ne 0$; a subnormal operand is read as nonzero | FTZ, DAZ, flush-to-zero devices |
| `(a + b) - a` and the TwoSum error on operands where reassociation changes the answer | `-fassociative-math`, Metal's default math mode |
| `fma(a, b, 0)` with $ab = -0$ returns $+0$; TwoProd error on operands where a duplicated product shows | `-fno-signed-zeros`, broken opaque products |
| `fma(1 + 2u, 1 - 2u, -1)` is exactly $-4u^2$ | a software or unfused `fma` |
| correctly rounded quotient and square root on hard cases | `-freciprocal-math`, `-prec-div=false`, Metal's fast `sqrt` |
| every generated 2-limb kernel on fixed operands against stored bit patterns | anything else that changes a kernel's result |

The CUDA version runs the same checks in a kernel on the device; the Metal version is an MSL
function the client's own pipeline calls, with the operand buffer and the expected outputs
provided as `constexpr` arrays so that no Objective-C or Swift lives in Kairn. A failed self-test
is a hard error by contract: the documentation tells clients not to proceed.

Limits, stated plainly: the self-test proves the flags of the translation unit it is compiled in,
not of every translation unit that includes Kairn; and a compiler is free to optimize two inlined
copies of a kernel differently. R1 and R2 are what make the second point harmless for contraction.

## The dynamic environment

`kairn::environment_ok()` reads one control register and tests three fields:

| Target | Register | Must be zero | Read with |
|---|---|---|---|
| x86-64 | MXCSR | RC (bits 13–14), FTZ (bit 15), DAZ (bit 6) | `_mm_getcsr()` |
| AArch64 | FPCR | RMode (bits 22–23), FZ (bit 24), and AH/FIZ (bits 1, 0) where implemented | `__builtin_aarch64_get_fpcr()` (GCC), `__arm_rsr64` (Clang), `_ReadStatusReg(ARM64_FPCR)` (MSVC) |

It is called at every batch-API entry and, in debug builds, in every scalar operation; a failure
invokes `KAIRN_ENVIRONMENT_FAILURE`, which by default prints the reason and aborts. It is the
documented precondition of every Kairn call, and the query the first client needs. That client, a
library for verified computation with balls on CPU and CUDA, runs its double intervals in upward
rounding and must be back in nearest before calling Kairn. The usual way to
end up with FTZ and DAZ set without asking is to link any object compiled with `-ffast-math`,
which pulls in a startup routine that sets them for the whole process; that goes in the
troubleshooting page. The cost of the read is a few cycles; it will be reported in Milestone 1.

## Backends

| Backend | What the vendor guarantees | What Phase 0 observed | Consequence |
|---|---|---|---|
| x86-64, GCC and Clang | IEEE operations in SSE/AVX; `-ffp-contract` defaults to `fast` (GCC, C++) and `on` (Clang) | Contraction table above; `std::fma` is an instruction with `-mfma` | R1/R2; `#error` without `__FMA__` |
| x86-64, MSVC 19.52 | No contraction under `/fp:precise` since VS 2022 17.0 | Confirmed; `/fp:contract` contracts scalars and intrinsics; `std::fma` is a call under `/fp:strict` and `/Od` | Use FMA intrinsics for scalars |
| x86-64, clang-cl | `/fp:precise` maps to `-ffp-contract=on` | **Not tested: clang-cl is not installed on the Windows machine** ([D10](decisions.md#d10-test-infrastructure)) | — |
| AArch64, Apple clang and GCC | IEEE; FPCR is zero at thread start on macOS | Contraction table above | R1/R2 |
| AArch64 Linux | same | Not run in Phase 0; CI will use QEMU user-mode, correctness only | — |
| AArch64 Windows | same | Not run; the Windows machine has only x64 and x86 MSVC targets installed | compile-only CI needs the ARM64 component |
| CUDA | IEEE `+ - * / sqrt fma` in round-to-nearest with subnormals by default; `__fadd_rn`, `__fmul_rn`, … "never merged into a single multiply-add"; no dynamic rounding mode; no macro for `--use_fast_math` or `-ftz` | see [CUDA](#cuda) | Device code uses the `_rn` intrinsics; device self-test |
| Metal | "Either round ties to even or round toward zero … may be supported"; subnormals "may be flushed to zero" with undefined sign; fast math on by default | see [Metal](#metal) | Scoped pragmas; model Z; device self-test |

### CUDA

On an RTX 3080 Ti, an RTX A5000 and an RTX 6000 Ada with CUDA 13.2
([`cuda/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/cuda)):

- The prototype's functions compile as `__host__ __device__ constexpr` **without**
  `--expt-relaxed-constexpr`, and a value computed by constant evaluation, by the host at run
  time and by the device at run time are bit-identical. Two changes were needed and are now
  rules: use `__builtin_is_constant_evaluated()` (nvcc treats `std::is_constant_evaluated` as a
  host-only function), and never call `nextafter` in device code (with `-std=c++20` and
  libstdc++ 13 the name resolves to a `constexpr` host function; stepping the bit pattern works).
- Device results of the intrinsic-based double-word product equal the host's on $2^{20}$ cases,
  for `double` and `float` limbs, with `-fmad=true` and `false`.
- Subnormal `float` results match the host by default. With `--use_fast_math` the `_rn`
  intrinsics flush subnormals to zero, as documented, and nothing at compile time reveals it: the
  device self-test must.
- The directed-rounding intrinsics agree with the round-to-nearest emulation on $4 \cdot 2^{20}$
  operations.
- **`float` is 69 times faster than `double`** on all three cards (NVIDIA's tables say 64:1 for
  compute capabilities 8.6, 8.9 and 12.x, workstation cards included). A 2-limb `float` number (48
  bits) runs a multiply-add 2.5 times *faster* than a plain `double` (53 bits), and 72 times faster
  than a 2-limb `double`. This settles the direction of the float-versus-double question for GPUs;
  the range caveat of [Numbers](numbers.md#precision-depends-on-magnitude) is the price.

### Metal

On an Apple M3 Max, with the shader compiled at run time
([`metal/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/metal)):

| Question | Answer on this device |
|---|---|
| Rounding of `+`, `*`, `fma` | Nearest-even: no difference from IEEE on 172 000 cases with normal operands and results. |
| Is `fma` a single rounding? | Yes: the TwoProd error term is exact in the normal range. |
| Default compile options (`fast`, and `relaxed`: identical results) | **TwoSum's error term is compiled to zero in 93% of cases**, `(a + b) - a` is simplified to `b`, division and `sqrt` are not correctly rounded. Unusable as is. |
| `mathMode = .safe` with precise functions | Error-free transformations are exact; `a * b + c` in one expression is still fused. |
| `#pragma METAL fp math_mode(safe)` and `fp contract(off)` at the start of a function body, in a shader compiled with default options | **Honored**, also when the function is a helper called from an unprotected kernel. `sqrt` stays the fast variant unless written `precise::sqrt`. |
| Subnormals | **Flushed.** Subnormal operands are read as zero (`x != 0` is false for a subnormal `x`); a subnormal result becomes a zero with the sign of the exact result; a result that is tiny before rounding is flushed even when it would round to the smallest normal. Apple documents `float` subnormal support only from the M6 GPU family. |

So Kairn's MSL header puts the two pragmas at the start of every function it defines, calls only
`precise::` library functions, and is proved under model Z. The specification allows a device to
round toward zero; this one does not, and a device that does fails the self-test, as the brief
requires. The reduced range of `float` numbers on Metal is in the
[table](numbers.md#precision-depends-on-magnitude).

## Compiler hazards found on the way

| Finding | Evidence | Rule |
|---|---|---|
| nvcc: `std::is_constant_evaluated()` is host-only | warning #20013-D | use the builtin |
| nvcc with libstdc++ 13: `nextafter` in device code is an error | `cuda_test.cu` | step bit patterns |
| MSVC: `std::fma` is a library call under `/fp:strict` and `/Od` | 0 fused instructions in the listing | scalar FMA intrinsics on MSVC |
| MSVC: a loop over a struct wrapping one `double` is not auto-vectorized, where the same loop over `double` is | [`k1/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/k1) | see [k = 1](library.md#one-limb) |
| MSVC: functions holding the prototype's class-template `Expansion<double, 1>` get a `/GS` stack-cookie check that the equivalent plain struct does not | `k1/results-windows-x64-gs.txt`; cause not isolated | open issue for Milestone 1. Outcome, Milestone 1: the cause was the array of one element passed by value to the operators; they take it by `const&` since `3672c2a`, and no function of the probe gets the cookie at `/O2` ([costs](../../results/costs-milestone1.md#3-msvc-and-the-gs-stack-cookie)) |
| Clang default (`-ffp-contract=on`): `a * b + c` fuses for `double` but not for a wrapper type, whose operators are separate functions | `k1/results-macos-arm64.txt` | see [k = 1](library.md#one-limb) |
| GCC `optimize` attribute, MSVC `fp_contract` pragma: block inlining | contraction table | not used |
| MSVC in conformance mode (`/std:c++20`): a long network written as a function *template* takes super-linear time to parse: 31 gates 0.15 s, 48 gates 5 s, 141 gates did not finish in 24 CPU-minutes. The same network as a plain function: 0.1 s. GCC and Clang: 0.1 s either way | [`compile_time/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/compile_time) | the generator emits one non-template function per limb type |

## CI matrix

Per the brief, the quick tier builds and runs under: contraction off and forced on
(`-ffp-contract=fast`, `/fp:contract`), `-O0` to `-O3` (`/Od`, `/O2`), `-frounding-math` and
`/fp:strict`, on GCC, Clang, Apple clang, MSVC, clang-cl and nvcc; plus the object-code check of
the previous section. Phase 0 ran a first version of this matrix by hand: 23 configurations for
contraction, 22 for constant evaluation.
