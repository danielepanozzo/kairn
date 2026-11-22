// The timed functions of the enclosure interface that Interval<T, k> and Ball<T, k> share
// (include/kairn/enclosure.hpp; bench/m2_data.hpp; bench/README.md, "Milestone 2", second part), for
// double limbs (backend m2e) and float limbs (m2ef), for each of Interval<T, 1>, Interval<T, 2>,
// Ball<T, 1> and Ball<T, 2> (the kernel's name starts with i1_, i2_, b1_, b2_): the predicates, the
// member and subset tests, the three-valued comparisons and member, the relations of IEEE 1788 of
// intervals, hull, intersection, split, midpoint() and radius() alone and together against mid_rad(),
// and the conversions between the two kinds; in a loop of 256 independent operations (KIND tp, time
// per operation) and, for those that return a set, in a dependent chain (KIND step, time per step).
//
// Variants: kairn, the generated kernel called on the limbs (the reference); op, the public function
// as a client calls it; plain, for one limb, the same question asked in plain arithmetic of T (a
// comparison of bounds, c - r and c + r for a ball), the control. The plain forms of the set
// operations of a ball compute other values than Kairn's (no outward rounding), so they are kernels
// of their own (b1_phull, b1_pinter, b1_psplit), each with a kairn reference that computes the same
// values with the generated one-limb kernels, as the floors of m2.cpp do; the plain midpoint, radius
// and bounds of the first part (m2/tp/plain_midrad_1, m2/tp/plain_bounds_1) are the controls of the
// midpoint, the split and the conversions. Every function is checked before it is timed against
// BACKEND/KIND/KERNEL/kairn, byte for byte (check() below).
//
// The operands: for each type 256 sets X around numbers +-[1, 2) 2^k, k in [-4, 4], of half-width
// (radius) 2^-30 of the center for one limb of double (2^-12 for float) and 2^-80 for two (2^-40);
// Y of the same width shifted by -6, -1, 0, 1 or 6 half-widths, so that the comparisons answer yes,
// no and unknown in turn; S, half of them inside X; W, from the midpoint of X to beyond it; points t,
// half of them the center and half three half-widths beyond it; and, for the chain of intersections,
// sets that all contain [-1/2, 1/2].
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <string>
#include <type_traits>
#include <vector>

#include "bench_util.hpp"
#include "m2_data.hpp"

