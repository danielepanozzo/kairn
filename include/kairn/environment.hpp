/// @file
/// The floating-point environment Kairn's guarantees assume, and the two checks a program can make
/// of it (docs/developer/design/phase0/environment.md, "The contract"):
///
/// - kairn::environment_ok(): the dynamic state, which can change while a program runs: the
///   rounding mode and flush-to-zero, read from the control register;
/// - kairn::self_test(): what the compiler did with the flags of the translation unit it is
///   compiled in, which no register shows, by computing known results and comparing.
///
/// Kairn never reads or writes the rounding mode to do its work and never changes the environment;
/// both checks only read.
#pragma once

#include "config.hpp"
#include "gen/scalar.hpp"
#include "gen/selftest.hpp"

#include <bit>
#include <cfenv>
#include <cstdint>
#include <limits>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
#include <xmmintrin.h>  // _mm_getcsr; <immintrin.h> would add about half a second per translation unit
#define KAIRN_DETAIL_MXCSR 1
#elif (defined(__aarch64__) || defined(_M_ARM64)) && (defined(__GNUC__) || defined(__clang__))
#define KAIRN_DETAIL_FPCR 1
#endif

namespace kairn {

namespace detail {

// What in the control register differs from the default environment, in words, or nullptr.
inline const char* environment_problem() noexcept {
#if defined(KAIRN_DETAIL_MXCSR)
    // MXCSR: rounding control in bits 13-14, flush-to-zero in bit 15, denormals-are-zero in bit 6.
    const unsigned csr = _mm_getcsr();
    if (csr & 0x6000u) return "the rounding mode is not to nearest (MXCSR.RC is not zero)";
    if (csr & 0x8000u) return "results below the normal range are flushed to zero (MXCSR.FTZ is set)";
    if (csr & 0x0040u) return "subnormal operands are read as zero (MXCSR.DAZ is set)";
    return nullptr;
#elif defined(KAIRN_DETAIL_FPCR)
    // FPCR: rounding mode in bits 22-23, flush-to-zero in bit 24, and where FEAT_AFP is
    // implemented, alternate handling in bit 1 and flush of inputs in bit 0 (otherwise both read
    // as zero).
#if defined(__clang__)
    const std::uint64_t fpcr = __builtin_arm_rsr64("fpcr");
#else
    const std::uint64_t fpcr = __builtin_aarch64_get_fpcr64();
#endif
    if (fpcr & (std::uint64_t{3} << 22)) return "the rounding mode is not to nearest (FPCR.RMode is not zero)";
    if (fpcr & (std::uint64_t{1} << 24)) return "subnormal numbers are flushed to zero (FPCR.FZ is set)";
    if (fpcr & std::uint64_t{2}) return "alternate floating-point behavior is on (FPCR.AH is set)";
    if (fpcr & std::uint64_t{1}) return "subnormal operands are read as zero (FPCR.FIZ is set)";
    return nullptr;
#else
    // No register read is written for this target: only the rounding mode, as the C library
    // reports it, is checked.
    return std::fegetround() == FE_TONEAREST ? nullptr : "the rounding mode is not to nearest";
#endif
}

// The environment check of KAIRN_CHECKS, before a scalar operation; nothing in constant
// evaluation, which has its own fixed rounding.
KAIRN_FORCEINLINE constexpr void check_environment() noexcept {
#if KAIRN_CHECKS
    if (!__builtin_is_constant_evaluated()) {
        if (const char* problem = environment_problem()) {
            KAIRN_ENVIRONMENT_FAILURE(problem);
        }
    }
#endif
}

}  // namespace detail

/// Whether the floating-point environment is the one every Kairn guarantee assumes.
///
/// Reads one control register (MXCSR on x86-64, FPCR on AArch64) and checks that the rounding
/// mode is to nearest and that subnormal numbers are neither flushed to zero as results nor read
/// as zero as operands. Kairn never changes these itself; other code can (a directed rounding
/// mode set by an interval library, or flush-to-zero set at startup by any object compiled with
/// -ffast-math), and a program that does must restore them before calling Kairn. Checked before
/// every scalar operation when KAIRN_CHECKS is 1. Costs a few cycles; only reads.
///
/// On a target other than x86-64 and AArch64 (or MSVC on AArch64, for which Kairn's kernels do
/// not compile yet), only the rounding mode is checked, through std::fegetround().
/// Not usable in constant evaluation.
inline bool environment_ok() noexcept {
    return detail::environment_problem() == nullptr;
}

/// The result of kairn::self_test().
struct Status {
    /// nullptr when every check passed; otherwise the first check that failed, in words.
    const char* failure = nullptr;
    /// For a failure of a generated kernel, which kernel and limb type, such as "mul_2_2 (float)";
    /// otherwise nullptr.
    const char* kernel = nullptr;

