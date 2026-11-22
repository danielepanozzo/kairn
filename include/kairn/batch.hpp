/// @file
/// Functions on arrays of k-numbers (docs/developer/design/milestone2.md, "Batch kernels"): the sum
/// and the dot product, which return one number; the maps add, sub, scale, mul_pow2 and axpy, which
/// write an array; the convolution conv, the coefficients of the product of two polynomials; and
/// norm_upper, an upper bound of the largest magnitude. For T float or double and k = 1 or 2.
///
/// The arrays are views, kairn::SoAView<T, k> (soa.hpp): one array of limbs per limb and a length.
/// An array that a function only reads is a view of T or of const T; an array it writes is a view
/// of T. A view of one limb is a plain array of T: a program that holds `const double* p` and a
/// length n passes `kairn::SoAView<const double, 1>(p, n)`, and for two limbs
/// `kairn::SoAView<const double, 2>(hi, lo, n)`, the leading limbs first; an SoA passes as
/// `a.view()`. Every view of one call has the same limb type and the same k: a sum of float and
/// double arrays, or of arrays of one and of two limbs, does not compile.
///
/// Nothing here computes: each function checks what KAIRN_CHECKS checks and calls one loop of the
/// generated headers (include/kairn/gen/scalar.hpp, gen/avx2.hpp, gen/neon.hpp), a fold of the
/// generator (docs/developer/architecture.md, "Folds", "Maps", "Folds of maxima",
/// "Convolutions"), whose claims are in gen/claims.json ("folds") and whose statements are proved
/// in the real model and in the IEEE model for every length and every number of lanes. The comment
/// of each function names its loop and states what the loop claims, and no more.
///
/// The arrays come from the program, which may have filled them with products in the same
/// function: a compiler that inlines the loop could fuse such a product into the loop's first
/// addition (rule R3 of docs/developer/architecture.md). So every function calls the loop on
/// supplied arrays (milestone2.md, "Arrays that the program fills"): the sums and the maps that
/// add an element are the loops named _entry, whose steps pass each limb that they add through the
/// guard a + 0 first; the dot product of one limb is the loop dot_1_entry, whose step guards both
/// factors of its fused operation, because a compiler that sees one of them to be 1 (an array of
/// ones) rewrites fma(x, 1, s) as x + s and fuses the program's product x into it (rule R3, the
/// factors of a fused operation: measured with Clang 18 on x86-64 and Apple clang 21 under
/// -ffp-contract=fast); scale, mul_pow2, the x of axpy, the dot product of two limbs and conv
/// only multiply their elements and are called without a guard (gen/kairn-gen build lists the
/// factors that are not guarded; the owner decided on 2026-11-21 that every one is to be guarded,
/// and those not guarded yet are on the generator's pending list, being closed). The loops on
/// stored arrays (sum_1,
/// sum_2, add_2, axpy_2, ...), for containers whose elements only Kairn writes, have no caller here:
/// no container of this library is such.
///
/// The order of summation. sum, sum_fast and dot are folds whose result depends on the order of its
/// additions; one theorem bounds every order by the same expression of the length
/// (milestone2.md, "Summation over any tree"), so that their statement is the same in both orders
/// the loops are emitted in:
/// - by default, the lane order with W = Packed<T, k>::lanes lanes (packed.hpp: 4 lanes of double
///   and 8 of float for AVX2, 2 and 4 for NEON, 1 in the scalar form): element i to lane i mod W of
///   the first W floor(n / W), each lane summed from zero, the lanes combined from lane 0 upward, the
///   rest added in order. It is the packed loop, the fast one, and its bits depend on the
///   instruction set the translation unit is compiled for (KAIRN_PACKED_FORM); with one lane, and
///   with fewer elements than lanes, it is the sequential order;
/// - with the argument kairn::sequential, the sequential order: element after element, from zero.
///   Its bits are the same on every platform and in every form.
/// The maps write each element from the elements of the same index alone, so their results do not
/// depend on the order: they are the packed loop, whose elements are those of the scalar loop bit
/// for bit (a zero can differ in sign). norm_upper computes the same state in every order. conv
/// has the sequential order only.
///
/// When something is not finite (milestone2.md, "When something is not finite"): a function that
/// returns a number returns a Reduction, the number and a flag finite, true exactly when the result
/// is finite; when false, the number is the canonical NaN (every limb a NaN). An infinite or NaN
/// element, or an overflow anywhere on the way, gives finite = false; which infinity IEEE 754 would
/// have given is not computed. A map returns a bool, true exactly when every element written is
/// finite; when false, every element written that is not finite is the canonical NaN, and the
/// others are as computed. finite = true means that every result is finite and within its bound.
///
/// Arrays that alias: a map may write an array it reads, the same arrays (z.limb(j) ==
/// x.limb(j) for every limb j, or the same with y), in place, since every element is read whole
/// before it is written and nothing else reads it; otherwise the array written overlaps no array
/// read, and its limbs overlap each other nowhere. A partial overlap is not supported. The array a
/// convolution writes overlaps neither array it reads. The arrays read may be the same.
///
/// The checks of a debug build (KAIRN_CHECKS 1, config.hpp): a function that rounds checks the
/// floating-point environment first, the rounding mode included; then the lengths (dot, the maps,
/// conv), the arrays that alias, every element of two limbs (canonical) and the scalars (canonical;
/// a positive power of two for mul_pow2), and stops the program with a message on the first that
/// fails. norm_upper does not round: its environment check leaves the rounding mode out, and it
/// checks its elements only when the rounding mode is to nearest (the test of a canonical pair
/// rounds). In a build without the checks these are requirements: lengths that differ read or
/// write outside the arrays, and elements that are not canonical have no guarantee.
///
/// Not here: constant evaluation (the loops are not constexpr), allocation (the program gives every
/// array, the one written included, and nothing throws), a product of arrays of two limbs by a
/// two-limb scalar without an addition (no loop: axpy with y zero computes it, with the bound of
/// axpy), and the sums of a container of stored arrays. The error bounds as functions of the
/// length are kairn::traits<X>::sum(n) and dot(n) (traits.hpp); the reference page of this header,
/// docs/reference/batch.md, states what a program may write with them.
#pragma once

