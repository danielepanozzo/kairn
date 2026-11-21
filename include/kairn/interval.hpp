/// @file
/// Interval<T, k>: a set of real numbers given by two bounds, each a k-limb number of T, with the
/// empty set and unbounded intervals as ordinary values (docs/developer/design/milestone2.md,
/// "Interval kernels" and "One enclosure interface"; docs/developer/design/phase0/operations.md,
/// "Interval").
///
/// Each operation forwards to one generated kernel: the constructor kernels interval_make_1 and
/// interval_make_2, the negations, sums, differences and products interval_neg_k, interval_add_k,
/// interval_sub_k and interval_mul_k, the hull and the intersection interval_hull_k and
/// interval_intersection_k, the midpoint and radius interval_mid_rad_k, the split interval_split_k,
/// the conversions interval_to_ball_k (in ball.hpp) and ball_to_interval_k, for the bounds of two
/// limbs as numbers of T the roundings to_down_2 and to_up_2, and the predicates, the three-valued
/// comparisons and the relations of IEEE 1788 of the enclosure interface: interval_empty_k,
/// interval_entire_k, interval_contains_k, interval_subset_k, interval_positive_k,
/// interval_negative_k, interval_zero_k, interval_less_k, interval_less_equal_k, interval_equal_k,
/// interval_rel_equal_k, interval_rel_interior_k and interval_rel_disjoint_k. Like every
/// operation, each needs the kairn::unverified marker while gen/claims.json does not mark its
/// kernel proved. Two kinds of function compose kernels, each documented as such: a constructor of
/// two limbs from a T builds the two-limb number first (make_2), as Ball<T, 2>(a) does, and so do
/// contains(t) and kairn::member of two limbs with a point t of T. make_2 gives t exactly, which
/// is the argument for both; it is not machine-checked as one statement.
///
/// The three-valued comparisons kairn::less, kairn::less_equal, kairn::equal and their mirrors
/// return a kairn::Trit (enclosure.hpp); intervals have no comparison operators, so that no answer
/// about sets becomes a bool unseen. The relations of IEEE 1788, which return a bool with the
/// standard's conventions for the empty set, are in the namespace kairn::ieee1788. No operation
/// mixes an interval with a number (X + a): no kernel takes one, and an interval of a point is
/// written Interval(a); a point given to contains(t) is a member test, never made an interval.
#pragma once

#include "ball.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

