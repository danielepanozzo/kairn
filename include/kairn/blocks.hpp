/// @file
/// The building blocks on T: functions of float and double that the operations of Kairn are made
/// of, for a program's own tests of exactness, its own radius arithmetic, and bounds rounded down
/// or up without changing the rounding mode (docs/developer/design/milestone2.md, "Building blocks
/// on T"). Each is one call of a generated kernel; the comment of each names it and quotes its
/// statement.
///
/// They are function templates of namespace kairn, for T float or double, with both operands of
/// the same type T: a program's own function of the same name (next_up is a common one) is not
/// hidden, and argument-dependent lookup does not find these for an operand of type double or
/// float, so they are called as kairn::next_up(a). Like every operation they need the marker
/// kairn::unverified on an operand while gen/claims.json does not mark their kernel proved.
///
/// Values that enter from the program: a block that adds its operands calls the entry form of its
/// kernel, which guards each operand (a + 0) before adding it (rule R3 of
/// docs/developer/architecture.md), so that a product the program computes and passes in, as in
/// two_sum(a * b, c), is not fused into the block's first addition by a compiler that contracts.
/// One exception, documented and not repaired: a square, two_sum(a * a, c), with Clang under
/// -ffp-contract=fast, which proves a square is never -0, removes the guard and fuses it
/// (docs/getting-started/guarantees.md, "The exception: a square"); kairn::self_test() reports it
/// in Status::limitation, for the translation unit that calls it.
/// The guard has the value of its operand; only the sign of a zero result can change, and the sign
/// of a zero is not part of any statement.
///
/// Rounding: every block but next_up and next_down computes with operations rounded to nearest and
/// is preceded, when KAIRN_CHECKS is 1, by the check of the floating-point environment, the
/// rounding mode included (config.hpp). next_up and next_down are integer operations on the bit
/// pattern, which no state of the environment can change, and are checked for nothing.
///
/// Constant evaluation: every block is constexpr but mul_down and mul_up, whose listings trust the
/// sign of the error term of a fused product, which constant evaluation, without a fused
/// multiply-add, computes otherwise (milestone2.md, "Building blocks on T").
#pragma once

#include "config.hpp"
#include "environment.hpp"
#include "expansion.hpp"
#include "gen/bounds.hpp"
#include "gen/scalar.hpp"

#include <type_traits>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

namespace detail {
// The check of KAIRN_CHECKS before the conversion of a SumAndError to Expansion<T, 2>: the
// environment without the rounding mode, then the pair is canonical but for the test of
// normalization, which the statement of the block gives (finite limbs; an infinity and a zero; two
// NaN). Written with == and != only, which no constant evaluator gets wrong on a NaN.
template <limb T>
KAIRN_FORCEINLINE constexpr void check_sum_pair([[maybe_unused]] T s, [[maybe_unused]] T e) noexcept {
#if KAIRN_CHECKS
    const bool ok = finite(s) ? finite(e) : (s == s ? e == 0 : e != e);
    if (check_environment_except_rounding() && !ok)
        fail("SumAndError", "the sum and the error term are not a canonical pair (an infinite operand, a sum that "
                            "overflows, or two_sum with |b| the largest finite number), so the conversion to "
                            "Expansion<T, 2> has no guarantee");
#endif
}
}  // namespace detail

/// The result of kairn::two_sum and kairn::fast_two_sum: the sum of a and b rounded to nearest,
/// and the error term, the number that the rounding left out.
///
/// When both members are finite (always, for finite operands whose sum does not overflow, but for
/// the corner of two_sum given below) they are exact: sum + error = a + b, and the pair
/// (sum, error) is normalized (sum is error + sum rounded to nearest), so that it is the canonical
/// two-limb number of value a + b; the explicit conversion to Expansion<T, 2> gives that number.
/// Two named members rather than a std::pair, since which is the rounded sum matters; it is an
/// aggregate, so `auto [s, e] = kairn::two_sum(a, b);` binds them in that order.
template <class T>
struct SumAndError {
    static_assert(detail::limb<T>, "SumAndError<T>: T is float or double");
    /// a + b rounded to nearest, ties to even: the result of IEEE 754's addition.
    T sum{};
    /// a + b - sum: exact, and a number of T, whenever both members are finite.
    T error{};