#include "order.hpp"
#include "reduction.hpp"
#include "soa.hpp"
#include "traits.hpp"

#include <bit>
#include <cstddef>
#include <cstdint>
#include <type_traits>

// Whether this translation unit has a packed loop for the lane order (gen/avx2.hpp or gen/neon.hpp):
// otherwise, in the scalar form, the lane order has one lane and is the sequential loop.
#define KAIRN_DETAIL_BATCH_PACKED (KAIRN_PACKED_FORM != KAIRN_PACKED_FORM_SCALAR)

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

// kairn::sequential, which asks sum, sum_fast and dot for the sequential order (element after
// element, from zero, the same bits on every platform and in every form of Packed), is defined in
// order.hpp, with the operations of BallVector's.

namespace detail {

// The loop each function calls is proved (gen/bounds.hpp, kairn::gen::bounds::loops: the loop's
// own statements, its minimum precision, and every kernel it runs, its step, combination, check
// and finish, and the loop of the coefficients of a convolution).
namespace loops = gen::bounds::loops;
template <class T, int K>
concept sum_loop_proved = (K == 1 && loops::sum_1_entry<T>::proved) || (K == 2 && loops::sum_2_entry<T>::proved);
template <class T, int K>
concept sum_fast_loop_proved = (K == 1 && sum_loop_proved<T, 1>) || (K == 2 && loops::sum_fast_2_entry<T>::proved);
template <class T, int K>
concept dot_loop_proved = (K == 1 && loops::dot_1_entry<T>::proved) || (K == 2 && loops::dot_2<T>::proved);
template <class T, int K>
concept add_loop_proved = (K == 1 && loops::add_1_entry<T>::proved) || (K == 2 && loops::add_2_entry<T>::proved);
template <class T, int K>
concept sub_loop_proved = (K == 1 && loops::sub_1_entry<T>::proved) || (K == 2 && loops::sub_2_entry<T>::proved);
template <class T, int K>
concept scale_loop_proved = (K == 1 && loops::scale_1<T>::proved) || (K == 2 && loops::scale_2<T>::proved);
template <class T, int K>
concept mul_pow2_loop_proved =
    (K == 1 && loops::mul_pow2_map_1<T>::proved) || (K == 2 && loops::mul_pow2_map_2<T>::proved);
// axpy with a scalar of T: axpy_1_entry for one limb, axpy_2_1_entry for two.
template <class T, int K>
concept axpy_limb_loop_proved =
    (K == 1 && loops::axpy_1_entry<T>::proved) || (K == 2 && loops::axpy_2_1_entry<T>::proved);
template <class T>
concept axpy_loop_proved = loops::axpy_2_entry<T>::proved;
template <class T, int K>
concept conv_loop_proved = (K == 1 && loops::conv_1<T>::proved) || (K == 2 && loops::conv_2<T>::proved);
template <class T, int K>
concept norm_loop_proved = (K == 1 && loops::norm_upper_1<T>::proved) || (K == 2 && loops::norm_upper_2<T>::proved);

// Views whose limbs are of the same type: T and U are the element types of two views (const or
// not), the same limb type.
template <class T, class U>
concept same_limbs = std::is_same_v<std::remove_const_t<T>, std::remove_const_t<U>>;
// A view through which a function writes: of T, not of const T.
template <class T>
concept writable = !std::is_const_v<T>;

// --- The checks of KAIRN_CHECKS ------------------------------------------------------------------

// Whether the n limbs from a and the m from b share an address. Integer comparisons of addresses:
// the arrays need not be parts of one object.
template <class T, class U>
inline bool overlap(const T* a, std::size_t n, const U* b, std::size_t m) noexcept {
    if (n == 0 || m == 0) return false;
    const std::uintptr_t p = reinterpret_cast<std::uintptr_t>(a), q = reinterpret_cast<std::uintptr_t>(b);
    return p < q + m * sizeof(U) && q < p + n * sizeof(T);
}
// Whether every element of x is canonical: any value of one limb; for two limbs, finite and
// normalized, (+-inf, 0) or (NaN, NaN), as detail::canonical of expansion.hpp.
template <class T, int K>
inline bool canonical_array(const SoAView<T, K>& x) noexcept {
    if constexpr (K == 2) {
        using V = std::remove_const_t<T>;
        for (std::size_t i = 0; i < x.size(); ++i) {
            Expansion<V, 2> e;
            e.limb[0] = x.limb(0)[i];
            e.limb[1] = x.limb(1)[i];
            if (!canonical(e)) return false;
        }
    }
    return true;
}
// Whether the array written, z, is exactly the array read x (every limb the same pointer), or
// overlaps none of x's limbs; and whether z's own limbs overlap each other nowhere.
template <class T, class U, int K>
inline bool alias_ok(const SoAView<T, K>& z, const SoAView<U, K>& x) noexcept {
    bool same = true;
    for (int j = 0; j < K; ++j) same = same && static_cast<const void*>(z.limb(j)) == static_cast<const void*>(x.limb(j));
    if (same && z.size() == x.size()) return true;
    for (int j = 0; j < K; ++j)
        for (int i = 0; i < K; ++i)
            if (overlap(z.limb(j), z.size(), x.limb(i), x.size())) return false;
    return true;
}
template <class T, int K>
inline bool limbs_apart(const SoAView<T, K>& z) noexcept {
    return K == 1 || !overlap(z.limb(0), z.size(), z.limb(K - 1), z.size());
}
// Whether c is a positive power of two of T, normal or subnormal, from its bit pattern.
template <limb T>
inline bool positive_power_of_two(T c) noexcept {
    if (!(c > T(0)) || !finite(c)) return false;
    if constexpr (sizeof(T) == 8) {
        const std::uint64_t b = std::bit_cast<std::uint64_t>(c), m = b & 0x000fffffffffffffu;
        return (b >> 52) != 0 ? m == 0 : (m & (m - 1)) == 0;
    } else {
        const std::uint32_t b = std::bit_cast<std::uint32_t>(c), m = b & 0x007fffffu;
        return (b >> 23) != 0 ? m == 0 : (m & (m - 1)) == 0;
    }
}

// The checks before a function that rounds: the environment (the rounding mode included), then
// what the function requires. The lengths and the arrays that alias are integer comparisons,
// checked even when KAIRN_ENVIRONMENT_FAILURE returned; the elements are checked only when the
// environment is the default one, since the test of a canonical pair rounds.
inline void check_rounds_start([[maybe_unused]] bool& elements) noexcept {
#if KAIRN_CHECKS
    elements = check_environment();
#endif
}
inline void check_that([[maybe_unused]] bool ok, [[maybe_unused]] const char* what,
                       [[maybe_unused]] const char* reason) noexcept {
#if KAIRN_CHECKS
    if (!ok) fail(what, reason);
#endif
}

template <class T, int K>
inline void check_reduction([[maybe_unused]] const char* what, [[maybe_unused]] const SoAView<T, K>& x) noexcept {
#if KAIRN_CHECKS
    bool elements = true;
    check_rounds_start(elements);
    if (elements) check_that(canonical_array(x), what, "an element of x is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
#endif
}
template <class T, class U, int K>
inline void check_dot([[maybe_unused]] const char* what, [[maybe_unused]] const SoAView<T, K>& x,
                      [[maybe_unused]] const SoAView<U, K>& y) noexcept {
#if KAIRN_CHECKS
    bool elements = true;
    check_rounds_start(elements);
    check_that(x.size() == y.size(), what, "x and y have different lengths");
    if (elements) {
        check_that(canonical_array(x), what, "an element of x is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
        check_that(canonical_array(y), what, "an element of y is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
    }
#endif
}
// A map z = f(x) or z = f(x, y): the lengths, the arrays that alias, the elements read. elements:
// whether the caller may check its scalars too (the environment is the default one).
template <class T, class U, int K>
inline bool check_map([[maybe_unused]] const char* what, [[maybe_unused]] const SoAView<T, K>& x,
                      [[maybe_unused]] const SoAView<U, K>& z) noexcept {
    bool elements = true;
#if KAIRN_CHECKS
    check_rounds_start(elements);
    check_that(x.size() == z.size(), what, "x and z have different lengths");
    check_that(limbs_apart(z), what, "the limb arrays of z overlap each other");
    check_that(alias_ok(z, x), what,
               "z overlaps x without being x (an array written is exactly an array read, in place, or apart from it)");
    if (elements) check_that(canonical_array(x), what, "an element of x is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
#endif
    return elements;
}
template <class T, class U, class V, int K>
inline bool check_map([[maybe_unused]] const char* what, [[maybe_unused]] const SoAView<T, K>& x,
                      [[maybe_unused]] const SoAView<U, K>& y, [[maybe_unused]] const SoAView<V, K>& z) noexcept {
    bool elements = check_map(what, x, z);
#if KAIRN_CHECKS
    check_that(y.size() == z.size(), what, "y and z have different lengths");
    check_that(alias_ok(z, y), what,
               "z overlaps y without being y (an array written is exactly an array read, in place, or apart from it)");
    if (elements) check_that(canonical_array(y), what, "an element of y is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
#endif
    return elements;
}
template <class T, class U, class V, int K>
inline void check_conv([[maybe_unused]] const SoAView<T, K>& x, [[maybe_unused]] const SoAView<U, K>& y,
                       [[maybe_unused]] const SoAView<V, K>& z) noexcept {
#if KAIRN_CHECKS
    bool elements = true;
    check_rounds_start(elements);
    const std::size_t nz = x.size() == 0 || y.size() == 0 ? 0 : x.size() + y.size() - 1;
    check_that(z.size() == nz, "conv", "z does not have the length of the product, x.size() + y.size() - 1 (0 when x or y is empty)");
    check_that(limbs_apart(z), "conv", "the limb arrays of z overlap each other");
    bool apart = true;
    for (int j = 0; j < K; ++j)
        for (int i = 0; i < K; ++i)
            apart = apart && !overlap(z.limb(j), z.size(), x.limb(i), x.size()) &&
                    !overlap(z.limb(j), z.size(), y.limb(i), y.size());
    check_that(apart, "conv", "z overlaps x or y (the coefficients written overlap neither array read)");
    if (elements) {
        check_that(canonical_array(x), "conv", "an element of x is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
        check_that(canonical_array(y), "conv", "an element of y is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
    }
#endif
}
// norm_upper does not round: the environment without the rounding mode, then the elements when the
// rounding mode is to nearest, where their test is exact (config.hpp, "Functions that do not round").
template <class T, int K>
inline void check_norm([[maybe_unused]] const SoAView<T, K>& x) noexcept {
#if KAIRN_CHECKS
    if (check_environment_except_rounding() && rounding_to_nearest())
        check_that(canonical_array(x), "norm_upper", "an element of x is not canonical (two limbs: finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN))");
#endif
}

}  // namespace detail

KAIRN_DETAIL_PACKED_BEGIN

// --- Sums ----------------------------------------------------------------------------------------

/// The sum of the elements of x, in the lane order of this translation unit (the packed loop):
/// loop sum_1_entry for one limb, sum_2_entry for two (each step guards the limbs it adds, rule R3;
/// the combination is add_1_1 or add_2_2, the finish fold_finish_1 or fold_finish_2). Rounds; not
/// constexpr. Returns Reduction<Expansion<T, K>>.
///
/// Statement, proved for every length n, in both orders and for every number of lanes: when
/// finite, value is finite (normalized, for two limbs) and
///   |value - sum_i x_i| <= ((1 + e)^(n-1) - 1) sum_i |x_i|  <=  gamma_(n-1)(e) sum_i |x_i|,
/// with e = u / (1 + u) for one limb and e = 3u^2 / (1 - 4u) for two (the bounds of add_1_1 and
/// add_2_2), u the unit roundoff of T; the second inequality when (n - 1) e < 1. There is no
/// underflow term. traits<Expansion<T, K>>::sum(n) is a number of T at least gamma_(n-1)(e).
/// n = 0 gives +0 and finite. An element that is infinite or a NaN, or an overflow, gives
/// finite = false and the canonical NaN.
///
/// Requires, for two limbs, canonical elements (checked with KAIRN_CHECKS). Any value of one limb.
template <class T, int K>
    requires detail::sum_loop_proved<std::remove_const_t<T>, K>
Reduction<Expansion<std::remove_const_t<T>, K>> sum(SoAView<T, K> x) noexcept {
    detail::check_reduction("sum", x);
    Reduction<Expansion<std::remove_const_t<T>, K>> r;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::sum_1_entry_packed(x.limb(0), x.size(), r.value.limb[0], r.finite);
#else
        gen::sum_1_entry_seq(x.limb(0), x.size(), r.value.limb[0], r.finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::sum_2_entry_packed(x.limb(0), x.limb(1), x.size(), r.value.limb[0], r.value.limb[1], r.finite);
#else
        gen::sum_2_entry_seq(x.limb(0), x.limb(1), x.size(), r.value.limb[0], r.value.limb[1], r.finite);
#endif
    }
    return r;
}
/// The sum of the elements of x in the sequential order: the same loops, sum_1_entry and
/// sum_2_entry, element after element; the same statement, and the same bits on every platform.
template <class T, int K>
    requires detail::sum_loop_proved<std::remove_const_t<T>, K>
Reduction<Expansion<std::remove_const_t<T>, K>> sum(SoAView<T, K> x, Sequential) noexcept {
    detail::check_reduction("sum", x);
    Reduction<Expansion<std::remove_const_t<T>, K>> r;
    if constexpr (K == 1) {
        gen::sum_1_entry_seq(x.limb(0), x.size(), r.value.limb[0], r.finite);
    } else {
        gen::sum_2_entry_seq(x.limb(0), x.limb(1), x.size(), r.value.limb[0], r.value.limb[1], r.finite);
    }
    return r;
}

/// The sum of the elements of x with the fast addition of two limbs, in the lane order of this
/// translation unit: loop sum_fast_2_entry (the step sum_fast_entry_step_2, the guarded
/// add_fast_2_2, combined by add_fast_2_2). For one limb it is sum(x), loop sum_1_entry, as
/// add_fast of one limb is the addition. Rounds; not constexpr. Returns Reduction<Expansion<T, K>>.
///
/// Statement, proved as that of sum, with e = 3u^2 for two limbs: the fast addition's bound is
/// relative to its operands, which the theorem of the sum needs and no more. 3u^2 is below the e
/// of sum, so traits<Expansion<T, 2>>::sum(n) bounds this sum too.
template <class T, int K>
    requires detail::sum_fast_loop_proved<std::remove_const_t<T>, K>
Reduction<Expansion<std::remove_const_t<T>, K>> sum_fast(SoAView<T, K> x) noexcept {
    if constexpr (K == 1) {
        return kairn::sum(x);
    } else {
        detail::check_reduction("sum_fast", x);
        Reduction<Expansion<std::remove_const_t<T>, K>> r;
#if KAIRN_DETAIL_BATCH_PACKED
        gen::sum_fast_2_entry_packed(x.limb(0), x.limb(1), x.size(), r.value.limb[0], r.value.limb[1], r.finite);
#else
        gen::sum_fast_2_entry_seq(x.limb(0), x.limb(1), x.size(), r.value.limb[0], r.value.limb[1], r.finite);
#endif
        return r;
    }
}
/// sum_fast in the sequential order (loops sum_fast_2_entry and sum_1_entry): the same statement,
/// and the same bits on every platform.
template <class T, int K>
    requires detail::sum_fast_loop_proved<std::remove_const_t<T>, K>
Reduction<Expansion<std::remove_const_t<T>, K>> sum_fast(SoAView<T, K> x, Sequential) noexcept {
    if constexpr (K == 1) {
        return kairn::sum(x, sequential);
    } else {
        detail::check_reduction("sum_fast", x);
        Reduction<Expansion<std::remove_const_t<T>, K>> r;
        gen::sum_fast_2_entry_seq(x.limb(0), x.limb(1), x.size(), r.value.limb[0], r.value.limb[1], r.finite);
        return r;
    }
}

// --- Dot products --------------------------------------------------------------------------------

/// The dot product sum_i x_i y_i of two arrays of the same length, in the lane order of this
/// translation unit: loop dot_1_entry for one limb (the step dot_entry_step_1, one fused operation
/// s = fma(x, y, s) on the elements guarded, so that no product is rounded on its own and no
/// product of the program is fused into it through a factor 1, rule R3), dot_2 for two (the step
/// dot_step_2: mul_2_2, then add_2_2, which only multiplies the elements). Rounds; not constexpr.
/// Returns Reduction<Expansion<T, K>>.
///
/// Statement, proved for every length n, in both orders and for every number of lanes: when
/// finite, value is finite (normalized, for two limbs) and
///   one limb:  |value - sum x_i y_i| <= ((1 + e)^n - 1) sum |x_i y_i| + (1 + e)^(n-1) n eta/2,
///              e = u / (1 + u);
///   two limbs: |value - sum x_i y_i| <= ((1 + 4u^2)(1 + e)^(n-1) - 1) sum |x_i y_i|
///                                       + (1 + e)^(n-1) n (3/2) eta,  e = 3u^2 / (1 - 4u),
/// eta the smallest positive subnormal number of T. traits<Expansion<T, K>>::dot(n) gives a g and a
/// t of T with |value - sum x_i y_i| <= g sum |x_i y_i| + t. n = 0 gives +0 and finite; an element
/// that is not finite, or an overflow, finite = false and the canonical NaN.
///
/// Requires x.size() == y.size() and, for two limbs, canonical elements (both checked with
/// KAIRN_CHECKS).
template <class T, class U, int K>
    requires detail::same_limbs<T, U> && detail::dot_loop_proved<std::remove_const_t<T>, K>
Reduction<Expansion<std::remove_const_t<T>, K>> dot(SoAView<T, K> x, SoAView<U, K> y) noexcept {
    detail::check_dot("dot", x, y);
    Reduction<Expansion<std::remove_const_t<T>, K>> r;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::dot_1_entry_packed(x.limb(0), y.limb(0), x.size(), r.value.limb[0], r.finite);
#else
        gen::dot_1_entry_seq(x.limb(0), y.limb(0), x.size(), r.value.limb[0], r.finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::dot_2_packed(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), r.value.limb[0], r.value.limb[1],
                          r.finite);
#else
        gen::dot_2_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), r.value.limb[0], r.value.limb[1],
                       r.finite);
#endif
    }
    return r;
}
/// The dot product in the sequential order: the same loops, dot_1_entry and dot_2, element after
/// element; the same statement, and the same bits on every platform.
template <class T, class U, int K>
    requires detail::same_limbs<T, U> && detail::dot_loop_proved<std::remove_const_t<T>, K>
Reduction<Expansion<std::remove_const_t<T>, K>> dot(SoAView<T, K> x, SoAView<U, K> y, Sequential) noexcept {
    detail::check_dot("dot", x, y);
    Reduction<Expansion<std::remove_const_t<T>, K>> r;
    if constexpr (K == 1) {
        gen::dot_1_entry_seq(x.limb(0), y.limb(0), x.size(), r.value.limb[0], r.finite);
    } else {
        gen::dot_2_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), r.value.limb[0], r.value.limb[1],
                       r.finite);
    }
    return r;
}

// --- Maps ----------------------------------------------------------------------------------------

/// z = x + y, element by element: loop add_1_entry for one limb, add_2_entry for two (the steps
/// add_entry_step_1 and add_entry_step_2, add_1_1 and add_2_2 on the elements guarded, rule R3).
/// Rounds; not constexpr. In place: z may be x or y.
///
/// Statement, proved, for every element when it is finite: one limb, z_i = x_i + y_i rounded to
/// nearest (IEEE 754's sum); two limbs, z_i normalized and |z_i - (x_i + y_i)| <= 3u^2/(1 - 4u)
/// |x_i + y_i| (the bound of add_2_2, traits<Expansion<T, 2>>::add). Returns true exactly when
/// every z_i is finite; when false, every z_i that is not finite (an infinite or NaN element, an
/// overflow) is the canonical NaN.
///
/// Requires x, y and z of the same length, z exactly x, exactly y, or apart from both, and for two
/// limbs canonical elements (checked with KAIRN_CHECKS).
template <class T, class U, class V, int K>
    requires detail::same_limbs<T, U> && detail::same_limbs<T, V> && detail::writable<V> &&
             detail::add_loop_proved<V, K>
bool add(SoAView<T, K> x, SoAView<U, K> y, SoAView<V, K> z) noexcept {
    detail::check_map("add", x, y, z);
    bool finite = true;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::add_1_entry_packed(x.limb(0), y.limb(0), x.size(), z.limb(0), finite);
#else
        gen::add_1_entry_seq(x.limb(0), y.limb(0), x.size(), z.limb(0), finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::add_2_entry_packed(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), z.limb(0), z.limb(1), finite);
#else
        gen::add_2_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), z.limb(0), z.limb(1), finite);
#endif
    }
    return finite;
}

