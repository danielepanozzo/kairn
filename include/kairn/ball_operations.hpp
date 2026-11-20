/// @file
/// Internal: the definitions of the operations of Ball that round, one generated kernel each,
/// whose declarations are in ball.hpp. ball.hpp includes this header when KAIRN_ENCLOSURE_CODE is
/// KAIRN_ENCLOSURE_CODE_INLINE or KAIRN_ENCLOSURE_CODE_OUTLINED; when it is
/// KAIRN_ENCLOSURE_CODE_EXTERNAL, kairn/definitions.hpp includes it, in the one translation unit
/// of the program that defines them (config.hpp). A program never includes it itself.
#pragma once

#include "ball.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn::detail {
KAIRN_DETAIL_ENCLOSURE_BEGIN

// The operations, without their markers and constraints: one kernel each. Not constexpr: the
// radius of each is computed with fused operations. The kernel is force-inlined into each, so
// that what each computes is the same in every setting of KAIRN_ENCLOSURE_CODE.
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> add(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_add_1_full(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> sub(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_sub_1_full(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> mul(const Ball<T, 1>& x, const Ball<T, 1>& y) noexcept {
    check_ball(x);
    check_ball(y);
    T c = T(0), r = T(0);
    gen::ball_mul_1_full(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 1> mul(const Ball<T, 1>& x, std::type_identity_t<T> a) noexcept {
    check_ball(x);
    T c = T(0), r = T(0);
    // a is only multiplied (the center's product, abs(a) times the radius): no guard needed.
    gen::ball_scale_1_full(x.center().limb[0], x.radius(), a, c, r);
    return Ball<T, 1>(kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> add(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_add_2_full(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                         y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> sub(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_sub_2_full(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                         y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> mul(const Ball<T, 2>& x, const Ball<T, 2>& y) noexcept {
    check_ball(x);
    check_ball(y);
    Expansion<T, 2> c;
    T r = T(0);
    gen::ball_mul_2_full(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1],
                         y.radius(), c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Ball<T, 2> mul(const Ball<T, 2>& x, std::type_identity_t<T> a) noexcept {
    check_ball(x);
    Expansion<T, 2> c;
    T r = T(0);
    // a is only multiplied (mul_2_1 on the center, abs(a) times the radius): no guard needed.
    gen::ball_scale_2_full(x.center().limb[0], x.center().limb[1], x.radius(), a, c.limb[0], c.limb[1], r);
    return Ball<T, 2>(kernel_result, c, r);
}

KAIRN_DETAIL_ENCLOSURE_END
}  // namespace kairn::detail
KAIRN_GEN_POP_WARNINGS
