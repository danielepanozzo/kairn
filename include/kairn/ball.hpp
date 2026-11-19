/// @file
/// Ball<T, k>: the set of reals within a radius of a center, with a k-limb center and a radius of
/// type T (docs/developer/design/phase0/operations.md, "Ball"; the kernels are in
/// docs/developer/design/milestone1.md, "Ball kernels").
///
/// Each operation forwards to one generated kernel: the full Ball kernels, each a finite core
/// followed by the fix-up of the special states (the empty set, the whole line), and the
/// constructor kernels ball_make_1 and ball_make_2. Like every operation, each needs the
/// kairn::unverified marker while gen/claims.json does not mark its kernel proved.
#pragma once

#include "expansion.hpp"

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
    using neg = gen::bounds::ball_neg_1<T>;
    using make = gen::bounds::ball_make_1<T>;
};
template <class T>
struct ball_kernels<T, 2> {
    using add = gen::bounds::ball_add_2_full<T>;
    using sub = gen::bounds::ball_sub_2_full<T>;
    using mul = gen::bounds::ball_mul_2_full<T>;
    using scale = gen::bounds::ball_scale_2_full<T>;
    using neg = gen::bounds::ball_neg_2<T>;
    using make = gen::bounds::ball_make_2<T>;
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
// constraint, for the constructors and the marked forms. Under KAIRN_CHECKS a negative radius is
// reported, as almost surely a bug, though the kernel gives it a meaning (the empty set).
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> make_ball(const Expansion<T, 1>& c, std::type_identity_t<T> r) noexcept;
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> make_ball(const Expansion<T, 2>& c, std::type_identity_t<T> r) noexcept;
template <class T, int K>
KAIRN_FORCEINLINE constexpr Ball<T, K> make_point(std::type_identity_t<T> a) noexcept {
    if constexpr (K == 1) {
        return make_ball(Expansion<T, 1>(a), T(0));
    } else {
        return make_ball(make<T>(a), T(0));
    }
}

template <class T, int K>
KAIRN_FORCEINLINE constexpr void check_ball([[maybe_unused]] const Ball<T, K>& x) noexcept {
#if KAIRN_CHECKS
    check_environment();
    if (!canonical_ball(x.center(), x.radius()))
        fail("a ball", "is not canonical (a finite ball with a canonical center and r >= 0, the whole line or the "
                       "empty set), so no guarantee applies to the result");
#endif
}

// The operations, without their markers and constraints: one kernel each. Not constexpr except
// the negation: the radius of every other one is computed with fused operations.
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> add(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_add_1_full(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> sub(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_sub_1_full(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> mul(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_mul_1_full(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> mul(const Ball<T, 1>& x, std::type_identity_t<T> a) noexcept {
    check_ball(x);
    T c = T(0), r = T(0);
    // a is only multiplied (the center's product, abs(a) times the radius): no guard needed.
    gen::ball_scale_1_full(x.center().limb[0], x.radius(), a, c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> neg(const Ball<T, 1>& x) noexcept {
    check_ball(x);
    T c = T(0), r = T(0);
    gen::ball_neg_1(x.center().limb[0], x.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> add(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_add_2_full(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                         y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> sub(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_sub_2_full(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                         y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> mul(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_mul_2_full(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                         y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> mul(const Ball<T, 2>& x, std::type_identity_t<T> a) noexcept {
    check_ball(x);
    Expansion<T, 2> c;
    T r = T(0);
    // a is only multiplied (mul_2_1 on the center, abs(a) times the radius): no guard needed.
    gen::ball_scale_2_full(x.center().limb[0], x.center().limb[1], x.radius(), a, c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> neg(const Ball<T, 2>& x) noexcept {
    check_ball(x);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_neg_2(x.center().limb[0], x.center().limb[1], x.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> mul(std::type_identity_t<T> a, const Ball<T, K>& x) noexcept {
    return mul(x, a);
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
///   radius that overflows;
/// - the empty set: every limb a NaN. It is what a ball made with a NaN or negative radius is,
///   and what every operation with an empty operand returns.
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
    constexpr Ball(T a) noexcept
        requires detail::point_proved<T, K>
        : Ball(detail::make_point<T, K>(a)) {}
    /// The same with a marked operand: see kairn::Unverified.
    explicit constexpr Ball(Unverified<T> a) noexcept : Ball(detail::make_point<T, K>(a.value)) {}
    /// The point c: center c, radius 0 (kernel ball_make_1 or ball_make_2). A c that is not finite
    /// gives the whole line.
    constexpr Ball(const Expansion<T, K>& c) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::make>
        : Ball(detail::make_ball(c, T(0))) {}
    /// The same with a marked operand.
    explicit constexpr Ball(const Unverified<Expansion<T, K>>& c) noexcept : Ball(detail::make_ball(c.value, T(0))) {}
    /// The ball of center c and radius r (kernel ball_make_1 or ball_make_2), each guarded. For a
    /// canonical c: the empty set when r is a NaN or negative (-inf included); otherwise the whole
    /// line when c is not finite or r is +inf; otherwise center c and radius r, exactly. When
    /// KAIRN_CHECKS is 1, c must be canonical and a negative r is reported (it is almost surely a
    /// mistake; write Ball::empty() for the empty set).
    constexpr Ball(const Expansion<T, K>& c, T r) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::make>
        : Ball(detail::make_ball(c, r)) {}
    /// The same with a marked center.
    constexpr Ball(const Unverified<Expansion<T, K>>& c, T r) noexcept : Ball(detail::make_ball(c.value, r)) {}
    /// Internal: a kernel's center and radius, as they are.
    constexpr Ball(detail::kernel_result_t, const Expansion<T, K>& c, T r) noexcept : c_(c), r_(r) {}

    /// The empty set: every limb a NaN.
    [[nodiscard]] static constexpr Ball empty() noexcept {
        constexpr T nan = std::numeric_limits<T>::quiet_NaN();
        Expansion<T, K> c;
        for (int i = 0; i < K; ++i) c.limb[i] = nan;
        return Ball(detail::kernel_result, c, nan);
    }
    /// The whole line: center 0, radius +inf.
    [[nodiscard]] static constexpr Ball whole() noexcept {
        return Ball(detail::kernel_result, Expansion<T, K>(), std::numeric_limits<T>::infinity());
    }

    /// The center: of a finite ball, the center; 0 for the whole line; NaN limbs for the empty set.
    constexpr const Expansion<T, K>& center() const noexcept { return c_; }
    /// The radius: of a finite ball, a bound on the distance of every point of the set to the
    /// center; +inf for the whole line; a NaN for the empty set.
    constexpr T radius() const noexcept { return r_; }
    /// Whether this is a finite ball (for a canonical ball: its radius is finite).
    constexpr bool is_finite() const noexcept { return std::numeric_limits<T>::infinity() > r_; }
    /// Whether this is the whole line (radius +inf).
    constexpr bool is_whole() const noexcept { return r_ == std::numeric_limits<T>::infinity(); }
    /// Whether this is the empty set (radius NaN).
    constexpr bool is_empty() const noexcept { return r_ != r_; }
};

namespace detail {
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 1> make_ball(const Expansion<T, 1>& c, std::type_identity_t<T> r) noexcept {
#if KAIRN_CHECKS
    if (0 > r) fail("a ball", "has a negative radius (Ball::empty() is the empty set)");
#endif
    T cw = T(0), rw = T(0);
    gen::ball_make_1(c.limb[0], r, cw, rw);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(cw), rw);
}
template <class T>
KAIRN_FORCEINLINE constexpr Ball<T, 2> make_ball(const Expansion<T, 2>& c, std::type_identity_t<T> r) noexcept {
#if KAIRN_CHECKS
    if (!canonical(c)) fail("a ball", "has a center that is not canonical");
    if (0 > r) fail("a ball", "has a negative radius (Ball::empty() is the empty set)");
#endif
    Expansion<T, 2> cw;
    T rw = T(0);
    gen::ball_make_2(c.limb[0], c.limb[1], r, cw.limb[0], cw.limb[1], rw);
    return Ball<T, 2>(kernel_result, cw, rw);
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

}  // namespace kairn
