/// @file
/// What Kairn requires of the compiler and its flags, checked where the preprocessor can see it, and
/// the marker that every operation without a checked proof needs.
///
/// The checks follow docs/developer/design/phase0/environment.md ("Compiler flags"): a flag that
/// makes the compiler change the value of a floating-point expression breaks the error-free
/// transformations every kernel is made of, and the result still looks like a k-number. Where such
/// a flag defines a macro, including Kairn fails here. Where it does not (Clang's
/// -fassociative-math, -fno-signed-zeros, -freciprocal-math, and -ffp-model=fast on Apple clang),
/// only kairn::self_test() can tell, at run time (environment.hpp).
#pragma once

#if defined(_MSVC_LANG) ? _MSVC_LANG < 202002L : __cplusplus < 202002L
#error "Kairn needs C++20 (-std=c++20, /std:c++20)"
#endif

#include <cfloat>

#if defined(__FAST_MATH__)
#error "Kairn does not work with -ffast-math, -Ofast or -ffp-model=fast: they let the compiler rewrite the error-free transformations that every Kairn kernel is made of"
#endif
#if defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__
#error "Kairn does not work with -ffinite-math-only: Kairn's results can be infinite or NaN, and its tests for them would be removed"
#endif
#if defined(__ASSOCIATIVE_MATH__)
#error "Kairn does not work with -fassociative-math or -funsafe-math-optimizations: (a + b) - a is not b in floating point, and Kairn's kernels depend on it"
#endif
#if defined(__NO_SIGNED_ZEROS__)
#error "Kairn does not work with -fno-signed-zeros: it lets the compiler turn the product fma(a, b, +0) back into a * b, which can then be contracted"
#endif
#if defined(__RECIPROCAL_MATH__)
#error "Kairn does not work with -freciprocal-math: it changes the value of quotients"
#endif
#if defined(_M_FP_FAST)
#error "Kairn does not work with /fp:fast: it lets the compiler rewrite the error-free transformations that every Kairn kernel is made of; use /fp:precise (the default), /fp:strict or /fp:contract"
#endif
// Each operation of float and double must be rounded to its own type: x87 evaluation (32-bit x86
// without SSE2), or Clang's -ffp-eval-method=double, rounds to a wider format first.
#if defined(FLT_EVAL_METHOD) && FLT_EVAL_METHOD != 0
#error "Kairn needs every float and double operation rounded to its own type (FLT_EVAL_METHOD == 0): no x87 evaluation, no -ffp-eval-method other than source"
#endif

// The kernels' own checks: hardware FMA on x86, and the force-inline macro.
#include "gen/prelude.hpp"

#include <cstdio>
#include <cstdlib>
#include <type_traits>

/// Forces a function to be inlined: kernels of at most two limbs, and everything that forwards to
/// them, must disappear into the caller (docs/developer/design/phase0/library.md, "Inlining and
/// compile time").
#define KAIRN_FORCEINLINE KAIRN_GEN_FORCEINLINE

/// @def KAIRN_CHECKS
/// 1 to check, before every operation of Expansion and Ball (all but sign, isfinite,
/// is_normalized and the accessors of Ball, which only read limbs) and in the constructors that
/// are given limbs or a center (Expansion<T, 2>::from_limbs, the narrowing to one limb, the
/// constructors of Ball), first that the floating-point environment is the default one
/// (kairn::environment_ok()), then the operands:
/// - an operator, and a function of kairn:: such as ldexp or to_down, requires each two-limb
///   operand to be canonical: finite and normalized (x0 + x1 == x0 in floating point), (+-inf, 0)
///   or (NaN, NaN); a one-limb operand and a T may be any value;
/// - a function of kairn::finite:: accepts what its cores may return: each two-limb operand
///   normalized, or with a leading limb that is not finite;
/// - a Ball operation requires each ball to be canonical: a finite ball with a canonical center
///   and a radius r >= 0, the whole line, or the empty set;
/// - from_limbs requires a canonical pair, and a constructor of Ball a canonical center and a
///   radius that is not negative (a NaN radius, which makes the empty set, is accepted).
///
/// An operand that fails prints a message and calls std::abort(); an environment that fails calls
/// KAIRN_ENVIRONMENT_FAILURE. 0 for no checks. The default is 1 when NDEBUG is not defined, as for
/// assert(). The checks are skipped in constant evaluation, except that an operand that fails them
/// makes the constant expression invalid. Define it the same way in every translation unit of a
/// program.
#if !defined(KAIRN_CHECKS)
#if defined(NDEBUG)
#define KAIRN_CHECKS 0
#else
#define KAIRN_CHECKS 1
#endif
#endif

/// @def KAIRN_ENVIRONMENT_FAILURE(reason)
/// What a check of KAIRN_CHECKS does when the floating-point environment is not the default one:
/// by default, prints the reason (a string literal) to the standard error and calls std::abort().
/// A program may define it, before including Kairn, as any statement. If it returns, the operation
/// (or the constructor) continues without checking its operands, since those checks compute in
/// the environment that failed (under a directed rounding mode x0 + x1 == x0 can be false for a
/// canonical pair), and its result has no guarantee.
#if !defined(KAIRN_ENVIRONMENT_FAILURE)
#define KAIRN_ENVIRONMENT_FAILURE(reason) ::kairn::detail::fail("the floating-point environment", reason)
#endif

