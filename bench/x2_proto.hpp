// The earlier scalar prototype of the two-limb interval under the rounding mode upward, kept for
// comparison (bench/x2_data.hpp, backend x2p): a measurement prop, not part of the library and NOT
// VERIFIED. Requires the rounding mode upward, set by std::fesetround around each loop in a unit
// compiled so that the compiler honors it (-frounding-math; FENV_ACCESS with Clang), as
// m2_fenv.cpp. No Kairn header.
//
// Under that mode every operation rounds up, so a sum of terms computed here is at least the exact
// sum, and the only subtractions are ones that are exact:
// - a pair (h, l) stands for the number h + l, and is an upper pair of a value v when h + l >= v;
// - an interval [lo, hi] is kept as an upper pair of -lo and an upper pair of hi;
// - fast_two_sum_up(a, b), |a| >= |b|: s = RU(a + b); s - a is exact; t = RU(b - (s - a)) is at
//   least the error a + b - s, which is not always a number of the format under a directed mode;
// - a product: p = RU(x0 y0), and its error by two fused operations, one rounded up for each sign.
// The special values follow Kairn's listings, a first limb that reaches the largest number counting
// as infinite. Its layout converts between Kairn's (l0, l1, h0, h1) and its own inside each operation
// of the original; here the arrays hold its own storage (Ival), filled outside the timed functions.
#pragma once

#include <cmath>
#include <limits>

#if defined(_MSC_VER) && !defined(__clang__)
#define KB_UP2_INLINE __forceinline
#define KB_UP2_FMA(a, b, c) std::fma(a, b, c)
#else
#define KB_UP2_INLINE inline __attribute__((always_inline))
#define KB_UP2_FMA(a, b, c) __builtin_fma(a, b, c)
#endif

namespace kairn_bench::up2 {

inline constexpr double kInf = std::numeric_limits<double>::infinity();
inline constexpr double kMax = std::numeric_limits<double>::max();

struct Pair {
    double h, l;   // the number h + l
};
struct Ival {
    Pair nl, hu;   // the interval [-(nl.h + nl.l), hu.h + hu.l]
};

KB_UP2_INLINE Pair fast_two_sum_up(double a, double b) {
    const double s = a + b;
    const double z = s - a;
    const double t = b - z;
    return {s, t};
}
KB_UP2_INLINE Pair two_sum_ord_up(double a, double b) {
    const bool m = std::fabs(a) < std::fabs(b);
    const double h = m ? b : a;
    const double l = m ? a : b;
    return fast_two_sum_up(h, l);
}
KB_UP2_INLINE Pair add_up(Pair x, Pair y) {
    const Pair s = two_sum_ord_up(x.h, y.h);
    const Pair t = two_sum_ord_up(x.l, y.l);
    const double c = s.l + t.h;
    const Pair v = two_sum_ord_up(s.h, c);
    const double d = t.l + v.l;
    return two_sum_ord_up(v.h, d);
}
KB_UP2_INLINE void mul_dir_up(Pair x, Pair y, Pair& up, Pair& dn) {
    const double nh = -x.h, nl = -x.l;
    const double p = x.h * y.h;
    const double e = KB_UP2_FMA(x.h, y.h, -p);
    const double f = KB_UP2_FMA(nh, y.h, p);
    const double a = KB_UP2_FMA(x.l, y.h, KB_UP2_FMA(x.h, y.l, x.l * y.l));
    const double b = KB_UP2_FMA(nl, y.h, KB_UP2_FMA(nh, y.l, nl * y.l));
    up = fast_two_sum_up(p, e + a);
    dn = fast_two_sum_up(-p, f + b);
}
KB_UP2_INLINE void mul_ext_up(Pair x, Pair y, Pair& up, Pair& dn) {
    Pair u, d;
    mul_dir_up(x, y, u, d);
    const double t = x.h * y.h;
    const bool fo = std::fabs(x.h) < kInf && std::fabs(y.h) < kInf;
    const bool nz = !(x.h == 0 || y.h == 0);
    const bool fin = std::fabs(u.h) < kMax && std::fabs(d.h) < kMax;
    u = {fin ? u.h : kInf, fin ? u.l : 0.0};
    d = {fin ? d.h : kInf, fin ? d.l : 0.0};
    u = {fo ? u.h : t, fo ? u.l : 0.0};
    d = {fo ? d.h : -t, fo ? d.l : 0.0};
    up = {nz ? u.h : 0.0, nz ? u.l : 0.0};
    dn = {nz ? d.h : 0.0, nz ? d.l : 0.0};
}
KB_UP2_INLINE Pair max2(Pair a, Pair b) {
    const bool m = a.h < b.h || (a.h == b.h && a.l < b.l);
    return {m ? b.h : a.h, m ? b.l : a.l};
}
KB_UP2_INLINE Pair finite_or_inf(Pair p) {
    const bool f = std::fabs(p.h) < kMax;
    return {f ? p.h : kInf, f ? p.l : 0.0};
}
KB_UP2_INLINE Ival or_empty(bool nonempty, Pair nl, Pair hu) {
    return {{nonempty ? nl.h : -kInf, nonempty ? nl.l : 0.0}, {nonempty ? hu.h : -kInf, nonempty ? hu.l : 0.0}};
}
KB_UP2_INLINE Ival iadd(Ival x, Ival y) {
    const Pair a = finite_or_inf(add_up(x.nl, y.nl));
    const Pair b = finite_or_inf(add_up(x.hu, y.hu));
    return or_empty(x.nl.h > -kInf && y.nl.h > -kInf, a, b);
}
// The difference: x - y = x + (-y), -y being y with its two pairs exchanged.
KB_UP2_INLINE Ival isub(Ival x, Ival y) { return iadd(x, Ival{y.hu, y.nl}); }
KB_UP2_INLINE Ival imul(Ival x, Ival y) {
    Pair u1, d1, u2, d2, u3, d3, u4, d4;
    mul_ext_up(x.nl, y.nl, u1, d1);   // xl yl
    mul_ext_up(x.nl, y.hu, d2, u2);   // -(xl yu)
    mul_ext_up(x.hu, y.nl, d3, u3);   // -(xu yl)
    mul_ext_up(x.hu, y.hu, u4, d4);   // xu yu
    const Pair hu = max2(max2(u1, u2), max2(u3, u4));
    const Pair nl = max2(max2(d1, d2), max2(d3, d4));
    return or_empty(x.nl.h > -kInf && y.nl.h > -kInf, nl, hu);
}
// Kairn's layout of an Interval<double, 2>: l0, l1, h0, h1.
KB_UP2_INLINE Ival load(const double* p) { return {{-p[0], -p[1]}, {p[2], p[3]}}; }
KB_UP2_INLINE void store(Ival v, double* p) {
    p[0] = -v.nl.h;
    p[1] = -v.nl.l;
    p[2] = v.hu.h;
    p[3] = v.hu.l;
}

}  // namespace kairn_bench::up2
