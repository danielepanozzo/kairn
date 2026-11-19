# The library: header-only design, API, and the check against miso2

## Delivery

Kairn is a CMake `INTERFACE` target, `kairn::kairn`, with an installable package config. A client
adds an include path and nothing else; there is no compiled part. The C ABI used by the Python,
Julia and Rust bindings is one optional source file that instantiates the headers; it is built by
each binding's own build and adds no code of its own.

```
include/kairn/
  kairn.hpp              umbrella for the scalar types (k <= 2 only: it stays cheap to include)
  config.hpp             flag checks (#error), platform macros
  environment.hpp        environment_ok(), self_test()
  traits.hpp             kairn::traits, error-model constants
  expansion.hpp          Expansion<T, 1>, Expansion<T, 2>
  expansion3.hpp, expansion4.hpp, expansion8.hpp, expansion_n.hpp     one header per size
  interval.hpp, ball.hpp, ball_vector.hpp
  simd.hpp, soa.hpp      packed lanes; structure-of-arrays containers and views
  batch/                 sum, dot, axpy, convolution, gemv, gemm, map, accumulator
  io.hpp                 decimal and hexadecimal input and output
  math/                  one header per elementary function
  cuda/warp.hpp          warp shuffles and reductions
  metal/kairn.metal      the MSL header
  instantiate.hpp        explicit-instantiation helpers
  gen/                   generated kernels, one file per (backend, k)
```

