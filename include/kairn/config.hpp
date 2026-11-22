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
/// 1 to check, before every operation of Expansion, Ball and Interval that rounds and every
/// building block of blocks.hpp that rounds, and in the constructors that are given limbs, a
/// center or bounds (Expansion<T, 2>::from_limbs, Interval::from_limbs and Ball::from_limbs, the
/// narrowing to one limb, the constructors of Ball and of Interval), first that the floating-point
/// environment is the default one
/// (kairn::environment_ok()), then the operands:
/// - an operator, and a function of kairn:: such as ldexp or to_down, requires each two-limb
///   operand to be canonical: finite and normalized (x0 + x1 == x0 in floating point), (+-inf, 0)
///   or (NaN, NaN); a one-limb operand and a T may be any value;
/// - a function of kairn::finite:: accepts what its cores may return: each two-limb operand
///   normalized, or with a leading limb that is not finite;
/// - a Ball operation requires each ball to be canonical: a finite ball with a canonical center
///   and a radius r >= 0, the whole line, or the empty set;
/// - an Interval operation requires each interval to be canonical: the empty set (+inf, -inf), or
///   bounds lo <= hi, neither a NaN, with lo < +inf and hi > -inf, each of two limbs canonical;
/// - from_limbs requires a canonical pair, Interval::from_limbs and Ball::from_limbs the limbs of a
///   canonical interval and of a canonical ball, a constructor of Ball a canonical center and a radius
///   that is not negative (a NaN radius, which makes the whole line, is accepted), and a
///   constructor of Interval canonical bounds of two limbs (bounds of T may be any value: reversed
///   ones make the empty set, a NaN the whole line, and neither is reported);
/// - fast_two_sum requires |a| >= |b|, and the conversion of the result of two_sum or fast_two_sum
///   to Expansion<T, 2> a pair that is canonical but for the test of normalization, which the
///   block's statement gives: a finite error term with a finite sum, a zero with an infinite one,
///   a NaN with a NaN (blocks.hpp); the other building blocks take any value of T.
///
/// An operand that fails prints a message and calls std::abort(); an environment that fails calls
/// KAIRN_ENVIRONMENT_FAILURE. 0 for no checks. The default is 1 when NDEBUG is not defined, as for
/// assert(). The checks are skipped in constant evaluation, except that an operand that fails them
/// makes the constant expression invalid. Define it the same way in every translation unit of a
/// program.
///
/// Functions that do not round (docs/developer/design/milestone2.md, "Functions that do not
/// round"): their result is the same under every rounding mode, so a program may call them under a
/// directed one, and the rounding mode is not checked before them. The rest of the environment is
/// (flush to zero, which makes a comparison read a subnormal operand as zero), and their operands
/// are checked as above, but only when the rounding mode is to nearest where that check rounds
/// (the test of a canonical pair). They are:
/// - negation and abs of a number of one or two limbs (a sign bit; abs_2 compares and selects);
/// - the comparisons <, <=, >, >=, ==, != of numbers of one and two limbs (comparisons of limbs);
/// - to_nearest, to_down, to_up and abs_upper, and the narrowing to one limb, which is to_nearest
///   (a limb; or a comparison, a step of the bit pattern and a select);
/// - the negation of a Ball (sign bits and a copy of the radius), and its sign predicates
///   certainly_positive(), certainly_negative() and certainly_zero() (comparisons of the radius
///   with the center);
/// - the negation of an Interval, its hull and its intersection (comparisons and selects), and
///   the bounds of an interval of two limbs as numbers of T, lower_as and upper_as (to_down and
///   to_up of a bound);
/// - the predicates of an Interval (is_empty, is_whole, the signs), its member and subset tests
///   (contains, kairn::member; for a point of T of two limbs the guard of make_2, whose value is
///   the point), its three-valued comparisons (kairn::less, less_equal, equal and their mirrors)
///   and the relations of IEEE 1788 (kairn::ieee1788): comparisons and selects;
/// - the constructors of a Ball from a T or from a number or a constant of one limb: Ball<T, 1>(a),
///   Ball<T, 1>(c), Ball<T, 1>(c, r), Ball<T, 1>(q) and Ball<T, 2>(a); and the constructors of an
///   Interval, Interval::from_bounds among them: of one limb, and of two from a T, whose only
///   rounded operations are the guards; of two limbs from numbers of two limbs, comparisons and
///   selects; and Interval::from_limbs and Ball::from_limbs of one limb, the guards and a test of
///   the limbs that does not round. The only rounded operations of
///   these are the guards a + 0, whose value is a under every rounding mode; only the sign of a
///   zero depends on the mode, and Kairn leaves it unspecified;
/// - the conversion of a SumAndError (the result of two_sum or fast_two_sum) to Expansion<T, 2>:
///   the same guards, and a test of the pair that compares and does not round (blocks.hpp);
/// - norm_upper of an array (batch.hpp: magnitudes, comparisons, a step of the bit pattern);
/// - and, with no check at all: next_up and next_down (integer operations on the bit pattern,
///   which no state of the environment changes); as before, the constructors of two limbs from a
///   T or a number of one limb and from_limbs_unchecked (the same guards), sign, isfinite,
///   is_normalized of one limb, the constructors that copy a value (Expansion<T, 1>(a),
///   Expansion<T, 1>::from_limbs), Ball::empty(), Ball::whole(), the accessors center(), radius(),
///   midpoint() and mid_rad() and the tests is_finite(), is_whole(), is_empty() of a Ball,
///   kairn::certainly and kairn::possibly of a Trit, Interval(),
///   Interval::empty(), Interval::whole(), the accessors lower() and upper() and the test
///   is_finite() of an Interval and,
///   for one limb, lower_as and upper_as, the constants of kairn::traits, and kairn::rational
///   (rational.hpp).
/// Every other function rounds and is checked as above: the arithmetic, ldexp and half (of numbers
/// and of balls), the arithmetic of intervals, the functions of kairn::finite::, the building
/// blocks of blocks.hpp but next_up and next_down (two_sum, fast_two_sum, which also checks
/// |a| >= |b|, two_prod, radd, rmul, and the sums and products rounded down and up, which compute
/// under rounding to nearest what rounding down or up gives), from_limbs and is_normalized of two
/// limbs (each tests x0 + x1 == x0), Interval::from_limbs and Ball::from_limbs of two limbs (the
/// same test of a bound or a center), the constructors of Ball<T, 2> from a center or a constant
/// (the test of a canonical center), and the functions of the interface that Ball and Interval
/// share that compute bounds or centers (milestone2.md, "Functions that do not round", its second
/// table): the midpoint, the radius, mid_rad and the split of an Interval, the conversions between
/// Interval and Ball, the ball from an interval of two T (Ball::from_interval and
/// Ball::from_bounds), the bounds of a Ball (lower_as,
/// upper_as, lower and upper), and the narrowing of a Ball to one limb; of a Ball the member and
/// subset tests, the three-valued comparisons, the hull, the intersection and the split, which
/// compute a difference of centers or the conversions to intervals and back; and the functions on
/// arrays of batch.hpp but norm_upper (sum, sum_fast, dot, the maps, conv), which also check the
/// lengths and the arrays that alias, and their elements as an operator does.
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