namespace {

namespace kg = kairn::gen;
using kairn::Trit;
using kairn_bench::m2::Entry;
constexpr int kN = kairn_bench::m2::kN;

template <class T, int K>
using I = kairn::Interval<T, K>;
template <class T, int K>
using B = kairn::Ball<T, K>;
template <class T, int K>
using E = kairn::Expansion<T, K>;

// The limb type, the number of limbs, the limbs of one set, and the type the conversion makes.
template <class X>
struct info;
template <class T_, int K_>
struct info<kairn::Interval<T_, K_>> {
    using T = T_;
    static constexpr int K = K_, limbs = 2 * K_;
    using other = kairn::Ball<T_, K_>;
};
template <class T_, int K_>
struct info<kairn::Ball<T_, K_>> {
    using T = T_;
    static constexpr int K = K_, limbs = K_ + 1;
    using other = kairn::Interval<T_, K_>;
};

// The operands and the outputs of one type.
template <class X>
struct Set {
    using T = typename info<X>::T;
    X x[kN], y[kN], s[kN], w[kN], wc[kN];
    T t[kN];
    signed char o8[kN];   // a bool or a Trit per element
    T ot[8 * kN];         // up to 8 values of T per element: the limbs of a set, of two, of a number
    T oc[8];              // the end of a chain
};
template <class X>
Set<X>* g_set = nullptr;

// Where a function writes (Entry::region).
enum Out : int { O8 = 0, OT = 1, OC = 2 };

#define KB_SI KAIRN_GEN_FORCEINLINE

KB_SI signed char t8(Trit t) { return static_cast<signed char>(t); }
KB_SI Trit trit(bool yes, bool no) { return yes ? Trit::yes : (no ? Trit::no : Trit::unknown); }

// The limbs of a set, as the kernels take them.
#define LI1(x) (x).lower().limb[0], (x).upper().limb[0]
#define LI2(x) (x).lower().limb[0], (x).lower().limb[1], (x).upper().limb[0], (x).upper().limb[1]
#define LB1(x) (x).center().limb[0], (x).radius()
#define LB2(x) (x).center().limb[0], (x).center().limb[1], (x).radius()

// Writes the limbs of v as element i of o, an array of values of T with N per element.
template <class T>
KB_SI void put(T* o, int i, const I<T, 1>& v) {
    o[2 * i] = v.lower().limb[0];
    o[2 * i + 1] = v.upper().limb[0];
}
template <class T>
KB_SI void put(T* o, int i, const I<T, 2>& v) {
    o[4 * i] = v.lower().limb[0];
    o[4 * i + 1] = v.lower().limb[1];
    o[4 * i + 2] = v.upper().limb[0];
    o[4 * i + 3] = v.upper().limb[1];
}
template <class T>
KB_SI void put(T* o, int i, const B<T, 1>& v) {
    o[2 * i] = v.center().limb[0];
    o[2 * i + 1] = v.radius();
}
template <class T>
KB_SI void put(T* o, int i, const B<T, 2>& v) {
    o[3 * i] = v.center().limb[0];
    o[3 * i + 1] = v.center().limb[1];
    o[3 * i + 2] = v.radius();
}
template <class X>
KB_SI void put_split(typename info<X>::T* o, int i, const kairn::Split<X>& s) {
    put(o, 2 * i, s.left);
    put(o, 2 * i + 1, s.right);
}
template <class T, int K>
KB_SI void put_number(T* o, int i, const E<T, K>& m) {
    for (int j = 0; j < K; ++j) o[K * i + j] = m.limb[j];
}

// --- The public functions, as free functions of one shape --------------------------------------

namespace api {
template <class X> KB_SI bool empty(const X& x) { return x.is_empty(); }
template <class X> KB_SI bool whole(const X& x) { return x.is_whole(); }
template <class X> KB_SI bool pos(const X& x) { return x.certainly_positive(); }
template <class X> KB_SI bool neg(const X& x) { return x.certainly_negative(); }
template <class X> KB_SI bool zero(const X& x) { return x.certainly_zero(); }
template <class X> KB_SI bool contains_t(const X& x, typename info<X>::T t) { return x.contains(t); }
template <class X> KB_SI bool contains_set(const X& x, const X& y) { return x.contains(y); }
template <class X> KB_SI Trit less(const X& x, const X& y) { return kairn::less(x, y); }
template <class X> KB_SI Trit less_equal(const X& x, const X& y) { return kairn::less_equal(x, y); }
template <class X> KB_SI Trit equal(const X& x, const X& y) { return kairn::equal(x, y); }
template <class X> KB_SI Trit member(typename info<X>::T t, const X& x) { return kairn::member(t, x); }
template <class X> KB_SI bool rel_equal(const X& x, const X& y) { return kairn::ieee1788::equal(x, y); }
template <class X> KB_SI bool rel_interior(const X& x, const X& y) { return kairn::ieee1788::interior(x, y); }
template <class X> KB_SI bool rel_disjoint(const X& x, const X& y) { return kairn::ieee1788::disjoint(x, y); }
}  // namespace api

// --- The generated kernels on the limbs, the references ----------------------------------------
// One overload per type; for an operation that a type has no kernel for there is none.

namespace kref {
#define KB_KPRED(NAME, KI, KB)                                                                     \
    template <class T> KB_SI bool NAME(const I<T, 1>& x) { bool m = false; kg::interval_##KI##_1(LI1(x), m); return m; } \
    template <class T> KB_SI bool NAME(const I<T, 2>& x) { bool m = false; kg::interval_##KI##_2(LI2(x), m); return m; }
KB_KPRED(empty, empty, )
KB_KPRED(whole, entire, )
KB_KPRED(pos, positive, )
KB_KPRED(neg, negative, )
KB_KPRED(zero, zero, )
#define KB_KBPRED(NAME, KB)                                                                        \
    template <class T> KB_SI bool NAME(const B<T, 1>& x) { bool m = false; kg::ball_##KB##_1(LB1(x), m); return m; } \
    template <class T> KB_SI bool NAME(const B<T, 2>& x) { bool m = false; kg::ball_##KB##_2(LB2(x), m); return m; }
KB_KBPRED(pos, positive)
template <class T, int K> KB_SI bool empty(const B<T, K>& x) { return x.radius() != x.radius(); }
template <class T, int K> KB_SI bool whole(const B<T, K>& x) { return x.radius() == std::numeric_limits<T>::infinity(); }
KB_KBPRED(neg, negative)
KB_KBPRED(zero, zero)
// The member test: for two limbs t made a number of two limbs first (make_2), as the headers do.
template <class T> KB_SI bool contains_t(const I<T, 1>& x, T t) { bool m = false; kg::interval_contains_1(LI1(x), t, m); return m; }
template <class T> KB_SI bool contains_t(const I<T, 2>& x, T t) {
    T p0, p1;
    kg::make_2(t, p0, p1);
    bool m = false;
    kg::interval_contains_2(LI2(x), p0, p1, m);
    return m;
}
template <class T> KB_SI bool contains_t(const B<T, 1>& x, T t) { bool m = false; kg::ball_contains_point_1(LB1(x), t, m); return m; }
template <class T> KB_SI Trit member_b2(const B<T, 2>& x, T t) {
    T p0, p1;
    kg::make_2(t, p0, p1);
    bool yes = false, no = false;
    kg::ball_contains_point_2(LB2(x), p0, p1, yes, no);
    return trit(yes, no);
}
template <class T> KB_SI bool contains_t(const B<T, 2>& x, T t) { return member_b2(x, t) == Trit::yes; }
template <class T> KB_SI Trit member(T t, const I<T, 1>& x) { return contains_t(x, t) ? Trit::yes : Trit::no; }
template <class T> KB_SI Trit member(T t, const I<T, 2>& x) { return contains_t(x, t) ? Trit::yes : Trit::no; }
template <class T> KB_SI Trit member(T t, const B<T, 1>& x) { return contains_t(x, t) ? Trit::yes : Trit::no; }
template <class T> KB_SI Trit member(T t, const B<T, 2>& x) { return member_b2(x, t); }
// X contains Y: for intervals the subset kernel with Y first, for balls X first.
template <class T> KB_SI bool contains_set(const I<T, 1>& x, const I<T, 1>& y) { bool m = false; kg::interval_subset_1(LI1(y), LI1(x), m); return m; }
template <class T> KB_SI bool contains_set(const I<T, 2>& x, const I<T, 2>& y) { bool m = false; kg::interval_subset_2(LI2(y), LI2(x), m); return m; }
template <class T> KB_SI bool contains_set(const B<T, 1>& x, const B<T, 1>& y) { bool m = false; kg::ball_contains_ball_1(LB1(x), LB1(y), m); return m; }
template <class T> KB_SI bool contains_set(const B<T, 2>& x, const B<T, 2>& y) { bool m = false; kg::ball_contains_ball_2(LB2(x), LB2(y), m); return m; }
#define KB_KTRIT(NAME)                                                                             \
    template <class T> KB_SI Trit NAME(const I<T, 1>& x, const I<T, 1>& y) { bool a = false, b = false; kg::interval_##NAME##_1(LI1(x), LI1(y), a, b); return trit(a, b); } \
    template <class T> KB_SI Trit NAME(const I<T, 2>& x, const I<T, 2>& y) { bool a = false, b = false; kg::interval_##NAME##_2(LI2(x), LI2(y), a, b); return trit(a, b); } \
    template <class T> KB_SI Trit NAME(const B<T, 1>& x, const B<T, 1>& y) { bool a = false, b = false; kg::ball_##NAME##_1(LB1(x), LB1(y), a, b); return trit(a, b); } \
    template <class T> KB_SI Trit NAME(const B<T, 2>& x, const B<T, 2>& y) { bool a = false, b = false; kg::ball_##NAME##_2(LB2(x), LB2(y), a, b); return trit(a, b); }
KB_KTRIT(less)
KB_KTRIT(less_equal)
KB_KTRIT(equal)
#define KB_KREL(NAME)                                                                              \
    template <class T> KB_SI bool NAME(const I<T, 1>& x, const I<T, 1>& y) { bool m = false; kg::interval_##NAME##_1(LI1(x), LI1(y), m); return m; } \
    template <class T> KB_SI bool NAME(const I<T, 2>& x, const I<T, 2>& y) { bool m = false; kg::interval_##NAME##_2(LI2(x), LI2(y), m); return m; }
KB_KREL(rel_equal)
KB_KREL(rel_interior)
KB_KREL(rel_disjoint)
// The set operations, written to o as put() writes the public result.
#define KB_KSET(NAME)                                                                              \
    template <class T> KB_SI void NAME(T* o, int i, const I<T, 1>& x, const I<T, 1>& y) {           \
        kg::interval_##NAME##_1(LI1(x), LI1(y), o[2 * i], o[2 * i + 1]); }                         \
    template <class T> KB_SI void NAME(T* o, int i, const I<T, 2>& x, const I<T, 2>& y) {           \
        kg::interval_##NAME##_2(LI2(x), LI2(y), o[4 * i], o[4 * i + 1], o[4 * i + 2], o[4 * i + 3]); } \
    template <class T> KB_SI void NAME(T* o, int i, const B<T, 1>& x, const B<T, 1>& y) {           \
        kg::ball_##NAME##_1(LB1(x), LB1(y), o[2 * i], o[2 * i + 1]); }                             \
    template <class T> KB_SI void NAME(T* o, int i, const B<T, 2>& x, const B<T, 2>& y) {           \
        kg::ball_##NAME##_2(LB2(x), LB2(y), o[3 * i], o[3 * i + 1], o[3 * i + 2]); }
KB_KSET(hull)
KB_KSET(intersection)
template <class T> KB_SI void split(T* o, int i, const I<T, 1>& x) {
    kg::interval_split_1(LI1(x), o[4 * i], o[4 * i + 1], o[4 * i + 2], o[4 * i + 3]);
}
template <class T> KB_SI void split(T* o, int i, const I<T, 2>& x) {
    T* p = o + 8 * i;
    kg::interval_split_2(LI2(x), p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]);
}
template <class T> KB_SI void split(T* o, int i, const B<T, 1>& x) {
    kg::ball_split_1(LB1(x), o[4 * i], o[4 * i + 1], o[4 * i + 2], o[4 * i + 3]);
}
template <class T> KB_SI void split(T* o, int i, const B<T, 2>& x) {
    T* p = o + 6 * i;
    kg::ball_split_2(LB2(x), p[0], p[1], p[2], p[3], p[4], p[5]);
}
// The midpoint and the radius of an interval: what the kernel writes, all or a part.
template <class T> KB_SI void mid_rad(const I<T, 1>& x, T* m, T& r) { kg::interval_mid_rad_1(LI1(x), m[0], r); }
template <class T> KB_SI void mid_rad(const I<T, 2>& x, T* m, T& r) { kg::interval_mid_rad_2(LI2(x), m[0], m[1], r); }
// The conversion to the other kind.
template <class T> KB_SI void convert(T* o, int i, const I<T, 1>& x) { kg::interval_to_ball_1(LI1(x), o[2 * i], o[2 * i + 1]); }
template <class T> KB_SI void convert(T* o, int i, const I<T, 2>& x) { kg::interval_to_ball_2(LI2(x), o[3 * i], o[3 * i + 1], o[3 * i + 2]); }
template <class T> KB_SI void convert(T* o, int i, const B<T, 1>& x) { kg::ball_to_interval_1(LB1(x), o[2 * i], o[2 * i + 1]); }
template <class T> KB_SI void convert(T* o, int i, const B<T, 2>& x) {
    kg::ball_to_interval_2(LB2(x), o[4 * i], o[4 * i + 1], o[4 * i + 2], o[4 * i + 3]);
}
}  // namespace kref

// --- The same questions in plain arithmetic of T, one limb --------------------------------------

namespace plain {
template <class T> KB_SI bool empty(const I<T, 1>& x) { return !(x.lower().limb[0] <= x.upper().limb[0]); }
template <class T> KB_SI bool whole(const I<T, 1>& x) {
    return x.lower().limb[0] == -std::numeric_limits<T>::infinity() && x.upper().limb[0] == std::numeric_limits<T>::infinity();
}
template <class T> KB_SI bool pos(const I<T, 1>& x) { return x.lower().limb[0] > 0; }
template <class T> KB_SI bool neg(const I<T, 1>& x) { return x.upper().limb[0] < 0; }
template <class T> KB_SI bool zero(const I<T, 1>& x) { return x.lower().limb[0] == 0 && x.upper().limb[0] == 0; }
template <class T> KB_SI bool contains_t(const I<T, 1>& x, T t) { return x.lower().limb[0] <= t && t <= x.upper().limb[0]; }
template <class T> KB_SI bool contains_set(const I<T, 1>& x, const I<T, 1>& y) {
    return x.lower().limb[0] <= y.lower().limb[0] && y.upper().limb[0] <= x.upper().limb[0];
}
template <class T> KB_SI Trit less(const I<T, 1>& x, const I<T, 1>& y) {
    return trit(x.upper().limb[0] < y.lower().limb[0], x.lower().limb[0] >= y.upper().limb[0]);
}
template <class T> KB_SI Trit less_equal(const I<T, 1>& x, const I<T, 1>& y) {
    return trit(x.upper().limb[0] <= y.lower().limb[0], x.lower().limb[0] > y.upper().limb[0]);
}
template <class T> KB_SI Trit equal(const I<T, 1>& x, const I<T, 1>& y) {
    const T xl = x.lower().limb[0], xu = x.upper().limb[0], yl = y.lower().limb[0], yu = y.upper().limb[0];
    return trit(xl == xu && yl == yu && xl == yl, xu < yl || yu < xl);
}
template <class T> KB_SI Trit member(T t, const I<T, 1>& x) { return contains_t(x, t) ? Trit::yes : Trit::no; }
template <class T> KB_SI bool rel_equal(const I<T, 1>& x, const I<T, 1>& y) {
    return x.lower().limb[0] == y.lower().limb[0] && x.upper().limb[0] == y.upper().limb[0];
}
template <class T> KB_SI bool rel_interior(const I<T, 1>& x, const I<T, 1>& y) {
    return y.lower().limb[0] < x.lower().limb[0] && x.upper().limb[0] < y.upper().limb[0];
}
template <class T> KB_SI bool rel_disjoint(const I<T, 1>& x, const I<T, 1>& y) {
    return x.upper().limb[0] < y.lower().limb[0] || y.upper().limb[0] < x.lower().limb[0];
}
template <class T> KB_SI void hull(T* o, int i, const I<T, 1>& x, const I<T, 1>& y) {
    const T xl = x.lower().limb[0], xu = x.upper().limb[0], yl = y.lower().limb[0], yu = y.upper().limb[0];
    o[2 * i] = yl < xl ? yl : xl;
    o[2 * i + 1] = xu < yu ? yu : xu;
}
template <class T> KB_SI void intersection(T* o, int i, const I<T, 1>& x, const I<T, 1>& y) {
    const T xl = x.lower().limb[0], xu = x.upper().limb[0], yl = y.lower().limb[0], yu = y.upper().limb[0];
    const T l = xl < yl ? yl : xl, h = yu < xu ? yu : xu;
    const bool e = h < l;
    o[2 * i] = e ? std::numeric_limits<T>::infinity() : l;
    o[2 * i + 1] = e ? -std::numeric_limits<T>::infinity() : h;
}
// Balls: c - r and c + r, rounded to nearest.
template <class T> KB_SI bool empty(const B<T, 1>& x) { return x.radius() != x.radius(); }
template <class T> KB_SI bool whole(const B<T, 1>& x) { return x.radius() == std::numeric_limits<T>::infinity(); }
template <class T> KB_SI bool pos(const B<T, 1>& x) { return x.center().limb[0] - x.radius() > 0; }
template <class T> KB_SI bool neg(const B<T, 1>& x) { return x.center().limb[0] + x.radius() < 0; }
template <class T> KB_SI bool zero(const B<T, 1>& x) { return x.center().limb[0] == 0 && x.radius() == 0; }
template <class T> KB_SI bool contains_t(const B<T, 1>& x, T t) { return std::fabs(t - x.center().limb[0]) <= x.radius(); }
template <class T> KB_SI bool contains_set(const B<T, 1>& x, const B<T, 1>& y) {
    return std::fabs(y.center().limb[0] - x.center().limb[0]) <= x.radius() - y.radius();
}
template <class T> KB_SI Trit less(const B<T, 1>& x, const B<T, 1>& y) {
    const T cx = x.center().limb[0], rx = x.radius(), cy = y.center().limb[0], ry = y.radius();
    return trit(cx + rx < cy - ry, cx - rx >= cy + ry);
}
template <class T> KB_SI Trit less_equal(const B<T, 1>& x, const B<T, 1>& y) {
    const T cx = x.center().limb[0], rx = x.radius(), cy = y.center().limb[0], ry = y.radius();
    return trit(cx + rx <= cy - ry, cx - rx > cy + ry);
}
template <class T> KB_SI Trit equal(const B<T, 1>& x, const B<T, 1>& y) {
    const T cx = x.center().limb[0], rx = x.radius(), cy = y.center().limb[0], ry = y.radius();
    return trit(rx == 0 && ry == 0 && cx == cy, cx + rx < cy - ry || cy + ry < cx - rx);
}
template <class T> KB_SI Trit member(T t, const B<T, 1>& x) { return contains_t(x, t) ? Trit::yes : Trit::no; }
}  // namespace plain

// The plain set operations of a ball of one limb (their own kernels: their values are not Kairn's):
// the bounds c - r, c + r rounded to nearest, their least and greatest, and the ball (l + h)/2,
// (h - l)/2; the split at the center, two balls of radius r/2. With a reference in the generated
// one-limb kernels (kairn), as m2.cpp writes its floors.
template <class T, bool Kernels>
KB_SI void ball_of(T l, T h, T& c, T& r) {
    if constexpr (Kernels) {
        T s, d;
        kg::add_1_1(l, h, s);
        kg::mul_1_1(s, T(0.5), c);
        kg::sub_1_1(h, l, d);
        kg::mul_1_1(d, T(0.5), r);
    } else {
        c = (l + h) * T(0.5);
        r = (h - l) * T(0.5);
    }
}
template <class T, bool Kernels>
KB_SI void bounds_of(const B<T, 1>& x, T& l, T& h) {
    if constexpr (Kernels) {
        kg::sub_1_1(x.center().limb[0], x.radius(), l);
        kg::add_1_1(x.center().limb[0], x.radius(), h);
    } else {
        l = x.center().limb[0] - x.radius();
        h = x.center().limb[0] + x.radius();
    }
}
template <class T, bool Kernels>
KB_SI void phull(T* o, int i, const B<T, 1>& x, const B<T, 1>& y) {
    T xl, xh, yl, yh;
    bounds_of<T, Kernels>(x, xl, xh);
    bounds_of<T, Kernels>(y, yl, yh);
    ball_of<T, Kernels>(yl < xl ? yl : xl, xh < yh ? yh : xh, o[2 * i], o[2 * i + 1]);
}
template <class T, bool Kernels>
KB_SI void pinter(T* o, int i, const B<T, 1>& x, const B<T, 1>& y) {
    T xl, xh, yl, yh;
    bounds_of<T, Kernels>(x, xl, xh);
    bounds_of<T, Kernels>(y, yl, yh);
    ball_of<T, Kernels>(xl < yl ? yl : xl, yh < xh ? yh : xh, o[2 * i], o[2 * i + 1]);
}
template <class T, bool Kernels>
KB_SI void psplit(T* o, int i, const B<T, 1>& x) {
    T h;
    const T c = x.center().limb[0];
    if constexpr (Kernels) {
        kg::mul_1_1(x.radius(), T(0.5), h);
        kg::sub_1_1(c, h, o[4 * i]);
        kg::add_1_1(c, h, o[4 * i + 2]);
    } else {
        h = x.radius() * T(0.5);
        o[4 * i] = c - h;
        o[4 * i + 2] = c + h;
    }
    o[4 * i + 1] = h;
    o[4 * i + 3] = h;
}

// The types, by the name of their data in the rows.
using d_i1 = I<double, 1>;
using d_i2 = I<double, 2>;
using d_b1 = B<double, 1>;
using d_b2 = B<double, 2>;
using f_i1 = I<float, 1>;
using f_i2 = I<float, 2>;
using f_b1 = B<float, 1>;
using f_b2 = B<float, 2>;

}  // namespace

// --- The timed functions ------------------------------------------------------------------------

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }
#define KB_N(X) info<X>::limbs   // values of T of one set

// X(B, S, TAG, KIND, OP, VARIANT, OUT, VALUES, BODY): S the type (d_i1, ...), TAG its short name,
// VALUES the values written per element (OUT O8 or OT) or in all (OC). In BODY, d is the Set of S, X
// the type, T its limb type, N the limbs of one set, O the limbs of the converted set, K the limbs of
// a number.
// A predicate: NS::OP(x) for NS api (variant op), kref (kairn) or plain (plain).
#define api_VAR op
#define kref_VAR kairn
#define plain_VAR plain
#define KB_EPRED(X, B, S, TAG, OP, NS) KB_EPRED_(X, B, S, TAG, OP, NS, NS##_VAR)
#define KB_EPRED_(X, B, S, TAG, OP, NS, VAR) KB_EPRED__(X, B, S, TAG, OP, NS, VAR)
#define KB_EPRED__(X, B, S, TAG, OP, NS, VAR) X(B, S, TAG, tp, OP, VAR, O8, 1, KB_EACH(d.o8[i] = NS::OP(d.x[i])))
#define KB_ECOMMON(X, B, S, TAG)                                                                   \
    X(B, S, TAG, tp, contains_t, op, O8, 1, KB_EACH(d.o8[i] = api::contains_t(d.x[i], d.t[i])))     \
    X(B, S, TAG, tp, contains_t, kairn, O8, 1, KB_EACH(d.o8[i] = kref::contains_t(d.x[i], d.t[i]))) \
    X(B, S, TAG, tp, contains_set, op, O8, 1, KB_EACH(d.o8[i] = api::contains_set(d.x[i], d.s[i]))) \
    X(B, S, TAG, tp, contains_set, kairn, O8, 1, KB_EACH(d.o8[i] = kref::contains_set(d.x[i], d.s[i]))) \
    X(B, S, TAG, tp, less, op, O8, 1, KB_EACH(d.o8[i] = t8(api::less(d.x[i], d.y[i]))))             \
    X(B, S, TAG, tp, less, kairn, O8, 1, KB_EACH(d.o8[i] = t8(kref::less(d.x[i], d.y[i]))))         \
    X(B, S, TAG, tp, less_equal, op, O8, 1, KB_EACH(d.o8[i] = t8(api::less_equal(d.x[i], d.y[i])))) \
    X(B, S, TAG, tp, less_equal, kairn, O8, 1, KB_EACH(d.o8[i] = t8(kref::less_equal(d.x[i], d.y[i])))) \
    X(B, S, TAG, tp, equal, op, O8, 1, KB_EACH(d.o8[i] = t8(api::equal(d.x[i], d.y[i]))))           \
    X(B, S, TAG, tp, equal, kairn, O8, 1, KB_EACH(d.o8[i] = t8(kref::equal(d.x[i], d.y[i]))))       \
    X(B, S, TAG, tp, member, op, O8, 1, KB_EACH(d.o8[i] = t8(api::member(d.t[i], d.x[i]))))         \
    X(B, S, TAG, tp, member, kairn, O8, 1, KB_EACH(d.o8[i] = t8(kref::member(d.t[i], d.x[i]))))     \
    KB_EPRED(X, B, S, TAG, empty, api) KB_EPRED(X, B, S, TAG, whole, api)                          \
    KB_EPRED(X, B, S, TAG, pos, api) KB_EPRED(X, B, S, TAG, pos, kref)                             \
    KB_EPRED(X, B, S, TAG, neg, api) KB_EPRED(X, B, S, TAG, neg, kref)                             \
    KB_EPRED(X, B, S, TAG, zero, api) KB_EPRED(X, B, S, TAG, zero, kref)                           \
    X(B, S, TAG, tp, hull, op, OT, KB_N(S), KB_EACH(put(d.ot, i, d.x[i].hull(d.w[i]))))             \
    X(B, S, TAG, tp, hull, kairn, OT, KB_N(S), KB_EACH(kref::hull(d.ot, i, d.x[i], d.w[i])))        \
    X(B, S, TAG, tp, intersection, op, OT, KB_N(S), KB_EACH(put(d.ot, i, d.x[i].intersection(d.w[i])))) \
    X(B, S, TAG, tp, intersection, kairn, OT, KB_N(S), KB_EACH(kref::intersection(d.ot, i, d.x[i], d.w[i]))) \
    X(B, S, TAG, tp, split, op, OT, 2 * KB_N(S), KB_EACH(put_split(d.ot, i, d.x[i].split())))       \
    X(B, S, TAG, tp, split, kairn, OT, 2 * KB_N(S), KB_EACH(kref::split(d.ot, i, d.x[i])))          \
    X(B, S, TAG, tp, convert, op, OT, info<info<S>::other>::limbs,                                 \
      KB_EACH(put(d.ot, i, typename info<S>::other(d.x[i]))))                                      \
    X(B, S, TAG, tp, convert, kairn, OT, info<info<S>::other>::limbs, KB_EACH(kref::convert(d.ot, i, d.x[i]))) \
    /* chains */                                                                                   \
    X(B, S, TAG, step, hull, op, OC, KB_N(S), S h = d.x[0]; KB_EACH(h = h.hull(d.x[i])) put(d.oc, 0, h);) \
    X(B, S, TAG, step, intersection, op, OC, KB_N(S), S h = d.wc[0];                               \
      KB_EACH(h = h.intersection(d.wc[i])) put(d.oc, 0, h);)                                       \
    X(B, S, TAG, step, split, op, OC, KB_N(S), S h = d.x[0];                                       \
      KB_EACH(h = h.split().left; if ((i & 31) == 31) h = d.x[i]) put(d.oc, 0, h);)                \
    X(B, S, TAG, step, convert, op, OC, KB_N(S), S h = d.x[0];                                     \
      KB_EACH(h = S(typename info<S>::other(h))) put(d.oc, 0, h);)

// The chains' references: the same steps on the limbs with the kernels.
#define KB_ECHAINREF(X, B, S, TAG, N, LIM)                                                         \
    X(B, S, TAG, step, hull, kairn, OC, N, typename info<S>::T h[N]; get_limbs(d.x[0], h);          \
      KB_EACH(typename info<S>::T z[N]; kref_hull_limbs(h, d.x[i], z); for (int j = 0; j < N; ++j) h[j] = z[j]) \
      for (int j = 0; j < N; ++j) d.oc[j] = h[j];)                                                 \
    X(B, S, TAG, step, intersection, kairn, OC, N, typename info<S>::T h[N]; get_limbs(d.wc[0], h); \
      KB_EACH(typename info<S>::T z[N]; kref_inter_limbs(h, d.wc[i], z); for (int j = 0; j < N; ++j) h[j] = z[j]) \
      for (int j = 0; j < N; ++j) d.oc[j] = h[j];)                                                 \
    X(B, S, TAG, step, split, kairn, OC, N, typename info<S>::T h[N]; get_limbs(d.x[0], h);         \
      KB_EACH(typename info<S>::T z[2 * N]; kref_split_limbs<S>(h, z); for (int j = 0; j < N; ++j) h[j] = z[j]; \
              if ((i & 31) == 31) get_limbs(d.x[i], h))                                            \
      for (int j = 0; j < N; ++j) d.oc[j] = h[j];)                                                 \
    X(B, S, TAG, step, convert, kairn, OC, N, typename info<S>::T h[N]; get_limbs(d.x[0], h);       \
      KB_EACH(kref_round_trip<S>(h)) for (int j = 0; j < N; ++j) d.oc[j] = h[j];)

#define KB_EINTERVAL(X, B, S, TAG)                                                                 \
    KB_EPRED(X, B, S, TAG, empty, kref) KB_EPRED(X, B, S, TAG, whole, kref)                        \
    X(B, S, TAG, tp, rel_equal, op, O8, 1, KB_EACH(d.o8[i] = api::rel_equal(d.x[i], d.y[i])))       \
    X(B, S, TAG, tp, rel_equal, kairn, O8, 1, KB_EACH(d.o8[i] = kref::rel_equal(d.x[i], d.y[i])))   \
    X(B, S, TAG, tp, rel_interior, op, O8, 1, KB_EACH(d.o8[i] = api::rel_interior(d.s[i], d.x[i]))) \
    X(B, S, TAG, tp, rel_interior, kairn, O8, 1, KB_EACH(d.o8[i] = kref::rel_interior(d.s[i], d.x[i]))) \
    X(B, S, TAG, tp, rel_disjoint, op, O8, 1, KB_EACH(d.o8[i] = api::rel_disjoint(d.x[i], d.y[i]))) \
    X(B, S, TAG, tp, rel_disjoint, kairn, O8, 1, KB_EACH(d.o8[i] = kref::rel_disjoint(d.x[i], d.y[i]))) \
    /* midpoint() and radius() each run the kernel of both; mid_rad() runs it once */              \
    X(B, S, TAG, tp, midpoint, op, OT, info<S>::K, KB_EACH(put_number(d.ot, i, d.x[i].midpoint()))) \
    X(B, S, TAG, tp, midpoint, kairn, OT, info<S>::K, KB_EACH(typename info<S>::T r; kref::mid_rad(d.x[i], d.ot + info<S>::K * i, r))) \
    X(B, S, TAG, tp, radius, op, OT, 1, KB_EACH(d.ot[i] = d.x[i].radius()))                         \
    X(B, S, TAG, tp, radius, kairn, OT, 1, KB_EACH(typename info<S>::T m[2]; kref::mid_rad(d.x[i], m, d.ot[i]))) \
    X(B, S, TAG, tp, midrad2, op, OT, info<S>::K + 1,                                              \
      KB_EACH(put_number(d.ot, i, d.x[i].midpoint()); d.ot[info<S>::K * kN + i] = d.x[i].radius())) \
    X(B, S, TAG, tp, midrad2, kairn, OT, info<S>::K + 1,                                           \
      KB_EACH(kref::mid_rad(d.x[i], d.ot + info<S>::K * i, d.ot[info<S>::K * kN + i])))             \
    X(B, S, TAG, tp, midrad, op, OT, info<S>::K + 1,                                               \
      KB_EACH(const auto mr = d.x[i].mid_rad(); put_number(d.ot, i, mr.midpoint); d.ot[info<S>::K * kN + i] = mr.radius)) \
    X(B, S, TAG, tp, midrad, kairn, OT, info<S>::K + 1,                                            \
      KB_EACH(kref::mid_rad(d.x[i], d.ot + info<S>::K * i, d.ot[info<S>::K * kN + i])))

// A ball's center and radius are stored: is_empty() and is_whole() test the radius, midpoint() and
// radius() read the limbs; no kernel computes them, and their references are those tests and reads.
#define KB_EBALL(X, B, S, TAG)                                                                     \
    KB_EPRED(X, B, S, TAG, empty, kref) KB_EPRED(X, B, S, TAG, whole, kref)                        \
    X(B, S, TAG, tp, midrad, kairn, OT, info<S>::K + 1,                                            \
      KB_EACH(for (int j = 0; j < info<S>::K; ++j) d.ot[info<S>::K * i + j] = d.x[i].center().limb[j]; \
              d.ot[info<S>::K * kN + i] = d.x[i].radius()))                                        \
    X(B, S, TAG, tp, midrad2, op, OT, info<S>::K + 1,                                              \
      KB_EACH(put_number(d.ot, i, d.x[i].midpoint()); d.ot[info<S>::K * kN + i] = d.x[i].radius())) \
    X(B, S, TAG, tp, midrad2, kairn, OT, info<S>::K + 1,                                           \
      KB_EACH(for (int j = 0; j < info<S>::K; ++j) d.ot[info<S>::K * i + j] = d.x[i].center().limb[j]; \
              d.ot[info<S>::K * kN + i] = d.x[i].radius()))                                        \
    X(B, S, TAG, tp, midrad, op, OT, info<S>::K + 1,                                               \
      KB_EACH(const auto mr = d.x[i].mid_rad(); put_number(d.ot, i, mr.midpoint); d.ot[info<S>::K * kN + i] = mr.radius))

// The controls in plain T, one limb.
#define KB_EPLAIN(X, B, S, TAG)                                                                    \
    KB_EPRED(X, B, S, TAG, empty, plain) KB_EPRED(X, B, S, TAG, whole, plain)                      \
    KB_EPRED(X, B, S, TAG, pos, plain) KB_EPRED(X, B, S, TAG, neg, plain) KB_EPRED(X, B, S, TAG, zero, plain) \
    X(B, S, TAG, tp, contains_t, plain, O8, 1, KB_EACH(d.o8[i] = plain::contains_t(d.x[i], d.t[i]))) \
    X(B, S, TAG, tp, contains_set, plain, O8, 1, KB_EACH(d.o8[i] = plain::contains_set(d.x[i], d.s[i]))) \
    X(B, S, TAG, tp, less, plain, O8, 1, KB_EACH(d.o8[i] = t8(plain::less(d.x[i], d.y[i]))))         \
    X(B, S, TAG, tp, less_equal, plain, O8, 1, KB_EACH(d.o8[i] = t8(plain::less_equal(d.x[i], d.y[i])))) \
    X(B, S, TAG, tp, equal, plain, O8, 1, KB_EACH(d.o8[i] = t8(plain::equal(d.x[i], d.y[i]))))       \
    X(B, S, TAG, tp, member, plain, O8, 1, KB_EACH(d.o8[i] = t8(plain::member(d.t[i], d.x[i]))))
#define KB_EPLAIN_I1(X, B, S, TAG)                                                                 \
    X(B, S, TAG, tp, rel_equal, plain, O8, 1, KB_EACH(d.o8[i] = plain::rel_equal(d.x[i], d.y[i])))   \
    X(B, S, TAG, tp, rel_interior, plain, O8, 1, KB_EACH(d.o8[i] = plain::rel_interior(d.s[i], d.x[i]))) \
    X(B, S, TAG, tp, rel_disjoint, plain, O8, 1, KB_EACH(d.o8[i] = plain::rel_disjoint(d.x[i], d.y[i]))) \
    X(B, S, TAG, tp, hull, plain, OT, 2, KB_EACH(plain::hull(d.ot, i, d.x[i], d.w[i])))              \
    X(B, S, TAG, tp, intersection, plain, OT, 2, KB_EACH(plain::intersection(d.ot, i, d.x[i], d.w[i])))
#define KB_EPLAIN_B1(X, B, S, TAG)                                                                 \
    X(B, S, TAG, tp, phull, plain, OT, 2, KB_EACH((phull<info<S>::T, false>(d.ot, i, d.x[i], d.w[i])))) \
    X(B, S, TAG, tp, phull, kairn, OT, 2, KB_EACH((phull<info<S>::T, true>(d.ot, i, d.x[i], d.w[i]))))  \
    X(B, S, TAG, tp, pinter, plain, OT, 2, KB_EACH((pinter<info<S>::T, false>(d.ot, i, d.x[i], d.w[i])))) \
    X(B, S, TAG, tp, pinter, kairn, OT, 2, KB_EACH((pinter<info<S>::T, true>(d.ot, i, d.x[i], d.w[i])))) \
    X(B, S, TAG, tp, psplit, plain, OT, 4, KB_EACH((psplit<info<S>::T, false>(d.ot, i, d.x[i]))))    \
    X(B, S, TAG, tp, psplit, kairn, OT, 4, KB_EACH((psplit<info<S>::T, true>(d.ot, i, d.x[i]))))

#define KB_ETYPE_I(X, B, S, TAG, N) KB_ECOMMON(X, B, S, TAG) KB_ECHAINREF(X, B, S, TAG, N, ) KB_EINTERVAL(X, B, S, TAG)
#define KB_ETYPE_B(X, B, S, TAG, N) KB_ECOMMON(X, B, S, TAG) KB_ECHAINREF(X, B, S, TAG, N, ) KB_EBALL(X, B, S, TAG)
#define KB_ELIMB(X, B, P)                                                                          \
    KB_ETYPE_I(X, B, P##_i1, i1, 2) KB_EPLAIN(X, B, P##_i1, i1) KB_EPLAIN_I1(X, B, P##_i1, i1)       \
    KB_ETYPE_I(X, B, P##_i2, i2, 4)                                                                \
    KB_ETYPE_B(X, B, P##_b1, b1, 2) KB_EPLAIN(X, B, P##_b1, b1) KB_EPLAIN_B1(X, B, P##_b1, b1)       \
    KB_ETYPE_B(X, B, P##_b2, b2, 3)
#define KB_ELIST(X) KB_ELIMB(X, "m2e", d) KB_ELIMB(X, "m2ef", f)

namespace {

// The limbs of a set, and the chains' steps on limbs.
template <class T> KB_SI void get_limbs(const I<T, 1>& x, T* h) { h[0] = x.lower().limb[0]; h[1] = x.upper().limb[0]; }
template <class T> KB_SI void get_limbs(const I<T, 2>& x, T* h) {
    h[0] = x.lower().limb[0]; h[1] = x.lower().limb[1]; h[2] = x.upper().limb[0]; h[3] = x.upper().limb[1];
}
template <class T> KB_SI void get_limbs(const B<T, 1>& x, T* h) { h[0] = x.center().limb[0]; h[1] = x.radius(); }
template <class T> KB_SI void get_limbs(const B<T, 2>& x, T* h) { h[0] = x.center().limb[0]; h[1] = x.center().limb[1]; h[2] = x.radius(); }
#define KB_LIMBOP(NAME, KI, KB)                                                                    \
    template <class T> KB_SI void NAME(const T* h, const I<T, 1>& y, T* z) { kg::interval_##KI##_1(h[0], h[1], LI1(y), z[0], z[1]); } \
    template <class T> KB_SI void NAME(const T* h, const I<T, 2>& y, T* z) {                        \
        kg::interval_##KI##_2(h[0], h[1], h[2], h[3], LI2(y), z[0], z[1], z[2], z[3]); }            \
    template <class T> KB_SI void NAME(const T* h, const B<T, 1>& y, T* z) { kg::ball_##KB##_1(h[0], h[1], LB1(y), z[0], z[1]); } \
    template <class T> KB_SI void NAME(const T* h, const B<T, 2>& y, T* z) { kg::ball_##KB##_2(h[0], h[1], h[2], LB2(y), z[0], z[1], z[2]); }
KB_LIMBOP(kref_hull_limbs, hull, hull)
KB_LIMBOP(kref_inter_limbs, intersection, intersection)
template <class X, class T>
KB_SI void kref_split_limbs(const T* h, T* z) {
    if constexpr (std::is_same_v<X, I<T, 1>>) {
        kg::interval_split_1(h[0], h[1], z[0], z[1], z[2], z[3]);
    } else if constexpr (std::is_same_v<X, I<T, 2>>) {
        kg::interval_split_2(h[0], h[1], h[2], h[3], z[0], z[1], z[2], z[3], z[4], z[5], z[6], z[7]);
    } else if constexpr (std::is_same_v<X, B<T, 1>>) {
        kg::ball_split_1(h[0], h[1], z[0], z[1], z[2], z[3]);
    } else {
        kg::ball_split_2(h[0], h[1], h[2], z[0], z[1], z[2], z[3], z[4], z[5]);
    }
}
template <class X, class T>
KB_SI void kref_round_trip(T* h) {
    if constexpr (std::is_same_v<X, I<T, 1>>) {
        T c, r;
        kg::interval_to_ball_1(h[0], h[1], c, r);
        kg::ball_to_interval_1(c, r, h[0], h[1]);
    } else if constexpr (std::is_same_v<X, I<T, 2>>) {
        T c0, c1, r;
        kg::interval_to_ball_2(h[0], h[1], h[2], h[3], c0, c1, r);
        kg::ball_to_interval_2(c0, c1, r, h[0], h[1], h[2], h[3]);
    } else if constexpr (std::is_same_v<X, B<T, 1>>) {
        T l, u;
        kg::ball_to_interval_1(h[0], h[1], l, u);
        kg::interval_to_ball_1(l, u, h[0], h[1]);
    } else {
        T l0, l1, u0, u1;
        kg::ball_to_interval_2(h[0], h[1], h[2], l0, l1, u0, u1);
        kg::interval_to_ball_2(l0, l1, u0, u1, h[0], h[1], h[2]);
    }
}

bool check(const Entry& e, char* why, std::size_t size);

}  // namespace

#define KB_EDEF(B, S, TAG, KIND, OP, VAR, OUT, VALUES, ...)                                        \
    extern "C" KB_NOINLINE void kb_m2_e##S##_##KIND##_##OP##__##VAR(void*) {                         \
        [[maybe_unused]] Set<S>& d = *g_set<S>;                                                    \
        __VA_ARGS__                                                                                \
    }
#define KB_ENAME(B, TAG, KIND, OP, VAR) B "/" #KIND "/" #TAG "_" #OP "/" #VAR
#define KB_EROW(B, S, TAG, KIND, OP, VAR, OUT, VALUES, ...)                                        \
    {KB_ENAME(B, TAG, KIND, OP, VAR), kb_m2_e##S##_##KIND##_##OP##__##VAR, int(8 * sizeof(info<S>::T)), 1,     \
     kN, OUT, OUT == OC ? (VALUES) : (VALUES) * kN, &check},

KB_ELIST(KB_EDEF)

namespace kairn_bench::m2 {

const Entry m2_enc_entries[] = {
    KB_ELIST(KB_EROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};

}  // namespace kairn_bench::m2

namespace {

using kairn_bench::util::Rng;

// The sets of one type around centers c, of half-width h (both as numbers of K limbs and T).
template <class T>
I<T, 1> make_set(const E<T, 1>& c, T h, I<T, 1>*) {
    return I<T, 1>(E<T, 1>(c.limb[0] - h), E<T, 1>(c.limb[0] + h));
}
template <class T>
I<T, 2> make_set(const E<T, 2>& c, T h, I<T, 2>*) {
    return I<T, 2>(c - E<T, 2>(h), c + E<T, 2>(h));
}
template <class T>
B<T, 1> make_set(const E<T, 1>& c, T h, B<T, 1>*) {
    return B<T, 1>(c, h);
}
template <class T>
B<T, 2> make_set(const E<T, 2>& c, T h, B<T, 2>*) {
    return B<T, 2>(c, h);
}

template <class X>
void fill(std::uint64_t seed) {
    using T = typename info<X>::T;
    constexpr int K = info<X>::K;
    if (!g_set<X>) g_set<X> = new Set<X>();
    Set<X>& d = *g_set<X>;
    Rng g{seed};
    const int rel = K == 1 ? (sizeof(T) == 8 ? 30 : 12) : (sizeof(T) == 8 ? 80 : 40);
    const auto center = [&g]() {
        const double s = g.sign();
        const double m = 1.0 + g.u01();
        const T a = T(s * std::ldexp(m, g.range(-4, 4)));
        if constexpr (K == 1) {
            return E<T, 1>(a);
        } else {
            const T b = T(double(a) * g.sym() * std::ldexp(1.0, -std::numeric_limits<T>::digits));
            T l[2];
            kg::fast_two_sum(a, b, l[0], l[1]);
            return E<T, 2>::from_limbs(l);
        }
    };
    static const int shifts[5] = {-6, -1, 0, 1, 6};
    for (int i = 0; i < kN; ++i) {
        const E<T, K> c = center();
        const T h = T(std::fabs(double(c.limb[0])) * std::ldexp(0.5 + 0.5 * g.u01(), -rel));
        d.x[i] = make_set(c, h, static_cast<X*>(nullptr));
        const int shift = shifts[g.range(0, 4)];
        d.y[i] = make_set(c + E<T, K>(T(shift) * h), h, static_cast<X*>(nullptr));
        d.s[i] = (g.next() & 1) ? make_set(c + E<T, K>(h / 4), h / 2, static_cast<X*>(nullptr)) : d.y[i];
        d.w[i] = make_set(c + E<T, K>(h), h, static_cast<X*>(nullptr));
        d.t[i] = (g.next() & 1) ? c.limb[0] : T(c.limb[0] + 3 * h);
        d.wc[i] = make_set(E<T, K>(T(0.1 * g.sym())), T(1 + 0.5 * g.u01()), static_cast<X*>(nullptr));
    }
}

void setup() {
    static bool done = false;
    if (done) return;
    done = true;
    fill<d_i1>(201);
    fill<d_i2>(202);
    fill<d_b1>(203);
    fill<d_b2>(204);
    fill<f_i1>(205);
    fill<f_i2>(206);
    fill<f_b1>(207);
    fill<f_b2>(208);
}

// The bytes of a region of the Set of the type of a function, after it ran.
struct Region {
    const unsigned char* p;
    std::size_t bytes;
};
template <class X>
Region region(int out, int values) {
    Set<X>& d = *g_set<X>;
    using T = typename info<X>::T;
    if (out == O8) return {reinterpret_cast<const unsigned char*>(d.o8), std::size_t(values)};
    if (out == OT) return {reinterpret_cast<const unsigned char*>(d.ot), std::size_t(values) * sizeof(T)};
    return {reinterpret_cast<const unsigned char*>(d.oc), std::size_t(values) * sizeof(T)};
}
template <class X>
void clear() {
    Set<X>& d = *g_set<X>;
    std::memset(d.o8, 0x7f, sizeof d.o8);
    std::memset(d.ot, 0xff, sizeof d.ot);
    std::memset(d.oc, 0xff, sizeof d.oc);
}
template <class X>
bool compare(const Entry& e, const Entry& ref, char* why, std::size_t size) {
    clear<X>();
    ref.fn(nullptr);
    const Region a = region<X>(ref.region, ref.values);
    const std::vector<unsigned char> want(a.p, a.p + a.bytes);
    clear<X>();
    e.fn(nullptr);
    const Region b = region<X>(e.region, e.values);
    if (a.bytes != b.bytes) {
        std::snprintf(why, size, "not the same number of values as %s", ref.name);
        return false;
    }
    for (std::size_t k = 0; k < b.bytes; ++k)
        if (want[k] != b.p[k]) {
            std::snprintf(why, size, "byte %zu differs from %s", k, ref.name);
            return false;
        }
    return true;
}

const Entry* find_entry(const std::string& name) {
    for (const Entry* e = kairn_bench::m2::m2_enc_entries; e->name; ++e)
        if (name == e->name) return e;
    return nullptr;
}

bool check(const Entry& e, char* why, std::size_t size) {
    setup();
    const std::string name = e.name;
    const std::string ref_name = name.substr(0, name.rfind('/')) + "/kairn";
    const Entry* ref = find_entry(ref_name);
    if (!ref) ref = find_entry(name.substr(0, name.rfind('/')) + "/plain");   // a ball's accessors
    if (!ref) {
        std::snprintf(why, size, "no reference %s", ref_name.c_str());
        return false;
    }
    if (ref == &e) return true;
    // The type: the backend gives the limb type, the kernel's first letters the kind and the limbs.
    const bool f = name.compare(0, 5, "m2ef/") == 0;
    const std::string tag = name.substr(name.find('/', name.find('/') + 1) + 1, 2);
    if (tag == "i1") return f ? compare<f_i1>(e, *ref, why, size) : compare<d_i1>(e, *ref, why, size);
    if (tag == "i2") return f ? compare<f_i2>(e, *ref, why, size) : compare<d_i2>(e, *ref, why, size);
    if (tag == "b1") return f ? compare<f_b1>(e, *ref, why, size) : compare<d_b1>(e, *ref, why, size);
    return f ? compare<f_b2>(e, *ref, why, size) : compare<d_b2>(e, *ref, why, size);
}

}  // namespace