namespace detail {

// The kernels of the Interval operations, by number of limbs of the bounds.
template <class T, int K>
struct interval_kernels;
template <class T>
struct interval_kernels<T, 1> {
    using make = gen::bounds::interval_make_1<T>;
    using neg = gen::bounds::interval_neg_1<T>;
    using add = gen::bounds::interval_add_1<T>;
    using sub = gen::bounds::interval_sub_1<T>;
    using mul = gen::bounds::interval_mul_1<T>;
    using hull = gen::bounds::interval_hull_1<T>;
    using intersection = gen::bounds::interval_intersection_1<T>;
    using mid_rad = gen::bounds::interval_mid_rad_1<T>;
    using split = gen::bounds::interval_split_1<T>;
    using from_ball = gen::bounds::ball_to_interval_1<T>;
    using empty = gen::bounds::interval_empty_1<T>;
    using entire = gen::bounds::interval_entire_1<T>;
    using contains = gen::bounds::interval_contains_1<T>;
    using subset = gen::bounds::interval_subset_1<T>;
    using positive = gen::bounds::interval_positive_1<T>;
    using negative = gen::bounds::interval_negative_1<T>;
    using zero = gen::bounds::interval_zero_1<T>;
    using less = gen::bounds::interval_less_1<T>;
    using less_equal = gen::bounds::interval_less_equal_1<T>;
    using equal = gen::bounds::interval_equal_1<T>;
    using rel_equal = gen::bounds::interval_rel_equal_1<T>;
    using rel_interior = gen::bounds::interval_rel_interior_1<T>;
    using rel_disjoint = gen::bounds::interval_rel_disjoint_1<T>;
};
template <class T>
struct interval_kernels<T, 2> {
    using make = gen::bounds::interval_make_2<T>;
    using neg = gen::bounds::interval_neg_2<T>;
    using add = gen::bounds::interval_add_2<T>;
    using sub = gen::bounds::interval_sub_2<T>;
    using mul = gen::bounds::interval_mul_2<T>;
    using hull = gen::bounds::interval_hull_2<T>;
    using intersection = gen::bounds::interval_intersection_2<T>;
    using mid_rad = gen::bounds::interval_mid_rad_2<T>;
    using split = gen::bounds::interval_split_2<T>;
    using from_ball = gen::bounds::ball_to_interval_2<T>;
    using empty = gen::bounds::interval_empty_2<T>;
    using entire = gen::bounds::interval_entire_2<T>;
    using contains = gen::bounds::interval_contains_2<T>;
    using subset = gen::bounds::interval_subset_2<T>;
    using positive = gen::bounds::interval_positive_2<T>;
    using negative = gen::bounds::interval_negative_2<T>;
    using zero = gen::bounds::interval_zero_2<T>;
    using less = gen::bounds::interval_less_2<T>;
    using less_equal = gen::bounds::interval_less_equal_2<T>;
    using equal = gen::bounds::interval_equal_2<T>;
    using rel_equal = gen::bounds::interval_rel_equal_2<T>;
    using rel_interior = gen::bounds::interval_rel_interior_2<T>;
    using rel_disjoint = gen::bounds::interval_rel_disjoint_2<T>;
};

/// Whether the kernels that build the interval of a point of T are proved: interval_make_1, or
/// make_2 and interval_make_2.
template <class T, int K>
concept interval_point_proved =
    proof_checked<typename interval_kernels<T, K>::make> && (K == 1 || proof_checked<gen::bounds::make_2<T>>);
/// Whether the kernels of the member test of a point of T are proved: interval_contains_1, or
/// make_2 and interval_contains_2.
template <class T, int K>
concept interval_member_proved =
    proof_checked<typename interval_kernels<T, K>::contains> && (K == 1 || proof_checked<gen::bounds::make_2<T>>);

// Whether an interval is canonical (milestone2.md, "Values of an interval"): the empty set,
// (+inf, -inf), the bounds of two limbs (+inf, +-0) and (-inf, +-0); or bounds lo <= hi, neither a
// NaN, with lo < +inf and hi > -inf, each of two limbs canonical. Comparisons are written b > a and
// b >= a: see detail::canonical. The test of a canonical pair of two limbs rounds (x0 + x1 == x0).
template <class T>
KAIRN_FORCEINLINE constexpr bool canonical_interval(const Expansion<T, 1>& lo, const Expansion<T, 1>& hi) noexcept {
    constexpr T inf = std::numeric_limits<T>::infinity();
    const T l = lo.limb[0], h = hi.limb[0];
    if (l == inf) return h == -inf;
    return h >= l && inf > l && h > -inf;  // false with a NaN bound
}
template <class T>
KAIRN_FORCEINLINE constexpr bool canonical_interval(const Expansion<T, 2>& lo, const Expansion<T, 2>& hi) noexcept {
    constexpr T inf = std::numeric_limits<T>::infinity();
    const T l = lo.limb[0], h = hi.limb[0];
    if (!canonical(lo) || !canonical(hi) || l != l || h != h) return false;
    if (l == inf) return h == -inf;
    if (!(inf > l && h > -inf)) return false;
    // lo <= hi for two canonical pairs: by the leading limbs, each the value rounded to nearest,
    // then by the second limbs.
    return h > l || (h == l && hi.limb[1] >= lo.limb[1]);
}

// The checks of KAIRN_CHECKS, once per operand: the environment, then a canonical interval, which
// is not checked when the environment is not the default one and KAIRN_ENVIRONMENT_FAILURE
// returned (check_environment).
template <class T, int K>
KAIRN_FORCEINLINE constexpr void check_interval([[maybe_unused]] const Interval<T, K>& x) noexcept {
#if KAIRN_CHECKS
    if (check_environment() && !canonical_interval(x.lower(), x.upper()))
        fail("an interval", "is not canonical (the empty set (+inf, -inf), or bounds lo <= hi, neither a NaN, with "
                            "lo < +inf, hi > -inf and each canonical), so no guarantee applies to the result");
#endif
}
// The same for a function that does not round (the negation, the hull, the intersection, the
// bounds as numbers of T): the environment without the rounding mode; then a canonical interval,
// which for two limbs is tested only when the rounding mode is to nearest, since the test of a
// canonical pair rounds (detail::check_exact).
template <class T, int K>
KAIRN_FORCEINLINE constexpr void check_interval_exact([[maybe_unused]] const Interval<T, K>& x) noexcept {
#if KAIRN_CHECKS
    if (check_environment_except_rounding() && (K == 1 || rounding_to_nearest()) &&
        !canonical_interval(x.lower(), x.upper()))
        fail("an interval", "is not canonical (the empty set (+inf, -inf), or bounds lo <= hi, neither a NaN, with "
                            "lo < +inf, hi > -inf and each canonical), so no guarantee applies to the result");
#endif
}

// The constructors, without their markers and constraints. One limb (interval_make_1): its only
// rounded operations are the guards of the bounds, lo + 0 and hi + 0, whose values are the bounds
// under every rounding mode, and every pair of values of T is accepted, so only the environment
// without the rounding mode is checked. Two limbs (interval_make_2): comparisons and selects,
// which do not round, on bounds that must be canonical, tested when the rounding mode is to
// nearest (check_exact). The interval of a point of T of two limbs: make_2, whose result is
// canonical by its proof, then interval_make_2; only the environment without the rounding mode is
// checked.
template <class T>
KAIRN_FORCEINLINE constexpr Interval<T, 1> make_interval(std::type_identity_t<T> lo, std::type_identity_t<T> hi) noexcept;
template <class T>
KAIRN_FORCEINLINE constexpr Interval<T, 2> make_interval_kernel(const Expansion<T, 2>& lo, const Expansion<T, 2>& hi) noexcept;
template <class T, int K>
KAIRN_FORCEINLINE constexpr Interval<T, K> make_interval(const Expansion<T, K>& lo, const Expansion<T, K>& hi) noexcept {
    if constexpr (K == 1) {
        return make_interval<T>(lo.limb[0], hi.limb[0]);
    } else {
        check_exact(lo, hi);
        return make_interval_kernel(lo, hi);
    }
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Interval<T, K> make_interval_point(std::type_identity_t<T> a) noexcept {
    if constexpr (K == 1) {
        return make_interval<T>(a, a);
    } else {
        check_environment_except_rounding();
        const Expansion<T, 2> x = make<T>(a);
        return make_interval_kernel(x, x);
    }
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Interval<T, K> make_interval_pair(std::type_identity_t<T> lo, std::type_identity_t<T> hi) noexcept {
    if constexpr (K == 1) {
        return make_interval<T>(lo, hi);
    } else {
        check_environment_except_rounding();
        return make_interval_kernel(make<T>(lo), make<T>(hi));
    }
}
// The interval of a ball (kernel ball_to_interval_1 or ball_to_interval_2), after the check of a
// canonical ball. Not constexpr for two limbs: the directed sums of two limbs have fused
// operations without a variant for constant evaluation.
template <class T>
KAIRN_FORCEINLINE constexpr Interval<T, 1> to_interval(const Ball<T, 1>& x) noexcept;
template <class T>
KAIRN_FORCEINLINE Interval<T, 2> to_interval(const Ball<T, 2>& x) noexcept;
// The midpoint and the radius (kernel interval_mid_rad_1 or interval_mid_rad_2), after the check of
// a canonical interval. Not constexpr for two limbs: each side of the radius is an upper bound from
// add_ball_2_2, which has fused operations without a variant for constant evaluation.
template <class T>
KAIRN_FORCEINLINE constexpr MidRad<T, 1> mid_rad(const Interval<T, 1>& x) noexcept;
template <class T>
KAIRN_FORCEINLINE MidRad<T, 2> mid_rad(const Interval<T, 2>& x) noexcept;

}  // namespace detail

/// An interval with bounds of K limbs of type T; defined for K = 1 and K = 2. A value is one of
/// (milestone2.md, "Values of an interval"):
/// - a nonempty interval [lo, hi]: the real numbers x with lo <= x <= hi, where lo <= hi, neither
///   bound is a NaN, lo < +inf and hi > -inf, and each bound is a number of the format or an
///   infinity (for two limbs a finite canonical pair, or (+-inf, 0)). An infinite bound is a bound,
///   never a member: [1, +inf] does not contain +inf. [-inf, +inf] is the whole line;
/// - the empty set, stored as (+inf, -inf) (for two limbs (+inf, 0) and (-inf, 0)), so that the
///   hull of two intervals is the smaller lower bound and the larger upper bound, with no test.
/// These are the canonical intervals; every constructor and operation returns one, and requires
/// canonical operands (checked when KAIRN_CHECKS is 1). There is no NaN interval, and a bound is
/// never a NaN.
///
/// Proved of every operation, in Flocq's model of IEEE 754 with overflow (statements I1 to I5 of
/// milestone2.md, "What is stated of an interval kernel"), for canonical operands X and Y and the
/// result Z of an operation: Z is canonical; it is empty exactly when an operand is; it contains
/// x op y for every real x in X and y in Y, unbounded operands included; and each operation says
/// how far its bounds are from those of the exact range {x op y} and when Z is bounded. For one
/// limb the bounds of a sum and a difference are the exact roundings outward of the exact ones,
/// the tightest interval of T; for two limbs they are within a bound proportional to u^2 of them,
/// and not the tightest interval of two limbs. The sign of a zero bound is not specified.
///
/// Kairn's intervals are modeled on IEEE Std 1788.1-2017 and differ from it on purpose in four
/// points (milestone2.md, "IEEE 1788"): a NaN given as a bound gives the whole line, not the empty
/// set; so does the same infinity given as both bounds, [+inf, +inf] or [-inf, -inf] (the interval
/// of an infinite point), which the standard makes the empty set, no real number being infinite;
/// the sign of a zero bound is not specified; and a product of one limb whose products of bounds
/// are below 2^(2p-1) eta in magnitude (2^-969 for double) may be one number of T wider than the
/// tightest on each side. Kairn has no decorations and no exceptions.
template <class T, int K>
class Interval {
    static_assert(detail::limb<T>, "Interval<T, k>: the limb type T is float or double");
    static_assert(K == 1 || K == 2, "Interval<T, k>: k is 1 or 2");

    Expansion<T, K> lo_{}, hi_{};

public:
    /// The point 0: the interval [0, 0], as Expansion() is 0 and Ball() the point 0.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr Interval() noexcept = default;
    /// The interval [a, a] of a point (kernel interval_make_1 or interval_make_2, with two limbs
    /// made by make_2 first): [a, a] for a finite a, and the whole line for a NaN or an infinite a.
    /// A value from the program that is not finite says that something failed or overflowed
    /// upstream, and says nothing about where the true value is: the whole line is the answer that
    /// is always true, and the empty set would say that there is no value. (IEEE 1788 makes
    /// [+inf, +inf] the empty set, an infinity being no real number; Kairn never makes the empty set
    /// of a value that is not finite.) So Interval(+inf).lower() is -inf and .upper() is +inf.
    /// Its only rounded operations are the guards, a + 0, whose values are a under every rounding
    /// mode (only the sign of a zero depends on the mode): not preceded by the debug build's check of
    /// the rounding mode (config.hpp).
    constexpr Interval(T a) noexcept
        requires detail::interval_point_proved<T, K>
        : Interval(detail::make_interval_point<T, K>(a)) {}
    /// The same with a marked operand: see kairn::Unverified.
    explicit constexpr Interval(Unverified<T> a) noexcept : Interval(detail::make_interval_point<T, K>(a.value)) {}
    /// The interval [a, a] of a number of K limbs (kernel interval_make_1 or interval_make_2), with
    /// the same cases as the constructor from a T: [a, a] for a finite a, the whole line otherwise.
    /// Does not round (comparisons and selects, and for one limb the guards): not preceded by the
    /// debug build's check of the rounding mode (config.hpp); a two-limb a must be canonical, which
    /// is checked when the rounding mode is to nearest.
    constexpr Interval(const Expansion<T, K>& a) noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::make>
        : Interval(detail::make_interval(a, a)) {}
    /// The same with a marked operand.
    explicit constexpr Interval(const Unverified<Expansion<T, K>>& a) noexcept
        : Interval(detail::make_interval(a.value, a.value)) {}
    /// The interval of two bounds (kernel interval_make_1 or interval_make_2); two values of T are
    /// first converted to K limbs, exactly. Proved, in the IEEE model, for any two values of T, or
    /// any two canonical numbers of two limbs: the result is canonical, and it is, by the first case
    /// that applies,
    /// - the whole line when a bound is a NaN, whatever the other bound is, and when both bounds are
    ///   the same infinity, [+inf, +inf] or [-inf, -inf]: a value from the program that is not finite
    ///   says that something failed or overflowed upstream, and the empty set would say that there
    ///   are no values (IEEE 1788 returns the empty set for both, and signals for a NaN; Kairn has no
    ///   exception by which to signal);
    /// - the empty set when the bounds are reversed, lo > hi, [+inf, -inf] and lo = +inf with a
    ///   finite hi among them. Reversed bounds are not reported by a debug build: they describe no
    ///   value, and the empty set is what they mean. Interval::empty() is the empty set;
    /// - otherwise [lo, hi], the same extended real numbers: lo <= hi, lo < +inf and hi > -inf,
    ///   [-inf, +inf], [lo, +inf] and [-inf, hi] included.
    /// Does not round (comparisons and selects; for one limb the guards of the bounds, whose values
    /// are the bounds under every rounding mode): not preceded by the debug build's check of the
    /// rounding mode (config.hpp); two-limb bounds must be canonical, which is checked when the
    /// rounding mode is to nearest.
    constexpr Interval(const Expansion<T, K>& lo, const Expansion<T, K>& hi) noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::make>
        : Interval(detail::make_interval(lo, hi)) {}
    /// The same with a marked lower bound.
    constexpr Interval(const Unverified<Expansion<T, K>>& lo, const Expansion<T, K>& hi) noexcept
        : Interval(detail::make_interval(lo.value, hi)) {}
    /// The same with a marked lower bound of T.
    constexpr Interval(Unverified<T> lo, T hi) noexcept : Interval(detail::make_interval_pair<T, K>(lo.value, hi)) {}
    /// An interval that contains the ball X (kernel ball_to_interval_1 or ball_to_interval_2).
    /// Proved, in the IEEE model, for a canonical ball: the interval is canonical, empty exactly
    /// when X is, and contains every member of X; the whole line gives [-inf, +inf]. For one limb it
    /// is the smallest interval of T that contains X, [RD(c - r), RU(c + r)], the roundings down and
    /// up in the format with overflow. For two limbs, for a finite ball and a bounded result, each
    /// bound is on its side of c - r or c + r and within A |v| + B of it, v being that bound, with
    /// the constants of the sum of two limbs, A about 8 u^2 and B about twice the smallest normal
    /// number of T (docs/reference/ball_to_interval_2.md gives them); a bound c - r or c + r that is
    /// exactly zero is returned as zero; the result is bounded when every member of X is at most
    /// 2^(e_max - 2) in magnitude, a quarter of the overflow threshold; it is not the smallest
    /// interval of two limbs. These are the values of X.lower() and X.upper().
    /// Explicit: the conversion widens the set. Rounds (it computes under rounding to nearest what
    /// rounding down and up give): preceded, when KAIRN_CHECKS is 1, by the check of the
    /// environment, the rounding mode included, and of a canonical ball (config.hpp). constexpr for
    /// one limb; for two not, its kernel having fused operations without a variant for constant
    /// evaluation.
    explicit constexpr Interval(const Ball<T, K>& x) noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::from_ball>
        : Interval(detail::to_interval(x)) {}
    /// The same with a marked operand.
    explicit constexpr Interval(const Unverified<Ball<T, K>>& x) noexcept : Interval(detail::to_interval(x.value)) {}
    /// Internal: a kernel's bounds, as they are.
    constexpr Interval(detail::kernel_result_t, const Expansion<T, K>& lo, const Expansion<T, K>& hi) noexcept
        : lo_(lo), hi_(hi) {}

    /// The empty set: (+inf, -inf), each bound of two limbs followed by a zero.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    [[nodiscard]] static constexpr Interval empty() noexcept {
        constexpr T inf = std::numeric_limits<T>::infinity();
        return Interval(detail::kernel_result, infinite(inf), infinite(-inf));
    }
    /// The whole line: [-inf, +inf], each bound of two limbs followed by a zero.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    [[nodiscard]] static constexpr Interval whole() noexcept {
        constexpr T inf = std::numeric_limits<T>::infinity();
        return Interval(detail::kernel_result, infinite(-inf), infinite(inf));
    }