    /// The two-limb number (sum, error), through Expansion<T, 2>::from_limbs_unchecked, without
    /// the test of normalization, which the statement of the block makes unnecessary.
    ///
    /// Valid, that is a canonical number of value a + b exactly, exactly when both members are
    /// finite. For two_sum that holds whenever a and b are finite, their sum does not overflow and
    /// |b| < Omega (the largest finite number of T): with b = +-Omega the error term can be a NaN
    /// although the sum is finite (two_sum(-1.5 ulp(Omega), Omega) has sum Omega - ulp(Omega) and a
    /// NaN error term, because sum - a overflows). For fast_two_sum it holds whenever |a| >= |b|
    /// and the sum is finite (its error term is finite whenever its sum is); with |a| < |b| the
    /// pair need not be a + b, nor normalized. Two NaN operands give (NaN, NaN), the canonical NaN.
    /// Otherwise (an infinite operand, a sum that overflows, the corner above) the error term is a
    /// NaN or an infinity, the pair is not canonical, and operations on the number have no
    /// guarantee, as for any pair that is not canonical given to from_limbs_unchecked.
    ///
    /// When KAIRN_CHECKS is 1 that last case is reported (a finite sum with an error term that is
    /// not finite, or an infinite sum with an error term other than a zero), after the check of
    /// the environment without the rounding mode: the conversion does not round, its only rounded
    /// operations being the guards of from_limbs_unchecked, whose values are the limbs under every
    /// rounding mode (only the sign of a zero depends on the mode). In constant evaluation such a
    /// pair makes the expression invalid.
    explicit constexpr operator Expansion<T, 2>() const noexcept
        requires detail::proof_checked<gen::bounds::make_2_limbs<T>>
    {
        detail::check_sum_pair(sum, error);
        const T limbs[2] = {sum, error};
        return Expansion<T, 2>::from_limbs_unchecked(limbs);
    }
};

/// The result of kairn::two_prod: the product of a and b rounded to nearest, and the error term.
/// Two named members, as SumAndError; an aggregate, so `auto [p, e] = kairn::two_prod(a, b);`
/// binds them in that order. Unlike that of a sum, the exact error of a product below
/// 2^(2p-1) eta in magnitude (2^-969 for double) need not be a number of T, and the error term is
/// then its rounding: the pair is not offered as a two-limb number, which would not always be the
/// product.
template <class T>
struct ProductAndError {
    static_assert(detail::limb<T>, "ProductAndError<T>: T is float or double");
    /// a * b rounded to nearest, ties to even: the result of IEEE 754's multiplication.
    T product{};
    /// a * b - product rounded to nearest: exact when a * b is zero or at least 2^(2p-1) eta in
    /// magnitude; within eta/2 of it otherwise (13/8 eta in constant evaluation).
    T error{};
};