/// z = x - y, element by element: loop sub_1_entry for one limb, sub_2_entry for two (the steps
/// sub_entry_step_1 and sub_entry_step_2, sub_1_1 and sub_2_2 on the elements guarded). Rounds; not
/// constexpr. In place: z may be x or y.
///
/// Statement, proved, for every element when it is finite: one limb, z_i = x_i - y_i rounded to
/// nearest; two limbs, z_i normalized and |z_i - (x_i - y_i)| <= 3u^2/(1 - 4u) |x_i - y_i| (the
/// bound of sub_2_2). The flag and the requirements are those of add.
template <class T, class U, class V, int K>
    requires detail::same_limbs<T, U> && detail::same_limbs<T, V> && detail::writable<V> &&
             detail::sub_loop_proved<V, K>
bool sub(SoAView<T, K> x, SoAView<U, K> y, SoAView<V, K> z) noexcept {
    detail::check_map("sub", x, y, z);
    bool finite = true;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::sub_1_entry_packed(x.limb(0), y.limb(0), x.size(), z.limb(0), finite);
#else
        gen::sub_1_entry_seq(x.limb(0), y.limb(0), x.size(), z.limb(0), finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::sub_2_entry_packed(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), z.limb(0), z.limb(1), finite);
#else
        gen::sub_2_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), z.limb(0), z.limb(1), finite);
