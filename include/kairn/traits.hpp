/// @file
/// kairn::traits<X>: the questions that float, double and every Expansion<T, K> answer the same
/// way, so that code templated on its scalar reads the same for all of them
/// (docs/developer/design/phase0/library.md, "API sketch"); and the error model as data
/// (docs/developer/design/phase0/operations.md, "Exported constants").
///
/// The constants come from include/kairn/gen/bounds.hpp, which the generator writes from
/// gen/claims.json. An operation whose kernel is not proved there has no constants here at all:
/// its entry is an UnverifiedBound, and reading entry.unit does not compile. No number in this file
/// is written by hand.
#pragma once

#include "config.hpp"
#include "gen/bounds.hpp"
#include "gen/scalar.hpp"

#include <cstddef>
#include <cstdint>
#include <limits>
#include <type_traits>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

template <class T, int K>
struct Expansion;

/// What an error bound is relative to.
enum class BoundForm {
    result,    ///< |computed - exact| <= unit |exact| + tiny.
    operands,  ///< |computed - exact| <= unit (|x| + |y|) + tiny, x and y the operands.
    /// |computed - exact| <= unit (the sum of the magnitudes of the terms of the exact value) + tiny:
    /// |a x| + |y| for a x + y, sum_i |x_i| for a sum, sum_i |x_i y_i| for a dot product.
    terms,
};

/// An entry of the error model, for an operation whose proof is checked.
///
/// For finite normalized operands whose computation does not overflow (see each operation for
/// what is proved near overflow): |computed - exact| <= unit * |exact| + tiny when reference is
/// BoundForm::result, <= unit * (|x| + |y|) + tiny when it is BoundForm::operands, and
/// <= unit * (the sum of the magnitudes of the terms) + tiny when it is BoundForm::terms. Each
/// constant of an operation is the smallest number of T not below the exact constant of the proved
/// statement: unit >= c u^k, tiny >= t eta. For BoundForm::result also
/// |computed - exact| <= unit_computed * |computed| + tiny_computed, the form of an analysis
/// written relative to the computed value (Higham's (2.5)), with unit_computed >=
/// unit / (1 - unit) and tiny_computed >= tiny / (1 - unit). For the other two forms no bound
/// relative to the computed value follows, and those two are +infinity.
///
/// The bounds of a sum and of a dot product as functions of the length (traits<X>::sum(n),
/// sum_height(h), dot(n)) are of BoundForm::terms and are computed by a generated, proved kernel:
/// numbers of T at least the proved constants, not the smallest such; +infinity, which claims
/// nothing, where no bound is given.
///
/// The constants are exact upper bounds of the proved ones; they are not a measurement, and they
/// say nothing about an operation applied to non-normalized or non-finite operands.
template <class T>
struct Bound {
    T unit;               ///< The relative term, rounded up.
    T tiny;               ///< The absolute (underflow) term, rounded up.
    T unit_computed;      ///< The relative term of the bound relative to the computed value.
    T tiny_computed;      ///< The absolute term of the bound relative to the computed value.
    BoundForm reference;  ///< What unit multiplies.
    /// True: the statement these constants come from has a proof checked by Rocq.
    static constexpr bool verified = true;
};

/// The entry of an operation whose proof is not checked yet (UNVERIFIED). It has no constants:
/// the statement it would have is a target, and a measured maximum is not a bound.
struct UnverifiedBound {
    /// False: no proof of this operation's statement is checked yet.
    static constexpr bool verified = false;
};