    /// The lower bound, a number of K limbs: of a nonempty interval its lower bound (-inf when it is
    /// unbounded below), +inf for the empty set.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr const Expansion<T, K>& lower() const noexcept { return lo_; }
    /// The upper bound, a number of K limbs: of a nonempty interval its upper bound (+inf when it is
    /// unbounded above), -inf for the empty set.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr const Expansion<T, K>& upper() const noexcept { return hi_; }
    /// The lower bound as a number of T, for U = T: for one limb the bound itself; for two limbs the
    /// bound rounded down to T (kernel to_down_2), the largest number of T not above it, with
    /// overflow (-inf below -Omega), so a lower bound of every member. +inf for the empty set, -inf
    /// for an interval unbounded below.
    /// Does not round (a limb; for two limbs a comparison, a step of the bit pattern and a select):
    /// not preceded by the debug build's check of the rounding mode (config.hpp); for two limbs the
    /// interval must be canonical, which is checked when the rounding mode is to nearest. A U other
    /// than T needs conversions between limb types, which Kairn does not have yet (milestone2.md,
    /// question 16).
    template <class U>
        requires(std::is_same_v<U, T> && (K == 1 || detail::proof_checked<gen::bounds::to_down_2<T>>))
    constexpr U lower_as() const noexcept {
        if constexpr (K == 1) {
            return lo_.limb[0];
        } else {
            detail::check_interval_exact(*this);
            T l = T(0);
            gen::to_down_2(lo_.limb[0], lo_.limb[1], l);
            return l;
        }
    }
    /// The upper bound as a number of T, for U = T: for one limb the bound itself; for two limbs the
    /// bound rounded up to T (kernel to_up_2), the smallest number of T not below it, with overflow
    /// (+inf above Omega), so an upper bound of every member. -inf for the empty set, +inf for an
    /// interval unbounded above. Does not round, and is checked, as lower_as.
    template <class U>
        requires(std::is_same_v<U, T> && (K == 1 || detail::proof_checked<gen::bounds::to_up_2<T>>))
    constexpr U upper_as() const noexcept {
        if constexpr (K == 1) {
            return hi_.limb[0];
        } else {
            detail::check_interval_exact(*this);
            T h = T(0);
            gen::to_up_2(hi_.limb[0], hi_.limb[1], h);
            return h;
        }
    }