#endif
    }
    return finite;
}

/// z = x a, element by element, a of T: loop scale_1 for one limb, scale_2 for two (the steps
/// scale_step_1, the product of T, and scale_step_2, mul_2_1). The elements and a are only
/// multiplied, and need no guard. Rounds; not constexpr. In place: z may be x.
///
/// Statement, proved, for every element when it is finite: one limb, z_i = x_i a rounded to nearest,
/// so |z_i - x_i a| <= u/(1 + u) |x_i a| + eta/2; two limbs, z_i normalized and
/// |z_i - x_i a| <= 2u^2 |x_i a| + eta (the bound of mul_2_1, traits<Expansion<T, 2>>::mul_limb).
/// The flag is that of add: an infinite or NaN a, an element that is not finite, or an overflow
/// makes the elements concerned the canonical NaN (a zero times an infinity, too).
///
/// Requires x and z of the same length, z exactly x or apart from it, and for two limbs canonical
/// elements (checked with KAIRN_CHECKS). Any value of a. No loop scales by a two-limb number.
template <class T, class V, int K>
    requires detail::same_limbs<T, V> && detail::writable<V> && detail::scale_loop_proved<V, K>
bool scale(SoAView<T, K> x, std::type_identity_t<V> a, SoAView<V, K> z) noexcept {
    detail::check_map("scale", x, z);
    bool finite = true;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::scale_1_packed(x.limb(0), x.size(), a, z.limb(0), finite);
#else
        gen::scale_1_seq(x.limb(0), x.size(), a, z.limb(0), finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::scale_2_packed(x.limb(0), x.limb(1), x.size(), a, z.limb(0), z.limb(1), finite);
#else
        gen::scale_2_seq(x.limb(0), x.limb(1), x.size(), a, z.limb(0), z.limb(1), finite);
#endif
    }
    return finite;
}