    /// Whether every check passed.
    constexpr bool ok() const noexcept { return failure == nullptr; }
    /// Whether every check passed.
    constexpr explicit operator bool() const noexcept { return ok(); }
    /// "ok", or the failure.
    constexpr const char* message() const noexcept { return failure ? failure : "ok"; }
};

namespace detail {

// The square root of the hardware, as the prelude does for fma: <cmath> alone would cost a fifth of
// a second per translation unit with some standard libraries, for one call.
inline double sqrt_rn(double a) noexcept {
#if defined(_MSC_VER) && !defined(__clang__)
    return _mm_cvtsd_f64(_mm_sqrt_sd(_mm_set_sd(a), _mm_set_sd(a)));
#else
    return __builtin_sqrt(a);
#endif
}
inline float sqrt_rn(float a) noexcept {
#if defined(_MSC_VER) && !defined(__clang__)
    return _mm_cvtss_f32(_mm_sqrt_ss(_mm_set_ss(a)));
#else
    return __builtin_sqrtf(a);
#endif
}

// Bit identity. Comparisons cannot be used where a subnormal number is involved: under
// flush-to-zero both AArch64 and x86 (with DAZ) read a subnormal operand of a comparison as zero.
template <class T>
inline bool bits_equal(T a, T b) noexcept {
    using U = std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>;
    return std::bit_cast<U>(a) == std::bit_cast<U>(b);
}

template <class T>
inline const char* self_test_limb() noexcept {
    // Operands are read from volatile objects: the compiler cannot know their values, so it must
    // emit the arithmetic, compiled as the flags of this translation unit say.
    constexpr T u = std::numeric_limits<T>::epsilon() / 2;   // 2^-p
    constexpr T lambda = std::numeric_limits<T>::min();      // the smallest normal number
    constexpr T eta = std::numeric_limits<T>::denorm_min();  // the smallest subnormal number
    volatile T v_one = T(1), v_u = u, v_3u = 3 * u, v_lambda = lambda, v_eta = eta, v_half = T(0.5);
    volatile T v_zero = T(0), v_minus_one = T(-1), v_small = u / 2;
    volatile T v_1p2u = 1 + 2 * u, v_1m2u = 1 - 2 * u, v_two = T(2), v_three = T(3), v_five = T(5),
               v_seven = T(7);
    const T one = v_one;

    // Round to nearest, ties to even: 1 + u and 1 + 3u are ties (between 1 and 1 + 2u, and between
    // 1 + 2u and 1 + 4u); upward and away from zero move the first, downward and toward zero the
    // second, and the negatives catch the mirror images.
    if (one + v_u != one || -one - v_u != -one || one + v_3u != 1 + 4 * u || -one - v_3u != -1 - 4 * u)
        return "rounding is not to nearest with ties to even";
    // Flush to zero of a subnormal result, then of a subnormal operand, compared bit by bit.
    constexpr T half_lambda = lambda / 2, two_eta = 2 * eta;
    if (!bits_equal(T(v_lambda * v_half), half_lambda)) return "subnormal results are flushed to zero";
    const T e = v_eta;
    if (!bits_equal(T(e + e), two_eta)) return "subnormal operands are read as zero";
    // Reassociation: (1 + u/2) - 1 is 0 in floating point and u/2 in real arithmetic, and the
    // error of that sum, which TwoSum computes, is u/2.
    const T small = v_small;
    const T s = one + small;
    if (s - one != 0) return "the compiler reassociates floating-point sums (-fassociative-math)";
    T ts, te;
    gen::two_sum(one, small, ts, te);
    if (ts != one || te != small) return "TwoSum is not error-free: the compiler rewrites floating-point sums";
    // fma(-1, +0, +0) is +0; a compiler that ignores signs of zeros turns it into -1 * +0 = -0,
    // and may then fold any opaque product back into a plain one.
    if (!bits_equal(gen::fma_rn(v_minus_one, v_zero, v_zero), T(0)))
        return "fma(a, b, +0) is not exact: the compiler ignores the signs of zeros (-fno-signed-zeros)";
    // (1 + 2u)(1 - 2u) - 1 is exactly -4u^2 when fused, and 0 when the product is rounded first.
    if (gen::fma_rn(v_1p2u, v_1m2u, -one) != -4 * u * u) return "fma is not a fused multiply-add";
    // Quotients by one divisor, where multiplying by a rounded reciprocal gives another result
    // (-freciprocal-math), and a correctly rounded square root. The expected values are constant
    // expressions, which compilers evaluate to nearest whatever the flags (-frounding-math too).
    constexpr T q5 = T(5) / T(3), q7 = T(7) / T(3), q2 = T(2) / T(3);
    const T three = v_three;
    if (v_five / three != q5 || v_seven / three != q7 || v_two / three != q2)
        return "quotients are not correctly rounded (-freciprocal-math)";
    T sqrt2 = T(0);
    if constexpr (sizeof(T) == 8) {
        sqrt2 = 0x1.6a09e667f3bcdp+0;
    } else {
        sqrt2 = 0x1.6a09e6p+0f;
    }
    if (sqrt_rn(T(v_two)) != sqrt2) return "the square root is not correctly rounded";
    return nullptr;
}

}  // namespace detail

/// Checks, at run time, that this translation unit was compiled and runs as Kairn's guarantees
/// assume; call it once at startup and do not use Kairn if it fails.
///
/// Compiled with the flags of the translation unit that calls it, it computes results that the
/// IEEE 754 rules fix exactly and compares: rounding to nearest with ties to even, no flush to
/// zero of subnormal results or operands, no reassociation of sums, signed zeros respected by
/// the fused multiply-add, a fused multiply-add that is fused, correctly rounded quotients and
/// square roots; then it runs every generated kernel, for float and double, on fixed operands and
/// compares with the results the generator's exact interpreter computed for them. Operands are
/// read through volatile objects, so the compiler cannot evaluate any of it at compile time.
///
/// What it catches: a flag with no macro for config.hpp to see (Clang's -fassociative-math,
/// -fno-signed-zeros, -freciprocal-math, Apple clang's -ffp-model=fast) where the flag changes one
/// of the results it computes (with Apple clang 21, -freciprocal-math alone and -fno-signed-zeros
/// alone changed none), a changed rounding mode or flush-to-zero at the moment it runs, and a
/// compiler that changes a kernel's result on the operands tried. What it does not prove: the flags of other translation units, nor the result
/// of every operand. Returns at the first failure; never aborts; only reads.
inline Status self_test() noexcept {
    if (const char* failure = detail::self_test_limb<double>()) return {failure, nullptr};
    if (const char* failure = detail::self_test_limb<float>()) return {failure, nullptr};
    if (const char* kernel = gen::selftest::run())
        return {"a generated kernel computed a result other than the exact one on fixed operands", kernel};
    return {};
}

}  // namespace kairn
