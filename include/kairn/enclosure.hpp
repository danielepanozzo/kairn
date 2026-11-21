/// @file
/// The types of the interface that Interval<T, k> and Ball<T, k> share
/// (docs/developer/design/milestone2.md, "One enclosure interface"): kairn::Trit, the answer of the
/// three-valued comparisons and of kairn::member, with kairn::certainly and kairn::possibly, the
/// two ways to make a bool of one; kairn::Split, the two parts of a split; and kairn::MidRad, a
/// midpoint with its radius. Nothing here computes: the operations are those of ball.hpp and
/// interval.hpp, which include this header, as kairn/kairn.hpp does through them.
#pragma once

#include "expansion.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

/// The answer of a three-valued comparison of two sets (kairn::less, kairn::less_equal,
/// kairn::equal and their mirrors) or of a membership (kairn::member). Each answer is about every
/// choice of members of the operands: yes when the relation holds for every choice, no when it
/// fails for every choice, and unknown otherwise. A comparison with an operand that is the empty
/// set is unknown (a query about nothing answers neither; kairn::member answers no there, the
/// empty set having no member), and so is, for the answers that are only certain (balls of two
/// limbs), every case the kernel does not decide. yes and no are never both true of one answer.
///
/// A Trit does not convert to bool: `if (kairn::less(x, y))` and `bool b = kairn::less(x, y)` do
/// not compile. A program says which answer it acts on: kairn::certainly(t), t is yes, or
/// kairn::possibly(t), t is not no; or it compares with the enumerators, or switches on them. A
/// static_cast to bool compiles, as for any scoped enumeration, and gives true for no as for yes:
/// it is never the question a program means.
enum class Trit : signed char {
    no = -1,      ///< The relation fails for every choice of members of the operands.
    unknown = 0,  ///< Neither of the others is known, or a comparison with the empty set.
    yes = 1,      ///< The relation holds for every choice of members of the operands.
};

/// Whether t is Trit::yes: the relation holds for every choice of members of the operands.
/// Does not round. constexpr.
[[nodiscard]] constexpr bool certainly(Trit t) noexcept { return t == Trit::yes; }
/// Whether t is not Trit::no: the relation was not shown to fail for every choice of members
/// (yes or unknown), so it may hold for some. Does not round. constexpr.
[[nodiscard]] constexpr bool possibly(Trit t) noexcept { return t != Trit::no; }

/// What split() returns: two sets that together are the one split (an interval) or cover it (a
/// ball). The functions that return one say what is claimed of the two parts.
template <class X>
struct Split {
    X left;   ///< The part that holds the lower bound (of a ball, the part below its center).
    X right;  ///< The part that holds the upper bound (of a ball, the part above its center).
};

/// A midpoint and a radius, for the k-number type Expansion<T, K>: what mid_rad() of an Interval
/// returns, from one call of its kernel, and of a Ball, its center and its radius. The functions
/// that return one say what is claimed of the two.
template <class T, int K>
struct MidRad {
    Expansion<T, K> midpoint;  ///< The midpoint, a number of K limbs.
    T radius;                  ///< The radius, a number of T.
};

namespace detail {

// The answer of a kernel of kind trit, whose claim says that its two masks are never both true:
// yes, no, or both false, unknown. A selection on two masks; nothing is computed.
KAIRN_FORCEINLINE constexpr Trit trit(bool yes, bool no) noexcept {
    return yes ? Trit::yes : (no ? Trit::no : Trit::unknown);
}
// The answer with yes and no exchanged: the three-valued negation, of not_equal.
KAIRN_FORCEINLINE constexpr Trit opposite(Trit t) noexcept {
    return t == Trit::yes ? Trit::no : (t == Trit::no ? Trit::yes : Trit::unknown);
}

}  // namespace detail
}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
