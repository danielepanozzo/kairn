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

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

namespace detail {

// The state of the environment as one read gives it: the control register, MXCSR on x86-64 (32
// bits) and FPCR on AArch64; on another target, 1 when the rounding mode that the C library
// reports is not to nearest, and 0 when it is (no register read is written there).
KAIRN_FORCEINLINE std::uint64_t environment_state() noexcept {
#if defined(KAIRN_DETAIL_MXCSR)
    return _mm_getcsr();
#elif defined(KAIRN_DETAIL_FPCR)
#if defined(__clang__)
    return __builtin_arm_rsr64("fpcr");
#else
    return __builtin_aarch64_get_fpcr64();
#endif
#else
    return std::fegetround() == FE_TONEAREST ? 0 : 1;
#endif
}

// The bits of environment_state() that are all zero in the default environment and that a check
// reads. With rounding false the rounding mode is left out, and what is left is flush to zero (and
// on AArch64 alternate handling): what can change the result even of a function that does not
// round, since a comparison reads a subnormal operand as zero there.
// - MXCSR: rounding control in bits 13-14 (0x6000), flush-to-zero in bit 15 (0x8000),
//   denormals-are-zero in bit 6 (0x0040): 0xE040, and 0x8040 without the rounding mode.
// - FPCR: rounding mode in bits 22-23 (0xC00000), flush-to-zero in bit 24 (0x1000000), and where
//   FEAT_AFP is implemented, alternate handling in bit 1 and flush of inputs in bit 0 (otherwise
//   both read as zero): 0x1C00003, and 0x1000003 without the rounding mode.
// - Another target: 1, and 0 without the rounding mode (nothing else is checked there).
constexpr std::uint64_t environment_mask(bool rounding) noexcept {
#if defined(KAIRN_DETAIL_MXCSR)
    return rounding ? 0xE040u : 0x8040u;
#elif defined(KAIRN_DETAIL_FPCR)
    return (rounding ? (std::uint64_t{3} << 22) : std::uint64_t{0}) | (std::uint64_t{1} << 24) | std::uint64_t{3};
#else
    return rounding ? 1 : 0;
#endif
}

// What the bits b of a state differ in from the default environment, in words (the first, in the
// order rounding mode, flush to zero, the rest), or nullptr when b is zero; b is a state masked
// by environment_mask.
inline const char* environment_message(std::uint64_t b) noexcept {
#if defined(KAIRN_DETAIL_MXCSR)
    if (b & 0x6000u) return "the rounding mode is not to nearest (MXCSR.RC is not zero)";
    if (b & 0x8000u) return "results below the normal range are flushed to zero (MXCSR.FTZ is set)";
    if (b & 0x0040u) return "subnormal operands are read as zero (MXCSR.DAZ is set)";
#elif defined(KAIRN_DETAIL_FPCR)
    if (b & (std::uint64_t{3} << 22)) return "the rounding mode is not to nearest (FPCR.RMode is not zero)";
    if (b & (std::uint64_t{1} << 24)) return "subnormal numbers are flushed to zero (FPCR.FZ is set)";
    if (b & std::uint64_t{2}) return "alternate floating-point behavior is on (FPCR.AH is set)";
    if (b & std::uint64_t{1}) return "subnormal operands are read as zero (FPCR.FIZ is set)";
#else
    if (b) return "the rounding mode is not to nearest";
#endif
    return nullptr;
}

// What in the control register differs from the default environment, in words, or nullptr; with
// rounding false the rounding mode is left out (environment_mask).
inline const char* environment_problem(bool rounding = true) noexcept {
    return environment_message(environment_state() & environment_mask(rounding));
}

// The report of a check of the environment that failed, the only place where Kairn expands
// KAIRN_ENVIRONMENT_FAILURE (config.hpp): the message of the bits b (a masked state that is not
// zero), given to the macro. A function of its own that the compiler is asked never to inline,
// and to place with the code that rarely runs (KAIRN_DETAIL_COLD), so that a check costs its
// caller one read and one test, and a call on the path that is not taken: the message, the two
// addresses of strings, and the program's statement are not compiled into every check, and do not
// count against the compiler's budget for inlining the caller. An inline function, of which the
// linker keeps one copy for the whole program: the reason why a program defines the macro the same
// way in every translation unit (config.hpp).
KAIRN_DETAIL_COLD inline void report_environment(std::uint64_t b) noexcept {
    KAIRN_ENVIRONMENT_FAILURE(environment_message(b));
}

// The check itself, at run time: one read of the control register (environment_state) and one
// test of the bits of environment_mask(rounding); when one of them is set, the report, and false.
// As GCC 13 and 16, Clang 18 and Apple clang 21 compile it at -O2 and -O3: on x86-64, (v)stmxcsr
// into memory and a load, an and of 0xE040 (0x8040 without the rounding mode), which sets the flags
// and keeps the bits for the report, and a branch; on AArch64, mrs of FPCR and a test of
// 0x1C00003 (0x1000003), which is no immediate of a logical instruction there: Apple clang puts it
// in a register by a mov and a movk (outside a loop, where a register is free for it) for one ands,
// GCC 16 makes it two ands of immediates (0x1ffffff, then 0xffffffffffc00003 or 0xffffffffff000003),
// and a branch. On another target, a call of std::fegetround() and a comparison (nothing without the
// rounding mode). The report is the last statement of its branch, the result set before it: MSVC
// sees that the default KAIRN_ENVIRONMENT_FAILURE does not return, and refuses a statement after
// the report as unreachable code (C4702, an error with /WX).
KAIRN_FORCEINLINE bool environment_checked(bool rounding) noexcept {
    bool ok = true;
    if (const std::uint64_t differs = environment_state() & environment_mask(rounding)) [[unlikely]] {
        ok = false;
        report_environment(differs);
    }
    return ok;
}

// The environment check of KAIRN_CHECKS, first in every check of an operation: whether the checks
// of its operands may follow. False when the environment is not the default one and
// KAIRN_ENVIRONMENT_FAILURE returned: the operation then goes on without them, since they
// compute in that environment (x0 + x1 == x0 under a directed rounding mode can be false for a
// canonical pair). Always true in constant evaluation, which has its own fixed rounding. The same
// read, test and report as check_batch_environment.
KAIRN_FORCEINLINE constexpr bool check_environment() noexcept {
    bool ok = true;
#if KAIRN_CHECKS
    if (!__builtin_is_constant_evaluated()) ok = environment_checked(true);
#endif
    return ok;
}

// The same for a function that does not round (config.hpp lists them): its result is the same
// under every rounding mode, so the rounding mode is left out of the check and of the report;
// the rest of the environment is checked, since flush to zero can change a comparison. Whether the
// checks of its operands that do not round may follow (a negative radius); those that round, the
// test of a canonical pair, also need rounding_to_nearest().
KAIRN_FORCEINLINE constexpr bool check_environment_except_rounding() noexcept {
    bool ok = true;
#if KAIRN_CHECKS
    if (!__builtin_is_constant_evaluated()) ok = environment_checked(false);
#endif
    return ok;
}

// The environment check of a batch entry, a function that runs a loop over arrays (the functions of
// batch.hpp, and the operations of ball_vector.hpp on whole ball vectors, their constructors
// included), made in every build, with KAIRN_CHECKS 1 or 0: docs/developer/design/brief.md,
// "Floating-point environment", asks it "at every batch-API entry", and of the scalar operations
// in debug builds only, where check_environment() makes it. The control register is read as
// environment_ok() reads it, and a state that is not the default one is reported through
// KAIRN_ENVIRONMENT_FAILURE, with the message of check_environment(): by default the program stops.
// Whether the environment is the default one: false when KAIRN_ENVIRONMENT_FAILURE returned, and
// then the checks of the operands of a debug build do not follow. With rounding false, for a
// function whose result the rounding mode cannot change, the rounding mode is left out, as
// check_environment_except_rounding() leaves it out. True in constant evaluation, which has no
// environment to read (no batch entry is constexpr today). Per call, whatever the length of the
// arrays: one read of the register and one test of a mask (environment_checked), the report out of
// line (report_environment). Its result must not initialize a const local
// variable (`const bool ok = check_batch_environment();`): the initializer of a const variable of
// integral type is tried as a constant expression first, where this function returns true without
// reading anything, and the check would never run (seen with Apple clang 21, at -O0 as at -O2); an
// assignment, a non-const variable or the condition of an if is evaluated at run time.
KAIRN_FORCEINLINE constexpr bool check_batch_environment(bool rounding = true) noexcept {
    bool ok = true;
    if (!__builtin_is_constant_evaluated()) ok = environment_checked(rounding);
    return ok;
}

// Whether the environment is the default one, the rounding mode to nearest among it, without a
// report: the checks of the operands of a function that does not round are made only then, when
// they round themselves (x0 + x1 == x0 under a directed rounding mode can be false for a
// canonical pair). True in constant evaluation.
KAIRN_FORCEINLINE constexpr bool rounding_to_nearest() noexcept {
    bool ok = true;
#if KAIRN_CHECKS
    if (!__builtin_is_constant_evaluated()) ok = (environment_state() & environment_mask(true)) == 0;
#endif
    return ok;
}

}  // namespace detail

