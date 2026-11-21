/// @file
/// Ball<T, k>: the set of reals within a radius of a center, with a k-limb center and a radius of
/// type T (docs/developer/design/phase0/operations.md, "Ball"; the kernels are in
/// docs/developer/design/milestone1.md, "Ball kernels").
///
/// Each operation forwards to one generated kernel: the full Ball kernels, each a finite core
/// followed by the fix-up of the special states (the empty set, the whole line), the scaling by a
/// power of two of ldexp and half (two or three calls of it when 2^n is not a number of T), the
/// constructor kernels ball_make_1 and ball_make_2 (from a center and a radius, or from a constant
/// of kairn::rational), and for the sign predicates of two limbs the comparisons lt_1_2, lt_2_1
/// and eq_2_1. The functions of the interface that Ball shares with Interval
/// (docs/developer/design/milestone2.md, "One enclosure interface") call the kernels of that
/// section: the bounds of a ball as numbers of T (ball_lower_as_k, ball_upper_as_k), the ball of
/// one limb of an interval (interval_to_ball_1), the ball of two limbs from an interval of two T
/// (ball_from_interval_2), and the narrowing of a ball of two limbs to one (ball_narrow_2_1).
/// Like every operation, each needs the kairn::unverified marker while gen/claims.json does not
/// mark its kernel proved.
///
/// This header includes kairn/interval.hpp at its end, so that Interval and the conversions
/// between the two types are there whichever of the two headers a program includes.
#pragma once

#include "expansion.hpp"
#include "rational.hpp"  // kairn::Constant, from which a Ball can be made

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

