/// @file
/// Interval<T, k>: a set of real numbers given by two bounds, each a k-limb number of T, with the
/// empty set and unbounded intervals as ordinary values (docs/developer/design/milestone2.md,
/// "Interval kernels" and "One enclosure interface"; docs/developer/design/phase0/operations.md,
/// "Interval").
///
/// Each operation forwards to one generated kernel: the constructor kernels interval_make_1 and
/// interval_make_2, the negations, sums, differences and products interval_neg_k, interval_add_k,
/// interval_sub_k and interval_mul_k, the hull and the intersection interval_hull_k and
/// interval_intersection_k, for one limb the midpoint and radius interval_mid_rad_1 and the split
/// interval_split_1, the conversions interval_to_ball_1 (in ball.hpp) and ball_to_interval_1, and
/// for the bounds of two limbs as numbers of T the roundings to_down_2 and to_up_2. Like every
/// operation, each needs the kairn::unverified marker while gen/claims.json does not mark its kernel
/// proved. A constructor of two limbs from a T builds the two-limb number first (make_2), as
/// Ball<T, 2>(a) does; no other function composes kernels.
///
/// Not here yet, their kernels being still to come: every predicate and comparison (is_empty,
/// is_entire, contains, the signs, the three-valued comparisons, the relations of IEEE 1788), and
/// for two limbs the midpoint, the radius, the split and the conversions between Interval and Ball.
/// No operation mixes an interval with a number (X + a): no kernel takes one, and an interval of a
/// point is written Interval(a).
#pragma once

#include "ball.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

namespace detail {

// The kernel that stands for a function of an interval of two limbs whose kernel is still to come.
struct kernel_not_generated_yet {
    static constexpr bool proved = false;
};

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
    using mid_rad = kernel_not_generated_yet;       // interval_mid_rad_2
    using split = kernel_not_generated_yet;         // interval_split_2
    using from_ball = kernel_not_generated_yet;     // ball_to_interval_2
};

/// Whether the kernels that build the interval of a point of T are proved: interval_make_1, or
/// make_2 and interval_make_2.
template <class T, int K>
concept interval_point_proved =
    proof_checked<typename interval_kernels<T, K>::make> && (K == 1 || proof_checked<gen::bounds::make_2<T>>);

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
// The interval of one limb of a ball of one limb (kernel ball_to_interval_1).
template <class T>
KAIRN_FORCEINLINE constexpr Interval<T, 1> to_interval(const Ball<T, 1>& x) noexcept;

}  // namespace detail