    /// Whether this is the empty set (kernel interval_empty_1 or interval_empty_2): its lower bound
    /// is +inf, which no nonempty canonical interval has. Proved, in the IEEE model, for a canonical
    /// interval: exact. IEEE 1788 calls it isEmpty.
    /// Does not round (a comparison): not preceded by the debug build's check of the rounding mode
    /// (config.hpp); for two limbs the interval must be canonical, which is checked when the
    /// rounding mode is to nearest. constexpr.
    constexpr bool is_empty() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::empty>
    {
        detail::check_interval_exact(*this);
        bool m = false;
        if constexpr (K == 1) {
            gen::interval_empty_1(lo_.limb[0], hi_.limb[0], m);
        } else {
            gen::interval_empty_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], m);
        }
        return m;
    }
    /// Whether this is the whole line, [-inf, +inf] (kernel interval_entire_1 or
    /// interval_entire_2): both bounds infinite. Proved, in the IEEE model, for a canonical
    /// interval: exact; false for the empty set and for a half-line. IEEE 1788 calls it isEntire;
    /// the name is that of Ball::is_whole(), so that code written for both reads the same, and the
    /// kernels keep the standard's. Does not round, and is checked, as is_empty(); constexpr.
    constexpr bool is_whole() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::entire>
    {
        detail::check_interval_exact(*this);
        bool m = false;
        if constexpr (K == 1) {
            gen::interval_entire_1(lo_.limb[0], hi_.limb[0], m);
        } else {
            gen::interval_entire_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], m);
        }
        return m;
    }

    /// Whether t, a value of T, is a member (kernel interval_contains_1 or interval_contains_2, for two
    /// limbs with t made a number of two limbs by make_2 first): lo <= t <= hi and t finite. Proved, in the IEEE model, for a canonical
    /// interval and every value of T: exact. The members of an interval are real numbers, so an
    /// infinite t or a NaN is a member of none, the whole line included ([1, +inf] does not contain
    /// +inf), and the empty set has no member. For two limbs this composes two proved kernels:
    /// make_2 gives t exactly as a number of two limbs ((t, 0), (+-inf, 0) or (NaN, NaN)), and
    /// interval_contains_2 answers exactly for that number; the composition is argued so, not
    /// machine-checked as one statement. kairn::member(t, X) is the same test, as a Trit.
    /// Does not round (comparisons; for two limbs the guard of make_2, t + 0, whose value is t under
    /// every rounding mode): not preceded by the debug build's check of the rounding mode
    /// (config.hpp); for two limbs the interval must be canonical, which is checked when the
    /// rounding mode is to nearest. constexpr.
    constexpr bool contains(T t) const noexcept
        requires detail::interval_member_proved<T, K>
    {
        return contains_point(t);
    }
    /// The same with a marked point: see kairn::Unverified.
    constexpr bool contains(Unverified<T> t) const noexcept { return contains_point(t.value); }
    /// Whether t, a number of K limbs, is a member (kernel interval_contains_1 or
    /// interval_contains_2): lo <= t <= hi and t finite, as contains(T). Proved, in the IEEE model,
    /// for a canonical interval and a canonical t: exact. Does not round, and is checked, as
    /// is_empty(); a t of two limbs must be canonical, which is checked when the rounding mode is to
    /// nearest. constexpr.
    constexpr bool contains(const Expansion<T, K>& t) const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::contains>
    {
        return contains_number(t);
    }
    /// The same with a marked point.
    constexpr bool contains(const Unverified<Expansion<T, K>>& t) const noexcept { return contains_number(t.value); }
    /// Whether Y is a subset of this interval: every member of Y is a member of this one (kernel
    /// interval_subset_1 or interval_subset_2, with Y as its first operand: y_l >= lo and
    /// y_u <= hi on the stored bounds). Proved, in the IEEE model, for canonical intervals: exact,
    /// with the readings of IEEE 1788 for the empty set: it is a subset of every interval, so
    /// X.contains(Interval::empty()) is true for every X, and the empty set contains no nonempty
    /// interval. kairn::ieee1788::subset(Y, X) is the same answer. Only an Interval of the same T
    /// and K is accepted: a point is not made an interval here (contains(t) is the member test,
    /// which differs on an infinite point).
    /// Does not round (comparisons): not preceded by the debug build's check of the rounding mode
    /// (config.hpp). constexpr.
    template <int J>
        requires(J == K && detail::proof_checked<typename detail::interval_kernels<T, K>::subset>)
    constexpr bool contains(const Interval<T, J>& y) const noexcept {
        return contains_set(y);
    }
    /// The same with a marked operand.
    constexpr bool contains(const Unverified<Interval>& y) const noexcept { return contains_set(y.value); }

    /// Whether every member is positive and the interval is not empty (kernel interval_positive_1
    /// or interval_positive_2): 0 < lo < +inf, on the leading limb of the lower bound. Proved, in
    /// the IEEE model, for a canonical interval: exact. False for the empty set, although "every
    /// member is positive" is vacuously true of it: a query about nothing answers no, and is_empty()
    /// is the query to make first (milestone2.md, "The empty set and the whole line").
    /// Does not round (comparisons): not preceded by the debug build's check of the rounding mode
    /// (config.hpp). constexpr.
    constexpr bool certainly_positive() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::positive>
    {
        detail::check_interval_exact(*this);
        bool m = false;
        if constexpr (K == 1) {
            gen::interval_positive_1(lo_.limb[0], hi_.limb[0], m);
        } else {
            gen::interval_positive_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], m);
        }
        return m;
    }
    /// Whether every member is negative and the interval is not empty (kernel interval_negative_1
    /// or interval_negative_2): -inf < hi < 0, on the leading limb of the upper bound. Exact; false
    /// for the empty set. Does not round, and is checked, as certainly_positive(); constexpr.
    constexpr bool certainly_negative() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::negative>
    {
        detail::check_interval_exact(*this);
        bool m = false;
        if constexpr (K == 1) {
            gen::interval_negative_1(lo_.limb[0], hi_.limb[0], m);
        } else {
            gen::interval_negative_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], m);
        }
        return m;
    }
    /// Whether the interval is [0, 0], its only member 0 (kernel interval_zero_1 or
    /// interval_zero_2): both bounds zero. Exact; false for the empty set. Does not round, and is
    /// checked, as certainly_positive(); constexpr.
    constexpr bool certainly_zero() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::zero>
    {
        detail::check_interval_exact(*this);
        bool m = false;
        if constexpr (K == 1) {
            gen::interval_zero_1(lo_.limb[0], hi_.limb[0], m);
        } else {
            gen::interval_zero_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], m);
        }
        return m;
    }

    /// The midpoint (kernel interval_mid_rad_1 or interval_mid_rad_2): the sum of the halves of the
    /// bounds, moved into the interval if a halving underflowed. It runs the kernel of the midpoint
    /// and the radius, and so does radius(): a program that needs both calls mid_rad(), which runs
    /// it once (twice the cost was measured for the two calls, docs/developer/results/
    /// bench-milestone2.md). Proved, in the IEEE model, for a canonical interval: for a bounded
    /// [l, h], a finite m with l <= m <= h and, for one limb, |m - (l + h)/2| <= u |(l + h)/2| + eta,
    /// for two limbs a normalized pair with |m - (l + h)/2| <= 3u^2/(1 - 4u) |(l + h)/2| + 2 eta;
    /// 0 for the whole line; Omega, the largest finite number of T, for [l, +inf] with l finite, and
    /// -Omega for [-inf, h]; a NaN (every limb) for the empty set. These are the values of mid in
    /// IEEE 1788, but for a bounded interval of one limb with a bound that is an odd multiple of
    /// eta, where the result is within eta and one rounding of the midpoint and need not be the
    /// midpoint rounded to nearest; for two limbs the midpoint is a canonical number in every case.
    /// Rounds (halvings and a sum): preceded, when KAIRN_CHECKS is 1, by the check of the
    /// environment, the rounding mode included, and of a canonical interval (config.hpp). constexpr
    /// for one limb; for two not, its kernel having fused operations without a variant for constant
    /// evaluation.
    constexpr Expansion<T, K> midpoint() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::mid_rad>
    {
        return detail::mid_rad(*this).midpoint;
    }
    /// The radius, for the midpoint that midpoint() returns (kernel interval_mid_rad_1 or
    /// interval_mid_rad_2), a number of T; it runs the whole kernel, as midpoint() does (mid_rad()
    /// gives both from one call). Proved, in the IEEE model, for a canonical interval: for a bounded
    /// [l, h] and one limb, the smallest number r of T with [m - r, m + r] containing [l, h],
    /// RU(max(m - l, h - m)); for two limbs a number r of T with [m - r, m + r] containing [l, h],
    /// not claimed the smallest, which is +inf for a bounded interval near the top of the range and
    /// finite when |l| and |h| are at most 2^(e_max - 2), a quarter of the overflow threshold;
    /// +inf for an unbounded interval; a NaN for the empty set, as rad in IEEE 1788. Rounds, and is
    /// checked, as midpoint(); constexpr for one limb.
    constexpr T radius() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::mid_rad>
    {
        return detail::mid_rad(*this).radius;
    }
    /// The midpoint and the radius together, from one call of their kernel (interval_mid_rad_1 or
    /// interval_mid_rad_2): the values of midpoint() and radius(), with their statements. Rounds,
    /// and is checked, as midpoint(); constexpr for one limb.
    constexpr MidRad<T, K> mid_rad() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::mid_rad>
    {
        return detail::mid_rad(*this);
    }
    /// Two intervals that together are this one and meet at a point of it (kernel interval_split_1
    /// or interval_split_2): left = [l, p] and right = [p, h]. Proved, in the IEEE model, for a
    /// canonical interval: both are canonical; both are empty for the empty set; otherwise neither
    /// is, left.lower() is l, right.upper() is h, and left.upper() equals right.lower(), a point p
    /// of the interval. **Which point p is, is not claimed.** The listing splits at the midpoint of
    /// mid_rad(), moved into the interval for two limbs (a bound of two limbs can lie beyond Omega,
    /// and then the midpoint Omega of a half-line is outside it), but no claim says so, and p can be
    /// a bound: [l, h] with h the number after l is split into itself and a point. A bisection
    /// therefore needs its own test of progress, such as a radius of each part at most three
    /// quarters of that of the interval (docs/tutorials/bisection.md). Rounds (halvings and a sum),
    /// and is checked, as midpoint(); constexpr.
    constexpr Split<Interval> split() const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::split>
    {
        detail::check_interval(*this);
        Expansion<T, K> al, au, bl, bu;
        if constexpr (K == 1) {
            gen::interval_split_1(lo_.limb[0], hi_.limb[0], al.limb[0], au.limb[0], bl.limb[0], bu.limb[0]);
        } else {
            gen::interval_split_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], al.limb[0], al.limb[1],
                                  au.limb[0], au.limb[1], bl.limb[0], bl.limb[1], bu.limb[0], bu.limb[1]);
        }
        return {Interval(detail::kernel_result, al, au), Interval(detail::kernel_result, bl, bu)};
    }

    /// The hull of this interval and Y, the smallest interval that contains both (kernel
    /// interval_hull_1 or interval_hull_2). Proved, in the IEEE model, for canonical intervals: the
    /// result is canonical; empty exactly when both are; otherwise its lower bound is the smaller of
    /// the lower bounds of the operands that are not empty and its upper bound the larger of their
    /// upper bounds, exactly; the hull with the empty set is the other operand.
    /// Does not round (comparisons and selects): not preceded by the debug build's check of the
    /// rounding mode (config.hpp). constexpr.
    constexpr Interval hull(const Interval& y) const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::hull>
    {
        return hull_of(y);
    }
    /// The same with a marked operand.
    constexpr Interval hull(const Unverified<Interval>& y) const noexcept { return hull_of(y.value); }
    /// The intersection of this interval and Y (kernel interval_intersection_1 or
    /// interval_intersection_2). Proved, in the IEEE model, for canonical intervals: the result is
    /// canonical; empty exactly when no real number is a member of both, that is when an operand is
    /// empty or the larger lower bound is above the smaller upper bound; otherwise exactly the
    /// larger lower bound and the smaller upper bound; the intersection with the whole line is the
    /// other operand.
    /// Does not round (comparisons and selects): not preceded by the debug build's check of the
    /// rounding mode (config.hpp). constexpr.
    constexpr Interval intersection(const Interval& y) const noexcept
        requires detail::proof_checked<typename detail::interval_kernels<T, K>::intersection>
    {
        return intersection_of(y);
    }
    /// The same with a marked operand.
    constexpr Interval intersection(const Unverified<Interval>& y) const noexcept { return intersection_of(y.value); }