namespace detail {

// The kernels of the Ball operations, by number of limbs of the center.
template <class T, int K>
struct ball_kernels;
template <class T>
struct ball_kernels<T, 1> {
    using add = gen::bounds::ball_add_1_full<T>;
    using sub = gen::bounds::ball_sub_1_full<T>;
    using mul = gen::bounds::ball_mul_1_full<T>;
    using scale = gen::bounds::ball_scale_1_full<T>;
    using scale_pow2 = gen::bounds::ball_mul_pow2_1_full<T>;
    using neg = gen::bounds::ball_neg_1<T>;
    using make = gen::bounds::ball_make_1<T>;
    using lower_as = gen::bounds::ball_lower_as_1<T>;
    using upper_as = gen::bounds::ball_upper_as_1<T>;
};
template <class T>
struct ball_kernels<T, 2> {
    using add = gen::bounds::ball_add_2_full<T>;
    using sub = gen::bounds::ball_sub_2_full<T>;
    using mul = gen::bounds::ball_mul_2_full<T>;
    using scale = gen::bounds::ball_scale_2_full<T>;
    using scale_pow2 = gen::bounds::ball_mul_pow2_2_full<T>;
    using neg = gen::bounds::ball_neg_2<T>;
    using make = gen::bounds::ball_make_2<T>;
    using lower_as = gen::bounds::ball_lower_as_2<T>;
    using upper_as = gen::bounds::ball_upper_as_2<T>;
};

/// Whether the kernel that makes a ball from a center is proved: ball_make_1 or ball_make_2.
template <class T, int K>
concept make_proved = proof_checked<typename ball_kernels<T, K>::make>;
/// Whether the kernels that build the point ball of a T are proved: ball_make_1, or make_2 and
/// ball_make_2.
template <class T, int K>
concept point_proved = make_proved<T, K> && (K == 1 || proof_checked<gen::bounds::make_2<T>>);

/// The tag of the constructor of Ball that takes a kernel's result as it is.
struct kernel_result_t {
    explicit kernel_result_t() = default;
};
inline constexpr kernel_result_t kernel_result{};

// Whether a ball is canonical: a finite ball (finite center, canonical for two limbs; finite
// radius, r >= 0), the whole line (center 0, radius +inf), or the empty set (every limb a NaN).
// Comparisons are written b > a and b >= a: see detail::canonical.
template <class T, int K>
KAIRN_FORCEINLINE constexpr bool canonical_ball(const Expansion<T, K>& c, T r) noexcept {
    constexpr T inf = std::numeric_limits<T>::infinity();
    bool nan = true, zero = true;
    for (int i = 0; i < K; ++i) {
        nan = nan && c.limb[i] != c.limb[i];
        zero = zero && c.limb[i] == 0;
    }
    if (r != r) return nan;
    if (r == inf) return zero;
    if (!(finite(r) && r >= 0)) return false;
    if constexpr (K == 1) {
        return finite(c.limb[0]);
    } else {
        return finite(c.limb[0]) && canonical(c);
    }
}

// A ball from a canonical center and a radius (kernel ball_make_1 or ball_make_2), without the
// constraint, for the constructors and the marked forms. Under KAIRN_CHECKS the environment is
// checked, then a center of two limbs that is not canonical and a negative radius are reported:
// the latter as almost surely a bug, though the kernel gives it a meaning (the empty set). With a
// center of one limb the constructor does not round but in its guards, whose values are the same
// under every rounding mode, and nothing it checks rounds: the rounding mode is not checked.
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> make_ball(const Expansion<T, 1>& c, std::type_identity_t<T> r) noexcept;
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> make_ball(const Expansion<T, 2>& c, std::type_identity_t<T> r) noexcept;
// The constructor kernel alone, without the checks.
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> make_ball_kernel(const Expansion<T, 2>& c, std::type_identity_t<T> r) noexcept;
// The point ball of a T. For two limbs, the center that make_2 returns is canonical, by the
// kernel's proof, and the radius is zero: there is no operand to check, and nothing rounds but the
// guards of a and of the radius, so only the environment without the rounding mode is checked.
template <class T, int K>
KAIRN_FORCEINLINE constexpr Ball<T, K> make_point(std::type_identity_t<T> a) noexcept {
    if constexpr (K == 1) {
        return make_ball(Expansion<T, 1>(a), T(0));
    } else {
        check_environment_except_rounding();
        return make_ball_kernel(make<T>(a), T(0));
    }
}

// The checks of KAIRN_CHECKS, once per operand: the environment, then a canonical ball, which is
// not checked when the environment is not the default one and KAIRN_ENVIRONMENT_FAILURE returned
// (check_environment).
template <class T, int K>
KAIRN_FORCEINLINE constexpr void check_ball([[maybe_unused]] const Ball<T, K>& x) noexcept {
#if KAIRN_CHECKS
    if (check_environment() && !canonical_ball(x.center(), x.radius()))
        fail("a ball", "is not canonical (a finite ball with a canonical center and r >= 0, the whole line or the "
                       "empty set), so no guarantee applies to the result");
#endif
}
// The same for a function that does not round (the negation): the environment without the
// rounding mode; then a canonical ball, which for two limbs is tested only when the rounding mode
// is to nearest, since the test of a canonical center rounds (detail::check_exact).
template <class T, int K>
KAIRN_FORCEINLINE constexpr void check_ball_exact([[maybe_unused]] const Ball<T, K>& x) noexcept {
#if KAIRN_CHECKS
    if (check_environment_except_rounding() && (K == 1 || rounding_to_nearest()) &&
        !canonical_ball(x.center(), x.radius()))
        fail("a ball", "is not canonical (a finite ball with a canonical center and r >= 0, the whole line or the "
                       "empty set), so no guarantee applies to the result");
#endif
}

// The functions of the interface that Ball shares with Interval (milestone2.md, "One enclosure
// interface"), without their markers and constraints: one kernel each, inline and constexpr in
// every setting of KAIRN_ENCLOSURE_CODE, as the constructors are. Each rounds, so each checks the
// environment, the rounding mode included, then a canonical ball: the bounds of a ball as numbers
// of T compute under rounding to nearest what rounding down or up gives, and the narrowing of two
// limbs to one widens the radius by radd. The ball from an interval of two T guards the bounds
// (rule R3) and halves them; it accepts any two values of T.
template <class T, int K>
KAIRN_FORCEINLINE constexpr T ball_lower_as(const Ball<T, K>& x) noexcept {
    check_ball(x);
    T l = T(0);
    if constexpr (K == 1) {
        gen::ball_lower_as_1(x.center().limb[0], x.radius(), l);
    } else {
        gen::ball_lower_as_2(x.center().limb[0], x.center().limb[1], x.radius(), l);
    }
    return l;
}
template <class T, int K>
KAIRN_FORCEINLINE constexpr T ball_upper_as(const Ball<T, K>& x) noexcept {
    check_ball(x);
    T h = T(0);
    if constexpr (K == 1) {
        gen::ball_upper_as_1(x.center().limb[0], x.radius(), h);
    } else {
        gen::ball_upper_as_2(x.center().limb[0], x.center().limb[1], x.radius(), h);
    }
    return h;
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> narrow(const Ball<T, 2>& x) noexcept {
    check_ball(x);
    T c = T(0), r = T(0);
    gen::ball_narrow_2_1(x.center().limb[0], x.center().limb[1], x.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> ball_from_interval(std::type_identity_t<T> lo, std::type_identity_t<T> hi) noexcept {
    check_environment();
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_from_interval_2(lo, hi, c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
// The ball of one limb of an interval of one limb (kernel interval_to_ball_1), after the check of a
// canonical interval: defined in interval.hpp, with the other conversions.
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> to_ball(const Interval<T, 1>& x) noexcept;

// The operations that round, without their markers and constraints: one kernel each. Where their
// code is depends on KAIRN_ENCLOSURE_CODE (config.hpp): declared here, defined in
// ball_operations.hpp, which the end of this header includes unless the setting is
// KAIRN_ENCLOSURE_CODE_EXTERNAL, and then kairn/definitions.hpp, in the one translation unit of the
// program that defines them. Not constexpr: the radius of each but scale_pow2 is computed with
// fused operations, and none can be evaluated at compile time when its definition is in another
// translation unit (KAIRN_ENCLOSURE_CODE_EXTERNAL). scale_pow2 is the scaling by a power of two of
// T, c > 0, that ldexp and half call (kernel ball_mul_pow2_1_full or ball_mul_pow2_2_full).
KAIRN_DETAIL_ENCLOSURE_BEGIN
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> add(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> sub(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> mul(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> mul(const Ball<T, 1>& x, std::type_identity_t<T> a) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> add(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> sub(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> mul(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> mul(const Ball<T, 2>& x, std::type_identity_t<T> a) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> scale_pow2(const Ball<T, 1>& x, std::type_identity_t<T> c) noexcept;
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> scale_pow2(const Ball<T, 2>& x, std::type_identity_t<T> c) noexcept;
KAIRN_DETAIL_ENCLOSURE_END

// The instances of those operations that KAIRN_ENCLOSURE_CODE_EXTERNAL leaves to
// kairn/definitions.hpp: for the limb type T, with PREFIX extern for their declarations and
// nothing for their definitions.
#define KAIRN_DETAIL_BALL_INSTANCES(PREFIX, T)                                                     \
    PREFIX template Ball<T, 1> add<T>(const Ball<T, 1>&, const Ball<T, 1>&) noexcept;              \
    PREFIX template Ball<T, 1> sub<T>(const Ball<T, 1>&, const Ball<T, 1>&) noexcept;              \
    PREFIX template Ball<T, 1> mul<T>(const Ball<T, 1>&, const Ball<T, 1>&) noexcept;              \
    PREFIX template Ball<T, 1> mul<T>(const Ball<T, 1>&, std::type_identity_t<T>) noexcept;        \
    PREFIX template Ball<T, 2> add<T>(const Ball<T, 2>&, const Ball<T, 2>&) noexcept;              \
    PREFIX template Ball<T, 2> sub<T>(const Ball<T, 2>&, const Ball<T, 2>&) noexcept;              \
    PREFIX template Ball<T, 2> mul<T>(const Ball<T, 2>&, const Ball<T, 2>&) noexcept;              \
    PREFIX template Ball<T, 2> mul<T>(const Ball<T, 2>&, std::type_identity_t<T>) noexcept;        \
    PREFIX template Ball<T, 1> scale_pow2<T>(const Ball<T, 1>&, std::type_identity_t<T>) noexcept; \
    PREFIX template Ball<T, 2> scale_pow2<T>(const Ball<T, 2>&, std::type_identity_t<T>) noexcept;

// The negation, a few changes of sign, stays inline in every setting, and constexpr. It does not
// round: the rounding mode is not checked (check_ball_exact).
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> neg(const Ball<T, 1>& x) noexcept {
    check_ball_exact(x);
    T c = T(0), r = T(0);
    gen::ball_neg_1(x.center().limb[0], x.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> neg(const Ball<T, 2>& x) noexcept {
    check_ball_exact(x);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_neg_2(x.center().limb[0], x.center().limb[1], x.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> mul(std::type_identity_t<T> a, const Ball<T, K>& x) noexcept {
    return mul(x, a);
}

// X 2^n through scale_pow2, as detail::ldexp_steps does for a number (expansion.hpp): when 2^n is
// not a number of T, two or three scalings by powers of two of T. For a ball the composition needs
// no argument of its own (milestone2.md, "Scaling a ball by a power of two"): each step returns a
// canonical ball that contains c times every member of its operand, so the last contains 2^n times
// every member of X; and each step is exact when nothing it scales underflows, so the whole is
// exact when every limb of the center of 2^n X and its radius is zero or above the smallest normal
// number N in magnitude (the steps up only make values larger, and a nonzero value of T times
// 2^pow2_max is above N; of the two steps down, the first keeps every value above the final one).
// What is argued and not machine-checked is the clamp of
// n, as for a number: above pow2_max + 1 - pow2_min (2098 for double), each step is exact until
// one overflows, so any ball but the point 0 becomes the whole line, which also contains X 2^n for
// the larger n, and the point 0 stays the point 0; below pow2_min - pow2_max - 2 (-2099), every
// member of X 2^n is below eta/4 in magnitude, and the result for the clamped n is the point 0 for
// the point 0 and otherwise a ball of center 0 and radius at least 2 eta: the second step scales
// values below 1/2 by eta, which rounds them to zero and steps the radius twice from zero.
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> ldexp(const Ball<T, K>& x, int n) noexcept {
    constexpr int lo = pow2_min<T>, hi = pow2_max<T>;
    constexpr int up = hi + 1 - lo, down = lo - hi - 2;
    if (n > up) n = up;
    if (down > n) n = down;
    Ball<T, K> z = x;
    if (lo > n) {
        z = detail::scale_pow2(z, pow2<T>(n - lo));
        n = lo;
    }
    while (n > hi) {
        z = detail::scale_pow2(z, pow2<T>(hi));
        n -= hi;
    }
    return detail::scale_pow2(z, pow2<T>(n));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> half(const Ball<T, K>& x) noexcept {
    return detail::scale_pow2(x, T(0.5));
}

// A point operand, a T or an Expansion of as many limbs, is the ball of radius zero that its
// constructor builds (the constructor kernel guards what it is given), and the operation is then
// that of two balls: no Ball kernel takes a point. A one-limb center times a ball of one limb is
// the scaling, which is a kernel of its own and gives a tighter radius.
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(const Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return add(x, make_point<T, K>(a));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(std::type_identity_t<T> a, const Ball<T, K>& y) noexcept {
    return add(make_point<T, K>(a), y);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(const Ball<T, K>& x, const Expansion<T, K>& c) noexcept {
    return add(x, make_ball(c, T(0)));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(const Expansion<T, K>& c, const Ball<T, K>& y) noexcept {
    return add(make_ball(c, T(0)), y);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(const Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return sub(x, make_point<T, K>(a));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(std::type_identity_t<T> a, const Ball<T, K>& y) noexcept {
    return sub(make_point<T, K>(a), y);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(const Ball<T, K>& x, const Expansion<T, K>& c) noexcept {
    return sub(x, make_ball(c, T(0)));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(const Expansion<T, K>& c, const Ball<T, K>& y) noexcept {
    return sub(make_ball(c, T(0)), y);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> mul(const Ball<T, 1>& x, const Expansion<T, 1>& c) noexcept {
    return mul(x, c.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> mul(const Expansion<T, 1>& c, const Ball<T, 1>& y) noexcept {
    return mul(y, c.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> mul(const Ball<T, 2>& x, const Expansion<T, 2>& c) noexcept {
    return mul(x, make_ball(c, T(0)));
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> mul(const Expansion<T, 2>& c, const Ball<T, 2>& y) noexcept {
    return mul(make_ball(c, T(0)), y);
}

}  // namespace detail

/// A ball with a center of K limbs of type T and a radius of type T; defined for K = 1 and
/// K = 2. A ball is in one of three states, each a set of real numbers:
/// - a finite ball, the set {t : |t - c| <= r}: a finite center c (canonical for two limbs) and a
///   finite radius r >= 0;
/// - the whole line, every real number: center 0 and radius +inf. It is what an operation returns
///   when it cannot bound its result: an operand or a scalar that is not finite, or a center or
///   radius that overflows; and what a ball made with a center that is not finite, or with a
///   radius that is +inf or a NaN, is;
/// - the empty set: every limb a NaN. It is what a ball made with a negative radius is, and what
///   every operation with an empty operand returns.
/// is_finite(), is_whole() and is_empty() say which; Ball::whole() and Ball::empty() make the
/// last two.
///
/// Each operation computes the center with the k-number operation of the same name, rounded to
/// nearest, and a radius that covers the operands' radii and that operation's own proved error
/// bound, evaluated with operations rounded to nearest and inflated once at the end
/// (milestone1.md, "The radius, second design"). It calls a full Ball kernel: that core and the
/// fix-up of the states. Proved, in Flocq's model of IEEE 754 with overflow, for canonical
/// operands (statements B1 to B4 of milestone1.md, "Ball kernels"): the result is canonical; it
/// is empty exactly when an operand is empty; if it is a finite ball, every operand is a finite
/// ball, every scalar finite, and the result contains x op y for every x in X and y in Y, with a
/// normalized center for two limbs. So in every case the result contains every x op y, the whole
/// line counting as containing everything. And the result of finite operands is a finite ball,
/// not the whole line, when no x op y is larger in magnitude than a quarter of the overflow
/// threshold of T (2^1022 for double, 2^126 for float): |cx op cy| + rx + ry for a sum or a
/// difference, (|cx| + rx) (|cy| + ry) for a product, (|cx| + rx) |a| for a scaling by a. For the
/// product of balls with one-limb centers the proved bound is a sixteenth of that threshold.
///
/// A point operand (a T, or an Expansion of K limbs) is the ball of radius zero its constructor
/// makes, and the operation is then the operation of two balls; times a ball, a T (and, for one
/// limb, a one-limb number) is the scaling, a kernel of its own.
template <class T, int K>
class Ball {
    static_assert(detail::limb<T>, "Ball<T, k>: the limb type T is float or double");
    static_assert(K == 1 || K == 2, "Ball<T, k>: k is 1 or 2");

    Expansion<T, K> c_{};
    T r_ = T(0);

public:
    /// The point 0: center 0, radius 0.
    constexpr Ball() noexcept = default;
    /// The point a: center a (exactly, up to the sign of a zero), radius 0 (kernels ball_make_1 or
    /// ball_make_2, with a two-limb center made by make_2 first). An infinite or NaN a gives the
    /// whole line.
    /// Its only rounded operations are the guards, a + 0 and 0 + 0, whose values are a and 0 under
    /// every rounding mode (only the sign of a zero depends on the mode): not preceded by the debug
    /// build's check of the rounding mode (config.hpp).
    constexpr Ball(T a) noexcept
        requires detail::point_proved<T, K>
        : Ball(detail::make_point<T, K>(a)) {}
    /// The same with a marked operand: see kairn::Unverified.
    explicit constexpr Ball(Unverified<T> a) noexcept : Ball(detail::make_point<T, K>(a.value)) {}
    /// The point c: center c, radius 0 (kernel ball_make_1 or ball_make_2). A c that is not finite
    /// gives the whole line. Checked as the constructor below, with r = 0.
    constexpr Ball(const Expansion<T, K>& c) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::make>
        : Ball(detail::make_ball(c, T(0))) {}
    /// The same with a marked operand.
    explicit constexpr Ball(const Unverified<Expansion<T, K>>& c) noexcept : Ball(detail::make_ball(c.value, T(0))) {}
    /// The ball of center c and radius r (kernel ball_make_1 or ball_make_2), each guarded. For a
    /// canonical c: the empty set when r is negative (-inf included); otherwise the whole line
    /// when c is not finite or r is +inf or a NaN (a NaN says that something failed upstream, and
    /// the whole line is the answer that is always true); otherwise center c and radius r,
    /// exactly. So Ball(X.center(), X.radius()) of an empty X is the whole line, not X. When
    /// KAIRN_CHECKS is 1, the environment is checked as for an operation (config.hpp), then c
    /// must be canonical and a negative r is reported (it is almost surely a mistake; write
    /// Ball::empty() for the empty set); the constructors of a point above check the same.
    /// For one limb, the only rounded operations are the guards, c + 0 and r + 0, whose values are
    /// c and r under every rounding mode (only the sign of a zero depends on the mode), and the
    /// rounding mode is not checked (config.hpp); the radius is checked under every mode. For two
    /// limbs the test of a canonical center rounds (c0 + c1 == c0), so the rounding mode is.
    constexpr Ball(const Expansion<T, K>& c, T r) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::make>
        : Ball(detail::make_ball(c, r)) {}
    /// The same with a marked center.
    constexpr Ball(const Unverified<Expansion<T, K>>& c, T r) noexcept : Ball(detail::make_ball(c.value, r)) {}
    /// The ball of a constant from a fraction, q = kairn::rational<Expansion<T, K>>(num, den) or
    /// kairn::integer: center q.value and radius q.error, which contains num/den (kernel ball_make_1
    /// or ball_make_2, as Ball(q.value, q.error), with the same checks). Explicit: the error becomes
    /// a radius. Until Kairn has a division, X * Ball(kairn::rational<Expansion<T, K>>(1, s)) is how
    /// to multiply a ball by 1/s for an integer s and keep an enclosure.
    ///
    /// q.error is the smallest number of T at least |q.value - num/den|, so for den != 0 the ball
    /// is finite, of radius zero exactly when q.exact. A q whose value is not finite gives what the
    /// constructor kernel gives such a center: for den = 0 at run time (value NaN, error +inf) the
    /// whole line. Usable in constant evaluation (kairn::rational is, for den != 0). For one limb it
    /// does not round, as Ball(c, r); for two the test of a canonical center does, when
    /// KAIRN_CHECKS is 1, and the rounding mode is checked (config.hpp).
    explicit constexpr Ball(const Constant<Expansion<T, K>>& q) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::make>
        : Ball(detail::make_ball(q.value, q.error)) {}
    /// Internal: a kernel's center and radius, as they are.
    constexpr Ball(detail::kernel_result_t, const Expansion<T, K>& c, T r) noexcept : c_(c), r_(r) {}

    /// The empty set: every limb a NaN.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    [[nodiscard]] static constexpr Ball empty() noexcept {
        constexpr T nan = std::numeric_limits<T>::quiet_NaN();
        Expansion<T, K> c;
        for (int i = 0; i < K; ++i) c.limb[i] = nan;
        return Ball(detail::kernel_result, c, nan);
    }
    /// The whole line: center 0, radius +inf.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    [[nodiscard]] static constexpr Ball whole() noexcept {
        return Ball(detail::kernel_result, Expansion<T, K>(), std::numeric_limits<T>::infinity());
    }

    /// The center: of a finite ball, the center; 0 for the whole line; NaN limbs for the empty set.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr const Expansion<T, K>& center() const noexcept { return c_; }
    /// The radius: of a finite ball, a bound on the distance of every point of the set to the
    /// center; +inf for the whole line; a NaN for the empty set.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr T radius() const noexcept { return r_; }
    /// Whether this is a finite ball (for a canonical ball: its radius is finite).
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr bool is_finite() const noexcept { return std::numeric_limits<T>::infinity() > r_; }
    /// Whether this is the whole line (radius +inf).
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr bool is_whole() const noexcept { return r_ == std::numeric_limits<T>::infinity(); }
    /// Whether this is the empty set (radius NaN).
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr bool is_empty() const noexcept { return r_ != r_; }

    /// Whether every member is positive: for a finite ball, c - r > 0, decided exactly as r < c, a
    /// comparison of the radius with the center (for two limbs, kernel lt_1_2; for one, the
    /// comparison of T). False for the empty set (a query about nothing answers no: test
    /// is_empty() first) and for the whole line (docs/developer/design/milestone2.md, "One
    /// enclosure interface").
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr bool certainly_positive() const noexcept
        requires(K == 1 || detail::proof_checked<gen::bounds::lt_1_2<T>>)
    {
        detail::check_ball_exact(*this);
        if constexpr (K == 1) {
            return c_.limb[0] > r_;
        } else {
            bool m = false;
            gen::lt_1_2(r_, c_.limb[0], c_.limb[1], m);
            return m;
        }
    }
    /// Whether every member is negative: for a finite ball, c + r < 0, decided exactly as c < -r, a
    /// comparison of the center with the radius (for two limbs, kernel lt_2_1; for one, the
    /// comparison of T). False for the empty set and for the whole line.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr bool certainly_negative() const noexcept
        requires(K == 1 || detail::proof_checked<gen::bounds::lt_2_1<T>>)
    {
        detail::check_ball_exact(*this);
        if constexpr (K == 1) {
            return -r_ > c_.limb[0];
        } else {
            bool m = false;
            gen::lt_2_1(c_.limb[0], c_.limb[1], -r_, m);
            return m;
        }
    }
    /// Whether the ball is the point 0: center 0 and radius 0, exactly (for two limbs, kernel
    /// eq_2_1 on the center and 0; for one, the comparison of T). False for the empty set and for
    /// the whole line.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr bool certainly_zero() const noexcept
        requires(K == 1 || detail::proof_checked<gen::bounds::eq_2_1<T>>)
    {
        detail::check_ball_exact(*this);
        bool m = false;
        if constexpr (K == 1) {
            m = c_.limb[0] == 0;
        } else {
            gen::eq_2_1(c_.limb[0], c_.limb[1], T(0), m);
        }
        return m && r_ == 0;
    }

    // The interface that Ball shares with Interval (docs/developer/design/milestone2.md, "One
    // enclosure interface"). Not here yet, their kernels being still to come: lower() and upper()
    // of a ball of two limbs (ball_to_interval_2), the conversion of an Interval<T, 2>
    // (interval_to_ball_2), contains, hull, intersection, split, is_entire and the three-valued
    // comparisons.

    /// The midpoint: the center, for code written once for a Ball and an Interval; 0 for the whole
    /// line, NaN limbs for the empty set.
    /// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
    constexpr const Expansion<T, K>& midpoint() const noexcept { return c_; }
    /// A lower bound of the ball as a number of T, for U = T (kernel ball_lower_as_1 or
    /// ball_lower_as_2). Proved, in the IEEE model, for a canonical ball: +inf for the empty set;
    /// otherwise at most every member, so -inf for the whole line. For one limb and a finite ball,
    /// exactly RD(c - r), the largest number of T not above c - r, in the format with overflow (-inf
    /// below -Omega). For two limbs, the center rounded down to T, minus the radius, rounded down:
    /// when the center, the radius and the result are finite, |l - (c - r)| <= 5 u (|c| + r) + 3 eta;
    /// no number of steps of T from RD(c - r) is claimed, since the rounding of the center moves the
    /// bound by up to a gap of T at c, which is many gaps at c - r when r is close to |c|.
    /// Rounds (it computes under rounding to nearest what rounding down would give): preceded, when
    /// KAIRN_CHECKS is 1, by the check of the environment, the rounding mode included, and of a
    /// canonical ball (config.hpp). constexpr. A U other than T needs conversions between limb types,
    /// which Kairn does not have yet (milestone2.md, question 16).
    template <class U>
        requires(std::is_same_v<U, T> && detail::proof_checked<typename detail::ball_kernels<T, K>::lower_as>)
    constexpr U lower_as() const noexcept {
        return detail::ball_lower_as(*this);
    }
    /// An upper bound of the ball as a number of T, for U = T (kernel ball_upper_as_1 or
    /// ball_upper_as_2). Proved, in the IEEE model, for a canonical ball: -inf for the empty set;
    /// otherwise at least every member, so +inf for the whole line. For one limb and a finite ball,
    /// exactly RU(c + r), the smallest number of T not below c + r, in the format with overflow (+inf
    /// above Omega). For two limbs, the center rounded up to T, plus the radius, rounded up: when the
    /// center, the radius and the result are finite, |h - (c + r)| <= 5 u (|c| + r) + 3 eta; no
    /// number of steps of T from RU(c + r) is claimed. Rounds, and is checked, as lower_as;
    /// constexpr.
    template <class U>
        requires(std::is_same_v<U, T> && detail::proof_checked<typename detail::ball_kernels<T, K>::upper_as>)
    constexpr U upper_as() const noexcept {
        return detail::ball_upper_as(*this);
    }
    /// The lower bound of a ball of one limb as a number of one limb (kernel ball_lower_as_1): the
    /// value of lower_as<T>(), RD(c - r) for a finite ball, +inf for the empty set, -inf for the
    /// whole line; that is also the lower bound of Interval<T, 1>(X), the smallest interval of T that
    /// contains the ball. Rounds, and is checked, as lower_as; constexpr.
    constexpr Expansion<T, 1> lower() const noexcept
        requires(K == 1 && detail::proof_checked<gen::bounds::ball_lower_as_1<T>>)
    {
        return Expansion<T, 1>(detail::ball_lower_as(*this));
    }
    /// The upper bound of a ball of one limb as a number of one limb (kernel ball_upper_as_1): the
    /// value of upper_as<T>(), RU(c + r) for a finite ball, -inf for the empty set, +inf for the
    /// whole line; that is also the upper bound of Interval<T, 1>(X). Rounds, and is checked, as
    /// lower_as; constexpr.
    constexpr Expansion<T, 1> upper() const noexcept
        requires(K == 1 && detail::proof_checked<gen::bounds::ball_upper_as_1<T>>)
    {
        return Expansion<T, 1>(detail::ball_upper_as(*this));
    }

    /// The ball of one limb that contains the interval X (kernel interval_to_ball_1), its center a
    /// midpoint of X and its radius the smallest for that center (the listing is that of
    /// X.midpoint() and X.radius()), but for an unbounded interval, which becomes the whole line,
    /// center 0 and radius +inf (a ball cannot be a half-line). Proved, in the IEEE model, for a
    /// canonical interval: the ball is canonical, and empty exactly when X is; for a
    /// bounded X = [l, h] it is a finite ball whose center c has l <= c <= h and
    /// |c - (l + h)/2| <= u |(l + h)/2| + eta, and whose radius is the smallest number of T for which
    /// [c - r, c + r] contains X, RU(max(c - l, h - c)). Explicit: the conversion widens the set.
    /// Rounds (sums and halvings): preceded, when KAIRN_CHECKS is 1, by the check of the environment,
    /// the rounding mode included, and of a canonical interval (config.hpp). constexpr. For two
    /// limbs not yet: its kernel, interval_to_ball_2, is still to come.
    explicit constexpr Ball(const Interval<T, K>& x) noexcept
        requires(K == 1 && detail::proof_checked<gen::bounds::interval_to_ball_1<T>>)
        : Ball(detail::to_ball(x)) {}
    /// The same with a marked operand: see kairn::Unverified.
    explicit constexpr Ball(const Unverified<Interval<T, K>>& x) noexcept
        requires(K == 1)
        : Ball(detail::to_ball(x.value)) {}
    /// The ball of two limbs whose center is the midpoint of [lo, hi], two values of T (kernel
    /// ball_from_interval_2), each guarded (rule R3): Ball<T, 2>::from_interval(lo, hi). Proved, in
    /// the IEEE model, for any two values of T: the ball is canonical; the whole line, center 0 and
    /// radius +inf, when a bound is a NaN, whatever the other (a NaN says that something failed
    /// upstream); when lo <= hi and both are finite, a finite ball that contains [lo, hi], and when
    /// moreover lo/2 and hi/2 are numbers of T (neither bound an odd multiple of eta below twice the
    /// smallest normal number) its center is (lo + hi)/2 exactly, the sum of the halves as two
    /// limbs, and its radius RU((hi - lo)/2), the smallest of T for that center; the whole line when
    /// lo <= hi, lo < +inf, hi > -inf and a bound is infinite (a ball cannot be a half-line); the
    /// empty set otherwise, that is for lo > hi, [+inf, +inf] and [-inf, -inf], as Interval(lo, hi).
    /// Rounds (halvings and a difference rounded up): preceded, when KAIRN_CHECKS is 1, by the check
    /// of the environment, the rounding mode included; every value of T is accepted. constexpr.
    static constexpr Ball from_interval(T lo, T hi) noexcept
        requires(K == 2 && detail::proof_checked<gen::bounds::ball_from_interval_2<T>>)
    {
        return detail::ball_from_interval<T>(lo, hi);
    }
    /// The same with a marked operand.
    static constexpr Ball from_interval(Unverified<T> lo, T hi) noexcept
        requires(K == 2)
    {
        return detail::ball_from_interval<T>(lo.value, hi);
    }
    /// A ball of one limb that contains the ball X of two limbs (kernel ball_narrow_2_1): the leading
    /// limb of the center, and the radius widened by the second limb, rounded up. Proved, in the
    /// IEEE model, for a canonical X (statements B1 to B4 of milestone1.md, "Ball kernels"): the
    /// result is canonical, empty exactly when X is, and if it is a finite ball then X is one and the
    /// result contains every member of X; so it contains X in every case, the whole line counting as
    /// containing everything. It is a finite ball when X is one and |c| + r is at most
    /// 2^(e_max - 2), a quarter of the overflow threshold (2^1022 for double, 2^126 for float).
    /// Explicit, as the narrowing of a number: the set grows. Rounds (radd): preceded, when
    /// KAIRN_CHECKS is 1, by the check of the environment, the rounding mode included, and of a
    /// canonical ball (config.hpp). constexpr.
    template <int J = 2>
        requires(K == 1 && J == 2 && detail::proof_checked<gen::bounds::ball_narrow_2_1<T>>)
    explicit constexpr Ball(const Ball<T, 2>& x) noexcept : Ball(detail::narrow(x)) {}
    /// The same with a marked operand.
    explicit constexpr Ball(const Unverified<Ball<T, 2>>& x) noexcept
        requires(K == 1)
        : Ball(detail::narrow(x.value)) {}
};

namespace detail {
// Under KAIRN_CHECKS the environment first, as for an operation, without the rounding mode for one
// limb, whose constructor does not round; then, for two limbs, the center, and the radius, which
// are not checked when the environment is not the default one and KAIRN_ENVIRONMENT_FAILURE
// returned (check_environment).
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> make_ball(const Expansion<T, 1>& c, std::type_identity_t<T> r) noexcept {
#if KAIRN_CHECKS
    if (check_environment_except_rounding() && 0 > r)
        fail("a ball", "has a negative radius (Ball::empty() is the empty set)");
#endif
    T cw = T(0), rw = T(0);
    gen::ball_make_1(c.limb[0], r, cw, rw);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(cw), rw);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> make_ball_kernel(const Expansion<T, 2>& c, std::type_identity_t<T> r) noexcept {
    Expansion<T, 2> cw;
    T rw = T(0);
    gen::ball_make_2(c.limb[0], c.limb[1], r, cw.limb[0], cw.limb[1], rw);
    return Ball<T, 2>(kernel_result, cw, rw);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> make_ball(const Expansion<T, 2>& c, std::type_identity_t<T> r) noexcept {
#if KAIRN_CHECKS
    if (check_environment()) {
        if (!canonical(c)) fail("a ball", "has a center that is not canonical");
        if (0 > r) fail("a ball", "has a negative radius (Ball::empty() is the empty set)");
    }
#endif
    return make_ball_kernel(c, r);
}
}  // namespace detail

/// The marked form of a Ball operand: see kairn::Unverified.
template <class T, int K>
struct Unverified<Ball<T, K>> {
    Ball<T, K> value;  ///< The operand.
};

/// Marks x as an operand of an operation whose proof is not checked yet; see kairn::Unverified.
template <class T, int K>
KAIRN_FORCEINLINE constexpr Unverified<Ball<T, K>> unverified(const Ball<T, K>& x) noexcept {
    return {x};
}

// The operators. As for Expansion, they are function templates, so that no operand converts: a
// point operand matches only the form written for it, gated on every kernel it calls.

/// X + Y (kernel ball_add_1_full or ball_add_2_full). Not usable in constant evaluation yet.
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add>
KAIRN_FORCEINLINE Ball<T, K> operator+(const Ball<T, K>& x, const Ball<T, K>& y) noexcept {
    return detail::add(x, y);
}
/// X + a: X plus the point a (kernel ball_add_1_full or ball_add_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add> && detail::point_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator+(const Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return detail::add(x, a);
}
/// a + X: the point a plus X (kernel ball_add_1_full or ball_add_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add> && detail::point_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator+(std::type_identity_t<T> a, const Ball<T, K>& x) noexcept {
    return detail::add(a, x);
}
/// X + c: X plus the point c (kernel ball_add_1_full or ball_add_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add> && detail::make_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator+(const Ball<T, K>& x, const Expansion<T, K>& c) noexcept {
    return detail::add(x, c);
}
/// c + X: the point c plus X (kernel ball_add_1_full or ball_add_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add> && detail::make_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator+(const Expansion<T, K>& c, const Ball<T, K>& x) noexcept {
    return detail::add(c, x);
}
/// X - Y (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub>
KAIRN_FORCEINLINE Ball<T, K> operator-(const Ball<T, K>& x, const Ball<T, K>& y) noexcept {
    return detail::sub(x, y);
}
/// X - a: X minus the point a (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub> && detail::point_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator-(const Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return detail::sub(x, a);
}
/// a - X: the point a minus X (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub> && detail::point_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator-(std::type_identity_t<T> a, const Ball<T, K>& x) noexcept {
    return detail::sub(a, x);
}
/// X - c: X minus the point c (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub> && detail::make_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator-(const Ball<T, K>& x, const Expansion<T, K>& c) noexcept {
    return detail::sub(x, c);
}
/// c - X: the point c minus X (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub> && detail::make_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K> operator-(const Expansion<T, K>& c, const Ball<T, K>& x) noexcept {
    return detail::sub(c, x);
}
/// X * Y (kernel ball_mul_1_full or ball_mul_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::mul>
KAIRN_FORCEINLINE Ball<T, K> operator*(const Ball<T, K>& x, const Ball<T, K>& y) noexcept {
    return detail::mul(x, y);
}
/// X a, the scaling by a T (kernel ball_scale_1_full or ball_scale_2_full). An infinite or NaN a
/// gives the whole line, or the empty set if X is empty.
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale>
KAIRN_FORCEINLINE Ball<T, K> operator*(const Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return detail::mul(x, a);
}
/// a X: as X a (kernel ball_scale_1_full or ball_scale_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale>
KAIRN_FORCEINLINE Ball<T, K> operator*(std::type_identity_t<T> a, const Ball<T, K>& x) noexcept {
    return detail::mul(a, x);
}
/// X c for a one-limb c: the scaling by its limb (kernel ball_scale_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::ball_scale_1_full<T>>
KAIRN_FORCEINLINE Ball<T, 1> operator*(const Ball<T, 1>& x, const Expansion<T, 1>& c) noexcept {
    return detail::mul(x, c);
}
/// c X for a one-limb c: the scaling by its limb (kernel ball_scale_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::ball_scale_1_full<T>>
KAIRN_FORCEINLINE Ball<T, 1> operator*(const Expansion<T, 1>& c, const Ball<T, 1>& x) noexcept {
    return detail::mul(c, x);
}
/// X c for a two-limb c: X times the point c (kernel ball_mul_2_full).
template <class T>
    requires detail::proof_checked<gen::bounds::ball_mul_2_full<T>> && detail::make_proved<T, 2>
KAIRN_FORCEINLINE Ball<T, 2> operator*(const Ball<T, 2>& x, const Expansion<T, 2>& c) noexcept {
    return detail::mul(x, c);
}
/// c X for a two-limb c: the point c times X (kernel ball_mul_2_full).
template <class T>
    requires detail::proof_checked<gen::bounds::ball_mul_2_full<T>> && detail::make_proved<T, 2>
KAIRN_FORCEINLINE Ball<T, 2> operator*(const Expansion<T, 2>& c, const Ball<T, 2>& x) noexcept {
    return detail::mul(c, x);
}
/// -X (kernel ball_neg_1 or ball_neg_2): exactly -X; the whole line and the empty set stay what
/// they are. No fix-up is needed.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::neg>
KAIRN_FORCEINLINE constexpr Ball<T, K> operator-(const Ball<T, K>& x) noexcept {
    return detail::neg(x);
}
/// X = X + Y (kernel ball_add_1_full or ball_add_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add>
KAIRN_FORCEINLINE Ball<T, K>& operator+=(Ball<T, K>& x, const Ball<T, K>& y) noexcept {
    return x = detail::add(x, y);
}
/// X = X + a (kernel ball_add_1_full or ball_add_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add> && detail::point_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K>& operator+=(Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return x = detail::add(x, a);
}
/// X = X + c (kernel ball_add_1_full or ball_add_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::add> && detail::make_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K>& operator+=(Ball<T, K>& x, const Expansion<T, K>& c) noexcept {
    return x = detail::add(x, c);
}
/// X = X - Y (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub>
KAIRN_FORCEINLINE Ball<T, K>& operator-=(Ball<T, K>& x, const Ball<T, K>& y) noexcept {
    return x = detail::sub(x, y);
}
/// X = X - a (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub> && detail::point_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K>& operator-=(Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return x = detail::sub(x, a);
}
/// X = X - c (kernel ball_sub_1_full or ball_sub_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub> && detail::make_proved<T, K>
KAIRN_FORCEINLINE Ball<T, K>& operator-=(Ball<T, K>& x, const Expansion<T, K>& c) noexcept {
    return x = detail::sub(x, c);
}
/// X = X * Y (kernel ball_mul_1_full or ball_mul_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::mul>
KAIRN_FORCEINLINE Ball<T, K>& operator*=(Ball<T, K>& x, const Ball<T, K>& y) noexcept {
    return x = detail::mul(x, y);
}
/// X = X a (kernel ball_scale_1_full or ball_scale_2_full).
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale>
KAIRN_FORCEINLINE Ball<T, K>& operator*=(Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return x = detail::mul(x, a);
}

/// X times 2^n, for every n (kernel ball_mul_pow2_1_full or ball_mul_pow2_2_full: the scaling of a
/// ball by a power of two c = 2^n, with the fix-up of the special states). Not usable in constant
/// evaluation yet, although the kernel is: like the other operations of a ball that round, its
/// code is where KAIRN_ENCLOSURE_CODE puts it, which can be another translation unit.
///
/// Exact when nothing underflows: when every limb of the center of 2^n X and its radius is zero or
/// above the smallest normal number N of T in magnitude (2^-1022 for double, 2^-126 for float), the
/// result is 2^n X itself, center 2^n c and radius 2^n r, and nothing is added; otherwise the
/// center loses at most eta per scaled limb and the radius is the second number of T after
/// 2^n r rounded to nearest, which covers it. Proved for each call of the kernel, in the IEEE model:
/// the result is canonical, it contains 2^n x for every x in X, it is the empty set exactly when X
/// is, the whole line when the scaled center or radius overflows, and a finite ball when
/// (|c| + r) 2^n <= 2^(e_max - 2). When 2^n is not a number of T (n above 1023 or below -1074 for
/// double) the kernel is called two or three times, as by ldexp of a number, and containment and
/// exactness of each call give those of the whole; that the steps may stop at n = +-2098 or so
/// (detail::ldexp) is argued, not machine-checked.
///
/// X * T(0.5) or X * 2.0 is the general scaling by a T (ball_scale_1_full, ball_scale_2_full),
/// whose radius also covers the rounding of a product that need not be exact, and so grows even
/// for a power of two; ldexp and half are for a power of two known as such, such as the halvings
/// of a subdivision, and keep the ball exact.
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale_pow2>
KAIRN_FORCEINLINE Ball<T, K> ldexp(const Ball<T, K>& x, int n) noexcept {
    return detail::ldexp(x, n);
}
/// X / 2 (kernel ball_mul_pow2_1_full or ball_mul_pow2_2_full, with c = 1/2): as ldexp(X, -1), one
/// call. Exact when every limb of the center of X / 2 and its radius is zero or above N in
/// magnitude: for double, when the last nonzero limb of the center of X is above 2^-1021 in
/// magnitude and the radius is zero or above 2^-1021. Not usable in constant evaluation yet.
template <class T, int K>
    requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale_pow2>
KAIRN_FORCEINLINE Ball<T, K> half(const Ball<T, K>& x) noexcept {
    return detail::half(x);
}

namespace detail {
template <class X, class Y>
concept marked_ball_pair = (marked<X> || marked<Y>) && (ball<X> || ball<Y>);
template <class X, class Y>
concept marked_ball_rhs = marked<Y> && !marked<X> && ball<X>;
}  // namespace detail

/// X + Y with a marked operand: a Ball and a Ball, an Expansion of as many limbs, or a T (a point
/// is a ball of radius zero).
template <class X, class Y>
    requires detail::marked_ball_pair<X, Y>
KAIRN_FORCEINLINE auto operator+(const X& x, const Y& y) noexcept
    -> decltype(detail::add(detail::unmark(x), detail::unmark(y))) {
    return detail::add(detail::unmark(x), detail::unmark(y));
}
/// X - Y with a marked operand.
template <class X, class Y>
    requires detail::marked_ball_pair<X, Y>
KAIRN_FORCEINLINE auto operator-(const X& x, const Y& y) noexcept
    -> decltype(detail::sub(detail::unmark(x), detail::unmark(y))) {
    return detail::sub(detail::unmark(x), detail::unmark(y));
}
/// X * Y with a marked operand; with a T operand, the scaling of the ball by that T.
template <class X, class Y>
    requires detail::marked_ball_pair<X, Y>
KAIRN_FORCEINLINE auto operator*(const X& x, const Y& y) noexcept
    -> decltype(detail::mul(detail::unmark(x), detail::unmark(y))) {
    return detail::mul(detail::unmark(x), detail::unmark(y));
}
/// -X with a marked operand.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class X>
    requires detail::marked<X> && detail::ball<X>
KAIRN_FORCEINLINE constexpr auto operator-(const X& x) noexcept -> decltype(detail::neg(detail::unmark(x))) {
    return detail::neg(detail::unmark(x));
}
/// X = X + Y with a marked right operand.
template <class X, class Y>
    requires detail::marked_ball_rhs<X, Y>
KAIRN_FORCEINLINE auto operator+=(X& x, const Y& y) noexcept -> decltype(x = detail::add(x, detail::unmark(y))) {
    return x = detail::add(x, detail::unmark(y));
}
/// X = X - Y with a marked right operand.
template <class X, class Y>
    requires detail::marked_ball_rhs<X, Y>
KAIRN_FORCEINLINE auto operator-=(X& x, const Y& y) noexcept -> decltype(x = detail::sub(x, detail::unmark(y))) {
    return x = detail::sub(x, detail::unmark(y));
}
/// X = X * Y with a marked right operand.
template <class X, class Y>
    requires detail::marked_ball_rhs<X, Y>
KAIRN_FORCEINLINE auto operator*=(X& x, const Y& y) noexcept -> decltype(x = detail::mul(x, detail::unmark(y))) {
    return x = detail::mul(x, detail::unmark(y));
}
/// X times 2^n with a marked operand.
template <class X>
    requires detail::marked<X> && detail::ball<X>
KAIRN_FORCEINLINE auto ldexp(const X& x, int n) noexcept -> decltype(detail::ldexp(detail::unmark(x), n)) {
    return detail::ldexp(detail::unmark(x), n);
}
/// X / 2 with a marked operand.
template <class X>
    requires detail::marked<X> && detail::ball<X>
KAIRN_FORCEINLINE auto half(const X& x) noexcept -> decltype(detail::half(detail::unmark(x))) {
    return detail::half(detail::unmark(x));
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
KAIRN_DETAIL_BALL_INSTANCES(extern, double)
KAIRN_DETAIL_BALL_INSTANCES(extern, float)
KAIRN_DETAIL_ENCLOSURE_END
}  // namespace kairn::detail
KAIRN_GEN_POP_WARNINGS
#else
#include "ball_operations.hpp"
#endif

// Interval<T, k> and the conversions between the two types (interval.hpp includes this header
// first, so the two are defined in this order whichever a program includes).
#include "interval.hpp"