namespace detail {

// The requirement of fast_two_sum, |a| >= |b|, after the environment, under KAIRN_CHECKS. A NaN
// operand is not reported (the comparison is false), nor anything when KAIRN_ENVIRONMENT_FAILURE
// returned.
template <limb T>
KAIRN_FORCEINLINE constexpr void check_ordered([[maybe_unused]] T a, [[maybe_unused]] T b) noexcept {
#if KAIRN_CHECKS
    if (check_environment() && gen::abs_bits(b) > gen::abs_bits(a))
        fail("fast_two_sum", "|a| < |b|, which its requirement |a| >= |b| excludes (two_sum takes any order)");
#endif
}

// The blocks, without their markers and constraints: one kernel each.
template <limb T>
KAIRN_FORCEINLINE constexpr SumAndError<T> two_sum(T a, T b) noexcept {
    check_environment();
    SumAndError<T> r;
    gen::two_sum_entry(a, b, r.sum, r.error);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr SumAndError<T> fast_two_sum(T a, T b) noexcept {
    check_ordered(a, b);
    SumAndError<T> r;
    gen::fast_two_sum_entry(a, b, r.sum, r.error);
    return r;
}
/// Called by kairn::two_prod in constant evaluation when its operands are finite and its error
/// term is not, which makes the expression invalid: the compiler's message names this function.
/// There the kernel runs Dekker's product, one of whose operations overflowed, and the run-time
/// result is another (kairn::two_prod says when).
inline void two_prod_overflows_in_constant_evaluation() noexcept {
    fail("two_prod", "an operation of Dekker's product overflows in constant evaluation");
}

// a and b are guarded by the kernel (two_prod_entry): they are factors of the fms of TwoProd, and a
// compiler that sees one of them to be 1 would fuse a product of the program into it. In constant
// evaluation, where the kernel runs Dekker's product on the operands as they are, finite operands
// with an error term that is not finite are refused (bit tests after the kernel, no arithmetic);
// at run time the test is not compiled.
template <limb T>
KAIRN_FORCEINLINE constexpr ProductAndError<T> two_prod(T a, T b) noexcept {
    check_environment();
    ProductAndError<T> r;
    gen::two_prod_entry(a, b, r.product, r.error);
    if (__builtin_is_constant_evaluated() && finite(a) && finite(b) && !finite(r.error))
        two_prod_overflows_in_constant_evaluation();
    return r;
}
// Integer operations on the bit pattern: nothing to check.
template <limb T>
KAIRN_FORCEINLINE constexpr T next_up(T a) noexcept {
    T r = T(0);
    gen::next_up(a, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr T next_down(T a) noexcept {
    T r = T(0);
    gen::next_down(a, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr T radd(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::radd_entry(a, b, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr T rmul(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::rmul(a, b, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr T add_down(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::add_down_entry(a, b, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr T add_up(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::add_up_entry(a, b, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr T sub_down(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::sub_down_entry(a, b, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE constexpr T sub_up(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::sub_up_entry(a, b, r);
    return r;
}
// Not constexpr: the kernels are stated for the fused product only.
template <limb T>
KAIRN_FORCEINLINE T mul_down(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::mul_down_entry(a, b, r);
    return r;
}
template <limb T>
KAIRN_FORCEINLINE T mul_up(T a, T b) noexcept {
    check_environment();
    T r = T(0);
    gen::mul_up_entry(a, b, r);
    return r;
}

/// Whether one of the two operands of a block is marked, the operation being otherwise that of
/// the unmarked block (the marked form exists only where the detail function does).
template <class X, class Y>
concept marked_block_pair = marked<X> || marked<Y>;

}  // namespace detail

// The blocks. Each has a form without the marker, constrained on its kernel's proof, and a form
// with kairn::unverified on an operand.

/// a + b as its rounded sum and the error of that rounding (kernel two_sum_entry: TwoSum on the
/// operands guarded). Rounds; constexpr, with the same values in constant evaluation (a zero
/// result can differ in sign: the guard is left out there).
///
/// Statement, proved: sum = RN(a + b) and sum + error = a + b exactly, for finite a and b when
/// no operation of the listing overflows; error is finite, and the statement holds, whenever sum
/// is finite and |b| < Omega. Outside: sum is IEEE 754's sum in every case; with b = +-Omega the
/// error term can be a NaN although the sum is finite; an infinite or NaN operand gives a NaN error
/// term. SumAndError says when the pair converts to Expansion<T, 2>.
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::two_sum_entry<T>>
KAIRN_FORCEINLINE constexpr SumAndError<T> two_sum(T a, T b) noexcept {
    return detail::two_sum(a, b);
}
/// two_sum with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto two_sum(const X& a, const Y& b) noexcept
    -> decltype(detail::two_sum(detail::unmark(a), detail::unmark(b))) {
    return detail::two_sum(detail::unmark(a), detail::unmark(b));
}

/// a + b as its rounded sum and the error of that rounding, for |a| >= |b|, in three operations
/// instead of six (kernel fast_two_sum_entry: Fast2Sum on the operands guarded). Rounds; constexpr,
/// with the same values in constant evaluation (a zero result can differ in sign).
///
/// Requires |a| >= |b|; when KAIRN_CHECKS is 1, a call with |a| < |b| stops the program with a
/// message (after the check of the environment), and makes a constant expression invalid.
/// Statement, proved: sum = RN(a + b), sum + error = a + b exactly, and (sum, error) normalized,
/// for finite a and b with |a| >= |b| when no operation overflows; its error term is finite
/// whenever its sum is. Outside the requirement, in a build without the checks: sum is still
/// RN(a + b) and error a number of T, but sum + error need not be a + b
/// (fast_two_sum(2^-60, 1.0) is (1, 0)).
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::fast_two_sum_entry<T>>
KAIRN_FORCEINLINE constexpr SumAndError<T> fast_two_sum(T a, T b) noexcept {
    return detail::fast_two_sum(a, b);
}
/// fast_two_sum with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto fast_two_sum(const X& a, const Y& b) noexcept
    -> decltype(detail::fast_two_sum(detail::unmark(a), detail::unmark(b))) {
    return detail::fast_two_sum(detail::unmark(a), detail::unmark(b));
}

/// a b as its rounded product and the error of that rounding (kernel two_prod_entry: TwoProd with a
/// fused multiply-add on the guarded operands; in constant evaluation the variant two_prod_dekker,
/// Dekker's product).
/// Rounds; constexpr, on the operands given below.
///
/// Statement, proved: product = RN(a b), |product + error - a b| <= eta/2, and product + error =
/// a b exactly when a b = 0 or |a b| >= 2^(2p-1) eta (2^-969 for double, 2^-102 for float), for
/// finite a and b when the product does not overflow. A product that overflows gives an infinite
/// product and the opposite infinity as the error term.
///
/// Constant evaluation runs Dekker's product, which splits a and b into halves and adds four
/// partial products: a split, or the product of the leading halves, can overflow where a b does
/// not. With finite operands the call is a constant expression only when its error term is
/// finite, which is when none of those operations overflows. Otherwise it is not one: a program
/// that needs one (a constexpr variable, a static_assert) does not compile, and the compiler's
/// message names detail::two_prod_overflows_in_constant_evaluation (GCC, which refuses an
/// overflow itself, names the operation that overflowed); a variable of static storage duration
/// that is not constexpr is initialized at run time, with the run-time result. It is one when
/// |a| <= 2^996, |b| <= 2^996 and |a b| <= 2^1023 (2^115, 2^115 and 2^127 for float): a sufficient
/// condition, not an exact one (the square of 0x1.ffffffbffffffp+511 is one, that of
/// 0x1.fffffffffffffp+511 is not). Where it is one the statement holds with 13/8 eta for eta/2,
/// and the values are those of run time when the product is exact (proved; a zero product can
/// differ in sign); below the threshold each execution has its own error term, within its own
/// bound. A product that overflows is not one either, nor, with GCC or Clang, an infinite operand
/// (the split computes inf - inf); a NaN operand is not with Clang, and gives two NaN with GCC,
/// as at run time.
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::two_prod_entry<T>>
KAIRN_FORCEINLINE constexpr ProductAndError<T> two_prod(T a, T b) noexcept {
    return detail::two_prod(a, b);
}
/// two_prod with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto two_prod(const X& a, const Y& b) noexcept
    -> decltype(detail::two_prod(detail::unmark(a), detail::unmark(b))) {
    return detail::two_prod(detail::unmark(a), detail::unmark(b));
}

/// The next number of T above a, IEEE 754's nextUp, on every value of T (kernel next_up).
/// Does not round: an integer operation on the bit pattern, the same under every state of the
/// floating-point environment, and not checked at all when KAIRN_CHECKS is 1 (config.hpp).
/// constexpr, with the same bits in constant evaluation.
///
/// Statement, proved: a NaN gives a NaN; +inf and Omega give +inf; a finite number below Omega the
/// smallest number of T above it, so that either zero gives eta (the smallest subnormal number),
/// -eta gives -0, and a negative number the next one toward zero; -Omega the number after it; -inf
/// gives -Omega, a finite number.
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::next_up<T>>
KAIRN_FORCEINLINE constexpr T next_up(T a) noexcept {
    return detail::next_up(a);
}
/// next_up with a marked operand.
/// Does not round: not checked at all (config.hpp).
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto next_up(const X& a) noexcept -> decltype(detail::next_up(detail::unmark(a))) {
    return detail::next_up(detail::unmark(a));
}

/// The next number of T below a, IEEE 754's nextDown, on every value of T (kernel next_down).
/// Does not round: an integer operation on the bit pattern, the same under every state of the
/// floating-point environment, and not checked at all when KAIRN_CHECKS is 1 (config.hpp).
/// constexpr, with the same bits in constant evaluation.
///
/// Statement, proved: a NaN gives a NaN; -inf and -Omega give -inf; a finite number above -Omega
/// the largest number of T below it, so that either zero gives -eta, eta gives +0, and a positive
/// number the previous one toward zero; Omega the number before it; +inf gives Omega.
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::next_down<T>>
KAIRN_FORCEINLINE constexpr T next_down(T a) noexcept {
    return detail::next_down(a);
}
/// next_down with a marked operand.
/// Does not round: not checked at all (config.hpp).
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto next_down(const X& a) noexcept -> decltype(detail::next_down(detail::unmark(a))) {
    return detail::next_down(detail::unmark(a));
}

/// An upper bound of a + b for radii: the number after a + b rounded to nearest (kernel
/// radd_entry: radd on the operands guarded). Rounds; constexpr, with the same bits in constant
/// evaluation.
///
/// Statement, proved for a, b >= 0: r >= a + b, and r exceeds a + b by at most 3/2 gaps of T at r
/// (r - next_down(r)); +inf when the sum overflows. A NaN operand gives a NaN, an infinite one
/// +inf (or a NaN for +inf and -inf). With a negative operand the result is still not below
/// a + b, and can exceed it by 2 gaps instead of 3/2 (measured, not claimed).
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::radd_entry<T>>
KAIRN_FORCEINLINE constexpr T radd(T a, T b) noexcept {
    return detail::radd(a, b);
}
/// radd with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto radd(const X& a, const Y& b) noexcept
    -> decltype(detail::radd(detail::unmark(a), detail::unmark(b))) {
    return detail::radd(detail::unmark(a), detail::unmark(b));
}

/// An upper bound of a b for radii: the number after a b rounded to nearest (kernel rmul).
/// Rounds; constexpr, with the same bits in constant evaluation (the plain product there, whose
/// zero can have the other sign, and the step after either zero is eta).
///
/// Statement, proved for a, b >= 0: r >= a b, and r exceeds a b by at most 3/2 gaps of T at r;
/// +inf when the product overflows. A NaN operand, or 0 times inf, gives a NaN; otherwise an
/// infinite operand gives +inf. With a negative operand the result is still not below a b, and
/// can exceed it by 2 gaps (measured, not claimed).
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::rmul<T>>
KAIRN_FORCEINLINE constexpr T rmul(T a, T b) noexcept {
    return detail::rmul(a, b);
}
/// rmul with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto rmul(const X& a, const Y& b) noexcept
    -> decltype(detail::rmul(detail::unmark(a), detail::unmark(b))) {
    return detail::rmul(detail::unmark(a), detail::unmark(b));
}

/// a + b rounded down: the largest number of T not above a + b, computed under rounding to nearest
/// (kernel add_down_entry: add_down_1, the sum of two_sum_ord and the sign of its error term, on
/// the operands guarded). Rounds (it assumes rounding to nearest, and computes what rounding down
/// would); constexpr, with the same values in constant evaluation (a zero result can differ in
/// sign).
///
/// Statement, proved, for any two values of T: for finite operands, RD(a + b) in the format with
/// overflow (Omega for a sum above Omega, -inf for one below -Omega); for an infinite or NaN
/// operand, IEEE 754's sum (a NaN for +inf + -inf).
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::add_down_entry<T>>
KAIRN_FORCEINLINE constexpr T add_down(T a, T b) noexcept {
    return detail::add_down(a, b);
}
/// add_down with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto add_down(const X& a, const Y& b) noexcept
    -> decltype(detail::add_down(detail::unmark(a), detail::unmark(b))) {
    return detail::add_down(detail::unmark(a), detail::unmark(b));
}

/// a + b rounded up: the smallest number of T not below a + b, computed under rounding to nearest
/// (kernel add_up_entry: add_up_1 on the operands guarded). Rounds; constexpr, with the same values
/// in constant evaluation (a zero result can differ in sign).
///
/// Statement, proved, for any two values of T: for finite operands, RU(a + b) in the format with
/// overflow (+inf for a sum above Omega, -Omega for one below -Omega); for an infinite or NaN
/// operand, IEEE 754's sum.
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::add_up_entry<T>>
KAIRN_FORCEINLINE constexpr T add_up(T a, T b) noexcept {
    return detail::add_up(a, b);
}
/// add_up with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto add_up(const X& a, const Y& b) noexcept
    -> decltype(detail::add_up(detail::unmark(a), detail::unmark(b))) {
    return detail::add_up(detail::unmark(a), detail::unmark(b));
}

/// a - b rounded down: the largest number of T not above a - b, computed under rounding to nearest
/// (kernel sub_down_entry: sub_down_1, the sum rounded down of a and -b, on the operands guarded).
/// Rounds; constexpr, with the same values in constant evaluation (a zero result can differ in
/// sign).
///
/// Statement, proved, for any two values of T: for finite operands, RD(a - b) in the format with
/// overflow; for an infinite or NaN operand, IEEE 754's difference (a NaN for +inf - +inf).
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::sub_down_entry<T>>
KAIRN_FORCEINLINE constexpr T sub_down(T a, T b) noexcept {
    return detail::sub_down(a, b);
}
/// sub_down with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto sub_down(const X& a, const Y& b) noexcept
    -> decltype(detail::sub_down(detail::unmark(a), detail::unmark(b))) {
    return detail::sub_down(detail::unmark(a), detail::unmark(b));
}

/// a - b rounded up: the smallest number of T not below a - b, computed under rounding to nearest
/// (kernel sub_up_entry: sub_up_1 on the operands guarded). Rounds; constexpr, with the same values
/// in constant evaluation (a zero result can differ in sign).
///
/// Statement, proved, for any two values of T: for finite operands, RU(a - b) in the format with
/// overflow; for an infinite or NaN operand, IEEE 754's difference.
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::sub_up_entry<T>>
KAIRN_FORCEINLINE constexpr T sub_up(T a, T b) noexcept {
    return detail::sub_up(a, b);
}
/// sub_up with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto sub_up(const X& a, const Y& b) noexcept
    -> decltype(detail::sub_up(detail::unmark(a), detail::unmark(b))) {
    return detail::sub_up(detail::unmark(a), detail::unmark(b));
}

/// A lower bound of a b: the product rounded to nearest, stepped down when the sign of the error
/// term of TwoProd says that it is above a b (kernel mul_down_entry). Rounds. Not usable in constant
/// evaluation: its statement is about the fused product, whose error term below 2^(2p-1) eta
/// Dekker's product, the only one constant evaluation has, computes otherwise and can give with
/// the other sign (milestone2.md, "Building blocks on T").
///
/// Statement, proved, for any two values of T: for finite operands, r <= a b, and r is RD(a b) or
/// the number before it; r = RD(a b) exactly when a b = 0 or |a b| >= 2^(2p-1) eta (2^-969 for
/// double, 2^-102 for float), in the format with overflow (Omega for a product above Omega, -inf
/// for one below -Omega); for an infinite or NaN operand, IEEE 754's product (a NaN for 0 inf).
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::mul_down_entry<T>>
KAIRN_FORCEINLINE T mul_down(T a, T b) noexcept {
    return detail::mul_down(a, b);
}
/// mul_down with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE auto mul_down(const X& a, const Y& b) noexcept
    -> decltype(detail::mul_down(detail::unmark(a), detail::unmark(b))) {
    return detail::mul_down(detail::unmark(a), detail::unmark(b));
}

/// An upper bound of a b: the product rounded to nearest, stepped up when the sign of the error
/// term of TwoProd says that it is below a b (kernel mul_up_entry). Rounds. Not usable in constant
/// evaluation, for the reason given at mul_down.
///
/// Statement, proved, for any two values of T: for finite operands, r >= a b, and r is RU(a b) or
/// the number after it; r = RU(a b) exactly when a b = 0 or |a b| >= 2^(2p-1) eta, in the format
/// with overflow (+inf for a product above Omega, -Omega for one below -Omega); for an infinite or
/// NaN operand, IEEE 754's product.
template <class T>
    requires detail::limb<T> && detail::proof_checked<gen::bounds::mul_up_entry<T>>
KAIRN_FORCEINLINE T mul_up(T a, T b) noexcept {
    return detail::mul_up(a, b);
}
/// mul_up with a marked operand.
template <class X, class Y>
    requires detail::marked_block_pair<X, Y>
KAIRN_FORCEINLINE auto mul_up(const X& a, const Y& b) noexcept
    -> decltype(detail::mul_up(detail::unmark(a), detail::unmark(b))) {
    return detail::mul_up(detail::unmark(a), detail::unmark(b));
}

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