/// What split() returns: two intervals whose union is the one split, the left one below the right
/// one, sharing the point at which it was split.
template <class X>
struct Split {
    X left;   ///< The part that holds the lower bound.
    X right;  ///< The part that holds the upper bound.
};

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
    /// The smallest interval of one limb that contains the ball X of one limb (kernel
    /// ball_to_interval_1): [RD(c - r), RU(c + r)], the roundings down and up in the format with
    /// overflow. Proved, in the IEEE model, for a canonical ball: the interval is canonical, empty
    /// exactly when X is, and contains every member of X; the whole line gives [-inf, +inf].
    /// Explicit: the conversion widens the set. Rounds (it computes under rounding to nearest what
    /// rounding down and up give): preceded, when KAIRN_CHECKS is 1, by the check of the
    /// environment, the rounding mode included, and of a canonical ball (config.hpp). constexpr. For
    /// two limbs not yet: its kernel, ball_to_interval_2, is still to come.
    explicit constexpr Interval(const Ball<T, K>& x) noexcept
        requires(K == 1 && detail::proof_checked<typename detail::interval_kernels<T, K>::from_ball>)
        : Interval(detail::to_interval(x)) {}
    /// The same with a marked operand.
    explicit constexpr Interval(const Unverified<Ball<T, K>>& x) noexcept
        requires(K == 1)
        : Interval(detail::to_interval(x.value)) {}
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

    /// The midpoint of an interval of one limb (kernel interval_mid_rad_1): the sum of the halves of
    /// the bounds, moved into the interval if a halving underflowed. Proved, in the IEEE model, for
    /// a canonical interval: for a bounded [l, h], a finite m with l <= m <= h and
    /// |m - (l + h)/2| <= u |(l + h)/2| + eta; 0 for the whole line; Omega, the largest finite number
    /// of T, for [l, +inf] with l finite, and -Omega for [-inf, h]; a NaN for the empty set. These
    /// are the values of mid in IEEE 1788, but for a bounded interval with a bound that is an odd
    /// multiple of eta, where the result is within eta and one rounding of the midpoint and need not
    /// be the midpoint rounded to nearest. Rounds (halvings and a sum): preceded, when KAIRN_CHECKS
    /// is 1, by the check of the environment, the rounding mode included, and of a canonical
    /// interval (config.hpp). constexpr. For two limbs not yet: its kernel, interval_mid_rad_2, is
    /// still to come.
    constexpr Expansion<T, 1> midpoint() const noexcept
        requires(K == 1 && detail::proof_checked<typename detail::interval_kernels<T, K>::mid_rad>)
    {
        T m = T(0), r = T(0);
        mid_rad(m, r);
        return Expansion<T, 1>(m);
    }
    /// The radius of an interval of one limb, for the midpoint that midpoint() returns (kernel
    /// interval_mid_rad_1). Proved, in the IEEE model, for a canonical interval: for a bounded
    /// [l, h], the smallest number r of T with [m - r, m + r] containing [l, h], RU(max(m - l, h - m));
    /// +inf for an unbounded interval; a NaN for the empty set, as rad in IEEE 1788. Rounds, and is
    /// checked, as midpoint(); constexpr. For two limbs not yet.
    constexpr T radius() const noexcept
        requires(K == 1 && detail::proof_checked<typename detail::interval_kernels<T, K>::mid_rad>)
    {
        T m = T(0), r = T(0);
        mid_rad(m, r);
        return r;
    }
    /// Two intervals of one limb whose union is this one, split at a point of it (kernel
    /// interval_split_1): left = [l, m] and right = [m, h]. Proved, in the IEEE model, for a
    /// canonical interval: both are canonical; both are empty for the empty set; otherwise neither
    /// is, left.lower() is l, right.upper() is h, and left.upper() equals right.lower(), a point of
    /// the interval. The point is the midpoint of the listing (interval_mid_rad_1), 0 for the whole
    /// line and Omega for [l, +inf]; that it is the midpoint is the listing's, not claimed. Rounds,
    /// and is checked, as midpoint(); constexpr. For two limbs not yet: its kernel, interval_split_2,
    /// is still to come.
    constexpr Split<Interval> split() const noexcept
        requires(K == 1 && detail::proof_checked<typename detail::interval_kernels<T, K>::split>)
    {
        detail::check_interval(*this);
        T al = T(0), au = T(0), bl = T(0), bu = T(0);
        gen::interval_split_1(lo_.limb[0], hi_.limb[0], al, au, bl, bu);
        return {Interval(detail::kernel_result, Expansion<T, 1>(al), Expansion<T, 1>(au)),
                Interval(detail::kernel_result, Expansion<T, 1>(bl), Expansion<T, 1>(bu))};
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
    // The midpoint and the radius (kernel interval_mid_rad_1).
    constexpr void mid_rad(T& m, T& r) const noexcept {
        detail::check_interval(*this);
        gen::interval_mid_rad_1(lo_.limb[0], hi_.limb[0], m, r);
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
KAIRN_FORCEINLINE constexpr Ball<T, 1> to_ball(const Interval<T, 1>& x) noexcept {
    check_interval(x);
    T c = T(0), r = T(0);
    gen::interval_to_ball_1(x.lower().limb[0], x.upper().limb[0], c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
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