/// z = x c, element by element, c a positive power of two of T: loop mul_pow2_map_1 for one limb,
/// mul_pow2_map_2 for two (the steps mul_pow2_step_1, one product, and mul_pow2_step_2, mul_pow2_2).
/// Only multiplied: no guard. Rounds; not constexpr. In place: z may be x.
///
/// Statement, proved, for every element when it is finite: one limb, z_i = x_i c rounded to
/// nearest, exact unless it is below the smallest normal number, and |z_i - x_i c| <= eta/2; two
/// limbs, z_i normalized and |z_i - x_i c| <= eta (the bound of mul_pow2_2,
/// traits<Expansion<T, 2>>::ldexp). The flag is that of add: an element that is not finite, or an
/// overflow, gives the canonical NaN.
///
/// Requires c a positive power of two of T (normal or subnormal), x and z of the same length, z
/// exactly x or apart from it, and for two limbs canonical elements (all checked with
/// KAIRN_CHECKS). For any power of two 2^n, ldexp of each element (expansion.hpp) is the form
/// without that requirement.
template <class T, class V, int K>
    requires detail::same_limbs<T, V> && detail::writable<V> && detail::mul_pow2_loop_proved<V, K>
bool mul_pow2(SoAView<T, K> x, std::type_identity_t<V> c, SoAView<V, K> z) noexcept {
    if (detail::check_map("mul_pow2", x, z))
        detail::check_that(detail::positive_power_of_two(c), "mul_pow2", "c is not a positive power of two of T");
    bool finite = true;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::mul_pow2_map_1_packed(x.limb(0), x.size(), c, z.limb(0), finite);
#else
        gen::mul_pow2_map_1_seq(x.limb(0), x.size(), c, z.limb(0), finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::mul_pow2_map_2_packed(x.limb(0), x.limb(1), x.size(), c, z.limb(0), z.limb(1), finite);
#else
        gen::mul_pow2_map_2_seq(x.limb(0), x.limb(1), x.size(), c, z.limb(0), z.limb(1), finite);
#endif
    }
    return finite;
}