/// The value of KAIRN_ENCLOSURE_CODE, the default, that forces the operations of Ball and Interval
/// inline.
#define KAIRN_ENCLOSURE_CODE_INLINE 2
/// The value of KAIRN_ENCLOSURE_CODE that makes the operations of Ball and Interval functions of
/// their own.
#define KAIRN_ENCLOSURE_CODE_OUTLINED 4
/// The value of KAIRN_ENCLOSURE_CODE that leaves the operations of Ball and Interval to one
/// translation unit of the program, which includes kairn/definitions.hpp.
#define KAIRN_ENCLOSURE_CODE_EXTERNAL 8

/// @def KAIRN_ENCLOSURE_CODE
/// Where the code of the arithmetic of the enclosures is: of a Ball, + - *, the scaling by a T,
/// and the scaling by a power of two that ldexp and half call; of an Interval, + - *; for one and
/// two limbs (docs/developer/design/milestone2.md, "Inlining and compile time"). One of:
/// - KAIRN_ENCLOSURE_CODE_INLINE, the default: each operation is forced inline into its caller,
///   as every kernel of at most two limbs is. The fastest code, and the longest compilations
///   where many operations are inlined into one function.
/// - KAIRN_ENCLOSURE_CODE_OUTLINED: each is an ordinary function that the compiler is asked not to
///   inline, compiled once per translation unit that uses it, whatever the number of its calls,
///   and kept once by the linker; each call then costs a call at run time. Usable where it was
///   usable before.
/// - KAIRN_ENCLOSURE_CODE_EXTERNAL: each is only declared, for float and double with one and two
///   limbs, and one translation unit of the program defines them all, by including
///   <kairn/definitions.hpp> (with the same settings as the others). The other translation units
///   do not compile them at all.
/// The negation of a Ball, its sign predicates and its constructors, a few instructions each, stay
/// inline in every setting, and so do the steps of ldexp (two or three calls of the scaling by a
/// power of two of T, when 2^n is not one) and everything of Expansion and of blocks.hpp; so do the
/// negation, the constructors, the hull, the intersection, the midpoint, the radius and the split
/// of an Interval, the conversions between Interval and Ball, the bounds and the narrowing of a
/// Ball, and the rest of the interface Ball and Interval share (the predicates, the member and
/// subset tests, the three-valued comparisons, the relations of IEEE 1788, and the hull, the
/// intersection and the split of a Ball), which are constexpr where their kernels are
/// (docs/reference/enclosure.md says which). None of the operations it places is usable in constant
/// evaluation, ldexp and half of a ball and the sum and the difference of intervals of one limb
/// included, whose kernels are constexpr: in the external setting their code is in another
/// translation unit. The three settings compute the same bits: the body of each operation is the
/// same code, the generated kernel force-inlined into it, whose rules R1 to R3 make it immune to
/// what a compiler does at the call boundary or across it. One kernel is not force-inlined in any
/// setting: interval_mul_2, the product of intervals of two limbs, some four hundred operations, is
/// an ordinary inline function, which the compiler may inline or call. With
/// KAIRN_ENCLOSURE_CODE_INLINE the product's checks and the call are inlined into the caller and
/// the kernel is the compiler's choice; with KAIRN_ENCLOSURE_CODE_OUTLINED the product is a function
/// of its own, into which the compiler may inline the kernel or not; with
/// KAIRN_ENCLOSURE_CODE_EXTERNAL the same, compiled in the program's definitions only.
///
/// Define it the same way, before including Kairn, in every translation unit of a program. The
/// operations of OUTLINED and EXTERNAL are in a namespace of their own for each setting and each
/// value of KAIRN_CHECKS, so that a translation unit gets the code of its own settings: one of
/// INLINE and one of OUTLINED in one program each work as they were compiled; one of EXTERNAL whose
/// definitions are missing, or were compiled with another setting or another KAIRN_CHECKS, does
/// not link (an undefined kairn::detail::external... or external_checked:: function). With MSVC
/// and clang-cl a program whose translation units disagree in any way does not link (LNK2038,
/// "mismatch detected for 'kairn_enclosure_code'"). Any other value does not compile. The
/// operations of BallVector (ball_vector.hpp) are ordinary inline functions in every setting: each
/// calls one generated loop, itself an ordinary inline function whose end is never inlined.
#if !defined(KAIRN_ENCLOSURE_CODE)
#define KAIRN_ENCLOSURE_CODE KAIRN_ENCLOSURE_CODE_INLINE
#endif
// (X + 0) is 0 for a value that is empty or a name the preprocessor does not know, and the values
// are not 0 or 1, so that a bare -DKAIRN_ENCLOSURE_CODE is refused too.
#if (KAIRN_ENCLOSURE_CODE + 0) != KAIRN_ENCLOSURE_CODE_INLINE && \
    (KAIRN_ENCLOSURE_CODE + 0) != KAIRN_ENCLOSURE_CODE_OUTLINED && \
    (KAIRN_ENCLOSURE_CODE + 0) != KAIRN_ENCLOSURE_CODE_EXTERNAL
