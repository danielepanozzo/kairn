// Ball<T, k>: the set of reals within a radius of a center, with a k-limb center and a radius of
// type T (docs/developer/design/phase0/operations.md, "Ball"; the kernels are in
// docs/developer/design/milestone1.md, "Ball kernels").
//
// Each operation forwards to one generated Ball kernel, the finite core of the operation; like
// every operation, it needs the kairn::unverified marker while gen/claims.json does not mark its
// kernel proved. The special states of a ball (the empty set, the whole line) and the treatment
// of a center or radius that overflows are designed (the full Ball kernels of
// docs/developer/design/milestone1.md) but not generated yet.
#pragma once

#include "expansion.hpp"

namespace kairn {

namespace detail {

// The kernels of the Ball operations, by number of limbs of the center.
template <class T, int K>
struct ball_kernels;
template <class T>
struct ball_kernels<T, 1> {
    using add = gen::bounds::ball_add_1<T>;
    using sub = gen::bounds::ball_sub_1<T>;
    using mul = gen::bounds::ball_mul_1<T>;
    using scale = gen::bounds::ball_scale_1<T>;
    using neg = gen::bounds::ball_neg_1<T>;
};
template <class T>
struct ball_kernels<T, 2> {
    using add = gen::bounds::ball_add_2<T>;
    using sub = gen::bounds::ball_sub_2<T>;
    using mul = gen::bounds::ball_mul_2<T>;
    using scale = gen::bounds::ball_scale_2<T>;
    using neg = gen::bounds::ball_neg_2<T>;
};

// A center as it enters a ball. One limb is guarded (detail::guard): it goes into the center's
// addition and can be a product the compiler sees. Two limbs were guarded when they were built.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> enter(const Expansion<T, 1>& c) noexcept {
    return Expansion<T, 1>(guard(c.limb[0]));
}
template <class T>
KAIRN_FORCEINLINE constexpr const Expansion<T, 2>& enter(const Expansion<T, 2>& c) noexcept {
    return c;
}

/// The tag of the constructor of Ball that takes a kernel's result, which needs no guard.
struct kernel_result_t {
    explicit kernel_result_t() = default;
};
inline constexpr kernel_result_t kernel_result{};

template <class T, int K>
KAIRN_FORCEINLINE constexpr void check_ball([[maybe_unused]] const Ball<T, K>& x) noexcept {
#if KAIRN_CHECKS
    check(x.center());
    if (x.radius() < 0) fail("a ball", "has a negative radius");
#endif
}

// The operations, without their markers and constraints: one kernel each. Not constexpr except
// the negation: the radius of every other one is computed with an opaque product.
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> add(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_add_1(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> sub(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_sub_1(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> mul(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_mul_1(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 1> mul(const Ball<T, 1>& x, std::type_identity_t<T> a) noexcept {
    check_ball(x);
    T c = T(0), r = T(0);
    // No guard: ball_scale_1 only multiplies a (prod(cx, a), and rmul(abs(a), rx)).
    gen::ball_scale_1(x.center().limb[0], x.radius(), a, c, r);
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
    gen::ball_add_2(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                    y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> sub(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_sub_2(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                    y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> mul(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_mul_2(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                    y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_FORCEINLINE Ball<T, 2> mul(const Ball<T, 2>& x, std::type_identity_t<T> a) noexcept {
    check_ball(x);
    Expansion<T, 2> c;
    T r = T(0);
    // No guard: ball_scale_2 only multiplies a (mul_2_1(cx, a), and rmul(abs(a), rx)).
    gen::ball_scale_2(x.center().limb[0], x.center().limb[1], x.radius(), a, c.limb[0], c.limb[1], r);
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

// A point operand, an Expansion of the same number of limbs or a T, is a ball of radius zero; a
// T multiplying a ball is the scaling above, not a product of balls.
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(const Ball<T, K>& x, const Expansion<T, K>& y) noexcept {
    return add(x, Ball<T, K>(y));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(const Expansion<T, K>& x, const Ball<T, K>& y) noexcept {
    return add(Ball<T, K>(x), y);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(const Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return add(x, Ball<T, K>(a));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> add(std::type_identity_t<T> a, const Ball<T, K>& y) noexcept {
    return add(Ball<T, K>(a), y);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(const Ball<T, K>& x, const Expansion<T, K>& y) noexcept {
    return sub(x, Ball<T, K>(y));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(const Expansion<T, K>& x, const Ball<T, K>& y) noexcept {
    return sub(Ball<T, K>(x), y);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(const Ball<T, K>& x, std::type_identity_t<T> a) noexcept {
    return sub(x, Ball<T, K>(a));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> sub(std::type_identity_t<T> a, const Ball<T, K>& y) noexcept {
    return sub(Ball<T, K>(a), y);
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> mul(const Ball<T, K>& x, const Expansion<T, K>& y) noexcept {
    return mul(x, Ball<T, K>(y));
}
template <class T, int K>
KAIRN_FORCEINLINE Ball<T, K> mul(const Expansion<T, K>& x, const Ball<T, K>& y) noexcept {
    return mul(Ball<T, K>(x), y);
}

}  // namespace detail

/// The set {t : |t - c| <= r} of the reals within r of c, for a center c of K limbs of type T
/// and a radius r of type T, r >= 0. Defined for K = 1 and K = 2.
///
/// Each operation computes the center with the k-number kernel of the same name (rounded to
/// nearest) and a radius that covers the radii of the operands and that kernel's own proved
/// error bound, evaluated with every step rounded up (milestone1.md, "Ball kernels"). The claim
/// of every Ball kernel (gen/claims.json) is containment, for finite operands with nonnegative
/// radii, in the model where no operation overflows: for every x in X and y in Y, x op y is in
/// the result; and for two limbs the center is normalized. As for every operation, the marker
/// kairn::unverified is needed exactly while a kernel's claim is not proved.
///
/// Not written yet: the special states (a NaN radius for the empty set; the whole line, r = +inf
/// with c = 0), the rule that a center or a radius that is not finite gives the whole line, and
/// any statement in the IEEE model with overflow. Today a result whose center or radius is not
/// finite is returned as the kernel computes it, and nothing is claimed about it.
template <class T, int K>
class Ball {
    static_assert(detail::limb<T>, "Ball<T, k>: the limb type T is float or double");
    static_assert(K == 1 || K == 2, "Ball<T, k>: k is 1 or 2");

    Expansion<T, K> c_{};
    T r_ = T(0);

public:
    // Every center and radius the program passes in is guarded (detail::guard, one addition of
    // +0): the radius goes into radd, an addition, and a one-limb center into the center's
    // addition, where a product the compiler sees could otherwise be fused. A -0 becomes +0.

    /// The point 0: center 0, radius 0.
    constexpr Ball() noexcept = default;
    /// The point x: center x (exactly, up to the sign of a zero), radius 0.
    constexpr Ball(T x) noexcept : c_(detail::enter(Expansion<T, K>(x))) {}
    /// The point c: center c, radius 0.
    constexpr Ball(const Expansion<T, K>& c) noexcept : c_(detail::enter(c)) {}
    /// The ball of center c and radius r. Requires a normalized c and r >= 0: checked when
    /// KAIRN_CHECKS is 1, except that a NaN radius passes (it is the planned representation of the
    /// empty set, about which nothing is claimed yet).
    constexpr Ball(const Expansion<T, K>& c, T r) noexcept : c_(detail::enter(c)), r_(detail::guard(r)) {
#if KAIRN_CHECKS
        detail::check(c_);
        if (r_ < 0) detail::fail("a ball", "has a negative radius");
#endif
    }
    /// Internal: a kernel's center and radius, as they are (rule R2 already keeps them out of
    /// reach of contraction, so they need no guard).
    constexpr Ball(detail::kernel_result_t, const Expansion<T, K>& c, T r) noexcept : c_(c), r_(r) {}

    /// The center.
    constexpr const Expansion<T, K>& center() const noexcept { return c_; }
    /// The radius: every point of the set is within it of the center.
    constexpr T radius() const noexcept { return r_; }

    /// X + Y (kernel ball_add_1 or ball_add_2). Not usable in constant evaluation yet.
    friend KAIRN_FORCEINLINE Ball operator+(const Ball& x, const Ball& y) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::add>
    {
        return detail::add(x, y);
    }
    /// X - Y (kernel ball_sub_1 or ball_sub_2).
    friend KAIRN_FORCEINLINE Ball operator-(const Ball& x, const Ball& y) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub>
    {
        return detail::sub(x, y);
    }
    /// X * Y (kernel ball_mul_1 or ball_mul_2).
    friend KAIRN_FORCEINLINE Ball operator*(const Ball& x, const Ball& y) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::mul>
    {
        return detail::mul(x, y);
    }
    /// a X, for an exact a of type T (kernel ball_scale_1 or ball_scale_2).
    friend KAIRN_FORCEINLINE Ball operator*(const Ball& x, T a) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale>
    {
        return detail::mul(x, a);
    }
    /// a X: as X a.
    friend KAIRN_FORCEINLINE Ball operator*(T a, const Ball& x) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale>
    {
        return detail::mul(a, x);
    }
    /// -X (kernel ball_neg_1 or ball_neg_2): exactly -X.
    friend KAIRN_FORCEINLINE constexpr Ball operator-(const Ball& x) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::neg>
    {
        return detail::neg(x);
    }
    /// X = X + Y.
    friend KAIRN_FORCEINLINE Ball& operator+=(Ball& x, const Ball& y) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::add>
    {
        return x = detail::add(x, y);
    }
    /// X = X - Y.
    friend KAIRN_FORCEINLINE Ball& operator-=(Ball& x, const Ball& y) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::sub>
    {
        return x = detail::sub(x, y);
    }
    /// X = X * Y.
    friend KAIRN_FORCEINLINE Ball& operator*=(Ball& x, const Ball& y) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::mul>
    {
        return x = detail::mul(x, y);
    }
    /// X = a X.
    friend KAIRN_FORCEINLINE Ball& operator*=(Ball& x, T a) noexcept
        requires detail::proof_checked<typename detail::ball_kernels<T, K>::scale>
    {
        return x = detail::mul(x, a);
    }
};

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