/// z = a x + y, element by element, a of T: loop axpy_1_entry for one limb (the step
/// axpy_entry_step_1: the product of T, then the sum), axpy_2_1_entry for two (the step
/// axpy_entry_step_2_1: mul_2_1, then add_2_2). a and x are only multiplied; y is guarded before it
/// is added (rule R3). Rounds; not constexpr. In place: z may be x or y (`axpy(a, x, y, y)` is
/// y = a x + y).
///
/// Statement, proved, for every element when it is finite, an error relative to the two terms:
///   |z_i - (a x_i + y_i)| <= c u^k (|a x_i| + |y_i|) + t eta,
/// one limb c = (2 + 3u)/(1 + u)^2, t = 2/3; two limbs c = 3(1 + 2u^2)/(1 - 4u) + 2, t = 5/4, and z_i
/// normalized: the constants of traits<Expansion<T, K>>::axpy_limb. The flag is that of add.
///
/// Requires x, y and z of the same length, z exactly x, exactly y, or apart from both, and for two
/// limbs canonical elements (checked with KAIRN_CHECKS). Any value of a.
template <class T, class U, class V, int K>
    requires detail::same_limbs<T, U> && detail::same_limbs<T, V> && detail::writable<V> &&
             detail::axpy_limb_loop_proved<V, K>