private:
    // A bound that is an infinity: the infinity, and for two limbs a zero, written into the limbs.
    static constexpr Expansion<T, K> infinite(T a) noexcept {
        Expansion<T, K> x;
        x.limb[0] = a;
        return x;
    }
    // The member tests and the subset test, without their markers and constraints.
    constexpr bool contains_point(T t) const noexcept {
        if constexpr (K == 1) {
            return contains_number(Expansion<T, 1>(t));
        } else {
            detail::check_interval_exact(*this);
            const Expansion<T, 2> p = detail::make<T>(t);
            bool m = false;
            gen::interval_contains_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], p.limb[0], p.limb[1], m);
            return m;
        }
    }
    constexpr bool contains_number(const Expansion<T, K>& t) const noexcept {
        detail::check_interval_exact(*this);
        bool m = false;
        if constexpr (K == 1) {
            gen::interval_contains_1(lo_.limb[0], hi_.limb[0], t.limb[0], m);
        } else {
            detail::check_exact(t);
            gen::interval_contains_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], t.limb[0], t.limb[1], m);
        }
        return m;
    }
    // Y inside this interval: the kernel's first operand is Y.
    constexpr bool contains_set(const Interval& y) const noexcept {
        detail::check_interval_exact(*this);
        detail::check_interval_exact(y);
        bool m = false;
        if constexpr (K == 1) {
            gen::interval_subset_1(y.lo_.limb[0], y.hi_.limb[0], lo_.limb[0], hi_.limb[0], m);
        } else {
            gen::interval_subset_2(y.lo_.limb[0], y.lo_.limb[1], y.hi_.limb[0], y.hi_.limb[1], lo_.limb[0], lo_.limb[1],
                                   hi_.limb[0], hi_.limb[1], m);
        }
        return m;
    }
    constexpr Interval hull_of(const Interval& y) const noexcept {
        detail::check_interval_exact(*this);
        detail::check_interval_exact(y);
        Expansion<T, K> l, h;
        if constexpr (K == 1) {
            gen::interval_hull_1(lo_.limb[0], hi_.limb[0], y.lo_.limb[0], y.hi_.limb[0], l.limb[0], h.limb[0]);
        } else {
            gen::interval_hull_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], y.lo_.limb[0], y.lo_.limb[1],
                                 y.hi_.limb[0], y.hi_.limb[1], l.limb[0], l.limb[1], h.limb[0], h.limb[1]);
        }
        return Interval(detail::kernel_result, l, h);
    }
    constexpr Interval intersection_of(const Interval& y) const noexcept {
        detail::check_interval_exact(*this);
        detail::check_interval_exact(y);
        Expansion<T, K> l, h;
        if constexpr (K == 1) {
            gen::interval_intersection_1(lo_.limb[0], hi_.limb[0], y.lo_.limb[0], y.hi_.limb[0], l.limb[0], h.limb[0]);
        } else {
            gen::interval_intersection_2(lo_.limb[0], lo_.limb[1], hi_.limb[0], hi_.limb[1], y.lo_.limb[0],
                                         y.lo_.limb[1], y.hi_.limb[0], y.hi_.limb[1], l.limb[0], l.limb[1],
                                         h.limb[0], h.limb[1]);
        }
        return Interval(detail::kernel_result, l, h);
    }
};

/// The marked form of an Interval operand: see kairn::Unverified.
template <class T, int K>
struct Unverified<Interval<T, K>> {
    Interval<T, K> value;  ///< The operand.
};

/// Marks x as an operand of an operation whose proof is not checked yet; see kairn::Unverified.
template <class T, int K>
KAIRN_FORCEINLINE constexpr Unverified<Interval<T, K>> unverified(const Interval<T, K>& x) noexcept {
    return {x};
}