// KAIRN_K1_CONTRACT, which a program defines (before including Kairn) and Kairn never does: lets
// Clang fuse a product and a sum of Expansion<T, 1> into one FMA, as it does for plain T under its
// default -ffp-contract=on (decision D6 of docs/developer/design/phase0/decisions.md). Without it,
// a * b + c on Expansion<T, 1> is two roundings under Clang's default where the same expression on
// T is one; both are correct, and with -ffp-contract=off or =fast, and on GCC and MSVC, the two
// already agree. With it, the one-limb operations fuse even when the program is compiled with
// -ffp-contract=off. No effect on other compilers, and none on any kernel of two limbs.
#if defined(KAIRN_K1_CONTRACT) && defined(__clang__)
#define KAIRN_DETAIL_K1_CONTRACT _Pragma("clang fp contract(fast)")
#else
#define KAIRN_DETAIL_K1_CONTRACT
#endif

// The warnings of MSVC and GCC about a declaration that hides a global variable of the program
// are off for the declarations of each header of Kairn (gen/prelude.hpp says why).
KAIRN_GEN_PUSH_WARNINGS

/// Kairn's public interface: the number types Expansion<T, 1> and Expansion<T, 2>, the balls
/// Ball<T, 1> and Ball<T, 2>, their operations, kairn::traits, kairn::self_test() and
/// kairn::environment_ok(), with T float or double. The namespaces kairn::detail and kairn::gen
/// are not part of it.
namespace kairn {

/// The marker of an operation whose proof is not checked yet ("UNVERIFIED").
///
/// An operation whose kernel is not `proved` in gen/claims.json is available only when one of its
/// operands is wrapped in kairn::unverified(): `kairn::unverified(x) - y`, `x < kairn::unverified(y)`,
/// `kairn::to_down(kairn::unverified(x))`, `x -= kairn::unverified(y)`. The wrapper changes nothing
/// else: the operation is the same code, and its result is an ordinary value, without the marker.
/// Written without it, the operation does not compile.
///
/// What the marker means: the operation has a statement (in gen/claims.json and the reference
/// pages) and is tested against it, but no proof of that statement has been checked by Rocq, so
/// it is a target and not a guarantee, and kairn::traits exports no constants for it. When the
/// proof is checked, the generator marks the kernel `proved` and the operation compiles without
/// the marker; code that still writes it keeps compiling.
///
/// Holds a copy of its operand (a few limbs). Has no operations of its own except those that
/// take it as an operand; for a limb type T it also converts to T, so that code generic over
/// float, double and Kairn's types can write the marker everywhere.
template <class X>
struct Unverified;

/// The marked form of a limb, for code generic over float, double and Kairn's types.
template <>
struct Unverified<double> {
    double value;  ///< The operand.
    /// The operand itself: the operations of double are IEEE 754's, about which Kairn claims nothing.
    constexpr operator double() const noexcept { return value; }
};
/// The marked form of a limb, for code generic over float, double and Kairn's types.
template <>
struct Unverified<float> {
    float value;  ///< The operand.
    /// The operand itself: the operations of float are IEEE 754's, about which Kairn claims nothing.
    constexpr operator float() const noexcept { return value; }
};

/// Marks an operand of a double operation; see kairn::Unverified.
constexpr Unverified<double> unverified(double x) noexcept { return {x}; }
/// Marks an operand of a float operation; see kairn::Unverified.
constexpr Unverified<float> unverified(float x) noexcept { return {x}; }

namespace detail {

/// The limb types.
template <class T>
concept limb = std::is_same_v<T, float> || std::is_same_v<T, double>;

/// Whether the kernel described by K (one of kairn::gen::bounds) is proved: the constraint of
/// every operation that needs no marker.
template <class K>
concept proof_checked = K::proved;

template <class X>
struct is_marked_t : std::false_type {};
template <class X>
struct is_marked_t<Unverified<X>> : std::true_type {};
/// Whether X is a marked operand, Unverified<Y>.
template <class X>
concept marked = is_marked_t<std::remove_cvref_t<X>>::value;

/// An operand without its marker.
template <class X>
KAIRN_FORCEINLINE constexpr const X& unmark(const X& x) noexcept {
    return x;
}
template <class X>
KAIRN_FORCEINLINE constexpr const X& unmark(const Unverified<X>& x) noexcept {
    return x.value;
}

/// The failure of a check (KAIRN_CHECKS). Never constexpr: reaching it in constant evaluation
/// makes the expression invalid, which is how a failed check shows at compile time.
[[noreturn]] inline void fail(const char* what, const char* reason) noexcept {
    std::fprintf(stderr, "kairn: %s: %s\n", what, reason);
    std::abort();
}

}  // namespace detail
}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