bool axpy(std::type_identity_t<V> a, SoAView<T, K> x, SoAView<U, K> y, SoAView<V, K> z) noexcept {
    detail::check_map("axpy", x, y, z);
    bool finite = true;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::axpy_1_entry_packed(x.limb(0), y.limb(0), x.size(), a, z.limb(0), finite);
#else
        gen::axpy_1_entry_seq(x.limb(0), y.limb(0), x.size(), a, z.limb(0), finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::axpy_2_1_entry_packed(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), a, z.limb(0), z.limb(1),
                                   finite);
#else
        gen::axpy_2_1_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), a, z.limb(0), z.limb(1),
                                finite);
#endif
    }
    return finite;
}
/// z = a x + y, element by element, a of two limbs: loop axpy_2_entry (the step axpy_entry_step_2:
/// mul_2_2, then add_2_2 on y guarded). Rounds; not constexpr. In place: z may be x or y.
///
/// Statement, proved, for every element when it is finite: z_i normalized and
///   |z_i - (a x_i + y_i)| <= c u^2 (|a x_i| + |y_i|) + 2 eta,  c = 3(1 + 4u^2)/(1 - 4u) + 4,
/// the constants of traits<Expansion<T, 2>>::axpy. The flag is that of add.
///
/// Requires a canonical, x, y and z of the same length, z exactly x, exactly y, or apart from both,
/// and canonical elements (checked with KAIRN_CHECKS).
template <class T, class U, class V>
    requires detail::same_limbs<T, U> && detail::same_limbs<T, V> && detail::writable<V> &&
             detail::axpy_loop_proved<V>
