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

#include <limits>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

template <class T, int K>
struct Expansion;

/// What an error bound is relative to.
enum class BoundForm {
    result,    ///< |computed - exact| <= unit |exact| + tiny.
    operands,  ///< |computed - exact| <= unit (|x| + |y|) + tiny, x and y the operands.
};

/// An entry of the error model, for an operation whose proof is checked.
///
/// For finite normalized operands whose computation does not overflow (see each operation for
/// what is proved near overflow): |computed - exact| <= unit * |exact| + tiny when reference is
/// BoundForm::result, or <= unit * (|x| + |y|) + tiny when it is BoundForm::operands. Each
/// constant is the smallest number of T not below the exact constant of the proved statement:
/// unit >= c u^k, tiny >= t eta. For BoundForm::result also
/// |computed - exact| <= unit_computed * |computed| + tiny_computed, the form of an analysis
/// written relative to the computed value (Higham's (2.5)), with unit_computed >=
/// unit / (1 - unit) and tiny_computed >= tiny / (1 - unit). For BoundForm::operands no bound
/// relative to the computed value follows, and those two are +infinity.
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
            return Bound<T>{G::unit, G::tiny, inf, inf, BoundForm::operands};
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
};

}  // namespace detail

/// The traits of a number type X: double, float, or Expansion<T, K>.
///
/// Each has `limb_type`, `limbs`, `precision` (limbs times the precision of the limb type), and
/// one entry of the error model per operation: `add`, `add_limb` (a k-number and a limb),
/// `add_fast`, `sub`, `sub_limb`, `mul`, `mul_limb`, `ldexp`. An entry is a Bound<limb_type>
/// when the operation's kernel is proved, and an UnverifiedBound, without constants, otherwise;
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
};

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