namespace detail {

// The entry of the operation computed by the kernel G (one of kairn::gen::bounds).
template <class T, class G>
constexpr auto bound_of() noexcept {
    if constexpr (G::proved && requires { G::unit; }) {
        if constexpr (G::form == gen::bounds::Form::result) {
            return Bound<T>{G::unit, G::tiny, G::unit_computed, G::tiny_computed, BoundForm::result};
        } else {
            constexpr T inf = std::numeric_limits<T>::infinity();
            constexpr BoundForm form = G::form == gen::bounds::Form::terms ? BoundForm::terms : BoundForm::operands;
            return Bound<T>{G::unit, G::tiny, inf, inf, form};
        }
    } else {
        return UnverifiedBound{};
    }
}

// The entry of an operation computed by either of two kernels, depending on the order of its
// operands: verified when both are, with the larger of each constant.
template <class T, class G, class H>
constexpr auto bound_of_either() noexcept {
    constexpr auto a = bound_of<T, G>();
    constexpr auto b = bound_of<T, H>();
    if constexpr (a.verified && b.verified) {
        static_assert(a.reference == b.reference, "the two kernels of one operation have bounds of different forms");
        auto larger = [](T x, T y) { return y > x ? y : x; };  // b > a, never a < b: see detail::canonical
        return Bound<T>{larger(a.unit, b.unit), larger(a.tiny, b.tiny), larger(a.unit_computed, b.unit_computed),
                        larger(a.tiny_computed, b.tiny_computed), a.reference};
    } else {
        return UnverifiedBound{};
    }
}

// --- The bounds as functions of the length --------------------------------------------------------
//
// A count n of the program, a std::size_t, as the count m of T that the kernels bound_sum_k and
// bound_dot_k take (and acc_radius_k, accumulator.hpp): the smallest number of T not below n.
// Integer bookkeeping and one conversion that is exact: n rounded up to p significant bits in
// integers (p the precision of T), which a number of T holds, so that the conversion of the
// integer to T is exact under every rounding mode and in constant evaluation; 2^64, the one value
// of that rounding that a 64-bit integer does not hold, is written as the constant it is. Why up:
// the kernels' statements ask of m only that it be a number of T, 0 or at least 1, and what they
// bound grows with m (gamma_m(e) = m e / (1 - m e), and m tiny (1 + g)), so a bound for m >= n
// is one for n; a conversion to nearest could give m < n. This code is the header's, not
// machine-checked: argued here, and tested at and beyond the counts where the conversion rounds
// (tests/api/constexpr.cpp, tests/api/accumulator_exact.py).
template <limb T>
KAIRN_FORCEINLINE constexpr T count_up(std::uint64_t n) noexcept {
    constexpr int p = std::numeric_limits<T>::digits;
    int bits = 0;
    for (std::uint64_t v = n; v != 0; v >>= 1) ++bits;
    if (bits <= p) return static_cast<T>(n);
    const int shift = bits - p;
    std::uint64_t q = n >> shift;
    if ((q << shift) != n) ++q;
    if (bits == 64 && q == (std::uint64_t{1} << p)) return static_cast<T>(0x1p64);
    return static_cast<T>(q << shift);
}

// The failure of a bound that is not given, in a constant expression: not constexpr, so that the
// expression is invalid and the compiler names this function and its message.
[[noreturn]] inline void no_bound_for_this_length(const char* reason) noexcept { fail("kairn::traits", reason); }

// The bounds as functions of the length (milestone2.md, "The bound as a function of n"), from the
// kernels bound_sum_k and bound_dot_k on the count m: unit = g and, for a dot product, tiny = t;
// where the kernel's mask is false, no bound is given and unit and tiny are +infinity, which
// claims nothing (a compile error in a constant expression). UnverifiedBound when the kernel is
// not proved. Only products and sums of nonnegative numbers, which constant evaluation computes
// with the same values: the same bits at compile time and at run time.
template <class T, int K>
KAIRN_FORCEINLINE constexpr auto bound_sum_of(std::uint64_t m) noexcept {
    using G = std::conditional_t<K == 1, gen::bounds::bound_sum_1<T>, gen::bounds::bound_sum_2<T>>;
    if constexpr (G::proved) {
        T g = T(0);
        bool ok = false;
        if constexpr (K == 1) {
            gen::bound_sum_1(count_up<T>(m), g, ok);
        } else {
            gen::bound_sum_2(count_up<T>(m), g, ok);
        }
        constexpr T inf = std::numeric_limits<T>::infinity();
        if (!ok) {
            if (__builtin_is_constant_evaluated())
                no_bound_for_this_length("no bound of a sum is given for this length: n e exceeds about 1/4");
            return Bound<T>{inf, inf, inf, inf, BoundForm::terms};
        }
        return Bound<T>{g, T(0), inf, inf, BoundForm::terms};
    } else {
        return UnverifiedBound{};
    }
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr auto bound_dot_of(std::uint64_t m) noexcept {
    using G = std::conditional_t<K == 1, gen::bounds::bound_dot_1<T>, gen::bounds::bound_dot_2<T>>;
    if constexpr (G::proved) {
        T g = T(0), t = T(0);
        bool ok = false;
        if constexpr (K == 1) {
            gen::bound_dot_1(count_up<T>(m), g, t, ok);
        } else {
            gen::bound_dot_2(count_up<T>(m), g, t, ok);
        }
        constexpr T inf = std::numeric_limits<T>::infinity();
        if (!ok) {
            if (__builtin_is_constant_evaluated())
                no_bound_for_this_length("no bound of a dot product is given for this length: n e exceeds about 1/4");
            return Bound<T>{inf, inf, inf, inf, BoundForm::terms};
        }
        return Bound<T>{g, t, inf, inf, BoundForm::terms};
    } else {
        return UnverifiedBound{};
    }
}

// One limb, for T and for Expansion<T, 1>: one IEEE 754 operation per entry.
template <class T>
struct traits_one_limb {
    /// The type of a limb.
    using limb_type = T;
    /// The number of limbs.
    static constexpr int limbs = 1;
    /// The number of significant bits: limbs times the precision of T.
    static constexpr int precision = std::numeric_limits<T>::digits;
    /// x + y (kernel add_1_1).
    static constexpr auto add = bound_of<T, gen::bounds::add_1_1<T>>();
    /// x + a, a of the limb type: the same operation (kernel add_1_1).
    static constexpr auto add_limb = add;
    /// The fast addition: the same operation (kernel add_1_1).
    static constexpr auto add_fast = add;
    /// x - y: one rounding, as x + y (kernel add_1_1).
    static constexpr auto sub = add;
    /// x - a and a - x: as x - y (kernel add_1_1).
    static constexpr auto sub_limb = add;
    /// x * y (kernel mul_1_1).
    static constexpr auto mul = bound_of<T, gen::bounds::mul_1_1<T>>();
    /// x * a: the same operation (kernel mul_1_1).
    static constexpr auto mul_limb = mul;
    /// x times a power of two: one rounded product (kernel mul_1_1).
    static constexpr auto ldexp = mul;
    /// a x + y, element by element, of kairn::axpy (batch.hpp): BoundForm::terms,
    /// |z - (a x + y)| <= unit (|a x| + |y|) + tiny (kernel axpy_entry_step_1).
    static constexpr auto axpy = bound_of<T, gen::bounds::axpy_entry_step_1<T>>();

    /// The bound of a sum of n numbers of one limb, in any order of summation: with b = sum(n), if
    /// b.unit is finite, |computed - sum_i x_i| <= b.unit sum_i |x_i| for every sum of n numbers of
    /// T made by n - 1 additions rounded to nearest, in any tree (kairn::sum and sum_fast of
    /// batch.hpp, in both orders). b.unit is at least gamma_(n-1)(e) = (n - 1) e / (1 - (n - 1) e),
    /// e = u / (1 + u), and tiny is 0 (no underflow term). n - 1 is given to the kernel as a number
    /// of T rounded up when it is not one (detail::count_up). Beyond the lengths the kernel bounds,
    /// (n - 1) e above about 1/4 (n above about 2^51 for double, 2^22 for float), unit and tiny are
    /// +infinity, which claims nothing; in a constant expression that is a compile error. constexpr,
    /// with the same bits at compile time and at run time (kernel bound_sum_1).
    static constexpr auto sum(std::size_t n) noexcept { return bound_sum_of<T, 1>(n == 0 ? 0 : n - 1); }
    /// The bound of a sum whose summation tree has height h (at most h additions between an element
    /// and the result), the same kernel with m = h: |computed - sum_i x_i| <= unit sum_i |x_i|, unit at
    /// least gamma_h(e) (kernel bound_sum_1). sum(n) is sum_height(n - 1): every tree of n elements
    /// has height at most n - 1.
    static constexpr auto sum_height(std::size_t h) noexcept { return bound_sum_of<T, 1>(h); }
    /// The bound of a dot product of n terms of one limb, in any order: with b = dot(n), if b.unit is
    /// finite, |computed - sum_i x_i y_i| <= b.unit sum_i |x_i y_i| + b.tiny for kairn::dot of
    /// batch.hpp in both orders (the fused step fma(x, y, s)) and for every coefficient of conv with
    /// n = min(x.size(), y.size()). unit >= gamma_n(e) >= (1 + e)^n - 1 and tiny >= n (eta / 2)(1 +
    /// unit), the two terms of the proved statement of dot_1. +infinity beyond n e about 1/4, as
    /// sum(n). constexpr (kernel bound_dot_1).
    static constexpr auto dot(std::size_t n) noexcept { return bound_dot_of<T, 1>(n); }
};

}  // namespace detail

/// The traits of a number type X: double, float, or Expansion<T, K>.
///
/// Each has `limb_type`, `limbs`, `precision` (limbs times the precision of the limb type), and
/// one entry of the error model per operation: `add`, `add_limb` (a k-number and a limb),
/// `add_fast`, `sub`, `sub_limb`, `mul`, `mul_limb`, `ldexp`, `axpy` (and `axpy_limb` for two
/// limbs: a scalar of T), and the bounds of the functions on arrays of batch.hpp as functions of
/// the length, `sum(n)`, `sum_height(h)` and `dot(n)`. An entry is a Bound<limb_type> when the
/// operation's kernel is proved, and an UnverifiedBound, without constants, otherwise;
/// `entry.verified` says which in both cases. The entries of float and double are those of one
/// IEEE 754 operation, the same as Expansion<T, 1>. For two limbs the kernel is the finite core
/// of the operation: its bound is what an operator's result satisfies whenever it is finite (the
/// operator adds only the fix-up of infinities and NaN), and what kairn::finite:: satisfies.
template <class X>
struct traits;

/// The traits of double: one IEEE 754 operation per entry.
template <>
struct traits<double> : detail::traits_one_limb<double> {};
/// The traits of float: one IEEE 754 operation per entry.
template <>
struct traits<float> : detail::traits_one_limb<float> {};
/// The traits of Expansion<T, 1>: those of T.
template <class T>
struct traits<Expansion<T, 1>> : detail::traits_one_limb<T> {};

/// The traits of Expansion<T, 2>.
template <class T>
struct traits<Expansion<T, 2>> {
    /// The type of a limb.
    using limb_type = T;
    /// The number of limbs.
    static constexpr int limbs = 2;
    /// The number of significant bits: 2 times the precision of T (106 for double), where the
    /// value is large enough for the second limb not to be subnormal.
    static constexpr int precision = 2 * std::numeric_limits<T>::digits;
    /// x + y (kernel add_2_2).
    static constexpr auto add = detail::bound_of<T, gen::bounds::add_2_2<T>>();
    /// x + a and a + x (kernel add_2_1).
    static constexpr auto add_limb = detail::bound_of<T, gen::bounds::add_2_1<T>>();
    /// The fast addition (kernel add_fast_2_2), whose bound is relative to the operands.
    static constexpr auto add_fast = detail::bound_of<T, gen::bounds::add_fast_2_2<T>>();
    /// x - y (kernel sub_2_2).
    static constexpr auto sub = detail::bound_of<T, gen::bounds::sub_2_2<T>>();
    /// x - a and a - x (kernels sub_2_1 and sub_1_2).
    static constexpr auto sub_limb = detail::bound_of_either<T, gen::bounds::sub_2_1<T>, gen::bounds::sub_1_2<T>>();
    /// x * y (kernel mul_2_2).
    static constexpr auto mul = detail::bound_of<T, gen::bounds::mul_2_2<T>>();
    /// x * a and a * x (kernel mul_2_1).
    static constexpr auto mul_limb = detail::bound_of<T, gen::bounds::mul_2_1<T>>();
    /// x times a power of two (kernel mul_pow2_2).
    static constexpr auto ldexp = detail::bound_of<T, gen::bounds::mul_pow2_2<T>>();
    /// a x + y, element by element, of kairn::axpy (batch.hpp) with a of two limbs:
    /// BoundForm::terms, |z - (a x + y)| <= unit (|a x| + |y|) + tiny (kernel axpy_entry_step_2).
    static constexpr auto axpy = detail::bound_of<T, gen::bounds::axpy_entry_step_2<T>>();
    /// a x + y with a of T (kernel axpy_entry_step_2_1).
    static constexpr auto axpy_limb = detail::bound_of<T, gen::bounds::axpy_entry_step_2_1<T>>();

