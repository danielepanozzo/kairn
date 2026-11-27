// The benchmark of the round-up interval (bench/up_data.hpp): Kairn's generated default kernels on
// the limbs of each enclosure type, as small types with the operators -, * and + that the
// determinant and Horner use, so that the variant kairn of a computation (the reference of every
// other variant of it) is the same expression as the others. Ordinary code: included by up_check.cpp
// and up_default.cpp, compiled under rounding to nearest, as the default kernels require.
#pragma once

#include <kairn/kairn.hpp>

#include "up_data.hpp"

namespace kairn_bench::up {

namespace kg = kairn::gen;

// Interval<T, 1>: lower and upper bound.
template <class T>
struct K1 {
    T l, u;
};
template <class T>
KB_UP_INLINE K1<T> operator+(const K1<T>& x, const K1<T>& y) {
    K1<T> z;
    kg::interval_add_1(x.l, x.u, y.l, y.u, z.l, z.u);
    return z;
}
template <class T>
KB_UP_INLINE K1<T> operator-(const K1<T>& x, const K1<T>& y) {
    K1<T> z;
    kg::interval_sub_1(x.l, x.u, y.l, y.u, z.l, z.u);
    return z;
}
template <class T>
KB_UP_INLINE K1<T> operator*(const K1<T>& x, const K1<T>& y) {
    K1<T> z;
    kg::interval_mul_1(x.l, x.u, y.l, y.u, z.l, z.u);
    return z;
}

// Interval<T, 2>: the limbs l0, l1 of the lower bound and h0, h1 of the upper one.
template <class T>
struct K2 {
    T l0, l1, h0, h1;
};
template <class T>
KB_UP_INLINE K2<T> operator+(const K2<T>& x, const K2<T>& y) {
    K2<T> z;
    kg::interval_add_2(x.l0, x.l1, x.h0, x.h1, y.l0, y.l1, y.h0, y.h1, z.l0, z.l1, z.h0, z.h1);
    return z;
}
template <class T>
KB_UP_INLINE K2<T> operator-(const K2<T>& x, const K2<T>& y) {
    K2<T> z;
    kg::interval_sub_2(x.l0, x.l1, x.h0, x.h1, y.l0, y.l1, y.h0, y.h1, z.l0, z.l1, z.h0, z.h1);
    return z;
}
template <class T>
KB_UP_INLINE K2<T> operator*(const K2<T>& x, const K2<T>& y) {
    K2<T> z;
    kg::interval_mul_2(x.l0, x.l1, x.h0, x.h1, y.l0, y.l1, y.h0, y.h1, z.l0, z.l1, z.h0, z.h1);
    return z;
}

// Ball<T, 1>: center and radius, the full kernels (with the fix-up), as the operators of Ball.
template <class T>
struct KB1 {
    T c, r;
};
template <class T>
KB_UP_INLINE KB1<T> operator+(const KB1<T>& x, const KB1<T>& y) {
    KB1<T> z;
    kg::ball_add_1_full(x.c, x.r, y.c, y.r, z.c, z.r);
    return z;
}
template <class T>
KB_UP_INLINE KB1<T> operator-(const KB1<T>& x, const KB1<T>& y) {
    KB1<T> z;
    kg::ball_sub_1_full(x.c, x.r, y.c, y.r, z.c, z.r);
    return z;
}
template <class T>
KB_UP_INLINE KB1<T> operator*(const KB1<T>& x, const KB1<T>& y) {
    KB1<T> z;
    kg::ball_mul_1_full(x.c, x.r, y.c, y.r, z.c, z.r);
    return z;
}

// Ball<T, 2>: the limbs c0, c1 of the center and the radius.
template <class T>
struct KB2 {
    T c0, c1, r;
};
template <class T>
KB_UP_INLINE KB2<T> operator+(const KB2<T>& x, const KB2<T>& y) {
    KB2<T> z;
    kg::ball_add_2_full(x.c0, x.c1, x.r, y.c0, y.c1, y.r, z.c0, z.c1, z.r);
    return z;
}
template <class T>
KB_UP_INLINE KB2<T> operator-(const KB2<T>& x, const KB2<T>& y) {
    KB2<T> z;
    kg::ball_sub_2_full(x.c0, x.c1, x.r, y.c0, y.c1, y.r, z.c0, z.c1, z.r);
    return z;
}
template <class T>
KB_UP_INLINE KB2<T> operator*(const KB2<T>& x, const KB2<T>& y) {
    KB2<T> z;
    kg::ball_mul_2_full(x.c0, x.c1, x.r, y.c0, y.c1, y.r, z.c0, z.c1, z.r);
    return z;
}

// A number of T, rounded to nearest: the one-limb kernels of Expansion<T, 1> (the floor's reference).
template <class T>
struct KT {
    T v;
};
template <class T>
KB_UP_INLINE KT<T> operator+(const KT<T>& x, const KT<T>& y) {
    KT<T> z;
    kg::add_1_1(x.v, y.v, z.v);
    return z;
}
template <class T>
KB_UP_INLINE KT<T> operator-(const KT<T>& x, const KT<T>& y) {
    KT<T> z;
    kg::sub_1_1(x.v, y.v, z.v);
    return z;
}
template <class T>
KB_UP_INLINE KT<T> operator*(const KT<T>& x, const KT<T>& y) {
    KT<T> z;
    kg::mul_1_1(x.v, y.v, z.v);
    return z;
}

}  // namespace kairn_bench::up