namespace detail {

template <class T>
KAIRN_FORCEINLINE constexpr Interval<T, 1> make_interval(std::type_identity_t<T> lo, std::type_identity_t<T> hi) noexcept {
    check_environment_except_rounding();
    T l = T(0), h = T(0);
    gen::interval_make_1(lo, hi, l, h);
    return Interval<T, 1>(kernel_result, Expansion<T, 1>(l), Expansion<T, 1>(h));
}
template <class T>
KAIRN_FORCEINLINE constexpr Interval<T, 2> make_interval_kernel(const Expansion<T, 2>& lo, const Expansion<T, 2>& hi) noexcept {
    Expansion<T, 2> l, h;
    gen::interval_make_2(lo.limb[0], lo.limb[1], hi.limb[0], hi.limb[1], l.limb[0], l.limb[1], h.limb[0], h.limb[1]);
    return Interval<T, 2>(kernel_result, l, h);
}
template <class T>
KAIRN_FORCEINLINE constexpr Interval<T, 1> to_interval(const Ball<T, 1>& x) noexcept {
    check_ball(x);
    T l = T(0), h = T(0);
    gen::ball_to_interval_1(x.center().limb[0], x.radius(), l, h);
    return Interval<T, 1>(kernel_result, Expansion<T, 1>(l), Expansion<T, 1>(h));
}
template <class T>
KAIRN_FORCEINLINE Interval<T, 2> to_interval(const Ball<T, 2>& x) noexcept {
    Expansion<T, 2> l, h;
    ball_bounds(x, l, h);
    return Interval<T, 2>(kernel_result, l, h);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> to_ball(const Interval<T, 1>& x) noexcept {
    check_interval(x);
    T c = T(0), r = T(0);
    gen::interval_to_ball_1(x.lower().limb[0], x.upper().limb[0], c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> to_ball(const Interval<T, 2>& x) noexcept {
    check_interval(x);
    Expansion<T, 2> c;
    T r = T(0);
    gen::interval_to_ball_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1], c.limb[0],
                            c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE constexpr MidRad<T, 1> mid_rad(const Interval<T, 1>& x) noexcept {
    check_interval(x);
    T m = T(0), r = T(0);
    gen::interval_mid_rad_1(x.lower().limb[0], x.upper().limb[0], m, r);
    return {Expansion<T, 1>(m), r};
}
template <class T>
KAIRN_FORCEINLINE MidRad<T, 2> mid_rad(const Interval<T, 2>& x) noexcept {
    check_interval(x);
    Expansion<T, 2> m;
    T r = T(0);
    gen::interval_mid_rad_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1], m.limb[0],
                            m.limb[1], r);
    return {m, r};
}

// The three-valued comparisons and the relations of IEEE 1788 of two intervals, and the member
// test of kairn::member, without their markers and constraints: one kernel each, comparisons and
// selects that do not round, so the rounding mode is not checked (check_interval_exact). The
// kernels of the comparisons return the two masks of a Trit; trit() makes it, and opposite()
// exchanges yes and no for not_equal; greater and greater_equal are less and less_equal of the
// operands exchanged; member is the member test, whose claim is exact, as a Trit that is never
// unknown.
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit less(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    check_interval_exact(x);
    check_interval_exact(y);
    bool yes = false, no = false;
    if constexpr (K == 1) {
        gen::interval_less_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], yes, no);
    } else {
        gen::interval_less_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1],
                             y.lower().limb[0], y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], yes, no);
    }
    return trit(yes, no);
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit less_equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    check_interval_exact(x);
    check_interval_exact(y);
    bool yes = false, no = false;
    if constexpr (K == 1) {
        gen::interval_less_equal_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], yes,
                                   no);
    } else {
        gen::interval_less_equal_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1],
                                   y.lower().limb[0], y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], yes, no);
    }
    return trit(yes, no);
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    check_interval_exact(x);
    check_interval_exact(y);
    bool yes = false, no = false;
    if constexpr (K == 1) {
        gen::interval_equal_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], yes, no);
    } else {
        gen::interval_equal_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1],
                              y.lower().limb[0], y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], yes, no);
    }
    return trit(yes, no);
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit greater(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::less(y, x);
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit greater_equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::less_equal(y, x);
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit not_equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::opposite(detail::equal(x, y));
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit member(std::type_identity_t<T> t, const Interval<T, K>& x) noexcept {
    return x.contains(unverified(t)) ? Trit::yes : Trit::no;
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr Trit member(const Expansion<T, K>& t, const Interval<T, K>& x) noexcept {
    return x.contains(unverified(t)) ? Trit::yes : Trit::no;
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr bool rel_subset(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return y.contains(unverified(x));
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr bool rel_equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    check_interval_exact(x);
    check_interval_exact(y);
    bool m = false;
    if constexpr (K == 1) {
        gen::interval_rel_equal_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], m);
    } else {
        gen::interval_rel_equal_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1],
                                  y.lower().limb[0], y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], m);
    }
    return m;
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr bool rel_interior(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    check_interval_exact(x);
    check_interval_exact(y);
    bool m = false;
    if constexpr (K == 1) {
        gen::interval_rel_interior_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], m);
    } else {
        gen::interval_rel_interior_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1],
                                     y.lower().limb[0], y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], m);
    }
    return m;
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr bool rel_disjoint(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    check_interval_exact(x);
    check_interval_exact(y);
    bool m = false;
    if constexpr (K == 1) {
        gen::interval_rel_disjoint_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], m);
    } else {
        gen::interval_rel_disjoint_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1],
                                     y.lower().limb[0], y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], m);
    }
    return m;
}

// The negation: two changes of sign and an exchange, inline in every setting, and constexpr. It
// does not round: the rounding mode is not checked (check_interval_exact).
template <class T, int K>
KAIRN_FORCEINLINE constexpr Interval<T, K> neg(const Interval<T, K>& x) noexcept {
    check_interval_exact(x);
    Expansion<T, K> l, h;
    if constexpr (K == 1) {
        gen::interval_neg_1(x.lower().limb[0], x.upper().limb[0], l.limb[0], h.limb[0]);
    } else {
        gen::interval_neg_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1], l.limb[0],
                            l.limb[1], h.limb[0], h.limb[1]);
    }
    return Interval<T, K>(kernel_result, l, h);
}