bool axpy(const Expansion<V, 2>& a, SoAView<T, 2> x, SoAView<U, 2> y, SoAView<V, 2> z) noexcept {
    if (detail::check_map("axpy", x, y, z))
        detail::check_that(detail::canonical(a), "axpy",
                           "a is not canonical (finite with a0 + a1 == a0, (+-inf, 0) or (NaN, NaN))");
    bool finite = true;
#if KAIRN_DETAIL_BATCH_PACKED
    gen::axpy_2_entry_packed(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), a.limb[0], a.limb[1], z.limb(0),
                             z.limb(1), finite);
#else
    gen::axpy_2_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), a.limb[0], a.limb[1], z.limb(0),
                          z.limb(1), finite);
#endif
    return finite;
}

// --- The convolution -----------------------------------------------------------------------------

/// The coefficients of the product of the polynomials x (x.size() coefficients, the constant one
/// first) and y: z_j = sum_i x_i y_(j-i), for j from 0 to x.size() + y.size() - 2, none when x or y
/// is empty. Loop conv_1 for one limb, conv_2 for two: coefficient j is the dot product dot_1 or
/// dot_2, in its sequential order, of its terms (x_i, y_(j-i)) in increasing i. Only multiplied: no
/// guard. Sequential only (no packed loop). Rounds; not constexpr.
///
/// Statement, proved: every coefficient that is finite satisfies the statement of dot (above) for
/// its own m_j terms, m_j <= min(x.size(), y.size()), so traits<Expansion<T, K>>::dot(min(x.size(),
/// y.size())) bounds every coefficient: |z_j - sum_i x_i y_(j-i)| <= g sum_i |x_i y_(j-i)| + t.
/// Returns true exactly when every z_j is finite; when false, every z_j that is not finite is the
/// canonical NaN.
///
/// Requires z.size() == x.size() + y.size() - 1 (0 when either is empty), z apart from x and y, and
/// for two limbs canonical coefficients (checked with KAIRN_CHECKS). Not in place.
template <class T, class U, class V, int K>
    requires detail::same_limbs<T, U> && detail::same_limbs<T, V> && detail::writable<V> &&
             detail::conv_loop_proved<V, K>
bool conv(SoAView<T, K> x, SoAView<U, K> y, SoAView<V, K> z) noexcept {
    detail::check_conv(x, y, z);
    bool finite = true;
    if constexpr (K == 1) {
        gen::conv_1_seq(x.limb(0), x.size(), y.limb(0), y.size(), z.limb(0), finite);
    } else {
        gen::conv_2_seq(x.limb(0), x.limb(1), x.size(), y.limb(0), y.limb(1), y.size(), z.limb(0), z.limb(1), finite);
    }
    return finite;
}

// --- An upper bound of the largest magnitude ----------------------------------------------------

/// An upper bound of the largest magnitude of the elements of x, as a T: loop norm_upper_1 for one
/// limb, norm_upper_2 for two (a fold of maxima: the step norm_step_1 or norm_step_2 on the leading
/// limb, the combination norm_combine, the finish norm_finish_1 or norm_finish_2). Every order
/// computes the same result. Does not round (magnitudes, comparisons, a step of the bit pattern):
/// not preceded by the debug build's check of the rounding mode (config.hpp). Not constexpr.
/// Returns Reduction<T>.
///
/// Statement, proved, with V = max_i |x_i| (0 for no element), |x_i| the exact magnitude of the
/// element: when finite, one limb, value = V; two limbs, V <= value <= succ(RU(V)), at most one step
/// of T above the smallest number of T not below V (a normalized pair is strictly between the
/// neighbors of its leading limb). So n = 0 gives 0 for one limb and the smallest positive number of
/// T for two. finite is false, and value a NaN, exactly when an element is not finite or the step
/// up is not (two limbs, V near the largest finite number).
///
/// Requires, for two limbs, canonical elements (checked with KAIRN_CHECKS when the rounding mode is
/// to nearest).
template <class T, int K>
    requires detail::norm_loop_proved<std::remove_const_t<T>, K>
Reduction<std::remove_const_t<T>> norm_upper(SoAView<T, K> x) noexcept {
    detail::check_norm(x);
    Reduction<std::remove_const_t<T>> r;
    if constexpr (K == 1) {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::norm_upper_1_packed(x.limb(0), x.size(), r.value, r.finite);
#else
        gen::norm_upper_1_seq(x.limb(0), x.size(), r.value, r.finite);
#endif
    } else {
#if KAIRN_DETAIL_BATCH_PACKED
        gen::norm_upper_2_packed(x.limb(0), x.limb(1), x.size(), r.value, r.finite);
#else
        gen::norm_upper_2_seq(x.limb(0), x.limb(1), x.size(), r.value, r.finite);
#endif
    }
    return r;
}

KAIRN_DETAIL_PACKED_END
}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