/// Whether the floating-point environment is the one every Kairn guarantee assumes.
///
/// Reads one control register (MXCSR on x86-64, FPCR on AArch64) and checks that the rounding
/// mode is to nearest and that subnormal numbers are neither flushed to zero as results nor read
/// as zero as operands. Kairn never changes these itself; other code can (a directed rounding
/// mode set by an interval library, or flush-to-zero set at startup by any object compiled with
/// -ffast-math), and a program that does must restore them before calling Kairn. Checked before
/// every operation, and in the constructors that check their operands, when KAIRN_CHECKS is 1,
/// before the operands; before a function that does not round, such as a comparison, without the
/// rounding mode, so that a program may call it under a directed one (config.hpp). Only reads.
/// Costs one read of the register:
/// measured at about 2 cycles on an Apple M3, 5 on an Intel Core i5-13500T and 21 on an AMD
/// Zen 2, where storing MXCSR is slow.
///
/// On a target other than x86-64 and AArch64 (or MSVC on AArch64, for which Kairn's kernels do
/// not compile yet), only the rounding mode is checked, through std::fegetround().
/// Not usable in constant evaluation.
inline bool environment_ok() noexcept {
    return (detail::environment_state() & detail::environment_mask(true)) == 0;
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
    // In parentheses, and no name below is `small`: <windows.h> defines min, max and small as
    // macros unless the program asks it not to (tests/api/platform_macros.cpp).
    constexpr T lambda = (std::numeric_limits<T>::min)();    // the smallest normal number
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
    const T half_u = v_small;
    const T s = one + half_u;
    if (s - one != 0) return "the compiler reassociates floating-point sums (-fassociative-math)";
    T ts, te;
    gen::two_sum(one, half_u, ts, te);
    if (ts != one || te != half_u) return "TwoSum is not error-free: the compiler rewrites floating-point sums";
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
KAIRN_GEN_POP_WARNINGS