// The operations that round, without their markers and constraints: one kernel each. Where their
// code is depends on KAIRN_ENCLOSURE_CODE (config.hpp), as for the operations of Ball that round:
// declared here, defined in interval_operations.hpp, which the end of this header includes unless
// the setting is KAIRN_ENCLOSURE_CODE_EXTERNAL, and then kairn/definitions.hpp, in the one
// translation unit of the program that defines them. Not constexpr: the kernels of the product of
// one limb and of every operation of two limbs have fused operations without a variant for
// constant evaluation, and none can be evaluated at compile time when its definition is in another
// translation unit (KAIRN_ENCLOSURE_CODE_EXTERNAL), the sum and the difference of one limb
// included, although their kernels are constexpr.
KAIRN_DETAIL_ENCLOSURE_BEGIN
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 1> add(const Interval<T, 1>& x, const Interval<T, 1>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 1> sub(const Interval<T, 1>& x, const Interval<T, 1>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 1> mul(const Interval<T, 1>& x, const Interval<T, 1>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 2> add(const Interval<T, 2>& x, const Interval<T, 2>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 2> sub(const Interval<T, 2>& x, const Interval<T, 2>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 2> mul(const Interval<T, 2>& x, const Interval<T, 2>& y) noexcept;
KAIRN_DETAIL_ENCLOSURE_END

// The instances of those operations that KAIRN_ENCLOSURE_CODE_EXTERNAL leaves to
// kairn/definitions.hpp: for the limb type T, with PREFIX extern for their declarations and
// nothing for their definitions.
#define KAIRN_DETAIL_INTERVAL_INSTANCES(PREFIX, T)                                                          \
    PREFIX template Interval<T, 1> add<T>(const Interval<T, 1>&, const Interval<T, 1>&) noexcept;           \
    PREFIX template Interval<T, 1> sub<T>(const Interval<T, 1>&, const Interval<T, 1>&) noexcept;           \
    PREFIX template Interval<T, 1> mul<T>(const Interval<T, 1>&, const Interval<T, 1>&) noexcept;           \
    PREFIX template Interval<T, 2> add<T>(const Interval<T, 2>&, const Interval<T, 2>&) noexcept;           \
    PREFIX template Interval<T, 2> sub<T>(const Interval<T, 2>&, const Interval<T, 2>&) noexcept;           \
    PREFIX template Interval<T, 2> mul<T>(const Interval<T, 2>&, const Interval<T, 2>&) noexcept;

template <class X, class Y>
concept marked_interval_pair = (marked<X> || marked<Y>) && (interval<X> || interval<Y>);
template <class X, class Y>
concept marked_interval_rhs = marked<Y> && !marked<X> && interval<X>;

}  // namespace detail

// The operators. As for Expansion and Ball, they are function templates, so that no operand
// converts: two intervals of the same T and K, and nothing else. A number is not an operand of an
// interval operation (no kernel takes one); Interval(a) is the interval of a point.

/// X + Y (kernel interval_add_1 or interval_add_2). Proved, in the IEEE model, for canonical X and
/// Y (I1 to I5): the result Z is canonical, empty exactly when an operand is, and contains x + y for
/// every x in X and y in Y. For one limb, of nonempty operands, Z is [RD(l), RU(h)] with [l, h] the
/// exact range, the tightest interval of T, an infinite bound of the range staying infinite; for
/// bounded operands Z is bounded exactly when every member of the exact range is at most Omega in
/// magnitude ([Omega, +inf] when the sum of two large bounds overflows). For two limbs, of bounded
/// operands and a bounded Z: l - zl <= A |l| + B and zu - h <= A |h| + B, with A about 8 u^2 and B
/// about twice the smallest normal number of T (docs/reference/interval_add_2.md gives them), not
/// the tightest interval of two limbs; a bound of the exact range that is zero is returned as zero,
/// so [0, 0] + [0, 0] is [0, 0]; an infinite bound of the range is returned as such; Z is bounded
/// when every member of the exact range is at most 2^(e_max - 2) in magnitude, a quarter of the
/// overflow threshold, and an overflow beyond gives the infinite bound on its side. Rounds. Not
/// usable in constant evaluation: its code is where KAIRN_ENCLOSURE_CODE puts it.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::add>
KAIRN_FORCEINLINE Interval<T, K> operator+(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::add(x, y);
}
/// X - Y (kernel interval_sub_1 or interval_sub_2): the statements of X + Y, for the exact range
/// {x - y}; for two limbs a bound of it that is zero is returned as zero, so X - X is [0, 0] when X
/// is a point. Rounds; not usable in constant evaluation.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::sub>
KAIRN_FORCEINLINE Interval<T, K> operator-(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::sub(x, y);
}
/// X * Y (kernel interval_mul_1 or interval_mul_2): the least and the greatest of the four products
/// of bounds, each rounded outward, with 0 times an infinite bound taken as 0. Proved, in the IEEE
/// model, for canonical X and Y: the result Z is canonical, empty exactly when an operand is, and
/// contains x y for every x in X and y in Y, unbounded operands included. For one limb, of nonempty
/// operands with exact range [l, h]: zl is RD(l) or the number of T below it, and zu is RU(h) or
/// the number above it; exactly RD(l) and RU(h) when each product of a finite bound of X and a
/// finite bound of Y is zero or at least 2^(2p-1) eta in magnitude (2^-969 for double, 2^-102 for
/// float); for bounded operands Z is bounded exactly when every member of the exact range is at
/// most Omega in magnitude. For two limbs, of bounded operands and a bounded Z, each bound within
/// A |v| + B of the bound v of the exact range, with A about 10 u^2 and B about twice the smallest
/// normal number (docs/reference/interval_mul_2.md); no bound is claimed exact, but [0, 0] times a
/// nonempty interval, unbounded included, is [0, 0]; an infinite bound of the range is returned as
/// such; Z is bounded when every member of the exact range is at most 2^(e_max - 2) in magnitude.
/// Rounds. Not usable in constant evaluation: its kernel has fused operations without a variant
/// for it, and its code is where KAIRN_ENCLOSURE_CODE puts it. The kernel of two limbs, some four
/// hundred operations, is an ordinary inline function in every setting, which the compiler may call
/// rather than inline (milestone2.md, "Inlining and compile time").
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::mul>
KAIRN_FORCEINLINE Interval<T, K> operator*(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::mul(x, y);
}
/// -X (kernel interval_neg_1 or interval_neg_2): the bounds negated and exchanged, exactly; the
/// empty set and the whole line stay what they are.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::neg>
KAIRN_FORCEINLINE constexpr Interval<T, K> operator-(const Interval<T, K>& x) noexcept {
    return detail::neg(x);
}
/// X = X + Y (kernel interval_add_1 or interval_add_2).
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::add>
KAIRN_FORCEINLINE Interval<T, K>& operator+=(Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return x = detail::add(x, y);
}
/// X = X - Y (kernel interval_sub_1 or interval_sub_2).
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::sub>
KAIRN_FORCEINLINE Interval<T, K>& operator-=(Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return x = detail::sub(x, y);
}
/// X = X * Y (kernel interval_mul_1 or interval_mul_2).
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::mul>
KAIRN_FORCEINLINE Interval<T, K>& operator*=(Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return x = detail::mul(x, y);
}

/// X + Y with a marked operand.
template <class X, class Y>
    requires detail::marked_interval_pair<X, Y>
KAIRN_FORCEINLINE auto operator+(const X& x, const Y& y) noexcept
    -> decltype(detail::add(detail::unmark(x), detail::unmark(y))) {
    return detail::add(detail::unmark(x), detail::unmark(y));
}
/// X - Y with a marked operand.
template <class X, class Y>
    requires detail::marked_interval_pair<X, Y>
KAIRN_FORCEINLINE auto operator-(const X& x, const Y& y) noexcept
    -> decltype(detail::sub(detail::unmark(x), detail::unmark(y))) {
    return detail::sub(detail::unmark(x), detail::unmark(y));
}
/// X * Y with a marked operand.
template <class X, class Y>
    requires detail::marked_interval_pair<X, Y>
KAIRN_FORCEINLINE auto operator*(const X& x, const Y& y) noexcept
    -> decltype(detail::mul(detail::unmark(x), detail::unmark(y))) {
    return detail::mul(detail::unmark(x), detail::unmark(y));
}
/// -X with a marked operand.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class X>
    requires detail::marked<X> && detail::interval<X>
KAIRN_FORCEINLINE constexpr auto operator-(const X& x) noexcept -> decltype(detail::neg(detail::unmark(x))) {
    return detail::neg(detail::unmark(x));
}
/// X = X + Y with a marked right operand.
template <class X, class Y>
    requires detail::marked_interval_rhs<X, Y>
KAIRN_FORCEINLINE auto operator+=(X& x, const Y& y) noexcept -> decltype(x = detail::add(x, detail::unmark(y))) {
    return x = detail::add(x, detail::unmark(y));
}
/// X = X - Y with a marked right operand.
template <class X, class Y>
    requires detail::marked_interval_rhs<X, Y>
KAIRN_FORCEINLINE auto operator-=(X& x, const Y& y) noexcept -> decltype(x = detail::sub(x, detail::unmark(y))) {
    return x = detail::sub(x, detail::unmark(y));
}
/// X = X * Y with a marked right operand.
template <class X, class Y>
    requires detail::marked_interval_rhs<X, Y>
KAIRN_FORCEINLINE auto operator*=(X& x, const Y& y) noexcept -> decltype(x = detail::mul(x, detail::unmark(y))) {
    return x = detail::mul(x, detail::unmark(y));
}

// The three-valued comparisons (milestone2.md, "Comparisons"), as functions and not operators:
// each answer is a kairn::Trit, which does not convert to bool, so that a program says which answer
// it acts on (kairn::certainly, kairn::possibly). Function templates, so that no operand converts:
// two intervals of the same T and K. The same names compare balls (ball.hpp). Each is exact for
// intervals of one and of two limbs: the comparisons of bounds of two limbs are exact.

/// The three-valued X < Y of intervals (kernel interval_less_1 or interval_less_2): yes when every
/// member of X is below every member of Y, x_u < y_l; no when no member of X is below a member of
/// Y, x_l >= y_u; unknown otherwise, and when an operand is empty (a query about nothing answers
/// neither). Proved, in the IEEE model, for canonical intervals: exact, so unknown exactly when
/// neither holds; with the whole line, never yes or no. Does not round (comparisons): not preceded
/// by the debug build's check of the rounding mode (config.hpp). constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::less>
KAIRN_FORCEINLINE constexpr Trit less(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::less(x, y);
}
/// The three-valued X <= Y (kernel interval_less_equal_1 or interval_less_equal_2): yes when
/// x_u <= y_l, no when x_l > y_u, unknown otherwise and for an empty operand; exact, as less().
/// Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::less_equal>
KAIRN_FORCEINLINE constexpr Trit less_equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::less_equal(x, y);
}
/// The three-valued X > Y: less(Y, X), the same kernel (interval_less_1 or interval_less_2) with
/// the operands exchanged, and its statement. Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::less>
KAIRN_FORCEINLINE constexpr Trit greater(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::greater(x, y);
}
/// The three-valued X >= Y: less_equal(Y, X) (kernel interval_less_equal_1 or
/// interval_less_equal_2). Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::less_equal>
KAIRN_FORCEINLINE constexpr Trit greater_equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::greater_equal(x, y);
}
/// The three-valued X = Y (kernel interval_equal_1 or interval_equal_2): yes when every member of
/// X equals every member of Y, that is when both are the same point, x_l = x_u = y_l = y_u; no
/// when no member of X equals a member of Y, the intervals being disjoint; unknown otherwise and
/// for an empty operand. Exact. Not the relation equal of IEEE 1788, whose answer is whether the
/// two sets have the same members: that is kairn::ieee1788::equal. Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::equal>
KAIRN_FORCEINLINE constexpr Trit equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::equal(x, y);
}
/// The three-valued X != Y: equal(X, Y) with yes and no exchanged (kernel interval_equal_1 or
/// interval_equal_2): yes when the intervals are disjoint, no when both are the same point. Does
/// not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::equal>
KAIRN_FORCEINLINE constexpr Trit not_equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::not_equal(x, y);
}
/// Whether t, a value of T, is a member of X, as a Trit (kernel interval_contains_1 or
/// interval_contains_2, with make_2 first for two limbs, as X.contains(t)): yes when it is, no when it
/// is not; the answer is exact, so never unknown. For code written for intervals and balls alike,
/// where the answer about a ball of two limbs is only certain. Does not round. constexpr.
template <class T, int K>
    requires detail::interval_member_proved<T, K>