#error "KAIRN_ENCLOSURE_CODE must be KAIRN_ENCLOSURE_CODE_INLINE, KAIRN_ENCLOSURE_CODE_OUTLINED or KAIRN_ENCLOSURE_CODE_EXTERNAL"
#endif

// What KAIRN_ENCLOSURE_CODE makes of an operation: its specifiers (KAIRN_DETAIL_ENCLOSURE), and the
// namespace around its declaration and its definition (KAIRN_DETAIL_ENCLOSURE_BEGIN, _END), inline
// in kairn::detail, whose name says the setting and KAIRN_CHECKS. KAIRN_DETAIL_NOINLINE asks the
// compiler not to inline a function, as KAIRN_GEN_COLD does in the generated code.
#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_DETAIL_NOINLINE __declspec(noinline)
#else
#define KAIRN_DETAIL_NOINLINE __attribute__((noinline))
#endif
#if KAIRN_ENCLOSURE_CODE == KAIRN_ENCLOSURE_CODE_INLINE
#define KAIRN_DETAIL_ENCLOSURE KAIRN_FORCEINLINE
#define KAIRN_DETAIL_ENCLOSURE_BEGIN
#define KAIRN_DETAIL_ENCLOSURE_END
#elif KAIRN_ENCLOSURE_CODE == KAIRN_ENCLOSURE_CODE_OUTLINED
// Function templates, so that each translation unit that uses one compiles its instances once
// and the linker keeps one copy, as of an inline function, without the keyword (with it, GCC
// warns that a declaration without its body is inline and noinline).
#define KAIRN_DETAIL_ENCLOSURE KAIRN_DETAIL_NOINLINE
#if KAIRN_CHECKS
#define KAIRN_DETAIL_ENCLOSURE_BEGIN inline namespace outlined_checked {
#else
#define KAIRN_DETAIL_ENCLOSURE_BEGIN inline namespace outlined {
#endif
#define KAIRN_DETAIL_ENCLOSURE_END }
#else
#define KAIRN_DETAIL_ENCLOSURE KAIRN_DETAIL_NOINLINE
#if KAIRN_CHECKS
#define KAIRN_DETAIL_ENCLOSURE_BEGIN inline namespace external_checked {
#else
#define KAIRN_DETAIL_ENCLOSURE_BEGIN inline namespace external {
#endif
#define KAIRN_DETAIL_ENCLOSURE_END }
#endif
// A macro argument that is nothing.
#define KAIRN_DETAIL_NOTHING
// MSVC's linker refuses objects that record different values under one name.
#if defined(_MSC_VER)
#if KAIRN_ENCLOSURE_CODE == KAIRN_ENCLOSURE_CODE_INLINE
#pragma detect_mismatch("kairn_enclosure_code", "inline")
#elif KAIRN_ENCLOSURE_CODE == KAIRN_ENCLOSURE_CODE_OUTLINED
#pragma detect_mismatch("kairn_enclosure_code", "outlined")
#else
#pragma detect_mismatch("kairn_enclosure_code", "external")
#endif
#endif

// The warnings of MSVC and GCC about a declaration that hides a global variable of the program
// are off for the declarations of each header of Kairn (gen/prelude.hpp says why).
KAIRN_GEN_PUSH_WARNINGS

/// Kairn's public interface: the number types Expansion<T, 1> and Expansion<T, 2>, the balls
/// Ball<T, 1> and Ball<T, 2>, the intervals Interval<T, 1> and Interval<T, 2>, their operations,
/// kairn::traits, kairn::self_test() and
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