    /// The bound of a sum of n numbers of two limbs, in any order of summation: with b = sum(n), if
    /// b.unit is finite, |computed - sum_i x_i| <= b.unit sum_i |x_i| for every sum of n normalized
    /// numbers made by n - 1 additions add_2_2 (the finite core of x + y), in any tree: kairn::sum
    /// of batch.hpp in both orders, and kairn::sum_fast, whose addition's bound, 3u^2 of its
    /// operands, is below e. b.unit is at least gamma_(n-1)(e), e = 3u^2 / (1 - 4u), and tiny is 0.
    /// n - 1 is given to the kernel as a number of T rounded up when it is not one
    /// (detail::count_up). Beyond the lengths the kernel bounds, (n - 1) e above about 1/4 (more
    /// than 2^101 terms for double, so never for a std::size_t, and about 2^44 for float), unit and
    /// tiny are +infinity, which claims nothing; in a constant expression that is a compile error.
    /// constexpr, with the same bits at compile time and at run time (kernel bound_sum_2).
    static constexpr auto sum(std::size_t n) noexcept { return detail::bound_sum_of<T, 2>(n == 0 ? 0 : n - 1); }
    /// The bound of a sum of two limbs whose summation tree has height h, the same kernel with
    /// m = h: unit at least gamma_h(e) (kernel bound_sum_2).
    static constexpr auto sum_height(std::size_t h) noexcept { return detail::bound_sum_of<T, 2>(h); }
    /// The bound of a dot product of n terms of two limbs, in any order: with b = dot(n), if b.unit
    /// is finite, |computed - sum_i x_i y_i| <= b.unit sum_i |x_i y_i| + b.tiny for kairn::dot of
    /// batch.hpp in both orders (mul_2_2, then add_2_2) and for every coefficient of conv with
    /// n = min(x.size(), y.size()). unit >= gamma_n(4u^2) >= (1 + 4u^2)(1 + e)^(n-1) - 1 and
    /// tiny >= n (3/2) eta (1 + unit), the two terms of the proved statement of dot_2. +infinity
    /// beyond n 4u^2 about 1/4, as sum(n). constexpr (kernel bound_dot_2).
    static constexpr auto dot(std::size_t n) noexcept { return detail::bound_dot_of<T, 2>(n); }
};

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