The files under `gen/` are produced by the generator. For a header-only library the practical
choice is to **commit them** and have CI regenerate and compare, so that a client can use a plain
clone and no build of Kairn ever needs Python; the alternative is to generate at configure time
([D7](decisions.md#d7-generated-headers)). The template's rule that nothing generated is committed
is kept for the documentation.

Required client flags: C++20; on x86-64 hardware FMA (`-mfma` or `-march=x86-64-v3`; `/arch:AVX2`
on MSVC); no fast-math. Everything else, including `-frounding-math` and any contraction setting,
is supported ([Environment](environment.md)).

## Inlining and compile time

Measured on the synthetic 8-limb-sized networks of
[`experiments/phase0/compile_time/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/compile_time)
(an addition of 141 `TwoSum` gates and a product of 28 `TwoProd`, 8 products and 213 gates: 846
and 1 342 flops), one translation unit with 1, 16 or 64 call sites of each:

| Policy | Clang 21 (M3 Max) | GCC 16 (M3 Max) | Object size at 64 sites |
|---|---|---|---|
| out of line, or plain `inline` (the compiler chose not to inline) | 0.10 s | 0.3 s | 13 kB |
| forced inline, 16 call sites | 0.55 s | 2.5 s | 130 kB |
| forced inline, 64 call sites | 2.9 s | 11.5 s | 0.5 MB |

A single 213-gate network compiles in 0.04 s (Clang), 0.13 s (GCC) and 0.10 s (MSVC, as a plain
function).

Rules that follow:

- **$k \le 2$: forced inline.** These are 6 to 31 flops and must disappear into the caller.
- **$k = 3, 4$: plain `inline`**, the compiler decides.
- **$k = 8$ and runtime $k$: never forced inline.** They are `inline` functions emitted once per
  translation unit; `instantiate.hpp` provides `KAIRN_INSTANTIATE(T, k)` and matching `extern`
  declarations so that a project pays for them in one translation unit only.
- **Kernels are non-template functions**, one per limb type. MSVC's two-phase template parsing is
  super-linear in the length of a network: 0.15 s at 31 gates, 5 s at 48, and no result after 24
  CPU-minutes at 141, against 0.1 s for the same code outside a template. The class templates
  `Expansion<T, k>` forward to these functions.
- Headers for large $k$ are separate, so including `kairn.hpp` never parses them.

Compile times of the real networks will be reported per milestone, as the brief asks.

## Runtime dispatch

Scalar and inline code target the instruction set the client compiles for. Batch kernels can also
use AVX-512 when the CPU has it: the AVX-512 functions carry a per-function `target` attribute on
GCC and Clang (MSVC needs none), and the choice is made from CPU detection inside the headers.

The brief forbids global mutable state and lazily initialized tables, and a cached CPU-detection
result is exactly that. The proposal is a value the client holds:

```cpp
const kairn::Backend backend = kairn::detect_backend();   // CPUID + XGETBV, once, wherever the client likes
kairn::dot(backend, x, y);                                // or kairn::dot(x, y): the compile-time baseline
```

`Backend` is a trivially copyable enum-like value; the default argument is the baseline the
translation unit was compiled for, so code that never asks for dispatch never pays for it. See
[D9](decisions.md#d9-runtime-dispatch-state) for the alternative (one idempotent atomic).

## Constant evaluation

Verified in Phase 0 with a prototype
([`experiments/phase0/constexpr/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/constexpr)):
the same function body serves constant evaluation and run time, switching on
`__builtin_is_constant_evaluated()`, and a `static_assert`-ed constant equals the run-time value
bit for bit for `TwoSum` and `TwoProd` in 22 configurations: GCC 11, 13 and 16, Clang 18, Apple
clang 21 and MSVC 19.52, at `-O0` and `-O2`, **with and without `-frounding-math`** (GCC turns the
flag off for manifestly constant evaluation, which its documentation does not say but its source
does), with `/fp:strict`, and under nvcc on host and device.

- At compile time `TwoProd` is Dekker's product (no `std::fma` in C++20 constant expressions) and
  a `muladd` is unfused; at run time both use FMA. They are different executions of the same
  kernel and the theorem covers both, so **a compile-time result and a run-time result of the same
  expression may differ in the last bits, both within the bound.** For the error-free blocks they
  are identical.
- Constants from integers and rationals use integer arithmetic only, on a small fixed-capacity
  big integer written without `__int128` (MSVC lacks it), so they do not depend on the
  floating-point semantics of constant evaluation at all. This is the generalization of miso2's
  `roundAbs` to $k$ limbs.

## One limb

The brief asks that `Expansion<T, 1>` cost the same as plain `T`. Measured on three small
functions (axpy, dot, a degree-7 Horner) by comparing the emitted instructions
([`experiments/phase0/k1/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/k1)):

| Compiler | Result |
|---|---|
| GCC 13 (x86-64), GCC 16 (arm64), every contraction setting | Same instructions as `double`. |
| Clang 18, Apple clang 21, `-ffp-contract=off` or `fast` | Identical. |
| Clang 18, Apple clang 21, **default (`-ffp-contract=on`)** | **Not the same.** `a * x + y` on `double` is one expression and is fused; on the wrapper it is two operator calls and is not: one extra instruction per multiply-add (7 in the Horner loop). |
| The same, with `#pragma clang fp contract(fast)` inside the two $k = 1$ operators | Identical again; but then $k = 1$ also fuses when the client compiled with `-ffp-contract=off`. |
| MSVC 19.52 | Scalar code is the same, but **the axpy loop over the wrapper is not auto-vectorized** where the loop over `double` is. Also see the `/GS` note in [Environment](environment.md#compiler-hazards-found-on-the-way). |

So the requirement holds on GCC, holds on Clang at a price that needs your choice
([D6](decisions.md#d6-one-limb-and-contraction-under-clang)), and for auto-vectorized loops on MSVC it
cannot be met by a wrapper type at all. The answer for loops is the same on every compiler: the
batch kernels and the SoA views at $k = 1$ operate on plain arrays of `T`.

## API sketch

Names are provisional; the shape is what Phase 0 commits to.

```cpp
namespace kairn {

template <class T, int K>            // T: float or double;  K >= 1
struct Expansion {
    T limb[K];                                               // public, most significant first
    constexpr Expansion() noexcept;                          // zero
    constexpr Expansion(T x) noexcept;                       // exact
    template <int J> explicit(J > K)
    constexpr Expansion(const Expansion<T, J>&) noexcept;    // wider: exact; narrower: truncation
    static constexpr Expansion from_limbs(const T* limbs);            // asserts normalized in debug
    static constexpr Expansion from_limbs_unchecked(const T* limbs);  // precondition: normalized
};
// Trivially copyable, standard layout, sizeof == K * sizeof(T), same layout on host and device.

// + - * / (also with a T operand), unary -, compound assignments, sqrt, fma, abs, ldexp, half,
// exact comparisons, sign, isfinite, is_normalized, renormalize.
// add_fast(x, y): the cheaper addition with the weaker (operand-relative) bound.
// kairn::finite::add, mul, ...: no canonicalization of non-finite results.
// to_nearest(x), to_down(x), to_up(x), abs_upper(x): exact conversions to T.
// two_sum, fast_two_sum, two_prod, next_up, next_down, radd, rmul: the building blocks, on T.

template <class T> struct Bound {    // an entry of the error model
    T unit, tiny;                    // |computed - exact| <= unit * |reference| + tiny
    T unit_computed, tiny_computed;  // |computed - exact| <= unit_computed * |computed| + tiny_computed
    enum { result, operands } reference;
    bool verified;                   // false while the operation is UNVERIFIED
};

template <class X> struct traits;    // X = float, double, Expansion<T, K>
//   using limb_type; static constexpr int limbs, precision;       (precision = limbs * p)
//   static constexpr Bound<limb_type> add, add_fast, sub, mul, mul_limb, div, div_limb, sqrt, fma, ldexp;
//   static constexpr Bound<limb_type> sum(std::size_t n), dot(std::size_t n), gemv(std::size_t n), ...;

template <class X> struct Constant { X value; typename traits<X>::limb_type error; bool exact; };
template <class X> constexpr Constant<X> rational(long long num, long long den);

template <class T, int K> struct Interval;      // two k-numbers
template <class T, int K> struct Ball;          // a k-number and a T radius
template <class T, int K, std::size_t N> struct BallVector;   // and a view type for run-time N
enum class Trit : signed char { no = -1, unknown = 0, yes = 1 };

Status self_test() noexcept;         // also kairn::cuda::self_test, and the MSL function
bool environment_ok() noexcept;

}  // namespace kairn
```

What makes this fit a client templated on its scalar:

- `float`, `double` and every `Expansion<T, K>` answer the same `traits` questions, so client code
  reads the same for all of them and a first pass at $k = 1$ is rerun at $k = 2, 4, 8$ by changing
  one template argument.
- The error model is data: a client bound written with $u$ and Higham's $\gamma_n$ becomes
  `traits<X>::mul.unit` and `traits<X>::dot(n)`. An `UNVERIFIED` operation's entry has
  `verified == false` and no usable constants, so a client cannot build a proof on a number that
  is only an empirical maximum.
- `Interval` and `Ball` share the enclosure interface of
  [Operations](operations.md#one-interface-and-conversions), so an algorithm can be generic over
  the enclosure and pick the cheaper one per $k$ (interval at $k = 1$ where directed rounding is
  one instruction on CUDA and AVX-512, ball at $k \ge 2$).
- On CUDA every scalar function is `__host__ __device__ constexpr` and usable inside the client's
  own kernels; device code has no recursion, no allocation and only plain structs. Warp helpers
  shuffle and reduce k-numbers limb by limb. In MSL the same operations are functions on small
  structs.
- `simd.hpp` exposes the generated per-ISA networks as a packed type (`W` numbers in registers,
  limb $i$ of all of them in one register), and `soa.hpp` containers and views with proxy element
  access, so that clients write their own vector loops over the proven networks.

Thread safety: no global mutable state, no lazily initialized tables, nothing written outside the
outputs. `environment_ok` and `self_test` only read.

## What miso2 needs

miso2 is a branch-and-bound solver over Bernstein polynomials that plans to rerun
precision-limited queries on k-numbers. I read its `docs/numbers-and-rounding.md`,
`docs/proofs-and-arguments.md`, `docs/design-decisions.md` and the arithmetic headers
(`Arithmetic.hpp`, `Ball.hpp`, `Interval.hpp`, `Lanes.hpp`) and its build flags; I did not read
all 14 500 lines, so this list is what those sources show, not an audit.

| miso2 today | With Kairn | Status |
|---|---|---|
| `Ball<S>::unit`, `tiny`, and `ballCovers(k)`: $u$, an underflow constant, and the check $k\,u \le \tfrac12$ | `traits<X>` constants and the `constexpr` bound functions, whose preconditions are checked at compile time | in the brief |
| `BallVector<N>`: $N$ `double` midpoints and one radius; `Polynomial` likewise | `BallVector<T, k>` | in the brief; its semantics are now [defined](operations.md#ballvector) |
| `norm()`, the largest absolute midpoint bounded above | `norm_upper` | **added**: not in the brief's kernel list |
| Radius arithmetic `nextUp`, `addUpAtNearest`, `mulUpAtNearest`: `constexpr`, same bits on host and device | `next_up`, `radd`, `rmul`, public | **added** as public API |
| Product of polynomials: a convolution over multi-indices with bound $\gamma_k$ | `convolution` covers the univariate case only; the multi-index one needs the public `Accumulator` | **added** |
| de Casteljau with deferred halving, exact scaling except on underflow | addition kernels, `ldexp`, `half` with their bound | in the brief |
| Exactness tests `fma(x, s, -y) == 0` | `two_prod`, `two_sum` public | **added** as public API |
| `roundAbs` and the Lagrange table: rationals rounded at compile time in integer arithmetic, with error bounds | `rational`, with error bound and exactness flag | in the brief |
| "Void" state (zero midpoints, infinite radius) when anything overflows or is NaN | whole-space `BallVector`; every kernel returns an all-finite flag | flag **added** |
| Leaves built on the host in `double` balls, narrowed to `float` balls for the device | conversions between `double`-limb and `float`-limb numbers, with the radius grown by the conversion error | **added**: the brief only has $k \leftrightarrow k'$ |
| `Interval`: one name, host type and device type with one layout; `lower(x)`, `upper(x)` in `float` or `double` | one `Interval<T, k>` on both sides; `lower_as<T>`, `upper_as<T>` | in the brief |
| Warp reductions (`min`, `hull`, `from`) by `__shfl_sync` on 32- and 64-bit values | warp helpers | in the brief |
| No `std::tuple` in device code (nvcc 13.2 miscompiled it), no recursion (1 kB device stack) | adopted as rules for Kairn's device code | — |
| Elementary functions of intervals (`sqrt`, `sin`, `cos`, `tan`, `log`, `sinpi`, `cospi`, from core-math) | the elementary-function milestone | in the brief, late |
| Built with `-frounding-math` (GCC, `gnu++23`) and nvcc `-std=c++20 --expt-relaxed-constexpr` | both work; the relaxed flag is not needed by Kairn | verified in Phase 0 |
| Host intervals run in upward rounding ("tight"), balls in nearest, under guards that write MXCSR | Kairn must be called in nearest; `environment_ok()` is the check | in the brief |

**What miso2 would need that Kairn does not provide**, beyond the additions above:

1. **Nothing replaces hardware directed rounding at $k = 1$ on the host.** A `double` interval
   operation in miso2's current library is one instruction per bound; Kairn's
   `Interval<double, 1>` emulates each bound with about ten operations because it may not change
   the rounding mode. miso2 should keep its own intervals for the first pass and use Kairn from
   $k = 2$ up, and for balls. Converting between the two is `lower_as<double>` and a constructor.
2. **Mixed rounding modes in one program.** miso2 will switch between upward (its intervals) and
   nearest (Kairn) around calls. Kairn can verify the mode but will not set it; the switching and
   its cost stay in miso2's guards.
3. **Bernstein-specific kernels** (subdivision along a lattice line, Lagrange-to-Bernstein
   conversion, the hull of a polynomial in $t$) are not in Kairn and should not be: they are
   compositions of sums, scalings and convolutions, and their radius bounds are miso2's own
   theorems with Kairn's constants substituted.
4. **Its GPU plan is float limbs with $k$ doubling.** The range table of
   [Numbers](numbers.md#precision-depends-on-magnitude) is the caveat: `float` k-numbers keep
   their precision only above about $10^{-16}$ at $k = 4$. miso2 centers its coordinates, which
   helps, but its determinants are products of differences and can be small; it will need exact
   power-of-two scaling of its inputs, which Kairn provides, or `double` limbs at 69 times the
   cost per operation.
5. **Timeline.** miso2's plan is $k$ doubled per rerun: 2, 4, 8. Verified $k = 2$ is Milestone 1;
   $k = 4$ carries the proof risk described in [Verification](verification.md#networks-for-three-and-four-limbs);
   $k = 8$ is research.