KAIRN_FORCEINLINE constexpr Trit member(std::type_identity_t<T> t, const Interval<T, K>& x) noexcept {
    return detail::member(t, x);
}
/// Whether t, a number of K limbs, is a member of X, as a Trit (kernel interval_contains_1 or
/// interval_contains_2): exact, never unknown, as X.contains(t). Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::contains>
KAIRN_FORCEINLINE constexpr Trit member(const Expansion<T, K>& t, const Interval<T, K>& x) noexcept {
    return detail::member(t, x);
}

namespace detail {
template <class X, class Y>
concept marked_enclosure_pair = (marked<X> || marked<Y>) && enclosure<X> && enclosure<Y>;
template <class P, class X>
concept marked_member = (marked<P> || marked<X>) && !enclosure<P> && enclosure<X>;
}  // namespace detail

/// less(X, Y) with a marked operand, of intervals or of balls.
template <class X, class Y>
    requires detail::marked_enclosure_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto less(const X& x, const Y& y) noexcept
    -> decltype(detail::less(detail::unmark(x), detail::unmark(y))) {
    return detail::less(detail::unmark(x), detail::unmark(y));
}
/// less_equal(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_enclosure_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto less_equal(const X& x, const Y& y) noexcept
    -> decltype(detail::less_equal(detail::unmark(x), detail::unmark(y))) {
    return detail::less_equal(detail::unmark(x), detail::unmark(y));
}
/// greater(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_enclosure_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto greater(const X& x, const Y& y) noexcept
    -> decltype(detail::greater(detail::unmark(x), detail::unmark(y))) {
    return detail::greater(detail::unmark(x), detail::unmark(y));
}
/// greater_equal(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_enclosure_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto greater_equal(const X& x, const Y& y) noexcept
    -> decltype(detail::greater_equal(detail::unmark(x), detail::unmark(y))) {
    return detail::greater_equal(detail::unmark(x), detail::unmark(y));
}
/// equal(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_enclosure_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto equal(const X& x, const Y& y) noexcept
    -> decltype(detail::equal(detail::unmark(x), detail::unmark(y))) {
    return detail::equal(detail::unmark(x), detail::unmark(y));
}
/// not_equal(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_enclosure_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto not_equal(const X& x, const Y& y) noexcept
    -> decltype(detail::not_equal(detail::unmark(x), detail::unmark(y))) {
    return detail::not_equal(detail::unmark(x), detail::unmark(y));
}
/// member(t, X) with a marked operand, of an interval or a ball.
template <class P, class X>
    requires detail::marked_member<P, X>
KAIRN_FORCEINLINE constexpr auto member(const P& t, const X& x) noexcept
    -> decltype(detail::member(detail::unmark(t), detail::unmark(x))) {
    return detail::member(detail::unmark(t), detail::unmark(x));
}

/// The relations of IEEE Std 1788.1-2017 of two intervals, under the standard's names, each
/// returning a bool with the standard's readings of the empty set: the empty set is a subset of
/// every interval, interior to every interval, disjoint from every interval, and equal to the empty
/// set only (milestone2.md, "Comparisons" and "IEEE 1788"; Tables 4.5 and 4.6 of the standard). In
/// a namespace of their own because two of the names are also those of Kairn's three-valued
/// comparisons, which answer another question: kairn::equal(X, Y) is yes when X and Y are the same
/// point, kairn::ieee1788::equal(X, Y) true when they have the same members. Each is one kernel,
/// exact, on intervals of one and of two limbs; none rounds. Balls have none of these:
/// Ball::contains, the three-valued comparisons and the conversion to an interval answer for them.
/// The relations of the full standard IEEE Std 1788-2015 that the simplified one does not require
/// (less, precedes, strict_less, strict_precedes) are not provided.
namespace ieee1788 {

/// The relation equal: X and Y have the same members, x_l = y_l and x_u = y_u on the stored bounds
/// (kernel interval_rel_equal_1 or interval_rel_equal_2). Proved, in the IEEE model, for canonical
/// intervals: exact; two empty sets are equal, and the empty set is equal to nothing else. Does not
/// round (comparisons): not preceded by the debug build's check of the rounding mode (config.hpp).
/// constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::rel_equal>
KAIRN_FORCEINLINE constexpr bool equal(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::rel_equal(x, y);
}
/// The relation subset: every member of X is a member of Y, y_l <= x_l and x_u <= y_u on the
/// stored bounds (kernel interval_subset_1 or interval_subset_2), the answer of Y.contains(X).
/// Exact; the empty set is a subset of every interval. Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::subset>
KAIRN_FORCEINLINE constexpr bool subset(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::rel_subset(x, y);
}
/// The relation interior: every member of X has a neighbourhood, an open interval around it, made
/// of members of Y (kernel interval_rel_interior_1 or interval_rel_interior_2): y_l < x_l, or both
/// are -inf, and x_u < y_u, or both are +inf, an infinite bound being inside an equal infinite
/// bound (the rule of the standard's Table 4.5). Exact; the empty set is interior to every
/// interval, and no nonempty interval to the empty set. Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::rel_interior>
KAIRN_FORCEINLINE constexpr bool interior(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::rel_interior(x, y);
}
/// The relation disjoint: no real number is a member of both (kernel interval_rel_disjoint_1 or
/// interval_rel_disjoint_2): an operand is empty, or x_u < y_l, or y_u < x_l. Exact; for nonempty
/// operands, the no of the three-valued kairn::equal. Does not round. constexpr.
template <class T, int K>
    requires detail::proof_checked<typename detail::interval_kernels<T, K>::rel_disjoint>
KAIRN_FORCEINLINE constexpr bool disjoint(const Interval<T, K>& x, const Interval<T, K>& y) noexcept {
    return detail::rel_disjoint(x, y);
}
/// equal(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_interval_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto equal(const X& x, const Y& y) noexcept
    -> decltype(detail::rel_equal(detail::unmark(x), detail::unmark(y))) {
    return detail::rel_equal(detail::unmark(x), detail::unmark(y));
}
/// subset(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_interval_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto subset(const X& x, const Y& y) noexcept
    -> decltype(detail::rel_subset(detail::unmark(x), detail::unmark(y))) {
    return detail::rel_subset(detail::unmark(x), detail::unmark(y));
}
/// interior(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_interval_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto interior(const X& x, const Y& y) noexcept
    -> decltype(detail::rel_interior(detail::unmark(x), detail::unmark(y))) {
    return detail::rel_interior(detail::unmark(x), detail::unmark(y));
}
/// disjoint(X, Y) with a marked operand.
template <class X, class Y>
    requires detail::marked_interval_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto disjoint(const X& x, const Y& y) noexcept
    -> decltype(detail::rel_disjoint(detail::unmark(x), detail::unmark(y))) {
    return detail::rel_disjoint(detail::unmark(x), detail::unmark(y));
}

}  // namespace ieee1788
}  // namespace kairn
KAIRN_GEN_POP_WARNINGS

// The definitions of the operations that round (config.hpp, KAIRN_ENCLOSURE_CODE): here, inline
// or outlined; or, external, in the one translation unit that includes kairn/definitions.hpp, and
// here the declarations of their instances, so that no translation unit compiles one of its own.
#if KAIRN_ENCLOSURE_CODE == KAIRN_ENCLOSURE_CODE_EXTERNAL
KAIRN_GEN_PUSH_WARNINGS
namespace kairn::detail {
KAIRN_DETAIL_ENCLOSURE_BEGIN
KAIRN_DETAIL_INTERVAL_INSTANCES(extern, double)
KAIRN_DETAIL_INTERVAL_INSTANCES(extern, float)
KAIRN_DETAIL_ENCLOSURE_END
}  // namespace kairn::detail
KAIRN_GEN_POP_WARNINGS
#else
#include "interval_operations.hpp"
#endif
