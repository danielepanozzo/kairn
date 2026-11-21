/// @file
/// Internal: the definitions of the operations of Interval that round, one generated kernel each
/// (+ - * of one and two limbs), whose declarations are in interval.hpp. interval.hpp includes this
/// header when KAIRN_ENCLOSURE_CODE is KAIRN_ENCLOSURE_CODE_INLINE or
/// KAIRN_ENCLOSURE_CODE_OUTLINED; when it is KAIRN_ENCLOSURE_CODE_EXTERNAL, kairn/definitions.hpp
/// includes it, in the one translation unit of the program that defines them (config.hpp). A
/// program never includes it itself.
#pragma once

#include "interval.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn::detail {
KAIRN_DETAIL_ENCLOSURE_BEGIN

// The operations, without their markers and constraints: one kernel each. Not constexpr: the
// kernels of the product of one limb and of the operations of two limbs have fused operations
// without a variant for constant evaluation, and in the external setting the code of each is in
// another translation unit. The kernels are force-inlined into each but interval_mul_2, an
// ordinary inline function in every setting (milestone2.md, "Inlining and compile time"); what
// each computes is the same in every setting of KAIRN_ENCLOSURE_CODE, the body being the same
// listing, whose rules R1 to R3 make it immune to what a compiler does at a call boundary.
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 1> add(const Interval<T, 1>& x, const Interval<T, 1>& y) noexcept {
    check_interval(x);
    check_interval(y);
    T l = T(0), h = T(0);
    gen::interval_add_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], l, h);
    return Interval<T, 1>(kernel_result, Expansion<T, 1>(l), Expansion<T, 1>(h));
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 1> sub(const Interval<T, 1>& x, const Interval<T, 1>& y) noexcept {
    check_interval(x);
    check_interval(y);
    T l = T(0), h = T(0);
    gen::interval_sub_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], l, h);
    return Interval<T, 1>(kernel_result, Expansion<T, 1>(l), Expansion<T, 1>(h));
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 1> mul(const Interval<T, 1>& x, const Interval<T, 1>& y) noexcept {
    check_interval(x);
    check_interval(y);
    T l = T(0), h = T(0);
    gen::interval_mul_1(x.lower().limb[0], x.upper().limb[0], y.lower().limb[0], y.upper().limb[0], l, h);
    return Interval<T, 1>(kernel_result, Expansion<T, 1>(l), Expansion<T, 1>(h));
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 2> add(const Interval<T, 2>& x, const Interval<T, 2>& y) noexcept {
    check_interval(x);
    check_interval(y);
    Expansion<T, 2> l, h;
    gen::interval_add_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1], y.lower().limb[0],
                        y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], l.limb[0], l.limb[1], h.limb[0],
                        h.limb[1]);
    return Interval<T, 2>(kernel_result, l, h);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 2> sub(const Interval<T, 2>& x, const Interval<T, 2>& y) noexcept {
    check_interval(x);
    check_interval(y);
    Expansion<T, 2> l, h;
    gen::interval_sub_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1], y.lower().limb[0],
                        y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], l.limb[0], l.limb[1], h.limb[0],
                        h.limb[1]);
    return Interval<T, 2>(kernel_result, l, h);
}
template <class T>
KAIRN_DETAIL_ENCLOSURE Interval<T, 2> mul(const Interval<T, 2>& x, const Interval<T, 2>& y) noexcept {
    check_interval(x);
    check_interval(y);
    Expansion<T, 2> l, h;
    gen::interval_mul_2(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0], x.upper().limb[1], y.lower().limb[0],
                        y.lower().limb[1], y.upper().limb[0], y.upper().limb[1], l.limb[0], l.limb[1], h.limb[0],
                        h.limb[1]);
    return Interval<T, 2>(kernel_result, l, h);
}

KAIRN_DETAIL_ENCLOSURE_END
}  // namespace kairn::detail
KAIRN_GEN_POP_WARNINGS
